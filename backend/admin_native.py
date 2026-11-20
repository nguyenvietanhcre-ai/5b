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

def item(db,key,bank):
    original=current(db,key);draft=db.execute('SELECT * FROM staff_knowledge_drafts WHERE lesson_key=?',(key,)).fetchone()
    payload=json.loads(draft['payload_json']) if draft else original
    from .lesson_resources import project_materials, video_preview, staff_bunny_video
    return {'lessonKey':key,'title':payload['title'],'topicKey':payload['topicKey'],'publishedRevision':original['revision'],
            'draftRevision':draft['revision'] if draft else 0,'baseRevision':draft['base_revision'] if draft else original['revision'],
            'archived':bool(draft['archived']) if draft else False,'sections':plain_sections(payload['sections']),
            'sectionTitles':[s['title'] for s in payload['sections']],
            'fixed':payload['fixed'],'solution':plain_sections(payload['fixed']['solution']),
            'videoRef':payload.get('videoRef',''),'videoPreview':video_preview(payload.get('videoRef','')),
            'bunnyVideo':staff_bunny_video(bank,payload,'native',key),
            'materials':project_materials(payload.get('materials',[]),'native',key,payload['revision'],admin=True)}

def list_items(handler,query,bank):
    p=provider(handler);q=query.get('q',[''])[0].casefold()[:160]
    with api.connect(p.path) as db:
        keys=[r[0] for r in db.execute('SELECT DISTINCT lesson_key FROM knowledge_lessons ORDER BY lesson_key')]
        rows=[]
        for key in keys:
            value=item(db,key,bank)
            if q not in (value['title']+' '+key).casefold():continue
            rows.append({k:value[k] for k in ('lessonKey','title','topicKey','publishedRevision','draftRevision','baseRevision','archived','bunnyVideo')})
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


def merge_fixed(original,body):
    """Edit one attached check without changing its identity, source or pinned media."""
    from .answers import requires_choice,validate_choices,validate_rule
    value={**original}
    if 'fixed' in body:
        incoming=body['fixed']
        if not isinstance(incoming,dict):raise api.APIError('Câu hỏi mẫu cần là một đối tượng.')
        editable={'prompt','responseMode','correctAnswer','answerKind','inputGuide','answerShape','answerTargets','options','choiceRationales'}
        for name,content in incoming.items():
            if name not in editable and (name not in original or content!=original[name]):raise api.APIError('Không được thay mã, nguồn hoặc thông tin ghim của câu hỏi.')
        value.update({name:content for name,content in incoming.items() if name in editable})
    if 'solution' in body:value['solution']=merge_texts(value['solution'],body['solution'])
    value['prompt']=text(value,'prompt',10000)
    value['correctAnswer']=text(value,'correctAnswer',500)
    if value.get('responseMode') not in ('typed','choice'):raise api.APIError('Chọn tự nhập hoặc trắc nghiệm cho câu hỏi mẫu.')
    if value.get('answerShape','scalar') not in ('scalar','single','parts','objects','solutions','complete-choice'):raise api.APIError('Cấu trúc đáp án không hợp lệ.')
    if 'inputGuide' in value:
        guide=value['inputGuide']
        if not isinstance(guide,dict) or set(guide)-{'instruction','labels','units','separator','placeholder'}:raise api.APIError('Hướng dẫn nhập đáp án không hợp lệ.')
        for name in ('instruction','separator','placeholder'):
            if name in guide and (not isinstance(guide[name],str) or len(guide[name])>(2000 if name=='instruction' else 160)):raise api.APIError('Hướng dẫn nhập đáp án quá dài hoặc không hợp lệ.')
        for name in ('labels','units'):
            if name in guide and (not isinstance(guide[name],list) or len(guide[name])>20 or any(not isinstance(v,str) or len(v)>60 for v in guide[name])):raise api.APIError('Nhãn hoặc đơn vị đáp án không hợp lệ.')
    targets=value.get('answerTargets')
    if targets is not None and (not isinstance(targets,list) or len(targets)>20 or any(not isinstance(v,str) or not v.strip() or len(v)>60 for v in targets)):raise api.APIError('Nhãn đáp án không hợp lệ.')
    try:
        if value['responseMode']=='typed':
            if requires_choice(value) or value.get('answerShape')=='complete-choice':raise ValueError('Câu có nhiều ý hoặc nhiều kết quả cần bốn phương án đầy đủ.')
            validate_rule(value['correctAnswer'],value.get('answerKind','number'))
        else:
            labels=value.get('inputGuide',{}).get('labels',[])
            validate_choices(value['correctAnswer'],value.get('options'),value.get('choiceRationales'),targets or (labels if len(labels)>1 else None))
    except ValueError as error:raise api.APIError(str(error)) from None
    return value

