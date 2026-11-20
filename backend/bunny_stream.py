"""Private Bunny Stream registry, upload credentials, and per-learner playback."""
from dataclasses import dataclass, field
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import unquote, urlencode, urlsplit

from . import platform_api as api


STAFF_PREFIX = '/api/staff/bunny-stream'
LEARNER_PREFIX = '/api/v1/lesson-videos'
API_HOST = 'video.bunnycdn.com'
TUS_ENDPOINT = f'https://{API_HOST}/tusupload'
PLAYER = 'https://player.mediadelivery.net/embed'
CONFIG_PATH = '/run/5bmath/bunny-stream.json'
MAX_CONFIG_BYTES = 16 * 1024
MAX_UPSTREAM_BYTES = 256 * 1024
MAX_UPLOAD_BYTES = 1024 ** 3
DEFAULT_MAX_VIDEOS = 10
TUS_TTL = 3600
PLAYBACK_TTL = 3600
GUID = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}')
UPLOAD_ID = re.compile(r'[0-9a-f]{32}')
REQUEST_KEY = re.compile(r'[A-Za-z0-9_-]{16,100}')
LESSON_KEY = re.compile(r'[A-Za-z0-9._-]{1,120}')


def error(message, status, code):
    result = api.APIError(message, status)
    result.code = code
    return result


def upstream_error():
    return error('Chưa thể xác nhận video với Bunny Stream. Hãy thử lại.', 502, 'bunny_upstream')


def not_found():
    return error('Không tìm thấy video thuộc bài học này.', 404, 'video_not_found')


def not_ready():
    return error('Video chưa xử lý xong. Hãy kiểm tra trạng thái rồi thử lại.', 409, 'bunny_video_not_ready')


@dataclass(frozen=True)
class Config:
    library_id: int = 0
    api_key: str = field(default='', repr=False)
    token_key: str = field(default='', repr=False)
    max_videos: int = DEFAULT_MAX_VIDEOS
    missing: tuple = ()
    source: str = 'file'

    def public(self):
        return {'configured': not self.missing, 'missing': list(self.missing),
                'configSource': self.source, 'maxVideos': self.max_videos,
                'maxUploadBytes': MAX_UPLOAD_BYTES}

    def require(self):
        if self.missing:
            raise error('Bunny Stream chưa được cấu hình trên máy chủ.', 503, 'bunny_unconfigured')
        return self


def read_config():
    path = Path(os.environ.get('BUNNY_STREAM_CONFIG_FILE') or CONFIG_PATH)
    try:
        configured=os.environ.get('BUNNY_STREAM_CONFIG_JSON')
        if configured is not None:data=configured.encode('utf-8')
        else:
            with path.open('rb') as file:
                data = file.read(MAX_CONFIG_BYTES + 1)
        value = json.loads(data) if len(data) <= MAX_CONFIG_BYTES else None
    except FileNotFoundError:
        return Config(missing=('enabled', 'libraryId', 'apiKey', 'tokenKey'), source='missing')
    except (OSError, ValueError, RecursionError):
        return Config(missing=('config',))
    if not isinstance(value, dict):
        return Config(missing=('config',))
    library = value.get('libraryId')
    if isinstance(library, str) and re.fullmatch(r'[1-9][0-9]{0,18}', library):
        library = int(library)
    limit = value.get('maxVideos', DEFAULT_MAX_VIDEOS)
    api_key, token_key = value.get('apiKey'), value.get('tokenKey')
    valid = {'enabled': value.get('enabled') is True,
             'libraryId': type(library) is int and 0 < library < 2 ** 63,
             'apiKey': isinstance(api_key, str) and bool(re.fullmatch(r'[!-~]{1,512}', api_key)),
             'tokenKey': isinstance(token_key, str) and bool(re.fullmatch(r'[!-~]{1,512}', token_key)),
             'maxVideos': type(limit) is int and 1 <= limit <= 100}
    return Config(library if valid['libraryId'] else 0,
                  api_key if valid['apiKey'] else '',
                  token_key if valid['tokenKey'] else '',
                  limit if valid['maxVideos'] else DEFAULT_MAX_VIDEOS,
                  tuple(name for name, ok in valid.items() if not ok))


class _ProviderRejection(Exception):
    """A known create rejection with no remote reservation."""


def _https_request(method, path, api_key, payload):
    # Direct HTTPS prevents credential forwarding through redirects or proxy
    # environment variables. The request path comes from validated numeric IDs
    # and the registry, never from a supplied URL.
    connection = http.client.HTTPSConnection(API_HOST, timeout=5)
    headers = {'AccessKey': api_key, 'Accept': 'application/json'}
    raw = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        raw = api.packed(payload).encode('utf-8')
    try:
        connection.request(method, path, body=raw, headers=headers)
        with connection.getresponse() as response:
            if method == 'POST' and response.status in (400, 401, 403, 404):
                raise _ProviderRejection()
            if response.status != 200:
                raise upstream_error()
            data = response.read(MAX_UPSTREAM_BYTES + 1)
    finally:
        connection.close()
    if len(data) > MAX_UPSTREAM_BYTES:
        raise upstream_error()
    return json.loads(data)


