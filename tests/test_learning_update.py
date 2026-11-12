import os
import secrets
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import test_platform_api as platform_tests
from backend.platform_api import APIError, connect, stamp


class LearningUpdateTests(unittest.TestCase):
    setUpClass = classmethod(platform_tests.PlatformTests.setUpClass.__func__)
    tearDownClass = classmethod(platform_tests.PlatformTests.tearDownClass.__func__)
    user = platform_tests.PlatformTests.user

    def fixture(self):
        client, state, _, _ = self.user()
        with connect(self.path, True) as db:
            aid = state['account']['id']
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (aid,)).fetchone()[0]
            ay = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (sid,)).fetchone()[0]
            teacher = db.execute('INSERT INTO teachers(full_name) VALUES (\'Giáo viên thử\')').lastrowid
            cid = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,schedule,curriculum) VALUES (?,5,?,\'Lớp thử nội bộ\',\'Thứ 3\',\'Toán 5\')', (teacher, ay)).lastrowid
            eid = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)', (sid, cid, stamp())).lastrowid
            db.execute('INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,\'internal\',?)', (aid, eid, stamp()))
            lid = db.execute('INSERT INTO class_sessions(class_id,title,starts_at,teacher_comment) VALUES (?,\'Buổi thử\',\'2026-11-03T12:00:00Z\',\'Có tiến bộ\')', (cid,)).lastrowid
            a1 = db.execute('INSERT INTO class_assignments(session_id,title) VALUES (?,\'Bài 1\')', (lid,)).lastrowid
            a2 = db.execute('INSERT INTO class_assignments(session_id,title) VALUES (?,\'Bài 2\')', (lid,)).lastrowid
            db.execute('INSERT INTO class_scores VALUES (?,?,8)', (a1, sid))
            db.execute('INSERT INTO class_attendance VALUES (?,?,\'charged\')', (lid, sid))
            fid = db.execute('INSERT INTO class_fees(class_id,student_id,month,amount) VALUES (?,?,\'2026-11\',100000)', (cid, sid)).lastrowid
        return client, cid, sid, a1, a2, fid

    def test_daily_limits_idempotency_vietnam_midnight_and_vip(self):
        c, _, _, _ = self.user()
        day = datetime(2026, 11, 11, 16, 59, tzinfo=timezone.utc)
        with patch('backend.learning_update.now', return_value=day):
            first = c.call('exams', {'requestKey':'same-key-123','count':3,'topic':'decimal'})
            self.assertEqual(c.call('exams', {'requestKey':'same-key-123','count':3,'topic':'decimal'}), first)
            with self.assertRaises(APIError) as caught: c.call('exams', {'requestKey':'different-key','count':3,'topic':'decimal'})
            self.assertEqual(caught.exception.status, 429)
            c.call('exams', {'requestKey':'combined-key','category':'combined'})
            with self.assertRaises(APIError): c.call('exams', {'requestKey':'combined-again','category':'combined'})
            for i in range(5): c.call('bot/start', {'requestKey':f'bot-key-{i}'})
            c.call('bot/start', {'requestKey':'bot-key-0'})
            with self.assertRaises(APIError): c.call('bot/start', {'requestKey':'bot-key-5'})
        with patch('backend.learning_update.now', return_value=day.replace(hour=17, minute=0)):
            c.call('exams', {'requestKey':'tomorrow-key','count':3,'topic':'decimal'})
        c.call('dev/upgrade', {'requestKey':secrets.token_hex(12)})
        for i in range(3): c.call('exams', {'requestKey':f'vip-content-{i}','count':3,'topic':'decimal'})
        self.assertIsNone(c.call('session')['account']['usage']['content']['limit'])

    def test_class_permissions_completion_averages_fees_and_roster(self):
        c, cid, sid, a1, a2, fid = self.fixture()
        state = c.call('session')
        self.assertEqual(state['account']['membership'], 'SVip')
        self.assertNotIn('reviewUpgrades', state['account'])
        result = c.call(f'classes/{cid}')
        self.assertFalse(result['sessions'][0]['complete'])
        self.assertEqual(result['months'], [{'month':'2026-11','average':8}])
        self.assertEqual(result['fees'][0]['count'], 1)
        with connect(self.path, True) as db: db.execute('INSERT INTO class_scores VALUES (?,?,10)', (a2, sid))
        result = c.call(f'classes/{cid}')
        self.assertTrue(result['sessions'][0]['complete'])
        self.assertEqual(result['months'][0]['average'], 9)
        self.assertEqual(c.call(f'classes/{cid}/ranking?assignment={a1}')['rows'][0]['value'],8)
        cycle = result['cycles'][0]['index']
        self.assertEqual(c.call(f'classes/{cid}/ranking?cycle={cycle}')['rows'][0]['value'],9)
        self.assertEqual(c.call(f'classes/{cid}?from=2026-11-04')['sessions'], [])
        with self.assertRaises(APIError): c.call(f'classes/{cid}?from=2026-12-01&to=2026-11-01')
        stranger, _, _, _ = self.user()
        with self.assertRaises(APIError): stranger.call(f'classes/{cid}')
        with self.assertRaises(APIError): stranger.call(f'classes/{cid}/ranking?assignment={a1}')
        with self.assertRaises(APIError): stranger.call('payments', {'feeId':fid})
        with self.assertRaises(APIError): stranger.call('leaderboard?scope=class')
        self.assertTrue(c.call('leaderboard?scope=class')['rows'][0]['mine'])

    def test_payment_pending_unique_reference_bank_config_and_no_self_upgrade(self):
        c, state, _, _ = self.user()
        with patch.dict(os.environ, {'MAM_TOAN_BANK_ID':'','MAM_TOAN_BANK_ACCOUNT':'','MAM_TOAN_BANK_NAME':''}):
            order = c.call('payments', {})['order']
            self.assertEqual(order['qrUrl'], '')
            self.assertEqual(c.call('payments', {})['order']['id'], order['id'])
            self.assertEqual(c.call('session')['account']['membership'], 'Free')
        with patch.dict(os.environ, {'MAM_TOAN_BANK_ID':'VCB','MAM_TOAN_BANK_ACCOUNT':'123456789','MAM_TOAN_BANK_NAME':'TEST OWNER'}):
            qr = c.call('payments', {})['order']
            self.assertIn('amount=100000', qr['qrUrl'])
            self.assertIn(order['reference'], qr['qrUrl'])
        internal, _, _, _, _, fid = self.fixture()
        fee = internal.call('payments', {'feeId':fid})['order']
        self.assertEqual(fee['amount'], 100000)
        with connect(self.path, True) as db: db.execute('UPDATE class_fees SET paid_at=? WHERE id=?', (stamp(),fid))
        with self.assertRaises(APIError): internal.call('payments', {'feeId':fid})
        with self.assertRaises(APIError): internal.call('payments', {})

    def test_vip_school_and_document_permissions(self):
        c, _, _, _ = self.user()
        with self.assertRaises(APIError): c.call('materials')
        with self.assertRaises(APIError): c.call('exams', {'requestKey':'school-free-key','category':'school','school':'cau-giay'})
        c.call('dev/upgrade', {'requestKey':secrets.token_hex(12)})
        self.assertIn('Phiếu',c.call('materials')['title'])
        exam = c.call('exams', {'requestKey':'school-vip-key','category':'school','school':'cau-giay'})['exam']
        self.assertIn('Mẫu tự biên soạn', exam['title'])
        self.assertNotIn('answer',exam['questions'][0])
        self.assertEqual(len([l for l in c.call('session')['lessons'] if l['week']==c.call('session')['state']['week']+1]),3)

    def test_public_challenge_acceptance_countdown_cancel_and_limits(self):
        first, state, _, _ = self.user()
        second, _, _, _ = self.user()
        for i in range(3):
            room = first.call('arena', {'action':'create','public':True})
            self.assertIn(room['code'],[r['code'] for r in second.call('arena', {'action':'list'})['rooms']])
            join = second.call('arena', {'action':'join','code':room['code']})
            self.assertTrue(first.call('arena', {'action':'state',**room})['host'])
            self.assertFalse(second.call('arena', {'action':'state',**join})['host'])
            first.call('arena', {'action':'accept',**room})
            runtime = self.server.arena.rooms[room['code']]
            answer = runtime['questions'][0]['answer']
            first.call('arena', {'action':'answer',**room,'answer':answer,'index':0})
            self.assertEqual(next(iter(runtime['players'].values()))['correct'],0)
            runtime['readyAt']=0
            first.call('arena', {'action':'state',**room})
            first.call('arena', {'action':'emote',**room,'emote':1})
            view=first.call('arena', {'action':'emote',**room,'emote':2})['battle']
            self.assertEqual(view['myEmote'],1)
            first.call('arena', {'action':'answer',**room,'answer':answer,'index':0})
            self.assertEqual(first.call('arena', {'action':'next',**room,'index':0})['battle']['index'],0)
            runtime['nextAt']=0
            self.assertEqual(first.call('arena', {'action':'state',**room})['battle']['index'],1)
            # Finish normally: this test checks the daily match quota, while
            # separate discipline tests cover repeated early exits.
            for index in range(1, 5):
                first.call('arena', {'action':'answer',**room,'index':index,
                                    'answer':runtime['questions'][index]['answer']})
                runtime['nextAt'] = 0
                completed = first.call('arena', {'action':'state',**room})
            self.assertTrue(completed['result']['completed'])
        with self.assertRaises(APIError): first.call('arena', {'action':'quick'})
        self.assertEqual(first.call('session')['account']['usage']['human']['used'],3)

    def test_wait_expiry_challenge_expiry_and_private_visibility(self):
        a, _, _, _ = self.user()
        b, _, _, _ = self.user()
        room=a.call('arena',{'action':'create'})
        self.assertNotIn(room['code'],[r['code'] for r in b.call('arena',{'action':'list'})['rooms']])
        runtime=self.server.arena.rooms[room['code']]
        runtime['created']=time.time()-301
        self.assertEqual(a.call('arena',{'action':'state',**room})['status'],'cancelled')
        room=a.call('arena',{'action':'quick'})
        join=b.call('arena',{'action':'quick'})
        self.assertEqual(room['code'],join['code'])
        self.server.arena.rooms[room['code']]['challengeUntil']=0
        self.assertEqual(a.call('arena',{'action':'state',**room})['status'],'cancelled')
        self.assertEqual(b.call('arena',{'action':'state',**join})['status'],'cancelled')
        self.assertEqual(a.call('session')['account']['usage']['human']['used'],0)
