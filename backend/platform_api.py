"""Same-origin, session-authenticated local learning API backed by SQLite.

Credentials, exam selection, deadlines, marking and referral rewards stay on the
server. The static/offline build deliberately does not enable this API client.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .nickname_policy import safe_nickname, validate_nickname


VN = timezone(timedelta(hours=7))
COOKIE = '5bmath_session'
ITERATIONS = 600_000
DEFAULT_THEME = 'garden-adventure'
LEARNING_THEMES = frozenset((DEFAULT_THEME, 'morning-garden', 'crayon-workshop',
                            'clay-sprout', 'garden-notebook'))
MASCOT_NAMES = {'voi': 'Voi', 'sprout': 'Mầm Sách', 'fox': 'Cáo Nâu', 'cat': 'Mèo', 'rabbit': 'Thỏ', 'gau': 'Gấu'}
MASCOT_NAMES['sparrow'] = 'Chim sẻ'
MASCOT_NAMES['eagle'] = 'Đại bàng'
MASCOT_NAMES['tiger'] = 'Hổ'
MASCOT_NAMES['lion'] = 'Sư tử'
MASCOT_NAMES['cu-meo'] = 'Cú mèo'
MASCOT_NAMES['ca-map'] = 'Cá mập'
MASCOT_NAMES['butterfly'] = 'Bướm'
MASCOT_NAMES['bee'] = 'Ong'
MASCOT_NAMES['dolphin'] = 'Cá heo'
MASCOT_NAMES['starfish'] = 'Sao biển'
MASCOT_NAMES['octopus'] = 'Bạch tuộc'
MASCOT_NAMES['horse'] = 'Ngựa'
MASCOT_NAMES['dog'] = 'Chó'
MASCOT_CODES = {name: code for code, name in MASCOT_NAMES.items()}
MASCOT_NAMES['crab'] = 'Cua biển'
MASCOT_CODES['Cua biển'] = 'crab'
_attempts = {}
_auth_lock = threading.Lock()

# The public articles use the same stable keys in account progress and views.
PUBLIC_LESSONS = (
    {'id': 'public-decimal', 'topic': 'decimal', 'title': 'So sánh số thập phân',
     'theory': 'So sánh phần nguyên trước. Nếu phần nguyên bằng nhau, so sánh lần lượt các hàng phần mười, phần trăm, phần nghìn đến hàng đầu tiên khác nhau. Có thể thêm chữ số 0 bên phải phần thập phân mà không đổi giá trị số.',
     'example': {'text': 'Thỏ nhảy 2,45 m, Sóc nhảy 2,5 m. Bạn nào nhảy xa hơn?',
                 'steps': ['Viết 2,5 = 2,50.', 'Hai số có phần nguyên bằng 2; ở hàng phần mười, 5 lớn hơn 4.', 'Vì 2,50 > 2,45 nên Sóc nhảy xa hơn.']}},
    {'id': 'public-percent', 'topic': 'percent', 'title': 'Hai lần thay đổi phần trăm',
     'theory': 'Mỗi tỉ lệ phần trăm được tính trên giá trị tại thời điểm đó. Tăng 20% rồi giảm 20% không đưa giá trở lại ban đầu vì hai lần tính dựa trên hai giá trị khác nhau.',
     'example': {'text': 'Ba lô giá 200.000 đồng, tăng 20% rồi giảm 20% trên giá đã tăng. Tính giá cuối.',
                 'steps': ['Giá sau tăng: 200.000 × 120 : 100 = 240.000 đồng.', 'Số tiền giảm: 240.000 × 20 : 100 = 48.000 đồng.', 'Giá cuối: 240.000 − 48.000 = 192.000 đồng.']}},
)


class APIError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(value=None):
    return (value or now()).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def public_origin():
    """Explicit website origin; never trust a client-supplied forwarded header."""
    value = os.environ.get('MAM_TOAN_PUBLIC_ORIGIN', '').strip().rstrip('/')
    if not value:
        return ''
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or
            parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise APIError('Địa chỉ website trên máy chủ chưa hợp lệ.', 503)
    return parsed.scheme + '://' + parsed.netloc.lower()


def same_origin(handler):
    origin = handler.headers.get('Origin')
    if not origin:
        return True  # Authenticated writes also require the session's CSRF token.
    try:
        parsed = urlsplit(origin)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or
                parsed.password or parsed.path or parsed.query or parsed.fragment):
            return False
        expected = public_origin()
        return (parsed.scheme + '://' + parsed.netloc.lower() == expected if expected else
                parsed.netloc.lower() == handler.headers.get('Host', '').lower())
    except ValueError:
        return False


def session_cookie(name, token, max_age):
    secure = '; Secure' if public_origin().startswith('https://') else ''
    return f'{name}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}' + secure


def mascot_code(name):
    return MASCOT_CODES.get(name, 'sprout')


@contextmanager
def connect(path, write=False):
    if hasattr(path, 'connect'):
        with path.connect(write) as db:
            yield db
        return
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if write:
            db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def academic():
    local = now().astimezone(VN)
    year = local.year - (local.month < 7)
    week = max(1, min(35, (local.date() - datetime(year, 9, 5).date()).days // 7 + 1))
    return year, week


def seed_catalog(path):
    catalog = json.loads(Path(__file__).with_name('learning-catalog.json').read_text(encoding='utf-8'))
    with connect(path, True) as db:
        for name in MASCOT_NAMES.values():
            db.execute('INSERT OR IGNORE INTO mascots(name) VALUES (?)', (name,))
        db.execute('INSERT OR IGNORE INTO mascot_levels(level,min_xp) VALUES (1,1000)')
        # Three actual reading/revision lessons for next week, reusing the
        # self-authored bank. Stable IDs retain progress as the week changes.
        future=[]
        for g in range(1,6):
            for i,original in enumerate([l for l in catalog['lessons'] if l['grade']==g][:3],1):
                future.append({**original,'id':f'g{g}-w{academic()[0]}-{academic()[1]+1}-{i}',
                               'week':academic()[1]+1,'title':'Ôn tập: '+original['title']})
        for lesson in catalog['lessons']+future:
            db.execute('INSERT INTO topics(grade_id,title,theory_json,client_key) SELECT ?,?,?,? '
                       'WHERE NOT EXISTS(SELECT 1 FROM topics WHERE grade_id=? AND client_key=?)',
                       (lesson['grade'], lesson['title'], packed([{'type':'text','text':lesson['theory']}]),
                        lesson['topic'], lesson['grade'], lesson['topic']))
            topic = db.execute('SELECT id FROM topics WHERE grade_id=? AND client_key=?',
                               (lesson['grade'], lesson['topic'])).fetchone()[0]
            db.execute('INSERT OR IGNORE INTO lessons(grade_id,topic_id,kind,week_no,title,body_json,client_key,presentation_json) '
                       'VALUES (?,?,\'weekly\',?,?,?,?,?)',
                       (lesson['grade'], topic, lesson['week'], lesson['title'],
                        packed([{'type':'text','text':lesson['theory']}]), lesson['id'], packed(lesson)))
        for public in PUBLIC_LESSONS:
            topic = db.execute('SELECT id FROM topics WHERE grade_id=5 AND client_key=?', (public['topic'],)).fetchone()
            presentation = {**public, 'grade': 5, 'week': 1, 'symbol': '<' if public['topic'] == 'decimal' else '%',
                            'description': public['theory'][:160], 'source': 'public-article'}
            db.execute("INSERT OR IGNORE INTO lessons(grade_id,topic_id,kind,week_no,title,body_json,client_key,presentation_json) VALUES (5,?,'topic',1,?,?,?,?)",
                       (topic['id'], public['title'], packed([{'type': 'text', 'text': public['theory']}]),
                        public['id'], packed(presentation)))
        from .question_bank import seed_question_bank
        seed_question_bank(db, catalog)
        # A visible rich-content example on the grade 5 area lesson exercises the
        # same media references and MathML blocks that real questions can store.
        image = Path(__file__).parent.parent/'frontend'/'demo-rectangle.svg'
        db.execute('INSERT OR IGNORE INTO media_assets(storage_key,url,mime_type,width,height,byte_size,alt_text) '
                   'VALUES (\'learning/rectangle.svg\',\'/demo-rectangle.svg\',\'image/svg+xml\',480,240,?,?)',
                   (image.stat().st_size,'Hình chữ nhật dài 18 cm, rộng 9 cm.'))
        asset=db.execute('SELECT id FROM media_assets WHERE storage_key=\'learning/rectangle.svg\'').fetchone()[0]
        lesson=db.execute('SELECT id,body_json FROM lessons WHERE client_key=\'g5-area\'').fetchone()
        if lesson and not db.execute('SELECT 1 FROM lesson_assets WHERE lesson_id=? AND asset_id=?',(lesson['id'],asset)).fetchone():
            blocks=json.loads(lesson['body_json']) + [
                {'type':'text','text':'Ví dụ minh họa: hình chữ nhật dài 18 cm và rộng 9 cm.'},
                {'type':'image','asset_id':asset},
                {'type':'math','latex':r'S=18\times9=162\ \mathrm{cm}^2',
                 'mathml':'<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>S</mi><mo>=</mo><mn>18</mn><mo>×</mo><mn>9</mn><mo>=</mo><mn>162</mn><msup><mi>cm</mi><mn>2</mn></msup></math>'}]
            db.execute('UPDATE lessons SET body_json=? WHERE id=?',(packed(blocks),lesson['id']))
            db.execute('INSERT INTO lesson_assets VALUES (?,?)',(lesson['id'],asset))


def password_hash(password):
    if not isinstance(password, str) or not 6 <= len(password) <= 128:
        raise APIError('Mật khẩu cần từ 6 đến 128 ký tự.')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password, encoded):
    # Same work for unknown usernames; never disclose which identifier exists.
    encoded = encoded or f'pbkdf2_sha256${ITERATIONS}${"00"*16}${"00"*32}'
    _, iterations, salt, expected = encoded.split('$')
    result = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(result.hex(), expected)


def limit_auth(handler):
    key = handler.client_address[0]
    clock = time.monotonic()
    with _auth_lock:
        for address in list(_attempts):
            _attempts[address] = [t for t in _attempts[address] if t > clock - 300]
            if not _attempts[address]:
                del _attempts[address]
        attempts = _attempts.setdefault(key, [])
        if len(attempts) >= 30:
            raise APIError('Đã thử nhiều lần. Em hãy đợi 5 phút rồi đăng nhập lại.', 429)
        attempts.append(clock)


def read_session(handler, db):
    cookie = SimpleCookie()
    try:
        cookie.load(handler.headers.get('Cookie', ''))
        token = cookie[COOKIE].value if COOKIE in cookie else ''
    except Exception:
        token = ''
    digest = hashlib.sha256(token.encode()).hexdigest()
    return db.execute('SELECT s.*, a.birth_year, a.invite_code, a.vip_expires_at, '
                      'p.id student_id,p.full_name FROM auth_sessions s JOIN accounts a ON a.id=s.account_id '
                      'JOIN students p ON p.account_id=a.id WHERE s.token_hash=? AND s.expires_at>? '
                      'AND a.status=\'active\' AND p.status=\'active\'', (digest, stamp())).fetchone()


def issue_session(handler, db, account_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (stamp(),))
    db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,?)',
               (hashlib.sha256(token.encode()).hexdigest(), account_id, csrf, stamp(), stamp(now()+timedelta(days=7))))
    handler.api_headers = {'Set-Cookie': session_cookie(COOKIE, token, 604800)}
    return db.execute('SELECT s.*,a.birth_year,a.invite_code,a.vip_expires_at,p.id student_id,p.full_name '
                      'FROM auth_sessions s JOIN accounts a ON a.id=s.account_id JOIN students p ON p.account_id=a.id '
                      'WHERE s.token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()


def text_field(body, key, maximum, minimum=1):
    value = body.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise APIError(f'Thông tin {key} không hợp lệ.')
    return value.strip()


def nickname_field(body):
    try:
        return validate_nickname(body.get('name'))
    except ValueError as error:
        raise APIError(str(error)) from error


def register(handler, db, body, credential=None):
    from .system_settings import require_feature
    require_feature(db, 'registration_open')
    login = text_field(body, 'login', 100, 3).lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.@+\-]{2,99}', login):
        raise APIError('Tên đăng nhập dùng ít nhất 3 chữ cái không dấu, số hoặc . _ @ + -')
    name = nickname_field(body)
    birth = body.get('birthYear')
    year, _ = academic()
    if type(birth) is not int or not 1 <= year-birth-5 <= 5:
        raise APIError('Năm sinh cần tương ứng học sinh khối 1–5 trong năm học hiện tại.')
    invite = body.get('inviteCode', '')
    if not isinstance(invite, str) or len(invite) > 30:
        raise APIError('Mã giới thiệu không hợp lệ.')
    inviter = db.execute('SELECT id FROM accounts WHERE invite_code=? AND status=\'active\'',
                         (invite.strip().upper(),)).fetchone() if invite.strip() else None
    if invite.strip() and not inviter:
        raise APIError('Mã giới thiệu không tồn tại. Em hãy kiểm tra lại.')
    credential = credential or password_hash(body.get('password'))
    if (db.execute('SELECT 1 FROM accounts WHERE lower(login_identifier)=?', (login,)).fetchone()
            or db.execute('SELECT 1 FROM staff_users WHERE login=?', (login,)).fetchone()):
        raise APIError('Tên đăng nhập này đã được sử dụng.', 409)
    code = secrets.token_hex(8).upper()
    aid = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash) '
                     'VALUES (?,?,?,?,?,?)', ('ACC-'+code,login,birth,'5B'+code[:10],stamp(),credential)).lastrowid
    sid = db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,?,?)',
                     ('HS-'+code,name,year-birth-5,aid)).lastrowid
    ensure_grade(db, sid, birth)
    mascot = db.execute('SELECT id FROM mascots WHERE name=\'Mầm Sách\'').fetchone()[0]
    db.execute('INSERT INTO student_companions(student_id,mascot_id) VALUES (?,?)', (sid,mascot))
    db.execute('INSERT INTO learning_preferences(student_id) VALUES (?)', (sid,))
    if inviter:
        db.execute('INSERT INTO account_referrals(inviter_account_id,invitee_account_id,invite_code,registered_at) VALUES (?,?,?,?)',
                   (inviter[0],aid,invite.strip().upper(),stamp()))
    return issue_session(handler,db,aid)


def prepare_login(path, body, staff_only=False):
    """Do expensive verification without reserving SQLite's single writer."""
    login = text_field(body, 'login', 100, 3).lower()
    password = body.get('password', '')
    if not isinstance(password, str) or len(password) > 128:
        raise APIError('Thông tin đăng nhập không đúng.', 401)
    with connect(path) as db:
        account = None if staff_only else db.execute(
            "SELECT a.id,a.password_hash FROM accounts a JOIN students s ON s.account_id=a.id "
            "WHERE a.login_identifier=? AND a.status='active' AND s.status='active'", (login,)).fetchone()
        staff = db.execute("SELECT id,password_hash FROM staff_users WHERE login=? AND status='active'", (login,)).fetchone()
    # One real derivation for a unique active identity, one dummy for unknown names.
    # Retain both candidates for legacy imports with an identifier in both tables.
    candidates = [('student', account)] if account else []
    if staff:
        candidates.append(('staff', staff))
    for principal, candidate in candidates or [('unknown', None)]:
        credential = candidate['password_hash'] if candidate else None
        if verify_password(password, credential) and candidate and credential:
            return principal, candidate['id'], credential, login
    raise APIError('Thông tin đăng nhập không đúng.', 401)


