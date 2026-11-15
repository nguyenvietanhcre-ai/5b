"""QA9-only main UI launcher, fake databases and isolated cookie. Never used for 8765 cutover."""
import argparse,json,os
from pathlib import Path
from backend import platform_api as api
from backend.database import initialize
from backend.server import Handler,ThreadingHTTPServer
from backend.arena import Arena
from backend.local_pilot import LocalPilot

def main():
    p=argparse.ArgumentParser();p.add_argument('--main-database',type=Path,required=True);p.add_argument('--pilot-database',type=Path,required=True);p.add_argument('--port',type=int,default=8000);p.add_argument('--external-port',type=int,default=18990);a=p.parse_args()
    if os.environ.get('FIVEBMATH_QA_CONTAINER')!='1' or a.external_port==8765:raise ValueError('Isolated QA9 only, never main8765')
    a.main_database.parent.mkdir(parents=True,exist_ok=True)
    with a.main_database.open('xb'):pass
    initialize(a.main_database);api.initialize_catalog(a.main_database)
    with api.connect(a.main_database,True) as db:db.execute("CREATE TABLE local_native_qa_owner(label TEXT NOT NULL)");db.execute("INSERT INTO local_native_qa_owner VALUES ('native-round9-fake-main-only')")
    server=ThreadingHTTPServer(('0.0.0.0',a.port),Handler);server.database_path=a.main_database;server.review_upgrades=False;server.real_accounts=True;server.arena=Arena();server.daemon_threads=True
    server.student_cookie_name=f'5bmath_native_qa_{a.external_port}_session';server.local_pilot_ports={a.external_port}
    server.local_pilot=LocalPilot(a.main_database,a.pilot_database,Path('/app/pilot-inputs'))
    print(json.dumps({'qaOnly':True,'nativeUI':True,'externalPort':a.external_port,'cookieName':server.student_cookie_name}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
