"""Account administration behavior, including historical data and access revocation."""
import json
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, now, seed_catalog, stamp
from backend.staff_api import create_first_admin
from test_platform_api import Client as StudentClient
from test_staff_api import StaffClient


class StaffAccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='staff-account-tests-', dir=work)
        cls.template = Path(cls.directory.name) / 'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)
        cls.admin_password = secrets.token_urlsafe(20)
        create_first_admin(cls.template, 'admin', 'Quản trị thử', cls.admin_password)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path = Path(self.directory.name) / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.template)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        self.admin = StaffClient(self.server)
        self.admin.call('login', {'login': 'admin', 'password': self.admin_password})

    def body(self, **changes):
        return {'login': 'account-' + secrets.token_hex(5), 'name': 'Mầm xanh',
                'birthYear': academic()[0] - 10, 'password': secrets.token_urlsafe(20),
                'status': 'active', **changes}

    def create(self, **changes):
        body = self.body(**changes)
        result = self.admin.call('accounts', body)
        self.assertTrue(result['saved'])
        self.assertNotIn(body['password'], json.dumps(result))
        return result['account'], body

    def update(self, row, body, **changes):
        return self.admin.call('accounts/' + str(row['id']), {
            'revision': row['revision'], 'login': row['login_identifier'],
            'name': row['full_name'], 'status': row['status'], 'password': '', **changes})['account']

    def delete(self, row, **changes):
        return self.admin.call(f'accounts/{row["id"]}/delete', {
            'revision': row['revision'], 'confirmLogin': row['login_identifier'], **changes})['account']

    def assert_error(self, status, client, path, body=None):
        with self.assertRaises(APIError) as caught:
            client.call(path, body)
        self.assertEqual(caught.exception.status, status)

    def login(self, login, password):
        client = StudentClient(self.server)
        state = client.call('auth/login', {'login': login, 'password': password})
        self.assertTrue(state['authenticated'])
        return client, state

    def test_create_initializes_one_student_and_keeps_admin_session(self):
        row, body = self.create(login='New.Student')
        self.assertEqual(row['login_identifier'], 'new.student')
        self.assertEqual(row['full_name'], body['name'])
        self.assertEqual(row['grade_level'], 5)
        self.assertEqual(row['revision'], 1)
        self.assertIsNone(row['deleted_at'])
        self.assertEqual((row['membership'], row['mascot'], row['points']), ('Free', 'sprout', 1000))
        self.assertIsNone(row['membership_expires_at'])
        self.assertEqual(self.admin.call('session')['user']['role'], 'admin')
        self.assertTrue(self.admin.headers['Cookie'].startswith('5bmath_staff='))
        student, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual(state['account']['id'], row['id'])
        self.assertEqual(state['state']['grade'], 5)
        self.assertEqual(state['name'], 'Mầm xanh')
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM students WHERE account_id=?', (row['id'],)).fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM student_grades WHERE student_id=?', (row['student_id'],)).fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT m.name FROM student_companions c JOIN mascots m ON m.id=c.mascot_id WHERE c.student_id=?',
                                        (row['student_id'],)).fetchone()[0], 'Mầm Sách')
            self.assertIsNotNone(db.execute('SELECT 1 FROM learning_preferences WHERE student_id=?', (row['student_id'],)).fetchone())
            credential = db.execute('SELECT password_hash FROM accounts WHERE id=?', (row['id'],)).fetchone()[0]
            self.assertTrue(credential.startswith('pbkdf2_sha256$600000$'))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_invalid_or_duplicate_create_rolls_back_without_disclosing_credentials(self):
        row, body = self.create()
        with connect(self.path) as db:
            before = tuple(db.execute('SELECT (SELECT count(*) FROM accounts),(SELECT count(*) FROM students),(SELECT count(*) FROM staff_audit_log)').fetchone())
        self.assert_error(409, self.admin, 'accounts', {**body, 'login': row['login_identifier'].upper()})
        self.assert_error(409, self.admin, 'accounts', self.body(login='admin'))
        for changes in ({'login': 'bad name'}, {'name': '0912345678'},
                        {'birthYear': academic()[0] - 5}, {'birthYear': True},
                        {'password': 'short'}, {'status': 'deleted'}):
            self.assert_error(400, self.admin, 'accounts', self.body(**changes))
        with connect(self.path) as db:
            after = tuple(db.execute('SELECT (SELECT count(*) FROM accounts),(SELECT count(*) FROM students),(SELECT count(*) FROM staff_audit_log)').fetchone())
            self.assertEqual(after, before)
            audit = '\n'.join(r[0] for r in db.execute('SELECT summary FROM staff_audit_log'))
            self.assertNotIn(body['password'], audit)

    def test_edit_login_name_and_password_revoke_old_access_and_reject_stale_revision(self):
        row, body = self.create()
        student, state = self.login(row['login_identifier'], body['password'])
        second, _ = self.login(row['login_identifier'], body['password'])
        new_password = secrets.token_urlsafe(20)
        changed = self.update(row, body, login='changed-' + secrets.token_hex(5),
                              name='Vườn nhỏ', password=new_password)
        self.assertEqual(changed['revision'], row['revision'] + 1)
        self.assertEqual(changed['full_name'], 'Vườn nhỏ')
        self.assertFalse(student.call('session')['authenticated'])
        self.assertFalse(second.call('session')['authenticated'])
        self.assert_error(401, StudentClient(self.server), 'auth/login', {
            'login': row['login_identifier'], 'password': body['password']})
        self.assert_error(401, StudentClient(self.server), 'auth/login', {
            'login': changed['login_identifier'], 'password': body['password']})
        fresh, state = self.login(changed['login_identifier'], new_password)
        self.assertEqual(state['name'], 'Vườn nhỏ')
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', {
            'revision': row['revision'], 'login': row['login_identifier'],
            'name': 'Cũ', 'password': '', 'status': 'active'})
        corrected = self.update(changed, body, birthYear=body['birthYear'] + 1)
        preserved = self.admin.call('accounts?q=' + changed['login_identifier'])['rows'][0]
        self.assertEqual(preserved['full_name'], 'Vườn nhỏ')
        self.assertEqual(preserved['birth_year'], body['birthYear'] + 1)
        self.assertEqual(preserved['revision'], corrected['revision'])
        self.assertFalse(fresh.call('session')['authenticated'])

    def test_suspend_and_reopen_require_fresh_revision_and_new_login(self):
        row, body = self.create()
        student, _ = self.login(row['login_identifier'], body['password'])
        room = student.call('arena', {'action': 'create', 'public': False})
        locked = self.update(row, body, status='suspended')
        self.assertFalse(student.call('session')['authenticated'])
        with connect(self.path) as db:
            member = db.execute('SELECT revoked_at FROM arena_members WHERE student_id=?', (row['student_id'],)).fetchone()
            self.assertIsNotNone(member)
            self.assertIsNotNone(member['revoked_at'])
        self.assert_error(401, StudentClient(self.server), 'auth/login', {
            'login': row['login_identifier'], 'password': body['password']})
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', {
            'revision': row['revision'], 'status': 'active'})
        opened = self.update(locked, body, status='active')
        self.assertEqual(opened['status'], 'active')
        self.assertFalse(student.call('session')['authenticated'])
        reopened, _ = self.login(row['login_identifier'], body['password'])
        self.assert_error(403, reopened, 'arena', {'action': 'state', **room})
        # Existing status-only clients still receive conflict checks.
        self.admin.call(f'accounts/{row["id"]}', {'status': 'suspended', 'expectedStatus': 'active'})
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', {'status': 'active', 'expectedStatus': 'active'})

    def test_delete_and_restore_preserve_history_but_end_class_and_room_access(self):
        row, body = self.create()
        student, state = self.login(row['login_identifier'], body['password'])
        lesson = state['lessons'][0]['id']
        student.call(f'lessons/{lesson}/complete', {})
        payment = student.call('payments', {})['order']
        personnel = self.admin.call('users', {'login': 'teacher-' + secrets.token_hex(4),
            'fullName': 'Giáo viên thử', 'role': 'teacher', 'status': 'active',
            'password': secrets.token_urlsafe(20)})['users']
        teacher = next(user for user in personnel if user['role'] == 'teacher')
        classroom = self.admin.call('classes', {'name': 'Lớp kiểm thử', 'grade': 5,
            'teacherId': teacher['teacher_id'], 'status': 'active', 'schedule': '',
            'curriculum': '', 'meetingUrl': ''})['class']
        self.admin.call(f'classes/{classroom["id"]}/enroll', {'action': 'enroll', 'studentId': row['student_id']})
        room = student.call('arena', {'action': 'create', 'public': False})
        with connect(self.path, True) as db:
            duel = db.execute('SELECT duel_id FROM arena_members WHERE student_id=?', (row['student_id'],)).fetchone()[0]
            fee = db.execute("INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,'2026-11',100000)",
                             (classroom['id'], row['student_id'])).lastrowid
        row = self.admin.call('accounts?q=' + row['login_identifier'])['rows'][0]
        self.assert_error(400, self.admin, f'accounts/{row["id"]}/delete', {
            'revision': row['revision'], 'confirmLogin': 'wrong-account'})
        self.assertTrue(student.call('session')['authenticated'])
        deleted = self.delete(row)
        self.assertIsNotNone(deleted['deleted_at'])
        self.assertEqual(deleted['status'], 'suspended')
        self.assertFalse(student.call('session')['authenticated'])
        self.assert_error(401, StudentClient(self.server), 'auth/login', {
            'login': row['login_identifier'], 'password': body['password']})
        self.assertEqual(self.admin.call('accounts?q=' + row['login_identifier'])['total'], 0)
        self.assertEqual(self.admin.call('accounts?status=deleted&q=' + row['login_identifier'])['total'], 1)
        self.assert_error(409, self.admin, f'accounts/{row["id"]}/restore', {'revision': row['revision']})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM auth_sessions WHERE account_id=?', (row['id'],)).fetchone()[0], 0)
            member = db.execute('SELECT duel_id,revoked_at FROM arena_members WHERE student_id=?', (row['student_id'],)).fetchone()
            self.assertIsNotNone(member)
            self.assertEqual(member['duel_id'], duel)
            self.assertIsNotNone(member['revoked_at'])
            self.assertEqual(db.execute('SELECT status FROM students WHERE id=?', (row['student_id'],)).fetchone()[0], 'inactive')
            self.assertIsNotNone(db.execute('SELECT left_at FROM class_enrollments WHERE student_id=?', (row['student_id'],)).fetchone()[0])
            self.assertIsNotNone(db.execute('SELECT ends_at FROM access_entitlements WHERE account_id=?', (row['id'],)).fetchone()[0])
            self.assertIsNotNone(db.execute('SELECT 1 FROM lesson_progress WHERE student_id=?', (row['student_id'],)).fetchone())
            self.assertIsNotNone(db.execute('SELECT 1 FROM payment_orders WHERE id=?', (payment['id'],)).fetchone())
            self.assertIsNotNone(db.execute('SELECT 1 FROM class_fees WHERE id=?', (fee,)).fetchone())
            self.assertIsNotNone(db.execute('SELECT 1 FROM duels WHERE id=?', (duel,)).fetchone())
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        restored = self.admin.call(f'accounts/{row["id"]}/restore', {'revision': deleted['revision']})['account']
        self.assertIsNone(restored['deleted_at'])
        self.assertEqual(restored['status'], 'suspended')
        self.assert_error(401, StudentClient(self.server), 'auth/login', {
            'login': row['login_identifier'], 'password': body['password']})
        self.update(restored, body, status='active')
        reopened, state = self.login(row['login_identifier'], body['password'])
        self.assertIn(lesson, state['state']['completed'])
        self.assert_error(403, reopened, 'arena', {'action': 'state', **room})
        self.assert_error(403, reopened, f'classes/{classroom["id"]}')
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM class_enrollments WHERE student_id=? AND left_at IS NULL', (row['student_id'],)).fetchone()[0], 0)

    def test_account_routes_enforce_admin_csrf_and_origin(self):
        row, body = self.create()
        stranger = StaffClient(self.server)
        self.assert_error(401, stranger, 'accounts')
        self.assert_error(401, stranger, 'accounts', self.body())
        credentials = {'login': 'teacher-' + secrets.token_hex(4), 'password': secrets.token_urlsafe(20)}
        self.admin.call('users', {**credentials, 'fullName': 'Giáo viên thử', 'role': 'teacher', 'status': 'active'})
        teacher = StaffClient(self.server)
        teacher.call('login', credentials)
        for path, data in [('accounts', None), ('accounts', self.body()),
                           (f'accounts/{row["id"]}', {'revision': row['revision'], 'status': 'suspended'}),
                           (f'accounts/{row["id"]}', {'revision': row['revision'], 'birthYear': body['birthYear'] + 1,
                               'membership': 'SVip', 'membershipExpiresAt': None, 'mascot': 'horse', 'points': 2000}),
                           (f'accounts/{row["id"]}/delete', {'revision': row['revision'], 'confirmLogin': row['login_identifier']}),
                           (f'accounts/{row["id"]}/restore', {'revision': row['revision']})]:
            self.assert_error(403, teacher, path, data)
        saved_csrf = self.admin.csrf
        self.admin.csrf = 'invalid'
        self.assert_error(403, self.admin, 'accounts', self.body())
        self.assert_error(403, self.admin, f'accounts/{row["id"]}/delete', {'revision': row['revision'], 'confirmLogin': row['login_identifier']})
        self.admin.csrf = saved_csrf
        self.admin.headers['Origin'] = 'https://untrusted.example'
        self.assert_error(403, self.admin, 'accounts', self.body())

    def test_student_profile_changes_conflict_with_an_open_admin_form(self):
        row, body = self.create()
        student, _ = self.login(row['login_identifier'], body['password'])
        student.call('profile', {'name': 'Lá nhỏ'})
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', {
            'revision': row['revision'], 'login': row['login_identifier'],
            'name': 'Tên cũ', 'password': '', 'status': 'active'})
        current = self.admin.call('accounts?q=' + row['login_identifier'])['rows'][0]
        self.assertEqual(current['full_name'], 'Lá nhỏ')
        self.assertEqual(current['revision'], row['revision'] + 1)
        public_body = self.body(login='admin')
        self.assert_error(409, StudentClient(self.server), 'auth/register', public_body)

    def test_status_search_grade_and_pagination_counts_agree(self):
        row, body = self.create(login='page-student-00')
        # A batch of independent fixture accounts makes the 25-row boundary real.
        with connect(self.path, True) as db:
            for index in range(1, 27):
                aid = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash,status) '
                    'SELECT ?,?,birth_year,?,?,password_hash,? FROM accounts WHERE id=?',
                    (f'FIX-{index}', f'page-student-{index:02}', f'INV-{index}', stamp(),
                     'suspended' if index == 26 else 'active', row['id'])).lastrowid
                db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,5,?)',
                           (f'FIX-HS-{index}', 'Mầm xanh', aid))
        first = self.admin.call('accounts?q=page-student-&grade=5')
        second = self.admin.call('accounts?q=page-student-&grade=5&page=2')
        self.assertEqual((first['total'], len(first['rows']), len(second['rows'])), (27, 25, 2))
        self.assertFalse({value['id'] for value in first['rows']} & {value['id'] for value in second['rows']})
        self.assertEqual(self.admin.call('accounts?q=page-student-&status=suspended')['total'], 1)
        self.assertEqual(self.admin.call('accounts?q=page-student-&status=active')['total'], 26)
        self.assertEqual(self.admin.call('accounts?q=page-student-&grade=4')['total'], 0)
        self.delete(row)
        self.assertEqual(self.admin.call('accounts?q=page-student-&status=all')['total'], 26)
        self.assertEqual(self.admin.call('accounts?q=page-student-&status=deleted')['total'], 1)
        self.assertEqual(self.admin.call('accounts?q=page-student-&status=active')['total'], 25)
        self.assertEqual(self.admin.call('accounts?q=page-student-&page=2')['rows'][-1]['login_identifier'], 'page-student-01')
        self.assert_error(400, self.admin, 'accounts?status=invalid')

    def test_admin_corrects_birth_and_current_grade_without_rewriting_history(self):
        row, body = self.create()
        student, state = self.login(row['login_identifier'], body['password'])
        self.assert_error(400, student, 'profile', {'name': 'Mầm mới', 'birthYear': body['birthYear'] + 1})
        lesson = state['lessons'][0]['id']
        student.call(f'lessons/{lesson}/complete', {})
        exam = student.call('exams', {'requestKey': secrets.token_hex(12), 'count': 3, 'topic': 'decimal'})['exam']
        room = student.call('arena', {'action': 'create', 'public': False})
        year = academic()[0]
        with connect(self.path, True) as db:
            old_year = db.execute('INSERT INTO academic_years(label,grade_effective_from,instruction_starts_on,ends_on) VALUES (?,?,?,?)',
                (f'{year-1}–{year}', f'{year-1}-07-01', f'{year-1}-09-05', f'{year}-06-30')).lastrowid
            db.execute('INSERT INTO student_grades VALUES (?,?,3)', (row['student_id'], old_year))
        corrected = self.update(row, body, birthYear=body['birthYear'] + 1)
        self.assertEqual(corrected['birth_year'], body['birthYear'] + 1)
        self.assertEqual(corrected['grade_level'], 4)
        self.assertFalse(student.call('session')['authenticated'])
        reopened, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual((state['state']['birthYear'], state['state']['grade']), (body['birthYear'] + 1, 4))
        self.assertIn(lesson, state['state']['completed'])
        self.assertEqual(reopened.call('exams/' + str(exam['id']))['exam']['grade'], 5)
        self.assert_error(403, reopened, 'arena', {'action': 'state', **room})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT grade_level FROM students WHERE id=?', (row['student_id'],)).fetchone()[0], 4)
            self.assertEqual(db.execute('SELECT grade_id FROM student_grades WHERE student_id=? AND academic_year_id=?',
                (row['student_id'], old_year)).fetchone()[0], 3)
            self.assertEqual(db.execute('SELECT g.grade_id FROM student_grades g JOIN academic_years y ON y.id=g.academic_year_id '
                'WHERE g.student_id=? AND y.label=?', (row['student_id'], f'{year}–{year+1}')).fetchone()[0], 4)
            self.assertEqual(db.execute('SELECT grade_level FROM exams WHERE id=?', (exam['id'],)).fetchone()[0], 5)
            summary = db.execute("SELECT summary FROM staff_audit_log WHERE entity='account' AND entity_id=? ORDER BY id DESC LIMIT 1",
                (str(row['id']),)).fetchone()[0]
            self.assertIn(str(body['birthYear']), summary)
            self.assertIn(str(body['birthYear'] + 1), summary)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        with self.assertRaises(sqlite3.IntegrityError), connect(self.path, True) as db:
            db.execute('UPDATE accounts SET birth_year=birth_year+1 WHERE id=?', (row['id'],))

    def test_admin_manual_plans_change_real_limits_class_access_and_expire_without_rewards(self):
        inviter, inviter_body = self.create()
        _, inviter_state = self.login(inviter['login_identifier'], inviter_body['password'])
        student = StudentClient(self.server)
        body = self.body(inviteCode=inviter_state['state']['inviteCode'])
        state = student.call('auth/register', body)
        row = self.admin.call('accounts?q=' + body['login'])['rows'][0]
        self.assertEqual(state['account']['membership'], 'Free')
        self.assertEqual(state['account']['usage']['bot']['limit'], 5)
        for _ in range(5):
            student.call('bot/start', {'requestKey': secrets.token_hex(12)})
        self.assert_error(429, student, 'bot/start', {'requestKey': secrets.token_hex(12)})

        vip_expiry = now() + timedelta(hours=1)
        row = self.update(row, body, membership='VIP', membershipExpiresAt=stamp(vip_expiry))
        student, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual((row['membership'], row['membership_expires_at']), ('VIP', stamp(vip_expiry)))
        self.assertEqual(state['account']['membership'], 'VIP')
        self.assertIsNone(state['account']['usage']['bot']['limit'])
        student.call('bot/start', {'requestKey': secrets.token_hex(12)})
        with patch('backend.platform_api.now', return_value=vip_expiry + timedelta(seconds=1)):
            expired = student.call('session')
            self.assertEqual(expired['account']['membership'], 'Free')
            self.assertEqual(expired['account']['usage']['bot']['limit'], 5)

        # Keep an existing class assignment to distinguish access from enrollment.
        with connect(self.path, True) as db:
            teacher = db.execute("INSERT INTO teachers(full_name) VALUES ('Giáo viên thử')").lastrowid
            academic_year = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (row['student_id'],)).fetchone()[0]
            classroom = db.execute("INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,schedule,curriculum) VALUES (?,5,?,'Lớp quyền học','','')",
                                   (teacher, academic_year)).lastrowid
            enrollment = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                                    (row['student_id'], classroom, stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                       (row['id'], enrollment, stamp(now() + timedelta(days=2))))
        self.assert_error(403, student, f'classes/{classroom}')
        svip_expiry = now() + timedelta(hours=2)
        row = self.admin.call('accounts?q=' + row['login_identifier'])['rows'][0]
        row = self.update(row, body, membership='SVip', membershipExpiresAt=stamp(svip_expiry))
        student, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual((row['membership'], row['membership_expires_at']), ('SVip', stamp(svip_expiry)))
        self.assertEqual(state['account']['membership'], 'SVip')
        self.assertEqual(student.call(f'classes/{classroom}')['class']['id'], classroom)
        self.assertIsNone(state['account']['usage']['bot']['limit'])
        with patch('backend.platform_api.now', return_value=svip_expiry + timedelta(seconds=1)):
            self.assertEqual(student.call('session')['account']['membership'], 'Free')
            self.assert_error(403, student, f'classes/{classroom}')
        row = self.update(row, body, membership='SVip', membershipExpiresAt=None)
        self.assertEqual(row['membership'], 'SVip')
        self.assertIsNone(row['membership_expires_at'])
        row = self.update(row, body, membership='Free', membershipExpiresAt=None)
        student, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual(state['account']['membership'], 'Free')
        self.assertIsNone(row['vip_expires_at'])
        self.assertEqual(state['account']['usage']['bot']['limit'], 5)
        self.assert_error(429, student, 'bot/start', {'requestKey': secrets.token_hex(12)})
        self.assert_error(403, student, f'classes/{classroom}')
        with connect(self.path) as db:
            self.assertIsNone(db.execute('SELECT left_at FROM class_enrollments WHERE id=?', (enrollment,)).fetchone()[0])
            self.assertEqual(db.execute('SELECT count(*) FROM access_entitlements WHERE account_id=? AND (ends_at IS NULL OR ends_at>?)',
                                       (row['id'], stamp())).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM notifications').fetchone()[0], 0)
            referral = db.execute('SELECT reward_status,first_vip_upgraded_at FROM account_referrals WHERE invitee_account_id=?', (row['id'],)).fetchone()
            self.assertEqual(tuple(referral), ('pending', None))
            self.assertIsNone(db.execute('SELECT vip_expires_at FROM accounts WHERE id=?', (inviter['id'],)).fetchone()[0])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_admin_can_create_and_edit_mascot_points_and_plan_without_inventing_a_class(self):
        row, body = self.create(mascot='horse', points=2045, membership='SVip', membershipExpiresAt=None)
        student, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual((row['mascot'], row['points'], row['membership']), ('horse', 2045, 'SVip'))
        self.assertEqual((state['state']['mascot'], state['state']['points']), ('horse', 2045))
        self.assertEqual(state['account']['classes'], [])
        room = student.call('arena', {'action': 'create', 'public': False})
        changed = self.update(row, body, mascot='fox', points=1234)
        self.assertFalse(student.call('session')['authenticated'])
        reopened, state = self.login(row['login_identifier'], body['password'])
        self.assertEqual((state['state']['mascot'], state['state']['points']), ('fox', 1234))
        self.assert_error(403, reopened, 'arena', {'action': 'state', **room})
        self.assertEqual(state['account']['membership'], 'SVip')
        self.assertEqual(state['account']['classes'], [])
        self.assertEqual(self.admin.call('accounts?q=' + row['login_identifier'])['rows'][0]['points'], 1234)
        reopened.call('mascot', {'mascot': 'cat'})
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', {
            'revision': changed['revision'], 'mascot': 'horse', 'points': 2045})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT xp FROM student_companions WHERE student_id=?', (row['student_id'],)).fetchone()[0], 1234)
            self.assertEqual(db.execute('SELECT count(*) FROM class_enrollments WHERE student_id=?', (row['student_id'],)).fetchone()[0], 0)

    def test_invalid_full_profile_rolls_back_year_name_plan_and_companion_atomically(self):
        row, body = self.create()
        future = stamp(now() + timedelta(days=30))
        good = {'revision': row['revision'], 'name': 'Lá mới', 'birthYear': body['birthYear'] + 1,
                'membership': 'VIP', 'membershipExpiresAt': future, 'mascot': 'cat', 'points': 1250}
        invalid = ({'birthYear': True}, {'birthYear': academic()[0] - 5},
                   {'membership': 'Gold'}, {'membershipExpiresAt': 'not-a-date'},
                   {'membershipExpiresAt': None}, {'membershipExpiresAt': stamp(now() - timedelta(days=1))},
                   {'membershipExpiresAt': '2026-11-12T25:00:00Z'}, {'mascot': 'unknown'},
                   {'points': 999}, {'points': 1_000_000_001}, {'points': True}, {'points': 1234.5})
        with connect(self.path) as db:
            before_audit = db.execute('SELECT count(*) FROM staff_audit_log').fetchone()[0]
        for changes in invalid:
            with self.subTest(changes=changes):
                self.assert_error(400, self.admin, f'accounts/{row["id"]}', {**good, **changes})
                preserved = self.admin.call('accounts?q=' + row['login_identifier'])['rows'][0]
                self.assertEqual((preserved['full_name'], preserved['birth_year'], preserved['revision'],
                                  preserved['membership'], preserved['mascot'], preserved['points']),
                                 ('Mầm xanh', body['birthYear'], row['revision'], 'Free', 'sprout', 1000))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM staff_audit_log').fetchone()[0], before_audit)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        saved = self.admin.call(f'accounts/{row["id"]}', good)['account']
        self.assertEqual((saved['membership'], saved['mascot'], saved['points']), ('VIP', 'cat', 1250))
        self.assert_error(409, self.admin, f'accounts/{row["id"]}', good)