def verified_login(db, proof):
    """Recheck credentials and status after acquiring the write transaction."""
    principal, identity, credential, login = proof
    if principal == 'staff':
        row = db.execute("SELECT * FROM staff_users WHERE id=? AND password_hash=? AND login=? AND status='active'",
                         (identity, credential, login)).fetchone()
    else:
        row = db.execute("SELECT a.* FROM accounts a JOIN students s ON s.account_id=a.id "
                         "WHERE a.id=? AND a.password_hash=? AND a.login_identifier=? AND a.status='active' AND s.status='active'",
                         (identity, credential, login)).fetchone()
    if not row:
        raise APIError('Thông tin đăng nhập vừa thay đổi. Hãy đăng nhập lại.', 401)
    return row


def ensure_grade(db, sid, birth):
    year, _ = academic()
    grade = max(1,min(5,year-birth-5))
    label = f'{year}–{year+1}'
    row = db.execute('SELECT id FROM academic_years WHERE label=?', (label,)).fetchone()
    if row:
        ayid = row[0]
    else:
        ayid = db.execute('INSERT INTO academic_years(label,grade_effective_from,instruction_starts_on,ends_on) VALUES (?,?,?,?)',
                         (label,f'{year}-07-01',f'{year}-09-05',f'{year+1}-06-30')).lastrowid
    if not db.execute('SELECT 1 FROM student_grades WHERE student_id=? AND academic_year_id=?', (sid, ayid)).fetchone():
        db.execute('INSERT INTO student_grades VALUES (?,?,?)', (sid,ayid,grade))
    return grade, ayid


