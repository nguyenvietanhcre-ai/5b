/* Native module within the existing learning shell; no iframe, profile impersonation or main-state mutation. */
'use strict';
const LocalPilot=(()=>{
 let generation=0,panel=null,busy=false,catalogue=null,exam=null,index=0,pending=new Map(),saving=null,saveError=false,allocation=null,timer=null,owner=null,csrf=null,routeNow='',criteriaState={pool:'all',count:10,scope:'topic',topicKey:'',difficulty:'',school:'cau-giay',initialized:false},historyItems=[],historyFilter='all',historySearch='',course=null,courseProgress={},fixedPending=null,fixedBusy=false,walletExpanded=false;
 const solutionView=window.SolutionView;
 const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const displayTitle=value=>String(value).replace(/— (?:free|vip)\.(?:parts|unit|reverse)\.(\d+)$/,'— Bài $1');
 const q=s=>panel?.querySelector(s),url=()=>new URLSearchParams(location.search),enabled=()=>PlatformAPI.snapshot.localPilotEnabled===true;
 const requested=route=>(['testing','results'].includes(route)&&url().has('pilotExam'))||(route==='lesson'&&(url().has('pilotLesson')||url().has('knowledgeLesson')));
 const handles=route=>enabled()&&(requested(route)||(Number(PlatformAPI.snapshot.state?.grade)===5&&['exams','weekly','topics'].includes(route)));
 const shell=()=>'<section id="local-pilot" class="local-pilot" aria-label="Học tập khối 5"><p role="status">Đang tải học liệu thí điểm…</p></section>';
 const path=(route,id)=>'/'+route+'/?pilotExam='+encodeURIComponent(id);
 const button=(label,action,extra='',kind='dark')=>`<button type="button" class="btn ${kind}" data-pilot="${action}" ${extra}>${e(label)}</button>`;
 const note=()=>'<p class="learning-notice">Học tập lớp 5 · Bản mẫu · kho ví, bài làm và điểm riêng · học liệu tự biên soạn, chờ giáo viên rà. Thanh toán mô phỏng, không chuyển tiền.</p>';
 async function api(route,body){
  const g=generation;const response=await fetch('/api/local-pilot/'+route,{credentials:'same-origin',cache:'no-store',...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||''},body:JSON.stringify(body)})});
  const value=await response.json();
  if(g!==generation||owner!==PlatformAPI.snapshot.account?.id||csrf!==PlatformAPI.snapshot.csrf)throw new DOMException('Phiên đã thay đổi.','AbortError');
  if(!response.ok){const error=new Error(value.error||'Chưa thể kết nối kho thí điểm.');error.status=response.status;error.reconfirm=response.status===409&&value.reconfirm===true;throw error;}
  return value;
 }
 function error(message){if(!panel)return;const target=q('dialog[open]')||panel;let box=target.querySelector('[data-pilot-error]');if(!box){box=document.createElement('p');box.dataset.pilotError='';box.setAttribute('role','alert');box.className='learning-notice';target.prepend(box);}box.textContent=message;}

 function controls(){panel?.querySelectorAll('button[data-pilot]').forEach(b=>b.disabled=busy||b.dataset.unavailable==='true'||(b.dataset.pilot==='previous'&&index<=0)||(b.dataset.pilot==='next'&&index>=((exam?.questions.length||1)-1)));panel?.querySelectorAll('input,select').forEach(input=>input.disabled=busy);}
 const time=value=>value?new Date(value).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'Chưa có';
 function allocationHTML(){return `<dialog id="pilot-allocation" aria-labelledby="pilot-allocation-title"><h2 id="pilot-allocation-title">Xác nhận lượt học</h2><div id="pilot-allocation-text"></div><p id="pilot-allocation-notice"></p><div class="pilot-actions">${button('Quay lại','cancel-allocation','','outline')}${button('Xác nhận cấp bài','commit')}</div></dialog>`;}
 const field=(label,id,items,value)=>`<label class="field"><span>${e(label)}</span><select id="${id}">${items.map(([v,t])=>`<option value="${e(v)}" ${String(v)===String(value)?'selected':''}>${e(t)}</option>`).join('')}</select></label>`;
 const count=value=>Number.isFinite(Number(value))?Number(value):0;
 const courseHref=(key,revision)=>'/bai-giang/?knowledgeLesson='+encodeURIComponent(key)+(revision?'&lessonRevision='+encodeURIComponent(revision):'');
 const topicHref=key=>'/thi-thu/?topicKey='+encodeURIComponent(key);
 const content=value=>{const context=course?{lessonKey:course.lessonKey,revision:course.revision}:null;const render=v=>typeof v==='string'||v?.type==='text'?`<p>${solutionView.text(typeof v==='string'?v:v.text)}</p>`:block(v,context,'');return Array.isArray(value)?value.map(render).join(''):render(value);};
 function walletHTML(state){
  const vip=state.vip||{},unlimited=catalogue.internalUnlimited;
  return `<section class="r11-wallet" aria-label="Ví thí điểm"><h2>Ví thí điểm</h2><div class="r11-wallet-stats"><span>VIP ngày đã dùng <b>${vip.active?count(vip.dayUsed)+'/30':'—'}</b></span><span>Chu kỳ đã dùng <b>${vip.active?count(vip.cycleUsed)+'/300':'—'}</b></span><span>Gói riêng còn <b>${count(state.privateRemaining)} câu</b></span></div>${button('Chi tiết','wallet-detail','','outline')}</section><section id="r11-wallet-detail" class="r11-wallet-detail" ${walletExpanded?'':'hidden'}><h3>${e(catalogue.role)}${unlimited?' · quyền nội bộ, không trừ ví':''}</h3><p>${e(catalogue.cycleNotice)}</p><p>VIP: tối đa 30 câu mới/ngày và 300 câu mới/chu kỳ 30 ngày, dùng trước gói riêng còn hạn. Câu Free, câu đã nhận và xem lại không trừ thêm.</p><p>Gói riêng 100 câu / 50.000đ / 90 ngày, không kéo dài VIP hoặc mở quyền Zoom, Đấu trí, đề theo trường.</p><p>VIP hết hạn: ${e(time(vip.vipExpiresAt))}</p>${(state.packs||[]).map(p=>`<p>${count(p.remaining)} câu · hạn ${e(time(p.expires_at))}${p.usable?'':' · không dùng được'}</p>`).join('')}<p>Chức năng dưới đây chỉ mô phỏng, không chuyển tiền.</p>${button('Tạo đơn mô phỏng 100 câu','buy')}${(state.orders||[]).filter(o=>o.status==='pending').map(o=>`<div class="pilot-order"><p>Đơn mô phỏng đang chờ</p>${button('Xác nhận thanh toán giả','mock-confirm',`data-order="${e(o.orderId)}"`)}${button('Mô phỏng thất bại','mock-fail',`data-order="${e(o.orderId)}"`,'outline')}</div>`).join('')}</section>`;
 }
 function availableQuestions(category){
  let items=(catalogue.questions||[]).filter(x=>x.eligible===true&&(category!=='content'||criteriaState.scope==='weekly'||x.topicKey===criteriaState.topicKey));
  if(criteriaState.pool!=='all')items=items.filter(x=>String(x.access).toLowerCase()===(criteriaState.pool==='free'?'free':'vip'));
  if(category==='combined'&&criteriaState.difficulty){
   if(items.some(x=>x.difficulty===undefined))return null;
   items=items.filter(x=>Number(x.difficulty)===Number(criteriaState.difficulty));
  }
  return items;
 }
 function capability(category){
  if(category==='school'&&!catalogue.schoolAccess)return {ok:false,reason:'Ôn đề theo trường dành cho VIP+. Vào Nâng cấp gói để mở quyền.'};
  if(category==='school'&&!catalogue.schoolReady)return {ok:false,reason:'Chưa có cấu trúc và bộ câu theo trường được duyệt. Chưa tạo đề hoặc trừ lượt.'};
  if(category==='content'&&criteriaState.scope==='weekly'&&!catalogue.weekReady)return {ok:false,reason:'Học liệu chưa được đối chiếu theo tuần. Em có thể chọn Chuyên đề để luyện nội dung hiện có.'};
  const items=availableQuestions(category);
  if(items===null)return {ok:false,reason:'Mức độ này chưa có đầy đủ thông tin phân loại cho bộ lọc. Em chọn Tất cả mức độ để tiếp tục.'};
  const n=count(criteriaState.count);
  const available=items.filter(x=>x.cost===0).length+Math.min(count(catalogue.practiceBudget?.newPaidAvailable),items.filter(x=>x.cost===1).length);
  if(available<n)return {ok:false,reason:`Chỉ có ${available} câu phù hợp, chưa đủ ${n} câu. Giảm số câu hoặc mở rộng bộ lọc; chưa cấp đề, chưa trừ lượt.`};
  return {ok:true,reason:`Có ${available} câu trong bộ lọc. Đề ${n} câu dùng dạng trả lời phù hợp từng câu.`};
 }
 function criteria(category){
  const selected={category,count:count(criteriaState.count),pool:criteriaState.pool};
  if(category==='content'){
   if(criteriaState.scope==='weekly')selected.week=Number(PlatformAPI.snapshot.state?.week||1);
   else selected.topicKey=criteriaState.topicKey;
  }
  if(category==='combined'&&criteriaState.difficulty)selected.difficulty=Number(criteriaState.difficulty);
  if(category==='school')selected.school=criteriaState.school;
  return selected;
 }
 function createButton(label,category){const c=capability(category);return button(label,'practice-create',`data-category="${category}" data-unavailable="${!c.ok}" ${c.ok?'':'disabled'}`);}
 function drawPractice(){
  const c=catalogue,topics=c.topics||[];
  if(!criteriaState.topicKey||!topics.some(t=>t.key===criteriaState.topicKey))criteriaState.topicKey=topics[0]?.key||'';
  const requestedTopic=url().get('topicKey');
  if(!criteriaState.initialized&&topics.some(t=>t.key===requestedTopic))criteriaState.topicKey=requestedTopic;
  criteriaState.initialized=true;
  panel.innerHTML=`<div class="intro"><div><h1>Luyện tập</h1><p>Chọn nội dung, làm đề và xem lại lời giải.</p></div><span class="tag sage">Khối 5</span></div>${walletHTML(c.wallet)}<section class="card card-pad r11-config" aria-label="Cấu hình đề">${field('Ngân hàng câu luyện tập','exam-pool',[['all','Free và tính phí'],['free','Chỉ câu Free'],['paid','Chỉ câu tính phí']],criteriaState.pool)}${field('Số câu','exam-count',(c.practiceCounts||[1,2,3,5,10]).map(n=>[n,n+' câu']),criteriaState.count)}<p class="r11-policy-note">Mỗi câu tự dùng hình thức phù hợp: một đáp số điền đáp án; nhiều ý chọn một phương án có đầy đủ kết quả. Câu tự luyện miễn phí kèm bài giảng được soạn riêng, không đưa vào đề này.</p></section><div class="r11-forms"><section class="card card-pad r11-form"><span class="tile" aria-hidden="true">◎</span><h2>Ôn theo nội dung</h2><p>Luyện theo chương trình trên lớp hoặc chuyên đề.</p>${field('Phạm vi','exam-scope',[['topic','Chuyên đề'],['weekly','Theo chương trình học trên lớp']],criteriaState.scope)}<label class="field"><span>Nội dung · Tìm kiếm</span><input id="exam-content-search" type="search" placeholder="Tìm nội dung"></label>${field('Nội dung','exam-topic',topics.map(t=>[t.key,t.title]),criteriaState.topicKey)}<p class="r11-capability" id="r11-content-capability">${e(capability('content').reason)}</p><div class="r11-form-actions">${createButton('Tạo đề theo nội dung','content')}</div></section><section class="card card-pad r11-form"><span class="tile peach" aria-hidden="true">▤</span><h2>Đề tổng hợp</h2><p>Kết hợp các nội dung trong ngân hàng học liệu tự biên soạn, không phải đề chính thức.</p>${field('Độ khó','exam-difficulty',[['','Tất cả mức độ'],[1,'Cơ bản'],[2,'Nâng cao'],[3,'Khó'],[4,'Tư duy']],criteriaState.difficulty)}<p class="r11-capability">${e(capability('combined').reason)}</p><div class="r11-form-actions">${createButton('Tạo đề ngẫu nhiên','combined')}</div></section><section class="card card-pad r11-form"><span class="tile sand" aria-hidden="true">⌑</span><h2>Đề theo trường</h2><p>Dành cho khối 5; cần bộ câu và cấu trúc trường đã được duyệt.</p>${field('Trường','exam-school',[['cau-giay','THCS Cầu Giấy'],['ngoai-ngu','THCS Ngoại ngữ'],['ntt','Nguyễn Tất Thành']],criteriaState.school)}<p class="r11-capability">${e(capability('school').reason)}</p><div class="r11-form-actions">${createButton('Luyện đề theo trường','school')}</div></section></div><section class="card card-pad practice-lookup"><h2>Tra cứu câu hỏi</h2><p>Xem lại câu hỏi bằng mã khi cần ôn tập.</p><a class="btn outline" href="/tra-cuu-cau-hoi/">Tra cứu mã câu hỏi</a></section><section id="r11-history" aria-labelledby="r11-history-title"><h2 id="r11-history-title">Đề đã làm</h2><div class="r11-history-tools">${field('Hiển thị','r11-history-filter',[['all','Tất cả'],['completed','Đã nộp'],['pending','Đang làm']],historyFilter)}<label class="field r11-history-search"><span>Tìm đề</span><input id="r11-history-search" type="search" value="${e(historySearch)}" placeholder="Tên đề hoặc nội dung"></label></div><div class="card" id="r11-history-list"></div></section>${allocationHTML()}`;
  bind();bindFilters();drawHistory();
 }
 function drawHistory(){
  const filtered=historyItems.filter(x=>(historyFilter==='all'||(historyFilter==='completed')===Boolean(x.submitted))&&String(x.title||'').toLocaleLowerCase('vi').includes(historySearch.toLocaleLowerCase('vi')));
  const box=q('#r11-history-list');if(!box)return;
  box.innerHTML=filtered.map(item=>{
   if(!['main','pilot'].includes(item.provider)||!/^\d+$/.test(String(item.id)))return '';
   const href=item.provider==='pilot'?path(item.submitted?'ket-qua-thi':'lam-de',item.id):'/'+(item.submitted?'ket-qua-thi':'lam-de')+'/?id='+encodeURIComponent(item.id);
   const format=item.responseMode==='mixed'?'Trắc nghiệm và điền đáp án':item.responseMode==='choice'?'Trắc nghiệm':'Điền đáp án';
   return `<div class="r11-history-row" data-reference="${e(item.reference)}"><div><strong>${e(item.title)} <span class="tag ${item.submitted?'sage':'peach'}">${item.submitted?e(item.score)+'/10':'Đang làm'}</span></strong><small>${e(format)} · ${e(time(item.submittedAt||item.startedAt))}</small></div><a class="btn outline" href="${href}">${item.submitted?'Xem lại':'Làm tiếp'}</a></div>`;
  }).join('')||`<div class="r11-empty"><h3>${historyItems.length?'Chưa có đề khớp bộ lọc':'Em chưa có đề đã làm'}</h3><p>${historyItems.length?'Thử từ khác hoặc chọn Tất cả.':'Chọn nội dung phía trên để bắt đầu. Bài làm mới và trước đây cùng xuất hiện ở đây.'}</p></div>`;
 }
 function bindFilters(){
  const ids={'exam-pool':'pool','exam-count':'count','exam-scope':'scope','exam-topic':'topicKey','exam-difficulty':'difficulty','exam-school':'school'};
  for(const [id,key] of Object.entries(ids))q('#'+id)?.addEventListener('change',ev=>{criteriaState[key]=ev.target.value;drawPractice();});
  q('#exam-content-search')?.addEventListener('input',ev=>{
   const value=ev.target.value.toLocaleLowerCase('vi'),select=q('#exam-topic');
   [...select.options].forEach(o=>o.hidden=!o.textContent.toLocaleLowerCase('vi').includes(value));
   const first=[...select.options].find(o=>!o.hidden);select.disabled=!first;
   if(first){criteriaState.topicKey=first.value;select.value=first.value;}
   const c=first?capability('content'):{ok:false,reason:'Chưa có nội dung khớp tìm kiếm. Thử từ khác; chưa tạo đề hoặc trừ lượt.'};
   q('#r11-content-capability').textContent=c.reason;const b=q('[data-category="content"]');b.dataset.unavailable=String(!c.ok);b.disabled=!c.ok;
  });
  q('#r11-history-filter')?.addEventListener('change',ev=>{historyFilter=ev.target.value;drawHistory();});
  q('#r11-history-search')?.addEventListener('input',ev=>{historySearch=ev.target.value;drawHistory();});
 }
 function drawCourses(){
  const topics=catalogue.topics||[],lessons=catalogue.knowledge||[];
  panel.innerHTML=`<div class="intro"><div><h1>Bài giảng</h1><p>Đọc bài giảng, hiểu phương pháp và tự luyện những câu miễn phí trong từng bài.</p></div><span class="tag sage">Khối 5</span></div><nav class="r11-tabs" aria-label="Tìm bài giảng"><a class="btn ${routeNow==='weekly'?'dark':'outline'}" href="/hoc-theo-tuan/">Theo tuần</a><a class="btn ${routeNow==='topics'?'dark':'outline'}" href="/chuyen-de/">Chuyên đề</a></nav>${routeNow==='weekly'&&!catalogue.weekReady?'<p class="learning-notice">Khung tuần đang chờ đối chiếu chương trình. Em có thể chọn một chuyên đề bên dưới; đây không phải lịch tuần SGK.</p>':''}<div class="r11-topics">${topics.map((t,i)=>`<article class="card card-pad r11-topic"><span class="r11-topic-icon" aria-hidden="true">${String(i+1).padStart(2,'0')}</span><h2>${e(t.title)}</h2><p>Lý thuyết · Định hướng tư duy · Câu tự luyện cố định miễn phí.</p><div class="r11-course-list">${lessons.filter(l=>l.topicKey===t.key).map(l=>`<a class="r11-course-link" href="${courseHref(l.lessonKey,l.revision)}"><strong>${e(l.title)}</strong><small>${l.completed?'Đã tự kiểm tra':'Học và tự kiểm tra'} · Miễn phí</small></a>`).join('')||'<p>Học liệu đang được cập nhật.</p>'}</div><small>${count(t.availableCount)} câu luyện tập theo quyền hiện có.</small><a class="btn outline" href="${topicHref(t.key)}">Luyện tập chuyên đề</a></article>`).join('')}</div>${topics.length?'':'<div class="card r11-empty"><h2>Học liệu đang được cập nhật</h2><p>Chưa có chuyên đề để hiển thị. Không lấy bài chữa của câu tính phí thay vào bài giảng.</p></div>'}`;
 }
 async function loadCatalogue(){
  catalogue=await api('catalogue');
  if(catalogue.restructureEnabled!==true)throw Error('Kho học liệu mới chưa sẵn sàng. Em thử lại sau.');
  if(routeNow==='exams'){const h=await api('history');historyItems=h.items||[];drawPractice();}else drawCourses();
  if(panel&&!q('#premium-library')){panel.insertAdjacentHTML('beforeend',LearningApp.premiumLibrary());LearningApp.loadPremiumLibrary();}
 }
 function showAllocation(chosen,reconfirm=false){
  const quote=chosen.quote,selection=quote.selection||[],typed=selection.filter(i=>i.responseMode==='typed').length,choice=selection.filter(i=>i.responseMode==='choice').length;
  q('#pilot-allocation-text').innerHTML=`<div class="r11-allocation"><div><strong>${count(quote.free)}</strong>Free</div><div><strong>${count(quote.retained)}</strong>Đã nhận</div><div><strong>${count(quote.vip)}</strong>Dùng VIP</div><div><strong>${count(quote.private)}</strong>Dùng gói riêng</div></div>${selection.length?`<p>${typed} câu điền đáp án · ${choice} câu trắc nghiệm đầy đủ.</p>`:''}`;
  q('#pilot-allocation-notice').textContent=(reconfirm?'Phân bổ đã thay đổi hoặc xác nhận hết hạn. Em xem lại và xác nhận lần nữa. ':'')+(quote.private?'Xác nhận dùng lượt gói riêng còn hạn. Không chuyển tiền.':'Không trừ lượt gói riêng.');
  const dialog=q('#pilot-allocation');if(!dialog.open)dialog.showModal();
 }
 async function allocatePractice(category){
  if(busy)return;const c=capability(category);if(!c.ok)return error(c.reason);
  busy=true;controls();const chosen={kind:'practice',criteria:structuredClone(criteria(category)),intentId:crypto.randomUUID(),requestKey:crypto.randomUUID()};
  try{chosen.quote=await api('practice/quote',{...chosen.criteria,intentId:chosen.intentId});allocation=chosen;showAllocation(chosen);}catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}
 }
 async function allocate(selector){
  if(busy)return;busy=true;controls();try{const chosen={kind:'replay',selector:structuredClone(selector),requestKey:crypto.randomUUID()};chosen.quote=await api('quote',chosen.selector);allocation=chosen;showAllocation(chosen);}catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}
 }
 async function commit(){
  if(busy||!allocation)return;busy=true;controls();const chosen=allocation;
  try{
   const body=chosen.kind==='practice'?{intentId:chosen.intentId,requestKey:chosen.requestKey,quoteId:chosen.quote.quoteId,confirmWallet:chosen.quote.private>0}:{requestKey:chosen.requestKey,...chosen.selector,quoteId:chosen.quote.quoteId,confirmWallet:chosen.quote.private>0};
   const result=await api(chosen.kind==='practice'?'practice/exams':'exams',body);allocation=null;location.assign(path('lam-de',result.exam.id));
  }catch(err){
   if(err.reconfirm){
    try{chosen.quote=await api(chosen.kind==='practice'?'practice/quote':'quote',chosen.kind==='practice'?{...chosen.criteria,intentId:chosen.intentId}:chosen.selector);allocation=chosen;showAllocation(chosen,true);}catch(next){if(next.name!=='AbortError')q('#pilot-allocation-notice').textContent=next.message;}
   }else if(err.name!=='AbortError')q('#pilot-allocation-notice').textContent='Chưa nhận kết quả. Gửi lại giữ cùng mã yêu cầu, không trừ lặp. '+err.message;
  }finally{busy=false;controls();}
 }
 function drawKnowledge(){
  const fixed=course.fixed||{},mode=fixed.responseMode||'typed',guide=fixed.inputGuide||{};
  panel.innerHTML=`<a class="text-link" href="/chuyen-de/">← Chuyên đề</a><h1>${e(course.title)}</h1><p class="learning-notice">Học liệu tự biên soạn, chưa giáo viên độc lập duyệt · Câu tự luyện dưới đây miễn phí, không dùng ví, hạn mức hoặc điểm kinh nghiệm.</p><article class="r11-knowledge">${(course.sections||[]).map((s,i)=>`<section class="card card-pad r11-knowledge-section"><h2>${i+1}. ${e(s.title)}</h2>${content(s.blocks||s.body||[])}</section>`).join('')}</article><section class="r11-fixed" aria-labelledby="r11-fixed-title"><span class="tag sage">Câu riêng theo bài · Miễn phí</span><h2 id="r11-fixed-title">Câu tự luyện cố định</h2><div>${content(fixed.prompt||[])}</div>${mode==='choice'?(fixed.options||[]).map((option,i)=>`<label class="answer-choice"><input type="radio" name="r11-fixed-answer" value="${e(option)}"><b>${String.fromCharCode(65+i)}.</b> ${e(option)}</label>`).join(''):`<label class="field"><span>Đáp án của em</span><input id="r11-fixed-answer" type="text" maxlength="500" autocomplete="off" aria-describedby="r11-fixed-guide"></label><p id="r11-fixed-guide">${e(guide.instruction||'Nhập một đáp số theo đề bài.')}</p>`}<div class="pilot-actions">${button('Tự kiểm tra','fixed-check')}${button('Làm lại cùng câu','fixed-reset','','outline')}</div><p class="r11-fixed-feedback" id="r11-fixed-feedback" role="status"></p><small id="r11-fixed-progress">Đã tự kiểm tra ${count(courseProgress.attemptCount)} lần · Không thêm vào Đề đã làm</small><div id="r11-fixed-solution" class="r11-solution" hidden></div></section>`;
  bind();q('#r11-fixed-answer')?.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();checkFixed();}});
  panel.querySelectorAll('#r11-fixed-answer,[name="r11-fixed-answer"]').forEach(input=>input.addEventListener('input',()=>{if(!fixedBusy)fixedPending=null;}));
 }
 async function loadKnowledge(){
  const key=url().get('knowledgeLesson');if(!key)throw Error('Em chọn một bài trong Chuyên đề.');
  const revision=url().get('lessonRevision');const data=await api('knowledge/'+encodeURIComponent(key)+(revision?'?revision='+encodeURIComponent(revision):''));course=data.lesson;courseProgress=data.progress||{};if(!course?.lessonKey)throw Error('Bài giảng chưa sẵn sàng.');drawKnowledge();
 }
 async function checkFixed(){
  if(fixedBusy||!course)return;const answer=course.fixed?.responseMode==='choice'?(q('[name="r11-fixed-answer"]:checked')?.value||''):(q('#r11-fixed-answer')?.value||'');
  if(!fixedPending||fixedPending.answer!==answer)fixedPending={requestKey:crypto.randomUUID(),answer,lessonRevision:course.revision};
  const chosen={...fixedPending};fixedBusy=true;panel.querySelectorAll('.r11-fixed input,.r11-fixed button').forEach(b=>b.disabled=true);
  try{
   const data=await api('knowledge/'+encodeURIComponent(course.lessonKey)+'/check',chosen);courseProgress={completed:true,attemptCount:data.attemptCount};
   q('#r11-fixed-feedback').textContent=data.correct?'Đúng rồi! Em xem cách thử lại hoặc làm lại cùng câu.':'Chưa đúng. Em xem hướng dẫn và thử lại cùng câu nhé.';
   q('#r11-fixed-progress').textContent=`Đã tự kiểm tra ${count(data.attemptCount)} lần · Không dùng ví, hạn mức, điểm kinh nghiệm hoặc Đề đã làm`;
   const solution=q('#r11-fixed-solution');solution.hidden=false;
   const parts=Array.isArray(data.solution)&&data.solution.every(s=>s&&s.title&&Array.isArray(s.blocks))?data.solution:data.solution?.sections;
   solution.innerHTML=`<h2>Hướng dẫn và lời giải miễn phí</h2>${solutionView.answer(data.expectedAnswer??data.answer??'','Đáp án')}${parts?parts.map((s,i)=>`<section class="card card-pad pilot-lesson-section"><h3>${i+1}. ${e(s.title)}</h3>${content(s.blocks||[])}</section>`).join(''):`<section class="card card-pad">${content(data.solution||[])}</section>`}`;
  }catch(err){if(err.name!=='AbortError')q('#r11-fixed-feedback').textContent='Chưa nhận kết quả. Thử lại giữ cùng câu và yêu cầu. '+err.message;}
  finally{fixedBusy=false;panel?.querySelectorAll('.r11-fixed input,.r11-fixed button').forEach(b=>b.disabled=false);}
 }
 function resetFixed(){
  if(fixedBusy)return;fixedPending=null;if(q('#r11-fixed-answer'))q('#r11-fixed-answer').value='';panel.querySelectorAll('[name="r11-fixed-answer"]').forEach(i=>i.checked=false);q('#r11-fixed-feedback').textContent='Vẫn cùng câu cố định. Em làm lại miễn phí, không mất lượt.';q('#r11-fixed-solution').hidden=true;q('#r11-fixed-solution').replaceChildren();
 }

 function status(){const box=q('#pilot-save-status');if(box)box.textContent=saveError?'Chưa lưu được; đáp án vẫn ở màn này.':pending.size||saving?'Đang lưu…':'Đã lưu trên máy chủ';const retry=q('[data-pilot="retry-save"]');if(retry)retry.hidden=!saveError;}
 async function flush(){if(saving)return saving;if(!pending.size||!exam||exam.submittedAt){status();return;}const g=generation,eid=exam.id;
  saving=(async()=>{while(pending.size&&g===generation){const [position,answer]=pending.entries().next().value;pending.delete(position);status();try{const result=await api('exams/'+eid+'/answers',{position,answer});if(result.exam.submittedAt){exam=result.exam;pending.clear();await drawResults();return;}saveError=false;}catch(err){if(g!==generation)return;if(!pending.has(position))pending.set(position,answer);saveError=true;error(err.message);break;}}})();try{await saving;}finally{saving=null;status();}}
 function changed(value){const position=index+1;exam.answers[String(position)]=value;pending.set(position,value);saveError=false;panel.querySelectorAll('[data-pilot=question]').forEach(nav=>{const i=Number(nav.dataset.index),done=Boolean(String(exam.answers[exam.questions[i].id]??'').trim());nav.classList.toggle('done',done);nav.setAttribute('aria-label','Câu '+(i+1)+(done?' · Đã trả lời':' · Chưa trả lời'));});status();flush();}
 function drawExam(){
  if(exam.submittedAt){drawResults();return;}index=Math.max(0,Math.min(index,exam.questions.length-1));const item=exam.questions[index],guide=item.inputGuide||{instruction:'Nhập đáp án theo đề.',labels:[],units:[]};
  panel.innerHTML=`<a class="text-link" href="/thi-thu/">← Về luyện tập</a><h1>Bài luyện tập thí điểm</h1>${note()}<div class="grid-wide"><section class="card card-pad question"><p>Câu ${index+1} / ${exam.questions.length}</p><fieldset><legend id="pilot-question" tabindex="-1">${e(item.text)}</legend><div class="pilot-answer">${(item.responseMode||exam.responseMode)==='typed'?`<p id="pilot-guide">${e(guide.instruction)}<br>${guide.labels.map((l,i)=>e(l)+': '+e(guide.units[i])).join(' · ')}</p><label class="field"><span>Đáp án của em</span><input id="pilot-typed-answer" type="text" maxlength="500" autocomplete="off" aria-describedby="pilot-guide" value="${e(exam.answers[item.id]??'')}"></label>`:item.options.map((option,n)=>`<label class="answer-choice"><input type="radio" name="pilot-answer" value="${e(option)}" ${exam.answers[item.id]===option?'checked':''}><b>${String.fromCharCode(65+n)}.</b> ${e(option)}</label>`).join('')}</div></fieldset>${PracticeScratchpad.markup()}<div class="pilot-actions">${button('Câu trước','previous','','outline')}${button('Câu tiếp','next')}</div></section><aside class="card card-pad self-start"><h2>Phiếu làm bài</h2><p id="pilot-timer"></p><div class="question-grid">${exam.questions.map((v,n)=>`<button type="button" class="${n===index?'current ':''}${String(exam.answers[v.id]??'').trim()?'done':''}" data-pilot="question" data-index="${n}" aria-current="${n===index?'step':'false'}" aria-label="Câu ${n+1}${String(exam.answers[v.id]??'').trim()?' · Đã trả lời':' · Chưa trả lời'}">${n+1}</button>`).join('')}</div><p id="pilot-save-status" role="status"></p>${button('Thử lưu lại','retry-save','','outline')}<div class="practice-export-actions">${button('Nộp bài','submit')}${PlatformAPI.snapshot.practiceExport?.enabled&&typeof PracticeExport!=='undefined'?PracticeExport.button('pilot',exam.id):''}</div></aside></div><dialog id="pilot-submit" aria-labelledby="pilot-submit-title"><h2 id="pilot-submit-title">Nộp bài để xem kết quả?</h2><p id="pilot-submit-note"></p><div class="pilot-actions">${button('Tiếp tục làm','cancel-submit','','outline')}${button('Xác nhận nộp','confirm-submit')}</div></dialog>`;
  PracticeScratchpad.mount('pilot:'+exam.id+':'+(index+1));bind();q('[data-pilot="previous"]').disabled=index===0;q('[data-pilot="next"]').disabled=index===exam.questions.length-1;status();
  q('#pilot-typed-answer')?.addEventListener('input',ev=>changed(ev.target.value));q('#pilot-typed-answer')?.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();flush();}});panel.querySelectorAll('[name="pilot-answer"]').forEach(input=>input.addEventListener('change',()=>changed(input.value)));
 }
 async function drawResults(){
  const result=await api('exams/'+exam.id+'/review');exam=result.exam;
  panel.innerHTML=`<a class="text-link" href="/thi-thu/">← Về luyện tập</a><h1>Kết quả thí điểm</h1>${note()}<section class="result-band sage"><div class="score-circle"><strong id="pilot-score">${exam.score}<span>/10</span></strong><small>Điểm ở kho thí điểm</small></div><p>${exam.correct} / ${exam.questions.length} câu đúng · Không thay điểm kinh nghiệm hoặc xếp hạng chính.</p></section>${button('Làm lại đúng phiên bản','replay','','outline')}<div class="solution-list">${exam.questions.map((item,n)=>`<article class="card card-pad solution pilot-review"><h2>Câu ${n+1} · ${item.correct?'Đúng':'Xem lại'}</h2><p>${e(item.text)}</p><p>Em nhập: ${e(exam.answers[item.id]??'chưa trả lời')}</p>${solutionView.answer(item.answer,'Đáp án')}<ol>${(item.steps||[]).map(step=>`<li>${solutionView.text(step)}</li>`).join('')}</ol><a class="btn outline" href="/bai-giang/?pilotLesson=${encodeURIComponent(result.contentKeys[n])}&pilotExam=${encodeURIComponent(exam.id)}">Đọc bài giảng ba phần và hình</a></article>`).join('')}</div>${allocationHTML()}`;bind();
 }
 function block(value,eid,key){
  if(Array.isArray(value))return value.map(v=>block(v,eid,key)).join('');if(typeof value==='string'||typeof value==='number')return solutionView.text(value);if(!value||typeof value!=='object')return '';if(value.type==='math')return `<span class="math">${e(value.text||value.latex||'')}</span>`;
  if(value.type==='text')return solutionView.text(value.text);
  if(value.type==='media'){
   const resource=eid&&typeof eid==='object'?`/api/local-pilot/knowledge/${encodeURIComponent(eid.lessonKey)}/asset?revision=${encodeURIComponent(eid.revision)}&sha=${encodeURIComponent(value.sha256)}`:`/api/local-pilot/exams/${eid}/asset?contentKey=${encodeURIComponent(key)}&sha=${encodeURIComponent(value.sha256)}`;
   return solutionView.figure(resource,value.alt||'Hình minh họa',`<a href="${e(resource)}" target="_blank" rel="noopener">Mở hình gốc</a>`);
  }
  const tag=['p','strong','em','ol','ul','li','aside','h3','h4','figure','figcaption','div','span','br','table','thead','tbody','tr','th','td','caption','code'].includes(value.tag)?value.tag:'div';return `<${tag}${solutionView.blockClass(value)}>${block(value.children||[],eid,key)}</${tag}>`;
 }
 async function drawLesson(){const eid=url().get('pilotExam'),key=url().get('pilotLesson');if(!/^\d+$/.test(eid||''))throw Error('Mở bài giảng từ kết quả đã nộp.');const data=await api('exams/'+eid+'/lesson?contentKey='+encodeURIComponent(key)),lesson=data.lesson;panel.innerHTML=`<a class="text-link" href="${path('ket-qua-thi',eid)}">← Kết quả bài đã nộp</a><h1>${e(displayTitle(lesson.title))}</h1>${note()}<p>${e(lesson.sourceLabel)}</p><section class="card card-pad">${block(lesson.prompt,eid,key)}${block(lesson.overview,eid,key)}</section>${lesson.sections.map((s,n)=>`<section class="card card-pad pilot-lesson-section"><h2>${n+1}. ${e(s.title)}</h2>${block(s.blocks,eid,key)}</section>`).join('')}`;}
 function bind(){panel.querySelectorAll('button[data-pilot]').forEach(b=>b.onclick=()=>action(b));}
 async function action(b){const kind=b.dataset.pilot;
  if(kind==='practice-create')return allocatePractice(b.dataset.category);if(kind==='wallet-detail'){const box=q('#r11-wallet-detail');box.hidden=!box.hidden;walletExpanded=!box.hidden;b.setAttribute('aria-expanded',String(!box.hidden));return;}if(kind==='fixed-check')return checkFixed();if(kind==='fixed-reset')return resetFixed();if(kind==='allocate')return allocate(JSON.parse(b.dataset.selector));if(kind==='commit')return commit();if(kind==='cancel-allocation'){q('#pilot-allocation').close();allocation=null;return;}
  if(kind==='retry-save')return flush();if(kind==='cancel-submit'){q('#pilot-submit').close();return;}
  if(['previous','next','question'].includes(kind)){index=kind==='question'?Number(b.dataset.index):index+(kind==='next'?1:-1);drawExam();q('#pilot-typed-answer')?.focus({preventScroll:true});return;}
  if(kind==='submit'){await flush();if(pending.size)return error('Còn đáp án chưa lưu. Thử lưu lại trước khi nộp.');q('#pilot-submit-note').textContent=`Đã trả lời ${Object.values(exam.answers).filter(v=>String(v).trim()).length}/${exam.questions.length} câu. Sau khi nộp không sửa bài này.`;q('#pilot-submit').showModal();return;}
  if(kind==='replay')return allocate({replayExamId:Number(exam.id)});
  if(busy)return;busy=true;controls();try{
   if(kind==='confirm-submit'){await flush();if(pending.size)throw Error('Còn đáp án chưa lưu.');exam=(await api('exams/'+exam.id+'/submit',{})).exam;location.assign(path('ket-qua-thi',exam.id));return;}
   if(kind==='buy'){const requestKey=b.dataset.requestKey||(b.dataset.requestKey=crypto.randomUUID());await api('orders',{requestKey,sku:'qa.questions.100'});await loadCatalogue();}
   else if(kind==='mock-confirm'||kind==='mock-fail'){await api(kind,{orderId:b.dataset.order});await loadCatalogue();}
  }catch(err){error(err.message);}finally{busy=false;controls();}
 }
 function unmount(){PracticeScratchpad.unmount();generation++;clearInterval(timer);timer=null;panel=null;}
 async function mount(route){if(!handles(route))return;routeNow=route;panel=document.getElementById('local-pilot');if(!panel)return;const g=++generation;owner=PlatformAPI.snapshot.account?.id;csrf=PlatformAPI.snapshot.csrf;pending=new Map();saving=null;saveError=false;allocation=null;busy=false;exam=null;index=0;course=null;courseProgress={};fixedPending=null;fixedBusy=false;
  try{if(requested(route)){if(route==='lesson'&&url().has('knowledgeLesson'))await loadKnowledge();else if(route==='lesson')await drawLesson();else{exam=(await api('exams/'+url().get('pilotExam'))).exam;exam.submittedAt?await drawResults():drawExam();timer=setInterval(async()=>{if(g!==generation||!exam||exam.submittedAt)return;const left=Math.max(0,Math.ceil((exam.expiresAt-Date.now())/1000));if(q('#pilot-timer'))q('#pilot-timer').textContent=`Còn ${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`;if(!left&&!busy){busy=true;try{exam=(await api('exams/'+exam.id)).exam;if(exam.submittedAt)await drawResults();}catch(err){error(err.message);}finally{busy=false;}}},500);}}else await loadCatalogue();}
  catch(err){if(g===generation&&panel)panel.innerHTML=`<h2>Học liệu thí điểm lớp 5</h2>${note()}<p role="alert">${e(err.message)}</p>`;}
 }
 document.addEventListener('click',event=>{const anchor=event.target.closest?.('a[href]');if(anchor&&panel&&exam&&!exam.submittedAt&&(pending.size||saving)){event.preventDefault();event.stopImmediatePropagation();flush().then(()=>{if(!pending.size&&!saveError)location.assign(anchor.href);else error('Còn đáp án chưa lưu. Thử lưu lại trước khi rời bài.');});}},true);
 window.addEventListener('beforeunload',event=>{if(panel&&(pending.size||saving)){event.preventDefault();event.returnValue='';}});
 return {enabled,requested,handles,shell,mount,unmount};
})();
