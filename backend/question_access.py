"""Version-pinned bank classification, compatibility inventory and scoped rights.

Legacy compatibility is not a content review or a tier assignment. Activation of
the classified selector is an integration decision after every runtime source
has been inventoried and its game pools checked on a database copy.
"""
import hashlib
import hmac
import json
import re
from urllib.parse import parse_qs, urlsplit

TIERS = ('trial', 'free', 'vip', 'vip_plus')
PURPOSES = ('practice', 'arena', 'group-games', 'premium', 'exam-sale')
PIN_KEYS = ('question_id', 'revision', 'grade_id', 'topic_id', 'difficulty',
            'curriculum_week', 'prompt_json', 'grading_rule_json',
            'solution_steps_json', 'hints_json', 'options_json')
BASE = '/api/staff/question-access'


def fail(message, status=400):
    from .platform_api import APIError
    raise APIError(message, status)


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def version(db, identity):
    return db.execute('SELECT v.*,q.grade_id,q.topic_id,q.question_code,t.title topic '
                      'FROM question_versions v JOIN questions q ON q.id=v.question_id '
                      'JOIN topics t ON t.id=q.topic_id WHERE v.id=?', (identity,)).fetchone()


def pin(row):
    return {key: row[key] for key in PIN_KEYS}


def digest(row):
    return hashlib.sha256(packed(pin(row)).encode()).hexdigest()


def policy(db):
    row = db.execute('SELECT mode,baseline FROM question_access_policy WHERE id=1').fetchone()
    return {**dict(row), 'note': 'Allowlist cũ không phải nhãn Free hoặc xác nhận duyệt học liệu.'}


def legacy_allowed(db, row):
    old = db.execute('SELECT pin_json FROM question_access_legacy WHERE version_id=?', (row['id'],)).fetchone()
    return bool(old and json.loads(old[0]) == pin(row))


def snapshot_seed_versions(db, identities):
    """Pin only the original BANK2 sample bootstrap, before its one-time marker.

    New installs create these known sample fixtures after SQL migrations. This
    never sweeps arbitrary published rows or adds pedagogical approvals.
    """
    # Historical migration rehearsals seed a deliberately old schema before
    # upgrading it. Do not create future tables or rights in that schema:
    # migration0035 will capture the published baseline during the upgrade.
    # Selectors still require policy/allowlist tables; this is no access fallback.
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='question_access_legacy'").fetchone():
        return
    if db.execute("SELECT 1 FROM system_settings WHERE name='private_question_bank'").fetchone():
        return
    for identity in identities:
        row = version(db, identity)
        if not row or not row['question_code'].startswith('BANK2-'):
            fail('Nguồn khởi tạo mẫu không hợp lệ.', 503)
        db.execute('INSERT OR IGNORE INTO question_access_legacy VALUES (?,?,?)',
                   (identity, 'bank2-initial-sample-v2', packed(pin(row))))


def entitled_tiers(db, session):
    if not session or not session['account_id'] or not session['student_id']:
        return ()
    from .learning_update import membership
    role = membership(db, session)
    return ('free', 'vip', 'vip_plus') if role in ('VIP+', 'SVip') else ('free', 'vip') if role == 'VIP' else ('free',)


def allowed(db, identity, *, session=None, purpose='practice', public_game=False,
            trial_ids=(), allow_legacy=True):
    if purpose not in PURPOSES:
        return False
    row = version(db, identity)
    if not row or row['status'] != 'published':
        return False
    from .curriculum_samples import main_allowed
    sample=main_allowed(db,identity,session=session,purpose=purpose,public_game=public_game)
    if sample is not None:return sample
    if policy(db)['mode'] == 'legacy':
        return bool(allow_legacy and legacy_allowed(db, row))
    label = db.execute('SELECT * FROM question_access_labels WHERE version_id=?', (identity,)).fetchone()
    if label:
        if (label['review_status'] != 'approved' or label['content_sha256'] != digest(row)
                or purpose not in json.loads(label['purposes_json'])):
            return False
        if label['tier'] == 'trial':
            # A trial consumer must supply its server-pinned finite allowlist.
            return identity in trial_ids and purpose == 'practice'
        if public_game:
            return label['tier'] == 'free' and purpose in ('arena', 'group-games')
        return label['tier'] in entitled_tiers(db, session)
    return False


def filter_ids(db, identities, **access):
    """Choose latest eligible pinned version, not newest unclassified revision."""
    chosen = {}
    for identity in identities:
        row = version(db, identity)
        if row and allowed(db, identity, **access):
            previous = chosen.get(row['question_id'])
            if previous is None or row['revision'] > previous[0]:
                chosen[row['question_id']] = (row['revision'], identity)
    return [item[1] for item in chosen.values()]


