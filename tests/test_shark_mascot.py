"""Regression checks for the persisted Cá mập companion across API boundaries."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class SharkMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep Windows fixtures in the project; Docker already provides /tmp.
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'shark-mascot-tests'
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

    def companion(self, account_id):
        with connect(self.path) as db:
            row = db.execute(
                'SELECT c.mascot_id,c.xp,m.name FROM student_companions c '
                'JOIN mascots m ON m.id=c.mascot_id '
                'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                (account_id,)).fetchone()
            return dict(row)

    def test_shark_choice_survives_login_and_is_trusted_in_arena_and_ranking(self):
        shark, initial, login, password = self.user()
        friend, _, _, _ = self.user()
        account_id = initial['account']['id']
        selected = shark.call('mascot', {'mascot': 'ca-map'})
        self.assertEqual(selected['state']['mascot'], 'ca-map')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        self.assertEqual(self.companion(account_id)['name'], 'Cá mập')
        self.assertEqual(shark.call('session')['state']['mascot'], 'ca-map')
        for kind in ('battle', 'activity'):
            with self.subTest(ranking=kind):
                mine = next(row for row in shark.call(
                    f'leaderboard?kind={kind}&period=all')['rows'] if row['mine'])
                self.assertEqual(mine['mascot'], 'ca-map')
                self.assertEqual(mine['xp'], initial['state']['points'])

        friend.call('mascot', {'mascot': 'fox'})
        # Both the top-level choice and nested client stats must be replaced
        # with each authenticated account's saved companion and XP.
        room = shark.call('arena', {
            'action': 'create', 'public': True, 'scope': 'weekly',
            'mascot': 'fox', 'stats': {'mascot': 'fox', 'xp': 999999}})
        listing = friend.call('arena', {'action': 'list'})['rooms']
        listed = next(row for row in listing if row['code'] == room['code'])
        self.assertEqual(listed['mascot'], 'ca-map')
        self.assertEqual(listed['xp'], initial['state']['points'])
        joined = friend.call('arena', {
            'action': 'join', 'code': room['code'], 'scope': 'weekly',
            'mascot': 'ca-map', 'stats': {'mascot': 'ca-map', 'xp': 999999}})
        shark.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        self.assertEqual(friend.call('arena', {'action': 'state', **joined})[
            'battle']['opponentMascot'], 'ca-map')
        self.assertEqual(shark.call('arena', {'action': 'state', **room})[
            'battle']['opponentMascot'], 'fox')
        shark.call('arena', {'action': 'leave', **room})
        shark.call('auth/logout', {})
        resumed_client = platform_tests.Client(self.server)
        resumed = resumed_client.call('auth/login', {'login': login, 'password': password})
        self.assertEqual(resumed['state']['mascot'], 'ca-map')
        self.assertEqual(resumed_client.call('session')['state']['mascot'], 'ca-map')

    def test_reseed_and_invalid_choices_preserve_shark_id_and_existing_xp(self):
        client, initial, _, _ = self.user()
        account_id = initial['account']['id']
        with connect(self.path, True) as db:
            db.execute('UPDATE student_companions SET xp=1240 WHERE student_id='
                       '(SELECT id FROM students WHERE account_id=?)', (account_id,))
        # Default companions still round-trip before the newly added choice.
        for code in ('sprout', 'fox', 'ca-map'):
            state = client.call('mascot', {'mascot': code})['state']
            self.assertEqual(state['mascot'], code)
            self.assertEqual(state['points'], 1240)
        saved = self.companion(account_id)
        for value in ('shark', 'ca_map', 'Cá mập', 'unknown', '', None, [], {}, 1, True):
            with self.subTest(value=value):
                with self.assertRaises(APIError) as caught:
                    client.call('mascot', {'mascot': value})
                self.assertEqual(caught.exception.status, 400)
                state = client.call('session')['state']
                self.assertEqual((state['mascot'], state['points']), ('ca-map', 1240))
                self.assertEqual(self.companion(account_id), saved)
        seed_catalog(self.path)
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM mascots WHERE name='Cá mập'").fetchone()[0], 1)
        self.assertEqual(self.companion(account_id), saved)
        state = client.call('session')['state']
        self.assertEqual((state['mascot'], state['points']), ('ca-map', 1240))


if __name__ == '__main__':
    unittest.main()
