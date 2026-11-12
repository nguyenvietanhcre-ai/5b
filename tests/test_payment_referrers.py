"""Admin payment reconciliation must identify the attributed reward recipient."""
import secrets
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, now, seed_catalog, stamp
from backend.staff_api import create_first_admin
from test_platform_api import Client as StudentClient
from test_staff_api import StaffClient
import test_staff_api as support


class PaymentReferrerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path(__file__).resolve().parents[1] / 'work'
        scratch.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='payment-referrer-tests-', dir=scratch)
        cls.path = Path(cls.directory.name) / 'payments.sqlite3'
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

    def student(self, name='Mầm Xanh', invite=''):
        client = StudentClient(self.server)
        state = client.call('auth/register', {
            'login': 'referrer-' + secrets.token_hex(7), 'password': secrets.token_urlsafe(20),
            'name': name, 'birthYear': academic()[0] - 10, 'inviteCode': invite})
        with connect(self.path) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (state['account']['id'],)).fetchone()[0]
        return client, state, sid

    def referred_payment(self, name='Mầm Xanh'):
        inviter, inviter_state, _ = self.student(name)
        student, state, sid = self.student('Lá Non', inviter_state['state']['inviteCode'])
        order = student.call('payments', {})['order']
        return inviter, inviter_state, student, state, sid, order

    def payment(self, identity, **query):
        result = self.admin.call('payments?' + urlencode(query))
        return next(row for row in result['rows'] if row['id'] == identity)

    def test_attributed_referrer_and_unreferred_payments(self):
        _, inviter, _, payer, _, order = self.referred_payment()
        row = self.payment(order['id'], q=order['reference'])
        self.assertEqual(row['login_identifier'], payer['account']['login'])
        self.assertEqual(row['full_name'], 'Lá Non')
        self.assertEqual(row['referrer'], {
            'accountId': inviter['account']['id'], 'login': inviter['account']['login'],
            'name': 'Mầm Xanh', 'membership': 'Free', 'rewardStatus': 'pending',
            'rewardGrantedAt': None, 'rewardVipExpiresAt': None,
            'referralId': row['referrer']['referralId'], 'supportConfirmedAt': None,
            'supportConfirmedBy': None, 'canConfirmSupport': False})
        self.assertIsInstance(row['referrer']['referralId'], int)
        self.assertFalse(any(key.startswith('referrer_') for key in row))
        student, state, _ = self.student()
        ordinary_order = student.call('payments', {})['order']
        ordinary = self.payment(ordinary_order['id'], q=state['account']['login'])
        self.assertIsNone(ordinary['referrer'])
        self.assertNotEqual(ordinary['id'], row['id'])

    def test_membership_uses_current_expiry_and_entitlement_dates(self):
        _, inviter, _, _, _, order = self.referred_payment()
        identity = inviter['account']['id']
        with connect(self.path, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?', (stamp(now() - timedelta(days=1)), identity))
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                       (identity, stamp(now() + timedelta(days=1))))
        self.assertEqual(self.payment(order['id'], q=order['reference'])['referrer']['membership'], 'Free')
        with connect(self.path, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?', (stamp(now() + timedelta(days=10)), identity))
        self.assertEqual(self.payment(order['id'], q=order['reference'])['referrer']['membership'], 'VIP')
        with connect(self.path, True) as db:
            entitlement = db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                                     (identity, stamp(now() - timedelta(days=2)))).lastrowid
        self.assertEqual(self.payment(order['id'], q=order['reference'])['referrer']['membership'], 'SVip')
        with connect(self.path, True) as db:
            db.execute('UPDATE access_entitlements SET ends_at=? WHERE id=?', (stamp(now() - timedelta(days=1)), entitlement))
        self.assertEqual(self.payment(order['id'], q=order['reference'])['referrer']['membership'], 'VIP')

    def test_referrer_search_and_combined_filters_paginate_without_duplicates(self):
        _, inviter, _, payer, _, order = self.referred_payment()
        prefix = 'PAGE-' + secrets.token_hex(6)
        with connect(self.path, True) as db:
            db.executemany('INSERT INTO payment_orders(account_id,reference,amount,created_at,status) '
                           "VALUES (?,?,100000,?,'cancelled')",
                           [(payer['account']['id'], f'{prefix}-{index:02}', stamp()) for index in range(26)])
        login = inviter['account']['login']
        first = self.admin.call('payments?' + urlencode({'referrer': login}))
        second = self.admin.call('payments?' + urlencode({'referrer': login, 'page': 2}))
        self.assertEqual((first['total'], second['total']), (27, 27))
        self.assertEqual((len(first['rows']), len(second['rows'])), (25, 2))
        identities = [row['id'] for row in first['rows'] + second['rows']]
        self.assertEqual(len(set(identities)), 27)
        self.assertEqual(identities, sorted(identities, reverse=True))
        general = self.admin.call('payments?' + urlencode({'q': login}))
        self.assertEqual(general['total'], 27)
        by_name = self.admin.call('payments?' + urlencode({'q': prefix + '-00', 'referrer': 'Mầm Xanh'}))
        self.assertEqual(by_name['total'], 1)
        self.assertEqual(by_name['rows'][0]['reference'], prefix + '-00')
        payer_filter = self.admin.call('payments?' + urlencode({'q': payer['account']['login'], 'referrer': login}))
        self.assertEqual(payer_filter['total'], 27)
        self.assertEqual(self.admin.call('payments?' + urlencode({'q': order['reference'], 'referrer': 'No-such-referrer'}))['total'], 0)
        self.assertEqual(self.admin.call('payments?' + urlencode({'referrer': "' OR 1=1 --"}))['total'], 0)

    def test_rewards_and_tuition_keep_original_attribution_without_list_side_effects(self):
        for svip in (False, True):
            _, inviter, student, payer, sid, order = self.referred_payment()
            if svip:
                with connect(self.path, True) as db:
                    db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                               (inviter['account']['id'], stamp(now() - timedelta(days=1))))
            body = {'reference': order['reference'], 'amount': order['amount']}
            self.admin.call(f'payments/{order["id"]}/confirm', body)
            paid = self.payment(order['id'], q=order['reference'])
            referrer = paid['referrer']
            self.assertEqual(referrer['rewardStatus'], 'customer_service' if svip else 'granted')
            self.assertEqual(referrer['membership'], 'SVip' if svip else 'VIP')
            self.assertEqual(referrer['rewardGrantedAt'] is None, svip)
            self.assertEqual(referrer['rewardVipExpiresAt'] is None, svip)
            renewal = student.call('payments', {})['order']
            self.assertEqual(self.payment(renewal['id'], q=renewal['reference'])['referrer'], referrer)
            teacher, user = support.StaffTests.teacher(self)
            group = support.StaffTests.classroom(self, user)
            self.admin.call(f'classes/{group["id"]}/enroll', {'studentId': sid, 'action': 'enroll'})
            with connect(self.path, True) as db:
                fee_id = db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?)',
                                    (group['id'], sid, '2026-11', 200000)).lastrowid
            fee = student.call('payments', {'feeId': fee_id})['order']
            fee_row = self.payment(fee['id'], q=fee['reference'])
            self.assertEqual(fee_row['referrer'], referrer)
            self.assertEqual(fee_row['month'], '2026-11')
            self.assertEqual(fee_row['class_name'], group['name'])
            with connect(self.path) as db:
                before = tuple(tuple(db.execute(f'SELECT * FROM {table}')) for table in
                               ('account_referrals', 'vip_purchases', 'notifications', 'payment_orders'))
            self.payment(fee['id'], q=fee['reference'])
            self.payment(order['id'], q=order['reference'])
            self.admin.call(f'payments/{order["id"]}/confirm', body)
            with connect(self.path) as db:
                after = tuple(tuple(db.execute(f'SELECT * FROM {table}')) for table in
                              ('account_referrals', 'vip_purchases', 'notifications', 'payment_orders'))
            self.assertEqual(before, after)

    def test_admin_only_and_legacy_referrer_nickname_is_masked(self):
        _, inviter, _, _, _, order = self.referred_payment()
        teacher, _ = support.StaffTests.teacher(self)
        with self.assertRaises(APIError) as denied:
            teacher.call('payments?' + urlencode({'referrer': inviter['account']['login']}))
        self.assertEqual(denied.exception.status, 403)
        with connect(self.path, True) as db:
            db.execute('UPDATE students SET full_name=? WHERE account_id=?', ('<script>alert(1)</script>', inviter['account']['id']))
        referrer = self.payment(order['id'], q=order['reference'])['referrer']
        self.assertEqual(referrer['name'], 'Bạn học')
        self.assertEqual(referrer['login'], inviter['account']['login'])
