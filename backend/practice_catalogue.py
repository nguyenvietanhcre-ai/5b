"""One atomic mixed-representation wallet selector. No legacy exam-count quota."""
from datetime import timedelta
import hashlib,json,secrets
from . import platform_api as api,wallet_qa as wallet
from . import purchased_credits as credits
from .mcq_import import digest
from .free_vip_pilot import clock_window,version_allowed

SCHEMA=[
 'CREATE TABLE IF NOT EXISTS practice_intents(student_id INTEGER NOT NULL REFERENCES students(id),intent_id TEXT NOT NULL,criteria_hash TEXT NOT NULL,catalogue_revision TEXT NOT NULL,selection_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(student_id,intent_id))',
 'CREATE TABLE IF NOT EXISTS practice_exam_items(exam_id INTEGER NOT NULL,position INTEGER NOT NULL,content_key TEXT NOT NULL REFERENCES pilot_content(content_key),response_mode TEXT NOT NULL CHECK(response_mode IN (\'choice\',\'typed\')),topic_title TEXT NOT NULL,PRIMARY KEY(exam_id,position),FOREIGN KEY(exam_id,position) REFERENCES exam_items(exam_id,position))',
 'CREATE TABLE IF NOT EXISTS practice_requests(student_id INTEGER NOT NULL REFERENCES students(id),request_key TEXT NOT NULL,payload_hash TEXT NOT NULL,exam_id INTEGER NOT NULL REFERENCES exams(id),PRIMARY KEY(student_id,request_key))'
]

def initialize(db):
    for sql in SCHEMA:db.execute(sql)

def criteria(body):
    allowed={'intentId','category','count','topicKey','difficulty','week','school','pool','funding'}
    if not isinstance(body,dict) or set(body)-allowed:raise api.APIError('Chỉ gửi tiêu chí tạo đề; không tự chọn cách trả lời/quyền/khóa câu.')
    intent=api.text_field(body,'intentId',80,8)
    c={k:body[k] for k in ('category','count','topicKey','difficulty','week','school','pool','funding') if k in body}
    c.setdefault('pool','all')
    if c['pool'] not in ('all','free','paid'):raise api.APIError('Phạm vi câu hỏi không hợp lệ.')
    if c.get('category') not in ('content','combined','school') or type(c.get('count')) is not int or c['count'] not in (1,2,3,5,10):raise api.APIError('Loại đề hoặc số câu không hợp lệ.')
    if credits.funding(c)==credits.EXAMS and c['count']!=credits.COMPLETE_COUNT:
        raise api.APIError('Một lượt tạo đề đã mua dùng cho một đề đủ 10 câu.')
    if 'topicKey' in c and (not isinstance(c['topicKey'],str) or len(c['topicKey'])>100):raise api.APIError('Chuyên đề không hợp lệ.')
    if 'difficulty' in c and (type(c['difficulty']) is not int or c['difficulty'] not in (1,2,3,4)):raise api.APIError('Mức khó không hợp lệ.')
    if c['category']=='school' or 'school' in c or 'week' in c:raise api.APIError('Chưa có nguồn theo trường/tuần đã duyệt; chưa cấp hoặc trừ lượt.',503)
    return intent,c

