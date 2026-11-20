"""Bounded lesson resources; PDF bytes are private and immutable, never presentation data."""
import base64
import binascii
import hashlib
import json
import re
import secrets
import unicodedata
from urllib.parse import parse_qs, urlsplit

from . import platform_api as api

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_MATERIALS = 20
MATERIAL_PATH = re.compile(r'/api/v1/lesson-materials/(main|native)/([A-Za-z0-9._-]{1,120})/([1-9][0-9]{0,8})/([a-f0-9]{32})')


def initialize_storage(db):
    """Dedicated pilot stores deliberately apply only their supported migrations."""
    from pathlib import Path
    from .database import execute_sql
    name = '0043_lesson_materials.sql'
    if not db.execute('SELECT 1 FROM schema_migrations WHERE name=?', (name,)).fetchone():
        execute_sql(db, (Path(__file__).with_name('migrations') / name).read_text(encoding='utf-8'))
        db.execute('INSERT INTO schema_migrations(name) VALUES (?)', (name,))


def safe_url(value, *, empty=False):
    if not isinstance(value, str) or len(value) > 2048:
        raise api.APIError('Đường dẫn cần là chuỗi tối đa 2.048 ký tự.')
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise api.APIError('Đường dẫn không được chứa ký tự điều khiển.')
    value = value.strip()
    if not value and empty:
        return ''
    if not value or '\\' in value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise api.APIError('Đường dẫn cần bắt đầu bằng / hoặc HTTPS an toàn.')
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password
                 or value.startswith('/') and not value.startswith('//') and not parsed.scheme and not parsed.netloc)
        # A malformed port must fail here, before a browser interprets the URL.
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise api.APIError('Đường dẫn cần bắt đầu bằng / hoặc HTTPS, không chứa tài khoản truy cập.')
    return value


def video_preview(value):
    try:
        href = safe_url(value, empty=True)
    except api.APIError:
        return None
    if not href:
        return None
    parsed = urlsplit(href)
    result = {'href': href, 'provider': 'link'}
    host = (parsed.hostname or '').lower()
    identity = None
    if host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        identity = parse_qs(parsed.query).get('v', [None])[0] if parsed.path == '/watch' else (parsed.path.split('/')[2] if parsed.path.startswith(('/embed/', '/shorts/')) and len(parsed.path.split('/')) > 2 else None)
    elif host == 'youtu.be':
        identity = parsed.path.lstrip('/')
    if identity and re.fullmatch(r'[A-Za-z0-9_-]{11}', identity):
        result.update(provider='youtube', embedUrl='https://www.youtube-nocookie.com/embed/' + identity)
    elif host in ('vimeo.com', 'www.vimeo.com', 'player.vimeo.com') and re.fullmatch(r'/(?:video/)?[0-9]+', parsed.path):
        result.update(provider='vimeo', embedUrl='https://player.vimeo.com/video/' + parsed.path.rsplit('/', 1)[1])
    elif parsed.path.lower().endswith(('.mp4', '.webm', '.ogg')):
        result['provider'] = 'file'
    return result


def bunny_reference(presentation):
    from .bunny_stream import UPLOAD_ID
    value = presentation.get('bunnyVideo') if isinstance(presentation, dict) else None
    if not isinstance(value, dict):
        return None
    identity = value.get('uploadId')
    if isinstance(identity, str) and UPLOAD_ID.fullmatch(identity):
        return value
    return None


def lesson_video(presentation, legacy):
    ref = bunny_reference(presentation)
    if ref:
        return {'provider': 'bunny', 'durationSeconds': ref.get('durationSeconds', 0)}
    return video_preview(legacy)


def staff_bunny_video(db, presentation, provider, key):
    from .bunny_stream import registered
    ref = bunny_reference(presentation)
    if not ref:
        return None
    try:
        row = registered(db, ref['uploadId'], provider, key)
    except api.APIError as exc:
        if exc.status != 404:
            raise
        return {'uploadId': ref['uploadId'], 'status': 'failed', 'durationSeconds': 0}
    return {'uploadId': row['id'], 'status': row['state'], 'durationSeconds': row['duration_seconds']}


