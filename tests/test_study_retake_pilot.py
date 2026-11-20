"""Real family session -> pilot retake with no allocation or new wallet usage."""
import json,secrets,unittest
from backend import platform_api as api,study_retake as study
from backend.knowledge_catalogue import Knowledge,SCHEMA
import test_family_local_pilot as base

class PilotStudyRetakeTests(unittest.TestCase):
 PASSWORD=base.FamilyLocalPilotTests.PASSWORD
 setUpClass=classmethod(base.FamilyLocalPilotTests.setUpClass.__func__)
 setUp=base.FamilyLocalPilotTests.setUp
 family_actor=base.FamilyLocalPilotTests.family_actor
 call=base.FamilyLocalPilotTests.call
 quote_body=base.FamilyLocalPilotTests.quote_body
 exam=base.FamilyLocalPilotTests.exam
 def test_real_pilot_retake_versions_revision_history_and_ledger_no_debit(self):
  client,state=self.family_actor();exam,_=self.exam(client)
  self.call(client,'exams/'+exam['id']+'/submit',{})
  with api.connect(self.pilot,True) as db:
   from backend.practice_catalogue import initialize
   initialize(db)
   for row in db.execute('SELECT i.position,c.content_key FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id JOIN pilot_content c ON c.question_id=v.question_id WHERE i.exam_id=?',(exam['id'],)).fetchall():
    db.execute('INSERT INTO practice_exam_items VALUES(?,?,?,?,?)',(int(exam['id']),row['position'],row['content_key'],'choice','Pin đề đã sở hữu'))
  with api.connect(self.pilot) as db:
   original=dict(db.execute('SELECT * FROM exam_attempts WHERE exam_id=?',(exam['id'],)).fetchone())
   pins=[tuple(r)[1:] for r in db.execute('SELECT * FROM exam_items WHERE exam_id=? ORDER BY position',(exam['id'],))]
   tables=('pilot_grants','wallet_debits','wallet_attempt_receipts','pilot_requests','daily_usage')
   ledger={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in tables}
  key=secrets.token_hex(12);retake=self.call(client,'exams/'+exam['id']+'/retake',{'requestKey':key})['exam']
  self.assertNotEqual(retake['id'],exam['id']);self.assertEqual([q['options'] for q in retake['questions']],[q['options'] for q in exam['questions']])
  self.assertEqual(self.call(client,'exams/'+exam['id']+'/retake',{'requestKey':key})['exam']['id'],retake['id'])
  with self.assertRaises(api.APIError):self.call(client,'exams/'+retake['id']+'/answers',{'position':1,'answer':retake['questions'][0]['options'][0]})
  self.call(client,'exams/'+retake['id']+'/answers',{'position':1,'answer':retake['questions'][0]['options'][0],'revision':0})
  self.call(client,'exams/'+retake['id']+'/submit',{})
  review=self.call(client,'exams/'+retake['id']+'/review')['exam'];self.assertRegex(review['questions'][0]['questionCode'],r'^5B-P-')
  with api.connect(self.pilot) as db:
   self.assertEqual(pins,[tuple(r)[1:] for r in db.execute('SELECT * FROM exam_items WHERE exam_id=? ORDER BY position',(retake['id'],))])
   self.assertEqual([tuple(r)[1:] for r in db.execute('SELECT * FROM practice_exam_items WHERE exam_id=? ORDER BY position',(exam['id'],))],[tuple(r)[1:] for r in db.execute('SELECT * FROM practice_exam_items WHERE exam_id=? ORDER BY position',(retake['id'],))])
   self.assertEqual(dict(db.execute('SELECT * FROM exam_attempts WHERE exam_id=?',(exam['id'],)).fetchone()),original)
   for t,rows in ledger.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+t)],rows,t)
   from backend.practice_catalogue import history
   sid=db.execute('SELECT student_id FROM exam_attempts WHERE exam_id=?',(exam['id'],)).fetchone()[0]
   items=history(db,sid,'pilot');self.assertEqual((len(items),items[0]['id'],items[0]['rootExamId']),(1,retake['id'],exam['id']))
 def test_knowledge_open_tracking_continuation_checks_completion_grade_and_sibling_isolation(self):
  client,state=self.family_actor()
  self.call(client,'catalogue')
  with api.connect(self.pilot,True) as db:
   for sql in SCHEMA:db.execute(sql)
   sid=db.execute('SELECT pilot_student_id FROM local_principals WHERE main_student_id=?',(state['selectedChildId'],)).fetchone()[0]
   value={'lessonKey':'study.actual-open','topicKey':'fixture','title':'Bài học đã mở thật','revision':1,'sections':[],
     'fixed':{'questionKey':'study.fixed','revision':1,'prompt':'Tính 1 + 1','responseMode':'typed','inputGuide':{},'correctAnswer':'2','solution':[]}}
   db.execute('INSERT INTO knowledge_lessons VALUES(?,?,?,?,?)',(value['lessonKey'],1,'fixture','fixture-hash',api.packed(value)))
   knowledge=object.__new__(Knowledge);knowledge.provider=self.provider
   knowledge.lesson(db,{'student_id':sid},value['lessonKey'])
  client.path='/api/v1/state';client.headers['X-Family-Context']=client.context
  with api.connect(self.main) as main:
   session=api.read_session(client,main);result=study.continuation(main,session,self.provider)
   self.assertEqual((result['kind'],result['provider'],result['lessonKey']),('lesson','pilot',value['lessonKey']))
   self.assertIn('lessonRevision=1',result['href']);self.assertNotIn('answer',str(result))
  with api.connect(self.pilot,True) as db:
   knowledge.check(db,{'student_id':sid},value['lessonKey'],{'requestKey':secrets.token_hex(12),'lessonRevision':1,'answer':'2'})
  with api.connect(self.main) as main:self.assertIsNone(study.continuation(main,session,self.provider))
  with api.connect(self.pilot,True) as db:
   db.execute('DELETE FROM knowledge_checks WHERE student_id=?',(sid,))
  with api.connect(self.main,True) as main:
   main.execute('UPDATE family_children SET declared_grade=4 WHERE student_id=?',(state['selectedChildId'],))
   self.assertIsNone(study.continuation(main,session,self.provider))
