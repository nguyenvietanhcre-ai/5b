"""Family cart grant and payment integration on disposable local databases."""
import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend import payments, platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.staff_api import create_first_admin
from backend.subscriptions import active_annual_cycle
from test_family_accounts import FamilyClient
from test_staff_api import StaffClient


class FamilyCartTests(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[2] / 'test-databases'
        work.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix='family-cart-', dir=work)
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'cart.sqlite3'
        initialize(self.path)
        api.initialize_catalog(self.path)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        self.secret = 'isolated-family-cart-test-signing-key-01'
        self.environment = {'MAM_TOAN_SEPAY_ENABLED': '1', 'MAM_TOAN_SEPAY_WEBHOOK_SECRET': self.secret,
                            'MAM_TOAN_BANK_ID': 'ACB', 'MAM_TOAN_BANK_ACCOUNT': '123456789',
                            'MAM_TOAN_BANK_NAME': 'TAI KHOAN THU NGHIEM'}
        settings = patch.dict(os.environ, self.environment)
        settings.start()
        self.addCleanup(settings.stop)
        hashing = patch.object(api, 'ITERATIONS', 1000)
        hashing.start()
        self.addCleanup(hashing.stop)

    def parent(self, two_children=True):
        client = FamilyClient(self.server)
        email = secrets.token_hex(8) + '@example.test'
        consent = {'accepted': True, 'version': '2026-11-17-draft1', 'name': 'Phụ huynh thử',
                   'contact': email, 'role': 'parent'}
        state = client.call('register', {'email': email, 'password': 'test-family-cart-42',
                                        'parentName': consent['name'], 'legalConsent': consent,
                                        'requestKey': secrets.token_hex(12),
                                        'child': {'name': 'Bé Một', 'grade': 5, 'birthYear': api.academic()[0]-10,
                                                  'mascot': 'cat', 'pin': '4321'}})
        self.assertEqual(len(state['children']), 1)
        state = client.call('parent/pin/setup', {'pin': '654321'})
        if two_children:
            state = client.call('children/add', {'name': 'Bé Hai', 'grade': 4, 'birthYear': api.academic()[0]-9,
                                                 'mascot': 'dog', 'pin': '4321', 'legalConsent': consent,
                                                 'requestKey': secrets.token_hex(12)})
        return client, [child['id'] for child in state['children']]

    def add(self, parent, sid, revision, plan='VIP', period='month', referral_code=''):
        return parent.call('cart/items/upsert', {'revision': revision, 'studentId': sid, 'plan': plan, 'period': period,
                                                 'referralCode': referral_code})['cart']

    def checkout_body(self, parent, revision):
        quote = parent.call('cart/preview', {'revision': revision})
        return {'revision': revision, 'checkout': {'accepted': True, 'policyVersion': quote['preview']['policyVersion'],
                    'quoteHash': quote['quoteHash'], 'purchaser': {'name': 'Phụ huynh thử', 'contact': 'payer@example.test',
                                                                  'relationship': 'parent', 'representativeDeclared': True}}}

    def accounts(self, children):
        with api.connect(self.path) as db:
            return [db.execute('SELECT account_id FROM students WHERE id=?', (child,)).fetchone()[0] for child in children]

    def webhook(self, order, identity, amount=None):
        event = {'id': identity, 'gateway': 'ACB', 'accountNumber': self.environment['MAM_TOAN_BANK_ACCOUNT'],
                 'content': order['reference'] + ' thanh toan', 'transferType': 'in', 'referenceCode': f'TEST-{identity}',
                 'transferAmount': order['amount'] if amount is None else amount}
        raw = json.dumps(event).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(self.secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        headers = {'Content-Type': 'application/json', 'X-SePay-Timestamp': timestamp,
                   'X-SePay-Signature': 'sha256=' + signature}
        return payments.receive_webhook(self.path, headers, raw)

    def test_signed_transfer_grants_two_children_preserving_unrelated_pending_exam(self):
        parent, children = self.parent()
        accounts = self.accounts(children)
        _, referral_children = self.parent(False)
        referrer = self.accounts(referral_children)[0]
        with api.connect(self.path, True) as db:
            code = db.execute('SELECT invite_code FROM accounts WHERE id=?', (referrer,)).fetchone()[0]
            exam = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at,purchase_type,'
                              'exam_product_slug,exam_title,exam_payload_json) VALUES (?,?,?,?,?,?,?,?)',
                              (accounts[0], 'BM' + 'E' * 20, 64000, api.stamp(), 'exam', 'exam-cart-fixture',
                               'Đề riêng đang chờ', api.packed({'title': 'Đề riêng đang chờ', 'price': 64000}))).lastrowid
        before = parent.call('state')['selectedChildId']
        first = self.add(parent, children[0], 0, referral_code=code)
        cart = self.add(parent, children[1], first['revision'], 'VIP+', 'year')
        body = self.checkout_body(parent, cart['revision'])
        order = parent.call('cart/checkout', body)['order']
        self.assertEqual(order['amount'], 2100000)
        self.assertIn(order['reference'], order['qrUrl'])
        self.assertEqual(parent.call('cart/checkout', body)['order']['id'], order['id'])
        self.assertEqual(parent.call('state')['selectedChildId'], before)

        self.add(parent, children[0], cart['revision'], plan='VIP+', period='month')
        self.assertEqual(self.webhook(order, 41, 99), ({'success': True}, 201))
        review = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual((review['status'], review['paymentReceived'], review['qrUrl']), ('review', True, ''))
        self.assertEqual(self.webhook(order, 42), ({'success': True}, 201))
        self.assertEqual(self.webhook(order, 42), ({'success': True}, 201))
        self.assertEqual(self.webhook(order, 43), ({'success': True}, 201))

        paid = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual(paid['fulfillmentStatus'], 'granted')
        self.assertTrue(all(line['subscriptionEndsAt'] for line in paid['items']))
        self.assertEqual(parent.call('cart/checkout', body)['order']['id'], order['id'])
        remaining = parent.call('cart')['cart']['items']
        self.assertEqual([(item['studentId'], item['plan']) for item in remaining], [(children[0], 'VIP+')])
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?', (exam,)).fetchone()[0], 'pending')
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM child_referral_rewards').fetchone()[0], 1)
            self.assertEqual(active_annual_cycle(db, {'account_id': accounts[1]})['limit'], 3600)
            self.assertEqual(len(payments.order_history(db, {'account_id': accounts[0]})['orders']), 1)
            self.assertEqual(db.execute("SELECT count(*) FROM payment_receipts WHERE status='processed' "
                                        'AND family_cart_order_id=?', (order['id'],)).fetchone()[0], 1)

    def test_manual_confirmation_and_legacy_subscription_exclusion(self):
        parent, children = self.parent()
        first, second = self.accounts(children)
        self.add(parent, children[1], 0)
        with api.connect(self.path, True) as db:
            existing = payments.create_order(db, {'account_id': second, 'student_id': children[1]}, {})['order']
        with self.assertRaises(api.APIError) as conflict:
            self.checkout_body(parent, 1)
        self.assertEqual(conflict.exception.code, 'cart_subscription_pending')
        with api.connect(self.path, True) as db:
            db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (existing['id'],))
        order = parent.call('cart/checkout', self.checkout_body(parent, 1))['order']
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError) as blocked:
                payments.create_order(db, {'account_id': second, 'student_id': children[1]}, {})
            self.assertEqual(blocked.exception.code, 'cart_subscription_pending')
            payments.create_order(db, {'account_id': first, 'student_id': children[0]}, {})

        password = 'family-cart-staff-test-42'
        create_first_admin(self.path, 'staff-cart-fixture', 'Quản trị kiểm thử', password)
        admin = StaffClient(self.server)
        admin.call('login', {'login': 'staff-cart-fixture', 'password': password})
        listed = admin.call('payments')['rows']
        aggregate = next(row for row in listed if row.get('isFamilyOrder'))
        self.assertEqual(aggregate['reference'], order['reference'])
        data = {'reference': order['reference'], 'amount': order['amount']}
        endpoint = f"family-payments/{order['id']}/confirm"
        admin.call(endpoint, data)
        admin.call(endpoint, data)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT account_id FROM vip_purchases').fetchall()[0][0], second)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM staff_audit_log WHERE entity='family_payment'").fetchone()[0], 1)

    def test_cancelled_order_with_late_transfer_remains_ungranted(self):
        parent, children = self.parent(False)
        self.add(parent, children[0], 0)
        order = parent.call('cart/checkout', self.checkout_body(parent, 1))['order']
        endpoint = f"cart/orders/{order['id']}"
        self.assertEqual(parent.call(endpoint + '/cancel', {})['order']['status'], 'cancelled')
        self.webhook(order, 91)
        late = parent.call(endpoint)['order']
        self.assertEqual((late['status'], late['fulfillmentStatus'], late['paymentReceived']), ('review', 'cancelled', True))
        self.assertIsNone(parent.call('cart')['pendingOrder'])
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 0)
