"""Account inboxes and role-scoped, idempotent staff announcements."""
from urllib.parse import parse_qs, urlsplit

from .nickname_policy import safe_nickname
from .platform_api import APIError, stamp

INBOX_SIZE = 5
OUTBOX_SIZE = 25
GROUPS = [('all', 'Tất cả tài khoản'), ('Free', 'Tài khoản Free'),
          ('VIP', 'Tài khoản VIP'), ('SVip', 'Tài khoản SVip')]
INBOX_FIELDS = 'id,title,sender_name,sender_role,kind,body,created_at,read_at'


def page_number(path):
    raw = parse_qs(urlsplit(path).query).get('page', ['1'])[0]
    try:
        page = int(raw)
    except (TypeError, ValueError):
        raise APIError('Số trang không hợp lệ.')
    if not 1 <= page <= 100000:
        raise APIError('Số trang không hợp lệ.')
    return page


def inbox(db, account_id, page=1):
    counts = db.execute('SELECT count(*) total,count(CASE WHEN read_at IS NULL THEN 1 END) unread '
                        'FROM notifications WHERE account_id=?', (account_id,)).fetchone()
    rows = db.execute(f'SELECT {INBOX_FIELDS} FROM notifications WHERE account_id=? '
                      'ORDER BY (read_at IS NOT NULL),created_at DESC,id DESC LIMIT ? OFFSET ?',
                      (account_id, INBOX_SIZE, (page-1)*INBOX_SIZE)).fetchall()
    return {'rows': [dict(row) for row in rows], 'total': counts['total'], 'unreadCount': counts['unread'],
            'page': page, 'pageSize': INBOX_SIZE}


def referrals(db, account_id, page=1):
    total = db.execute('SELECT count(*) FROM account_referrals WHERE inviter_account_id=?', (account_id,)).fetchone()[0]
    rows = db.execute('SELECT r.id,s.full_name,r.registered_at,r.first_vip_upgraded_at,r.reward_status,'
                      'r.reward_granted_at,r.reward_vip_expires_at,rc.confirmed_at support_confirmed_at '
                      'FROM account_referrals r JOIN students s ON s.account_id=r.invitee_account_id '
                      'LEFT JOIN referral_reward_confirmations rc ON rc.referral_id=r.id WHERE r.inviter_account_id=? '
                      'ORDER BY r.registered_at DESC,r.id DESC LIMIT ? OFFSET ?',
                      (account_id, INBOX_SIZE, (page-1)*INBOX_SIZE)).fetchall()
    return {'rows': [{**dict(row), 'full_name': safe_nickname(row['full_name'])} for row in rows],
            'total': total, 'page': page, 'pageSize': INBOX_SIZE}


def read_notice(db, account_id, identity):
    row = db.execute(f'SELECT {INBOX_FIELDS} FROM notifications WHERE id=? AND account_id=?',
                     (identity, account_id)).fetchone()
    if not row:
        raise APIError('Không tìm thấy thông báo của tài khoản này.', 404)
    if row['read_at'] is None:
        db.execute('UPDATE notifications SET read_at=? WHERE id=? AND account_id=?', (stamp(), identity, account_id))
    return dict(db.execute(f'SELECT {INBOX_FIELDS} FROM notifications WHERE id=? AND account_id=?',
                           (identity, account_id)).fetchone())


def audience(db, user, body):
    kind = body.get('audience')
    if kind not in ('all', 'Free', 'VIP', 'SVip', 'class'):
        raise APIError('Nhóm nhận thông báo không hợp lệ.')
    if user['role'] != 'admin' and kind != 'class':
        raise APIError('Giáo viên chỉ được gửi thông báo tới lớp đang được phân công.', 403)
    if kind == 'class':
        identity = body.get('classId')
        if type(identity) is not int or identity < 1:
            raise APIError('Lớp nhận thông báo không hợp lệ.')
        classroom = db.execute("SELECT id,name,teacher_id FROM online_classes WHERE id=? AND status='active'",
                               (identity,)).fetchone()
        if not classroom or (user['role'] != 'admin' and classroom['teacher_id'] != user['teacher_id']):
            raise APIError('Chọn lớp đang hoạt động thuộc quyền quản lý của bạn.', 403)
        return kind, identity, 'Lớp: ' + classroom['name']
    if body.get('classId') is not None:
        raise APIError('Nhóm tài khoản không dùng mã lớp.')
    return kind, None, dict(GROUPS)[kind]


