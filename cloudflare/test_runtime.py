"""Run real local workerd integration tests with disposable synthetic data.

Prerequisites (no production credentials or Cloudflare login required):
    npm ci --ignore-scripts
    python -m pip install workers-runtime-sdk==1.9.6
    python cloudflare/build_worker.py --vendor-sdk
    python cloudflare/test_runtime.py --port 8895

The installed Node/Wrangler and vendored SDK are used without npm downloads.
All config, test secrets, Python fixture DB, local DO state and logs stay under
work/. The runner never targets port8765 or a remote Worker. NODE_BIN may
select Node; use the chosen Python to invoke this script. UV_BIN is not needed
for this SDK-only project. Evidence is retained for diagnosing failures.
"""
import argparse
import base64
import copy
import hashlib
import http.client
import http.cookiejar
import importlib.util
import json
import os
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def assert_loopback_port_available(port):
    with socket.socket() as probe:
        # Linux retains recently closed connections in TIME_WAIT after the
        # intentional workerd restart. Match Node's Unix reuse behavior while
        # still calling listen(), so an actual listener is never accepted.
        # Windows SO_REUSEADDR has different sharing semantics; leave it off.
        if os.name != 'nt':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
            probe.listen(1)
        except OSError as error:
            raise RuntimeError('QA port is already occupied; choose an unused non-production port') from error


class HTTPClient:
    def __init__(self, origin):
        self.origin, self.csrf = origin, ''
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.last_headers, self.last_status = {}, None

    def call(self, path, body=None, *, expected=200, raw=False, headers=None):
        request_headers = {'Origin': self.origin, 'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf}
        request_headers.update(headers or {})
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        request = Request(self.origin + path, data, request_headers, method='POST' if body is not None else 'GET')
        try:
            response = self.opener.open(request, timeout=90)
        except HTTPError as error:
            response = error
        with response:
            self.last_status, content = response.code, response.read()
            self.last_headers = {key.lower(): value for key, value in response.headers.items()}
        if self.last_status != expected:
            raise AssertionError('Runtime HTTP status mismatch for ' + path + ': got ' + str(self.last_status) + ', expected ' + str(expected))
        if raw:
            return content
        result = json.loads(content)
        if isinstance(result, dict) and result.get('csrf'):
            self.csrf = result['csrf']
        return result


def fixture_database(directory):
    """Build the migration source with CPython's existing real account/staff APIs."""
    from backend.arena import Arena
    from backend.database import initialize
    from backend.platform_api import academic, connect, stamp
    from backend.staff_api import create_first_admin
    from test_staff_api import StaffClient, StaffTests
    from test_platform_api import Client as StudentClient

    database = directory / 'source.sqlite3'
    initialize(database)
    from backend.platform_api import seed_catalog
    seed_catalog(database)
    admin_login, admin_password = 'runtime-admin', secrets.token_urlsafe(24)
    create_first_admin(database, admin_login, 'Quản trị kiểm thử', admin_password)
    server = SimpleNamespace(database_path=database, review_upgrades=False, arena=Arena())
    admin = StaffClient(server)
    admin.call('login', {'login': admin_login, 'password': admin_password})
    support = SimpleNamespace(admin=admin, path=database, server=server)
    teacher_client, teacher = StaffTests.teacher(support)
    group = StaffTests.classroom(support, teacher)

    def student(label, invite=''):
        client, login, password = StudentClient(server), 'runtime-' + secrets.token_hex(7), secrets.token_urlsafe(24)
        state = client.call('auth/register', {'login': login, 'password': password, 'name': label,
                     'birthYear': academic()[0] - 10, 'inviteCode': invite})
        with connect(database) as db:
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (state['account']['id'],)).fetchone()[0]
        return {'login': login, 'password': password, 'student_id': sid, 'account_id': state['account']['id']}, state

    other, other_state = student('Học sinh thử')
    tuition, _ = student('Mầm Xanh', other_state['state']['inviteCode'])
    for record in (tuition, other):
        admin.call('classes/' + str(group['id']) + '/enroll', {'action': 'enroll', 'studentId': record['student_id']})
    detail = teacher_client.call('classes/' + str(group['id']) + '/sessions', {
        'title': 'Buổi kiểm thử runtime', 'startsAt': stamp(), 'videoUrl': '', 'comment': 'Dữ liệu giả'})
    lesson_id = detail['sessions'][0]['id']
    detail = teacher_client.call('sessions/' + str(lesson_id) + '/assignments', {
        'title': 'Bài nộp kiểm thử', 'kind': 'Bài tập về nhà', 'documentUrl': ''})
    assignment_id = detail['sessions'][0]['assignments'][0]['id']
    local = datetime.now(timezone(timedelta(hours=7)))
    month = local.strftime('%Y-%m')
    next_month = (local.replace(day=1) + timedelta(days=32)).strftime('%Y-%m')
    fee_ids = []
    for record, period in ((tuition, month), (other, month), (tuition, next_month)):
        detail = admin.call('classes/' + str(group['id']))
        detail = admin.call('classes/' + str(group['id']) + '/fees', {
            'revision': detail['class']['revision'], 'studentId': record['student_id'], 'month': period, 'amount': 100000})
        fee_ids.append(next(fee['id'] for fee in detail['fees'] if fee['student_id'] == record['student_id'] and fee['month'] == period))

    legacy_content = b'%PDF-1.4\nLegacy inline synthetic fixture\n%%EOF'
    with connect(database, True) as db:
        legacy_id = db.execute('INSERT INTO class_submissions(assignment_id,student_id,filename,mime_type,size,content,digest,submitted_at) VALUES (?,?,?,?,?,?,?,?)',
                              (assignment_id, tuition['student_id'], 'legacy.pdf', 'application/pdf', len(legacy_content),
                               legacy_content, hashlib.sha256(legacy_content).hexdigest(), stamp())).lastrowid
    result = {'admin': {'login': admin_login, 'password': admin_password}, 'tuition': tuition, 'other': other,
              'class_id': group['id'], 'assignment_id': assignment_id, 'legacy_id': legacy_id,
              'classId': group['id'], 'feeOwner': tuition, 'feeOther': other,
              'feeId': fee_ids[0], 'otherFeeId': fee_ids[1], 'nextFeeId': fee_ids[2]}
    return database, result, legacy_content


