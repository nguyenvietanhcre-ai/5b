"""Exact owned practice retakes; immutable previous grades, no allocation/debit."""
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote
import secrets
from . import platform_api as api

def exists(db,table):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone())

def root_id(db,eid):
    row=db.execute('SELECT root_exam_id FROM study_retakes WHERE exam_id=?',(eid,)).fetchone()
    return row[0] if row else eid

def versions_retakable(db,eid):
    from .free_vip_pilot import version_allowed
    rows=db.execute('SELECT v.id,v.status FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=?',(eid,)).fetchall()
    return bool(rows) and all(version_allowed(db,row['id'],row['status']) for row in rows)

def retake(db,session,eid,body):
    if type(eid) is not int or eid<1 or not isinstance(body,dict) or set(body)!={'requestKey'}:
        raise api.APIError('Yêu cầu làm lại đề không hợp lệ.')
    key=api.text_field(body,'requestKey',80,8);sid=session['student_id']
    source=api.owned_attempt(db,session,eid)
    owned=db.execute('SELECT * FROM exams WHERE id=? AND owner_student_id=? AND form_id IS NULL AND status=\'published\'',(eid,sid)).fetchone()
    if not owned or source['status']!='submitted':raise api.APIError('Chỉ làm lại đề riêng đã nộp và còn quyền xem.',403)
    prior=db.execute('SELECT * FROM study_retake_requests WHERE student_id=? AND request_key=?',(sid,key)).fetchone()
    if prior:
        if prior['requested_exam_id']!=eid:raise api.APIError('Mã yêu cầu đã dùng cho đề khác.',409)
        return {'exam':api.exam_view(db,api.owned_attempt(db,session,prior['exam_id'])),'rootExamId':str(root_id(db,eid))}
    root=root_id(db,eid)
    # A withdrawn root cannot be revived through one of its retakes.
    if not db.execute("SELECT 1 FROM exams WHERE id=? AND owner_student_id=? AND status='published' AND form_id IS NULL",(root,sid)).fetchone():
        raise api.APIError('Đề gốc không còn mở làm lại.',403)
    active=db.execute("SELECT a.exam_id,r.root_exam_id FROM exam_attempts a LEFT JOIN study_retakes r ON r.exam_id=a.exam_id WHERE a.student_id=? AND a.status='in_progress' AND a.due_at>? ORDER BY a.id DESC LIMIT 1",(sid,api.stamp())).fetchone()
    if active:
        if active['root_exam_id']!=root:raise api.APIError('Con còn bài đang làm. Hãy hoàn thành bài đó trước.',409)
        new_id=active['exam_id']
    else:
        if not versions_retakable(db,eid):raise api.APIError('Phiên bản đã ngừng mở lượt mới; kết quả cũ vẫn được giữ để xem lại.',409)
        duration=owned['duration_minutes']
        new_id=db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,academic_year_id,owner_student_id,mode,week_limit,created_at,response_mode) VALUES(?,?,?,?,'published',?,?,?,?,?,?)",
            ('RETAKE-'+secrets.token_hex(12),owned['title'],owned['grade_level'],duration,owned['academic_year_id'],sid,owned['mode'],owned['week_limit'],api.stamp(),owned['response_mode'])).lastrowid
        rows=db.execute('SELECT * FROM exam_items WHERE exam_id=? ORDER BY position',(eid,)).fetchall()
        if not rows:raise api.APIError('Đề đã lưu chưa có câu hỏi để làm lại.',409)
        for row in rows:
            db.execute('INSERT INTO exam_items(exam_id,position,question_version_id,max_points,options_json) VALUES(?,?,?,?,?)',
                (new_id,row['position'],row['question_version_id'],row['max_points'],row['options_json']))
        if exists(db,'practice_exam_items'):
            db.execute('INSERT INTO practice_exam_items SELECT ?,position,content_key,response_mode,topic_title FROM practice_exam_items WHERE exam_id=?',(new_id,eid))
        db.execute('INSERT INTO study_retakes VALUES(?,?,?,?,?)',(new_id,root,eid,sid,api.stamp()))
        db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES(?,?,?,?,'in_progress',?)",
            (new_id,sid,api.stamp(),api.stamp(api.now()+timedelta(minutes=duration)),'retake-'+secrets.token_hex(20)))
    db.execute('INSERT INTO study_retake_requests VALUES(?,?,?,?)',(sid,key,eid,new_id))
    return {'exam':api.exam_view(db,api.owned_attempt(db,session,new_id)),'rootExamId':str(root)}

