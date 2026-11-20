"""Family-owned draft cart and one immutable transfer for multiple beneficiaries."""
import hashlib
import json
import re
import secrets

from . import family_accounts as family
from . import exam_commerce, payments, platform_api as api
from .family_personal import POLICY, referral
from .learning_update import enrolled, membership
from .subscriptions import add_months, product


def _conflict(message, code):
    return family._error(message, 409, code)


def _revision(db, family_id):
    row = db.execute('SELECT revision FROM family_carts WHERE family_id=?', (family_id,)).fetchone()
    return row['revision'] if row else 0


def _check_revision(db, family_id, body):
    revision = body.get('revision')
    if type(revision) is not int or revision < 0:
        raise api.APIError('Phiên bản giỏ hàng không hợp lệ.')
    if revision != _revision(db, family_id):
        raise _conflict('Giỏ hàng vừa thay đổi trên thiết bị khác. Hãy tải lại giỏ.', 'cart_revision_conflict')
    return revision


def _student_id(body):
    identity = body.get('studentId')
    if type(identity) is not int or not 1 <= identity < 2**63:
        raise api.APIError('Hãy chọn đúng hồ sơ con.', 400)
    return identity


def _pending(db, family_id):
    return db.execute("SELECT * FROM family_cart_orders WHERE family_id=? AND status='pending'",
                      (family_id,)).fetchone()


def _draft_items(db, family_id):
    return db.execute('SELECT * FROM family_cart_items WHERE family_id=? ORDER BY student_id', (family_id,)).fetchall()


def _draft_products(db, family_id):
    return db.execute('SELECT * FROM family_cart_product_items WHERE family_id=? ORDER BY student_id,type,product_key',
                      (family_id,)).fetchall()


def _advance(db, family_id):
    db.execute('INSERT INTO family_carts(family_id,revision) VALUES(?,1) '
               'ON CONFLICT(family_id) DO UPDATE SET revision=family_carts.revision+1', (family_id,))
    return _revision(db, family_id)


def _item(identity, kind, product_key, title, unit_amount, quantity=1, child=None):
    return {'type': kind, 'productKey': product_key, 'lineId': f'{identity}:{product_key}',
            'studentId': identity, 'studentName': api.safe_nickname(child['full_name']) if child else 'Hồ sơ không còn khả dụng',
            'grade': family.child_grade(child) if child else None, 'title': title, 'quantity': quantity,
            'unitAmount': unit_amount, 'amount': unit_amount * quantity, 'available': bool(child)}


def _line(db, row, child):
    terms = product(row['plan'], row['period'])
    item = _item(row['student_id'], 'subscription', 'subscription', terms['plan'], terms['amount'], child=child)
    item.update(plan=terms['plan'], period=terms['period'], months=terms['months'], referralCode=row['referral_code'],
                estimatedStartsAt=None, estimatedEndsAt=None, subscriptionAction=None)
    if not child:
        return item
    aid = child['account_id']
    account = db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts WHERE id=?', (aid,)).fetchone()
    current = membership(db, {'account_id': aid})
    starts = payments.subscription_start(account, terms['plan'], terms['period'], api.stamp())
    action = 'renew' if current == terms['plan'] else 'upgrade' if current == 'VIP' and terms['plan'] == 'VIP+' else 'subscribe'
    item.update(estimatedStartsAt=starts, estimatedEndsAt=add_months(starts, terms['months']), subscriptionAction=action)
    return item


def _fee_line(db, child, fee, class_info):
    fee_id = fee['id']
    item = _item(child['student_id'], 'tuition', f'tuition:{fee_id}', 'Học phí tháng ' + fee['month'],
                 fee['amount'], child=child)
    paid_at = payments.fee_paid_at(db, fee)
    availability = 'available'
    if paid_at:
        availability = 'paid'
    elif fee['amount'] <= 0:
        availability = 'no-fee'
    elif _pending_fee(db, fee_id) or reserved_fee(db, fee_id):
        availability = 'pending'
    item.update(feeId=fee_id, classId=fee['class_id'], className=class_info['name'], month=fee['month'],
                paidAt=paid_at, available=availability == 'available', availability=availability,
                rights=['Ghi nhận học phí của lớp và tháng đã chọn.'])
    return item


