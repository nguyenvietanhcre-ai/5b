"""Operator-only SQLite transfer files. Data-bearing output stays under work/."""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.backups import backup, verify

FORMAT = '5bmath-sqlite-transfer'
MAX_BYTES = 16 * 1024 * 1024
MAX_BLOB = 8 * 1024 * 1024
MAX_SQL = 100_000
MAX_PARAMS = 100
WORK = ROOT / 'work'


class TransferError(ValueError):
    """An intentionally data-free operator error."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def checksum(payload):
    return hashlib.sha256(canonical({k:v for k,v in payload.items() if k != 'transferSha256'})).hexdigest()


def quote_name(value):
    return '"' + value.replace('"', '""') + '"'


def output_path(path):
    candidate = Path(path).absolute()
    if candidate.is_symlink():
        raise TransferError('Output must be a new regular file under work/')
    resolved = candidate.resolve()
    if not resolved.is_relative_to(WORK.resolve()) or resolved == WORK.resolve():
        raise TransferError('Data-bearing output must stay under project work/')
    if resolved.exists() or any(Path(str(resolved)+s).exists() or Path(str(resolved)+s).is_symlink()
                                for s in ('-wal','-shm','-journal')):
        raise TransferError('Output already exists; choose a new path')
    return resolved


def reserve(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)


def table_names(db):
    return [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name")]


def counts(db):
    return {name:db.execute('SELECT count(*) FROM '+quote_name(name)).fetchone()[0] for name in table_names(db)}


def bound_value(value):
    if value is None or isinstance(value, str):
        return '?', value
    if isinstance(value, int):
        return 'CAST(? AS INTEGER)', {'integer':str(value)}
    if isinstance(value, float):
        if math.isinf(value):
            return '9e999' if value > 0 else '-9e999', None
        if not math.isfinite(value):
            raise TransferError('Unsupported non-finite numeric value')
        return 'CAST(? AS REAL)', {'real':repr(value)}
    if isinstance(value, bytes):
        if len(value) > MAX_BLOB:
            raise TransferError('A BLOB exceeds the transfer value limit; migrate storage chunks first')
        return '?', {'base64':base64.b64encode(value).decode('ascii')}
    raise TransferError('Unsupported SQLite value type')


def inserts(db, table):
    columns = [row[1] for row in db.execute('PRAGMA table_xinfo('+quote_name(table)+')') if row[6] == 0]
    if len(columns) > MAX_PARAMS:
        raise TransferError('A table exceeds the transfer column limit')
    prefix = 'INSERT INTO '+quote_name(table)+'('+','.join(map(quote_name,columns))+') VALUES('
    for row in db.execute('SELECT '+','.join(map(quote_name,columns))+' FROM '+quote_name(table)):
        expressions, params = [], []
        for value in row:
            expression, param = bound_value(value)
            expressions.append(expression)
            if '?' in expression:
                params.append(param)
        yield {'sql':prefix+','.join(expressions)+');', 'params':params}


def dump_snapshot(path):
    verified = verify(path, require_manifest=True)
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND upper(sql) LIKE 'CREATE VIRTUAL TABLE%' LIMIT 1").fetchone():
            raise TransferError('Virtual tables are outside transfer protocol v1')
        table_schema, statements, late_schema, emitted = [], [], [], set()
        # iterdump can place sqlite_sequence data after trigger DDL. Keep all
        # index/trigger/view creation until after *every* table's row data.
        # Parameterize its data phase to preserve large BLOBs, NUL text and
        # exact 64-bit integers across the JavaScript bridge.
        for statement in db.iterdump():
            upper = statement.strip().upper()
            if upper in ('BEGIN TRANSACTION;', 'COMMIT;') or upper.startswith('PRAGMA '):
                continue
            if upper.startswith('CREATE TABLE'):
                table_schema.append(statement)
                continue
            if upper.startswith(('CREATE INDEX','CREATE UNIQUE INDEX','CREATE TRIGGER','CREATE VIEW')):
                late_schema.append(statement)
                continue
            if upper.startswith('INSERT INTO '):
                match = re.match(r'INSERT INTO "((?:[^"]|"")+)"', statement)
                if not match:
                    raise TransferError('Unsupported SQLite dump INSERT layout')
                table = match.group(1).replace('""','"')
                if table not in emitted:
                    statements.extend(inserts(db, table))
                    emitted.add(table)
            else:
                statements.append(statement)
        statements = table_schema + statements + late_schema
        payload = {'format':FORMAT,'version':1,'createdAt':datetime.now(timezone.utc).isoformat(),
                   'source':{'kind':'sqlite','sha256':verified['sha256'],'tables':counts(db),'bookmark':None},
                   'statements':statements}
    payload['transferSha256'] = checksum(payload)
    validate(payload)
    return payload


def decode_param(value):
    if value is None or isinstance(value,str):
        return value
    if not isinstance(value,dict) or len(value) != 1:
        raise TransferError('Invalid typed SQL parameter')
    if 'integer' in value:
        raw = value['integer']
        if not isinstance(raw,str) or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)',raw) or not -(2**63) <= int(raw) < 2**63:
            raise TransferError('Invalid 64-bit integer parameter')
        return raw  # SQL CAST(? AS INTEGER) retains the exact value in JS too.
    if 'real' in value:
        raw = value['real']
        if not isinstance(raw,str) or not math.isfinite(float(raw)):
            raise TransferError('Invalid real parameter')
        return raw
    if 'base64' in value:
        try:
            raw = base64.b64decode(value['base64'], validate=True)
        except (ValueError, TypeError) as error:
            raise TransferError('Invalid BLOB parameter') from error
        if len(raw) > MAX_BLOB:
            raise TransferError('BLOB exceeds transfer value limit')
        return raw
    raise TransferError('Unknown SQL parameter type')


def validate(payload):
    expected = {'format','version','createdAt','source','statements','transferSha256'}
    if not isinstance(payload,dict) or set(payload) != expected or payload['format'] != FORMAT or type(payload['version']) is not int or payload['version'] != 1:
        raise TransferError('Unsupported transfer format')
    if len(canonical(payload)) + 1 > MAX_BYTES:
        raise TransferError('Transfer exceeds the payload limit')
    if payload['transferSha256'] != checksum(payload):
        raise TransferError('Transfer checksum does not match')
    try:
        if datetime.fromisoformat(payload['createdAt'].replace('Z','+00:00')).tzinfo is None:
            raise ValueError()
        source = payload['source']
        if set(source) != {'kind','sha256','tables','bookmark'} or source['kind'] not in ('sqlite','cloudflare'):
            raise ValueError()
        if source['sha256'] is not None and not re.fullmatch(r'[0-9a-f]{64}',source['sha256']):
            raise ValueError()
        if source['kind'] == 'sqlite' and source['sha256'] is None:
            raise ValueError()
        if source['bookmark'] is not None and not isinstance(source['bookmark'],str):
            raise ValueError()
        if not isinstance(source['tables'],dict) or not source['tables'] or any(not isinstance(n,str) or type(c) is not int or c < 0 for n,c in source['tables'].items()):
            raise ValueError()
    except (AttributeError, TypeError, ValueError) as error:
        raise TransferError('Invalid transfer provenance metadata') from error
    if not isinstance(payload['statements'],list) or not payload['statements']:
        raise TransferError('Transfer has no ordered statements')
    saw_trigger = False
    for statement in payload['statements']:
        sql = statement if isinstance(statement,str) else statement.get('sql') if isinstance(statement,dict) else None
        if not isinstance(sql,str) or not sql or len(sql.encode('utf-8')) > MAX_SQL:
            raise TransferError('Invalid or oversized SQL statement')
        upper = sql.lstrip().upper()
        if upper.startswith(('BEGIN','COMMIT','ROLLBACK','PRAGMA','ATTACH','DETACH')):
            raise TransferError('Transaction/control SQL is not allowed in transfer files')
        if upper.startswith('CREATE TRIGGER'):
            saw_trigger = True
        if saw_trigger and upper.startswith(('INSERT','DELETE','CREATE TABLE')):
            raise TransferError('Row data must precede trigger creation')
        if isinstance(statement,dict):
            if set(statement) != {'sql','params'} or not upper.startswith('INSERT INTO ') or not isinstance(statement['params'],list) or len(statement['params']) > MAX_PARAMS:
                raise TransferError('Invalid parameterized INSERT')
            for param in statement['params']:
                decode_param(param)
    return payload


def save_payload(payload, output):
    validate(payload)
    output = output_path(output)
    descriptor = reserve(output)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(canonical(payload)+b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return output


def load_payload(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise TransferError('Transfer exceeds the payload limit')
    return validate(json.loads(data))


def prepare(source, output):
    output = output_path(output)
    snapshot = backup(source, output.parent / (output.stem+'-snapshots'))
    payload = dump_snapshot(snapshot)
    save_payload(payload, output)
    return payload, snapshot


def authorizer(action, one, two, database, trigger):
    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and (two or one or '').lower() == 'load_extension':
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def restore_payload(payload, target):
    validate(payload)
    target = output_path(target)
    os.close(reserve(target))
    try:
        with closing(sqlite3.connect(target)) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('BEGIN IMMEDIATE')
            db.execute('PRAGMA defer_foreign_keys=ON')
            db.set_authorizer(authorizer)
            for statement in payload['statements']:
                if isinstance(statement,str):
                    db.execute(statement)
                else:
                    db.execute(statement['sql'],tuple(decode_param(p) for p in statement['params']))
            db.set_authorizer(None)
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
                raise TransferError('Restored transfer fails database checks')
            if counts(db) != payload['source']['tables']:
                raise TransferError('Restored transfer table counts differ')
            db.commit()
        verify(target)
    except BaseException:
        target.unlink(missing_ok=True)
        for suffix in ('-wal','-shm','-journal'):
            Path(str(target)+suffix).unlink(missing_ok=True)
        raise
    return target


def fingerprints(path):
    """Digest every declared row value without returning/logging those values."""
    result = {}
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        for table in table_names(db):
            rows = []
            for row in db.execute('SELECT * FROM '+quote_name(table)):
                encoded = []
                for value in row:
                    expression,param = bound_value(value)
                    encoded.append({'expression':expression,'value':param})
                rows.append(canonical(encoded))
            digest = hashlib.sha256()
            for row in sorted(rows):
                digest.update(str(len(row)).encode('ascii')+b':'+row)
            result[table] = {'count':len(rows),'sha256':digest.hexdigest()}
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TransferError('Operator endpoint redirects are not allowed')


def remote_request(action, payload=None):
    origin = os.environ.get('MAM_TOAN_CLOUDFLARE_OPERATOR_URL','').rstrip('/')
    parsed = urlsplit(origin)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or not parsed.hostname or not (
            parsed.scheme == 'https' or parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1','localhost')):
        raise TransferError('Set a valid HTTPS operator origin')
    secret_path = Path(os.environ.get('MAM_TOAN_CLOUDFLARE_OPERATOR_SECRET_FILE',''))
    if not secret_path.is_file() or secret_path.is_symlink():
        raise TransferError('Operator secret must come from a protected regular file')
    with secret_path.open('r',encoding='utf-8') as stream:
        stored = stream.read(65537).strip()
    if len(stored) > 65536:
        raise TransferError('Operator configuration exceeds the supported size')
    # Reuse the deployment's existing protected JSON file. Never require an
    # extra plaintext copy of an operator credential just for this command.
    token = json.loads(stored).get('OPERATOR_TOKEN', '') if stored.startswith('{') else stored
    if not isinstance(token, str):
        raise TransferError('Invalid operator secret file')
    if not 32 <= len(token) <= 512 or any(c.isspace() for c in token):
        raise TransferError('Invalid operator secret file')
    body = canonical(validate(payload)) if payload is not None else None
    request = Request(origin+'/__ops/'+action, data=body,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json',
                 'User-Agent':'5BMath-Operator/1.0 (+https://5bmath.vn/)'},
        method='POST' if action == 'import' else 'GET')
    try:
        with build_opener(NoRedirect()).open(request,timeout=60) as response:
            data = response.read(MAX_BYTES+1)
    except (HTTPError, URLError) as error:
        raise TransferError('Operator request failed; check endpoint/access without logging response data') from error
    if len(data) > MAX_BYTES:
        raise TransferError('Remote response exceeds transfer payload limit')
    return json.loads(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    local = commands.add_parser('prepare')
    local.add_argument('--source',type=Path,required=True)
    local.add_argument('--output',type=Path,required=True)
    recover = commands.add_parser('restore')
    recover.add_argument('--input',type=Path,required=True)
    recover.add_argument('--target',type=Path,required=True)
    compare = commands.add_parser('compare')
    compare.add_argument('--left',type=Path,required=True)
    compare.add_argument('--right',type=Path,required=True)
    send = commands.add_parser('import')
    send.add_argument('--input',type=Path,required=True)
    fetch = commands.add_parser('export')
    fetch.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'prepare':
            payload,snapshot = prepare(args.source,args.output)
            result = {'prepared':True,'file':str(args.output),'snapshot':str(snapshot),'tables':len(payload['source']['tables']),
                      'statements':len(payload['statements']),'transferSha256':payload['transferSha256']}
        elif args.command == 'restore':
            restored = restore_payload(load_payload(args.input),args.target)
            result = {'restored':True,'file':str(restored)}
        elif args.command == 'compare':
            left,right = fingerprints(args.left),fingerprints(args.right)
            if left != right:
                raise TransferError('Database row-value fingerprints differ')
            result = {'match':True,'tables':len(left)}
        elif args.command == 'import':
            payload = load_payload(args.input)
            response = remote_request('import',payload)
            if (not isinstance(response,dict) or response.get('imported') is not True or
                    response.get('tables') != payload['source']['tables'] or
                    response.get('transferSha256') != payload['transferSha256']):
                raise TransferError('Remote import acknowledgement does not match')
            result = {'imported':True}
        else:
            payload = validate(remote_request('export'))
            saved = save_payload(payload,args.output)
            restored = restore_payload(payload,saved.with_suffix('.verified.sqlite3'))
            result = {'exported':True,'file':str(saved),'verifiedRestore':str(restored),'tables':len(payload['source']['tables'])}
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except Exception:
        # SQL, HTTP bodies and parser diagnostics can contain credentials/rows.
        print(json.dumps({'error':'Transfer failed; verify inputs, limits, protected operator configuration and a fresh output path.'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
