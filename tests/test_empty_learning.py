"""No automatic sample content, and safe learning flows with an empty bank."""
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, initialize_catalog, seed_catalog, stamp, now
from datetime import timedelta
from backend.staff_api import create_first_admin
from test_platform_api import Client
from test_staff_api import StaffClient


class EmptyLearningTests(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'empty.sqlite3'
        initialize(self.path)
        initialize_catalog(self.path)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())

    def student(self):
        client = Client(self.server)
        login, password = 'empty-' + secrets.token_hex(6), secrets.token_urlsafe(16)
        result = client.call('auth/register', {'login':login, 'password':password,
                            'name':'Bạn học', 'birthYear':academic()[0]-10})
        return client, result, login, password

    def snapshot(self):
        with connect(self.path) as db:
            return {r[0]: [tuple(row) for row in db.execute('SELECT * FROM "'+r[0]+'" ORDER BY rowid')]
                    for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

    def test_system_initialization_never_seeds_or_reads_sample_catalog(self):
        with patch('backend.platform_api.Path', side_effect=AssertionError('No sample files on startup')):
            initialize_catalog(self.path)
        with connect(self.path) as db:
            for table in ('topics','lessons','questions','question_versions','media_assets'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0], 0)
            self.assertGreater(db.execute('SELECT count(*) FROM mascots').fetchone()[0], 0)

    def test_existing_content_and_account_rows_are_unchanged_on_restart(self):
        seed_catalog(self.path)  # explicit fixture, never application startup
        client, state, _, _ = self.student()
        client.call('lessons/'+state['lessons'][0]['id']+'/complete', {})
        client.call('exams', {'requestKey':secrets.token_hex(10), 'difficulty':0})
        before = self.snapshot()
        initialize(self.path)
        initialize_catalog(self.path)
        initialize_catalog(self.path)
        self.assertEqual(before, self.snapshot())

    def test_empty_bank_keeps_auth_profile_mascot_history_and_leaderboard_working(self):
        client, state, login, password = self.student()
        self.assertEqual(state['lessons'], [])
        self.assertFalse(state['questionBankReady'])
        client.call('profile', {'name':'Học sinh mới'})
        client.call('mascot', {'mascot':'sprout'})
        self.assertEqual(client.call('session')['state']['exams'], {})
        self.assertIn('rows', client.call('leaderboard?kind=battle&period=all'))
        client.call('auth/logout', {})
        self.assertTrue(client.call('auth/login', {'login':login, 'password':password})['authenticated'])

    def test_withdrawn_content_keeps_existing_attempt_reviewable(self):
        seed_catalog(self.path)
        client, _, _, _ = self.student()
        exam = client.call('exams', {'requestKey':secrets.token_hex(10)})['exam']
        with connect(self.path, True) as db:
            db.execute("UPDATE lessons SET publication_status='draft'")
            db.execute("UPDATE question_versions SET status='retired'")
        initialize_catalog(self.path)
        state = client.call('session')
        self.assertEqual(state['lessons'], [])
        self.assertFalse(state['questionBankReady'])
        self.assertIn(exam['id'], state['state']['exams'])
        reviewed = client.call('exams/'+exam['id']+'/submit', {})['exam']
        self.assertEqual(len(reviewed['questions']), 10)
        self.assertTrue(reviewed['submittedAt'])

    def test_empty_bank_rejects_new_exams_and_matches_without_usage_or_fallback(self):
        client, _, _, _ = self.student()
        before = self.snapshot()
        requests = [('exams', {'difficulty':0}),
                    ('exams', {'category':'content','maxWeek':academic()[1]}),
                    ('exams', {'category':'content','topic':'missing','count':3}),
                    ('bot/start', {'scope':'all'}), ('bot/start', {'scope':'weekly'}),
                    ('arena', {'action':'create','scope':'all'}),
                    ('arena', {'action':'quick','scope':'weekly'})]
        with patch.object(self.server.arena, '_questions', side_effect=AssertionError('No generated fallback')):
            for endpoint, body in requests:
                with self.subTest(endpoint=endpoint, body=body):
                    with self.assertRaises(APIError) as caught:
                        client.call(endpoint, {**body, 'requestKey':secrets.token_hex(10)})
                    self.assertIn('câu hỏi', str(caught.exception))
        after = self.snapshot()
        for table in ('daily_usage','exams','exam_attempts','duels','arena_members','xp_events','questions'):
            self.assertEqual(before[table], after[table], table)
        self.assertEqual(self.server.arena.rooms, {})

    def test_bot_receives_only_published_database_questions(self):
        seed_catalog(self.path)
        client, _, _, _ = self.student()
        result = client.call('bot/start', {'requestKey':secrets.token_hex(10), 'scope':'all'})
        self.assertEqual(len(result['questions']), 20)
        with connect(self.path) as db:
            for question in result['questions']:
                self.assertEqual(db.execute('SELECT status FROM question_versions WHERE id=?',
                                            (question['questionVersionId'],)).fetchone()[0], 'published')

    def test_admin_can_inspect_empty_content_lists(self):
        password = secrets.token_urlsafe(16)
        create_first_admin(self.path, 'empty-admin', 'Quản trị', password)
        staff = StaffClient(self.server)
        staff.call('login', {'login':'empty-admin','password':password})
        for kind in ('topics','lessons','questions'):
            result = staff.call('content?kind='+kind+'&grade=5')
            self.assertEqual(result['total'], 0)
            self.assertEqual(result['rows'], [])

    def test_paid_empty_bank_has_no_school_exam_or_sample_download(self):
        client, state, _, _ = self.student()
        with connect(self.path, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',
                       (stamp(now()+timedelta(days=30)),state['account']['id']))
        with self.assertRaises(APIError) as caught:
            client.call('exams', {'category':'school','school':'cau-giay','requestKey':secrets.token_hex(10)})
        self.assertEqual(caught.exception.status,403)
        self.assertIn('VIP+', str(caught.exception))
        with self.assertRaises(APIError) as caught:
            client.call('materials')
        self.assertEqual(caught.exception.status,404)
        self.assertIn('đang được cập nhật', str(caught.exception))
