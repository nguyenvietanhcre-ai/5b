'use strict';

// The game only loads the Hổ sheets/renderer when a Hổ is present. Every motion
// has a finite lifetime; the WebP sheets are cached for the next round.
const TigerAnimation = (() => {
    const base = new URL('arena-art/ho-v1/', document.baseURI);
    const players = new Map();
    const overlays = new Map();
    const timers = new Set();
    let prepared;
    let observer;
    const later = (callback, delay) => {
        const timer = setTimeout(() => { timers.delete(timer); callback(); }, delay);
        timers.add(timer);
        return timer;
    };
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const image = file => new Promise((resolve, reject) => {
        const asset = new Image();
        asset.onload = () => resolve(asset);
        asset.onerror = () => reject(new Error('Không tải được ảnh Hổ.'));
        asset.src = new URL(file, base).href;
    });
    function prepare() {
        if (!prepared) prepared = Promise.all([
            image('poses.webp'), image('reactions.webp'),
            fetch(new URL('poses.json', base)).then(response => {
                if (!response.ok) throw new Error('Không tải được tư thế Hổ.');
                return response.json();
            }),
            fetch(new URL('reactions.json', base)).then(response => {
                if (!response.ok) throw new Error('Không tải được biểu cảm Hổ.');
                return response.json();
            }),
            new Promise((resolve, reject) => {
                if (window.TigerAnimationRenderer) { resolve(); return; }
                const script = document.createElement('script');
                script.src = new URL('tiger-renderer.js', base).href;
                script.onload = resolve;
                script.onerror = () => { script.remove(); reject(new Error('Không tải được chuyển động Hổ.')); };
                document.head.append(script);
            }),
        ]).then(([actor, reactions, poses, reactionPoses]) => ({actor, reactions, poses, reactionPoses})).catch(error => {
            prepared = null;
            throw error;
        });
        return prepared;
    }
    function stop(record) {
        if (!record) return;
        record.cancelled = true;
        cancelAnimationFrame(record.frame);
    }
    function play(pet, mode = 'idle') {
        if (!pet?.classList.contains('tiger')) return false;
        stop(players.get(pet));
        let canvas = pet.querySelector('.tiger-canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.className = 'tiger-canvas';
            canvas.width = canvas.height = 512;
            canvas.setAttribute('aria-hidden', 'true');
            pet.append(canvas);
        }
        const record = {mode, frame:0, cancelled:false};
        players.set(pet, record);
        const mood = mode === 'hurt' ? 'hit' : mode === 'defeat' ? 'lose' : mode === 'victory' ? 'win' : mode;
        if (pet.dataset.mood !== mood) pet.dataset.mood = mood;
        prepare().then(assets => {
            if (record.cancelled || !pet.isConnected) return;
            const renderer = window.TigerAnimationRenderer;
            const duration = renderer.duration(mode);
            const context = canvas.getContext('2d');
            const start = performance.now();
            pet.classList.add('tiger-ready');
            const draw = now => {
                if (record.cancelled || !pet.isConnected) { stop(record); players.delete(pet); return; }
                const elapsed = reduced() || document.hidden ? duration : Math.min(duration, (now - start) / 1000);
                renderer.render(context, {...assets, mode, time:elapsed, transparent:true, actorOnly:true, facing:'right', reducedMotion:reduced()});
                if (elapsed < duration && !['idle','victory'].includes(mode)) record.frame = requestAnimationFrame(draw);
                else if (mode === 'attack' || mode === 'hurt') {
                    if (reduced() && !document.hidden) later(() => { if (players.get(pet) === record) play(pet, 'idle'); }, duration * 1000);
                    else play(pet, 'idle');
                }
            };
            draw(start);
        }).catch(() => {
            // The static Hổ remains visible if an asset could not be decoded.
            if (!record.cancelled) pet.classList.remove('tiger-ready');
        });
        return true;
    }
    function hydrate(root = document) {
        for (const pet of root.querySelectorAll('.battle-pet.tiger')) {
            const mood = pet.dataset.mood;
            play(pet, mood === 'lose' ? 'defeat' : mood === 'win' ? 'victory' : 'idle');
        }
        for (const [pet, record] of players) if (!pet.isConnected) { stop(record); players.delete(pet); }
        if (!observer && !(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed)) {
            observer = new MutationObserver(changes => {
                for (const {target} of changes) {
                    if (!target.matches?.('.battle-pet.tiger')) continue;
                    const mood = target.dataset.mood;
                    const mode = {hit:'hurt',lose:'defeat',win:'victory'}[mood] || mood;
                    if (['idle','attack','hurt','defeat','victory'].includes(mode) && players.get(target)?.mode !== mode) play(target, mode);
                }
            });
            observer.observe(document.body, {subtree:true, attributes:true, attributeFilter:['data-mood']});
        }
    }
    function finishOverlay(stage, record, settle = true) {
        if (overlays.get(stage) !== record) return;
        stop(record);
        record.canvas?.remove();
        record.source?.classList.remove('tiger-ultimate-hidden');
        stage.classList.remove('tiger-ultimate-playing');
        overlays.delete(stage);
        if (settle && record.source?.isConnected) play(record.source, 'victory');
    }
    function playUltimate(stage, source, target) {
        const pet = source?.querySelector('.battle-pet.tiger');
        if (!stage || !pet) return false;
        const previous = overlays.get(stage);
        if (previous) finishOverlay(stage, previous);
        const record = {source:pet, frame:0, cancelled:false, until:performance.now() + 3000};
        overlays.set(stage, record);
        prepare().then(assets => {
            if (record.cancelled || !stage.isConnected) return;
            const canvas = document.createElement('canvas');
            canvas.className = 'tiger-ultimate-canvas';
            canvas.width = canvas.height = 1280;
            canvas.setAttribute('aria-hidden', 'true');
            stage.append(canvas);
            record.canvas = canvas;
            const box = stage.getBoundingClientRect();
            const actor = pet.getBoundingClientRect();
            const opponent = target?.querySelector('.battle-pet')?.getBoundingClientRect();
            const point = (rect, tiger = false) => ({x:(rect.left + rect.width / 2 - box.left) * 1280 / box.width,
                y:(rect.top + rect.height * (tiger ? 472 / 512 : 1) - box.top) * 1280 / box.height});
            const options = {...assets, mode:'ultimate', transparent:true, actorOnly:false, showVictory:false, sceneHeight:1280,
                facing:source.classList.contains('right') ? 'left' : 'right', start:point(actor, true),
                target:opponent ? point(opponent, target.querySelector('.battle-pet')?.classList.contains('tiger')) : {x:1000,y:390}, actorHeight:actor.height * (370 / 512) * 1280 / box.height,
                targetHeight:opponent ? opponent.height * 1280 / box.height : 260};
            stop(players.get(pet));
            pet.classList.add('tiger-ultimate-hidden');
            stage.classList.add('tiger-ultimate-playing');
            const context = canvas.getContext('2d');
            const started = performance.now();
            // Loading never delays game state or navigation. In a slow first
            // load, render only the remaining part of the presentation.
            const initial = Math.max(0, 3 - (record.until - started) / 1000);
            const draw = now => {
                if (record.cancelled || !stage.isConnected) { finishOverlay(stage, record); return; }
                const elapsed = reduced() || document.hidden ? 3 : Math.min(3, initial + (now - started) / 1000);
                window.TigerAnimationRenderer.render(context, {...options, time:elapsed, reducedMotion:reduced()});
                if (elapsed < 3) record.frame = requestAnimationFrame(draw);
                else finishOverlay(stage, record);
            };
            draw(started);
        }).catch(() => finishOverlay(stage, record));
        return true;
    }
    function remaining() {
        return reduced() ? 0 : Math.max(0, ...[...overlays.values()].map(record => record.until - performance.now()));
    }
    function hit({source, victim, final}) {
        const pet = source?.querySelector('.battle-pet.tiger');
        const stage = source?.closest('#battle-stage');
        if (!pet || !stage) return false;
        const victimPet = victim?.querySelector('.battle-pet');
        const announcement = stage.querySelector('#spell-announcement');
        source.classList.add('attacking');
        victim?.classList.remove('taking-hit');
        if (announcement) announcement.textContent = final ? reduced() ? 'HỔ VỒ SẤM CHỚP' : '' : '✦ Hổ vồ nhanh';
        if (final) {
            pet.dataset.mood = 'ultimate';
            playUltimate(stage, source, victim);
        } else play(pet, 'attack');
        const impact = () => {
            if (!victim?.isConnected || !victimPet) return;
            victim.dataset.spell = 'lightning';
            victimPet.dataset.mood = final ? 'lose' : 'hit';
            victim.classList.add('taking-hit');
            if (victimPet.classList.contains('tiger')) play(victimPet, final ? 'defeat' : 'hurt');
        };
        if (final && !reduced()) later(impact, 1750); else impact();
        later(() => {
            source.classList.remove('attacking');
            victim?.classList.remove('taking-hit');
            if (victimPet?.isConnected && !final) victimPet.dataset.mood = 'idle';
            if (announcement?.isConnected) announcement.textContent = '';
        }, final ? 3000 : 1000);
        return true;
    }
    function cancelAll() {
        observer?.disconnect(); observer = null;
        for (const timer of timers) clearTimeout(timer);
        timers.clear();
        for (const [stage, record] of overlays) finishOverlay(stage, record, false);
        for (const record of players.values()) stop(record);
        players.clear();
    }
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) return;
        for (const [stage, record] of overlays) finishOverlay(stage, record);
        for (const [pet, record] of players) {
            if (['idle','victory'].includes(record.mode)) continue;
            play(pet, record.mode === 'defeat' ? 'defeat' : 'idle');
        }
    });
    window.addEventListener('pagehide', cancelAll);
    return {hydrate, play, playUltimate, remaining, cancelAll, prepare, hit};
})();
