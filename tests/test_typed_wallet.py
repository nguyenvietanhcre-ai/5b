"""Round6 integration on the actual ten questions, new synthetic DB per test."""
import copy,json,os,secrets,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from backend import platform_api as api
from backend import answers
from backend.typed_wallet_study import create_server,close_server
from backend.mcq_import import import_package,load_json,ImportFailure
from scripts.free_vip_smoke import HTTPClient

class TypedWalletIntegrationTests(unittest.TestCase):
    def setUp(self):
        folder=os.environ.get('FIVEBMATH_QA_TYPED_INPUT_DIR')
        if not folder:self.skipTest('Supply FIVEBMATH_QA_TYPED_INPUT_DIR')
        self.inputs=Path(folder);Path('work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir='work')
        self.server=create_server(Path(self.temp.name)/'qa.sqlite3',*(self.inputs/f for f in ('questions-typed.json','sample-sets-typed.json','sources.json')))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.package=load_json(self.inputs/'questions-typed.json');self.manifest=load_json(self.inputs/'sample-sets-typed.json')
        self.bykey={q['contentKey']:q for q in self.package['questions']}
    def tearDown(self):
        if hasattr(self,'server'):self.server.shutdown();self.thread.join();close_server(self.server);self.temp.cleanup()
    def client(self,profile='binh'):
        c=HTTPClient(self.base);c.call('/qa-api/bootstrap');c.call('/qa-api/profiles/select',{'profileId':profile});return c
    def exam(self,c,**selector):
        q=c.call('/qa-api/wallet/quote',selector)
        return c.call('/api/v1/exams',dict(selector,requestKey=secrets.token_hex(12),quoteId=q['quoteId'],confirmWallet=bool(q['private'])))['exam']
    def save(self,c,e,p,value,expected=200):return c.call('/api/v1/exams/'+e['id']+'/answers',{'position':p,'answer':value},expected=expected)
    def test_actual_mapping_rules_and_safe_guide(self):
        original=load_json(self.inputs/'originals/questions-mcq.json')['questions']
        self.assertEqual(len(self.bykey),10);self.assertEqual(sum(q['answerKind']=='ordered' for q in self.bykey.values()),6)
        for old in original:
            q=self.bykey[old['contentKey']];self.assertEqual(q['quotaKey'],old['quotaKey']);self.assertEqual(q['sourceContentKey'],old['sourceContentKey']);self.assertEqual(q['sourceRevision'],old['sourceRevision'])
            self.assertEqual(q['prompt'],old['prompt']);self.assertEqual(q['revision'],3)
            self.assertTrue(answers.matches(q['correctAnswer'],{'answer':q['correctAnswer'],'answerKind':q['answerKind']}))
            self.assertNotIn(q['correctAnswer'],json.dumps(q['inputGuide'],ensure_ascii=False))
            if q['answerKind']=='ordered':self.assertFalse(answers.matches(';'.join(q['correctAnswer'].split(';')[::-1]),{'answer':q['correctAnswer'],'answerKind':'ordered'}))
    def test_typed_save_zero_delete_limit_owner_and_score(self):
        c=self.client();other=self.client('chi');e=self.exam(c,setIndex=1)
        self.assertEqual(e['responseMode'],'typed')
        for q in e['questions']:
            self.assertFalse(set(q)&{'options','answer','correctAnswer','gradingRule','solutionSteps'});self.assertIn('inputGuide',q)
        self.assertEqual(c.call('/qa-api/choice-labels/'+e['id']),{'labels':{}})
        c.call('/qa-api/review/'+e['id'],expected=403)
        self.save(c,e,1,'0');self.assertEqual(c.call('/api/v1/exams/'+e['id'])['exam']['answers']['1'],'0')
        self.save(c,e,1,'');self.assertFalse(c.call('/api/v1/exams/'+e['id'])['exam']['answers'].get('1'))
        self.save(c,e,1,'x'*501,400);self.save(c,e,1,42,400);self.save(c,e,1,{'x':1},400)
        for i,key in enumerate(self.manifest['orderedContentKeys']):
            q=self.bykey[key];value=q['correctAnswer'] if i%2==0 else '0'
            if q['answerKind']=='number' and i%2==0:value=str(int(value)*2)+'/2'
            self.save(c,e,i+1,value)
        before=c.call('/qa-api/wallet');done=c.call('/api/v1/exams/'+e['id']+'/submit',{})['exam'];self.assertEqual(done['score'],6)
        again=c.call('/api/v1/exams/'+e['id']+'/submit',{})['exam'];self.assertEqual(again['score'],6)
        review=c.call('/qa-api/review/'+e['id']);self.assertEqual(len(review['questions']),5)
        self.assertTrue(all('choices' not in q and 'correctText' in q for q in review['questions']))
        self.assertEqual(c.call('/qa-api/wallet')['privateRemaining'],before['privateRemaining'])
        other.call('/qa-api/review/'+e['id'],expected=404)
    def test_old_choice_submitted_score_is_not_regraded(self):
        c=self.client('an');eid=self.server.qa_legacy_history['an']
        old=c.call('/api/v1/exams/'+eid)['exam'];self.assertEqual((old['responseMode'],old['score']),('choice',6))
        self.assertTrue(all(len(q['options'])==4 for q in old['questions']))
        with patch('backend.answers.matches',side_effect=AssertionError('Must not regrade')):
            self.assertEqual(c.call('/api/v1/exams/'+eid+'/submit',{})['exam']['score'],6)
            review=c.call('/qa-api/review/'+eid);self.assertEqual(review['responseMode'],'choice')
        self.assertEqual([q['revision'] for q in review['questions']],[2]*5)
    def test_old_choice_pending_can_still_save_submit(self):
        c=self.client('chi');eid=self.server.qa_legacy_history['chi'];e=c.call('/api/v1/exams/'+eid)['exam']
        self.assertEqual(e['responseMode'],'choice');self.save(c,e,2,e['questions'][1]['options'][0])
        done=c.call('/api/v1/exams/'+eid+'/submit',{})['exam'];self.assertTrue(done['submittedAt'])
        self.assertEqual(c.call('/qa-api/review/'+eid)['responseMode'],'choice')
    def test_paid_mcq_to_typed_same_key_one_debit_and_old_replay(self):
        self.server.shutdown();self.thread.join();close_server(self.server)
        from backend.wallet_study import create_server as mcq_server
        self.server=mcq_server(Path(self.temp.name)/'old-first.sqlite3',self.inputs/'originals/questions-mcq.json',self.inputs/'history-sets.json',self.inputs/'sources.json')
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        c=self.client();key=self.manifest['vipSupplementContentKeys'][0]
        # Obtain old revision2 via original historical snapshot, on owned QA clock only.
        self.server.qa_clock.anchor=self.server.qa_clock.anchor.replace(day=9)
        from dataclasses import replace
        self.server.free_vip_pilot=replace(self.server.free_vip_pilot,response_mode='choice')
        old=self.exam(c,contentKeys=[key]);self.assertEqual(old['responseMode'],'choice')
        before=c.call('/qa-api/wallet');self.assertEqual(before['vip']['dayUsed'],1)
        import_package(self.server.database_path,self.package,self.manifest,load_json(self.inputs/'sources.json'),allow_draft_qa=True)
        self.server.qa_clock.anchor=self.server.qa_clock.anchor.replace(day=16)
        self.server.free_vip_pilot=replace(self.server.free_vip_pilot,response_mode='typed')
        c=self.client() # QA clock advanced seven days; obtain fresh session, same owner.
        typed=self.exam(c,contentKeys=[key]);self.assertEqual(typed['responseMode'],'typed')
        receipt=c.call('/qa-api/wallet/receipts/'+typed['id'])['allocation'];self.assertEqual((receipt['retained'],receipt['vip'],receipt['private']),(1,0,0))
        self.save(c,typed,1,self.bykey[key]['correctAnswer']);self.assertEqual(c.call('/api/v1/exams/'+typed['id']+'/submit',{})['exam']['score'],10)
        replay=self.exam(c,replayExamId=int(old['id']));self.assertEqual(replay['responseMode'],'choice');self.assertEqual(len(replay['questions'][0]['options']),4)
    def test_import_replay_invalid_guide_draft_and_atomic(self):
        sources=load_json(self.inputs/'sources.json')
        result=import_package(self.server.database_path,self.package,self.manifest,sources,allow_draft_qa=True);self.assertEqual(result['insertedVersions'],0)
        bad=copy.deepcopy(self.package);bad['questions'][0]['inputGuide']['separator']='wrong'
        with self.assertRaises(ImportFailure):import_package(self.server.database_path,bad,self.manifest,sources,allow_draft_qa=True)
        with self.assertRaises(ImportFailure):import_package(self.server.database_path,self.package,self.manifest,sources,allow_draft_qa=False)
        with api.connect(self.server.database_path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM mcq_versions').fetchone()[0],20)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
