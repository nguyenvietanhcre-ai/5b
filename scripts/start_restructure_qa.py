"""Round11 QA only. Creates two NEW fake databases and a per-port cookie."""
import argparse,json,os,secrets
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta
from backend import platform_api as api
from backend.database import initialize
from backend.server import Handler,ThreadingHTTPServer
from backend.arena import Arena
from backend.local_pilot import LocalPilot
from backend.content_retirement import activate

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--port',type=int,default=19011);p.add_argument('--external-port',type=int);p.add_argument('--host',default='127.0.0.1');p.add_argument('--restructure-inputs',type=Path);a=p.parse_args();external=a.external_port or a.port
    if os.environ.get('FIVEBMATH_QA_CONTAINER')!='1' or external in (8765,18986) or not 1024<=external<=65535:raise ValueError('Explicit QA flag/isolated unreserved port required')
    if a.host!='127.0.0.1' and not(a.host=='0.0.0.0' and os.environ.get('FIVEBMATH_QA_DOCKER')=='1'):raise ValueError('Bind loopback only; Docker must publish loopback')
    folder=a.directory.resolve();folder.mkdir(parents=True,exist_ok=False)
    main_db=folder/'main-fake.sqlite3';pilot_db=folder/'pilot-fake.sqlite3';initialize(main_db);api.initialize_catalog(main_db);api.seed_catalog(main_db)
    with api.connect(main_db,True) as db:db.execute('CREATE TABLE local_native_qa_owner(label TEXT NOT NULL)');db.execute("INSERT INTO local_native_qa_owner VALUES('round11-new-synthetic-only')")
    root=Path(__file__).resolve().parents[1];provider=LocalPilot(main_db,pilot_db,root/'pilot-inputs',a.restructure_inputs or root/'restructure-inputs')
    profiles=[]
    for role in ('Free','VIP','expired','SVip','grade4','FreePack','VIPBoundary'):
        password=secrets.token_urlsafe(12);login='qa-r11-'+role.lower();birth=api.academic()[0]-(4 if role=='grade4' else 5)-5
        fake=SimpleNamespace(server=SimpleNamespace(),headers={},api_headers={})
        with api.connect(main_db,True) as db:
            session=api.register(fake,db,{'login':login,'password':password,'name':'QA '+('Bốn' if role=='grade4' else 'Năm'),'birthYear':birth})
            if role in ('VIP','VIPBoundary'):db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()+timedelta(days=60)),session['account_id']))
            if role=='expired':db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()-timedelta(seconds=1)),session['account_id']))
            if role=='SVip':db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal','2026-01-01T00:00:00Z')",(session['account_id'],))
            if role=='VIP':
                old=api.create_exam(db,session,{'requestKey':secrets.token_hex(12),'category':'combined','count':10,'difficulty':0});attempt=api.owned_attempt(db,session,old['id']);api.submit(db,attempt)
            if role=='FreePack':
                old=api.create_exam(db,session,{'requestKey':secrets.token_hex(12),'category':'combined','count':10,'difficulty':0})
            main=dict(db.execute('SELECT s.id student_id,a.birth_year,s.full_name,a.id account_id,a.vip_expires_at FROM students s JOIN accounts a ON a.id=s.account_id WHERE a.id=?',(session['account_id'],)).fetchone())
            from backend.learning_update import membership
            member=membership(db,main)
        if role!='grade4':
            with api.connect(pilot_db,True) as db:
                mapped=provider.principal(db,main,member)
                if role in ('FreePack','VIPBoundary'):
                    from backend import wallet_qa as wallet
                    o=wallet.create_order(db,mapped,{'requestKey':secrets.token_hex(12),'sku':'qa.questions.100'});wallet.mock_event(db,mapped,{'orderId':o['orderId']},confirm=True)
                    if role=='VIPBoundary':
                        v=wallet.balance(db,mapped,provider.ensure_week()[0])['vip'];db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(mapped['student_id'],v['day'],v['cycleStart'],28,100,'synthetic round11 browser boundary'))
        profiles.append({'role':role,'login':login,'password':password})
    with api.connect(main_db,True) as db:retirement=activate(db)
    (folder/'retirement-manifest.json').write_text(api.packed(retirement),encoding='utf-8')
    (folder/'qa-profiles.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2),encoding='utf-8')
    server=ThreadingHTTPServer((a.host,a.port),Handler);server.database_path=main_db;server.review_upgrades=False;server.real_accounts=True;server.arena=Arena();server.daemon_threads=True
    server.student_cookie_name=f'5bmath_restructure_qa_{external}_session';server.local_pilot_ports={external};server.local_pilot=provider
    print(json.dumps({'qaOnly':True,'port':external,'directory':str(folder),'cookieName':server.student_cookie_name}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
