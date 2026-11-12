'use strict';
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const {randomBytes}=require('node:crypto');
const base=new URL(process.env.BASE_URL||'http://127.0.0.1:18886');
assert(['127.0.0.1','localhost','review-20261112.5bmath.pages.dev'].includes(base.hostname),'Disposable QA/preview only');
const out=path.resolve(__dirname,'../work/auth-performance');fs.mkdirSync(out,{recursive:true});
const report={scope:'QA only: delayed session, immediate login, compact auth, full dashboard, duplicate submit',layouts:[],errors:[]};
(async()=>{
 const executablePath=process.env.CHROME_PATH||(process.platform==='win32'?require('../tools/mascot-animation/runtime.cjs').chromePath():undefined);
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
 try{
  for(const [width,height] of [[390,844],[844,390],[768,1024],[1024,768],[1440,900],[900,1440]]){
   const context=await browser.newContext({viewport:{width,height}});const page=await context.newPage();const resources=[];
   page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>resources.push(new URL(r.url()).pathname));
   await context.route('https://fonts.googleapis.com/**',r=>r.abort());
   await context.route('https://fonts.gstatic.com/**',r=>r.abort());
   let release;const pending=new Promise(r=>release=r);
   await page.route('**/api/v1/session?view=identity',async r=>{await pending;await r.fulfill({json:{authenticated:false}});});
   await page.goto(base.href,{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>typeof document.querySelector('#account')?.onclick==='function');
   if(width<800){await page.locator('#menu').click();assert.equal(await page.locator('#menu').getAttribute('aria-expanded'),'true');}
   await page.evaluate(()=>{window.authClickAt=performance.now();document.querySelector('#account').click();});
   await page.locator('#auth-form').waitFor();
   const elapsed=await page.evaluate(()=>performance.now()-window.authClickAt);
   assert(elapsed<500,'Login dialog must open without waiting for session or learning');
   assert(!resources.some(p=>/\/(learning|learning-content|arena-audio)\.(js|css)$/.test(p)),'No learning/audio transfer before guest login dialog');
   await page.locator('#auth-form button[type=submit]').scrollIntoViewIfNeeded();
   const hit=await page.locator('#auth-form button[type=submit]').evaluate(n=>{const b=n.getBoundingClientRect();return n.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2));});assert(hit);
   await page.screenshot({path:path.join(out,`login-${width}x${height}.png`)});
   release();await page.waitForTimeout(50);report.layouts.push({width,height,clickToDialogMs:Math.round(elapsed),sessionWasPending:true});await context.close();
  }
  const login='perf-'+randomBytes(8).toString('hex'),password='Mật-khẩu-'+randomBytes(16).toString('hex');
  const birthYear=Number(new Intl.DateTimeFormat('en',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric'}).format(new Date()))-10;
  const registration=await fetch(new URL('/api/v1/auth/register',base),{method:'POST',headers:{'User-Agent':'5BMath-QA/1.0','Origin':base.origin,'Content-Type':'application/json'},body:JSON.stringify({login,password,name:'Bạn học thử',birthYear})});assert.equal(registration.status,200);await registration.arrayBuffer();
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();let posts=0,authBytes=0;
  page.on('pageerror',e=>report.errors.push(e.message));
  page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/auth/login'))posts++;});
  await page.goto(base.href,{waitUntil:'load'});await page.locator('#account').click();await page.locator('#auth-form').waitFor();
  await page.locator('[name=login]').fill(login);await page.locator('[name=password]').fill(password);
  const responsePromise=page.waitForResponse(r=>r.url().includes('/auth/login'));
  const started=Date.now();await page.locator('#auth-form').evaluate(f=>{f.requestSubmit();f.requestSubmit();});
  const response=await responsePromise;const auth=await response.json();authBytes=(await response.body()).byteLength;
  assert.equal(response.status(),200);assert.equal(auth.partial,true);assert(!auth.lessons);assert(auth.authenticated);
  await page.waitForURL('**/goc-hoc-tap/');await page.waitForFunction(()=>typeof PlatformAPI!=='undefined'&&PlatformAPI.snapshot.authenticated&&!PlatformAPI.snapshot.partial);
  assert.equal(posts,1,'Duplicate form submission must not issue two auth requests');
  report.login={status:200,loginApiMs:Date.now()-started,compactBytes:authBytes,posts,fullDashboard:true};await context.close();
  assert.deepEqual(report.errors,[]);report.status='passed';console.log(JSON.stringify(report));
 }finally{await browser.close();fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));}
})().catch(e=>{console.error(e);process.exitCode=1;});