def _request(server, config, method, path, payload=None):
    # Tests may replace transport on their own server object.
    transport = getattr(server, 'bunny_stream_transport', _https_request)
    try:
        value = transport(method, path, config.api_key, payload)
    except api.APIError:
        raise
    except (OSError, http.client.HTTPException, ValueError, RecursionError):
        raise upstream_error() from None
    if not isinstance(value, dict):
        raise upstream_error()
    return value


def _video_path(config, guid=None):
    path = f'/library/{config.library_id}/videos'
    return f'{path}/{guid}' if guid else path


def _video_guid(config, data):
    guid = data.get('guid')
    if (type(data.get('videoLibraryId')) is not int or data['videoLibraryId'] != config.library_id
            or not isinstance(guid, str) or not GUID.fullmatch(guid.lower())):
        raise upstream_error()
    return guid.lower()


def _binding(body):
    provider, key = body.get('provider'), body.get('lessonKey')
    if provider not in ('main', 'native') or not isinstance(key, str) or not LESSON_KEY.fullmatch(key):
        raise api.APIError('Nguồn hoặc mã bài học không hợp lệ.')
    return provider, key


def _upload_id(value):
    if not isinstance(value, str) or not UPLOAD_ID.fullmatch(value):
        raise api.APIError('Mã upload video không hợp lệ.')
    return value


def _check_lesson(server, db, provider, key):
    if provider == 'main':
        row = db.execute('SELECT 1 FROM lessons WHERE client_key=?', (key,)).fetchone()
    else:
        pilot = getattr(server, 'local_pilot', None)
        if not pilot or not pilot.knowledge:
            raise not_found()
        with api.connect(pilot.path) as native:
            row = native.execute('SELECT 1 FROM knowledge_lessons WHERE lesson_key=?', (key,)).fetchone()
    if not row:
        raise not_found()


def registered(db, identity, provider=None, key=None):
    row = db.execute('SELECT * FROM bunny_stream_uploads WHERE id=? AND video_guid IS NOT NULL', (identity,)).fetchone()
    if not row or (provider is not None and (row['provider'] != provider or row['lesson_key'] != key)):
        raise not_found()
    return row


def check_library(row, config):
    if row['library_id'] != config.library_id:
        raise not_found()


def _upload(row):
    return {'id': row['id'], 'provider': row['provider'], 'lessonKey': row['lesson_key'],
            'status': row['state'], 'size': row['declared_size'], 'durationSeconds': row['duration_seconds']}


def _upload_credentials(row, config):
    result = {'upload': _upload(row)}
    if row['state'] == 'uploading':
        expires = int(time.time()) + TUS_TTL
        library, guid = str(config.library_id), row['video_guid']
        digest = hashlib.sha256(f'{library}{config.api_key}{expires}{guid}'.encode()).hexdigest()
        result['tus'] = {'endpoint': TUS_ENDPOINT, 'expiresAt': expires, 'headers': {
            'AuthorizationSignature': digest, 'AuthorizationExpire': str(expires),
            'VideoId': guid, 'LibraryId': library,
        }}
    return result


def _recover_creation(server, config, title):
    query = urlencode({'search': title, 'itemsPerPage': 10})
    page = _request(server, config, 'GET', f'{_video_path(config)}?{query}')
    items = page.get('items')
    if not isinstance(items, list):
        raise upstream_error()
    matches = [item for item in items if isinstance(item, dict) and item.get('title') == title]
    if len(matches) != 1:
        raise upstream_error()
    return matches[0]


