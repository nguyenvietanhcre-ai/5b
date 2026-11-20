"""Family capabilities are server-side, per device and bound to one learner.

These tests use disposable project-local databases, never the localhost volume.
"""
import json
import secrets
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend import family_accounts as family
from backend import platform_api as api
from backend.arena import Arena
from backend.database import initialize, execute_sql


class FamilyClient:
    def __init__(self, server):
        self.server = server
        self.client_address = ('family-test-' + secrets.token_hex(5), 1234)
        self.headers = {'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'}
        self.path = ''
        self.command = 'GET'
        self.api_headers = {}
        self.csrf = ''
        self.context = ''

    def remember(self, result):
        cookie = self.api_headers.pop('Set-Cookie', None)
        if cookie:
            self.headers['Cookie'] = cookie.split(';')[0]
        if result.get('csrf'):
            self.csrf = result['csrf']
        if result.get('context'):
            self.context = result['context']
        return result

    def call(self, endpoint, body=None):
        self.path = '/api/family/' + endpoint
        self.command = 'GET' if body is None else 'POST'
        self.headers['X-CSRF-Token'] = self.csrf
        if self.context:
            self.headers['X-Family-Context'] = self.context
        result, status = family.request(self, self.command, self.path, body)
        assert 200 <= status < 300, (status, result)
        return self.remember(result)

    def learner(self, endpoint='session', body=None):
        self.path = '/api/v1/' + endpoint
        self.command = 'GET' if body is None else 'POST'
        self.headers['X-CSRF-Token'] = self.csrf
        self.headers['X-Family-Context'] = self.context
        result, status = api.dispatch(self, self.command, self.path.split('?')[0], body)
        assert status == 200, (status, result)
        return self.remember(result)

    def copy_capability(self):
        other = FamilyClient(self.server)
        other.headers = dict(self.headers)
        other.csrf, other.context = self.csrf, self.context
        return other


