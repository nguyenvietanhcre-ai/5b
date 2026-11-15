/* QA-only client. No answers, role authority, storage, service worker or offline catalog. */
'use strict';
const $ = id => document.getElementById(id);
let boot = null, exam = null, index = 0, labels = {}, generation = 0, busy = false;
let serverAnchor = 0, monoAnchor = 0, pending = new Map(), savingPromise = null, saveError = false;
const textOf = value => typeof value === 'string' ? value : Array.isArray(value) ? value.map(v => typeof v === 'string' ? v : v.text || v.latex || '').join(' ') : '';
function node(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
function clock(data) { if (data.nowMs) { serverAnchor = data.nowMs; monoAnchor = performance.now(); } }
function show(section) { for (const id of ['sets','quiz','results']) $(id).hidden = id !== section; }
function error(message) { $('error-text').textContent = message; $('global-error').hidden = false; }
function clearError() { $('global-error').hidden = true; }
function urlExam(id) { const u = new URL(location.href); id ? u.searchParams.set('exam',id) : u.searchParams.delete('exam'); history.replaceState(null,'',u.pathname+u.search); }
async function api(path, body) {
  const options = {credentials:'same-origin',cache:'no-store',headers:{}};
  if (body !== undefined) { options.method = 'POST'; options.headers = {'Content-Type':'application/json','X-CSRF-Token':boot?.csrf || ''}; options.body = JSON.stringify(body); }
  const response = await fetch(path,options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) { const e=new Error(data.error || 'Chưa thể kết nối máy chủ. Em hãy thử lại.');e.reconfirm=response.status===409 && data.reconfirm===true;e.allocation=data.allocation;throw e; }
  return data;
}
function controls() {
  for (const e of document.querySelectorAll('[data-profile]')) e.disabled = busy;
  for(const e of document.querySelectorAll('[data-batch-selector]')) e.disabled=busy || !boot?.authenticated;
  $('start-free').disabled = busy || !boot?.authenticated;
  $('start-vip').disabled = busy || !boot?.authenticated;
  $('buy-pack').disabled=busy || !boot?.authenticated;
  $('confirm-allocation').disabled=busy;
  $('submit').disabled = busy;
  $('confirm-submit').disabled = busy;
}
function renderProfiles() {
  $('profiles').replaceChildren();
  for (const profile of boot.profiles) {
    const button = node('button','profile'); button.type = 'button'; button.dataset.profile = profile.id;
    button.setAttribute('aria-pressed',String(boot.profileId === profile.id));
    button.setAttribute('aria-label','Hồ sơ '+profile.name+' — '+profile.label);
    button.append(node('span','initial',profile.name.slice(0,1)));
    const copy = node('span'); copy.append(node('strong','',profile.name),node('small','',profile.label)); button.append(copy);
    button.addEventListener('click',() => chooseProfile(profile.id)); $('profiles').append(button);
  }
  $('package-label').textContent = boot.packageLabel;
  $('qa-notice').textContent = boot.notice;
  $('profile-note').textContent = boot.authenticated ? 'Đang dùng '+(boot.profiles.find(p => p.id === boot.profileId)?.name || 'hồ sơ mẫu')+'. Chỉ bài của hồ sơ này được mở.' : 'Ba hồ sơ đều là dữ liệu giả cho phiên thử này.';
  $('vip-note').textContent = boot.membership === 'VIP' ? 'Hồ sơ này đang có quyền VIP thử nghiệm.' : 'Chọn hồ sơ Bình Mẫu để thử bộ VIP. Hồ sơ hết hạn vẫn xem lại bài đã được cấp.';
  renderWallet(); renderBatch(); controls();
}
function renderBatch() {
  const batch=boot?.batch; $('legacy-sets').hidden=!!batch; $('batch-sets').hidden=!batch;
  $('batch-sets').replaceChildren(); $('set-size-label').textContent=batch?'Tối đa 10 câu / bộ':'5 câu / bộ';
  if(!batch)return;
  function add(label,selector) {
    const card=node('article','set-card'),b=node('button','primary',label); b.type='button'; b.dataset.batchSelector=JSON.stringify(selector);
    card.append(node('h3','',label),b); b.addEventListener('click',()=>requestAllocation(selector)); $('batch-sets').append(card);
  }
  for(const item of batch.freeSets)add(`MCQ Free ${item.slot} · 10 câu`,{setIndex:item.slot,responseMode:'choice'});
  for(const [keys,mode,label] of [[batch.vipKeys,'choice','MCQ VIP'],[batch.typedFree,'typed','Tự nhập Free'],[batch.typedVip,'typed','Tự nhập VIP']])
    for(let i=0;i<keys.length;i+=10)add(`${label} ${1+i/10} · ${Math.min(10,keys.length-i)} câu`,{contentKeys:keys.slice(i,i+10),responseMode:mode});
}
function renderHistory() {
  $('history').replaceChildren(); const historyItems = boot.history || [];
  $('history-wrap').hidden = historyItems.length === 0;
  for (const [i,item] of historyItems.entries()) {
    const b = node('button'); b.type = 'button'; b.dataset.exam = item.id;
    b.append(node('span','',item.submitted ? 'Xem lại bài đã nộp' : 'Tiếp tục bài đang làm'),node('span','',`Lần ${historyItems.length-i}`));
    b.addEventListener('click',() => openExam(item.id)); $('history').append(b);
  }
}
function wipe() { exam = null; index = 0; labels = {}; pending.clear(); saveError = false; $('choices').replaceChildren(); $('review-list').replaceChildren(); $('question-text').textContent = ''; $('submit-dialog').close(); $('allocation-dialog').close();allocationPending=null;orderPendingKey=null; }
async function chooseProfile(id) {
  if (busy) return;
  await flush(); if (pending.size) { error('Lựa chọn còn chưa lưu. Em hãy thử lưu lại trước khi đổi hồ sơ.'); return; }
  const g = ++generation; busy = true; controls(); clearError();
  try {
    const next = await api('/qa-api/profiles/select',{profileId:id}); if (g !== generation) return;
    wipe(); boot = next; clock(boot); urlExam(null); renderProfiles(); renderHistory(); show('sets'); $('sets-heading').focus();
  } catch (e) { error(e.message); }
  finally { if (g === generation) { busy = false; controls(); } }
}
async function home() {
  await flush(); if (pending.size) { error('Bài còn câu trả lời chưa lưu. Em hãy thử lưu lại nhé.'); return; }
  const g = ++generation; clearError();
  try { const next = await api('/qa-api/bootstrap'); if (g !== generation) return; boot = next; clock(boot); wipe(); renderProfiles(); renderHistory(); show(boot.authenticated ? 'sets' : null); urlExam(null); }
  catch (e) { error(e.message); }
}
let allocationPending=null,orderPendingKey=null;
function vnTime(value) { return value ? new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',dateStyle:'short',timeStyle:'short'}).format(new Date(value))+' (giờ Việt Nam)' : 'Chưa có'; }
function renderWallet() {
  const state=boot?.wallet; $('wallet-panel').hidden=!state;
  if(!state)return;
  $('scope-label').textContent=state.catalog.scopeLabel;
  $('wallet-role').textContent=state.membership+(state.membership==='Free' && state.privateRemaining>0 ? ' có gói câu hỏi riêng' : '')+' · gói riêng không kéo dài VIP';
  $('vip-balance').textContent=`Ngày ${state.vip.dayUsed}/${state.vip.dayLimit} · Chu kỳ ${state.vip.cycleUsed}/${state.vip.cycleLimit}`;
  $('vip-expiry').textContent=`VIP ${state.vip.active?'còn hạn':'không còn hiệu lực'} · hết hạn ${vnTime(state.vip.vipExpiresAt)} · kỳ kết thúc ${vnTime(state.vip.cycleEnd)}`;
  $('wallet-balance').textContent=`Còn ${state.privateRemaining} lượt riêng hợp lệ`;
  $('pack-expiry').textContent=state.packs.length ? state.packs.map(p=>`${p.remaining} lượt · hạn ${vnTime(p.expires_at)}${p.usable?'':' · không tiêu được'}`).join(' | ') : 'Chưa có gói riêng';
  $('seed-notice').textContent=state.seededCountersNotice;
  $('vip-note').textContent='Free, VIP và VIP hết hạn đều dùng được gói riêng còn hạn. Câu Free/câu đã nhận không trừ thêm.';
  $('wallet-orders').replaceChildren();
  for(const order of state.orders) {
    const row=node('article','order-row');row.append(node('p','',`Đơn giả: ${order.status} · 100 lượt / 50.000đ`));
    if(order.status==='pending') {
      for(const [action,label] of [['mock-confirm','Mô phỏng máy chủ xác nhận'],['mock-fail','Mô phỏng thất bại']]) {
        const button=node('button','secondary',label);button.type='button';button.dataset.mock=action;
        button.addEventListener('click',()=>settleOrder(order.orderId,action));row.append(button);
      }
    } else if(order.receipt) row.append(node('p','',`Biên nhận QA: +100 lượt · hết hạn ${vnTime(order.receipt.expires_at)}`));
    $('wallet-orders').append(row);
  }
}
async function refreshWallet() { boot.wallet=await api('/qa-api/wallet');renderWallet(); }
async function buyPack() {
  if(busy)return;busy=true;controls();clearError();
  orderPendingKey ||= crypto.randomUUID();
  try { await api('/qa-api/wallet/orders',{requestKey:orderPendingKey,sku:'qa.questions.100'});orderPendingKey=null;await refreshWallet(); }
  catch(e){error('Đơn QA chưa hoàn tất, thử lại giữ cùng mã yêu cầu. '+e.message);}
  finally{busy=false;controls();}
}
async function settleOrder(orderId,action) {
  if(busy)return;busy=true;controls();clearError();
  try { await api('/qa-api/wallet/'+action,{orderId});await refreshWallet(); }
  catch(e){error(e.message);}finally{busy=false;controls();}
}
async function start(kind) {
  return requestAllocation(kind==='free'?{setIndex:1}:{contentKeys:boot.vipKeys});
}
async function requestAllocation(selector) {
  if(busy)return;const g=generation;busy=true;controls();clearError();
  try {
    const selected=structuredClone(selector);
    const quote=await api('/qa-api/wallet/quote',selected);
    if(g!==generation)return;
    allocationPending={selector:selected,quote,requestKey:crypto.randomUUID()};
    $('allocation-text').textContent=`Câu trả phí mới: ${quote.newPaid}. Sẽ trừ VIP: ${quote.vip}; gói riêng: ${quote.private}. Free: ${quote.free}; đã nhận: ${quote.retained}.`;
    $('allocation-notice').textContent=quote.private ? `Em xác nhận dùng ${quote.private} lượt mua riêng. Không chuyển tiền trong QA. Nếu cần thêm, máy chủ yêu cầu xác nhận lại.` : 'Không trừ gói riêng. Máy chủ vẫn kiểm lại khi cấp bài.';
    if(!$('allocation-dialog').open)$('allocation-dialog').showModal();
  }catch(e){error(e.message);}finally{busy=false;controls();}
}
async function commitAllocation() {
  if(busy || !allocationPending)return;busy=true;controls();clearError();const g=generation;const choice=allocationPending;
  try {
    const response=await api('/api/v1/exams',{requestKey:choice.requestKey,...choice.selector,quoteId:choice.quote.quoteId,confirmWallet:choice.quote.private>0});
    $('allocation-dialog').close();allocationPending=null;await refreshWallet();if(g===generation)await acceptExam(response.exam,g);
  }catch(e){
    if(e.reconfirm){
      $('allocation-dialog').close();allocationPending=null;busy=false;controls();await requestAllocation(choice.selector);error(e.message);return;
    }
    const message='Chưa nhận cấp bài. Em có thể gửi lại an toàn cùng yêu cầu. '+e.message;
    $('allocation-notice').textContent=message;error(message);
  }finally{busy=false;controls();}
}
async function openExam(id) {
  if (busy) return; await flush(); if (pending.size) return;
  const g = generation; busy = true; controls(); clearError();
  try { const response = await api('/api/v1/exams/'+encodeURIComponent(id)); if (g === generation) await acceptExam(response.exam,g); }
  catch (e) { error(e.message); }
  finally { if (g === generation) { busy = false; controls(); } }
}
async function acceptExam(value,g) {
  const meta = value.responseMode==='choice' ? await api('/qa-api/choice-labels/'+value.id) : {labels:{}}; if (g !== generation) return;
  exam = value; labels = meta.labels; pending.clear(); saveError = false;
  index = Math.min(index,exam.questions.length-1); urlExam(exam.id);
  if (exam.submittedAt) await showResults(g);
  else { show('quiz'); renderQuestion(true); }
}
function progress() {
  if (!exam) return; const answered = exam.questions.filter(q => Boolean(exam.answers[q.id])).length;
  $('progress').max = exam.questions.length; $('progress').value = answered;
  $('progress-text').textContent = `Đã trả lời ${answered}/${exam.questions.length} câu`;
  $('question-nav').replaceChildren();
  exam.questions.forEach((q,i) => { const b = node('button',exam.answers[q.id] ? 'answered' : '',String(i+1)); b.type = 'button'; b.setAttribute('aria-label',`Câu ${i+1}${exam.answers[q.id] ? ', đã chọn' : ', chưa chọn'}`); b.setAttribute('aria-current',String(i === index)); b.addEventListener('click',() => { index = i; renderQuestion(true); }); $('question-nav').append(b); });
  $('previous').disabled = index === 0; $('next').disabled = index === exam.questions.length-1;
  status();
}
function status() {
  $('save-status').textContent = saveError ? 'Chưa lưu được. Câu trả lời vẫn còn trong màn này.' : pending.size || savingPromise ? 'Đang lưu câu trả lời…' : 'Đã lưu trên máy chủ';
  $('retry-save').hidden = !saveError;
}
function renderQuestion(focus) {
  if (!exam || exam.submittedAt) return;
  const q=exam.questions[index]; $('question-position').textContent=`CÂU ${index+1} / ${exam.questions.length}`;
  $('question-text').textContent=q.text; $('choices').replaceChildren();
  if(exam.responseMode==='typed') {
    const guide=q.inputGuide || {instruction:'Nhập đáp án theo đề. Dùng dấu ; để ngăn cách nhiều kết quả.',labels:[],units:[]};
    const help=node('p','muted',guide.instruction);help.id='answer-guide';
    const units=node('p','muted',guide.labels.map((label,i)=>`${label}: ${guide.units[i]}`).join(' · '));
    const label=node('label','','Đáp án của em');label.htmlFor='typed-answer';
    const input=node('input');input.type='text';input.id='typed-answer';input.inputMode='text';input.enterKeyHint='done';
    input.autocomplete='off';input.autocapitalize='off';input.spellcheck=false;input.maxLength=500;
    input.setAttribute('aria-describedby','answer-guide');input.placeholder='Nhập đáp án';input.value=exam.answers[q.id] ?? '';
    input.addEventListener('input',()=>{exam.answers[q.id]=input.value;pending.set(Number(q.id),input.value);saveError=false;progress();flush();});
    input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();flush();}});
    $('choices').append(help,units,label,input);
  } else {
    for (const [i,option] of q.options.entries()) {
      const choice=node('label','choice');const input=node('input');input.type='radio';input.name='choice';input.value=option;input.checked=exam.answers[q.id]===option;
      const id=labels[q.id]?.[i]?.id || String.fromCharCode(65+i);const copy=node('span');copy.append(node('strong','',id+'. '),document.createTextNode(option));
      input.addEventListener('change',()=>{exam.answers[q.id]=option;pending.set(Number(q.id),option);saveError=false;progress();flush();});
      choice.append(input,copy);$('choices').append(choice);
    }
  }
  progress();timer();if(focus){$('question-text').focus?.();if(exam.responseMode==='typed')$('typed-answer').focus({preventScroll:true});}
}
async function flush() {
  if (savingPromise) return savingPromise;
  if (!exam || exam.submittedAt || !pending.size) { status(); return; }
  const id = exam.id, g = generation;
  savingPromise = (async () => {
    while (pending.size && g === generation && exam?.id === id) {
      const [position,answer] = pending.entries().next().value; pending.delete(position); status();
      try { const response = await api(`/api/v1/exams/${id}/answers`,{position,answer});
        if (g !== generation) return;
        if (response.exam.submittedAt) { exam = response.exam; pending.clear(); await showResults(g); return; }
      } catch (e) { if (!pending.has(position)) pending.set(position,answer); saveError = true; break; }
    }
  })();
  status();
  try { await savingPromise; }
  finally { savingPromise = null; if (!pending.size && !saveError) clearError(); status(); }
}
async function askSubmit() {
  if (busy || !exam || exam.submittedAt) return; await flush();
  if (pending.size) { error('Chưa lưu xong câu trả lời. Em hãy thử lưu lại trước khi nộp.'); return; }
  const missing = exam.questions.filter(q => !exam.answers[q.id]).length;
  $('submit-message').textContent = missing ? `Còn ${missing} câu chưa trả lời. Em muốn quay lại làm tiếp hay nộp bài hiện tại?` : `Em đã trả lời đủ ${exam.questions.length} câu. Mình cùng xem kết quả nhé.`;
  $('submit-dialog').showModal();
}
async function submit() {
  if (busy || !exam) return; const g = generation; busy = true; controls(); clearError();
  try { const response = await api('/api/v1/exams/'+exam.id+'/submit',{}); if (g !== generation) return; exam = response.exam; $('submit-dialog').close(); await showResults(g); }
  catch (e) { $('submit-dialog').close(); error('Chưa nhận được kết quả nộp. Em có thể nộp lại an toàn. '+e.message); }
  finally { if (g === generation) { busy = false; controls(); } }
}
async function showResults(g = generation) {
  if (!exam?.submittedAt) return; show('results'); pending.clear(); $('review-list').replaceChildren(); $('review-error').hidden = true;
  $('score').textContent = `${exam.score}/10`;
  $('score-detail').textContent = `Đúng ${exam.correct}/${exam.questions.length} câu · Bài đã được nộp và lưu`;
  $('results-heading').focus();
  try { const review = await api('/qa-api/review/'+exam.id); if (g !== generation) return; renderReview(review); }
  catch (e) { if (g === generation) $('review-error').hidden = false; }
}
function renderReview(review) {
  $('review-list').replaceChildren();
  for (const item of review.questions) {
    const q = exam.questions[item.position-1]; const card = node('details','review-card'); card.open = item.position === 1;
    const summary = node('summary'); const copy = node('span','',`Câu ${item.position}`); const outcome = {correct:'✓ Đúng',incorrect:'✕ Chưa đúng',unanswered:'— Chưa chọn'}[item.outcome];
    copy.append(node('span','outcome '+item.outcome,outcome)); summary.append(copy); card.append(summary);
    const body = node('div','review-body'); body.append(node('p','review-prompt',q.text));
    for (const [title,value] of [['Em đã nhập',item.selectedText || 'Chưa trả lời'],['Đáp án đúng',item.correctText]]) { const line = node('p','answer-line'); line.append(node('strong','',title),document.createTextNode(value)); body.append(line); }
    const selected = (item.choices || []).find(c => c.id === item.selectedChoiceId);
    if (selected) body.append(node('p','',textOf(selected.rationale)));
    const solution = node('section','solution'); solution.append(node('h3','','Cùng xem cách giải'));
    const steps = node('ol'); const items = Array.isArray(item.solutionSteps) ? item.solutionSteps : [item.solutionSteps];
    for (const step of items) steps.append(node('li','',textOf(step)));
    solution.append(steps,node('p','',textOf(item.answerExplanation))); body.append(solution);
    if(exam.responseMode==='choice') {
    const rationale = node('details','rationale'); rationale.append(node('summary','','Giải thích cả bốn câu trả lời'));
    for (const choice of item.choices) { const box = node('div','rationale-item'); box.append(node('strong','',choice.id+'. '+choice.text),node('p','',textOf(choice.rationale))); rationale.append(box); }
    body.append(rationale); } card.append(body); $('review-list').append(card);
  }
}
function timer() {
  if (!exam || exam.submittedAt || !serverAnchor) return;
  const now = serverAnchor + (performance.now()-monoAnchor);
  const seconds = Math.max(0,Math.ceil((exam.expiresAt-now)/1000));
  $('timer').textContent = seconds ? `Phiên thử còn ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}` : 'Phiên thử đã đến hạn';
}
async function init() {
  const g = ++generation; clearError();
  try { const next = await api('/qa-api/bootstrap'); if (g !== generation) return; boot = next; clock(boot); renderProfiles(); renderHistory(); show(boot.authenticated ? 'sets' : null);
    const id = new URL(location.href).searchParams.get('exam'); if (boot.authenticated && id && /^\d+$/.test(id)) await openExam(id);
  } catch (e) { error(e.message); }
}
$('buy-pack').addEventListener('click',buyPack);
$('cancel-allocation').addEventListener('click',()=>{$('allocation-dialog').close();allocationPending=null;});
$('confirm-allocation').addEventListener('click',commitAllocation);
$('start-free').addEventListener('click',() => start('free')); $('start-vip').addEventListener('click',() => start('vip'));
$('previous').addEventListener('click',() => { if (index > 0) { index--; renderQuestion(true); } });
$('next').addEventListener('click',() => { if (exam && index < exam.questions.length-1) { index++; renderQuestion(true); } });
$('retry-save').addEventListener('click',() => { saveError = false; flush(); });
$('submit').addEventListener('click',askSubmit); $('confirm-submit').addEventListener('click',submit); $('cancel-submit').addEventListener('click',() => $('submit-dialog').close());
for (const id of ['go-home','back-sets','result-home']) $(id).addEventListener('click',home);
$('retry-load').addEventListener('click',init); $('retry-review').addEventListener('click',() => showResults());
window.addEventListener('online',() => { if (pending.size) { saveError = false; flush(); } });
window.addEventListener('beforeunload',event => { if (pending.size || savingPromise) { event.preventDefault(); event.returnValue = ''; } });
window.addEventListener('pageshow',event => { if (event.persisted) { wipe(); init(); } });
setInterval(timer,1000); init();
