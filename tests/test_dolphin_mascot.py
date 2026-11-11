import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class DolphinMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'dolphin-mascot-tests'
        work.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=work)
        cls.path = Path(cls.directory.name) / 'fixture.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=False, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    user = platform_tests.PlatformTests.user

    def test_dolphin_selection_persists_and_authenticated_choice_reaches_arena(self):
        dolphin, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = dolphin.call('mascot', {'mascot': 'dolphin'})
        self.assertEqual(selected['state']['mascot'], 'dolphin')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        mine = next(row for row in dolphin.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'dolphin')
        # The server derives the opponent's mascot from the saved selection.
        room = dolphin.call('arena', {'action': 'create', 'public': True,
                                     'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'dolphin')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        dolphin.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'dolphin')
        dolphin.call('arena', {'action': 'leave', **room})
        dolphin.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'dolphin')

    def test_seed_is_idempotent_and_rejected_choices_keep_dolphin(self):
        client, _, _, _ = self.user()
        client.call('mascot', {'mascot': 'dolphin'})
        seed_catalog(self.path)
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Cá heo'").fetchone()[0], 1)
        for value in ('ca-heo', 'unknown', '', None, [], {}):
            with self.subTest(value=value):
                with self.assertRaises(APIError) as caught:
                    client.call('mascot', {'mascot': value})
                self.assertEqual(caught.exception.status, 400)
                self.assertEqual(client.call('session')['state']['mascot'], 'dolphin')


if __name__ == '__main__':
    unittest.main()
