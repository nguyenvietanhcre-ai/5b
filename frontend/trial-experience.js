(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const line = value => esc(value).replace(/\n/g, '<br>');
  const labels = {bot:'Đấu trí với BOT',capture_flag:'Cướp Cờ mẫu',animal_race:'Đua Thú mẫu'};
  const images = new Map();
  const signatures = new Map();
  let config = null, state = null, activeTab = 'learn', activeGame = 'bot';
  let offset = 0, busy = false, polling = false, lastActivity = 0, draftTimer = null, lastBattleAttack = '';

  function sampleFigure(question){return QuestionFrame.diagram(question,{className:'trial-diagram'});}
  function now() { return Date.now() + offset; }
  function notice(message, error = false) {
    const box = $('#trial-message');
    box.textContent = message || '';
    box.hidden = !message;
    box.classList.toggle('is-error', error);
  }
  function date(value) { return new Date(Number(value)).toLocaleString('vi-VN', {hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}); }
  function errorMessage(error) {
    if (error.status === 429) return `${error.message || 'Em đã bắt đầu lại nhiều lần trong thời gian ngắn.'}${error.retryAfter ? ` Hãy thử lại sau ${Math.ceil(error.retryAfter)} giây.` : ' Hãy chờ một chút rồi thử lại.'}`;
    if (error.status === 409) return error.message || 'Trang này đã thay đổi ở tab khác. Nội dung mới nhất đã được tải lại.';
    if (error.status === 403) return error.message || 'Phiên cần được tải lại trước khi thực hiện thao tác.';
    return error.message || 'Chưa kết nối được máy chủ. Bài trên màn hình vẫn giữ nguyên; em hãy thử lại.';
  }
  async function request(path, method = 'GET', body) {
    const headers = {Accept:'application/json'};
    if (method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      const csrf = state?.csrf;
      if (csrf) headers['X-Trial-CSRF'] = csrf;
    }
    const response = await fetch(`/api/trial${path}`, {method,headers,credentials:'same-origin',cache:'no-store',...(body !== undefined ? {body:JSON.stringify(body)} : {})});
    let payload;
    try { payload = await response.json(); } catch { payload = {}; }
    if (!response.ok) {
      if (response.status === 429 && payload.challengeRequired && method === 'POST') {
        const challenge = await askChallenge();
        if (challenge !== null) return request(path,method,{...body,challenge});
      }
      const raw = payload.error;
      const error = new Error(typeof raw === 'string' ? raw : raw?.message || payload.message || `Máy chủ trả mã ${response.status}.`);
      error.status = response.status;
      error.payload = payload;
      error.retryAfter = Number(response.headers.get('Retry-After') || payload.retryAfter || raw?.retryAfter || 0);
      throw error;
    }
    return payload;
  }
  function accept(payload, force = false) {
    if (payload?.session) {
      const previous = state?.session;
      if (previous && payload.session.generation < previous.generation) return payload;
      if(previous?.id===payload.session.id&&Number(payload.gradeRevision||0)<Number(state.gradeRevision||0))return payload;
      state = payload;
      if (typeof payload.serverTime === 'number') offset = payload.serverTime - Date.now();
      if (force || previous?.generation !== state.session.generation || previous?.id !== state.session.id) signatures.clear();
      if (!previous) {
        const running = ['bot','capture_flag','animal_race'].find(mode => ['playing','preparing','intermission'].includes(state.activities?.[mode]?.status));
        if (running) activeGame = running;
      }
      render();
    }
    return payload;
  }
  async function mutation(path, values = {}) {
    const expected = state?.session;
    const payload = await request(path,'POST',{generation:expected?.generation,...values});
    if (!state?.session || state.session.id !== expected?.id || state.session.generation !== expected?.generation) return payload;
    return accept(payload);
  }
  async function perform(action) {
    if (busy) return;
    busy = true;
    $$('[data-action="start"], [data-action="reset"], .trial-answer-submit').forEach(button => { button.disabled = true; });
    try { notice(''); await action(); }
    catch (error) {
      notice(errorMessage(error),true);
      if ([401,410].includes(error.status)) await ended(error.message);
      else if ([403,409].includes(error.status)) await refresh(true).catch(() => {});
    } finally {
      busy = false;
      $$('[data-action="start"], [data-action="reset"], .trial-answer-submit').forEach(button => { button.disabled = false; });
      // A response can lock an already-submitted question. Respect that lock.
      $$('.trial-answer-form[data-locked="true"] .trial-answer-submit').forEach(button => { button.disabled = true; });
    }
  }
  async function refresh(force = false) {
    if (!state?.session || polling) return;
    polling = true;
    const expected = {id:state.session.id,generation:state.session.generation};
    try {
      const payload = await request('/state');
      if (state?.session?.id === expected.id && state.session.generation === expected.generation) accept(payload,force);
    } catch (error) {
      if (state?.session?.id === expected.id && state.session.generation === expected.generation) throw error;
    }
    finally { polling = false; }
  }
  async function start() {
    const payload = await request('/session','POST',{});
    accept(payload,true);
    $('#trial-ended').hidden = true;
    $('#trial-workspace').hidden = false;
    $('#trial-start').textContent = 'Tiếp tục khám phá ↗';
    $('#trial-workspace').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function showTab(tab, activity = true) {
    activeTab = tab;
    $$('[data-tab]').forEach(button => {
      if (button.dataset.tab === tab) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
    });
    $$('[data-panel]').forEach(panel => { panel.hidden = panel.dataset.panel !== tab; });
    if (tab !== 'bot') window.BadgeMascots?.destroy(); else mountRuntime();
    if (activity) meaningfulActivity();
    drawMascots();
  }
  function render() {
    $('#trial-workspace').hidden = false;
    $('#trial-ended').hidden = true;
    $('#trial-start').textContent = 'Tiếp tục khám phá ↗';
    $('#trial-session-label').textContent = `Dữ liệu mẫu · Toán ${state?.grade || config?.pilotGrade || 5}`;
    const gradePicker=$('#trial-grade');if(gradePicker){gradePicker.value=String(state.grade||5);gradePicker.disabled=false;}
    $('#trial-workspace-heading').textContent='Toán '+(state.grade||5)+' · Học thử cùng Mầm Sách';
    renderLesson();
    renderAttempt('practice');
    renderBotLobby();
    renderAttempt(activeGame);
    renderFamily();
    renderPreferences();
    tick();
    drawMascots();
  }
  function renderLesson() {
    const lesson = state.lesson || {};
    const signature = JSON.stringify([state.grade,lesson.id,lesson.revision,state.lessonComplete]);
    if (signatures.get('lesson') === signature) return;
    signatures.set('lesson',signature);
    const sections = lesson.sections || [
      {title:'Định hướng tư duy',body:lesson.thinking},
      {title:'Điểm mấu chốt',body:lesson.key},
      {title:'Bài giải chi tiết',body:lesson.solution}
    ].filter(section => section.body);
    const diagram = lesson.diagram;
    $('#trial-lesson').innerHTML = `<span class="trial-demo-label">Mẫu tự biên soạn · Chờ giáo viên duyệt</span><h3>${esc(lesson.title || `Một ý nhỏ trong Toán lớp ${Number(state.grade)||5}`)}</h3>${lesson.prompt ? `<p>${line(lesson.prompt)}</p>` : ''}${sampleFigure(lesson)}${lesson.options?.length ? `<ol type="A">${lesson.options.map(option=>`<li>${esc(option)}</li>`).join('')}</ol>` : ''}${sections.map((section,index) => `<section><h4>${index + 1}. ${esc(section.title)}</h4><p>${line(section.body)}</p></section>`).join('')}${diagram ? `<figure class="trial-diagram"><div class="trial-diagram-parts" role="img" aria-label="${esc(diagram.description)}">${(diagram.labels || []).map((label,index) => `<span${index < diagram.selected ? ' class="is-selected"' : ''}>${esc(label)}</span>`).join('')}</div><figcaption>${esc(diagram.description)}</figcaption></figure>` : ''}<div class="trial-actions" style="margin-top:18px"><button type="button" class="trial-button trial-button-light" data-action="lesson-complete">${state.lessonComplete ? 'Đã đọc bài ✓' : 'Em đã đọc và hiểu ý chính'}</button></div>`;
  }
  function modeInfo(key) { return (config?.modes || []).find(mode => mode.key === key); }
  function renderBotLobby() {
    const signature = JSON.stringify([state.grade,config?.modes,state.preferences?.mascot]);
    if (signatures.get('lobby') === signature) return;
    signatures.set('lobby',signature);
    const bot = modeInfo('bot');
    $('#trial-bot-lobby').innerHTML = `<div class="trial-bot-hero"><canvas width="200" height="220" data-mascot="fox" role="img" aria-label="Cáo Nâu Lanh Lợi, đối thủ máy minh họa"></canvas><div><span class="trial-demo-label">Phòng mẫu riêng · Không ghép người thật</span><h3>Đấu trí với một người bạn máy</h3><p>Tổng hợp Toán ${state?.grade||5}. Bộ 20 câu Free; mỗi câu chỉ gửi một lần. Khi có người trả lời đúng đầu tiên, người còn lại có 3 giây phòng thủ: đúng mất 10 máu, sai hoặc không trả lời mất 20 máu.</p><button type="button" class="trial-button" data-action="game" data-mode="bot" ${bot?.ready ? '' : 'disabled'}>${bot?.ready ? 'Thử một trận với BOT' : 'Bộ câu BOT đang được chuẩn bị'}</button><p class="trial-small" style="margin:14px 0 0">Bản thử dùng học liệu đã tự kiểm số học, đang chờ giáo viên duyệt. Không ghi XP hay kết quả thi thật.</p></div></div><div class="trial-mode-grid">${['capture_flag','animal_race'].map(key => { const mode = modeInfo(key); return `<section class="trial-card"><h3>${esc(labels[key])}</h3><p>Em và 4 bạn máy cùng chơi trên bộ mẫu Toán ${state?.grade||5}. Mục tiêu 5 câu đúng; 60 giây mỗi vòng, chuyển câu sau 3 giây.</p><button type="button" class="trial-button trial-button-light" data-action="game" data-mode="${key}" ${mode?.ready ? '' : 'disabled'}>${mode?.ready ? 'Chơi thử' : 'Chưa đủ nguồn để mở'}</button></section>`; }).join('')}</div>`;
  }
  function gameQuestion(attempt) {
    const game = attempt.game;
    return attempt.currentQuestion || game?.battle?.questions?.[game.battle.index] || game?.question;
  }
  function renderAttempt(mode) {
    const target = mode === 'practice' ? $('#trial-practice') : $('#trial-bot');
    const attempt = state.activities?.[mode];
    if (!attempt) { target.hidden = true; return; }
    const game = attempt.game || {};
    const battle = game.battle;
    const question = gameQuestion(attempt);
    const result = (attempt.results || []).find(item => item.questionId === question?.id);
    const mine = game.players?.find(player => player.mine);
    const locked = Boolean(result || battle?.answer !== null && battle?.answer !== undefined || mine?.answered || battle?.resolved);
    const signature = JSON.stringify([attempt.id,attempt.status,attempt.index,question?.id,attempt.results,attempt.score,battle?.hp,battle?.opponentHp,battle?.resolved,battle?.answer,battle?.defenseUntil,battle?.roundOutcome,game.status,game.players?.map(player => [player.steps,player.answered,player.correct]),game.result]);
    if (signatures.get(`attempt-${mode}`) === signature && target.dataset.mode === mode && !target.hidden) return;
    signatures.set(`attempt-${mode}`,signature);
    target.dataset.mode = mode;
    target.hidden = false;
    const finished = ['completed','finished','cancelled','ended'].includes(attempt.status) || ['finished','cancelled'].includes(game.status);
    const total = attempt.total || (mode === 'bot' ? 20 : 5);
    const index = attempt.index ?? battle?.index ?? Math.max(0,(game.round || 1)-1);
    let html = `<div class="trial-question-top"><div><span class="trial-demo-label">${mode === 'practice' ? 'Bài luyện mẫu' : 'Trò chơi mẫu'}</span><h3>${esc(mode === 'practice' ? 'Tự làm, rồi cùng hiểu' : labels[mode])}</h3></div><span class="trial-pill">${finished ? 'Đã kết thúc' : `Câu ${Math.min(index + 1,total)} / ${total}`}</span></div>`;
    if (mode !== 'practice') html += renderGameStage(attempt);
    if (finished) {
      const score = typeof attempt.score === 'number' ? attempt.score : (attempt.results || []).filter(item => item.correct).length;
      html += `<div class="trial-result"><h4>Em đã hoàn thành một vòng khám phá!</h4><p>${mode === 'practice' ? `Em làm đúng ${score} / ${total} câu.` : 'Kết quả và diễn biến trong trận chỉ thuộc phiên mẫu này.'} Mỗi câu đã làm là một cơ hội để hiểu thêm.</p><div class="trial-actions"><button type="button" class="trial-button trial-button-light" data-action="${mode === 'practice' ? 'practice' : 'game'}"${mode === 'practice' ? '' : ` data-mode="${esc(mode)}"`}>Thử lại bộ mẫu</button></div></div>`;
      if (attempt.results?.length) html += `<details><summary>Xem lại ${attempt.results.length} câu đã làm</summary>${attempt.results.map(item => resultMarkup(item)).join('')}</details>`;
      target.innerHTML = html;
      mountRuntime();
      return;
    }
    if (!question?.id || !question.text && !question.prompt) {
      html += '<p role="status">Máy chủ đang chuẩn bị vòng tiếp theo…</p>';
      target.innerHTML = html;
      mountRuntime();
      return;
    }
    if (mode === 'practice' && attempt.results?.length && !result) {
      const previousResult = attempt.results[attempt.results.length - 1];
      html += `<details class="trial-previous-result" open><summary>Cách giải câu vừa làm</summary>${resultMarkup(previousResult)}</details>`;
    }
    const draft = attempt.answers?.[question.id];
    const answerValue = typeof draft === 'object' && draft !== null ? draft.answer || '' : draft || '';
    const scratchValue = attempt.scratch || '';
    const choices = question.options || [];
    const responseMode = question.responseMode || (choices.length ? 'choice' : 'typed');
    html += `${QuestionFrame.prompt(question,{provider:'trial',tag:'p',className:'trial-question-text',diagramClass:'trial-diagram',multiline:true})}<form class="trial-answer-form" data-mode="${mode}" data-attempt="${esc(attempt.id)}" data-question="${esc(question.id)}" data-locked="${locked}" ${locked ? 'aria-label="Câu này đã được gửi"' : ''}>${responseMode === 'choice' ? `<fieldset class="trial-options"><legend class="trial-small">Chọn một phương án đủ kết quả</legend>${choices.map((choice,choiceIndex) => { const normalized=QuestionFrame.choices({id:question.id,options:[choice]},{provider:'trial'})[0]; const value=typeof choice==='object'?(choice.id??choice.value??choiceIndex):normalized.submitValue; const text=normalized.text; return `<label class="trial-option"><input type="radio" name="answer" value="${esc(value)}" ${String(answerValue) === String(value) ? 'checked' : ''} ${locked ? 'disabled' : ''} required><span>${String.fromCharCode(65+choiceIndex)}. ${esc(text)}</span></label>`; }).join('')}</fieldset>` : `<label>Đáp án của em${question.unit ? ` (${esc(question.unit)})` : ''}<input type="text" name="answer" value="${esc(answerValue)}" placeholder="Nhập một đáp số" inputmode="decimal" autocomplete="off" maxlength="120" ${locked ? 'disabled' : ''} required></label>`}<details${scratchValue ? ' open' : ''}><summary>✎ Nháp của em</summary><label class="trial-small" style="margin-top:10px">Nháp được giữ trong phiên mẫu này<textarea name="scratch" maxlength="2000" placeholder="Em có thể ghi từng bước ở đây…" ${locked ? 'disabled' : ''}>${esc(scratchValue)}</textarea></label><span class="trial-draft-status" aria-live="polite">${scratchValue || answerValue ? 'Đã khôi phục nháp của câu này.' : ''}</span></details><div class="trial-actions"><button type="submit" class="trial-button trial-answer-submit" ${locked ? 'disabled' : ''}>${locked ? 'Đã gửi một lần ✓' : 'Gửi đáp án'}</button>${mode === 'practice' ? '<button type="button" class="trial-text-button" data-action="save-draft">Lưu nháp</button>' : ''}</div></form>`;
    if (result) html += resultMarkup(result);
    if (battle?.feedback) html += `<p class="trial-game-feedback" role="status">${esc(battle.feedback)}</p>`;
    if (mode === 'practice' && result && index < total - 1) html += '<button type="button" class="trial-button trial-button-light" data-action="next-practice">Câu tiếp theo →</button>';
    target.innerHTML = html;
    mountRuntime();
    tick();
  }
  function resultMarkup(result) {
    return `<div class="trial-result${result.correct ? '' : ' is-incorrect'}"><h4>${result.correct ? 'Em đã tìm đúng rồi! ✓' : 'Cùng xem lại một bước nhé'}</h4><p>Đáp án em gửi: <strong>${esc(result.answer ?? 'Chưa gửi')}</strong>${result.expected !== undefined ? ` · Đáp số: <strong>${esc(result.expected)}</strong>` : ''}</p>${result.explanation ? `<p>${line(typeof result.explanation === 'object' ? result.explanation.body || result.explanation.text || '' : result.explanation)}</p>` : ''}</div>`;
  }
  function renderGameStage(attempt) {
    const game = attempt.game || {}, battle = game.battle, result = game.result;
    if (attempt.mode === 'bot' || battle || result) {
      const myHp = battle?.hp ?? result?.hp ?? 100, theirHp = battle?.opponentHp ?? result?.opponentHp ?? 100;
      const sprite = (code,label) => window.BadgeMascots ? window.BadgeMascots.markup(code,0,label) : `<canvas width="180" height="200" data-mascot="${esc(code)}" aria-label="${esc(label)}"></canvas>`;
      return `<div class="trial-battle-stage" id="battle-stage"><div class="fighter left" id="trial-fighter-me"><strong>Em · ${myHp} máu</strong><meter min="0" max="100" value="${myHp}">${myHp}/100</meter>${sprite(state.preferences?.mascot || 'sprout','Linh vật của em')}</div><span class="trial-battle-vs" aria-hidden="true">✦</span><div class="fighter right" id="trial-fighter-bot"><strong>BOT · ${theirHp} máu</strong><meter min="0" max="100" value="${theirHp}">${theirHp}/100</meter>${sprite(battle?.opponentMascot || result?.opponentMascot || 'fox','Linh vật của BOT')}</div></div>${battle ? `<p class="trial-game-clock" role="status" data-game-deadline="${battle.defenseUntil || battle.nextAt || battle.deadline}" data-clock-kind="${battle.defenseUntil ? 'defense' : battle.nextAt ? 'next' : 'answer'}"></p>` : ''}${result?.outcome ? `<p class="trial-game-feedback">${({win:'Em đã thắng trận mẫu!',lose:'Bạn máy đã thắng trận mẫu. Em thử lại nhé!',draw:'Hai bạn hòa nhau trong trận mẫu.',left:'Trận mẫu đã dừng.'})[result.outcome] || 'Trận mẫu đã hoàn thành.'}</p>` : ''}`;
    }
    if (game.players?.length) {
      return `<div class="trial-race-stage" aria-label="Tiến độ người chơi mẫu">${game.players.map(player => `<div class="trial-race-row${player.mine ? ' is-me' : ''}"><canvas width="70" height="75" data-mascot="${esc(player.mascot || 'sprout')}" aria-hidden="true"></canvas><div><strong>${esc(player.name)}${player.mine ? ' (Em)' : ' · BOT'}</strong><div class="trial-progress"><span style="--progress:${Math.max(0,Math.min(100,100 * Number(player.correct || 0) / Number(game.target || 5)))}%"></span></div></div><span>${Number(player.correct || 0)} / ${Number(game.target || 5)}</span></div>`).join('')}</div>${game.deadline || game.nextAt ? `<p class="trial-game-clock" role="status" data-game-deadline="${game.nextAt || game.deadline}" data-clock-kind="${game.nextAt ? 'next' : 'answer'}"></p>` : ''}`;
    }
    return '';
  }
  function mountRuntime() {
    if (!window.BadgeMascots || activeTab !== 'bot') return;
    window.BadgeMascots.mount($('#trial-bot'));
    const battle = state.activities?.[activeGame]?.game?.battle;
    if (battle?.defenseUntil) window.BadgeMascots.defend(battle.attacking ? '#trial-fighter-bot' : '#trial-fighter-me',true);
    const result = state.activities?.[activeGame]?.game?.result;
    const attack = battle?.lastAttack || result?.lastAttack;
    const key = JSON.stringify([state.activities?.[activeGame]?.id,attack]);
    if (attack && key !== lastBattleAttack) {
      lastBattleAttack = key;
      const source = attack.attacker === 'me' ? '#trial-fighter-me' : '#trial-fighter-bot';
      const target = attack.attacker === 'me' ? '#trial-fighter-bot' : '#trial-fighter-me';
      setTimeout(() => window.BadgeMascots?.hit(target,source,Boolean(result?.hp === 0 || result?.opponentHp === 0)),100);
    }
  }
  function fixtureRows(items, fallback) {
    if (!Array.isArray(items) || !items.length) return `<p class="trial-small">${esc(fallback)}</p>`;
    return `<ul class="trial-fixture-list">${items.map(item => `<li><span class="trial-fixture-dot" aria-hidden="true"></span><div><strong>${esc(item.title || item.name || item.label || 'Minh họa')}</strong><p>${esc(item.description || item.note || item.status || item.time || '')}${item.amount !== undefined ? ` · ${Number(item.amount).toLocaleString('vi-VN')}đ (mẫu)` : ''}</p></div></li>`).join('')}</ul>`;
  }
  function renderFamily() {
    const fixtures = state.fixtures || {};
    const signature = JSON.stringify(fixtures);
    if (signatures.get('family') === signature) return;
    signatures.set('family',signature);
    const children = fixtures.children || fixtures.family?.children || [];
    $('#trial-family').innerHTML = `<div class="trial-card"><div class="trial-section-line"><div><span class="trial-demo-label">TOÀN BỘ LÀ MINH HỌA</span><h3 style="margin-top:10px">Một gia đình, mỗi con một góc học</h3></div></div><p>Ba mẹ có thể quản lý việc học của các con từ cùng một tài khoản gia đình. Hai hồ sơ dưới đây chỉ là dữ liệu mẫu; tên, tiến độ, lớp, nhận xét và học phí đều không thuộc học sinh thật.</p><div class="trial-family-grid">${children.map((child,index) => `<article class="trial-card"><div class="trial-family-profile"><canvas width="95" height="105" data-mascot="${esc(child.mascot || (index ? 'rabbit' : 'sprout'))}" aria-hidden="true"></canvas><div><h3>${esc(child.name || child.nickname || 'Bạn mẫu')}</h3><p>Khối ${esc(child.grade || 5)} · ${esc(child.plan || child.tier || 'Hồ sơ mẫu')}</p><span class="trial-demo-label">Hồ sơ minh họa</span></div></div>${fixtureRows(child.progress || child.activities,'Tiến độ mẫu được hiển thị khi có bộ minh họa.')}<p class="trial-small">${esc(child.note || child.comment || '')}</p></article>`).join('')}</div></div><div class="trial-family-grid"><section class="trial-card"><h3>Lớp & lịch học mẫu</h3>${fixtureRows(fixtures.classes || fixtures.schedule,'Chưa có lịch mẫu cho phiên này.')}${fixtureRows(fixtures.assignments,'Bài tập mẫu không nhận tệp hay nộp bài thật.')}</section><section class="trial-card"><h3>Nhận xét & học phí mẫu</h3>${fixtureRows(fixtures.comments || fixtures.reviews,'Nhận xét minh họa không phải đánh giá chuyên môn về em.')}${fixtureRows(fixtures.fees || fixtures.tuition,'Không có yêu cầu đóng học phí thật trong trải nghiệm.')}</section></div><section class="trial-card" style="margin-top:20px"><span class="trial-demo-label">XEM CÁCH CHỌN GÓI · KHÔNG THANH TOÁN</span><h3 style="margin-top:12px">Thử xem một đơn minh họa</h3><p>Em và ba mẹ có thể thử các lựa chọn. Trang này không tạo đơn thật, mã QR, chuyển khoản hay cấp gói.</p><div class="trial-order-controls"><label>Gói mẫu<select id="trial-preview-plan"><option value="vip">VIP</option><option value="vip_plus">VIP+</option></select></label><label>Kỳ mẫu<select id="trial-preview-period"><option value="month">Theo tháng</option><option value="year">Theo năm</option></select></label></div><button type="button" class="trial-button trial-button-light" data-action="order-preview">Xem đơn mẫu</button><div id="trial-order-preview"></div>${fixtureRows(fixtures.orders,'Chưa tạo đơn mẫu trong phiên này.')}</section>`;
  }
  function renderPreferences() {
    const preferences = state.preferences || {};
    const signature = JSON.stringify(preferences);
    if (signatures.get('preferences') === signature) return;
    signatures.set('preferences',signature);
    document.body.dataset.trialTheme = preferences.theme || 'garden';
    const data = window.BadgeMascotData || {};
    $('#trial-preferences').innerHTML = `<p class="trial-small" style="margin:14px 0 0">Chọn người bạn đồng hành từ 20 linh vật đã có. Lựa chọn chỉ giữ trong phiên mẫu.</p><div class="trial-mascot-grid">${Object.entries(data).map(([code,pet]) => `<button type="button" class="trial-mascot-choice" data-action="mascot" data-mascot-code="${esc(code)}" aria-pressed="${(preferences.mascot || 'sprout') === code}"><canvas width="100" height="110" data-mascot="${esc(code)}" aria-hidden="true"></canvas><span>${esc(pet.name)}</span></button>`).join('')}</div><div class="trial-theme-choices" aria-label="Màu vườn mẫu">${[['garden','Vườn Khám Phá'],['morning','Sương Mai'],['crayon','Bút Sáp'],['sprout','Mầm Sách 3D'],['notebook','Sổ Tay']].map(([key,title]) => `<button type="button" data-action="theme" data-theme-choice="${key}" aria-pressed="${(preferences.theme || 'garden') === key}">${title}</button>`).join('')}</div>`;
  }
  async function ended(message) {
    state = null;
    clearTimeout(draftTimer);
    signatures.clear();
    window.BadgeMascots?.destroy();
    $('#trial-workspace').hidden = true;
    $('#trial-idle').hidden = true;
    $('#trial-ended').hidden = false;
    $('#trial-start').textContent = 'Bắt đầu phiên mới ↗';
    $('#trial-ended-note').textContent = message || 'Phiên trải nghiệm đã kết thúc. Em có thể bắt đầu lại để khám phá bộ mẫu.';
  }
  function confirmAction(action) {
    const dialog = $('#trial-confirm');
    $('#trial-confirm-title').textContent = action === 'reset' ? 'Bắt đầu lại từ đầu?' : 'Kết thúc trải nghiệm?';
    $('#trial-confirm-copy').textContent = 'Thao tác này xóa bài, nháp và trạng thái của phiên mẫu hiện tại.';
    $('#trial-confirm-ok').textContent = action === 'reset' ? 'Bắt đầu lại' : 'Kết thúc phiên';
    return new Promise(resolve => {
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm'), {once:true});
      dialog.showModal();
    });
  }
  function askChallenge() {
    const dialog = $('#trial-challenge');
    const input = $('#trial-challenge-answer');
    input.value = '';
    return new Promise(resolve => {
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm' ? input.value.trim() : null), {once:true});
      dialog.showModal();
      input.focus();
    });
  }
  function tick() {
    const session = state?.session;
    if (session) {
      const remaining = Math.max(0,Math.ceil((Math.min(session.idleExpiresAt,session.absoluteExpiresAt)-now())/1000));
      const warn = now() >= session.idleWarnAt || now() >= session.absoluteExpiresAt-120000;
      $('#trial-idle').hidden = !warn;
      $('#trial-idle-text').textContent = remaining > 0 ? `Phiên còn khoảng ${Math.floor(remaining/60)} phút ${remaining%60} giây. Bấm Tiếp tục học nếu em muốn ở lại.` : 'Đang kiểm tra thời hạn phiên trên máy chủ…';
      $('#trial-time-note').textContent = `Giữ tạm đến ${date(Math.min(session.idleExpiresAt,session.absoluteExpiresAt))}. Hoạt động học giữ phiên; tối đa ${date(session.absoluteExpiresAt)}.`;
    }
    $$('[data-game-deadline]').forEach(element => {
      const remaining = Math.max(0,Math.ceil((Number(element.dataset.gameDeadline)-now())/1000));
      element.textContent = element.dataset.clockKind === 'defense' ? `Phòng thủ: ${remaining} giây · Đúng mất 10 máu, sai hoặc không trả lời mất 20 máu` : element.dataset.clockKind === 'next' ? `Câu tiếp theo sau ${remaining} giây…` : `Thời gian trả lời: ${remaining} giây`;
    });
  }
  function meaningfulActivity() {
    if (!state?.session || now()-lastActivity < 30000) return;
    lastActivity = now();
    mutation('/activity').catch(() => {});
  }
  async function saveDraft(form, explicit = false) {
    if (!form || form.dataset.locked === 'true' || !state?.session) return;
    const attempt = state.activities?.[form.dataset.mode];
    if (attempt?.id !== form.dataset.attempt) return;
    const formData = new FormData(form);
    const answers = {...(attempt.answers || {}),[form.dataset.question]:String(formData.get('answer') || '')};
    const status = $('.trial-draft-status',form);
    if (status) status.textContent = 'Đang giữ nháp…';
    try {
      // Keep the focused input intact while the server acknowledges its draft.
      const payload = await request('/draft','POST',{generation:state.session.generation,attemptId:attempt.id,answers,scratch:String(formData.get('scratch') || '')});
      if (payload?.session && state?.session && payload.session.generation === state.session.generation && payload.session.id === state.session.id) {
        state = payload;
        if (payload.serverTime) offset = payload.serverTime-Date.now();
      }
      if (status?.isConnected) status.textContent = 'Đã giữ nháp trong phiên mẫu.';
      if (explicit) notice('Nháp đã được giữ trong phiên mẫu này.');
    } catch (error) { if (status?.isConnected) status.textContent = 'Chưa giữ được nháp. Em có thể thử lại.'; if (explicit) notice(errorMessage(error),true); }
  }
  function drawMascots() {
    const data = window.BadgeMascotData || {};
    $$('canvas[data-mascot]').forEach(canvas => {
      if (!canvas.getClientRects().length) return;
      const code = data[canvas.dataset.mascot] ? canvas.dataset.mascot : 'sprout';
      if (canvas.dataset.drawn === code) return;
      if (!images.has(code)) images.set(code,new Promise((resolve,reject) => { const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = `/arena-art/badge-mascots/${code}.webp`; }));
      images.get(code).then(img => {
        if (!canvas.isConnected) return;
        const frame = data[code]?.profile?.frames?.[0];
        if (!frame) return;
        const context = canvas.getContext('2d');
        context.clearRect(0,0,canvas.width,canvas.height);
        const scale = Math.min(canvas.width/frame.width,canvas.height/frame.height)*.95;
        context.drawImage(img,frame.left,frame.top,frame.width,frame.height,(canvas.width-frame.width*scale)/2,canvas.height-frame.height*scale,frame.width*scale,frame.height*scale);
        canvas.dataset.drawn = code;
      }).catch(() => { canvas.setAttribute('aria-label',data[code]?.name || 'Linh vật mẫu'); });
    });
  }
  document.addEventListener('click', event => {
    const tab = event.target.closest('[data-tab]');
    if (tab) { showTab(tab.dataset.tab); return; }
    const button = event.target.closest('[data-action]');
    if (!button || button.disabled) return;
    const action = button.dataset.action;
    if (action === 'guide') { $('#trial-guide').hidden = false; $('#trial-guide').scrollIntoView({behavior:'smooth',block:'start'}); return; }
    if (action === 'skip-guide') { $('#trial-guide').hidden = true; if (state) $('#trial-workspace').scrollIntoView({behavior:'smooth'}); return; }
    perform(async () => {
      if (action === 'start') { if (state) { await refresh(); $('#trial-workspace').scrollIntoView({behavior:'smooth'}); } else await start(); }
      else if (action === 'continue') await mutation('/activity');
      else if (action === 'lesson-complete') { await mutation('/lesson/complete'); notice('Đã ghi nhận bài đọc trong phiên mẫu. Đến lượt em thử bài ngắn!'); }
      else if (action === 'practice') { await mutation('/practice/start'); $('#trial-practice').scrollIntoView({behavior:'smooth',block:'start'}); }
      else if (action === 'next-practice') { await refresh(true); }
      else if (action === 'game') { activeGame = button.dataset.mode; await mutation(activeGame === 'bot' ? '/bot/start' : '/game/start',activeGame === 'bot' ? {} : {mode:activeGame}); renderAttempt(activeGame); $('#trial-bot').scrollIntoView({behavior:'smooth',block:'start'}); }
      else if (action === 'save-draft') await saveDraft(button.closest('form'),true);
      else if (action === 'mascot') await mutation('/preferences',{mascot:button.dataset.mascotCode,theme:state.preferences?.theme || 'garden'});
      else if (action === 'theme') await mutation('/preferences',{theme:button.dataset.themeChoice,mascot:state.preferences?.mascot || 'sprout'});
      else if (action === 'order-preview') {
        const payload = await mutation('/order/preview',{plan:$('#trial-preview-plan').value,period:$('#trial-preview-period').value});
        const order = payload.order || payload.preview || payload.fixtures?.orderPreview || {};
        $('#trial-order-preview').innerHTML = `<div class="trial-preview-note"><strong>Đơn minh họa · Không cần thanh toán</strong><p>${esc(order.title || `${$('#trial-preview-plan').selectedOptions[0].text} · ${$('#trial-preview-period').selectedOptions[0].text}`)}</p>${order.amount !== undefined ? `<p>${Number(order.amount).toLocaleString('vi-VN')}đ (mẫu)</p>` : ''}<p class="trial-small">${esc(order.note || 'Lựa chọn này chỉ mô phỏng giao diện. Không có đơn, QR hoặc quyền gói thật được tạo.')}</p></div>`;
      }
      else if (action === 'reset' || action === 'end') {
        if (!(await confirmAction(action))) return;
        if (action === 'reset') { accept(await request('/reset','POST',{generation:state.session.generation}),true); notice('Đã bắt đầu phiên mẫu mới.'); }
        else { await request('/end','POST',{generation:state.session.generation}); await ended('Phiên mẫu đã kết thúc. Bài và nháp của phiên vừa kết thúc đã được xóa.'); }
      }
    });
  });
  document.addEventListener('submit', event => {
    const form = event.target.closest('.trial-answer-form');
    if (!form) return;
    event.preventDefault();
    if (form.dataset.locked === 'true') return;
    clearTimeout(draftTimer);
    const answer = new FormData(form).get('answer');
    if (answer === null || !String(answer).trim()) { notice('Em hãy nhập hoặc chọn đáp án trước khi gửi.',true); return; }
    perform(async () => {
      await saveDraft(form);
      const mode = form.dataset.mode;
      await mutation(mode === 'practice' ? '/practice/answer' : mode === 'bot' ? '/bot/answer' : '/game/answer',{attemptId:form.dataset.attempt,questionId:form.dataset.question,answer:String(answer).trim()});
      renderAttempt(mode);
    });
  });
  document.addEventListener('input', event => {
    const form = event.target.closest('.trial-answer-form');
    if (!form || form.dataset.locked === 'true') return;
    clearTimeout(draftTimer);
    const status = $('.trial-draft-status',form);
    if (status) status.textContent = 'Đang nhập nháp…';
    draftTimer = setTimeout(() => saveDraft(form),900);
  });
  document.addEventListener('toggle', () => drawMascots(),true);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && state) refresh().catch(error => { if ([401,410].includes(error.status)) ended(error.message); else notice(errorMessage(error),true); }); });
  window.addEventListener('online', () => { if (state) refresh().then(() => notice('Đã kết nối lại, bài được khôi phục từ máy chủ.')).catch(error => notice(errorMessage(error),true)); });
  document.addEventListener('change',event=>{if(event.target.id!=='trial-grade'||!state?.session)return;const picker=event.target;const grade=Number(picker.value);picker.disabled=true;mutation('/grade',{grade}).catch(error=>{notice(errorMessage(error),true);picker.value=String(state?.grade||5);}).finally(()=>{picker.disabled=false;});});
  async function boot() {
    drawMascots();
    try {
      config = await request('/config');
      let expiredMessage = '';
      try { accept(await request('/state'),true); } catch (error) { if (![401,404,410].includes(error.status)) throw error; if (error.status === 410) expiredMessage = error.message; }
        if (!state && expiredMessage) await ended(expiredMessage);
    } catch (error) { notice(errorMessage(error),true); }
    setInterval(tick,1000);
    setInterval(() => {
      if (!state || document.hidden || busy) return;
      refresh().catch(error => { if ([401,410].includes(error.status)) ended(error.message); else if (error.status !== 429) notice(errorMessage(error),true); });
    },2000);
  }
  boot();
})();
