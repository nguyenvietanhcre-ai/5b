import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend import platform_api as api
from backend.database import initialize
from backend.group_games import GroupGames, QuestionSource, leaderboard
from backend.group_games_qa import synthetic_source
SYNTHETIC_CREDENTIAL = api.password_hash('syntheticpassword123')


class GroupGamesTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / 'work/test-runs'
        folder.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=str(folder))
        self.path = Path(self.tmp.name) / 'new-synthetic.sqlite3'
        initialize(self.path); api.initialize_catalog(self.path)
        self.now = 1_000_000
        self.game = GroupGames(synthetic_source(), qa_only=True, policy_approved=True, clock=lambda: self.now)
        self.users = []
        self.cookies = []
        for i in range(7):
            h = SimpleNamespace(server=SimpleNamespace(), headers={}, api_headers={})
            with api.connect(self.path, True) as db:
                s = api.register(h, db, {'login': f'qa-actor-{i}', 'name': 'Mầm Xanh', 'birthYear': api.academic()[0]-10, 'password': 'syntheticpassword123'}, SYNTHETIC_CREDENTIAL)
                self.users.append(dict(s))
                self.cookies.append(h.api_headers['Set-Cookie'].split(';')[0])

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, mode='capture_flag', user=0, key='create-0001'):
        with api.connect(self.path, True) as db:
            return self.game.enter(db, self.users[user], {'mode': mode, 'requestKey': key}, 'create', 5)

    def full(self, mode='capture_flag'):
        room = self.create(mode, key='full-room-'+mode)
        for index in range(1, 5):
            with api.connect(self.path, True) as db:
                room = self.game.enter(db, self.users[index], {'code': room['code'], 'requestKey': f'join-user-{index}'}, 'join', 5)
        return room

    def answer(self, room, index, value=None, key=None):
        with api.connect(self.path, True) as db:
            raw = self.game._load(db, room['id'])
            if value is None:
                value = raw['questions'][raw['round']-1]['answer']
            return self.game.mutate(db, self.users[index], room['id'], {'round': room['round'], 'answer': value, 'requestKey': key or f'answer-round-{room["round"]}-user-{index}'}, 'answer')

    def poll(self, room, user=0):
        with api.connect(self.path, True) as db:
            r = self.game._load(db, room['id']); self.game._member(r, self.users[user]['student_id']); self.game._tick(db, r, self.now)
            return self.game.view(r, self.users[user]['student_id'], self.now)

    def win(self, mode='capture_flag'):
        room = self.full(mode)
        for round_index in range(5):
            self.now += 100
            room = self.answer(room, 0)
            if round_index == 4:
                return room
            for user in range(1, 5):
                self.now += 100
                room = self.answer(room, user, '999')
            self.assertEqual(room['status'], 'intermission')
            self.now += 3000; room = self.poll(room)

    def test_requires_five_distinct_humans_and_room_capacity(self):
        room = self.create()
        self.assertEqual(room['status'], 'waiting')
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError):
                self.game.enter(db, self.users[0], {'code': room['code'], 'requestKey': 'duplicate-user'}, 'join', 5)
        for user in range(1, 5):
            with api.connect(self.path, True) as db:
                room = self.game.enter(db, self.users[user], {'code': room['code'], 'requestKey': f'new-player-{user}'}, 'join', 5)
        self.assertEqual(room['status'], 'playing'); self.assertEqual(len(room['players']), 5)
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError):
                self.game.enter(db, self.users[5], {'code': room['code'], 'requestKey': 'sixth-player'}, 'join', 5)

    def test_question_projection_owner_and_deadline(self):
        room = self.full()
        self.assertNotIn('answer', room['question']); self.assertNotIn('questions', room)
        self.assertNotIn('answerCorrect', room['players'][0])  # finaljoin is user4
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError): self.game._member(self.game._load(db, room['id']), self.users[6]['student_id'])
        self.now = room['deadline']
        with self.assertRaises(api.APIError): self.answer(room, 0)
        room = self.poll(room)
        self.assertEqual(room['status'], 'intermission')
        self.assertTrue(all(p['totalTimeMs'] == 60000 for p in room['players']))
        self.now += 2999; self.assertEqual(self.poll(room)['round'], 1)
        self.now += 1; self.assertEqual(self.poll(room)['round'], 2)

    def test_all_answered_once_and_three_second_transition(self):
        room = self.full()
        self.now += 500; room = self.answer(room, 0)
        room = self.answer(room, 0)  # same request is idempotent
        with self.assertRaises(api.APIError): self.answer(room, 0, key='second-answer-same-round')
        for user in range(1, 5): room = self.answer(room, user, '999')
        self.assertEqual(room['status'], 'intermission')
        self.assertEqual(room['nextAt'], self.now+3000)
        self.assertEqual(room['players'][0]['correct'], 1)

    def test_atomic_rewards_restart_retry_and_independent_boards(self):
        room = self.win('capture_flag')
        self.assertEqual(room['endReason'], 'target_reached')
        self.assertEqual([r['points'] for r in room['rankings']], [5,4,3,2,1])
        self.assertEqual(room['winnerId'], self.users[0]['student_id'])
        self.game = GroupGames(synthetic_source(), qa_only=True, policy_approved=True, clock=lambda: self.now)
        for _ in range(3): self.poll(room)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT SUM(points),COUNT(*) FROM group_game_rewards').fetchone()[0], 15)
            self.assertEqual(db.execute('SELECT SUM(xp) FROM student_companions').fetchone()[0], 15)
            b = leaderboard(db, {'kind':['capture_flag'], 'limit':['1']})
            self.assertEqual(len(b['top3']), 3); self.assertEqual(b['items'][0]['rank'], 4); self.assertTrue(b['hasMore'])
            self.assertEqual(leaderboard(db, {'kind':['animal_race']})['total'], 0)
            self.assertEqual(leaderboard(db, {'kind':['duel']})['total'], 0)

    def test_simultaneous_fifth_answers_settle_one_winner_once(self):
        room = self.full()
        with api.connect(self.path, True) as db:
            raw = self.game._load(db, room['id'])
            for p in raw['players']: p.update(correct=4, steps=4)
            self.game._save(db, raw, self.now)
        barrier = threading.Barrier(5); errors=[]; results=[]
        def answer(user):
            barrier.wait()
            try: results.append(self.answer(room, user))
            except api.APIError as e: errors.append(e.status)
        threads = [threading.Thread(target=answer, args=(i,)) for i in range(5)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(results), 1); self.assertEqual(errors, [409]*4)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0], 5)
            self.assertEqual(db.execute('SELECT SUM(xp) FROM student_companions').fetchone()[0], 15)

    def test_source_exhaustion_does_not_award_or_fake_win(self):
        room = self.full()
        self.now += 15*63000
        room = self.poll(room)
        self.assertEqual(room['endReason'], 'source_exhausted'); self.assertIsNone(room['winnerId'])
        self.assertEqual(sum(r['points'] for r in room['rankings']), 0)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],0)

    def test_gate_empty_source_and_rejected_source_purposes(self):
        self.assertFalse(GroupGames().catalogue(5)['ready'])
        with api.connect(self.path, True) as db:
            with self.assertRaises(api.APIError): GroupGames().enter(db,self.users[0],{'mode':'animal_race','requestKey':'not-ready-key'},'create',5)
        self.assertFalse(GroupGames(synthetic_source(),policy_approved=True).enabled())
        with self.assertRaises(ValueError):QuestionSource([{'id':'bad','purpose':'paid','grade':5}])
        with self.assertRaises(ValueError):QuestionSource([{'id':'bad','purpose':'group-games','grade':5,'revision':1,'text':'test','responseMode':'typed','answer':'1;2','answerKind':'ordered'}])
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rooms').fetchone()[0],0)

    def test_request_binding_forfeit_and_wait_expiry(self):
        room = self.create()
        self.assertEqual(self.create()['id'], room['id'])
        with self.assertRaises(api.APIError):self.create('animal_race')
        self.now += 300000; self.assertEqual(self.poll(room)['status'],'cancelled')
        room = self.full('animal_race')
        for i in range(5):
            with api.connect(self.path,True) as db:
                room=self.game.mutate(db,self.users[i],room['id'],{'requestKey':f'leave-player-{i}'},'leave')
        self.assertEqual(room['endReason'],'cancelled');self.assertIsNone(room['winnerId'])
        self.assertTrue(all(r['points']==0 for r in room['rankings']))
        self.assertEqual(self.game._signature('answer',{'round':1,'answer':'2'}),self.game._signature('answer',{'answer':'2','round':1}))

    def test_waiting_leave_retry_and_xp_cap(self):
        room=self.create()
        body={'requestKey':'waiting-leave-0001'}
        with api.connect(self.path,True) as db:
            first=self.game.mutate(db,self.users[0],room['id'],body,'leave')
        with api.connect(self.path,True) as db:
            repeated=self.game.mutate(db,self.users[0],room['id'],body,'leave')
            self.assertEqual(first['id'],repeated['id'])
            with self.assertRaises(api.APIError):self.game.mutate(db,self.users[1],room['id'],body,'leave')
            db.execute('UPDATE student_companions SET xp=999999999 WHERE student_id=?',(self.users[0]['student_id'],))
        room=self.win()
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?',(self.users[0]['student_id'],)).fetchone()[0],1000000000)
            self.assertEqual(db.execute('SELECT points FROM group_game_rewards WHERE student_id=?',(self.users[0]['student_id'],)).fetchone()[0],5)

    def test_strict_source_types_and_shared_choice_validation(self):
        q={'id':'source-test','revision':1,'purpose':'group-games','grade':True,'text':'Test source','responseMode':'typed','answer':'2'}
        with self.assertRaises(ValueError):QuestionSource([q],qa_only=True)
        q.update(grade=5,modes='animal_race')
        with self.assertRaises(ValueError):QuestionSource([q],qa_only=True)
        q.update(modes=['animal_race'],responseMode='choice',options=['2','2.0','3','4'],choiceRationales=['Đối chiếu phép tính và kết quả.']*4)
        with self.assertRaises(ValueError):QuestionSource([q],approved=True)
        q['options']=['2','3','4','5'];q['choiceRationales']=['Lý do sai có đối chiếu rõ ràng.']*3
        with self.assertRaises(ValueError):QuestionSource([q],approved=True)

    def test_dispatch_auth_csrf_owner_disabled_and_grade_boundary(self):
        from backend.group_games import dispatch,BASE
        server=SimpleNamespace(database_path=self.path,group_games=self.game)
        handler=SimpleNamespace(server=server,headers={'Host':'127.0.0.1:19031'},path=BASE+'/catalogue')
        with self.assertRaises(api.APIError) as caught:dispatch(handler,'GET',handler.path,{})
        self.assertEqual(caught.exception.status,401)
        handler.headers['Cookie']=self.cookies[0]
        data,status=dispatch(handler,'GET',handler.path,{})
        self.assertTrue(data['ready']);self.assertEqual(status,200)
        handler.path=BASE+'/rooms'
        with self.assertRaises(api.APIError) as caught:dispatch(handler,'POST',handler.path,{'mode':'animal_race','requestKey':'dispatch-create-01'})
        self.assertEqual(caught.exception.status,403)
        handler.headers.update({'X-CSRF-Token':self.users[0]['csrf_token'],'Origin':'http://evil.invalid'})
        with self.assertRaises(api.APIError) as caught:dispatch(handler,'POST',handler.path,{'mode':'animal_race','requestKey':'dispatch-create-01'})
        self.assertEqual(caught.exception.status,403)
        handler.headers['Origin']='http://127.0.0.1:19031'
        room=dispatch(handler,'POST',handler.path,{'mode':'animal_race','requestKey':'dispatch-create-01'})[0]['room']
        handler.path=BASE+'/rooms/'+room['id'];handler.headers['Cookie']=self.cookies[6]
        with self.assertRaises(api.APIError) as caught:dispatch(handler,'GET',handler.path,{})
        self.assertEqual(caught.exception.status,403)
        with api.connect(self.path,True) as db:
            with self.assertRaises(api.APIError):self.game.enter(db,self.users[6],{'code':room['code'],'requestKey':'wrong-grade-join'},'join',4)
        server.group_games=None;handler.headers['Cookie']=self.cookies[5];handler.headers['X-CSRF-Token']=self.users[5]['csrf_token'];handler.path=BASE+'/rooms'
        with self.assertRaises(api.APIError) as caught:dispatch(handler,'POST',handler.path,{'mode':'capture_flag','requestKey':'default-disabled'})
        self.assertEqual(caught.exception.status,503)


if __name__ == '__main__':unittest.main()
