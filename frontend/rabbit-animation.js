/* Thỏ: Canvas runtime. Only the two WebP sheets and frame bounds are loaded. */
const RabbitAnimation = (() => {
    'use strict';
    const sprites = {}, active = new Map(), mounted = new Set(), timers = new Set();
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const clamp = n => Math.max(0, Math.min(1, n));
    const smooth = n => { n = clamp(n); return n * n * (3 - 2 * n); };
    let readyPromise, frame = 0;
    function image(src) {
        return new Promise((resolve, reject) => {
            const img = new Image(); img.onload = () => resolve(img); img.onerror = reject; img.src = src;
        });
    }
    function ready() {
        if (!readyPromise) readyPromise = Promise.all([
            image('arena-art/tho-poses.webp'), image('arena-art/tho-actions.webp'),
            fetch('arena-art/tho-frames.json').then(r => { if (!r.ok) throw Error('Thỏ: thiếu frame bounds'); return r.json(); }),
        ]).then(([ultimate, actions, bounds]) => {
            for (const [key, img] of Object.entries({ultimate, actions})) {
                const spec = bounds[key];
                if (!spec || spec.frames.length !== 16) throw Error('Thỏ: frame bounds không hợp lệ');
                sprites[key] = {image:img, ...spec, maxHeight:Math.max(...spec.frames.map(f => f.height)), maxWidth:Math.max(...spec.frames.map(f => f.width))};
            }
        });
        return readyPromise;
    }
    function star(ctx, x, y, r, alpha=1) {
        ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x,y); ctx.fillStyle='#ffcf7b'; ctx.beginPath();
        for (let i=0;i<10;i++) { const a=i*Math.PI/5-Math.PI/2, d=i%2?r*.43:r; ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d); }
        ctx.closePath(); ctx.fill(); ctx.restore();
    }
    function pose(ctx, sheet, index, x, feet, height, flip=false, rotation=0) {
        const spec=sprites[sheet], f=spec.frames[index], scale=height/spec.maxHeight;
        ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);if(flip)ctx.scale(-1,1);
        ctx.drawImage(spec.image,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);ctx.restore();
    }
    function canvasFor(node) {
        let canvas=node.querySelector('.rabbit-canvas');
        if(!canvas){canvas=document.createElement('canvas');canvas.width=384;canvas.height=384;canvas.className='rabbit-canvas';canvas.setAttribute('aria-hidden','true');node.append(canvas);}
        return canvas;
    }
    function drawPet(node, action, seconds) {
        const ctx=canvasFor(node).getContext('2d');ctx.clearRect(0,0,384,384);
        let sheet='actions',index=0,x=192,feet=365,rotation=0;
        const u=clamp(seconds/(action==='attack'||action==='hit'?1.2:3));
        if(action==='attack'){index=4+Math.min(3,Math.floor(u*4));x+=Math.sin(u*Math.PI)*35;feet-=Math.sin(u*Math.PI)*18;}
        else if(action==='hit'){index=8+Math.min(3,Math.floor(u*4));x+=Math.sin(u*Math.PI*6)*(1-u)*13;rotation=Math.sin(u*Math.PI)*-.08;}
        else if(action==='lose')index=12+Math.min(3,Math.floor(u*4));
        else if(action==='win'){sheet='ultimate';index=12+Math.min(3,Math.floor(u*4));feet-=Math.sin(u*Math.PI)*17;}
        pose(ctx,sheet,index,x,feet,322,false,rotation);
        if(action==='hit'&&u<.8)for(let i=0;i<3;i++)star(ctx,150+i*42,40+Math.sin(u*12+i)*9,9,1-u);
    }
    function ultimateCanvas(node) {
        const stage=node.closest('#battle-stage');if(!stage)return null;
        const canvas=document.createElement('canvas');canvas.width=768;canvas.height=768;canvas.className='rabbit-ultimate-canvas';canvas.setAttribute('aria-hidden','true');stage.append(canvas);
        const box=stage.getBoundingClientRect(), own=node.getBoundingClientRect(), opponent=stage.querySelector(node.closest('.fighter').id==='fighter-me'?'#fighter-opponent .battle-pet':'#fighter-me .battle-pet').getBoundingClientRect();
        const point=rect=>({x:(rect.x-box.x+rect.width/2)/box.width*768,y:(rect.y-box.y+rect.height)/box.height*768,height:rect.height/box.height*768});
        node.classList.add('rabbit-in-ultimate');
        stage.classList.add('rabbit-ultimate-playing');
        return {canvas,stage,start:point(own),target:point(opponent),flip:node.closest('.fighter').classList.contains('right')};
    }
    function drawUltimate(job,t) {
        const {canvas,start:a,target:b,flip}=job.overlay,ctx=canvas.getContext('2d');ctx.clearRect(0,0,768,768);
        const actorHeight=Math.min(a.height*.94,220),apex=Math.max(actorHeight+24,Math.min(a.y-44,310));
        const mx=384,my=apex-actorHeight*.52,mr=110,show=smooth(t/.55)*(1-smooth((t-2.1)/.7));
        ctx.save();ctx.globalAlpha=show*.86;ctx.fillStyle='#fff4c9';ctx.shadowColor='#fff1a0';ctx.shadowBlur=22;ctx.beginPath();ctx.arc(mx,my,mr,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle='#ffe3a1';
        for(const [x,y,r]of [[-28,-30,17],[43,24,23],[-36,44,12]]){ctx.beginPath();ctx.arc(mx+x,my+y,r,0,Math.PI*2);ctx.fill();}ctx.restore();
        let x=a.x,y=a.y,index=0,rotation=0;
        if(t<.95){index=Math.min(3,Math.floor(t/.95*4));y+=Math.sin(clamp(t/.95)*Math.PI)*8;}
        else if(t<1.75){const u=(t-.95)/.8;x=a.x+(mx-a.x)*Math.sin(u*Math.PI);y=a.y-Math.sin(u*Math.PI)*(a.y-apex);index=4+Math.min(3,Math.floor(u*4));rotation=Math.sin(u*Math.PI)*-.08;}
        else if(t<1.9){index=8+Math.min(3,Math.floor((t-1.75)/.15*4));y+=Math.sin((t-1.75)/.15*Math.PI)*8;}
        else{index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));y-=Math.sin(clamp((t-1.9)/.7)*Math.PI)*12;}
        if(t>=1.6){const u=clamp((t-1.6)/.4);ctx.save();ctx.globalAlpha=.85*(1-smooth((t-2.05)/.4));ctx.fillStyle='#fff1c7';ctx.beginPath();ctx.ellipse(a.x,a.y-3,Math.max(2,a.height*.45*u),15*u,0,0,Math.PI*2);ctx.fill();ctx.restore();}
        if(t>=1.75){const u=clamp((t-1.75)/.65);ctx.save();ctx.globalAlpha=1-u;ctx.strokeStyle='#fff4c9';ctx.lineWidth=8*(1-u)+2;ctx.beginPath();ctx.ellipse(a.x+(b.x-a.x)*u,a.y+(b.y-a.y)*u-20,30+u*110,15+u*42,0,0,Math.PI*2);ctx.stroke();ctx.restore();for(let i=0;i<8;i++){const angle=i*Math.PI/4;star(ctx,b.x+Math.cos(angle)*(25+u*100),b.y-b.height*.45+Math.sin(angle)*(25+u*80),8,1-u);}}
        pose(ctx,'ultimate',index,x,y,actorHeight,flip,rotation);
        const announcement=job.node.closest('#battle-stage')?.querySelector('#spell-announcement');
        if(announcement)announcement.textContent=t>=.65&&t<1.75?'☾ Cú Nhảy Trăng Rằm':'';
    }
    function dispose(job) {
        job.overlay?.canvas.remove();job.overlay?.stage.classList.remove('rabbit-ultimate-playing');job.node.classList.remove('rabbit-in-ultimate');
    }
    function tick(now) {
        frame=0;if(document.hidden)return;
        for(const [node,job]of active){
            if(!node.isConnected){dispose(job);active.delete(node);continue;}
            const t=Math.max(0,Math.min(job.duration,(now-job.started)/1000));
            if(job.overlay)drawUltimate(job,t);else drawPet(node,job.action,t);
            if(t>=job.duration){dispose(job);active.delete(node);if(job.action!=='lose'&&job.action!=='win'){node.dataset.mood='idle';drawPet(node,'idle',0);}}
        }
        if(active.size)frame=requestAnimationFrame(tick);
    }
    function play(node,action='idle') {
        if(!node?.classList.contains('rabbit'))return false;
        node.dataset.mood=action;
        ready().then(()=>{
            if(!node.isConnected||node.dataset.mood!==action)return;
            if(active.get(node)?.action===action)return;
            if(active.has(node)){dispose(active.get(node));active.delete(node);}
            const duration=action==='attack'||action==='hit'?1.2:3;
            node.classList.add('rabbit-ready');
            if(action==='idle'||reduced.matches){drawPet(node,action==='ultimate'?'win':action,action==='idle'?0:duration);return;}
            const job={node,action,duration,started:performance.now(),overlay:action==='ultimate'?ultimateCanvas(node):null};
            if(job.overlay)drawPet(node,'idle',0);
            active.set(node,job);if(!frame&&!document.hidden)frame=requestAnimationFrame(tick);
        }).catch(()=>{node.classList.remove('rabbit-ready');node.dataset.mood='idle';});
        return true;
    }
    function mount(root=document){for(const node of root.querySelectorAll('.battle-pet.rabbit')){mounted.add(node);play(node,node.dataset.mood||'idle');}}
    function notifyVictim(target,attacker,final){
        const victim=document.querySelector(target),node=victim?.querySelector('.battle-pet.rabbit');
        if(!node)return false;
        const impact=()=>{if(!node.isConnected)return;victim.classList.add('taking-hit');play(node,final?'lose':'hit');};
        if(final){const timer=setTimeout(()=>{timers.delete(timer);impact();},1750);timers.add(timer);}else impact();
        return true;
    }
    function destroy(){cancelAnimationFrame(frame);frame=0;for(const timer of timers)clearTimeout(timer);timers.clear();for(const job of active.values())dispose(job);active.clear();mounted.clear();}
    document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;}else if(active.size&&!frame)frame=requestAnimationFrame(tick);});
    return {ready,mount,play,notifyVictim,destroy};
})();
