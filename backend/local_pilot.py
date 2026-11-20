"""Local-only native learning provider. Main sessions authenticate; every write goes to pilot DB."""
from base64 import b64decode
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta
from pathlib import Path
from types import SimpleNamespace
import hashlib,hmac,json,re,secrets,threading,ipaddress
import xml.etree.ElementTree as ET
from . import platform_api as api,wallet_qa as wallet,purchased_credits as credits
from .free_vip_pilot import PilotConfig,clock_window,create_exam
from .content_batch_qa import import_batch
from .mcq_import import load_json,digest,require_qa
from .learning_update import membership
from .answers import requires_choice

SCHEMA=[
 'CREATE TABLE IF NOT EXISTS local_principals(main_account_id INTEGER PRIMARY KEY,main_student_id INTEGER NOT NULL UNIQUE,pilot_account_id INTEGER NOT NULL UNIQUE,pilot_student_id INTEGER NOT NULL UNIQUE,created_at TEXT NOT NULL)',
 'CREATE TABLE IF NOT EXISTS local_lesson_versions(content_key TEXT NOT NULL,revision INTEGER NOT NULL,payload_hash TEXT NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(content_key,revision))',
 'CREATE TABLE IF NOT EXISTS local_lesson_pins(version_id INTEGER PRIMARY KEY REFERENCES question_versions(id),content_key TEXT NOT NULL,lesson_revision INTEGER NOT NULL,FOREIGN KEY(content_key,lesson_revision) REFERENCES local_lesson_versions(content_key,revision))',
 'CREATE TABLE IF NOT EXISTS local_lesson_assets(sha256 TEXT PRIMARY KEY,mime TEXT NOT NULL,payload BLOB NOT NULL)',
 'CREATE TABLE IF NOT EXISTS local_installations(batch_key TEXT PRIMARY KEY,source_hash TEXT NOT NULL,derived_manifest_json TEXT NOT NULL,installed_at TEXT NOT NULL)'
]

def safe_svg(data):
    root=ET.fromstring(data);allowed={'svg','g','rect','path','line','polyline','polygon','circle','ellipse','text','tspan','defs','marker','title','desc'}
    for node in root.iter():
        if node.tag.split('}')[-1] not in allowed:raise ValueError('Unsafe SVG tag')
        for attr,value in node.attrib.items():
            name=attr.split('}')[-1].lower()
            if name.startswith('on') or name in ('href','src') or 'javascript:' in value.lower() or ('url(' in value and not re.fullmatch(r'url\(#[A-Za-z0-9_-]+\)',value)):raise ValueError('Unsafe SVG attribute')
    return data

def media_keys(value):
    if isinstance(value,list):return set().union(*(media_keys(x) for x in value)) if value else set()
    if not isinstance(value,dict):return set()
    result={value['sha256']} if value.get('type')=='media' else set()
    for child in value.values():
        if isinstance(child,(dict,list)):result|=media_keys(child)
    return result

def migrate_pilot_premium(path):
    """Extend the dedicated learning store without importing main-only game schema."""
    from .database import execute_sql
    with api.connect(path, True) as db:
        for name in ('0024_vip_plus.sql', '0025_exam_commerce.sql', '0027_premium_admin.sql', '0028_native_admin.sql', '0036_local_pilot_family_grades.sql', '0043_purchased_credits.sql'):
            if not db.execute('SELECT 1 FROM schema_migrations WHERE name=?', (name,)).fetchone():
                execute_sql(db, (Path(__file__).with_name('migrations') / name).read_text(encoding='utf-8'))
                db.execute('INSERT INTO schema_migrations(name) VALUES (?)', (name,))


