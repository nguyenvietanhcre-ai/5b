"""No-human-submit schedule diagnostics through the real authenticated API."""
import unittest,json
import test_local_test_games as native
from backend import platform_api as api
class MixedPlans:
    def __init__(self):self.calls=0
    def randrange(self,a,b):return 42000+(self.calls%4)*4000
    def random(self):self.calls+=1;return .1 if self.calls%2 else .9
class IdleBotAPITests(unittest.TestCase):
    setUp=native.NativeLocalTestGamesTests.setUp
    tearDown=native.NativeLocalTestGamesTests.tearDown
    actor=native.NativeLocalTestGamesTests.actor
    def setup_room(self,mode):
        self.now=1000000;self.engine=self.server.local_test_games.group_games;self.engine.clock=lambda:self.now;self.engine.rng=MixedPlans();client=self.actor();room=client.call('group-games/rooms',{'mode':mode,'playMode':'bot','requestKey':'idle-create-'+mode})['room'];return client,room
    def get(self,c,room):return c.call('group-games/rooms/'+room['id'])['room']
    def raw(self,room):
        with api.connect(self.path) as db:return self.engine._load(db,room['id'])
    def test_each_bot_due_without_human_submit_both_modes(self):
        for mode in ('capture_flag','animal_race'):
            c,room=self.setup_room(mode);initial=self.raw(room);planned=[(p['botAt'],p['botPlannedCorrect']) for p in initial['players'] if p.get('isBot')]
            for n,(at,correct) in enumerate(planned):
                self.now=at-1;before=self.get(c,room);self.assertEqual(sum(p['answered'] for p in before['players']),n)
                for bot in before['players'][1:]:
                    self.assertFalse({'botAt','botPlannedCorrect','answer'}&set(bot))
                    if not bot['answered']:self.assertNotIn('answerCorrect',bot)
                self.now=at;view=self.get(c,room);self.assertEqual(sum(p['answered'] for p in view['players']),n+1);self.assertEqual(view['players'][n+1]['correct'],int(correct));self.assertIs(view['players'][n+1]['answerCorrect'],correct);self.assertFalse(view['players'][0]['answered'])
                repeated=self.get(c,room);self.assertEqual(repeated,view)
            self.assertEqual(planned,[(p['botAt'],p['botPlannedCorrect']) for p in self.raw(room)['players'] if p.get('isBot')])
    def test_first_poll_at60_settles_persisted_plans_and_human_timeout(self):
        for mode in ('capture_flag','animal_race'):
            c,room=self.setup_room(mode);initial=self.raw(room);self.now=initial['deadline'];view=self.get(c,room)
            self.assertEqual(view['status'],'intermission');self.assertEqual([p['correct'] for p in view['players']],[0,1,0,1,0]);self.assertEqual(view['nextAt'],self.now+3000)
            stored=self.raw(room);self.assertEqual([p['totalTimeMs'] for p in stored['players']],[60000,42000,46000,50000,54000])
            self.assertEqual(self.get(c,room),view)
    def test_late_first_poll63_advances_once_without_losing_bot_results(self):
        for mode in ('capture_flag','animal_race'):
            c,room=self.setup_room(mode);initial=self.raw(room);self.now=initial['deadline']+3000;view=self.get(c,room)
            self.assertEqual(view['round'],2);self.assertEqual(view['status'],'playing');self.assertEqual([p['correct'] for p in view['players']],[0,1,0,1,0]);self.assertFalse(any(p['answered'] for p in view['players']));self.assertEqual(self.get(c,room),view)
            with api.connect(self.path) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM group_game_rewards').fetchone()[0],0);self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?',(c.sid,)).fetchone()[0],0)

    def test_other_human_answer_outcome_stays_private(self):
        clients=[self.actor() for _ in range(5)];self.now=1000000;self.engine=self.server.local_test_games.group_games;self.engine.clock=lambda:self.now
        room=clients[0].call('group-games/rooms',{'mode':'capture_flag','requestKey':'human-create-idle'})['room']
        for n,c in enumerate(clients[1:]):c.call('group-games/join',{'code':room['code'],'requestKey':'human-join-idle-'+str(n)})
        raw=self.raw(room);clients[0].call('group-games/rooms/'+room['id']+'/answer',{'round':1,'answer':raw['questions'][0]['answer'],'requestKey':'human-answer-private'})
        view=self.get(clients[1],room)
        self.assertTrue(view['players'][0]['answered']);self.assertNotIn('answerCorrect',view['players'][0])
