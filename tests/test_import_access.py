"""Round4 contracts against the supplied ten existing questions, never new content.
Set FIVEBMATH_QA_INPUT_DIR to questions-mcq.json/sample-sets.json/sources.json.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import closing
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend import platform_api as api
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.mcq_import import ImportFailure,import_package,load_json
from backend.mcq_preview import preview_package
from scripts.import_mcq_qa import initialize_empty_qa
from test_free_vip_pilot import Client

NOW=datetime(2026,11,16,5,tzinfo=timezone.utc)


class ImportAccessTests(unittest.TestCase):
    evidence=[]

    @classmethod
    def setUpClass(cls):
        folder=os.environ.get('FIVEBMATH_QA_INPUT_DIR')
        if not folder:raise unittest.SkipTest('Supply the existing ten-question package with FIVEBMATH_QA_INPUT_DIR')
        folder=Path(folder)
        cls.inputs=[load_json(folder/f) for f in ('questions-mcq.json','sample-sets.json','sources.json')]
        assert len(cls.inputs[0]['questions'])==10
        Path('work').mkdir(exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir='work');cls.folder=Path(cls.temp.name)
        cls.base=cls.folder/'empty.sqlite3'
        with patch.object(api,'now',return_value=NOW):initialize_empty_qa(cls.base)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.clock=patch.object(api,'now',return_value=NOW);self.clock.start();self.addCleanup(self.clock.stop)
        self.path=self.folder/(secrets.token_hex(8)+'.sqlite3')
        with closing(sqlite3.connect(self.base)) as source,closing(sqlite3.connect(self.path)) as target:source.backup(target)
        self.package,self.manifest,self.sources=deepcopy(self.inputs)
        self.keys=self.manifest['vipSupplementContentKeys']
        self.server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),
            student_cookie_name='5bmath_qa_contract_session',free_vip_pilot=PilotConfig(free_sets=1,set_size=5,daily_new=2))

    def record(self,**details):self.evidence.append({'test':self._testMethodName,**details})
    def import_(self):return import_package(self.path,self.package,self.manifest,self.sources,allow_draft_qa=True)
    def preview(self):return preview_package(self.path,self.package,self.manifest,self.sources,allow_draft_qa=True)
    def count(self,table):
        with api.connect(self.path) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name=?",(table,)).fetchone():return 0
            return db.execute('SELECT count(*) FROM '+table).fetchone()[0]
    def user(self,vip=False):
        c=Client(self.server)
        aid=c.call('auth/register',{'login':'r4-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),
            'name':'QA vòng 4','birthYear':api.academic()[0]-10})['account']['id']
        if vip:self.expire(aid,NOW+timedelta(days=30))
        return c,aid
    def expire(self,aid,value):
        with api.connect(self.path,True) as db:db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(value),aid))
    def exam(self,c,**body):return c.call('exams',{'requestKey':secrets.token_hex(12),**body})['exam']
    def deny(self,status,c,path,body=None):
        with self.assertRaises(api.APIError) as e:c.call(path,body)
        self.assertEqual(e.exception.status,status)

    def test_preview_new_replay_is_byte_identical_and_no_batch_write(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest();r=self.preview()
        self.assertTrue(r['importable']);self.assertEqual(r['summary']['new'],10)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        imported=self.import_();before=hashlib.sha256(self.path.read_bytes()).hexdigest();r=self.preview()
        self.assertEqual(r['summary']['exact_duplicate'],10);self.assertTrue(r['importable'])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        self.assertEqual(self.count('mcq_import_batches'),1)
        self.record(previewDBSHAUnchanged=True,firstNew=10,replay=10,batchId=imported['batchId'])

    def test_preview_reports_every_invalid_id_and_never_partial_imports(self):
        self.package['questions'][0].pop('choices');self.package['questions'][1]['correctChoiceId']='E'
        self.package['questions'][2]['responseType']='constructed-response'
        self.package['questions'][3]['origin']={}
        self.package['questions'][4]['prompt']='<img src="x">'
        self.package['questions'][5]['contentKey']=self.package['questions'][6]['contentKey']
        r=self.preview();self.assertFalse(r['importable']);self.assertEqual(r['summary']['invalid'],7)
        with self.assertRaises(ImportFailure):self.import_()
        self.assertEqual(self.count('pilot_content'),0);self.assertEqual(self.count('mcq_import_batches'),0)
        self.record(summary=r['summary'],rejected=[{'index':x['index'],'reasons':x['reasons']} for x in r['questions'] if x['reasons']])

    def test_conflict_revision_access_and_source_mapping_are_distinct(self):
        self.import_();self.package['questions'][0]['answerExplanation']='QA conflict test only'
        self.assertEqual(self.preview()['summary']['conflict'],1)
        with self.assertRaisesRegex(ImportFailure,'immutable'):self.import_()
        self.package=deepcopy(self.inputs[0]);q=self.package['questions'][5];q['revision']+=1
        self.assertEqual(self.preview()['summary']['new_revision'],1)
        self.assertTrue(self.preview()['importable']);self.import_()
        self.package=deepcopy(self.inputs[0]);q=self.package['questions'][5];q['revision']+=2;q['proposedAccess']='Free'
        self.assertEqual(self.preview()['summary']['conflict'],1)
        with self.assertRaises(ImportFailure):self.import_()
        self.package=deepcopy(self.inputs[0]);self.package['questions'][0]['sourceRevision']=999
        self.assertFalse(self.preview()['importable'])
        self.assertEqual(self.count('mcq_versions'),11)
        self.record(immutableConflict=True,newRevision=True,accessRelabelDenied=True,unknownMappingDenied=True)

    def test_near_similar_is_warning_never_merge_or_quota_alias(self):
        self.import_();q=self.package['questions'][5];old=q['contentKey']
        q.update(contentKey='qa.round4.mapping-example',quotaKey='qa.round4.mapping-example',lineageRelationship='replacement')
        self.manifest['vipSupplementContentKeys'][0]=q['contentKey']
        self.manifest['contentRevisions'].pop(old,None)
        r=self.preview();row=r['questions'][5]
        self.assertEqual(row['status'],'new');self.assertTrue(row['warnings'])
        # Preview only: the replacement is NOT imported as an extra question.
        self.assertEqual(self.count('mcq_versions'),10)
        self.record(warnings=row['warnings'],autoMerge=False,additionalQuestionImported=False)

    def test_injected_mid_import_failure_rolls_back_ddl_versions_and_batch(self):
        ck=self.package['questions'][5]['contentKey']
        with api.connect(self.path,True) as db:
            db.execute("CREATE TRIGGER fail_mid_import BEFORE INSERT ON question_versions WHEN NEW.revision=2 AND (SELECT question_code FROM questions WHERE id=NEW.question_id)="+"'"+ck+"' BEGIN SELECT RAISE(ABORT,'injected halfway'); END")
        before=self.count('questions')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'halfway'):self.import_()
        for name in ('mcq_versions','pilot_content','pilot_sets','pilot_grants','mcq_import_batches'):self.assertEqual(self.count(name),0)
        self.assertEqual(self.count('questions'),before)
        with api.connect(self.path,True) as db:db.execute('DROP TRIGGER fail_mid_import')
        self.import_();self.assertEqual(self.count('mcq_versions'),10)
        self.record(rollbackAll=True,rolledBackDDL=True,retryInserted=10)

    def test_import_race_has_one_batch_and_ten_versions_no_grants(self):
        with ThreadPoolExecutor(max_workers=3) as pool:r=list(pool.map(lambda _:self.import_(),range(3)))
        self.assertEqual(sorted(x['insertedVersions'] for x in r),[0,0,10])
        self.assertEqual(len({x['batchId'] for x in r}),1);self.assertEqual(self.count('mcq_import_batches'),1)
        self.assertEqual(self.count('mcq_versions'),10);self.assertEqual(self.count('pilot_grants'),0)
        self.record(insertedPerRequest=[x['insertedVersions'] for x in r],batches=1,versions=10,grants=0)

    def test_draft_not_published_not_selected_by_legacy_and_opt_in_required(self):
        with self.assertRaises(ImportFailure):import_package(self.path,self.package,self.manifest,self.sources)
        self.import_()
        with api.connect(self.path) as db:
            statuses={r[0] for r in db.execute('SELECT v.status FROM question_versions v JOIN mcq_versions m ON m.version_id=v.id')}
            self.assertEqual(statuses,{'draft'})
            from backend.question_bank import published_version_ids
            ids=set(published_version_ids(db,5,4,53))
            imported={r[0] for r in db.execute('SELECT version_id FROM mcq_versions')}
            self.assertFalse(ids & imported)
        c,_=self.user();exam=self.exam(c,setIndex=1);self.assertEqual(len(exam['questions']),5)
        with api.connect(self.path,True) as db:
            db.execute("UPDATE mcq_versions SET metadata_json=json_remove(metadata_json,'$.servingStatus')")
        self.deny(503,c,'exams',{'requestKey':'no-qa-trial-marker','setIndex':1})
        self.record(allDraft=True,legacyCannotSelect=True,explicitOptIn=True,trialMarkerRequired=True)

    def test_small_quota_race_and_identical_request_retry(self):
        self.import_();c,_=self.user(vip=True)
        def send(i):
            clone=Client(self.server);clone.headers.update(c.headers);clone.csrf=c.csrf
            try:return ('ok',self.exam(clone,contentKeys=[self.keys[i]])['id'])
            except api.APIError as e:return (e.status,None)
        with ThreadPoolExecutor(max_workers=5) as pool:r=list(pool.map(send,range(5)))
        self.assertEqual(sum(x[0]=='ok' for x in r),2);self.assertEqual(sum(x[0]==429 for x in r),3)
        self.assertEqual(self.count('pilot_grants'),2);self.assertEqual(self.count('pilot_requests'),2)
        self.assertEqual(self.count('exam_attempts'),2)
        used=c.call('pilot/sets')['newUsed'];self.assertEqual(used,2)
        self.record(raceSuccess=2,raceLimited=3,newUsed=used,attempts=2,grants=2)

    def test_same_request_race_failure_rollback_and_retry(self):
        self.import_();c,_=self.user(vip=True)
        with api.connect(self.path,True) as db:
            db.execute("CREATE TRIGGER fail_attempt BEFORE INSERT ON exam_attempts BEGIN SELECT RAISE(ABORT,'attempt failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.exam(c,contentKeys=[self.keys[0]])
        for t in ('pilot_grants','pilot_requests','exam_attempts','exams'):self.assertEqual(self.count(t),0)
        with api.connect(self.path,True) as db:db.execute('DROP TRIGGER fail_attempt')
        body={'requestKey':'same-idempotent-key','contentKeys':[self.keys[0]]}
        def run(_):
            clone=Client(self.server);clone.headers.update(c.headers);clone.csrf=c.csrf
            return clone.call('exams',body)['exam']['id']
        with ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(run,range(4)))
        self.assertEqual(len(set(ids)),1);self.assertEqual(self.count('pilot_grants'),1)
        self.assertEqual(self.count('pilot_requests'),1);self.assertEqual(self.count('exam_attempts'),1)
        self.record(failedAttemptRollback=True,retryAndRaceOneAttempt=True,grants=1)

    def test_revision_replay_and_reset_at_saigon_midnight(self):
        self.import_();c,_=self.user(vip=True);self.server.free_vip_pilot=PilotConfig(free_sets=1,set_size=5,daily_new=1)
        with patch.object(api,'now',return_value=datetime(2026,11,16,16,59,59,tzinfo=timezone.utc)):
            old=self.exam(c,contentKeys=[self.keys[0]])
            self.deny(429,c,'exams',{'requestKey':'before-midnight-limit','contentKeys':[self.keys[1]]})
            self.package['questions'][5]['revision']+=1;self.import_()
            self.exam(c,contentKeys=[self.keys[0]]);self.exam(c,replayExamId=int(old['id']))
            self.assertEqual(c.call('pilot/sets')['newUsed'],1)
        with patch.object(api,'now',return_value=datetime(2026,11,16,17,tzinfo=timezone.utc)):
            self.exam(c,contentKeys=[self.keys[0]]);self.assertEqual(c.call('pilot/sets')['newUsed'],0)
            self.exam(c,contentKeys=[self.keys[1]]);self.assertEqual(c.call('pilot/sets')['newUsed'],1)
            self.assertEqual(c.call('pilot/sets')['day'],'2026-11-17')
        self.record(revisionChargedAgain=False,replayChargedAgain=False,dayReset='2026-11-17',timezone='Asia/Saigon')

    def test_same_free_week_pins_many_accounts_and_next_week_reuses_ten(self):
        self.import_();a,_=self.user();b,_=self.user();old=self.exam(a,setIndex=1)
        self.assertEqual(old['questions'],self.exam(b,setIndex=1)['questions'])
        self.deny(403,b,'exams',{'requestKey':'free-no-vip','contentKeys':self.keys})
        self.manifest.update(setKey='qa.round4.next-week',windowStart='2026-11-23T00:00:00+07:00',windowEnd='2026-11-30T00:00:00+07:00')
        self.import_()
        with api.connect(self.path,True) as db:db.execute('UPDATE auth_sessions SET expires_at=?',(api.stamp(NOW+timedelta(days=8)),))
        with patch.object(api,'now',return_value=NOW+timedelta(days=7)):
            self.assertEqual(self.exam(a,setIndex=1)['questions'],old['questions'])
        self.assertEqual(self.count('mcq_versions'),10);self.assertEqual(self.count('pilot_sets'),2)
        self.record(sharedFree=True,nextWeekManifestOnly=True,mcqVersions=10,newContent=False)

    def test_expiry_exact_boundary_in_progress_submit_review_owner_and_tamper(self):
        self.import_();c,aid=self.user(vip=True);other,_=self.user()
        exam=self.exam(c,contentKeys=[self.keys[0]])
        self.expire(aid,NOW)
        self.assertEqual(c.call('session')['account']['membership'],'Free')
        self.deny(403,c,'exams',{'requestKey':'expired-vip-new','contentKeys':[self.keys[1]]})
        for field,value in [('role','VIP'),('membership','VIP'),('vipExpiresAt','2099'),('quota',999),('price',0),('plan','VIP')]:
            self.deny(400,c,'exams',{'requestKey':'forged-'+field,'setIndex':1,field:value})
        self.deny(404,other,'exams/'+exam['id'])
        self.deny(404,other,'exams/'+exam['id']+'/answers',{'position':1,'answer':exam['questions'][0]['options'][0]})
        self.deny(404,other,'exams/'+exam['id']+'/submit',{})
        q=self.package['questions'][5];correct=next(ch['text'] for ch in q['choices'] if ch['id']==q['correctChoiceId'])
        self.assertNotIn('correctChoiceId',json.dumps(exam))
        c.call('exams/'+exam['id']+'/answers',{'position':1,'answer':correct})
        self.assertEqual(c.call('exams/'+exam['id']+'/submit',{})['exam']['score'],10)
        self.exam(c,replayExamId=int(exam['id']))
        self.record(expiryExactIsFree=True,finishGranted=True,review=True,replay=True,ownerBlocked=True,clientPolicyIgnored=True)

    def test_legacy_mapping_not_inferred_and_old_cohort_simulated_without_backfill(self):
        self.import_();c,aid=self.user(vip=True)
        old=self.exam(c,contentKeys=[self.keys[0]])
        with api.connect(self.path,True) as db:db.execute("INSERT INTO pilot_cohorts VALUES (?,'legacy')",(aid,))
        self.assertGreater(len(c.call('state')['lessons']),0)
        self.assertEqual(c.call('exams/'+old['id'])['exam']['questions'],old['questions'])
        self.exam(c,count=3,topic='decimal')
        self.assertEqual(self.count('pilot_grants'),1)
        # Simulate unknown legacy identity in fake DB: preview/import must fail closed.
        with api.connect(self.path,True) as db:
            db.execute('DELETE FROM mcq_versions WHERE content_key=?',(self.keys[4],))
        self.assertEqual(self.preview()['summary']['conflict'],1)
        with self.assertRaisesRegex(ImportFailure,'unmapped'):self.import_()
        self.record(legacyCohortPreserved=True,backfillNotInferred=True,existingAttemptPreserved=True)

    def test_preview_and_commit_reject_unmarked_or_missing_database(self):
        missing=self.path.with_name('not-created.sqlite3')
        with self.assertRaises(ImportFailure):preview_package(missing,self.package,self.manifest,self.sources,allow_draft_qa=True)
        self.assertFalse(missing.exists())
        with api.connect(self.path,True) as db:db.execute('DROP TABLE pilot_environment')
        for fn in (preview_package,import_package):
            with self.assertRaisesRegex(ImportFailure,'marker'):fn(self.path,self.package,self.manifest,self.sources,allow_draft_qa=True)
        self.record(missingNotCreated=True,unmarkedDenied=True)

    def test_rights_metadata_and_unsupported_object_report_per_question(self):
        self.package['questions'][0]['origin'].pop('rightsNote')
        self.package['questions'][1]['responseType']={'type':'object'}
        self.package['questions'][2]['skillKey']=[]
        r=self.preview();self.assertEqual(r['summary']['invalid'],3)
        with self.assertRaises(ImportFailure):self.import_()
        self.record(metadataMissingDenied=True,objectTypeDenied=True,invalidSkillDenied=True)

    def test_cli_preview_default_draft_refusal_and_output_guards(self):
        import subprocess,sys
        paths=[]
        for label,value in zip(('questions','manifest','sources'),(self.package,self.manifest,self.sources)):
            f=self.path.with_name(self.path.stem+'-'+label+'.json');f.write_text(json.dumps(value),encoding='utf-8');paths.append(f)
        prefix=[sys.executable,'-m','scripts.import_mcq_qa','--database',str(self.path)]
        for label,f in zip(('questions','manifest','sources'),paths):prefix+=['--'+label,str(f)]
        report=self.path.with_suffix('.report.json')
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        run=subprocess.run(prefix+['--report',str(report),'--preview','--allow-draft-qa'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr);self.assertTrue(json.loads(report.read_text())['importable'])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        draftreport=self.path.with_suffix('.draft.json')
        run=subprocess.run(prefix+['--report',str(draftreport),'--preview'],capture_output=True,text=True)
        self.assertEqual(run.returncode,2);self.assertFalse(json.loads(draftreport.read_text())['importable'])
        for tail in (['--report',str(self.path),'--preview'],['--report',str(report),'--allow-draft-qa'],
                     ['--report',str(self.path.with_suffix('.new.json')),'--new-database','--preview']):
            run=subprocess.run(prefix+tail,capture_output=True,text=True);self.assertEqual(run.returncode,2)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        self.assertEqual(self.count('pilot_content'),0)
        self.record(cliPreviewNoWrite=True,defaultDraftRefused=True,outputOverwriteRefused=True,previewCreateRefused=True)
