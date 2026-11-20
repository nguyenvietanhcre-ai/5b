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
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

from .platform_api import APIError, VN, connect, now, stamp

VIP_UNIT_PRICE = 100000
MAX_AMOUNT = 10**12
CHECKOUT_POLICY_VERSION = '2026-11-17-draft1'
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
    'invalid_product': 'Thông tin sản phẩm không hợp lệ',
    'internal_account': 'Tài khoản đã có quyền SVip; cần đối soát',
    'purchase_conflict': 'Mã mua VIP đã được ghi nhận khác thông tin đơn',
    'family_unavailable': 'Tài khoản gia đình đang đóng hoặc không còn hiệu lực',
    'membership_changed': 'Gói hiện hành của học sinh đã thay đổi',
    'family_subscription_pending': 'Hồ sơ học sinh đã có gói trong đơn gia đình đang chờ',
    'family_fee_pending': 'Khoản học phí đã nằm trong đơn gia đình đang chờ',
    'family_exam_pending': 'Bộ đề đã nằm trong đơn gia đình đang chờ',
    'exam_paid': 'Học sinh đã mua bộ đề này hoặc cùng nội dung',
    'exam_content_changed': 'Phiên bản câu hỏi của bộ đề đã thay đổi',
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
    result.pop('exam_payload_json', None)
    for column, key in (('checkout_snapshot_json', 'checkoutSnapshot'), ('purchaser_json', 'purchaser')):
        value = result.pop(column, None)
        result[key] = json.loads(value) if value else None
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
    row = db.execute('SELECT * FROM payment_orders WHERE id=? AND account_id=? AND family_cart_order_id IS NULL '
                     'AND family_cart_product_line_id IS NULL',
                     (identity, session['account_id'])).fetchone()
    if not row:
        raise APIError('Không tìm thấy đơn thanh toán của tài khoản này.', 404)
    return {'order': order_view(row)}


def fee_paid_at(db, fee):
    if fee['paid_at']:
        return fee['paid_at']
    order = db.execute("SELECT coalesce(paid_at,created_at) FROM payment_orders WHERE fee_id=? AND status='paid' "
                       'ORDER BY id LIMIT 1', (fee['id'],)).fetchone()
    return order[0] if order else None


def checkout_preview(db, session, body):
    """Read server prices and eligibility without creating or cancelling any order."""
    from .learning_update import enrolled, membership
    from .subscriptions import product
    fee_id = body.get('feeId')
    if body.get('examProduct') is not None:
        from .exam_commerce import sale_terms
        from .family_cart import reject_legacy_exam
        from .platform_api import text_field
        if fee_id is not None or 'plan' in body:
            raise APIError('Mỗi đơn chỉ chọn một gói học hoặc một bộ đề.')
        slug = text_field(body, 'examProduct', 100, 1)
        item, payload = sale_terms(db, session, slug)
        reject_legacy_exam(db, session['account_id'], slug, payload)
        summary = {'type': 'exam', 'examProduct': slug, 'title': item['title'], 'amount': item['price'],
                   'period': 'one-off', 'rights': ['Một lượt làm bộ đề đã chọn sau khi xác nhận thanh toán.'],
                   'contentFingerprint': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}
    elif fee_id is not None:
        if type(fee_id) is not int or not 1 <= fee_id < 2**63:
            raise APIError('Khoản học phí không hợp lệ.')
        fee = db.execute('SELECT * FROM class_fees WHERE id=? AND student_id=?', (fee_id, session['student_id'])).fetchone()
        if not fee:
            raise APIError('Học phí không thuộc tài khoản của em.', 404)
        enrolled(db, session, fee['class_id'])
        if fee_paid_at(db, fee) or fee['amount'] <= 0:
            raise APIError('Tháng này đã nộp hoặc không có học phí.')
        summary = {'type': 'tuition', 'feeId': fee_id, 'title': 'Học phí tháng ' + fee['month'],
                   'amount': fee['amount'], 'period': fee['month'], 'classId': fee['class_id'],
                   'rights': ['Ghi nhận học phí của lớp và tháng đã chọn; không tạo thêm quyền gói.']}
    else:
        plan = body.get('plan', 'VIP')
        selected = product(plan, body.get('period', 'month'))
        if membership(db, session) == 'SVip':
            raise APIError('Học sinh nội bộ đã có đầy đủ quyền học.', 403)
        if membership(db, session) == 'VIP+' and plan == 'VIP':
            raise APIError('Em đang dùng VIP+. Chọn gia hạn VIP+ để giữ quyền học nâng cao.', 409)
        rights = ['Xem trọn series video đã phát hành.', 'Quyền học được cấp sau khi xác nhận thanh toán.']
        if plan == 'VIP+':
            rights.append('Truy cập nội dung nâng cao đã phát hành; bộ đề bán riêng không nằm trong giá gói.')
        if selected['period'] == 'year':
            rights.append('30 câu mới/ngày; 3.600 câu cho toàn chu kỳ 12 tháng, không đặt lại mỗi tháng.')
        else:
            rights.append('30 câu mới/ngày; 300 câu cho chu kỳ 30 ngày theo hạn mức hiện hành.')
        summary = {'type': 'subscription', 'title': plan, 'plan': plan, 'period': selected['period'],
                   'months': selected['months'], 'amount': selected['amount'], 'rights': rights}
    summary.update(currency='VND', total=summary['amount'], accountId=session['account_id'],
                   studentId=session['student_id'], policyVersion=CHECKOUT_POLICY_VERSION,
                   fulfillment='Sau khi xác nhận khoản thanh toán; không tự động gia hạn hoặc trừ tiền.')
    if summary['type']=='subscription':
        from .family_personal import referral
        summary.update({k:v for k,v in referral(db,session,body).items() if k!='referrer'})
    canonical = json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return {'preview': summary, 'quoteHash': hashlib.sha256(canonical.encode()).hexdigest()}


