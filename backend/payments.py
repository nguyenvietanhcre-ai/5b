"""Server-owned orders and authenticated SePay bank-transfer settlement.

All callers settle inside a single BEGIN IMMEDIATE transaction. Neither a browser
claim nor a webhook return URL grants access. Bank event IDs and order IDs each
have an independent database uniqueness guard.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlsplit

from .platform_api import APIError, VN, connect, now, stamp

VIP_UNIT_PRICE = 100000
MAX_AMOUNT = 10**12
REASONS = {
    'settled': 'Đã xác nhận và cập nhật tài khoản',
    'outgoing': 'Giao dịch tiền ra, không cấp quyền',
    'unknown_reference': 'Không tìm thấy mã đơn',
    'ambiguous_reference': 'Có nhiều mã đơn trong giao dịch',
    'receiver_unconfigured': 'Đơn chưa có thông tin tài khoản nhận',
    'wrong_receiver': 'Không khớp ngân hàng hoặc tài khoản nhận của đơn',
    'amount_mismatch': 'Số tiền không khớp đơn',
    'order_paid': 'Đơn đã thanh toán; cần kiểm tra tiền chuyển thêm',
    'order_cancelled': 'Đơn đã hủy',
    'account_unavailable': 'Tài khoản học sinh đang khóa hoặc đã xóa',
    'student_mismatch': 'Thông tin tài khoản và học sinh không khớp',
    'fee_mismatch': 'Học phí đã đổi học sinh, lớp, tháng hoặc số tiền',
    'fee_paid': 'Khoản học phí đã được thanh toán',
    'invalid_product': 'Thông tin gói VIP không hợp lệ',
    'internal_account': 'Tài khoản đã có quyền SVip; cần đối soát',
    'purchase_conflict': 'Mã mua VIP đã được ghi nhận khác thông tin đơn',
}


def bank_configuration():
    values = tuple(os.environ.get('MAM_TOAN_BANK_' + key, '').strip()
                   for key in ('ID', 'ACCOUNT', 'NAME'))
    bank, account, owner = values
    valid = bool(re.fullmatch(r'[A-Za-z0-9]{2,20}', bank) and
                 re.fullmatch(r'[0-9]{6,19}', account) and
                 0 < len(owner) <= 200 and not any(ord(c) < 32 for c in owner))
    return values if valid else ('', '', '')


def automation_enabled():
    secret = os.environ.get('MAM_TOAN_SEPAY_WEBHOOK_SECRET', '')
    return bool(os.environ.get('MAM_TOAN_SEPAY_ENABLED') == '1' and
                32 <= len(secret) <= 1024 and all(bank_configuration()))


def _bank_key(value):
    key = re.sub(r'[^A-Z0-9]', '', value.upper())
    aliases = {
        '970416': 'ACB', 'ASIACOMMERCIALBANK': 'ACB',
        '970436': 'VIETCOMBANK', 'VCB': 'VIETCOMBANK',
        '970407': 'TECHCOMBANK', 'TCB': 'TECHCOMBANK',
        '970422': 'MBBANK', 'MB': 'MBBANK',
        '970415': 'VIETINBANK', 'ICB': 'VIETINBANK', 'CTG': 'VIETINBANK',
        '970418': 'BIDV', '970423': 'TPBANK', 'TPB': 'TPBANK',
        '970432': 'VPBANK', 'VPB': 'VPBANK', '970403': 'SACOMBANK', 'STB': 'SACOMBANK',
        '970426': 'MSB', '970448': 'OCB', '970452': 'KIENLONGBANK', 'KLB': 'KIENLONGBANK',
        '970424': 'SHINHANBANK', 'SHBVN': 'SHINHANBANK',
    }
    return aliases.get(key, key)


def order_view(order):
    result = dict(order)
    bank, account, owner = (result.get('bank_id') or '', result.get('bank_account') or '',
                            result.get('bank_name') or '')
    result.update(bank=bank, bankAccount=account, bankName=owner, qrUrl='',
                  automationEnabled=automation_enabled())
    if (result['status'] == 'pending' and re.fullmatch(r'[A-Za-z0-9]{2,20}', bank) and
            re.fullmatch(r'[0-9]{6,19}', account) and owner):
        result['qrUrl'] = f'https://img.vietqr.io/image/{bank}-{account}-compact2.png?' + urlencode({
            'amount': result['amount'], 'addInfo': result['reference'], 'accountName': owner})
    return result


def order_status(db, session, identity):
    if type(identity) is not int or not 1 <= identity <= 2**63 - 1:
        raise APIError('Không tìm thấy đơn thanh toán của tài khoản này.', 404)
    row = db.execute('SELECT * FROM payment_orders WHERE id=? AND account_id=?',
                     (identity, session['account_id'])).fetchone()
    if not row:
        raise APIError('Không tìm thấy đơn thanh toán của tài khoản này.', 404)
    return {'order': order_view(row)}


def create_order(db, session, body):
    from .learning_update import enrolled, membership
    fee_id = body.get('feeId')
    if fee_id is not None and (type(fee_id) is not int or fee_id <= 0):
        raise APIError('Khoản học phí không hợp lệ.')
    fee = None
    if fee_id is not None:
        fee = db.execute('SELECT * FROM class_fees WHERE id=? AND student_id=?',
                         (fee_id, session['student_id'])).fetchone()
        if not fee:
            raise APIError('Học phí không thuộc tài khoản của em.', 404)
        enrolled(db, session, fee['class_id'])
        if fee['paid_at'] or fee['amount'] == 0:
            raise APIError('Tháng này đã nộp hoặc không có học phí.')
        amount = fee['amount']
    else:
        if membership(db, session) == 'SVip':
            raise APIError('Học sinh nội bộ đã có đầy đủ quyền học.', 403)
        amount = VIP_UNIT_PRICE
    order = db.execute("SELECT * FROM payment_orders WHERE account_id=? AND coalesce(fee_id,0)=? AND status='pending'",
                       (session['account_id'], fee_id or 0)).fetchone()
    if order and order['amount'] != amount:
        # A QR already shown must never silently become a different purchase.
        db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (order['id'],))
        order = None
    bank, account, owner = bank_configuration()
    if order is None:
        identity = db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at,kind,'
            'vip_months,vip_unit_price,fee_student_id,fee_class_id,fee_month,bank_id,bank_account,bank_name) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (session['account_id'], fee_id, 'BM' + secrets.token_hex(10).upper(), amount, stamp(),
             'tuition' if fee else 'vip', None if fee else 1, None if fee else VIP_UNIT_PRICE,
             fee['student_id'] if fee else None, fee['class_id'] if fee else None, fee['month'] if fee else None,
             bank or None, account or None, owner or None)).lastrowid
    else:
        identity = order['id']
        # Legacy orders have no invented receiver. Bind only when the owner asks
        # for their payment instructions and a complete bank config is present.
        if bank and not order['bank_id'] and not order['bank_account'] and not order['bank_name']:
            db.execute('UPDATE payment_orders SET bank_id=?,bank_account=?,bank_name=? WHERE id=?',
                       (bank, account, owner, identity))
    return {'order': order_view(db.execute('SELECT * FROM payment_orders WHERE id=?', (identity,)).fetchone())}


def settlement_problem(db, order):
    if order['status'] != 'pending':
        return 'order_paid' if order['status'] == 'paid' else 'order_cancelled'
    account = db.execute('SELECT id,status,deleted_at FROM accounts WHERE id=?', (order['account_id'],)).fetchone()
    if not account or account['status'] != 'active' or account['deleted_at'] is not None:
        return 'account_unavailable'
    student = db.execute('SELECT id,status FROM students WHERE account_id=?', (order['account_id'],)).fetchone()
    if not student or student['status'] != 'active':
        return 'student_mismatch'
    if order['kind'] == 'tuition' and order['fee_id'] is not None:
        fee = db.execute('SELECT * FROM class_fees WHERE id=?', (order['fee_id'],)).fetchone()
        if (not fee or fee['student_id'] != student['id'] or fee['student_id'] != order['fee_student_id'] or
                fee['class_id'] != order['fee_class_id'] or fee['month'] != order['fee_month'] or
                fee['amount'] != order['amount'] or fee['amount'] <= 0):
            return 'fee_mismatch'
        if fee['paid_at'] or db.execute("SELECT 1 FROM payment_orders WHERE fee_id=? AND status='paid'", (fee['id'],)).fetchone():
            return 'fee_paid'
    elif order['kind'] == 'vip' and order['fee_id'] is None:
        if (type(order['vip_months']) is not int or not 1 <= order['vip_months'] <= 120 or
                type(order['vip_unit_price']) is not int or order['vip_unit_price'] <= 0 or
                order['amount'] != order['vip_unit_price'] * order['vip_months']):
            return 'invalid_product'
        if db.execute("SELECT 1 FROM access_entitlements WHERE kind='internal' AND account_id=? AND starts_at<=? "
                      'AND (ends_at IS NULL OR ends_at>?)', (order['account_id'], stamp(), stamp())).fetchone():
            return 'internal_account'
        purchase = db.execute('SELECT account_id,months FROM vip_purchases WHERE payment_ref=?',
                              ('STAFF-ORDER-' + str(order['id']),)).fetchone()
        if purchase and (purchase['account_id'] != order['account_id'] or purchase['months'] != order['vip_months']):
            return 'purchase_conflict'
    else:
        return 'invalid_product'
    return None


def settle_order(db, order, source, receipt_id=None):
    """Apply the existing VIP trigger or exact fee once; caller owns transaction."""
    if order['status'] == 'paid':
        return False
    problem = settlement_problem(db, order)
    if problem:
        raise APIError(REASONS[problem] + '. Kiểm tra lại trước khi xác nhận.', 409)
    confirmed = stamp()
    if order['kind'] == 'tuition':
        db.execute('UPDATE class_fees SET paid_at=? WHERE id=? AND paid_at IS NULL', (confirmed, order['fee_id']))
        db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,created_at) "
            "VALUES (?,'staff_message','Thanh toán học phí thành công',?,'5BMath','system',?)",
            (order['account_id'], 'Học phí tháng ' + order['fee_month'] + ' đã hoàn thành. Mã thanh toán: ' + order['reference'] + '.', confirmed))
    else:
        # Keep one key for both legacy staff confirmations and bank webhooks.
        db.execute('INSERT OR IGNORE INTO vip_purchases(account_id,payment_ref,months,confirmed_at) VALUES (?,?,?,?)',
                   (order['account_id'], 'STAFF-ORDER-' + str(order['id']), order['vip_months'], confirmed))
    db.execute("UPDATE payment_orders SET status='paid',paid_at=?,confirmed_source=?,receipt_id=? WHERE id=? AND status='pending'",
               (confirmed, source, receipt_id, order['id']))
    return True


def _text(payload, key, maximum, empty=False):
    value = payload.get(key, '' if empty else None)
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
        raise APIError('Thông tin giao dịch không hợp lệ.')
    if any(ord(character) < 32 for character in value):
        raise APIError('Thông tin giao dịch không hợp lệ.')
    return value


def _payload(raw_body):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    try:
        payload = json.loads(raw_body.decode('utf-8'), object_pairs_hook=unique_keys,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Invalid JSON number')))
    except (ValueError, UnicodeError, RecursionError):
        raise APIError('Nội dung giao dịch phải là JSON hợp lệ.')
    if not isinstance(payload, dict):
        raise APIError('Nội dung giao dịch phải là một đối tượng JSON.')
    return payload


def _verify(headers, raw_body):
    if not automation_enabled():
        raise APIError('Kết nối thanh toán tự động chưa được cấu hình.', 503)
    if not isinstance(raw_body, bytes) or not 0 < len(raw_body) <= 16384:
        raise APIError('Kích thước thông báo không hợp lệ.', 413)
    timestamp = headers.get('X-SePay-Timestamp', '')
    signature = headers.get('X-SePay-Signature', '')
    if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{1,12}', timestamp):
        raise APIError('Chữ ký thông báo không hợp lệ.', 401)
    if abs(now().timestamp() - int(timestamp)) > 300:
        raise APIError('Thông báo thanh toán đã hết thời gian xác thực.', 401)
    if not isinstance(signature, str) or not re.fullmatch(r'sha256=[a-fA-F0-9]{64}', signature):
        raise APIError('Chữ ký thông báo không hợp lệ.', 401)
    expected = hmac.new(os.environ['MAM_TOAN_SEPAY_WEBHOOK_SECRET'].encode('utf-8'),
                        timestamp.encode('ascii') + b'.' + raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature[7:].lower()):
        raise APIError('Chữ ký thông báo không hợp lệ.', 401)


def _transaction_time(payload):
    value = payload.get('transactionDate')
    if value in (None, ''):
        return None
    if not isinstance(value, str) or len(value) != 19:
        raise APIError('Thời gian giao dịch không hợp lệ.')
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=VN)
    except ValueError:
        raise APIError('Thời gian giao dịch không hợp lệ.')
    return stamp(parsed)


def _find_order(db, code, content):
    # A supplied code must match exactly; do not repair or guess a mistyped code.
    if code:
        order = db.execute('SELECT * FROM payment_orders WHERE reference=? COLLATE NOCASE', (code,)).fetchone()
        references = {token.upper() for token in re.findall(
            r'(?<![A-Za-z0-9])(?:BM[A-Fa-f0-9]{20}|5B[A-Fa-f0-9]{11,30})(?![A-Za-z0-9])', content, re.I)}
        if references and (len(references) > 1 or code.upper() not in references):
            return None, 'ambiguous_reference'
        return order, None if order else 'unknown_reference'
    tokens = {token.upper() for token in re.findall(
        r'(?<![A-Za-z0-9])(?:BM[A-Fa-f0-9]{20}|5B[A-Fa-f0-9]{11,30})(?![A-Za-z0-9])', content, re.I)}
    if len(tokens) > 1:
        return None, 'ambiguous_reference'
    if len(tokens) == 1:
        order = db.execute('SELECT * FROM payment_orders WHERE reference=? COLLATE NOCASE', (next(iter(tokens)),)).fetchone()
        return order, None if order else 'unknown_reference'
    return None, 'unknown_reference'


def receive_webhook(path, headers, raw_body):
    _verify(headers, raw_body)
    payload = _payload(raw_body)
    identity = payload.get('id')
    if type(identity) is not int or not 0 <= identity <= 2**63 - 1:
        raise APIError('Mã giao dịch không hợp lệ.')
    if identity == 0:
        # Dashboard test sends mock events, never real financial records.
        return {'success': True}, 201
    amount = payload.get('transferAmount')
    if type(amount) is not int or not 0 < amount <= MAX_AMOUNT:
        raise APIError('Số tiền giao dịch không hợp lệ.')
    if 'currency' in payload and payload['currency'] != 'VND':
        raise APIError('Đơn thanh toán chỉ nhận tiền Việt Nam đồng.')
    direction = _text(payload, 'transferType', 3)
    if direction not in ('in', 'out'):
        raise APIError('Loại giao dịch không hợp lệ.')
    bank = _text(payload, 'gateway', 100)
    account = _text(payload, 'accountNumber', 40)
    content = _text(payload, 'content', 2000, True)
    bank_reference = _text(payload, 'referenceCode', 200, True)
    code = payload.get('code')
    if code is not None and (not isinstance(code, str) or len(code) > 80 or any(ord(c) < 32 for c in code)):
        raise APIError('Mã thanh toán không hợp lệ.')
    transaction_at = _transaction_time(payload)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                       separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    try:
        with connect(path, True) as db:
            existing = db.execute("SELECT payload_hash FROM payment_receipts WHERE provider='sepay' AND transaction_id=?", (identity,)).fetchone()
            if existing:
                if not hmac.compare_digest(existing['payload_hash'], digest):
                    raise APIError('Mã giao dịch đã tồn tại với nội dung khác. Cần đối soát.', 409)
                return {'success': True}, 201
            order, reason = _find_order(db, code, content)
            if direction == 'out':
                status, reason = 'ignored', 'outgoing'
            else:
                status = 'review'
                if order is not None:
                    if not order['bank_id'] or not order['bank_account']:
                        reason = 'receiver_unconfigured'
                    elif _bank_key(bank) != _bank_key(order['bank_id']) or account != order['bank_account']:
                        reason = 'wrong_receiver'
                    elif amount != order['amount']:
                        reason = 'amount_mismatch'
                    else:
                        reason = settlement_problem(db, order)
                        if reason is None:
                            status, reason = 'processed', 'settled'
            receipt_id = db.execute('INSERT INTO payment_receipts(provider,transaction_id,payload_hash,order_id,status,reason,'
                'amount,reference,bank,bank_account,bank_reference,transaction_at,received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('sepay', identity, digest, order['id'] if order else None, status, reason,
                 amount, order['reference'] if order else code or '', bank, account, bank_reference,
                 transaction_at, stamp())).lastrowid
            if status == 'processed':
                settle_order(db, order, 'sepay', receipt_id)
        return {'success': True}, 201
    except sqlite3.Error:
        raise APIError('Chưa thể lưu giao dịch thanh toán. Hệ thống sẽ nhận lại thông báo.', 503)


def receipt_list(db, handler):
    query = parse_qs(urlsplit(handler.path).query)
    try:
        page = int(query.get('page', ['1'])[0])
    except ValueError:
        raise APIError('Trang giao dịch không hợp lệ.')
    if not 1 <= page <= 100000:
        raise APIError('Trang giao dịch không hợp lệ.')
    status = query.get('status', ['all'])[0]
    if status not in ('all', 'processed', 'review', 'ignored'):
        raise APIError('Trạng thái giao dịch không hợp lệ.')
    search = query.get('q', [''])[0][:100]
    clause = ('WHERE (instr(lower(r.reference),lower(?))>0 OR instr(lower(r.bank_reference),lower(?))>0 '
              'OR instr(lower(CAST(r.transaction_id AS TEXT)),lower(?))>0)')
    args = [search] * 3
    if status != 'all':
        clause += ' AND r.status=?'
        args.append(status)
    total = db.execute('SELECT count(*) FROM payment_receipts r ' + clause, args).fetchone()[0]
    rows = [dict(row) for row in db.execute('SELECT r.id,r.provider,r.transaction_id,r.order_id,r.status,r.reason,'
        'r.amount,r.reference,r.bank,r.bank_account,r.bank_reference,r.transaction_at,r.received_at '
        'FROM payment_receipts r ' + clause + ' ORDER BY r.id DESC LIMIT 25 OFFSET ?', (*args, (page - 1) * 25))]
    for row in rows:
        row['reasonLabel'] = REASONS.get(row['reason'], 'Cần kiểm tra giao dịch')
    return {'rows': rows, 'total': total, 'page': page, 'pageSize': 25,
            'automationEnabled': automation_enabled()}
