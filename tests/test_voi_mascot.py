"""Voi selection must retain identity across DB sessions and Arena opponents."""
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, dispatch, seed_catalog


class Client:
    def __init__(self, server):
        self.server = server
        self.client_address = ('voi-test-' + secrets.token_hex(6), 1234)
        self.headers = {'Host':'localhost:8765', 'Origin':'http://localhost:8765'}
        self.path = ''
        self.api_headers = {}
        self.csrf = ''

    def call(self, endpoint, body=None):
        self.path = '/api/v1/' + endpoint
        self.headers['X-CSRF-Token'] = self.csrf
        result, status = dispatch(self, 'GET' if body is None else 'POST', self.path.split('?')[0], body)
        cookie = self.api_headers.pop('Set-Cookie', None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        if result.get('csrf'):
            self.csrf = result['csrf']
        if status != 200:
            raise AssertionError(status)
        return result


class VoiIntegrationTests(unittest.TestCase):
    def test_selection_resume_ranking_and_server_owned_arena_identity(self):
        scratch = Path(__file__).resolve().parents[1] / 'work' / 'voi-game-integration' / 'tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            database = Path(directory) / 'voi.sqlite3'
            initialize(database)
            seed_catalog(database)
            seed_catalog(database)
            server = SimpleNamespace(database_path=database, review_upgrades=False, arena=Arena())
            first, second = Client(server), Client(server)
            login = 'voi-' + secrets.token_hex(6)
            password = secrets.token_urlsafe(20)
            first.call('auth/register', {'login':login, 'password':password, 'name':'Bạn Voi',
                       'birthYear':academic()[0]-10})
            second.call('auth/register', {'login':'friend-'+secrets.token_hex(6),
                        'password':secrets.token_urlsafe(20), 'name':'Bạn cùng chơi', 'birthYear':academic()[0]-10})
            selected = first.call('mascot', {'mascot':'voi'})
            self.assertEqual(selected['state']['mascot'], 'voi')
            self.assertEqual(selected['state']['points'], 1000)
            with self.assertRaises(APIError):
                first.call('mascot', {'mascot':'unknown-mascot'})
            with self.assertRaises(APIError):
                first.call('mascot', {'mascot':[]})
            first.call('auth/logout', {})
            resumed = first.call('auth/login', {'login':login, 'password':password})
            self.assertEqual(resumed['state']['mascot'], 'voi')
            ranks = first.call('leaderboard?kind=battle&period=all')['rows']
            self.assertEqual(next(row for row in ranks if row['mine'])['mascot'], 'voi')

            room = first.call('arena', {'action':'create', 'public':True, 'mascot':'fox'})
            rooms = second.call('arena', {'action':'list'})['rooms']
            self.assertEqual(next(row for row in rooms if row['code']==room['code'])['mascot'], 'voi')
            joined = second.call('arena', {'action':'join', 'code':room['code']})
            first.call('arena', {'action':'accept', **room})
            server.arena.rooms[room['code']]['readyAt'] = 0
            opponent_view = second.call('arena', {'action':'state', **joined})
            self.assertEqual(opponent_view['battle']['opponentMascot'], 'voi')
            self.assertEqual(opponent_view['battle']['hp'], 100)
            self.assertEqual(opponent_view['battle']['opponentHp'], 100)
            with connect(database) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Voi'").fetchone()[0], 1)
