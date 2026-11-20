"""Independent exam purchases and immutable access to paid exam content."""
import hashlib
import json
import secrets
from . import platform_api as api


def content_valid(db, payload):
    from .question_access import valid_payload
    return valid_payload(db,payload,purpose='exam-sale',sale=True)


def sale_terms(db, session, slug):
    from .admin_catalogue import require_open
    require_open(db, 'sales_open')
    product = db.execute('SELECT * FROM exam_products WHERE slug=? AND published=1 AND archived=0', (slug,)).fetchone()
    if not product:
        raise api.APIError('Bộ đề chưa mở bán.', 404)
    grade = api.grade_for_student(db, session['student_id'], session['birth_year'])
    if grade != product['grade']:
        raise api.APIError('Bộ đề không thuộc khối của em.', 403)
    payload = {'ids':json.loads(product['question_version_ids_json']), 'grade':grade,
               'duration_minutes':product['duration_minutes'], 'title':product['title'], 'price':product['price']}
    if not content_valid(db, payload):
        raise api.APIError('Bộ đề chưa đủ nội dung được phát hành; chưa tạo đơn.', 503)
    return product, payload


def content_key(db, payload):
    """Compare the same questions across versions, titles and catalogue entries."""
    ids = payload.get('ids') if isinstance(payload, dict) else None
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100 or
            any(type(identity) is not int or not 1 <= identity < 2**63 for identity in ids)):
        return None
    rows = db.execute('SELECT id,question_id FROM question_versions WHERE id IN (' + ','.join('?' for _ in ids) + ')',
                      ids).fetchall()
    questions = sorted({row['question_id'] for row in rows})
    if len(rows) != len(ids) or len(questions) != len(ids):
        return None
    return hashlib.sha256(api.packed(questions).encode()).hexdigest()


def legacy_duplicate(db, account_id, slug, key, status, *, exclude_id=None):
    orders = db.execute("SELECT id,exam_product_slug,exam_payload_json FROM payment_orders WHERE account_id=? "
                        "AND purchase_type='exam' AND status=? AND family_cart_product_line_id IS NULL ",
                        (account_id, status))
    for order in orders:
        if order['id'] == exclude_id:
            continue
        if order['exam_product_slug'] == slug:
            return True
        try:
            previous = content_key(db, json.loads(order['exam_payload_json']))
        except (ValueError, TypeError):
            continue
        if key and key == previous:
            return True
    return False


def create_order(db, session, body):
    from .family_cart import reject_legacy_exam
    from .payments import bank_configuration, order_view
    if body.get('feeId') is not None or 'plan' in body:
        raise api.APIError('Mỗi đơn chỉ chọn một gói học hoặc một bộ đề.')
    slug = api.text_field(body, 'examProduct', 100, 1)
    product, payload = sale_terms(db, session, slug)
    reject_legacy_exam(db, session['account_id'], slug, payload)
    old = db.execute("SELECT * FROM payment_orders WHERE account_id=? AND fee_id IS NULL AND status='pending'", (session['account_id'],)).fetchone()
    if old and (old['purchase_type'] != 'exam' or old['exam_product_slug'] != slug or
                old['amount'] != product['price'] or old['exam_payload_json'] != api.packed(payload)):
        db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (old['id'],))
        old = None
    if old:
        from .question_access import pin_order
        pin_order(db,old['id'],payload)
        return {'order':order_view(old)}
    bank, account, owner = bank_configuration()
    identity = db.execute("INSERT INTO payment_orders(account_id,reference,amount,created_at,kind,vip_months,vip_unit_price,bank_id,bank_account,bank_name,purchase_type,exam_product_slug,exam_title,exam_payload_json) VALUES (?,?,?,?,'vip',NULL,NULL,?,?,?,'exam',?,?,?)",
        (session['account_id'],'BM'+secrets.token_hex(10).upper(),product['price'],api.stamp(),bank or None,account or None,owner or None,slug,product['title'],api.packed(payload))).lastrowid
    from .question_access import pin_order
    pin_order(db,identity,payload)
    return {'order':order_view(db.execute('SELECT * FROM payment_orders WHERE id=?',(identity,)).fetchone())}


def notify_purchase(db, account_id, title, reference, confirmed):
    db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,created_at) "
               "VALUES (?,'staff_message','Mua bộ đề thành công',?,'5BMath','system',?)",
               (account_id, title + ' · ' + reference, confirmed))


def grant_family_line(db, order, line, item, payload, source, confirmed):
    """Produce a paid content right in the existing exam launch/PDF system."""
    from .question_access import pin_order
    reference = f"GRANT-{order['reference']}-EXAM-{line['id']}"
    identity = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at,status,kind,'
                          'purchase_type,exam_product_slug,exam_title,exam_payload_json,paid_at,confirmed_source,'
                          "family_cart_product_line_id) VALUES(?,?,?,?,'paid','vip','exam',?,?,?,?,?,?)",
                          (line['account_id'], reference, item['amount'], order['created_at'], line['product_ref'],
                           item['title'], api.packed(payload), confirmed, source, line['id'])).lastrowid
    pin_order(db, identity, payload)
    notify_purchase(db, line['account_id'], item['title'], order['reference'], confirmed)


def start_order(db, session, identity):
    order = db.execute("SELECT * FROM payment_orders WHERE id=? AND account_id=? AND purchase_type='exam'", (identity, session['account_id'])).fetchone()
    if not order:
        raise api.APIError('Không tìm thấy đơn mua đề của em.',404)
    if order['status'] != 'paid':
        raise api.APIError('Bộ đề đang chờ xác nhận thanh toán.',403)
    prior = db.execute('SELECT exam_id FROM exam_order_attempts WHERE order_id=?',(identity,)).fetchone()
    if prior:
        return {'exam':api.exam_view(db,api.owned_attempt(db,session,prior[0]))}
    payload = json.loads(order['exam_payload_json'])
    from .premium_content import issue_exam
    result = issue_exam(db,session,payload,'purchase-'+secrets.token_hex(16),'PURCHASE-'+str(identity)+'-'+secrets.token_hex(8),purchase_order_id=identity)
    db.execute('INSERT INTO exam_order_attempts VALUES (?,?)',(identity,int(result['exam']['id'])))
    return result