def _checkout_consent(body, preview):
    checkout = body.get('checkout')
    if not isinstance(checkout, dict) or checkout.get('accepted') is not True:
        raise APIError('Hãy chủ động đồng ý chính sách trước khi tạo đơn.')
    if checkout.get('policyVersion') != CHECKOUT_POLICY_VERSION:
        raise APIError('Chính sách đã thay đổi. Hãy xem lại và đồng ý phiên bản hiện tại.', 409)
    if checkout.get('quoteHash') != preview['quoteHash']:
        raise APIError('Thông tin đơn đã thay đổi. Hãy xem lại gói, kỳ và số tiền.', 409)
    purchaser = checkout.get('purchaser')
    if not isinstance(purchaser, dict):
        raise APIError('Hãy nhập thông tin người mua.')
    clean = {}
    for key, maximum in (('name', 120), ('contact', 200)):
        value = purchaser.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
            raise APIError('Tên và email hoặc số điện thoại liên hệ người mua là bắt buộc.')
        clean[key] = value.strip()
    if not (re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', clean['contact']) or
            re.fullmatch(r'\+?[0-9][0-9 .()-]{6,24}', clean['contact'])):
        raise APIError('Hãy nhập email hoặc số điện thoại liên hệ hợp lệ.')
    if purchaser.get('relationship') not in ('self', 'parent', 'representative'):
        raise APIError('Hãy chọn vai trò của người mua.')
    clean['relationship'] = purchaser['relationship']
    if clean['relationship'] != 'self' and purchaser.get('representativeDeclared') is not True:
        raise APIError('Người mua thay trẻ cần tự khai là phụ huynh hoặc người đại diện.')
    clean['representativeDeclared'] = clean['relationship'] != 'self'
    clean['verification'] = 'self-declared'
    return clean


