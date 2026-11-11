/* 5BMath — Mầm Sách. Canvas presentation only; never changes battle results. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.MamSachAnimation) return;
    const config = {asset:'arena-art/mam-sach/poses.webp',frames:null};
    const durations = {idle:0,attack:1.1,hit:1.05,lose:2.4,win:1.1,ultimate:3};
    const pets = new Map(), effects = new Set();
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,n));
    const ease = n => { n=clamp(n);return n*n*(3-2*n); };
    const lerp = (a,b,p) => a+(b-a)*p;
    const modeOf = mode => ({hurt:'hit',defeat:'lose',sad:'lose',victory:'win'}[mode] || mode || 'idle');
    const petOf = node => node?.matches?.('.battle-pet.sprout') ? node : node?.querySelector?.('.battle-pet.sprout');
    let atlas, loading, observer, queued=false, enabled=true, generation=0, pendingUntilAt=0;

    function ready() {
        if (!loading) loading = new Promise(resolve => {
            const img = new Image();
            img.onload = () => { atlas=img;resolve(img); };
            img.onerror = () => { loading=null;resolve(null); };
            img.src = new URL(config.asset,document.baseURI).href;
        });
        return loading;
    }
    function rect(index) {
        if (config.frames?.[index]) {
            const f=config.frames[index];
            return {x:f.left??f.x,y:f.top??f.y,w:f.width??f.w,h:f.height??f.h};
        }
        const col=index%4,row=Math.floor(index/4),W=atlas.naturalWidth,H=atlas.naturalHeight;
        const x=Math.round(col*W/4),y=Math.round(row*H/4);
        return {x,y,w:Math.round((col+1)*W/4)-x,h:Math.round((row+1)*H/4)-y};
    }
    function drawSprite(ctx,index,x,y,size,{facing=1,rotation=0,alpha=1}={}) {
        if (!atlas) return;
        const f=rect(index);
        // One scale for every pose prevents the book and body from pulsing.
        const maximum=config.frames ? Math.max(...config.frames.map(r=>Math.max(r.width??r.w,r.height??r.h)))
            : Math.max(atlas.naturalWidth,atlas.naturalHeight)/4;
        const scale=size/maximum;
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(facing<0?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(atlas,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);ctx.restore();
    }
    function sample(mode,time=0) {
        mode=modeOf(mode);time=clamp(time,0,durations[mode]||0);
        const p=durations[mode]?time/durations[mode]:0;
        let pose=0;
        if(mode==='ultimate') pose=time<.65 ? Math.min(1,Math.floor(time/.65*2))
            : time<.95 ? 2+Math.min(1,Math.floor((time-.65)/.3*2))
                : time<1.9 ? 4+Math.min(1,Math.floor((time-.95)/.95*2))
                    : 6+Math.min(1,Math.floor((time-1.9)/1.1*2));
        else if(mode==='attack')pose=8+Math.min(3,Math.floor(p*4));
        else if(mode==='hit')pose=12+Math.min(1,Math.floor(p*2));
        else if(mode==='lose')pose=14+Math.min(1,Math.floor(p*2));
        else if(mode==='win')pose=6+Math.min(1,Math.floor(p*2));
        return {mode,time,pose,progress:p,finished:time>=(durations[mode]||0)};
    }
    function star(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.globalAlpha*=alpha;ctx.fillStyle='#FFBE73';ctx.beginPath();
        for(let i=0;i<10;i++){const a=i*Math.PI/5-Math.PI/2,d=i%2?r*.42:r;i?ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d):ctx.moveTo(Math.cos(a)*d,Math.sin(a)*d);}
        ctx.closePath();ctx.fill();ctx.restore();
    }
    function page(ctx,x,y,size,rotation,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha*=alpha;
        ctx.fillStyle='#FFF9ED';ctx.strokeStyle='#FFBE73';ctx.lineWidth=Math.max(1,size*.035);
        ctx.beginPath();ctx.roundRect(-size*.34,-size*.48,size*.68,size*.96,size*.06);ctx.fill();ctx.stroke();
        ctx.strokeStyle='#1F6248';ctx.globalAlpha*=.55;
        for(let i=-1;i<=1;i++){ctx.beginPath();ctx.moveTo(-size*.19,i*size*.18);ctx.lineTo(size*.19,i*size*.18);ctx.stroke();}
        ctx.restore();
    }
    function renderPet(ctx,{time=0,mode='idle',x=192,y=192,size=360,facing=1,motion=true}={}) {
        const state=sample(mode,time),p=state.progress;
        let dx=0,dy=0,angle=0;
        if(motion){
            if(state.mode==='attack'){dy=-Math.sin(p*Math.PI)*size*.035;angle=-Math.sin(p*Math.PI)*.035;}
            if(state.mode==='hit'){dx=Math.sin(p*Math.PI*7)*(1-p)*size*.035;angle=Math.sin(p*Math.PI)*.055;}
            if(state.mode==='lose')dy=ease(p)*size*.025;
            if(state.mode==='win'||state.mode==='ultimate'&&time>=1.9)dy=-Math.sin(clamp((time-(state.mode==='ultimate'?1.9:0))/.8)*Math.PI)*size*.035;
        }
        drawSprite(ctx,state.pose,x+dx,y+dy,size,{facing,rotation:angle});
        if(state.mode==='hit'&&p<.8&&motion)for(let i=0;i<3;i++)star(ctx,x+(i-1)*size*.12,y-size*.4+Math.sin(p*9+i)*size*.025,size*.027,1-p);
        return state;
    }
    function banner(ctx,W,H,text) {
        const font=Math.max(12,Math.min(38,W*.042)),top=H*.18;
        ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
        const width=Math.min(W-18,ctx.measureText(text).width+32),height=font+20;
        ctx.fillStyle='#1F6248';ctx.strokeStyle='#FFBE73';ctx.lineWidth=2;ctx.beginPath();
        ctx.roundRect((W-width)/2,top-height/2,width,height,12);ctx.fill();ctx.stroke();
        ctx.fillStyle='#FFF9ED';ctx.fillText(text,W/2,top,W-38);ctx.restore();
    }
    function drawMath(ctx,symbol,x,y,size,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.font=`800 ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.lineWidth=Math.max(2,size*.10);ctx.strokeStyle='#FFF9ED';ctx.strokeText(symbol,x,y);ctx.fillStyle='#1F6248';ctx.fillText(symbol,x,y);ctx.restore();
    }
    // Pure rendering API shared by the standalone Canvas preview and the game.
    // Coordinates, targetLift and size use CSS pixels; t is in seconds.
    function renderUltimate(ctx,t,W,H,options={}) {
        t=clamp(t,0,3);
        const from=options.from||{x:W*.23,y:H*.66},to=options.to||{x:W*.76,y:H*.43};
        const size=options.size||Math.min(W*.27,H*.50),targetSize=options.targetSize||size;
        const grow=ease((t-1.28)/.47),fade=1-ease((t-1.92)/.55);
        const base={x:to.x,y:to.y+targetSize*.43};
        // The opponent sits near the top of the diagonal arena. Fit the full
        // crown and the lifted body inside it while retaining the large tree
        // in standalone previews that have enough room above the opponent.
        const treeSize=Math.min(targetSize,Math.max(0,(base.y-8)/1.55));
        const treeHeight=treeSize*1.12*grow;
        const targetLift=Math.min(Math.max(0,to.y-targetSize*.38-8),
            targetSize*.32*ease((t-1.40)/.35)*(1-ease((t-2.05)/.42)));
        const treeTop=base.y-treeSize*1.55*grow;
        const nameVisible=t>=.65&&t<1.60;
        if(t<1.25){
            const pulse=ease(t/.65)*(1-ease((t-.98)/.27));
            ctx.save();ctx.globalAlpha=pulse*.5;ctx.fillStyle='#FFBE73';
            ctx.beginPath();ctx.ellipse(from.x,from.y-size*.36,size*.24,size*.12,0,0,Math.PI*2);ctx.fill();ctx.restore();
            for(let i=0;i<4;i++){const p=clamp((t-.15-i*.08)/.65);if(!p||p>=1)continue;drawMath(ctx,['2','+','5','×'][i],from.x+(i-1.5)*size*.10,from.y-size*(.08+p*.43),size*.12,Math.sin(p*Math.PI));}
        }
        if(t>=.95&&t<1.65){
            // Six small glyphs fly from the open book, then settle as seeds.
            for(let i=0;i<6;i++){
                const p=clamp((t-.95-i*.045)/.45);if(!p||p>=1)continue;
                const x=lerp(from.x,base.x+(i-2.5)*targetSize*.052,p);
                const y=lerp(from.y+size*.12,base.y,p)-Math.sin(p*Math.PI)*size*.28;
                drawMath(ctx,['1','+','2','−','×','÷'][i],x,y,size*.13,1-p*.35);
            }
        }
        if(grow>0&&fade>0){
            ctx.save();ctx.globalAlpha=fade;ctx.translate(base.x,base.y);
            ctx.strokeStyle='#FFE6A1';ctx.lineCap='round';ctx.lineWidth=Math.max(2,treeSize*.065*grow);
            ctx.beginPath();ctx.moveTo(0,0);ctx.bezierCurveTo(-treeSize*.05,-treeHeight*.3,treeSize*.05,-treeHeight*.68,0,-treeHeight);ctx.stroke();
            ctx.lineWidth=Math.max(1,treeSize*.032*grow);
            for(const side of [-1,1]){
                ctx.beginPath();ctx.moveTo(0,-treeHeight*.50);ctx.quadraticCurveTo(side*treeSize*.10*grow,-treeHeight*.70,side*treeSize*.27*grow,-treeHeight*.81);ctx.stroke();
                ctx.beginPath();ctx.moveTo(0,-treeHeight*.18);ctx.quadraticCurveTo(side*treeSize*.12*grow,-treeHeight*.36,side*treeSize*.37*grow,-treeHeight*.45);ctx.stroke();
            }
            for(let i=0;i<7;i++){
                const a=i*Math.PI*2/7,x=Math.cos(a)*treeSize*.26*grow,y=-treeHeight+Math.sin(a)*treeSize*.17*grow;
                ctx.fillStyle=i%2?'#A8D178':'#78B77E';ctx.beginPath();ctx.ellipse(x,y,treeSize*.26*grow,treeSize*.19*grow,a*.14,0,Math.PI*2);ctx.fill();
                ctx.strokeStyle='#FFF4BD';ctx.lineWidth=Math.max(1,treeSize*.012);ctx.stroke();
            }
            ctx.strokeStyle='#FFBE73';ctx.lineWidth=Math.max(1,treeSize*.02);ctx.beginPath();ctx.ellipse(0,0,treeSize*.40*grow,treeSize*.09*grow,0,0,Math.PI*2);ctx.stroke();ctx.restore();
        }
        if(t>=1.75&&t<2.95){
            const p=clamp((t-1.75)/1.2);
            for(let i=0;i<16;i++){
                const angle=i*Math.PI*2/16,spread=targetSize*(.17+p*.7);
                const x=to.x+Math.cos(angle)*spread,y=to.y-targetSize*.36+Math.sin(angle)*spread*.55+targetSize*p*p*.7;
                if(i%3===0)page(ctx,x,y,targetSize*.12,angle+p*2,1-p);else star(ctx,x,y,targetSize*.035*(1-p)+1,1-p);
            }
        }
        if(options.drawActor!==false)renderPet(ctx,{time:t,mode:'ultimate',x:from.x,y:from.y,size,facing:options.facing??(to.x<from.x?-1:1),motion:options.motion!==false});
        if(nameVisible&&options.drawName!==false)banner(ctx,W,H,'ĐẠI THỤ TRI THỨC');
        return {...sample('ultimate',t),nameVisible,attackStarted:t>=.95,impact:t>=1.75,victory:t>=1.9,flourish:t>=1.9,tree:grow*fade,targetLift,treeTop};
    }
    function renderAttack(ctx,t,W,H,{from,to,size}={}) {
        from ||= {x:W*.23,y:H*.66};to ||= {x:W*.76,y:H*.43};size ||= W*.24;
        for(let i=0;i<3;i++){
            const p=(t-.18-i*.10)/.52;if(p<0||p>1)continue;
            const x=lerp(from.x,to.x,ease(p)),y=lerp(from.y+size*.12,to.y,ease(p))-Math.sin(p*Math.PI)*size*.15;
            drawMath(ctx,['+','2','×'][i],x,y,size*.14,Math.sin(p*Math.PI));
        }
        if(t>=.65&&t<1.1){const p=(t-.65)/.45;for(let i=0;i<6;i++){const a=i*Math.PI/3;star(ctx,to.x+Math.cos(a)*size*p*.4,to.y+Math.sin(a)*size*p*.4,size*.035,1-p);}}
    }

    function fit(canvas) {
        const box=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);
        const W=Math.max(1,Math.round(box.width*dpr)),H=Math.max(1,Math.round(box.height*dpr));
        if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H;}
        return {W:box.width,H:box.height,dpr};
    }
    function paintPet(entry,t) {
        const {canvas,ctx}=entry,{W,H,dpr}=fit(canvas);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
        const state=renderPet(ctx,{mode:entry.mode,time:t,x:W/2,y:H/2,size:Math.min(W,H)*.96,motion:!reduced.matches});
        canvas.dataset.mode=entry.mode;canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.pose=String(state.pose);
    }
    function cancelPet(entry) { cancelAnimationFrame(entry.raf);entry.raf=0; }
    function playPet(entry,mode,force=false) {
        mode=modeOf(mode);if(entry.mode===mode&&!force)return;
        cancelPet(entry);entry.mode=mode;entry.started=performance.now();
        if(!atlas)return;
        const duration=durations[mode]||0;
        if(reduced.matches||document.hidden||!duration){paintPet(entry,duration);return;}
        const tick=now=>{
            entry.raf=0;if(!entry.node.isConnected||document.hidden||!enabled)return;
            const time=Math.min(duration,(now-entry.started)/1000);paintPet(entry,time);
            if(time<duration)entry.raf=requestAnimationFrame(tick);
            else if(mode==='attack'||mode==='hit'){entry.mode='idle';paintPet(entry,0);entry.mode=mode;}
        };
        paintPet(entry,0);entry.raf=requestAnimationFrame(tick);
    }
    function mount(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='mam-sach-pose';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mode:null,raf:0};pets.set(node,entry);
        ready().then(image=>{
            if(!image||!node.isConnected||pets.get(node)!==entry||!enabled)return;
            node.append(canvas);node.classList.add('mam-sach-ready');playPet(entry,node.dataset.mood||'idle',true);
        });
        return entry;
    }
    function sync(root=document) {
        if(!enabled)return;
        for(const [node,entry] of pets)if(!node.isConnected){cancelPet(entry);pets.delete(node);}
        const nodes=[...root.querySelectorAll('.battle-pet.sprout')];if(root.matches?.('.battle-pet.sprout'))nodes.unshift(root);
        for(const node of nodes){const entry=mount(node);if(entry)playPet(entry,node.dataset.mood||'idle');}
        for(const effect of [...effects])if(!effect.stage.isConnected)effect.finish();
    }
    function scheduleSync() { if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();}); }
    function playEffect(source,victim,ultimate) {
        const actor=petOf(source),stage=source?.closest('.battle-stage');
        if(!actor||!stage||!victim)return false;
        const duration=ultimate?3:1.1,started=performance.now(),token=generation;
        if(ultimate)pendingUntilAt=started+3000;
        if(reduced.matches||document.hidden){
            const label=stage.querySelector('#spell-announcement');if(ultimate&&label){label.textContent='✦ Đại Thụ Tri Thức';label.dataset.mamSach='true';}return true;
        }
        ready().then(image=>{
            if(!image||!stage.isConnected||document.hidden||token!==generation||(performance.now()-started)/1000>=duration)return;
            for(const previous of [...effects])if(previous.stage===stage)previous.finish();
            const canvas=document.createElement('canvas');canvas.className='mam-sach-effect';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const box=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),target=victim.querySelector('.battle-pet')||victim;
            const b=target.getBoundingClientRect(),turn=target.closest('.pet-turn');
            const from={x:a.left-box.left+a.width/2,y:a.top-box.top+a.height/2},to={x:b.left-box.left+b.width/2,y:b.top-box.top+b.height/2};
            const liftBefore=turn?.style.translate||'',announcement=stage.querySelector('#spell-announcement');let raf=0,done=false;
            const effect={stage,finish:()=>{
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();
                if(turn){if(liftBefore)turn.style.translate=liftBefore;else turn.style.removeProperty('translate');}
                stage.classList.remove('mam-sach-action-active');
                if(announcement?.dataset.mamSach==='true'){announcement.textContent='';delete announcement.dataset.mamSach;announcement.classList.remove('mam-sach-spell-accessible');}
                effects.delete(effect);
            }};
            stage.append(canvas);stage.classList.add('mam-sach-action-active');effects.add(effect);
            const tick=now=>{
                raf=0;if(!enabled||document.hidden||!stage.isConnected||!actor.isConnected||!target.isConnected){effect.finish();return;}
                const t=Math.min(duration,(now-started)/1000),{W,H,dpr}=fit(canvas);
                ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                let state;
                if(ultimate){
                    state=renderUltimate(ctx,t,W,H,{from,to,size:a.width,targetSize:b.width,drawActor:false});
                    if(turn)turn.style.translate=`0 ${-state.targetLift}px`;
                    if(state.nameVisible&&announcement){announcement.textContent='✦ Đại Thụ Tri Thức';announcement.dataset.mamSach='true';announcement.classList.add('mam-sach-spell-accessible');}
                }else renderAttack(ctx,t,W,H,{from,to,size:a.width});
                canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.nameVisible=String(Boolean(state?.nameVisible));canvas.dataset.impact=String(Boolean(state?.impact));
                if(t>=duration){effect.finish();return;}raf=requestAnimationFrame(tick);
            };
            raf=requestAnimationFrame(tick);
        });
        return true;
    }
    function hit({source,victim,final=false}={}) {
        if(!enabled||!petOf(source))return false;
        const node=petOf(source);node.dataset.mood=final?'ultimate':'attack';sync();
        const entry=pets.get(node);if(entry)playPet(entry,final?'ultimate':'attack',true);
        return playEffect(source,victim,final);
    }
    function stop() {
        generation++;pendingUntilAt=0;
        for(const entry of pets.values())cancelPet(entry);
        for(const effect of [...effects])effect.finish();
    }
    function configure(options={}) {
        if(options.asset&&options.asset!==config.asset){config.asset=options.asset;atlas=null;loading=null;}
        if(options.frames)config.frames=options.frames;
        for(const entry of pets.values())ready().then(image=>{if(image&&entry.node.isConnected)playPet(entry,entry.node.dataset.mood||'idle',true);});
    }
    function destroy() {
        enabled=false;observer?.disconnect();stop();
        for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('mam-sach-ready');}pets.clear();
    }
    function inspect() {
        return {loaded:Boolean(atlas),reducedMotion:reduced.matches,mounted:pets.size,
            activeRaf:[...pets.values()].filter(e=>e.raf).length+effects.size,
            pets:[...pets.values()].map(e=>({mode:e.mode,pose:Number(e.canvas.dataset.pose),frame:Number(e.canvas.dataset.pose),
                time:Number(e.canvas.dataset.time),running:Boolean(e.raf),connected:e.node.isConnected,
                facing:e.node.closest('.fighter')?.classList.contains('right')?'left':'right'})),effects:effects.size};
    }
    window.MamSachAnimation={ready,configure,sync,hit,stop,destroy,sample,renderPet,renderUltimate,renderAttack,drawSprite,inspect,pendingUntil:()=>Date.now()+Math.max(0,pendingUntilAt-performance.now())};
    function start(){observer=new MutationObserver(scheduleSync);observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-mood']});sync();}
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{stop();if(!document.hidden)for(const entry of pets.values())if(atlas)paintPet(entry,durations[entry.mode]||0);});
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();for(const entry of pets.values())if(atlas)paintPet(entry,durations[entry.mode]||0);});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())if(atlas)paintPet(entry,durations[entry.mode]||0);});
})();
