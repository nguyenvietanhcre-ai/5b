/* 5BMath — Cá heo / Sóng Âm Cầu Vồng. Canvas presentation only. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.ArenaDolphin) return;
    const settings = {
        assets:{ultimate:'arena-art/ca-heo-v1/poses.webp',actions:'arena-art/ca-heo-v1/actions.webp'},
        frames:{},
        modes:{idle:[0],attack:[1,2,4,5,6,7],hit:[8,9,10,11],lose:[12,13,14,15],win:[12,13,14,15]},
    };
    const durations={idle:0,attack:900,hit:900,lose:2200,win:1100,ultimate:3000};
    const colours=['#ffbe73','#ffe59c','#8cddae','#70d8ea','#9aabef','#dfabe8'];
    const media=matchMedia('(prefers-reduced-motion: reduce)');
    const images=new Map(),pets=new Map(),flights=new Set(),timers=new Set();
    const clamp=(n,min=0,max=1)=>Math.max(min,Math.min(max,n));
    const ease=n=>{n=clamp(n);return n*n*(3-2*n);};
    const lerp=(a,b,n)=>a+(b-a)*n;
    let raf=0,observer=null,queued=false,generation=0,enabled=true;
    const dolphin=node=>node?.matches?.('.battle-pet.dolphin')?node:node?.querySelector?.('.battle-pet.dolphin');

    function sheet(kind) {
        if(images.has(kind))return images.get(kind).promise;
        const img=new Image(),record={img,ready:false};
        record.promise=new Promise(resolve=>{
            img.onload=()=>{record.ready=true;resolve(img);};
            img.onerror=()=>{images.delete(kind);resolve(null);};
        });
        images.set(kind,record);
        img.src=new URL(settings.assets[kind],document.baseURI).href;
        return record.promise;
    }
    function ready(){return Promise.all([sheet('actions'),sheet('ultimate')]).then(values=>values.every(Boolean));}
    function frame(kind,index) {
        const img=images.get(kind)?.img;if(!img)return null;
        const explicit=settings.frames[kind]?.[index];
        if(explicit)return {x:explicit.left??explicit.x,y:explicit.top??explicit.y,w:explicit.width,h:explicit.height};
        const col=index%4,row=Math.floor(index/4),w=img.naturalWidth,h=img.naturalHeight;
        const x=Math.round(col*w/4),y=Math.round(row*h/4);
        return {x,y,w:Math.round((col+1)*w/4)-x,h:Math.round((row+1)*h/4)-y};
    }
    function sprite(ctx,kind,index,x,y,size,{flip=false,rotation=0,alpha=1}={}) {
        const record=images.get(kind);if(!record?.ready)return;
        const f=frame(kind,index),scale=size/Math.max(f.w,f.h);
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(record.img,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);ctx.restore();
    }
    function bubble(ctx,x,y,r,colour,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle=colour+'30';ctx.strokeStyle=colour;
        ctx.lineWidth=Math.max(1,r*.08);ctx.beginPath();ctx.arc(x,y,Math.max(.1,r),0,Math.PI*2);ctx.fill();ctx.stroke();
        ctx.strokeStyle='#fff9ed';ctx.lineWidth=Math.max(1,r*.08);ctx.beginPath();ctx.arc(x-r*.12,y-r*.12,r*.57,Math.PI,Math.PI*1.58);ctx.stroke();ctx.restore();
    }
    function ring(ctx,x,y,size,angle,colour,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;ctx.strokeStyle=colour;
        ctx.lineWidth=Math.max(1.5,size*.06);ctx.beginPath();ctx.ellipse(0,0,size*.47,size,0,0,Math.PI*2);ctx.stroke();ctx.restore();
    }
    function poseFor(mode,elapsed) {
        const list=settings.modes[mode]||settings.modes.idle,p=clamp(elapsed/(durations[mode]||1));
        return list[Math.min(list.length-1,Math.floor(p*list.length))]??0;
    }
    function sizePet(record) {
        const side=Math.max(1,Math.min(640,Math.ceil(record.node.getBoundingClientRect().width*Math.min(devicePixelRatio||1,2))));
        if(record.canvas.width!==side){record.canvas.width=side;record.canvas.height=side;}
        return side;
    }
    function paintPet(record,elapsed) {
        const size=sizePet(record),ctx=record.ctx,mode=record.mode;
        const kind=mode==='win'?'ultimate':'actions',p=clamp(elapsed/(durations[mode]||1));
        let x=size*.5,y=size*.5,rotation=0;
        if(!media.matches){
            if(mode==='attack'){x+=Math.sin(p*Math.PI)*size*.095;y-=Math.sin(p*Math.PI)*size*.045;rotation=Math.sin(p*Math.PI)*-.08;}
            if(mode==='hit'){x+=Math.sin(p*Math.PI*6)*(1-p)*size*.035;rotation=Math.sin(p*Math.PI)*.07;}
            if(mode==='lose'){y+=ease(p)*size*.025;rotation=ease(p)*.06;}
            if(mode==='win')y-=Math.sin(p*Math.PI)*size*.065;
        }
        ctx.clearRect(0,0,size,size);const index=poseFor(mode,elapsed);
        sprite(ctx,kind,index,x,y,size*.94,{rotation});
        if(mode==='attack'&&p>.2&&p<.85)ring(ctx,size*.77,size*.46,size*(.06+p*.07),0,'#70d8ea',Math.sin((p-.2)/.65*Math.PI));
        if(mode==='hit'&&p<.65&&!media.matches){for(let i=0;i<3;i++)bubble(ctx,size*(.35+i*.15),size*(.16+Math.sin(p*10+i)*.02),size*.018,colours[i],1-p);}
        record.canvas.dataset.mode=mode;record.canvas.dataset.pose=String(index);record.canvas.dataset.time=String(Math.round(elapsed));
    }
    function requestTick(){if(!raf&&!document.hidden&&enabled&&!media.matches)raf=requestAnimationFrame(tick);}
    function tick(now) {
        raf=0;if(document.hidden||!enabled)return;
        let running=false;
        for(const [node,record]of pets){
            if(!node.isConnected){pets.delete(node);continue;}
            if(!record.running)continue;
            const elapsed=Math.min(durations[record.mode]||0,now-record.started);paintPet(record,elapsed);
            record.running=elapsed<(durations[record.mode]||0);
            if(!record.running&&(record.mode==='attack'||record.mode==='hit')){
                record.mode='idle';node.dataset.mood='idle';paintPet(record,0);
            }
            running ||=record.running;
        }
        for(const flight of [...flights]){flight.draw(now);running ||=flights.has(flight);}
        if(running)requestTick();
    }
    function mountPet(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='dolphin-pose-canvas';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const record={node,canvas,ctx,mode:null,started:0,running:false,ticket:0};pets.set(node,record);return record;
    }
    function play(node,mode='idle',{force=true}={}) {
        node=dolphin(node);if(!node||!enabled)return false;
        if(mode==='hurt')mode='hit';
        if(!(mode in durations))mode='idle';
        const record=mountPet(node);if(!record)return false;
        if(!force&&record.mode===mode)return true;
        record.mode=mode;record.running=false;node.dataset.mood=mode;
        const ticket=++record.ticket,epoch=generation;
        const kind=mode==='win'?'ultimate':'actions';
        sheet(kind).then(img=>{
            if(!img||!enabled||epoch!==generation||ticket!==record.ticket||!node.isConnected||pets.get(node)!==record)return;
            if(!canvasAttached(record)){node.append(record.canvas);node.classList.add('dolphin-ready');}
            record.started=performance.now();
            const elapsed=media.matches||document.hidden?durations[mode]||0:0;
            paintPet(record,elapsed);record.running=Boolean(durations[mode])&&!media.matches&&!document.hidden&&mode!=='ultimate';
            if(record.running)requestTick();
        });
        return true;
    }
    function canvasAttached(record){return record.canvas.parentNode===record.node;}

    // Reusable by the workshop demo. Time is in seconds, coordinates in CSS pixels.
    function renderUltimate(ctx,t,W,H,options={}) {
        t=clamp(t,0,3);
        const from=options.from||{x:W*.23,y:H*.64},to=options.to||{x:W*.77,y:H*.38};
        const size=options.size||Math.min(W*.3,H*.48),flip=options.flip??to.x<from.x;
        const angle=Math.atan2(to.y-from.y,to.x-from.x),u=clamp((t-.95)/.95);
        let x=from.x,y=from.y,rotation=0,index=0;
        if(t<.65){index=Math.min(3,Math.floor(t/.65*4));y+=Math.sin(t/.65*Math.PI)*size*.035;}
        else if(t<.95){index=4+Math.min(3,Math.floor((t-.65)/.3*4));y-=ease((t-.65)/.3)*size*.08;}
        else if(t<1.9){
            index=8+Math.min(3,Math.floor(u*4));x+=Math.sin(u*Math.PI)*(to.x-from.x)*.36;
            y-=Math.sin(u*Math.PI)*size*.82;
            rotation=(flip?-1:1)*ease((t-1.02)/.57)*Math.PI*2;
        }else{index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));y-=Math.sin(clamp((t-1.9)/.8)*Math.PI)*size*.2;}
        if(t<1.9){
            const wind=ease(t/.6),fade=1-ease((t-1.7)/.2);
            for(let i=0;i<3;i++)ring(ctx,from.x+(flip?-1:1)*size*(.25+i*.07),from.y-size*.05,size*(.07+i*.035)*wind,angle,colours[i+2],fade*(.4+i*.17));
        }
        if(t>=.95&&t<1.8){
            for(let i=0;i<6;i++){
                const p=(t-.95-i*.075)/.62;if(p<0||p>1)continue;
                ring(ctx,lerp(from.x,to.x,ease(p)),lerp(from.y,to.y,ease(p)),size*(.08+.14*p),angle,colours[i],Math.sin(p*Math.PI)*.9);
            }
        }
        if(t>=1.28&&t<1.82){
            const p=ease((t-1.28)/.47),bx=lerp(from.x,to.x,p),by=lerp(from.y,to.y,p);
            bubble(ctx,bx,by,size*(.09+.35*p),'#70d8ea',1-ease((t-1.75)/.07));
            for(let i=0;i<6;i++){const a=i*Math.PI/3+t*3;ring(ctx,bx,by,size*(.08+.29*p),a,colours[i],.5);}
        }
        if(t>=1.75&&t<2.6){
            const p=clamp((t-1.75)/.85);
            for(let i=0;i<18;i++){
                const a=i*Math.PI*2/18,r=size*(.12+p*.85);
                bubble(ctx,to.x+Math.cos(a)*r,to.y+Math.sin(a)*r*.75+p*p*size*.15,size*(.025+(i%3)*.012)*(1-p*.55),colours[i%6],1-p);
            }
        }
        if(t>=1.88&&t<2.5){
            const p=clamp((t-1.88)/.62);ctx.save();ctx.globalAlpha=1-p;ctx.strokeStyle='#a5e9ed';ctx.lineWidth=Math.max(1,size*.012);
            ctx.beginPath();ctx.ellipse(from.x,from.y+size*.31,size*(.18+p*.46),size*(.035+p*.08),0,0,Math.PI*2);ctx.stroke();ctx.restore();
        }
        sprite(ctx,'ultimate',index,x,y,size,{flip,rotation});
        const nameVisible=t>=.65&&t<1.62;
        if(nameVisible&&options.banner!==false){
            const text='SÓNG ÂM CẦU VỒNG',font=Math.max(11,Math.min(34,W*.045));
            ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const width=Math.min(W-16,ctx.measureText(text).width+26),height=font+20,cy=H*.2;
            ctx.fillStyle='#1f6248f2';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect((W-width)/2,cy-height/2,width,height,12);ctx.fill();ctx.stroke();
            ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,cy,W-30);ctx.restore();
        }
        return {time:t,pose:index,nameVisible,attackStarted:t>=.95,impact:t>=1.75,flourish:t>=1.9,finished:t>=3};
    }
    function finishFlight(flight) {
        if(!flights.has(flight))return;
        flights.delete(flight);flight.canvas.remove();flight.actor.classList.remove('dolphin-in-ultimate');
        if(![...flights].some(other=>other.stage===flight.stage))flight.stage.classList.remove('dolphin-ultimate-active');
        if(flight.actor.isConnected&&flight.actor.dataset.mood==='ultimate')play(flight.actor,'idle');
    }
    function ultimate(source,victim) {
        const actor=dolphin(source),stage=source?.closest?.('#battle-stage');
        if(!actor||!stage||!victim)return false;
        if(media.matches||document.hidden){play(actor,'win');return true;}
        const epoch=generation;actor.dataset.mood='ultimate';
        sheet('ultimate').then(img=>{
            if(!img||epoch!==generation||!actor.isConnected||!stage.isConnected||document.hidden||!enabled)return;
            for(const old of [...flights])if(old.stage===stage)finishFlight(old);
            const canvas=document.createElement('canvas');canvas.className='dolphin-ultimate-canvas';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const bounds=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),b=(victim.querySelector?.('.battle-pet')||victim).getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5);
            if(!W||!H)return;
            canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const from={x:a.left-bounds.left+a.width/2,y:a.top-bounds.top+a.height/2},to={x:b.left-bounds.left+b.width/2,y:b.top-bounds.top+b.height/2};
            const flight={canvas,stage,actor,started:performance.now(),impactShown:false,draw(now){
                if(!stage.isConnected||!actor.isConnected||document.hidden){finishFlight(flight);return;}
                const t=Math.min(3,(now-flight.started)/1000);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                const state=renderUltimate(ctx,t,W,H,{from,to,size:a.width*.96});
                canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.pose=String(state.pose);canvas.dataset.nameVisible=String(state.nameVisible);canvas.dataset.impact=String(state.impact);
                if(t>=1.75&&!flight.impactShown){flight.impactShown=true;feedback(victim,true);}
                if(t>=3)finishFlight(flight);
            }};
            stage.append(canvas);actor.classList.add('dolphin-in-ultimate');stage.classList.add('dolphin-ultimate-active');flights.add(flight);requestTick();
        });
        return true;
    }
    function reactOther(pet,mode) {
        if(!pet)return;
        if(pet.classList.contains('rabbit')&&typeof RabbitAnimation!=='undefined')RabbitAnimation.play(pet,mode);
        if(pet.classList.contains('gau')&&window.BearAnimation){const canvas=pet.querySelector('canvas[data-bear]');if(canvas)window.BearAnimation.play(canvas,mode==='lose'?'defeat':mode);}
        if(pet.classList.contains('tiger')&&typeof TigerAnimation!=='undefined')TigerAnimation.play(pet,mode==='lose'?'defeat':mode==='hit'?'hurt':mode);
        if(pet.classList.contains('lion')&&mode!=='idle'&&typeof ArenaLion!=='undefined'&&pet.closest('.fighter')?.id)ArenaLion.animate('#'+pet.closest('.fighter').id,'#__dolphin-no-source',mode==='lose');
    }
    function feedback(victim,final) {
        if(!victim?.isConnected)return;
        victim.dataset.spell='dolphin';victim.classList.remove('taking-hit');void victim.offsetWidth;victim.classList.add('taking-hit');
        const target=dolphin(victim);if(target)play(target,final?'lose':'hit');
        else{const pet=victim.querySelector?.('.battle-pet');if(pet){pet.dataset.mood=final?'lose':'hit';reactOther(pet,final?'lose':'hit');}}
        const epoch=generation;
        const timer=setTimeout(()=>{
            timers.delete(timer);if(epoch!==generation||!victim.isConnected)return;
            victim.classList.remove('taking-hit');
            const pet=victim.querySelector?.('.battle-pet');if(!final&&pet?.dataset.mood==='hit'){pet.dataset.mood='idle';reactOther(pet,'idle');}
        },final?1300:900);timers.add(timer);
    }
    function hit({source,victim,final=false}={}) {
        if(!enabled)return false;
        sync();const actor=dolphin(source),target=dolphin(victim);
        if(!actor){if(target)play(target,final?'lose':'hit');return false;}
        if(final){const accepted=ultimate(source,victim);if(media.matches||document.hidden)feedback(victim,true);return accepted;}
        play(actor,'attack');feedback(victim,false);return true;
    }
    function sync(root=document) {
        if(!enabled)return;
        for(const [node]of pets)if(!node.isConnected)pets.delete(node);
        const nodes=[...root.querySelectorAll('.battle-pet.dolphin')];if(root.matches?.('.battle-pet.dolphin'))nodes.unshift(root);
        for(const node of nodes){const mode=node.dataset.mood||'idle';if(pets.get(node)?.mode!==mode)play(node,mode,{force:false});}
        for(const flight of [...flights])if(!flight.stage.isConnected)finishFlight(flight);
    }
    function scheduleSync(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();});}
    function stop() {
        generation++;if(raf)cancelAnimationFrame(raf);raf=0;
        for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const record of pets.values()){record.running=false;record.ticket++;}
        for(const flight of [...flights])finishFlight(flight);
    }
    function destroy() {
        enabled=false;observer?.disconnect();observer=null;
        stop();for(const record of pets.values()){record.canvas.remove();record.node.classList.remove('dolphin-ready');}pets.clear();
    }
    function configure(options={}) {
        stop();if(options.assets){settings.assets={...settings.assets,...options.assets};images.clear();}
        if(options.frames)settings.frames=options.frames;
        if(options.modes)settings.modes={...settings.modes,...options.modes};
        for(const record of pets.values())record.mode=null;sync();
    }
    function mount(root=document){enabled=true;if(!observer){observer=new MutationObserver(scheduleSync);observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});}sync(root);}
    function inspect(){return {loaded:[...images].filter(([,r])=>r.ready).map(([kind])=>kind),running:Boolean(raf),enabled,reducedMotion:media.matches,pets:[...pets.values()].map(r=>({mode:r.mode,pose:Number(r.canvas.dataset.pose),time:Number(r.canvas.dataset.time),running:r.running,connected:r.node.isConnected})),flights:flights.size,timers:timers.size};}
    window.ArenaDolphin={ready,play,hit,sync,mount,stop,destroy,configure,renderUltimate,drawSprite:sprite,inspect};
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',()=>mount(),{once:true}):mount();
    document.addEventListener('visibilitychange',()=>{
        if(document.hidden){stop();return;}
        for(const record of pets.values())play(record.node,record.node.dataset.mood==='ultimate'?'idle':record.node.dataset.mood||'idle');
    });
    window.addEventListener('pagehide',destroy);
    window.addEventListener('resize',()=>{stop();for(const record of pets.values())play(record.node,record.node.dataset.mood==='ultimate'?'idle':record.node.dataset.mood||'idle');});
    media.addEventListener('change',()=>{stop();for(const record of pets.values())play(record.node,record.node.dataset.mood==='ultimate'?'win':record.node.dataset.mood||'idle');});
})();
