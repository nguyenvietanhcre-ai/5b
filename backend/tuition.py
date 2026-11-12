"""Server-calculated monthly tuition with explicit preview and saved calendars."""
import hashlib
import json
import re
from datetime import datetime

from .nickname_policy import safe_nickname
from .platform_api import APIError, VN, packed, stamp

MAX_AMOUNT = 1_000_000_000


def month_field(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value):
        raise APIError('Tháng học phí cần có dạng YYYY-MM.')
    try:
        datetime.strptime(value, '%Y-%m')
    except ValueError:
        raise APIError('Tháng học phí không hợp lệ.')
    return value


def session_calendar(db, class_id, student_id, month):
    result = []
    for row in db.execute('SELECT s.id,s.title,s.starts_at,a.status FROM class_sessions s '
                          'LEFT JOIN class_attendance a ON a.session_id=s.id AND a.student_id=? '
                          "WHERE s.class_id=? AND substr(datetime(s.starts_at,'+7 hours'),1,7)=? ORDER BY s.starts_at,s.id",
                          (student_id, class_id, month)):
        day = datetime.fromisoformat(row['starts_at'].replace('Z', '+00:00')).astimezone(VN).date().isoformat()
        result.append({'id': row['id'], 'title': row['title'], 'startsAt': row['starts_at'], 'date': day, 'status': row['status']})
    return result


def snapshot(rate, sessions):
    counts = {name: sum(row['status'] == status for row in sessions) for name, status in
              [('chargedCount', 'charged'), ('freeCount', 'free'), ('absentCount', 'absent'), ('pendingCount', None)]}
    return {'sessionFee': rate, **counts, 'sessions': sessions}


def fee_detail(db, fee):
    result = dict(fee)
    sessions = (json.loads(fee['sessions_json']) if fee['source'] == 'calculated' and fee['sessions_json'] is not None
                else session_calendar(db, fee['class_id'], fee['student_id'], fee['month']))
    result['sessions'] = [{**row, 'starts_at': row['startsAt']} for row in sessions]
    result['count'] = fee['charged_count'] if fee['source'] == 'calculated' else sum(row['status'] == 'charged' for row in sessions)
    return result


