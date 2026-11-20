"""Opt-in QA policy. No migrations, fixtures or activation on ordinary startup."""
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import secrets

from . import platform_api as api
from .learning_update import membership


@dataclass(frozen=True)
class PilotConfig:
    grade: int = 5
    free_sets: int = 3
    set_size: int = 10
    daily_new: int = 100
    wallet: bool = False
    vip_daily: int = 30
    vip_cycle: int = 300
    response_mode: str = 'choice'
    batch_set_key: str = ''
    internal_unlimited: bool = False
    vip_cycle_start: str = ''
    vip_cycle_end: str = ''


SCHEMA = """
CREATE TABLE pilot_environment (id INTEGER PRIMARY KEY CHECK(id=1), label TEXT NOT NULL);
INSERT INTO pilot_environment VALUES(1,'synthetic-only-v1');
CREATE TABLE pilot_cohorts (account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
 mode TEXT NOT NULL CHECK(mode IN ('pilot','legacy')));
CREATE TABLE pilot_content (content_key TEXT PRIMARY KEY, question_id INTEGER NOT NULL UNIQUE REFERENCES questions(id),
 proposed_access TEXT NOT NULL CHECK(proposed_access IN ('free','vip')));
CREATE TABLE pilot_sets (set_key TEXT PRIMARY KEY, grade INTEGER NOT NULL, window_start TEXT NOT NULL,
 window_end TEXT NOT NULL, slot INTEGER NOT NULL, revision INTEGER NOT NULL,
 UNIQUE(grade,window_start,slot));
CREATE TABLE pilot_set_items (set_key TEXT NOT NULL REFERENCES pilot_sets(set_key), position INTEGER NOT NULL,
 content_key TEXT NOT NULL REFERENCES pilot_content(content_key), version_id INTEGER NOT NULL REFERENCES question_versions(id),
 PRIMARY KEY(set_key,position), UNIQUE(set_key,content_key));
CREATE TABLE pilot_grants (student_id INTEGER NOT NULL REFERENCES students(id),
 content_key TEXT NOT NULL REFERENCES pilot_content(content_key), version_id INTEGER NOT NULL REFERENCES question_versions(id),
 first_granted_at TEXT NOT NULL, local_day TEXT NOT NULL, quota_charged INTEGER NOT NULL CHECK(quota_charged IN (0,1)),
 PRIMARY KEY(student_id,content_key));
CREATE INDEX pilot_grants_day ON pilot_grants(student_id,local_day,quota_charged);
CREATE TABLE pilot_requests (student_id INTEGER NOT NULL REFERENCES students(id), request_key TEXT NOT NULL,
 payload_hash TEXT NOT NULL, exam_id INTEGER NOT NULL REFERENCES exams(id), PRIMARY KEY(student_id,request_key));
"""


def clock_window():
    local = api.now().astimezone(api.VN)
    monday = local.date() - timedelta(days=local.weekday())
    return local.date().isoformat(), monday.isoformat(), (monday + timedelta(days=7)).isoformat()


def active(handler, db, session):
    config = getattr(handler.server, 'free_vip_pilot', None)  # absent/off by default
    if not isinstance(config, PilotConfig):
        return None
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_environment'").fetchone():
        raise api.APIError('Pilot requires an isolated synthetic QA database.', 503)
    if db.execute('SELECT label FROM pilot_environment WHERE id=1').fetchone()[0] != 'synthetic-only-v1':
        raise api.APIError('Invalid QA environment.', 503)
    grade = api.grade_for_student(db, session['student_id'], session['birth_year'])
    if grade != config.grade or membership(db, session) == 'SVip':
        return None
    cohort = db.execute('SELECT mode FROM pilot_cohorts WHERE account_id=?', (session['account_id'],)).fetchone()
    return None if cohort and cohort[0] == 'legacy' else config


def guard(handler, db, session, path):
    config = active(handler, db, session)
    if config and (path.startswith('/api/v1/lessons/') or path in (
            '/api/v1/bot/start', '/api/v1/arena', '/api/v1/materials', '/api/v1/dev/upgrade')):
        raise api.APIError('Đường nội dung này chưa hỗ trợ pilot; đã khóa trên QA.', 403)
    return config


