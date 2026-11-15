"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const [base,output,questionsFile,manifestFile]=process.argv.slice(2);
assert(/^http:\/\/127\.0\.0\.1:\d+\/$/.test(base),'Only supplied loopback QA URL');
assert(!base.includes(':8765/'),'Never main port');
fs.mkdirSync(output,{recursive:true});
const packageData=JSON.parse(fs.readFileSync(questionsFile,'utf8').replace(/^\uFEFF/,''));
const manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8').replace(/^\uFEFF/,''));
const byKey=Object.fromEntries(packageData.questions.map(q=>[q.contentKey,q]));
const report={browser:'Playwright + installed Google Chrome headless, emulated viewports',base,viewports:[],pageErrors:[],checks:[],cookieIsolation:{syntheticOnly:true,realServicesContacted:false,mainRequests:0,viewportsPassed:0}};
const sizes=[[390,844],[844,390],[768,1024],[1024,768],[1366,768],[1920,1080]];
let browser;
async function visible(page,id){await page.locator(id).waitFor({state:'visible'});}
async function saved(page){await page.waitForFunction(()=>document.querySelector('#save-status').textContent==='Đã lưu trên máy chủ');}
async function cleanLayout(page,label){const size=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth}));assert(size.scrollWidth<=size.width+1,label+': overflow '+JSON.stringify(size));return size;}
async function shot(page,name){await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});}
async function select(page,id){await page.locator(`[data-profile="${id}"]`).click();await visible(page,'#sets');await page.waitForFunction(id=>document.querySelector(`[data-profile="${id}"]`)?.getAttribute('aria-pressed')==='true',id);}
async function choose(page,keys,position,correct){await page.locator('#question-nav button').nth(position).click();const q=byKey[keys[position]];const idx=q.choices.findIndex(c=>correct?c.id===q.correctChoiceId:c.id!==q.correctChoiceId);await page.locator('input[name=choice]').nth(idx).check();await saved(page);return idx;}
async function finish(page,score){await page.locator('#submit').click();await visible(page,'#submit-dialog');await page.locator('#confirm-submit').click();await visible(page,'#results');await page.waitForFunction(()=>document.querySelectorAll('#review-list>.review-card').length===5);assert.equal(await page.locator('#score').innerText(),score+'/10');}
(async()=>{
try{
 const chrome=process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
 assert(fs.existsSync(chrome),'Installed Chrome required; do not install or download browsers');
 browser=await chromium.launch({headless:true,executablePath:chrome});report.browserVersion=browser.version();
 for(const [w,h] of sizes){
  const label=w+'x'+h, context=await browser.newContext({viewport:{width:w,height:h},deviceScaleFactor:1,hasTouch:w<=1024,isMobile:w<=1024});
  const fakeMainValue='SYNTHETIC-MAIN-COOKIE-PLACEHOLDER';
  await context.addCookies([{name:'5bmath_session',value:fakeMainValue,url:'http://127.0.0.1:8765/',httpOnly:true,sameSite:'Strict'}]);
  // Registering a placeholder cookie does not make an HTTP request. Block any accidental browser request.
  await context.route('http://127.0.0.1:8765/**',route=>{report.cookieIsolation.mainRequests++;return route.abort();});
  const page=await context.newPage();page.setDefaultTimeout(20000);page.on('pageerror',e=>report.pageErrors.push({viewport:label,message:e.message}));
  let submitRequests=0;page.on('request',req=>{if(req.method()==='POST'&&/\/api\/v1\/exams\/\d+\/submit$/.test(req.url()))submitRequests++;});
  const row={width:w,height:h,checks:[],cookieIsolation:[]};report.viewports.push(row);
  const qaCookieName='5bmath_qa_'+new URL(base).port+'_session';
  const qaGuestName='5bmath_qa_'+new URL(base).port+'_bootstrap';
  async function cookieCheck(phase,loggedIn){
    const cookies=await context.cookies('http://127.0.0.1:8765/');
    const main=cookies.find(c=>c.name==='5bmath_session');
    assert(main&&main.value===fakeMainValue,'Main placeholder changed during '+phase);
    assert(main.path==='/'&&main.httpOnly&&main.sameSite==='Strict','Main placeholder attributes changed');
    const qa=cookies.find(c=>c.name===qaCookieName);
    assert(Boolean(qa)===loggedIn,'QA session presence incorrect during '+phase);
    if(qa)assert(qa.httpOnly&&qa.sameSite==='Strict'&&qa.path==='/','QA cookie flags must remain protected');
    assert(cookies.some(c=>c.name===qaGuestName),'QA bootstrap must use its own per-server name');
    row.cookieIsolation.push({phase,mainPlaceholderUnchanged:true,qaSessionPresent:loggedIn});
  }
  await page.goto(base+'?role=VIP&profile=binh',{waitUntil:'networkidle'});
  assert.equal(await page.locator('[data-profile][aria-pressed=true]').count(),0);await cookieCheck('guest-main-only',false);
  await select(page,'an');await cookieCheck('select-free',true);assert(await page.locator('#start-vip').isDisabled());
  await cleanLayout(page,label+'home');await shot(page,label+'-home');row.checks.push('server-profile-not-query');
  await page.locator('#start-free').click();await visible(page,'#quiz');await page.waitForFunction(()=>document.querySelectorAll('input[name=choice]').length===4);
  const freeId=new URL(page.url()).searchParams.get('exam');assert(freeId);
  let response=await context.request.get(base+'api/v1/exams/'+freeId);let pre=await response.json();
  for(const q of pre.exam.questions)for(const key of ['answer','solution','steps','thinking','correctChoiceId','choiceRationales'])assert(!(key in q));
  response=await context.request.get(base+'qa-api/review/'+freeId);assert.equal(response.status(),403);
  row.checks.push('pre-submit-answer-feedback-hidden');
  const firstIdx=await choose(page,manifest.orderedContentKeys,0,true);
  await page.reload({waitUntil:'networkidle'});await visible(page,'#quiz');await page.waitForFunction(()=>document.querySelectorAll('input[name=choice]').length===4);
  assert(await page.locator('input[name=choice]').nth(firstIdx).isChecked());row.checks.push('reload-keeps-server-saved-answer');
  assert.match(await page.locator('#timer').innerText(),/Phiên thử còn (?:2\d|30):\d{2}/);
  if(w===390){
   await page.locator('input[name=choice]').nth(0).focus();await page.keyboard.press('ArrowDown');await saved(page);
   assert(await page.locator('input[name=choice]').nth(1).isChecked());
   const focus=await page.evaluate(()=>({tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle}));assert.equal(focus.tag,'INPUT');assert.notEqual(focus.outline,'none');row.checks.push('keyboard-radio-and-visible-focus');
   await context.setOffline(true);await page.locator('input[name=choice]').nth((firstIdx+1)%4).check();
   await page.waitForFunction(()=>document.querySelector('#save-status').textContent.includes('Chưa lưu được'));
   await shot(page,label+'-offline-retry');await page.locator('#submit').click();await visible(page,'#global-error');assert(!(await page.locator('#submit-dialog').isVisible()));
   await context.setOffline(false);if(await page.locator('#retry-save').isVisible())await page.locator('#retry-save').click();await saved(page);
   await page.locator('input[name=choice]').nth(firstIdx).check();await saved(page);assert(!(await page.locator('#global-error').isVisible()));row.checks.push('offline-keeps-draft-and-retry-saves-before-submit');
  }
  if(w<=1024){const opposite={width:h,height:w};await page.setViewportSize(opposite);await cleanLayout(page,label+'rotated');assert(await page.locator('input[name=choice]').nth(firstIdx).isChecked());await page.setViewportSize({width:w,height:h});row.checks.push('rotation-preserves-choice');}
  await page.locator('#submit').click();await visible(page,'#submit-dialog');assert.match(await page.locator('#submit-message').innerText(),/Còn 4 câu/);await page.locator('#cancel-submit').click();
  for(let p=1;p<4;p++)await choose(page,manifest.orderedContentKeys,p,p%2===0);
  await page.locator('#question-nav button').nth(4).click();await cleanLayout(page,label+'quiz');await shot(page,label+'-quiz');
  await page.locator('#submit').click();await visible(page,'#submit-dialog');assert.match(await page.locator('#submit-message').innerText(),/Còn 1 câu/);
  const beforeSubmit=submitRequests;
  await page.evaluate(()=>{document.querySelector('#confirm-submit').click();document.querySelector('#confirm-submit').click();});
  await visible(page,'#results');await page.waitForFunction(()=>document.querySelectorAll('#review-list>.review-card').length===5);
  assert.equal(await page.locator('#score').innerText(),'4/10');assert.equal(submitRequests-beforeSubmit,1);
  assert.match(await page.locator('.review-card').nth(4).innerText(),/Chưa chọn/);
  await cleanLayout(page,label+'results');await shot(page,label+'-results');
  await page.locator('.review-card').first().locator('.rationale summary').click();assert.equal(await page.locator('.review-card').first().locator('.rationale-item').count(),4);
  await cleanLayout(page,label+'rationales');await shot(page,label+'-rationale');row.checks.push('blank-confirmation-cancel-submit-once-score-rationale');
  await page.reload({waitUntil:'networkidle'});await visible(page,'#results');assert.equal(await page.locator('#score').innerText(),'4/10');row.checks.push('submitted-reload-review');
  await select(page,'binh');await cookieCheck('select-vip',true);assert(!(await page.locator('#start-vip').isDisabled()));await page.locator('#start-vip').click();await visible(page,'#quiz');
  for(let p=0;p<5;p++)await choose(page,manifest.vipSupplementContentKeys,p,true);
  await finish(page,10);row.checks.push('vip-five-correct-server-score10');
  await select(page,'chi');await cookieCheck('select-expired',true);assert(await page.locator('#start-vip').isDisabled());await page.locator('#history button').first().click();await visible(page,'#results');await page.waitForFunction(()=>document.querySelectorAll('#review-list>.review-card').length===5);
  await cleanLayout(page,label+'expired');await shot(page,label+'-expired-review');
  const boot=await (await context.request.get(base+'qa-api/bootstrap')).json();
  response=await context.request.post(base+'api/v1/exams',{data:{requestKey:'expired-ui-'+label,contentKeys:manifest.vipSupplementContentKeys},headers:{Origin:new URL(base).origin,'X-CSRF-Token':boot.csrf}});assert.equal(response.status(),403);
  response=await context.request.get(base+'api/v1/exams/'+freeId);assert.equal(response.status(),404);row.checks.push('expired-vip-review-no-new-vip-owner404');
  const storage=await page.evaluate(async()=>({serviceWorkers:(await navigator.serviceWorker.getRegistrations()).length,caches:(await caches.keys()).length,local:localStorage.length,session:sessionStorage.length}));assert.deepEqual(storage,{serviceWorkers:0,caches:0,local:0,session:0});row.checks.push('no-private-offline-storage');
  const buttons=await page.locator('button:visible').evaluateAll(nodes=>nodes.filter(n=>!n.disabled).map(n=>({w:n.getBoundingClientRect().width,h:n.getBoundingClientRect().height,text:n.textContent.trim()})));
  assert(buttons.every(b=>b.w>=43&&b.h>=43),'Small enabled touch target '+JSON.stringify(buttons.filter(b=>b.w<43||b.h<43)));
  row.checks.push('controls-present-touch-targets-no-horizontal-overflow');
  const logout=await context.request.post(base+'api/v1/auth/logout',{data:{},headers:{Origin:new URL(base).origin,'X-CSRF-Token':boot.csrf}});assert.equal(logout.status(),200);
  await cookieCheck('qa-logout-main-preserved',false);
  const loggedOut=await (await context.request.get(base+'api/v1/session')).json();assert.equal(loggedOut.authenticated,false);
  await page.reload({waitUntil:'networkidle'});assert.equal(await page.locator('[data-profile][aria-pressed=true]').count(),0);await cookieCheck('reload-after-logout',false);
  assert.equal(report.cookieIsolation.mainRequests,0,'No request may target real port8765');
  report.cookieIsolation.viewportsPassed++;row.checks.push('same-context-main-placeholder-kept-and-qa-only-cookie-logout');
  row.status='PASS';await context.close();
 }
 assert.equal(report.pageErrors.length,0,JSON.stringify(report.pageErrors));
 assert.equal(report.cookieIsolation.viewportsPassed,6);report.cookieIsolation.status='PASS';
 report.status='PASS';report.checks.push('all-six-viewports-real-browser','no-page-errors');
}catch(e){report.status='FAIL';report.error=String(e.stack||e);process.exitCode=1;}
finally{if(browser)await browser.close();fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,completedViewports:report.viewports.filter(r=>r.status==='PASS').length,error:report.error||null}));}
})();