class FamilyAccountsTests(unittest.TestCase):
    PASSWORD = 'Family-test-password-17'

    def setUp(self):
        work = Path(__file__).resolve().parents[2] / 'test-databases'
        work.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='family-', dir=work)
        self.path = Path(self.directory.name) / 'family.sqlite3'
        initialize(self.path)
        api.initialize_catalog(self.path)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=True, arena=Arena())
        self.hash_patch = patch.object(api, 'ITERATIONS', 1000)
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)
        self.addCleanup(self.directory.cleanup)
        self.email = 'parent-' + secrets.token_hex(6) + '@example.test'

    def consent(self):
        return {'accepted': True, 'version': '2026-11-17-draft1',
                'name': 'Phụ huynh thử', 'contact': self.email, 'role': 'parent'}

    def register_body(self):
        return {'email': self.email, 'password': self.PASSWORD, 'parentName': 'Phụ huynh thử',
                'child': {'name': 'Bé Một', 'grade': 5, 'birthYear': api.academic()[0] - 10,
                          'mascot': 'cat', 'pin': '4321'}, 'requestKey': secrets.token_hex(12),
                'legalConsent': self.consent()}

    def register(self):
        client = FamilyClient(self.server)
        state = client.call('register', self.register_body())
        self.full(client)
        state = client.call('select', {'childId': state['children'][0]['id'], 'pin': '4321'})
        return client, state

    def full(self, client):
        state = client.call('state')
        state = client.call('parent/unlock' if state['parentPinSet'] else 'parent/pin/setup', {'pin': '654321'})
        self.assertEqual(state['scope'], 'parent_full')
        return state

    def add_child(self, client, name='Bé Hai', grade=4):
        self.full(client)
        return client.call('children/add', {'name': name, 'grade': grade, 'birthYear': api.academic()[0] - grade - 5,
                                          'mascot': 'dog', 'pin': '4321',
                                          'requestKey': secrets.token_hex(12),
                                          'legalConsent': self.consent()})

    def assert_denied(self, callback, statuses=(400, 401, 403, 409, 429)):
        with self.assertRaises(api.APIError) as caught:
            callback()
        self.assertIn(caught.exception.status, statuses)
        return caught.exception

    def make_exam(self, client):
        """Pin one self-contained fixture, independent of production bank seeding."""
        client.learner()
        with api.connect(self.path, True) as db:
            session = api.read_session(client, db)
            sid = session['student_id']
            grade, year_id = api.ensure_grade(db, sid, session['birth_year'])
            topic = db.execute('INSERT INTO topics(grade_id,title,theory_json) VALUES (?,?,?)',
                               (grade, 'Cộng số tự nhiên — kiểm thử', '[]')).lastrowid
            question = db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (?,?,?)',
                                  (grade, topic, 'FAMILY-TEST-' + secrets.token_hex(8))).lastrowid
            version = db.execute('INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,'
                                 'prompt_json,grading_rule_json,solution_steps_json,hints_json,status) '
                                 "VALUES (?,1,1,1,?,?,?,'[]','published')",
                                 (question, api.packed([{'type': 'text', 'text': 'Tính 1 + 1.'}]),
                                  api.packed({'answer': '2', 'answerKind': 'number', 'responseMode': 'typed'}),
                                  api.packed([{'type': 'text', 'text': '1 + 1 = 2.'}]))).lastrowid
            exam = db.execute('INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,'
                              'academic_year_id,owner_student_id,mode,created_at,response_mode) '
                              "VALUES (?,?,?,?, 'published',?,?, 'test',?,'typed')",
                              ('5B-FAMILY-' + secrets.token_hex(5), 'Đề kiểm thử gia đình', grade,
                               30, year_id, sid, api.stamp())).lastrowid
            db.execute("INSERT INTO exam_items(exam_id,position,question_version_id,max_points,options_json) VALUES (?,1,?,1,'[]')", (exam, version))
            db.execute('INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) '
                       "VALUES (?,?,?,?,'in_progress',?)",
                       (exam, sid, api.stamp(), api.stamp(api.now() + timedelta(minutes=30)), secrets.token_hex(12)))
            return exam

    def standalone(self):
        client = FamilyClient(self.server)
        body = self.register_body()
        body.pop('child')
        body['password'] = 'abc123'
        return client, client.call('register', body), body

    def raw_login(self, client, **extra):
        client.path = '/api/family/login'
        return family.request(client, 'POST', client.path,
                              {'email': self.email, 'password': self.PASSWORD, **extra})

    def test_standalone_signup_min6_creates_no_student_and_records_adult_consent(self):
        client, state, body = self.standalone()
        self.assertEqual(state['children'], [])
        self.assertEqual(state['activeProfile']['type'], 'parent')
        self.assertTrue(state['parentLocked'])
        self.assertTrue(state['onboarding']['needsChild'])
        self.assertTrue(state['onboarding']['canSetupParentPin'])
        self.assertTrue(state['device']['remember'])
        with api.connect(self.path) as db:
            for table in ('accounts', 'students', 'family_child_consents'):
                self.assertEqual(db.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM family_registration_consents').fetchone()[0], 1)
            self.assertGreater(len(db.execute('SELECT content_sha256 FROM family_registration_consents').fetchone()[0]), 20)
        self.assert_denied(lambda: client.call('parent/reauth', {'password': 'abc123'}), (403,))
        full = client.call('parent/pin/setup', {'pin': '654321'})
        self.assertEqual(full['scope'], 'parent_full')
        self.assertEqual(full['activeProfile']['type'], 'parent')
        self.assert_denied(lambda: client.call('parent/pin/setup', {'pin': '111111'}), (403,))
        with api.connect(self.path) as db:
            self.assertIsNotNone(db.execute('SELECT pin_hash FROM family_accounts').fetchone()[0])
        # Password login can open the account, but cannot replace an existing PIN.
        client.call('login', {'email': self.email, 'password': body['password']})
        self.assert_denied(lambda: client.call('parent/pin/setup', {'pin': '111111'}), (403,))

    def test_bootstrap_window_expires_and_password_login_renews_only_missing_pin(self):
        client, state, body = self.standalone()
        with patch.object(api, 'now', return_value=api.now() + timedelta(minutes=10, seconds=1)):
            error = self.assert_denied(lambda: client.call('parent/pin/setup', {'pin': '654321'}), (403,))
            self.assertEqual(error.code, 'family_pin_setup_expired')
            reopened = client.call('login', {'email': self.email, 'password': body['password']})
            self.assertEqual(reopened['device']['id'], state['device']['id'])
            self.assertEqual(client.call('parent/pin/setup', {'pin': '654321'})['scope'], 'parent_full')

    def test_onboard_birth_companion_pin_retry_and_three_children_keep_individual_identity(self):
        client, _, _ = self.standalone()
        client.call('parent/pin/setup', {'pin': '654321'})
        identities = []
        for i, mascot in enumerate(('cat', 'dog', 'fox')):
            body = {'name': 'Con số ' + str(i + 1), 'birthYear': api.academic()[0] - 6 - i,
                    'mascot': mascot, 'pin': '4321', 'requestKey': secrets.token_hex(12), 'legalConsent': self.consent()}
            state = client.call('children/add', body)
            sid = state['addedChildId']
            identities.append(sid)
            self.assertEqual(client.call('children/add', body)['addedChildId'], sid)
            child = next(c for c in state['children'] if c['id'] == sid)
            self.assertEqual(child['grade'], i + 1)
            self.assertEqual(child['mascot'], mascot)
            self.assertTrue(child['pinRequired'])
            self.assert_denied(lambda: client.call('children/add', {**body, 'pin': '4322'}), (409,))
            self.assert_denied(lambda: client.call('select', {'childId': sid, 'pin': '654321'}), (403,))
            selected = client.call('select', {'childId': sid, 'pin': '4321'})
            self.assertEqual(selected['activeProfile'], {'type': 'child', 'childId': sid})
            self.assertNotIn('email', selected['family'])
            self.assertEqual(client.learner()['state']['mascot'], mascot)
            self.full(client)
        self.assertEqual(len(set(identities)), 3)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM family_child_consents').fetchone()[0], 3)
            self.assertEqual(db.execute('SELECT count(DISTINCT account_id) FROM students').fetchone()[0], 3)
            self.assertEqual(db.execute('SELECT sum(xp) FROM student_companions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM accounts WHERE vip_expires_at IS NOT NULL').fetchone()[0], 0)
        invalid = {'name': 'Con chưa đủ', 'birthYear': api.academic()[0] - 7, 'requestKey': secrets.token_hex(12),
                   'legalConsent': self.consent(), 'mascot': 'invented', 'pin': '4321'}
        self.assert_denied(lambda: client.call('children/add', invalid), (400,))
        self.assert_denied(lambda: client.call('children/add', {**invalid, 'mascot': 'cat', 'pin': None}), (400,))

    def test_legacy_child_without_pin_opens_and_parent_can_explicitly_remove_child_pin(self):
        client, state = self.register()
        sid = state['selectedChildId']
        with api.connect(self.path, True) as db:
            db.execute('UPDATE family_children SET pin_hash=NULL WHERE student_id=?', (sid,))
        self.full(client)
        selected = client.call('select', {'childId': sid})
        self.assertFalse(selected['children'][0]['pinRequired'])
        self.full(client)
        self.assert_denied(lambda: client.call('parent/pin', {'pin': None}), (400,))
        self.assert_denied(lambda: client.call('child/pin', {'childId': sid, 'pin': None}), (400,))
        client.call('child/pin', {'childId': sid, 'pin': '456789'})
        self.assertEqual(client.call('select', {'childId': sid, 'pin': '456789'})['scope'], 'child')
        self.full(client)
        client.call('child/pin', {'childId': sid, 'noPin': True})
        self.assertEqual(client.call('select', {'childId': sid})['scope'], 'child')

    def test_three_device_limit_replacement_is_atomic_and_same_browser_reuses_slot(self):
        first, state = self.register()
        second, third = FamilyClient(self.server), FamilyClient(self.server)
        state2 = second.call('login', {'email': self.email, 'password': self.PASSWORD})
        third.call('login', {'email': self.email, 'password': self.PASSWORD})
        fourth = FamilyClient(self.server)
        payload, status = self.raw_login(fourth)
        self.assertEqual((status, payload['code'], len(payload['devices'])), (409, 'family_device_limit', 3))
        self.assertNotIn('email', json.dumps(payload['devices']))
        same = first.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.assertEqual(same['device']['id'], state['device']['id'])
        self.assertEqual(same['activeProfile'], state['activeProfile'])
        self.assert_denied(lambda: self.raw_login(fourth, replaceDeviceId=state2['device']['id'], parentPin='111111'), (403,))
        self.assertTrue(second.call('state')['authenticated'])
        self.assert_denied(lambda: self.raw_login(fourth, replaceDeviceId='other-family-device', parentPin='654321'), (404,))
        succeeded, status = self.raw_login(fourth, replaceDeviceId=state2['device']['id'], parentPin='654321')
        fourth.remember(succeeded)
        self.assertEqual(status, 200)
        self.assertFalse(second.call('state')['authenticated'])
        self.assertTrue(first.call('state')['authenticated'])
        self.assertTrue(third.call('state')['authenticated'])
        with api.connect(self.path) as db:
            self.assertEqual(len(family._devices(db, state['family']['id'])), 3)

    def test_replacement_pin_lock_preserves_existing_sessions_and_wrong_password_has_no_inventory(self):
        first, state = self.register()
        for _ in range(2):
            FamilyClient(self.server).call('login', {'email': self.email, 'password': self.PASSWORD})
        fourth = FamilyClient(self.server)
        for _ in range(5):
            self.assert_denied(lambda: self.raw_login(fourth, replaceDeviceId=state['device']['id'], parentPin='111111'), (403, 429))
        self.assert_denied(lambda: self.raw_login(fourth, replaceDeviceId=state['device']['id'], parentPin='654321'), (429,))
        self.assertTrue(first.call('state')['authenticated'])
        self.assert_denied(lambda: fourth.call('login', {'email': self.email, 'password': 'wrong-pass'}), (401,))
        with api.connect(self.path) as db:
            self.assertEqual(len(family._devices(db, state['family']['id'])), 3)

    def test_concurrent_fourth_device_replacements_cannot_exceed_three_or_revoke_two(self):
        first, state = self.register()
        for _ in range(2):
            FamilyClient(self.server).call('login', {'email': self.email, 'password': self.PASSWORD})
        def replace(_):
            try:
                return self.raw_login(FamilyClient(self.server), replaceDeviceId=state['device']['id'], parentPin='654321')[1]
            except api.APIError as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(replace, range(2)))
        self.assertEqual(sorted(results), [200, 404])
        with api.connect(self.path) as db:
            self.assertEqual(len(family._devices(db, state['family']['id'])), 3)
            self.assertEqual(db.execute('SELECT count(*) FROM family_devices WHERE revoked_at IS NOT NULL').fetchone()[0], 1)

    def test_parent_expiry_concurrent_state_keeps_cookie_profile_and_invalidates_old_private_context(self):
        client, state = self.register()
        self.full(client)
        old = client.copy_capability()
        cookie = client.headers['Cookie']
        copies = [client.copy_capability(), client.copy_capability()]
        for actor in copies:
            actor.context = ''
            actor.headers.pop('X-Family-Context', None)
        with patch.object(api, 'now', return_value=api.now() + timedelta(minutes=5, seconds=1)):
            with ThreadPoolExecutor(max_workers=2) as pool:
                states = list(pool.map(lambda actor: actor.call('state'), copies))
            self.assertEqual(states[0]['context'], states[1]['context'])
            self.assertEqual(states[0]['csrf'], states[1]['csrf'])
            for actor, current in zip(copies, states):
                self.assertEqual(actor.headers['Cookie'], cookie)
                self.assertEqual(current['activeProfile']['type'], 'parent')
                self.assertEqual(current['scope'], 'profiles')
                self.assertTrue(current['parentLocked'])
                self.assertNotIn('email', current['family'])
            error = self.assert_denied(lambda: old.learner('payments'), (403,))
            self.assertTrue(error.familyAccessChanged)
            restored = copies[0].call('parent/unlock', {'pin': '654321'})
            self.assertEqual(restored['activeProfile']['type'], 'parent')
            self.assertEqual(restored['selectedChildId'], state['selectedChildId'])

    def test_failed_replacement_rolls_back_revoke_and_concurrent_new_login_respects_cap(self):
        first, state = self.register()
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        def login(_):
            return self.raw_login(FamilyClient(self.server))[1]
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(login, range(2))), [200, 409])
        self.assert_denied(lambda: self.raw_login(FamilyClient(self.server), replaceDeviceId=state['device']['id'],
                                                parentPin='654321', deviceName=''), (400,))
        self.assertTrue(first.call('state')['authenticated'])
        self.assertTrue(second.call('state')['authenticated'])
        with api.connect(self.path) as db:
            self.assertEqual(len(family._devices(db, state['family']['id'])), 3)
            self.assertEqual(db.execute('SELECT count(*) FROM family_devices WHERE revoked_at IS NOT NULL').fetchone()[0], 0)

    def test_same_cookie_parent_relogin_preserves_parent_without_elevating_and_remember_30_days(self):
        first, state = self.register()
        self.full(first)
        logged = first.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.assertEqual(logged['device']['id'], state['device']['id'])
        self.assertEqual(logged['activeProfile']['type'], 'parent')
        self.assertEqual(logged['scope'], 'profiles')
        self.assertTrue(logged['parentLocked'])
        self.assert_denied(lambda: first.call('devices'), (403,))
        with api.connect(self.path) as db:
            device = db.execute('SELECT * FROM family_devices').fetchone()
            self.assertEqual(device['remembered'], 1)
            self.assertGreater(device['expires_at'], api.stamp(api.now() + timedelta(days=29)))

    def test_trial_history_api_is_gone_without_deleting_historical_records(self):
        client, state = self.register()
        with api.connect(self.path, True) as db:
            db.execute('INSERT INTO trial_claimed_history(package_id,student_id,family_id,claimed_at,consent_basis,snapshot_json) '
                       'VALUES(?,?,?,?,?,?)', ('old-package', state['selectedChildId'], str(state['family']['id']),
                                             1, 'historical-consent', '{}'))
            previous = [tuple(r) for r in db.execute('SELECT * FROM trial_claimed_history')]
        for actor in (client, FamilyClient(self.server)):
            self.assert_denied(lambda: actor.call('trial-history', {}), (410,))
            self.assert_denied(lambda: actor.call('trial-history'), (410,))
        with api.connect(self.path) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM trial_claimed_history')], previous)

    def test_migration_0037_preserves_every_old_column_and_row_in_populated_family(self):
        client, state = self.register()
        self.full(client)
        # Reconstruct exactly the pre-0037 schema and copy all existing values.
        older = self.path.with_name('pre-0037.sqlite3')
        connection = sqlite3.connect(older)
        self.addCleanup(connection.close)
        for migration in sorted((Path(family.__file__).parent / 'migrations').glob('*.sql')):
            if migration.name < '0037':
                execute_sql(connection, migration.read_text(encoding='utf-8'))
        with api.connect(self.path) as source:
            # Existing reference catalog is part of the values being preserved.
            tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            columns = {table: [r[1] for r in connection.execute('PRAGMA table_info(' + table + ')')] for table in tables}
            snapshots = {}
            connection.execute('PRAGMA foreign_keys=OFF')
            for table in tables:
                names = ','.join(columns[table])
                rows = [tuple(r) for r in source.execute('SELECT ' + names + ' FROM ' + table + ' ORDER BY rowid')]
                connection.execute('DELETE FROM ' + table)
                if rows:
                    connection.executemany('INSERT INTO ' + table + '(' + names + ') VALUES(' + ','.join('?' for _ in columns[table]) + ')', rows)
                snapshots[table] = rows
        execute_sql(connection, (Path(family.__file__).parent / 'migrations' / '0037_family_profile_pins.sql').read_text(encoding='utf-8'))
        for table, rows in snapshots.items():
            self.assertEqual(connection.execute('SELECT ' + ','.join(columns[table]) + ' FROM ' + table + ' ORDER BY rowid').fetchall(), rows, table)
        self.assertEqual(connection.execute('SELECT active_profile FROM family_devices').fetchone()[0], 'parent')
        connection.commit()

    def test_atomic_signup_retry_keeps_legacy_account_untouched(self):
        legacy = FamilyClient(self.server)
        legacy.path = '/api/v1/auth/register'
        legacy.command = 'POST'
        legacy_body = {'login': 'legacy-' + secrets.token_hex(6), 'password': self.PASSWORD,
                       'name': 'Học sinh cũ', 'birthYear': api.academic()[0] - 10}
        legacy_result, _ = api.dispatch(legacy, 'POST', legacy.path, legacy_body)
        legacy_id = legacy_result['account']['id']
        with api.connect(self.path) as db:
            old = dict(db.execute('SELECT * FROM accounts WHERE id=?', (legacy_id,)).fetchone())
            counts = tuple(db.execute('SELECT (SELECT count(*) FROM accounts),'
                                      '(SELECT count(*) FROM students),'
                                      '(SELECT count(*) FROM family_accounts)').fetchone())
        body = self.register_body()
        broken = {**body, 'legalConsent': {**self.consent(), 'accepted': False}}
        self.assert_denied(lambda: FamilyClient(self.server).call('register', broken))
        # remember is validated after family/child creation: rollback must undo
        # every insert when the final device setup fails.
        self.assert_denied(lambda: FamilyClient(self.server).call('register', {**body, 'remember': 'yes'}))
        with api.connect(self.path) as db:
            self.assertEqual(tuple(db.execute('SELECT (SELECT count(*) FROM accounts),'
                                             '(SELECT count(*) FROM students),'
                                             '(SELECT count(*) FROM family_accounts)').fetchone()), counts)
        client = FamilyClient(self.server)
        first = client.call('register', body)
        retried = FamilyClient(self.server).call('register', body)
        self.assert_denied(lambda: FamilyClient(self.server).call('register',
                           {**body, 'child': {**body['child'], 'pin': 1234}}), (400,))
        self.assertEqual(first['children'][0]['id'], retried['children'][0]['id'])
        self.assertEqual(first['scope'], 'profiles')
        self.assertEqual(len(first['children']), 1)
        self.assertNotIn(self.PASSWORD, json.dumps(first))
        self.assert_denied(lambda: FamilyClient(self.server).call('register',
                           {**body, 'child': {'name': 'Khác', 'grade': 4, 'birthYear': api.academic()[0] - 9}}), (409,))
        with api.connect(self.path) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM accounts WHERE id=?', (legacy_id,)).fetchone()), old)
            self.assertEqual(db.execute('SELECT count(*) FROM family_accounts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM family_parent_profiles').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM family_children').fetchone()[0], 1)

    def test_two_devices_select_independent_children_and_entitlements(self):
        first, state = self.register()
        child_one = state['selectedChildId']
        state = self.add_child(first)
        child_two = next(c['id'] for c in state['children'] if c['id'] != child_one)
        second = FamilyClient(self.server)
        logged = second.call('login', {'email': self.email, 'password': self.PASSWORD, 'remember': True})
        self.assertEqual(logged['scope'], 'profiles')
        first.call('select', {'childId': child_one, 'pin': '4321'})
        second.call('select', {'childId': child_two, 'pin': '4321'})
        a, b = first.learner(), second.learner()
        self.assertNotEqual(a['account']['id'], b['account']['id'])
        self.assertEqual(first.call('state')['selectedChildId'], child_one)
        self.assertEqual(second.call('state')['selectedChildId'], child_two)
        with api.connect(self.path) as db:
            mapped_a = api.read_session(first, db)
            mapped_b = api.read_session(second, db)
            self.assertNotEqual(mapped_a['student_id'], mapped_b['student_id'])
            self.assertEqual(db.execute('SELECT birth_year FROM accounts WHERE id=?',
                                        (mapped_a['account_id'],)).fetchone()[0], api.academic()[0] - 10)
        with api.connect(self.path, True) as db:
            from backend.learning_update import consume
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                       (api.stamp(api.now() + timedelta(days=30)), mapped_a['account_id']))
            consume(db, mapped_a, 'bot', secrets.token_hex(12))
        paid, free = first.learner(), second.learner()
        self.assertEqual(paid['account']['membership'], 'VIP')
        self.assertEqual(free['account']['membership'], 'Free')
        self.assertEqual(paid['account']['usage']['bot']['used'], 1)
        self.assertEqual(free['account']['usage']['bot']['used'], 0)
        self.assertIsNone(paid['account']['usage']['bot']['limit'])
        self.assertEqual(free['account']['usage']['bot']['limit'], 5)
        self.assertEqual(a['state']['birthYear'], api.academic()[0] - 10)
        self.full(first)
        self.assertEqual(second.call('state')['scope'], 'child')
        first.call('lock', {})
        self.assertEqual(second.call('state')['selectedChildId'], child_two)

    def test_rotation_rejects_old_cookie_and_stale_tab_context(self):
        client, state = self.register()
        old = client.copy_capability()
        previous_cookie = client.headers['Cookie']
        previous_context = client.context
        client.call('select', {'childId': state['selectedChildId'], 'pin': '4321'})
        self.assertNotEqual(client.headers['Cookie'], previous_cookie)
        self.assertNotEqual(client.context, previous_context)
        self.assertFalse(old.learner()['authenticated'])
        self.assert_denied(lambda: old.learner('profile', {'name': 'Không hợp lệ'}), (401, 403))
        tab = client.copy_capability()
        tab.context = previous_context
        self.assert_denied(lambda: tab.learner(), (403,))
        self.assert_denied(lambda: tab.call('state'), (403,))
        tab.context = ''
        tab.headers.pop('X-Family-Context', None)
        self.assertTrue(tab.call('state')['authenticated'])

    def test_csrf_origin_and_missing_family_context(self):
        client, state = self.register()
        client.csrf = 'wrong'
        self.assert_denied(lambda: client.call('select', {'childId': state['selectedChildId']}), (403,))
        client.csrf = state['csrf']
        client.headers['Origin'] = 'https://evil.example'
        self.assert_denied(lambda: client.call('parent/reauth', {'password': self.PASSWORD}), (403,))
        client.headers['Origin'] = 'http://localhost:8765'
        client.context = ''
        self.assert_denied(lambda: client.learner(), (403,))

    def test_cross_family_child_ids_are_never_authority(self):
        first, state_one = self.register()
        self.email = 'other-' + secrets.token_hex(5) + '@example.test'
        second, state_two = self.register()
        self.assert_denied(lambda: first.call('select', {'childId': state_two['selectedChildId']}), (403, 404))
        self.full(first)
        self.assert_denied(lambda: first.call('child/pin', {'childId': state_two['selectedChildId'], 'pin': '1234'}), (403, 404))
        self.assert_denied(lambda: first.call('devices/revoke', {'deviceId': state_two['device']['id']}), (403, 404))
        self.assertEqual(first.call('state')['selectedChildId'], state_one['selectedChildId'])
        self.assertEqual(second.call('state')['selectedChildId'], state_two['selectedChildId'])

    def test_parent_pin_failure_lock_is_persisted_and_device_local(self):
        first, _ = self.register()
        self.full(first)
        first.call('parent/pin', {'pin': '654321'})
        first.call('lock', {})
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        for _ in range(5):
            self.assert_denied(lambda: first.call('parent/unlock', {'pin': '111111'}))
        self.assert_denied(lambda: first.call('parent/unlock', {'pin': '654321'}), (429,))
        self.assertEqual(second.call('parent/unlock', {'pin': '654321'})['scope'], 'parent_full')
        self.assert_denied(lambda: first.call('parent/reauth', {'password': self.PASSWORD}), (403,))
        with patch.object(api, 'now', return_value=api.now() + timedelta(minutes=15, seconds=1)):
            self.assertEqual(first.call('parent/unlock', {'pin': '654321'})['scope'], 'parent_full')

    def test_parent_pin_opens_full_management_and_locked_parent_cannot_read_private_data(self):
        client, _ = self.register()
        self.assert_denied(lambda: client.learner('payments'), (403,))
        self.full(client)
        client.call('parent/pin', {'pin': '654321'})
        client.call('lock', {})
        self.assert_denied(lambda: client.call('devices'), (403,))
        self.assert_denied(lambda: client.call('children/add', {'name': 'Bé Ba', 'grade': 3,
                           'requestKey': secrets.token_hex(12), 'legalConsent': self.consent()}), (403,))
        self.assert_denied(lambda: client.learner('payments'), (403,))
        self.assert_denied(lambda: client.learner('payments/preview', {'plan': 'VIP'}), (403,))
        client.path = '/api/website/support/export/download'
        client.command = 'GET'
        with api.connect(self.path) as db:
            self.assert_denied(lambda: api.read_session(client, db), (403,))
        self.full(client)
        self.assertEqual(client.learner('payments')['orders'], [])
        self.assertTrue(client.call('devices')['devices'])

    def test_child_pin_and_child_only_device_cannot_elevate_or_switch_sibling(self):
        first, state = self.register()
        child_one = state['selectedChildId']
        state = self.add_child(first)
        child_two = next(c['id'] for c in state['children'] if c['id'] != child_one)
        first.call('child/pin', {'childId': child_two, 'pin': '4321'})
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.assert_denied(lambda: second.call('select', {'childId': child_two}))
        self.assertEqual(second.call('select', {'childId': child_two, 'pin': '4321'})['selectedChildId'], child_two)
        self.full(first)
        first.call('parent/pin', {'pin': '654321'})
        configured = first.call('devices/configure', {'remember': True, 'childOnly': True, 'childId': child_one})
        self.assertEqual([c['id'] for c in configured['children']], [child_one])
        self.assert_denied(lambda: first.call('parent/unlock', {'pin': '654321'}), (403,))
        self.assert_denied(lambda: first.call('parent/reauth', {'password': self.PASSWORD}), (403,))
        self.assert_denied(lambda: first.call('select', {'childId': child_two, 'pin': '4321'}), (403, 404))

    def test_parent_idle_and_absolute_expiry(self):
        client, _ = self.register()
        base = api.now()
        self.full(client)
        with patch.object(api, 'now', return_value=base + timedelta(minutes=5, seconds=1)):
            self.assertNotIn(client.call('state')['scope'], ('parent_read', 'parent_full'))
        self.full(client)
        for minutes in (4, 8, 12):
            with patch.object(api, 'now', return_value=base + timedelta(minutes=minutes)):
                self.assertEqual(client.call('parent/overview')['scope'], 'parent_full')
        with patch.object(api, 'now', return_value=base + timedelta(minutes=15, seconds=1)):
            self.assertNotIn(client.call('state')['scope'], ('parent_read', 'parent_full'))

    def test_revoke_device_keeps_other_device_and_logoutall_revokes_current(self):
        first, _ = self.register()
        second = FamilyClient(self.server)
        state_two = second.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.full(first)
        devices = first.call('devices')
        self.assertNotIn('token_hash', json.dumps(devices))
        first.call('devices/revoke', {'deviceId': state_two['device']['id']})
        self.assertFalse(second.call('state')['authenticated'])
        self.assertTrue(first.call('state')['authenticated'])
        first.call('devices/logout-all', {})
        self.assertFalse(first.call('state')['authenticated'])

    def test_password_change_revokes_all_devices_and_old_password(self):
        first, _ = self.register()
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.full(first)
        replacement = 'Replacement-family-password-17'
        first.call('password', {'newPassword': replacement})
        self.assertFalse(first.call('state')['authenticated'])
        self.assertFalse(second.call('state')['authenticated'])
        self.assert_denied(lambda: FamilyClient(self.server).call('login',
                           {'email': self.email, 'password': self.PASSWORD}), (401,))
        self.assertTrue(FamilyClient(self.server).call('login',
                        {'email': self.email, 'password': replacement})['authenticated'])

    def test_two_devices_stale_answer_revision_cannot_overwrite(self):
        first, _ = self.register()
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        second.call('select', {'childId': first.call('state')['children'][0]['id'], 'pin': '4321'})
        exam_id = self.make_exam(first)
        self.assert_denied(lambda: second.learner('exams', {'requestKey': secrets.token_hex(12),
                           'count': 3, 'category': 'content', 'maxWeek': 35, 'difficulty': 0}), (409,))
        original = first.learner('exams/' + str(exam_id))['exam']
        concurrent = second.learner('exams/' + str(exam_id))['exam']
        self.assertEqual(original['revision'], concurrent['revision'])
        saved = first.learner(f'exams/{exam_id}/answers',
                              {'position': 1, 'answer': '2', 'revision': original['revision']})['exam']
        self.assertGreater(saved['revision'], original['revision'])
        self.assert_denied(lambda: second.learner(f'exams/{exam_id}/answers',
                           {'position': 1, 'answer': '3', 'revision': concurrent['revision']}), (409,))
        self.assert_denied(lambda: second.learner(f'exams/{exam_id}/answers',
                           {'position': 1, 'answer': '3'}), (409,))
        self.assertEqual(second.learner('exams/' + str(exam_id))['exam']['answers']['1'], '2')
        first.learner(f'exams/{exam_id}/submit', {'revision': saved['revision']})
        second.learner(f'exams/{exam_id}/submit', {'revision': saved['revision']})
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM exam_answers WHERE exam_id=?', (exam_id,)).fetchone()[0], 1)

    def test_two_devices_scratch_revision_conflict_keeps_first_note(self):
        first, _ = self.register()
        second = FamilyClient(self.server)
        second.call('login', {'email': self.email, 'password': self.PASSWORD})
        second.call('select', {'childId': first.call('state')['children'][0]['id'], 'pin': '4321'})
        exam_id = self.make_exam(first)
        note = {'version': 1, 'open': True, 'text': 'Bài của máy một', 'color': '#203a32', 'strokes': []}
        initial = first.learner(f'exams/{exam_id}/scratch?position=1')['scratch']
        first.learner(f'exams/{exam_id}/scratch', {'position': 1, 'revision': initial['revision'],
                      'requestKey': secrets.token_hex(12), 'note': note})
        result = second.learner(f'exams/{exam_id}/scratch', {'position': 1, 'revision': initial['revision'],
                               'requestKey': secrets.token_hex(12), 'note': {**note, 'text': 'Ghi đè cũ'}})
        self.assertTrue(result['conflict'])
        self.assertEqual(result['scratch']['note'], note)

    def test_declared_grade_is_independent_of_true_birth_year(self):
        client = FamilyClient(self.server)
        body = self.register_body()
        body['child']['grade'] = 4
        # This child studies one grade below the previous age-derived default.
        state = client.call('register', body)
        self.assertEqual(state['children'][0]['grade'], 4)
        self.full(client)
        client.call('select', {'childId': state['children'][0]['id'], 'pin': '4321'})
        learner = client.learner()
        self.assertEqual(learner['state']['grade'], 4)
        self.assertEqual(learner['state']['birthYear'], body['child']['birthYear'])
        with api.connect(self.path) as db:
            session = api.read_session(client, db)
            self.assertEqual(api.grade_for_student(db, session['student_id'], session['birth_year']), 4)
            self.assertEqual(db.execute('SELECT birth_year FROM accounts WHERE id=?',
                                        (session['account_id'],)).fetchone()[0], body['child']['birthYear'])

    def test_parent_select_preserves_elevation_absolute_deadline(self):
        client, initial = self.register()
        state = self.add_child(client)
        other_child = next(c['id'] for c in state['children'] if c['id'] != initial['selectedChildId'])
        base = api.now()
        self.full(client)
        for minute in (4, 8):
            with patch.object(api, 'now', return_value=base + timedelta(minutes=minute)):
                client.call('parent/overview')
        old = client.copy_capability()
        with patch.object(api, 'now', return_value=base + timedelta(minutes=12)):
            selected = client.call('parent/select', {'childId': other_child})
            self.assertEqual(selected['scope'], 'parent_full')
            self.assertEqual(selected['selectedChildId'], other_child)
        self.assertFalse(old.learner()['authenticated'])
        with patch.object(api, 'now', return_value=base + timedelta(minutes=15, seconds=1)):
            locked = client.call('state')
            self.assertEqual(locked['scope'], 'profiles')
            self.assertEqual(locked['activeProfile']['type'], 'parent')
            self.assertTrue(locked['parentLocked'])

    def test_trial_claim_requires_full_selected_child_and_live_consent(self):
        client, state = self.register()
        selected = state['selectedChildId']
        client.path = '/api/trial/claim'
        client.headers['X-CSRF-Token'] = client.csrf
        client.headers['X-Family-Context'] = client.context
        with api.connect(self.path) as db:
            self.assert_denied(lambda: family.authorize_claim(client, db, {}), (403,))
        self.full(client)
        client.path = '/api/trial/claim'
        client.headers['X-CSRF-Token'] = client.csrf
        client.headers['X-Family-Context'] = client.context
        with api.connect(self.path) as db:
            claim = family.authorize_claim(client, db, {'childId': selected})
            self.assertEqual(claim['student_id'], selected)
            self.assertTrue(claim['consent_basis'].startswith('self_declared:learning:'))
            self.assert_denied(lambda: family.authorize_claim(client, db, {'childId': selected + 1}), (403,))
        with api.connect(self.path, True) as db:
            db.execute("UPDATE family_child_consents SET withdrawn_at=? WHERE student_id=? AND purpose='learning'", (api.stamp(), selected))
        with api.connect(self.path) as db:
            self.assert_denied(lambda: family.authorize_claim(client, db, {}), (403,))

    def test_revoked_family_cookie_never_falls_back_to_valid_legacy_cookie(self):
        legacy = FamilyClient(self.server)
        legacy.path, legacy.command = '/api/v1/auth/register', 'POST'
        result, _ = api.dispatch(legacy, 'POST', legacy.path,
                                {'login': 'legacy-' + secrets.token_hex(6), 'password': self.PASSWORD,
                                 'name': 'Học sinh cũ', 'birthYear': api.academic()[0] - 10})
        legacy.remember(result)
        family_client, _ = self.register()
        self.full(family_client)
        stale = family_client.copy_capability()
        family_client.call('devices/logout-all', {})
        stale.headers['Cookie'] += '; ' + legacy.headers['Cookie']
        self.assertFalse(stale.learner()['authenticated'])
        self.assertTrue(legacy.learner()['authenticated'])

    def test_family_login_revokes_same_browser_legacy_capability_only(self):
        family_client, _ = self.register()
        legacy = FamilyClient(self.server)
        legacy.path, legacy.command = '/api/v1/auth/register', 'POST'
        result, _ = api.dispatch(legacy, 'POST', legacy.path,
                                {'login': 'legacy-' + secrets.token_hex(6), 'password': self.PASSWORD,
                                 'name': 'Học sinh cũ', 'birthYear': api.academic()[0] - 10})
        legacy.remember(result)
        previous_legacy = legacy.copy_capability()
        legacy.call('login', {'email': self.email, 'password': self.PASSWORD})
        self.assertFalse(previous_legacy.learner()['authenticated'])
        self.assertTrue(family_client.call('state')['authenticated'])


if __name__ == '__main__':
    unittest.main()