def snapshot(handler, db, session, payload):
    if active(handler, db, session):
        payload['lessons'] = []
        payload.get('state', {})['battles'] = {}
        payload['pilot'] = {'enabled': True, 'apiOnly': True, 'unsupported': ['lessons','bot','arena','materials']}
    return payload


def metadata(db, session, config):
    if config.wallet:
        from .wallet_qa import balance
        return balance(db,session,config)
    day, start, end = clock_window()
    sets = [dict(row) for row in db.execute('SELECT set_key,slot,revision FROM pilot_sets '
            'WHERE grade=? AND window_start=? AND window_end=? ORDER BY slot', (config.grade,start,end))]
    used = db.execute('SELECT count(*) FROM pilot_grants WHERE student_id=? AND local_day=? AND quota_charged=1',
                      (session['student_id'],day)).fetchone()[0]
    keys = []
    if membership(db,session) in ('VIP','VIP+'):
        keys = [row[0] for row in db.execute('SELECT content_key FROM pilot_content ORDER BY content_key')]
    return {'pilot': True, 'grade':config.grade, 'day':day, 'windowStart':start, 'windowEnd':end,
            'timezone':'Asia/Saigon', 'sets':sets, 'contentKeys':keys, 'newUsed':used, 'newLimit':config.daily_new}


def version_allowed(db, version_id, status):
    if status == 'published': return True
    if status == 'draft':
        from .curriculum_samples import registered
        sample=registered(db,version_id)
        if sample is not None:return bool(sample)
    if status != 'draft' or not db.execute("SELECT 1 FROM sqlite_master WHERE name='mcq_versions'").fetchone():
        return False
    row=db.execute('SELECT metadata_json FROM mcq_versions WHERE version_id=?',(version_id,)).fetchone()
    return bool(row and json.loads(row[0]).get('servingStatus')=='qa-trial')


