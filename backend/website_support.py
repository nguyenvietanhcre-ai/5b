"""Authenticated support, manual refund records and draft website configuration.

This module never transfers money, deletes account data, revokes entitlements,
sends mail or publishes policy. All writes share the existing IMMEDIATE transaction.
"""
import hmac
import json
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from .platform_api import APIError, connect, read_session, same_origin, stamp, text_field
from .staff_api import read_session as read_staff, require_admin, audit

POLICY_VERSION = '2026-11-17-draft1'
BUSINESS_FIELDS = ('legal_name', 'registration_number', 'tax_code', 'representative', 'address', 'phone', 'email')
KINDS = ('support', 'order', 'refund', 'data_access', 'data_correct', 'data_delete', 'consent_withdraw')
TRANSITIONS = {
    'received': ('reviewing', 'waiting_user', 'resolved', 'rejected'),
    'reviewing': ('waiting_user', 'resolved', 'rejected'),
    'waiting_user': ('reviewing', 'resolved', 'rejected'),
    'resolved': (), 'rejected': (),
}


def get_business(db):
    row = db.execute('SELECT * FROM website_business WHERE id=1').fetchone()
    data = json.loads(row['payload_json']) if row else {}
    return {'business': {key: data.get(key, '') for key in BUSINESS_FIELDS},
            'revision': row['revision'] if row else 1,
            'policyVersion': POLICY_VERSION, 'policyDraft': True}


def _integer(value, label, minimum=1):
    if type(value) is not int or value < minimum or value > 2**53-1:
        raise APIError(label + ' không hợp lệ.')
    return value


def _revision(row, body):
    if type(body.get('revision')) is not int or body['revision'] != row['revision']:
        raise APIError('Yêu cầu vừa thay đổi. Tải lại trước khi lưu.', 409)


def _request(db, identity, account_id=None):
    sql, args = 'SELECT * FROM website_support_requests WHERE id=?', [identity]
    if account_id is not None:
        sql += ' AND account_id=?'
        args.append(account_id)
    row = db.execute(sql, args).fetchone()
    if row is None:
        raise APIError('Không tìm thấy yêu cầu.', 404)
    return row


def _detail(db, row):
    result = dict(row)
    result['events'] = [dict(e) for e in db.execute(
        'SELECT id,actor,status,message,created_at FROM website_support_events WHERE request_id=? ORDER BY id', (row['id'],))]
    result['refunds'] = [dict(e) for e in db.execute(
        'SELECT amount,reference,manual_status,created_at FROM website_refund_records WHERE request_id=? ORDER BY id', (row['id'],))]
    return result


def _event(db, row, actor, message, status=None, staff_id=None):
    current = status or row['status']
    db.execute('INSERT INTO website_support_events(request_id,actor,staff_id,status,message,created_at) VALUES(?,?,?,?,?,?)',
               (row['id'], actor, staff_id, current, message, stamp()))
    db.execute('UPDATE website_support_requests SET status=?,revision=revision+1,updated_at=? WHERE id=?',
               (current, stamp(), row['id']))


