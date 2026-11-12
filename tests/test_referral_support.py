"""Only an authorized admin can acknowledge an eligible assisted SVip reward."""
import secrets
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, now, seed_catalog, stamp
from backend.staff_api import create_first_admin
import test_payment_referrers as payment_support
from test_staff_api import StaffClient
import test_staff_api as support


class ReferralSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='referral-support-tests-', dir=work)
        cls.path = Path(cls.directory.name) / 'support.sqlite3'
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

    student = payment_support.PaymentReferrerTests.student
    referred_payment = payment_support.PaymentReferrerTests.referred_payment
    payment = payment_support.PaymentReferrerTests.payment

    def eligible(self):
        inviter, state, student, payer, sid, order = self.referred_payment()
        with connect(self.path, True) as db:
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                       (state['account']['id'], stamp(now() - timedelta(days=1))))
        self.admin.call(f'payments/{order["id"]}/confirm', {'reference': order['reference'], 'amount': order['amount']})
        referrer = self.payment(order['id'], q=order['reference'])['referrer']
        self.assertTrue(referrer['canConfirmSupport'])
        return inviter, state, student, payer, sid, order, referrer['referralId']

    def confirm(self, referral, account, client=None):
        return (client or self.admin).call(f'referrals/{referral}/confirm-support', {'referrerAccountId': account})

    def financial(self):
        with connect(self.path) as db:
            return {table: [tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY id')]
                    for table in ('accounts', 'access_entitlements', 'account_referrals', 'vip_purchases',
                                  'payment_orders', 'class_fees', 'notifications')}

    def test_confirm_persists_without_vip_payment_or_legacy_referral_changes(self):
        inviter, state, _, _, _, order, referral = self.eligible()
        before = self.financial()
        result = self.confirm(referral, state['account']['id'])
        self.assertEqual(self.financial(), before)
        self.assertTrue(result['saved'])
        self.assertFalse(result['replayed'])
        self.assertEqual(result['referralId'], referral)
        self.assertTrue(result['supportConfirmedAt'])
        row = self.payment(order['id'], q=order['reference'])['referrer']
        self.assertFalse(row['canConfirmSupport'])
        self.assertEqual(row['supportConfirmedAt'], result['supportConfirmedAt'])
        self.assertEqual(row['supportConfirmedBy'], result['supportConfirmedBy'])
        self.assertEqual(row['rewardStatus'], 'customer_service')
        self.assertIsNone(row['rewardGrantedAt'])
        self.assertIsNone(row['rewardVipExpiresAt'])
        history = inviter.call('referrals')['rows'][0]
        self.assertEqual(history['support_confirmed_at'], result['supportConfirmedAt'])
        self.assertEqual(history['reward_status'], 'customer_service')
        self.assertEqual(inviter.call('session')['account']['referrals'][0], history)
        initialize(self.path)
        initialize(self.path)
        self.assertEqual(inviter.call('referrals')['rows'][0]['support_confirmed_at'], result['supportConfirmedAt'])

    def test_retry_by_another_admin_is_once_and_all_order_rows_share_state(self):
        _, state, student, _, _, order, referral = self.eligible()
        renewal = student.call('payments', {})['order']
        first = self.confirm(referral, state['account']['id'])
        login, password = 'second-admin-' + secrets.token_hex(5), secrets.token_urlsafe(20)
        self.admin.call('users', {'login': login, 'fullName': 'Admin thứ hai', 'role': 'admin',
                                  'status': 'active', 'password': password})
        other = StaffClient(self.server)
        other.call('login', {'login': login, 'password': password})
        second = self.confirm(referral, state['account']['id'], other)
        self.assertTrue(second['replayed'])
        self.assertEqual(second['supportConfirmedAt'], first['supportConfirmedAt'])
        self.assertEqual(second['supportConfirmedBy'], first['supportConfirmedBy'])
        self.assertEqual(self.payment(order['id'], q=order['reference'])['referrer'],
                         self.payment(renewal['id'], q=renewal['reference'])['referrer'])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM referral_reward_confirmations WHERE referral_id=?',
                                        (referral,)).fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM staff_audit_log WHERE entity='referral_reward' AND entity_id=?",
                                        (str(referral),)).fetchone()[0], 1)

    def test_auth_csrf_teacher_binding_and_unknown_referral_are_rejected(self):
        _, state, _, _, _, _, referral = self.eligible()
        with self.assertRaises(APIError) as anonymous:
            self.confirm(referral, state['account']['id'], StaffClient(self.server))
        self.assertEqual(anonymous.exception.status, 401)
        teacher, _ = support.StaffTests.teacher(self)
        with self.assertRaises(APIError) as denied:
            self.confirm(referral, state['account']['id'], teacher)
        self.assertEqual(denied.exception.status, 403)
        csrf = StaffClient(self.server)
        csrf.headers['Cookie'] = self.admin.headers['Cookie']
        with self.assertRaises(APIError) as bad_csrf:
            self.confirm(referral, state['account']['id'], csrf)
        self.assertEqual(bad_csrf.exception.status, 403)
        with self.assertRaises(APIError) as wrong:
            self.confirm(referral, state['account']['id'] + 99999)
        self.assertEqual(wrong.exception.status, 409)
        with self.assertRaises(APIError) as missing:
            self.confirm(999999999, state['account']['id'])
        self.assertEqual(missing.exception.status, 404)
        for invalid in (None, True, '1', 0):
            with self.assertRaises(APIError) as malformed:
                self.confirm(referral, invalid)
            self.assertEqual(malformed.exception.status, 400)
        first = self.confirm(referral, state['account']['id'])
        with self.assertRaises(APIError) as wrong_replay:
            self.confirm(referral, state['account']['id'] + 99999)
        self.assertEqual(wrong_replay.exception.status, 409)
        self.assertTrue(first['saved'])

    def test_pending_automatic_and_non_svip_rewards_cannot_be_acknowledged(self):
        _, pending_state, _, _, _, pending_order = self.referred_payment()
        with connect(self.path, True) as db:
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                       (pending_state['account']['id'], stamp(now() - timedelta(days=1))))
        pending = self.payment(pending_order['id'], q=pending_order['reference'])['referrer']
        self.assertFalse(pending['canConfirmSupport'])
        with self.assertRaises(APIError) as unqualified:
            self.confirm(pending['referralId'], pending_state['account']['id'])
        self.assertEqual(unqualified.exception.status, 409)
        _, auto_state, _, _, _, auto_order = self.referred_payment()
        self.admin.call(f'payments/{auto_order["id"]}/confirm', {'reference': auto_order['reference'], 'amount': auto_order['amount']})
        automatic = self.payment(auto_order['id'], q=auto_order['reference'])['referrer']
        self.assertEqual(automatic['rewardStatus'], 'granted')
        self.assertFalse(automatic['canConfirmSupport'])
        with self.assertRaises(APIError) as auto:
            self.confirm(automatic['referralId'], auto_state['account']['id'])
        self.assertEqual(auto.exception.status, 409)
        _, state, _, _, _, order, referral = self.eligible()
        with connect(self.path, True) as db:
            db.execute('UPDATE access_entitlements SET ends_at=? WHERE account_id=?',
                       (stamp(now() - timedelta(hours=1)), state['account']['id']))
        self.assertFalse(self.payment(order['id'], q=order['reference'])['referrer']['canConfirmSupport'])
        with self.assertRaises(APIError) as expired:
            self.confirm(referral, state['account']['id'])
        self.assertEqual(expired.exception.status, 409)
        _, legacy_state, _, _, _, legacy_order, legacy_referral = self.eligible()
        ordinary, ordinary_state, _ = self.student()
        ordinary_order = ordinary.call('payments', {})['order']
        self.admin.call(f'payments/{ordinary_order["id"]}/confirm',
                        {'reference': ordinary_order['reference'], 'amount': ordinary_order['amount']})
        with connect(self.path, True) as db:
            unrelated_purchase = db.execute('SELECT id FROM vip_purchases WHERE account_id=?',
                                             (ordinary_state['account']['id'],)).fetchone()[0]
            db.execute('UPDATE account_referrals SET qualifying_purchase_id=? WHERE id=?',
                       (unrelated_purchase, legacy_referral))
        self.assertFalse(self.payment(legacy_order['id'], q=legacy_order['reference'])['referrer']['canConfirmSupport'])
        with self.assertRaises(APIError) as malformed_legacy:
            self.confirm(legacy_referral, legacy_state['account']['id'])
        self.assertEqual(malformed_legacy.exception.status, 409)

    def test_failed_audit_rolls_back_and_completed_confirmation_remains_immutable(self):
        _, state, _, _, _, _, referral = self.eligible()
        with connect(self.path, True) as db:
            db.execute("CREATE TRIGGER reject_support_audit BEFORE INSERT ON staff_audit_log "
                       "WHEN NEW.entity='referral_reward' BEGIN SELECT RAISE(ABORT,'QA audit failure'); END")
        before = self.financial()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                self.confirm(referral, state['account']['id'])
            self.assertEqual(self.financial(), before)
            with connect(self.path) as db:
                self.assertFalse(db.execute('SELECT 1 FROM referral_reward_confirmations WHERE referral_id=?',
                                            (referral,)).fetchone())
        finally:
            with connect(self.path, True) as db:
                db.execute('DROP TRIGGER reject_support_audit')
        result = self.confirm(referral, state['account']['id'])
        with connect(self.path, True) as db:
            db.execute('UPDATE access_entitlements SET ends_at=? WHERE account_id=?',
                       (stamp(now() - timedelta(hours=1)), state['account']['id']))
        replay = self.confirm(referral, state['account']['id'])
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['supportConfirmedAt'], result['supportConfirmedAt'])
        for sql in ('UPDATE referral_reward_confirmations SET confirmed_at=confirmed_at WHERE referral_id=?',
                    'DELETE FROM referral_reward_confirmations WHERE referral_id=?'):
            with connect(self.path, True) as db:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql, (referral,))

    def test_history_pagination_and_owner_privacy_keep_assistance_on_correct_referral(self):
        inviter, state, student, _, _, _, referral = self.eligible()
        result = self.confirm(referral, state['account']['id'])
        for _ in range(5):
            self.student(invite=state['state']['inviteCode'])
        first, second = inviter.call('referrals'), inviter.call('referrals?page=2')
        self.assertEqual((first['total'], len(first['rows']), len(second['rows'])), (6, 5, 1))
        self.assertFalse(any(row['support_confirmed_at'] for row in first['rows']))
        self.assertEqual(second['rows'][0]['id'], referral)
        self.assertEqual(second['rows'][0]['support_confirmed_at'], result['supportConfirmedAt'])
        self.assertEqual(student.call('referrals')['rows'], [])


if __name__ == '__main__':
    unittest.main()
