/* Sao biển: finite Canvas actions backed by a lazy WebP atlas. */
(function () {
    'use strict';
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set(), timers = new Set();
    const modes = {idle:[0],attack:[8,9,10,11],hit:[1,2,1,0],lose:[3,2,1,0],win:[12,13,14,15]};
    const duration = {idle:0,attack:850,hit:700,lose:1800,win:1100,ultimate:3000};
    let asset = 'arena-art/sao-bien-v1/poses.webp', image = null, loading = null;
    let reactionsAsset = 'arena-art/sao-bien-v1/reactions.webp', reactionsImage = null;
    let metadataAsset = 'arena-art/sao-bien-v1/metadata.json', bounds = {};
    let frame = 0, generation = 0, scheduled = false, suspended = false, observer;
    const clamp = (n,a=0,b=1) => Math.max(a,Math.min(b,n));
    const ease = p => {p=clamp(p);return p*p*(3-2*p);};
    const clock = () => performance.now();
    const pet = node => node?.matches?.('.battle-pet.starfish') ? node : node?.querySelector?.('.battle-pet.starfish');

    function fetchImage(url) {
        return new Promise(resolve => {
            const atlas = new Image();
            atlas.onload = () => resolve(atlas);
            atlas.onerror = () => resolve(null);
            atlas.src = new URL(url,document.baseURI).href;
        });
    }
    function ready() {
        if (!loading) loading = Promise.all([image||fetchImage(asset),reactionsAsset?(reactionsImage||fetchImage(reactionsAsset)):null,
            fetch(new URL(metadataAsset,document.baseURI)).then(r=>r.ok?r.json():{}).catch(()=>({}))]).then(([poses,reactions,metadata])=>{
            image=poses;reactionsImage=reactions;bounds={poses:metadata.ultimate,reactions:metadata.reactions};if(!image)loading=null;redraw();return image;
        });
        return loading;
    }
    function fit(canvas) {
        const box = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1,2);
        const w = Math.max(1,Math.round(box.width*dpr)),h = Math.max(1,Math.round(box.height*dpr));
        if (canvas.width!==w || canvas.height!==h) {canvas.width=w;canvas.height=h;}
        return {w,h};
    }
    function sprite(ctx,index,x,y,size,{alpha=1,rotation=0,flip=false,sheet='poses'}={}) {
        const atlas=sheet==='reactions'?reactionsImage:image;
        if (!atlas) return;
        const manifest=bounds[sheet],f=manifest?.frames?.[index],col=index%4,row=Math.floor(index/4);
        const sx=f?.left??Math.round(col*atlas.naturalWidth/4),sy=f?.top??Math.round(row*atlas.naturalHeight/4);
        const sw=f?.width??Math.round((col+1)*atlas.naturalWidth/4)-sx,sh=f?.height??Math.round((row+1)*atlas.naturalHeight/4)-sy;
        const max=manifest?.frames?.reduce((n,entry)=>Math.max(n,entry.width,entry.height),0)||Math.max(sw,sh),scale=size/max;
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);if(flip)ctx.scale(-1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(atlas,sx,sy,sw,sh,-sw*scale/2,-sh*scale/2,sw*scale,sh*scale);ctx.restore();
    }
    function star(ctx,x,y,r,{alpha=1,fill='#ffce7d',rotation=0}={}) {
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.fillStyle=fill;ctx.beginPath();
        for(let i=0;i<10;i++){const a=i*Math.PI/5-Math.PI/2,d=i%2?r*.45:r;ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d);}
        ctx.closePath();ctx.fill();ctx.restore();
    }
    function sample(mood,t) {
        const p=clamp(t/(duration[mood]||1));
        if(mood==='ultimate')return t<650?Math.min(3,Math.floor(t/650*4)):t<950?4+Math.min(3,Math.floor((t-650)/300*4)):t<1900?8+Math.min(3,Math.floor((t-950)/950*4)):12+Math.min(3,Math.floor((t-1900)/1100*4));
        const sequence=modes[mood]||modes.idle;
        return sequence[Math.min(sequence.length-1,Math.floor(p*sequence.length))];
    }
    function paint(record,now) {
        const {node,canvas}=record;
        if(!node.isConnected){canvas.remove();pets.delete(node);return false;}
        if(!image)return false;
        const t=reduced.matches?duration[record.mood]:Math.max(0,now-record.start),p=clamp(t/(duration[record.mood]||1));
        const {w,h}=fit(canvas),ctx=canvas.getContext('2d');ctx.clearRect(0,0,w,h);
        let x=w/2,y=h*.52,rotation=0,size=Math.min(w,h)*.95;
        if(!reduced.matches){
            if(record.mood==='attack'){x+=Math.sin(p*Math.PI)*w*.12;y-=Math.sin(p*Math.PI)*h*.04;rotation=Math.sin(p*Math.PI)*.12;}
            if(record.mood==='hit'){x+=Math.sin(p*Math.PI*5)*(1-p)*w*.045;rotation=-Math.sin(p*Math.PI)*.12;}
            if(record.mood==='win'){y-=Math.sin(p*Math.PI)*h*.06;rotation=Math.sin(p*Math.PI*2)*.08;}
        }
        if(record.mood==='lose'){y+=p*h*.055;rotation=-p*.12;}
        const reactionRow={attack:0,hit:1,lose:2,idle:3}[record.mood];
        const sheet=reactionsImage&&reactionRow!==undefined?'reactions':'poses';
        const index=sheet==='reactions'?reactionRow*4+Math.min(3,Math.floor(p*4)):sample(record.mood,t);
        sprite(ctx,index,x,y,size,{rotation,sheet});
        if(record.mood==='hit'&&p<.9)for(let i=0;i<3;i++)star(ctx,w*(.32+i*.18),h*.13,Math.min(w,h)*.04,{alpha:1-p});
        if(record.mood==='lose'&&p>.4){
            ctx.save();ctx.globalAlpha=.7;ctx.fillStyle='#8bcecf';ctx.beginPath();ctx.ellipse(w*.62,h*.47,Math.max(1,w*.018),Math.max(1,h*.03),.2,0,Math.PI*2);ctx.fill();ctx.restore();
        }
        canvas.dataset.pose=String(index);canvas.dataset.sheet=sheet;canvas.dataset.time=String(Math.round(t));node.classList.add('starfish-ready');
        if(t>=duration[record.mood]&&!['idle','lose','win'].includes(record.mood)){
            record.mood='idle';record.start=now;node.dataset.mood='idle';paint(record,now);return false;
        }
        return !reduced.matches&&record.mood!=='idle'&&t<duration[record.mood];
    }
    function mountPet(node) {
        if(pets.has(node))return pets.get(node);
        suspended=false;
        const canvas=document.createElement('canvas');canvas.className='starfish-pose-canvas';canvas.setAttribute('aria-hidden','true');node.append(canvas);
        const record={node,canvas,mood:node.dataset.mood||'idle',start:clock()};pets.set(node,record);
        ready().then(()=>{if(node.isConnected)redraw();});return record;
    }
    function play(node,mood='idle') {
        const target=pet(node);if(!target)return false;
        suspended=false;
        const record=mountPet(target);record.mood=duration[mood]===undefined?'idle':mood;record.start=clock();target.dataset.mood=record.mood;
        redraw();return true;
    }
    function point(node,canvas) {
        const a=node.getBoundingClientRect(),b=canvas.getBoundingClientRect();
        return {x:(a.left+a.width/2-b.left)/b.width*canvas.width,y:(a.top+a.height*.53-b.top)/b.height*canvas.height,size:a.width/b.width*canvas.width};
    }
    function finish(flight) {
        if(flight.done)return;flight.done=true;flight.canvas.remove();flights.delete(flight);
        flight.actor.classList.remove('starfish-in-ultimate');flight.stage.classList.remove('starfish-ultimate-active');
        const label=flight.stage.querySelector('#spell-announcement');
        if(label?.dataset.starfish==='true'){if(label.textContent)label.textContent='';delete label.dataset.starfish;}
        if(flight.actor.isConnected&&flight.actor.dataset.mood==='ultimate'){
            const record=pets.get(flight.actor);if(record){record.mood='idle';record.start=clock();}
            flight.actor.dataset.mood='idle';
        }
    }
    function renderUltimate(ctx,t,W,H,{from,to,size,flip=false}) {
        const windup=clamp(t/.65),orbit=clamp((t-.95)/.65),burst=clamp((t-1.75)/.75),r=size*(.4+.18*Math.sin(orbit*Math.PI));
        const index=sample('ultimate',t*1000);
        // Five real five-armed silhouettes orbit the target and join as a pentagram.
        if(t>=.35&&t<1.9){
            const emerge=ease((t-.35)/.6),positions=[];
            for(let i=0;i<5;i++){
                const a=-Math.PI/2+i*Math.PI*2/5+orbit*Math.PI*1.2;
                const end={x:to.x+Math.cos(a)*r,y:to.y+Math.sin(a)*r*.56};
                const x=from.x+(end.x-from.x)*emerge,y=from.y+(end.y-from.y)*emerge;
                positions.push({x,y});sprite(ctx,Math.min(7,4+i%4),x,y,size*.43,{alpha:.35+.42*emerge,rotation:a+Math.PI/2,flip});
            }
            if(t>=1.35){
                ctx.save();ctx.globalAlpha=clamp((t-1.35)/.25)*.9;ctx.strokeStyle='#fff0ae';ctx.lineWidth=Math.max(2,W*.004);ctx.shadowColor='#ffbd73';ctx.shadowBlur=W*.015;ctx.beginPath();
                for(let i=0;i<=5;i++){const p=positions[(i*2)%5];i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}ctx.stroke();ctx.restore();
            }
        }
        if(t>=1.65&&t<2.12){
            const a=Math.sin(clamp((t-1.65)/.47)*Math.PI),beamW=size*.52;
            const gradient=ctx.createLinearGradient(to.x,0,to.x,to.y+size*.3);gradient.addColorStop(0,'#fff7ce00');gradient.addColorStop(.55,'#fff7cebb');gradient.addColorStop(1,'#ffd17bf0');
            ctx.save();ctx.globalAlpha=a;ctx.fillStyle=gradient;ctx.fillRect(to.x-beamW/2,0,beamW,to.y+size*.26);ctx.restore();
        }
        if(t>=1.75&&t<2.65)for(let i=0;i<25;i++){
            const a=i*2.39996,rad=size*(.12+burst*(.8+(i%4)*.18));
            star(ctx,to.x+Math.cos(a)*rad,to.y+Math.sin(a)*rad*.7,size*(.025+(i%3)*.011),{alpha:1-burst,rotation:a+burst,fill:i%2?'#fff4c5':'#ffbe73'});
        }
        const hop=t>=1.9?Math.sin(clamp((t-1.9)/.7)*Math.PI)*size*.09:Math.sin(windup*Math.PI)*-size*.025;
        sprite(ctx,index,from.x,from.y-hop,size,{flip,rotation:t>=1.9?Math.sin(clamp((t-1.9)/.75)*Math.PI*2)*.1:0});
        const nameVisible=t>=.65&&t<1.73;
        if(nameVisible){
            const font=Math.max(12,Math.min(W*.043,38)),text='NGŨ TINH TỎA SÁNG';ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const width=Math.min(W-20,ctx.measureText(text).width+30),height=font+22,y=H*.22;
            ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect((W-width)/2,y-height/2,width,height,12);ctx.fill();ctx.stroke();ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,y,W-38);ctx.restore();
        }
        return {pose:index,nameVisible,impact:t>=1.75,finished:t>=3};
    }
    function drawFlight(flight,now) {
        if(!flight.actor.isConnected||!flight.target.isConnected||!flight.stage.isConnected){finish(flight);return false;}
        const t=Math.min(3,(now-flight.start)/1000),{w,h}=fit(flight.canvas),ctx=flight.canvas.getContext('2d');ctx.clearRect(0,0,w,h);
        const from=point(flight.actor,flight.canvas),to=point(flight.target,flight.canvas),state=renderUltimate(ctx,t,w,h,{from,to,size:from.size,flip:to.x<from.x});
        Object.assign(flight.canvas.dataset,{time:String(Math.round(t*1000)),pose:String(state.pose),impact:String(state.impact),nameVisible:String(state.nameVisible)});
        const label=flight.stage.querySelector('#spell-announcement');if(label){
            const text=state.nameVisible?'✦ Ngũ Tinh Tỏa Sáng':'';
            label.dataset.starfish='true';
            if(label.textContent!==text)label.textContent=text;
        }
        if(t>=3){finish(flight);return false;}return true;
    }
    function redraw() {
        const now=clock();let active=false;
        for(const record of pets.values())active=paint(record,now)||active;
        for(const flight of [...flights])active=drawFlight(flight,now)||active;
        if(active&&!suspended&&!document.hidden&&!reduced.matches&&!frame)frame=requestAnimationFrame(()=>{frame=0;redraw();});
    }
    function later(callback,delay) {
        const ticket=generation,id=setTimeout(()=>{timers.delete(id);if(ticket===generation)callback();},delay);timers.add(id);
    }
    function ultimate(source,victim) {
        const actor=pet(source),target=victim?.querySelector?.('.battle-pet')||victim,stage=source?.closest?.('#battle-stage');
        if(!actor||!target||!stage)return false;
        if(reduced.matches||document.hidden){play(actor,'win');return true;}
        const ticket=generation;
        ready().then(atlas=>{
            if(!atlas||ticket!==generation||!stage.isConnected||document.hidden)return;
            for(const old of [...flights])if(old.stage===stage)finish(old);
            const canvas=document.createElement('canvas');canvas.className='starfish-ultimate-canvas';canvas.setAttribute('aria-hidden','true');stage.append(canvas);
            actor.classList.add('starfish-in-ultimate');stage.classList.add('starfish-ultimate-active');
            flights.add({canvas,actor,target,stage,start:clock(),done:false});redraw();
        });return true;
    }
    function animate(targetSelector,sourceSelector,final=false) {
        const source=typeof sourceSelector==='string'?document.querySelector(sourceSelector):sourceSelector;
        const target=typeof targetSelector==='string'?document.querySelector(targetSelector):targetSelector;
        const attacker=pet(source),defender=pet(target);
        // Other renderers set the victim mood at their own impact time.
        if(!attacker)return false;
        const impact=()=>{
            if(!target?.isConnected)return;target.dataset.spell='starfish';target.classList.add('taking-hit');
            const victim=target.querySelector('.battle-pet');if(victim)victim.dataset.mood=final?'lose':'hit';
            if(defender)play(defender,final?'lose':'hit');
        };
        play(attacker,final?'ultimate':'attack');
        if(final){ultimate(source,target);later(impact,reduced.matches?0:1750);}else impact();
        later(()=>{target?.classList.remove('taking-hit');const victim=target?.querySelector('.battle-pet');if(victim?.isConnected&&!final)victim.dataset.mood='idle';},final?3000:850);
        return true;
    }
    function sync() {
        scheduled=false;
        for(const record of [...pets.values()])if(!record.node.isConnected){record.canvas.remove();pets.delete(record.node);}
        for(const node of document.querySelectorAll('.battle-pet.starfish')){
            const record=mountPet(node),mood=node.dataset.mood||'idle';
            if(record.mood!==mood){record.mood=mood;record.start=clock();}
        }
        redraw();
    }
    function mount() {suspended=false;sync();}
    function stop() {
        suspended=true;
        generation++;cancelAnimationFrame(frame);frame=0;
        for(const id of timers)clearTimeout(id);timers.clear();for(const flight of [...flights])finish(flight);
    }
    function destroy() {stop();for(const {canvas,node} of pets.values()){canvas.remove();node.classList.remove('starfish-ready');}pets.clear();}
    function configure(options={}) {
        if(options.asset&&options.asset!==asset){asset=options.asset;image=null;loading=null;}
        if(options.reactionsAsset&&options.reactionsAsset!==reactionsAsset){reactionsAsset=options.reactionsAsset;reactionsImage=null;loading=null;}
        if(options.metadataAsset&&options.metadataAsset!==metadataAsset){metadataAsset=options.metadataAsset;loading=null;}
        if(options.modes)Object.assign(modes,options.modes);
        ready().then(sync);
    }
    window.ArenaStarfish={mount,play,animate,ultimate,stop,destroy,ready,configure,renderUltimate,drawSprite:sprite,
        inspect:()=>({loaded:Boolean(image),reactionsLoaded:Boolean(reactionsImage),asset,reactionsAsset,reducedMotion:reduced.matches,pets:[...pets.values()].map(r=>({mood:r.mood,pose:Number(r.canvas.dataset.pose),sheet:r.canvas.dataset.sheet,time:Number(r.canvas.dataset.time),connected:r.node.isConnected})),flights:flights.size,running:Boolean(frame),timers:timers.size})};
    function start(){
        observer=new MutationObserver(records=>{
            // Text labels and Canvas overlays are output, not new characters.
            // Observing their writes would schedule redraw from its own output.
            const relevant=records.some(record=>record.type==='attributes'
                ?record.target.matches('.battle-pet.starfish')
                :[...record.addedNodes,...record.removedNodes].some(node=>node.nodeType===1&&
                    (node.matches('.battle-pet.starfish')||node.querySelector('.battle-pet.starfish'))));
            if(relevant&&!scheduled){scheduled=true;queueMicrotask(sync);}
        });
        observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});sync();
    }
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else{suspended=false;redraw();}});
    window.addEventListener('pagehide',stop);window.addEventListener('resize',()=>{for(const flight of [...flights])finish(flight);redraw();});
    reduced.addEventListener('change',()=>{stop();suspended=false;redraw();});
})();
