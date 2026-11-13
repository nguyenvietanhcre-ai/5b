"""Role-scoped staff tools for classes, content and platform administration."""
import hashlib
import hmac
import json
import math
import re
import secrets
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit
from .platform_api import (APIError, MASCOT_NAMES, MASCOT_DISPLAY_NAMES, VN, academic, connect, limit_auth, mascot_code, now, packed,
                           ensure_grade, nickname_field, password_hash, stamp,
                           text_field, verify_password, same_origin, session_cookie,
                           prepare_login, verified_login)
from .system_settings import settings
from .nickname_policy import safe_nickname

COOKIE = '5bmath_staff'


def number(body, key, minimum=1, maximum=2**31-1):
    value = body.get(key)
    if type(value) is not int or not minimum <= value <= maximum:
        raise APIError(f'Thông tin {key} không hợp lệ.')
    return value


def url_field(body, key):
    value = text_field(body, key, 2000, 0)
    if value:
        try:
            parsed = urlsplit(value)
        except ValueError:
            raise APIError('Liên kết không hợp lệ.')
        if (parsed.username or parsed.password or '\\' in value or any(ord(c) < 32 for c in value) or
                not ((parsed.scheme in ('http', 'https') and parsed.netloc) or
                     (value.startswith('/') and not value.startswith('//')))):
            raise APIError('Liên kết cần bắt đầu bằng https://, http:// hoặc đường dẫn trên website.')
    return value


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            result = result.replace(tzinfo=VN)
        return stamp(result)
    except (AttributeError, ValueError, OverflowError):
        raise APIError('Ngày giờ buổi học không hợp lệ.')


def get_row(db, table, identity):
    # The table name comes only from the literal call sites in this module.
    row = db.execute(f'SELECT * FROM {table} WHERE id=?', (identity,)).fetchone()
    if not row:
        raise APIError('Không tìm thấy dữ liệu.', 404)
    return row


def check_revision(row, body):
    if type(body.get('revision')) is not int or body['revision'] != row['revision']:
        raise APIError('Dữ liệu vừa được cập nhật ở nơi khác. Tải lại rồi lưu thay đổi.', 409)


def audit(db, user, action, entity, identity, summary):
    db.execute('INSERT INTO staff_audit_log(staff_id,action,entity,entity_id,summary,created_at) VALUES (?,?,?,?,?,?)',
               (user['id'], action, entity, str(identity), summary[:500], stamp()))


def public_user(row):
    return {key: row[key] for key in ('id', 'login', 'full_name', 'role', 'teacher_id', 'status', 'revision')}


def read_session(handler, db):
    cookie = SimpleCookie()
    try:
        cookie.load(handler.headers.get('Cookie', ''))
        token = cookie[COOKIE].value if COOKIE in cookie else ''
    except Exception:
        token = ''
    return db.execute('SELECT u.*,s.token_hash,s.csrf_token FROM staff_sessions s '
                      "JOIN staff_users u ON u.id=s.staff_id WHERE s.token_hash=? AND s.expires_at>? AND u.status='active'",
                      (hashlib.sha256(token.encode()).hexdigest(), stamp())).fetchone()


def issue_session(handler, db, user):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute('DELETE FROM staff_sessions WHERE expires_at<=?', (stamp(),))
    db.execute('INSERT INTO staff_sessions VALUES (?,?,?,?)',
               (hashlib.sha256(token.encode()).hexdigest(), user['id'], csrf, stamp(now()+timedelta(hours=12))))
    handler.api_headers = {'Set-Cookie': session_cookie(COOKIE, token, 43200)}
    return {'authenticated': True, 'csrf': csrf, 'user': public_user(user)}


def create_first_admin(path, login, name, password):
    if not isinstance(login, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.@+-]{2,99}', login):
        raise APIError('Tên đăng nhập cần ít nhất ba ký tự không dấu.')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise APIError('Tên quản trị không hợp lệ.')
    credential = password_hash(password)
    with connect(path, True) as db:
        if db.execute("SELECT 1 FROM staff_users WHERE role='admin'").fetchone():
            raise APIError('Đã có admin. Dùng trang Quản trị để cấp tài khoản tiếp theo.', 409)
        identity = db.execute("INSERT INTO staff_users(login,full_name,password_hash,role,created_at) VALUES (?,?,?,'admin',?)",
                              (login.lower(), name.strip(), credential, stamp())).lastrowid
        audit(db, {'id': identity}, 'create', 'staff', identity, 'Khởi tạo quản trị viên đầu tiên')
        return identity


def require_admin(user):
    if user['role'] != 'admin':
        raise APIError('Chức năng dành cho quản trị viên.', 403)


def classroom(db, user, identity):
    row = get_row(db, 'online_classes', identity)
    if user['role'] != 'admin' and row['teacher_id'] != user['teacher_id']:
        raise APIError('Lớp không thuộc phân công của giáo viên.', 403)
    return row


def session_class(db, user, identity):
    row = get_row(db, 'class_sessions', identity)
    classroom(db, user, row['class_id'])
    return row


def classes(db, user):
    return [dict(row) for row in db.execute(
        'SELECT c.*,t.full_name teacher,y.label academic_year,'
        '(SELECT count(*) FROM class_enrollments e WHERE e.class_id=c.id AND e.left_at IS NULL) student_count,'
        '(SELECT min(s.starts_at) FROM class_sessions s WHERE s.class_id=c.id AND s.starts_at>=?) next_session '
        'FROM online_classes c JOIN teachers t ON t.id=c.teacher_id JOIN academic_years y ON y.id=c.academic_year_id '
        "WHERE (?='admin' OR c.teacher_id=?) ORDER BY c.status,c.grade_id,c.name",
        (stamp(), user['role'], user['teacher_id']))]


def class_detail(db, user, identity):
    from .zoom_classroom import attendance_rows, score_rows, session_submissions
    info = dict(classroom(db, user, identity))
    info['teacher'] = get_row(db, 'teachers', info['teacher_id'])['full_name']
    roster = [dict(row) for row in db.execute(
        'SELECT s.id,s.full_name,s.grade_level,s.account_id,a.login_identifier FROM class_enrollments e '
        'JOIN students s ON s.id=e.student_id LEFT JOIN accounts a ON a.id=s.account_id '
        'WHERE e.class_id=? AND e.left_at IS NULL ORDER BY s.full_name,s.id', (identity,))]
    for student in roster:
        student['full_name'] = safe_nickname(student['full_name'])
    sessions = [dict(row) for row in db.execute(
        'SELECT * FROM class_sessions WHERE class_id=? ORDER BY starts_at DESC,id DESC LIMIT 150', (identity,))]
    for item in sessions:
        item['assignments'] = [dict(row) for row in db.execute(
            'SELECT * FROM class_assignments WHERE session_id=? ORDER BY id', (item['id'],))]
        item['attendance'] = attendance_rows(db, item['id'])
        item['scores'] = score_rows(db, item['id'])
        item['submissions'] = session_submissions(db, item['id'])
    fees = [dict(row) for row in db.execute(
        'SELECT f.*,s.full_name FROM class_fees f JOIN students s ON s.id=f.student_id '
        'WHERE f.class_id=? ORDER BY f.month DESC,s.full_name LIMIT 500', (identity,))]
    for fee in fees:
        fee['full_name'] = safe_nickname(fee['full_name'])
    return {'class': info, 'students': roster, 'sessions': sessions, 'fees': fees}


def close_enrollment(db, enrollment):
    end = stamp()
    db.execute('UPDATE class_enrollments SET left_at=? WHERE id=? AND left_at IS NULL', (end, enrollment['id']))
    for row in db.execute('SELECT id,starts_at FROM access_entitlements WHERE enrollment_id=? AND ends_at IS NULL',
                          (enrollment['id'],)).fetchall():
        start = datetime.fromisoformat(row['starts_at'].replace('Z', '+00:00'))
        expiry = stamp(max(now(), start+timedelta(seconds=1)))
        db.execute('UPDATE access_entitlements SET ends_at=? WHERE id=?', (expiry, row['id']))


