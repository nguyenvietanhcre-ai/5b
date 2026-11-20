"""Bounded provider IO outside SQL transactions; no credential in source/logs."""
import hashlib,json
from pathlib import Path
from backend.platform_api import APIError
from sqlite_storage import REQUEST_SCOPE, NeedsExternal

def website_request(handler,method,path,body=None):
    if method=='GET' and path=='/api/website/legal':
        from backend.website_legal import public_info
        from backend.platform_api import connect
        with connect(handler.server.database_path) as db:return public_info(db),200
    from backend.website_support import dispatch
    return dispatch(handler,method,path,body)

def bunny_lifecycle(event,identity):
    scope=REQUEST_SCOPE.get()
    if scope is None:raise APIError('Video provider requires a request scope.',503)
    if event=='check' and ('bunny-rejected',) in scope.crypto:raise scope.crypto['bunny-rejected',]
    if event=='reserved':scope.crypto['bunny-new',identity]=True
    if event=='reserved_here':return scope.crypto.get(('bunny-new',identity),False)
    if event=='rejected':
        from backend.bunny_stream import upstream_error
        scope.crypto['bunny-rejected',]=upstream_error()

def bunny_transport(method,path,api_key,payload):
    scope=REQUEST_SCOPE.get()
    if scope is None:raise APIError('Video provider requires a request scope.',503)
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':'))
    key=('bunny-provider',method,path,hashlib.sha256(api_key.encode()).hexdigest(),encoded)
    if key in scope.crypto:
        ok,value=scope.crypto[key]
        if not ok:raise value
        return value
    def perform():
        try:return True,provider_fetch(method,path,api_key,payload)
        except Exception as error:return False,error
    raise NeedsExternal(key,perform)

def provider_fetch(method,path,api_key,payload):
    from js import fetch,Request,Object,AbortSignal
    from pyodide.ffi import run_sync,to_js
    from backend.bunny_stream import MAX_UPSTREAM_BYTES, _ProviderRejection, upstream_error
    if method not in ('GET','POST') or not path.startswith('/library/') or any(c in path for c in ('\r','\n','#','\\')):raise upstream_error()
    # Workers supports manual/follow; manual never forwards provider credentials
    # to a redirect target. Non-200 (including redirects) is rejected below.
    options={'method':method,'redirect':'manual','headers':{'AccessKey':api_key,'Accept':'application/json'},'signal':AbortSignal.timeout(5000)}
    if payload is not None:
        options['body']=json.dumps(payload);options['headers']['Content-Type']='application/json'
    response=run_sync(fetch(Request.new('https://video.bunnycdn.com'+path,to_js(options,dict_converter=Object.fromEntries))))
    if method=='POST' and response.status in (400,401,403,404):raise _ProviderRejection()
    if response.status!=200:raise upstream_error()
    reader=response.body.getReader();data=bytearray()
    while True:
        part=run_sync(reader.read())
        if part.done:break
        data.extend(part.value.to_bytes())
        if len(data)>MAX_UPSTREAM_BYTES:
            run_sync(reader.cancel());raise upstream_error()
    return json.loads(data)

def install_release(database,learning,body):
    """Operator-only additive samples; no user/account import or data reset."""
    from backend.curriculum_samples import loaded_package,validate_package,install,BATCH
    from backend import platform_api as api
    package=loaded_package()
    if not package or not learning:raise APIError('Private release sources are not configured.',503)
    digest=validate_package(package)
    source=Path(__file__).with_name('release-content.json')
    extras=json.loads(source.read_text(encoding='utf-8')) if source.exists() else None
    expected={'packageHash':digest,'batchId':BATCH}
    if extras:expected['learningHash']=hashlib.sha256(source.read_bytes()).hexdigest()
    if not isinstance(body,dict):raise APIError('Release identity mismatch.',409)
    segment=body.get('segment')
    identity={k:v for k,v in body.items() if k!='segment'}
    if identity!=expected:raise APIError('Release identity mismatch.',409)
    if segment is not None:
        if not isinstance(segment,dict) or set(segment)!={'store','offset'} or segment['store'] not in ('main','native','lessons') or type(segment['offset']) is not int:raise APIError('Invalid release segment.',409)
        store,offset=segment['store'],segment['offset']
        if store=='lessons':
            if offset!=0:raise APIError('Invalid release segment.',409)
            def finish_lessons():
                for path,count in ((database,1500),(learning.path,2475)):
                    with api.connect(path) as db:
                        actual=db.execute('SELECT count(*) FROM curriculum_sample_versions WHERE batch_id=?',(BATCH,)).fetchone()[0]
                        if actual!=count:raise APIError('Complete every source segment before importing lessons.',409)
                lessons=install_lessons(database,learning,extras) if extras else {}
                record_complete(database,digest,expected.get('learningHash',''))
                return {'status':'passed','segment':segment,'lessons':lessons,'accountDataImported':False}
            return database.run(finish_lessons)
        eligible=[q for q in package['questions'] if store=='native' or q['access']=='free']
        if offset<0 or offset>=len(eligible) or offset%250:raise APIError('Invalid release segment.',409)
        selected=frozenset(q['id'] for q in eligible[offset:offset+250])
        def apply_segment():
            with api.connect(learning.path if store=='native' else database,True) as db:
                result=install(db,package,pilot=store=='native',question_keys=selected)
            return {'status':'passed','segment':segment,'result':result,'selected':len(selected),'accountDataImported':False}
        return database.run(apply_segment)
    def apply():
        with api.connect(database,True) as main:main_result=install(main,package,pilot=False)
        with api.connect(learning.path,True) as native:native_result=install(native,package,pilot=True)
        extra_result=install_lessons(database,learning,extras) if extras else {}
        record_complete(database,digest,expected.get('learningHash',''))
        return {'status':'passed','packageHash':digest,'main':main_result,'native':native_result,'lessons':extra_result,'accountDataImported':False}
    return database.run(apply)

