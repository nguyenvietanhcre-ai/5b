import sqlite3
import unittest
from unittest.mock import patch
from backend import premium_content


class StudyLibraryLabels(unittest.TestCase):
    def test_rename_only_classification_returned_label_preserves_slug_source_and_acl(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        db.executescript('CREATE TABLE video_series(slug TEXT,title TEXT,position INT,archived INT);'
                         'CREATE TABLE series_videos(id INT,title TEXT,position INT,series_slug TEXT,published INT,archived INT);')
        labels = [('giai-de-10-phut', 'Giải đề 10 phút'),
                  ('cau-phan-loai', 'Giải câu phân loại HS, thi HSG'), ('meo-lam-bai', 'Mẹo làm bài')]
        for i, (slug, label) in enumerate(labels):
            db.execute('INSERT INTO video_series VALUES(?,?,?,0)', (slug, label, i))
            for n in range(1, 5):
                db.execute('INSERT INTO series_videos VALUES(?,?,?,?,1,0)', (i * 10 + n, 'Video thật', n, slug))
        with patch.object(premium_content, 'membership', return_value='Free'), patch('backend.admin_catalogue.controls', return_value={'videos_open': True}):
            data = premium_content.series(db, {})['series']
        self.assertEqual([s['slug'] for s in data], [s[0] for s in labels])
        self.assertEqual([s['title'] for s in data], ['Giải đề 10 phút', 'Giải câu điểm 10', 'Mẹo làm bài'])
        self.assertEqual([v['accessible'] for v in data[1]['videos']], [True, True, True, False])
        self.assertEqual(db.execute("SELECT title FROM video_series WHERE slug='cau-phan-loai'").fetchone()[0], labels[1][1])
