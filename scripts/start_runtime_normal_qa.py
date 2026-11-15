"""Normal handler/pilot OFF; explicit ten-identity QA fixture, isolated cookie."""
import argparse,json,os
from pathlib import Path
from backend.server import Handler,ThreadingHTTPServer
from backend import platform_api as api
from backend.arena import Arena
from backend.mcq_import import import_package,load_json,require_qa
from scripts.import_mcq_qa import initialize_empty_qa

class TenIdentityArena(Arena):
    """QA-only10 repeated for20rounds; stock bank20minimum guard untouched."""
    def __init__(self,database):super().__init__();self.database=database
    def handle(self,payload,question_provider=None):
        def provider(grade,difficulty,scope):
            with api.connect(self.database) as db:
                require_qa(db);rows=db.execute('SELECT v.* FROM question_versions v JOIN mcq_versions m ON m.version_id=v.id WHERE m.revision=3 ORDER BY m.content_key').fetchall();assert len(rows)==10
                questions=[]
                for row in rows:
                    rule=json.loads(row['grading_rule_json']);questions.append({'id':str(row['id']),'questionVersionId':row['id'],'text':api.blocks_text(json.loads(row['prompt_json'])),'answer':rule['answer'],'gradingRule':rule,'answerKind':rule['answerKind'],'difficulty':0,'steps':[],'sampleLabel':'QA:10identity lap2vong, chua phat hanh'})
                return questions+questions
        return super().handle(payload,provider)

def main():
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--port',type=int,default=18976);a=p.parse_args()
    if os.environ.get('FIVEBMATH_QA_CONTAINER')!='1' or a.port==8765:raise ValueError('Explicit QA container required')
    folder=Path('/app/qa-inputs');path=initialize_empty_qa(a.database,seed_learning=False)
    import_package(path,load_json(folder/'originals/questions-mcq.json'),load_json(folder/'history-sets.json'),load_json(folder/'sources.json'),allow_draft_qa=True)
    import_package(path,load_json(folder/'questions-typed.json'),load_json(folder/'sample-sets-typed.json'),load_json(folder/'sources.json'),allow_draft_qa=True)
    # Only new fake DB versions, original package statuses/production guards unchanged.
    with api.connect(path,True) as db:require_qa(db);db.execute("UPDATE question_versions SET status='published' WHERE id IN (SELECT version_id FROM mcq_versions WHERE revision=3)")
    server=ThreadingHTTPServer(('0.0.0.0',a.port),Handler);server.database_path=path;server.real_accounts=True;server.review_upgrades=False;server.arena=TenIdentityArena(path);server.student_cookie_name=f'5bmath_runtime_qa_{a.port}_session'
    print(json.dumps({'qaOnly':True,'pilot':False,'port':a.port,'database':str(path),'arenaFixture':'10identities repeated twice; production20guard retained'}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
