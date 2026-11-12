/* Bướm: lazy WebP atlas + finite Canvas playback; combat state stays in Learning. */
window.ButterflyAnimation = (() => {
    'use strict';
    const jobs = new Map(), mounted = new Set(), reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let atlas, loading, frame = 0, observer, generation = 0;
    const durations = {attack:1.1, hit:.75, lose:1.8, win:1.1, ultimate:3};
    function ready() {
        if (!loading) loading = new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => { atlas = image; resolve(image); };
            image.onerror = () => { loading = null; reject(Error('Không tải được ảnh Bướm')); };
            image.src = 'arena-art/butterfly-poses.webp';
        });
        return loading;
    }
    function canvasFor(node) {
        let canvas = node.querySelector('.butterfly-pose-canvas');
        if (!canvas) {
            canvas = document.createElement('canvas'); canvas.width = canvas.height = 384;
            canvas.className = 'butterfly-pose-canvas'; canvas.setAttribute('aria-hidden','true'); node.append(canvas);
        }
        return canvas;
    }
    function draw(node, action, seconds) {
        const ctx = canvasFor(node).getContext('2d'), duration = durations[action] || 1;
        const u = Math.max(0, Math.min(1, seconds / duration));
        let pose = 0, x = 192, y = 194, rotation = 0;
        if (action === 'attack') { pose = 4 + Math.min(3, Math.floor(u * 4)); x += Math.sin(u*Math.PI)*27; y -= Math.sin(u*Math.PI)*20; rotation = Math.sin(u*Math.PI)*.12; }
        if (action === 'hit') { pose = u < .45 ? 12 : 13; x += Math.sin(u*24)*(1-u)*15; rotation = -.16*Math.sin(u*Math.PI); }
        if (action === 'lose') { pose = u < .5 ? 14 : 15; y += 18*u; }
        if (action === 'win') { pose = 10 + (u > .5 ? 1 : 0); y -= Math.sin(u*Math.PI)*18; }
        ctx.clearRect(0,0,384,384);
        window.ButterflyRenderer.pose(ctx,atlas,pose,x,y,370,rotation);
        node.classList.add('butterfly-ready');
    }
    function dispose(job) {
        if (job.overlay) {
            job.overlay.remove(); job.stage?.classList.remove('butterfly-ultimate-active');
            job.node.classList.remove('butterfly-in-ultimate');
            if (job.announcement?.dataset.butterfly === 'true') {
                job.announcement.textContent = ''; delete job.announcement.dataset.butterfly;
            }
        }
    }
    function overlayFor(node) {
        const stage = node.closest('#battle-stage'); if (!stage) return {};
        const overlay = document.createElement('canvas'); overlay.width = overlay.height = 768;
        overlay.className = 'butterfly-ultimate-canvas'; overlay.setAttribute('aria-hidden','true');
        stage.append(overlay); stage.classList.add('butterfly-ultimate-active'); node.classList.add('butterfly-in-ultimate');
        return {overlay,stage,announcement:stage.querySelector('#spell-announcement')};
    }
    function drawUltimate(job,t) {
        const ctx = job.overlay.getContext('2d'), box = job.stage.getBoundingClientRect();
        const rect = job.node.getBoundingClientRect();
        const foe = job.stage.querySelector(job.node.closest('.fighter').id === 'fighter-me' ? '#fighter-opponent .battle-pet' : '#fighter-me .battle-pet');
        const point = r => ({x:(r.x-box.x+r.width/2)/box.width*768, y:(r.y-box.y+r.height/2)/box.height*768, size:r.width/box.width*768});
        const source = point(rect), target = foe ? point(foe.getBoundingClientRect()) : {x:600,y:220,size:170};
        ctx.clearRect(0,0,768,768);
        window.ButterflyRenderer.effects(ctx,t,source,target,{title:false,lowQuality:matchMedia('(max-width: 600px)').matches});
        const pose = t < .95 ? Math.min(3,Math.floor(t/.24)) : t < 1.9 ? (t < 1.5 ? 8 : 9) : (t < 2.4 ? 10 : 11);
        window.ButterflyRenderer.pose(ctx,atlas,pose,source.x,source.y-Math.sin(Math.min(1,t/3)*Math.PI)*20,source.size,0,source.x>target.x);
        if (job.announcement) {
            job.announcement.dataset.butterfly = 'true';
            job.announcement.textContent = t >= .65 && t < 2.7 ? 'Vũ Điệu Ngàn Cánh' : '';
        }
    }
    function tick(now) {
        frame = 0; if (document.hidden) return;
        for (const [node,job] of jobs) {
            if (!node.isConnected) { dispose(job); jobs.delete(node); continue; }
            const t = Math.min(job.duration,(now-job.started)/1000);
            if (job.overlay) drawUltimate(job,t); else draw(node,job.action,t);
            if (t >= job.duration) {
                dispose(job); jobs.delete(node);
                if (job.action === 'ultimate') { node.dataset.mood = 'win'; draw(node,'win',1.1); }
                else if (!['lose','win'].includes(job.action)) { node.dataset.mood = 'idle'; draw(node,'idle',0); }
            }
        }
        if (jobs.size) frame = requestAnimationFrame(tick);
    }
    function play(node,action='idle') {
        if (!node?.classList.contains('butterfly')) return false;
        if (!['idle','attack','hit','lose','win','ultimate'].includes(action)) action = 'idle';
        if (node.dataset.mood !== action) node.dataset.mood = action;
        const version = generation;
        ready().then(() => {
            if (!node.isConnected || version !== generation || node.dataset.mood !== action) return;
            if (jobs.has(node)) { dispose(jobs.get(node)); jobs.delete(node); }
            const duration = durations[action] || 0;
            if (reduced.matches || action === 'idle') { draw(node,action === 'ultimate' ? 'win' : action,duration); return; }
            const job = {node,action,duration,started:performance.now(),...(action === 'ultimate' ? overlayFor(node) : {})};
            jobs.set(node,job); if (job.overlay) drawUltimate(job,0); else draw(node,action,0);
            if (!frame && !document.hidden) frame = requestAnimationFrame(tick);
        }).catch(() => { node.classList.remove('butterfly-ready'); });
        return true;
    }
    function mount(root=document) {
        for (const node of root.querySelectorAll('.battle-pet.butterfly')) {
            if (!mounted.has(node)) { mounted.add(node); play(node,node.dataset.mood || 'idle'); }
        }
        if (!observer && !(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed)) {
            observer = new MutationObserver(records => {
                for (const record of records) if (record.type === 'attributes' && record.target.matches('.battle-pet.butterfly')) {
                    const node = record.target, action = node.dataset.mood || 'idle';
                    if (jobs.get(node)?.action !== action) play(node,action);
                }
                if (records.some(r=>r.type==='childList')) {
                    for (const node of mounted) if (!node.isConnected) { if(jobs.has(node))dispose(jobs.get(node)); jobs.delete(node); mounted.delete(node); }
                    mount(document);
                }
            });
            observer.observe(document.querySelector('#app') || document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});
        }
    }
    function hit({source,victim,final}) {
        const node = source?.querySelector('.battle-pet.butterfly'); if (!node) return false;
        const victimPet = victim?.querySelector('.battle-pet'), version = generation;
        source.dataset.spell = 'butterfly';
        play(node, final ? 'ultimate' : 'attack');
        const impact = () => {
            if (version !== generation || !victim?.isConnected || !victimPet) return;
            victim.dataset.spell = 'butterfly'; victim.classList.add('taking-hit');
            victimPet.dataset.mood = final ? 'lose' : 'hit';
            play(victimPet,final?'lose':'hit');
            if (typeof RabbitAnimation !== 'undefined') RabbitAnimation.play(victimPet,final?'lose':'hit');
            window.EagleAnimation?.play(victimPet,final?'lose':'hit');
        };
        if (final && !reduced.matches) setTimeout(impact,1750); else impact();
        setTimeout(()=>{if(version===generation)victim?.classList.remove('taking-hit');},final?3000:1100);
        return true;
    }
    function destroy() {
        generation++; cancelAnimationFrame(frame); frame = 0; observer?.disconnect(); observer = null;
        for (const job of jobs.values()) dispose(job); jobs.clear(); mounted.clear();
    }
    document.addEventListener('visibilitychange',()=>{
        if(document.hidden) { cancelAnimationFrame(frame); frame=0; }
        else if(jobs.size && !frame) frame=requestAnimationFrame(tick);
    });
    reduced.addEventListener('change',()=>{if(reduced.matches)for(const [node,job] of [...jobs])play(node,job.action);});
    return {ready,mount,play,hit,destroy,debug:()=>({active:jobs.size,frame,mounted:mounted.size})};
})();
