"""Ong remains the authenticated companion in sessions and arena rooms."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class BeeMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'bee-mascot-tests'
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

    def test_bee_selection_survives_login_and_opponent_room_state(self):
        bee, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = bee.call('mascot', {'mascot': 'bee'})
        self.assertEqual(selected['state']['mascot'], 'bee')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        self.assertEqual(bee.call('session')['state']['mascot'], 'bee')
        mine = next(row for row in bee.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'bee')
        # The room takes the authenticated stored mascot, even if the body spoofs fox.
        room = bee.call('arena', {'action': 'create', 'public': True,
                                 'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'bee')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        bee.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        self.assertEqual(friend.call('arena', {'action': 'state', **joined})['battle']['opponentMascot'], 'bee')
        bee.call('arena', {'action': 'leave', **room})
        bee.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'bee')

    def test_seed_is_idempotent_and_invalid_choice_keeps_bee(self):
        client, _, _, _ = self.user()
        client.call('mascot', {'mascot': 'bee'})
        for invalid in ('ong', '', None, [], {}):
            with self.subTest(invalid=invalid), self.assertRaises(APIError) as caught:
                client.call('mascot', {'mascot': invalid})
            self.assertEqual(caught.exception.status, 400)
            self.assertEqual(client.call('session')['state']['mascot'], 'bee')
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Ong'").fetchone()[0], 1)
        self.assertEqual(client.call('session')['state']['mascot'], 'bee')


if __name__ == '__main__':
    unittest.main()
