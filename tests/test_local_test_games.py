"""Native opt-in is separate from the QA marker/port bypass and default-off."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from http.server import HTTPServer
import json,secrets,tempfile,unittest
from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.content_retirement import activate
from backend.local_test_games import NativeLocalTestGames
from test_arena_penalties import Client

CREDENTIAL=api.password_hash('native-local-test-only')
class NativeLocalTestGamesTests(unittest.TestCase):
    def setUp(self):
        folder=Path('work/native-local-test-unit');folder.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=folder);self.path=Path(self.tmp.name)/'fresh-main.sqlite3'
        initialize(self.path);api.initialize_catalog(self.path)
        with api.connect(self.path,True) as db:activate(db)
        self.server=object.__new__(HTTPServer)
        self.server.database_path=self.path;self.server.review_upgrades=False;self.server.arena=Arena()
        self.server.server_address=('0.0.0.0',8000);self.server.native_python_backend=True
        self.server.local_test_games=NativeLocalTestGames({8765,19033})
    def tearDown(self):self.tmp.cleanup()
    def actor(self,grade=5):
        client=Client(self.server);client.headers.update(Host='localhost:8765',Origin='http://localhost:8765')
        with api.connect(self.path,True) as db:
            session=api.register(client,db,{'login':'native-local-'+secrets.token_hex(6),'name':'Mầm Xanh','birthYear':api.academic()[0]-grade-5,'password':'native-local-test-only'},CREDENTIAL)
        client.headers['Cookie']=client.api_headers.pop('Set-Cookie').split(';')[0];client.csrf=session['csrf_token'];client.sid=session['student_id']
        return client
    def test_native_8765_docker_bind_no_qa_marker_and_test_labels(self):
        client=self.actor();session=client.call('session?view=identity')
        self.assertTrue(session['arenaQuestionSource']['localTest']);self.assertFalse(session['arenaQuestionSource']['qaOnly'])
        self.assertTrue(session['arenaBotQuestionSource']['localTest'])
        created=client.call('arena',{'action':'create','scope':'all'})
        self.assertTrue(created['code'])
        with api.connect(self.path) as db:
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='group_games_qa_owner'").fetchone())
            self.assertIsNone(api.qa_arena_source(client,db)) # original QA gate still rejects8765
            self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0],0)
    def test_native_groups_ready_pending_commercial_policy_no_seed(self):
        client=self.actor();result=client.call('group-games/catalogue')
        self.assertTrue(result['ready']);self.assertEqual(result['policyStatus'],'pending-commercial')
        self.assertEqual(result['sourceStatus'],'local-test')
        room=client.call('group-games/rooms',{'mode':'capture_flag','requestKey':'native-create-001'})['room']
        self.assertEqual(room['status'],'waiting');self.assertEqual(len(room['players']),1)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)
    def test_flag_absent_cannot_be_enabled_by_body(self):
        client=self.actor();del self.server.local_test_games
        self.assertNotIn('arenaQuestionSource',client.call('session'))
        self.assertFalse(client.call('group-games/catalogue')['ready'])
        with self.assertRaises(api.APIError) as caught:client.call('arena',{'action':'create','scope':'all','MAM_TOAN_LOCAL_TEST_GAMES':'1','localTest':True})
        self.assertEqual(caught.exception.status,503)
        with self.assertRaises(api.APIError):client.call('group-games/rooms',{'mode':'animal_race','requestKey':'body-cannot-enable','localTest':True})
    def test_lan_and_forwarded_host_do_not_enable_source(self):
        client=self.actor();client.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        client.headers['X-Forwarded-Host']='localhost:8765'
        self.assertNotIn('arenaQuestionSource',client.call('session'))
        cat=client.call('group-games/catalogue');self.assertFalse(cat['ready']);self.assertEqual(cat['sourceStatus'],'localhost-required')
        for path,body in [('arena',{'action':'create','scope':'all'}),('bot/start',{'scope':'all','requestKey':'wrong-host-bot'}),('group-games/rooms',{'mode':'animal_race','requestKey':'wrong-host-group'})]:
            with self.assertRaises(api.APIError) as caught:client.call(path,body)
            self.assertEqual(caught.exception.status,403 if path.startswith('group-games/') else 503)
    def test_cloud_server_and_public_origin_fail_closed(self):
        client=self.actor();native=self.server.local_test_games
        cloud=SimpleNamespace(native_python_backend=True,local_test_games=native,server_address=('127.0.0.1',8765))
        self.assertFalse(native.allowed(SimpleNamespace(server=cloud,headers={'Host':'localhost:8765'})))
        with patch.object(api,'public_origin',return_value='https://5bmath.vn'):
            self.assertFalse(native.allowed(client))
    def test_wrong_port_and_private_instance_fail_closed(self):
        client=self.actor()
        for host in ['localhost:19031','localhost:80','localhost.evil:8765','5bmath.vn:8765','localhost:8765/path']:
            client.headers['Host']=host;self.assertFalse(self.server.local_test_games.allowed(client))
        client.headers['Host']='127.0.0.1:19033';self.assertTrue(self.server.local_test_games.allowed(client))
        self.server.native_python_backend=False;self.assertFalse(self.server.local_test_games.allowed(client))
    def test_local_bot_disjoint_client_demo_zero_xp_existing_limit(self):
        client=self.actor()
        with patch('backend.question_bank.arena_questions',side_effect=AssertionError('No paid/legacy bank')):
            bot=client.call('bot/start',{'scope':'all','requestKey':'native-bot-one'})
        self.assertTrue(bot['questionSource']['localTest']);self.assertFalse(bot['ranked']);self.assertEqual(bot['xpAward'],0)
        self.assertTrue(all(q['id'].startswith('ARENA-BOT-QA-') for q in bot['questions']))
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?',(client.sid,)).fetchone()[0],0)

    def test_lan_grade4_legacy_provider_and_source_queues_preserved(self):
        from copy import deepcopy
        local=self.actor(4);lan=self.actor(4)
        created=local.call('arena',{'action':'quick','scope':'all','public':True})
        lan.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        legacy=deepcopy(self.server.local_test_games.arena.questions(4))
        for q in legacy:q['id']='LEGACY-MOCK-'+q['id'];q.pop('purpose',None)
        with patch('backend.question_bank.arena_questions',return_value=legacy) as old:
            other=lan.call('arena',{'action':'quick','scope':'all','sourcePool':'local-test'})
            self.assertEqual(old.call_count,1)
        self.assertNotEqual(created['code'],other['code'])
        self.assertEqual(self.server.arena.rooms[created['code']]['sourcePool'],'local-test')
        self.assertEqual(self.server.arena.rooms[other['code']]['sourcePool'],'legacy')
        local_rooms=local.call('arena',{'action':'list'})['rooms'];lan_rooms=lan.call('arena',{'action':'list'})['rooms']
        self.assertFalse(any(r['code']==other['code'] for r in local_rooms))
        self.assertFalse(any(r['code']==created['code'] for r in lan_rooms))
        lan.call('game-claim',{'action':'leave','claimId':other['gameClaim']['claimId']})
        with patch('backend.question_bank.arena_questions',return_value=legacy) as old:
            bot=lan.call('bot/start',{'scope':'all','requestKey':'lan-old-bot-bank'})
            self.assertEqual(old.call_count,1);self.assertTrue(bot['questions'][0]['id'].startswith('LEGACY-MOCK-'))
    def test_local_room_cannot_be_joined_or_read_from_lan(self):
        local=self.actor(4);other=self.actor(4)
        created=local.call('arena',{'action':'create','scope':'all','public':True})
        other.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        with self.assertRaises(api.APIError) as caught:other.call('arena',{'action':'join','scope':'all','code':created['code'],'sourcePool':'local-test'})
        self.assertEqual(caught.exception.status,403)
        local.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        with self.assertRaises(api.APIError) as caught:local.call('arena',{'action':'state',**{k:created[k] for k in ('code','token')},'sourcePool':'local-test'})
        self.assertEqual(caught.exception.status,403)

    def test_wrong_host_accept_and_answer_rejected_before_quota_or_presence(self):
        host=self.actor(4);friend=self.actor(4)
        created=host.call('arena',{'action':'create','scope':'all'})
        joined=friend.call('arena',{'action':'join','scope':'all','code':created['code']})
        room=self.server.arena.rooms[created['code']]
        before={t:p['seen'] for t,p in room['players'].items()}
        host.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        from backend.learning_update import usage
        for action in ['accept','answer','next','emote','state']:
            with self.assertRaises(api.APIError) as caught:
                host.call('arena',{'action':action,'code':created['code'],'token':created['token'],'index':0,'answer':'1','sourcePool':'local-test'})
            self.assertEqual(caught.exception.status,403)
        self.assertEqual(room['status'],'challenged')
        self.assertEqual({t:p['seen'] for t,p in room['players'].items()},before)
        with api.connect(self.path) as db:
            session=api.read_session(host,db)
            self.assertEqual(usage(db,session)['human']['used'],0)
        self.assertEqual(len(room['players']),2)

    def test_concurrent_quick_match_never_crosses_source_pool(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        gate=Barrier(4);arena=Arena()
        questions=self.server.local_test_games.arena.questions(4)
        def enter(i):
            pool='local-test' if i%2 else 'legacy';gate.wait()
            result=arena.handle({'action':'quick','name':'Mầm Xanh','grade':4,'scope':'all','accountId':i,'sourcePool':pool},lambda *args:questions)
            return pool,result['code']
        with ThreadPoolExecutor(max_workers=4) as executor:rows=list(executor.map(enter,range(4)))
        by_pool={pool:{code for p,code in rows if p==pool} for pool in ('legacy','local-test')}
        self.assertEqual(len(arena.rooms),2)
        self.assertEqual(len(by_pool['legacy']),1);self.assertEqual(len(by_pool['local-test']),1)
        self.assertTrue(by_pool['legacy'].isdisjoint(by_pool['local-test']))
        self.assertTrue(all(len(room['players'])==2 for room in arena.rooms.values()))

if __name__=='__main__':unittest.main()