def valid_payload(db, payload, *, session=None, purpose='premium', sale=False):
    if not isinstance(payload, dict) or type(payload.get('grade')) is not int:
        return False
    ids = payload.get('ids')
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100 or
            any(type(item) is not int for item in ids) or len(set(ids)) != len(ids)):
        return False
    for identity in ids:
        row = version(db, identity)
        if not row or row['grade_id'] != payload['grade']:
            return False
        if sale:
            # Product publication may offer an independently purchasable tier;
            # it does not grant a learner access until payment is verified.
            label = db.execute('SELECT * FROM question_access_labels WHERE version_id=?', (identity,)).fetchone()
            valid = (row['status'] == 'published' and label and label['tier'] != 'trial'
                     and label['review_status'] == 'approved' and label['content_sha256'] == digest(row)
                     and 'exam-sale' in json.loads(label['purposes_json']))
            if policy(db)['mode'] == 'legacy':
                valid = row['status'] == 'published' and legacy_allowed(db, row)
            if not valid:
                return False
        elif not allowed(db, identity, session=session, purpose=purpose):
            return False
    return True


def pin_order(db, order_id, payload):
    for identity in payload['ids']:
        row = version(db, identity)
        db.execute('INSERT OR IGNORE INTO question_access_order_pins VALUES (?,?,?)',
                   (order_id, identity, packed(pin(row))))


def purchased_payload(db, session, order_id):
    """Return only a paid owner's exact immutable order payload and version pins."""
    order = db.execute("SELECT * FROM payment_orders WHERE id=? AND account_id=? AND purchase_type='exam' AND status='paid'",
                       (order_id, session['account_id'])).fetchone()
    if not order:
        fail('Không tìm thấy quyền mua đề đã thanh toán.', 403)
    payload = json.loads(order['exam_payload_json'])
    ids = payload.get('ids', [])
    if not ids or len(set(ids)) != len(ids):
        fail('Bản lưu đề mua cần được kiểm tra.', 503)
    for identity in ids:
        row = version(db, identity)
        old = db.execute('SELECT pin_json FROM question_access_order_pins WHERE order_id=? AND version_id=?', (order_id, identity)).fetchone()
        if not row or not old or json.loads(old[0]) != pin(row) or row['grade_id'] != payload['grade']:
            fail('Phiên bản đề mua đã thay đổi; chưa cấp bài hoặc trừ lượt.', 503)
    return payload


def inventory(db):
    """Read-only counts for a supplied snapshot, never claims live runtime totals."""
    counts = [dict(r) for r in db.execute(
        "SELECT q.grade_id grade,t.title topic,v.difficulty,v.status,COALESCE(a.tier,'unmapped') tier,"
        "COALESCE(a.review_status,'unmapped') reviewStatus,count(*) count FROM question_versions v "
        'JOIN questions q ON q.id=v.question_id JOIN topics t ON t.id=q.topic_id '
        'LEFT JOIN question_access_labels a ON a.version_id=v.id '
        'GROUP BY q.grade_id,t.id,v.difficulty,v.status,a.tier,a.review_status')]
    return {'counts': counts, 'policy': policy(db),
            'legacyCount': db.execute('SELECT count(*) FROM question_access_legacy').fetchone()[0],
            'orderPins': db.execute('SELECT count(*) FROM question_access_order_pins').fetchone()[0]}


def item_view(db, row):
    from .platform_api import blocks_text
    label = db.execute('SELECT * FROM question_access_labels WHERE version_id=?', (row['id'],)).fetchone()
    return {'versionId': row['id'], 'questionCode': row['question_code'], 'revision': label['revision'] if label else 0,
            'contentRevision': row['revision'], 'grade': row['grade_id'], 'difficulty': row['difficulty'],
            'topic': row['topic'], 'week': row['curriculum_week'], 'status': row['status'],
            'prompt': blocks_text(json.loads(row['prompt_json'])), 'tier': label['tier'] if label else None,
            'purposes': json.loads(label['purposes_json']) if label else [],
            'reviewStatus': label['review_status'] if label else 'unmapped',
            'sourceNote': label['source_note'] if label else '',
            'contentUnchanged': bool(label and label['content_sha256'] == digest(row))}