def annotate(db,session,payload,provider):
    """Question codes match existing PDF/lookup, only for a submitted owned exam."""
    attempt=api.owned_attempt(db,session,int(payload['id']))
    payload.update(rootExamId=str(root_id(db,attempt['exam_id'])))
    payload['canRetake']=bool(db.execute("SELECT 1 FROM exams e JOIN exams r ON r.id=? WHERE e.id=? AND e.owner_student_id=? AND e.form_id IS NULL AND e.status='published' AND r.status='published'",(int(payload['rootExamId']),attempt['exam_id'],session['student_id'])).fetchone())
    payload['canRetake']=payload['canRetake'] and versions_retakable(db,attempt['exam_id'])
    if attempt['status']!='submitted':return payload
    if not db.execute('SELECT 1 FROM exams WHERE id=? AND owner_student_id=? AND form_id IS NULL',(attempt['exam_id'],session['student_id'])).fetchone():return payload
    from . import practice_export as exports
    exports.initialize(db)
    for row in db.execute('SELECT i.position,i.options_json,v.*,q.question_code,t.title topic_title FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id JOIN questions q ON q.id=v.question_id JOIN topics t ON t.id=q.topic_id WHERE i.exam_id=? ORDER BY i.position',(attempt['exam_id'],)).fetchall():
        data=exports.snapshot_item(db,attempt,row,provider,Path(__file__).resolve().parents[1]/'frontend')
        code,digest=exports.identity(data)
        prior=db.execute('SELECT payload_sha256 FROM practice_export_codes WHERE code=?',(code,)).fetchone()
        if prior and prior[0]!=digest:raise api.APIError('Mã câu đã lưu bị xung đột.',409)
        db.execute('INSERT OR IGNORE INTO practice_export_codes VALUES(?,?,?,?,?,?,?)',(code,provider,data['versionId'],data['revision'],digest,exports.packed(data),api.stamp()))
        db.execute('INSERT OR IGNORE INTO practice_export_rights VALUES(?,?,?,?)',(session['student_id'],code,attempt['exam_id'],api.stamp()))
        question=next((q for q in payload['questions'] if str(q['id'])==str(row['position'])),None)
        if question is not None:question['questionCode']=code
    return payload

def collapse(db,items,provider):
    if not exists(db,'study_retakes'):return items
    grouped={}
    for item in items:
        root=str(root_id(db,int(item['id'])));grouped.setdefault(root,[]).append(item)
    result=[]
    for root,rows in grouped.items():
        done=sorted((r for r in rows if r['submitted']),key=lambda r:(r.get('submittedAt') or '',int(r['id'])),reverse=True)
        active=sorted((r for r in rows if not r['submitted']),key=lambda r:(r['startedAt'],int(r['id'])),reverse=True)
        shown=dict(done[0] if done else active[0]);shown.update(reference=provider+':'+root,rootExamId=root)
        shown['canRetake']=bool(shown.get('canRetake') and db.execute("SELECT 1 FROM exams WHERE id=? AND status='published'",(int(root),)).fetchone())
        shown['canRetake']=shown['canRetake'] and versions_retakable(db,int(shown['id']))
        if active:shown['activeRetakeId']=active[0]['id']
        result.append(shown)
    return sorted(result,key=lambda r:(r['startedAt'],int(r['id'])),reverse=True)

def continuation(db,session,provider=None):
    from .practice_catalogue import history
    lessons=[];exams=[];sid=session['student_id'];grade=api.grade_for_student(db,sid,session['birth_year'])
    row=db.execute("SELECT l.client_key,l.title FROM learning_preferences p JOIN lessons l ON l.client_key=p.last_lesson WHERE p.student_id=? AND l.grade_id=? AND l.publication_status='published' AND NOT EXISTS(SELECT 1 FROM lesson_progress x WHERE x.student_id=p.student_id AND x.lesson_id=l.id)",(sid,grade)).fetchone()
    if row:lessons.append(('',{'kind':'lesson','provider':'main','lessonKey':row['client_key'],'title':row['title'],'href':'/bai-giang/?id='+quote(row['client_key'])}))
    exams.extend([item for item in history(db,sid,'main') if db.execute('SELECT 1 FROM exams WHERE id=? AND grade_level=?',(int(item['id']),grade)).fetchone()])
    if provider and grade==5:
        with api.connect(provider.path) as pilot:
            mapping=pilot.execute('SELECT pilot_student_id FROM local_principals WHERE main_student_id=?',(sid,)).fetchone()
            if mapping:
                psid=mapping[0];exams.extend(history(pilot,psid,'pilot'))
                if exists(pilot,'study_lesson_opens') and exists(pilot,'knowledge_lessons'):
                    for opened in pilot.execute('SELECT o.*,k.payload_json FROM study_lesson_opens o JOIN knowledge_lessons k ON k.lesson_key=o.lesson_key AND k.revision=o.lesson_revision WHERE o.student_id=? AND NOT EXISTS(SELECT 1 FROM knowledge_checks c WHERE c.student_id=o.student_id AND c.lesson_key=o.lesson_key AND c.lesson_revision=o.lesson_revision) ORDER BY o.opened_at DESC',(psid,)):
                        if exists(pilot,'study_knowledge_completions') and pilot.execute('SELECT 1 FROM study_knowledge_completions WHERE student_id=? AND lesson_key=? AND lesson_revision=?',(psid,opened['lesson_key'],opened['lesson_revision'])).fetchone():continue
                        if exists(pilot,'staff_knowledge_drafts') and pilot.execute('SELECT 1 FROM staff_knowledge_drafts WHERE lesson_key=? AND archived=1',(opened['lesson_key'],)).fetchone():continue
                        import json
                        value=json.loads(opened['payload_json'])
                        lessons.append((opened['opened_at'],{'kind':'lesson','provider':'pilot','lessonKey':opened['lesson_key'],'revision':opened['lesson_revision'],'title':value['title'],'href':'/bai-giang/?knowledgeLesson='+quote(opened['lesson_key'])+'&lessonRevision='+str(opened['lesson_revision'])}))
    if lessons:return max(lessons,key=lambda item:item[0])[1]
    candidates=[r for r in exams if r['submitted'] and r.get('score',10)<10 and r.get('canRetake',False)]
    if not candidates:return None
    item=max(candidates,key=lambda r:(r.get('submittedAt') or '',r['reference']))
    return {'kind':'retake','provider':item['provider'],'examId':item['id'],'rootExamId':item.get('rootExamId',item['id']),'title':item['title'],'score':item['score'],
            'href':'/ket-qua-thi/?'+('pilotExam=' if item['provider']=='pilot' else 'id=')+str(item['id'])}
