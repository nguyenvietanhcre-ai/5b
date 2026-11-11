"""Exercise the persisted butterfly choice through the authenticated game API."""
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, seed_catalog
from test_platform_api import Client


class ButterflyMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Windows work stays in the project; the read-only Docker image has /tmp.
        work = (Path(__file__).resolve().parents[1] / 'work' / 'butterfly-tests'
                if os.name == 'nt' else Path(tempfile.gettempdir()) / 'butterfly-tests')
        work.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=work)
        cls.path = Path(cls.directory.name) / 'platform.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path,
                                     review_upgrades=True, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def user(self):
        client = Client(self.server)
        login, password = 'butterfly-' + secrets.token_hex(6), secrets.token_urlsafe(18)
        initial = client.call('auth/register', {
            'login': login, 'password': password, 'name': 'Bạn Bướm thử nghiệm',
            'birthYear': academic()[0] - 10, 'inviteCode': '',
        })
        return client, initial, login, password

    def test_choice_persists_and_authenticated_arena_uses_saved_mascot(self):
        butterfly, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = butterfly.call('mascot', {'mascot': 'butterfly'})
        self.assertEqual(selected['state']['mascot'], 'butterfly')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        with connect(self.path) as db:
            row = db.execute('SELECT m.name, c.xp FROM student_companions c '
                             'JOIN mascots m ON m.id=c.mascot_id '
                             'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                             (initial['account']['id'],)).fetchone()
            self.assertEqual(row['name'], 'Bướm')
            self.assertEqual(row['xp'], initial['state']['points'])
        self.assertEqual(butterfly.call('session')['state']['mascot'], 'butterfly')
        mine = next(row for row in butterfly.call(
            'leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'butterfly')

        # Caller-supplied artwork cannot replace the authenticated saved choice.
        room = butterfly.call('arena', {'action': 'create', 'public': True,
                                        'scope': 'weekly', 'mascot': 'fox'})
        listed = next(row for row in friend.call('arena', {'action': 'list'})['rooms']
                      if row['code'] == room['code'])
        self.assertEqual(listed['mascot'], 'butterfly')
        joined = friend.call('arena', {'action': 'join', 'code': room['code']})
        butterfly.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'butterfly')
        butterfly.call('arena', {'action': 'leave', **room})
        butterfly.call('auth/logout', {})
        resumed = Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'butterfly')
        self.assertEqual(resumed['state']['points'], initial['state']['points'])

    def test_reseed_and_rejected_choices_preserve_butterfly_and_experience(self):
        client, initial, _, _ = self.user()
        for code in ('sprout', 'fox', 'butterfly'):
            state = client.call('mascot', {'mascot': code})['state']
            self.assertEqual(state['mascot'], code)
            self.assertEqual(state['points'], initial['state']['points'])
        for value in ('buom', 'unknown', '', None, [], {}):
            with self.subTest(value=value):
                with self.assertRaises(APIError) as caught:
                    client.call('mascot', {'mascot': value})
                self.assertEqual(caught.exception.status, 400)
                state = client.call('session')['state']
                self.assertEqual(state['mascot'], 'butterfly')
                self.assertEqual(state['points'], initial['state']['points'])
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Bướm'")
                             .fetchone()[0], 1)
        self.assertEqual(client.call('session')['state']['mascot'], 'butterfly')


if __name__ == '__main__':
    unittest.main()
