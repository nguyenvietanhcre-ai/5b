"""Keep row fingerprints on the same DO; return only counts and recovery metadata.

No account rows, credentials, financial payloads or database copies leave the
tenant. New columns are ignored for old-row comparison; every old cell remains
part of its row digest. The audited cutover rejects missing or changed rows.
"""
from collections import Counter
import hashlib,json,re
from backend.platform_api import APIError
from sqlite_storage import Connection
import transfer

TABLE='release_audit_baselines'
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def quote(value):return '"'+value.replace('"','""')+'"'
def rows(database,table,columns):
    expressions=[]
    for column in columns:
        name=quote(column)
        expressions+=['typeof('+name+')',"CASE typeof("+name+") WHEN 'blob' THEN hex("+name+") WHEN 'integer' THEN CAST("+name+" AS TEXT) WHEN 'real' THEN printf('%!.26g',"+name+") ELSE "+name+' END']
    result=[]
    for row in database.storage.sql.exec('SELECT '+','.join(expressions)+' FROM '+quote(table)).raw():
        result.append(hashlib.sha256(canonical(list(row))).hexdigest())
    return result
def snapshot(database):
    tables={}
    for table in transfer.table_names(database):
        if table in (TABLE,'sqlite_sequence'):continue
        columns=[r['name'] for r in database.storage.sql.exec('PRAGMA table_info('+quote(table)+')')]
        tables[table]={'columns':columns,'rows':rows(database,table,columns)}
    return {'tables':tables}
def valid_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{40}',value):raise APIError('Release identity is invalid.',409)
    return value
def get(database,release_id):
    if not list(database.storage.sql.exec("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",TABLE)):return None
    values=list(database.storage.sql.exec('SELECT baseline_json,is_open FROM '+TABLE+' WHERE release_id=?',valid_id(release_id)))
    return values[0] if values else None
def is_open(database,release_id):
    item=get(database,release_id)
    return bool(item and item['is_open'])
def begin(database,release_id):
    release_id=valid_id(release_id)
    old=get(database,release_id)
    if old:return {'status':'already-recorded','releaseId':release_id,'existingTables':len(json.loads(old['baseline_json'])['tables']),'accountRowsDownloaded':False}
    data=snapshot(database);bookmark=transfer.bookmark(database)
    # This write contains digests only. It neither initializes app migrations
    # nor copies a tenant database to another system.
    def persist():
        db=Connection(database)
        db.execute('CREATE TABLE IF NOT EXISTS '+TABLE+'(release_id TEXT PRIMARY KEY,baseline_json TEXT NOT NULL,bookmark TEXT,is_open INTEGER NOT NULL DEFAULT 0 CHECK(is_open IN(0,1)))')
        db.execute('INSERT INTO '+TABLE+'(release_id,baseline_json,bookmark) VALUES(?,?,?)',(release_id,canonical(data).decode(),bookmark))
    database.run(persist)
    return {'status':'recorded','releaseId':release_id,'existingTables':len(data['tables']),'recoveryBookmark':bookmark,'accountRowsDownloaded':False}
def compare(database,release_id):
    item=get(database,release_id)
    if not item:raise APIError('Record the tenant baseline before migration.',409)
    before=json.loads(item['baseline_json']);missing={};additions={}
    for table,metadata in before['tables'].items():
        if not list(database.storage.sql.exec("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",table)):
            missing[table]='table missing';continue
        columns={r['name'] for r in database.storage.sql.exec('PRAGMA table_info('+quote(table)+')')}
        if not set(metadata['columns'])<=columns:missing[table]='old column missing';continue
        old=Counter(metadata['rows']);new=Counter(rows(database,table,metadata['columns']))
        removed=old-new
        if removed:missing[table]=sum(removed.values())
        added=sum((new-old).values())
        if added:additions[table]=added
    violations=list(database.storage.sql.exec('PRAGMA foreign_key_check'))
    return {'status':'passed' if not missing and not violations else 'failed','existingTables':len(before['tables']),'oldRowsAndValuesPreserved':not missing,'unexpectedMissingOrChangedRows':missing,'newRowsInExistingTables':additions,'foreignKeyViolations':len(violations),'accountRowsDownloaded':False,'baselineStoredInTenant':True}
def finalize(database,release_id):
    report=compare(database,release_id)
    if report['status']!='passed':raise APIError('Tenant row audit failed; the release remains closed.',409)
    database.run(lambda:Connection(database).execute('UPDATE '+TABLE+' SET is_open=1 WHERE release_id=?',(valid_id(release_id),)))
    return report