def create_order(db, session, body, *, require_checkout=False):
    """Internal callers remain compatible; customer routes require explicit consent."""
    from .family_cart import reject_legacy_fee, reject_legacy_subscription
    if body.get('examProduct') is None and type(body.get('feeId')) is int and 1 <= body['feeId'] < 2**63:
        reject_legacy_fee(db, session['account_id'], body['feeId'])
    elif body.get('examProduct') is None and body.get('feeId') is None:
        reject_legacy_subscription(db, session['account_id'])
    checked = None
    if require_checkout or 'checkout' in body:
        checked = checkout_preview(db, session, body)
        purchaser = _checkout_consent(body, checked)
        # A legacy pending QR remains an honest legacy record. A new consented
        # checkout must not silently attach new evidence to that older order.
        db.execute("UPDATE payment_orders SET status='cancelled' WHERE account_id=? AND status='pending' "
                   "AND checkout_snapshot_json IS NULL AND coalesce(fee_id,0)=?",
                   (session['account_id'], body.get('feeId') or 0))
        prior = db.execute("SELECT id,purchaser_json,checkout_snapshot_json FROM payment_orders WHERE account_id=? AND status='pending' AND coalesce(fee_id,0)=?",
                           (session['account_id'], body.get('feeId') or 0)).fetchone()
        if prior and prior['checkout_snapshot_json']:
            evidence = json.loads(prior['checkout_snapshot_json'])
            if (json.loads(prior['purchaser_json']) != purchaser or
                    evidence.get('quoteHash') != checked['quoteHash']):
                db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (prior['id'],))
    from .family_personal import pin_order
    result = pin_order(db, session, body, _create_order)
    if checked and result['order'].get('checkoutSnapshot') is None:
        accepted = stamp()
        snapshot = {**checked['preview'], 'quoteHash': checked['quoteHash'], 'purchaser': purchaser,
                    'acceptedPolicyVersion': CHECKOUT_POLICY_VERSION, 'acceptedAt': accepted}
        db.execute('UPDATE payment_orders SET accepted_policy_version=?,accepted_policy_at=?,purchaser_json=?,checkout_snapshot_json=? WHERE id=? AND checkout_snapshot_json IS NULL',
                   (CHECKOUT_POLICY_VERSION, accepted, json.dumps(purchaser, ensure_ascii=False),
                    json.dumps(snapshot, ensure_ascii=False), result['order']['id']))
        return order_status(db, session, result['order']['id'])
    return result


def order_history(db, session, query=None):
    """Descending, bounded owner-only history; includes honest legacy null evidence."""
    query = query or {}
    cursor = query.get('before', [''])
    cursor = cursor[0] if isinstance(cursor, list) and len(cursor) == 1 else None
    if cursor is None or not isinstance(cursor, str) or cursor and not re.fullmatch(r'[1-9][0-9]{0,18}', cursor):
        raise APIError('Mốc lịch sử đơn không hợp lệ.')
    before = int(cursor) if cursor else 2**63 - 1
    if before > 2**63 - 1:
        raise APIError('Mốc lịch sử đơn không hợp lệ.')
    rows = db.execute('SELECT * FROM payment_orders WHERE account_id=? AND family_cart_order_id IS NULL '
                      'AND family_cart_product_line_id IS NULL '
                      'AND id<? ORDER BY id DESC LIMIT 21',
                      (session['account_id'], before)).fetchall()
    return {'orders': [order_view(row) for row in rows[:20]],
            'nextBefore': rows[19]['id'] if len(rows) > 20 else None}


