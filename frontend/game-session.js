'use strict';
const GameSession=(()=>{
 const browser=typeof document!=='undefined',e=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let mounted=false,generation=0,current=null,watcher=null,shown=null,admission=null;
 const names={duel:'Đấu trí',capture_flag:'Cướp Cờ',animal_race:'Đua Thú'};
 const owner=()=>typeof PlatformAPI!=='undefined'?PlatformAPI.snapshot.account?.id:null;
 async function request(route,body){const id=owner();const result=await PlatformAPI.request(route,body,{owner:id});if(id!==owner())throw new DOMException('Phiên tài khoản đã thay đổi.','AbortError');return result;}
 function accept(claim){current=claim||null;if(browser)try{sessionStorage.setItem('5bmath-game-claim',JSON.stringify({owner:owner(),claim:current}));}catch{}return current;}
 async function get(){const g=generation,result=await request('game-claim');if(g===generation)accept(result.claim);return result.claim;}
 function anchor(){return document.querySelector('#game-claim-status');}
 function sameRoute(claim){if(!claim)return false;const url=new URL(location.href);if(claim.game!=='duel')return url.searchParams.get('game')===claim.game&&url.searchParams.get('room')===String(claim.roomId);if(claim.playMode==='bot'){let b=null;try{b=JSON.parse(sessionStorage.getItem('5bmath-bot-battle')||'null');}catch{}return url.pathname.endsWith('/tran-dau/')&&(url.searchParams.get('bot')===claim.claimId||b?.gameClaimId===claim.claimId);}try{const room=JSON.parse(sessionStorage.getItem('5bmath-room')||'null');return /\/(phong-dau|tran-dau)\/$/.test(url.pathname)&&room?.code===(claim.code||claim.credentials?.code);}catch{return false;}}
 function hide(){anchor()?.replaceChildren();shown=null;}
 function show(claim,message){if(!browser||!mounted||!anchor())return;shown=claim||null;const canResume=claim&&claim.sourceAvailable!==false;anchor().innerHTML=`<section class="card card-pad game-claim-notice" role="status"><h2>${claim?'Em đang có một trận đang mở':'Phiên luyện đã tạm dừng'}</h2><p>${e(message||`Em đang chơi ${names[claim?.game]||'trò chơi'}${claim?.playMode==='bot'?' với Bot':''}. Tiếp tục trận này hoặc chủ động rời phòng trước khi đổi trò chơi.`)}</p>${claim?.sourceAvailable===false?'<p>Nguồn câu của trận này chưa mở ở địa chỉ hiện tại. Em vẫn có thể chủ động rời trận.</p>':''}${claim?.playMode==='human'?'<small>Rời trận đang chơi với người có thể được xử lý là bỏ trận theo luật hiện có.</small>':''}<div class="actions">${canResume?'<button type="button" class="btn dark" data-game-claim-resume>Tiếp tục trận đang mở</button>':''}${claim?'<button type="button" class="btn outline" data-game-claim-leave>Rời trận đang mở</button>':'<a class="btn outline" href="/dau-tri/">Về sảnh trò chơi</a>'}</div><p data-game-claim-feedback role="status"></p></section>`;}
 function conflict(error){const claim=error?.details?.gameClaim||error?.gameClaim||error?.claim;if(error?.status===409||claim){if(claim)accept(claim);show(claim,error?.message||error?.error);return true;}return false;}
 async function resume(claim){const latest=await get();if(!latest||latest.claimId!==claim.claimId){show(latest,'Trạng thái phòng đã thay đổi. Em hãy chọn trận hiện đang mở.');return;}if(latest.sourceAvailable===false){show(latest);return;}if(latest.game==='duel'&&latest.playMode==='human'&&latest.credentials)sessionStorage.setItem('5bmath-room',JSON.stringify(latest.credentials));if(latest.game==='duel'&&latest.playMode==='bot'){sessionStorage.removeItem('5bmath-room');sessionStorage.setItem('5bmath-bot-battle',JSON.stringify({...latest.botBattle,gameClaimId:latest.claimId,gameClaimRevision:latest.checkpointRevision}));}const url=new URL(latest.resumeUrl,location.origin);if(url.origin!==location.origin||!['/dau-tri/','/phong-dau/','/tran-dau/'].includes(url.pathname))throw Error('Đường tiếp tục trận không hợp lệ.');location.assign(url.href);}
 async function leave(claim){const result=await request('game-claim',{action:'leave',claimId:claim.claimId});accept(result.claim);if(claim.game==='duel'){if(claim.playMode==='bot'){const saved=sessionStorage.getItem('5bmath-bot-battle');if(saved)sessionStorage.setItem('5bmath-bot-battle-backup:'+owner()+':'+claim.claimId,saved);sessionStorage.removeItem('5bmath-bot-battle');}else sessionStorage.removeItem('5bmath-room');}unwatch();show(null,'Đã rời trận. Em có thể chọn cách chơi để bắt đầu lượt mới.');return result;}
 function unwatch(){if(watcher){watcher.alive=false;clearInterval(watcher.timer);clearTimeout(watcher.saveTimer);watcher=null;}}
 function backupLegacy(){if(!browser)return;const raw=sessionStorage.getItem('5bmath-bot-battle');if(!raw)return;try{if(!JSON.parse(raw).gameClaimId&&!sessionStorage.getItem('5bmath-legacy-bot-backup:'+owner()))sessionStorage.setItem('5bmath-legacy-bot-backup:'+owner(),raw);}catch{}}
 function unmount(){generation++;mounted=false;unwatch();}
 async function mount(){unmount();mounted=true;const g=generation;if(!owner())return null;backupLegacy();try{const claim=await get();if(g!==generation||!mounted)return null;if(claim&&!sameRoute(claim))show(claim);return claim;}catch(error){if(error.name!=='AbortError'&&g===generation)show(null,'Chưa kiểm tra được phòng đang mở. Thử kết nối lại trước khi bắt đầu.');return null;}}
 async function admit(kind,values,send){if(admission?.busy){if(admission.kind===kind)return admission.promise;throw Error('Đang kiểm tra yêu cầu bắt đầu trước đó. Em hãy chờ một chút.');}const key=JSON.stringify(values);if(!admission||admission.kind!==kind||admission.key!==key)admission={kind,key,requestKey:crypto.randomUUID(),busy:false};const active=admission;active.busy=true;active.promise=(async()=>{try{const result=await send(active.requestKey);if(!result.gameClaim?.claimId)throw Error('Máy chủ chưa xác nhận quyền giữ phòng. Hãy tải lại trang trước khi bắt đầu.');if(result.gameClaim)accept(result.gameClaim);admission=null;hide();return result;}catch(error){if(error.status===409)admission=null;conflict(error);throw error;}finally{active.busy=false;}})();return active.promise;}
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
 if(browser)document.addEventListener('click',async event=>{const resumeButton=event.target.closest('[data-game-claim-resume]'),leaveButton=event.target.closest('[data-game-claim-leave]');if(!resumeButton&&!leaveButton)return;const button=resumeButton||leaveButton,claim=shown;if(!claim)return;button.disabled=true;try{if(resumeButton)await resume(claim);else await leave(claim);}catch(error){if(!conflict(error)){const note=anchor()?.querySelector('[data-game-claim-feedback]');if(note)note.textContent=error.message;}}finally{if(button.isConnected)button.disabled=false;}});
 return {accept,get,mount,unmount,show,conflict,resume,leave,admit,validateBot,saveBot,watchBot,changedBot,releaseBot,unwatch,get current(){return current;}};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=GameSession;
if(typeof window!=='undefined')window.GameSession=GameSession;
