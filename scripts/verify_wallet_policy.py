"""Run wallet contracts with exact supplied ten-MCQ files, save named evidence."""
import argparse,hashlib,io,json,os,unittest
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--typed',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);os.environ['FIVEBMATH_QA_TYPED_INPUT_DIR' if a.typed else 'FIVEBMATH_QA_INPUT_DIR']=str(a.inputs.resolve())
    stream=io.StringIO();suite=unittest.defaultTestLoader.discover('tests',pattern='test_wallet_typed.py') if a.typed else unittest.TestSuite([unittest.defaultTestLoader.discover('tests',pattern='test_wallet.py'),unittest.defaultTestLoader.discover('tests',pattern='test_wallet_http.py')])
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    from test_wallet import WalletTests
    if a.typed:
        from test_wallet_typed import TypedWalletPolicyTests
        WalletTests=TypedWalletPolicyTests
    report={'status':'PASS' if result.wasSuccessful() and result.testsRun==32 and not result.skipped else 'FAIL','testsRun':result.testsRun,'skipped':len(result.skipped),
        'inputSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.inputs.iterdir() if p.is_file()},'qaOnly':True,'questionCount':10,'evidence':WalletTests.evidence}
    (a.output/'tests.txt').write_text(stream.getvalue(),encoding='utf-8');(a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(stream.getvalue());print(json.dumps({k:v for k,v in report.items() if k!='evidence'},indent=2))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
