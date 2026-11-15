"""QA source injection only; normal engine/quota/damage/prod bank unchanged."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,secrets,tempfile,time,unittest
from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize
from backend.arena_qa_source import ArenaQAQuestionSource,ArenaBotQAQuestionSource
from backend.content_retirement import activate
from backend.learning_update import usage
from test_arena_penalties import Client

CREDENTIAL=api.password_hash('synthetic-duel-source-only')

class ArenaQAQuestionSourceTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).resolve().parents[1]/'work/test-runs';folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.path=Path(self.temp.name)/'new-fake.sqlite3'
        initialize(self.path);api.initialize_catalog(self.path)
        with api.connect(self.path,True) as db:
            db.execute('CREATE TABLE group_games_qa_owner(label TEXT NOT NULL)')
            db.execute("INSERT INTO group_games_qa_owner VALUES('group-games-qa-new-synthetic-only')")
            activate(db)
        self.server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),
            qa_arena_enabled=True,qa_arena_source=ArenaQAQuestionSource(),qa_arena_bot_source=ArenaBotQAQuestionSource(),
            server_address=('127.0.0.1',19032))
        self.clock=time.time();self.timer=patch('backend.arena.time.time',side_effect=lambda:self.clock);self.timer.start()
        self.addCleanup(self.timer.stop)
    def tearDown(self):self.temp.cleanup()
    def actor(self,grade=5):
        client=Client(self.server);client.headers.update(Host='127.0.0.1:19032',Origin='http://127.0.0.1:19032')
        with api.connect(self.path,True) as db:
            session=api.register(client,db,{'login':'qa-source-'+secrets.token_hex(6),'name':'Mầm Xanh','birthYear':api.academic()[0]-grade-5,'password':'synthetic-duel-source-only'},CREDENTIAL)
        client.headers['Cookie']=client.api_headers.pop('Set-Cookie').split(';')[0];client.csrf=session['csrf_token'];client.sid=session['student_id']
        return client
    def room(self,grade=5):
        a,b=self.actor(grade),self.actor(grade)
        created=a.call('arena',{'action':'create','scope':'all'})
        joined=b.call('arena',{'action':'join','scope':'all','code':created['code']})
        a.call('arena',{'action':'accept','code':created['code'],'token':created['token']})
        self.clock+=3.01
        state=a.call('arena',{'action':'state','code':created['code'],'token':created['token']})
        return a,b,created,joined,state
    def test_all_grades_twenty_questions_and_distinct_bot_banks(self):
        source,bot=self.server.qa_arena_source,self.server.qa_arena_bot_source
        for grade in range(1,6):
            p,b=source.questions(grade),bot.questions(grade)
            self.assertEqual(len(p),20);self.assertEqual(len(b),20)
            self.assertEqual({q['responseMode'] for q in p},{'typed','choice'})
            self.assertTrue(all(q['purpose']=='arena-duel-QA' and q['revision']==1 for q in p))
            self.assertTrue(all(q['purpose']=='arena-bot-qa' for q in b))
            self.assertFalse({q['id'] for q in p}&{q['id'] for q in b})
            self.assertFalse({q['text'] for q in p}&{q['text'] for q in b})
            self.assertFalse({q['answer'] for q in p}&{q['answer'] for q in b})
        with self.assertRaises(ValueError):source.questions(True)
    def test_qa_no_bank_borrow_metadata_and_live_projection(self):
        with patch('backend.question_bank.arena_questions',side_effect=AssertionError('No legacy bank read')):
            a,b,created,joined,state=self.room()
        self.assertEqual(state['status'],'playing')
        self.assertIn('ARENA-DUEL-QA',state['battle']['questions'][state['battle']['index']]['id'])
        serialized=json.dumps(state['battle']['questions'],ensure_ascii=False)
        for key in ['"answer":','"gradingRule":','"steps":','"choiceRationales":']:
            self.assertNotIn(key,serialized)
        meta=a.call('session')['arenaQuestionSource'];self.assertTrue(meta['qaOnly']);self.assertEqual(meta['questionCount'],20)
        self.assertEqual(a.call('session?view=identity')['arenaQuestionSource']['purpose'],'arena-duel-QA')
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0],0)
    def test_gate_off_wrong_port_lan_missing_marker_and_body_cannot_enable(self):
        actor=self.actor()
        cases=[('qa_arena_enabled',False),('server_address',('127.0.0.1',8765)),('server_address',('0.0.0.0',19032))]
        for name,value in cases:
            before=getattr(self.server,name);setattr(self.server,name,value)
            with self.assertRaises(api.APIError) as caught:actor.call('arena',{'action':'create','scope':'all','qa_arena_enabled':True,'purpose':'arena-duel-QA'})
            self.assertEqual(caught.exception.status,503);setattr(self.server,name,before)
        with api.connect(self.path,True) as db:db.execute('DELETE FROM group_games_qa_owner')
        with self.assertRaises(api.APIError) as caught:actor.call('arena',{'action':'create','scope':'all'})
        self.assertEqual(caught.exception.status,503)
        self.assertNotIn('arenaQuestionSource',actor.call('session'))
    def test_normal_production_off_path_uses_original_factory(self):
        actor=self.actor(4);self.server.qa_arena_enabled=False
        expected=self.server.qa_arena_source.questions(4)
        with patch('backend.question_bank.arena_questions',return_value=expected) as original:
            actor.call('arena',{'action':'create','scope':'all'})
            self.assertEqual(original.call_count,1)
        self.assertNotIn('arenaQuestionSource',actor.call('session'))
    def test_pvp_pins_single_submit_and_three_second_damage_unchanged(self):
        a,b,created,joined,state=self.room()
        room=self.server.arena.rooms[created['code']];question=room['questions'][0];answer=question['answer']
        original=next(q for q in self.server.qa_arena_source._questions[5] if q['id']==question['id'])
        original['answer']='not-the-room-answer';original['gradingRule']['answer']='not-the-room-answer'
        before=a.call('arena',{'action':'answer','code':created['code'],'token':created['token'],'index':0,'answer':answer})
        self.assertEqual(room['players'][created['token']]['correct'],1)
        self.assertEqual(room['defenseUntil'],self.clock+3)
        a.call('arena',{'action':'answer','code':created['code'],'token':created['token'],'index':0,'answer':answer})
        self.assertEqual(room['players'][created['token']]['correct'],1)
        self.clock+=1
        b.call('arena',{'action':'answer','code':created['code'],'token':joined['token'],'index':0,'answer':answer})
        self.assertEqual(room['damage'],10);self.assertEqual(room['players'][joined['token']]['hp'],90)
    def test_bot_only_demo_bank_no_xp_and_existing_five_turn_limit(self):
        actor=self.actor()
        for i in range(5):
            with patch('backend.question_bank.arena_questions',side_effect=AssertionError('No legacy bot bank read')):
                result=actor.call('bot/start',{'scope':'all','requestKey':f'bot-qa-request-{i}'})
            self.assertEqual(len(result['questions']),20);self.assertEqual(result['gradingMode'],'client-demo')
            self.assertEqual(result['xpAward'],0);self.assertFalse(result['ranked'])
            self.assertTrue(all(q['id'].startswith('ARENA-BOT-QA-') and q['purpose']=='arena-bot-qa' for q in result['questions']))
            # Each practice finishes before the next admission under one-room rules.
            actor.call('game-claim',{'action':'release','claimId':result['gameClaim']['claimId'],'reason':'finish'})
        with self.assertRaises(api.APIError) as caught:actor.call('bot/start',{'scope':'all','requestKey':'sixth-bot-qa-request'})
        self.assertEqual(caught.exception.status,429)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?',(actor.sid,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)
        self.assertTrue(actor.call('session')['arenaBotQuestionSource']['qaOnly'])

    def test_complete_qa_ko_pins_reviews_and_settles_original_xp_once(self):
        from copy import deepcopy
        bank=sorted(self.server.qa_arena_source.questions(5),key=lambda q:q['id'])
        self.server.qa_arena_source.questions=lambda grade,difficulty=0,scope='all':deepcopy(bank)
        a,b,created,joined,state=self.room()
        # Change the injected author's raw fixture after room creation. The
        # room's detached snapshot must remain answerable with original values.
        original_answer=bank[0]['answer'];bank[0]['answer']='changed-after-pin';bank[0]['gradingRule']['answer']='changed-after-pin'
        modes=set()
        for index in range(5):
            raw=self.server.arena.rooms[created['code']]['questions'][index]
            modes.add(raw['responseMode'])
            current=state['battle']['questions'][index]
            for secret in ('answer','steps','gradingRule','choiceRationales'):self.assertNotIn(secret,current)
            answer=original_answer if index==0 else raw['answer']
            a.call('arena',{'action':'answer','code':created['code'],'token':created['token'],'index':index,'answer':answer})
            self.clock+=3.001
            state=a.call('arena',{'action':'state','code':created['code'],'token':created['token']})
            self.assertEqual(self.server.arena.rooms[created['code']]['players'][joined['token']]['hp'],100-(index+1)*20)
            self.clock+=3.001
            state=a.call('arena',{'action':'state','code':created['code'],'token':created['token']})
        self.assertEqual(modes,{'typed','choice'})
        self.assertEqual(state['status'],'finished');self.assertEqual(state['result']['outcome'],'win');self.assertEqual(state['result']['points'],2)
        self.assertTrue(all(q['id'].startswith('ARENA-DUEL-QA-') for q in state['result']['review']))
        self.assertEqual(state['result']['review'][0]['answer'],original_answer)
        for _ in range(3):
            again=a.call('arena',{'action':'state','code':created['code'],'token':created['token']})
            self.assertEqual(again['result'],state['result'])
        b.call('arena',{'action':'state','code':created['code'],'token':joined['token']})
        with api.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM duels WHERE status='completed'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM duel_players').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM xp_events').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?',(a.sid,)).fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0],0)
            self.assertEqual(usage(db,api.read_session(a,db))['human']['used'],1)

if __name__=='__main__':unittest.main()