def _pack_line(child, pack, quantity=1):
    item = _item(child['student_id'], 'credits', 'credits:' + pack['sku'], pack['title'], pack['amount'], quantity, child)
    units = pack['quantity'] * quantity
    name = 'câu hỏi' if pack['unit'] == 'questions' else 'lượt tạo đề theo lựa chọn'
    item.update(sku=pack['sku'], creditKind=pack['unit'], credits=pack['quantity'], totalCredits=units,
                expiresAt=None, scopeLabel=pack['scopeLabel'], eligibleCounts=pack['eligibleCounts'],
                sourceQuestionCount=pack['sourceQuestionCount'],
                rights=[f'Thêm {units} {name} cho hồ sơ con. Lượt mua không hết hạn.'])
    if pack['unit'] == 'exams':
        item['rights'].append('Mỗi đề gồm 10 câu từ kho đang khả dụng, theo điều kiện đã chọn.')
    return item


def _exam_line(db, child, session, slug):
    from .question_access import digest, version
    selected, payload = exam_commerce.sale_terms(db, session, slug)
    key = exam_commerce.content_key(db, payload)
    if not key:
        raise api.APIError('Bộ đề cần được kiểm tra lại nội dung.', 503)
    aid = child['account_id']
    if _purchased_exam(db, aid, slug, key):
        raise _conflict(payments.REASONS['exam_paid'] + '.', 'cart_exam_owned')
    if reserved_exam(db, aid, slug, key) or exam_commerce.legacy_duplicate(db, aid, slug, key, 'pending'):
        raise _conflict('Hồ sơ này đã có bộ đề hoặc cùng nội dung trong đơn đang chờ.', 'cart_exam_pending')
    item = _item(child['student_id'], 'exam', 'exam:' + slug, selected['title'], selected['price'], child=child)
    item.update(examProduct=slug, description=selected['description'], questionCount=len(payload['ids']),
                durationMinutes=payload['duration_minutes'], rights=['Một lượt làm bộ đề đã chọn sau khi thanh toán.'])
    pin = {'contentKey': key, 'payload': payload, 'catalogueRevision': selected['revision'],
           'questionDigests': [digest(version(db, identity)) for identity in payload['ids']]}
    return item, pin


def _product_line(db, row, child, kind, ref, quantity, local_pilot, credit_catalogue=None):
    session = family._mapped(db, row, child)
    if kind == 'credits':
        from .purchased_credits import catalogue
        info = credit_catalogue if credit_catalogue is not None else catalogue(db, session, local_pilot)
        pack = next((record for record in info['products'] if record['sku'] == ref), None)
        if not pack or not pack['eligible']:
            raise _conflict((pack or {}).get('reason') or 'Gói lượt chưa khả dụng cho học sinh này.',
                            'cart_pack_unavailable')
        return _pack_line(child, pack, quantity), {'sku': ref, 'grade': session['grade']}
    if kind == 'tuition':
        fee = db.execute('SELECT * FROM class_fees WHERE id=? AND student_id=?', (int(ref), child['student_id'])).fetchone()
        if not fee:
            raise api.APIError('Không tìm thấy khoản học phí của học sinh này.', 404)
        item = _fee_line(db, child, fee, enrolled(db, session, fee['class_id']))
        if not item['available']:
            if item['availability'] == 'pending':
                raise _conflict('Khoản học phí đã có đơn chờ thanh toán.', 'cart_fee_pending')
            raise _conflict('Khoản này đã được nộp hoặc không phát sinh học phí.', 'cart_fee_unavailable')
        return item, {'revision': fee['cart_quote_revision']}
    return _exam_line(db, child, session, ref)


def _catalogue(db, row, local_pilot):
    from .purchased_credits import catalogue
    credit_packs, tuition, exams, balances = [], [], [], {}
    for child in family._children(db, row):
        identity = child['student_id']
        session = family._mapped(db, row, child)
        info = catalogue(db, session, local_pilot)
        balances[str(identity)] = {key: info[key] for key in ('questionsRemaining', 'examsRemaining', 'expiresAt')}
        credit_packs.extend(_pack_line(child, pack) for pack in info['products'] if pack['eligible'])
        if membership(db, session) == 'SVip':
            fees = db.execute("SELECT f.*,c.name FROM class_fees f JOIN online_classes c ON c.id=f.class_id "
                              'JOIN class_enrollments e ON e.class_id=c.id AND e.student_id=f.student_id '
                              "WHERE f.student_id=? AND c.status='active' AND e.left_at IS NULL "
                              'ORDER BY f.month DESC,f.id', (identity,))
            tuition.extend(_fee_line(db, child, fee, fee) for fee in fees)
        for item in db.execute('SELECT slug FROM exam_products WHERE grade=? AND published=1 AND archived=0 '
                               'ORDER BY price,slug', (session['grade'],)):
            try:
                line, _ = _exam_line(db, child, session, item['slug'])
            except api.APIError:
                continue
            exams.append(line)
    return {'creditPacks': credit_packs, 'tuition': tuition, 'exams': exams, 'balances': balances}


