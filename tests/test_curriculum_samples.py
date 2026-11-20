"""Access, wallet and owner regressions use disposable, clearly synthetic fixtures.

These arithmetic fixtures test behavior only, not the editorial sample package.
"""
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import json,secrets,threading,unittest
from unittest.mock import patch

from backend import curriculum_samples as samples,platform_api as api
from backend.practice_catalogue import initialize as initialize_practice
import test_local_pilot as legacy_fixture
import test_trial_experience as trial_fixture
from test_trial_experience import Client as TrialClient


def fixture_package():
    topics=[];questions=[]
    for grade in range(1,6):
        tid=f'qa.fixture.g{grade}.C01';topics.append({'id':tid,'grade':grade,'title':f'QA fixture lớp {grade}'})
        for band,(count,access,engine) in samples.BANDS.items():
            for i in range(count):
                q={'id':f'{tid}.{band}.{i:02}','revision':1,'grade':grade,'topicId':tid,'skillId':tid+'.S01',
                   'band':band,'access':access,'difficultyScore':[2,5,7,9][engine-1],
                   'stem':f'[QA FIXTURE ONLY] {grade}+1, item {band} {i}',
                   'responseType':'choice','correctOptionId':'B','answerValue':str(grade+1),'answerText':str(grade+1),
                   'options':[{'id':key,'text':str(value),'value':str(value),'rationale':'Synthetic access-test choice'} for key,value in zip('ABCD',[grade,grade+1,grade+2,grade+3])],
                   'thinking':'QA fixture guidance','keyPoint':'QA fixture key','solutionSteps':[f'{grade}+1={grade+1}'],
                   'check':'QA fixture check','extension':{'prompt':'QA fixture','answer':'QA fixture'},
                   'gradeFit':{'knowledge':['QA fixture'],'reason':'Not authored curriculum content'},
                   'review':{'teacher':'pending','math':'self-checked','author':'assistant','sourceKind':'original-authored'},'diagram':None}
                if i==0 and band=='free-basic':
                    q['diagram']={'svg':'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect x="10" y="10" width="100" height="50" fill="#1F6248"/></svg>',
                                  'alt':'QA rectangle','width':200,'height':100}
                questions.append(q)
    return {'id':samples.BATCH,'revision':1,'topics':topics,'questions':questions,'teacherReview':'pending',
            'authorization':{'localhostUse':True,'fixtureOnly':True},'validation':{'status':'pass'}}


class CurriculumPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):legacy_fixture.LocalPilotTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):legacy_fixture.LocalPilotTests.tearDownClass.__func__(cls)
    actor=legacy_fixture.LocalPilotTests.actor
    call=legacy_fixture.LocalPilotTests.call

    def setUp(self):
        legacy_fixture.LocalPilotTests.setUp(self)
        self.package=fixture_package()
        # Only the exact size guard is bypassed for these five small fixtures.
        # Actual installations must validate all 2,475 authored questions.
        with patch.object(samples,'validate_package',side_effect=lambda p:samples.digest(p)):
            with api.connect(self.main,True) as db:samples.install(db,self.package,pilot=False)
            with api.connect(self.pilot,True) as db:
                initialize_practice(db);samples.install(db,self.package,pilot=True)
        self.provider.practice=samples.CurriculumPractice(self.provider,None,self.package)
        self.provider.choice_required.update(q['id'] for q in self.package['questions'])
        self.provider.knowledge=SimpleNamespace(catalogue=lambda *_:{'topics':[],'lessons':[]})

    def create(self,client,grade,*,pool='free',difficulty=1,category='content',count=3):
        criteria={'intentId':secrets.token_hex(12),'category':category,'count':count,'pool':pool,'difficulty':difficulty}
        if category=='content':criteria['topicKey']=f'qa.fixture.g{grade}.C01'
        quote=self.call(client,'practice/quote',criteria)
        body={'intentId':criteria['intentId'],'requestKey':secrets.token_hex(12),'quoteId':quote['quoteId'],'confirmWallet':False}
        exam=self.call(client,'practice/exams',body)['exam']
        self.assertEqual(exam['responseMode'],'choice')
        return exam,body

    def test_all_five_catalogues_are_grade_bound_and_mcq_without_answers(self):
        for grade in range(1,6):
            c=self.actor(grade=grade);catalogue=self.call(c,'catalogue')
            self.assertEqual(catalogue['grade'],grade);self.assertEqual(len(catalogue['questions']),33)
            self.assertEqual(Counter(q['band'] for q in catalogue['questions']),{b:n for b,(n,_,_) in samples.BANDS.items()})
            self.assertTrue(all(q['responseMode']=='choice' and q['contentKey'].startswith(f'qa.fixture.g{grade}.') for q in catalogue['questions']))
            self.assertFalse(any(set(q)&{'stem','prompt','answer','options','verification','solutionSteps'} for q in catalogue['questions']))
            self.assertEqual(sum(q['eligible'] for q in catalogue['questions']),20)

    def test_free_paid_denial_same_grade_quote_and_daily_quota_are_atomic(self):
        c=self.actor(grade=2)
        with self.assertRaises(api.APIError):self.create(c,2,pool='paid',difficulty=3)
        with self.assertRaises(api.APIError):self.create(c,1)
        exam,body=self.create(c,2)
        self.assertEqual(self.call(c,'practice/exams',body)['exam']['id'],exam['id'])
        with api.connect(self.main) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],1)
        with api.connect(self.pilot) as db:before=db.execute('SELECT count(*) FROM exam_attempts').fetchone()[0]
        with self.assertRaises(api.APIError):self.create(c,2)
        with api.connect(self.pilot) as db:self.assertEqual(db.execute('SELECT count(*) FROM exam_attempts').fetchone()[0],before)
        with api.connect(self.main) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],1)

    def test_hsg_is_paid_and_vip_debits_once_with_owned_review_only(self):
        c=self.actor('VIP',grade=4);other=self.actor(grade=4)
        exam,body=self.create(c,4,pool='paid',difficulty=4)
        self.assertEqual(len(exam['questions']),3)
        for question in exam['questions']:
            self.assertEqual(question['responseMode'],'choice');self.assertEqual(len(question['options']),4)
            self.assertEqual(question['sampleBand'],'paid-hsg');self.assertNotIn('answer',question)
            self.assertNotIn('thinking',question);self.assertEqual(question['teacherReview'],'pending')
        with self.assertRaises(api.APIError):self.call(other,'exams/'+exam['id'])
        with api.connect(self.pilot) as db:self.assertEqual(db.execute("SELECT count(*) FROM wallet_debits WHERE source='vip'").fetchone()[0],3)
        self.call(c,'practice/exams',body)
        with api.connect(self.pilot) as db:self.assertEqual(db.execute("SELECT count(*) FROM wallet_debits WHERE source='vip'").fetchone()[0],3)
        for i in range(1,4):self.call(c,'exams/'+exam['id']+'/answers',{'position':i,'answer':'5'})
        result=self.call(c,'exams/'+exam['id']+'/submit',{})['exam']
        self.assertEqual(result['score'],10)
        self.assertTrue(all(q.get('keyPoint') and q.get('check') for q in result['questions']))

    def test_hash_tamper_retires_eligibility_and_free_new_items_cannot_request_typed(self):
        c=self.actor(grade=5)
        with self.assertRaises(api.APIError):self.call(c,'quote',{'contentKeys':['qa.fixture.g5.C01.free-basic.01'],'responseMode':'typed'})
        with api.connect(self.pilot,True) as db:
            identity=db.execute("SELECT version_id FROM curriculum_sample_versions WHERE content_key='qa.fixture.g5.C01.free-basic.01'").fetchone()[0]
            db.execute('UPDATE question_versions SET prompt_json=? WHERE id=?',('[{"type":"text","text":"tampered"}]',identity))
        catalogue=self.call(c,'catalogue')
        self.assertFalse(next(q for q in catalogue['questions'] if q['contentKey']=='qa.fixture.g5.C01.free-basic.01')['eligible'])

    def test_private_diagrams_are_given_only_to_own_attempt_without_answers(self):
        c=self.actor(grade=1)
        exam,_=self.create(c,1,count=10)
        # Deterministic selection of all basic items includes the diagram.
        figures=[q['sampleDiagram'] for q in exam['questions'] if q.get('sampleDiagram')]
        self.assertEqual(len(figures),1);self.assertTrue(figures[0]['dataUrl'].startswith('data:image/svg+xml;base64,'))
        self.assertTrue(all('answer' not in q for q in exam['questions']))

    def test_main_free_export_retains_its_exact_diagram_and_three_part_solution(self):
        from backend.practice_export import snapshot_item,safe_question
        with api.connect(self.main) as db:
            row=db.execute('SELECT 1 position,v.*,q.question_code,t.title topic_title FROM curriculum_sample_versions s '
                'JOIN question_versions v ON v.id=s.version_id JOIN questions q ON q.id=v.question_id '
                'JOIN topics t ON t.id=q.topic_id WHERE s.grade=1 AND s.diagram_sha256 IS NOT NULL').fetchone()
            payload=snapshot_item(db,{'exam_id':0,'grade_level':1,'response_mode':'choice'},row,'main',Path('frontend'))
            self.assertEqual([s['key'] for s in payload['lesson']['sections']],['thinking','key','detail'])
            self.assertEqual(len(payload['assets']),1)
            public=safe_question(payload,'QA-EXPORT',False)
            self.assertEqual(len(public['options']),4)
            self.assertNotIn('answer',public);self.assertNotIn('lesson',public)


