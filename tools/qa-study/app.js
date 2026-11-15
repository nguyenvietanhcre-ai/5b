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
  if (!response.ok) throw new Error(data.error || 'Chưa thể kết nối máy chủ. Em hãy thử lại.');
  return data;
}
function controls() {
  for (const e of document.querySelectorAll('[data-profile]')) e.disabled = busy;
  $('start-free').disabled = busy || !boot?.authenticated;
  $('start-vip').disabled = busy || boot?.membership !== 'VIP';
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
  controls();
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
function wipe() { exam = null; index = 0; labels = {}; pending.clear(); saveError = false; $('choices').replaceChildren(); $('review-list').replaceChildren(); $('question-text').textContent = ''; $('submit-dialog').close(); }
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
  await flush(); if (pending.size) { error('Bài còn lựa chọn chưa lưu. Em hãy thử lưu lại nhé.'); return; }
  const g = ++generation; clearError();
  try { const next = await api('/qa-api/bootstrap'); if (g !== generation) return; boot = next; clock(boot); wipe(); renderProfiles(); renderHistory(); show(boot.authenticated ? 'sets' : null); urlExam(null); }
  catch (e) { error(e.message); }
}
async function start(kind) {
  if (busy) return; const g = generation; busy = true; controls(); clearError();
  try {
    const body = {requestKey:crypto.randomUUID()};
    if (kind === 'free') body.setIndex = 1;
    else { const allowed = await api('/qa-api/bootstrap'); body.contentKeys = allowed.vipKeys; }
    const response = await api('/api/v1/exams',body); if (g !== generation) return;
    await acceptExam(response.exam,g);
  } catch (e) { error(e.message); }
  finally { if (g === generation) { busy = false; controls(); } }
}
async function openExam(id) {
  if (busy) return; await flush(); if (pending.size) return;
  const g = generation; busy = true; controls(); clearError();
  try { const response = await api('/api/v1/exams/'+encodeURIComponent(id)); if (g === generation) await acceptExam(response.exam,g); }
  catch (e) { error(e.message); }
  finally { if (g === generation) { busy = false; controls(); } }
}
async function acceptExam(value,g) {
  const meta = await api('/qa-api/choice-labels/'+value.id); if (g !== generation) return;
  exam = value; labels = meta.labels; pending.clear(); saveError = false;
  index = Math.min(index,exam.questions.length-1); urlExam(exam.id);
  if (exam.submittedAt) await showResults(g);
  else { show('quiz'); renderQuestion(true); }
}
function progress() {
  if (!exam) return; const answered = exam.questions.filter(q => Boolean(exam.answers[q.id])).length;
  $('progress').max = exam.questions.length; $('progress').value = answered;
  $('progress-text').textContent = `Đã chọn ${answered}/${exam.questions.length} câu`;
  $('question-nav').replaceChildren();
  exam.questions.forEach((q,i) => { const b = node('button',exam.answers[q.id] ? 'answered' : '',String(i+1)); b.type = 'button'; b.setAttribute('aria-label',`Câu ${i+1}${exam.answers[q.id] ? ', đã chọn' : ', chưa chọn'}`); b.setAttribute('aria-current',String(i === index)); b.addEventListener('click',() => { index = i; renderQuestion(true); }); $('question-nav').append(b); });
  $('previous').disabled = index === 0; $('next').disabled = index === exam.questions.length-1;
  status();
}
function status() {
  $('save-status').textContent = saveError ? 'Chưa lưu được. Lựa chọn vẫn còn trong màn này.' : pending.size || savingPromise ? 'Đang lưu lựa chọn…' : 'Đã lưu trên máy chủ';
  $('retry-save').hidden = !saveError;
}
function renderQuestion(focus) {
  if (!exam || exam.submittedAt) return;
  const q = exam.questions[index]; $('question-position').textContent = `CÂU ${index+1} / ${exam.questions.length}`;
  $('question-text').textContent = q.text; $('choices').replaceChildren();
  const choices = labels[q.id] || q.options.map((text,i) => ({id:'ABCD'[i],text}));
  for (const choice of choices) {
    const label = node('label','choice'); const input = node('input'); input.type = 'radio'; input.name = 'choice'; input.value = choice.text; input.checked = exam.answers[q.id] === choice.text;
    input.addEventListener('change',() => { exam.answers[q.id] = choice.text; pending.set(Number(q.id),choice.text); saveError = false; progress(); flush(); });
    const copy = node('span'); copy.append(node('span','letter',choice.id+'. '),document.createTextNode(choice.text)); label.append(input,copy); $('choices').append(label);
  }
  progress(); timer(); if (focus) $('question-text').focus?.();
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
  if (pending.size) { error('Chưa lưu xong lựa chọn. Em hãy thử lưu lại trước khi nộp.'); return; }
  const missing = exam.questions.filter(q => !exam.answers[q.id]).length;
  $('submit-message').textContent = missing ? `Còn ${missing} câu chưa chọn đáp án. Em muốn quay lại làm tiếp hay nộp bài hiện tại?` : `Em đã chọn đủ ${exam.questions.length} câu. Mình cùng xem kết quả nhé.`;
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
    for (const [title,value] of [['Em đã chọn',item.selectedText || 'Chưa chọn đáp án'],['Đáp án đúng',item.correctText]]) { const line = node('p','answer-line'); line.append(node('strong','',title),document.createTextNode(value)); body.append(line); }
    const selected = item.choices.find(c => c.id === item.selectedChoiceId);
    if (selected) body.append(node('p','',textOf(selected.rationale)));
    const solution = node('section','solution'); solution.append(node('h3','','Cùng xem cách giải'));
    const steps = node('ol'); const items = Array.isArray(item.solutionSteps) ? item.solutionSteps : [item.solutionSteps];
    for (const step of items) steps.append(node('li','',textOf(step)));
    solution.append(steps,node('p','',textOf(item.answerExplanation))); body.append(solution);
    const rationale = node('details','rationale'); rationale.append(node('summary','','Giải thích cả bốn lựa chọn'));
    for (const choice of item.choices) { const box = node('div','rationale-item'); box.append(node('strong','',choice.id+'. '+choice.text),node('p','',textOf(choice.rationale))); rationale.append(box); }
    body.append(rationale); card.append(body); $('review-list').append(card);
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