def create_exam(db, session, body, config, *, quote_only=False):
    # The caller holds BEGIN IMMEDIATE: selection, quota, grants and attempt commit together.
    key = api.text_field(body,'requestKey',80,8)
    selectors={'setIndex','contentKeys','replayExamId'}
    allowed={'requestKey'}|selectors|({'responseMode'} if config.batch_set_key else set())|({'quoteId','confirmWallet'} if config.wallet else set())
    if set(body) - allowed or sum(k in body for k in selectors) != 1:
        raise api.APIError('Chọn một setIndex, contentKeys hoặc replayExamId; không tự chọn khối/tuần.')
    digest = hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    old = db.execute('SELECT * FROM pilot_requests WHERE student_id=? AND request_key=?',
                     (session['student_id'],key)).fetchone()
    if old:
        if old['payload_hash'] != digest:
            raise api.APIError('requestKey đã dùng với nội dung khác.',409)
        return api.exam_view(db,api.owned_attempt(db,session,old['exam_id']))
    if db.execute('SELECT 1 FROM exam_attempts WHERE student_id=? AND request_key=?',
                  (session['student_id'],key)).fetchone():
        raise api.APIError('requestKey đã dùng trước pilot.',409)
    if db.execute('SELECT count(*) FROM exam_attempts WHERE student_id=? AND started_at>?',
                  (session['student_id'],api.stamp(api.now()-timedelta(hours=1)))).fetchone()[0] >= 60:
        raise api.APIError('Em đã tạo nhiều đề. Hãy tiếp tục bài đang làm trước.',429)
    day, start, end = clock_window()
    paid = membership(db,session) in ('VIP','VIP+')
    selected = []
    response_mode=body.get('responseMode',config.response_mode)
    if response_mode not in ('choice','typed'):raise api.APIError('Chế độ trả lời không hợp lệ.')
    if response_mode not in ('choice','typed'):raise api.APIError('Invalid server response mode.',503)
    if 'replayExamId' in body:
        if type(body['replayExamId']) is not int:
            raise api.APIError('Mã bài làm không hợp lệ.')
        owned = api.owned_attempt(db,session,body['replayExamId'])
        response_mode=owned['response_mode']
        if 'responseMode' in body and body['responseMode']!=response_mode:raise api.APIError('Làm lại giữ đúng chế độ bài gốc.',409)
        # Only pilot attempts have contentKey mapping. Legacy history still opens normally.
        if not db.execute('SELECT 1 FROM pilot_requests WHERE exam_id=?', (owned['exam_id'],)).fetchone():
            raise api.APIError('Bài cũ chưa được mapping pilot; vẫn có thể xem/nộp bằng ID.',409)
        selected = db.execute('SELECT c.content_key,i.question_version_id version_id FROM exam_items i '
            'JOIN question_versions v ON v.id=i.question_version_id JOIN pilot_content c ON c.question_id=v.question_id '
            'WHERE i.exam_id=? ORDER BY i.position', (owned['exam_id'],)).fetchall()
    elif 'setIndex' in body:
        if config.batch_set_key and response_mode!='choice':raise api.APIError('Bộ tự nhập dùng danh sách câu đủ điều kiện riêng.')
        slot = body['setIndex']
        if type(slot) is not int or not 1 <= slot <= config.free_sets:
            raise api.APIError('Bộ mẫu không hợp lệ.')
        selected = db.execute('SELECT i.content_key,i.version_id FROM pilot_sets s JOIN pilot_set_items i ON i.set_key=s.set_key '
            'WHERE s.grade=? AND s.window_start=? AND s.window_end=? AND s.slot=? ORDER BY i.position',
            (config.grade,start,end,slot)).fetchall()
        if config.batch_set_key:
            parent=db.execute("SELECT metadata_json FROM qa_content_batches WHERE set_key=? AND mode='choice'",(config.batch_set_key,)).fetchone()
            pins=json.loads(parent[0]) if parent else {}
            free=next((v for v in pins.get('freeSets',[]) if v['slot']==slot),None)
            if not free or pins.get('windowStart','')[:10]!=start or pins.get('windowEnd','')[:10]!=end:
                raise api.APIError('Bộ QA đã ghim không thuộc tuần hiện hành.',503)
            selected=db.execute('SELECT content_key,version_id FROM pilot_set_items WHERE set_key=? ORDER BY position',(free['setKey'],)).fetchall()
        if len(selected) != config.set_size:
            raise api.APIError('Chưa có bộ mẫu đã ghim cho tuần này.',503)
    else:
        if not paid and not config.wallet:
            raise api.APIError('Free chỉ nhận bộ mẫu chung của tuần.',403)
        keys = body['contentKeys']
        if (not isinstance(keys,list) or not 1 <= len(keys) <= config.set_size or
                any(not isinstance(k,str) or len(k)>120 for k in keys) or len(set(keys)) != len(keys)):
            raise api.APIError('Danh sách contentKey không hợp lệ.')
        for content_key in keys:
            if config.batch_set_key:
                matches=db.execute('SELECT v.content_key,v.version_id FROM qa_batch_versions v JOIN qa_content_batches b ON b.set_key=v.set_key '
                    "WHERE v.content_key=? AND v.mode=? AND ((b.mode='choice' AND b.set_key=?) OR (b.mode='typed' AND b.parent_set_key=?))",
                    (content_key,response_mode,config.batch_set_key,config.batch_set_key)).fetchall()
                if len(matches)>1:raise api.APIError('Mapping mode QA không duy nhất.',503)
                row=matches[0] if matches else None
            else:
                row = db.execute('SELECT c.content_key,v.id version_id FROM pilot_content c JOIN questions q ON q.id=c.question_id '
                    "JOIN question_versions v ON v.question_id=q.id AND v.status IN ('published','draft') WHERE c.content_key=? AND q.grade_id=? "
                    'ORDER BY v.revision DESC LIMIT 1', (content_key,config.grade)).fetchone()
            if not row:
                raise api.APIError('Nội dung không thuộc kho pilot đã duyệt.',404)
            selected.append(row)
    if not selected:
        raise api.APIError('Chưa có nội dung được phép.',503)
    if 'replayExamId' in body and db.execute("SELECT 1 FROM sqlite_master WHERE name='practice_exam_items'").fetchone():
        pins={r['position']:dict(r) for r in db.execute('SELECT * FROM practice_exam_items WHERE exam_id=?',(body['replayExamId'],))}
        if pins:
            if len(pins)!=len(selected):raise api.APIError('Pin bài hỗn hợp cũ chưa đủ.',503)
            selected=[{**dict(row),'itemMode':pins[pos]['response_mode'],'topicTitle':pins[pos]['topic_title']} for pos,row in enumerate(selected,1)]
    for row in selected:
        version = db.execute('SELECT q.grade_id,v.status,c.proposed_access FROM question_versions v '
            'JOIN questions q ON q.id=v.question_id JOIN pilot_content c ON c.question_id=q.id '
            'WHERE v.id=? AND c.content_key=?', (row['version_id'],row['content_key'])).fetchone()
        if (not version or version['grade_id'] != config.grade or
                'replayExamId' not in body and (not version_allowed(db,row['version_id'],version['status']) or
                 'setIndex' in body and version['proposed_access'] != 'free')):
            raise api.APIError('Mapping bộ mẫu chưa hợp lệ hoặc nội dung đã ngừng cấp.',503)
        if db.execute('SELECT 1 FROM question_assets WHERE question_version_id=?',(row['version_id'],)).fetchone():
            raise api.APIError('Media riêng chưa hỗ trợ trên pilot QA.',503)
    # MCQ importer validates immutable lineage. Resolve its server-side quotaKey,
    # never a field from the request. Round1 fixtures retain their contentKey identity.
    for selected_row in selected:
        version=db.execute('SELECT options_json FROM question_versions WHERE id=?',(selected_row['version_id'],)).fetchone()
        item_mode=selected_row.get('itemMode',response_mode) if isinstance(selected_row,dict) else response_mode
        if (item_mode=='choice') != bool(json.loads(version['options_json'])):
            raise api.APIError('Phiên bản câu không phù hợp chế độ làm bài.',409)
    has_mcq = db.execute("SELECT 1 FROM sqlite_master WHERE name='mcq_versions'").fetchone()
    grants = {}
    for row in selected:
        quota_key = row['content_key']
        if has_mcq:
            mapping = db.execute('SELECT quota_key FROM mcq_versions WHERE version_id=?', (row['version_id'],)).fetchone()
            if mapping:
                quota_key = mapping[0]
                if quota_key != row['content_key']:
                    raise api.APIError('Invalid server-side MCQ quota lineage.',503)
        grants.setdefault(quota_key,row)
    fresh = [(quota_key,row) for quota_key,row in grants.items() if not db.execute(
        'SELECT 1 FROM pilot_grants WHERE student_id=? AND content_key=?', (session['student_id'],quota_key)).fetchone()]
    used = db.execute('SELECT count(*) FROM pilot_grants WHERE student_id=? AND local_day=? AND quota_charged=1',
                      (session['student_id'],day)).fetchone()[0]
    allocation=None
    if config.wallet:
        from . import wallet_qa
        allocation=wallet_qa.plan(db,session,selected,grants,config,body)
        if quote_only:return allocation
        wallet_qa.confirm_quote(db,session,body,allocation)
    if not config.wallet and paid and used + len(fresh) > config.daily_new:
        raise api.APIError('Đã đạt hạn mức nội dung mới hôm nay trên QA.',429)
    grade, ayid = api.ensure_grade(db,session['student_id'],session['birth_year'])
    eid = db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,academic_year_id,owner_student_id,mode,created_at) "
        "VALUES (?,?,?,30,'published',?,?,'test',?)", ('QA-'+secrets.token_hex(8),'QA giả — Free/VIP đợt 1',
        grade,ayid,session['student_id'],api.stamp())).lastrowid
    db.execute('UPDATE exams SET response_mode=? WHERE id=?',(response_mode,eid))
    for position, row in enumerate(selected,1):
        options = db.execute('SELECT options_json FROM question_versions WHERE id=?',(row['version_id'],)).fetchone()[0]
        db.execute('INSERT INTO exam_items VALUES (?,?,?,?,?)',(eid,position,row['version_id'],1,options))
        if isinstance(row,dict) and 'itemMode' in row:db.execute('INSERT INTO practice_exam_items VALUES (?,?,?,?,?)',(eid,position,row['content_key'],row['itemMode'],row['topicTitle']))
    for quota_key, row in fresh:
        db.execute('INSERT INTO pilot_grants VALUES (?,?,?,?,?,?)',
                   (session['student_id'],quota_key,row['version_id'],api.stamp(),day,int(paid and not config.wallet)))
    if allocation:wallet_qa.debit(db,session,allocation,eid)
    db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES (?,?,?,?,'in_progress',?)",
               (eid,session['student_id'],api.stamp(),api.stamp(api.now()+timedelta(minutes=30)),key))
    db.execute('INSERT INTO pilot_requests VALUES (?,?,?,?)',(session['student_id'],key,digest,eid))
    return api.exam_view(db,api.owned_attempt(db,session,eid))
