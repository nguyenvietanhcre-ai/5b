"""Approved grade-five discovery retirement. Explicit activation; never delete content."""
import json
from . import platform_api as api

SCHEMA = '''CREATE TABLE IF NOT EXISTS content_retirement_policy(grade INTEGER PRIMARY KEY CHECK(grade=5),enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),manifest_json TEXT NOT NULL,applied_at TEXT NOT NULL)'''

def retired(db, grade):
    if grade != 5 or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='content_retirement_policy'").fetchone():return False
    row=db.execute('SELECT enabled FROM content_retirement_policy WHERE grade=5').fetchone()
    return bool(row and row[0])

def manifest(db):
    return {'scope':'approved-A-grade5-only','topics':[r[0] for r in db.execute('SELECT id FROM topics WHERE grade_id=5 ORDER BY id')],
            'lessons':[r[0] for r in db.execute('SELECT id FROM lessons WHERE grade_id=5 ORDER BY id')],
            'questions':[r[0] for r in db.execute('SELECT id FROM questions WHERE grade_id=5 ORDER BY id')],
            'publishedVersions':[r[0] for r in db.execute("SELECT v.id FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.status='published' ORDER BY v.id")],
            'action':'exclude legacy grade5 from discovery/new allocation; preserve rows/status/title/body/history; grades1-4 unchanged'}

def activate(db, expected=None, *, enabled=True):
    snapshot=manifest(db)
    if expected is not None and expected!=snapshot:raise api.APIError('Danh sách ngừng cấp đã đổi; cần rà lại manifest.',409)
    db.execute(SCHEMA)
    old=db.execute('SELECT manifest_json FROM content_retirement_policy WHERE grade=5').fetchone()
    if old and enabled and json.loads(old[0])!=snapshot:raise api.APIError('Manifest đã áp khác nguồn; không tự mở rộng phạm vi.',409)
    db.execute('INSERT INTO content_retirement_policy VALUES(5,?,?,?) ON CONFLICT(grade) DO UPDATE SET enabled=excluded.enabled',
               (int(enabled),api.packed(snapshot),api.stamp()))
    return snapshot
