"""Explicit QA-only60MCQ/typedsubset adapter. Legacy validate10 remains unchanged."""
from collections import Counter
from contextlib import closing
from datetime import datetime,timedelta
from pathlib import Path
import json,sqlite3
from . import platform_api as api
from .mcq_import import (SCHEMA_VERSION,TABLES,scan,key,integer,review,source_registry,normalize_question,digest,fail,require_qa,store_versions)
PROFILE='g5-pilot60-v1'
SCHEMA=[
 'CREATE TABLE IF NOT EXISTS qa_content_batches(set_key TEXT PRIMARY KEY,mode TEXT NOT NULL,parent_set_key TEXT,manifest_hash TEXT NOT NULL,package_hash TEXT NOT NULL,source_hash TEXT NOT NULL,metadata_json TEXT NOT NULL,result_json TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS qa_batch_versions(set_key TEXT NOT NULL REFERENCES qa_content_batches(set_key),content_key TEXT NOT NULL,version_id INTEGER NOT NULL REFERENCES question_versions(id),mode TEXT NOT NULL,PRIMARY KEY(set_key,content_key))'
]

def validate_batch(package,manifest,sources,*,allow_batch_qa=False,allow_draft_qa=False):
    if allow_batch_qa is not True:fail('batch','explicit allow_batch_qa=True required; legacy10 default unchanged')
    scan(package);scan(manifest)
    if not isinstance(package,dict) or package.get('schemaVersion')!=SCHEMA_VERSION or package.get('qaOnly') is not True:fail('package','mcq-draft-v1 QA envelope required')
    if not isinstance(manifest,dict) or manifest.get('qaOnly') is not True or manifest.get('batchProfile')!=PROFILE:fail('manifest','explicit QA60profile required')
    mode=manifest.get('responseMode');schema={'choice':'mcq-batch-qa-v1','typed':'typed-subset-qa-v1'}
    if mode not in schema or manifest.get('schemaVersion')!=schema[mode]:fail('manifest.mode','mode/schema mismatch')
    key(package.get('packageId'),'package.packageId');key(manifest.get('setKey'),'manifest.setKey')
    if type(manifest.get('grade')) is not int or manifest['grade']!=5:fail('grade','only grade5')
    if manifest.get('timeZone')!='Asia/Saigon' or manifest.get('windowEndExclusive') is not True:fail('window','VN/exclusive required')
    try:
        start=datetime.fromisoformat(manifest['windowStart']);end=datetime.fromisoformat(manifest['windowEnd'])
        valid=start.utcoffset()==end.utcoffset()==timedelta(hours=7) and start.weekday()==0 and start.time().isoformat()=='00:00:00' and end-start==timedelta(days=7)
    except (ValueError,TypeError,KeyError):valid=False
    if not valid:fail('window','Monday midnight+07 seven days required')
    questions=package.get('questions')
    if not isinstance(questions,list) or (mode=='choice' and len(questions)!=60) or (mode=='typed' and not 1<=len(questions)<=60):fail('questions','choice60 / typedsubset1..60 required')
    registry=source_registry(sources);normalized=[];seen=set();draft=review(manifest.get('reviewStatus'),'manifest.reviewStatus',allow_draft_qa)
    for q in questions:
        item,trial=normalize_question(q,registry,allow_draft_qa);ck=q['contentKey'];draft=draft or trial
        if q['grade']!=5:fail(ck,'batch only grade5')
        if ck in seen:fail(ck,'duplicate identity')
        if q['contentKey']!=q['quotaKey'] or q['lineageRelationship']!='equivalent':fail(ck,'batch keeps existing same identity/quota, no replacement')
        if q['responseType']!=('single-choice' if mode=='choice' else 'short-answer'):fail(ck,'mixed representation not allowed')
        if mode=='typed' and q.get('answerKind') not in ('number','ordered','unordered'):fail(ck,'only exact numeric/list typed kinds')
        normalized.append(item);seen.add(ck)
    revisions=manifest.get('contentRevisions')
    if not isinstance(revisions,dict) or set(revisions)!=seen:fail('pins','pin every and only imported identity')
    for item in normalized:
        ck=item['raw']['contentKey'];integer(revisions[ck],'pin.'+ck)
        if revisions[ck]!=item['raw']['revision']:fail(ck,'manifest pin must match package revision')
    sets=[]
    if mode=='choice':
        free=manifest.get('orderedContentKeys');vip=manifest.get('vipSupplementContentKeys');sets=manifest.get('freeSets')
        if not isinstance(free,list) or not isinstance(vip,list) or len(free)!=30 or len(vip)!=30 or any(not isinstance(k,str) for k in free+vip) or len(set(free+vip))!=60 or set(free+vip)!=seen:fail('keys','30Free+30VIP exact partition required')
        bykey={i['raw']['contentKey']:i['raw'] for i in normalized}
        if any(bykey[k]['proposedAccess']!=('Free' if k in free else 'VIP') for k in seen):fail('access','manifest/package mismatch')
        if not isinstance(sets,list) or len(sets)!=3:fail('sets','three10question Free sets required')
        flat=[];setkeys=[]
        for slot,item in enumerate(sets,1):
            if not isinstance(item,dict) or set(item)!={'slot','setKey','contentKeys'} or type(item['slot']) is not int or item['slot']!=slot:fail('sets','ordered slots1,2,3')
            setkeys.append(key(item['setKey'],'sets.setKey'));keys=item['contentKeys']
            if not isinstance(keys,list) or len(keys)!=10 or any(not isinstance(k,str) for k in keys):fail('sets','each set10keys')
            flat+=keys
        if flat!=free or len(set(setkeys))!=3 or manifest['setKey'] in setkeys:fail('sets','exact flat30 order and unique set keys required')
    else:
        parent=key(manifest.get('parentSetKey'),'parentSetKey')
        eligible=manifest.get('eligibleContentKeys')
        if not isinstance(eligible,list) or any(not isinstance(k,str) for k in eligible) or len(set(eligible))!=len(eligible) or set(eligible)!=seen:fail('eligible','must partition exactly typedsubset')
        if 'freeSets' in manifest:fail('typed','typedsubset does not allocate conflicting Free slots')
    return normalized,{'mode':mode,'draft':draft,'start':start.date().isoformat(),'end':end.date().isoformat(),'sets':sets}

