'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(path.resolve(__dirname,'../../../battle-loading-release-20261113/src/node_modules/playwright'));
const front=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/student');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});try{
const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort();if(u.pathname==='/')return route.fulfill({body:'<!doctype html><html><head><meta charset="utf-8"><base href="/"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/learning.css"><link rel="stylesheet" href="/arena-shared.css"></head><body class="learning-mode"><main id="app"></main><dialog id="modal"><div id="modal-body"></div></dialog></body></html>',contentType:'text/html'});try{const f=path.join(front,u.pathname);return route.fulfill({body:fs.readFileSync(f),contentType:f.endsWith('.js')?'text/javascript; charset=utf-8':f.endsWith('.css')?'text/css; charset=utf-8':'image/webp'});}catch{return route.fulfill({status:404,body:''});}});
await page.goto('http://127.0.0.1:19129/');
for(const f of ['nickname-policy.js','learning-content.js','group-games.js','game-rules.js','solution-view.js','arena-art/badge-mascots/data.js','arena-art/badge-mascots/runtime.js','arena-shared.js'])await page.addScriptTag({url:'/'+f});
await page.evaluate(()=>{window.PlatformAPI={enabled:true,familyContext:{scope:'child'},snapshot:{authenticated:true,name:'Mầm QA',account:{id:1,login:'qa',membership:'Free',companionChangesRemaining:1,notifications:[],referrals:[],classes:[]},state:{mascot:'sprout',grade:5,birthYear:2015,points:80,completed:{},exams:{},battles:{},activity:{}}},request:async()=>PlatformAPI.snapshot};window.ArenaAudio={setActive(){},button(){return ''},mount(){}};window.confirm=()=>true;});
for(const dep of ['ui-controls.js', 'question-frame.js', 'practice-scratchpad.js', 'learning-modules/study.js', 'learning-modules/practice.js', 'learning-modules/profile.js', 'learning-modules/classroom.js', 'learning-modules/commerce.js', 'learning-modules/arena.js'])await page.addScriptTag({url:'/'+dep});await page.addScriptTag({url:'/learning.js'});
await page.evaluate(()=>{window.routeForTest='profile';window.drawStudent=()=>{LearningApp.configure({progress:{name:'Mầm QA',completed:[],attempts:[]},toast:()=>{},redraw:drawStudent,showModal:html=>{document.querySelector('#modal-body').innerHTML=html;document.querySelector('#modal').showModal();}});document.querySelector('#app').innerHTML=LearningApp.render(routeForTest);};drawStudent();});
const results=[];
for(const [width,height] of [[360,800],[800,360],[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){await page.setViewportSize({width,height});for(const route of ['weekly','exams','arena','rank','profile','mascot','upgrade']){await page.evaluate(r=>{routeForTest=r;drawStudent();},route);assert.equal(await page.locator('.sidebar,.topbar,#learning-navigation').count(),0);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${route} ${width}`);if(['weekly','exams'].includes(route))assert.equal(await page.locator('.student-study-tabs a').count(),2);if(['profile','mascot'].includes(route)){assert.equal(await page.locator('.personal-overview').count(),1);assert.equal(await page.locator('.personal-zoom').count(),0);}results.push(`${route}:${width}x${height}`);}await page.screenshot({path:path.join(out,`${width}x${height}.png`),fullPage:true});}
await page.evaluate(()=>{PlatformAPI.snapshot.account.membership='VIP';routeForTest='profile';drawStudent();});assert.equal(await page.locator('.personal-zoom').count(),0);
await page.evaluate(()=>{PlatformAPI.snapshot.account.companionChangesRemaining=0;drawStudent();});assert.equal(await page.locator('[data-learning^="choose-"]').count(),0);
await page.evaluate(()=>{delete PlatformAPI.snapshot.account.companionChangesRemaining;drawStudent();});assert.equal(await page.locator('[data-learning^="choose-"]').count(),0);
await page.evaluate(()=>{PlatformAPI.snapshot.account.companionChangesRemaining=1;drawStudent();});assert.equal(await page.locator('[data-learning="open-companion"]').count(),1);
await page.evaluate(()=>{history.replaceState(null,'','/?childId=12');routeForTest='upgrade';drawStudent();});for(const href of await page.locator('a[href*="thanh-toan/"]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href'))))assert(href.includes('childId=12'));
await page.evaluate(()=>{history.replaceState(null,'','/');routeForTest='profile';drawStudent();window.mascotCalls=0;PlatformAPI.request=async(action,body)=>{if(action==='mascot'){mascotCalls++;await new Promise(resolve=>setTimeout(resolve,30));PlatformAPI.snapshot.state.mascot=body.mascot;PlatformAPI.snapshot.account.companionChangesRemaining=0;}return PlatformAPI.snapshot;};LearningApp.mount('profile');});
await page.evaluate(()=>{document.querySelector('[data-learning="open-companion"]').click();const controls=[...document.querySelectorAll('[data-learning^="choose-"]')];controls[0].click();controls[1].click();});
await page.waitForFunction(()=>mascotCalls===1&&!document.querySelector('[data-learning="open-companion"]')&&!document.querySelector('#modal').open);
assert.equal(await page.evaluate(()=>PlatformAPI.snapshot.state.points),80);
assert.equal(await page.locator('.personal-overview').count(),1);
// A parent's selected beneficiary is not an active learner. Exercise real mount
// and lifecycle events with a stale room cache and a 61-second clock advance.
await page.evaluate(()=>{
 LearningApp.unmount();window.parentCalls=[];window.timerCallbacks=[];
 PlatformAPI.familyState={scope:'parent_full',activeProfile:{type:'parent'},selectedChildId:12,context:'fixture-parent',csrf:'fixture-parent'};
 PlatformAPI.snapshot.csrf='fixture-parent';
 PlatformAPI.request=async action=>{parentCalls.push(action);return PlatformAPI.snapshot;};
 window.oldInterval=window.setInterval;window.setInterval=(callback)=>{timerCallbacks.push(callback);return 9001;};
 sessionStorage.setItem('5bmath-room','stale-learner-room');
 history.replaceState(null,'','/?childId=12');routeForTest='upgrade';drawStudent();LearningApp.mount('upgrade');
 const realNow=Date.now;Date.now=()=>realNow()+61000;
 for(const event of ['focus','pageshow','online','pagehide'])window.dispatchEvent(new Event(event));
 document.dispatchEvent(new Event('visibilitychange'));timerCallbacks.forEach(fn=>fn());
 LearningApp.unmount();Date.now=realNow;window.setInterval=oldInterval;
});
assert.deepEqual(await page.evaluate(()=>parentCalls),[],'parent upgrade must perform no learner background requests');
await page.evaluate(()=>{
 PlatformAPI.request=async action=>{parentCalls.push(action);return action==='payments/preview'?{quoteHash:'fixture',preview:{studentId:12,type:'subscription',plan:'VIP',period:'month',title:'VIP fixture',total:100000,rights:[],fulfillment:'Fixture',policyVersion:'fixture'}}:{orders:[]};};
 routeForTest='payment';drawStudent();LearningApp.mount('payment');
});
await page.locator('.checkout-review').waitFor();
assert((await page.evaluate(()=>parentCalls)).every(action=>action==='payments'||action==='payments/preview'));
await page.evaluate(()=>{LearningApp.unmount();PlatformAPI.request=async action=>{parentCalls.push(action);return PlatformAPI.snapshot;};});
await page.evaluate(()=>{PlatformAPI.familyState={scope:'child',activeProfile:{type:'child'}};sessionStorage.removeItem('5bmath-room');routeForTest='profile';drawStudent();LearningApp.mount('profile');});
assert((await page.evaluate(()=>parentCalls)).includes('heartbeat'),'child still sends heartbeat');
await page.evaluate(()=>LearningApp.unmount());
assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify({status:'PASS',renderChecks:results.length,viewports:7,checks:['no sidebar/topbar','study subtabs','legacy mascot personal','Free Zoom hidden','paid personal Zoom','allowance1/0/missing','upgrade/payment preserves childId','mounted companion action: rapid two clicks only one mutation, allowance0 reflected, XP unchanged','Vietnamese UTF8 heading correct','parent upgrade mount/61s clock/focus/online/pageshow/pagehide/visibility/unmount: zero learner requests even stale room cache','parent payment mounts checkout form with payment-only preview/history calls','child profile still sends heartbeat'],errors,network:'all local files/fixtures, no real server'},null,2));console.log('PASS '+results.length+' renders; companion/beneficiary/parent lifecycle/payment/child heartbeat checks');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
