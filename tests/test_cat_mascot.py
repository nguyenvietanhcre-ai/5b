import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class CatMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep Windows artifacts in the workspace; Docker's read-only app uses
        # its existing writable /tmp mount rather than trying to create /work.
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'cat-mascot-tests'
        work.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=work)
        cls.path = Path(cls.directory.name) / 'platform.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=True, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    user = platform_tests.PlatformTests.user

    def test_cat_choice_survives_session_and_reports_in_ranking_and_arena(self):
        cat, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = cat.call('mascot', {'mascot': 'cat'})
        self.assertEqual(selected['state']['mascot'], 'cat')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        account_id = initial['account']['id']
        with connect(self.path) as db:
            row = db.execute('SELECT m.name FROM student_companions c '
                             'JOIN mascots m ON m.id=c.mascot_id '
                             'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                             (account_id,)).fetchone()
            self.assertEqual(row['name'], 'Mèo')
        self.assertEqual(cat.call('session')['state']['mascot'], 'cat')
        mine = next(row for row in cat.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'cat')
        # A request-supplied mascot cannot replace the authenticated DB choice.
        room = cat.call('arena', {'action': 'create', 'public': True,
                                 'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'cat')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        cat.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'cat')
        cat.call('arena', {'action': 'leave', **room})
        cat.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'cat')

    def test_seed_is_idempotent_and_invalid_choices_preserve_current_mascot(self):
        client, _, _, _ = self.user()
        for code in ('sprout', 'fox', 'rabbit', 'cat'):
            self.assertEqual(client.call('mascot', {'mascot': code})['state']['mascot'], code)
            self.assertEqual(client.call('session')['state']['mascot'], code)
            mine = next(row for row in client.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
            self.assertEqual(mine['mascot'], code)
        for value in ('meo', 'unknown', '', None, [], {}):
            with self.subTest(value=value), self.assertRaises(APIError) as caught:
                client.call('mascot', {'mascot': value})
            self.assertEqual(caught.exception.status, 400)
            self.assertEqual(client.call('session')['state']['mascot'], 'cat')
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Mèo'").fetchone()[0], 1)
        self.assertEqual(client.call('session')['state']['mascot'], 'cat')


if __name__ == '__main__':
    unittest.main()
