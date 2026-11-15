"""Import and grading contract tests: synthetic data only, no authored package mutation."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from backend import platform_api as api
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.mcq_import import ImportFailure,validate,import_package,load_json
from scripts.import_mcq_qa import initialize_empty_qa
from scripts.mcq_fixture import fixture
from test_free_vip_pilot import Client

NOW=datetime(2026,11,16,5,tzinfo=timezone.utc)


class MCQTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(dir='work')
        cls.base=Path(cls.directory.name)/'base.sqlite3'
        with patch.object(api,'now',return_value=NOW): initialize_empty_qa(cls.base)

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    def setUp(self):
        self.clock=patch.object(api,'now',return_value=NOW); self.clock.start(); self.addCleanup(self.clock.stop)
        self.path=Path(self.directory.name)/(secrets.token_hex(8)+'.sqlite3')
        a=sqlite3.connect(self.base); b=sqlite3.connect(self.path)
        try: a.backup(b)
        finally: a.close(); b.close()
        self.package,self.manifest,self.sources=fixture()
        self.server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),
            free_vip_pilot=PilotConfig(free_sets=1,set_size=5))

    def import_(self,**kwargs):
        return import_package(self.path,self.package,self.manifest,self.sources,**kwargs)

    def user(self,vip=False):
        c=Client(self.server)
        state=c.call('auth/register',{'login':'mcq-'+secrets.token_hex(8),'password':secrets.token_urlsafe(18),
            'name':'Hoc sinh thu','birthYear':api.academic()[0]-10})
        aid=state['account']['id']
        if vip: self.expire(aid,'2027-01-01T00:00:00Z')
        return c,aid

    def expire(self,aid,value):
        with api.connect(self.path,True) as db: db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(value,aid))

    def count(self,table):
        with api.connect(self.path) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone(): return 0
            return db.execute('SELECT count(*) FROM '+table).fetchone()[0]

    def exam(self,c,**kw): return c.call('exams',{'requestKey':secrets.token_hex(12),**kw})['exam']

    def deny(self,status,c,path,body=None):
        with self.assertRaises(api.APIError) as caught: c.call(path,body)
        self.assertEqual(caught.exception.status,status)

    def test_drafts_default_refused_opt_in_keeps_review_metadata(self):
        with self.assertRaisesRegex(ImportFailure,'reviewStatus'): self.import_()
        self.assertEqual(self.count('pilot_content'),0)
        r=self.import_(allow_draft_qa=True)
        self.assertEqual(r['insertedVersions'],10); self.assertFalse(r['independentTeacherApproved'])
        with api.connect(self.path) as db:
            values=[json.loads(x[0]) for x in db.execute('SELECT metadata_json FROM mcq_versions')]
        self.assertTrue(all(x['qaOnly'] and not x['reviewStatus']['independentTeacherApproved'] for x in values))
        self.assertTrue(all(x['difficultyMapping']['provisional'] and len(x['choices'])==4 for x in values))

    def test_marker_required_even_with_explicit_draft_opt_in(self):
        with api.connect(self.path,True) as db: db.execute('DROP TABLE pilot_environment')
        with self.assertRaisesRegex(ImportFailure,'marker'): self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('pilot_content'),0)
        missing=self.path.with_name('not-created.sqlite3')
        with self.assertRaises(ImportFailure): import_package(missing,self.package,self.manifest,self.sources,allow_draft_qa=True)
        self.assertFalse(missing.exists())

    def test_schema_choices_source_lineage_and_quota_tampering(self):
        cases=[('correctChoiceId','E'),('grade',4),('revision',True),('sourceRevision',99),('skillKey','unknown'),
               ('quotaKey','new-quota'),('contentKey','new-equivalent-key'),('responseType','constructed-response'),
               ('proposedAccess','Admin'),('lineageRelationship','unknown')]
        for field,value in cases:
            with self.subTest(field=field):
                p=deepcopy(self.package);p['questions'][0][field]=value
                with self.assertRaises(ImportFailure): validate(p,self.manifest,self.sources,allow_draft_qa=True)
        for choices in ([{'id':'A','text':'x'}]*4,
            [{'id':c,'text':' Same ' if i==0 else 'same' if i==1 else str(i)} for i,c in enumerate('ABCD')],
            [{'id':c,'text':str(i)} for i,c in enumerate(('A','B','C',4))]):
            p=deepcopy(self.package);p['questions'][0]['choices']=choices
            with self.assertRaises(ImportFailure): validate(p,self.manifest,self.sources,allow_draft_qa=True)

    def test_all_blocks_metadata_and_nested_fields_reject_media_html_urls(self):
        for field in ('prompt','hints','solutionSteps','answerExplanation','sourceLocator','choiceRationales'):
            for bad in ('<img src="x">','https://outside.invalid/x','data:image/png;base64,x',r'\href{evil}{x}'):
                p=deepcopy(self.package)
                if field=='choiceRationales': p['questions'][0][field]['A']=bad
                elif field=='sourceLocator': p['questions'][0][field]={'path':bad}
                else: p['questions'][0][field]=bad
                with self.subTest(field=field,bad=bad):
                    with self.assertRaises(ImportFailure): validate(p,self.manifest,self.sources,allow_draft_qa=True)
        p=deepcopy(self.package);p['questions'][0]['prompt']=[{'type':'image','asset_id':1}]
        with self.assertRaises(ImportFailure): validate(p,self.manifest,self.sources,allow_draft_qa=True)
        self.assertEqual(self.count('pilot_content'),0)

    def test_manifest_grade_week_access_and_pins(self):
        for field,value in (('grade',4),('timeZone','UTC'),('windowEndExclusive',False),
            ('windowStart','2026-11-17T00:00:00+07:00'),('orderedContentKeys',['qa.mcq.05']*5)):
            m=deepcopy(self.manifest);m[field]=value
            with self.assertRaises(ImportFailure): validate(self.package,m,self.sources,allow_draft_qa=True)
        self.manifest['contentRevisions']['qa.mcq.00']=99
        with self.assertRaisesRegex(ImportFailure,'pinned'): self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('mcq_versions'),0)
        self.assertEqual(self.count('pilot_content'),0)

    def test_import_retry_conflict_and_late_failure_are_atomic(self):
        self.assertEqual(self.import_(allow_draft_qa=True)['insertedVersions'],10)
        self.assertEqual(self.import_(allow_draft_qa=True)['replayedVersions'],10)
        self.package['questions'][-1]['answerExplanation']='Conflicting immutable explanation'
        with self.assertRaisesRegex(ImportFailure,'immutable'): self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('mcq_versions'),10)
        self.package=fixture()[0]
        self.package['questions'][0]['revision']=3
        self.manifest['setKey']='different-set-in-same-week'
        with self.assertRaisesRegex(ImportFailure,'occupied'): self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('mcq_versions'),10)
        self.assertEqual(self.count('pilot_sets'),1)

    def test_database_failure_after_partial_inserts_rolls_back_everything(self):
        with api.connect(self.path,True) as db:
            db.execute("CREATE TRIGGER mcq_failure BEFORE INSERT ON question_versions WHEN NEW.revision=2 AND (SELECT question_code FROM questions WHERE id=NEW.question_id)='qa.mcq.05' BEGIN SELECT RAISE(ABORT,'injected storage failure'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('pilot_content'),0);self.assertEqual(self.count('mcq_versions'),0)
        self.assertEqual(self.count('pilot_sets'),0);self.assertEqual(self.count('pilot_grants'),0)

    def test_free_shared_set_server_text_grading_no_pre_submit_solution_and_owner(self):
        self.import_(allow_draft_qa=True)
        c,_=self.user();other,_=self.user()
        first=self.exam(c,setIndex=1); second=self.exam(other,setIndex=1)
        self.assertEqual(first['questions'],second['questions'])
        self.assertEqual(len(first['questions']),5)
        self.assertNotIn('solution',json.dumps(first)); self.assertNotIn('QA correct',json.dumps(first))
        self.deny(403,c,'exams',{'requestKey':'free-vip-denied','contentKeys':['qa.mcq.05']})
        self.deny(400,c,'exams/'+first['id']+'/answers',{'position':1,'answer':'A'})
        self.deny(404,other,'exams/'+first['id']+'/submit',{})
        for i,q in enumerate(first['questions']):
            c.call('exams/'+first['id']+'/answers',{'position':i+1,'answer':q['options'][0 if i%2==0 else 1]})
        result=c.call('exams/'+first['id']+'/submit',{})['exam']
        self.assertEqual(result['score'],6);self.assertEqual(result['correct'],3)
        self.assertIn('solution',result['questions'][0])
        self.assertEqual(result,c.call('exams/'+first['id']+'/submit',{})['exam'])

    def test_revision_quota_retry_expiry_review_and_immutable_attempt(self):
        self.import_(allow_draft_qa=True);c,aid=self.user(vip=True)
        self.server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5,daily_new=1)
        old=self.exam(c,contentKeys=['qa.mcq.05'])
        self.assertEqual(c.call('pilot/sets')['newUsed'],1)
        self.package['questions'][5]['revision']=3
        self.package['questions'][5]['prompt']='  '+self.package['questions'][5]['prompt']+'  '
        self.import_(allow_draft_qa=True)
        new=self.exam(c,contentKeys=['qa.mcq.05'])
        self.assertNotEqual(old['questions'][0]['text'],new['questions'][0]['text'])
        self.assertEqual(c.call('pilot/sets')['newUsed'],1)
        self.assertEqual(c.call('exams/'+old['id'])['exam']['questions'],old['questions'])
        self.deny(429,c,'exams',{'requestKey':'second-content','contentKeys':['qa.mcq.06']})
        self.expire(aid,'2026-11-16T04:59:59Z')
        c.call('exams/'+old['id']+'/answers',{'position':1,'answer':'7'})
        self.assertEqual(c.call('exams/'+old['id']+'/submit',{})['exam']['score'],10)
        self.exam(c,replayExamId=int(old['id']))
        self.deny(403,c,'exams',{'requestKey':'after-expiry','contentKeys':['qa.mcq.06']})

    def test_replacement_has_new_identity_and_bad_equivalent_alias_rejected(self):
        q=self.package['questions'][5]; old=q['contentKey']
        q.update(contentKey='qa.replacement.05',quotaKey='qa.replacement.05',lineageRelationship='replacement',
                 changeReason='QA different objective, genuinely replacement')
        self.manifest['vipSupplementContentKeys'][0]=q['contentKey']
        self.import_(allow_draft_qa=True)
        c,_=self.user(vip=True);self.exam(c,contentKeys=[q['contentKey']])
        self.assertEqual(c.call('pilot/sets')['newUsed'],1)
        with api.connect(self.path,True) as db:
            db.execute('UPDATE mcq_versions SET quota_key=? WHERE content_key=?',(old,q['contentKey']))
        self.deny(503,c,'exams',{'requestKey':'forged-db-alias','contentKeys':[q['contentKey']]})

    def test_import_race_same_package_has_single_version_set(self):
        def run(_): return self.import_(allow_draft_qa=True)['insertedVersions']
        with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(run,range(3)))
        self.assertEqual(sorted(results),[0,0,10]);self.assertEqual(self.count('mcq_versions'),10)
        self.assertEqual(self.count('pilot_sets'),1)

    def test_flag_off_and_locked_secondary_paths(self):
        self.import_(allow_draft_qa=True);c,_=self.user(vip=True)
        exam=self.exam(c,setIndex=1)
        for route,body in [('bot/start',{'requestKey':'abcdefgh'}),('arena',{'action':'quick'}),('materials',None),('lessons/test/open',{})]:
            self.deny(403,c,route,body)
        self.server.free_vip_pilot=None
        self.assertEqual(c.call('exams/'+exam['id'])['exam']['questions'],exam['questions'])
        self.assertEqual(len(self.exam(c,count=3,topic='decimal')['questions']),3)
        self.assertEqual(self.count('pilot_grants'),5)

    def test_duplicate_json_fields_refused_without_evaluation(self):
        p=self.path.with_suffix('.json');p.write_text('{"schemaVersion":"a","schemaVersion":"b"}',encoding='utf-8')
        with self.assertRaisesRegex(ImportFailure,'duplicate JSON'): load_json(p)


    def test_equivalent_cannot_hide_a_different_problem_under_old_quota(self):
        self.package['questions'][0]['prompt']='QA entirely different problem'
        with self.assertRaisesRegex(ImportFailure,'preserve the trusted source problem'):
            self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('pilot_content'),0)

    def test_choice_shuffle_keeps_id_text_answer_mapping(self):
        for q in self.package['questions']:
            q['choices']=list(reversed(q['choices']))
            q['correctChoiceId']='C'
        self.import_(allow_draft_qa=True)
        c,_=self.user();exam=self.exam(c,setIndex=1)
        for i,view in enumerate(exam['questions']):
            self.assertEqual(view['options'][1],str(i+4))
            c.call('exams/'+exam['id']+'/answers',{'position':i+1,'answer':view['options'][1]})
        self.assertEqual(c.call('exams/'+exam['id']+'/submit',{})['exam']['score'],10)
