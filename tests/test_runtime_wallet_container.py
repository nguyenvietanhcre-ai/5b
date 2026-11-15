import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend import platform_api as api
from backend.typed_wallet_study import create_server,close_server
class RuntimeWalletContainerTests(unittest.TestCase):
    def test_non_loopback_cannot_be_enabled_without_explicit_container_flag(self):
        from backend.qa_study import create_server as factory
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'explicit isolated QA'):factory('never.sqlite3','missing','missing','missing',bind_host='0.0.0.0')
        self.assertFalse(Path('never.sqlite3').exists())
    def test_strict_container_fixture_contains_only_ten_question_identities(self):
        if not os.environ.get('FIVEBMATH_QA_TYPED_INPUT_DIR'):self.skipTest('Private wallet fixture; run the local release gate')
        folder=Path(os.environ['FIVEBMATH_QA_TYPED_INPUT_DIR']);Path('work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='work') as tmp:
            server=create_server(Path(tmp)/'strict.sqlite3',*(folder/f for f in ('questions-typed.json','sample-sets-typed.json','sources.json')),seed_learning=False)
            try:
                with api.connect(server.database_path) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0],10)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM question_versions').fetchone()[0],20)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0],0)
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            finally:close_server(server)
