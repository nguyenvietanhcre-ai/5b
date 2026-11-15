"""Policy tests use real dispatch/session/SQLite, exclusively synthetic databases."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
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
from scripts.free_vip_fixture import initialize_qa

NOW = datetime(2026,11,13,10,tzinfo=timezone.utc)


class Client:
    def __init__(self, server):
        self.server = server
        self.client_address = (secrets.token_hex(12),1234)
        self.headers = {'Host':'127.0.0.1:18931','Origin':'http://127.0.0.1:18931'}
        self.api_headers = {}
        self.csrf = ''

    def call(self, path, body=None):
        self.path = '/api/v1/' + path
        self.headers['X-CSRF-Token'] = self.csrf
        result, status = api.dispatch(self,'GET' if body is None else 'POST',self.path.split('?')[0],body)
        cookie = self.api_headers.pop('Set-Cookie',None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        if result.get('csrf'):
            self.csrf = result['csrf']
        assert status == 200
        return result


class FreeVipPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir='work')
        cls.base = Path(cls.directory.name)/'base.sqlite3'
        with patch.object(api,'now',return_value=NOW):
            initialize_qa(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.time = patch.object(api,'now',return_value=NOW)
        self.time.start()
        self.addCleanup(self.time.stop)
        self.path = Path(self.directory.name)/(secrets.token_hex(8)+'.sqlite3')
        src = sqlite3.connect(self.base)
        dst = sqlite3.connect(self.path)
        try:
            src.backup(dst)
        finally:
            src.close()
            dst.close()
        self.server = SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),free_vip_pilot=PilotConfig())

    def user(self, vip=False, grade=5):
        client = Client(self.server)
        state = client.call('auth/register', {'login':'qa-'+secrets.token_hex(8),'password':secrets.token_urlsafe(18),
            'name':'Học sinh thử','birthYear':api.academic()[0]-5-grade})
        aid = state['account']['id']
        if vip:
            self.expiry(aid,'2027-01-01T00:00:00Z')
        return client, aid

    def expiry(self, aid, expiry):
        with api.connect(self.path,True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(expiry,aid))

    def exam(self, client, **body):
        return client.call('exams', {'requestKey':secrets.token_hex(12), **body})['exam']

    def deny(self, status, client, path, body=None):
        with self.assertRaises(api.APIError) as caught:
            client.call(path,body)
        self.assertEqual(caught.exception.status,status)

    def count(self, sql, params=()):
        with api.connect(self.path) as db:
            return db.execute(sql,params).fetchone()[0]

    def test_guest_and_client_cannot_activate_flag(self):
        guest = Client(self.server)
        self.deny(401,guest,'pilot/sets')
        self.deny(401,guest,'exams',{'requestKey':'abcdefgh','setIndex':1})
        client,_ = self.user()
        del self.server.free_vip_pilot
        client.headers['X-Free-Vip-Pilot']='1'
        self.deny(404,client,'pilot/sets?enablePilot=1')
        exam=self.exam(client,count=3,topic='decimal',freeVipPilot=True)
        self.assertEqual(len(exam['questions']),3)  # old behavior, query/header/body cannot switch server policy

    def test_many_free_same_three_sets_and_only_thirty_keys(self):
        clients = [self.user()[0] for _ in range(4)]
        expected=[]
        for slot in range(1,4):
            views=[self.exam(c,setIndex=slot)['questions'] for c in clients]
            self.assertTrue(all(v==views[0] for v in views))
            self.assertEqual(len(views[0]),10)
            expected.extend(q['text'] for q in views[0])
        self.assertEqual(len(set(expected)),30)
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),120)
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants WHERE quota_charged=1'),0)

    def test_tamper_grade_week_ids_and_topic(self):
        client,_=self.user()
        for extra in ({'grade':4},{'week':1},{'windowStart':'2026-11-02'},{'topic':'decimal'},
                      {'questionVersionId':1},{'accountId':999},{'enablePilot':False}):
            self.deny(400,client,'exams',{'requestKey':secrets.token_hex(12),'setIndex':1,**extra})
        self.deny(403,client,'exams',{'requestKey':'abcdefgh','contentKeys':['qa-fixture-100']})
        self.deny(400,client,'exams',{'requestKey':'abcdefgh','setIndex':4})

    def test_owner_and_answers_only_after_submission(self):
        client,_=self.user()
        stranger,_=self.user()
        exam=self.exam(client,setIndex=1)
        self.assertNotIn('answer',json.dumps(exam['questions']))
        for suffix,body in (('',None),('/answers',{'position':1,'answer':'32'}),('/submit',{})):
            self.deny(404,stranger,'exams/'+exam['id']+suffix,body)
        self.deny(404,stranger,'exams',{'requestKey':'abcdefgh','replayExamId':int(exam['id'])})
        marked=client.call('exams/'+exam['id']+'/submit',{})['exam']
        self.assertIn('answer',marked['questions'][0])
        self.assertIn('solution',marked['questions'][0])
        self.assertEqual(marked,client.call('exams/'+exam['id']+'/submit',{})['exam'])

    def test_request_retry_and_conflicting_payload(self):
        client,_=self.user(vip=True)
        body={'requestKey':'same-key-123','contentKeys':['qa-fixture-100']}
        first=client.call('exams',body)
        self.assertEqual(first,client.call('exams',dict(reversed(list(body.items())))))
        self.deny(409,client,'exams',{**body,'contentKeys':['qa-fixture-101']})
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),1)

    def test_daily_cap_and_atomic_rejection_and_replay(self):
        client,_=self.user(vip=True)
        for offset in range(90,190,10):
            self.exam(client,contentKeys=[f'qa-fixture-{i:03}' for i in range(offset,offset+10)])
        self.assertEqual(client.call('pilot/sets')['newUsed'],100)
        self.deny(429,client,'exams',{'requestKey':'overflow-123','contentKeys':['qa-fixture-190']})
        self.assertEqual(self.count('SELECT count(*) FROM pilot_requests'),10)
        repeated=self.exam(client,contentKeys=['qa-fixture-090'])
        self.exam(client,replayExamId=int(repeated['id']))
        self.assertEqual(client.call('pilot/sets')['newUsed'],100)

    def test_race_last_quota_slots(self):
        client,_=self.user(vip=True)
        self.server.free_vip_pilot=PilotConfig(daily_new=10)
        def send(offset):
            other=Client(self.server)
            other.headers=dict(client.headers)
            other.csrf=client.csrf
            try:
                self.exam(other,contentKeys=[f'qa-fixture-{i:03}' for i in range(offset,offset+10)])
                return 200
            except api.APIError as e:
                return e.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(send,(90,100))),[200,429])
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),10)
        self.assertEqual(self.count('SELECT count(*) FROM pilot_requests'),1)

    def test_race_same_request_returns_single_attempt(self):
        client,_=self.user(vip=True)
        def send(_):
            other=Client(self.server)
            other.headers=dict(client.headers)
            other.csrf=client.csrf
            return other.call('exams',{'requestKey':'race-same-123','contentKeys':['qa-fixture-090']})['exam']['id']
        with ThreadPoolExecutor(max_workers=5) as pool:
            self.assertEqual(len(set(pool.map(send,range(5)))),1)
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),1)

    def test_local_midnight_and_lifetime_distinct(self):
        client,_=self.user(vip=True)
        self.server.free_vip_pilot=PilotConfig(daily_new=1)
        with patch.object(api,'now',return_value=datetime(2026,11,13,16,59,59,tzinfo=timezone.utc)):
            self.exam(client,contentKeys=['qa-fixture-090'])
            self.assertEqual(client.call('pilot/sets')['day'],'2026-11-13')
        with patch.object(api,'now',return_value=datetime(2026,11,13,17,tzinfo=timezone.utc)):
            self.exam(client,contentKeys=['qa-fixture-090'])
            self.assertEqual(client.call('pilot/sets')['newUsed'],0)
            self.exam(client,contentKeys=['qa-fixture-091'])
            self.assertEqual(client.call('pilot/sets')['day'],'2026-11-14')
            self.assertEqual(client.call('pilot/sets')['newUsed'],1)

    def test_monday_boundary_and_no_unpublished_fallback(self):
        client,_=self.user()
        with patch.object(api,'now',return_value=datetime(2026,11,15,16,59,59,tzinfo=timezone.utc)):
            before=self.exam(client,setIndex=1)
            self.assertEqual(client.call('pilot/sets')['windowStart'],'2026-11-09')
        with patch.object(api,'now',return_value=datetime(2026,11,15,17,tzinfo=timezone.utc)):
            after=self.exam(client,setIndex=1)
            self.assertEqual(client.call('pilot/sets')['windowStart'],'2026-11-16')
            self.assertNotEqual(before['questions'],after['questions'])
            self.assertEqual(client.call('exams/'+before['id'])['exam']['questions'],before['questions'])
        with api.connect(self.path,True) as db:
            db.execute("DELETE FROM pilot_set_items WHERE set_key LIKE 'qa-g5-2026-11-09-%'")
        self.deny(503,client,'exams',{'requestKey':'missing-set','setIndex':1})

    def test_expired_vip_keeps_work_review_and_replay(self):
        client,aid=self.user(vip=True)
        exam=self.exam(client,contentKeys=['qa-fixture-090'])
        self.expiry(aid,'2026-11-13T09:59:59Z')
        self.assertEqual(client.call('exams/'+exam['id'])['exam']['questions'],exam['questions'])
        client.call('exams/'+exam['id']+'/answers',{'position':1,'answer':'92'})
        self.assertEqual(client.call('exams/'+exam['id']+'/submit',{})['exam']['score'],10)
        self.exam(client,replayExamId=int(exam['id']))
        self.deny(403,client,'exams',{'requestKey':'expired-new','contentKeys':['qa-fixture-091']})
        self.exam(client,setIndex=1)

    def test_revision_current_mapping_and_pinned_free_history(self):
        client,_=self.user(vip=True)
        old=self.exam(client,setIndex=1)
        with api.connect(self.path,True) as db:
            qid=db.execute("SELECT question_id FROM pilot_content WHERE content_key='qa-fixture-030'").fetchone()[0]
            db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,"
                "solution_steps_json,hints_json,status,options_json) SELECT question_id,2,difficulty,curriculum_week,?,grading_rule_json,"
                "solution_steps_json,hints_json,'published',options_json FROM question_versions WHERE question_id=? AND revision=1",
                ('[{"type":"text","text":"QA revised presentation"}]',qid))
        latest=self.exam(client,contentKeys=['qa-fixture-030'])
        self.assertEqual(latest['questions'][0]['text'],'QA revised presentation')
        self.assertEqual(self.exam(client,setIndex=1)['questions'],old['questions'])
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),10)

    def test_side_routes_locked_state_filtered_and_no_usage_xp_change(self):
        client,_=self.user()
        xp=self.count('SELECT sum(xp) FROM student_companions')
        for path,body in (('bot/start',{'requestKey':'abcdefgh'}),('arena',{'action':'quick'}),
                          ('arena',{'action':'state','token':'fake'}),('materials',None),
                          ('lessons/g5-decimal/open',{})):
            self.deny(403,client,path,body)
        state=client.call('state')
        self.assertEqual(state['lessons'],[])
        self.assertEqual(state['state']['battles'],{})
        self.assertEqual(self.count('SELECT count(*) FROM daily_usage'),0)
        self.assertEqual(self.count('SELECT sum(xp) FROM student_companions'),xp)
        self.assertEqual(self.count('SELECT count(*) FROM payment_orders'),0)

    def test_legacy_vip_and_other_grade_excluded(self):
        client,aid=self.user(vip=True)
        with api.connect(self.path,True) as db:
            db.execute("INSERT INTO pilot_cohorts VALUES (?,'legacy')",(aid,))
        self.assertGreater(len(client.call('state')['lessons']),0)
        self.assertEqual(len(self.exam(client,count=3,topic='decimal')['questions']),3)
        other,_=self.user(grade=4)
        lessons=other.call('state')['lessons']
        self.assertGreater(len(lessons),0)
        self.assertEqual(len(self.exam(other,count=3,topic=lessons[0]['topic'])['questions']),3)

    def test_svip_retains_legacy_paths(self):
        client,aid=self.user()
        with api.connect(self.path,True) as db:
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal','2026-01-01T00:00:00Z')",(aid,))
        self.assertEqual(client.call('state')['account']['membership'],'SVip')
        self.assertGreater(len(client.call('state')['lessons']),0)
        self.assertIn('text',client.call('materials'))
        self.assertEqual(client.call('bot/start',{'requestKey':'svip-bot-123'})['status'],'started')

    def test_csrf_origin_and_session_do_not_change_quota(self):
        client,_=self.user(vip=True)
        csrf=client.csrf
        client.csrf='invalid'
        self.deny(403,client,'exams',{'requestKey':'bad-csrf-123','setIndex':1})
        client.csrf=csrf
        client.headers['Origin']='http://bad.example'
        self.deny(403,client,'exams',{'requestKey':'bad-origin-123','setIndex':1})
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),0)

    def test_free_then_upgrade_does_not_charge_old_keys(self):
        client,aid=self.user()
        self.exam(client,setIndex=1)
        self.expiry(aid,'2027-01-01T00:00:00Z')
        self.exam(client,contentKeys=['qa-fixture-030','qa-fixture-090'])
        self.assertEqual(client.call('pilot/sets')['newUsed'],1)

    def test_unknown_key_duplicates_and_unpublished_are_atomic(self):
        client,_=self.user(vip=True)
        self.deny(404,client,'exams',{'requestKey':'unknown-123','contentKeys':['qa-fixture-090','private-real-key']})
        self.deny(400,client,'exams',{'requestKey':'duplicate-123','contentKeys':['qa-fixture-090','qa-fixture-090']})
        with api.connect(self.path,True) as db:
            db.execute("UPDATE question_versions SET status='retired' WHERE question_id=(SELECT question_id FROM pilot_content WHERE content_key='qa-fixture-090')")
        self.deny(404,client,'exams',{'requestKey':'retired-123','contentKeys':['qa-fixture-090']})
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),0)
        self.assertEqual(self.count('SELECT count(*) FROM pilot_requests'),0)

    def test_flag_off_rollback_preserves_attempts_and_grants(self):
        client,_=self.user(vip=True)
        exam=self.exam(client,setIndex=1)
        before=self.count('SELECT count(*) FROM pilot_grants')
        self.server.free_vip_pilot=None
        self.assertGreater(len(client.call('state')['lessons']),0)
        self.assertEqual(client.call('exams/'+exam['id'])['exam']['questions'],exam['questions'])
        self.exam(client,count=3,topic='decimal')
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),before)

    def test_missing_marker_and_existing_db_refused(self):
        with self.assertRaises(FileExistsError):
            initialize_qa(self.path)
        client,_=self.user()
        with api.connect(self.path,True) as db:
            db.execute('DROP TABLE pilot_environment')
        self.deny(503,client,'pilot/sets')

    def test_private_fixture_absent_from_public_allowlist(self):
        from backend.assets import public_assets, FRONTEND
        assets=public_assets()
        for name,relative in assets.items():
            self.assertNotIn('free_vip',name)
            self.assertNotIn('learning-catalog',name)
            if Path(relative).suffix in ('.js','.json','.html','.txt'):
                body=(FRONTEND/relative).read_text(encoding='utf-8')
                self.assertNotIn('qa-fixture-',body)
                self.assertNotIn('QA GIẢ #',body)

    def test_flag_off_does_not_import_optional_qa_module(self):
        import builtins
        original=builtins.__import__
        def no_pilot(name,*args,**kwargs):
            if 'free_vip_pilot' in name:
                raise ImportError('QA module deliberately absent from ordinary runtime bundle')
            return original(name,*args,**kwargs)
        self.server.free_vip_pilot=None
        with patch('builtins.__import__',side_effect=no_pilot):
            client,_=self.user()
            self.assertGreater(len(client.call('state')['lessons']),0)
            self.assertEqual(len(self.exam(client,count=3,topic='decimal')['questions']),3)

    def test_media_and_invalid_set_mapping_fail_closed(self):
        client,_=self.user()
        with api.connect(self.path,True) as db:
            item=db.execute("SELECT set_key,position,version_id FROM pilot_set_items WHERE content_key='qa-fixture-030'").fetchone()
            asset=db.execute("INSERT INTO media_assets(storage_key,url,mime_type,width,height,byte_size,alt_text) "
                "VALUES ('qa-private','/qa-private.png','image/png',10,10,10,'QA')").lastrowid
            db.execute('INSERT INTO question_assets VALUES (?,?)',(item['version_id'],asset))
        self.deny(503,client,'exams',{'requestKey':'media-block-123','setIndex':1})
        with api.connect(self.path,True) as db:
            db.execute('DELETE FROM question_assets WHERE asset_id=?',(asset,))
            other=db.execute('SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=4 LIMIT 1').fetchone()[0]
            db.execute('UPDATE pilot_set_items SET version_id=? WHERE set_key=? AND position=?',
                       (other,item['set_key'],item['position']))
        self.deny(503,client,'exams',{'requestKey':'mapping-block-123','setIndex':1})
        self.assertEqual(self.count('SELECT count(*) FROM pilot_grants'),0)


if __name__ == '__main__':
    unittest.main()
