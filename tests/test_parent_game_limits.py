"""Family game controls against authentic family sessions and disposable main DBs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
import os
import secrets
import threading
import unittest
from unittest.mock import patch

from backend import platform_api as api
from backend.local_test_games import NativeLocalTestGames
from test_family_accounts import FamilyClient
import test_family_accounts as fixtures


ENDPOINT = 'children/game-limits'
PARENT_USAGE_ENDPOINT = 'parent/game-limits'
STUDENT_ENDPOINT = 'game-limits'
GAMES = ('duel', 'capture_flag', 'animal_race')


class ParentGameLimitsTests(unittest.TestCase):
    PASSWORD = fixtures.FamilyAccountsTests.PASSWORD
    consent = fixtures.FamilyAccountsTests.consent
    register_body = fixtures.FamilyAccountsTests.register_body
    register = fixtures.FamilyAccountsTests.register
    full = fixtures.FamilyAccountsTests.full
    add_child = fixtures.FamilyAccountsTests.add_child
    assert_denied = fixtures.FamilyAccountsTests.assert_denied

    def setUp(self):
        fixtures.FamilyAccountsTests.setUp(self)
        server = object.__new__(HTTPServer)
        server.__dict__.update(vars(self.server))
        server.server_address = ('0.0.0.0', 8000)
        server.native_python_backend = True
        server.local_test_games = NativeLocalTestGames({8765})
        self.server = server
        environment = patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '1'})
        environment.start()
        self.addCleanup(environment.stop)
        self.child, state = self.register()
        self.sid = state['selectedChildId']
        self.parent = self.login_device()
        self.full(self.parent)

    def login_device(self):
        device = FamilyClient(self.server)
        device.call('login', {'email': self.email, 'password': self.PASSWORD})
        return device

    def save(self, sid=None, **values):
        return self.parent.call(ENDPOINT, {'childId': self.sid if sid is None else sid,
                                           'limits': dict.fromkeys(GAMES) | values})

    def limits(self, sid=None):
        return self.parent.call(f'{ENDPOINT}?childId={self.sid if sid is None else sid}')

    def game(self, game, sid=None):
        return next(row for row in self.limits(sid)['games'] if row['id'] == game)

    def admission(self, client, game, action, code=None, request_key=None):
        body = {'requestKey': request_key or secrets.token_hex(16)}
        if code:
            body['code'] = code
        if game == 'duel':
            body['scope'] = 'all'
            if action == 'bot':
                return client.learner('bot/start', body)
            return client.learner('arena', {**body, 'action': action, 'public': action != 'create'})
        if action == 'join':
            return client.learner('group-games/join', body)
        return client.learner('group-games/quick' if action == 'quick' else 'group-games/rooms',
                              {**body, 'mode': game, 'playMode': 'bot' if action == 'bot' else 'human'})

    @staticmethod
    def leave(client, game_result):
        return client.learner('game-claim', {'action': 'leave', 'claimId': game_result['gameClaim']['claimId']})

    def snapshot(self, *tables):
        with api.connect(self.path) as db:
            return {table: [tuple(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
                    for table in tables}

    def test_parent_overview_and_poll_use_the_same_vietnam_day_and_ledger(self):
        sibling = self.add_child(self.parent, grade=5)['addedChildId']
        self.save(duel=1, capture_flag=0)
        self.save(sibling, animal_race=3)
        midnight = int(datetime(2026, 11, 19, 17, tzinfo=timezone.utc).timestamp() * 1000)
        self.server.game_claim_clock = lambda: midnight - 1
        waiting = self.admission(self.child, 'duel', 'create')
        self.assertEqual(waiting['gameClaim']['roomStatus'], 'waiting')

        with patch.object(self.server, 'game_claim_clock', side_effect=[midnight - 1]) as clock:
            overview = self.parent.call('parent/overview')
        clock.assert_called_once()
        summary = {item['id']: item['gameUsage'] for item in overview['overview']}
        self.assertEqual(set(summary), {self.sid, sibling})
        self.assertEqual(overview['gameUsage'], {'day': '2026-11-19', 'timeZone': 'Asia/Ho_Chi_Minh',
            'serverTime': '2026-11-19T23:59:59.999+07:00', 'resetsAt': '2026-11-20T00:00:00.000+07:00'})
        self.assertEqual(summary[self.sid], self.limits())
        self.assertEqual([(g['used'], g['remaining']) for g in summary[self.sid]['games']], [(1, 0), (0, 0), (0, None)])
        self.assertEqual([(g['used'], g['remaining']) for g in summary[sibling]['games']], [(0, None), (0, None), (0, 3)])

        tables = self.snapshot('family_devices', 'child_game_limits', 'game_claim_requests', 'game_claims', 'daily_usage')
        with patch.object(self.server, 'game_claim_clock', side_effect=[midnight]) as clock:
            usage = self.parent.call(PARENT_USAGE_ENDPOINT)
        clock.assert_called_once()
        self.assertEqual(self.snapshot(*tables), tables)
        self.assertEqual(usage['day'], '2026-11-20')
        self.assertEqual(usage['serverTime'], overview['gameUsage']['resetsAt'])
        self.assertEqual(usage['resetsAt'], '2026-11-21T00:00:00.000+07:00')
        self.assertEqual({item['childId'] for item in usage['children']}, {self.sid, sibling})
        own = next(item for item in usage['children'] if item['childId'] == self.sid)
        self.assertEqual([(g['used'], g['remaining']) for g in own['games']], [(0, 1), (0, 0), (0, None)])

    def test_parent_usage_rejects_cross_family_selectors_and_does_not_extend_pin(self):
        self.email = 'other-' + secrets.token_hex(6) + '@example.test'
        stranger, state = self.register()
        self.full(stranger)
        stranger_sid = state['selectedChildId']
        self.assertEqual([c['childId'] for c in stranger.call(PARENT_USAGE_ENDPOINT)['children']], [stranger_sid])
        self.assertEqual([c['childId'] for c in self.parent.call(PARENT_USAGE_ENDPOINT)['children']], [self.sid])
        self.assert_denied(lambda: self.parent.call(f'{PARENT_USAGE_ENDPOINT}?childId={stranger_sid}'), (400,))
        self.assert_denied(lambda: self.parent.call(PARENT_USAGE_ENDPOINT, {'childId': stranger_sid}), (405,))
        self.assert_denied(lambda: FamilyClient(self.server).call(PARENT_USAGE_ENDPOINT), (401,))
        self.assert_denied(lambda: self.child.call(PARENT_USAGE_ENDPOINT), (403,))
        missing = self.parent.copy_capability()
        missing.context = ''
        missing.headers.pop('X-Family-Context', None)
        self.assertTrue(self.assert_denied(lambda: missing.call(PARENT_USAGE_ENDPOINT), (403,)).familyAccessChanged)
        older_overview = missing.call('parent/overview')
        self.assertNotIn('gameUsage', older_overview)
        self.assertNotIn('gameUsage', older_overview['overview'][0])

        with api.connect(self.path, True) as db:
            device = fixtures.family._row(self.parent, db)
            db.execute("UPDATE family_devices SET scope='parent_read' WHERE id=?", (device['id'],))
        self.assert_denied(lambda: self.parent.call(PARENT_USAGE_ENDPOINT), (403,))
        self.assertNotIn('gameUsage', self.parent.call('parent/overview'))

        moment = api.now()
        with patch.object(api, 'now', return_value=moment):
            self.full(self.parent)
        before = self.snapshot('family_devices')
        with patch.object(api, 'now', return_value=moment + fixtures.family.PARENT_IDLE - timedelta(seconds=1)):
            self.parent.call(PARENT_USAGE_ENDPOINT)
        with patch.object(api, 'now', return_value=moment + fixtures.family.PARENT_IDLE):
            error = self.assert_denied(lambda: self.parent.call(PARENT_USAGE_ENDPOINT), (403,))
            self.assertEqual(error.code, 'family_parent_pin_required')
        self.assertEqual(self.snapshot(*before), before)

    def test_student_projection_shares_the_ledger_and_does_not_write(self):
        self.save(duel=1, capture_flag=0)
        parent_games = self.limits()['games']
        before = self.snapshot('child_game_limits', 'game_claim_requests', 'game_claims', 'daily_usage',
                               'family_devices')
        initial = self.child.learner(STUDENT_ENDPOINT)
        self.assertEqual(set(initial), {'childId', 'day', 'timeZone', 'serverTime', 'resetsAt', 'games'})
        self.assertEqual(initial['childId'], self.sid)
        self.assertEqual(initial['timeZone'], 'Asia/Ho_Chi_Minh')
        self.assertEqual(initial['games'], parent_games)
        self.assertEqual([(game['limit'], game['used'], game['remaining']) for game in initial['games']],
                         [(1, 0, 1), (0, 0, 0), (None, 0, None)])
        self.assertEqual(before, self.snapshot(*before))

        play = self.admission(self.child, 'duel', 'bot')
        after = self.child.learner(STUDENT_ENDPOINT)
        self.assertEqual(after['games'], self.limits()['games'])
        self.assertEqual([(game['used'], game['remaining']) for game in after['games']],
                         [(1, 0), (0, 0), (0, None)])
        self.leave(self.child, play)
        error = self.assert_denied(lambda: self.admission(self.child, 'duel', 'bot'), (429,))
        self.assertEqual(error.code, 'parent_game_limit')
        self.assertEqual(self.child.learner(STUDENT_ENDPOINT)['games'], after['games'])

    def test_student_projection_requires_current_child_context_and_cannot_select_another_student(self):
        sibling = self.add_child(self.parent, grade=5)['addedChildId']
        self.save(duel=0)
        self.save(sibling, duel=7)
        sibling_device = self.login_device()
        sibling_device.call('select', {'childId': sibling, 'pin': '4321'})
        self.assertEqual(sibling_device.learner(STUDENT_ENDPOINT)['games'][0]['remaining'], 7)

        self.email = 'other-' + secrets.token_hex(6) + '@example.test'
        outsider, state = self.register()
        foreign_sid = state['selectedChildId']
        self.assertIsNone(outsider.learner(STUDENT_ENDPOINT)['games'][0]['remaining'])
        for sid in (self.sid, sibling, foreign_sid):
            self.assert_denied(lambda: self.child.learner(f'{STUDENT_ENDPOINT}?childId={sid}'), (400,))
        self.assertEqual(self.child.learner(STUDENT_ENDPOINT)['games'][0]['remaining'], 0)
        self.assert_denied(lambda: outsider.learner(f'{STUDENT_ENDPOINT}?childId={self.sid}'), (400,))
        self.assert_denied(lambda: self.child.learner(STUDENT_ENDPOINT, {'childId': sibling}), (405,))
        self.assert_denied(lambda: FamilyClient(self.server).learner(STUDENT_ENDPOINT), (401,))
        self.assert_denied(lambda: self.parent.learner(STUDENT_ENDPOINT), (403,))
        missing = self.child.copy_capability()
        missing.context = ''
        self.assertTrue(self.assert_denied(lambda: missing.learner(STUDENT_ENDPOINT), (403,)).familyAccessChanged)

        original = self.child.copy_capability()
        self.full(self.child)
        self.child.call('devices/configure', {'remember': True, 'childOnly': True, 'childId': self.sid})
        self.assert_denied(lambda: self.child.learner(STUDENT_ENDPOINT), (403,))
        self.assert_denied(lambda: self.child.call('select', {'childId': sibling, 'pin': '4321'}), (404,))
        self.child.call('select', {'childId': self.sid, 'pin': '4321'})
        self.assertEqual(self.child.learner(STUDENT_ENDPOINT)['childId'], self.sid)
        self.assert_denied(lambda: original.learner(STUDENT_ENDPOINT), (401,))
        original.headers['Cookie'] = self.child.headers['Cookie']
        self.assertTrue(self.assert_denied(lambda: original.learner(STUDENT_ENDPOINT), (403,)).familyAccessChanged)

    def test_legacy_projection_is_own_and_does_not_bypass_revoked_family_capability(self):
        legacy = FamilyClient(self.server)
        result = legacy.learner('auth/register', {'login': 'legacy-' + secrets.token_hex(6),
                                                 'password': self.PASSWORD, 'name': 'Học sinh cũ',
                                                 'birthYear': api.academic()[0] - 10})
        projection = legacy.learner(STUDENT_ENDPOINT)
        with api.connect(self.path) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (result['account']['id'],)).fetchone()[0]
        self.assertEqual(projection['childId'], sid)
        self.assertNotEqual(sid, self.sid)
        self.assertTrue(all(game['limit'] is None and game['used'] == 0 for game in projection['games']))

        self.full(self.child)
        revoked = self.child.copy_capability()
        self.child.call('logout', {})
        revoked.headers['Cookie'] += '; ' + legacy.headers['Cookie']
        self.assert_denied(lambda: revoked.learner(STUDENT_ENDPOINT), (401,))
        self.assertEqual(legacy.learner(STUDENT_ENDPOINT)['childId'], sid)

    def test_parent_full_context_csrf_exact_owner_zero_null_and_bounds(self):
        initial = self.limits()
        self.assertEqual(initial['childId'], self.sid)
        self.assertEqual(initial['maxLimit'], 1000)
        self.assertEqual([(r['id'], r['label'], r['limit'], r['used'], r['remaining']) for r in initial['games']],
                         [('duel', 'Đấu trí', None, 0, None), ('capture_flag', 'Cướp Cờ', None, 0, None),
                          ('animal_race', 'Đua Thú', None, 0, None)])
        sibling_state = self.add_child(self.parent, grade=5)
        sibling = sibling_state['addedChildId']
        self.save(duel=0, capture_flag=1000)
        self.save(sibling, animal_race=3)
        self.assertEqual(self.game('duel')['remaining'], 0)
        self.assertEqual(self.game('capture_flag')['remaining'], 1000)
        self.assertEqual(self.game('animal_race', sibling)['remaining'], 3)
        self.assertIsNone(self.game('duel', sibling)['limit'])
        self.assertIsNone(self.game('animal_race')['limit'])

        old_email = self.email
        self.email = 'other-' + secrets.token_hex(6) + '@example.test'
        outsider, outgoing = self.register()
        self.email = old_email
        self.full(outsider)
        foreign_sid = outgoing['selectedChildId']
        self.assert_denied(lambda: self.limits(foreign_sid), (404,))
        self.assert_denied(lambda: self.save(foreign_sid, duel=5), (404,))
        payload = {'childId': self.sid, 'limits': dict.fromkeys(GAMES)}
        unauthed = FamilyClient(self.server)
        for device, status in ((self.child, 403), (unauthed, 401)):
            self.assert_denied(lambda: device.call(f'{ENDPOINT}?childId={self.sid}'), (status,))
            self.assert_denied(lambda: device.call(ENDPOINT, payload), (status,))
        reader = self.parent.copy_capability()
        reader.context = 'stale-context'
        error = self.assert_denied(lambda: reader.call(f'{ENDPOINT}?childId={self.sid}'), (403,))
        self.assertTrue(error.familyAccessChanged)
        self.assert_denied(lambda: reader.call(ENDPOINT, payload), (403,))
        reader = self.parent.copy_capability()
        reader.csrf = 'stale-csrf'
        self.assert_denied(lambda: reader.call(ENDPOINT, payload), (403,))
        spoofed = self.parent.copy_capability()
        spoofed.headers['Origin'] = 'https://different.example.test'
        self.assert_denied(lambda: spoofed.call(ENDPOINT, payload), (403,))
        for invalid in (True, '0', -1, 1001, 1.5, [], {}):
            with self.subTest(invalid=invalid):
                self.assert_denied(lambda: self.save(duel=invalid), (400,))
        self.assert_denied(lambda: self.parent.call(ENDPOINT, {'childId': self.sid, 'limits': {'duel': 2}}), (400,))
        self.assert_denied(lambda: self.parent.call(ENDPOINT, {'limits': dict.fromkeys(GAMES)}), (400,))
        self.assert_denied(lambda: self.parent.call(ENDPOINT + f'?childId={self.sid}&childId={sibling}'), (400,))
        self.assertEqual(self.game('duel')['limit'], 0)

        self.save()
        self.assertIsNone(self.game('duel')['limit'])
        with api.connect(self.path, True) as db:
            device = fixtures.family._row(self.parent, db)
            db.execute("UPDATE family_devices SET scope='parent_read' WHERE id=?", (device['id'],))
        self.assert_denied(self.limits, (403,))
        self.assert_denied(self.save, (403,))

    def test_all_games_share_bot_and_human_counts_and_preserve_ongoing_rounds(self):
        host = self.login_device()
        host_sid = self.add_child(self.parent, grade=5)['addedChildId']
        host.call('select', {'childId': host_sid, 'pin': '4321'})
        for game in GAMES:
            with self.subTest(game=game):
                # Existing successful admissions count even when the limit
                # was previously blank. Lowering limits preserves live rooms.
                self.save()
                nonce = secrets.token_hex(16)
                bot = self.admission(self.child, game, 'bot', request_key=nonce)
                self.save(**{game: 0})
                self.assertEqual(self.admission(self.child, game, 'bot', request_key=nonce)['gameClaim']['claimId'],
                                 bot['gameClaim']['claimId'])
                if game == 'duel':
                    resumed = self.child.learner('game-claim', {'action': 'touch', 'claimId': bot['gameClaim']['claimId']})
                    self.assertEqual(resumed['claim']['playMode'], 'bot')
                else:
                    room = bot['room']
                    reply = self.child.learner(f"group-games/rooms/{room['id']}/answer", {
                        'round': room['round'], 'answer': '1', 'requestKey': secrets.token_hex(16)})
                    self.assertEqual(reply['room']['id'], room['id'])
                self.leave(self.child, bot)
                self.assertEqual(self.game(game)['used'], 1)
                self.assert_denied(lambda: self.admission(self.child, game, 'quick'), (429,))

                self.save(**{game: 2})
                waiting = self.admission(host, game, 'create')
                code = waiting['code'] if game == 'duel' else waiting['room']['code']
                joined = self.admission(self.child, game, 'join', code)
                self.assertEqual(self.game(game)['used'], 2)
                self.assertEqual(self.game(game)['remaining'], 0)
                self.save(**{game: 0})
                if game == 'duel':
                    begun = host.learner('arena', {'action': 'accept', 'code': code, 'token': waiting['token']})
                    self.assertEqual(begun['status'], 'preparing')
                    state = self.child.learner('arena', {'action': 'state', 'code': code, 'token': joined['token']})
                    self.assertEqual(state['status'], 'preparing')
                self.leave(self.child, joined)
                self.assert_denied(lambda: self.admission(self.child, game, 'bot'), (429,))
                self.assertEqual(self.game(game)['used'], 2)
                self.assertEqual(self.game(game, host_sid)['used'], 1)
                live = host.learner('game-claim')['claim']
                if live:
                    self.leave(host, {'gameClaim': live})

    def test_rejected_create_join_quick_and_bot_leave_no_room_nonce_or_quota(self):
        host = self.login_device()
        sid = self.add_child(self.parent, grade=5)['addedChildId']
        host.call('select', {'childId': sid, 'pin': '4321'})
        self.save(**dict.fromkeys(GAMES, 0))
        for game in GAMES:
            with self.subTest(game=game):
                waiting = self.admission(host, game, 'quick')
                code = waiting['code'] if game == 'duel' else waiting['room']['code']
                before = self.snapshot('daily_usage', 'game_claim_requests', 'group_game_requests',
                                       'arena_members', 'duel_players', 'duels')
                for action in ('create', 'quick', 'join', 'bot'):
                    nonce = secrets.token_hex(16)
                    error = self.assert_denied(lambda: self.admission(self.child, game, action,
                                                                     code if action == 'join' else None, nonce), (429,))
                    self.assertEqual(error.code, 'parent_game_limit')
                self.assertEqual(self.game(game)['used'], 0)
                self.assertEqual(before, self.snapshot(*before))
                self.assertIsNone(self.child.learner('game-claim')['claim'])
                if game == 'duel':
                    room = self.server.arena.rooms[code]
                    self.assertEqual(room['status'], 'waiting')
                    self.assertEqual(len(room['players']), 1)
                else:
                    room = host.learner('group-games/rooms/' + waiting['room']['id'])['room']
                    self.assertEqual(room['status'], 'waiting')
                    self.assertEqual(len(room['players']), 1)
                self.leave(host, waiting)

    def test_failed_source_or_bad_room_followed_by_success_with_same_nonce(self):
        self.save(**dict.fromkeys(GAMES, 1))
        before = self.snapshot('daily_usage', 'game_claim_requests', 'game_claims', 'group_game_rooms')
        for game in GAMES:
            self.assert_denied(lambda: self.admission(self.child, game, 'join', 'BAD12345'), (404,))
        duel_nonce = secrets.token_hex(16)
        with patch.object(self.server.local_test_games.bot, 'questions', return_value=[]):
            self.assert_denied(lambda: self.admission(self.child, 'duel', 'bot', request_key=duel_nonce), (503,))
        self.assertEqual(before, self.snapshot(*before))
        result = self.admission(self.child, 'duel', 'bot', request_key=duel_nonce)
        self.assertEqual(self.game('duel')['used'], 1)
        self.leave(self.child, result)

    def test_same_child_across_two_authenticated_devices_only_gets_last_slot_once(self):
        other = self.login_device()
        other.call('select', {'childId': self.sid, 'pin': '4321'})
        self.assertNotEqual(self.child.headers['Cookie'], other.headers['Cookie'])
        self.save(animal_race=1)
        barrier = threading.Barrier(2)

        def try_last_play(device):
            barrier.wait(timeout=5)
            try:
                return 200, self.admission(device, 'animal_race', 'bot')
            except api.APIError as error:
                return error.status, None

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(try_last_play, (self.child, other)))
        self.assertEqual(sorted(status for status, _ in results), [200, 409])
        self.assertEqual(self.game('animal_race')['used'], 1)
        winner = next(result for status, result in results if status == 200)
        self.leave(other, winner)
        self.assert_denied(lambda: self.admission(self.child, 'animal_race', 'create'), (429,))
        self.assertEqual(len(self.snapshot('game_claim_requests')['game_claim_requests']), 1)

    def test_vietnam_midnight_rejoin_deduplicates_even_on_new_day(self):
        host = self.login_device()
        sid = self.add_child(self.parent, grade=5)['addedChildId']
        host.call('select', {'childId': sid, 'pin': '4321'})
        utc = datetime(2026, 11, 19, 17, tzinfo=timezone.utc)
        clock = int((utc - timedelta(milliseconds=1)).timestamp() * 1000)
        self.server.game_claim_clock = lambda: clock
        older = self.admission(host, 'capture_flag', 'create')
        code = older['room']['code']
        joined = self.admission(self.child, 'capture_flag', 'join', code)
        self.leave(self.child, joined)
        self.save(capture_flag=1)
        self.assertEqual(self.limits()['day'], '2026-11-19')
        self.assertEqual(self.game('capture_flag')['remaining'], 0)
        before_midnight = self.child.learner(STUDENT_ENDPOINT)
        self.assertEqual(before_midnight['day'], '2026-11-19')
        self.assertEqual(before_midnight['serverTime'], '2026-11-19T23:59:59.999+07:00')
        self.assertEqual(before_midnight['resetsAt'], '2026-11-20T00:00:00.000+07:00')
        self.assertEqual(before_midnight['games'][1]['remaining'], 0)
        clock += 1
        self.assertEqual(self.limits()['day'], '2026-11-20')
        self.assertEqual(self.game('capture_flag')['remaining'], 1)
        after_midnight = self.child.learner(STUDENT_ENDPOINT)
        self.assertEqual(after_midnight['day'], '2026-11-20')
        self.assertEqual(after_midnight['serverTime'], before_midnight['resetsAt'])
        self.assertEqual(after_midnight['resetsAt'], '2026-11-21T00:00:00.000+07:00')
        self.assertEqual(after_midnight['games'][1]['remaining'], 1)
        joined_again = self.admission(self.child, 'capture_flag', 'join', code)
        self.assertEqual(joined_again['room']['id'], joined['room']['id'])
        self.assertEqual(self.game('capture_flag')['used'], 0)
        self.leave(self.child, joined_again)
        bot = self.admission(self.child, 'capture_flag', 'bot')
        self.assertEqual(self.game('capture_flag')['used'], 1)
        self.leave(self.child, bot)
        self.assert_denied(lambda: self.admission(self.child, 'capture_flag', 'create'), (429,))
        self.assertEqual(len(self.snapshot('game_claim_requests')['game_claim_requests']), 4)

    def test_settings_do_not_reset_existing_product_limits_or_historical_rows(self):
        for _ in range(6):
            self.leave(self.child, self.admission(self.child, 'duel', 'bot'))
        history = self.snapshot('daily_usage', 'game_claim_requests')
        self.assertEqual(len(history['daily_usage']), 6)
        self.assertEqual(self.game('duel')['used'], 6)
        self.save(duel=5)
        self.assert_denied(lambda: self.admission(self.child, 'duel', 'bot'), (429,))
        self.save()
        self.assertEqual(self.game('duel')['used'], 6)
        with patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '0'}):
            error = self.assert_denied(lambda: self.admission(self.child, 'duel', 'bot'), (429,))
            self.assertFalse(hasattr(error, 'code'))
        self.assertEqual(history, self.snapshot(*history))


if __name__ == '__main__':
    unittest.main()
