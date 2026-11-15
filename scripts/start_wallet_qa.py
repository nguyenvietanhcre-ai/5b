"""Launch QA UI only on loopback, with NEW fake DB and progressing QA clock."""
import argparse
import json
import os
from pathlib import Path
from backend.wallet_study import create_server,close_server


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True)
    p.add_argument('--questions',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True)
    p.add_argument('--port',type=int,default=18955)
    p.add_argument('--status-file',type=Path)
    a=p.parse_args()
    server=create_server(a.database,a.questions,a.manifest,a.sources,a.port)
    status={'url':f'http://127.0.0.1:{server.server_port}/','pid':os.getpid(),'database':str(server.database_path),
        'qaOnly':True,'label':'Ví QA — không chuyển tiền','inputSHA256':server.qa_input_sha}
    if a.status_file:a.status_file.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False,indent=2),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:close_server(server)


if __name__=='__main__':main()