def create_upload(server, db, user, body, config):
    lifecycle=getattr(server,'bunny_upload_lifecycle',lambda *_:None)
    lifecycle('check',None)
    if set(body) != {'provider', 'lessonKey', 'requestKey', 'size'}:
        raise api.APIError('Dữ liệu tạo upload video không hợp lệ.')
    provider, key = _binding(body)
    request_key, size = body['requestKey'], body['size']
    if not isinstance(request_key, str) or not REQUEST_KEY.fullmatch(request_key):
        raise api.APIError('Mã yêu cầu upload không hợp lệ.')
    if type(size) is not int or not 1 <= size <= MAX_UPLOAD_BYTES:
        raise api.APIError('Dung lượng video phải từ 1 byte đến 1 GiB.')
    _check_lesson(server, db, provider, key)
    old = db.execute('SELECT * FROM bunny_stream_uploads WHERE staff_id=? AND request_key=?',
                     (user['id'], request_key)).fetchone()
    if old:
        if (provider, key, size, config.library_id) != (old['provider'], old['lesson_key'], old['declared_size'], old['library_id']):
            raise error('Mã yêu cầu đã dùng cho một video khác.', 409, 'bunny_upload_conflict')
        if old['video_guid'] is not None:
            return _upload_credentials(refresh_upload(server, db, old, config), config)
        identity = old['id']
    else:
        count = db.execute('SELECT count(*) FROM bunny_stream_uploads').fetchone()[0]
        if count >= config.max_videos:
            raise error('Đã hết chỗ video Bunny Stream trong đợt thí điểm.', 409, 'bunny_video_limit')
        identity = secrets.token_hex(16)
        db.execute("INSERT INTO bunny_stream_uploads(id,staff_id,request_key,provider,lesson_key,library_id,state,declared_size,updated_at) "
                   "VALUES(?,?,?,?,?,?,'creating',?,?)",
                   (identity, user['id'], request_key, provider, key, config.library_id, size, api.stamp()))
        lifecycle('reserved',identity)

    # Persist the reservation before making a non-idempotent remote request.
    # An uncertain response is reconciled by its opaque title on retry.
    if not old or not getattr(server,'bunny_upload_lifecycle',None):db.commit()
    title = f'5BMath {identity}'
    try:
        data = (_recover_creation(server, config, title) if old and not lifecycle('reserved_here',identity) else
                _request(server, config, 'POST', _video_path(config), {'title': title}))
    except _ProviderRejection:
        db.execute("DELETE FROM bunny_stream_uploads WHERE id=? AND state='creating'", (identity,))
        lifecycle('rejected',identity)
        db.commit()
        raise upstream_error() from None
    guid = _video_guid(config, data)
    db.execute('BEGIN IMMEDIATE')
    occupied = db.execute('SELECT id FROM bunny_stream_uploads WHERE library_id=? AND video_guid=?',
                          (config.library_id, guid)).fetchone()
    if occupied and occupied['id'] != identity:
        raise upstream_error()
    db.execute("UPDATE bunny_stream_uploads SET video_guid=?,state='uploading',updated_at=? WHERE id=? AND state='creating'",
               (guid, api.stamp(), identity))
    row = registered(db, identity)
    if row['video_guid'] != guid:
        raise upstream_error()
    return _upload_credentials(row, config)


def encoded_output(data):
    """Interpret complete or playable-resolution metadata from Bunny."""
    status, duration, size = data.get('status'), data.get('length'), data.get('storageSize')
    progress = data.get('encodeProgress', 100 if status == 3 else 0)
    minimum_duration = 1 if status == 3 else 0
    if (type(status) is not int or status not in (3, 4) or
            type(duration) is not int or not minimum_duration <= duration < 2 ** 31 or
            type(size) is not int or not 0 <= size < 2 ** 63 or
            type(progress) is not int or not 0 <= progress <= 100):
        raise upstream_error()
    # Bunny can report "finished" before progress and storage converge. A
    # playable resolution needs explicit 100% before it can be published here.
    state = 'ready' if duration > 0 and size > 0 and progress == 100 else 'processing'
    return state, duration, size


def refresh_upload(server, db, row, config):
    check_library(row, config)
    data = _request(server, config, 'GET', _video_path(config, row['video_guid']))
    if _video_guid(config, data) != row['video_guid']:
        raise upstream_error()
    status = data.get('status')
    if type(status) is not int:
        raise upstream_error()
    if status in (3, 4):
        state, duration, size = encoded_output(data)
    elif status in (0, 6):
        state, duration, size = ('uploading' if row['state'] == 'uploading' else 'processing'), 0, 0
    elif status in (1, 2, 7):
        state, duration, size = 'processing', 0, 0
    elif status in (5, 8, 32):
        state, duration, size = 'failed', 0, 0
    else:
        raise upstream_error()
    db.execute('UPDATE bunny_stream_uploads SET state=?,duration_seconds=?,storage_bytes=?,updated_at=? WHERE id=?',
               (state, duration, size, api.stamp(), row['id']))
    return registered(db, row['id'])


def staff_dispatch(server, db, user, method, path, body):
    if path == f'{STAFF_PREFIX}/config' and method == 'GET':
        return read_config().public()
    if path == f'{STAFF_PREFIX}/uploads' and method == 'POST':
        return create_upload(server, db, user, body, read_config().require())
    action = re.fullmatch(STAFF_PREFIX + r'/uploads/([0-9a-f]{32})/(renew|refresh|preview)', path)
    if not action or method != 'POST':
        raise not_found()
    if body:
        raise api.APIError('Thao tác video chỉ nhận mã upload đã đăng ký.')
    row = registered(db, action[1])
    if row['staff_id'] != user['id']:
        raise not_found()
    _check_lesson(server, db, row['provider'], row['lesson_key'])
    config = read_config().require()
    row = refresh_upload(server, db, row, config)
    if action[2] == 'renew':
        return _upload_credentials(row, config)
    if action[2] == 'preview':
        return {'playback': playback(row, config)}
    return {'upload': _upload(row)}


