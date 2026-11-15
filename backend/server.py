"""Dependency-free HTTP demo; explicitly serve frontend assets only."""
import argparse
import hashlib
import json
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as StandardThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from .content import grade
from .database import count_published_exams, demo_samples, initialize
from .arena import Arena, ArenaError
from .platform_api import APIError, dispatch, initialize_catalog
from .staff_api import dispatch as staff_dispatch

class ThreadingHTTPServer(StandardThreadingHTTPServer):
    # Browsers fetch the game scripts/art concurrently; retain pending sockets
    # while the local machine is busy exporting animations in other chats.
    request_queue_size = 64


ARENA = Arena()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
DEFAULT_DATABASE = FRONTEND.parent / "work" / "database" / "5bmath-demo.sqlite3"
from .assets import public_assets
ASSETS = public_assets()
PAGES = {
    "/bai-hoc-toan-lop-5/": "courses",
    "/so-sanh-so-thap-phan/": "lesson-decimal",
    "/hai-lan-thay-doi-phan-tram/": "lesson-percent",
    "/luyen-tap-so-thap-phan/": "practice",
    "/de-thi-thu-toan-vao-lop-6/": "exam",
    "/tro-choi-xep-so-thap-phan/": "game",
    "/goc-hoc-tap/": "dashboard",
    "/dang-ky-kiem-tra-dau-vao/": "entrance",
}
MAX_BODY = 16384
LEARNING_ROUTES = {
    "hoc-theo-tuan": "weekly", "chuyen-de": "topics", "bai-giang": "lesson",
    "bai-chuyen-de": "advanced", "thi-thu": "exams", "lam-de": "testing",
    "ket-qua-thi": "results", "dau-tri": "arena", "phong-dau": "room",
    "tran-dau": "battle", "ket-qua-tran": "battleResult", "linh-vat": "mascot",
    "xep-hang": "rank", "tai-khoan": "profile", "lop-zoom": "classroom",
    "dang-ky-hoc-zoom": "zoomRegistration", "nang-cap": "upgrade", "thanh-toan": "payment",
    "tra-cuu-cau-hoi": "lookup",
}
PAGES.update({"/" + path + "/": "learn-" + name for path, name in LEARNING_ROUTES.items()})
PRIVATE_PAGES = {"dashboard", *("learn-" + name for name in LEARNING_ROUTES.values())}
PAGES.update({"/giao-vien/": "staff-teacher", "/quan-tri/": "staff-admin"})
PRIVATE_PAGES.update({"staff-teacher", "staff-admin"})

