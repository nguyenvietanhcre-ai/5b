"""Gấu uses the existing companion persistence and trusted arena payloads."""
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import academic, connect, dispatch, seed_catalog


class BearClient:
    def __init__(self, server):
        self.server = server
        self.client_address = ('bear-test-' + secrets.token_hex(6), 1234)
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.path = ''
        self.api_headers = {}
        self.csrf = ''

    def call(self, path, body=None):
        self.path = '/api/v1/' + path
        self.headers['X-CSRF-Token'] = self.csrf
        result, status = dispatch(self, 'GET' if body is None else 'POST',
                                  self.path.split('?')[0], body)
        if cookie := self.api_headers.pop('Set-Cookie', None):
            self.headers['Cookie'] = cookie.split(';')[0]
        if result.get('csrf'):
            self.csrf = result['csrf']
        assert status == 200
        return result


class BearMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path(__file__).resolve().parents[1] / 'work' / 'mascot-animation' / 'gau' / 'v1'
        if Path('/.dockerenv').exists():
            scratch = Path('/tmp/bear-api-tests')
        scratch.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='bear-api-', dir=scratch)
        cls.path = Path(cls.directory.name) / 'bear.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=False, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def user(self):
        client = BearClient(self.server)
        login = 'bear-' + secrets.token_hex(8)
        password = secrets.token_urlsafe(18)
        client.call('auth/register', {'login': login, 'password': password, 'name': 'Bạn Gấu thử',
                                     'birthYear': academic()[0] - 10, 'inviteCode': ''})
        return client, login, password

    def test_seed_preserves_existing_ids_and_inserts_bear_once(self):
        with connect(self.path) as db:
            before = dict(db.execute('SELECT name,id FROM mascots'))
        seed_catalog(self.path)
        with connect(self.path) as db:
            after = dict(db.execute('SELECT name,id FROM mascots'))
            count = db.execute('SELECT count(*) FROM mascots WHERE name=?', ('Gấu',)).fetchone()[0]
        self.assertIn('Gấu', before)
        self.assertEqual(before, after)
        self.assertEqual(count, 1)

    def test_bear_selection_survives_login_and_reaches_arena_and_ranking(self):
        client, login, password = self.user()
        selected = client.call('mascot', {'mascot': 'gau'})
        self.assertEqual(selected['state']['mascot'], 'gau')
        self.assertEqual(selected['state']['points'], 1000)
        restored = BearClient(self.server)
        self.assertEqual(restored.call('auth/login', {'login': login, 'password': password})
                         ['state']['mascot'], 'gau')
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT m.name FROM student_companions c '
                                        'JOIN mascots m ON m.id=c.mascot_id '
                                        'JOIN students s ON s.id=c.student_id '
                                        'JOIN accounts a ON a.id=s.account_id '
                                        'WHERE a.login_identifier=?', (login,)).fetchone()[0], 'Gấu')
        self.assertTrue(any(row['mine'] and row['mascot'] == 'gau' for row in
                            client.call('leaderboard?kind=battle&period=all')['rows']))
        room = client.call('arena', {'action': 'create', 'scope': 'weekly', 'public': True})
        friend, _, _ = self.user()
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'gau')
        joined = friend.call('arena', {'action': 'join', 'code': room['code']})
        client.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'gau')
        self.assertEqual((battle['hp'], battle['opponentHp']), (100, 100))


if __name__ == '__main__':
    unittest.main()
