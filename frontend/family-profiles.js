'use strict';
(() => {
  if (window.FamilyProfiles) return;
  let state = {}, config = {}, revision = 0, pendingRefresh, pendingInit, dialog, opener, selected, afterUnlock;
  let requestQueue = Promise.resolve();
  const beforeRead = new WeakMap();
  let navigate = url => location.assign(url);
  const hosts = new Set();
  const source = Array.from(crypto.getRandomValues(new Uint32Array(3))).join('-');
  // First front-facing frame from the existing badge-mascot atlas metadata; no new bitmap assets.
  const portraits={cat:[1261,1247,44,40,231,263],rabbit:[1263,1245,84,31,185,272],horse:[1263,1246,42,35,235,248],voi:[1263,1246,39,94,238,195],tiger:[1261,1247,48,23,204,282],lion:[1263,1246,61,21,211,282],gau:[1263,1245,88,15,162,269],sparrow:[1271,1237,46,41,221,253],eagle:[1269,1240,43,51,263,245],'cu-meo':[1261,1247,50,36,214,265],butterfly:[1263,1246,51,40,207,222],bee:[1261,1247,47,35,243,238],'ca-map':[1261,1247,33,71,268,193],dolphin:[1262,1246,36,78,272,202],octopus:[1263,1246,35,40,252,239],crab:[1263,1246,52,73,240,211],starfish:[1263,1246,49,31,233,246],fox:[1263,1246,58,48,200,256],sprout:[1261,1247,81,8,190,275],dog:[1261,1247,60,26,196,254]};
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('5bmath-family-context') : null;
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  function emit(name, detail) { window.dispatchEvent(new CustomEvent(name, {detail})); }
  function profileOf(s = state) {
    if (s.activeProfile?.type) return s.activeProfile;
    if (s.activeProfile === 'parent' || ['parent_read','parent_full'].includes(s.scope)) return {type:'parent'};
    const id = s.activeProfile?.childId ?? s.activeProfile?.id ?? s.selectedChildId;
    return id ? {type:'child',childId:id} : {type:'parent'};
  }
  function isParent(s = state) { return profileOf(s).type === 'parent'; }
  function childOf(profile = profileOf(), s = state) { return (s.children || []).find(child => String(child.id) === String(profile.childId ?? profile.id)); }
  function companionAvatar(code) {
    code=Object.hasOwn(portraits,code)?code:'sprout';
    const [width,height,left,top,w,h]=portraits[code], ns='http://www.w3.org/2000/svg';
    const svg=document.createElementNS(ns,'svg'),img=document.createElementNS(ns,'image');
    svg.setAttribute('class','family-profile-avatar');svg.setAttribute('viewBox',[left-12,top-12,w+24,h+24].join(' '));svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
    img.setAttribute('href','/arena-art/badge-mascots/'+code+'.webp');img.setAttribute('width',width);img.setAttribute('height',height);svg.append(img);return svg;
  }
  function avatar(profile = profileOf(), s = state) {
    if (profile.type === 'child') { const child=childOf(profile,s); return companionAvatar(child?.mascotCode||child?.mascot||child?.avatar); }
    const img = el('img', undefined, 'family-profile-avatar'); img.alt = ''; img.width = 44; img.height = 44;
    const child = childOf(profile, s), companion = (config.companions || config.companionCatalog || []).find(item => item.code === (child?.mascotCode || child?.mascot || child?.companionCode));
    const path = profile.type === 'parent' ? '/family-parent.svg' : child?.avatarUrl || child?.mascotArtUrl || companion?.artUrl || companion?.artURL || companion?.imageUrl;
    img.src = typeof path === 'string' && /^\/(?!\/)/.test(path) ? path : '/family-parent.svg';
    return img;
  }
  function destination(s = state) {
    if (!s.authenticated || s.onboarding?.needsParentPin || s.onboarding?.needsChild || !s.children?.length) return '/gia-dinh/';
    return isParent(s) ? '/gia-dinh/?view=parent' : profileOf(s).type === 'child' ? '/tai-khoan/' : '/gia-dinh/';
  }
  function renderHost(host) {
    const signature = JSON.stringify([Boolean(state.authenticated),profileOf(),state.children?.map(child => [child.id,child.nickname,child.name,child.avatarUrl,child.mascotCode])]);
    if (host.dataset.familyProfileSignature === signature) return;
    host.dataset.familyProfileSignature = signature;
    host.replaceChildren(); host.hidden = !state.authenticated;
    if (!state.authenticated) return;
    const profile = profileOf(), b = el('button', undefined, 'family-profile-trigger'); b.type = 'button';
    const label = isParent() ? (host.classList.contains('app-bottom-profile')?'Phụ huynh':'Góc Phụ Huynh') : profile.type === 'profiles' ? 'Chọn hồ sơ' : childOf(profile)?.nickname || childOf(profile)?.name || 'Góc Học Tập';
    b.setAttribute('aria-haspopup','dialog'); b.setAttribute('aria-label', label + ' — Chuyển hồ sơ');
    const portrait=el('span',undefined,'family-profile-portrait'),cue=document.createElementNS('http://www.w3.org/2000/svg','svg');
    cue.setAttribute('viewBox','0 0 24 24');cue.setAttribute('class','family-profile-switch-cue');cue.setAttribute('aria-hidden','true');
    const tiles=document.createElementNS(cue.namespaceURI,'path');tiles.setAttribute('d','M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z');cue.append(tiles);
    portrait.append(avatar(profile),cue);b.append(portrait,el('span',label));b.title='Chọn hồ sơ khác';b.onclick=()=>open();host.append(b);
  }
  function mount(host) { if (!host) return; hosts.add(host); renderHost(host); }
  function accept(result, options = {}) {
    const next = result?.state || result; if (!next || !Object.hasOwn(next,'authenticated')) return state;
    const previous = state, changed = Boolean(previous.context && next.context !== previous.context);
    if (changed) revision++;
    state = next; hosts.forEach(host => { if (host.isConnected) renderHost(host); else hosts.delete(host); });
    emit('family-state-updated',{state,previous});
    if (previous.authenticated && !state.authenticated) emit('family-guest',{state,previous});
    if (options.refresh && changed) invalidate('context-changed', false);
    if (options.refresh && isParent(previous) && previous.scope === 'parent_full' && state.authenticated && state.scope !== 'parent_full') emit('family-privilege-expired',{state,previous});
    return state;
  }
  function invalidate(reason, clearState = true) {
    revision++; if (clearState) { state = {}; hosts.forEach(renderHost); }
    close(); emit('family-access-invalidated',{reason,state});
  }
  function request(action, data, {signal, expectedContext}={}) {
    const cancel=data===undefined&&(['cart','cart/catalog','parent/game-limits'].includes(action)||/^children\/game-limits\?childId=\d+$/.test(action))?signal:undefined;
    const next=requestQueue.then(() => {
      if (typeof expectedContext === 'string' && state.context !== expectedContext) {
        const error = new Error('Hồ sơ đã thay đổi. Vui lòng mở lại hồ sơ.');
        error.familyAccessChanged = true;
        throw error;
      }
      return performRequest(action,data,cancel);
    });
    requestQueue=next.catch(() => {}); return next;
  }
  async function performRequest(action, data, signal) {
    if(signal?.aborted)throw signal.reason;
    const headers = {Accept:'application/json'}; if (data !== undefined) { headers['Content-Type']='application/json'; headers['X-CSRF-Token']=state.csrf || ''; }
    if (state.context) headers['X-Family-Context']=state.context;
    const started = revision, controller = new AbortController(), timeout = setTimeout(() => controller.abort(),20000);
    const cancel=()=>controller.abort(signal.reason);
    signal?.addEventListener('abort',cancel,{once:true});
    try {
      const response = await fetch('/api/family/' + action,{method:data === undefined ? 'GET' : 'POST',credentials:'same-origin',cache:'no-store',headers,body:data === undefined ? undefined : JSON.stringify(data),signal:controller.signal});
      let result; try { result=await response.json(); } catch { throw new Error('Máy chủ chưa sẵn sàng. Vui lòng thử lại.'); }
      if(signal?.aborted)throw signal.reason;
      if (started !== revision) { const e = new Error('Hồ sơ đã thay đổi. Vui lòng mở lại hồ sơ.'); e.familyAccessChanged = true; throw e; }
      if (!response.ok) {
        const error = Object.assign(new Error(result.error || 'Chưa thể hoàn tất. Vui lòng thử lại.'),result,{status:response.status});
        if (error.familyAccessChanged) invalidate('server-context');
        else if (response.status === 401 && state.authenticated) { accept({authenticated:false}); }
        throw error;
      }
      if (action === 'config') { config = result; return result; }
      const before = state; if (action === 'state' && result && typeof result === 'object') beforeRead.set(result,before); accept(result);
      if (data !== undefined && (before.context !== state.context || ['register','login','logout','devices/logout-all','password'].includes(action))) channel?.postMessage({type:'changed',source});
      return result;
    } catch (error) {
      if(signal?.aborted)throw signal.reason;
      if (error.name === 'AbortError' || error instanceof TypeError) throw new Error('Kết nối bị gián đoạn. Vui lòng thử lại.');
      throw error;
    } finally { clearTimeout(timeout);signal?.removeEventListener('abort',cancel); }
  }
  async function refresh() {
    if (pendingRefresh) return pendingRefresh;
    pendingRefresh = (async () => { const result = await request('state'); const previous=beforeRead.get(result)||state, next = result.state || result;
      const expired = previous.scope === 'parent_full' && next.scope !== 'parent_full' && next.authenticated && isParent(next);
      if (expired) emit('family-privilege-expired',{state:next,previous});
      else if (previous.context && previous.context !== next.context) invalidate('context-changed', false);
      return next;
    })().finally(() => { pendingRefresh = null; }); return pendingRefresh;
  }
  function close() { if (dialog?.open) dialog.close(); }
  function ensureDialog() {
    if (dialog) return;
    dialog = el('dialog',undefined,'family-profile-dialog'); dialog.setAttribute('aria-labelledby','family-profile-title');
    dialog.addEventListener('close',() => { selected = null; afterUnlock = null; const focus = opener; opener = null; if (focus?.isConnected && (document.activeElement === document.body || document.activeElement === dialog)) focus.focus({preventScroll:true}); });
    dialog.addEventListener('keydown',event => {
      if (event.key !== 'Tab') return;
      const items = [...dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),a[href]')].filter(item => item.getClientRects().length);
      const first = items[0], last = items.at(-1);
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
    });
    dialog.addEventListener('click', e => { if (e.target === dialog) { const rect = dialog.getBoundingClientRect(); if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) close(); } });
    document.body.append(dialog);
  }
  function header(title) {
    dialog.replaceChildren(); const head = el('div',undefined,'family-profile-dialog-head'), h = el('h2',title); h.id = 'family-profile-title';
    const x = el('button','×','family-profile-close'); x.type='button'; x.setAttribute('aria-label','Đóng chọn hồ sơ'); x.onclick = close; head.append(h,x); dialog.append(head);
  }
  function picker() {
    selected = null; header('Mình dùng hồ sơ nào?'); dialog.append(el('p','Chọn hồ sơ của mình. Hồ sơ có PIN sẽ yêu cầu xác nhận.','family-profile-help'));
    const grid = el('div',undefined,'family-profile-grid');
    const profiles = [...(!state.device?.childOnly ? [{type:'parent'}] : []),...(state.children || []).map(child => ({type:'child',childId:child.id}))];
    const active=profileOf();
    profiles.forEach(profile => {
      const child=childOf(profile),b=el('button',undefined,'family-profile-choice');b.type='button';
      const current=active.type===profile.type&&(profile.type==='parent'||String(active.childId)===String(profile.childId));
      b.append(avatar(profile),el('strong',profile.type==='parent'?'Góc Phụ Huynh':child?.nickname||child?.name||'Con'));
      if(child)b.append(el('span','Lớp '+child.grade));
      if(current){b.disabled=true;b.classList.add('is-current');b.setAttribute('aria-current','true');b.setAttribute('aria-label',(profile.type==='parent'?'Góc Phụ Huynh':child?.nickname||child?.name||'Con')+' — hồ sơ đang mở');}
      else b.onclick=()=>pinForm(profile);
      grid.append(b);
    });
    dialog.append(grid); (dialog.querySelector('.family-profile-choice:not(:disabled)')||dialog.querySelector('.family-profile-close'))?.focus();
  }
  async function selectWithoutPin(profile) {
    const child=childOf(profile);if(!child)return picker();
    header('Đang mở góc của '+(child.nickname||child.name||'con'));dialog.append(el('p','Đang chuyển hồ sơ…','family-profile-help'));
    try{
      const previous=state,result=await request('select',{childId:child.id}),callback=afterUnlock;
      close();emit('family-profile-changed',{state,previous});if(callback)await callback(result);else navigate(destination());
    }catch(error){
      if(!dialog.open)return;
      header('Chưa thể mở hồ sơ');dialog.append(el('p',error.message,'family-profile-error'));
      const retry=el('button','Thử lại');retry.type='button';retry.onclick=async()=>{try{await refresh();if(dialog.open)pinForm(profile);}catch(e){dialog.querySelector('.family-profile-error').textContent=e.message;}};
      const back=el('button','Chọn hồ sơ khác','family-profile-back');back.type='button';back.onclick=picker;dialog.append(retry,back);retry.focus();
    }
  }
  function pinForm(profile) {
    selected = profile; const parent = profile.type === 'parent', child = childOf(profile);
    header(parent ? 'Mở Góc Phụ Huynh' : 'Mở góc học của ' + (child?.nickname || child?.name || 'con'));
    if (parent && !state.parentPinSet) { dialog.append(el('p','Ba mẹ cần thiết lập PIN phụ huynh trước.')); const go = el('a','Thiết lập PIN phụ huynh'); go.href='/gia-dinh/'; dialog.append(go); go.focus(); return; }
    if (!parent && child && !child.pinSet) return selectWithoutPin(profile);
    const form = el('form',undefined,'family-profile-pin-form'), label = el('label'), input = el('input');
    label.append(el('span',parent ? 'PIN phụ huynh · 6 số' : 'PIN của con')); input.type='password'; input.name='pin'; input.inputMode='numeric'; input.autocomplete='off'; input.required=true; input.maxLength=6; input.pattern=parent ? '[0-9]{6}' : '[0-9]{4,6}'; label.append(input);
    const help = el('p',parent ? 'PIN mở các chức năng quản lý của ba mẹ.' : 'Dùng PIN riêng của hồ sơ này.','family-profile-help');
    const error = el('p',undefined,'family-profile-error'); error.setAttribute('role','alert');
    const submit = el('button',parent ? 'Mở Góc Phụ Huynh' : 'Vào góc học'); submit.type='submit';
    const back = el('button','Chọn hồ sơ khác','family-profile-back'); back.type='button'; back.onclick=picker;
    form.append(label,help,error,submit,back); dialog.append(form);
    let submitting = false;
    form.onsubmit=async event => { event.preventDefault(); if (submitting || !form.reportValidity()) return; submitting=true; submit.disabled=true; error.textContent='';
      try {
        const previous = state, result = await request(parent ? 'parent/unlock' : 'select', parent ? {pin:input.value} : {childId:child.id,pin:input.value});
        const callback = afterUnlock; input.value=''; close(); emit('family-profile-changed',{state,previous});
        if (callback) await callback(result); else navigate(destination());
      } catch (e) { if (form.isConnected) { error.textContent=e.message; input.select(); input.focus(); } }
      finally { submitting=false; submit.disabled=false; }
    }; input.focus();
  }
  function open(options = {}) {
    if (!state.authenticated) { navigate('/gia-dinh/'); return; }
    ensureDialog(); opener = document.activeElement; afterUnlock = options.onSuccess || (options.stay ? () => {} : null);
    if (!dialog.open) dialog.showModal();
    if (options.target === 'parent') pinForm({type:'parent'}); else if (options.target?.type) pinForm(options.target); else picker();
  }
  async function initialize(options = {}) {
    if (options.navigate) navigate=options.navigate;
    if (options.config) config=options.config; else if (!Object.keys(config).length) await request('config');
    if (options.state) accept(options.state); else await request('state');
    document.querySelectorAll('[data-family-profile-menu]').forEach(mount); return state;
  }
  function init(options = {}) { if (pendingInit) return pendingInit; pendingInit = initialize(options).finally(() => { pendingInit = null; }); return pendingInit; }
  channel && (channel.onmessage = event => { if (event.data?.type === 'changed' && event.data.source !== source && state.authenticated) { invalidate('other-tab'); refresh().catch(() => {}); } });
  const resume = () => { if (state.authenticated && document.visibilityState !== 'hidden') refresh().catch(() => {}); };
  window.addEventListener('focus',resume); document.addEventListener('visibilitychange',resume); window.addEventListener('pageshow',event => { if (event.persisted) resume(); });
  // GET state does not renew parent privilege; detect expiry while an idle form stays open.
  setInterval(() => { if (state.scope === 'parent_full') resume(); },15000);
  window.FamilyProfiles = {source,init,mount,open,close,request,accept,refresh,destination,avatar,companionAvatar,profileOf,get state(){return state;},get config(){return config;},get ready(){return pendingInit || pendingRefresh || Promise.resolve(state);}};
})();
