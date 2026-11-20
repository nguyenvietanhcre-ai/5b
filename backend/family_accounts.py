"""Shared family credentials, isolated learner identities and rotating device scopes.

The account rows behind children are compatibility identities, never adult login
identities. No existing account is linked, rewritten, reset or granted rights.
"""
import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit

from . import platform_api as api

COOKIE = '5bmath_family'
PARENT_IDLE = timedelta(minutes=5)
PARENT_MAX = timedelta(minutes=15)
PIN_LOCK = timedelta(minutes=15)
PIN_SETUP = timedelta(minutes=10)
MAX_DEVICES = 3

def access_changed(message):
    error=api.APIError(message,403)
    error.familyAccessChanged=True
    return error


def _error(message, status=400, code=None):
    error = api.APIError(message, status)
    if code:
        error.code = code
    return error


def _cookie(handler):
    jar = SimpleCookie()
    try:
        jar.load(handler.headers.get('Cookie', ''))
    except Exception:
        return ''
    return jar[COOKIE].value if COOKIE in jar else ''


def family_present(handler):
    # A malformed/present cookie must not fall through to another identity.
    return bool(re.search(r'(?:^|;\s*)' + re.escape(COOKIE) + r'=', handler.headers.get('Cookie', '')))


def _available(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='family_accounts'").fetchone())


def _row(handler, db):
    if not _available(db):
        return None
    token = _cookie(handler)
    if not token:
        return None
    return db.execute(
        "SELECT d.*,f.email,f.password_hash,f.pin_hash family_pin_hash,p.display_name parent_name "
        "FROM family_devices d JOIN family_accounts f ON f.id=d.family_id "
        "JOIN family_parent_profiles p ON p.family_id=f.id "
        "WHERE d.token_hash=? AND d.revoked_at IS NULL AND d.expires_at>? "
        "AND f.status='active' AND f.auth_revision=d.auth_revision",
        (hashlib.sha256(token.encode()).hexdigest(), api.stamp())).fetchone()


def _parent_expired(row):
    if row['scope'] not in ('parent_read', 'parent_full'):
        return False
    return (not row['parent_opened_at'] or not row['parent_seen_at'] or
            row['parent_opened_at'] <= api.stamp(api.now() - PARENT_MAX) or
            row['parent_seen_at'] <= api.stamp(api.now() - PARENT_IDLE))


def _context(handler, row, required=True):
    context = handler.headers.get('X-Family-Context', '')
    if (required or context) and not hmac.compare_digest(context, row['context']):
        raise access_changed('Hồ sơ hoặc quyền trên máy này vừa đổi. Hãy tải lại trước khi tiếp tục.')


def _csrf(handler, row):
    if not hmac.compare_digest(handler.headers.get('X-CSRF-Token', ''), row['csrf_token']):
        raise access_changed('Phiên gia đình cần được tải lại.')


def _require(row, full=False):
    if _parent_expired(row) or row['scope'] not in (('parent_full',) if full else ('parent_read', 'parent_full')):
        raise access_changed('Hãy nhập PIN phụ huynh để mở lại Góc phụ huynh.')
    if row['allowed_student_id'] is not None:
        raise access_changed('Thiết bị này chỉ dành cho một con.')


def _children(db, row):
    return db.execute(
        "SELECT c.*,s.full_name,s.account_id,s.status,a.status account_status,a.birth_year,m.name mascot_name "
        "FROM family_children c JOIN students s ON s.id=c.student_id JOIN accounts a ON a.id=s.account_id "
        "LEFT JOIN student_companions sc ON sc.student_id=c.student_id LEFT JOIN mascots m ON m.id=sc.mascot_id "
        "WHERE c.family_id=? AND s.status='active' AND a.status='active' AND a.deleted_at IS NULL "
        "AND (? IS NULL OR c.student_id=?) ORDER BY c.student_id",
        (row['family_id'], row['allowed_student_id'], row['allowed_student_id'])).fetchall()


def _child(db, row, identity=None):
    identity = row['selected_student_id'] if identity is None else identity
    if type(identity) is not int or identity <= 0:
        raise api.APIError('Hãy chọn đúng hồ sơ con trên thiết bị này.', 403)
    child = next((c for c in _children(db, row) if c['student_id'] == identity), None)
    if not child:
        raise api.APIError('Không tìm thấy hồ sơ con được cấp cho thiết bị này.', 404)
    return child


def child_grade(child):
    return max(1, min(5, child['declared_grade'] + max(0, api.academic()[0] - child['grade_academic_year'])))


def _mapped(db, row, child):
    account = db.execute('SELECT * FROM accounts WHERE id=?', (child['account_id'],)).fetchone()
    return {**dict(account), 'account_id': child['account_id'], 'student_id': child['student_id'],
            'birth_year': account['birth_year'], 'actual_birth_year': account['birth_year'],
            'grade': child_grade(child), 'full_name': child['full_name'], 'family_id': row['family_id'],
            'family_scope': row['scope'], 'family_device_id': row['id'], 'family_context': row['context'],
            'token_hash': row['token_hash'], 'csrf_token': row['csrf_token'], 'expires_at': row['expires_at']}


def _sensitive(path):
    return (path.startswith('/api/v1/payments') or path.startswith('/api/website/support/') or
            path.startswith('/api/v1/notifications') or path == '/api/v1/referrals' or
            path == '/api/v1/dev/upgrade')


def read_learner_session(handler, db):
    """Central guard for every old API importing platform_api.read_session."""
    # Serialize capability validation with downgrade/revoke for the whole request,
    # including sensitive GETs whose legacy handlers open a read connection.
    if not getattr(db, 'in_transaction', False):
        db.execute('BEGIN IMMEDIATE')
    row = _row(handler, db)
    if not row:
        return None
    path = urlsplit(handler.path).path
    # Browser attachment links cannot supply the SPA context header. This
    # read-only route still validates any supplied context and all child gates.
    material_link = (getattr(handler, 'command', 'GET') == 'GET' and
                     re.fullmatch(r'/api/v1/lesson-materials/(?:main|native)/[A-Za-z0-9._-]{1,120}/[1-9][0-9]{0,8}/[a-f0-9]{32}', path))
    _context(handler, row, required=not material_link)
    if _parent_expired(row):
        raise access_changed('Góc phụ huynh đã khóa. Hãy mở lại để tiếp tục.')
    if _sensitive(path):
        _require(row, full=True)
        db.execute('UPDATE family_devices SET parent_seen_at=? WHERE id=?', (api.stamp(), row['id']))
    elif row['scope'] != 'child' and not (row['scope'] == 'parent_full' and
            (path in ('/api/v1/session', '/api/v1/state', '/api/v1/classes/unread', '/api/v1/personal/notifications', '/api/v1/personal/notifications/read') or
             re.fullmatch(r'/api/v1/classes/\d+', path))):
        raise access_changed('Hãy chọn con để học hoặc mở đúng quyền phụ huynh.')
    return _mapped(db, row, _child(db, row))


def learning_payload(session, payload):
    """Mixed legacy class/state views omit adult-only data for family learners."""
    if not isinstance(session, dict) or session.get('family_scope') != 'child':
        return payload
    account = payload.get('account')
    if isinstance(account, dict):
        account.update(login='', notifications=[], notificationUnreadCount=0, notificationTotal=0,
                       referrals=[], referralTotal=0)
    if isinstance(payload.get('state'), dict):
        payload['state']['invitedBy']=''
    if 'fees' in payload:
        payload['fees'] = []
    for source in (payload, account or {}):
        for name in ('classroomUnread', 'unread'):
            summary = source.get(name)
            if isinstance(summary, dict):
                summary['fees'] = 0
                summary['total'] = summary.get('assignments', 0)
                for value in summary.get('classes', {}).values():
                    value['fees'] = 0
                    value['total'] = value.get('assignments', 0)
        if isinstance(source.get('readThrough'), dict):
            source['readThrough']['fees'] = 0
    return payload


def require_child(handler, db, full_parent=False):
    """Integration hook: never authorize a browser-supplied target student ID."""
    if not api.same_origin(handler):
        raise api.APIError('Yêu cầu phải xuất phát từ website đang mở.', 403)
    row = _row(handler, db)
    if not row:
        raise api.APIError('Hãy đăng nhập tài khoản gia đình.', 401)
    _context(handler, row)
    _csrf(handler, row)
    if full_parent:
        _require(row, full=True)
    elif row['scope'] != 'child' or _parent_expired(row):
        raise api.APIError('Hãy chọn con để tiếp tục.', 403)
    return _mapped(db, row, _child(db, row))


def authorize_claim(handler, db, body):
    session = require_child(handler, db, full_parent=True)
    selected = session['student_id']
    if any(k in body and body[k] != selected for k in ('childId', 'studentId', 'student_id')):
        raise api.APIError('Hãy xác nhận đúng con đang được chọn trên thiết bị.', 403)
    consent = db.execute(
        "SELECT version,accepted_at FROM family_child_consents WHERE family_id=? AND student_id=? "
        "AND purpose='learning' AND withdrawn_at IS NULL ORDER BY id DESC LIMIT 1",
        (session['family_id'], selected)).fetchone()
    if not consent:
        raise api.APIError('Chưa có đồng ý còn hiệu lực cho hồ sơ con này.', 403)
    return {'family_id': session['family_id'], 'student_id': selected,
            'consent_basis': 'self_declared:learning:' + consent['version'] + ':' + consent['accepted_at']}


def _revoke_staff_on_browser(handler,db):
    # Handing this browser to a child also ends any independent staff capability.
    jar=SimpleCookie()
    try:jar.load(handler.headers.get('Cookie',''))
    except Exception:return
    if '5bmath_staff' in jar and db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_sessions'").fetchone():
        db.execute('DELETE FROM staff_sessions WHERE token_hash=?',(hashlib.sha256(jar['5bmath_staff'].value.encode()).hexdigest(),))

def _rotate(handler, db, row, scope, selected=None, preserve_elevation=False, active_profile=None):
    if scope in ('child','profiles'):_revoke_staff_on_browser(handler,db)
    token, csrf, context = (secrets.token_urlsafe(32) for _ in range(3))
    elevated = scope in ('parent_read', 'parent_full')
    active_profile = active_profile or ('parent' if elevated else 'child' if scope == 'child' else row['active_profile'])
    db.execute('UPDATE family_devices SET token_hash=?,csrf_token=?,context=?,scope=?,selected_student_id=?,active_profile=?, '
               'parent_opened_at=?,parent_seen_at=?,full_authenticated_at=?,last_seen_at=? WHERE id=?',
               (hashlib.sha256(token.encode()).hexdigest(), csrf, context, scope, selected, active_profile,
                row['parent_opened_at'] if preserve_elevation else api.stamp() if elevated else None,
                api.stamp() if elevated else None,
                row['full_authenticated_at'] if preserve_elevation else api.stamp() if scope == 'parent_full' else None,
                api.stamp(), row['id']))
    seconds = max(0, int((datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00')) - api.now()).total_seconds()))
    handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, token, seconds)}
    return _row(handler_with_token(handler, token), db)


def handler_with_token(handler, token):
    from types import SimpleNamespace
    return SimpleNamespace(headers={**dict(handler.headers), 'Cookie': COOKIE + '=' + token})


def _new_device(handler, db, family, remember=True, name=None, existing=None):
    # One browser has one learner principal. Revoke only its current legacy
    # capability so clearing the family cookie cannot resurrect another learner.
    jar = SimpleCookie()
    try:
        jar.load(handler.headers.get('Cookie', ''))
        legacy_name = api.student_cookie_name(handler)
        legacy = jar[legacy_name].value if legacy_name in jar else ''
    except Exception:
        legacy = ''
    if legacy:
        db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (hashlib.sha256(legacy.encode()).hexdigest(),))
    _revoke_staff_on_browser(handler,db)
    token, csrf, context = (secrets.token_urlsafe(32) for _ in range(3))
    days = 30 if remember else 7
    setup_until = api.stamp(api.now() + PIN_SETUP) if not family['pin_hash'] else None
    if existing:
        db.execute('UPDATE family_devices SET remembered=?,device_name=?,expires_at=?,pin_setup_until=? WHERE id=?',
                   (int(remember), _device_name(name if name is not None else existing['device_name']),
                    api.stamp(api.now() + timedelta(days=days)), setup_until, existing['id']))
        row = _row(handler, db)
        scope = 'child' if row['scope'] == 'child' else 'profiles'
        return _rotate(handler, db, row, scope, row['selected_student_id'])
    identity = secrets.token_hex(16)
    db.execute('INSERT INTO family_devices(id,family_id,token_hash,csrf_token,context,scope,selected_student_id,'
               'device_name,remembered,auth_revision,created_at,last_seen_at,expires_at,active_profile,pin_setup_until) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (identity, family['id'], hashlib.sha256(token.encode()).hexdigest(), csrf, context,
                'profiles', None, _device_name(name), int(remember), family['auth_revision'],
                api.stamp(), api.stamp(), api.stamp(api.now() + timedelta(days=days)),
                'parent' if not family['pin_hash'] else 'profiles', setup_until))
    handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, token, days * 86400)}
    return _row(handler_with_token(handler, token), db)


