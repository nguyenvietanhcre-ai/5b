from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from backend.database import BACKEND, execute_sql, initialize
from backend.platform_api import initialize_catalog


class MascotBadgeMigrationTest(unittest.TestCase):
    def test_new_account_and_rank_boundaries(self):
        from types import SimpleNamespace
        from backend.arena import Arena
        from backend.platform_api import connect, academic
        from test_platform_api import Client
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'rank.sqlite3'
            initialize(target)
            initialize_catalog(target)
            client=Client(SimpleNamespace(database_path=target,review_upgrades=False,arena=Arena()))
            result=client.call('auth/register',{'login':'rank-boundaries','password':'Rank-QA-Only-2026','name':'Mầm thử','birthYear':academic()[0]-10})
            self.assertEqual(result['state']['points'],0)
            for xp,level in [(0,1),(19,1),(20,2),(80,5),(99,5),(100,6),(199,10),(200,11),(280,15),(999,15)]:
                with connect(target,True) as db:
                    db.execute('UPDATE student_companions SET xp=?',(xp,))
                row=client.call('leaderboard?kind=battle&period=all')['rows'][0]
                self.assertEqual((row['xp'],row['level']),(xp,level))

    def test_old_xp_removed_once_and_references_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'badge.sqlite3'
            db=sqlite3.connect(target)
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('CREATE TABLE schema_migrations(name TEXT PRIMARY KEY,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            for migration in sorted((BACKEND/'migrations').glob('*.sql')):
                if migration.name.startswith('0020_'):
                    break
                execute_sql(db,migration.read_text(encoding='utf-8'))
                db.execute('INSERT INTO schema_migrations(name) VALUES (?)',(migration.name,))
            db.execute("INSERT INTO mascots(id,name) VALUES(1,'Test')")
            db.execute('INSERT INTO mascot_levels VALUES(1,1000)')
            db.execute("INSERT INTO mascot_variants VALUES(1,1,'test.webp',NULL)")
            db.execute("INSERT INTO bots(id,kind,display_name,skill_level,xp) VALUES(1,'training','Bot',1,1120)")
            db.commit()
            db.close()
            initialize(target)
            initialize_catalog(target)
            initialize(target)
            with closing(sqlite3.connect(target)) as db:
                self.assertEqual(db.execute('SELECT xp FROM bots').fetchone()[0],120)
                self.assertEqual(db.execute('SELECT count(*),min(min_xp),max(min_xp) FROM mascot_levels').fetchone(),(15,0,280))
                self.assertEqual(db.execute('SELECT level,image_ref FROM mascot_variants').fetchone(),(1,'test.webp'))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
                self.assertIn('DEFAULT 0',db.execute("SELECT sql FROM sqlite_master WHERE name='student_companions'").fetchone()[0])
