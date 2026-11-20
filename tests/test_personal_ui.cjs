'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(path.resolve(__dirname,'../../../battle-loading-release-20261113/src/node_modules/playwright'));
const front=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/student');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});try{
 const errors=[],checks=[];
 async function setup(){
 const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort();if(u.pathname==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><base href="/"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/learning.css"><link rel="stylesheet" href="/arena-shared.css"><link rel="stylesheet" href="/themes.css"></head><body class="learning-mode"><main id="app"></main><dialog id="modal"><div id="modal-body"></div></dialog></body></html>'});try{const f=path.join(front,u.pathname);return route.fulfill({body:fs.readFileSync(f),contentType:f.endsWith('.js')?'text/javascript; charset=utf-8':f.endsWith('.css')?'text/css; charset=utf-8':'image/webp'});}catch{return route.fulfill({status:404,body:''});}});
 await page.goto('http://127.0.0.1:19131/');
 for(const f of ['nickname-policy.js','learning-content.js','group-games.js','game-rules.js','solution-view.js','themes.js','arena-art/badge-mascots/data.js','arena-art/badge-mascots/runtime.js','arena-shared.js'])await page.addScriptTag({url:'/'+f});
 await page.evaluate(()=>{
 window.calls=[];window.themes={1:'morning-garden',2:'garden-notebook'};window.eligible=true;window.quote=0;window.noticeMode=false;
 window.makeSnapshot=(id=1)=>({authenticated:true,name:id===1?'Mầm QA':'Bông QA',csrf:'fixture',account:{id,login:'qa',membership:'Free',companionChangesRemaining:1,notifications:[],referrals:[],classes:[]},state:{mascot:'sprout',grade:5,birthYear:2015,points:80,theme:themes[id],completed:{},exams:{},battles:{},activity:{}},personalSummary:{study:{completedLessons:12,submittedExams:8,answeredQuestions:90},games:{wins:5,losses:3,draws:2,total:10},referral:{code:id===1?'CHILD01':'CHILD02',rewardDays:7,policy:'child-first-paid-v1'}}});
 window.PlatformAPI={enabled:true,familyContext:'fixture',familyState:{scope:'child',activeProfile:{type:'child'}},snapshot:makeSnapshot(),request:async(action,body,options)=>{
 calls.push({action,body,owner:options?.owner});
 if(action==='personal/notifications'||action==='personal/notifications/read')return {rows:noticeMode?[{id:81,title:'Bài tập của em',body:'Nội dung <img src=x onerror=alert(1)>',createdAt:'2026-11-18T01:00:00Z',readAt:action.endsWith('/read')?'2026-11-18T02:00:00Z':null,senderName:'Giáo viên',kind:'class_assignment'}]:[],total:noticeMode?1:0,unreadCount:noticeMode&&!action.endsWith('/read')?1:0};
 if(action==='preferences'){themes[options.owner]=body.theme;PlatformAPI.snapshot.state.theme=body.theme;return structuredClone(PlatformAPI.snapshot);}
 if(action==='mascot'){await new Promise(resolve=>setTimeout(resolve,30));PlatformAPI.snapshot.state.mascot=body.mascot;PlatformAPI.snapshot.account.companionChangesRemaining=0;return structuredClone(PlatformAPI.snapshot);}
 if(action==='payments/preview'){if(body.referralCode==='INVALID')throw new Error('Mã giới thiệu chưa hợp lệ.');return {quoteHash:'quote'+(++quote),preview:{studentId:PlatformAPI.familyState?.selectedChildId||1,type:'subscription',title:'VIP',plan:body.plan,period:body.period,total:100000,rights:[],fulfillment:'Fixture',policyVersion:'fixture',referralEligible:eligible,referralCode:body.referralCode||''}};}
 if(action==='payments'&&body){window.orderBody=structuredClone(body);throw new Error('Fixture transient');}
 if(action==='payments')return {orders:[]};
 return PlatformAPI.snapshot;
 }};
 window.ArenaAudio={setActive(){},button(){return ''},mount(){}};window.confirm=()=>true;
 });
 for(const dep of ['ui-controls.js', 'question-frame.js', 'practice-scratchpad.js', 'learning-modules/study.js', 'learning-modules/practice.js', 'learning-modules/profile.js', 'learning-modules/classroom.js', 'learning-modules/commerce.js', 'learning-modules/arena.js'])await page.addScriptTag({url:'/'+dep});await page.addScriptTag({url:'/learning.js'});
 await page.evaluate(()=>{window.routeForTest='profile';window.drawPersonal=()=>{ThemeManager.sync(PlatformAPI.snapshot);LearningApp.configure({progress:{name:PlatformAPI.snapshot.name,completed:[],attempts:[]},toast:message=>window.testToast=message,redraw:drawPersonal,showModal:html=>{document.querySelector('#modal-body').innerHTML=html;document.querySelector('#modal').showModal();}});document.querySelector('#app').innerHTML=LearningApp.render(routeForTest);};drawPersonal();LearningApp.mount('profile');});
 return page;
 }
 const page=await setup();
 await page.evaluate(()=>{PlatformAPI.snapshot.personalSummary.referral.rewards=['queued','active','used','held-internal'].map((status,index)=>({tier:index%2?'VIP+':'VIP',days:7,startsAt:status==='held-internal'?null:'2026-11-19T01:00:00Z',endsAt:status==='held-internal'?null:'2026-11-26T01:00:00Z',status,inviteeName:'PRIVATE-INVITEE',orderId:'PRIVATE-ORDER',email:'PRIVATE-EMAIL'}));drawPersonal();LearningApp.mount('profile');});
 assert.equal(await page.locator('#account-notifications .personal-reward-notice').count(),4);
 assert((await page.locator('.personal-reward-notices').textContent()).includes('7 ngày VIP+'));
 assert(!(await page.locator('#account-notifications').textContent()).includes('PRIVATE-'));
 assert.equal(await page.locator('.personal-reward-notices button,.personal-reward-notices a').count(),0);
 checks.push('own reward notice: queued/active/used/held, tier+7days+timeline only, no invitee/order/email or mutation controls');
 for(const [width,height] of [[360,800],[800,360],[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){
 await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
 assert.equal(await page.locator('.personal-overview').count(),1);assert.equal(await page.locator('#app .pet-option').count(),0);
 assert.equal(await page.locator('#appearance-cancel,#appearance-default,[data-learning="logout"],[data-learning="refresh-account"],#account-referrals').count(),0);
 assert.equal(await page.locator('a[href*="invite="]').count(),0);
 assert.equal(await page.locator('.personal-summary dd').allTextContents().then(x=>x.join(',')),'12,8,90');
 assert.equal(await page.locator('.personal-study-next').count(),1);
 assert.equal(await page.locator('.personal-zoom').count(),0);
 assert.equal(await page.locator('#personal-referral-code').inputValue(),'CHILD01');
 await page.screenshot({path:path.join(out,`personal-${width}x${height}.png`),fullPage:true});
 }checks.push('7 viewports portrait/landscape: merged real stats, compact companion, no removed actions/link/referrer panel');
 assert(await page.evaluate(()=>{const a=document.querySelector('#account-notifications'),b=document.querySelector('#appearance'),c=document.querySelector('.personal-invite');return Boolean(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING)&&Boolean(b.compareDocumentPosition(c)&Node.DOCUMENT_POSITION_FOLLOWING);}));checks.push('notifications before theme before own-code panel');
 await page.locator('[data-learning="open-companion"]').click();await page.locator('#modal[open] .pet-option').first().waitFor();
 await page.evaluate(()=>{const controls=[...document.querySelectorAll('#modal-body [data-learning^="choose-"]')];controls[0].click();controls[1].click();});
 await page.waitForFunction(()=>!document.querySelector('#modal').open&&!document.querySelector('[data-learning="open-companion"]'));
 assert.equal(await page.evaluate(()=>calls.filter(x=>x.action==='mascot').length),1);assert.equal(await page.evaluate(()=>PlatformAPI.snapshot.state.points),80);checks.push('companion opens dialog; rapid two choices produce one mutation, XP retained');
 await page.evaluate(()=>LearningApp.mount('profile'));
 await page.locator('.theme-option').filter({has:page.locator('[value="crayon-workshop"]')}).click();
 assert.equal(await page.evaluate(()=>calls.filter(x=>x.action==='preferences').length),0);
 await page.locator('#appearance-form [type="submit"]').click();await page.waitForFunction(()=>ThemeManager.savedTheme==='crayon-workshop');
 assert.equal(await page.evaluate(()=>themes[1]),'crayon-workshop');
 await page.evaluate(()=>{PlatformAPI.snapshot=makeSnapshot(2);drawPersonal();LearningApp.mount('profile');});
 assert.equal(await page.evaluate(()=>ThemeManager.theme),'garden-notebook');assert.equal(await page.locator('#personal-referral-code').inputValue(),'CHILD02');
 assert.equal(await page.locator('.personal-reward-notice').count(),0);checks.push('switch child hides previous child reward notices; absent rewards field is empty');
 await page.evaluate(()=>{PlatformAPI.snapshot=makeSnapshot(1);drawPersonal();LearningApp.mount('profile');});
 assert.equal(await page.evaluate(()=>ThemeManager.theme),'crayon-workshop');checks.push('theme requires apply; child1/child2 switch isolates preferences and codes');
 const second=await setup();await second.evaluate(()=>{themes[1]='crayon-workshop';PlatformAPI.snapshot=makeSnapshot(1);drawPersonal();LearningApp.mount('profile');});assert.equal(await second.evaluate(()=>ThemeManager.theme),'crayon-workshop');await second.close();checks.push('second independent browser context uses server preference');
 await page.evaluate(()=>{noticeMode=true;PlatformAPI.snapshot.account.membership='SVip';LearningApp.mount('profile');});await page.locator('[data-personal-notice="81"]').waitFor();await page.locator('[data-personal-notice="81"]').click();await page.locator('#personal-notice-close').waitFor();assert.equal(await page.locator('#modal-body img').count(),0);assert((await page.locator('#modal-body').textContent()).includes('<img'));await page.locator('#personal-notice-close').click();assert((await page.evaluate(()=>calls)).some(x=>x.action==='personal/notifications/read'&&x.body.ids[0]===81));checks.push('safe personal notices endpoint/read IDs; camelCase fields rendered, body escaped');
 await page.evaluate(()=>{LearningApp.unmount();PlatformAPI.familyState={scope:'parent_full',activeProfile:{type:'parent'},context:'fixture',csrf:PlatformAPI.snapshot.csrf,selectedChildId:12};history.replaceState(null,'','/?childId=12');routeForTest='payment';drawPersonal();LearningApp.mount('payment');});
 await page.locator('.checkout-review').waitFor().catch(async error=>{console.log('CHECKOUT DEBUG',await page.evaluate(()=>({text:document.querySelector('#payment-content')?.textContent,toast:window.testToast,errors:window.errors,calls:calls.slice(-4)})));throw error;});
 await page.getByLabel('Mã giới thiệu (không bắt buộc)').fill('CHILD77');
 assert(await page.locator('.checkout-review [type="submit"]').isDisabled());
 await page.waitForFunction(()=>calls.some(x=>x.action==='payments/preview'&&x.body.referralCode==='CHILD77')&&!document.querySelector('.checkout-review [type="submit"]').disabled);
 await page.locator('[name="purchaserName"]').fill('Phụ huynh QA');await page.locator('[name="purchaserContact"]').fill('qa@example.test');await page.locator('[name="relationship"]').selectOption('parent');await page.locator('[name="representativeDeclared"]').check();await page.locator('[name="accepted"]').check();await page.locator('.checkout-review [type="submit"]').click();
 await page.waitForFunction(()=>Boolean(window.orderBody));assert.equal(await page.evaluate(()=>orderBody.referralCode),'CHILD77');assert(await page.evaluate(()=>orderBody.checkout.accepted));checks.push('eligible referral requotes before consent; confirmed order body preserves code + quote');
 await page.evaluate(()=>{LearningApp.unmount();eligible=false;drawPersonal();LearningApp.mount('payment');});await page.locator('.checkout-review').waitFor();assert.equal(await page.locator('[name="referralCode"]').count(),0);checks.push('ineligible/repeat purchase has no referral input');
 await page.evaluate(()=>{window.parentStart=calls.length;for(const type of ['focus','online','pageshow','pagehide'])window.dispatchEvent(new Event(type));document.dispatchEvent(new Event('visibilitychange'));});assert((await page.evaluate(()=>calls.slice(parentStart))).every(x=>x.action.startsWith('payments')));checks.push('parent-commerce lifecycle retains no learner heartbeat or personal-notices calls');
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'PERSONAL-RESULT.json'),JSON.stringify({status:'PASS',checks,viewports:7,pageErrors:errors,scope:'candidate files+API fixtures only; no live/DB/payment'},null,2));console.log(JSON.stringify({status:'PASS',checks,pageErrors:errors}));
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
