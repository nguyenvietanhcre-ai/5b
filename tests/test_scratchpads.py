import copy,json,secrets,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from backend.database import initialize
from backend import platform_api as api,scratchpads

class AccountScratchpads(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'qa.sqlite3';initialize(cls.path);api.seed_catalog(cls.path)
  def user():
   h=SimpleNamespace(server=SimpleNamespace(database_path=cls.path),client_address=('scratch-'+secrets.token_hex(5),1),headers={'Host':'localhost:8765','Origin':'http://localhost:8765'},api_headers={})
   with api.connect(cls.path,True) as db:api.register(h,db,{'login':'scratch-'+secrets.token_hex(5),'password':secrets.token_urlsafe(24),'name':'QA Nháp','birthYear':api.academic()[0]-9})
   h.headers['Cookie']=h.api_headers['Set-Cookie'].split(';')[0]
   with api.connect(cls.path) as db:return dict(api.read_session(h,db))
  cls.owner=user();cls.other=user()
  with api.connect(cls.path,True) as db:cls.eid=int(api.create_exam(db,cls.owner,{'requestKey':secrets.token_hex(12),'category':'content','maxWeek':35,'count':3,'difficulty':0})['id'])
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def note(self,text='Nháp'):return {'version':1,'open':True,'text':text,'color':'#203a32','strokes':[{'color':'#203a32','points':[{'x':.1,'y':.2},{'x':.8,'y':.9}]}]}
 def test_revision_retry_and_ownership(self):
  with api.connect(self.path,True) as db:
   get=lambda user:self.call(db,user,'GET',None,{'position':['1']})
   initial=get(self.owner)['scratch'];body={'position':1,'revision':initial['revision'],'requestKey':secrets.token_hex(12),'note':self.note()}
   before={t:[tuple(x) for x in db.execute('SELECT * FROM '+t)] for t in ('exam_attempts','exam_draft_answers','exam_answers')}
   first=self.call(db,self.owner,'POST',body);self.assertEqual(first,self.call(db,self.owner,'POST',body))
   stale={**body,'requestKey':secrets.token_hex(12),'note':self.note('stale')};result=self.call(db,self.owner,'POST',stale);self.assertTrue(result['conflict']);self.assertEqual(result['scratch']['note'],body['note'])
   with self.assertRaises(api.APIError):get(self.other)
   with self.assertRaises(api.APIError):self.call(db,self.other,'POST',body)
   for t,rows in before.items():self.assertEqual(rows,[tuple(x) for x in db.execute('SELECT * FROM '+t)])
 def call(self,db,user,method,body=None,query=None):return scratchpads.access(db,user,self.eid,method,body,query)
 def test_validation_and_question_pin(self):
  with api.connect(self.path,True) as db:
   base={'position':2,'revision':0,'requestKey':secrets.token_hex(12),'note':self.note()}
   cases=[]
   for field,value in [('position',999),('position',True),('revision',True),('requestKey','x')]:cases.append({**base,field:value})
   for note in [{**self.note(),'text':'x'*20001},{**self.note(),'color':'red'},{**self.note(),'secret':'x'},{**self.note(),'strokes':[{'color':'#203a32','points':[{'x':float('nan'),'y':0}]}]}]:cases.append({**base,'note':note})
   for body in cases:
    with self.subTest(body=list(body)),self.assertRaises(api.APIError):self.call(db,self.owner,'POST',body)
 def test_large_vectors_and_clear(self):
  with api.connect(self.path,True) as db:
   note=self.note();note['strokes'][0]['points']=[{'x':i/2000,'y':.3} for i in range(2000)];body={'position':3,'revision':0,'requestKey':secrets.token_hex(12),'note':note};self.assertGreater(len(json.dumps(body)),16384)
   result=self.call(db,self.owner,'POST',body);self.assertEqual(result['scratch']['note'],note)
   body.update(revision=result['scratch']['revision'],requestKey=secrets.token_hex(12),note={**self.note(''),'strokes':[]});self.call(db,self.owner,'POST',body)
   saved=self.call(db,self.owner,'GET',query={'position':['3']})['scratch']['note'];self.assertEqual(saved['text'],'');self.assertEqual(saved['strokes'],[])
