/* Native module within the existing learning shell; no iframe, profile impersonation or main-state mutation. */
'use strict';
const LocalPilot=(()=>{
 let generation=0,panel=null,busy=false,catalogue=null,exam=null,index=0,pending=new Map(),saving=null,saveError=false,saveConflict=false,conflictSnapshot=null,allocation=null,timer=null,owner=null,csrf=null,routeNow='',criteriaState={pool:'all',count:10,scope:'topic',topicKey:'',difficulty:'',school:'cau-giay',initialized:false},historyItems=[],historyFilter='all',historySearch='',course=null,courseProgress={},fixedPending=null,fixedBusy=false,walletExpanded=false;
 let stickyWatch=null,wrongOnly=false,lessonStudyCleanup=null;
 let boughtExams=[];
 const nonce=()=>globalThis.crypto?.randomUUID?.()||Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)),v=>v.toString(16).padStart(2,'0')).join('');
 const solutionView=window.SolutionView;
 const studySolution=window.StudySolution;
 const retakeKeys=new Map();
 async function retakeOwned(identity){
  const eid=String(identity);if(!/^[1-9][0-9]*$/.test(eid))throw Error('Mã đề làm lại không hợp lệ.');
  const actor=PlatformAPI.snapshot.account?.id,context=PlatformAPI.familyContext,token=PlatformAPI.snapshot.csrf,key=[actor,context,eid].join(':');
  if(!actor||!token)throw Error('Em hãy đăng nhập để làm lại đề.');
  const requestKey=retakeKeys.get(key)||nonce();retakeKeys.set(key,requestKey);
  const response=await fetch('/api/local-pilot/exams/'+eid+'/retake',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':token,...(context?{'X-Family-Context':context}:{})},body:JSON.stringify({requestKey})});
  const result=await response.json();if(result.familyAccessChanged){PlatformAPI.invalidateFamily();throw new DOMException('Quyền gia đình đã đổi.','AbortError');}
  if(actor!==PlatformAPI.snapshot.account?.id||context!==PlatformAPI.familyContext||token!==PlatformAPI.snapshot.csrf)throw new DOMException('Hồ sơ đã đổi.','AbortError');
  if(!response.ok)throw Error(result.error||'Chưa thể mở lại đề.');
  location.assign(path('lam-de',result.exam.id));return result;
 }
 const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const displayTitle=value=>String(value).replace(/— (?:free|vip)\.(?:parts|unit|reverse)\.(\d+)$/,'— Bài $1');
 const q=s=>panel?.querySelector(s),url=()=>new URLSearchParams(location.search),enabled=()=>PlatformAPI.snapshot.localPilotEnabled===true;
 const requested=route=>(['testing','results'].includes(route)&&url().has('pilotExam'))||(route==='lesson'&&(url().has('pilotLesson')||url().has('knowledgeLesson')));
 const handles=route=>enabled()&&(requested(route)||(PlatformAPI.snapshot.curriculumSamples?.enabled&&route==='exams')||(Number(PlatformAPI.snapshot.state?.grade)===5&&['exams','weekly','topics'].includes(route)));
 const shell=()=>'<section id="local-pilot" class="local-pilot" aria-label="Học tập theo lớp"><p role="status">Đang tải học liệu thí điểm…</p></section>';
 const path=(route,id)=>'/'+route+'/?pilotExam='+encodeURIComponent(id);
 const button=(label,action,extra='',kind='dark')=>UIControls.markup(label,{kind,actionAttribute:'data-pilot',action,extra});
 const note=()=>'<p class="learning-notice">Mẫu Toán lớp '+e(catalogue?.grade||PlatformAPI.snapshot.state?.grade||5)+' · Tự biên soạn, đã tự kiểm, chờ giáo viên duyệt.</p>';
 async function api(route,body){
  const g=generation,context=PlatformAPI.familyContext;const response=await fetch('/api/local-pilot/'+route,{credentials:'same-origin',cache:'no-store',headers:{...(context?{'X-Family-Context':context}:{}),...(body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf||''})},...(body===undefined?{}:{method:'POST',body:JSON.stringify(body)})});
  const value=await response.json();
  if(value.familyAccessChanged){PlatformAPI.invalidateFamily();throw new DOMException('Quyền gia đình đã thay đổi.','AbortError');}
  if(g!==generation||owner!==PlatformAPI.snapshot.account?.id||csrf!==PlatformAPI.snapshot.csrf||context!==PlatformAPI.familyContext)throw new DOMException('Phiên đã thay đổi.','AbortError');
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
  const hasTestPacks=Boolean(state.packs?.length);
  return `<section class="r11-wallet" aria-label="Hạn mức luyện tập VIP"><h2>Hạn mức luyện tập VIP</h2><div class="r11-wallet-stats"><span>VIP ngày đã dùng <b>${vip.active?count(vip.dayUsed)+'/'+count(vip.dayLimit||30):'—'}</b></span><span>Chu kỳ đã dùng <b>${vip.active?count(vip.cycleUsed)+'/'+count(vip.cycleLimit||300):'—'}</b></span>${hasTestPacks?`<span>Ví mô phỏng còn <b>${count(state.privateRemaining)} câu</b></span>`:''}</div>${button('Chi tiết','wallet-detail',`aria-controls="r11-wallet-detail" aria-expanded="${walletExpanded}"`,'outline')}</section><section id="r11-wallet-detail" class="r11-wallet-detail" ${walletExpanded?'':'hidden'}><h3>${e(catalogue.role)}${unlimited?' · quyền nội bộ, không trừ ví':''}</h3><p>${e(catalogue.cycleNotice)}</p><p>VIP: tối đa ${count(vip.dayLimit||30)} câu mới/ngày và ${count(vip.cycleLimit||300)} câu mới cho cả chu kỳ ${vip.cyclePeriod==='year'?'12 tháng (không đặt lại mỗi tháng)':'30 ngày'}. Câu Free, câu đã nhận và xem lại không trừ thêm.</p><p>VIP hết hạn ${e(time(vip.vipExpiresAt))}</p>${hasTestPacks?`<h4>Ví mô phỏng từ đợt thí điểm</h4>${state.packs.map(p=>`<p>${count(p.remaining)} câu · hạn ${e(time(p.expires_at))}${p.usable?'':' · không dùng được'}</p>`).join('')}`:''}</section>`;
 }
 function selectedFunding(){
  const sku=criteriaState.funding,credits=catalogue.purchasedCredits;
  if(!sku||credits?.available===false||!credits?.products?.some(product=>product.sku===sku&&product.eligible))return '';
  const remaining=sku==='questions-100'?credits.questionsRemaining:credits.examsRemaining;
  return remaining>0&&catalogue.purchasedPractice?.[sku]?sku:'';
 }
 function practiceCounts(){
  const sku=selectedFunding();
  const product=catalogue.purchasedCredits?.products?.find(item=>item.sku===sku);
  return product?.eligibleCounts?.length?product.eligibleCounts:(catalogue.practiceCounts||[1,2,3,5,10]);
 }
 const selectedCount=()=>practiceCounts().includes(count(criteriaState.count))?count(criteriaState.count):practiceCounts().at(-1);
 function availableQuestions(category){
  const paid=catalogue.purchasedPractice?.[selectedFunding()];
  const eligibility=paid?new Map(paid.questions.map(item=>[item.contentKey,item])):null;
  let items=(catalogue.questions||[]).map(item=>eligibility?{...item,eligible:false,...eligibility.get(item.contentKey)}:item).filter(x=>x.eligible===true&&(category!=='content'||criteriaState.scope==='weekly'||x.topicKey===criteriaState.topicKey));
  if(criteriaState.pool!=='all')items=items.filter(x=>String(x.access).toLowerCase()===(criteriaState.pool==='free'?'free':'vip'));
  if(category==='combined'&&criteriaState.difficulty){
   if(items.some(x=>x.difficulty===undefined))return null;
   items=items.filter(x=>Number(x.difficulty)===Number(criteriaState.difficulty));
  }
  return items;
 }
 function capability(category){
  if(category==='school'&&selectedFunding())return {ok:false,reason:'Lượt đã mua dùng cho Ôn theo nội dung hoặc Đề tổng hợp.'};
  if(category==='school'&&!catalogue.schoolAccess)return {ok:false,reason:'Ôn đề theo trường dành cho VIP+. Vào Nâng cấp gói để mở quyền.'};
  if(category==='school'&&!catalogue.schoolReady)return {ok:false,reason:'Chưa có cấu trúc và bộ câu theo trường được duyệt. Chưa tạo đề hoặc trừ lượt.'};
  if(category==='content'&&criteriaState.scope==='weekly'&&!catalogue.weekReady)return {ok:false,reason:'Học liệu chưa được đối chiếu theo tuần. Em có thể chọn Chuyên đề để luyện nội dung hiện có.'};
  const items=availableQuestions(category);
  if(items===null)return {ok:false,reason:'Mức độ này chưa có đầy đủ thông tin phân loại cho bộ lọc. Em chọn Tất cả mức độ để tiếp tục.'};
  const n=selectedCount(),budget=catalogue.purchasedPractice?.[selectedFunding()]?.practiceBudget||catalogue.practiceBudget;
  const available=items.filter(x=>x.cost===0).length+Math.min(count(budget?.newPaidAvailable),items.filter(x=>x.cost===1).length);
  if(available<n)return {ok:false,reason:`Chỉ có ${available} câu phù hợp, chưa đủ ${n} câu. Giảm số câu hoặc mở rộng bộ lọc; chưa cấp đề, chưa trừ lượt.`};
  return {ok:true,reason:`Có ${available} câu trong bộ lọc. Đề ${n} câu dùng dạng trả lời phù hợp từng câu.`};
 }
 function criteria(category){
  const funding=selectedFunding();
  const selected={category,count:selectedCount(),pool:criteriaState.pool,...(funding?{funding}:{})};
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
  const c=catalogue,topics=c.topics||[],funding=selectedFunding();
  const fundingMarkup=window.FamilyCart?.fundingPanel(c.purchasedCredits,funding,'pilot-exam-funding');
  if(!criteriaState.topicKey||!topics.some(t=>t.key===criteriaState.topicKey))criteriaState.topicKey=topics[0]?.key||'';
  const requestedTopic=url().get('topicKey');
  if(!criteriaState.initialized&&topics.some(t=>t.key===requestedTopic))criteriaState.topicKey=requestedTopic;
  criteriaState.initialized=true;
  panel.innerHTML=`<div class="intro"><div><h1>Luyện tập</h1><p>Chọn nội dung, làm đề và xem lại lời giải.</p></div><span class="tag sage">Khối ${e(c.grade||5)}</span></div>${c.curriculumSamples?`<p class="learning-notice">${e(c.notice)}</p>`:''}${walletHTML(c.wallet)}<section class="card card-pad purchased-practice" id="pilot-purchased-exams" hidden></section>${fundingMarkup?`<section class="card card-pad purchased-practice" id="pilot-purchased-practice">${fundingMarkup}</section>`:''}<section class="card card-pad r11-config" aria-label="Cấu hình đề">${field('Ngân hàng câu luyện tập','exam-pool',[['all','Free và tính phí'],['free','Chỉ câu Free'],['paid','Chỉ câu tính phí']],criteriaState.pool)}${field('Số câu','exam-count',practiceCounts().map(n=>[n,n+' câu']),selectedCount())}<p class="r11-policy-note">${c.curriculumSamples?'Bộ mẫu này dùng trắc nghiệm bốn phương án. Câu Free gồm Cơ bản và Nâng cao; câu tính phí gồm mức 7–8 và Học Sinh Giỏi 9–10.':'Mỗi câu dùng hình thức phù hợp: một đáp số điền đáp án; nhiều ý chọn một phương án đủ kết quả.'}</p></section><div class="r11-forms"><section class="card card-pad r11-form"><span class="tile" aria-hidden="true">◎</span><h2>Ôn theo nội dung</h2><p>Luyện theo chương trình trên lớp hoặc chuyên đề.</p>${field('Phạm vi','exam-scope',[['topic','Chuyên đề'],['weekly','Theo chương trình học trên lớp']],criteriaState.scope)}<label class="field"><span>Nội dung · Tìm kiếm</span><input id="exam-content-search" type="search" placeholder="Tìm nội dung"></label>${field('Nội dung','exam-topic',topics.map(t=>[t.key,t.title]),criteriaState.topicKey)}<p class="r11-capability" id="r11-content-capability">${e(capability('content').reason)}</p><div class="r11-form-actions">${createButton('Tạo đề theo nội dung','content')}</div></section><section class="card card-pad r11-form"><span class="tile peach" aria-hidden="true">▤</span><h2>Đề tổng hợp</h2><p>Kết hợp các nội dung trong ngân hàng học liệu tự biên soạn, không phải đề chính thức.</p>${field('Độ khó','exam-difficulty',[['','Tất cả mức độ'],[1,'Cơ bản'],[2,'Nâng cao'],[3,c.curriculumSamples?'Khó · 7–8':'Khó'],[4,c.curriculumSamples?'Học Sinh Giỏi · 9–10':'Tư duy']],criteriaState.difficulty)}<p class="r11-capability">${e(capability('combined').reason)}</p><div class="r11-form-actions">${createButton('Tạo đề ngẫu nhiên','combined')}</div></section><section class="card card-pad r11-form"><span class="tile sand" aria-hidden="true">⌑</span><h2>Đề theo trường</h2><p>Dành cho khối 5; cần bộ câu và cấu trúc trường đã được duyệt.</p>${field('Trường','exam-school',[['cau-giay','THCS Cầu Giấy'],['ngoai-ngu','THCS Ngoại ngữ'],['ntt','Nguyễn Tất Thành']],criteriaState.school)}<p class="r11-capability">${e(capability('school').reason)}</p><div class="r11-form-actions">${createButton('Luyện đề theo trường','school')}</div></section></div><section class="card card-pad practice-lookup"><h2>Tra cứu câu hỏi</h2><p>Xem lại câu hỏi bằng mã khi cần ôn tập.</p><a class="btn outline" href="/tra-cuu-cau-hoi/">Tra cứu mã câu hỏi</a></section><section id="r11-history" aria-labelledby="r11-history-title"><h2 id="r11-history-title">Đề đã làm</h2><div class="r11-history-tools">${field('Hiển thị','r11-history-filter',[['all','Tất cả'],['completed','Đã nộp'],['pending','Đang làm']],historyFilter)}<label class="field r11-history-search"><span>Tìm đề</span><input id="r11-history-search" type="search" value="${e(historySearch)}" placeholder="Tên đề hoặc nội dung"></label></div><div class="card" id="r11-history-list"></div></section>${allocationHTML()}`;
  bind();bindFilters();drawHistory();
  window.FamilyCart?.mountPurchasedExams(q('#pilot-purchased-exams'),boughtExams,exam=>location.assign('/lam-de/?id='+encodeURIComponent(exam.id)));
 }
 function drawHistory(){
  const filtered=historyItems.filter(x=>(historyFilter==='all'||(historyFilter==='completed'?Boolean(x.submitted):!x.submitted||Boolean(x.activeRetakeId)))&&String(x.title||'').toLocaleLowerCase('vi').includes(historySearch.toLocaleLowerCase('vi')));
  const box=q('#r11-history-list');if(!box)return;
  box.innerHTML=filtered.map(item=>{
   if(!['main','pilot'].includes(item.provider)||!/^\d+$/.test(String(item.id)))return '';
   const target=item.activeRetakeId||item.id,hasActive=Boolean(item.activeRetakeId)||!item.submitted;const href=item.provider==='pilot'?path(hasActive?'lam-de':'ket-qua-thi',target):'/'+(hasActive?'lam-de':'ket-qua-thi')+'/?id='+encodeURIComponent(target);
   const format=item.responseMode==='mixed'?'Trắc nghiệm và điền đáp án':item.responseMode==='choice'?'Trắc nghiệm':'Điền đáp án';
   return `<div class="r11-history-row" data-reference="${e(item.reference)}"><div><strong>${e(item.title)} <span class="tag ${item.submitted?'sage':'peach'}">${item.submitted?e(item.score)+'/10':'Đang làm'}</span></strong><small>${e(format)} · ${e(time(item.submittedAt||item.startedAt))}</small></div><a class="btn outline" href="${href}">${hasActive?'Làm tiếp':'Xem lại'}</a></div>`;
  }).join('')||`<div class="r11-empty"><h3>${historyItems.length?'Chưa có đề khớp bộ lọc':'Em chưa có đề đã làm'}</h3><p>${historyItems.length?'Thử từ khác hoặc chọn Tất cả.':'Chọn nội dung phía trên để bắt đầu. Bài làm mới và trước đây cùng xuất hiện ở đây.'}</p></div>`;
 }
 function bindFilters(){
  const ids={'exam-pool':'pool','exam-count':'count','exam-scope':'scope','exam-topic':'topicKey','exam-difficulty':'difficulty','exam-school':'school'};
  for(const [id,key] of Object.entries(ids))q('#'+id)?.addEventListener('change',ev=>{criteriaState[key]=ev.target.value;drawPractice();});
  q('#pilot-exam-funding')?.addEventListener('change',ev=>{criteriaState.funding=ev.target.value;drawPractice();q('#pilot-exam-funding')?.focus({preventScroll:true});});
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
  panel.innerHTML=`<div class="intro"><div><h1>Bài giảng</h1><p>Đọc bài giảng, hiểu phương pháp và tự luyện những câu miễn phí trong từng bài.</p></div><span class="tag sage">Khối 5</span></div><nav class="r11-tabs" aria-label="Tìm bài giảng"><a class="btn ${routeNow==='weekly'?'dark':'outline'}" href="/hoc-theo-tuan/">Theo tuần</a><a class="btn ${routeNow==='topics'?'dark':'outline'}" href="/chuyen-de/">Chuyên đề</a></nav>${routeNow==='weekly'&&!catalogue.weekReady?'<p class="learning-notice">Khung tuần đang chờ đối chiếu chương trình. Em có thể chọn một chuyên đề bên dưới; đây không phải lịch tuần SGK.</p>':''}<div class="r11-topics">${topics.map((t,i)=>`<article class="card card-pad r11-topic"><span class="r11-topic-icon" aria-hidden="true">${String(i+1).padStart(2,'0')}</span><h2>${e(t.title)}</h2><p>Lý thuyết · Định hướng tư duy · Câu tự luyện cố định miễn phí.</p><div class="r11-course-list">${lessons.filter(l=>l.topicKey===t.key).map(l=>`<a class="r11-course-link" href="${courseHref(l.lessonKey,l.revision)}"><strong>${e(l.title)}</strong><small>${l.completed?'Đã học':'Học và tự kiểm tra'} · Miễn phí</small></a>`).join('')||'<p>Học liệu đang được cập nhật.</p>'}</div><small>${count(t.availableCount)} câu luyện tập theo quyền hiện có.</small><a class="btn outline" href="${topicHref(t.key)}">Luyện tập chuyên đề</a></article>`).join('')}</div>${topics.length?'':'<div class="card r11-empty"><h2>Học liệu đang được cập nhật</h2><p>Chưa có chuyên đề để hiển thị. Không lấy bài chữa của câu tính phí thay vào bài giảng.</p></div>'}`;
 }
 async function loadCatalogue(){
  catalogue=await api('catalogue');
  if(catalogue.restructureEnabled!==true)throw Error('Kho học liệu mới chưa sẵn sàng. Em thử lại sau.');
  if(routeNow==='exams'){
   const g=generation;
   const [history,premium]=await Promise.all([api('history'),PlatformAPI.request('premium',undefined,{owner}).catch(()=>null)]);
   if(g!==generation||!panel)return;
   historyItems=history.items||[];boughtExams=premium?.purchases||[];drawPractice();
  }else drawCourses();
 }
 function showAllocation(chosen,reconfirm=false){
  const quote=chosen.quote,selection=quote.selection||[],typed=selection.filter(i=>i.responseMode==='typed').length,choice=selection.filter(i=>i.responseMode==='choice').length;
  const paid=quote.purchased,unit=paid?.sku==='questions-100'?'câu luyện tập':'lượt tạo đề tự chọn';
  const summary=paid?`<p>Dùng <strong>${count(paid.quantity)} ${unit}</strong> để tạo đề ${chosen.criteria.count} câu. Sau khi tạo còn <strong>${count(paid.remainingAfter)} ${unit}</strong>.</p>`:`<div class="r11-allocation"><div><strong>${count(quote.free)}</strong>Free</div><div><strong>${count(quote.retained)}</strong>Đã nhận</div><div><strong>${count(quote.vip)}</strong>Dùng VIP</div><div><strong>${count(quote.private)}</strong>Dùng ví mô phỏng</div></div>`;
  q('#pilot-allocation-text').innerHTML=summary+(selection.length?`<p>${typed} câu điền đáp án · ${choice} câu trắc nghiệm đầy đủ.</p>`:'');
  const message=paid?'':quote.private?'Xác nhận dùng lượt trong ví mô phỏng.':'Không trừ lượt đã mua.';
  q('#pilot-allocation-notice').textContent=(reconfirm?'Phân bổ đã thay đổi hoặc xác nhận hết hạn. Em xem lại và xác nhận lần nữa. ':'')+message;
  q('[data-pilot="commit"]').dataset.unavailable='false';
  const dialog=q('#pilot-allocation');if(!dialog.open)dialog.showModal();
 }
 async function allocatePractice(category){
  if(busy)return;const c=capability(category);if(!c.ok)return error(c.reason);
  busy=true;controls();const chosen={kind:'practice',criteria:structuredClone(criteria(category)),intentId:nonce(),requestKey:nonce()};
  try{chosen.quote=await api('practice/quote',{...chosen.criteria,intentId:chosen.intentId});allocation=chosen;showAllocation(chosen);}catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}
 }
 async function allocate(selector){
  if(busy)return;busy=true;controls();try{const chosen={kind:'replay',selector:structuredClone(selector),requestKey:nonce()};chosen.quote=await api('quote',chosen.selector);allocation=chosen;showAllocation(chosen);}catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}
 }
 async function commit(){
  if(busy||!allocation)return;busy=true;controls();const chosen=allocation;
  try{
   const body=chosen.kind==='practice'?{intentId:chosen.intentId,requestKey:chosen.requestKey,quoteId:chosen.quote.quoteId,confirmWallet:chosen.quote.private>0}:{requestKey:chosen.requestKey,...chosen.selector,quoteId:chosen.quote.quoteId,confirmWallet:chosen.quote.private>0};
   if(chosen.criteria?.funding)Object.assign(body,{funding:chosen.criteria.funding,confirmPurchased:true});
   const result=await api(chosen.kind==='practice'?'practice/exams':'exams',body);allocation=null;location.assign(path('lam-de',result.exam.id));
  }catch(err){
   if(err.reconfirm){
    try{chosen.quote=await api(chosen.kind==='practice'?'practice/quote':'quote',chosen.kind==='practice'?{...chosen.criteria,intentId:chosen.intentId}:chosen.selector);allocation=chosen;showAllocation(chosen,true);}catch(next){if(next.name!=='AbortError'){q('#pilot-allocation-notice').textContent=next.message;q('[data-pilot="commit"]').dataset.unavailable='true';}}
   }else if(err.name!=='AbortError')q('#pilot-allocation-notice').textContent='Chưa nhận kết quả. Gửi lại giữ cùng mã yêu cầu, không trừ lặp. '+err.message;
  }finally{busy=false;controls();}
 }
 function drawKnowledge(){
  const fixed=course.fixed||{},mode=fixed.responseMode||'typed',guide=fixed.inputGuide||{};
  const lesson=course,bunnyVideo=lesson.video?.provider==='bunny';
  panel.innerHTML=`<a class="text-link" href="/chuyen-de/">← Chuyên đề</a><h1>${e(course.title)}</h1><p class="learning-notice">Học liệu tự biên soạn, chưa giáo viên độc lập duyệt · Câu tự luyện dưới đây miễn phí, không dùng ví, hạn mức hoặc điểm kinh nghiệm.</p>${window.LessonStudy.render({completed:courseProgress.completed,videoRef:course.videoRef,videoTitle:course.title,bunnyVideo,exerciseAvailable:Boolean(fixed.questionKey),exerciseTarget:'r11-fixed',materials:course.materials})}<article class="r11-knowledge">${(course.sections||[]).map((s,i)=>`<section class="card card-pad r11-knowledge-section"><h2>${i+1}. ${e(s.title)}</h2>${content(s.blocks||s.body||[])}</section>`).join('')}</article><section id="r11-fixed" class="r11-fixed" aria-labelledby="r11-fixed-title" hidden><span class="tag sage">Câu riêng theo bài · Miễn phí</span><h2 id="r11-fixed-title">Câu tự luyện cố định</h2><div>${content(fixed.prompt||[])}</div>${mode==='choice'?(fixed.options||[]).map((option,i)=>`<label class="answer-choice"><input type="radio" name="r11-fixed-answer" value="${e(option)}"><b>${String.fromCharCode(65+i)}.</b> ${e(option)}</label>`).join(''):`<label class="field"><span>Đáp án của em</span><input id="r11-fixed-answer" type="text" maxlength="500" autocomplete="off" aria-describedby="r11-fixed-guide"></label><p id="r11-fixed-guide">${e(guide.instruction||'Nhập một đáp số theo đề bài.')}</p>`}<div class="pilot-actions">${button('Tự kiểm tra','fixed-check')}${button('Làm lại cùng câu','fixed-reset','','outline')}</div><p class="r11-fixed-feedback" id="r11-fixed-feedback" role="status"></p><small id="r11-fixed-progress">Đã tự kiểm tra ${count(courseProgress.attemptCount)} lần · Không thêm vào Đề đã làm</small><div id="r11-fixed-solution" class="r11-solution" hidden></div></section>`;
  lessonStudyCleanup?.();lessonStudyCleanup=window.LessonStudy.mount(panel,{videoLesson:bunnyVideo?{provider:'native',lessonKey:lesson.lessonKey,revision:lesson.revision,title:lesson.title}:null,onComplete:async()=>{const result=await api('knowledge/'+encodeURIComponent(lesson.lessonKey)+'/complete',{lessonRevision:lesson.revision});courseProgress=result.progress||courseProgress;return result;}});
  bind();q('#r11-fixed-answer')?.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();checkFixed();}});
  panel.querySelectorAll('#r11-fixed-answer,[name="r11-fixed-answer"]').forEach(input=>input.addEventListener('input',()=>{if(!fixedBusy)fixedPending=null;}));
 }
 async function loadKnowledge(){
  const key=url().get('knowledgeLesson');if(!key)throw Error('Em chọn một bài trong Chuyên đề.');
  const revision=url().get('lessonRevision');const data=await api('knowledge/'+encodeURIComponent(key)+(revision?'?revision='+encodeURIComponent(revision):''));course=data.lesson;courseProgress=data.progress||{};if(!course?.lessonKey)throw Error('Bài giảng chưa sẵn sàng.');drawKnowledge();
 }
 async function checkFixed(){
  if(fixedBusy||!course)return;const answer=course.fixed?.responseMode==='choice'?(q('[name="r11-fixed-answer"]:checked')?.value||''):(q('#r11-fixed-answer')?.value||'');
  if(!fixedPending||fixedPending.answer!==answer)fixedPending={requestKey:nonce(),answer,lessonRevision:course.revision};
  const chosen={...fixedPending};fixedBusy=true;panel.querySelectorAll('.r11-fixed input,.r11-fixed button').forEach(b=>b.disabled=true);
  try{
   const data=await api('knowledge/'+encodeURIComponent(course.lessonKey)+'/check',chosen);courseProgress=data.progress||{completed:true,checked:true,attemptCount:data.attemptCount};window.LessonStudy.setCompleted(panel,courseProgress.completed);
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

 function status(){const box=q('#pilot-save-status');if(box)box.textContent=saveConflict?'Bài đã đổi trên thiết bị khác. Nháp máy này vẫn được giữ để đối chiếu.':saveError?'Chưa lưu được; đáp án vẫn ở màn này.':pending.size||saving?'Đang lưu…':'Đã lưu trên máy chủ';const retry=q('[data-pilot="retry-save"]');if(retry){retry.hidden=!saveError&&!saveConflict;retry.textContent=saveConflict?'Đối chiếu hai bản':'Thử lưu lại';}}
 async function flush(){if(saving)return saving;if(saveConflict||!pending.size||!exam||exam.submittedAt){status();return;}const g=generation,eid=exam.id;
  saving=(async()=>{while(pending.size&&g===generation){const [position,answer]=pending.entries().next().value;pending.delete(position);status();try{const body={position,answer};if(PlatformAPI.familyContext)body.revision=exam.revision??0;const result=await api('exams/'+eid+'/answers',body);if(Number.isInteger(result.exam?.revision))exam.revision=result.exam.revision;if(result.exam.submittedAt){exam=result.exam;pending.clear();await drawResults();return;}saveError=false;}catch(err){if(g!==generation)return;if(!pending.has(position))pending.set(position,answer);saveError=true;if(PlatformAPI.familyContext&&err.status===409)saveConflict=true;error(err.message);break;}}})();try{await saving;}finally{saving=null;status();}}
 async function compareDrafts(){
  if(busy||!exam)return;busy=true;controls();try{conflictSnapshot=(await api('exams/'+exam.id)).exam;let dialog=q('#pilot-draft-conflict');if(!dialog){dialog=document.createElement('dialog');dialog.id='pilot-draft-conflict';dialog.setAttribute('aria-labelledby','pilot-draft-conflict-title');panel.append(dialog);}
   dialog.innerHTML=`<h2 id="pilot-draft-conflict-title">Đối chiếu đáp án trước khi lưu</h2><p>${conflictSnapshot.submittedAt?'Bài đã được nộp trên máy chủ. Em có thể mở bản đã nộp.':'Nháp máy này chưa ghi đè bản đã lưu. Em chọn bản muốn dùng sau khi đối chiếu.'}</p><div class="solution-list">${[...pending].map(([position,answer])=>`<section class="card card-pad"><h3>Câu ${position}</h3><p>Máy này: ${e(answer||'(để trống)')}</p><p>Đã lưu: ${e(conflictSnapshot.answers[String(position)]||'(để trống)')}</p></section>`).join('')}</div><div class="pilot-actions">${button('Dùng bản đã lưu','conflict-server')}${conflictSnapshot.submittedAt?'':button('Lưu nháp máy này sau đối chiếu','conflict-local','','outline')}${button('Xem lại sau','conflict-cancel','','outline')}</div>`;bind();dialog.showModal();
  }catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}
 }
 async function resolveDraft(useLocal){if(!conflictSnapshot)return;const latest=conflictSnapshot;conflictSnapshot=null;q('#pilot-draft-conflict')?.close();if(!useLocal||latest.submittedAt)pending.clear();exam={...latest,answers:{...latest.answers,...Object.fromEntries(pending)}};saveConflict=false;saveError=false;if(exam.submittedAt)await drawResults();else{drawExam();if(useLocal)await flush();}}
 function changed(value){const position=index+1;exam.answers[String(position)]=value;pending.set(position,value);if(!saveConflict)saveError=false;panel.querySelectorAll('[data-pilot=question]').forEach(nav=>{const i=Number(nav.dataset.index),done=Boolean(String(exam.answers[exam.questions[i].id]??'').trim());nav.classList.toggle('done',done);nav.setAttribute('aria-label','Câu '+(i+1)+(done?' · Đã trả lời':' · Chưa trả lời'));});status();flush();}
 function arrangeScratch(){
  const scratch=q('.scratch-panel');if(!scratch)return;const canvas=scratch.querySelector('canvas'),tools=scratch.querySelector('.scratch-tools');
  scratch.querySelector(':scope > p:not([role])')?.remove();if(canvas&&tools&&scratch.firstElementChild!==canvas)scratch.prepend(canvas);
 }
 function watchSticky(){
  stickyWatch?.disconnect();const stack=q('.study-question-stack'),card=q('.question'),header=stack?.querySelector('.study-question-prompt');if(!stack||!card||!header)return;
  let frame=0,disposed=false,mode=stack.classList.contains('study-stick-all')?'all':stack.classList.contains('study-stick-question')?'question':'';
  const outerHeight=node=>{const style=getComputedStyle(node);return node.getBoundingClientRect().height+(parseFloat(style.marginTop)||0)+(parseFloat(style.marginBottom)||0);};
  const measure=()=>{if(disposed||!stack.isConnected)return;const view=window.visualViewport?.height||innerHeight;
   const bar=document.querySelector('[data-app-shell-nav],.app-shell-nav,.app-bottom-nav');const room=Math.max(0,view-(bar?.getBoundingClientRect().height||0)),limit=room*.65;
   // Measure the prompt's contents, not its decorated box: question-only sticky
   // adds padding/border and prevents margin collapse, which used to flip the
   // measured height back across this same threshold on every observer frame.
   const prompt=[...header.children].reduce((sum,node)=>sum+outerHeight(node),0);
   const full=[...stack.children].reduce((sum,node)=>sum+(node===header?prompt:outerHeight(node)),0);
   // Match the extra vertical space in local-pilot.css (16+1 and 12+1 px).
   // A small entry/exit gap also avoids toggling at fractional viewport sizes.
   const fits=(height,active)=>height<=limit+(active?8:-8);
   const next=fits(full+13,mode==='all')?'all':fits(prompt+17,mode==='question')?'question':'';
   if(next!==mode){stack.classList.toggle('study-stick-all',next==='all');stack.classList.toggle('study-stick-question',next==='question');mode=next;}
  };
  const schedule=()=>{if(!disposed&&!frame)frame=requestAnimationFrame(()=>{frame=0;measure();});};
  const observer=new ResizeObserver(schedule);observer.observe(card);observer.observe(header);window.addEventListener('resize',schedule);window.visualViewport?.addEventListener('resize',schedule);
  stickyWatch={disconnect(){disposed=true;if(frame)cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('resize',schedule);window.visualViewport?.removeEventListener('resize',schedule);}};schedule();
 }
 function drawExam(){
  if(exam.submittedAt){drawResults();return;}index=Math.max(0,Math.min(index,exam.questions.length-1));const item=exam.questions[index],guide=item.inputGuide||{instruction:'Nhập đáp án theo đề.',labels:[],units:[]};
  stickyWatch?.disconnect();
  panel.innerHTML=`<a class="text-link" href="/thi-thu/">← Về luyện tập</a><h1>Bài luyện tập</h1>${item.sampleLabel?`<p class="learning-notice">${e(item.sampleLabel)}</p>`:''}<div class="grid-wide"><section class="card card-pad question"><div class="study-question-stack"><div class="study-question-prompt"><div class="study-question-heading"><strong>Câu ${index+1}/${exam.questions.length}</strong><span id="pilot-timer" role="timer" aria-label="Thời gian còn lại"></span></div>${QuestionFrame.prompt(item,{provider:'pilot',id:'pilot-question',tabIndex:-1})}</div><fieldset aria-labelledby="pilot-question"><div class="pilot-answer">${(item.responseMode||exam.responseMode)==='typed'?`<p id="pilot-guide">${e(guide.instruction)}<br>${(guide.labels||[]).map((l,i)=>e(l)+': '+e(guide.units?.[i])).join(' · ')}</p><label class="field"><span>Đáp án của em</span><input id="pilot-typed-answer" type="text" maxlength="500" autocomplete="off" aria-describedby="pilot-guide" value="${e(exam.answers[item.id]??'')}"></label>`:QuestionFrame.choices(item,{provider:'pilot'}).map(option=>`<label class="answer-choice"><input type="radio" name="pilot-answer" value="${e(option.submitValue)}" ${exam.answers[item.id]===option.submitValue?'checked':''}><b>${option.label}.</b> ${e(option.text)}</label>`).join('')}</div></fieldset><div class="pilot-actions study-question-nav">${button('Câu trước','previous','','outline')}${button('Câu tiếp','next')}</div></div>${PracticeScratchpad.markup()}</section><aside class="card card-pad self-start"><h2>Phiếu làm bài</h2><div class="question-grid">${exam.questions.map((v,n)=>`<button type="button" class="${n===index?'current ':''}${String(exam.answers[v.id]??'').trim()?'done':''}" data-pilot="question" data-index="${n}" aria-current="${n===index?'step':'false'}" aria-label="Câu ${n+1}${String(exam.answers[v.id]??'').trim()?' · Đã trả lời':' · Chưa trả lời'}">${n+1}</button>`).join('')}</div><p id="pilot-save-status" role="status"></p>${button('Thử lưu lại','retry-save','','outline')}<div class="practice-export-actions">${button('Nộp bài','submit')}${PlatformAPI.snapshot.practiceExport?.enabled&&typeof PracticeExport!=='undefined'?PracticeExport.button('pilot',exam.id):''}</div></aside></div><dialog id="pilot-submit" aria-labelledby="pilot-submit-title"><h2 id="pilot-submit-title">Nộp bài để xem kết quả?</h2><p id="pilot-submit-note"></p><div class="pilot-actions">${button('Tiếp tục làm','cancel-submit','','outline')}${button('Xác nhận nộp','confirm-submit')}</div></dialog>`;
  PracticeScratchpad.mount('pilot:'+exam.id+':'+(index+1));arrangeScratch();bind();q('[data-pilot="previous"]').disabled=index===0;q('[data-pilot="next"]').disabled=index===exam.questions.length-1;status();watchSticky();
  const left=Math.max(0,Math.ceil((exam.expiresAt-Date.now())/1000));q('#pilot-timer').textContent=Math.floor(left/60)+':'+String(left%60).padStart(2,'0');
  q('#pilot-typed-answer')?.addEventListener('input',ev=>changed(ev.target.value));panel.querySelectorAll('[name="pilot-answer"]').forEach(input=>input.onchange=()=>changed(input.value));
 }
 async function drawResults(){
  stickyWatch?.disconnect();PracticeScratchpad.unmount();const result=await api('exams/'+exam.id+'/review');exam=result.exam;
  panel.innerHTML=`<a class="text-link" href="/thi-thu/">← Về luyện tập</a><h1>Kết quả bài làm</h1>${exam.questions[0]?.sampleLabel?`<p class="learning-notice">${e(exam.questions[0].sampleLabel)}</p>`:''}<section class="result-band sage"><div class="score-circle"><strong id="pilot-score">${e(exam.score)}<span>/10</span></strong><small>Điểm bài luyện tập</small></div><p>${e(exam.correct)} / ${exam.questions.length} câu đúng</p></section><div class="study-result-tools">${button('Làm lại đề này','replay','','outline')}<label class="study-wrong-filter"><input type="checkbox" id="study-wrong-only" ${wrongOnly?'checked':''}> Chỉ xem câu sai</label></div><p id="study-no-wrong" hidden>Không có câu sai trong bài này.</p><div class="solution-list">${exam.questions.map((item,n)=>`<article class="card card-pad solution pilot-review ${item.correct?'study-correct':'study-incorrect'}" data-study-correct="${Boolean(item.correct)}" ${wrongOnly&&item.correct?'hidden':''}><h2 class="study-result-heading"><span>Câu ${n+1}</span><code>${e(item.questionCode||item.contentKey||'Mã chưa có')}</code><strong>${item.correct?'Đúng':'Sai'}</strong></h2><p>${solutionView.text(item.text)}</p>${solutionView.sampleFigure(item)}<p>Em nhập: ${e(exam.answers[item.id]||'chưa trả lời')}</p>${solutionView.answer(item.answer,'Đáp án')}<details class="study-short-solution"><summary><span class="study-show-solution">Xem lời giải</span><span class="study-hide-solution">Ẩn lời giải</span></summary><div>${studySolution.render(item,{includeAnswer:false,renderMedia:value=>block(value,exam.id,result.contentKeys?.[n]||item.contentKey||'')})}</div></details></article>`).join('')}</div>`;bind();
  const filter=()=>{q('#study-no-wrong').hidden=!wrongOnly||exam.questions.some(item=>!item.correct);panel.querySelectorAll('[data-study-correct]').forEach(row=>row.hidden=wrongOnly&&row.dataset.studyCorrect==='true');};
  q('#study-wrong-only').onchange=ev=>{wrongOnly=ev.target.checked;filter();};filter();
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
  if(kind==='retry-save')return saveConflict?compareDrafts():flush();if(kind==='conflict-server')return resolveDraft(false);if(kind==='conflict-local')return resolveDraft(true);if(kind==='conflict-cancel'){q('#pilot-draft-conflict').close();conflictSnapshot=null;return;}if(kind==='cancel-submit'){q('#pilot-submit').close();return;}
  if(['previous','next','question'].includes(kind)){index=kind==='question'?Number(b.dataset.index):index+(kind==='next'?1:-1);drawExam();q('#pilot-typed-answer')?.focus({preventScroll:true});return;}
  if(kind==='submit'){await flush();if(pending.size)return error('Còn đáp án chưa lưu. Thử lưu lại trước khi nộp.');q('#pilot-submit-note').textContent=`Đã trả lời ${Object.values(exam.answers).filter(v=>String(v).trim()).length}/${exam.questions.length} câu. Sau khi nộp không sửa bài này.`;q('#pilot-submit').showModal();return;}
  if(kind==='replay'){if(busy)return;busy=true;controls();try{const requestKey=b.dataset.requestKey||(b.dataset.requestKey=nonce());const result=await api('exams/'+exam.id+'/retake',{requestKey});location.assign(path('lam-de',result.exam.id));}catch(err){if(err.name!=='AbortError')error(err.message);}finally{busy=false;controls();}return;}
  if(busy)return;busy=true;controls();try{
   if(kind==='confirm-submit'){await flush();if(pending.size)throw Error('Còn đáp án chưa lưu.');exam=(await api('exams/'+exam.id+'/submit',{})).exam;location.assign(path('ket-qua-thi',exam.id));return;}
  }catch(err){error(err.message);}finally{busy=false;controls();}
 }
 function unmount(){lessonStudyCleanup?.();lessonStudyCleanup=null;stickyWatch?.disconnect();PracticeScratchpad.unmount();generation++;clearInterval(timer);timer=null;panel=null;}
 async function mount(route){if(!handles(route))return;routeNow=route;panel=document.getElementById('local-pilot');if(!panel)return;criteriaState.funding='';const g=++generation;owner=PlatformAPI.snapshot.account?.id;csrf=PlatformAPI.snapshot.csrf;pending=new Map();saving=null;saveError=false;saveConflict=false;conflictSnapshot=null;allocation=null;busy=false;exam=null;index=0;course=null;courseProgress={};fixedPending=null;fixedBusy=false;
  try{if(requested(route)){if(route==='lesson'&&url().has('knowledgeLesson'))await loadKnowledge();else if(route==='lesson')await drawLesson();else{exam=(await api('exams/'+url().get('pilotExam'))).exam;exam.submittedAt?await drawResults():drawExam();timer=setInterval(async()=>{if(g!==generation||!exam||exam.submittedAt)return;const left=Math.max(0,Math.ceil((exam.expiresAt-Date.now())/1000));if(q('#pilot-timer'))q('#pilot-timer').textContent=`Còn ${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`;if(!left&&!busy){busy=true;try{exam=(await api('exams/'+exam.id)).exam;if(exam.submittedAt)await drawResults();}catch(err){error(err.message);}finally{busy=false;}}},500);}}else await loadCatalogue();}
  catch(err){if(g===generation&&panel)panel.innerHTML=`<h2>Học liệu Toán</h2>${note()}<p role="alert">${e(err.message)}</p>`;}
 }
 document.addEventListener('click',event=>{const anchor=event.target.closest?.('a[href]');if(anchor&&panel&&exam&&!exam.submittedAt&&(pending.size||saving)){event.preventDefault();event.stopImmediatePropagation();flush().then(()=>{if(!pending.size&&!saveError)location.assign(anchor.href);else error('Còn đáp án chưa lưu. Thử lưu lại trước khi rời bài.');});}},true);
 window.addEventListener('beforeunload',event=>{if(panel&&(pending.size||saving)){event.preventDefault();event.returnValue='';}});
 return {enabled,requested,handles,shell,mount,unmount,retakeOwned};
})();