def save(handler,user,body,bank):
    if not isinstance(body,dict):raise api.APIError('Dữ liệu cần là một đối tượng JSON.')
    if set(body)-{'lessonKey','action','draftRevision','baseRevision','title','sections','videoRef','bunnyVideo','materials','fixed','solution'}:raise api.APIError('Trường biên tập không hợp lệ.')
    p=provider(handler);key=text(body,'lessonKey',120);action=body.get('action','draft')
    if action not in ('draft','publish','archive','restore'):raise api.APIError('Thao tác bài giảng không hợp lệ.')
    with api.connect(p.path,True) as db:
        original=current(db,key);old=db.execute('SELECT * FROM staff_knowledge_drafts WHERE lesson_key=?',(key,)).fetchone()
        rev=old['revision'] if old else 0
        if type(body.get('baseRevision')) is not int or type(body.get('draftRevision')) is not int or body['draftRevision']!=rev or body.get('baseRevision')!=original['revision']:raise api.APIError('Bài giảng vừa thay đổi. Tải lại trước khi lưu.',409)
        value=json.loads(old['payload_json']) if old else original
        archived=int(action=='archive') if action in ('archive','restore') else (old['archived'] if old else 0)
        if action in ('draft','publish'):
            if action=='publish' and archived:raise api.APIError('Khôi phục bài trước khi phát hành.')
            value={**value,'title':text(body,'title'),'sections':merge_texts(value['sections'],body.get('sections'))}
            from .lesson_resources import save_lesson_video,normalize_materials
            video=save_lesson_video(bank,handler.server,user,body,value,'native',key,'videoRef',
                                    value.get('videoRef',''),publishing=action=='publish')
            if 'videoRef' in value or 'videoRef' in body or 'bunnyVideo' in body:
                value['videoRef']=video
            if 'materials' in body:value['materials']=normalize_materials(db,body['materials'],'native',key)
            if 'fixed' in body or 'solution' in body:value['fixed']=merge_fixed(value['fixed'],body)
        if action=='publish':
            q=value['fixed'];old_q=original['fixed']
            changed={k:v for k,v in q.items() if k not in ('revision','lessonRevision')}!={k:v for k,v in old_q.items() if k not in ('revision','lessonRevision')}
            if changed:value['fixed']={**q,'revision':old_q['revision']+1,**({'lessonRevision':original['revision']+1} if 'lessonRevision' in q else {})}
            else:value['fixed']=old_q
            value={**value,'revision':original['revision']+1,'adminEdit':{'staffId':user['id'],'at':api.stamp(),'review':'admin-published'}}
            db.execute('INSERT INTO knowledge_lessons VALUES (?,?,?,?,?)',(key,value['revision'],value['topicKey'],digest(value),api.packed(value)))
            from .lesson_resources import bind_materials
            bind_materials(db,value.get('materials',[]),'native',key,value['revision'],5,True)
        db.execute('INSERT INTO staff_knowledge_drafts VALUES (?,?,?,?,?) ON CONFLICT(lesson_key) DO UPDATE SET base_revision=excluded.base_revision,revision=excluded.revision,payload_json=excluded.payload_json,archived=excluded.archived',
                   (key,value['revision'] if action=='publish' else original['revision'],rev+1,api.packed(value),archived))
        db.execute('INSERT INTO staff_native_events(staff_id,staff_name,lesson_key,action,lesson_revision,created_at) VALUES (?,?,?,?,?,?)',(user['id'],user['full_name'],key,action,value['revision'],api.stamp()))
        return {'saved':True,'item':item(db,key,bank)}

def dispatch(handler,user,method,path,body,query,bank):
    p=provider(handler)
    if path=='/api/staff/native-lessons':return (list_items(handler,query,bank) if method=='GET' else save(handler,user,body,bank)),200
    if path=='/api/staff/native-lessons/item' and method=='GET':
        with api.connect(p.path) as db:return {'item':item(db,query.get('key',[''])[0],bank)},200
    if path=='/api/staff/native-lessons/events' and method=='GET':
        with api.connect(p.path) as db:return {'rows':[dict(row) for row in db.execute('SELECT * FROM staff_native_events ORDER BY id DESC LIMIT 100')]},200
    raise api.APIError('API bài giảng không tồn tại.',404)