class LocalPilot:
    def __init__(self,main_database,pilot_database,inputs,restructure_inputs=None):
        self.path=Path(pilot_database).resolve();self.inputs=Path(inputs).resolve();self.lock=threading.RLock();self.week_cache=None
        if self.path==Path(main_database).resolve() or (self.path.exists() and Path(main_database).exists() and self.path.samefile(main_database)):raise ValueError('Pilot DB must be separate from main DB')
        seal=load_json(self.inputs/'manifest.json')
        expected={'questions-mcq60.json','batch-manifest.json','questions-typed-subset.json','typed-manifest.json','sources.json','lessons-bundle.json'}
        if {r['path'] for r in seal['files']}!=expected:raise ValueError('Six sealed pilot inputs required')
        for row in seal['files']:
            payload=(self.inputs/row['path']).read_bytes()
            if hashlib.sha256(payload).hexdigest()!=row['sha256'] or len(payload)!=row['bytes']:raise ValueError('Sealed pilot input mismatch')
        self.choice=load_json(self.inputs/'questions-mcq60.json');self.original_manifest=load_json(self.inputs/'batch-manifest.json')
        self.typed=load_json(self.inputs/'questions-typed-subset.json');self.original_typed=load_json(self.inputs/'typed-manifest.json');self.sources=load_json(self.inputs/'sources.json')
        self.choice_required={q['contentKey'] for q in self.typed['questions'] if requires_choice(q)}
        self.typed_eligible=set(self.original_typed['eligibleContentKeys'])-self.choice_required
        self.bundle=load_json(self.inputs/'lessons-bundle.json');self.lessons={x['source']['contentKey']:x for x in self.bundle['lessons']}
        if len(self.lessons)!=60 or set(self.lessons)!={q['contentKey'] for q in self.choice['questions']}:raise ValueError('Exactly sixty matching sealed lessons required')
        self.assets={a['sha256']:safe_svg(b64decode(a['base64'],validate=True)) for a in self.bundle['assets']}
        if any(hashlib.sha256(v).hexdigest()!=k for k,v in self.assets.items()):raise ValueError('Lesson asset SHA mismatch')
        if not self.path.exists():
            from scripts.import_mcq_qa import initialize_empty_qa
            initialize_empty_qa(self.path,seed_learning=False)
        migrate_pilot_premium(self.path)
        with api.connect(self.path,True) as db:
            require_qa(db)
            from .scratchpads import initialize as initialize_scratchpads
            initialize_scratchpads(db)
            from .practice_export import initialize as initialize_exports
            initialize_exports(db)
            for sql in SCHEMA:db.execute(sql)
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='wallet_scopes'").fetchone():wallet.initialize(db,self.original_manifest['vipSupplementContentKeys'])
            for ck,lesson in self.lessons.items():
                old=db.execute('SELECT payload_hash FROM local_lesson_versions WHERE content_key=? AND revision=?',(ck,lesson['revision'])).fetchone()
                if old and old[0]!=digest(lesson):raise ValueError('Immutable lesson revision conflict')
                db.execute('INSERT OR IGNORE INTO local_lesson_versions VALUES (?,?,?,?)',(ck,lesson['revision'],digest(lesson),api.packed(lesson)))
            for sha,data in self.assets.items():db.execute('INSERT OR IGNORE INTO local_lesson_assets VALUES (?,\'image/svg+xml\',?)',(sha,data))
        self.ensure_week()
        self.practice=None;self.knowledge=None
        if restructure_inputs is not None:
            from .practice_catalogue import Practice,initialize
            self.practice=Practice(self,load_json(Path(restructure_inputs)/'mapping60.json'))
            with api.connect(self.path,True) as db:initialize(db)
            from .knowledge_catalogue import Knowledge
            self.knowledge=Knowledge(self,Path(restructure_inputs))
            from .curriculum_samples import activate_provider
            self.practice=activate_provider(self,self.practice)
            if hasattr(self.practice,'supports_grade'):self.choice_required.update(self.practice.questions)

    def ensure_week(self):
        with self.lock:
            _,start,end=clock_window()
            if self.week_cache and self.week_cache[0]==start:return self.week_cache[1],self.week_cache[2]
            m=deepcopy(self.original_manifest);tm=deepcopy(self.original_typed);sk='local.g5.pilot60.'+start
            m.update(setKey=sk,windowStart=start+'T00:00:00+07:00',windowEnd=end+'T00:00:00+07:00')
            for item in m['freeSets']:item['setKey']=sk+'.free.'+str(item['slot'])
            tm.update(setKey=sk+'.typed',parentSetKey=sk,windowStart=m['windowStart'],windowEnd=m['windowEnd'])
            import_batch(self.path,self.choice,m,self.sources,allow_batch_qa=True,allow_draft_qa=True)
            import_batch(self.path,self.typed,tm,self.sources,allow_batch_qa=True,allow_draft_qa=True)
            with api.connect(self.path,True) as db:
                db.execute('INSERT OR IGNORE INTO local_installations VALUES (?,?,?,?)',(sk,digest({'choice':self.original_manifest,'typed':self.original_typed}),api.packed({'reason':'Derived local current-week pins; original author manifests preserved','choice':m,'typed':tm}),api.stamp()))
                for row in db.execute('SELECT version_id,content_key FROM qa_batch_versions WHERE set_key IN (?,?)',(sk,tm['setKey'])):
                    lesson=self.lessons[row['content_key']];old=db.execute('SELECT content_key,lesson_revision FROM local_lesson_pins WHERE version_id=?',(row['version_id'],)).fetchone()
                    if old and tuple(old)!=(row['content_key'],lesson['revision']):raise ValueError('Immutable lesson pin conflict')
                    db.execute('INSERT OR IGNORE INTO local_lesson_pins VALUES (?,?,?)',(row['version_id'],row['content_key'],lesson['revision']))
            config=PilotConfig(wallet=True,batch_set_key=sk);self.week_cache=(start,config,m)
            return config,m

    def principal(self,db,main,role,grade=None):
        row=db.execute('SELECT * FROM local_principals WHERE main_account_id=?',(main['account_id'],)).fetchone()
        if row and row['main_student_id']!=main['student_id']:raise api.APIError('Mapping học sinh cần được rà lại.',409)
        if not row:
            if isinstance(main,dict) and 'family_id' in main:
                # Trusted main session supplies identity/grade. A technical child
                # mirror must not pass the old age-based public signup validator.
                trusted_grade=grade if grade is not None else main.get('grade')
                if type(trusted_grade) is not int or not 1<=trusted_grade<=5:raise api.APIError('Chưa xác định được khối học của con.',409)
                code=secrets.token_hex(16)
                aid=db.execute('INSERT INTO accounts(account_code,login_identifier,birth_year,invite_code,created_at,password_hash) VALUES(?,?,?,?,?,NULL)',
                               ('LFP-'+code,'local-pilot-'+str(main['account_id'])+'-'+code,main['birth_year'],'5B'+code[:16].upper(),api.stamp())).lastrowid
                sid=db.execute('INSERT INTO students(student_code,full_name,grade_level,account_id) VALUES(?,?,?,?)',
                               ('LFP-'+code,'Học sinh thí điểm',trusted_grade,aid)).lastrowid
                db.execute("INSERT INTO student_companions(student_id,mascot_id) SELECT ?,id FROM mascots WHERE name='Mầm Sách'",(sid,))
                db.execute('INSERT INTO learning_preferences(student_id,theme) VALUES(?,?)',(sid,api.DEFAULT_THEME))
                session={'account_id':aid,'student_id':sid}
            else:
                fake=SimpleNamespace(server=SimpleNamespace(),headers={},api_headers={})
                session=api.register(fake,db,{'login':'local-pilot-'+str(main['account_id'])+'-'+secrets.token_hex(5),'password':secrets.token_urlsafe(32),'name':'Học sinh thí điểm','birthYear':main['birth_year']},credential=getattr(self,'mirror_credential',None))
            db.execute('INSERT INTO local_principals VALUES (?,?,?,?,?)',(main['account_id'],main['student_id'],session['account_id'],session['student_id'],api.stamp()))
            db.execute('DELETE FROM auth_sessions WHERE account_id=?',(session['account_id'],));row=db.execute('SELECT * FROM local_principals WHERE main_account_id=?',(main['account_id'],)).fetchone()
        if isinstance(main,dict) and 'family_id' in main:
            trusted_grade=grade if grade is not None else main.get('grade')
            if type(trusted_grade) is not int or not 1<=trusted_grade<=5:raise api.APIError('Chưa xác định được khối học của con.',409)
            db.execute('INSERT INTO local_pilot_family_grades VALUES(?,?,?,?,?,?) ON CONFLICT(pilot_student_id) DO UPDATE SET '
                       'main_family_id=excluded.main_family_id,main_student_id=excluded.main_student_id,declared_grade=excluded.declared_grade,'
                       'grade_academic_year=excluded.grade_academic_year,updated_at=excluded.updated_at',
                       (row['pilot_student_id'],main['family_id'],main['student_id'],trusted_grade,api.academic()[0],api.stamp()))
            # Correct older technical mirror grade history, never its true birth.
            _,ayid=api.ensure_grade(db,row['pilot_student_id'],main['birth_year'])
            db.execute('UPDATE student_grades SET grade_id=? WHERE student_id=? AND academic_year_id=?',(trusted_grade,row['pilot_student_id'],ayid))
            db.execute('UPDATE students SET grade_level=? WHERE id=?',(trusted_grade,row['pilot_student_id']))
        expiry=main['vip_expires_at'] if role in ('VIP','VIP+') else None
        db.execute('UPDATE accounts SET vip_expires_at=? WHERE id=?',(expiry,row['pilot_account_id']))
        db.execute('UPDATE accounts SET vip_plus_expires_at=? WHERE id=?',(main['vip_plus_expires_at'] if role=='VIP+' else None,row['pilot_account_id']))
        if role in ('VIP','VIP+','SVip'):db.execute('INSERT OR IGNORE INTO wallet_terms VALUES (?,?,?)',(row['pilot_student_id'],api.stamp(),wallet.POLICY))
        return {**dict(main),'account_id':row['pilot_account_id'],'student_id':row['pilot_student_id']}

    def catalogue(self,db,session,config,m,role):
        eligible=self.typed_eligible
        history=[{'id':str(r['exam_id']),'submitted':r['status']=='submitted','mode':r['response_mode']} for r in db.execute('SELECT a.exam_id,a.status,e.response_mode FROM exam_attempts a JOIN exams e ON e.id=a.exam_id WHERE a.student_id=? ORDER BY a.id DESC LIMIT 60',(session['student_id'],))]
        rows=[{'contentKey':q['contentKey'],'title':self.lessons[q['contentKey']]['title'],'access':q['proposedAccess'],'typed':q['contentKey'] in eligible,'choiceRequired':q['contentKey'] in self.choice_required,'skillKey':q['skillKey']} for q in self.choice['questions']]
        result={'localPilot':True,'notice':'Thí điểm cục bộ lớp 5 · học liệu tự biên soạn, chờ giáo viên rà · ví/điểm riêng, không đổi VIP hoặc XP tài khoản chính','role':role,'internalUnlimited':role=='SVip','windowStart':m['windowStart'],'windowEnd':m['windowEnd'],'sets':m['freeSets'],'questions':rows,'typedEligible':sorted(eligible),'responsePolicy':'single-or-complete-choice-v1','wallet':wallet.balance(db,session,config),'history':history,'cycleNotice':('Gói năm: 30 câu mới/ngày, tối đa 3.600 câu cho toàn bộ kỳ 12 tháng; không đặt lại mỗi tháng.' if config.vip_cycle_start else 'Chu kỳ ví thí điểm 30 ngày từ lần đầu sử dụng với quyền VIP; không thay kỳ thanh toán gói chính.')}
        if self.practice and not hasattr(self.practice,'catalogue'):
            from .free_vip_pilot import clock_window
            _,start,end=clock_window()
            available={r[0] for r in db.execute('SELECT i.content_key FROM pilot_set_items i JOIN pilot_sets s ON s.set_key=i.set_key WHERE s.grade=5 AND s.window_start=? AND s.window_end=?',(start,end))}
            result.update(restructureEnabled=True,topics=self.practice.metadata(db,session,config),knowledge=self.knowledge.catalogue(db,session),practiceCounts=[1,2,3,5,10],schoolReady=False,schoolAccess=role in ('VIP+','SVip'),advancedAccess=role in ('VIP+','SVip'),weekReady=False,catalogueRevision=self.practice.revision,availableFreeKeys=sorted(available))
            eligible_pool,paid_budget=self.practice.pool(db,session,config)
            eligible_by_key={x['contentKey']:x for x in eligible_pool}
            result['practiceBudget']={'newPaidAvailable':paid_budget,'internalUnlimited':config.internal_unlimited}
            for q in result['questions']:
                entry=eligible_by_key.get(q['contentKey']);q.update(eligible=entry is not None,cost=entry['cost'] if entry else None)
                q.update(topicKey=self.practice.mapping[q['contentKey']]['proposedTopicKey'],responseMode='typed' if q['contentKey'] in self.typed_eligible else 'choice',difficulty=min(4,(self.practice.original[q['contentKey']]['difficultyOriginal']['value']-1)//3+1))
        if hasattr(self.practice,'catalogue'):
            result.update(restructureEnabled=True,knowledge=self.knowledge.catalogue(db,session) if config.grade==5 else {'topics':[],'lessons':[]},
                          practiceCounts=[1,2,3,5,10],schoolReady=False,schoolAccess=role in ('VIP+','SVip'),
                          advancedAccess=role in ('VIP+','SVip'),weekReady=False)
            result=self.practice.catalogue(db,session,config,result)
        return result

    def paid_inventory(self,db,grade=5):
        if db is None or self.practice is None:return 0,0
        return self.practice.paid_inventory(db,replace(self.week_cache[1],grade=grade))

    def lesson(self,db,session,eid,ck):
        attempt=api.owned_attempt(db,session,eid)
        if attempt['status']!='submitted':raise api.APIError('Nộp bài trước khi mở bài giảng và lời giải.',403)
        row=db.execute('SELECT v.payload_json FROM exam_items i JOIN local_lesson_pins p ON p.version_id=i.question_version_id JOIN local_lesson_versions v ON v.content_key=p.content_key AND v.revision=p.lesson_revision WHERE i.exam_id=? AND p.content_key=?',(eid,ck)).fetchone()
        if not row:raise api.APIError('Bài giảng không thuộc phiên bản bài đã nộp.',404)
        return json.loads(row[0])

    def request(self,handler,method,path,body,query):
        host=handler.headers.get('Host','');ports=getattr(handler.server,'local_pilot_ports',{handler.server.server_port});expected={f'{name}:{port}' for name in ('127.0.0.1','localhost') for port in ports}
        # LAN devices may resume owned work and sync drafts. New allocations,
        # wallet operations and native PDF remain on the existing loopback gate.
        lan=False
        try:
            from urllib.parse import urlsplit
            parsed=urlsplit('//'+host);address=ipaddress.ip_address(parsed.hostname or '')
            private=any(address in ipaddress.ip_network(network) for network in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
            lan=private and parsed.port in ports and not(parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment) and getattr(handler.server,'native_python_backend',False) is True
        except (ValueError,TypeError):pass
        resume=bool(re.fullmatch(r'exams/[1-9][0-9]*(?:/(?:scratch|answers|submit|review|receipt|lesson|asset|retake))?',path))
        read=method=='GET' and (path in ('catalogue','history') or resume)
        edit=method=='POST' and bool(re.fullmatch(r'exams/[1-9][0-9]*/(?:scratch|answers|submit|retake)',path))
        cloud=self is getattr(handler.server,'cloud_learning_provider',None)
        if cloud and (not api.same_origin(handler) or (method=='POST' and not handler.headers.get('Origin'))):raise api.APIError('Yêu cầu học tập phải cùng origin.',403)
        if not cloud and host not in expected and not(lan and (read or edit)):raise api.APIError('Tạo đề và thao tác kho thí điểm chỉ mở trên localhost. Em có thể mở bài đã có và tiếp tục làm qua LAN.',403)
        if not cloud and method=='POST' and handler.headers.get('Origin')!='http://'+host:raise api.APIError('Yêu cầu thí điểm phải cùng origin.',403)
        allocated=method=='POST' and path in ('practice/quote','practice/exams')
        sku=credits.funding(body) if allocated else None
        if sku and (self.practice is None or cloud and not getattr(handler.server,'cloud_paid_credits_enabled',False)):credits.unavailable()
        paid_create=bool(sku and path=='practice/exams')
        with api.connect(handler.server.database_path) as main_db:
            main=api.read_session(handler,main_db)
            if not main:
                error=api.APIError('Em hãy đăng nhập tài khoản chính trước.',401)
                from .family_accounts import family_present
                if family_present(handler):error.familyAccessChanged=True
                raise error
            if method=='POST' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),main['csrf_token']):raise api.APIError('Phiên đăng nhập cần tải lại.',403)
            if method=='POST' and path in ('quote','exams','practice/quote','practice/exams'):
                from .system_settings import require_feature
                require_feature(main_db,'practice_open')
            grade=api.grade_for_student(main_db,main['student_id'],main['birth_year']);role=membership(main_db,main)
            from .family_personal import effective_dates
            # Trusted derived capabilities only; never change main paid columns.
            main={**dict(main),**effective_dates(main_db,main['account_id'])}
            from .subscriptions import active_annual_cycle
            annual=active_annual_cycle(main_db,main) if role in ('VIP','VIP+') else None
            if method=='POST' and path in ('practice/quote','practice/exams') and body.get('category')=='school':
                from .premium_content import require_plus
                require_plus(main_db,main)
            if path.startswith('knowledge/'):
                from .system_settings import require_feature
                require_feature(main_db,'learning_open')
            main_history=[]
            if self.practice and method=='GET' and path=='history':
                from .practice_catalogue import history
                main_history=history(main_db,main['student_id'],'main')
        sample_grade=bool(hasattr(self.practice,'supports_grade') and self.practice.supports_grade(grade))
        if grade!=5 and not sample_grade:raise api.APIError('Bộ thí điểm này dành cho lớp 5. Khối học và quyền tài khoản của em được giữ nguyên; không trừ lượt.',403)
        if grade!=5 and path.startswith('knowledge/'):raise api.APIError('Bài giảng này thuộc khối 5.',403)
        if grade!=5 and path in ('quote','exams','orders','mock-confirm','mock-fail'):raise api.APIError('Nguồn cũ này dành cho khối 5; hãy dùng bộ mẫu đúng lớp.',403)
        config,m=self.ensure_week();config=replace(config,grade=grade,internal_unlimited=role=='SVip')
        if annual:config=replace(config,vip_daily=30,vip_cycle=annual['limit'],vip_cycle_start=annual['start'],vip_cycle_end=annual['end'])
        from .database import initialize as initialize_database
        initialize_database(self.path)
        if paid_create:
            with api.connect(self.path) as source:
                key=credits.store_key(source)
            credits.bind_native(handler.server.database_path,main['student_id'],key)
        purchased_catalogue=(not cloud or getattr(handler.server,'cloud_paid_credits_enabled',False)) and self.practice and method=='GET' and path=='catalogue'
        sample_free_create=bool(sample_grade and role=='Free' and not sku and method=='POST' and path=='practice/exams')
        with ExitStack() as stack:
            # Hold the canonical writer from before the pilot BEGIN until after
            # its commit. The creation writes only the attempt store.
            bank=stack.enter_context(api.connect(handler.server.database_path,paid_create or sample_free_create)) if sku or purchased_catalogue or sample_free_create else None
            if paid_create or sample_free_create:
                current=api.read_session(handler,bank)
                if (not current or current['account_id']!=main['account_id'] or current['student_id']!=main['student_id']
                        or not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),current['csrf_token'])):
                    raise api.APIError('Phiên đăng nhập cần được tải lại.',403)
                from .system_settings import require_feature
                require_feature(bank,'practice_open')
                if api.grade_for_student(bank,current['student_id'],current['birth_year'])!=grade:
                    raise api.APIError('Hồ sơ không còn thuộc khối học này.',409)
            db=stack.enter_context(api.connect(self.path,True))
            require_qa(db);session=self.principal(db,main,role,grade)
            if isinstance(main,dict) and 'family_id' in main and method=='POST' and path in ('exams','practice/exams'):
                # The pilot store alone owns these attempt IDs and ledgers. Main
                # attempt IDs can coincide; never compare unqualified IDs/stores.
                key=body.get('requestKey')
                previous=db.execute('SELECT 1 FROM pilot_requests WHERE student_id=? AND request_key=?',(session['student_id'],key)).fetchone() if isinstance(key,str) else None
                if not previous and db.execute("SELECT 1 FROM exam_attempts WHERE student_id=? AND status='in_progress' AND due_at>? LIMIT 1",(session['student_id'],api.stamp())).fetchone():
                    raise api.APIError('Con còn bài thí điểm đang làm. Hãy tiếp tục hoặc nộp bài trước khi mở lượt mới.',409)
            if (method=='POST' and path=='practice/export') or (method=='GET' and path=='practice/lookup'):
                from .practice_export_api import available
                if not available(handler):raise api.APIError('PDF và tra cứu mã chỉ mở trên localhost đã cấu hình.',503)
                if query.get('solutions',['0'])[0] not in ('0','1'):raise api.APIError('Lựa chọn lời giải không hợp lệ.')
                from .practice_export import export_pdf,lookup
                if method=='POST':return export_pdf(db,session,body,provider='pilot',frontend=Path(__file__).resolve().parents[1]/'frontend')
                return lookup(db,session,query.get('code',[''])[0],solutions=query.get('solutions',['0'])[0]=='1')
            if method=='POST' and path in ('quote','exams') and body.get('responseMode')=='typed':
                # Existing requests/replay/history retain their immutable representation.
                prior = db.execute('SELECT 1 FROM pilot_requests WHERE student_id=? AND request_key=?',(session['student_id'],body.get('requestKey'))).fetchone() if path=='exams' and isinstance(body.get('requestKey'),str) else None
                keys=body.get('contentKeys',[])
                if not isinstance(keys,list):raise api.APIError('Danh sách câu hỏi không hợp lệ.')
                if not prior and any(key in self.choice_required for key in keys if isinstance(key,str)):
                    raise api.APIError('Câu có nhiều ý hoặc nhiều đối tượng cần đáp số: em hãy chọn dạng trắc nghiệm đầy đủ.',409)
            if self.practice:
                if allocated:
                    balances=credits.balance(bank,main['student_id'],db) if sku else None
                    if path=='practice/quote':return self.practice.quote(db,session,body,config,balances=balances)
                    result=self.practice.create(db,session,body,config,balances=balances,
                                                bank_db=bank,bank_student_id=main['student_id'])
                    if sample_free_create:
                        from .learning_update import consume
                        receipt=wallet.attempt_receipt(db,session,int(result['id']))
                        category=receipt['allocation'].get('criteria',{}).get('category')
                        if category not in ('content','combined'):raise api.APIError('Chưa xác định được hạn mức của đề.',503)
                        consume(bank,current,category,body['requestKey'])
                    return {'exam':result}
                if method=='GET' and path=='history':
                    from .practice_catalogue import history
                    items=main_history+history(db,session['student_id'],'pilot');items.sort(key=lambda x:(x['startedAt'],x['reference']),reverse=True)
                    return {'items':items,'pending':[x for x in items if not x['submitted']],'completed':[x for x in items if x['submitted']]}
                if path.startswith('knowledge/'):
                    parts=path.split('/')
                    if len(parts)==2 and method=='GET':
                        rev=query.get('revision',[None])[0]
                        if rev is not None and (not isinstance(rev,str) or not rev.isdigit()):raise api.APIError('Phiên bản không hợp lệ.')
                        return self.knowledge.lesson(db,session,parts[1],int(rev) if rev else None)
                    if len(parts)==3 and parts[2]=='check' and method=='POST':return self.knowledge.check(db,session,parts[1],body)
                    if len(parts)==3 and parts[2]=='complete' and method=='POST':return self.knowledge.complete(db,session,parts[1],body)
                    if len(parts)==3 and parts[2]=='asset' and method=='GET':
                        rev=query.get('revision',[''])[0]
                        if not isinstance(rev,str) or not rev.isdigit():raise api.APIError('Cần phiên bản bài học cho tài sản.')
                        return self.knowledge.asset(db,session,parts[1],query.get('sha',[''])[0],int(rev))
                    raise api.APIError('Không có thao tác bài kiến thức này.',404)
            if method=='GET' and path=='catalogue':
                result=self.catalogue(db,session,config,m,role)
                if purchased_catalogue:
                    balance=credits.catalogue(bank,main,self,native_db=db)
                    result.update(purchasedCredits=balance,purchasedPractice=self.practice.paid_metadata(db,session,config,balance))
                return result
            if method=='GET' and path=='wallet':return wallet.balance(db,session,config)
            if method=='POST' and path=='quote':return wallet.quote(db,session,body,config)
            if method=='POST' and path=='exams':return {'exam':create_exam(db,session,body,config)}
            if method=='POST' and path=='orders':return wallet.create_order(db,session,body)
            if method=='POST' and path in ('mock-confirm','mock-fail'):return wallet.mock_event(db,session,body,confirm=path=='mock-confirm')
            found=re.fullmatch(r'exams/(\d+)(?:/(answers|submit|review|receipt|lesson|asset|scratch|retake))?',path)
            if not found:raise api.APIError('Không có đường thí điểm này.',404)
            eid=int(found[1]);action=found[2];attempt=api.owned_attempt(db,session,eid)
            if action=='retake' and method=='POST':
                from .study_retake import retake
                return retake(db,session,eid,body)
            if action=='scratch':
                from .scratchpads import access
                return access(db,session,eid,method,body,query)
            if method=='GET' and action=='receipt':
                bought=credits.receipt(db,session['student_id'],eid)
                if bought:return {'examId':str(eid),'purchasedCredits':bought,'qaOnly':False}
                return wallet.attempt_receipt(db,session,eid)
            if method=='GET' and action in ('lesson','asset'):
                ck=query.get('contentKey',[''])[0];lesson=self.lesson(db,session,eid,ck)
                if action=='lesson':return {'lesson':lesson,'examId':str(eid),'contentKey':ck}
                sha=query.get('sha',[''])[0]
                if sha not in media_keys(lesson):raise api.APIError('Hình không thuộc bài giảng đã nhận.',404)
                row=db.execute('SELECT mime,payload FROM local_lesson_assets WHERE sha256=?',(sha,)).fetchone()
                if not row:raise api.APIError('Chưa có hình của phiên bản này.',404)
                return {'_local_binary':bytes(row['payload']),'mime':row['mime']}
            if action=='review' and method=='GET':
                if attempt['status']!='submitted':raise api.APIError('Chỉ xem lời giải sau khi nộp.',403)
                from .study_retake import annotate
                return {'exam':annotate(db,session,api.exam_view(db,attempt),'pilot'),'contentKeys':[r[0] for r in db.execute('SELECT c.content_key FROM exam_items i JOIN question_versions v ON v.id=i.question_version_id JOIN pilot_content c ON c.question_id=v.question_id WHERE i.exam_id=? ORDER BY i.position',(eid,))]}
            if method not in ('GET','POST') or (method=='GET' and action) or (method=='POST' and action not in ('answers','submit')):raise api.APIError('Phương thức không hợp lệ.',405)
            if attempt['status']!='submitted' and api.stamp()>=attempt['due_at']:api.submit(db,attempt);attempt=api.owned_attempt(db,session,eid)
            if method=='POST' and action=='answers':
                family=isinstance(main,dict) and 'family_id' in main
                if family and attempt['status']!='submitted':
                    revision=db.execute('SELECT revision FROM family_exam_revisions WHERE attempt_id=?',(attempt['id'],)).fetchone()
                    if type(body.get('revision')) is not int or body['revision']!=(revision[0] if revision else 0):raise api.APIError('Bài làm vừa được lưu trên thiết bị khác. Hãy tải lại và xem đáp án trước khi ghi tiếp.',409)
                if set(body)!=({'position','answer','revision'} if family else {'position','answer'}) or type(body['position']) is not int or not isinstance(body['answer'],str) or len(body['answer'])>500:raise api.APIError('Câu trả lời không hợp lệ.')
                if not db.execute('SELECT 1 FROM exam_items WHERE exam_id=? AND position=?',(eid,body['position'])).fetchone():raise api.APIError('Vị trí câu không hợp lệ.')
                item=db.execute('SELECT options_json FROM exam_items WHERE exam_id=? AND position=?',(eid,body['position'])).fetchone()
                from .practice_catalogue import item_pin
                pin=item_pin(db,eid,body['position'])
                mode=pin['response_mode'] if pin else attempt['response_mode']
                if mode=='choice' and body['answer']!='' and body['answer'] not in json.loads(item[0]):raise api.APIError('Đáp án không thuộc lựa chọn của câu.')
                if attempt['status']!='submitted':
                    db.execute('INSERT INTO exam_draft_answers VALUES (?,?,?,?,?) ON CONFLICT(attempt_id,position) DO UPDATE SET answer=excluded.answer,saved_at=excluded.saved_at',(attempt['id'],eid,body['position'],body['answer'],api.stamp()))
                    if family:db.execute('INSERT INTO family_exam_revisions(attempt_id,revision) VALUES(?,1) ON CONFLICT(attempt_id) DO UPDATE SET revision=revision+1',(attempt['id'],))
            elif method=='POST' and action=='submit':
                if body:raise api.APIError('Nộp bài không nhận đáp án/điểm từ client.')
                api.submit(db,attempt)
            return {'exam':api.exam_view(db,api.owned_attempt(db,session,eid))}
