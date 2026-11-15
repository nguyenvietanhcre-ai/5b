"""Isolated study QA only. Not imported or routed by normal backend startup."""
from datetime import datetime,timedelta,timezone
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

from . import platform_api as api
from .arena import Arena
from .learning_update import membership
from .free_vip_pilot import PilotConfig
from .mcq_import import import_package,load_json,require_qa
from .server import Handler,ThreadingHTTPServer
from scripts.import_mcq_qa import initialize_empty_qa

UI=Path(__file__).resolve().parents[1]/'tools/qa-study'
ASSETS={'/':('index.html','text/html'),'/qa/app.js':('app.js','text/javascript'),
        '/qa/styles.css':('styles.css','text/css'),'/qa/tokens.css':('tokens.css','text/css'),'/qa/logo.svg':('logo.svg','image/svg+xml')}
QA_COOKIE_PREFIX='5bmath_qa'


class QAClock:
    def __init__(self,anchor): self.anchor=anchor;self.start=time.monotonic()
    def now(self): return self.anchor+timedelta(seconds=time.monotonic()-self.start)


def review_payload(db,session,exam_id):
    attempt=api.owned_attempt(db,session,exam_id)
    if attempt['status']!='submitted':raise api.APIError('Chỉ xem giải thích sau khi nộp bài.',403)
    result=[];typed=attempt['response_mode']=='typed'
    for row in db.execute('SELECT i.position,i.options_json,v.grading_rule_json,m.metadata_json,d.answer,a.awarded_points '
        'FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id JOIN mcq_versions m ON m.version_id=v.id '
        'LEFT JOIN exam_draft_answers d ON d.attempt_id=? AND d.position=i.position '
        'LEFT JOIN exam_answers a ON a.attempt_id=? AND a.position=i.position '
        'WHERE i.exam_id=? ORDER BY i.position',(attempt['id'],attempt['id'],exam_id)):
        metadata=json.loads(row['metadata_json']);rule=json.loads(row['grading_rule_json']);selected=row['answer'] or ''
        if row['awarded_points'] is None:raise api.APIError('Chưa thể đối chiếu điểm đã lưu.',503)
        item={'position':row['position'],'selectedText':selected,'correctText':rule['answer'],
              'outcome':'unanswered' if not selected.strip() else 'correct' if row['awarded_points'] else 'incorrect',
              'answerExplanation':metadata['answerExplanation'],'solutionSteps':metadata['solutionSteps'],
              'revision':metadata['revision'],'responseMode':attempt['response_mode']}
        if typed:item['answerKind']=rule.get('answerKind','auto')
        else:
            choices=metadata['choices'];text_by_id={c['id']:c['text'] for c in choices}
            if set(json.loads(row['options_json']))!=set(text_by_id.values()) or text_by_id[metadata['correctChoiceId']]!=rule['answer']:
                raise api.APIError('Chưa thể đối chiếu giải thích phiên bản cũ.',503)
            item.update(correctChoiceId=metadata['correctChoiceId'],selectedChoiceId=next((c['id'] for c in choices if c['text']==selected),None),
                        choices=[{'id':c['id'],'text':c['text'],'rationale':metadata['choiceRationales'][c['id']]} for c in choices])
        result.append(item)
    if not result:raise api.APIError('Bài chưa có giải thích QA.',503)
    return {'examId':str(exam_id),'responseMode':attempt['response_mode'],'questions':result,
            'notice':'Đáp án và lời giải của đúng phiên bản đã làm; không kết luận nguyên nhân chỉ từ câu sai.'}


