"""Migrate an actual pre-typed-answer database in workerd, with fake data only."""
import argparse,json,secrets,sqlite3,tempfile,traceback,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_runtime import LocalWorker,HTTPClient,transfer_payload
from backend.database import BACKEND,execute_sql
from backend import platform_api as api

def run(port):
    root=Path(__file__).resolve().parents[1];(root/'work').mkdir(exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='legacy-migration-worker-',dir=root/'work'))
    report={'status':'running','scope':'synthetic pre-0019 database, actual local workerd only'};worker=None
    try:
        source=directory/'source.sqlite3';password=secrets.token_urlsafe(24);credential=api.password_hash(password)
        with sqlite3.connect(source) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('CREATE TABLE schema_migrations(name TEXT PRIMARY KEY,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            for migration in sorted((BACKEND/'migrations').glob('*.sql')):
                if migration.name>='0019_':break
                execute_sql(db,migration.read_text('utf-8'));db.execute('INSERT INTO schema_migrations(name) VALUES(?)',(migration.name,))
            db.execute("INSERT INTO mascots(id,name) VALUES(100,'Legacy QA')")
            db.execute('INSERT INTO mascot_levels VALUES(1,1000)')
            db.execute("INSERT INTO mascot_variants VALUES(100,1,'legacy-variant.webp',NULL)")
            db.execute("INSERT INTO accounts(id,account_code,login_identifier,birth_year,invite_code,created_at,password_hash) VALUES(1,'OLD-ACCOUNT','legacy-migration',?,'LEGACY-QA',?,?)",(api.academic()[0]-10,api.stamp(),credential))
            db.execute("INSERT INTO students(id,student_code,full_name,grade_level,account_id) VALUES(1,'OLD-STUDENT','Học sinh dữ liệu giả',5,1)")
            db.execute('INSERT INTO student_companions VALUES(1,100,1260)')
            db.execute("INSERT INTO bots(id,kind,display_name,skill_level,xp) VALUES(1,'training','Legacy BOT',1,1120)")
        payload,transfer=transfer_payload(source,directory);token=secrets.token_urlsafe(36)
        worker=LocalWorker(directory,port,token,secrets.token_urlsafe(36))
        worker.start()
        operator=HTTPClient(worker.origin);auth={'Authorization':'Bearer '+token}
        operator.call('/__ops/import',payload,headers=auth)
        student=HTTPClient(worker.origin);state=student.call('/api/v1/auth/login',{'login':'legacy-migration','password':password})
        assert state['account']['id']==1 and state['state']['points']==260
        exported=operator.call('/__ops/export',headers=auth)
        restored=directory/'after.verified.sqlite3';transfer.restore_payload(exported,restored)
        with sqlite3.connect(restored) as db:
            assert db.execute('SELECT password_hash FROM accounts WHERE id=1').fetchone()[0]==credential
            assert db.execute('SELECT xp FROM student_companions WHERE student_id=1').fetchone()[0]==260
            assert db.execute('SELECT xp FROM bots WHERE id=1').fetchone()[0]==120
            assert db.execute('SELECT image_ref FROM mascot_variants WHERE mascot_id=100 AND level=1').fetchone()[0]=='legacy-variant.webp'
            assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
            report['migrationCount']=db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0]
        worker.stop();worker.start()
        again=HTTPClient(worker.origin);assert again.call('/api/v1/auth/login',{'login':'legacy-migration','password':password})['state']['points']==260
        report.update(status='passed',checks=['pre-0019 schema migrates through current ledger in actual Durable Object SQLite','old account/password/student/variant IDs preserved; only the approved 1000 starter-XP offset removed','all foreign keys valid after exported SQLite roundtrip','restart does not apply XP conversion twice'])
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error));traceback.print_exc()
    finally:
        if worker:worker.stop()
        (directory/'migration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({**report,'evidence':str(directory)},ensure_ascii=True),flush=True)
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8896);raise SystemExit(run(p.parse_args().port))
