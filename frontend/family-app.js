'use strict';
(() => {
  const view = document.getElementById('family-view'), notice = document.getElementById('family-status'), profiles = window.FamilyProfiles;
  if (!view || !profiles) return;
  let busy = false, currentPage = '', protectedPage = false, suspended = null, childManagement = null, parentGameUsage = null;
  const gameNames = {duel: 'Đấu trí', capture_flag: 'Cướp Cờ', animal_race: 'Đua Thú'};
  const gameLimitIds = Object.keys(gameNames);
  const gameLimitsAction = 'children/game-limits';
  const gameUsageUnavailable = 'Chưa xem được lượt chơi.';
  const gameUsageLoading = 'Đang cập nhật lượt chơi…';
  let resetToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
  if(resetToken) history.replaceState(null,'','/gia-dinh/?mode=reset');
  const state = () => profiles.state, config = () => profiles.config;
  const node = (tag,text,cls) => { const n=document.createElement(tag); if(text !== undefined) n.textContent=String(text); if(cls)n.className=cls; return n; };
  function status(message='',error=false){notice.textContent=message;notice.dataset.error=String(error);}
  function syncShellView(){const map={parent:'overview','add-child':'addchild',devices:'account',account:'account',password:'account','delete-account':'account','logout-all':'account','parent-pin':'account','child-pin':'overview',cart:'cart','cart-locked':'cart'};if(state().authenticated)window.AppShell?.setView({role:'parent',view:map[currentPage]||'overview'});}
  function clear(page,privatePage=false){closeChildManagement(false);clearParentGameUsage();if(currentPage==='cart')window.FamilyCart?.unmount();view.replaceChildren();status();currentPage=page;protectedPage=privatePage;syncShellView();}
  function title(text,help){view.append(node('h2',text));if(help)view.append(node('p',help));}
  function button(text,action,cls=''){return UIControls.create(document,text,{className:cls,onClick:()=>run(action)});}
  function link(text,href){const a=node('a',text);a.href=href;return a;}
  function actions(...items){const row=node('div',undefined,'family-actions');row.append(...items);view.append(row);}
  function field(form,label,name,type='text',attrs={}){const wrap=node('label',undefined,'family-field'),input=node('input');input.type=type;input.name=name;input.required=attrs.required!==false;for(const [key,value] of Object.entries(attrs))if(key!=='required')input.setAttribute(key,value);wrap.append(node('span',label),input);form.append(wrap);return input;}
  function check(form,text,name,required=false,checked=false){const label=node('label',undefined,'family-check'),input=node('input');input.type='checkbox';input.name=name;input.required=required;input.checked=checked;label.append(input,node('span',text));form.append(label);return input;}
  function requestKey(){if(typeof crypto.randomUUID==='function')return crypto.randomUUID();const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const hex=Array.from(bytes,n=>n.toString(16).padStart(2,'0')).join('');return hex.slice(0,8)+'-'+hex.slice(8,12)+'-'+hex.slice(12,16)+'-'+hex.slice(16,20)+'-'+hex.slice(20);}
  function form(onSubmit,text){const f=node('form',undefined,'family-form'),submit=UIControls.create(document,text,{type:'submit'});f.addEventListener('submit',event=>{event.preventDefault();if(!f.reportValidity())return;const data=Object.fromEntries(new FormData(f));data.requestKey=f.requestKey ||= requestKey();run(()=>onSubmit(data,f));});return {f,submit};}
  async function run(action){if(busy)return;busy=true;status('Đang xử lý…');view.setAttribute('aria-busy','true');const buttons=[...view.querySelectorAll('button')].map(b=>({node:b,disabled:b.disabled,busy:b.getAttribute('aria-busy')}));buttons.forEach(({node:b,disabled})=>{b.disabled=true;if(!disabled)b.setAttribute('aria-busy','true');});try{await action();if(notice.textContent==='Đang xử lý…')status();}catch(e){if(e.familyAccessChanged){clearParentGameUsage();suspended=null;view.replaceChildren();protectedPage=false;title('Hồ sơ vừa thay đổi','Mở lại để dùng đúng hồ sơ trên máy này.');actions(button('Mở gia đình',async()=>{await profiles.refresh();await home();},'secondary'));}else if(e.status===401&&state().authenticated===false){login();}status(e.message||'Chưa thể kết nối. Vui lòng thử lại.',true);}finally{busy=false;view.removeAttribute('aria-busy');buttons.forEach(({node:b,disabled,busy})=>{b.disabled=disabled;if(busy===null)b.removeAttribute('aria-busy');else b.setAttribute('aria-busy',busy);});}}
  function legal(data){return {accepted:data.consent==='on',version:config().legalVersion,name:data.parentName||state().family?.parentName||state().family?.name||'Phụ huynh',contact:data.email||state().family?.email||'',role:'parent'};}
  async function api(action,data){return profiles.request(action,data);}
  function login(register=false){
    clear(register?'register':'login');title(register?'Cùng con bắt đầu':'Chào ba mẹ!',register?'Tạo tài khoản của ba mẹ, rồi mở góc học riêng cho con.':'Đăng nhập một lần, chọn đúng hồ sơ trên từng máy.');
    const tabs=node('div',undefined,'family-tabs');tabs.append(button('Đăng nhập',()=>login(false),register?'secondary':''),button('Đăng ký 5BMath',()=>login(true),register?'':'secondary'));view.append(tabs);
    const {f,submit}=form(async data=>{
      const payload={email:data.email,password:data.password,remember:data.remember==='on'};
      if(register){if(data.password!==data.confirm)throw new Error('Hai lần nhập mật khẩu chưa khớp.');Object.assign(payload,{requestKey:data.requestKey,legalConsent:legal(data)});}
      try{await api(register?'register':'login',payload);}catch(e){if(!register&&e.code==='family_device_limit'){deviceLimit(f,e);status(e.message,true);return;}throw e;}
      f.reset();if(state().onboarding?.needsChild||!state().children?.length)return addChild(true);
      if(profiles.profileOf().type==='child'&&new URLSearchParams(location.search).get('view')!=='cart')return location.assign(profiles.destination());
      return home();
    },register?'Tạo tài khoản':'Đăng nhập');
    field(f,'Email của ba mẹ','email','email',{autocomplete:'username',maxlength:254});
    field(f,'Mật khẩu 5BMath','password','password',{autocomplete:register?'new-password':'current-password',minlength:register?6:1,maxlength:128});
    if(register)field(f,'Nhập lại mật khẩu','confirm','password',{autocomplete:'new-password',minlength:6,maxlength:128});
    else f.append(button('Lấy lại mật khẩu',forgotPassword,'family-text-button'));
    if(register){f.append(node('p','Mật khẩu từ 6 ký tự.','family-help'),link('Điều khoản sử dụng','/dieu-khoan/'),link('Thông báo dữ liệu','/bao-ve-du-lieu/'));check(f,'Tôi là người lớn và đồng ý với điều khoản sử dụng, thông báo dữ liệu.','consent',true);}
    check(f,'Ghi nhớ tài khoản trên máy này trong 30 ngày','remember',false,true);f.append(submit);view.append(f);
    if(!register)view.append(node('p','Một gia đình dùng tối đa 3 thiết bị đăng nhập. Mỗi máy chọn hồ sơ riêng.','family-help'));
    view.append(node('hr',undefined,'family-divider'),link('Tài khoản hiện có / giáo viên','/?legacy_login=1'));
  }
  function deviceLimit(loginForm,error){
    loginForm.querySelector('[data-device-limit]')?.remove();const group=node('fieldset');group.dataset.deviceLimit='';group.append(node('legend','Gia đình đã đăng nhập đủ 3 máy'),node('p','Chọn một máy ngừng sử dụng và nhập PIN phụ huynh để thay. Các máy khác vẫn giữ đăng nhập.'));
    const label=node('label',undefined,'family-field'),select=node('select');select.name='replaceDeviceId';select.required=true;label.append(node('span','Máy muốn thay'),select);
    const placeholder=node('option','Chọn thiết bị');placeholder.value='';select.append(placeholder);for(const device of error.devices||[]){const option=node('option',device.name||'Thiết bị gia đình');option.value=String(device.id);select.append(option);}group.append(label);
    field(group,'PIN phụ huynh · 6 số','parentPin','password',{inputmode:'numeric',pattern:'[0-9]{6}',maxlength:6,autocomplete:'off'});
    const replace=node('button','Thay máy và đăng nhập');replace.type='button';replace.onclick=()=>run(async()=>{if(!loginForm.reportValidity())return;const current=Object.fromEntries(new FormData(loginForm));const payload={email:current.email,password:current.password,remember:current.remember==='on',replaceDeviceId:String(select.value),parentPin:current.parentPin};await api('login',payload);loginForm.reset();return home();});
    group.append(replace,button('Giữ các máy đang đăng nhập',()=>{group.remove();loginForm.querySelector('input[name=password]')?.focus();},'secondary'));loginForm.append(group);select.focus();
  }
  async function home(){
    const requestedView=new URLSearchParams(location.search).get('view');
    if(resetToken||new URLSearchParams(location.search).get('reset')==='1'||new URLSearchParams(location.search).get('mode')==='reset')return resetPassword();
    if(!state().authenticated){if(resetToken||new URLSearchParams(location.search).get('mode')==='reset'||new URLSearchParams(location.search).get('reset')==='1')return resetPassword();return login(new URLSearchParams(location.search).get('mode')==='register');}
    if(state().onboarding?.needsChild||!state().children?.length)return addChild(true);
    if(state().onboarding?.needsParentPin)return parentGate();
    if(requestedView==='cart'){
      if(state().device?.childOnly){clear('cart-locked');title('Giỏ hàng gia đình','Ba mẹ mở giỏ trên thiết bị được phép dùng hồ sơ phụ huynh.');return;}
      if(state().scope!=='parent_full'){lockedShell('cart');return profiles.open({target:'parent',stay:true,onSuccess:()=>navigate('cart',false)});}
      return navigate('cart',false);
    }
    if(profiles.profileOf().type==='parent'||['parent','overview','addchild','devices','account'].includes(requestedView))return full(()=>navigate(requestedView||'overview',false));
    clear('profiles');title('Mình dùng hồ sơ nào?','Mỗi con có góc học riêng. Chọn hồ sơ rồi nhập PIN của hồ sơ đó.');
    const grid=node('div',undefined,'family-grid');
    if(!state().device?.childOnly){const b=button('',()=>profiles.open({target:'parent',stay:true,onSuccess:()=>{history.replaceState(null,'','/gia-dinh/?view=parent');return parent();}}),'family-child');b.append(profiles.avatar({type:'parent'}),node('strong','Góc Phụ Huynh'));grid.append(b);}
    for(const child of state().children||[]){const b=button('',()=>profiles.open({target:{type:'child',childId:child.id}}),'family-child');b.dataset.childId=String(child.id);b.append(profiles.avatar({type:'child',childId:child.id}),node('strong',child.nickname||child.name),node('span','Lớp '+child.grade));grid.append(b);}view.append(grid);
    actions(button('Đăng xuất máy này',logout,'secondary'));
  }
  function full(next){return state().scope==='parent_full'?next():profiles.open({target:'parent',stay:true,onSuccess:next});}
  function parentGate(){if(state().scope==='parent_full')return parent();if(state().onboarding?.needsParentPin)return state().children?.length?setupExistingParent():addChild(true);lockedShell();profiles.open({target:'parent',stay:true,onSuccess:parent});}
  function setupExistingParent(){clear('setup-parent');title('Đặt PIN phụ huynh','Ba mẹ đặt PIN 6 số để mở các chức năng quản lý. Hồ sơ và tiến độ hiện có của con vẫn được giữ.');if(!state().onboarding?.canSetupParentPin){view.append(node('p','Ba mẹ cần đăng nhập lại để thiết lập PIN lần đầu.'));actions(button('Đăng nhập lại',logout));return;}const {f,submit}=form(async data=>{await api('parent/pin/setup',{pin:data.pin});f.reset();return parent();},'Lưu PIN phụ huynh');field(f,'PIN phụ huynh · 6 số','pin','password',{inputmode:'numeric',pattern:'[0-9]{6}',minlength:6,maxlength:6,autocomplete:'new-password'});f.append(submit);view.append(f);}
  function lockedShell(page){clearParentGameUsage();view.replaceChildren();status();currentPage=page==='cart'?'cart-locked':'parent-locked';protectedPage=false;syncShellView();title(page==='cart'?'Giỏ hàng gia đình':'Góc Phụ Huynh','Nhập PIN phụ huynh để tiếp tục.');actions(button('Mở bằng PIN phụ huynh',()=>profiles.open({target:'parent',stay:true,onSuccess:restoreParent})),button('Chọn hồ sơ',()=>profiles.open(),'secondary'));}
  function membershipLabel(value){return typeof value==='string'?value:value?.label||value?.name||value?.tier||value?.membership||'Chưa có thông tin';}
  function canReadGameUsage(context) {
    const s = state();
    return s.authenticated && s.scope === 'parent_full' && !s.parentLocked && !s.device?.childOnly &&
      profiles.profileOf(s).type === 'parent' && typeof context === 'string' && context !== '' && s.context === context;
  }
  function ownsGameUsageChild(childId) {
    return state().children?.some(child => String(child.id) === childId);
  }
  function isCurrentGameUsage(batch) {
    return parentGameUsage === batch && currentPage === 'parent' && protectedPage &&
      batch.familyId === state().family?.id && canReadGameUsage(batch.context);
  }
  function makeGameUsageCard(childId) {
    const region = node('section', undefined, 'family-game-usage');
    region.dataset.parentGameUsage = '';
    const heading = node('h4', 'Lượt chơi hôm nay');
    heading.id = 'family-game-usage-' + childId;
    region.setAttribute('aria-labelledby', heading.id);
    const feedback = node('p', undefined, 'family-game-usage-status');
    feedback.dataset.gameUsageStatus = '';
    feedback.setAttribute('role', 'status');
    const list = node('dl', undefined, 'family-game-usage-list');
    list.hidden = true;
    const rows = Object.entries(gameNames).map(([id, name]) => {
      const row = node('div'), pair = node('dd');
      const used = node('span'), remaining = node('span');
      row.dataset.gameId = id;
      used.dataset.gameUsed = '';
      remaining.dataset.gameRemaining = '';
      pair.append(used, remaining);
      row.append(node('dt', name), pair);
      list.append(row);
      return {id, used, remaining};
    });
    region.append(heading, feedback, list);
    return {region, feedback, list, rows};
  }
  function renderGameUsage(card, games, message = gameUsageUnavailable) {
    const ordered = Array.isArray(games) && gameLimitIds.map(id => games.find(game => game?.id === id));
    const ready = Boolean(ordered && ordered.every(game => game && Number.isSafeInteger(game.used) && game.used >= 0 &&
      (game.limit === null ? game.remaining === null : Number.isSafeInteger(game.limit) && game.limit >= 0 &&
        game.remaining === Math.max(0, game.limit - game.used))));
    card.list.hidden = !ready;
    card.feedback.hidden = ready;
    const feedbackText = ready ? '' : message;
    if (card.feedback.textContent !== feedbackText) card.feedback.textContent = feedbackText;
    for (const [index, row] of card.rows.entries()) {
      const game = ready ? ordered[index] : null;
      const usedText = game ? `Đã chơi ${game.used} lượt` : '';
      const remainingText = !game ? '' : game.remaining === null ? 'Không giới hạn' : `Còn ${game.remaining} lượt`;
      if (row.used.textContent !== usedText) row.used.textContent = usedText;
      if (row.remaining.textContent !== remainingText) row.remaining.textContent = remainingText;
      row.remaining.classList.toggle('is-exhausted', game?.remaining === 0);
    }
    return ready;
  }
  function clearParentGameUsage() {
    const batch = parentGameUsage;
    parentGameUsage = null;
    if (!batch) return;
    batch.read?.abort();
    clearTimeout(batch.rollover);
    for (const card of batch.cards.values()) {
      renderGameUsage(card, null);
      card.region.hidden = true;
    }
  }
  function expireGameUsage(batch) {
    batch.day = null;
    for (const card of batch.cards.values()) renderGameUsage(card, null, gameUsageLoading);
  }
  function applyGameUsage(batch, clock, childUsage) {
    const msUntilReset = Date.parse(clock?.resetsAt) - Date.parse(clock?.serverTime);
    const hasClock = /^\d{4}-\d{2}-\d{2}$/.test(clock?.day) && clock.timeZone === 'Asia/Ho_Chi_Minh' &&
      msUntilReset > 0 && msUntilReset <= 86400000;
    if (hasClock) {
      batch.day = clock.day;
      batch.deadline = performance.now() + msUntilReset;
      clearTimeout(batch.rollover);
      batch.rollover = setTimeout(() => {
        if (!isCurrentGameUsage(batch)) return;
        expireGameUsage(batch);
        refreshParentGameUsage();
      }, msUntilReset);
    }
    const byChild = new Map(Array.isArray(childUsage) ? childUsage.map(item => [String(item?.childId), item]) : []);
    for (const [id, card] of batch.cards) {
      if (!ownsGameUsageChild(id)) continue;
      const entry = byChild.get(id);
      card.region.hidden = false;
      renderGameUsage(card, hasClock && (!entry?.day || entry.day === batch.day) ? entry?.games : null);
    }
  }
  async function refreshParentGameUsage() {
    const batch = parentGameUsage;
    if (!batch || !batch.cards.size || !isCurrentGameUsage(batch) || batch.read || childManagement?.saving ||
        document.visibilityState === 'hidden') return;
    if (batch.day && performance.now() >= batch.deadline) expireGameUsage(batch);
    const read = new AbortController();
    batch.read = read;
    try {
      const data = await profiles.request('parent/game-limits', undefined, {signal: read.signal, expectedContext: batch.context});
      if (isCurrentGameUsage(batch) && !read.signal.aborted) applyGameUsage(batch, data, data.children);
    } catch (error) {
      if (!isCurrentGameUsage(batch) || read.signal.aborted) return;
      if (error.code === 'family_parent_pin_required') {
        clearParentGameUsage();
        closeChildManagement(false);
        profiles.refresh().catch(() => {});
      } else {
        for (const card of batch.cards.values()) renderGameUsage(card, null);
      }
    } finally {
      if (batch.read === read) batch.read = null;
    }
  }
  async function parent(){
    if(state().scope!=='parent_full')return parentGate();
    const context = state().context;
    const result = await profiles.request('parent/overview', undefined, {expectedContext: context});
    if (!canReadGameUsage(context)) return;
    clear('parent',true);title('Các con','Theo dõi việc học và lượt chơi hôm nay của từng con. Lượt chơi tính cả phòng chờ đã tham gia.');
    const batch = {context, familyId: state().family?.id, cards: new Map(), day: null, deadline: 0, rollover: null, read: null};
    parentGameUsage = batch;
    for(const entry of result.overview||result.children||state().children||[]){
      const profile=state().children?.find(item=>String(item.id)===String(entry.id));
      const child={...profile,...entry,pinSet:typeof profile?.pinSet==='boolean'?profile.pinSet:entry.pinSet};
      const card=node('section',undefined,'family-child-card'),head=node('div',undefined,'family-child-summary');
      const childTitle = node('h3', child.nickname || child.name);
      childTitle.id = 'family-child-name-' + child.id;
      card.setAttribute('aria-labelledby', childTitle.id);
      card.dataset.childId = String(child.id);
      head.append(profiles.avatar({type:'child',childId:child.id}), childTitle);
      card.append(head,node('p','Lớp '+child.grade+' · '+(child.pinSet===true?'Có mã PIN':child.pinSet===false?'Không dùng mã PIN':'Chưa có thông tin PIN'),'family-child-meta'));
      if(child.membership)card.append(node('p','Gói học: '+membershipLabel(child.membership),'family-badge'));
      const summary=child.today;
      card.append(node('h4','Hôm nay con đã học'));
      if(summary){const dl=node('dl',undefined,'family-daily-summary');for(const [label,value]of [['Bài học',summary.completedLessons],['Câu luyện tập',summary.answeredQuestions],['Bài kiểm tra',summary.submittedExams]]){const group=node('div');group.append(node('dt',label),node('dd',Number.isFinite(value)?String(value):'Chưa có dữ liệu'));dl.append(group);}card.append(dl);}
      else card.append(node('p','Chưa có dữ liệu tổng kết hôm nay.','family-help'));
      const usageCard = makeGameUsageCard(String(child.id));
      batch.cards.set(String(child.id), usageCard);
      card.append(usageCard.region);
      const manage = node('button', 'Quản lý', 'secondary');
      manage.type = 'button';
      manage.dataset.manageChildId = String(child.id);
      manage.setAttribute('aria-haspopup', 'dialog');
      manage.setAttribute('aria-describedby', childTitle.id);
      manage.addEventListener('click', () => openChildManagement(child, manage));
      head.append(manage);
      const row=node('div',undefined,'family-actions');row.append(button('Chọn gói học',()=>full(()=>manageChild(child,'/nang-cap/'))),button('Đổi mã PIN',()=>full(()=>setPin(child)),'secondary'));card.append(row);view.append(card);
    }
    const footer = node('div', undefined, 'family-actions family-overview-actions');
    footer.append(button('Thêm con', () => full(() => addChild(false))));
    view.append(footer);
    applyGameUsage(batch, result.gameUsage, result.overview?.map(child => child.gameUsage));
  }
  function canManageChild({childId, context}) {
    return currentPage === 'parent' && protectedPage && canReadGameUsage(context) && ownsGameUsageChild(childId);
  }
  function isOpenManagement(panel) {
    return childManagement === panel && panel.dialog.open && canManageChild(panel);
  }
  function closeChildManagement(restoreFocus = true) {
    if (!childManagement) return;
    const {dialog, opener, read} = childManagement;
    childManagement = null;
    read?.abort();
    dialog.close();
    dialog.remove();
    if (restoreFocus && opener.isConnected) opener.focus({preventScroll: true});
  }
  function openChildManagement(child, opener) {
    const childId = String(child.id), context = state().context;
    if (busy || childManagement || !/^[1-9]\d*$/.test(childId) || !canManageChild({childId, context})) return;
    status();
    const dialog = node('dialog', undefined, 'family-child-management');
    const title = node('h2', 'Quản lý ' + (child.nickname || child.name));
    title.id = 'family-child-management-title';
    title.tabIndex = -1;
    dialog.setAttribute('aria-labelledby', title.id);
    const heading = node('h3', 'Giới hạn lượt chơi mỗi ngày');
    const instructions = node('p', 'Giới hạn mỗi trò tính chung lượt chơi với AI và với bạn. Để trống là không giới hạn. Nhập 0 để ngừng mở lượt chơi mới.', 'family-help');
    instructions.id = 'family-child-management-help';
    dialog.setAttribute('aria-describedby', instructions.id);
    const feedback = node('p', undefined, 'family-help family-management-feedback');
    feedback.setAttribute('role', 'status');
    const error = node('p', undefined, 'family-status family-management-feedback');
    error.setAttribute('role', 'alert');
    error.dataset.error = 'true';
    const settings = node('form', undefined, 'family-form');
    const fields = node('fieldset', undefined, 'family-management-fields');
    const legend = node('legend', 'Lượt chơi tối đa mỗi ngày', 'family-management-legend');
    const controls = node('div', undefined, 'family-actions family-management-actions');
    const cancel = node('button', 'Hủy', 'secondary');
    cancel.type = 'button';
    const retry = node('button', 'Thử lại', 'secondary');
    retry.type = 'button';
    retry.hidden = true;
    const save = node('button', 'Lưu giới hạn');
    save.type = 'submit';
    save.hidden = true;
    fields.hidden = true;
    fields.append(legend);
    controls.append(cancel, retry, save);
    settings.append(fields, controls);
    dialog.append(title, heading, instructions, feedback, error, settings);
    const panel = {dialog, opener, childId, context, read: null, saving: false};
    childManagement = panel;

    function handleError(problem) {
      if (!isOpenManagement(panel)) return;
      if (problem.familyAccessChanged || problem.code === 'family_parent_pin_required' || problem.status === 401) {
        closeChildManagement(false);
        profiles.refresh().catch(() => {});
        return;
      }
      error.textContent = problem.message || 'Chưa thể kết nối. Vui lòng thử lại.';
    }
    async function load() {
      if (!isOpenManagement(panel) || panel.read) return;
      const read = new AbortController();
      panel.read = read;
      const focusRetry = document.activeElement === retry;
      if (focusRetry) title.focus({preventScroll: true});
      retry.hidden = true;
      error.textContent = '';
      feedback.textContent = 'Đang tải giới hạn lượt chơi…';
      try {
        const result = await profiles.request(`${gameLimitsAction}?childId=${childId}`, undefined, {signal: read.signal, expectedContext: context});
        if (!isOpenManagement(panel)) return;
        const max = result.maxLimit;
        const games = gameLimitIds.map(id => Array.isArray(result.games) && result.games.find(game => game?.id === id));
        if (String(result.childId) !== childId || !Number.isSafeInteger(max) || max < 1 || games.some(game => !game || typeof game.label !== 'string' ||
          (game.limit !== null && (!Number.isSafeInteger(game.limit) || game.limit < 0 || game.limit > max)))) {
          throw new Error('Chưa thể đọc giới hạn của hồ sơ này. Vui lòng thử lại.');
        }
        for (const game of games) {
          const input = field(fields, game.label, game.id, 'number', {
            required: false, min: 0, max, step: 1, inputmode: 'numeric', placeholder: 'Không giới hạn'
          });
          input.value = game.limit ?? '';
          const label = input.parentElement.firstElementChild;
          label.id = 'family-child-game-' + game.id;
          input.setAttribute('aria-labelledby', label.id);
          if (Number.isSafeInteger(game.used) && game.used >= 0) {
            const usage = node('span', `Đã dùng ${game.used} lượt hôm nay`, 'family-help family-management-usage');
            usage.id = 'family-child-usage-' + game.id;
            input.parentElement.insertBefore(usage, input);
            input.setAttribute('aria-describedby', usage.id);
          }
        }
        fields.hidden = false;
        save.hidden = false;
        feedback.textContent = '';
      } catch (problem) {
        if (!isOpenManagement(panel)) return;
        feedback.textContent = '';
        handleError(problem);
        if (isOpenManagement(panel)) {
          retry.hidden = false;
          if (focusRetry) retry.focus();
        }
      } finally {
        panel.read = null;
      }
    }
    settings.addEventListener('submit', async event => {
      event.preventDefault();
      if (!isOpenManagement(panel) || panel.saving || fields.hidden || !settings.reportValidity()) return;
      const limits = Object.fromEntries(gameLimitIds.map(id => {
        const value = settings.elements.namedItem(id).value;
        return [id, value === '' ? null : Number(value)];
      }));
      panel.saving = fields.disabled = cancel.disabled = save.disabled = true;
      parentGameUsage?.read?.abort();
      error.textContent = '';
      feedback.textContent = 'Đang lưu giới hạn lượt chơi…';
      try {
        const result = await profiles.request(gameLimitsAction, {childId: child.id, limits}, {expectedContext: context});
        if (!isOpenManagement(panel)) return;
        if (String(result.childId) !== childId) throw new Error('Chưa thể xác nhận giới hạn đã lưu. Vui lòng thử lại.');
        const batch = parentGameUsage;
        const usageCard = batch?.cards.get(childId);
        const sameDay = usageCard && isCurrentGameUsage(batch) && batch.day === result.day && performance.now() < batch.deadline;
        const rendered = sameDay && renderGameUsage(usageCard, result.games);
        if (batch && !sameDay) expireGameUsage(batch);
        closeChildManagement();
        status('Đã lưu giới hạn lượt chơi cho ' + (child.nickname || child.name) + '.');
        if (!rendered) refreshParentGameUsage();
      } catch (problem) {
        handleError(problem);
      } finally {
        if (isOpenManagement(panel)) {
          panel.saving = fields.disabled = cancel.disabled = save.disabled = false;
          feedback.textContent = '';
          if (document.activeElement === document.body || document.activeElement === dialog) save.focus();
        }
      }
    });
    cancel.addEventListener('click', () => closeChildManagement());
    retry.addEventListener('click', load);
    dialog.addEventListener('cancel', event => {
      event.preventDefault();
      if (!panel.saving) closeChildManagement();
    });
    document.body.append(dialog);
    dialog.showModal();
    title.focus({preventScroll: true});
    load();
  }
  function navigate(target,update=true){const views={overview:parent,parent:parent,addchild:()=>addChild(false),devices:account,account,cart};if(!views[target])target='overview';if(target==='devices')target='account';if(update)history.replaceState(null,'','/gia-dinh/?view='+target);return full(views[target]);}
  function cart(){clear('cart',true);const section=node('div',undefined,'family-cart');view.append(section);return window.FamilyCart?.mount(section);}
  async function account(){
    clear('account',true);title('Tài khoản phụ huynh','Quản lý thông tin đăng nhập và quyền truy cập của gia đình.');
    if(state().family?.email)view.append(node('p',state().family.email,'family-account-email'));
    actions(button('Đổi mật khẩu',()=>full(passwordForm)),button('Đổi PIN phụ huynh',()=>full(()=>setPin()),'secondary'));
    const section=node('section',undefined,'family-account-devices'),heading=node('h3','Thiết bị đăng nhập'),list=node('div');
    heading.id='family-devices-title';section.setAttribute('aria-labelledby',heading.id);list.setAttribute('aria-live','polite');list.append(node('p','Đang đọc các thiết bị…','family-help'));
    section.append(heading,node('p','Tối đa 3 máy đăng nhập. Thu hồi máy không còn dùng; các máy khác vẫn hoạt động.','family-help'),list);view.append(section);
    const all=node('div',undefined,'family-actions');all.append(button('Đăng xuất tất cả thiết bị',()=>full(logoutAllPrompt),'danger'));section.append(all);
    view.append(node('hr',undefined,'family-divider'));actions(button('Xóa tài khoản',()=>full(deleteAccount),'danger'));
    const result=await api('devices');
    if(!section.isConnected&&!suspended?.fragment.contains(section))return;
    list.replaceChildren();
    for(const device of result.devices||[]){const row=node('section',undefined,'family-device'),own=String(device.id)===String(state().device?.id);row.append(node('strong',device.name||device.label||'Thiết bị gia đình'),node('p',own?'Máy đang dùng':'Thiết bị của gia đình'));if(device.lastSeenAt)row.append(node('p','Hoạt động gần nhất: '+device.lastSeenAt,'family-help'));row.append(button(own?'Đăng xuất máy này':'Thu hồi thiết bị',()=>full(async()=>{await api('devices/revoke',{deviceId:device.id});if(own){profiles.accept({authenticated:false});login();}else await account();}),'secondary'));list.append(row);}
    if(!list.childNodes.length)list.append(node('p','Chưa có thiết bị để hiển thị.','family-help'));
  }
  function deleteAccount(){clear('delete-account',true);title('Xóa tài khoản gia đình','Đóng tài khoản sẽ đăng xuất mọi thiết bị và ngừng quyền truy cập của gia đình. Chứng từ giao dịch được giữ theo yêu cầu lưu trữ; thao tác này không xóa ngay mọi bản ghi.');const {f,submit}=form(async data=>{if(data.confirm!=='on')throw new Error('Ba mẹ cần xác nhận đóng tài khoản.');await api('account/delete',{pin:data.pin,confirm:'XOA TAI KHOAN'});f.reset();profiles.accept({authenticated:false});login();status('Tài khoản đã đóng. Các thiết bị đã được đăng xuất.');},'Xác nhận xóa tài khoản');field(f,'PIN phụ huynh · 6 số','pin','password',{inputmode:'numeric',pattern:'[0-9]{6}',maxlength:6,autocomplete:'off'});check(f,'Tôi xác nhận đóng tài khoản gia đình và ngừng quyền truy cập của các hồ sơ con.','confirm',true);submit.className='danger';f.append(submit);view.append(f);actions(button('Giữ tài khoản',account,'secondary'));}
  function forgotPassword(){clear('forgot');title('Lấy lại mật khẩu','Nhập email của ba mẹ để nhận liên kết xác nhận và tự đặt mật khẩu mới.');if(config().passwordReset?.delivery==='local-test')view.append(node('p','Bản thử cục bộ: liên kết được gửi vào hộp thư thử nghiệm của 5BMath.','family-help'));const {f,submit}=form(async data=>{await api('password/reset/request',{email:data.email});f.reset();status('Nếu email có tài khoản, liên kết đặt lại mật khẩu sẽ được gửi đến hộp thư. Vui lòng kiểm tra thư đến.');},'Gửi liên kết xác nhận');field(f,'Email của ba mẹ','email','email',{autocomplete:'email',maxlength:254});f.append(submit);view.append(f);actions(button('Về đăng nhập',()=>login(),'family-text-button'));}
  function resetPassword(){clear('reset');title('Đặt mật khẩu mới','Chỉ khi xác nhận tại đây, mật khẩu mới có hiệu lực và các thiết bị cũ được đăng xuất.');if(!resetToken){view.append(node('p','Liên kết thiếu mã xác nhận. Ba mẹ vui lòng yêu cầu liên kết mới.'));actions(button('Lấy liên kết mới',forgotPassword));return;}const {f,submit}=form(async data=>{if(data.password!==data.confirm)throw new Error('Hai lần nhập mật khẩu chưa khớp.');await api('password/reset/confirm',{token:resetToken,newPassword:data.password,confirmPassword:data.confirm});resetToken='';f.reset();login();status('Đã đặt mật khẩu mới. Ba mẹ đăng nhập lại để tiếp tục.');},'Xác nhận mật khẩu mới');field(f,'Mật khẩu mới','password','password',{minlength:6,maxlength:128,autocomplete:'new-password'});field(f,'Nhập lại mật khẩu mới','confirm','password',{minlength:6,maxlength:128,autocomplete:'new-password'});f.append(submit);view.append(f);actions(button('Lấy liên kết mới',()=>{resetToken='';forgotPassword();},'family-text-button'));}

    async function manageChild(child,destination){await api('parent/select',{childId:child.id});const next=new URLSearchParams(location.search).get('next');location.assign(safePath(next,destination));}
  function addChild(first=false){
    clear('add-child',state().scope==='parent_full');title(first?'Tạo góc học cho bé':'Thêm góc học cho con','Chọn tên gọi, năm sinh và Bạn Đồng Hành. Ba mẹ có thể đặt mã PIN riêng cho con hoặc chọn không dùng mã PIN.');
    const {f,submit}=form(async data=>{
      if(state().onboarding?.needsParentPin){await api('parent/pin/setup',{pin:data.parentPin});f.querySelector('[data-parent-bootstrap]')?.remove();protectedPage=true;}
      if(state().scope!=='parent_full'){profiles.open({target:'parent',stay:true,onSuccess:()=>create(data)});return;}
      return create(data);
    },first?'Tạo hồ sơ và vào học':'Thêm con');
    async function create(data){const result=await api('children/add',{name:data.nickname,birthYear:Number(data.birthYear),mascot:data.mascot,...(data.noPin==='on'?{noPin:true}:{pin:data.pin}),requestKey:data.requestKey,legalConsent:legal(data)});const childId=result.addedChildId||state().children?.at(-1)?.id;if(first){await api('select',{childId,pin:data.noPin==='on'?'':data.pin});f.reset();location.assign('/tai-khoan/');}else{f.reset();await parent();status('Đã thêm góc học cho con.');}}
    field(f,'Tên gọi của con','nickname','text',{maxlength:40,autocomplete:'off'});
    const birth=field(f,'Năm sinh của con','birthYear','number',{min:1900,max:new Date().getFullYear(),step:1,inputmode:'numeric',placeholder:'Ví dụ: 2016'});
    const grade=node('p','Nhập năm sinh thật. Lớp học ban đầu được gợi ý theo năm học.','family-help');birth.addEventListener('input',()=>{const d=new Date(),year=d.getFullYear()-(d.getMonth()<6?1:0),g=Math.max(1,Math.min(5,year-Number(birth.value)-5));grade.textContent=birth.value?'Lớp học ban đầu: Lớp '+g+'.':'Nhập năm sinh thật. Lớp học ban đầu được gợi ý theo năm học.';});f.append(grade);
    const choices=node('fieldset',undefined,'family-companions');choices.append(node('legend','Bạn Đồng Hành của con'));const grid=node('div',undefined,'family-companion-grid');
    for(const companion of config().companions||[]){const label=node('label',undefined,'family-companion'),input=node('input');input.type='radio';input.name='mascot';input.value=companion.code;input.required=true;label.append(input,profiles.companionAvatar(companion.code),node('span',companion.name));grid.append(label);}choices.append(grid);f.append(choices);
    optionalChildPin(f,'PIN riêng của con · 4 số');
    if(state().onboarding?.needsParentPin){const setup=node('fieldset');setup.dataset.parentBootstrap='';setup.append(node('legend','Khóa Góc Phụ Huynh'),node('p','Ba mẹ đặt PIN 6 số để quản lý hồ sơ, gói học và thiết bị. Giữ PIN này cho ba mẹ.','family-help'));field(setup,'PIN phụ huynh · 6 số','parentPin','password',{inputmode:'numeric',pattern:'[0-9]{6}',minlength:6,maxlength:6,autocomplete:'new-password'});f.append(setup);if(!state().onboarding.canSetupParentPin){setup.replaceChildren(node('p','Phiên thiết lập PIN đã hết hạn. Ba mẹ đăng nhập lại để tiếp tục.'));actions(button('Đăng nhập lại',logout,'secondary'));submit.disabled=true;}}
    f.append(link('Thông báo dữ liệu và quyền của gia đình','/bao-ve-du-lieu/'));check(f,'Tôi là người lớn chịu trách nhiệm quản lý hồ sơ này và đồng ý lưu thông tin cần thiết cho việc học của con.','consent',true);f.append(submit);view.append(f);
  }
  function optionalChildPin(f,label,noPin=false){
    const toggle=check(f,'Không dùng mã PIN','noPin',false,noPin);
    const input=field(f,label,'pin','password',{inputmode:'numeric',pattern:'[0-9]{4}',minlength:4,maxlength:4,autocomplete:'new-password'});
    const help=node('p','Khi không dùng PIN, người đang cầm thiết bị đã đăng nhập có thể mở hồ sơ con.','family-help');f.append(help);
    const sync=()=>{input.required=!toggle.checked;input.disabled=toggle.checked;input.closest('label').hidden=toggle.checked;help.hidden=!toggle.checked;};toggle.addEventListener('change',sync);sync();return input;
  }
  function setPin(child){clear(child?'child-pin':'parent-pin',true);title(child?'Mã PIN của '+(child.nickname||child.name):'Đổi PIN phụ huynh',child?'Chọn dùng PIN riêng hoặc không dùng mã PIN cho hồ sơ con.':'PIN phụ huynh gồm 6 số và luôn cần để mở các chức năng quản lý.');const {f,submit}=form(async data=>{await api(child?'child/pin':'parent/pin',child?{childId:child.id,...(data.noPin==='on'?{noPin:true}:{pin:data.pin})}:{pin:data.pin});f.reset();await parent();status('Đã lưu lựa chọn mã PIN.');},'Lưu lựa chọn');if(child)optionalChildPin(f,'PIN mới · 4 số',child.pinSet===false);else field(f,'PIN mới','pin','password',{inputmode:'numeric',pattern:'[0-9]{6}',minlength:6,maxlength:6,autocomplete:'new-password'});f.append(submit);view.append(f);}
  function passwordForm(){clear('password',true);title('Đổi mật khẩu 5BMath','Mật khẩu từ 6 ký tự, dùng để đăng nhập. Sau khi đổi, các máy cần đăng nhập lại.');const {f,submit}=form(async data=>{if(data.password!==data.confirm)throw new Error('Hai lần nhập mật khẩu chưa khớp.');await api('password',{newPassword:data.password});f.reset();login();status('Đã đổi mật khẩu. Ba mẹ đăng nhập lại để tiếp tục.');},'Lưu mật khẩu');field(f,'Mật khẩu mới','password','password',{minlength:6,maxlength:128,autocomplete:'new-password'});field(f,'Nhập lại mật khẩu mới','confirm','password',{minlength:6,maxlength:128,autocomplete:'new-password'});f.append(submit);view.append(f);actions(button('Quay lại',()=>full(parent),'secondary'));}
  function logoutAllPrompt(){clear('logout-all',true);title('Đăng xuất tất cả thiết bị?','Các máy của ba mẹ và các con đều cần đăng nhập lại. Tiến độ học vẫn được giữ.');actions(button('Đăng xuất tất cả',()=>full(async()=>{await api('devices/logout-all',{});profiles.accept({authenticated:false});login();status('Đã đăng xuất tất cả thiết bị.');}),'danger'),button('Giữ đăng nhập',()=>full(account),'secondary'));}
  async function logout(){await api('logout',{});suspended=null;profiles.accept({authenticated:false});login();}
  function safePath(value,fallback){if(typeof value!=='string'||!/^\/(?!\/)/.test(value)||/[\\\u0000-\u0020\u007f]/.test(value))return fallback;try{const target=new URL(value,location.origin);return target.origin===location.origin?target.pathname+target.search+target.hash:fallback;}catch{return fallback;}}
  async function restoreParent(){
    if(suspended?.page==='parent'){
      suspended=null;
      return run(parent);
    }
    if(suspended){view.replaceChildren(suspended.fragment);protectedPage=true;currentPage=suspended.page;syncShellView();const focus=suspended.focus;suspended=null;status();if(focus?.isConnected)focus.focus({preventScroll:true});if(currentPage==='cart')await window.FamilyCart?.resume();return;}
    return navigate(new URLSearchParams(location.search).get('view')==='cart'?'cart':'parent',false);
  }
  function retainCart(){
    if(state().device?.childOnly||profiles.profileOf().type!=='parent')return false;
    if(currentPage==='cart-locked'){
      profiles.open({target:'parent',stay:true,onSuccess:restoreParent});
      return true;
    }
    return currentPage==='cart'&&protectedPage&&state().scope==='parent_full'&&!state().parentLocked;
  }
  window.addEventListener('family-privilege-expired',()=>{closeChildManagement(false);if(!protectedPage)return;const fragment=document.createDocumentFragment(),focus=document.activeElement,page=currentPage;while(view.firstChild)fragment.append(view.firstChild);suspended={fragment,focus,page};lockedShell(page);profiles.open({target:'parent',stay:true,onSuccess:restoreParent});});
  window.addEventListener('family-access-invalidated',()=>{closeChildManagement(false);clearParentGameUsage();window.FamilyCart?.unmount();suspended=null;view.replaceChildren();currentPage='';protectedPage=false;status('Hồ sơ hoặc phiên vừa thay đổi.');actions(button('Mở lại gia đình',async()=>{await profiles.refresh();await home();},'secondary'));});
  window.addEventListener('family-guest',()=>{window.FamilyCart?.unmount();suspended=null;login();status('Phiên đã hết hạn. Ba mẹ vui lòng đăng nhập lại.',true);});
  window.addEventListener('focus',refreshParentGameUsage);
  document.addEventListener('visibilitychange',refreshParentGameUsage);
  window.addEventListener('online',refreshParentGameUsage);
  window.addEventListener('pageshow',event=>{if(event.persisted)refreshParentGameUsage();});
  window.addEventListener('pagehide',()=>{
    closeChildManagement(false);
    if (!parentGameUsage) return;
    parentGameUsage.read?.abort();
    expireGameUsage(parentGameUsage);
  });
  setInterval(refreshParentGameUsage,15000);
  window.FamilyApp={navigate:target=>run(()=>navigate(target)),retainCart};
  window.addEventListener('family-state-updated',()=>{
    if(childManagement&&!canManageChild(childManagement))closeChildManagement(false);
    const batch = parentGameUsage;
    if (batch && !isCurrentGameUsage(batch)) clearParentGameUsage();
    else if (batch) {
      for (const [id, card] of batch.cards) {
        if (ownsGameUsageChild(id)) continue;
        renderGameUsage(card, null);
        card.region.hidden = true;
      }
    }
    document.body.classList.toggle('family-authenticated',Boolean(state().authenticated));const trial=document.querySelector('[data-family-guest-trial]');if(trial)trial.hidden=Boolean(state().authenticated);
  });
  run(async()=>{await profiles.init();await home();});
})();