def recipients(db, kind, class_id):
    current = stamp()
    rows = db.execute('SELECT a.id FROM accounts a JOIN students s ON s.account_id=a.id '
                      "WHERE a.deleted_at IS NULL AND s.status='active' AND "
                      "(?<>'class' OR EXISTS(SELECT 1 FROM class_enrollments e WHERE e.student_id=s.id "
                      'AND e.class_id=? AND e.left_at IS NULL)) AND '
                      "(? IN ('all','class') OR ?=CASE WHEN EXISTS(SELECT 1 FROM access_entitlements x "
                      'WHERE x.account_id=a.id AND x.starts_at<=? AND (x.ends_at IS NULL OR x.ends_at>?)) '
                      "THEN 'SVip' WHEN a.vip_expires_at>? THEN 'VIP' ELSE 'Free' END) ORDER BY a.id",
                      (kind, class_id, kind, kind, current, current, current)).fetchall()
    return [row['id'] for row in rows]


def staff_metadata(db, user, page=1):
    classes = [dict(row) for row in db.execute("SELECT id,name,grade_id,teacher_id FROM online_classes "
               "WHERE status='active' AND (?='admin' OR teacher_id=?) ORDER BY name,id", (user['role'], user['teacher_id']))]
    where = "WHERE (?='admin' OR staff_id=?)"
    values = (user['role'], user['id'])
    total = db.execute('SELECT count(*) FROM notification_broadcasts ' + where, values).fetchone()[0]
    rows = db.execute('SELECT id,staff_id,title,body,audience,class_id,audience_label,recipient_count,'
                      'sender_name,sender_role,sender_name staff_name,created_at FROM notification_broadcasts '
                      + where + ' ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',
                      (*values, OUTBOX_SIZE, (page-1)*OUTBOX_SIZE)).fetchall()
    return {'groups': [{'value': value, 'label': label} for value, label in GROUPS] if user['role'] == 'admin' else [],
            'classes': classes, 'rows': [dict(row) for row in rows], 'total': total, 'page': page, 'pageSize': OUTBOX_SIZE}


def preview(db, user, body):
    if set(body)-{'audience', 'classId'}:
        raise APIError('Thông tin nhóm nhận không hợp lệ.')
    kind, class_id, label = audience(db, user, body)
    return {'recipientCount': len(recipients(db, kind, class_id)), 'audienceLabel': label}


def plain_field(body, name, maximum, minimum=1):
    value = body.get(name)
    if not isinstance(value, str) or not minimum <= len(value) <= maximum or not value.strip():
        raise APIError({'title': 'Tiêu đề cần từ 1 đến 160 ký tự.', 'body': 'Nội dung cần từ 1 đến 10.000 ký tự.',
                        'requestKey': 'Mã gửi cần từ 8 đến 80 ký tự.'}[name])
    return value


def send(db, user, body):
    if set(body)-{'title', 'body', 'audience', 'classId', 'requestKey'}:
        raise APIError('Thông tin gửi thông báo không hợp lệ.')
    title, content = plain_field(body, 'title', 160), plain_field(body, 'body', 10000)
    request_key = plain_field(body, 'requestKey', 80, 8)
    kind, class_id, label = audience(db, user, body)
    previous = db.execute('SELECT * FROM notification_broadcasts WHERE staff_id=? AND request_key=?',
                          (user['id'], request_key)).fetchone()
    if previous:
        if (previous['title'], previous['body'], previous['audience'], previous['class_id']) != (title, content, kind, class_id):
            raise APIError('Mã gửi đã dùng cho nội dung khác. Tạo lượt gửi mới để tiếp tục.', 409)
        return {'sent': True, 'broadcastId': previous['id'], 'recipientCount': previous['recipient_count'],
                'audienceLabel': previous['audience_label'], 'replayed': True}
    targets = recipients(db, kind, class_id)
    if not targets:
        raise APIError('Nhóm đã chọn chưa có tài khoản nhận thông báo.')
    created = stamp()
    identity = db.execute('INSERT INTO notification_broadcasts(staff_id,request_key,title,body,audience,class_id,'
                          'audience_label,sender_name,sender_role,recipient_count,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                          (user['id'], request_key, title, content, kind, class_id, label, user['full_name'], user['role'],
                           len(targets), created)).lastrowid
    db.executemany('INSERT INTO notification_broadcast_recipients(broadcast_id,account_id) VALUES (?,?)',
                   [(identity, target) for target in targets])
    db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,sender_staff_id,broadcast_id,created_at) "
               "SELECT account_id,'staff_message',?,?,?,?,?,?,? FROM notification_broadcast_recipients WHERE broadcast_id=?",
               (title, content, user['full_name'], user['role'], user['id'], identity, created, identity))
    db.execute('INSERT INTO staff_audit_log(staff_id,action,entity,entity_id,summary,created_at) VALUES (?,?,?,?,?,?)',
               (user['id'], 'send', 'notification_broadcast', str(identity), f'{title} · {label} · {len(targets)} tài khoản', created))
    return {'sent': True, 'broadcastId': identity, 'recipientCount': len(targets), 'audienceLabel': label, 'replayed': False}