def owned_attempt(db, session, exam_id):
    row = db.execute('SELECT a.*,e.title,e.exam_code,e.grade_level FROM exam_attempts a JOIN exams e ON e.id=a.exam_id '
                     'WHERE a.exam_id=? AND a.student_id=?', (exam_id,session['student_id'])).fetchone()
    if not row:
        raise APIError('Không tìm thấy bài làm của tài khoản này.',404)
    return row


def blocks_text(blocks):
    return ' '.join(b.get('text', b.get('latex', '')) for b in blocks
                    if isinstance(b, dict) and b.get('type') in ('text','math'))


def exam_view(db, attempt, summary=False):
    submitted = attempt['status'] == 'submitted'
    if summary and submitted:
        return {'id':str(attempt['exam_id']),'code':attempt['exam_code'],'title':attempt['title'],
                'grade':attempt['grade_level'],'submittedAt':attempt['submitted_at'],
                'score':round(attempt['earned_points']/attempt['total_points']*10,1),'questions':[]}
    answers = {str(r['position']):r['answer'] for r in db.execute('SELECT position,answer FROM exam_draft_answers WHERE attempt_id=?', (attempt['id'],))}
    questions = []
    for row in db.execute('SELECT i.position,i.options_json,v.*,t.title topic_title FROM exam_items i '
                          'JOIN question_versions v ON v.id=i.question_version_id JOIN questions q ON q.id=v.question_id '
                          'JOIN topics t ON t.id=q.topic_id WHERE i.exam_id=? ORDER BY i.position', (attempt['exam_id'],)):
        prompt = json.loads(row['prompt_json'])
        # options are immutable per exam, not a client-generated shuffle.
        options = json.loads(row[1])
        question = {'id':str(row['position']),'text':blocks_text(prompt),'prompt':prompt,
                    'options':options,'topicTitle':row['topic_title']}
        if submitted:
            rule = json.loads(row['grading_rule_json'])
            steps = json.loads(row['solution_steps_json'])
            question.update(answer=rule['answer'],steps=[blocks_text([b]) for b in steps],
                            solution=steps,thinking=blocks_text(json.loads(row['hints_json'])))
        questions.append(question)
    assets = [dict(r) for r in db.execute('SELECT DISTINCT m.* FROM media_assets m JOIN question_assets a ON a.asset_id=m.id '
                                         'JOIN exam_items i ON i.question_version_id=a.question_version_id WHERE i.exam_id=?', (attempt['exam_id'],))]
    start = datetime.fromisoformat(attempt['started_at'].replace('Z','+00:00'))
    due = datetime.fromisoformat(attempt['due_at'].replace('Z','+00:00'))
    result = {'id':str(attempt['exam_id']),'code':attempt['exam_code'],'title':attempt['title'],
              'grade':attempt['grade_level'],'questions':questions,'assets':assets,'answers':answers,
              'index':attempt['cursor'],'startedAt':int(start.timestamp()*1000),'expiresAt':int(due.timestamp()*1000)}
    if submitted:
        end = datetime.fromisoformat(attempt['submitted_at'].replace('Z','+00:00'))
        result.update(submittedAt=attempt['submitted_at'],correct=attempt['earned_points'],
                      score=round(attempt['earned_points']/attempt['total_points']*10,1),
                      duration=max(0,int((min(end,due)-start).total_seconds())))
    return result


def submit(db, attempt):
    if attempt['status'] == 'submitted':
        return
    earned = 0
    rows = db.execute('SELECT i.position,v.grading_rule_json,d.answer FROM exam_items i '
                       'JOIN question_versions v ON v.id=i.question_version_id LEFT JOIN exam_draft_answers d '
                       'ON d.attempt_id=? AND d.position=i.position WHERE i.exam_id=? ORDER BY i.position',
                       (attempt['id'],attempt['exam_id'])).fetchall()
    for row in rows:
        answer = row['answer'] or ''
        correct = int(answer == str(json.loads(row['grading_rule_json'])['answer']))
        earned += correct
        db.execute('INSERT INTO exam_answers VALUES (?,?,?,?,?)',
                   (attempt['id'],attempt['exam_id'],row['position'],packed({'answer':answer}),correct))
    db.execute('UPDATE exam_attempts SET status=\'submitted\',submitted_at=?,earned_points=?,total_points=? WHERE id=?',
               (stamp(),earned,len(rows),attempt['id']))


def create_exam(db, session, body):
    from .learning_update import consume, membership
    key = text_field(body,'requestKey',80,8)
    old = db.execute('SELECT exam_id FROM exam_attempts WHERE student_id=? AND request_key=?', (session['student_id'],key)).fetchone()
    if old:
        return exam_view(db,owned_attempt(db,session,old[0]))
    count, difficulty = body.get('count',10), body.get('difficulty',0)
    if type(count) is not int or count not in (3,10) or type(difficulty) is not int or difficulty not in range(4):
        raise APIError('Số câu hoặc độ khó không hợp lệ.')
    if db.execute('SELECT count(*) FROM exam_attempts WHERE student_id=? AND started_at>?',
                  (session['student_id'],stamp(now()-timedelta(hours=1)))).fetchone()[0] >= 60:
        raise APIError('Em đã tạo nhiều đề. Hãy tiếp tục bài đang làm trước.',429)
    grade, ayid = ensure_grade(db,session['student_id'],session['birth_year'])
    topic = body.get('topic','')
    if not isinstance(topic,str) or len(topic)>60:
        raise APIError('Chuyên đề không hợp lệ.')
    category = body.get('category') or ('content' if topic or body.get('maxWeek') is not None else 'combined')
    if category not in ('content','combined','school'): raise APIError('Loại luyện tập không hợp lệ.')
    if category=='combined' and (topic or body.get('maxWeek') is not None or body.get('week') is not None or count==3):
        raise APIError('Phạm vi này thuộc luyện theo nội dung.')
    if category=='content' and not topic and body.get('maxWeek') is None:
        raise APIError('Chọn chuyên đề hoặc chương trình trên lớp.')
    if category=='combined' and difficulty==3: raise APIError('Đề tổng hợp có ba mức: Cơ bản, Nâng cao, Khó.')
    if category=='school':
        if membership(db,session)=='Free': raise APIError('Đề theo trường dành cho VIP và SVip.',403)
        if grade!=5: raise APIError('Đề theo trường chỉ dành cho khối 5.',403)
        if body.get('school') not in ('cau-giay','ngoai-ngu','ntt'): raise APIError('Trường không hợp lệ.')
        difficulty=1
    max_week = academic()[1] if body.get('maxWeek') is not None else 35
    exact_week = body.get('week')
    if exact_week is not None and (type(exact_week) is not int or exact_week not in range(1,academic()[1]+1)):
        raise APIError('Tuần học không hợp lệ.')
    from .question_bank import published_version_ids
    pool = published_version_ids(db, grade, difficulty + 1, max_week, topic, exact_week)
    if len(pool)<count:
        raise APIError('Chưa đủ câu hỏi trong phạm vi này.')
    if category!='school': consume(db,session,category,key)
    previous = db.execute('SELECT exam_id FROM exam_attempts WHERE student_id=? ORDER BY id DESC LIMIT 1', (session['student_id'],)).fetchone()
    used = {r[0] for r in db.execute('SELECT question_version_id FROM exam_items WHERE exam_id=?', (previous[0],))} if previous else set()
    fresh = [qid for qid in pool if qid not in used]
    selected = secrets.SystemRandom().sample(fresh if len(fresh)>=count else pool,count)
    minutes = 10 if count==3 else 30
    code = '5B-'+secrets.token_hex(5).upper()
    title = ('Luyện theo trường · '+{'cau-giay':'Cầu Giấy','ngoai-ngu':'Ngoại ngữ','ntt':'Nguyễn Tất Thành'}[body['school']]+' · Mẫu tự biên soạn') if category=='school' else 'Luyện theo nội dung' if category=='content' else 'Luyện đề tổng hợp'
    from .question_bank import SAMPLE_LABEL
    placeholders = ','.join('?' for _ in selected)
    if SAMPLE_LABEL not in title and db.execute(
            'SELECT 1 FROM question_versions v JOIN questions q ON q.id=v.question_id '
            f"WHERE v.id IN ({placeholders}) AND q.question_code LIKE 'BANK2-%' LIMIT 1", selected).fetchone():
        title += ' · ' + SAMPLE_LABEL
    eid = db.execute('INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,academic_year_id,owner_student_id,mode,week_limit,created_at) '
                     'VALUES (?,?,?,?,\'published\',?,?,\'test\',?,?)',
                     (code,title,grade,minutes,ayid,session['student_id'],max_week,stamp())).lastrowid
    for position, qid in enumerate(selected,1):
        options = json.loads(db.execute('SELECT options_json FROM question_versions WHERE id=?',(qid,)).fetchone()[0])
        secrets.SystemRandom().shuffle(options)
        db.execute('INSERT INTO exam_items VALUES (?,?,?,?,?)', (eid,position,qid,1,packed(options)))
    db.execute('INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES (?,?,?,?,\'in_progress\',?)',
               (eid,session['student_id'],stamp(),stamp(now()+timedelta(minutes=minutes)),key))
    return exam_view(db,owned_attempt(db,session,eid))


