import unittest,secrets
from backend import platform_api as api,wallet_qa as wallet
from backend.answers import requires_choice
from backend.free_vip_pilot import create_exam
import test_local_pilot as base


class NativeResponsePolicyTests(unittest.TestCase):
    setUpClass=classmethod(base.LocalPilotTests.setUpClass.__func__)
    tearDownClass=classmethod(base.LocalPilotTests.tearDownClass.__func__)
    setUp=base.LocalPilotTests.setUp
    actor=base.LocalPilotTests.actor
    call=base.LocalPilotTests.call
    exam=base.LocalPilotTests.exam
    logical=base.LocalPilotTests.logical

    def test_catalogue_excludes_multi_component_typed_without_exposing_prompts(self):
        c=self.actor('VIP');cat=self.call(c,'catalogue')
        expected={q['contentKey'] for q in self.provider.typed['questions'] if not requires_choice(q)}
        self.assertEqual(set(cat['typedEligible']),expected);self.assertTrue(expected)
        self.assertLess(len(expected),49);self.assertEqual(len(cat['questions']),60)
        self.assertTrue(all('prompt' not in q and 'answer' not in q for q in cat['questions']))
        self.assertTrue(all(not q['typed'] for q in cat['questions'] if q['choiceRequired']))

    def test_forced_choice_cannot_be_bypassed_and_does_not_debit_on_rejection(self):
        c=self.actor('VIP');self.call(c,'catalogue');key=next(iter(self.provider.choice_required))
        before=self.call(c,'wallet');main=self.logical()
        for path,body in [('quote',{'contentKeys':[key],'responseMode':'typed'}),('exams',{'requestKey':secrets.token_hex(12),'contentKeys':[key],'responseMode':'typed'})]:
            with self.assertRaises(api.APIError) as caught:self.call(c,path,body)
            self.assertEqual(caught.exception.status,409)
        self.assertEqual(self.call(c,'wallet'),before);self.assertEqual(self.logical(),main)
        exam,_=self.exam(c,contentKeys=[key],responseMode='choice')
        self.assertEqual(exam['responseMode'],'choice');self.assertEqual(len(exam['questions'][0]['options']),4)

    def test_existing_typed_attempt_and_same_request_retry_keep_snapshot(self):
        c=self.actor('VIP');self.call(c,'catalogue');key=next(iter(self.provider.choice_required));config,_=self.provider.ensure_week()
        with api.connect(self.main) as main_db:main=api.read_session(c,main_db)
        with api.connect(self.pilot,True) as db:
            session=self.provider.principal(db,main,'VIP');selector={'contentKeys':[key],'responseMode':'typed'}
            quote=wallet.quote(db,session,selector,config)
            body={**selector,'requestKey':secrets.token_hex(12),'quoteId':quote['quoteId'],'confirmWallet':False}
            old=create_exam(db,session,body,config)
        before=self.call(c,'wallet')
        self.assertEqual(self.call(c,'exams/'+old['id'])['exam']['responseMode'],'typed')
        self.assertEqual(self.call(c,'exams',body)['exam']['id'],old['id'])
        self.assertEqual(self.call(c,'wallet'),before)