def bootstrap(handler,db,session):
    profiles=[{'id':key,'name':value['name'],'label':value['label']} for key,value in handler.server.qa_profiles.items()]
    result={'authenticated':bool(session),'profiles':profiles,'packageLabel':handler.server.qa_package_label,
        'nowMs':int(api.now().timestamp()*1000),'notice':'Bản thử QA — dữ liệu giả, học liệu chưa duyệt độc lập'}
    if session:
        selected=next((key for key,v in handler.server.qa_profiles.items() if v['accountId']==session['account_id']),None)
        result.update(csrf=session['csrf_token'],profileId=selected,membership=membership(db,session))
        result['vipKeys']=handler.server.qa_manifest['vipSupplementContentKeys'] if membership(db,session)=='VIP' else []
        result['history']=[{'id':str(r['exam_id']),'title':r['title'],'submitted':r['status']=='submitted'} for r in db.execute(
            'SELECT a.exam_id,a.status,e.title FROM exam_attempts a JOIN exams e ON e.id=a.exam_id WHERE a.student_id=? ORDER BY a.id DESC LIMIT 30',
            (session['student_id'],))]
    else:
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        with handler.server.qa_guest_lock:
            # Bounded process-only guest CSRF registry; never a student login token.
            now=time.monotonic()
            handler.server.qa_guests={k:v for k,v in handler.server.qa_guests.items() if v[1]>now}
            if len(handler.server.qa_guests)>=128:handler.server.qa_guests.pop(next(iter(handler.server.qa_guests)))
            handler.server.qa_guests[hashlib.sha256(token.encode()).hexdigest()]=(csrf,now+3600)
        handler.api_headers={'Set-Cookie':api.session_cookie(handler.server.qa_guest_cookie_name,token,3600)}
        result['csrf']=csrf
    extension=getattr(handler.server,'qa_bootstrap_extension',None)
    if session and callable(extension):extension(db,session,result)
    return result


class StudyHandler(Handler):
    def json_response(self,status,payload):
        self.api_headers={**getattr(self,'api_headers',{}),'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}
        super().json_response(status,payload)

    def do_GET(self):
        path=urlsplit(self.path).path
        self.api_headers={}
        if path in ASSETS:
            name,mime=ASSETS[path]
            self.api_headers={'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}
            self.respond(200,(UI/name).read_bytes(),mime+'; charset=utf-8');return
        if path.startswith('/qa-api/'):
            try:
                with api.connect(self.server.database_path) as db:
                    require_qa(db);session=api.read_session(self,db)
                    if path=='/qa-api/bootstrap':result=bootstrap(self,db,session)
                    elif re.fullmatch(r'/qa-api/choice-labels/\d+',path):
                        if not session:raise api.APIError('Em hãy chọn hồ sơ thử trước.',401)
                        eid=int(path.rsplit('/',1)[1]);attempt=api.owned_attempt(db,session,eid)
                        if attempt['response_mode']=='typed':
                            self.json_response(200,{'labels':{}});return
                        labels={}
                        for item in db.execute('SELECT i.position,i.options_json,m.metadata_json FROM exam_items i JOIN mcq_versions m ON m.version_id=i.question_version_id WHERE i.exam_id=?',(eid,)):
                            choices=json.loads(item['metadata_json'])['choices'];ids={c['text']:c['id'] for c in choices}
                            labels[str(item['position'])]=[{'id':ids[t],'text':t} for t in json.loads(item['options_json'])]
                        result={'labels':labels}
                    elif re.fullmatch(r'/qa-api/review/\d+',path):
                        if not session:raise api.APIError('Em hãy chọn hồ sơ thử trước.',401)
                        result=review_payload(db,session,int(path.rsplit('/',1)[1]))
                    else:raise api.APIError('Không tìm thấy đường dẫn QA.',404)
                self.json_response(200,result)
            except api.APIError as error:self.json_response(error.status,{'error':str(error)})
            return
        if path=='/api/v1/materials' or path.startswith('/api/v1/lessons/'):
            self.json_response(403,{'error':'Đường nội dung chưa mở trên QA.'});return
        if path=='/api/health' or path in ('/api/v1/session','/api/v1/state','/api/v1/pilot/sets') or re.fullmatch(r'/api/v1/exams/\d+',path):
            super().do_GET();return
        self.json_response(404,{'error':'QA allowlist only.'})

    def do_POST(self):
        path=urlsplit(self.path).path
        if path=='/qa-api/profiles/select':
            self.api_headers={}
            try:
                host=self.headers.get('Host','')
                if host not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}') or self.headers.get('Origin')!='http://'+host:
                    raise api.APIError('Yêu cầu phải từ màn QA đang mở.',403)
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise api.APIError('Use JSON',415)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1024:raise api.APIError('Invalid size',413)
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict) or set(body)!={'profileId'} or not isinstance(body['profileId'],str):raise api.APIError('Chọn một hồ sơ có sẵn.',400)
                profile=self.server.qa_profiles.get(body['profileId'])
                if not profile:raise api.APIError('Hồ sơ thử không tồn tại.',404)
                with api.connect(self.server.database_path,True) as db:
                    require_qa(db);session=api.read_session(self,db)
                    supplied=self.headers.get('X-CSRF-Token','')
                    if session:valid=hmac.compare_digest(supplied,session['csrf_token'])
                    else:
                        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
                        guest_name=self.server.qa_guest_cookie_name
                        token=cookie[guest_name].value if guest_name in cookie else ''
                        with self.server.qa_guest_lock:record=self.server.qa_guests.get(hashlib.sha256(token.encode()).hexdigest())
                        valid=bool(record and record[1]>time.monotonic() and hmac.compare_digest(supplied,record[0]))
                    if not valid:raise api.APIError('Phiên chọn hồ sơ cần tải lại.',403)
                    if session:db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(session['token_hash'],))
                    selected=api.issue_session(self,db,profile['accountId'])
                    result=bootstrap(self,db,selected)
                self.json_response(200,result)
            except api.APIError as error:self.json_response(error.status,{'error':str(error)})
            except (ValueError,TypeError):self.json_response(400,{'error':'Dữ liệu QA không hợp lệ.'})
            return
        if path in ('/api/v1/exams','/api/v1/auth/logout') or re.fullmatch(r'/api/v1/exams/\d+/(answers|submit)',path):
            super().do_POST();return
        self.json_response(403,{'error':'Đường này không mở trên QA học thử.'})


