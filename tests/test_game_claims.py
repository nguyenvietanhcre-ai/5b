"""Isolated atomic cross-game claims and public pairing tests."""
import secrets,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_local_test_games as native
from backend import platform_api as api, game_claims as claims
class GameClaimTests(unittest.TestCase):
    setUp=native.NativeLocalTestGamesTests.setUp
    tearDown=native.NativeLocalTestGamesTests.tearDown
    actor=native.NativeLocalTestGamesTests.actor
    def bot(self,c,key=None):return c.call('bot/start',{'scope':'all','requestKey':key or secrets.token_hex(12)})
    def quick(self,c,key=None):return c.call('arena',{'action':'quick','scope':'all','requestKey':key or secrets.token_hex(12)})
    def leave(self,c,claim):return c.call('game-claim',{'action':'leave','claimId':claim['claimId']})
    def test_group_visibility_projection_private_code_join_and_nonce_intent(self):
        a,b,outsider,bot=[self.actor() for _ in range(4)]
        public=a.call('group-games/rooms',{'mode':'capture_flag','public':True,'requestKey':'public-room-qa'})['room']
        private=b.call('group-games/rooms',{'mode':'capture_flag','public':False,'requestKey':'private-room-qa'})['room']
        self.assertIs(public['public'],True);self.assertIs(private['public'],False)
        replay=b.call('group-games/rooms',{'mode':'capture_flag','public':False,'requestKey':'private-room-qa'})['room']
        self.assertEqual(replay['id'],private['id']);self.assertIs(replay['public'],False)
        with self.assertRaises(api.APIError) as caught:b.call('group-games/rooms',{'mode':'capture_flag','public':True,'requestKey':'private-room-qa'})
        self.assertEqual(caught.exception.status,409)
        listed=outsider.call('group-games/rooms?mode=capture_flag')['rooms']
        self.assertIn(public['id'],{row['id'] for row in listed});self.assertNotIn(private['id'],{row['id'] for row in listed})
        with self.assertRaises(api.APIError) as caught:outsider.call('group-games/rooms/'+private['id'])
        self.assertEqual(caught.exception.status,403)
        joined=outsider.call('group-games/join',{'code':private['code'],'requestKey':'private-code-join'})['room']
        self.assertIs(joined['public'],False);self.assertEqual(len(joined['players']),2)
        practice=bot.call('group-games/rooms',{'mode':'animal_race','playMode':'bot','public':True,'requestKey':'bot-private-qa'})['room']
        self.assertIs(practice['public'],False)
    def test_public_auto_private_accept(self):
        a,b=self.actor(),self.actor();x=self.quick(a);y=self.quick(b)
        self.assertEqual(x['code'],y['code']);room=self.server.arena.rooms[x['code']];self.assertEqual(room['status'],'preparing')
        self.assertAlmostEqual(room['readyAt']-max(p['seen'] for p in room['players'].values()),3)
        with api.connect(self.path) as db:self.assertEqual(db.execute("SELECT count(*) FROM daily_usage WHERE category='human'").fetchone()[0],2)
        c,d=self.actor(),self.actor();p=c.call('arena',{'action':'create','scope':'all','public':False});d.call('arena',{'action':'join','code':p['code']})
        self.assertEqual(self.server.arena.rooms[p['code']]['status'],'challenged')
    def test_ineligible_host_skip_no_ghost_charge(self):
        a,b=self.actor(),self.actor();x=self.quick(a)
        with api.connect(self.path,True) as db:
            from backend.learning_update import consume
            record=db.execute('SELECT id student_id,account_id FROM students WHERE id=?',(a.sid,)).fetchone()
            for n in range(3):consume(db,record,'human','used-'+str(n))
        y=self.quick(b);self.assertNotEqual(x['code'],y['code']);self.assertEqual(len(self.server.arena.rooms[x['code']]['players']),1)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage WHERE student_id=?',(b.sid,)).fetchone()[0],0)
    def test_persistence_failure_ram_compensation(self):
        a,b=self.actor(),self.actor();x=self.quick(a)
        with patch.object(claims,'bind',side_effect=RuntimeError('injected persistence failure')):
            with self.assertRaises(RuntimeError):self.quick(b)
        self.assertEqual(len(self.server.arena.rooms[x['code']]['players']),1);self.assertEqual(self.server.arena.rooms[x['code']]['status'],'waiting')
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],0)
    def test_bot_replay_crossgame_conflict(self):
        c=self.actor();x=self.bot(c,'same-bot-nonce');y=self.bot(c,'same-bot-nonce')
        self.assertEqual(x['gameClaim']['claimId'],y['gameClaim']['claimId']);self.assertEqual(x['questions'],y['questions'])
        with self.assertRaises(api.APIError) as e:self.quick(c)
        self.assertEqual(e.exception.status,409)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],1)
    def test_two_tabs_one_winner(self):
        c=self.actor();barrier=threading.Barrier(2)
        def run(kind):
            from test_arena_penalties import Client
            other=Client(self.server);other.headers=dict(c.headers);other.csrf=c.csrf;barrier.wait()
            try:return ('ok',self.bot(other) if kind=='bot' else self.quick(other))
            except api.APIError as e:return ('error',e.status)
        with ThreadPoolExecutor(max_workers=2) as workers:results=list(workers.map(run,['bot','human']))
        self.assertEqual(sorted(r[0] for r in results),['error','ok']);self.assertEqual(next(r[1] for r in results if r[0]=='error'),409)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM game_claims').fetchone()[0],1)
    def test_checkpoint_cas_validation_and_generation(self):
        c=self.actor();x=self.bot(c);cid=x['gameClaim']['claimId'];base={'action':'touch','claimId':cid,'expectedRevision':0}
        for invalid in ({'deadline':{}},{'botAnswered':'yes'},{'review':[{'myAnswer':{}}]},{'lastAttack':{'damage':False}}):
            with self.assertRaises(api.APIError) as e:c.call('game-claim',{**base,'state':invalid})
            self.assertEqual(e.exception.status,400)
        touched=c.call('game-claim',{**base,'state':{'index':1,'hp':80,'opponentHp':100,'correct':0}});self.assertEqual(touched['claim']['checkpointRevision'],1)
        with self.assertRaises(api.APIError):c.call('game-claim',{**base,'state':{'index':0}})
        self.leave(c,x['gameClaim']);new=self.quick(c)
        with self.assertRaises(api.APIError):self.leave(c,x['gameClaim'])
        self.assertEqual(c.call('game-claim')['claim']['claimId'],new['gameClaim']['claimId'])
    def test_legacy_adopt_failclosed(self):
        c=self.actor()
        with self.assertRaises(api.APIError) as e:c.call('bot/adopt',{'battle':{'mode':'bot'}})
        self.assertEqual(e.exception.status,409)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],0)
    def test_crosspool_owned_leave(self):
        c=self.actor();x=self.quick(c);c.headers.update(Host='192.168.1.13:8765',Origin='http://192.168.1.13:8765')
        state=c.call('game-claim')['claim'];self.assertFalse(state['sourceAvailable']);self.assertNotIn('credentials',state)
        out=self.leave(c,state);self.assertTrue(out['left']);self.assertIsNone(c.call('game-claim')['claim']);self.assertEqual(self.server.arena.rooms[x['code']]['status'],'cancelled')


    def test_group_quick_fullest_private_listing_and_crossgame(self):
        people=[self.actor() for _ in range(8)]
        def create(c,private=False):return c.call('group-games/rooms',{'mode':'capture_flag','public':not private,'requestKey':secrets.token_hex(12)})['room']
        def join(c,r):return c.call('group-games/join',{'code':r['code'],'requestKey':secrets.token_hex(12)})['room']
        one=create(people[0]);two=create(people[1]);private=create(people[2],True)
        join(people[3],one);join(people[4],two);join(people[5],two)
        listed=people[6].call('group-games/rooms?mode=capture_flag')['rooms']
        self.assertEqual({r['id'] for r in listed},{one['id'],two['id']})
        hit=people[6].call('group-games/quick',{'mode':'capture_flag','requestKey':'fullest-quick-key'})
        self.assertEqual(hit['room']['id'],two['id']);self.assertEqual(len(hit['room']['players']),4)
        with self.assertRaises(api.APIError) as e:self.bot(people[6])
        self.assertEqual(e.exception.status,409)
        # An old same-grade room in another pool cannot leak into listings or admissions.
        with api.connect(self.path,True) as db:
            import json
            row=db.execute('SELECT payload_json FROM group_game_rooms WHERE id=?',(one['id'],)).fetchone()
            data=json.loads(row[0]);data['sourcePool']='legacy';db.execute('UPDATE group_game_rooms SET payload_json=? WHERE id=?',(api.packed(data),one['id']))
        self.assertNotIn(one['id'],{r['id'] for r in people[7].call('group-games/rooms?mode=capture_flag')['rooms']})
        with self.assertRaises(api.APIError) as e:people[0].call('group-games/rooms/'+one['id']+'/answer',{'round':1,'answer':'1','requestKey':'pool-answer-guard'})
        self.assertEqual(e.exception.status,403)
        self.leave(people[0],people[0].call('game-claim')['claim'])
        self.assertIsNone(people[0].call('game-claim')['claim'])
    def test_nonce_intent_and_completed_nonce_never_reconsume(self):
        c=self.actor();x=self.bot(c,'global-intent-key')
        with self.assertRaises(api.APIError) as e:c.call('arena',{'action':'quick','scope':'all','requestKey':'global-intent-key'})
        self.assertEqual(e.exception.status,409);self.leave(c,x['gameClaim'])
        with self.assertRaises(api.APIError) as e:self.bot(c,'global-intent-key')
        self.assertEqual(e.exception.status,409)
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],1)
    def test_bot_lease_expires_but_live_human_lease_does_not(self):
        c=self.actor();x=self.bot(c)
        with api.connect(self.path,True) as db:db.execute('UPDATE game_claims SET expires_at=0 WHERE student_id=?',(c.sid,))
        self.assertIsNone(c.call('game-claim')['claim']);human=self.quick(c)
        with api.connect(self.path,True) as db:db.execute('UPDATE game_claims SET expires_at=0 WHERE student_id=?',(c.sid,))
        self.assertEqual(c.call('game-claim')['claim']['claimId'],human['gameClaim']['claimId'])
        with self.assertRaises(api.APIError):self.bot(c)
    def test_legacy_authoritative_human_adopts_and_claims_are_owner_only(self):
        c,d=self.actor(),self.actor();x=self.quick(c)
        with api.connect(self.path,True) as db:
            db.execute('DELETE FROM game_claims WHERE student_id=?',(c.sid,))
        adopted=c.call('game-claim')['claim'];self.assertEqual(adopted['roomId'],self.server.arena.rooms[x['code']]['id'])
        self.assertIsNone(d.call('game-claim')['claim'])
        with self.assertRaises(api.APIError):d.call('game-claim',{'action':'leave','claimId':adopted['claimId']})
        self.assertEqual(c.call('game-claim')['claim']['claimId'],adopted['claimId'])

    def test_commit_failure_restores_ram_and_durable_membership(self):
        import sqlite3
        a,b=self.actor(),self.actor();x=self.quick(a);original=sqlite3.connect
        class FailCommit(sqlite3.Connection):
            fail=False
            def execute(self,sql,*args,**kwargs):
                result=super().execute(sql,*args,**kwargs)
                if sql.startswith('INSERT INTO duel_players'):self.fail=True
                return result
            def commit(self):
                if self.fail:
                    self.fail=False;raise sqlite3.OperationalError('injected commit failure')
                return super().commit()
        def connect(*args,**kwargs):return original(*args,**kwargs,factory=FailCommit)
        with patch.object(sqlite3,'connect',side_effect=connect):
            with self.assertRaises(sqlite3.OperationalError):self.quick(b)
        room=self.server.arena.rooms[x['code']];self.assertEqual(room['status'],'waiting');self.assertEqual(len(room['players']),1)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM arena_members').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM game_claims').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],0)
