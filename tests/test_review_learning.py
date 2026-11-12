"""Regression coverage for the learning-flow findings in the project review."""
import secrets
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena
from backend.database import initialize
from backend import platform_api, staff_api
from test_platform_api import Client
from test_staff_api import StaffClient


class ReviewLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='review-learning-', dir=work)
        cls.path = Path(cls.directory.name) / 'learning.sqlite3'
        initialize(cls.path)
        platform_api.seed_catalog(cls.path)
        cls.password = secrets.token_urlsafe(20)
        staff_api.create_first_admin(cls.path, 'review-admin', 'Quản trị thử', cls.password)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=False, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def student(self):
        client = Client(self.server)
        login, password = 'review-' + secrets.token_hex(8), secrets.token_urlsafe(20)
        state = client.call('auth/register', {'login': login, 'password': password,
                            'name': 'Học sinh thử', 'birthYear': platform_api.academic()[0] - 10})
        return client, state, login, password

    def admin(self):
        client = StaffClient(self.server)
        client.call('login', {'login': 'review-admin', 'password': self.password})
        return client

    def test_public_article_progress_is_stable_owned_and_idempotent(self):
        client, state, login, password = self.student()
        keys = {'public-decimal', 'public-percent'}
        self.assertTrue(keys <= {lesson['id'] for lesson in state['lessons']})
        for key in keys:
            saved = client.call('lessons/' + key + '/complete', {})
            first = saved['state']['completed'][key]
            self.assertEqual(client.call('lessons/' + key + '/complete', {})['state']['completed'][key], first)
        self.assertNotIn('g5-percent', saved['state']['completed'])
        resumed = Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertTrue(keys <= resumed['state']['completed'].keys())
        stranger, _, _, _ = self.student()
        self.assertTrue(keys.isdisjoint(stranger.call('session')['state']['completed']))
        with platform_api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM lesson_progress p JOIN lessons l ON l.id=p.lesson_id '
                                       'JOIN students s ON s.id=p.student_id WHERE s.account_id=? AND l.client_key IN (?,?)',
                                       (state['account']['id'], 'public-decimal', 'public-percent')).fetchone()[0], 2)

    def test_admin_lesson_example_and_video_reach_student_with_safe_schema(self):
        admin = self.admin()
        student, _, _, _ = self.student()
        with platform_api.connect(self.path) as db:
            topic = db.execute("SELECT id FROM topics WHERE grade_id=5 AND client_key='decimal'").fetchone()[0]
        body = {'grade': 5, 'topicId': topic, 'title': 'Bài đọc thử của quản trị',
                'intro': 'Nội dung thử cho kiểm tra luồng học.', 'week': 1,
                'videoUrl': '', 'kind': 'topic', 'status': 'published'}
        identity = admin.call('lessons', body)['id']
        with platform_api.connect(self.path) as db:
            row = db.execute('SELECT * FROM lessons WHERE id=?', (identity,)).fetchone()
            key, revision = row['client_key'], row['revision']
        lesson = next(item for item in student.call('session')['lessons'] if item['id'] == key)
        self.assertIsNone(lesson['example'])
        self.assertEqual(lesson['videoRef'], '')
        edit = {**body, 'id': identity, 'revision': revision,
                'exampleText': 'So sánh 2,45 và 2,5.',
                'exampleSteps': 'Viết 2,5 = 2,50.\nSo sánh được 2,45 < 2,50.',
                'videoUrl': 'https://www.youtube.com/watch?v=learning-review'}
        admin.call('lessons', edit)
        lesson = next(item for item in student.call('session')['lessons'] if item['id'] == key)
        self.assertEqual(lesson['example'], {'text': edit['exampleText'],
                         'steps': ['Viết 2,5 = 2,50.', 'So sánh được 2,45 < 2,50.']})
        self.assertEqual(lesson['videoRef'], edit['videoUrl'])
        self.assertEqual(lesson['video_ref'], edit['videoUrl'])
        row = next(row for row in admin.call('content?kind=lessons&grade=5')['rows'] if row['id'] == identity)
        self.assertEqual(row['exampleText'], edit['exampleText'])
        self.assertEqual(row['exampleSteps'], edit['exampleSteps'])
        for bad in ({'exampleSteps': [12]}, {'videoUrl': 'javascript:alert(1)'},
                    {'videoUrl': '//another.example/video'}, {'videoUrl': 'https://user:pass@example.com/video'}):
            with self.subTest(bad=bad):
                with self.assertRaises(platform_api.APIError):
                    admin.call('lessons', {**edit, 'revision': row['revision'], **bad})
        with platform_api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT revision FROM lessons WHERE id=?', (identity,)).fetchone()[0], row['revision'])
        student.call('lessons/' + key + '/complete', {})

    def test_activity_uses_vietnam_midnight_without_rewriting_intervals(self):
        client, state, _, _ = self.student()
        intervals = [('2026-11-11T17:05:00Z', '2026-11-11T17:15:00Z', None),
                     ('2026-11-12T16:55:00Z', '2026-11-12T17:05:00Z', None),
                     ('2026-11-13T16:59:00Z', '2026-11-13T17:15:00Z', '2026-11-13T17:01:00Z')]
        with platform_api.connect(self.path, True) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (state['account']['id'],)).fetchone()[0]
            db.executemany('INSERT INTO online_intervals(student_id,started_at,last_seen_at,ended_at) VALUES (?,?,?,?)',
                           [(sid, *interval) for interval in intervals])
        self.assertEqual(client.call('session')['state']['activity'],
                         {'2026-11-12': 900, '2026-11-13': 360, '2026-11-14': 60})
        with platform_api.connect(self.path) as db:
            self.assertEqual([tuple(row) for row in db.execute('SELECT started_at,last_seen_at,ended_at '
                             'FROM online_intervals WHERE student_id=? ORDER BY id', (sid,))], intervals)

    def test_regular_gets_do_not_wait_for_an_unrelated_writer(self):
        student, _, _, _ = self.student()
        admin = self.admin()
        anonymous = Client(self.server)
        staff_anonymous = StaffClient(self.server)
        calls = [(anonymous, 'session'), (student, 'session'), (student, 'leaderboard'),
                 (staff_anonymous, 'session'), (admin, 'content?kind=lessons&grade=5')]
        executor = ThreadPoolExecutor(max_workers=1)
        writer = sqlite3.connect(self.path)
        try:
            writer.execute('BEGIN IMMEDIATE')
            for client, route in calls:
                with self.subTest(route=route, client=type(client).__name__):
                    result = executor.submit(client.call, route).result(timeout=2)
                    self.assertIsInstance(result, dict)
        finally:
            writer.rollback()
            writer.close()
            executor.shutdown(wait=True)

    def assert_writer_available(self):
        with closing(sqlite3.connect(self.path, timeout=0)) as db:
            db.execute('BEGIN IMMEDIATE')
            db.rollback()

    def test_hashing_and_verification_run_without_a_reserved_writer(self):
        original_hash, original_verify = platform_api.password_hash, platform_api.verify_password
        probes = []

        def hash_unlocked(password):
            self.assert_writer_available()
            probes.append('hash')
            return original_hash(password)

        def verify_unlocked(password, credential):
            self.assert_writer_available()
            probes.append('verify')
            return original_verify(password, credential)

        with patch.object(platform_api, 'password_hash', hash_unlocked), patch.object(platform_api, 'verify_password', verify_unlocked):
            _, _, login, password = self.student()
            Client(self.server).call('auth/login', {'login': login, 'password': password})
        admin = self.admin()
        with patch.object(staff_api, 'password_hash', hash_unlocked), patch.object(staff_api, 'verify_password', verify_unlocked):
            admin.call('users', {'login': 'teacher-' + secrets.token_hex(8), 'fullName': 'Giáo viên thử',
                               'role': 'teacher', 'status': 'active', 'password': secrets.token_urlsafe(20)})
        self.assertGreaterEqual(probes.count('hash'), 2)
        self.assertGreaterEqual(probes.count('verify'), 1)

    def test_login_rechecks_status_and_password_after_verification(self):
        original = platform_api.verify_password
        for changed in ('status', 'password', 'login'):
            _, state, login, password = self.student()
            replacement = platform_api.password_hash(secrets.token_urlsafe(20))

            def change_after_verify(cleartext, encoded):
                result = original(cleartext, encoded)
                if result:
                    with platform_api.connect(self.path, True) as db:
                        if changed == 'status':
                            db.execute("UPDATE accounts SET status='suspended',revision=revision+1 WHERE id=?", (state['account']['id'],))
                        elif changed == 'password':
                            db.execute('UPDATE accounts SET password_hash=?,revision=revision+1 WHERE id=?',
                                       (replacement, state['account']['id']))
                        else:
                            db.execute('UPDATE accounts SET login_identifier=?,revision=revision+1 WHERE id=?',
                                       ('renamed-' + secrets.token_hex(8), state['account']['id']))
                return result

            with self.subTest(changed=changed), patch.object(platform_api, 'verify_password', change_after_verify):
                with self.assertRaises(platform_api.APIError) as caught:
                    Client(self.server).call('auth/login', {'login': login, 'password': password})
                self.assertEqual(caught.exception.status, 401)

    def test_staff_password_hashing_is_unlocked_and_rechecks_current_revision(self):
        admin = self.admin()
        login, old_password = 'password-' + secrets.token_hex(8), secrets.token_urlsafe(20)
        users = admin.call('users', {'login': login, 'fullName': 'Giáo viên thử', 'role': 'teacher',
                                    'status': 'active', 'password': old_password})['users']
        identity = next(user['id'] for user in users if user['login'] == login)
        teacher = StaffClient(self.server)
        teacher.call('login', {'login': login, 'password': old_password})
        original_hash, original_verify = staff_api.password_hash, staff_api.verify_password
        new_password = secrets.token_urlsafe(20)

        def hash_unlocked(password):
            self.assert_writer_available()
            return original_hash(password)

        def verify_unlocked(password, credential):
            self.assert_writer_available()
            return original_verify(password, credential)

        with patch.object(staff_api, 'password_hash', hash_unlocked), patch.object(staff_api, 'verify_password', verify_unlocked):
            teacher.call('password', {'currentPassword': old_password, 'newPassword': new_password})
        StaffClient(self.server).call('login', {'login': login, 'password': new_password})

        def change_revision(password, credential):
            result = original_verify(password, credential)
            with platform_api.connect(self.path, True) as db:
                db.execute('UPDATE staff_users SET revision=revision+1 WHERE id=?', (identity,))
            return result

        with patch.object(staff_api, 'verify_password', change_revision):
            with self.assertRaises(platform_api.APIError) as caught:
                teacher.call('password', {'currentPassword': new_password, 'newPassword': secrets.token_urlsafe(20)})
            self.assertEqual(caught.exception.status, 409)
        StaffClient(self.server).call('login', {'login': login, 'password': new_password})

    def test_admin_revision_is_checked_after_preparing_password(self):
        admin = self.admin()
        _, state, _, _ = self.student()
        identity = state['account']['id']
        with platform_api.connect(self.path) as db:
            old = db.execute('SELECT revision,password_hash FROM accounts WHERE id=?', (identity,)).fetchone()
        original = staff_api.password_hash

        def change_revision(password):
            credential = original(password)
            with platform_api.connect(self.path, True) as db:
                db.execute('UPDATE accounts SET revision=revision+1 WHERE id=?', (identity,))
            return credential

        with patch.object(staff_api, 'password_hash', change_revision):
            with self.assertRaises(platform_api.APIError) as caught:
                admin.call('accounts/' + str(identity), {'revision': old['revision'], 'password': secrets.token_urlsafe(20)})
            self.assertEqual(caught.exception.status, 409)
        with platform_api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT password_hash FROM accounts WHERE id=?', (identity,)).fetchone()[0], old['password_hash'])


if __name__ == '__main__':
    unittest.main()
