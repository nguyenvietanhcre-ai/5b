"""Permanent learner credits from settled family-cart lines.

The main store owns grants and serializes paid creates across both stores.
Each attempt and its debit are committed together in the store that owns it.
"""
from datetime import timedelta
import hashlib
import json
import secrets

from . import platform_api as api


QUESTIONS = 'questions-100'
EXAMS = 'exams-10'
COMPLETE_COUNT = 10
PACKS = {
    QUESTIONS: {'sku': QUESTIONS, 'unit': 'questions', 'quantity': 100, 'amount': 50000,
                'currency': 'VND', 'title': '100 lượt câu hỏi', 'expiresAt': None},
    EXAMS: {'sku': EXAMS, 'unit': 'exams', 'quantity': 10, 'amount': 50000,
            'currency': 'VND', 'title': '10 lượt tạo đề tự chọn', 'expiresAt': None},
}


def digest(value):
    normalized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(normalized.encode()).hexdigest()


def enabled(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='purchased_credit_grants'").fetchone())


def funding(body):
    if 'funding' not in body:
        if 'confirmPurchased' in body:
            raise api.APIError('Hãy chọn loại lượt trước khi xác nhận.')
        return None
    sku = body['funding']
    if not isinstance(sku, str) or sku not in PACKS:
        raise api.APIError('Nguồn lượt đã mua không hợp lệ.')
    return sku


def grant(db, account_id, student_id, sku, source_line_id):
    """Record one paid product line while its cart settlement transaction is open."""
    line = db.execute('SELECT i.*,o.status order_status FROM family_cart_product_order_items i '
                      'JOIN family_cart_orders o ON o.id=i.order_id WHERE i.id=?', (source_line_id,)).fetchone()
    if (not line or line['account_id'] != account_id or line['student_id'] != student_id
            or line['type'] != 'credits' or line['product_ref'] != sku or sku not in PACKS):
        raise api.APIError('Dòng mua lượt không khớp hồ sơ hoặc sản phẩm.', 409)
    item = json.loads(line['item_json'])
    pack = PACKS[sku]
    units = item.get('credits')
    if (type(units) is not int or units != pack['quantity'] or item.get('creditKind') != pack['unit']
            or item.get('sku') != sku or item.get('quantity') != line['quantity']
            or not 1 <= line['quantity'] <= 10):
        raise api.APIError('Số lượt đã chốt trong đơn cần được rà lại.', 409)
    quantity = units * line['quantity']
    old = db.execute('SELECT id,account_id,student_id,sku,quantity FROM purchased_credit_grants WHERE source_line_id=?',
                     (source_line_id,)).fetchone()
    if old:
        if tuple(old)[1:] != (account_id, student_id, sku, quantity):
            raise api.APIError('Quyền đã cấp không khớp dòng đơn.', 409)
        return old['id']
    if line['order_status'] != 'pending' or not db.execute('SELECT 1 FROM students WHERE id=? AND account_id=?',
                                                          (student_id, account_id)).fetchone():
        raise api.APIError('Dòng đơn không còn chờ cấp lượt cho hồ sơ này.', 409)
    return db.execute('INSERT INTO purchased_credit_grants(source_line_id,account_id,student_id,sku,quantity,granted_at) '
                      'VALUES (?,?,?,?,?,?)', (source_line_id, account_id, student_id, sku, quantity, api.stamp())).lastrowid


def store_key(db):
    if db is not None and enabled(db):
        return db.execute('SELECT store_key FROM purchased_credit_native_store WHERE id=1').fetchone()[0]
    return None


def bind_native(main_database, student_id, key):
    """Commit the store identity before it can take a debit for this learner."""
    with api.connect(main_database, True) as db:
        binding = db.execute('SELECT store_key FROM purchased_credit_native_bindings WHERE student_id=?',
                             (student_id,)).fetchone()
        if not key or binding and binding[0] != key:
            unavailable()
        if not binding:
            db.execute('INSERT INTO purchased_credit_native_bindings VALUES (?,?)', (student_id, key))


def unavailable():
    raise api.APIError('Chưa đối soát được lượt đã mua với kho luyện tập. Hãy thử lại sau.', 503)


def balance(db, student_id, native_db=None):
    totals = {QUESTIONS: 0, EXAMS: 0}
    if enabled(db):
        totals.update(db.execute('SELECT g.sku,SUM(g.quantity) FROM purchased_credit_grants g '
                                 'JOIN family_cart_product_order_items i ON i.id=g.source_line_id '
                                 'JOIN family_cart_orders o ON o.id=i.order_id WHERE g.student_id=? AND o.status=\'paid\' '
                                 'GROUP BY g.sku', (student_id,)))
        binding = db.execute('SELECT store_key FROM purchased_credit_native_bindings WHERE student_id=?',
                             (student_id,)).fetchone()
        if binding and binding[0] != store_key(native_db):
            unavailable()
        for source in (db, native_db if binding else None):
            if source is None:
                continue
            for sku, spent in source.execute('SELECT sku,SUM(quantity) FROM purchased_credit_usage '
                                             'WHERE bank_key=? AND bank_student_id=? GROUP BY sku',
                                             (store_key(db), student_id)):
                totals[sku] -= spent
        if min(totals.values()) < 0:
            unavailable()
    return {'questionsRemaining': totals[QUESTIONS], 'examsRemaining': totals[EXAMS], 'expiresAt': None}


def amount_left(balances, sku):
    return balances[PACKS[sku]['unit'] + 'Remaining']


def allocation(sku, balances, question_keys):
    quantity = len(question_keys) if sku == QUESTIONS else 1
    remaining = amount_left(balances, sku)
    if not remaining or quantity > remaining:
        raise api.APIError('Không đủ lượt đã mua để tạo đề này. Số dư được giữ nguyên.', 402)
    return {'sku': sku, 'unit': PACKS[sku]['unit'], 'quantity': quantity,
            'remainingBefore': remaining, 'remainingAfter': remaining - quantity, 'expiresAt': None}


def recent_request(db, session, request_key, body):
    old = db.execute('SELECT exam_id,request_hash FROM purchased_credit_usage WHERE student_id=? AND request_key=?',
                     (session['student_id'], request_key)).fetchone()
    if not old:
        return None
    if old['request_hash'] != digest(body):
        raise api.APIError('Mã yêu cầu đã dùng với nội dung khác.', 409)
    return api.exam_view(db, api.owned_attempt(db, session, old['exam_id']))


def quote(db, session, sku, criteria, payload):
    qid = 'credits-' + secrets.token_hex(16)
    expires = api.stamp(api.now() + timedelta(minutes=2))
    db.execute('INSERT INTO purchased_credit_quotes VALUES (?,?,?,?,?,?)',
               (qid, session['student_id'], sku, digest(criteria), api.packed(payload), expires))
    return {'quoteId': qid, 'expiresAt': expires}


def confirm(db, session, sku, criteria, body):
    from .wallet_qa import QuoteChanged
    qid = body.get('quoteId')
    row = db.execute('SELECT * FROM purchased_credit_quotes WHERE quote_id=? AND student_id=?',
                     (qid, session['student_id'])).fetchone() if isinstance(qid, str) else None
    if (not row or row['sku'] != sku or row['criteria_hash'] != digest(criteria)
            or row['expires_at'] <= api.stamp() or body.get('confirmPurchased') is not True):
        raise QuoteChanged({}, purchased=True)
    if db.execute('SELECT 1 FROM purchased_credit_usage WHERE quote_id=?', (qid,)).fetchone():
        raise api.APIError('Xác nhận này đã được dùng để tạo một đề.', 409)
    return json.loads(row['quote_json'])


def debit(db, session, bank_db, bank_student_id, eid, body, plan, question_keys):
    key = api.text_field(body, 'requestKey', 80, 8)
    sid = session['student_id']
    bank_key = store_key(bank_db)
    db.execute('INSERT INTO purchased_credit_usage VALUES (?,?,?,?,?,?,?,?,?,?,?)',
               (eid, sid, bank_key, bank_student_id, plan['sku'], plan['quantity'], body['quoteId'],
                key, digest(body), api.stamp(), body.get('intentId')))
    db.executemany('INSERT INTO purchased_credit_question_usage VALUES (?,?,?,?)',
                   [(bank_key, sid, content_key, eid) for content_key in question_keys])


def receipt(db, student_id, exam_id):
    if not enabled(db):
        return None
    row = db.execute('SELECT sku,quantity,spent_at FROM purchased_credit_usage WHERE student_id=? AND exam_id=?',
                     (student_id, exam_id)).fetchone()
    if row:
        return {'sku': row['sku'], 'unit': PACKS[row['sku']]['unit'], 'quantity': row['quantity'],
                'spentAt': row['spent_at'], 'expiresAt': None}


def main_inventory(db, session, grade):
    from .content_retirement import retired
    from .question_bank import published_version_ids
    if retired(db, grade):
        return 0, 0
    counts = [len(published_version_ids(db, grade, level, session=session, purpose='practice'))
              for level in (1, 2, 3, 4)]
    return sum(counts), max(counts, default=0)


def catalogue(db, session, local_pilot=None, *, native_db=None):
    """Report actual accessible source size and remaining permanent credits."""
    from contextlib import nullcontext
    from sqlite3 import Error
    from .system_settings import settings

    grade = api.grade_for_student(db, session['student_id'], session['birth_year'])
    pilot = local_pilot is not None and local_pilot.practice is not None and (grade == 5 or hasattr(local_pilot.practice,'supports_grade') and local_pilot.practice.supports_grade(grade))
    viewer = 'pilot' if pilot else 'main'
    scope = (f'Kho lớp {grade} trên localhost. Học liệu tự biên soạn đang chờ giáo viên độc lập rà soát.'
             if pilot else f'Kho câu luyện tập lớp {grade} đã phát hành, trong phạm vi quyền hiện có.')
    try:
        context = nullcontext(native_db) if native_db is not None else native_connection(local_pilot)
        with context as source:
            values = balance(db, session['student_id'], source)
            if pilot:
                inventory = local_pilot.paid_inventory(source,grade) if hasattr(local_pilot.practice,'supports_grade') else local_pilot.paid_inventory(source)
            else:
                inventory = main_inventory(db, session, grade)
        available = enabled(db) and settings(db)['practice_open']
    except (api.APIError, Error, OSError):
        values = {'questionsRemaining': None, 'examsRemaining': None, 'expiresAt': None}
        inventory = (0, 0)
        available = False
    question_count, largest_pool = inventory
    no_source = 'Hiện chưa đủ câu hợp lệ trong kho để dùng gói này.'
    no_store = 'Kho luyện tập hoặc số dư đã mua hiện chưa sẵn sàng.'
    options = [1, 2, 3, 5, 10] if pilot else [3, 10]
    products = []
    for sku, pack in PACKS.items():
        counts = [n for n in options if n <= largest_pool and (sku == QUESTIONS or n == COMPLETE_COUNT)]
        eligible = bool(available and counts and (question_count > 0 or sku == EXAMS))
        products.append({**pack, 'grade': grade, 'provider': viewer, 'eligible': eligible,
                         'eligibleCounts': counts if eligible else [], 'scopeLabel': scope,
                         'sourceQuestionCount': question_count if sku == QUESTIONS else largest_pool,
                         'reason': '' if eligible else no_source if available else no_store})
    return {**values, 'available': bool(available), 'products': products}


def native_connection(local_pilot):
    from contextlib import nullcontext
    if local_pilot is None:
        return nullcontext(None)
    if not hasattr(local_pilot.path,'connect') and not local_pilot.path.is_file():
        unavailable()
    return api.connect(local_pilot.path)
