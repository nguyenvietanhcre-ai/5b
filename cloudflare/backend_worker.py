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
import release_audit
from release_bridge import website_request,bunny_transport,bunny_lifecycle,install_release,require_complete


def api_path(path):
    return path.startswith(('/api/v1/', '/api/staff/', '/api/local-pilot/', '/api/family/', '/api/trial/', '/api/website/')) or path in ('/api/health', '/api/grade', '/api/webhooks/sepay','/api/site-visibility/check','/quan-tri/bao-tri/','/quan-tri/bao-tri')


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
    os.environ['MAM_TOAN_CURRICULUM_SAMPLES'] = getattr(env,'MAM_TOAN_CURRICULUM_SAMPLES','0')
    os.environ['MAM_TOAN_RESET_BASE_URL'] = env.PUBLIC_ORIGIN
    bunny=getattr(env,'BUNNY_STREAM_CONFIG_JSON',None)
    if bunny is not None:os.environ['BUNNY_STREAM_CONFIG_JSON']=bunny
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
        self.learning = None
        self.demo_games = None
        self.trial_alarm_scheduled=False
        if getattr(env,'DEMO_GAMES_ENABLED','false')=='true':
            from native_learning import CloudDemoGames
            self.demo_games = CloudDemoGames()

    def initialize(self):
        if not self.ready:
            from backend.platform_api import initialize_catalog
            self.database.initialize()
            self.database.run(lambda: initialize_catalog(self.database))
            self.database.restore_arena()
            if getattr(self.env,'NATIVE_LEARNING_ENABLED','false')=='true':
                from native_learning import CloudLearning
                self.learning = CloudLearning(self.database)
                self.database.run(self.learning.path.initialize)
                from backend import platform_api as api
                from backend.content_retirement import activate,retired
                def retire_legacy_grade5():
                    with api.connect(self.database,True) as db:
                        if not retired(db,5):activate(db)
                self.database.run(retire_legacy_grade5)
            self.ready = True

    async def schedule_trial_cleanup(self):
        if not self.trial_alarm_scheduled and getattr(self.env,'QA_LEGACY_CONTRACT','0')!='1':
            import time
            await self.ctx.storage.setAlarm(int(time.time()*1000)+3600000)
            self.trial_alarm_scheduled=True

    async def alarm(self):
        configure(self.env)
        release_id=getattr(self.env,'RELEASE_ID','')
        if release_id and not release_audit.is_open(self.database,release_id):
            import time
            await self.ctx.storage.setAlarm(int(time.time()*1000)+30000)
            return
        self.initialize()
        from backend import platform_api as api
        from backend.trial_experience import cleanup
        def expire():
            with api.connect(self.database,True) as db:cleanup(db)
        self.database.run(expire)
        self.trial_alarm_scheduled=False
        await self.schedule_trial_cleanup()

    async def fetch(self, request):
        path = urlsplit(request.url).path
        method = str(request.method)
        try:
            configure(self.env)
            if path.startswith('/__ops/'):
                transfer.authorize(self.env, request.headers, importing=path == '/__ops/import')
                release_id=getattr(self.env,'RELEASE_ID','')
                if path == '/__ops/release-begin' and method == 'POST':
                    raw=await bounded_body(request,4096)
                    if json.loads(raw)!={'releaseId':release_id}:raise APIError('Release identity mismatch.',409)
                    payload=release_audit.begin(self.database,release_id)
                elif path == '/__ops/release-audit' and method == 'GET':
                    payload=release_audit.compare(self.database,release_id)
                elif path == '/__ops/release-finalize' and method == 'POST':
                    raw=await bounded_body(request,4096)
                    if json.loads(raw)!={'releaseId':release_id}:raise APIError('Release identity mismatch.',409)
                    require_complete(self.database)
                    payload=release_audit.finalize(self.database,release_id)
                elif path == '/__ops/status' and method == 'GET':
                    payload = transfer.status(self.database)
                elif path == '/__ops/export' and method == 'GET':
                    payload = transfer.export_data(self.database)
                elif path == '/__ops/import' and method == 'POST':
                    raw = await bounded_body(request, transfer.MAX_TRANSFER)
                    if not 0 < len(raw) <= transfer.MAX_TRANSFER:
                        raise APIError('Tệp chuyển dữ liệu vượt giới hạn 16 MiB.', 413)
                    payload = transfer.import_data(self.database, json.loads(raw))
                    self.ready = False
                    self.learning = None
                elif path == '/__ops/release-content' and method == 'POST':
                    if release_id and not release_audit.get(self.database,release_id):raise APIError('Record the tenant baseline before migration.',409)
                    self.initialize()
                    raw=await bounded_body(request,4096)
                    payload=install_release(self.database,self.learning,json.loads(raw))
                    self.learning=None
                    self.ready=False
                else:
                    raise APIError('API không tồn tại.', 404)
                return Response.json(payload, headers={'Cache-Control': 'no-store'})
            if not api_path(path):
                raise APIError('API không tồn tại.', 404)
            from backend import site_visibility as visibility
            # The recovery HTML is self-contained and must remain reachable
            # even if release storage or the learning subsystem is unavailable.
            if path in (visibility.PORTAL,visibility.PORTAL.rstrip('/')) and method in ('GET','HEAD'):
                return Response(visibility.page(True) if method=='GET' else b'',status=200,headers=visibility.headers(True))
            recovery=path in visibility.RECOVERY
            release_id=getattr(self.env,'RELEASE_ID','')
            if release_id and path!='/api/health' and not recovery and not release_audit.is_open(self.database,release_id):
                return Response('Bản cập nhật đang được kiểm tra. Vui lòng quay lại sau ít phút.',status=503,headers={'Cache-Control':'no-store','Retry-After':'30','X-5BMath-Maintenance':'1'})
            pending_import = getattr(self.env, 'TRANSFER_ENABLED', 'false') == 'true' and not transfer.table_names(self.database)
            if path == '/api/health' and method == 'GET':
                return Response.json({'status': 'ok', 'ready': not pending_import and (not release_id or release_audit.is_open(self.database,release_id)),
                                      'backend': 'python-durable-object-sqlite'}, headers={'Cache-Control': 'no-store'})
            if pending_import:
                raise APIError('Hệ thống đang chuyển dữ liệu. Vui lòng quay lại sau.', 503)
            if recovery:
                self.database.initialize()
            else:
                self.initialize()
                await self.schedule_trial_cleanup()
            if not visibility.exempt(method,path) and self.database.run(lambda:visibility.read(self.database))['hidden']:
                return Response(visibility.page() if method!='HEAD' else b'',status=503,headers=visibility.headers())
            if path=='/api/site-visibility/check' and method in ('GET','HEAD'):
                return Response(None,status=204,headers={'Cache-Control':'no-store'})
            crypto_compat.install()
            body = None
            raw = b''
            if method == 'POST':
                if request.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                    raise APIError('Use application/json', 415)
                limit = 32768 if path.startswith(('/api/family/','/api/trial/')) else 262144 if path.startswith(('/api/staff/','/api/website/admin/')) else 16384
                if path in ('/api/staff/lessons','/api/staff/native-lessons'):limit=8*1024*1024
                if re.fullmatch(r'/api/(?:v1|local-pilot)/exams/\d+/scratch',path):limit=1048576+2048
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
            handler.server.server_port = urlsplit(request.url).port or (443 if request.url.startswith('https:') else 80)
            handler.server.local_pilot_ports = {handler.server.server_port}
            handler.server.local_pilot = self.learning
            handler.server.cloud_learning_provider = self.learning
            handler.server.cloud_pdf_enabled = self.learning is not None
            handler.server.local_test_games = self.demo_games
            handler.server.cloud_demo_games = self.demo_games
            handler.server.cloud_paid_credits_enabled = self.learning is not None
            handler.server.bunny_stream_transport = bunny_transport
            handler.server.bunny_upload_lifecycle = bunny_lifecycle
            handler.server.real_accounts = True
            handler.server.family_registration_enabled = getattr(self.env,'QA_LEGACY_CONTRACT','0')!='1'
            handler.server.website_readiness_enabled = getattr(self.env,'QA_LEGACY_CONTRACT','0')!='1'
            if path.startswith('/api/family/'):
                from backend.family_accounts import request as family_request
                callback=lambda:family_request(handler,method,path,body)
            elif path.startswith('/api/trial/'):
                from backend.trial_experience import route as trial_request
                callback=lambda:trial_request(handler,method,path,body)
            elif path.startswith('/api/website/'):
                callback=lambda:website_request(handler,method,path,body)
            elif path.startswith('/api/staff/question-access'):
                from backend.question_access import request as question_request
                callback=lambda:question_request(handler,method,path,body)
            elif path.startswith('/api/local-pilot/'):
                if self.learning is None:raise APIError('Kho học tập chưa được cấu hình.',503)
                from urllib.parse import parse_qs
                from backend.system_settings import require_feature
                route = path[len('/api/local-pilot/'):]
                callback = lambda: (self.learning.request(handler,method,route,body,parse_qs(urlsplit(request.url).query)),200)
            elif path == '/api/webhooks/sepay':
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
            if isinstance(payload,dict) and 'authenticated' in payload:payload['localPilotEnabled']=self.learning is not None
            response_headers = {**handler.api_headers, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
            if isinstance(payload,dict) and isinstance(payload.get('_lesson_binary'),bytes):
                from urllib.parse import quote
                return Response(payload['_lesson_binary'],status=status,headers={**response_headers,'Content-Type':payload['mime'],'Content-Disposition':'attachment; filename="lesson-material.pdf"; filename*=UTF-8'''+quote(payload['filename'],safe=''),'Content-Security-Policy':"sandbox; default-src 'none'"})
            if isinstance(payload,dict) and isinstance(payload.get('_local_binary'),bytes):
                return Response(payload['_local_binary'],status=status,headers={**response_headers,'Content-Type':payload['mime'],'Content-Security-Policy':"sandbox; default-src 'none'"})
            if isinstance(payload, dict) and isinstance(payload.get('_binary'), bytes):
                response_headers.update({'Content-Type': payload['contentType'], 'Content-Disposition': payload['disposition'],
                                         'Content-Security-Policy': "sandbox; default-src 'none'"})
                return Response(payload['_binary'], status=status, headers=response_headers)
            return Response.json(payload, status=status, headers=response_headers)
        except (APIError, ArenaError) as error:
            payload = {'error': str(error)}
            if getattr(error, 'arenaDiscipline', None):
                payload['arenaDiscipline'] = error.arenaDiscipline
            if getattr(error,'familyAccessChanged',False):payload['familyAccessChanged']=True
            if isinstance(getattr(error,'code',None),str):payload['code']=error.code
            if getattr(error,'allocation',None) is not None:payload.update(reconfirm=True,allocation=error.allocation)
            for key in ('gameClaim','gameConflicts'):
                if hasattr(error,key):payload[key]=getattr(error,key)
            return Response.json(payload, status=error.status, headers={'Cache-Control': 'no-store'})
        except (ValueError, UnicodeError, TypeError, RecursionError):
            return Response.json({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=400, headers={'Cache-Control': 'no-store'})
        except sqlite3.Error as error:
            from js import console
            console.error(json.dumps(crypto_compat.safe_error_report(error), ensure_ascii=True))
            return Response.json({'error': 'Chưa thể lưu dữ liệu. Em hãy thử lại.'}, status=503, headers={'Cache-Control': 'no-store'})
        except Exception as error:
            from js import console
            console.error(json.dumps(crypto_compat.safe_error_report(error), ensure_ascii=True))
            return Response.json({'error': 'Chưa thể xử lý yêu cầu. Em hãy thử lại.'}, status=503, headers={'Cache-Control': 'no-store'})


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlsplit(request.url).path
        if path == '/api/grade':
            stub=self.env.SCHOOLS.getByName(self.env.TENANT_KEY)
            check=await stub.fetch(Request(urlsplit(request.url)._replace(path='/api/site-visibility/check',query='').geturl(),method='GET'))
            if check.status!=204:return check
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