def _device_name(value):
    if value is None:
        return 'Thiết bị gia đình'
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 or any(ord(c) < 32 for c in value):
        raise api.APIError('Tên thiết bị không hợp lệ.')
    return value.strip()


def _state(db, row):
    from .family_features import companion_remaining
    children = [{'id': c['student_id'], 'name': api.safe_nickname(c['full_name']),
                 'nickname': api.safe_nickname(c['full_name']), 'grade': child_grade(c), 'birthYear': c['birth_year'],
                 'avatar': api.mascot_code(c['mascot_name']), 'mascot': api.mascot_code(c['mascot_name']),
                 'mascotCode': api.mascot_code(c['mascot_name']), 'avatarUrl': _art(api.mascot_code(c['mascot_name'])),
                 'pinSet': bool(c['pin_hash']), 'pinRequired': bool(c['pin_hash']),
                 'companionChangesRemaining': companion_remaining(db, c['student_id'])} for c in _children(db, row)]
    family = {'id': row['family_id']}
    if row['scope'] == 'parent_full' and not _parent_expired(row):
        family.update(email=row['email'], parentName=row['parent_name'], verificationStatus='self_declared')
    selected = row['selected_student_id'] if any(c['id'] == row['selected_student_id'] for c in children) else None
    return {'authenticated': True, 'csrf': row['csrf_token'], 'context': row['context'], 'scope': row['scope'],
            'activeProfile': {'type': row['active_profile'], 'childId': selected if row['active_profile'] == 'child' else None},
            'parentLocked': row['active_profile'] == 'parent' and (row['scope'] != 'parent_full' or _parent_expired(row)),
            'onboarding': {'needsParentPin': not bool(row['family_pin_hash']), 'needsChild': not bool(children),
                           'canSetupParentPin': not bool(row['family_pin_hash']) and bool(row['pin_setup_until'] and row['pin_setup_until'] > api.stamp())},
            'selectedChildId': selected, 'children': children, 'parentPinSet': bool(row['family_pin_hash']),
            'device': {'id': row['id'], 'name': row['device_name'], 'remember': bool(row['remembered']),
                       'childOnly': row['allowed_student_id'] is not None, 'expiresAt': row['expires_at']},
            'family': family, 'parentIdleSeconds': 300, 'parentMaxSeconds': 900}


