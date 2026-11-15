import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.answers import matches, validate_rule
from backend.arena import Arena
from backend.database import initialize
from backend.platform_api import academic, connect, seed_catalog
from test_platform_api import Client


class AnswerRulesTests(unittest.TestCase):
    def test_exact_numbers_and_text(self):
        for value in ['0,5','0.50','1/2','2/4',' 1 / 2 ', '５/１０']:
            self.assertTrue(matches(value, {'answer':'0.5'}), value)
        for value in ['', '1/0', 'NaN', 'Infinity', '1+1', '1 2', '0.50000000001', '5e1000000']:
            self.assertFalse(matches(value, {'answer':'0.5'}), value)
        self.assertTrue(matches(' < ', {'answer':'<'}))
        self.assertFalse(matches('0.5', {'answer':'0,5','answerKind':'text'}))

    def test_multiple_results_and_validation(self):
        self.assertTrue(matches('1/2;2', {'answer':'0,5;2','answerKind':'ordered'}))
        self.assertFalse(matches('2;1/2', {'answer':'0,5;2','answerKind':'ordered'}))
        self.assertTrue(matches('2;1/2', {'answer':'0,5;2','answerKind':'unordered'}))
        self.assertFalse(matches('2;2', {'answer':'0,5;2','answerKind':'unordered'}))
        for answer, kind in [('NaN','number'),('1;;2','ordered'),('3','unknown')]:
            with self.assertRaises(ValueError): validate_rule(answer,kind)


class DefenseTests(unittest.TestCase):
    def setUp(self):
        self.arena=Arena()
        questions=[{'id':str(i),'text':'Tính 1/4 + 1/4','answer':'1/2','difficulty':0,'steps':[]} for i in range(20)]
        with patch('backend.arena.time.time',return_value=1000):
            self.a=self.arena.handle({'action':'create','name':'Bạn An','grade':5}, lambda *args:questions)
            self.b=self.arena.handle({'action':'join','name':'Bạn Bình','grade':5,'code':self.a['code']})
            self.arena.handle({**self.a,'action':'accept'})
        self.room=self.arena.rooms[self.a['code']]
        self.at(1003)

    def at(self,now,player=None,action='state',**body):
        with patch('backend.arena.time.time',return_value=now):
            return self.arena.handle({**(player or self.a),'action':action,**body})

    def answer(self,now,player,answer):
        return self.at(now,player,'answer',index=0,answer=answer)['battle']

    def test_defense_reduces_damage_and_counts_both_correct_without_answer_leak(self):
        pending=self.answer(1010,self.a,'0,5')
        self.assertEqual((pending['opponentHp'],pending['resolved'],pending['defenseUntil']),(100,False,1013000))
        defender=self.at(1011,self.b)['battle']
        self.assertFalse(defender['attacking'])
        self.assertNotIn('answer',defender['questions'][0])
        self.assertNotIn('options',defender['questions'][0])
        blocked=self.answer(1012.999,self.b,'2/4')
        self.assertEqual((blocked['hp'],blocked['damage'],blocked['correct']),(90,10,1))
        self.assertTrue(blocked['resolved'])
        self.assertTrue(blocked['lastAttack']['defended'])
        repeated=self.answer(1013,self.b,'wrong')
        self.assertEqual((repeated['hp'],repeated['correct']),(90,1))
        self.assertEqual(self.at(1013)['battle']['correct'],1)

    def test_exact_boundary_is_late_and_settles_only_once(self):
        self.answer(1010,self.a,'1/2')
        late=self.answer(1013,self.b,'1/2')
        self.assertEqual((late['hp'],late['correct'],late['damage']),(80,0,20))
        self.assertEqual(self.at(1013.1,self.b)['battle']['hp'],80)

    def test_full_three_seconds_near_original_deadline_and_no_early_ko(self):
        self.room['players'][self.b['token']]['hp']=10
        deadline=self.room['deadline']
        pending=self.answer(deadline-.01,self.a,'1/2')
        self.assertFalse(pending['resolved'])
        self.assertEqual(pending['opponentHp'],10)
        self.assertFalse(self.at(deadline+1,self.b)['battle']['resolved'])
        end=self.answer(deadline+2.9,self.b,'1/2')
        self.assertEqual(end['hp'],0)
        self.assertEqual(end['damage'],10)
        self.assertEqual(self.at(deadline+6,self.b)['status'],'finished')

    def test_wrong_first_never_starts_defense_or_allows_second_submission(self):
        wrong=self.answer(1010,self.b,'9')
        self.assertIsNone(wrong['defenseUntil'])
        self.answer(1011,self.b,'1/2')
        hit=self.answer(1012,self.a,'1/2')
        self.assertEqual((hit['opponentHp'],hit['damage']),(80,20))

    def test_wrong_defense_full_damage_and_both_wrong_no_attack(self):
        self.answer(1010,self.a,'1/2')
        self.assertEqual(self.answer(1011,self.b,'9')['hp'],80)
        self.setUp()
        self.answer(1010,self.a,'9')
        result=self.answer(1011,self.b,'8')
        self.assertEqual((result['hp'],result['opponentHp'],result['roundReason']),(100,100,'both_wrong'))


class TypedExamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('work').mkdir(exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(dir=Path('work'))
        cls.path=Path(cls.directory.name)/'typed.sqlite3'
        initialize(cls.path);seed_catalog(cls.path)
        cls.server=SimpleNamespace(database_path=cls.path,review_upgrades=False,arena=Arena())

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    def user(self):
        client=Client(self.server)
        import secrets
        client.call('auth/register',{'login':'typed-'+secrets.token_hex(5),'password':'Testing-typed-2026','name':'Bạn học thử','birthYear':academic()[0]-10})
        return client

    def test_free_text_draft_equivalence_resume_and_submission_idempotency(self):
        client=self.user()
        exam=client.call('exams',{'requestKey':'typed-test-new-0001'})['exam']
        self.assertEqual(exam['responseMode'],'typed')
        self.assertNotIn('options',exam['questions'][0]);self.assertNotIn('answer',exam['questions'][0])
        with connect(self.path) as db:
            rules=[json.loads(r[0]) for r in db.execute('SELECT v.grading_rule_json FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id WHERE i.exam_id=? ORDER BY i.position',(exam['id'],))]
        for i,rule in enumerate(rules,1):
            # A correct numeric answer supplied in an equivalent notation.
            from backend.answers import number
            n=number(rule['answer'])
            value=f'{n.numerator*2}/{n.denominator*2}' if n is not None else rule['answer']
            client.call(f"exams/{exam['id']}/answers",{'position':i,'answer':value})
        resumed=client.call(f"exams/{exam['id']}")['exam']
        self.assertEqual(len(resumed['answers']),len(rules))
        self.assertEqual(client.call('session')['state']['exams'][exam['id']]['answers'],resumed['answers'])
        result=client.call(f"exams/{exam['id']}/submit",{})['exam']
        self.assertEqual(result['score'],10)
        self.assertTrue(all(q['correct'] for q in result['questions']))
        self.assertEqual(client.call(f"exams/{exam['id']}/submit",{})['exam']['score'],10)

    def test_wrong_and_cleared_answers_are_saved_without_choice_validation(self):
        client=self.user();exam=client.call('exams',{'requestKey':'typed-test-new-0002'})['exam'];eid=exam['id']
        client.call(f'exams/{eid}/answers',{'position':1,'answer':'Tự nghĩ ra một đáp án sai'})
        self.assertEqual(client.call(f'exams/{eid}')['exam']['answers']['1'],'Tự nghĩ ra một đáp án sai')
        client.call(f'exams/{eid}/answers',{'position':1,'answer':''})
        self.assertEqual(client.call(f'exams/{eid}/submit',{})['exam']['score'],0)
