"""Explicit QA8-only container launcher, create-only independent database."""
import argparse,json,os
from pathlib import Path
from backend.content_batch_study import create_server,close_server

def main():
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--port',type=int,default=18986);a=p.parse_args()
    if os.environ.get('FIVEBMATH_QA_CONTAINER')!='1':raise ValueError('Explicit QA container flag required')
    server=create_server(a.database,Path('/app/qa-inputs'),Path('/app/round8-inputs'),a.port,bind_host='0.0.0.0')
    (a.database.parent/'confirm-harness-owned.json').write_text(json.dumps({'database':str(a.database.resolve()),'purpose':'confirm-fix-only-v1'}),encoding='utf-8')
    print(json.dumps({'qaOnly':True,'port':server.server_port,'inputSHA':server.qa_input_sha,'import':server.qa_import}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:close_server(server)
if __name__=='__main__':main()
