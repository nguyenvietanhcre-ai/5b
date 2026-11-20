"""Lesson resources/check editing against disposable SQLite stores and real session dispatch."""
import base64
import copy
import json
from pathlib import Path
import secrets
import unittest

from backend import platform_api as api
from backend.lesson_resources import MAX_PDF_BYTES, safe_url
from backend.staff_api import create_first_admin
import test_vip_plus as base
import test_staff_api as staff_fixture
import test_platform_api as students
import test_family_accounts as family_fixture

PDF = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n'


def upload(data=PDF, **extra):
    return {'title': 'Phiếu học tập QA', 'upload': {'filename': 'phieu-hoc-tap.pdf', 'mime': 'application/pdf',
            'base64': base64.b64encode(data).decode(), **extra}}


class LessonAdminResourceTests(unittest.TestCase):
    def setUp(self):
        base.VipPlusTests.setUp(self)
        create_first_admin(self.path, 'lesson-admin', 'Quản trị học liệu QA', 'qa-lesson-resource-password')
        self.admin = staff_fixture.StaffClient(self.client.server)
        self.admin.call('login', {'login': 'lesson-admin', 'password': 'qa-lesson-resource-password'})

    def body(self, **extra):
        with api.connect(self.path) as db:
            topic = db.execute('SELECT id FROM topics WHERE grade_id=5 LIMIT 1').fetchone()[0]
        return {'grade': 5, 'topicId': topic, 'kind': 'topic', 'week': 1, 'title': 'Bài tài liệu QA ' + secrets.token_hex(4),
                'intro': 'Nội dung biên soạn QA rõ ràng.', 'videoUrl': 'https://youtu.be/abcdefghijk', 'status': 'draft', **extra}

    def row(self, identity):
        with api.connect(self.path) as db:
            row = db.execute('SELECT title FROM lessons WHERE id=?', (identity,)).fetchone()
        return next(r for r in self.admin.call('content?kind=lessons&q=' + row['title'])['rows'] if r['id'] == identity)

    def save(self, body, **change):
        value = {**body, **change}
        if 'id' in value:
            value['revision'] = self.row(value['id'])['revision']
        result = self.admin.call('lessons', value)
        return self.row(result['id']), value

    def download(self, href, client=None):
        client = client or self.client
        client.path = href
        client.command = 'GET'
        return api.dispatch(client, 'GET', href)[0]

    def test_ordinary_draft_publish_projection_and_pdf_cookie_download(self):
        examples = [{'text': 'Ví dụ QA có đáp số đã giải.', 'steps': ['Bước giải tự học QA.'], 'answer': '12'}]
        body = self.body(materials=[upload(), {'title': 'Tài liệu liên kết', 'href': 'https://example.test/phieu.pdf'}], examples=examples)
        row, _ = self.save(body)
        private_href = row['materials'][0]['href']
        self.assertNotIn(row['title'], [v['title'] for v in self.client.call('session')['lessons']])
        with self.assertRaises(api.APIError) as error:
            self.download(private_href)
        self.assertEqual(error.exception.status, 404)
        row, _ = self.save(body, id=row['id'], status='published', materials=row['materials'])
        public = next(v for v in self.client.call('session')['lessons'] if v['title'] == row['title'])
        self.assertEqual(public['examples'], examples)
        self.assertEqual(public['videoPreview']['provider'], 'youtube')
        for name in ('base64', 'resourceId', 'sha256', 'filename'):
            self.assertNotIn('"' + name + '"', json.dumps(public))
        self.assertEqual(self.download(public['materials'][0]['href'])['_lesson_binary'], PDF)
        stranger = students.Client(self.client.server)
        with self.assertRaises(api.APIError) as error:
            self.download(public['materials'][0]['href'], stranger)
        self.assertEqual(error.exception.status, 401)

    def test_old_pdf_revision_retained_and_crosslesson_grade_spoofs_denied(self):
        body = self.body(materials=[upload()], status='published')
        row, _ = self.save(body)
        href = row['materials'][0]['href']
        old_id = row['materials'][0]['resourceId']
        row, _ = self.save(body, id=row['id'], materials=[])
        self.assertEqual(row['materials'], [])
        self.assertEqual(self.download(href)['_lesson_binary'], PDF)
        with self.assertRaises(api.APIError):
            self.download(href.replace('/1/', '/2/'))
        with self.assertRaises(api.APIError):
            self.save(self.body(materials=[{'title': 'Sai bài', 'resourceId': old_id}]))
        younger = students.Client(self.client.server)
        younger.call('auth/register', {'login': 'grade4-' + secrets.token_hex(5), 'password': secrets.token_urlsafe(20),
                     'name': 'Học sinh khối khác', 'birthYear': api.academic()[0] - 9})
        with self.assertRaises(api.APIError) as error:
            self.download(href, younger)
        self.assertEqual(error.exception.status, 404)
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM lesson_material_files').fetchone()[0], 1)

    def test_upload_validation_and_aggregate_limit_roll_back_all_files(self):
        values = [upload(mime='image/png'), upload(filename='../phieu.pdf'), upload(filename='CON.pdf'),
                  upload(data=b'not a PDF'), upload(base64='%%%bad%%%'), upload(filename='bad\n.pdf')]
        half = b'%PDF-1.4\n' + b' ' * (MAX_PDF_BYTES // 2) + b'\n%%EOF'
        values.append([upload(half), upload(half)])
        for material in values:
            with self.subTest(kind=str(material)[:30]):
                with self.assertRaises(api.APIError):
                    self.save(self.body(materials=material if isinstance(material, list) else [material]))
                with api.connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM lesson_material_files').fetchone()[0], 0)

    def test_safe_urls_examples_legacy_and_revision_conflict(self):
        for value in ('javascript:alert(1)', '//example.test/a', 'http://example.test/a', '/\\example.test',
                      'https://user:pass@example.test/a', 'https://example.test/a\n', 'https://exa mple.test', 'https://x:bad/a'):
            with self.subTest(url=value), self.assertRaises(api.APIError):
                safe_url(value)
        body = self.body(videoUrl='/video/bai.mp4', exampleText='Bài mẫu cũ', exampleSteps='Bước một\nBước hai')
        row, _ = self.save(body)
        self.assertEqual(row['examples'], [{'text': 'Bài mẫu cũ', 'steps': ['Bước một', 'Bước hai']}])
        stale = {**body, 'id': row['id'], 'revision': row['revision'], 'examples': []}
        self.admin.call('lessons', stale)
        self.assertEqual(self.row(row['id'])['examples'], [])
        with self.assertRaises(api.APIError) as error:
            self.admin.call('lessons', stale)
        self.assertEqual(error.exception.status, 409)
        with self.assertRaises(api.APIError):
            self.save(self.body(examples=[{'text': 'QA', 'steps': []}] * 11))
        self.admin.csrf = 'bad'
        with self.assertRaises(api.APIError) as error:
            self.save(self.body(materials=[upload()]))
        self.assertEqual(error.exception.status, 403)

    def test_teacher_cannot_edit_resources_or_read_staff_fixed_answers(self):
        self.admin.call('users', {'login': 'lesson-teacher', 'fullName': 'Giáo viên QA', 'role': 'teacher',
                                'status': 'active', 'password': 'qa-lesson-teacher-password'})
        teacher = staff_fixture.StaffClient(self.client.server)
        teacher.call('login', {'login': 'lesson-teacher', 'password': 'qa-lesson-teacher-password'})
        for endpoint, body in (('content?kind=lessons', None), ('lessons', self.body(materials=[upload()])),
                               ('native-lessons', None)):
            with self.subTest(endpoint=endpoint), self.assertRaises(api.APIError) as error:
                teacher.call(endpoint, body)
            self.assertEqual(error.exception.status, 403)

    def native(self):
        from backend.local_pilot import LocalPilot
        root = Path(__file__).resolve().parents[1]
        if not (root/'pilot-inputs/manifest.json').is_file():self.skipTest('Private sealed learning inputs; mandatory local release gate')
        self.pilot = LocalPilot(self.path, Path(self.tmp.name) / 'pilot.sqlite3', root / 'pilot-inputs', restructure_inputs=root / 'restructure-inputs')
        self.client.server.local_pilot = self.pilot
        with api.connect(self.path) as db:
            session = api.read_session(self.client, db)
        with api.connect(self.pilot.path, True) as db:
            self.native_session = self.pilot.principal(db, session, 'Free', 5)
        key = self.admin.call('native-lessons')['rows'][0]['lessonKey']
        return self.admin.call('native-lessons/item?key=' + key)['item']

    def native_save(self, old, **extra):
        return self.admin.call('native-lessons', {'lessonKey': old['lessonKey'], 'draftRevision': old['draftRevision'],
                  'baseRevision': old['publishedRevision'], 'title': old['title'], 'sections': old['sections'], 'action': 'draft', **extra})['item']

    def public_native(self, key, revision=None):
        with api.connect(self.pilot.path, True) as db:
            return self.pilot.knowledge.lesson(db, self.native_session, key, revision)

    def test_native_draft_pdf_invisible_publish_old_revision_download_and_no_answer_grant(self):
        old = self.native()
        key = old['lessonKey']
        with api.connect(self.pilot.path) as db:
            original = db.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=1', (key,)).fetchone()[0]
        draft = self.native_save(old, videoRef='/video/native.mp4', materials=[upload()])
        self.assertEqual(self.public_native(key)['lesson']['materials'], [])
        with self.assertRaises(api.APIError):
            self.download(draft['materials'][0]['href'])
        published = self.native_save(draft, action='publish')
        public = self.public_native(key)['lesson']
        self.assertEqual(public['revision'], 2)
        self.assertEqual(public['videoRef'], '/video/native.mp4')
        self.assertEqual(self.download(public['materials'][0]['href'])['_lesson_binary'], PDF)
        for name in ('correctAnswer', 'expectedAnswer', 'solution', 'base64', 'resourceId'):
            self.assertNotIn('"' + name + '"', json.dumps(public))
        href = public['materials'][0]['href']
        latest = self.native_save(published, action='publish', materials=[])
        self.assertEqual(self.public_native(key)['lesson']['materials'], [])
        self.assertEqual(self.download(href)['_lesson_binary'], PDF)
        with api.connect(self.pilot.path) as db:
            self.assertEqual(db.execute('SELECT payload_json FROM knowledge_lessons WHERE lesson_key=? AND revision=1', (key,)).fetchone()[0], original)
            self.assertEqual(db.execute('SELECT count(*) FROM knowledge_checks').fetchone()[0], 0)
        self.native_save(latest, action='archive')
        with self.assertRaises(api.APIError):
            self.download(href)

    def test_native_fixed_edit_revision_old_check_and_choice_validation(self):
        old = self.native()
        key = old['lessonKey']
        original_fixed = copy.deepcopy(old['fixed'])
        q = copy.deepcopy(original_fixed)
        q.update(prompt='Câu hỏi QA một kết quả: nhập số hai.', correctAnswer='2')
        draft = self.native_save(old, fixed=q, solution=['Định hướng QA.', 'Mấu chốt QA.', 'Kết quả bằng 2.'])
        self.assertEqual(self.public_native(key)['lesson']['fixed']['prompt'], original_fixed['prompt'])
        published = self.native_save(draft, action='publish')
        self.assertEqual(published['fixed']['revision'], original_fixed['revision'] + 1)
        with api.connect(self.pilot.path, True) as db:
            previous = self.pilot.knowledge.check(db, self.native_session, key, {'requestKey': secrets.token_hex(12), 'answer': original_fixed['correctAnswer'], 'lessonRevision': 1})
            current = self.pilot.knowledge.check(db, self.native_session, key, {'requestKey': secrets.token_hex(12), 'answer': '2', 'lessonRevision': 2})
        self.assertTrue(previous['correct'])
        self.assertTrue(current['correct'])
        unchanged = self.native_save(published, action='publish', videoRef='https://example.test/native')
        self.assertEqual(unchanged['fixed']['revision'], published['fixed']['revision'])
        q = copy.deepcopy(unchanged['fixed'])
        q.update(responseMode='choice', options=['2', '3', '4', '5'], correctAnswer='2',
                 choiceRationales=['Đối chiếu đủ mọi dữ kiện QA.', 'Nhầm phép cộng trong dữ kiện QA.', 'Nhầm phép trừ trong dữ kiện QA.', 'Nhầm số phần bằng nhau khi giải QA.'])
        choice = self.native_save(unchanged, action='publish', fixed=q)
        self.assertEqual(self.public_native(key)['lesson']['fixed']['options'], q['options'])
        for change in ({'options': ['2', '2,0', '4', '5']}, {'choiceRationales': ['x'] * 4},
                       {'correctAnswer': '9'}, {'questionKey': 'foreign-question'},
                       {'responseMode': 'typed', 'answerShape': 'parts'}):
            with self.subTest(change=change), self.assertRaises(api.APIError):
                self.native_save(choice, fixed={**choice['fixed'], **change})

    def test_existing_native_complete_choice_can_edit_prompt_and_solution(self):
        self.native()
        rows = self.admin.call('native-lessons')['rows']
        current = next(value for value in (self.admin.call('native-lessons/item?key=' + row['lessonKey'])['item'] for row in rows)
                       if value['fixed'].get('answerShape') == 'complete-choice')
        fixed = copy.deepcopy(current['fixed'])
        fixed['prompt'] += '\nGhi chú biên tập QA.'
        published = self.native_save(current, action='publish', fixed=fixed,
                                     solution=['Định hướng QA đầy đủ.', 'Mấu chốt QA đầy đủ.', 'Bài giải QA đầy đủ.'])
        self.assertEqual(published['fixed']['options'], current['fixed']['options'])
        self.assertEqual(published['fixed']['revision'], current['fixed']['revision'] + 1)
        public = self.public_native(current['lessonKey'])['lesson']['fixed']
        self.assertEqual(public['prompt'], fixed['prompt'])
        self.assertNotIn('correctAnswer', public)


class FamilyLessonMaterialTests(unittest.TestCase):
    PASSWORD = family_fixture.FamilyAccountsTests.PASSWORD
    setUp = family_fixture.FamilyAccountsTests.setUp
    consent = family_fixture.FamilyAccountsTests.consent
    register_body = family_fixture.FamilyAccountsTests.register_body
    register = family_fixture.FamilyAccountsTests.register
    full = family_fixture.FamilyAccountsTests.full
    add_child = family_fixture.FamilyAccountsTests.add_child
    body = LessonAdminResourceTests.body
    row = LessonAdminResourceTests.row
    save = LessonAdminResourceTests.save
    download = LessonAdminResourceTests.download

    def test_cookie_only_pdf_preserves_current_child_context_and_parent_guards(self):
        api.seed_catalog(self.path)
        self.client, state = self.register()
        create_first_admin(self.path, 'family-lesson-admin', 'Quản trị QA', 'qa-family-lesson-password')
        self.admin = staff_fixture.StaffClient(self.server)
        self.admin.call('login', {'login': 'family-lesson-admin', 'password': 'qa-family-lesson-password'})
        row, _ = self.save(self.body(materials=[upload()], status='published'))
        href = row['materials'][0]['href']
        self.client.headers.pop('X-Family-Context', None)
        self.assertEqual(self.download(href)['_lesson_binary'], PDF)
        self.client.headers['X-Family-Context'] = 'stale-explicit-context'
        with self.assertRaises(api.APIError) as error:
            self.download(href)
        self.assertEqual(error.exception.status, 403)
        self.client.headers['X-Family-Context'] = self.client.context
        self.add_child(self.client, grade=4)
        children = self.client.call('state')['children']
        younger = next(c for c in children if c['grade'] == 4)
        self.client.call('select', {'childId': younger['id'], 'pin': '4321'})
        self.client.headers.pop('X-Family-Context', None)
        with self.assertRaises(api.APIError) as error:
            self.download(href)
        self.assertEqual(error.exception.status, 404)
        self.full(self.client)
        self.client.headers.pop('X-Family-Context', None)
        with self.assertRaises(api.APIError) as error:
            self.download(href)
        self.assertEqual(error.exception.status, 403)


if __name__ == '__main__':
    unittest.main()
