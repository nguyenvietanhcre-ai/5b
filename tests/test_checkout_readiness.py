"""Checkout evidence and ownership on a new private database, never user data."""
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.payments import (CHECKOUT_POLICY_VERSION, checkout_preview, create_order,
                              order_history, order_status, settle_order)
from test_platform_api import Client


class CheckoutReadinessTests(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[1] / 'work' / 'checkout-tests'
        work.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'private.sqlite3'
        initialize(self.path)
        api.initialize_catalog(self.path)
        server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        client = Client(server)
        result = client.call('auth/register', {'login': 'checkout-' + secrets.token_hex(6),
            'password': secrets.token_urlsafe(20), 'name': 'Người học thử', 'birthYear': api.academic()[0] - 10})
        self.aid = result['account']['id']
        with api.connect(self.path) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (self.aid,)).fetchone()[0]
        self.session = {'account_id': self.aid, 'student_id': sid, 'birth_year': api.academic()[0] - 10}

    def body(self, db, **selection):
        preview = checkout_preview(db, self.session, selection)
        return {**selection, 'checkout': {'accepted': True, 'policyVersion': CHECKOUT_POLICY_VERSION,
            'quoteHash': preview['quoteHash'], 'purchaser': {'name': 'Phụ huynh thử',
            'contact': 'parent@example.test', 'relationship': 'parent', 'representativeDeclared': True}}}

    def test_preview_visit_and_change_selection_never_create_or_cancel_orders(self):
        with api.connect(self.path, True) as db:
            old = create_order(db, self.session, {})['order']
            for plan, period, amount in [('VIP', 'month', 100000), ('VIP', 'year', 1000000), ('VIP+', 'year', 2000000)]:
                result = checkout_preview(db, self.session, {'plan': plan, 'period': period, 'amount': 1})
                self.assertEqual(result['preview']['total'], amount)
                self.assertEqual(result['preview']['accountId'], self.aid)
                self.assertEqual(len(result['quoteHash']), 64)
            self.assertEqual(db.execute('SELECT count(*) FROM payment_orders').fetchone()[0], 1)
            self.assertEqual(order_status(db, self.session, old['id'])['order']['status'], 'pending')
            self.assertIsNone(db.execute('SELECT vip_expires_at FROM accounts WHERE id=?', (self.aid,)).fetchone()[0])

    def test_customer_requires_active_version_consent_and_matching_server_quote(self):
        with api.connect(self.path, True) as db:
            valid = self.body(db, plan='VIP', period='year')
            for invalid in ({'plan': 'VIP'}, {**valid, 'checkout': {**valid['checkout'], 'accepted': False}},
                            {**valid, 'checkout': {**valid['checkout'], 'accepted': 'true'}},
                            {**valid, 'checkout': {**valid['checkout'], 'policyVersion': 'old'}},
                            {**valid, 'period': 'month'}):
                with self.assertRaises(api.APIError):
                    create_order(db, self.session, invalid, require_checkout=True)
            self.assertEqual(db.execute('SELECT count(*) FROM payment_orders').fetchone()[0], 0)

    def test_purchaser_contact_role_and_representative_self_declaration(self):
        with api.connect(self.path, True) as db:
            valid = self.body(db)
            for changes in ({'name': ''}, {'contact': 'unknown'}, {'contact': 'a\nb@example.test'},
                            {'relationship': 'guardian-verified'}, {'representativeDeclared': False}):
                purchaser = {**valid['checkout']['purchaser'], **changes}
                with self.assertRaises(api.APIError):
                    create_order(db, self.session, {**valid, 'checkout': {**valid['checkout'], 'purchaser': purchaser}}, require_checkout=True)
            order = create_order(db, self.session, valid, require_checkout=True)['order']
            self.assertEqual(order['purchaser']['verification'], 'self-declared')
            self.assertEqual(order['accepted_policy_version'], CHECKOUT_POLICY_VERSION)

    def test_snapshot_and_retry_preserve_original_evidence(self):
        with api.connect(self.path, True) as db:
            body = self.body(db, plan='VIP+', period='year')
            first = create_order(db, self.session, body, require_checkout=True)['order']
            again = create_order(db, self.session, body, require_checkout=True)['order']
            self.assertEqual(again['id'], first['id'])
            self.assertEqual(again['checkoutSnapshot'], first['checkoutSnapshot'])
            snapshot = first['checkoutSnapshot']
            self.assertEqual((snapshot['total'], snapshot['months'], snapshot['period']), (2000000, 12, 'year'))
            self.assertTrue(any('3.600' in right for right in snapshot['rights']))
            self.assertEqual(snapshot['acceptedPolicyVersion'], CHECKOUT_POLICY_VERSION)
            self.assertEqual(snapshot['acceptedAt'], first['accepted_policy_at'])
            self.assertNotIn('checkout_snapshot_json', first)

    def test_revised_purchaser_gets_new_order_without_rewriting_old_snapshot(self):
        with api.connect(self.path, True) as db:
            body = self.body(db)
            original = create_order(db, self.session, body, require_checkout=True)['order']
            body['checkout']['purchaser']['name'] = 'Người mua khác'
            updated = create_order(db, self.session, body, require_checkout=True)['order']
            old = order_status(db, self.session, original['id'])['order']
            self.assertNotEqual(updated['id'], original['id'])
            self.assertEqual(old['status'], 'cancelled')
            self.assertEqual(old['checkoutSnapshot'], original['checkoutSnapshot'])

    def test_history_owner_only_detail_and_pagination(self):
        with api.connect(self.path, True) as db:
            body = self.body(db)
            for _ in range(23):
                order = create_order(db, self.session, body, require_checkout=True)['order']
                db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (order['id'],))
            first = order_history(db, self.session)
            second = order_history(db, self.session, {'before': [str(first['nextBefore'])]})
            self.assertEqual((len(first['orders']), len(second['orders'])), (20, 3))
            self.assertFalse(set(o['id'] for o in first['orders']) & set(o['id'] for o in second['orders']))
            stranger = {**self.session, 'account_id': self.aid + 1000}
            self.assertEqual(order_history(db, stranger)['orders'], [])
            with self.assertRaises(api.APIError) as missing:
                order_status(db, stranger, order['id'])
            self.assertEqual(missing.exception.status, 404)

    def test_invalid_history_cursor_is_rejected(self):
        with api.connect(self.path) as db:
            for value in ('-1', '0', 'nan', '9223372036854775808'):
                with self.assertRaises(api.APIError):
                    order_history(db, self.session, {'before': [value]})

    def test_legacy_orders_keep_null_consent_and_internal_call_compatibility(self):
        with api.connect(self.path, True) as db:
            legacy = create_order(db, self.session, {'plan': 'VIP', 'period': 'year'})['order']
            self.assertEqual(legacy['amount'], 1000000)
            self.assertIsNone(legacy['checkoutSnapshot'])
            self.assertIsNone(legacy['accepted_policy_at'])
            self.assertEqual(create_order(db, self.session, {'period': 'year'})['order']['id'], legacy['id'])
            fresh = create_order(db, self.session, self.body(db, period='year'), require_checkout=True)['order']
            self.assertNotEqual(fresh['id'], legacy['id'])
            old = order_status(db, self.session, legacy['id'])['order']
            self.assertIsNone(old['checkoutSnapshot'])
            self.assertEqual(old['amount'], 1000000)

    def test_annual_settlement_and_replay_do_not_duplicate_rights_or_evidence(self):
        with api.connect(self.path, True) as db:
            order = create_order(db, self.session, self.body(db, plan='VIP+', period='year'), require_checkout=True)['order']
            original_snapshot = order['checkoutSnapshot']
            row = db.execute('SELECT * FROM payment_orders WHERE id=?', (order['id'],)).fetchone()
            self.assertTrue(settle_order(db, row, 'staff'))
            row = db.execute('SELECT * FROM payment_orders WHERE id=?', (order['id'],)).fetchone()
            self.assertFalse(settle_order(db, row, 'webhook'))
            paid = order_status(db, self.session, order['id'])['order']
            self.assertEqual(paid['checkoutSnapshot'], original_snapshot)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (self.aid,)).fetchone()[0], 1)
            self.assertIsNotNone(paid['subscription_starts_at'])
            self.assertIsNotNone(paid['subscription_ends_at'])

    def test_invalid_fee_and_exam_preview_do_not_mutate_pending(self):
        with api.connect(self.path, True) as db:
            pending = create_order(db, self.session, {})['order']
            for selection in ({'feeId': True}, {'feeId': 999}, {'examProduct': 'missing'}):
                with self.assertRaises(api.APIError):
                    checkout_preview(db, self.session, selection)
            self.assertEqual(order_status(db, self.session, pending['id'])['order']['status'], 'pending')

    def test_tuition_has_exact_owned_month_total_and_consent_without_new_subscription(self):
        with api.connect(self.path, True) as db:
            year = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (self.session['student_id'],)).fetchone()[0]
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên thử')").lastrowid
            cid = db.execute("INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name) VALUES (?,5,?,'Lớp thử')", (teacher, year)).lastrowid
            enrollment = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)', (self.session['student_id'], cid, api.stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)", (self.aid, enrollment, api.stamp()))
            fid = db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?)', (cid, self.session['student_id'], '2026-11', 350000)).lastrowid
            order = create_order(db, self.session, self.body(db, feeId=fid), require_checkout=True)['order']
            self.assertEqual((order['checkoutSnapshot']['type'], order['checkoutSnapshot']['period'], order['amount']), ('tuition', '2026-11', 350000))
            row = db.execute('SELECT * FROM payment_orders WHERE id=?', (order['id'],)).fetchone()
            self.assertTrue(settle_order(db, row, 'staff'))
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 0)

    def test_exam_quote_detects_price_and_content_changes_without_leaking_answers(self):
        api.seed_catalog(self.path)
        with api.connect(self.path, True) as db:
            ids = [r[0] for r in db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' LIMIT 3")]
            db.execute("INSERT INTO exam_products(slug,title,price,question_version_ids_json,published) VALUES ('checkout-exam','Đề riêng',12345,?,1)", (json.dumps(ids),))
            body = self.body(db, examProduct='checkout-exam')
            db.execute("UPDATE exam_products SET price=20000 WHERE slug='checkout-exam'")
            with self.assertRaises(api.APIError) as stale:
                create_order(db, self.session, body, require_checkout=True)
            self.assertEqual(stale.exception.status, 409)
            self.assertEqual(db.execute('SELECT count(*) FROM payment_orders').fetchone()[0], 0)
            order = create_order(db, self.session, self.body(db, examProduct='checkout-exam'), require_checkout=True)['order']
            self.assertEqual((order['purchase_type'], order['amount']), ('exam', 20000))
            self.assertNotIn('exam_payload_json', order)
            self.assertNotIn('ids', order['checkoutSnapshot'])
            self.assertNotIn('grading_rule_json', json.dumps(order))


if __name__ == '__main__':
    unittest.main()
