import base64
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog
from backend.staff_api import create_first_admin
import test_staff_api as support


class ZoomClassroomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path(__file__).resolve().parents[1] / 'work'
        scratch.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='zoom-tests-', dir=scratch)
        cls.path = Path(cls.directory.name) / 'zoom.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.password = secrets.token_urlsafe(20)
        create_first_admin(cls.path, 'admin', 'Quản trị thử', cls.password)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=False, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.admin = support.StaffClient(self.server)
        self.admin.call('login', {'login': 'admin', 'password': self.password})
        self.teacher_client, teacher = support.StaffTests.teacher(self)
        self.group = support.StaffTests.classroom(self, teacher)
        self.student_client, self.state, self.sid = support.StaffTests.student(self)
        self.admin.call(f'classes/{self.group["id"]}/enroll', {'action': 'enroll', 'studentId': self.sid})
        self.detail = self.teacher_client.call(f'classes/{self.group["id"]}/sessions', {
            'title': 'Buổi học Zoom', 'startsAt': '2026-11-12T19:00:00+07:00',
            'videoUrl': '', 'comment': 'Nhận xét chung'})
        self.session_id = self.detail['sessions'][0]['id']

    def assignment(self, title='Bài tập mới'):
        self.detail = self.teacher_client.call(f'sessions/{self.session_id}/assignments', {
            'title': title, 'kind': 'Bài tập về nhà', 'documentUrl': ''})
        return self.detail['sessions'][0]['assignments'][-1]

    def records(self, **values):
        revision = self.detail['sessions'][0]['revision']
        self.detail = self.teacher_client.call(f'sessions/{self.session_id}/records', {'revision': revision, **values})
        return self.detail['sessions'][0]

    def counts(self, client=None):
        return (client or self.student_client).call('classes/unread')['classroomUnread']

    def upload(self, assignment, **values):
        data = {'filename': 'bai-lam.pdf', 'mimeType': 'application/pdf',
                'data': base64.b64encode(b'%PDF-1.4\nZoom homework fixture\n%%EOF').decode()}
        data.update(values)
        return self.student_client.call(f'classes/{self.group["id"]}/assignments/{assignment["id"]}/submissions', data)['submission']

    def test_attendance_and_grading_comments_are_independent_and_visible_only_to_owner(self):
        assignment = self.assignment()
        record = self.records(attendance=[{'studentId': self.sid, 'status': None, 'comment': 'Cần rèn đọc đề'}])
        self.assertEqual(record['attendance'][0]['comment'], 'Cần rèn đọc đề')
        record = self.records(scores=[{'studentId': self.sid, 'assignmentId': assignment['id'], 'score': None, 'comment': 'Trình bày rõ'}])
        self.assertEqual(record['attendance'][0]['comment'], 'Cần rèn đọc đề')
        self.assertIsNone(record['scores'][0]['score'])
        record = self.records(attendance=[{'studentId': self.sid, 'status': 'charged'}])
        self.assertEqual(record['attendance'][0]['comment'], 'Cần rèn đọc đề')
        self.assertEqual(record['scores'][0]['comment'], 'Trình bày rõ')
        record = self.records(scores=[{'studentId': self.sid, 'assignmentId': assignment['id'], 'score': 8.5}])
        self.assertEqual(record['scores'][0]['comment'], 'Trình bày rõ')
        view = self.student_client.call(f'classes/{self.group["id"]}')['sessions'][0]
        self.assertEqual(view['teacher_comment'], 'Nhận xét chung')
        self.assertEqual(view['personal_comment'], 'Cần rèn đọc đề')
        self.assertEqual(view['attendance_status'], 'charged')
        self.assertEqual(view['assignments'][0]['comment'], 'Trình bày rõ')
        self.assertEqual(view['assignments'][0]['score'], 8.5)
        other, _, other_sid = support.StaffTests.student(self)
        self.admin.call(f'classes/{self.group["id"]}/enroll', {'action': 'enroll', 'studentId': other_sid})
        other_view = other.call(f'classes/{self.group["id"]}')['sessions'][0]
        self.assertEqual(other_view['personal_comment'], '')
        self.assertEqual(other_view['assignments'][0]['comment'], '')

    def test_bad_records_rollback_and_revisions_prevent_stale_overwrite(self):
        assignment = self.assignment()
        revision = self.detail['sessions'][0]['revision']
        with self.assertRaises(APIError):
            self.teacher_client.call(f'sessions/{self.session_id}/records', {'revision': revision,
                'attendance': [{'studentId': self.sid, 'status': 'charged', 'comment': 'Must roll back'}],
                'scores': [{'studentId': self.sid, 'assignmentId': assignment['id'], 'score': 11}]})
        data = self.teacher_client.call(f'classes/{self.group["id"]}')['sessions'][0]
        self.assertEqual(data['attendance'], [])
        self.assertEqual(data['revision'], revision)
        self.records(scores=[{'studentId': self.sid, 'assignmentId': assignment['id'], 'score': 0, 'comment': ''}])
        with self.assertRaises(APIError) as conflict:
            self.teacher_client.call(f'sessions/{self.session_id}/records', {'revision': revision, 'attendance': []})
        self.assertEqual(conflict.exception.status, 409)
        with self.assertRaises(APIError):
            self.records(attendance=[{'studentId': self.sid, 'status': None, 'comment': 'x' * 10001}])

    def test_unread_assignments_fees_are_targeted_persistent_and_edits_do_not_duplicate(self):
        other, _, sid = support.StaffTests.student(self)
        self.admin.call(f'classes/{self.group["id"]}/enroll', {'action': 'enroll', 'studentId': sid})
        self.assertEqual(self.counts()['total'], 0)
        assignment = self.assignment()
        self.assertEqual(self.counts()['assignments'], 1)
        self.assertEqual(self.counts(other)['assignments'], 1)
        self.detail = self.teacher_client.call(f'sessions/{self.session_id}/assignments', {
            'id': assignment['id'], 'revision': assignment['revision'], 'title': 'Tên đã sửa',
            'kind': assignment['kind'], 'documentUrl': ''})
        self.assertEqual(self.counts()['assignments'], 1)
        detail = self.admin.call(f'classes/{self.group["id"]}')
        detail = self.admin.call(f'classes/{self.group["id"]}/fees', {'revision': detail['class']['revision'],
            'studentId': self.sid, 'month': '2026-11', 'amount': 100000})
        self.assertEqual(self.counts()['fees'], 1)
        self.assertEqual(self.counts(other)['fees'], 0)
        self.admin.call(f'classes/{self.group["id"]}/fees', {'revision': detail['class']['revision'],
            'studentId': self.sid, 'month': '2026-11', 'amount': 200000})
        self.assertEqual(self.counts()['fees'], 1)
        state = self.student_client.call('state')
        self.assertEqual(state['account']['classroomUnread']['total'], 2)
        self.assertEqual(state['account']['classroomUnread']['classes'][str(self.group['id'])]['total'], 2)
        initialize(self.path)
        self.assertEqual(self.counts()['total'], 2)
        self.admin.call(f'classes/{self.group["id"]}/enroll', {'action': 'leave', 'studentId': self.sid})
        self.assertEqual(self.counts()['total'], 0)
        with self.assertRaises(APIError):
            self.student_client.call(f'classes/{self.group["id"]}/read', {'section': 'fees', 'through': 0})

    def test_read_snapshot_does_not_consume_later_notices_or_other_sections(self):
        self.assignment('Bài đầu')
        detail = self.admin.call(f'classes/{self.group["id"]}')
        self.admin.call(f'classes/{self.group["id"]}/fees', {'revision': detail['class']['revision'],
            'studentId': self.sid, 'month': '2026-11', 'amount': 100000})
        snapshot = self.student_client.call(f'classes/{self.group["id"]}')
        first = snapshot['readThrough']['assignments']
        self.assignment('Bài sau khi mở trang')
        result = self.student_client.call(f'classes/{self.group["id"]}/read', {'section': 'assignments', 'through': first})
        self.assertEqual(result['unread']['assignments'], 1)
        self.assertEqual(result['classroomUnread']['total'], 2)
        self.assertEqual(result['unread']['fees'], 1)
        again = self.student_client.call(f'classes/{self.group["id"]}/read', {'section': 'assignments', 'through': first})
        self.assertEqual(again['classroomUnread']['total'], 2)
        with self.assertRaises(APIError):
            self.student_client.call(f'classes/{self.group["id"]}/read', {'section': 'assignments', 'through': 999999})
        final = self.student_client.call(f'classes/{self.group["id"]}/read', {
            'section': 'assignments', 'through': result['readThrough']['assignments']})
        self.assertEqual(final['classroomUnread']['total'], 1)
        final = self.student_client.call(f'classes/{self.group["id"]}/read', {
            'section': 'fees', 'through': snapshot['readThrough']['fees']})
        self.assertEqual(final['classroomUnread']['total'], 0)

    def test_temporarily_suspended_accounts_keep_new_class_notices(self):
        with connect(self.path, True) as db:
            db.execute("UPDATE accounts SET status='suspended' WHERE id=?", (self.state['account']['id'],))
        self.assignment()
        with connect(self.path, True) as db:
            db.execute("UPDATE accounts SET status='active' WHERE id=?", (self.state['account']['id'],))
        self.assertEqual(self.counts()['assignments'], 1)

    def test_submissions_versions_private_access_and_metadata(self):
        assignment = self.assignment()
        submission = self.upload(assignment)
        repeated = self.upload(assignment)
        self.assertEqual(submission['id'], repeated['id'])
        # Re-upload keeps the previous version and existing teacher feedback.
        self.detail = self.teacher_client.call(f'classes/{self.group["id"]}')
        self.records(scores=[{'studentId': self.sid, 'assignmentId': assignment['id'], 'score': 9, 'comment': 'Tốt'}])
        newer = self.upload(assignment, filename='bai-lam-moi.pdf',
                            data=base64.b64encode(b'%PDF-1.4\nNewer homework\n%%EOF').decode())
        self.assertGreater(newer['id'], submission['id'])
        data = self.teacher_client.call(f'classes/{self.group["id"]}')['sessions'][0]
        self.assertEqual(data['submissions'][0]['id'], newer['id'])
        self.assertEqual(data['scores'][0]['score'], 9)
        self.assertNotIn('content', data['submissions'][0])
        student_view = self.student_client.call(f'classes/{self.group["id"]}')['sessions'][0]['assignments'][0]
        self.assertEqual(student_view['submission']['id'], newer['id'])
        from backend.zoom_classroom import file_payload
        from backend.platform_api import read_session as student_session
        from backend.staff_api import read_session as staff_session
        with connect(self.path) as db:
            payload = file_payload(db, submission['id'], session=student_session(self.student_client, db))
            self.assertTrue(payload['_binary'].startswith(b'%PDF-'))
            self.assertEqual(payload['contentType'], 'application/pdf')
            self.assertIn('attachment;', payload['disposition'])
            self.assertTrue(file_payload(db, submission['id'], user=staff_session(self.teacher_client, db))['_binary'])
        other, _, sid = support.StaffTests.student(self)
        self.admin.call(f'classes/{self.group["id"]}/enroll', {'action': 'enroll', 'studentId': sid})
        with self.assertRaises(APIError) as rejected:
            other.call(f'class-submissions/{submission["id"]}/file')
        self.assertEqual(rejected.exception.status, 403)
        stranger, _ = support.StaffTests.teacher(self)
        with self.assertRaises(APIError) as rejected:
            stranger.call(f'submissions/{submission["id"]}/file')
        self.assertEqual(rejected.exception.status, 403)

    def test_submission_validation_and_class_scope(self):
        assignment = self.assignment()
        for update in ({'filename': '../bad.pdf'}, {'filename': 'bad\n.pdf'}, {'mimeType': 'image/svg+xml'},
                       {'data': 'not base64'}, {'data': base64.b64encode(b'<script>bad</script>').decode()},
                       {'filename': 'wrong.png'}, {'data': ''}):
            with self.subTest(update=list(update)), self.assertRaises(APIError):
                self.upload(assignment, **update)
        with self.assertRaises(APIError) as too_large:
            self.upload(assignment, data='A' * (4 * ((10 * 1024 * 1024 + 2) // 3) + 4))
        self.assertEqual(too_large.exception.status, 413)
        other, _ = support.StaffTests.student(self)[:2]
        with self.assertRaises(APIError):
            other.call(f'classes/{self.group["id"]}/assignments/{assignment["id"]}/submissions', {
                'filename': 'bai.pdf', 'mimeType': 'application/pdf', 'data': base64.b64encode(b'%PDF-1.4').decode()})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM class_submissions WHERE assignment_id=?', (assignment['id'],)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
