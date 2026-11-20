"""Student-only personal aggregates and first confirmed paid referral policy."""
import json
from datetime import datetime, timedelta
from . import platform_api as api

POLICY = 'child-first-paid-v1'

def first_paid(db, aid):
    return not db.execute('SELECT 1 FROM vip_purchases WHERE account_id=? LIMIT 1',(aid,)).fetchone() and not db.execute("SELECT 1 FROM payment_orders WHERE account_id=? AND status='paid' AND kind='vip' AND purchase_type='subscription' LIMIT 1",(aid,)).fetchone() and not db.execute('SELECT 1 FROM account_referrals WHERE invitee_account_id=?',(aid,)).fetchone()

def referral(db, session, body):
    eligible = first_paid(db, session['account_id'])
    code = body.get('referralCode', '')
    if not isinstance(code,str) or len(code)>30:
        raise api.APIError('Mã giới thiệu không hợp lệ.')
    code=code.strip().upper()
    referrer=None
    if code:
        if not eligible or body.get('feeId') is not None or body.get('examProduct') is not None:
            raise api.APIError('Mã giới thiệu chỉ dùng khi mua gói VIP/VIP+ trả phí lần đầu.',409)
        candidate=db.execute("SELECT s.id,s.account_id FROM accounts a JOIN students s ON s.account_id=a.id WHERE a.invite_code=? AND a.status='active' AND a.deleted_at IS NULL AND s.status='active'",(code,)).fetchone()
        legacy=db.execute('SELECT 1 FROM account_referrals WHERE invitee_account_id=?',(session['account_id'],)).fetchone()
        same_family = candidate and db.execute('SELECT 1 FROM family_children a JOIN family_children b ON a.family_id=b.family_id WHERE a.student_id=? AND b.student_id=?',(candidate['id'],session['student_id'])).fetchone()
        closed = candidate and db.execute("SELECT 1 FROM family_children c JOIN family_accounts f ON f.id=c.family_id WHERE c.student_id=? AND f.status<>'active'",(candidate['id'],)).fetchone()
        if not candidate or candidate['id']==session['student_id'] or same_family or legacy or closed:
            raise api.APIError('Mã giới thiệu không hợp lệ cho lượt mua này.')
        referrer=candidate['id']
    return {'referralEligible':eligible,'referralPolicy':POLICY,'referralCode':code,'referrer':referrer}

def pin_order(db, session, body, create):
    info=referral(db,session,body)
    pending=db.execute("SELECT id FROM payment_orders WHERE account_id=? AND status='pending' AND coalesce(fee_id,0)=?",(session['account_id'],body.get('feeId') or 0)).fetchone()
    if pending:
        pin=db.execute('SELECT code FROM child_referral_order_pins WHERE order_id=?',(pending['id'],)).fetchone()
        if not pin and info['referralCode']:
            raise api.APIError('Đơn đang có giữ cam kết trước đây. Hãy hoàn tất đơn trước khi tạo lựa chọn mới.',409)
        if pin and pin['code']!=info['referralCode']:
            db.execute("UPDATE payment_orders SET status='cancelled' WHERE id=?",(pending['id'],))
    result=create(db,session,body)
    order=result['order']
    # A reused older pending order has its own commitment; never retrofit it.
    fresh = not pending or order['id']!=pending['id']
    if fresh and order['kind']=='vip' and order['purchase_type']=='subscription':
        db.execute('INSERT INTO child_referral_order_pins VALUES(?,?,?,?,?)',(order['id'],POLICY,session['student_id'],info['referrer'],info['referralCode']))
    return result

def bonus_tier(db, aid):
    rows=db.execute('SELECT tier FROM child_referral_periods WHERE account_id=? AND starts_at<=? AND ends_at>?',(aid,api.stamp(),api.stamp())).fetchall()
    return 'VIP+' if any(r[0]=='VIP+' for r in rows) else 'VIP' if rows else None

