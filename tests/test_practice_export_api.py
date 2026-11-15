from http.server import HTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile,secrets,unittest
from backend import platform_api as api
from backend.database import initialize
from backend.arena import Arena
from backend.practice_export_api import available
from test_arena_penalties import Client

CREDENTIAL=api.password_hash('export-native-qa-only')
class PracticeExportGateTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'work';root.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=root);self.path=Path(self.tmp.name)/'fresh.sqlite3'
        initialize(self.path);api.initialize_catalog(self.path)
        self.server=object.__new__(HTTPServer);self.server.database_path=self.path;self.server.review_upgrades=False;self.server.arena=Arena()
        self.server.native_python_backend=True;self.server.practice_export_enabled=True;self.server.practice_export_ports={8765}
        self.client=Client(self.server)
        with api.connect(self.path,True) as db:
            s=api.register(self.client,db,{'login':'pdf-gate-'+secrets.token_hex(8),'name':'Mầm Xanh','birthYear':api.academic()[0]-9,'password':'export-native-qa-only'},CREDENTIAL)
        self.client.headers['Cookie']=self.client.api_headers.pop('Set-Cookie').split(';')[0];self.client.csrf=s['csrf_token']
    def tearDown(self):self.tmp.cleanup()
    def test_flag_host_and_public_origin_fail_closed(self):
        self.assertTrue(available(self.client))
        for host in ('192.168.1.13:8765','5bmath.vn:8765','localhost:19031','localhost.evil:8765'):
            self.client.headers['Host']=host;self.client.headers['X-Forwarded-Host']='localhost:8765'
            self.assertFalse(available(self.client))
        self.client.headers['Host']='localhost:8765'
        with patch.object(api,'public_origin',return_value='https://5bmath.vn'):self.assertFalse(available(self.client))
        self.server.practice_export_enabled=False
        with self.assertRaises(api.APIError) as caught:self.client.call('practice-export',{'provider':'main','attemptId':1,'practice_export_enabled':True})
        self.assertEqual(caught.exception.status,503)
    def test_worker_cannot_enable_native_dependency_import(self):
        worker=Client(SimpleNamespace(database_path=self.path,native_python_backend=False,practice_export_enabled=True))
        with self.assertRaises(api.APIError) as caught:worker.call('practice-export',{'provider':'main','attemptId':1})
        self.assertEqual(caught.exception.status,503)
        cloud=SimpleNamespace(native_python_backend=True,practice_export_enabled=True,practice_export_ports={8765})
        self.assertFalse(available(SimpleNamespace(server=cloud,headers={'Host':'localhost:8765'})))
    def test_auth_csrf_and_renderer_only_after_gates(self):
        with patch('backend.practice_export.export_pdf',return_value={'mime':'application/pdf'}) as export:
            unauth=Client(self.server)
            with self.assertRaises(api.APIError) as caught:unauth.call('practice-export',{'provider':'main','attemptId':1})
            self.assertEqual(caught.exception.status,401);export.assert_not_called()
            original=self.client.csrf;self.client.csrf='bad-csrf'
            with self.assertRaises(api.APIError) as caught:self.client.call('practice-export',{'provider':'main','attemptId':1})
            self.assertEqual(caught.exception.status,403);export.assert_not_called()
            self.client.csrf=original
            self.assertEqual(self.client.call('practice-export',{'provider':'main','attemptId':1})['mime'],'application/pdf')
            export.assert_called_once()
    def test_missing_pilot_no_fallback_or_request_schema_write(self):
        with self.assertRaises(api.APIError) as caught:self.client.call('practice-export',{'provider':'pilot','attemptId':1})
        self.assertEqual(caught.exception.status,503)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM practice_export_codes').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM practice_export_rights').fetchone()[0],0)

if __name__=='__main__':unittest.main()
