import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class LionMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use isolated fixtures; selecting a mascot must never touch user data.
        work = (Path(__file__).resolve().parents[1] / 'work' / 'lion-animation'
                if os.name == 'nt' else Path(tempfile.gettempdir()) / 'lion-animation')
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

    def test_lion_persists_and_authenticated_choice_reaches_arena_and_ranking(self):
        lion, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = lion.call('mascot', {'mascot': 'lion'})
        self.assertEqual(selected['state']['mascot'], 'lion')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        account_id = initial['account']['id']
        with connect(self.path) as db:
            row = db.execute('SELECT m.name,c.xp FROM student_companions c '
                             'JOIN mascots m ON m.id=c.mascot_id '
                             'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                             (account_id,)).fetchone()
            self.assertEqual(row['name'], 'Sư tử')
            self.assertEqual(row['xp'], initial['state']['points'])
        self.assertEqual(lion.call('session')['state']['mascot'], 'lion')
        mine = next(row for row in lion.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'lion')

        # A supplied room payload cannot impersonate a different companion.
        room = lion.call('arena', {'action': 'create', 'public': True,
                                  'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'lion')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        lion.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'lion')
        lion.call('arena', {'action': 'leave', **room})
        lion.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'lion')

    def test_invalid_choices_and_reseed_preserve_lion_without_duplicate_or_xp_change(self):
        client, initial, _, _ = self.user()
        client.call('mascot', {'mascot': 'lion'})
        for value in ('su-tu', 'unknown', '', None, [], {}):
            with self.subTest(value=value), self.assertRaises(APIError) as caught:
                client.call('mascot', {'mascot': value})
            self.assertEqual(caught.exception.status, 400)
            current = client.call('session')['state']
            self.assertEqual(current['mascot'], 'lion')
            self.assertEqual(current['points'], initial['state']['points'])
        seed_catalog(self.path)
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Sư tử'").fetchone()[0], 1)
        current = client.call('session')['state']
        self.assertEqual(current['mascot'], 'lion')
        self.assertEqual(current['points'], initial['state']['points'])


if __name__ == '__main__':
    unittest.main()
