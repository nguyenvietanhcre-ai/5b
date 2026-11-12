import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.database import demo_samples, initialize
from backend.membership import record_vip_purchase
from backend.rich_content import validate_blocks
from backend.demo_seed import FIRST_ID, seed, samples


class PlatformDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'test.sqlite3'
        initialize(self.path)

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.execute('PRAGMA foreign_keys = ON')
        return connection

    def account(self, identifier, expiry=None):
        with closing(self.connect()) as connection, connection:
            connection.execute(
                'INSERT INTO accounts '
                '(id, account_code, login_identifier, birth_year, invite_code, created_at, vip_expires_at) '
                'VALUES (?, ?, ?, 2016, ?, ?, ?)',
                (identifier, f'ACCOUNT-{identifier}', f'{identifier}@example.invalid',
                 f'INVITE-{identifier}', '2026-01-01T00:00:00Z', expiry)
            )

    def refer(self, inviter, invitee):
        with closing(self.connect()) as connection, connection:
            connection.execute(
                'INSERT INTO account_referrals (inviter_account_id, invitee_account_id, invite_code, registered_at) '
                'VALUES (?, ?, ?, ?)',
                (inviter, invitee, f'INVITE-{inviter}', '2026-01-01T00:00:00Z')
            )

    def test_calendar_month_end_leap_year_and_vietnam_boundary(self):
        cases = [
            ('2027-01-31T02:00:00Z', '2027-02-28T02:00:00Z'),
            ('2028-01-31T02:00:00Z', '2028-02-29T02:00:00Z'),
            ('2026-12-31T02:00:00Z', '2027-01-31T02:00:00Z'),
            ('2027-01-31T20:00:00Z', '2027-02-28T20:00:00Z'),
            ('2026-10-01T02:00:00Z', '2026-12-11T02:00:00Z'),
        ]
        for identifier, (expiry, expected) in enumerate(cases, 1):
            with self.subTest(expiry=expiry):
                self.account(identifier, expiry)
                record_vip_purchase(self.path, identifier, f'PAID-{identifier}', 1, '2026-11-11T02:00:00Z')
                with closing(self.connect()) as connection:
                    actual = connection.execute('SELECT vip_expires_at FROM accounts WHERE id = ?', (identifier,)).fetchone()[0]
                self.assertEqual(actual, expected)

    def test_referral_only_first_purchase_and_duplicate_delivery(self):
        self.account(1, '2027-01-31T02:00:00Z')
        self.account(2)
        self.refer(1, 2)
        first = record_vip_purchase(self.path, 2, 'FIRST', 1, '2026-11-11T02:00:00Z')
        duplicate = record_vip_purchase(self.path, 2, 'FIRST', 1, '2026-11-11T02:00:00Z')
        record_vip_purchase(self.path, 2, 'RENEWAL', 1, '2026-11-11T02:00:00Z')
        self.assertTrue(first['created'])
        self.assertFalse(duplicate['created'])
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notifications WHERE referral_id IS NOT NULL').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT vip_expires_at FROM accounts WHERE id=1').fetchone()[0], '2027-02-28T02:00:00Z')
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM vip_purchases WHERE account_id=2').fetchone()[0], 2)

    def test_concurrent_deliveries_apply_one_reward(self):
        self.account(1)
        self.account(2)
        self.refer(1, 2)
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(
                lambda _: record_vip_purchase(self.path, 2, 'CONCURRENT', 1, '2026-11-11T02:00:00Z'),
                range(10)
            ))
        self.assertEqual(sum(result['created'] for result in results), 1)
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notifications WHERE referral_id IS NOT NULL').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM vip_purchases').fetchone()[0], 1)

    def test_multiple_referrals_each_notify_and_accumulate(self):
        self.account(1)
        for invitee in (2, 3):
            self.account(invitee)
            self.refer(1, invitee)
            record_vip_purchase(self.path, invitee, f'PAID-{invitee}', 1, '2026-11-11T02:00:00Z')
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notifications WHERE account_id=1').fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT vip_expires_at FROM accounts WHERE id=1').fetchone()[0], '2027-01-11T02:00:00Z')

    def test_notification_failure_rolls_back_purchase_and_reward(self):
        self.account(1)
        self.account(2)
        self.refer(1, 2)
        with closing(self.connect()) as connection, connection:
            connection.execute(
                "CREATE TRIGGER fail_notification BEFORE INSERT ON notifications "
                "BEGIN SELECT RAISE(ABORT, 'forced failure'); END"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            record_vip_purchase(self.path, 2, 'ROLLBACK', 1, '2026-11-11T02:00:00Z')
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM vip_purchases').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT reward_status FROM account_referrals').fetchone()[0], 'pending')
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM accounts WHERE vip_expires_at IS NOT NULL').fetchone()[0], 0)

    def test_five_demo_cases_idempotent_and_internal_notification(self):
        seed(self.path)
        seed(self.path)
        report = demo_samples(self.path)
        self.assertEqual(len(report['cases']), 5)
        self.assertEqual(len(report['questions']), 5)
        self.assertEqual(report['cases'][0]['reward_vip_expires_at'], '2027-02-28T02:00:00Z')
        self.assertEqual(report['cases'][3]['reward_vip_expires_at'], '2026-12-11T02:00:00Z')
        internal = report['cases'][4]
        self.assertIsNone(internal['vip_expires_at'])
        self.assertEqual(internal['reward_count'], 0)
        self.assertEqual(internal['notifications'][0]['kind'], 'referral_contact_support')
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM accounts').fetchone()[0], 5)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notifications WHERE referral_id IS NOT NULL').fetchone()[0], 3)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_birth_year_and_referrer_are_fixed(self):
        seed(self.path)
        with closing(self.connect()) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute('UPDATE accounts SET birth_year=2017 WHERE id=?', (FIRST_ID,))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute('UPDATE account_referrals SET inviter_account_id=? WHERE id=?', (FIRST_ID + 4, FIRST_ID))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    'INSERT INTO account_referrals (inviter_account_id,invitee_account_id,invite_code,registered_at) '
                    'VALUES (?, ?, ?, ?)',
                    (FIRST_ID, FIRST_ID, 'DEMO-INVITE-01', '2026-11-11T02:00:00Z')
                )

    def test_rich_math_and_image_content_round_trip(self):
        seed(self.path)
        with closing(self.connect()) as connection:
            for prompt, solution in connection.execute('SELECT prompt_json, solution_steps_json FROM question_versions'):
                validate_blocks(json.loads(prompt))
                validate_blocks(json.loads(solution))
        for _, _, prompt, solution, _ in samples():
            validate_blocks(prompt)
            validate_blocks(solution)
        with self.assertRaises(ValueError):
            validate_blocks([{'type': 'math', 'latex': 'x', 'mathml': '<math xmlns="http://www.w3.org/1998/Math/MathML"><script>alert(1)</script></math>'}])

    def test_exam_snapshot_and_single_submission(self):
        seed(self.path)
        with closing(self.connect()) as connection, connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE question_versions SET prompt_json='[]' WHERE id=?", (FIRST_ID,))
            connection.execute(
                "INSERT INTO exam_attempts (id,exam_id,student_id,started_at,due_at,status) "
                "VALUES (1,?,?, '2026-11-11T02:00:00Z','2026-11-11T02:15:00Z','in_progress')",
                (FIRST_ID, FIRST_ID)
            )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute('UPDATE exam_items SET max_points=3 WHERE exam_id=?', (FIRST_ID,))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO exam_attempts (exam_id,student_id,started_at,due_at,status) "
                    "VALUES (?,?,'2026-11-11T02:00:00Z','2026-11-11T02:15:00Z','in_progress')",
                    (FIRST_ID, FIRST_ID)
                )

    def test_query_plans_use_indexes(self):
        seed(self.path)
        queries = [
            ("SELECT id FROM questions WHERE grade_id=5 AND topic_id=900001 ORDER BY id LIMIT 20", 'questions_pool'),
            ("SELECT id FROM notifications WHERE account_id=900001 ORDER BY created_at DESC,id DESC LIMIT 20", 'notifications_inbox'),
            ("SELECT id FROM exams WHERE owner_student_id=900001 ORDER BY created_at DESC,id DESC LIMIT 20", 'exams_owner_history'),
        ]
        with closing(self.connect()) as connection:
            for query, expected in queries:
                with self.subTest(index=expected):
                    plan = ' '.join(row[3] for row in connection.execute('EXPLAIN QUERY PLAN ' + query))
                    self.assertIn(expected, plan)
                    self.assertNotIn('TEMP B-TREE', plan)

    def test_migration_preserves_legacy_students_and_exams(self):
        legacy = Path(self.directory.name) / 'legacy.sqlite3'
        with closing(sqlite3.connect(legacy)) as connection:
            connection.executescript(Path('backend/migrations/0000_demo_base.sql').read_text(encoding='utf-8'))
            connection.execute("INSERT INTO students (student_code,full_name,grade_level) VALUES ('OLD','Old demo',5)")
            connection.execute("INSERT INTO exams (exam_code,title,grade_level,duration_minutes) VALUES ('OLD','Old demo',5,15)")
            connection.commit()
        initialize(legacy)
        initialize(legacy)
        with closing(sqlite3.connect(legacy)) as connection:
            self.assertEqual(connection.execute("SELECT student_code FROM students").fetchone()[0], 'OLD')
            self.assertEqual(connection.execute("SELECT exam_code FROM exams").fetchone()[0], 'OLD')

    def test_idempotency_key_cannot_change_purchase_owner(self):
        self.account(1)
        self.account(2)
        record_vip_purchase(self.path, 1, 'KEY', 1, '2026-11-11T02:00:00Z')
        with self.assertRaises(ValueError):
            record_vip_purchase(self.path, 2, 'KEY', 1, '2026-11-11T02:00:00Z')


if __name__ == '__main__':
    unittest.main()
