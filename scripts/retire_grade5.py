"""Explicit scope-A dry-run/apply/rollback; never invoked on startup."""
import argparse,json,sqlite3
from pathlib import Path
from contextlib import closing
from backend import platform_api as api
from backend.content_retirement import manifest,activate

def main():
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--manifest',type=Path);g=p.add_mutually_exclusive_group();g.add_argument('--apply',action='store_true');g.add_argument('--rollback',action='store_true');p.add_argument('--approved-scope-A',action='store_true');a=p.parse_args()
    target=a.database.resolve()
    if not target.is_file():raise ValueError('Existing database only; this tool never initializes/copies a database')
    if not a.apply and not a.rollback:
        with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');result=manifest(db)
        if not a.output:raise ValueError('--output required for reviewed dry-run manifest')
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'dryRun':True,'scope':result['scope'],'counts':{k:len(result[k]) for k in ('topics','lessons','questions','publishedVersions')}}));return
    if not a.approved_scope_A or not a.manifest:raise ValueError('Explicit --approved-scope-A and reviewed --manifest required')
    expected=json.loads(a.manifest.read_text(encoding='utf-8-sig'))
    with api.connect(target,True) as db:
        if manifest(db)!=expected:raise ValueError('Live catalogue differs from approved manifest; no writes applied')
        activate(db,expected,enabled=not a.rollback)
    print(json.dumps({'applied':a.apply,'rolledBack':a.rollback,'scope':'grade5-only','deletedRows':0,'changedOriginalContentRows':0}))
if __name__=='__main__':main()
