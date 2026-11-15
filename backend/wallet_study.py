"""Wallet UI/API only on the isolated MCQ QA server; no ordinary-server routes."""
from datetime import timedelta
import json
import sqlite3
import re
from pathlib import Path
import secrets
from types import SimpleNamespace
from urllib.parse import urlsplit
from . import platform_api as api
from . import wallet_qa as wallet
from .mcq_import import load_json
from .free_vip_pilot import PilotConfig,active
from .qa_study import StudyHandler,create_server as study_server,close_server

UI=Path(__file__).resolve().parents[1]/'tools/wallet-qa'
ASSETS={'/':('index.html','text/html'),'/qa/app.js':('app.js','text/javascript'),'/qa/styles.css':('styles.css','text/css'),
        '/qa/tokens.css':('tokens.css','text/css'),'/qa/logo.svg':('logo.svg','image/svg+xml')}
POSTS={'/qa-api/wallet/quote','/qa-api/wallet/orders','/qa-api/wallet/mock-confirm','/qa-api/wallet/mock-fail'}


def authorized(handler,db):
    session=api.read_session(handler,db)
    if not session:raise api.APIError('Chọn hồ sơ QA trước.',401)
    config=active(handler,db,session)
    if not config or not config.wallet or not getattr(handler.server,'wallet_mock_enabled',False):
        raise api.APIError('Ví chỉ mở trong pilot QA được bật.',403)
    wallet.require_wallet(db)
    return session,config


