"""Strict mcq-draft-v1 adapter. Operator-only, synthetic QA databases exclusively."""
from datetime import datetime, timedelta
import hashlib
import html
import json
import re
import unicodedata
from urllib.parse import unquote

from . import platform_api as api

SCHEMA_VERSION = 'mcq-draft-v1'
SKILLS = {'g5.parts', 'g5.unit', 'g5.reverse'}
PROVISIONAL_DIFFICULTY = {i: min(4, (i-1)//3+1) for i in range(1,11)}


class ImportFailure(ValueError):
    pass


def fail(path, message):
    raise ImportFailure(f'{path}: {message}')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_json(path):
    raw = path.read_bytes()
    if len(raw) > 4*1024*1024:
        fail(str(path),'package exceeds 4 MiB')
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result: fail(str(path),f'duplicate JSON field {k}')
            result[k]=v
        return result
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda x: fail(str(path),f'invalid numeric constant {x}'))


def scan(value, path='$', depth=0):
    if depth > 30: fail(path,'maximum nesting exceeded')
    if isinstance(value, dict):
        if path.startswith('$.questions[') and isinstance(value.get('contentKey'),str):
            path=value['contentKey']
        for k,v in value.items():
            if not isinstance(k,str): fail(path,'JSON keys must be strings')
            if k.casefold() in {'html','mathml','url','href','src','media','image','video','asset_id','assets'}:
                fail(path+'.'+k,'unsupported media/HTML/URL field')
            scan(v,path+'.'+k,depth+1)
    elif isinstance(value,list):
        for i,v in enumerate(value): scan(v,f'{path}[{i}]',depth+1)
    elif isinstance(value,str):
        decoded=unicodedata.normalize('NFKC',html.unescape(unquote(value)))
        if len(value)>30000: fail(path,'text too long')
        if any(unicodedata.category(c) in ('Cc','Cf') and c not in '\n\t\r' for c in decoded):
            fail(path,'unsupported invisible/control character')
        if re.search(r'<\s*/?\s*[a-z!][^>]*>|(?:https?|file)\s*://|www\.|data\s*:|javascript\s*:|\\(?:href|url|includegraphics)\b',decoded,re.I):
            fail(path,'unsupported media/HTML/URL content (metadata is never fetched)')
    elif value is not None and type(value) not in (bool,int,float):
        fail(path,'unsupported JSON value')


def text(value,path):
    if not isinstance(value,str) or not value.strip(): fail(path,'nonempty text required')
    return value


def key(value,path):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,119}',value):
        fail(path,'invalid stable key')
    return value


def integer(value,path,minimum=1,maximum=1000000):
    if type(value) is not int or not minimum<=value<=maximum: fail(path,'invalid integer')
    return value


def blocks(value,path):
    if isinstance(value,str):
        return [{'type':'text','text':text(value,path)}]
    if not isinstance(value,list) or not value: fail(path,'text or nonempty text/math blocks required')
    result=[]
    for i,block in enumerate(value):
        where=f'{path}[{i}]'
        if isinstance(block,str): result.append({'type':'text','text':text(block,where)}); continue
        if not isinstance(block,dict): fail(where,'invalid block')
        kind=block.get('type')
        prop='text' if kind=='text' else 'latex' if kind=='math' else None
        if not prop or set(block)!={'type',prop}: fail(where,'only plain text or LaTeX blocks supported')
        text(block[prop],where+'.'+prop)
        result.append(dict(block))
    return result


def review(value,path,allow_draft):
    if not isinstance(value,dict) or type(value.get('independentTeacherApproved')) is not bool:
        fail(path,'reviewStatus with boolean independentTeacherApproved required')
    approved=value['independentTeacherApproved'] and value.get('stage') in ('teacher-approved','approved','independently-approved')
    draft=value.get('stage')=='draft-self-checked' and value['independentTeacherApproved'] is False
    if not approved and not (allow_draft and draft):
        fail(path,'draft rejected by default; explicit allow_draft_qa needed on synthetic QA only')
    return not approved


def source_registry(sources):
    raw_sources=sources.get('questions') if isinstance(sources,dict) else None
    if not isinstance(raw_sources,list): fail('sources','trusted original question registry required')
    registry={}
    for source in raw_sources:
        if not isinstance(source,dict): fail('sources','source record object required')
        ident=(key(source.get('contentKey'),'sources.contentKey'),integer(source.get('revision'),'sources.revision'))
        if ident in registry: fail('sources','duplicate source key/revision')
        registry[ident]=source
    return registry