def _art(code):
    return '/arena-art/badge-mascots/' + code + '.webp'


def _devices(db, family_id):
    return [dict(r) for r in db.execute('SELECT id,device_name name,remembered remember,created_at createdAt,last_seen_at lastSeenAt,'
        'expires_at expiresAt,allowed_student_id childOnlyId FROM family_devices WHERE family_id=? AND revoked_at IS NULL '
        'AND expires_at>? AND auth_revision=(SELECT auth_revision FROM family_accounts WHERE id=?) ORDER BY created_at,id',
        (family_id, api.stamp(), family_id))]


def _record_registration_consent(db, family_id, body):
    from .website_legal import VERSION, SLUGS, validate_consent
    consent = validate_consent(body)
    folder = Path(__file__).resolve().parent.parent / 'frontend' / 'legal'
    raw = json.dumps({slug: (folder / slug / 'index.html').read_text(encoding='utf-8') for slug in SLUGS},
                     ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    prior = db.execute('SELECT content_sha256 FROM website_policy_snapshots WHERE version=?', (VERSION,)).fetchone()
    if prior and prior[0] != digest:
        raise api.APIError('Bản chính sách vừa đổi; cần phát hành phiên bản mới trước khi nhận đồng ý.', 409)
    db.execute('INSERT OR IGNORE INTO website_policy_snapshots VALUES(?,?,?,?)', (VERSION, raw, digest, api.stamp()))
    db.execute('INSERT INTO family_registration_consents VALUES(?,?,?,?,?,?,?)',
               (family_id, VERSION, consent['name'], consent['contact'], consent['role'], digest, api.stamp()))


def _email(body):
    value = body.get('email', body.get('login'))
    if not isinstance(value, str) or not re.fullmatch(r'[^\s@]{1,100}@[^\s@.]{1,100}(?:\.[^\s@.]{1,63})+', value.strip()) or len(value.strip()) > 180:
        raise api.APIError('Hãy điền email liên hệ của người lớn.')
    return value.strip().lower()


def _key(body):
    value = body.get('requestKey')
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', value):
        raise api.APIError('Mã yêu cầu không hợp lệ.')
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _child_input(body):
    name = api.nickname_field(body)
    if body.get('pin') is not None and (not isinstance(body['pin'], str) or not re.fullmatch(r'[0-9]{4,6}', body['pin'])):
        raise api.APIError('PIN con cần từ 4 đến 6 chữ số.')
    birth = body.get('birthYear')
    if type(birth) is not int or not 1900 <= birth <= api.academic()[0]:
        raise api.APIError('Hãy điền năm sinh thật của con.')
    grade = body.get('grade', max(1, min(5, api.academic()[0] - birth - 5)))
    if type(grade) is not int or grade not in range(1, 6):
        raise api.APIError('Hãy chọn khối lớp từ 1 đến 5.')
    mascot = body.get('mascot', body.get('mascotCode', 'sprout'))
    if not isinstance(mascot, str) or mascot not in api.MASCOT_NAMES:
        raise api.APIError('Hãy chọn Bạn Đồng Hành trong danh sách.')
    return name, grade, birth, mascot


def _add_child(db, family_id, body, key, consent_body, legacy=False):
    from .website_legal import record_consent, validate_consent, VERSION
    name, grade, birth, mascot_code = _child_input(body)
    pin = body.get('pin')
    pin_hash = _hash_pin(pin) if pin is not None else None
    if not pin_hash and not legacy and body.get('noPin') is not True:
        raise api.APIError('Hãy đặt PIN riêng cho hồ sơ con.')
    consent = validate_consent(consent_body)
    fingerprint = _digest({'name': name, 'grade': grade, 'birthYear': birth, 'mascot': mascot_code,
                           'pinSet': bool(pin_hash), 'consent': consent, 'version': VERSION})
    previous = db.execute('SELECT * FROM family_children WHERE family_id=? AND request_key=?', (family_id, key)).fetchone()
    if previous:
        if not hmac.compare_digest(previous['request_digest'], fingerprint):
            raise api.APIError('Mã yêu cầu đã được dùng cho hồ sơ khác.', 409)
        if pin_hash and not api.verify_password(pin, previous['pin_hash']):
            raise api.APIError('Mã yêu cầu đã được dùng với PIN khác.', 409)
        return previous['student_id']
    code = secrets.token_hex(16).upper()
    aid = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash) '
                     'VALUES(?,?,?,?,?,NULL)', ('FCH-' + code, 'family-child-' + code.lower() + '@example.invalid',
                     birth, '5B' + code[:16], api.stamp())).lastrowid
    sid = db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES(?,?,?,?)',
                     ('HS-' + code, name, grade, aid)).lastrowid
    db.execute('INSERT INTO family_children(student_id,family_id,declared_grade,grade_academic_year,actual_birth_year,pin_hash,request_key,request_digest,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
               (sid, family_id, grade, api.academic()[0], birth, pin_hash, key, fingerprint, api.stamp()))
    api.ensure_grade(db, sid, birth)
    mascot_name = api.MASCOT_NAMES[mascot_code]
    mascot = db.execute('SELECT id FROM mascots WHERE name=?', (mascot_name,)).fetchone()
    if not mascot:
        db.execute('INSERT OR IGNORE INTO mascots(name) VALUES(?)', (mascot_name,))
        mascot = db.execute('SELECT id FROM mascots WHERE name=?', (mascot_name,)).fetchone()
    db.execute('INSERT INTO student_companions(student_id,mascot_id) VALUES(?,?)', (sid, mascot[0]))
    db.execute('INSERT INTO learning_preferences(student_id,theme) VALUES(?,?)', (sid, api.DEFAULT_THEME))
    record_consent(db, aid, consent_body)
    db.execute("INSERT INTO family_child_consents(family_id,student_id,purpose,version,representative_role,accepted_at) VALUES(?,?,'learning',?,?,?)",
               (family_id, sid, VERSION, consent['role'], api.stamp()))
    return sid


