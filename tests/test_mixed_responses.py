import json,secrets,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.answers import requires_choice,validate_choices,propose_choices
from backend.arena import Arena,ArenaError
from backend.database import initialize
from backend import platform_api as api
from backend.staff_api import create_first_admin,save_question
from test_platform_api import Client


def bundle():
    return propose_choices([{'label':'Dài','value':'12','unit':'cm'},{'label':'Rộng','value':'8','unit':'cm'}],[
        {'values':['8','12'],'reason':'Đảo thứ tự chiều dài và chiều rộng.'},
        {'values':['24','16'],'reason':'Dùng chu vi thay nửa chu vi nên gấp đôi cả hai cạnh.'},
        {'values':['16','4'],'reason':'Nhầm quan hệ tổng và hiệu khi tìm hai cạnh.'}])


class ChoicePolicyTests(unittest.TestCase):
    def test_structural_cases_and_single_decimal(self):
        for q in [{'answerShape':'parts'},{'answerShape':'objects'},{'multipleAnswers':True},{'answerCount':2},{'answerKind':'ordered'},{'inputGuide':{'labels':['A','B']}},{'prompt':'a) Tính cạnh dài. b) Tính cạnh rộng.'}]:
            self.assertTrue(requires_choice(q),q)
        self.assertFalse(requires_choice({'correctAnswer':'0,5','answerKind':'number','inputGuide':{'labels':['Diện tích']}}))

    def test_complete_distractors_require_reasons_not_random_filler(self):
        q=bundle();self.assertEqual(len(q['options']),4)
        self.assertTrue(all('Dài:' in o and 'Rộng:' in o and o.count('cm')==2 for o in q['options']))
        self.assertEqual(q['reviewStatus'],'draft-suggestions')
        with self.assertRaises(ValueError):propose_choices([{'label':'A','value':'2'}],[])
        with self.assertRaises(ValueError):validate_choices('1/2',['1/2','0,5','2','3'],['Giải thích đủ dài']*4)
        with self.assertRaises(ValueError):validate_choices(q['answer'],[q['answer'],'Dài: 9 cm',*q['options'][2:]],q['choiceRationales'],['Dài','Rộng'])
        with self.assertRaises(ValueError):propose_choices([{'label':'A','value':'0,5'}],[{'values':[v],'reason':'Một lỗi giải cần được giải thích.'} for v in ['1/2','2','3']])


class MixedArenaTests(unittest.TestCase):
    def setUp(self):
        self.q=bundle();self.arena=Arena()
        qs=[{'id':str(i),'text':'Câu QA có hai đại lượng','difficulty':0,'responseMode':'choice','answer':self.q['answer'],'options':self.q['options'],'steps':[]} for i in range(20)]
        with patch('backend.arena.time.time',return_value=1000):
            self.a=self.arena.handle({'action':'create','name':'Bạn An','grade':5},lambda *args:qs)
            self.b=self.arena.handle({'action':'join','name':'Bạn Bình','grade':5,'code':self.a['code']})
            self.arena.handle({**self.a,'action':'accept'})
        self.at(1003)

    def at(self,now,actor=None,action='state',answer=None):
        with patch('backend.arena.time.time',return_value=now):return self.arena.handle({**(actor or self.a),'action':action,'index':0,'answer':answer})

    def test_choice_defense_keeps_full_three_seconds_and_one_submission(self):
        shown=self.at(1004,self.b)['battle']['questions'][0]
        self.assertEqual(len(shown['options']),4);self.assertNotIn('answer',shown)
        with self.assertRaises(ArenaError):self.at(1004,self.b,'answer','Không thuộc phương án')
        self.assertIsNone(self.at(1004,self.b)['battle']['answer'])
        pending=self.at(1010,self.a,'answer',self.q['answer'])['battle'];self.assertEqual(pending['opponentHp'],100)
        result=self.at(1012.999,self.b,'answer',self.q['answer'])['battle']
        self.assertEqual((result['hp'],result['damage'],result['correct']),(90,10,1))
        self.assertEqual(self.at(1013,self.b,'answer',self.q['options'][1])['battle']['hp'],90)

    def test_choice_wrong_or_late_defense_stays_twenty(self):
        self.at(1010,self.a,'answer',self.q['answer'])
        result=self.at(1011,self.b,'answer',self.q['options'][1])['battle'];self.assertEqual(result['hp'],80)
        self.setUp();self.at(1010,self.a,'answer',self.q['answer'])
        self.assertEqual(self.at(1013,self.b,'answer',self.q['answer'])['battle']['hp'],80)


class MixedExamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True);cls.tmp=tempfile.TemporaryDirectory(dir='work');cls.path=Path(cls.tmp.name)/'mixed.sqlite3'
        initialize(cls.path);api.seed_catalog(cls.path);create_first_admin(cls.path,'mixed-admin','Quản trị QA','QA-only-Mixed-2026')
        cls.server=SimpleNamespace(database_path=cls.path,review_upgrades=False,arena=Arena())

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_new_complex_authoring_and_mixed_exam_server_grading(self):
        c=Client(self.server);c.call('auth/register',{'login':'mixed-'+secrets.token_hex(5),'password':'QA-only-Mixed-2026','name':'Bạn thử','birthYear':api.academic()[0]-10})
        q=bundle()
        with api.connect(self.path,True) as db:
            user=dict(db.execute("SELECT * FROM staff_users WHERE login='mixed-admin'").fetchone())
            topic=db.execute("INSERT INTO topics(grade_id,title,client_key) VALUES (5,'Chuyên đề QA hỗn hợp','qa-mixed')").lastrowid
            body={'grade':5,'topicId':topic,'prompt':'a) Tìm dài. b) Tìm rộng. (QA giả)','answer':q['answer'],'answerShape':'objects','responseType':'typed','answerTargets':['Dài','Rộng'],'options':q['options'],'choiceRationales':q['choiceRationales'],'steps':'QA kiểm tra đủ hai kết quả.','thinking':'QA','difficulty':1,'week':1,'status':'published'}
            with self.assertRaises(api.APIError):save_question(db,user,{**body,'options':[]})
            saved=save_question(db,user,body)
            row=db.execute('SELECT id,grading_rule_json FROM question_versions WHERE question_id=?',(saved['id'],)).fetchone()
            self.assertEqual(json.loads(row['grading_rule_json'])['responseType'],'choice')
            for value in ('5','6'):save_question(db,user,{**body,'prompt':'QA một đáp số '+value,'answer':value,'answerKind':'number','answerShape':'single','responseType':'typed','answerTargets':[],'options':[],'choiceRationales':[]})
        exam=c.call('exams',{'requestKey':secrets.token_hex(12),'topic':'qa-mixed','count':3})['exam']
        shown=c.call('exams/'+exam['id'])['exam'];choice=next(q for q in shown['questions'] if q['responseMode']=='choice');typed=next(q for q in shown['questions'] if q['responseMode']=='typed')
        self.assertNotIn('answer',choice);self.assertNotIn('options',typed)
        with self.assertRaises(api.APIError):c.call('exams/'+exam['id']+'/answers',{'position':int(choice['id']),'answer':'Bịa đáp án'})
        with api.connect(self.path) as db:
            rows=list(db.execute('SELECT i.position,v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=? ORDER BY i.position',(exam['id'],)))
        for row in rows:c.call('exams/'+exam['id']+'/answers',{'position':row['position'],'answer':str(json.loads(row['grading_rule_json'])['answer'])})
        result=c.call('exams/'+exam['id']+'/submit',{})['exam'];self.assertEqual(result['score'],10)
        self.assertEqual(c.call('exams/'+exam['id']+'/submit',{})['exam'],result)
