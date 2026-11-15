"""Operator entrypoint: marked QA database, explicit batch opt-in, preview default."""
import argparse,json
from pathlib import Path
from backend.mcq_import import load_json
from backend.content_batch_qa import preview_batch,import_batch

def main():
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--questions',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--allow-batch-qa',action='store_true');p.add_argument('--allow-draft-qa',action='store_true');p.add_argument('--apply',action='store_true');a=p.parse_args()
    method=import_batch if a.apply else preview_batch
    result=method(a.database,load_json(a.questions),load_json(a.manifest),load_json(a.sources),allow_batch_qa=a.allow_batch_qa,allow_draft_qa=a.allow_draft_qa)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
