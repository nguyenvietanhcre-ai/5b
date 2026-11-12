"""Private Zoom homework files, per-student remarks and tab unread counts."""
import base64
import binascii
import hashlib
import re
from urllib.parse import quote

from .platform_api import APIError, stamp, text_field

MAX_FILE_SIZE = 10 * 1024 * 1024
FILE_CHUNK_SIZE = 1024 * 1024


def _atomic_submission(db, write):
    """Nest file writes without committing the caller's larger transaction."""
    atomic = getattr(db, 'atomic', None)
    if callable(atomic):
        # The Durable Object adapter uses storage.transactionSync; it does not
        # accept SQL SAVEPOINT statements.
        return atomic(write)
    db.execute('SAVEPOINT class_submission_file')
    try:
        result = write()
    except BaseException:
        db.execute('ROLLBACK TO SAVEPOINT class_submission_file')
        db.execute('RELEASE SAVEPOINT class_submission_file')
        raise
    db.execute('RELEASE SAVEPOINT class_submission_file')
    return result


def attendance_rows(db, session_id):
    return [dict(row) for row in db.execute(
        'SELECT a.session_id,a.student_id,a.status,coalesce(c.comment,\'\') comment '
        'FROM class_attendance a LEFT JOIN class_session_comments c '
        'ON c.session_id=a.session_id AND c.student_id=a.student_id WHERE a.session_id=? '
        'UNION ALL SELECT c.session_id,c.student_id,NULL,c.comment FROM class_session_comments c '
        'WHERE c.session_id=? AND NOT EXISTS (SELECT 1 FROM class_attendance a '
        'WHERE a.session_id=c.session_id AND a.student_id=c.student_id)', (session_id, session_id))]


def score_rows(db, session_id):
    return [dict(row) for row in db.execute(
        'SELECT x.assignment_id,x.student_id,x.score,coalesce(c.comment,\'\') comment '
        'FROM class_scores x JOIN class_assignments a ON a.id=x.assignment_id '
        'LEFT JOIN class_assignment_comments c ON c.assignment_id=x.assignment_id AND c.student_id=x.student_id '
        'WHERE a.session_id=? UNION ALL SELECT c.assignment_id,c.student_id,NULL,c.comment '
        'FROM class_assignment_comments c JOIN class_assignments a ON a.id=c.assignment_id '
        'WHERE a.session_id=? AND NOT EXISTS (SELECT 1 FROM class_scores x '
        'WHERE x.assignment_id=c.assignment_id AND x.student_id=c.student_id)', (session_id, session_id))]


def submission_metadata(row, staff=False):
    data = {key: row[key] for key in ('id', 'assignment_id', 'student_id', 'filename', 'mime_type', 'size', 'submitted_at')}
    data['url'] = (f'/api/staff/submissions/{row["id"]}/file' if staff else
                   f'/api/v1/class-submissions/{row["id"]}/file')
    return data


def session_submissions(db, session_id):
    return [submission_metadata(row, True) for row in db.execute(
        'SELECT x.id,x.assignment_id,x.student_id,x.filename,x.mime_type,x.size,x.submitted_at '
        'FROM class_submissions x JOIN class_assignments a ON a.id=x.assignment_id '
        'WHERE a.session_id=? AND x.id=(SELECT max(n.id) FROM class_submissions n '
        'WHERE n.assignment_id=x.assignment_id AND n.student_id=x.student_id)', (session_id,))]


def create_notices(db, class_id, section, source_id, student_id=None, refresh=False):
    if refresh:
        # A changed bill needs a new watermark, so an acknowledgement of its
        # previous version cannot consume the new unread notice.
        db.execute('DELETE FROM class_notices WHERE class_id=? AND section=? AND source_id=? '
                   'AND (? IS NULL OR student_id=?)', (class_id,section,source_id,student_id,student_id))
    db.execute('INSERT OR IGNORE INTO class_notices(class_id,student_id,section,source_id,created_at) '
               'SELECT e.class_id,e.student_id,?,?,? FROM class_enrollments e '
               'JOIN students s ON s.id=e.student_id JOIN accounts a ON a.id=s.account_id '
               'JOIN online_classes c ON c.id=e.class_id '
               "WHERE e.class_id=? AND e.left_at IS NULL AND c.status='active' "
               "AND s.status='active' AND a.deleted_at IS NULL "
               'AND (? IS NULL OR e.student_id=?)',
               (section, source_id, stamp(), class_id, student_id, student_id))