def lesson_payload(row):
    """Normalize legacy/admin lesson records without inventing an example."""
    try:
        presentation = json.loads(row['presentation_json'])
    except (ValueError, TypeError):
        presentation = {}
    lesson = dict(presentation) if isinstance(presentation, dict) else {}
    lesson.update(id=row['client_key'], grade=row['grade_id'], title=row['title'],
                  week=row['week_no'], topic=row['topic_client'])
    try:
        body = json.loads(row['body_json'])
    except (ValueError, TypeError):
        body = []
    lesson['body'] = body if isinstance(body, list) else []
    if not isinstance(lesson.get('theory'), str):
        lesson['theory'] = blocks_text(lesson['body'])
    example = lesson.get('example')
    lesson['example'] = ({'text': example['text'], 'steps': list(example['steps'])}
        if isinstance(example, dict) and isinstance(example.get('text'), str) and example['text'].strip() and
        isinstance(example.get('steps'), list) and all(isinstance(step, str) for step in example['steps']) else None)
    video = row['video_ref'] or ''
    try:
        parsed = urlsplit(video)
        safe_video = not parsed.username and not parsed.password and '\\' not in video and not any(ord(c) < 32 for c in video) and (
            parsed.scheme in ('http', 'https') and parsed.netloc or video.startswith('/') and not video.startswith('//'))
    except ValueError:
        safe_video = False
    lesson['videoRef'] = video if safe_video else ''
    lesson['video_ref'] = lesson['videoRef']
    return lesson


def vietnam_activity(rows):
    """Split recorded intervals at Vietnam midnight without changing UTC data."""
    def local_time(value):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(VN)

    totals = {}
    for row in rows:
        try:
            start = local_time(row['started_at'])
            end = local_time(row['last_seen_at'])
            if row['ended_at']:
                end = min(end, local_time(row['ended_at']))
        except (ValueError, TypeError, AttributeError):
            continue
        if end < start:
            continue
        totals.setdefault(start.date().isoformat(), 0)
        while start < end:
            midnight = start.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            stop = min(end, midnight)
            key = start.date().isoformat()
            totals[key] = totals.get(key, 0) + (stop - start).total_seconds()
            start = stop
    return {day: int(seconds) for day, seconds in totals.items()}


def identity_view(db, session):
    """Small authenticated public-page snapshot; full learning state stays on demand."""
    sid = session['student_id']
    profile = db.execute('SELECT s.full_name,a.login_identifier FROM students s JOIN accounts a ON a.id=s.account_id WHERE s.id=?', (sid,)).fetchone()
    preferences = db.execute('SELECT theme FROM learning_preferences WHERE student_id=?', (sid,)).fetchone()
    companion = db.execute('SELECT c.xp,m.name FROM student_companions c JOIN mascots m ON m.id=c.mascot_id WHERE student_id=?', (sid,)).fetchone()
    completed = {r['client_key']: {'date':r['first_completed_at'],'grade':r['grade_id']} for r in db.execute(
        "SELECT l.client_key,l.grade_id,p.first_completed_at FROM lesson_progress p JOIN lessons l ON l.id=p.lesson_id WHERE p.student_id=? AND l.client_key IN ('public-decimal','public-percent')", (sid,))}
    theme = preferences['theme'] if preferences else DEFAULT_THEME
    return {'authenticated':True,'csrf':session['csrf_token'],'name':safe_nickname(profile['full_name']),
            'account':{'id':session['account_id'],'login':profile['login_identifier']},'partial':True,
            'state':{'birthYear':session['birth_year'],'completed':completed,
                     'mascot':mascot_code(companion['name'] if companion else None),
                     'points':companion['xp'] if companion else 1000,
                     'theme':theme if theme in LEARNING_THEMES else DEFAULT_THEME}}


def state_view(db, session, review=False, read_only=False):
    from .zoom_classroom import unread_summary
    from .learning_update import usage, membership as member_label
    from .notifications import inbox, referrals as referral_page
    sid, aid = session['student_id'],session['account_id']
    grade = max(1, min(5, academic()[0] - session['birth_year'] - 5))
    if not read_only:
        ensure_grade(db,sid,session['birth_year'])
    current = db.execute('SELECT * FROM accounts WHERE id=?',(aid,)).fetchone()
    internal = bool(db.execute('SELECT 1 FROM access_entitlements WHERE account_id=? AND starts_at<=? '
                               'AND (ends_at IS NULL OR ends_at>?)',(aid,stamp(),stamp())).fetchone())
    membership = member_label(db,session)
    lessons = []
    for row in db.execute("SELECT l.*,t.client_key topic_client FROM lessons l LEFT JOIN topics t ON t.id=l.topic_id WHERE l.grade_id=? AND l.client_key IS NOT NULL AND l.publication_status='published' AND l.week_no<=? ORDER BY l.week_no,l.id",(grade,academic()[1]+1)):
        lesson = lesson_payload(row)
        lesson['assets']=[dict(a) for a in db.execute('SELECT m.* FROM media_assets m JOIN lesson_assets a ON a.asset_id=m.id WHERE a.lesson_id=?',(row['id'],))]
        lessons.append(lesson)
    completed = {r['client_key']:{'date':r['first_completed_at'],'grade':r['grade_id']} for r in db.execute(
        'SELECT l.client_key,l.grade_id,p.first_completed_at FROM lesson_progress p JOIN lessons l ON l.id=p.lesson_id '
        'WHERE p.student_id=? AND l.client_key IS NOT NULL',(sid,))}
    exams = {}
    for row in db.execute('SELECT a.*,e.title,e.exam_code,e.grade_level FROM exam_attempts a JOIN exams e ON e.id=a.exam_id '
                          'WHERE a.student_id=? ORDER BY a.id DESC LIMIT 100',(sid,)).fetchall():
        if not read_only and row['status']=='in_progress' and row['due_at']<=stamp():
            submit(db,row)
            row = owned_attempt(db,session,row['exam_id'])
        exams[str(row['exam_id'])] = exam_view(db,row,summary=True)
    active = next((eid for eid,exam in exams.items() if not exam.get('submittedAt')),'')
    companion = db.execute('SELECT c.xp,m.name FROM student_companions c JOIN mascots m ON m.id=c.mascot_id WHERE student_id=?',(sid,)).fetchone()
    invited = db.execute('SELECT invite_code FROM account_referrals WHERE invitee_account_id=?',(aid,)).fetchone()
    preferences = db.execute('SELECT * FROM learning_preferences WHERE student_id=?',(sid,)).fetchone()
    theme = preferences['theme'] if preferences and 'theme' in preferences.keys() else DEFAULT_THEME
    activity = vietnam_activity(db.execute('SELECT started_at,last_seen_at,ended_at FROM online_intervals WHERE student_id=?', (sid,)))
    notification_page = inbox(db, aid)
    referral_result = referral_page(db, aid)
    classes = [dict(r) for r in db.execute('SELECT c.id,c.name,c.meeting_ref,t.full_name teacher FROM class_enrollments e '
                   'JOIN online_classes c ON c.id=e.class_id JOIN teachers t ON t.id=c.teacher_id WHERE e.student_id=? AND e.left_at IS NULL AND c.status=\'active\'',(sid,))]
    battles = {str(r['duel_id']):{'id':str(r['duel_id']),'mode':'human','grade':r['grade_id'],'outcome':r['outcome'] or 'left',
                'completed':r['status']=='completed','reason':'completed' if r['status']=='completed' else 'cancelled',
                'correct':0,'rounds':0,'points':r['delta'] or 0,'review':[],'date':r['ended_at'] or r['created_at']} for r in db.execute(
        'SELECT p.duel_id,p.outcome,d.grade_id,d.status,d.ended_at,d.created_at,x.delta FROM duel_players p JOIN duels d ON d.id=p.duel_id '
        'LEFT JOIN xp_events x ON x.duel_player_id=p.id WHERE p.student_id=? AND d.status IN (\'completed\',\'abandoned\') ORDER BY d.id DESC LIMIT 100',(sid,))}
    for record in db.execute('SELECT result_json FROM arena_members WHERE student_id=? AND result_json IS NOT NULL',(sid,)):
        battle=json.loads(record[0])
        if 'opponent' in battle:
            battle['opponent'] = safe_nickname(battle['opponent'])
        if isinstance(battle.get('players'), list):
            battle['players'] = [safe_nickname(name) for name in battle['players']]
        if battle['id'] in battles:
            battle['date']=battles[battle['id']]['date']
            battles[battle['id']]=battle
    from .system_settings import settings
    return {'authenticated':True,'csrf':session['csrf_token'],'features':settings(db),'arenaDiscipline':arena_discipline(db,sid),'name':safe_nickname(db.execute('SELECT full_name FROM students WHERE id=?',(sid,)).fetchone()[0]),
            'account':{'id':aid,'login':current['login_identifier'],'membership':membership,'vipExpiresAt':current['vip_expires_at'],
                       'notifications':notification_page['rows'],'notificationUnreadCount':notification_page['unreadCount'],
                       'notificationTotal':notification_page['total'],'referrals':referral_result['rows'],
                       'referralTotal':referral_result['total'],'classes':classes if internal else [],'usage':usage(db,session),
                       'classroomUnread':unread_summary(db,session)},
            'lessons':lessons,'state':{'birthYear':session['birth_year'],'inviteCode':session['invite_code'],
            'invitedBy':invited[0] if invited else '', 'grade':grade,'week':academic()[1],
            'mascot':mascot_code(companion['name'] if companion else None),'points':companion['xp'] if companion else 1000,
            'theme':theme if theme in LEARNING_THEMES else DEFAULT_THEME,
            'completed':completed,'exams':exams,'battles':battles,'activity':activity,'lastLesson':preferences['last_lesson'] if preferences else '', 'activeExam':active}}


