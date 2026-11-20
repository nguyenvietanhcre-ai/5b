"""Lesson reading completion stays separate from fixed checks, on disposable stores."""
import json,secrets,unittest
from backend import platform_api as api,study_retake,family_personal
import test_restructure_round11 as fixtures

class KnowledgeCompletionTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.KnowledgeTests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.KnowledgeTests.tearDownClass.__func__)
    setUp=fixtures.KnowledgeTests.setUp
    actor=fixtures.KnowledgeTests.actor
    call=fixtures.KnowledgeTests.call
    logical=fixtures.KnowledgeTests.logical
    counts=fixtures.KnowledgeTests.counts
    bundle=fixtures.KnowledgeTests.bundle

    def prepare(self):
        bundle=self.bundle();self.provider.knowledge.install(bundle)
        client=self.actor();other=self.actor();self.call(client,'catalogue');self.call(other,'catalogue')
        return bundle,client,other,bundle['lessons'][0]['lessonKey']

    def test_mark_replay_is_private_no_answer_no_solution_assets_no_wallet_or_exam(self):
        bundle,client,other,key=self.prepare();before=self.counts();main=self.logical()
        marked=self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':1})
        self.assertTrue(marked['progress']['completed']);self.assertTrue(marked['progress']['markedComplete'])
        self.assertFalse(marked['progress']['checked']);self.assertEqual(marked['progress']['attemptCount'],0)
        self.assertEqual(self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':1}),marked)
        lesson=self.call(client,'knowledge/'+key)
        self.assertEqual(lesson['progress'],marked['progress']);self.assertIsNone(lesson['lesson']['video']);self.assertEqual(lesson['lesson']['materials'],[])
        for field in ('correctAnswer','expectedAnswer','solution'):self.assertNotIn(field,json.dumps(lesson))
        self.assertFalse(self.call(other,'knowledge/'+key)['progress']['completed'])
        sha=bundle['assets'][1]['sha256']
        with self.assertRaises(api.APIError):self.call(client,'knowledge/'+key+'/asset?revision=1&sha='+sha)
        self.assertEqual(self.counts(),before);self.assertEqual(self.logical(),main)
        self.assertEqual(self.call(client,'history')['items'],[])
        checked=self.call(client,'knowledge/'+key+'/check',{'requestKey':secrets.token_hex(12),'lessonRevision':1,'answer':'0'})
        self.assertTrue(checked['progress']['checked']);self.assertEqual(checked['progress']['attemptCount'],1)
        self.assertTrue(self.call(client,'knowledge/'+key+'/asset?revision=1&sha='+sha)['_local_binary'])
        with self.assertRaises(api.APIError):self.call(other,'knowledge/'+key+'/asset?revision=1&sha='+sha)

    def test_mark_pins_revision_and_does_not_modify_immutable_lessons_or_checks(self):
        bundle,client,other,key=self.prepare();self.provider.knowledge.install(self.bundle(2))
        with api.connect(self.pilot) as db:before=[tuple(row) for row in db.execute('SELECT * FROM knowledge_lessons')]
        self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':1})
        self.assertTrue(self.call(client,'knowledge/'+key+'?revision=1')['progress']['completed'])
        self.assertFalse(self.call(client,'knowledge/'+key)['progress']['completed'])
        with api.connect(self.pilot) as db:
            self.assertEqual([tuple(row) for row in db.execute('SELECT * FROM knowledge_lessons')],before)
            self.assertEqual(db.execute('SELECT count(*) FROM knowledge_checks').fetchone()[0],0)
        for invalid in (None,True,'1',0,-1,99):
            with self.assertRaises(api.APIError):self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':invalid})
        for invalid in ({},{'lessonRevision':1,'studentId':999}):
            with self.assertRaises(api.APIError):self.call(client,'knowledge/'+key+'/complete',invalid)

    def test_completion_guards_csrf_grade_archived_and_learning_feature(self):
        bundle,client,other,key=self.prepare()
        client.csrf='invalid-csrf'
        with self.assertRaises(api.APIError):self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':1})
        wrong_grade=self.actor(grade=4)
        with self.assertRaises(api.APIError):self.call(wrong_grade,'knowledge/'+key+'/complete',{'lessonRevision':1})
        with api.connect(self.main,True) as db:
            settings=db.execute("SELECT value_json FROM system_settings WHERE name='platform'").fetchone()[0]
            db.execute("UPDATE system_settings SET value_json=json_set(value_json,'$.learning_open',0) WHERE name='platform'")
        with self.assertRaises(api.APIError):self.call(other,'knowledge/'+key+'/complete',{'lessonRevision':1})
        with api.connect(self.main,True) as db:db.execute("UPDATE system_settings SET value_json=? WHERE name='platform'",(settings,))
        with api.connect(self.pilot,True) as db:
            db.execute('INSERT INTO staff_knowledge_drafts VALUES(?,?,?,?,?)',(key,1,1,'{}',1))
        with self.assertRaises(api.APIError):self.call(other,'knowledge/'+key+'/complete',{'lessonRevision':1})
        # Existing archived read/check rights remain as before this change.
        self.assertEqual(self.call(other,'knowledge/'+key)['lesson']['lessonKey'],key)

    def test_personal_summary_and_continue_use_mark_without_counting_twice_after_check(self):
        bundle,client,other,key=self.prepare();self.call(client,'knowledge/'+key)
        client.path='/api/v1/state'
        with api.connect(self.main) as db:
            session=api.read_session(client,db)
            self.assertEqual(study_retake.continuation(db,session,self.provider)['lessonKey'],key)
            before=family_personal.summary(db,session,self.provider)['study']['completedLessons']
        self.call(client,'knowledge/'+key+'/complete',{'lessonRevision':1})
        with api.connect(self.main) as db:
            summary=family_personal.summary(db,session,self.provider)
            self.assertIsNone(summary['continueStudy']);self.assertEqual(summary['study']['completedLessons'],before+1)
        self.call(client,'knowledge/'+key+'/check',{'requestKey':secrets.token_hex(12),'lessonRevision':1,'answer':'0'})
        with api.connect(self.main) as db:self.assertEqual(family_personal.summary(db,session,self.provider)['study']['completedLessons'],before+1)
        other.path='/api/v1/state'
        with api.connect(self.main) as db:
            sibling=api.read_session(other,db)
            self.assertEqual(family_personal.summary(db,sibling,self.provider)['study']['completedLessons'],0)

if __name__=='__main__':unittest.main()
