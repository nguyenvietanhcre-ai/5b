"""Dependency-free HTTP demo; explicitly serve frontend assets only."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .content import grade

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
ASSETS = {"/": "index.html", "/index.html": "index.html",
          "/styles.css": "styles.css", "/app.js": "app.js",
          "/5bmath-logo.svg": "5bmath-logo.svg", "/5bmath-icon.svg": "5bmath-icon.svg"}
PAGES = {
    "/bai-hoc-toan-lop-5/": "courses",
    "/so-sanh-so-thap-phan/": "lesson-decimal",
    "/hai-lan-thay-doi-phan-tram/": "lesson-percent",
    "/luyen-tap-so-thap-phan/": "practice",
    "/de-thi-thu-toan-vao-lop-6/": "exam",
    "/tro-choi-xep-so-thap-phan/": "game",
    "/goc-hoc-tap/": "dashboard",
}
MAX_BODY = 16384

class Handler(BaseHTTPRequestHandler):
    server_version = "MamToan"
    def respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
    def json_response(self, status, payload):
        self.respond(status, json.dumps(payload, ensure_ascii=False).encode(),
                     "application/json; charset=utf-8")
    def do_GET(self):
        url = urlsplit(self.path)
        route = unquote(url.path)
        if route == "/api/health":
            self.json_response(200, {"status": "ok", "backend": "python", "mode": "demo"})
        elif route in ASSETS or route in PAGES:
            page = PAGES.get(route)
            file = FRONTEND / ("index.html" if page else ASSETS[route])
            try:
                mime = {".js":"text/javascript", ".css":"text/css", ".html":"text/html",
                        ".svg":"image/svg+xml"}[file.suffix]
                body = file.read_bytes()
                if page:
                    body = body.replace(b'<html lang="vi"', f'<html lang="vi" data-page="{page}"'.encode(), 1)
                    body = body.replace(b"<head>", b'<head>\n    <base href="../">', 1)
                    if page == "dashboard":
                        body = body.replace(b"</head>", b'    <meta name="robots" content="noindex">\n</head>', 1)
                self.respond(200, body, mime + "; charset=utf-8")
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
        if urlsplit(self.path).path != "/api/grade":
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
            if not isinstance(body, dict) or not isinstance(body.get("kind"), str):
                raise ValueError("Invalid body")
            result = grade(body["kind"], body.get("answers"))
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self.json_response(400, {"error":"Invalid quiz or answers"})
            return
        self.json_response(200, result)
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

def main():
    parser = argparse.ArgumentParser(description="Run Mam Toan Python demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
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
