"""Mixed commerce integration against disposable family account/payment databases."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from backend import exam_commerce, payments, platform_api as api, purchased_credits
import test_family_cart as fixture


class CartCommerceTest(unittest.TestCase):
    setUp = fixture.FamilyCartTests.setUp
    parent = fixture.FamilyCartTests.parent
    add = fixture.FamilyCartTests.add
    checkout_body = fixture.FamilyCartTests.checkout_body
    accounts = fixture.FamilyCartTests.accounts
    webhook = fixture.FamilyCartTests.webhook

    def fee(self, sid, aid, amount=74000, month='2026-11'):
        with api.connect(self.path, True) as db:
            ayid = db.execute('SELECT id FROM academic_years ORDER BY id DESC LIMIT 1').fetchone()[0]
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên kiểm thử')").lastrowid
            class_id = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name) VALUES (?,?,?,?)',
                                  (teacher, 5, ayid, 'Lớp kiểm thử')).lastrowid
            enrollment = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                                    (sid, class_id, api.stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                       (aid, enrollment, api.stamp()))
            return db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,?)',
                              (class_id, sid, month, amount)).lastrowid

    def exam(self, slug, price=43000, *, reverse=False):
        if not reverse:
            api.seed_catalog(self.path)
        with api.connect(self.path, True) as db:
            ids = [row[0] for row in db.execute("SELECT min(v.id) FROM question_versions v JOIN questions q ON q.id=v.question_id "
                                               'JOIN question_access_legacy a ON a.version_id=v.id '
                                               "WHERE q.grade_id=5 AND v.status='published' GROUP BY q.id ORDER BY q.id LIMIT 3")]
            self.assertEqual(len(ids), 3)
            db.execute('INSERT INTO exam_products(slug,title,price,question_version_ids_json,published) VALUES (?,?,?,?,1)',
                       (slug, 'Bộ đề ' + slug, price, json.dumps(ids[::-1] if reverse else ids)))

    def product(self, parent, sid, revision, kind, **selection):
        return parent.call('cart/items/upsert', {'revision': revision, 'studentId': sid, 'type': kind, **selection})['cart']

    def test_signed_mixed_transfer_pins_all_lines_and_grants_them_once(self):
        parent, (first, second) = self.parent()
        first_account, second_account = self.accounts([first, second])
        fee = self.fee(first, first_account)
        self.exam('cart-bought')
        with patch.object(purchased_credits, 'main_inventory', return_value=(28, 16)):
            available = parent.call('cart/catalog')
            self.assertEqual({(item['studentId'], item['unitAmount']) for item in available['creditPacks']},
                             {(first, 50000), (second, 50000)})
            self.assertEqual([(item['feeId'], item['className']) for item in available['tuition']], [(fee, 'Lớp kiểm thử')])
            self.assertEqual([(item['studentId'], item['examProduct']) for item in available['exams']], [(first, 'cart-bought')])
            cart = self.add(parent, second, 0)
            for kind, selection in (('credits', {'sku': 'questions-100', 'quantity': 2}), ('credits', {'sku': 'exams-10'}),
                                    ('tuition', {'feeId': fee}), ('exam', {'examProduct': 'cart-bought'})):
                cart = self.product(parent, first, cart['revision'], kind, **selection)
            self.assertEqual(len({item['lineId'] for item in cart['items']}), 5)
            checkout = self.checkout_body(parent, cart['revision'])
            order = parent.call('cart/checkout', checkout)['order']
            self.assertEqual(order['amount'], 367000)
            # A catalogue price edit after QR leaves that invoice and its access unchanged.
            with api.connect(self.path, True) as db:
                db.execute("UPDATE exam_products SET price=90000,revision=revision+1 WHERE slug='cart-bought'")
            self.assertEqual(parent.call('cart/checkout', checkout)['order']['amount'], 367000)
            self.assertEqual(self.webhook(order, 200, order['amount']-1), ({'success': True}, 201))
            pending = parent.call(f"cart/orders/{order['id']}")['order']
            self.assertEqual((pending['status'], pending['qrUrl']), ('review', ''))
            with api.connect(self.path) as db:
                self.assertEqual(purchased_credits.balance(db, first)['questionsRemaining'], 0)
                self.assertFalse(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee,)).fetchone()[0])
            self.assertEqual(self.webhook(order, 201), ({'success': True}, 201))
            self.assertEqual(self.webhook(order, 201), ({'success': True}, 201))
            self.assertEqual(self.webhook(order, 202), ({'success': True}, 201))
        paid = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual((paid['status'], paid['checkoutSnapshot']), ('paid', order['checkoutSnapshot']))
        self.assertTrue(all(item['fulfillmentStatus'] == 'granted' for item in paid['items']))
        self.assertEqual(parent.call('cart')['cart']['items'], [])
        purchase_id = next(item['purchaseOrderId'] for item in paid['items'] if item['type'] == 'exam')
        with api.connect(self.path, True) as db:
            self.assertEqual(purchased_credits.balance(db, first),
                             {'questionsRemaining': 200, 'examsRemaining': 10, 'expiresAt': None})
            self.assertEqual(purchased_credits.balance(db, second)['examsRemaining'], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_grants').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (second_account,)).fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM payment_receipts WHERE status='processed'").fetchone()[0], 1)
            self.assertTrue(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee,)).fetchone()[0])
            self.assertEqual(payments.order_history(db, {'account_id': first_account})['orders'], [])
            session = {'account_id': first_account, 'student_id': first, 'birth_year': api.academic()[0]-10}
            attempt = exam_commerce.start_order(db, session, purchase_id)['exam']
            self.assertEqual(len(attempt['questions']), 3)
            self.assertEqual(exam_commerce.start_order(db, session, purchase_id)['exam']['id'], attempt['id'])
            with self.assertRaises(api.APIError):
                exam_commerce.start_order(db, {**session, 'account_id': second_account, 'student_id': second}, purchase_id)

    def test_fee_reservation_and_exact_revision_prevent_double_collection(self):
        parent, (sid,) = self.parent(False)
        aid = self.accounts([sid])[0]
        fee = self.fee(sid, aid)
        session = {'account_id': aid, 'student_id': sid}
        with api.connect(self.path, True) as db:
            standalone = payments.create_order(db, session, {'feeId': fee})['order']
        with self.assertRaises(api.APIError) as blocked:
            self.product(parent, sid, 0, 'tuition', feeId=fee)
        self.assertEqual(blocked.exception.code, 'cart_fee_pending')
        with api.connect(self.path, True) as db:
            db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (standalone['id'],))
        cart = self.product(parent, sid, 0, 'tuition', feeId=fee)
        stale = self.checkout_body(parent, cart['revision'])
        with api.connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET amount=amount+1 WHERE id=?', (fee,))
            db.execute('UPDATE class_fees SET amount=amount-1 WHERE id=?', (fee,))
        with self.assertRaises(api.APIError) as changed:
            parent.call('cart/checkout', stale)
        self.assertEqual(changed.exception.status, 409)
        order = parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))['order']
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError) as blocked:
                payments.create_order(db, session, {'feeId': fee})
            self.assertEqual(blocked.exception.code, 'cart_fee_pending')
            db.execute('UPDATE class_fees SET amount=amount+5000 WHERE id=?', (fee,))
        blocked_order = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual((blocked_order['checkoutBlocked'], blocked_order['qrUrl'], blocked_order['paymentReceived']),
                         (True, '', False))
        self.assertEqual(self.webhook(order, 301), ({'success': True}, 201))
        review = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual((review['status'], review['reviewReasonCode']), ('review', 'fee_mismatch'))
        with api.connect(self.path) as db:
            self.assertFalse(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee,)).fetchone()[0])

    def test_fixed_product_duplicate_alias_and_legacy_pending_and_paid_rights(self):
        parent, (sid,) = self.parent(False)
        aid = self.accounts([sid])[0]
        self.exam('initial')
        self.exam('alias', reverse=True)
        session = {'account_id': aid, 'student_id': sid, 'birth_year': api.academic()[0]-10}
        cart = self.product(parent, sid, 0, 'exam', examProduct='initial')
        with self.assertRaises(api.APIError) as blocked:
            self.product(parent, sid, cart['revision'], 'exam', examProduct='alias')
        self.assertEqual(blocked.exception.code, 'cart_exam_duplicate')
        with api.connect(self.path, True) as db:
            old = payments.create_order(db, session, {'examProduct': 'alias'})['order']
        with self.assertRaises(api.APIError) as blocked:
            self.checkout_body(parent, cart['revision'])
        self.assertEqual(blocked.exception.code, 'cart_exam_pending')
        self.assertEqual(self.webhook(old, 401), ({'success': True}, 201))
        with self.assertRaises(api.APIError) as blocked:
            self.checkout_body(parent, cart['revision'])
        self.assertEqual(blocked.exception.code, 'cart_exam_owned')
        with api.connect(self.path, True) as db:
            self.assertEqual(len(exam_commerce.start_order(db, session, old['id'])['exam']['questions']), 3)

    def test_error_inside_fulfillment_rolls_back_subscription_credits_and_receipt(self):
        parent, (student, fee_student) = self.parent()
        account, fee_account = self.accounts([student, fee_student])
        fee = self.fee(fee_student, fee_account)
        with patch.object(purchased_credits, 'main_inventory', return_value=(12, 12)):
            cart = self.add(parent, student, 0)
            cart = self.product(parent, student, cart['revision'], 'credits', sku='exams-10')
            cart = self.product(parent, fee_student, cart['revision'], 'tuition', feeId=fee)
            order = parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))['order']
        with patch.object(payments, 'settle_fee', side_effect=sqlite3.IntegrityError('fault fixture')):
            with self.assertRaises(api.APIError) as failed:
                self.webhook(order, 501)
        self.assertEqual(failed.exception.status, 503)
        with api.connect(self.path) as db:
            self.assertEqual(purchased_credits.balance(db, student)['examsRemaining'], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (account,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM payment_receipts WHERE transaction_id=501').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT status FROM family_cart_orders WHERE id=?', (order['id'],)).fetchone()[0], 'pending')
        self.assertEqual(self.webhook(order, 501), ({'success': True}, 201))
        with api.connect(self.path) as db:
            self.assertEqual(purchased_credits.balance(db, student)['examsRemaining'], 10)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?', (account,)).fetchone()[0], 1)
