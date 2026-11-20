"""Family recovery, one companion reselect and truthful retention on closure."""
import hashlib
import os
import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit
from . import platform_api as api


def recovery_config():
    local = os.environ.get('MAM_TOAN_SMTP_LOCAL_TEST') == '1'
    ready = bool(os.environ.get('MAM_TOAN_SMTP_HOST')) and (local or os.environ.get('MAM_TOAN_SMTP_STARTTLS') == '1')
    return {'available': ready, 'delivery': 'local-test' if ready and local else 'smtp' if ready else 'unavailable'}


def send_reset(email, token):
    base = os.environ.get('MAM_TOAN_RESET_BASE_URL', 'http://localhost:8765').rstrip('/')
    parsed = urlsplit(base)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or
            (parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1'))):
        raise ValueError('Invalid trusted reset origin')
    message = EmailMessage()
    message['From'] = os.environ.get('MAM_TOAN_SMTP_FROM', '5BMath <no-reply@5bmath.local>')
    message['To'] = email
    message['Subject'] = '5BMath — Đặt lại mật khẩu'
    message.set_content('Mở liên kết dưới đây để tự đặt mật khẩu mới trong 20 phút. '
                        'Nếu không yêu cầu, hãy bỏ qua thư.\n\n' + base + '/gia-dinh/?reset=1#token=' + token)
    with smtplib.SMTP(os.environ['MAM_TOAN_SMTP_HOST'], int(os.environ.get('MAM_TOAN_SMTP_PORT', '1025')), timeout=10) as smtp:
        if os.environ.get('MAM_TOAN_SMTP_STARTTLS') == '1':
            smtp.starttls()
        if os.environ.get('MAM_TOAN_SMTP_USER'):
            smtp.login(os.environ['MAM_TOAN_SMTP_USER'], os.environ.get('MAM_TOAN_SMTP_PASSWORD', ''))
        smtp.send_message(message)


def recovery(handler, action, body):
    from .family_accounts import _email
    api.limit_auth(handler)
    if action.endswith('/request'):
        email = _email(body)
        if not recovery_config()['available']:
            raise api.APIError('Chức năng gửi liên kết chưa được cấu hình.', 503)
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with api.connect(handler.server.database_path, True) as db:
            row = db.execute("SELECT id FROM family_accounts WHERE email=? AND status='active'", (email,)).fetchone()
            recent = db.execute('SELECT count(*) FROM family_password_resets WHERE family_id=? AND created_at>?',
                                (row['id'], api.stamp(api.now() - timedelta(hours=1)))).fetchone()[0] if row else 0
            issue = bool(row and recent < 3)
            if issue:
                db.execute('INSERT INTO family_password_resets VALUES(?,?,?,?,NULL)',
                           (digest, row['id'], api.stamp(), api.stamp(api.now() + timedelta(minutes=20))))
        if issue:
            try:
                send_reset(email, token)
            except Exception:
                # Do not expose delivery/account existence or leave a usable failed token.
                with api.connect(handler.server.database_path, True) as db:
                    db.execute('DELETE FROM family_password_resets WHERE token_hash=?', (digest,))
        return {'ok': True, 'message': 'Nếu email thuộc tài khoản đang hoạt động, liên kết xác nhận sẽ được gửi. Hộp thư thử chỉ dùng kiểm thử cục bộ.'}, 200
    password, token = body.get('newPassword'), body.get('token')
    if not isinstance(password, str) or password != body.get('confirmPassword'):
        raise api.APIError('Hai mật khẩu mới cần trùng nhau.')
    credential = api.password_hash(password)
    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        raise api.APIError('Liên kết không hợp lệ hoặc đã hết hạn.')
    with api.connect(handler.server.database_path, True) as db:
        row = db.execute("SELECT r.* FROM family_password_resets r JOIN family_accounts f ON f.id=r.family_id "
                         "WHERE token_hash=? AND redeemed_at IS NULL AND expires_at>? AND f.status='active'",
                         (hashlib.sha256(token.encode()).hexdigest(), api.stamp())).fetchone()
        if not row:
            raise api.APIError('Liên kết không hợp lệ hoặc đã hết hạn.')
        db.execute('UPDATE family_password_resets SET redeemed_at=? WHERE family_id=? AND redeemed_at IS NULL', (api.stamp(), row['family_id']))
        db.execute('UPDATE family_accounts SET password_hash=?,auth_revision=auth_revision+1 WHERE id=?', (credential, row['family_id']))
        db.execute('UPDATE family_devices SET revoked_at=? WHERE family_id=? AND revoked_at IS NULL', (api.stamp(), row['family_id']))
    return {'ok': True, 'authenticated': False}, 200


def companion_remaining(db, sid):
    return 0 if db.execute('SELECT 1 FROM companion_reselections WHERE student_id=?', (sid,)).fetchone() else 1


def reselect(db, sid, code):
    if not isinstance(code, str) or code not in api.MASCOT_NAMES:
        raise api.APIError('Linh vật không hợp lệ.')
    before = db.execute('SELECT mascot_id FROM student_companions WHERE student_id=?', (sid,)).fetchone()
    target = db.execute('SELECT id FROM mascots WHERE name=?', (api.MASCOT_NAMES[code],)).fetchone()
    if not before or not target:
        raise api.APIError('Chưa có Bạn Đồng Hành.', 409)
    if before[0] == target[0]:
        return
    if not companion_remaining(db, sid):
        raise api.APIError('Con đã dùng một lần chọn lại Bạn Đồng Hành.', 409)
    db.execute('INSERT INTO companion_reselections VALUES(?,?,?,?)', (sid, api.stamp(), before[0], target[0]))
    db.execute('UPDATE student_companions SET mascot_id=? WHERE student_id=?', (target[0], sid))


def daily_counts(db, sid):
    local = api.now().astimezone(api.VN).replace(hour=0, minute=0, second=0, microsecond=0)
    start, end = api.stamp(local), api.stamp(local + timedelta(days=1))
    exams = db.execute("SELECT count(*) FROM exam_attempts WHERE student_id=? AND status='submitted' AND submitted_at>=? AND submitted_at<?", (sid,start,end)).fetchone()[0]
    answers = db.execute("SELECT count(*) FROM exam_answers a JOIN exam_attempts e ON e.id=a.attempt_id WHERE e.student_id=? AND e.status='submitted' AND e.submitted_at>=? AND e.submitted_at<? AND trim(COALESCE(json_extract(a.response_json,'$.answer'),''))<>''", (sid,start,end)).fetchone()[0]
    lessons = db.execute('SELECT count(*) FROM lesson_progress WHERE student_id=? AND first_completed_at>=? AND first_completed_at<?', (sid,start,end)).fetchone()[0]
    return {'date': local.date().isoformat(), 'timezone': 'Asia/Ho_Chi_Minh', 'submittedExams': exams, 'answeredQuestions': answers, 'completedLessons': lessons}


def today(handler, db, child):
    result = daily_counts(db, child['student_id'])
    provider = getattr(handler.server, 'local_pilot', None)
    if provider:
        with api.connect(provider.path) as pilot:
            mapped = pilot.execute('SELECT pilot_student_id FROM local_principals WHERE main_student_id=?', (child['student_id'],)).fetchone()
            if mapped:
                extra = daily_counts(pilot, mapped[0])
                for key in ('submittedExams','answeredQuestions','completedLessons'):
                    result[key] += extra[key]
    return result
