"""Learning appearance is an authenticated, isolated student preference."""
import secrets
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena
from backend.database import BACKEND, initialize
from backend.platform_api import (APIError, DEFAULT_THEME, LEARNING_THEMES, academic,
                                  connect, seed_catalog)
from test_platform_api import Client


class LearningThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='learning-themes-', dir=work)
        cls.template = Path(cls.directory.name) / 'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path = Path(self.directory.name) / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.template)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())

    def user(self):
        client = Client(self.server)
        login = 'theme-' + secrets.token_hex(6)
        password = secrets.token_urlsafe(18)
        state = client.call('auth/register', {'login': login, 'password': password,
                            'name': 'Mầm giao diện', 'birthYear': academic()[0] - 10})
        return client, state, login, password

    def test_all_themes_persist_through_logout_new_session_and_preserve_learning(self):
        client, initial, login, password = self.user()
        self.assertEqual(initial['state']['theme'], 'garden-adventure')
        lesson = initial['lessons'][0]['id']
        completed = client.call(f'lessons/{lesson}/complete', {})['state']['completed']
        for theme in sorted(LEARNING_THEMES):
            with self.subTest(theme=theme):
                saved = client.call('preferences', {'theme': theme})
                self.assertTrue(saved['authenticated'])
                self.assertEqual(saved['state']['theme'], theme)
                self.assertEqual(saved['state']['lastLesson'], lesson)
                self.assertEqual(saved['state']['completed'], completed)
                self.assertEqual(client.call('session')['state']['theme'], theme)
        client.call('preferences', {'theme': 'clay-sprout'})
        client.call('auth/logout', {})
        self.assertFalse(client.call('session')['authenticated'])
        initialize(self.path)
        resumed = Client(SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena()))
        logged = resumed.call('auth/login', {'login': login, 'password': password})
        self.assertEqual(logged['state']['theme'], 'clay-sprout')
        self.assertEqual(logged['state']['completed'], completed)
        self.assertEqual(logged['state']['lastLesson'], lesson)

    def test_preferences_are_per_student_and_missing_row_defaults_then_upserts(self):
        first, initial, _, _ = self.user()
        second, other, _, _ = self.user()
        first.call('preferences', {'theme': 'garden-notebook'})
        self.assertEqual(second.call('session')['state']['theme'], DEFAULT_THEME)
        with connect(self.path, True) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (other['account']['id'],)).fetchone()[0]
            db.execute('DELETE FROM learning_preferences WHERE student_id=?', (sid,))
        self.assertEqual(second.call('session')['state']['theme'], DEFAULT_THEME)
        self.assertEqual(second.call('preferences', {'theme': 'morning-garden'})['state']['theme'], 'morning-garden')
        self.assertEqual(first.call('session')['state']['theme'], 'garden-notebook')
        self.assertNotEqual(initial['account']['id'], other['account']['id'])

    def test_invalid_preferences_authentication_and_csrf_cannot_write(self):
        client, _, _, _ = self.user()
        client.call('preferences', {'theme': 'crayon-workshop'})
        for body in ({}, {'theme': 'unknown'}, {'theme': 'GARDEN-ADVENTURE'},
                     {'theme': '../custom.css'}, {'theme': ''}, {'theme': None},
                     {'theme': 4}, {'theme': True}, {'theme': ['clay-sprout']},
                     {'theme': {'id': 'clay-sprout'}}, {'theme': 'clay-sprout', 'studentId': 1},
                     ['garden-adventure']):
            with self.subTest(body=body):
                with self.assertRaises(APIError) as caught:
                    client.call('preferences', body)
                self.assertEqual(caught.exception.status, 400)
                self.assertEqual(client.call('session')['state']['theme'], 'crayon-workshop')
        client.csrf = 'invalid'
        with self.assertRaises(APIError) as caught:
            client.call('preferences', {'theme': 'clay-sprout'})
        self.assertEqual(caught.exception.status, 403)
        client.call('session')
        client.headers['Origin'] = 'https://other.invalid'
        with self.assertRaises(APIError) as caught:
            client.call('preferences', {'theme': 'clay-sprout'})
        self.assertEqual(caught.exception.status, 403)
        client.headers['Origin'] = 'http://localhost:8765'
        self.assertEqual(client.call('session')['state']['theme'], 'crayon-workshop')
        stranger = Client(self.server)
        with self.assertRaises(APIError) as caught:
            stranger.call('preferences', {'theme': 'clay-sprout'})
        self.assertEqual(caught.exception.status, 401)

    def test_migration_adds_default_without_changing_existing_rows_and_is_idempotent(self):
        old_root = Path(self.directory.name) / 'legacy-migrations'
        (old_root / 'migrations').mkdir(parents=True)
        for source in (BACKEND / 'migrations').glob('*.sql'):
            if source.name < '0017':
                shutil.copy2(source, old_root / 'migrations' / source.name)
        legacy = old_root / 'legacy.sqlite3'
        with patch('backend.database.BACKEND', old_root):
            initialize(legacy)
        with connect(legacy, True) as db:
            db.execute("INSERT INTO students(student_code,full_name,grade_level) VALUES ('THEME-OLD','Học sinh cũ',5)")
            sid = db.execute("SELECT id FROM students WHERE student_code='THEME-OLD'").fetchone()[0]
            db.execute('INSERT INTO learning_preferences(student_id,last_lesson) VALUES (?,?)', (sid, 'legacy-lesson'))
            tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                                   "AND name NOT LIKE 'sqlite_%' AND name<>'schema_migrations'")]
            columns = {table: [row['name'] for row in db.execute('PRAGMA table_info("' + table + '")')]
                       for table in tables}
            rows = {table: [tuple(row) for row in db.execute('SELECT * FROM "' + table + '"')]
                    for table in tables}
        initialize(legacy)
        initialize(legacy)
        with connect(legacy) as db:
            for table in tables:
                with self.subTest(table=table):
                    selected = ','.join('"' + name + '"' for name in columns[table])
                    self.assertEqual(rows[table], [tuple(row) for row in db.execute('SELECT ' + selected + ' FROM "' + table + '"')])
            preference = db.execute('SELECT * FROM learning_preferences WHERE student_id=?', (sid,)).fetchone()
            self.assertEqual(preference['last_lesson'], 'legacy-lesson')
            self.assertEqual(preference['theme'], DEFAULT_THEME)
            self.assertEqual(db.execute("SELECT count(*) FROM schema_migrations WHERE name='0017_learning_themes.sql'").fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        with self.assertRaises(sqlite3.IntegrityError):
            with connect(legacy, True) as db:
                db.execute('UPDATE learning_preferences SET theme=? WHERE student_id=?', ('unknown', sid))


if __name__ == '__main__':
    unittest.main()
