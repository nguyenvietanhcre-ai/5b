"""Audit old cells without exporting tenant records or accepting silent updates."""
import json,sqlite3,unittest
from unittest.mock import patch
from test_storage import FakeStorage
from sqlite_storage import StorageDatabase
from backend.platform_api import APIError
import release_audit as audit

class TenantAuditTests(unittest.TestCase):
 def setUp(self):
  self.storage=FakeStorage();self.database=StorageDatabase(self.storage);self.release='a'*40
  self.storage.db.execute('CREATE TABLE preserved(id INTEGER PRIMARY KEY,label TEXT,n INTEGER,payload BLOB)')
  self.storage.db.execute('INSERT INTO preserved VALUES(?,?,?,?)',(1,'private\x00text',2**63-1,b'\x00\xff'))
  self.enterContext(patch.object(audit.transfer,'bookmark',return_value='synthetic-bookmark'))
 def tearDown(self):self.storage.db.close()
 def begin(self):return audit.begin(self.database,self.release)
 def test_return_value_contains_metadata_only_and_baseline_lives_in_tenant(self):
  result=self.begin();self.assertEqual(result['existingTables'],1);self.assertFalse(result['accountRowsDownloaded'])
  text=json.dumps(result);self.assertNotIn('private',text);self.assertNotIn('payload',text)
  baseline=self.storage.db.execute('SELECT baseline_json FROM release_audit_baselines').fetchone()[0]
  self.assertNotIn('private',baseline);self.assertNotIn('9223372036854775807',baseline)
  self.assertFalse(audit.is_open(self.database,self.release))
 def test_new_column_and_new_row_preserve_all_original_cell_values(self):
  self.begin();self.storage.db.execute('ALTER TABLE preserved ADD COLUMN added TEXT')
  self.storage.db.execute("INSERT INTO preserved(id,label) VALUES(2,'new')")
  result=audit.compare(self.database,self.release);self.assertEqual(result['status'],'passed');self.assertEqual(result['newRowsInExistingTables'],{'preserved':1})
  audit.finalize(self.database,self.release);self.assertTrue(audit.is_open(self.database,self.release))
 def test_changed_or_deleted_old_row_prevents_opening(self):
  self.begin();self.storage.db.execute("UPDATE preserved SET label='changed' WHERE id=1")
  self.assertEqual(audit.compare(self.database,self.release)['status'],'failed')
  with self.assertRaises(APIError):audit.finalize(self.database,self.release)
  self.assertFalse(audit.is_open(self.database,self.release))
 def test_retry_cannot_replace_the_original_baseline(self):
  self.begin();self.storage.db.execute('DELETE FROM preserved');self.assertEqual(self.begin()['status'],'already-recorded')
  self.assertEqual(audit.compare(self.database,self.release)['status'],'failed')
