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
    def test_migration_constraint_probe_stays_transactional_without_temp_database(self):
        storage=FakeStorage();database=StorageDatabase(storage)
        try:
            def probe(value):
                with database.connect(True) as db:
                    db.execute('CREATE TEMP TABLE mascot_rank_fk_check (violations INTEGER CHECK(violations=0))')
                    db.execute('INSERT INTO mascot_rank_fk_check VALUES(?)',(value,))
                    db.execute('DROP TABLE mascot_rank_fk_check')
            database.run(lambda:probe(0))
            with self.assertRaises(sqlite3.IntegrityError):database.run(lambda:probe(1))
            self.assertIsNone(storage.db.execute("SELECT name FROM sqlite_master WHERE name='mascot_rank_fk_check'").fetchone())
        finally:storage.db.close()

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

    def test_startup_system_catalog_does_not_create_sample_learning(self):
        from backend.platform_api import initialize_catalog
        self.database.run(lambda: initialize_catalog(self.database))
        self.database.run(lambda: initialize_catalog(self.database))
        for table in ('topics', 'lessons', 'questions', 'question_versions', 'media_assets'):
            self.assertEqual(self.storage.db.execute('SELECT count(*) FROM '+table).fetchone()[0], 0)
        self.assertGreater(self.storage.db.execute('SELECT count(*) FROM mascots').fetchone()[0], 0)

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

    def test_public_duel_auto_pair_claims_and_quota_in_storage_adapter(self):
        from backend import platform_api as api
        from backend.arena_qa_source import ArenaQAQuestionSource
        from unittest.mock import patch
        handler=SimpleNamespace(server=SimpleNamespace(database_path=self.database,arena=self.arena),headers={'Host':'5bmath.vn'},api_headers={})
        users=[];credential=api.password_hash('claims-duel-storage-only')
        def setup():
            users.clear();api.initialize_catalog(self.database)
            with self.database.connect(True) as db:
                for index in range(2):users.append(dict(api.register(handler,db,{'login':'claims-duel-'+str(index),'name':'Mầm Xanh','birthYear':api.academic()[0]-9,'password':'claims-duel-storage-only'},credential)))
        self.database.run(setup)
        def enter(index):
            def callback():
                with self.database.connect(True) as db:return api.arena_request(handler,db,users[index],{'action':'quick','scope':'all','requestKey':'storage-duel-key-'+str(index)})
            return self.database.run(callback)
        with patch('backend.question_bank.arena_questions',return_value=ArenaQAQuestionSource().questions(4)):
            first=enter(0);second=enter(1)
        self.assertEqual(first['code'],second['code']);self.assertEqual(self.arena.rooms[first['code']]['status'],'preparing')
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM game_claims').fetchone()[0],2)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],2)

    def test_account_game_claims_and_json_membership_in_storage_adapter(self):
        from backend import platform_api as api, game_claims as claims
        from backend.group_game_bots import BotGroupGames
        from backend.group_games_qa import synthetic_source
        game=BotGroupGames(synthetic_source(),qa_only=True,policy_approved=True)
        handler=SimpleNamespace(server=SimpleNamespace(database_path=self.database,arena=self.arena,group_games=game),headers={},api_headers={})
        principal=[];credential=api.password_hash('claims-storage-only')
        def setup():
            principal.clear();api.initialize_catalog(self.database)
            with self.database.connect(True) as db:
                principal.append(dict(api.register(handler,db,{'login':'claims-storage-player','name':'Mầm Xanh','birthYear':api.academic()[0]-10,'password':'claims-storage-only'},credential)))
        self.database.run(setup)
        def admit():
            with self.database.connect(True) as db:return claims.group_admission(handler,db,principal[0],game,{'mode':'capture_flag','requestKey':'storage-claims-key'},'create',5)
        first=self.database.run(admit);again=self.database.run(admit)
        self.assertEqual(first['gameClaim']['claimId'],again['gameClaim']['claimId'])
        def conflict():
            with self.database.connect(True) as db:return claims.bot_start(handler,db,principal[0],{'requestKey':'storage-bot-conflict'},lambda: (_ for _ in ()).throw(AssertionError('must reject before bank/consume')))
        with self.assertRaises(APIError) as error:self.database.run(conflict)
        self.assertEqual(error.exception.status,409)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM game_claims').fetchone()[0],1)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM daily_usage').fetchone()[0],0)

    def test_group_games_durable_rooms_and_exactly_once_xp_in_storage_adapter(self):
        from backend import platform_api as api
        from backend.group_games import GroupGames, leaderboard
        from backend.group_games_qa import synthetic_source
        self.database.initialize()
        users=[]
        credential=api.password_hash('synthetic-storage-only')
        def setup():
            api.initialize_catalog(self.database)
            with self.database.connect(True) as db:
                for index in range(5):
                    handler=SimpleNamespace(server=SimpleNamespace(),headers={},api_headers={})
                    users.append(dict(api.register(handler,db,{'login':f'storage-player-{index}','name':'Mầm Xanh','birthYear':api.academic()[0]-10,'password':'synthetic-storage-only'},credential)))
        # Register callback replays at first write; keep request-local outputs
        # separate from any previous preflight to mirror HTTP return semantics.
        def setup_replay():
            users.clear()
            return setup()
        self.database.run(setup_replay)
        clock=[1000000]
        game=GroupGames(synthetic_source(),qa_only=True,policy_approved=True,clock=lambda:clock[0])
        def create():
            with self.database.connect(True) as db:return game.enter(db,users[0],{'mode':'animal_race','requestKey':'storage-create-1'},'create',5)
        room=self.database.run(create)
        for index in range(1,5):
            def join():
                with self.database.connect(True) as db:return game.enter(db,users[index],{'code':room['code'],'requestKey':f'storage-join-{index}'},'join',5)
            room=self.database.run(join)
        for turn in range(5):
            for index in range(5 if turn<4 else 1):
                clock[0]+=100
                def answer():
                    with self.database.connect(True) as db:
                        raw=game._load(db,room['id'])
                        return game.mutate(db,users[index],room['id'],{'round':turn+1,'answer':raw['questions'][turn]['answer'] if index==0 else '999','requestKey':f'storage-answer-{turn}-{index}'},'answer')
                room=self.database.run(answer)
            if turn<4:
                clock[0]+=3000
                def poll():
                    with self.database.connect(True) as db:
                        raw=game._load(db,room['id']);game._tick(db,raw,clock[0]);return game.view(raw,users[0]['student_id'],clock[0])
                room=self.database.run(poll)
        self.assertEqual(room['winnerId'],users[0]['student_id'])
        for _ in range(3):
            def retry_final():
                with self.database.connect(True) as db:return game.mutate(db,users[0],room['id'],{'round':5,'answer':game._load(db,room['id'])['questions'][4]['answer'],'requestKey':'storage-answer-4-0'},'answer')
            room=self.database.run(retry_final)
        def check():
            with self.database.connect() as db:
                self.assertEqual(db.execute('SELECT SUM(xp) FROM student_companions').fetchone()[0],15)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM group_game_rewards').fetchone()[0],5)
                self.assertEqual(leaderboard(db,{'kind':['animal_race']})['total'],5)
        self.database.run(check)


if __name__ == '__main__':
    unittest.main()
