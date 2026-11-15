"""Smoke real MCQ package via isolated HTTP; no live DB, assets, or secrets."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import socket
import threading
from unittest.mock import patch

from backend import platform_api as api
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.mcq_import import load_json,import_package,ImportFailure
from backend.server import ThreadingHTTPServer
from scripts.free_vip_qa import QAHandler
from scripts.free_vip_smoke import HTTPClient
from scripts.import_mcq_qa import initialize_empty_qa


def run(database,questions_path,manifest_path,sources_path,report_path):
    package,manifest,sources=map(load_json,(questions_path,manifest_path,sources_path))
    raw_hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in (questions_path,manifest_path,sources_path)}
    fixed=(datetime.fromisoformat(manifest['windowStart'])+timedelta(hours=12)).astimezone(timezone.utc)
    server=ThreadingHTTPServer(('127.0.0.1',0),QAHandler)
    server.student_cookie_name=f'5bmath_qa_{server.server_port}_session'
    thread=None; port=server.server_port
    with patch.object(api,'now',return_value=fixed):
        try:
            path=initialize_empty_qa(database)
            try:
                import_package(path,package,manifest,sources)
            except ImportFailure:
                default_rejected=True
            else:
                raise AssertionError('Self-checked learning package unexpectedly accepted without QA opt-in')
            imported=import_package(path,package,manifest,sources,allow_draft_qa=True)
            replay=import_package(path,package,manifest,sources,allow_draft_qa=True)
            assert replay['insertedVersions']==0 and replay['replayedVersions']==10
            server.database_path=path
            server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5)
            server.review_upgrades=False;server.real_accounts=True;server.arena=Arena()
            base=f'http://127.0.0.1:{port}'
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            a,b,v=HTTPClient(base),HTTPClient(base),HTTPClient(base)
            a.register();b.register();vip=v.register()
            with api.connect(path,True) as db:
                db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(fixed+timedelta(days=30)),vip['account']['id']))
            body={'requestKey':'mcq-http-free-001','setIndex':1}
            free=a.call('/api/v1/exams',body)['exam']
            same=b.call('/api/v1/exams',{'requestKey':'mcq-http-free-002','setIndex':1})['exam']
            assert free['questions']==same['questions'] and len(free['questions'])==5
            b.call('/api/v1/exams/'+free['id'],expected=404)
            a.call('/api/v1/exams',{'requestKey':'forged-quota','setIndex':1,'quotaKey':'forged'},expected=400)
            a.call('/api/v1/exams',{'requestKey':'free-vip-bypass','contentKeys':manifest['vipSupplementContentKeys']},expected=403)
            a.call('/api/v1/exams/'+free['id']+'/answers',{'position':1,'answer':'A'},expected=400)
            assert a.call('/api/v1/exams',body)['exam']['id']==free['id']
            vb={'requestKey':'mcq-http-vip-001','contentKeys':manifest['vipSupplementContentKeys']}
            paid=v.call('/api/v1/exams',vb)['exam']
            assert v.call('/api/v1/exams',vb)['exam']['id']==paid['id']
            assert v.call('/api/v1/pilot/sets')['newUsed']==5
            bykey={q['contentKey']:q for q in package['questions']}
            scores={};graded=[]
            for label,c,exam,keys in (('Free',a,free,manifest['orderedContentKeys']),('VIP',v,paid,manifest['vipSupplementContentKeys'])):
                for i,(view,ck) in enumerate(zip(exam['questions'],keys)):
                    assert not {'answer','steps','solution','thinking','choiceRationales','correctChoiceId','answerExplanation'} & set(view)
                    authored=bykey[ck]; correct=next(ch['text'] for ch in authored['choices'] if ch['id']==authored['correctChoiceId'])
                    assert view['options']==[ch['text'] for ch in authored['choices']]
                    expected_correct=label=='VIP' or i%2==0
                    answer=correct if expected_correct else next(ch['text'] for ch in authored['choices'] if ch['id']!=authored['correctChoiceId'])
                    c.call('/api/v1/exams/'+exam['id']+'/answers',{'position':i+1,'answer':answer})
                    graded.append({'contentKey':ck,'expectedCorrect':expected_correct})
                result=c.call('/api/v1/exams/'+exam['id']+'/submit',{})['exam']
                assert result['score']==(10 if label=='VIP' else 6)
                assert all('solution' in q and 'answer' in q for q in result['questions'])
                assert c.call('/api/v1/exams/'+exam['id']+'/submit',{})['exam']==result
                scores[label]={'score':result['score'],'correct':result['correct'],'count':len(result['questions'])}
            with api.connect(path,True) as db:
                db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(fixed-timedelta(seconds=1)),vip['account']['id']))
            assert v.call('/api/v1/exams/'+paid['id'])['exam']['score']==10
            v.call('/api/v1/exams',{'requestKey':'expired-new','contentKeys':manifest['vipSupplementContentKeys']},expected=403)
            for endpoint,payload in (('/api/v1/bot/start',{'requestKey':'mcq-bot-block'}),('/api/v1/arena',{'action':'quick'}),('/api/v1/materials',None),('/api/v1/lessons/test/open',{})):
                a.call(endpoint,payload,expected=403)
            for endpoint in ('/backend/mcq_import.py','/questions-mcq.json','/learning.js','/api/database-demo/samples'):
                a.call(endpoint,expected=404)
            a.call('/api/webhooks/sepay',{},expected=403)
            with api.connect(path) as db:
                assert db.execute('SELECT count(*) FROM pilot_content').fetchone()[0]==10
                assert db.execute('SELECT count(*) FROM mcq_versions').fetchone()[0]==10
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert not db.execute('PRAGMA foreign_key_check').fetchall()
                quota=db.execute('SELECT count(*) FROM pilot_grants WHERE quota_charged=1').fetchone()[0]
                assert quota==5
            result={'status':'PASS','qaOnly':True,'sourceFileSHA256':raw_hashes,'import':imported,
                'draftDefaultRejected':default_rejected,'idempotentImport':True,'qaClock':api.stamp(fixed),
                'systemClockChanged':False,'base':base,'database':str(path),'freeSameSet':True,
                'importedQuestions':10,'distinctGradedQuestions':10,'graded':graded,'scores':scores,
                'quotaCharged':quota,'expiredVipReview':True,'owner404':True,'choiceIdRejectedTextGraded':True,
                'noAnswerBeforeSubmit':True,'sideRoutesBlocked':True,'privateAssets404':True,'integrity':'ok'}
        finally:
            if thread: server.shutdown();thread.join(timeout=10)
            server.server_close()
    probe=socket.socket()
    try: probe.bind(('127.0.0.1',port));result['portFreeToBindAfterRun']=True
    finally: probe.close()
    result['listenerStopped']=True
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in raw_hashes.items())
    report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('database','questions','manifest','sources','report'): p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.database,a.questions,a.manifest,a.sources,a.report)


if __name__=='__main__':main()