def require_database(path):
    if type(path).__module__ == 'learning_storage' and type(path).__name__ == 'LearningDatabase':
        with api.connect(path) as db:require_qa(db)
        return path
    target=Path(path).resolve()
    if not target.is_file():fail('database','existing marked QA DB required')
    with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as db:require_qa(db)
    return target

def import_batch(path,package,manifest,sources,*,allow_batch_qa=False,allow_draft_qa=False):
    normalized,info=validate_batch(package,manifest,sources,allow_batch_qa=allow_batch_qa,allow_draft_qa=allow_draft_qa);target=require_database(path)
    with api.connect(target,True) as db:
        require_qa(db)
        for sql in TABLES+SCHEMA:db.execute(sql)
        mh,ph,sh=digest(manifest),digest(package),digest(sources);sk=manifest['setKey'];mode=info['mode']
        existing=db.execute('SELECT * FROM qa_content_batches WHERE set_key=?',(sk,)).fetchone()
        if existing and (existing['manifest_hash'],existing['package_hash'],existing['source_hash'])!=(mh,ph,sh):fail('batch','immutable batch payload/manifest/source conflict')
        if mode=='typed':
            parent=db.execute("SELECT * FROM qa_content_batches WHERE set_key=? AND mode='choice'",(manifest['parentSetKey'],)).fetchone()
            if not parent:fail('parent','import MCQ60 batch first')
            if db.execute("SELECT 1 FROM qa_content_batches WHERE mode='typed' AND parent_set_key=? AND set_key!=?",(manifest['parentSetKey'],sk)).fetchone():fail('typed','one immutable typed subset per parent')
            pm=json.loads(parent['metadata_json'])
            if any(manifest[k]!=pm[k] for k in ('windowStart','windowEnd','grade')):fail('typed.window','must match parent')
            parentkeys=set(pm['orderedContentKeys']+pm['vipSupplementContentKeys'])
            if not set(manifest['eligibleContentKeys'])<=parentkeys:fail('typed.keys','outside parent60')
        inserted,versions=store_versions(db,normalized)
        if not existing:
            if mode=='choice':
                for free in info['sets']:
                    if db.execute('SELECT 1 FROM pilot_sets WHERE set_key=? OR (grade=5 AND window_start=? AND slot=?)',(free['setKey'],info['start'],free['slot'])).fetchone():fail('sets','immutable window/slot conflict')
                    db.execute('INSERT INTO pilot_sets VALUES (?,5,?,?,?,1)',(free['setKey'],info['start'],info['end'],free['slot']))
                    for pos,ck in enumerate(free['contentKeys'],1):db.execute('INSERT INTO pilot_set_items VALUES (?,?,?,?)',(free['setKey'],pos,ck,versions[ck,manifest['contentRevisions'][ck]]))
            result={'qaOnly':True,'batchSetKey':sk,'mode':mode,'questionCount':len(normalized),'insertedVersions':inserted,'replayedVersions':len(normalized)-inserted,'packageHash':ph,'manifestHash':mh,'sourceRegistryHash':sh,'independentTeacherApproved':False,'servingStatus':'qa-trial','mapping':[{'contentKey':i['raw']['contentKey'],'quotaKey':i['raw']['quotaKey'],'revision':i['raw']['revision'],'versionId':versions[i['raw']['contentKey'],i['raw']['revision']]} for i in normalized]}
            db.execute('INSERT INTO qa_content_batches VALUES (?,?,?,?,?,?,?,?)',(sk,mode,manifest.get('parentSetKey'),mh,ph,sh,api.packed(manifest),api.packed(result)))
            for item in normalized:
                q=item['raw'];ck=q['contentKey'];db.execute('INSERT INTO qa_batch_versions VALUES (?,?,?,?)',(sk,ck,versions[ck,q['revision']],mode))
        else:result={**json.loads(existing['result_json']),'insertedVersions':0,'replayedVersions':len(normalized)}
        return result

def preview_batch(path,package,manifest,sources,*,allow_batch_qa=False,allow_draft_qa=False):
    target=require_database(path)
    try:validate_batch(package,manifest,sources,allow_batch_qa=allow_batch_qa,allow_draft_qa=allow_draft_qa)
    except ValueError as error:return {'qaOnly':True,'mode':'preview','importable':False,'databaseChanged':False,'errors':[str(error)]}
    # Reuse commit validation against an independent disposable QA SQLite snapshot; original is read-only.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='batch-preview-',dir=target.parent) as folder:
        probe=Path(folder)/'preview.sqlite3'
        with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as original,closing(sqlite3.connect(probe)) as dest:original.backup(dest)
        try:result=import_batch(probe,package,manifest,sources,allow_batch_qa=True,allow_draft_qa=allow_draft_qa)
        except (ValueError,sqlite3.Error) as error:return {'qaOnly':True,'mode':'preview','importable':False,'databaseChanged':False,'errors':[str(error)]}
    return {'qaOnly':True,'mode':'preview','importable':True,'databaseChanged':False,'errors':[],'result':result}
