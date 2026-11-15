'use strict';
// Disposable loopback database only. Never run against the main service.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const runtime=require('../tools/mascot-animation/runtime.cjs');
const {chromium}=runtime.getPackage('playwright');
const base=process.env.TYPED_BASE_URL||'http://127.0.0.1:18871',out=path.resolve(process.env.TYPED_BROWSER_OUTPUT||'work/typed-answers-20261113/browser');
assert(new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='8765','Disposable loopback only');
const database=process.env.TYPED_DATABASE||'work/typed-answers-20261113/browser.sqlite3';
fs.mkdirSync(out,{recursive:true});
const report={checks:[],errors:[],screenshots:[]};
let debugPage;
const python=process.env.TYPED_PYTHON;
const rules=()=>JSON.parse(execFileSync(python,['-c',"import sqlite3,json,sys; d=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); print(json.dumps({str(r[0]):json.loads(r[1])['answer'] for r in d.execute('select id,grading_rule_json from question_versions')}))",database],{encoding:'utf8'}));
const equivalent=value=>{const n=String(value).match(/^(\d+)\/(\d+)$/);return n?`${Number(n[1])*2}/${Number(n[2])*2}`:String(value).replace('.',',');};
async function call(context,route,body,csrf=''){
 const response=await context.request[body===undefined?'get':'post'](base+'/api/v1/'+route,{headers:{Origin:base,'X-CSRF-Token':csrf},...(body===undefined?{}:{data:body})});
 const value=await response.json();assert.equal(response.status(),200,JSON.stringify(value));return value;
}
async function user(browser,name){
 const context=await browser.newContext({viewport:{width:390,height:844}});
 await context.route('https://fonts.googleapis.com/**',r=>r.abort());await context.route('https://fonts.gstatic.com/**',r=>r.abort());
 const state=await call(context,'auth/register',{login:'typed-'+Date.now()+'-'+Math.random().toString(16).slice(2),password:'Typed-Only-QA-2026',name,birthYear:2016});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 return {context,page,csrf:state.csrf};
}
async function shot(page,name){await page.waitForFunction(()=>!document.documentElement.classList.contains('page-loading'));await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});report.screenshots.push(name+'.png');}
async function noOverflow(page){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'Horizontal overflow');}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:runtime.chromePath()});
 try{
  const a=await user(browser,'Bạn An QA'),b=await user(browser,'Bạn Bình QA');debugPage=a.page;
  const exam=(await call(a.context,'exams',{requestKey:crypto.randomUUID(),topic:'fraction',count:3},a.csrf)).exam;
  assert.equal(exam.responseMode,'typed');assert(!('options'in exam.questions[0]));
  await a.page.goto(base+'/lam-de/?id='+exam.id);await a.page.locator('#exam-answer').waitFor();
  assert.equal(await a.page.locator('input[type=radio]').count(),0);
  await a.page.locator('#exam-answer').fill('1/2');
  // Immediate navigation must flush the current value before redrawing.
  await a.page.locator('[data-learning=next]').click();
  await a.page.waitForFunction(()=>document.querySelector('#exam-answer')?.dataset.position==='2');
  assert.equal((await call(a.context,'exams/'+exam.id)).exam.answers['1'],'1/2');
  await a.page.locator('#exam-answer').fill('0,75');
  await a.page.waitForFunction(()=>document.querySelector('#answer-save-status')?.textContent==='Đã lưu');
  await a.page.reload();await a.page.locator('#exam-answer').waitFor();
  assert.equal(await a.page.locator('#exam-answer').inputValue(),'0,75');
  for(const [width,height]of [[390,844],[844,390],[768,1024],[1024,768],[1440,900],[900,1440]]){
   await a.page.setViewportSize({width,height});await noOverflow(a.page);await shot(a.page,`exam-${width}x${height}`);
  }
  report.checks.push('Typed exam: no choices; immediate navigation saves; reload retains answer; six portrait/landscape viewports.');
  const owner=await call(a.context,'arena',{action:'create',scope:'all'},a.csrf);
  const friend=await call(b.context,'arena',{action:'join',code:owner.code},b.csrf);
  await call(a.context,'arena',{action:'accept',...owner},a.csrf);
  for(const [u,room]of [[a,owner],[b,friend]]){
   await u.page.goto(base+'/goc-hoc-tap/');await u.page.evaluate(room=>sessionStorage.setItem('5bmath-room',JSON.stringify(room)),room);
   await u.page.goto(base+'/tran-dau/');
  }
  await a.page.locator('#battle-answer:not([disabled])').waitFor();await b.page.locator('#battle-answer:not([disabled])').waitFor();
  const current=(await call(a.context,'arena',{action:'state',...owner},a.csrf)).battle;
  const answers=rules(),answer=equivalent(answers[current.questions[current.index].id]);
  await b.page.locator('#battle-answer').fill(answer);await b.page.locator('#battle-answer').focus();
  await a.page.locator('#battle-answer').fill(answer);await a.page.locator('#battle-answer-form button').click();
  await b.page.locator('#battle-defense-status:not([hidden])').waitFor();
  assert.equal(await b.page.locator('#battle-answer').inputValue(),answer);
  assert(await b.page.locator('#battle-answer').evaluate(e=>e===document.activeElement),'Defense stole typing focus');
  assert.match(await a.page.locator('#battle-defense-status').innerText(),/Chờ đối thủ phòng thủ/);
  assert.equal((await call(b.context,'arena',{action:'state',...friend},b.csrf)).battle.hp,100);
  await b.page.locator('#battle-answer-form button').click();
  await b.page.waitForFunction(()=>document.querySelector('#my-hp')?.textContent.startsWith('90 /'));
  assert.equal(await b.page.locator('#fighter-me .damage').innerText(),'−10 ♥');
  assert(await b.page.locator('#fighter-me').evaluate(e=>e.classList.contains('defending')));
  await shot(b.page,'defense-success-390x844');
  report.checks.push('Two authenticated players: pending HP100; countdown on attacker; draft and focus preserved; defense gives HP90 and −10 label.');
  await a.page.waitForFunction(()=>document.querySelector('.battle-question-meta')?.textContent.includes('Câu 2 /'),null,{timeout:10000});
  const second=(await call(a.context,'arena',{action:'state',...owner},a.csrf)).battle;
  await a.page.locator('#battle-answer').fill(String(answers[second.questions[second.index].id]));await a.page.locator('#battle-answer-form button').click();
  await b.page.waitForFunction(()=>document.querySelector('#my-hp')?.textContent.startsWith('70 /'),null,{timeout:8000});
  assert.equal(await b.page.locator('#fighter-me .damage').innerText(),'−20 ♥');
  report.checks.push('No defense: exactly20 additional HP lost after3seconds.');
  // Independent bot demo also uses pending defense rather than immediate damage.
  const c=await user(browser,'Bạn Chi QA');await c.page.goto(base+'/dau-tri/');
  await c.page.evaluate(()=>sessionStorage.removeItem('5bmath-room'));
  await c.page.locator('[data-arena-mode=bot]').click();
  await c.page.locator('[data-learning=start-bot]').first().click();
  // The scope chooser is required before a bot request is made.
  const confirm=c.page.locator('#arena-preflight-confirm');
  if(await confirm.count())await confirm.click();
  await c.page.waitForURL('**/tran-dau/');
  await c.page.locator('#arena-overlay').waitFor({state:'hidden'});
  await c.page.locator('#battle-answer:not([disabled])').waitFor();
  // Bot is explicitly an unranked client demo; its scheduled questions are
  // persisted by the app, including standalone/offline sample questions.
  const botAnswer=await c.page.evaluate(()=>{const b=JSON.parse(sessionStorage.getItem('5bmath-bot-battle'));return String(b.questions[b.index].answer);});
  await c.page.locator('#battle-answer').fill(botAnswer);await c.page.locator('#battle-answer-form button').click();
  await c.page.locator('#battle-defense-status:not([hidden])').waitFor();
  assert(await c.page.locator('#opponent-hp').innerText()==='100 / 100 ♥');
  await c.page.waitForFunction(()=>document.querySelector('#opponent-hp')?.textContent.startsWith('80 /'),null,{timeout:8000});
  report.checks.push('Bot: correct first answer opens3seconds before applying20damage; no automatic correct defense.');
  await c.context.close();
  await a.context.close();await b.context.close();
  assert.deepEqual(report.errors,[]);
  report.status='PASS';
 }catch(error){report.status='FAIL';report.failure=error.stack;if(debugPage){await shot(debugPage,'failure');report.body=await debugPage.locator('body').innerText();}throw error;}
 finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
