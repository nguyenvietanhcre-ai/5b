"""Regression checks for assessment secrecy, publication and self-authored demos."""
import json
import re
import secrets
import tempfile
import time
import unittest
from collections import Counter
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena, ArenaError
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, seed_catalog
from backend.question_bank import arena_questions, published_version_ids, sample_problem
from test_platform_api import Client


ROOT = Path(__file__).resolve().parents[1]


class ReviewBankTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='review-bank-', dir=ROOT / 'work')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'bank.sqlite3'
        initialize(self.path)

    def seed(self):
        seed_catalog(self.path)

    def test_private_instances_are_not_the_public_offline_answer_catalog(self):
        self.seed()
        catalog = json.loads((ROOT / 'backend/learning-catalog.json').read_text(encoding='utf-8'))
        self.assertNotIn('questions', catalog)
        self.assertEqual(catalog['privateBankVersion'], 2)
        # Known public teaching examples. The complete browser export contract
        # is checked independently by test_bank_boundary.cjs, keeping this
        # backend regression runnable inside the Python-only runtime image.
        public_prompts = {(lesson['grade'], lesson['example']['text']) for lesson in catalog['lessons']}
        public_prompts.update((5,text) for text in (
            'So sánh 2,45 … 2,5.', 'So sánh 3,40 … 3,4.', 'So sánh 7,08 … 7,008.'))
        with connect(self.path) as db:
            rows = db.execute("SELECT q.grade_id,q.question_code,v.prompt_json FROM questions q JOIN question_versions v ON v.question_id=q.id WHERE q.question_code LIKE 'BANK2-%'").fetchall()
        self.assertEqual(len(rows), 960)
        assessed = {(r['grade_id'], json.loads(r['prompt_json'])[0]['text']) for r in rows}
        self.assertEqual(len(assessed), 960)
        self.assertFalse(assessed & public_prompts)
        self.assertTrue(all(re.fullmatch(r'BANK2-[A-F0-9]{32}', r['question_code']) for r in rows))
        other = Path(self.directory.name) / 'independent.sqlite3'
        initialize(other)
        seed_catalog(other)
        with connect(other) as db:
            other_codes = {r[0] for r in db.execute("SELECT question_code FROM questions WHERE question_code LIKE 'BANK2-%'")}
        self.assertFalse(other_codes & {r['question_code'] for r in rows})

    def test_legacy_retirement_keeps_content_and_finished_exam_history(self):
        with connect(self.path, True) as db:
            topic = db.execute("INSERT INTO topics(grade_id,title,theory_json,client_key) VALUES (1,'Cộng','[]','add')").lastrowid
            question = db.execute("INSERT INTO questions(grade_id,topic_id,question_code) VALUES (1,?,'BANK-1-add-0-0')", (topic,)).lastrowid
            version = db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,status,options_json) VALUES (?,1,1,1,?,?,?,'published',?)",
                (question, '[{"type":"text","text":"Bài cũ đã dùng"}]', '{"answer":"3"}', '[{"type":"text","text":"Lời giải cũ"}]', '["2","3"]')).lastrowid
            copy = db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,status,options_json) SELECT question_id,2,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,'published',options_json FROM question_versions WHERE id=?", (version,)).lastrowid
            private = db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,status,options_json) VALUES (?,3,1,1,?,?,?,'published',?)",
                (question, '[{"type":"text","text":"Bài do giáo viên sửa riêng"}]', '{"answer":"7"}', '[{"type":"text","text":"Lời giải mới"}]', '["6","7"]')).lastrowid
            student = db.execute("INSERT INTO students(student_code,full_name,grade_level) VALUES ('QA-HISTORY','Lịch sử thử',1)").lastrowid
            exam = db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,owner_student_id) VALUES ('QA-HISTORY','Bài đã làm',1,10,'published',?)", (student,)).lastrowid
            db.execute("INSERT INTO exam_items VALUES (?,1,?,1,'[\"2\",\"3\"]')", (exam, version))
            attempt = db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,submitted_at,earned_points,total_points,status) VALUES (?,?,'2026-11-01T00:00:00Z','2026-11-01T00:10:00Z','2026-11-01T00:01:00Z',1,1,'submitted')", (exam, student)).lastrowid
        self.seed()
        with connect(self.path) as db:
            row = db.execute('SELECT * FROM question_versions WHERE id=?', (version,)).fetchone()
            self.assertEqual(row['status'], 'retired')
            self.assertEqual(json.loads(row['grading_rule_json']), {'answer':'3'})
            self.assertEqual(json.loads(row['prompt_json'])[0]['text'], 'Bài cũ đã dùng')
            self.assertEqual(db.execute('SELECT question_version_id FROM exam_items WHERE exam_id=?', (exam,)).fetchone()[0], version)
            self.assertEqual(db.execute('SELECT earned_points FROM exam_attempts WHERE id=?', (attempt,)).fetchone()[0], 1)
            self.assertNotIn(version, published_version_ids(db, 1, 1))
            self.assertEqual(db.execute('SELECT status FROM question_versions WHERE id=?', (copy,)).fetchone()[0], 'retired')
            self.assertEqual(db.execute('SELECT status FROM question_versions WHERE id=?', (private,)).fetchone()[0], 'published')
            self.assertIn(private, published_version_ids(db, 1, 1))

    def test_restart_does_not_republish_withdrawn_bank_or_reseed(self):
        self.seed()
        with connect(self.path, True) as db:
            ids = {r[0] for r in db.execute('SELECT id FROM question_versions')}
            db.execute("UPDATE question_versions SET status='retired'")
        self.seed()
        with connect(self.path) as db:
            self.assertEqual(ids, {r[0] for r in db.execute('SELECT id FROM question_versions')})
            self.assertEqual(published_version_ids(db, 5, 1), [])
            with self.assertRaises(ArenaError) as error:
                arena_questions(db, 5, 0, 'all')
            self.assertEqual(error.exception.status, 503)
            arena = Arena()
            with patch.object(arena, '_questions', side_effect=AssertionError('Demo fallback forbidden')):
                with self.assertRaises(ArenaError):
                    arena.handle({'action':'create','name':'Thử ngân hàng','grade':5},
                                 question_provider=lambda g,d,s: arena_questions(db,g,d,s))
            self.assertEqual(arena.rooms, {})

    def test_exams_and_arena_use_current_published_versions_not_drafts_or_retired(self):
        self.seed()
        with connect(self.path, True) as db:
            old = db.execute("SELECT v.* FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=5 AND v.difficulty=1 LIMIT 1").fetchone()
            values = [old[k] for k in ('question_id','difficulty','curriculum_week','prompt_json','grading_rule_json','solution_steps_json','hints_json','options_json')]
            insert = 'INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,hints_json,options_json,status) VALUES (?,2,?,?,?,?,?,?,?,?)'
            draft = db.execute(insert, (*values, 'draft')).lastrowid
            self.assertIn(old['id'], published_version_ids(db, 5, 1))
            self.assertNotIn(draft, published_version_ids(db, 5, 1))
            db.execute("UPDATE question_versions SET status='retired' WHERE id=?", (old['id'],))
            db.execute("UPDATE question_versions SET status='published' WHERE id=?", (draft,))
            pool = published_version_ids(db, 5, 1)
            self.assertIn(draft, pool)
            self.assertNotIn(old['id'], pool)
            db.execute("UPDATE question_versions SET status='retired' WHERE question_id=?", (old['question_id'],))
            for _ in range(8):
                chosen = arena_questions(db, 5, 0, 'all')
                self.assertFalse({old['id'],draft} & {q['questionVersionId'] for q in chosen})
                self.assertTrue(all(q['questionVersionId'] in published_version_ids(db,5,q['difficulty']+1) for q in chosen))
            self.assertEqual(published_version_ids(db,5,1,exact_week=53), [])

    def test_active_arena_keeps_snapshot_and_discloses_only_current_question(self):
        self.seed()
        with connect(self.path, True) as db:
            questions = arena_questions(db, 5, 0, 'all')
            arena = Arena()
            owner = arena.handle({'action':'create','name':'Chủ phòng','grade':5}, question_provider=lambda *_: questions)
            friend = arena.handle({'action':'join','code':owner['code'],'name':'Bạn thử','grade':5})
            room = arena.rooms[owner['code']]
            original_text = room['questions'][0]['text']
            questions[0]['text'] = 'Provider subsequently changed'
            self.assertEqual(room['questions'][0]['text'], original_text)
            db.execute("UPDATE question_versions SET status='retired'")
            arena.handle({**owner,'action':'accept'})
            room['readyAt'] = time.time() - 1
            battle = arena.handle({**owner,'action':'state'})['battle']
            self.assertEqual(battle['questions'][0]['text'], original_text)
            self.assertEqual(len(battle['questions']), 20)
            self.assertTrue(all('answer' not in q and 'steps' not in q for q in battle['questions']))
            self.assertTrue(all('text' not in q and 'options' not in q for q in battle['questions'][1:]))
            self.assertIn('token', friend)

    def test_authenticated_exam_keeps_version_after_withdrawal_and_new_work_is_blocked(self):
        self.seed()
        server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        client = Client(server)
        client.call('auth/register', {'login':'bank-'+secrets.token_hex(8),
                    'password':secrets.token_urlsafe(20), 'name':'Học sinh thử',
                    'birthYear':academic()[0]-10})
        exam = client.call('exams', {'requestKey':secrets.token_hex(12),'count':3,'topic':'decimal'})['exam']
        self.assertIn('Mẫu tự biên soạn', exam['title'])
        with connect(self.path, True) as db:
            before = [tuple(r) for r in db.execute('SELECT i.question_version_id,v.prompt_json,v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=? ORDER BY i.position', (exam['id'],))]
            db.execute("UPDATE question_versions SET status='retired'")
        self.seed()
        resumed = client.call('exams/'+exam['id'])['exam']
        self.assertEqual(resumed['questions'], exam['questions'])
        with connect(self.path) as db:
            after = [tuple(r) for r in db.execute('SELECT i.question_version_id,v.prompt_json,v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=? ORDER BY i.position', (exam['id'],))]
        self.assertEqual(before, after)
        with self.assertRaises(APIError) as error:
            client.call('exams', {'requestKey':secrets.token_hex(12),'count':3,'topic':'decimal'})
        self.assertIn('Chưa đủ câu hỏi', str(error.exception))
        with self.assertRaises(APIError) as error:
            client.call('arena', {'action':'create','scope':'all'})
        self.assertEqual(error.exception.status, 503)
        self.assertEqual(server.arena.rooms, {})

    def test_samples_are_unique_balanced_and_exact_with_elementary_steps(self):
        self.seed()
        with connect(self.path) as db:
            rows = db.execute("SELECT q.grade_id,t.client_key topic,v.* FROM questions q JOIN topics t ON t.id=q.topic_id JOIN question_versions v ON v.question_id=q.id WHERE q.question_code LIKE 'BANK2-%'").fetchall()
        comparison = Counter()
        for row in rows:
            answer = str(json.loads(row['grading_rule_json'])['answer'])
            options = json.loads(row['options_json'])
            self.assertEqual(len(set(options)), len(options))
            self.assertIn(answer, options)
            self.assertTrue(json.loads(row['solution_steps_json']))
            self.assertIn('Mẫu tự biên soạn', row['hints_json'])
            if row['topic'] in ('decimal', 'compare'):
                comparison[row['grade_id'],row['difficulty'],answer] += 1
            if row['grade_id'] == 1:
                self.assertNotIn('nhân', json.loads(row['prompt_json'])[0]['text'])
                if row['topic'] != 'compare':
                    self.assertTrue(0 <= Fraction(answer) <= 20)
        for grade in (1,5):
            for level in range(1,5):
                self.assertEqual([comparison[grade,level,s] for s in ('<','=','>')], [4,4,4])
        # Verify arithmetic independently from generated solution/answer strings.
        rng = secrets.SystemRandom()
        for level in range(4):
            for variant in range(12):
                decimal = sample_problem(5,'decimal',level,variant,rng)
                expr = decimal['text'].split(': ',1)[1].rstrip('.')
                left, right = expr.split(' … ')
                def evaluate(value):
                    terms = re.findall(r'\d+(?:,\d+)?|[+×−()]', value)
                    numeric = [Fraction(t.replace(',','.')) if re.fullmatch(r'\d+(?:,\d+)?',t) else t for t in terms]
                    if '+' in numeric:
                        return numeric[1] + numeric[3]
                    if '×' in numeric:
                        return numeric[1] * numeric[3] - numeric[5]
                    return numeric[0]
                l, r = evaluate(left), evaluate(right)
                self.assertEqual(decimal['answer'], '<' if l < r else '>' if l > r else '=')
                fraction = sample_problem(4,'fraction',level,variant,rng)
                text = fraction['text']
                numbers = list(map(int,re.findall(r'\d+',text)))
                if level == 0 or level == 2:
                    a,b,c,d = numbers
                    expected = Fraction(a,b) + Fraction(c,d)
                elif level == 1:
                    whole,a,b,c,d = numbers
                    expected = whole - Fraction(a,b) - Fraction(c,d)
                else:
                    length, _, d1, _, d2 = numbers
                    expected = length * (1-Fraction(1,d1)-Fraction(1,d2))
                self.assertEqual(Fraction(fraction['answer']), expected)


if __name__ == '__main__':
    unittest.main()
