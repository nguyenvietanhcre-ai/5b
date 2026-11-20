"""Trial tests use only fresh SQLite fixtures under the approved work tree."""
import io
import json
import secrets
import shutil
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend import trial_experience as trial
from backend.database import initialize
from backend.platform_api import APIError, connect


class Client:
    def __init__(self, server):
        self.server = server
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.api_headers = {}
        self.cookies = {}
        self.csrf = ''
        self.generation = None
        self.client_address = ('127.0.0.1', 1)

    def call(self, path, body=None, csrf=None):
        self.path = trial.BASE + path
        self.headers['Cookie'] = '; '.join(k + '=' + v for k, v in self.cookies.items())
        self.headers['X-Trial-CSRF'] = self.csrf if csrf is None else csrf
        self.api_headers = {}
        with patch.object(trial, 'clock', return_value=self.server.at):
            result, status = trial.route(self, 'GET' if body is None else 'POST', self.path, body)
        cookie = self.api_headers.get('Set-Cookie', '').split(';')[0]
        if '=' in cookie:
            key, value = cookie.split('=', 1)
            self.cookies[key] = value
        if result.get('csrf'):
            self.csrf = result['csrf']
        if result.get('session'):
            self.generation = result['session']['generation']
        return result, status

    def post(self, path, **values):
        return self.call(path, {'generation': self.generation, **values})

    def copy(self):
        other = Client(self.server)
        other.cookies, other.csrf, other.generation = dict(self.cookies), self.csrf, self.generation
        return other


class TrialTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        (root / 'qa').mkdir(exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix='trial-qa-', dir=root / 'qa'))
        self.path = self.directory / 'test.sqlite3'
        initialize(self.path)
        self.server = SimpleNamespace(database_path=self.path, at=1_800_000_000_000)
        self.client = Client(self.server)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def start(self, client=None):
        return (client or self.client).call('session', {})[0]

    def error(self, code, fn):
        with self.assertRaises(APIError) as caught:
            fn()
        self.assertEqual(caught.exception.status, code)

    def test_finite_arithmetic_exact_and_truthful_review(self):
        content = trial.load_content()
        self.assertEqual(len(content['questions']), 30)
        self.assertEqual(content['independentTeacherReview'], 'pending')
        for q in content['questions']:
            v = q['verification']
            args = [Fraction(x) for x in v['operands']]
            op = v['operation']
            operations = {'percent_of': lambda: args[0] * args[1] / 100,
                'add': lambda: sum(args), 'subtract': lambda: args[0] - args[1],
                'multiply': lambda: args[0] * args[1], 'divide': lambda: args[0] / args[1],
                'percent_ratio': lambda: args[0] / args[1] * 100,
                'percent_inverse': lambda: args[0] * 100 / args[1],
                'percent_remaining': lambda: args[0] * (100 - args[1]) / 100,
                'fraction_add': lambda: args[0] + args[1],
                'fraction_subtract': lambda: args[0] - args[1],
                'fraction_of': lambda: args[0] * args[1],
                'fraction_remaining': lambda: args[0] * (1 - args[1]),
                'triangle_area': lambda: args[0] * args[1] / 2,
                'trapezoid_area': lambda: (args[0] + args[1]) * args[2] / 2}
            self.assertIn(op, operations)
            self.assertEqual(operations[op](), Fraction(v['exactRational']))
            self.assertEqual(Fraction(q['answer']), Fraction(v['exactRational']))
            self.assertEqual(q['grade'], 5)
            self.assertEqual(q['reviewStatus'], 'arithmetic_checked')
        cfg, status = self.client.call('config')
        self.assertEqual(status, 200)
        self.assertEqual(cfg['pool']['teacherReview'], 'pending')
        self.assertTrue(all(m['ready'] for m in cfg['modes']))

    def test_principal_isolation_csrf_and_no_real_side_effects(self):
        state = self.start()
        self.assertTrue(state['demo'])
        self.assertNotIn('answer', json.dumps(state['activities']))
        cookies = self.client.api_headers['Set-Cookie']
        self.assertIn('HttpOnly', cookies)
        self.assertIn('SameSite=Strict', cookies)
        self.error(403, lambda: self.client.call('activity', {'generation': 1}, csrf='bad'))
        self.client.headers['Origin'] = 'http://evil.invalid'
        self.error(403, lambda: self.client.post('activity'))
        self.client.headers['Origin'] = 'http://localhost:8765'
        other = Client(self.server)
        self.start(other)
        first = self.client.post('practice/start')[0]['activities']['practice']
        self.error(404, lambda: other.post('practice/answer', attemptId=first['id'],
                                         questionId=first['currentQuestion']['id'], answer='24'))
        with connect(self.path) as db:
            for table in ('accounts', 'students', 'payment_orders', 'group_game_rooms'):
                exists = db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
                if exists:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)

    def test_idle_warning_multitab_refresh_and_absolute_lifetime(self):
        state = self.start()
        original = state['session']['lastActivityAt']
        self.server.at += 28 * 60_000
        self.assertTrue(self.client.call('state')[0]['session']['warning'])
        self.assertEqual(self.client.call('state')[0]['session']['lastActivityAt'], original)
        other_tab = self.client.copy()
        other_tab.post('activity')
        self.server.at += 3 * 60_000
        self.assertFalse(self.client.call('state')[0]['session']['warning'])
        self.server.at += trial.IDLE
        self.error(410, lambda: self.client.call('state'))
        self.start()
        with connect(self.path, True) as db:
            db.execute('UPDATE trial_sessions SET absolute_expires_at=?', (self.server.at + 1000,))
        self.server.at += 1000
        self.error(410, lambda: self.client.post('activity'))

    def test_answer_single_submit_retry_draft_and_state_resume(self):
        self.start()
        a = self.client.post('practice/start')[0]['activities']['practice']
        qid, aid = a['currentQuestion']['id'], a['id']
        self.assertNotIn('expected', a['currentQuestion'])
        self.client.post('draft', attemptId=aid, answers={qid: '24'}, scratch='120 : 100 × 20')
        restored = self.client.copy().call('state')[0]['activities']['practice']
        self.assertEqual(restored['scratch'], '120 : 100 × 20')
        self.assertEqual(restored['answers'][qid], '24')
        r = self.client.post('practice/answer', attemptId=aid, questionId=qid, answer='24')[0]
        self.assertTrue(r['activities']['practice']['results'][0]['correct'])
        retry = self.client.post('practice/answer', attemptId=aid, questionId=qid, answer='24')[0]
        self.assertEqual(len(retry['activities']['practice']['results']), 1)
        self.error(409, lambda: self.client.post('practice/answer', attemptId=aid, questionId=qid, answer='99'))

    def test_reset_revokes_inflight_and_keeps_counter(self):
        self.start()
        old = self.client.copy()
        reset = self.client.post('reset')[0]
        self.assertEqual(reset['session']['generation'], 2)
        self.error(409, lambda: old.post('activity'))
        with connect(self.path) as db:
            self.assertEqual(len(json.loads(db.execute('SELECT creates_json FROM trial_counters').fetchone()[0])), 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 0)

    def test_reset_rate_challenge_cooldown_survives_generation(self):
        self.start()
        for _ in range(4):
            self.assertEqual(self.client.post('reset')[1], 200)
        result, status = self.client.post('reset')
        self.assertEqual(status, 429)
        self.assertTrue(result['challengeRequired'])
        for _ in range(3):
            self.assertEqual(self.client.post('reset', challenge='5BMath')[1], 200)
        result, status = self.client.post('reset', challenge='5BMath')
        self.assertEqual(status, 429)
        self.assertEqual(result['retryAt'], self.server.at + 300_000)
        self.server.at += 1000
        self.assertEqual(self.client.post('reset', challenge='5BMath')[1], 429)

    def legacy_history_fixture(self):
        state = self.start()
        at = self.server.at
        with connect(self.path, True) as db:
            sid = db.execute("INSERT INTO students(student_code,full_name,grade_level) VALUES (?,?,?)",
                             ('TRIAL-LEGACY-QA', 'Legacy trial fixture', 5)).lastrowid
            bid = db.execute('SELECT id FROM trial_browsers').fetchone()[0]
            data = json.dumps({'kind': 'trial-history', 'summary': {'answeredCount': 1},
                               'scratch': 'legacy fixture', 'officialGrade': False})
            db.execute('INSERT INTO trial_keep_packages VALUES (?,?,?,?,?,?,?,?,NULL,?,?,?)',
                       ('legacy-claimed', bid, state['session']['id'], trial.digest('legacy-capability'),
                        'fixture-csrf', at, at + trial.DAY, data, at, sid, 'fixture-family'))
            db.execute('INSERT INTO trial_keep_packages VALUES (?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL)',
                       ('legacy-pending', bid, state['session']['id'], trial.digest('pending-capability'),
                        'fixture-csrf', at, at + trial.DAY, data))
            db.execute('INSERT INTO trial_claimed_history(package_id,student_id,family_id,claimed_at,consent_basis,snapshot_json) '
                       'VALUES (?,?,?,?,?,?)', ('legacy-claimed', sid, 'fixture-family', at, 'fixture-consent', data))
            original = tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone())
        return sid, original

    def test_retired_endpoints_return_410_without_database_or_identity_access(self):
        paths = ('keep', 'keep/state', 'keep/cancel', 'keep/claim', 'claim', 'history', 'history/1', 'trial-history')
        for logged_in in (False, True):
            client = self.client if logged_in else Client(SimpleNamespace(at=self.server.at))
            if logged_in:
                self.start()
            with patch.object(trial.api, 'connect', side_effect=AssertionError('Retired endpoint opened SQLite')):
                for path in paths:
                    for body in (None, {}, {'studentId': 999, 'consent': True}):
                        with self.subTest(path=path, post=body is not None, logged_in=logged_in):
                            self.error(410, lambda: client.call(path, body))
                            self.assertNotIn('Set-Cookie', client.api_headers)
                            self.assertEqual(client.api_headers['Cache-Control'], 'no-store')

    def test_retired_endpoints_do_not_mutate_legacy_packages_or_claimed_history(self):
        sid, original = self.legacy_history_fixture()
        with connect(self.path) as db:
            packages = [tuple(r) for r in db.execute('SELECT * FROM trial_keep_packages ORDER BY id')]
        self.server.trial_claim_authorizer = lambda *_: self.fail('Retired claim requested identity')
        for path in ('keep', 'keep/state', 'keep/cancel', 'keep/claim', 'claim', 'history'):
            self.error(410, lambda: self.client.post(path, consent=True, childId=sid))
        with connect(self.path) as db:
            self.assertEqual(tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone()), original)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM trial_keep_packages ORDER BY id')], packages)

    def test_legacy_ttl_cleanup_preserves_claimed_history_at_exact_boundaries(self):
        sid, original = self.legacy_history_fixture()
        at = self.server.at
        with connect(self.path, True) as db:
            trial.cleanup(db, at + trial.IDLE)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_sessions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 2)
            trial.cleanup(db, at + trial.DAY - 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 2)
            trial.cleanup(db, at + trial.DAY)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 0)
            self.assertEqual(tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone()), original)
            trial.cleanup(db, at + 8 * trial.DAY)
            self.assertEqual(tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone()), original)
            self.assertEqual(len(trial.claimed_history(db, sid)), 1)

    def test_reset_and_end_preserve_claimed_history_and_never_create_new_packages(self):
        _, original = self.legacy_history_fixture()
        self.client.post('practice/start')
        for action in ('reset', 'end'):
            self.client.post(action)
            with connect(self.path) as db:
                self.assertEqual(tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone()), original)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages WHERE cancelled_at IS NOT NULL').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0], 0)

    def test_public_session_snapshot_omits_legacy_keep_metadata(self):
        self.legacy_history_fixture()
        for payload in (self.client.call('state')[0], self.client.post('practice/start')[0], self.client.post('reset')[0]):
            self.assertNotIn('keep', payload)
            self.assertNotIn('history', payload)
            self.assertNotIn('fixture-consent', json.dumps(payload))

    def test_retired_claim_concurrent_with_reset_cannot_write_history(self):
        _, original = self.legacy_history_fixture()
        claimant, resetter = self.client.copy(), self.client.copy()
        def retired_claim():
            self.error(410, lambda: claimant.post('keep/claim', consent=True))
        with ThreadPoolExecutor(2) as pool:
            rejected, reset = pool.submit(retired_claim), pool.submit(resetter.post, 'reset')
            rejected.result()
            self.assertEqual(reset.result()[1], 200)
        with connect(self.path) as db:
            self.assertEqual(tuple(db.execute('SELECT * FROM trial_claimed_history').fetchone()), original)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_keep_packages').fetchone()[0], 2)

    def test_duel_reuses_defense_law_and_persists_no_reward(self):
        self.start()
        a = self.client.post('bot/start')[0]['activities']['bot']
        self.assertEqual(a['total'], 20)
        self.assertEqual(a['game']['status'], 'preparing')
        self.server.at += 3001
        a = self.client.call('state')[0]['activities']['bot']
        self.assertEqual(a['game']['battle']['hp'], 100)
        result = self.client.post('bot/answer', attemptId=a['id'],
            questionId=a['currentQuestion']['id'], answer='24')[0]['activities']['bot']
        self.assertIsNotNone(result['game']['battle']['defenseUntil'])
        self.assertEqual(result['game']['battle']['opponentHp'], 100)
        self.server.at += 3001
        final = self.client.copy().call('state')[0]['activities']['bot']
        self.assertIn(final['game']['battle']['opponentHp'], (80, 90))
        self.assertIn(final['game']['battle']['damage'], (10, 20))

    def test_stale_generation_after_expiry_and_end_never_reused(self):
        self.start()
        old = self.client.copy()
        self.server.at += trial.IDLE
        newer = self.start()
        self.assertGreater(newer['session']['generation'], old.generation)
        self.error(409, lambda: old.post('end'))
        second = self.client.copy()
        self.client.post('end')
        newest = self.start()
        self.assertGreater(newest['session']['generation'], second.generation)
        self.error(409, lambda: second.post('preferences', theme='garden', mascot='dog'))

    def test_malformed_requests_count_towards_resource_limit(self):
        self.start()
        for _ in range(119):
            self.error(404, lambda: self.client.post('practice/answer',
                attemptId='bad-id', questionId='bad-question', answer='1'))
        self.assertEqual(self.client.post('activity')[1], 429)

    def test_bot_sparse_polling_keeps_scheduled_defense(self):
        self.start()
        self.client.post('bot/start')
        self.server.at += 3000
        a = self.client.call('state')[0]['activities']['bot']
        with connect(self.path, True) as db:
            row = db.execute('SELECT payload_json FROM trial_attempts WHERE id=?', (a['id'],)).fetchone()
            raw = json.loads(row[0])
            raw['room']['trialBotCorrect'] = True
            trial.save_attempt(db, raw)
        pending = self.client.post('bot/answer', attemptId=a['id'],
            questionId=a['currentQuestion']['id'], answer='24')[0]['activities']['bot']
        self.assertEqual(pending['results'], [])
        self.server.at += 3000
        settled = self.client.call('state')[0]['activities']['bot']
        self.assertEqual(settled['game']['battle']['damage'], 10)
        self.assertEqual(settled['game']['battle']['opponentHp'], 90)

    def test_group_modes_reuse_bot_rules_no_live_room_or_xp(self):
        self.start()
        for mode in ('capture_flag', 'animal_race'):
            a = self.client.post('game/start', mode=mode)[0]['activities'][mode]
            self.assertEqual(len(a['game']['players']), 5)
            self.assertEqual(a['game']['target'], 5)
            qid = a['currentQuestion']['id']
            result = self.client.post('game/answer', attemptId=a['id'], questionId=qid, answer='24')[0]['activities'][mode]
            self.assertEqual(result['game']['players'][0]['correct'], 1)
            with connect(self.path) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rooms').fetchone()[0], 0)

    def test_all_game_modes_finish_without_rewards(self):
        self.start()
        pool = {q['id']: q['answer'] for q in trial.load_content()['questions']}
        for mode in ('capture_flag', 'animal_race', 'bot'):
            a = self.client.post('bot/start' if mode == 'bot' else 'game/start', mode=mode)[0]['activities'][mode]
            if mode == 'bot':
                self.server.at += 3000
                a = self.client.call('state')[0]['activities'][mode]
            for _ in range(10):
                if a['status'] in ('finished', 'completed'):
                    break
                if mode == 'bot':
                    with connect(self.path, True) as db:
                        raw = json.loads(db.execute('SELECT payload_json FROM trial_attempts WHERE id=?', (a['id'],)).fetchone()[0])
                        raw['room']['trialBotCorrect'] = False
                        trial.save_attempt(db, raw)
                q = a['currentQuestion']
                self.client.post('bot/answer' if mode == 'bot' else 'game/answer',
                                 attemptId=a['id'], questionId=q['id'], answer=pool[q['id']])
                self.server.at += 6000 if mode == 'bot' else 3000
                a = self.client.call('state')[0]['activities'][mode]
            self.assertEqual(a['status'], 'finished')
            if mode == 'bot':
                self.assertEqual(a['game']['result']['points'], 0)
            else:
                self.assertTrue(all(r['points'] == 0 for r in a['game']['rankings']))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rooms').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM student_companions').fetchone()[0], 0)

    def test_log_redaction_ttl_and_counter_cleanup(self):
        self.start()
        self.client.post('practice/start')
        self.client.post('end', password='MARKER-password', contact='MARKER-contact', answer='MARKER-answer')
        with connect(self.path, True) as db:
            raw = json.dumps([tuple(r) for r in db.execute('SELECT * FROM trial_events')])
            self.assertNotIn('MARKER', raw)
            self.assertNotIn(self.client.cookies[trial.BROWSER_COOKIE], raw)
            trial.cleanup(db, self.server.at + 8 * trial.DAY)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_events').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_counters').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_sessions').fetchone()[0], 0)

    def test_http_adapter_bounds_body_and_unknown_route(self):
        c = self.client
        self.assertFalse(trial.dispatch(SimpleNamespace(path='/not-trial')))
        c.command, c.path, c.rfile = 'POST', trial.BASE + 'session', io.BytesIO(b'{}')
        c.headers.update({'Content-Type': 'application/json', 'Content-Length': '40000'})
        c.json_response = lambda status, body: setattr(c, 'response', (status, body))
        self.assertTrue(trial.dispatch(c))
        self.assertEqual(c.response[0], 413)
        c.headers['Content-Length'] = '2'
        with patch.object(trial, 'route', side_effect=sqlite3.OperationalError('MARKER-private-db-detail')):
            self.assertTrue(trial.dispatch(c))
        self.assertEqual(c.response[0], 503)
        self.assertNotIn('MARKER', json.dumps(c.response))

    def test_cleanup_worker_runs_without_http_and_stops(self):
        self.start()
        ready = threading.Event()
        real_cleanup = trial.cleanup
        def cleanup_now(db, at=None):
            real_cleanup(db, self.server.at + 8 * trial.DAY)
            ready.set()
        with patch.object(trial, 'cleanup', side_effect=cleanup_now):
            worker, stopped = trial.start_cleanup_worker(self.path, interval_seconds=1)
            try:
                self.assertTrue(ready.wait(5))
            finally:
                stopped.set()
                worker.join(5)
            self.assertFalse(worker.is_alive())
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM trial_sessions').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
