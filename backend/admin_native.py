"""Versioned editing of the actual native knowledge library. Original revisions never change."""
import json,secrets,hashlib
from . import platform_api as api
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
from .admin_catalogue import integer,text

def provider(handler):
    p=getattr(handler.server,'local_pilot',None)
    if not p or not p.knowledge:raise api.APIError('Thư viện lớp 5 chưa được cấu hình trên máy chủ này.',503)
    return p

def overview(handler):
    p=getattr(handler.server,'local_pilot',None)
    if not p or not p.knowledge:return {'available':False,'lessons':0,'drafts':0}
    with api.connect(p.path) as db:
        return {'available':True,'lessons':db.execute('SELECT count(DISTINCT lesson_key) FROM knowledge_lessons').fetchone()[0],
                'drafts':db.execute('SELECT count(*) FROM staff_knowledge_drafts').fetchone()[0]}

def plain_sections(sections):return ['\n\n'.join(b['text'] for b in s['blocks'] if b.get('type')=='text') for s in sections]

def current(db,key):
    row=db.execute('SELECT * FROM knowledge_lessons WHERE lesson_key=? ORDER BY revision DESC LIMIT 1',(key,)).fetchone()
    if not row:raise api.APIError('Không tìm thấy bài giảng.',404)
    return json.loads(row['payload_json'])

def item(db,key):
    original=current(db,key);draft=db.execute('SELECT * FROM staff_knowledge_drafts WHERE lesson_key=?',(key,)).fetchone()
    payload=json.loads(draft['payload_json']) if draft else original
    return {'lessonKey':key,'title':payload['title'],'topicKey':payload['topicKey'],'publishedRevision':original['revision'],
            'draftRevision':draft['revision'] if draft else 0,'baseRevision':draft['base_revision'] if draft else original['revision'],
            'archived':bool(draft['archived']) if draft else False,'sections':plain_sections(payload['sections']),
            'sectionTitles':[s['title'] for s in payload['sections']],
            'fixed':payload['fixed'],'solution':plain_sections(payload['fixed']['solution'])}

def list_items(handler,query):
    p=provider(handler);q=query.get('q',[''])[0].casefold()[:160]
    with api.connect(p.path) as db:
        keys=[r[0] for r in db.execute('SELECT DISTINCT lesson_key FROM knowledge_lessons ORDER BY lesson_key')]
        rows=[]
        for key in keys:
            value=item(db,key)
            if q not in (value['title']+' '+key).casefold():continue
            rows.append({k:value[k] for k in ('lessonKey','title','topicKey','publishedRevision','draftRevision','baseRevision','archived')})
        return {'rows':rows,'total':len(rows),'page':1,'pageSize':max(1,len(rows)),'native':True}

def merge_texts(original,strings):
    if not isinstance(strings,list) or len(strings)!=3 or any(not isinstance(v,str) or not v.strip() or len(v)>20000 for v in strings):raise api.APIError('Mỗi bài cần đủ ba phần nội dung, tối đa 20.000 ký tự/phần.')
    result=[]
    for section,value in zip(original,strings):
        if value.strip()=='\n\n'.join(b['text'] for b in section['blocks'] if b.get('type')=='text').strip():
            result.append(section);continue
        # Existing media stays SHA-pinned; only editable text is replaced.
        blocks=[];inserted=False
        for block in section['blocks']:
            if block.get('type')=='text':
                if not inserted:blocks.append({'type':'text','text':value.strip()});inserted=True
            else:blocks.append(block)
        if not inserted:blocks.insert(0,{'type':'text','text':value.strip()})
        result.append({**section,'blocks':blocks})
    return result

def save(handler,user,body):
    if not isinstance(body,dict):raise api.APIError('Dữ liệu cần là một đối tượng JSON.')
    if set(body)-{'lessonKey','action','draftRevision','baseRevision','title','sections'}:raise api.APIError('Trường biên tập không hợp lệ.')
    p=provider(handler);key=text(body,'lessonKey',120);action=body.get('action','draft')
    if action not in ('draft','publish','archive','restore'):raise api.APIError('Thao tác bài giảng không hợp lệ.')
    with api.connect(p.path,True) as db:
        original=current(db,key);old=db.execute('SELECT * FROM staff_knowledge_drafts WHERE lesson_key=?',(key,)).fetchone()
        rev=old['revision'] if old else 0
        if type(body.get('baseRevision')) is not int or type(body.get('draftRevision')) is not int or body['draftRevision']!=rev or body.get('baseRevision')!=original['revision']:raise api.APIError('Bài giảng vừa thay đổi. Tải lại trước khi lưu.',409)
        value=json.loads(old['payload_json']) if old else original
        if action in ('draft','publish'):
            value={**value,'title':text(body,'title'),'sections':merge_texts(value['sections'],body.get('sections'))}
            # Fixed questions/solutions retain their source and grading rules in this editor.
            # Math editing stays in the existing question workflow; do not silently rewrite checks.
        archived=int(action=='archive') if action in ('archive','restore') else (old['archived'] if old else 0)
        if action=='publish':
            if archived:raise api.APIError('Khôi phục bài trước khi phát hành.')
            value={**value,'revision':original['revision']+1,'adminEdit':{'staffId':user['id'],'at':api.stamp(),'review':'admin-published'}}
            db.execute('INSERT INTO knowledge_lessons VALUES (?,?,?,?,?)',(key,value['revision'],value['topicKey'],digest(value),api.packed(value)))
        db.execute('INSERT INTO staff_knowledge_drafts VALUES (?,?,?,?,?) ON CONFLICT(lesson_key) DO UPDATE SET base_revision=excluded.base_revision,revision=excluded.revision,payload_json=excluded.payload_json,archived=excluded.archived',
                   (key,value['revision'] if action=='publish' else original['revision'],rev+1,api.packed(value),archived))
        db.execute('INSERT INTO staff_native_events(staff_id,staff_name,lesson_key,action,lesson_revision,created_at) VALUES (?,?,?,?,?,?)',(user['id'],user['full_name'],key,action,value['revision'],api.stamp()))
        return {'saved':True,'item':item(db,key)}

def dispatch(handler,user,method,path,body,query):
    p=provider(handler)
    if path=='/api/staff/native-lessons':return (list_items(handler,query) if method=='GET' else save(handler,user,body)),200
    if path=='/api/staff/native-lessons/item' and method=='GET':
        with api.connect(p.path) as db:return {'item':item(db,query.get('key',[''])[0])},200
    if path=='/api/staff/native-lessons/events' and method=='GET':
        with api.connect(p.path) as db:return {'rows':[dict(row) for row in db.execute('SELECT * FROM staff_native_events ORDER BY id DESC LIMIT 100')]},200
    raise api.APIError('API bài giảng không tồn tại.',404)
