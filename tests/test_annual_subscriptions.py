"""Yearly checkout, immutable paid periods and one 3,600-question annual budget."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import secrets,unittest,json,time,hmac,hashlib
from backend import platform_api as api,wallet_qa as wallet
from backend.arena import Arena
from backend.payments import create_order,settle_order,settlement_problem
from backend.subscriptions import product,active_annual_cycle,add_months
from backend.free_vip_pilot import PilotConfig
from scripts.import_mcq_qa import initialize_empty_qa
from test_platform_api import Client

NOW=datetime(2026,11,16,5,tzinfo=timezone.utc)
class AnnualSubscriptionTests(unittest.TestCase):
    def setUp(self):
        work=Path(__file__).resolve().parents[1]/'work';work.mkdir(exist_ok=True)
        self.tmp=TemporaryDirectory(dir=work);self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'annual.sqlite3'
        initialize_empty_qa(self.path,seed_learning=False)
        clock=patch.object(api,'now',return_value=NOW);clock.start();self.addCleanup(clock.stop)
        self.client=Client(SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena()))
        result=self.client.call('auth/register',{'login':'annual-'+secrets.token_hex(5),'password':secrets.token_urlsafe(20),'name':'Học sinh thử','birthYear':2016})
        self.aid=result['account']['id']
        with api.connect(self.path,True) as db:
            self.sid=db.execute('SELECT id FROM students WHERE account_id=?',(self.aid,)).fetchone()[0]
            wallet.initialize(db,[]);db.execute('INSERT INTO wallet_terms VALUES (?,?,?)',(self.sid,api.stamp(),wallet.POLICY))
        self.session={'account_id':self.aid,'student_id':self.sid,'birth_year':2016}
    def buy(self,db,plan='VIP',period='year'):
        result=create_order(db,self.session,{'plan':plan,'period':period})['order']
        order=db.execute('SELECT * FROM payment_orders WHERE id=?',(result['id'],)).fetchone()
        self.assertTrue(settle_order(db,order,'staff'))
        return db.execute('SELECT * FROM payment_orders WHERE id=?',(result['id'],)).fetchone()
    def annual_config(self,db):
        annual=active_annual_cycle(db,self.session);self.assertIsNotNone(annual)
        return replace(PilotConfig(wallet=True),vip_daily=30,vip_cycle=3600,vip_cycle_start=annual['start'],vip_cycle_end=annual['end'])
    def test_server_prices_and_checkout_snapshot(self):
        for plan,expected in [('VIP',1000000),('VIP+',2000000)]:
            with api.connect(self.path,True) as db:
                result=create_order(db,self.session,{'plan':plan,'period':'year','amount':1,'vip_months':120})['order']
                self.assertEqual((result['amount'],result['vip_months'],result['subscription_period']),(expected,12,'year'))
                self.assertEqual(result['vip_unit_price'],product(plan,'month')['amount'])
                self.assertIsNone(db.execute('SELECT vip_expires_at FROM accounts WHERE id=?',(self.aid,)).fetchone()[0])
                self.assertEqual(result['id'],create_order(db,self.session,{'plan':plan,'period':'year'})['order']['id'])
        for period in ['quarter',12,True,{},None]:
            with self.assertRaises(api.APIError):product('VIP',period)
    def test_switching_period_cancels_old_qr_without_repricing_it(self):
        with api.connect(self.path,True) as db:
            month=create_order(db,self.session,{})['order'];year=create_order(db,self.session,{'period':'year'})['order']
            old=dict(db.execute('SELECT * FROM payment_orders WHERE id=?',(month['id'],)).fetchone())
            self.assertEqual(old['status'],'cancelled');self.assertEqual(old['amount'],100000);self.assertEqual(old['vip_months'],1)
            self.assertNotEqual(month['reference'],year['reference']);self.assertEqual(year['amount'],1000000)
            self.assertEqual(settlement_problem(db,old),'order_cancelled')
    def test_year_settlement_is_idempotent_and_preserves_queued_renewal(self):
        with api.connect(self.path,True) as db:
            first=self.buy(db);self.assertEqual(first['subscription_ends_at'],add_months(api.stamp(),12))
            self.assertFalse(settle_order(db,first,'sepay'));self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0],1)
            second=self.buy(db);self.assertEqual(second['subscription_starts_at'],first['subscription_ends_at'])
            self.assertEqual(active_annual_cycle(db,self.session)['start'],first['subscription_starts_at'])
        boundary=datetime.fromisoformat(first['subscription_ends_at'])
        with patch.object(api,'now',return_value=boundary),api.connect(self.path) as db:
            self.assertEqual(active_annual_cycle(db,self.session)['start'],second['subscription_starts_at'])
    def test_plus_year_grants_twelve_months_and_calendar_leap_clamp(self):
        self.assertEqual(add_months('2028-02-29T05:00:00Z',12),'2029-02-28T05:00:00Z')
        with api.connect(self.path,True) as db:
            order=self.buy(db,'VIP+');row=db.execute('SELECT vip_plus_expires_at,vip_expires_at FROM accounts WHERE id=?',(self.aid,)).fetchone()
            self.assertEqual(row['vip_plus_expires_at'],order['subscription_ends_at']);self.assertEqual(row['vip_expires_at'],order['subscription_ends_at'])
    def test_cross_tier_annual_upgrade_queues_question_budget_without_resetting_current_usage(self):
        with api.connect(self.path,True) as db:
            first=self.buy(db);config=self.annual_config(db)
            db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(self.sid,NOW.date().isoformat(),config.vip_cycle_start,0,3600,'Synthetic exhausted existing year'))
            second=self.buy(db,'VIP+')
            self.assertEqual(second['subscription_starts_at'],first['subscription_ends_at'])
            self.assertEqual(active_annual_cycle(db,self.session)['start'],first['subscription_starts_at'])
            self.assertEqual(wallet.vip_budget(db,self.session,self.annual_config(db))['available'],0)
    def test_annual_budget_never_resets_at_month_boundary_and_daily_limit_stays_thirty(self):
        with api.connect(self.path,True) as db:
            first=self.buy(db);config=self.annual_config(db)
            db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(self.sid,NOW.date().isoformat(),config.vip_cycle_start,29,3599,'Synthetic quota boundary only'))
            state=wallet.vip_budget(db,self.session,config);self.assertEqual((state['available'],state['dayLimit'],state['cycleLimit']),(1,30,3600))
        with patch.object(api,'now',return_value=NOW+timedelta(days=45)),api.connect(self.path,True) as db:
            config=self.annual_config(db);state=wallet.vip_budget(db,self.session,config)
            self.assertEqual((state['cycleUsed'],state['available'],state['cycleStart']),(3599,1,first['subscription_starts_at']))
            db.execute('UPDATE wallet_usage_seeds SET cycle_used=3600 WHERE student_id=?',(self.sid,))
            self.assertEqual(wallet.vip_budget(db,self.session,config)['available'],0)
        with patch.object(api,'now',return_value=NOW+timedelta(days=300)),api.connect(self.path) as db:
            self.assertEqual(wallet.vip_budget(db,self.session,self.annual_config(db))['available'],0)
    def test_new_paid_year_uses_a_new_budget_only_after_previous_year_ends(self):
        with api.connect(self.path,True) as db:
            first=self.buy(db);second=self.buy(db);config=self.annual_config(db)
            db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(self.sid,NOW.date().isoformat(),config.vip_cycle_start,0,3600,'Synthetic spent annual quota'))
            self.assertEqual(wallet.vip_budget(db,self.session,config)['available'],0)
        with patch.object(api,'now',return_value=datetime.fromisoformat(first['subscription_ends_at'])),api.connect(self.path) as db:
            state=wallet.vip_budget(db,self.session,self.annual_config(db));self.assertEqual(state['cycleStart'],second['subscription_starts_at']);self.assertEqual((state['cycleUsed'],state['available']),(0,30))
    def test_invalid_annual_price_or_month_count_does_not_settle(self):
        for field,value in [('amount',1200000),('vip_months',1),('vip_unit_price',1)]:
            with api.connect(self.path,True) as db:
                order=create_order(db,self.session,{'period':'year'})['order'];db.execute('UPDATE payment_orders SET '+field+'=? WHERE id=?',(value,order['id']))
                row=db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone();self.assertEqual(settlement_problem(db,row),'invalid_product')
                db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?",(order['id'],))
    def test_monthly_budget_and_price_remain_unchanged(self):
        with api.connect(self.path,True) as db:
            order=self.buy(db,period='month');self.assertEqual((order['amount'],order['vip_months']),(100000,1));self.assertIsNone(active_annual_cycle(db,self.session))
            state=wallet.vip_budget(db,self.session,PilotConfig(wallet=True));self.assertEqual((state['dayLimit'],state['cycleLimit'],state['cyclePeriod']),(30,300,'month'))
    def signed_annual_payment(self,plan):
        from backend.payments import receive_webhook
        env={'MAM_TOAN_SEPAY_ENABLED':'1','MAM_TOAN_SEPAY_WEBHOOK_SECRET':'QA-ONLY-ANNUAL-PAYMENT-SIGNATURE-NOT-LIVE','MAM_TOAN_BANK_ID':'ACB','MAM_TOAN_BANK_ACCOUNT':'123456789','MAM_TOAN_BANK_NAME':'QA ONLY'}
        with patch.dict('os.environ',env):
            with api.connect(self.path,True) as db:order=create_order(db,self.session,{'plan':plan,'period':'year'})['order']
            event={'id':secrets.randbelow(10**10)+1,'gateway':'ACB','accountNumber':'123456789','code':order['reference'],'content':order['reference'],'transferType':'in','transferAmount':order['amount']+200000,'transactionDate':'2026-11-16 12:00:00','referenceCode':'QA-ANNUAL'}
            def receive(value):
                raw=json.dumps(value).encode();timestamp=str(int(time.time()));signature=hmac.new(env['MAM_TOAN_SEPAY_WEBHOOK_SECRET'].encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
                return receive_webhook(self.path,{'X-SePay-Timestamp':timestamp,'X-SePay-Signature':'sha256='+signature},raw)
            receive(event)
            with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?',(order['id'],)).fetchone()[0],'pending')
            correct={**event,'id':event['id']+1,'transferAmount':order['amount']};receive(correct);receive(correct)
            with api.connect(self.path) as db:
                saved=db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone();self.assertEqual(saved['status'],'paid');self.assertIsNotNone(active_annual_cycle(db,self.session));self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?',(self.aid,)).fetchone()[0],1)
    def test_signed_vip_year_wrong_amount_and_duplicate_webhook(self):self.signed_annual_payment('VIP')
    def test_signed_plus_year_wrong_amount_and_duplicate_webhook(self):self.signed_annual_payment('VIP+')

class AnnualNativeBudgetTests(unittest.TestCase):
    def test_main_paid_year_is_enforced_in_the_native_wallet_without_monthly_reset(self):
        if not Path('pilot-inputs/batch-manifest.json').exists():self.skipTest('Private native inputs; covered by the local full release gate')
        from backend.local_pilot import LocalPilot
        from backend.database import initialize
        from test_free_vip_pilot import Client as NativeClient
        work=Path(__file__).resolve().parents[1]/'work';work.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=work) as folder,patch.object(api,'now',return_value=NOW):
            main=Path(folder)/'main.sqlite3';pilot=Path(folder)/'pilot.sqlite3';initialize(main);api.initialize_catalog(main)
            provider=LocalPilot(main,pilot,Path('pilot-inputs'),restructure_inputs=Path('restructure-inputs'))
            server=SimpleNamespace(database_path=main,server_port=18931,local_pilot=provider,local_pilot_ports={18931},real_accounts=True,review_upgrades=False,arena=Arena())
            actor=NativeClient(server);account=actor.call('auth/register',{'login':'native-annual-'+secrets.token_hex(5),'password':secrets.token_urlsafe(20),'name':'QA gói năm','birthYear':2016})['account']['id']
            with api.connect(main,True) as db:
                session=api.read_session(actor,db);order=create_order(db,session,{'period':'year'})['order'];settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(order['id'],)).fetchone(),'staff')
                db.execute('UPDATE auth_sessions SET expires_at=? WHERE account_id=?',(api.stamp(NOW+timedelta(days=500)),account))
            def catalogue():
                actor.headers['X-CSRF-Token']=actor.csrf;actor.path='/api/local-pilot/catalogue';return provider.request(actor,'GET','catalogue',None,{})
            first=catalogue()['wallet']['vip'];self.assertEqual((first['dayLimit'],first['cycleLimit'],first['cyclePeriod']),(30,3600,'year'))
            with api.connect(pilot,True) as db:
                sid=db.execute('SELECT pilot_student_id FROM local_principals WHERE main_account_id=?',(account,)).fetchone()[0]
                db.execute('INSERT INTO wallet_usage_seeds VALUES (?,?,?,?,?,?)',(sid,first['day'],first['cycleStart'],0,3600,'Synthetic annual exhaustion boundary'))
            with patch.object(api,'now',return_value=NOW+timedelta(days=45)):
                later=catalogue()['wallet']['vip'];self.assertEqual((later['cycleUsed'],later['available'],later['cycleStart']),(3600,0,first['cycleStart']))