def effective_dates(db, aid):
    account=db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts WHERE id=?',(aid,)).fetchone()
    result=dict(account)
    for row in db.execute('SELECT tier,max(ends_at) expiry FROM child_referral_periods WHERE account_id=? AND starts_at<=? AND ends_at>? GROUP BY tier',(aid,api.stamp(),api.stamp())):
        column='vip_plus_expires_at' if row['tier']=='VIP+' else 'vip_expires_at'
        result[column]=max(result[column] or '',row['expiry'])
    # Technical pilot wallet needs base paid capability for either paid tier.
    result['vip_expires_at']=max(result['vip_expires_at'] or '',result['vip_plus_expires_at'] or '') or None
    return result

def activate_held(db, aid):
    if db.execute('SELECT 1 FROM access_entitlements WHERE account_id=? AND starts_at<=? AND (ends_at IS NULL OR ends_at>?)',(aid,api.stamp(),api.stamp())).fetchone():return
    account=db.execute('SELECT * FROM accounts WHERE id=?',(aid,)).fetchone()
    for row in db.execute('SELECT * FROM child_referral_periods WHERE account_id=? AND starts_at IS NULL ORDER BY order_id',(aid,)).fetchall():
        previous=db.execute('SELECT max(ends_at) FROM child_referral_periods WHERE account_id=? AND (tier=? OR ?=\'VIP\')',(aid,row['tier'],row['tier'])).fetchone()[0]
        anchor=max(api.stamp(),account['vip_plus_expires_at'] or '',account['vip_expires_at'] or '' if row['tier']=='VIP' else '',previous or '')
        end=api.stamp(datetime.fromisoformat(anchor.replace('Z','+00:00'))+timedelta(days=7))
        db.execute('UPDATE child_referral_periods SET starts_at=?,ends_at=? WHERE order_id=?',(anchor,end,row['order_id']))
        if row['tier']=='VIP+':shift_vip(db,aid,end)

def shift_vip(db, aid, plus_end):
    """Preserve only unconsumed lower-tier bonus seconds, behind higher access."""
    shift_tier(db,aid,'VIP',plus_end)

def shift_tier(db, aid, tier, paid_end):
    anchor=max(api.stamp(),paid_end or api.stamp())
    for row in db.execute("SELECT * FROM child_referral_periods WHERE account_id=? AND tier=? AND ends_at>? ORDER BY starts_at,order_id",(aid,tier,api.stamp())).fetchall():
        if row['starts_at']>=anchor:
            anchor=max(anchor,row['ends_at']);continue
        remaining=(datetime.fromisoformat(row['ends_at'].replace('Z','+00:00'))-datetime.fromisoformat(max(row['starts_at'],api.stamp()).replace('Z','+00:00'))).total_seconds()
        end=api.stamp(datetime.fromisoformat(anchor.replace('Z','+00:00'))+timedelta(seconds=remaining))
        db.execute('UPDATE child_referral_periods SET starts_at=?,ends_at=? WHERE order_id=?',(anchor,end,row['order_id']))
        anchor=end

def preserve_after_purchase(db, aid, tier):
    account=db.execute('SELECT vip_expires_at,vip_plus_expires_at FROM accounts WHERE id=?',(aid,)).fetchone()
    if tier=='VIP+':shift_tier(db,aid,'VIP+',account['vip_plus_expires_at'])
    plus_bonus=db.execute("SELECT max(ends_at) FROM child_referral_periods WHERE account_id=? AND tier='VIP+'",(aid,)).fetchone()[0]
    shift_vip(db,aid,max(account['vip_expires_at'] or '',account['vip_plus_expires_at'] or '',plus_bonus or '',api.stamp()))