def leaderboard(db, session, query):
    from .learning_update import membership
    kind, period, scope = (query.get(k,[v])[0] for k,v in [('kind','battle'),('period','all'),('scope','all')])
    if kind not in ('battle','activity','exams') or period not in ('day','week','month','all') or scope not in ('all','grade','class'):
        raise APIError('Bộ lọc xếp hạng không hợp lệ.')
    if scope=='class' and membership(db,session)!='SVip': raise APIError('Xếp hạng lớp Zoom dành cho học sinh nội bộ.',403)
    local = now().astimezone(VN)
    cutoff = local.replace(hour=0,minute=0,second=0,microsecond=0)
    if period=='week': cutoff -= timedelta(days=cutoff.weekday())
    if period=='month': cutoff = cutoff.replace(day=1)
    start = stamp(cutoff) if period!='all' else '1970-01-01T00:00:00Z'
    grade, ayid = ensure_grade(db,session['student_id'],session['birth_year'])
    # Each aggregate is reduced per student before joining the bounded ranking.
    metrics = {
        'battle':('SELECT student_id,sum(delta) value FROM xp_events WHERE awarded_at>=? GROUP BY student_id',),
        'lessons':('SELECT student_id,count(*) value FROM lesson_progress WHERE first_completed_at>=? GROUP BY student_id',),
        'exams':('SELECT student_id,count(*) value FROM exam_attempts WHERE status=\'submitted\' AND submitted_at>=? GROUP BY student_id',),
        'activity':('SELECT student_id,sum(max(0,strftime(\'%s\',last_seen_at)-max(strftime(\'%s\',started_at),strftime(\'%s\',?)))) value FROM online_intervals GROUP BY student_id',),
    }
    value = 'c.xp' if kind=='battle' and period=='all' else 'coalesce(m.value,0)'
    rows = db.execute(f'WITH metric AS ({metrics[kind][0]}) SELECT s.id,s.full_name,g.grade_id,c.xp,ma.name mascot,{value} value, '
                      "(SELECT count(*) FROM duel_players p JOIN duels d ON d.id=p.duel_id WHERE p.student_id=s.id AND p.outcome='win' AND d.status='completed') wins, "
                      "(SELECT count(*) FROM duel_players p JOIN duels d ON d.id=p.duel_id WHERE p.student_id=s.id AND p.outcome='lose' AND d.status='completed') losses, "
                      '(SELECT z.name FROM class_enrollments e JOIN online_classes z ON z.id=e.class_id WHERE e.student_id=s.id AND e.left_at IS NULL LIMIT 1) class_name '
                      'FROM students s JOIN accounts a ON a.id=s.account_id JOIN student_grades g ON g.student_id=s.id '
                      'JOIN student_companions c ON c.student_id=s.id JOIN mascots ma ON ma.id=c.mascot_id LEFT JOIN metric m ON m.student_id=s.id '
                      'WHERE g.academic_year_id=? AND (?<>\'grade\' OR g.grade_id=?) AND a.is_demo=0 AND a.status=\'active\' '
                      'AND (?<>\'class\' OR EXISTS(SELECT 1 FROM class_enrollments e JOIN class_enrollments mine '
                      'ON mine.class_id=e.class_id AND mine.student_id=? AND mine.left_at IS NULL '
                      'WHERE e.student_id=s.id AND e.left_at IS NULL)) ORDER BY value DESC,s.id LIMIT 50',
                      (start,ayid,scope,grade,scope,session['student_id'])).fetchall()
    return {'rows':[{'rank':i+1,'name':safe_nickname(r['full_name']),'value':round(r['value']/3600,2) if kind=='activity' else r['value'],
                     'mine':r['id']==session['student_id'],'class':r['class_name'] if scope=='class' else 'Lớp '+str(r['grade_id']),
                     'mascot':mascot_code(r['mascot']),'level':(r['xp']-1000)//20+1,'xp':r['xp'],
                     'wins':r['wins'],'losses':r['losses']} for i,r in enumerate(rows)]}


def arena_discipline(db, student_id):
    clock = time.time()
    row = db.execute('SELECT count(*) abandons,coalesce(sum(is_strike),0) strikes,'
                     'coalesce(max(cooldown_until),0) available FROM arena_discipline_events '
                     'WHERE student_id=? AND occurred_at>?', (student_id, clock - 86400)).fetchone()
    free = not db.execute('SELECT 1 FROM arena_discipline_events WHERE student_id=? '
                          'AND kind=\'disconnect\' AND occurred_at>? LIMIT 1',
                          (student_id, clock - 86400)).fetchone()
    available = row['available'] if row['available'] > clock else 0
    remaining = max(0, int(available - clock + 0.999))
    warning = ('Em đang tạm nghỉ đấu với người. Có thể luyện với máy trong lúc chờ.' if remaining else
               'Hãy chơi trọn trận để cả hai bạn cùng vui nhé.' if row['strikes'] else '')
    return {'availableAt': round(available * 1000), 'remainingSeconds': remaining,
            'recentAbandons': row['abandons'], 'recentStrikes': row['strikes'],
            'warning': warning, 'freeDisconnectAvailable': free}


def _require_arena_available(db, student_id, requester_id=None):
    discipline = arena_discipline(db, student_id)
    if discipline['remainingSeconds']:
        minutes = (discipline['remainingSeconds'] + 59) // 60
        message = (f'Em cần nghỉ đấu với người thêm {minutes} phút vì đã rời trận nhiều lần.'
                   if requester_id in (None, student_id) else
                   'Bạn chơi đang tạm nghỉ đấu với người. Em hãy chọn một phòng khác.')
        error = APIError(message, 429)
        error.arenaDiscipline = arena_discipline(db, requester_id or student_id)
        raise error


