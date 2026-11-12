"""Money-to-entitlement integration, against private databases only."""

import hashlib
import hmac
import http.client
import json
import os
import secrets
import shutil
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from backend.arena import Arena
from backend.database import BACKEND, initialize
from backend.platform_api import APIError, academic, connect, seed_catalog, stamp
from backend.server import Handler, ThreadingHTTPServer
from backend.staff_api import create_first_admin
from test_platform_api import Client
from test_staff_api import StaffClient


class QuietHandler(Handler):
    def log_message(self, *_args):
        pass


class SePayPaymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = BACKEND.parent / 'work' / 'sepay-tests'
        root.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='integration-', dir=root)
        cls.path = Path(cls.directory.name) / 'payments.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.password = secrets.token_urlsafe(20)
        create_first_admin(cls.path, 'admin-sepay', 'Quản trị thử', cls.password)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.server.database_path = cls.path
        cls.server.review_upgrades = False
        cls.server.arena = Arena()
        cls.server.real_accounts = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.http = build_opener(ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.directory.cleanup()

    def setUp(self):
        self.secret = 'TEST-ONLY-SEPAY-WEBHOOK-SECRET-DO-NOT-USE-LIVE'
        self.environment = {
            'MAM_TOAN_SEPAY_ENABLED': '1',
            'MAM_TOAN_SEPAY_WEBHOOK_SECRET': self.secret,
            'MAM_TOAN_BANK_ID': 'ACB',
            'MAM_TOAN_BANK_ACCOUNT': '123456789',
            'MAM_TOAN_BANK_NAME': 'TAI KHOAN THU NGHIEM',
        }
        self.settings = patch.dict(os.environ, self.environment)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.admin = StaffClient(self.server)
        self.admin.call('login', {'login': 'admin-sepay', 'password': self.password})

    def student(self, invite='', server=None):
        client = Client(server or self.server)
        state = client.call('auth/register', {
            'login': 'sepay-' + secrets.token_hex(7),
            'password': secrets.token_urlsafe(20),
            'name': 'Học sinh thử',
            'birthYear': academic()[0] - 10,
            'inviteCode': invite,
        })
        with connect(client.server.database_path) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?',
                             (state['account']['id'],)).fetchone()[0]
        return client, state, sid

    def classroom(self, client, state, sid, amount=350000):
        with connect(self.path, True) as db:
            year = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?',
                              (sid,)).fetchone()[0]
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên thử')").lastrowid
            cid = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name) '
                             "VALUES (?,5,?,'Lớp thu học phí thử')", (teacher, year)).lastrowid
            enrollment = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                                    (sid, cid, stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                       (state['account']['id'], enrollment, stamp()))
            fee_id = db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?)',
                                (cid, sid, '2026-11', amount)).lastrowid
            other_fee = db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?)',
                                   (cid, sid, '2026-12', amount)).lastrowid
        return cid, fee_id, other_fee

    def event(self, order, **changes):
        event = {
            'id': secrets.randbelow(10**12) + 1,
            'gateway': 'ACB',
            'transactionDate': datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S'),
            'accountNumber': self.environment['MAM_TOAN_BANK_ACCOUNT'],
            'subAccount': '',
            'code': order['reference'],
            'content': order['reference'] + ' thanh toan',
            'transferType': 'in',
            'transferAmount': order['amount'],
            'description': 'Phụ huynh chuyển giúp học sinh',
            'referenceCode': 'BANK-' + secrets.token_hex(7),
            'accumulated': 999999999,
        }
        event.update(changes)
        return event

    def signed(self, event=None, *, raw=None, timestamp=None):
        raw = raw if raw is not None else json.dumps(event, ensure_ascii=False).encode('utf-8')
        timestamp = str(int(time.time()) if timestamp is None else timestamp)
        signature = hmac.new(self.secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
        return raw, {'Content-Type': 'application/json', 'X-SePay-Timestamp': timestamp,
                     'X-SePay-Signature': 'sha256=' + signature}

    def receive(self, event=None, **kwargs):
        from backend.payments import receive_webhook
        raw, headers = self.signed(event, **kwargs)
        return receive_webhook(self.path, headers, raw)

    def post(self, raw, headers=None):
        request = Request(self.base + '/api/webhooks/sepay', raw, headers or {}, method='POST')
        try:
            with self.http.open(request, timeout=20) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except HTTPError as error:
            return error.code, json.loads(error.read()), dict(error.headers)

    def snapshot(self, aid):
        with connect(self.path) as db:
            return {
                'vip': db.execute('SELECT vip_expires_at FROM accounts WHERE id=?', (aid,)).fetchone()[0],
                'purchases': db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (aid,)).fetchone()[0],
                'notices': db.execute('SELECT count(*) FROM notifications WHERE account_id=?', (aid,)).fetchone()[0],
            }

    def order_status(self, order):
        with connect(self.path) as db:
            return db.execute('SELECT status FROM payment_orders WHERE id=?', (order['id'],)).fetchone()[0]

    def receipt(self, event):
        with connect(self.path) as db:
            return db.execute('SELECT * FROM payment_receipts WHERE provider=? AND transaction_id=?',
                              ('sepay', str(event['id']))).fetchone()

    def test_signed_http_receipt_settles_correct_account_and_returns_ack_after_commit(self):
        buyer, state, _ = self.student()
        stranger, stranger_state, _ = self.student()
        order = buyer.call('payments', {})['order']
        before_stranger = self.snapshot(stranger_state['account']['id'])
        event = self.event(order)
        raw, headers = self.signed(event)
        status, payload, response_headers = self.post(raw, headers)
        self.assertEqual(status, 201)
        self.assertEqual(payload, {'success': True})
        self.assertEqual(response_headers['Cache-Control'], 'no-store')
        self.assertEqual(self.order_status(order), 'paid')
        self.assertEqual(buyer.call('session')['account']['membership'], 'VIP')
        self.assertEqual(self.snapshot(stranger_state['account']['id']), before_stranger)
        self.assertEqual(self.receipt(event)['status'], 'processed')
        self.assertEqual(self.snapshot(state['account']['id'])['purchases'], 1)

    def test_signature_missing_tampered_stale_future_and_raw_unicode_bytes(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        raw, good_headers = self.signed(event)
        before = self.snapshot(state['account']['id'])
        for body, headers in [
                (raw, {'Content-Type': 'application/json'}),
                (raw + b' ', good_headers),
                self.signed(event, timestamp=int(time.time()) - 1000),
                self.signed(event, timestamp=int(time.time()) + 1000)]:
            with self.subTest(headers=sorted(headers)):
                status, _, _ = self.post(body, headers)
                self.assertEqual(status, 401)
                self.assertEqual(self.snapshot(state['account']['id']), before)
                self.assertEqual(self.order_status(order), 'pending')
        # Re-encoding JSON after parsing would break this authentic UTF-8 signature.
        self.assertIn('Phụ huynh'.encode(), raw)
        self.assertEqual(self.post(raw, good_headers)[0], 201)

    def test_webhook_disabled_incomplete_configuration_and_short_secret_fail_closed(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        raw, headers = self.signed(event)
        before = self.snapshot(state['account']['id'])
        for values in [
            {'MAM_TOAN_SEPAY_ENABLED': '0'},
            {'MAM_TOAN_SEPAY_WEBHOOK_SECRET': ''},
            {'MAM_TOAN_SEPAY_WEBHOOK_SECRET': 'short'},
            {'MAM_TOAN_BANK_ACCOUNT': ''},
            {'MAM_TOAN_BANK_ID': ''},
            {'MAM_TOAN_BANK_NAME': ''},
        ]:
            with self.subTest(values=sorted(values)), patch.dict(os.environ, values):
                status, _, _ = self.post(raw, headers)
                self.assertIn(status, (403, 503))
        self.assertEqual(self.snapshot(state['account']['id']), before)
        self.assertIsNone(self.receipt(event))

    def test_http_rejects_wrong_content_type_malformed_json_and_large_body(self):
        for raw, content_type, expected in [
                (b'{}', 'text/plain', 415),
                (b'{broken', 'application/json', 400),
                (b'[]', 'application/json', 400),
                (b'x' * 100000, 'application/json', 413)]:
            signed_raw, headers = self.signed(raw=raw)
            headers['Content-Type'] = content_type
            self.assertEqual(self.post(signed_raw, headers)[0], expected)

    def test_http_rejects_ambiguous_framing_and_duplicate_authentication_headers(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        raw, signed_headers = self.signed(self.event(order))
        for extra, expected in [
            ([('Content-Length', str(len(raw)))], 400),
            ([('Transfer-Encoding', 'chunked')], 400),
            ([('X-SePay-Signature', signed_headers['X-SePay-Signature'])], 401),
            ([('X-SePay-Timestamp', signed_headers['X-SePay-Timestamp'])], 401),
        ]:
            with self.subTest(extra=extra[0][0]):
                connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
                try:
                    connection.putrequest('POST', '/api/webhooks/sepay')
                    connection.putheader('Content-Length', str(len(raw)))
                    for key, value in list(signed_headers.items()) + extra:
                        connection.putheader(key, value)
                    connection.endheaders(raw)
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    self.assertFalse(json.loads(response.read())['success'])
                finally:
                    connection.close()
        self.assertEqual(self.order_status(order), 'pending')
        self.assertEqual(self.snapshot(state['account']['id'])['purchases'], 0)

    def test_mock_id_zero_has_no_receipt_or_financial_effect(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        event = self.event(order, id=0)
        before = self.snapshot(state['account']['id'])
        self.assertEqual(self.receive(event), ({'success': True}, 201))
        self.assertIsNone(self.receipt(event))
        self.assertEqual(self.snapshot(state['account']['id']), before)
        self.assertEqual(self.order_status(order), 'pending')

    def test_first_purchase_rewards_saved_referrer_once_renewal_only_extends_buyer(self):
        inviter, invited_state, _ = self.student()
        buyer, state, _ = self.student(invited_state['state']['inviteCode'])
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        self.assertEqual(self.receive(event)[1], 201)
        after_buyer = self.snapshot(state['account']['id'])
        after_inviter = self.snapshot(invited_state['account']['id'])
        self.assertEqual(inviter.call('session')['account']['membership'], 'VIP')
        with connect(self.path) as db:
            relation = db.execute('SELECT * FROM account_referrals WHERE invitee_account_id=?',
                                  (state['account']['id'],)).fetchone()
            self.assertEqual(relation['inviter_account_id'], invited_state['account']['id'])
            self.assertEqual(relation['reward_status'], 'granted')
        self.receive(event)
        self.assertEqual(self.snapshot(state['account']['id']), after_buyer)
        self.assertEqual(self.snapshot(invited_state['account']['id']), after_inviter)
        renewal = buyer.call('payments', {})['order']
        self.assertNotEqual(renewal['id'], order['id'])
        self.receive(self.event(renewal))
        self.assertGreater(self.snapshot(state['account']['id'])['vip'], after_buyer['vip'])
        self.assertEqual(self.snapshot(state['account']['id'])['purchases'], 2)
        self.assertEqual(self.snapshot(invited_state['account']['id']), after_inviter)

    def test_svip_referrer_keeps_assisted_reward_policy(self):
        inviter, invited_state, sid = self.student()
        self.classroom(inviter, invited_state, sid)
        buyer, state, _ = self.student(invited_state['state']['inviteCode'])
        before = self.snapshot(invited_state['account']['id'])
        order = buyer.call('payments', {})['order']
        self.receive(self.event(order))
        self.assertEqual(buyer.call('session')['account']['membership'], 'VIP')
        self.assertEqual(inviter.call('session')['account']['membership'], 'SVip')
        self.assertEqual(self.snapshot(invited_state['account']['id'])['vip'], before['vip'])
        with connect(self.path) as db:
            referral = db.execute('SELECT reward_status,reward_granted_at FROM account_referrals WHERE invitee_account_id=?',
                                 (state['account']['id'],)).fetchone()
            self.assertEqual(referral['reward_status'], 'customer_service')
            self.assertIsNone(referral['reward_granted_at'])

    def test_tuition_settles_only_right_student_class_month_without_vip_or_referral_reward(self):
        inviter, invited_state, _ = self.student()
        buyer, state, sid = self.student(invited_state['state']['inviteCode'])
        cid, fee_id, other_fee = self.classroom(buyer, state, sid)
        other, other_state, other_sid = self.student()
        _, unrelated_fee, _ = self.classroom(other, other_state, other_sid)
        with self.assertRaises(APIError):
            other.call('payments', {'feeId': fee_id})
        before_buyer = self.snapshot(state['account']['id'])
        before_inviter = self.snapshot(invited_state['account']['id'])
        order = buyer.call('payments', {'feeId': fee_id})['order']
        self.receive(self.event(order))
        self.assertEqual(self.order_status(order), 'paid')
        self.assertEqual(self.snapshot(state['account']['id'])['purchases'], before_buyer['purchases'])
        self.assertEqual(self.snapshot(state['account']['id'])['vip'], before_buyer['vip'])
        self.assertEqual(self.snapshot(invited_state['account']['id']), before_inviter)
        fees = {fee['id']: fee for fee in buyer.call(f'classes/{cid}')['fees']}
        self.assertIsNotNone(fees[fee_id]['paid_at'])
        self.assertIsNone(fees[other_fee]['paid_at'])
        with connect(self.path) as db:
            self.assertIsNone(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (unrelated_fee,)).fetchone()[0])
            referral = db.execute('SELECT first_vip_upgraded_at FROM account_referrals WHERE invitee_account_id=?',
                                  (state['account']['id'],)).fetchone()
            self.assertIsNone(referral[0])

    def test_wrong_money_bank_account_missing_unknown_and_ambiguous_reference_need_review(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        before = self.snapshot(state['account']['id'])
        for changes in [
            {'transferAmount': order['amount'] - 1},
            {'transferAmount': order['amount'] + 1},
            {'gateway': 'Vietcombank'},
            {'accountNumber': '987654321'},
            {'code': None, 'content': 'chuyen tien cho con'},
            {'code': 'BM' + 'F' * 20, 'content': 'BM' + 'F' * 20},
            {'code': order['reference'], 'content': order['reference'] + ' BM' + 'F' * 20},
        ]:
            with self.subTest(changes=changes):
                event = self.event(order, **changes)
                self.assertEqual(self.receive(event)[1], 201)
                self.assertNotEqual(self.receipt(event)['status'], 'processed')
                self.assertEqual(self.order_status(order), 'pending')
                self.assertEqual(self.snapshot(state['account']['id']), before)

    def test_unlabelled_incoming_transfer_is_saved_for_review_including_empty_content(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        before = self.snapshot(state['account']['id'])
        for content in ('', 'dong hoc phi cho con'):
            with self.subTest(content=content):
                event = self.event(order, code=None, content=content)
                self.assertEqual(self.receive(event)[1], 201)
                self.assertEqual(self.receipt(event)['status'], 'review')
                self.assertEqual(self.order_status(order), 'pending')
                self.assertEqual(self.snapshot(state['account']['id']), before)

    def test_outgoing_invalid_amounts_and_cancelled_orders_never_fulfill(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        before = self.snapshot(state['account']['id'])
        event = self.event(order, transferType='out')
        self.assertEqual(self.receive(event)[1], 201)
        self.assertNotEqual(self.receipt(event)['status'], 'processed')
        for amount in (0, -1, 100000.0, True, '100000'):
            with self.subTest(amount=amount), self.assertRaises(APIError) as caught:
                self.receive(self.event(order, transferAmount=amount))
            self.assertEqual(caught.exception.status, 400)
        with connect(self.path, True) as db:
            db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (order['id'],))
        cancelled = self.event(order)
        self.assertEqual(self.receive(cancelled)[1], 201)
        self.assertEqual(self.receipt(cancelled)['status'], 'review')
        self.assertEqual(self.snapshot(state['account']['id']), before)

    def test_different_bank_events_for_same_paid_order_and_conflicting_replay_do_not_extend_again(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        self.receive(event)
        after = self.snapshot(state['account']['id'])
        self.receive(event)
        extra = self.event(order)
        self.receive(extra)
        self.assertEqual(self.receipt(extra)['status'], 'review')
        with self.assertRaises(APIError) as caught:
            self.receive({**event, 'transferAmount': event['transferAmount'] + 1})
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.snapshot(state['account']['id']), after)

    def test_simultaneous_webhooks_and_manual_confirmation_apply_purchase_and_reward_once(self):
        inviter, invited_state, _ = self.student()
        buyer, state, _ = self.student(invited_state['state']['inviteCode'])
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        barrier = threading.Barrier(3)

        def webhook():
            barrier.wait(timeout=10)
            return self.receive(event)[1]

        def manual():
            barrier.wait(timeout=10)
            return self.admin.call(f'payments/{order["id"]}/confirm',
                                   {'reference': order['reference'], 'amount': order['amount']})

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(webhook), pool.submit(webhook), pool.submit(manual)]
            for future in futures:
                future.result(timeout=30)
        self.assertEqual(self.snapshot(state['account']['id'])['purchases'], 1)
        self.assertEqual(self.order_status(order), 'paid')
        with connect(self.path) as db:
            referral = db.execute('SELECT reward_status,qualifying_purchase_id FROM account_referrals WHERE invitee_account_id=?',
                                  (state['account']['id'],)).fetchone()
            self.assertEqual(referral['reward_status'], 'granted')
            count = db.execute("SELECT count(*) FROM notifications WHERE account_id=? AND kind='referral_vip_reward'",
                               (invited_state['account']['id'],)).fetchone()[0]
            self.assertEqual(count, 1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_failed_purchase_rolls_back_receipt_order_and_reward_then_retry_works(self):
        inviter, invited_state, _ = self.student()
        buyer, state, _ = self.student(invited_state['state']['inviteCode'])
        order = buyer.call('payments', {})['order']
        event = self.event(order)
        before_buyer = self.snapshot(state['account']['id'])
        before_inviter = self.snapshot(invited_state['account']['id'])
        with connect(self.path, True) as db:
            db.execute("CREATE TRIGGER reject_sepay_test_purchase BEFORE INSERT ON vip_purchases "
                       "BEGIN SELECT RAISE(ABORT,'forced payment test failure'); END")
        try:
            raw, headers = self.signed(event)
            self.assertEqual(self.post(raw, headers)[0], 503)
            self.assertIsNone(self.receipt(event))
            self.assertEqual(self.order_status(order), 'pending')
            self.assertEqual(self.snapshot(state['account']['id']), before_buyer)
            self.assertEqual(self.snapshot(invited_state['account']['id']), before_inviter)
        finally:
            with connect(self.path, True) as db:
                db.execute('DROP TRIGGER reject_sepay_test_purchase')
        self.assertEqual(self.post(*self.signed(event))[0], 201)
        self.assertEqual(self.order_status(order), 'paid')

    def test_tuition_change_and_order_account_tampering_are_rechecked_at_settlement(self):
        buyer, state, sid = self.student()
        _, fee_id, _ = self.classroom(buyer, state, sid)
        order = buyer.call('payments', {'feeId': fee_id})['order']
        with connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET amount=amount+10000 WHERE id=?', (fee_id,))
        changed = self.event(order)
        self.receive(changed)
        self.assertEqual(self.receipt(changed)['status'], 'review')
        other, other_state, _ = self.student()
        with connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET amount=? WHERE id=?', (order['amount'], fee_id))
            # Simulates a corrupt/stale row: the settlement boundary must still enforce ownership.
            db.execute('UPDATE payment_orders SET account_id=? WHERE id=?', (other_state['account']['id'], order['id']))
        mismatched = self.event(order)
        self.receive(mismatched)
        self.assertEqual(self.receipt(mismatched)['status'], 'review')
        with connect(self.path) as db:
            self.assertIsNone(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee_id,)).fetchone()[0])
        self.assertEqual(self.order_status(order), 'pending')

    def test_suspended_recipient_is_sent_to_review_without_granting_paid_access(self):
        buyer, state, _ = self.student()
        order = buyer.call('payments', {})['order']
        before = self.snapshot(state['account']['id'])
        with connect(self.path, True) as db:
            db.execute("UPDATE accounts SET status='suspended' WHERE id=?", (state['account']['id'],))
        event = self.event(order)
        self.assertEqual(self.receive(event)[1], 201)
        self.assertEqual(self.receipt(event)['status'], 'review')
        self.assertEqual(self.order_status(order), 'pending')
        self.assertEqual(self.snapshot(state['account']['id']), before)

    def test_owner_only_status_and_admin_only_receipts_expose_no_private_signature_or_balance(self):
        buyer, state, _ = self.student()
        other, _, _ = self.student()
        order = buyer.call('payments', {})['order']
        self.assertEqual(buyer.call(f'payments/{order["id"]}')['order']['status'], 'pending')
        with self.assertRaises(APIError) as unauthorized:
            Client(self.server).call(f'payments/{order["id"]}')
        self.assertEqual(unauthorized.exception.status, 401)
        with self.assertRaises(APIError) as foreign:
            other.call(f'payments/{order["id"]}')
        self.assertEqual(foreign.exception.status, 404)
        for unavailable in (0, 2**63):
            with self.subTest(order_id=unavailable), self.assertRaises(APIError) as missing:
                buyer.call(f'payments/{unavailable}')
            self.assertEqual(missing.exception.status, 404)
        buyer.csrf = 'not-needed-for-read-only-status'
        self.assertEqual(buyer.call(f'payments/{order["id"]}')['order']['status'], 'pending')
        event = self.event(order)
        self.receive(event)
        response = buyer.call(f'payments/{order["id"]}')
        self.assertEqual(response['order']['status'], 'paid')
        self.assertTrue(response['order']['paid_at'])
        teacher_login = 'sepay-teacher-' + secrets.token_hex(5)
        teacher_password = secrets.token_urlsafe(20)
        self.admin.call('users', {'login': teacher_login, 'fullName': 'Giáo viên thử',
                                 'role': 'teacher', 'status': 'active', 'password': teacher_password})
        teacher = StaffClient(self.server)
        teacher.call('login', {'login': teacher_login, 'password': teacher_password})
        for staff in (StaffClient(self.server), teacher):
            with self.assertRaises(APIError):
                staff.call('payment-receipts')
        rows = self.admin.call('payment-receipts?q=' + order['reference'])
        self.assertTrue(any(row['order_id'] == order['id'] for row in rows['rows']))
        public = json.dumps({'student': response, 'admin': rows})
        for private in (self.secret, 'accumulated', 'X-SePay-Signature', 'payload_hash'):
            self.assertNotIn(private, public)

    def test_legacy_pending_order_can_be_paid_and_reinitializing_database_is_idempotent(self):
        buyer, state, _ = self.student()
        reference = '5B' + str(state['account']['id']) + secrets.token_hex(5).upper()
        with connect(self.path, True) as db:
            oid = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at) VALUES (?,?,100000,?)',
                             (state['account']['id'], reference, stamp())).lastrowid
        order = buyer.call('payments', {})['order']
        self.assertEqual(order['id'], oid)
        self.assertEqual(order['reference'], reference)
        # Fallback content must accept the complete legacy token, not a substring.
        event = self.event(order, code=None, content=reference + ' chuyen khoan')
        self.receive(event)
        self.assertEqual(self.order_status(order), 'paid')
        before = self.snapshot(state['account']['id'])
        with connect(self.path) as db:
            counts = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                      for table in ('accounts', 'students', 'payment_orders', 'payment_receipts', 'vip_purchases', 'notifications')}
        initialize(self.path)
        initialize(self.path)
        with connect(self.path) as db:
            self.assertEqual(counts, {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in counts})
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.snapshot(state['account']['id']), before)

    def test_migration_preserves_all_previous_rows_and_backfills_only_order_snapshots(self):
        migration_root = Path(self.directory.name) / ('legacy-' + secrets.token_hex(5))
        (migration_root / 'migrations').mkdir(parents=True)
        for source in (BACKEND / 'migrations').glob('*.sql'):
            if source.name < '0016':
                shutil.copy2(source, migration_root / 'migrations' / source.name)
        legacy_path = migration_root / 'legacy.sqlite3'
        with patch('backend.database.BACKEND', migration_root):
            initialize(legacy_path)
        seed_catalog(legacy_path)
        legacy_server = SimpleNamespace(database_path=legacy_path, review_upgrades=False, arena=Arena())
        _, state, sid = self.student(server=legacy_server)
        with connect(legacy_path, True) as db:
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên cũ')").lastrowid
            year = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (sid,)).fetchone()[0]
            cid = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name) '
                             "VALUES (?,5,?,'Lớp trước tích hợp')", (teacher, year)).lastrowid
            fee = db.execute("INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,'2026-10',200000)",
                             (cid, sid)).lastrowid
            old_paid = db.execute('INSERT INTO payment_orders(account_id,reference,amount,created_at,status) '
                                 "VALUES (?, '5BOLDPAID',100000,?,'paid')", (state['account']['id'], stamp())).lastrowid
            old_fee = db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at) '
                                "VALUES (?,?,'5BOLDFEE',200000,?)", (state['account']['id'], fee, stamp())).lastrowid
        with connect(legacy_path) as db:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                              "AND name NOT LIKE 'sqlite_%' AND name<>'schema_migrations'")]
            old_columns = {table: [r['name'] for r in db.execute('PRAGMA table_info("' + table + '")')]
                           for table in tables}
            old_rows = {table: [tuple(row) for row in db.execute('SELECT * FROM "' + table + '"')]
                        for table in tables}
        initialize(legacy_path)
        initialize(legacy_path)
        with connect(legacy_path) as db:
            for table in tables:
                with self.subTest(table=table):
                    selected = ','.join('"' + column + '"' for column in old_columns[table])
                    self.assertEqual(old_rows[table], [tuple(row) for row in db.execute('SELECT ' + selected + ' FROM "' + table + '"')])
            self.assertEqual(db.execute('SELECT count(*) FROM payment_receipts').fetchone()[0], 0)
            paid = db.execute('SELECT * FROM payment_orders WHERE id=?', (old_paid,)).fetchone()
            self.assertEqual((paid['kind'], paid['vip_months'], paid['amount'], paid['status']), ('vip', 1, 100000, 'paid'))
            tuition = db.execute('SELECT * FROM payment_orders WHERE id=?', (old_fee,)).fetchone()
            self.assertEqual((tuition['kind'], tuition['fee_student_id'], tuition['fee_class_id'], tuition['fee_month']),
                             ('tuition', sid, cid, '2026-10'))
            self.assertIsNone(tuition['bank_account'])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_bank_change_preserves_existing_order_destination_and_new_orders_use_new_bank(self):
        buyer, _, _ = self.student()
        order = buyer.call('payments', {})['order']
        with patch.dict(os.environ, {'MAM_TOAN_BANK_ACCOUNT': '999999999'}):
            reused = buyer.call('payments', {})['order']
            self.assertEqual(reused['id'], order['id'])
            self.assertEqual(reused['bankAccount'], '123456789')
            mismatch = self.event(order, accountNumber='999999999')
            self.receive(mismatch)
            self.assertEqual(self.receipt(mismatch)['status'], 'review')
        valid = self.event(order)
        self.receive(valid)
        self.assertEqual(self.order_status(order), 'paid')

    def test_explicit_https_website_origin_works_behind_proxy_with_secure_student_and_staff_cookies(self):
        def request(path, body, headers):
            req = Request(self.base + path, json.dumps(body).encode(),
                          {'Content-Type': 'application/json', **headers}, method='POST')
            try:
                with self.http.open(req, timeout=15) as response:
                    return response.status, json.loads(response.read()), dict(response.headers)
            except HTTPError as error:
                return error.code, json.loads(error.read()), dict(error.headers)

        trusted = {'Origin': 'https://5bmath.vn', 'Host': 'backend.internal:8000'}
        with patch.dict(os.environ, {'MAM_TOAN_PUBLIC_ORIGIN': 'https://5bmath.vn'}):
            status, student, headers = request('/api/v1/auth/register', {
                'login': 'https-sepay-' + secrets.token_hex(7), 'password': secrets.token_urlsafe(20),
                'name': 'Học sinh thử', 'birthYear': academic()[0] - 10, 'inviteCode': '',
            }, trusted)
            self.assertEqual(status, 200)
            self.assertIn('; Secure', headers['Set-Cookie'])
            self.assertIn('; HttpOnly', headers['Set-Cookie'])
            student_auth = {**trusted, 'Cookie': headers['Set-Cookie'].split(';')[0],
                            'X-CSRF-Token': student['csrf']}
            self.assertEqual(request('/api/v1/profile', {'name': 'Bạn học mới'}, student_auth)[0], 200)
            bad = {**student_auth, 'Origin': 'https://untrusted.example'}
            self.assertEqual(request('/api/v1/profile', {'name': 'Tên không lưu'}, bad)[0], 403)
            status, _, logout_headers = request('/api/v1/auth/logout', {}, student_auth)
            self.assertEqual(status, 200)
            self.assertIn('Max-Age=0', logout_headers['Set-Cookie'])
            self.assertIn('; Secure', logout_headers['Set-Cookie'])
            status, staff, staff_headers = request('/api/staff/login',
                {'login': 'admin-sepay', 'password': self.password}, trusted)
            self.assertEqual(status, 200)
            self.assertIn('; Secure', staff_headers['Set-Cookie'])
            staff_auth = {**trusted, 'Cookie': staff_headers['Set-Cookie'].split(';')[0],
                          'X-CSRF-Token': staff['csrf']}
            self.assertEqual(request('/api/staff/logout', {},
                                     {**staff_auth, 'Origin': 'https://untrusted.example'})[0], 403)
            status, _, logout_headers = request('/api/staff/logout', {}, staff_auth)
            self.assertEqual(status, 200)
            self.assertIn('; Secure', logout_headers['Set-Cookie'])
        # Explicit public origin is optional for localhost/LAN development.
        with patch.dict(os.environ, {'MAM_TOAN_PUBLIC_ORIGIN': ''}):
            local, state, _ = self.student()
            self.assertTrue(state['authenticated'])
            self.assertEqual(local.call('profile', {'name': 'Bạn học tại nhà'})['name'], 'Bạn học tại nhà')


if __name__ == '__main__':
    unittest.main()