def _create_order(db, session, body):
    from .learning_update import enrolled, membership
    if body.get('examProduct') is not None:
        from .exam_commerce import create_order as create_exam_order
        return create_exam_order(db, session, body)
    plan = body.get('plan', 'VIP')
    if not isinstance(plan,str) or plan not in ('VIP', 'VIP+'):
        raise APIError('Gói đăng ký không hợp lệ.')
    from .subscriptions import product
    selection=product(plan,body.get('period','month'))
    fee_id = body.get('feeId')
    if fee_id is not None and (type(fee_id) is not int or not 1 <= fee_id < 2**63):
        raise APIError('Khoản học phí không hợp lệ.')
    fee = None
    if fee_id is not None:
        fee = db.execute('SELECT * FROM class_fees WHERE id=? AND student_id=?',
                         (fee_id, session['student_id'])).fetchone()
        if not fee:
            raise APIError('Học phí không thuộc tài khoản của em.', 404)
        enrolled(db, session, fee['class_id'])
        if fee_paid_at(db, fee) or fee['amount'] == 0:
            raise APIError('Tháng này đã nộp hoặc không có học phí.')
        amount = fee['amount']
    else:
        if membership(db, session) == 'SVip':
            raise APIError('Học sinh nội bộ đã có đầy đủ quyền học.', 403)
        if membership(db, session) == 'VIP+' and plan == 'VIP':
            raise APIError('Em đang dùng VIP+. Chọn gia hạn VIP+ để giữ quyền học nâng cao.', 409)
        amount = selection['amount']
    order = db.execute("SELECT * FROM payment_orders WHERE account_id=? AND coalesce(fee_id,0)=? AND status='pending'",
                       (session['account_id'], fee_id or 0)).fetchone()
    if order and (order['amount'] != amount or (not fee and (order['subscription_plan'] != plan or order['subscription_period'] != selection['period']) or order['purchase_type'] == 'exam')):
        # A QR already shown must never silently become a different purchase.
        db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (order['id'],))
        order = None
    bank, account, owner = bank_configuration()
    if order is None:
        identity = db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at,kind,'
            'vip_months,vip_unit_price,fee_student_id,fee_class_id,fee_month,bank_id,bank_account,bank_name,subscription_plan,subscription_period) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (session['account_id'], fee_id, 'BM' + secrets.token_hex(10).upper(), amount, stamp(),
             'tuition' if fee else 'vip', None if fee else selection['months'], None if fee else selection['monthlyPrice'],
             fee['student_id'] if fee else None, fee['class_id'] if fee else None, fee['month'] if fee else None,
             bank or None, account or None, owner or None, plan if not fee else 'VIP',selection['period'] if not fee else 'month')).lastrowid
    else:
        identity = order['id']
        # Legacy orders have no invented receiver. Bind only when the owner asks
        # for their payment instructions and a complete bank config is present.
        if bank and not order['bank_id'] and not order['bank_account'] and not order['bank_name']:
            db.execute('UPDATE payment_orders SET bank_id=?,bank_account=?,bank_name=? WHERE id=?',
                       (bank, account, owner, identity))
    if fee:
        db.execute("UPDATE payment_orders SET purchase_type='tuition' WHERE id=?", (identity,))
    return {'order': order_view(db.execute('SELECT * FROM payment_orders WHERE id=?', (identity,)).fetchone())}