def normalize_question(q,registry,allow_draft_qa):
    if not isinstance(q,dict): fail('questions','question object required')
    scan(q)
    ck=key(q.get('contentKey'),'questions.contentKey'); where=ck
    rev=integer(q.get('revision'),where+'.revision')
    sk=key(q.get('sourceContentKey'),where+'.sourceContentKey')
    sr=integer(q.get('sourceRevision'),where+'.sourceRevision')
    source=registry.get((sk,sr))
    if not source: fail(where+'.sourceContentKey/sourceRevision','unknown trusted source revision')
    reason=text(q.get('changeReason'),where+'.changeReason')
    relationship=q.get('lineageRelationship'); quota=key(q.get('quotaKey'),where+'.quotaKey')
    if relationship=='equivalent':
        if ck!=sk or rev<=sr or quota!=sk: fail(where+'.quotaKey','equivalent must keep source contentKey/quotaKey and increase revision')
        if q.get('skillKey')!=source.get('skillKey'): fail(where+'.skillKey','equivalent must keep source skill')
    elif relationship=='replacement':
        if ck==sk or quota!=ck or any(k[0]==ck for k in registry):
            fail(where+'.quotaKey','replacement requires a new contentKey/quotaKey and reason')
    else: fail(where+'.lineageRelationship','expected equivalent or replacement')
    if type(q.get('grade')) is not int or q['grade']!=5 or source.get('grade')!=5:
        fail(where+'.grade','only grade5 and matching source supported')
    if not isinstance(q.get('skillKey'),str) or q['skillKey'] not in SKILLS: fail(where+'.skillKey','unsupported pilot skill')
    if q.get('proposedAccess') not in ('Free','VIP'): fail(where+'.proposedAccess','Free or VIP required')
    if q.get('responseType') not in ('single-choice','short-answer'): fail(where+'.responseType','short-answer or legacy single-choice required')
    difficulty=q.get('difficultyOriginal')
    if not isinstance(difficulty,dict): fail(where+'.difficultyOriginal','value/scale/reason object required')
    level=integer(difficulty.get('value'),where+'.difficultyOriginal.value',1,10)
    if difficulty.get('scale')!='1-10': fail(where+'.difficultyOriginal.scale','expected 1-10')
    text(difficulty.get('reason'),where+'.difficultyOriginal.reason')
    if not isinstance(q.get('prerequisites'),list): fail(where+'.prerequisites','list required')
    for v in q['prerequisites']: text(v,where+'.prerequisites')
    if q['responseType']=='short-answer':
        from .answers import validate_rule
        try: rule=validate_rule(q.get('correctAnswer'),q.get('answerKind','auto'))
        except ValueError as error: fail(where+'.correctAnswer',str(error))
        option_texts=[];answer=rule['answer']
    else:
        choices=q.get('choices')
        if not isinstance(choices,list) or len(choices)!=4: fail(where+'.choices','exactly four choices required')
        ids=[]; option_texts=[]
        for choice in choices:
            if not isinstance(choice,dict) or set(choice)!={'id','text'}: fail(where+'.choices','objects must contain only id,text')
            ids.append(choice['id']); option_texts.append(text(choice['text'],where+'.choices.text'))
        if any(not isinstance(i,str) for i in ids) or sorted(ids)!=list('ABCD'): fail(where+'.choices.id','unique A/B/C/D required')
        norms=[' '.join(unicodedata.normalize('NFKC',v).split()).casefold() for v in option_texts]
        if len(set(norms))!=4: fail(where+'.choices.text','duplicate normalized choice text')
        correct=q.get('correctChoiceId')
        if correct not in ids: fail(where+'.correctChoiceId','must identify exactly one choice')
        rationales=q.get('choiceRationales')
        if not isinstance(rationales,dict) or set(rationales)!=set('ABCD'): fail(where+'.choiceRationales','all four rationale IDs required')
        for rid,value in rationales.items():
            if isinstance(value,dict):
                if not any(isinstance(v,str) and v.strip() for v in value.values()): fail(where+'.choiceRationales.'+rid,'nonempty rationale text required')
            else: text(value,where+'.choiceRationales.'+rid)
        answer=option_texts[ids.index(correct)]
    prompt=blocks(q.get('prompt'),where+'.prompt')
    if relationship=='equivalent':
        source_prompt=blocks(source.get('prompt'),where+'.source.prompt')
        norm=lambda b: ' '.join(unicodedata.normalize('NFKC',api.blocks_text(b)).split()).casefold()
        if norm(prompt)!=norm(source_prompt):
            fail(where+'.prompt','equivalent must preserve the trusted source problem; use reviewed replacement for a different problem')
    hints=blocks(q.get('hints'),where+'.hints')
    solution=blocks(q.get('solutionSteps'),where+'.solutionSteps')
    explanation=blocks(q.get('answerExplanation'),where+'.answerExplanation')
    for field in ('verification','origin','sourceLocator'):
        if not isinstance(q.get(field),(dict,str)) or not q[field]: fail(where+'.'+field,'metadata required')
    if isinstance(q['origin'],dict):
        text(q['origin'].get('kind'),where+'.origin.kind')
        if q['origin']['kind']!='synthetic-fixture': text(q['origin'].get('rightsNote'),where+'.origin.rightsNote')
    for field in ('sourceRecordId','sourceDataset','topicKey'):
        if field in q: text(q[field],where+'.'+field)
    guide=q.get('inputGuide')
    if guide is not None:
        if q['responseType']!='short-answer' or not isinstance(guide,dict) or set(guide)!={'instruction','labels','units','separator'}:fail(where+'.inputGuide','typed safe guide shape required')
        text(guide['instruction'],where+'.inputGuide.instruction')
        if not isinstance(guide['labels'],list) or not isinstance(guide['units'],list) or not 1<=len(guide['labels'])<=20 or len(guide['labels'])!=len(guide['units']):fail(where+'.inputGuide','matching labels/units required')
        for value in guide['labels']+guide['units']:text(value,where+'.inputGuide')
        expected_separator=';' if q.get('answerKind') in ('ordered','unordered') else ''
        if guide['separator']!=expected_separator:fail(where+'.inputGuide.separator','separator must match answerKind')
    draft=review(q.get('reviewStatus'),where+'.reviewStatus',allow_draft_qa)
    return ({'raw':q,'sourceHash':digest(source),'prompt':prompt,'hints':hints,
            'solution':solution+explanation,'options':option_texts,'answer':answer,'answerKind':q.get('answerKind','auto'),
            'difficulty':PROVISIONAL_DIFFICULTY[level]},draft)


