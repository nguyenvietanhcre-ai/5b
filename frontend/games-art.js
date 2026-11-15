(function (global) {
  'use strict';
  const D = typeof BadgeMascotData !== 'undefined' ? BadgeMascotData : (typeof require === 'function' ? require('./arena-art/badge-mascots/data.js') : {});
  const W = 1000, H = 700, TAU = Math.PI * 2, cache = new Map();
  const clamp = (n, a = 0, b = 1) => Math.max(a, Math.min(b, Number(n) || 0));
  const mapNumber = value => Math.floor(clamp(value, 1, 10));
  const mix = (a, b, t) => a + (b - a) * t;
  // The target is the visible centre of the flag cloth, not the canvas centre.
  // Keep this anchor shared by painting and capture-only facing calculations.
  function captureTarget(mapId) {
    const map = maps[mapNumber(mapId) - 1], f = map.captureFlag || { poleX: 485, poleY: 370, size: 58 };
    return { ...f, x: f.poleX + f.size / 2, y: f.poleY - f.size * 1.5 + f.size / 3 };
  }
  const captureFacing = (x, mapId) => x > captureTarget(mapId).x ? -1 : 1;
  const maps = [
    { id: 1, name: 'Vườn Nắng Mai', sky: '#e8f4e5', ground: '#cfe5b0', edge: '#719b58', path: '#f4e4b3', motif: 'flowers' },
    { id: 2, name: 'Rừng Tre Xanh', sky: '#d9eddf', ground: '#c2d9b4', edge: '#488575', path: '#e8d9aa', motif: 'bamboo' },
    { id: 3, name: 'Đầm Sen Hồng', sky: '#e6f2ed', ground: '#c9e0c1', edge: '#78a99c', path: '#f4e4c2', motif: 'lotus' },
    { id: 4, name: 'Đồi Lá Thu', sky: '#fff0d6', ground: '#edc795', edge: '#bf7d51', path: '#ffe6b5', motif: 'autumn' },
    { id: 5, name: 'Bờ Biển San Hô', sky: '#e1f5f5', ground: '#f0dfae', edge: '#68afbb', path: '#fff1cb', motif: 'shells' },
    { id: 6, name: 'Đêm Hội Trăng', sky: '#e3e4f3', ground: '#c4cba8', edge: '#7e86ad', path: '#f1d99b', motif: 'lanterns' },
    { id: 7, name: 'Đồi Chè Mây Trắng', sky: '#e5f2e7', ground: '#c1d6a5', edge: '#5a9368', path: '#eee2bc', motif: 'hills' },
    { id: 8, name: 'Đồng Hướng Dương', sky: '#fff1cc', ground: '#dce2ac', edge: '#b5a359', path: '#f7dda0', motif: 'sunflowers' },
    { id: 9, name: 'Vườn Trên Mây', sky: '#e4edf7', ground: '#e2e3e2', edge: '#96a4bf', path: '#fff4df', motif: 'clouds' },
    { id: 10, name: 'Khu Vườn Tuyết', sky: '#e8f0f5', ground: '#e3ece5', edge: '#8aa5aa', path: '#fff3d7', motif: 'snow' }
  ];
  const codeFor = player => {
    const raw = String(player.mascotCode || player.mascotId || player.mascot || 'sprout');
    return D[raw] ? raw : (Object.keys(D).find(k => D[k].id === raw) || 'sprout');
  };
  const speciesFor = player => D[codeFor(player)]?.speciesType || 'sprout';
  function laneOrder(players) {
    const priority = p => ['bird', 'insect'].includes(speciesFor(p)) ? 0 : speciesFor(p) === 'aquatic' ? 2 : 1;
    return players.map((p, i) => ({ p, i })).sort((a, b) => priority(a.p) - priority(b.p) || a.i - b.i).map(x => x.p);
  }
  const xpFor = p => p.mascotXp ?? p.xp ?? 0;
  const formFor = p => Math.min(2, Math.floor(Math.max(0, Number(xpFor(p)) || 0) / 100));
  function imageFor(code, base) {
    const key = base + code;
    if (!cache.has(key)) {
      const item = { image: null, failed: false };
      item.promise = new Promise(resolve => {
        const image = new Image();
        image.onload = () => { item.image = image; resolve(item); };
        image.onerror = () => { item.failed = true; resolve(item); };
        image.src = base + code + '.webp';
      });
      cache.set(key, item);
    }
    return cache.get(key);
  }
  function rounded(ctx, x, y, w, h, radius, fill, stroke) {
    ctx.beginPath(); ctx.roundRect(x, y, w, h, radius);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
  }
  function text(ctx, value, x, y, size = 22, color = '#203a32', align = 'center') {
    ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'middle';
    ctx.font = `700 ${size}px "Be Vietnam Pro",system-ui,sans-serif`; ctx.fillText(String(value), x, y);
  }
  function ellipse(ctx, x, y, rx, ry, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); ctx.fill(); }
  function star(ctx, x, y, r, fill) {
    ctx.beginPath();
    for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? r * .382 : r; ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
  }
  function flag(ctx, x, y, size = 75, wave = 0) {
    ctx.save(); ctx.translate(x, y);
    ctx.strokeStyle = '#86654c'; ctx.lineWidth = Math.max(3, size / 18); ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -size * 1.5); ctx.stroke();
    const top = -size * 1.5, hh = size * 2 / 3;
    ctx.fillStyle = '#da251d'; ctx.beginPath(); ctx.moveTo(0, top);
    ctx.quadraticCurveTo(size * .5, top + wave, size, top + wave * .5);
    ctx.lineTo(size, top + hh + wave * .5); ctx.quadraticCurveTo(size * .5, top + hh + wave, 0, top + hh); ctx.closePath(); ctx.fill();
    star(ctx, size * .5, top + hh * .5 + wave * .35, size * .2, '#ffff00'); ctx.restore();
  }
  function flower(ctx, x, y, size, color) {
    for (let i = 0; i < 6; i++) ellipse(ctx, x + Math.cos(i * TAU / 6) * size * .65, y + Math.sin(i * TAU / 6) * size * .65, size * .55, size * .55, color);
    ellipse(ctx, x, y, size * .42, size * .42, '#b18443');
  }
  function motif(ctx, theme, x, y, size, n) {
    ctx.save(); ctx.translate(x, y);
    if (theme.motif === 'bamboo') {
      for (let j = -1; j <= 1; j++) { rounded(ctx, j * size * .4, -size * 2.4, size * .18, size * 2.6, 5, '#568c65'); for (let k = 0; k < 3; k++) { ctx.strokeStyle = '#bfce95'; ctx.beginPath(); ctx.moveTo(j * size * .4, -k * size); ctx.lineTo(j * size * .4 + size * .18, -k * size); ctx.stroke(); ellipse(ctx, j * size * .4 + (k % 2 ? -.3 : .4) * size, -k * size - size * .3, size * .4, size * .13, '#6fa777'); } }
    } else if (theme.motif === 'lotus') {
      ellipse(ctx, 0, 0, size * 1.4, size * .55, '#8fbea8');
      for (let j = -2; j <= 2; j++) { ctx.save(); ctx.rotate(j * .3); ellipse(ctx, 0, -size * .3, size * .28, size * .65, j % 2 ? '#e9b1b3' : '#f7d4cd'); ctx.restore(); }
    } else if (theme.motif === 'autumn') {
      ctx.rotate(n * .7); for (let j = 0; j < 3; j++) { ellipse(ctx, j * size * .4, -j * size * .3, size * .6, size * .23, ['#dba361', '#b37d58', '#efc178'][j]); }
    } else if (theme.motif === 'shells') {
      ctx.fillStyle = n % 2 ? '#eab6a1' : '#ebc789'; ctx.beginPath(); ctx.moveTo(-size, 0); ctx.arc(0, 0, size, Math.PI, 0); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = '#fff9ed'; for (let j = 1; j < 5; j++) { ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(j * Math.PI / 5) * size, -Math.sin(j * Math.PI / 5) * size); ctx.stroke(); }
    } else if (theme.motif === 'lanterns') {
      ctx.strokeStyle = '#8d83a5'; ctx.beginPath(); ctx.moveTo(0, -size * 1.8); ctx.lineTo(0, -size * .8); ctx.stroke();
      ellipse(ctx, 0, 0, size * .75, size, n % 2 ? '#e3b566' : '#d38b81'); rounded(ctx, -size * .25, size * .9, size * .5, size * .3, 3, '#bc765d');
    } else if (theme.motif === 'hills') {
      for (let j = 2; j >= 0; j--) { ellipse(ctx, -size * .8 + j * size * .8, j * size * .23, size * 1.5, size * .7, ['#699e74', '#8bb289', '#abc69b'][j]); }
    } else if (theme.motif === 'sunflowers') {
      rounded(ctx, -3, 0, 6, size * 1.3, 3, '#78a262'); flower(ctx, 0, 0, size * .8, '#edc45d');
    } else if (theme.motif === 'clouds') {
      for (let j = -1; j <= 1; j++) ellipse(ctx, j * size * .7, Math.abs(j) * size * .2, size * .85, size * .6, '#fffdfa');
    } else if (theme.motif === 'snow') {
      ctx.strokeStyle = '#a3bdc5'; ctx.lineWidth = 3;
      for (let j = 0; j < 6; j++) { const a = j * TAU / 6; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * size, Math.sin(a) * size); ctx.stroke(); }
    } else flower(ctx, 0, 0, size * .7, n % 2 ? '#efc886' : '#f6e6ba');
    ctx.restore();
  }
  function backdrop(ctx, theme, mode) {
    const gradient = ctx.createLinearGradient(0, 0, 0, H); gradient.addColorStop(0, theme.sky); gradient.addColorStop(1, theme.ground); ctx.fillStyle = gradient; ctx.fillRect(0, 0, W, H);
    ellipse(ctx, 900, 75, 44, 44, theme.motif === 'lanterns' ? '#fff0bd' : '#ffe6a5');
    // Distinct terrain silhouettes and landmarks, kept outside the playable route.
    if (theme.motif === 'lotus') { ellipse(ctx, 60, 350, 113, 180, '#8ec7c5'); ellipse(ctx, 944, 395, 100, 190, '#9acac6'); }
    else if (theme.motif === 'shells') { ctx.fillStyle = '#8ac8d3'; ctx.beginPath(); ctx.moveTo(0, 625); for (let i = 0; i <= 20; i++) ctx.lineTo(i * 50, 618 + Math.sin(i * .9) * 20); ctx.lineTo(1000, 700); ctx.lineTo(0, 700); ctx.fill(); }
    else if (theme.motif === 'hills') { for (let i = 0; i < 4; i++) { ellipse(ctx, -5, 180 + i * 110, 110 - i * 10, 71, ['#a9c796', '#8bb480', '#6fa06b', '#56895d'][i]); ellipse(ctx, 1010, 180 + i * 110, 100 - i * 10, 70, ['#a9c796', '#8bb480', '#6fa06b', '#56895d'][i]); } }
    else if (theme.motif === 'bamboo') { for (const x of [24, 68, 944, 978]) { rounded(ctx, x, 160 + x % 80, 12, 360, 7, '#669e76'); for (let j = 0; j < 6; j++) ellipse(ctx, x + 15, 170 + j * 55, 35, 9, '#8cb18b'); } }
    else if (theme.motif === 'lanterns') { ctx.strokeStyle = '#77718d'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(30, 83); ctx.quadraticCurveTo(500, 150, 970, 83); ctx.stroke(); for (let j = 0; j < 7; j++) motif(ctx, theme, 100 + j * 133, 100 + Math.sin(j * Math.PI / 6) * 28, 17, j); }
    else if (theme.motif === 'clouds') { for (const x of [45, 950]) for (let j = 0; j < 4; j++) motif(ctx, theme, x, 190 + j * 120, 48, j); }
    else if (theme.motif === 'snow') { for (let j = 0; j < 8; j++) { ellipse(ctx, j % 2 ? 960 : 40, 160 + j * 59, 70, 27, '#ffffffc0'); star(ctx, 35 + j * 131, 100, 4, '#adc5cd'); } }
    else if (theme.motif === 'sunflowers') { for (const x of [39, 956]) for (let j = 0; j < 5; j++) motif(ctx, theme, x, 175 + j * 95, 29, j); }
    else if (theme.motif === 'autumn') { for (let j = 0; j < 14; j++) { const x = j % 2 ? 35 : 959; motif(ctx, theme, x, 150 + j * 34, 28, j); } }
    else { for (const x of [38, 957]) for (let j = 0; j < 6; j++) motif(ctx, theme, x, 175 + j * 79, 19, j); }
    for (let i = 0; i < 10; i++) { const x = 45 + i * 103; motif(ctx, theme, x, 60 + (i % 2) * 12, 19 + i % 3 * 4, i); motif(ctx, theme, x, 654 + (i % 2) * 7, 17, i + 1); }
    if (mode === 'capture_flag') {
      ellipse(ctx, 500, 350, 388, 255, theme.edge + '3b'); ellipse(ctx, 500, 350, 370, 238, theme.path);
      ellipse(ctx, 500, 350, 344, 215, theme.ground);
      ctx.strokeStyle = '#ffffff8a'; ctx.lineWidth = 3; ctx.setLineDash([9, 10]); ctx.beginPath(); ctx.ellipse(500, 350, 330, 205, 0, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
      const target = captureTarget(theme.id);
      ellipse(ctx, 500, 357, 48, 22, theme.path); flag(ctx, target.poleX, target.poleY, target.size);
    }
    text(ctx, theme.name, 500, 31, 24);
  }
  function fallback(ctx, p, x, y, size) {
    ellipse(ctx, x, y - size * .45, size * .3, size * .34, '#e2d8b9'); text(ctx, String(p.name || '?').slice(0, 1), x, y - size * .45, size * .3); text(ctx, 'Đang tải hình', x, y + 10, 17);
  }
  function pet(ctx, p, x, feet, size, time, moving, celebrate, base, reduced, holdingFlag, facing = 1) {
    const code = codeFor(p), data = D[code], image = imageFor(code, base).image;
    if (!data || !image) { fallback(ctx, p, x, feet, size); return; }
    const type = speciesFor(p), b = formFor(p), pulse = reduced ? 0 : Math.sin(time / (type === 'insect' ? 68 : type === 'bird' ? 130 : type === 'aquatic' ? 190 : 90));
    let frame = b * 4, dy = 0, angle = 0;
    if (celebrate) { frame = code === 'eagle' ? b * 4 + 1 : 12 + b; dy = reduced ? 0 : -Math.abs(Math.sin(time / 175)) * size * .055; }
    else if (moving) {
      // No hit/lose frame or dog attack choreography is reused for locomotion.
      frame = ['bird', 'insect'].includes(type) && pulse > 0 ? b * 4 + 1 : b * 4;
      if (['bird', 'insect'].includes(type)) { dy = -size * .07 + pulse * size * .025; angle = pulse * .025; }
      else if (type === 'aquatic') { dy = pulse * size * .035; angle = (code === 'crab' ? .02 : .045) * pulse; }
      else { dy = -Math.abs(pulse) * size * (code === 'rabbit' ? .1 : .04); angle = pulse * .025; }
    }
    const f = data.profile.frames[frame], scale = Math.min(size / Math.max(f.height, f.width * .9), size * 1.1 / f.width);
    ellipse(ctx, x, feet + 4, size * .25, size * .055, '#203a321c');
    ctx.save(); ctx.translate(x, feet + dy); ctx.rotate(angle);
    // Only capture callers supply a facing override. All profile/race/podium
    // callers keep the original approved orientation and source pixels.
    if (facing === -1) ctx.scale(-1, 1);
    ctx.drawImage(image, f.left, f.top, f.width, f.height, -f.width * scale / 2, -f.height * scale, f.width * scale, f.height * scale);
    if (holdingFlag) {
      // Grip follows the near paw/wing/fin; never adds a new limb or bakes over the source atlas.
      const gripX = size * .23, gripY = -size * .4;
      ctx.save(); ctx.translate(gripX, gripY + size * .3); ctx.rotate(.55);
      flag(ctx, 0, 0, size * (holdingFlag === 'podium' ? .34 : .43), reduced ? 0 : Math.sin(time / 170) * 3); ctx.restore();
    }
    ctx.restore();
  }
  function badge(ctx, label, x, y, color = '#1f6248') { ellipse(ctx, x, y, 18, 18, '#fff9ed'); text(ctx, label, x, y + 1, 21, color); }
  function capture(ctx, state, time, positions, base, reduced) {
    const players = (state.players || []).slice(0, 5), theme = maps[mapNumber(state.mapId) - 1]; backdrop(ctx, theme, 'capture_flag');
    for (let i = 0; i < players.length; i++) {
      const p = players[i], a = -Math.PI / 2 + i * TAU / 5, step = positions.get(String(p.id))?.value ?? clamp(p.steps, 0, 5), t = step / 5;
      const x = 500 + Math.cos(a) * mix(330, 35, t), y = 380 + Math.sin(a) * mix(220, 24, t);
      for (let j = 0; j < 5; j++) { const r = (j + 1) / 5; ellipse(ctx, 500 + Math.cos(a) * mix(35, 330, r), 350 + Math.sin(a) * mix(24, 220, r), 8, 6, j < 5 - Math.floor(step) ? '#ffffff90' : theme.edge + '55'); }
      const moving = !!positions.get(String(p.id))?.moving, win = state.winnerId != null && String(state.winnerId) === String(p.id);
      pet(ctx, p, x, y, 108, time, moving, win, base, reduced, win, captureFacing(x, state.mapId));
      badge(ctx, `${Math.floor(clamp(p.steps, 0, 5))}/5`, x, y + 25); text(ctx, String(p.name || 'Người chơi').slice(0, 16), i === 0 ? x + 106 : x, i === 0 ? y + 13 : y + 53, 20);
    }
  }
  function legacyRace(ctx, state, time, positions, base, reduced) {
    const theme = maps[mapNumber(state.mapId) - 1]; backdrop(ctx, theme, 'animal_race');
    const players = laneOrder((state.players || []).slice(0, 5));
    rounded(ctx, 70, 104, 863, 510, 28, theme.edge + '30');
    for (let i = 0; i < 5; i++) {
      const p = players[i], y = 124 + i * 96, type = p ? speciesFor(p) : 'mammal', water = type === 'aquatic', air = ['bird', 'insect'].includes(type);
      rounded(ctx, 83, y, 835, 88, 14, water ? '#a8d9e0' : air ? '#dfedf3' : theme.path);
      if (water) { ctx.strokeStyle = '#ffffff75'; ctx.lineWidth = 3; for (let n = 0; n < 12; n++) { const xx = 100 + n * 69; ctx.beginPath(); ctx.moveTo(xx, y + 60); ctx.quadraticCurveTo(xx + 15, y + 50, xx + 30, y + 60); ctx.quadraticCurveTo(xx + 45, y + 70, xx + 60, y + 60); ctx.stroke(); } }
      if (air) { for (let n = 0; n < 5; n++) ellipse(ctx, 180 + n * 151, y + 65, 27, 6, '#ffffff6b'); }
      for (let j = 0; j < 6; j++) { ctx.strokeStyle = '#ffffffa8'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(150 + j * 140, y + 7); ctx.lineTo(150 + j * 140, y + 81); ctx.stroke(); }
      if (!p) continue;
      const current = positions.get(String(p.id)), step = current?.value ?? clamp(p.steps, 0, 5), x = 145 + step * 140;
      // Paint names behind the sprite, so arrival labels cannot mask eyes/faces.
      text(ctx, String(p.name || 'Người chơi').slice(0, 14), Math.min(820, Math.max(235, x + 94)), y + 22, 20);
      pet(ctx, p, x, y + 80, 86, time, !!current?.moving, state.winnerId != null && String(state.winnerId) === String(p.id), base, reduced, false);
      badge(ctx, i + 1, 108, y + 20);
    }
    for (let i = 0; i < 22; i++) { ctx.fillStyle = i % 2 ? '#fff9ed' : '#203a32'; ctx.fillRect(881 + (i % 2) * 12, 118 + Math.floor(i / 2) * 44, 12, 44); }
    rounded(ctx, 809, 82, 129, 33, 10, '#1f6248'); text(ctx, 'VỀ ĐÍCH', 874, 99, 19, '#fff9ed');
    text(ctx, 'XUẤT PHÁT', 150, 628, 18);
  }
  function race(ctx,state,time,positions,base,reduced,roster,widthCss,onReady) {
    const rs=global.RaceScenes;if(!rs){legacyRace(ctx,state,time,positions,base,reduced);return null;}
    const scene=rs.draw(ctx,{mapId:state.mapId,roster,widthCss,dpr:devicePixelRatio||1,onReady});
    const actorSize=scene.mobile?Math.max(120,44/widthCss*1000):86,labelFontSize=scene.mobile?12/widthCss*1000:19;
    text(ctx,scene.themeName,430,scene.mobile?48:33,scene.mobile?Math.max(28,12/widthCss*1000):24);
    rounded(ctx,811,scene.mobile?23:17,108,39,12,'#1f6248');text(ctx,'ĐÍCH',865,scene.mobile?43:37,scene.mobile?Math.max(29,12/widthCss*1000):20,'#fff9ed');
    for(const lane of scene.lanes){const p=(state.players||[]).find(p=>String(p.id)===lane.id)||lane.player,current=positions.get(lane.id),step=current?.value??clamp(p.steps,0,5),x=mix(lane.startX,lane.finishX,step/5);
      const boxW=scene.mobile?245:198,maxTextW=boxW-22,rows=[];let rest=String(lane.slot+1)+'. '+String(p.name||'Người chơi').replace(/\s+/g,' ').trim();
      ctx.font=`700 ${labelFontSize}px "Be Vietnam Pro",system-ui,sans-serif`;
      for(let row=0;row<2&&rest;row++){if(ctx.measureText(rest).width<=maxTextW){rows.push(rest);break;}let n=0;while(n<rest.length&&ctx.measureText(rest.slice(0,n+1)+(row===1?'…':'')).width<=maxTextW)n++;n=Math.max(1,n);if(row===0){const space=rest.lastIndexOf(' ',n);if(space>2)n=space;rows.push(rest.slice(0,n).trim());rest=rest.slice(n).trim();}else rows.push(rest.slice(0,n).trim()+'…');}
      const lineH=labelFontSize*1.2,boxH=Math.max(52,rows.length*lineH+18),labelX=12+boxW/2;
      rounded(ctx,12,lane.y-actorSize*.75,boxW,boxH,15,'#fff9edec');rows.forEach((s,i)=>text(ctx,s,labelX,lane.y-actorSize*.75+14+lineH*(i+.25),labelFontSize));
      pet(ctx,p,x,lane.y,actorSize,time,!!current?.moving,state.winnerId!=null&&String(state.winnerId)===lane.id,base,reduced,false);
    }
    return {...scene,actorSize,labelFontSize};
  }
  const paperColors = ['#dbad42', '#ffbe73', '#6ba286', '#e9a7a0', '#8cb8c9', '#c8a4ca', '#efe1a5'];
  const paperCache = new Map(), paperEpochs = new Map();
  function confettiEpoch(seed) {
    if (!paperEpochs.has(seed)) { if (paperEpochs.size >= 32) paperEpochs.delete(paperEpochs.keys().next().value); paperEpochs.set(seed, performance.now()); }
    return paperEpochs.get(seed);
  }
  function seeded(seed) {
    let value = 2166136261;
    for (const char of String(seed)) value = Math.imul(value ^ char.charCodeAt(0), 16777619);
    return () => { value += 0x6d2b79f5; let t = Math.imul(value ^ value >>> 15, 1 | value); t ^= t + Math.imul(t ^ t >>> 7, 61 | t); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  function confettiParticles(seed = '5bmath', count = 60) {
    count = Math.floor(clamp(count, 1, 96)); const key = `${seed}:${count}`;
    if (paperCache.has(key)) return paperCache.get(key);
    const random = seeded(seed), between = (a, b) => mix(a, b, random());
    const result = Array.from({ length: count }, () => {
      const side = random(), direction = side < .38 ? 1 : side < .76 ? -1 : 0;
      return Object.freeze({
        ox: direction === 1 ? between(-.08, .17) : direction === -1 ? between(.83, 1.08) : between(.15, .85),
        oy: direction ? between(.5, 1.03) : between(-.18, .22),
        vx: direction ? direction * between(.28, 1.04) : between(-.25, .25),
        vy: direction ? between(-1.3, -.5) : between(-.18, .2),
        drag: between(.5, 1.6), gravity: between(.45, 1), life: between(3, 4.8),
        delay: between(0, .7), phase: between(.05, 1.8), pause: between(.65, 2.2),
        rotation: between(-Math.PI, Math.PI), spin: between(-8, 8), flutter: between(1.6, 6.7),
        width: between(3, 8), height: between(5, 14), shape: random(), color: paperColors[Math.floor(random() * paperColors.length)],
        stillX: between(.025, .975), stillY: between(.03, .94)
      });
    });
    if (paperCache.size >= 16) paperCache.delete(paperCache.keys().next().value);
    paperCache.set(key, Object.freeze(result)); return paperCache.get(key);
  }
  function confettiFrame(seed, time, width, height, reduced, repeat = true, count = 60) {
    return confettiParticles(seed, count).map(p => {
      const age = reduced ? .8 : repeat ? (Math.max(0, time) / 1000 + p.phase) % (p.life + p.pause) : Math.max(0, time) / 1000 + p.phase - p.delay;
      if (!reduced && (age < 0 || age > p.life)) return null;
      const travel = (1 - Math.exp(-p.drag * age)) / p.drag;
      const x = reduced ? p.stillX : p.ox + p.vx * travel + Math.sin(age * p.flutter + p.rotation) * .008;
      const y = reduced ? p.stillY : p.oy + (p.vy - p.gravity / p.drag) * travel + p.gravity * age / p.drag;
      return { ...p, x: x * width, y: y * height, angle: p.rotation + (reduced ? 0 : p.spin * age),
        alpha: reduced ? .4 : .82 * Math.min(1, age / .12, (p.life - age) / .65),
        tilt: reduced ? .8 : Math.max(.16, Math.abs(Math.cos(age * p.flutter + p.rotation))) };
    }).filter(Boolean);
  }
  function drawConfetti(ctx, time, width, height, seed, reduced, repeat = true, count = 60) {
    const scale = Math.max(.6, Math.min(1, width / 650));
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, width, height); ctx.clip();
    for (const p of confettiFrame(seed, time, width, height, reduced, repeat, count)) {
      if (p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20 || p.alpha <= 0) continue;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.angle); ctx.globalAlpha = p.alpha; ctx.fillStyle = p.color;
      const w = p.width * p.tilt * scale, h = p.height * scale;
      if (p.shape < .18) { ctx.beginPath(); ctx.ellipse(0, 0, Math.max(1, w / 2), h / 2, 0, 0, TAU); ctx.fill(); }
      else { ctx.fillRect(-w / 2, -h / 2, w, h); }
      ctx.restore();
    }
    ctx.restore();
  }
  function confetti(ctx, time, reduced, state) {
    drawConfetti(ctx, time, W, 560, state?.confettiSeed || `podium:${(state?.players || []).map(p => p.id).join(':')}`, reduced);
  }
  function confettiMarkup(options = {}) {
    const seed = options.seed ?? '5bmath-celebration';
    return `<canvas class="garden-celebration-confetti ${escapeHTML(options.className || '')}" data-garden-confetti="${escapeHTML(seed)}" aria-hidden="true"></canvas>`;
  }
  function mountConfetti(root, options = {}) {
    const canvases = root?.matches?.('[data-garden-confetti]') ? [root] : [...(root?.querySelectorAll?.('[data-garden-confetti]') || [])];
    const controllers = canvases.map(canvas => {
      const ctx = canvas.getContext('2d'), media = matchMedia('(prefers-reduced-motion: reduce)'), seed = options.seed ?? canvas.dataset.gardenConfetti;
      // Polls may replace the DOM. The same celebration seed keeps its clock,
      // so particles never restart as a synchronized row on every poll.
      let disposed = false, raf = 0, start = confettiEpoch(String(seed)), pausedAt = null, manual = null, onscreen = true;
      const reduced = () => options.reducedMotion === true || media.matches;
      function draw(now) {
        if (disposed) return;
        const box = canvas.getBoundingClientRect(), width = Math.max(1, box.width), height = Math.max(1, box.height), dpr = Math.min(2, devicePixelRatio || 1);
        if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height);
        drawConfetti(ctx, manual ?? Math.max(0, now - start), width, height, seed, reduced(), options.repeat !== false, reduced() ? 20 : width < 500 ? 40 : 64);
        canvas.dataset.confettiReady = 'true';
      }
      function tick(now) {
        raf = 0; if (!canvas.isConnected) { destroy(); return; }
        draw(now);
        if (!disposed && !document.hidden && onscreen && !reduced() && manual === null && (options.repeat !== false || now - start < 5500)) raf = requestAnimationFrame(tick);
      }
      function schedule() { if (!disposed && !raf && !document.hidden && onscreen && !reduced() && manual === null) raf = requestAnimationFrame(tick); }
      function visibility() {
        const now = performance.now(), paused = document.hidden || !onscreen;
        cancelAnimationFrame(raf); raf = 0;
        if (paused) { if (pausedAt === null) pausedAt = now; }
        else { if (pausedAt !== null) start += now - pausedAt; pausedAt = null; draw(now); schedule(); }
      }
      function motionChange() { cancelAnimationFrame(raf); raf = 0; draw(performance.now()); schedule(); }
      const resize = typeof ResizeObserver === 'function' ? new ResizeObserver(() => draw(performance.now())) : null;
      const intersection = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => { onscreen = entries[0]?.isIntersecting !== false; visibility(); }) : null;
      function destroy() { if (disposed) return; disposed = true; cancelAnimationFrame(raf); raf = 0; resize?.disconnect(); intersection?.disconnect(); document.removeEventListener('visibilitychange', visibility); media.removeEventListener?.('change', motionChange); canvas.dataset.confettiDestroyed = 'true'; }
      resize?.observe(canvas); intersection?.observe(canvas); document.addEventListener('visibilitychange', visibility); media.addEventListener?.('change', motionChange);
      draw(start); schedule();
      return { ready: () => Promise.resolve(), destroy, renderAt(ms) { if (!disposed) { manual = Math.max(0, Number(ms) || 0); cancelAnimationFrame(raf); raf = 0; draw(start + manual); } },
        getState: () => ({ disposed, animationScheduled: !!raf, reducedMotion: reduced(), seed, onscreen, count: reduced() ? 20 : canvas.clientWidth < 500 ? 40 : 64 }) };
    });
    return { ready: () => Promise.all(controllers.map(c => c.ready())), destroy() { controllers.forEach(c => c.destroy()); }, renderAt(ms) { controllers.forEach(c => c.renderAt(ms)); }, getState: () => controllers.map(c => c.getState()) };
  }
  function podium(ctx, state, time, base, reduced) {
    backdrop(ctx, maps[mapNumber(state.mapId) - 1], 'podium');
    const players = (state.players || []).filter(p => Number(p.rank) >= 1 && Number(p.rank) <= 3).sort((a, b) => a.rank - b.rank);
    if (!players.length) { text(ctx, 'Chưa có kết quả xếp hạng', 500, 350, 28); return; }
    confetti(ctx, time, reduced, state);
    const geometry = { 1: { x: 500, top: 420, color: '#f0cf81' }, 2: { x: 260, top: 468, color: '#d2dfe0' }, 3: { x: 740, top: 495, color: '#dfbc99' } };
    for (const p of players) {
      const g = geometry[p.rank]; rounded(ctx, g.x - 110, g.top, 220, 620 - g.top, 17, g.color);
      text(ctx, p.rank, g.x, g.top + 43, 46); pet(ctx, p, g.x, g.top - 14, p.rank === 1 ? 208 : 172, time, false, true, base, reduced, p.rank === 1 && state.captureWinner === true);
      rounded(ctx, g.x - 108, 626, 216, 42, 14, '#fff9eddd'); text(ctx, String(p.name || 'Người chơi').slice(0, 17), g.x, 647, 21);
      if (p.rank === 1) { star(ctx, g.x, 154, 27, '#d6a63e'); }
    }
    text(ctx, state.title || 'Chúc mừng các nhà vô địch!', 500, 99, 29);
  }
  function podiumActor(ctx, state, time, base, reduced) {
    const p = (state.players || [])[0];
    if (!p) return;
    const carrying = state.captureWinner === true && Number(p.rank) === 1;
    pet(ctx, p, carrying ? 390 : 500, 954, carrying ? 680 : 720, time, false, true, base, reduced, carrying ? 'podium' : false);
  }
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hasNumber = value => typeof value === 'number' && Number.isFinite(value);
  const leafIcon = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M7 26c4-11 10-18 20-21 1 13-4 21-14 20M9 23l14-13" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/><path d="m12 17 7 1m-3-6 1 6" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
  const trophyIcon = '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M15 7h18v13c0 7-4 11-9 11s-9-4-9-11V7Z" fill="currentColor"/><path d="M15 11H8v6c0 6 4 9 9 9m16-15h7v6c0 6-4 9-9 9M24 31v8m-8 3h16" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><path d="m24 11 2.5 5 5.5.8-4 3.8 1 5.4-5-2.5-5 2.5 1-5.4-4-3.8 5.5-.8Z" fill="#fff9ed"/></svg>';
  const medalIcon = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="m8 3 8 11 8-11-3 13H11L8 3Z" fill="currentColor" opacity=".55"/><circle cx="16" cy="21" r="9" fill="none" stroke="currentColor" stroke-width="2.4"/><path d="m16 15 1.6 3.3 3.6.5-2.6 2.5.6 3.6-3.2-1.7-3.2 1.7.6-3.6-2.6-2.5 3.6-.5Z" fill="currentColor"/></svg>';
  function podiumRows(players) {
    const seen = new Set();
    return (Array.isArray(players) ? players : []).filter(p => {
      const r = Number(p?.rank); if (![1, 2, 3].includes(r) || seen.has(r)) return false; seen.add(r); return true;
    }).sort((a, b) => Number(a.rank) - Number(b.rank));
  }
  function badgeText(p) {
    const xp = p.mascotXp ?? p.xp;
    if (!hasNumber(xp)) return '';
    const n = Math.min(14, Math.floor(Math.max(0, xp) / 20));
    return ['Đồng', 'Bạc', 'Vàng'][Math.floor(n / 5)] + ' ' + ['I', 'II', 'III', 'IV', 'V'][n % 5];
  }
  function scoreMarkup(score) {
    const formatted = score.toLocaleString('vi-VN'), groups = formatted.split('.');
    return `<strong class="garden-podium-score-value${formatted.length > 9 ? ' garden-podium-score-long' : ''}">${groups.map((g, i) => `<span class="garden-podium-number-group">${escapeHTML(g + (i < groups.length - 1 ? '.' : ''))}</span>`).join('<wbr>')}</strong>`;
  }
  function podiumMarkup(players, options = {}) {
    const rows = podiumRows(players), title = options.title ?? 'Những mầm tài năng';
    const particles = confettiMarkup({ seed: options.confettiSeed || `podium:${options.kind || ''}:${rows.map(p => p.id).join(':')}` });
    const head = title ? `<header class="garden-podium-heading"><span class="garden-podium-kicker">${leafIcon}<span>Cùng học, cùng tỏa sáng</span>${leafIcon}</span><h3>${escapeHTML(title)}</h3></header>` : '';
    if (!rows.length) return `<section class="garden-podium garden-podium-empty" aria-label="Bục vinh danh"><div class="garden-podium-empty-mark">${trophyIcon}</div>${head}<p>Chưa có kết quả xếp hạng.</p><small>Những kết quả thật sẽ xuất hiện ở đây.</small></section>`;
    const cards = rows.map((p, i) => {
      const rank = Number(p.rank), code = codeFor(p), mascotName = D[code]?.name || 'Linh vật', playerName = String(p.name ?? '').trim();
      const badge = badgeText(p), score = hasNumber(p.score) ? p.score : null, scoreLabel = String(p.scoreLabel ?? options.metricLabel ?? '').trim();
      return `<li class="garden-podium-slot garden-podium-place-${rank}" data-podium-rank="${rank}"><div class="garden-podium-figure"><span class="garden-podium-halo" aria-hidden="true"></span>${rank === 1 ? `<span class="garden-podium-crown" aria-hidden="true">${trophyIcon}</span>` : ''}<canvas class="garden-podium-actor" data-podium-actor="${i}" aria-hidden="true"></canvas></div><div class="garden-podium-plinth"><span class="garden-podium-place"><span class="garden-podium-place-icon">${rank === 1 ? trophyIcon : medalIcon}</span><span>Hạng <strong>${rank}</strong></span></span><h4 class="garden-podium-mascot">${escapeHTML(mascotName)}</h4>${playerName && playerName !== mascotName ? `<p class="garden-podium-player">${escapeHTML(playerName)}</p>` : ''}${badge ? `<span class="garden-podium-badge">${medalIcon}<span>${escapeHTML(badge)}</span></span>` : ''}${score !== null && scoreLabel ? `<div class="garden-podium-score">${scoreMarkup(score)}<span>${escapeHTML(scoreLabel)}</span></div>` : ''}${p.detailLabel ? `<small class="garden-podium-detail">${escapeHTML(p.detailLabel)}</small>` : ''}</div></li>`;
    }).join('');
    return `<section class="garden-podium garden-podium-count-${rows.length}" aria-label="Bục vinh danh ba vị trí đầu" data-podium-kind="${escapeHTML(options.kind || '')}">${particles}${head}<ol class="garden-podium-slots">${cards}</ol><div class="garden-podium-ground" aria-hidden="true">${leafIcon}<span>5BMath · Mỗi bước tiến đều đáng tự hào</span>${leafIcon}</div></section>`;
  }
  function mountPodium(root, initial = {}) {
    if (!root || typeof root.querySelectorAll !== 'function') throw new TypeError('GamesArt.mountPodium requires an element');
    let state = { players: [], ...initial }, controllers = [], effect = null, disposed = false, host = root;
    function clear() { controllers.forEach(c => c.destroy()); controllers = []; effect?.destroy(); effect = null; }
    function render() {
      if (disposed) return; clear();
      const template = document.createElement('template'); template.innerHTML = podiumMarkup(state.players, state);
      const section = template.content.firstElementChild;
      if (root.classList.contains('garden-podium')) { root.className = section.className; root.innerHTML = section.innerHTML; root.setAttribute('aria-label', section.getAttribute('aria-label')); host = root; }
      else { root.replaceChildren(section); host = section; }
      const rows = podiumRows(state.players);
      for (const canvas of host.querySelectorAll('[data-podium-actor]')) {
        const p = rows[Number(canvas.dataset.podiumActor)];
        controllers.push(mount(canvas, { mode: 'podium_actor', players: [p], captureWinner: state.captureWinner === true, reducedMotion: state.reducedMotion, assetBase: state.assetBase }));
      }
      effect = mountConfetti(host, { reducedMotion: state.reducedMotion, repeat: state.confettiRepeat !== false });
    }
    render();
    return { update(next) { if (!disposed) { state = { ...state, ...next }; render(); } }, ready() { return Promise.all([...controllers.map(c => c.ready()), effect?.ready()]); }, renderAt(ms) { controllers.forEach(c => c.renderAt(ms)); effect?.renderAt(ms); }, destroy() { if (disposed) return; disposed = true; clear(); host.querySelectorAll('canvas').forEach(c => { c.dataset.artDestroyed = 'true'; }); }, getState() { return { disposed, players: podiumRows(state.players).length, actorStates: controllers.map(c => c.getState()), confetti: effect?.getState() || [] }; } };
  }
  // Memory-only room poses survive harmless DOM refreshes; never infer score.
  const motionRooms = new Map(), MOTION_MS = 900;
  function clearMotion(key) { motionRooms.delete(String(key)); }
  function samplePosition(p, now, snap) {
    const t = snap ? 1 : clamp((now - p.changed) / MOTION_MS);
    p.value = mix(p.from, p.to, t * t * (3 - 2 * t));
    p.moving = t < 1 && Math.abs(p.to - p.from) > .00001;
    return p;
  }
  function mount(canvas, initial = {}) {
    if (!canvas || typeof canvas.getContext !== 'function') throw new TypeError('GamesArt.mount requires a canvas');
    let state = { mode: 'capture_flag', mapId: 1, players: [], ...initial }, disposed = false, raf = 0, start = performance.now(), manualTime = null;
    const ctx = canvas.getContext('2d'), media = matchMedia('(prefers-reduced-motion: reduce)');
    const motionKey = initial.motionKey == null ? null : String(initial.motionKey);
    let roomPose = motionKey === null ? null : motionRooms.get(motionKey);
    if (!roomPose && motionKey !== null) {
      if (motionRooms.size >= 16) motionRooms.delete(motionRooms.keys().next().value);
      roomPose = { positions: new Map(), mode: state.mode, mapId: mapNumber(state.mapId) }; motionRooms.set(motionKey, roomPose);
    }
    const positions = roomPose?.positions || new Map();
    let raceRoster=roomPose?.raceRoster||null,raceScene=null;
    let offscreen = false, pausedAt = null,raceStyled=false;
    const originalAspect=canvas.style.aspectRatio,originalHeight=canvas.style.height,originalMaxHeight=canvas.style.maxHeight;
    const base = initial.assetBase || '/arena-art/badge-mascots/';
    const reduced = () => state.reducedMotion === true || (state.reducedMotion !== false && media.matches);
    const clock = () => manualTime === null ? performance.now() : start + manualTime;
    canvas.classList.add('games-art-canvas');
    if (!canvas.hasAttribute('role')) canvas.setAttribute('role', 'img');
    if (!canvas.hasAttribute('aria-label')) canvas.setAttribute('aria-label', state.mode === 'animal_race' ? 'Vị trí các linh vật trên đường đua' : state.mode === 'podium' ? 'Bục chúc mừng ba người đứng đầu' : 'Các linh vật tiến về lá cờ Việt Nam');
    function sync() {
      const now = pausedAt ?? clock();
      if (roomPose && (roomPose.mode !== state.mode || roomPose.mapId !== mapNumber(state.mapId))) {
        positions.clear(); roomPose.mode = state.mode; roomPose.mapId = mapNumber(state.mapId);raceRoster=null;roomPose.raceRoster=null;
      }
      if(state.mode==='animal_race'&&global.RaceScenes&&(!raceRoster||raceRoster.length<5&&(state.players||[]).length===5)){raceRoster=global.RaceScenes.pin(state.players);if(roomPose)roomPose.raceRoster=raceRoster;}
      for (const p of state.players || []) {
        const id = String(p.id), to = clamp(p.steps ?? p.correctCount ?? p.correct ?? 0, 0, 5), prior = positions.get(id);
        if (!prior) positions.set(id, { from: to, to, value: to, changed: now, moving: false });
        else if (prior.to !== to) {
          samplePosition(prior, now, reduced());
          positions.set(id, { from: prior.value, to, value: prior.value, changed: now, moving: !reduced() });
        }
        imageFor(codeFor(p), base).promise.then(() => { if (!disposed && !document.hidden && !offscreen) draw(clock()); });
      }
      const ids = new Set((state.players || []).map(p => String(p.id))); for (const id of positions.keys()) if (!ids.has(id)) positions.delete(id);
    }
    function draw(now) {
      if (disposed) return;
      const cssWidth=canvas.getBoundingClientRect().width||640;
      const raceHeight=state.mode==='animal_race'&&global.RaceScenes?global.RaceScenes.layout(raceRoster||[],{widthCss:cssWidth}).logicalHeight:H;
      if(state.mode==='animal_race'&&global.RaceScenes){canvas.style.aspectRatio='1000 / '+raceHeight;canvas.style.height='auto';canvas.style.maxHeight='none';raceStyled=true;}else if(raceStyled){canvas.style.aspectRatio=originalAspect;canvas.style.height=originalHeight;canvas.style.maxHeight=originalMaxHeight;raceStyled=false;}
      const dpr = Math.max(1, Math.min(2, devicePixelRatio || 1)), rect = canvas.getBoundingClientRect(), width = Math.max(1, Math.round((rect.width || 640) * dpr)), height = Math.max(1, Math.round((rect.height || 448) * dpr));
      if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
      const logicalHeight = state.mode === 'podium_actor' ? 1000 : state.mode==='animal_race'?raceHeight:H;
      ctx.setTransform(width / W, 0, 0, height / logicalHeight, 0, 0); ctx.clearRect(0, 0, W, logicalHeight);
      for (const p of positions.values()) samplePosition(p, pausedAt ?? now, reduced());
      const time = manualTime === null ? now - start : manualTime;
      if (state.mode === 'podium_actor') podiumActor(ctx, state, time, base, reduced());
      else if (state.mode === 'podium') podium(ctx, state, time, base, reduced());
      else if (state.mode === 'animal_race') raceScene=race(ctx, state, time, positions, base, reduced(),raceRoster||[],cssWidth,raceAssetReady);
      else capture(ctx, state, time, positions, base, reduced());
      canvas.dataset.artReady = 'true';
      canvas.dataset.mapId = String(mapNumber(state.mapId));
      canvas.dataset.assetErrors = String((state.players || []).filter(p => imageFor(codeFor(p), base).failed).length);
    }
    function tick(now) { raf = 0; if (!canvas.isConnected) { destroy(); return; } draw(now); schedule(); }
    function raceAssetReady(){if(!disposed&&!document.hidden&&!offscreen)draw(clock());}
    function schedule() { if (!disposed && !document.hidden && !offscreen && !reduced() && !raf && manualTime === null) raf = requestAnimationFrame(tick); }
    function visibility() {
      const now = clock();
      if (document.hidden || offscreen) { if (pausedAt === null) pausedAt = now; cancelAnimationFrame(raf); raf = 0; }
      else { if (pausedAt !== null) { for (const p of positions.values()) p.changed += now - pausedAt; pausedAt = null; } draw(now); schedule(); }
    }
    function motionChange() { cancelAnimationFrame(raf); raf = 0; draw(clock()); if (!reduced()) schedule(); }
    const resize = typeof ResizeObserver === 'function' ? new ResizeObserver(() => { if (!disposed && !document.hidden && !offscreen) draw(clock()); }) : null;
    const intersection = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => { offscreen = !entries[0].isIntersecting; visibility(); }) : null;
    intersection?.observe(canvas);
    resize?.observe(canvas); document.addEventListener('visibilitychange', visibility); media.addEventListener?.('change', motionChange);
    sync(); draw(clock()); visibility();
    function destroy() { if (disposed) return; const now = clock(); draw(now); const shift = performance.now() - (pausedAt ?? now); for (const p of positions.values()) p.changed += shift; disposed = true; cancelAnimationFrame(raf); raf = 0; resize?.disconnect(); intersection?.disconnect(); document.removeEventListener('visibilitychange', visibility); media.removeEventListener?.('change', motionChange);if(raceStyled){canvas.style.aspectRatio=originalAspect;canvas.style.height=originalHeight;canvas.style.maxHeight=originalMaxHeight;} if (!roomPose) positions.clear(); canvas.dataset.artDestroyed = 'true'; }
    return {
      update(next) { if (disposed) return; state = { ...state, ...next }; sync(); draw(clock()); schedule(); },
      renderAt(ms) { if (disposed) return; manualTime = Math.max(0, Number(ms) || 0); cancelAnimationFrame(raf); raf = 0; draw(start + manualTime); },
      play() { if (disposed) return; const now = performance.now(), shift = now - clock(); for (const p of positions.values()) p.changed += shift; if (pausedAt !== null) pausedAt += shift; manualTime = null; start = now; schedule(); },
      ready() { return Promise.all([...(state.players || []).map(p => imageFor(codeFor(p), base).promise),raceScene?.promise]); },
      destroy,
      getState() { return { disposed, animationScheduled: !!raf, reducedMotion: reduced(), offscreen, motionKey, mode: state.mode, mapId: mapNumber(state.mapId),raceScene:raceScene?{themeKey:raceScene.themeKey,themeName:raceScene.themeName,assetURL:raceScene.assetURL,assetReady:raceScene.assetReady,assetFailed:raceScene.assetFailed,logicalWidth:1000,logicalHeight:raceScene.logicalHeight,actorSize:raceScene.actorSize,labelFontSize:raceScene.labelFontSize,lanes:raceScene.lanes.map(({player,...lane})=>lane),counts:raceScene.counts,stats:global.RaceScenes.getStats()}:null, positions: [...positions].map(([id, p]) => ({ id, value: p.value, target: p.to, moving: p.moving })) }; }
    };
  }
  const api = { mount, clearMotion, maps, laneOrder, speciesFor, codeFor, podiumMarkup, mountPodium, captureTarget, captureFacing, confettiMarkup, mountConfetti, confettiParticles, confettiFrame };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.GamesArt = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