def save_class(db, user, body):
    require_admin(user)
    identity = body.get('id')
    old = get_row(db, 'online_classes', identity) if identity else None
    if old:
        check_revision(old, body)
    teacher = number(body, 'teacherId')
    get_row(db, 'teachers', teacher)
    grade = number(body, 'grade', 1, 5)
    name = text_field(body, 'name', 120)
    schedule, curriculum = (text_field(body, key, 3000, 0) for key in ('schedule', 'curriculum'))
    meeting = url_field(body, 'meetingUrl')
    status = body.get('status', 'active')
    if status not in ('active', 'closed'):
        raise APIError('Trạng thái lớp không hợp lệ.')
    session_fee = number(body, 'sessionFee', 0, 1_000_000_000) if 'sessionFee' in body else (old['session_fee'] if old else None)
    if old:
        db.execute('UPDATE online_classes SET teacher_id=?,grade_id=?,name=?,schedule=?,curriculum=?,meeting_ref=?,status=?,session_fee=?,revision=revision+1 WHERE id=?',
                   (teacher, grade, name, schedule, curriculum, meeting, status, session_fee, identity))
        if status == 'closed':
            for enrollment in db.execute('SELECT * FROM class_enrollments WHERE class_id=? AND left_at IS NULL', (identity,)).fetchall():
                close_enrollment(db, enrollment)
    else:
        year, _ = academic()
        label = f'{year}–{year+1}'
        db.execute('INSERT OR IGNORE INTO academic_years(label,grade_effective_from,instruction_starts_on,ends_on) VALUES (?,?,?,?)',
                   (label, f'{year}-07-01', f'{year}-09-05', f'{year+1}-06-30'))
        ayid = db.execute('SELECT id FROM academic_years WHERE label=?', (label,)).fetchone()[0]
        identity = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,meeting_ref,status,schedule,curriculum,session_fee) VALUES (?,?,?,?,?,?,?,?,?)',
                              (teacher, grade, ayid, name, meeting, status, schedule, curriculum, session_fee)).lastrowid
    summary = name
    previous_fee = old['session_fee'] if old else None
    if previous_fee != session_fee:
        summary += f' · Học phí/buổi: {previous_fee if previous_fee is not None else "Chưa cấu hình"} → {session_fee}'
    audit(db, user, 'update' if old else 'create', 'class', identity, summary)
    return class_detail(db, user, identity)


def enroll(db, user, identity, body):
    require_admin(user)
    info = classroom(db, user, identity)
    student = get_row(db, 'students', number(body, 'studentId'))
    current = db.execute('SELECT * FROM class_enrollments WHERE student_id=? AND left_at IS NULL', (student['id'],)).fetchone()
    action = body.get('action')
    if action == 'leave':
        if current and current['class_id'] == identity:
            close_enrollment(db, current)
    elif action == 'enroll':
        account = db.execute('SELECT deleted_at FROM accounts WHERE id=?', (student['account_id'],)).fetchone()
        if info['status'] != 'active' or not account or account['deleted_at'] or student['status'] != 'active':
            raise APIError('Chọn lớp đang hoạt động và học sinh có tài khoản.')
        if current and current['class_id'] != identity:
            raise APIError('Học sinh đang thuộc lớp khác. Cho rời lớp hiện tại trước khi chuyển.', 409)
        if not current:
            eid = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                             (student['id'], identity, stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                       (student['account_id'], eid, stamp(now()-timedelta(seconds=1))))
    else:
        raise APIError('Thao tác ghi danh không hợp lệ.')
    audit(db, user, action, 'enrollment', identity, 'Học sinh ' + str(student['id']))
    return class_detail(db, user, identity)


def save_session(db, user, identity, body):
    classroom(db, user, identity)
    title = text_field(body, 'title', 180)
    start = timestamp(body.get('startsAt'))
    video, comment = url_field(body, 'videoUrl'), text_field(body, 'comment', 10000, 0)
    session_id = body.get('id')
    if session_id:
        old = session_class(db, user, session_id)
        if old['class_id'] != identity:
            raise APIError('Buổi học không thuộc lớp này.', 403)
        check_revision(old, body)
        db.execute('UPDATE class_sessions SET title=?,starts_at=?,video_url=?,teacher_comment=?,revision=revision+1 WHERE id=?',
                   (title, start, video, comment, session_id))
    else:
        session_id = db.execute('INSERT INTO class_sessions(class_id,title,starts_at,video_url,teacher_comment) VALUES (?,?,?,?,?)',
                                (identity, title, start, video, comment)).lastrowid
    audit(db, user, 'save', 'session', session_id, title)
    return class_detail(db, user, identity)


def save_assignment(db, user, identity, body):
    session = session_class(db, user, identity)
    title, kind = text_field(body, 'title', 180), text_field(body, 'kind', 80)
    document = url_field(body, 'documentUrl')
    assignment_id = body.get('id')
    if assignment_id:
        old = get_row(db, 'class_assignments', assignment_id)
        if old['session_id'] != identity:
            raise APIError('Bài tập không thuộc buổi học.', 403)
        check_revision(old, body)
        db.execute('UPDATE class_assignments SET title=?,kind=?,document_url=?,revision=revision+1 WHERE id=?',
                   (title, kind, document, assignment_id))
    else:
        assignment_id = db.execute('INSERT INTO class_assignments(session_id,title,kind,document_url) VALUES (?,?,?,?)',
                                   (identity, title, kind, document)).lastrowid
        from .zoom_classroom import create_notices
        create_notices(db, session['class_id'], 'assignments', assignment_id)
    db.execute('UPDATE class_sessions SET revision=revision+1 WHERE id=?', (identity,))
    audit(db, user, 'save', 'assignment', assignment_id, title)
    return class_detail(db, user, session['class_id'])


def save_records(db, user, identity, body):
    session = session_class(db, user, identity)
    check_revision(session, body)
    roster = {row[0] for row in db.execute('SELECT student_id FROM class_enrollments WHERE class_id=? AND left_at IS NULL',
                                          (session['class_id'],))}
    assignments = {row[0] for row in db.execute('SELECT id FROM class_assignments WHERE session_id=?', (identity,))}
    attendance, scores = body.get('attendance', []), body.get('scores', [])
    if not isinstance(attendance, list) or not isinstance(scores, list) or len(attendance) + len(scores) > 3000:
        raise APIError('Danh sách điểm danh hoặc điểm không hợp lệ.')
    for row in attendance:
        if not isinstance(row, dict) or type(row.get('studentId')) is not int or row['studentId'] not in roster or row.get('status') not in (None, 'charged', 'free', 'absent'):
            raise APIError('Điểm danh cần thuộc học sinh trong lớp.')
        if 'status' in row:
            if row['status'] is None:
                db.execute('DELETE FROM class_attendance WHERE session_id=? AND student_id=?', (identity, row['studentId']))
            else:
                db.execute('INSERT INTO class_attendance VALUES (?,?,?) ON CONFLICT(session_id,student_id) DO UPDATE SET status=excluded.status',
                           (identity, row['studentId'], row['status']))
        if 'comment' in row:
            comment = text_field(row, 'comment', 10000, 0)
            db.execute('INSERT INTO class_session_comments VALUES (?,?,?) '
                       'ON CONFLICT(session_id,student_id) DO UPDATE SET comment=excluded.comment',
                       (identity, row['studentId'], comment))
    for row in scores:
        if not isinstance(row, dict) or type(row.get('studentId')) is not int or row['studentId'] not in roster or type(row.get('assignmentId')) is not int or row['assignmentId'] not in assignments:
            raise APIError('Điểm cần thuộc bài tập và học sinh của buổi học.')
        value = row.get('score')
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 10):
            raise APIError('Điểm cần trong khoảng 0–10.')
        if 'score' in row:
            if value is None:
                db.execute('DELETE FROM class_scores WHERE assignment_id=? AND student_id=?', (row['assignmentId'], row['studentId']))
            else:
                db.execute('INSERT INTO class_scores VALUES (?,?,?) ON CONFLICT(assignment_id,student_id) DO UPDATE SET score=excluded.score',
                           (row['assignmentId'], row['studentId'], value))
        if 'comment' in row:
            comment = text_field(row, 'comment', 10000, 0)
            db.execute('INSERT INTO class_assignment_comments VALUES (?,?,?) '
                       'ON CONFLICT(assignment_id,student_id) DO UPDATE SET comment=excluded.comment',
                       (row['assignmentId'], row['studentId'], comment))
    db.execute('UPDATE class_sessions SET revision=revision+1 WHERE id=?', (identity,))
    audit(db, user, 'save', 'class_records', identity, f'{len(attendance)} điểm danh, {len(scores)} điểm')
    return class_detail(db, user, session['class_id'])