def transfer_payload(source, directory):
    spec = importlib.util.spec_from_file_location('runtime_transfer_tool', ROOT / 'scripts' / 'cloudflare-data.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload, _ = module.prepare(source, directory / 'fixture-transfer.json')
    return payload, module


class LocalWorker:
    def __init__(self, directory, port, operator_token, webhook_secret):
        self.directory, self.port = directory, port
        self.origin = 'http://127.0.0.1:' + str(port)
        self.project = directory / 'worker-project'
        self.project.mkdir()
        source = ROOT / 'cloudflare'
        if not (source / 'runtime' / 'backend_worker.py').is_file() or not (source / 'python_modules' / 'workers').is_dir():
            raise RuntimeError('Stage the pinned SDK and Worker first: python cloudflare/build_worker.py --vendor-sdk')
        shutil.copytree(source / 'runtime', self.project / 'runtime', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(source / 'python_modules', self.project / 'python_modules', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        config = json.loads((source / 'wrangler.jsonc').read_text(encoding='utf-8'))
        config.pop('build', None)
        config.pop('env', None)
        config['name'] = 'fivebmath-isolated-runtime-qa'
        config['vars'] = {'PUBLIC_ORIGIN': self.origin, 'TENANT_KEY': 'runtime-qa', 'TRANSFER_ENABLED': 'true'}
        config['dev'] = {'ip': '127.0.0.1', 'port': port, 'inspector_port': port + 500}
        (self.project / 'wrangler.jsonc').write_text(json.dumps(config), encoding='utf-8')
        values = {'PUBLIC_ORIGIN': self.origin, 'TENANT_KEY': 'runtime-qa', 'TRANSFER_ENABLED': 'true',
                  'OPERATOR_TOKEN': operator_token, 'MAM_TOAN_BANK_ID': 'ACB',
                  'MAM_TOAN_BANK_ACCOUNT': '900000000001', 'MAM_TOAN_BANK_NAME': 'TAI KHOAN GIA CHI DUNG QA',
                  'MAM_TOAN_SEPAY_ENABLED': '1', 'MAM_TOAN_SEPAY_WEBHOOK_SECRET': webhook_secret}
        secrets_file = self.project / '.dev.vars'
        secrets_file.write_text(''.join(key + '=' + json.dumps(value) + '\n' for key, value in values.items()), encoding='utf-8')
        secrets_file.chmod(0o600)
        self.environment = dict(os.environ)
        for key in ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_API_KEY', 'CLOUDFLARE_API_EMAIL', 'CLOUDFLARE_ACCOUNT_ID',
                    'CF_API_TOKEN', 'CF_API_KEY', 'CF_API_EMAIL'):
            self.environment.pop(key, None)
        for key in ('TEMP', 'TMP', 'TMPDIR', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'UV_CACHE_DIR', 'UV_PROJECT_ENVIRONMENT'):
            folder = directory / key.lower()
            folder.mkdir(exist_ok=True)
            self.environment[key] = str(folder)
        self.environment.update({'WRANGLER_SEND_METRICS': 'false', 'CI': 'true', 'NO_COLOR': '1',
                                 'WRANGLER_LOG_PATH': str(directory / 'wrangler-debug.log')})
        self.process, self.log = None, None
        self.starts = 0

    def start(self):
        assert_loopback_port_available(self.port)
        self.starts += 1
        self.log = (self.directory / ('worker-' + str(self.starts) + '.log')).open('wb')
        node = os.environ.get('NODE_BIN') or shutil.which('node')
        cli = ROOT / 'node_modules' / 'wrangler' / 'bin' / 'wrangler.js'
        if not node or not cli.is_file():
            raise RuntimeError('Install the locked root npm dependencies before runtime QA')
        command = [node, str(cli), 'dev', '--config', str(self.project / 'wrangler.jsonc'), '--local',
                   '--port', str(self.port), '--inspector-port', str(self.port + 500),
                   '--persist-to', str(self.directory / 'do-state'), '--show-interactive-dev-session', 'false',
                   '--log-level', 'warn']
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        self.process = subprocess.Popen(command, cwd=ROOT, env=self.environment, stdout=self.log, stderr=subprocess.STDOUT, **flags)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError('Local Wrangler stopped before becoming ready; see the retained Worker log')
            try:
                return HTTPClient(self.origin).call('/api/health')
            except (URLError, OSError, TimeoutError, http.client.HTTPException):
                time.sleep(0.25)
        raise RuntimeError('Local Worker startup timed out; see the retained Worker log')

    def stop(self):
        if self.process and self.process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    self.process.kill()
                else:
                    os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=10)
        if self.log:
            self.log.close()
        self.process, self.log = None, None


def student_login(origin, credentials):
    client = HTTPClient(origin)
    state = client.call('/api/v1/auth/login', {'login': credentials['login'], 'password': credentials['password']})
    assert state['account']['id'] == credentials['account_id'], 'Imported CPython credential restored the wrong owner'
    return client, state


def chunked_limit(origin):
    connection = http.client.HTTPConnection('127.0.0.1', int(origin.rsplit(':', 1)[1]), timeout=20)
    try:
        connection.request('POST', '/api/grade', body=iter([b'{"kind":"exam","padding":"', b'x' * 20000, b'"}']),
                           headers={'Content-Type': 'application/json', 'Origin': origin}, encode_chunked=True)
        response = connection.getresponse()
        response.read()
        assert response.status == 413, 'Chunked oversized request was not rejected'
    finally:
        connection.close()


def run(port):
    if not 1024 <= port <= 64000 or port == 8765:
        raise ValueError('Choose a dedicated QA port between1024 and64000, excluding8765')
    work = ROOT / 'work'
    work.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='worker-runtime-qa-', dir=work))
    report = {'scope': 'Actual local workerd, isolated CPython fixture and DO storage; no production resources.',
              'status': 'running', 'checks': []}
    worker = None
    try:
        print('Runtime QA: preparing isolated fixture', flush=True)
        source, fixture, legacy = fixture_database(directory)
        payload, transfer_tool = transfer_payload(source, directory)
        operator_token, webhook_secret = secrets.token_urlsafe(36), secrets.token_urlsafe(40)
        worker = LocalWorker(directory, port, operator_token, webhook_secret)
        health = worker.start()
        assert health['ready'] is False, 'Synthetic import gate must be enabled before any normal API request'
        origin = worker.origin
        operator = HTTPClient(origin)
        auth = {'Authorization': 'Bearer ' + operator_token}
        anonymous = HTTPClient(origin)
        anonymous.call('/__ops/status', expected=404)
        anonymous.call('/__ops/import', payload, expected=404)
        anonymous.call('/api/v1/session', expected=503)
        corrupted = copy.deepcopy(payload)
        first_table = next(iter(corrupted['source']['tables']))
        corrupted['source']['tables'][first_table] += 1
        corrupted['transferSha256'] = transfer_tool.checksum(corrupted)
        operator.call('/__ops/import', corrupted, headers=auth, expected=409)
        assert operator.call('/__ops/status', headers=auth)['tables'] == {}, 'Failed import leaked partial schema or rows'
        imported = operator.call('/__ops/import', payload, headers=auth)
        assert imported['imported'] is True
        operator.call('/__ops/import', payload, headers=auth, expected=409)
        exported = operator.call('/__ops/export', headers=auth)
        transfer_tool.validate(exported)
        assert exported['source']['kind'] == 'cloudflare'
        assert exported['source']['bookmark'] is None or isinstance(exported['source']['bookmark'], str)
        report['checks'].append('Empty-DO operator import preserves CPython data; malformed transfer rolls back all schema/rows; unauthorized routes404, pending API503, reimport409, export protocol valid.')

        print('Runtime QA: real authentication, ownership and assessment', flush=True)
        student, state = student_login(origin, fixture['tuition'])
        other, _ = student_login(origin, fixture['other'])
        assert state['account']['membership'] == 'SVip'
        student.call('/api/v1/profile', {'name': 'Mầm Xanh'}, headers={'Origin': 'https://wrong-origin.invalid'}, expected=403)
        student.call('/api/v1/profile', {'name': 'Mầm Xanh'}, headers={'X-CSRF-Token': 'invalid-fixture'}, expected=403)
        student.call('/api/v1/profile', {'name': 'Mầm Xanh'})
        complete = student.call('/api/v1/lessons/public-decimal/complete', {})
        assert complete['state']['completed']['public-decimal']
        assert student.call('/api/v1/session')['state']['completed']['public-decimal']
        assert not other.call('/api/v1/session')['state']['completed'].get('public-decimal')
        registered_client = HTTPClient(origin)
        from backend.platform_api import academic
        registered = registered_client.call('/api/v1/auth/register', {
            'login': 'runtime-created-' + secrets.token_hex(7), 'password': secrets.token_urlsafe(24),
            'name': 'Học sinh thử', 'birthYear': academic()[0] - 10})
        assert registered['authenticated']
        exam = student.call('/api/v1/exams', {'topic': 'decimal', 'count': 3, 'requestKey': secrets.token_hex(12)})['exam']
        assert len(exam['questions']) == 3
        assert all('answer' not in question and 'solution' not in question for question in exam['questions'])
        other.call('/api/v1/exams/' + str(exam['id']), expected=404)
        student.call('/api/v1/exams/' + str(exam['id']) + '/answers', {'position': 1, 'answer': exam['questions'][0]['options'][0]})
        result = student.call('/api/v1/exams/' + str(exam['id']) + '/submit', {})['exam']
        assert result['submittedAt'] and 0 <= result['score'] <= 10
        assert result['questions'][0]['solution']
        grade = anonymous.call('/api/grade', {'kind': 'exam', 'answers': ['<', '7/8', '36', '162', '247500']})
        assert grade['score'] == 10
        anonymous.call('/api/grade', b'{' + b'x' * 20000 + b'}', expected=413)
        anonymous.call('/api/v1/auth/register', b'{' + b'x' * 20000 + b'}', expected=413)
        chunked_limit(origin)
        report['checks'].append('CPython password login, 600k-compatible registration, Origin/CSRF rejection, owner completion/readback, private exam submit and public grading work.')
        report['checks'].append('Oversized declared and chunked bodies return413 without ordinary application writes.')

        print('Runtime QA: signed financial transactions', flush=True)
        from runtime_financial_qa import run_financial_qa
        report['financial'] = run_financial_qa(origin, fixture, webhook_secret)
        assert all(report['financial'].values())
        report['checks'].append('Synthetic signed SePay flows: first VIP, exactly-once referral, renewal, tuition owner/month, duplicate/conflict behavior.')

        print('Runtime QA: long Unicode admin searches', flush=True)
        admin = HTTPClient(origin)
        admin.call('/api/staff/login', fixture['admin'])
        search = 'Nguyễn Trường Khánh Vân Ánh Dương Minh Ngọc _%'
        assert len(search.encode('utf-8')) > 50
        for route, query in [
            ('accounts', {'q': search}),
            ('content', {'kind': 'questions', 'q': search}),
            ('payments', {'q': search, 'referrer': search}),
            ('payment-receipts', {'q': search}),
            ('admissions', {'q': search}),
        ]:
            matches = admin.call('/api/staff/' + route + '?' + urlencode(query))
            assert matches['total'] == 0 and not matches['rows'], 'Long Unicode search returned unrelated rows'
        report['checks'].append('Five actual admin searches accept long Unicode and literal wildcard characters without SQLite LIKE-limit errors.')

        print('Runtime QA: private10MB file and restart persistence', flush=True)
        assert student.call('/api/v1/class-submissions/' + str(fixture['legacy_id']) + '/file', raw=True) == legacy
        prefix = b'%PDF-1.7\nSynthetic runtime10MB\n'
        content = prefix + b'X' * (10 * 1024 * 1024 - len(prefix))
        upload_body = {'filename': 'runtime.pdf', 'mimeType': 'application/pdf', 'data': base64.b64encode(content).decode('ascii')}
        upload_path = '/api/v1/classes/' + str(fixture['class_id']) + '/assignments/' + str(fixture['assignment_id']) + '/submissions'
        submission = student.call(upload_path, upload_body)['submission']
        assert student.call(upload_path, upload_body)['submission']['id'] == submission['id']
        file_path = '/api/v1/class-submissions/' + str(submission['id']) + '/file'
        assert student.call(file_path, raw=True) == content
        assert student.last_headers.get('content-type', '').startswith('application/pdf')
        assert student.last_headers.get('cache-control') == 'no-store'
        other.call(file_path, expected=403)
        print('Runtime QA: active Arena room and answer-history persistence', flush=True)
        room = student.call('/api/v1/arena', {'action': 'create', 'public': True, 'scope': 'weekly'})
        room_credentials = {key: room[key] for key in ('code', 'token')}
        joined = other.call('/api/v1/arena', {'action': 'join', 'code': room['code']})
        other_credentials = {key: joined[key] for key in ('code', 'token')}
        student.call('/api/v1/arena', {'action': 'accept', **room_credentials})
        time.sleep(3.2)
        battle = student.call('/api/v1/arena', {'action': 'state', **room_credentials})['battle']
        question = battle['questions'][battle['index']]
        # Deliberately choose a wrong valid option from the trusted source QA DB,
        # so the round stays open rather than randomly advancing before restart.
        with sqlite3.connect(source) as fixture_db:
            correct = str(json.loads(fixture_db.execute('SELECT grading_rule_json FROM question_versions WHERE id=?',
                                                       (question['questionVersionId'],)).fetchone()[0])['answer'])
        selected = next(option for option in question['options'] if option != correct)
        answered = student.call('/api/v1/arena', {'action': 'answer', **room_credentials,
                                                'index': battle['index'], 'answer': selected})['battle']
        assert answered['answer'] == selected and not answered['resolved']
        other.call('/api/v1/arena', {'action': 'state', **other_credentials})
        owner = state['account']['id']
        worker.stop()
        worker.start()
        resumed, resumed_state = student_login(origin, fixture['tuition'])
        assert resumed_state['account']['id'] == owner
        assert resumed_state['state']['completed']['public-decimal']
        assert resumed.call('/api/v1/exams/' + str(exam['id']))['exam']['submittedAt']
        assert resumed.call(file_path, raw=True) == content
        assert resumed.call('/api/v1/class-submissions/' + str(fixture['legacy_id']) + '/file', raw=True) == legacy
        restored = resumed.call('/api/v1/arena', {'action': 'state', **room_credentials})['battle']
        assert restored['id'] == battle['id'] and restored['index'] == battle['index']
        assert restored['answer'] == selected, 'Current Arena answer was lost after restart'
        assert other.call('/api/v1/arena', {'action': 'state', **other_credentials})['battle']['id'] == battle['id']
        left = resumed.call('/api/v1/arena', {'action': 'leave', **room_credentials})['result']
        assert left['review'][battle['index']]['myAnswer'] == selected, 'Arena integer-keyed answer history was lost after JSON restore'
        other.call('/api/v1/arena', {'action': 'leave', **other_credentials})
        report['checks'].append('Legacy inline and10MB chunked private files roundtrip, duplicate upload is idempotent, wrong owner403; account/progress/exam/file survive actual workerd restart.')
        report['checks'].append('Active two-player Arena room, both member tokens, current answer and final review history survive actual workerd restart.')
        report['status'] = 'passed'
        print(json.dumps({'status': 'passed', 'checks': report['checks'], 'financial': report['financial'],
                          'evidence': str(directory.relative_to(ROOT))}, ensure_ascii=False), flush=True)
        return 0
    except BaseException as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__, 'error': str(error),
                          'evidence': str(directory.relative_to(ROOT))}, ensure_ascii=False), flush=True)
        return 1
    finally:
        if worker:
            worker.stop()
        (directory / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8895, help='Dedicated loopback QA port, never8765 (default8895)')
    raise SystemExit(run(parser.parse_args().port))