def _state(db, row, local_pilot):
    family_id = row['family_id']
    children = {child['student_id']: child for child in family._children(db, row)}
    items = [_line(db, item, children.get(item['student_id'])) for item in _draft_items(db, family_id)]
    pending = _pending(db, family_id)
    for stored in _draft_products(db, family_id):
        child = children.get(stored['student_id'])
        item = json.loads(stored['item_json'])
        if not child:
            item.update(available=False, unavailableReason='Hồ sơ không còn khả dụng')
        else:
            try:
                item, _ = _product_line(db, row, child, stored['type'], stored['product_ref'], stored['quantity'], local_pilot)
            except api.APIError as error:
                item.update(available=False, unavailableReason=str(error))
        if pending and not item['available'] and _line_in_order(db, pending['id'], stored):
            item.update(inPendingOrder=True)
        items.append(item)
    return {'cart': {'revision': _revision(db, family_id), 'items': items, 'currency': 'VND',
                     'total': sum(item['amount'] for item in items)},
            'pendingOrder': order_view(db, pending) if pending else None}


def _upsert(db, row, body, local_pilot):
    family_id = row['family_id']
    _check_revision(db, family_id, body)
    student_id = _student_id(body)
    child = family._child(db, row, student_id)
    kind = body.get('type', 'subscription')
    if kind != 'subscription':
        return _upsert_product(db, row, child, kind, body, local_pilot)
    selection = {'plan': body.get('plan'), 'period': body.get('period'), 'referralCode': body.get('referralCode', '')}
    checked = payments.checkout_preview(db, family._mapped(db, row, child), selection)['preview']
    values = (checked['plan'], checked['period'], checked['referralCode'])
    stored = db.execute('SELECT plan,period,referral_code FROM family_cart_items WHERE family_id=? AND student_id=?',
                        (family_id, student_id)).fetchone()
    if stored is None or tuple(stored) != values:
        revision = _advance(db, family_id)
        db.execute('INSERT INTO family_cart_items(family_id,student_id,plan,period,referral_code,revision) '
                   'VALUES(?,?,?,?,?,?) ON CONFLICT(family_id,student_id) DO UPDATE SET plan=excluded.plan,'
                   'period=excluded.period,referral_code=excluded.referral_code,revision=excluded.revision',
                   (family_id, student_id, *values, revision))
    return _state(db, row, local_pilot)


def _upsert_product(db, row, child, kind, body, local_pilot):
    from .purchased_credits import PACKS
    quantity = body.get('quantity', 1)
    if type(quantity) is not int or not 1 <= quantity <= 10 or (kind != 'credits' and quantity != 1):
        raise api.APIError('Số lượng sản phẩm không hợp lệ.')
    if kind == 'credits':
        ref = body.get('sku')
        if not isinstance(ref, str) or ref not in PACKS:
            raise api.APIError('Gói lượt không hợp lệ.')
    elif kind == 'tuition':
        fee_id = body.get('feeId')
        if type(fee_id) is not int or not 1 <= fee_id < 2**63:
            raise api.APIError('Khoản học phí không hợp lệ.')
        ref = str(fee_id)
    elif kind == 'exam':
        ref = api.text_field(body, 'examProduct', 100, 1)
    else:
        raise api.APIError('Loại sản phẩm không hợp lệ.')
    item, pin = _product_line(db, row, child, kind, ref, quantity, local_pilot)
    family_id, student_id, product_key = row['family_id'], child['student_id'], item['productKey']
    if kind == 'exam':
        _reject_duplicate_draft_exam(db, family_id, student_id, ref, pin['contentKey'])
    stored = db.execute('SELECT quantity FROM family_cart_product_items WHERE family_id=? AND student_id=? AND product_key=?',
                        (family_id, student_id, product_key)).fetchone()
    if not stored or stored['quantity'] != quantity:
        db.execute('INSERT INTO family_cart_product_items(family_id,student_id,type,product_key,product_ref,quantity,revision,item_json) '
                   'VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(family_id,student_id,product_key) DO UPDATE SET '
                   'quantity=excluded.quantity,revision=excluded.revision,item_json=excluded.item_json',
                   (family_id, student_id, kind, product_key, ref, quantity, _advance(db, family_id), api.packed(item)))
    return _state(db, row, local_pilot)