def _pin(handler, db, row, value, encoded):
    if row['pin_locked_until'] and row['pin_locked_until'] > api.stamp():
        raise api.APIError('Cổng PIN trên thiết bị tạm khóa 15 phút. Hãy thử lại sau.', 429)
    if isinstance(value,str) and encoded and callable(getattr(db,'prepare_verification',None)):db.prepare_verification(value,encoded)
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4,6}', value) or not encoded or not api.verify_password(value, encoded):
        count = row['pin_failures'] + 1 if not row['pin_locked_until'] or row['pin_locked_until'] > api.stamp() else 1
        db.execute('UPDATE family_devices SET pin_failures=?,pin_locked_until=? WHERE id=?',
                   (count, api.stamp(api.now() + PIN_LOCK) if count >= 5 else None, row['id']))
        # Failed attempts must survive the APIError/transaction rollback.
        error=api.APIError('PIN chưa đúng.' if count < 5 else 'Cổng PIN trên thiết bị tạm khóa 15 phút.', 403 if count < 5 else 429)
        if callable(getattr(db,'commit_and_raise',None)):db.commit_and_raise(error)
        db.commit()
        raise error
    db.execute('UPDATE family_devices SET pin_failures=0,pin_locked_until=NULL WHERE id=?', (row['id'],))


