"""Loopback UI server contract. Only synthetic fixture DB; no product handler changes."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from urllib.request import Request

from backend import platform_api as api
from backend.qa_study import create_server,close_server
from backend.server import Handler,ThreadingHTTPServer
from scripts.free_vip_smoke import HTTPClient
from scripts.mcq_fixture import fixture


class StudyQATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(dir='work');cls.folder=Path(cls.directory.name)
        values=fixture();cls.paths=[]
        for name,value in zip(('questions.json','manifest.json','sources.json'),values):
            p=cls.folder/name;p.write_text(json.dumps(value),encoding='utf-8');cls.paths.append(p)
        cls.server=create_server(cls.folder/'ui.sqlite3',*cls.paths)
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join();close_server(cls.server);cls.directory.cleanup()

    def client(self,profile=None):
        c=HTTPClient(self.base);c.call('/qa-api/bootstrap')
        if profile:c.call('/qa-api/profiles/select',{'profileId':profile})
        return c

    def exam(self,c,**kwargs):
        import secrets
        return c.call('/api/v1/exams',{'requestKey':secrets.token_hex(12),**kwargs})['exam']

    def test_guest_profile_csrf_origin_and_no_client_role_authority(self):
        c=HTTPClient(self.base)
        c.call('/qa-api/profiles/select',{'profileId':'binh'},expected=403)
        c.call('/qa-api/bootstrap');csrf=c.csrf;c.csrf='bad'
        c.call('/qa-api/profiles/select',{'profileId':'binh'},expected=403)
        c.csrf=csrf
        c.call('/qa-api/profiles/select',{'profileId':'an','membership':'VIP'},expected=400)
        c.call('/qa-api/profiles/select',{'profileId':'not-a-profile'},expected=404)
        result=c.call('/qa-api/profiles/select',{'profileId':'an'})
        self.assertEqual(result['membership'],'Free')
        self.assertEqual(c.call('/qa-api/bootstrap?role=VIP&profile=binh')['membership'],'Free')
        req=Request(self.base+'/qa-api/profiles/select',data=b'{"profileId":"binh"}',headers={
            'Origin':'http://wrong.invalid','Content-Type':'application/json','X-CSRF-Token':c.csrf})
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as caught:c.opener.open(req)
        self.assertEqual(caught.exception.code,403);caught.exception.close()

    def test_pre_submit_no_feedback_even_explicit_review_request(self):
        c=self.client('an');exam=self.exam(c,setIndex=1)
        for q in exam['questions']:self.assertFalse({'answer','solution','steps','correctChoiceId','choiceRationales'} & set(q))
        c.call('/qa-api/review/'+exam['id'],expected=403)
        labels=c.call('/qa-api/choice-labels/'+exam['id'])['labels']
        self.assertEqual(set(labels['1'][0]),{'id','text'})
        self.assertEqual(len(labels),5)
        stranger=self.client('binh');stranger.call('/qa-api/review/'+exam['id'],expected=404)
        stranger.call('/qa-api/choice-labels/'+exam['id'],expected=404)

    def test_submit_unanswered_repeat_and_text_rationale_owner(self):
        c=self.client('an');exam=self.exam(c,setIndex=1)
        c.call('/api/v1/exams/'+exam['id']+'/answers',{'position':1,'answer':'3'}) # wrong B for fixture0
        result=c.call('/api/v1/exams/'+exam['id']+'/submit',{})['exam']
        self.assertEqual(result['score'],0)
        review=c.call('/qa-api/review/'+exam['id'])
        self.assertEqual(review['questions'][0]['selectedChoiceId'],'B')
        self.assertEqual(review['questions'][0]['correctChoiceId'],'A')
        self.assertEqual(review['questions'][0]['choices'][1]['rationale'],'QA distractor')
        self.assertEqual(review['questions'][1]['outcome'],'unanswered')
        self.assertEqual(result,c.call('/api/v1/exams/'+exam['id']+'/submit',{})['exam'])
        with api.connect(self.server.database_path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM exam_answers WHERE exam_id=?',(exam['id'],)).fetchone()[0],5)

    def test_save_retry_reload_and_profile_switch_ownership(self):
        c=self.client('an');exam=self.exam(c,setIndex=1)
        for _ in range(2):c.call('/api/v1/exams/'+exam['id']+'/answers',{'position':1,'answer':'2'})
        self.assertEqual(c.call('/api/v1/exams/'+exam['id'])['exam']['answers']['1'],'2')
        old_csrf=c.csrf;c.call('/qa-api/profiles/select',{'profileId':'binh'})
        c.call('/api/v1/exams/'+exam['id'],expected=404)
        c.csrf=old_csrf;c.call('/api/v1/exams',{'requestKey':'wrong-owner-csrf','setIndex':1},expected=403)

    def test_expired_profile_reopens_issued_vip_but_not_new_vip(self):
        c=self.client('chi');state=c.call('/qa-api/bootstrap')
        self.assertEqual(state['membership'],'Free');self.assertEqual(state['vipKeys'],[])
        self.assertTrue(state['history'][0]['submitted'])
        eid=state['history'][0]['id'];exam=c.call('/api/v1/exams/'+eid)['exam']
        self.assertIn('answer',exam['questions'][0])
        self.assertEqual(len(c.call('/qa-api/review/'+eid)['questions']),5)
        c.call('/api/v1/exams',{'requestKey':'expired-vip-create','contentKeys':['qa.mcq.05']},expected=403)
        self.assertEqual(len(self.exam(c,setIndex=1)['questions']),5)

    def test_vip_uses_server_catalog_and_grading_is_server_side(self):
        c=self.client('binh');state=c.call('/qa-api/bootstrap');self.assertEqual(len(state['vipKeys']),5)
        exam=self.exam(c,contentKeys=state['vipKeys'])
        for i,q in enumerate(exam['questions'],1):c.call('/api/v1/exams/'+exam['id']+'/answers',{'position':i,'answer':str(i+6)})
        self.assertEqual(c.call('/api/v1/exams/'+exam['id']+'/submit',{})['exam']['score'],10)
        self.assertEqual(c.call('/qa-api/review/'+exam['id'])['questions'][0]['outcome'],'correct')

    def test_qa_clock_advances_and_deadline_is_relative_to_server(self):
        c=self.client('an');now=c.call('/qa-api/bootstrap')['nowMs'];time.sleep(.03)
        after=c.call('/qa-api/bootstrap')['nowMs'];self.assertGreater(after,now)
        exam=self.exam(c,setIndex=1);self.assertGreater(exam['expiresAt']-after,29*60*1000)
        self.assertLess(exam['expiresAt']-after,31*60*1000)

    def test_allowlist_no_store_and_no_private_catalog_assets(self):
        c=self.client('an')
        for path in ('/.git/config','/work/','/Learn/a.pdf','/backend/qa_study.py','/prototype-total.patch',
                     '/questions-mcq.json','/qa/../../backend/server.py','/sw.js','/api/database-demo/samples'):
            c.call(path,expected=404)
        for path,body in (('/api/v1/materials',None),('/api/v1/bot/start',{}),('/api/v1/arena',{}),('/api/v1/lessons/test/open',{}),('/api/webhooks/sepay',{})):
            c.call(path,body,expected=403)
        for path in ('/','/qa/app.js','/qa/styles.css','/qa/tokens.css','/qa/logo.svg','/qa-api/bootstrap'):
            with c.opener.open(self.base+path) as response:
                self.assertEqual(response.headers['Cache-Control'],'no-store')
                self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
                if path=='/qa/app.js':
                    body=response.read().decode();self.assertNotIn('QA distractor',body);self.assertNotIn('localStorage',body)

    def test_normal_handler_has_no_profile_switch_or_feedback_routes(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=HTTPClient(f'http://127.0.0.1:{server.server_port}')
            c.call('/qa-api/bootstrap',expected=404);c.call('/qa-api/profiles/select',{'profileId':'binh'},expected=404)
        finally:server.shutdown();thread.join();server.server_close()

    def test_main_port_refused_without_creating_database(self):
        path=self.folder/'must-not-create.sqlite3'
        with self.assertRaises(ValueError):create_server(path,*self.paths,port=8765)
        self.assertFalse(path.exists())


    def test_qa_cookie_keeps_main_placeholder_on_switch_and_logout(self):
        from http.cookiejar import Cookie
        import hashlib
        c=self.client()
        jar=next(h.cookiejar for h in c.opener.handlers if hasattr(h,'cookiejar'))
        placeholder='synthetic-main-placeholder-only'
        jar.set_cookie(Cookie(0,api.COOKIE,placeholder,None,False,'127.0.0.1',False,False,'/',True,False,None,True,None,None,{'HttpOnly':None},False))
        cookie=lambda name:next((v.value for v in jar if v.name==name),None)
        c.call('/qa-api/profiles/select',{'profileId':'an'})
        self.assertTrue(cookie(api.COOKIE)==placeholder,'Main fake cookie must remain unchanged')
        old=cookie(self.server.student_cookie_name)
        self.assertTrue(old and self.server.student_cookie_name!=api.COOKIE)
        c.call('/qa-api/profiles/select',{'profileId':'binh'})
        self.assertTrue(cookie(api.COOKIE)==placeholder,'Switch must preserve main fake cookie')
        self.assertTrue(cookie(self.server.student_cookie_name)!=old,'QA switch must rotate QA token')
        with api.connect(self.server.database_path) as db:
            self.assertIsNone(db.execute('SELECT 1 FROM auth_sessions WHERE token_hash=?',(hashlib.sha256(old.encode()).hexdigest(),)).fetchone())
        c.call('/api/v1/auth/logout',{})
        self.assertIsNone(cookie(self.server.student_cookie_name),'Logout clears QA cookie only')
        self.assertTrue(cookie(api.COOKIE)==placeholder,'QA logout must preserve main fake cookie')
        self.assertFalse(c.call('/api/v1/session')['authenticated'])
        self.assertFalse(c.call('/qa-api/bootstrap')['authenticated'])
        self.assertTrue(cookie(self.server.qa_guest_cookie_name))
        self.assertTrue(cookie(api.COOKIE)==placeholder)

    def test_main_cookie_even_with_valid_qa_token_cannot_authenticate_qa(self):
        c=self.client('an');jar=next(h.cookiejar for h in c.opener.handlers if hasattr(h,'cookiejar'))
        token=next(v.value for v in jar if v.name==self.server.student_cookie_name)
        other=HTTPClient(self.base)
        def read(cookie):
            req=Request(self.base+'/api/v1/session',headers={'Cookie':cookie})
            with other.opener.open(req) as response:return json.load(response)
        # Token was generated for a fake QA account, never from main/production.
        self.assertFalse(read(api.COOKIE+'='+token)['authenticated'])
        self.assertFalse(read(api.COOKIE+'='+token+'; '+self.server.student_cookie_name+'=invalid-placeholder')['authenticated'])
        self.assertTrue(read(api.COOKIE+'=synthetic-main; '+self.server.student_cookie_name+'='+token)['authenticated'])
        self.assertTrue(read(self.server.student_cookie_name+'='+token+'; '+api.COOKIE+'=synthetic-main')['authenticated'])

    def test_default_product_cookie_issue_read_and_revoke_remain_unchanged(self):
        from types import SimpleNamespace
        import secrets
        from backend.arena import Arena
        from test_free_vip_pilot import Client
        server=SimpleNamespace(database_path=self.server.database_path,review_upgrades=False,arena=Arena())
        self.assertEqual(api.student_cookie_name(SimpleNamespace(server=server)), '5bmath_session')
        c=Client(server)
        c.call('auth/register',{'login':'default-'+secrets.token_hex(7),'password':secrets.token_urlsafe(20),
                               'name':'Ban mau','birthYear':api.academic()[0]-10})
        self.assertEqual(c.headers['Cookie'].split('=',1)[0],'5bmath_session')
        self.assertTrue(c.call('session')['authenticated'])
        c.call('auth/logout',{})
        self.assertEqual(c.headers['Cookie'],'5bmath_session=')
        self.assertFalse(c.call('session')['authenticated'])

    def test_cookie_names_are_per_qa_port_without_global_cookie_patch(self):
        import secrets
        baseline=api.COOKIE
        other=create_server(self.folder/('other-'+secrets.token_hex(4)+'.sqlite3'),*self.paths)
        try:
            self.assertEqual(api.COOKIE,baseline)
            self.assertEqual(baseline,'5bmath_session')
            self.assertNotEqual(self.server.student_cookie_name,other.student_cookie_name)
            self.assertNotEqual(self.server.qa_guest_cookie_name,other.qa_guest_cookie_name)
            self.assertTrue(other.student_cookie_name.startswith('5bmath_qa_'))
        finally:close_server(other)
