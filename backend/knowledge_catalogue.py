"""Separate immutable knowledge lessons and fixed self-checks: no wallet or XP hooks."""
import hashlib,json,re
from base64 import b64decode
from pathlib import Path
from . import platform_api as api
from .answers import matches,requires_choice,validate_choices,validate_rule
from .mcq_import import digest,require_qa,load_json

SCHEMA=[
 'CREATE TABLE IF NOT EXISTS knowledge_lessons(lesson_key TEXT NOT NULL,revision INTEGER NOT NULL,topic_key TEXT NOT NULL,payload_hash TEXT NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(lesson_key,revision))',
 'CREATE TABLE IF NOT EXISTS knowledge_assets(sha256 TEXT PRIMARY KEY,mime TEXT NOT NULL,payload BLOB NOT NULL)',
 'CREATE TABLE IF NOT EXISTS knowledge_checks(student_id INTEGER NOT NULL REFERENCES students(id),request_key TEXT NOT NULL,lesson_key TEXT NOT NULL,lesson_revision INTEGER NOT NULL,payload_hash TEXT NOT NULL,result_json TEXT NOT NULL,checked_at TEXT NOT NULL,PRIMARY KEY(student_id,request_key),FOREIGN KEY(lesson_key,lesson_revision) REFERENCES knowledge_lessons(lesson_key,revision))',
 'CREATE INDEX IF NOT EXISTS knowledge_progress ON knowledge_checks(student_id,lesson_key)'
]

def sections(value,assets):
    if not isinstance(value,list) or len(value)!=3:raise ValueError('Exactly three framed sections required')
    result=[]
    for section in value:
        if not isinstance(section,dict) or not isinstance(section.get('title'),str) or not section['title'] or not isinstance(section.get('blocks'),list) or not section['blocks']:raise ValueError('Invalid section')
        blocks=[]
        for b in section['blocks']:
            if not isinstance(b,dict):raise ValueError('Invalid block')
            if b.get('type')=='text' and isinstance(b.get('text'),str) and len(b['text'])<=20000:blocks.append({'type':'text','text':b['text']})
            elif b.get('type')=='media' and b.get('sha256') in assets and isinstance(b.get('alt'),str):blocks.append({'type':'media','sha256':b['sha256'],'alt':b['alt']})
            else:raise ValueError('Only safe text and SHA-pinned SVG blocks supported')
        result.append({'title':section['title'],'blocks':blocks})
    return result

def validate_bundle(provider,bundle):
    from .local_pilot import safe_svg
    if not isinstance(bundle,dict) or bundle.get('schemaVersion')!='knowledge-fixed-v1' or bundle.get('grade')!=5 or bundle.get('qaOnly') is not True:raise ValueError('Separate knowledge-fixed-v1 QA profile required')
    lessons=bundle.get('lessons');rawassets=bundle.get('assets',[])
    if not isinstance(lessons,list) or len(lessons)!=24 or not isinstance(rawassets,list):raise ValueError('Exactly24 knowledge lessons/fixed checks required')
    assets={}
    for a in rawassets:
        if not isinstance(a,dict) or a.get('mime')!='image/svg+xml':raise ValueError('Only safe SVG assets')
        data=safe_svg(b64decode(a['base64'],validate=True));sha=hashlib.sha256(data).hexdigest()
        if sha!=a.get('sha256') or sha in assets or sha in provider.assets:raise ValueError('Asset SHA mismatch/duplicate/reuse of practice worked solution')
        assets[sha]=data
    allowedtopics={x['proposedTopicKey'] for x in provider.practice.mapping.values()};keys=set();fixedkeys=set();normalized=[]
    for lesson in lessons:
        if not isinstance(lesson,dict):raise ValueError('Lesson object required')
        key=lesson.get('lessonKey');topic=lesson.get('topicKey');rev=lesson.get('revision');title=lesson.get('title');q=lesson.get('fixed')
        if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9._-]{8,120}',key) or key in keys or topic not in allowedtopics or type(rev) is not int or rev<1 or not isinstance(title,str) or not title:raise ValueError('Invalid lesson identity/topic/revision')
        if not isinstance(q,dict) or not isinstance(q.get('questionKey'),str) or q['questionKey'] in fixedkeys or q['questionKey'] in provider.practice.mapping or not re.fullmatch(r'[a-zA-Z0-9._-]{8,120}',q['questionKey']):raise ValueError('Fixed needs a new knowledge identity outside practice')
        if type(q.get('revision')) is not int or q['revision']<1 or not isinstance(q.get('prompt'),str) or not q['prompt'] or len(q['prompt'])>10000 or not isinstance(q.get('correctAnswer'),str):raise ValueError('Invalid fixed question')
        mode=q.get('responseMode')
        if mode not in ('typed','choice') or mode=='typed' and requires_choice(q):raise ValueError('Complex fixed must be complete choice')
        if mode=='choice':validate_choices(q['correctAnswer'],q.get('options'),q.get('choiceRationales'),q.get('answerTargets'))
        else:validate_rule(q['correctAnswer'],q.get('answerKind','number'))
        body=sections(lesson.get('sections'),assets);solution=sections(q.get('solution'),assets)
        # Store author metadata unchanged; serve only explicitly projected safe fields.
        value={**lesson,'sections':body,'fixed':{**q,'solution':solution}}
        normalized.append(value);keys.add(key);fixedkeys.add(q['questionKey'])
    if {x['topicKey'] for x in normalized}!=allowedtopics:raise ValueError('All12 approved topics required')
    return normalized,assets

