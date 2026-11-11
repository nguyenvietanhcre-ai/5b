import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class CrabMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The desktop keeps artifacts in work; Docker already has writable /tmp.
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'crab-mascot-tests'
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

    def test_crab_persists_and_arena_uses_authenticated_choice(self):
        crab, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = crab.call('mascot', {'mascot': 'crab'})
        self.assertEqual(selected['state']['mascot'], 'crab')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        self.assertEqual(crab.call('session')['state']['mascot'], 'crab')
        mine = next(row for row in crab.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'crab')

        # Reseeding must neither duplicate the mascot nor reset the selection.
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Cua biển'").fetchone()[0], 1)
            row = db.execute('SELECT m.name FROM student_companions c '
                             'JOIN mascots m ON m.id=c.mascot_id '
                             'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                             (initial['account']['id'],)).fetchone()
            self.assertEqual(row['name'], 'Cua biển')
        for invalid in ('cua-bien', 'unknown', '', None, [], {}):
            with self.subTest(invalid=invalid), self.assertRaises(APIError) as caught:
                crab.call('mascot', {'mascot': invalid})
            self.assertEqual(caught.exception.status, 400)
            self.assertEqual(crab.call('session')['state']['mascot'], 'crab')

        # The API must ignore a forged mascot supplied in the arena request.
        room = crab.call('arena', {'action': 'create', 'public': True,
                                  'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'crab')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        crab.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'crab')
        crab.call('arena', {'action': 'leave', **room})
        crab.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'crab')
        self.assertEqual(resumed['state']['points'], initial['state']['points'])


if __name__ == '__main__':
    unittest.main()
