"""Adapter invariants; actual platform behavior is gated by test_runtime.py."""
import importlib.util
import sqlite3
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.arena import Arena
from backend.platform_api import APIError
from sqlite_storage import Connection, REQUEST_SCOPE, StorageDatabase, bind_parameters
import transfer


class FakeCursor:
    def __init__(self, cursor):
        self.columnNames = [field[0] for field in cursor.description or ()]
        self.rows = cursor.fetchall()

    def raw(self):
        return self.rows

    def one(self):
        if len(self.rows) != 1:
            raise ValueError('Expected one result')
        return dict(zip(self.columnNames, self.rows[0]))

    def __iter__(self):
        return iter([dict(zip(self.columnNames, row)) for row in self.rows])


class FakeStorage:
    def __init__(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.sql = self
        self.depth = 0
        self.writes = []

    def exec(self, sql, *params):
        self.writes.append(sql)
        return FakeCursor(self.db.execute(sql, params))

    def transactionSync(self, callback):
        self.depth += 1
        name = 'storage_' + str(self.depth)
        self.db.execute('SAVEPOINT ' + name)
        try:
            result = callback()
            self.db.execute('RELEASE ' + name)
            return result
        except BaseException:
            self.db.execute('ROLLBACK TO ' + name)
            self.db.execute('RELEASE ' + name)
            raise
        finally:
            self.depth -= 1


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = FakeStorage()
        self.arena = Arena()
        self.database = StorageDatabase(self.storage, self.arena)
        self.database.initialize()
        self.storage.exec('CREATE TABLE ledger(id INTEGER PRIMARY KEY,value TEXT)')

    def tearDown(self):
        self.storage.db.close()
        self.assertIsNone(REQUEST_SCOPE.get())

    def rows(self):
        return self.storage.db.execute('SELECT * FROM ledger ORDER BY id').fetchall()

    def test_parameters_preserve_int64_and_question_mark_literals(self):
        statement, values = bind_parameters("SELECT ?, '?' AS literal, ? -- ? ignored\n", (2**63 - 1, b'bytes'))
        self.assertIn('CAST(? AS INTEGER)', statement)
        self.assertEqual(values[0], str(2**63 - 1))
        self.assertEqual(self.storage.db.execute(statement, values).fetchone(), (2**63 - 1, '?', b'bytes'))
        with self.assertRaises(sqlite3.ProgrammingError):
            bind_parameters('SELECT ?', (1, 2))

    def test_api_error_rolls_back_sql_and_restores_arena(self):
        def write():
            with self.database.connect(True) as db:
                db.execute('INSERT INTO ledger VALUES (?,?)', (1, 'uncommitted'))
                self.arena.rooms['bad'] = {'id': 'bad'}
                raise APIError('Quota rejected', 429)

        with self.assertRaises(APIError) as caught:
            self.database.run(write)
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.arena.rooms, {})

    def test_explicit_commit_survives_later_rejection(self):
        def request():
            with self.database.connect(True) as db:
                if not db.execute('SELECT 1 FROM ledger WHERE id=1').fetchone():
                    db.execute('INSERT INTO ledger VALUES (1,?)', ('settled',))
                    self.arena.rooms['settled'] = {'id': 'settled'}
                    db.commit()
                db.execute('INSERT INTO ledger VALUES (2,?)', ('rejected admission',))
                self.arena.rooms['rejected'] = {'id': 'rejected'}
                raise APIError('Quota rejected', 429)

        with self.assertRaises(APIError):
            self.database.run(request)
        self.assertEqual(self.rows(), [(1, 'settled')])
        self.assertEqual(set(self.arena.rooms), {'settled'})
        restored = StorageDatabase(self.storage, Arena())
        restored.restore_arena()
        self.assertEqual(set(restored.arena.rooms), {'settled'})

    def test_nested_atomic_rollback_can_be_caught_by_outer_transaction(self):
        def request():
            with self.database.connect(True) as db:
                db.execute('INSERT INTO ledger VALUES (1,?)', ('before',))

                def incomplete_upload():
                    db.execute('INSERT INTO ledger VALUES (2,?)', ('partial chunk',))
                    raise APIError('Upload rejected')

                try:
                    db.atomic(incomplete_upload)
                except APIError:
                    pass
                return db.execute('INSERT INTO ledger VALUES (3,?)', ('after',)).lastrowid

        self.assertEqual(self.database.run(request), 3)
        self.assertEqual(self.rows(), [(1, 'before'), (3, 'after')])

    def test_other_request_committed_during_preflight_is_not_reverted(self):
        arrived = False

        def concurrent_write():
            with self.database.connect(True) as db:
                self.arena.rooms['other'] = {'id': 'other'}
                db.execute('INSERT INTO ledger VALUES (1,?)', ('other request',))

        def slow_login():
            nonlocal arrived
            scope = REQUEST_SCOPE.get()
            if not scope.transaction and not arrived:
                arrived = True
                self.database.run(concurrent_write)
            with self.database.connect(True) as db:
                db.execute('INSERT INTO ledger VALUES (2,?)', ('login session',))

        self.database.run(slow_login)
        self.assertEqual(self.rows(), [(1, 'other request'), (2, 'login session')])
        self.assertEqual(set(self.arena.rooms), {'other'})

    def test_arena_persists_only_changed_room_rows(self):
        def request():
            with self.database.connect(True):
                self.arena.rooms['one'] = {'id': 'one', 'players': {}}

        self.database.run(request)
        before = sum(sql.startswith('INSERT INTO cloudflare_arena_rooms') for sql in self.storage.writes)
        self.database.run(request)
        after = sum(sql.startswith('INSERT INTO cloudflare_arena_rooms') for sql in self.storage.writes)
        self.assertEqual(before, 1)
        self.assertEqual(after, before)

    def test_arena_answer_history_restores_integer_question_keys(self):
        def write():
            with self.database.connect(True):
                self.arena.rooms['answered'] = {'id': 'answered', 'players': {'token': {'answers': {0: 'A', 1: 'B'}}}}

        self.database.run(write)
        restored = StorageDatabase(self.storage, Arena())
        restored.restore_arena()
        self.assertEqual(restored.arena.rooms['answered']['players']['token']['answers'], {0: 'A', 1: 'B'})

    def test_operator_import_flag_and_numeric_validation(self):
        env = SimpleNamespace(OPERATOR_TOKEN='x' * 32, TRANSFER_ENABLED='false')
        headers = {'Authorization': 'Bearer ' + 'x' * 32}
        transfer.authorize(env, headers)
        with self.assertRaises(APIError) as caught:
            transfer.authorize(env, headers, importing=True)
        self.assertEqual(caught.exception.status, 404)
        with self.assertRaises(APIError):
            transfer.authorize(env, {'Authorization': 'Bearer wrong'})
        for value in ('nan', 'inf', '-inf'):
            with self.subTest(value=value), self.assertRaises(APIError):
                transfer._parameter({'real': value})


if __name__ == '__main__':
    unittest.main()
