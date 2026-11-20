'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(path.resolve(__dirname,'../../../battle-loading-release-20261113/src/node_modules/playwright'));
const front=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/games-ui');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});try{
const page=await browser.newPage(),errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort();if(u.pathname==='/tran-dau/')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><h1>Trận đấu</h1>'});if(u.pathname==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html><head><meta charset="utf-8"><base href="/"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/learning.css"><link rel="stylesheet" href="/group-games.css"><link rel="stylesheet" href="/arena-shared.css"><link rel="stylesheet" href="/game-session.css"><link rel="stylesheet" href="/app-shell.css"></head><body class="learning-mode"><main id="app"></main><nav id="test-nav" style="position:fixed;bottom:0;left:0;right:0;height:var(--app-nav-height);background:white">Thanh điều hướng</nav></body></html>'});try{const f=path.join(front,u.pathname);return route.fulfill({body:fs.readFileSync(f),contentType:f.endsWith('.js')?'text/javascript; charset=utf-8':f.endsWith('.css')?'text/css; charset=utf-8':'image/webp'});}catch{return route.fulfill({status:404,body:''});}});
await page.goto('http://127.0.0.1:19137/');for(const f of ['game-rules.js','arena-art/badge-mascots/data.js','arena-art/badge-mascots/runtime.js','arena-shared.js'])await page.addScriptTag({url:'/'+f});
await page.evaluate(()=>{
 window.claim=null;window.room=null;window.calls=[];window.failNext=false;window.holdClaim=false;window.createCount=0;window.confirm=()=>{throw Error('Popup must not request native confirmation');};
 window.PlatformAPI={snapshot:{authenticated:true,account:{id:1},csrf:'session-1',state:{mascot:'sprout',points:80}},familyContext:'family-1',familyState:{activeProfile:{type:'child'},scope:'child'},request:async(action,body)=>{
 calls.push({action,body});
 if(action==='game-claim'){if(failNext){failNext=false;throw new Error('Fixture temporary');}const value=claim;if(holdClaim){await new Promise(resolve=>window.resolveClaim=resolve);}if(body?.action==='leave'){claim=null;return {claim:null};}return {claim:value};}
 if(action==='group-games/catalogue')return {ready:true,modes:[{key:'capture_flag',ready:true},{key:'animal_race',ready:true}],playModes:['human','bot']};
 if(action.startsWith('group-games/rooms?'))return {rooms:[]};
 if(action==='group-games/rooms'){
 createCount++;const id=('a'+createCount).padEnd(32,'0');room={id,mode:body.mode,code:'ABCD1234',public:body.public,status:'waiting',playMode:'human',meStudentId:1,serverTime:Date.now(),players:[{studentId:1,mine:true,name:'Mầm QA',mascot:'sprout',xp:80,seat:0,steps:0}],rankings:[],mapIndex:0,round:0,target:5};
 claim={claimId:'claim'+createCount,game:body.mode,playMode:'human',roomId:id,code:room.code,roomStatus:'waiting',waitingExpiresAt:Date.now()+300000,serverTime:Date.now(),sourceAvailable:true,resumeUrl:'/dau-tri/?game='+body.mode+'&room='+id};return {room,gameClaim:claim};
 }
 if(action.startsWith('group-games/rooms/'))return {room,gameClaim:claim};
 throw Error('Unexpected '+action);
 }};
});await page.addScriptTag({url:'/game-session.js'});await page.addScriptTag({url:'/group-games.js'});
await page.evaluate(()=>GameSession.mountGlobal());assert.equal(await page.locator('#game-session-floating').count(),0);
for(const mode of ['capture_flag','animal_race']){
 await page.evaluate(async mode=>{FivePlayerGames.unmount();history.replaceState(null,'','/dau-tri/?game='+mode);document.querySelector('#app').innerHTML=FivePlayerGames.shell('arena');await FivePlayerGames.mount('arena');},mode);
 assert.equal(await page.locator('.group-page-heading .eyebrow').count(),0);assert.equal(await page.locator('[data-games-audio-slot]').count(),1);
 assert(await page.evaluate(()=>document.querySelector('.group-game-tabs').nextElementSibling.hasAttribute('data-games-audio-slot')));
 await page.locator('[data-group-lobby-tab="friends"]').click();
 for(const [width,height] of [[360,800],[800,360],[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){
 await page.setViewportSize({width,height});await page.locator('[data-group-action="create-friends"]').click();await page.locator('.group-preflight-dialog[open]').waitFor();assert.equal(await page.locator('.group-preflight-dialog').count(),1);assert(await page.locator('[name="visibility"][value="private"]').isChecked());
 assert(await page.evaluate(()=>{const r=document.querySelector('.group-preflight-dialog').getBoundingClientRect();return r.width<=innerWidth&&r.height<=innerHeight&&r.top>=0;}));await page.screenshot({path:path.join(out,`${mode}-preflight-${width}x${height}.png`)});await page.locator('.group-preflight-dialog [value="cancel"]').click();
 }
 await page.locator('[data-group-action="create-friends"]').click();if(mode==='animal_race')await page.locator('[name="visibility"][value="public"]').check();await page.locator('[data-preflight-confirm]').click();await page.locator('.group-joined-list').waitFor();
 assert.equal(await page.evaluate(()=>calls.filter(x=>x.action==='group-games/rooms').at(-1).body.public),mode==='animal_race');
 assert.equal(await page.locator('.group-waiting-lobby .arena-player').count(),0);assert.equal(await page.locator('.group-joined-list .group-player-list li').count(),5);
 for(const [width,height] of [[390,844],[844,390],[1440,900]]){await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,`${mode}-waiting-${width}x${height}.png`),fullPage:true});}
 await page.evaluate(()=>GameSession.mountGlobal());assert.equal(await page.locator('#game-session-floating').count(),0);
 await page.evaluate(()=>{FivePlayerGames.unmount();history.replaceState(null,'','/tai-khoan/');document.querySelector('#app').innerHTML='<h1>Cá nhân</h1>';return GameSession.mountGlobal();});
 if(await page.locator('[data-game-claim-expand]').count())await page.locator('[data-game-claim-expand]').click();
 for(const [width,height] of [[360,800],[800,360],[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){
 await page.setViewportSize({width,height});assert(await page.evaluate(()=>{const r=document.querySelector('#game-session-floating').getBoundingClientRect(),nav=document.querySelector('#test-nav').getBoundingClientRect();return r.bottom<nav.top&&r.left>=0&&r.right<=innerWidth&&r.top>=0;}));
 await page.screenshot({path:path.join(out,`${mode}-global-${width}x${height}.png`)});
 }
 await page.locator('[data-game-claim-minimize]').click();await page.evaluate(()=>{history.replaceState(null,'','/hoc-theo-tuan/');return GameSession.mountGlobal();});assert.equal(await page.locator('#game-session-floating[data-minimized="true"]').count(),1);await page.locator('[data-game-claim-expand]').click();
 await page.evaluate(()=>{failNext=true;return GameSession.refreshGlobal();});assert.equal(await page.locator('#game-session-floating').count(),1);await page.locator('[data-game-claim-retry]').click();await page.locator('[data-game-claim-leave]').click();await page.waitForFunction(()=>!document.querySelector('#game-session-floating'));
}
checks.push('2games: no inner eyebrow; audio slot after chooser; 14preflight +14popup viewport checks; private/public create flags; shared lobby mascot/ownwaiting hidden/list5; global popup single/minimize/navigation/retry/leave');
const popup=page.locator('#game-session-floating'),inline=page.locator('[data-game-session-inline]');
const resume=inline.locator('[data-game-claim-resume]'),leave=inline.locator('[data-game-claim-leave]');
const gameNames={duel:'Đấu trí',capture_flag:'Cướp Cờ',animal_race:'Đua Thú'};
const renderCard=()=>page.evaluate(()=>{
 history.replaceState(null,'','/dau-tri/');
 document.querySelector('#app').innerHTML=ArenaLobby.playerCard({game:'duel',mascot:'sprout',xp:10});
 GameSession.syncInline();
});
const acceptClaim=value=>page.evaluate(value=>{window.claim=value;GameSession.accept(value);},value);
const roomClaim=(game,playMode,roomStatus)=>({
 claimId:game+'-'+playMode,game,playMode,roomStatus,roomId:game+'-room',code:'ABCD1234',
 credentials:{code:'ABCD1234',token:'test-only'},
 sourceAvailable:true,waitingExpiresAt:Date.now()+300000,serverTime:Date.now(),
 resumeUrl:game==='duel'?(playMode==='bot'?'/tran-dau/?bot=duel-bot':'/phong-dau/'):'/dau-tri/?game='+game+'&room='+game+'-room'
});
for(const [game,name] of Object.entries(gameNames)){
 const waiting=roomClaim(game,'human','waiting');
 await renderCard();
 if(game==='duel'){
  const requestKey=await page.evaluate(async value=>{
   window.claim=value;
   let key;
   await GameSession.admit('fixture',{},async requestKey=>{key=requestKey;return {gameClaim:value};});
   return key;
  },waiting);
  assert.match(requestKey,/^[a-f0-9-]{32,36}$/);
 }else await acceptClaim(waiting);
 assert(await popup.isVisible());
 assert(!(await inline.isVisible()));
 await page.evaluate(game=>{
  const url=game==='duel'?'/phong-dau/':'/dau-tri/?game='+game+'&room='+claim.roomId;
  history.replaceState(null,'',url);
  if(game==='duel')sessionStorage.setItem('5bmath-room',JSON.stringify(claim.credentials));
  GameSession.setRoomView({mode:game,id:claim.roomId,code:claim.code,status:'waiting'});
 },game);
 assert.equal(await popup.count(),0);
 await page.evaluate(()=>{
  history.replaceState(null,'','/tai-khoan/');
  document.querySelector('#app').innerHTML='<h1>Cá nhân</h1>';
  GameSession.setRoomView(null);
 });
 assert(await popup.isVisible());
 await acceptClaim({...waiting,roomStatus:'challenged'});
 assert(await popup.isVisible());
 await page.evaluate(game=>GameSession.setRoomView({mode:game,id:claim.roomId,code:claim.code,status:'preparing'}),game);
 assert.equal(await popup.count(),0);
 assert.equal(await inline.count(),0);
 await page.evaluate(()=>GameSession.setRoomView(null));
 await acceptClaim(waiting);
 assert.equal(await popup.count(),0,'older waiting observation cannot reopen an active room');
 await acceptClaim({...waiting,roomStatus:'preparing'});
 await renderCard();
 assert(await inline.isVisible());
 assert.equal(await inline.getAttribute('aria-label'),'Trận hiện tại · '+name);
 assert.match(await inline.textContent(),/luật bỏ trận/);
 await resume.focus();
 await page.evaluate(()=>window.focusedResume=document.activeElement);
 for(const roomStatus of ['playing','intermission']){
  await acceptClaim({...waiting,roomStatus});
  assert.equal(await popup.count(),0);
  assert(await page.evaluate(()=>focusedResume===document.activeElement&&focusedResume.isConnected));
  assert(await resume.isEnabled());
 }
 assert.equal(await page.evaluate(()=>GameSession.current.claimId),waiting.claimId);
 await acceptClaim({...waiting,roomStatus:'finished'});
 assert(!(await inline.isVisible()));
 assert.equal(await popup.count(),0);
 await acceptClaim({...waiting,roomStatus:'playing'});
 assert(!(await inline.isVisible()),'older active observation cannot reopen a finished room');
 await acceptClaim(null);
 const bot=roomClaim(game,'bot',game==='duel'?undefined:'playing');
 if(game==='duel')delete bot.roomStatus;
 await acceptClaim(bot);
 assert(await inline.isVisible());
 assert.equal(await popup.count(),0);
 await page.evaluate(()=>{failNext=true;return GameSession.refreshGlobal();});
 assert.equal(await popup.count(),0,'background read failure leaves the popup absent');
 await page.evaluate(()=>{
  history.replaceState(null,'','/hoc-theo-tuan/');
  document.querySelector('#app').innerHTML='<h1>Học theo tuần</h1>';
  return GameSession.mountGlobal();
 });
 assert.equal(await popup.count(),0);
 assert.equal(await inline.count(),0);
 assert.equal(await page.evaluate(()=>GameSession.current.claimId),bot.claimId);
 await acceptClaim(null);
}
checks.push('3games: human waiting/challenged → preparing/playing/intermission → finished, own waiting hidden, off-page active and BOT hidden, stale waiting suppression, inline focus preserved');
await renderCard();
const inaccessible={...roomClaim('duel','human',undefined),sourceAvailable:false};
await acceptClaim(inaccessible);
assert.equal(await popup.count(),0);assert(await inline.isVisible());
assert.equal(await resume.count(),0);assert.match(await inline.textContent(),/Nguồn câu chưa mở/);
await leave.click();
await inline.waitFor({state:'hidden'});
assert.equal(await page.evaluate(()=>calls.at(-1).body.claimId),inaccessible.claimId);
checks.push('unknown-status source-unavailable claim retains explicit inline leave');
const active=roomClaim('duel','bot',undefined);
await acceptClaim(active);
await page.evaluate(()=>{holdClaim=true;window.staleRequest=GameSession.refreshGlobal();});
await page.waitForFunction(()=>typeof resolveClaim==='function');
await page.evaluate(async()=>{
 PlatformAPI.familyContext='family-2';
 window.dispatchEvent(new Event('family-state-updated'));
 holdClaim=false;resolveClaim();await staleRequest;
});
assert.equal(await popup.count(),0);assert(!(await inline.isVisible()));assert.equal(await page.evaluate(()=>GameSession.current),null);
assert.equal(await page.evaluate(()=>sessionStorage.getItem('5bmath-game-claim')),null);
checks.push('late previous family-context response clears inline/popup/current even when account ID is unchanged');
const count=await page.evaluate(()=>calls.length);await page.evaluate(()=>{PlatformAPI.familyState={activeProfile:{type:'parent'},scope:'parent_full'};return GameSession.mountGlobal();});assert.equal(await page.evaluate(()=>calls.length),count);checks.push('parent commerce beneficiary never requests game-claim');
await page.evaluate(async()=>{
 PlatformAPI.familyState={activeProfile:{type:'child'},scope:'child'};
 window.claim=null;
 await GameSession.mountGlobal();
});
await acceptClaim(active);
await page.evaluate(()=>{window.claim={...claim,claimId:'new-claim'};});
await resume.click();
await page.waitForFunction(()=>GameSession.current.claimId==='new-claim');
assert(!page.url().includes('/tran-dau/'));
assert.equal(await page.evaluate(()=>sessionStorage.getItem('5bmath-bot-battle')),null);
assert.match(await inline.locator('[role="status"]').textContent(),/Trạng thái phòng đã thay đổi/);
await acceptClaim({...active,checkpointRevision:3,botBattle:{draftAnswer:'42'}});
await Promise.all([page.waitForURL('**/tran-dau/?bot=duel-bot'),resume.click()]);
assert.deepEqual(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('5bmath-bot-battle'))),{
 draftAnswer:'42',gameClaimId:'duel-bot',gameClaimRevision:3
});
checks.push('resume rejects a different claim generation and restores a matching BOT checkpoint/draft using GET');
assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify({status:'PASS',checks,pageErrors:errors,network:'all intercepted files/API fixtures; no live'},null,2));console.log(JSON.stringify({status:'PASS',checks,pageErrors:errors}));
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
