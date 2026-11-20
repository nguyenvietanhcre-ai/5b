"""Real main/family -> isolated LocalPilot authorization and draft regression tests."""
from contextlib import closing
from datetime import timedelta
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.local_pilot import LocalPilot
from backend.website_legal import VERSION
from test_family_accounts import FamilyClient


class FamilyLocalPilotTests(unittest.TestCase):
    PASSWORD = 'Local-family-pilot-password-17'

    @classmethod
    def setUpClass(cls):
        cls.work = Path(__file__).resolve().parents[2] / 'test-databases'
        cls.work.mkdir(exist_ok=True)
        cls.folder = tempfile.TemporaryDirectory(prefix='family-local-pilot-', dir=cls.work)
        cls.addClassCleanup(cls.folder.cleanup)
        cls.hash_patch = patch.object(api, 'ITERATIONS', 1000)
        cls.hash_patch.start()
        cls.addClassCleanup(cls.hash_patch.stop)
        options = [Path(os.environ['FAMILY_PILOT_INPUTS'])] if os.environ.get('FAMILY_PILOT_INPUTS') else [Path('pilot-inputs'), Path('/app/pilot-inputs')]
        cls.inputs = next((p for p in options if (p / 'manifest.json').is_file()), None)
        if cls.inputs is None:
            raise unittest.SkipTest('Private sealed learning inputs; mandatory local release gate covers this suite')
        cls.main_base = Path(cls.folder.name) / 'main-base.sqlite3'
        cls.pilot_base = Path(cls.folder.name) / 'pilot-base.sqlite3'
        initialize(cls.main_base)
        api.initialize_catalog(cls.main_base)
        LocalPilot(cls.main_base, cls.pilot_base, cls.inputs)

    def setUp(self):
        self.main = Path(self.folder.name) / (secrets.token_hex(8) + '-main.sqlite3')
        self.pilot = self.main.with_name(self.main.stem + '-pilot.sqlite3')
        for source, dest in ((self.main_base, self.main), (self.pilot_base, self.pilot)):
            with closing(sqlite3.connect(source)) as before, closing(sqlite3.connect(dest)) as after:
                before.backup(after)
        self.provider = LocalPilot(self.main, self.pilot, self.inputs)
        self.server = SimpleNamespace(database_path=self.main, server_port=8765,
                                      local_pilot=self.provider, local_pilot_ports={8765},
                                      real_accounts=True, review_upgrades=False, arena=Arena())
        self.email = 'local-family-' + secrets.token_hex(6) + '@example.test'

    def family_actor(self, *, grade=5, birth=None, client=None):
        client = client or FamilyClient(self.server)
        birth = api.academic()[0] - 8 if birth is None else birth
        result = client.call('register', {'email': self.email, 'password': self.PASSWORD,
                             'parentName': 'Phụ huynh thí điểm', 'requestKey': secrets.token_hex(12),
                             'child': {'name': 'Con học lớp năm', 'grade': grade, 'birthYear': birth,
                                       'pin': '4321', 'mascot': 'cat'},
                             'legalConsent': {'accepted': True, 'version': VERSION, 'name': 'Phụ huynh thí điểm',
                                              'contact': self.email, 'role': 'parent'}})
        client.call('parent/pin/setup', {'pin': '654321'})
        return client, client.call('select', {'childId': result['children'][0]['id'], 'pin': '4321'})

    def legacy_actor(self):
        client = FamilyClient(self.server)
        client.learner('auth/register', {'login': 'legacy-pilot-' + secrets.token_hex(6),
                                        'password': self.PASSWORD, 'name': 'Học sinh cũ lớp năm',
                                        'birthYear': api.academic()[0] - 10})
        return client

    def call(self, client, endpoint, body=None):
        parsed = urlsplit(endpoint)
        client.path = '/api/local-pilot/' + endpoint
        client.command = 'GET' if body is None else 'POST'
        client.headers['X-CSRF-Token'] = client.csrf
        client.headers['X-Family-Context'] = client.context
        return self.provider.request(client, client.command, parsed.path, body, parse_qs(parsed.query))

    def quote_body(self, client, slot=1):
        selector = {'setIndex': slot, 'responseMode': 'choice'}
        quote = self.call(client, 'quote', selector)
        return {**selector, 'requestKey': secrets.token_hex(12), 'quoteId': quote['quoteId'],
                'confirmWallet': bool(quote['private'])}

    def exam(self, client, slot=1):
        body = self.quote_body(client, slot)
        return self.call(client, 'exams', body)['exam'], body

    def denied(self, callback, status=409):
        with self.assertRaises(api.APIError) as caught:
            callback()
        self.assertEqual(caught.exception.status, status)

    def ledgers(self):
        with api.connect(self.pilot) as db:
            tables = ('pilot_grants', 'pilot_requests', 'wallet_debits', 'wallet_attempt_receipts',
                      'exam_attempts', 'exam_draft_answers')
            return {name: [tuple(row) for row in db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
                    for name in tables}

    def main_attempt(self, client, identity=1):
        client.learner()
        with api.connect(self.main, True) as db:
            session = api.read_session(client, db)
            grade, year_id = api.ensure_grade(db, session['student_id'], session['birth_year'])
            db.execute('INSERT INTO exams(id,exam_code,title,grade_level,duration_minutes,status,'
                       'academic_year_id,owner_student_id,mode,created_at,response_mode) '
                       "VALUES (?,?,?,?,30,'published',?,?,'test',?,'typed')",
                       (identity, 'MAIN-ONLY-' + secrets.token_hex(6), 'Bài chính đang làm', grade,
                        year_id, session['student_id'], api.stamp()))
            db.execute('INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) '
                       "VALUES (?,?,?,?,'in_progress',?)", (identity, session['student_id'], api.stamp(),
                       api.stamp(api.now() + timedelta(minutes=30)), secrets.token_hex(12)))
        return identity

    def test_declared_grade_five_and_actual_birth_are_preserved_in_pilot(self):
        client, _ = self.family_actor()
        birth = api.academic()[0] - 8  # The historical age formula would choose grade 3.
        self.assertEqual(self.call(client, 'catalogue')['role'], 'Free')
        exam, _ = self.exam(client)
        self.assertEqual(exam['grade'], 5)
        self.assertEqual(exam['reference'], 'pilot:' + exam['id'])
        with api.connect(self.pilot) as db:
            principal = db.execute('SELECT * FROM local_principals').fetchone()
            account = db.execute('SELECT birth_year FROM accounts WHERE id=?', (principal['pilot_account_id'],)).fetchone()
            student = db.execute('SELECT grade_level FROM students WHERE id=?', (principal['pilot_student_id'],)).fetchone()
            self.assertEqual(account[0], birth)
            self.assertEqual(student[0], 5)
            self.assertEqual(api.grade_for_student(db, principal['pilot_student_id'], birth), 5)
        with api.connect(self.main) as db:
            self.assertEqual(db.execute('SELECT actual_birth_year FROM family_children').fetchone()[0], birth)

    def test_family_two_devices_require_current_answer_revision_and_submit_once(self):
        first, _ = self.family_actor()
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        second.call('select', {'childId': first.call('state')['selectedChildId'], 'pin': '4321'})
        exam, _ = self.exam(first)
        eid = exam['id']
        other_view = self.call(second, 'exams/' + eid)['exam']
        self.assertEqual(other_view['revision'], exam['revision'])
        answer = exam['questions'][0]['options'][0]
        saved = self.call(first, f'exams/{eid}/answers',
                          {'position': 1, 'answer': answer, 'revision': exam['revision']})['exam']
        self.assertGreater(saved['revision'], exam['revision'])
        before = self.ledgers()
        stale_answer = exam['questions'][0]['options'][1]
        self.denied(lambda: self.call(second, f'exams/{eid}/answers',
                    {'position': 1, 'answer': stale_answer, 'revision': other_view['revision']}))
        self.denied(lambda: self.call(second, f'exams/{eid}/answers', {'position': 1, 'answer': stale_answer}))
        self.assertEqual(self.ledgers(), before)
        current = self.call(second, 'exams/' + eid)['exam']
        self.assertEqual(current['answers']['1'], answer)
        submitted = self.call(first, f'exams/{eid}/submit', {})['exam']
        replay = self.call(second, f'exams/{eid}/submit', {})['exam']
        self.assertEqual(submitted['submittedAt'], replay['submittedAt'])
        self.assertEqual(submitted['score'], replay['score'])
        with api.connect(self.pilot) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM exam_answers WHERE exam_id=?', (int(eid),)).fetchone()[0], len(exam['questions']))

    def test_late_grade_five_child_does_not_pass_through_legacy_age_validator(self):
        birth = api.academic()[0] - 11  # Historical registration would reject implied grade 6.
        client, _ = self.family_actor(birth=birth)
        self.call(client, 'catalogue')
        exam, _ = self.exam(client)
        self.assertEqual(exam['grade'], 5)
        with api.connect(self.pilot) as db:
            self.assertEqual(db.execute('SELECT a.birth_year FROM local_principals p JOIN accounts a '
                                        'ON a.id=p.pilot_account_id').fetchone()[0], birth)

    def test_active_pilot_exam_conflict_never_debits_or_collides_with_main_source(self):
        client, _ = self.family_actor()
        main_id = self.main_attempt(client)
        exam, body = self.exam(client)
        # Source stores may legitimately allocate the exact same integer ID.
        self.assertEqual(int(exam['id']), main_id)
        self.assertEqual(exam['reference'], 'pilot:' + str(main_id))
        main_view = client.learner('exams/' + str(main_id))['exam']
        self.assertEqual(main_view['reference'], 'main:' + str(main_id))
        self.assertEqual(main_view['title'], 'Bài chính đang làm')
        second_body = self.quote_body(client, slot=2)
        before = self.ledgers()
        self.denied(lambda: self.call(client, 'exams', second_body))
        self.assertEqual(self.ledgers(), before)
        self.assertEqual(self.call(client, 'exams', body)['exam']['id'], exam['id'])
        with api.connect(self.main) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM exam_attempts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0], 0)

    def test_legacy_two_key_answer_body_still_saves_without_family_revision(self):
        client = self.legacy_actor()
        exam, _ = self.exam(client)
        answer = exam['questions'][0]['options'][0]
        saved = self.call(client, 'exams/' + exam['id'] + '/answers', {'position': 1, 'answer': answer})['exam']
        self.assertEqual(saved['answers']['1'], answer)
        self.call(client, 'exams/' + exam['id'] + '/submit', {})
        self.assertTrue(self.call(client, 'exams/' + exam['id'])['exam']['submittedAt'])

    def test_family_signup_flag_blocks_public_legacy_signup_only(self):
        self.legacy_actor()
        with api.connect(self.main) as db:
            legacy_login = db.execute('SELECT login_identifier FROM accounts').fetchone()[0]
        self.server.family_registration_enabled = True
        public = FamilyClient(self.server)
        self.denied(lambda: public.learner('auth/register',
                    {'login': 'blocked-' + secrets.token_hex(6), 'password': self.PASSWORD,
                     'name': 'Đăng ký cũ bị chặn', 'birthYear': api.academic()[0] - 10}), 409)
        with api.connect(self.main) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0], 1)
        existing = FamilyClient(self.server)
        self.assertTrue(existing.learner('auth/login', {'login': legacy_login, 'password': self.PASSWORD})['authenticated'])
        family_client, _ = self.family_actor()
        self.assertEqual(self.exam(family_client)[0]['grade'], 5)
        # The legacy learning mirror is internal and still uses api.register.
        self.assertEqual(self.exam(existing)[0]['grade'], 5)

    def test_child_handoff_and_new_family_device_revoke_only_same_browser_staff(self):
        from backend.staff_api import create_first_admin
        from test_staff_api import StaffClient

        create_first_admin(self.main, 'family-test-admin', 'Quản trị thử', self.PASSWORD)

        def staff_login():
            client = StaffClient(self.server)
            self.assertTrue(client.call('login', {'login': 'family-test-admin', 'password': self.PASSWORD})['authenticated'])
            return client

        other_browser = staff_login()
        on_registration = staff_login()
        browser = FamilyClient(self.server)
        browser.headers['Cookie'] = on_registration.headers['Cookie']
        browser, state = self.family_actor(client=browser)
        self.assertFalse(on_registration.call('session')['authenticated'])
        self.assertTrue(other_browser.call('session')['authenticated'])

        # A staff tab can subsequently authenticate in the same browser. The
        # explicit child handoff must revoke that independent capability too.
        browser.call('parent/unlock', {'pin': '654321'})
        on_handoff = staff_login()
        browser.headers['Cookie'] += '; ' + on_handoff.headers['Cookie']
        browser.call('select', {'childId': state['selectedChildId'], 'pin': '4321'})
        self.assertFalse(on_handoff.call('session')['authenticated'])
        self.assertTrue(other_browser.call('session')['authenticated'])

        on_login = staff_login()
        new_browser = FamilyClient(self.server)
        new_browser.headers['Cookie'] = on_login.headers['Cookie']
        self.assertTrue(new_browser.call('login', {'email': self.email, 'password': self.PASSWORD})['authenticated'])
        self.assertFalse(on_login.call('session')['authenticated'])
        self.assertTrue(other_browser.call('session')['authenticated'])
        self.assertTrue(browser.call('state')['authenticated'])

    def test_revoked_family_cookie_marks_pilot_access_changed(self):
        client, _ = self.family_actor()
        client.call('parent/unlock', {'pin': '654321'})
        revoked = client.copy_capability()
        client.call('devices/logout-all', {})
        with self.assertRaises(api.APIError) as caught:
            self.call(revoked, 'catalogue')
        self.assertEqual(caught.exception.status, 401)
        self.assertIs(caught.exception.familyAccessChanged, True)

    def test_referral_bonus_is_mirrored_as_trusted_paid_capability_and_expires_without_minting(self):
        from backend import payments
        for tier in ('VIP','VIP+'):
            self.email='bonus-ref-'+secrets.token_hex(6)+'@example.test'
            ref,state=self.family_actor()
            self.email='bonus-buy-'+secrets.token_hex(6)+'@example.test'
            buyer,_=self.family_actor()
            with api.connect(self.main,True) as db:
                code=db.execute('SELECT a.invite_code FROM accounts a JOIN students s ON s.account_id=a.id WHERE s.id=?',(state['selectedChildId'],)).fetchone()[0]
                buyer.path='/api/v1/state'
                buyer.headers['X-Family-Context']=buyer.context
                buyer.headers['X-CSRF-Token']=buyer.csrf
                session=api.read_session(buyer,db)
                order=payments.create_order(db,session,{'plan':tier,'referralCode':code})['order']
                payments.settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone(),'staff')
                before=tuple(db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts a JOIN students s ON s.account_id=a.id WHERE s.id=?',(state['selectedChildId'],)).fetchone())
            wallet=self.call(ref,'wallet')
            self.assertEqual(wallet['membership'],tier)
            self.assertTrue(wallet['vip']['active']);self.assertEqual(wallet['vip']['dayLimit'],30)
            with api.connect(self.pilot) as db:
                mapping=db.execute('SELECT * FROM local_principals WHERE main_student_id=?',(state['selectedChildId'],)).fetchone()
                self.assertEqual(db.execute('SELECT count(*) FROM child_referral_rewards').fetchone()[0],0)
                anchor=db.execute('SELECT anchor_at FROM wallet_terms WHERE student_id=?',(mapping['pilot_student_id'],)).fetchone()[0]
            with patch.object(api,'now',return_value=api.now()+timedelta(days=8)):
                expired=self.call(ref,'wallet');self.assertEqual(expired['membership'],'Free');self.assertFalse(expired['vip']['active'])
            with api.connect(self.main) as db:
                self.assertEqual(before,tuple(db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts a JOIN students s ON s.account_id=a.id WHERE s.id=?',(state['selectedChildId'],)).fetchone()))
            with api.connect(self.pilot) as db:
                self.assertEqual(db.execute('SELECT anchor_at FROM wallet_terms WHERE student_id=?',(mapping['pilot_student_id'],)).fetchone()[0],anchor)


if __name__ == '__main__':
    unittest.main()