def _remove(db, row, body, local_pilot):
    family_id = row['family_id']
    _check_revision(db, family_id, body)
    identity = body.get('lineId')
    if identity is None:
        student_id, key = _student_id(body), 'subscription'
    else:
        match = re.fullmatch(r'([1-9][0-9]{0,18}):(.{1,106})', identity) if isinstance(identity, str) else None
        if not match or int(match[1]) >= 2**63:
            raise api.APIError('Dòng giỏ hàng không hợp lệ.')
        student_id, key = int(match[1]), match[2]
    if key == 'subscription':
        removed = db.execute('DELETE FROM family_cart_items WHERE family_id=? AND student_id=?', (family_id, student_id)).rowcount
    else:
        removed = db.execute('DELETE FROM family_cart_product_items WHERE family_id=? AND student_id=? AND product_key=?',
                             (family_id, student_id, key)).rowcount
    if removed:
        _advance(db, family_id)
    return _state(db, row, local_pilot)


def _legacy_pending(db, aid):
    return db.execute("SELECT 1 FROM payment_orders WHERE account_id=? AND family_cart_order_id IS NULL "
                      "AND status='pending' AND kind='vip' AND purchase_type='subscription' AND fee_id IS NULL",
                      (aid,)).fetchone()


def reserved(db, aid):
    return db.execute('SELECT 1 FROM family_cart_order_items i JOIN family_cart_orders o ON o.id=i.order_id '
                      "WHERE i.account_id=? AND o.status='pending'", (aid,)).fetchone()


def reject_legacy_subscription(db, aid):
    if reserved(db, aid):
        raise _conflict('Hồ sơ này đã có gói trong đơn gia đình đang chờ.', 'cart_subscription_pending')


def _pending_fee(db, fee_id):
    return db.execute("SELECT 1 FROM payment_orders WHERE fee_id=? AND status='pending'", (fee_id,)).fetchone()


def reserved_fee(db, fee_id, account_id=None, *, exclude_order_id=None):
    return db.execute('SELECT 1 FROM family_cart_product_order_items i JOIN family_cart_orders o ON o.id=i.order_id '
                      "WHERE i.type='tuition' AND i.fee_id=? AND o.status='pending' AND o.id IS NOT ? "
                      'AND (? IS NULL OR i.account_id=?)', (fee_id, exclude_order_id, account_id, account_id)).fetchone()


def reject_legacy_fee(db, aid, fee_id):
    if reserved_fee(db, fee_id, aid):
        raise _conflict(payments.REASONS['family_fee_pending'] + '.', 'cart_fee_pending')


def _cart_exam(db, aid, slug, key, status, exclude_order_id=None):
    return db.execute('SELECT 1 FROM family_cart_product_order_items i JOIN family_cart_orders o ON o.id=i.order_id '
                      "WHERE i.type='exam' AND i.account_id=? AND o.status=? AND o.id IS NOT ? "
                      'AND (i.product_ref=? OR i.content_key=?)', (aid, status, exclude_order_id, slug, key)).fetchone()


def reserved_exam(db, aid, slug, key, *, exclude_order_id=None):
    return _cart_exam(db, aid, slug, key, 'pending', exclude_order_id)


def _purchased_exam(db, aid, slug, key):
    return _cart_exam(db, aid, slug, key, 'paid') or exam_commerce.legacy_duplicate(db, aid, slug, key, 'paid')


def reject_legacy_exam(db, aid, slug, payload):
    key = exam_commerce.content_key(db, payload)
    if reserved_exam(db, aid, slug, key):
        raise _conflict(payments.REASONS['family_exam_pending'] + '.', 'cart_exam_pending')
    if _cart_exam(db, aid, slug, key, 'paid'):
        raise _conflict(payments.REASONS['exam_paid'] + '.', 'cart_exam_owned')


def _reject_duplicate_draft_exam(db, family_id, student_id, slug, key):
    others = db.execute('SELECT p.question_version_ids_json FROM family_cart_product_items i JOIN exam_products p '
                        'ON p.slug=i.product_ref WHERE i.family_id=? AND i.student_id=? '
                        "AND i.type='exam' AND p.slug<>?", (family_id, student_id, slug))
    for other in others:
        if key == exam_commerce.content_key(db, {'ids': json.loads(other[0])}):
            raise _conflict('Giỏ đã có bộ đề cùng nội dung cho học sinh này.', 'cart_exam_duplicate')