def preview(db, info, body):
    if set(body)-{'month'}:
        raise APIError('Chỉ cần chọn tháng để tính học phí.')
    month = month_field(body.get('month'))
    rate = info['session_fee']
    if rate is None:
        raise APIError('Admin cần cấu hình học phí mỗi buổi của lớp trước khi tính.')
    if type(rate) is not int or not 0 <= rate <= MAX_AMOUNT:
        raise APIError('Học phí mỗi buổi không hợp lệ.')
    class_id = info['id']
    students = db.execute('SELECT s.*,a.deleted_at,a.status account_status FROM students s '
        'LEFT JOIN accounts a ON a.id=s.account_id WHERE '
        'EXISTS(SELECT 1 FROM class_enrollments e WHERE e.student_id=s.id AND e.class_id=? AND e.left_at IS NULL) '
        'OR EXISTS(SELECT 1 FROM class_attendance a JOIN class_sessions c ON c.id=a.session_id '
        "WHERE a.student_id=s.id AND c.class_id=? AND substr(datetime(c.starts_at,'+7 hours'),1,7)=?) "
        'OR EXISTS(SELECT 1 FROM class_fees f WHERE f.student_id=s.id AND f.class_id=? AND f.month=?) ORDER BY s.id',
        (class_id, class_id, month, class_id, month)).fetchall()
    fees = {row['student_id']: row for row in db.execute('SELECT * FROM class_fees WHERE class_id=? AND month=? ORDER BY id', (class_id, month))}
    rows, token_students = [], []
    for student in students:
        sid = student['id']
        old = fees.get(sid)
        eligible = bool(student['account_id'] and student['deleted_at'] is None and student['status'] == 'active')
        if not eligible and not old:
            continue
        current = db.execute('SELECT 1 FROM class_enrollments WHERE student_id=? AND class_id=? AND left_at IS NULL', (sid, class_id)).fetchone()
        sessions = session_calendar(db, class_id, sid, month)
        saved = snapshot(rate, sessions)
        amount = rate*saved['chargedCount']
        paid = bool(old and (old['paid_at'] or db.execute("SELECT 1 FROM payment_orders WHERE fee_id=? AND status='paid'", (old['id'],)).fetchone()))
        locked = paid or not eligible
        if not locked and amount > MAX_AMOUNT:
            raise APIError(f'Học phí của {safe_nickname(student["full_name"])} vượt giới hạn 1.000.000.000 đồng.')
        changed = bool(not locked and (not old or old['source'] != 'calculated' or old['amount'] != amount
            or old['session_fee'] != rate or old['sessions_json'] != packed(sessions)))
        rows.append({'studentId': sid, 'fullName': safe_nickname(student['full_name']), 'accountId': student['account_id'],
            'historical': not bool(current), 'eligible': eligible, 'chargedCount': saved['chargedCount'], 'freeCount': saved['freeCount'],
            'absentCount': saved['absentCount'], 'pendingCount': saved['pendingCount'], 'amount': old['amount'] if locked and old else amount,
            'calculatedAmount': amount, 'existingAmount': old['amount'] if old else None, 'feeId': old['id'] if old else None,
            'paidAt': old['paid_at'] if old else None, 'source': old['source'] if old else 'calculated', 'locked': locked,
            'lockedReason': 'paid' if paid else 'inactive' if not eligible else None, 'sessions': sessions, 'changed': changed})
        token_students.append(dict(student))
    sessions_input = [dict(row) for row in db.execute("SELECT * FROM class_sessions WHERE class_id=? AND substr(datetime(starts_at,'+7 hours'),1,7)=? ORDER BY id", (class_id, month))]
    attendance = [dict(row) for row in db.execute('SELECT a.* FROM class_attendance a JOIN class_sessions c ON c.id=a.session_id '
        "WHERE c.class_id=? AND substr(datetime(c.starts_at,'+7 hours'),1,7)=? ORDER BY a.session_id,a.student_id", (class_id, month))]
    enrollments = [dict(row) for row in db.execute('SELECT * FROM class_enrollments WHERE class_id=? ORDER BY id', (class_id,))]
    orders = [dict(row) for row in db.execute('SELECT o.* FROM payment_orders o JOIN class_fees f ON f.id=o.fee_id '
        'WHERE f.class_id=? AND f.month=? ORDER BY o.id', (class_id, month))]
    inputs = {'class': dict(info), 'month': month, 'students': token_students, 'sessions': sessions_input,
              'attendance': attendance, 'enrollments': enrollments, 'fees': [dict(row) for row in fees.values()], 'orders': orders}
    token = hashlib.sha256(packed(inputs).encode()).hexdigest()
    totals = {key: sum(row[key] for row in rows) for key in ('chargedCount', 'freeCount', 'absentCount', 'pendingCount')}
    totals.update(students=len(rows), totalAmount=sum(row['amount'] for row in rows),
                  paidLocked=sum(row['lockedReason'] == 'paid' for row in rows), changed=sum(row['changed'] for row in rows))
    return {'classId': class_id, 'className': info['name'], 'month': month, 'sessionFee': rate,
            'previewToken': token, 'rows': rows, 'totals': totals}


def cancel_pending(db, fee_id):
    db.execute("UPDATE payment_orders SET status='cancelled' WHERE fee_id=? AND status='pending'", (fee_id,))


