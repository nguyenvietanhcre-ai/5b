"""Full suite on merged source, both actual input packages, no skipped suites."""
import argparse,json,os,time,unittest,tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    os.environ['FIVEBMATH_QA_TYPED_INPUT_DIR']=str(a.inputs.resolve());os.environ['FIVEBMATH_QA_INPUT_DIR']=str((a.inputs/'originals').resolve())
    temp=a.output/'runtime-temp';temp.mkdir();tempfile.tempdir=str(temp.resolve());os.environ.update(TMP=str(temp.resolve()),TEMP=str(temp.resolve()),TMPDIR=str(temp.resolve()))
    start=time.monotonic()
    with (a.output/'tests.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
    report={'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL','testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-start,3),'qaOnly':True}
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
