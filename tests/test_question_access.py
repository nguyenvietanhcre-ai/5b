"""ACL regressions use isolated SQLite databases, never the running localhost."""
import hashlib
import io
import json
import secrets
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from backend import question_access as access
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, now, seed_catalog, stamp
from backend.question_bank import published_version_ids
from test_platform_api import Client


class QuestionAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'work')
        cls.template = Path(cls.directory.name) / 'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path = Path(self.directory.name) / (secrets.token_hex(8) + '.sqlite3')
        with closing(sqlite3.connect(self.template)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        self.client = Client(self.server)
        self.state = self.client.call('auth/register', {'login': 'acl-' + secrets.token_hex(6),
            'password': 'isolated-test-password', 'name': 'Bạn thử', 'birthYear': academic()[0] - 10})
        with connect(self.path, True) as db:
            self.aid = self.state['account']['id']
            self.sid = db.execute('SELECT id FROM students WHERE account_id=?', (self.aid,)).fetchone()[0]
            self.session = {'account_id': self.aid, 'student_id': self.sid, 'birth_year': academic()[0] - 10}
            self.vid = db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' LIMIT 1").fetchone()[0]
            self.staff = db.execute("INSERT INTO staff_users(login,full_name,password_hash,role,created_at) VALUES (?,'Test admin','unused','admin',?)", ('acl-admin-' + secrets.token_hex(4), stamp())).lastrowid
            self.user = {'id': self.staff, 'role': 'admin'}
            db.execute("UPDATE question_access_policy SET mode='classified'")

    def label(self, db, vid=None, tier='free', purposes=None, review='approved', expected=0):
        return access.classify(db, self.user, vid or self.vid, {'tier': tier,
            'purposes': purposes or ['practice'], 'reviewStatus': review,
            'sourceNote': 'Test fixture: đáp án, lời giải và nguồn được đối chiếu trong bài kiểm thử.',
            'expectedRevision': expected})

    def grant(self, db, role):
        expiry = stamp(now() + timedelta(days=3))
        db.execute('UPDATE accounts SET vip_expires_at=?,vip_plus_expires_at=? WHERE id=?',
                   (expiry if role in ('VIP', 'VIP+') else None, expiry if role == 'VIP+' else None, self.aid))

    def test_tier_lattice_expiry_grade_and_difficulty_are_independent(self):
        with connect(self.path, True) as db:
            self.label(db, tier='vip_plus')
            row = access.version(db, self.vid)
            original = (row['grade_id'], row['difficulty'], row['topic_id'])
            for role, expected in [('Free', False), ('VIP', False), ('VIP+', True)]:
                self.grant(db, role)
                self.assertEqual(access.allowed(db, self.vid, session=self.session), expected)
            self.grant(db, 'Free')
            self.assertFalse(access.allowed(db, self.vid, session=self.session))
            self.label(db, tier='free', expected=1)
            self.assertTrue(access.allowed(db, self.vid, session=self.session))
            self.assertFalse(access.allowed(db, self.vid))
            current = access.version(db, self.vid)
            self.assertEqual(original, (current['grade_id'], current['difficulty'], current['topic_id']))
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 0)

    def test_svip_reuses_existing_entitlement_without_fifth_tier(self):
        with connect(self.path, True) as db:
            from unittest.mock import patch
            self.label(db, tier='vip_plus')
            with patch('backend.learning_update.membership', return_value='SVip'):
                self.assertTrue(access.allowed(db, self.vid, session=self.session))
            self.assertEqual(access.TIERS, ('trial', 'free', 'vip', 'vip_plus'))

    def test_public_game_requires_free_approved_purpose_and_exact_content(self):
        with connect(self.path, True) as db:
            self.label(db, tier='free', purposes=['practice'])
            self.assertFalse(access.allowed(db, self.vid, purpose='arena', public_game=True))
            self.label(db, purposes=['arena'], expected=1)
            self.assertTrue(access.allowed(db, self.vid, purpose='arena', public_game=True))
            self.assertFalse(access.allowed(db, self.vid, purpose='group-games', public_game=True))
            db.execute("UPDATE question_versions SET hints_json='[]' WHERE id=?", (self.vid,))
            self.assertFalse(access.allowed(db, self.vid, purpose='arena', public_game=True))

    def test_unmapped_draft_retired_and_trial_do_not_enter_normal_selector(self):
        with connect(self.path, True) as db:
            self.assertFalse(access.allowed(db, self.vid, session=self.session))
            self.label(db, review='draft')
            self.assertFalse(access.allowed(db, self.vid, session=self.session))
            self.label(db, tier='trial', expected=1)
            self.assertFalse(access.allowed(db, self.vid, session=self.session))
            self.assertTrue(access.allowed(db, self.vid, trial_ids=(self.vid,)))
            db.execute("UPDATE question_versions SET status='retired' WHERE id=?", (self.vid,))
            self.assertFalse(access.allowed(db, self.vid, trial_ids=(self.vid,)))

    def test_legacy_snapshot_preserves_old_pool_but_never_new_revision(self):
        with connect(self.path, True) as db:
            db.execute("UPDATE question_access_policy SET mode='legacy'")
            row = access.version(db, self.vid)
            old = published_version_ids(db, row['grade_id'], row['difficulty'])
            new = db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,status,options_json) SELECT question_id,revision+1,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,'published',options_json FROM question_versions WHERE id=?", (self.vid,)).lastrowid
            self.assertFalse(access.allowed(db, new, session=self.session))
            self.assertEqual(old, published_version_ids(db, row['grade_id'], row['difficulty']))
            # Staging labels do not activate a new selector or change old quotas.
            self.label(db, tier='vip_plus', review='draft')
            self.assertEqual(old, published_version_ids(db, row['grade_id'], row['difficulty']))
            db.execute("UPDATE question_versions SET options_json='[]' WHERE id=?", (self.vid,))
            self.assertNotIn(self.vid, published_version_ids(db, row['grade_id'], row['difficulty']))

    def test_classification_cas_admin_only_and_no_auto_publication(self):
        with connect(self.path, True) as db:
            self.label(db)
            with self.assertRaises(APIError) as stale:
                self.label(db)
            self.assertEqual(stale.exception.status, 409)
            with self.assertRaises(APIError):
                access.classify(db, {'id': self.staff, 'role': 'teacher'}, self.vid, {})
            with self.assertRaises(APIError):
                self.label(db, tier='vip', purposes=['arena'], expected=1)
            db.execute("UPDATE question_versions SET status='draft' WHERE id=?", (self.vid,))
            with self.assertRaises(APIError):
                self.label(db, expected=1)
            self.assertEqual(db.execute('SELECT status FROM question_versions WHERE id=?', (self.vid,)).fetchone()[0], 'draft')

    def publish_product(self, db):
        self.label(db, tier='vip_plus', purposes=['premium', 'exam-sale'])
        db.execute("INSERT INTO exam_products(slug,title,price,question_version_ids_json,published) VALUES ('acl-exam','Đề kiểm quyền',10000,?,1)", (json.dumps([self.vid]),))

    def test_paid_exam_exact_order_right_does_not_grant_whole_bank(self):
        from backend.exam_commerce import create_order, start_order
        from backend.payments import settle_order
        with connect(self.path, True) as db:
            self.publish_product(db)
            order = create_order(db, self.session, {'examProduct': 'acl-exam'})['order']
            with self.assertRaises(APIError):
                start_order(db, self.session, order['id'])
            settle_order(db, db.execute('SELECT * FROM payment_orders WHERE id=?', (order['id'],)).fetchone(), 'staff')
            self.assertFalse(access.allowed(db, self.vid, session=self.session))
            # Withdrawal stops new sales, while the exact paid snapshot survives.
            db.execute("UPDATE question_versions SET status='retired' WHERE id=?", (self.vid,))
            first = start_order(db, self.session, order['id'])['exam']
            self.assertEqual(first['id'], start_order(db, self.session, order['id'])['exam']['id'])
            self.assertNotIn('answer', first['questions'][0])
            with self.assertRaises(APIError):
                start_order(db, {**self.session, 'account_id': self.aid + 100000}, order['id'])
            with self.assertRaises(APIError):
                create_order(db, self.session, {'examProduct': 'acl-exam'})

    def test_forged_premium_issue_code_and_order_payload_cannot_bypass(self):
        from backend.premium_content import issue_exam
        from backend.exam_commerce import create_order
        from backend.payments import settle_order
        with connect(self.path, True) as db:
            self.publish_product(db)
            payload = {'grade': 5, 'ids': [self.vid], 'title': 'Forged', 'duration_minutes': 30}
            with self.assertRaises(APIError) as error:
                issue_exam(db, self.session, payload, 'forged-code', 'PURCHASE-1-forged')
            self.assertEqual(error.exception.status, 403)
            order = create_order(db, self.session, {'examProduct': 'acl-exam'})['order']
            settle_order(db, db.execute('SELECT * FROM payment_orders WHERE id=?', (order['id'],)).fetchone(), 'staff')
            with self.assertRaises(APIError):
                issue_exam(db, self.session, payload, 'forged-order', 'PURCHASE-forged', purchase_order_id=order['id'])
            db.execute("UPDATE question_versions SET solution_steps_json='[]' WHERE id=?", (self.vid,))
            with self.assertRaises(APIError):
                access.purchased_payload(db, self.session, order['id'])
            self.assertEqual(db.execute('SELECT count(*) FROM exam_order_attempts').fetchone()[0], 0)

    def test_historical_read_marking_and_lookup_use_owned_attempts_after_expiry(self):
        from backend.platform_api import create_exam, owned_attempt, exam_view, submit
        from backend.practice_export import initialize as export_init, lookup, identity, export_pdf
        with connect(self.path, True) as db:
            db.execute("UPDATE question_access_policy SET mode='legacy'")
            row = access.version(db, self.vid)
            result = create_exam(db, self.session, {'requestKey': 'history-claim-123', 'count': 3,
                'topic': db.execute('SELECT client_key FROM topics WHERE id=?', (row['topic_id'],)).fetchone()[0]})
            eid = int(result['id'])
            db.execute("UPDATE question_access_policy SET mode='classified'")
            db.execute("UPDATE question_versions SET status='retired' WHERE id IN (SELECT question_version_id FROM exam_items WHERE exam_id=?)", (eid,))
            attempt = owned_attempt(db, self.session, eid)
            self.assertEqual(len(exam_view(db, attempt)['questions']), 3)
            with self.assertRaises(APIError):
                owned_attempt(db, {**self.session, 'student_id': self.sid + 999}, eid)
            submit(db, attempt)
            self.assertIn('answer', exam_view(db, owned_attempt(db, self.session, eid))['questions'][0])
            export_init(db)
            received = db.execute('SELECT question_version_id FROM exam_items WHERE exam_id=? LIMIT 1', (eid,)).fetchone()[0]
            snapshot = {'provider': 'main', 'revision': 1, 'grade': 5, 'topicTitle': 'Mẫu đã nhận',
                        'text': 'Tính 1 + 1.', 'prompt': [{'type': 'text', 'text': 'Tính 1 + 1.'}],
                        'responseMode': 'typed', 'options': [], 'answer': '2', 'steps': [],
                        'thinking': [], 'lesson': None, 'assets': {}}
            code, sha = identity(snapshot)
            db.execute('INSERT INTO practice_export_codes VALUES (?,?,?,?,?,?,?)',
                       (code, 'main', received, 1, sha, json.dumps(snapshot), stamp()))
            self.assertNotIn('answer', lookup(db, self.session, code)['question'])
            self.assertEqual(lookup(db, self.session, code, solutions=True)['question']['answer'], '2')
            stranger = {**self.session, 'student_id': self.sid + 999}
            with self.assertRaises(APIError) as private_code:
                lookup(db, stranger, code, solutions=True)
            self.assertEqual(private_code.exception.status, 404)
            with self.assertRaises(APIError) as private_pdf:
                export_pdf(db, stranger, {'provider': 'main', 'attemptId': eid, 'includeSolutions': True},
                           provider='main', frontend=Path(__file__).resolve().parents[1] / 'frontend')
            self.assertEqual(private_pdf.exception.status, 404)

    def test_migration_inventory_does_not_change_entitlements_usage_or_issued_data(self):
        with connect(self.path, True) as db:
            tables = ('accounts', 'students', 'daily_usage', 'exam_attempts', 'exam_items', 'vip_purchases')
            before = {table: [tuple(r) for r in db.execute('SELECT * FROM ' + table)] for table in tables}
            for table in ('question_access_order_pins', 'question_access_labels', 'question_access_legacy', 'question_access_policy'):
                db.execute('DROP TABLE ' + table)
            db.execute("DELETE FROM schema_migrations WHERE name='0035_question_access.sql'")
        initialize(self.path)
        with connect(self.path) as db:
            after = {table: [tuple(r) for r in db.execute('SELECT * FROM ' + table)] for table in tables}
            self.assertEqual(before, after)
            self.assertEqual(db.execute('SELECT count(*) FROM question_access_labels').fetchone()[0], 0)
            self.assertEqual(access.inventory(db)['legacyCount'], db.execute("SELECT count(*) FROM question_versions WHERE status='published'").fetchone()[0])

    def test_old_schema_bootstrap_waits_for_real_access_migration(self):
        from backend.database import BACKEND
        from unittest.mock import patch
        old_backend = Path(self.directory.name) / ('old-backend-' + secrets.token_hex(4))
        migrations = old_backend / 'migrations'
        migrations.mkdir(parents=True)
        for source in (BACKEND / 'migrations').glob('*.sql'):
            if source.name < '0016_sepay_payments.sql':
                shutil.copy2(source, migrations / source.name)
        legacy_path = old_backend / 'old.sqlite3'
        with patch('backend.database.BACKEND', old_backend):
            initialize(legacy_path)
        seed_catalog(legacy_path)
        with connect(legacy_path) as db:
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='question_access_legacy'").fetchone())
            published = db.execute("SELECT count(*) FROM question_versions WHERE status='published'").fetchone()[0]
            pins_before = [tuple(r) for r in db.execute('SELECT id,prompt_json,grading_rule_json FROM question_versions ORDER BY id')]
            # Missing future schema never falls back to unfiltered selection.
            with self.assertRaises(sqlite3.OperationalError):
                published_version_ids(db, 5, 1)
        initialize(legacy_path)
        with connect(legacy_path) as db:
            self.assertEqual(access.inventory(db)['legacyCount'], published)
            self.assertEqual(db.execute('SELECT count(*) FROM question_access_labels').fetchone()[0], 0)
            self.assertEqual(pins_before, [tuple(r) for r in db.execute('SELECT id,prompt_json,grading_rule_json FROM question_versions ORDER BY id')])
            self.assertTrue(published_version_ids(db, 5, 1))

    def test_staff_endpoint_rejects_guest_csrf_and_exposes_no_answers(self):
        handler = SimpleNamespace(server=self.server, path=access.BASE, headers={'Host': 'localhost:8765', 'Origin': 'http://localhost:8765'})
        with self.assertRaises(APIError) as guest:
            access.request(handler, 'GET', access.BASE)
        self.assertEqual(guest.exception.status, 401)
        token, csrf = 'isolated-staff-token', 'isolated-staff-csrf'
        with connect(self.path, True) as db:
            db.execute('INSERT INTO staff_sessions VALUES (?,?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), self.staff, csrf, stamp(now() + timedelta(hours=1))))
        handler.headers['Cookie'] = '5bmath_staff=' + token
        data, status = access.request(handler, 'GET', access.BASE)
        self.assertEqual(status, 200)
        self.assertEqual(data['pageSize'], 40)
        self.assertFalse(any(key in item for item in data['items'] for key in ('answer', 'solution', 'grading_rule_json')))
        with self.assertRaises(APIError) as forgery:
            access.request(handler, 'POST', access.BASE + '/versions/' + str(self.vid), {})
        self.assertEqual(forgery.exception.status, 403)
        handler.command, handler.rfile = 'POST', io.BytesIO(b'{}')
        handler.headers.update({'Content-Type': 'application/json', 'Content-Length': '2'})
        replies = []
        handler.json_response = lambda status, value: replies.append((status, value))
        self.assertTrue(access.dispatch(handler, self.path))
        self.assertEqual(replies[0][0], 403)

    def test_group_source_free_purpose_gate_and_mutation_detection(self):
        from backend.group_games import QuestionSource
        questions = [{'id': 'acl-group-' + str(i), 'revision': 1, 'purpose': 'group-games', 'grade': 5,
            'text': 'Tính 1 + 1.', 'answer': '2', 'answerKind': 'number', 'responseMode': 'typed',
            'tier': 'free', 'reviewStatus': 'approved'} for i in range(5)]
        source = QuestionSource(questions, approved=True, revision='acl-group-v1')
        self.assertEqual(len(source.select(5, 'capture_flag')), 5)
        with self.assertRaises(ValueError):
            QuestionSource([{**q, 'tier': 'vip_plus'} for q in questions], approved=True)
        source.questions[0]['answer'] = '99'
        with self.assertRaises(APIError):
            source.select(5, 'capture_flag')

    def test_group_catalogue_uses_declared_grade_without_rewriting_birth(self):
        from backend import group_games
        with connect(self.path, True) as db:
            family_id = db.execute('INSERT INTO family_accounts(email,password_hash,registration_key,registration_digest,created_at) VALUES (?,?,?,?,?)',
                                   ('grade-' + secrets.token_hex(5) + '@example.test', 'unused', secrets.token_hex(8), 'fixture', stamp())).lastrowid
            db.execute('INSERT INTO family_children(student_id,family_id,declared_grade,grade_academic_year,actual_birth_year,request_key,request_digest,created_at) VALUES (?,?,?,?,?,?,?,?)',
                       (self.sid, family_id, 2, academic()[0], self.session['birth_year'], 'grade-fixture', 'fixture', stamp()))
        self.server.group_games = SimpleNamespace(catalogue=lambda grade: {'selectedGrade': grade})
        self.client.path = group_games.BASE + '/catalogue'
        data, status = group_games.dispatch(self.client, 'GET', self.client.path, None)
        self.assertEqual((status, data['selectedGrade']), (200, 2))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT birth_year FROM accounts WHERE id=?', (self.aid,)).fetchone()[0], self.session['birth_year'])


if __name__ == '__main__':
    unittest.main()
