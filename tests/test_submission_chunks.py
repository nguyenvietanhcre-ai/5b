"""Homework storage preserves the10MB contract with bounded, atomic private chunks."""
import base64
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.database import initialize
from backend.platform_api import APIError, connect
from backend.zoom_classroom import FILE_CHUNK_SIZE, MAX_FILE_SIZE, file_payload, submit_file


class SubmissionChunkTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / 'work'
        scratch.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='submission-chunks-', dir=scratch)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'submissions.sqlite3'
        initialize(self.path)
        self.session = {'account_id': 101, 'student_id': 101}
        with connect(self.path, True) as db:
            for identity in (101, 102):
                db.execute('INSERT INTO accounts(id,account_code,login_identifier,birth_year,invite_code,created_at) '
                           'VALUES (?,?,?,?,?,?)', (identity, 'CHUNK-' + str(identity), 'chunk-' + str(identity),
                                                   2016, 'CHUNKINV' + str(identity), '2026-01-01T00:00:00Z'))
                db.execute('INSERT INTO students(id,student_code,full_name,grade_level,account_id) VALUES (?,?,?,?,?)',
                           (identity, 'CHUNK-STUDENT-' + str(identity), 'Học sinh thử', 5, identity))
            db.execute("INSERT INTO academic_years VALUES (101,'Chunk QA','2026-07-01','2026-09-05','2027-06-30')")
            db.execute("INSERT INTO teachers(id,full_name) VALUES (101,'Giáo viên thử')")
            db.execute("INSERT INTO online_classes(id,teacher_id,grade_id,academic_year_id,name) VALUES (101,101,5,101,'Lớp thử')")
            for identity in (101, 102):
                db.execute("INSERT INTO class_enrollments(id,student_id,class_id,joined_at) VALUES (?,?,101,'2000-01-01T00:00:00Z')",
                           (identity, identity))
                db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal','2000-01-01T00:00:00Z')",
                           (identity, identity))
            db.execute("INSERT INTO class_sessions(id,class_id,title,starts_at) VALUES (101,101,'Buổi thử','2026-11-12T12:00:00Z')")
            db.execute("INSERT INTO class_assignments(id,session_id,title) VALUES (101,101,'Bài thử')")

    @staticmethod
    def pdf(size):
        prefix = b'%PDF-1.7\nChunk fixture\n'
        return prefix + b'0123456789ABCDEF' * ((size - len(prefix)) // 16) + b'X' * ((size - len(prefix)) % 16)

    @staticmethod
    def body(content, filename='bai-lam.pdf'):
        return {'filename': filename, 'mimeType': 'application/pdf',
                'data': base64.b64encode(content).decode('ascii')}

    def upload(self, content, filename='bai-lam.pdf'):
        with connect(self.path, True) as db:
            return submit_file(db, self.session, 101, 101, self.body(content, filename))['submission']

    def test_ten_megabyte_roundtrip_uses_bounded_rows_and_preserves_download(self):
        content = self.pdf(MAX_FILE_SIZE)
        submission = self.upload(content)
        with connect(self.path) as db:
            parent = db.execute('SELECT size,length(content) inline_size,digest FROM class_submissions WHERE id=?',
                                (submission['id'],)).fetchone()
            self.assertEqual(parent['size'], MAX_FILE_SIZE)
            self.assertEqual(parent['inline_size'], 0)
            self.assertEqual(parent['digest'], hashlib.sha256(content).hexdigest())
            rows = db.execute('SELECT position,length(content) size FROM class_submission_chunks WHERE submission_id=? ORDER BY position',
                              (submission['id'],)).fetchall()
            self.assertEqual([row['position'] for row in rows], list(range(10)))
            self.assertEqual([row['size'] for row in rows], [FILE_CHUNK_SIZE] * 10)
            payload = file_payload(db, submission['id'], session=self.session)
            self.assertEqual(payload['_binary'], content)
            self.assertEqual(payload['contentType'], 'application/pdf')
            self.assertIn("filename*=UTF-8''bai-lam.pdf", payload['disposition'])
            self.assertEqual(file_payload(db, submission['id'], user={'role': 'teacher', 'teacher_id': 101})['_binary'], content)

    def test_duplicate_upload_is_idempotent_and_versions_keep_prior_chunks(self):
        content = self.pdf(FILE_CHUNK_SIZE + 19)
        first = self.upload(content)
        with connect(self.path) as db:
            revision = db.execute('SELECT revision FROM class_sessions WHERE id=101').fetchone()[0]
        duplicate = self.upload(content)
        self.assertEqual(first['id'], duplicate['id'])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM class_submissions').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM class_submission_chunks').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT revision FROM class_sessions WHERE id=101').fetchone()[0], revision)
        newer = self.upload(content, 'bai-lam-moi.pdf')
        self.assertGreater(newer['id'], first['id'])
        with connect(self.path) as db:
            self.assertEqual(file_payload(db, first['id'], session=self.session)['_binary'], content)
            self.assertEqual(file_payload(db, newer['id'], session=self.session)['_binary'], content)

    def test_wrong_owner_and_unassigned_teacher_are_denied_before_bytes_are_read(self):
        submission = self.upload(self.pdf(FILE_CHUNK_SIZE + 7))
        # Even damaged storage must not disclose a corruption error to another account.
        with connect(self.path, True) as db:
            db.execute('DELETE FROM class_submission_chunks WHERE submission_id=? AND position=1', (submission['id'],))
        with connect(self.path) as db:
            statements = []
            db.set_trace_callback(statements.append)
            for credentials in ({'session': {'account_id': 102, 'student_id': 102}},
                                {'user': {'role': 'teacher', 'teacher_id': 999}}, {}):
                with self.subTest(credentials=list(credentials)), self.assertRaises(APIError) as denied:
                    file_payload(db, submission['id'], **credentials)
                self.assertEqual(denied.exception.status, 403)
            self.assertFalse(any('FROM class_submission_chunks' in sql or
                                 'SELECT content FROM class_submissions' in sql for sql in statements))
            with self.assertRaises(APIError) as owner:
                file_payload(db, submission['id'], session=self.session)
            self.assertEqual(owner.exception.status, 503)

    def test_chunk_failure_caught_by_caller_rolls_back_parent_chunks_and_revision(self):
        content = self.pdf(FILE_CHUNK_SIZE + 17)
        with connect(self.path, True) as db:
            before = db.execute('SELECT revision FROM class_sessions WHERE id=101').fetchone()[0]
            db.execute("CREATE TRIGGER qa_fail_second_chunk BEFORE INSERT ON class_submission_chunks "
                       "WHEN NEW.position=1 BEGIN SELECT RAISE(ABORT,'QA interrupted chunk write'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                submit_file(db, self.session, 101, 101, self.body(content))
            # Deliberately keep using and commit the outer transaction.
            self.assertEqual(db.execute('SELECT count(*) FROM class_submissions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM class_submission_chunks').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT revision FROM class_sessions WHERE id=101').fetchone()[0], before)
            db.execute("UPDATE teachers SET bio='Outer transaction still usable' WHERE id=101")
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM class_submissions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT bio FROM teachers WHERE id=101').fetchone()[0], 'Outer transaction still usable')

    def test_missing_reordered_or_tampered_chunks_fail_integrity_validation(self):
        content = self.pdf(FILE_CHUNK_SIZE + 13)
        submission = self.upload(content)
        with connect(self.path, True) as db:
            original = db.execute('SELECT content FROM class_submission_chunks WHERE submission_id=? AND position=1',
                                  (submission['id'],)).fetchone()[0]
            for change, params in [
                ('UPDATE class_submission_chunks SET position=2 WHERE submission_id=? AND position=1', (submission['id'],)),
                ('UPDATE class_submission_chunks SET content=? WHERE submission_id=? AND position=1', (b'Z' * len(original), submission['id'])),
                ('DELETE FROM class_submission_chunks WHERE submission_id=? AND position=1', (submission['id'],)),
            ]:
                db.execute('SAVEPOINT corrupt_fixture')
                db.execute(change, params)
                with self.assertRaises(APIError) as corrupt:
                    file_payload(db, submission['id'], session=self.session)
                self.assertEqual(corrupt.exception.status, 503)
                db.execute('ROLLBACK TO corrupt_fixture')
                db.execute('RELEASE corrupt_fixture')
            self.assertEqual(file_payload(db, submission['id'], session=self.session)['_binary'], content)

    def test_legacy_inline_file_is_read_unchanged_and_never_rewritten(self):
        content = self.pdf(81)
        with connect(self.path, True) as db:
            identity = db.execute('INSERT INTO class_submissions(assignment_id,student_id,filename,mime_type,size,content,digest,submitted_at) '
                                  'VALUES (101,101,?,?,?,?,?,?)',
                                  ('legacy.pdf', 'application/pdf', len(content), content,
                                   hashlib.sha256(content).hexdigest(), '2026-11-12T00:00:00Z')).lastrowid
        initialize(self.path)
        with connect(self.path) as db:
            self.assertEqual(file_payload(db, identity, session=self.session)['_binary'], content)
            self.assertEqual(bytes(db.execute('SELECT content FROM class_submissions WHERE id=?', (identity,)).fetchone()[0]), content)
            self.assertEqual(db.execute('SELECT count(*) FROM class_submission_chunks WHERE submission_id=?', (identity,)).fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
