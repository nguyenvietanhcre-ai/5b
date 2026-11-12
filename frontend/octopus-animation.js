/* 5BMath — Bạch tuộc / Tám Tay Ảo Thuật. Canvas presentation only. */
const OctopusAnimation = (() => {
    'use strict';
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set();
    const duration = {attack:1,hit:1,win:1.8,lose:2.2,ultimate:3};
    const clamp = n => Math.max(0,Math.min(1,n));
    const smooth = n => {n=clamp(n);return n*n*(3-2*n);};
    const mix = (a,b,u) => a+(b-a)*u;
    let atlas, bounds, loading, observer, queued=false,enabled=true;

    function ready() {
        if (!loading) loading = Promise.all([
            new Promise((resolve,reject) => {
                const image = new Image();
                image.onload=()=>resolve(image);image.onerror=()=>reject(Error('Không tải được hình Bạch tuộc.'));
                image.src=new URL('arena-art/bach-tuoc-poses.webp',document.baseURI).href;
            }),
            fetch(new URL('arena-art/bach-tuoc-frames.json',document.baseURI)).then(response=>{
                if(!response.ok)throw Error('Không tải được tư thế Bạch tuộc.');return response.json();
            }),
        ]).then(([image,data])=>{
            if(!Array.isArray(data.frames)||data.frames.length!==16)throw Error('Tư thế Bạch tuộc chưa đầy đủ.');
            atlas=image;bounds=data.frames;
            return image;
        }).catch(error=>{loading=null;throw error;});
        return loading;
    }
    function sprite(ctx,index,x,feet,size,{alpha=1,flip=false,rotation=0}={}) {
        if(!atlas||!bounds)return;
        const f=bounds[index],scale=size/Math.max(...bounds.map(frame=>Math.max(frame.width,frame.height)));
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,feet);ctx.rotate(rotation);if(flip)ctx.scale(-1,1);
        ctx.drawImage(atlas,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);
        ctx.restore();
    }
    function pose(action,time) {
        const u=clamp(time/(duration[action]||1));
        if(action==='attack')return 8+Math.min(1,Math.floor(u*2));
        if(action==='hit')return 10+Math.min(1,Math.floor(u*2));
        if(action==='lose')return 14+Math.min(1,Math.floor(u*2));
        if(action==='win')return 12+Math.min(1,Math.floor(u*2));
        return 0;
    }
    function fit(canvas) {
        const box=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
        const w=Math.max(1,Math.round(box.width*dpr)),h=Math.max(1,Math.round(box.height*dpr));
        if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
        return {w,h};
    }
    function drawPet(entry,time=0) {
        const {w,h}=fit(entry.canvas),ctx=entry.canvas.getContext('2d'),action=entry.action,u=clamp(time/(duration[action]||1));
        ctx.clearRect(0,0,w,h);let x=w/2,feet=h*.96,rotation=0;
        if(!reduced.matches){
            if(action==='attack'){x+=Math.sin(u*Math.PI)*w*.025;rotation=-Math.sin(u*Math.PI)*.035;}
            if(action==='hit'){x+=Math.sin(u*Math.PI*5)*(1-u)*w*.025;rotation=Math.sin(u*Math.PI)*.035;}
            if(action==='lose')feet+=smooth(u)*h*.02;
            if(action==='win')feet-=Math.sin(u*Math.PI)*h*.07;
        }
        const index=pose(action,time);sprite(ctx,index,x,feet,Math.min(w,h)*.9,{rotation});
        entry.canvas.dataset.action=action;entry.canvas.dataset.pose=String(index);
    }
    function bubble(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;
        const gradient=ctx.createRadialGradient(x-r*.3,y-r*.35,r*.05,x,y,r);
        gradient.addColorStop(0,'#f2ffffb0');gradient.addColorStop(.65,'#81d9e36a');gradient.addColorStop(1,'#459dcb99');
        ctx.fillStyle=gradient;ctx.strokeStyle='#c3f8ff';ctx.lineWidth=Math.max(1,r*.07);
        ctx.beginPath();ctx.arc(x,y,Math.max(.1,r),0,Math.PI*2);ctx.fill();ctx.stroke();
        ctx.strokeStyle='#fff9ed';ctx.lineWidth=Math.max(1,r*.1);ctx.beginPath();ctx.arc(x,y,r*.67,Math.PI*1.13,Math.PI*1.47);ctx.stroke();ctx.restore();
    }
    // Eight water spheres are numbered by their arm index, never an unbounded particle loop.
    function renderUltimate(ctx,time,W,H,{from,to,size,flip=false,drawActor=true}={}) {
        const t=Math.max(0,Math.min(3,time)),a=from||{x:W*.23,y:H*.75},b=to||{x:W*.76,y:H*.45};
        size=size||Math.min(W*.28,H*.4);
        const edge=size*.09+2,radiusX=Math.max(3,Math.min(size*.7,b.x-edge,W-b.x-edge)),radiusY=Math.max(3,Math.min(size*.7,b.y-edge,H-b.y-edge));
        let index=0,alpha=1,feet=a.y;
        if(t<.65)index=Math.min(3,Math.floor(t/.65*4));
        else if(t<.95){index=3;alpha=1-smooth((t-.65)/.3);}
        else if(t<1.75){index=4+Math.min(3,Math.floor((t-.95)/.8*4));alpha=0;}
        else if(t<1.9){index=7;alpha=0;}
        else{index=12+Math.min(1,Math.floor((t-1.9)/1.1*2));feet-=Math.sin(clamp((t-1.9)/.8)*Math.PI)*size*.06;}
        if(t>=.38&&t<1.22){
            const u=clamp((t-.38)/.84),r=size*(.18+u*.8),opacity=Math.sin(u*Math.PI)*.62;
            ctx.save();ctx.globalAlpha=opacity;
            const ink=ctx.createRadialGradient(a.x,a.y-size*.43,0,a.x,a.y-size*.43,r);
            ink.addColorStop(0,'#4d3b72e8');ink.addColorStop(.65,'#75609ca0');ink.addColorStop(1,'#75609c00');
            ctx.fillStyle=ink;ctx.beginPath();ctx.arc(a.x,a.y-size*.43,r,0,Math.PI*2);ctx.fill();ctx.restore();
        }
        if(t>=.95&&t<1.9){
            const u=clamp((t-.95)/.8),growth=smooth((t-.95)/.23),collapse=smooth((u-.36)/.64);
            ctx.save();ctx.globalAlpha=1-smooth((t-1.76)/.14);ctx.lineCap='round';
            for(let arm=0;arm<8;arm++){
                const angle=arm*Math.PI/4,dx=Math.cos(angle),dy=Math.sin(angle),px=-dy,py=dx;
                const root={x:b.x+dx*radiusX,y:b.y+dy*radiusY};
                const tip={x:b.x+dx*radiusX*(1-growth*.62),y:b.y+dy*radiusY*(1-growth*.62)};
                const bend=Math.min(size*.17,radiusX*.25,radiusY*.25)*Math.sin(u*Math.PI+arm*.42);
                ctx.strokeStyle='#9474bd';ctx.lineWidth=size*.085;
                ctx.beginPath();ctx.moveTo(root.x,root.y);ctx.quadraticCurveTo(b.x+dx*radiusX*.69+px*bend,b.y+dy*radiusY*.69+py*bend,tip.x,tip.y);ctx.stroke();
                ctx.strokeStyle='#c2a8df';ctx.lineWidth=size*.027;
                ctx.beginPath();ctx.moveTo(root.x+px*size*.015,root.y+py*size*.015);ctx.quadraticCurveTo(b.x+dx*radiusX*.69+px*(bend+size*.015),b.y+dy*radiusY*.69+py*(bend+size*.015),tip.x+px*size*.015,tip.y+py*size*.015);ctx.stroke();
                ctx.fillStyle='#fff0d8';
                for(let dot=0;dot<3;dot++){
                    const p=(dot+1)/4,cx=mix(root.x,tip.x,p)+px*bend*2*p*(1-p),cy=mix(root.y,tip.y,p)+py*bend*2*p*(1-p);
                    ctx.beginPath();ctx.arc(cx,cy,size*.016,0,Math.PI*2);ctx.fill();
                }
                bubble(ctx,mix(tip.x,b.x,collapse),mix(tip.y,b.y,collapse),size*.07,Math.min(1,(t-.95)*10));
            }ctx.restore();
        }
        if(t>=1.75&&t<2.35){
            const u=clamp((t-1.75)/.6);
            ctx.save();ctx.globalAlpha=1-u;ctx.strokeStyle='#9de9ed';ctx.lineWidth=Math.max(1,size*.025*(1-u));
            ctx.beginPath();ctx.ellipse(b.x,b.y,radiusX*(.14+.86*u),radiusY*(.14+.86*u),0,0,Math.PI*2);ctx.stroke();
            for(let arm=0;arm<8;arm++){
                const angle=arm*Math.PI/4,x=b.x+Math.cos(angle)*radiusX*(.28+.72*u),y=b.y+Math.sin(angle)*radiusY*(.28+.72*u),r=size*.045*(1-u)+1;
                ctx.fillStyle=arm%2?'#ffbe73':'#fff9ed';ctx.beginPath();
                for(let point=0;point<8;point++){const theta=point*Math.PI/4-Math.PI/2,rr=point%2?r*.3:r;ctx.lineTo(x+Math.cos(theta)*rr,y+Math.sin(theta)*rr);}
                ctx.closePath();ctx.fill();
            }ctx.restore();
        }
        if(drawActor)sprite(ctx,index,a.x,feet,size,{alpha,flip});
        return {pose:index,nameVisible:t>=.65&&t<1.75,impact:t>=1.75,spheres:t>=.95&&t<1.9?8:0,finished:t>=3};
    }
    function stopFlight(flight) {
        cancelAnimationFrame(flight.raf);flight.canvas.remove();flight.node.classList.remove('octopus-in-ultimate');
        flight.stage.classList.remove('octopus-ultimate-active');flights.delete(flight);
        const label=flight.stage.querySelector('#spell-announcement');
        if(label?.dataset.octopus==='true'){label.textContent='';delete label.dataset.octopus;}
    }
    function ultimate(entry) {
        const node=entry.node,stage=node.closest('#battle-stage'),fighter=node.closest('.fighter');
        const target=stage?.querySelector(fighter?.id==='fighter-me'?'#fighter-opponent .battle-pet':'#fighter-me .battle-pet');
        if(!stage||!target||reduced.matches){const action=entry.action;entry.action='win';drawPet(entry,duration.win);entry.action=action;return;}
        const canvas=document.createElement('canvas');canvas.className='octopus-ultimate-canvas';canvas.setAttribute('aria-hidden','true');
        const box=stage.getBoundingClientRect(),own=node.getBoundingClientRect(),other=target.getBoundingClientRect();
        const dpr=Math.min(devicePixelRatio||1,1.5),W=box.width,H=box.height;
        canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
        const from={x:own.left-box.left+own.width/2,y:own.top-box.top+own.height*.96};
        const to={x:other.left-box.left+other.width/2,y:other.top-box.top+other.height*.48};
        const flight={canvas,stage,node,raf:0,started:performance.now()};flights.add(flight);
        stage.append(canvas);node.classList.add('octopus-in-ultimate');stage.classList.add('octopus-ultimate-active');
        function tick(now){
            flight.raf=0;if(!node.isConnected||!stage.isConnected||document.hidden){stopFlight(flight);return;}
            const t=Math.min(3,(now-flight.started)/1000),ctx=canvas.getContext('2d');
            ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
            const sample=renderUltimate(ctx,t,W,H,{from,to,size:own.width*.9,flip:to.x<from.x});
            canvas.dataset.time=String(t);canvas.dataset.spheres=String(sample.spheres);canvas.dataset.pose=String(sample.pose);
            const label=stage.querySelector('#spell-announcement');if(label){label.dataset.octopus='true';label.textContent=sample.nameVisible?'✦ Tám Tay Ảo Thuật':'';}
            if(t>=3){stopFlight(flight);if(entry.node.isConnected){entry.node.dataset.mood='idle';play(entry.node,'idle');}return;}
            flight.raf=requestAnimationFrame(tick);
        }
        flight.raf=requestAnimationFrame(tick);
    }
    function play(node,action='idle') {
        if(!node?.matches?.('.battle-pet.octopus'))return false;
        if(node.dataset.mood!==action)node.dataset.mood=action;
        let entry=pets.get(node);
        if(!entry){
            const canvas=document.createElement('canvas');canvas.className='octopus-canvas';canvas.setAttribute('aria-hidden','true');node.append(canvas);
            entry={node,canvas,raf:0,action:'idle',ticket:0};pets.set(node,entry);
        }
        cancelAnimationFrame(entry.raf);entry.raf=0;entry.action=action;
        const ticket=++entry.ticket;
        for(const flight of [...flights])if(flight.node===node)stopFlight(flight);
        ready().then(()=>{
            if(!node.isConnected||entry.ticket!==ticket)return;
            node.classList.add('octopus-ready');
            if(action==='ultimate'){ultimate(entry);return;}
            drawPet(entry,reduced.matches?duration[action]||0:0);
            if(!duration[action]||reduced.matches||document.hidden)return;
            const started=performance.now();
            const tick=now=>{
                entry.raf=0;if(!node.isConnected||document.hidden)return;
                const t=Math.min(duration[action],(now-started)/1000);drawPet(entry,t);
                if(t<duration[action])entry.raf=requestAnimationFrame(tick);
            };entry.raf=requestAnimationFrame(tick);
        }).catch(()=>{node.classList.remove('octopus-ready');});
        return true;
    }
    function sync() {
        queued=false;
        if(!enabled)return;
        for(const [node,entry]of pets)if(!node.isConnected){cancelAnimationFrame(entry.raf);entry.ticket++;pets.delete(node);}
        for(const flight of [...flights])if(!flight.node.isConnected)stopFlight(flight);
        for(const node of document.querySelectorAll('.battle-pet.octopus')){
            const action=node.dataset.mood||'idle',entry=pets.get(node);
            if(!entry||entry.action!==action)play(node,action);
        }
    }
    function schedule(){if(!queued){queued=true;queueMicrotask(sync);}}
    function mount(){enabled=true;if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed) && !observer)start();else sync();}
    function destroy(){
        enabled=false;observer?.disconnect();observer=null;queued=false;
        for(const flight of [...flights])stopFlight(flight);
        for(const entry of pets.values()){cancelAnimationFrame(entry.raf);entry.ticket++;entry.canvas.remove();entry.node.classList.remove('octopus-ready');}
        pets.clear();
    }
    function start(){enabled=true;observer=new MutationObserver(schedule);observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});sync();}
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{
        if(document.hidden){for(const flight of [...flights])stopFlight(flight);for(const entry of pets.values()){cancelAnimationFrame(entry.raf);entry.raf=0;}}
        else for(const entry of pets.values())play(entry.node,entry.node.dataset.mood||'idle');
    });
    window.addEventListener('pagehide',destroy);
    window.addEventListener('pageshow',()=>{if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed) && !observer)start();});
    window.addEventListener('resize',()=>{for(const flight of [...flights])stopFlight(flight);for(const entry of pets.values())if(atlas)drawPet(entry,duration[entry.action]||0);});
    reduced.addEventListener('change',()=>{for(const entry of pets.values())play(entry.node,entry.node.dataset.mood||'idle');});
    const inspect=()=>({loaded:Boolean(atlas),pets:[...pets.values()].map(entry=>({action:entry.action,pose:Number(entry.canvas.dataset.pose),running:Boolean(entry.raf)})),flights:flights.size,reducedMotion:reduced.matches});
    return {ready,mount,play,destroy,renderUltimate,inspect};
})();