def _settle_arena_results(db, arena):
    """Settle every terminal room, including one abandoned without a peer poll.

    The caller holds arena.lock and the SQLite write transaction. result_json
    and the event's unique key make all XP, refunds and strikes idempotent.
    """
    changed = False
    rooms = list(arena.rooms.values()) + list(arena.retired.values())
    for room in rooms:
        if room['status'] not in ('finished', 'cancelled'):
            continue
        members = list(db.execute('SELECT * FROM arena_members WHERE room_id=?', (room['id'],)))
        if not members:
            continue
        did = members[0]['duel_id']
        duel = db.execute('SELECT status,ended_at FROM duels WHERE id=?', (did,)).fetchone()
        if room['status'] == 'cancelled':
            if not duel['ended_at']:
                db.execute('UPDATE duels SET status=\'abandoned\',ended_at=? WHERE id=?', (stamp(), did))
                db.execute('DELETE FROM daily_usage WHERE category=\'human\' AND request_key=?', (room['id'],))
                changed = True
            elif room['id'] in arena.retired:
                arena.retired.pop(room['id'], None)
            continue
        if all(record['result_json'] for record in members):
            arena.retired.pop(room['id'], None)
            continue
        incomplete = room['interrupted']
        db.execute('UPDATE duels SET status=?,ended_at=coalesce(ended_at,?) WHERE id=?',
                   ('abandoned' if incomplete else 'completed', stamp(), did))
        for token, player in room['players'].items():
            digest = hashlib.sha256(token.encode()).hexdigest()
            record = next((m for m in members if m['token_hash'] == digest), None)
            if not record or record['result_json']:
                continue
            sid = record['student_id']
            trusted = arena._view(room, token)['result']
            trusted['id'] = str(did)
            abandoned = token in room.get('abandonedTokens', [])
            penalty = {'kind': None, 'strike': 0, 'cooldownSeconds': 0,
                       'xpDelta': 0, 'disconnectForgiven': False}
            refund = incomplete and not abandoned
            if incomplete and abandoned:
                kind = room.get('endReason', 'disconnect')
                clock = time.time()
                forgiven = kind == 'disconnect' and arena_discipline(db, sid)['freeDisconnectAvailable']
                strike = arena_discipline(db, sid)['recentStrikes'] + (not forgiven)
                delay = 0 if forgiven or strike < 2 else 300 if strike == 2 else 900 if strike == 3 else 3600
                db.execute('INSERT INTO arena_discipline_events '
                           '(student_id,duel_id,kind,occurred_at,is_strike,cooldown_until) VALUES (?,?,?,?,?,?)',
                           (sid, did, kind, clock, int(not forgiven), clock + delay if delay else 0))
                trusted.update(outcome='lose', points=0 if forgiven else -1)
                penalty.update(kind=kind, strike=strike, cooldownSeconds=delay,
                               disconnectForgiven=forgiven)
            elif incomplete:
                trusted.update(outcome='win', points=0)
            if refund:
                db.execute('DELETE FROM daily_usage WHERE student_id=? AND category=\'human\' AND request_key=?',
                           (sid, room['id']))
            xp = db.execute('SELECT xp FROM student_companions WHERE student_id=?', (sid,)).fetchone()[0]
            delta = max(1000, xp + trusted['points']) - xp
            p = db.execute('SELECT id FROM duel_players WHERE duel_id=? AND student_id=?', (did, sid)).fetchone()
            db.execute('INSERT OR IGNORE INTO xp_events(student_id,duel_player_id,delta,awarded_at) VALUES (?,?,?,?)',
                       (sid, p[0], delta, stamp()))
            db.execute('UPDATE student_companions SET xp=? WHERE student_id=?', (xp + delta, sid))
            db.execute('UPDATE duel_players SET outcome=?,hp=? WHERE id=?',
                       (trusted['outcome'], player['hp'], p[0]))
            penalty['xpDelta'] = delta
            trusted.update(points=delta, completed=not incomplete,
                           penalty=penalty, quotaRefunded=refund)
            db.execute('UPDATE arena_members SET result_json=? WHERE token_hash=?', (packed(trusted), digest))
            changed = True
    # Runtime rooms are deliberately not restored after a server restart. Such
    # cancellation is neither player's fault: return both reserved attempts.
    live_ids = {r['id'] for r in list(arena.rooms.values()) + list(arena.retired.values())}
    orphaned = list(db.execute("SELECT d.id,d.grade_id,m.room_id FROM duels d "
                               "JOIN arena_members m ON m.duel_id=d.id "
                               "WHERE d.status IN ('waiting','active') AND d.ended_at IS NULL "
                               "AND json_extract(d.settings_json,'$.runtime')='local-python' GROUP BY d.id,m.room_id"))
    for duel in orphaned:
        if duel['room_id'] in live_ids:
            continue
        db.execute("UPDATE duels SET status='abandoned',ended_at=? WHERE id=?", (stamp(), duel['id']))
        db.execute("DELETE FROM daily_usage WHERE category='human' AND request_key=?", (duel['room_id'],))
        cancelled = {'id':str(duel['id']), 'grade':duel['grade_id'], 'mode':'player',
                     'outcome':'left', 'points':0, 'correct':0, 'rounds':0, 'review':[],
                     'completed':False, 'reason':'server_restart', 'quotaRefunded':True,
                     'penalty':{'kind':None, 'strike':0, 'cooldownSeconds':0,
                                'xpDelta':0, 'disconnectForgiven':False}}
        db.execute('UPDATE arena_members SET result_json=? WHERE duel_id=? AND result_json IS NULL',
                   (packed(cancelled), duel['id']))
        changed = True
    return changed


def _arena_preflight(db, arena, session, credentials=None):
    # Only an authenticated member's token may renew presence before cleanup.
    arena.handle({'action': 'list', 'grade': 0, 'accountId': session['account_id'], **(credentials or {})})
    with arena.lock:
        changed = _settle_arena_results(db, arena)
    if changed:
        # Finalizing previous matches is independent of the next admission.
        # A rejected admission must not roll back that completed settlement.
        db.commit()
        db.execute('BEGIN IMMEDIATE')


def arena_request(handler, db, session, body):
    from .arena import ArenaError
    from .learning_update import consume, usage
    arena = handler.server.arena
    action=body.get('action')
    payload=dict(body)
    grade,_=ensure_grade(db,session['student_id'],session['birth_year'])
    payload.update(name=safe_nickname(session['full_name']),grade=grade,
                   accountId=session['account_id'],difficulty=0)
    member = None
    entering = action in ('create', 'quick', 'join', 'challenge')
    if not entering and action != 'list':
        token=body.get('token')
        if not isinstance(token,str): raise APIError('Phiên phòng không hợp lệ.',403)
        member=db.execute('SELECT * FROM arena_members WHERE token_hash=? AND student_id=? AND revoked_at IS NULL',
                          (hashlib.sha256(token.encode()).hexdigest(),session['student_id'])).fetchone()
        if not member: raise APIError('Phòng không thuộc tài khoản đang đăng nhập.',403)
    _arena_preflight(db, arena, session,
                     {'code': body.get('code'), 'token': body.get('token')} if member else None)
    pet = db.execute('SELECT c.xp,m.name FROM student_companions c JOIN mascots m ON m.id=c.mascot_id WHERE c.student_id=?',
                     (session['student_id'],)).fetchone()
    outcomes = dict(db.execute("SELECT p.outcome,count(*) FROM duel_players p JOIN duels d ON d.id=p.duel_id "
                              "WHERE p.student_id=? AND d.status='completed' GROUP BY p.outcome", (session['student_id'],)))
    xp = pet['xp'] if pet else 1000
    payload['stats'] = {'xp':xp, 'level':(xp-1000)//20+1, 'wins':outcomes.get('win',0),
                        'losses':outcomes.get('lose',0), 'mascot':mascot_code(pet['name'] if pet else None)}
    if action == 'list':
        result = arena.handle({'action': 'list', 'grade': grade, 'accountId': session['account_id']})
        return {**result, 'arenaDiscipline': arena_discipline(db, session['student_id'])}
    if entering:
        _require_arena_available(db, session['student_id'])
    if member:
        cached = db.execute('SELECT result_json FROM arena_members WHERE token_hash=?',
                            (member['token_hash'],)).fetchone()[0]
        if cached and action in ('state', 'leave', 'next', 'answer', 'emote'):
            return {'status': 'finished', 'result': json.loads(cached),
                    'arenaDiscipline': arena_discipline(db, session['student_id'])}
        if action=='accept':
            with arena.lock:
                room=arena.rooms.get(body.get('code'))
                valid=room and room['status']=='challenged' and room['host']==token and time.time()<room['challengeUntil']
            if valid:
                records = list(db.execute('SELECT m.student_id,s.account_id FROM arena_members m JOIN students s ON s.id=m.student_id WHERE m.room_id=?',(member['room_id'],)))
                for record in records:
                    _require_arena_available(db, record['student_id'], session['student_id'])
                for record in records:
                    consume(db,record,'human',member['room_id'])
    else:
        remaining=usage(db,session)['human']
        if remaining['limit'] is not None and remaining['used']>=remaining['limit']:
            raise APIError('Em đã dùng hết 3 lượt đấu với bạn hôm nay. Vào Nâng cấp gói để tiếp tục.',429)
        code=body.get('code','')
        if isinstance(code,str) and action=='join':
            with arena.lock:
                room=arena.rooms.get(code.upper())
                room_id=room['id'] if room else ''
            if db.execute('SELECT 1 FROM arena_members WHERE room_id=? AND student_id=?',(room_id,session['student_id'])).fetchone():
                raise APIError('Một tài khoản không thể tham gia hai bên của cùng trận.')
        if action=='quick':
            # Prevent matching the same account with its own waiting room.
            own={r[0] for r in db.execute('SELECT room_id FROM arena_members WHERE student_id=?',(session['student_id'],))}
            with arena.lock:
                if any(r['id'] in own and r['status']=='waiting' and r['public'] for r in arena.rooms.values()):
                    raise APIError('Em đang có phòng chờ. Hãy quay lại phòng đó hoặc rời phòng trước.')
    try:
        from .question_bank import arena_questions
        result=arena.handle(payload, question_provider=lambda g,d,s: arena_questions(db,g,d,s,academic()[1]))
    except ArenaError as error:
        raise APIError(str(error),error.status)
    code=result.get('code') or body.get('code')
    with arena.lock:
        room=arena.rooms.get(code)
        if not room: raise APIError('Phòng đã hết hạn.',404)
        if action in ('create','quick','join'):
            existing=db.execute('SELECT duel_id FROM arena_members WHERE room_id=? LIMIT 1',(room['id'],)).fetchone()
            if existing:
                did=existing[0]
            else:
                did=db.execute('INSERT INTO duels(grade_id,mode,join_code,status,difficulty,curriculum_mode,settings_json,created_at) '
                               'VALUES (?,?,?,\'waiting\',?,?,?,?)',
                               (grade,'public' if room['public'] else 'friends',room['code'],room['difficulty']+1,
                                'weekly' if room['scope']=='weekly' else 'exam',packed({'runtime':'local-python'}),stamp())).lastrowid
            slot=len(room['players'])
            db.execute('INSERT INTO arena_members(room_id,token_hash,student_id,duel_id) VALUES (?,?,?,?)',
                       (room['id'],hashlib.sha256(result['token'].encode()).hexdigest(),session['student_id'],did))
            db.execute('INSERT INTO duel_players(duel_id,student_id,slot) VALUES (?,?,?)',(did,session['student_id'],slot))
        else:
            did=member['duel_id']
        if room['status'] in ('playing','preparing'):
            db.execute('UPDATE duels SET status=\'active\',started_at=coalesce(started_at,?) WHERE id=?',(stamp(),did))
        _settle_arena_results(db, arena)
        if result.get('result'):
            cached = db.execute('SELECT result_json FROM arena_members WHERE token_hash=?',
                                (member['token_hash'],)).fetchone()[0]
            if cached:
                result['result'] = json.loads(cached)
    result['arenaDiscipline'] = arena_discipline(db, session['student_id'])
    return result