class WalletHandler(StudyHandler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ASSETS:
            name,mime=ASSETS[path];self.api_headers={'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}
            self.respond(200,(UI/name).read_bytes(),mime+'; charset=utf-8');return
        if re.fullmatch(r'/qa-api/wallet/receipts/\d+',path):
            try:
                self.api_headers={}
                with api.connect(self.server.database_path) as db:
                    session,_=authorized(self,db);result=wallet.attempt_receipt(db,session,int(path.rsplit('/',1)[1]))
                self.json_response(200,result)
            except api.APIError as e:self.json_response(e.status,{'error':str(e)})
            return
        if path=='/qa-api/wallet':
            try:
                self.api_headers={}
                with api.connect(self.server.database_path) as db:
                    session,config=authorized(self,db);result=wallet.balance(db,session,config)
                self.json_response(200,result)
            except api.APIError as e:self.json_response(e.status,{'error':str(e)})
            return
        if path.startswith('/qa-api/wallet/'):
            self.json_response(404,{'error':'Chỉ mở các đường ví QA cho phép.'});return
        super().do_GET()

    def platform_request(self,method,endpoint):
        if endpoint!='/api/v1/exams' or method!='POST':return super().platform_request(method,endpoint)
        self.api_headers={}
        try:
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise api.APIError('Use JSON',415)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=8192:raise api.APIError('Invalid size',413)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise api.APIError('Use object')
            payload,status=api.dispatch(self,method,endpoint,body)
            self.json_response(status,payload)
        except wallet.QuoteChanged as e:self.json_response(409,{'error':str(e),'allocation':e.allocation,'reconfirm':True})
        except api.APIError as e:self.json_response(e.status,{'error':str(e)})
        except (ValueError,TypeError):self.json_response(400,{'error':'Dữ liệu QA không hợp lệ.'})
        except sqlite3.Error:self.json_response(503,{'error':'Chưa thể lưu; thử lại an toàn.'})

    def do_POST(self):
        path=urlsplit(self.path).path
        if path not in POSTS:
            try:super().do_POST()
            except wallet.QuoteChanged as e:self.json_response(409,{'error':str(e),'allocation':e.allocation,'reconfirm':True})
            return
        self.api_headers={}
        try:
            if not api.same_origin(self):raise api.APIError('Yêu cầu phải từ màn QA đang mở.',403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise api.APIError('Use JSON',415)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=8192:raise api.APIError('Invalid size',413)
            body=json.loads(self.rfile.read(length))
            with api.connect(self.server.database_path,True) as db:
                session,config=authorized(self,db)
                import hmac
                if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf_token']):raise api.APIError('Phiên QA cần tải lại.',403)
                if path.endswith('/quote'):result=wallet.quote(db,session,body,config)
                elif path.endswith('/orders'):result=wallet.create_order(db,session,body)
                else:result=wallet.mock_event(db,session,body,confirm=path.endswith('/mock-confirm'))
            self.json_response(200,result)
        except api.APIError as e:self.json_response(e.status,{'error':str(e)})
        except (ValueError,TypeError):self.json_response(400,{'error':'Dữ liệu mô phỏng QA không hợp lệ.'})
        except sqlite3.Error:self.json_response(503,{'error':'Chưa thể lưu mô phỏng QA; thử lại cùng yêu cầu.'})


def create_server(database,questions,manifest,sources,port=0,*,bind_host='127.0.0.1',seed_learning=True):
    server=study_server(database,questions,manifest,sources,port,'Ví câu hỏi QA — đúng 10 MCQ hiện có',seed_expired=False,bind_host=bind_host,seed_learning=seed_learning)
    try:
        server.RequestHandlerClass=WalletHandler
        mode='typed' if all(q['responseType']=='short-answer' for q in load_json(questions)['questions']) else 'choice'
        server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5,wallet=True,response_mode=mode)
        server.wallet_mock_enabled=True
        def extend_bootstrap(db,session,result):
            config=active(SimpleNamespace(server=server),db,session)
            if config and config.wallet:
                result['wallet']=wallet.balance(db,session,config);result['vipKeys']=wallet.scope_keys(db)
        server.qa_bootstrap_extension=extend_bootstrap
        fake=SimpleNamespace(server=server,headers={},api_headers={})
        with api.connect(server.database_path,True) as db:
            wallet.initialize(db,server.qa_manifest['vipSupplementContentKeys'])
            for key,name,label,day,cycle in [('dung','Dũng Biên Ngày','VIP QA 28/30, kỳ100/300; ví50',28,100),
                                            ('ha','Hà Biên Kỳ','VIP QA ngày0/30, kỳ298/300; ví50',0,298)]:
                session=api.register(fake,db,{'login':'qa-wallet-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),'name':name,'birthYear':api.academic()[0]-10})
                aid=session['account_id'];db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()+timedelta(days=60)),aid))
                server.qa_profiles[key]={'accountId':aid,'name':name,'label':label}
            for key,profile in server.qa_profiles.items():
                aid=profile['accountId'];sid=db.execute('SELECT id FROM students WHERE account_id=?',(aid,)).fetchone()[0]
                if key!='an':db.execute('INSERT INTO wallet_terms VALUES (?,?,?)',(sid,api.stamp(api.now()-timedelta(days=5)),wallet.POLICY))
                if key=='chi':db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()-timedelta(seconds=1)),aid))
                if key in ('binh','dung','ha'):
                    session={'student_id':sid,'account_id':aid}
                    order=wallet.create_order(db,session,{'requestKey':'qa-seed-pack-'+key,'sku':wallet.CATALOG['sku']})
                    receipt=wallet.mock_event(db,session,{'orderId':order['orderId']},confirm=True)['receipt']
                    if key in ('dung','ha'):
                        db.execute('INSERT INTO wallet_pack_seeds VALUES (?,50,?)',(receipt['pack_id'],'QA synthetic balance50, not 50 authored questions'))
                        budget=wallet.vip_budget(db,session,server.free_vip_pilot)
                        used=(28,100) if key=='dung' else (0,298)
                        db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(sid,budget['day'],budget['cycleStart'],*used,'QA boundary counters, not authored questions'))
            db.execute('DELETE FROM auth_sessions')
        return server
    except BaseException:close_server(server);raise
