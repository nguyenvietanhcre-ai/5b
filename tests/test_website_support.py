"""Support ACL, safe exports and manual accounting using isolated SQLite fixtures."""
import hashlib
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from backend.database import BACKEND, initialize
from backend.platform_api import APIError, connect, stamp
from backend.website_support import dispatch


class WebsiteSupportTests(unittest.TestCase):
    def setUp(self):
        root=BACKEND.parent/'work'/'website-support-tests'
        root.mkdir(parents=True,exist_ok=True)
        self.directory=tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'test.sqlite3'
        initialize(self.path)
        with connect(self.path,True) as db:
            for i in (1,2):
                db.execute('INSERT INTO accounts(id,account_code,login_identifier,birth_year,invite_code,created_at,password_hash) VALUES(?,?,?,?,?,?,?)',
                           (i,'A'+str(i),'user'+str(i),2016,'INV'+str(i),stamp(),'DO-NOT-EXPORT-PASSWORD'))
                db.execute('INSERT INTO students(id,student_code,full_name,grade_level,account_id) VALUES(?,?,?,?,?)',(i,'S'+str(i),'Học sinh '+str(i),5,i))
                db.execute('INSERT INTO auth_sessions VALUES(?,?,?,?,?)',(hashlib.sha256(('user'+str(i)).encode()).hexdigest(),i,'csrf',stamp(),'2099-01-01T00:00:00+07:00'))
            db.execute("INSERT INTO teachers(id,full_name) VALUES(1,'Giáo viên')")
            for i,role in ((1,'admin'),(2,'teacher')):
                db.execute('INSERT INTO staff_users(id,login,full_name,password_hash,role,teacher_id,created_at) VALUES(?,?,?,?,?,?,?)',(i,role,role,'secret',role,None if i==1 else 1,stamp()))
                db.execute('INSERT INTO staff_sessions VALUES(?,?,?,?)',(hashlib.sha256(role.encode()).hexdigest(),i,'csrf','2099-01-01T00:00:00+07:00'))
            for i in (1,2):
                db.execute("INSERT INTO payment_orders(id,account_id,reference,amount,created_at,status) VALUES(?,?,?,?,?,'paid')",(i,i,'ORDER'+str(i),100000,stamp()))

    def call(self,path='',body=None,who='user1',csrf='csrf',origin='http://localhost'):
        admin=path.startswith('/admin/')
        headers={'Cookie':('5bmath_staff=' if who in ('admin','teacher') else '5bmath_session=')+who,
                 'X-CSRF-Token':csrf,'Origin':origin,'Host':'localhost'}
        handler=SimpleNamespace(headers=headers,path='/api/website'+path,server=SimpleNamespace(database_path=self.path))
        return dispatch(handler,'GET' if body is None else 'POST',handler.path.split('?')[0],body)[0]

    def ticket(self,kind='support',order=None):
        return self.call('/support/requests',{'kind':kind,'subject':'Cần hỗ trợ','message':'Nội dung thử','orderId':order})['request']

    def error(self,code,fn):
        with self.assertRaises(APIError) as caught:fn()
        self.assertEqual(caught.exception.status,code)

    def test_authenticated_owner_only(self):
        self.error(401,lambda:self.call('/support/requests',who='unknown'))
        row=self.ticket()
        self.error(404,lambda:self.call('/support/requests/'+str(row['id']),who='user2'))
        self.assertEqual(self.call('/support/requests',who='user2')['requests'],[])
        self.error(404,lambda:self.ticket('refund',2))

    def test_admin_only_and_no_student_escalation(self):
        row=self.ticket()
        self.error(403,lambda:self.call('/admin/requests',who='teacher'))
        self.error(401,lambda:self.call('/admin/requests',who='user1'))
        self.error(403,lambda:self.call('/support/requests/'+str(row['id'])+'/status',{'revision':row['revision'],'status':'resolved','message':'x'}))
        self.assertEqual(len(self.call('/admin/requests',who='admin')['requests']),1)

    def test_csrf_origin_and_required_conclusion(self):
        body={'kind':'support','subject':'A','message':'B'}
        self.error(403,lambda:self.call('/support/requests',body,csrf='wrong'))
        self.error(403,lambda:self.call('/support/requests',body,origin='https://evil.example'))
        row=self.ticket('data_delete')
        self.error(400,lambda:self.call('/admin/requests/'+str(row['id'])+'/status',{'revision':row['revision'],'status':'resolved','message':''},who='admin'))
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0],2)

    def test_status_race_has_one_winner_and_audit(self):
        row=self.ticket('consent_withdraw')
        def update(_):
            try:
                self.call('/admin/requests/'+str(row['id'])+'/status',{'revision':row['revision'],'status':'reviewing','message':'Kiểm tra phạm vi đồng ý; chưa tự thu hồi.'},who='admin')
                return 200
            except APIError as e:return e.status
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(update,range(2))),[200,409])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM staff_audit_log').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT status FROM accounts WHERE id=1').fetchone()[0],'active')

    def test_manual_refund_total_duplicate_and_paid_validation(self):
        row=self.ticket('refund',1)
        path='/admin/requests/'+str(row['id'])+'/refund'
        body={'revision':row['revision'],'amount':70000,'reference':'BANK-001','message':'Đã đối soát thủ công.'}
        row=self.call(path,body,who='admin')['request']
        self.error(400,lambda:self.call(path,{**body,'revision':row['revision'],'amount':40000,'reference':'BANK-002'},who='admin'))
        self.error(409,lambda:self.call(path,{**body,'revision':row['revision'],'amount':10000},who='admin'))
        self.error(400,lambda:self.call(path,{**body,'revision':row['revision'],'amount':True,'reference':'BANK-003'},who='admin'))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=1').fetchone()[0],'paid')
            self.assertIsNone(db.execute('SELECT vip_expires_at FROM accounts WHERE id=1').fetchone()[0])

    def test_export_ownership_and_no_credential_or_session(self):
        self.ticket()
        payload=self.call('/support/export/download')['export']
        encoded=json.dumps(payload)
        self.assertEqual(payload['account']['id'],1)
        self.assertEqual([r['id'] for r in payload['orders']],[1])
        for secret in ('password_hash','token_hash','csrf_token','DO-NOT-EXPORT-PASSWORD','user2'):
            self.assertNotIn(secret,encoded)
        self.error(401,lambda:self.call('/support/export/download',who='unknown'))

    def test_cross_ticket_refund_race_cannot_exceed_order(self):
        rows=[self.ticket('refund',1),self.ticket('refund',1)]
        def refund(item):
            i,row=item
            try:
                self.call('/admin/requests/'+str(row['id'])+'/refund',{'revision':row['revision'],'amount':60000,'reference':'RACE-'+str(i),'message':'Đã hoàn ngoài hệ thống.'},who='admin')
                return 200
            except APIError as e:return e.status
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(refund,enumerate(rows))),[200,400])
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT sum(amount) FROM website_refund_records').fetchone()[0],60000)

    def test_closed_request_and_unpaid_refund_are_rejected(self):
        row=self.ticket('refund',1)
        with connect(self.path,True) as db:db.execute("UPDATE payment_orders SET status='pending' WHERE id=1")
        self.error(400,lambda:self.call('/admin/requests/'+str(row['id'])+'/refund',{'revision':row['revision'],'amount':10000,'reference':'PENDING-1','message':'Thử'},who='admin'))
        path='/admin/requests/'+str(row['id'])+'/status'
        row=self.call(path,{'revision':row['revision'],'status':'rejected','message':'Chưa có bằng chứng thanh toán.'},who='admin')['request']
        self.error(409,lambda:self.call(path,{'revision':row['revision'],'status':'reviewing','message':'Không mở lại bằng trạng thái.'},who='admin'))
        self.error(409,lambda:self.call('/support/requests/'+str(row['id'])+'/reply',{'revision':row['revision'],'message':'Thử'}))

    def test_business_defaults_drafts_and_xss_plain_text(self):
        data=self.call('/admin/config',who='admin')
        self.assertTrue(all(v=='' for v in data['business'].values()))
        payload={**data['business'],'legal_name':'<img src=x onerror=alert(1)>','revision':data['revision'],'bctApproved':True}
        saved=self.call('/admin/config',payload,who='admin')
        self.assertNotIn('bctApproved',saved['business'])
        self.assertTrue(saved['policyDraft'])
        row=self.ticket()
        row=self.call('/support/requests/'+str(row['id'])+'/reply',{'revision':row['revision'],'message':'<script>alert(1)</script>'})['request']
        self.assertEqual(row['events'][-1]['message'],'<script>alert(1)</script>')
        source=(BACKEND.parent/'frontend'/'support-center.js').read_text(encoding='utf-8')
        self.assertNotIn('innerHTML',source)
        self.assertIn('textContent',source)
        self.call('/admin/policies',{'version':'test-draft-2','title':'T','content':'Nháp','draft':False},who='admin')
        self.assertTrue(all(r['draft']==1 for r in self.call('/admin/policies',who='admin')['policies']))

    def test_cursor_reaches_old_requests_without_leaking_other_account(self):
        with connect(self.path,True) as db:
            for i in range(202):
                db.execute("INSERT INTO website_support_requests(ticket,account_id,kind,subject,created_at,updated_at) VALUES(?,1,'support','Cũ',?,?)",('T-'+str(i),stamp(),stamp()))
            db.execute("INSERT INTO website_support_requests(ticket,account_id,kind,subject,created_at,updated_at) VALUES('PRIVATE',2,'support','Riêng',?,?)",(stamp(),stamp()))
        first=self.call('/support/requests')
        self.assertEqual(len(first['requests']),200)
        second=self.call('/support/requests?before='+str(first['nextCursor']))
        self.assertEqual(len(second['requests']),2)
        self.assertIsNone(second['nextCursor'])
        self.assertEqual(len({r['id'] for r in first['requests']+second['requests']}),202)
        self.assertNotIn('PRIVATE',json.dumps(first)+json.dumps(second))

    def test_export_includes_only_self_declared_own_consent(self):
        with connect(self.path,True) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='website_account_consents'").fetchone():
                self.skipTest('Consent migration belongs to integration module')
            db.execute("INSERT INTO website_policy_snapshots VALUES('test-consent','{}','hash',?)",(stamp(),))
            for i in (1,2):
                db.execute('INSERT INTO website_account_consents(account_id,version,representative_name,representative_contact,representative_role,accepted_at) VALUES(?,?,?,?,?,?)',(i,'test-consent','Đại diện '+str(i),'CONTACT-'+str(i),'parent',stamp()))
        result=self.call('/support/export/preview')['export']['websiteConsents']
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['representative_contact'],'CONTACT-1')
        self.assertEqual(result[0]['representativeVerification'],'self_declared')


if __name__=='__main__':unittest.main()
