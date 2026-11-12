/* 5BMath — Mèo / Ảo Ảnh Móng Mèo. Presentation only: never changes a battle. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.ArenaCatAnimation) return;
    const settings = {
        asset:'arena-art/meo-poses.webp',
        frames:[
            {left:103,top:9,width:211,height:244},{left:439,top:51,width:249,height:203},
            {left:823,top:84,width:262,height:170},{left:1199,top:23,width:246,height:227},
            {left:59,top:309,width:298,height:190},{left:442,top:267,width:287,height:206},
            {left:814,top:276,width:269,height:222},{left:1187,top:272,width:281,height:227},
            {left:77,top:530,width:245,height:225},{left:453,top:513,width:233,height:241},
            {left:828,top:544,width:250,height:209},{left:1251,top:513,width:193,height:241},
            {left:102,top:772,width:209,height:237},{left:467,top:770,width:211,height:239},
            {left:839,top:802,width:211,height:207},{left:1217,top:814,width:214,height:192},
        ],
        modes:{idle:[0],windup:[0,1,2,3],attack:[3,4,6,7],strike:[6,7],hit:[8,9,10],win:[11,12,13],lose:[0,14,15]},
    };
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set();
    const durations = {attack:900,hit:1000,win:1200,lose:2200,ultimate:3000};
    let atlas, loading, observer, queued=false, active=true, generation=0, pendingUntilAt=0;
    const clamp = (n,min=0,max=1) => Math.min(max,Math.max(min,n));
    const lerp = (a,b,p) => a+(b-a)*p;
    const ease = p => {p=clamp(p);return p*p*(3-2*p);};
    const cat = node => node?.matches?.('.battle-pet.cat') ? node : node?.querySelector?.('.battle-pet.cat');

    function load() {
        if (loading) return loading;
        loading = new Promise(resolve => {
            const image = new Image();
            image.onload = () => {atlas=image;resolve(image);};
            image.onerror = () => {loading=null;resolve(null);};
            image.src = new URL(settings.asset,document.baseURI).href;
        });
        return loading;
    }
    function frame(index) {
        if (settings.frames?.[index]) {
            const f=settings.frames[index];
            return {x:f.left??f.x,y:f.top??f.y,w:f.width,h:f.height};
        }
        const x=index%4,y=Math.floor(index/4),w=atlas.naturalWidth,h=atlas.naturalHeight;
        return {x:Math.round(x*w/4),y:Math.round(y*h/4),w:Math.round((x+1)*w/4)-Math.round(x*w/4),h:Math.round((y+1)*h/4)-Math.round(y*h/4)};
    }
    function sprite(ctx,index,x,y,size,{alpha=1,flip=false,rotation=0}={}) {
        if (!atlas) return;
        const f=frame(index),scale=size/Math.max(f.w,f.h);
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(atlas,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);
        ctx.restore();
    }
    function pose(mode,time) {
        const list=settings.modes[mode]||settings.modes.idle;
        const duration=durations[mode]||1;
        return list[Math.min(list.length-1,Math.floor(clamp(time/duration)*list.length))]??0;
    }
    function resizePet(entry) {
        const size=Math.max(1,Math.ceil(entry.node.getBoundingClientRect().width));
        const pixels=Math.min(512,Math.ceil(size*Math.min(devicePixelRatio||1,2)));
        if(entry.canvas.width!==pixels){entry.canvas.width=pixels;entry.canvas.height=pixels;}
    }
    function paintPet(entry,time) {
        resizePet(entry);
        const {ctx,canvas,mood}=entry,size=canvas.width;
        ctx.clearRect(0,0,size,size);
        let x=size/2,y=size/2,rotation=0;
        if(!reduced.matches){
            const p=clamp(time/(durations[mood]||1));
            if(mood==='attack'){x+=Math.sin(p*Math.PI)*size*.07;rotation=-Math.sin(p*Math.PI)*.06;}
            if(mood==='hit'){x+=Math.sin(p*Math.PI*5)*(1-p)*size*.035;rotation=Math.sin(p*Math.PI)*.04;}
            if(mood==='lose')y+=ease(p)*size*.035;
            if(mood==='win')y-=Math.sin(p*Math.PI)*size*.06;
        }
        const index=pose(mood,reduced.matches?(durations[mood]||0):time);
        entry.canvas.dataset.mode=mood;entry.canvas.dataset.pose=String(index);entry.canvas.dataset.time=String(Math.round(time));
        sprite(ctx,index,x,y,size*.96,{rotation});
    }
    function cancelPet(entry) {
        if(entry.raf)cancelAnimationFrame(entry.raf);
        entry.raf=0;
    }
    function playPet(entry,mood,force=false) {
        if(entry.mood===mood&&!force)return;
        cancelPet(entry);entry.mood=mood;entry.started=performance.now();
        if(!atlas)return;
        paintPet(entry,0);
        if(reduced.matches||document.hidden||!durations[mood]){
            paintPet(entry,durations[mood]||0);return;
        }
        const tick=now=>{
            entry.raf=0;
            if(!entry.node.isConnected||document.hidden||!active)return;
            const elapsed=Math.min(now-entry.started,durations[mood]);
            paintPet(entry,elapsed);
            if(elapsed<durations[mood])entry.raf=requestAnimationFrame(tick);
        };
        entry.raf=requestAnimationFrame(tick);
    }
    function mount(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');
        canvas.className='arena-cat-sprite';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');
        if(!ctx)return null;
        const entry={node,canvas,ctx,mood:null,raf:0};
        pets.set(node,entry);
        load().then(image=>{
            if(!image||!node.isConnected||!pets.has(node))return;
            node.append(canvas);node.classList.add('cat-canvas-ready');
            playPet(entry,node.dataset.mood||'idle',true);
        });
        return entry;
    }
    function sync(root=document) {
        if(!active)return;
        for(const [node,entry]of pets){
            if(!node.isConnected){cancelPet(entry);pets.delete(node);}
        }
        const nodes=[...root.querySelectorAll('.battle-pet.cat')];
        if(root.matches?.('.battle-pet.cat'))nodes.unshift(root);
        for(const node of nodes){const entry=mount(node);if(entry)playPet(entry,node.dataset.mood||'idle');}
        for(const flight of flights)if(!flight.stage.isConnected)flight.finish();
    }
    function scheduleSync() {
        if(queued)return;queued=true;
        queueMicrotask(()=>{queued=false;sync();});
    }
    function drawClaws(ctx,x,y,size,progress,alpha,flip=false) {
        ctx.save();ctx.translate(x,y);ctx.scale(flip?-1:1,1);ctx.rotate(-.45);
        ctx.globalAlpha=alpha;ctx.lineCap='round';
        for(let i=-1;i<=1;i++){
            ctx.strokeStyle=i===0?'#fff9ed':'#ffbe73';ctx.lineWidth=Math.max(2,size*.025);
            ctx.beginPath();ctx.moveTo(i*size*.17-size*.25,-size*.35);
            ctx.quadraticCurveTo(i*size*.17+size*.12,0,i*size*.17+size*.25,size*(progress*.7-.35));ctx.stroke();
        }
        ctx.restore();
    }
    // Also used by the standalone Canvas demo. Time is in seconds; no DOM writes.
    function renderUltimate(ctx,t,W,H,options={}) {
        t=clamp(t,0,3);
        const from=options.from||{x:W*.23,y:H*.64},to=options.to||{x:W*.77,y:H*.48};
        const size=options.size||Math.min(W*.25,H*.53),flip=options.flip??to.x<from.x;
        const dash=ease((t-.95)/.65),back=ease((t-1.9)/.23);
        let x=t<1.9?lerp(from.x,to.x,dash):lerp(to.x,from.x,back);
        let y=t<1.9?lerp(from.y,to.y,dash)-Math.sin(dash*Math.PI)*size*.32:lerp(to.y,from.y,back);
        const windup=settings.modes.windup||settings.modes.idle;
        let index=t<.65?windup[Math.min(windup.length-1,Math.floor(t/.65*windup.length))]:t<.95?windup.at(-1):t<1.6?pose('attack',(t-.95)/.8*900):t<1.73?6:t<1.9?7:pose('win',(t-1.9)/1.1*1200);
        if(t>=.95&&t<1.75){
            // The original and two reflections form three evenly spaced points.
            const orbit=clamp((t-1.25)/.4),entry=ease((t-1.18)/.12),radius=size*.62*(1-ease((t-1.65)/.1));
            const angle=orbit*Math.PI*2+Math.atan2(from.y-to.y,from.x-to.x);
            for(let k=0;k<2;k++){
                const cloneAngle=angle+(k+1)*Math.PI*2/3;
                const cloneX=clamp(lerp(x,to.x+Math.cos(cloneAngle)*radius,entry),size*.52,W-size*.52),cloneY=clamp(lerp(y,to.y+Math.sin(cloneAngle)*radius*.58,entry),size*.52,H-size*.52);
                sprite(ctx,index,cloneX,cloneY,size*.9,{alpha:.23+k*.09,flip});
            }
            x=lerp(x,to.x+Math.cos(angle)*radius,entry);y=lerp(y,to.y+Math.sin(angle)*radius*.58,entry);
        }
        if(t>=1.48&&t<1.86){
            const p=clamp((t-1.48)/.27),radius=size*(.3+p*.24);
            ctx.save();ctx.strokeStyle='#ffbe73';ctx.lineWidth=Math.max(2,size*.015);ctx.globalAlpha=1-clamp((t-1.75)/.11);
            for(let k=0;k<3;k++){
                const a=-Math.PI*.7+k*Math.PI*2/3;
                ctx.beginPath();ctx.ellipse(to.x,to.y,radius,radius*.73,a,-Math.PI*.38,-Math.PI*.38+Math.PI*1.45*p);ctx.stroke();
            }ctx.restore();
        }
        if(t>=1.61&&t<2.1)drawClaws(ctx,to.x,to.y,size*1.1,clamp((t-1.61)/.28),1-clamp((t-1.86)/.24),flip);
        if(t>=1.75&&t<2.22){
            const p=(t-1.75)/.47;
            ctx.save();
            for(let k=0;k<12;k++){
                const angle=k*Math.PI/6,r=size*(.2+p*.8),sx=to.x+Math.cos(angle)*r,sy=to.y+Math.sin(angle)*r,star=size*.035*(1-p)+1;
                ctx.globalAlpha=1-p;ctx.fillStyle=k%2?'#ffbe73':'#fff9ed';ctx.beginPath();
                for(let i=0;i<8;i++){const a=i*Math.PI/4-Math.PI/2,rr=i%2?star*.3:star;i?ctx.lineTo(sx+Math.cos(a)*rr,sy+Math.sin(a)*rr):ctx.moveTo(sx+Math.cos(a)*rr,sy+Math.sin(a)*rr);}
                ctx.closePath();ctx.fill();
            }ctx.restore();
        }
        if(t>=1.9)y-=Math.sin(clamp((t-1.9)/.7)*Math.PI)*size*.13;
        sprite(ctx,index,clamp(x,size*.52,W-size*.52),clamp(y,size*.52,H-size*.52),size,{flip});
        const nameVisible=t>=.65&&t<=1.56;
        if(nameVisible){
            const text='ẢO ẢNH MÓNG MÈO',font=Math.max(12,Math.min(38,W*.043));
            ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const width=Math.min(W-20,ctx.measureText(text).width+30),height=font+22,top=H*.28;
            ctx.fillStyle='#1f6248f5';ctx.beginPath();ctx.roundRect((W-width)/2,top-height/2,width,height,12);ctx.fill();
            ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,top,W-38);ctx.restore();
        }
        return {time:t,pose:index,nameVisible,attackStarted:t>=.95,impact:t>=1.75,flourish:t>=1.9,finished:t>=3};
    }
    function ultimate({source,victim}) {
        const actor=cat(source),stage=source?.closest('#battle-stage');
        if(!actor||!stage||!victim)return false;
        const duration=3000;
        if(reduced.matches||document.hidden){
            actor.dataset.mood='win';
            const target=cat(victim);if(target)target.dataset.mood='lose';
            const label=stage.querySelector('#spell-announcement');if(label)label.textContent='✦ Ảo Ảnh Móng Mèo';
            return true;
        }
        const ticket=generation;
        pendingUntilAt=performance.now()+duration;
        load().then(image=>{
            if(!image||!stage.isConnected||document.hidden||ticket!==generation)return;
            for(const flight of [...flights])if(flight.stage===stage)flight.finish();
            const canvas=document.createElement('canvas');canvas.className='arena-cat-ultimate';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const bounds=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),v=(victim.querySelector('.battle-pet')||victim).getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5);
            canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const from={x:a.left-bounds.left+a.width/2,y:a.top-bounds.top+a.height/2};
            const to={x:v.left-bounds.left+v.width/2,y:v.top-bounds.top+v.height/2};
            const flip=to.x<from.x,size=a.width,started=performance.now(),announcement=stage.querySelector('#spell-announcement');
            pendingUntilAt=started+duration;
            let raf=0,done=false,targetHit=false;
            const flight={stage,finish:()=>{
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();actor.classList.remove('cat-ultimate-hidden');stage.classList.remove('cat-ultimate-active');
                if(announcement?.textContent==='✦ Ảo Ảnh Móng Mèo')announcement.textContent='';
                announcement?.classList.remove('cat-spell-accessible');
                if(actor.isConnected&&actor.dataset.mood==='ultimate'){actor.dataset.mood='idle';const entry=pets.get(actor);if(entry)playPet(entry,'idle',true);}
                flights.delete(flight);
            }};
            stage.append(canvas);actor.classList.add('cat-ultimate-hidden');stage.classList.add('cat-ultimate-active');flights.add(flight);
            function draw(now) {
                raf=0;
                if(!stage.isConnected||document.hidden||!active){flight.finish();return;}
                const t=Math.min((now-started)/1000,3);
                ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                const state=renderUltimate(ctx,t,W,H,{from,to,size,flip});
                if(state.impact&&!targetHit){targetHit=true;const target=cat(victim);if(target)target.dataset.mood='lose';}
                if(state.nameVisible&&announcement&&!announcement.classList.contains('cat-spell-accessible')){announcement.textContent='✦ Ảo Ảnh Móng Mèo';announcement.classList.add('cat-spell-accessible');}
                canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.pose=String(state.pose);canvas.dataset.nameVisible=String(state.nameVisible);canvas.dataset.impact=String(state.impact);
                if(t>=3){flight.finish();return;}
                raf=requestAnimationFrame(draw);
            }
            raf=requestAnimationFrame(draw);
            // The result route may remove the stage; the observer releases it too.
            flight.endsAt=started+duration;
        });
        return true;
    }
    function hit({source,victim,final=false}={}) {
        if(!active)return false;
        sync();
        const actor=cat(source),target=cat(victim);
        if(!actor)return false;
        if(target&&!final){target.dataset.mood='hit';const entry=mount(target);if(entry)playPet(entry,'hit',true);}
        actor.dataset.mood=final?'ultimate':'attack';
        if(final)return ultimate({source,victim});
        const entry=mount(actor);if(entry)playPet(entry,'attack',true);
        return true;
    }
    function stop() {
        generation++;pendingUntilAt=0;
        for(const entry of pets.values())cancelPet(entry);
        for(const flight of [...flights])flight.finish();
    }
    function configure(options={}) {
        const changed=options.asset&&options.asset!==settings.asset;
        if(options.asset)settings.asset=options.asset;
        if(options.frames)settings.frames=options.frames;
        if(options.modes)settings.modes={...settings.modes,...options.modes};
        if(changed){atlas=null;loading=null;}
        for(const entry of pets.values())load().then(image=>{if(image&&entry.node.isConnected)playPet(entry,entry.node.dataset.mood||'idle',true);});
    }
    function destroy() {
        active=false;observer?.disconnect();stop();
        for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('cat-canvas-ready');}
        pets.clear();
    }
    const inspect=()=>({loaded:Boolean(atlas),pets:[...pets.values()].map(e=>({mood:e.mood,pose:Number(e.canvas.dataset.pose),time:Number(e.canvas.dataset.time),running:Boolean(e.raf),connected:e.node.isConnected})),flights:[...flights].map(f=>({connected:f.stage.isConnected,endsAt:f.endsAt})),reducedMotion:reduced.matches});
    const pendingUntil=()=>Date.now()+Math.max(0,pendingUntilAt-performance.now());
    window.ArenaCatAnimation={mountManaged(root=document){active=true;sync(root);},configure,sync,hit,stop,destroy,ready:load,renderUltimate,drawSprite:sprite,inspect,pendingUntil};
    function start() {
        observer=new MutationObserver(scheduleSync);
        observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});sync();
    }
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{
        if(document.hidden)stop();else for(const entry of pets.values())playPet(entry,entry.node.dataset.mood||'idle',true);
    });
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();for(const entry of pets.values())if(atlas)paintPet(entry,durations[entry.mood]||0);});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())if(atlas)playPet(entry,entry.node.dataset.mood||'idle',true);});
})();
