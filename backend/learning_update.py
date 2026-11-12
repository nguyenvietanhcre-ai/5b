"""Membership, usage, classroom views and pending bank-transfer orders."""
from collections import defaultdict
from datetime import datetime, timedelta

from .platform_api import APIError, VN, now, stamp
from .nickname_policy import safe_nickname

LIMITS = {'content': 1, 'combined': 1, 'human': 3, 'bot': 5}


def membership(db, session):
    aid = session['account_id']
    if db.execute('SELECT 1 FROM access_entitlements WHERE account_id=? AND starts_at<=? AND (ends_at IS NULL OR ends_at>?)',
                  (aid, stamp(), stamp())).fetchone():
        return 'SVip'
    expiry = db.execute('SELECT vip_expires_at FROM accounts WHERE id=?', (aid,)).fetchone()[0]
    return 'VIP' if expiry and expiry > stamp() else 'Free'


def usage(db, session):
    from .system_settings import settings
    day = now().astimezone(VN).date().isoformat()
    counts = dict(db.execute('SELECT category,count(*) FROM daily_usage WHERE student_id=? AND day=? GROUP BY category',
                             (session['student_id'], day)))
    paid = membership(db, session) != 'Free'
    limits = settings(db)['free_limits']
    return {key: {'used': counts.get(key, 0), 'limit': None if paid else limits[key]} for key in LIMITS}


def consume(db, session, category, key):
    if db.execute('SELECT 1 FROM daily_usage WHERE student_id=? AND category=? AND request_key=?',
                  (session['student_id'], category, key)).fetchone():
        return
    value = usage(db, session)[category]
    if value['limit'] is not None and value['used'] >= value['limit']:
        raise APIError('Em đã dùng hết lượt hôm nay. Vào Nâng cấp gói để luyện tập không giới hạn.', 429)
    db.execute('INSERT INTO daily_usage VALUES (?,?,?,?)',
               (session['student_id'], now().astimezone(VN).date().isoformat(), category, key))


def enrolled(db, session, class_id):
    if membership(db, session) != 'SVip':
        raise APIError('Lớp Zoom dành cho học sinh nội bộ.', 403)
    row = db.execute('SELECT c.*,t.full_name teacher FROM online_classes c JOIN teachers t ON t.id=c.teacher_id '
                     'JOIN class_enrollments e ON e.class_id=c.id WHERE c.id=? AND e.student_id=? '
                     'AND e.left_at IS NULL AND c.status=\'active\'', (class_id, session['student_id'])).fetchone()
    if not row:
        raise APIError('Lớp học không thuộc tài khoản của em.', 403)
    return dict(row)


def local_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(VN).date()


