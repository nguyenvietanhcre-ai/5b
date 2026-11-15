"""Run round4 contracts with the supplied existing ten-question QA package."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    files=[a.inputs/f for f in ('questions-mcq.json','sample-sets.json','sources.json')]
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    os.environ['FIVEBMATH_QA_INPUT_DIR']=str(a.inputs.resolve())
    stream=io.StringIO();suite=unittest.defaultTestLoader.discover('tests',pattern='test_import_access.py')
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    from test_import_access import ImportAccessTests
    report={'status':'PASS' if result.wasSuccessful() and result.testsRun==16 and not result.skipped else 'FAIL',
        'testsRun':result.testsRun,'sourceFileSHA256':hashes,'qaOnly':True,'questionCount':10,
        'evidence':ImportAccessTests.evidence,'skipped':len(result.skipped)}
    (a.output/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(stream.getvalue());print(json.dumps({k:v for k,v in report.items() if k!='evidence'},indent=2))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