def read_needs_maintenance(handler, path):
    """Reserve a writer only for due work, rather than every session poll."""
    state_request = path in ('/api/v1/session', '/api/v1/state')
    exam_match = re.fullmatch(r'/api/v1/exams/(\d+)', path)
    if not state_request and not exam_match and path != '/api/v1/leaderboard':
        return False
    with connect(handler.server.database_path) as db:
        session = read_session(handler, db)
        if not session:
            return False
        if state_request or path == '/api/v1/leaderboard':
            year = academic()[0]
            if not db.execute('SELECT 1 FROM student_grades g JOIN academic_years y ON y.id=g.academic_year_id '
                              'WHERE g.student_id=? AND y.label=?',
                              (session['student_id'], f'{year}–{year+1}')).fetchone():
                return True
        if state_request and db.execute("SELECT 1 FROM exam_attempts WHERE student_id=? AND status='in_progress' AND due_at<=? LIMIT 1",
                                       (session['student_id'], stamp())).fetchone():
            return True
        if exam_match and db.execute("SELECT 1 FROM exam_attempts WHERE student_id=? AND exam_id=? AND status='in_progress' AND due_at<=?",
                                    (session['student_id'], int(exam_match[1]), stamp())).fetchone():
            return True
        if not state_request:
            return False
        arena = handler.server.arena
        arena.handle({'action': 'list', 'grade': 0, 'accountId': session['account_id']})
        with arena.lock:
            rooms = list(arena.rooms.values()) + list(arena.retired.values())
            live_ids = {room['id'] for room in rooms}
            for room in rooms:
                if room['status'] not in ('finished', 'cancelled'):
                    continue
                members = list(db.execute('SELECT m.result_json,d.ended_at FROM arena_members m '
                                          'JOIN duels d ON d.id=m.duel_id WHERE m.room_id=?', (room['id'],)))
                if members and (room['status'] == 'cancelled' and not members[0]['ended_at'] or
                                room['status'] == 'finished' and any(not member['result_json'] for member in members)):
                    return True
                if members:
                    arena.retired.pop(room['id'], None)
            return any(row['room_id'] not in live_ids for row in db.execute(
                "SELECT m.room_id FROM duels d JOIN arena_members m ON m.duel_id=d.id "
                "WHERE d.status IN ('waiting','active') AND d.ended_at IS NULL "
                "AND json_extract(d.settings_json,'$.runtime')='local-python'"))