def classroom(db, session, class_id, query):
    from .zoom_classroom import notice_snapshot, submission_metadata
    info = enrolled(db, session, class_id)
    start, end = (query.get(k, [''])[0] for k in ('from', 'to'))
    try:
        if start: datetime.strptime(start, '%Y-%m-%d')
        if end: datetime.strptime(end, '%Y-%m-%d')
    except ValueError:
        raise APIError('Ngày lọc không hợp lệ.')
    if start and end and start > end:
        raise APIError('Từ ngày phải trước hoặc bằng đến ngày.')
    sessions = [dict(r) for r in db.execute('SELECT * FROM class_sessions WHERE class_id=? ORDER BY starts_at DESC', (class_id,))]
    month_scores, cycle_scores = defaultdict(list), defaultdict(list)
    anchor = datetime.fromisoformat(db.execute('SELECT instruction_starts_on FROM academic_years WHERE id=?', (info['academic_year_id'],)).fetchone()[0]).date()
    assignments = []
    for lesson in sessions:
        date = local_date(lesson['starts_at'])
        lesson['date'] = date.isoformat()
        personal = db.execute('SELECT comment FROM class_session_comments WHERE session_id=? AND student_id=?',
                              (lesson['id'], session['student_id'])).fetchone()
        attendance = db.execute('SELECT status FROM class_attendance WHERE session_id=? AND student_id=?',
                                (lesson['id'], session['student_id'])).fetchone()
        lesson['personal_comment'] = personal[0] if personal else ''
        lesson['attendance_status'] = attendance[0] if attendance else None
        lesson['assignments'] = [dict(r) for r in db.execute('SELECT a.*,s.score,coalesce(c.comment,\'\') comment FROM class_assignments a '
            'LEFT JOIN class_scores s ON s.assignment_id=a.id AND s.student_id=? '
            'LEFT JOIN class_assignment_comments c ON c.assignment_id=a.id AND c.student_id=? '
            'WHERE a.session_id=? ORDER BY a.id',
            (session['student_id'], session['student_id'], lesson['id']))]
        for assignment in lesson['assignments']:
            submitted = db.execute('SELECT id,assignment_id,student_id,filename,mime_type,size,submitted_at '
                                   'FROM class_submissions WHERE assignment_id=? AND student_id=? ORDER BY id DESC LIMIT 1',
                                   (assignment['id'], session['student_id'])).fetchone()
            assignment['submission'] = submission_metadata(submitted) if submitted else None
        lesson['complete'] = bool(lesson['assignments']) and all(a['score'] is not None for a in lesson['assignments'])
        assignments.extend(lesson['assignments'])
        for a in lesson['assignments']:
            if a['score'] is not None:
                month_scores[date.strftime('%Y-%m')].append(a['score'])
        cycle = max(0, (date-anchor).days // 14)
        cycle_scores[cycle].extend(a['score'] for a in lesson['assignments'] if a['score'] is not None)
    fees = []
    from .tuition import fee_detail
    for r in db.execute('SELECT * FROM class_fees WHERE class_id=? AND student_id=? ORDER BY month DESC', (class_id, session['student_id'])):
        fees.append(fee_detail(db,r))
    return {'class': info, 'sessions': [s for s in sessions if (not start or s['date'] >= start) and (not end or s['date'] <= end)],
            'months': [{'month': m, 'average': round(sum(v)/len(v), 2)} for m, v in sorted(month_scores.items())],
            'cycles': [{'index': c, 'from': (anchor+timedelta(days=c*14)).isoformat(),
                        'to': (anchor+timedelta(days=c*14+13)).isoformat(),
                        'average': round(sum(v)/len(v), 2) if v else None} for c, v in sorted(cycle_scores.items(), reverse=True)], 'fees': fees,
            **notice_snapshot(db, session, class_id)}


def class_ranking(db, session, class_id, query):
    info = enrolled(db, session, class_id)
    assignment = query.get('assignment', [''])[0]
    cycle = query.get('cycle', [''])[0]
    if not assignment and not cycle: raise APIError('Chọn bài tập hoặc chu kỳ.')
    if assignment and not db.execute('SELECT 1 FROM class_assignments a JOIN class_sessions s ON s.id=a.session_id WHERE a.id=? AND s.class_id=?', (assignment, class_id)).fetchone():
        raise APIError('Bài tập không thuộc lớp này.', 404)
    anchor = datetime.fromisoformat(db.execute('SELECT instruction_starts_on FROM academic_years WHERE id=?', (info['academic_year_id'],)).fetchone()[0]).date()
    try: index = int(cycle) if cycle else None
    except ValueError: raise APIError('Chu kỳ không hợp lệ.')
    if index is not None and not 0 <= index <= 30: raise APIError('Chu kỳ không hợp lệ.')
    students = db.execute('SELECT s.id,s.full_name FROM students s JOIN class_enrollments e ON e.student_id=s.id WHERE e.class_id=? AND e.left_at IS NULL', (class_id,)).fetchall()
    rows = []
    for student in students:
        scores = [r['score'] for r in db.execute('SELECT x.score,s.starts_at,a.id FROM class_scores x '
                  'JOIN class_assignments a ON a.id=x.assignment_id JOIN class_sessions s ON s.id=a.session_id '
                  'WHERE x.student_id=? AND s.class_id=?', (student['id'], class_id))
                  if (str(r['id']) == assignment if assignment else max(0, (local_date(r['starts_at'])-anchor).days//14) == index)]
        rows.append({'name': safe_nickname(student['full_name']), 'mine': student['id'] == session['student_id'], 'value': round(sum(scores)/len(scores), 2) if scores else None})
    rows.sort(key=lambda r: -(r['value'] if r['value'] is not None else -1))
    previous, rank = object(), 0
    for i, row in enumerate(rows, 1):
        if row['value'] != previous: rank = i
        previous = row['value']
        row['rank'] = rank if row['value'] is not None else None
    return {'rows': rows}


def payment(db, session, body):
    from .payments import create_order
    return create_order(db, session, body)
