/* Canvas appearance for the Ngựa account mascot. Combat rules stay in LearningApp. */
(() => {
    'use strict';
    const ASSET_ROOT=new URL('arena-art/horse/v1/',document.baseURI).href;
    const LEGACY_KEY='5bmath:arena-appearance';
    const DURATIONS={idle:0,attack:1.2,hit:.9,defeat:2.6,win:1.5,ultimate:3};
    const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
    const ease=v=>{const u=clamp(v);return u*u*(3-2*u);};
    const media=matchMedia('(prefers-reduced-motion: reduce)');
    const controllers=new Set(),mounted=new Map(),effects=new Set(),timers=new Map(),operations=new Set(),pendingFinals=new Set();
    let assetsPromise,generation=0,finaleUntil=0,queued=false;
    // An old browser-only appearance must never replace the selected account mascot.
    try {if(localStorage.getItem(LEGACY_KEY)==='horse')localStorage.removeItem(LEGACY_KEY);} catch {}

    function loadImage(url) {
        return new Promise((resolve,reject)=>{
            const image=new Image();image.onload=()=>resolve(image);
            image.onerror=()=>reject(new Error('Không tải được ảnh Ngựa.'));image.src=url;
        });
    }
    async function loadAtlas(name,signal) {
        const [image,response]=await Promise.all([loadImage(ASSET_ROOT+name+'.webp'),fetch(ASSET_ROOT+name+'.json',{signal})]);
        if(!response.ok)throw new Error('Không tải được tư thế Ngựa.');
        const atlas=await response.json();
        if(!Array.isArray(atlas.frames)||atlas.frames.length!==16)throw new Error('Tư thế Ngựa chưa đủ.');
        for(const f of atlas.frames) {
            if(![f.left,f.top,f.width,f.height].every(Number.isFinite)||f.width<=0||f.height<=0||f.left<0||f.top<0||f.left+f.width>image.naturalWidth||f.top+f.height>image.naturalHeight)throw new Error('Khung hình Ngựa không hợp lệ.');
        }
        return {image,...atlas};
    }
    function preload() {
        if(!assetsPromise) {
            const abort=new AbortController();let timeout;
            const deadline=new Promise((resolve,reject)=>{timeout=setTimeout(()=>{abort.abort();reject(new Error('Ảnh Ngựa tải quá lâu.'));},8000);});
            assetsPromise=Promise.race([Promise.all([loadAtlas('poses',abort.signal),loadAtlas('reactions',abort.signal)]),deadline])
                .then(([poses,reactions])=>({poses,reactions}))
                .catch(error=>{assetsPromise=null;throw error;})
                .finally(()=>clearTimeout(timeout));
        }
        return assetsPromise;
    }
    function horseshoe(ctx,x,y,size,rotation=0,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rotation);
        ctx.strokeStyle='#ffd28a';ctx.lineWidth=size*.19;ctx.lineCap='round';
        ctx.beginPath();ctx.arc(0,0,size*.34,-Math.PI*.1,Math.PI*1.1);ctx.stroke();
        ctx.strokeStyle='#fff5cb';ctx.lineWidth=size*.055;
        ctx.beginPath();ctx.arc(0,0,size*.34,0,Math.PI);ctx.stroke();ctx.restore();
    }
    function sprite(ctx,atlas,index,x,feet,height,direction=1,rotation=0,alpha=1) {
        const f=atlas.frames[index],scale=height/Math.max(...atlas.frames.map(frame=>Math.max(frame.height,frame.width)));
        const w=f.width*scale,h=f.height*scale;
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,feet);ctx.rotate(rotation);ctx.scale(direction,1);
        ctx.drawImage(atlas.image,f.left,f.top,f.width,f.height,-w/2,-h,w,h);ctx.restore();
    }
    function poseFor(state,t) {
        t=clamp(t,0,DURATIONS[state]||0);
        if(state==='ultimate') {
            if(t<.95)return {atlas:'poses',index:Math.min(3,Math.floor(t/.24))};
            if(t<1.55)return {atlas:'poses',index:4+Math.floor((t-.95)*12)%4};
            if(t<1.9)return {atlas:'poses',index:8+Math.min(3,Math.floor((t-1.55)/.35*4))};
            return {atlas:'poses',index:12+Math.min(3,Math.floor((t-1.9)/1.1*4))};
        }
        const row={attack:0,hit:4,defeat:8,idle:12,win:12}[state]??12;
        return {atlas:state==='win'?'poses':'reactions',index:row+(state==='idle'?0:Math.min(3,Math.floor(t/DURATIONS[state]*4)))};
    }
    const normalize=state=>state==='lose'||state==='sad'?'defeat':state==='hurt'?'hit':state;
    function create(canvas,{direction=1}={}) {
        const ctx=canvas.getContext('2d');canvas.width=384;canvas.height=384;
        let assets,frame=0,disposed=false,state='idle',time=0,start=0,lastDraw=-1,requestId=0;
        const controller={canvas,ready:null,play,stop,dispose,get state(){return state;},get running(){return Boolean(frame);}};
        controllers.add(controller);
        function draw(t) {
            if(!assets||disposed)return;
            const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);
            const pose=poseFor(state,t),progress=clamp(t/(DURATIONS[state]||1));
            let x=w/2,y=h*.92,rotation=0;
            if(!media.matches) {
                if(state==='attack'){x+=direction*Math.sin(progress*Math.PI)*w*.065;y-=Math.sin(progress*Math.PI)*h*.035;}
                if(state==='hit'){x-=direction*Math.sin(progress*Math.PI)*w*.05;rotation=direction*Math.sin(progress*Math.PI)*.06;}
                if(state==='defeat')y+=ease(progress)*h*.015;
                if(state==='ultimate'&&t>=.95&&t<1.9){x+=direction*Math.sin((t-.95)/.95*Math.PI)*w*.06;y-=Math.abs(Math.sin(t*15))*h*.025;}
                if(state==='win')y-=Math.sin(progress*Math.PI)*h*.06;
            }
            ctx.save();ctx.fillStyle='#203a3220';ctx.beginPath();ctx.ellipse(w/2,h*.91,w*.23,h*.025,0,0,Math.PI*2);ctx.fill();ctx.restore();
            if(state==='ultimate'&&t>=.95&&t<1.9) {
                for(let k=3;k>=1;k--)sprite(ctx,assets[pose.atlas],pose.index,x-direction*k*14,y,h*.77,direction,rotation,.09/k);
                for(let k=0;k<4;k++)horseshoe(ctx,x-direction*(k*21+15),h*.9-k*3,19,t+k,.5);
            }
            sprite(ctx,assets[pose.atlas],pose.index,x,y,h*.85,direction,rotation);
            if(state==='hit'&&t<.65)for(let k=0;k<3;k++) {
                const a=k*Math.PI*2/3+t*3;horseshoe(ctx,x+Math.cos(a)*57,h*.21+Math.sin(a)*14,13,-a,.65);
            }
            canvas.dataset.horseState=state;canvas.dataset.horseTime=t.toFixed(3);canvas.dataset.horsePose=String(pose.index);
        }
        function tick(now) {
            frame=0;if(disposed||document.hidden||!canvas.isConnected)return;
            time=clamp((now-start)/1000,0,DURATIONS[state]);
            if(time-lastDraw>=1/30||time===DURATIONS[state]){draw(time);lastDraw=time;}
            if(time<DURATIONS[state])frame=requestAnimationFrame(tick);
            else if(['attack','hit'].includes(state)){state='idle';draw(0);}
        }
        async function play(nextState='idle') {
            nextState=normalize(nextState);if(!(nextState in DURATIONS)||disposed)return false;
            cancelAnimationFrame(frame);frame=0;const request=++requestId;state=nextState;time=0;lastDraw=-1;
            try {assets=await preload();} catch(error){if(!disposed&&request===requestId)canvas.dispatchEvent(new CustomEvent('horseerror',{detail:error}));return false;}
            if(disposed||request!==requestId||!canvas.isConnected)return false;
            canvas.dispatchEvent(new CustomEvent('horseready'));
            if(media.matches||document.hidden||!DURATIONS[state]){draw(DURATIONS[state]);return true;}
            start=performance.now();draw(0);frame=requestAnimationFrame(tick);return true;
        }
        function stop(){cancelAnimationFrame(frame);frame=0;requestId++;if(assets){if(['attack','hit'].includes(state))state='idle';draw(DURATIONS[state]);}}
        function dispose(){if(disposed)return;disposed=true;cancelAnimationFrame(frame);frame=0;requestId++;controllers.delete(controller);}
        controller.ready=play('idle');return controller;
    }

    function later(callback,delay,nodes=[]) {
        const timer=setTimeout(()=>{timers.delete(timer);if(!document.hidden&&nodes.every(node=>node?.isConnected))callback();},delay);
        timers.set(timer,nodes);return timer;
    }
    function stopEffect(record) {
        if(!record||!effects.has(record))return;
        effects.delete(record);cancelAnimationFrame(record.frame);record.canvas.remove();
        if(![...effects].some(other=>other.target===record.target))record.target?.classList.remove('horse-whirl-target');
        for(const kind of ['horse-ultimate','horse-strike'])if(![...effects].some(other=>other.stage===record.stage&&other.kind===kind))record.stage.classList.remove(kind);
    }
    function clearOperation(operation) {
        operations.delete(operation);
        if(![...operations].some(other=>other.source===operation.source))operation.source.classList.remove('attacking');
        if(![...operations].some(other=>other.victim===operation.victim))operation.victim.classList.remove('taking-hit');
    }
    function stopAll() {
        generation++;finaleUntil=0;pendingFinals.clear();
        for(const timer of timers.keys())clearTimeout(timer);timers.clear();
        for(const operation of [...operations])clearOperation(operation);
        for(const record of [...effects])stopEffect(record);
        for(const controller of controllers)controller.stop();
    }
    function playEffect(stage,{ultimate=false,source,victim}={}) {
        if(!stage||!source||!victim||document.hidden||media.matches)return;
        for(const record of [...effects])if(record.source===source)stopEffect(record);
        const canvas=document.createElement('canvas');canvas.className='horse-stage-effect';canvas.width=720;canvas.height=720;canvas.setAttribute('aria-hidden','true');stage.append(canvas);
        const ctx=canvas.getContext('2d'),target=victim.closest('.fighter'),direction=source.closest('.right')?-1:1;
        const duration=ultimate?3:1.2,start=performance.now(),kind=ultimate?'horse-ultimate':'horse-strike';
        const record={canvas,stage,target,source,kind,frame:0};effects.add(record);stage.classList.add(kind);
        const box=stage.getBoundingClientRect();
        if(!target||!box.width||!box.height){stopEffect(record);return;}
        const point=node=>{const r=node.getBoundingClientRect();return {x:(r.x-box.x+r.width/2)/box.width*720,y:(r.y-box.y+r.height*.55)/box.height*720};};
        const a=point(source),b=point(victim);
        function render(t) {
            ctx.clearRect(0,0,720,720);
            canvas.dataset.horseTime=t.toFixed(3);canvas.dataset.horseNameVisible=String(ultimate&&t>=.65&&t<1.7);
            canvas.dataset.horsePhase=ultimate?(t<.65?'windup':t<.95?'name':t<1.75?'charge':t<1.9?'impact':'victory'):'attack';
            if(ultimate&&t>=.65&&t<1.7) {
                // The upper-left scenery area stays clear of both fighters and their HP cards.
                ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(28,90,430,68,22);ctx.fill();ctx.stroke();
                ctx.fillStyle='#fff9ed';ctx.font='800 26px Arial,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('VÓ NGỰA CUỒNG PHONG',243,125,400);
            }
            const from=ultimate?.95:.22,to=ultimate?1.75:.7;
            if(t>=from&&t<to+.4) {
                const u=clamp((t-from)/(to-from)),fade=1-clamp((t-to)/.4),x=a.x+(b.x-a.x)*ease(u),y=a.y+(b.y-a.y)*ease(u);
                if(ultimate) {
                    for(let k=0;k<19;k++){const angle=k*.79+t*14,r=22+(k%6)*8;horseshoe(ctx,x+Math.cos(angle)*r,y+Math.sin(angle)*r*.52,18+k%3*3,angle,fade*(.3+k/30));}
                    const entry=mounted.get(source);if(entry?.assets)sprite(ctx,entry.assets.poses,6,x,y+60,150,direction,0,fade*.28);
                } else horseshoe(ctx,x,y,45,-t*3,fade);
            }
            if(ultimate&&t>=1.75&&t<2.3) {
                if(!target.classList.contains('horse-whirl-target'))target.classList.add('horse-whirl-target');const u=clamp((t-1.75)/.55);
                for(let k=0;k<10;k++){const angle=k*Math.PI/5;horseshoe(ctx,b.x+Math.cos(angle)*(20+u*90),b.y+Math.sin(angle)*(20+u*65),17,angle+t,1-u);}
            } else if(target.classList.contains('horse-whirl-target'))target.classList.remove('horse-whirl-target');
        }
        function tick(now) {
            record.frame=0;if(!effects.has(record)||!stage.isConnected||!source.isConnected||!victim.isConnected||document.hidden){stopEffect(record);return;}
            const t=clamp((now-start)/1000,0,duration);render(t);
            if(t<duration)record.frame=requestAnimationFrame(tick);else stopEffect(record);
        }
        render(0);record.frame=requestAnimationFrame(tick);
    }
    function isHorse(node){return Boolean(node?.matches?.('.battle-pet.horse'));}
    function attachPet(pet) {
        if(mounted.has(pet))return mounted.get(pet);
        if(!isHorse(pet))return null;
        const canvas=document.createElement('canvas');canvas.className='horse-pet-canvas';canvas.setAttribute('aria-hidden','true');pet.append(canvas);
        const controller=create(canvas,{direction:pet.closest('.right')?-1:1});
        const entry={controller,canvas,mood:'idle',assets:null,serial:0};mounted.set(pet,entry);pet.classList.add('horse-loading');
        canvas.addEventListener('horseready',()=>{
            if(!pet.isConnected||mounted.get(pet)!==entry)return;
            pet.classList.remove('horse-loading','horse-failed');pet.classList.add('horse-ready');pet.parentElement?.classList.add('horse-facing');
        });
        canvas.addEventListener('horseerror',()=>{if(mounted.get(pet)===entry){pet.classList.remove('horse-loading','horse-ready');pet.classList.add('horse-failed');}});
        preload().then(assets=>{if(mounted.get(pet)===entry)entry.assets=assets;}).catch(()=>{});
        return entry;
    }
    function detachPet(pet,entry) {
        entry.serial++;entry.controller.dispose();entry.canvas.remove();mounted.delete(pet);
        pet.classList.remove('horse-ready','horse-loading','horse-failed');pet.parentElement?.classList.remove('horse-facing');
    }
    function play(pet,state='idle') {
        if(!isHorse(pet))pet=pet?.querySelector?.('.battle-pet.horse');
        const entry=attachPet(pet);if(!entry)return Promise.resolve(false);
        state=normalize(state);if(!(state in DURATIONS))return Promise.resolve(false);
        entry.mood=state;pet.dataset.mood=state==='defeat'?'lose':state;
        return entry.controller.play(state);
    }
    function notifyVictimNodes(source,victim,final=false) {
        const pet=victim?.querySelector('.battle-pet.horse');if(!source||!pet||source.querySelector('.battle-pet.horse'))return;
        if(final)finaleUntil=Math.max(finaleUntil,Date.now()+3100);
        const entry=attachPet(pet),now=performance.now();
        if(entry.lastIncoming!==undefined&&now-entry.lastIncoming<80)return;entry.lastIncoming=now;
        later(()=>play(pet,final?'defeat':'hit'),final?1750:0,[source,pet]);
    }
    function notifyVictim(target,attacker,final=false) {
        notifyVictimNodes(typeof attacker==='string'?document.querySelector(attacker):attacker,typeof target==='string'?document.querySelector(target):target,final);
    }
    function hit({source,victim,final=false}={}) {
        if(!source||!victim)return false;
        notifyVictimNodes(source,victim,final);
        const sourcePet=source.querySelector('.battle-pet.horse'),victimPet=victim.querySelector('.battle-pet'),stage=source.closest('#battle-stage');
        if(!sourcePet||!victimPet||!stage)return false;
        const entry=attachPet(sourcePet),serial=++entry.serial,request=generation,pending={source:sourcePet,victim:victimPet};
        if(final){finaleUntil=Math.max(finaleUntil,Date.now()+3100);pendingFinals.add(pending);}
        play(sourcePet,final?'ultimate':'attack').then(started=>{
            pendingFinals.delete(pending);
            if(generation!==request||entry.serial!==serial||!sourcePet.isConnected||!victimPet.isConnected)return;
            if(final)finaleUntil=Math.max(finaleUntil,Date.now()+3100);
            const operation={source,victim};operations.add(operation);source.classList.add('attacking');
            if(started)playEffect(stage,{ultimate:final,source:sourcePet,victim:victimPet});
            const impact=()=>{
                victim.dataset.spell='horse';victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');
                if(victimPet.classList.contains('horse'))play(victimPet,final?'defeat':'hit');
                if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victimPet,final?'lose':'hit');
            };
            if(final)later(impact,1750,[sourcePet,victimPet]);else impact();
            later(()=>{
                clearOperation(operation);
                if(!final){play(sourcePet,'idle');if(victimPet.isConnected)victimPet.dataset.mood='idle';}
            },final?3000:1200,[sourcePet,victimPet]);
        });
        return true;
    }
    function scan() {
        for(const [node,entry] of mounted)if(!node.isConnected||!isHorse(node))detachPet(node,entry);
        for(const [timer,nodes] of timers)if(nodes.some(node=>!node?.isConnected)){clearTimeout(timer);timers.delete(timer);}
        for(const operation of [...operations])if(!operation.source.isConnected||!operation.victim.isConnected)clearOperation(operation);
        for(const pending of [...pendingFinals])if(!pending.source.isConnected||!pending.victim.isConnected)pendingFinals.delete(pending);
        for(const record of [...effects])if(!record.stage.isConnected||!record.source.isConnected||!record.target.isConnected)stopEffect(record);
        // The normal account mascot picker replaces the former browser-only panel.
        document.querySelectorAll('.horse-appearance-panel').forEach(panel=>panel.remove());
        for(const pet of document.querySelectorAll('.battle-pet.horse')) {
            const entry=attachPet(pet);let mood=normalize(pet.dataset.mood||'idle');
            if(!(mood in DURATIONS))mood='idle';
            if(entry.mood!==mood) {
                // A delayed legacy idle cannot cut a finale or held defeat pose short.
                if(mood==='idle'&&['ultimate','defeat'].includes(entry.controller.state))continue;
                entry.mood=mood;entry.controller.play(mood);
            }
        }
    }
    function queueScan(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;scan();});}
    function boot(){const observer=new MutationObserver(queueScan);observer.observe(document.querySelector('#app')||document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-mood','class']});scan();}
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stopAll();else scan();});
    media.addEventListener('change',stopAll);window.addEventListener('resize',stopAll);window.addEventListener('pagehide',stopAll);
    const pendingUntil=()=>pendingFinals.size?Math.max(finaleUntil,Date.now()+200):finaleUntil;
    const inspect=()=>({pets:[...mounted].map(([node,entry])=>({battle:true,side:node.closest('.right')?'right':'left',mood:entry.mood,state:entry.controller.state,pose:Number(entry.canvas.dataset.horsePose),running:entry.controller.running,connected:node.isConnected})),effects:effects.size,timers:timers.size,pendingLoads:pendingFinals.size,reducedMotion:media.matches,pendingUntil:pendingUntil()});
    window.HorseAnimation=Object.freeze({preload,create,hit,notifyVictim,play,mount:scan,sync:scan,stop:stopAll,inspect,pendingUntil,setEnabled:()=>scan(),get enabled(){return Boolean(document.querySelector('.battle-pet.horse'));},get activeCount(){return [...controllers].filter(c=>c.running).length+[...effects].filter(record=>record.frame).length;}});
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed)){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();}
})();