def save_fee(db, user, identity, body):
    require_admin(user)
    info = classroom(db, user, identity)
    check_revision(info, body)
    student, amount = number(body, 'studentId'), number(body, 'amount', 0, 1_000_000_000)
    month = text_field(body, 'month', 7, 7)
    try:
        datetime.strptime(month, '%Y-%m')
    except ValueError:
        raise APIError('Tháng học phí không hợp lệ.')
    if not db.execute('SELECT 1 FROM class_enrollments WHERE class_id=? AND student_id=? AND left_at IS NULL', (identity, student)).fetchone():
        raise APIError('Học sinh cần đang theo học lớp này.')
    old = db.execute('SELECT * FROM class_fees WHERE class_id=? AND student_id=? AND month=?', (identity, student, month)).fetchone()
    if old and (old['paid_at'] or db.execute("SELECT 1 FROM payment_orders WHERE fee_id=? AND status='paid'", (old['id'],)).fetchone()):
        raise APIError('Học phí đã đối soát. Giữ lịch sử thanh toán đã ghi nhận.', 409)
    if old and old['amount'] != amount:
        from .tuition import cancel_pending
        cancel_pending(db, old['id'])
    db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?) '
               "ON CONFLICT(class_id,student_id,month) DO UPDATE SET amount=excluded.amount,source='manual',session_fee=NULL,"
               'charged_count=NULL,free_count=NULL,absent_count=NULL,pending_count=NULL,sessions_json=NULL,calculation_id=NULL,calculated_at=NULL',
               (identity, student, month, amount))
    if not old or old['amount'] != amount:
        from .zoom_classroom import create_notices
        fee_id = db.execute('SELECT id FROM class_fees WHERE class_id=? AND student_id=? AND month=?',
                            (identity, student, month)).fetchone()[0]
        create_notices(db, identity, 'fees', fee_id, student, refresh=bool(old))
    db.execute('UPDATE online_classes SET revision=revision+1 WHERE id=?', (identity,))
    audit(db, user, 'save', 'class_fee', identity, f'Học sinh {student} · {month} · {amount} đồng')
    return class_detail(db, user, identity)


def page_query(handler):
    query = parse_qs(urlsplit(handler.path).query)
    try:
        page = int(query.get('page', ['1'])[0])
        grade = int(query.get('grade', ['0'])[0])
    except ValueError:
        raise APIError('Bộ lọc không hợp lệ.')
    if page < 1 or page > 100000 or grade not in range(6):
        raise APIError('Bộ lọc không hợp lệ.')
    return query.get('q', [''])[0][:100], grade, page


def accounts(db, handler):
    search, grade, page = page_query(handler)
    status = parse_qs(urlsplit(handler.path).query).get('status', ['all'])[0]
    if status not in ('all', 'active', 'suspended', 'deleted'):
        raise APIError('Bộ lọc trạng thái không hợp lệ.')
    year = academic()[0]
    clause = ('WHERE (?=0 OR min(5,max(1,?-a.birth_year-5))=?) '
              'AND (instr(lower(s.full_name),lower(?))>0 OR instr(lower(a.login_identifier),lower(?))>0) '
              'AND ((?=\'deleted\' AND a.deleted_at IS NOT NULL) '
              'OR (?<>\'deleted\' AND a.deleted_at IS NULL AND (?=\'all\' OR a.status=?)))')
    values = (grade, year, grade, search, search, status, status, status, status)
    total = db.execute('SELECT count(*) FROM accounts a JOIN students s ON s.account_id=a.id ' + clause, values).fetchone()[0]
    rows = db.execute('SELECT a.id,a.login_identifier,a.birth_year,a.status,a.vip_expires_at,a.is_demo,a.revision,a.deleted_at,'
                      's.id student_id,s.full_name,min(5,max(1,?-a.birth_year-5)) grade_level,'
                      "(SELECT c.name FROM online_classes c JOIN class_enrollments e ON e.class_id=c.id WHERE e.student_id=s.id AND e.left_at IS NULL LIMIT 1) class_name,"
                      "CASE WHEN EXISTS(SELECT 1 FROM access_entitlements x WHERE x.account_id=a.id AND x.starts_at<=? AND (x.ends_at IS NULL OR x.ends_at>?)) THEN 'SVip' "
                      "WHEN a.vip_expires_at>? THEN 'VIP' ELSE 'Free' END membership "
                      'FROM accounts a JOIN students s ON s.account_id=a.id ' + clause + ' ORDER BY a.id DESC LIMIT 25 OFFSET ?',
                      (year, stamp(), stamp(), stamp(), *values, (page-1)*25)).fetchall()
    return {'rows': [account_profile(db, row) for row in rows], 'total': total, 'page': page, 'pageSize': 25,
            'mascots': [{'code': code, 'name': name} for code, name in MASCOT_DISPLAY_NAMES.items()]}


def account_profile(db, row):
    current = stamp()
    grants = db.execute('SELECT ends_at FROM access_entitlements WHERE account_id=? AND starts_at<=? '
                        'AND (ends_at IS NULL OR ends_at>?)', (row['id'], current, current)).fetchall()
    if grants:
        membership = 'SVip'
        expiry = None if any(grant['ends_at'] is None for grant in grants) else max(grant['ends_at'] for grant in grants)
    elif row['vip_expires_at'] and row['vip_expires_at'] > current:
        membership, expiry = 'VIP', row['vip_expires_at']
    else:
        membership, expiry = 'Free', None
    companion = db.execute('SELECT m.name,c.xp FROM student_companions c JOIN mascots m ON m.id=c.mascot_id '
                           'WHERE c.student_id=?', (row['student_id'],)).fetchone()
    return {**dict(row), 'full_name': safe_nickname(row['full_name']),
            'grade_level': max(1, min(5, academic()[0]-row['birth_year']-5)),
            'membership': membership, 'membership_expires_at': expiry,
            'mascot': mascot_code(companion['name'] if companion else None), 'points': companion['xp'] if companion else 1000}


def account_result(db, identity):
    row = db.execute('SELECT a.id,a.login_identifier,a.birth_year,a.status,a.vip_expires_at,a.is_demo,'
                     'a.revision,a.deleted_at,s.id student_id,s.full_name '
                     'FROM accounts a JOIN students s ON s.account_id=a.id WHERE a.id=?', (identity,)).fetchone()
    return {'saved': True, 'account': account_profile(db, row)}


def plan_expiry(body):
    plan = body.get('membership')
    if plan not in ('Free', 'VIP', 'SVip'):
        raise APIError('Gói tài khoản không hợp lệ.')
    value = body.get('membershipExpiresAt')
    if plan == 'Free':
        if value not in (None, ''):
            raise APIError('Gói Free không có ngày hết hạn.')
        return plan, None
    if value in (None, ''):
        if plan == 'VIP':
            raise APIError('Gói VIP cần ngày hết hạn trong tương lai.')
        return plan, None
    try:
        if not isinstance(value, str) or len(value) > 50 or 'T' not in value:
            raise ValueError
        expiry = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if expiry.tzinfo is None:
            raise ValueError
        expiry = stamp(expiry)
    except (TypeError, ValueError, OverflowError):
        raise APIError('Ngày hết hạn gói không hợp lệ. Cần ngày giờ có múi giờ.')
    if expiry <= stamp():
        raise APIError('Ngày hết hạn gói cần ở trong tương lai.')
    return plan, expiry