def save_lesson_video(db, server, user, body, presentation, provider, key, legacy_key, previous, *, publishing):
    from . import bunny_stream
    legacy = safe_url(body[legacy_key], empty=True) if legacy_key in body else previous
    bunny_stream.guarded_legacy_url(legacy, previous)
    ref = bunny_reference(presentation)
    if 'bunnyVideo' in body:
        value = body['bunnyVideo']
        if value is None:
            presentation.pop('bunnyVideo', None)
            return legacy
        if not isinstance(value, dict) or set(value) != {'uploadId'} or not isinstance(value['uploadId'], str) or not bunny_stream.UPLOAD_ID.fullmatch(value['uploadId']):
            raise api.APIError('Tham chiếu video không hợp lệ.')
        legacy = legacy if legacy_key in body else ''
        changed = not ref or ref['uploadId'] != value['uploadId']
        ref = value
    else:
        changed = False
    if not ref:
        return legacy
    if legacy:
        raise api.APIError('Chỉ chọn một nguồn video cho bài học.')
    if not changed and not publishing:
        return ''
    row = bunny_stream.registered(db, ref['uploadId'], provider, key)
    if changed and row['staff_id'] != user['id']:
        raise bunny_stream.not_found()
    config = bunny_stream.read_config().require()
    bunny_stream.check_library(row, config)
    if publishing:
        row = bunny_stream.refresh_upload(server, db, row, config)
        bunny_stream.require_ready(row)
    presentation['bunnyVideo'] = {'uploadId': row['id'], 'durationSeconds': row['duration_seconds']}
    return ''


def normalize_examples(value):
    if not isinstance(value, list) or len(value) > 10:
        raise api.APIError('Mỗi bài có tối đa 10 câu hỏi mẫu.')
    result = []
    for example in value:
        if not isinstance(example, dict) or set(example) - {'text', 'steps', 'answer'}:
            raise api.APIError('Câu hỏi mẫu cần có đề bài, các bước giải và đáp số tùy chọn.')
        prompt = api.text_field(example, 'text', 20000)
        steps = example.get('steps', [])
        if isinstance(steps, str):
            steps = [s.strip() for s in steps.splitlines() if s.strip()]
        if not isinstance(steps, list) or len(steps) > 50 or any(not isinstance(s, str) or not s.strip() or len(s) > 2000 for s in steps):
            raise api.APIError('Lời giải mẫu cần tối đa 50 bước, mỗi bước không quá 2.000 ký tự.')
        item = {'text': prompt, 'steps': [s.strip() for s in steps]}
        if 'answer' in example:
            answer = api.text_field(example, 'answer', 2000, 0)
            if answer:
                item['answer'] = answer
        result.append(item)
    return result


def public_examples(presentation):
    source = presentation.get('examples')
    if not isinstance(source, list):
        source = [presentation['example']] if isinstance(presentation.get('example'), dict) else []
    # Legacy incomplete data never breaks a student snapshot.
    result = []
    for value in source[:10]:
        try:
            result.extend(normalize_examples([value]))
        except api.APIError:
            continue
    return result


def file_metadata(row):
    return {name: row[name] for name in ('resource_id', 'filename', 'mime', 'size', 'sha256')}


