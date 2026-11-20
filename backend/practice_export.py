"""Explicit, owner-scoped printable practice exports and revision-pinned lookup.

No submission, grading, entitlement allocation, wallet or XP writes occur here.
PDF libraries are imported lazily by practice_pdf, so Workers can reject PDF
export before importing native-only dependencies.
"""
import base64,hashlib,json,re
from pathlib import Path
from . import platform_api as api

SCHEMA = [
 "CREATE TABLE IF NOT EXISTS practice_export_codes(code TEXT PRIMARY KEY,provider TEXT NOT NULL CHECK(provider IN ('main','pilot')),version_id INTEGER NOT NULL,revision INTEGER NOT NULL,payload_sha256 TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL)",
 "CREATE TABLE IF NOT EXISTS practice_export_rights(student_id INTEGER NOT NULL REFERENCES students(id),code TEXT NOT NULL REFERENCES practice_export_codes(code),exam_id INTEGER NOT NULL REFERENCES exams(id),created_at TEXT NOT NULL,PRIMARY KEY(student_id,code))"
]
CODE = re.compile(r'^5B-[MP]-[A-Z2-7]{4}-[A-Z2-7]{4}-[A-Z2-7]{4}$')

def normalize_code(code):
    if not isinstance(code,str):return ''
    value=re.sub(r'[\s-]','',code).upper()
    match=re.fullmatch(r'5B([MP])([A-Z2-7]{12})',value)
    return '5B-'+match[1]+'-'+'-'.join(match[2][i:i+4] for i in range(0,12,4)) if match else ''

def initialize(db):
    for sql in SCHEMA:db.execute(sql)

def packed(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def exists(db,table):return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone())

def media_keys(value):
    if isinstance(value,list):return set().union(*(media_keys(x) for x in value)) if value else set()
    if not isinstance(value,dict):return set()
    result={value['sha256']} if value.get('type')=='media' and isinstance(value.get('sha256'),str) else set()
    for v in value.values():result|=media_keys(v)
    return result

def legacy_refs(value):
    if isinstance(value,list):return set().union(*(legacy_refs(x) for x in value)) if value else set()
    if not isinstance(value,dict):return set()
    result=set()
    for name in ('assetId','asset_id'):
        if name in value:result.add('legacy:'+str(value[name]))
    if value.get('type') in ('image','svg'):
        for key in ('src','url'):
            if isinstance(value.get(key),str):result.add(value[key])
    for v in value.values():result|=legacy_refs(v)
    return result

def snapshot_item(db,attempt,row,provider,frontend):
    rule=json.loads(row['grading_rule_json']);prompt=json.loads(row['prompt_json']);steps=json.loads(row['solution_steps_json']);hints=json.loads(row['hints_json'])
    from .answers import response_mode
    pin=None
    if exists(db,'practice_exam_items'):pin=db.execute('SELECT * FROM practice_exam_items WHERE exam_id=? AND position=?',(attempt['exam_id'],row['position'])).fetchone()
    mode=pin['response_mode'] if pin else response_mode(rule,attempt['response_mode'])
    payload={'provider':provider,'versionId':row['id'],'revision':row['revision'],'questionKey':row['question_code'],'grade':attempt['grade_level'],'topicTitle':pin['topic_title'] if pin else row['topic_title'],'prompt':prompt,'text':api.blocks_text(prompt),'responseMode':mode,'options':json.loads(row['options_json']) if mode=='choice' else [],'answer':rule.get('answer',''),'steps':steps,'thinking':hints,'lesson':None,'assets':{}}
    if exists(db,'local_lesson_pins'):
        lesson=db.execute('SELECT v.payload_json FROM local_lesson_pins p JOIN local_lesson_versions v ON v.content_key=p.content_key AND v.revision=p.lesson_revision WHERE p.version_id=?',(row['id'],)).fetchone()
        if lesson:payload['lesson']=json.loads(lesson[0])
    from .curriculum_samples import export_lesson,export_asset
    if payload['lesson'] is None:payload['lesson']=export_lesson(db,row['id'])
    for sha in media_keys([prompt,steps,hints,payload['lesson']]):
        asset=db.execute('SELECT mime,payload FROM local_lesson_assets WHERE sha256=?',(sha,)).fetchone() if exists(db,'local_lesson_assets') else None
        if not asset:asset=export_asset(db,row['id'],sha)
        if not asset:raise api.APIError('Thiếu hình của đúng phiên bản câu hỏi; chưa thể tạo PDF đầy đủ.',503)
        payload['assets'][sha]={'mime':asset['mime'],'data':base64.b64encode(bytes(asset['payload'])).decode()}
    # Legacy media is read only from the allowlisted frontend tree, never URL fetched.
    for asset in db.execute('SELECT m.* FROM media_assets m JOIN question_assets a ON a.asset_id=m.id WHERE a.question_version_id=?',(row['id'],)):
        url=asset['url'];clean=url.lstrip('/')
        refs=legacy_refs([prompt,steps,hints]);key='legacy:'+str(asset['id'])
        if key not in refs and url not in refs:raise api.APIError('Hình cũ chưa có phân loại đề/lời giải rõ ràng; chưa thể tải an toàn.',503)
        if '://' in url or '?' in url or '\\' in url:raise api.APIError('Hình câu hỏi chưa hỗ trợ xuất cục bộ an toàn.',503)
        path=(Path(frontend)/clean).resolve()
        if not path.is_relative_to(Path(frontend).resolve()) or not path.is_file():raise api.APIError('Không tìm thấy hình câu hỏi để in.',503)
        payload['assets'][key]={'mime':asset['mime_type'],'data':base64.b64encode(path.read_bytes()).decode(),'alt':asset['alt_text'],'url':url}
    return payload

