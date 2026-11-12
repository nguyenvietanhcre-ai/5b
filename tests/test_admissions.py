import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend.database import initialize
from backend.platform_api import APIError, connect, dispatch
from backend.staff_api import create_first_admin
from test_staff_api import StaffClient


class IntakeClient:
    def __init__(self, server):
        self.server = server
        self.client_address = ('intake-' + secrets.token_hex(8), 1234)
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.api_headers = {}

    def token(self):
        value, _ = dispatch(self, 'GET', '/api/v1/admissions/token')
        self.headers['Cookie'] = self.api_headers['Set-Cookie'].split(';')[0]
        self.headers['X-Intake-Token'] = value['token']

    def submit(self, **changes):
        body = dict(parentName='Phụ huynh thử', phone='+84 912 345 678', email='qa@example.invalid',
            studentName='Học sinh thử', grade=4, school='', city='Hà Nội', goal='Phát triển tư duy Toán',
            level='Cần tư vấn', schedule='Sáng cuối tuần', contact='Zalo', notes='', consent=True,
            requestKey=secrets.token_hex(16), website='')
        body.update(changes)
        return dispatch(self, 'POST', '/api/v1/admissions', body)[0], body


class AdmissionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'intake.sqlite3'
        initialize(self.path)
        self.server = SimpleNamespace(database_path=self.path)
        self.client = IntakeClient(self.server)
        self.client.token()

    def tearDown(self):
        self.directory.cleanup()

    def admin(self):
        password = secrets.token_urlsafe(20)
        create_first_admin(self.path, 'admin', 'Quản trị thử', password)
        client = StaffClient(self.server)
        client.call('login', dict(login='admin', password=password))
        return client

    def test_anonymous_save_normalization_and_safe_retry(self):
        result, body = self.client.submit()
        again, _ = self.client.submit(**body)
        self.assertEqual(result, again)
        self.assertTrue(result['saved'])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM entrance_registrations').fetchone()[0], 1)
            row = db.execute('SELECT * FROM entrance_registrations').fetchone()
            self.assertEqual(row['phone'], '0912345678')
            self.assertTrue(json.loads(row['details_json'])['consent'])
        with self.assertRaises(APIError) as raised:
            self.client.submit(**{**body, 'studentName': 'Đã đổi tên'})
        self.assertEqual(raised.exception.status, 409)

    def test_validation_consent_and_honeypot(self):
        for patch in ({'phone':'123'}, {'email':'invalid'}, {'grade':6}, {'grade':True},
                      {'consent':False}, {'parentName':''}, {'notes':'x'*1501}, {'contact':'Unknown'}, {'website':'bot'}):
            with self.subTest(patch=list(patch)), self.assertRaises(APIError):
                self.client.submit(**patch)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM entrance_registrations').fetchone()[0], 0)

    def test_csrf_cookie_origin_and_expired_token(self):
        original = self.client.headers.copy()
        for patch in ({'X-Intake-Token':''}, {'Cookie':''}, {'Origin':'https://other.invalid'},
                      {'Origin':''}, {'X-Intake-Token':'1.invalid'}):
            self.client.headers = {**original, **patch}
            with self.subTest(patch=list(patch)), self.assertRaises(APIError) as raised:
                self.client.submit()
            self.assertEqual(raised.exception.status, 403)

    def test_rate_limit_and_retry_does_not_duplicate(self):
        first, body = self.client.submit()
        for _ in range(4):
            self.client.submit()
        retry, _ = self.client.submit(**body)
        self.assertEqual(first, retry)
        with self.assertRaises(APIError) as raised:
            self.client.submit()
        self.assertEqual(raised.exception.status, 429)

    def test_admin_review_revision_audit_and_teacher_denied(self):
        result, _ = self.client.submit()
        admin = self.admin()
        rows = admin.call('admissions?q=' + result['reference'])['rows']
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertNotIn('request_key', row)
        change = dict(status='scheduled', note='Đã trao đổi', revision=row['revision'])
        admin.call('admissions/' + str(row['id']), change)
        with self.assertRaises(APIError) as raised:
            admin.call('admissions/' + str(row['id']), change)
        self.assertEqual(raised.exception.status, 409)
        current = admin.call('admissions')['rows'][0]
        self.assertEqual(current['status'], 'scheduled')
        self.assertEqual(current['admin_note'], 'Đã trao đổi')
        audit = admin.call('audit')['rows'][0]
        self.assertEqual(audit['entity'], 'admission')
        self.assertNotIn('0912345678', audit['summary'])
        password = secrets.token_urlsafe(20)
        admin.call('users', dict(login='teacher', fullName='Giáo viên thử', role='teacher', status='active', password=password))
        teacher = StaffClient(self.server)
        teacher.call('login', dict(login='teacher', password=password))
        for path, body in [('admissions', None), ('admissions/'+str(row['id']), change)]:
            with self.assertRaises(APIError) as raised:
                teacher.call(path, body)
            self.assertEqual(raised.exception.status, 403)
        with self.assertRaises(APIError) as raised:
            StaffClient(self.server).call('admissions')
        self.assertEqual(raised.exception.status, 401)

    def test_no_public_readback(self):
        self.client.submit()
        with self.assertRaises(APIError) as raised:
            dispatch(self.client, 'GET', '/api/v1/admissions')
        self.assertEqual(raised.exception.status, 404)
