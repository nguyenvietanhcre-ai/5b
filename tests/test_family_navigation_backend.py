"""Focused backend changes use disposable databases, never live data."""
import hashlib
import os
import re
import secrets
import shutil
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from backend import platform_api as api, family_features as features
import test_family_accounts as existing_family_tests
from test_family_accounts import FamilyClient
SEND_RESET = features.send_reset

class FamilyNavigationTests(unittest.TestCase):
    PASSWORD = existing_family_tests.FamilyAccountsTests.PASSWORD
    setUp = existing_family_tests.FamilyAccountsTests.setUp
    consent = existing_family_tests.FamilyAccountsTests.consent
    register_body = existing_family_tests.FamilyAccountsTests.register_body
    register = existing_family_tests.FamilyAccountsTests.register
    full = existing_family_tests.FamilyAccountsTests.full
    make_exam = existing_family_tests.FamilyAccountsTests.make_exam
    assert_denied = existing_family_tests.FamilyAccountsTests.assert_denied

    def tokens(self):
        self.sent=[]
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'MAM_TOAN_SMTP_HOST':'local-test-mail','MAM_TOAN_SMTP_LOCAL_TEST':'1'}).start()
        patch.object(features,'send_reset',side_effect=lambda email,token:self.sent.append((email,token))).start()
        return self.sent

    def request_reset(self, client=None):
        return (client or FamilyClient(self.server)).call('password/reset/request',{'email':self.email})

    def redeem(self, token, **extra):
        return FamilyClient(self.server).call('password/reset/confirm', {'token':token,'newPassword':'new123','confirmPassword':'new123',**extra})

    def test_generic_registration_and_recovery_uniform_no_change_until_confirmation(self):
        self.tokens()
        body=self.register_body();body.pop('parentName');body.pop('child')
        client=FamilyClient(self.server);state=client.call('register',body)
        with api.connect(self.path) as db:
            before=dict(db.execute('SELECT * FROM family_accounts').fetchone())
            self.assertEqual(db.execute('SELECT display_name FROM family_parent_profiles').fetchone()[0],'Phụ huynh')
        known=self.request_reset(client)
        unknown=FamilyClient(self.server).call('password/reset/request',{'email':'unknown@example.test'})
        self.assertEqual(known,unknown);self.assertEqual(len(self.sent),1)
        self.assertTrue(client.call('state')['authenticated'])
        with api.connect(self.path) as db:
            self.assertEqual(before,dict(db.execute('SELECT * FROM family_accounts').fetchone()))
            saved=dict(db.execute('SELECT * FROM family_password_resets').fetchone())
            self.assertNotIn(self.sent[0][1],str(saved))
            self.assertEqual(saved['token_hash'],hashlib.sha256(self.sent[0][1].encode()).hexdigest())

    def test_reset_requires_matching_min6_valid_unexpired_single_use_revokes_all_preserves_pin(self):
        self.tokens();client,state=self.register()
        other=FamilyClient(self.server);other.call('login',{'email':self.email,'password':self.PASSWORD})
        with api.connect(self.path) as db:
            pin=db.execute('SELECT pin_hash FROM family_accounts').fetchone()[0]
            children=[tuple(r) for r in db.execute('SELECT * FROM family_children')]
        self.request_reset();token=self.sent[-1][1]
        self.assert_denied(lambda:self.redeem(token,confirmPassword='different'),(400,))
        self.assert_denied(lambda:self.redeem(token,newPassword='short',confirmPassword='short'),(400,))
        self.redeem(token)
        self.assertFalse(client.call('state')['authenticated']);self.assertFalse(other.call('state')['authenticated'])
        self.assert_denied(lambda:self.redeem(token),(400,))
        self.assert_denied(lambda:FamilyClient(self.server).call('login',{'email':self.email,'password':self.PASSWORD}),(401,))
        self.assertTrue(FamilyClient(self.server).call('login',{'email':self.email,'password':'new123'})['authenticated'])
        with api.connect(self.path) as db:
            self.assertEqual(pin,db.execute('SELECT pin_hash FROM family_accounts').fetchone()[0])
            self.assertEqual(children,[tuple(r) for r in db.execute('SELECT * FROM family_children')])

    def test_reset_expiry_rate_and_concurrent_redemption(self):
        self.tokens();self.register()
        for _ in range(4):self.request_reset()
        self.assertEqual(len(self.sent),3)
        token=self.sent[-1][1]
        with patch.object(api,'now',return_value=api.now()+timedelta(minutes=20,seconds=1)):
            self.assert_denied(lambda:self.redeem(token),(400,))
        def claim(_):
            try:self.redeem(token);return 200
            except api.APIError as error:return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(claim,range(2))),[200,400])
        self.assert_denied(lambda:self.redeem(self.sent[0][1]),(400,))

    def test_password_change_invalidates_previously_issued_reset_and_origin_guard(self):
        self.tokens();client,_=self.register();self.request_reset();token=self.sent[-1][1]
        alien=FamilyClient(self.server);alien.headers['Origin']='https://untrusted.example'
        self.assert_denied(lambda:self.request_reset(alien),(403,))
        self.full(client);client.call('password',{'newPassword':'other123'})
        self.assert_denied(lambda:self.redeem(token),(400,))

    def test_smtp_disabled_failure_uniform_and_host_header_not_used(self):
        self.tokens();client,_=self.register()
        with patch.object(features,'send_reset',side_effect=OSError('test failure')):
            self.assertTrue(self.request_reset()['ok'])
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM family_password_resets').fetchone()[0],0)
        with patch.dict(os.environ,{'MAM_TOAN_SMTP_HOST':''}):self.assert_denied(lambda:self.request_reset(),(503,))
        with patch.dict(os.environ,{'MAM_TOAN_SMTP_HOST':'local','MAM_TOAN_RESET_BASE_URL':'http://localhost:19876'}):
            with patch('smtplib.SMTP') as smtp:
                SEND_RESET(self.email, 'test-token-placeholder')
                mail=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
                self.assertIn('http://localhost:19876/gia-dinh/?reset=1#token=',mail.get_content())
                self.assertEqual(mail['To'],self.email)

    def test_companion_one_reselect_same_value_retry_race_and_unchanged_xp(self):
        client,state=self.register();sid=state['selectedChildId']
        self.assertEqual(client.learner()['state']['companionChangesRemaining'],1)
        client.learner('mascot',{'mascot':'cat'})
        def change(code):
            try:
                with api.connect(self.path,True) as db:features.reselect(db,sid,code)
                return 200
            except api.APIError as error:return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(change,['dog','fox'])),[200,409])
        result=client.learner();chosen=result['state']['mascot']
        self.assertEqual(result['state']['companionChangesRemaining'],0)
        client.learner('mascot',{'mascot':chosen})
        self.assert_denied(lambda:client.learner('mascot',{'mascot':'cat'}),(409,))
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT xp FROM student_companions').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],0)
        self.full(client);self.assertEqual(client.call('state')['children'][0]['companionChangesRemaining'],0)

    def test_daily_summary_zero_and_main_pilot_vietnam_midnight(self):
        client,state=self.register();self.full(client)
        self.assertEqual(client.call('parent/overview')['overview'][0]['today']['submittedExams'],0)
        client.call('select',{'childId':state['selectedChildId'],'pin':'4321'})
        exam=self.make_exam(client);client.learner('exams/'+str(exam)+'/submit',{})
        base=api.now().replace(hour=18,minute=0,second=0,microsecond=0)
        with api.connect(self.path,True) as db:
            db.execute('UPDATE exam_attempts SET submitted_at=?',(api.stamp(base),))
        pilot=self.path.with_name('summary-pilot.sqlite3')
        with sqlite3.connect(self.path) as source,sqlite3.connect(pilot) as dest:source.backup(dest)
        with api.connect(pilot,True) as db:
            db.execute('CREATE TABLE local_principals(main_student_id INTEGER,pilot_student_id INTEGER)')
            db.execute('INSERT INTO local_principals VALUES(?,?)',(state['selectedChildId'],state['selectedChildId']))
            db.execute('UPDATE exam_attempts SET submitted_at=?',(api.stamp(base.replace(hour=16,minute=59)),))
        self.server.local_pilot=SimpleNamespace(path=pilot)
        with patch.object(api,'now',return_value=base):
            self.full(client)
            self.assertEqual(client.call('parent/overview')['overview'][0]['today']['submittedExams'],1)
            self.assertEqual(client.call('parent/overview')['overview'][0]['today']['answeredQuestions'],0)
            with api.connect(pilot,True) as db:
                db.execute('UPDATE exam_attempts SET submitted_at=?',(api.stamp(base),))
                db.execute('UPDATE exam_answers SET response_json=?',(api.packed({'answer':'2'}),))
            summary=client.call('parent/overview')['overview'][0]['today']
            self.assertEqual(summary['submittedExams'],2)
            self.assertEqual(summary['answeredQuestions'],1)

    def test_closure_requires_full_pin_confirmation_preserves_rows_and_blocks_reset(self):
        self.tokens();client,state=self.register();self.request_reset();token=self.sent[-1][1]
        self.assert_denied(lambda:client.call('account/delete',{'confirm':'XOA TAI KHOAN','pin':'654321'}),(403,))
        self.full(client)
        self.assert_denied(lambda:client.call('account/delete',{'confirm':'no','pin':'654321'}),(400,))
        self.assert_denied(lambda:client.call('account/delete',{'confirm':'XOA TAI KHOAN','pin':'111111'}),(403,))
        self.assertTrue(client.call('account/delete',{'confirm':'XOA TAI KHOAN','pin':'654321'})['closed'])
        self.assertFalse(client.call('state')['authenticated'])
        self.assert_denied(lambda:self.redeem(token),(400,))
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM family_children').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM family_closures').fetchone()[0],1)
