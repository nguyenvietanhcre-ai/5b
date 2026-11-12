"""Inbox history, paid-plan receipts and role-scoped announcement delivery."""
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import BACKEND, execute_sql, initialize
from backend.membership import record_vip_purchase
from backend.platform_api import APIError, academic, connect, ensure_grade, issue_session, now, seed_catalog, stamp
from backend.staff_api import create_first_admin, issue_session as issue_staff_session
from test_platform_api import Client
from test_staff_api import StaffClient


class NotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1] / 'work'
        work.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='notification-tests-', dir=work)
        cls.template = Path(cls.directory.name) / 'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)
        create_first_admin(cls.template, 'admin', 'Quản trị thử', secrets.token_urlsafe(20))
        with connect(cls.template, True) as db:
            credential = db.execute('SELECT password_hash FROM staff_users WHERE id=1').fetchone()[0]
            cls.teachers = []
            for index in range(2):
                teacher = db.execute('INSERT INTO teachers(full_name) VALUES (?)', ('Giáo viên thử',)).lastrowid
                staff = db.execute("INSERT INTO staff_users(login,full_name,password_hash,role,teacher_id,created_at) "
                    "VALUES (?,?,?,'teacher',?,?)", (f'teacher-{index}', 'Giáo viên thử', credential, teacher, stamp())).lastrowid
                cls.teachers.append((teacher, staff))
            cls.accounts, cls.students = [], []
            for index in range(8):
                aid = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash) '
                    'VALUES (?,?,?,?,?,?)', (f'NOTICE-{index}', f'notice-{index}', academic()[0]-10,
                     f'NOTICE-INVITE-{index}', stamp(), credential)).lastrowid
                sid = db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,5,?)',
                                 (f'NOTICE-HS-{index}', 'Mầm xanh', aid)).lastrowid
                _, ayid = ensure_grade(db, sid, academic()[0]-10)
                db.execute("INSERT INTO student_companions(student_id,mascot_id) SELECT ?,id FROM mascots WHERE name='Mầm Sách'", (sid,))
                db.execute('INSERT INTO learning_preferences(student_id) VALUES (?)', (sid,))
                cls.accounts.append(aid)
                cls.students.append(sid)
            cls.classes = []
            for index, status in enumerate(('active', 'active', 'closed')):
                cid = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,status) VALUES (?,5,?,?,?)',
                    (cls.teachers[index % 2][0], ayid, f'Lớp thông báo {index}', status)).lastrowid
                cls.classes.append(cid)
            for account_index, class_index in ((6, 0), (7, 1)):
                eid = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)',
                    (cls.students[account_index], cls.classes[class_index], stamp(now()-timedelta(days=1)))).lastrowid
                db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                    (cls.accounts[account_index], eid, stamp(now()-timedelta(days=1))))
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?', (stamp(now()+timedelta(days=30)), cls.accounts[1]))
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                       (cls.accounts[2], stamp(now()-timedelta(days=1))))
            db.execute("UPDATE accounts SET status='suspended' WHERE id IN (?,?)", (cls.accounts[3], cls.accounts[4]))
            db.execute('UPDATE accounts SET deleted_at=? WHERE id=?', (stamp(), cls.accounts[4]))
            db.execute("UPDATE students SET status='inactive' WHERE id IN (?,?)", (cls.students[4], cls.students[5]))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path = Path(self.directory.name) / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.template)) as source, closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server = SimpleNamespace(database_path=self.path, review_upgrades=False, arena=Arena())
        self.admin = self.staff(1)
        self.teacher = self.staff(self.teachers[0][1])
        self.other_teacher = self.staff(self.teachers[1][1])

    def staff(self, identity):
        client = StaffClient(self.server)
        with connect(self.path, True) as db:
            result = issue_staff_session(client, db, db.execute('SELECT * FROM staff_users WHERE id=?', (identity,)).fetchone())
        client.headers['Cookie'] = client.api_headers.pop('Set-Cookie').split(';')[0]
        client.csrf = result['csrf']
        return client

    def student(self, index=0):
        client = Client(self.server)
        with connect(self.path, True) as db:
            session = issue_session(client, db, self.accounts[index])
            client.csrf = session['csrf_token']
        client.headers['Cookie'] = client.api_headers.pop('Set-Cookie').split(';')[0]
        return client

    def error(self, status, client, path, body=None):
        with self.assertRaises(APIError) as caught:
            client.call(path, body)
        self.assertEqual(caught.exception.status, status)

    def announcement(self, **changes):
        return {'title': 'Lịch ôn tập', 'body': 'Các em mở bài ôn tập.\nChúc các em học vui!',
                'audience': 'all', 'requestKey': secrets.token_hex(12), **changes}

    def test_staff_audiences_permissions_and_recipient_boundaries(self):
        metadata = self.admin.call('notifications')
        self.assertEqual([group['value'] for group in metadata['groups']], ['all', 'Free', 'VIP', 'SVip'])
        self.assertEqual({row['id'] for row in metadata['classes']}, set(self.classes[:2]))
        own = self.teacher.call('notifications')
        self.assertEqual(own['groups'], [])
        self.assertEqual([row['id'] for row in own['classes']], self.classes[:1])
        for group, count in [('all', 6), ('Free', 2), ('VIP', 1), ('SVip', 3)]:
            self.assertEqual(self.admin.call('notifications/preview', {'audience': group})['recipientCount'], count)
        for group in ('all', 'Free', 'VIP', 'SVip'):
            self.error(403, self.teacher, 'notifications/preview', {'audience': group})
            self.error(403, self.teacher, 'notifications', self.announcement(audience=group))
        for cid in self.classes[1:]:
            self.error(403, self.teacher, 'notifications', self.announcement(audience='class', classId=cid))
        sent = self.teacher.call('notifications', self.announcement(audience='class', classId=self.classes[0]))
        self.assertEqual(sent['recipientCount'], 1)
        all_sent = self.admin.call('notifications', self.announcement())
        self.assertEqual(all_sent['recipientCount'], 6)
        with connect(self.path) as db:
            targets = {r[0] for r in db.execute('SELECT account_id FROM notification_broadcast_recipients WHERE broadcast_id=?', (all_sent['broadcastId'],))}
            self.assertEqual(targets, {self.accounts[i] for i in (0, 1, 2, 3, 6, 7)})
        notice = self.student(6).call('notifications')['rows']
        self.assertEqual({n['sender_role'] for n in notice}, {'admin', 'teacher'})
        self.assertEqual(self.teacher.call('notifications')['total'], 1)
        self.assertEqual(self.other_teacher.call('notifications')['total'], 0)
        self.assertEqual(self.admin.call('notifications')['total'], 2)
        with connect(self.path, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?', (stamp(now()-timedelta(seconds=1)), self.accounts[1]))
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES (?,'internal',?)",
                       (self.accounts[0], stamp(now()+timedelta(days=1))))
            db.execute('UPDATE online_classes SET teacher_id=? WHERE id=?', (self.teachers[1][0], self.classes[0]))
        self.assertEqual(self.admin.call('notifications/preview', {'audience': 'Free'})['recipientCount'], 3)
        self.assertEqual(self.admin.call('notifications/preview', {'audience': 'VIP'})['recipientCount'], 0)
        self.error(403, self.teacher, 'notifications', self.announcement(audience='class', classId=self.classes[0]))
        self.assertEqual(self.teacher.call('notifications')['classes'], [])

    def test_replay_snapshot_changed_payload_atomic_rollback_and_empty_group(self):
        payload = self.announcement()
        first = self.admin.call('notifications', payload)
        with connect(self.path, True) as db:
            db.execute("UPDATE students SET status='active' WHERE id=?", (self.students[5],))
        repeat = self.admin.call('notifications', payload)
        self.assertEqual(repeat['broadcastId'], first['broadcastId'])
        self.assertEqual(repeat['recipientCount'], 6)
        self.assertTrue(repeat['replayed'])
        self.error(409, self.admin, 'notifications', {**payload, 'body': payload['body'] + ' Nội dung khác.'})
        with connect(self.path, True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM notifications').fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT count(*) FROM staff_audit_log WHERE entity='notification_broadcast'").fetchone()[0], 1)
            db.execute(f"CREATE TRIGGER fail_delivery BEFORE INSERT ON notifications WHEN NEW.account_id={self.accounts[3]} "
                       "BEGIN SELECT RAISE(ABORT,'forced delivery failure'); END")
        failed = self.announcement()
        with self.assertRaises(sqlite3.IntegrityError):
            self.admin.call('notifications', failed)
        with connect(self.path, True) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM notification_broadcasts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM notification_broadcast_recipients').fetchone()[0], 6)
            self.assertEqual(db.execute('SELECT count(*) FROM notifications').fetchone()[0], 6)
            db.execute('DROP TRIGGER fail_delivery')
        self.assertEqual(self.admin.call('notifications', failed)['recipientCount'], 7)
        self.assertEqual(self.admin.call('notifications/preview', {'audience': 'VIP'})['recipientCount'], 1)
        with connect(self.path, True) as db:
            db.execute('UPDATE accounts SET vip_expires_at=NULL WHERE id=?', (self.accounts[1],))
        self.assertEqual(self.admin.call('notifications/preview', {'audience': 'VIP'})['recipientCount'], 0)
        self.error(400, self.admin, 'notifications', self.announcement(audience='VIP'))
        self.assertEqual(self.admin.call('notifications')['total'], 2)

    def test_inbox_five_unread_first_read_detail_idempotency_and_ownership(self):
        base = now()-timedelta(hours=1)
        ids = []
        with connect(self.path, True) as db:
            for index in range(12):
                ids.append(db.execute("INSERT INTO notifications(account_id,kind,title,body,created_at,read_at) "
                    "VALUES (?,'referral_contact_support',?,?,?,?)", (self.accounts[0], f'Thông báo {index}',
                    'Dòng một\nDòng hai <b>chữ nguyên văn</b>', stamp(base+timedelta(minutes=max(index,11) if index>=10 else index)),
                    stamp(base) if index < 3 else None)).lastrowid)
        student = self.student()
        page = student.call('notifications')
        self.assertEqual((page['pageSize'], page['total'], page['unreadCount']), (5, 12, 9))
        self.assertEqual([r['id'] for r in page['rows']], ids[-1:-6:-1])
        # Badge/referral polling must keep reading while another request owns
        # the database write reservation, without requesting a second one.
        with connect(self.path, True):
            self.assertEqual(student.call('notifications')['total'], 12)
            self.assertEqual(student.call('referrals')['total'], 0)
        second = student.call('notifications?page=2')
        self.assertEqual([r['id'] for r in second['rows']], [ids[i] for i in (6, 5, 4, 3, 2)])
        snapshot = student.call('session')['account']
        self.assertEqual(snapshot['notifications'], page['rows'])
        self.assertEqual((snapshot['notificationTotal'], snapshot['notificationUnreadCount']), (12, 9))
        selected = student.call(f'notifications/{ids[-1]}/read', {})
        self.assertEqual(selected['notification']['id'], ids[-1])
        self.assertEqual(selected['notification']['body'], 'Dòng một\nDòng hai <b>chữ nguyên văn</b>')
        self.assertIsNotNone(selected['notification']['read_at'])
        self.assertEqual(selected['account']['notificationUnreadCount'], 8)
        self.assertNotIn(ids[-1], [r['id'] for r in selected['account']['notifications']])
        self.assertEqual(student.call(f'notifications/{ids[-1]}/read', {})['notification']['read_at'], selected['notification']['read_at'])
        self.error(404, self.student(1), f'notifications/{ids[-1]}/read', {})
        self.error(404, student, 'notifications/999999/read', {})
        for invalid in ('0', '-1', 'bad'):
            self.error(400, student, 'notifications?page=' + invalid)
        self.assertEqual(student.call('notifications?page=99')['rows'], [])
        student.csrf = 'invalid'
        self.error(403, student, f'notifications/{ids[-2]}/read', {})

    def test_referrals_five_latest_registration_order_and_snapshot_total(self):
        ids = []
        with connect(self.path, True) as db:
            invite = db.execute('SELECT invite_code FROM accounts WHERE id=?', (self.accounts[0],)).fetchone()[0]
            for index in range(8):
                aid = db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at) VALUES (?,?,2016,?,?)',
                    (f'REF-{index}', f'ref-{index}', f'REF-INV-{index}', stamp())).lastrowid
                db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,5,?)',
                           (f'REF-HS-{index}', 'Bạn học', aid))
                ids.append(db.execute('INSERT INTO account_referrals(inviter_account_id,invitee_account_id,invite_code,registered_at) VALUES (?,?,?,?)',
                    (self.accounts[0], aid, invite, stamp(now()-timedelta(days=index)))).lastrowid)
        student = self.student()
        first, second = student.call('referrals'), student.call('referrals?page=2')
        self.assertEqual((first['total'], first['pageSize']), (8, 5))
        self.assertEqual([r['id'] for r in first['rows']], ids[:5])
        self.assertEqual([r['id'] for r in second['rows']], ids[5:])
        self.assertEqual(student.call('session')['account']['referrals'], first['rows'])
        self.assertEqual(student.call('session')['account']['referralTotal'], 8)

    def test_vip_first_renewal_actual_expiry_referral_once_and_no_manual_receipt(self):
        with connect(self.path, True) as db:
            invite = db.execute('SELECT invite_code FROM accounts WHERE id=?', (self.accounts[0],)).fetchone()[0]
            db.execute('INSERT INTO account_referrals(inviter_account_id,invitee_account_id,invite_code,registered_at) VALUES (?,?,?,?)',
                       (self.accounts[0], self.accounts[1], invite, stamp()))
        first = record_vip_purchase(self.path, self.accounts[1], 'NOTIFICATION-FIRST', 1, stamp())
        repeat = record_vip_purchase(self.path, self.accounts[1], 'NOTIFICATION-FIRST', 1, stamp())
        self.assertTrue(first['created'])
        self.assertFalse(repeat['created'])
        with connect(self.path) as db:
            expiry = db.execute("SELECT strftime('%d/%m/%Y %H:%M',vip_expires_at,'+7 hours') FROM accounts WHERE id=?", (self.accounts[1],)).fetchone()[0]
        first_notice = self.student(1).call('notifications')['rows'][0]
        self.assertEqual(first_notice['kind'], 'vip_subscription_success')
        self.assertIn(expiry, first_notice['body'])
        self.assertEqual((first_notice['sender_name'], first_notice['sender_role']), ('5BMath', 'system'))
        record_vip_purchase(self.path, self.accounts[1], 'NOTIFICATION-RENEWAL', 1, stamp())
        notices = self.student(1).call('notifications')
        self.assertEqual(notices['total'], 2)
        self.assertEqual(notices['rows'][0]['kind'], 'vip_renewal_success')
        with connect(self.path) as db:
            expiry = db.execute("SELECT strftime('%d/%m/%Y %H:%M',vip_expires_at,'+7 hours') FROM accounts WHERE id=?", (self.accounts[1],)).fetchone()[0]
            inviter_expiry = db.execute("SELECT strftime('%d/%m/%Y %H:%M',vip_expires_at,'+7 hours') FROM accounts WHERE id=?", (self.accounts[0],)).fetchone()[0]
        self.assertIn(expiry, notices['rows'][0]['body'])
        rewards = self.student().call('notifications')
        self.assertEqual(rewards['total'], 1)
        self.assertIn(inviter_expiry, rewards['rows'][0]['body'])
        row = self.admin.call('accounts?q=notice-0')['rows'][0]
        self.admin.call(f'accounts/{row["id"]}', {'revision': row['revision'], 'membership': 'VIP',
            'membershipExpiresAt': stamp(now()+timedelta(days=90))})
        self.assertEqual(self.student().call('notifications')['total'], 1)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM vip_purchases').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM notifications WHERE referral_id IS NOT NULL').fetchone()[0], 1)

    def test_staff_auth_csrf_input_validation_and_page_bounds(self):
        self.error(401, StaffClient(self.server), 'notifications')
        original = self.admin.csrf
        self.admin.csrf = 'wrong'
        self.error(403, self.admin, 'notifications', self.announcement())
        self.admin.csrf = original
        for changes in ({'title': ''}, {'title': 'x'*161}, {'body': ' '}, {'body': 'x'*10001},
                        {'requestKey': 'short'}, {'audience': 'forged'}, {'audience': 'class', 'classId': True}):
            self.error(400, self.admin, 'notifications', self.announcement(**changes))
        for value in ('0', '-1', 'bad'):
            self.error(400, self.admin, 'notifications?page=' + value)
        self.admin.headers['Origin'] = 'https://untrusted.example'
        self.error(403, self.admin, 'notifications', self.announcement())
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM notification_broadcasts').fetchone()[0], 0)

    def test_migration_preserves_legacy_notification_ids_bodies_dates_and_read_state(self):
        legacy = Path(self.directory.name) / 'legacy-before-0012.sqlite3'
        backend = BACKEND
        with closing(sqlite3.connect(legacy)) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.executescript((backend/'migrations'/'0000_demo_base.sql').read_text(encoding='utf-8'))
            db.execute('CREATE TABLE schema_migrations(name TEXT PRIMARY KEY,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            for migration in sorted((backend/'migrations').glob('*.sql')):
                if migration.name >= '0012_notifications.sql':
                    break
                execute_sql(db, migration.read_text(encoding='utf-8'))
                db.execute('INSERT INTO schema_migrations(name) VALUES (?)', (migration.name,))
            db.execute("INSERT INTO accounts(id,account_code,login_identifier,birth_year,invite_code,created_at) VALUES (1,'OLD','old',2016,'OLD-INVITE','2026-01-01T00:00:00Z')")
            for identity, read in ((4, None), (9, '2026-02-02T04:00:00Z')):
                db.execute("INSERT INTO notifications(id,account_id,kind,body,created_at,read_at) VALUES (?,1,'referral_contact_support',?,?,?)",
                           (identity, f'Nội dung cũ {identity}\nGiữ nguyên.', '2026-02-01T03:00:00Z', read))
            before = db.execute('SELECT id,account_id,referral_id,kind,body,created_at,read_at FROM notifications ORDER BY id').fetchall()
            db.commit()
        initialize(legacy)
        with closing(sqlite3.connect(legacy)) as db:
            self.assertEqual(db.execute('SELECT id,account_id,referral_id,kind,body,created_at,read_at FROM notifications ORDER BY id').fetchall(), before)
            self.assertEqual(db.execute('SELECT DISTINCT sender_name,sender_role FROM notifications').fetchall(), [('5BMath', 'system')])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        record_vip_purchase(legacy, 1, 'AFTER-MIGRATION', 1, '2026-11-12T03:00:00Z')
        with closing(sqlite3.connect(legacy)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM notifications WHERE kind='vip_subscription_success'").fetchone()[0], 1)