def settlement_problem(db, order):
    if 'family_id' in order.keys():
        from .family_cart import settlement_problem as cart_problem
        return cart_problem(db, order)
    if order['status'] != 'pending':
        return 'order_paid' if order['status'] == 'paid' else 'order_cancelled'
    account = db.execute('SELECT id,status,deleted_at FROM accounts WHERE id=?', (order['account_id'],)).fetchone()
    if not account or account['status'] != 'active' or account['deleted_at'] is not None:
        return 'account_unavailable'
    student = db.execute('SELECT id,status FROM students WHERE account_id=?', (order['account_id'],)).fetchone()
    if not student or student['status'] != 'active':
        return 'student_mismatch'
    if order['purchase_type'] == 'exam':
        from .exam_commerce import content_key, content_valid
        from .family_cart import reserved_exam
        try:
            payload=json.loads(order['exam_payload_json'])
            if order['fee_id'] is not None or payload.get('price') != order['amount'] or not content_valid(db,payload):
                return 'invalid_product'
            if reserved_exam(db, order['account_id'], order['exam_product_slug'], content_key(db, payload)):
                return 'family_exam_pending'
        except (ValueError,TypeError,KeyError):
            return 'invalid_product'
        return None
    if order['kind'] == 'tuition' and order['fee_id'] is not None:
        fee = db.execute('SELECT * FROM class_fees WHERE id=?', (order['fee_id'],)).fetchone()
        if (not fee or fee['student_id'] != student['id'] or fee['student_id'] != order['fee_student_id'] or
                fee['class_id'] != order['fee_class_id'] or fee['month'] != order['fee_month'] or
                fee['amount'] != order['amount'] or fee['amount'] <= 0):
            return 'fee_mismatch'
        if fee_paid_at(db, fee):
            return 'fee_paid'
        from .family_cart import reserved_fee
        if reserved_fee(db, fee['id']):
            return 'family_fee_pending'
    elif order['kind'] == 'vip' and order['fee_id'] is None:
        from .subscriptions import product
        family_grant = order['family_cart_order_id'] is not None
        if not family_grant:
            from .family_cart import reserved
            if reserved(db, order['account_id']):
                return 'family_subscription_pending'
        if order['subscription_period']=='year' and not family_grant:
            selected=product(order['subscription_plan'],'year')
            if (order['vip_months']!=12 or order['vip_unit_price']!=selected['monthlyPrice'] or order['amount']!=selected['amount']):
                return 'invalid_product'
        if not family_grant and order['subscription_plan'] == 'VIP+' and order['vip_unit_price'] != 200000:
            return 'invalid_product'
        if (type(order['vip_months']) is not int or not 1 <= order['vip_months'] <= 120 or
                type(order['vip_unit_price']) is not int or order['vip_unit_price'] <= 0 or
                (order['subscription_period']=='month' and order['amount'] != order['vip_unit_price'] * order['vip_months'])):
            return 'invalid_product'
        if db.execute("SELECT 1 FROM access_entitlements WHERE kind='internal' AND account_id=? AND starts_at<=? "
                      'AND (ends_at IS NULL OR ends_at>?)', (order['account_id'], stamp(), stamp())).fetchone():
            return 'internal_account'
        purchase = db.execute('SELECT account_id,months FROM vip_purchases WHERE payment_ref=?',
                              (_purchase_key(order),)).fetchone()
        if purchase and (family_grant or purchase['account_id'] != order['account_id'] or purchase['months'] != order['vip_months']):
            return 'purchase_conflict'
    else:
        return 'invalid_product'
    return None


def subscription_start(account, plan, period, confirmed):
    # Annual budgets follow the VIP purchase trigger. Monthly VIP+ follows its
    # own calendar expiry, as it did for standalone subscriptions.
    column = 'vip_plus_expires_at' if period == 'month' and plan == 'VIP+' else 'vip_expires_at'
    return max(confirmed, account[column] or confirmed)


def _purchase_key(order):
    return order['reference'] if order['family_cart_order_id'] is not None else 'STAFF-ORDER-' + str(order['id'])


def settle_fee(db, fee_id, account_id, month, reference, confirmed):
    if db.execute('UPDATE class_fees SET paid_at=? WHERE id=? AND paid_at IS NULL', (confirmed, fee_id)).rowcount != 1:
        raise APIError(REASONS['fee_paid'], 409)
    db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,created_at) "
               "VALUES (?,'staff_message','Thanh toán học phí thành công',?,'5BMath','system',?)",
               (account_id, 'Học phí tháng ' + month + ' đã hoàn thành. Mã thanh toán: ' + reference + '.', confirmed))