class Practice:
    def __init__(self,provider,mapping):
        self.provider=provider
        rows=mapping['questions'];self.mapping={x['contentKey']:x for x in rows}
        if len(rows)!=60 or set(self.mapping)!={q['contentKey'] for q in provider.choice['questions']}:raise ValueError('Taxonomy must map exactly sixty original identities')
        if any(x['quotaKey']!=x['contentKey'] or x.get('convertedToFixedLessonFree') for x in rows):raise ValueError('Taxonomy cannot change identity or access')
        self.original={q['contentKey']:q for q in provider.choice['questions']}
        if any(x['currentProposedAccess']!=self.original[x['contentKey']]['proposedAccess'] for x in rows):raise ValueError('Taxonomy changed access')
        self.revision=digest({'mapping':mapping,'freshTyped':sorted(provider.typed_eligible),'policy':'single-or-complete-choice-v1'})

    def paid_inventory(self,db,config):
        valid=self.pinned_source(db,config)
        free=paid=0
        for ck,row in valid.items():
            if row['scope']=='vip':paid+=1
            elif row['scope']=='free' and row['in_window']:free+=1
        return paid,free+paid

    def pinned_source(self,db,config):
        _,start,end=clock_window()
        scope=set(wallet.scope_keys(db));valid={}
        rows=db.execute("SELECT b.mode,v.content_key,v.version_id,c.proposed_access,q.grade_id,qv.status,qv.options_json, "
                        "EXISTS (SELECT 1 FROM question_assets a WHERE a.question_version_id=qv.id) has_asset, "
                        "EXISTS (SELECT 1 FROM pilot_set_items i JOIN pilot_sets s ON s.set_key=i.set_key "
                        "WHERE i.content_key=v.content_key AND s.grade=? AND s.window_start=? AND s.window_end=?) in_window "
                        "FROM qa_batch_versions v JOIN qa_content_batches b ON b.set_key=v.set_key "
                        "JOIN question_versions qv ON qv.id=v.version_id JOIN pilot_content c ON c.question_id=qv.question_id "
                        "AND c.content_key=v.content_key JOIN questions q ON q.id=qv.question_id "
                        "WHERE (b.mode='choice' AND b.set_key=?) OR (b.mode='typed' AND b.parent_set_key=?)",
                        (config.grade,start,end,config.batch_set_key,config.batch_set_key))
        for row in rows:
            ck=row['content_key'];access=row['proposed_access']
            mode='typed' if ck in self.provider.typed_eligible else 'choice'
            if (ck in self.mapping and row['mode']==mode and row['grade_id']==config.grade and not row['has_asset']
                    and self.original[ck]['proposedAccess'].lower()==access
                    and (mode=='choice')==bool(json.loads(row['options_json']))
                    and version_allowed(db,row['version_id'],row['status']) and (access=='free' or ck in scope)):
                if ck in valid:raise api.APIError('Pin phiên bản không duy nhất; chưa cấp đề.',503)
                valid[ck]={'scope':access,'in_window':bool(row['in_window']),'version_id':row['version_id']}
        return valid

    def pool(self,db,session,config,*,funding=None,balances=None):
        _,start,end=clock_window();state=wallet.balance(db,session,config)
        current_free={r[0] for r in db.execute('SELECT i.content_key FROM pilot_set_items i JOIN pilot_sets s ON s.set_key=i.set_key WHERE s.grade=5 AND s.window_start=? AND s.window_end=?',(start,end))}
        budget=10000 if config.internal_unlimited else state['vip']['available']+state['privateRemaining']
        entitled=state['vip']['active'] or state['privateRemaining']>0 or config.internal_unlimited
        valid=None
        if funding:
            if balances is None:credits.unavailable()
            remaining=credits.amount_left(balances,funding)
            budget=remaining if funding==credits.QUESTIONS else (credits.COMPLETE_COUNT if remaining else 0)
            entitled=bool(remaining)
            valid=self.pinned_source(db,config)
        pool=[]
        for ck,x in self.mapping.items():
            q=self.original[ck];mode='typed' if ck in self.provider.typed_eligible else 'choice';level=min(4,(q['difficultyOriginal']['value']-1)//3+1)
            if valid is not None:
                if ck not in valid:continue
                vid=valid[ck]['version_id']
            else:
                pins=db.execute("SELECT v.version_id FROM qa_batch_versions v JOIN qa_content_batches b ON b.set_key=v.set_key WHERE v.content_key=? AND v.mode=? AND ((b.mode='choice' AND b.set_key=?) OR (b.mode='typed' AND b.parent_set_key=?))",(ck,mode,config.batch_set_key,config.batch_set_key)).fetchall()
                if len(pins)!=1:raise api.APIError('Pin phiên bản không duy nhất; chưa cấp đề.',503)
                vid=pins[0][0]
            old=db.execute('SELECT version_id FROM pilot_grants WHERE student_id=? AND content_key=?',(session['student_id'],ck)).fetchone()
            access=q['proposedAccess'];cost=0
            if old:
                if access=='VIP' and old[0]!=vid and not entitled:continue
            elif access=='Free':
                if ck not in current_free:continue
            else:
                if not budget:continue
                cost=1
            pool.append({'contentKey':ck,'versionId':vid,'responseMode':mode,'topicKey':x['proposedTopicKey'],'topicTitle':x['topicTitle'],'difficulty':level,'access':access,'cost':cost})
        return pool,budget

    @staticmethod
    def capacity(pool,budget):return sum(x['cost']==0 for x in pool)+min(budget,sum(x['cost']==1 for x in pool))

    def metadata(self,db,session,config):
        pool,budget=self.pool(db,session,config);topics={}
        for ck,x in self.mapping.items():
            key=x['proposedTopicKey'];topics.setdefault(key,{'key':key,'title':x['topicTitle'],'totalCount':0})['totalCount']+=1
        for key,row in topics.items():
            items=[x for x in pool if x['topicKey']==key]
            row.update(availableCount=self.capacity(items,budget),freeCount=sum(x['access']=='Free' for x in items),paidCount=self.capacity([x for x in items if x['access']=='VIP'],budget),typedCount=self.capacity([x for x in items if x['responseMode']=='typed'],budget),choiceCount=self.capacity([x for x in items if x['responseMode']=='choice'],budget),difficulties={str(level):self.capacity([x for x in items if x['difficulty']==level],budget) for level in (1,2,3,4)})
        return [topics[key] for key in sorted(topics)]

    def paid_metadata(self,db,session,config,balances):
        if not balances['available']:return {}
        result={}
        for sku in credits.PACKS:
            if not credits.amount_left(balances,sku):continue
            pool,budget=self.pool(db,session,config,funding=sku,balances=balances)
            result[sku]={'questions':[{'contentKey':x['contentKey'],'eligible':True,'cost':x['cost']} for x in pool],
                         'practiceBudget':{'newPaidAvailable':budget,'internalUnlimited':False}}
        return result

    def selection(self,db,session,body,config,*,balances=None):
        intent,c=criteria(body);sid=session['student_id']
        old=db.execute('SELECT * FROM practice_intents WHERE student_id=? AND intent_id=?',(sid,intent)).fetchone()
        if old:
            if old['criteria_hash']!=digest(c):raise api.APIError('intentId đã dùng với tiêu chí khác.',409)
            if old['catalogue_revision']!=self.revision:raise api.APIError('Danh mục đã đổi; bộ đã chọn giữ nguyên, cần rà trước yêu cầu mới.',409)
            return intent,c,json.loads(old['selection_json'])
        if c.get('topicKey') and c['topicKey'] not in {x['proposedTopicKey'] for x in self.mapping.values()}:raise api.APIError('Không có chuyên đề này.',404)
        sku=credits.funding(c)
        pool,budget=self.pool(db,session,config,funding=sku,balances=balances)
        pool=[x for x in pool if (not c.get('topicKey') or x['topicKey']==c['topicKey']) and ('difficulty' not in c or x['difficulty']==c['difficulty']) and (c['pool']=='all' or x['access']==('Free' if c['pool']=='free' else 'VIP'))]
        if self.capacity(pool,budget)<c['count']:raise api.APIError('Chưa đủ câu được phép nhận đúng tiêu chí hoặc số dư; chưa cấp/trừ lượt.',503)
        secrets.SystemRandom().shuffle(pool);selected=[]
        for item in pool:
            if item['cost'] and budget<=0:continue
            selected.append({k:item[k] for k in ('contentKey','versionId','responseMode','topicKey','topicTitle')});budget-=item['cost']
            if len(selected)==c['count']:break
        db.execute('INSERT INTO practice_intents VALUES (?,?,?,?,?,?)',(sid,intent,digest(c),self.revision,api.packed(selected),api.stamp()))
        return intent,c,selected

    def allocation(self,db,session,selection,config,*,funding=None,balances=None):
        selected=[]
        valid=self.pinned_source(db,config) if funding else {}
        for item in selection:
            row=db.execute('SELECT v.status,c.content_key,q.grade_id,v.options_json FROM question_versions v JOIN pilot_content c ON c.question_id=v.question_id JOIN questions q ON q.id=c.question_id WHERE v.id=? AND c.content_key=?',(item['versionId'],item['contentKey'])).fetchone()
            if (not row or row['grade_id']!=5 or not version_allowed(db,item['versionId'],row['status'])
                    or funding and valid.get(item['contentKey'],{}).get('version_id')!=item['versionId']):
                raise api.APIError('Phiên bản đã ngừng cấp; giữ bộ đã chọn để rà lại.',409)
            if (item['responseMode']=='choice')!=bool(json.loads(row['options_json'])):raise api.APIError('Pin cách trả lời không hợp lệ.',503)
            selected.append({'content_key':item['contentKey'],'version_id':item['versionId']})
        body={'contentKeys':[x['contentKey'] for x in selection],'responseMode':'typed'}
        a=wallet.plan(db,session,selected,{x['content_key']:x for x in selected},config,body,purchased_sku=funding)
        if funding:
            if balances is None:credits.unavailable()
            keys=[x['quotaKey'] for x in a['allocations'] if x['source']=='purchased']
            a['purchased']=credits.allocation(funding,balances,keys)
        return a

    def quote(self,db,session,body,config,*,balances=None):
        intent,c,selection=self.selection(db,session,body,config,balances=balances)
        sku=credits.funding(c)
        a=self.allocation(db,session,selection,config,funding=sku,balances=balances)
        a.update(intentId=intent,criteria=c,selection=selection,catalogueRevision=self.revision)
        if sku:return {**a,**credits.quote(db,session,sku,{'intentId':intent,'selection':selection,'catalogueRevision':self.revision},a)}
        qid='quote-'+secrets.token_hex(16);expires=api.stamp(api.now()+timedelta(minutes=2))
        db.execute('INSERT INTO wallet_quotes VALUES (?,?,?,?,?,?,?)',(qid,session['student_id'],digest({'intentId':intent,'selection':selection,'catalogueRevision':self.revision}),api.packed(a),a['private'],expires,wallet.POLICY))
        return {**a,'quoteId':qid,'expiresAt':expires}

    def selected_title(self,grade,c):
        """Only validated selector kinds and trusted taxonomy enter new titles."""
        label={'content':'Đề luyện tập theo nội dung','combined':'Đề luyện tập tổng hợp'}[c['category']]
        topic=None
        if c['category']=='content' and c.get('topicKey'):
            topic=next(x['topicTitle'] for x in self.mapping.values() if x['proposedTopicKey']==c['topicKey'])
            if not isinstance(topic,str) or not topic.strip() or len(topic)>120 or any(ord(ch)<32 for ch in topic):raise api.APIError('Tên nội dung trong danh mục không hợp lệ.',503)
            topic=topic.strip()
        title=label+((' – '+topic) if topic else '')+' – Lớp '+str(grade)
        return title,{'category':c['category'],'topicKey':c.get('topicKey'),'topicTitle':topic,'difficulty':c.get('difficulty'),'questionCount':c['count'],'titleSource':'validated-owner-quote'}

    def create(self,db,session,body,config,*,balances=None,bank_db=None,bank_student_id=None):
        sku=credits.funding(body)
        extra={'funding','confirmPurchased'} if sku else set()
        if not isinstance(body,dict) or set(body)!=({'intentId','requestKey','quoteId','confirmWallet'}|extra) or type(body['confirmWallet']) is not bool:raise api.APIError('Chỉ gửi xác nhận của bộ đã chọn.')
        key=api.text_field(body,'requestKey',80,8);intent=api.text_field(body,'intentId',80,8);sid=session['student_id'];payload=digest(body)
        old=db.execute('SELECT * FROM practice_requests WHERE student_id=? AND request_key=?',(sid,key)).fetchone()
        if old:
            if old['payload_hash']!=payload:raise api.APIError('requestKey đã dùng với nội dung khác.',409)
            return api.exam_view(db,api.owned_attempt(db,session,old['exam_id']))
        if db.execute('SELECT 1 FROM exam_attempts WHERE student_id=? AND request_key=?',(sid,key)).fetchone():raise api.APIError('requestKey thuộc bài khác.',409)
        if sku and db.execute('SELECT 1 FROM purchased_credit_usage WHERE student_id=? AND intent_id=?',(sid,intent)).fetchone():
            raise api.APIError('Xác nhận này đã được dùng để tạo một đề.',409)
        row=db.execute('SELECT * FROM practice_intents WHERE student_id=? AND intent_id=?',(sid,intent)).fetchone()
        if not row:raise api.APIError('Không tìm thấy bộ câu đã chọn của em.',404)
        selection=json.loads(row['selection_json']);a=self.allocation(db,session,selection,config,funding=sku,balances=balances)
        a.update(intentId=intent,selection=selection,catalogueRevision=row['catalogue_revision'])
        quoted_fields={'intentId':intent,'selection':selection,'catalogueRevision':self.revision}
        if sku:
            if bank_db is None:credits.unavailable()
            plan=credits.confirm(db,session,sku,quoted_fields,body)
            if plan['purchased']['quantity']!=a['purchased']['quantity']:raise wallet.QuoteChanged(a,purchased=True)
        else:
            quote=db.execute('SELECT * FROM wallet_quotes WHERE quote_id=? AND student_id=?',(body['quoteId'],sid)).fetchone() if isinstance(body['quoteId'],str) else None
            expected=digest(quoted_fields)
            if not quote or quote['expires_at']<=api.stamp() or quote['selector_hash']!=expected or quote['policy_version']!=wallet.POLICY or a['private']>quote['max_private'] or a['private'] and not body['confirmWallet']:raise wallet.QuoteChanged(a)
            plan=json.loads(quote['plan_json'])
        # Existing quote JSON already pins the original allowlisted criteria.
        # A matching selector hash alone does not prove a proposed title/kind.
        try:
            stored=plan['criteria']
            selected_intent,clean=criteria({**stored,'intentId':intent})
        except (TypeError,ValueError,KeyError):
            raise wallet.QuoteChanged(a,purchased=bool(sku))
        if selected_intent!=intent or clean!=stored or digest(clean)!=row['criteria_hash'] or credits.funding(clean)!=sku:
            raise wallet.QuoteChanged(a,purchased=bool(sku))
        if db.execute('SELECT count(*) FROM exam_attempts WHERE student_id=? AND started_at>?',(sid,api.stamp(api.now()-timedelta(hours=1)))).fetchone()[0]>=60:raise api.APIError('Em đã tạo nhiều đề; hãy tiếp tục bài đang làm.',429)
        grade,ayid=api.ensure_grade(db,sid,session['birth_year'])
        title,selection_metadata=self.selected_title(grade,clean)
        a.update(criteria=clean,practiceTitle=title,practiceSelection=selection_metadata)
        eid=db.execute("INSERT INTO exams(exam_code,title,grade_level,duration_minutes,status,academic_year_id,owner_student_id,mode,created_at,response_mode) VALUES (?,?,?,30,'published',?,?,'test',?,'typed')",('PRACTICE-'+secrets.token_hex(8),title,grade,ayid,sid,api.stamp())).lastrowid
        for pos,item in enumerate(selection,1):
            options=db.execute('SELECT options_json FROM question_versions WHERE id=?',(item['versionId'],)).fetchone()[0]
            db.execute('INSERT INTO exam_items VALUES (?,?,?,?,?)',(eid,pos,item['versionId'],1,options))
            db.execute('INSERT INTO practice_exam_items VALUES (?,?,?,?,?)',(eid,pos,item['contentKey'],item['responseMode'],item['topicTitle']))
            if not db.execute('SELECT 1 FROM pilot_grants WHERE student_id=? AND content_key=?',(sid,item['contentKey'])).fetchone():db.execute('INSERT INTO pilot_grants VALUES (?,?,?,?,?,0)',(sid,item['contentKey'],item['versionId'],api.stamp(),a['vipBudget']['day']))
        if sku:
            keys=[x['quotaKey'] for x in a['allocations'] if x['source']=='purchased'] if sku==credits.QUESTIONS else []
            credits.debit(db,session,bank_db,bank_student_id,eid,body,a['purchased'],keys)
        else:
            wallet.debit(db,session,a,eid)
        db.execute("INSERT INTO exam_attempts(exam_id,student_id,started_at,due_at,status,request_key) VALUES (?,?,?,?,'in_progress',?)",(eid,sid,api.stamp(),api.stamp(api.now()+timedelta(minutes=30)),key))
        db.execute('INSERT INTO practice_requests VALUES (?,?,?,?)',(sid,key,payload,eid))
        # Existing owner/history and replay machinery recognizes the original request too.
        db.execute('INSERT INTO pilot_requests VALUES (?,?,?,?)',(sid,key,payload,eid))
        return api.exam_view(db,api.owned_attempt(db,session,eid))

def item_pin(db,eid,pos):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='practice_exam_items'").fetchone():return None
    return db.execute('SELECT * FROM practice_exam_items WHERE exam_id=? AND position=?',(eid,pos)).fetchone()

def history(db,sid,provider):
    result=[]
    for r in db.execute('SELECT a.*,e.title,e.response_mode,e.owner_student_id,e.form_id,e.status exam_status FROM exam_attempts a JOIN exams e ON e.id=a.exam_id WHERE a.student_id=? ORDER BY a.started_at DESC,a.id DESC',(sid,)):
        done=r['status']=='submitted';eid=str(r['exam_id']);item={'reference':provider+':'+eid,'provider':provider,'id':eid,'title':r['title'],'submitted':done,'submittedAt':r['submitted_at'],'startedAt':r['started_at'],'responseMode':r['response_mode'],'questionCount':db.execute('SELECT count(*) FROM exam_items WHERE exam_id=?',(r['exam_id'],)).fetchone()[0]}
        if provider=='pilot' and db.execute("SELECT 1 FROM sqlite_master WHERE name='practice_exam_items'").fetchone():
            modes={x[0] for x in db.execute('SELECT DISTINCT response_mode FROM practice_exam_items WHERE exam_id=?',(r['exam_id'],))}
            if modes:item['responseMode']='mixed' if len(modes)>1 else next(iter(modes))
        if done:item['score']=round(r['earned_points']/r['total_points']*10,1) if r['total_points'] else 0
        item['canRetake']=r['owner_student_id']==sid and r['form_id'] is None and r['exam_status']=='published'
        result.append(item)
    from .study_retake import collapse
    return collapse(db,result,provider)[:200]