def create_server(database,questions_path,manifest_path,sources_path,port=0,package_label='Mẫu MCQ vòng 2 — 10 câu',seed_expired=True,*,bind_host='127.0.0.1',seed_learning=True):
    if port==8765:raise ValueError('Never use port8765')
    if bind_host!='127.0.0.1' and not (bind_host=='0.0.0.0' and os.environ.get('FIVEBMATH_QA_CONTAINER')=='1'):raise ValueError('Non-loopback bind requires explicit isolated QA container flag')
    package,manifest,sources=map(load_json,(questions_path,manifest_path,sources_path))
    server=ThreadingHTTPServer((bind_host,port),StudyHandler)
    original_now=api.now
    clock=QAClock((datetime.fromisoformat(manifest['windowStart'])+timedelta(hours=12)).astimezone(timezone.utc))
    api.now=clock.now
    try:
        path=initialize_empty_qa(database,seed_learning=seed_learning)
        result=import_package(path,package,manifest,sources,allow_draft_qa=True)
        server.database_path=path;server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5)
        # Ports do not scope browser cookies; explicit per-QA-server names do.
        server.student_cookie_name=f'{QA_COOKIE_PREFIX}_{server.server_port}_session'
        server.qa_guest_cookie_name=f'{QA_COOKIE_PREFIX}_{server.server_port}_bootstrap'
        server.review_upgrades=False;server.real_accounts=True;server.arena=Arena()
        server.qa_guests={};server.qa_guest_lock=threading.Lock();server.qa_package_label=package_label
        server.qa_profiles={};server.qa_clock=clock;server.qa_original_now=original_now;server.qa_import=result
        server.qa_input_sha={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in (questions_path,manifest_path,sources_path)}
        server.qa_manifest=manifest
        fake=SimpleNamespace(server=server,headers={},api_headers={})
        with api.connect(path,True) as db:
            for key,name,label,paid in [('an','An Mẫu','Free',False),('binh','Bình Mẫu','VIP',True),('chi','Chi Mẫu','VIP hết hạn',True)]:
                session=api.register(fake,db,{'login':'qa-ui-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),'name':name,'birthYear':api.academic()[0]-10})
                aid=session['account_id']
                if paid:db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()+timedelta(days=30)),aid))
                server.qa_profiles[key]={'accountId':aid,'name':name,'label':label}
                if key=='chi' and seed_expired:
                    from .free_vip_pilot import create_exam
                    exam=create_exam(db,session,{'requestKey':'qa-seed-expired','contentKeys':manifest['vipSupplementContentKeys']},server.free_vip_pilot)
                    for i,q in enumerate(exam['questions'],1):
                        db.execute('INSERT INTO exam_draft_answers VALUES (?,?,?,?,?)',(api.owned_attempt(db,session,int(exam['id']))['id'],int(exam['id']),i,q['options'][0],api.stamp()))
                    api.submit(db,api.owned_attempt(db,session,int(exam['id'])))
                    db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()-timedelta(days=1)),aid))
            db.execute('DELETE FROM auth_sessions')
        return server
    except BaseException:
        api.now=original_now;server.server_close();raise


def close_server(server):
    server.server_close();api.now=server.qa_original_now
