"""Synchronous SQLite facade over a tenant Durable Object's SQL storage.

Transactions belong to run(), never to SQL BEGIN/SAVEPOINT statements. The
preflight stops before the first write and retains only request-local crypto
results, then replays the operation in transactionSync. No credentials survive
the request. Explicit business commit boundaries are committed before replay.
"""
import contextvars
import copy
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


class NeedsTransaction(BaseException):
    pass


class CommitBoundary(BaseException):
    pass


@dataclass
class RequestScope:
    crypto: dict = field(default_factory=dict)
    auth_limited: bool = False
    transaction: bool = False


REQUEST_SCOPE = contextvars.ContextVar('fivebmath_request_scope', default=None)


class Row:
    def __init__(self, names, values):
        self.names, self.values = tuple(names), tuple(values)

    def keys(self):
        return list(self.names)

    def __getitem__(self, key):
        return self.values[self.names.index(key)] if isinstance(key, str) else self.values[key]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)


class Cursor:
    def __init__(self, names=(), rows=(), lastrowid=None, rowcount=-1):
        self.rows = [Row(names, row) for row in rows]
        self.index, self.lastrowid, self.rowcount = 0, lastrowid, rowcount
        self.description = [(name, None, None, None, None, None, None) for name in names] or None

    def fetchone(self):
        if self.index == len(self.rows):
            return None
        row = self.rows[self.index]
        self.index += 1
        return row

    def fetchall(self):
        rows = self.rows[self.index:]
        self.index = len(self.rows)
        return rows

    def __iter__(self):
        while (row := self.fetchone()) is not None:
            yield row


def bind_parameters(statement, parameters):
    """Avoid JavaScript Number rounding for SQLite's signed 64-bit integers."""
    parameters = tuple(parameters)
    if not parameters:
        return statement, ()
    output, bound, index, position = [], [], 0, 0
    quote = None
    while position < len(statement):
        char = statement[position]
        if quote:
            output.append(char)
            if char == quote:
                if position + 1 < len(statement) and statement[position + 1] == quote:
                    output.append(char)
                    position += 1
                else:
                    quote = None
        elif char in "'\"`[":
            quote = ']' if char == '[' else char
            output.append(char)
        elif statement.startswith('--', position):
            stop = statement.find('\n', position)
            stop = len(statement) if stop < 0 else stop
            output.append(statement[position:stop])
            position = stop - 1
        elif statement.startswith('/*', position):
            stop = statement.find('*/', position + 2)
            stop = len(statement) if stop < 0 else stop + 2
            output.append(statement[position:stop])
            position = stop - 1
        elif char == '?':
            if index >= len(parameters):
                raise sqlite3.ProgrammingError('Incorrect number of bindings')
            value = parameters[index]
            if isinstance(value, int):
                if not -(2**63) <= value < 2**63:
                    raise OverflowError('Python int too large to convert to SQLite INTEGER')
                output.append('CAST(? AS INTEGER)')
                bound.append(str(int(value)))
            else:
                output.append('?')
                bound.append(memoryview(value) if isinstance(value, (bytes, bytearray)) else value)
            index += 1
        else:
            output.append(char)
        position += 1
    if index != len(parameters):
        raise sqlite3.ProgrammingError('Incorrect number of bindings')
    return ''.join(output), tuple(bound)


class Connection:
    def __init__(self, database):
        self.database = database

    def execute(self, statement, parameters=()):
        clean = re.sub(r'\A\s*(?:--[^\n]*\n\s*)*', '', statement).strip()
        command = clean.split(None, 1)[0].upper().rstrip(';') if clean else ''
        scope = REQUEST_SCOPE.get()
        if command in ('BEGIN', 'SAVEPOINT'):
            if not scope or not scope.transaction:
                raise NeedsTransaction()
            return Cursor()
        if command in ('COMMIT', 'END'):
            self.commit()
            return Cursor()
        if command in ('ROLLBACK', 'RELEASE'):
            raise sqlite3.OperationalError('Use connection.atomic(callback) for nested rollback')
        if command not in ('SELECT', 'WITH', 'EXPLAIN') and not (scope and scope.transaction):
            raise NeedsTransaction()
        if re.match(r'(?is)^PRAGMA\s+journal_mode\b', clean):
            return Cursor(['journal_mode'], [('wal',)])
        sql, values = bind_parameters(statement, parameters)
        try:
            cursor = self.database.storage.sql.exec(sql, *values)
            names = list(cursor.columnNames)
            rows = list(cursor.raw())
            identity = changes = None
            if command in ('INSERT', 'UPDATE', 'DELETE', 'REPLACE'):
                metadata = self.database.storage.sql.exec('SELECT last_insert_rowid() AS id,changes() AS n').one()
                identity, changes = metadata['id'], metadata['n']
            return Cursor(names, rows, identity, changes if changes is not None else -1)
        except Exception as error:
            message = str(error)
            kind = sqlite3.IntegrityError if 'constraint failed' in message.lower() else sqlite3.OperationalError
            raise kind(message) from error

    def executemany(self, statement, parameters):
        result = Cursor(rowcount=0)
        total = 0
        for row in parameters:
            result = self.execute(statement, row)
            total += max(0, result.rowcount)
        result.rowcount = total
        return result

    def executescript(self, script):
        from backend.database import execute_sql
        execute_sql(self, script)

    def atomic(self, callback):
        return self.database.transaction(callback).get('result')

    def commit(self):
        if REQUEST_SCOPE.get() and REQUEST_SCOPE.get().transaction:
            raise CommitBoundary()

    def rollback(self):
        raise sqlite3.OperationalError('Rollback is owned by the transaction callback')

    def close(self):
        pass