class Knowledge:
    def __init__(self,provider,inputs):
        self.provider=provider;self.inputs=Path(inputs)
        with api.connect(provider.path,True) as db:
            require_qa(db)
            for sql in SCHEMA:db.execute(sql)
        manifest=self.inputs/'knowledge-manifest.json'
        if manifest.exists():
            m=load_json(manifest)
            if m.get('profile')!='knowledge-fixed-v1' or m.get('bundle')!='knowledge-bundle.json':raise ValueError('Knowledge manifest allowlist mismatch')
            data=(self.inputs/'knowledge-bundle.json').read_bytes()
            if hashlib.sha256(data).hexdigest()!=m.get('sha256'):raise ValueError('Knowledge bundle SHA mismatch')
            self.install(json.loads(data))

    def install(self,bundle):
        lessons,assets=validate_bundle(self.provider,bundle)
        with api.connect(self.provider.path,True) as db:
            require_qa(db)
            for lesson in lessons:
                old=db.execute('SELECT payload_hash FROM knowledge_lessons WHERE lesson_key=? AND revision=?',(lesson['lessonKey'],lesson['revision'])).fetchone()
                if old and old[0]!=digest(lesson):raise ValueError('Immutable knowledge lesson revision conflict')
                # One fixed source key belongs to one immutable knowledge lesson, never a paid practice identity.
                for row in db.execute('SELECT lesson_key,payload_json FROM knowledge_lessons'):
                    existing=json.loads(row['payload_json'])
                    if existing['fixed']['questionKey']==lesson['fixed']['questionKey'] and row['lesson_key']!=lesson['lessonKey']:raise ValueError('Fixed binding conflict')
                db.execute('INSERT OR IGNORE INTO knowledge_lessons VALUES (?,?,?,?,?)',(lesson['lessonKey'],lesson['revision'],lesson['topicKey'],digest(lesson),api.packed(lesson)))
            for sha,data in assets.items():db.execute('INSERT OR IGNORE INTO knowledge_assets VALUES (?,\'image/svg+xml\',?)',(sha,data))
        return {'lessons':len(lessons),'fixed':len(lessons),'assets':len(assets)}

    def current(self,db,key,revision=None):
        if revision is not None and (type(revision) is not int or revision<1):raise api.APIError('Phiên bản bài học không hợp lệ.')
        row=db.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND (? IS NULL OR revision=?) ORDER BY revision DESC LIMIT 1',(key,revision,revision)).fetchone()
        if not row:raise api.APIError('Bài kiến thức đang được chuẩn bị.',404)
        return json.loads(row[0])

    def progress(self,db,session,key,revision):
        rows=[json.loads(r[0]) for r in db.execute('SELECT result_json FROM knowledge_checks WHERE student_id=? AND lesson_key=? AND lesson_revision=?',(session['student_id'],key,revision))]
        return {'completed':bool(rows),'attemptCount':len(rows),'correctCount':sum(bool(r['correct']) for r in rows)}

    def catalogue(self,db,session):
        rows=db.execute('SELECT k.* FROM knowledge_lessons k WHERE k.revision=(SELECT max(v.revision) FROM knowledge_lessons v WHERE v.lesson_key=k.lesson_key) ORDER BY k.topic_key,k.lesson_key')
        result=[]
        for row in rows:
            hidden=db.execute('SELECT archived FROM staff_knowledge_drafts WHERE lesson_key=?',(row['lesson_key'],)).fetchone()
            if hidden and hidden[0]:continue
            value=json.loads(row['payload_json']);progress=self.progress(db,session,value['lessonKey'],value['revision'])
            result.append({'lessonKey':value['lessonKey'],'topicKey':value['topicKey'],'title':value['title'],'revision':value['revision'],'status':'ready','completed':progress['completed'],'progress':progress})
        return result

    def lesson(self,db,session,key,revision=None):
        value=self.current(db,key,revision);q=value['fixed'];fixed={k:q[k] for k in ('questionKey','revision','prompt','responseMode','inputGuide') if k in q}
        if q['responseMode']=='choice':fixed['options']=q['options']
        return {'lesson':{k:value[k] for k in ('lessonKey','topicKey','title','revision','sections')}|{'fixed':fixed},'progress':self.progress(db,session,key,value['revision'])}

    def check(self,db,session,key,body):
        if not isinstance(body,dict) or set(body)!={'requestKey','answer','lessonRevision'} or not isinstance(body.get('answer'),str) or len(body['answer'])>500:raise api.APIError('Đáp án tự kiểm tra không hợp lệ.')
        request=api.text_field(body,'requestKey',80,8);payload=digest({'lessonKey':key,'body':body})
        old=db.execute('SELECT * FROM knowledge_checks WHERE student_id=? AND request_key=?',(session['student_id'],request)).fetchone()
        if old:
            if old['payload_hash']!=payload:raise api.APIError('requestKey đã dùng với bài/đáp án khác.',409)
            result=json.loads(old['result_json']);progress=self.progress(db,session,key,old['lesson_revision']);return {**result,'progress':progress,'attemptCount':progress['attemptCount']}
        value=self.current(db,key,body['lessonRevision']);q=value['fixed'];answer=body['answer']
        if q['responseMode']=='choice' and answer!='' and answer not in q['options']:raise api.APIError('Chọn một phương án của câu.',400)
        correct=(answer==q['correctAnswer']) if q['responseMode']=='choice' else matches(answer,{'answer':q['correctAnswer'],'answerKind':q.get('answerKind','number')})
        result={'correct':bool(correct),'answer':answer,'expectedAnswer':q['correctAnswer'],'solution':q['solution'],'completed':True,'requestKey':request,'lessonRevision':value['revision']}
        db.execute('INSERT INTO knowledge_checks VALUES (?,?,?,?,?,?,?)',(session['student_id'],request,key,value['revision'],payload,api.packed(result),api.stamp()))
        progress=self.progress(db,session,key,value['revision'])
        return {**result,'progress':progress,'attemptCount':progress['attemptCount']}

    def asset(self,db,session,key,sha,revision):
        from .local_pilot import media_keys
        if revision is None:raise api.APIError('Cần phiên bản bài học cho tài sản.')
        value=self.current(db,key,revision);allowed=media_keys(value['sections'])
        if self.progress(db,session,key,value['revision'])['completed']:allowed|=media_keys(value['fixed']['solution'])
        if sha not in allowed:raise api.APIError('Hình không thuộc phần bài học em được mở.',404)
        row=db.execute('SELECT mime,payload FROM knowledge_assets WHERE sha256=?',(sha,)).fetchone()
        if not row:raise api.APIError('Chưa có hình của bài học.',404)
        return {'_local_binary':bytes(row['payload']),'mime':row['mime']}