def record_complete(database,package_hash,learning_hash):
    from sqlite_storage import Connection
    db=Connection(database)
    db.execute('CREATE TABLE IF NOT EXISTS release_source_installations(package_hash TEXT NOT NULL,learning_hash TEXT NOT NULL,PRIMARY KEY(package_hash,learning_hash))')
    db.execute('INSERT OR IGNORE INTO release_source_installations VALUES(?,?)',(package_hash,learning_hash))

def require_complete(database):
    from backend.curriculum_samples import loaded_package,digest
    from sqlite_storage import Connection
    source=Path(__file__).with_name('release-content.json')
    package=loaded_package()
    learning_hash=hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else ''
    with database.connect() as db:
        present=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='release_source_installations'").fetchone()
        if not present or not package or not db.execute('SELECT 1 FROM release_source_installations WHERE package_hash=? AND learning_hash=?',(digest(package),learning_hash)).fetchone():
            raise APIError('Complete the sealed source installation before opening the release.',409)

def install_lessons(database,learning,source):
    from base64 import b64decode
    from backend import platform_api as api
    allowed={'native':{'knowledge_lessons','knowledge_assets','lesson_material_files','lesson_material_bindings'},'main':{'bunny_stream_uploads','lesson_material_files','lesson_material_bindings'}}
    if source.get('format')!='5bmath-release-learning' or source.get('version')!=1 or source.get('containsAccounts') is not False or source.get('containsSessions') is not False:raise APIError('Unsafe lesson release source.',409)
    report={}
    for kind,path in (('main',database),('native',learning.path)):
        if set(source[kind])!=allowed[kind]:raise APIError('Unexpected lesson source table.',409)
        report[kind]={}
        with api.connect(path,True) as db:
            for table,rows in source[kind].items():
                if not rows:report[kind][table]=0;continue
                columns=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
                pk=[r[1] for r in sorted(db.execute('PRAGMA table_info('+table+')'),key=lambda r:r[5]) if r[5]]
                if not pk:raise APIError('Lesson source identity missing.',409)
                added=0
                for original in rows:
                    row={k:b64decode(v['base64'],validate=True) if isinstance(v,dict) and set(v)=={'base64'} else v for k,v in original.items()}
                    if set(row)!=set(columns):raise APIError('Lesson source schema changed.',409)
                    if table=='bunny_stream_uploads':
                        admin=db.execute("SELECT id FROM staff_users WHERE role='admin' AND status='active' ORDER BY id LIMIT 1").fetchone()
                        if not admin:raise APIError('An existing active administrator is required.',409)
                        row['staff_id']=admin[0]
                    old=db.execute('SELECT * FROM '+table+' WHERE '+' AND '.join(k+'=?' for k in pk),tuple(row[k] for k in pk)).fetchone()
                    if old:
                        def same(k):
                            a,b=old[k],row[k]
                            return json.loads(a)==json.loads(b) if k.endswith('_json') else a==b
                        compare_columns=columns
                        if table=='bunny_stream_uploads':
                            # Preserve fresher provider state and target ownership.
                            compare_columns=[k for k in columns if k not in ('staff_id','state','duration_seconds','storage_bytes','updated_at')]
                        if not all(same(k) for k in compare_columns):raise APIError('Existing immutable lesson source conflicts with this release.',409)
                        continue
                    db.execute('INSERT INTO '+table+'('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(row[k] for k in columns));added+=1
                report[kind][table]=added
    return report
