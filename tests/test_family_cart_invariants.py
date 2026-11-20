"""Exercise the family cart over HTTP with isolated accounts and bank events."""

import hashlib
import hmac
import http.client
import json
import os
import secrets
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from backend import platform_api as api, subscriptions
from backend.arena import Arena
from backend.database import initialize
from backend.server import Handler, ThreadingHTTPServer
from backend.website_legal import VERSION


class QuietHandler(Handler):
    def log_message(self, *_args):
        pass


class CartClient:
    def __init__(self, port):
        self.port = port
        self.origin = f'http://127.0.0.1:{port}'
        self.cookie = self.context = self.csrf = ''

    def request(self, path, body=None, *, raw=None, headers=None):
        if raw is None and body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode()
        request_headers = {'Origin': self.origin, 'Cookie': self.cookie,
                           'X-Family-Context': self.context, 'X-CSRF-Token': self.csrf}
        if raw is not None:
            request_headers['Content-Type'] = 'application/json'
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        try:
            connection.request('GET' if raw is None else 'POST', path, raw, request_headers)
            response = connection.getresponse()
            cookie = response.getheader('Set-Cookie')
            result = response.status, json.loads(response.read())
        finally:
            connection.close()
        if cookie:
            self.cookie = cookie.split(';', 1)[0]
        if 'csrf' in result[1]:
            self.csrf = result[1]['csrf']
        if 'context' in result[1]:
            self.context = result[1]['context']
        return result


