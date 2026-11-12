/* 5BMath — Cua biển / Song Càng Khóa Sóng. Canvas presentation only. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.ArenaCrabAnimation) return;
    const settings = {asset:'arena-art/cua-bien-poses.webp',frames:[
        {left:66,top:82,width:201,height:172},{left:371,top:71,width:198,height:183},
        {left:662,top:101,width:206,height:154},{left:963,top:88,width:200,height:166},
        {left:70,top:381,width:208,height:171},{left:375,top:382,width:211,height:168},
        {left:665,top:387,width:199,height:162},{left:965,top:384,width:211,height:163},
        {left:66,top:682,width:207,height:172},{left:370,top:674,width:200,height:178},
        {left:662,top:685,width:208,height:168},{left:968,top:679,width:205,height:173},
        {left:66,top:969,width:204,height:179},{left:371,top:973,width:193,height:173},
        {left:662,top:970,width:202,height:177},{left:966,top:979,width:206,height:171},
    ]};
    const duration = {idle:0,attack:850,hit:850,win:1100,lose:1800,ultimate:3000};
    const poses = {idle:[0],attack:[0,4,5,6,7,0],hit:[13,14,0],win:[12],lose:[14,15]};
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set(), timers = new Set(), visuals = new Set();
    const actorOwners = new WeakMap(), victimOwners = new WeakMap();
    let announcementOwner=null;
    let atlas=null, loading=null, observer=null, queued=false, active=true, generation=0;
    const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,n));
    const lerp = (a,b,p) => a+(b-a)*p;
    const ease = p => {p=clamp(p);return p*p*(3-2*p);};
    const crab = node => node?.matches?.('.battle-pet.crab,.battle-pet.cua-bien') ? node : node?.querySelector?.('.battle-pet.crab,.battle-pet.cua-bien');
    const moodName = mood => ({hurt:'hit',defeat:'lose',victory:'win'}[mood] || (duration[mood]!==undefined?mood:'idle'));

    function later(callback,delay,action) {
        const timer=setTimeout(()=>{timers.delete(timer);action?.timers.delete(timer);callback();},delay);
        timers.add(timer);action?.timers.add(timer);return timer;
    }
    function load() {
        if (loading) return loading;
        loading=new Promise(resolve=>{
            const image=new Image();
            image.onload=()=>{atlas=image;resolve(image);};
            image.onerror=()=>{loading=null;resolve(null);};
            image.src=new URL(settings.asset,document.baseURI).href;
        });
        return loading;
    }
    function frame(index) {
        if (settings.frames?.[index]) {
            const f=settings.frames[index];
            return {x:f.left??f.x,y:f.top??f.y,w:f.width??f.w,h:f.height??f.h};
        }
        const col=index%4,row=Math.floor(index/4),w=atlas.naturalWidth,h=atlas.naturalHeight;
        const x=Math.round(col*w/4),y=Math.round(row*h/4);
        return {x,y,w:Math.round((col+1)*w/4)-x,h:Math.round((row+1)*h/4)-y};
    }
    function sprite(ctx,index,x,y,size,{alpha=1,flip=false,rotation=0}={}) {
        if (!atlas) return;
        const f=frame(index),scale=size/Math.max(f.w,f.h);
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(atlas,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);
        ctx.restore();
    }
    function pose(mood,time) {
        if (mood==='ultimate') {
            const t=time/1000;
            return t<.65 ? Math.min(3,Math.floor(t/.65*4))
                : t<.95 ? 3 : t<1.4 ? 4+Math.min(3,Math.floor((t-.95)/.45*4))
                : t<1.9 ? 8+Math.min(3,Math.floor((t-1.4)/.5*4)) : 12;
        }
        const list=poses[mood]||poses.idle;
        return list[Math.min(list.length-1,Math.floor(clamp(time/(duration[mood]||1))*list.length))];
    }
    function fit(canvas) {
        const box=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);
        const width=Math.max(1,Math.round(box.width*dpr)),height=Math.max(1,Math.round(box.height*dpr));
        if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
        return {width,height};
    }
    function paintPet(entry,time) {
        const {width,height}=fit(entry.canvas),ctx=entry.ctx,mood=entry.mood;
        ctx.clearRect(0,0,width,height);
        let x=width/2,y=height/2,rotation=0;
        const p=clamp(time/(duration[mood]||1));
        if(!reduced.matches){
            if(mood==='attack')x+=Math.sin(p*Math.PI)*width*.11;
            if(mood==='hit'){x+=Math.sin(p*Math.PI*5)*(1-p)*width*.025;rotation=Math.sin(p*Math.PI)*.045;}
            if(mood==='lose')y+=ease(p)*height*.035;
            if(mood==='win')y-=Math.sin(p*Math.PI)*height*.04;
        }
        const index=pose(mood,reduced.matches?(duration[mood]||0):time);
        sprite(ctx,index,x,y,Math.min(width,height)*.98,{rotation});
        entry.canvas.dataset.mode=mood;entry.canvas.dataset.pose=String(index);entry.canvas.dataset.time=String(Math.round(time));
    }
    function cancelPet(entry) {cancelAnimationFrame(entry.raf);entry.raf=0;}
    function playPet(entry,mood,force=false) {
        mood=moodName(mood);
        if(entry.mood===mood&&!force)return;
        cancelPet(entry);entry.mood=mood;entry.started=performance.now();
        if(!atlas)return;
        const span=duration[mood];
        paintPet(entry,0);
        if(!span||reduced.matches||document.hidden){paintPet(entry,span);return;}
        function tick(now) {
            entry.raf=0;
            if(!active||document.hidden||!entry.node.isConnected)return;
            const elapsed=clamp(now-entry.started,0,span);
            paintPet(entry,elapsed);
            if(elapsed<span)entry.raf=requestAnimationFrame(tick);
        }
        entry.raf=requestAnimationFrame(tick);
    }
    function mount(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='arena-crab-sprite';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mood:null,raf:0};pets.set(node,entry);
        load().then(image=>{
            if(!image||!active||!node.isConnected||!pets.has(node))return;
            node.append(canvas);node.classList.add('crab-canvas-ready');
            playPet(entry,node.dataset.mood||'idle',true);
        });
        return entry;
    }
    function play(node,mood,{force=true,delay=0}={}) {
        node=crab(node);if(!node||!active)return false;
        if(delay){later(()=>{if(node.isConnected)play(node,mood,{force});},delay);return true;}
        mood=moodName(mood);if(node.dataset.mood!==mood)node.dataset.mood=mood;
        const entry=mount(node);if(entry)playPet(entry,mood,force);return true;
    }
    function settle(node,mood,animate) {
        if(!node?.isConnected)return;
        const entry=pets.get(node);
        if(animate&&crab(node)){play(node,mood);return;}
        node.dataset.mood=mood;
        if(entry){
            cancelPet(entry);entry.mood=mood;entry.started=performance.now();
            if(atlas)paintPet(entry,duration[mood]||0);
        }
    }
    function finishVisual(action,{animate=false}={}) {
        if(!visuals.delete(action))return;
        for(const timer of action.timers){clearTimeout(timer);timers.delete(timer);}action.timers.clear();
        const {actor,victim,final,sourceMood,victimMood}=action;
        if(actorOwners.get(actor)===action){
            actorOwners.delete(actor);
            if(actor.dataset.mood===sourceMood)settle(actor,final?'win':'idle',animate);
        }
        if(victim&&victimOwners.get(victim)===action){
            victimOwners.delete(victim);
            // A later attacker owns its own spell and hit feedback.
            if(victim.dataset.spell==='crab'){
                victim.classList.remove('taking-hit');delete victim.dataset.spell;
                const pet=victim.querySelector('.battle-pet');
                if(victimMood&&pet?.dataset.mood===victimMood)settle(pet,final?'lose':'idle',animate);
            }
        }
        if(announcementOwner===action){
            announcementOwner=null;
            const label=action.announcement;
            clearAnnouncement(label);
        }
        for(const flight of [...flights])if(flight.action===action)flight.finish();
    }
    function clearAnnouncement(label) {
        if(label?.dataset.crab!=='true')return;
        if(['','✦ Càng Cua','✦ SONG CÀNG KHÓA SÓNG'].includes(label.textContent))label.textContent='';
        delete label.dataset.crab;
    }
    function sync(root=document) {
        if(!active)return;
        for(const [node,entry]of pets){if(!node.isConnected){cancelPet(entry);pets.delete(node);}}
        const nodes=[...root.querySelectorAll('.battle-pet.crab,.battle-pet.cua-bien')];
        if(root.matches?.('.battle-pet.crab,.battle-pet.cua-bien'))nodes.unshift(root);
        for(const node of nodes){const entry=mount(node);if(entry)playPet(entry,node.dataset.mood||'idle');}
        for(const flight of [...flights])if(!flight.stage.isConnected)flight.finish();
        for(const action of [...visuals])if(!action.actor.isConnected||(action.victim&&!action.victim.isConnected))finishVisual(action);
    }
    function scheduleSync() {if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();});}
    function claw(ctx,x,y,size,side,closure,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.scale(side,1);ctx.rotate(lerp(-.35,.1,closure));ctx.globalAlpha*=alpha;
        ctx.shadowColor='#fff2c4';ctx.shadowBlur=size*.1;ctx.lineWidth=Math.max(1,size*.022);
        ctx.fillStyle='#ffbe73';ctx.strokeStyle='#fff9ed';
        ctx.beginPath();ctx.moveTo(-size*.32,size*.25);
        ctx.bezierCurveTo(-size*.6,-size*.03,-size*.48,-size*.62,size*.08,-size*.62);
        ctx.quadraticCurveTo(size*.38,-size*.5,size*.35,-size*.18);
        ctx.lineTo(size*.02,-size*.38);ctx.lineTo(-size*.06,-size*.04);
        ctx.lineTo(size*.24,-size*.12);ctx.quadraticCurveTo(size*.45,size*.08,size*.22,size*.32);
        ctx.quadraticCurveTo(-size*.02,size*.52,-size*.32,size*.25);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
    }
    function star(ctx,x,y,r,rotation=0) {
        ctx.beginPath();
        for(let i=0;i<10;i++){const a=i*Math.PI/5-Math.PI/2+rotation,rr=i%2?r*.42:r;i?ctx.lineTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr):ctx.moveTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr);}
        ctx.closePath();ctx.fill();
    }
    // Pure drawing function, also suitable for the standalone Canvas review.
    // t is in seconds; positions and sizes are in the caller's canvas units.
    function renderUltimate(ctx,t,W,H,options={}) {
        t=clamp(t,0,3);
        const from=options.from||{x:W*.23,y:H*.65},to=options.to||{x:W*.77,y:H*.55};
        const size=options.size||Math.min(W*.25,H*.5),flip=options.flip??to.x<from.x;
        const wind=ease(t/.65),dash=ease((t-.95)/.6),back=ease((t-1.9)/.3);
        const stop={x:lerp(from.x,to.x,.57),y:lerp(from.y,to.y,.57)};
        let x=t<.95?from.x+(reduced.matches?0:Math.sin(wind*Math.PI*5)*size*.025):t<1.9?lerp(from.x,stop.x,dash):lerp(stop.x,from.x,back);
        let y=t<1.9?lerp(from.y,stop.y,dash):lerp(stop.y,from.y,back);
        const index=pose('ultimate',t*1000);
        if(t>=.95&&t<1.65&&!reduced.matches){
            for(let k=1;k<=3;k++){
                const past=ease((t-.95-k*.065)/.6);
                sprite(ctx,4+k,lerp(from.x,stop.x,past),lerp(from.y,stop.y,past),size,{alpha:.11+(3-k)*.055,flip});
            }
        }
        if(t>=1.13&&t<1.93){
            const p=ease((t-1.13)/.62),radius=size*(.38+.16*p),alpha=1-clamp((t-1.83)/.1);
            ctx.save();ctx.globalAlpha=alpha;ctx.strokeStyle='#6ad6e8';ctx.lineWidth=Math.max(1,size*.018);
            for(let i=0;i<3;i++){
                const gap=(1-p)*size*(.5+i*.11);
                ctx.beginPath();ctx.ellipse(to.x,to.y,radius+gap,radius*.75+gap*.45,0,Math.PI*.08+i*.19,Math.PI*1.7+i*.19);ctx.stroke();
            }
            ctx.fillStyle='#a2e6f32b';ctx.beginPath();ctx.arc(to.x,to.y,radius,0,Math.PI*2);ctx.fill();
            ctx.strokeStyle='#c8f4ff';ctx.lineWidth=Math.max(1,size*.014);ctx.stroke();
            ctx.strokeStyle='#fff9ed';ctx.beginPath();ctx.arc(to.x-radius*.18,to.y-radius*.1,radius*.66,Math.PI*1.08,Math.PI*1.48);ctx.stroke();ctx.restore();
            const gap=size*(.95-.55*p);
            claw(ctx,to.x-gap,to.y-size*.03,size*.87,1,p,alpha);
            claw(ctx,to.x+gap,to.y-size*.03,size*.87,-1,p,alpha);
        }
        if(t>=1.75&&t<2.45){
            const p=clamp((t-1.75)/.7);ctx.save();ctx.globalAlpha=1-p;
            ctx.strokeStyle='#a2e6f3';ctx.lineWidth=Math.max(1,size*.013);ctx.beginPath();ctx.arc(to.x,to.y,size*(.35+p*.65),0,Math.PI*2);ctx.stroke();
            for(let k=0;k<14;k++){
                const a=k*Math.PI*2/14,r=size*(.35+p*.65),sx=to.x+Math.cos(a)*r,sy=to.y+Math.sin(a)*r*.8;
                ctx.fillStyle=k%2?'#ffbe73':'#fff9ed';star(ctx,sx,sy,size*(.035*(1-p)+.009),a+p);
            }ctx.restore();
        }
        if(t>=1.9&&!reduced.matches)y-=Math.sin(clamp((t-1.9)/.65)*Math.PI)*size*.09;
        sprite(ctx,index,x,y,size,{flip});
        const nameVisible=t>=.65&&t<1.78;
        if(nameVisible&&options.showName!==false){
            const text='SONG CÀNG KHÓA SÓNG',font=Math.max(11,Math.min(34,W*.039));
            ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const bw=Math.min(W-16,ctx.measureText(text).width+28),bh=font+20,by=H*.22;
            ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;
            ctx.beginPath();ctx.roundRect((W-bw)/2,by-bh/2,bw,bh,11);ctx.fill();ctx.stroke();
            ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,by,W-34);ctx.restore();
        }
        return {time:t,pose:index,nameVisible,attackStarted:t>=.95,impact:t>=1.75,flourish:t>=1.9,finished:t>=3};
    }
    function ultimate({source,victim,action}) {
        const actor=crab(source),stage=source?.closest('.battle-stage');
        if(!actor||!stage||!victim)return false;
        const ticket=generation;
        load().then(image=>{
            if(!image||!active||ticket!==generation||!stage.isConnected||document.hidden||(action&&actorOwners.get(actor)!==action))return;
            for(const flight of [...flights])if(flight.stage===stage)flight.finish();
            const canvas=document.createElement('canvas');canvas.className='arena-crab-ultimate';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const box=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),b=(victim.querySelector('.battle-pet')||victim).getBoundingClientRect();
            const W=box.width,H=box.height,dpr=Math.min(devicePixelRatio||1,1.5);
            canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const from={x:a.left-box.left+a.width/2,y:a.top-box.top+a.height/2};
            const to={x:b.left-box.left+b.width/2,y:b.top-box.top+b.height/2};
            let raf=0,done=false;const started=performance.now();
            const flight={stage,action,finish:()=>{
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();
                actor.classList.remove('crab-ultimate-hidden');stage.classList.remove('crab-ultimate-active');flights.delete(flight);
            }};
            stage.append(canvas);actor.classList.add('crab-ultimate-hidden');stage.classList.add('crab-ultimate-active');flights.add(flight);
            function draw(now) {
                raf=0;if(!active||document.hidden||!stage.isConnected){flight.finish();return;}
                const t=Math.min((now-started)/1000,3);
                ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                const state=renderUltimate(ctx,reduced.matches?1.75:t,W,H,{from,to,size:a.width,flip:to.x<from.x,showName:false});
                canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.pose=String(state.pose);canvas.dataset.impact=String(state.impact);
                if(t>=3){flight.finish();return;}
                if(!reduced.matches)raf=requestAnimationFrame(draw);
            }
            draw(started);
            if(reduced.matches)later(flight.finish,3000,action);
        });return true;
    }
    function hit({source,victim,final=false}={}) {
        if(!active)return false;
        sync();const actor=crab(source),target=crab(victim);
        if(!actor){if(target)play(target,final?'lose':'hit');return false;}
        const previous=actorOwners.get(actor);if(previous)finishVisual(previous);
        const announcement=document.querySelector('#spell-announcement');
        const action={actor,victim,final,sourceMood:final?'ultimate':'attack',victimMood:null,announcement,timers:new Set()};
        visuals.add(action);actorOwners.set(actor,action);if(victim)victimOwners.set(victim,action);
        play(actor,final?'ultimate':'attack');
        announcementOwner=action;
        if(announcement){announcement.dataset.crab='true';announcement.textContent=final?'':'✦ Càng Cua';}
        if(final){
            ultimate({source,victim,action});
            later(()=>{if(announcementOwner===action&&announcement?.isConnected&&announcement.dataset.crab==='true')announcement.textContent='✦ SONG CÀNG KHÓA SÓNG';},650,action);
        }
        const impact=()=>{
            if(!visuals.has(action)||!victim?.isConnected||victimOwners.get(victim)!==action)return;
            victim.dataset.spell='crab';victim.classList.add('taking-hit');
            const targetPet=victim.querySelector('.battle-pet');
            action.victimMood=final?'lose':'hit';
            if(target)play(target,action.victimMood);else if(targetPet)targetPet.dataset.mood=action.victimMood;
        };
        if(final)later(impact,1750,action);else impact();
        later(()=>finishVisual(action,{animate:true}),final?3000:900,action);
        return true;
    }
    function stop() {
        generation++;for(const entry of pets.values())cancelPet(entry);
        for(const flight of [...flights])flight.finish();
        for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const action of [...visuals])finishVisual(action);
        const announcement=document.querySelector('#spell-announcement');
        clearAnnouncement(announcement);
    }
    function configure(options={}) {
        const changed=options.asset&&options.asset!==settings.asset;
        if(options.asset)settings.asset=options.asset;if(options.frames)settings.frames=options.frames;
        if(changed){stop();atlas=null;loading=null;}
        for(const entry of pets.values())load().then(image=>{if(image&&active&&entry.node.isConnected)playPet(entry,entry.node.dataset.mood||'idle',true);});
    }
    function destroy() {
        active=false;observer?.disconnect();stop();
        for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('crab-canvas-ready');}pets.clear();
    }
    const inspect=()=>({loaded:Boolean(atlas),pets:[...pets.values()].map(e=>({mood:e.mood,pose:Number(e.canvas.dataset.pose),time:Number(e.canvas.dataset.time),running:Boolean(e.raf),connected:e.node.isConnected})),flights:flights.size,visuals:visuals.size,timers:timers.size,reducedMotion:reduced.matches});
    window.ArenaCrabAnimation={mountManaged(root=document){active=true;sync(root);},configure,sync,play,hit,stop,destroy,ready:load,renderUltimate,drawSprite:sprite,inspect};
    function start(){observer=new MutationObserver(scheduleSync);observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});sync();}
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else for(const entry of pets.values())playPet(entry,entry.node.dataset.mood||'idle',true);});
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();for(const entry of pets.values())if(atlas)paintPet(entry,duration[entry.mood]||0);});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())if(atlas)playPet(entry,entry.node.dataset.mood||'idle',true);});
})();
