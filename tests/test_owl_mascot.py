"""Owl selection survives catalog upgrades and reaches both arena participants."""
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import academic, connect, dispatch, mascot_code, seed_catalog


class OwlClient:
    def __init__(self, server):
        self.server = server
        self.client_address = ('owl-test-' + secrets.token_hex(4), 1234)
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.api_headers = {}
        self.csrf = ''

    def call(self, path, body=None):
        self.path = '/api/v1/' + path
        self.headers['X-CSRF-Token'] = self.csrf
        payload, status = dispatch(self, 'GET' if body is None else 'POST', self.path.split('?')[0], body)
        cookie = self.api_headers.pop('Set-Cookie', None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        if payload.get('csrf'):
            self.csrf = payload['csrf']
        assert status == 200
        return payload


class OwlMascotTests(unittest.TestCase):
    def setUp(self):
        workspace = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                     else Path(tempfile.gettempdir()))
        workspace.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='owl-backend-test-', dir=workspace)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'platform.sqlite3'
        initialize(self.path)
        seed_catalog(self.path)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=True, arena=Arena())

    def user(self):
        client = OwlClient(self.server)
        login, password = 'owl-' + secrets.token_hex(6), secrets.token_urlsafe(18)
        client.call('auth/register', {'login': login, 'password': password, 'name': 'Bạn Cú mèo',
                                    'birthYear': academic()[0] - 10, 'inviteCode': ''})
        return client, login, password

    def test_old_catalog_adds_owl_without_changing_existing_companion(self):
        client, _, _ = self.user()
        client.call('mascot', {'mascot': 'fox'})
        with connect(self.path, True) as db:
            before = tuple(db.execute('SELECT student_id,mascot_id,xp FROM student_companions').fetchone())
            db.execute('DELETE FROM mascots WHERE name=?', ('Cú mèo',))
        seed_catalog(self.path)
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM mascots WHERE name=?', ('Cú mèo',)).fetchone()[0], 1)
            self.assertEqual(tuple(db.execute('SELECT student_id,mascot_id,xp FROM student_companions').fetchone()), before)
        self.assertEqual(client.call('mascot', {'mascot': 'cu-meo'})['state']['mascot'], 'cu-meo')
        self.assertEqual(mascot_code('Cú mèo'), 'cu-meo')

    def test_owl_persists_and_is_shown_to_both_arena_participants(self):
        owner, login, password = self.user()
        self.assertEqual(owner.call('mascot', {'mascot': 'cu-meo'})['state']['mascot'], 'cu-meo')
        resumed = OwlClient(self.server)
        self.assertEqual(resumed.call('auth/login', {'login': login, 'password': password})['state']['mascot'], 'cu-meo')
        self.assertTrue(any(row['mine'] and row['mascot'] == 'cu-meo'
                            for row in owner.call('leaderboard?kind=battle&period=all')['rows']))
        room = owner.call('arena', {'action': 'create', 'scope': 'weekly', 'public': True})
        friend, _, _ = self.user()
        listed = next(row for row in friend.call('arena', {'action': 'list'})['rooms'] if row['code'] == room['code'])
        self.assertEqual(listed['mascot'], 'cu-meo')
        friend.call('mascot', {'mascot': 'cu-meo'})
        joined = friend.call('arena', {'action': 'join', 'code': room['code']})
        owner.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        for client, access in ((owner, room), (friend, joined)):
            state = client.call('arena', {'action': 'state', **access})
            self.assertEqual(state['battle']['opponentMascot'], 'cu-meo')


if __name__ == '__main__':
    unittest.main()
