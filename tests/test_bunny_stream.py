"""Managed video dispatch and migration in disposable stores with a fake Bunny API."""
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import secrets
import tempfile
from threading import Event
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from backend import bunny_stream as bunny, platform_api as api
from backend.arena import Arena
from backend.content_retirement import activate
from backend.database import initialize
from backend.knowledge_catalogue import Knowledge, SCHEMA
from backend.staff_api import create_first_admin
import test_family_accounts as family_tests
from test_lesson_admin_resources import PDF, upload
from test_platform_api import Client
from test_staff_api import StaffClient


class FakeBunny:
    def __init__(self):
        self.videos = {}
        self.creates = 0
        self.lose_reply = False

    def __call__(self, method, path, api_key, payload):
        assert api_key == 'fixture-upload-key'
        route = urlsplit(path)
        parts = route.path.split('/')
        assert parts[1:4] == ['library', '12345', 'videos'], parts
        if method == 'POST':
            assert len(parts) == 4 and set(payload) == {'title'}
            assert payload['title'].startswith('5BMath ') and len(payload['title']) == 39
            guid = str(uuid4())
            video = self.videos[guid] = {'title': payload['title'], 'guid': guid, 'videoLibraryId': 12345,
                                         'status': 0, 'length': 0, 'storageSize': 0}
            self.creates += 1
            if self.lose_reply:
                self.lose_reply = False
                raise OSError('private upstream response and fixture-upload-key')
            return dict(video)
        if route.query:
            title = parse_qs(route.query)['search'][0]
            return {'items': [dict(video) for video in self.videos.values() if video['title'] == title]}
        return dict(self.videos[parts[-1]])

    def ready(self, result):
        self.videos[result['tus']['headers']['VideoId']].update(status=3, length=165, storageSize=7340032)