def dispatch(handler, method, path, body=None):
    """Return payload, status. Header mutation is limited to the session cookie."""
    body = body or {}
    if path.startswith('/api/v1/admissions'):
        from .admissions import dispatch as admissions_dispatch
        return admissions_dispatch(handler, method, path, body)
    payment_match = re.fullmatch(r'/api/v1/payments/(\d+)', path)
    if method == 'GET' and payment_match:
        from .payments import order_status
        with connect(handler.server.database_path) as db:
            session = read_session(handler, db)
            if not session:
                raise APIError('Em hãy đăng nhập để tiếp tục.', 401)
            return order_status(db, session, int(payment_match[1])), 200
    if method=='GET' and path in ('/api/v1/notifications','/api/v1/referrals'):
        from .notifications import inbox, page_number, referrals
        with connect(handler.server.database_path) as db:
            session = read_session(handler,db)
            if not session:
                raise APIError('Em hãy đăng nhập để tiếp tục.',401)
            fn = inbox if path.endswith('/notifications') else referrals
            return fn(db,session['account_id'],page_number(handler.path)),200
    if method=='POST':
        if not same_origin(handler):
            raise APIError('Yêu cầu phải xuất phát từ website đang mở.',403)
    review = getattr(handler.server,'review_upgrades',False)
    credential = login_proof = None
    if method == 'POST' and path in ('/api/v1/auth/register', '/api/v1/auth/login'):
        limit_auth(handler)
        if path.endswith('/register'):
            credential = password_hash(body.get('password'))
        else:
            login_proof = prepare_login(handler.server.database_path, body)
    compact = path in ('/api/v1/auth/login','/api/v1/auth/register','/api/v1/session') and parse_qs(urlsplit(handler.path).query).get('view') == ['identity']
    write = method == 'POST' or method == 'GET' and not compact and read_needs_maintenance(handler, path)
    with connect(handler.server.database_path, write) as db:
        session = read_session(handler,db)
        if path in ('/api/v1/auth/register','/api/v1/auth/login') and method=='POST':
            if path.endswith('/register'):
                session = register(handler,db,body,credential)
            else:
                account = verified_login(db, login_proof)
                if login_proof[0] == 'staff':
                    # The homepage form is shared; staff still receive their own
                    # cookie and never gain a student session through this route.
                    from .staff_api import issue_session as issue_staff_session
                    return {**issue_staff_session(handler, db, account), 'principal': 'staff'}, 200
                session = issue_session(handler,db,account['id'])
            return (identity_view(db,session) if compact else state_view(db,session,review)),200
        if path=='/api/v1/session' and method=='GET' and not session:
            return {'authenticated':False},200
        if not session:
            raise APIError('Em hãy đăng nhập để tiếp tục.',401)
        if method=='POST' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),session['csrf_token']):
            raise APIError('Phiên đăng nhập cần được tải lại.',403)
        from .system_settings import require_feature
        if method=='POST' and path=='/api/v1/exams':
            require_feature(db, 'practice_open')
        if method=='POST' and path.startswith('/api/v1/lessons/'):
            require_feature(db, 'learning_open')
        if method=='GET' and path=='/api/v1/leaderboard':
            require_feature(db, 'leaderboard_open')
        if method=='POST' and path=='/api/v1/bot/start':
            require_feature(db, 'arena_open')
        if method=='POST' and path=='/api/v1/arena' and body.get('action') in ('create','quick','join','challenge'):
            require_feature(db, 'arena_open')
        if method=='GET' and path in ('/api/v1/session','/api/v1/state'):
            if write:
                _arena_preflight(db, handler.server.arena, session)
            return (identity_view(db,session) if compact else state_view(db,session,review,read_only=not write)),200
        if method=='POST' and path=='/api/v1/auth/logout':
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(session['token_hash'],))
            handler.api_headers={'Set-Cookie': session_cookie(COOKIE, '', 0)}
            return {'authenticated':False},200
        if method=='POST' and path=='/api/v1/profile':
            if set(body)-{'name'}: raise APIError('Chỉ được đổi tên hiển thị. Năm sinh đã cố định.')
            db.execute('UPDATE students SET full_name=? WHERE id=?',(nickname_field(body),session['student_id']))
            db.execute('UPDATE accounts SET revision=revision+1 WHERE id=?',(session['account_id'],))
        elif method=='POST' and path=='/api/v1/mascot':
            pet=body.get('mascot')
            if not isinstance(pet,str) or pet not in MASCOT_NAMES: raise APIError('Linh vật không hợp lệ.')
            db.execute('UPDATE student_companions SET mascot_id=(SELECT id FROM mascots WHERE name=?) WHERE student_id=?',
                       (MASCOT_NAMES[pet],session['student_id']))
        elif method=='POST' and path=='/api/v1/preferences':
            if (not isinstance(body,dict) or set(body) != {'theme'} or
                    not isinstance(body['theme'],str) or body['theme'] not in LEARNING_THEMES):
                raise APIError('Em hãy chọn một giao diện có sẵn.')
            db.execute('INSERT INTO learning_preferences(student_id,theme) VALUES (?,?) '
                       'ON CONFLICT(student_id) DO UPDATE SET theme=excluded.theme',
                       (session['student_id'],body['theme']))
        elif method=='POST' and re.fullmatch(r'/api/v1/lessons/[a-z0-9-]+/(complete|open)',path):
            lesson=db.execute("SELECT id,grade_id FROM lessons WHERE client_key=? AND publication_status='published'",(path.split('/')[4],)).fetchone()
            grade,_=ensure_grade(db,session['student_id'],session['birth_year'])
            if not lesson or lesson['grade_id']!=grade: raise APIError('Bài học không thuộc khối của em.',404)
            db.execute('INSERT INTO learning_preferences(student_id,last_lesson) VALUES (?,?) '
                       'ON CONFLICT(student_id) DO UPDATE SET last_lesson=excluded.last_lesson',(session['student_id'],path.split('/')[4]))
            if path.endswith('/complete'):
                db.execute('INSERT OR IGNORE INTO lesson_progress VALUES (?,?,?)',(session['student_id'],lesson['id'],stamp()))
        elif method=='POST' and path=='/api/v1/exams':
            return {'exam':create_exam(db,session,body)},200
        elif re.fullmatch(r'/api/v1/exams/\d+(/answers|/submit)?',path):
            attempt=owned_attempt(db,session,int(path.split('/')[4]))
            expired=attempt['due_at']<=stamp()
            if method=='POST' and path.endswith('/answers') and attempt['status']!='submitted' and not expired:
                position,answer=body.get('position'),body.get('answer')
                if type(position) is not int or not isinstance(answer,str) or len(answer)>500:
                    raise APIError('Câu trả lời không hợp lệ.')
                item=db.execute('SELECT options_json FROM exam_items WHERE exam_id=? AND position=?',(attempt['exam_id'],position)).fetchone()
                if not item or answer not in json.loads(item[0]): raise APIError('Đáp án không nằm trong lựa chọn của câu hỏi.')
                db.execute('INSERT INTO exam_draft_answers VALUES (?,?,?,?,?) ON CONFLICT(attempt_id,position) '
                           'DO UPDATE SET answer=excluded.answer,saved_at=excluded.saved_at',
                           (attempt['id'],attempt['exam_id'],position,answer,stamp()))
                db.execute('UPDATE exam_attempts SET cursor=? WHERE id=?',(position-1,attempt['id']))
            elif method=='POST' and not path.endswith('/submit') and not path.endswith('/answers'):
                raise APIError('Thao tác không hợp lệ.',404)
            if expired or (method=='POST' and path.endswith('/submit')):
                if not write:
                    # The deadline may pass between the read preflight and view.
                    db.execute('BEGIN IMMEDIATE')
                    attempt=owned_attempt(db,session,attempt['exam_id'])
                submit(db,attempt)
            return {'exam':exam_view(db,owned_attempt(db,session,attempt['exam_id']))},200
        elif method=='GET' and path=='/api/v1/leaderboard':
            return leaderboard(db,session,parse_qs(urlsplit(handler.path).query)),200
        elif method=='GET' and path=='/api/v1/classes/unread':
            from .zoom_classroom import unread_summary
            return {'classroomUnread':unread_summary(db,session)},200
        elif method=='GET' and re.fullmatch(r'/api/v1/class-submissions/\d+/file',path):
            from .zoom_classroom import file_payload
            return file_payload(db,int(path.split('/')[4]),session=session),200
        elif method=='POST' and re.fullmatch(r'/api/v1/classes/\d+/read',path):
            from .zoom_classroom import mark_read
            return mark_read(db,session,int(path.split('/')[4]),body),200
        elif method=='POST' and re.fullmatch(r'/api/v1/classes/\d+/assignments/\d+/submissions',path):
            from .zoom_classroom import submit_file
            return submit_file(db,session,int(path.split('/')[4]),int(path.split('/')[6]),body),200
        elif method=='GET' and re.fullmatch(r'/api/v1/classes/\d+(/ranking)?',path):
            from .learning_update import classroom, class_ranking
            fn=class_ranking if path.endswith('/ranking') else classroom
            return fn(db,session,int(path.split('/')[4]),parse_qs(urlsplit(handler.path).query)),200
        elif method=='POST' and path=='/api/v1/payments':
            from .learning_update import payment
            return payment(db,session,body),200
        elif method=='POST' and path=='/api/v1/bot/start':
            from .learning_update import consume
            consume(db,session,'bot',text_field(body,'requestKey',80,8))
            return {'status':'started'},200
        elif method=='GET' and path=='/api/v1/materials':
            from .learning_update import membership
            if membership(db,session)=='Free': raise APIError('Tải tài liệu dành cho VIP và SVip.',403)
            return {'title':'Phiếu luyện tập tự biên soạn','text':'5BMath — Phiếu luyện tập mẫu\n1. Tính 25% của 240.\n2. Hình chữ nhật dài 18 cm, rộng 9 cm. Tính diện tích.\n3. So sánh 2,35 và 2,305.\n\nĐáp án: 60; 162 cm²; 2,35 > 2,305.'},200
        elif method=='POST' and path=='/api/v1/arena':
            return arena_request(handler,db,session,body),200
        elif method=='POST' and path=='/api/v1/heartbeat':
            latest=db.execute('SELECT * FROM online_intervals WHERE student_id=? ORDER BY id DESC LIMIT 1',(session['student_id'],)).fetchone()
            current=stamp()
            if latest and latest['ended_at'] is None and latest['last_seen_at']>=stamp(now()-timedelta(seconds=75)):
                db.execute('UPDATE online_intervals SET last_seen_at=? WHERE id=?',(current,latest['id']))
            else:
                if latest and latest['ended_at'] is None:
                    db.execute('UPDATE online_intervals SET ended_at=last_seen_at WHERE id=?',(latest['id'],))
                db.execute('INSERT INTO online_intervals(student_id,started_at,last_seen_at) VALUES (?,?,?)',(session['student_id'],current,current))
            return {'status':'saved'},200
        elif method=='POST' and re.fullmatch(r'/api/v1/notifications/\d+/read',path):
            from .notifications import read_notice
            selected = read_notice(db,session['account_id'],int(path.split('/')[4]))
            return {**state_view(db,session,review),'notification':selected},200
        elif method=='POST' and path=='/api/v1/dev/upgrade' and review:
            # Explicit opt-in local review only, never a payment webhook.
            key=text_field(body,'requestKey',80,8)
            db.execute('INSERT OR IGNORE INTO vip_purchases(account_id,payment_ref,months,confirmed_at) VALUES (?,?,1,?)',
                       (session['account_id'],'LOCAL-REVIEW-'+str(session['account_id'])+'-'+key,stamp()))
        else:
            raise APIError('API không tồn tại.',404)
        return state_view(db,session,review),200
