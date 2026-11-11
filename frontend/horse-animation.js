/* Browser-local appearance only. Battle rules and account data stay in LearningApp. */
(() => {
    'use strict';
    const ASSET_ROOT=new URL('arena-art/horse/v1/',document.baseURI).href;
    const STORAGE_KEY='5bmath:arena-appearance';
    const DURATIONS={idle:0,attack:1.2,hit:.9,defeat:2.6,win:1.5,ultimate:3};
    const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
    const ease=v=>{const u=clamp(v);return u*u*(3-2*u);};
    const media=matchMedia('(prefers-reduced-motion: reduce)');
    const controllers=new Set(),mounted=new Map(),timers=new Set();
    let assetsPromise,enabled=false,effect=null;
    try {enabled=localStorage.getItem(STORAGE_KEY)==='horse';} catch {}

    function loadImage(url) {
        return new Promise((resolve,reject)=>{
            const image=new Image();image.onload=()=>resolve(image);
            image.onerror=()=>reject(new Error('Không tải được ảnh Ngựa.'));image.src=url;
        });
    }
    async function loadAtlas(name) {
        const [image,response]=await Promise.all([loadImage(ASSET_ROOT+name+'.webp'),fetch(ASSET_ROOT+name+'.json')]);
        if(!response.ok)throw new Error('Không tải được tư thế Ngựa.');
        const atlas=await response.json();
        if(!Array.isArray(atlas.frames)||atlas.frames.length!==16)throw new Error('Tư thế Ngựa chưa đủ.');
        for(const f of atlas.frames) {
            if(![f.left,f.top,f.width,f.height].every(Number.isFinite)||f.width<=0||f.height<=0||f.left<0||f.top<0||f.left+f.width>image.naturalWidth||f.top+f.height>image.naturalHeight)throw new Error('Khung hình Ngựa không hợp lệ.');
        }
        return {image,...atlas};
    }
    function preload() {
        if(!assetsPromise)assetsPromise=Promise.all([loadAtlas('poses'),loadAtlas('reactions')])
            .then(([poses,reactions])=>({poses,reactions}))
            .catch(error=>{assetsPromise=null;throw error;});
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
    function create(canvas,{direction=1}={}) {
        const ctx=canvas.getContext('2d');canvas.width=384;canvas.height=384;
        let assets,frame=0,disposed=false,state='idle',time=0,start=0,lastDraw=-1,generation=0;
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
                for(let k=3;k>=1;k--)sprite(ctx,assets[pose.atlas],pose.index,x-direction*k*14,y,h*.85,direction,rotation,.09/k);
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
            // A RAF timestamp belongs to the frame start, which may precede a
            // play() call made in that frame's microtask checkpoint.
            time=clamp((now-start)/1000,0,DURATIONS[state]);
            if(time-lastDraw>=1/30||time===DURATIONS[state]){draw(time);lastDraw=time;}
            if(time<DURATIONS[state])frame=requestAnimationFrame(tick);
            else if(['attack','hit'].includes(state)){state='idle';draw(0);}
        }
        async function play(nextState='idle') {
            if(!(nextState in DURATIONS)||disposed)return;
            cancelAnimationFrame(frame);frame=0;generation++;
            const request=generation;state=nextState;time=0;lastDraw=-1;
            try {assets=await preload();} catch(error){canvas.dispatchEvent(new CustomEvent('horseerror',{detail:error}));return;}
            if(disposed||request!==generation||!canvas.isConnected)return;
            canvas.dispatchEvent(new CustomEvent('horseready'));
            if(media.matches||document.hidden||!DURATIONS[state]){draw(DURATIONS[state]);return;}
            start=performance.now();draw(0);frame=requestAnimationFrame(tick);
        }
        function stop(){cancelAnimationFrame(frame);frame=0;generation++;if(assets){if(['attack','hit'].includes(state))state='idle';draw(DURATIONS[state]);}}
        function dispose(){if(disposed)return;disposed=true;cancelAnimationFrame(frame);frame=0;generation++;controllers.delete(controller);}
        controller.ready=play('idle');return controller;
    }

    function stopEffect() {
        if(!effect)return;
        cancelAnimationFrame(effect.frame);effect.target?.classList.remove('horse-whirl-target');
        effect.stage.classList.remove('horse-ultimate','horse-strike');effect.canvas.remove();effect=null;
    }
    function later(callback,delay) {
        const timer=setTimeout(()=>{timers.delete(timer);if(!document.hidden&&enabled)callback();},delay);timers.add(timer);return timer;
    }
    function stopAll() {
        for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const c of controllers)c.stop();stopEffect();
    }
    function playEffect(stage,{ultimate=false,direction=1}={}) {
        stopEffect();if(!stage||document.hidden||media.matches)return;
        const canvas=document.createElement('canvas');canvas.className='horse-stage-effect';canvas.width=720;canvas.height=720;canvas.setAttribute('aria-hidden','true');stage.append(canvas);
        const ctx=canvas.getContext('2d'),target=stage.querySelector(direction===1?'#fighter-opponent':'#fighter-me');
        const source=stage.querySelector(direction===1?'#fighter-me .battle-pet':'#fighter-opponent .battle-pet');
        const duration=ultimate?3:1.2,start=performance.now(),record={canvas,stage,target,frame:0};effect=record;
        stage.classList.add(ultimate?'horse-ultimate':'horse-strike');
        const box=stage.getBoundingClientRect();
        const point=node=>{const r=node.getBoundingClientRect();return {x:(r.x-box.x+r.width/2)/box.width*720,y:(r.y-box.y+r.height*.55)/box.height*720};};
        const a=point(source),b=point(target.querySelector('.battle-pet'));
        function render(t) {
            ctx.clearRect(0,0,720,720);
            canvas.dataset.horseTime=t.toFixed(3);
            canvas.dataset.horseNameVisible=String(ultimate&&t>=.65&&t<1.7);
            canvas.dataset.horsePhase=ultimate?(t<.65?'windup':t<.95?'name':t<1.75?'charge':t<1.9?'impact':'victory'):'attack';
            if(ultimate&&t>=.65&&t<1.7) {
                ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(50,310,620,62,22);ctx.fill();ctx.stroke();
                ctx.fillStyle='#fff9ed';ctx.font='800 29px Arial,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('VÓ NGỰA CUỒNG PHONG',360,342,580);
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
                if(!target.classList.contains('horse-whirl-target'))target.classList.add('horse-whirl-target');
                const u=clamp((t-1.75)/.55);
                for(let k=0;k<10;k++){const angle=k*Math.PI/5;horseshoe(ctx,b.x+Math.cos(angle)*(20+u*90),b.y+Math.sin(angle)*(20+u*65),17,angle+t,1-u);}
            } else if(target.classList.contains('horse-whirl-target'))target.classList.remove('horse-whirl-target');
        }
        function tick(now) {
            record.frame=0;if(effect!==record||!stage.isConnected||document.hidden){stopEffect();return;}
            const t=Math.min(duration,(now-start)/1000);render(t);
            if(t<duration)record.frame=requestAnimationFrame(tick);else stopEffect();
        }
        record.frame=requestAnimationFrame(tick);
    }
    function makePanel() {
        const panel=document.createElement('section');panel.className='card card-pad horse-appearance-panel';
        panel.innerHTML='<canvas class="horse-appearance-preview" aria-label="Ngựa nâu hạt dẻ, ngoại hình trận đấu" role="img"></canvas><div><h2>Ngựa · ngoại hình trận đấu</h2><p>Chọn Ngựa cho các trận Đấu trí trên trình duyệt này.</p><div class="actions"><button class="btn dark" type="button" data-horse-choice="horse">Dùng Ngựa</button><button class="btn outline" type="button" data-horse-choice="profile">Dùng linh vật hồ sơ</button></div><small class="horse-appearance-status" role="status"></small></div>';
        panel.addEventListener('click',event=>{const button=event.target.closest('[data-horse-choice]');if(button)setEnabled(button.dataset.horseChoice==='horse');});
        const canvas=panel.querySelector('canvas'),preview=create(canvas);mounted.set(canvas,{controller:preview,panel:true});
        canvas.addEventListener('horseerror',()=>{panel.querySelector('[role="status"]').textContent='Chưa tải được Ngựa. Em hãy tải lại trang để thử lại.';});
        return panel;
    }
    function setEnabled(value) {
        enabled=Boolean(value);try {localStorage.setItem(STORAGE_KEY,enabled?'horse':'profile');} catch {}
        if(!enabled)stopAll();
        window.dispatchEvent(new CustomEvent('5bmath:arena-appearance',{detail:{appearance:enabled?'horse':'profile'}}));scan();
    }
    function attachPet(pet) {
        if(mounted.has(pet))return mounted.get(pet);
        // Temporarily remove the profile species hooks so its own runtime cannot
        // launch a second ultimate over the horse. The account is untouched.
        const classes=[...pet.classList].filter(name=>!['battle-pet','horse-ready','horse-loading'].includes(name));
        if(classes.includes('rabbit')&&typeof RabbitAnimation!=='undefined')RabbitAnimation.play(pet,'idle');
        for(const name of classes)pet.classList.remove(name);
        pet.classList.add('horse-loading');
        const canvas=document.createElement('canvas');canvas.className='horse-pet-canvas';canvas.setAttribute('aria-hidden','true');pet.append(canvas);
        const direction=pet.closest('.right')?-1:1,controller=create(canvas,{direction});
        const entry={controller,canvas,mood:null,assets:null,classes,originalLabel:pet.getAttribute('aria-label')};mounted.set(pet,entry);
        canvas.addEventListener('horseready',()=>{
            if(!enabled||!pet.isConnected)return;
            pet.classList.remove('horse-loading');pet.classList.add('horse-ready');pet.parentElement.classList.add('horse-facing');pet.setAttribute('aria-label','Ngựa · ngoại hình trận đấu');
        });
        preload().then(assets=>{entry.assets=assets;}).catch(()=>{pet.classList.remove('horse-loading');for(const name of classes)pet.classList.add(name);});return entry;
    }
    function detachPet(pet,entry) {
        entry.controller.dispose();entry.canvas?.remove();pet.classList.remove('horse-ready','horse-loading');pet.parentElement?.classList.remove('horse-facing');
        for(const name of entry.classes||[])pet.classList.add(name);
        if(entry.originalLabel!==undefined)pet.setAttribute('aria-label',entry.originalLabel||'');mounted.delete(pet);
        if(pet.isConnected){if(typeof RabbitAnimation!=='undefined')RabbitAnimation.mount(pet.parentElement);window.ArenaCatAnimation?.sync(pet.parentElement);}
    }
    // Called before other species handlers. Only a horse attacker consumes the
    // event; a horse victim is notified even when another handler returns early.
    function notifyVictimNodes(source,victim,final=false) {
        if(!enabled||!source||victim?.id!=='fighter-me')return;
        const pet=victim.querySelector('.battle-pet');if(!pet)return;
        const entry=attachPet(pet),now=performance.now();
        if(entry.lastIncoming&&now-entry.lastIncoming<80)return;
        entry.lastIncoming=now;
        later(()=>{
            if(!pet.isConnected)return;
            const mood=final?'defeat':'hit';entry.mood=mood;pet.dataset.mood=final?'lose':'hit';entry.controller.play(mood);
        },final?1750:0);
    }
    function notifyVictim(target,attacker,final=false) {
        notifyVictimNodes(document.querySelector(attacker),document.querySelector(target),final);
    }
    function hit({source,victim,final=false}={}) {
        if(!enabled||!source||!victim)return false;
        const sourcePet=source.querySelector('.battle-pet'),victimPet=victim.querySelector('.battle-pet');
        if(!sourcePet||!victimPet)return false;
        notifyVictimNodes(source,victim,final);
        if(source.id!=='fighter-me')return false;
        const entry=attachPet(sourcePet),stage=source.closest('#battle-stage');
        if(!entry.assets||!stage)return false;
        const mood=final?'ultimate':'attack';entry.mood=mood;sourcePet.dataset.mood=mood;entry.controller.play(mood);
        source.classList.add('attacking');playEffect(stage,{ultimate:final,direction:source.classList.contains('right')?-1:1});
        const impact=()=>{
            if(!victim.isConnected)return;
            victim.dataset.spell='horse';victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');
            if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victimPet,final?'lose':'hit');
        };
        if(final)later(impact,1750);else impact();
        later(()=>{
            source.classList.remove('attacking');victim.classList.remove('taking-hit');
            if(sourcePet.isConnected&&!final){sourcePet.dataset.mood='idle';entry.mood='idle';entry.controller.play('idle');}
            if(victimPet.isConnected&&!final)victimPet.dataset.mood='idle';
        },final?3000:1200);
        return true;
    }
    function scan() {
        for(const [node,entry] of mounted)if(!node.isConnected){entry.controller.dispose();mounted.delete(node);}
        if(effect&&!effect.stage.isConnected)stopEffect();
        const placement=document.querySelector('.arena-lobby')||document.querySelector('.mascot-feature')?.parentElement;
        if(placement&&!placement.querySelector('.horse-appearance-panel')){
            const panel=makePanel(),options=placement.querySelector('.arena-options');
            if(options)placement.insertBefore(panel,options);else placement.querySelector('.mascot-feature').after(panel);
        }
        document.querySelectorAll('.horse-appearance-panel').forEach(panel=>{
            panel.querySelectorAll('[data-horse-choice]').forEach(button=>{const value=String(enabled===(button.dataset.horseChoice==='horse'));if(button.getAttribute('aria-pressed')!==value)button.setAttribute('aria-pressed',value);});
            const status=panel.querySelector('.horse-appearance-status'),text=enabled?'Đang dùng Ngựa trong trận đấu.':'Đang dùng linh vật trong hồ sơ.';
            if(status.textContent!==text&&!status.textContent.startsWith('Chưa tải'))status.textContent=text;
        });
        const pets=[...document.querySelectorAll('#fighter-me .battle-pet,.result-pet .battle-pet')];
        for(const [node,entry] of mounted)if(!entry.panel&&(!enabled||!pets.includes(node)))detachPet(node,entry);
        if(!enabled){stopEffect();return;}
        for(const pet of pets) {
            const entry=attachPet(pet),fighter=pet.closest('.fighter'),stage=pet.closest('#battle-stage');
            let mood=pet.dataset.mood||'idle';if(mood==='lose')mood='defeat';
            if(mood==='attack'&&stage?.querySelector('#fighter-opponent .meter')?.getAttribute('aria-valuenow')==='0')mood='ultimate';
            if(mood==='hit'&&fighter?.querySelector('.meter')?.getAttribute('aria-valuenow')==='0')mood='defeat';
            if(entry.mood!==mood) {
                // Legacy idle at 1.6 s must not cut off the three-second horse finale.
                if(mood==='idle'&&['ultimate','defeat'].includes(entry.controller.state))continue;
                entry.mood=mood;entry.controller.play(mood);
                if(stage&&['attack','ultimate'].includes(mood))playEffect(stage,{ultimate:mood==='ultimate',direction:fighter.classList.contains('right')?-1:1});
            }
        }
    }
    let queued=false;
    function queueScan(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;scan();});}
    function boot(){const observer=new MutationObserver(queueScan);observer.observe(document.querySelector('#app')||document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-mood','class','aria-valuenow']});scan();}
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stopAll();});
    media.addEventListener('change',stopAll);
    window.addEventListener('pagehide',stopAll);
    window.addEventListener('storage',event=>{if(event.key===STORAGE_KEY){enabled=event.newValue==='horse';scan();}});
    window.addEventListener('5bmath:arena-appearance',event=>{if(event.detail?.appearance&&event.detail.appearance!=='horse'){enabled=false;scan();}});
    window.HorseAnimation=Object.freeze({preload,create,hit,notifyVictim,setEnabled,get enabled(){return enabled;},stop:stopAll,get activeCount(){return [...controllers].filter(c=>c.running).length+(effect?.frame?1:0);}});
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