def unread_summary(db, session):
    from .learning_update import membership
    result = {'total': 0, 'assignments': 0, 'fees': 0, 'classes': {}}
    if membership(db, session) != 'SVip':
        return result
    for row in db.execute(
            'SELECT n.class_id,n.section,count(*) count FROM class_notices n '
            'JOIN online_classes c ON c.id=n.class_id WHERE n.student_id=? AND n.read_at IS NULL '
            "AND c.status='active' AND EXISTS (SELECT 1 FROM class_enrollments e "
            'WHERE e.class_id=n.class_id AND e.student_id=n.student_id AND e.left_at IS NULL) '
            'GROUP BY n.class_id,n.section', (session['student_id'],)):
        counts = result['classes'].setdefault(str(row['class_id']), {'total': 0, 'assignments': 0, 'fees': 0})
        counts[row['section']] = row['count']
        counts['total'] += row['count']
        result[row['section']] += row['count']
        result['total'] += row['count']
    return result


def notice_snapshot(db, session, class_id):
    unread, through = {'total': 0, 'assignments': 0, 'fees': 0}, {'assignments': 0, 'fees': 0}
    for row in db.execute('SELECT section,max(id) last_id,sum(read_at IS NULL) unread FROM class_notices '
                          'WHERE student_id=? AND class_id=? GROUP BY section', (session['student_id'], class_id)):
        through[row['section']] = row['last_id']
        unread[row['section']] = row['unread']
        unread['total'] += row['unread']
    return {'unread': unread, 'readThrough': through}


def mark_read(db, session, class_id, body):
    from .learning_update import enrolled
    enrolled(db, session, class_id)
    section, through = body.get('section'), body.get('through')
    if section not in ('assignments', 'fees') or type(through) is not int or through < 0:
        raise APIError('Mục thông báo hoặc mốc đã đọc không hợp lệ.')
    # The server snapshot bounds this acknowledgement so a stale/open tab cannot
    # consume future notices, including notices created in the next transaction.
    last = notice_snapshot(db, session, class_id)['readThrough'][section]
    if through > last:
        raise APIError('Mốc thông báo cần thuộc lớp đang mở.')
    db.execute('UPDATE class_notices SET read_at=? WHERE student_id=? AND class_id=? '
               'AND section=? AND id<=? AND read_at IS NULL',
               (stamp(), session['student_id'], class_id, section, through))
    return {'classroomUnread': unread_summary(db, session), **notice_snapshot(db, session, class_id)}


def submit_file(db, session, class_id, assignment_id, body):
    from .learning_update import enrolled
    enrolled(db, session, class_id)
    assignment = db.execute('SELECT a.*,s.class_id FROM class_assignments a '
                            'JOIN class_sessions s ON s.id=a.session_id WHERE a.id=? AND s.class_id=?',
                            (assignment_id, class_id)).fetchone()
    if not assignment:
        raise APIError('Bài tập không thuộc lớp này.', 404)
    filename = text_field(body, 'filename', 180)
    if filename in ('.', '..') or re.search(r'[/\\\x00-\x1f\x7f]', filename):
        raise APIError('Tên tệp bài nộp không hợp lệ.')
    mime = body.get('mimeType')
    extensions = {'image/png': ('.png',), 'image/jpeg': ('.jpg', '.jpeg'),
                  'image/webp': ('.webp',), 'application/pdf': ('.pdf',)}
    if mime not in extensions or not filename.lower().endswith(extensions[mime]):
        raise APIError('Chọn ảnh JPG, PNG, WebP hoặc PDF đúng định dạng.')
    encoded = body.get('data')
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE_SIZE + 2) // 3):
        raise APIError('Bài nộp tối đa 10 MB.', 413)
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise APIError('Dữ liệu tệp bài nộp không hợp lệ.')
    if not content or len(content) > MAX_FILE_SIZE:
        raise APIError('Bài nộp cần có nội dung và tối đa 10 MB.', 413)
    valid = {'image/png': content.startswith(b'\x89PNG\r\n\x1a\n'),
             'image/jpeg': content.startswith(b'\xff\xd8\xff'),
             'image/webp': content.startswith(b'RIFF') and content[8:12] == b'WEBP',
             'application/pdf': content.startswith(b'%PDF-')}
    if not valid[mime]:
        raise APIError('Nội dung tệp không khớp định dạng đã chọn.')
    digest = hashlib.sha256(content).hexdigest()
    latest = db.execute('SELECT * FROM class_submissions WHERE assignment_id=? AND student_id=? '
                        'ORDER BY id DESC LIMIT 1', (assignment_id, session['student_id'])).fetchone()
    if latest and latest['digest'] == digest and latest['filename'] == filename:
        return {'submission': submission_metadata(latest)}
    def write():
        identity = db.execute('INSERT INTO class_submissions(assignment_id,student_id,filename,mime_type,size,content,digest,submitted_at) '
                              'VALUES (?,?,?,?,?,?,?,?)',
                              (assignment_id, session['student_id'], filename, mime, len(content), b'', digest, stamp())).lastrowid
        for position, offset in enumerate(range(0, len(content), FILE_CHUNK_SIZE)):
            db.execute('INSERT INTO class_submission_chunks(submission_id,position,content) VALUES (?,?,?)',
                       (identity, position, content[offset:offset + FILE_CHUNK_SIZE]))
        db.execute('UPDATE class_sessions SET revision=revision+1 WHERE id=?', (assignment['session_id'],))
        return identity

    identity = _atomic_submission(db, write)
    row = db.execute('SELECT * FROM class_submissions WHERE id=?', (identity,)).fetchone()
    return {'submission': submission_metadata(row)}


