/* Ngựa / v1. Canvas choreography. Source PNG and review GIF/MP4 never enter runtime. */
(() => {
  'use strict';
  const C = window.ANIMATION_CONFIG, canvas = document.getElementById('stage');
  const ctx = canvas.getContext('2d', { alpha: false });
  const W = 1280, H = 720, DURATION = 3, PI = Math.PI;
  const clamp = (n, a = 0, b = 1) => Math.max(a, Math.min(b, n));
  const mix = (a, b, n) => a + (b - a) * n;
  const smooth = n => { n = clamp(n); return n * n * (3 - 2 * n); };
  const out = n => 1 - (1 - clamp(n)) ** 3;
  const actions = {
    ultimate: { title: 'Vó Ngựa Cuồng Phong', subtitle: 'Hất bờm → phi nước đại → lốc vó ngựa → tự hào', beats: ['0–0,95 s · Lấy đà|Hất bờm, nhấc vó. Tên chiêu hiện từ 0,65 giây.', '0,95–1,90 s · Cuồng phong|Dấu móng sáng hợp thành lốc hình ngựa, cuốn đối thủ một vòng.', '1,90–3,00 s · Chiến thắng|Lốc tan thành dấu móng và sao. Ngựa dừng vững, tự hào.'] },
    attack: { title: 'Cú Vó Nhanh', subtitle: 'Lấy đà → lao tới → chạm vó → trở về', beats: ['0–0,35 s · Chuẩn bị|Hạ trọng tâm, hướng mắt về phía đối thủ.', '0,35–0,95 s · Tấn công|Lao một nhịp ngắn và chạm vó trong ánh sao mềm.', '0,95–3,00 s · Trở về|Đáp vững, thu vó và trở về tư thế sẵn sàng.'] },
    hit: { title: 'Chịu đòn', subtitle: 'Bất ngờ → lùi nhẹ → lấy lại bình tĩnh', beats: ['0–0,35 s · Bất ngờ|Ngựa nhìn thấy đòn đánh đến.', '0,35–1,10 s · Chịu đòn|Lùi nhẹ, nhắm mắt trong chốc lát; không có thương tích.', '1,10–3,00 s · Hồi phục|Mở mắt, đứng vững và sẵn sàng thử tiếp.'] },
    defeat: { title: 'Buồn bã khi thua cuộc', subtitle: 'Hạ đầu → cụp tai → ngồi nghỉ, vẫn đáng yêu', beats: ['0–0,60 s · Chùng xuống|Ngựa chậm rãi hạ đầu sau trận.', '0,60–1,70 s · Buồn bã|Tai và bờm rũ nhẹ, nét mặt tiếc nuối.', '1,70–3,00 s · Nghỉ một chút|Ngồi nghỉ bình tĩnh. Thử lại ở trận sau nhé!'] }
  };
  const query = new URLSearchParams(location.search);
  let action = Object.hasOwn(actions, query.get('action')) ? query.get('action') : 'ultimate';
  let clock = 0, speed = 1, playing = false, raf = 0, last = 0, loaded = false;
  const assets = {}, reduced = matchMedia('(prefers-reduced-motion: reduce)');
  function load(name, url) { return new Promise((resolve, reject) => { const img = new Image(); img.onload = () => { assets[name] = img; resolve(); }; img.onerror = () => reject(new Error('Không tải được ' + url)); img.src = url; }); }
  function rect(x, y, w, h, radius, fill, stroke) { ctx.beginPath(); ctx.roundRect(x, y, w, h, radius); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); } }
  function text(str, x, y, size, color = '#fff9ed', weight = 800, align = 'center') { ctx.font = `${weight} ${size}px Arial,sans-serif`; ctx.textAlign = align; ctx.textBaseline = 'middle'; ctx.fillStyle = color; ctx.fillText(str, x, y); }
  function star(x, y, r, color, rotation = 0, alpha = 1) { ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y); ctx.rotate(rotation); ctx.beginPath(); for (let i = 0; i < 10; i++) { const angle = -PI / 2 + i * PI / 5, rr = i % 2 ? r * .43 : r; const px = Math.cos(angle) * rr, py = Math.sin(angle) * rr; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); } ctx.closePath(); ctx.fillStyle = color; ctx.fill(); ctx.restore(); }
  function horseshoe(x, y, size = 40, rotation = 0, alpha = 1) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rotation); ctx.scale(size / 40, size / 40); ctx.globalAlpha *= alpha;
    ctx.strokeStyle = '#ffe4a3'; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.shadowColor = '#ffcd70'; ctx.shadowBlur = 14;
    ctx.beginPath(); ctx.moveTo(-12, -13); ctx.bezierCurveTo(-26, 18, -7, 28, 0, 25); ctx.bezierCurveTo(18, 26, 22, 7, 13, -13); ctx.stroke();
    ctx.shadowBlur = 0; ctx.fillStyle = '#8b6539'; for (const [px, py] of [[-14, -3], [-13, 10], [-5, 18], [7, 18], [14, 6]]) { ctx.beginPath(); ctx.arc(px, py, 1.5, 0, PI * 2); ctx.fill(); } ctx.restore();
  }
  function shadow(x, feet, size = 90, alpha = .2) { ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = '#163e2d'; ctx.filter = 'blur(7px)'; ctx.beginPath(); ctx.ellipse(x, feet, size, 11, 0, 0, PI * 2); ctx.fill(); ctx.restore(); }
  function pose(index, x, feet, options = {}) {
    const sheet = options.reaction ? 'reaction' : 'actor', map = options.reaction ? window.HORSE_REACTIONS : window.ANIMATION_POSES;
    const frame = map.frames[index], maxHeight = Math.max(...map.frames.map(f => f.height));
    const scale = 300 / maxHeight * (options.size || 1);
    ctx.save(); ctx.globalAlpha *= options.alpha ?? 1; ctx.translate(x, feet); ctx.rotate(options.rotation || 0);
    ctx.drawImage(assets[sheet], frame.left, frame.top, frame.width, frame.height, -frame.width * scale / 2, -frame.height * scale, frame.width * scale, frame.height * scale); ctx.restore();
  }
  function fox(t, mode = action) {
    const spin = mode === 'ultimate' ? smooth((t - 1.75) / .34) : 0;
    const hit = mode === 'attack' ? Math.sin(clamp((t - .66) / .3) * PI) : 0;
    const fade = mode === 'ultimate' ? clamp((t - 2.15) / .38) : 0;
    const x = 1010 + 42 * spin + 20 * hit, feet = 596 - 42 * Math.sin(spin * PI) - 12 * hit;
    shadow(x, 600, 87, .18 * (1 - fade)); ctx.save(); ctx.globalAlpha *= 1 - .84 * fade;
    ctx.translate(x, feet - 150); ctx.rotate(spin * PI * 2 + hit * .08);
    const img = assets.opponent, half = img.width / 2;
    ctx.drawImage(img, half, 0, half, img.height, -158, -150, 316, 316); ctx.restore();
    if ((mode === 'ultimate' && t > 1.75 && t < 2.18) || (mode === 'attack' && t > .65 && t < .98)) {
      const u = mode === 'ultimate' ? clamp((t - 1.75) / .43) : clamp((t - .65) / .33);
      for (let i = 0; i < 9; i++) { const a = i * PI * 2 / 9 + u; star(x + Math.cos(a) * (45 + u * 95), feet - 170 + Math.sin(a) * (30 + u * 90), 5 + 6 * (1 - u), '#ffe3a3', a, 1 - u); }
    }
  }
  function track(t) {
    if (t < .95 || t > 2.12) return;
    for (let i = 0; i < 8; i++) {
      const appear = smooth((t - (.99 + i * .065)) / .12), fade = 1 - clamp((t - 1.66) / .46);
      if (appear * fade > 0) horseshoe(310 + i * 61, 588 + (i % 2 ? 12 : -6), 28 + 4 * Math.sin(t * 8 - i), -.25, .78 * appear * fade);
    }
  }
  function streaks(x, feet, alpha = 1) { ctx.save(); ctx.lineCap = 'round'; for (let i = 0; i < 8; i++) { ctx.globalAlpha = alpha * (.18 + (i % 3) * .1); ctx.strokeStyle = i % 2 ? '#ffe5a4' : '#f4f9d1'; ctx.lineWidth = 3 + i % 3; const y = feet - 55 - (i * 37) % 190; ctx.beginPath(); ctx.moveTo(x - 210 - i * 8, y); ctx.lineTo(x - 92 - i * 3, y); ctx.stroke(); } ctx.restore(); }
  function windHorse(t) {
    if (t < 1.34 || t > 2.12) return;
    const p = clamp((t - 1.34) / .43), fade = 1 - clamp((t - 1.85) / .27), x = mix(695, 1015, out(p));
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = fade;
    const glow = ctx.createRadialGradient(x, 421, 4, x, 421, 180); glow.addColorStop(0, '#ffe3a44a'); glow.addColorStop(1, '#ffcf7000'); ctx.fillStyle = glow; ctx.fillRect(x - 190, 220, 380, 390);
    ctx.save(); ctx.globalAlpha *= .57; ctx.translate(x, 531); ctx.drawImage(assets.windHorse, -145, -208, 290, 208); ctx.restore();
    ctx.strokeStyle = '#ffe4a3'; ctx.lineCap = 'round'; ctx.shadowColor = '#ffcd70'; ctx.shadowBlur = 16;
    for (let j = 0; j < 5; j++) { ctx.lineWidth = 2 + j % 2; ctx.globalAlpha = fade * (.8 - j * .11); ctx.beginPath(); ctx.ellipse(x - 14, 478 - j * 27, 110 - j * 9, 25 + j * 2, -.2, t * 9 + j, t * 9 + j + PI * 1.54); ctx.stroke(); }
    ctx.shadowBlur = 0;
    for (let i = 0; i < 6; i++) { const a = t * 9 + i * PI / 3; horseshoe(x + Math.cos(a) * 125, 431 + Math.sin(a) * 85, 22, a + PI / 2, fade * .86); }
    ctx.restore();
    if (t >= 1.75) { const u = clamp((t - 1.75) / .36); for (let i = 0; i < 18; i++) { const a = i * PI * 2 / 18; star(1040 + Math.cos(a) * u * 175, 442 + Math.sin(a) * u * 140, 5 + 6 * (1 - u), i % 2 ? '#fff2c4' : '#ffbe73', a, 1 - u); } }
  }
  function banner(t) {
    if (action !== 'ultimate' || t < .65 || t > 1.56) return;
    const p = out((t - .65) / .17), fade = 1 - clamp((t - 1.42) / .14);
    ctx.save(); ctx.globalAlpha = fade; ctx.translate(640, 211); ctx.scale(.9 + .1 * p, .9 + .1 * p);
    ctx.shadowColor = '#ffcf7b'; ctx.shadowBlur = 22; rect(-430, -48, 860, 96, 28, '#153f31f5', '#ffc77e'); ctx.shadowBlur = 0;
    text('VÓ NGỰA CUỒNG PHONG', 0, 2, 42, '#fff3d2'); horseshoe(-378, -3, 30); horseshoe(378, -3, 30); ctx.restore();
  }
  function celebration(t) {
    if (t < 1.9 || action !== 'ultimate') return;
    const u = t - 1.9, colors = ['#ffcf7b', '#fff3c5', '#a1d28b', '#ffad86'];
    for (let i = 0; i < 42; i++) { const a = i * 2.39996, p = Math.max(0, u - (i % 5) * .02), v = 120 + i * 41 % 260, x = 650 + Math.cos(a) * v * p, y = 435 + Math.sin(a) * v * p + 100 * p * p; const alpha = clamp(1 - Math.max(0, p - .6) / .55); if (i % 8 === 0) horseshoe(x, y, 18, a + p, alpha); else star(x, y, 5 + i % 5, colors[i % 4], a + p, alpha); }
    ctx.save(); ctx.globalAlpha = out(u / .22); ctx.shadowColor = '#153f31'; ctx.shadowBlur = 16;
    ctx.font = '900 63px Arial,sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineWidth = 8; ctx.strokeStyle = '#26563d'; ctx.strokeText('CHIẾN THẮNG!', 640, 205); ctx.fillStyle = '#fff4ca'; ctx.fillText('CHIẾN THẮNG!', 640, 205); ctx.shadowBlur = 0;
    text('Vó Ngựa Cuồng Phong', 640, 261, 24, '#ffe3a3'); ctx.restore();
  }
  function frameBackground() {
    ctx.drawImage(assets.background, 0, 0, W, H);
    const gradient = ctx.createLinearGradient(0, 0, 0, H); gradient.addColorStop(0, '#0c2c26b5'); gradient.addColorStop(.47, '#0c2c2600'); gradient.addColorStop(1, '#08261a35'); ctx.fillStyle = gradient; ctx.fillRect(0, 0, W, H);
    text('5BMath', 45, 35, 25, '#fff5d9', 800, 'left'); text('NGỰA · ĐẤU TRÍ', W - 45, 35, 16, '#e8f1db', 800, 'right');
  }
  function actorUltimate(t) {
    let index = 0, x = 265, feet = 600, rotation = 0;
    if (t < .65) index = Math.min(2, Math.floor(t / .22));
    else if (t < .95) { index = 3; x -= 17 * smooth((t - .65) / .3); }
    else if (t < 1.55) { const u = (t - .95) / .6; x = mix(248, 635, smooth(u)); feet -= 17 * Math.sin(u * PI * 4); index = 4 + Math.floor(u * 12) % 4; rotation = -.035; streaks(x, feet); for (let i = 3; i > 0; i--) pose(index, x - 42 * i, feet + i * 2, { alpha: .045 + .025 * (3 - i), rotation }); }
    else if (t < 1.9) { x = 635; index = 8 + Math.min(3, Math.floor((t - 1.55) / .35 * 4)); feet -= 9 * Math.sin(clamp((t - 1.55) / .35) * PI); }
    else { x = 635; index = 12 + Math.min(3, Math.floor((t - 1.9) / .8 * 4)); feet -= 18 * Math.sin(clamp((t - 1.98) / .58) * PI); }
    shadow(x, 602); pose(index, x, feet, { rotation }); return index;
  }
  function actorReaction(t) {
    let index, x = 310, feet = 600, rotation = 0;
    if (action === 'attack') {
      if (t < .35) index = 0;
      else if (t < .65) { index = 1; x += 430 * out((t - .35) / .3); feet -= 22 * Math.sin((t - .35) / .3 * PI); streaks(x, feet, .7); }
      else if (t < .9) { index = 2; x = 740; }
      else if (t < 1.32) { index = 3; x = mix(740, 310, smooth((t - .9) / .42)); }
      else index = 12;
      if (t >= .65 && t < .94) { const u = clamp((t - .65) / .29); horseshoe(870 + 85 * u, 490, 40 + u * 24, -.5 + u, 1 - u); }
    } else if (action === 'hit') {
      if (t < .35) index = 4;
      else if (t < .62) { index = 5; x -= 45 * out((t - .35) / .27); rotation = -.04; }
      else if (t < 1.1) { index = 6; x -= 45; rotation = -.025; }
      else if (t < 1.65) { index = 7; x -= 45 * (1 - smooth((t - 1.1) / .55)); }
      else index = 12;
      if (t < .44) { const p = clamp(t / .4); star(mix(885, 345, out(p)), mix(430, 455, p), 18, '#ffdf98', p * PI * 2, 1 - clamp((t - .35) / .09)); }
      if (t >= .35 && t < .83) { const p = clamp((t - .35) / .48); for (let i = 0; i < 5; i++) { const a = -PI + i * PI / 5; star(x + Math.cos(a) * (55 + 70 * p), 430 + Math.sin(a) * (40 + 45 * p), 5 + 4 * (1 - p), '#ffe3a3', a, 1 - p); } }
    } else {
      index = t < .6 ? 8 : t < 1.13 ? 9 : t < 1.7 ? 10 : 11; x = 365; feet += 4 * smooth(t / 2);
      if (t > 1.5) { ctx.save(); ctx.globalAlpha = out((t - 1.5) / .4); rect(168, 195, 394, 64, 24, '#fff9edf0'); text('Nghỉ chút, rồi mình thử lại!', 365, 228, 23, '#203a32', 700); ctx.restore(); }
    }
    shadow(x, 605); pose(index, x, feet, { reaction: true, rotation }); return index;
  }
  function phaseAt(t) { if (action === 'ultimate') return t < .95 ? 'LẤY ĐÀ' : t < 1.9 ? 'VÓ NGỰA CUỒNG PHONG' : 'CHIẾN THẮNG'; if (action === 'attack') return t < .35 ? 'LẤY ĐÀ' : t < .95 ? 'CÚ VÓ NHANH' : 'SẴN SÀNG'; if (action === 'hit') return t < .35 ? 'BẤT NGỜ' : t < 1.1 ? 'CHỊU ĐÒN' : 'BÌNH TĨNH TRỞ LẠI'; return t < 1.7 ? 'BUỒN BÃ' : 'MÌNH SẼ THỬ LẠI!'; }
  function draw(t) {
    if (!loaded) return null;
    t = clamp(t, 0, DURATION); frameBackground(); if (action === 'ultimate') track(t); fox(t);
    const index = action === 'ultimate' ? actorUltimate(t) : actorReaction(t);
    if (action === 'ultimate') { windHorse(t); celebration(t); banner(t); }
    else { rect(413, 86, 454, 58, 22, '#153f31dc', '#c2d6b74d'); text(actions[action].title.toLocaleUpperCase('vi-VN'), 640, 116, action === 'defeat' ? 23 : 27, '#fff3d2'); }
    const phase = phaseAt(t); rect(420, 650, 440, 40, 20, '#153f31d9'); text(phase, 640, 671, 17, '#fff3d2');
    document.getElementById('seek').value = t; document.getElementById('clock').textContent = t.toFixed(2).replace('.', ',') + ' / 3,00 s';
    return { time: t, t, action, phase, pose: index, nameVisible: action === 'ultimate' && t >= .65 && t <= 1.56, attackStarted: action === 'ultimate' ? t >= .95 : action === 'attack' && t >= .35, impact: action === 'ultimate' ? t >= 1.75 : action === 'attack' && t >= .65, victory: action === 'ultimate' && t >= 1.9 };
  }
  function pause() { playing = false; if (raf) { cancelAnimationFrame(raf); raf = 0; } document.getElementById('pause').textContent = 'Tiếp tục'; }
  function play(reset = false) { if (!loaded) return; if (reset || clock >= DURATION) clock = 0; playing = true; last = performance.now(); document.getElementById('pause').textContent = 'Tạm dừng'; if (!raf) raf = requestAnimationFrame(tick); }
  function tick(now) { raf = 0; if (!playing) return; clock = Math.min(DURATION, clock + Math.max(0, (now - last) / 1000) * speed); last = now; draw(clock); if (clock < DURATION) raf = requestAnimationFrame(tick); else pause(); }
  function setAction(next, autoplay = false) {
    if (!Object.hasOwn(actions, next)) throw new Error('Hoạt cảnh không hợp lệ: ' + next);
    pause(); action = next; clock = 0; document.title = 'Ngựa — ' + actions[action].title + ' · 5BMath'; document.querySelector('h1').textContent = actions[action].title; document.querySelector('header p').textContent = actions[action].subtitle;
    for (const button of document.querySelectorAll('[data-action]')) button.setAttribute('aria-pressed', String(button.dataset.action === action));
    const beats = document.querySelectorAll('.beat'); actions[action].beats.forEach((line, i) => { const [title, detail] = line.split('|'); beats[i].replaceChildren(); const strong = document.createElement('strong'); strong.textContent = title; beats[i].append(strong, document.createTextNode(detail)); });
    canvas.setAttribute('aria-label', 'Ngựa — ' + actions[action].title + '. ' + actions[action].subtitle); if (loaded) draw(0); if (autoplay && !reduced.matches) play(); return action;
  }
  const ready = Promise.all([load('actor', C.webpFile || C.poseFile), load('reaction', 'assets/reactions.webp'), load('background', C.backgroundFile), load('opponent', C.opponentFile)]).then(() => {
    if (!window.ANIMATION_POSES?.frames || !window.HORSE_REACTIONS?.frames) throw new Error('Thiếu bản đồ tư thế poses.js hoặc reactions.js.');
    const frame = window.ANIMATION_POSES.frames[6], ghost = document.createElement('canvas'); ghost.width = frame.width; ghost.height = frame.height; const g = ghost.getContext('2d'); g.drawImage(assets.actor, frame.left, frame.top, frame.width, frame.height, 0, 0, frame.width, frame.height); g.globalCompositeOperation = 'source-in'; g.fillStyle = '#ffe3a3'; g.fillRect(0, 0, ghost.width, ghost.height); assets.windHorse = ghost;
    loaded = true; setAction(action); if (!query.has('export') && !reduced.matches) play(true);
  });
  window.animationDemo = { ready, render: draw, pause, play, setAction, duration: DURATION, config: C, get state() { return { action, time: clock, playing, raf, ready: loaded }; } };
  document.getElementById('replay').onclick = () => play(true); document.getElementById('pause').onclick = () => playing ? pause() : play();
  document.getElementById('speed').onchange = e => { speed = Number(e.target.value); };
  document.getElementById('seek').oninput = e => { pause(); clock = Number(e.target.value); draw(clock); };
  for (const button of document.querySelectorAll('[data-action]')) button.onclick = () => setAction(button.dataset.action, true);
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); }); reduced.addEventListener('change', () => { if (reduced.matches) pause(); }); window.addEventListener('pagehide', pause);
  ready.catch(error => { document.querySelector('.note').textContent = error.message; console.error(error); });
})();