def _line_in_order(db, order_id, draft):
    return db.execute('SELECT 1 FROM family_cart_product_order_items WHERE order_id=? AND student_id=? '
                      'AND product_key=? AND cart_item_revision=?',
                      (order_id, draft['student_id'], draft['product_key'], draft['revision'])).fetchone()


def _preview(db, row, body, local_pilot):
    family_id = row['family_id']
    revision = _check_revision(db, family_id, body)
    lines = _draft_items(db, family_id)
    products = _draft_products(db, family_id)
    if not lines and not products:
        raise api.APIError('Hãy chọn ít nhất một sản phẩm trong giỏ.')
    entries, signatures = [], []
    for line in lines:
        child = family._child(db, row, line['student_id'])
        session = family._mapped(db, row, child)
        if _legacy_pending(db, child['account_id']):
            raise _conflict(f"{api.safe_nickname(child['full_name'])} còn đơn gói học riêng đang chờ.",
                            'cart_subscription_pending')
        choice = {'plan': line['plan'], 'period': line['period'], 'referralCode': line['referral_code']}
        checked = payments.checkout_preview(db, session, choice)['preview']
        pin = referral(db, session, choice)
        item = _line(db, line, child)
        item.update(rights=checked['rights'], referralEligible=checked['referralEligible'],
                    referralApplied=bool(pin['referrer']))
        entries.append((line, child, item, pin['referrer']))
        # Draft estimate advances with the clock. Hash the quote's actual terms
        # and the pre-existing entitlement anchors, excluding clock estimates.
        signature = {key: value for key, value in item.items() if key not in ('estimatedStartsAt', 'estimatedEndsAt')}
        dates = db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts WHERE id=?',
                           (child['account_id'],)).fetchone()
        signatures.append(dict(signature, childAccountId=child['account_id'], itemRevision=line['revision'],
                               referrerStudentId=pin['referrer'], previousExpiry=dict(dates),
                               monthlyPrice=product(line['plan'], line['period'])['monthlyPrice']))
    items = [entry[2] for entry in entries]
    product_entries, exam_keys = [], set()
    for line in products:
        child = family._child(db, row, line['student_id'])
        item, pin = _product_line(db, row, child, line['type'], line['product_ref'], line['quantity'], local_pilot)
        if line['type'] == 'exam':
            exam_key = (child['student_id'], pin['contentKey'])
            if exam_key in exam_keys:
                raise _conflict('Giỏ đã có bộ đề cùng nội dung cho học sinh này.', 'cart_exam_duplicate')
            exam_keys.add(exam_key)
        items.append(item)
        product_entries.append((line, child, item, pin))
        signatures.append(dict(item, childAccountId=child['account_id'], itemRevision=line['revision'], pin=pin))
    total = sum(item['amount'] for item in items)
    if not 0 < total <= payments.MAX_AMOUNT:
        raise api.APIError('Tổng thanh toán của giỏ vượt giới hạn cho một đơn.')
    preview = {'revision': revision, 'items': items, 'total': total, 'currency': 'VND',
               'policyVersion': payments.CHECKOUT_POLICY_VERSION,
               'fulfillment': 'Xác nhận một khoản thanh toán rồi ghi nhận đầy đủ từng sản phẩm cho từng con.'}
    canonical = json.dumps({**preview, 'items': signatures, 'familyId': family_id}, ensure_ascii=False,
                           sort_keys=True, separators=(',', ':'))
    return {'preview': preview, 'quoteHash': hashlib.sha256(canonical.encode()).hexdigest()}, entries, product_entries


def _purchaser(body, checked):
    purchaser = payments._checkout_consent(body, checked)
    if purchaser['relationship'] not in ('parent', 'representative'):
        raise api.APIError('Hãy chọn vai trò phụ huynh hoặc người đại diện.')
    return purchaser


def _repeat_order(db, family_id, body):
    evidence = body.get('checkout')
    revision = body.get('revision')
    if (not isinstance(evidence, dict) or type(revision) is not int or not 1 <= revision < 2**63 or
            not isinstance(evidence.get('quoteHash'), str) or len(evidence['quoteHash']) != 64):
        return None
    order = db.execute("SELECT * FROM family_cart_orders WHERE family_id=? AND cart_revision=? AND quote_hash=? "
                       "AND status IN ('pending','paid') ORDER BY id DESC LIMIT 1",
                       (family_id, revision, evidence['quoteHash'])).fetchone()
    if order and _purchaser(body, {'quoteHash': order['quote_hash']}) == json.loads(order['purchaser_json']):
        return order
    return None


