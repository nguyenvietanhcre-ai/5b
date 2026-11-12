/* Cáo Nâu — Canvas/WebP presentation. The server remains authoritative for battles. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.FoxAnimation) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set(), sheets = {};
    const durations = {attack:1000,hit:1100,lose:2200,win:1600,ultimate:3000};
    const modes = {attack:[0,1,2,3],hit:[4,5,6,7],lose:[8,9,10,11],win:[12,13,14,15]};
    const clamp = p => Math.max(0,Math.min(1,p));
    const mix = (a,b,p) => a+(b-a)*p;
    const smooth = p => {p=clamp(p);return p*p*(3-2*p);};
    const fox = node => node?.matches?.('.battle-pet.fox') ? node : node?.querySelector?.('.battle-pet.fox');
    let loading,observer,queued=false,enabled=true,generation=0,finaleUntil=0;

    function loadImage(file) {
        return new Promise((resolve,reject) => {
            const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(Error('Cáo Nâu: thiếu '+file));
            image.src=new URL('arena-art/cao-nau/'+file,document.baseURI).href;
        });
    }
    function ready() {
        if(!loading) loading=Promise.all([
            loadImage('poses.webp'),loadImage('reactions.webp'),
            fetch(new URL('arena-art/cao-nau/frames.json',document.baseURI)).then(r=>r.ok?r.json():null).catch(()=>null),
        ]).then(([ultimate,reactions,bounds])=>{
            for(const [key,image] of Object.entries({ultimate,reactions})) {
                const frames=bounds?.[key]?.frames || Array.from({length:16},(_,i)=>{
                    const left=Math.round(i%4*image.naturalWidth/4),top=Math.round(Math.floor(i/4)*image.naturalHeight/4);
                    return {left,top,width:Math.round((i%4+1)*image.naturalWidth/4)-left,height:Math.round((Math.floor(i/4)+1)*image.naturalHeight/4)-top};
                });
                if(frames.length!==16||frames.some(f=>f.width<=0||f.height<=0||f.left<0||f.top<0||f.left+f.width>image.naturalWidth||f.top+f.height>image.naturalHeight))throw Error('Cáo Nâu: frame không hợp lệ');
                sheets[key]={image,frames,max:Math.max(...frames.map(f=>Math.max(f.width,f.height)))};
            }
        }).catch(error=>{loading=null;throw error;});
        return loading;
    }
    function sprite(ctx,key,index,x,y,size,{flip=false,rotation=0,alpha=1}={}) {
        const sheet=sheets[key];if(!sheet)return;
        const f=sheet.frames[index],scale=size/sheet.max;
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);
        ctx.drawImage(sheet.image,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale/2,f.width*scale,f.height*scale);ctx.restore();
    }
    function leaf(ctx,x,y,size,angle,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(angle);ctx.fillStyle='#ffbe73';
        ctx.beginPath();ctx.moveTo(-size,0);ctx.quadraticCurveTo(0,-size*.85,size,0);ctx.quadraticCurveTo(0,size*.85,-size,0);ctx.fill();
        ctx.strokeStyle='#b65d30';ctx.lineWidth=Math.max(.7,size*.1);ctx.beginPath();ctx.moveTo(-size*.8,0);ctx.lineTo(size*.8,0);ctx.stroke();ctx.restore();
    }
    function cancel(entry) {cancelAnimationFrame(entry.raf);entry.raf=0;}
    function paint(entry,time) {
        const {canvas,ctx,node,mood}=entry,box=node.getBoundingClientRect(),pixels=Math.max(1,Math.min(512,Math.round(box.width*Math.min(devicePixelRatio||1,2))));
        if(canvas.width!==pixels){canvas.width=pixels;canvas.height=pixels;}
        ctx.clearRect(0,0,pixels,pixels);
        const u=clamp(time/(durations[mood]||1));let x=pixels/2,y=pixels/2,rotation=0;
        const key=mood==='idle'||mood==='ultimate'?'ultimate':'reactions';
        const sequence=modes[mood]||[0],index=sequence[Math.min(sequence.length-1,Math.floor(u*sequence.length))];
        if(!reduced.matches) {
            if(mood==='attack'){x+=Math.sin(u*Math.PI)*pixels*.08;rotation=-Math.sin(u*Math.PI)*.07;}
            if(mood==='hit'){x+=Math.sin(u*Math.PI*7)*(1-u)*pixels*.035;rotation=Math.sin(u*Math.PI)*.08;}
            if(mood==='lose')y+=smooth(u)*pixels*.025;
            if(mood==='win')y-=Math.sin(u*Math.PI)*pixels*.04;
        }
        sprite(ctx,key,index,x,y,pixels*.94,{rotation});
        canvas.dataset.mode=mood;canvas.dataset.pose=String(index);canvas.dataset.time=String(Math.round(time));
    }
    function animate(entry,mood,force=false) {
        if(entry.mood===mood&&!force)return;
        cancel(entry);entry.mood=mood;entry.started=performance.now();
        if(!sheets.reactions)return;
        const duration=durations[mood]||0;
        if(reduced.matches||document.hidden||!duration){paint(entry,duration);return;}
        paint(entry,0);
        function tick(now) {
            entry.raf=0;if(!enabled||!entry.node.isConnected||document.hidden)return;
            const elapsed=Math.max(0,Math.min(duration,now-entry.started));paint(entry,elapsed);
            if(elapsed<duration)entry.raf=requestAnimationFrame(tick);
            else if(mood==='attack'||mood==='hit'){entry.node.dataset.mood='idle';animate(entry,'idle');}
        }
        entry.raf=requestAnimationFrame(tick);
    }
    function mountOne(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='fox-canvas';canvas.width=384;canvas.height=384;canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mood:null,raf:0};pets.set(node,entry);
        ready().then(()=>{if(!node.isConnected||!pets.has(node))return;node.append(canvas);node.classList.add('fox-ready');animate(entry,node.dataset.mood||'idle',true);}).catch(()=>node.classList.remove('fox-ready'));
        return entry;
    }
    function mount(root=document) {
        for(const [node,entry] of pets)if(!node.isConnected){cancel(entry);pets.delete(node);}
        const nodes=[...root.querySelectorAll('.battle-pet.fox')];if(root.matches?.('.battle-pet.fox'))nodes.unshift(root);
        for(const node of nodes){const entry=mountOne(node);if(entry)animate(entry,node.dataset.mood||'idle');}
        for(const flight of [...flights])if(!flight.stage.isConnected)flight.finish();
    }

    function renderUltimate(ctx,t,W,H,{from,to,size,flip=false}={}) {
        t=Math.max(0,Math.min(3,t));
        from=from||{x:W*.25,y:H*.68};to=to||{x:W*.75,y:H*.29};size=size||W*.29;
        const sign=flip?-1:1;let x=from.x,y=from.y,index=0,rotation=0;
        if(t<.95){index=Math.min(3,Math.floor(t/.95*4));x+=Math.sin(t*9)*size*.025;}
        else if(t<1.44){const p=smooth((t-.95)/.49);x=mix(from.x,to.x+sign*size*.35,p);y=mix(from.y,to.y,p)-Math.sin(p*Math.PI)*size*.24;index=4+Math.min(3,Math.floor(p*4));}
        else if(t<1.9){const p=clamp((t-1.44)/.46);x=to.x+Math.cos(p*Math.PI*2)*sign*size*.35;y=to.y+Math.sin(p*Math.PI*2)*size*.09;index=8+Math.min(3,Math.floor(p*4));rotation=Math.sin(p*Math.PI*2)*.12;}
        else{const p=smooth((t-1.9)/.4);x=mix(to.x+sign*size*.35,from.x,p);y=mix(to.y,from.y,p);index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));y-=Math.sin(p*Math.PI)*size*.15;}
        if(t>=.25&&t<1.15)for(let i=0;i<7;i++){
            const a=i*Math.PI*2/7+t*4,r=size*(.27+(1-smooth((t-.25)/.8))*.3);
            leaf(ctx,from.x+Math.cos(a)*r,from.y+size*.2+Math.sin(a)*size*.12,size*.035,a,Math.min(1,t*2));
        }
        if(t>=1.12&&t<2.48){
            const p=clamp((t-1.12)/.63),fade=1-smooth((t-1.9)/.58),count=W<420?22:36;
            ctx.save();ctx.globalAlpha=fade;
            for(let i=0;i<count;i++){
                const level=i/count,a=i*2.39996-t*14,burst=smooth((t-1.9)/.55);
                const radius=size*(.13+level*.55)*p+burst*size*.65;
                const lx=to.x+Math.cos(a)*radius,ly=to.y+size*.3-level*size*1.05+Math.sin(a)*size*.07+burst*Math.sin(i*2.1)*size*.6;
                leaf(ctx,lx,ly,size*(.025+level*.018),a+.5,1-burst*.35);
            }
            ctx.strokeStyle='#ffbe73';ctx.lineWidth=Math.max(1.5,size*.018);ctx.globalAlpha*=.6;
            for(let i=0;i<4;i++){ctx.beginPath();ctx.ellipse(to.x,to.y+size*.25-i*size*.2,size*(.22+i*.1)*p,size*.065,t*2+i,0,Math.PI*1.65);ctx.stroke();}
            ctx.restore();
        }
        // Keep the complete rotated silhouette inside a narrow battle stage.
        const frame=sheets.ultimate?.frames[index];
        if(frame){
            const scale=size/sheets.ultimate.max,c=Math.abs(Math.cos(rotation)),s=Math.abs(Math.sin(rotation));
            const padX=(frame.width*c+frame.height*s)*scale/2+2,padY=(frame.height*c+frame.width*s)*scale/2+2;
            x=Math.max(padX,Math.min(W-padX,x));y=Math.max(padY,Math.min(H-padY,y));
        }
        sprite(ctx,'ultimate',index,x,y,size,{flip,rotation});
        const nameVisible=t>=.65&&t<1.55;
        if(nameVisible){
            const text='LỐC ĐUÔI TINH QUÁI',font=Math.max(12,Math.min(26,W*.043)),top=H*.39;
            ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const width=Math.min(W-20,ctx.measureText(text).width+30),height=font+22;
            ctx.fillStyle='#1f6248f5';ctx.beginPath();ctx.roundRect((W-width)/2,top-height/2,width,height,12);ctx.fill();ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,top,W-38);ctx.restore();
        }
        return {pose:index,nameVisible,impact:t>=1.75,finished:t>=3};
    }
    function ultimate({source,victim}={}) {
        const actor=fox(source),stage=actor?.closest('#battle-stage');if(!actor||!stage||!victim)return false;
        finaleUntil=performance.now()+3000;
        if(reduced.matches||document.hidden){play(actor,'win');return true;}
        const ticket=generation;
        ready().then(()=>{
            if(!enabled||ticket!==generation||!stage.isConnected||document.hidden)return;
            for(const old of [...flights])if(old.stage===stage)old.finish();
            const bounds=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),target=victim.querySelector('.battle-pet')||victim,b=target.getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5),size=a.width;
            const from={x:a.left-bounds.left+a.width/2,y:a.top-bounds.top+a.height/2},to={x:b.left-bounds.left+b.width/2,y:b.top-bounds.top+b.height/2},flip=to.x<from.x;
            const canvas=document.createElement('canvas');canvas.className='fox-ultimate-canvas';canvas.setAttribute('aria-hidden','true');canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const started=performance.now(),announcement=stage.querySelector('#spell-announcement');let raf=0,done=false;
            finaleUntil=started+3000;
            const flight={stage,finish(settle=true){
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();actor.classList.remove('fox-in-ultimate');target.classList.remove('fox-caught');stage.classList.remove('fox-ultimate-active');
                announcement?.classList.remove('fox-spell-accessible');if(announcement?.textContent==='✦ Lốc Đuôi Tinh Quái')announcement.textContent='';
                flights.delete(flight);
                if(actor.isConnected&&actor.dataset.mood==='ultimate'){
                    if(settle)play(actor,'win');
                    else {actor.dataset.mood='win';const entry=pets.get(actor);if(entry){cancel(entry);entry.mood='win';paint(entry,durations.win);}}
                }
            }};
            stage.append(canvas);actor.classList.add('fox-in-ultimate');stage.classList.add('fox-ultimate-active');flights.add(flight);
            function draw(now) {
                raf=0;if(!enabled||!stage.isConnected||document.hidden){flight.finish();return;}
                const t=Math.max(0,Math.min(3,(now-started)/1000));ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                const state=renderUltimate(ctx,t,W,H,{from,to,size,flip});
                if(t>=1.55&&t<2.35)target.classList.add('fox-caught');else target.classList.remove('fox-caught');
                if(state.nameVisible&&announcement&&!announcement.classList.contains('fox-spell-accessible')){announcement.textContent='✦ Lốc Đuôi Tinh Quái';announcement.classList.add('fox-spell-accessible');}
                canvas.dataset.time=String(Math.round(t*1000));canvas.dataset.pose=String(state.pose);canvas.dataset.nameVisible=String(state.nameVisible);canvas.dataset.impact=String(state.impact);
                if(t>=3){flight.finish();return;}raf=requestAnimationFrame(draw);
            }
            raf=requestAnimationFrame(draw);
        }).catch(()=>actor.classList.remove('fox-in-ultimate'));
        return true;
    }
    function play(node,action='idle') {node=fox(node);if(!node)return false;node.dataset.mood=action;const entry=mountOne(node);if(entry)animate(entry,action,true);return true;}
    function hit({source,victim,final=false}={}) {
        const actor=fox(source),target=fox(victim);
        if(target&&!actor)play(target,final?'lose':'hit');
        if(!actor)return false;
        if(final){play(actor,'ultimate');return ultimate({source,victim});}
        return play(actor,'attack');
    }
    function stop() {generation++;finaleUntil=0;for(const entry of pets.values())cancel(entry);for(const flight of [...flights])flight.finish(false);}
    function destroy() {enabled=false;observer?.disconnect();stop();for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('fox-ready');}pets.clear();}
    const inspect=()=>({loaded:Boolean(sheets.reactions),pets:[...pets.values()].map(e=>({mood:e.mood,pose:Number(e.canvas.dataset.pose),time:Number(e.canvas.dataset.time),running:Boolean(e.raf),connected:e.node.isConnected})),flights:flights.size,reducedMotion:reduced.matches});
    const pendingUntil=()=>Date.now()+Math.max(0,finaleUntil-performance.now());
    window.FoxAnimation={mountManaged(root=document){enabled=true;mount(root);},ready,mount,play,hit,ultimate,stop,destroy,renderUltimate,inspect,pendingUntil};
    function start() {observer=new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;if(enabled)mount();});});observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});mount();}
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else for(const entry of pets.values())animate(entry,entry.node.dataset.mood||'idle',true);});
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();for(const entry of pets.values())if(sheets.reactions)paint(entry,durations[entry.mood]||0);});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())animate(entry,entry.node.dataset.mood||'idle',true);});
})();
