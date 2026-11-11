'use strict';

// Sư tử uses WebP pose sheets. Only finite actions request animation frames;
// the character remains still while the pupil reads the next maths question.
const ArenaLion = (() => {
    const urls = {combat:'arena-art/lion-combat.webp',ultimate:'arena-art/lion-ultimate.webp'};
    const images = new Map(), pets = new Map(), actions = new Map();
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0, stage = null, observer = null, moodObserver = null, flash = null;
    const clock = () => performance.now();
    const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,n));
    const ease = n => 1-Math.pow(1-clamp(n),3);

    function sheet(kind) {
        if (images.has(kind)) return images.get(kind).promise;
        const img = new Image(), entry = {img,ready:false};
        entry.promise = new Promise(resolve => {
            img.onload = () => { entry.ready = true; resolve(img); redraw(); };
            img.onerror = () => resolve(null);
        });
        images.set(kind,entry);
        img.src = new URL(urls[kind],document.baseURI).href;
        return entry.promise;
    }

    function fitCanvas(canvas) {
        const bounds = canvas.getBoundingClientRect();
        const ratio = Math.min(devicePixelRatio || 1,2);
        const w = Math.max(1,Math.round(bounds.width*ratio));
        const h = Math.max(1,Math.round(bounds.height*ratio));
        if (canvas.width !== w || canvas.height !== h) { canvas.width=w;canvas.height=h; }
        return {w,h};
    }

    function pose(ctx,img,index,w,h) {
        const col = index%4, row = Math.floor(index/4);
        const x = Math.round(col*img.naturalWidth/4), y = Math.round(row*img.naturalHeight/4);
        const sw = Math.round((col+1)*img.naturalWidth/4)-x;
        const sh = Math.round((row+1)*img.naturalHeight/4)-y;
        const scale = Math.min(w/sw,h/sh);
        const dw = sw*scale, dh = sh*scale;
        ctx.drawImage(img,x,y,sw,sh,(w-dw)/2,(h-dh)/2,dw,dh);
    }

    function drawPet(record,now) {
        if (!record.node.isConnected) { pets.delete(record.node);actions.delete(record.node);return; }
        const action = actions.get(record.node);
        const elapsed = action ? clamp((now-action.start)/action.duration) : 1;
        let kind = 'combat', index=12;
        if (action && now>=action.start) {
            const p = reduced.matches ? 1 : elapsed;
            if (action.kind === 'ultimate') {
                kind='ultimate';
                const seconds = p*3;
                index = seconds<.65 ? Math.min(3,Math.floor(seconds/.65*4))
                    : seconds<.95 ? 4+Math.min(3,Math.floor((seconds-.65)/.3*4))
                    : seconds<1.9 ? 8+Math.min(3,Math.floor((seconds-.95)/.95*4))
                    : 12+Math.min(3,Math.floor((seconds-1.9)/1.1*4));
            } else if (action.kind === 'win') { kind='ultimate';index=12+Math.min(3,Math.floor(p*4)); }
            else {
                const offset = {attack:0,hit:4,lose:8,idle:12}[action.kind] ?? 12;
                index=offset+Math.min(3,Math.floor(p*4));
            }
            if (elapsed>=1 && !action.hold) {
                actions.delete(record.node);
                if(record.node.dataset.mood!=='idle')record.node.dataset.mood='idle';
                index=12;kind='combat';
            }
        }
        const asset = images.get(kind);
        if (!asset?.ready) return;
        const {w,h} = fitCanvas(record.canvas),ctx=record.ctx;
        ctx.clearRect(0,0,w,h);
        ctx.save();
        if (action?.kind==='attack' && elapsed<1 && !reduced.matches) ctx.translate(Math.sin(elapsed*Math.PI)*w*.10,0);
        if (action?.kind==='hit' && elapsed<1 && !reduced.matches) ctx.translate(Math.sin(elapsed*Math.PI*6)*(1-elapsed)*w*.04,0);
        pose(ctx,asset.img,index,w,h);
        ctx.restore();record.node.classList.add('lion-ready');
    }

    function crown(ctx,x,y,size,opacity=1) {
        ctx.save();ctx.translate(x,y);ctx.globalAlpha=opacity;
        ctx.fillStyle='#ffd06a';ctx.strokeStyle='#ab6725';ctx.lineWidth=size*.045;
        ctx.beginPath();ctx.moveTo(-size*.48,size*.19);ctx.lineTo(-size*.58,-size*.35);
        ctx.lineTo(-size*.22,-size*.13);ctx.lineTo(0,-size*.52);ctx.lineTo(size*.22,-size*.13);
        ctx.lineTo(size*.58,-size*.35);ctx.lineTo(size*.48,size*.19);ctx.closePath();ctx.fill();ctx.stroke();
        ctx.fillStyle='#fff3bc';ctx.fillRect(-size*.45,size*.16,size*.9,size*.16);
        ctx.fillStyle='#ff9c65';ctx.beginPath();ctx.arc(0,0,size*.065,0,Math.PI*2);ctx.fill();ctx.restore();
    }

    function point(node,canvas) {
        const box=node.getBoundingClientRect(),area=canvas.getBoundingClientRect();
        return {x:(box.left+box.width*.5-area.left)/area.width*canvas.width,
            y:(box.top+box.height*.52-area.top)/area.height*canvas.height};
    }

    function drawFX(now) {
        if (!stage) return;
        const {canvas,ctx}=stage,{w,h}=fitCanvas(canvas);ctx.clearRect(0,0,w,h);
        if (!flash || !flash.source.isConnected || !flash.target.isConnected) return;
        const t=(now-flash.start)/1000;
        const announcement=document.querySelector('#spell-announcement');
        if (t>=3) { if(announcement?.dataset.lion==='true'){announcement.textContent='';delete announcement.dataset.lion;}flash=null;return; }
        if (announcement) {
            announcement.dataset.lion='true';
            announcement.textContent=t>=.65?'✦ TIẾNG GẦM SƯ VƯƠNG':'';
        }
        const a=point(flash.source,canvas),b=point(flash.target,canvas);
        if (reduced.matches) { crown(ctx,b.x,b.y-h*.08,w*.13,.8);return; }
        // The mane shines before the roar. The waves follow the diagonal
        // between the fighters rather than assuming a particular screen size.
        if (t<1.9) {
            const glow=ctx.createRadialGradient(a.x,a.y,0,a.x,a.y,w*.22);
            glow.addColorStop(0,'#ffe7a452');glow.addColorStop(1,'#ffe7a400');
            ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
        }
        for (let i=0;i<4;i++) {
            const p=(t-.95-i*.13)/.8;
            if (p<0 || p>1) continue;
            const x=a.x+(b.x-a.x)*ease(p),y=a.y+(b.y-a.y)*ease(p);
            ctx.save();ctx.translate(x,y);ctx.rotate(Math.atan2(b.y-a.y,b.x-a.x));
            ctx.globalAlpha=Math.sin(p*Math.PI)*.9;ctx.strokeStyle=i===3?'#fff0a3':'#ffc14e';
            ctx.lineWidth=w*.009;ctx.shadowColor='#ffe491';ctx.shadowBlur=w*.018;
            ctx.beginPath();ctx.ellipse(0,0,w*(.025+p*.035),w*(.055+p*.055),0,0,Math.PI*2);ctx.stroke();ctx.restore();
        }
        if (t>=1.45 && t<2.1) {
            const p=clamp((t-1.45)/.3),fade=t<1.9?1:1-(t-1.9)/.2;
            crown(ctx,a.x+(b.x-a.x)*ease(p),a.y+(b.y-a.y)*ease(p)-h*.04,w*(.09+.1*p),fade);
        }
        if (t>=1.75 && t<2.6) {
            const p=(t-1.75)/.85;
            for(let i=0;i<16;i++) {
                const angle=i*Math.PI*2/16,rad=w*(.04+.19*p);
                ctx.globalAlpha=(1-p)*.9;ctx.fillStyle=i%2?'#fff5b8':'#ffbc58';
                const x=b.x+Math.cos(angle)*rad,y=b.y+Math.sin(angle)*rad;
                ctx.save();ctx.translate(x,y);ctx.rotate(angle+p);ctx.fillRect(-w*.006,-w*.014,w*.012,w*.028);ctx.restore();
            }
            ctx.globalAlpha=1;
        }
    }

    function redraw() {
        const now=clock();for(const record of pets.values())drawPet(record,now);drawFX(now);
        if (!document.hidden && !reduced.matches && !frame && (flash || [...actions.values()].some(a=>now<a.start+a.duration))) frame=requestAnimationFrame(tick);
    }
    function tick() { frame=0;redraw(); }

    function play(node,kind,duration,hold=false,delay=0) {
        if(!pets.has(node))return;
        if(kind==='idle') {
            actions.delete(node);
            if(node.dataset.mood!=='idle')node.dataset.mood='idle';
            sheet('combat');redraw();return;
        }
        const start=clock()+delay;
        actions.set(node,{kind,start,duration,hold});
        if(node.dataset.mood!==kind)node.dataset.mood=kind;
        sheet(kind==='ultimate'||kind==='win'?'ultimate':'combat');
        if(delay)later(redraw,delay);redraw();
    }

    function mount() {
        destroy();
        for (const node of document.querySelectorAll('.battle-pet.lion')) {
            const canvas=document.createElement('canvas');canvas.className='lion-pose-canvas';canvas.setAttribute('aria-hidden','true');
            node.append(canvas);pets.set(node,{node,canvas,ctx:canvas.getContext('2d')});
            const mood=node.dataset.mood;
            if(mood==='lose')play(node,'lose',2200,true);
            if(mood==='win')play(node,'win',1100,true);
        }
        if (!pets.size) return;
        sheet('combat');
        const arena=document.querySelector('#battle-stage');
        if (arena) {
            const canvas=document.createElement('canvas');canvas.className='lion-ultimate-canvas';canvas.setAttribute('aria-hidden','true');arena.append(canvas);
            stage={canvas,ctx:canvas.getContext('2d')};sheet('ultimate');
        }
        observer=new ResizeObserver(redraw);for(const record of pets.values())observer.observe(record.node);
        // Other mascots set data-mood at their own impact timestamp. Observe
        // that signal so Sư tử reacts to their hit at the correct moment too.
        moodObserver=new MutationObserver(changes=>{
            for(const change of changes){
                const node=change.target,mood=node.dataset.mood;
                if(actions.get(node)?.kind===mood)continue;
                if(mood==='idle'){actions.delete(node);redraw();continue;}
                if(['idle','attack','hit','lose','win','ultimate'].includes(mood))
                    play(node,mood,mood==='ultimate'?3000:mood==='lose'?2200:mood==='win'?1100:650,mood==='lose'||mood==='win');
            }
        });
        for(const node of pets.keys())moodObserver.observe(node,{attributes:true,attributeFilter:['data-mood']});
        if(stage)observer.observe(stage.canvas);redraw();
    }

    function animate(targetSelector,sourceSelector,final) {
        const target=document.querySelector(targetSelector),source=document.querySelector(sourceSelector);
        const victim=target?.querySelector('.battle-pet'),attacker=source?.querySelector('.battle-pet');
        const lion=attacker?.classList.contains('lion');
        if (!lion) return false;
        play(attacker,final?'ultimate':'attack',final?3000:650,Boolean(final));
        if (final && stage && victim) {
            flash={start:clock(),source:attacker,target:victim};redraw();
        } else {
            const announcement=document.querySelector('#spell-announcement');
            if(announcement){announcement.textContent='✦ Cú vồ Sư tử';announcement.dataset.lion='true';}
        }
        // CSS damage feedback is kept separate from the rendered character.
        // No combat state, answer deadline or damage value is changed here.
        const impact=()=>{
            if(target?.isConnected){target.classList.add('taking-hit');target.dataset.spell='lion';}
            if(victim?.isConnected){
                const mood=final?'lose':'hit';victim.dataset.mood=mood;
                if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victim,mood);
                const bear=victim.querySelector('canvas[data-bear]');
                if(bear&&typeof BearAnimation!=='undefined')BearAnimation.play(bear,final?'defeat':'hit');
                if(typeof TigerAnimation!=='undefined')TigerAnimation.play(victim,final?'defeat':'hurt');
            }
        };
        if(final)later(impact,1750);else impact();
        const cleanupAt=final?3000:700;
        later(()=>{
            target?.classList.remove('taking-hit');
            if(victim?.isConnected&&!victim.classList.contains('lion'))victim.dataset.mood=final?'lose':'idle';
            const announcement=document.querySelector('#spell-announcement');
            if(announcement?.dataset.lion==='true'){announcement.textContent='';delete announcement.dataset.lion;}
            redraw();
        },cleanupAt);
        return true;
    }

    const timers=new Set();
    function later(callback,delay) {
        const timer=setTimeout(()=>{timers.delete(timer);callback();},delay);timers.add(timer);
    }
    function destroy() {
        if(frame)cancelAnimationFrame(frame);frame=0;observer?.disconnect();observer=null;moodObserver?.disconnect();moodObserver=null;
        for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const record of pets.values()){record.canvas.remove();record.node.classList.remove('lion-ready');}
        pets.clear();actions.clear();stage?.canvas.remove();stage=null;flash=null;
        const announcement=document.querySelector('#spell-announcement');
        if(announcement?.dataset.lion==='true'){announcement.textContent='';delete announcement.dataset.lion;}
    }

    document.addEventListener('visibilitychange',()=>{if(document.hidden){if(frame)cancelAnimationFrame(frame);frame=0;}else redraw();});
    reduced.addEventListener('change',()=>{if(frame)cancelAnimationFrame(frame);frame=0;redraw();});
    window.addEventListener('pagehide',destroy);
    const inspect=()=>({running:Boolean(frame),effects:Boolean(flash),pets:[...pets.keys()].map(node=>({mood:node.dataset.mood,action:actions.get(node)?.kind||'idle'}))});
    return {mount,animate,destroy,inspect};
})();
