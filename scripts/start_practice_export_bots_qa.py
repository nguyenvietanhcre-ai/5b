"""Fresh QA only: Linux main volume, separate Windows pilot bind, no real DBs."""
import argparse,json,os
from pathlib import Path
from backend import platform_api as api
from backend.database import initialize
from backend.server import Handler,ThreadingHTTPServer
from backend.arena import Arena
from backend.local_pilot import LocalPilot
from backend.local_test_games import NativeLocalTestGames
from backend.content_retirement import activate

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--pilot-database',type=Path,required=True);p.add_argument('--external-port',type=int,required=True);a=p.parse_args()
    if os.environ.get('FIVEBMATH_PRACTICE_EXPORT_BOTS_QA')!='practice-export-bots-20261114' or a.external_port not in (19033,19034):raise ValueError('Explicit new QA namespace required')
    folder=a.directory.resolve();pilot=a.pilot_database.resolve()
    if not folder.is_relative_to('/qa') or folder==Path('/qa') or not pilot.is_relative_to('/qa-pilot') or pilot.exists():raise ValueError('Only fresh scratch main/pilot paths allowed')
    folder.mkdir(parents=True,exist_ok=False);pilot.parent.mkdir(parents=True,exist_ok=True)
    path=folder/'main-fake.sqlite3';initialize(path);api.initialize_catalog(path);api.seed_catalog(path)
    with api.connect(path,True) as db:
        db.execute('CREATE TABLE practice_export_bots_qa_owner(label TEXT NOT NULL)')
        db.execute("INSERT INTO practice_export_bots_qa_owner VALUES('practice-export-bots-qa-new-synthetic-only')");activate(db)
    root=Path(__file__).resolve().parents[1];server=ThreadingHTTPServer(('0.0.0.0',8000),Handler)
    server.database_path=path;server.real_accounts=True;server.review_upgrades=False;server.arena=Arena();server.daemon_threads=True
    server.student_cookie_name=f'5bmath_print_bots_{a.external_port}_session';server.native_python_backend=True
    server.practice_export_enabled=True;server.practice_export_ports={a.external_port}
    server.local_test_games=NativeLocalTestGames({a.external_port});server.local_pilot_ports={a.external_port}
    server.local_pilot=LocalPilot(path,pilot,root/'pilot-inputs',restructure_inputs=root/'restructure-inputs')
    data={'qaOnly':True,'port':a.external_port,'base':f'http://127.0.0.1:{a.external_port}/','mainDatabase':str(path),'pilotDatabase':str(pilot),
        'cookieName':server.student_cookie_name,'ownerMarkerTable':'practice_export_bots_qa_owner','ownerMarker':'practice-export-bots-qa-new-synthetic-only','practiceExportEnabled':True,'allowSyntheticLegacyHistory':True}
    Path('/qa/QA-SESSION.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data),flush=True)
    try:server.serve_forever()
    finally:server.server_close()
if __name__=='__main__':main()