def end_account_entitlements(db, identity):
    end = stamp()
    db.execute('DELETE FROM access_entitlements WHERE account_id=? AND starts_at>=?', (identity, end))
    db.execute('UPDATE access_entitlements SET ends_at=? WHERE account_id=? AND (ends_at IS NULL OR ends_at>?)',
               (end, identity, end))


def apply_account_plan(db, identity, plan, expiry):
    end_account_entitlements(db, identity)
    db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?', (expiry if plan == 'VIP' else None, identity))
    if plan == 'SVip':
        db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at,ends_at) VALUES (?,'internal',?,?)",
                   (identity, stamp(now()-timedelta(seconds=1)), expiry))


def account_login(db, body, identity=0):
    login = text_field(body, 'login', 100, 3).lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.@+\-]{2,99}', login):
        raise APIError('Tên đăng nhập dùng ít nhất 3 chữ cái không dấu, số hoặc . _ @ + -')
    if (db.execute('SELECT 1 FROM accounts WHERE lower(login_identifier)=? AND id<>?', (login, identity)).fetchone()
            or db.execute('SELECT 1 FROM staff_users WHERE login=?', (login,)).fetchone()):
        raise APIError('Tên đăng nhập này đã được sử dụng.', 409)
    return login


def save_account(db, user, identity, body, prepared_credential=None):
    require_admin(user)
    if set(body) - {'login', 'name', 'birthYear', 'password', 'status', 'revision', 'expectedStatus',
                    'membership', 'membershipExpiresAt', 'mascot', 'points'}:
        raise APIError('Thông tin tài khoản không hợp lệ.')
    old = get_row(db, 'accounts', identity) if identity else None
    if old and old['deleted_at']:
        raise APIError('Tài khoản đã xóa. Khôi phục trước khi chỉnh sửa.', 409)
    legacy_status = old and set(body) <= {'status', 'expectedStatus'}
    if old:
        if legacy_status:
            if body.get('expectedStatus') != old['status'] and body.get('status') != old['status']:
                raise APIError('Trạng thái vừa thay đổi. Tải lại để kiểm tra.', 409)
        else:
            check_revision(old, body)
    before = account_result(db, identity)['account'] if old else None
    birth = body.get('birthYear', old['birth_year'] if old else None)
    year = academic()[0]
    if ('birthYear' in body or not old) and (type(birth) is not int or not 1 <= year-birth-5 <= 5):
        raise APIError('Năm sinh cần tương ứng học sinh khối 1–5 trong năm học hiện tại.')
    plan, expiry = plan_expiry(body) if 'membership' in body else (None, None)
    if 'membershipExpiresAt' in body and plan is None:
        raise APIError('Chọn gói tài khoản trước khi đổi ngày hết hạn.')
    mascot = body.get('mascot', before['mascot'] if before else 'sprout')
    if not isinstance(mascot, str) or mascot not in MASCOT_NAMES:
        raise APIError('Linh vật không hợp lệ.')
    points = body.get('points', before['points'] if before else 1000)
    if type(points) is not int or not 1000 <= points <= 1_000_000_000:
        raise APIError('Kinh nghiệm linh vật cần là số nguyên từ 1.000 đến 1.000.000.000.')
    status = body.get('status', old['status'] if old else 'active')
    if status not in ('active', 'suspended'):
        raise APIError('Trạng thái tài khoản không hợp lệ.')
    status_only = old and set(body) <= {'status', 'expectedStatus', 'revision'}
    if status_only:
        db.execute('UPDATE accounts SET status=?,revision=revision+1 WHERE id=?', (status, identity))
        reset_credentials = False
    else:
        login = account_login(db, body, identity or 0) if 'login' in body or not old else old['login_identifier']
        name = nickname_field(body) if 'name' in body or not old else db.execute(
            'SELECT full_name FROM students WHERE account_id=?', (identity,)).fetchone()[0]
        password = body.get('password', '')
        if not isinstance(password, str):
            raise APIError('Mật khẩu cần từ 6 đến 128 ký tự.')
        credential = (prepared_credential or password_hash(password)) if password or not old else old['password_hash']
        reset_credentials = bool(old and (password or login != old['login_identifier']))
        if old:
            if birth != old['birth_year']:
                db.execute('INSERT INTO admin_birth_year_permits(account_id,staff_id,old_birth_year,new_birth_year) VALUES (?,?,?,?)',
                           (identity, user['id'], old['birth_year'], birth))
                reset_credentials = True
            db.execute('UPDATE accounts SET login_identifier=?,password_hash=?,status=?,birth_year=?,revision=revision+1 WHERE id=?',
                       (login, credential, status, birth, identity))
            db.execute('UPDATE students SET full_name=? WHERE account_id=?', (name, identity))
            if birth != old['birth_year']:
                sid = before['student_id']
                grade, academic_year = ensure_grade(db, sid, birth)
                db.execute('UPDATE students SET grade_level=? WHERE id=?', (grade, sid))
                db.execute('INSERT INTO student_grades(student_id,academic_year_id,grade_id) VALUES (?,?,?) '
                           'ON CONFLICT(student_id,academic_year_id) DO UPDATE SET grade_id=excluded.grade_id',
                           (sid, academic_year, grade))
        else:
            code = secrets.token_hex(8).upper()
            identity = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,'
                                  'created_at,password_hash,status) VALUES (?,?,?,?,?,?,?)',
                                  ('ACC-'+code, login, birth, '5B'+code[:10], stamp(), credential, status)).lastrowid
            sid = db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,?,?)',
                             ('HS-'+code, name, year-birth-5, identity)).lastrowid
            ensure_grade(db, sid, birth)
            db.execute("INSERT OR IGNORE INTO mascots(name) VALUES ('Mầm Sách')")
            db.execute("INSERT INTO student_companions(student_id,mascot_id) SELECT ?,id FROM mascots WHERE name='Mầm Sách'", (sid,))
            db.execute('INSERT INTO learning_preferences(student_id) VALUES (?)', (sid,))
    if not old or mascot != before['mascot'] or points != before['points']:
        sid = before['student_id'] if before else sid
        db.execute('INSERT OR IGNORE INTO mascots(name) VALUES (?)', (MASCOT_NAMES[mascot],))
        db.execute('INSERT INTO student_companions(student_id,mascot_id,xp) '
                   'VALUES (?,(SELECT id FROM mascots WHERE name=?),?) ON CONFLICT(student_id) '
                   'DO UPDATE SET mascot_id=excluded.mascot_id,xp=excluded.xp '
                   'WHERE mascot_id<>excluded.mascot_id OR xp<>excluded.xp', (sid, MASCOT_NAMES[mascot], points))
        if old:
            reset_credentials = True
    if plan is not None:
        plan_changed = not before or plan != before['membership'] or expiry != before['membership_expires_at']
        if not plan_changed and plan == 'Free':
            plan_changed = bool(old['vip_expires_at']) or bool(db.execute(
                'SELECT 1 FROM access_entitlements WHERE account_id=? AND (ends_at IS NULL OR ends_at>?)',
                (identity, stamp())).fetchone())
        if plan_changed:
            apply_account_plan(db, identity, plan, expiry)
    if status == 'suspended' or reset_credentials:
        db.execute('DELETE FROM auth_sessions WHERE account_id=?', (identity,))
        db.execute('UPDATE arena_members SET revoked_at=coalesce(revoked_at,?) '
                   'WHERE student_id IN (SELECT id FROM students WHERE account_id=?)', (stamp(), identity))
    result = account_result(db, identity)
    after = result['account']
    changes = []
    for key, title in [('birth_year', 'Năm sinh'), ('membership', 'Gói'),
                       ('membership_expires_at', 'Hạn gói'), ('mascot', 'Linh vật'), ('points', 'Kinh nghiệm')]:
        if not before or before[key] != after[key]:
            changes.append(f'{title}: {before[key] if before else "—"} → {after[key]}')
    audit(db, user, 'status' if legacy_status else 'update' if old else 'create', 'account', identity,
          ('Cập nhật' if old else 'Tạo') + ' tài khoản học sinh · ' + status + (' · ' + '; '.join(changes) if changes else ''))
    return result


