"""QA-only independent question packs and VIP debit ledger. No payment integrations."""
from datetime import datetime,timedelta
import json
import secrets
from . import platform_api as api
from .learning_update import membership
from .mcq_import import require_qa,digest

POLICY='wallet-qa-v1'
CATALOG={'sku':'qa.questions.100','quantity':100,'amount':50000,'currency':'VND','validDays':90,
         'notice':'Thanh toán giả trên QA — không chuyển tiền','scopeLabel':'5 câu VIP MCQ khối 5 hiện có; không mở tính năng VIP'}
SCHEMA="""
CREATE TABLE wallet_scopes(scope_id TEXT PRIMARY KEY,grade INTEGER NOT NULL,keys_json TEXT NOT NULL);
CREATE TABLE wallet_terms(student_id INTEGER PRIMARY KEY REFERENCES students(id),anchor_at TEXT NOT NULL,policy_version TEXT NOT NULL);
CREATE TABLE wallet_orders(order_id TEXT PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES accounts(id),student_id INTEGER NOT NULL REFERENCES students(id),request_key TEXT NOT NULL,sku TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','failed','confirmed')),catalog_json TEXT NOT NULL,created_at TEXT NOT NULL,confirmed_at TEXT,UNIQUE(student_id,request_key));
CREATE TABLE wallet_packs(pack_id TEXT PRIMARY KEY,order_id TEXT NOT NULL UNIQUE REFERENCES wallet_orders(order_id),student_id INTEGER NOT NULL REFERENCES students(id),scope_id TEXT NOT NULL REFERENCES wallet_scopes(scope_id),credits INTEGER NOT NULL CHECK(credits=100),confirmed_at TEXT NOT NULL,expires_at TEXT NOT NULL,policy_version TEXT NOT NULL);
CREATE TABLE wallet_quotes(quote_id TEXT PRIMARY KEY,student_id INTEGER NOT NULL REFERENCES students(id),selector_hash TEXT NOT NULL,plan_json TEXT NOT NULL,max_private INTEGER NOT NULL CHECK(max_private>=0),expires_at TEXT NOT NULL,policy_version TEXT NOT NULL);
CREATE TABLE wallet_attempt_receipts(exam_id INTEGER PRIMARY KEY REFERENCES exams(id),student_id INTEGER NOT NULL REFERENCES students(id),policy_version TEXT NOT NULL,allocation_json TEXT NOT NULL);
CREATE TABLE wallet_debits(student_id INTEGER NOT NULL REFERENCES students(id),quota_key TEXT NOT NULL REFERENCES pilot_content(content_key),version_id INTEGER NOT NULL REFERENCES question_versions(id),source TEXT NOT NULL CHECK(source IN ('free','vip','pack')),pack_id TEXT REFERENCES wallet_packs(pack_id),local_day TEXT NOT NULL,cycle_start TEXT,exam_id INTEGER NOT NULL REFERENCES exams(id),consumed_at TEXT NOT NULL,policy_version TEXT NOT NULL,receipt_json TEXT NOT NULL,PRIMARY KEY(student_id,quota_key),CHECK((source='pack' AND pack_id IS NOT NULL) OR (source!='pack' AND pack_id IS NULL)));
CREATE TABLE wallet_usage_seeds(student_id INTEGER NOT NULL REFERENCES students(id),local_day TEXT NOT NULL,cycle_start TEXT NOT NULL,day_used INTEGER NOT NULL CHECK(day_used>=0),cycle_used INTEGER NOT NULL CHECK(cycle_used>=0),label TEXT NOT NULL,PRIMARY KEY(student_id,local_day,cycle_start));
CREATE TABLE wallet_pack_seeds(pack_id TEXT PRIMARY KEY REFERENCES wallet_packs(pack_id),spent INTEGER NOT NULL CHECK(spent>=0 AND spent<=100),label TEXT NOT NULL);
"""


def initialize(db,keys):
    require_qa(db)
    from .database import execute_sql
    execute_sql(db,SCHEMA)
    db.execute('INSERT INTO wallet_scopes VALUES (?,5,?)',('qa.g5.vip10',api.packed(keys)))


def require_wallet(db):
    require_qa(db)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='wallet_scopes'").fetchone():
        raise api.APIError('Ví chỉ mở trên QA đã khởi tạo riêng.',503)


