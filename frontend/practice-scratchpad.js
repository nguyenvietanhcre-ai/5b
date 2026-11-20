(function(global){
'use strict';
const PracticeScratchpad=(()=>{
 const entries=new Map(),prefix='5bmath-scratch-v1:';let stop=()=>{};
 const blank=()=>({version:1,open:false,text:'',color:'#203a32',strokes:[]});
 const pack=n=>({version:1,open:n.open,text:n.text,color:n.color,strokes:n.strokes});
 const copy=n=>JSON.parse(JSON.stringify(pack(n)));
 function valid(n){return n?.version===1&&typeof n.open==='boolean'&&typeof n.text==='string'&&n.text.length<=20000&&/^#[0-9a-f]{6}$/i.test(n.color)&&Array.isArray(n.strokes)&&n.strokes.every(l=>l&&/^#[0-9a-f]{6}$/i.test(l.color)&&Array.isArray(l.points)&&l.points.length&&l.points.every(p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=0&&p.x<=1&&p.y>=0&&p.y<=1));}
 function markup(){return '<section class="practice-scratch"><button type="button" class="btn outline" data-scratch-toggle aria-expanded="false" aria-controls="practice-scratch-panel">Nháp</button><div id="practice-scratch-panel" class="scratch-panel" hidden><canvas data-scratch-canvas width="1000" height="500" aria-label="Bảng trắng để vẽ nháp; có ô nhập văn bản bên dưới"></canvas><label class="field"><span>Nháp bằng văn bản</span><textarea data-scratch-text rows="5" maxlength="20000" placeholder="Gõ cách tính hoặc ghi chú của em…"></textarea></label><div class="scratch-tools"><label>Màu bút <input type="color" data-scratch-color value="#203a32"></label><button type="button" class="btn outline" data-scratch-undo>Hoàn tác nét</button><button type="button" class="btn outline" data-scratch-clear>Xóa nét vẽ</button></div><p data-scratch-status role="status" aria-live="polite"></p><div class="scratch-tools"><button type="button" class="btn outline" data-scratch-retry hidden>Thử đồng bộ lại</button><button type="button" class="btn outline" data-scratch-remote hidden>Dùng bản trên tài khoản</button><button type="button" class="btn outline" data-scratch-local hidden>Lưu bản nháp này</button></div></div></section>';}
 function mount(identity){
  stop();const el=document.querySelector('.practice-scratch');if(!el)return;
  const owner=typeof PlatformAPI!=='undefined'?PlatformAPI.snapshot.account?.id:null,parts=identity.split(':'),provider=parts[0],eid=parts[1],position=Number(parts[2]),key=prefix+JSON.stringify([owner??'offline',identity]);
  const familyContext=typeof PlatformAPI!=='undefined'?PlatformAPI.familyContext||'':'';
  const online=Boolean(owner&&PlatformAPI.enabled),url=(provider==='pilot'?'/api/local-pilot/':'/api/v1/')+'exams/'+encodeURIComponent(eid)+'/scratch';
  if(!entries.has(key)){
   let cache=null;try{const raw=localStorage.getItem(key);if(raw){const n=JSON.parse(raw);if(valid(n))cache=n;}}catch{}
   entries.set(key,{note:cache?copy(cache):blank(),revision:Number(cache?.serverRevision)||0,dirty:Boolean(cache?.pending),legacy:Boolean(cache&&!Object.hasOwn(cache,'serverRevision')),ready:!online,saving:null,loading:null,pending:null,conflict:null,error:false,notify:()=>{}});
  }
  const entry=entries.get(key),panel=el.querySelector('.scratch-panel'),toggle=el.querySelector('[data-scratch-toggle]'),canvas=el.querySelector('canvas'),ctx=canvas.getContext('2d'),text=el.querySelector('textarea'),color=el.querySelector('[data-scratch-color]'),status=el.querySelector('[data-scratch-status]'),retry=el.querySelector('[data-scratch-retry]'),remote=el.querySelector('[data-scratch-remote]'),local=el.querySelector('[data-scratch-local]');let stroke=null,pointer=null,timer=null,disposed=false;
  const cache=()=>{try{localStorage.setItem(key,JSON.stringify({...pack(entry.note),serverRevision:entry.revision,pending:entry.dirty,updatedAt:Date.now()}));return true;}catch{return false;}};
  const call=async(body,keepalive=false)=>{
   if(PlatformAPI.snapshot.account?.id!==owner||(PlatformAPI.familyContext||'')!==familyContext)throw new Error('Tài khoản đã thay đổi.');
   const response=await fetch(url+(body===undefined?'?position='+position:''),{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:{...(familyContext?{'X-Family-Context':familyContext}:{}),...(body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':PlatformAPI.snapshot.csrf||''})},body:body===undefined?undefined:JSON.stringify(body),keepalive});
   const result=await response.json();if(PlatformAPI.snapshot.account?.id!==owner||(PlatformAPI.familyContext||'')!==familyContext)throw new Error('Tài khoản đã thay đổi.');if(!response.ok)throw new Error(result.error||'Chưa thể lưu nháp.');return result;
  };
  const syncUI=()=>{
   if(disposed)return;const note=entry.note;
   panel.hidden=!note.open;toggle.setAttribute('aria-expanded',String(note.open));
   if(document.activeElement!==text)text.value=note.text;color.value=note.color;
   retry.hidden=!entry.error;remote.hidden=local.hidden=!entry.conflict;
   status.textContent=entry.conflict?'Nháp đã thay đổi ở nơi khác. Chọn bản muốn giữ trước khi lưu tiếp.':!online?'Nháp lưu trên trình duyệt này; cần đăng nhập để đồng bộ.':entry.error?'Chưa đồng bộ được. Bản nháp trên máy được giữ để thử lại.':!entry.ready?'Đang tải nháp theo tài khoản…':entry.dirty||entry.saving?'Đang lưu nháp theo tài khoản…':'Đã lưu nháp theo tài khoản.';
   const locked=online&&!entry.ready;text.disabled=color.disabled=locked;canvas.style.pointerEvents=locked?'none':'';el.querySelector('[data-scratch-clear]').disabled=locked;el.querySelector('[data-scratch-undo]').disabled=locked||!note.strokes.length;
  };
  const draw=()=>{ctx.clearRect(0,0,canvas.width,canvas.height);ctx.lineCap='round';ctx.lineJoin='round';for(const line of entry.note.strokes){ctx.strokeStyle=ctx.fillStyle=line.color;ctx.lineWidth=3;ctx.beginPath();const first=line.points[0];ctx.moveTo(first.x*canvas.width,first.y*canvas.height);for(const p of line.points.slice(1))ctx.lineTo(p.x*canvas.width,p.y*canvas.height);if(line.points.length===1){ctx.arc(first.x*canvas.width,first.y*canvas.height,1.5,0,Math.PI*2);ctx.fill();}else ctx.stroke();}syncUI();};
  const resize=()=>{const width=canvas.getBoundingClientRect().width;if(!width)return;const ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*ratio);canvas.height=Math.round(300*ratio);draw();};
  entry.notify=()=>{syncUI();resize();};
  const save=(keepalive=false)=>{
   clearTimeout(timer);timer=null;cache();
   if(!online){entry.dirty=false;syncUI();return Promise.resolve();}
   if(!entry.ready||entry.conflict||!entry.dirty)return entry.saving||Promise.resolve();
   if(entry.saving)return entry.saving;
   entry.saving=(async()=>{try{
    while(entry.dirty&&!entry.conflict){
     if(!entry.pending)entry.pending={position,revision:entry.revision,requestKey:crypto.randomUUID(),note:copy(entry.note)};
     const pending=entry.pending,result=await call(pending,keepalive);
     if(result.conflict){entry.conflict=result.scratch;entry.pending=null;break;}
     entry.revision=result.scratch.revision;entry.pending=null;entry.dirty=JSON.stringify(pack(entry.note))!==JSON.stringify(pending.note);entry.legacy=false;entry.error=false;cache();
    }
   }catch{entry.error=true;cache();}finally{entry.saving=null;entry.notify();}})();syncUI();return entry.saving;
  };
  const load=()=>{
   if(!online)return Promise.resolve();if(entry.loading)return entry.loading;
   entry.loading=(async()=>{try{
    if(entry.saving)await entry.saving;
    const result=await call(),server=result.scratch;
    if(server.note&&!valid(server.note))throw Error('Nháp tài khoản không hợp lệ.');
    const differs=server.note&&JSON.stringify(pack(entry.note))!==JSON.stringify(pack(server.note));
    if((entry.dirty||entry.legacy)&&server.note&&differs&& (entry.legacy||entry.revision!==server.revision)){entry.conflict=server;}
    else if(entry.dirty&&entry.revision===server.revision){}
    else if(server.note){entry.note=copy(server.note);entry.revision=server.revision;entry.dirty=false;entry.legacy=false;}
    else {entry.revision=0;entry.dirty=entry.dirty||entry.legacy;entry.legacy=false;}
    entry.ready=true;entry.error=false;cache();entry.notify();if(entry.dirty&&!entry.conflict)await save();
   }catch{entry.ready=true;entry.error=true;entry.notify();}finally{entry.loading=null;}})();return entry.loading;
  };
  const changed=()=>{entry.dirty=true;cache();clearTimeout(timer);timer=setTimeout(()=>save(),500);syncUI();};
  const point=ev=>{const rect=canvas.getBoundingClientRect();return {x:+Math.max(0,Math.min(1,(ev.clientX-rect.left)/rect.width)).toFixed(5),y:+Math.max(0,Math.min(1,(ev.clientY-rect.top)/rect.height)).toFixed(5)};};
  const finish=()=>{stroke=null;pointer=null;save();};
  canvas.onpointerdown=ev=>{if(ev.button!==0||pointer!==null||online&&!entry.ready)return;ev.preventDefault();pointer=ev.pointerId;canvas.setPointerCapture(pointer);stroke={color:entry.note.color,points:[point(ev)]};entry.note.strokes.push(stroke);draw();changed();};
  canvas.onpointermove=ev=>{if(!stroke||ev.pointerId!==pointer)return;ev.preventDefault();stroke.points.push(point(ev));draw();changed();};
  canvas.onpointerup=canvas.onpointercancel=canvas.onlostpointercapture=finish;
  toggle.onclick=()=>{entry.note.open=!entry.note.open;syncUI();resize();changed();};
  text.value=entry.note.text;text.oninput=()=>{entry.note.text=text.value;changed();};
  color.oninput=()=>{entry.note.color=color.value;changed();};
  el.querySelector('[data-scratch-undo]').onclick=()=>{stroke=null;pointer=null;entry.note.strokes.pop();draw();changed();save();};
  el.querySelector('[data-scratch-clear]').onclick=()=>{stroke=null;pointer=null;entry.note.strokes=[];draw();changed();save();};
  retry.onclick=async()=>{entry.error=false;await load();if(!entry.conflict)await save();};
  remote.onclick=()=>{entry.note=entry.conflict.note?copy(entry.conflict.note):blank();entry.revision=entry.conflict.revision;entry.conflict=null;entry.dirty=false;entry.pending=null;entry.legacy=false;cache();entry.notify();};
  local.onclick=()=>{entry.revision=entry.conflict.revision;entry.conflict=null;entry.pending=null;entry.dirty=true;cache();save();};
  const onHide=()=>{save(true);},onVisibility=()=>{if(document.hidden)save(true);else if(!entry.dirty&&!stroke)load();};
  window.addEventListener('pagehide',onHide);document.addEventListener('visibilitychange',onVisibility);
  const observer=new ResizeObserver(resize);observer.observe(canvas);syncUI();resize();load();
  stop=()=>{clearTimeout(timer);observer.disconnect();stroke=null;pointer=null;save();disposed=true;window.removeEventListener('pagehide',onHide);document.removeEventListener('visibilitychange',onVisibility);};
 }
 return {markup,mount,unmount:()=>{stop();stop=()=>{};}};
})();

'use strict';
global.PracticeScratchpad=PracticeScratchpad;
if(typeof module!=='undefined'&&module.exports)module.exports=PracticeScratchpad;

})(typeof globalThis!=='undefined'?globalThis:this);
