import json,secrets,tempfile,unittest
from pathlib import Path
from backend import platform_api as api
from backend.database import initialize
from backend.group_game_bots import BotGroupGames
from backend.group_games_qa import synthetic_source
from backend.arena import Arena
from types import SimpleNamespace
from test_arena_penalties import Client

CREDENTIAL=api.password_hash('bot-fixture-only')
class CorrectPlans:
    def randrange(self,a,b):return a+1234
    def random(self):return 0.25
class MixedPlans:
    def __init__(self):self.n=0
    def randrange(self,a,b):return a+(self.n*4000)%18000
    def random(self):
        self.n+=1;return 0.25 if self.n%2 else 0.75
class GroupBotTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).resolve().parents[1]/'work'/'group-bot-tests';folder.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=folder);self.path=Path(self.tmp.name)/'synthetic.sqlite3'
        initialize(self.path);api.initialize_catalog(self.path);self.now=100_000
        self.engine=BotGroupGames(synthetic_source(),qa_only=True,policy_approved=True,clock=lambda:self.now,rng=CorrectPlans())
        client=Client(SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena()))
        with api.connect(self.path,True) as db:
            self.session=api.register(client,db,{'login':'bot-unit-'+secrets.token_hex(8),'name':'Mầm Xanh','birthYear':api.academic()[0]-10,'password':'bot-fixture-only'},CREDENTIAL)
    def tearDown(self):self.tmp.cleanup()
    def create(self,**extra):
        with api.connect(self.path,True) as db:return self.engine.enter(db,self.session,{'mode':'capture_flag','playMode':'bot','requestKey':'bot-create-key',**extra},'create',5)
    def room(self,rid):
        with api.connect(self.path) as db:return self.engine._load(db,rid)
    def tick(self,rid):
        with api.connect(self.path,True) as db:
            room=self.engine._load(db,rid);self.engine._tick(db,room,self.now);return self.engine.view(room,self.session['student_id'],self.now)
    def answer(self,rid,round,answer,key=None):
        with api.connect(self.path,True) as db:return self.engine.mutate(db,self.session,rid,{'round':round,'answer':answer,'requestKey':key or 'bot-answer-'+secrets.token_hex(8)},'answer')
    def test_explicit_four_bots_autostart_without_accounts_or_grading_leak(self):
        room=self.create();self.assertEqual(room['status'],'playing');self.assertFalse(room['ranked'])
        self.assertEqual(sum(p['isBot'] for p in room['players']),4);self.assertEqual(len(room['players']),5)
        self.assertEqual(sum(p['mine'] for p in room['players']),1)
        self.assertFalse({'answer','gradingRule','choiceRationales','botAt'}&set(room['question']))
        self.assertTrue(all('botAt' not in p for p in room['players']))
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
        with self.assertRaises(api.APIError):self.create(playMode='forged')
    def test_persisted_schedule_last_thirty_percent_and_reconnect(self):
        room=self.create();raw=self.room(room['id']);schedule=[p['botAt'] for p in raw['players'] if p.get('isBot')]
        self.assertTrue(all(42_000<=at-raw['startedAt']<60_000 for at in schedule))
        self.now=raw['startedAt']+41_999;state=self.tick(room['id']);self.assertFalse(any(p['answered'] for p in state['players']))
        self.engine=BotGroupGames(synthetic_source(),qa_only=True,policy_approved=True,clock=lambda:self.now,rng=CorrectPlans())
        self.assertEqual(schedule,[p['botAt'] for p in self.room(room['id'])['players'] if p.get('isBot')])
        self.now=max(schedule);state=self.tick(room['id']);self.assertEqual(sum(p['answered'] for p in state['players']),4)
        self.assertEqual(state['status'],'playing');self.assertFalse(next(p for p in state['players'] if p['mine'])['answered'])
    def test_wrong_accepted_materializes_persisted_plans_and_three_second_boundary(self):
        room=self.create();self.now+=1000
        state=self.answer(room['id'],1,'not-the-correct-answer','wrong-idempotent')
        self.assertEqual(state['status'],'intermission');self.assertTrue(all(p['answered'] for p in state['players']))
        self.assertEqual([p['correct'] for p in state['players']],[0,1,1,1,1]);self.assertEqual(state['nextAt'],self.now+3000)
        self.assertEqual(state['lastRoundReason'],'human_answer_planned_bots')
        self.assertEqual(self.answer(room['id'],1,'not-the-correct-answer','wrong-idempotent')['round'],1)
        with self.assertRaises(api.APIError):self.answer(room['id'],1,'wrong-again')
        self.now+=2999;self.assertEqual(self.tick(room['id'])['round'],1)
        self.now+=1;self.assertEqual(self.tick(room['id'])['round'],2)
        replay=self.answer(room['id'],1,'not-the-correct-answer','wrong-idempotent')
        self.assertEqual(replay['round'],2);self.assertFalse(any(p['answered'] for p in replay['players']))
    def test_invalid_empty_does_not_trigger_or_consume(self):
        room=self.create()
        for value in ('',None,[],False,' '):
            with self.assertRaises(api.APIError):self.answer(room['id'],1,value)
        self.assertTrue(all(not p['answered'] and p['correct']==0 for p in self.room(room['id'])['players']))
    def test_wrong_five_rounds_finish_exactly_once_no_ledger_xp_or_fake_accounts(self):
        room=self.create()
        for n in range(1,6):
            state=self.answer(room['id'],n,'incorrect',f'wrong-round-{n}')
            if n<5:self.now=state['nextAt'];self.tick(room['id'])
        self.assertEqual(state['status'],'finished');self.assertLess(state['winnerId'],0)
        self.assertTrue(all(r['points']==r['xpAward']==0 for r in state['rankings']))
        for _ in range(3):self.tick(room['id']);self.answer(room['id'],5,'incorrect','wrong-round-5')
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT xp FROM student_companions').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
    def test_human_win_zero_xp_and_leave_cancel(self):
        room=self.create()
        for n in range(1,6):
            raw=self.room(room['id']);state=self.answer(room['id'],n,raw['questions'][n-1]['answer'])
            if n<5:
                self.now=state['nextAt'];self.tick(room['id'])
        self.assertEqual(state['winnerId'],self.session['student_id']);self.assertFalse(state['ranked'])
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)
        second=self.create(requestKey='bot-create-second')
        with api.connect(self.path,True) as db:
            ended=self.engine.mutate(db,self.session,second['id'],{'requestKey':'leave-practice'},'leave')
            replay=self.engine.mutate(db,self.session,second['id'],{'requestKey':'leave-practice'},'leave')
        self.assertEqual(ended['endReason'],'cancelled');self.assertEqual(replay['status'],'finished')
    def test_human_mode_unchanged_waits_five_real_members(self):
        room=self.create(playMode='human');self.assertEqual(room['status'],'waiting');self.assertEqual(len(room['players']),1)
        self.assertFalse(room['players'][0]['isBot']);self.assertTrue(room['ranked'])

    def test_crossmode_request_keys_join_and_identity_spoofs_cannot_add_humans(self):
        room=self.create()
        for play_mode in ('human','bot'):
            with self.assertRaises(api.APIError):
                with api.connect(self.path,True) as db:
                    self.engine.enter(db,{'student_id':999,'full_name':'Other'},
                        {'code':room['code'],'requestKey':'cross-mode-join','playMode':play_mode},'join',5)
        with self.assertRaises(api.APIError) as caught:self.create(playMode='human')
        self.assertEqual(caught.exception.status,409)
        self.assertEqual(len(self.room(room['id'])['players']),5)
        replay=self.create();self.assertEqual(replay['id'],room['id'])
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM students').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)

    def test_late_poll_clock_payload_cannot_reschedule_or_repeat_bot_answers(self):
        room=self.create();raw=self.room(room['id']);self.now=raw['deadline']+3000
        next_round=self.tick(room['id']);self.assertEqual(next_round['round'],2)
        self.assertEqual([p['correct'] for p in next_round['players']],[0,1,1,1,1])
        self.assertTrue(all(not p['answered'] for p in next_round['players']))
        again=self.tick(room['id']);self.assertEqual(again,next_round)
        with api.connect(self.path,True) as db:
            current=self.engine.mutate(db,self.session,room['id'],{'round':2,'answer':'wrong','requestKey':'forged-clock-key','serverTime':10**16,'botAt':0,'isBot':True},'answer')
        self.assertEqual(current['round'],2);self.assertEqual(current['serverTime'],self.now)
        self.assertEqual([p['correct'] for p in current['players']],[0,2,2,2,2])

    def test_independent_mixed_plans_correct_human_also_settles_early(self):
        self.engine.rng=MixedPlans();room=self.create();raw=self.room(room['id'])
        expected=[p['botPlannedCorrect'] for p in raw['players'] if p.get('isBot')]
        planned=[p['botAt'] for p in raw['players'] if p.get('isBot')]
        self.assertEqual(expected,[True,False,True,False]);self.now+=500
        answer=raw['questions'][0]['answer'];state=self.answer(room['id'],1,answer,'correct-early-key')
        self.assertEqual(state['status'],'intermission');self.assertEqual(state['nextAt'],self.now+3000)
        stored=self.room(room['id']);bots=[p for p in stored['players'] if p.get('isBot')]
        self.assertEqual([p['answerCorrect'] for p in bots],expected)
        self.assertEqual([p['totalTimeMs'] for p in bots],[at-raw['startedAt'] for at in planned])
        self.assertEqual([p['correct'] for p in bots],[1,0,1,0])
        self.answer(room['id'],1,answer,'correct-early-key');self.tick(room['id'])
        self.assertEqual(bots,[p for p in self.room(room['id'])['players'] if p.get('isBot')])

if __name__=='__main__':unittest.main()
