'use strict';
const GameSession=(()=>{
 const browser=typeof document!=='undefined',e=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let mounted=false,generation=0,current=null,watcher=null,shown=null,admission=null,globalTimer=null,countdownTimer=null,mountProfile=null,pendingGet=null,roomView=null,clockSkew=0,expiryRefresh=null,leaving=null,roomProgress=null,claimVersion=0;
 const names={duel:'Đấu trí',capture_flag:'Cướp Cờ',animal_race:'Đua Thú'};
 const inlineSelector='[data-game-session-inline]';
 const inlineViews=new WeakMap();
 const startedStatuses=['preparing','playing','intermission'];
 const closedStatuses=['finished','cancelled','expired','left'];
 const owner=()=>typeof PlatformAPI!=='undefined'?PlatformAPI.snapshot.account?.id:null;
 function childAllowed(){const family=typeof PlatformAPI!=='undefined'?PlatformAPI.familyState:null;return Boolean(owner()&&PlatformAPI.snapshot.authenticated!==false&&(!family||(family.activeProfile?.type==='child'&&family.scope==='child')));}
 function profile(){return {owner:owner(),expectedFamilyContext:PlatformAPI.familyContext,expectedCsrf:PlatformAPI.snapshot.csrf};}
 function sameProfile(value){return Boolean(value&&childAllowed()&&value.owner===owner()&&value.expectedFamilyContext===PlatformAPI.familyContext&&value.expectedCsrf===PlatformAPI.snapshot.csrf);}
 function requestKey(){if(typeof crypto.randomUUID==='function')return crypto.randomUUID();const bytes=crypto.getRandomValues(new Uint8Array(16));return Array.from(bytes,n=>n.toString(16).padStart(2,'0')).join('');}
 async function request(route,body){if(!childAllowed())throw new DOMException('Phiên học sinh đã thay đổi.','AbortError');const context=profile();const result=await PlatformAPI.request(route,body,context);if(!sameProfile(context))throw new DOMException('Phiên tài khoản đã thay đổi.','AbortError');return result;}
 function accept(claim){
  claimVersion++;
  if(current?.claimId!==claim?.claimId)roomProgress=null;
  current=claim||null;
  if(Number.isFinite(claim?.serverTime))clockSkew=claim.serverTime-Date.now();
  if(!current||current.claimId!==expiryRefresh)expiryRefresh=null;
  if(browser)try{sessionStorage.setItem('5bmath-game-claim',JSON.stringify({owner:owner(),claim:current}));}catch{}
  if(browser&&mounted)show(current);
  return current;
 }
 async function get(){
  if(sameProfile(pendingGet?.profile)&&pendingGet.generation===generation&&pendingGet.claimVersion===claimVersion)return pendingGet.promise;
  if(!childAllowed())throw new DOMException('Phiên học sinh đã thay đổi.','AbortError');
  const entry={profile:profile(),generation,claimVersion,promise:null};
  entry.promise=(async()=>{try{const result=await request('game-claim');if(entry.generation!==generation||!sameProfile(entry.profile))throw new DOMException('Phiên đã thay đổi.','AbortError');return entry.claimVersion===claimVersion?accept(result.claim):current;}finally{if(pendingGet===entry)pendingGet=null;}})();pendingGet=entry;return entry.promise;
 }
 function anchor(){let node=document.getElementById('game-session-floating');if(!node){node=document.createElement('aside');node.id='game-session-floating';node.className='game-session-floating';node.setAttribute('role','region');node.setAttribute('aria-label','Phòng đang mở');document.body.append(node);}return node;}
 function sameRoute(claim){if(!claim)return false;const url=new URL(location.href);if(claim.game!=='duel')return url.pathname==='/dau-tri/'&&url.searchParams.get('game')===claim.game&&url.searchParams.get('room')===String(claim.roomId);if(claim.playMode==='bot'){let b=null;try{b=JSON.parse(sessionStorage.getItem('5bmath-bot-battle')||'null');}catch{}return url.pathname.endsWith('/tran-dau/')&&(url.searchParams.get('bot')===claim.claimId||b?.gameClaimId===claim.claimId);}try{const room=JSON.parse(sessionStorage.getItem('5bmath-room')||'null');return /\/(phong-dau|tran-dau)\/$/.test(url.pathname)&&room?.code===(claim.code||claim.credentials?.code);}catch{return false;}}
 function observedStatus(claim){
  if(!roomView||roomView.owner!==owner()||roomView.mode!==claim.game)return null;
  const sameRoom=roomView.id!=null&&roomView.id===String(claim.roomId);
  const sameDuel=claim.game==='duel'&&roomView.code&&roomView.code===(claim.code||claim.credentials?.code);
  return sameRoom||sameDuel?roomView.status:null;
 }
 function roomPhase(claim){
  if(!claim?.claimId)return null;
  const observed=observedStatus(claim),status=claim.roomStatus;
  const known=roomProgress?.claimId===claim.claimId?roomProgress.phase:null;
  if(known==='closed'||closedStatuses.includes(status)||closedStatuses.includes(observed))return 'closed';
  if(known==='started'||claim.playMode==='bot'||startedStatuses.includes(status)||startedStatuses.includes(observed))return 'started';
  if(status==='waiting'||status==='challenged')return status;
  return 'unknown';
 }
 function ownWaitingRoom(claim){return claim.roomStatus==='waiting'&&observedStatus(claim)==='waiting'&&sameRoute(claim);}
 function setRoomView(room){
  roomView=room?{id:room.id==null?null:String(room.id),code:room.code,mode:room.mode,status:room.status,owner:owner()}:null;
  if(browser&&mounted)show(current);
 }
 function inlineMarkup(){return '<section class="game-session-inline" data-game-session-inline hidden></section>';}
 function actionButtons(canResume){return `${canResume?'<button type="button" class="btn dark" data-game-claim-resume>Tiếp tục</button>':''}<button type="button" class="btn outline" data-game-claim-leave>Rời phòng</button>`;}
 function syncInline(message){
  if(!browser)return;
  const phase=mounted&&sameProfile(mountProfile)?roomPhase(current):null;
  const claim=phase==='started'||phase==='unknown'?current:null;
  for(const node of document.querySelectorAll(inlineSelector)){
   if(!claim){
    if(!node.hidden)node.replaceChildren();
    node.hidden=true;
    inlineViews.delete(node);
    continue;
   }
   const title='Trận hiện tại · '+(names[claim.game]||'Trò chơi');
   const canResume=claim.sourceAvailable!==false;
   const human=claim.playMode==='human';
   const signature=JSON.stringify([generation,claim.claimId,title,canResume,human]);
   if(inlineViews.get(node)?.signature!==signature){
    node.innerHTML=`<strong>${e(title)}</strong>${!canResume?'<p>Nguồn câu chưa mở ở địa chỉ này. Em vẫn có thể rời phòng.</p>':''}${human?'<p>Rời trận đã bắt đầu với người được xử lý theo luật bỏ trận.</p>':''}<div class="game-session-inline-actions">${actionButtons(canResume)}</div><p data-game-claim-feedback role="status"></p>`;
    node.setAttribute('aria-label',title);
    inlineViews.set(node,{signature,claimId:claim.claimId,generation});
    node.hidden=false;
   }
   if(message)node.querySelector('[data-game-claim-feedback]').textContent=message;
  }
 }
 function tickCountdown(){if(!mounted||!current||current.roomStatus!=='waiting'||!Number.isFinite(current.waitingExpiresAt))return;const seconds=Math.max(0,Math.ceil((current.waitingExpiresAt-Date.now()-clockSkew)/1000)),node=document.querySelector('[data-game-claim-countdown]');if(node)node.textContent=seconds?Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0'):'Đang xác nhận đóng phòng…';if(!seconds&&expiryRefresh!==current.claimId){expiryRefresh=current.claimId;refreshGlobal();}}
 function hide(){if(browser)document.getElementById('game-session-floating')?.remove();shown=null;}
 function collapsed(claim){try{return sessionStorage.getItem('5bmath-room-minimized:'+owner()+':'+claim.claimId)==='1'||sameRoute(claim)&&sessionStorage.getItem('5bmath-room-minimized:'+owner()+':'+claim.claimId)!=='0';}catch{return sameRoute(claim);}}
 function minimize(value){if(!shown)return;try{sessionStorage.setItem('5bmath-room-minimized:'+owner()+':'+shown.claimId,value?'1':'0');}catch{}show(shown);}
 function show(claim,message){
  if(!browser||!mounted||!sameProfile(mountProfile)){hide();syncInline();return;}
  const phase=roomPhase(claim);
  // Room and occupancy reads can finish out of order. Keep UI progress for this claim.
  if((phase==='started'||phase==='closed')&&current?.claimId===claim.claimId)roomProgress={claimId:claim.claimId,phase};
  syncInline(claim&&current?.claimId===claim.claimId?message:undefined);
  if((phase!=='waiting'&&phase!=='challenged')||ownWaitingRoom(claim)){hide();return;}
  shown=claim;
  const node=anchor(),small=collapsed(claim),canResume=claim.sourceAvailable!==false;
  node.dataset.minimized=String(small);
  node.innerHTML=`<div class="game-session-heading"><strong>${e(names[claim.game]||'Trò chơi')} · ${phase==='waiting'?'Phòng đang chờ':'Phòng đang mở'}</strong><button type="button" class="btn outline" ${small?'data-game-claim-expand':'data-game-claim-minimize'} aria-label="${small?'Mở thông tin phòng':'Thu gọn thông tin phòng'}">${small?'Mở':'Thu gọn'}</button></div>${small?'':`<div class="game-session-details"><p>${e(message||'Tiếp tục phòng hiện có hoặc chủ động rời phòng trước khi đổi trò chơi.')}</p>${!canResume?'<p>Nguồn câu chưa mở ở địa chỉ này. Em vẫn có thể rời phòng.</p>':''}${phase==='waiting'?`${Number.isFinite(claim.waitingExpiresAt)?'<p>Phòng tự đóng sau <strong data-game-claim-countdown role="timer">…</strong></p>':''}<small>Rời phòng chờ không bị tính bỏ trận.</small>`:''}<div class="actions">${actionButtons(canResume)}</div><p data-game-claim-feedback role="status"></p></div>`}`;tickCountdown();
 }
 function conflict(error){const claim=error?.details?.gameClaim||error?.gameClaim||error?.claim;if(error?.status===409||claim){if(claim)accept(claim);show(claim,error?.message||error?.error);return true;}return false;}
 async function resume(claim){
  const latest=await get();
  if(!latest||latest.claimId!==claim.claimId||roomPhase(latest)==='closed'){
   show(latest,'Trạng thái phòng đã thay đổi. Em hãy chọn trận hiện đang mở.');
   return;
  }
  if(latest.sourceAvailable===false)return;
  const url=new URL(latest.resumeUrl,location.origin);
  if(url.origin!==location.origin||!['/dau-tri/','/phong-dau/','/tran-dau/'].includes(url.pathname))throw Error('Đường tiếp tục trận không hợp lệ.');
  if(latest.game==='duel'&&latest.playMode==='human'&&latest.credentials)sessionStorage.setItem('5bmath-room',JSON.stringify(latest.credentials));
  if(latest.game==='duel'&&latest.playMode==='bot'){sessionStorage.removeItem('5bmath-room');sessionStorage.setItem('5bmath-bot-battle',JSON.stringify({...latest.botBattle,gameClaimId:latest.claimId,gameClaimRevision:latest.checkpointRevision}));}
  location.assign(url.href);
 }
 async function leave(claim){if(leaving){if(leaving.claimId===claim.claimId)return leaving.promise;throw Error('Đang rời phòng trước đó. Em hãy chờ một chút.');}const entry={claimId:claim.claimId,generation,promise:null};leaving=entry;entry.promise=(async()=>{try{const result=await request('game-claim',{action:'leave',claimId:claim.claimId});if(entry.generation!==generation||current&&current.claimId!==claim.claimId)return result;accept(result.claim);if(claim.game==='duel'){if(claim.playMode==='bot'){const saved=sessionStorage.getItem('5bmath-bot-battle');if(saved)sessionStorage.setItem('5bmath-bot-battle-backup:'+owner()+':'+claim.claimId,saved);sessionStorage.removeItem('5bmath-bot-battle');}else sessionStorage.removeItem('5bmath-room');}unwatch();return result;}finally{if(leaving===entry)leaving=null;}})();return entry.promise;}
 function unwatch(){if(watcher){watcher.alive=false;clearInterval(watcher.timer);clearTimeout(watcher.saveTimer);watcher=null;}}
 function backupLegacy(){if(!browser)return;const raw=sessionStorage.getItem('5bmath-bot-battle');if(!raw)return;try{if(!JSON.parse(raw).gameClaimId&&!sessionStorage.getItem('5bmath-legacy-bot-backup:'+owner()))sessionStorage.setItem('5bmath-legacy-bot-backup:'+owner(),raw);}catch{}}
 function unmount(){generation++;mounted=false;mountProfile=null;clearInterval(globalTimer);clearInterval(countdownTimer);globalTimer=null;countdownTimer=null;unwatch();current=null;roomView=null;roomProgress=null;leaving=null;hide();syncInline();if(browser)try{sessionStorage.removeItem('5bmath-game-claim');}catch{}}
 async function refreshGlobal(){if(!mounted||document.hidden)return null;if(!sameProfile(mountProfile)){unmount();return null;}try{return await get();}catch(error){if(error.name!=='AbortError'&&mounted&&shown){const note=document.querySelector('#game-session-floating [data-game-claim-feedback]');if(note)note.innerHTML='Chưa cập nhật được phòng. <button type="button" class="btn outline" data-game-claim-retry>Thử lại</button>';}return null;}}
 async function mount(){if(!childAllowed()){unmount();return null;}if(mounted&&sameProfile(mountProfile)){show(current);return current;}unmount();mounted=true;mountProfile=profile();backupLegacy();globalTimer=setInterval(refreshGlobal,15000);countdownTimer=setInterval(tickCountdown,1000);return refreshGlobal();}
 async function admit(kind,values,send){if(admission?.busy){if(admission.kind===kind)return admission.promise;throw Error('Đang kiểm tra yêu cầu bắt đầu trước đó. Em hãy chờ một chút.');}const key=JSON.stringify(values);if(!admission||admission.kind!==kind||admission.key!==key)admission={kind,key,requestKey:requestKey(),busy:false};const active=admission;active.busy=true;active.promise=(async()=>{try{const result=await send(active.requestKey);if(!result.gameClaim?.claimId)throw Error('Máy chủ chưa xác nhận quyền giữ phòng. Hãy tải lại trang trước khi bắt đầu.');if(result.gameClaim)accept(result.gameClaim);admission=null;return result;}catch(error){if(error.status===409)admission=null;conflict(error);throw error;}finally{active.busy=false;}})();return active.promise;}
 function checkpoint(state){const value={...state};for(const key of ['questions','id','grade','mode','botLevel','gameClaimId','gameClaimRevision'])delete value[key];return value;}
 async function validateBot(state){if(!state?.gameClaimId){const raw=sessionStorage.getItem('5bmath-bot-battle');if(raw&&!sessionStorage.getItem('5bmath-legacy-bot-backup:'+owner()))sessionStorage.setItem('5bmath-legacy-bot-backup:'+owner(),raw);const claim=await get();if(claim){show(claim,'Có một trận đang mở. Phiên luyện Bot cũ không thể tiếp tục với cơ chế phòng mới.');return null;}show(null,'Phiên luyện Bot cũ không thể tiếp tục với cơ chế phòng mới. Dữ liệu cũ đã được giữ lại. Em có thể về sảnh và chủ động bắt đầu lượt mới theo hạn mức hiện có.');return null;}const claim=await get();if(!claim||claim.claimId!==state.gameClaimId||claim.game!=='duel'||claim.playMode!=='bot'||claim.sourceAvailable===false){show(claim,'Phiên luyện này không còn quyền điều khiển phòng. Tiếp tục phòng hiện có để đồng bộ.');return null;}if(claim.checkpointRevision>0&&state.gameClaimRevision!==claim.checkpointRevision){show(claim,'Tiến độ đã được cập nhật ở phiên khác. Tiếp tục trận đang mở để đồng bộ; chưa bắt đầu lượt mới.');return null;}return claim;}
 async function saveBot(claim,state){const result=await request('game-claim',{action:'touch',claimId:claim.claimId,expectedRevision:claim.checkpointRevision,state:checkpoint(state)});return result.claim;}
 function watchBot(claim,{state,onLost,onClaim}){
  unwatch();const initial=JSON.stringify(checkpoint(state()));const value={alive:true,claim,queued:initial,lastSent:initial,busy:false,timer:null,saveTimer:null};watcher=value;
  function schedule(){if(value.alive&&!value.saveTimer)value.saveTimer=setTimeout(()=>{value.saveTimer=null;touch(true);},350);}
  async function touch(withState){
   if(!value.alive||value.busy||document.hidden)return;value.busy=true;
   let sent='';
   try{
    const sending=state();if(!sending)return;
    if(withState)sent=JSON.stringify(checkpoint(sending));
    const next=withState?await saveBot(value.claim,sending):(await request('game-claim',{action:'touch',claimId:value.claim.claimId})).claim;
    if(!value.alive)return;
    if(!next||next.claimId!==value.claim.claimId){onLost(next);return;}
    if(!withState&&next.checkpointRevision!==value.claim.checkpointRevision){onLost(next,new Error('Tiến độ đã được cập nhật ở phiên khác. Tiếp tục trận để đồng bộ.'));return;}
    accept(next);value.claim=next;if(withState)value.lastSent=sent;onClaim?.(next,{checkpoint:withState});
   }catch(error){if(value.alive){conflict(error);onLost(error.details?.gameClaim||null,error);}}
   finally{value.busy=false;if(value.alive&&value.queued&&value.queued!==value.lastSent)schedule();}
  }
  value.timer=setInterval(()=>touch(false),20000);
  value.schedule=state=>{const packed=JSON.stringify(checkpoint(state));if(packed===value.queued||packed===value.lastSent)return;value.queued=packed;schedule();};
  return ()=>{if(watcher===value)unwatch();};
 }
 function changedBot(state){watcher?.schedule(state);}
 async function releaseBot(state,reason){unwatch();if(!state?.gameClaimId)return;try{const result=await request('game-claim',{action:'release',claimId:state.gameClaimId,reason});accept(result.claim);}catch(error){if(error.status===409){const claim=await get();if(claim?.claimId!==state.gameClaimId)return;}throw error;}}
 if(browser){
  window.addEventListener('focus',()=>refreshGlobal());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshGlobal();});
  window.addEventListener('family-access-invalidated',unmount);
  window.addEventListener('family-profile-changed',unmount);
  window.addEventListener('family-state-updated',()=>{if(mounted&&!sameProfile(mountProfile))unmount();});
  document.addEventListener('click',async event=>{
   if(!(event.target instanceof Element)||!mounted||!sameProfile(mountProfile)||!current)return;
   const section=event.target.closest(inlineSelector+',#game-session-floating');
   if(!section||section.hidden)return;
   const inline=inlineViews.get(section);
   if(inline?inline.generation!==generation||inline.claimId!==current.claimId:section.id!=='game-session-floating'||shown?.claimId!==current.claimId)return;
   if(event.target.closest('[data-game-claim-minimize]')){minimize(true);return;}
   if(event.target.closest('[data-game-claim-expand]')){minimize(false);return;}
   if(event.target.closest('[data-game-claim-retry]')){await refreshGlobal();return;}
   const button=event.target.closest('[data-game-claim-resume],[data-game-claim-leave]');
   if(!button||button.disabled)return;
   const claim=current,profileAtClick=mountProfile,generationAtClick=generation;
   const note=section.querySelector('[data-game-claim-feedback]');
   if(note)note.textContent='';
   button.disabled=true;
   try{
    if(button.hasAttribute('data-game-claim-resume'))await resume(claim);
    else await leave(claim);
   }catch(error){
    if(error.name!=='AbortError'&&generation===generationAtClick&&sameProfile(profileAtClick)&&current?.claimId===claim.claimId&&!conflict(error)){
     const feedback=(inline?section:document.getElementById('game-session-floating'))?.querySelector('[data-game-claim-feedback]');
     if(feedback)feedback.textContent=error.message;
    }
   }finally{if(button.isConnected)button.disabled=false;}
  });
 }
 return {accept,get,mount,mountGlobal:mount,unmount,unmountGlobal:unmount,refreshGlobal,requestKey,show,conflict,resume,leave,admit,validateBot,saveBot,watchBot,changedBot,releaseBot,unwatch,setRoomView,inlineMarkup,syncInline,get current(){return current;}};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=GameSession;
if(typeof window!=='undefined')window.GameSession=GameSession;