class CurriculumTrialTests(unittest.TestCase):
    setUp=trial_fixture.TrialTests.setUp
    tearDown=trial_fixture.TrialTests.tearDown

    def test_cleanup_worker_waits_for_cutover_unfreeze_before_deleting_expired_rows(self):
        from backend import trial_experience as trial
        self.client.call('session',{})
        frozen=threading.Event();frozen.set();observed=threading.Event();cleaned=threading.Event()
        original=trial.cleanup
        def is_frozen():observed.set();return frozen.is_set()
        def cleanup_future(db,at=None):
            original(db,self.server.at+8*trial.DAY);cleaned.set()
        with patch.object(trial,'cleanup',side_effect=cleanup_future):
            worker,stop=trial.start_cleanup_worker(self.path,interval_seconds=1,frozen=is_frozen)
            try:
                self.assertTrue(observed.wait(5));self.assertFalse(cleaned.is_set())
                with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM trial_sessions').fetchone()[0],1)
                frozen.clear();self.assertTrue(cleaned.wait(5))
            finally:stop.set();worker.join(5)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM trial_sessions').fetchone()[0],0)

    def test_only_free_mcq_per_grade_and_stale_grade_answer_is_rejected(self):
        package=fixture_package()
        with patch.object(samples,'loaded_package',return_value=package):
            for grade in range(1,6):
                content=samples.trial_content(grade)
                self.assertEqual(len(content['questions']),20)
                self.assertTrue(all(q['grade']==grade and '.free-' in q['id'] and len(q['options'])==4 for q in content['questions']))
                self.assertEqual(len(content['lesson']['options']),4)
                self.assertTrue(content['lesson']['id'].startswith(f'qa.fixture.g{grade}.'))
                self.assertTrue(content['lesson']['sampleDiagram']['dataUrl'].startswith('data:image/svg+xml;base64,'))
            self.client.call('session',{})
            self.client.post('grade',grade=2)
            state,_=self.client.post('practice/start')
            attempt=state['activities']['practice'];question=attempt['currentQuestion']
            self.assertEqual(state['grade'],2);self.assertEqual(question['responseMode'],'choice')
            self.assertNotIn('answer',question)
            with self.assertRaises(api.APIError):self.client.post('practice/answer',attemptId=attempt['id'],questionId=question['id'],answer='not-a-choice')
            self.client.post('grade',grade=1)
            with self.assertRaises(api.APIError):self.client.post('practice/answer',attemptId=attempt['id'],questionId=question['id'],answer='3')
            restored,_=self.client.post('grade',grade=2)
            self.assertEqual(restored['activities']['practice']['id'],attempt['id'])
            restarted,_=self.client.post('practice/start')
            self.assertEqual(restarted['activities']['practice']['id'],attempt['id'])
            self.client.post('lesson/complete')
            grade1,_=self.client.post('grade',grade=1)
            self.assertFalse(grade1['lessonComplete'])
            grade2,_=self.client.post('grade',grade=2)
            self.assertTrue(grade2['lessonComplete'])
            # Real browser radio values are full option text, never an index.
            option=question['options'][0]
            answered,_=self.client.post('practice/answer',attemptId=attempt['id'],questionId=question['id'],answer=option)
            self.assertEqual(len(answered['activities']['practice']['results']),1)


if __name__=='__main__':unittest.main()
