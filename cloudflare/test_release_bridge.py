"""Provider replay must never yield or call a remote API inside SQL storage."""
import unittest
from test_storage import FakeStorage
from sqlite_storage import StorageDatabase,NeedsExternal,REQUEST_SCOPE
from backend.platform_api import APIError
from types import SimpleNamespace
from unittest.mock import patch
from backend import platform_api as api,bunny_stream as bunny
import release_bridge as bridge

class ExternalReplayTests(unittest.TestCase):
    def setUp(self):
        self.storage=FakeStorage();self.database=StorageDatabase(self.storage)
        self.storage.exec('CREATE TABLE probe(id INTEGER PRIMARY KEY,value TEXT)')
    def tearDown(self):self.storage.db.close()
    def test_remote_call_runs_after_rollback_and_once_before_successful_replay(self):
        calls=[];key=('provider','safe-fixture')
        def perform():
            self.assertFalse(REQUEST_SCOPE.get().transaction)
            self.assertEqual(self.storage.db.execute('SELECT count(*) FROM probe').fetchone()[0],0)
            calls.append(True);return 'ready'
        def callback():
            with self.database.connect(True) as db:
                db.execute('INSERT INTO probe VALUES (1,?)',('before-io',))
                scope=REQUEST_SCOPE.get()
                if key not in scope.crypto:raise NeedsExternal(key,perform)
                db.execute('UPDATE probe SET value=? WHERE id=1',(scope.crypto[key],))
                return 'success'
        self.assertEqual(self.database.run(callback),'success')
        self.assertEqual(calls,[True])
        self.assertEqual(self.storage.db.execute('SELECT value FROM probe').fetchone()[0],'ready')
        self.assertIsNone(REQUEST_SCOPE.get())
    def test_later_authorization_failure_rolls_back_sql_after_remote_read(self):
        key=('provider','read');calls=[]
        def callback():
            with self.database.connect(True) as db:
                db.execute('INSERT INTO probe VALUES(1,?)',('tentative',))
                if key not in REQUEST_SCOPE.get().crypto:raise NeedsExternal(key,lambda:(calls.append(True),'cached')[1])
                raise APIError('ownership changed',403)
        with self.assertRaises(APIError):self.database.run(callback)
        self.assertEqual(calls,[True]);self.assertEqual(self.storage.db.execute('SELECT count(*) FROM probe').fetchone()[0],0)
    def test_external_result_never_survives_request_scope(self):
        key=('provider','request-local');calls=[]
        def callback():
            scope=REQUEST_SCOPE.get()
            if key not in scope.crypto:raise NeedsExternal(key,lambda:(calls.append(True),'one')[1])
            return scope.crypto[key]
        self.assertEqual(self.database.run(callback),'one')
        self.assertEqual(self.database.run(callback),'one')
        self.assertEqual(len(calls),2)
    def test_committed_rejection_does_not_repeat_attempt_counter(self):
        attempts=[]
        def callback():
            with self.database.connect(True) as db:
                attempts.append(True)
                db.execute("INSERT INTO probe VALUES(1,'failed-once')")
                db.commit_and_raise(APIError('PIN chưa đúng.',403))
        with self.assertRaises(APIError):self.database.run(callback)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM probe').fetchone()[0],1)
        self.assertEqual(attempts,[True])

class BunnyReplayTests(unittest.TestCase):
    def setUp(self):
        self.storage=FakeStorage();self.database=StorageDatabase(self.storage)
        self.database.initialize();self.database.run(lambda:api.seed_catalog(self.database))
        self.storage.db.execute("UPDATE lessons SET client_key='qa.bunny' WHERE id=(SELECT min(id) FROM lessons)")
        self.server=SimpleNamespace(bunny_stream_transport=bridge.bunny_transport,bunny_upload_lifecycle=bridge.bunny_lifecycle)
        self.body={'provider':'main','lessonKey':'qa.bunny','requestKey':'qa-request-'+'a'*20,'size':100}
        self.config=bunny.Config(12345,'fixture-key','fixture-token')
        self.creates=0;self.videos={};self.lose_reply=False;self.reject=False
        self.enterContext(patch.object(bridge,'provider_fetch',self.fetch))
    def tearDown(self):self.storage.db.close()
    def fetch(self,method,path,key,payload):
        self.assertFalse(REQUEST_SCOPE.get().transaction)
        if method=='POST':
            if self.reject:raise bunny._ProviderRejection()
            self.creates+=1
            video={'guid':'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee','videoLibraryId':12345,'title':payload['title'],'status':0,'length':0,'storageSize':0}
            self.videos[video['guid']]=video
            if self.lose_reply:self.lose_reply=False;raise OSError('synthetic lost response')
            return dict(video)
        if '?' in path:return {'items':list(self.videos.values())}
        return dict(self.videos[path.rsplit('/',1)[1]])
    def call(self):
        def callback():
            with self.database.connect(True) as db:return bunny.create_upload(self.server,db,{'id':1},self.body,self.config)
        return self.database.run(callback)
    def test_new_upload_and_same_request_retry_create_only_one_remote_video(self):
        first=self.call();again=self.call()
        self.assertEqual(first['upload']['id'],again['upload']['id']);self.assertEqual(self.creates,1)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM bunny_stream_uploads').fetchone()[0],1)
    def test_uncertain_reply_keeps_reservation_and_recovers_without_another_post(self):
        self.lose_reply=True
        with self.assertRaises(APIError):self.call()
        self.assertEqual(self.storage.db.execute('SELECT state FROM bunny_stream_uploads').fetchone()[0],'creating')
        restored=self.call();self.assertEqual(restored['upload']['status'],'uploading');self.assertEqual(self.creates,1)
    def test_known_provider_rejection_removes_reservation_without_recreating_it(self):
        self.reject=True
        with self.assertRaises(APIError):self.call()
        self.assertEqual(self.creates,0)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM bunny_stream_uploads').fetchone()[0],0)