def settle_order(db, order, source, receipt_id=None):
    """Apply the existing VIP trigger or exact fee once; caller owns transaction."""
    if 'family_id' in order.keys():
        from .family_cart import settle_order as settle_cart
        return settle_cart(db, order, source, receipt_id)
    if order['status'] == 'paid':
        return False
    problem = settlement_problem(db, order)
    if problem:
        raise APIError(REASONS[problem] + '. Kiểm tra lại trước khi xác nhận.', 409)
    confirmed = stamp()
    if order['purchase_type'] == 'exam':
        from .exam_commerce import notify_purchase
        notify_purchase(db, order['account_id'], order['exam_title'], order['reference'], confirmed)
    elif order['kind'] == 'tuition':
        settle_fee(db, order['fee_id'], order['account_id'], order['fee_month'], order['reference'], confirmed)
    else:
        # Keep one key for both legacy staff confirmations and bank webhooks.
        from .subscriptions import add_months
        account = db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts WHERE id=?',
                             (order['account_id'],)).fetchone()
        begins = subscription_start(account, order['subscription_plan'], order['subscription_period'], confirmed)
        ends = add_months(begins, order['vip_months'])
        db.execute('INSERT INTO vip_purchases(account_id,payment_ref,months,confirmed_at) VALUES (?,?,?,?) '
                   'ON CONFLICT(payment_ref) DO NOTHING',
                   (order['account_id'], _purchase_key(order), order['vip_months'], confirmed))
        if order['subscription_plan'] == 'VIP+':
            previous = db.execute('SELECT vip_plus_expires_at FROM accounts WHERE id=?', (order['account_id'],)).fetchone()[0]
            anchor = max(confirmed, previous or confirmed)
            # Same calendar-month rule as VIP; never convert existing VIP time.
            from calendar import monthrange
            start = datetime.fromisoformat(anchor).astimezone(VN)
            months = start.year * 12 + start.month - 1 + order['vip_months']
            year, month = divmod(months, 12)
            month += 1
            until = start.replace(year=year, month=month, day=min(start.day, monthrange(year, month)[1]))
            db.execute('UPDATE accounts SET vip_plus_expires_at=?,revision=revision+1 WHERE id=?', (stamp(until), order['account_id']))
        db.execute('UPDATE payment_orders SET subscription_starts_at=?,subscription_ends_at=? WHERE id=?',(begins,ends,order['id']))
    db.execute("UPDATE payment_orders SET status='paid',paid_at=?,confirmed_source=?,receipt_id=? WHERE id=? AND status='pending'",
               (confirmed, source, receipt_id, order['id']))
    if order['kind']=='vip' and order['purchase_type']=='subscription':
        from .family_personal import settle_referral, preserve_after_purchase
        preserve_after_purchase(db,order['account_id'],order['subscription_plan'])
        settle_referral(db,order)
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
    def lookup(reference):
        family = db.execute('SELECT * FROM family_cart_orders WHERE reference=?', (reference,)).fetchone()
        legacy = db.execute('SELECT * FROM payment_orders WHERE reference=? COLLATE NOCASE '
                            'AND family_cart_order_id IS NULL AND family_cart_product_line_id IS NULL',
                            (reference,)).fetchone()
        if family and legacy:
            return None, 'ambiguous_reference'
        return family or legacy, None if family or legacy else 'unknown_reference'

    # A supplied code must match exactly; do not repair or guess a mistyped code.
    if code:
        references = {token.upper() for token in re.findall(
            r'(?<![A-Za-z0-9])(?:BM[A-Fa-f0-9]{20}|5B[A-Fa-f0-9]{11,30})(?![A-Za-z0-9])', content, re.I)}
        if references and (len(references) > 1 or code.upper() not in references):
            return None, 'ambiguous_reference'
        return lookup(code)
    tokens = {token.upper() for token in re.findall(
        r'(?<![A-Za-z0-9])(?:BM[A-Fa-f0-9]{20}|5B[A-Fa-f0-9]{11,30})(?![A-Za-z0-9])', content, re.I)}
    if len(tokens) > 1:
        return None, 'ambiguous_reference'
    if len(tokens) == 1:
        return lookup(next(iter(tokens)))
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
            family_order = order is not None and 'family_id' in order.keys()
            receipt_id = db.execute('INSERT INTO payment_receipts(provider,transaction_id,payload_hash,order_id,family_cart_order_id,status,reason,'
                'amount,reference,bank,bank_account,bank_reference,transaction_at,received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('sepay', identity, digest, order['id'] if order and not family_order else None,
                 order['id'] if family_order else None, status, reason,
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
    rows = [dict(row) for row in db.execute('SELECT r.id,r.provider,r.transaction_id,r.order_id,r.family_cart_order_id,r.status,r.reason,'
        'r.amount,r.reference,r.bank,r.bank_account,r.bank_reference,r.transaction_at,r.received_at '
        'FROM payment_receipts r ' + clause + ' ORDER BY r.id DESC LIMIT 25 OFFSET ?', (*args, (page - 1) * 25))]
    for row in rows:
        row['reasonLabel'] = REASONS.get(row['reason'], 'Cần kiểm tra giao dịch')
    return {'rows': rows, 'total': total, 'page': page, 'pageSize': 25,
            'automationEnabled': automation_enabled()}
