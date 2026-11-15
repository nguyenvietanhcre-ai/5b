"""New short-answer imports, no four choices or distractor rationales required."""
import unittest
from test_mcq_import import MCQTests
from backend import platform_api as api
from backend.mcq_import import ImportFailure


class TypedImportTests(unittest.TestCase):
    setUpClass=classmethod(MCQTests.setUpClass.__func__)
    tearDownClass=classmethod(MCQTests.tearDownClass.__func__)
    setUp=MCQTests.setUp
    import_=MCQTests.import_
    user=MCQTests.user
    expire=MCQTests.expire
    exam=MCQTests.exam
    count=MCQTests.count

    def typed(self):
        from dataclasses import replace
        self.server.free_vip_pilot=replace(self.server.free_vip_pilot,response_mode='typed')
        for q in self.package['questions']:
            q['correctAnswer']=q['choices'][0]['text'];q['answerKind']='number';q['responseType']='short-answer'
            for key in ('choices','choiceRationales','correctChoiceId'):q.pop(key)

    def test_import_without_choices_and_equivalent_fraction_scores(self):
        self.typed();result=self.import_(allow_draft_qa=True)
        self.assertEqual(result['insertedVersions'],10)
        c,_=self.user();exam=self.exam(c,setIndex=1)
        self.assertEqual(exam['responseMode'],'typed')
        for i,q in enumerate(exam['questions']):
            self.assertNotIn('answer',q);self.assertNotIn('options',q)
            c.call('exams/'+exam['id']+'/answers',{'position':i+1,'answer':f'{(i+2)*2}/2'})
        self.assertEqual(c.call('exams/'+exam['id']+'/submit',{})['exam']['score'],10)
        self.assertEqual(self.import_(allow_draft_qa=True)['insertedVersions'],0)

    def test_invalid_numeric_answer_never_commits_partial_import(self):
        self.typed();self.package['questions'][5]['correctAnswer']='1/0'
        with self.assertRaises(ImportFailure):self.import_(allow_draft_qa=True)
        self.assertEqual(self.count('pilot_content'),0)
