import json,secrets,threading,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
from backend.database import initialize
from backend.platform_api import connect,APIError
from backend.staff_api import create_first_admin
from backend.server import Handler,ThreadingHTTPServer
from backend import site_visibility as visibility
from test_staff_api import StaffClient

class SiteVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work=Path(__file__).resolve().parents[1]/'work';work.mkdir(exist_ok=True)
        cls.tmp=TemporaryDirectory(dir=work);cls.path=Path(cls.tmp.name)/'visibility.sqlite3';initialize(cls.path)
        cls.password=secrets.token_urlsafe(20);create_first_admin(cls.path,'maintenance-admin','Admin thử',cls.password)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.database_path=cls.path
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port);cls.http=build_opener(ProxyHandler({}))
        admin=StaffClient(cls.server);admin.call('login',{'login':'maintenance-admin','password':cls.password})
        cls.teacher_password=secrets.token_urlsafe(20)
        admin.call('users',{'login':'maintenance-teacher','fullName':'Giáo viên thử','role':'teacher','status':'active','password':cls.teacher_password})
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(5);cls.tmp.cleanup()
    def setUp(self):
        with connect(self.path,True) as db:db.execute("DELETE FROM system_settings WHERE name='website_visibility'")
        self.admin=StaffClient(self.server);self.admin.call('site-visibility/login',{'login':'maintenance-admin','password':self.password})
    def request(self,path,method='GET',body=None,admin=False,headers=None):
        h={'Origin':self.base,**({'Cookie':self.admin.headers.get('Cookie',''),'X-CSRF-Token':self.admin.csrf} if admin else {}),**(headers or {})}
        if body is not None:h['Content-Type']='application/json'
        req=Request(self.base+path,None if body is None else json.dumps(body).encode(),h,method=method)
        try:r=self.http.open(req,timeout=10)
        except HTTPError as e:r=e
        with r:return r.status,dict(r.headers),r.read()
    def hide(self):return self.admin.call('site-visibility',{'hidden':True,'revision':self.admin.call('site-visibility')['visibility']['revision']})
    def test_public_default_no_settings_write(self):
        self.assertEqual(self.admin.call('site-visibility')['visibility'],{'hidden':False,'revision':0,'updatedAt':None})
        for route,status in [('/',200),('/app.js',200),('/missing-page/',404),('/api/site-visibility/check',204)]:self.assertEqual(self.request(route)[0],status)
        with connect(self.path) as db:self.assertIsNone(db.execute("SELECT 1 FROM system_settings WHERE name='website_visibility'").fetchone())
    def test_missing_storage_fails_closed_without_creating_a_database(self):
        original=self.server.database_path;missing=Path(self.tmp.name)/'missing.sqlite3'
        try:
            self.server.database_path=missing
            status,_,body=self.request('/')
            self.assertEqual(status,503);self.assertIn('Hệ thống đang được cập nhật',body.decode());self.assertFalse(missing.exists())
        finally:self.server.database_path=original
    def test_hidden_covers_all_routes_methods_queries_and_logged_in_admin(self):
        self.hide()
        for route in ['/','/index.html','/goc-hoc-tap/','/quan-tri/','/app.js','/robots.txt','/sitemap.xml','/.git/config','/missing/?next=/quan-tri/','/api/v1/session','/api/local-pilot/catalogue','/api/staff/settings','/api/grade','/api/database-demo','/api/site-visibility/check']:
            with self.subTest(route=route):
                status,h,b=self.request(route,admin=True);self.assertEqual(status,503);self.assertIn('Hệ thống đang được cập nhật',b.decode());self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(h['Retry-After'],'300');self.assertIn('noindex',h['X-Robots-Tag'])
        for method in ['POST','PUT','DELETE','PATCH','OPTIONS']:
            self.assertEqual(self.request('/api/v1/preferences',method,{'theme':'morning-garden'},admin=True)[0],503)
        status,h,b=self.request('/goc-hoc-tap/','HEAD');self.assertEqual(status,503);self.assertEqual(b,b'');self.assertGreater(int(h['Content-Length']),0)
    def test_portal_stays_available_and_can_reopen_with_existing_admin_session(self):
        self.hide();status,h,b=self.request(visibility.PORTAL)
        self.assertEqual(status,200);self.assertIn('Vận hành website',b.decode());self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy']);self.assertIn("script-src 'sha256-",h['Content-Security-Policy'])
        s,_,b=self.request(visibility.ENDPOINT+'/session',admin=True);self.assertEqual(s,200);self.assertTrue(json.loads(b)['authenticated'])
        status,_,b=self.request(visibility.ENDPOINT,admin=True);revision=json.loads(b)['visibility']['revision']
        self.assertEqual(self.request(visibility.ENDPOINT,'POST',{'hidden':False,'revision':revision},admin=True)[0],200)
        self.assertEqual(self.request('/')[0],200);self.assertEqual(self.request('/missing/')[0],404)
    def test_roles_origin_csrf_and_stale_revision(self):
        self.assertEqual(self.request(visibility.ENDPOINT,'POST',{'hidden':True,'revision':0})[0],401)
        self.assertEqual(self.request(visibility.ENDPOINT,'POST',{'hidden':True,'revision':0},admin=True,headers={'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(self.request(visibility.ENDPOINT,'POST',{'hidden':True,'revision':0},admin=True,headers={'X-CSRF-Token':'wrong'})[0],403)
        teacher=StaffClient(self.server)
        with self.assertRaises(APIError) as e:teacher.call('site-visibility/login',{'login':'maintenance-teacher','password':self.teacher_password})
        self.assertEqual(e.exception.status,403)
        teacher.call('login',{'login':'maintenance-teacher','password':self.teacher_password})
        with self.assertRaises(APIError) as e:teacher.call('site-visibility',{'hidden':True,'revision':0})
        self.assertEqual(e.exception.status,403)
        self.hide()
        with self.assertRaises(APIError) as e:self.admin.call('site-visibility',{'hidden':False,'revision':0})
        self.assertEqual(e.exception.status,409);self.assertTrue(visibility.read(self.path)['hidden'])
    def test_persistence_audit_and_no_content_or_account_mutation(self):
        with connect(self.path) as db:
            before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ['accounts','students','questions','question_versions','exams','exam_attempts','payment_orders']}
        self.hide();self.assertTrue(visibility.read(Path(str(self.path)))['hidden'])
        with connect(self.path) as db:self.assertEqual(db.execute("SELECT count(*) FROM staff_audit_log WHERE entity='website' AND action='visibility'").fetchone()[0]>0,True)
        revision=visibility.read(self.path)['revision'];self.admin.call('site-visibility',{'hidden':False,'revision':revision})
        with connect(self.path) as db:
            after={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in before}
            self.assertEqual(before,after)
    def test_invalid_types_and_health_webhook_do_not_open_public_routes(self):
        for body in [{'hidden':1,'revision':0},{'hidden':True,'revision':False},{'hidden':True,'revision':0,'role':'admin'}]:
            self.assertEqual(self.request(visibility.ENDPOINT,'POST',body,admin=True)[0],400)
        self.hide();self.assertEqual(self.request('/api/health')[0],200)
        self.assertEqual(self.request('/api/webhooks/sepay','GET')[0],503)
        self.assertEqual(self.request('/api/webhooks/sepay','POST',{})[0],401)
        self.assertEqual(self.request('/')[0],503)
