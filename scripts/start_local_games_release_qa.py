"""Own Docker QA only: two NEW synthetic DBs, never a runtime DB mount."""
from pathlib import Path
import argparse,json,os
from backend import platform_api as api
from backend.database import initialize
from backend.server import Handler,ThreadingHTTPServer
from backend.arena import Arena
from backend.local_pilot import LocalPilot
from backend.local_test_games import NativeLocalTestGames
from backend.content_retirement import activate

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--external-port',type=int,required=True)
    parser.add_argument('--port',type=int,default=8000);args=parser.parse_args()
    if os.environ.get('FIVEBMATH_RELEASE_QA')!='multiplayer-localhost-20261114' or args.external_port not in (19033,19034):raise ValueError('Explicit isolated release QA namespace/port required')
    folder=args.directory.resolve()
    if not folder.is_relative_to(Path('/qa')) or folder==Path('/qa'):raise ValueError('Fresh QA subdirectory required; never /data or /pilot')
    folder.mkdir(parents=True,exist_ok=False)
    main_db=folder/'main-fake.sqlite3';pilot_db=folder/'pilot-fake.sqlite3'
    initialize(main_db);api.initialize_catalog(main_db);api.seed_catalog(main_db)
    with api.connect(main_db,True) as db:
        db.execute('CREATE TABLE localhost_release_qa_owner(label TEXT NOT NULL)')
        db.execute("INSERT INTO localhost_release_qa_owner VALUES('multiplayer-localhost-20261114-new-synthetic-only')")
        activate(db)
    root=Path(__file__).resolve().parents[1]
    server=ThreadingHTTPServer(('0.0.0.0',args.port),Handler)
    server.database_path=main_db;server.real_accounts=True;server.review_upgrades=False;server.arena=Arena();server.daemon_threads=True
    server.student_cookie_name=f'5bmath_release_{args.external_port}_session'
    server.native_python_backend=True;server.local_test_games=NativeLocalTestGames({args.external_port})
    server.local_pilot_ports={args.external_port}
    server.local_pilot=LocalPilot(main_db,pilot_db,root/'pilot-inputs',restructure_inputs=root/'restructure-inputs')
    state={'qaOnly':True,'port':args.external_port,'base':f'http://127.0.0.1:{args.external_port}/','mainDatabase':str(main_db),'pilotDatabase':str(pilot_db),
           'cookieName':server.student_cookie_name,'ownerMarker':'multiplayer-localhost-20261114-new-synthetic-only','nativeLocalTestGames':True}
    (Path('/qa')/'QA-SESSION.json').write_text(json.dumps(state,indent=2),encoding='utf-8');print(json.dumps(state),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
