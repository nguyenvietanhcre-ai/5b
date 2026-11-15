import base64
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing

from backend.lesson_library import import_bundle, load_bundle, render_articles, SECTIONS


def sample():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>Diagram</title><path d="M0 0 L10 10"/></svg>'
    sha = hashlib.sha256(svg).hexdigest()
    return {'schemaVersion': 1, 'assets': [{'sha256': sha, 'mimeType': 'image/svg+xml', 'base64': base64.b64encode(svg).decode()}], 'lessons': [{
        'schemaVersion': 1, 'id': 'example', 'revision': 1, 'grade': 5,
        'status': 'draft', 'reviewerType': 'assistant', 'title': 'Example',
        'eyebrow': 'Sample', 'sourceLabel': 'Original', 'source': {'kind': 'original'},
        'prompt': [{'type': 'text', 'text': 'Question'}],
        'overview': [{'type': 'media', 'sha256': sha, 'alt': 'Diagram'}],
        'sections': [{'key': key, 'title': title, 'blocks': [{'type': 'text', 'text': '<script>alert(1)</script>'}]} for key, title in SECTIONS]}]}


class LessonLibraryTests(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[1]/'work'/'lesson-library-tests'
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name)/'bank.sqlite3'

    def test_roundtrip_media_and_idempotency(self):
        bundle = sample()
        import_bundle(self.db, bundle)
        import_bundle(self.db, bundle)
        self.assertEqual(load_bundle(self.db), bundle)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM lesson_revisions').fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_revisions_remain_immutable_and_latest_exports(self):
        first = sample()
        import_bundle(self.db, first)
        second = copy.deepcopy(first)
        second['lessons'][0].update(revision=2, title='Revised')
        import_bundle(self.db, second)
        self.assertEqual(load_bundle(self.db)['lessons'][0]['title'], 'Revised')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM lesson_revisions').fetchone()[0], 2)

    def test_conflicting_batch_rolls_back_new_lesson(self):
        original = sample()
        import_bundle(self.db, original)
        conflict = copy.deepcopy(original)
        conflict['lessons'][0]['title'] = 'Conflict'
        new = copy.deepcopy(original['lessons'][0])
        new['id'] = 'new-lesson'
        conflict['lessons'].insert(0, new)
        with self.assertRaisesRegex(ValueError, 'conflict'):
            import_bundle(self.db, conflict)
        self.assertEqual(load_bundle(self.db), original)

    def test_missing_media_rejected(self):
        bundle = sample()
        bundle['assets'] = []
        with self.assertRaisesRegex(ValueError, 'media'):
            import_bundle(self.db, bundle)

    def test_noncanonical_sections_rejected(self):
        bundle = sample()
        bundle['lessons'][0]['sections'][0]['title'] = 'Old name'
        with self.assertRaisesRegex(ValueError, 'canonical'):
            import_bundle(self.db, bundle)

    def test_html_attributes_and_external_links_rejected(self):
        for attrs in [{'onclick': 'alert(1)'}, {'href': 'javascript:alert(1)'}, {'style': 'display:none'}]:
            bundle = sample()
            bundle['lessons'][0]['prompt'] = [{'type': 'element', 'tag': 'a', 'attrs': attrs, 'children': []}]
            with self.assertRaises(ValueError):
                import_bundle(self.db, bundle)

    def test_svg_active_content_and_external_reference_rejected(self):
        for raw in [b'<svg><script>alert(1)</script></svg>', b'<svg><path fill="url(https://example.com/a)"/></svg>', b'<svg onload="alert(1)"/>']:
            bundle = sample()
            sha = hashlib.sha256(raw).hexdigest()
            bundle['assets'][0].update(sha256=sha, base64=base64.b64encode(raw).decode())
            with self.assertRaises(ValueError):
                import_bundle(self.db, bundle)

    def test_checksum_mismatch_rejected(self):
        bundle = sample()
        bundle['assets'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            import_bundle(self.db, bundle)

    def test_draft_only_and_teacher_claim_rejected(self):
        for field, value in [('status', 'published'), ('reviewerType', 'teacher')]:
            bundle = sample()
            bundle['lessons'][0][field] = value
            with self.assertRaises(ValueError):
                import_bundle(self.db, bundle)

    def test_renderer_escapes_text_and_keeps_three_sections(self):
        result = render_articles(sample())
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<script>', result)
        for _, title in SECTIONS:
            self.assertIn(title, result)
        self.assertEqual(result.count('class="section-number"'), 3)

    def test_valid_math_and_invalid_math(self):
        bundle = sample()
        block = {'type': 'math', 'latex': '12', 'mathml': '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>12</mn></math>'}
        bundle['lessons'][0]['sections'][2]['blocks'] = [block]
        import_bundle(self.db, bundle)
        self.assertIn('<mn>12</mn>', render_articles(load_bundle(self.db)))
        block['mathml'] = '<math xmlns="http://www.w3.org/1998/Math/MathML"><script/></math>'
        with self.assertRaises(ValueError):
            import_bundle(self.db, bundle)

    def test_stored_asset_corruption_detected(self):
        import_bundle(self.db, sample())
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE lesson_media SET content=?', (b'<svg/>',))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_bundle(self.db)


if __name__ == '__main__':
    unittest.main()