def delete_account(db, user, identity, body):
    require_admin(user)
    old = get_row(db, 'accounts', identity)
    check_revision(old, body)
    if old['deleted_at']:
        raise APIError('Tài khoản đã được xóa.', 409)
    if body.get('confirmLogin') != old['login_identifier']:
        raise APIError('Nhập đúng tên đăng nhập để xác nhận xóa tài khoản.')
    end = stamp()
    db.execute("UPDATE accounts SET status='suspended',deleted_at=?,revision=revision+1 WHERE id=?", (end, identity))
    db.execute("UPDATE students SET status='inactive' WHERE account_id=?", (identity,))
    db.execute('DELETE FROM auth_sessions WHERE account_id=?', (identity,))
    db.execute('UPDATE arena_members SET revoked_at=coalesce(revoked_at,?) '
               'WHERE student_id IN (SELECT id FROM students WHERE account_id=?)', (end, identity))
    db.execute('UPDATE class_enrollments SET left_at=max(joined_at,?) '
               'WHERE student_id IN (SELECT id FROM students WHERE account_id=?) AND left_at IS NULL', (end, identity))
    # Scheduled grants have never taken effect. Cancel them rather than allow
    # one to activate after restoration; keep all grants that have begun.
    db.execute('DELETE FROM access_entitlements WHERE account_id=? AND starts_at>=?', (identity, end))
    db.execute('UPDATE access_entitlements SET ends_at=? WHERE account_id=? AND (ends_at IS NULL OR ends_at>?)',
               (end, identity, end))
    audit(db, user, 'delete', 'account', identity, 'Xóa tài khoản học sinh khỏi danh sách hoạt động; giữ lịch sử')
    return account_result(db, identity)


def restore_account(db, user, identity, body):
    require_admin(user)
    old = get_row(db, 'accounts', identity)
    check_revision(old, body)
    if not old['deleted_at']:
        raise APIError('Tài khoản chưa bị xóa.', 409)
    db.execute("UPDATE accounts SET deleted_at=NULL,status='suspended',revision=revision+1 WHERE id=?", (identity,))
    db.execute("UPDATE students SET status='active' WHERE account_id=?", (identity,))
    audit(db, user, 'restore', 'account', identity, 'Khôi phục tài khoản ở trạng thái tạm khóa; không tự ghi danh lại')
    return account_result(db, identity)


def staff_list(db):
    return [public_user(row) for row in db.execute('SELECT * FROM staff_users ORDER BY role,full_name')]


def save_staff(db, user, body, prepared_credential=None):
    require_admin(user)
    identity = body.get('id')
    old = get_row(db, 'staff_users', identity) if identity else None
    if old:
        check_revision(old, body)
    login = text_field(body, 'login', 100, 3).lower()
    name = text_field(body, 'fullName', 100)
    role, status = body.get('role'), body.get('status', 'active')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.@+-]{2,99}', login) or role not in ('admin', 'teacher') or status not in ('active', 'disabled'):
        raise APIError('Tên đăng nhập, vai trò hoặc trạng thái không hợp lệ.')
    if (db.execute('SELECT 1 FROM staff_users WHERE login=? AND id<>?', (login, identity or 0)).fetchone()
            or db.execute('SELECT 1 FROM accounts WHERE lower(login_identifier)=?', (login,)).fetchone()):
        raise APIError('Tên đăng nhập đã tồn tại.', 409)
    if old and old['role'] == 'admin' and old['status'] == 'active' and (role != 'admin' or status != 'active'):
        if db.execute("SELECT count(*) FROM staff_users WHERE role='admin' AND status='active'").fetchone()[0] <= 1:
            raise APIError('Cần giữ ít nhất một quản trị viên đang hoạt động.')
    credential = (prepared_credential or password_hash(body.get('password'))) if body.get('password') or not old else old['password_hash']
    teacher = old['teacher_id'] if old else None
    selected_teacher = body.get('teacherId', 0)
    if role == 'teacher' and selected_teacher:
        if type(selected_teacher) is not int:
            raise APIError('Hồ sơ giáo viên không hợp lệ.')
        get_row(db, 'teachers', selected_teacher)
        if db.execute('SELECT 1 FROM staff_users WHERE teacher_id=? AND id<>?', (selected_teacher, identity or 0)).fetchone():
            raise APIError('Hồ sơ giáo viên đã gắn với tài khoản khác.', 409)
        teacher = selected_teacher
    if role == 'teacher' and not teacher:
        teacher = db.execute('INSERT INTO teachers(full_name) VALUES (?)', (name,)).lastrowid
    if teacher:
        db.execute('UPDATE teachers SET full_name=? WHERE id=?', (name, teacher))
    teacher = teacher if role == 'teacher' else None
    if old:
        db.execute('UPDATE staff_users SET login=?,full_name=?,role=?,status=?,teacher_id=?,password_hash=?,revision=revision+1 WHERE id=?',
                   (login, name, role, status, teacher, credential, identity))
        if body.get('password') or status == 'disabled':
            db.execute('DELETE FROM staff_sessions WHERE staff_id=?', (identity,))
    else:
        identity = db.execute('INSERT INTO staff_users(login,full_name,role,status,teacher_id,password_hash,created_at) VALUES (?,?,?,?,?,?,?)',
                              (login, name, role, status, teacher, credential, stamp())).lastrowid
    audit(db, user, 'save', 'staff', identity, f'{name} · {role} · {status}')
    return {'users': staff_list(db)}


def intro_text(raw):
    return next((item.get('text', '') for item in json.loads(raw) if item.get('type') == 'text'), '')


def replace_intro(raw, text):
    blocks = json.loads(raw)
    for item in blocks:
        if item.get('type') == 'text':
            item['text'] = text
            return blocks
    return [{'type': 'text', 'text': text}, *blocks]


def content_list(db, handler):
    search, grade, page = page_query(handler)
    query = parse_qs(urlsplit(handler.path).query)
    kind = query.get('kind', ['lessons'])[0]
    topic_rows = [dict(row) for row in db.execute('SELECT id,grade_id,title,client_key FROM topics ORDER BY grade_id,title')]
    if kind == 'topics':
        clause = 'WHERE (?=0 OR grade_id=?) AND instr(lower(title),lower(?))>0'
        values = (grade, grade, search)
        total = db.execute('SELECT count(*) FROM topics ' + clause, values).fetchone()[0]
        rows = [dict(row) for row in db.execute('SELECT * FROM topics ' + clause + ' ORDER BY grade_id,title LIMIT 25 OFFSET ?', (*values, (page-1)*25))]
        for row in rows:
            row['intro'] = intro_text(row['theory_json'])
    elif kind == 'lessons':
        clause = 'WHERE (?=0 OR grade_id=?) AND instr(lower(title),lower(?))>0'
        values = (grade, grade, search)
        total = db.execute('SELECT count(*) FROM lessons ' + clause, values).fetchone()[0]
        rows = [dict(row) for row in db.execute('SELECT * FROM lessons ' + clause + ' ORDER BY grade_id,week_no,id LIMIT 25 OFFSET ?', (*values, (page-1)*25))]
        for row in rows:
            row['intro'] = intro_text(row['body_json'])
            try:
                presentation = json.loads(row['presentation_json'])
            except (ValueError, TypeError):
                presentation = {}
            example = presentation.get('example') if isinstance(presentation, dict) else None
            row['exampleText'] = example.get('text', '') if isinstance(example, dict) else ''
            steps = example.get('steps', []) if isinstance(example, dict) else []
            row['exampleSteps'] = '\n'.join(step for step in steps if isinstance(step, str)) if isinstance(steps, list) else ''
            row['videoUrl'] = row['video_ref'] or ''
    elif kind == 'questions':
        clause = 'WHERE v.revision=(SELECT max(x.revision) FROM question_versions x WHERE x.question_id=q.id) AND (?=0 OR q.grade_id=?) AND (instr(lower(v.prompt_json),lower(?))>0 OR instr(lower(q.question_code),lower(?))>0)'
        values = (grade, grade, search, search)
        source = 'FROM questions q JOIN question_versions v ON v.question_id=q.id '
        total = db.execute('SELECT count(*) ' + source + clause, values).fetchone()[0]
        rows = [dict(row) for row in db.execute(
            'SELECT q.id,q.grade_id,q.topic_id,q.question_code,v.* ' + source + clause + ' ORDER BY q.id DESC LIMIT 25 OFFSET ?',
            (*values, (page-1)*25))]
        # q.id is the stable identity; version id is exposed separately.
        for row in rows:
            row['id'] = row['question_id']
            row['prompt'] = intro_text(row['prompt_json'])
            row['answer'] = str(json.loads(row['grading_rule_json']).get('answer', ''))
            row['options'] = json.loads(row['options_json'])
            row['steps'] = '\n'.join(item.get('text', '') for item in json.loads(row['solution_steps_json']) if item.get('type') == 'text')
            row['thinking'] = intro_text(row['hints_json'])
    else:
        raise APIError('Loại học liệu không hợp lệ.')
    return {'rows': rows, 'topics': topic_rows, 'total': total, 'page': page, 'pageSize': 25, 'kind': kind}


