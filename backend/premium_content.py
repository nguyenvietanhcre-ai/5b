"""Server-side premium catalogue. Never expose locked media URLs in metadata."""
from urllib.parse import urlsplit
import json
import secrets
from datetime import timedelta
from . import platform_api as api
from .platform_api import APIError
from .learning_update import membership

PLUS = ('VIP+', 'SVip')


def require_plus(db, session):
    if membership(db, session) not in PLUS:
        raise APIError('Nội dung này dành cho VIP+. Em hãy nâng cấp gói.', 403)


def series(db, session):
    paid = membership(db, session) != 'Free'
    from .admin_catalogue import controls
    opened=controls(db)['videos_open']
    result = []
    for item in db.execute('SELECT * FROM video_series WHERE archived=0 ORDER BY position'):
        videos = []
        for index, video in enumerate(db.execute(
                'SELECT id,title,position FROM series_videos WHERE series_slug=? AND published=1 AND archived=0 ORDER BY position',
                (item['slug'],)), 1):
            videos.append({**dict(video), 'accessible': opened and (paid or index <= 3)})
        result.append({'slug': item['slug'], 'title': item['title'], 'videos': videos,
                       'freePreviewCount': 3})
    return {'series': result}


def video(db, session, identity):
    from .admin_catalogue import require_open
    require_open(db,'videos_open')
    row = db.execute('SELECT v.* FROM series_videos v JOIN video_series s ON s.slug=v.series_slug WHERE v.id=? AND v.published=1 AND v.archived=0 AND s.archived=0', (identity,)).fetchone()
    if not row:
        raise APIError('Video chưa được phát hành.', 404)
    position = db.execute('SELECT count(*) FROM series_videos WHERE series_slug=? AND published=1 AND archived=0 AND position<=?',
                          (row['series_slug'], row['position'])).fetchone()[0]
    if membership(db, session) == 'Free' and position > 3:
        raise APIError('Free xem được 3 video đầu mỗi series. Nâng cấp VIP để xem tiếp.', 403)
    parsed = urlsplit(row['media_url'])
    if (parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password
            or '\\' in row['media_url'] or any(ord(c) < 32 for c in row['media_url'])):
        raise APIError('Đường dẫn video đang chờ cập nhật.', 503)
    return {'video': {'id': row['id'], 'title': row['title'], 'url': row['media_url']}}


def catalogue(db, session):
    role = membership(db, session)
    from .admin_catalogue import controls
    flags=controls(db)
    return {'controls':flags,'membership': role, 'schoolAccess': role in PLUS,
            'advancedAccess': role in PLUS,
            'tracks': [{'key': key, 'title': title, 'accessible': role in PLUS,
                        'ready': bool(db.execute('SELECT 1 FROM premium_sets WHERE track=? AND published=1 AND archived=0', (key,)).fetchone())} for key, title in (
                ('super-hard', 'Câu siêu khó'), ('classification', 'Phân loại học sinh'),
                ('olympiad', 'Thi học sinh giỏi'), ('school', 'Ôn theo trường · Khối 5'))],
            'sets': [dict(row) for row in db.execute('SELECT slug,title,track,grade FROM premium_sets WHERE published=1 AND archived=0 ORDER BY grade,title')],
            'purchases': [dict(row) for row in db.execute("SELECT id,exam_title,amount,status FROM payment_orders WHERE account_id=? AND purchase_type='exam' ORDER BY id DESC LIMIT 50",(session['account_id'],))],
            'examProducts': [dict(row) for row in db.execute(
                'SELECT slug,title,description,price FROM exam_products WHERE published=1 AND archived=0 ORDER BY price,slug')],
            **series(db, session)}


def start_set(db, session, body):
    """Issue only explicitly curated, published versions; keep owned history readable."""
    key = api.text_field(body, 'requestKey', 80, 8)
    slug = api.text_field(body, 'slug', 100, 1)
    old = db.execute('SELECT exam_id FROM exam_attempts WHERE student_id=? AND request_key=?',
                     (session['student_id'], key)).fetchone()
    if old:
        exam = api.owned_attempt(db, session, old[0])
        code = db.execute('SELECT exam_code FROM exams WHERE id=?', (old[0],)).fetchone()[0]
        if not code.startswith('PREMIUM-' + slug + '-'):
            raise APIError('Mã tạo bài đã dùng cho nội dung khác.', 409)
        return {'exam': api.exam_view(db, exam)}
    from .admin_catalogue import require_open
    require_open(db,'advanced_open')
    require_plus(db, session)
    row = db.execute('SELECT * FROM premium_sets WHERE slug=? AND published=1 AND archived=0', (slug,)).fetchone()
    if not row:
        raise APIError('Bộ nội dung đang được biên tập, chưa cấp bài hoặc trừ lượt.', 503)
    payload = {'grade':row['grade'],'duration_minutes':row['duration_minutes'],'title':row['title'],'ids':json.loads(row['question_version_ids_json'])}
    return issue_exam(db,session,payload,key,'PREMIUM-'+slug+'-'+secrets.token_hex(8))


def issue_exam(db,session,payload,key,code):
    grade, year = api.ensure_grade(db, session['student_id'], session['birth_year'])
    if grade != payload['grade']:
        raise APIError('Bộ nội dung không thuộc khối của em.', 403)
    ids = payload['ids']
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100
            or any(type(identity) is not int for identity in ids) or len(set(ids)) != len(ids)):
        raise APIError('Bộ nội dung cần được rà lại.', 503)
    for identity in ids:
        valid = db.execute("SELECT 1 FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE v.id=? AND v.status='published' AND q.grade_id=?", (identity, grade)).fetchone()
        if not valid:
            raise APIError('Có câu chưa được phát hành; chưa cấp bài.', 503)
    if db.execute('SELECT count(*) FROM exam_attempts WHERE student_id=? AND started_at>?',
                  (session['student_id'], api.stamp(api.now()-timedelta(hours=1)))).fetchone()[0] >= 60:
        raise APIError('Em đã tạo nhiều bài. Hãy tiếp tục bài đang làm.', 429)
    eid = db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,academic_year_id,owner_student_id,mode,week_limit,created_at,response_mode) VALUES (?,?,?,?,'published',?,?,'test',35,?,'typed')",
                     (code, payload['title'], grade,
                      payload['duration_minutes'], year, session['student_id'], api.stamp())).lastrowid
    for position, identity in enumerate(ids, 1):
        options = json.loads(db.execute('SELECT options_json FROM question_versions WHERE id=?', (identity,)).fetchone()[0])
        secrets.SystemRandom().shuffle(options)
        db.execute('INSERT INTO exam_items VALUES (?,?,?,?,?)', (eid, position, identity, 1, api.packed(options)))
    db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES (?,?,?,?,'in_progress',?)",
               (eid, session['student_id'], api.stamp(), api.stamp(api.now()+timedelta(minutes=payload['duration_minutes'])), key))
    return {'exam': api.exam_view(db, api.owned_attempt(db, session, eid))}
