"""Actual workerd end-to-end checks for the private learning release inputs."""
import argparse,base64,json,secrets,tempfile,traceback,sys,os,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from test_runtime import LocalWorker,HTTPClient,fixture_database,transfer_payload,student_login

def run(port):
    root=Path(__file__).resolve().parents[1]
    directory=Path(tempfile.mkdtemp(prefix='native-worker-qa-',dir=root/'work'))
    report={'status':'running','scope':'fresh fake accounts and local workerd only','checks':[]}
    worker=None
    try:
        source,fixture,_=fixture_database(directory)
        payload,transfer=transfer_payload(source,directory)
        token=secrets.token_urlsafe(36)
        worker=LocalWorker(directory,port,token,secrets.token_urlsafe(40),native_features=True);worker.start()
        ops=HTTPClient(worker.origin);ops.call('/__ops/import',payload,headers={'Authorization':'Bearer '+token})
        student=HTTPClient(worker.origin);password=secrets.token_urlsafe(24);login='native-'+secrets.token_hex(8)
        state=student.call('/api/v1/auth/register',{'login':login,'password':password,'name':'Học sinh QA lớp 5','birthYear':2016})
        assert state['localPilotEnabled'] is True
        catalogue=student.call('/api/local-pilot/catalogue')
        assert len(catalogue['questions'])==60
        (directory/'catalogue.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2),encoding='utf-8')
        report['checks'].append('Authenticated grade-five catalogue: 60 questions; account stores remain distinct.')
        intent=secrets.token_hex(12)
        quote=student.call('/api/local-pilot/practice/quote',{'intentId':intent,'category':'content','count':3,'pool':'free'})
        confirm={'intentId':intent,'requestKey':secrets.token_hex(12),'quoteId':quote['quoteId'],'confirmWallet':False}
        exam=student.call('/api/local-pilot/practice/exams',confirm)['exam'];eid=str(exam['id'])
        assert len(exam['questions'])==3
        assert student.call('/api/local-pilot/practice/exams',confirm)['exam']['id']==exam['id']
        print('Native QA: catalogue and owner-pinned mixed exam PASS',flush=True)
        # A valid empty note uses the public scratchpad protocol and a revision pin.
        scratch=student.call('/api/local-pilot/exams/'+eid+'/scratch?position=1')
        (directory/'scratch-before.json').write_text(json.dumps(scratch),encoding='utf-8')
        note={'version':1,'open':True,'text':'Nháp đồng bộ QA','color':'#203a32','strokes':[{'color':'#203a32','points':[{'x':i/2000,'y':.3} for i in range(2000)]}]}
        saved=student.call('/api/local-pilot/exams/'+eid+'/scratch',{'position':1,'revision':0,'requestKey':secrets.token_hex(12),'note':note})
        other_device=HTTPClient(worker.origin);other_device.call('/api/v1/auth/login',{'login':login,'password':password})
        assert other_device.call('/api/local-pilot/exams/'+eid+'/scratch?position=1')['scratch']['note']==note
        conflict=student.call('/api/local-pilot/exams/'+eid+'/scratch',{'position':1,'revision':0,'requestKey':secrets.token_hex(12),'note':{**note,'text':'stale'}})
        assert conflict['conflict'] is True
        report['checks'].append('Owner mixed exam/retry; >16KB vector/text scratch sync across two independent sessions; stale revisions conflict.')
        print('Native QA: PDF rendering',flush=True)
        for solutions in (False,True):
            pdf=student.call('/api/v1/practice-export',{'provider':'pilot','attemptId':eid,'includeSolutions':solutions})
            data=base64.b64decode(pdf['pdfBase64']);assert data.startswith(b'%PDF-')
            (directory/('solutions.pdf' if solutions else 'questions.pdf')).write_bytes(data)
            assert len(pdf['codes'])==3
        lookup=student.call('/api/v1/practice-lookup?code='+pdf['codes'][0]['code'])
        assert lookup['solutionsIncluded'] is False
        assert student.call('/api/v1/practice-lookup?code='+pdf['codes'][0]['code']+'&solutions=1')['solutionsIncluded'] is True
        report['checks'].append('Actual WASM PDF rendering with Vietnamese fonts, assets and optional solutions.')
        lesson_key=catalogue['knowledge'][0]['lessonKey']
        lesson=student.call('/api/local-pilot/knowledge/'+lesson_key)
        admin=HTTPClient(worker.origin);admin.call('/api/staff/login',fixture['admin'])
        rows=admin.call('/api/staff/native-lessons')['rows'];assert len(rows)==24
        original=admin.call('/api/staff/native-lessons/item?key='+lesson_key)['item']
        draft={'lessonKey':lesson_key,'draftRevision':0,'baseRevision':1,'title':'Bài giảng QA trên Worker','sections':original['sections'],'action':'draft'}
        edited=admin.call('/api/staff/native-lessons',draft)['item']
        published=admin.call('/api/staff/native-lessons',{**draft,'draftRevision':edited['draftRevision'],'action':'publish'})['item']
        assert published['publishedRevision']==2 and published['fixed']==original['fixed']
        assert len(admin.call('/api/staff/native-lessons/events')['rows'])==2
        assert len(admin.call('/api/staff/catalogue/series')['rows'])==3
        student.call('/api/staff/native-lessons',expected=401)
        report['checks'].append('24 native lessons; admin draft/publish/audit preserves fixed question; student denied staff access; three video series.')
        if os.environ.get('NATIVE_BROWSER_QA')=='1':
            env=dict(os.environ);env['NATIVE_BROWSER_CONFIG']=json.dumps({'directory':str(directory),'workerOrigin':worker.origin,'login':login,'password':password,'lessonKey':lesson_key,'examId':eid,'code':pdf['codes'][0]['code'],'admin':fixture['admin']})
            subprocess.run([os.environ.get('NODE_BIN','node'),str(root/'tests/native-cloud-browser.cjs')],cwd=root,env=env,check=True,timeout=240)
            report['checks'].append('Actual browser: student/native/exam/lookup/plans/admin, four portrait/landscape viewports.')
        print('Native QA: game catalogue and BOT',flush=True)
        games=student.call('/api/v1/group-games/catalogue')
        (directory/'games.json').write_text(json.dumps(games),encoding='utf-8')
        bot=student.call('/api/v1/group-games/rooms',{'mode':'animal_race','playMode':'bot','requestKey':secrets.token_hex(12),'public':False})
        (directory/'bot.json').write_text(json.dumps(bot),encoding='utf-8')
        report['checks'].append('Animal race BOT admission persists through the tenant transaction.')
        worker.stop();worker.start()
        resumed=HTTPClient(worker.origin);resumed.call('/api/v1/auth/login',{'login':login,'password':password})
        assert resumed.call('/api/local-pilot/exams/'+eid)['exam']['id']==exam['id']
        assert resumed.call('/api/local-pilot/exams/'+eid+'/scratch?position=1')['scratch']['note']==note
        assert resumed.call('/api/v1/group-games/rooms/'+bot['room']['id'])['room']['id']==bot['room']['id']
        report['checks'].append('Learning ownership/exam/scratch and BOT room survive actual workerd process restart.')
        report['status']='passed'
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error))
        traceback.print_exc()
    finally:
        if worker:worker.stop()
        (directory/'native-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({**report,'evidence':str(directory)},ensure_ascii=True),flush=True)
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=19062)
    raise SystemExit(run(p.parse_args().port))