def _checkout(db, row, body, local_pilot):
    family_id = row['family_id']
    repeat = _repeat_order(db, family_id, body)
    if repeat:
        return order_view(db, repeat)
    if _pending(db, family_id):
        raise _conflict('Gia đình còn một đơn đang chờ thanh toán hoặc đối soát.', 'cart_pending_order')
    checked, entries, product_entries = _preview(db, row, body, local_pilot)
    purchaser = _purchaser(body, checked)
    preview = checked['preview']
    created = api.stamp()
    bank, account, owner = payments.bank_configuration()
    reference = '5BC' + secrets.token_hex(10).upper()
    snapshot = {**preview, 'quoteHash': checked['quoteHash'], 'purchaser': purchaser,
                'acceptedPolicyVersion': payments.CHECKOUT_POLICY_VERSION, 'acceptedAt': created}
    order_id = db.execute('INSERT INTO family_cart_orders(family_id,reference,amount,created_at,bank_id,bank_account,'
                          'bank_name,quote_hash,cart_revision,purchaser_json,checkout_snapshot_json) '
                          'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                          (family_id, reference, preview['total'], created, bank or None, account or None, owner or None,
                           checked['quoteHash'], preview['revision'], api.packed(purchaser), api.packed(snapshot))).lastrowid
    db.executemany('INSERT INTO family_cart_order_items(order_id,student_id,account_id,cart_item_revision,item_json,referrer_student_id) '
                   'VALUES(?,?,?,?,?,?)',
                   [(order_id, child['student_id'], child['account_id'], line['revision'],
                     api.packed({**item, 'monthlyPrice': product(line['plan'], line['period'])['monthlyPrice']}), referrer)
                    for line, child, item, referrer in entries])
    db.executemany('INSERT INTO family_cart_product_order_items(order_id,student_id,account_id,type,product_key,product_ref,'
                   'fee_id,content_key,quantity,cart_item_revision,item_json,pin_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   [(order_id, child['student_id'], child['account_id'], line['type'], line['product_key'], line['product_ref'],
                     item.get('feeId'), pin.get('contentKey'), line['quantity'], line['revision'], api.packed(item), api.packed(pin))
                    for line, child, item, pin in product_entries])
    return order_view(db, _pending(db, family_id))


def _order_lines(db, order_id):
    return db.execute('SELECT i.*,p.subscription_starts_at,p.subscription_ends_at FROM family_cart_order_items i '
                      'LEFT JOIN payment_orders p ON p.id=i.grant_order_id WHERE i.order_id=? ORDER BY i.student_id',
                      (order_id,)).fetchall()


def _product_order_lines(db, order_id):
    return db.execute('SELECT i.*,p.id purchase_order_id FROM family_cart_product_order_items i '
                      'LEFT JOIN payment_orders p ON p.family_cart_product_line_id=i.id WHERE i.order_id=? '
                      'ORDER BY i.student_id,i.type,i.product_key', (order_id,)).fetchall()


def _money_observed(db, order_id):
    return db.execute("SELECT amount,reason FROM payment_receipts WHERE family_cart_order_id=? AND status='review' "
                      "AND reason NOT IN ('receiver_unconfigured','wrong_receiver') ORDER BY id DESC LIMIT 1",
                      (order_id,)).fetchone()


def order_view(db, order):
    receipt = _money_observed(db, order['id'])
    status = 'review' if order['status'] != 'paid' and receipt else order['status']
    fulfillment = {'paid': 'granted', 'cancelled': 'cancelled'}.get(order['status'], status)
    products = _product_order_lines(db, order['id'])
    blocked = settlement_problem(db, order) if products and status == 'pending' else None
    base = payments.order_view({**dict(order), 'status': 'review' if blocked else status})
    items = []
    for line in _order_lines(db, order['id']):
        stored = json.loads(line['item_json'])
        item = _item(line['student_id'], 'subscription', 'subscription', stored['plan'], stored['amount'])
        item.update(stored, subscriptionStartsAt=line['subscription_starts_at'],
                    subscriptionEndsAt=line['subscription_ends_at'], fulfillmentStatus=fulfillment)
        item.pop('monthlyPrice', None)
        items.append(item)
    for line in products:
        item = dict(json.loads(line['item_json']), fulfillmentStatus=fulfillment)
        if order['status'] == 'paid':
            item['fulfilledAt'] = line['applied_at']
            if line['type'] == 'tuition':
                item['paidAt'] = line['applied_at']
            if line['purchase_order_id'] is not None:
                item['purchaseOrderId'] = line['purchase_order_id']
        items.append(item)
    visible = ('id', 'reference', 'amount', 'created_at', 'paid_at', 'bank', 'bankAccount', 'bankName',
               'qrUrl', 'automationEnabled', 'checkoutSnapshot')
    return {**{key: base[key] for key in visible}, 'status': status, 'currency': 'VND', 'items': items,
            'fulfillmentStatus': fulfillment, 'checkoutBlocked': bool(blocked),
            'paymentReceived': bool(receipt or status == 'paid'),
            'receivedAmount': order['amount'] if status == 'paid' else receipt['amount'] if receipt else None,
            'reviewReason': payments.REASONS.get(receipt['reason'] if receipt else blocked),
            'reviewReasonCode': receipt['reason'] if receipt else blocked}


