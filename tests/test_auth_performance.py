import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.staff_api import create_first_admin
from test_platform_api import Client


class AuthPerformanceTests(unittest.TestCase):
    def setUp(self):
        Path('work').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='work')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'auth.sqlite3'
        initialize(self.path)
        self.server = SimpleNamespace(database_path=self.path, arena=Arena(), review_upgrades=False)
        api.seed_catalog(self.path)
        self.client = Client(self.server)
        self.login = 'auth-' + secrets.token_hex(6)
        self.password = 'Mật-khẩu-' + secrets.token_urlsafe(12)
        self.state = self.client.call('auth/register', {'login':self.login,'password':self.password,
            'name':'Bạn học thử','birthYear':api.academic()[0]-10})

    def test_public_identity_omits_private_history_and_preserves_theme_progress_owner(self):
        self.client.call('lessons/public-decimal/complete',{})
        self.client.call('preferences',{'theme':'garden-notebook'})
        full = self.client.call('session')
        public = self.client.call('session?view=identity')
        self.assertTrue(public['partial'])
        self.assertEqual(public['csrf'], full['csrf'])
        self.assertEqual(public['account']['id'],full['account']['id'])
        self.assertEqual(public['state']['theme'],full['state']['theme'])
        self.assertEqual(public['state']['mascot'],full['state']['mascot'])
        self.assertIn('public-decimal',public['state']['completed'])
        self.assertNotIn('lessons',public)
        self.assertNotIn('exams',public['state'])
        self.assertNotIn('notifications',public['account'])
        self.assertLess(len(json.dumps(public)),len(json.dumps(full)))
        other=Client(self.server)
        self.assertFalse(other.call('session?view=identity')['authenticated'])
        logged=other.call('auth/login?view=identity',{'login':self.login,'password':self.password})
        self.assertEqual(logged['account']['id'],full['account']['id'])
        self.assertTrue(logged['partial'])
        self.assertIn('lessons',other.call('session'))
        other.csrf='wrong'
        with self.assertRaises(api.APIError) as caught:
            other.call('lessons/public-percent/complete',{})
        self.assertEqual(caught.exception.status,403)

    def test_student_staff_unknown_and_wrong_password_each_verify_once(self):
        staff_login='staff-'+secrets.token_hex(6)
        create_first_admin(self.path,staff_login,'Giáo viên thử',self.password)
        for login,password,expected in [(self.login,self.password,'student'),
                (staff_login,self.password,'staff'),('missing-'+secrets.token_hex(6),self.password,None),
                (self.login,'wrong-password',None),(staff_login,'wrong-password',None)]:
            with self.subTest(login=login), patch.object(api,'verify_password',wraps=api.verify_password) as verify:
                if expected:
                    self.assertEqual(api.prepare_login(self.path,{'login':login,'password':password})[0],expected)
                else:
                    with self.assertRaises(api.APIError) as caught:
                        api.prepare_login(self.path,{'login':login,'password':password})
                    self.assertEqual(caught.exception.status,401)
                self.assertEqual(verify.call_count,1)

    def test_proof_rechecks_status_after_password_verification(self):
        proof=api.prepare_login(self.path,{'login':self.login,'password':self.password})
        with api.connect(self.path,True) as db:
            db.execute("UPDATE accounts SET status='suspended' WHERE id=?",(proof[1],))
        with api.connect(self.path,True) as db:
            with self.assertRaises(api.APIError):api.verified_login(db,proof)