def _create(db, session, body):
    kind = body.get('kind')
    if kind not in KINDS:
        raise APIError('Loại yêu cầu không hợp lệ.')
    subject = text_field(body, 'subject', 150)
    message = text_field(body, 'message', 4000)
    order_id = body.get('orderId')
    if order_id == '':
        order_id = None
    if order_id is not None:
        _integer(order_id, 'Mã đơn')
        if not db.execute('SELECT 1 FROM payment_orders WHERE id=? AND account_id=? AND family_cart_order_id IS NULL '
                          'AND family_cart_product_line_id IS NULL',
                          (order_id,session['account_id'])).fetchone():
            raise APIError('Không tìm thấy đơn của tài khoản này.',404)
    if kind in ('order','refund') and order_id is None:
        raise APIError('Chọn mã đơn thuộc tài khoản để gửi yêu cầu về đơn/hoàn tiền.')
    if db.execute("SELECT count(*) FROM website_support_requests WHERE account_id=? AND status IN ('received','reviewing','waiting_user')",(session['account_id'],)).fetchone()[0] >= 30:
        raise APIError('Đã có nhiều yêu cầu đang xử lý. Hãy bổ sung vào yêu cầu hiện có.',429)
    ticket = '5B-' + secrets.token_hex(6).upper()
    identity = db.execute('INSERT INTO website_support_requests(ticket,account_id,kind,subject,order_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                          (ticket, session['account_id'], kind, subject, order_id, stamp(),stamp())).lastrowid
    row = _request(db, identity)
    _event(db,row,'user',message)
    return {'request': _detail(db,_request(db,identity))}


def export_preview(db, session):
    """Explicit allowlist. Never serialize auth/session rows or arbitrary tables."""
    account = dict(db.execute('SELECT id,account_code,login_identifier,birth_year,created_at,status FROM accounts WHERE id=?',
                              (session['account_id'],)).fetchone())
    student = dict(db.execute('SELECT id,student_code,full_name,grade_level,status,created_at FROM students WHERE id=? AND account_id=?',
                              (session['student_id'],session['account_id'])).fetchone())
    orders = [dict(r) for r in db.execute('SELECT id,reference,amount,status,created_at FROM payment_orders '
                                        'WHERE account_id=? AND family_cart_order_id IS NULL '
                                        'AND family_cart_product_line_id IS NULL ORDER BY id',
                                        (session['account_id'],))]
    requests = [_detail(db,r) for r in db.execute('SELECT * FROM website_support_requests WHERE account_id=? ORDER BY id', (session['account_id'],))]
    consents = []
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='website_account_consents'").fetchone():
        consents = [dict(r) for r in db.execute('SELECT version,representative_name,representative_contact,representative_role,accepted_at FROM website_account_consents WHERE account_id=? ORDER BY id',(session['account_id'],))]
    for consent in consents:
        consent['representativeVerification'] = 'self_declared'
    return {'generatedAt':stamp(),'scope':'Bản trích xuất một phần: hồ sơ, đơn thanh toán và yêu cầu hỗ trợ của chính tài khoản. Chưa bao gồm toàn bộ lịch sử học, tệp nộp bài hay dữ liệu cần rà soát thủ công. Gửi yêu cầu truy cập dữ liệu nếu cần bổ sung.',
            'account':account,'student':student,'orders':orders,'requests':requests,'websiteConsents':consents}


def _refund(db, user, row, body):
    if row['kind'] != 'refund' or row['status'] not in ('received','reviewing','waiting_user'):
        raise APIError('Chỉ ghi hoàn tiền cho yêu cầu hoàn tiền còn đang xử lý.')
    order = db.execute("SELECT * FROM payment_orders WHERE id=? AND account_id=? AND status='paid'", (row['order_id'],row['account_id'])).fetchone()
    if order is None:
        raise APIError('Đơn chưa được xác nhận đã thanh toán.')
    amount = _integer(body.get('amount'), 'Số tiền')
    reference = text_field(body,'reference',100)
    if not re.fullmatch(r'[A-Za-z0-9._/-]{3,100}', reference):
        raise APIError('Mã tham chiếu chỉ gồm chữ không dấu, số, dấu chấm/gạch.')
    message = text_field(body,'message',4000)
    total = db.execute('SELECT coalesce(sum(amount),0) FROM website_refund_records WHERE order_id=?',(order['id'],)).fetchone()[0]
    if total + amount > order['amount']:
        raise APIError('Tổng tiền hoàn không được vượt số tiền đã thanh toán.')
    if db.execute('SELECT 1 FROM website_refund_records WHERE reference=?',(reference,)).fetchone():
        raise APIError('Mã tham chiếu hoàn tiền đã được ghi nhận.',409)
    db.execute("INSERT INTO website_refund_records(request_id,order_id,amount,reference,manual_status,staff_id,created_at) VALUES(?,?,?,?,'completed_manual',?,?)", (row['id'],order['id'],amount,reference,user['id'],stamp()))
    _event(db,row,'admin',f'Ghi nhận hoàn tiền thủ công {amount} VND; mã {reference}. '+message,staff_id=user['id'])
    audit(db,user,'manual_refund','website_support',row['id'],f'Ghi nhận {amount} VND; tham chiếu {reference}; không tự đổi quyền')


def dispatch(handler, method, path, body=None):
    body = body or {}
    if not isinstance(body,dict):
        raise APIError('Nội dung yêu cầu không hợp lệ.')
    if method not in ('GET','POST'):
        raise APIError('Phương thức không hỗ trợ.',405)
    admin = path.startswith('/api/website/admin/')
    if method == 'POST' and not same_origin(handler):
        raise APIError('Yêu cầu phải xuất phát từ website đang mở.',403)
    with connect(handler.server.database_path,method=='POST') as db:
        user = read_staff(handler,db) if admin else read_session(handler,db)
        if not user:
            raise APIError('Đăng nhập để tiếp tục.',401)
        if admin:
            require_admin(user)
        if method == 'POST' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),user['csrf_token']):
            raise APIError('Phiên đăng nhập cần được tải lại.',403)
        if path == '/api/website/support/session' and method=='GET':
            return {'authenticated':True,'csrf':user['csrf_token']},200
        if path == '/api/website/admin/config':
            if method=='POST':
                row = db.execute('SELECT * FROM website_business WHERE id=1').fetchone()
                _revision(row,body)
                data = {key:text_field(body,key,500 if key=='address' else 200,0) for key in BUSINESS_FIELDS}
                if data['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):
                    raise APIError('Địa chỉ email không hợp lệ.')
                db.execute('UPDATE website_business SET payload_json=?,revision=revision+1,updated_at=? WHERE id=1',(json.dumps(data,ensure_ascii=False),stamp()))
                audit(db,user,'config','website_business',1,'Cập nhật thông tin chủ quản; không xác nhận BCT/chính sách')
            return get_business(db),200
        if path == '/api/website/admin/policies':
            if method=='POST':
                version = text_field(body,'version',80)
                if not re.fullmatch(r'[A-Za-z0-9._-]{3,80}',version):
                    raise APIError('Mã phiên bản không hợp lệ.')
                if db.execute('SELECT 1 FROM website_policy_drafts WHERE version=?',(version,)).fetchone():
                    raise APIError('Phiên bản đã tồn tại; lưu phiên bản nháp mới.',409)
                title,content = text_field(body,'title',200),text_field(body,'content',30000)
                db.execute('INSERT INTO website_policy_drafts(version,title,content,created_at,staff_id) VALUES(?,?,?,?,?)',(version,title,content,stamp(),user['id']))
                audit(db,user,'draft','website_policy',version,'Lưu phiên bản nháp; chưa phát hành')
            return {'policies':[dict(r) for r in db.execute('SELECT id,version,title,content,draft,created_at FROM website_policy_drafts ORDER BY id DESC LIMIT 100')]},200
        prefix = '/api/website/admin/requests' if admin else '/api/website/support/requests'
        if path == prefix:
            if method=='POST':
                if admin:raise APIError('Quản trị xử lý yêu cầu đã có.',405)
                return _create(db,user,body),201
            query,args = ('SELECT * FROM website_support_requests WHERE 1=1',[]) if admin else ('SELECT * FROM website_support_requests WHERE account_id=?',[user['account_id']])
            before = parse_qs(urlsplit(handler.path).query).get('before', [''])[0]
            if before:
                if not re.fullmatch(r'[1-9][0-9]{0,15}',before):
                    raise APIError('Mốc trang không hợp lệ.')
                query += ' AND id<?'
                args.append(int(before))
            rows = [dict(r) for r in db.execute(query+' ORDER BY id DESC LIMIT 201',args)]
            return {'requests':rows[:200],'limit':200,'nextCursor':rows[199]['id'] if len(rows)>200 else None},200
        if not admin and path in ('/api/website/support/export/preview','/api/website/support/export/download') and method=='GET':
            return {'export':export_preview(db,user),'filename':'5bmath-du-lieu-ca-nhan.json'},200
        match = re.fullmatch(re.escape(prefix)+r'/(\d+)(?:/(reply|status|refund))?',path)
        if match:
            row = _request(db,int(match[1]),None if admin else user['account_id'])
            action = match[2]
            if method=='GET' and action is None:
                return {'request':_detail(db,row)},200
            if method=='POST' and action in ('reply','status','refund'):
                _revision(row,body)
                if action=='refund' and admin:
                    _refund(db,user,row,body)
                elif action=='status' and admin:
                    status = body.get('status')
                    if status not in TRANSITIONS[row['status']]:
                        raise APIError('Chuyển trạng thái không hợp lệ.',409)
                    message = text_field(body,'message',4000)
                    _event(db,row,'admin',message,status,user['id'])
                    audit(db,user,'status','website_support',row['id'],'Kết luận/trạng thái: '+status)
                elif action=='reply':
                    if row['status'] in ('resolved','rejected'):
                        raise APIError('Yêu cầu đã kết thúc. Tạo yêu cầu mới để trao đổi tiếp.',409)
                    _event(db,row,'admin' if admin else 'user',text_field(body,'message',4000),staff_id=user['id'] if admin else None)
                    if admin:audit(db,user,'reply','website_support',row['id'],'Phản hồi người dùng')
                else:
                    raise APIError('Không có quyền thực hiện.',403)
                return {'request':_detail(db,_request(db,row['id']))},200
        raise APIError('Không tìm thấy chức năng.',404)
