/* Voi Canvas runtime: WebP sheets load only when this mascot is visible. */
'use strict';
const ArenaVoi = (() => {
    let ready, renderer, actors = [], effects = [], raf = 0, generation = 0, timers = [], poseAspect = 1;
    const later = (fn, ms) => { const id=setTimeout(fn,ms); timers.push(id); return id; };
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const clock = () => performance.now() / 1000;
    const stateForMood = mood => ({attack:'attack',hit:'hurt',win:'victory',lose:'defeat',ultimate:'ultimate'}[mood] || 'idle');

    function loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => reject(new Error('Không tải được hình Voi. Em hãy tải lại trang.'));
            img.src = new URL(src, document.baseURI).href;
        });
    }
    function load() {
        if (!ready) ready = Promise.all([
            loadImage('arena-art/voi-poses.webp'), loadImage('arena-art/voi-reactions.webp'),
        ]).then(([posesImage, reactionsImage]) => {
            const frames = window.VOI_FRAMES;
            poseAspect = Math.max(...[frames.poses,frames.reactions].map(sheet =>
                Math.max(...sheet.map(frame=>frame.width)) / Math.max(...sheet.map(frame=>frame.height))));
            renderer = VoiRenderer.create({posesImage, reactionsImage,
                posesFrames:frames.poses, reactionsFrames:frames.reactions});
            return renderer;
        }).catch(error => { ready = null; throw error; });
        return ready;
    }
    function resize(canvas) {
        const box = canvas.getBoundingClientRect(), ratio = Math.min(window.devicePixelRatio || 1, 2);
        const width = Math.max(1, Math.round(box.width * ratio)), height = Math.max(1, Math.round(box.height * ratio));
        if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
        return {width, height};
    }
    function actorFor(node) {
        const canvas = node?.matches?.('canvas[data-voi]') ? node : node?.querySelector('canvas[data-voi]');
        return actors.find(actor => actor.canvas === canvas);
    }
    function setState(actor, state, delay = 0) {
        if (!actor) return;
        actor.state = state; actor.start = clock() + delay; actor.hold = ['defeat', 'victory'].includes(state);
    }
    function drawActor(actor, now) {
        const canvas = actor.canvas;
        if (!canvas.isConnected) return false;
        const {width, height} = resize(canvas), ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, width, height);
        const duration = renderer.duration(actor.state), elapsed = Math.max(0, now - actor.start);
        let state = actor.state, time = reduced() ? duration : Math.min(elapsed, duration);
        if (now < actor.start) { state = 'idle'; time = 0; }
        // Fit wide ears and the extended trunk, including the motion and rotation margin.
        const fittedHeight = Math.min(height*.88, width*.92/(poseAspect+.28));
        actor.trunkTip=renderer.drawActor(ctx, {state, time, x:width/2, feet:height*.96, height:fittedHeight, facing:1})?.trunkTip;
        if (elapsed >= duration && !actor.hold && actor.state !== 'idle') { actor.state = 'idle'; actor.start = now; }
        return !reduced() && state !== 'idle' && elapsed < duration || now < actor.start;
    }
    function pointWithin(canvas, stage, lift = 0) {
        const a = canvas.getBoundingClientRect(), b = stage.getBoundingClientRect();
        return {x:(a.left+a.width/2-b.left)*stage.width/b.width,
            y:(a.top+a.height*.5-b.top-lift)*stage.height/b.height};
    }
    function clearEffect(effect) {
        effect.victimTurn?.style.removeProperty('translate');
        effect.canvas.remove();
    }
    function trunkPointWithin(source, stage) {
        const tip=actorFor(source)?.trunkTip;
        if(!tip)return pointWithin(source,stage);
        const a=source.getBoundingClientRect(), b=stage.getBoundingClientRect();
        const turn=source.closest('.pet-turn');
        const matrix=turn ? getComputedStyle(turn).transform : 'none';
        const mirrored=matrix!=='none' && new DOMMatrixReadOnly(matrix).a<0;
        return {x:(a.left+a.width*(mirrored?1-tip.x/source.width:tip.x/source.width)-b.left)*stage.width/b.width,
            y:(a.top+a.height*tip.y/source.height-b.top)*stage.height/b.height};
    }
    function drawEffect(effect, now) {
        if (!effect.source.isConnected || !effect.victim.isConnected || !effect.canvas.isConnected) { clearEffect(effect); return false; }
        const duration = renderer.duration(effect.state), elapsed = Math.max(0, now-effect.start);
        if (elapsed >= duration) { clearEffect(effect); return false; }
        const canvas = effect.canvas, ctx = canvas.getContext('2d');
        resize(canvas); ctx.clearRect(0,0,canvas.width,canvas.height);
        if (reduced()) { clearEffect(effect); return false; }
        // Read the unlifted target so the bubble and character move together.
        effect.victimTurn?.style.removeProperty('translate');
        const from = trunkPointWithin(effect.source,canvas), to = pointWithin(effect.victim,canvas);
        const targetBox=effect.victim.getBoundingClientRect(), stageBox=canvas.getBoundingClientRect();
        const targetHeightCSS=targetBox.height, scale=canvas.height/stageBox.height;
        const targetHeight=targetHeightCSS*scale;
        // Keep the complete opposing sprite inside the stage, including at peak lift.
        const safeCSS=Math.min(8,stageBox.height*.02);
        const maxLiftCSS=Math.max(0,targetBox.top-stageBox.top-safeCSS);
        const peakLiftCSS=Math.min(targetHeightCSS*.28,maxLiftCSS), peakLift=peakLiftCSS*scale;
        const safe=safeCSS*scale;
        const bubbleRadius=Math.max(1,Math.min(targetHeight*.55,to.x-safe,
            canvas.width-to.x-safe,to.y-peakLift-safe,canvas.height-to.y-safe));
        const sample = renderer.effectSample?.(effect.state,elapsed);
        const lift = sample?.bubbleLift || 0;
        if (effect.victimTurn && lift) effect.victimTurn.style.translate = `0 ${-lift*peakLiftCSS}px`;
        renderer.drawEffect(ctx,{state:effect.state,time:elapsed,from,to,targetHeight,
            maxLift:peakLift,bubbleRadius});
        return true;
    }
    function frame() {
        raf = 0;
        if (document.hidden || !renderer) return;
        const now = clock(); let active = false;
        for (const actor of actors) active = drawActor(actor,now) || active;
        effects = effects.filter(effect => drawEffect(effect,now));
        if (active || effects.length) raf = requestAnimationFrame(frame);
    }
    function wake() { if (!raf && !document.hidden) raf = requestAnimationFrame(frame); }
    function stop() {
        generation++;
        cancelAnimationFrame(raf); raf = 0;
        timers.forEach(clearTimeout); timers = [];
        effects.forEach(clearEffect); effects = []; actors = [];
    }
    async function mount(root = document) {
        stop();
        const token = generation, canvases = [...root.querySelectorAll('canvas[data-voi]')];
        if (!canvases.length) return;
        try {
            await load();
            if (token !== generation) return;
            actors = canvases.filter(canvas => canvas.isConnected).map(canvas => ({canvas,
                state:stateForMood(canvas.closest('.battle-pet')?.dataset.mood), start:clock(),
                hold:['win','lose'].includes(canvas.closest('.battle-pet')?.dataset.mood)}));
            for (const actor of actors) actor.canvas.dataset.voiReady = 'true';
            wake();
        } catch (error) {
            if (token !== generation) return;
            for (const canvas of canvases) { const text = document.createElement('span'); text.className='voi-load-error'; text.textContent='Voi'; canvas.replaceWith(text); }
            console.error(error.message);
        }
    }
    function play(source, victim, {ultimate = false, fatal = false} = {}) {
        const attacker = actorFor(source), defender = actorFor(victim);
        setState(attacker, ultimate ? 'ultimate' : 'attack');
        setState(defender, fatal ? 'defeat' : 'hurt', ultimate ? 1.75 : .35);
        if (attacker && !reduced()) {
            const stage = source.closest('.battle-stage');
            const target = victim?.querySelector('.battle-pet');
            if (stage && target) {
                const canvas = document.createElement('canvas');
                canvas.className='voi-arena-effect'; canvas.setAttribute('aria-hidden','true'); stage.append(canvas);
                effects.push({canvas,source:attacker.canvas,victim:target,
                    victimTurn:target.closest('.pet-turn'),state:ultimate?'ultimate':'attack',start:clock()});
            }
        }
        wake();
    }
    function animate(target, attacker, final) {
        const source=document.querySelector(attacker), victim=document.querySelector(target);
        const sourcePet=source?.querySelector('.battle-pet'), victimPet=victim?.querySelector('.battle-pet');
        if (!sourcePet?.classList.contains('voi')) {
            return false;
        }
        victim?.classList.remove('taking-hit'); source?.classList.remove('attacking');
        if(victim)void victim.offsetWidth;
        sourcePet.dataset.mood=final?'ultimate':'attack'; source.classList.add('attacking');
        const announcement=document.querySelector('#spell-announcement');
        if(announcement)announcement.textContent=final?'':'✦ Vòi nước';
        if(final)later(()=>{if(announcement?.isConnected)announcement.textContent='✦ VÒI RỒNG CẦU VỒNG';},650);
        const hit=()=>{
            if(!victim?.isConnected||!victimPet)return;
            victim.dataset.spell='water'; victimPet.dataset.mood=final?'lose':'hit'; victim.classList.add('taking-hit');
            if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victimPet,final?'lose':'hit');
        };
        later(hit,final?1750:350);
        play(source,victim,{ultimate:final,fatal:final});
        later(()=>{
            victim?.classList.remove('taking-hit'); source?.classList.remove('attacking');
            if(sourcePet.isConnected)sourcePet.dataset.mood='idle';
            if(victimPet?.isConnected&&!final){victimPet.dataset.mood='idle';if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victimPet,'idle');}
            if(announcement?.isConnected)announcement.textContent='';
        },final?3000:1600);
        return true;
    }
    function notifyVictim(target, attacker, final) {
        const source=document.querySelector(attacker), victim=document.querySelector(target);
        if(source?.querySelector('.battle-pet.voi'))return;
        setState(actorFor(victim),final?'defeat':'hurt',final?1.75:0);
        wake();
    }
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) { cancelAnimationFrame(raf); raf=0; }
        else wake();
    });
    window.addEventListener('resize',wake);
    return {mount,play,animate,notifyVictim,stop};
})();