def guarded_legacy_url(url, previous):
    if not url or url == previous:
        return
    parsed = urlsplit(url)
    host = unquote(parsed.hostname or '').rstrip('.').lower()
    first = unquote(parsed.path).lstrip('/').split('/', 1)[0].lower()
    if (host in (API_HOST, 'player.mediadelivery.net', 'iframe.mediadelivery.net')
            or (host.endswith('.b-cdn.net') and GUID.fullmatch(first))):
        raise api.APIError('Hãy gắn video Bunny Stream bằng mục tải video.')


def require_ready(row):
    if row['state'] != 'ready' or row['duration_seconds'] <= 0:
        raise not_ready()


def playback(row, config, position=0):
    check_library(row, config)
    require_ready(row)
    expires = int(time.time()) + PLAYBACK_TTL
    guid = row['video_guid']
    digest = hashlib.sha256(f'{config.token_key}{guid}{expires}'.encode()).hexdigest()
    params = urlencode({'token': digest, 'expires': expires, 'autoplay': 'false',
                        'rememberPosition': 'false', 'rememberSettings': 'false'})
    return {'embedUrl': f'{PLAYER}/{config.library_id}/{guid}?{params}', 'expiresAt': expires,
            'durationSeconds': row['duration_seconds'], 'positionSeconds': position}


def _published_native(server, key, revision, grade):
    pilot = getattr(server, 'local_pilot', None)
    if grade != 5 or not pilot or not pilot.knowledge:
        raise not_found()
    with api.connect(pilot.path) as native:
        if native.execute('SELECT 1 FROM staff_knowledge_drafts WHERE lesson_key=? AND archived=1',
                          (key,)).fetchone():
            raise not_found()
        row = native.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=?',
                             (key, revision)).fetchone()
        if not row:
            raise not_found()
        return json.loads(row[0])


def learner_video(handler, db, session, action, body):
    from .system_settings import require_feature
    from .lesson_resources import bunny_reference
    require_feature(db, 'learning_open')
    expected = {'provider', 'lessonKey', 'revision'} | ({'positionSeconds'} if action == 'progress' else set())
    if set(body) != expected or type(body.get('revision')) is not int or not 1 <= body['revision'] <= 999999999:
        raise api.APIError('Mã hoặc phiên bản bài học không hợp lệ.')
    provider, key = _binding(body)
    revision = body['revision']
    grade = api.grade_for_student(db, session['student_id'], session['birth_year'])
    if provider == 'main':
        from .content_retirement import retired
        from .free_vip_pilot import guard
        guard(handler, db, session, '/api/v1/lessons/video')
        if retired(db, grade):
            raise not_found()
        lesson = db.execute("SELECT presentation_json FROM lessons WHERE client_key=? AND revision=? AND grade_id=? "
                            "AND publication_status='published' AND week_no<=?",
                            (key, revision, grade, api.academic()[1] + 1)).fetchone()
        if not lesson:
            raise not_found()
        payload = json.loads(lesson[0])
    else:
        payload = _published_native(handler.server, key, revision, grade)
    ref = bunny_reference(payload)
    if not ref:
        raise not_found()
    row = registered(db, ref['uploadId'], provider, key)
    config = read_config().require()
    check_library(row, config)
    require_ready(row)
    binding = (session['student_id'], provider, key, revision, row['id'])
    if action == 'playback':
        saved = db.execute('SELECT position_seconds FROM bunny_stream_progress WHERE '
                           'student_id=? AND provider=? AND lesson_key=? AND lesson_revision=? AND upload_id=?',
                           binding).fetchone()
        position = min(saved[0], row['duration_seconds']) if saved else 0
        return {'playback': playback(row, config, position)}
    position = body['positionSeconds']
    if (type(position) not in (int, float) or not 0 <= position <= row['duration_seconds']
            or not math.isfinite(position)):
        raise api.APIError('Vị trí xem không hợp lệ.')
    position = round(position, 3)
    db.execute('INSERT INTO bunny_stream_progress VALUES(?,?,?,?,?,?,?) '
               'ON CONFLICT(student_id,provider,lesson_key,lesson_revision,upload_id) '
               'DO UPDATE SET position_seconds=excluded.position_seconds,updated_at=excluded.updated_at',
               (*binding, position, api.stamp()))
    return {'positionSeconds': position}