def save_topic(db, user, body):
    grade, title = number(body, 'grade', 1, 5), text_field(body, 'title', 180)
    intro = text_field(body, 'intro', 20000, 0)
    identity = body.get('id')
    if identity:
        old = get_row(db, 'topics', identity)
        if old['grade_id'] != grade:
            raise APIError('Chuyên đề đang gắn với bài học/câu hỏi. Tạo chuyên đề mới khi đổi khối.')
        check_revision(old, body)
        db.execute('UPDATE topics SET title=?,theory_json=?,revision=revision+1 WHERE id=?',
                   (title, packed(replace_intro(old['theory_json'], intro)), identity))
    else:
        identity = db.execute('INSERT INTO topics(grade_id,title,theory_json,client_key) VALUES (?,?,?,?)',
                              (grade, title, packed([{'type': 'text', 'text': intro}]), 'admin-' + secrets.token_hex(8))).lastrowid
    audit(db, user, 'save', 'topic', identity, title)
    return {'saved': True, 'id': identity}


def save_lesson(db, user, body):
    identity = body.get('id')
    old = get_row(db, 'lessons', identity) if identity else None
    if old:
        check_revision(old, body)
    grade, topic_id = number(body, 'grade', 1, 5), number(body, 'topicId')
    topic = get_row(db, 'topics', topic_id)
    if topic['grade_id'] != grade:
        raise APIError('Chuyên đề cần cùng khối với bài học.')
    if old and old['grade_id'] != grade and db.execute('SELECT 1 FROM lesson_progress WHERE lesson_id=?', (identity,)).fetchone():
        raise APIError('Bài đã có tiến độ học. Tạo bài mới khi chuyển khối.')
    title, intro = text_field(body, 'title', 180), text_field(body, 'intro', 20000)
    week, video = number(body, 'week', 1, 53), url_field(body, 'videoUrl')
    kind, status = body.get('kind'), body.get('status')
    if kind not in ('weekly', 'topic') or status not in ('draft', 'published'):
        raise APIError('Loại bài hoặc trạng thái phát hành không hợp lệ.')
    key = old['client_key'] if old and old['client_key'] else 'admin-lesson-' + secrets.token_hex(8)
    try:
        presentation = json.loads(old['presentation_json']) if old else {}
    except (ValueError, TypeError):
        presentation = {}
    if not isinstance(presentation, dict):
        presentation = {}
    if 'exampleText' in body or 'exampleSteps' in body:
        old_example = presentation.get('example') if isinstance(presentation.get('example'), dict) else {}
        example_text = text_field(body, 'exampleText', 20000, 0) if 'exampleText' in body else old_example.get('text', '')
        steps = body.get('exampleSteps', old_example.get('steps', []))
        if isinstance(steps, str):
            steps = [step.strip() for step in steps.splitlines() if step.strip()]
        if (not isinstance(steps, list) or len(steps) > 50 or
                any(not isinstance(step, str) or len(step) > 2000 for step in steps)):
            raise APIError('Lời giải ví dụ cần tối đa 50 bước, mỗi bước không quá 2.000 ký tự.')
        if steps and not example_text:
            raise APIError('Điền đề bài ví dụ trước khi nhập các bước giải.')
        presentation['example'] = {'text': example_text, 'steps': steps} if example_text else None
    elif not old:
        presentation['example'] = None
    presentation.update(id=key, grade=grade, topic=topic['client_key'], title=title, week=week,
                        theory=intro, description=intro[:160], symbol=presentation.get('symbol', '+'))
    blocks = replace_intro(old['body_json'], intro) if old else [{'type': 'text', 'text': intro}]
    values = (grade, topic_id, kind, week, title, packed(blocks), video, key, packed(presentation), status)
    if old:
        db.execute('UPDATE lessons SET grade_id=?,topic_id=?,kind=?,week_no=?,title=?,body_json=?,video_ref=?,client_key=?,presentation_json=?,publication_status=?,revision=revision+1 WHERE id=?', (*values, identity))
    else:
        identity = db.execute('INSERT INTO lessons(grade_id,topic_id,kind,week_no,title,body_json,video_ref,client_key,presentation_json,publication_status) VALUES (?,?,?,?,?,?,?,?,?,?)', values).lastrowid
    audit(db, user, 'save', 'lesson', identity, title + ' · ' + status)
    return {'saved': True, 'id': identity}


def save_question(db, user, body):
    grade, topic_id = number(body, 'grade', 1, 5), number(body, 'topicId')
    topic = get_row(db, 'topics', topic_id)
    if topic['grade_id'] != grade:
        raise APIError('Chuyên đề cần cùng khối với câu hỏi.')
    prompt = text_field(body, 'prompt', 10000)
    answer = text_field(body, 'answer', 500)
    options = body.get('options')
    if not isinstance(options, list) or not 2 <= len(options) <= 4 or any(not isinstance(option, str) or not option.strip() or len(option) > 500 for option in options):
        raise APIError('Nhập từ hai đến bốn lựa chọn, mỗi lựa chọn trên một dòng.')
    if len(set(options)) != len(options) or answer not in options:
        raise APIError('Các lựa chọn cần khác nhau và có đáp án đúng.')
    steps, thinking = text_field(body, 'steps', 20000), text_field(body, 'thinking', 10000, 0)
    difficulty, week = number(body, 'difficulty', 1, 4), number(body, 'week', 1, 53)
    status = body.get('status')
    if status not in ('draft', 'published', 'retired'):
        raise APIError('Trạng thái câu hỏi không hợp lệ.')
    identity = body.get('id')
    previous = None
    if identity:
        question = get_row(db, 'questions', identity)
        previous = db.execute('SELECT * FROM question_versions WHERE question_id=? ORDER BY revision DESC LIMIT 1', (identity,)).fetchone()
        if question['grade_id'] != grade or question['topic_id'] != topic_id:
            raise APIError('Tạo câu hỏi mới khi đổi khối hoặc chuyên đề của một bài toán đã có phiên bản.')
        if not previous or body.get('revision') != previous['revision']:
            raise APIError('Câu hỏi vừa có phiên bản mới. Tải lại để sửa tiếp.', 409)
    else:
        identity = db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (?,?,?)',
                              (grade, topic_id, 'ADM-' + secrets.token_hex(8).upper())).lastrowid
    if status in ('published', 'retired'):
        db.execute("UPDATE question_versions SET status='retired' WHERE question_id=? AND status='published'", (identity,))
    blocks = replace_intro(previous['prompt_json'], prompt) if previous else [{'type': 'text', 'text': prompt}]
    lines = [value.strip() for value in steps.splitlines() if value.strip()]
    solution = []
    if previous:
        for item in json.loads(previous['solution_steps_json']):
            if item.get('type') != 'text':
                solution.append(item)
            elif lines:
                solution.append({'type': 'text', 'text': lines.pop(0)})
    solution += [{'type': 'text', 'text': line} for line in lines]
    rule = json.loads(previous['grading_rule_json']) if previous else {}
    rule['answer'] = answer
    hints = replace_intro(previous['hints_json'], thinking) if previous else [{'type': 'text', 'text': thinking}]
    version_id = db.execute('INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,status,options_json) VALUES (?,?,?,?,?,?,?,?,?,?)',
               (identity, previous['revision']+1 if previous else 1, difficulty, week, packed(blocks),
                packed(rule), packed(solution), packed(hints), status, packed(options))).lastrowid
    if previous:
        db.execute('INSERT INTO question_assets(question_version_id,asset_id) SELECT ?,asset_id FROM question_assets WHERE question_version_id=?',
                   (version_id, previous['id']))
    audit(db, user, 'version', 'question', identity, prompt[:120] + ' · ' + status)
    return {'saved': True, 'id': identity}