def validate(package, manifest, sources, *, allow_draft_qa=False):
    scan(package); scan(manifest)
    for value,label in ((package,'package'),(manifest,'manifest')):
        if not isinstance(value,dict) or value.get('schemaVersion')!=SCHEMA_VERSION or value.get('qaOnly') is not True:
            fail(label,'schemaVersion mcq-draft-v1 and qaOnly=true required')
    key(package.get('packageId'),'package.packageId')
    registry=source_registry(sources)
    questions=package.get('questions')
    if not isinstance(questions,list) or len(questions)!=10: fail('questions','round2 sample requires exactly 10 questions')
    seen=set(); normalized=[]; draft=False
    for q in questions:
        item,is_draft=normalize_question(q,registry,allow_draft_qa)
        ck=item['raw']['contentKey']
        if ck in seen: fail(ck,'duplicate contentKey')
        seen.add(ck); normalized.append(item); draft=is_draft or draft
    draft=review(manifest.get('reviewStatus'),'manifest.reviewStatus',allow_draft_qa) or draft
    key(manifest.get('setKey'),'manifest.setKey')
    if type(manifest.get('grade')) is not int or manifest['grade']!=5: fail('manifest.grade','grade5 required')
    if manifest.get('timeZone')!='Asia/Saigon' or manifest.get('windowEndExclusive') is not True:
        fail('manifest.window','Asia/Saigon and exclusive end required')
    try:
        start=datetime.fromisoformat(manifest['windowStart']); end=datetime.fromisoformat(manifest['windowEnd'])
        valid=start.utcoffset()==end.utcoffset()==timedelta(hours=7) and start.weekday()==0 and start.time().isoformat()=='00:00:00' and end-start==timedelta(days=7)
    except (KeyError,ValueError,TypeError): valid=False
    if not valid: fail('manifest.window','Monday midnight +07:00, seven-day exclusive window required')
    free=manifest.get('orderedContentKeys'); vip=manifest.get('vipSupplementContentKeys')
    if not isinstance(free,list) or not isinstance(vip,list) or len(free)!=5 or len(vip)!=5 or any(not isinstance(k,str) for k in free+vip):
        fail('manifest.keys','five Free and five VIP keys required')
    if len(set(free+vip))!=10 or set(free+vip)!=seen: fail('manifest.keys','keys must partition all ten questions without duplicates')
    revisions=manifest.get('contentRevisions')
    if not isinstance(revisions,dict) or not set(free)<=set(revisions)<=seen: fail('manifest.contentRevisions','pin all Free revisions; optional VIP pins must belong to this package')
    bykey={v['raw']['contentKey']:v['raw'] for v in normalized}
    for ck in free+vip:
        if bykey[ck]['proposedAccess']!=('Free' if ck in free else 'VIP'): fail('manifest.'+ck,'access mismatch')
    for ck in revisions: integer(revisions[ck],'manifest.contentRevisions.'+ck)
    return normalized, {'draft':draft,'start':start.date().isoformat(),'end':end.date().isoformat()}


