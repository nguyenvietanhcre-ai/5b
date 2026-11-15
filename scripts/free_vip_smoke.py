"""Real loopback HTTP demonstration; creates only a NEW QA database, then closes its port."""
import argparse
from datetime import timedelta
from http.cookiejar import CookieJar
import json
from pathlib import Path
import secrets
import threading
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from backend import platform_api as api
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.server import ThreadingHTTPServer
from scripts.free_vip_fixture import initialize_qa
from scripts.free_vip_qa import QAHandler


class HTTPClient:
    def __init__(self, base):
        self.base=base
        self.opener=build_opener(HTTPCookieProcessor(CookieJar()))
        self.csrf=''

    def call(self,path,body=None,expected=200):
        headers={'Origin':self.base,'Content-Type':'application/json','X-CSRF-Token':self.csrf}
        request=Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            response=self.opener.open(request,timeout=15)
        except HTTPError as error:
            response=error
        with response:
            raw=response.read()
            assert response.status == expected, (path,response.status,raw[:200])
            if response.headers.get('Content-Type','').startswith('application/json'):
                result=json.loads(raw)
            else:
                result={}
            if result.get('csrf'):
                self.csrf=result['csrf']
            return result

    def register(self):
        # Credentials live only in this process. Evidence never includes them or cookies.
        return self.call('/api/v1/auth/register',{'login':'smoke-'+secrets.token_hex(8),
            'password':secrets.token_urlsafe(24),'name':'Học sinh thử','birthYear':api.academic()[0]-10})


def run(database, report):
    server=ThreadingHTTPServer(('127.0.0.1',0),QAHandler)  # OS reserves an available separate port
    server.student_cookie_name=f'5bmath_qa_{server.server_port}_session'
    thread=None
    results={}
    try:
        server.database_path=initialize_qa(database)
        server.free_vip_pilot=PilotConfig()
        server.review_upgrades=False
        server.real_accounts=True
        server.arena=Arena()
        base=f'http://127.0.0.1:{server.server_port}'
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        a,b=HTTPClient(base),HTTPClient(base)
        a.call('/api/health')
        a.call('/api/v1/pilot/sets',expected=401)
        identity=a.register()
        b.register()
        first=a.call('/api/v1/exams',{'requestKey':'smoke-free-a','setIndex':1})['exam']
        second=b.call('/api/v1/exams',{'requestKey':'smoke-free-b','setIndex':1})['exam']
        assert first['questions']==second['questions'] and len(first['questions'])==10
        assert all('answer' not in q and 'solution' not in q for q in first['questions'])
        b.call('/api/v1/exams/'+first['id'],expected=404)
        for path,body in (('/api/v1/bot/start',{'requestKey':'smoke-bot'}),('/api/v1/arena',{'action':'quick'}),
                          ('/api/v1/materials',None)):
            a.call(path,body,expected=403)
        for path in ('/backend/learning-catalog.json','/learning-catalog.json','/scripts/free_vip_fixture.py',
                     '/learning.js','/index.html','/api/database-demo/samples'):
            a.call(path,expected=404)
        a.call('/api/webhooks/sepay',{},expected=403)
        a.call('/api/v1/payments',{},expected=403)
        a.call('/api/staff/auth/login',{},expected=403)
        submitted=a.call('/api/v1/exams/'+first['id']+'/submit',{})['exam']
        assert 'answer' in submitted['questions'][0]
        with api.connect(database,True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                (api.stamp(api.now()+timedelta(days=30)),identity['account']['id']))
        for offset in range(90,190,10):
            a.call('/api/v1/exams',{'requestKey':f'smoke-vip-{offset}',
                'contentKeys':[f'qa-fixture-{i:03}' for i in range(offset,offset+10)]})
        a.call('/api/v1/exams',{'requestKey':'smoke-overflow','contentKeys':['qa-fixture-190']},expected=429)
        assert a.call('/api/v1/pilot/sets')['newUsed']==100
        with api.connect(database,True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                (api.stamp(api.now()-timedelta(seconds=1)),identity['account']['id']))
        assert 'solution' in a.call('/api/v1/exams/'+first['id'])['exam']['questions'][0]
        results={'status':'PASS','base':base,'database':str(Path(database).resolve()),
            'freeSameSet':True,'owner404':True,'answersOnlySubmitted':True,'vip100Then429':True,
            'expiredReview':True,'sideRoutes403':True,'assets404':True,'financialStaffBlocked':True,
            'checkedAt':api.stamp(),'portClosedAfterRun':True}
    finally:
        if thread:
            server.shutdown()
            thread.join(timeout=10)
        server.server_close()
    Path(report).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    run(args.database,args.report)


if __name__=='__main__':
    main()
