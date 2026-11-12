"""Persistent, server-authoritative abandonment policy, using an isolated DB."""
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, dispatch, seed_catalog


class Client:
    def __init__(self, server):
        self.server = server
        self.client_address = ('arena-qa-' + secrets.token_hex(6), 1234)
        self.headers = {'Host':'localhost:8765', 'Origin':'http://localhost:8765'}
        self.api_headers = {}
        self.csrf = ''

    def call(self, path, body=None):
        self.path = '/api/v1/' + path
        self.headers['X-CSRF-Token'] = self.csrf
        result, status = dispatch(self, 'GET' if body is None else 'POST', self.path.split('?')[0], body)
        cookie = self.api_headers.pop('Set-Cookie', None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        self.csrf = result.get('csrf', self.csrf)
        assert status == 200
        return result


class ArenaPenaltyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path(__file__).resolve().parents[1] / 'work' / 'battle-lobby-review-20261112'
        scratch.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=scratch)
        cls.path = Path(cls.directory.name) / 'penalties.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.clock = time.time()
        self.patcher = patch('backend.arena.time.time', side_effect=lambda: self.clock)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=True, arena=Arena())
        self.first = self.user()
        self.second = self.user()

    def user(self):
        client = Client(self.server)
        client.login = 'arena-' + secrets.token_hex(6)
        client.password = secrets.token_urlsafe(18)
        state = client.call('auth/register', {'login':client.login, 'password':client.password,
                            'name':'Bạn thử nghiệm', 'birthYear':academic()[0]-10})
        client.account_id = state['account']['id']
        with connect(self.path, True) as db:
            client.sid = db.execute('SELECT id FROM students WHERE account_id=?', (client.account_id,)).fetchone()[0]
            db.execute('UPDATE student_companions SET xp=1006 WHERE student_id=?', (client.sid,))
        return client

    def pair(self, playing=True):
        room = self.first.call('arena', {'action':'create', 'scope':'weekly', 'public':False})
        join = self.second.call('arena', {'action':'join', 'code':room['code']})
        self.first.call('arena', {'action':'accept', **room})
        if playing:
            self.clock += 3.01
            self.first.call('arena', {'action':'state', **room})
        return room, join

    def leave(self, room):
        return self.first.call('arena', {'action':'leave', **room})

    def paid(self, client):
        with connect(self.path, True) as db:
            db.execute("UPDATE accounts SET vip_expires_at='2099-01-01T00:00:00Z' WHERE id=?", (client.account_id,))

    def test_forfeit_debits_once_refunds_survivor_and_never_counts_official_stats(self):
        room, join = self.pair()
        result = self.leave(room)
        self.assertEqual((result['result']['outcome'], result['result']['points']), ('lose', -1))
        self.assertEqual(result['arenaDiscipline']['recentStrikes'], 1)
        survivor = self.second.call('arena', {'action':'state', **join})['result']
        self.assertEqual((survivor['outcome'], survivor['points']), ('win', 0))
        self.assertTrue(survivor['quotaRefunded'])
        self.assertFalse(survivor['completed'])
        self.assertEqual(self.leave(room)['result'], result['result'])
        self.assertEqual(self.second.call('arena', {'action':'leave', **join})['result'], survivor)
        self.assertEqual(self.first.call('session')['state']['points'], 1005)
        saved = self.second.call('session')
        self.assertEqual(saved['state']['points'], 1006)
        self.assertEqual(saved['account']['usage']['human']['used'], 0)
        rows = self.first.call('leaderboard?kind=battle&period=all')['rows']
        own = next(row for row in rows if row['mine'])
        self.assertEqual((own['wins'], own['losses']), (0, 0))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM arena_discipline_events WHERE student_id=?', (self.first.sid,)).fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM xp_events WHERE student_id=?', (self.first.sid,)).fetchone()[0], 1)

    def test_escalating_cooldown_blocks_every_entry_and_survives_restart_and_login(self):
        self.paid(self.first)
        for strike, delay in [(1,0), (2,300), (3,900), (4,3600)]:
            room, _ = self.pair()
            result = self.leave(room)
            self.assertEqual(result['result']['penalty']['cooldownSeconds'], delay)
            self.assertEqual(result['arenaDiscipline']['recentStrikes'], strike)
            if delay:
                for action in ('create','quick','join','challenge'):
                    with self.assertRaises(APIError) as caught:
                        self.first.call('arena', {'action':action, 'code':'NOPE'})
                    self.assertEqual(caught.exception.status, 429)
                    self.assertGreater(caught.exception.arenaDiscipline['remainingSeconds'], 0)
                self.server.arena = Arena()
                fresh = Client(self.server)
                state = fresh.call('auth/login', {'login':self.first.login, 'password':self.first.password})
                self.assertEqual(state['arenaDiscipline']['remainingSeconds'], delay)
                self.clock += delay
        self.clock += 86400
        self.assertEqual(self.first.call('session')['arenaDiscipline']['recentStrikes'], 0)

    def test_xp_floor_and_preparation_cancellation_refund_both(self):
        with connect(self.path, True) as db:
            db.execute('UPDATE student_companions SET xp=1000 WHERE student_id=?', (self.first.sid,))
        room, _ = self.pair(playing=False)
        self.assertEqual(self.leave(room)['status'], 'cancelled')
        self.assertEqual(self.first.call('session')['account']['usage']['human']['used'], 0)
        self.assertEqual(self.second.call('session')['account']['usage']['human']['used'], 0)
        self.assertEqual(self.first.call('session')['arenaDiscipline']['recentAbandons'], 0)
        room, _ = self.pair()
        self.assertEqual(self.leave(room)['result']['points'], 0)
        self.assertEqual(self.first.call('session')['state']['points'], 1000)

    def test_network_forgiveness_then_strikes_and_settlement_without_survivor_poll(self):
        self.paid(self.first)
        for attempt in range(3):
            room, join = self.pair()
            raw = self.server.arena.rooms[room['code']]
            self.clock += raw['disconnectAfter'] + 0.01
            # The disconnected child's next admission triggers cleanup itself;
            # no survivor state poll is needed to persist that prior result.
            if attempt < 2:
                new = self.first.call('arena', {'action':'create'})
                self.first.call('arena', {'action':'leave', **new})
            else:
                with self.assertRaises(APIError) as caught:
                    self.first.call('arena', {'action':'quick'})
                self.assertEqual(caught.exception.status, 429)
            stored = self.first.call('arena', {'action':'state', **room})['result']
            self.assertEqual(stored['penalty']['disconnectForgiven'], attempt == 0)
            self.assertEqual(stored['points'], 0 if attempt == 0 else -1)
            self.assertEqual(stored['penalty']['strike'], attempt)
            # Both stopped polling, so both are disconnected in this scenario.
            self.assertFalse(self.second.call('arena', {'action':'state', **join})['result']['completed'])
            if attempt == 2:
                with connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM arena_discipline_events WHERE student_id=?', (self.first.sid,)).fetchone()[0], 3)
                self.assertEqual(self.first.call('session')['arenaDiscipline']['remainingSeconds'], 300)

    def test_live_survivor_gets_refund_after_network_grace(self):
        room, join = self.pair()
        raw = self.server.arena.rooms[room['code']]
        self.clock += raw['disconnectAfter'] + 0.01
        survivor = self.second.call('arena', {'action':'state', **join})['result']
        self.assertEqual((survivor['outcome'], survivor['points']), ('win', 0))
        self.assertTrue(survivor['quotaRefunded'])
        self.assertEqual(self.second.call('session')['account']['usage']['human']['used'], 0)
        leaver = self.first.call('arena', {'action':'state', **room})['result']
        self.assertTrue(leaver['penalty']['disconnectForgiven'])

    def test_natural_final_result_and_completed_friend_xp_remain_immutable(self):
        room, join = self.pair()
        raw = self.server.arena.rooms[room['code']]
        raw.update(resolved=True, nextAt=self.clock + 3)
        raw['players'][join['token']]['hp'] = 0
        result = self.leave(room)['result']
        self.assertEqual((result['outcome'], result['points']), ('win', 2))
        self.assertTrue(result['completed'])
        self.assertEqual(self.second.call('arena', {'action':'leave', **join})['result']['points'], -1)
        self.assertEqual(self.first.call('session')['arenaDiscipline']['recentAbandons'], 0)
        own = next(r for r in self.first.call('leaderboard?kind=battle&period=all')['rows'] if r['mine'])
        self.assertEqual((own['wins'], own['losses']), (1,0))

    def test_server_restart_cancels_without_penalty_and_refunds_both(self):
        room, join = self.pair()
        self.server.arena = Arena()
        state = self.first.call('session')
        self.assertEqual(state['account']['usage']['human']['used'], 0)
        self.assertEqual(state['arenaDiscipline']['recentAbandons'], 0)
        result = self.first.call('arena', {'action':'state', **room})['result']
        self.assertEqual((result['reason'], result['points'], result['completed']), ('server_restart',0,False))
        self.assertEqual(self.second.call('session')['account']['usage']['human']['used'], 0)


if __name__ == '__main__':
    unittest.main()