def scope_keys(db):
    row=db.execute("SELECT keys_json FROM wallet_scopes WHERE scope_id='qa.g5.vip10' AND grade=5").fetchone()
    from .curriculum_samples import paid_keys
    return sorted(set(json.loads(row[0]) if row else []) | paid_keys(db))


def catalog_view(db,*,_scope=None):
    count=len(scope_keys(db) if _scope is None else _scope)
    return CATALOG if count==5 else {**CATALOG,'scopeLabel':f'{count} câu VIP khối 5 trong batch QA; không mở tính năng VIP'}


def vip_budget(db,session,config):
    sid=session['student_id'];active=membership(db,session) in ('VIP','VIP+');now=api.now()
    term=db.execute('SELECT anchor_at FROM wallet_terms WHERE student_id=?',(sid,)).fetchone()
    day=now.astimezone(api.VN).date().isoformat();start=None;end=None
    if active and not term:raise api.APIError('VIP chưa có mốc chu kỳ đã xác minh trên QA.',503)
    if term:
        anchor=datetime.fromisoformat(term[0]);index=max(0,(now-anchor)//timedelta(days=30))
        start=api.stamp(anchor+timedelta(days=30*index));end=api.stamp(anchor+timedelta(days=30*(index+1)))
        if now<anchor:active=False
    annual=bool(config.vip_cycle_start and config.vip_cycle_end)
    if annual:
        start,end=config.vip_cycle_start,config.vip_cycle_end
        if not datetime.fromisoformat(start)<=now<datetime.fromisoformat(end):active=False
    day_used=db.execute("SELECT count(*) FROM wallet_debits WHERE student_id=? AND source='vip' AND local_day=?",(sid,day)).fetchone()[0]
    day_used+=db.execute('SELECT coalesce(sum(day_used),0) FROM wallet_usage_seeds WHERE student_id=? AND local_day=?',(sid,day)).fetchone()[0]
    cycle_used=db.execute("SELECT count(*) FROM wallet_debits WHERE student_id=? AND source='vip' AND cycle_start=?",(sid,start)).fetchone()[0]
    cycle_used+=db.execute('SELECT coalesce(sum(cycle_used),0) FROM wallet_usage_seeds WHERE student_id=? AND cycle_start=?',(sid,start)).fetchone()[0]
    expiry=db.execute('SELECT vip_expires_at FROM accounts WHERE id=?',(session['account_id'],)).fetchone()[0]
    return {'active':active,'day':day,'dayUsed':day_used,'dayLimit':config.vip_daily,'cycleUsed':cycle_used,'cycleLimit':config.vip_cycle,'cyclePeriod':'year' if annual else 'month',
            'cycleStart':start,'cycleEnd':end,'vipExpiresAt':expiry,'available':max(0,min(config.vip_daily-day_used,config.vip_cycle-cycle_used)) if active else 0}


def pack_rows(db,sid):
    return [dict(r) for r in db.execute("SELECT p.*,p.credits-(SELECT count(*) FROM wallet_debits d WHERE d.pack_id=p.pack_id)-coalesce(s.spent,0) remaining FROM wallet_packs p LEFT JOIN wallet_pack_seeds s ON s.pack_id=p.pack_id WHERE p.student_id=? ORDER BY p.expires_at,p.pack_id",(sid,))]


def balance(db,session,config):
    require_wallet(db);now=api.stamp();packs=pack_rows(db,session['student_id']);scope=scope_keys(db)
    for pack in packs:pack['usable']=pack['expires_at']>now and pack['remaining']>0 and pack['scope_id']=='qa.g5.vip10'
    return {'policyVersion':POLICY,'catalog':catalog_view(db,_scope=scope),'membership':membership(db,session),'vip':vip_budget(db,session,config),
            'privateRemaining':sum(p['remaining'] for p in packs if p['usable']),'packs':packs,
            'orders':[order_view(db,session,r[0]) for r in db.execute('SELECT order_id FROM wallet_orders WHERE student_id=? ORDER BY created_at DESC,order_id LIMIT 20',(session['student_id'],))],'scopeKeys':scope,'timezone':'Asia/Saigon',
            'seededCountersNotice':('Các bộ đếm biên QA có nhãn giả; kho 60 câu tự biên soạn, không tạo thêm câu để lấp hạn mức.' if config.batch_set_key else 'Các bộ đếm biên QA có nhãn giả; kho vẫn chỉ 10 câu.')}


def selector(body):return {k:body[k] for k in ('setIndex','contentKeys','replayExamId','responseMode') if k in body}


def plan(db,session,selected,grants,config,body,*,purchased_sku=None):
    require_wallet(db);state=balance(db,session,config);scope=set(state['scopeKeys']);sid=session['student_id']
    vip_left=state['vip']['available'];packs=[{**p} for p in state['packs'] if p['usable']];alloc=[]
    from .free_vip_pilot import clock_window
    _,start,end=clock_window()
    current_free={r[0] for r in db.execute('SELECT i.content_key FROM pilot_set_items i JOIN pilot_sets s ON s.set_key=i.set_key WHERE s.grade=? AND s.window_start=? AND s.window_end=?',(config.grade,start,end))}
    from .curriculum_samples import free_keys,registered
    current_free.update(free_keys(db))
    for quota,row in grants.items():
        ck=row['content_key'];version=row['version_id']
        old=db.execute('SELECT version_id FROM pilot_grants WHERE student_id=? AND content_key=?',(sid,quota)).fetchone()
        access=db.execute('SELECT proposed_access FROM pilot_content WHERE content_key=?',(ck,)).fetchone()[0]
        entry={'quotaKey':quota,'contentKey':ck,'versionId':version,'source':'retained','packId':None,'expiresAt':None}
        if old:
            if access=='vip' and 'replayExamId' not in body and old[0]!=version and not state['vip']['active'] and not packs and not config.internal_unlimited and not (purchased_sku and ck in scope):
                raise api.APIError('Bài đã cấp giữ bản cũ; mở từ lịch sử để xem đúng phiên bản.',403)
        elif access=='free':
            if ck not in current_free:raise api.APIError('Câu Free ngoài manifest hiện hành.',403)
            entry['source']='free'
        else:
            if ck not in scope:raise api.APIError('Câu ngoài phạm vi gói QA.',403)
            if purchased_sku:
                entry['source']='purchased'
            elif config.internal_unlimited:
                entry.update(source='free',reason='server-internal-entitlement')
            elif vip_left:
                entry['source']='vip';vip_left-=1
            else:
                # Original private QA packs retain their original scope. Newly
                # authored samples use VIP or actually purchased permanent credits.
                pack=next((p for p in packs if p['remaining']>0),None) if registered(db,version) is None else None
                if not pack:raise api.APIError('Không đủ lượt VIP/gói riêng còn hạn; chưa cấp hoặc trừ câu nào.',402)
                pack['remaining']-=1;entry.update(source='pack',packId=pack['pack_id'],expiresAt=pack['expires_at'])
        alloc.append(entry)
    return {'policyVersion':POLICY,'newPaid':sum(a['source'] in ('vip','pack','purchased') for a in alloc),
            'vip':sum(a['source']=='vip' for a in alloc),'private':sum(a['source']=='pack' for a in alloc),
            'free':sum(a['source']=='free' for a in alloc),'retained':sum(a['source']=='retained' for a in alloc),
            'allocations':alloc,'vipBudget':state['vip'],'selector':selector(body),'scopeLabel':catalog_view(db)['scopeLabel']}


class QuoteChanged(api.APIError):
    def __init__(self,allocation,*,purchased=False):
        message = ('Lượt đã mua hoặc phiên xác nhận đã đổi. Hãy xem báo giá mới trước khi tạo đề.' if purchased else
                   'Phân bổ đã đổi hoặc xác nhận hết hạn. Xem lại và xác nhận gói riêng trước khi cấp.')
        super().__init__(message,409)
        self.allocation=allocation


def quote(db,session,body,config):
    from .free_vip_pilot import create_exam
    if not isinstance(body,dict) or set(body)-({'setIndex','contentKeys','replayExamId'}|({'responseMode'} if config.batch_set_key else set())):raise api.APIError('Chỉ chọn nội dung cần xem trước.')
    result=create_exam(db,session,{'requestKey':secrets.token_hex(16),**body},config,quote_only=True)
    qid='quote-'+secrets.token_hex(16);expires=api.stamp(api.now()+timedelta(minutes=2))
    db.execute('INSERT INTO wallet_quotes VALUES (?,?,?,?,?,?,?)',(qid,session['student_id'],digest(selector(body)),api.packed(result),result['private'],expires,POLICY))
    return {**result,'quoteId':qid,'expiresAt':expires}


def confirm_quote(db,session,body,allocation):
    if allocation['private']==0 and 'quoteId' not in body:return
    qid=body.get('quoteId');row=db.execute('SELECT * FROM wallet_quotes WHERE quote_id=? AND student_id=?',(qid,session['student_id'])).fetchone() if isinstance(qid,str) else None
    if not row or row['expires_at']<=api.stamp() or row['selector_hash']!=digest(selector(body)) or row['policy_version']!=POLICY:
        raise QuoteChanged(allocation)
    if allocation['private']>row['max_private'] or allocation['private'] and body.get('confirmWallet') is not True:
        raise QuoteChanged(allocation)


def debit(db,session,allocation,eid):
    # Called after exam/items and before attempt, inside the caller's BEGIN IMMEDIATE.
    for entry in allocation['allocations']:
        if entry['source']=='retained':continue
        vip=allocation['vipBudget']
        snapshot={**entry,'vipDayLimit':vip['dayLimit'],'vipCycleLimit':vip['cycleLimit'],'cycleStart':vip['cycleStart'],
                  'cycleEnd':vip['cycleEnd'],'policyVersion':POLICY,'examId':eid}
        db.execute('INSERT INTO wallet_debits VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (session['student_id'],entry['quotaKey'],entry['versionId'],entry['source'],entry['packId'],vip['day'],
             vip['cycleStart'] if entry['source']=='vip' else None,eid,api.stamp(),POLICY,api.packed(snapshot)))
    db.execute('INSERT INTO wallet_attempt_receipts VALUES (?,?,?,?)',(eid,session['student_id'],POLICY,api.packed(allocation)))


