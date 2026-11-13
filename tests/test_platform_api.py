import hashlib
import json
import secrets
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import APIError, connect, dispatch, seed_catalog, stamp


class Client:
    def __init__(self, server):
        self.server=server
        self.client_address=('test-'+secrets.token_hex(4),1234)
        self.headers={'Host':'localhost:8765','Origin':'http://localhost:8765'}
        self.path=''
        self.api_headers={}
        self.csrf=''

    def call(self,path,body=None):
        self.path='/api/v1/'+path
        self.headers['X-CSRF-Token']=self.csrf
        result,status=dispatch(self,'GET' if body is None else 'POST',self.path.split('?')[0],body)
        cookie=self.api_headers.pop('Set-Cookie',None)
        if cookie:self.headers['Cookie']=cookie.split(';')[0]
        if result.get('csrf'):self.csrf=result['csrf']
        assert status==200
        return result


class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.path=Path(cls.directory.name)/'platform.sqlite3'
        initialize(cls.path)
        seed_catalog(cls.path)
        cls.server=SimpleNamespace(database_path=cls.path,review_upgrades=True,arena=Arena())

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def user(self,invite=''):
        from backend.platform_api import academic
        client=Client(self.server)
        login='test-'+secrets.token_hex(6)
        password=secrets.token_urlsafe(18)
        result=client.call('auth/register',{'login':login,'password':password,'name':'Học sinh thử',
                    'birthYear':academic()[0]-10,'inviteCode':invite})
        return client,result,login,password

    def test_session_credentials_csrf_birth_and_database_resume(self):
        client,state,login,password=self.user()
        self.assertTrue(state['authenticated'])
        self.assertEqual(state['state']['grade'],5)
        self.assertNotIn(password,json.dumps(state))
        with connect(self.path) as db:
            account=db.execute('SELECT password_hash FROM accounts WHERE login_identifier=?',(login,)).fetchone()
            self.assertTrue(account[0].startswith('pbkdf2_sha256$600000$'))
        lesson=state['lessons'][0]['id']
        client.call(f'lessons/{lesson}/complete',{})
        client.call(f'lessons/{lesson}/complete',{})
        client.call('profile',{'name':'Tên đã đổi'})
        with self.assertRaises(APIError):client.call('profile',{'birthYear':2015})
        other=Client(self.server)
        self.assertFalse(other.call('session')['authenticated'])
        with self.assertRaises(APIError):other.call('auth/login',{'login':login,'password':'wrong-password'})
        logged=other.call('auth/login',{'login':login,'password':password})
        self.assertEqual(logged['name'],'Tên đã đổi')
        self.assertIn(lesson,logged['state']['completed'])
        other.csrf='invalid'
        with self.assertRaises(APIError) as caught:other.call('profile',{'name':'bad'})
        self.assertEqual(caught.exception.status,403)
        other.csrf=logged['csrf']
        other.headers['Origin']='http://evil.example'
        with self.assertRaises(APIError):other.call('profile',{'name':'bad'})
        client.call('auth/logout',{})
        self.assertFalse(client.call('session')['authenticated'])

    def test_random_exam_server_marking_ownership_retry_and_deadline(self):
        client,_,_,_=self.user()
        body={'requestKey':secrets.token_hex(12),'count':3,'topic':'decimal'}
        exam=client.call('exams',body)['exam']
        self.assertEqual(client.call('exams',body)['exam']['id'],exam['id'])
        self.assertTrue(all('answer' not in q and 'steps' not in q for q in exam['questions']))
        stranger,_,_,_=self.user()
        with self.assertRaises(APIError):stranger.call('exams/'+exam['id'])
        with connect(self.path) as db:
            answers=[(r['position'],str(json.loads(r['grading_rule_json'])['answer'])) for r in db.execute(
                'SELECT i.position,v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=? ORDER BY i.position',(exam['id'],))]
        for position,answer in answers:
            client.call('exams/'+exam['id']+'/answers',{'position':position,'answer':answer})
        resumed=client.call('session')['state']['exams'][exam['id']]
        self.assertEqual(len(resumed['answers']),3)
        marked=client.call('exams/'+exam['id']+'/submit',{})['exam']
        self.assertEqual(marked['score'],10)
        self.assertTrue(all('answer' in q for q in marked['questions']))
        self.assertEqual(client.call('exams/'+exam['id']+'/submit',{})['exam'],marked)
        with self.assertRaises(APIError) as quota:client.call('exams',{'requestKey':secrets.token_hex(12),'count':3,'topic':'decimal'})
        self.assertEqual(quota.exception.status,429)
        client.call('dev/upgrade',{'requestKey':secrets.token_hex(12)})
        later=client.call('exams',{'requestKey':secrets.token_hex(12),'count':3,'topic':'decimal'})['exam']
        with connect(self.path,True) as db:
            first={r[0] for r in db.execute('SELECT question_version_id FROM exam_items WHERE exam_id=?',(exam['id'],))}
            second={r[0] for r in db.execute('SELECT question_version_id FROM exam_items WHERE exam_id=?',(later['id'],))}
            self.assertFalse(first & second)
            db.execute('UPDATE exam_attempts SET started_at=\'2020-01-01T00:00:00Z\',due_at=\'2020-01-01T00:30:00Z\' WHERE exam_id=?',(later['id'],))
        expired=client.call('exams/'+later['id']+'/answers',{'position':1,'answer':later['questions'][0]['options'][0]})['exam']
        self.assertEqual(expired['score'],0)
        self.assertEqual(expired['answers'],{})

    def test_nickname_rejected_before_registration_or_profile_write(self):
        from backend.platform_api import academic
        client, state, _, _ = self.user()
        for bad in ['0912345678', '+84 912 345 678', 'd-c-m', 'l_ồ_n', 'Bạn\u200bhọc']:
            with self.subTest(name=bad):
                with self.assertRaises(APIError) as caught:
                    client.call('profile', {'name': bad})
                self.assertEqual(caught.exception.status, 400)
                self.assertNotIn(bad, str(caught.exception))
                self.assertEqual(client.call('session')['name'], state['name'])
                login = 'blocked-'+secrets.token_hex(6)
                stranger = Client(self.server)
                with self.assertRaises(APIError):
                    stranger.call('auth/register', {'login': login, 'password': secrets.token_urlsafe(18),
                                  'name': bad, 'birthYear': academic()[0]-10})
                with connect(self.path) as db:
                    self.assertIsNone(db.execute('SELECT id FROM accounts WHERE login_identifier=?', (login,)).fetchone())
        self.assertEqual(client.call('profile', {'name': '  Nguyễn   Phúc Long  '})['name'], 'Nguyễn Phúc Long')

    def test_legacy_unsafe_names_are_masked_without_database_rewrite(self):
        from backend.nickname_policy import POLICY
        inviter, first, _, _ = self.user()
        invitee, second, _, _ = self.user(first['state']['inviteCode'])
        with connect(self.path, True) as db:
            db.execute('UPDATE students SET full_name=? WHERE account_id=?', ('0912345678', second['account']['id']))
        self.assertEqual(invitee.call('session')['name'], POLICY['fallback'])
        referral = inviter.call('session')['account']['referrals'][0]
        self.assertEqual(referral['full_name'], POLICY['fallback'])
        self.assertEqual(next(row for row in invitee.call('leaderboard?kind=battle&period=all')['rows'] if row['mine'])['name'], POLICY['fallback'])
        room = invitee.call('arena', {'action': 'create', 'public': True})
        listing = inviter.call('arena', {'action': 'list'})['rooms']
        self.assertEqual(next(row for row in listing if row['code']==room['code'])['name'], POLICY['fallback'])
        join = inviter.call('arena', {'action': 'join', 'code': room['code']})
        self.assertEqual(inviter.call('arena', {'action': 'state', **join})['opponent'], POLICY['fallback'])
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT full_name FROM students WHERE account_id=?', (second['account']['id'],)).fetchone()[0], '0912345678')
        invitee.call('arena', {'action': 'accept', **room})
        self.server.arena.rooms[room['code']]['readyAt'] = 0
        invitee.call('arena', {'action': 'state', **room})
        invitee.call('arena', {'action': 'leave', **room})
        with connect(self.path, True) as db:
            member = db.execute('SELECT duel_id,result_json FROM arena_members WHERE token_hash=?', (hashlib.sha256(room['token'].encode()).hexdigest(),)).fetchone()
            legacy = json.loads(member['result_json'])
            legacy.update(opponent='dcm', players=['0912345678', 'Minh Anh'])
            db.execute('UPDATE arena_members SET result_json=? WHERE token_hash=?', (json.dumps(legacy), hashlib.sha256(room['token'].encode()).hexdigest()))
            sid = db.execute('SELECT id FROM students WHERE account_id=?', (second['account']['id'],)).fetchone()[0]
            ay = db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?', (sid,)).fetchone()[0]
            teacher = db.execute('INSERT INTO teachers(full_name) VALUES (\'Giáo viên thử\')').lastrowid
            cid = db.execute('INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name,schedule,curriculum) VALUES (?,5,?,\'Lớp thử biệt danh\',\'Thứ 3\',\'Toán 5\')', (teacher, ay)).lastrowid
            eid = db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES (?,?,?)', (sid, cid, stamp())).lastrowid
            db.execute('INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES (?,?,\'internal\',?)', (second['account']['id'], eid, stamp()))
            lesson = db.execute('INSERT INTO class_sessions(class_id,title,starts_at) VALUES (?,\'Buổi thử\',\'2026-11-03T12:00:00Z\')', (cid,)).lastrowid
            assignment = db.execute('INSERT INTO class_assignments(session_id,title) VALUES (?,\'Bài thử\')', (lesson,)).lastrowid
        battle = invitee.call('session')['state']['battles'][str(member['duel_id'])]
        self.assertEqual(battle['opponent'], POLICY['fallback'])
        self.assertEqual(battle['players'], [POLICY['fallback'], 'Minh Anh'])
        self.assertEqual(invitee.call(f'classes/{cid}/ranking?assignment={assignment}')['rows'][0]['name'], POLICY['fallback'])

    def test_referral_first_purchase_reward_once_notification_and_calendar(self):
        inviter,initial,_,_=self.user()
        invitee,_,_,_=self.user(initial['state']['inviteCode'])
        key=secrets.token_hex(12)
        vip=invitee.call('dev/upgrade',{'requestKey':key})
        self.assertEqual(vip['account']['membership'],'VIP')
        rewarded=inviter.call('session')
        self.assertEqual(rewarded['account']['membership'],'VIP')
        self.assertEqual(len(rewarded['account']['notifications']),1)
        referral=rewarded['account']['referrals'][0]
        self.assertEqual(referral['reward_status'],'granted')
        self.assertIsNotNone(referral['first_vip_upgraded_at'])
        self.assertIsNotNone(referral['reward_granted_at'])
        invitee.call('dev/upgrade',{'requestKey':key})
        invitee.call('dev/upgrade',{'requestKey':secrets.token_hex(12)})
        final=inviter.call('session')
        self.assertEqual(final['account']['vipExpiresAt'],rewarded['account']['vipExpiresAt'])
        self.assertEqual(len(final['account']['notifications']),1)
        nid=final['account']['notifications'][0]['id']
        self.assertIsNotNone(inviter.call(f'notifications/{nid}/read',{})['account']['notifications'][0]['read_at'])
        self.server.review_upgrades=False
        try:
            with self.assertRaises(APIError):invitee.call('dev/upgrade',{'requestKey':secrets.token_hex(12)})
        finally:self.server.review_upgrades=True

    def test_arena_auth_identity_and_single_award(self):
        first,_,_,_=self.user()
        second,_,_,_=self.user()
        settings={'difficulty':0,'scope':'weekly','grade':1,'name':'Forged'}
        room=first.call('arena',{'action':'create',**settings})
        with self.assertRaises(APIError):first.call('arena',{'action':'join','code':room['code'],**settings})
        join=second.call('arena',{'action':'join','code':room['code'],**settings})
        self.assertEqual(first.call('arena',{'action':'state',**room})['status'],'challenged')
        with self.assertRaises(APIError):second.call('arena',{'action':'accept',**join})
        first.call('arena',{'action':'accept',**room})
        self.server.arena.rooms[room['code']]['readyAt']=0
        first.call('arena',{'action':'state',**room})
        with self.assertRaises(APIError):second.call('arena',{'action':'state',**room})
        for index in range(5):
            with self.server.arena.lock:
                answer=self.server.arena.rooms[room['code']]['questions'][index]['answer']
            result=first.call('arena',{'action':'answer',**room,'index':index,'answer':answer})
            self.server.arena.rooms[room['code']]['nextAt']=0
            result=first.call('arena',{'action':'state',**room})
        self.assertEqual(result['result']['outcome'],'win')
        first.call('arena',{'action':'state',**room})
        second.call('arena',{'action':'state',**join})
        self.assertEqual(first.call('session')['state']['points'],1002)
        self.assertEqual(second.call('session')['state']['points'],1000)
        self.assertEqual(first.call('leaderboard?kind=battle&period=all')['rows'][0]['value'],1002)


    def test_rabbit_companion_persists_and_reaches_opponent_and_leaderboard(self):
        client,_,login,password=self.user()
        selected=client.call('mascot',{'mascot':'rabbit'})
        self.assertEqual(selected['state']['mascot'],'rabbit')
        other=Client(self.server)
        self.assertEqual(other.call('auth/login',{'login':login,'password':password})['state']['mascot'],'rabbit')
        self.assertTrue(any(row['mine'] and row['mascot']=='rabbit' for row in client.call('leaderboard?kind=battle&period=all')['rows']))
        room=client.call('arena',{'action':'create','scope':'weekly','public':True})
        friend,_,_,_=self.user()
        self.assertEqual(next(row for row in friend.call('arena',{'action':'list'})['rooms'] if row['code']==room['code'])['mascot'],'rabbit')
        join=friend.call('arena',{'action':'join','code':room['code']})
        client.call('arena',{'action':'accept',**room})
        self.server.arena.rooms[room['code']]['readyAt']=0
        view=friend.call('arena',{'action':'state',**join})
        self.assertEqual(view['battle']['opponentMascot'],'rabbit')
        with self.assertRaises(APIError):client.call('mascot',{'mascot':'unknown'})
        with self.assertRaises(APIError):client.call('mascot',{'mascot':['rabbit']})


    def test_dog_companion_persists_and_reaches_opponent_and_leaderboard(self):
        client,_,login,password=self.user()
        selected=client.call('mascot',{'mascot':'dog'})
        self.assertEqual(selected['state']['mascot'],'dog')
        other=Client(self.server)
        self.assertEqual(other.call('auth/login',{'login':login,'password':password})['state']['mascot'],'dog')
        self.assertTrue(any(row['mine'] and row['mascot']=='dog' for row in client.call('leaderboard?kind=battle&period=all')['rows']))
        room=client.call('arena',{'action':'create','scope':'weekly','public':True})
        friend,_,_,_=self.user()
        self.assertEqual(next(row for row in friend.call('arena',{'action':'list'})['rooms'] if row['code']==room['code'])['mascot'],'dog')
        join=friend.call('arena',{'action':'join','code':room['code']})
        client.call('arena',{'action':'accept',**room})
        self.server.arena.rooms[room['code']]['readyAt']=0
        view=friend.call('arena',{'action':'state',**join})
        self.assertEqual(view['battle']['opponentMascot'],'dog')
        with self.assertRaises(APIError):client.call('mascot',{'mascot':'unknown'})
        with self.assertRaises(APIError):client.call('mascot',{'mascot':['dog']})


if __name__=='__main__':unittest.main()
