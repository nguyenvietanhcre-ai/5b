"""Run real-browser QA on the exact imported package, then close the isolated server."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
from backend.qa_study import create_server,close_server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('database','questions','manifest','sources','output','node'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    server=create_server(a.database,a.questions,a.manifest,a.sources)
    port=server.server_port;base=f'http://127.0.0.1:{port}/'
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    summary={'url':base,'database':str(server.database_path),'inputSHA256':server.qa_input_sha,'qaOnly':True}
    try:
        cmd=[str(a.node),str(Path(__file__).resolve().parents[1]/'tests/qa-study-browser.cjs'),base,str(a.output.resolve()),str(a.questions.resolve()),str(a.manifest.resolve())]
        temp=a.output.resolve()/'runtime-temp';temp.mkdir(exist_ok=True)
        env=os.environ.copy();env.update(TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
        result=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf-8',env=env)
        (a.output/'browser-process.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        summary['browserExitCode']=result.returncode
        if result.returncode:raise RuntimeError('Browser QA failed; see browser-report.json and browser-process.txt')
    finally:
        server.shutdown();t.join(timeout=10);close_server(server)
        probe=socket.socket()
        try:probe.bind(('127.0.0.1',port));summary['listenerStoppedAndPortFree']=True
        finally:probe.close()
        (a.output/'server-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
