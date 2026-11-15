"""Main/pilot isolation tests use only newly created fake stores; no runtime data reads."""
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
import json,os,secrets,sqlite3,tempfile,unittest
from unittest.mock import patch
from backend import platform_api as api
from backend.database import initialize
from backend.arena import Arena
from backend.local_pilot import LocalPilot
from backend.free_vip_pilot import PilotConfig
from backend.wallet_qa import QuoteChanged
from test_free_vip_pilot import Client

class LocalPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path('pilot-inputs/manifest.json').is_file():raise unittest.SkipTest('Private learning sources: covered by the separate local release gate, never published in GitHub')
        Path('work').mkdir(exist_ok=True);cls.folder=tempfile.TemporaryDirectory(dir='work');cls.base=Path(cls.folder.name)/'main-base.sqlite3';initialize(cls.base);api.initialize_catalog(cls.base)
        cls.inputs=Path('pilot-inputs');cls.pbase=Path(cls.folder.name)/'pilot-base.sqlite3';LocalPilot(cls.base,cls.pbase,cls.inputs)
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    def setUp(self):
        self.main=Path(self.folder.name)/(secrets.token_hex(6)+'.sqlite3');self.pilot=self.main.with_name(self.main.stem+'-pilot.sqlite3')
        for source,dest in ((self.base,self.main),(self.pbase,self.pilot)):
            with closing(sqlite3.connect(source)) as a,closing(sqlite3.connect(dest)) as b:a.backup(b)
        self.provider=LocalPilot(self.main,self.pilot,self.inputs);self.server=SimpleNamespace(database_path=self.main,server_port=18931,local_pilot=self.provider,local_pilot_ports={18931},real_accounts=True,review_upgrades=False,arena=Arena())
    def actor(self,role='Free',grade=5):
        c=Client(self.server);state=c.call('auth/register',{'login':'qa-native-'+secrets.token_hex(6),'password':secrets.token_urlsafe(20),'name':'QA thí điểm','birthYear':api.academic()[0]-grade-5});aid=state['account']['id']
        with api.connect(self.main,True) as db:
            if role=='VIP':db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()+timedelta(days=60)),aid))
            elif role=='expired':db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(api.stamp(api.now()-timedelta(seconds=1)),aid))
            elif role=='SVip':db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal','2026-01-01T00:00:00Z')",(aid,))
        return c
    def call(self,c,path,body=None):
        c.headers['X-CSRF-Token']=c.csrf;u=urlsplit(path)
        return self.provider.request(c,'GET' if body is None else 'POST',u.path,body,parse_qs(u.query))
    def exam(self,c,**selector):
        quote=self.call(c,'quote',selector);body={'requestKey':secrets.token_hex(12),**selector,'quoteId':quote['quoteId'],'confirmWallet':bool(quote['private'])};return self.call(c,'exams',body)['exam'],body
    def logical(self):
        with api.connect(self.main) as db:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")];return {t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in tables}
    def test_main_session_authority_private_store_clock_and_metadata(self):
        c=self.actor('VIP');before=self.logical();clock=api.now;now=api.now();cat=self.call(c,'catalogue');self.assertIs(api.now,clock);self.assertLess(abs((api.now()-now).total_seconds()),10)
        self.assertEqual(len(cat['questions']),60);self.assertTrue(all(not(set(q)&{'prompt','answer','correctAnswer','solutionSteps'}) for q in cat['questions']));self.assertEqual(cat['wallet']['privateRemaining'],0)
        self.exam(c,contentKeys=cat['questions'][30:31] and [cat['questions'][30]['contentKey']],responseMode='choice');self.assertEqual(self.logical(),before)
        with api.connect(self.main) as db:self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_environment'").fetchone())
    def test_auth_csrf_host_grade_and_forged_principal(self):
        anon=Client(self.server)
        with self.assertRaises(api.APIError):self.call(anon,'catalogue')
        c=self.actor();cat=self.call(c,'catalogue');c.headers['Origin']='http://evil.invalid'
        with self.assertRaises(api.APIError):self.call(c,'quote',{'setIndex':1})
        c.headers['Origin']='http://127.0.0.1:18931'
        with self.assertRaises(api.APIError):self.call(c,'quote',{'setIndex':1,'studentId':1,'vip':True})
        c.headers['Host']='192.168.1.6:18931'
        with self.assertRaises(api.APIError):self.call(c,'catalogue')
        other=self.actor(grade=4)
        with self.assertRaisesRegex(api.APIError,'lớp 5'):self.call(other,'catalogue')
    def test_same_path_and_hardlink_fail_before_database_write(self):
        with self.assertRaisesRegex(ValueError,'separate'):LocalPilot(self.main,self.main,self.inputs)
        alias=self.main.with_suffix('.hardlink');os.link(self.main,alias)
        try:
            with self.assertRaisesRegex(ValueError,'separate'):LocalPilot(self.main,alias,self.inputs)
        finally:alias.unlink()
    def test_native_typed_save_delete_grade_and_private_lesson_owner(self):
        c=self.actor('VIP');other=self.actor();cat=self.call(c,'catalogue');keys=cat['typedEligible'][:2];exam,body=self.exam(c,contentKeys=keys,responseMode='typed');eid=exam['id']
        self.assertNotIn('answer',exam['questions'][0])
        for suffix in ('review','lesson?contentKey='+keys[0],'asset?contentKey='+keys[0]+'&sha='+('a'*64)):
            with self.assertRaises(api.APIError):self.call(c,'exams/'+eid+'/'+suffix)
        self.call(c,'exams/'+eid+'/answers',{'position':1,'answer':'0'});self.assertEqual(self.call(c,'exams/'+eid)['exam']['answers']['1'],'0')
        self.call(c,'exams/'+eid+'/answers',{'position':1,'answer':''});self.assertEqual(self.call(c,'exams/'+eid)['exam']['answers']['1'],'')
        bykey={q['contentKey']:q for q in self.provider.typed['questions']}
        for pos,key in enumerate(keys,1):self.call(c,'exams/'+eid+'/answers',{'position':pos,'answer':bykey[key]['correctAnswer']})
        self.assertEqual(self.call(c,'exams/'+eid+'/submit',{})['exam']['score'],10);self.assertEqual(self.call(c,'exams/'+eid+'/submit',{})['exam']['score'],10)
        lesson=self.call(c,'exams/'+eid+'/lesson?contentKey='+keys[0])['lesson'];self.assertEqual(len(lesson['sections']),3)
        with self.assertRaises(api.APIError):self.call(other,'exams/'+eid)
        with self.assertRaises(api.APIError):self.call(other,'exams/'+eid+'/lesson?contentKey='+keys[0])
        self.assertEqual(self.call(c,'exams',body)['exam']['id'],eid)
    def test_vip_same_key_modes_then_expiry_old_review_and_mock_wallet(self):
        c=self.actor('VIP');cat=self.call(c,'catalogue');key=next(k for k in cat['typedEligible'] if k in cat['wallet']['scopeKeys']);before=self.logical();choice,_=self.exam(c,contentKeys=[key],responseMode='choice');typed,_=self.exam(c,contentKeys=[key],responseMode='typed')
        self.assertEqual(self.call(c,'wallet')['vip']['dayUsed'],1);self.assertEqual(self.logical(),before)
        self.call(c,'exams/'+typed['id']+'/submit',{})
        with api.connect(self.main,True) as db:db.execute("UPDATE accounts SET vip_expires_at='2026-01-01T00:00:00Z'")
        self.assertFalse(self.call(c,'wallet')['vip']['active']);self.assertTrue(self.call(c,'exams/'+typed['id']+'/review')['exam']['submittedAt'])
        order=self.call(c,'orders',{'requestKey':secrets.token_hex(12),'sku':'qa.questions.100'});receipt=self.call(c,'mock-confirm',{'orderId':order['orderId']});self.call(c,'mock-confirm',{'orderId':order['orderId']});self.assertEqual(self.call(c,'wallet')['privateRemaining'],100)
    def test_svip_uses_server_entitlement_without_debiting_vip_or_pack(self):
        c=self.actor('SVip');cat=self.call(c,'catalogue');self.assertTrue(cat['internalUnlimited']);key=cat['wallet']['scopeKeys'][0];self.exam(c,contentKeys=[key],responseMode='choice');wallet=self.call(c,'wallet');self.assertEqual(wallet['vip']['dayUsed'],0);self.assertEqual(wallet['privateRemaining'],0)
        with api.connect(self.pilot) as db:
            row=db.execute('SELECT source,receipt_json FROM wallet_debits').fetchone();self.assertEqual(row['source'],'free');self.assertIn('server-internal-entitlement',row['receipt_json'])
    def test_expired_confirmation_keeps_mode_and_key_and_retry(self):
        c=self.actor('VIP');cat=self.call(c,'catalogue');selector={'contentKeys':cat['typedEligible'][:2],'responseMode':'typed'};q=self.call(c,'quote',selector)
        with api.connect(self.pilot,True) as db:db.execute("UPDATE wallet_quotes SET expires_at='2026-01-01T00:00:00Z'")
        body={'requestKey':secrets.token_hex(12),**selector,'quoteId':q['quoteId'],'confirmWallet':False}
        with self.assertRaises(QuoteChanged):self.call(c,'exams',body)
        fresh=self.call(c,'quote',selector);self.assertEqual(fresh['selector'],selector);body['quoteId']=fresh['quoteId'];exam=self.call(c,'exams',body)['exam'];self.assertEqual(self.call(c,'exams',body)['exam']['id'],exam['id'])

    def test_deep_json_returns_400_instead_of_connection_drop(self):
        from io import BytesIO
        from backend.server import Handler
        for depth in (200,7000):
            handler=object.__new__(Handler);payload=b'{"a":'+b'['*depth+b'0'+b']'*depth+b'}'
            handler.server=SimpleNamespace(local_pilot=object());handler.headers={'Content-Type':'application/json','Content-Length':str(len(payload))};handler.rfile=BytesIO(payload);handler.path='/api/local-pilot/quote';responses=[]
            handler.json_response=lambda status,data:responses.append((status,data))
            handler.local_pilot_request('POST','/api/local-pilot/quote');self.assertEqual(responses[0][0],400);self.assertEqual(handler.api_headers,{})
