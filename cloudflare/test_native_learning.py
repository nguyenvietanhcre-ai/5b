"""Namespace isolation and transaction replay against a real SQLite engine."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_storage import FakeStorage
from sqlite_storage import StorageDatabase
from native_learning import CloudLearning
from learning_storage import rewrite,LearningDatabase
from backend import platform_api as api


class PublicNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.storage=FakeStorage();self.main=StorageDatabase(self.storage)
        self.learning=LearningDatabase(self.main)
        self.storage.db.execute('CREATE TABLE accounts(id INTEGER PRIMARY KEY,value TEXT)')
        self.main.run(lambda:self.create_learning())

    def create_learning(self):
        with self.learning.connect(True) as db:db.execute('CREATE TABLE accounts(id INTEGER PRIMARY KEY,value TEXT)')

    def tearDown(self):self.storage.db.close()

    def test_parameters_and_json_content_remain_literal(self):
        def insert():
            with self.learning.connect(True) as db:db.execute('INSERT INTO accounts VALUES (?,?)',(1,'accounts'))
        self.main.run(insert)
        self.assertEqual(self.storage.db.execute('SELECT value FROM native_learning_accounts').fetchone()[0],'accounts')
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM accounts').fetchone()[0],0)

    def test_schema_discovery_stays_in_namespace(self):
        with self.learning.connect() as db:
            self.assertEqual([row[0] for row in db.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')],['accounts'])

    def test_optional_or_unknown_tables_never_fall_back_to_main(self):
        self.storage.db.execute('CREATE TABLE private_main_only(value TEXT)')
        self.storage.db.execute('CREATE TABLE content_retirement_policy(grade INTEGER,enabled INTEGER)')
        self.storage.db.execute('INSERT INTO content_retirement_policy VALUES(5,1)')
        with self.learning.connect() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='content_retirement_policy'").fetchone())
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name=?",('private_main_only',)).fetchone())
            with self.assertRaises(Exception):db.execute('SELECT * FROM private_main_only')

    def test_both_namespaces_share_one_rollback(self):
        def fail():
            with self.main.connect(True) as db:db.execute("INSERT INTO accounts VALUES (1,'main')")
            with self.learning.connect(True) as db:db.execute("INSERT INTO accounts VALUES (1,'learning')")
            raise ValueError('synthetic rollback')
        with self.assertRaises(ValueError):self.main.run(fail)
        for name in ('accounts','native_learning_accounts'):
            self.assertEqual(self.storage.db.execute('SELECT count(*) FROM '+name).fetchone()[0],0)


@unittest.skipUnless((Path(__file__).resolve().parents[1]/'pilot-inputs/manifest.json').is_file(),'Private native-library fixture; run the local release gate')
class NativeLearningTests(unittest.TestCase):
    def setUp(self):
        self.old_origin=os.environ.get('MAM_TOAN_PUBLIC_ORIGIN')
        os.environ['MAM_TOAN_PUBLIC_ORIGIN']='https://5bmath.vn'
        self.storage=FakeStorage();self.main=StorageDatabase(self.storage)
        self.storage.db.execute('PRAGMA foreign_keys=ON')
        self.main.initialize();self.main.run(lambda:api.initialize_catalog(self.main))
        self.pilot=CloudLearning(self.main)
        self.main.run(self.pilot.path.initialize)
        self.handler=SimpleNamespace(server=SimpleNamespace(database_path=self.main,local_pilot=self.pilot,cloud_learning_provider=self.pilot,server_port=443),headers={'Host':'5bmath.vn','Origin':'https://5bmath.vn'},api_headers={})
        def register():
            with api.connect(self.main,True) as db:return api.register(self.handler,db,{'login':'cloud-native-test','password':'correct-password-123','name':'Học sinh thử','birthYear':2016})
        self.session=self.main.run(register)
        token=self.handler.api_headers['Set-Cookie'].split(';')[0]
        self.handler.headers.update(Cookie=token,**{'X-CSRF-Token':self.session['csrf_token']})

    def tearDown(self):
        if self.old_origin is None:os.environ.pop('MAM_TOAN_PUBLIC_ORIGIN',None)
        else:os.environ['MAM_TOAN_PUBLIC_ORIGIN']=self.old_origin
        self.storage.db.close()

    def call(self,method,path,body=None):
        return self.main.run(lambda:self.pilot.request(self.handler,method,path,body or {},{}))

    def test_namespaced_seed_and_authenticated_catalogue(self):
        result=self.call('GET','catalogue')
        self.assertEqual(len(result['questions']),60)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM accounts').fetchone()[0],1)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM native_learning_accounts').fetchone()[0],1)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM questions').fetchone()[0],0)
        self.assertGreater(self.storage.db.execute('SELECT count(*) FROM native_learning_questions').fetchone()[0],0)

    def test_namespace_rollback_is_atomic_with_main(self):
        def broken():
            with api.connect(self.main,True) as db:db.execute("UPDATE accounts SET login_identifier='changed'")
            with api.connect(self.pilot.path,True) as db:db.execute("INSERT INTO practice_requests VALUES (999,'x','x',999)")
            raise RuntimeError('intentional failure after both stores wrote')
        with self.assertRaises(Exception):self.main.run(broken)
        self.assertNotEqual(self.storage.db.execute('SELECT login_identifier FROM accounts').fetchone()[0],'changed')

    def test_sql_values_and_payloads_are_not_rewritten(self):
        sql,params=rewrite("INSERT INTO accounts(display_name) VALUES (?)",('accounts',))
        self.assertIn('native_learning_accounts',sql);self.assertEqual(params,('accounts',))
        sql,_=rewrite("SELECT 'accounts' FROM accounts")
        self.assertEqual(sql,"SELECT 'accounts' FROM native_learning_accounts")

    def test_foreign_origin_cannot_allocate(self):
        self.handler.headers['Origin']='https://evil.example'
        with self.assertRaises(api.APIError):self.call('POST','practice/quote',{})

if __name__=='__main__':unittest.main()