def settle_referral(db, order):
    # Called after confirmed settlement; ignore all historical/non-pinned orders.
    if not db.execute("SELECT 1 FROM payment_orders WHERE id=? AND account_id=? AND status='paid'",(order['id'],order['account_id'])).fetchone():return
    pin=db.execute('SELECT * FROM child_referral_order_pins WHERE order_id=?',(order['id'],)).fetchone()
    if not pin or not pin['referrer_student_id']:
        return
    aid=order['account_id']
    if db.execute('SELECT count(*) FROM vip_purchases WHERE account_id=?',(aid,)).fetchone()[0]!=1:
        return
    if db.execute("SELECT 1 FROM payment_orders WHERE account_id=? AND status='paid' AND kind='vip' AND purchase_type='subscription' AND id<>?",(aid,order['id'])).fetchone():
        return
    if db.execute('SELECT 1 FROM account_referrals WHERE invitee_account_id=?',(aid,)).fetchone():
        return
    inserted=db.execute('INSERT OR IGNORE INTO child_referral_rewards VALUES(?,?,?,?,7,?)',(pin['invitee_student_id'],pin['referrer_student_id'],order['id'],order['subscription_plan'],api.stamp())).rowcount
    if not inserted:return
    target=db.execute('SELECT a.* FROM students s JOIN accounts a ON a.id=s.account_id WHERE s.id=?',(pin['referrer_student_id'],)).fetchone()
    tier=order['subscription_plan']
    internal=db.execute('SELECT 1 FROM access_entitlements WHERE account_id=? AND starts_at<=? AND (ends_at IS NULL OR ends_at>?)',(target['id'],api.stamp(),api.stamp())).fetchone()
    periods=db.execute('SELECT max(ends_at) FROM child_referral_periods WHERE account_id=? AND (tier=? OR ?=\'VIP\')',(target['id'],tier,tier)).fetchone()[0]
    start=max(api.stamp(),target['vip_plus_expires_at'] or '',target['vip_expires_at'] or '' if tier=='VIP' else '',periods or '')
    end=api.stamp(datetime.fromisoformat(start.replace('Z','+00:00'))+timedelta(days=7))
    db.execute('INSERT INTO child_referral_periods VALUES(?,?,?,?,?)',(order['id'],target['id'],tier,None if internal else start,None if internal else end))
    if tier=='VIP+' and not internal:shift_vip(db,target['id'],end)
    db.execute("INSERT INTO notifications(account_id,kind,title,body,sender_name,sender_role,created_at) VALUES(?,'staff_message','Nhận thưởng giới thiệu',?,'5BMath','system',?)",(target['id'],'Con nhận 7 ngày '+tier+'; thời gian thưởng được xếp sau quyền đang có theo chính sách giới thiệu.',api.stamp()))