def normalize_materials(db, value, provider, key):
    if not isinstance(value, list) or len(value) > MAX_MATERIALS:
        raise api.APIError('Mỗi bài có tối đa 20 tài liệu.')
    result = []
    aggregate = 0
    for material in value:
        if not isinstance(material, dict):
            raise api.APIError('Thông tin tài liệu không hợp lệ.')
        title = api.text_field(material, 'title', 180)
        upload = material.get('upload')
        identity = material.get('resourceId')
        if upload is not None and identity:
            raise api.APIError('Chỉ chọn một nguồn cho mỗi tài liệu.')
        if upload is not None:
            if not isinstance(upload, dict) or set(upload) != {'filename', 'mime', 'base64'}:
                raise api.APIError('Tệp PDF cần tên tệp, MIME và dữ liệu base64.')
            filename = upload.get('filename')
            if (not isinstance(filename, str) or not 1 <= len(filename) <= 160 or filename != filename.strip()
                    or any(ord(c) < 32 or ord(c) == 127 or c in '/\\:<>"|?*' for c in filename)
                    or not filename.lower().endswith('.pdf') or filename.startswith('.')
                    or re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])\.pdf', filename, re.I)):
                raise api.APIError('Tên tệp PDF không hợp lệ; không dùng đường dẫn hoặc ký tự điều khiển.')
            encoded = upload.get('base64')
            if upload.get('mime') != 'application/pdf' or not isinstance(encoded, str) or len(encoded) > ((MAX_PDF_BYTES + 2) // 3) * 4:
                raise api.APIError('Chỉ nhận PDF, tổng dung lượng tải lên tối đa 5 MiB mỗi lần lưu.')
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise api.APIError('Dữ liệu base64 của PDF không hợp lệ.') from None
            aggregate += len(data)
            if aggregate > MAX_PDF_BYTES:
                raise api.APIError('Tổng dung lượng PDF tải lên không được quá 5 MiB mỗi lần lưu.')
            if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-1024:]:
                raise api.APIError('Nội dung tệp không có định dạng PDF hợp lệ.')
            identity = secrets.token_hex(16)
            db.execute('INSERT INTO lesson_material_files VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (identity, provider, key, unicodedata.normalize('NFC', filename), 'application/pdf', len(data), hashlib.sha256(data).hexdigest(), data, api.stamp(), 1))
        if identity:
            if not isinstance(identity, str) or not re.fullmatch(r'[a-f0-9]{32}', identity):
                raise api.APIError('Mã tài liệu không hợp lệ.')
            row = db.execute('SELECT * FROM lesson_material_files WHERE resource_id=? AND provider=? AND lesson_key=?', (identity, provider, key)).fetchone()
            if not row:
                raise api.APIError('Tệp không thuộc bài học đang biên tập.', 404)
            metadata = file_metadata(row)
            result.append({'title': title, 'resourceId': metadata.pop('resource_id'), **metadata, 'download': True})
        else:
            href = safe_url(material.get('href'))
            if 'download' in material and type(material['download']) is not bool:
                raise api.APIError('Lựa chọn tải tài liệu không hợp lệ.')
            result.append({'title': title, 'href': href, **({'download': True} if material.get('download') else {})})
    return result


def project_materials(values, provider, key, revision, *, admin=False):
    result = []
    if not isinstance(values, list):
        return result
    for material in values[:MAX_MATERIALS]:
        if not isinstance(material, dict) or not isinstance(material.get('title'), str):
            continue
        identity = material.get('resourceId')
        if identity and isinstance(identity, str) and re.fullmatch(r'[a-f0-9]{32}', identity):
            href = f'/api/v1/lesson-materials/{provider}/{key}/{revision}/{identity}'
            item = {'title': material['title'], 'href': href, 'download': True}
            if admin:
                item.update({k: material[k] for k in ('resourceId', 'filename', 'mime', 'size', 'sha256') if k in material})
        else:
            try:
                href = safe_url(material.get('href'))
            except api.APIError:
                continue
            item = {'title': material['title'], 'href': href}
            if material.get('download') is True:
                item['download'] = True
        result.append(item)
    return result


def bind_materials(db, materials, provider, key, revision, grade, published):
    seen = set()
    for material in materials:
        identity = material.get('resourceId')
        if identity and identity not in seen:
            db.execute('INSERT INTO lesson_material_bindings VALUES(?,?,?,?,?,?)', (provider, key, revision, identity, grade, int(published)))
            seen.add(identity)


def material_download(handler, db, session, path):
    found = MATERIAL_PATH.fullmatch(path)
    if not found:
        raise api.APIError('Không tìm thấy tài liệu.', 404)
    provider, key, revision, identity = found.groups()
    revision = int(revision)
    from .system_settings import require_feature
    require_feature(db, 'learning_open')
    grade = api.grade_for_student(db, session['student_id'], session['birth_year'])
    if provider == 'main':
        from .content_retirement import retired
        if retired(db, grade):
            raise api.APIError('Học liệu của khối đang được cập nhật.', 404)
        return download_from(db, provider, key, revision, identity, grade)
    pilot = getattr(handler.server, 'local_pilot', None)
    if grade != 5 or not pilot or not pilot.knowledge:
        raise api.APIError('Tài liệu không thuộc khối của em.', 404)
    with api.connect(pilot.path) as native:
        hidden = native.execute('SELECT archived FROM staff_knowledge_drafts WHERE lesson_key=?', (key,)).fetchone()
        if hidden and hidden[0]:
            raise api.APIError('Bài học đã được rút khỏi danh mục.', 404)
        row = native.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=?', (key, revision)).fetchone()
        if not row or identity not in {m.get('resourceId') for m in json.loads(row[0]).get('materials', [])}:
            raise api.APIError('Tài liệu không thuộc phiên bản bài học.', 404)
        return download_from(native, provider, key, revision, identity, grade)


def download_from(db, provider, key, revision, identity, grade):
    row = db.execute('SELECT f.* FROM lesson_material_files f JOIN lesson_material_bindings b ON b.resource_id=f.resource_id '
                     'WHERE f.provider=? AND f.lesson_key=? AND f.resource_id=? AND b.provider=f.provider AND b.lesson_key=f.lesson_key '
                     'AND b.lesson_revision=? AND b.grade=? AND b.published=1', (provider, key, identity, revision, grade)).fetchone()
    if not row:
        raise api.APIError('Tài liệu chưa được phát hành hoặc không thuộc bài học này.', 404)
    return {'_lesson_binary': bytes(row['payload']), 'mime': row['mime'], 'filename': row['filename']}
