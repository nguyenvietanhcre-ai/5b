'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');const {chromium}=require('playwright');
const [base,output,database,python,width,height]=process.argv.slice(2),w=Number(width),h=Number(height);
assert(/^http:\/\/127\.0\.0\.1:\d+\/$/.test(base)&&!base.includes(':8765/'));
const report={status:'RUNNING',width:w,height:h,checks:[],cookieChecks:[],mainRequests:0,websiteRequests:0,pageErrors:[],syntheticOnly:true,selectors:[],commitFingerprints:[]};
let browser,context,page;const quotes=[],commits=[];const fakeMain='SYNTHETIC-MAIN-COOKIE-PLACEHOLDER';
const fingerprint=body=>crypto.createHash('sha256').update(JSON.stringify(body)).digest('hex');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<200;i++){if(await fn())return;await sleep(50);}throw Error('Expected confirmation event did not arrive');}
async function visible(id){await page.locator(id).waitFor({state:'visible'});}
async function ready(){await page.waitForFunction(()=>!document.querySelector('#confirm-allocation').disabled&&!document.querySelector('#buy-pack').disabled);}
async function shot(name){await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});}
async function layout(name){const a=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert(a.scroll<=a.width+1);report.checks.push(name);}
async function cookie(phase,expected){const cs=await context.cookies(),main=cs.find(c=>c.name==='5bmath_session'),qa=cs.find(c=>c.name===`5bmath_qa_${new URL(base).port}_session`);assert(main&&main.value===fakeMain&&main.httpOnly&&main.sameSite==='Strict'&&main.path==='/');assert.equal(!!qa,expected);report.cookieChecks.push({phase,mainUnchanged:true,qaSessionPresent:!!qa});}
async function call(route,body){return page.evaluate(async({route,body})=>{const boot=await(await fetch('/qa-api/bootstrap',{cache:'no-store'})).json();const r=await fetch(route,{cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':boot.csrf},body:JSON.stringify(body)})});return{status:r.status,data:await r.json()};},{route,body});}
async function state(){const r=await call('/qa-api/wallet');assert.equal(r.status,200);return r.data;}
async function select(profile){await page.locator(`[data-profile="${profile}"]`).click();await page.waitForFunction(profile=>document.querySelector(`[data-profile="${profile}"]`).getAttribute('aria-pressed')==='true',profile);await ready();}
async function counts(){const boot=await call('/qa-api/bootstrap'),s=await state();return{attempts:boot.data.history.length,private:s.privateRemaining,vip:s.vip.dayUsed,orders:s.orders.length};}
async function buy(){await page.locator('#buy-pack').click();await visible('[data-mock="mock-confirm"]');await ready();await page.locator('[data-mock="mock-confirm"]').click();await until(async()=> (await state()).privateRemaining===100);await ready();}
function control(action,id){execFileSync('docker',['exec',process.env.QA_CONTAINER,'python','-m','scripts.verify_typed_wallet_confirm_qa','--control',action,'--database',database,'--quote-id',id],{encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}});}
async function quote(selector){const n=quotes.length;await page.evaluate(s=>requestAllocation(s),selector);await visible('#allocation-dialog');await ready();await until(()=>quotes.length>n);assert.deepEqual(quotes.at(-1).selector,selector);return quotes.at(-1);}
async function reconfirm(old){const n=quotes.length;await page.locator('#confirm-allocation').click();await until(()=>quotes.length>n);await ready();const fresh=quotes.at(-1);assert.deepEqual(fresh.selector,old.selector);await visible('#allocation-dialog');return fresh;}
async function cancel(){await page.locator('#cancel-allocation').click();await page.locator('#allocation-dialog').waitFor({state:'hidden'});}
async function commit(){await ready();await page.locator('#confirm-allocation').click();await visible('#quiz');await ready();return new URL(page.url()).searchParams.get('exam');}
async function receipt(id){const r=await call('/qa-api/wallet/receipts/'+id);assert.equal(r.status,200);return r.data.allocation;}
(async()=>{try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'});report.browserVersion=browser.version();
 context=await browser.newContext({viewport:{width:w,height:h},isMobile:w<=1024,hasTouch:w<=1024,deviceScaleFactor:1});
 await context.addCookies([{name:'5bmath_session',value:fakeMain,url:'http://127.0.0.1:8765/',httpOnly:true,sameSite:'Strict'}]);
 await context.route('**/*',async route=>{if(['5bmath.vn','www.5bmath.vn'].includes(new URL(route.request().url()).hostname)){report.websiteRequests++;await route.abort();}else if(new URL(route.request().url()).port==='8765'){report.mainRequests++;await route.abort();}else await route.continue();});
 page=await context.newPage();page.on('pageerror',e=>report.pageErrors.push(e.message));
 page.on('response',async response=>{if(new URL(response.url()).pathname==='/qa-api/wallet/quote'&&response.status()===200){const value=await response.json();const selector=response.request().postDataJSON();quotes.push({selector,id:value.quoteId,private:value.private,vip:value.vip,free:value.free,retained:value.retained});report.selectors.push(selector);}});
 page.on('request',request=>{if(request.method()==='POST'&&new URL(request.url()).pathname==='/api/v1/exams'){const body=request.postDataJSON();commits.push(body);report.commitFingerprints.push(fingerprint(body));}});
 await page.goto(base);await visible('[data-profile="an"]');await cookie('guest',false);
 await select('an');await cookie('free',true);await buy();const freeBefore=await counts();assert.equal(freeBefore.private,100);
 // Use the actual Free button for the reported P2.
 let n=quotes.length;await page.locator('#start-free').click();await visible('#allocation-dialog');await ready();await until(()=>quotes.length>n);let q=quotes.at(-1);assert.deepEqual(q.selector,{setIndex:1});control('expire',q.id);
 let next=await reconfirm(q);assert.deepEqual([next.free+next.retained,next.vip,next.private],[5,0,0]);assert.deepEqual(await counts(),freeBefore);await shot('free-expired-keeps-free-zero-private');await cancel();assert.deepEqual(await counts(),freeBefore);
 q=await quote({setIndex:1});control('expire',q.id);next=await reconfirm(q);const freeId=await commit();let r=await receipt(freeId);assert.deepEqual([r.free+r.retained,r.vip,r.private],[5,0,0]);assert.equal((await state()).privateRemaining,100);await layout('Free expiry reconfirm/cancel/confirm remains Free0');
 await select('binh');await cookie('vip',true);const vipState=await state(),subset=vipState.scopeKeys.slice(1,3),vipBefore=await counts();
 q=await quote({contentKeys:subset});control('expire',q.id);next=await reconfirm(q);assert.deepEqual(next.selector,{contentKeys:subset});assert.equal(next.private,0);await shot('vip-expired-keeps-exact-subset');await cancel();assert.deepEqual(await counts(),vipBefore);
 q=await quote({contentKeys:subset});control('expire',q.id);await reconfirm(q);const vipId=await commit();r=await receipt(vipId);assert.deepEqual(r.allocations.map(a=>a.contentKey),subset);assert.deepEqual([r.vip,r.private],[2,0]);assert.equal((await state()).privateRemaining,100);await layout('VIP expired exact list and order preserved');
 await select('an');const replayBefore=await counts();q=await quote({replayExamId:Number(freeId)});control('expire',q.id);next=await reconfirm(q);assert.deepEqual(next.selector,{replayExamId:Number(freeId)});assert.equal(next.private,0);await shot('replay-expired-keeps-exam-selector');await cancel();assert.deepEqual(await counts(),replayBefore);
 q=await quote({replayExamId:Number(freeId)});control('expire',q.id);await reconfirm(q);const replayId=await commit();r=await receipt(replayId);assert.deepEqual([r.retained,r.vip,r.private],[5,0,0]);await layout('Replay expired selector preserved');
 await select('dung');const boundaryBefore=await counts(),three=(await state()).scopeKeys.slice(0,3);
 q=await quote({contentKeys:three});assert.deepEqual([q.vip,q.private],[2,1]);control('exhaust-vip',q.id);next=await reconfirm(q);assert.deepEqual(next.selector,{contentKeys:three});assert.deepEqual([next.vip,next.private],[0,3]);assert.equal((await state()).privateRemaining,50);assert.equal((await counts()).attempts,boundaryBefore.attempts);await shot('increased-private-needs-confirmation');await cancel();assert.equal((await state()).privateRemaining,50);
 q=await quote({contentKeys:three});assert.equal(q.private,3);const boundaryId=await commit();r=await receipt(boundaryId);assert.deepEqual([r.vip,r.private],[0,3]);assert.equal((await state()).privateRemaining,47);await layout('Allocation increase cannot spend before reconfirm');
 await select('chi');await cookie('expired-vip',true);await buy();const chiKeys=(await state()).scopeKeys;q=await quote({contentKeys:chiKeys.slice(0,1)});
 const pending=await page.evaluate(()=>({requestKey:allocationPending.requestKey,quoteId:allocationPending.quote.quoteId,selector:structuredClone(allocationPending.selector)}));
 // Create a real prior request with same requestKey but a DIFFERENT selector. Then let real server issue409.
 await page.evaluate(async({requestKey,selection})=>{const quote=await api('/qa-api/wallet/quote',selection);await api('/api/v1/exams',{requestKey,...selection,quoteId:quote.quoteId,confirmWallet:true});},{requestKey:pending.requestKey,selection:{contentKeys:chiKeys.slice(1,2)}});
 await until(()=>quotes.length>=1);const conflictBefore=await counts(),quoteCount=quotes.length;
 await page.locator('#confirm-allocation').click();await ready();await page.waitForFunction(()=>document.querySelector('#allocation-notice').textContent.includes('requestKey'));assert.equal(quotes.length,quoteCount);assert.deepEqual(await counts(),conflictBefore);assert.deepEqual(await page.evaluate(()=>allocationPending.selector),pending.selector);await shot('request-key-conflict-does-not-requote');
 for(const [status,reconfirm] of [[409,false],[409,'true'],[403,true]]){
   const handler=route=>route.fulfill({status,contentType:'application/json',body:JSON.stringify({error:'QA conflict without allocation confirmation',reconfirm})});
   await page.route('**/api/v1/exams',handler);await page.locator('#confirm-allocation').click();await ready();await page.waitForFunction(()=>document.querySelector('#allocation-notice').textContent.includes('QA conflict'));
   assert.equal(quotes.length,quoteCount);assert.deepEqual(await counts(),conflictBefore);assert.deepEqual(await page.evaluate(()=>({requestKey:allocationPending.requestKey,selector:allocationPending.selector,quoteId:allocationPending.quote.quoteId})),pending);
   await page.unroute('**/api/v1/exams',handler);
 }
 await cancel();assert.deepEqual(await counts(),conflictBefore);await layout('Real409/conflict and non-confirmation flags keep request and selector; no order/debit');
 await select('an');const lostBefore=await counts();q=await quote({contentKeys:(await state()).scopeKeys.slice(0,1)});let lostId,deliveredBody;
 const drop=async route=>{deliveredBody=route.request().postDataJSON();const response=await route.fetch();assert.equal(response.status(),200);lostId=(await response.json()).exam.id;await route.abort('failed');};
 await page.route('**/api/v1/exams',drop,{times:1});await page.locator('#confirm-allocation').click();await until(()=>lostId!==undefined);await ready();await page.waitForFunction(()=>document.querySelector('#allocation-notice').textContent.includes('gửi lại an toàn'));await page.unroute('**/api/v1/exams',drop);
 const lostAfter=await counts();assert.deepEqual([lostAfter.attempts-lostBefore.attempts,lostBefore.private-lostAfter.private],[1,1]);control('expire',q.id);await shot('lost-response-keeps-request-for-safe-retry');const retryId=await commit();assert.equal(retryId,lostId);assert.deepEqual(commits.at(-1),deliveredBody);assert.deepEqual(await counts(),lostAfter);r=await receipt(retryId);assert.equal(r.private,1);await layout('Lost response retry after quote expiry remains one attempt/debit');
 report.results={freeQuoteExpired:{selector:{setIndex:1},private:0,walletRemaining:100,cancelNoCharge:true},vipQuoteExpired:{selector:{contentKeys:subset},private:0,keptOrder:true},replayQuoteExpired:{replayExamId:Number(freeId),private:0},increase:{confirmedInitially:1,recomputed:3,cancelNoCharge:true,chargedAfterReconfirm:3},conflict409:{realRequestKeyConflict:true,noRequote:true,noNewOrderOrDebit:true,sameRequestPreserved:true},lostResponse:{oneAttempt:true,oneDebit:true,sameRequestBody:true,sameExam:true,retryAfterQuoteExpired:true}};
 const logout=await call('/api/v1/auth/logout',{});assert.equal(logout.status,200);await cookie('logout',false);await page.reload();await visible('[data-profile="an"]');await cookie('reload-after-logout',false);await layout('Final layout');assert.equal(report.mainRequests,0);assert.equal(report.websiteRequests,0);assert.deepEqual(report.pageErrors,[]);report.status='PASS';
}catch(e){report.status='FAIL';report.error=e.stack;if(page)await shot('failure').catch(()=>{});process.exitCode=1;}finally{if(browser)await browser.close();fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,width:w,height:h,error:report.error}));}})();