TABLES = [
 'CREATE TABLE IF NOT EXISTS mcq_import_batches(batch_id TEXT PRIMARY KEY,package_hash TEXT NOT NULL,manifest_hash TEXT NOT NULL,source_hash TEXT NOT NULL,mapping_json TEXT NOT NULL,result_json TEXT NOT NULL,imported_at TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS mcq_versions(version_id INTEGER PRIMARY KEY REFERENCES question_versions(id),content_key TEXT NOT NULL,revision INTEGER NOT NULL,quota_key TEXT NOT NULL,source_key TEXT NOT NULL,source_revision INTEGER NOT NULL,source_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,metadata_json TEXT NOT NULL,UNIQUE(content_key,revision))',
 'CREATE TABLE IF NOT EXISTS mcq_manifests(set_key TEXT PRIMARY KEY,manifest_hash TEXT NOT NULL,metadata_json TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS mcq_packages(package_id TEXT NOT NULL,package_hash TEXT NOT NULL,manifest_hash TEXT NOT NULL,source_hash TEXT NOT NULL,qa_only INTEGER NOT NULL,PRIMARY KEY(package_id,package_hash,manifest_hash))'
]


def require_qa(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_environment'").fetchone():
        fail('database','synthetic-only marker required; importer never initializes a real database')
    row=db.execute('SELECT label FROM pilot_environment WHERE id=1').fetchone()
    if not row or row[0]!='synthetic-only-v1': fail('database','synthetic-only-v1 marker required')


def store_versions(db,normalized):
    inserted=0; versions={}
    for item in normalized:
        q=item['raw']; ck=q['contentKey']; rev=q['revision']; payload_hash=digest(q)
        existing=db.execute('SELECT * FROM mcq_versions WHERE content_key=? AND revision=?',(ck,rev)).fetchone()
        if existing:
            if existing['payload_hash']!=payload_hash or existing['source_hash']!=item['sourceHash']:
                fail(ck+'.revision','same key/revision conflicts with immutable payload/source hash')
            versions[ck,rev]=existing['version_id']; continue
        identity=db.execute('SELECT * FROM mcq_versions WHERE content_key=? LIMIT 1',(ck,)).fetchone()
        if identity and (identity['quota_key'],identity['source_key'],identity['source_revision'],identity['source_hash'])!=(q['quotaKey'],q['sourceContentKey'],q['sourceRevision'],item['sourceHash']):
            fail(ck+'.lineage','cannot retarget an existing identity')
        current=db.execute('SELECT * FROM pilot_content WHERE content_key=?',(ck,)).fetchone()
        if current:
            if not identity: fail(ck,'unmapped pre-existing pilot key; requires explicit legacy backfill')
            if current['proposed_access']!=q['proposedAccess'].lower(): fail(ck+'.proposedAccess','access changes require separate policy decision')
            qid=current['question_id']
        else:
            topic=db.execute('SELECT id FROM topics WHERE grade_id=5 AND client_key=?',(q['skillKey'],)).fetchone()
            if topic: tid=topic[0]
            else: tid=db.execute('INSERT INTO topics(grade_id,title,client_key) VALUES (5,?,?)',(q['skillKey'],q['skillKey'])).lastrowid
            qid=db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (5,?,?)',(tid,ck)).lastrowid
            db.execute('INSERT INTO pilot_content VALUES (?,?,?)',(ck,qid,q['proposedAccess'].lower()))
        metadata={**q,'qaOnly':True,'sourceRecordHash':item['sourceHash'],
            'servingStatus':'qa-trial','difficultyMapping':{'provisional':True,'original':q['difficultyOriginal'],'engineLevel':item['difficulty']}}
        vid=db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,status,options_json) VALUES (?,?,?,1,?,?,?,?,'draft',?)",
            (qid,rev,item['difficulty'],api.packed(item['prompt']),api.packed({'answer':item['answer'],'answerKind':item['answerKind']}),api.packed(item['solution']),api.packed(item['hints']),api.packed(item['options']))).lastrowid
        db.execute('INSERT INTO mcq_versions VALUES (?,?,?,?,?,?,?,?,?)',
            (vid,ck,rev,q['quotaKey'],q['sourceContentKey'],q['sourceRevision'],item['sourceHash'],payload_hash,api.packed(metadata)))
        versions[ck,rev]=vid; inserted+=1
    return inserted,versions


