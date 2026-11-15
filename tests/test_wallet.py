"""Wallet policy QA against exactly the supplied ten MCQs; no source mutation."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json,os,secrets,sqlite3,tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from backend import platform_api as api
from backend import wallet_qa as wallet
from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.mcq_import import load_json,import_package
from scripts.import_mcq_qa import initialize_empty_qa
from test_free_vip_pilot import Client

NOW=datetime(2026,11,16,5,tzinfo=timezone.utc)


class WalletTests(unittest.TestCase):
    evidence=[]
    @classmethod
    def setUpClass(cls):
        folder=os.environ.get(getattr(cls,'input_env','FIVEBMATH_QA_INPUT_DIR'))
        if not folder:raise unittest.SkipTest('Supply the unchanged ten MCQ inputs via FIVEBMATH_QA_INPUT_DIR')
        cls.values=[load_json(Path(folder)/f) for f in getattr(cls,'input_files',('questions-mcq.json','sample-sets.json','sources.json'))]
        assert len(cls.values[0]['questions'])==10
        Path('work').mkdir(exist_ok=True);cls.temp=tempfile.TemporaryDirectory(dir='work');cls.folder=Path(cls.temp.name);cls.base=cls.folder/'base.sqlite3'
        with patch.object(api,'now',return_value=NOW):
            initialize_empty_qa(cls.base);import_package(cls.base,*cls.values,allow_draft_qa=True)
            with api.connect(cls.base,True) as db:wallet.initialize(db,cls.values[1]['vipSupplementContentKeys'])
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.clock=patch.object(api,'now',return_value=NOW);self.clock.start();self.addCleanup(self.clock.stop)
        self.path=self.folder/(secrets.token_hex(8)+'.sqlite3')
        with closing(sqlite3.connect(self.base)) as source,closing(sqlite3.connect(self.path)) as target:source.backup(target)
        self.server=SimpleNamespace(database_path=self.path,free_vip_pilot=PilotConfig(free_sets=1,set_size=5,wallet=True),review_upgrades=False,arena=Arena(),student_cookie_name='5bmath_qa_contract_wallet')
        self.keys=self.values[1]['vipSupplementContentKeys']
    def record(self,**details):self.evidence.append({'test':self._testMethodName,**details})
    def user(self,vip=False,expired=False,anchor=NOW):
        c=Client(self.server);aid=c.call('auth/register',{'login':'wallet-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),'name':'QA ví','birthYear':api.academic()[0]-10})['account']['id']
        if vip or expired:
            with api.connect(self.path,True) as db:
                sid=db.execute('SELECT id FROM students WHERE account_id=?',(aid,)).fetchone()[0]
                db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(NOW+timedelta(days=120) if vip else NOW),aid))
                db.execute('INSERT INTO wallet_terms VALUES (?,?,?)',(sid,api.stamp(anchor),wallet.POLICY))
        return c
    def session(self,c,db):return api.read_session(c,db)
    def invoke(self,c,fn,*args,**kw):
        with api.connect(self.path,True) as db:return fn(db,self.session(c,db),*args,**kw)
    def state(self,c):return c.call('pilot/sets')
    def buy(self,c):
        order=self.invoke(c,wallet.create_order,{'requestKey':secrets.token_hex(12),'sku':wallet.CATALOG['sku']})
        return self.invoke(c,wallet.mock_event,{'orderId':order['orderId']},confirm=True)['receipt']
    def spent(self,pack,value):
        with api.connect(self.path,True) as db:db.execute('INSERT OR REPLACE INTO wallet_pack_seeds VALUES (?,?,?)',(pack['pack_id'],value,'QA synthetic spent counter; not extra learning content'))
    def seed(self,c,day,cycle):
        budget=self.state(c)['vip']
        with api.connect(self.path,True) as db:db.execute('INSERT OR REPLACE INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(self.session(c,db)['student_id'],budget['day'],budget['cycleStart'],day,cycle,'QA boundary counter, not 300 authored questions'))
    def quote(self,c,body):return self.invoke(c,wallet.quote,body,self.server.free_vip_pilot)
    def exam(self,c,keys=None,**selector):
        if keys is not None:selector={'contentKeys':keys}
        q=self.quote(c,selector)
        body={'requestKey':secrets.token_hex(12),**selector,'quoteId':q['quoteId'],'confirmWallet':q['private']>0}
        return c.call('exams',body)['exam']
    def count(self,table):
        with api.connect(self.path) as db:return db.execute('SELECT count(*) FROM '+table).fetchone()[0]
    def deny(self,status,fn,*args,**kw):
        with self.assertRaises(api.APIError) as e:fn(*args,**kw)
        self.assertEqual(e.exception.status,status)
    def long_session(self,c,until):
        with api.connect(self.path,True) as db:db.execute('UPDATE auth_sessions SET expires_at=?',(api.stamp(until),))

    def test_catalog_free_vip_expired_buy_independent_no_vip_extension(self):
        self.assertEqual((wallet.CATALOG['quantity'],wallet.CATALOG['amount'],wallet.CATALOG['validDays']),(100,50000,90))
        for args in ({},{'vip':True},{'expired':True}):
            c=self.user(**args);before=c.call('session')['account'];receipt=self.buy(c)
            self.assertEqual(receipt['credits'],100);self.assertEqual(receipt['expires_at'],api.stamp(NOW+timedelta(days=90)))
            self.assertEqual(c.call('session')['account'],before)
            self.exam(c,self.keys[:1]);self.assertEqual(self.state(c)['privateRemaining'],100 if args.get('vip') else 99)
        self.record(catalog100_50000_90=True,allMemberships=True,noVipExtension=True)

    def test_pending_failed_confirm_duplicate_and_credit_race_once(self):
        c=self.user();body={'requestKey':'same-order-request','sku':wallet.CATALOG['sku']}
        def order(_):return self.invoke(c,wallet.create_order,body)
        with ThreadPoolExecutor(max_workers=4) as pool:orders=list(pool.map(order,range(4)))
        self.assertEqual(len({o['orderId'] for o in orders}),1);self.assertEqual(self.state(c)['privateRemaining'],0)
        self.deny(402,self.exam,c,self.keys[:1])
        oid=orders[0]['orderId']
        def confirm(_):return self.invoke(c,wallet.mock_event,{'orderId':oid},confirm=True)
        with ThreadPoolExecutor(max_workers=4) as pool:receipts=list(pool.map(confirm,range(4)))
        self.assertEqual(len({r['receipt']['pack_id'] for r in receipts}),1);self.assertEqual(self.state(c)['privateRemaining'],100)
        failed=self.invoke(c,wallet.create_order,{'requestKey':'failed-order-request','sku':wallet.CATALOG['sku']})
        self.invoke(c,wallet.mock_event,{'orderId':failed['orderId']},confirm=False)
        self.assertEqual(self.invoke(c,wallet.mock_event,{'orderId':failed['orderId']},confirm=True)['status'],'failed')
        self.assertEqual(self.count('wallet_packs'),1)
        self.record(orderRaceOne=True,eventRaceCredit100Once=True,pendingFailedNoCredit=True)

    def test_tampered_catalog_success_owner_role_quantity_expiry_denied(self):
        c=self.user();other=self.user()
        for name,value in [('amount',0),('quantity',10000),('role','VIP'),('expiresAt','2099'),('accountId',1),('success',True)]:
            self.deny(400,self.invoke,c,wallet.create_order,{'requestKey':'forged-'+name,'sku':wallet.CATALOG['sku'],name:value})
        order=self.invoke(c,wallet.create_order,{'requestKey':'owner-only-order','sku':wallet.CATALOG['sku']})
        self.deny(404,self.invoke,other,wallet.order_view,order['orderId'])
        self.deny(404,self.invoke,other,wallet.mock_event,{'orderId':order['orderId']},confirm=True)
        self.deny(400,self.invoke,c,wallet.mock_event,{'orderId':order['orderId'],'success':True},confirm=True)
        self.assertEqual(self.count('wallet_packs'),0);self.record(tamperingDenied=True,ownerIsolated=True)

    def test_vip_priority_free_and_received_zero_no_client_skip(self):
        c=self.user(vip=True);self.buy(c);self.exam(c,setIndex=1)
        self.assertEqual(self.state(c)['vip']['dayUsed'],0)
        self.exam(c,self.keys[:2]);self.exam(c,self.keys[:2]);self.exam(c,setIndex=1)
        self.assertEqual(self.state(c)['privateRemaining'],100);self.assertEqual(self.state(c)['vip']['dayUsed'],2)
        q=self.quote(c,{'contentKeys':self.keys[2:3]});self.assertEqual((q['vip'],q['private']),(1,0))
        c.call('exams',{'requestKey':'cannot-skip-vip','contentKeys':self.keys[2:3],'quoteId':q['quoteId'],'confirmWallet':True})
        self.assertEqual(self.state(c)['privateRemaining'],100)
        self.record(freeZero=True,receivedZero=True,vipFirst=True,skipVipNotPossible=True)

    def test_mixed_day_boundary_28_100_private50_becomes30_102_47(self):
        c=self.user(vip=True);p=self.buy(c);self.spent(p,50);self.seed(c,28,100)
        q=self.quote(c,{'contentKeys':self.keys});self.assertEqual((q['vip'],q['private']),(2,3))
        self.exam(c,self.keys);s=self.state(c)
        self.assertEqual((s['vip']['dayUsed'],s['vip']['cycleUsed'],s['privateRemaining']),(30,102,47))
        with api.connect(self.path) as db:sources=[r[0] for r in db.execute('SELECT source FROM wallet_debits ORDER BY rowid')]
        self.assertEqual(sources,['vip','vip','pack','pack','pack']);self.record(before=[28,100,50],after=[30,102,47],allocation=sources,seededCounters=True)

    def test_mixed_cycle_boundary_298_uses_two_vip_three_pack(self):
        c=self.user(vip=True);p=self.buy(c);self.spent(p,50);self.seed(c,0,298);self.exam(c,self.keys);s=self.state(c)
        self.assertEqual((s['vip']['dayUsed'],s['vip']['cycleUsed'],s['privateRemaining']),(2,300,47));self.record(after=[2,300,47],seededCounters=True)

    def test_day_full_cycle_full_both_use_private_total_over30(self):
        for day,cycle in [(30,100),(0,300),(30,300)]:
            c=self.user(vip=True);self.buy(c);self.seed(c,day,cycle);self.exam(c,self.keys);s=self.state(c)
            self.assertEqual((s['vip']['dayUsed'],s['vip']['cycleUsed'],s['privateRemaining']),(day,cycle,95))
        self.record(dayOnlyCycleOnlyBoth=True,total35Allowed=True,seeded30Not30Authored=True)

    def test_insufficient_total_is_all_or_nothing(self):
        c=self.user(vip=True);p=self.buy(c);self.spent(p,98);self.seed(c,28,100)
        self.deny(402,self.exam,c,self.keys)
        for table in ('pilot_grants','wallet_debits','exam_attempts','pilot_requests'):self.assertEqual(self.count(table),0)
        self.assertEqual(self.state(c)['privateRemaining'],2);self.assertEqual(self.state(c)['vip']['dayUsed'],28)
        self.record(partialDebit=False,partialGrant=False,privateRemaining=2)

    def test_saigon_midnight_vip_resumes_private_balance_retained(self):
        c=self.user(vip=True);self.buy(c)
        with patch.object(api,'now',return_value=datetime(2026,11,16,16,59,59,tzinfo=timezone.utc)):
            self.seed(c,30,100);self.exam(c,self.keys[:2]);self.assertEqual(self.state(c)['privateRemaining'],98)
        with patch.object(api,'now',return_value=datetime(2026,11,16,17,tzinfo=timezone.utc)):
            self.exam(c,self.keys[2:]);s=self.state(c);self.assertEqual((s['vip']['dayUsed'],s['privateRemaining']),(3,98));self.assertEqual(s['vip']['day'],'2026-11-17')
        self.record(midnightReset=True,privateRetained=98,vipResumes=True)

    def test_cycle_anchor_30days_not_calendar_month_reset(self):
        anchor=NOW-timedelta(days=30)+timedelta(seconds=1);c=self.user(vip=True,anchor=anchor);self.buy(c);self.seed(c,0,300)
        self.exam(c,self.keys[:2]);self.assertEqual(self.state(c)['privateRemaining'],98)
        with patch.object(api,'now',return_value=NOW+timedelta(seconds=1)):
            self.exam(c,self.keys[2:]);s=self.state(c);self.assertEqual((s['vip']['cycleUsed'],s['privateRemaining']),(3,98))
        self.record(anchorBoundaryReset=True,calendarMonthNotUsed=True,privateRetained=98)

    def test_early_renewal_does_not_reset_and_free_upgrade_prefers_vip(self):
        c=self.user(vip=True,anchor=NOW-timedelta(days=5));self.buy(c);self.seed(c,30,300)
        with api.connect(self.path,True) as db:db.execute('UPDATE accounts SET vip_expires_at=?',(api.stamp(NOW+timedelta(days=180)),))
        self.exam(c,self.keys[:1]);self.assertEqual(self.state(c)['privateRemaining'],99);self.assertEqual(self.state(c)['vip']['cycleUsed'],300)
        free=self.user();self.buy(free);self.exam(free,self.keys[:1])
        with api.connect(self.path,True) as db:
            session=self.session(free,db);db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(NOW+timedelta(days=30)),session['account_id']))
            db.execute('INSERT INTO wallet_terms VALUES (?,?,?)',(session['student_id'],api.stamp(),wallet.POLICY))
        self.exam(free,self.keys);s=self.state(free);self.assertEqual((s['vip']['dayUsed'],s['privateRemaining']),(4,99))
        self.record(earlyRenewNoReset=True,upgradeVipFirst=True,noRetroRefund=True)

    def test_vip_exact_expiry_does_not_freeze_private_wallet(self):
        c=self.user(vip=True);self.buy(c)
        with api.connect(self.path,True) as db:db.execute('UPDATE accounts SET vip_expires_at=?',(api.stamp(),))
        self.exam(c,self.keys[:2]);s=self.state(c);self.assertEqual(s['membership'],'Free');self.assertEqual((s['vip']['dayUsed'],s['privateRemaining']),(0,98))
        self.record(vipExpiryInclusive=True,privateStillUsable=True)

    def test_pack_89days235959_valid_exact90days_excluded(self):
        c=self.user();self.buy(c);self.long_session(c,NOW+timedelta(days=91))
        with patch.object(api,'now',return_value=NOW+timedelta(days=90)-timedelta(seconds=1)):
            self.exam(c,self.keys[:1]);self.assertEqual(self.state(c)['privateRemaining'],99)
        with patch.object(api,'now',return_value=NOW+timedelta(days=90)):
            self.deny(402,self.exam,c,self.keys[1:2]);self.assertEqual(self.state(c)['privateRemaining'],0)
            self.assertEqual(self.state(c)['packs'][0]['remaining'],99)
        self.record(before90Valid=True,exact90Excluded=True,expiredBalanceAuditable=99)

    def test_fefo_nearest_expiry_and_tie_stable(self):
        c=self.user();first=self.buy(c);self.spent(first,99)
        with patch.object(api,'now',return_value=NOW+timedelta(seconds=1)):second=self.buy(c)
        self.exam(c,self.keys[:3])
        with api.connect(self.path) as db:ids=[r[0] for r in db.execute("SELECT pack_id FROM wallet_debits WHERE source='pack' ORDER BY rowid")]
        self.assertEqual(ids,[first['pack_id'],second['pack_id'],second['pack_id']])
        tie=self.user();a=self.buy(tie);b=self.buy(tie);self.exam(tie,self.keys[:1]);s=self.state(tie)
        self.assertEqual(next(p['pack_id'] for p in s['packs'] if p['remaining']==99),min(a['pack_id'],b['pack_id']))
        self.record(fefo=True,stableTie='expires_at,pack_id')

    def test_expired_pack_not_spent_when_newer_pack_valid(self):
        c=self.user();old=self.buy(c);self.long_session(c,NOW+timedelta(days=92))
        with patch.object(api,'now',return_value=NOW+timedelta(days=1)):new=self.buy(c)
        with patch.object(api,'now',return_value=NOW+timedelta(days=90)):
            self.exam(c,self.keys[:2]);s=self.state(c)
            self.assertEqual(next(p['remaining'] for p in s['packs'] if p['pack_id']==old['pack_id']),100)
            self.assertEqual(next(p['remaining'] for p in s['packs'] if p['pack_id']==new['pack_id']),98)
        self.record(expiredSkipped=True,validNewPackUsed=True)

    def test_pack_expiry_keeps_save_submit_review_replay_snapshot(self):
        c=self.user();other=self.user();self.buy(c);self.long_session(c,NOW+timedelta(days=91))
        with patch.object(api,'now',return_value=NOW+timedelta(days=90)-timedelta(seconds=1)):exam=self.exam(c,self.keys[:1])
        with patch.object(api,'now',return_value=NOW+timedelta(days=90)):
            q=self.values[0]['questions'][5];answer=q.get('correctAnswer') if q['responseType']=='short-answer' else next(x['text'] for x in q['choices'] if x['id']==q['correctChoiceId'])
            c.call('exams/'+exam['id']+'/answers',{'position':1,'answer':answer})
            self.assertEqual(c.call('exams/'+exam['id']+'/submit',{})['exam']['score'],10)
            self.exam(c,replayExamId=int(exam['id']))
            self.deny(402,self.exam,c,self.keys[1:2])
        self.assertEqual(self.count('wallet_debits'),1);self.record(afterPackExpiryFinishReviewReplay=True,noNewRights=True)

    def test_revision_same_identity_zero_and_expired_only_old_snapshot(self):
        c=self.user();pack=self.buy(c);old=self.exam(c,self.keys[:1])
        package,manifest,sources=deepcopy(self.values);package['questions'][5]['revision']+=1
        import_package(self.path,package,manifest,sources,allow_draft_qa=True)
        self.exam(c,self.keys[:1]);self.assertEqual(self.state(c)['privateRemaining'],99)
        self.spent(pack,99)
        self.deny(403,self.exam,c,self.keys[:1]);self.exam(c,replayExamId=int(old['id']))
        self.assertEqual(self.count('wallet_debits'),1);self.record(revisionZero=True,oldSnapshotReplay=True,noUnfundedNewRevision=True)

    def test_private_race_last_two_five_requests_never_negative(self):
        c=self.user();p=self.buy(c);self.spent(p,98)
        def run(i):
            try:return self.exam(c,self.keys[i:i+1])['id']
            except api.APIError as e:return e.status
        with ThreadPoolExecutor(max_workers=5) as pool:r=list(pool.map(run,range(5)))
        self.assertEqual(sum(isinstance(x,str) for x in r),2);self.assertEqual(r.count(402),3)
        self.assertEqual(self.state(c)['privateRemaining'],0);self.assertEqual(self.count('wallet_debits'),2);self.assertEqual(self.count('exam_attempts'),2)
        self.record(success=2,insufficient=3,negativeBalance=False)

    def test_race_between_last_vip_and_last_private(self):
        c=self.user(vip=True);p=self.buy(c);self.spent(p,99);self.seed(c,29,299)
        def run(i):
            try:return self.exam(c,self.keys[i:i+1])['id']
            except wallet.QuoteChanged:
                try:return self.exam(c,self.keys[i:i+1])['id']
                except api.APIError as e:return e.status
            except api.APIError as e:return e.status
        with ThreadPoolExecutor(max_workers=5) as pool:r=list(pool.map(run,range(5)))
        # A quote racing to require MORE private can also return409, requiring user reconfirmation.
        self.assertEqual(sum(isinstance(x,str) for x in r),2);self.assertTrue(all(isinstance(x,str) or x in (402,409) for x in r))
        s=self.state(c);self.assertEqual((s['vip']['dayUsed'],s['vip']['cycleUsed'],s['privateRemaining']),(30,300,0));self.assertEqual(self.count('wallet_debits'),2)
        self.record(vip=1,private=1,noOverrun=True)

    def test_identical_request_race_one_attempt_one_debit_payload409(self):
        c=self.user();self.buy(c);q=self.quote(c,{'contentKeys':self.keys[:1]})
        body={'requestKey':'same-wallet-request','contentKeys':self.keys[:1],'quoteId':q['quoteId'],'confirmWallet':True}
        def run(_):return c.call('exams',body)['exam']['id']
        with ThreadPoolExecutor(max_workers=4) as pool:ids=list(pool.map(run,range(4)))
        self.assertEqual(len(set(ids)),1);self.assertEqual(self.count('wallet_attempt_receipts'),1);self.assertEqual(self.count('wallet_debits'),1);self.assertEqual(self.count('exam_attempts'),1)
        self.deny(409,c.call,'exams',{**body,'contentKeys':self.keys[1:2]})
        with patch.object(api,'now',return_value=NOW+timedelta(minutes=3)):self.assertEqual(c.call('exams',body)['exam']['id'],ids[0])
        self.record(sameRequestOneAttempt=True,expiredQuoteRetryNoDebit=True,differentPayload409=True)

    def test_failure_after_debit_grant_before_attempt_rolls_back_retry(self):
        c=self.user();self.buy(c);q=self.quote(c,{'contentKeys':self.keys[:2]})
        body={'requestKey':'rollback-wallet-request','contentKeys':self.keys[:2],'quoteId':q['quoteId'],'confirmWallet':True}
        with api.connect(self.path,True) as db:db.execute("CREATE TRIGGER fail_attempt BEFORE INSERT ON exam_attempts BEGIN SELECT RAISE(ABORT,'wallet injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):c.call('exams',body)
        for table in ('wallet_debits','wallet_attempt_receipts','pilot_grants','exam_items','exams','exam_attempts','pilot_requests'):self.assertEqual(self.count(table),0)
        self.assertEqual(self.state(c)['privateRemaining'],100)
        with api.connect(self.path,True) as db:db.execute('DROP TRIGGER fail_attempt')
        c.call('exams',body);self.assertEqual(self.state(c)['privateRemaining'],98)
        self.record(rollbackAfterDebitAndGrant=True,retry=True)

    def test_quote_race_never_spends_more_private_than_confirmed(self):
        c=self.user(vip=True);self.buy(c);self.seed(c,28,100)
        q=self.quote(c,{'contentKeys':self.keys[2:]});self.assertEqual((q['vip'],q['private']),(2,1))
        self.exam(c,self.keys[:2])
        body={'requestKey':'stale-quote-request','contentKeys':self.keys[2:],'quoteId':q['quoteId'],'confirmWallet':True}
        with self.assertRaises(wallet.QuoteChanged) as e:c.call('exams',body)
        self.assertEqual(e.exception.allocation['private'],3);self.assertEqual(self.state(c)['privateRemaining'],100);self.assertEqual(self.count('pilot_grants'),2)
        self.exam(c,self.keys[2:]);self.assertEqual(self.state(c)['privateRemaining'],97)
        self.record(confirmedPrivate=1,recomputedPrivate=3,reconfirmRequired=True,unconfirmedDebit=0)

    def test_quote_expiry_owner_tamper_selector_and_no_preview_debit(self):
        c=self.user();other=self.user();self.buy(c);q=self.quote(c,{'contentKeys':self.keys[:1]})
        self.assertEqual(self.count('wallet_debits'),0);self.assertEqual(self.count('pilot_grants'),0)
        body={'requestKey':'quote-expiry-request','contentKeys':self.keys[:1],'quoteId':q['quoteId'],'confirmWallet':True}
        with patch.object(api,'now',return_value=NOW+timedelta(minutes=2)):self.deny(409,c.call,'exams',body)
        self.deny(409,c.call,'exams',{**body,'contentKeys':self.keys[1:2]})
        self.buy(other);self.deny(409,other.call,'exams',body)
        self.deny(409,c.call,'exams',{**body,'confirmWallet':False})
        self.assertEqual(self.count('wallet_debits'),0);self.record(previewNoDebit=True,quoteExpiryOwnerSelectorConfirmation=True)

    def test_scope_unknown_wrong_grade_free_historical_fail_closed(self):
        c=self.user();self.buy(c)
        self.deny(404,self.exam,c,['not-in-pilot'])
        with api.connect(self.path,True) as db:db.execute("UPDATE wallet_scopes SET keys_json=?",(api.packed(self.keys[1:]),))
        self.deny(403,self.exam,c,self.keys[:1])
        with api.connect(self.path,True) as db:
            db.execute('UPDATE pilot_sets SET window_start=?,window_end=?',('2026-11-09','2026-11-16'))
        self.deny(403,self.exam,c,self.values[1]['orderedContentKeys'][:1]);self.assertEqual(self.count('wallet_debits'),0)
        self.record(outOfScopeDenied=True,unknownDenied=True,freeHistoryNotWholeWarehouse=True)

    def test_missing_term_marker_flag_off_and_legacy_preserved(self):
        c=self.user(vip=True)
        with api.connect(self.path,True) as db:db.execute('DELETE FROM wallet_terms')
        self.deny(503,self.exam,c,self.keys[:1])
        self.server.free_vip_pilot=None
        self.assertEqual(len(c.call('exams',{'requestKey':'flag-off-legacy','count':3,'topic':'decimal'})['exam']['questions']),3)
        self.assertEqual(self.count('wallet_debits'),0);self.record(missingAnchorDenied=True,flagOffLegacy=True)

    def test_credit_storage_failure_rolls_back_order_then_retry_credits_once(self):
        c=self.user();order=self.invoke(c,wallet.create_order,{'requestKey':'credit-failure-order','sku':wallet.CATALOG['sku']})
        with api.connect(self.path,True) as db:db.execute("CREATE TRIGGER fail_credit BEFORE INSERT ON wallet_packs BEGIN SELECT RAISE(ABORT,'credit injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.invoke(c,wallet.mock_event,{'orderId':order['orderId']},confirm=True)
        self.assertEqual(self.invoke(c,wallet.order_view,order['orderId'])['status'],'pending');self.assertEqual(self.count('wallet_packs'),0)
        with api.connect(self.path,True) as db:db.execute('DROP TRIGGER fail_credit')
        for _ in range(2):self.invoke(c,wallet.mock_event,{'orderId':order['orderId']},confirm=True)
        self.assertEqual(self.state(c)['privateRemaining'],100);self.assertEqual(self.count('wallet_packs'),1)
        self.record(creditFailureOrderRollback=True,retryCredit100Once=True)
