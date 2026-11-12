"""5BMath's same-origin API service; Pages serves the static site separately."""
import json
import os
import re
import sqlite3
from types import SimpleNamespace
from urllib.parse import urlsplit

from workers import DurableObject, Request, Response, WorkerEntrypoint

from backend.arena import Arena, ArenaError
from backend.platform_api import APIError
from sqlite_storage import StorageDatabase
import crypto_compat
import transfer


def api_path(path):
    return path.startswith(('/api/v1/', '/api/staff/')) or path in ('/api/health', '/api/grade', '/api/webhooks/sepay')


async def bounded_body(request, limit):
    length = request.headers.get('Content-Length')
    if length is not None and (not re.fullmatch(r'[0-9]+', length) or int(length) > limit):
        raise APIError('Kích thước dữ liệu không hợp lệ.', 413)
    if request.body is None:
        return b''
    reader = request.body.getReader()
    data = bytearray()
    while True:
        part = await reader.read()
        if part.done:
            return bytes(data)
        if len(data) + part.value.byteLength > limit:
            await reader.cancel()
            raise APIError('Kích thước dữ liệu vượt giới hạn.', 413)
        data.extend(part.value.to_bytes())


def configure(env):
    # All bindings below are fixed per deployed Worker, never request data.
    os.environ['MAM_TOAN_PUBLIC_ORIGIN'] = env.PUBLIC_ORIGIN
    for name in ('BANK_ID', 'BANK_ACCOUNT', 'BANK_NAME', 'SEPAY_ENABLED', 'SEPAY_WEBHOOK_SECRET'):
        value = getattr(env, 'MAM_TOAN_' + name, None)
        if value is not None:
            os.environ['MAM_TOAN_' + name] = value