def _product_problem(db, order, line):
    item, pin = json.loads(line['item_json']), json.loads(line['pin_json'])
    quantity = line['quantity']
    if (line['applied_at'] is not None or line['purchase_order_id'] is not None or
            item['quantity'] != quantity or item['amount'] != item['unitAmount'] * quantity):
        return 'purchase_conflict'
    if line['type'] == 'tuition':
        fee = db.execute('SELECT * FROM class_fees WHERE id=?', (line['fee_id'],)).fetchone()
        if not fee or fee['student_id'] != line['student_id']:
            return 'fee_mismatch'
        if payments.fee_paid_at(db, fee):
            return 'fee_paid'
        if (fee['class_id'] != item['classId'] or fee['month'] != item['month'] or
                fee['amount'] != item['amount'] or fee['cart_quote_revision'] != pin['revision']):
            return 'fee_mismatch'
        if _pending_fee(db, fee['id']) or reserved_fee(db, fee['id'], exclude_order_id=order['id']):
            return 'purchase_conflict'
    elif line['type'] == 'exam':
        from .question_access import digest, version
        payload, key, aid, slug = pin['payload'], line['content_key'], line['account_id'], line['product_ref']
        if payload['price'] != item['amount'] or not exam_commerce.content_valid(db, payload):
            return 'exam_content_changed'
        if pin['questionDigests'] != [digest(version(db, identity)) for identity in payload['ids']]:
            return 'exam_content_changed'
        if _purchased_exam(db, aid, slug, key):
            return 'exam_paid'
        if (reserved_exam(db, aid, slug, key, exclude_order_id=order['id']) or
                exam_commerce.legacy_duplicate(db, aid, slug, key, 'pending')):
            return 'purchase_conflict'
    return None


def settlement_problem(db, order):
    if order['status'] != 'pending':
        return 'order_paid' if order['status'] == 'paid' else 'order_cancelled'
    owner = db.execute('SELECT status FROM family_accounts WHERE id=?', (order['family_id'],)).fetchone()
    if not owner or owner['status'] != 'active':
        return 'family_unavailable'
    subscriptions = _order_lines(db, order['id'])
    lines = [*subscriptions, *_product_order_lines(db, order['id'])]
    if not lines or sum(json.loads(line['item_json'])['amount'] for line in lines) != order['amount']:
        return 'invalid_product'
    for line in lines:
        child = db.execute("SELECT s.account_id,s.status,a.status account_status,a.deleted_at FROM family_children c "
                           "JOIN students s ON s.id=c.student_id JOIN accounts a ON a.id=s.account_id "
                           "WHERE c.family_id=? AND c.student_id=?", (order['family_id'], line['student_id'])).fetchone()
        if not child or child['account_id'] != line['account_id'] or child['status'] != 'active':
            return 'student_mismatch'
        if child['account_status'] != 'active' or child['deleted_at'] is not None:
            return 'account_unavailable'
        if 'type' in line.keys():
            problem = _product_problem(db, order, line)
            if problem:
                return problem
            continue
        if _legacy_pending(db, line['account_id']) or line['grant_order_id'] is not None:
            return 'purchase_conflict'
        current = membership(db, {'account_id': line['account_id']})
        if current == 'SVip':
            return 'internal_account'
        if current == 'VIP+' and json.loads(line['item_json'])['plan'] == 'VIP':
            return 'membership_changed'
    return None


