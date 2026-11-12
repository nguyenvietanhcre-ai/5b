/* Ong — Lục Giác Hoàng Kim. Canvas presentation; battle rules stay on the server. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.ArenaBeeAnimation) return;
    const settings = {asset:'arena-art/bee/poses.webp',frames:[
        {left:29,top:32,width:259,height:254},{left:333,top:47,width:265,height:239},
        {left:636,top:49,width:261,height:236},{left:957,top:19,width:262,height:256},
        {left:26,top:348,width:258,height:248},{left:337,top:373,width:252,height:201},
        {left:639,top:376,width:263,height:201},{left:957,top:342,width:263,height:248},
        {left:26,top:658,width:251,height:249},{left:328,top:658,width:250,height:236},
        {left:637,top:705,width:269,height:196},{left:957,top:658,width:262,height:242},
        {left:26,top:976,width:249,height:249},{left:338,top:1013,width:253,height:204},
        {left:637,top:1039,width:258,height:184},{left:967,top:990,width:243,height:239},
    ]};
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set();
    const durations = {attack:900,hit:1100,lose:2200,win:1100,ultimate:3000};
    let atlas, loading, observer, queued=false, suspended=false, generation=0;
    const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,n));
    const smooth = p => { p=clamp(p);return p*p*(3-2*p); };
    const lerp = (a,b,p) => a+(b-a)*p;
    const bee = node => node?.matches?.('.battle-pet.bee') ? node : node?.querySelector?.('.battle-pet.bee');

    function ready() {
        if (loading) return loading;
        const url=settings.asset;
        loading=new Promise(resolve=>{
            const image=new Image();
            image.onload=()=>{if(settings.asset===url)atlas=image;resolve(settings.asset===url?image:null);};
            image.onerror=()=>{if(settings.asset===url)loading=null;resolve(null);};
            image.src=new URL(url,document.baseURI).href;
        });
        return loading;
    }
    function frame(index) {
        const f=settings.frames?.[index];
        if(f)return {x:f.x??f.left,y:f.y??f.top,w:f.width,h:f.height};
        const col=index%4,row=Math.floor(index/4),w=atlas.naturalWidth,h=atlas.naturalHeight;
        const x=Math.round(col*w/4),y=Math.round(row*h/4);
        return {x,y,w:Math.round((col+1)*w/4)-x,h:Math.round((row+1)*h/4)-y};
    }
    function sprite(ctx,index,x,y,size,{flip=false,alpha=1,rotation=0}={}) {
        if(!atlas)return;
        const f=frame(index),scale=size/Math.max(f.w,f.h);
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);
        ctx.drawImage(atlas,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);ctx.restore();
    }
    function sample(mode,seconds) {
        const p=clamp(seconds/((durations[mode]||1)/1000));
        if(mode==='attack')return 4+Math.min(3,Math.floor(p*4));
        if(mode==='hit')return 8+Math.min(3,Math.floor(p*4));
        if(mode==='lose')return 12+Math.min(3,Math.floor(p*4));
        if(mode==='win')return 3;
        return 0;
    }
    function hex(ctx,x,y,r,fill,stroke,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.beginPath();
        for(let k=0;k<6;k++){const a=k*Math.PI/3-Math.PI/6;ctx.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r);}
        ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=Math.max(1,r*.09);ctx.stroke();ctx.restore();
    }
    function drop(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.fillStyle='#ffc454';ctx.strokeStyle='#b77e24';ctx.lineWidth=Math.max(1,r*.1);
        ctx.beginPath();ctx.moveTo(0,-r*1.5);ctx.bezierCurveTo(r*1.6,r*.15,r*.8,r,0,r);ctx.bezierCurveTo(-r*.8,r,-r*1.6,r*.15,0,-r*1.5);ctx.fill();ctx.stroke();
        ctx.fillStyle='#fff2bb';ctx.beginPath();ctx.ellipse(-r*.22,0,r*.18,r*.35,-.2,0,Math.PI*2);ctx.fill();ctx.restore();
    }
    function star(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle='#fff7c7';ctx.strokeStyle='#e8b64f';ctx.lineWidth=1;ctx.beginPath();
        for(let k=0;k<8;k++){const a=k*Math.PI/4-Math.PI/2,rr=k%2?r*.32:r;ctx.lineTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr);}
        ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
    }
    function paintPet(entry,seconds) {
        const size=Math.max(1,Math.min(512,Math.ceil(entry.node.getBoundingClientRect().width*Math.min(devicePixelRatio||1,2))));
        if(entry.canvas.width!==size){entry.canvas.width=size;entry.canvas.height=size;}
        const ctx=entry.ctx,p=clamp(seconds/((durations[entry.mode]||1)/1000));
        ctx.clearRect(0,0,size,size);
        let x=size/2,y=size/2,rotation=0;
        if(!reduced.matches){
            if(entry.mode==='attack'){x+=Math.sin(p*Math.PI)*size*.08;y-=Math.sin(p*Math.PI)*size*.06;rotation=-Math.sin(p*Math.PI)*.08;}
            if(entry.mode==='hit'){x+=Math.sin(p*Math.PI*6)*(1-p)*size*.035;rotation=Math.sin(p*Math.PI)*.08;}
            if(entry.mode==='lose')y+=smooth(p)*size*.035;
            if(entry.mode==='win')y-=Math.sin(p*Math.PI)*size*.07;
        }
        const index=sample(entry.mode,seconds);
        sprite(ctx,index,x,y,size*.96,{rotation});
        if(entry.mode==='hit'&&p<.8)for(let k=0;k<3;k++)star(ctx,size*(.34+k*.16),size*.13,Math.max(2,size*.03),1-p);
        entry.canvas.dataset.mode=entry.mode;entry.canvas.dataset.pose=String(index);entry.canvas.dataset.time=String(Math.round(seconds*1000));
    }
    function cancel(entry) {if(entry.raf)cancelAnimationFrame(entry.raf);entry.raf=0;}
    function play(entry,mode,force=false) {
        if(!force&&entry.mode===mode)return;
        cancel(entry);entry.mode=mode;entry.started=performance.now();
        if(!atlas)return;
        const duration=durations[mode]||0;
        if(reduced.matches||document.hidden||suspended||!duration||mode==='ultimate'){paintPet(entry,duration/1000);return;}
        paintPet(entry,0);
        const tick=now=>{
            entry.raf=0;
            if(!entry.node.isConnected||document.hidden||suspended)return;
            const elapsed=Math.min(now-entry.started,duration);paintPet(entry,elapsed/1000);
            if(elapsed<duration)entry.raf=requestAnimationFrame(tick);
        };
        entry.raf=requestAnimationFrame(tick);
    }
    function mount(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='arena-bee-sprite';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mode:null,raf:0};pets.set(node,entry);
        ready().then(image=>{
            if(!image||!node.isConnected||pets.get(node)!==entry)return;
            node.append(canvas);node.classList.add('bee-canvas-ready');play(entry,node.dataset.mood||'idle',true);
        });
        return entry;
    }
    function sync(root=document) {
        if(suspended)return;
        for(const [node,entry]of pets)if(!node.isConnected){cancel(entry);pets.delete(node);}
        const nodes=[...root.querySelectorAll('.battle-pet.bee')];if(root.matches?.('.battle-pet.bee'))nodes.unshift(root);
        for(const node of nodes){const entry=mount(node);if(entry)play(entry,node.dataset.mood||'idle');}
        for(const flight of [...flights])if(!flight.stage.isConnected)flight.finish();
    }
    function scheduleSync() {if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();});}

    // Shared with the separate Canvas preview. Coordinates and time are deterministic.
    function renderUltimate(ctx,seconds,W,H,options={}) {
        const t=clamp(seconds,0,3),from=options.from||{x:W*.22,y:H*.63},to=options.to||{x:W*.75,y:H*.44};
        const size=options.size||Math.min(W*.25,H*.47),flip=options.flip??to.x<from.x;
        const rise=smooth(t/.65),p=smooth((t-.95)/.8),burst=clamp((t-1.75)/.65);
        const center={x:lerp(from.x,to.x,p),y:lerp(from.y-size*.13,to.y,p)};
        // Keep the entire summoned effect inside the arena, including the upper
        // opponent's small top/right margins. The original actor keeps its size.
        const edgeX=Math.max(0,Math.min(to.x,W-to.x)-4),edgeY=Math.max(0,Math.min(to.y,H-to.y)-4),edge=Math.min(edgeX,edgeY);
        const smallBeeSize=Math.min(size*.23,edge*1.1);
        const orbitX=Math.min(size*.91,Math.max(0,edgeX-smallBeeSize*.55));
        const orbitY=Math.min(size*.74,Math.max(0,edgeY-smallBeeSize*.55));
        // The original bee hovers; the summoned bees form the honeycomb.
        const actorX=from.x+Math.sin(clamp((t-.95)/.95)*Math.PI)*size*.08*(flip?-1:1);
        const actorY=from.y-size*.1*rise+(t>=1.9?-Math.sin(clamp((t-1.9)/1.1)*Math.PI)*size*.08:0);
        let index=t<.4?Math.min(1,Math.floor(t/.2)):t<.95?2:t<1.9?4+Math.min(3,Math.floor((t-.95)/.95*4)):3;
        if(t<.95){
            for(let k=0;k<3;k++){const a=k*Math.PI*2/3+t*2;hex(ctx,from.x+Math.cos(a)*size*.48,from.y+Math.sin(a)*size*.36,size*.07,'#ffd56655','#e6b64c',rise*.75);}
        }
        if(t>=.35&&t<2.4){
            // The seven-cell cluster reaches 2.598r horizontally and 2.5r
            // vertically; reserve a little more room for its rounded stroke.
            const formed=smooth((t-.35)/1.4),fade=1-smooth((t-1.75)/.6),radius=Math.min(size*.38,edgeX/2.66,edgeY/2.56);
            // Center + six neighbors: a real hexagonal honeycomb with a visible target inside.
            for(let k=0;k<7;k++){
                const a=(k-1)*Math.PI/3,spacing=radius*Math.sqrt(3),dx=k?Math.cos(a)*spacing:0,dy=k?Math.sin(a)*spacing:0;
                const sx=from.x+Math.cos(a+t*3)*size*.5,sy=from.y+Math.sin(a+t*3)*size*.3;
                const x=lerp(sx,to.x+dx,formed),y=lerp(sy,to.y+dy,formed);
                if(t>=.95+k*.075)hex(ctx,x,y,radius*(.4+.6*formed),'#ffcf582d','#f7c34f',fade);
                const orbit=a+t*2,beeX=lerp(sx,to.x+Math.cos(orbit)*orbitX,formed),beeY=lerp(sy,to.y+Math.sin(orbit)*orbitY,formed);
                sprite(ctx,4+k%4,beeX,beeY,smallBeeSize,{flip,alpha:fade*.83});
            }
        }
        if(t>=1.75&&t<2.4){
            const particleSize=Math.min(size*.04,edge*.09),dropSize=Math.min(size*.033+1,particleSize);
            const drift=Math.min(burst*size*.13,edgeY*.16),padding=particleSize*1.7;
            const r=Math.min(size*(.3+burst*.9),Math.max(0,edgeX-padding),Math.max(0,(edgeY-drift-padding)/.78)),alpha=1-burst;
            for(let k=0;k<12;k++){const a=k*Math.PI/6;drop(ctx,to.x+Math.cos(a)*r,to.y+Math.sin(a)*r*.74+drift,dropSize,alpha);if(k%2===0)star(ctx,to.x+Math.cos(a+.2)*r*.8,to.y+Math.sin(a+.2)*r*.75,particleSize,alpha);}
        }
        // A small rising curl of honey links the summoning gesture to the swarm.
        if(t>=.95&&t<1.75){
            ctx.save();ctx.strokeStyle='#ffd572';ctx.lineWidth=Math.max(2,size*.018);ctx.globalAlpha=.7;ctx.setLineDash([size*.035,size*.035]);
            ctx.beginPath();ctx.moveTo(from.x,from.y);ctx.quadraticCurveTo((from.x+to.x)/2,H*.2,center.x,center.y);ctx.stroke();ctx.restore();
        }
        sprite(ctx,index,actorX,actorY,size,{flip});
        const nameVisible=t>=.65&&t<1.75;
        if(nameVisible&&options.showName!==false){
            ctx.save();const font=Math.max(12,Math.min(38,W*.043));ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const text='LỤC GIÁC HOÀNG KIM',width=Math.min(W-20,ctx.measureText(text).width+30),height=font+22,y=H*.22;
            ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect((W-width)/2,y-height/2,width,height,12);ctx.fill();ctx.stroke();
            ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,y,W-36);ctx.restore();
        }
        return {time:t,pose:index,nameVisible,attackStarted:t>=.95,impact:t>=1.75,victory:t>=1.9,flourish:t>=1.9,finished:t>=3};
    }
    function ultimate({source,victim}) {
        const actor=bee(source),stage=source?.closest('#battle-stage');
        if(!actor||!victim||!stage)return false;
        if(reduced.matches||document.hidden){actor.dataset.mood='win';sync();return true;}
        const ticket=generation;
        ready().then(image=>{
            if(!image||!actor.isConnected||!stage.isConnected||document.hidden||ticket!==generation)return;
            for(const flight of [...flights])if(flight.stage===stage)flight.finish();
            const canvas=document.createElement('canvas');canvas.className='arena-bee-ultimate';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const bounds=stage.getBoundingClientRect(),own=actor.getBoundingClientRect(),target=(victim.querySelector('.battle-pet')||victim).getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5),started=performance.now();
            canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const point=r=>({x:r.left-bounds.left+r.width/2,y:r.top-bounds.top+r.height/2});
            const from=point(own),to=point(target),announcement=stage.querySelector('#spell-announcement');
            let raf=0,done=false;
            const flight={stage,finish:()=>{
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();actor.classList.remove('bee-ultimate-hidden');stage.classList.remove('bee-ultimate-active');
                if(announcement?.isConnected&&announcement.textContent==='⬡ Lục Giác Hoàng Kim')announcement.textContent='';
                if(actor.isConnected&&actor.dataset.mood==='ultimate'){actor.dataset.mood='win';const entry=pets.get(actor);if(entry)play(entry,'win',true);}
                flights.delete(flight);
            }};
            stage.append(canvas);actor.classList.add('bee-ultimate-hidden');stage.classList.add('bee-ultimate-active');flights.add(flight);
            function draw(now) {
                raf=0;if(!stage.isConnected||document.hidden||suspended){flight.finish();return;}
                const seconds=Math.min((now-started)/1000,3);
                ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                const state=renderUltimate(ctx,seconds,W,H,{from,to,size:own.width,showName:false});
                if(announcement)announcement.textContent=state.nameVisible?'⬡ Lục Giác Hoàng Kim':'';
                canvas.dataset.time=String(Math.round(seconds*1000));canvas.dataset.pose=String(state.pose);canvas.dataset.impact=String(state.impact);
                if(seconds>=3){flight.finish();return;}raf=requestAnimationFrame(draw);
            }
            raf=requestAnimationFrame(draw);
        });
        return true;
    }
    function hit({source,victim,final=false,animateVictim=true}={}) {
        if(suspended)return false;
        sync();
        const actor=bee(source),target=bee(victim);
        if(target&&animateVictim){target.dataset.mood=final?'lose':'hit';const entry=mount(target);if(entry)play(entry,final?'lose':'hit',true);}
        if(!actor)return false;
        actor.dataset.mood=final?'ultimate':'attack';
        if(final)return ultimate({source,victim});
        const entry=mount(actor);if(entry)play(entry,'attack',true);
        return true;
    }
    function stop() {
        generation++;
        for(const entry of pets.values())cancel(entry);
        for(const flight of [...flights])flight.finish();
    }
    function configure(options={}) {
        if(options.asset&&options.asset!==settings.asset){stop();settings.asset=options.asset;atlas=null;loading=null;}
        if(options.frames)settings.frames=options.frames;
        for(const entry of pets.values())ready().then(image=>{if(image&&entry.node.isConnected)play(entry,entry.node.dataset.mood||'idle',true);});
    }
    function destroy() {
        suspended=true;observer?.disconnect();stop();
        for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('bee-canvas-ready');}pets.clear();
    }
    function start() {
        suspended=false;
        if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed)){if(!observer)observer=new MutationObserver(scheduleSync);
        observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});}sync();
    }
    function inspect() {return {loaded:Boolean(atlas),pets:[...pets.values()].map(e=>({mood:e.mode,pose:Number(e.canvas.dataset.pose),running:Boolean(e.raf),connected:e.node.isConnected})),flights:flights.size,reducedMotion:reduced.matches};}
    window.ArenaBeeAnimation={ready,configure,sync,hit,stop,destroy,start,renderUltimate,drawSprite:sprite,sample,inspect};
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else if(!suspended)for(const entry of pets.values())play(entry,entry.node.dataset.mood||'idle',true);});
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();if(atlas)for(const entry of pets.values())paintPet(entry,(durations[entry.mode]||0)/1000);});
    reduced.addEventListener('change',()=>{stop();if(atlas)for(const entry of pets.values())play(entry,entry.node.dataset.mood||'idle',true);});
})();