def identity(payload):
    value=dict(payload);value['options']=sorted(value['options'])
    digest=hashlib.sha256(packed(value).encode()).digest()
    short=base64.b32encode(digest[:8]).decode()[:12]
    return '5B-'+('P' if payload['provider']=='pilot' else 'M')+'-'+'-'.join(short[i:i+4] for i in range(0,12,4)),hashlib.sha256(packed(value).encode()).hexdigest()

def can_read(db,session,row):
    sid=session['student_id']
    if db.execute('SELECT 1 FROM practice_export_rights WHERE student_id=? AND code=?',(sid,row['code'])).fetchone():return True
    attempts=db.execute('SELECT DISTINCT a.exam_id FROM exam_items i JOIN exam_attempts a ON a.exam_id=i.exam_id JOIN exams e ON e.id=i.exam_id WHERE a.student_id=? AND i.question_version_id=? AND e.owner_student_id=? AND e.form_id IS NULL',(sid,row['version_id'],sid)).fetchall()
    if attempts:
        if row['provider']=='main':return True
        if any(exists(db,table) and db.execute('SELECT 1 FROM '+table+' WHERE student_id=? AND exam_id=?',(sid,attempt[0])).fetchone() for attempt in attempts for table in ['practice_requests','pilot_requests']):return True
    if exists(db,'pilot_grants') and db.execute('SELECT 1 FROM pilot_grants WHERE student_id=? AND version_id=?',(sid,row['version_id'])).fetchone():return True
    return False

def safe_question(payload,code,solutions=False):
    value={key:payload[key] for key in ['provider','revision','grade','topicTitle','text','prompt','responseMode','options']}
    # Assets that occur only in solutions must not leak through a default lookup.
    visible=media_keys(payload['prompt'])|legacy_refs(payload['prompt']);value['assets']={k:v for k,v in payload['assets'].items() if k in visible or v.get('url') in visible}
    value['code']=code
    if solutions:value.update(answer=payload['answer'],steps=payload['steps'],thinking=payload['thinking'],lesson=payload['lesson'],assets=payload['assets'])
    return value

def lookup(db,session,code,*,solutions=False):
    code=normalize_code(code)
    if not isinstance(code,str) or not CODE.fullmatch(code):raise api.APIError('Không tìm thấy mã câu hỏi.',404)
    if type(solutions) is not bool:raise api.APIError('Lựa chọn lời giải không hợp lệ.')
    row=db.execute('SELECT * FROM practice_export_codes WHERE code=?',(code,)).fetchone()
    if not row or not can_read(db,session,row):raise api.APIError('Không tìm thấy câu hỏi trong quyền đã nhận của tài khoản.',404)
    payload=json.loads(row['payload_json'])
    return {'question':safe_question(payload,code,solutions),'solutionsIncluded':solutions,'sourceLabel':'Đúng phiên bản của câu đã nhận; mã tra cứu không cấp quyền câu mới.'}

