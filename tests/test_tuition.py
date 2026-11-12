"""Preview/save tuition from attendance without changing financial history."""
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, academic, connect, ensure_grade, issue_session, now, seed_catalog, stamp
from backend.staff_api import create_first_admin, issue_session as staff_session
from test_platform_api import Client
from test_staff_api import StaffClient


class TuitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = Path(__file__).resolve().parents[1]/'work'/'tuition-20261112'
        work.mkdir(parents=True, exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix='tests-',dir=work)
        cls.template = Path(cls.directory.name)/'template.sqlite3'
        initialize(cls.template)
        seed_catalog(cls.template)
        create_first_admin(cls.template,'admin','Quản trị thử',secrets.token_urlsafe(20))
        cls.accounts,cls.students,cls.teachers,cls.classes,cls.sessions=[],[],[],[],[]
        with connect(cls.template,True) as db:
            credential = db.execute('SELECT password_hash FROM staff_users WHERE id=1').fetchone()[0]
            for index in range(2):
                tid=db.execute('INSERT INTO teachers(full_name) VALUES (?)',('Giáo viên thử',)).lastrowid
                uid=db.execute("INSERT INTO staff_users(login,full_name,password_hash,role,teacher_id,created_at) VALUES (?,?,?,'teacher',?,?)",
                    (f'tuition-teacher-{index}','Giáo viên thử',credential,tid,stamp())).lastrowid
                cls.teachers.append((tid,uid))
            for index in range(5):
                aid=db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash) VALUES (?,?,?,?,?,?)',
                    (f'TUITION-{index}',f'tuition-{index}',academic()[0]-10,f'TUITION-INV-{index}',stamp(),credential)).lastrowid
                sid=db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,5,?)',
                    (f'TUITION-HS-{index}','Mầm xanh',aid)).lastrowid
                _,ayid=ensure_grade(db,sid,academic()[0]-10)
                db.execute("INSERT INTO student_companions(student_id,mascot_id) SELECT ?,id FROM mascots WHERE name='Mầm Sách'",(sid,))
                db.execute('INSERT INTO learning_preferences(student_id) VALUES (?)',(sid,))
                cls.accounts.append(aid);cls.students.append(sid)
            for index in range(2):
                cls.classes.append(db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,session_fee) VALUES (?,5,?,?,120000)',
                    (cls.teachers[index][0],ayid,f'Lớp học phí {index}')).lastrowid)
            for index in range(3):
                eid=db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at,left_at) VALUES (?,?,?,?)',
                    (cls.students[index],cls.classes[0],'2026-11-02T00:00:00Z',stamp() if index==2 else None)).lastrowid
                if index<2:
                    db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,'internal',?)",
                        (cls.accounts[index],eid,stamp(now()-timedelta(days=1))))
            for index,date in enumerate(('2026-10-31T16:59:59Z','2026-10-31T17:00:00Z','2026-11-01T01:00:00Z',
                '2026-11-02T01:00:00Z','2026-11-03T01:00:00Z','2026-11-04T01:00:00Z','2026-11-30T16:59:59Z','2026-11-30T17:00:00Z')):
                cls.sessions.append(db.execute('INSERT INTO class_sessions(class_id,title,starts_at) VALUES (?,?,?)',
                    (cls.classes[0],f'Buổi {index}',date)).lastrowid)
            for index,status in enumerate(('charged','charged','charged','free','absent',None,'charged','charged')):
                if status:
                    db.execute('INSERT INTO class_attendance VALUES (?,?,?)',(cls.sessions[index],cls.students[0],status))
            for index in (2,3):
                db.execute("INSERT INTO class_attendance VALUES (?,?,'charged')",(cls.sessions[3],cls.students[index]))
            db.execute("UPDATE students SET status='inactive' WHERE id IN (?,?)",(cls.students[3],cls.students[4]))
            db.execute("UPDATE accounts SET deleted_at=?,status='suspended' WHERE id IN (?,?)",(stamp(),cls.accounts[3],cls.accounts[4]))
            cls.paid_fee=db.execute('INSERT INTO class_fees(class_id,student_id,month,amount,paid_at) VALUES (?,?,?,777,?)',
                (cls.classes[0],cls.students[4],'2026-11',stamp())).lastrowid

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.path=Path(self.directory.name)/(self._testMethodName+'.sqlite3')
        with closing(sqlite3.connect(self.template)) as source,closing(sqlite3.connect(self.path)) as target:
            source.backup(target)
        self.server=SimpleNamespace(database_path=self.path,review_upgrades=False,arena=Arena())
        self.admin,self.teacher,self.other=self.staff(1),self.staff(self.teachers[0][1]),self.staff(self.teachers[1][1])
        self.base=f'classes/{self.classes[0]}/fees'

    def staff(self,identity):
        client=StaffClient(self.server)
        with connect(self.path,True) as db:
            result=staff_session(client,db,db.execute('SELECT * FROM staff_users WHERE id=?',(identity,)).fetchone())
        client.headers['Cookie']=client.api_headers.pop('Set-Cookie').split(';')[0];client.csrf=result['csrf']
        return client

    def student(self,index=0):
        client=Client(self.server)
        with connect(self.path,True) as db:
            result=issue_session(client,db,self.accounts[index]);client.csrf=result['csrf_token']
        client.headers['Cookie']=client.api_headers.pop('Set-Cookie').split(';')[0]
        return client

    def preview(self,client=None):
        return (client or self.teacher).call(self.base+'/preview',{'month':'2026-11'})

    def save(self,preview=None,key=None,client=None):
        view=preview or self.preview(client)
        return (client or self.teacher).call(self.base+'/calculate',{'month':view['month'],'previewToken':view['previewToken'],
            'requestKey':key or secrets.token_hex(12)})

    def error(self,status,client,path,body=None):
        with self.assertRaises(APIError) as caught:client.call(path,body)
        self.assertEqual(caught.exception.status,status)

    def counts(self):
        with connect(self.path) as db:
            return {name:db.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in
                ('class_fees','class_tuition_calculations','class_tuition_calculation_items','notifications','class_notices','staff_audit_log')}

    def test_preview_vietnam_month_multiple_sessions_statuses_history_and_no_writes(self):
        before=self.counts();view=self.preview();self.assertEqual(self.counts(),before)
        rows={row['studentId']:row for row in view['rows']};row=rows[self.students[0]]
        self.assertEqual((row['chargedCount'],row['freeCount'],row['absentCount'],row['pendingCount'],row['amount']),(3,1,1,1,360000))
        self.assertEqual([s['id'] for s in row['sessions']],self.sessions[1:7])
        self.assertEqual([s['date'] for s in row['sessions'][:2]],['2026-11-01','2026-11-01'])
        self.assertTrue(rows[self.students[2]]['historical']);self.assertEqual(rows[self.students[2]]['amount'],120000)
        self.assertNotIn(self.students[3],rows)
        self.assertTrue(rows[self.students[4]]['locked']);self.assertEqual(rows[self.students[4]]['amount'],777)
        self.assertEqual(view['totals']['totalAmount'],480777)
        self.assertEqual(view['previewToken'],self.preview()['previewToken'])

    def test_null_zero_and_overflow_rates_and_legacy_class_configuration(self):
        with connect(self.path,True) as db:db.execute('UPDATE online_classes SET session_fee=NULL WHERE id=?',(self.classes[0],))
        self.error(400,self.teacher,self.base+'/preview',{'month':'2026-11'})
        with connect(self.path,True) as db:db.execute('UPDATE online_classes SET session_fee=0 WHERE id=?',(self.classes[0],))
        result=self.save()['calculation'];self.assertEqual((result['created'],result['notificationsSent'],result['totalAmount']),(3,3,777))
        with connect(self.path,True) as db:db.execute('UPDATE online_classes SET session_fee=1000000000 WHERE id=?',(self.classes[0],))
        self.error(400,self.teacher,self.base+'/preview',{'month':'2026-11'})
        body={'name':'Lớp cũ chưa cấu hình','grade':5,'teacherId':self.teachers[0][0],'status':'active','schedule':'','curriculum':'','meetingUrl':''}
        legacy=self.admin.call('classes',body)['class'];self.assertIsNone(legacy['session_fee'])
        updated=self.admin.call('classes',{**body,'id':legacy['id'],'revision':legacy['revision'],'sessionFee':0})['class']
        self.assertEqual(updated['session_fee'],0)
        self.error(400,self.admin,'classes',{**body,'sessionFee':True})

    def test_saved_snapshot_replay_unchanged_no_spam_and_notice_watermark(self):
        initial=self.preview();key=secrets.token_hex(12);saved=self.save(initial,key);summary=saved['calculation']
        self.assertEqual((summary['created'],summary['updated'],summary['paidLocked'],summary['notificationsSent']),(3,0,1,3))
        fee=next(f for f in saved['fees'] if f['student_id']==self.students[0]);fee_id=fee['id']
        student=self.student();class_path=f'classes/{self.classes[0]}'
        first=student.call(class_path);bill=next(f for f in first['fees'] if f['id']==fee_id)
        self.assertEqual((bill['source'],bill['session_fee'],bill['count'],bill['amount']),('calculated',120000,3,360000))
        old_watermark=first['readThrough']['fees']
        student.call(class_path+'/read',{'section':'fees','through':old_watermark})
        repeat=self.save(initial,key)['calculation'];self.assertTrue(repeat['replayed']);self.assertEqual(repeat['id'],summary['id'])
        same=self.save()['calculation'];self.assertEqual((same['created'],same['updated'],same['unchanged'],same['notificationsSent']),(0,0,3,0))
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM notifications').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT calculation_id FROM class_fees WHERE id=?',(fee_id,)).fetchone()[0],summary['id'])
        with connect(self.path,True) as db:
            db.execute("UPDATE class_attendance SET status='free' WHERE session_id=? AND student_id=?",(self.sessions[1],self.students[0]))
            db.execute("UPDATE class_sessions SET title='Buổi đã sửa' WHERE id=?",(self.sessions[1],))
            db.execute('UPDATE online_classes SET session_fee=250000 WHERE id=?',(self.classes[0],))
        self.assertEqual(next(f for f in student.call(class_path)['fees'] if f['id']==fee_id),bill)
        self.assertEqual(self.teacher.call(self.base+f'/{fee_id}')['sessions'][0]['title'],'Buổi 1')
        self.error(409,self.teacher,self.base+'/calculate',{'month':'2026-12','previewToken':initial['previewToken'],'requestKey':key})
        changed=self.save();newbill=next(f for f in student.call(class_path)['fees'] if f['id']==fee_id)
        self.assertEqual(newbill['amount'],500000);self.assertEqual(newbill['sessions'][0]['title'],'Buổi đã sửa')
        self.assertGreater(student.call(class_path)['readThrough']['fees'],old_watermark)
        remaining=student.call(class_path+'/read',{'section':'fees','through':old_watermark})
        self.assertEqual(remaining['unread']['fees'],1)
        with connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM class_notices WHERE student_id=? AND section='fees' AND source_id=?",(self.students[0],fee_id)).fetchone()[0],1)

    def test_preview_stale_rate_attendance_invoice_and_pending_payment(self):
        for mutation in ('rate','attendance','invoice','payment'):
            with self.subTest(mutation=mutation):
                view=self.preview()
                with connect(self.path,True) as db:
                    if mutation=='rate':db.execute('UPDATE online_classes SET session_fee=session_fee+1 WHERE id=?',(self.classes[0],))
                    elif mutation=='attendance':db.execute("UPDATE class_attendance SET status='free' WHERE session_id=? AND student_id=?",(self.sessions[2],self.students[0]))
                    elif mutation=='invoice':db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,99)',(self.classes[0],self.students[0],'2026-11'))
                    else:
                        fee=db.execute('SELECT id FROM class_fees WHERE student_id=?',(self.students[0],)).fetchone()[0]
                        db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at) VALUES (?,?,?,?,?)',(self.accounts[0],fee,'STALE-PAYMENT',99,stamp()))
                self.error(409,self.teacher,self.base+'/calculate',{'month':'2026-11','previewToken':view['previewToken'],'requestKey':secrets.token_hex(12)})

    def test_failed_notice_rolls_back_fees_pending_orders_run_items_badges_and_audit(self):
        with connect(self.path,True) as db:
            fee=db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,42)',(self.classes[0],self.students[0],'2026-11')).lastrowid
            db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at) VALUES (?,?,?,?,?)',(self.accounts[0],fee,'ROLLBACK-ORDER',42,stamp()))
            db.execute("CREATE TRIGGER fail_tuition_notice BEFORE INSERT ON notifications WHEN NEW.kind='staff_message' BEGIN SELECT RAISE(ABORT,'forced fee notice failure'); END")
        before=self.counts();view=self.preview()
        with self.assertRaises(sqlite3.IntegrityError):self.save(view)
        self.assertEqual(self.counts(),before)
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT amount FROM class_fees WHERE id=?',(fee,)).fetchone()[0],42)
            self.assertEqual(db.execute('SELECT status FROM payment_orders').fetchone()[0],'pending')

    def test_pending_orders_cancel_on_automatic_and_manual_changes_paid_invoices_locked(self):
        with connect(self.path,True) as db:
            fee=db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,?,55)',(self.classes[0],self.students[0],'2026-11')).lastrowid
            order=db.execute('INSERT INTO payment_orders(account_id,fee_id,reference,amount,created_at) VALUES (?,?,?,?,?)',(self.accounts[0],fee,'OLD-ORDER',55,stamp())).lastrowid
        saved=self.save();self.assertEqual(saved['calculation']['updated'],1)
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?',(order,)).fetchone()[0],'cancelled')
        fresh=self.student().call('payments',{'feeId':fee})['order'];self.assertNotEqual(fresh['reference'],'OLD-ORDER')
        manual=self.admin.call(self.base,{'revision':saved['class']['revision'],'studentId':self.students[0],'month':'2026-11','amount':999})
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT status FROM payment_orders WHERE id=?',(fresh['id'],)).fetchone()[0],'cancelled')
            self.assertEqual(db.execute('SELECT source,sessions_json FROM class_fees WHERE id=?',(fee,)).fetchone()[:],('manual',None))
        with connect(self.path,True) as db:db.execute('UPDATE class_fees SET paid_at=? WHERE id=?',(stamp(),fee))
        locked=self.save();self.assertEqual(locked['calculation']['paidLocked'],2)
        self.error(409,self.admin,self.base,{'revision':locked['class']['revision'],'studentId':self.students[0],'month':'2026-11','amount':123})
        with connect(self.path) as db:self.assertEqual(db.execute('SELECT amount FROM class_fees WHERE id=?',(fee,)).fetchone()[0],999)

    def test_role_csrf_forged_totals_and_legacy_manual_calendar(self):
        self.error(401,StaffClient(self.server),self.base+'/preview',{'month':'2026-11'})
        self.error(403,self.other,self.base+'/preview',{'month':'2026-11'})
        self.error(403,self.teacher,self.base,{'revision':1,'studentId':self.students[0],'month':'2026-11','amount':1})
        self.error(400,self.teacher,self.base+'/preview',{'month':'2026-11','amount':1})
        view=self.preview()
        self.error(400,self.teacher,self.base+'/calculate',{'month':'2026-11','previewToken':view['previewToken'],'requestKey':'forged-key','totalAmount':1})
        csrf=self.teacher.csrf;self.teacher.csrf='bad'
        self.error(403,self.teacher,self.base+'/calculate',{'month':'2026-11','previewToken':view['previewToken'],'requestKey':'csrf-key-01'})
        self.teacher.csrf=csrf
        for month in ('2026-1','2026-13','0000-01','bad'):
            self.error(400,self.teacher,self.base+'/preview',{'month':month})
        info=self.admin.call(f'classes/{self.classes[0]}')['class']
        saved=self.admin.call(self.base,{'revision':info['revision'],'studentId':self.students[0],'month':'2026-11','amount':123})
        fee=next(f for f in saved['fees'] if f['student_id']==self.students[0])
        detail=self.teacher.call(self.base+f'/{fee["id"]}')
        self.assertEqual(detail['fee']['source'],'manual');self.assertEqual(detail['fee']['amount'],123)
        self.assertEqual(len(detail['sessions']),6)
        self.error(403,self.other,self.base+f'/{fee["id"]}')
