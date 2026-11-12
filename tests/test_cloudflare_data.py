"""Private transfer protocol tests use synthetic data and never call Cloudflare."""
import copy
import importlib.util
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cloudflare_data', ROOT / 'scripts/cloudflare-data.py')
transfer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transfer)


class CloudflareDataTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='cloudflare-data-', dir=ROOT / 'work')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'source.sqlite3'
        self.marker = 'NEVER-LOG-'+secrets.token_hex(16)
        self.blob = bytes(range(256))*1024  # Larger than DO's 100KB SQL limit.
        with closing(sqlite3.connect(self.source)) as db, db:
            db.executescript('''PRAGMA foreign_keys=ON;
                CREATE TABLE z_parent(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);
                CREATE TABLE a_child(id INTEGER PRIMARY KEY,parent_id INTEGER REFERENCES z_parent(id),
                    body BLOB, note TEXT, exact_integer INTEGER, ratio REAL);
                CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,note TEXT NOT NULL);
                CREATE TRIGGER parent_event AFTER INSERT ON z_parent BEGIN
                    INSERT INTO events(note) VALUES(NEW.name);
                END;''')
            db.execute('INSERT INTO z_parent(id,name) VALUES (1,?)',(self.marker,))
            db.execute('INSERT INTO z_parent(id,name) VALUES (40,?)',('later deleted',))
            db.execute('DELETE FROM z_parent WHERE id=40')
            db.execute('INSERT INTO a_child VALUES (1,1,?,?,?,?)',
                       (self.blob,"Tiếng Việt\x00line\n'quoted'",2**63-1,1.2345678901234567e20))
            db.execute('INSERT INTO a_child VALUES (2,1,?,?,?,?)',(b'',None,-2**63,float('inf')))

    def prepared(self, name='transfer.json'):
        output = self.root / name
        payload,snapshot = transfer.prepare(self.source, output)
        return payload,snapshot,output

    def test_parameterized_roundtrip_preserves_every_value_trigger_history_and_sequences(self):
        payload,snapshot,output = self.prepared()
        self.assertEqual(payload['source']['kind'],'sqlite')
        self.assertEqual(len(payload['source']['sha256']),64)
        self.assertIn('sqlite_sequence',payload['source']['tables'])
        self.assertTrue(snapshot.with_suffix('.json').exists())
        self.assertEqual(transfer.load_payload(output),payload)
        row_operations = [s for s in payload['statements'] if isinstance(s,dict)]
        self.assertTrue(any(any(isinstance(p,dict) and 'base64' in p for p in s['params']) for s in row_operations))
        self.assertTrue(all(len((s if isinstance(s,str) else s['sql']).encode('utf-8')) < 100_000 for s in payload['statements']))
        trigger_index = next(i for i,s in enumerate(payload['statements']) if isinstance(s,str) and s.startswith('CREATE TRIGGER'))
        self.assertTrue(all(isinstance(s,str) for s in payload['statements'][trigger_index:]))
        restored = transfer.restore_payload(payload,self.root/'restored.sqlite3')
        self.assertEqual(transfer.fingerprints(snapshot),transfer.fingerprints(restored))
        with closing(sqlite3.connect(restored)) as db, db:
            row = db.execute('SELECT body,note,exact_integer,ratio FROM a_child WHERE id=1').fetchone()
            self.assertEqual(row,(self.blob,"Tiếng Việt\x00line\n'quoted'",2**63-1,1.2345678901234567e20))
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],2)
            self.assertEqual(db.execute('INSERT INTO z_parent(name) VALUES (?)',('after restore',)).lastrowid,41)
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],3)

    def test_remote_export_provenance_restores_same_format_and_all_row_values(self):
        payload,snapshot,_ = self.prepared()
        exported = copy.deepcopy(payload)
        exported['source'].update(kind='cloudflare',sha256=None,bookmark='synthetic-bookmark')
        exported['transferSha256'] = transfer.checksum(exported)
        restored = transfer.restore_payload(exported,self.root/'remote-restored.sqlite3')
        self.assertEqual(transfer.fingerprints(snapshot),transfer.fingerprints(restored))

    def test_complete_project_schema_and_demo_financial_history_roundtrip_without_trigger_replay(self):
        from backend.demo_seed import seed
        from backend.platform_api import seed_catalog
        source = self.root/'project-fixture.sqlite3'
        seed(source)
        seed_catalog(source)
        payload,snapshot = transfer.prepare(source,self.root/'project-transfer.json')
        restored = transfer.restore_payload(payload,self.root/'project-restored.sqlite3')
        self.assertEqual(transfer.fingerprints(snapshot),transfer.fingerprints(restored))
        with closing(sqlite3.connect(snapshot)) as before, closing(sqlite3.connect(restored)) as after:
            for table in ('vip_purchases','account_referrals','notifications','accounts'):
                self.assertEqual(before.execute('SELECT count(*) FROM '+table).fetchone()[0],
                                 after.execute('SELECT count(*) FROM '+table).fetchone()[0])
            self.assertGreater(before.execute('SELECT count(*) FROM vip_purchases').fetchone()[0],0)

    def test_checksum_counts_and_foreign_keys_reject_corruption_without_leaving_output(self):
        payload,_,_ = self.prepared()
        corrupted = copy.deepcopy(payload)
        corrupted['source']['tables']['a_child'] += 1
        with self.assertRaises(transfer.TransferError):
            transfer.validate(corrupted)
        corrupted['transferSha256'] = transfer.checksum(corrupted)
        target = self.root/'bad-counts.sqlite3'
        with self.assertRaises(transfer.TransferError):
            transfer.restore_payload(corrupted,target)
        self.assertFalse(target.exists())
        orphan = copy.deepcopy(payload)
        for statement in orphan['statements']:
            if isinstance(statement,dict) and statement['sql'].startswith('INSERT INTO "a_child"'):
                statement['params'][1] = {'integer':'999'}
        orphan['transferSha256'] = transfer.checksum(orphan)
        with self.assertRaises(transfer.TransferError):
            transfer.restore_payload(orphan,self.root/'orphan.sqlite3')
        self.assertFalse((self.root/'orphan.sqlite3').exists())

    def test_output_boundary_and_existing_files_are_preserved(self):
        payload,_,output = self.prepared()
        original = output.read_bytes()
        with self.assertRaises(transfer.TransferError):
            transfer.save_payload(payload,output)
        self.assertEqual(output.read_bytes(),original)
        with self.assertRaises(transfer.TransferError):
            transfer.restore_payload(payload,self.source)
        with self.assertRaises(transfer.TransferError):
            transfer.output_path(ROOT/'forbidden-data.json')
        self.assertFalse((ROOT/'forbidden-data.json').exists())
        target = self.root/'sidecar.sqlite3'
        sidecar = Path(str(target)+'-wal')
        sidecar.write_bytes(b'preserve')
        with self.assertRaises(transfer.TransferError):
            transfer.restore_payload(payload,target)
        self.assertEqual(sidecar.read_bytes(),b'preserve')

    def test_control_sql_cannot_attach_database_outside_the_restore_target(self):
        payload,_,_ = self.prepared()
        unsafe = copy.deepcopy(payload)
        unsafe['statements'].append("ATTACH DATABASE 'outside.sqlite3' AS outside;")
        unsafe['transferSha256'] = transfer.checksum(unsafe)
        with self.assertRaises(transfer.TransferError):
            transfer.validate(unsafe)
        unsafe['statements'][-1] = "SELECT load_extension('private-extension');"
        unsafe['transferSha256'] = transfer.checksum(unsafe)
        with self.assertRaises(sqlite3.DatabaseError):
            transfer.restore_payload(unsafe,self.root/'extension.sqlite3')
        self.assertFalse((self.root/'extension.sqlite3').exists())

    def test_limits_typed_values_and_trigger_order_fail_before_transfer(self):
        payload,_,_ = self.prepared()
        for value in ({'integer':str(2**63)},{'integer':'1.5'},{'real':'nan'},{'base64':'%%%'},3):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises((transfer.TransferError,ValueError)):
                    transfer.decode_param(value)
        with patch.object(transfer,'MAX_BLOB',10):
            with self.assertRaises(transfer.TransferError):
                transfer.validate(payload)
        with patch.object(transfer,'MAX_BYTES',100):
            with self.assertRaises(transfer.TransferError):
                transfer.validate(payload)
        wrong_order = copy.deepcopy(payload)
        trigger = next(s for s in wrong_order['statements'] if isinstance(s,str) and s.startswith('CREATE TRIGGER'))
        wrong_order['statements'].remove(trigger)
        wrong_order['statements'].insert(0,trigger)
        wrong_order['transferSha256'] = transfer.checksum(wrong_order)
        with self.assertRaises(transfer.TransferError):
            transfer.validate(wrong_order)

    def test_operator_reuses_existing_deployment_json_without_copying_secret(self):
        secret = secrets.token_urlsafe(40)
        secret_path = self.root/'deployment-secrets.json'
        secret_path.write_text(json.dumps({'OPERATOR_TOKEN':secret,'UNRELATED':'keep'}),encoding='utf-8')
        before = set(self.root.iterdir())
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'{"verified":true}'
        class Opener:
            def open(self, request, timeout):
                if request.get_header('Authorization') != 'Bearer '+secret:
                    raise AssertionError('Existing operator configuration was not used')
                if request.get_header('User-agent') != '5BMath-Operator/1.0 (+https://5bmath.vn/)':
                    raise AssertionError('Operator client must identify its own application')
                return Response()
        with patch.dict(os.environ,{'MAM_TOAN_CLOUDFLARE_OPERATOR_URL':'https://example.invalid',
                                   'MAM_TOAN_CLOUDFLARE_OPERATOR_SECRET_FILE':str(secret_path)}), \
             patch.object(transfer,'build_opener',return_value=Opener()):
            self.assertEqual(transfer.remote_request('export'),{'verified':True})
        self.assertEqual(set(self.root.iterdir()),before)

    def test_cli_diagnostics_never_print_private_rows_or_operator_secret(self):
        _,_,output = self.prepared()
        result = subprocess.run([sys.executable,str(ROOT/'scripts/cloudflare-data.py'),'restore','--input',str(output),
                                 '--target',str(self.root/'cli-restored.sqlite3')],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0)
        self.assertNotIn(self.marker,result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['restored'],True)
        secret = secrets.token_urlsafe(32)
        token_path = self.root/'operator-secret'
        token_path.write_text(secret,encoding='utf-8')
        with patch.dict(os.environ,{'MAM_TOAN_CLOUDFLARE_OPERATOR_URL':'https://example.invalid',
                                   'MAM_TOAN_CLOUDFLARE_OPERATOR_SECRET_FILE':str(token_path)}),\
             patch.object(transfer,'build_opener',side_effect=RuntimeError(secret)):
            from contextlib import redirect_stdout
            from io import StringIO
            captured = StringIO()
            with redirect_stdout(captured):
                code = transfer.main(['import','--input',str(output)])
        self.assertEqual(code,1)
        self.assertNotIn(secret,captured.getvalue())
        self.assertNotIn(self.marker,captured.getvalue())


if __name__ == '__main__':
    unittest.main()
