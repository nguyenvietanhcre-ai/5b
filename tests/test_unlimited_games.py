"""Game-only opt-in keeps the real daily ledger and practice limits intact."""
import json
import os
import sqlite3
import unittest
from unittest.mock import patch

from backend.learning_update import consume, membership, unlimited_games, usage
from backend.platform_api import APIError


class UnlimitedGamesTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript('''
            CREATE TABLE accounts(id INTEGER PRIMARY KEY,vip_expires_at TEXT,vip_plus_expires_at TEXT);
            INSERT INTO accounts VALUES(1,NULL,NULL);
            CREATE TABLE access_entitlements(account_id INTEGER,starts_at TEXT,ends_at TEXT);
            CREATE TABLE child_referral_periods(account_id INTEGER,tier TEXT,starts_at TEXT,ends_at TEXT);
            CREATE TABLE system_settings(name TEXT PRIMARY KEY,value_json TEXT,revision INTEGER);
            CREATE TABLE daily_usage(
                student_id INTEGER NOT NULL,day TEXT NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('content','combined','human','bot')),
                request_key TEXT NOT NULL,PRIMARY KEY(student_id,category,request_key));
        ''')
        self.limits = {'content': 1, 'combined': 1, 'human': 3, 'bot': 5}
        self.db.execute('INSERT INTO system_settings VALUES(?,?,1)',
                        ('platform', json.dumps({'free_limits': self.limits})))
        self.session = {'account_id': 1, 'student_id': 1}
        env = patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': ''})
        env.start()
        self.addCleanup(env.stop)

    def consume_many(self, category, count):
        for index in range(count):
            key = f'{category}-{index}'
            consume(self.db, self.session, category, key)
            consume(self.db, self.session, category, key)

    def assert_exhausted(self, category):
        with self.assertRaises(APIError) as caught:
            consume(self.db, self.session, category, category + '-extra')
        self.assertEqual(caught.exception.status, 429)

    def test_flag_requires_explicit_one(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(unlimited_games())
        for value in ('', '0', 'true', 'yes', ' 1', '1 '):
            with self.subTest(value=value), patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': value}):
                self.assertFalse(unlimited_games())
        with patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '1'}):
            self.assertTrue(unlimited_games())

    def test_free_games_exceed_old_limits_and_still_record_once(self):
        self.assertEqual(membership(self.db, self.session), 'Free')
        with patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '1'}):
            self.consume_many('human', 8)
            self.consume_many('bot', 9)
            actual = usage(self.db, self.session)
            self.assertEqual(actual['human'], {'used': 8, 'limit': None})
            self.assertEqual(actual['bot'], {'used': 9, 'limit': None})
            self.assertEqual(self.db.execute('SELECT count(*) FROM daily_usage').fetchone()[0], 17)
        # Disabling the temporary policy restores the cap against the same ledger.
        self.assert_exhausted('human')
        self.assert_exhausted('bot')

    def test_free_practice_caps_remain_one_when_games_unlimited(self):
        with patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '1'}):
            for category in ('content', 'combined'):
                self.consume_many(category, 1)
                self.assert_exhausted(category)
                self.assertEqual(usage(self.db, self.session)[category], {'used': 1, 'limit': 1})

    def test_default_free_game_caps_remain_three_and_five(self):
        for category, limit in (('human', 3), ('bot', 5)):
            self.consume_many(category, limit)
            self.assert_exhausted(category)
            self.assertEqual(usage(self.db, self.session)[category], {'used': limit, 'limit': limit})

    def test_override_preserves_configured_practice_limits_and_settings(self):
        configured = {'content': 2, 'combined': 4, 'human': 0, 'bot': 0}
        payload = json.dumps({'free_limits': configured})
        self.db.execute('UPDATE system_settings SET value_json=?', (payload,))
        with patch.dict(os.environ, {'MAM_TOAN_UNLIMITED_GAMES': '1'}):
            actual = usage(self.db, self.session)
            self.assertEqual({key: actual[key]['limit'] for key in configured},
                             {'content': 2, 'combined': 4, 'human': None, 'bot': None})
            self.consume_many('human', 1)
            self.consume_many('bot', 1)
        self.assertEqual(self.db.execute('SELECT value_json,revision FROM system_settings').fetchone()[:],
                         (payload, 1))

    def test_existing_paid_roles_remain_unlimited_without_flag(self):
        for role in ('VIP', 'VIP+', 'SVip'):
            with self.subTest(role=role):
                self.db.execute('UPDATE accounts SET vip_expires_at=NULL,vip_plus_expires_at=NULL')
                self.db.execute('DELETE FROM access_entitlements')
                self.db.execute('DELETE FROM daily_usage')
                if role == 'SVip':
                    self.db.execute("INSERT INTO access_entitlements VALUES(1,'2000-01-01T00:00:00Z',NULL)")
                else:
                    column = 'vip_expires_at' if role == 'VIP' else 'vip_plus_expires_at'
                    self.db.execute(f"UPDATE accounts SET {column}='2999-01-01T00:00:00Z'")
                self.assertEqual(membership(self.db, self.session), role)
                for category in ('content', 'combined', 'human', 'bot'):
                    self.consume_many(category, 6)
                    self.assertEqual(usage(self.db, self.session)[category], {'used': 6, 'limit': None})


if __name__ == '__main__':
    unittest.main()
