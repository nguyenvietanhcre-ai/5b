import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, seed_catalog
from backend.staff_api import create_first_admin, dispatch
from test_platform_api import Client as StudentClient


class StaffClient:
    def __init__(self, server):
        self.server = server
        self.client_address = ('staff-test-' + secrets.token_hex(6), 1234)
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.api_headers = {}
        self.csrf = ''

    def call(self, path, body=None):
        self.path = '/api/staff/' + path
        self.headers['X-CSRF-Token'] = self.csrf
        result, status = dispatch(self, 'GET' if body is None else 'POST', self.path.split('?')[0], body)
        cookie = self.api_headers.pop('Set-Cookie', None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        if result.get('csrf'):
            self.csrf = result['csrf']
        assert status == 200
        return result


class StaffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name) / 'staff.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.password = secrets.token_urlsafe(20)
        create_first_admin(cls.path, 'admin', 'Quản trị thử', cls.password)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=False, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.admin = StaffClient(self.server)
        self.admin.call('login', {'login': 'admin', 'password': self.password})

    def teacher(self):
        login = 'teacher-' + secrets.token_hex(5)
        password = secrets.token_urlsafe(20)
        result = self.admin.call('users', {'login': login, 'fullName': 'Giáo viên thử',
                                          'role': 'teacher', 'status': 'active', 'password': password})
        user = next(row for row in result['users'] if row['login'] == login)
        client = StaffClient(self.server)
        client.call('login', {'login': login, 'password': password})
        return client, user

    def classroom(self, teacher):
        return self.admin.call('classes', {'name': 'Lớp thử', 'grade': 5, 'teacherId': teacher['teacher_id'],
            'status': 'active', 'schedule': 'Lịch thử', 'curriculum': 'Nội dung thử',
            'meetingUrl': 'https://zoom.us/j/123456789'})['class']

    def student(self, invite=''):
        client = StudentClient(self.server)
        login = 'student-' + secrets.token_hex(6)
        state = client.call('auth/register', {'login': login, 'password': secrets.token_urlsafe(20),
             'name': 'Học sinh thử', 'birthYear': academic()[0]-10, 'inviteCode': invite})
        with connect(self.path) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (state['account']['id'],)).fetchone()[0]
        return client, state, sid

    def test_homepage_login_accepts_staff_and_keeps_sessions_separate(self):
        teacher_login = 'homepage-teacher-' + secrets.token_hex(5)
        teacher_password = secrets.token_urlsafe(20)
        self.admin.call('users', {'login': teacher_login, 'fullName': 'Giáo viên đăng nhập từ trang chủ',
                                  'role': 'teacher', 'status': 'active', 'password': teacher_password})
        for login, password, role in [('admin', self.password, 'admin'),
                                       (teacher_login, teacher_password, 'teacher')]:
            client = StudentClient(self.server)
            result = client.call('auth/login', {'login': login, 'password': password})
            self.assertEqual(result['principal'], 'staff')
            self.assertEqual(result['user']['role'], role)
            self.assertTrue(client.headers['Cookie'].startswith('5bmath_staff='))
            self.assertFalse(client.call('session')['authenticated'])
            staff = StaffClient(self.server)
            staff.headers['Cookie'] = client.headers['Cookie']
            self.assertEqual(staff.call('session')['user']['role'], role)
            with self.assertRaises(APIError) as invalid:
                StudentClient(self.server).call('auth/login', {'login': login, 'password': 'incorrect'})
            self.assertEqual(invalid.exception.status, 401)
        with connect(self.path, True) as db:
            db.execute("UPDATE staff_users SET status='disabled' WHERE login=?", (teacher_login,))
        with self.assertRaises(APIError) as disabled:
            StudentClient(self.server).call('auth/login', {'login': teacher_login, 'password': teacher_password})
        self.assertEqual(disabled.exception.status, 401)

    def test_credentials_roles_csrf_and_teacher_scope(self):
        teacher, user = self.teacher()
        other, other_user = self.teacher()
        mine, theirs = self.classroom(user), self.classroom(other_user)
        self.assertEqual(teacher.call('classes')['classes'][0]['id'], mine['id'])
        with self.assertRaises(APIError) as caught:
            teacher.call('classes/' + str(theirs['id']))
        self.assertEqual(caught.exception.status, 403)
        for path in ('users', 'accounts', 'settings', 'payments', 'audit'):
            with self.subTest(path=path), self.assertRaises(APIError):
                teacher.call(path)
        anonymous = StaffClient(self.server)
        self.assertFalse(anonymous.call('session')['authenticated'])
        with self.assertRaises(APIError):
            anonymous.call('overview')
        teacher.csrf = 'bad'
        with self.assertRaises(APIError):
            teacher.call('classes/' + str(mine['id']) + '/sessions', {})
        self.assertNotIn('password_hash', json.dumps(self.admin.call('users')))

    def test_records_rollback_conflict_and_student_visibility(self):
        teacher, user = self.teacher()
        group = self.classroom(user)
        student, _, sid = self.student()
        self.admin.call(f'classes/{group["id"]}/enroll', {'action': 'enroll', 'studentId': sid})
        data = teacher.call(f'classes/{group["id"]}/sessions', {'title': 'Buổi thử', 'startsAt': '2026-11-11T19:00:00+07:00',
                'videoUrl': 'https://example.com/recording.mp4', 'comment': 'Nhận xét buổi học'})
        session = data['sessions'][0]
        data = teacher.call(f'sessions/{session["id"]}/assignments', {'title': 'Bài thử', 'kind': 'Bài tập về nhà', 'documentUrl': ''})
        session, assignment = data['sessions'][0], data['sessions'][0]['assignments'][0]
        body = {'revision': session['revision'], 'attendance': [{'studentId': sid, 'status': 'charged'}],
                'scores': [{'studentId': sid, 'assignmentId': assignment['id'], 'score': 8.5}]}
        data = teacher.call(f'sessions/{session["id"]}/records', body)
        self.assertEqual(data['sessions'][0]['scores'][0]['score'], 8.5)
        with self.assertRaises(APIError) as caught:
            teacher.call(f'sessions/{session["id"]}/records', body)
        self.assertEqual(caught.exception.status, 409)
        bad = {**body, 'revision': data['sessions'][0]['revision'],
               'scores': [{'studentId': sid, 'assignmentId': assignment['id'], 'score': 99}]}
        with self.assertRaises(APIError):
            teacher.call(f'sessions/{session["id"]}/records', bad)
        student_view = student.call(f'classes/{group["id"]}')
        self.assertEqual(student_view['sessions'][0]['assignments'][0]['score'], 8.5)
        self.assertEqual(student_view['sessions'][0]['teacher_comment'], 'Nhận xét buổi học')
        self.admin.call(f'classes/{group["id"]}/enroll', {'action': 'leave', 'studentId': sid})
        with self.assertRaises(APIError):
            student.call(f'classes/{group["id"]}')

    def test_legacy_student_nicknames_masked_in_staff_views(self):
        teacher, user = self.teacher()
        group = self.classroom(user)
        student, state, sid = self.student()
        order = student.call('payments', {})['order']
        self.admin.call(f'classes/{group["id"]}/enroll', {'action': 'enroll', 'studentId': sid})
        with connect(self.path, True) as db:
            db.execute('UPDATE students SET full_name=? WHERE id=?', ('0912345678', sid))
            db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,\'2026-11\',100000)', (group['id'], sid))
            login = db.execute('SELECT login_identifier FROM accounts WHERE id=?', (state['account']['id'],)).fetchone()[0]
        detail = teacher.call(f'classes/{group["id"]}')
        self.assertEqual(next(row for row in detail['students'] if row['id']==sid)['full_name'], 'Bạn học')
        self.assertEqual(next(row for row in detail['fees'] if row['student_id']==sid)['full_name'], 'Bạn học')
        self.assertEqual(detail['class']['teacher'], user['full_name'])
        account = next(row for row in self.admin.call('accounts?q='+login)['rows'] if row['id']==state['account']['id'])
        self.assertEqual(account['full_name'], 'Bạn học')
        self.assertEqual(account['login_identifier'], login)
        payment = next(row for row in self.admin.call('payments?q='+order['reference'])['rows'] if row['id']==order['id'])
        self.assertEqual(payment['full_name'], 'Bạn học')
        self.assertEqual(payment['login_identifier'], login)
        self.assertEqual(self.admin.call('session')['user']['full_name'], 'Quản trị thử')
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT full_name FROM students WHERE id=?', (sid,)).fetchone()[0], '0912345678')

    def test_lesson_publish_and_question_snapshot_are_preserved(self):
        student, _, _ = self.student()
        topic = self.admin.call('content?kind=topics&grade=5')['rows'][0]
        body = {'grade': 5, 'topicId': topic['id'], 'title': 'Bài quản trị thử',
                'intro': 'Nội dung tự biên soạn để thử.', 'kind': 'weekly', 'week': 1,
                'videoUrl': '', 'status': 'draft'}
        saved = self.admin.call('lessons', body)
        before = student.call('session')['lessons']
        self.assertNotIn(body['title'], [row['title'] for row in before])
        row = next(row for row in self.admin.call('content?kind=lessons&q=Bài quản trị thử')['rows'] if row['id'] == saved['id'])
        self.admin.call('lessons', {**body, 'id': row['id'], 'revision': row['revision'], 'status': 'published'})
        self.assertIn(body['title'], [row['title'] for row in student.call('session')['lessons']])
        exam = student.call('exams', {'requestKey': secrets.token_hex(12), 'count': 3, 'topic': 'decimal'})['exam']
        with connect(self.path) as db:
            q = db.execute('SELECT q.question_code,v.id version_id FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id '
                           'JOIN questions q ON q.id=v.question_id WHERE i.exam_id=? LIMIT 1', (exam['id'],)).fetchone()
        rows = self.admin.call('content?kind=questions&q=' + q['question_code'])['rows']
        self.assertIn(q['question_code'], [row['question_code'] for row in rows])
        row = next(row for row in rows if row['question_code'] == q['question_code'])
        with connect(self.path, True) as db:
            asset = db.execute('SELECT id FROM media_assets LIMIT 1').fetchone()[0]
            db.execute('INSERT OR IGNORE INTO question_assets VALUES (?,?)', (q['version_id'], asset))
        self.admin.call('questions', {'id': row['id'], 'revision': row['revision'], 'grade': row['grade_id'], 'topicId': row['topic_id'],
             'prompt': 'Nội dung đã sửa', 'answer': row['answer'], 'options': row['options'], 'steps': row['steps'],
             'thinking': row['thinking'], 'difficulty': row['difficulty'], 'week': row['curriculum_week'], 'status': 'published'})
        self.assertEqual(student.call('exams/' + exam['id'])['exam']['questions'][0]['text'], exam['questions'][0]['text'])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT status FROM question_versions WHERE id=?', (q['version_id'],)).fetchone()[0], 'retired')
            self.assertTrue(db.execute('SELECT 1 FROM question_assets a JOIN question_versions v ON v.id=a.question_version_id '
                                       'WHERE v.question_id=? AND v.revision=? AND a.asset_id=?',
                                       (row['id'], row['revision']+1, asset)).fetchone())

    def test_settings_affect_backend_limits_and_feature_gates(self):
        settings = self.admin.call('settings')['settings']
        try:
            changed = {**settings, 'registration_open': False, 'practice_open': False,
                       'free_limits': {**settings['free_limits'], 'bot': 0}}
            self.admin.call('settings', changed)
            with self.assertRaises(APIError):
                self.student()
            # A trusted test account created before the switch can still log in.
            changed = self.admin.call('settings')['settings']
            changed['registration_open'] = True
            self.admin.call('settings', changed)
            student, _, _ = self.student()
            with self.assertRaises(APIError) as caught:
                student.call('exams', {'requestKey': secrets.token_hex(12), 'count': 3, 'topic': 'decimal'})
            self.assertEqual(caught.exception.status, 403)
            with self.assertRaises(APIError) as caught:
                student.call('bot/start', {'requestKey': secrets.token_hex(12)})
            self.assertEqual(caught.exception.status, 429)
        finally:
            current = self.admin.call('settings')['settings']
            self.admin.call('settings', {**settings, 'revision': current['revision']})

    def test_confirm_payment_is_idempotent_and_applies_referral_once(self):
        inviter, inviter_state, _ = self.student()
        student, state, _ = self.student(inviter_state['state']['inviteCode'])
        order = student.call('payments', {})['order']
        with self.assertRaises(APIError):
            self.admin.call(f'payments/{order["id"]}/confirm', {'reference': order['reference'], 'amount': 1})
        body = {'reference': order['reference'], 'amount': order['amount']}
        self.admin.call(f'payments/{order["id"]}/confirm', body)
        expiry = student.call('session')['account']['vipExpiresAt']
        self.admin.call(f'payments/{order["id"]}/confirm', body)
        self.assertEqual(student.call('session')['account']['vipExpiresAt'], expiry)
        self.assertEqual(len(inviter.call('session')['account']['notifications']), 1)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (state['account']['id'],)).fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_last_admin_cannot_be_locked_and_bootstrap_cannot_repeat(self):
        me = self.admin.call('session')['user']
        with self.assertRaises(APIError):
            self.admin.call('users', {'id': me['id'], 'revision': me['revision'], 'login': me['login'], 'fullName': me['full_name'],
                                     'role': 'admin', 'status': 'disabled', 'password': ''})
        with self.assertRaises(APIError):
            create_first_admin(self.path, 'other-admin', 'Khác', secrets.token_urlsafe(20))