def payment_list(db, handler):
    from .learning_update import membership
    search, _, page = page_query(handler)
    referrer_search = parse_qs(urlsplit(handler.path).query).get('referrer', [''])[0][:100].strip()
    clause = ('WHERE (instr(lower(o.reference),lower(?))>0 OR instr(lower(a.login_identifier),lower(?))>0 '
              'OR instr(lower(s.full_name),lower(?))>0 OR instr(lower(ra.login_identifier),lower(?))>0 '
              'OR instr(lower(rs.full_name),lower(?))>0)')
    values = (search,) * 5
    if referrer_search:
        clause += ' AND (instr(lower(ra.login_identifier),lower(?))>0 OR instr(lower(rs.full_name),lower(?))>0)'
        values += (referrer_search,) * 2
    source = ('FROM payment_orders o JOIN accounts a ON a.id=o.account_id '
              'JOIN students s ON s.account_id=a.id '
              'LEFT JOIN account_referrals r ON r.invitee_account_id=a.id '
              'LEFT JOIN referral_reward_confirmations rc ON rc.referral_id=r.id '
              'LEFT JOIN accounts ra ON ra.id=r.inviter_account_id '
              'LEFT JOIN students rs ON rs.account_id=ra.id ')
    total = db.execute('SELECT count(*) ' + source + clause, values).fetchone()[0]
    rows = [dict(row) for row in db.execute('SELECT o.*,a.login_identifier,s.full_name,f.month,c.name class_name,'
            'ra.id referrer_account_id,ra.login_identifier referrer_login,rs.full_name referrer_name,'
            'r.id referrer_referral_id,ra.deleted_at referrer_deleted_at,'
            '(r.first_vip_upgraded_at IS NOT NULL AND EXISTS (SELECT 1 FROM vip_purchases qp '
            'WHERE qp.id=r.qualifying_purchase_id AND qp.account_id=r.invitee_account_id)) referrer_qualifies,'
            'rc.confirmed_at referrer_support_confirmed_at,rc.confirmed_by referrer_support_confirmed_by,'
            'r.reward_status referrer_reward_status,r.reward_granted_at referrer_reward_granted_at,'
            'r.reward_vip_expires_at referrer_reward_vip_expires_at ' + source +
            'LEFT JOIN class_fees f ON f.id=o.fee_id LEFT JOIN online_classes c ON c.id=f.class_id ' + clause +
            ' ORDER BY o.id DESC LIMIT 25 OFFSET ?', (*values, (page-1)*25))]
    for row in rows:
        row['full_name'] = safe_nickname(row['full_name'])
        referrer = {'accountId': row.pop('referrer_account_id'), 'login': row.pop('referrer_login'),
                    'name': safe_nickname(row.pop('referrer_name')), 'rewardStatus': row.pop('referrer_reward_status'),
                    'rewardGrantedAt': row.pop('referrer_reward_granted_at'),
                    'rewardVipExpiresAt': row.pop('referrer_reward_vip_expires_at'),
                    'referralId': row.pop('referrer_referral_id'),
                    'supportConfirmedAt': row.pop('referrer_support_confirmed_at'),
                    'supportConfirmedBy': row.pop('referrer_support_confirmed_by')}
        deleted_at = row.pop('referrer_deleted_at')
        qualifies = bool(row.pop('referrer_qualifies'))
        if referrer['accountId'] is not None:
            referrer['membership'] = membership(db, {'account_id': referrer['accountId']})
            referrer['canConfirmSupport'] = (referrer['membership'] == 'SVip' and
                referrer['rewardStatus'] == 'customer_service' and qualifies and
                not referrer['supportConfirmedAt'] and deleted_at is None)
            row['referrer'] = referrer
        else:
            row['referrer'] = None
    return {'rows': rows, 'total': total, 'page': page, 'pageSize': 25}


def confirm_payment(db, user, identity, body):
    from .payments import settle_order
    order = get_row(db, 'payment_orders', identity)
    if body.get('reference') != order['reference'] or type(body.get('amount')) is not int or body['amount'] != order['amount']:
        raise APIError('Đối chiếu chính xác mã đơn và số tiền đã nhận.')
    if settle_order(db, order, 'staff'):
        audit(db, user, 'confirm', 'payment', identity, order['reference'] + ' · ' + str(order['amount']) + ' đồng')
    return {'saved': True}


def save_settings(db, user, body):
    current = settings(db)
    if body.get('revision') != current['revision']:
        raise APIError('Cấu hình vừa thay đổi. Tải lại trước khi lưu.', 409)
    keys = ('registration_open', 'learning_open', 'practice_open', 'arena_open', 'leaderboard_open')
    if any(type(body.get(key)) is not bool for key in keys):
        raise APIError('Trạng thái chức năng không hợp lệ.')
    limits = body.get('free_limits')
    if not isinstance(limits, dict) or set(limits) != {'content', 'combined', 'human', 'bot'}:
        raise APIError('Hạn mức không hợp lệ.')
    for value in limits.values():
        if type(value) is not int or not 0 <= value <= 100:
            raise APIError('Hạn mức mỗi ngày cần từ 0 đến 100.')
    values = {key: body[key] for key in keys}
    values['free_limits'] = limits
    db.execute("UPDATE system_settings SET value_json=?,revision=revision+1,updated_at=?,staff_id=? WHERE name='platform'",
               (packed(values), stamp(), user['id']))
    audit(db, user, 'update', 'settings', 'platform', 'Cập nhật chức năng và hạn mức Free')
    return {'settings': settings(db)}


def prepare_credentials(handler, path, body):
    """Authorize first, then hash outside the write transaction.

    The dispatch transaction reads the session again; record/revision checks in
    save_account and save_staff still run against the current committed rows.
    """
    self_password = path == '/api/staff/password'
    account_create = path == '/api/staff/accounts'
    account_edit = bool(re.fullmatch(r'/api/staff/accounts/\d+', path))
    staff_edit = path == '/api/staff/users'
    if not (self_password or account_create or account_edit or staff_edit):
        return None, None
    with connect(handler.server.database_path) as db:
        user = read_session(handler, db)
    if not user:
        raise APIError('Đăng nhập tài khoản giáo viên hoặc quản trị viên để tiếp tục.', 401)
    if not hmac.compare_digest(handler.headers.get('X-CSRF-Token', ''), user['csrf_token']):
        raise APIError('Phiên đăng nhập cần được tải lại.', 403)
    if self_password:
        if not isinstance(body.get('currentPassword'), str) or not verify_password(body['currentPassword'], user['password_hash']):
            raise APIError('Mật khẩu hiện tại chưa đúng.')
        return password_hash(body.get('newPassword')), (user['password_hash'], user['revision'])
    require_admin(user)
    if account_create or staff_edit and not body.get('id') or body.get('password'):
        return password_hash(body.get('password')), None
    return None, None


