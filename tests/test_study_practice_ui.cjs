'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(path.resolve(__dirname,'../../../battle-loading-release-20261113/src/node_modules/playwright'));
const front=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/practice-ui');fs.mkdirSync(out,{recursive:true});
const sketch=fs.readFileSync(path.join(front,'practice-scratchpad.js'),'utf8');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const checks=[],errors=[];
try{
 async function setup(view,submitted=false,routeName='testing'){
  const page=await browser.newPage({viewport:view});page.on('pageerror',err=>errors.push(err.message));const requests=[];let revision=0;
  const exam={id:'1',grade:5,title:'Đề đã sở hữu',responseMode:'mixed',answers:{},revision:0,expiresAt:Date.now()+1800000,questions:[{id:'1',text:'Tính 1 + 1.',responseMode:'typed',answerKind:'number',inputGuide:{instruction:'Nhập một đáp số.',labels:[],units:[]}},{id:'2',text:'Chọn phương án đầy đủ.',responseMode:'choice',options:Array.from({length:4},(_,i)=>'Phương án '+(i+1)+' '+('nội dung khá dài '.repeat(35)))}]};
  if(submitted){Object.assign(exam,{submittedAt:new Date().toISOString(),score:5,correct:1,answers:{'1':'2','2':'sai'}});exam.questions.forEach((q,i)=>Object.assign(q,{correct:i===0,questionCode:'5B-P-AAAA-BBBB-CCC'+i,answer:'2',steps:['Đáp số: 2','<script>window.UNSAFE=1</script>'],solution:[{type:'text',text:'Đáp số: 2'},{type:'text',text:'<script>window.UNSAFE=1</script>'}]}));}
  await page.route('**/*',async handler=>{const req=handler.request(),u=new URL(req.url());if(u.hostname!=='127.0.0.1')return handler.abort();
   if(u.pathname.startsWith('/api/local-pilot/')){const endpoint=u.pathname.replace('/api/local-pilot/','');requests.push({endpoint,method:req.method(),body:req.postDataJSON(),context:req.headers()['x-family-context']});let data;
    if(endpoint.endsWith('/scratch'))data={scratch:{revision:0,note:null}};
    else if(endpoint.endsWith('/answers')){exam.answers[String(req.postDataJSON().position)]=req.postDataJSON().answer;exam.revision=++revision;data={exam};}
    else if(endpoint.endsWith('/retake'))data={exam:{...exam,id:'3',submittedAt:null}};
    else if(endpoint.endsWith('/review'))data={exam,contentKeys:['owned-a','owned-b']};
    else data={exam};return handler.fulfill({contentType:'application/json',body:JSON.stringify(data)});
   }
   if(u.pathname.endsWith('.css'))return handler.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(front,path.basename(u.pathname)))});
   return handler.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/learning.css"><link rel="stylesheet" href="/local-pilot.css"><link rel="stylesheet" href="/solution-view.css"><link rel="stylesheet" href="/solution-format.css"></head><body class="learning-mode"><main style="padding:16px;max-width:1200px;margin:auto"><section id="local-pilot" class="local-pilot"></section></main></body></html>'});
  });
  await page.goto('http://127.0.0.1:19201/'+(submitted?'ket-qua-thi':'lam-de')+'/?pilotExam=1');
  await page.evaluate(()=>window.PlatformAPI={snapshot:{account:{id:10},csrf:'qa-csrf',state:{grade:5},localPilotEnabled:true},familyContext:'context-current',invalidateFamily(){window.INVALIDATED=true;}});
  await page.addScriptTag({content:fs.readFileSync(path.join(front,'ui-controls.js'),'utf8')});await page.addScriptTag({content:fs.readFileSync(path.join(front,'solution-view.js'),'utf8')});await page.addScriptTag({content:fs.readFileSync(path.join(front,'solution-format.js'),'utf8')});await page.addScriptTag({content:fs.readFileSync(path.join(front,'question-frame.js'),'utf8')});await page.addScriptTag({content:sketch});await page.addScriptTag({content:fs.readFileSync(path.join(front,'local-pilot.js'),'utf8')});
  if(routeName)await page.evaluate(name=>LocalPilot.mount(name),routeName);
  return {page,requests};
 }
 for(const view of [{width:390,height:844},{width:844,height:390},{width:768,height:1024},{width:1440,height:900}]){
  const {page}=await setup(view);await page.locator('#pilot-timer').waitFor();
  assert(await page.locator('.study-question-heading #pilot-timer').count());
  assert(await page.locator('.study-question-nav').evaluate(el=>Boolean(el.compareDocumentPosition(document.querySelector('.practice-scratch'))&Node.DOCUMENT_POSITION_FOLLOWING)));
  await page.getByRole('button',{name:'Nháp',exact:true}).click();await page.waitForTimeout(80);
  assert(await page.locator('.scratch-panel').evaluate(el=>el.firstElementChild.tagName==='CANVAS'));
  await page.locator('#pilot-typed-answer').fill('2');await page.waitForTimeout(80);await page.getByRole('button',{name:'Câu tiếp',exact:true}).click();await page.waitForTimeout(80);
  assert(await page.locator('.study-stick-question').count());assert(!(await page.locator('.study-stick-all').count()));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,`mcq-${view.width}x${view.height}.png`),fullPage:false});
  checks.push({view,questionTimer:true,navBeforeScratch:true,canvasFirst:true,longMCQQuestionOnly:true,noOverflow:true});await page.close();
 }
 const {page,requests}=await setup({width:390,height:844},true,'results');
 assert.equal(await page.locator('.pilot-review').count(),2);assert.equal(await page.getByRole('link',{name:/Đọc bài giảng/}).count(),0);
 assert.equal(await page.locator('details[open]').count(),0);await page.getByText('Xem lời giải',{exact:true}).first().click();assert.equal(await page.locator('details[open]').count(),1);
 assert.equal(await page.locator('.pilot-review').first().locator('.study-solution-steps>li').count(),2);assert.equal(await page.evaluate(()=>window.UNSAFE),undefined);await page.screenshot({path:path.join(out,'review-open-390x844.png'),fullPage:true});await page.locator('#study-wrong-only').check();assert.equal(await page.locator('.pilot-review:not([hidden])').count(),1);
 await page.getByRole('button',{name:'Làm lại đề này',exact:true}).click();await page.waitForURL('**/lam-de/?pilotExam=3');assert(requests.some(r=>r.endpoint==='exams/1/retake'&&r.body.requestKey));assert(!requests.some(r=>r.endpoint==='quote'||r.endpoint==='practice/quote'));
 checks.push({resultsWrongOnly:true,collapsedSafeSolution:true,directExactRetake:true,noAllocationPopup:true});await page.close();
 const standalone=await setup({width:390,height:844},false,null);await standalone.page.evaluate(()=>LocalPilot.retakeOwned('1'));await standalone.page.waitForURL('**/lam-de/?pilotExam=3');assert.equal(standalone.requests[0].context,'context-current');checks.push({retakeFromPersonalWithoutMount:true});await standalone.page.close();
 const stale=await setup({width:390,height:844},false,null);const rejected=await stale.page.evaluate(async()=>{const pending=LocalPilot.retakeOwned('1').then(()=> 'unexpected').catch(error=>error.name);PlatformAPI.familyContext='switched-child';return pending;});assert.equal(rejected,'AbortError');assert(stale.page.url().endsWith('pilotExam=1'));checks.push({lateRetakeAfterProfileSwitchIgnored:true});await stale.page.close();
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify({status:'PASS',checks,errors,network:'intercepted fixture; not live API'},null,2));console.log(JSON.stringify({status:'PASS',checks:checks.length,errors}));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