def classify(db, user, identity, body):
    from .staff_api import require_admin, audit
    from .platform_api import stamp
    require_admin(user)
    row = version(db, identity)
    if not row:
        fail('Không tìm thấy phiên bản câu hỏi.', 404)
    if not isinstance(body, dict) or set(body) - {'tier', 'purposes', 'reviewStatus', 'sourceNote', 'expectedRevision'}:
        fail('Thông tin phân loại không hợp lệ.')
    tier, purposes, review = body.get('tier'), body.get('purposes'), body.get('reviewStatus')
    if (tier not in TIERS or not isinstance(purposes, list) or not purposes or
            any(not isinstance(x, str) or x not in PURPOSES for x in purposes) or len(set(purposes)) != len(purposes)
            or review not in ('draft', 'approved', 'rejected')):
        fail('Nhóm quyền, mục đích hoặc trạng thái duyệt không hợp lệ.')
    note = body.get('sourceNote')
    if not isinstance(note, str) or not 1 <= len(note.strip()) <= 2000:
        fail('Ghi nguồn và căn cứ kiểm tra trước khi lưu phân loại.')
    if tier == 'trial' and purposes != ['practice']:
        fail('Câu trải nghiệm chỉ dùng trong bộ mẫu luyện tập riêng.')
    if any(x in purposes for x in ('arena', 'group-games')) and tier != 'free':
        fail('Game công khai chỉ sử dụng câu Free được duyệt đúng mục đích.')
    old = db.execute('SELECT revision FROM question_access_labels WHERE version_id=?', (identity,)).fetchone()
    current = old[0] if old else 0
    if type(body.get('expectedRevision')) is not int or body['expectedRevision'] != current:
        fail('Phân loại đã thay đổi. Tải lại trước khi lưu.', 409)
    if review == 'approved' and row['status'] != 'published':
        fail('Chỉ duyệt quyền cho phiên bản đã phát hành; không tự phát hành câu.', 409)
    db.execute('INSERT INTO question_access_labels VALUES (?,?,?,?,?,?,?,?,?) '
               'ON CONFLICT(version_id) DO UPDATE SET tier=excluded.tier,purposes_json=excluded.purposes_json,'
               'review_status=excluded.review_status,source_note=excluded.source_note,content_sha256=excluded.content_sha256,'
               'revision=excluded.revision,staff_id=excluded.staff_id,updated_at=excluded.updated_at',
               (identity, tier, packed(purposes), review, note.strip(), digest(row), current + 1, user['id'], stamp()))
    audit(db, user, 'classify', 'question_access', identity, tier + '/' + review + '/' + ','.join(purposes))
    return {'item': item_view(db, row)}


def request(handler, method, path, body=None, *, database_path=None):
    """Tuple adapter for the existing server platform_request dispatcher."""
    from . import platform_api as api
    from .staff_api import read_session, require_admin
    if method not in ('GET', 'POST'):
        fail('Phương thức không hợp lệ.', 405)
    if method == 'POST' and not api.same_origin(handler):
        fail('Yêu cầu phải xuất phát từ website đang mở.', 403)
    with api.connect(database_path or handler.server.database_path, method == 'POST') as db:
        user = read_session(handler, db)
        if not user:
            fail('Đăng nhập quản trị viên để tiếp tục.', 401)
        require_admin(user)
        if method == 'POST' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token', ''), user['csrf_token']):
            fail('Phiên đăng nhập cần được tải lại.', 403)
        match = re.fullmatch(BASE + r'/versions/([1-9][0-9]*)', path)
        if match and method == 'POST':
            return classify(db, user, int(match[1]), body), 200
        if path != BASE or method != 'GET':
            fail('Không tìm thấy chức năng phân loại.', 404)
        query = parse_qs(urlsplit(handler.path).query)
        try:
            page = max(1, min(100000, int(query.get('page', ['1'])[0])))
            grade = int(query.get('grade', ['0'])[0])
        except ValueError:
            fail('Bộ lọc trang hoặc khối không hợp lệ.')
        if grade not in range(6):
            fail('Khối không hợp lệ.')
        tier, review = query.get('tier', [''])[0], query.get('review', [''])[0]
        if tier not in ('', 'unmapped') + TIERS or review not in ('', 'unmapped', 'draft', 'approved', 'rejected'):
            fail('Bộ lọc phân loại không hợp lệ.')
        where = 'WHERE (?=0 OR q.grade_id=?) AND (?=\'\' OR COALESCE(a.tier,\'unmapped\')=?) AND (?=\'\' OR COALESCE(a.review_status,\'unmapped\')=?)'
        args = (grade, grade, tier, tier, review, review)
        joins = 'FROM question_versions v JOIN questions q ON q.id=v.question_id LEFT JOIN question_access_labels a ON a.version_id=v.id '
        total = db.execute('SELECT count(*) ' + joins + where, args).fetchone()[0]
        identities = db.execute('SELECT v.id ' + joins + where + ' ORDER BY q.grade_id,v.id LIMIT 40 OFFSET ?', args + ((page - 1) * 40,)).fetchall()
        return {**inventory(db), 'items': [item_view(db, version(db, r[0])) for r in identities], 'page': page, 'pageSize': 40, 'total': total}, 200


def dispatch(handler, database_path):
    """Standalone bool hook; catches only expected API errors and writes JSON."""
    from .platform_api import APIError
    path = urlsplit(handler.path).path
    if path != BASE and not path.startswith(BASE + '/'):
        return False
    try:
        method = handler.command
        body = None
        if method == 'POST':
            if handler.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                fail('Use application/json', 415)
            try:
                size = int(handler.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    fail('Invalid request size', 413)
                body = json.loads(handler.rfile.read(size))
            except (ValueError, UnicodeError):
                fail('Invalid JSON body')
        result, status = request(handler, method, path, body, database_path=database_path)
    except APIError as error:
        result, status = {'error': str(error)}, error.status
    handler.json_response(status, result)
    return True
