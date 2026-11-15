"""Real-browser confirmation regression. DB mutation is test-only and owner-marked."""
import argparse,json,os,socket,subprocess,threading,sqlite3
from pathlib import Path
from backend.wallet_study import create_server,close_server
from backend.mcq_import import require_qa


def control(database,action,quote_id):
    database=database.resolve();seal=database.parent/'confirm-harness-owned.json'
    owner=json.loads(seal.read_text(encoding='utf-8'))
    if owner!={'database':str(database),'purpose':'confirm-fix-only-v1'}:raise ValueError('Not an owned confirmation QA database')
    if not database.is_file():raise ValueError('QA database must already exist')
    db=sqlite3.connect(database)
    try:
        db.execute('BEGIN IMMEDIATE');require_qa(db)
        row=db.execute('SELECT student_id FROM wallet_quotes WHERE quote_id=?',(quote_id,)).fetchone()
        if not row:raise ValueError('Unknown test quote')
        if action=='expire':
            db.execute("UPDATE wallet_quotes SET expires_at='2000-01-01T00:00:00Z' WHERE quote_id=?",(quote_id,))
        elif action=='exhaust-vip':
            cursor=db.execute('UPDATE wallet_usage_seeds SET day_used=30 WHERE student_id=?',(row[0],))
            if cursor.rowcount!=1:raise ValueError('Expected one labelled boundary seed')
        else:raise ValueError('Unknown test-only action')
        db.commit()
    except BaseException:db.rollback();raise
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path);p.add_argument('--control',choices=['expire','exhaust-vip']);p.add_argument('--quote-id')
    for n in ('questions','manifest','sources','output','node'):p.add_argument('--'+n,type=Path)
    p.add_argument('--sizes',default='390x844,844x390,768x1024,1024x768,1366x768,1920x1080')
    a=p.parse_args()
    if a.control:
        if not a.database or not a.quote_id:p.error('Test control needs owned database and quote')
        control(a.database,a.control,a.quote_id);return
    if not all((a.questions,a.manifest,a.sources,a.output,a.node)):p.error('Supply three inputs/output/node')
    a.output.mkdir(parents=True,exist_ok=False);records=[]
    for size in a.sizes.split(','):
        w,h=map(int,size.split('x'));folder=a.output/size;folder.mkdir();database=(folder/'confirm.sqlite3').resolve()
        server=create_server(database,a.questions,a.manifest,a.sources);port=server.server_port
        (folder/'confirm-harness-owned.json').write_text(json.dumps({'database':str(database),'purpose':'confirm-fix-only-v1'}),encoding='utf-8')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        result={'size':size,'port':port,'qaOnly':True,'inputSHA256':server.qa_input_sha}
        try:
            temp=folder/'runtime-temp';temp.mkdir();env=os.environ.copy();env.update(TMP=str(temp.resolve()),TEMP=str(temp.resolve()),TMPDIR=str(temp.resolve()),PYTHONUTF8='1')
            import sys
            process=subprocess.run([str(a.node),str(Path('tests/wallet-confirm-browser.cjs').resolve()),f'http://127.0.0.1:{port}/',str(folder.resolve()),str(database),sys.executable,str(w),str(h)],capture_output=True,text=True,encoding='utf-8',env=env)
            (folder/'process.txt').write_text(process.stdout+process.stderr,encoding='utf-8');result['exitCode']=process.returncode
            result['browser']=json.loads((folder/'browser-report.json').read_text(encoding='utf-8'))
        finally:
            server.shutdown();thread.join(timeout=10);close_server(server)
            with socket.socket() as probe:probe.bind(('127.0.0.1',port));result['listenerStoppedAndPortFree']=True
            (folder/'server-report.json').write_text(json.dumps({k:v for k,v in result.items() if k!='browser'},indent=2),encoding='utf-8')
        records.append(result)
        report={'status':'PASS' if all(r['exitCode']==0 for r in records) else 'FAIL','viewports':records,'mainRequests8765':sum(r['browser']['mainRequests'] for r in records)}
        (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result['exitCode']:raise RuntimeError('Confirmation browser failed: '+size)
    print(json.dumps({'status':report['status'],'viewports':len(records),'requests8765':report['mainRequests8765']}))


if __name__=='__main__':main()
