"""Permanent purchased-credit usage against isolated main and native stores."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import secrets
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend import platform_api as api, purchased_credits as credits
from backend.database import initialize
from backend.local_pilot import LocalPilot
import test_family_local_pilot as base


class PurchasedCreditTests(unittest.TestCase):
    PASSWORD = base.FamilyLocalPilotTests.PASSWORD
    setUpClass = classmethod(base.FamilyLocalPilotTests.setUpClass.__func__)
    setUp = base.FamilyLocalPilotTests.setUp
    family_actor = base.FamilyLocalPilotTests.family_actor
    call = base.FamilyLocalPilotTests.call

    def configure_native(self):
        restructure = Path(os.environ.get('CREDIT_RESTRUCTURE_INPUTS', 'restructure-inputs'))
        self.provider = LocalPilot(self.main, self.pilot, self.inputs, restructure_inputs=restructure)
        self.server.local_pilot = self.provider
        self.server.native_python_backend = True

    def credit_lines(self, db, student_id, packs):
        info = db.execute('SELECT c.family_id,s.account_id FROM family_children c JOIN students s ON s.id=c.student_id '
                          'WHERE s.id=?', (student_id,)).fetchone()
        price = 50000 * sum(packs.values())
        order = db.execute('INSERT INTO family_cart_orders(family_id,reference,amount,created_at,quote_hash,cart_revision,'
                           'purchaser_json,checkout_snapshot_json) VALUES (?,?,?,?,?,1,?,?)',
                           (info['family_id'], secrets.token_hex(12), price, api.stamp(), '0' * 64, '{}', '{}')).lastrowid
        lines = {}
        for sku, quantity in packs.items():
            pack = credits.PACKS[sku]
            item = {'sku': sku, 'creditKind': pack['unit'], 'credits': pack['quantity'], 'quantity': quantity}
            lines[sku] = db.execute('INSERT INTO family_cart_product_order_items(order_id,student_id,account_id,type,'
                                    'product_key,product_ref,quantity,cart_item_revision,item_json,pin_json) '
                                    "VALUES (?,?,?,'credits',?,?,?,1,?,'{}')",
                                    (order, student_id, info['account_id'], 'credits:' + sku, sku, quantity,
                                     api.packed(item))).lastrowid
        return order, info['account_id'], lines

    def grant(self, student_id, **packs):
        with api.connect(self.main, True) as db:
            order, aid, lines = self.credit_lines(db, student_id, packs)
            for sku, line in lines.items():
                grants = [credits.grant(db, aid, student_id, sku, line) for _ in range(2)]
                self.assertEqual(grants[0], grants[1])
                db.execute('UPDATE family_cart_product_order_items SET applied_at=? WHERE id=?', (api.stamp(), line))
            db.execute("UPDATE family_cart_orders SET status='paid',paid_at=?,confirmed_source='staff' WHERE id=?",
                       (api.stamp(), order))
        return order, lines

    def assert_status(self, status, fn):
        with self.assertRaises(api.APIError) as caught:
            fn()
        self.assertEqual(caught.exception.status, status)

    def assert_balance(self, client, questions, exams):
        value = client.learner('purchased-credits')
        self.assertEqual((value['questionsRemaining'], value['examsRemaining'], value['expiresAt']),
                         (questions, exams, None))
        return value

    def main_quote(self, client, sku):
        selector = {'category': 'combined', 'count': 10, 'difficulty': 0, 'funding': sku}
        quote = client.learner('exams/quote', selector)
        body = {**selector, 'quoteId': quote['quoteId'], 'requestKey': secrets.token_hex(12), 'confirmPurchased': True}
        return quote, body

    def native_quote(self, client, sku, *, count=10, pool='all'):
        selector = {'category': 'combined', 'count': count, 'pool': pool, 'funding': sku,
                    'intentId': secrets.token_hex(12)}
        quote = self.call(client, 'practice/quote', selector)
        body = {'intentId': selector['intentId'], 'requestKey': secrets.token_hex(12), 'quoteId': quote['quoteId'],
                'confirmWallet': False, 'funding': sku, 'confirmPurchased': True}
        return quote, body

    def test_grant_atomic_per_exact_line_and_keeps_balances_permanent(self):
        client, state = self.family_actor(grade=4)
        sid = state['selectedChildId']
        with self.assertRaises(RuntimeError):
            with api.connect(self.main, True) as db:
                _, aid, lines = self.credit_lines(db, sid, {credits.QUESTIONS: 2})
                self.assert_status(409, lambda: credits.grant(db, aid, sid + 1, credits.QUESTIONS, lines[credits.QUESTIONS]))
                credits.grant(db, aid, sid, credits.QUESTIONS, lines[credits.QUESTIONS])
                self.assertEqual(credits.balance(db, sid)['questionsRemaining'], 0)
                raise RuntimeError('Rollback the complete settlement')
        self.assert_balance(client, 0, 0)
        self.grant(sid, **{credits.QUESTIONS: 2, credits.EXAMS: 1})
        self.assert_balance(client, 200, 10)
        with patch.object(api, 'now', return_value=api.now() + timedelta(days=1000)):
            with api.connect(self.main) as db:
                self.assertEqual(credits.balance(db, sid), {'questionsRemaining': 200, 'examsRemaining': 10, 'expiresAt': None})
        self.email = secrets.token_hex(8) + '@example.test'
        another, _ = self.family_actor(grade=4)
        self.assert_balance(another, 0, 0)

    def test_main_quote_confirm_independent_funding_exact_retries_and_free_retake(self):
        client, state = self.family_actor(grade=4)
        api.seed_catalog(self.main)
        self.grant(state['selectedChildId'], **{credits.QUESTIONS: 1, credits.EXAMS: 1})
        status = self.assert_balance(client, 100, 10)
        self.assertEqual([(p['sku'], p['eligible']) for p in status['products']], [(credits.QUESTIONS, True), (credits.EXAMS, True)])
        quote, body = self.main_quote(client, credits.QUESTIONS)
        self.assertEqual(quote['purchased']['quantity'], 10)
        self.assert_balance(client, 100, 10)
        self.assert_status(409, lambda: client.learner('exams', {**body, 'confirmPurchased': False}))
        self.assert_status(409, lambda: client.learner('exams', {**body, 'funding': credits.EXAMS}))
        exam = client.learner('exams', body)['exam']
        self.assertEqual(exam['purchasedCredits']['quantity'], 10)
        self.assertEqual(client.learner('exams', dict(reversed(list(body.items()))))['exam']['id'], exam['id'])
        self.assert_status(409, lambda: client.learner('exams', {**body, 'difficulty': 1}))
        client.learner('exams/' + exam['id'] + '/submit', {})
        self.assert_balance(client, 90, 10)
        _, one_exam = self.main_quote(client, credits.EXAMS)
        complete = client.learner('exams', one_exam)['exam']
        self.assertEqual((len(complete['questions']), complete['purchasedCredits']['quantity']), (10, 1))
        self.assert_balance(client, 90, 9)
        self.assert_status(409, lambda: client.learner('exams', {**one_exam, 'requestKey': secrets.token_hex(12)}))
        client.learner('exams/' + complete['id'] + '/submit', {})
        second = client.learner('exams/' + complete['id'] + '/retake', {'requestKey': secrets.token_hex(12)})['exam']
        self.assertNotIn('purchasedCredits', second)
        self.assert_balance(client, 90, 9)
        with api.connect(self.main) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM daily_usage').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_question_usage').fetchone()[0], 10)

    def test_native_usage_commits_with_attempt_fails_closed_and_recovers_link(self):
        self.configure_native()
        client, state = self.family_actor()
        sid = state['selectedChildId']
        mock = self.call(client, 'orders', {'sku': 'qa.questions.100', 'requestKey': secrets.token_hex(12)})
        self.call(client, 'mock-confirm', {'orderId': mock['orderId']})
        self.assert_balance(client, 0, 0)
        self.grant(sid, **{credits.QUESTIONS: 1, credits.EXAMS: 1})
        self.assertEqual(self.call(client, 'catalogue')['purchasedCredits']['questionsRemaining'], 100)
        quote, body = self.native_quote(client, credits.QUESTIONS, count=2, pool='paid')
        self.assertEqual((quote['purchased']['quantity'], quote['vip'], quote['private']), (2, 0, 0))
        race = [client.copy_capability(), client.copy_capability()]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda actor: self.call(actor, 'practice/exams', body)['exam'], race))
        exam = results[0]
        self.assertEqual(exam['id'], results[1]['id'])
        self.assertEqual(self.call(client, 'exams/' + exam['id'] + '/receipt')['purchasedCredits']['quantity'], 2)
        self.assert_balance(client, 98, 10)
        self.call(client, 'exams/' + exam['id'] + '/submit', {})
        _, complete_body = self.native_quote(client, credits.EXAMS)
        complete = self.call(client, 'practice/exams', complete_body)['exam']
        self.assertEqual((len(complete['questions']), complete['purchasedCredits']['quantity']), (10, 1))
        self.assert_balance(client, 98, 9)
        with api.connect(self.pilot) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_usage').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM wallet_debits').fetchone()[0], 0)
        self.server.local_pilot = None
        self.assertEqual(self.assert_balance(client, None, None)['products'][0]['eligibleCounts'], [])
        replacement = self.pilot.with_name('replacement.sqlite3')
        initialize(replacement)
        self.server.local_pilot = SimpleNamespace(path=replacement, practice=None)
        self.assertFalse(self.assert_balance(client, None, None)['available'])
        self.server.local_pilot = self.provider
        self.assert_balance(client, 98, 9)

    def test_absent_or_withdrawn_native_sources_leave_paid_balances_intact(self):
        self.configure_native()
        client, state = self.family_actor()
        self.grant(state['selectedChildId'], **{credits.EXAMS: 1})
        self.assert_status(400, lambda: self.native_quote(client, credits.EXAMS, count=5))
        topics = self.call(client, 'catalogue')['topics']
        topic = next(row['key'] for row in topics if row['totalCount'] < 10)
        self.assert_status(503, lambda: self.call(client, 'practice/quote', {
            'category': 'content', 'topicKey': topic, 'count': 10, 'funding': credits.EXAMS, 'intentId': secrets.token_hex(12)}))
        _, body = self.native_quote(client, credits.EXAMS)
        with api.connect(self.pilot, True) as db:
            row = db.execute('SELECT quote_json FROM purchased_credit_quotes WHERE quote_id=?', (body['quoteId'],)).fetchone()
            selection = json.loads(row[0])['selection']
            db.execute("UPDATE question_versions SET status='retired' WHERE id=?", (selection[0]['versionId'],))
        self.assert_status(409, lambda: self.call(client, 'practice/exams', body))
        self.assert_balance(client, 0, 10)
        _, retry = self.native_quote(client, credits.EXAMS)
        with patch.object(api, 'exam_view', side_effect=api.APIError('Lỗi tạm sau khi ghi lượt.', 503)):
            self.assert_status(503, lambda: self.call(client, 'practice/exams', retry))
        self.assert_balance(client, 0, 10)
        with api.connect(self.pilot) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM purchased_credit_usage').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM exam_attempts').fetchone()[0], 0)
        self.call(client, 'practice/exams', retry)
        self.assert_balance(client, 0, 9)

    def test_main_counts_native_debits_after_grade_changes(self):
        self.configure_native()
        client, state = self.family_actor()
        sid = state['selectedChildId']
        self.grant(sid, **{credits.EXAMS: 1})
        _, first_body = self.native_quote(client, credits.EXAMS)
        first = self.call(client, 'practice/exams', first_body)['exam']
        self.call(client, 'exams/' + first['id'] + '/submit', {})
        api.seed_catalog(self.main)
        with api.connect(self.main, True) as db:
            db.execute('UPDATE family_children SET declared_grade=4 WHERE student_id=?', (sid,))
        quote, body = self.main_quote(client, credits.EXAMS)
        self.assertEqual(quote['purchased']['remainingBefore'], 9)
        second = client.learner('exams', body)['exam']
        self.assertNotEqual(first['reference'], second['reference'])
        self.assert_balance(client, 0, 8)

    def test_unfunded_paid_quote_does_not_replace_free_limit(self):
        client, _ = self.family_actor(grade=4)
        api.seed_catalog(self.main)
        selector = {'category': 'combined', 'count': 10, 'difficulty': 0}
        first = client.learner('exams', {**selector, 'requestKey': secrets.token_hex(12)})['exam']
        client.learner('exams/' + first['id'] + '/submit', {})
        self.assert_status(429, lambda: client.learner('exams', {**selector, 'requestKey': secrets.token_hex(12)}))
        self.assert_status(402, lambda: self.main_quote(client, credits.QUESTIONS))
