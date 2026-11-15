"""Six fresh wallet QA databases/browser profiles; always close each listener."""
import argparse,json,os,socket,subprocess,threading
from pathlib import Path
from backend.wallet_study import create_server,close_server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('questions','manifest','sources','output','node'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--sizes',default='390x844,844x390,768x1024,1024x768,1366x768,1920x1080')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);reports=[]
    for size in a.sizes.split(','):
        w,h=map(int,size.split('x'));folder=a.output/size;folder.mkdir()
        server=create_server(folder/'wallet.sqlite3',a.questions,a.manifest,a.sources);port=server.server_port
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        record={'size':size,'port':port,'qaOnly':True,'inputSHA256':server.qa_input_sha}
        try:
            temp=folder/'runtime-temp';temp.mkdir();env=os.environ.copy();env.update(TMP=str(temp.resolve()),TEMP=str(temp.resolve()),TMPDIR=str(temp.resolve()))
            result=subprocess.run([str(a.node),str(Path('tests/wallet-browser.cjs').resolve()),f'http://127.0.0.1:{port}/',str(folder.resolve()),str(a.questions.resolve()),str(a.manifest.resolve()),str(w),str(h)],capture_output=True,text=True,encoding='utf-8',env=env)
            (folder/'process.txt').write_text(result.stdout+result.stderr,encoding='utf-8');record['exitCode']=result.returncode
            record['browser']=json.loads((folder/'browser-report.json').read_text(encoding='utf-8'))
        finally:
            server.shutdown();thread.join(timeout=10);close_server(server)
            with socket.socket() as probe:probe.bind(('127.0.0.1',port));record['listenerStoppedAndPortFree']=True
            (folder/'server-report.json').write_text(json.dumps({k:v for k,v in record.items() if k!='browser'},indent=2),encoding='utf-8')
        reports.append(record)
        summary={'status':'PASS' if all(r['exitCode']==0 for r in reports) else 'FAIL','viewports':reports,'mainRequests8765':sum(r['browser']['mainRequests'] for r in reports)}
        (a.output/'report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        if record['exitCode']:raise RuntimeError('Wallet browser failed for '+size+'; see process/report')
    print(json.dumps({'status':summary['status'],'viewports':len(reports),'requests8765':summary['mainRequests8765']},indent=2))


if __name__=='__main__':main()
