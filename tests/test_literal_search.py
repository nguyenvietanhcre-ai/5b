"""Literal contains search under Durable Object's short LIKE-pattern limit."""
import secrets
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

from backend import admissions, payments, staff_api
from backend.database import initialize
from backend.platform_api import academic, packed, stamp


ROOT = Path(__file__).resolve().parents[1]
LONG_NAME = 'Nguyễn Trường Khánh Vân Ánh Dương Minh Ngọc'


class LiteralSearchTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='literal-search-',dir=ROOT/'work')
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name)/'search.sqlite3'
        initialize(path)
        self.db = sqlite3.connect(path)
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.setlimit(sqlite3.SQLITE_LIMIT_LIKE_PATTERN_LENGTH,50)
        self.assertGreater(len(LONG_NAME.encode('utf-8')),50)

    def handler(self, **query):
        return SimpleNamespace(path='/api/staff/search?'+urlencode(query))

    def account(self, name, *, grade=5, status='active', login=None):
        token = secrets.token_hex(6)
        aid = self.db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,status) VALUES (?,?,?,?,?,?)',
            ('QA-'+token,login or 'qa-'+token,academic()[0]-grade-5,'INV-'+token,stamp(),status)).lastrowid
        self.db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES (?,?,?,?)',
                        ('HS-'+token,name,grade,aid))
        return aid

    def order(self, account, reference):
        return self.db.execute("INSERT INTO payment_orders(account_id,reference,amount,created_at,status) VALUES (?,?,100000,?,'cancelled')",
                               (account,reference,stamp())).lastrowid

    def test_long_utf8_account_names_keep_grade_status_case_and_pagination(self):
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute('SELECT ? LIKE ?', (LONG_NAME,LONG_NAME)).fetchone()
        for i in range(27):
            self.account(LONG_NAME+' '+str(i))
        self.account(LONG_NAME,grade=4)
        suspended = self.account(LONG_NAME,status='suspended')
        result = staff_api.accounts(self.db,self.handler(q=LONG_NAME,grade=5,status='active',page=2))
        self.assertEqual((result['total'],len(result['rows']),result['page']),(27,2,2))
        self.assertEqual(staff_api.accounts(self.db,self.handler(q=LONG_NAME,grade=5,status='suspended'))['rows'][0]['id'],suspended)
        literal = self.account('Literal %_ name',login='qa-CASE-'+secrets.token_hex(3))
        self.account('Literal OTHER name')
        for term in ('%','_','%_','QA-case'):
            rows = staff_api.accounts(self.db,self.handler(q=term))['rows']
            self.assertEqual([row['id'] for row in rows],[literal])

    def test_content_titles_and_prompts_are_literal_and_keep_grade_latest_version(self):
        title = LONG_NAME+' %_'
        topic = self.db.execute("INSERT INTO topics(grade_id,title,theory_json,client_key) VALUES (5,?,'[]','literal')",(title,)).lastrowid
        other_topic = self.db.execute("INSERT INTO topics(grade_id,title,theory_json,client_key) VALUES (4,?,'[]','other')",(title,)).lastrowid
        self.db.execute("INSERT INTO topics(grade_id,title,theory_json,client_key) VALUES (5,'Plain title','[]','plain')")
        for grade,tid in ((5,topic),(4,other_topic)):
            self.db.execute("INSERT INTO lessons(grade_id,topic_id,kind,week_no,title,body_json) VALUES (?,?,'weekly',1,?,'[]')",(grade,tid,title))
            question = self.db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (?,?,?)',(grade,tid,'QA-%_-'+str(grade))).lastrowid
            for revision,prompt in ((1,'Old only prompt'),(2,title)):
                self.db.execute("INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,grading_rule_json,solution_steps_json,status,options_json) VALUES (?,?,1,1,?,?,?,'published',?)",
                    (question,revision,packed([{'type':'text','text':prompt}]),'{"answer":"2"}','[]','["1","2"]'))
        for kind in ('topics','lessons','questions'):
            for term in (LONG_NAME,'%','_'):
                result = staff_api.content_list(self.db,self.handler(q=term,kind=kind,grade=5))
                self.assertEqual(result['total'],1)
                self.assertEqual(result['rows'][0]['grade_id'],5)
        self.assertEqual(staff_api.content_list(self.db,self.handler(q='Old only prompt',kind='questions'))['total'],0)

    def test_payment_search_matches_long_referrer_and_literal_filters_together(self):
        referrer = self.account(LONG_NAME+' %_',login='referrer_literal')
        buyer = self.account('Buyer')
        stranger = self.account('Stranger')
        invite = self.db.execute('SELECT invite_code FROM accounts WHERE id=?',(referrer,)).fetchone()[0]
        self.db.execute('INSERT INTO account_referrals(inviter_account_id,invitee_account_id,invite_code,registered_at) VALUES (?,?,?,?)',
                        (referrer,buyer,invite,stamp()))
        matched = self.order(buyer,'PAY_%_LITERAL')
        self.order(stranger,'PAY-PLAIN')
        for filters in ({'q':LONG_NAME},{'referrer':LONG_NAME},{'q':'%_'},{'q':'pay_%','referrer':LONG_NAME},
                        {'q':'buyer','referrer':'_'},{'q':'%','referrer':'referrer_literal'}):
            result = staff_api.payment_list(self.db,self.handler(**filters))
            self.assertEqual([row['id'] for row in result['rows']],[matched])
            self.assertEqual(result['total'],1)
        self.assertEqual(staff_api.payment_list(self.db,self.handler(q='PLAIN',referrer=LONG_NAME))['total'],0)
        self.assertEqual(staff_api.payment_list(self.db,self.handler(q=LONG_NAME,page=2))['rows'],[])

    def receipt(self, transaction, reference, bank_reference, status='review'):
        return self.db.execute("INSERT INTO payment_receipts(provider,transaction_id,payload_hash,status,reason,amount,reference,bank,bank_account,bank_reference,received_at) VALUES ('sepay',?,?,?,'unknown_reference',100000,?,'ACB','123456789',?,?)",
                               (transaction,'0'*64,status,reference,bank_reference,stamp())).lastrowid

    def test_receipt_search_long_bank_reference_status_pagination_and_numeric_id(self):
        for i in range(27):
            self.receipt(1000+i,'REF-'+str(i),LONG_NAME+' %_')
        self.receipt(2000,'REF-IGNORED',LONG_NAME+' %_',status='ignored')
        self.receipt(3000,'REF-PLAIN','plain')
        result = payments.receipt_list(self.db,self.handler(q=LONG_NAME,status='review',page=2))
        self.assertEqual((result['total'],len(result['rows'])),(27,2))
        for term in ('%','_'):
            self.assertEqual(payments.receipt_list(self.db,self.handler(q=term))['total'],28)
        self.assertEqual(payments.receipt_list(self.db,self.handler(q='3000'))['rows'][0]['transaction_id'],3000)
        self.assertEqual(payments.receipt_list(self.db,self.handler(q='ref-plain'))['total'],1)

    def admission(self, parent, student='Student', reference=None):
        token = secrets.token_hex(6)
        return self.db.execute('INSERT INTO entrance_registrations(reference,request_key,payload_hash,parent_name,phone,student_name,grade,details_json,created_at,updated_at) VALUES (?,?,?,?,?,?,5,?,?,?)',
            (reference or 'DV-'+token,'REQ-'+token,'0'*64,parent,'0912345678',student,packed({'consent':True}),stamp(),stamp())).lastrowid

    def test_admission_search_long_names_and_literal_characters_preserve_pagination(self):
        for i in range(27):
            self.admission(LONG_NAME+' '+str(i))
        literal = self.admission('Parent literal %_',reference='DV_CASE_%_')
        self.admission('Parent other')
        long_student = self.admission('Parent plain',student=LONG_NAME)
        result = admissions.list_registrations(self.db,LONG_NAME,2)
        self.assertEqual((result['total'],len(result['rows'])),(28,3))
        self.assertNotIn('payload_hash',result['rows'][0])
        for term in ('%','_','dv_case'):
            self.assertEqual([row['id'] for row in admissions.list_registrations(self.db,term,1)['rows']],[literal])
        self.assertEqual(admissions.list_registrations(self.db,'Parent plain',1)['rows'][0]['id'],long_student)


if __name__ == '__main__':
    unittest.main()
