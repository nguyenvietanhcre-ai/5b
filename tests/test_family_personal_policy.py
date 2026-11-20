"""Personal family policy focused tests; disposable databases only."""
import secrets
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from backend import platform_api as api, family_personal as personal, payments
from backend.learning_update import membership
import test_family_accounts as old

class PersonalPolicyTests(unittest.TestCase):
    PASSWORD=old.FamilyAccountsTests.PASSWORD
    setUp=old.FamilyAccountsTests.setUp
    consent=old.FamilyAccountsTests.consent
    register_body=old.FamilyAccountsTests.register_body
    register=old.FamilyAccountsTests.register
    full=old.FamilyAccountsTests.full
    assert_denied=old.FamilyAccountsTests.assert_denied

    def actor(self):
        self.email=secrets.token_hex(8)+'@example.test'
        client,state=self.register();self.full(client)
        return client,state

    def mapped(self,client,db):
        client.path='/api/v1/state';client.headers['X-Family-Context']=client.context
        return api.read_session(client,db)

    def code(self,client):
        return client.learner()['personalSummary']['referral']['code']

    def order(self,client,code='',tier='VIP'):
        body={'plan':tier,'period':'month','referralCode':code}
        with api.connect(self.path,True) as db:
            session=self.mapped(client,db)
            preview=payments.checkout_preview(db,session,body)
            body['checkout']={'accepted':True,'policyVersion':payments.CHECKOUT_POLICY_VERSION,'quoteHash':preview['quoteHash'],'purchaser':{'name':'Phụ huynh','contact':'qa@example.test','relationship':'parent','representativeDeclared':True}}
            return payments.create_order(db,session,body,require_checkout=True)['order']

    def paid(self,oid):
        with api.connect(self.path,True) as db:
            return payments.settle_order(db,db.execute('SELECT * FROM payment_orders WHERE id=?',(oid,)).fetchone(),'staff')

    def test_optional_pin_creation_removal_target_and_acl_parent_pin_unchanged(self):
        first,state=self.actor();sid=state['selectedChildId']
        first.call('child/pin',{'childId':sid,'noPin':True})
        selected=first.call('select',{'childId':sid})
        self.assertFalse(selected['children'][0]['pinRequired']);self.assertFalse(selected['children'][0]['pinSet'])
        self.assert_denied(lambda:first.call('child/pin',{'childId':sid,'noPin':True}),(403,))
        self.full(first)
        first.call('child/pin',{'childId':sid,'pin':'4321'})
        self.assert_denied(lambda:first.call('select',{'childId':sid}),(403,))
        added=first.call('children/add',{'name':'Con không PIN','birthYear':api.academic()[0]-7,'mascot':'fox','noPin':True,'requestKey':secrets.token_hex(12),'legalConsent':self.consent()})
        self.assertEqual(first.call('select',{'childId':added['addedChildId']})['scope'],'child')
        other,_=self.actor()
        self.assert_denied(lambda:other.call('select',{'childId':added['addedChildId']}),(404,403))
        self.assert_denied(lambda:first.call('parent/unlock',{'pin':'111111'}),(403,))

    def test_referral_quote_retry_snapshot_normalized_no_self_same_family_or_identity_lookup(self):
        ref,_=self.actor();buyer,state=self.actor();code=self.code(ref)
        order=self.order(buyer,' '+code.lower()+' ')
        self.assertEqual(order['checkoutSnapshot']['referralCode'],code)
        self.assertEqual(self.order(buyer,code)['id'],order['id'])
        self.assertEqual(order['amount'],100000)
        self.assertNotIn('referrer',str(order['checkoutSnapshot']))
        for bad in (self.code(buyer),'NOT-A-CODE'):
            self.assert_denied(lambda:self.order(buyer,bad),(400,))
        sibling=buyer.call('children/add',{'name':'Em cùng nhà','birthYear':api.academic()[0]-7,'mascot':'dog','noPin':True,'requestKey':secrets.token_hex(12),'legalConsent':self.consent()})
        with api.connect(self.path) as db:
            ownfamilycode=db.execute('SELECT a.invite_code FROM students s JOIN accounts a ON a.id=s.account_id WHERE s.id=?',(sibling['addedChildId'],)).fetchone()[0]
        self.assert_denied(lambda:self.order(buyer,ownfamilycode),(400,))

    def test_confirmed_first_paid_awards_exactly_seven_days_tier_and_duplicates_cannot_award(self):
        ref,_=self.actor();buyer,_=self.actor();order=self.order(buyer,self.code(ref),'VIP+')
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM child_referral_rewards').fetchone()[0],0)
        def settle(_):return self.paid(order['id'])
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(settle,range(2))),[False,True])
        with api.connect(self.path) as db:
            row=db.execute('SELECT * FROM child_referral_rewards').fetchone();period=db.execute('SELECT * FROM child_referral_periods').fetchone()
            self.assertEqual((row['tier'],row['days']),('VIP+',7))
            self.assertEqual(membership(db,self.mapped(ref,db)),'VIP+')
            self.assertEqual(db.execute('SELECT count(*) FROM account_referrals').fetchone()[0],0)
        reward=self.code(ref)
        visible=ref.learner()['personalSummary']['referral']['rewards']
        self.assertEqual((visible[0]['tier'],visible[0]['days']),('VIP+',7))
        self.assertEqual(set(visible[0]),{'tier','days','startsAt','endsAt','status'})
        self.assert_denied(lambda:self.order(buyer,self.code(ref)),(409,))
        self.assertFalse(self.paid(order['id']))

    def test_cancelled_and_repeat_paid_no_reward_and_immutable_legacy_attribution(self):
        ref,_=self.actor();buyer,_=self.actor();code=self.code(ref)
        discarded=self.order(buyer,code)
        with api.connect(self.path,True) as db:db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?",(discarded['id'],))
        self.assert_denied(lambda:self.paid(discarded['id']),(409,))
        paid=self.order(buyer);self.paid(paid['id'])
        self.assert_denied(lambda:self.order(buyer,code),(409,))
        with api.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM child_referral_rewards').fetchone()[0],0)

    def test_old_referral_commitment_keeps_legacy_reward_without_new_double_award(self):
        ref,_=self.actor();buyer,_=self.actor();code=self.code(ref)
        with api.connect(self.path,True) as db:
            inviter=self.mapped(ref,db)['account_id'];invitee=self.mapped(buyer,db)['account_id']
            db.execute('INSERT INTO account_referrals(inviter_account_id,invitee_account_id,invite_code,registered_at) VALUES(?,?,?,?)',(inviter,invitee,code,api.stamp()))
        self.assert_denied(lambda:self.order(buyer,code),(409,))
        self.paid(self.order(buyer)['id'])
        with api.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT reward_status FROM account_referrals').fetchone()[0],'granted')
            self.assertEqual(db.execute('SELECT count(*) FROM child_referral_rewards').fetchone()[0],0)

    def test_child_safe_notice_positive_read_rejects_fee_and_other_student(self):
        client,state=self.actor();sid=state['selectedChildId']
        with api.connect(self.path,True) as db:
            aid=self.mapped(client,db)['account_id'];year=db.execute('SELECT academic_year_id FROM student_grades WHERE student_id=?',(sid,)).fetchone()[0]
            teacher=db.execute("INSERT INTO teachers(full_name) VALUES('Giáo viên thử')").lastrowid
            classroom=db.execute("INSERT INTO online_classes(teacher_id,grade_id,academic_year_id,name) VALUES(?,5,?,'Lớp thử')",(teacher,year)).lastrowid
            enrollment=db.execute('INSERT INTO class_enrollments(student_id,class_id,joined_at) VALUES(?,?,?)',(sid,classroom,api.stamp())).lastrowid
            db.execute("INSERT INTO access_entitlements(account_id,enrollment_id,kind,starts_at) VALUES(?,?,'internal',?)",(aid,enrollment,api.stamp()))
            lesson=db.execute("INSERT INTO class_sessions(class_id,title,starts_at) VALUES(?,'Buổi học',?)",(classroom,api.stamp())).lastrowid
            assignment=db.execute("INSERT INTO class_assignments(session_id,title) VALUES(?,'Bài học của con')",(lesson,)).lastrowid
            notice=db.execute("INSERT INTO class_notices(class_id,student_id,section,source_id,created_at) VALUES(?,?,'assignments',?,?)",(classroom,sid,assignment,api.stamp())).lastrowid
            fee=db.execute("INSERT INTO class_notices(class_id,student_id,section,source_id,created_at) VALUES(?,?,'fees',999,?)",(classroom,sid,api.stamp())).lastrowid
            db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,created_at) VALUES(?,'staff_message','Hóa đơn','PRIVATE-BANK-DATA','5BMath','system',?)",(aid,api.stamp()))
        client.call('select',{'childId':sid,'pin':'4321'})
        visible=client.learner('personal/notifications')
        self.assertEqual([r['id'] for r in visible['rows']],[notice]);self.assertEqual(visible['unreadCount'],1)
        self.assertNotIn('PRIVATE-BANK-DATA',str(visible))
        self.assert_denied(lambda:client.learner('personal/notifications/read',{'ids':[fee]}),(403,))
        self.assertEqual(client.learner('personal/notifications/read',{'ids':[notice]})['unreadCount'],0)
        other,_=self.actor();self.assertEqual(other.learner('personal/notifications')['rows'],[])

    def test_paid_purchase_queues_unconsumed_same_tier_bonus_without_changing_grant_history(self):
        ref,_=self.actor();buyer,_=self.actor();self.paid(self.order(buyer,self.code(ref))['id'])
        with api.connect(self.path) as db:
            before=tuple(db.execute('SELECT * FROM child_referral_rewards').fetchone())
        self.paid(self.order(ref)['id'])
        with api.connect(self.path) as db:
            aid=self.mapped(ref,db)['account_id'];expiry=db.execute('SELECT vip_expires_at FROM accounts WHERE id=?',(aid,)).fetchone()[0]
            period=db.execute('SELECT * FROM child_referral_periods').fetchone()
            self.assertEqual(period['starts_at'],expiry)
            self.assertEqual(tuple(db.execute('SELECT * FROM child_referral_rewards').fetchone()),before)

    def test_internal_higher_access_holds_credit_and_next_writable_snapshot_activates_after_expiry(self):
        ref,state=self.actor();buyer,_=self.actor()
        with api.connect(self.path,True) as db:
            aid=self.mapped(ref,db)['account_id']
            db.execute("INSERT INTO access_entitlements(account_id,kind,starts_at) VALUES(?,'internal',?)",(aid,api.stamp(api.now()-timedelta(days=1))))
        self.paid(self.order(buyer,self.code(ref))['id'])
        visible=ref.learner()['personalSummary']['referral']['rewards'][0]
        self.assertEqual(visible['status'],'held-internal');self.assertIsNone(visible['startsAt'])
        with api.connect(self.path,True) as db:db.execute('UPDATE access_entitlements SET ends_at=? WHERE account_id=?',(api.stamp(),aid))
        ref.call('select',{'childId':state['selectedChildId'],'pin':'4321'})
        updated=ref.learner('profile',{'name':'Con nhận thưởng'})
        self.assertEqual(updated['personalSummary']['referral']['rewards'][0]['status'],'active')
        self.assertEqual(updated['account']['membership'],'VIP')

    def test_reward_vip_queues_behind_higher_paid_and_later_plus_extension_preserves_seconds(self):
        ref,_=self.actor();buyer,_=self.actor();base=api.now()
        with api.connect(self.path,True) as db:
            aid=self.mapped(ref,db)['account_id'];prior=api.stamp(base+timedelta(days=30))
            db.execute('UPDATE accounts SET vip_plus_expires_at=? WHERE id=?',(prior,aid))
        self.paid(self.order(buyer,self.code(ref))['id'])
        with api.connect(self.path) as db:
            period=db.execute('SELECT * FROM child_referral_periods').fetchone()
            self.assertEqual(period['starts_at'],prior)
            self.assertEqual(membership(db,self.mapped(ref,db)),'VIP+')
            self.assertEqual(db.execute('SELECT vip_plus_expires_at FROM accounts WHERE id=?',(aid,)).fetchone()[0],prior)
        second,_=self.actor();self.paid(self.order(second,self.code(ref),'VIP+')['id'])
        with api.connect(self.path) as db:
            vip=db.execute("SELECT * FROM child_referral_periods WHERE tier='VIP'").fetchone()
            plus=db.execute("SELECT * FROM child_referral_periods WHERE tier='VIP+'").fetchone()
            self.assertEqual(vip['starts_at'],plus['ends_at'])
            from datetime import datetime
            self.assertEqual((datetime.fromisoformat(vip['ends_at'].replace('Z','+00:00'))-datetime.fromisoformat(vip['starts_at'].replace('Z','+00:00'))).days,7)
            with patch.object(api,'now',return_value=base+timedelta(days=38)):
                # Membership imports its own clock, use bonus helper directly.
                self.assertEqual(personal.bonus_tier(db,aid),'VIP')

    def test_theme_student_isolation_two_devices_and_safe_notifications_guard(self):
        first,state=self.actor();sid=state['selectedChildId'];first.call('select',{'childId':sid,'pin':'4321'})
        first.learner('preferences',{'theme':'garden-adventure'})
        second=old.FamilyClient(self.server);second.call('login',{'email':self.email,'password':self.PASSWORD});second.call('select',{'childId':sid,'pin':'4321'})
        self.assertEqual(second.learner()['state']['theme'],'garden-adventure')
        other,_=self.actor();self.assertNotEqual(other.learner()['state']['theme'],'garden-adventure')
        self.assertEqual(second.learner('personal/notifications')['rows'],[])
        self.assert_denied(lambda:second.learner('notifications'),(403,))

    def test_summary_counts_three_games_once_and_no_client_bot_checkpoint(self):
        client,state=self.actor();sid=state['selectedChildId']
        with api.connect(self.path,True) as db:
            did=db.execute("INSERT INTO duels(grade_id,mode,status,difficulty,curriculum_mode,settings_json,created_at,ended_at) VALUES(5,'training','completed',1,'weekly','{}',?,?)",(api.stamp(),api.stamp())).lastrowid
            db.execute("INSERT INTO duel_players(duel_id,student_id,slot,outcome) VALUES(?,?,1,'win')",(did,sid))
            for mode,winner in (('capture_flag',sid+100),('animal_race',None)):
                payload=api.packed({'players':[{'studentId':sid,'forfeited':False}],'winnerId':winner})
                db.execute("INSERT INTO group_game_rooms VALUES(?,?,?,5,'finished',?,1)",(secrets.token_hex(8),secrets.token_hex(8),mode,payload))
        result=client.learner()['personalSummary']
        self.assertEqual(result['games'],{'wins':1,'losses':1,'draws':1,'total':3})
        self.assertEqual(result['study']['submittedExams'],0)
        self.assertEqual(set(result['referral']),{'code','eligibleForFirstPurchase','policy','rewardDays','rewards'})
