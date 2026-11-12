/* 5BMath — Cá mập. Canvas presentation; battle results remain server-owned. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.SharkAnimation) return;
    const base = 'arena-art/shark/';
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const active = new Map(), mounted = new Set(), timers = new Set();
    const durations = {attack:.9, hit:1, lose:2.2, win:1.1, ultimate:3};
    const sheets = {};
    let loading, frame = 0, generation = 0;
    const clamp = x => Math.max(0, Math.min(1, x));
    const smooth = x => {x=clamp(x);return x*x*(3-2*x);};
    const shark = node => node?.matches?.('.battle-pet.ca-map') ? node : node?.querySelector?.('.battle-pet.ca-map');
    const image = src => new Promise((resolve,reject) => {const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error('Không tải được ảnh Cá mập'));img.src=src;});
    const style=document.createElement('style');
    style.textContent=`
body.learning-mode .mascot-art.ca-map{background-image:url('${base}idle.webp');background-size:contain;background-position:center}
body.learning-mode .battle-pet.ca-map .motion-sprite{display:none!important}
body.learning-mode .battle-pet.ca-map:not(.shark-ready)>.mascot-art{visibility:visible}
body.learning-mode .battle-pet.ca-map.shark-ready>.mascot-art{visibility:hidden;animation:none}
body.learning-mode .shark-canvas{display:block;position:absolute;inset:0;width:100%;height:100%}
body.learning-mode .shark-in-ultimate{visibility:hidden}
body.learning-mode .shark-ultimate-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:4}
body.learning-mode .shark-ultimate-active .energy-beam{display:none!important}
body.learning-mode .shark-ultimate-active .spell-announcement{max-width:94%;white-space:normal;text-align:center}
`;
    document.head.append(style);

    function ready() {
        if (!loading) loading=Promise.all([
            image(base+'poses.webp'), image(base+'actions.webp'),
            fetch(base+'manifest.json').then(r=>{if(!r.ok)throw Error('Thiếu dữ liệu Cá mập');return r.json();}),
        ]).then(([poses,actions,bounds])=>{
            for(const [key,img] of Object.entries({poses,actions})){
                const spec=bounds[key];
                if(!Array.isArray(spec?.frames)||spec.frames.length!==16)throw Error('Dữ liệu Cá mập không hợp lệ');
                sheets[key]={image:img,...spec,maxWidth:Math.max(...spec.frames.map(f=>f.width)),maxHeight:Math.max(...spec.frames.map(f=>f.height))};
            }
            return true;
        }).catch(error=>{loading=null;throw error;});
        return loading;
    }
    function pose(ctx,sheet,index,x,y,size,flip=false,rotation=0) {
        const spec=sheets[sheet],f=spec?.frames[index];if(!f)return;
        const scale=size/Math.max(spec.maxWidth,spec.maxHeight);
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);if(Boolean(flip)!==(f.facing==='left'))ctx.scale(-1,1);
        ctx.drawImage(spec.image,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale/2,f.width*scale,f.height*scale);ctx.restore();
    }
    function canvasFor(node) {
        let canvas=node.querySelector('.shark-canvas');
        if(!canvas){canvas=document.createElement('canvas');canvas.width=384;canvas.height=384;canvas.className='shark-canvas';canvas.setAttribute('aria-hidden','true');node.append(canvas);}
        return canvas;
    }
    function paint(node,action,t) {
        const canvas=canvasFor(node),ctx=canvas.getContext('2d');if(!ctx)return;
        ctx.clearRect(0,0,384,384);
        const u=clamp(t/(durations[action]||1)),step=Math.min(3,Math.floor(u*4));
        let sheet='actions',index=12,x=192,y=195,rotation=0;
        if(action==='attack'){index=step;x+=Math.sin(u*Math.PI)*40;y-=Math.sin(u*Math.PI)*12;rotation=Math.sin(u*Math.PI)*-.06;}
        else if(action==='hit'){index=4+step;x-=Math.sin(u*Math.PI*5)*(1-u)*14;rotation=Math.sin(u*Math.PI)*.12;}
        else if(action==='lose'){index=8+step;y+=smooth(u)*17;rotation=smooth(u)*.08;}
        else if(action==='win'){sheet='poses';index=12+step;y-=Math.sin(u*Math.PI)*17;}
        canvas.dataset.pose=String(index);canvas.dataset.action=action;canvas.dataset.time=String(t);
        pose(ctx,sheet,index,x,y,350,false,rotation);
        if(action==='hit'&&u<.8){ctx.save();ctx.globalAlpha=(1-u)*.8;ctx.fillStyle='#FFBE73';for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(140+i*50,50+Math.sin(u*15+i)*10,7,0,Math.PI*2);ctx.fill();}ctx.restore();}
    }
    function overlay(node,victim) {
        const stage=node.closest('#battle-stage'),target=victim?.querySelector?.('.battle-pet')||victim;
        if(!stage||!target)return null;
        const canvas=document.createElement('canvas');canvas.width=768;canvas.height=768;canvas.className='shark-ultimate-canvas';canvas.setAttribute('aria-hidden','true');
        const box=stage.getBoundingClientRect(),a=node.getBoundingClientRect(),b=target.getBoundingClientRect();
        if(!box.width||!box.height)return null;
        const point=r=>({x:(r.left-box.left+r.width/2)/box.width*768,y:(r.top-box.top+r.height/2)/box.height*768,size:Math.max(r.width/box.width,r.height/box.height)*768});
        stage.append(canvas);node.classList.add('shark-in-ultimate');stage.classList.add('shark-ultimate-active');
        return {canvas,stage,start:point(a),target:point(b),flip:b.left<a.left};
    }
    function drawUltimate(job,t) {
        const {canvas,stage,start:a,target:b,flip}=job.overlay,ctx=canvas.getContext('2d');if(!ctx)return;
        ctx.clearRect(0,0,768,768);
        const intensity=smooth(t/.5)*(1-smooth((t-2.25)/.75));
        ctx.save();ctx.globalAlpha=intensity;
        const sea=ctx.createLinearGradient(0,180,0,768);sea.addColorStop(0,'#65cfdf00');sea.addColorStop(1,'#1a97bc99');ctx.fillStyle=sea;ctx.fillRect(0,150,768,618);
        ctx.strokeStyle='#b5f5f6';ctx.lineWidth=5;
        for(let i=0;i<4;i++){const radius=35+i*27+Math.sin(t*7-i)*5;ctx.beginPath();ctx.ellipse(b.x,b.y+40,radius,radius*.3,t*2+i*.3,0,Math.PI*2);ctx.stroke();}
        ctx.restore();
        let x=a.x,y=a.y,index=0,rotation=0;
        if(t<.95){index=Math.min(3,Math.floor(t/.95*4));y+=Math.sin(t/.95*Math.PI)*18;rotation=Math.sin(t*6)*.04;}
        else if(t<1.42){const u=(t-.95)/.47,angle=u*Math.PI*3.2;x=b.x+Math.cos(angle)*120;y=b.y+40+Math.sin(angle)*35;index=4+Math.min(3,Math.floor(u*4));
            ctx.save();ctx.fillStyle='#577d91';ctx.beginPath();ctx.moveTo(x-20,y+8);ctx.quadraticCurveTo(x-8,y-60,x+12,y+6);ctx.closePath();ctx.fill();ctx.strokeStyle='#e7ffff';ctx.lineWidth=4;ctx.beginPath();ctx.ellipse(x,y+8,31,8,0,0,Math.PI*2);ctx.stroke();ctx.restore();
        } else if(t<1.9){const u=(t-1.42)/.48;x=b.x+(flip?70:-70)*(1-u);y=b.y-Math.sin(u*Math.PI)*120;index=8+Math.min(3,Math.floor(u*4));rotation=(flip?1:-1)*Math.sin(u*Math.PI)*.18;}
        else{const u=clamp((t-1.9)/1.1);x=a.x+Math.sin(u*Math.PI*2)*30;y=a.y-Math.sin(u*Math.PI)*25;index=12+Math.min(3,Math.floor(u*4));}
        if(t<.95||t>=1.42)pose(ctx,'poses',index,x,y,a.size*1.06,flip,rotation);
        if(t>=1.42&&t<2.15){const u=clamp((t-1.42)/.33),fade=1-smooth((t-1.82)/.33),radius=130;
            ctx.save();ctx.globalAlpha=fade;ctx.strokeStyle='#4dbfd9';ctx.lineWidth=25;ctx.lineCap='round';
            for(const side of [-1,1]){ctx.beginPath();ctx.ellipse(b.x,b.y+side*(1-u)*62,radius,85*(1-u)+12,0,side<0?Math.PI:0,side<0?Math.PI*2:Math.PI);ctx.stroke();}
            ctx.strokeStyle='#edffff';ctx.lineWidth=7;ctx.beginPath();ctx.ellipse(b.x,b.y+14,radius+14,43,0,0,Math.PI*2);ctx.stroke();ctx.restore();
        }
        if(t>=1.75){const u=clamp((t-1.75)/1.05);ctx.save();ctx.globalAlpha=1-u;for(let i=0;i<20;i++){const angle=i*2.399,radius=(25+u*160)*(1+(i%3)*.18);ctx.fillStyle=i%3?'#f5ffff':'#FFBE73';ctx.beginPath();ctx.arc(b.x+Math.cos(angle)*radius,b.y+Math.sin(angle)*radius*.7-u*55,4+(i%4)*2,0,Math.PI*2);ctx.fill();}ctx.restore();}
        const announcement=stage.querySelector('#spell-announcement');if(announcement)announcement.textContent=t>=.65&&t<1.9?'≋ VÂY XÉ ĐẠI DƯƠNG':'';
        canvas.dataset.time=String(t);
    }
    function dispose(job) {
        job.overlay?.canvas.remove();job.node.classList.remove('shark-in-ultimate');
        if(job.overlay){job.overlay.stage.classList.remove('shark-ultimate-active');const title=job.overlay.stage.querySelector('#spell-announcement');if(title?.textContent.includes('VÂY XÉ'))title.textContent='';}
    }
    function tick(now) {
        frame=0;if(document.hidden)return;
        for(const [node,job]of active){
            if(!node.isConnected){dispose(job);active.delete(node);mounted.delete(node);continue;}
            const t=Math.min(job.duration,(now-job.started)/1000);
            if(job.overlay)drawUltimate(job,t);else paint(node,job.action,t);
            if(t>=job.duration){dispose(job);active.delete(node);if(job.action==='ultimate'){node.dataset.mood='win';paint(node,'win',durations.win);}else if(!['lose','win'].includes(job.action)){node.dataset.mood='idle';paint(node,'idle',0);}}
        }
        if(active.size)frame=requestAnimationFrame(tick);
    }
    function play(node,action='idle',victim) {
        node=shark(node);if(!node)return false;
        if(node.sharkDefeated)action='lose';
        // Reserve this node before changing data-mood. MutationObserver runs
        // before the image promise settles and must not enqueue another play.
        mounted.add(node);
        node.sharkObservedMood=action;node.dataset.mood=action;
        const token=Symbol(action),epoch=generation;node.sharkActionToken=token;
        ready().then(()=>{
            if(!node.isConnected||node.sharkActionToken!==token||epoch!==generation)return;
            if(active.has(node)){dispose(active.get(node));active.delete(node);}
            node.classList.add('shark-ready');mounted.add(node);
            const duration=durations[action]||0;
            if(action==='idle'||reduced.matches||document.hidden){paint(node,action==='ultimate'?'win':action,duration);return;}
            const job={node,action,duration,started:performance.now(),overlay:action==='ultimate'?overlay(node,victim):null};
            if(action==='ultimate'&&!job.overlay){paint(node,'win',durations.win);return;}
            active.set(node,job);if(!frame)frame=requestAnimationFrame(tick);
        }).catch(()=>{if(node.sharkActionToken===token){mounted.delete(node);node.classList.remove('shark-ready');}});
        return true;
    }
    function mount(root=document){
        for(const node of mounted)if(!node.isConnected)mounted.delete(node);
        const nodes=[...root.querySelectorAll('.battle-pet.ca-map')];if(root.matches?.('.battle-pet.ca-map'))nodes.unshift(root);
        for(const node of nodes)if(!mounted.has(node)||node.sharkObservedMood!==(node.dataset.mood||'idle'))play(node,node.dataset.mood||'idle');
    }
    function later(fn,ms){const timer=setTimeout(()=>{timers.delete(timer);fn();},ms);timers.add(timer);}
    function reaction(pet,mood){
        if(!pet)return;pet.dataset.mood=mood;
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(pet,mood);
        const bear=pet.querySelector('canvas[data-bear]');if(bear&&typeof BearAnimation!=='undefined')BearAnimation.play(bear,mood==='lose'?'defeat':mood);
        if(pet.classList.contains('ca-map'))play(pet,mood);
    }
    function animate(target,attacker,final){
        const source=document.querySelector(attacker),victim=document.querySelector(target),actor=shark(source),targetPet=victim?.querySelector('.battle-pet');
        if(!actor||!victim||!targetPet)return false;
        const epoch=generation,stage=source.closest('#battle-stage'),announcement=stage?.querySelector('#spell-announcement');
        victim.classList.remove('taking-hit');source.classList.add('attacking');
        if(announcement)announcement.textContent=final?'':'≋ Sóng vây';
        const impact=()=>{if(epoch!==generation||!victim.isConnected)return;victim.dataset.spell='shark';victim.classList.add('taking-hit');reaction(targetPet,final?'lose':'hit');};
        if(final)later(impact,1750);else impact();
        play(actor,final?'ultimate':'attack',victim);
        later(()=>{
            if(epoch!==generation)return;
            source.classList.remove('attacking');victim.classList.remove('taking-hit');
            if(actor.isConnected)play(actor,final?'win':'idle');
            if(targetPet.isConnected)reaction(targetPet,final?'lose':'idle');
            if(announcement?.isConnected)announcement.textContent='';
        },final?3000:1100);
        return true;
    }
    function destroy(){generation++;cancelAnimationFrame(frame);frame=0;for(const timer of timers)clearTimeout(timer);timers.clear();for(const job of active.values())dispose(job);active.clear();mounted.clear();}
    function render(pet,mood='idle'){if(pet!=='ca-map')return '';return `<span class="pet-turn face-ca-map"><span class="battle-pet ca-map" data-mood="${['idle','attack','hit','win','lose','ultimate'].includes(mood)?mood:'idle'}" role="img" aria-label="Cá mập"><span class="mascot-art ca-map" aria-hidden="true"></span></span></span>`;}
    function markDefeated(node){node=shark(node);if(node)node.sharkDefeated=true;}
    document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;for(const [node,job]of active){dispose(job);if(node.isConnected)paint(node,job.action==='ultimate'?'win':job.action,job.duration);}active.clear();}});
    window.addEventListener('resize',()=>{for(const [node,job]of active)if(job.overlay){dispose(job);active.delete(node);node.dataset.mood='win';paint(node,'win',durations.win);}});
    reduced.addEventListener('change',()=>{if(reduced.matches){cancelAnimationFrame(frame);frame=0;for(const [node,job]of active){dispose(job);paint(node,job.action==='ultimate'?'win':job.action,job.duration);}active.clear();}});
    // Other mascots also set data-mood when they hit this one. Observe those
    // presentation changes so mixed-species matches show the shark reaction.
    let queued=false;
    const observer=new MutationObserver(records=>{
        const relevant=records.some(r=>r.type==='attributes'?r.target.matches?.('.battle-pet.ca-map'):
            [...r.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('.battle-pet.ca-map')||n.querySelector?.('.battle-pet.ca-map'))));
        if(relevant&&!queued){queued=true;queueMicrotask(()=>{queued=false;mount();});}
    });
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});
    window.SharkAnimation={ready,preload:ready,mount,play,render,animate,markDefeated,destroy,attack:(source,victim)=>play(source,'attack',victim),ultimate:(source,victim)=>play(source,'ultimate',victim),inspect:()=>({loaded:Boolean(sheets.poses),active:active.size,canvases:[...mounted].filter(n=>n.isConnected).map(n=>({mood:n.dataset.mood,pose:n.querySelector('canvas')?.dataset.pose})),reducedMotion:reduced.matches})};
})();
