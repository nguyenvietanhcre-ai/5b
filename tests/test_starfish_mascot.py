"""The saved Sao biển companion remains authoritative across sessions and matches."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class StarfishMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'starfish-mascot-tests'
        root.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=root)
        cls.path = Path(cls.directory.name) / 'platform.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server = SimpleNamespace(database_path=cls.path, review_upgrades=True, arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    user = platform_tests.PlatformTests.user

    def test_saved_starfish_survives_login_and_is_seen_by_both_arena_players(self):
        owner, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        selected = owner.call('mascot', {'mascot': 'starfish'})
        self.assertEqual(selected['state']['mascot'], 'starfish')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        with connect(self.path) as db:
            before = dict(db.execute('SELECT name,id FROM mascots'))
            saved = db.execute('SELECT m.name FROM student_companions c '
                               'JOIN mascots m ON m.id=c.mascot_id '
                               'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                               (initial['account']['id'],)).fetchone()[0]
        self.assertEqual(saved, 'Sao biển')
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(dict(db.execute('SELECT name,id FROM mascots')), before)
            self.assertEqual(db.execute('SELECT count(*) FROM mascots WHERE name=?',
                                        ('Sao biển',)).fetchone()[0], 1)
        owner.call('auth/logout', {})
        owner = platform_tests.Client(self.server)
        self.assertEqual(owner.call('auth/login', {'login': login, 'password': password})
                         ['state']['mascot'], 'starfish')
        for invalid in ('sao-bien', None, []):
            with self.subTest(invalid=invalid), self.assertRaises(APIError):
                owner.call('mascot', {'mascot': invalid})
            self.assertEqual(owner.call('session')['state']['mascot'], 'starfish')
        # A request body cannot replace the actual companion used for a room.
        room = owner.call('arena', {'action': 'create', 'public': True,
                                    'scope': 'weekly', 'mascot': 'fox'})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code'] == room['code'])
                         ['mascot'], 'starfish')
        joined = friend.call('arena', {'action': 'join', 'code': room['code'], 'scope': 'weekly'})
        owner.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        mine = owner.call('arena', {'action': 'state', **room})['battle']
        theirs = friend.call('arena', {'action': 'state', **joined})['battle']
        self.assertEqual(theirs['opponentMascot'], 'starfish')
        self.assertEqual(mine['opponentMascot'], 'sprout')
        self.assertEqual((mine['hp'], mine['opponentHp']), (100, 100))
        self.assertEqual((theirs['hp'], theirs['opponentHp']), (100, 100))
        owner.call('arena', {'action': 'leave', **room})


if __name__ == '__main__':
    unittest.main()
