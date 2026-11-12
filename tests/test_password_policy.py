"""Password length boundaries and the account paths sharing that policy.

Passwords below are deterministic synthetic fixtures, never real credentials.
"""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, password_hash, seed_catalog, verify_password
from backend.staff_api import create_first_admin
from test_platform_api import Client as StudentClient
from test_staff_api import StaffClient


def synthetic_password(length):
    return 'T' + 'a' * (length - 2) + '9'


class PasswordPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='password-policy-tests-', dir=work)
        cls.template = Path(cls.directory.name) / 'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)
        cls.admin_password = synthetic_password(10)
        create_first_admin(cls.template, 'admin', 'Quản trị thử', cls.admin_password)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path = Path(self.directory.name) / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.template)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        self.admin = StaffClient(self.server)
        self.admin.call('login', {'login': 'admin', 'password': self.admin_password})

    def student_body(self, login, length):
        return {'login': login, 'name': 'Mầm xanh', 'birthYear': academic()[0]-10,
                'password': synthetic_password(length), 'status': 'active'}

    def test_shared_hash_accepts_six_through_128_characters(self):
        for length in (6, 7, 9, 10, 128):
            with self.subTest(length=length):
                password = synthetic_password(length)
                encoded = password_hash(password)
                self.assertTrue(encoded.startswith('pbkdf2_sha256$600000$'))
                self.assertNotIn(password, encoded)
                self.assertTrue(verify_password(password, encoded))
                self.assertFalse(verify_password(password+'x', encoded))
        for length in (0, 5, 129):
            with self.subTest(rejected_length=length), self.assertRaises(APIError):
                password_hash('a'*length)
        for value in (None, 123456, [], {}):
            with self.subTest(rejected_type=type(value).__name__), self.assertRaises(APIError):
                password_hash(value)

    def test_student_registration_login_and_existing_hash_are_preserved(self):
        for length in (6, 7, 9, 10):
            with self.subTest(length=length):
                login = 'policy-student-'+str(length)
                body = self.student_body(login, length)
                body.pop('status')
                result = StudentClient(self.server).call('auth/register', body)
                self.assertTrue(result['authenticated'])
                with connect(self.path) as db:
                    before = db.execute('SELECT password_hash FROM accounts WHERE id=?', (result['account']['id'],)).fetchone()[0]
                logged = StudentClient(self.server).call('auth/login', {'login': login, 'password': body['password']})
                self.assertEqual(logged['account']['id'], result['account']['id'])
                self.assertNotIn(body['password'], json.dumps(logged))
                with connect(self.path) as db:
                    after = db.execute('SELECT password_hash FROM accounts WHERE id=?', (result['account']['id'],)).fetchone()[0]
                self.assertEqual(before, after)
        for length in (5, 129):
            body = self.student_body('policy-rejected-'+str(length), length)
            body.pop('status')
            with self.subTest(rejected_length=length), self.assertRaises(APIError):
                StudentClient(self.server).call('auth/register', body)
            with connect(self.path) as db:
                self.assertIsNone(db.execute('SELECT id FROM accounts WHERE login_identifier=?', (body['login'],)).fetchone())

    def test_admin_creates_student_and_resets_password_to_six_characters(self):
        body = self.student_body('policy-admin-student', 7)
        row = self.admin.call('accounts', body)['account']
        StudentClient(self.server).call('auth/login', {'login': body['login'], 'password': body['password']})
        for length in (5, 129):
            with self.subTest(rejected_length=length), self.assertRaises(APIError):
                self.admin.call('accounts/'+str(row['id']), {'revision': row['revision'], 'password': synthetic_password(length)})
        changed = self.admin.call('accounts/'+str(row['id']), {'revision': row['revision'], 'password': synthetic_password(6)})['account']
        StudentClient(self.server).call('auth/login', {'login': body['login'], 'password': synthetic_password(6)})
        with self.assertRaises(APIError):
            StudentClient(self.server).call('auth/login', {'login': body['login'], 'password': body['password']})
        with connect(self.path) as db:
            before = db.execute('SELECT password_hash FROM accounts WHERE id=?', (row['id'],)).fetchone()[0]
        self.admin.call('accounts/'+str(row['id']), {'revision': changed['revision'], 'password': '', 'name': 'Mầm nhỏ'})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT password_hash FROM accounts WHERE id=?', (row['id'],)).fetchone()[0], before)
        with self.assertRaises(APIError):
            self.admin.call('accounts', self.student_body('policy-admin-short', 5))

    def test_staff_create_reset_and_self_change_use_six_character_minimum(self):
        teacher_body = {'login': 'policy-teacher', 'fullName': 'Giáo viên thử', 'role': 'teacher',
                        'status': 'active', 'password': synthetic_password(6)}
        users = self.admin.call('users', teacher_body)['users']
        teacher = next(row for row in users if row['login']==teacher_body['login'])
        StaffClient(self.server).call('login', {'login': teacher['login'], 'password': teacher_body['password']})
        for length in (5, 129):
            with self.subTest(rejected_length=length), self.assertRaises(APIError):
                self.admin.call('users', {**teacher_body, 'id': teacher['id'], 'revision': teacher['revision'], 'password': synthetic_password(length)})
        users = self.admin.call('users', {**teacher_body, 'id': teacher['id'], 'revision': teacher['revision'], 'password': synthetic_password(9)})['users']
        teacher = next(row for row in users if row['id']==teacher['id'])
        client = StaffClient(self.server)
        client.call('login', {'login': teacher['login'], 'password': synthetic_password(9)})
        for length in (5, 129):
            with self.subTest(rejected_self_length=length), self.assertRaises(APIError):
                client.call('password', {'currentPassword': synthetic_password(9), 'newPassword': synthetic_password(length)})
        client.call('password', {'currentPassword': synthetic_password(9), 'newPassword': synthetic_password(6)})
        StaffClient(self.server).call('login', {'login': teacher['login'], 'password': synthetic_password(6)})
        with self.assertRaises(APIError):
            StaffClient(self.server).call('login', {'login': teacher['login'], 'password': synthetic_password(9)})

    def test_first_admin_bootstrap_accepts_six_and_rejects_five(self):
        path = Path(self.directory.name) / 'bootstrap.sqlite3'
        initialize(path)
        with self.assertRaises(APIError):
            create_first_admin(path, 'admin', 'Quản trị thử', synthetic_password(5))
        create_first_admin(path, 'admin', 'Quản trị thử', synthetic_password(6))
        with connect(path) as db:
            encoded = db.execute('SELECT password_hash FROM staff_users WHERE login=\'admin\'').fetchone()[0]
        self.assertTrue(verify_password(synthetic_password(6), encoded))


if __name__ == '__main__':
    unittest.main()
