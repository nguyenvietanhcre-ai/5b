"""Independent mixed-payment guards on disposable databases, never user data."""
import sqlite3
import unittest
from unittest.mock import patch

from backend import payments, platform_api as api
import test_family_cart as previous


class CommerceGuardTests(unittest.TestCase):
    setUp = previous.FamilyCartTests.setUp
    parent = previous.FamilyCartTests.parent
    accounts = previous.FamilyCartTests.accounts
    checkout_body = previous.FamilyCartTests.checkout_body
    webhook = previous.FamilyCartTests.webhook

    def fee(self, sid, amount=125000):
        with api.connect(self.path, True) as db:
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên QA')").lastrowid
            year = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (sid,)).fetchone()[0]
            group = db.execute("INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,schedule,curriculum) "
                               "VALUES (?,4,?,'Lớp QA học phí','Lịch QA','Nội dung QA')", (teacher, year)).lastrowid
            enrollment = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                                    (sid, group, api.stamp())).lastrowid
            account = db.execute('SELECT account_id FROM students WHERE id=?', (sid,)).fetchone()[0]
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                       (account, enrollment, api.stamp()))
            return db.execute("INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,'2026-11',?)",
                              (group, sid, amount)).lastrowid

    def add_product(self, parent, sid, kind, **fields):
        revision = parent.call('cart')['cart']['revision']
        return parent.call('cart/items/upsert', dict(revision=revision, studentId=sid, type=kind, **fields))['cart']

    def mixed(self):
        parent, children = self.parent()
        api.seed_catalog(self.path)
        fee = self.fee(children[1])
        self.add_product(parent, children[0], 'subscription', plan='VIP', period='month')
        self.add_product(parent, children[0], 'credits', sku='questions-100', quantity=1)
        self.add_product(parent, children[0], 'credits', sku='exams-10', quantity=1)
        cart = self.add_product(parent, children[1], 'tuition', feeId=fee)
        return parent, children, fee, cart

    def check_ungranted(self, parent, order, fee):
        with api.connect(self.path) as db:
            self.assertIsNone(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee,)).fetchone()[0])
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 0)
        self.assertNotEqual(parent.call(f"cart/orders/{order['id']}")['order']['fulfillmentStatus'], 'granted')

    def test_same_child_multiple_products_remove_only_one_and_fee_zero_paid_foreign_denied(self):
        parent, children, fee, cart = self.mixed()
        self.assertEqual(cart['total'], 325000)
        self.assertEqual(len(cart['items']), 4)
        line = next(i for i in cart['items'] if i['type'] == 'credits' and i['sku'] == 'questions-100')
        result = parent.call('cart/items/remove', {'revision': cart['revision'], 'lineId': line['lineId']})['cart']
        self.assertEqual(result['total'], 275000)
        self.assertEqual(len(result['items']), 3)
        self.assertTrue(any(i['type'] == 'subscription' for i in result['items']))
        with self.assertRaises(api.APIError):
            self.add_product(parent, children[0], 'tuition', feeId=fee)
        with api.connect(self.path, True) as db:
            group = db.execute('SELECT class_id FROM class_fees WHERE id=?', (fee,)).fetchone()[0]
            free_fee = db.execute("INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,'2026-12',0)",
                                  (group, children[1])).lastrowid
        with self.assertRaises(api.APIError):
            self.add_product(parent, children[1], 'tuition', feeId=free_fee)
        with api.connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET paid_at=? WHERE id=?', (api.stamp(), fee))
        with self.assertRaises(api.APIError):
            parent.call('cart/preview', {'revision': result['revision']})

    def test_fee_repricing_before_checkout_requires_new_review_without_creating_order(self):
        parent, children, fee, cart = self.mixed()
        consent = self.checkout_body(parent, cart['revision'])
        with api.connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET amount=126000 WHERE id=?', (fee,))
        with self.assertRaises(api.APIError):
            parent.call('cart/checkout', consent)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM family_cart_orders').fetchone()[0], 0)
        fresh = parent.call('cart/preview', {'revision': cart['revision']})
        self.assertEqual(fresh['preview']['total'], 326000)

    def test_fee_changes_after_qr_holds_entire_exact_transfer_for_review(self):
        parent, children, fee, cart = self.mixed()
        order = parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))['order']
        with api.connect(self.path, True) as db:
            db.execute('UPDATE class_fees SET amount=126000 WHERE id=?', (fee,))
        self.webhook(order, 91101)
        viewed = parent.call(f"cart/orders/{order['id']}")['order']
        self.assertEqual(viewed['status'], 'review')
        self.assertEqual(viewed['amount'], 325000)
        self.check_ungranted(parent, order, fee)

    def test_legacy_pending_fee_and_cart_pending_fee_block_both_directions(self):
        parent, children, fee, cart = self.mixed()
        aid = self.accounts(children)[1]
        with api.connect(self.path, True) as db:
            group = db.execute('SELECT class_id FROM class_fees WHERE id=?', (fee,)).fetchone()[0]
            legacy = db.execute("INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at,kind,purchase_type,"
                                "fee_student_id,fee_class_id,fee_month) VALUES (?,?,'BM99112233445566778800',125000,?,'tuition',"
                                "'tuition',?,?,'2026-11')", (aid, fee, api.stamp(), children[1], group)).lastrowid
        with self.assertRaises(api.APIError):
            parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))
        with api.connect(self.path, True) as db:
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?', (legacy,)).fetchone()[0], 'pending')
            db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?", (legacy,))
        order = parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))['order']
        parent.call('parent/select', {'childId': children[1]})
        try:
            checked = parent.learner('payments/preview', {'feeId': fee})
        except api.APIError as error:
            self.assertEqual(error.status, 409)
        else:
            with self.assertRaises(api.APIError):
                parent.learner('payments', {'feeId': fee, 'checkout': {
                    'accepted': True, 'policyVersion': checked['preview']['policyVersion'],
                    'quoteHash': checked['quoteHash'], 'purchaser': {'name': 'QA học phí',
                        'contact': 'fee@example.test', 'relationship': 'parent', 'representativeDeclared': True}}})
        self.check_ungranted(parent, order, fee)

    def test_last_product_storage_failure_rolls_back_subscription_fee_and_bank_receipt(self):
        parent, children, fee, cart = self.mixed()
        order = parent.call('cart/checkout', self.checkout_body(parent, cart['revision']))['order']
        original = payments.settle_fee
        def failing(*args, **kwargs):
            original(*args, **kwargs)
            raise sqlite3.IntegrityError('Private QA injected storage failure after last fee write')
        with patch.object(payments, 'settle_fee', side_effect=failing):
            with self.assertRaises(api.APIError):
                self.webhook(order, 91102)
        self.check_ungranted(parent, order, fee)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM payment_receipts WHERE transaction_id=91102').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_grants').fetchone()[0], 0)
        self.webhook(order, 91102)
        self.webhook(order, 91102)
        self.assertEqual(parent.call(f"cart/orders/{order['id']}")['order']['fulfillmentStatus'], 'granted')
        with api.connect(self.path) as db:
            self.assertIsNotNone(db.execute('SELECT paid_at FROM class_fees WHERE id=?', (fee,)).fetchone()[0])
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_grants').fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
