"""Integrated typed wallet QA: preserve ten MCQ identities/history, add typed revision3."""
from datetime import datetime,timedelta,timezone
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
from . import platform_api as api
from .free_vip_pilot import PilotConfig,create_exam
from .mcq_import import load_json,import_package
from .qa_study import QAClock,close_server
from .wallet_study import create_server as wallet_server


def create_server(database,questions,manifest,sources,port=0,*,bind_host='127.0.0.1',seed_learning=True):
    questions,manifest,sources=map(Path,(questions,manifest,sources));folder=questions.parent
    originals=folder/'originals';history_manifest=folder/'history-sets.json'
    server=wallet_server(database,originals/'questions-mcq.json',history_manifest,originals/'sources.json',port,bind_host=bind_host,seed_learning=seed_learning)
    try:
        package=load_json(questions);pins=load_json(manifest)
        typed_anchor=(datetime.fromisoformat(pins['windowStart'])+timedelta(hours=12)).astimezone(timezone.utc)
        bykey={q['contentKey']:q for q in load_json(originals/'questions-mcq.json')['questions']}
        fake=SimpleNamespace(server=server,headers={},api_headers={});legacy={}
        with api.connect(server.database_path,True) as db:
            for profile in ('an','chi'):
                session=api.issue_session(fake,db,server.qa_profiles[profile]['accountId'])
                exam=create_exam(db,session,{'requestKey':'qa-history-'+profile,'setIndex':1},server.free_vip_pilot)
                attempt=api.owned_attempt(db,session,int(exam['id']));legacy[profile]=exam['id']
                keys=server.qa_manifest['orderedContentKeys']
                for index,ck in enumerate(keys if profile=='an' else keys[:1],1):
                    q=bykey[ck];correct=next(c['text'] for c in q['choices'] if c['id']==q['correctChoiceId'])
                    answer=correct if index%2 else next(c['text'] for c in q['choices'] if c['id']!=q['correctChoiceId'])
                    db.execute('INSERT INTO exam_draft_answers VALUES (?,?,?,?,?)',(attempt['id'],int(exam['id']),index,answer,api.stamp()))
                if profile=='an':api.submit(db,attempt)
                else:db.execute('UPDATE exam_attempts SET started_at=?,due_at=? WHERE id=?',
                     (api.stamp(typed_anchor-timedelta(minutes=1)),api.stamp(typed_anchor+timedelta(minutes=30)),attempt['id']))
        imported=import_package(server.database_path,package,pins,load_json(sources),allow_draft_qa=True)
        server.qa_clock=QAClock(typed_anchor);api.now=server.qa_clock.now
        server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5,wallet=True,response_mode='typed')
        server.qa_manifest=pins;server.qa_import=imported;server.qa_package_label='QA ghép ví + tự nhập — 10 câu, cùng danh tính'
        server.qa_legacy_history=legacy
        with api.connect(server.database_path,True) as db:
            db.execute('UPDATE wallet_usage_seeds SET local_day=?',(api.now().astimezone(api.VN).date().isoformat(),))
            db.execute('DELETE FROM auth_sessions')
        paths=(questions,manifest,sources,originals/'questions-mcq.json',history_manifest,originals/'sources.json')
        server.qa_input_sha={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        return server
    except BaseException:close_server(server);raise