def import_package(path,package,manifest,sources,*,allow_draft_qa=False):
    # Pure validation of ALL data occurs before opening a writable transaction.
    normalized,info=validate(package,manifest,sources,allow_draft_qa=allow_draft_qa)
    from pathlib import Path
    import sqlite3
    target=Path(path).resolve()
    if not target.is_file(): fail('database','existing synthetic QA database required')
    probe=sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)
    try: require_qa(probe)
    finally: probe.close()
    with api.connect(target,True) as db:
        require_qa(db)
        for sql in TABLES: db.execute(sql)
        inserted,versions=store_versions(db,normalized)
        for ck,revision in manifest['contentRevisions'].items():
            if not db.execute('SELECT 1 FROM mcq_versions WHERE content_key=? AND revision=?',(ck,revision)).fetchone():
                fail('manifest.contentRevisions.'+ck,'pinned version not imported')
        mh=digest(manifest); sk=manifest['setKey']
        old=db.execute('SELECT manifest_hash FROM mcq_manifests WHERE set_key=?',(sk,)).fetchone()
        if old and old[0]!=mh: fail('manifest.setKey','immutable manifest hash conflict')
        if not old:
            if db.execute('SELECT 1 FROM pilot_sets WHERE grade=5 AND window_start=? AND slot=1',(info['start'],)).fetchone():
                fail('manifest.window','window/slot already occupied; never overwrite an issued set')
            db.execute('INSERT INTO pilot_sets VALUES (?,5,?,?,1,1)',(sk,info['start'],info['end']))
            for pos,ck in enumerate(manifest['orderedContentKeys'],1):
                revision=manifest['contentRevisions'][ck]
                version=db.execute('SELECT version_id FROM mcq_versions WHERE content_key=? AND revision=?',(ck,revision)).fetchone()
                if not version: fail('manifest.contentRevisions.'+ck,'pinned version not imported')
                db.execute('INSERT INTO pilot_set_items VALUES (?,?,?,?)',(sk,pos,ck,version[0]))
            db.execute('INSERT INTO mcq_manifests VALUES (?,?,?)',(sk,mh,api.packed(manifest)))
        db.execute('INSERT OR IGNORE INTO mcq_packages VALUES (?,?,?,?,1)',(package['packageId'],digest(package),mh,digest(sources)))
        result={'qaOnly':True,'draftOptIn':bool(allow_draft_qa),'independentTeacherApproved':not info['draft'],
            'questionCount':len(normalized),'insertedVersions':inserted,'replayedVersions':len(normalized)-inserted,
            'packageHash':digest(package),'manifestHash':mh,'sourceRegistryHash':digest(sources),
            'difficultyMapping':{'provisional':True,'table':PROVISIONAL_DIFFICULTY},'setKey':sk}
        batch_id='qa-import-'+digest([digest(package),mh,digest(sources)])
        mapping=[{'contentKey':item['raw']['contentKey'],'revision':item['raw']['revision'],
                  'quotaKey':item['raw']['quotaKey'],'sourceContentKey':item['raw']['sourceContentKey'],
                  'sourceRevision':item['raw']['sourceRevision'],
                  'versionId':versions[item['raw']['contentKey'],item['raw']['revision']]} for item in normalized]
        result.update(batchId=batch_id,servingStatus='qa-trial',mapping=mapping)
        db.execute('INSERT OR IGNORE INTO mcq_import_batches VALUES (?,?,?,?,?,?,?)',
                   (batch_id,digest(package),mh,digest(sources),api.packed(mapping),api.packed(result),api.stamp()))
        return result