class Handler(BaseHTTPRequestHandler):
    server_version = "MamToan"
    def log_request(self, code='-', size='-'):
        # Contact searches and other private query parameters do not belong in access logs.
        self.log_message('"%s %s %s" %s %s', self.command, urlsplit(self.path).path,
                         self.request_version, str(code), str(size))

    def respond(self, status, body, content_type, cache_control="no-store", etag=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", cache_control)
        if etag:
            self.send_header("ETag", etag)
        for key, value in getattr(self, 'api_headers', {}).items():
            self.send_header(key, value)
        self.api_headers = {}
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
    def json_response(self, status, payload):
        self.respond(status, json.dumps(payload, ensure_ascii=False).encode(),
                     "application/json; charset=utf-8")
    def do_GET(self):
        url = urlsplit(self.path)
        route = unquote(url.path)
        if route.startswith('/api/local-pilot/'):
            self.local_pilot_request('GET',route)
            return
        if route.startswith(('/api/v1/', '/api/staff/')):
            self.platform_request('GET', route)
        elif route == "/api/health":
            self.json_response(200, {"status": "ok", "backend": "python", "mode": "demo"})
        elif route == "/api/database-demo":
            try:
                published_exams = count_published_exams(self.server.database_path)
            except sqlite3.Error:
                self.json_response(503, {"status": "unavailable"})
            else:
                self.json_response(200, {"status": "ok", "published_exams": published_exams})
        elif route == "/api/database-demo/samples":
            try:
                payload = demo_samples(self.server.database_path)
            except sqlite3.Error:
                self.json_response(503, {"status": "unavailable"})
            else:
                self.json_response(200, payload)
        elif route in ASSETS or route in PAGES or route in ('/robots.txt', '/sitemap.xml'):
            page = "home" if route in ("/", "/index.html") else PAGES.get(route)
            file = FRONTEND / ("admissions.html" if page == "entrance" else "index.html" if page else ASSETS.get(route, 'index.html'))
            if route in ('/robots.txt', '/sitemap.xml'):
                file = FRONTEND / 'public-pages' / route[1:]
            built = FRONTEND / 'public-pages' / route.strip('/') / 'index.html'
            if route == '/index.html':
                built = FRONTEND / 'public-pages' / 'index.html'
            if page and built.is_file():
                file = built
            prerendered = file.is_relative_to(FRONTEND / 'public-pages')
            try:
                mime = {".js":"text/javascript", ".css":"text/css", ".html":"text/html",
                        ".svg":"image/svg+xml", ".webp":"image/webp", ".png":"image/png", ".json":"application/json",
                        ".txt":"text/plain", ".xml":"application/xml"}[file.suffix]
                body = file.read_bytes()
                if file.suffix == '.html' and page != 'entrance' and not prerendered:
                    body = body.replace(b'<html lang="vi"', b'<html lang="vi" data-backend="database"', 1)
                if page and page != "entrance" and not prerendered:
                    body = body.replace(b'    <link rel="canonical" href="https://5bmath.vn/">', b'')
                    body = body.replace(b'<html lang="vi"', f'<html lang="vi" data-page="{page}"'.encode(), 1)
                    body = body.replace(b"<head>", b'<head>\n    <base href="../">', 1)
                    if page == "dashboard":
                        body = body.replace(b'<html lang="vi"', b'<html lang="vi" data-database="enabled"', 1)
                    if page in PRIVATE_PAGES:
                        body = body.replace(b"</head>", b'    <meta name="robots" content="noindex">\n</head>', 1)
                etag = '"' + hashlib.sha256(body).hexdigest() + '"'
                cache = 'no-store' if page in PRIVATE_PAGES else 'public, max-age=0, must-revalidate'
                if cache != 'no-store' and self.headers.get('If-None-Match') == etag:
                    self.respond(304, b'', mime, cache, etag)
                else:
                    self.respond(200, body, mime if file.suffix in ('.webp', '.png') else mime + '; charset=utf-8', cache, etag)
            except OSError:
                self.json_response(500, {"error":"Frontend unavailable"})
        elif route + "/" in PAGES:
            self.send_response(308)
            self.send_header("Location", route + "/" + ("?" + url.query if url.query else ""))
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.json_response(404, {"error":"Not found"})
    def do_HEAD(self):
        self.do_GET()
    def do_POST(self):
        endpoint = urlsplit(self.path).path
        if endpoint.startswith('/api/local-pilot/'):
            self.local_pilot_request('POST',endpoint)
            return
        if endpoint == '/api/webhooks/sepay':
            self.sepay_request()
            return
        if endpoint.startswith(('/api/v1/', '/api/staff/')):
            self.platform_request('POST', endpoint)
            return
        if endpoint == '/api/arena' and getattr(self.server, 'real_accounts', False):
            self.json_response(403, {'error': 'Đăng nhập và sử dụng API tài khoản để vào phòng.'})
            return
        if endpoint not in ("/api/grade", "/api/arena"):
            self.json_response(404, {"error":"Not found"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self.json_response(415, {"error":"Use application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.json_response(400, {"error":"Invalid content length"})
            return
        if not 0 < length <= MAX_BODY:
            self.json_response(413, {"error":"Invalid request size"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode())
            if not isinstance(body, dict):
                raise ValueError("Invalid body")
            if endpoint == "/api/arena":
                result = ARENA.handle(body)
            else:
                if not isinstance(body.get("kind"), str):
                    raise ValueError("Invalid body")
                result = grade(body["kind"], body.get("answers"))
        except ArenaError as error:
            self.json_response(error.status, {"error": str(error)})
            return
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self.json_response(400, {"error":"Invalid quiz or answers"})
            return
        self.json_response(200, result)
    def sepay_request(self):
        """Keep signed request bytes intact; bank events do not use student cookies."""
        self.api_headers = {}
        try:
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise APIError('Use application/json', 415)
            lengths = self.headers.get_all('Content-Length', [])
            if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch(r'[0-9]+', lengths[0]):
                raise APIError('Invalid content length', 400)
            length = int(lengths[0])
            if not 0 < length <= MAX_BODY:
                raise APIError('Invalid request size', 413)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise APIError('Incomplete request body', 400)
            for name in ('X-SePay-Signature', 'X-SePay-Timestamp'):
                if len(self.headers.get_all(name, [])) != 1:
                    raise APIError('Invalid webhook authentication', 401)
            from .payments import receive_webhook
            payload, status = receive_webhook(self.server.database_path, self.headers, raw)
        except APIError as error:
            self.json_response(error.status, {'success': False, 'error': str(error)})
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self.json_response(400, {'success': False, 'error': 'Invalid webhook data'})
        except sqlite3.Error:
            self.log_error('Payment database operation failed')
            self.json_response(503, {'success': False, 'error': 'Payment storage unavailable'})
        else:
            self.json_response(status, payload)

    def local_pilot_request(self,method,endpoint):
        self.api_headers={}
        provider=getattr(self.server,'local_pilot',None)
        if provider is None:self.json_response(404,{'error':'Thí điểm cục bộ chưa bật.'});return
        try:
            body=None
            if method=='POST':
                if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise APIError('Use application/json',415)
                length=int(self.headers.get('Content-Length','0'))
                limit=1048576+2048 if re.fullmatch(r'/api/local-pilot/exams/\d+/scratch',endpoint) else MAX_BODY
                if not 0<length<=limit:raise APIError('Invalid request size',413)
                body=json.loads(self.rfile.read(length).decode())
                if not isinstance(body,dict):raise APIError('Invalid body')
                stack=[(body,0)];nodes=0
                while stack:
                    item,depth=stack.pop();nodes+=1
                    if depth>16 or nodes>(100000 if re.fullmatch(r'/api/local-pilot/exams/\d+/scratch',endpoint) else 4096):raise APIError('JSON thí điểm quá sâu hoặc quá nhiều phần tử.')
                    if isinstance(item,dict):stack.extend((v,depth+1) for v in item.values())
                    elif isinstance(item,list):stack.extend((v,depth+1) for v in item)
            result=provider.request(self,method,endpoint.removeprefix('/api/local-pilot/'),body,parse_qs(urlsplit(self.path).query))
            if '_local_binary' in result:
                self.api_headers['Content-Security-Policy']="sandbox; default-src 'none'; style-src 'none'"
                self.respond(200,result['_local_binary'],result['mime']);return
            self.json_response(200,result)
        except APIError as error:
            from .wallet_qa import QuoteChanged
            payload={'error':str(error)}
            if isinstance(error,QuoteChanged):payload.update(reconfirm=True,allocation=error.allocation)
            self.json_response(error.status,payload)
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):self.json_response(400,{'error':'Dữ liệu thí điểm không hợp lệ.'})
        except sqlite3.Error:self.json_response(503,{'error':'Chưa thể lưu dữ liệu thí điểm; gửi lại cùng yêu cầu.'})

    def platform_request(self, method, endpoint):
        self.api_headers = {}
        try:
            body = None
            if method == 'POST':
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    raise APIError('Use application/json', 415)
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    raise APIError('Invalid content length')
                limit = 262144 if endpoint.startswith('/api/staff/') else MAX_BODY
                if re.fullmatch(r'/api/v1/exams/\d+/scratch',endpoint):limit=1048576+2048
                if re.fullmatch(r'/api/v1/classes/\d+/assignments/\d+/submissions', endpoint):
                    limit = 4 * ((10 * 1024 * 1024 + 2) // 3) + 2048
                if not 0 < length <= limit:
                    raise APIError('Invalid request size', 413)
                body = json.loads(self.rfile.read(length).decode())
                if not isinstance(body, dict):
                    raise APIError('Invalid body')
            api = staff_dispatch if endpoint.startswith('/api/staff/') else dispatch
            payload, status = api(self, method, endpoint, body)
            if isinstance(payload,dict) and 'authenticated' in payload and getattr(self.server,'local_pilot',None):payload['localPilotEnabled']=True
        except APIError as error:
            self.api_headers = {}
            payload = {'error': str(error)}
            discipline = getattr(error, 'arenaDiscipline', None)
            if discipline is not None:
                payload['arenaDiscipline'] = discipline
            for key in ('gameClaim','gameConflicts'):
                if hasattr(error,key):payload[key]=getattr(error,key)
            self.json_response(error.status, payload)
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self.api_headers = {}
            self.json_response(400, {'error': 'Dữ liệu gửi lên không hợp lệ.'})
        except sqlite3.Error:
            self.api_headers = {}
            self.log_error('Database operation failed for %s', endpoint)
            self.json_response(503, {'error': 'Chưa thể lưu dữ liệu. Em hãy thử lại.'})
        else:
            if isinstance(payload, dict) and isinstance(payload.get('_binary'), bytes):
                self.api_headers['Content-Disposition'] = payload['disposition']
                self.api_headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
                self.respond(status, payload['_binary'], payload['contentType'])
            else:
                self.json_response(status, payload)
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

def main():
    parser = argparse.ArgumentParser(description="Run Mam Toan Python demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", type=Path, default=os.environ.get("MAM_TOAN_DATABASE", DEFAULT_DATABASE))
    args = parser.parse_args()
    initialize(args.database)
    initialize_catalog(args.database)
    # A cold arena page can request many CSS/JS files at once.
    # Keep local browser bursts queued instead of refusing core scripts.
    ThreadingHTTPServer.request_queue_size = 128
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.database_path = args.database
    server.review_upgrades = os.environ.get('MAM_TOAN_REVIEW_UPGRADES') == '1'
    server.arena = ARENA
    server.real_accounts = True
    server.native_python_backend = True
    server.practice_export_enabled=os.environ.get('MAM_TOAN_PRACTICE_EXPORT')=='1'
    server.practice_export_ports=frozenset(int(p) for p in os.environ.get('MAM_TOAN_PRACTICE_EXPORT_PORTS','8765').split(','))
    if any(not 1024<=p<=65535 for p in server.practice_export_ports):raise ValueError('Trusted native export external port required')
    if os.environ.get('MAM_TOAN_LOCAL_TEST_GAMES')=='1':
        from .local_test_games import NativeLocalTestGames
        ports={int(value) for value in os.environ.get('MAM_TOAN_LOCAL_TEST_GAMES_PORTS','8765').split(',')}
        server.local_test_games=NativeLocalTestGames(ports)
    if os.environ.get('MAM_TOAN_LOCAL_PILOT')=='1':
        from .local_pilot import LocalPilot
        server.local_pilot_ports={int(v) for v in os.environ.get('MAM_TOAN_LOCAL_PILOT_PORTS',str(args.port)).split(',')}
        if not server.local_pilot_ports or any(not 1024<=v<=65535 for v in server.local_pilot_ports):raise ValueError('Trusted local pilot external port required')
        server.local_pilot=LocalPilot(args.database,os.environ.get('MAM_TOAN_LOCAL_PILOT_DATABASE','/pilot/local-pilot.sqlite3'),os.environ.get('MAM_TOAN_LOCAL_PILOT_INPUTS',str(FRONTEND.parent/'pilot-inputs')),restructure_inputs=(os.environ.get('MAM_TOAN_RESTRUCTURE_INPUTS',str(FRONTEND.parent/'restructure-inputs')) if os.environ.get('MAM_TOAN_RESTRUCTURE')=='1' else None))
    server.daemon_threads = True
    print(f"Mam Toan (Python): http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
