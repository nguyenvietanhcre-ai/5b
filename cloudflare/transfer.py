"""Operator-only, empty-database transfer format shared with the local tool."""
import base64
import hashlib
import hmac
import json
import math
import re
from datetime import datetime, timezone

from backend.platform_api import APIError
from sqlite_storage import Connection

FORMAT = '5bmath-sqlite-transfer'
MAX_TRANSFER = 16 * 1024 * 1024
FIELDS = {'format', 'version', 'createdAt', 'source', 'statements', 'transferSha256'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def authorize(env, headers, importing=False):
    expected = getattr(env, 'OPERATOR_TOKEN', '')
    supplied = headers.get('Authorization', '')
    if (importing and getattr(env, 'TRANSFER_ENABLED', 'false') != 'true' or not isinstance(expected, str) or len(expected) < 32 or
            not isinstance(supplied, str) or not supplied.startswith('Bearer ') or
            not hmac.compare_digest(supplied[7:].encode(), expected.encode())):
        raise APIError('API không tồn tại.', 404)


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def table_names(database):
    return [row['name'] for row in database.storage.sql.exec(
        "SELECT name FROM sqlite_master WHERE type='table' AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name")
        if not row['name'].startswith(('_cf_', '__cf_'))]


def counts(database):
    return {name: database.storage.sql.exec('SELECT count(*) AS n FROM ' + quote_identifier(name)).one()['n']
            for name in table_names(database)}


def bookmark(database):
    from pyodide.ffi import run_sync
    try:
        return run_sync(database.storage.getCurrentBookmark())
    except Exception as error:
        if any(message in str(error).lower() for message in ('not implemented', 'not supported', 'local mode')):
            return None
        raise


def status(database):
    return {'format': FORMAT, 'version': 1, 'tables': counts(database), 'bookmark': bookmark(database)}


def _parameter(value):
    if value is None or isinstance(value, str):
        return value
    if not isinstance(value, dict) or len(value) != 1:
        raise APIError('Tham số chuyển dữ liệu không hợp lệ.')
    if 'integer' in value and isinstance(value['integer'], str) and re.fullmatch(r'-?(0|[1-9][0-9]*)', value['integer']):
        number = int(value['integer'])
        if -(2**63) <= number < 2**63:
            return value['integer']
    if 'real' in value and isinstance(value['real'], str):
        try:
            if math.isfinite(float(value['real'])):
                return value['real']
        except ValueError:
            pass
    if 'base64' in value and isinstance(value['base64'], str):
        try:
            decoded = base64.b64decode(value['base64'], validate=True)
            if len(decoded) <= 8 * 1024 * 1024:
                return memoryview(decoded)
        except (ValueError, TypeError):
            pass
    raise APIError('Tham số chuyển dữ liệu không hợp lệ.')


def import_data(database, payload):
    if not isinstance(payload, dict) or set(payload) != FIELDS or payload['format'] != FORMAT or payload['version'] != 1:
        raise APIError('Định dạng chuyển dữ liệu không hợp lệ.')
    if not isinstance(payload['transferSha256'], str):
        raise APIError('Thiếu mã kiểm tra dữ liệu.')
    content = {key: value for key, value in payload.items() if key != 'transferSha256'}
    encoded = canonical(content)
    if len(encoded) > MAX_TRANSFER:
        raise APIError('Tệp chuyển dữ liệu vượt giới hạn 16 MiB.', 413)
    if not hmac.compare_digest(hashlib.sha256(encoded).hexdigest(), payload['transferSha256']):
        raise APIError('Mã kiểm tra dữ liệu không khớp.')
    source = payload['source']
    if (not isinstance(source, dict) or set(source) != {'kind', 'sha256', 'tables', 'bookmark'} or
            source['kind'] not in ('sqlite', 'cloudflare') or not isinstance(source['tables'], dict) or
            any(not isinstance(key, str) or type(value) is not int or value < 0 for key, value in source['tables'].items()) or
            not isinstance(payload['statements'], list)):
        raise APIError('Thông tin nguồn dữ liệu không hợp lệ.')

    def write():
        if table_names(database):
            raise APIError('Chỉ nhập vào cơ sở dữ liệu trống. Không ghi đè dữ liệu hiện có.', 409)
        database.storage.sql.exec('PRAGMA defer_foreign_keys=ON')
        for item in payload['statements']:
            if isinstance(item, str):
                sql, parameters = item, ()
            elif isinstance(item, dict) and set(item) == {'sql', 'params'} and isinstance(item['sql'], str) and isinstance(item['params'], list):
                sql, parameters = item['sql'], [_parameter(value) for value in item['params']]
            else:
                raise APIError('Câu lệnh chuyển dữ liệu không hợp lệ.')
            if len(sql.encode('utf-8')) > 100_000 or re.match(r'(?is)^\s*(BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|ATTACH|DETACH)\b', sql):
                raise APIError('Câu lệnh chuyển dữ liệu không được hỗ trợ.')
            database.storage.sql.exec(sql, *parameters)
        if list(database.storage.sql.exec('PRAGMA foreign_key_check')):
            raise APIError('Dữ liệu vi phạm liên kết tài khoản/lớp học.', 409)
        # DO's SQL authorizer disallows integrity_check. This imports logical
        # SQL into a newly constructed engine database, not native file bytes;
        # engine constraints, FK checks and exact table counts run before commit.
        actual = counts(database)
        if actual != source['tables']:
            raise APIError('Số lượng bản ghi không khớp nguồn dữ liệu.', 409)
        return actual

    actual = database.transaction(write).get('result')
    return {'imported': True, 'tables': actual, 'transferSha256': payload['transferSha256'], 'bookmark': bookmark(database)}


def export_data(database):
    def read():
        statements = []
        schema = [row for row in database.storage.sql.exec(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY rowid")
                  if not row['name'].startswith(('_cf_', '__cf_'))]
        for row in schema:
            if row['type'] == 'table':
                if row['sql'].lstrip().upper().startswith('CREATE VIRTUAL'):
                    raise APIError('Bảng ảo chưa được hỗ trợ trong định dạng chuyển dữ liệu.', 409)
                statements.append(row['sql'])
        names = sorted(table_names(database), key=lambda name: name == 'sqlite_sequence')
        for name in names:
            if name == 'sqlite_sequence':
                statements.append('DELETE FROM sqlite_sequence')
            columns = [row['name'] for row in database.storage.sql.exec('PRAGMA table_info(' + quote_identifier(name) + ')')]
            projection = ','.join('typeof(' + quote_identifier(column) + ') AS t' + str(index) +
                                  ',CASE WHEN typeof(' + quote_identifier(column) + ")='blob' THEN " + quote_identifier(column) +
                                  " WHEN typeof(" + quote_identifier(column) + ")='real' THEN printf('%!.17g'," + quote_identifier(column) +
                                  ') ELSE CAST(' + quote_identifier(column) + ' AS TEXT) END AS v' + str(index)
                                  for index, column in enumerate(columns))
            for row in database.storage.sql.exec('SELECT ' + projection + ' FROM ' + quote_identifier(name)):
                parameters, expressions = [], []
                for index in range(len(columns)):
                    kind, value = row['t' + str(index)], row['v' + str(index)]
                    if kind == 'null':
                        parameters.append(None)
                        expressions.append('?')
                    elif kind == 'integer':
                        parameters.append({'integer': value})
                        expressions.append('CAST(? AS INTEGER)')
                    elif kind == 'real':
                        if value in ('Inf', '-Inf'):
                            expressions.append('-9e999' if value.startswith('-') else '9e999')
                        else:
                            parameters.append({'real': value})
                            expressions.append('CAST(? AS REAL)')
                    elif kind == 'blob':
                        parameters.append({'base64': base64.b64encode(bytes(value)).decode('ascii')})
                        expressions.append('?')
                    else:
                        parameters.append(value)
                        expressions.append('?')
                sql = 'INSERT INTO ' + quote_identifier(name) + '(' + ','.join(map(quote_identifier, columns)) + ') VALUES (' + ','.join(expressions) + ')'
                statements.append({'sql': sql, 'params': parameters})
        statements += [row['sql'] for row in schema if row['type'] in ('index', 'trigger', 'view')]
        result = {'format': FORMAT, 'version': 1, 'createdAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                  'source': {'kind': 'cloudflare', 'sha256': None, 'tables': counts(database), 'bookmark': None},
                  'statements': statements}
        encoded = canonical(result)
        if len(encoded) > MAX_TRANSFER:
            raise APIError('Bản xuất vượt giới hạn 16 MiB; cần công cụ sao lưu phân trang.', 413)
        return result

    result = database.transaction(read).get('result')
    result['source']['bookmark'] = bookmark(database)
    result['transferSha256'] = hashlib.sha256(canonical(result)).hexdigest()
    return result
