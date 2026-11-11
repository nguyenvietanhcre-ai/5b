"""Bạch tuộc selection persists and reaches the authenticated arena identity."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class OctopusMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'octopus-mascot-tests'
        base.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=base)
        cls.path = Path(cls.directory.name) / 'platform.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=True, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    user = platform_tests.PlatformTests.user

    def test_octopus_identity_persists_and_server_ignores_forged_mascot(self):
        client, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = client.call('mascot', {'mascot': 'octopus'})
        self.assertEqual(selected['state']['mascot'], 'octopus')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        self.assertEqual(client.call('session')['state']['mascot'], 'octopus')
        mine = next(row for row in client.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])
        self.assertEqual(mine['mascot'], 'octopus')
        room = client.call('arena', {'action': 'create', 'public': True, 'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])['mascot'], 'octopus')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        client.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        battle = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(battle['opponentMascot'], 'octopus')
        self.assertEqual((battle['hp'], battle['opponentHp']), (100, 100))
        client.call('arena', {'action': 'leave', **room})
        client.call('auth/logout', {})
        resumed = platform_tests.Client(self.server).call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'octopus')

    def test_seed_preserves_existing_choices_and_rejects_invalid_values(self):
        client, _, _, _ = self.user()
        for code in ('sprout', 'fox', 'rabbit', 'octopus'):
            self.assertEqual(client.call('mascot', {'mascot': code})['state']['mascot'], code)
        for value in ('bach-tuoc', 'unknown', '', None, [], {}):
            with self.subTest(value=value), self.assertRaises(APIError) as caught:
                client.call('mascot', {'mascot': value})
            self.assertEqual(caught.exception.status, 400)
            self.assertEqual(client.call('session')['state']['mascot'], 'octopus')
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM mascots WHERE name='Bạch tuộc'").fetchone()[0], 1)
        self.assertEqual(client.call('session')['state']['mascot'], 'octopus')


if __name__ == '__main__':
    unittest.main()