def settle_order(db, order, source, receipt_id=None):
    """Every line and the parent transfer share the caller's write transaction."""
    if order['status'] == 'paid':
        return False
    problem = settlement_problem(db, order)
    if problem:
        raise api.APIError(payments.REASONS[problem] + '. Kiểm tra lại trước khi xác nhận.', 409)
    order_id = order['id']
    confirmed = api.stamp()
    removed = 0
    for line in _order_lines(db, order_id):
        item = json.loads(line['item_json'])
        grant_id = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at,kind,vip_months,'
                              'vip_unit_price,subscription_plan,subscription_period,family_cart_order_id) '
                              "VALUES(?,?,?,?,'vip',?,?,?,?,?)",
                              (line['account_id'], f"GRANT-{order['reference']}-{line['student_id']}", item['amount'],
                               order['created_at'], item['months'], item['monthlyPrice'], item['plan'], item['period'],
                               order_id)).lastrowid
        db.execute('INSERT INTO child_referral_order_pins VALUES(?,?,?,?,?)',
                   (grant_id, POLICY, line['student_id'], line['referrer_student_id'], item['referralCode']))
        grant = db.execute('SELECT * FROM payment_orders WHERE id=?', (grant_id,)).fetchone()
        payments.settle_order(db, grant, source)
        db.execute('UPDATE family_cart_order_items SET grant_order_id=? WHERE order_id=? AND student_id=?',
                   (grant_id, order_id, line['student_id']))
        removed += db.execute('DELETE FROM family_cart_items WHERE family_id=? AND student_id=? AND revision=?',
                              (order['family_id'], line['student_id'], line['cart_item_revision'])).rowcount
    for line in _product_order_lines(db, order_id):
        item = json.loads(line['item_json'])
        if line['type'] == 'credits':
            from .purchased_credits import grant
            grant(db, line['account_id'], line['student_id'], line['product_ref'], line['id'])
        elif line['type'] == 'tuition':
            payments.settle_fee(db, line['fee_id'], line['account_id'], item['month'], order['reference'], confirmed)
        else:
            exam_commerce.grant_family_line(db, order, line, item, json.loads(line['pin_json'])['payload'], source, confirmed)
        db.execute('UPDATE family_cart_product_order_items SET applied_at=? WHERE id=?', (confirmed, line['id']))
        removed += db.execute('DELETE FROM family_cart_product_items WHERE family_id=? AND student_id=? '
                              'AND product_key=? AND revision=?', (order['family_id'], line['student_id'],
                               line['product_key'], line['cart_item_revision'])).rowcount
    if removed:
        _advance(db, order['family_id'])
    db.execute("UPDATE family_cart_orders SET status='paid',paid_at=?,confirmed_source=?,receipt_id=? WHERE id=?",
               (api.stamp(), source, receipt_id, order_id))
    return True


def _find(db, family_id, identity):
    order = db.execute('SELECT * FROM family_cart_orders WHERE family_id=? AND id=?', (family_id, identity)).fetchone()
    if not order:
        raise api.APIError('Không tìm thấy đơn thanh toán của gia đình.', 404)
    return order


def request(db, row, method, action, body, *, local_pilot=None):
    family_id = row['family_id']
    if (method, action) == ('GET', 'cart'):
        return _state(db, row, local_pilot)
    if (method, action) == ('GET', 'cart/catalog'):
        return _catalogue(db, row, local_pilot)
    if (method, action) == ('POST', 'cart/items/upsert'):
        return _upsert(db, row, body, local_pilot)
    if (method, action) == ('POST', 'cart/items/remove'):
        return _remove(db, row, body, local_pilot)
    if (method, action) == ('POST', 'cart/preview'):
        return _preview(db, row, body, local_pilot)[0]
    if (method, action) == ('POST', 'cart/checkout'):
        return {'order': _checkout(db, row, body, local_pilot)}
    if (method, action) == ('GET', 'cart/orders'):
        orders = db.execute('SELECT * FROM family_cart_orders WHERE family_id=? ORDER BY id DESC LIMIT 20', (family_id,))
        return {'orders': [order_view(db, order) for order in orders]}
    match = re.fullmatch(r'cart/orders/([1-9][0-9]{0,18})(/cancel)?', action)
    if match and int(match[1]) < 2**63:
        identity = int(match[1])
        if method == 'GET' and not match[2]:
            return {'order': order_view(db, _find(db, family_id, identity))}
        if method == 'POST' and match[2]:
            order = _find(db, family_id, identity)
            if order['status'] == 'paid' or _money_observed(db, identity):
                raise _conflict('Đơn đã có giao dịch. Hãy đối soát với 5BMath trước khi đổi đơn.', 'cart_payment_received')
            if order['status'] == 'pending':
                db.execute("UPDATE family_cart_orders SET status='cancelled',cancelled_at=? WHERE id=?",
                           (api.stamp(), identity))
            return {'order': order_view(db, _find(db, family_id, identity))}
    raise api.APIError('API giỏ hàng không tồn tại.', 404)
