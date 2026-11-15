"""Mechanical unit fixtures only; final authored package has separate integration evidence."""
from copy import deepcopy
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,secrets,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend import platform_api as api,wallet_qa as wallet
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.content_batch_qa import validate_batch,import_batch,preview_batch
from backend.mcq_import import ImportFailure,validate
from scripts.import_mcq_qa import initialize_empty_qa
from scripts.mcq_fixture import fixture
from test_free_vip_pilot import Client

NOW=datetime(2026,11,23,5,tzinfo=timezone.utc)

def batch_fixture():
    p,m,s=fixture();q0=deepcopy(p['questions']);s0=deepcopy(s['questions']);p['questions']=[];s['questions']=[]
    for i in range(60):
        q=deepcopy(q0[i%10]);source=deepcopy(s0[i%10]);key=f'qa.batch.{i:02}'
        q.update(contentKey=key,sourceContentKey=key,quotaKey=key,proposedAccess='Free' if i<30 else 'VIP')
        source['contentKey']=key;p['questions'].append(q);s['questions'].append(source)
    keys=[q['contentKey'] for q in p['questions']]
    m.update(schemaVersion='mcq-batch-qa-v1',batchProfile='g5-pilot60-v1',responseMode='choice',setKey='qa.batch60',windowStart='2026-11-23T00:00:00+07:00',windowEnd='2026-11-30T00:00:00+07:00',orderedContentKeys=keys[:30],vipSupplementContentKeys=keys[30:],contentRevisions={k:2 for k in keys},freeSets=[{'slot':i+1,'setKey':f'qa.batch60.free.{i+1}','contentKeys':keys[10*i:10*i+10]} for i in range(3)])
    t=deepcopy(p);t['packageId']='qa.batch60.typed';t['questions']=t['questions'][:5]+t['questions'][30:35]
    for q in t['questions']:
        q.update(revision=3,responseType='short-answer',correctAnswer='2',answerKind='number',inputGuide={'instruction':'Nhập một số.','labels':['Đáp án'],'units':['đơn vị'],'separator':''})
        for field in ('choices','correctChoiceId','choiceRationales'):q.pop(field)
    tm={k:deepcopy(m[k]) for k in ('qaOnly','grade','batchProfile','timeZone','windowStart','windowEnd','windowEndExclusive','reviewStatus')}
    tm.update(schemaVersion='typed-subset-qa-v1',responseMode='typed',setKey='qa.batch60.typed',parentSetKey=m['setKey'],eligibleContentKeys=[q['contentKey'] for q in t['questions']],contentRevisions={q['contentKey']:3 for q in t['questions']})
    return p,m,s,t,tm

class BatchQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True);cls.folder=tempfile.TemporaryDirectory(dir='work');cls.base=Path(cls.folder.name)/'base.sqlite3'
        with patch.object(api,'now',return_value=NOW):initialize_empty_qa(cls.base,seed_learning=False)
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    def setUp(self):
        self.clock=patch.object(api,'now',return_value=NOW);self.clock.start();self.addCleanup(self.clock.stop)
        self.path=Path(self.folder.name)/(secrets.token_hex(8)+'.sqlite3')
        with closing(sqlite3.connect(self.base)) as a,closing(sqlite3.connect(self.path)) as b:a.backup(b)
        self.p,self.m,self.s,self.t,self.tm=batch_fixture()
    def load(self,typed=False):return import_batch(self.path,self.t if typed else self.p,self.tm if typed else self.m,self.s,allow_batch_qa=True,allow_draft_qa=True)
    def rows(self):
        with api.connect(self.path) as db:return tuple(db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('questions','question_versions','pilot_sets','pilot_content'))
    def test_opt_in_and_legacy10_remain_strict(self):
        with self.assertRaises(ImportFailure):validate_batch(self.p,self.m,self.s,allow_draft_qa=True)
        with self.assertRaises(ImportFailure):validate(self.p,self.m,self.s,allow_draft_qa=True)
        p,m,s=fixture();validate(p,m,s,allow_draft_qa=True)
        with self.assertRaises(ImportFailure):import_batch(self.path,self.p,self.m,self.s,allow_batch_qa=True)
    def test_preview_readonly_and_replay(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest();preview=preview_batch(self.path,self.p,self.m,self.s,allow_batch_qa=True,allow_draft_qa=True)
        self.assertTrue(preview['importable']);self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.load()['insertedVersions'],60);self.assertEqual(self.load(True)['insertedVersions'],10)
        self.assertEqual(self.load()['replayedVersions'],60);self.assertEqual(self.load(True)['replayedVersions'],10);self.assertEqual(self.rows(),(60,70,3,60))
        with api.connect(self.path) as db:self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_marker_and_missing_database(self):
        with self.assertRaises(ImportFailure):import_batch(self.path.with_suffix('.missing'),self.p,self.m,self.s,allow_batch_qa=True,allow_draft_qa=True)
        with api.connect(self.path,True) as db:db.execute('DELETE FROM pilot_environment')
        with self.assertRaises(ImportFailure):self.load()
    def test_validation_bad_whole_batch_no_writes(self):
        mutations=[lambda p,m:p['questions'][-1].update(quotaKey='other'),lambda p,m:p['questions'][-1].update(responseType='short-answer'),lambda p,m:m['contentRevisions'].update({'bad':2}),lambda p,m:m['freeSets'][1].update(slot=1),lambda p,m:m.update(vipSupplementContentKeys=m['orderedContentKeys']),lambda p,m:p['questions'].pop()]
        for mutate in mutations:
            p,m=deepcopy(self.p),deepcopy(self.m);mutate(p,m)
            with self.assertRaises(ImportFailure):import_batch(self.path,p,m,self.s,allow_batch_qa=True,allow_draft_qa=True)
            self.assertEqual(self.rows(),(0,0,0,0))
            self.assertFalse(preview_batch(self.path,p,m,self.s,allow_batch_qa=True,allow_draft_qa=True)['importable'])
    def test_parent_and_immutable_conflicts(self):
        with self.assertRaises(ImportFailure):self.load(True)
        self.load();self.load(True);before=self.rows();self.p['questions'][0]['prompt']+=' changed'
        with self.assertRaises(ImportFailure):self.load()
        self.assertEqual(self.rows(),before)
        self.tm['setKey']+='other'
        with self.assertRaises(ImportFailure):self.load(True)
    def test_slot_conflict_rolls_back_everything_and_preview_errors(self):
        with api.connect(self.path,True) as db:db.execute("INSERT INTO pilot_sets VALUES ('occupied',5,'2026-11-23','2026-11-30',2,1)")
        before=self.rows();r=preview_batch(self.path,self.p,self.m,self.s,allow_batch_qa=True,allow_draft_qa=True);self.assertFalse(r['importable'])
        with self.assertRaises(ImportFailure):self.load()
        self.assertEqual(self.rows(),before)
    def test_injected_partial_storage_error_rolls_back(self):
        with api.connect(self.path,True) as db:db.execute("CREATE TRIGGER fail_batch BEFORE INSERT ON question_versions WHEN NEW.prompt LIKE '%#5:%' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.Error):self.load()
        self.assertEqual(self.rows(),(0,0,0,0))
    def test_mode_pins_quota_and_quote_selector(self):
        self.load();self.load(True)
        with api.connect(self.path,True) as db:wallet.initialize(db,self.m['vipSupplementContentKeys'])
        server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),free_vip_pilot=PilotConfig(wallet=True,batch_set_key=self.m['setKey']))
        c=Client(server);state=c.call('auth/register',{'login':'batch-'+secrets.token_hex(8),'password':secrets.token_urlsafe(18),'name':'QA Batch','birthYear':api.academic()[0]-10})
        sid=state['state']['studentId'] if 'studentId' in state.get('state',{}) else None
        with api.connect(self.path,True) as db:
            aid=state['account']['id'];db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',('2027-01-01T00:00:00Z',aid));sid=db.execute('SELECT id FROM students WHERE account_id=?',(aid,)).fetchone()[0];db.execute('INSERT INTO wallet_terms VALUES (?,?,?)',(sid,api.stamp(NOW),wallet.POLICY))
        key=self.m['vipSupplementContentKeys'][0]
        def exam(mode,keys):return c.call('exams',{'requestKey':secrets.token_hex(12),'contentKeys':keys,'responseMode':mode})['exam']
        choice=exam('choice',[key]);typed=exam('typed',[key]);self.assertEqual(choice['responseMode'],'choice');self.assertEqual(typed['responseMode'],'typed')
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM wallet_debits WHERE student_id=?',(sid,)).fetchone()[0],1)
        with self.assertRaises(api.APIError):exam('typed',[key,self.m['vipSupplementContentKeys'][9]])
        self.assertNotEqual(wallet.selector({'contentKeys':[key],'responseMode':'typed'}),wallet.selector({'contentKeys':[key],'responseMode':'choice'}))
        for slot in (1,2,3):self.assertEqual(len(c.call('exams',{'requestKey':secrets.token_hex(12),'setIndex':slot})['exam']['questions']),10)
        with api.connect(self.path,True) as db:
            db.execute("INSERT INTO pilot_sets VALUES ('qa.other.week',5,'2026-11-30','2026-12-07',1,1)")
            db.execute("INSERT INTO pilot_set_items SELECT 'qa.other.week',position,content_key,version_id FROM pilot_set_items WHERE set_key='qa.batch60.free.1'")
        with patch.object(api,'now',return_value=datetime(2026,11,30,5,tzinfo=timezone.utc)):
            with self.assertRaises(api.APIError):c.call('exams',{'requestKey':secrets.token_hex(12),'setIndex':1})
