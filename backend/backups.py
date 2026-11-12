"""Consistent SQLite backups and verified restore to a new file."""
import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

NAME = re.compile(r'5bmath-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}\.sqlite3\Z')
SIDECARS = ('-wal', '-shm', '-journal')


def _sidecars(path):
    return [Path(str(path) + suffix) for suffix in SIDECARS]


def _reserve(path):
    if path.exists() or path.is_symlink() or any(p.exists() or p.is_symlink() for p in _sidecars(path)):
        raise ValueError('Output or SQLite sidecar already exists; choose a new file')
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)


def _manifest(path, details, required=False):
    manifest = path.with_suffix('.json')
    if not manifest.exists() and not manifest.is_symlink():
        if required:
            raise ValueError('Backup manifest is required')
        return
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('Backup manifest must be a regular file')
    try:
        expected = json.loads(manifest.read_text(encoding='utf-8'))
        created = datetime.fromisoformat(expected['created_at'].replace('Z', '+00:00'))
        if (expected['file'] != path.name or expected['format'] != 1 or created.tzinfo is None or
                expected['sha256'] != details['sha256'] or expected['tables'] != details['tables']):
            raise ValueError('Backup does not match its manifest')
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError('Backup manifest is invalid') from error


def verify(path, require_manifest=False):
    """Verify a completed standalone snapshot, not the mutable live database."""
    path = Path(path).resolve()
    if any(p.exists() or p.is_symlink() for p in _sidecars(path)):
        raise ValueError('Verify a standalone backup, not a database with SQLite sidecars')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'delete':
            raise ValueError('Snapshot must use DELETE journal mode; create it with backup first')
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Database integrity check failed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Database foreign key check failed')
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        counts = {name: db.execute('SELECT count(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for name in tables}
        before = path.stat()
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('Snapshot changed during verification')
        details = {'sha256': digest, 'tables': counts}
        _manifest(path, details, required=require_manifest)
    return details


def backup(source, directory):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if not source.is_file():
        raise ValueError('Source database does not exist')
    directory.mkdir(parents=True, exist_ok=True)
    name = '5bmath-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(4) + '.sqlite3'
    target = directory / name
    manifest = target.with_suffix('.json')
    if manifest.exists() or manifest.is_symlink():
        raise ValueError('Backup manifest already exists; choose a new file')
    _reserve(target)
    manifest_created = False
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)) as origin:
            with closing(sqlite3.connect(target)) as destination:
                origin.backup(destination, pages=128, sleep=0.05)
                destination.execute('PRAGMA journal_mode=DELETE')
        details = verify(target)
        details.update(file=name, created_at=datetime.now(timezone.utc).isoformat(), format=1)
        descriptor = os.open(manifest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        manifest_created = True
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(details, ensure_ascii=False, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        for sidecar in _sidecars(target):
            sidecar.unlink(missing_ok=True)
        if manifest_created:
            manifest.unlink(missing_ok=True)
        raise
    return target


def restore(source, target):
    source, target = Path(source).resolve(), Path(target).absolute()
    details = verify(source, require_manifest=True)
    if target.exists() or target.is_symlink():
        raise ValueError('Restore target already exists; restore to a new file')
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.with_suffix('.json').exists() or target.with_suffix('.json').is_symlink():
        raise ValueError('Restore target manifest already exists; choose a new file')
    _reserve(target)
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as origin:
            with closing(sqlite3.connect(target)) as destination:
                origin.backup(destination)
                destination.execute('PRAGMA journal_mode=DELETE')
        restored = verify(target)
        if restored['tables'] != details['tables']:
            raise ValueError('Restore row counts differ from backup')
    except BaseException:
        target.unlink(missing_ok=True)
        for sidecar in _sidecars(target):
            sidecar.unlink(missing_ok=True)
        raise
    return target


def prune(directory, keep):
    directory = Path(directory).resolve()
    if type(keep) is not int or keep < 1:
        raise ValueError('Keep at least one verified backup')
    entries = []
    for path in directory.glob('5bmath-*.sqlite3'):
        if path.is_symlink() or path.parent.resolve() != directory or not NAME.fullmatch(path.name):
            continue
        manifest = path.with_suffix('.json')
        if not manifest.is_file() or manifest.is_symlink():
            continue
        try:
            verify(path, require_manifest=True)
            details = json.loads(manifest.read_text(encoding='utf-8'))
            created = datetime.fromisoformat(details['created_at'].replace('Z', '+00:00'))
        except (ValueError, OSError, sqlite3.Error):
            continue
        entries.append((created, path.name, path))
    removed = []
    for _, _, path in sorted(entries, reverse=True)[keep:]:
        path.unlink()
        path.with_suffix('.json').unlink()
        removed.append(path.name)
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('backup')
    create.add_argument('--source', type=Path, required=True)
    create.add_argument('--directory', type=Path, required=True)
    create.add_argument('--keep', type=int, default=14)
    create.add_argument('--prune', action='store_true')
    recover = commands.add_parser('restore')
    recover.add_argument('--source', type=Path, required=True)
    recover.add_argument('--target', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'backup':
        result = {'backup': str(backup(args.source, args.directory))}
        if args.prune:
            result['pruned'] = prune(args.directory, args.keep)
    elif args.command == 'restore':
        result = {'restored': str(restore(args.source, args.target))}
    else:
        result = verify(args.source)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
