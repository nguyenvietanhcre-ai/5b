"""Owner-scoped vector/text drafts, separate from submitted answers and grading."""
import json,math,re
from pathlib import Path
from . import platform_api as api

MAX_BYTES=1048576
def initialize(db):
    """Pilot applies only this migration, never unrelated game schemas."""
    name='0026_account_scratchpads.sql'
    if not db.execute('SELECT 1 FROM schema_migrations WHERE name=?',(name,)).fetchone():
        from .database import execute_sql
        execute_sql(db,(Path(__file__).parent/'migrations'/name).read_text(encoding='utf-8'))
        db.execute('INSERT INTO schema_migrations(name) VALUES (?)',(name,))

def validate(note):
    if not isinstance(note,dict) or set(note)!={'version','open','text','color','strokes'} or note['version']!=1 or type(note['version']) is not int or type(note['open']) is not bool:
        raise api.APIError('Nháp không hợp lệ.')
    if not isinstance(note['text'],str) or len(note['text'])>20000 or not isinstance(note['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',note['color']):raise api.APIError('Văn bản hoặc màu nháp không hợp lệ.')
    if not isinstance(note['strokes'],list) or len(note['strokes'])>2048:raise api.APIError('Nháp có quá nhiều nét vẽ.')
    count=0
    for line in note['strokes']:
        if not isinstance(line,dict) or set(line)!={'color','points'} or not isinstance(line['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',line['color']) or not isinstance(line['points'],list) or not line['points']:raise api.APIError('Nét vẽ không hợp lệ.')
        count+=len(line['points'])
        if count>20000:raise api.APIError('Nháp có quá nhiều điểm vẽ.')
        for p in line['points']:
            if not isinstance(p,dict) or set(p)!={'x','y'} or any(type(p[k]) not in (int,float) or not math.isfinite(p[k]) or not 0<=p[k]<=1 for k in ('x','y')):raise api.APIError('Tọa độ nháp không hợp lệ.')
    packed=json.dumps(note,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    if len(packed.encode())>MAX_BYTES:raise api.APIError('Nháp vượt dung lượng lưu cho một câu.',413)
    return packed

def access(db,session,eid,method,body=None,query=None):
    attempt=api.owned_attempt(db,session,eid)
    if method not in ('GET','POST'):raise api.APIError('Phương thức không hợp lệ.',405)
    raw=(query or {}).get('position',[''])[0] if method=='GET' else body.get('position')
    if method=='GET':
        if not isinstance(raw,str) or not re.fullmatch('[1-9][0-9]{0,3}',raw):raise api.APIError('Câu hỏi không hợp lệ.')
        position=int(raw)
    else:
        position=raw
        if type(position) is not int or position<1:raise api.APIError('Câu hỏi không hợp lệ.')
    if not db.execute('SELECT 1 FROM exam_items WHERE exam_id=? AND position=?',(eid,position)).fetchone():raise api.APIError('Câu hỏi không thuộc bài làm.',404)
    sid=session['student_id'];row=db.execute('SELECT * FROM account_scratchpads WHERE student_id=? AND exam_id=? AND position=?',(sid,eid,position)).fetchone()
    def public(value):return {'position':position,'revision':value['revision'] if value else 0,'note':json.loads(value['note_json']) if value else None,'updatedAt':value['updated_at'] if value else None}
    if method=='GET':return {'scratch':public(row)}
    if set(body)!={'position','revision','requestKey','note'} or type(body['revision']) is not int or body['revision']<0 or not isinstance(body['requestKey'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',body['requestKey']):raise api.APIError('Yêu cầu lưu nháp không hợp lệ.')
    packed=validate(body['note'])
    if row and row['request_key']==body['requestKey']:
        if row['note_json']!=packed:raise api.APIError('Mã yêu cầu lưu nháp đã được dùng.',409)
        return {'scratch':public(row)}
    if body['revision']!=(row['revision'] if row else 0):return {'conflict':True,'scratch':public(row)}
    db.execute('INSERT INTO account_scratchpads VALUES (?,?,?,?,?,?,?) ON CONFLICT(student_id,exam_id,position) DO UPDATE SET revision=excluded.revision,note_json=excluded.note_json,request_key=excluded.request_key,updated_at=excluded.updated_at',
               (sid,eid,position,body['revision']+1,packed,body['requestKey'],api.stamp()))
    return {'scratch':public(db.execute('SELECT * FROM account_scratchpads WHERE student_id=? AND exam_id=? AND position=?',(sid,eid,position)).fetchone())}