def _hash_pin(value, parent=False):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{6}' if parent else r'[0-9]{4,6}', value):
        raise api.APIError('PIN phụ huynh cần 6 chữ số.' if parent else 'PIN con cần từ 4 đến 6 chữ số.')
    # PBKDF same work factor and unique random salt; no PIN plaintext stored.
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode(), salt, api.ITERATIONS)
    return f'pbkdf2_sha256${api.ITERATIONS}${salt.hex()}${digest.hex()}'


def _replacement_pin(db, family, value):
    row = db.execute('SELECT * FROM family_replacement_pin_locks WHERE family_id=?', (family['id'],)).fetchone()
    if row and row['locked_until'] and row['locked_until'] > api.stamp():
        raise api.APIError('Cổng PIN thay thiết bị tạm khóa 15 phút.', 429)
    if isinstance(value,str) and family['pin_hash'] and callable(getattr(db,'prepare_verification',None)):db.prepare_verification(value,family['pin_hash'])
    if (not isinstance(value, str) or not re.fullmatch(r'[0-9]{6}', value) or not family['pin_hash']
            or not api.verify_password(value, family['pin_hash'])):
        count = row['failures'] + 1 if row and not row['locked_until'] else 1
        db.execute('INSERT INTO family_replacement_pin_locks VALUES(?,?,?) ON CONFLICT(family_id) '
                   'DO UPDATE SET failures=excluded.failures,locked_until=excluded.locked_until',
                   (family['id'], count, api.stamp(api.now() + PIN_LOCK) if count >= 5 else None))
        error=api.APIError('PIN phụ huynh chưa đúng.' if count < 5 else 'Cổng PIN thay thiết bị tạm khóa 15 phút.',403 if count < 5 else 429)
        if callable(getattr(db,'commit_and_raise',None)):db.commit_and_raise(error)
        db.commit()
        raise error
    db.execute('DELETE FROM family_replacement_pin_locks WHERE family_id=?', (family['id'],))


def _expire_parent(db, row):
    # Keep the device cookie stable for concurrent state reads across tabs.
    # Only the capability changes: old contexts cannot read private data.
    db.execute("UPDATE family_devices SET scope='profiles',csrf_token=?,context=?,parent_opened_at=NULL,"
               'parent_seen_at=NULL,full_authenticated_at=NULL WHERE id=?',
               (secrets.token_urlsafe(32), secrets.token_urlsafe(32), row['id']))
    return db.execute('SELECT d.*,f.email,f.password_hash,f.pin_hash family_pin_hash,p.display_name parent_name '
                      'FROM family_devices d JOIN family_accounts f ON f.id=d.family_id '
                      'JOIN family_parent_profiles p ON p.family_id=f.id WHERE d.id=?', (row['id'],)).fetchone()


def _overview(db, row, handler=None, include_game_usage=False):
    from .learning_update import membership
    from .family_features import today
    children = _children(db, row)
    game_usage = {}
    if include_game_usage:
        from . import game_claims, game_limits
        game_usage = game_limits.family_view(db, (child['student_id'] for child in children), game_claims.now(handler))
    games_by_child = {item['childId']: item for item in game_usage.pop('children', ())}
    result = []
    for child in children:
        student_id = child['student_id']
        session = _mapped(db, row, child)
        entry = {'id': student_id, 'name': api.safe_nickname(child['full_name']), 'grade': child_grade(child),
                 'membership': membership(db, session),
                 'completedLessons': db.execute('SELECT count(*) FROM lesson_progress WHERE student_id=?', (student_id,)).fetchone()[0],
                 'submittedExams': db.execute("SELECT count(*) FROM exam_attempts WHERE student_id=? AND status='submitted'", (student_id,)).fetchone()[0],
                 'today': today(handler, db, child)}
        if include_game_usage:
            entry['gameUsage'] = {**games_by_child[student_id], 'day': game_usage['day'], 'maxLimit': game_limits.MAX_LIMIT}
        result.append(entry)
    return {'overview': result, **({'gameUsage': game_usage} if include_game_usage else {})}