class StorageDatabase:
    def __init__(self, storage, arena=None):
        self.storage, self.arena = storage, arena
        self._persisted_rooms = {}

    @contextmanager
    def connect(self, write=False):
        if write and not (REQUEST_SCOPE.get() and REQUEST_SCOPE.get().transaction):
            raise NeedsTransaction()
        yield Connection(self)

    def transaction(self, callback, allow_commit_boundary=False):
        scope = REQUEST_SCOPE.get()
        own_scope = scope is None
        token = REQUEST_SCOPE.set(RequestScope()) if own_scope else None
        scope = REQUEST_SCOPE.get()
        prior = scope.transaction
        outcome = {}

        def invoke():
            scope.transaction = True
            try:
                outcome['result'] = callback()
            except CommitBoundary:
                if not allow_commit_boundary:
                    outcome['error'] = sqlite3.OperationalError('Unexpected commit boundary')
                    raise RuntimeError('Transaction callback aborted')
                outcome['boundary'] = True
            except BaseException as error:
                outcome['error'] = error
                raise RuntimeError('Transaction callback aborted')
            finally:
                scope.transaction = prior

        try:
            self.storage.transactionSync(invoke)
        except Exception:
            if 'error' in outcome:
                raise outcome['error']
            raise
        finally:
            scope.transaction = prior
            if own_scope:
                REQUEST_SCOPE.reset(token)
        return outcome

    def _snapshot(self):
        return copy.deepcopy((self.arena.rooms, self.arena.retired, self._persisted_rooms)) if self.arena else None

    def _restore(self, snapshot):
        if self.arena and snapshot is not None:
            self.arena.rooms, self.arena.retired, self._persisted_rooms = snapshot

    def persist_arena(self):
        if self.arena:
            import json
            current = {(bucket, key): json.dumps(room, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
                       for bucket in ('rooms', 'retired') for key, room in getattr(self.arena, bucket).items()}
            for key in self._persisted_rooms.keys() - current.keys():
                self.storage.sql.exec('DELETE FROM cloudflare_arena_rooms WHERE bucket=? AND room_key=?', *key)
            for key, payload in current.items():
                if self._persisted_rooms.get(key) != payload:
                    self.storage.sql.exec('INSERT INTO cloudflare_arena_rooms VALUES (?,?,?) '
                                          'ON CONFLICT(bucket,room_key) DO UPDATE SET payload=excluded.payload', *key, payload)
            self._persisted_rooms = current

    def restore_arena(self):
        if not self.arena or not list(self.storage.sql.exec(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cloudflare_arena_rooms'")):
            return
        import json
        self.arena.rooms, self.arena.retired = {}, {}
        self._persisted_rooms = {}
        for row in self.storage.sql.exec('SELECT bucket,room_key,payload FROM cloudflare_arena_rooms'):
            room = json.loads(row['payload'])
            for player in room.get('players', {}).values():
                # Arena indexes answer history by integer question position;
                # JSON object keys become strings during persistence.
                player['answers'] = {int(key): value for key, value in player.get('answers', {}).items()}
            getattr(self.arena, row['bucket'])[row['room_key']] = room
            self._persisted_rooms[(row['bucket'], row['room_key'])] = row['payload']

    def run(self, callback):
        token = REQUEST_SCOPE.set(RequestScope())
        original = self._snapshot()
        try:
            try:
                result = callback()
                if self._snapshot() != original:
                    self.transaction(self.persist_arena)
                return result
            except NeedsTransaction:
                # PBKDF preflight may suspend. Another event can commit while
                # it runs, so never restore a snapshot taken before preflight.
                # Preflight itself stops before business SQL/Arena mutations;
                # natural Arena timeout cleanup is settled in the next segment.
                pass
            for _ in range(8):
                original = self._snapshot()

                def write():
                    try:
                        result = callback()
                    except CommitBoundary:
                        self.persist_arena()
                        raise
                    self.persist_arena()
                    return result

                try:
                    outcome = self.transaction(write, allow_commit_boundary=True)
                except BaseException:
                    self._restore(original)
                    raise
                if not outcome.get('boundary'):
                    return outcome.get('result')
            raise sqlite3.OperationalError('Too many explicit transaction boundaries')
        finally:
            REQUEST_SCOPE.reset(token)

    def initialize(self):
        from backend.database import BACKEND, execute_sql

        def migrate():
            db = Connection(self)
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations '
                       '(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            applied = {row[0] for row in db.execute('SELECT name FROM schema_migrations')}
            for path in sorted((BACKEND / 'migrations').glob('*.sql')):
                if path.name not in applied:
                    execute_sql(db, path.read_text(encoding='utf-8'))
                    db.execute('INSERT INTO schema_migrations(name) VALUES (?)', (path.name,))
            db.execute('CREATE TABLE IF NOT EXISTS cloudflare_arena_rooms '
                       "(bucket TEXT NOT NULL CHECK(bucket IN ('rooms','retired')),room_key TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(bucket,room_key))")

        self.transaction(migrate)
