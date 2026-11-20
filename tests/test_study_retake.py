"""Exact owned retake lineage, audit, quota, continuation and lookup ACL."""
import secrets,sqlite3,unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from backend import platform_api as api,study_retake as study
from backend.practice_catalogue import history
import test_family_accounts as base

class StudyRetakeTests(unittest.TestCase):
 PASSWORD=base.FamilyAccountsTests.PASSWORD
 setUp=base.FamilyAccountsTests.setUp
 consent=base.FamilyAccountsTests.consent
 register_body=base.FamilyAccountsTests.register_body
 register=base.FamilyAccountsTests.register
 full=base.FamilyAccountsTests.full
 make_exam=base.FamilyAccountsTests.make_exam
 assert_denied=base.FamilyAccountsTests.assert_denied
 def session(self,c,db):
  c.path='/api/v1/state';c.headers['X-Family-Context']=c.context;return api.read_session(c,db)
 def submitted(self):
  c,state=self.register();eid=self.make_exam(c);c.learner(f'exams/{eid}/submit',{});return c,eid
 def redo(self,c,eid,key):
  with api.connect(self.path,True) as db:return study.retake(db,self.session(c,db),eid,{'requestKey':key})
 def test_exact_pins_history_one_row_old_grade_preserved_and_latest_replaces_visible(self):
  c,eid=self.submitted()
  with api.connect(self.path) as db:
   original=dict(db.execute('SELECT * FROM exam_attempts WHERE exam_id=?',(eid,)).fetchone());oldanswers=[tuple(r) for r in db.execute('SELECT * FROM exam_answers')]
   pins=[tuple(r)[1:] for r in db.execute('SELECT * FROM exam_items WHERE exam_id=? ORDER BY position',(eid,))]
   before={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in ('daily_usage','xp_events','vip_purchases')}
  key=secrets.token_hex(12);res=self.redo(c,eid,key);rid=int(res['exam']['id'])
  self.assertNotEqual(rid,eid);self.assertNotIn('answer',res['exam']['questions'][0])
  self.assertEqual(self.redo(c,eid,key)['exam']['id'],str(rid))
  with api.connect(self.path) as db:
   self.assertEqual(pins,[tuple(r)[1:] for r in db.execute('SELECT * FROM exam_items WHERE exam_id=? ORDER BY position',(rid,))])
   rows=history(db,self.session(c,db)['student_id'],'main');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['id'],str(eid));self.assertEqual(rows[0]['activeRetakeId'],str(rid));self.assertEqual(rows[0]['score'],0)
  c.learner(f'exams/{rid}/answers',{'position':1,'answer':'2','revision':0});c.learner(f'exams/{rid}/submit',{})
  with api.connect(self.path) as db:
   self.assertEqual(dict(db.execute('SELECT * FROM exam_attempts WHERE exam_id=?',(eid,)).fetchone()),original)
   self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM exam_answers WHERE exam_id=?',(eid,))],oldanswers)
   rows=history(db,self.session(c,db)['student_id'],'main');self.assertEqual((len(rows),rows[0]['reference'],rows[0]['score']),(1,'main:'+str(eid),10))
   self.assertIsNone(study.continuation(db,self.session(c,db)))
   for t,values in before.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+t)],values)
 def test_parallel_requests_alias_retry_idempotency_and_foreign_student_rejected(self):
  c,eid=self.submitted();keys=[secrets.token_hex(12),secrets.token_hex(12)]
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda k:self.redo(c.copy_capability(),eid,k),keys))
  self.assertEqual(results[0]['exam']['id'],results[1]['exam']['id'])
  rid=int(results[0]['exam']['id']);c.learner(f'exams/{rid}/submit',{})
  for key in keys:self.assertEqual(self.redo(c,eid,key)['exam']['id'],str(rid))
  self.email='other-'+secrets.token_hex(8)+'@example.test';other,_=self.register()
  self.assert_denied(lambda:self.redo(other,eid,secrets.token_hex(12)),(404,))
  self.assert_denied(lambda:self.redo(c,rid,keys[0]),(409,))
 def test_root_main_api_retake_uses_existing_session_csrf_and_metadata(self):
  c,eid=self.submitted();body={'requestKey':secrets.token_hex(12)}
  result=c.learner(f'exams/{eid}/retake',body)
  self.assertEqual(result['rootExamId'],str(eid));self.assertNotEqual(result['exam']['id'],str(eid))
  self.assertEqual(c.learner(f'exams/{eid}/retake',body)['exam']['id'],result['exam']['id'])
  broken=c.copy_capability();broken.csrf='invalid'
  self.assert_denied(lambda:broken.learner(f'exams/{eid}/retake',{'requestKey':secrets.token_hex(12)}),(403,))
 def test_retired_version_stops_new_retake_while_owned_final_remains_reviewable(self):
  c,eid=self.submitted()
  with api.connect(self.path,True) as db:db.execute("UPDATE question_versions SET status='retired' WHERE id IN (SELECT question_version_id FROM exam_items WHERE exam_id=?)",(eid,))
  self.assert_denied(lambda:self.redo(c,eid,secrets.token_hex(12)),(409,))
  self.assertEqual(c.learner(f'exams/{eid}')['exam']['score'],0)
  with api.connect(self.path) as db:self.assertFalse(history(db,self.session(c,db)['student_id'],'main')[0]['canRetake'])
 def test_unsubmitted_withdrawn_other_active_copyright_form_and_forged_body_rejected(self):
  c,state=self.register();eid=self.make_exam(c)
  self.assert_denied(lambda:self.redo(c,eid,secrets.token_hex(12)),(403,))
  c.learner(f'exams/{eid}/submit',{})
  active=self.make_exam(c)
  self.assert_denied(lambda:self.redo(c,eid,secrets.token_hex(12)),(409,))
  c.learner(f'exams/{active}/submit',{})
  with api.connect(self.path,True) as db:db.execute("UPDATE exams SET status='hidden' WHERE id=?",(eid,))
  self.assert_denied(lambda:self.redo(c,eid,secrets.token_hex(12)),(403,))
  with api.connect(self.path,True) as db:
   form=db.execute("INSERT INTO exam_forms(grade_id,form_code,version,purpose,selection_mode,question_count,duration_minutes,difficulty_mix_json,required_access) VALUES(5,'FORM-REVIEW-ONLY',1,'test','fixed_topics',1,30,'{}','regular')").lastrowid
   db.execute('UPDATE exams SET form_id=? WHERE id=?',(form,active))
  self.assert_denied(lambda:self.redo(c,active,secrets.token_hex(12)),(403,))
  with api.connect(self.path,True) as db:
   self.assert_denied(lambda:study.retake(db,self.session(c,db),active,{'requestKey':secrets.token_hex(12),'studentId':1}),(400,))
 def test_question_code_matches_existing_lookup_only_after_owned_submission(self):
  c,eid=self.submitted()
  with api.connect(self.path,True) as db:
   session=self.session(c,db);payload=study.annotate(db,session,api.exam_view(db,api.owned_attempt(db,session,eid)),'main')
   code=payload['questions'][0]['questionCode'];self.assertRegex(code,r'^5B-M-')
   from backend.practice_export import lookup
   visible=lookup(db,session,code,solutions=False);self.assertNotIn('answer',visible)
   stranger={**session,'student_id':session['student_id']+100}
   self.assert_denied(lambda:lookup(db,stranger,code,solutions=True),(403,404))
 def test_continuation_uses_real_open_unfinished_lesson_else_low_score_and_is_student_scoped(self):
  c,eid=self.submitted()
  with api.connect(self.path,True) as db:
   session=self.session(c,db);self.assertEqual(study.continuation(db,session)['examId'],str(eid))
   db.execute("INSERT INTO lessons(grade_id,kind,week_no,title,body_json,client_key,publication_status) VALUES(4,'weekly',1,'KHÔNG phải lớp của con','[]','study-open-grade4','published')")
   db.execute('UPDATE learning_preferences SET last_lesson=? WHERE student_id=?',('study-open-grade4',session['student_id']))
   self.assertEqual(study.continuation(db,session)['kind'],'retake')
   lesson=db.execute("INSERT INTO lessons(grade_id,kind,week_no,title,body_json,client_key,publication_status) VALUES(5,'weekly',1,'Bài đã mở','[]','study-open-real','published')").lastrowid
   db.execute('UPDATE learning_preferences SET last_lesson=? WHERE student_id=?',('study-open-real',session['student_id']))
   descriptor=study.continuation(db,session);self.assertEqual((descriptor['kind'],descriptor['lessonKey']),('lesson','study-open-real'))
   self.assertEqual(descriptor['title'],'Bài đã mở')
   db.execute('INSERT INTO lesson_progress VALUES(?,?,?)',(session['student_id'],lesson,api.stamp()))
   self.assertEqual(study.continuation(db,session)['kind'],'retake')
   self.assertIsNone(study.continuation(db,{**session,'student_id':session['student_id']+100}))
