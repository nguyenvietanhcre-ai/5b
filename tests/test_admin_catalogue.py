import json
import secrets
import unittest
from datetime import timedelta
from pathlib import Path
from backend.platform_api import APIError,connect,now,stamp
from backend.staff_api import create_first_admin
from backend.payments import create_order,settle_order
from backend.premium_content import catalogue,video,start_set
from backend.exam_commerce import start_order


class AdminCatalogueTests(unittest.TestCase):
    def setUp(self):
        from test_vip_plus import VipPlusTests
        from test_staff_api import StaffClient
        VipPlusTests.setUp(self)
        create_first_admin(self.path,'catalog-admin','Quản trị QA','test-password-catalogue')
        self.admin=StaffClient(self.client.server);self.admin.call('login',{'login':'catalog-admin','password':'test-password-catalogue'})

    def create(self,kind,**extra):
        body={'title':'Nội dung QA','archived':False,**extra}
        return self.admin.call('catalogue/'+kind,body)['item']

    def ids(self):
        with connect(self.path) as db:return [r[0] for r in db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' LIMIT 3")]

    def test_series_video_crud_preview_order_archive_and_cas(self):
        series=self.create('series',slug='qa-series',position=10)
        videos=[self.create('videos',title='Video '+str(i),series_slug=series['slug'],position=i,published=True,media_url='https://example.test/'+str(i)) for i in range(1,5)]
        with connect(self.path) as db:
            row=next(s for s in catalogue(db,self.session)['series'] if s['slug']=='qa-series')
            self.assertEqual([v['accessible'] for v in row['videos']],[True,True,True,False])
            with self.assertRaises(APIError):video(db,self.session,videos[-1]['id'])
        self.admin.call('catalogue/videos/move',{'identity':videos[-1]['id'],'revision':videos[-1]['revision'],'direction':'up'})
        with connect(self.path) as db:self.assertIn('url',video(db,self.session,videos[-1]['id'])['video'])
        with self.assertRaises(APIError) as err:self.admin.call('catalogue/videos',{**videos[-1],'identity':videos[-1]['id'],'title':'Stale'})
        self.assertEqual(err.exception.status,409)
        self.admin.call('catalogue/series',{'identity':series['slug'],'revision':series['revision'],'title':series['title'],'position':10,'archived':True})
        with connect(self.path) as db:
            self.assertNotIn('qa-series',[s['slug'] for s in catalogue(db,self.session)['series']])
            with self.assertRaises(APIError):video(db,self.session,videos[0]['id'])

    def test_url_publish_validation_and_colliding_position(self):
        s=self.create('series',slug='safe-series',position=10)
        self.assertTrue(self.admin.call('catalogue/series?q=NOI%20DUNG')['rows'])
        with self.assertRaises(APIError):self.create('videos',series_slug=s['slug'],media_url='javascript:alert(1)',published=False)
        with self.assertRaises(APIError):self.create('videos',series_slug=s['slug'],media_url='',published=True)
        self.create('videos',series_slug=s['slug'],media_url='',published=False,position=1)
        with self.assertRaises(APIError) as err:self.create('videos',series_slug=s['slug'],media_url='',published=False,position=1)
        self.assertEqual(err.exception.status,409)

    def test_product_edits_preserve_payment_snapshot_and_paid_access(self):
        ids=self.ids();product=self.create('products',slug='qa-product',published=True,grade=5,duration_minutes=10,price=12345,description='QA',questionIds=ids)
        with connect(self.path,True) as db:order=create_order(db,self.session,{'examProduct':product['slug']})['order']
        changed=self.admin.call('catalogue/products',{'identity':product['slug'],'revision':product['revision'],'title':'Tên mới','archived':False,'published':True,'grade':5,'duration_minutes':20,'price':99999,'description':'Mới','questionIds':ids[::-1]})['item']
        with connect(self.path,True) as db:
            old=db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone()
            self.assertEqual(old['amount'],12345);self.assertEqual(json.loads(old['exam_payload_json'])['ids'],ids)
            settle_order(db,old,'staff')
        self.admin.call('catalogue/products',{'identity':changed['slug'],'revision':changed['revision'],'title':changed['title'],'archived':True,'published':False,'grade':5,'duration_minutes':20,'price':99999,'description':'Mới','questionIds':ids[::-1]})
        with connect(self.path,True) as db:
            with self.assertRaises(APIError):create_order(db,self.session,{'examProduct':product['slug']})
            exam=start_order(db,self.session,order['id'])['exam'];self.assertEqual(len(exam['questions']),3)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0],0)

    def test_question_picker_and_publication_validation(self):
        found=self.admin.call('catalogue/questions?grade=5&page=1')
        self.assertGreater(found['total'],0);self.assertNotIn('answer',json.dumps(found))
        with self.assertRaises(APIError):self.create('products',published=True,grade=5,duration_minutes=10,price=10,questionIds=[])
        with self.assertRaises(APIError):self.create('products',published=True,grade=4,duration_minutes=10,price=10,questionIds=self.ids())
        with self.assertRaises(APIError):self.create('sets',published=True,grade=4,duration_minutes=10,track='school',school='cau-giay',questionIds=self.ids())

    def test_controls_block_new_requests_and_keep_owned_attempt(self):
        p=self.create('products',published=True,grade=5,duration_minutes=10,price=100,questionIds=self.ids())
        with connect(self.path,True) as db:
            order=create_order(db,self.session,{'examProduct':p['slug']})['order'];settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone(),'staff')
        controls=self.admin.call('catalogue/controls')['controls']
        self.admin.call('catalogue/controls',{'revision':controls['revision'],'videos_open':False,'sales_open':False,'advanced_open':False})
        with connect(self.path,True) as db:
            with self.assertRaises(APIError):create_order(db,self.session,{'examProduct':p['slug']})
            self.assertIn('exam',start_order(db,self.session,order['id']))
            with self.assertRaises(APIError):start_set(db,self.session,{'slug':'qa','requestKey':'disabled-test'})
        with self.assertRaises(APIError):self.admin.call('catalogue/controls',controls)

    def test_admin_permissions_csrf_and_management_inventory(self):
        result=self.admin.call('management');self.assertGreaterEqual(sum(len(g['items']) for g in result['groups']),12)
        self.admin.csrf='bad'
        with self.assertRaises(APIError) as error:self.create('series',position=10)
        self.assertEqual(error.exception.status,403)
        with connect(self.path,True) as db:
            teacher=db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên QA')").lastrowid
            db.execute("UPDATE staff_users SET role='teacher',teacher_id=? WHERE login='catalog-admin'",(teacher,))
        with self.assertRaises(APIError) as error:self.admin.call('management')
        self.assertEqual(error.exception.status,403)

    def test_vip_plus_notifications_are_exactly_targeted(self):
        with connect(self.path,True) as db:db.execute('UPDATE accounts SET vip_plus_expires_at=? WHERE id=?',(stamp(now()+timedelta(days=30)),self.aid))
        groups=self.admin.call('notifications')['groups'];self.assertIn('VIP+',[g['value'] for g in groups])
        self.assertEqual(self.admin.call('notifications/preview',{'audience':'VIP+'})['recipientCount'],1)
        self.assertEqual(self.admin.call('notifications/preview',{'audience':'VIP'})['recipientCount'],0)

    def test_native_draft_publish_archive_preserves_fixed_and_original_version(self):
        if not (Path(__file__).resolve().parents[1]/'pilot-inputs/manifest.json').exists():self.skipTest('Private native-library fixture; run the local release gate')
        from backend.local_pilot import LocalPilot
        root=Path(__file__).resolve().parents[1]
        pilot=LocalPilot(self.path,Path(self.tmp.name)/'pilot.sqlite3',root/'pilot-inputs',restructure_inputs=root/'restructure-inputs')
        self.client.server.local_pilot=pilot
        rows=self.admin.call('native-lessons')['rows'];self.assertEqual(len(rows),24);key=rows[0]['lessonKey']
        old=self.admin.call('native-lessons/item?key='+key)['item']
        with connect(pilot.path) as db:payload=db.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=1',(key,)).fetchone()[0]
        body={'lessonKey':key,'draftRevision':0,'baseRevision':1,'title':'Bản biên tập QA','sections':old['sections'],'action':'draft'}
        draft=self.admin.call('native-lessons',body)['item'];self.assertEqual(draft['publishedRevision'],1)
        published=self.admin.call('native-lessons',{**body,'draftRevision':draft['draftRevision'],'action':'publish'})['item'];self.assertEqual(published['publishedRevision'],2)
        with connect(pilot.path) as db:
            self.assertEqual(db.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=1',(key,)).fetchone()[0],payload)
            self.assertEqual(pilot.knowledge.current(db,key)['fixed'],json.loads(payload)['fixed'])
        with self.assertRaises(APIError):self.admin.call('native-lessons',body)
        self.admin.call('native-lessons',{'lessonKey':key,'draftRevision':published['draftRevision'],'baseRevision':2,'action':'archive'})
        with connect(pilot.path) as db:self.assertNotIn(key,[l['lessonKey'] for l in pilot.knowledge.catalogue(db,{'student_id':1})])
        self.assertGreaterEqual(len(self.admin.call('native-lessons/events')['rows']),3)
