"""Five-minute room clocks and claim cleanup on isolated fixture DBs/HTTP."""
import http.client
import json
import threading
import unittest
from backend import platform_api as api
from backend.server import ThreadingHTTPServer
from backend.local_test_games import NativeLocalTestGames
import test_local_test_games as native
from test_group_room_http import QuietHandler


class WaitingRoomExpiryTests(unittest.TestCase):
    tearDown = native.NativeLocalTestGamesTests.tearDown
    actor = native.NativeLocalTestGamesTests.actor

    def setUp(self):
        native.NativeLocalTestGamesTests.setUp(self)
        self.clock = 1_800_000_000_000
        self.server.local_test_games.group_games.clock = lambda: self.clock
        self.server.game_claim_clock = lambda: self.clock

    def create(self, client, mode='capture_flag', key='waiting-create-001'):
        return client.call('group-games/rooms', {'mode': mode, 'requestKey': key})

    def test_both_modes_keep_created_deadline_across_poll_join_and_exact_boundary(self):
        for mode in ('capture_flag', 'animal_race'):
            with self.subTest(mode=mode):
                first, second = self.actor(), self.actor()
                opened = self.create(first, mode)
                room = opened['room']; expiry = self.clock + 300_000
                self.assertEqual(room['waitingExpiresAt'], expiry)
                self.assertEqual(opened['gameClaim']['waitingExpiresAt'], expiry)
                self.assertEqual(opened['gameClaim']['roomStatus'], 'waiting')
                self.clock += 120_000
                joined = second.call('group-games/join', {'code': room['code'], 'requestKey': 'waiting-join-001'})
                self.assertEqual(joined['room']['waitingExpiresAt'], expiry)
                self.clock = expiry - 1
                for client in (first, second):
                    view = client.call('group-games/rooms/' + room['id'])['room']
                    self.assertEqual(view['status'], 'waiting')
                    self.assertEqual(view['waitingExpiresAt'] - view['serverTime'], 1)
                    self.assertEqual(client.call('game-claim')['claim']['waitingExpiresAt'], expiry)
                self.clock = expiry
                # No room-page poll: the cross-page claim endpoint advances the
                # same authoritative clock and releases every member's claim.
                self.assertIsNone(first.call('game-claim')['claim'])
                self.assertIsNone(second.call('game-claim')['claim'])
                expired = first.call('group-games/rooms/' + room['id'])['room']
                self.assertEqual((expired['status'], expired['endReason']), ('cancelled', 'waiting_expired'))
                self.assertTrue(all(not p['forfeited'] for p in expired['players']))
                with api.connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM game_claims WHERE room_id=?', (room['id'],)).fetchone()[0], 0)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards WHERE room_id=?', (room['id'],)).fetchone()[0], 0)
                    self.assertEqual(db.execute('SELECT SUM(xp) FROM student_companions WHERE student_id IN (?,?)', (first.sid, second.sid)).fetchone()[0], 0)
                # A fresh intent may start another game after expiry.
                new = self.create(first, mode, 'waiting-reopen-001')
                self.assertNotEqual(new['room']['id'], room['id'])
                first.call('game-claim', {'action': 'leave', 'claimId': new['gameClaim']['claimId']})

    def test_listing_expiry_releases_all_claims_without_owner_polling(self):
        first, second, outsider = self.actor(), self.actor(), self.actor()
        opened = self.create(first); room = opened['room']
        second.call('group-games/join', {'code': room['code'], 'requestKey': 'listing-join-001'})
        self.clock = room['waitingExpiresAt']
        self.assertEqual(outsider.call('group-games/rooms?mode=capture_flag')['rooms'], [])
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM game_claims WHERE room_id=?', (room['id'],)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM game_claim_requests WHERE room_id=? AND status='active'", (room['id'],)).fetchone()[0], 0)

    def test_waiting_leave_is_free_and_active_leave_keeps_existing_forfeit(self):
        players = [self.actor() for _ in range(6)]
        opened = self.create(players[0]); room = opened['room']
        players[1].call('group-games/join', {'code': room['code'], 'requestKey': 'leave-join-001'})
        players[0].call('game-claim', {'action': 'leave', 'claimId': opened['gameClaim']['claimId']})
        remaining = players[1].call('group-games/rooms/' + room['id'])['room']
        self.assertEqual(remaining['status'], 'waiting')
        self.assertEqual([p['studentId'] for p in remaining['players']], [players[1].sid])
        self.assertFalse(remaining['players'][0]['forfeited'])
        for index in (0, 2, 3, 4):
            last = players[index].call('group-games/join', {'code': room['code'], 'requestKey': 'active-join-' + str(index)})
        self.assertEqual(last['room']['status'], 'playing')
        self.assertEqual(last['gameClaim']['roomStatus'], 'playing')
        active_claim = players[0].call('game-claim')['claim']
        self.assertEqual(active_claim['roomStatus'], 'playing')
        players[0].call('game-claim', {'action': 'leave', 'claimId': active_claim['claimId']})
        after = players[1].call('group-games/rooms/' + room['id'])['room']
        self.assertTrue(next(p for p in after['players'] if p['studentId'] == players[0].sid)['forfeited'])
        self.clock = room['waitingExpiresAt']
        still_playing = players[1].call('group-games/rooms/' + room['id'])['room']
        self.assertNotEqual(still_playing['endReason'], 'waiting_expired')

    def test_real_http_clock_expiry_on_claim_endpoint_allows_new_game(self):
        client = self.actor()
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        port = server.server_address[1]
        server.database_path = self.path; server.arena = self.server.arena
        server.native_python_backend = True; server.real_accounts = True; server.review_upgrades = False
        server.local_test_games = NativeLocalTestGames({port})
        server.local_test_games.group_games.clock = lambda: self.clock
        server.game_claim_clock = lambda: self.clock
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()

        def call(path, body=None):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            headers = {'Host': f'127.0.0.1:{port}', 'Origin': f'http://127.0.0.1:{port}',
                       'Cookie': client.headers['Cookie'], 'X-CSRF-Token': client.csrf}
            if body is not None: headers['Content-Type'] = 'application/json'
            try:
                connection.request('GET' if body is None else 'POST', '/api/v1/' + path,
                                   None if body is None else json.dumps(body), headers)
                response = connection.getresponse(); value = json.loads(response.read())
                self.assertEqual(response.status, 200, value.get('error'))
                return value
            finally: connection.close()
        try:
            first = call('group-games/rooms', {'mode': 'animal_race', 'requestKey': 'http-countdown-one'})
            expiry = first['room']['waitingExpiresAt']
            self.clock = expiry - 1
            claim = call('game-claim')['claim']
            self.assertEqual(claim['waitingExpiresAt'] - claim['serverTime'], 1)
            self.clock = expiry
            self.assertIsNone(call('game-claim')['claim'])
            reopened = call('group-games/rooms', {'mode': 'capture_flag', 'requestKey': 'http-countdown-two'})
            self.assertNotEqual(reopened['room']['id'], first['room']['id'])
        finally:
            server.shutdown(); server.server_close(); worker.join(5)