def export_pdf(db,session,body,*,provider,frontend):
    if not isinstance(body,dict) or set(body)-{'provider','attemptId','includeSolutions'}:raise api.APIError('Yêu cầu tải đề không hợp lệ.')
    if provider not in ('main','pilot') or body.get('provider')!=provider:raise api.APIError('Nguồn bài luyện tập không hợp lệ.')
    include=body.get('includeSolutions',False)
    if type(include) is not bool:raise api.APIError('Chọn có hoặc không lời giải bằng giá trị đúng/sai.')
    eid=body.get('attemptId')
    if type(eid) is int:valid=eid>0
    else:valid=isinstance(eid,str) and bool(re.fullmatch(r'[1-9][0-9]{0,12}',eid))
    if not valid:raise api.APIError('Mã bài luyện tập không hợp lệ.')
    attempt=api.owned_attempt(db,session,int(eid))
    source=db.execute('SELECT form_id,owner_student_id,mode FROM exams WHERE id=?',(attempt['exam_id'],)).fetchone()
    if not source or source['form_id'] is not None or source['owner_student_id']!=session['student_id']:
        raise api.APIError('Chỉ tải đề luyện tập tự tạo của tài khoản. Bài có cấu trúc thi hoặc bài cũ chưa đủ bằng chứng sở hữu vẫn xem theo lịch sử hiện có.',403)
    if provider=='pilot':
        practice=any(exists(db,table) and db.execute('SELECT 1 FROM '+table+' WHERE student_id=? AND exam_id=?',(session['student_id'],attempt['exam_id'])).fetchone() for table in ['practice_requests','pilot_requests'])
        if not practice:raise api.APIError('Bài này không phải đề luyện tập đã xuất cho tài khoản.',403)
    rows=db.execute('SELECT i.position,i.options_json,v.*,q.question_code,t.title topic_title FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id JOIN questions q ON q.id=v.question_id JOIN topics t ON t.id=q.topic_id WHERE i.exam_id=? ORDER BY i.position',(attempt['exam_id'],)).fetchall()
    if not rows:raise api.APIError('Bài luyện tập chưa có câu hỏi để in.',409)
    questions=[]
    for row in rows:
        payload=snapshot_item(db,attempt,row,provider,frontend);code,digest=identity(payload)
        questions.append({'code':code,'position':row['position'],'payload':payload,'digest':digest})
    questions.sort(key=lambda item: {'choice':0,'typed':1}.get(item['payload']['responseMode'],2))
    from .practice_pdf import render_pdf
    pdf=render_pdf({'title':attempt['title'],'examCode':attempt['exam_code'],'grade':attempt['grade_level'],'questions':questions},include_solutions=include,frontend=Path(frontend))
    # Mapping is additive and contains only existing immutable version snapshots.
    for item in questions:
        old=db.execute('SELECT payload_sha256 FROM practice_export_codes WHERE code=?',(item['code'],)).fetchone()
        if old and old[0]!=item['digest']:raise api.APIError('Mã câu hỏi xung đột; chưa thể tải đề.',409)
        db.execute('INSERT OR IGNORE INTO practice_export_codes VALUES (?,?,?,?,?,?,?)',(item['code'],provider,item['payload']['versionId'],item['payload']['revision'],item['digest'],packed(item['payload']),api.stamp()))
        db.execute('INSERT OR IGNORE INTO practice_export_rights VALUES (?,?,?,?)',(session['student_id'],item['code'],attempt['exam_id'],api.stamp()))
    filename='5BMath-'+re.sub(r'[^A-Za-z0-9_-]','-',attempt['exam_code'])+('-co-loi-giai' if include else '-de-in')+'.pdf'
    return {'mime':'application/pdf','filename':filename,'pdfBase64':base64.b64encode(pdf).decode(),'solutionsIncluded':include,'codes':[{'position':x['position'],'code':x['code'],'revision':x['payload']['revision']} for x in questions],'notice':'Tải và tra cứu không trừ lượt, ví hoặc kinh nghiệm. Mã chỉ dùng với quyền câu hỏi đã nhận.'}
