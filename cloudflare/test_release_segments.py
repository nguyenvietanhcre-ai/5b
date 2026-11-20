"""Operator segments stay sealed, bounded and closed until final completion."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_storage import FakeStorage
from sqlite_storage import StorageDatabase
from backend import curriculum_samples as samples
from backend.platform_api import APIError
import release_bridge as bridge

class ReleaseSegmentTests(unittest.TestCase):
    def setUp(self):
        self.storage=FakeStorage();self.database=StorageDatabase(self.storage);self.database.initialize()
        self.learning=SimpleNamespace(path=self.database)
        self.package={'questions':[{'id':str(i),'access':'free' if i<500 else 'paid'} for i in range(650)]}
        self.identity={'packageHash':'a'*64,'batchId':samples.BATCH}
        self.stack=[]
        for obj,name,value in [(samples,'loaded_package',lambda:self.package),(samples,'validate_package',lambda p:'a'*64),(bridge,'Path',lambda *_:SimpleNamespace(with_name=lambda _:SimpleNamespace(exists=lambda:False)))]:
            p=patch.object(obj,name,value);p.start();self.stack.append(p)
    def tearDown(self):
        for p in self.stack:p.stop()
        self.storage.db.close()
    def call(self,store,offset):return bridge.install_release(self.database,self.learning,{**self.identity,'segment':{'store':store,'offset':offset}})
    def test_source_selection_is_bounded_and_main_excludes_paid(self):
        def install(db,package,*,pilot,question_keys):return {'inserted':len(question_keys),'pilot':pilot,'keys':sorted(question_keys)}
        with patch.object(samples,'install',install):
            main=self.call('main',250);self.assertEqual(main['selected'],250);self.assertFalse(main['result']['pilot']);self.assertTrue(all(int(k)<500 for k in main['result']['keys']))
            native=self.call('native',500);self.assertEqual(native['selected'],150);self.assertTrue(native['result']['pilot'])
    def test_invalid_segment_and_identity_cannot_call_installer(self):
        with patch.object(samples,'install') as install:
            for store,offset in [('main',-1),('native',1),('main',500),('native',True),('unknown',0)]:
                with self.assertRaises(APIError):self.call(store,offset)
            with self.assertRaises(APIError):bridge.install_release(self.database,self.learning,{**self.identity,'packageHash':'b'*64,'segment':{'store':'main','offset':0}})
            install.assert_not_called()
    def test_failed_segment_rolls_back_its_writes(self):
        def fail(db,*args,**kwargs):
            db.execute("INSERT INTO release_segment_probe VALUES('must roll back')");raise APIError('Synthetic failure',409)
        self.storage.exec('CREATE TABLE release_segment_probe(value TEXT)')
        with patch.object(samples,'install',fail):
            with self.assertRaises(APIError):self.call('main',0)
        self.assertEqual(self.storage.db.execute('SELECT count(*) FROM release_segment_probe').fetchone()[0],0)
    def test_lessons_cannot_complete_before_both_stores_are_full(self):
        with self.assertRaises(APIError):self.call('lessons',0)
        self.assertIsNone(self.storage.db.execute("SELECT 1 FROM sqlite_master WHERE name='release_source_installations'").fetchone())
