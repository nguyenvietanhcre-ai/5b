"""Chim sẻ selection survives sessions and is visible to real Arena opponents."""
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import academic, dispatch, seed_catalog


class SparrowTests(unittest.TestCase):
    def test_companion_selection_survives_login_and_arena_transport(self):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work, prefix='sparrow-test-') as directory:
            db = Path(directory) / 'fixture.sqlite3'
            initialize(db)
            seed_catalog(db)
            server = SimpleNamespace(database_path=db, review_upgrades=True, arena=Arena())

            def client():
                return SimpleNamespace(server=server, client_address=(secrets.token_hex(8), 1234),
                    headers={'Host':'localhost:8765','Origin':'http://localhost:8765'}, api_headers={})

            def call(c, route, body=None):
                c.path = '/api/v1/' + route
                value, status = dispatch(c, 'GET' if body is None else 'POST', c.path.split('?')[0], body)
                self.assertEqual(status, 200)
                cookie = c.api_headers.pop('Set-Cookie', None)
                if cookie:
                    c.headers['Cookie'] = cookie.split(';')[0]
                if value.get('csrf'):
                    c.headers['X-CSRF-Token'] = value['csrf']
                return value

            def register(c):
                credentials = {'login':'sparrow-' + secrets.token_hex(8), 'password':secrets.token_urlsafe(24)}
                call(c, 'auth/register', {**credentials, 'name':'QA Chim sẻ', 'birthYear':academic()[0]-10})
                return credentials

            owner, friend = client(), client()
            credentials = register(owner)
            register(friend)
            self.assertEqual(call(owner, 'mascot', {'mascot':'sparrow'})['state']['mascot'], 'sparrow')
            resumed = client()
            self.assertEqual(call(resumed, 'auth/login', credentials)['state']['mascot'], 'sparrow')
            self.assertTrue(any(r['mine'] and r['mascot']=='sparrow' for r in
                call(resumed, 'leaderboard?kind=battle&period=all')['rows']))
            room = call(resumed, 'arena', {'action':'create','scope':'weekly','public':True})
            self.assertEqual(next(r for r in call(friend, 'arena', {'action':'list'})['rooms']
                if r['code']==room['code'])['mascot'], 'sparrow')
            joined = call(friend, 'arena', {'action':'join','code':room['code']})
            call(resumed, 'arena', {'action':'accept', **room})
            server.arena.rooms[room['code']]['readyAt'] = 0
            self.assertEqual(call(friend, 'arena', {'action':'state', **joined})['battle']['opponentMascot'], 'sparrow')


if __name__ == '__main__':
    unittest.main()
