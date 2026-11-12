/* 5BMath Hổ — deterministic Canvas choreography shared by review and game adapters. */
(() => {
  'use strict';
  const PI = Math.PI;
  const durations = Object.freeze({ ultimate: 3, attack: .8, hurt: .65, defeat: 1.8, idle: 1.6, victory: 1.1 });
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const mix = (a, b, u) => a + (b - a) * u;
  const ease = u => { u = clamp(u); return u * u * (3 - 2 * u); };
  const out = u => 1 - (1 - clamp(u)) ** 3;
  const duration = mode => durations[mode] || durations.ultimate;
  function star(ctx, x, y, r, color, rotation = 0, alpha = 1) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rotation); ctx.globalAlpha *= alpha; ctx.beginPath();
    for (let i = 0; i < 10; i++) { const a = -PI / 2 + i * PI / 5, radius = i % 2 ? r * .43 : r, px = Math.cos(a) * radius, py = Math.sin(a) * radius; if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
    ctx.closePath(); ctx.fillStyle = color; ctx.fill(); ctx.restore();
  }
  function text(ctx, str, x, y, size, color = '#fff9ed', weight = 800) { ctx.font = `${weight} ${size}px Arial,sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = color; ctx.fillText(str, x, y); }
  function sprite(ctx, image, manifest, index, x, feet, height, facing, alpha = 1, rotation = 0, glow = 0) {
    const frames = manifest?.frames, f = frames?.[clamp(index, 0, (frames?.length || 1) - 1)]; if (!image || !f) return;
    const scale = height / Math.max(...frames.map(frame => frame.height));
    ctx.save(); ctx.translate(x, feet); ctx.rotate(rotation); ctx.scale(facing === 'left' ? -1 : 1, 1); ctx.globalAlpha *= alpha;
    if (glow) { ctx.shadowColor = '#ffe7a3'; ctx.shadowBlur = glow; ctx.filter = 'brightness(1.65) saturate(.6)'; }
    ctx.drawImage(image, f.left, f.top, f.width, f.height, -f.width * scale / 2, -f.height * scale, f.width * scale, f.height * scale); ctx.restore();
  }
  function shadow(ctx, x, y, width, alpha = .2) { ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = '#173c2c'; ctx.beginPath(); ctx.ellipse(x, y, width, Math.max(4, width * .1), 0, 0, PI * 2); ctx.fill(); ctx.restore(); }
  function slash(ctx, x, y, length, direction = 1, alpha = 1, angle = -.35) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.scale(direction, 1); ctx.globalAlpha *= alpha; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (let i = 0; i < 3; i++) { const dy = (i - 1) * 27; ctx.beginPath(); ctx.moveTo(-length * .5, dy - 25); ctx.lineTo(-length * .08, dy - 9); ctx.lineTo(-length * .2, dy + 9); ctx.lineTo(length * .5, dy + 24); ctx.strokeStyle = '#ffbe73'; ctx.lineWidth = 13 - i; ctx.shadowColor = '#ffd493'; ctx.shadowBlur = 14; ctx.stroke(); ctx.strokeStyle = '#fff5cc'; ctx.lineWidth = 4; ctx.shadowBlur = 0; ctx.stroke(); }
    ctx.restore();
  }
  function charge(ctx, t, x, feet, height, direction) {
    const fade = 1 - clamp((t - .95) / .12); if (t < .15 || fade <= 0) return;
    ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = '#ffe9ae'; ctx.lineWidth = height * .014; ctx.shadowColor = '#ffd18b'; ctx.shadowBlur = 9;
    for (let i = 0; i < 3; i++) { const appear = ease((t - .18 - i * .13) / .18); if (!appear) continue; ctx.globalAlpha = appear * fade * .75; const xx = x + direction * (i - 1) * height * .12, yy = feet - height * (.44 + .07 * i); ctx.beginPath(); ctx.moveTo(xx - direction * height * .08, yy - height * .13); ctx.quadraticCurveTo(xx + direction * height * .04, yy - height * .08, xx + direction * height * .06, yy + height * .04); ctx.stroke(); }
    ctx.restore();
  }
  function title(ctx, t, actorOnly) {
    if (actorOnly || t < .65 || t > 1.55) return;
    ctx.save(); ctx.globalAlpha *= out((t - .65) / .16) * (1 - clamp((t - 1.4) / .15)); ctx.fillStyle = '#173f32f2'; ctx.strokeStyle = '#ffbe73'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(290, 128, 700, 90, 25); ctx.fill(); ctx.stroke(); text(ctx, 'HỔ VỒ SẤM CHỚP', 640, 174, 43, '#fff3d2');
    slash(ctx, 338, 175, 36, 1, 1, -.65); slash(ctx, 942, 175, 36, -1, 1, .65); ctx.restore();
  }
  function bursts(ctx, t, x, y, radius = 145) {
    const p = clamp((t - 1.75) / .5); if (t < 1.75 || p >= 1) return;
    for (let i = 0; i < 18; i++) { const a = i * PI * 2 / 18, distance = radius * out(p); star(ctx, x + Math.cos(a) * distance, y + Math.sin(a) * distance * .7, 4 + 8 * (1 - p), i % 2 ? '#ffbe73' : '#fff1bc', a + p, 1 - p); }
  }
  function confetti(ctx, t, x, y, small = false) {
    if (t < 1.9) return; const p = t - 1.9;
    for (let i = 0; i < (small ? 12 : 32); i++) { const a = i * 2.4, v = 75 + (i * 41) % (small ? 100 : 240), fade = 1 - clamp((p - .65) / .5); star(ctx, x + Math.cos(a) * v * p, y + Math.sin(a) * v * p + 80 * p * p, 4 + i % 4, i % 3 ? '#ffdc8e' : '#abc98e', a + p, fade); }
  }
  function render(ctx, options = {}) {
    const mode = Object.hasOwn(durations, options.mode) ? options.mode : 'ultimate';
    const total = duration(mode), inputTime = clamp(Number(options.time) || 0, 0, total), reduced = options.reducedMotion === true || options.reduceMotion === true;
    const t = reduced ? (mode === 'ultimate' ? 3 : mode === 'defeat' ? total : mode === 'hurt' ? .3 : mode === 'attack' ? .38 : 0) : inputTime;
    const actorOnly = !!options.actorOnly, W = actorOnly ? 512 : 1280;
    const sceneHeight = Number.isFinite(options.sceneHeight) && options.sceneHeight > 0 ? options.sceneHeight : 720;
    const H = actorOnly ? 512 : sceneHeight, direction = options.facing === 'left' ? -1 : 1;
    const start = options.start || { x: actorOnly ? 256 : direction === 1 ? 278 : 1002, y: actorOnly ? 472 : 602 };
    const target = options.target || { x: direction === 1 ? 1030 : 250, y: 594 };
    const height = options.actorHeight || (actorOnly ? 370 : 318), targetHeight = options.targetHeight || 300, facing = options.facing || 'right';
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height); ctx.scale(ctx.canvas.width / W, ctx.canvas.height / H);
    if (!options.transparent) { if (options.background) ctx.drawImage(options.background, 0, 0, W, H); else { ctx.fillStyle = '#fff9ed'; ctx.fillRect(0, 0, W, H); } if (!actorOnly) { const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#0b30268c'); g.addColorStop(.5, '#0b302600'); g.addColorStop(1, '#0b302630'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); } }
    if (!actorOnly && options.opponent) { const impact = mode === 'ultimate' ? clamp((t - 1.75) / .24) : 0; ctx.save(); ctx.globalAlpha *= 1 - impact * .7; ctx.translate(target.x + direction * 28 * out(impact), target.y); ctx.rotate(direction * impact * .08); const img = options.opponent, half = img.width / 2; ctx.drawImage(img, half, 0, half, img.height, -targetHeight / 2, -targetHeight, targetHeight, targetHeight); ctx.restore(); }
    let index = 0, x = start.x, y = start.y, rotation = 0, source = options.actor, manifest = options.poses, phase = 'LẤY ĐÀ';
    if (mode === 'ultimate') {
      if (t < .95) { index = t < .22 ? 0 : t < .43 ? 1 : t < .65 ? 2 : 3; x -= direction * 16 * ease((t - .4) / .55); y += 6 * ease(t / .95); if (!reduced) charge(ctx, t, x, y, height, direction); }
      else if (t < 1.62) { const p = clamp((t - .95) / .67), q = ease(p), destination = actorOnly ? start.x + direction * 80 : mix(start.x, target.x, .76); x = mix(start.x - direction * 16, destination, q); y = mix(start.y, actorOnly ? start.y : target.y, q) - Math.sin(p * PI) * height * (actorOnly ? .26 : .62); index = 4 + Math.min(3, Math.floor(p * 4)); rotation = direction * (-.15 + p * .2); phase = 'BẬT VỒ';
        if (!reduced) { for (let k = 3; k >= 1; k--) sprite(ctx, source, manifest, index, x - direction * k * height * .14, y + k * height * .035, height, facing, .04 + (3 - k) * .035, rotation, 12); if (!actorOnly) slash(ctx, x - direction * height * .4, y - height * .45, height * .8, direction, Math.sin(p * PI) * .7, Math.atan2(target.y - start.y, Math.abs(target.x - start.x)) - .2); }
      } else if (t < 1.9) { const p = clamp((t - 1.62) / .28); x = actorOnly ? start.x + direction * 80 : mix(start.x, target.x, .76); y = actorOnly ? start.y : target.y; index = 8 + Math.min(3, Math.floor(p * 4)); phase = 'BA VỆT SẤM CHỚP'; }
      else { const p = clamp((t - 1.9) / 1.1); x = actorOnly ? mix(start.x + direction * 80, start.x, out(p)) : mix(start.x, target.x, .76); y = actorOnly ? start.y : target.y; index = 12 + Math.min(3, Math.floor(p * 4)); phase = 'CHIẾN THẮNG'; }
      if (!actorOnly && !reduced && t > 1.35 && t < 1.94) { const p = clamp((t - 1.35) / .59), alpha = Math.sin(p * PI) * .29, echoX = mix(start.x, target.x, .48 + .5 * out(p)), echoY = mix(start.y, target.y, p) - Math.sin(p * PI) * height * .35; sprite(ctx, options.actor, options.poses, 6, echoX, echoY, height * 1.65, facing, alpha, direction * -.06, 28); }
      if (!reduced && t >= 1.62 && t < 2.08) { const p = clamp((t - 1.62) / .22), fade = 1 - clamp((t - 1.83) / .25), tx = actorOnly ? x + direction * height * .10 : mix(x, target.x, out(p)), ty = actorOnly ? y - height * .45 : mix(y - height * .4, target.y - targetHeight * .5, out(p)); slash(ctx, tx, ty, height * (actorOnly ? .36 : .7), direction, fade, direction * -.45); }
      if (!actorOnly && !reduced) bursts(ctx, t, target.x, target.y - targetHeight * .5, height * .6);
    } else {
      source = options.reactions || options.actor; manifest = options.reactionPoses || options.poses; const p = clamp(t / total);
      if (mode === 'attack') { phase = 'TẤN CÔNG'; index = Math.min(3, Math.floor(p * 4)); const reach = actorOnly ? direction * height * .18 : (target.x - start.x) * .75; x += reach * Math.sin(p * PI); y += (actorOnly ? 0 : (target.y - start.y) * .75) * Math.sin(p * PI) - height * .065 * Math.sin(p * PI); if (!reduced && p >= .32 && p <= .72) slash(ctx, x + direction * height * (actorOnly ? .2 : .35), y - height * .48, height * (actorOnly ? .25 : .38), direction, Math.sin((p - .32) / .4 * PI), -.4 * direction); }
      else if (mode === 'hurt') { phase = 'CHỊU ĐÒN'; index = 4 + Math.min(3, Math.floor(p * 4)); x -= direction * height * .08 * Math.sin(p * PI); rotation = -.065 * direction * Math.sin(p * PI); if (!reduced && p < .65) for (let i = 0; i < 3; i++) star(ctx, x + (i - 1) * height * .13, y - height * (.85 + .08 * Math.sin(i)), height * .025, '#ffcf86', t * 3 + i, 1 - p / .65); }
      else if (mode === 'defeat') { phase = 'BUỒN KHI THUA'; index = 8 + Math.min(3, Math.floor(p * 4)); y += height * .025 * ease(p); rotation = direction * .015 * ease(p); if (!options.transparent && !actorOnly && p > .65) { ctx.save(); ctx.fillStyle = '#153f31ed'; ctx.beginPath(); ctx.roundRect(255, 151, 770, 74, 24); ctx.fill(); text(ctx, 'Nghỉ một chút, rồi thử lại nhé!', 640, 188, 34, '#fff9ed'); ctx.restore(); } }
      else if (mode === 'victory') { source = options.actor; manifest = options.poses; index = 12 + Math.min(3, Math.floor(p * 4)); phase = 'TỰ HÀO'; }
      else { phase = 'SẴN SÀNG'; index = 12 + Math.min(3, Math.floor(p * 4)); y -= reduced ? 0 : Math.sin(p * PI * 2) * height * .006; }
    }
    if (options.drawActor !== false) { shadow(ctx, x, actorOnly ? start.y + 3 : (mode === 'ultimate' && t >= 1.62 ? target.y : start.y) + 3, height * .25, .17); sprite(ctx, source, manifest, index, x, y, height, facing, 1, rotation); }
    if (mode === 'ultimate') { if (!reduced) confetti(ctx, t, x, y - height * .5, actorOnly); if (options.showTitle !== false) title(ctx, t, actorOnly); if (!actorOnly && t >= 1.9 && options.showVictory !== false) { ctx.save(); ctx.globalAlpha = out((t - 1.9) / .25); text(ctx, 'CHIẾN THẮNG!', 640, 172, 61, '#fff0ba', 900); text(ctx, 'Hổ Vồ Sấm Chớp', 640, 230, 24, '#ffe4ad'); ctx.restore(); } }
    if (!options.transparent && !actorOnly) { text(ctx, '5BMath', 100, 38, 24, '#fff5d9'); ctx.save(); ctx.fillStyle = '#153f31db'; ctx.beginPath(); ctx.roundRect(423, 650, 434, 42, 21); ctx.fill(); text(ctx, phase, 640, 672, 16, '#fff3d2'); ctx.restore(); }
    ctx.restore();
    const actorFrame = manifest?.frames?.[index], actorScale = height / Math.max(...(manifest?.frames || [{height: 1}]).map(f => f.height));
    const actorBounds = actorFrame ? {left:x-actorFrame.width*actorScale/2,right:x+actorFrame.width*actorScale/2,top:y-actorFrame.height*actorScale,bottom:y} : null;
    return { mode, time: inputTime, t: inputTime, duration: total, phase, pose: index, actorBounds, nameVisible: mode === 'ultimate' && inputTime >= .65 && inputTime <= 1.55, attackStarted: mode === 'ultimate' && inputTime >= .95, impact: mode === 'ultimate' && inputTime >= 1.75, victory: mode === 'ultimate' && inputTime >= 1.9, reducedMotion: reduced };
  }
  window.TigerAnimationRenderer = Object.freeze({ duration, durations, render, version: 'ho-v1-1' });
})();