def calculate(db, user, info, body):
    if set(body)-{'month', 'previewToken', 'requestKey'}:
        raise APIError('Không gửi số tiền tự tính từ trình duyệt.')
    month = month_field(body.get('month'))
    request_key, token = body.get('requestKey'), body.get('previewToken')
    if not isinstance(request_key, str) or not 8 <= len(request_key) <= 80 or not request_key.strip():
        raise APIError('Mã lưu cần từ 8 đến 80 ký tự.')
    if not isinstance(token, str) or not re.fullmatch('[0-9a-f]{64}', token):
        raise APIError('Cần xem trước học phí trước khi lưu.')
    previous = db.execute('SELECT * FROM class_tuition_calculations WHERE staff_id=? AND request_key=?', (user['id'], request_key)).fetchone()
    if previous:
        if (previous['class_id'], previous['month'], previous['preview_token']) != (info['id'], month, token):
            raise APIError('Mã lưu đã dùng cho bảng tính khác.', 409)
        return {**json.loads(previous['result_json']), 'replayed': True}
    candidate = preview(db, info, {'month': month})
    if token != candidate['previewToken']:
        raise APIError('Điểm danh, học phí hoặc thanh toán vừa thay đổi. Tính lại và kiểm tra trước khi lưu.', 409)
    created_at = stamp()
    identity = db.execute('INSERT INTO class_tuition_calculations(class_id,staff_id,request_key,month,preview_token,result_json,created_at) '
        'VALUES (?,?,?,?,?,?,?)', (info['id'], user['id'], request_key, month, token, '{}', created_at)).lastrowid
    summary = {'id': identity, 'month': month, 'created': 0, 'updated': 0, 'unchanged': 0,
               'paidLocked': 0, 'notificationsSent': 0, 'totalAmount': candidate['totals']['totalAmount'], 'replayed': False}
    for row in candidate['rows']:
        action = 'paidLocked' if row['lockedReason'] == 'paid' else 'unchanged'
        fee_id = row['feeId']
        if row['changed']:
            action = 'updated' if fee_id else 'created'
            if fee_id and row['amount'] != row['existingAmount']:
                cancel_pending(db, fee_id)
            values = (row['amount'], candidate['sessionFee'], row['chargedCount'], row['freeCount'], row['absentCount'],
                      row['pendingCount'], packed(row['sessions']), identity, created_at)
            if fee_id:
                db.execute("UPDATE class_fees SET amount=?,source='calculated',session_fee=?,charged_count=?,free_count=?,absent_count=?,"
                    'pending_count=?,sessions_json=?,calculation_id=?,calculated_at=? WHERE id=?', (*values, fee_id))
            else:
                fee_id = db.execute('INSERT INTO class_fees(amount,session_fee,charged_count,free_count,absent_count,pending_count,'
                    "sessions_json,calculation_id,calculated_at,source,class_id,student_id,month) VALUES (?,?,?,?,?,?,?,?,?,'calculated',?,?,?)",
                    (*values, info['id'], row['studentId'], month)).lastrowid
            title = f'Học phí tháng {month} · {info["name"]}'
            content = (f'Học phí tháng {month}: {row["amount"]:,} đồng.\n'
                f'{row["chargedCount"]} buổi tính phí × {candidate["sessionFee"]:,} đồng/buổi.\n'
                + ('Liên hệ giáo viên để xem chi tiết học phí của lớp cũ.' if row['historical'] else
                   'Em mở Lớp Zoom → Học phí để xem lịch từng buổi đã lưu.')).replace(',', '.')
            db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,sender_staff_id,created_at) "
                "VALUES (?,'staff_message',?,?,?,?,?,?)", (row['accountId'], title, content, user['full_name'], user['role'], user['id'], created_at))
            from .zoom_classroom import create_notices
            create_notices(db, info['id'], 'fees', fee_id, row['studentId'], refresh=True)
            summary['notificationsSent'] += 1
        summary[action] += 1
        saved = {'sessionFee': candidate['sessionFee'], 'amount': row['amount'], 'chargedCount': row['chargedCount'],
                 'freeCount': row['freeCount'], 'absentCount': row['absentCount'], 'pendingCount': row['pendingCount'], 'sessions': row['sessions']}
        db.execute('INSERT INTO class_tuition_calculation_items(calculation_id,student_id,fee_id,action,snapshot_json) VALUES (?,?,?,?,?)',
                   (identity, row['studentId'], fee_id, action, packed(saved)))
    db.execute('UPDATE class_tuition_calculations SET result_json=? WHERE id=?', (packed(summary), identity))
    if summary['created'] or summary['updated']:
        db.execute('UPDATE online_classes SET revision=revision+1 WHERE id=?', (info['id'],))
    db.execute('INSERT INTO staff_audit_log(staff_id,action,entity,entity_id,summary,created_at) VALUES (?,?,?,?,?,?)',
        (user['id'], 'calculate', 'class_tuition', str(identity), f'{info["name"]} · {month} · {summary["created"]} mới, {summary["updated"]} cập nhật', created_at))
    return summary
