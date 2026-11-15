"""Wallet HTTP security/quote/receipt regressions: loopback and fake DB only."""
import json,os,secrets,socket,tempfile,threading,unittest
from pathlib import Path
from urllib.request import Request
from urllib.error import HTTPError
from backend import platform_api as api
from backend import wallet_qa as wallet
from backend.wallet_study import create_server,close_server
from backend.server import ThreadingHTTPServer,Handler
from scripts.free_vip_smoke import HTTPClient


class WalletHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=os.environ.get(getattr(cls,'input_env','FIVEBMATH_QA_INPUT_DIR'))
        if not folder:raise unittest.SkipTest('Supply unchanged ten MCQs via FIVEBMATH_QA_INPUT_DIR')
        cls.inputs=Path(folder);Path('work').mkdir(exist_ok=True);cls.temp=tempfile.TemporaryDirectory(dir='work')
        cls.server=create_server(Path(cls.temp.name)/'wallet.sqlite3',*(cls.inputs/f for f in getattr(cls,'input_files',('questions-mcq.json','sample-sets.json','sources.json'))))
        cls.base=f'http://127.0.0.1:{cls.server.server_port}';cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.thread.join();close_server(cls.server);cls.temp.cleanup()
    def client(self,profile=None):
        c=HTTPClient(self.base);c.call('/qa-api/bootstrap')
        if profile:c.call('/qa-api/profiles/select',{'profileId':profile})
        return c
    def test_guest_csrf_origin_and_catalog_injection(self):
        guest=self.client();guest.call('/qa-api/wallet',expected=401)
        guest.call('/qa-api/wallet/orders',{'requestKey':'guest-order','sku':wallet.CATALOG['sku']},expected=401)
        c=self.client('an');csrf=c.csrf;c.csrf='invalid'
        c.call('/qa-api/wallet/orders',{'requestKey':'bad-csrf-order','sku':wallet.CATALOG['sku']},expected=403);c.csrf=csrf
        req=Request(self.base+'/qa-api/wallet/orders',data=b'{}',headers={'Origin':'http://wrong.invalid','Content-Type':'application/json','X-CSRF-Token':csrf})
        with self.assertRaises(HTTPError) as caught:c.opener.open(req)
        self.assertEqual(caught.exception.code,403);caught.exception.close()
        c.call('/qa-api/wallet/orders',{'requestKey':'forged-price','sku':wallet.CATALOG['sku'],'amount':0},expected=400)
        c.call('/qa-api/wallet/mock-confirm',{'orderId':'none','success':True},expected=400)
    def test_owner_pending_fail_confirm_and_membership_stays_free(self):
        c=self.client('an');other=self.client('binh');key=secrets.token_hex(12)
        order=c.call('/qa-api/wallet/orders',{'requestKey':key,'sku':wallet.CATALOG['sku']})
        self.assertEqual(order['status'],'pending')
        other.call('/qa-api/wallet/mock-confirm',{'orderId':order['orderId']},expected=404)
        with api.connect(self.server.database_path,True) as db:db.execute("CREATE TRIGGER fail_credit_http BEFORE INSERT ON wallet_packs BEGIN SELECT RAISE(ABORT,'injected'); END")
        c.call('/qa-api/wallet/mock-confirm',{'orderId':order['orderId']},expected=503)
        self.assertEqual(next(o['status'] for o in c.call('/qa-api/wallet')['orders'] if o['orderId']==order['orderId']),'pending')
        with api.connect(self.server.database_path,True) as db:db.execute('DROP TRIGGER fail_credit_http')
        c.call('/qa-api/wallet/mock-confirm',{'orderId':order['orderId']})
        c.call('/qa-api/wallet/mock-confirm',{'orderId':order['orderId']})
        state=c.call('/qa-api/wallet');self.assertEqual(state['membership'],'Free')
        self.assertEqual(sum(p['credits'] for p in state['packs'] if p['order_id']==order['orderId']),100)
        same=c.call('/qa-api/wallet/orders',{'requestKey':key,'sku':wallet.CATALOG['sku']});self.assertEqual(same['orderId'],order['orderId'])
    def test_reconfirm_response_contains_allocation_and_no_extra_private(self):
        c=self.client('dung');boot=c.call('/qa-api/bootstrap');keys=boot['vipKeys']
        q=c.call('/qa-api/wallet/quote',{'contentKeys':keys[2:]});self.assertEqual(q['private'],1)
        q2=c.call('/qa-api/wallet/quote',{'contentKeys':keys[:2]})
        c.call('/api/v1/exams',{'requestKey':secrets.token_hex(12),'contentKeys':keys[:2],'quoteId':q2['quoteId'],'confirmWallet':False})
        denied=c.call('/api/v1/exams',{'requestKey':secrets.token_hex(12),'contentKeys':keys[2:],'quoteId':q['quoteId'],'confirmWallet':True},expected=409)
        self.assertTrue(denied['reconfirm']);self.assertEqual(denied['allocation']['private'],3)
        self.assertEqual(c.call('/qa-api/wallet')['privateRemaining'],50)
    def test_answers_feedback_owner_no_store_private_assets_and_side_paths(self):
        c=self.client('ha');other=self.client('chi');keys=c.call('/qa-api/bootstrap')['vipKeys']
        q=c.call('/qa-api/wallet/quote',{'contentKeys':keys})
        exam=c.call('/api/v1/exams',{'requestKey':secrets.token_hex(12),'contentKeys':keys,'quoteId':q['quoteId'],'confirmWallet':True})['exam']
        for item in exam['questions']:self.assertFalse(set(item)&{'answer','solution','correctChoiceId','choiceRationales'})
        receipt=c.call('/qa-api/wallet/receipts/'+exam['id']);self.assertEqual((receipt['allocation']['vip'],receipt['allocation']['private']),(2,3))
        other.call('/qa-api/wallet/receipts/'+exam['id'],expected=404)
        c.call('/qa-api/review/'+exam['id'],expected=403);other.call('/api/v1/exams/'+exam['id'],expected=404)
        other.call('/qa-api/review/'+exam['id'],expected=404)
        for f in ('/work/','/backend/wallet_qa.py','/inputs/questions-mcq.json','/prototype-total.patch','/qa/sw.js'):c.call(f,expected=404)
        for route in ('/api/v1/materials','/api/v1/lessons/test'):c.call(route,expected=403)
        for route in ('/api/v1/bot/start','/api/v1/arena','/api/webhooks/sepay'):c.call(route,{},expected=403)
        with c.opener.open(Request(self.base+'/qa-api/wallet')) as response:self.assertIn('no-store',response.headers['Cache-Control'])
    def test_ordinary_handler_has_no_qa_financial_or_switch_routes(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.database_path=self.server.database_path;server.real_accounts=True
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=HTTPClient(f'http://127.0.0.1:{server.server_port}')
            c.call('/qa-api/wallet',expected=404);c.call('/qa-api/wallet/mock-confirm',{},expected=404)
            c.call('/qa-api/profiles/select',{},expected=404)
        finally:server.shutdown();thread.join();server.server_close()
    def test_launcher_refuses_existing_database_and_main_port(self):
        paths=[self.inputs/f for f in getattr(self,'input_files',('questions-mcq.json','sample-sets.json','sources.json'))]
        with self.assertRaises(FileExistsError):create_server(self.server.database_path,*paths)
        target=Path(self.temp.name)/'never-created.sqlite3'
        with self.assertRaises(ValueError):create_server(target,*paths,port=8765)
        self.assertFalse(target.exists())