def create_order(db,session,body):
    require_wallet(db)
    if not isinstance(body,dict) or set(body)!={'requestKey','sku'} or body['sku']!=CATALOG['sku']:raise api.APIError('Catalog QA cố định; không gửi giá/lượt/quyền/thời hạn.')
    key=api.text_field(body,'requestKey',80,8)
    old=db.execute('SELECT * FROM wallet_orders WHERE student_id=? AND request_key=?',(session['student_id'],key)).fetchone()
    if old:return order_view(db,session,old['order_id'])
    oid='order-'+secrets.token_hex(12)
    db.execute("INSERT INTO wallet_orders VALUES (?,?,?,?,?,'pending',?,?,NULL)",(oid,session['account_id'],session['student_id'],key,CATALOG['sku'],api.packed(catalog_view(db)),api.stamp()))
    return order_view(db,session,oid)


def order_view(db,session,oid):
    row=db.execute('SELECT * FROM wallet_orders WHERE order_id=? AND student_id=? AND account_id=?',(oid,session['student_id'],session['account_id'])).fetchone()
    if not row:raise api.APIError('Không tìm thấy đơn QA của hồ sơ.',404)
    pack=db.execute('SELECT pack_id,credits,confirmed_at,expires_at FROM wallet_packs WHERE order_id=?',(oid,)).fetchone()
    return {'orderId':oid,'status':row['status'],'catalog':json.loads(row['catalog_json']),'receipt':dict(pack) if pack else None,'qaOnly':True,'notice':CATALOG['notice']}


