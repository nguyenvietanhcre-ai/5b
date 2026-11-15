"""Loopback API-only QA. Run with --enable-pilot and a NEW synthetic SQLite path."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

from backend.arena import Arena
from backend.free_vip_pilot import PilotConfig
from backend.server import Handler, ThreadingHTTPServer
from scripts.free_vip_fixture import initialize_qa


class QAHandler(Handler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/health' or path.startswith('/api/v1/'):
            return super().do_GET()
        self.json_response(404, {'error':'QA API only; no public assets or media.'})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path.startswith('/api/v1/') and not path.startswith(('/api/v1/payments','/api/v1/dev/','/api/v1/admissions')):
            return super().do_POST()
        self.json_response(403, {'error':'Payments, staff, webhooks and legacy anonymous APIs disabled on QA.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18931)
    parser.add_argument('--enable-pilot', action='store_true')
    args = parser.parse_args()
    if not args.enable_pilot:
        parser.error('Explicit --enable-pilot required; ordinary backend remains unchanged.')
    if args.port == 8765:
        parser.error('Never use the main service port.')
    # Bind/check availability BEFORE creating the database; failure cannot disturb an existing listener.
    server = ThreadingHTTPServer(('127.0.0.1', args.port), QAHandler)
    server.student_cookie_name=f'5bmath_qa_{server.server_port}_session'
    try:
        server.database_path = initialize_qa(args.database)
        server.free_vip_pilot = PilotConfig()
        server.review_upgrades = False
        server.real_accounts = True
        server.arena = Arena()
        print(f'QA synthetic API http://127.0.0.1:{server.server_port}; DB={server.database_path}', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