def request(handler, method, path, body=None):
    body = body or {}
    requested = urlsplit(path)
    path = requested.path
    handler.path = getattr(handler, 'path', '') or requested.geturl()
    if not path.startswith('/api/family/'):
        raise api.APIError('API gia đình không tồn tại.', 404)
    action = path.removeprefix('/api/family/')
    if method not in ('GET', 'POST'):
        raise api.APIError('Phương thức không hỗ trợ.', 405)
    game_usage_action = action == 'parent/game-limits'
    if game_usage_action:
        if method != 'GET':
            raise api.APIError('Phương thức không hỗ trợ.', 405)
        if body or requested.query or urlsplit(handler.path).query:
            raise api.APIError('Yêu cầu đọc lượt chơi không nhận thông tin chọn hồ sơ.')
    if not isinstance(body, dict):
        raise api.APIError('Nội dung yêu cầu không hợp lệ.')
    if method == 'POST' and (not api.same_origin(handler) or not handler.headers.get('Origin')):
        raise api.APIError('Yêu cầu phải xuất phát từ website đang mở.', 403)
    if action == 'trial-history':
        raise api.APIError('Lịch sử trải nghiệm không còn được cung cấp.', 410)
    if method == 'POST' and action in ('password/reset/request', 'password/reset/confirm'):
        from .family_features import recovery
        return recovery(handler, action, body)
    if action == 'config' and method == 'GET':
        from .website_legal import VERSION
        from .family_features import recovery_config
        return {'emailPassword': True, 'google': {'available': False, 'reason': 'Đăng nhập Google chưa được cấu hình và kiểm chứng.'},
                'legalVersion': VERSION, 'legacyLoginUrl': '/?legacy_login=1', 'passwordReset': recovery_config(),
                'minPasswordLength': 6, 'maxDevices': MAX_DEVICES, 'rememberDefault': True, 'rememberDays': 30,
                'companions': [{'code': code, 'name': api.MASCOT_DISPLAY_NAMES[code], 'artUrl': _art(code)}
                               for code in api.MASCOT_NAMES]}, 200
    if action in ('register', 'login') and method == 'POST':
        api.limit_auth(handler)
        email = _email(body)
        password = body.get('password')
        if not isinstance(password, str) or not 6 <= len(password) <= 128:
            raise api.APIError('Thông tin đăng nhập không hợp lệ.', 401)
        # Password derivation outside the write transaction.
        if action == 'register':
            credential = api.password_hash(password)
        else:
            with api.connect(handler.server.database_path) as db:
                family = db.execute("SELECT * FROM family_accounts WHERE email=? AND status='active'", (email,)).fetchone()
            if not api.verify_password(password, family['password_hash'] if family else None) or not family:
                raise api.APIError('Thông tin đăng nhập không đúng.', 401)
            credential = family['password_hash']
        with api.connect(handler.server.database_path, True) as db:
            if action == 'register':
                from .system_settings import require_feature
                from .website_legal import validate_consent
                require_feature(db, 'registration_open')
                validate_consent(body)
                key = _key(body)
                child_body = body.get('child')
                if child_body is not None and not isinstance(child_body, dict):
                    raise api.APIError('Thông tin hồ sơ con không hợp lệ.')
                parent = api.text_field({**body, 'parentName': body.get('parentName') or 'Phụ huynh'}, 'parentName', 120, 2)
                if child_body is not None:
                    _child_input(child_body)
                fingerprint = _digest({'email': email, 'parentName': parent,
                                       'child': {k: v for k, v in child_body.items() if k != 'pin'} if child_body is not None else None,
                                       'legalConsent': body.get('legalConsent')})
                family = db.execute('SELECT * FROM family_accounts WHERE registration_key=?', (key,)).fetchone()
                if family:
                    if not hmac.compare_digest(family['registration_digest'], fingerprint) or not api.verify_password(password, family['password_hash']):
                        raise api.APIError('Yêu cầu đăng ký không khớp lần trước.', 409)
                    if child_body and child_body.get('pin') is not None:
                        first_child = db.execute('SELECT pin_hash FROM family_children WHERE family_id=? AND request_key=?',
                                                 (family['id'], 'first-' + key)).fetchone()
                        if not first_child or not api.verify_password(child_body['pin'], first_child['pin_hash']):
                            raise api.APIError('PIN hồ sơ không khớp lần đăng ký trước.', 409)
                else:
                    if (db.execute('SELECT 1 FROM family_accounts WHERE email=?', (email,)).fetchone() or
                            db.execute('SELECT 1 FROM accounts WHERE lower(login_identifier)=?', (email,)).fetchone() or
                            db.execute('SELECT 1 FROM staff_users WHERE lower(login)=?', (email,)).fetchone()):
                        raise api.APIError('Không thể dùng thông tin đăng ký này. Hãy đăng nhập tài khoản hiện có.', 409)
                    fid = db.execute('INSERT INTO family_accounts(email,password_hash,registration_key,registration_digest,created_at) VALUES(?,?,?,?,?)',
                                     (email, credential, key, fingerprint, api.stamp())).lastrowid
                    db.execute('INSERT INTO family_parent_profiles VALUES(?,?,?,?)', (fid, parent, 'self_declared', api.stamp()))
                    _record_registration_consent(db, fid, body)
                    if child_body is not None:
                        _add_child(db, fid, child_body, 'first-' + key, body, legacy=True)
                    family = db.execute('SELECT * FROM family_accounts WHERE id=?', (fid,)).fetchone()
            else:
                family = db.execute("SELECT * FROM family_accounts WHERE email=? AND password_hash=? AND status='active'", (email, credential)).fetchone()
                if not family:
                    raise api.APIError('Thông tin đăng nhập vừa đổi. Hãy đăng nhập lại.', 401)
            if type(body.get('remember', True)) is not bool:
                raise api.APIError('Lựa chọn ghi nhớ thiết bị không hợp lệ.')
            existing = _row(handler, db)
            existing = existing if existing and existing['family_id'] == family['id'] else None
            devices = _devices(db, family['id'])
            if not existing and len(devices) >= MAX_DEVICES:
                replace = body.get('replaceDeviceId')
                if not replace:
                    return {'error': 'Gia đình đã đăng nhập trên 3 thiết bị. Hãy chọn máy cũ và nhập PIN phụ huynh để thay.',
                            'code': 'family_device_limit', 'maxDevices': MAX_DEVICES, 'devices': devices}, 409
                if not isinstance(replace, str) or not any(d['id'] == replace for d in devices):
                    raise api.APIError('Không tìm thấy thiết bị đang dùng trong gia đình.', 404)
                _replacement_pin(db, family, body.get('parentPin'))
                db.execute('UPDATE family_devices SET revoked_at=? WHERE id=? AND family_id=?',
                           (api.stamp(), replace, family['id']))
            return _state(db, _new_device(handler, db, family, body.get('remember', True), body.get('deviceName'), existing)), 200
    cart_action = action == 'cart' or action.startswith('cart/')
    game_limits_action = action == 'children/game-limits'
    with api.connect(handler.server.database_path, True) as db:
        row = _row(handler, db)
        if not row:
            if action == 'state' and method == 'GET':
                return {'authenticated': False}, 200
            if action == 'logout' and method == 'POST':
                handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, '', 0)}
                return {'authenticated': False}, 200
            raise api.APIError('Hãy đăng nhập tài khoản gia đình.', 401)
        _context(handler, row, required=method == 'POST' or cart_action or game_limits_action or game_usage_action)
        if method == 'POST':
            _csrf(handler, row)
        if game_usage_action:
            if (row['active_profile'] != 'parent' or row['scope'] != 'parent_full'
                    or row['allowed_student_id'] is not None or _parent_expired(row)):
                raise _error('Hãy nhập PIN phụ huynh để xem lượt chơi của các con.', 403, 'family_parent_pin_required')
            from . import game_claims, game_limits
            children = _children(db, row)
            return game_limits.family_view(db, (child['student_id'] for child in children), game_claims.now(handler)), 200
        if cart_action:
            if row['active_profile'] == 'parent' and row['allowed_student_id'] is None and (
                    row['scope'] != 'parent_full' or _parent_expired(row)):
                raise _error('Hãy nhập PIN phụ huynh để mở lại giỏ hàng.', 403, 'family_parent_pin_required')
            _require(row, full=True)
            if method == 'POST':
                db.execute('UPDATE family_devices SET parent_seen_at=? WHERE id=?', (api.stamp(), row['id']))
            from .family_cart import request as cart_request
            return cart_request(db, row, method, action, body,
                                local_pilot=getattr(handler.server, 'local_pilot', None)), 200
        if action == 'state' and method == 'GET':
            if _parent_expired(row):
                row = _expire_parent(db, row)
            return _state(db, row), 200
        if action == 'logout' and method == 'POST':
            db.execute('UPDATE family_devices SET revoked_at=? WHERE id=?', (api.stamp(), row['id']))
            handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, '', 0)}
            return {'authenticated': False}, 200
        if action == 'select' and method == 'POST':
            child = _child(db, row, body.get('childId'))
            if child['pin_hash']:
                _pin(handler, db, row, body.get('pin'), child['pin_hash'])
            return _state(db, _rotate(handler, db, row, 'child', child['student_id'])), 200
        if action == 'lock' and method == 'POST':
            return _state(db, _rotate(handler, db, row, 'profiles', row['selected_student_id'])), 200
        if action == 'parent/pin/setup' and method == 'POST':
            if row['allowed_student_id'] is not None or row['family_pin_hash']:
                raise api.APIError('Không thể thiết lập PIN phụ huynh trên phiên này.', 403)
            if not row['pin_setup_until'] or row['pin_setup_until'] <= api.stamp():
                raise _error('Hãy đăng nhập lại để thiết lập PIN phụ huynh lần đầu.', 403, 'family_pin_setup_expired')
            db.execute('UPDATE family_accounts SET pin_hash=? WHERE id=?', (_hash_pin(body.get('pin'), parent=True), row['family_id']))
            db.execute('UPDATE family_devices SET pin_setup_until=NULL WHERE family_id=?', (row['family_id'],))
            return _state(db, _rotate(handler, db, row, 'parent_full', row['selected_student_id'])), 200
        if action in ('parent/unlock', 'parent/reauth') and method == 'POST':
            if row['allowed_student_id'] is not None:
                raise api.APIError('Thiết bị này chỉ dành cho một con.', 403)
            if action == 'parent/unlock':
                _pin(handler, db, row, body.get('pin'), row['family_pin_hash'])
                scope = 'parent_full'
            else:
                raise api.APIError('Hãy dùng PIN phụ huynh để mở quyền quản lý.', 403)
            return _state(db, _rotate(handler, db, row, scope, row['selected_student_id'])), 200
        if action == 'parent/overview' and method == 'GET':
            _require(row)
            db.execute('UPDATE family_devices SET parent_seen_at=? WHERE id=?', (api.stamp(), row['id']))
            include_game_usage = (row['scope'] == 'parent_full' and row['active_profile'] == 'parent'
                                  and bool(handler.headers.get('X-Family-Context')))
            return {**_state(db, row), **_overview(db, row, handler, include_game_usage)}, 200
        _require(row, full=True)
        db.execute('UPDATE family_devices SET parent_seen_at=? WHERE id=?', (api.stamp(), row['id']))
        if game_limits_action:
            from . import game_claims, game_limits
            if method == 'GET':
                query = parse_qs(urlsplit(handler.path).query, keep_blank_values=True)
                ids = query.get('childId', [])
                child_id = int(ids[0]) if len(ids) == 1 and re.fullmatch(r'[1-9][0-9]{0,18}', ids[0]) else None
            else:
                child_id = body.get('childId')
            if type(child_id) is not int or child_id <= 0:
                raise api.APIError('Hãy chọn đúng hồ sơ con.')
            child = _child(db, row, child_id)
            if method == 'POST':
                game_limits.save(db, child['student_id'], body.get('limits'))
            return game_limits.view(db, child['student_id'], game_claims.now(handler)), 200
        if action == 'account/delete' and method == 'POST':
            if body.get('confirm') != 'XOA TAI KHOAN':
                raise api.APIError('Hãy xác nhận rõ yêu cầu đóng tài khoản.')
            _pin(handler, db, row, body.get('pin'), row['family_pin_hash'])
            notice = 'Tài khoản đã đóng và các phiên đã thu hồi. Hồ sơ học tập, giao dịch và chứng từ được giữ phục vụ đối soát; đây chưa phải xóa toàn bộ dữ liệu cá nhân.'
            db.execute("UPDATE family_accounts SET status='suspended',auth_revision=auth_revision+1 WHERE id=?", (row['family_id'],))
            db.execute('UPDATE family_devices SET revoked_at=? WHERE family_id=? AND revoked_at IS NULL', (api.stamp(), row['family_id']))
            db.execute('INSERT INTO family_closures VALUES(?,?,?)', (row['family_id'], api.stamp(), notice))
            handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, '', 0)}
            return {'authenticated': False, 'closed': True, 'message': notice}, 200
        if action == 'parent/select' and method == 'POST':
            child = _child(db, row, body.get('childId'))
            return _state(db, _rotate(handler, db, row, 'parent_full', child['student_id'], preserve_elevation=True)), 200
        if action == 'children/add' and method == 'POST':
            child_id = _add_child(db, row['family_id'], body, _key(body), body)
            return {**_state(db, row), 'addedChildId': child_id}, 200
        if action == 'parent/pin' and method == 'POST':
            pin_hash = _hash_pin(body.get('pin'), parent=True)
            db.execute('UPDATE family_accounts SET pin_hash=? WHERE id=?', (pin_hash, row['family_id']))
            db.execute("UPDATE family_devices SET revoked_at=? WHERE family_id=? AND id<>? AND scope IN ('parent_read','parent_full')",
                       (api.stamp(), row['family_id'], row['id']))
            return _state(db, _rotate(handler, db, row, 'parent_full', row['selected_student_id'], preserve_elevation=True)), 200
        if action == 'child/pin' and method == 'POST':
            child = _child(db, row, body.get('childId'))
            pin = body.get('pin')
            db.execute('UPDATE family_children SET pin_hash=? WHERE student_id=?',
                       (None if body.get('noPin') is True else _hash_pin(pin), child['student_id']))
            return _state(db, row), 200
        if action == 'devices' and method == 'GET':
            return {**_state(db, row), 'devices': _devices(db, row['family_id'])}, 200
        if action == 'devices/revoke' and method == 'POST':
            identity = body.get('deviceId')
            if not isinstance(identity, str) or not db.execute('SELECT 1 FROM family_devices WHERE id=? AND family_id=?', (identity, row['family_id'])).fetchone():
                raise api.APIError('Không tìm thấy thiết bị trong tài khoản.', 404)
            db.execute('UPDATE family_devices SET revoked_at=? WHERE id=?', (api.stamp(), identity))
            if identity == row['id']:
                handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, '', 0)}
                return {'authenticated': False}, 200
            return _state(db, row), 200
        if action == 'devices/configure' and method == 'POST':
            remember, child_only = body.get('remember', bool(row['remembered'])), body.get('childOnly', False)
            if type(remember) is not bool or type(child_only) is not bool:
                raise api.APIError('Thiết lập thiết bị không hợp lệ.')
            child = _child(db, row, body.get('childId')) if child_only else None
            selected = child['student_id'] if child else row['selected_student_id']
            db.execute('UPDATE family_devices SET remembered=?,allowed_student_id=?,device_name=?,expires_at=? WHERE id=?',
                       (int(remember), child['student_id'] if child else None, _device_name(body.get('deviceName', row['device_name'])),
                        api.stamp(api.now() + timedelta(days=30 if remember else 7)), row['id']))
            row = _row(handler, db)
            # Device restriction changes are management, not a child PIN bypass.
            return _state(db, _rotate(handler, db, row, 'profiles', selected,
                                     active_profile='child' if child_only else row['active_profile'])), 200
        if action in ('devices/logout-all', 'password') and method == 'POST':
            if action == 'password':
                credential = api.password_hash(body.get('newPassword'))
                db.execute('UPDATE family_accounts SET password_hash=?,auth_revision=auth_revision+1 WHERE id=?', (credential, row['family_id']))
                db.execute('UPDATE family_password_resets SET redeemed_at=? WHERE family_id=? AND redeemed_at IS NULL', (api.stamp(), row['family_id']))
            db.execute('UPDATE family_devices SET revoked_at=? WHERE family_id=? AND revoked_at IS NULL', (api.stamp(), row['family_id']))
            handler.api_headers = {'Set-Cookie': api.session_cookie(COOKIE, '', 0)}
            return {'authenticated': False}, 200
        raise api.APIError('API gia đình không tồn tại.', 404)


def dispatch(handler, database_path):
    """HTTP adapter for root integration when routing outside platform_request."""
    path = urlsplit(handler.path).path
    if not path.startswith('/api/family/'):
        return False
    handler.api_headers = {}
    method = handler.command
    try:
        body = None
        if method == 'POST':
            if handler.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise api.APIError('Use application/json', 415)
            length = int(handler.headers.get('Content-Length', '0'))
            if not 0 < length <= 32768:
                raise api.APIError('Nội dung yêu cầu quá lớn.', 413)
            body = json.loads(handler.rfile.read(length).decode())
        payload, status = request(handler, method, path, body)
    except api.APIError as error:
        handler.api_headers = {}
        payload, status = {'error': str(error)}, error.status
        if getattr(error, 'code', None):
            payload['code'] = error.code
        if getattr(error, 'familyAccessChanged', False):
            payload['familyAccessChanged'] = True
    except (ValueError, TypeError, UnicodeError, RecursionError):
        payload, status = {'error': 'Dữ liệu gửi lên không hợp lệ.'}, 400
    handler.json_response(status, payload)
    return True
