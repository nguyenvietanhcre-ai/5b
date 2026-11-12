"""A saved Ngựa companion must round-trip through sessions and both arena views."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import test_platform_api as platform_tests
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, seed_catalog


class HorseMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = (Path(__file__).resolve().parents[1] / 'work' if os.name == 'nt'
                else Path(tempfile.gettempdir())) / 'horse-mascot-tests'
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
            return dict(db.execute(
                'SELECT c.mascot_id,c.xp,m.name FROM student_companions c '
                'JOIN mascots m ON m.id=c.mascot_id '
                'JOIN students s ON s.id=c.student_id WHERE s.account_id=?',
                (account_id,)).fetchone())

    def test_saved_horse_survives_login_and_reaches_both_arena_players(self):
        horse, initial, login, password = self.user()
        friend, friend_initial, _, _ = self.user()
        selected = horse.call('mascot', {'mascot': 'horse'})
        self.assertEqual(selected['state']['mascot'], 'horse')
        self.assertEqual(selected['state']['points'], initial['state']['points'])
        self.assertEqual(self.companion(initial['account']['id'])['name'], 'Ngựa')
        self.assertEqual(horse.call('session')['state']['mascot'], 'horse')
        for kind in ('battle', 'activity'):
            with self.subTest(ranking=kind):
                mine = next(row for row in horse.call(
                    f'leaderboard?kind={kind}&period=all')['rows'] if row['mine'])
                self.assertEqual(mine['mascot'], 'horse')
                self.assertEqual(mine['xp'], initial['state']['points'])

        friend.call('mascot', {'mascot': 'fox'})
        # Rooms must take each mascot from authenticated saved state; client
        # payloads must not disguise either participant or award arbitrary XP.
        room = horse.call('arena', {
            'action': 'create', 'public': True, 'scope': 'weekly',
            'mascot': 'fox', 'stats': {'mascot': 'fox', 'xp': 999999}})
        listed = next(row for row in friend.call('arena', {'action': 'list'})['rooms']
                      if row['code'] == room['code'])
        self.assertEqual((listed['mascot'], listed['xp']),
                         ('horse', initial['state']['points']))
        joined = friend.call('arena', {
            'action': 'join', 'code': room['code'], 'scope': 'weekly',
            'mascot': 'horse', 'stats': {'mascot': 'horse', 'xp': 999999}})
        horse.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        for client, credentials, expected in (
                (friend, joined, 'horse'), (horse, room, 'fox')):
            with self.subTest(view=expected):
                battle = client.call('arena', {'action': 'state', **credentials})['battle']
                self.assertEqual(battle['opponentMascot'], expected)
                self.assertEqual((battle['hp'], battle['opponentHp']), (100, 100))
        self.assertEqual(self.companion(friend_initial['account']['id'])['name'], 'Cáo Nâu')
        horse.call('arena', {'action': 'leave', **room})
        horse.call('auth/logout', {})
        restored = platform_tests.Client(self.server)
        self.assertEqual(restored.call('auth/login', {
            'login': login, 'password': password})['state']['mascot'], 'horse')
        self.assertEqual(restored.call('session')['state']['mascot'], 'horse')

    def test_reseed_and_rejected_choices_keep_horse_and_accumulated_xp(self):
        client, initial, _, _ = self.user()
        account_id = initial['account']['id']
        with connect(self.path, True) as db:
            db.execute('UPDATE student_companions SET xp=1240 WHERE student_id='
                       '(SELECT id FROM students WHERE account_id=?)', (account_id,))
        for code in ('sprout', 'fox', 'horse'):
            state = client.call('mascot', {'mascot': code})['state']
            self.assertEqual((state['mascot'], state['points']), (code, 1240))
        saved = self.companion(account_id)
        for invalid in ('ngua', 'Ngựa', 'unknown', '', None, [], {}, 1, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(APIError) as caught:
                    client.call('mascot', {'mascot': invalid})
                self.assertEqual(caught.exception.status, 400)
                self.assertEqual(self.companion(account_id), saved)
                self.assertEqual(client.call('session')['state']['mascot'], 'horse')
        seed_catalog(self.path)
        seed_catalog(self.path)
        with connect(self.path) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM mascots WHERE name='Ngựa'").fetchone()[0], 1)
        self.assertEqual(self.companion(account_id), saved)
        state = client.call('session')['state']
        self.assertEqual((state['mascot'], state['points']), ('horse', 1240))


if __name__ == '__main__':
    unittest.main()