def mock_event(db,session,body,*,confirm):
    require_wallet(db)
    if not isinstance(body,dict) or set(body)!={'orderId'} or not isinstance(body['orderId'],str):raise api.APIError('Chỉ gửi mã đơn QA; kết quả do mô phỏng server xác nhận.')
    view=order_view(db,session,body['orderId']);oid=view['orderId']
    if view['status']!='pending':return view
    if not confirm:db.execute("UPDATE wallet_orders SET status='failed' WHERE order_id=?",(oid,));return order_view(db,session,oid)
    confirmed=api.stamp();expiry=api.stamp(api.now()+timedelta(days=90))
    db.execute("UPDATE wallet_orders SET status='confirmed',confirmed_at=? WHERE order_id=?",(confirmed,oid))
    db.execute('INSERT INTO wallet_packs VALUES (?,?,?,?,100,?,?,?)',('pack-'+secrets.token_hex(12),oid,session['student_id'],'qa.g5.vip10',confirmed,expiry,POLICY))
    return order_view(db,session,oid)


def attempt_receipt(db,session,eid):
    api.owned_attempt(db,session,eid)
    row=db.execute('SELECT allocation_json FROM wallet_attempt_receipts WHERE exam_id=? AND student_id=?',(eid,session['student_id'])).fetchone()
    if not row:raise api.APIError('Chưa có biên nhận ví QA cho bài này.',404)
    return {'examId':str(eid),'allocation':json.loads(row[0]),'policyVersion':POLICY,'qaOnly':True}