def summary(db, session, provider=None):
    sid=session['student_id']
    def study(store, identity):
        return {'completedLessons':store.execute('SELECT count(*) FROM lesson_progress WHERE student_id=?',(identity,)).fetchone()[0],
                'submittedExams':store.execute("SELECT count(*) FROM exam_attempts WHERE student_id=? AND status='submitted'",(identity,)).fetchone()[0],
                'answeredQuestions':store.execute("SELECT count(*) FROM exam_answers a JOIN exam_attempts e ON e.id=a.attempt_id WHERE e.student_id=? AND e.status='submitted' AND trim(COALESCE(json_extract(a.response_json,'$.answer'),''))<>''",(identity,)).fetchone()[0]}
    counts=study(db,sid)
    if provider:
        with api.connect(provider.path) as pilot:
            mapped=pilot.execute('SELECT pilot_student_id FROM local_principals WHERE main_student_id=?',(sid,)).fetchone()
            if mapped:
                for key,value in study(pilot,mapped[0]).items():counts[key]+=value
                from .study_retake import exists
                if exists(pilot,'knowledge_checks'):
                    completed={(row[0],row[1]) for row in pilot.execute('SELECT DISTINCT lesson_key,lesson_revision FROM knowledge_checks WHERE student_id=?',(mapped[0],))}
                    if exists(pilot,'study_knowledge_completions'):
                        completed.update((row[0],row[1]) for row in pilot.execute('SELECT lesson_key,lesson_revision FROM study_knowledge_completions WHERE student_id=?',(mapped[0],)))
                    counts['completedLessons']+=len(completed)
    games={'wins':0,'losses':0,'draws':0,'total':0}
    for row in db.execute("SELECT p.outcome,count(*) n FROM duel_players p JOIN duels d ON d.id=p.duel_id WHERE p.student_id=? AND d.status='completed' GROUP BY p.outcome",(sid,)):
        key={'win':'wins','lose':'losses','draw':'draws'}.get(row['outcome'])
        if key:games[key]+=row['n']
    for row in db.execute("SELECT payload_json FROM group_game_rooms WHERE status='finished' AND mode IN ('capture_flag','animal_race')"):
        room=json.loads(row[0]);player=next((p for p in room.get('players',[]) if p.get('studentId')==sid),None)
        if player:
            key='wins' if room.get('winnerId')==sid else 'losses' if room.get('winnerId') is not None or player.get('forfeited') else 'draws'
            games[key]+=1
    games['total']=sum(games[k] for k in ('wins','losses','draws'))
    code=db.execute('SELECT invite_code FROM accounts WHERE id=?',(session['account_id'],)).fetchone()[0]
    rewards=[{'tier':r['tier'],'days':r['days'],'startsAt':r['starts_at'],'endsAt':r['ends_at'],
              'status':'held-internal' if not r['starts_at'] else 'queued' if r['starts_at']>api.stamp() else 'active' if r['ends_at']>api.stamp() else 'used'}
             for r in db.execute('SELECT r.tier,r.days,p.starts_at,p.ends_at FROM child_referral_rewards r JOIN child_referral_periods p ON p.order_id=r.order_id WHERE r.referrer_student_id=? ORDER BY r.granted_at DESC,r.order_id DESC',(sid,))]
    from .study_retake import continuation
    return {'continueStudy':continuation(db,session,provider),'study':counts,'games':games,'referral':{'code':code,'eligibleForFirstPurchase':first_paid(db,session['account_id']),'policy':POLICY,'rewardDays':7,'rewards':rewards}}

def safe_notices(db, session, read_ids=None):
    from .learning_update import membership
    if membership(db,session)!='SVip':
        return {'rows':[],'unreadCount':0,'total':0}
    rows=[dict(r) for r in db.execute("SELECT n.id,a.title,n.created_at createdAt,n.read_at readAt FROM class_notices n JOIN class_assignments a ON a.id=n.source_id JOIN class_sessions cs ON cs.id=a.session_id AND cs.class_id=n.class_id JOIN online_classes c ON c.id=n.class_id JOIN class_enrollments e ON e.class_id=n.class_id AND e.student_id=n.student_id WHERE n.student_id=? AND n.section='assignments' AND e.left_at IS NULL AND c.status='active' ORDER BY n.id DESC LIMIT 100",(session['student_id'],))]
    if read_ids is not None:
        if not isinstance(read_ids,list) or len(read_ids)>100 or any(type(i) is not int for i in read_ids):
            raise api.APIError('Danh sách thông báo không hợp lệ.')
        allowed={r['id'] for r in rows}
        if any(i not in allowed for i in read_ids):
            raise api.APIError('Thông báo không thuộc nội dung học tập của con.',403)
        for identity in read_ids:
            db.execute("UPDATE class_notices SET read_at=coalesce(read_at,?) WHERE id=? AND student_id=? AND section='assignments'",(api.stamp(),identity,session['student_id']))
        for row in rows:
            if row['id'] in read_ids:row['readAt']=row['readAt'] or api.stamp()
    for row in rows:
        row.update(kind='learning_assignment',body='Con có bài tập lớp học được giao.',senderName='5BMath',senderRole='system')
    return {'rows':rows,'unreadCount':sum(not r['readAt'] for r in rows),'total':len(rows)}
