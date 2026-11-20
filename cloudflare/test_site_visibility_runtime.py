"""Actual local workerd only: persistent hide/reopen and independent admin recovery."""
import argparse,json,secrets,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_runtime import LocalWorker,HTTPClient,fixture_database,transfer_payload
def run(port):
 root=Path(__file__).resolve().parents[1];directory=Path(tempfile.mkdtemp(prefix='maintenance-worker-',dir=root/'work'));worker=None
 report={'status':'running','scope':'Actual workerd, disposable SQLite and synthetic accounts only'}
 try:
  source,fixture,_=fixture_database(directory);payload,_=transfer_payload(source,directory);token=secrets.token_urlsafe(36)
  worker=LocalWorker(directory,port,token,secrets.token_urlsafe(40))
  config_path=worker.project/'wrangler.jsonc';config=json.loads(config_path.read_text(encoding='utf8'));config['vars']['RELEASE_ID']='f'*40;config_path.write_text(json.dumps(config),encoding='utf8')
  worker.start()
  cold=HTTPClient(worker.origin)
  for path in ('/quan-tri/bao-tri','/quan-tri/bao-tri/'):
   assert b'id="login"' in cold.call(path,raw=True)
  assert cold.call('/__ops/status',headers={'Authorization':'Bearer '+token})['tables']=={},'Recovery HTML must not initialize or require a database'
  cold.call('/api/v1/session',expected=503,raw=True)
  worker.stop();del config['vars']['RELEASE_ID'];config_path.write_text(json.dumps(config),encoding='utf8');worker.start()
  ops=HTTPClient(worker.origin);ops.call('/__ops/import',payload,headers={'Authorization':'Bearer '+token})
  admin=HTTPClient(worker.origin);admin.call('/api/staff/site-visibility/login',fixture['admin'])
  before=admin.call('/api/staff/site-visibility')['visibility'];assert before['hidden'] is False
  admin.call('/api/staff/site-visibility',{'hidden':True,'revision':before['revision']})
  guest=HTTPClient(worker.origin)
  for path in ['/api/v1/session','/api/local-pilot/catalogue','/api/site-visibility/check','/api/staff/management']:
   assert b'<html' in guest.call(path,expected=503,raw=True)
  assert b'<html' in guest.call('/api/grade',{'kind':'practice','answers':[]},expected=503,raw=True)
  assert b'<!doctype' in guest.call('/quan-tri/bao-tri/',raw=True)
  worker.stop();worker.start();assert admin.call('/api/staff/site-visibility')['visibility']['hidden'] is True
  renewed=HTTPClient(worker.origin);renewed.call('/api/staff/site-visibility/login',fixture['admin']);state=renewed.call('/api/staff/site-visibility')['visibility']
  renewed.call('/api/staff/site-visibility',{'hidden':False,'revision':state['revision']})
  assert guest.call('/api/v1/session')['authenticated'] is False
  assert admin.call('/api/staff/site-visibility')['visibility']['hidden'] is False
  report.update(status='passed',checks=['Cold recovery portal works with a closed release and no database, without creating tables','Admin-only recovery login and toggle','Main/native/staff/grade blocked with HTML503','Standalone recovery portal remains reachable','Hidden state and admin sessions survive actual workerd restart','Fresh independent admin login reopens normal API'],evidence=str(directory))
  print(json.dumps(report));return 0
 except Exception as e:
  report.update(status='failed',error=type(e).__name__+': '+str(e));print(json.dumps(report));return 1
 finally:
  if worker:worker.stop()
  (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=19069);raise SystemExit(run(parser.parse_args().port))
