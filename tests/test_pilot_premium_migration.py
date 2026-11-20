import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.database import BACKEND, initialize
from backend.platform_api import connect, seed_catalog, register, academic
from backend.local_pilot import migrate_pilot_premium
from types import SimpleNamespace


class PilotPremiumMigrationTests(unittest.TestCase):
    def test_existing_pilot_keeps_original_values_without_main_game_tables(self):
        root=BACKEND.parent/'work';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            folder=Path(folder);old=folder/'legacy';(old/'migrations').mkdir(parents=True)
            for source in (BACKEND/'migrations').glob('*.sql'):
                if source.name < '0030' and source.name not in ('0021_group_games.sql','0023_game_claims.sql','0024_vip_plus.sql','0025_exam_commerce.sql','0027_premium_admin.sql','0028_native_admin.sql'):
                    shutil.copy2(source,old/'migrations'/source.name)
            dbpath=folder/'pilot.sqlite3'
            with patch('backend.database.BACKEND',old):initialize(dbpath)
            seed_catalog(dbpath)
            with connect(dbpath,True) as db:
                register(SimpleNamespace(server=SimpleNamespace(),headers={},api_headers={}),db,{'login':'qa-legacy-premium','password':'test-only-password-128','name':'Học sinh thử','birthYear':academic()[0]-10})
            with connect(dbpath) as db:
                names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                before={name:{'columns':[r[1] for r in db.execute('PRAGMA table_info("'+name+'")')],'rows':[tuple(r) for r in db.execute('SELECT * FROM "'+name+'"')]} for name in names}
            migrate_pilot_premium(dbpath)
            with connect(dbpath) as db:
                for name,oldtable in before.items():
                    columns=','.join('"'+c+'"' for c in oldtable['columns'])
                    rows=[tuple(r) for r in db.execute('SELECT '+columns+' FROM "'+name+'"')]
                    if name in ('schema_migrations','system_settings'):self.assertTrue(set(oldtable['rows']).issubset(rows))
                    else:self.assertEqual(rows,oldtable['rows'],name)
                for name in ('group_game_rooms','group_game_requests','group_game_rewards','game_claims','game_claim_requests'):
                    self.assertIsNone(db.execute('SELECT 1 FROM sqlite_master WHERE name=?',(name,)).fetchone())
                first={r[0]:r[1] for r in db.execute('SELECT name,applied_at FROM schema_migrations')}
                self.assertEqual(db.execute('SELECT count(*) FROM video_series').fetchone()[0],3)
            migrate_pilot_premium(dbpath)
            with connect(dbpath) as db:
                self.assertEqual({r[0]:r[1] for r in db.execute('SELECT name,applied_at FROM schema_migrations')},first)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
