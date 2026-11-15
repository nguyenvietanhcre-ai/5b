"""Operator CLI: preview is read-only; commit requires an isolated marked QA DB."""
import argparse
from pathlib import Path
import json
import sqlite3
from backend import platform_api as api
from backend.database import initialize,execute_sql
from backend.free_vip_pilot import SCHEMA
from backend.mcq_import import ImportFailure,load_json,import_package,validate
from backend.mcq_preview import preview_package


def initialize_empty_qa(path,*,seed_learning=True):
    path=Path(path).resolve()
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb'): pass
    initialize(path)
    (api.seed_catalog if seed_learning else api.initialize_catalog)(path)
    with api.connect(path,True) as db: execute_sql(db,SCHEMA)
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('database','questions','manifest','sources','report'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--new-database',action='store_true')
    p.add_argument('--preview','--dry-run',action='store_true')
    p.add_argument('--allow-draft-qa',action='store_true')
    a=p.parse_args()
    if a.preview and a.new_database:p.error('preview never creates a database; omit --new-database')
    if not a.report.parent.is_dir():p.error('report parent directory must already exist')
    if a.report.exists() or a.report.resolve() in {f.resolve() for f in (a.database,a.questions,a.manifest,a.sources)}:
        p.error('report must be a new file distinct from database and inputs')
    try:
        package,manifest,sources=map(load_json,(a.questions,a.manifest,a.sources))
        if a.preview:
            result=preview_package(a.database,package,manifest,sources,allow_draft_qa=a.allow_draft_qa)
        else:
            validate(package,manifest,sources,allow_draft_qa=a.allow_draft_qa)
            if a.new_database:initialize_empty_qa(a.database)
            result=import_package(a.database,package,manifest,sources,allow_draft_qa=a.allow_draft_qa)
            result['status']='PASS'
    except (ImportFailure,ValueError,TypeError,AttributeError,KeyError,OSError,sqlite3.Error) as exc:
        result={'status':'REJECTED','qaOnly':True,'mode':'preview' if a.preview else 'import','error':str(exc)}
    with a.report.open('x',encoding='utf-8') as report:json.dump(result,report,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get('status')=='REJECTED' or result.get('importable') is False:raise SystemExit(2)


if __name__=='__main__':main()