class BunnyStreamTests(unittest.TestCase):
    PASSWORD = family_tests.FamilyAccountsTests.PASSWORD
    consent = family_tests.FamilyAccountsTests.consent
    register_body = family_tests.FamilyAccountsTests.register_body
    full = family_tests.FamilyAccountsTests.full
    add_child = family_tests.FamilyAccountsTests.add_child

    def setUp(self):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix='bunny-stream-', dir=work)
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'main.sqlite3'
        self.config = self.path.with_name('bunny-stream.json')
        self.enterContext(patch.dict(os.environ, {'BUNNY_STREAM_CONFIG_FILE': str(self.config)}))
        self.enterContext(patch.object(api, 'ITERATIONS', 1000))
        self.set_config()
        initialize(self.path)
        initialize(self.path)
        api.seed_catalog(self.path)
        self.fake = FakeBunny()
        self.server = SimpleNamespace(database_path=self.path, arena=Arena(), bunny_stream_transport=self.fake)
        self.admin_password = 'qa-bunny-staff-password'
        create_first_admin(self.path, 'bunny-admin', 'Quản trị QA', self.admin_password)
        self.admin = StaffClient(self.server)
        self.admin.call('login', {'login': 'bunny-admin', 'password': self.admin_password})
        self.email = 'bunny-family-' + secrets.token_hex(6) + '@example.test'

    def set_config(self, **extra):
        self.config.write_text(json.dumps({'enabled': True, 'libraryId': 12345,
                                           'apiKey': 'fixture-upload-key', 'tokenKey': 'fixture-embed-key', **extra}),
                               encoding='utf-8')

    def lesson(self, **extra):
        with api.connect(self.path) as db:
            topic = db.execute('SELECT id FROM topics WHERE grade_id=5 ORDER BY id LIMIT 1').fetchone()[0]
        return {'grade': 5, 'topicId': topic, 'kind': 'topic', 'week': 1, 'title': 'QA-' + secrets.token_hex(4),
                'intro': 'Bài học kiểm thử video có nội dung.', 'status': 'draft', **extra}

    def row(self, body):
        return self.admin.call('content?kind=lessons&q=' + body['title'])['rows'][0]

    def draft(self, **extra):
        body = self.lesson(**extra)
        self.admin.call('lessons', body)
        return body, self.row(body)

    def edit(self, body, row, **changes):
        self.admin.call('lessons', {**body, 'id': row['id'], 'revision': row['revision'], **changes})
        return self.row(body)

    def request_body(self, key, provider='main', **extra):
        return {'provider': provider, 'lessonKey': key, 'requestKey': secrets.token_hex(16), 'size': 1200000, **extra}

    def start(self, key, provider='main', **extra):
        return self.admin.call('bunny-stream/uploads', self.request_body(key, provider, **extra))

    def action(self, result, action, admin=None):
        return (admin or self.admin).call(f"bunny-stream/uploads/{result['upload']['id']}/{action}", {})

    def learner(self, grade=5):
        client = Client(self.server)
        client.call('auth/register', {'login': 'bunny-learner-' + secrets.token_hex(4),
                    'password': 'qa-video-learner-password', 'name': 'Học sinh QA',
                    'birthYear': api.academic()[0] - grade - 5})
        return client

    def denied(self, status, callback, code=None):
        with self.assertRaises(api.APIError) as caught:
            callback()
        self.assertEqual(caught.exception.status, status)
        if code:
            self.assertEqual(getattr(caught.exception, 'code', None), code)
        self.assertNotIn('fixture-upload-key', str(caught.exception))
        return caught.exception

    def main_published(self):
        body, row = self.draft()
        result = self.start(row['client_key'])
        self.fake.ready(result)
        updated = self.edit(body, row, status='published', bunnyVideo={'uploadId': result['upload']['id']})
        return body, updated, result

    def target(self, row):
        return {'provider': 'main', 'lessonKey': row['client_key'], 'revision': row['revision']}

    def assert_signed(self, result, upload_result):
        signed = urlsplit(result['embedUrl'])
        guid = upload_result['tus']['headers']['VideoId']
        self.assertEqual((signed.scheme, signed.netloc, signed.path),
                         ('https', 'player.mediadelivery.net', '/embed/12345/' + guid))
        query = parse_qs(signed.query)
        expires = result['expiresAt']
        self.assertGreater(expires, int(time.time()))
        self.assertLessEqual(expires, int(time.time()) + bunny.PLAYBACK_TTL)
        self.assertEqual(query, {
            'token': [hashlib.sha256(f'fixture-embed-key{guid}{expires}'.encode()).hexdigest()],
            'expires': [str(expires)], 'autoplay': ['false'], 'rememberPosition': ['false'],
            'rememberSettings': ['false'],
        })

    def test_config_reload_secrets_acl_and_csrf(self):
        outsider = StaffClient(self.server)
        self.denied(401, lambda: outsider.call('bunny-stream/config'))
        self.assertEqual(self.admin.call('bunny-stream/config'), {'configured': True, 'configSource': 'file',
                         'missing': [], 'maxVideos': 10, 'maxUploadBytes': 1024 ** 3})
        self.admin.call('users', {'login': 'bunny-teacher', 'fullName': 'Giáo viên QA', 'role': 'teacher',
                                  'status': 'active', 'password': self.admin_password})
        teacher = StaffClient(self.server)
        teacher.call('login', {'login': 'bunny-teacher', 'password': self.admin_password})
        self.denied(403, lambda: teacher.call('bunny-stream/config'))
        self.denied(403, lambda: teacher.call('bunny-stream/uploads', {}))
        original_csrf = self.admin.csrf
        self.admin.csrf = 'stale'
        self.denied(403, lambda: self.admin.call('bunny-stream/uploads', {}))
        self.admin.csrf = original_csrf
        self.admin.headers['Origin'] = 'https://other.example'
        self.denied(403, lambda: self.admin.call('bunny-stream/uploads', {}))
        self.admin.headers['Origin'] = 'http://localhost:8765'
        self.set_config(enabled=False)
        self.assertEqual(self.admin.call('bunny-stream/config')['missing'], ['enabled'])
        self.denied(503, lambda: self.start('unknown'), 'bunny_unconfigured')
        self.config.write_bytes(b'{' + b' ' * bunny.MAX_CONFIG_BYTES)
        self.assertEqual(self.admin.call('bunny-stream/config')['missing'], ['config'])
        self.config.unlink()
        self.assertEqual(self.admin.call('bunny-stream/config')['configSource'], 'missing')
        self.assertEqual(self.fake.creates, 0)

    def test_single_reservation_signature_limit_renewal_and_library_binding(self):
        _body, row = self.draft()
        self.set_config(maxVideos=1)
        self.denied(400, lambda: self.start(row['client_key'], size=bunny.MAX_UPLOAD_BYTES + 1))
        self.denied(404, lambda: self.start('foreign-lesson'))
        request = self.request_body(row['client_key'])
        result = self.admin.call('bunny-stream/uploads', request)
        signed = result['tus']['headers']
        self.assertEqual(result['tus']['endpoint'], 'https://video.bunnycdn.com/tusupload')
        self.assertEqual(signed['AuthorizationSignature'], hashlib.sha256(
            f"12345fixture-upload-key{signed['AuthorizationExpire']}{signed['VideoId']}".encode()).hexdigest())
        with patch.object(bunny.time, 'time', return_value=int(signed['AuthorizationExpire']) + 2):
            renewed = self.action(result, 'renew')
        self.assertEqual(renewed['upload'], result['upload'])
        self.assertGreater(renewed['tus']['expiresAt'], result['tus']['expiresAt'])
        self.assertEqual(renewed['tus']['headers']['VideoId'], signed['VideoId'])
        self.assertEqual(self.admin.call('bunny-stream/uploads', request)['upload'], result['upload'])
        self.denied(409, lambda: self.admin.call('bunny-stream/uploads', {**request, 'size': 1}), 'bunny_upload_conflict')
        self.denied(409, lambda: self.start(row['client_key']), 'bunny_video_limit')
        self.assertEqual(self.fake.creates, 1)
        self.set_config(libraryId=99999)
        self.denied(404, lambda: self.action(result, 'renew'), 'video_not_found')

    def test_unknown_remote_create_result_recovers_without_second_video(self):
        _body, row = self.draft()
        request = self.request_body(row['client_key'])
        self.fake.lose_reply = True
        self.denied(502, lambda: self.admin.call('bunny-stream/uploads', request), 'bunny_upstream')
        with api.connect(self.path) as db:
            pending = db.execute('SELECT id,state,video_guid FROM bunny_stream_uploads').fetchone()
            self.assertEqual(tuple(pending)[1:], ('creating', None))
        result = self.admin.call('bunny-stream/uploads', request)
        self.assertEqual(result['upload']['id'], pending['id'])
        self.assertEqual(self.fake.creates, 1)
        guid = result['tus']['headers']['VideoId']
        self.fake.videos[guid].update(status=3, length=60, storageSize=-1)
        self.denied(502, lambda: self.action(result, 'refresh'), 'bunny_upstream')
        self.fake.videos[guid].update(storageSize=200, videoLibraryId=987)
        self.denied(502, lambda: self.action(result, 'refresh'), 'bunny_upstream')

    def test_finish_status_waits_for_encoded_output(self):
        body, row = self.draft()
        result = self.start(row['client_key'])
        video = self.fake.videos[result['tus']['headers']['VideoId']]
        video.update(status=3, length=86, storageSize=0, encodeProgress=35)
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        self.assertNotIn('tus', self.action(result, 'renew'))
        self.denied(409, lambda: self.action(result, 'preview'), 'bunny_video_not_ready')
        self.denied(409, lambda: self.edit(body, row, status='published',
                                          bunnyVideo={'uploadId': result['upload']['id']}), 'bunny_video_not_ready')
        for size, progress in ((5000000, 35), (0, 100)):
            video.update(storageSize=size, encodeProgress=progress)
            self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        video.update(storageSize=5000000, encodeProgress=101)
        self.denied(502, lambda: self.action(result, 'refresh'), 'bunny_upstream')
        video['encodeProgress'] = 100
        ready = self.action(result, 'refresh')['upload']
        self.assertEqual((ready['id'], ready['status'], ready['durationSeconds']), (result['upload']['id'], 'ready', 86))
        self.assert_signed(self.action(result, 'preview')['playback'], result)
        self.assertEqual(self.fake.creates, 1)

    def test_playable_resolution_requires_explicit_complete_progress(self):
        body, row = self.draft()
        result = self.start(row['client_key'])
        video = self.fake.videos[result['tus']['headers']['VideoId']]
        video.update(status=4, length=86, storageSize=14013462)
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        video['encodeProgress'] = 99
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        video['encodeProgress'] = '100'
        self.denied(502, lambda: self.action(result, 'refresh'), 'bunny_upstream')
        video.update(encodeProgress=100, length=0)
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        video.update(length=86, storageSize=0)
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'processing')
        video['storageSize'] = 14013462
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'ready')
        published = self.edit(body, row, status='published', bunnyVideo={'uploadId': result['upload']['id']})
        self.assertEqual(published['bunnyVideo']['durationSeconds'], 86)
        self.assertEqual(self.fake.creates, 1)

    def test_simultaneous_requests_share_one_remote_creation(self):
        _body, row = self.draft()
        request = self.request_body(row['client_key'])
        entered, release = Event(), Event()

        def transport(method, path, api_key, payload):
            if method == 'POST':
                entered.set()
                self.assertTrue(release.wait(8))
            return self.fake(method, path, api_key, payload)

        self.server.bunny_stream_transport = transport
        second = StaffClient(self.server)
        second.headers, second.csrf = dict(self.admin.headers), self.admin.csrf
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.admin.call, 'bunny-stream/uploads', request)
            try:
                self.assertTrue(entered.wait(8))
                self.denied(502, lambda: second.call('bunny-stream/uploads', request), 'bunny_upstream')
            finally:
                release.set()
            first = future.result(timeout=8)
        self.assertEqual(second.call('bunny-stream/uploads', request)['upload']['id'], first['upload']['id'])
        self.assertEqual(self.fake.creates, 1)

    def test_main_publish_is_ready_atomic_projection_and_keeps_other_resources(self):
        body, row = self.draft(materials=[upload()], examples=[{'text': 'Ví dụ QA', 'steps': ['Bước QA.']}])
        body.pop('materials')
        result = self.start(row['client_key'])
        ref = {'uploadId': result['upload']['id']}
        self.denied(409, lambda: self.action(result, 'preview'), 'bunny_video_not_ready')
        self.denied(409, lambda: self.edit(body, row, status='published', bunnyVideo=ref), 'bunny_video_not_ready')
        self.assertEqual(self.row(body)['revision'], row['revision'])
        draft = self.edit(body, row, bunnyVideo=ref)
        self.assertEqual(draft['bunnyVideo']['status'], 'uploading')
        learner = self.learner()
        self.denied(404, lambda: learner.call('lesson-videos/playback', self.target(draft)), 'video_not_found')
        self.fake.ready(result)
        self.assertEqual(self.action(result, 'refresh')['upload']['status'], 'ready')
        self.assertNotIn('tus', self.action(result, 'renew'))
        self.assert_signed(self.action(result, 'preview')['playback'], result)
        published = self.edit(body, draft, status='published')
        lesson = next(item for item in learner.call('session')['lessons'] if item['id'] == row['client_key'])
        self.assertEqual(lesson['video'], {'provider': 'bunny', 'durationSeconds': 165})
        self.assertEqual(lesson['video'], lesson['videoPreview'])
        self.assertEqual(lesson['videoRef'], '')
        self.assertNotIn('bunnyVideo', lesson)
        self.assertNotIn(ref['uploadId'], json.dumps(lesson))
        self.assertEqual(lesson['examples'], body['examples'])
        href = lesson['materials'][0]['href']
        learner.path = href
        self.assertEqual(api.dispatch(learner, 'GET', href)[0]['_lesson_binary'], PDF)
        self.assert_signed(learner.call('lesson-videos/playback', self.target(published))['playback'], result)
        cleared = self.edit(body, published, status='published', bunnyVideo=None, videoUrl='https://youtu.be/abcdefghijk')
        self.assertIsNone(cleared['bunnyVideo'])
        self.assertEqual(cleared['videoPreview']['provider'], 'youtube')
        self.denied(404, lambda: learner.call('lesson-videos/playback', self.target(published)), 'video_not_found')

    def test_owner_lesson_binding_and_no_raw_bunny_url_attachment(self):
        body, row = self.draft()
        result = self.start(row['client_key'])
        self.admin.call('users', {'login': 'bunny-other-admin', 'fullName': 'Quản trị khác QA', 'role': 'admin',
                                  'status': 'active', 'password': self.admin_password})
        other = StaffClient(self.server)
        other.call('login', {'login': 'bunny-other-admin', 'password': self.admin_password})
        for action in ('renew', 'refresh', 'preview'):
            self.denied(404, lambda: self.action(result, action, other), 'video_not_found')
        ref = {'uploadId': result['upload']['id']}
        self.denied(404, lambda: other.call('lessons', {**body, 'id': row['id'], 'revision': row['revision'],
                                                      'bunnyVideo': ref}), 'video_not_found')
        other_body, other_lesson = self.draft()
        self.denied(404, lambda: self.edit(other_body, other_lesson, bunnyVideo=ref), 'video_not_found')
        self.denied(400, lambda: self.edit(body, row, bunnyVideo={'uploadId': result['tus']['headers']['VideoId']}))
        self.denied(400, lambda: self.edit(body, row, videoUrl='https://player.mediadelivery.net/embed/12345/anything'))
        self.denied(400, lambda: self.edit(body, row, videoUrl='https://player%2emediadelivery.net/embed/12345/anything'))

    def test_family_context_role_and_progress_are_child_isolated(self):
        _body, row, _result = self.main_published()
        target = self.target(row)
        family, state = family_tests.FamilyAccountsTests.register(self)
        first = state['children'][0]['id']
        self.assertEqual(family.learner('lesson-videos/playback', target)['playback']['positionSeconds'], 0)
        before = self.count_side_effects()
        self.assertEqual(family.learner('lesson-videos/progress', {**target, 'positionSeconds': 47.125})['positionSeconds'], 47.125)
        self.assertEqual(family.learner('lesson-videos/playback', target)['playback']['positionSeconds'], 47.125)
        self.assertEqual(before, self.count_side_effects())
        stale = family.copy_capability()
        stale.context = 'wrong'
        error = self.denied(403, lambda: stale.learner('lesson-videos/playback', target))
        self.assertTrue(error.familyAccessChanged)
        for unauth in ('context', 'csrf'):
            stale = family.copy_capability()
            setattr(stale, unauth, '')
            self.denied(403, lambda: stale.learner('lesson-videos/progress', {**target, 'positionSeconds': 2}))
        result = self.add_child(family, grade=5)
        self.denied(403, lambda: family.learner('lesson-videos/playback', target))
        second = next(child['id'] for child in result['children'] if child['id'] != first)
        family.call('select', {'childId': second, 'pin': '4321'})
        self.assertEqual(family.learner('lesson-videos/playback', target)['playback']['positionSeconds'], 0)
        for position in (-1, 166, float('nan'), float('inf'), True, '40'):
            with self.subTest(position=position):
                self.denied(400, lambda: family.learner('lesson-videos/progress', {**target, 'positionSeconds': position}))
        self.denied(400, lambda: family.learner('lesson-videos/progress', {**target, 'positionSeconds': 12, 'childId': first}))

    def count_side_effects(self):
        with api.connect(self.path) as db:
            return {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                    for table in ('lesson_progress', 'xp_events', 'exam_attempts', 'payment_orders',
                                  'family_cart_orders', 'purchased_credit_usage', 'purchased_credit_grants')}

    def test_grade_feature_schedule_retirement_and_missing_config(self):
        body, row, _result = self.main_published()
        target = self.target(row)
        learner = self.learner()
        self.denied(401, lambda: Client(self.server).call('lesson-videos/playback', target))
        self.denied(404, lambda: self.learner(4).call('lesson-videos/playback', target))
        self.denied(404, lambda: learner.call('lesson-videos/playback', {**target, 'revision': row['revision'] + 1}))
        self.denied(405, lambda: learner.call('lesson-videos/playback'))
        self.set_config(enabled=False)
        self.denied(503, lambda: learner.call('lesson-videos/playback', target), 'bunny_unconfigured')
        self.set_config()
        future = self.edit(body, row, status='published', week=53)
        self.denied(404, lambda: learner.call('lesson-videos/playback', self.target(future)))
        current = self.edit(body, future, status='published', week=1)
        with api.connect(self.path, True) as db:
            db.execute("UPDATE system_settings SET value_json=json_set(value_json,'$.learning_open',0) WHERE name='platform'")
        self.denied(403, lambda: learner.call('lesson-videos/playback', self.target(current)))
        with api.connect(self.path, True) as db:
            db.execute("UPDATE system_settings SET value_json=json_set(value_json,'$.learning_open',1) WHERE name='platform'")
            activate(db)
        self.denied(404, lambda: learner.call('lesson-videos/playback', self.target(current)))

    def native_fixture(self):
        path = self.path.with_name('native.sqlite3')
        initialize(path)
        key = 'native-video-qa'
        section = {'title': 'Phần QA', 'blocks': [{'type': 'text', 'text': 'Nội dung QA.'}]}
        value = {'lessonKey': key, 'topicKey': 'native-topic-qa', 'title': 'Bài bản địa QA', 'revision': 1,
                 'sections': [section] * 3, 'fixed': {'questionKey': 'fixed-video-qa', 'revision': 1,
                 'prompt': 'Nhập số một.', 'responseMode': 'typed', 'correctAnswer': '1', 'solution': [section] * 3}}
        with api.connect(path, True) as db:
            for sql in SCHEMA:
                db.execute(sql)
            db.execute('INSERT INTO knowledge_lessons VALUES(?,?,?,?,?)',
                       (key, 1, 'native-topic-qa', 'fake-digest', api.packed(value)))
        knowledge = Knowledge.__new__(Knowledge)
        self.server.local_pilot = SimpleNamespace(path=path, knowledge=knowledge)
        return path, key

    def native_edit(self, old, **extra):
        return self.admin.call('native-lessons', {'lessonKey': old['lessonKey'], 'draftRevision': old['draftRevision'],
                  'baseRevision': old['publishedRevision'], 'title': old['title'], 'sections': old['sections'],
                  'action': 'draft', **extra})['item']

    def test_native_immutable_video_revision_archive_and_no_fixed_answer_disclosure(self):
        learner = self.learner()
        native, key = self.native_fixture()
        original = self.admin.call('native-lessons/item?key=' + key)['item']
        result = self.start(key, 'native')
        ref = {'uploadId': result['upload']['id']}
        draft = self.native_edit(original, bunnyVideo=ref)
        target = {'provider': 'native', 'lessonKey': key, 'revision': 2}
        self.denied(404, lambda: learner.call('lesson-videos/playback', target))
        self.denied(409, lambda: self.native_edit(draft, action='publish'), 'bunny_video_not_ready')
        self.fake.ready(result)
        published = self.native_edit(draft, action='publish')
        self.assertEqual(published['publishedRevision'], 2)
        self.assert_signed(learner.call('lesson-videos/playback', target)['playback'], result)
        with api.connect(native, True) as db:
            student_id = db.execute("INSERT INTO students(student_code,full_name,grade_level) VALUES('QA-VID','QA',5)").lastrowid
            lesson = self.server.local_pilot.knowledge.lesson(db, {'student_id': student_id}, key, 2)['lesson']
        self.assertEqual(lesson['videoPreview'], {'provider': 'bunny', 'durationSeconds': 165})
        self.assertNotIn('correctAnswer', lesson['fixed'])
        self.assertNotIn('solution', lesson['fixed'])
        self.assertNotIn('bunnyVideo', lesson)
        learner.call('lesson-videos/progress', {**target, 'positionSeconds': 29})
        republished = self.native_edit(published, action='publish')
        self.assertEqual(republished['publishedRevision'], 3)
        self.assertEqual(learner.call('lesson-videos/playback', {**target, 'revision': 3})['playback']['positionSeconds'], 0)
        self.assertEqual(learner.call('lesson-videos/playback', target)['playback']['positionSeconds'], 29)
        newer = self.native_edit(republished, action='publish', bunnyVideo=None, videoRef='https://vimeo.com/123456')
        self.assertEqual(newer['publishedRevision'], 4)
        self.assert_signed(learner.call('lesson-videos/playback', target)['playback'], result)
        self.denied(404, lambda: learner.call('lesson-videos/playback', {**target, 'revision': 4}))
        archived = self.native_edit(newer, action='archive')
        self.denied(404, lambda: learner.call('lesson-videos/playback', target))
        self.native_edit(archived, action='restore')
        self.assert_signed(learner.call('lesson-videos/playback', target)['playback'], result)


if __name__ == '__main__':
    unittest.main()
