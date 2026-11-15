import json
import unittest
from datetime import timedelta
from test_vip_plus import VipPlusTests
from backend.platform_api import APIError, connect, stamp, now
from backend.payments import create_order, settle_order, settlement_problem
from backend.exam_commerce import start_order
from backend.learning_update import membership


class ExamCommerceTests(unittest.TestCase):
    setUp = VipPlusTests.setUp

    def publish(self, db):
        ids = [r[0] for r in db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' LIMIT 3")]
        db.execute("INSERT INTO exam_products(slug,title,price,question_version_ids_json,published) VALUES ('test-exam','Đề TEST riêng',12345,?,1)",(json.dumps(ids),))

    def test_every_plan_can_buy_without_subscription_or_referral_effects(self):
        with connect(self.path,True) as db:
            self.publish(db)
            for role in ('Free','VIP','VIP+'):
                with self.subTest(role=role):
                    expiry = stamp(now()+timedelta(days=30))
                    db.execute('UPDATE accounts SET vip_expires_at=?,vip_plus_expires_at=? WHERE id=?',(None if role=='Free' else expiry,expiry if role=='VIP+' else None,self.aid))
                    order = create_order(db,self.session,{'examProduct':'test-exam','amount':1})['order']
                    self.assertEqual(order['amount'],12345)
                    self.assertEqual(order['purchase_type'],'exam')
                    self.assertNotIn('exam_payload_json',order)
                    with self.assertRaises(APIError):start_order(db,self.session,order['id'])
                    row = db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone()
                    settle_order(db,row,'staff')
                    self.assertEqual(membership(db,self.session),role)
                    self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?',(self.aid,)).fetchone()[0],0)
                    first=start_order(db,self.session,order['id'])['exam']
                    self.assertEqual(first['id'],start_order(db,self.session,order['id'])['exam']['id'])
                    self.assertEqual(len(first['questions']),3)
                    with self.assertRaises(APIError):start_order(db,{**self.session,'account_id':999999},order['id'])

    def test_price_snapshot_and_pending_subscription_replacement(self):
        with connect(self.path,True) as db:
            self.publish(db)
            vip=create_order(db,self.session,{'plan':'VIP'})['order']
            item=create_order(db,self.session,{'examProduct':'test-exam'})['order']
            self.assertNotEqual(vip['id'],item['id'])
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?',(vip['id'],)).fetchone()[0],'cancelled')
            self.assertEqual(item['id'],create_order(db,self.session,{'examProduct':'test-exam'})['order']['id'])
            db.execute("UPDATE exam_products SET price=50000 WHERE slug='test-exam'")
            old=db.execute('SELECT * FROM payment_orders WHERE id=?',(item['id'],)).fetchone()
            self.assertIsNone(settlement_problem(db,old))
            db.execute('UPDATE payment_orders SET amount=1 WHERE id=?',(item['id'],))
            self.assertEqual(settlement_problem(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(item['id'],)).fetchone()),'invalid_product')
            with self.assertRaises(APIError):create_order(db,self.session,{'examProduct':'test-exam','plan':'VIP+'})
            with self.assertRaises(APIError):create_order(db,self.session,{'examProduct':'missing'})

    def test_real_api_purchase_returns_same_owned_attempt(self):
        with connect(self.path,True) as db:self.publish(db)
        order=self.client.call('payments',{'examProduct':'test-exam'})['order']
        with connect(self.path,True) as db:settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone(),'staff')
        result=self.client.call('premium/purchases/'+str(order['id'])+'/start',{})
        self.assertEqual(len(result['exam']['questions']),3)
