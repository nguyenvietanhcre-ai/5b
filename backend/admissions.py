"""Public parent intake, kept separate from student and staff sessions."""
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from .platform_api import APIError, connect, stamp

_secret = secrets.token_bytes(32)
_lock = threading.Lock()
_submissions = {}
COOKIE = '5bmath_intake'
STATUSES = ('new', 'contacted', 'scheduled', 'completed', 'closed')


def cookie_nonce(handler):
    jar = SimpleCookie()
    try:
        jar.load(handler.headers.get('Cookie', ''))
        return jar[COOKIE].value if COOKIE in jar else ''
    except Exception:
        return ''


def signature(nonce, issued):
    return hmac.new(_secret, f'{nonce}:{issued}'.encode(), hashlib.sha256).hexdigest()


def field(body, name, maximum, required=False):
    value = body.get(name, '')
    if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
        raise APIError('Vui lòng kiểm tra trường ' + name + '.')
    return value.strip()


def validate(body):
    values = {key: field(body, key, maximum, required) for key, maximum, required in [
        ('parentName', 100, True), ('studentName', 100, True), ('phone', 30, True),
        ('email', 160, False), ('school', 160, False), ('city', 100, True),
        ('goal', 500, True), ('level', 100, True), ('schedule', 300, True),
        ('contact', 30, True), ('notes', 1500, False)]}
    phone = re.sub(r'[\s.()-]', '', values['phone'])
    if phone.startswith('+84'):
        phone = '0' + phone[3:]
    if not re.fullmatch(r'0[1-9]\d{8,9}', phone):
        raise APIError('Số điện thoại chưa hợp lệ. Vui lòng nhập số liên hệ tại Việt Nam.')
    values['phone'] = phone
    if values['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']):
        raise APIError('Email chưa hợp lệ.')
    if type(body.get('grade')) is not int or body['grade'] not in range(1, 6):
        raise APIError('Vui lòng chọn khối lớp từ 1 đến 5.')
    if values['contact'] not in ('Zalo', 'Điện thoại', 'Facebook'):
        raise APIError('Vui lòng chọn cách liên hệ.')
    if body.get('consent') is not True:
        raise APIError('Cần sự đồng ý của phụ huynh/người giám hộ trước khi gửi.')
    values.update(grade=body['grade'], consent=True, consentVersion='2026-11-11')
    return values


def dispatch(handler, method, path, body=None):
    if path == '/api/v1/admissions/token' and method == 'GET':
        nonce = secrets.token_urlsafe(24)
        issued = str(int(time.time()))
        handler.api_headers = {'Set-Cookie': f'{COOKIE}={nonce}; Path=/api/v1/admissions; HttpOnly; SameSite=Strict; Max-Age=7200'}
        return {'token': issued + '.' + signature(nonce, issued)}, 200
    if path != '/api/v1/admissions' or method != 'POST':
        raise APIError('API không tồn tại.', 404)
    origin = urlsplit(handler.headers.get('Origin', ''))
    if origin.netloc != handler.headers.get('Host') or origin.scheme not in ('http', 'https'):
        raise APIError('Vui lòng gửi đăng ký từ website đang mở.', 403)
    token = handler.headers.get('X-Intake-Token', '').split('.')
    nonce = cookie_nonce(handler)
    if (len(token) != 2 or len(token[0]) > 12 or not token[0].isdigit() or not nonce or
            not 0 <= time.time() - int(token[0]) < 7200 or
            not hmac.compare_digest(token[1], signature(nonce, token[0]))):
        raise APIError('Phiên biểu mẫu đã hết hạn. Vui lòng thử gửi lại.', 403)
    body = body or {}
    if body.get('website'):
        raise APIError('Không thể gửi biểu mẫu này.')
    key = field(body, 'requestKey', 80, True)
    if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', key):
        raise APIError('Mã yêu cầu không hợp lệ.')
    values = validate(body)
    packed = json.dumps(values, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(packed.encode()).hexdigest()
    with connect(handler.server.database_path, True) as db:
        existing = db.execute('SELECT reference,payload_hash FROM entrance_registrations WHERE request_key=?', (key,)).fetchone()
        if existing:
            if not hmac.compare_digest(existing['payload_hash'], digest):
                raise APIError('Mã yêu cầu đã được dùng. Vui lòng tải lại biểu mẫu.', 409)
            return {'saved': True, 'reference': existing['reference']}, 200
        # Short-lived limits in memory; no IP address is stored with parent/student data.
        current = time.time()
        address = handler.client_address[0]
        with _lock:
            for old in list(_submissions):
                _submissions[old] = [value for value in _submissions[old] if current-value < 3600]
                if not _submissions[old]:
                    del _submissions[old]
            attempts = _submissions.setdefault(address, [])
            if len(attempts) >= 5:
                raise APIError('Đã gửi nhiều đăng ký. Vui lòng thử lại sau hoặc liên hệ Zalo.', 429)
            attempts.append(current)
        reference = 'DV-' + secrets.token_hex(6).upper()
        when = stamp()
        db.execute('INSERT INTO entrance_registrations '
                   '(reference,request_key,payload_hash,parent_name,phone,student_name,grade,details_json,created_at,updated_at) '
                   'VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (reference,key,digest,values['parentName'],values['phone'],values['studentName'],values['grade'],packed,when,when))
    return {'saved': True, 'reference': reference}, 200


def list_registrations(db, query, page):
    where = (' WHERE instr(lower(parent_name),lower(?))>0 OR instr(lower(student_name),lower(?))>0 '
             'OR instr(lower(phone),lower(?))>0 OR instr(lower(reference),lower(?))>0')
    params = (query,) * 4
    rows = [dict(row) for row in db.execute('SELECT * FROM entrance_registrations' + where +
        ' ORDER BY id DESC LIMIT 25 OFFSET ?', (*params, (page-1)*25))]
    for row in rows:
        row['details'] = json.loads(row.pop('details_json'))
        row.pop('request_key')
        row.pop('payload_hash')
    return {'rows': rows, 'page': page, 'pageSize': 25,
            'total': db.execute('SELECT count(*) FROM entrance_registrations' + where, params).fetchone()[0]}


def update_registration(db, identity, body):
    status = field(body, 'status', 30, True)
    note = field(body, 'note', 2000)
    if status not in STATUSES or type(body.get('revision')) is not int:
        raise APIError('Trạng thái hoặc phiên bản không hợp lệ.')
    row = db.execute('SELECT reference,revision FROM entrance_registrations WHERE id=?', (identity,)).fetchone()
    if not row:
        raise APIError('Không tìm thấy đăng ký.', 404)
    if row['revision'] != body['revision']:
        raise APIError('Đăng ký đã được cập nhật ở nơi khác. Tải lại trước khi sửa.', 409)
    db.execute('UPDATE entrance_registrations SET status=?,admin_note=?,revision=revision+1,updated_at=? WHERE id=?',
               (status,note,stamp(),identity))
    return row['reference']
