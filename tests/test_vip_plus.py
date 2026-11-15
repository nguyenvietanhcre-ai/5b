import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, academic, stamp, now, seed_catalog
from backend.payments import create_order, settle_order
from backend.learning_update import membership
from backend.premium_content import catalogue, video, require_plus, start_set
from test_platform_api import Client


class VipPlusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        initialize(self.path)
        seed_catalog(self.path)
        self.client = Client(SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena()))
        result = self.client.call('auth/register', {'login':'plus-'+secrets.token_hex(5), 'password':secrets.token_urlsafe(20), 'name':'Học sinh thử', 'birthYear':academic()[0]-10})
        self.aid = result['account']['id']
        with connect(self.path) as db:
            self.sid = db.execute('SELECT id FROM students WHERE account_id=?',(self.aid,)).fetchone()[0]
        self.session = {'account_id':self.aid,'student_id':self.sid,'birth_year':academic()[0]-10}

    def grant(self, db, plan):
        column = 'vip_plus_expires_at' if plan == 'VIP+' else 'vip_expires_at'
        db.execute('UPDATE accounts SET '+column+'=? WHERE id=?',(stamp(now()+timedelta(days=30)),self.aid))

    def test_price_idempotency_settlement_and_expiry(self):
        with connect(self.path,True) as db:
            first = create_order(db,self.session,{'plan':'VIP+'})['order']
            self.assertEqual(first['amount'],200000)
            self.assertEqual(first['subscription_plan'],'VIP+')
            self.assertEqual(first['id'],create_order(db,self.session,{'plan':'VIP+'})['order']['id'])
            self.assertEqual(membership(db,self.session),'Free')
            order = db.execute('SELECT * FROM payment_orders WHERE id=?',(first['id'],)).fetchone()
            self.assertTrue(settle_order(db,order,'staff'))
            after = db.execute('SELECT * FROM accounts WHERE id=?',(self.aid,)).fetchone()
            self.assertEqual(membership(db,self.session),'VIP+')
            self.assertFalse(settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(first['id'],)).fetchone(),'staff'))
            self.assertEqual(after['vip_plus_expires_at'],db.execute('SELECT vip_plus_expires_at FROM accounts WHERE id=?',(self.aid,)).fetchone()[0])
            db.execute('UPDATE accounts SET vip_plus_expires_at=? WHERE id=?',(stamp(now()-timedelta(seconds=1)),self.aid))
            self.assertEqual(membership(db,self.session),'VIP')

    def test_switch_pending_never_reuses_qr_or_amount(self):
        with connect(self.path,True) as db:
            vip = create_order(db,self.session,{})['order']
            plus = create_order(db,self.session,{'plan':'VIP+'})['order']
            self.assertNotEqual(vip['reference'],plus['reference'])
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?',(vip['id'],)).fetchone()[0],'cancelled')
            self.assertEqual(plus['amount'],200000)
            with self.assertRaises(APIError):create_order(db,self.session,{'plan':'fake'})

    def test_series_preview_per_series_and_no_locked_urls(self):
        with connect(self.path,True) as db:
            for slug in ('giai-de-10-phut','meo-lam-bai'):
                for index in range(1,6):
                    db.execute('INSERT INTO series_videos(series_slug,position,title,media_url,published) VALUES (?,?,?,?,?)',(slug,index,'Video '+str(index),'https://example.test/private/'+slug+str(index),int(index!=1)))
            data=catalogue(db,self.session)
            self.assertNotIn('https://',json.dumps(data))
            for item in (s for s in data['series'] if s['videos']):
                self.assertEqual([v['accessible'] for v in item['videos']],[True,True,True,False])
                self.assertIn('url',video(db,self.session,item['videos'][2]['id'])['video'])
                with self.assertRaises(APIError) as error:video(db,self.session,item['videos'][3]['id'])
                self.assertEqual(error.exception.status,403)
            self.grant(db,'VIP')
            self.assertTrue(all(v['accessible'] for s in catalogue(db,self.session)['series'] for v in s['videos']))

    def test_plus_gate_not_implied_by_vip_and_no_fake_inventory(self):
        with connect(self.path,True) as db:
            self.grant(db,'VIP')
            with self.assertRaises(APIError):require_plus(db,self.session)
            self.assertFalse(catalogue(db,self.session)['schoolAccess'])
            self.grant(db,'VIP+')
            require_plus(db,self.session)
            self.assertTrue(catalogue(db,self.session)['schoolAccess'])
            self.assertEqual(catalogue(db,self.session)['examProducts'],[])
            self.assertFalse(any(track['ready'] for track in catalogue(db,self.session)['tracks']))
            with self.assertRaises(APIError) as error:start_set(db,self.session,{'slug':'absent','requestKey':'missing-set-test'})
            self.assertEqual(error.exception.status,503)

    def test_api_catalogue_authenticated_and_video_not_found(self):
        self.assertEqual(len(self.client.call('premium')['series']),3)
        with self.assertRaises(APIError) as error:self.client.call('premium/videos/99999')
        self.assertEqual(error.exception.status,404)

    def test_curated_set_issue_replay_and_owner(self):
        with connect(self.path,True) as db:
            self.grant(db,'VIP+')
            ids=[r[0] for r in db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' LIMIT 3")]
            self.assertEqual(len(ids),3)
            db.execute("INSERT INTO premium_sets(slug,title,track,school,grade,duration_minutes,question_version_ids_json,published) VALUES ('test-set','Bộ test riêng','super-hard',NULL,5,10,?,1)",(json.dumps(ids),))
            first=start_set(db,self.session,{'slug':'test-set','requestKey':'premium-test-set'})['exam']
            again=start_set(db,self.session,{'slug':'test-set','requestKey':'premium-test-set'})['exam']
            self.assertEqual(first['id'],again['id'])
            self.assertEqual(len(first['questions']),3)
            self.assertNotIn('grading_rule',json.dumps(first))
            with self.assertRaises(APIError):start_set(db,self.session,{'slug':'other','requestKey':'premium-test-set'})