class FamilyCartInvariantTests(unittest.TestCase):
    cart = '/api/family/cart'
    family = '/api/family/'
    payments = '/api/v1/payments'
    secret = 'SYNTHETIC-SECRET-FAMILY-CART-TESTS-ONLY'
    bank = '123456789'
    password = 'qa-cart-only-password'
    pin = '447266'

    def setUp(self):
        # Force an ephemeral loopback port and separate database for each case.
        scratch = Path(__file__).resolve().parents[1] / 'work' / 'family-cart-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix='invariants-', dir=scratch)
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / 'private.sqlite3'
        initialize(self.db)
        api.initialize_catalog(self.db)
        self.enterContext(patch.dict(os.environ, {
            'MAM_TOAN_PUBLIC_ORIGIN': '',
            'MAM_TOAN_SEPAY_ENABLED': '1',
            'MAM_TOAN_SEPAY_WEBHOOK_SECRET': self.secret,
            'MAM_TOAN_BANK_ID': 'ACB',
            'MAM_TOAN_BANK_ACCOUNT': self.bank,
            'MAM_TOAN_BANK_NAME': 'TAI KHOAN THU NGHIEM',
        }))
        self.enterContext(patch.object(api, '_attempts', {}))
        self.enterContext(patch.object(api, 'ITERATIONS', 1000))
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.database_path = self.db
        self.server.real_accounts = True
        self.server.family_registration_enabled = True
        self.server.arena = Arena()
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def ok(self, client, path, body=None):
        status, result = client.request(path, body)
        self.assertIn(status, (200, 201), result)
        return result

    def parent(self, *names):
        client = CartClient(self.server.server_port)
        email = f'family-cart-{secrets.token_hex(5)}@example.invalid'
        consent = {'accepted': True, 'version': VERSION, 'name': 'Phụ huynh thử',
                   'contact': email, 'role': 'parent'}
        self.ok(client, self.family + 'register', {
            'email': email, 'password': self.password, 'requestKey': secrets.token_hex(10),
            'legalConsent': consent,
        })
        state = self.ok(client, self.family + 'parent/pin/setup', {'pin': self.pin})
        self.assertEqual(state['scope'], 'parent_full')
        children = []
        for name in names:
            state = self.ok(client, self.family + 'children/add', {
                'name': name, 'grade': 5, 'birthYear': api.academic()[0] - 10, 'noPin': True,
                'requestKey': secrets.token_hex(10), 'legalConsent': consent,
            })
            children.append(state['addedChildId'])
        return client, email, children

    def second_device(self, email):
        client = CartClient(self.server.server_port)
        self.ok(client, self.family + 'login', {'email': email, 'password': self.password})
        self.ok(client, self.family + 'parent/unlock', {'pin': self.pin})
        return client

    def upsert(self, client, revision, sid, plan='VIP', period='month', **fields):
        return self.ok(client, self.cart + '/items/upsert', {
            'revision': revision, 'studentId': sid, 'plan': plan, 'period': period, **fields,
        })['cart']

    @staticmethod
    def cart_choices(cart):
        return cart['revision'], cart['total'], [
            tuple(item[key] for key in ('studentId', 'plan', 'period', 'amount', 'referralCode'))
            for item in cart['items']
        ]

    @staticmethod
    def consent(quote):
        return {'accepted': True, 'policyVersion': quote['preview']['policyVersion'],
                'quoteHash': quote['quoteHash'], 'purchaser': {
                    'name': 'Phụ huynh thử', 'contact': 'buyer@example.invalid',
                    'relationship': 'parent', 'representativeDeclared': True,
                }}

    def checkout_body(self, parent, cart):
        revision = cart['revision']
        quote = self.ok(parent, self.cart + '/preview', {'revision': revision})
        return {'revision': revision, 'checkout': self.consent(quote)}

    def webhook(self, order, event_id, **changes):
        event = {'id': event_id, 'gateway': 'ACB', 'accountNumber': self.bank,
                 'code': order['reference'], 'content': 'Thanh toan ' + order['reference'],
                 'transferType': 'in', 'transferAmount': order['amount'],
                 'referenceCode': f'BANK-{event_id}'}
        event.update(changes)
        raw = json.dumps(event, sort_keys=True).encode()
        timestamp = str(int(time.time()))
        digest = hmac.new(self.secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        client = CartClient(self.server.server_port)
        return client.request('/api/webhooks/sepay', raw=raw, headers={
            'X-SePay-Timestamp': timestamp, 'X-SePay-Signature': 'sha256=' + digest,
        })

    def order(self, client, order):
        return self.ok(client, f'{self.cart}/orders/{order["id"]}')['order']

    def account(self, sid):
        with api.connect(self.db) as db:
            return dict(db.execute('SELECT a.* FROM students s JOIN accounts a ON a.id=s.account_id WHERE s.id=?',
                                   (sid,)).fetchone())

    def grants(self, *children):
        with api.connect(self.db) as db:
            return {sid: db.execute('SELECT count(*) FROM vip_purchases WHERE account_id='
                                    '(SELECT account_id FROM students WHERE id=?)', (sid,)).fetchone()[0]
                    for sid in children}

    def receipt(self, event_id):
        with api.connect(self.db) as db:
            row = db.execute('SELECT status,reason,order_id FROM payment_receipts WHERE transaction_id=?',
                             (str(event_id),)).fetchone()
            return dict(row) if row else None

    def test_cart_isolated_across_family_child_profile_pin_expiry_and_revoked_context(self):
        a, email, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        b, _, (foreign,) = self.parent('Mầm Tây')
        self.assertIsNone(self.ok(a, self.family + 'state')['selectedChildId'])
        cart = self.upsert(a, 0, second)
        status, denied = a.request(self.cart + '/items/upsert', {
            'revision': cart['revision'], 'studentId': foreign, 'plan': 'VIP', 'period': 'month',
        })
        self.assertIn(status, (403, 404), denied)
        self.assertEqual(self.cart_choices(self.ok(a, self.cart)['cart']), self.cart_choices(cart))
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        self.assertIsNone(self.ok(a, self.family + 'state')['selectedChildId'])
        self.assertEqual(self.ok(b, self.cart)['cart']['items'], [])
        self.assertEqual(self.ok(b, self.cart + '/orders')['orders'], [])
        status, denied = a.request(self.cart + '/items/remove', {
            'revision': cart['revision'], 'studentId': second,
        }, headers={'X-CSRF-Token': ''})
        self.assertEqual(status, 403, denied)
        status, denied = a.request(self.cart + '/items/remove', {
            'revision': cart['revision'], 'studentId': second,
        }, headers={'Origin': 'https://foreign.example.invalid'})
        self.assertEqual(status, 403, denied)
        for path, body in ((f'{self.cart}/orders/{order["id"]}', None),
                           (f'{self.cart}/orders/{order["id"]}/cancel', {})):
            status, denied = b.request(path, body)
            self.assertEqual(status, 404, denied)
            self.assertNotIn(order['reference'], json.dumps(denied))

        other_device = self.second_device(email)
        stale_context = other_device.context
        self.ok(other_device, self.family + 'select', {'childId': first})
        for context in (stale_context, other_device.context):
            status, denied = other_device.request(self.cart, headers={'X-Family-Context': context})
            self.assertIn(status, (401, 403, 409), denied)
            self.assertNotIn('cart', denied)

        device = self.ok(a, self.family + 'state')['device']['id']
        with api.connect(self.db, True) as db:
            db.execute('UPDATE family_devices SET parent_seen_at=? WHERE id=?',
                       (api.stamp(api.now() - timedelta(minutes=6)), device))
        status, denied = a.request(self.cart + '/preview', {'revision': cart['revision']})
        self.assertEqual((status, denied.get('code')), (403, 'family_parent_pin_required'), denied)
        self.ok(a, self.family + 'parent/unlock', {'pin': self.pin})
        restored = self.ok(a, self.cart)
        self.assertEqual(self.cart_choices(restored['cart']), self.cart_choices(cart))
        self.assertEqual(restored['pendingOrder']['id'], order['id'])

    def test_revision_conflict_and_server_quote_revalidation_leave_no_order(self):
        a, email, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        b = self.second_device(email)
        initial = self.ok(b, self.cart)['cart']
        cart = self.upsert(a, initial['revision'], first)
        status, denied = b.request(self.cart + '/items/upsert', {
            'revision': initial['revision'], 'studentId': second, 'plan': 'VIP+', 'period': 'year',
        })
        self.assertEqual((status, denied.get('code')), (409, 'cart_revision_conflict'), denied)
        self.assertEqual(self.cart_choices(self.ok(b, self.cart)['cart']), self.cart_choices(cart))
        request = self.checkout_body(b, cart)
        invalid = {**request, 'checkout': {**request['checkout'], 'accepted': False}}
        status, denied = b.request(self.cart + '/checkout', invalid)
        self.assertEqual(status, 400, denied)
        # Same cart revision, different server prices: the reviewed quote is no longer valid.
        with patch.dict(subscriptions.PRICES['VIP'], {'month': 120000}):
            status, denied = b.request(self.cart + '/checkout', request)
        self.assertEqual(status, 409, denied)
        first_account = self.account(first)['id']
        with api.connect(self.db, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                       (api.stamp(api.now() + timedelta(days=30)), first_account))
        renewal = self.checkout_body(b, cart)
        with api.connect(self.db, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                       (api.stamp(api.now() + timedelta(days=60)), first_account))
        status, denied = b.request(self.cart + '/checkout', renewal)
        self.assertEqual(status, 409, denied)
        cart_new = self.upsert(a, cart['revision'], second, 'VIP+', 'year')
        status, denied = b.request(self.cart + '/checkout', request)
        self.assertEqual((status, denied.get('code')), (409, 'cart_revision_conflict'), denied)
        self.assertEqual(self.cart_choices(self.ok(b, self.cart)['cart']), self.cart_choices(cart_new))
        self.assertEqual(self.ok(a, self.cart + '/orders')['orders'], [])

    def test_mixed_periods_immutable_order_and_concurrent_requests_apply_once(self):
        a, email, (selected, month, year) = self.parent('Mầm Bắc', 'Mầm Nam', 'Mầm Tây')
        self.ok(a, self.family + 'parent/select', {'childId': selected})
        b = self.second_device(email)
        cart = self.upsert(a, 0, month)
        cart = self.upsert(b, cart['revision'], year, 'VIP+', 'year')
        request = self.checkout_body(a, cart)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.request, self.cart + '/checkout', request) for client in (a, b)]
            results = [future.result(timeout=30) for future in futures]
        for status, result in results:
            self.assertIn(status, (200, 201), result)
        orders = [result['order'] for _, result in results]
        order = orders[0]
        self.assertEqual(order['id'], orders[1]['id'])
        self.assertEqual(order['reference'], orders[1]['reference'])
        self.assertEqual(order['amount'], 2100000)
        self.assertEqual(parse_qs(urlsplit(order['qrUrl']).query), {
            'amount': ['2100000'], 'addInfo': [order['reference']],
            'accountName': ['TAI KHOAN THU NGHIEM'],
        })
        self.assertEqual({i['studentId'] for i in order['items']}, {month, year})
        self.assertEqual(self.ok(a, self.family + 'state')['selectedChildId'], selected)

        cart = self.upsert(b, cart['revision'], month, 'VIP+', 'month')
        cart = self.upsert(b, cart['revision'], selected)
        self.assertEqual(self.order(a, order), order)
        changed_order = self.checkout_body(b, cart)
        status, denied = b.request(self.cart + '/checkout', changed_order)
        self.assertEqual((status, denied.get('code')), (409, 'cart_pending_order'), denied)
        with patch.dict(subscriptions.PRICES['VIP+'], {'year': 2100000}):
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [pool.submit(self.webhook, order, 101, code='') for _ in range(3)]
                self.assertEqual([f.result(timeout=30)[0] for f in futures], [201, 201, 201])
        self.assertEqual(self.webhook(order, 102)[0], 201)
        self.assertEqual(self.receipt(101)['status'], 'processed')
        self.assertEqual(self.receipt(102)['reason'], 'order_paid')
        paid = self.order(a, order)
        self.assertEqual((paid['status'], paid['fulfillmentStatus']), ('paid', 'granted'))
        self.assertEqual(paid['checkoutSnapshot'], order['checkoutSnapshot'])
        self.assertEqual(paid['qrUrl'], '')
        self.assertEqual(self.grants(selected, month, year), {selected: 0, month: 1, year: 1})
        lines = {item['studentId']: item for item in paid['items']}
        for sid, months in ((month, 1), (year, 12)):
            line = lines[sid]
            expiry = subscriptions.add_months(line['subscriptionStartsAt'], months)
            self.assertEqual(line['subscriptionEndsAt'], expiry)
            self.assertEqual(self.account(sid)['vip_expires_at'], expiry)
        self.assertEqual(self.account(year)['vip_plus_expires_at'], lines[year]['subscriptionEndsAt'])
        annual_account = self.account(year)['id']
        with api.connect(self.db) as db:
            cycle = subscriptions.active_annual_cycle(db, {'account_id': annual_account})
        self.assertEqual(cycle, {'start': lines[year]['subscriptionStartsAt'], 'end': lines[year]['subscriptionEndsAt'],
                                 'limit': 3600, 'dailyLimit': 30, 'period': 'year'})
        remaining = self.ok(a, self.cart)['cart']['items']
        self.assertEqual({row['studentId']: row['plan'] for row in remaining}, {month: 'VIP+', selected: 'VIP'})
        self.assertEqual(self.ok(a, self.cart + '/checkout', request)['order']['id'], order['id'])
        self.assertEqual(len(self.ok(a, self.cart + '/orders')['orders']), 1)

    def test_second_line_storage_failure_rolls_back_first_line_and_receipt_then_retries(self):
        a, _, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        cart = self.upsert(a, 0, first)
        cart = self.upsert(a, cart['revision'], second, 'VIP+')
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        denied_account = self.account(second)['id']
        with api.connect(self.db, True) as db:
            db.execute(f"CREATE TRIGGER qa_block_purchase BEFORE INSERT ON vip_purchases WHEN NEW.account_id={denied_account} "
                       "BEGIN SELECT RAISE(ABORT, 'private QA write failure'); END")
        status, response = self.webhook(order, 201)
        self.assertEqual(status, 503, response)
        self.assertIsNone(self.receipt(201))
        self.assertEqual(self.grants(first, second), {first: 0, second: 0})
        self.assertEqual(self.order(a, order)['fulfillmentStatus'], 'pending')
        self.assertEqual(self.cart_choices(self.ok(a, self.cart)['cart']), self.cart_choices(cart))
        with api.connect(self.db, True) as db:
            db.execute('DROP TRIGGER qa_block_purchase')
        self.assertEqual(self.webhook(order, 201)[0], 201)
        self.assertEqual(self.receipt(201)['status'], 'processed')
        self.assertEqual(self.grants(first, second), {first: 1, second: 1})

    def test_payment_for_changed_beneficiary_is_held_for_review_without_partial_grants(self):
        a, _, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        cart = self.upsert(a, 0, first)
        cart = self.upsert(a, cart['revision'], second)
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        second_account = self.account(second)['id']
        with api.connect(self.db, True) as db:
            db.execute("UPDATE accounts SET status='suspended' WHERE id=?", (second_account,))
        self.assertEqual(self.webhook(order, 301)[0], 201)
        self.assertEqual(self.receipt(301)['status'], 'review')
        held = self.order(a, order)
        self.assertEqual((held['status'], held['fulfillmentStatus'], held['qrUrl']), ('review', 'review', ''))
        self.assertTrue(held['paymentReceived'])
        self.assertEqual(self.grants(first, second), {first: 0, second: 0})
        self.assertEqual(self.ok(a, self.cart)['pendingOrder']['id'], order['id'])

    def test_wrong_transfer_and_late_cancelled_transfer_do_not_grant(self):
        a, _, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        cart = self.upsert(a, 0, first)
        cart = self.upsert(a, cart['revision'], second, 'VIP+')
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        self.assertEqual(self.webhook(order, 401, accountNumber='111111111')[0], 201)
        self.assertEqual(self.receipt(401)['reason'], 'wrong_receiver')
        self.assertEqual(self.order(a, order)['fulfillmentStatus'], 'pending')
        cancelled = self.ok(a, f'{self.cart}/orders/{order["id"]}/cancel', {})['order']
        self.assertEqual((cancelled['status'], cancelled['qrUrl']), ('cancelled', ''))
        replacement = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        self.assertNotEqual(replacement['reference'], order['reference'])
        self.assertEqual(self.webhook(order, 402)[0], 201)
        self.assertEqual(self.receipt(402)['reason'], 'order_cancelled')
        self.assertEqual(self.order(a, replacement)['fulfillmentStatus'], 'pending')
        self.assertEqual(self.grants(first, second), {first: 0, second: 0})
        late = self.order(a, order)
        self.assertEqual((late['status'], late['fulfillmentStatus'], late['qrUrl']), ('review', 'cancelled', ''))
        self.assertTrue(late['paymentReceived'])

        short_amount = replacement['amount'] - 1
        self.assertEqual(self.webhook(replacement, 403, transferAmount=short_amount)[0], 201)
        self.assertEqual(self.receipt(403)['reason'], 'amount_mismatch')
        held = self.order(a, replacement)
        self.assertEqual((held['status'], held['fulfillmentStatus'], held['qrUrl']), ('review', 'review', ''))
        self.assertTrue(held['paymentReceived'])
        self.assertEqual(held['receivedAmount'], short_amount)
        status, denied = a.request(f'{self.cart}/orders/{replacement["id"]}/cancel', {})
        self.assertEqual((status, denied.get('code')), (409, 'cart_payment_received'), denied)
        self.assertEqual(self.grants(first, second), {first: 0, second: 0})

    def test_referral_rewards_each_beneficiary_once_using_captured_code(self):
        a, _, (first, second) = self.parent('Mầm Bắc', 'Mầm Nam')
        b, _, (referrer,) = self.parent('Mầm Tây')
        code = self.account(referrer)['invite_code']
        cart = self.upsert(a, 0, first, referralCode=code)
        cart = self.upsert(a, cart['revision'], second, 'VIP+', 'year', referralCode=code)
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        # Editing a candidate's current cart code must leave the accepted order alone.
        self.upsert(a, cart['revision'], first, referralCode='')
        self.assertEqual(self.webhook(order, 501)[0], 201)
        self.assertEqual(self.webhook(order, 501)[0], 201)
        self.ok(b, self.family + 'select', {'childId': referrer})
        referral = self.ok(b, '/api/v1/state')['personalSummary']['referral']
        self.assertCountEqual([(reward['tier'], reward['days']) for reward in referral['rewards']],
                              [('VIP', 7), ('VIP+', 7)])
        for reward in referral['rewards']:
            starts = datetime.fromisoformat(reward['startsAt'])
            ends = datetime.fromisoformat(reward['endsAt'])
            self.assertEqual(ends - starts, timedelta(days=7))
        current = self.ok(a, self.cart)['cart']
        status, denied = a.request(self.cart + '/items/upsert', {
            'revision': current['revision'], 'studentId': first, 'plan': 'VIP', 'period': 'month',
            'referralCode': code,
        })
        self.assertEqual(status, 409, denied)
        self.assertEqual(len(self.ok(b, '/api/v1/state')['personalSummary']['referral']['rewards']), 2)

    def test_legacy_pending_transfer_keeps_reference_and_overlaps_block_both_directions(self):
        a, _, (first, second, unrelated) = self.parent('Mầm Bắc', 'Mầm Nam', 'Mầm Tây')
        legacy_ref = 'BM' + secrets.token_hex(10).upper()
        first_account = self.account(first)['id']
        with api.connect(self.db, True) as db:
            legacy_id = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at,bank_id,bank_account,bank_name) '
                                   'VALUES(?,?,?,?,?,?,?)', (first_account, legacy_ref, 100000,
                                                           api.stamp(), 'ACB', self.bank, 'TAI KHOAN THU NGHIEM')).lastrowid
        self.ok(a, self.family + 'parent/select', {'childId': first})
        legacy = self.ok(a, f'{self.payments}/{legacy_id}')['order']
        self.assertIsNone(legacy['checkoutSnapshot'])
        self.assertEqual(legacy['reference'], legacy_ref)
        revision = self.ok(a, self.cart)['cart']['revision']
        status, response = a.request(self.cart + '/items/upsert', {
            'revision': revision, 'studentId': first, 'plan': 'VIP+', 'period': 'month',
        })
        if status in (200, 201):
            status, response = a.request(self.cart + '/preview', {'revision': response['cart']['revision']})
            if status in (200, 201):
                status, response = a.request(self.cart + '/checkout', {
                    'revision': response['preview']['revision'], 'checkout': self.consent(response),
                })
        self.assertEqual((status, response.get('code')), (409, 'cart_subscription_pending'), response)
        self.assertEqual(self.ok(a, f'{self.payments}/{legacy_id}')['order'], legacy)
        self.assertEqual(self.ok(a, self.cart + '/orders')['orders'], [])
        self.assertEqual(self.webhook(legacy, 601)[0], 201)
        self.assertEqual(self.ok(a, f'{self.payments}/{legacy_id}')['order']['status'], 'paid')
        self.assertEqual(self.grants(first, second, unrelated), {first: 1, second: 0, unrelated: 0})

        self.ok(a, self.family + 'parent/select', {'childId': second})
        single = {'plan': 'VIP', 'period': 'month'}
        quote = self.ok(a, self.payments + '/preview', single)
        revision = self.ok(a, self.cart)['cart']['revision']
        cart = self.upsert(a, revision, second, 'VIP+', 'year')
        order = self.ok(a, self.cart + '/checkout', self.checkout_body(a, cart))['order']
        self.ok(a, self.family + 'parent/select', {'childId': unrelated})
        unrelated_quote = self.ok(a, self.payments + '/preview', single)
        unrelated_order = self.ok(a, self.payments, {**single, 'checkout': self.consent(unrelated_quote)})['order']
        self.assertNotEqual(unrelated_order['reference'], order['reference'])
        self.ok(a, self.family + 'parent/select', {'childId': second})
        status, response = a.request(self.payments, {**single, 'checkout': self.consent(quote)})
        self.assertEqual((status, response.get('code')), (409, 'cart_subscription_pending'), response)
        self.assertEqual(self.order(a, order), order)
