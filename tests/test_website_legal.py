import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, seed_catalog
from backend.arena import Arena
from test_platform_api import Client

class WebsiteLegalTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)/'legal.sqlite3'
        initialize(self.path);seed_catalog(self.path)
        self.server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena(),website_readiness_enabled=True)
    def tearDown(self):self.folder.cleanup()
    def body(self):
        return {'login':'legal-'+secrets.token_hex(6),'password':secrets.token_urlsafe(16),'name':'Mầm Xanh','birthYear':academic()[0]-10,
                'legalConsent':{'accepted':True,'version':'2026-11-17-draft1','name':'Người đại diện thử','contact':'parent@example.test','role':'parent'}}
    def test_missing_or_stale_consent_creates_no_account(self):
        for value in (None,{}, {'accepted':True,'version':'old'}):
            body=self.body();body['legalConsent']=value
            with self.assertRaises(APIError):Client(self.server).call('auth/register',body)
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0],0)
    def test_registration_keeps_versioned_notice_and_self_declared_representative(self):
        client=Client(self.server);body=self.body();result=client.call('auth/register',body)
        self.assertTrue(result['authenticated'])
        with connect(self.path) as db:
            row=db.execute('SELECT * FROM website_account_consents').fetchone()
            self.assertEqual(row['representative_contact'],'parent@example.test')
            snap=db.execute('SELECT * FROM website_policy_snapshots').fetchone()
            self.assertIn('dieu-khoan',snap['content_json']);self.assertEqual(len(snap['content_sha256']),64)
            self.assertNotIn(body['password'],snap['content_json'])
    def test_changed_document_under_same_version_rolls_back_new_registration(self):
        Client(self.server).call('auth/register',self.body())
        with connect(self.path,True) as db:db.execute("UPDATE website_policy_snapshots SET content_sha256='changed'")
        with self.assertRaises(APIError) as caught:Client(self.server).call('auth/register',self.body())
        self.assertEqual(caught.exception.status,409)
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0],1)
