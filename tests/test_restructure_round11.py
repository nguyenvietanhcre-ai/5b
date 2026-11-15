"""Round11 integration checks on new synthetic stores only."""
from datetime import timedelta
from pathlib import Path
import json,secrets,sqlite3,unittest,concurrent.futures
from backend import platform_api as api,wallet_qa as wallet
from backend.local_pilot import LocalPilot
from backend.content_retirement import activate,manifest,retired
from backend.question_bank import published_version_ids,arena_questions
from backend.arena import ArenaError
from backend.wallet_qa import QuoteChanged
import test_local_pilot as base

class RestructureTests(unittest.TestCase):
    setUpClass=classmethod(base.LocalPilotTests.setUpClass.__func__)
    tearDownClass=classmethod(base.LocalPilotTests.tearDownClass.__func__)
    actor=base.LocalPilotTests.actor
    call=base.LocalPilotTests.call
    logical=base.LocalPilotTests.logical
    def setUp(self):
        base.LocalPilotTests.setUp(self)
        import shutil
        mapping_inputs=self.main.parent/'mapping-only';mapping_inputs.mkdir(exist_ok=True);shutil.copyfile(Path('restructure-inputs/mapping60.json'),mapping_inputs/'mapping60.json')
        self.provider=LocalPilot(self.main,self.pilot,self.inputs,mapping_inputs);self.server.local_pilot=self.provider
    def quote(self,c,**kw):
        b={'intentId':secrets.token_hex(12),'category':'combined','count':3,'pool':'all',**kw}
        return self.call(c,'practice/quote',b),b
    def commit(self,c,q,**kw):
        b={'requestKey':secrets.token_hex(12),'intentId':q['intentId'],'quoteId':q['quoteId'],'confirmWallet':bool(q['private']),**kw}
        return self.call(c,'practice/exams',b)['exam'],b
    def pack(self,c):
        o=self.call(c,'orders',{'requestKey':secrets.token_hex(12),'sku':'qa.questions.100'});self.call(c,'mock-confirm',{'orderId':o['orderId']});return o
    def counts(self):
        with api.connect(self.pilot) as db:return {t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('exams','exam_attempts','pilot_grants','wallet_debits','practice_requests')}
    def test_mixed_pin_clear_zero_grade_owner_and_lostresponse(self):
        c=self.actor('VIP');other=self.actor();before=self.logical();q,_=self.quote(c,category='content',topicKey='proposal.g5.C02',count=3)
        self.assertEqual({x['responseMode'] for x in q['selection']},{'typed','choice'})
        exam,body=self.commit(c,q);self.assertEqual([x['responseMode'] for x in exam['questions']],[x['responseMode'] for x in q['selection']]);self.assertEqual(len({x['contentKey'] for x in q['selection']}),3)
        self.assertTrue(all('answer' not in x and 'solution' not in x for x in exam['questions']))
        for pos,x in enumerate(exam['questions'],1):
            answer=x['options'][0] if x['responseMode']=='choice' else '0';self.call(c,'exams/'+exam['id']+'/answers',{'position':pos,'answer':answer});self.assertEqual(self.call(c,'exams/'+exam['id'])['exam']['answers'][str(pos)],answer)
            self.call(c,'exams/'+exam['id']+'/answers',{'position':pos,'answer':''});self.assertEqual(self.call(c,'exams/'+exam['id'])['exam']['answers'][str(pos)],'')
        with api.connect(self.pilot) as db:answers=[(r[0],json.loads(r[1])['answer']) for r in db.execute('SELECT i.position,v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=?',(exam['id'],))]
        for pos,answer in answers:self.call(c,'exams/'+exam['id']+'/answers',{'position':pos,'answer':answer})
        self.assertEqual(self.call(c,'exams/'+exam['id']+'/submit',{})['exam']['score'],10);self.assertEqual(self.call(c,'exams/'+exam['id']+'/submit',{})['exam']['score'],10)
        counts=self.counts();self.assertEqual(self.call(c,'practice/exams',body)['exam']['id'],exam['id']);self.assertEqual(self.counts(),counts)
        with self.assertRaises(api.APIError):self.call(other,'exams/'+exam['id'])
        before_debits=self.counts()['wallet_debits']
        replay_quote=self.call(c,'quote',{'replayExamId':int(exam['id'])})
        replay=self.call(c,'exams',{'replayExamId':int(exam['id']),'requestKey':secrets.token_hex(12),'quoteId':replay_quote['quoteId'],'confirmWallet':False})['exam']
        self.assertEqual([x['responseMode'] for x in replay['questions']],[x['responseMode'] for x in exam['questions']]);self.assertEqual(self.counts()['wallet_debits'],before_debits)
        self.assertEqual(self.call(c,'history')['items'][0]['responseMode'],'mixed')
        self.assertEqual(self.logical(),before)
    def test_free_affordable_pool_current_manifest_and_paid_notready(self):
        c=self.actor();cat=self.call(c,'catalogue');self.assertEqual(sum(x['availableCount'] for x in cat['topics']),30);self.assertEqual(next(x for x in cat['topics'] if x['key']=='proposal.g5.C11')['availableCount'],0)
        q,_=self.quote(c,count=10);self.assertEqual((q['free'],q['vip'],q['private']),(10,0,0));self.commit(c,q);before=self.counts()
        with self.assertRaises(api.APIError):self.quote(c,topicKey='proposal.g5.C11',count=1)
        self.assertEqual(self.counts(),before)
        with api.connect(self.pilot,True) as db:db.execute("UPDATE pilot_sets SET window_end='2000-01-01'")
        self.assertEqual(sum(x['availableCount'] for x in self.call(c,'catalogue')['topics']),10)
    def test_vip_caps_pack_p2_same_intent_expiry_and_replay(self):
        c=self.actor('VIP');self.call(c,'catalogue');self.pack(c)
        with api.connect(self.pilot,True) as db:
            principal=db.execute('SELECT * FROM local_principals').fetchone();session={'student_id':principal['pilot_student_id'],'account_id':principal['pilot_account_id']};vip=wallet.balance(db,session,self.provider.ensure_week()[0])['vip'];db.execute('INSERT INTO wallet_usage_seeds VALUES(?,?,?,?,?,?)',(session['student_id'],vip['day'],vip['cycleStart'],28,100,'synthetic round11 boundary'))
        q,b=self.quote(c,pool='paid',count=5);self.assertEqual((q['vip'],q['private']),(2,3))
        with api.connect(self.pilot,True) as db:db.execute("UPDATE wallet_quotes SET expires_at='2000-01-01'")
        with self.assertRaises(QuoteChanged):self.commit(c,q)
        again=self.call(c,'practice/quote',b);self.assertEqual(again['selection'],q['selection']);exam,body=self.commit(c,again)
        self.assertEqual(self.call(c,'wallet')['privateRemaining'],97);self.assertEqual(self.call(c,'wallet')['vip']['dayUsed'],30);self.call(c,'practice/exams',body);self.assertEqual(self.call(c,'wallet')['privateRemaining'],97)
        with self.assertRaises(api.APIError):self.call(c,'practice/quote',{**b,'count':3})
    def test_private_increase_needs_new_explicit_confirmation(self):
        c=self.actor('VIP');self.pack(c);q,b=self.quote(c,pool='paid',count=3);self.assertEqual(q['private'],0)
        with api.connect(self.main,True) as db:db.execute("UPDATE accounts SET vip_expires_at='2000-01-01'")
        before=self.counts()
        with self.assertRaises(QuoteChanged):self.commit(c,q,confirmWallet=True)
        self.assertEqual(self.counts(),before);again=self.call(c,'practice/quote',b);self.assertEqual(again['selection'],q['selection']);self.assertEqual(again['private'],3)
        with self.assertRaises(QuoteChanged):self.commit(c,again,confirmWallet=False)
        self.commit(c,again);self.assertEqual(self.call(c,'wallet')['privateRemaining'],97)
    def test_rollback_and_concurrent_retry_one_attempt(self):
        c=self.actor('VIP');q,_=self.quote(c);before=self.counts();body={'intentId':q['intentId'],'requestKey':secrets.token_hex(12),'quoteId':q['quoteId'],'confirmWallet':False}
        with api.connect(self.pilot,True) as db:db.execute("CREATE TRIGGER fail_r11 BEFORE INSERT ON exam_attempts BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
        with self.assertRaises(sqlite3.Error):self.call(c,'practice/exams',body)
        self.assertEqual(self.counts(),before)
        with api.connect(self.pilot,True) as db:db.execute('DROP TRIGGER fail_r11')
        with concurrent.futures.ThreadPoolExecutor(2) as ex:result=list(ex.map(lambda _:self.call(c,'practice/exams',body)['exam']['id'],range(2)))
        self.assertEqual(result[0],result[1]);self.assertEqual(self.counts()['exams'],before['exams']+1)
    def test_free_expired_pack_no_old_exam_quota(self):
        for role in ('Free','expired'):
            c=self.actor(role);self.pack(c)
            for _ in range(3):q,_=self.quote(c,pool='paid',count=1);self.commit(c,q)
            self.assertEqual(self.call(c,'wallet')['vip']['dayUsed'],0);self.assertGreaterEqual(self.call(c,'wallet')['privateRemaining'],97)
    def test_invalid_criteria_no_debit_and_history_readonly(self):
        c=self.actor('VIP');before=self.counts()
        for kw in ({'category':'school','school':'test'},{'week':1},{'difficulty':4},{'topicKey':'missing'},{'responseMode':'typed'},{'pool':'bad'}):
            with self.assertRaises(api.APIError):self.quote(c,**kw)
        self.assertEqual(self.counts(),before);q,_=self.quote(c,count=1);exam,_=self.commit(c,q);main=self.logical();self.assertEqual(self.call(c,'history')['pending'][0]['reference'],'pilot:'+exam['id']);self.assertEqual(self.logical(),main)
        self.call(c,'exams/'+exam['id']+'/submit',{});self.assertEqual(len(self.call(c,'history')['completed']),1);other=self.actor();self.assertEqual(self.call(other,'history')['items'],[])
    def test_retire_scope_a_discovery_and_allocations_no_delete_rollback(self):
        api.seed_catalog(self.main)
        with api.connect(self.main) as db:
            expected=manifest(db);before={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('topics','lessons','questions','question_versions')};g4=published_version_ids(db,4,1);g5=published_version_ids(db,5,1)
        with api.connect(self.main,True) as db:activate(db,expected)
        with api.connect(self.main) as db:
            self.assertTrue(retired(db,5));self.assertFalse(retired(db,4));self.assertEqual(published_version_ids(db,5,1),[]);self.assertEqual(published_version_ids(db,4,1),g4);self.assertEqual(before,{t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in before})
            with self.assertRaises(ArenaError):arena_questions(db,5,0)
        c=self.actor('VIP');self.assertEqual(c.call('state')['lessons'],[])
        with self.assertRaisesRegex(api.APIError,'ngừng cấp đề mới'):c.call('exams',{'requestKey':secrets.token_hex(12),'count':10,'difficulty':0,'category':'combined'})
        with self.assertRaises(api.APIError):api.seed_catalog(self.main)
        with api.connect(self.main,True) as db:activate(db,enabled=False)
        with api.connect(self.main) as db:self.assertEqual(published_version_ids(db,5,1),g5);self.assertFalse(retired(db,5))

    def test_new_selected_titles_two_types_and_receipt_replay(self):
        c=self.actor('VIP');titles=[]
        for category,extra in [('combined',{}),('content',{'topicKey':'proposal.g5.C02'})]:
            q,_=self.quote(c,category=category,count=1,**extra);exam,body=self.commit(c,q)
            title=exam['title'];titles.append(title)
            self.assertTrue(title.startswith('Đề luyện tập tổng hợp' if category=='combined' else 'Đề luyện tập theo nội dung'));self.assertIn('Lớp 5',title)
            with api.connect(self.pilot) as db:
                allocation=json.loads(db.execute('SELECT allocation_json FROM wallet_attempt_receipts WHERE exam_id=?',(exam['id'],)).fetchone()[0])
                self.assertEqual(allocation['practiceTitle'],title);self.assertEqual(allocation['practiceSelection']['category'],category);self.assertEqual(allocation['criteria']['category'],category)
            before=self.counts();replay=self.call(c,'practice/exams',body)['exam'];self.assertEqual(replay['id'],exam['id']);self.assertEqual(replay['title'],title);self.assertEqual(self.counts(),before)
        self.assertNotEqual(*titles)
    def test_title_cannot_be_forged_or_rebound_to_changed_quotecriteria(self):
        c=self.actor('VIP');q,_=self.quote(c,count=1);body={'requestKey':secrets.token_hex(12),'intentId':q['intentId'],'quoteId':q['quoteId'],'confirmWallet':False};before=self.counts()
        with self.assertRaises(api.APIError):self.call(c,'practice/exams',{**body,'title':'UNTRUSTED CLIENT TITLE'})
        self.assertEqual(self.counts(),before)
        with api.connect(self.pilot,True) as db:
            plan=json.loads(db.execute('SELECT plan_json FROM wallet_quotes WHERE quote_id=?',(q['quoteId'],)).fetchone()[0]);plan['criteria']['category']='content';db.execute('UPDATE wallet_quotes SET plan_json=? WHERE quote_id=?',(api.packed(plan),q['quoteId']))
        with self.assertRaises(api.APIError) as caught:self.call(c,'practice/exams',body)
        self.assertEqual(caught.exception.status,409);self.assertEqual(self.counts(),before)
    def test_historical_generic_title_replay_is_not_backfilled(self):
        c=self.actor('VIP');q,_=self.quote(c,count=1);exam,body=self.commit(c,q)
        with api.connect(self.pilot,True) as db:db.execute('UPDATE exams SET title=? WHERE id=?',('Luyện tập lớp 5',exam['id']))
        before=self.counts();self.assertEqual(self.call(c,'practice/exams',body)['exam']['title'],'Luyện tập lớp 5');self.assertEqual(self.counts(),before)





class KnowledgeTests(unittest.TestCase):
    setUpClass=classmethod(base.LocalPilotTests.setUpClass.__func__)
    tearDownClass=classmethod(base.LocalPilotTests.tearDownClass.__func__)
    setUp=RestructureTests.setUp
    actor=RestructureTests.actor
    call=RestructureTests.call
    logical=RestructureTests.logical
    counts=RestructureTests.counts
    def bundle(self,revision=1):
        from base64 import b64encode
        import hashlib
        assets=[]
        for name in ('lesson','solution'):
            data=('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100"><text x="10" y="30">Synthetic '+name+' revision '+str(revision)+'</text></svg>').encode();assets.append({'sha256':hashlib.sha256(data).hexdigest(),'mime':'image/svg+xml','base64':b64encode(data).decode()})
        def sections(solution=False):return [{'title':'Synthetic section '+str(i),'blocks':[{'type':'text','text':'QA structural fixture only; not a published math lesson.'}]+([{'type':'media','sha256':assets[int(solution)]['sha256'],'alt':'Synthetic QA figure'}] if i==1 else [])} for i in range(3)]
        lessons=[]
        for i in range(24):
            lessons.append({'lessonKey':'knowledge.qa.lesson.'+str(i),'topicKey':'proposal.g5.C'+str(i//2+1).zfill(2),'revision':revision,'title':'Synthetic QA lesson '+str(i),'sections':sections(),'fixed':{'questionKey':'knowledge.qa.fixed.'+str(i),'revision':revision,'responseMode':'typed','answerKind':'number','correctAnswer':str(revision-1),'prompt':'Synthetic QA scalar check: enter zero for revision1.','solution':sections(True)}})
        return {'schemaVersion':'knowledge-fixed-v1','qaOnly':True,'grade':5,'lessons':lessons,'assets':assets}
    def test_fixed_check_wrong_correct_retry_free_no_leak_no_wallet_history_xp(self):
        bundle=self.bundle();self.provider.knowledge.install(bundle);c=self.actor();other=self.actor();self.call(c,'catalogue');before=self.counts();main=self.logical();key=bundle['lessons'][0]['lessonKey'];lesson=self.call(c,'knowledge/'+key)
        self.assertNotIn('correctAnswer',json.dumps(lesson));self.assertNotIn('solution',json.dumps(lesson));self.assertNotIn('expectedAnswer',json.dumps(lesson));self.assertEqual(len(self.call(c,'catalogue')['knowledge']),24)
        bad=self.call(c,'knowledge/'+key+'/check',{'requestKey':secrets.token_hex(12),'answer':'99','lessonRevision':1});self.assertFalse(bad['correct']);self.assertTrue(bad['completed'])
        body={'requestKey':secrets.token_hex(12),'answer':'0','lessonRevision':1};good=self.call(c,'knowledge/'+key+'/check',body);self.assertTrue(good['correct']);self.assertEqual(good['attemptCount'],2);self.assertEqual(self.call(c,'knowledge/'+key+'/check',body)['attemptCount'],2)
        self.assertFalse(self.call(other,'knowledge/'+key)['progress']['completed']);self.assertEqual(self.counts(),before);self.assertEqual(self.logical(),main);self.assertEqual(self.call(c,'history')['items'],[])
        for answer in (None,5,'x'*501):
            with self.assertRaises(api.APIError):self.call(c,'knowledge/'+key+'/check',{'requestKey':secrets.token_hex(12),'answer':answer,'lessonRevision':1})
    def test_stale_revision_check_progress_and_solution_assets_pinned(self):
        b1=self.bundle(1);self.provider.knowledge.install(b1);c=self.actor();key=b1['lessons'][0]['lessonKey'];self.call(c,'knowledge/'+key)
        b2=self.bundle(2);self.provider.knowledge.install(b2)
        body={'requestKey':secrets.token_hex(12),'answer':'0','lessonRevision':1};result=self.call(c,'knowledge/'+key+'/check',body);self.assertTrue(result['correct']);self.assertEqual(result['lessonRevision'],1)
        self.assertFalse(self.call(c,'knowledge/'+key)['progress']['completed']);self.assertTrue(self.call(c,'knowledge/'+key+'?revision=1')['progress']['completed']);self.assertEqual(self.call(c,'knowledge/'+key+'/check',body)['progress']['correctCount'],1)
        oldsha=b1['assets'][1]['sha256'];newsha=b2['assets'][1]['sha256']
        self.assertTrue(self.call(c,'knowledge/'+key+'/asset?revision=1&sha='+oldsha)['_local_binary'])
        with self.assertRaises(api.APIError):self.call(c,'knowledge/'+key+'/asset?revision=2&sha='+newsha)
        with self.assertRaises(api.APIError):self.call(c,'knowledge/'+key+'/asset?sha='+oldsha)
    def test_import_conflict_bad_binding_and_partial_batch_atomic(self):
        from copy import deepcopy
        good=self.bundle();self.provider.knowledge.install(good)
        with api.connect(self.pilot) as db:before=[tuple(r) for r in db.execute('SELECT * FROM knowledge_lessons')]
        for variant in ('immutable','practicekey','partial','badasset','typedcomplex'):
            b=deepcopy(good)
            if variant=='immutable':b['lessons'][-1]['title']='conflict title'
            elif variant=='practicekey':b['lessons'][0]['fixed']['questionKey']=next(iter(self.provider.practice.mapping))
            elif variant=='partial':b['lessons'].pop()
            elif variant=='badasset':b['assets'][0]['sha256']='0'*64
            elif variant=='typedcomplex':b['lessons'][0]['fixed']['answerKind']='ordered'
            with self.assertRaises(ValueError):self.provider.knowledge.install(b)
            with api.connect(self.pilot) as db:self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM knowledge_lessons')],before)

if __name__=='__main__':unittest.main()
