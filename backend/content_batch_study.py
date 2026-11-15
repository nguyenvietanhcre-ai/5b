"""Isolated QA8 batch study; legacy ten-question launchers remain unchanged."""
from datetime import datetime,timedelta,timezone
import hashlib
from pathlib import Path
from types import SimpleNamespace
from . import platform_api as api,wallet_qa as wallet
from .typed_wallet_study import create_server as typed_server
from .qa_study import QAClock,close_server
from .free_vip_pilot import PilotConfig,create_exam
from .mcq_import import load_json
from .content_batch_qa import import_batch

def create_server(database,legacy_folder,batch_folder,port=0,*,bind_host='127.0.0.1'):
    legacy_folder,batch_folder=map(Path,(legacy_folder,batch_folder))
    server=typed_server(database,legacy_folder/'questions-typed.json',legacy_folder/'sample-sets-typed.json',legacy_folder/'sources.json',port,bind_host=bind_host,seed_learning=False)
    try:
        # Keep a submitted typed fixture as well as the submitted/pending MCQ fixtures.
        old_typed=load_json(legacy_folder/'questions-typed.json');old_bykey={q['contentKey']:q for q in old_typed['questions']}
        with api.connect(database,True) as db:
            session=api.issue_session(SimpleNamespace(server=server,headers={},api_headers={}),db,server.qa_profiles['an']['accountId'])
            exam=create_exam(db,session,{'requestKey':'qa-r8-prior-typed','setIndex':1},server.free_vip_pilot)
            attempt=api.owned_attempt(db,session,int(exam['id']))
            for pos,ck in enumerate(server.qa_manifest['orderedContentKeys'],1):
                db.execute('INSERT INTO exam_draft_answers VALUES (?,?,?,?,?)',(attempt['id'],int(exam['id']),pos,old_bykey[ck]['correctAnswer'],api.stamp()))
            api.submit(db,attempt);server.qa_legacy_typed_history=exam['id']
        paths=[batch_folder/name for name in ('questions-mcq60.json','batch-manifest.json','questions-typed-subset.json','typed-manifest.json','sources.json')]
        choice,pins,typed,tpins,sources=map(load_json,paths)
        imports=[import_batch(database,choice,pins,sources,allow_batch_qa=True,allow_draft_qa=True),import_batch(database,typed,tpins,sources,allow_batch_qa=True,allow_draft_qa=True)]
        server.qa_clock=QAClock((datetime.fromisoformat(pins['windowStart'])+timedelta(hours=12)).astimezone(timezone.utc));api.now=server.qa_clock.now
        server.free_vip_pilot=PilotConfig(wallet=True,batch_set_key=pins['setKey'])
        server.qa_manifest=pins;server.qa_import=imports;server.qa_package_label=f'QA60 câu tự biên soạn · MCQ60 · tự nhập{len(typed["questions"])} · chờ giáo viên rà'
        previous=server.qa_bootstrap_extension
        def extend(db,session,result):
            previous(db,session,result)
            result['batch']={'setKey':pins['setKey'],'freeSets':pins['freeSets'],'vipKeys':pins['vipSupplementContentKeys'],
                'typedFree':[k for k in tpins['eligibleContentKeys'] if k in pins['orderedContentKeys']],
                'typedVip':[k for k in tpins['eligibleContentKeys'] if k in pins['vipSupplementContentKeys']]}
        server.qa_bootstrap_extension=extend
        with api.connect(database,True) as db:
            db.execute("UPDATE wallet_scopes SET keys_json=? WHERE scope_id='qa.g5.vip10'",(api.packed(pins['vipSupplementContentKeys']),))
            db.execute('UPDATE wallet_usage_seeds SET local_day=?',(api.now().astimezone(api.VN).date().isoformat(),))
            # The pending legacy fixture is deliberately kept available, not a production migration.
            db.execute("UPDATE exam_attempts SET started_at=?,due_at=? WHERE status='in_progress'",(api.stamp(api.now()-timedelta(minutes=1)),api.stamp(api.now()+timedelta(minutes=30))))
            db.execute('DELETE FROM auth_sessions')
        server.qa_input_sha.update({str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        return server
    except BaseException:close_server(server);raise
