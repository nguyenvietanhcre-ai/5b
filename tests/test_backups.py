import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from datetime import datetime, timezone
from unittest.mock import patch
from backend.backups import backup, prune, restore, verify


class BackupTests(unittest.TestCase):
    def setUp(self):
        directory = Path(__file__).resolve().parents[1] / 'work' / 'backup-tests'
        directory.mkdir(parents=True, exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source = self.root / 'live.sqlite3'
        with closing(sqlite3.connect(self.source)) as db, db:
            db.executescript('PRAGMA journal_mode=WAL; CREATE TABLE items(id INTEGER PRIMARY KEY, value BLOB);')
            db.execute('INSERT INTO items VALUES(1,?)', (b'original\x00bytes',))

    def test_backup_and_restore_preserve_committed_values_while_writer_is_open(self):
        writer = sqlite3.connect(self.source)
        self.addCleanup(writer.close)
        writer.execute("UPDATE items SET value='uncommitted' WHERE id=1")
        copied = backup(self.source, self.root / 'snapshots')
        recovered = restore(copied, self.root / 'recovered.sqlite3')
        with closing(sqlite3.connect(recovered)) as db:
            self.assertEqual(db.execute('SELECT value FROM items').fetchone()[0], b'original\x00bytes')
        self.assertEqual(verify(copied)['tables'], {'items': 1})
        writer.rollback()

    def test_snapshot_includes_committed_wal_and_is_standalone_without_source_sidecars(self):
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute('PRAGMA wal_autocheckpoint=0')
            writer.execute('INSERT INTO items VALUES(2,?)', (b'committed in WAL',))
            writer.commit()
            self.assertGreater(Path(str(self.source)+'-wal').stat().st_size, 0)
            writer.execute("UPDATE items SET value='not committed' WHERE id=1")
            with self.assertRaises(ValueError):
                verify(self.source)
            copied = backup(self.source, self.root / 'snapshots')
            self.assertFalse(any(Path(str(copied)+suffix).exists() for suffix in ('-wal','-shm','-journal')))
            self.assertEqual(verify(copied)['tables'], {'items':2})
            writer.rollback()
        standalone = self.root / 'independent'
        standalone.mkdir()
        for path in (copied, copied.with_suffix('.json')):
            shutil.copy2(path, standalone / path.name)
        recovered = restore(standalone / copied.name, self.root / 'rehearsal.sqlite3')
        with closing(sqlite3.connect(recovered)) as db:
            self.assertEqual(db.execute('SELECT id,value FROM items ORDER BY id').fetchall(),
                             [(1,b'original\x00bytes'),(2,b'committed in WAL')])

    def test_restore_never_overwrites_and_rejects_changed_backup(self):
        copied = backup(self.source, self.root / 'snapshots')
        with self.assertRaises(ValueError):
            restore(copied, self.source)
        with closing(sqlite3.connect(copied)) as db, db:
            db.execute('INSERT INTO items VALUES(2,?)', (b'changed',))
        with self.assertRaises(ValueError):
            restore(copied, self.root / 'rejected.sqlite3')
        self.assertFalse((self.root / 'rejected.sqlite3').exists())

    def test_retention_only_removes_verified_owned_backup_files(self):
        directory = self.root / 'snapshots'
        for _ in range(3):
            backup(self.source, directory)
        unrelated = directory / 'keep-me.sqlite3'
        unrelated.write_bytes(b'not a managed backup')
        self.assertEqual(len(prune(directory, 1)), 2)
        self.assertTrue(unrelated.exists())
        managed = [path for path in directory.glob('5bmath-*.sqlite3')]
        self.assertEqual(len(managed), 1)
        self.assertEqual(json.loads(managed[0].with_suffix('.json').read_text())['sha256'], verify(managed[0])['sha256'])

    def test_restore_requires_matching_complete_manifest_and_new_sidecar_free_target(self):
        copied = backup(self.source, self.root / 'snapshots')
        manifest = copied.with_suffix('.json')
        original = manifest.read_text(encoding='utf-8')
        for invalid in ('', '{', json.dumps({**json.loads(original),'file':'another.sqlite3'}),
                        json.dumps({**json.loads(original),'tables':{'items':99}})):
            manifest.write_text(invalid, encoding='utf-8')
            with self.assertRaises(ValueError):
                restore(copied, self.root / 'rejected.sqlite3')
            self.assertFalse((self.root / 'rejected.sqlite3').exists())
        manifest.unlink()
        with self.assertRaises(ValueError):
            restore(copied, self.root / 'missing-manifest.sqlite3')
        manifest.write_text(original, encoding='utf-8')
        collision = self.root / 'sidecar.sqlite3'
        sidecar = Path(str(collision)+'-wal')
        sidecar.write_bytes(b'existing sidecar must survive')
        with self.assertRaises(ValueError):
            restore(copied, collision)
        self.assertEqual(sidecar.read_bytes(), b'existing sidecar must survive')
        self.assertFalse(collision.exists())

    def test_retention_skips_malformed_corrupt_and_mismatched_candidates(self):
        directory = self.root / 'snapshots'
        valid = [backup(self.source, directory) for _ in range(3)]
        protected = []
        for index, mode in enumerate(('malformed','corrupt','counts','missing')):
            candidate = directory / f'5bmath-20000101T000000Z-{index:08x}.sqlite3'
            shutil.copy2(valid[0], candidate)
            details = json.loads(valid[0].with_suffix('.json').read_text(encoding='utf-8'))
            details['file'] = candidate.name
            if mode == 'counts':
                details['tables'] = {'items':999}
            if mode != 'missing':
                candidate.with_suffix('.json').write_text('{' if mode == 'malformed' else json.dumps(details), encoding='utf-8')
            if mode == 'corrupt':
                candidate.write_bytes(b'not sqlite')
            protected.append(candidate)
        self.assertEqual(len(prune(directory, 1)), 2)
        self.assertTrue(all(candidate.exists() for candidate in protected))
        for invalid in (0, -1, True):
            with self.assertRaises(ValueError):
                prune(directory, invalid)

    def test_backup_name_collision_does_not_modify_existing_output(self):
        directory = self.root / 'snapshots'
        with patch('backend.backups.datetime', wraps=datetime) as clock, patch('backend.backups.secrets.token_hex', return_value='1234abcd'):
            clock.now.return_value = datetime(2026,11,12,tzinfo=timezone.utc)
            copied = backup(self.source, directory)
            original = copied.read_bytes(), copied.with_suffix('.json').read_bytes()
            with self.assertRaises(ValueError):
                backup(self.source, directory)
            self.assertEqual(original, (copied.read_bytes(), copied.with_suffix('.json').read_bytes()))