def dispatch(handler, method, path, body=None):
    body = body or {}
    if method == 'POST':
        if not same_origin(handler):
            raise APIError('Yêu cầu phải xuất phát từ website đang mở.', 403)
    credential = password_proof = login_proof = None
    if method == 'POST':
        if path == '/api/staff/login':
            limit_auth(handler)
            login_proof = prepare_login(handler.server.database_path, body, staff_only=True)
        else:
            credential, password_proof = prepare_credentials(handler, path, body)
    with connect(handler.server.database_path, method == 'POST') as db:
        user = read_session(handler, db)
        if method == 'POST' and path == '/api/staff/login':
            account = verified_login(db, login_proof)
            return issue_session(handler, db, account), 200
        if path == '/api/staff/session' and method == 'GET':
            return ({'authenticated': True, 'csrf': user['csrf_token'], 'user': public_user(user)} if user else
                    {'authenticated': False, 'setupNeeded': not bool(db.execute("SELECT 1 FROM staff_users WHERE role='admin'").fetchone())}), 200
        if not user:
            raise APIError('Đăng nhập tài khoản giáo viên hoặc quản trị viên để tiếp tục.', 401)
        if method == 'POST' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token', ''), user['csrf_token']):
            raise APIError('Phiên đăng nhập cần được tải lại.', 403)
        if path == '/api/staff/logout' and method == 'POST':
            db.execute('DELETE FROM staff_sessions WHERE token_hash=?', (user['token_hash'],))
            handler.api_headers = {'Set-Cookie': session_cookie(COOKIE, '', 0)}
            return {'authenticated': False}, 200
        if path == '/api/staff/password' and method == 'POST':
            if password_proof != (user['password_hash'], user['revision']):
                raise APIError('Tài khoản vừa được cập nhật. Tải lại rồi đổi mật khẩu.', 409)
            db.execute('UPDATE staff_users SET password_hash=? WHERE id=?', (credential, user['id']))
            db.execute('DELETE FROM staff_sessions WHERE staff_id=? AND token_hash<>?', (user['id'], user['token_hash']))
            audit(db, user, 'password', 'staff', user['id'], 'Đổi mật khẩu')
            return {'saved': True}, 200
        if path == '/api/staff/notifications':
            from .notifications import page_number, send, staff_metadata
            if method == 'GET':
                return staff_metadata(db,user,page_number(handler.path)),200
            if method == 'POST':
                return send(db,user,body),200
        if path == '/api/staff/notifications/preview' and method == 'POST':
            from .notifications import preview
            return preview(db,user,body),200
        match = re.fullmatch(r'/api/staff/submissions/(\d+)/file', path)
        if match and method == 'GET':
            from .zoom_classroom import file_payload
            return file_payload(db, int(match[1]), user=user), 200
        if path == '/api/staff/classes':
            if method == 'GET':
                return {'classes': classes(db, user), 'teachers': [dict(row) for row in db.execute('SELECT id,full_name FROM teachers ORDER BY full_name')] if user['role'] == 'admin' else []}, 200
            if method == 'POST':
                return save_class(db, user, body), 200
        tuition_action = re.fullmatch(r'/api/staff/classes/(\d+)/fees/(preview|calculate)', path)
        if tuition_action and method == 'POST':
            from .tuition import calculate, preview
            identity = int(tuition_action[1])
            info = classroom(db,user,identity)
            if tuition_action[2] == 'preview':
                return preview(db,info,body),200
            summary = calculate(db,user,info,body)
            return {**class_detail(db,user,identity),'calculation':summary},200
        tuition_detail = re.fullmatch(r'/api/staff/classes/(\d+)/fees/(\d+)', path)
        if tuition_detail and method == 'GET':
            from .tuition import fee_detail
            identity, fee_id = map(int,tuition_detail.groups())
            classroom(db,user,identity)
            fee = db.execute('SELECT f.*,s.full_name FROM class_fees f JOIN students s ON s.id=f.student_id '
                             'WHERE f.id=? AND f.class_id=?', (fee_id,identity)).fetchone()
            if not fee:
                raise APIError('Không tìm thấy học phí của lớp này.',404)
            result = fee_detail(db,fee)
            result['full_name'] = safe_nickname(result['full_name'])
            return {'fee':{key:value for key,value in result.items() if key!='sessions'},'sessions':result['sessions']},200
        match = re.fullmatch(r'/api/staff/classes/(\d+)(?:/(enroll|sessions|fees))?', path)
        if match:
            identity, action = int(match[1]), match[2]
            if method == 'GET' and not action:
                return class_detail(db, user, identity), 200
            if method == 'POST' and action:
                fn = {'enroll': enroll, 'sessions': save_session, 'fees': save_fee}[action]
                return fn(db, user, identity, body), 200
        match = re.fullmatch(r'/api/staff/sessions/(\d+)/(assignments|records)', path)
        if match and method == 'POST':
            fn = save_assignment if match[2] == 'assignments' else save_records
            return fn(db, user, int(match[1]), body), 200
        require_admin(user)
        if path == '/api/staff/admissions' and method == 'GET':
            from .admissions import list_registrations
            query, _, page = page_query(handler)
            return list_registrations(db, query, page), 200
        admission = re.fullmatch(r'/api/staff/admissions/(\d+)', path)
        if admission and method == 'POST':
            from .admissions import update_registration
            reference = update_registration(db, int(admission[1]), body)
            audit(db, user, 'update', 'admission', int(admission[1]), reference + ' / ' + body['status'])
            return {'saved': True}, 200
        if method == 'GET' and path == '/api/staff/overview':
            counts = {name: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                      for name, table in [('students', 'students'), ('classes', 'online_classes'), ('lessons', 'lessons'), ('questions', 'questions')]}
            counts['students'] = db.execute('SELECT count(*) FROM students s LEFT JOIN accounts a ON a.id=s.account_id '
                                           'WHERE a.deleted_at IS NULL').fetchone()[0]
            counts['pendingPayments'] = db.execute("SELECT count(*) FROM payment_orders WHERE status='pending'").fetchone()[0]
            return {'counts': counts}, 200
        if path == '/api/staff/accounts':
            if method == 'GET':
                return accounts(db, handler), 200
            if method == 'POST':
                return save_account(db, user, None, body, credential), 200
        match = re.fullmatch(r'/api/staff/accounts/(\d+)(?:/(delete|restore))?', path)
        if match and method == 'POST':
            fn = {'delete': delete_account, 'restore': restore_account}.get(match[2], save_account)
            return (fn(db, user, int(match[1]), body, credential) if fn is save_account else
                    fn(db, user, int(match[1]), body)), 200
        if path == '/api/staff/users':
            if method == 'GET':
                return {'users': staff_list(db)}, 200
            if method == 'POST':
                return save_staff(db, user, body, credential), 200
        if path == '/api/staff/content' and method == 'GET':
            return content_list(db, handler), 200
        if path in ('/api/staff/topics', '/api/staff/lessons', '/api/staff/questions') and method == 'POST':
            fn = {'topics': save_topic, 'lessons': save_lesson, 'questions': save_question}[path.rsplit('/', 1)[1]]
            return fn(db, user, body), 200
        if path == '/api/staff/payments' and method == 'GET':
            return payment_list(db, handler), 200
        if path == '/api/staff/payment-receipts' and method == 'GET':
            from .payments import receipt_list
            return receipt_list(db, handler), 200
        referral_support = re.fullmatch(r'/api/staff/referrals/(\d+)/confirm-support', path)
        if referral_support and method == 'POST':
            from .referral_support import confirm_support
            return confirm_support(db, user, int(referral_support[1]), body), 200
        match = re.fullmatch(r'/api/staff/payments/(\d+)/confirm', path)
        if match and method == 'POST':
            return confirm_payment(db, user, int(match[1]), body), 200
        if path == '/api/staff/settings':
            if method == 'GET':
                return {'settings': settings(db)}, 200
            if method == 'POST':
                return save_settings(db, user, body), 200
        if path == '/api/staff/audit' and method == 'GET':
            _, _, page = page_query(handler)
            rows = [dict(row) for row in db.execute('SELECT l.*,u.full_name FROM staff_audit_log l JOIN staff_users u ON u.id=l.staff_id ORDER BY l.id DESC LIMIT 25 OFFSET ?', ((page-1)*25,))]
            return {'rows': rows, 'page': page, 'pageSize': 25, 'total': db.execute('SELECT count(*) FROM staff_audit_log').fetchone()[0]}, 200
        raise APIError('API không tồn tại.', 404)