def file_payload(db, identity, session=None, user=None):
    row = db.execute('SELECT x.id,x.student_id,x.filename,x.mime_type,x.size,x.digest,s.class_id FROM class_submissions x '
                     'JOIN class_assignments a ON a.id=x.assignment_id '
                     'JOIN class_sessions s ON s.id=a.session_id WHERE x.id=?', (identity,)).fetchone()
    if not row:
        raise APIError('Không tìm thấy bài nộp.', 404)
    if user is not None:
        from .staff_api import classroom
        classroom(db, user, row['class_id'])
    else:
        from .learning_update import enrolled
        if session is None or row['student_id'] != session['student_id']:
            raise APIError('Bài nộp không thuộc tài khoản của em.', 403)
        enrolled(db, session, row['class_id'])
    # Authorization precedes reading either inline bytes or private chunks.
    inline = db.execute('SELECT content FROM class_submissions WHERE id=?', (identity,)).fetchone()['content']
    if inline:
        content = bytes(inline)
    else:
        if not 0 < row['size'] <= MAX_FILE_SIZE:
            raise APIError('Dữ liệu bài nộp chưa đầy đủ. Vui lòng liên hệ giáo viên.', 503)
        parts = []
        expected = (row['size'] + FILE_CHUNK_SIZE - 1) // FILE_CHUNK_SIZE
        for position, chunk in enumerate(db.execute(
                'SELECT position,content FROM class_submission_chunks WHERE submission_id=? ORDER BY position', (identity,))):
            if (position >= expected or chunk['position'] != position or
                    not isinstance(chunk['content'], (bytes, bytearray, memoryview))):
                raise APIError('Dữ liệu bài nộp chưa đầy đủ. Vui lòng liên hệ giáo viên.', 503)
            part = bytes(chunk['content'])
            expected_size = min(FILE_CHUNK_SIZE, row['size'] - position * FILE_CHUNK_SIZE)
            if len(part) != expected_size:
                raise APIError('Dữ liệu bài nộp chưa đầy đủ. Vui lòng liên hệ giáo viên.', 503)
            parts.append(part)
        if len(parts) != expected:
            raise APIError('Dữ liệu bài nộp chưa đầy đủ. Vui lòng liên hệ giáo viên.', 503)
        content = b''.join(parts)
    if len(content) != row['size'] or hashlib.sha256(content).hexdigest() != row['digest']:
        raise APIError('Dữ liệu bài nộp chưa đầy đủ. Vui lòng liên hệ giáo viên.', 503)
    return {'_binary': content, 'contentType': row['mime_type'],
            'disposition': "attachment; filename=homework" + ('.pdf' if row['mime_type'] == 'application/pdf' else '.image') +
                           "; filename*=UTF-8''" + quote(row['filename'], safe='')}
