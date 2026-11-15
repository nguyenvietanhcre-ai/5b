"""Independent exam purchases for every membership; existing settlement authenticates money."""
import json
import secrets
from . import platform_api as api


def content_valid(db, payload):
    ids = payload.get('ids')
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 100 or
            any(type(identity) is not int for identity in ids) or len(set(ids)) != len(ids)):
        return False
    return all(db.execute("SELECT 1 FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE v.id=? AND v.status='published' AND q.grade_id=?", (identity, payload['grade'])).fetchone() for identity in ids)


def create_order(db, session, body):
    from .payments import bank_configuration, order_view
    from .admin_catalogue import require_open
    require_open(db,'sales_open')
    if body.get('feeId') is not None or 'plan' in body:
        raise api.APIError('Mỗi đơn chỉ chọn một gói học hoặc một bộ đề.')
    slug = api.text_field(body, 'examProduct', 100, 1)
    product = db.execute('SELECT * FROM exam_products WHERE slug=? AND published=1 AND archived=0', (slug,)).fetchone()
    if not product:
        raise api.APIError('Bộ đề chưa mở bán.', 404)
    grade, _ = api.ensure_grade(db, session['student_id'], session['birth_year'])
    if grade != product['grade']:
        raise api.APIError('Bộ đề không thuộc khối của em.', 403)
    payload = {'ids':json.loads(product['question_version_ids_json']), 'grade':grade,
               'duration_minutes':product['duration_minutes'], 'title':product['title'], 'price':product['price']}
    if not content_valid(db, payload):
        raise api.APIError('Bộ đề chưa đủ nội dung được phát hành; chưa tạo đơn.', 503)
    old = db.execute("SELECT * FROM payment_orders WHERE account_id=? AND fee_id IS NULL AND status='pending'", (session['account_id'],)).fetchone()
    if old and (old['purchase_type'] != 'exam' or old['exam_product_slug'] != slug or
                old['amount'] != product['price'] or old['exam_payload_json'] != api.packed(payload)):
        db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (old['id'],))
        old = None
    if old:
        return {'order':order_view(old)}
    bank, account, owner = bank_configuration()
    identity = db.execute("INSERT INTO payment_orders(account_id,reference,amount,created_at,kind,vip_months,vip_unit_price,bank_id,bank_account,bank_name,purchase_type,exam_product_slug,exam_title,exam_payload_json) VALUES (?,?,?,?,'vip',NULL,NULL,?,?,?,'exam',?,?,?)",
        (session['account_id'],'BM'+secrets.token_hex(10).upper(),product['price'],api.stamp(),bank or None,account or None,owner or None,slug,product['title'],api.packed(payload))).lastrowid
    return {'order':order_view(db.execute('SELECT * FROM payment_orders WHERE id=?',(identity,)).fetchone())}


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
    result = issue_exam(db,session,payload,'purchase-'+secrets.token_hex(16),'PURCHASE-'+str(identity)+'-'+secrets.token_hex(8))
    db.execute('INSERT INTO exam_order_attempts VALUES (?,?)',(identity,int(result['exam']['id'])))
    return result
