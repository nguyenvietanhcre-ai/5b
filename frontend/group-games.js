/* Five slots: explicitly selected human matches or labeled BOT practice. The server owns questions, time, steps, placement and rewards. */
(function(global){'use strict';
const modes={capture_flag:'Cướp Cờ',animal_race:'Đua Thú'},kinds={mascot:'Linh vật',duel:'Đấu trí',capture_flag:'Cướp Cờ',animal_race:'Đua Thú'};
const e=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const param=key=>new URLSearchParams(location.search).get(key);
const href=(mode,extra={})=>'/dau-tri/?'+new URLSearchParams({game:mode,...extra});
const rankHref=kind=>'/xep-hang/?'+new URLSearchParams({kind});
const uuid=()=>global.GameSession?.requestKey?.()||(typeof crypto.randomUUID==='function'?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join(''));
let host=null,owner=null,generation=0,controller=null,pollTimer=null,tickTimer=null,room=null,catalogue=null,mode=null,boardKind='mascot',busy=false,renderKey='',skew=0,roomDraft={round:0,value:''},answerPending=null,mutationPending=null,boardRows=[],boardTop=[],boardOffset=0,boardTotal=0,boardMore=false,showRest=false,dialogSeen=null;
let claimBlocked=false,gameVisual=null,activeQuestion=null,finishPaintRoom=null,finishTimer=null;
let visuals=[],onSessionUpdated=null,settledSessionRoom=null,lobbyTab='quick',lobbyRooms=[];
let allowance=null,familyContext=null,csrf=null;
const handles=route=>route==='rank'||(route==='arena'&&Object.hasOwn(modes,param('game')));
function tabs(selected='duel'){
 return `<nav class="group-game-tabs" aria-label="Trò chơi và bảng xếp hạng">${[['duel','Đấu trí','/dau-tri/'],['capture_flag','Cướp Cờ',href('capture_flag')],['animal_race','Đua Thú',href('animal_race')],['rank','Bảng xếp hạng','/xep-hang/']].map(([key,label,url])=>`<a href="${e(url)}" ${selected===key?'aria-current="page"':''}>${label}</a>`).join('')}</nav><div class="game-audio-bar" data-games-audio-slot></div>`;
}
function shell(route){return `${tabs(route==='rank'?'rank':param('game'))}<section id="group-games" class="group-games" aria-busy="true"><p role="status">Đang kết nối trò chơi…</p></section>`;}
const q=selector=>host?.querySelector(selector);
function valid(){return host?.isConnected&&owner===PlatformAPI.snapshot.account?.id&&familyContext===PlatformAPI.familyContext&&csrf===PlatformAPI.snapshot.csrf;}
async function api(path,body){
 const g=generation;
 try{const value=await PlatformAPI.request('group-games/'+path,body,{owner,expectedFamilyContext:familyContext,expectedCsrf:csrf,signal:controller.signal});
 if(g!==generation||!valid())throw new DOMException('Phiên tài khoản đã thay đổi.','AbortError');
 if(body!==undefined&&['quick','rooms','join'].includes(path)&&!value.gameClaim?.claimId)throw new Error('Máy chủ chưa xác nhận phòng chơi. Hãy tải lại trang.');
 if(Object.hasOwn(value,'gameClaim'))window.GameSession?.accept(value.gameClaim);
 return value;}catch(error){if(g===generation&&valid()&&error.status===409){claimBlocked=true;window.GameSession?.conflict(error);q('#group-answer-form')?.querySelectorAll('input,button').forEach(control=>control.disabled=true);}throw error;}
}
function destroyVisuals(){for(const visual of visuals)visual.destroy();visuals=[];gameVisual=null;}
function mountVisuals(){
 destroyVisuals();if(typeof GamesArt==='undefined')return;
 host.querySelectorAll('.garden-podium').forEach(element=>visuals.push(GamesArt.mountPodium(element,{players:podiumPlayers(),title:room?'Cùng chúc mừng các bạn!':'Những ngôi sao hôm nay',kind:room?room.mode:boardKind,metricLabel:room?(room.playMode==='bot'?'không tính XP':'kinh nghiệm nhận được'):boardKind==='mascot'?'kinh nghiệm':'điểm '+kinds[boardKind],captureWinner:room?.mode==='capture_flag'&&room?.endReason==='target_reached',confettiSeed:room?'result:'+room.id:'board:'+boardKind,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches})));
 host.querySelectorAll('canvas[data-group-art]').forEach(canvas=>{
  const podium=canvas.dataset.groupArt==='podium';
  const players=podium?(room?.rankings?.slice(0,3)||boardTop):room?.players||[];
  const normalize=p=>({id:p.studentId,name:p.name,mascotId:p.mascot||'sprout',mascotXp:p.mascotXp??p.xp??0,steps:p.steps||p.correct||0,rank:p.rank});
  const instance=GamesArt.mount(canvas,{mode:podium?'podium':mode,mapId:(room?.mapIndex??0)+1,players:players.map(normalize),winnerId:room?.winnerId,captureWinner:room?.mode==='capture_flag'&&room?.endReason==='target_reached',confettiSeed:room?'result:'+room.id:'board:'+boardKind,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,motionKey:room?'group:'+room.id+':'+mode+':'+room.mapIndex:null});visuals.push(instance);if(!podium)gameVisual=instance;
 });
}
function setError(message){if(!valid())return;let box=q('#group-error');if(!box){box=document.createElement('p');box.id='group-error';box.className='learning-notice group-error';box.setAttribute('role','alert');host.prepend(box);}box.textContent=message;}
function pageHeader(title,copy){return `<header class="group-page-heading"><div><h1>${e(title)}</h1>${copy?`<p>${e(copy)}</p>`:''}</div></header>`;}
function button(text,action,extra='',kind='dark'){return `<button type="button" class="btn ${kind}" data-group-action="${action}" ${extra}>${e(text)}</button>`;}
const lobbyIcons={search:'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0zm-2 5 6 6',friends:'M15 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m15-6a4 4 0 0 1 4 4v2M12 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zm4-4a4 4 0 0 1 0 8',flag:'M5 22V3h14l-3 5 3 5H5',cup:'M7 3h10v6a5 5 0 0 1-10 0z M7 5H3v2a4 4 0 0 0 4 4m10-6h4v2a4 4 0 0 1-4 4m-5 3v6m-4 1h8',arrow:'M4 12h15m-6-6 6 6-6 6',plus:'M5 12h14m-7-7v14',book:'M12 6C9 3 5 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-2-1-6-1-9 2zm0 0v14',down:'m6 9 6 6 6-6'};
function lobbyIcon(key,size=24){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${lobbyIcons[key]||lobbyIcons.cup}"/></svg>`;}
function lobbyPortrait(pet,xp,classes='mascot-art'){return typeof BadgeMascots!=='undefined'?BadgeMascots.portrait(pet,xp,'',classes):'';}
function ownListedRoom(value){try{const saved=JSON.parse(sessionStorage.getItem('5bmath-game-claim')||'null');if(saved?.owner!==PlatformAPI.snapshot.account?.id)return false;const claim=global.GameSession?.current||saved.claim;return claim?.game===mode&&(String(claim.roomId)===String(value.id)||(claim.code&&String(claim.code).toUpperCase()===String(value.code).toUpperCase()));}catch{return false;}}
function lobbyReady(){return catalogue?.ready&&catalogue.modes?.find(item=>item.key===mode)?.ready!==false;}
function openRoomRows(rows,filter=''){
 const filtered=rows.filter(r=>r.mine!==true&&!ownListedRoom(r)&&String(r.code).toLowerCase().includes(filter.toLowerCase()));
 const disabled=lobbyReady()?'':'disabled';
 return filtered.length?filtered.map(r=>`<article class="public-room group-public-room"><span class="group-public-room-art" aria-hidden="true">${lobbyIcon(mode==='capture_flag'?'flag':'cup',28)}</span><div><strong>Phòng ${e(r.code)}</strong><p>Khối ${e(r.grade)} · ${e(r.playerCount)}/5 người</p><small>Còn ${Math.max(0,5-Number(r.playerCount))} chỗ · Chờ đủ bạn để bắt đầu</small></div>${button('Tham gia','join',`data-game-admission data-code="${e(r.code)}" ${disabled}`,'dark')}</article>`).join(''):`<p class="group-rooms-empty">${filter?'Chưa tìm thấy phòng với mã này.':'Chưa có phòng đang chờ phù hợp. Em có thể tạo phòng và mời thêm bạn.'}</p>`;
}
function showLobbyTab(key){
 if(!['quick','friends','bot'].includes(key))return;lobbyTab=key;
 host.querySelectorAll('[data-group-lobby-tab]').forEach(tab=>{const selected=tab.dataset.groupLobbyTab===key;tab.classList.toggle('selected',selected);tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;});
 for(const item of ['quick','friends','bot']){const panel=q('#group-lobby-panel-'+item);if(panel)panel.hidden=item!==key;}
 const usage=q('#group-mode-usage');if(usage)usage.innerHTML=global.ArenaLobby.groupUsage(catalogue,key);
}
function gameRules(){return global.GameRules.markup(mode);}

function mascotCard(){
 const profile=PlatformAPI.snapshot.state||{};
 return global.ArenaLobby.playerCard({game:mode,mascot:profile.mascot||'sprout',xp:profile.points});
}
let preflightDialog=null;
function syncPreflightAllowance(){
 const note=preflightDialog?.querySelector('[data-preflight-allowance]');
 if(!note)return;
 const message=allowance?.errorMessage()||'';
 if(note.textContent!==message)note.textContent=message;
 note.hidden=!message;
}
function preflight({title='Sẵn sàng tạo phòng?',description='Chọn ai có thể vào phòng rồi xác nhận.',onConfirm}){
 if(preflightDialog?.open){preflightDialog.focus();return preflightDialog;}
 const dialog=document.createElement('dialog');preflightDialog=dialog;dialog.className='group-preflight-dialog';dialog.setAttribute('aria-label',title);
 dialog.innerHTML=`<form method="dialog"><p class="eyebrow">Trước khi tạo phòng</p><h2>${e(title)}</h2><p>${e(description)}</p><fieldset><legend>Ai có thể vào phòng?</legend><label><input type="radio" name="visibility" value="private" checked> Bạn bè có mã</label><label><input type="radio" name="visibility" value="public"> Tất cả</label></fieldset><p data-preflight-allowance role="status" hidden></p><p data-preflight-error role="alert" hidden></p><div class="actions"><button type="button" class="btn dark" data-preflight-confirm data-game-admission>Xác nhận & tạo phòng</button><button type="submit" class="btn outline" value="cancel">Quay lại</button></div></form>`;
 (host||document.body).append(dialog);
 dialog.addEventListener('close',()=>{if(preflightDialog===dialog)preflightDialog=null;dialog.remove();},{once:true});
 const confirm=dialog.querySelector('[data-preflight-confirm]'),error=dialog.querySelector('[data-preflight-error]');
 const setConfirmDisabled=disabled=>{
  if(allowance)global.GameAllowance.setDisabled(confirm,disabled);
  else confirm.disabled=disabled;
  dialog.querySelectorAll('input').forEach(input=>input.disabled=disabled);
 };
 confirm.onclick=async()=>{
  if(confirm.disabled||busy)return;
  setConfirmDisabled(true);error.hidden=true;
  try{
   const confirmed=await onConfirm({public:dialog.querySelector('[name=visibility]:checked').value==='public'},()=>dialog.open&&dialog.isConnected);
   if(confirmed!==false)dialog.close();
  }
  catch(problem){
   if(problem.name==='AbortError'){dialog.close();return;}
   syncPreflightAllowance();
   if(problem.message!==allowance?.errorMessage()){error.textContent=problem.message;error.hidden=false;}
  }finally{if(dialog.isConnected)setConfirmDisabled(false);}
 };
 allowance?.sync();syncPreflightAllowance();
 dialog.showModal();dialog.querySelector('[name=visibility]').focus();return dialog;
}
async function loadLobby(){
 catalogue=await api('catalogue');
 lobbyRooms=catalogue.ready?(await api('rooms?'+new URLSearchParams({mode}))).rooms:[];
 if(!valid())return;
 destroyVisuals();host.setAttribute('aria-busy','false');
 const profile=PlatformAPI.snapshot.state||{},pet=profile.mascot||'sprout',xp=Number(profile.points)||0;
 const ready=lobbyReady(),disabled=ready?'':'disabled',hasBot=catalogue.playModes?.includes('bot');
 const lobbyTabs=[['quick','search','Đấu nhanh'],['friends','friends','Mời bạn'],...(hasBot?[['bot','cup','Luyện với BOT']]:[])];
 host.innerHTML=`${pageHeader(modes[mode],mode==='capture_flag'?'Chọn cách chơi và cùng linh vật tiến về lá cờ Việt Nam.':'Chọn cách chơi và cùng linh vật chạy, bay, bơi về đích.')}
 <div class="arena-lobby group-styled-lobby">
  ${mascotCard()}${global.ArenaLobby.showcase(mode)}
  ${!ready?`<p class="learning-notice" role="status">${e(catalogue.reason||'Game đang chờ nguồn câu hỏi và chính sách lượt chơi được duyệt.')}</p>`:''}
  ${global.GameAllowance?global.GameAllowance.feedback?.(mode)||'':`<div class="arena-player-usage" id="group-mode-usage">${global.ArenaLobby.groupUsage(catalogue,lobbyTab)}</div>`}
  <div class="arena-modes group-lobby-modes ${hasBot?'group-with-bot':''}" role="tablist" aria-label="Cách chơi ${e(modes[mode])}">
   ${lobbyTabs.map(([key,icon,label])=>`<button type="button" role="tab" id="group-lobby-tab-${key}" data-group-lobby-tab="${key}" aria-controls="group-lobby-panel-${key}" aria-selected="${lobbyTab===key}" tabindex="${lobbyTab===key?'0':'-1'}" class="${lobbyTab===key?'selected':''}">${lobbyIcon(icon,25)}<span>${label}</span></button>`).join('')}
  </div>
  <section class="arena-mode-panel" id="group-lobby-panel-quick" role="tabpanel" aria-labelledby="group-lobby-tab-quick" ${lobbyTab==='quick'?'':'hidden'}>
   <h2 class="arena-panel-title">Tìm bạn cùng tranh tài</h2>
   <button type="button" class="arena-action arena-action-quick" data-group-action="quick" data-game-admission ${disabled}>${lobbyIcon('plus',30)}<span><strong>Tìm đối thủ</strong><small>Vào phòng đang chờ hoặc mở phòng công khai</small></span></button>
   <div class="section-head arena-rooms-heading"><h3>Phòng đang chờ</h3>${button('Tải lại','refresh','','outline')}</div>
   <section class="card card-pad group-room-browser"><label class="field group-room-search"><span>Tìm mã phòng</span><input type="search" id="group-room-search" placeholder="Nhập một phần mã phòng" autocomplete="off"></label><div id="group-open-room-list" aria-live="polite">${openRoomRows(lobbyRooms)}</div></section>
  </section>
  <section class="arena-mode-panel" id="group-lobby-panel-friends" role="tabpanel" aria-labelledby="group-lobby-tab-friends" ${lobbyTab==='friends'?'':'hidden'}>
   <h2 class="arena-panel-title">Cùng chơi với bạn</h2>
   <button type="button" class="arena-action arena-action-friends" data-group-action="create-friends" data-game-admission ${disabled}>${lobbyPortrait(pet,xp)}<span><strong>Rủ bạn cùng chơi</strong><small>Tạo phòng rồi chia sẻ mã mời các bạn cùng khối</small></span>${lobbyIcon('plus',24)}</button>
   <section class="card card-pad arena-join">
    <h3>Có mã phòng?</h3>
    <form id="group-join-form"><label class="field"><span>Mã phòng bạn gửi</span><input name="code" id="group-room-code" value="${e(param('code')||'')}" maxlength="40" required autocomplete="off" ${disabled}></label><button type="submit" class="btn dark" data-game-admission ${disabled}>Vào phòng</button></form>
    <small>Mỗi bạn đăng nhập một tài khoản. Trận bắt đầu ngay khi đủ 5 người.</small>
   </section>
  </section>
  ${hasBot?`<section class="arena-mode-panel group-bot-panel" id="group-lobby-panel-bot" role="tabpanel" aria-labelledby="group-lobby-tab-bot" ${lobbyTab==='bot'?'':'hidden'}><h2 class="arena-panel-title">Luyện cùng bốn BOT</h2><button type="button" class="arena-action arena-action-bot" data-group-action="create-bot" data-game-admission ${disabled}>${lobbyIcon('cup',30)}<span><strong>Bắt đầu luyện với Bot</strong></span></button></section>`:''}
  ${gameRules()}
 </div>`;
 global.GameSession?.syncInline?.();
 if(allowance){allowance.sync();void allowance.refresh();}
 else allowance=global.GameAllowance?.mount(mode,host,syncPreflightAllowance)||null;
 bind();
}
function ownPlayer(){return room?.players?.find(p=>p.mine||p.studentId===room.meStudentId);}
function msText(value){const ms=Math.max(0,Number(value)||0);return (ms/1000).toLocaleString('vi-VN',{maximumFractionDigits:2})+' giây';}
function rankedPlayers(){return [...(room.players||[])].sort((a,b)=>(Number(a.liveRank)||Number(a.seat)+1)-(Number(b.liveRank)||Number(b.seat)+1));}
function playerRow(p,index){return `<li data-player-id="${e(p.studentId)}" ${p.mine||p.studentId===room.meStudentId?'class="group-me"':''}><span class="group-seat">${index+1}</span><span class="group-player-name"><strong>${e(p.name)}</strong><small>${p.isBot?'BOT · ':''}${p.forfeited?'Đã rời trận':p.answered?(p.isBot&&typeof p.answerCorrect==='boolean'?(p.answerCorrect?'Đã trả lời · Đúng':'Đã trả lời · Sai'):'Đã trả lời'):'Đang chờ'}${p.mine||p.studentId===room.meStudentId?' · Em':''}</small></span><span class="group-step-count">${Number(p.steps)||0}/5 <small>bước</small></span></li>`;}
function playerList(){return `<ol class="group-player-list" aria-label="Thứ hạng hiện tại">${rankedPlayers().map(playerRow).join('')}${Array.from({length:Math.max(0,5-(room.players?.length||0))},()=>'<li class="group-slot"><span>+</span><span>Đang chờ bạn tham gia</span></li>').join('')}</ol>`;}
function syncPlayers(){
 const list=q('.group-player-list');if(!list)return;
 const before=new Map([...list.querySelectorAll('[data-player-id]')].map(n=>[n.dataset.playerId,n.getBoundingClientRect().top]));
 const nodes=new Map([...list.querySelectorAll('[data-player-id]')].map(n=>[n.dataset.playerId,n]));
 for(const [index,p]of rankedPlayers().entries()){
  let node=nodes.get(String(p.studentId));if(!node){const template=document.createElement('template');template.innerHTML=playerRow(p,index);node=template.content.firstElementChild;}
  node.classList.toggle('group-me',Boolean(p.mine||p.studentId===room.meStudentId));node.querySelector('.group-seat').textContent=String(index+1);
  node.querySelector('.group-player-name strong').textContent=p.name;
  node.querySelector('.group-player-name small').textContent=(p.isBot?'BOT · ':'')+(p.forfeited?'Đã rời trận':p.answered?(p.isBot&&typeof p.answerCorrect==='boolean'?(p.answerCorrect?'Đã trả lời · Đúng':'Đã trả lời · Sai'):'Đã trả lời'):'Đang chờ')+(p.mine||p.studentId===room.meStudentId?' · Em':'');
  node.querySelector('.group-step-count').firstChild.textContent=(Number(p.steps)||0)+'/5 ';
  if(list.children[index]!==node)list.insertBefore(node,list.children[index]||null);
 }
 if(!matchMedia('(prefers-reduced-motion: reduce)').matches)for(const node of list.querySelectorAll('[data-player-id]')){const old=before.get(node.dataset.playerId),delta=old-node.getBoundingClientRect().top;if(Number.isFinite(delta)&&Math.abs(delta)>1)node.animate?.([{transform:`translateY(${delta}px)`},{transform:'translateY(0)'}],{duration:360,easing:'cubic-bezier(.2,.7,.2,1)'});}
}
function stage(){const label=mode==='animal_race'&&global.RaceScenes?global.RaceScenes.themeFor((room.mapIndex??0)+1).name:'Bản đồ '+(Number(room.mapIndex)+1)+'/10';return `<section class="card group-stage-card" aria-label="Bản đồ ${e(modes[mode])}"><div class="group-stage-meta"><strong>${e(modes[mode])}</strong><span>${e(label)}</span></div><canvas class="group-stage" data-group-art="game" width="1200" height="720" role="img" aria-label="Vị trí linh vật; thứ hạng có trong danh sách bên dưới"></canvas></section>`;}
function question(){
 const own=ownPlayer(),question=activeQuestion;
 if(roomDraft.round!==room.round){roomDraft={round:room.round,value:''};answerPending=null;}
 const disabled=busy||claimBlocked||own?.answered||own?.forfeited||room.status!=='playing';
 return `<section class="card card-pad group-question" data-round="${e(room.round)}" aria-labelledby="group-question-title"><div class="group-question-meta"><span class="tag sage">Câu ${e(room.round)}</span><span class="group-timer" id="group-question-time" role="timer" aria-label="Thời gian còn lại"></span></div><div class="group-question-content"><h2 id="group-question-title">${e(question?.text||'Câu này đã kết thúc')}</h2>${question?`<form id="group-answer-form">${question.responseMode==='choice'?`<fieldset class="group-choices"><legend>Chọn đáp án để gửi ngay</legend>${(question.options||[]).map((choice,i)=>`<label><input type="radio" name="answer" value="${e(choice)}" ${roomDraft.value===choice?'checked':''} ${disabled?'disabled':''} required><b>${'ABCD'[i]}.</b><span>${e(choice)}</span></label>`).join('')}</fieldset>`:`<label class="field"><span>Đáp án của em</span><input id="group-typed-answer" name="answer" type="text" autocomplete="off" maxlength="500" value="${e(roomDraft.value)}" ${disabled?'disabled':''} required aria-describedby="group-answer-guide"></label><p id="group-answer-guide">${e(question.inputGuide?.instruction||'Nhập một đáp số theo đề bài.')}</p>`}${question.responseMode==='choice'?'':`<button class="btn dark" type="submit" ${disabled?'disabled':''}>${own?.answered?'Đã gửi đáp án':'Gửi đáp án'}</button>`}</form>`:''}</div><section class="group-round-feedback" id="group-round-feedback" role="status" aria-live="polite" hidden><h2 id="group-feedback-title"></h2><p id="group-feedback-detail"></p><div class="group-round-next" hidden><span>Câu tiếp theo sau</span><strong id="group-next-count"></strong><span>giây</span></div></section></section>`;
}
function bindAnswerForm(){const form=q('#group-answer-form');if(!form||form.dataset.bound)return;form.dataset.bound='1';form.addEventListener('submit',submit);form.addEventListener('change',event=>{if(event.target.matches('input[type=radio][name=answer]'))submit({preventDefault(){},currentTarget:form});});form.addEventListener('input',event=>{if(event.target.name==='answer')roomDraft={round:room.round,value:event.target.value};});}
function syncQuestion(){const position={left:scrollX,top:scrollY,behavior:'instant'};const clock=q('#group-question-time');if(clock)clock.hidden=room.status!=='playing';const slot=q('#group-question-slot');if(!slot)return;slot.style.minHeight=Math.max(parseFloat(slot.style.minHeight)||0,slot.getBoundingClientRect().height)+'px';if(slot.firstElementChild?.dataset.round!==String(room.round)){slot.innerHTML=question();bindAnswerForm();}const own=ownPlayer(),intermission=room.status==='intermission',disabled=busy||claimBlocked||own?.answered||own?.forfeited||room.status!=='playing';q('#group-answer-form')?.querySelectorAll('input,button').forEach(n=>n.disabled=Boolean(disabled));const submitButton=q('#group-answer-form [type=submit]');if(submitButton)submitButton.textContent=own?.answered?'Đã gửi đáp án':'Gửi đáp án';const feedback=q('#group-round-feedback');feedback.hidden=!intermission&&!own?.answered&&!own?.forfeited;feedback.dataset.outcome=own?.answerCorrect===true?'correct':own?.answerCorrect===false?'wrong':'waiting';q('#group-feedback-title').textContent=own?.forfeited?'Em đã rời trận':own?.answerCorrect===true?'Chính xác!':own?.answerCorrect===false?'Chưa đúng':intermission?'Đã hết thời gian':'Đã ghi nhận đáp án';q('#group-feedback-detail').textContent=own?.forfeited?'Em có thể xem kết quả.':intermission?'Sẵn sàng cho câu tiếp theo.':'Đang chờ kết quả câu này.';q('.group-round-next').hidden=!intermission;const card=q('.group-question'),content=q('.group-question-content');if(intermission&&!content.hidden)card.style.minHeight=card.getBoundingClientRect().height+'px';if(!intermission)card.style.minHeight='';content.hidden=intermission;window.scrollTo(position);}
function syncActiveRoom(){syncQuestion();syncPlayers();gameVisual?.update({players:(room.players||[]).map(p=>({id:p.studentId,name:p.name,mascotId:p.mascot||'sprout',mascotXp:p.mascotXp??p.xp??0,steps:p.steps||p.correct||0,rank:p.liveRank})),winnerId:room.winnerId});tick();}

function rankingsTable(rows){return `<div class="group-table-wrap"><table class="group-results-table"><thead><tr><th>Hạng</th><th>Người chơi / BOT</th><th>Đúng</th><th>Thời gian</th><th>Thưởng</th></tr></thead><tbody>${rows.map(p=>`<tr ${p.mine||p.studentId===room?.meStudentId?'class="mine"':''}><td>${e(p.rank)}</td><td><strong>${e(p.name)}</strong>${p.forfeited?'<small>Đã rời trận</small>':''}</td><td>${Number(p.correct)||0}</td><td>${msText(p.totalTimeMs)}${p.isBot?'<small>mô phỏng</small>':''}</td><td>${Number(p.xpAward??p.points??p.award??0)} XP</td></tr>`).join('')}</tbody></table></div>`;}
function podiumPlayers(){return (room?room.rankings?.slice(0,3)||[]:boardTop).map(p=>({id:p.studentId,name:p.name,mascotId:p.mascot||'sprout',mascotXp:p.mascotXp??p.xp??0,rank:p.rank,score:Number(room?p.xpAward??p.points:p.points)}));}
function podiumCanvas(){const options={title:room?'Cùng chúc mừng các bạn!':'Những ngôi sao hôm nay',kind:room?room.mode:boardKind,metricLabel:room?(room.playMode==='bot'?'không tính XP':'kinh nghiệm nhận được'):boardKind==='mascot'?'kinh nghiệm':'điểm '+kinds[boardKind],captureWinner:room?.mode==='capture_flag'&&room?.endReason==='target_reached'};return typeof GamesArt!=='undefined'&&GamesArt.podiumMarkup?GamesArt.podiumMarkup(podiumPlayers(),options):'<p role="status">Đang chuẩn bị bục chúc mừng…</p>';}
function endHeading(){return room.endReason==='target_reached'?'Chúc mừng những bước tiến của em!':room.endReason==='waiting_expired'?'Phòng chờ đã tự đóng':room.endReason==='source_exhausted'?'Trận đã dừng: hết nguồn câu hỏi':'Trận đã dừng';}
function finalPanel(){const normal=room.endReason==='target_reached';return `<section class="card card-pad group-finish"><h2>${endHeading()}</h2><p>${room.endReason==='waiting_expired'?'Đã hết 5 phút chờ. Em không bị tính bỏ trận và có thể tạo phòng mới.':room.playMode==='bot'?'Kết quả luyện với BOT':normal?'Kết quả và kinh nghiệm đã được máy chủ ghi nhận.':'Không có người giành cờ/về đích; trận này không tính thưởng.'}</p>${normal?button(room.playMode==='bot'?'Xem kết quả luyện':'Xem bục trao giải','podium','','outline'):''}${rankingsTable(room.rankings||[])}<a class="btn dark" href="${e(href(mode))}">Về sảnh ${e(modes[mode])}</a><a class="btn outline" href="${e(rankHref(mode))}">Bảng xếp hạng</a></section>${normal?`<dialog id="group-podium-dialog" class="group-podium-dialog" aria-labelledby="group-podium-title"><div class="group-podium-heading"><h2 id="group-podium-title">${e(mode==='capture_flag'?'Cờ đã tìm được chủ nhân!':'Cùng chúc mừng các tay đua!')}</h2>${button('Đóng','close-podium','','outline')}</div>${podiumCanvas()}<p>Mỗi bước tiến đều đáng tự hào. Cùng học và thử lại nhé!</p></dialog>`:''}`;}
function drawRoom(){
 const active=['playing','intermission'].includes(room.status),activeShell=q('#group-live-room');
 if(room.status==='finished'&&activeShell&&finishPaintRoom!==room.id){finishPaintRoom=room.id;syncActiveRoom();const id=room.id,g=generation;finishTimer=setTimeout(()=>{if(g===generation&&room?.id===id){renderKey='';drawRoom();}},950);return;}
 if(active&&activeShell?.dataset.roomId===String(room.id)){syncActiveRoom();return;}
 const key=JSON.stringify([room.id,room.status,room.round,room.endReason,room.players.map(p=>[p.studentId,p.steps,p.answered,p.forfeited]),room.rankings]);
 if(renderKey===key){tick();return;}renderKey=key;
 destroyVisuals();if(['finished','cancelled'].includes(room.status)||ownPlayer()?.forfeited)GamesArt?.clearMotion?.('group:'+room.id+':'+mode+':'+room.mapIndex);host.setAttribute('aria-busy','false');
 host.innerHTML=`${pageHeader(modes[mode],room.status==='waiting'?`Đang chờ ${room.players.length}/5 người`:room.status==='finished'?'Kết quả trận đấu':'')}${room.status==='waiting'?`<div class="group-waiting-actions" aria-label="Thao tác phòng chờ"><a class="btn dark" href="/tai-khoan/">Đi học tiếp</a>${button('Sao chép lời mời','copy','','outline')}${button('Rời phòng','leave','','outline')}</div>`:''}<div class="group-room-code ${room.status==='waiting'?'group-waiting-code':''}"><div><span>${room.playMode==='bot'?'Chế độ':'Mã phòng'}</span><strong>${room.playMode==='bot'?'Luyện với BOT':e(room.code)}</strong></div>${room.status==='waiting'?`<div class="group-waiting-details"><p>${room.public===true?'Tất cả có thể tìm thấy phòng này.':'Bạn bè có mã có thể vào phòng.'}</p><p>Phòng tự đóng sau <strong id="group-waiting-countdown" role="timer" aria-label="Thời gian chờ còn lại">…</strong></p><small>Rời phòng chờ không bị tính bỏ trận.</small></div>`:`<div class="actions">${room.playMode==='bot'?'':button('Sao chép lời mời','copy','','outline')}${room.status==='finished'||room.status==='cancelled'?'':button('Rời phòng','leave','','outline')}</div>`}</div>${room.status==='waiting'?`<section class="card card-pad group-joined-list"><h2>Người chơi đã tham gia · ${room.players.length}/5</h2>${playerList()}</section>`:room.status==='finished'||room.status==='cancelled'?finalPanel():`<div class="group-play-grid" id="group-live-room" data-room-id="${e(room.id)}"><div>${stage()}<div id="group-question-slot">${question()}</div></div><div>${playerList()}</div></div>`}`;
 bind();mountVisuals();if(active)syncActiveRoom();else tick();
 if(room.status==='finished'&&room.endReason==='target_reached'&&dialogSeen!==room.id){dialogSeen=room.id;showPodium();}
}
function showPodium(){const dialog=q('#group-podium-dialog');if(dialog&&!dialog.open){dialog.showModal();q('[data-group-action="close-podium"]')?.focus();}}
function tick(){if(!valid()||!room)return;const now=Date.now()+skew;const time=q('#group-question-time');if(time)time.textContent=Math.max(0,Math.ceil(((room.deadline||now)-now)/1000))+' giây';const next=q('#group-next-count');if(next)next.textContent=Math.max(0,Math.ceil(((room.nextAt||now)-now)/1000));const waiting=q('#group-waiting-countdown');if(waiting){const seconds=Math.max(0,Math.ceil((Number(room.waitingExpiresAt)-now)/1000));waiting.textContent=Number.isFinite(seconds)?Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0'):'…';}}
function acceptRoom(value){if(room&&room.id!==value.id){clearTimeout(finishTimer);finishPaintRoom=null;activeQuestion=null;}claimBlocked=false;room={...value,rankings:(value.rankings||[]).map(row=>({...value.players.find(p=>p.studentId===row.studentId),...row}))};skew=Number(room.serverTime)-Date.now();if(!Number.isFinite(skew))skew=0;mode=room.mode;if(value.question)activeQuestion=value.question;else if(roomDraft.round!==room.round)activeQuestion=null;drawRoom();window.GameSession?.setRoomView?.(room);if(room.playMode!=='bot'&&room.status==='finished'&&room.endReason==='target_reached'&&settledSessionRoom!==room.id){settledSessionRoom=room.id;refreshRewardSession(room.id);}}
async function refreshRewardSession(id){const g=generation;try{const snapshot=await PlatformAPI.request('session',undefined,{owner,signal:controller.signal});if(g!==generation||!valid()||room?.id!==id)return;onSessionUpdated?.(snapshot);}catch(error){if(g===generation&&valid()&&error.name!=='AbortError')setError('Kết quả trận đã lưu. Chưa tải lại được tổng kinh nghiệm; em có thể tải lại trang.');}}
async function poll(){if(!valid()||busy||claimBlocked||!room||['finished','cancelled'].includes(room.status))return;try{const result=await api('rooms/'+encodeURIComponent(room.id));acceptRoom(result.room);}catch(error){if(error.name!=='AbortError')setError('Kết nối tạm gián đoạn. Tiến độ vẫn do máy chủ giữ. '+error.message);}}
function setRoomURL(value){const url=new URL(location.href);url.search=new URLSearchParams({game:value.mode,room:value.id});history.replaceState(null,'',url);window.GameSession?.mountGlobal?.();}
async function mutate(kind,data,stillOpen=()=>true){
 if(busy)return;
 busy=true;
 const g=generation,admission=['quick','rooms','join'].includes(kind),currentAllowance=allowance;
 let submitted=false;
 try{
  if(admission){
   if(!lobbyReady())throw new Error(catalogue?.reason||'Trò chơi hiện chưa sẵn sàng.');
   const allowed=!currentAllowance||await currentAllowance.check();
   if(g!==generation||!valid()||!stillOpen())throw new DOMException('Phiên tạo hoặc vào phòng đã kết thúc.','AbortError');
   if(!allowed)return false;
  }
  if(!mutationPending||mutationPending.kind!==kind||JSON.stringify(mutationPending.data)!==JSON.stringify(data))mutationPending={kind,data,requestKey:uuid()};
  submitted=true;
  const result=await api(kind,{...data,requestKey:mutationPending.requestKey});
  mutationPending=null;busy=false;
  if(admission&&currentAllowance){
   const refreshed=currentAllowance.refresh();
   if(result.room)void refreshed.finally(()=>{
    if(allowance===currentAllowance){currentAllowance.unmount();allowance=null;}
   });
  }
  if(result.room){preflightDialog?.close();setRoomURL(result.room);renderKey='';acceptRoom(result.room);}
  return true;
 }catch(error){
  if(g===generation&&valid()){
   const parentLimit=admission&&(error.details?.code==='parent_game_limit'||error.code==='parent_game_limit');
   if(error.status===409||parentLimit)mutationPending=null;
   if(parentLimit)void currentAllowance?.refresh();
   if(admission&&submitted&&error.name!=='AbortError'&&(!error.status||error.status>=500)){
    void currentAllowance?.refresh();
    void global.GameSession?.refreshGlobal?.();
   }
  }
  throw error;
 }finally{if(g===generation)busy=false;}
}
async function submit(event){
 event.preventDefault();if(busy||claimBlocked||ownPlayer()?.answered)return;
 const value=new FormData(event.currentTarget).get('answer');if(value===null||!String(value).trim())return;
 roomDraft={round:room.round,value:String(value)};
 if(!answerPending||answerPending.round!==room.round)answerPending={round:room.round,answer:String(value),requestKey:uuid()};
 busy=true;q('#group-answer-form')?.querySelectorAll('input,button').forEach(n=>n.disabled=true);
 try{const result=await api('rooms/'+encodeURIComponent(room.id)+'/answer',answerPending);acceptRoom(result.room);}catch(error){if(error.name!=='AbortError'){setError(error.message);await poll();}}finally{busy=false;if(valid()&&room)syncQuestion();}
}
function reportError(error){if(error.name!=='AbortError')setError(error.message);}
function bind(){
 host.querySelectorAll('[data-group-lobby-tab]').forEach(tab=>tab.addEventListener('click',()=>showLobbyTab(tab.dataset.groupLobbyTab)));
 q('.group-lobby-modes')?.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;const tabs=[...host.querySelectorAll('[data-group-lobby-tab]')],current=tabs.indexOf(event.target);if(current<0)return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+1)%tabs.length;showLobbyTab(tabs[next].dataset.groupLobbyTab);tabs[next].focus();});
 const list=q('#group-open-room-list');
 q('#group-room-search')?.addEventListener('input',event=>{list.innerHTML=openRoomRows(lobbyRooms,event.target.value);allowance?.sync();});
 list?.addEventListener('click',event=>{
  const control=event.target.closest('[data-group-action="join"]');
  if(control&&!control.disabled)mutate('join',{code:control.dataset.code}).catch(reportError);
 });
 bindAnswerForm();
 q('#group-join-form')?.addEventListener('submit',event=>{
  event.preventDefault();
  if(event.currentTarget.querySelector('[type="submit"]').disabled)return;
  const code=String(new FormData(event.currentTarget).get('code')||'').trim();
  mutate('join',{code}).catch(reportError);
 });
 host.querySelectorAll('[data-group-action]:not([data-group-action="join"])').forEach(control=>control.addEventListener('click',async()=>{
  if(busy||control.disabled)return;const action=control.dataset.groupAction;
  try{
   if(action==='quick')await mutate('quick',{mode});
   if(action==='create'||action==='create-friends')preflight({title:'Sẵn sàng chơi '+modes[mode]+'?',onConfirm:(options,stillOpen)=>mutate('rooms',{mode,playMode:'human',public:options.public},stillOpen)});
   if(action==='create-bot')await mutate('rooms',{mode,playMode:'bot'});
   if(action==='refresh'){const g=generation;busy=true;try{await loadLobby();}finally{if(g===generation)busy=false;}}
   if(action==='copy'){const invitation=new URL(href(mode,{code:room.code}),location.origin).href;await navigator.clipboard.writeText(invitation);control.textContent='Đã sao chép';}
   if(action==='leave'){const isActive=room.status!=='waiting';if(isActive&&!confirm(room.playMode==='bot'?'Dừng lượt luyện với BOT?':'Rời trận sẽ không nhận kinh nghiệm. Em vẫn muốn rời?'))return;await mutate('rooms/'+encodeURIComponent(room.id)+'/leave',{});location.assign(href(mode));}
   if(action==='podium')showPodium();
   if(action==='close-podium')q('#group-podium-dialog')?.close();
   if(action==='more')await loadMore();
  }catch(error){reportError(error);}
 }));
 host.querySelectorAll('[data-group-rank]').forEach(control=>control.addEventListener('click',()=>{if(busy)return;boardKind=control.dataset.groupRank;showRest=false;boardRows=[];boardOffset=0;const url=new URL(location.href);url.search=new URLSearchParams({kind:boardKind});history.replaceState(null,'',url);loadBoard().catch(error=>setError(error.message));}));
}
function boardRow(p){return `<li class="group-board-row"><span class="group-rank-number">${e(p.rank)}</span><div><strong>${e(p.name)}</strong>${p.mine?'<small>Em</small>':''}</div><strong>${Number(p.points)||0}<small>${boardKind==='mascot'?'kinh nghiệm':'điểm'}</small></strong></li>`;}
function drawBoard(){
 destroyVisuals();host.setAttribute('aria-busy','false');
 host.innerHTML=`<header class="group-page-heading"><div><p class="eyebrow">Cùng học, cùng tiến bộ</p><h1>Bảng xếp hạng</h1><p>Tôn vinh những bước tiến của em. Chọn bảng để xem thành tích thật của từng cuộc chơi.</p></div></header><div class="group-rank-tabs" role="group" aria-label="Loại xếp hạng">${Object.entries(kinds).map(([key,label])=>`<button type="button" data-group-rank="${key}" aria-pressed="${boardKind===key}" class="${boardKind===key?'selected':''}">${lobbyIcon(key==='mascot'?'friends':key==='capture_flag'?'flag':'cup',22)}<span>${e(label)}</span></button>`).join('')}</div><section class="card group-board-podium" aria-label="Bục vinh danh ${e(kinds[boardKind])}">${podiumCanvas()}</section>${boardTotal>3?`<div class="group-board-more">${!showRest?button('Xem thêm từ hạng 4','more','','outline'):`<ol class="card group-board-rest" start="4">${boardRows.map(boardRow).join('')}</ol>${boardMore?button('Xem thêm','more','','outline'):'<p>Đã hiển thị hết bảng xếp hạng.</p>'}`}</div>`:''}`;
 bind();mountVisuals();
}
async function loadBoard(){
 const kind=boardKind,g=generation;const result=await api('leaderboard?'+new URLSearchParams({kind,offset:0,limit:20}));if(kind!==boardKind||g!==generation)return;
 boardTop=result.top3||[];boardRows=result.items||[];boardOffset=boardRows.length;boardTotal=result.total||0;boardMore=Boolean(result.hasMore);drawBoard();
}
async function loadMore(){if(!showRest){showRest=true;drawBoard();return;}busy=true;try{const result=await api('leaderboard?'+new URLSearchParams({kind:boardKind,offset:boardOffset,limit:20}));boardRows.push(...(result.items||[]));boardOffset=boardRows.length;boardMore=Boolean(result.hasMore);drawBoard();}finally{busy=false;}}
async function mount(route,sessionUpdated){
 unmount();host=document.getElementById('group-games');if(!host)return;
 const family=PlatformAPI.familyState;
 if(!PlatformAPI.snapshot.authenticated||!PlatformAPI.snapshot.account?.id||PlatformAPI.snapshot.familyParent||(family&&(family.activeProfile?.type!=='child'||family.scope!=='child')))return;
 owner=PlatformAPI.snapshot.account.id;familyContext=PlatformAPI.familyContext;csrf=PlatformAPI.snapshot.csrf;
 controller=new AbortController();onSessionUpdated=sessionUpdated;const g=generation;
 try{if(route==='rank'){boardKind=Object.hasOwn(kinds,param('kind'))?param('kind'):'mascot';await loadBoard();}else{mode=param('game');lobbyTab=param('code')?'friends':param('practice')==='bot'?'bot':'quick';const id=param('room');if(id){catalogue=await api('catalogue');const result=await api('rooms/'+encodeURIComponent(id));acceptRoom(result.room);}else await loadLobby();pollTimer=setInterval(poll,1000);tickTimer=setInterval(tick,250);}}
 catch(error){if(g===generation&&error.name!=='AbortError'){host.setAttribute('aria-busy','false');host.innerHTML=`${pageHeader(route==='rank'?'Bảng xếp hạng':modes[mode]||'Trò chơi','Chưa thể kết nối lúc này.')}<p class="learning-notice" role="alert">${e(error.message)}</p><a class="btn outline" href="${e(route==='rank'?'/xep-hang/':href(mode))}">Thử lại</a>`;}}
}
function unmount(){
 preflightDialog?.close();preflightDialog?.remove();preflightDialog=null;
 allowance?.unmount();allowance=null;generation++;clearTimeout(finishTimer);finishPaintRoom=null;controller?.abort();clearInterval(pollTimer);clearInterval(tickTimer);destroyVisuals();host=null;owner=null;familyContext=null;csrf=null;room=null;catalogue=null;busy=false;renderKey='';answerPending=null;mutationPending=null;roomDraft={round:0,value:''};activeQuestion=null;boardTop=[];boardRows=[];showRest=false;dialogSeen=null;onSessionUpdated=null;settledSessionRoom=null;lobbyRooms=[];lobbyTab='quick';window.GameSession?.setRoomView?.(null);
}
const apiPublic={handles,shell,tabs,mount,unmount,preflight};global.FivePlayerGames=apiPublic;if(typeof module!=='undefined'&&module.exports)module.exports=apiPublic;
})(typeof window!=='undefined'?window:globalThis);
