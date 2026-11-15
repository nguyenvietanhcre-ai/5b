import sys,json,tempfile,unittest,base64,io,secrets,copy
from pathlib import Path
R=Path(__file__).resolve().parents[1]
from backend import platform_api as api,practice_export as export
from backend.database import initialize
from pypdf import PdfReader
from types import SimpleNamespace

class Exports(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  (R/'work/pdf-export-tests').mkdir(parents=True,exist_ok=True);cls.tmp=tempfile.TemporaryDirectory(dir=R/'work/pdf-export-tests');cls.path=Path(cls.tmp.name)/'fake.sqlite3';initialize(cls.path);api.seed_catalog(cls.path)
  cls.server=SimpleNamespace(database_path=cls.path,review_upgrades=True)
  def user():
   handler=SimpleNamespace(server=cls.server,client_address=('export-qa-'+secrets.token_hex(3),123),headers={'Host':'localhost:8765','Origin':'http://localhost:8765'},api_headers={})
   with api.connect(cls.path,True) as db:
    result=api.register(handler,db,{'login':'export-unit-'+secrets.token_hex(6),'password':secrets.token_urlsafe(20),'name':'QA Xuất đề','birthYear':api.academic()[0]-9})
    cookie=handler.api_headers['Set-Cookie'].split(';')[0]
   handler.headers['Cookie']=cookie
   with api.connect(cls.path) as db:return dict(api.read_session(handler,db))
  cls.owner=user();cls.stranger=user()
  with api.connect(cls.path,True) as db:
   export.initialize(db);exam=api.create_exam(db,cls.owner,{'requestKey':'export-fixture-'+secrets.token_hex(5),'count':3,'difficulty':0,'category':'content','maxWeek':35});cls.eid=exam['id'];db.execute('DELETE FROM question_assets WHERE question_version_id IN (SELECT question_version_id FROM exam_items WHERE exam_id=?)',(cls.eid,))
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def call(self,include=False,extra=None):
  with api.connect(self.path,True) as db:return export.export_pdf(db,self.owner,{'provider':'main','attemptId':self.eid,'includeSolutions':include,**(extra or {})},provider='main',frontend=R/'frontend')
 def text(self,result):return '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(base64.b64decode(result['pdfBase64']))).pages)
 def test_01_default_no_answer_projection_or_pdf_payload(self):
  result=self.call();text=self.text(result);self.assertNotIn('Đáp án:',text);self.assertNotIn('PRIVATE EXPORT SOLUTION SENTINEL',text);self.assertNotIn('Lời giải của đúng phiên bản đề',text)
  reader=PdfReader(io.BytesIO(base64.b64decode(result['pdfBase64'])));self.assertNotIn('/EmbeddedFiles',str(reader.trailer));self.assertNotIn('/JavaScript',str(reader.trailer));self.assertTrue(result['filename'].endswith('.pdf'))
  with api.connect(self.path) as db:
   code=result['codes'][0]['code'];lookup=export.lookup(db,self.owner,code);self.assertNotIn('answer',lookup['question']);self.assertNotIn('steps',lookup['question']);self.assertNotIn('lesson',lookup['question'])
 def test_02_strict_boolean(self):
  for value in ['false','true',0,1,None,[],{}]:
   with self.subTest(value=value),self.assertRaises(api.APIError):self.call(value)
 def test_03_explicit_solutions_stable_codes(self):
  plain=self.call();full=self.call(True);self.assertEqual(plain['codes'],full['codes']);text=self.text(full);self.assertIn('Đáp án:',text);self.assertIn('Các bước giải đã lưu',text)
 def test_04_forbidden_unknown_and_case_space_normalization(self):
  code=self.call()['codes'][0]['code']
  with api.connect(self.path) as db:
   for owner,value in [(self.stranger,code),(self.owner,'5B-M-AAAA-BBBB-CCCC')]:
    with self.assertRaises(api.APIError) as error:export.lookup(db,owner,value,solutions=True)
    self.assertEqual(error.exception.status,404)
   self.assertEqual(export.lookup(db,self.owner,' '+code.lower().replace('-',' ')+' ')['question']['code'],code)
 def test_05_no_game_wallet_quota_submission_or_xp_writes(self):
  def snapshot(db):
   tables=['exam_attempts','exam_draft_answers','exam_answers','xp_events','student_companions','usage_events'];return {table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in tables if export.exists(db,table)}
  with api.connect(self.path) as db:before=snapshot(db);normal=api.exam_view(db,api.owned_attempt(db,self.owner,int(self.eid)));self.assertTrue(all('answer' not in q for q in normal['questions']))
  self.call(True);self.call()
  with api.connect(self.path) as db:self.assertEqual(before,snapshot(db));self.assertTrue(all('answer' not in q for q in api.exam_view(db,api.owned_attempt(db,self.owner,int(self.eid)))['questions']))
 def test_06_unproven_historical_or_foreign_owner_denied(self):
  with api.connect(self.path,True) as db:
   db.execute('UPDATE exams SET owner_student_id=NULL WHERE id=?',(self.eid,))
   try:
    with self.assertRaises(api.APIError) as error:export.export_pdf(db,self.owner,{'provider':'main','attemptId':self.eid},provider='main',frontend=R/'frontend')
    self.assertEqual(error.exception.status,403)
   finally:db.execute('UPDATE exams SET owner_student_id=? WHERE id=?',(self.owner['student_id'],self.eid))
 def test_07_code_revision_and_option_order(self):
  with api.connect(self.path) as db:row=db.execute('SELECT payload_json FROM practice_export_codes LIMIT 1').fetchone();payload=json.loads(row[0])
  same=copy.deepcopy(payload);same['options']=list(reversed(same['options']));self.assertEqual(export.identity(payload),export.identity(same));same['revision']+=1;self.assertNotEqual(export.identity(payload)[0],export.identity(same)[0])
 def test_08_solution_only_legacy_asset_excluded(self):
  payload={'provider':'main','revision':1,'grade':4,'topicTitle':'Ví dụ','text':'Đề','prompt':[{'type':'text','text':'Đề'}],'responseMode':'typed','options':[],'assets':{'legacy:1':{'mime':'image/svg+xml','data':'PRIVATE','url':'private.svg'}}};self.assertEqual(export.safe_question(payload,'code')['assets'],{})
 def test_09_assigned_nonpractice_attempt_cannot_unlock_lookup(self):
  code=self.call()['codes'][0]['code']
  with api.connect(self.path,True) as db:
   assigned=db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,mode,owner_student_id,created_at,response_mode) SELECT ?,title,grade_level,duration_minutes,status,mode,NULL,created_at,response_mode FROM exams WHERE id=?",('ASSIGNED-'+secrets.token_hex(6),self.eid)).lastrowid
   db.execute('INSERT INTO exam_items SELECT ?,position,question_version_id,max_points,options_json FROM exam_items WHERE exam_id=?',(assigned,self.eid))
   db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES (?,?,?,?,'in_progress',?)",(assigned,self.stranger['student_id'],api.stamp(),api.stamp(api.now()+__import__('datetime').timedelta(minutes=30)),'assigned-'+secrets.token_hex(5)))
   try:
    with self.assertRaises(api.APIError) as error:export.lookup(db,self.stranger,code,solutions=True)
    self.assertEqual(error.exception.status,404)
   finally:
    db.execute('DELETE FROM exam_attempts WHERE exam_id=?',(assigned,))
    db.execute('DELETE FROM exam_items WHERE exam_id=?',(assigned,))
    db.execute('DELETE FROM exams WHERE id=?',(assigned,))
 def test_10_removed_print_only_notice_does_not_change_snapshot(self):
  from backend.practice_pdf import render_pdf
  plain=self.call();self.assertNotIn('Học liệu thí điểm tự biên soạn, chưa có giáo viên độc lập duyệt.',self.text(plain))
  with api.connect(self.path) as db:payload=json.loads(db.execute('SELECT payload_json FROM practice_export_codes LIMIT 1').fetchone()[0])
  payload['provider']='pilot';data=render_pdf({'title':'Luyện tập','examCode':'PILOT-SOURCE-COPY','grade':5,'questions':[{'code':'5B-P-AAAA-BBBB-CCCC','payload':payload}]},include_solutions=False,frontend=R/'frontend')
  text=self.text({'pdfBase64':base64.b64encode(data).decode()});self.assertNotIn('Học liệu thí điểm tự biên soạn, chưa có giáo viên độc lập duyệt.',text);self.assertNotIn('Họ và tên:',text);self.assertNotIn(' · Phiên bản ',text);self.assertIn('5B-P-AAAA-BBBB-CCCC',text);self.assertEqual(payload['provider'],'pilot');self.assertIn('revision',payload)

if __name__=='__main__':unittest.main(verbosity=2)