class SchoolBackend(DurableObject):
    def __init__(self, ctx, env):
        self.ctx, self.env = ctx, env
        self.arena = Arena()
        self.database = StorageDatabase(ctx.storage, self.arena)
        self.ready = False

    def initialize(self):
        if not self.ready:
            from backend.platform_api import seed_catalog
            self.database.initialize()
            self.database.run(lambda: seed_catalog(self.database))
            self.database.restore_arena()
            self.ready = True

    async def fetch(self, request):
        path = urlsplit(request.url).path
        method = str(request.method)
        try:
            configure(self.env)
            if path.startswith('/__ops/'):
                transfer.authorize(self.env, request.headers, importing=path == '/__ops/import')
                if path == '/__ops/status' and method == 'GET':
                    payload = transfer.status(self.database)
                elif path == '/__ops/export' and method == 'GET':
                    payload = transfer.export_data(self.database)
                elif path == '/__ops/import' and method == 'POST':
                    raw = await bounded_body(request, transfer.MAX_TRANSFER)
                    if not 0 < len(raw) <= transfer.MAX_TRANSFER:
                        raise APIError('Tệp chuyển dữ liệu vượt giới hạn 16 MiB.', 413)
                    payload = transfer.import_data(self.database, json.loads(raw))
                    self.ready = False
                else:
                    raise APIError('API không tồn tại.', 404)
                return Response.json(payload, headers={'Cache-Control': 'no-store'})
            if not api_path(path):
                raise APIError('API không tồn tại.', 404)
            pending_import = getattr(self.env, 'TRANSFER_ENABLED', 'false') == 'true' and not transfer.table_names(self.database)
            if path == '/api/health' and method == 'GET':
                return Response.json({'status': 'ok', 'ready': not pending_import,
                                      'backend': 'python-durable-object-sqlite'}, headers={'Cache-Control': 'no-store'})
            if pending_import:
                raise APIError('Hệ thống đang chuyển dữ liệu. Vui lòng quay lại sau.', 503)
            self.initialize()
            crypto_compat.install()
            body = None
            raw = b''
            if method == 'POST':
                if request.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                    raise APIError('Use application/json', 415)
                limit = 262144 if path.startswith('/api/staff/') else 16384
                if re.fullmatch(r'/api/v1/classes/\d+/assignments/\d+/submissions', path):
                    limit = 4 * ((10 * 1024 * 1024 + 2) // 3) + 2048
                raw = await bounded_body(request, limit)
                if not 0 < len(raw) <= limit:
                    raise APIError('Invalid body', 413)
                if path != '/api/webhooks/sepay':
                    body = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                    if not isinstance(body, dict):
                        raise APIError('Dữ liệu gửi lên không hợp lệ.')
            elif method != 'GET':
                raise APIError('API không tồn tại.', 404)
            headers = request.headers
            if headers.get_all('Host'):
                del headers['Host']
            headers['Host'] = urlsplit(request.url).netloc
            handler = SimpleNamespace(server=SimpleNamespace(database_path=self.database, review_upgrades=False, arena=self.arena),
                                      headers=headers, path=urlsplit(request.url).path + ('?' + urlsplit(request.url).query if urlsplit(request.url).query else ''),
                                      api_headers={}, client_address=(headers.get('X-5BMath-Client-IP', 'unknown'), 0))
            if path == '/api/webhooks/sepay':
                from backend.payments import receive_webhook
                for name in ('X-SePay-Timestamp', 'X-SePay-Signature'):
                    if len(headers.get_all(name, [])) != 1:
                        raise APIError('Invalid webhook authentication', 401)
                callback = lambda: receive_webhook(self.database, headers, raw)
            elif path.startswith('/api/staff/'):
                from backend.staff_api import dispatch
                callback = lambda: dispatch(handler, method, path, body)
            else:
                from backend.platform_api import dispatch
                callback = lambda: dispatch(handler, method, path, body)
            payload, status = self.database.run(callback)
            response_headers = {**handler.api_headers, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
            if isinstance(payload, dict) and isinstance(payload.get('_binary'), bytes):
                response_headers.update({'Content-Type': payload['contentType'], 'Content-Disposition': payload['disposition'],
                                         'Content-Security-Policy': "sandbox; default-src 'none'"})
                return Response(payload['_binary'], status=status, headers=response_headers)
            return Response.json(payload, status=status, headers=response_headers)
        except (APIError, ArenaError) as error:
            payload = {'error': str(error)}
            if getattr(error, 'arenaDiscipline', None):
                payload['arenaDiscipline'] = error.arenaDiscipline
            return Response.json(payload, status=error.status, headers={'Cache-Control': 'no-store'})
        except (ValueError, UnicodeError, TypeError, RecursionError):
            return Response.json({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=400, headers={'Cache-Control': 'no-store'})
        except sqlite3.Error:
            return Response.json({'error': 'Chưa thể lưu dữ liệu. Em hãy thử lại.'}, status=503, headers={'Cache-Control': 'no-store'})
        except Exception as error:
            from js import console
            console.error(json.dumps(crypto_compat.safe_error_report(error), ensure_ascii=True))
            return Response.json({'error': 'Chưa thể xử lý yêu cầu. Em hãy thử lại.'}, status=503, headers={'Cache-Control': 'no-store'})


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlsplit(request.url).path
        if path == '/api/grade':
            try:
                if str(request.method) != 'POST':
                    raise APIError('API không tồn tại.', 404)
                if request.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                    raise APIError('Use application/json', 415)
                raw = await bounded_body(request, 16384)
                body = json.loads(raw)
                if not isinstance(body, dict) or not isinstance(body.get('kind'), str):
                    raise ValueError('Invalid body')
                from backend.content import grade
                return Response.json(grade(body['kind'], body.get('answers')), headers={'Cache-Control': 'no-store'})
            except APIError as error:
                return Response.json({'error': str(error)}, status=error.status)
            except (ValueError, UnicodeError, TypeError, RecursionError):
                return Response.json({'error': 'Invalid quiz or answers'}, status=400)
        if not api_path(path) and not path.startswith('/__ops/'):
            return Response.json({'error': 'API không tồn tại.'}, status=404)
        # The edge overwrites CF-Connecting-IP. Never accept the internal header
        # supplied by the browser; DO bindings are accessible only to this Worker.
        headers = request.headers
        if headers.get_all('X-5BMath-Client-IP'):
            del headers['X-5BMath-Client-IP']
        headers['X-5BMath-Client-IP'] = headers.get('CF-Connecting-IP', 'unknown')
        forwarded = Request(request, headers=list(headers.items()))
        stub = self.env.SCHOOLS.getByName(self.env.TENANT_KEY)
        return await stub.fetch(forwarded)
