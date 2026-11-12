/* 5BMath — Chim sẻ. Visuals only; damage and outcomes belong to Arena. */
(() => {
    'use strict';
    if (typeof window === 'undefined' || window.ArenaSparrowAnimation) return;
    const settings = {
        asset:'arena-art/chim-se/poses.webp', metadata:'arena-art/chim-se/poses.json', actionsAsset:null,
        frames:null, actionFrames:null,
        modes:{idle:[0],windup:[0,1,2,3],flight:[4,5,6,7],strike:[8,9],win:[12,13],attack:[8,9],hit:[10,11],lose:[14,15]},
    };
    const duration = {attack:1000,hit:1100,win:1500,lose:2400};
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const pets = new Map(), flights = new Set(), pictures = new Map();
    let observer, queued=false, enabled=true, revision=0, metadataPromise=null;
    const clamp = n => Math.min(1,Math.max(0,n));
    const ease = n => {n=clamp(n);return n*n*(3-2*n);};
    const lerp = (a,b,n) => a+(b-a)*n;
    const pet = node => node?.matches?.('.battle-pet.sparrow') ? node : node?.querySelector?.('.battle-pet.sparrow');
    const atlasFor = mode => ['idle','attack','hit','lose'].includes(mode) && settings.actionsAsset ? 'actions' : 'ultimate';
    const assetFor = sheet => sheet==='actions' ? settings.actionsAsset : settings.asset;

    function metadata() {
        if(settings.frames)return Promise.resolve(settings.frames);
        if(!metadataPromise)metadataPromise=fetch(new URL(settings.metadata,document.baseURI)).then(r=>{
            if(!r.ok)throw Error('Chim sẻ: thiếu metadata');return r.json();
        }).then(spec=>{
            if(!Array.isArray(spec.frames)||spec.frames.length!==16||spec.frames.some(f=>![f.left,f.top,f.width,f.height].every(Number.isFinite)||f.width<=0||f.height<=0))throw Error('Chim sẻ: frame bounds không hợp lệ');
            settings.frames=spec.frames;return spec.frames;
        }).catch(()=>{metadataPromise=null;return null;});
        return metadataPromise;
    }
    function load(sheet='ultimate') {
        const asset=assetFor(sheet);
        if(!asset)return Promise.resolve(null);
        if(pictures.has(asset))return pictures.get(asset);
        const imagePending=new Promise(resolve=>{
            const img=new Image();
            img.onload=()=>resolve(img);
            img.onerror=()=>{pictures.delete(asset);resolve(null);};
            img.src=new URL(asset,document.baseURI).href;
        });
        const pending=Promise.all([imagePending,metadata()]).then(([img,frames])=>{
            if(!img||!frames){pictures.delete(asset);return null;}return img;
        });
        pictures.set(asset,pending);return pending;
    }
    function frame(img,index,sheet) {
        const custom=sheet==='actions'?settings.actionFrames:settings.frames;
        if(custom?.[index]){const f=custom[index];return {x:f.left??f.x,y:f.top??f.y,w:f.width,h:f.height};}
        const w=img.naturalWidth,h=img.naturalHeight,x=index%4,y=Math.floor(index/4);
        return {x:Math.round(x*w/4),y:Math.round(y*h/4),w:Math.round((x+1)*w/4)-Math.round(x*w/4),h:Math.round((y+1)*h/4)-Math.round(y*h/4)};
    }
    function sprite(ctx,img,sheet,index,x,y,size,{flip=false,rotation=0,alpha=1}={}) {
        const f=frame(img,index,sheet),bounds=sheet==='actions'?settings.actionFrames:settings.frames;
        const maxSide=bounds?Math.max(...bounds.map(b=>Math.max(b.width,b.height))):Math.max(f.w,f.h),scale=size/maxSide;
        ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);
        ctx.drawImage(img,f.x,f.y,f.w,f.h,-f.w*scale/2,-f.h*scale/2,f.w*scale,f.h*scale);ctx.restore();
    }
    function pose(mode,progress) {
        const list=settings.modes[mode]||settings.modes.idle;
        return list[Math.min(list.length-1,Math.floor(clamp(progress)*list.length))]??0;
    }
    function star(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle='#ffcf7b';ctx.beginPath();
        for(let i=0;i<10;i++){const a=i*Math.PI/5-Math.PI/2,d=i%2?r*.44:r;ctx.lineTo(x+Math.cos(a)*d,y+Math.sin(a)*d);}
        ctx.closePath();ctx.fill();ctx.restore();
    }
    function feather(ctx,x,y,size,angle,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;
        ctx.fillStyle='#ffbe73';ctx.beginPath();ctx.ellipse(0,0,size*.24,size,0,0,Math.PI*2);ctx.fill();
        ctx.strokeStyle='#fff9ed';ctx.lineWidth=Math.max(1,size*.1);ctx.beginPath();ctx.moveTo(0,-size*.7);ctx.lineTo(0,size*.9);ctx.stroke();ctx.restore();
    }
    function resize(entry) {
        const pixels=Math.min(512,Math.max(1,Math.ceil(entry.node.getBoundingClientRect().width*Math.min(devicePixelRatio||1,2))));
        if(entry.canvas.width!==pixels){entry.canvas.width=pixels;entry.canvas.height=pixels;}
    }
    function paint(entry,elapsed) {
        if(!entry.image)return;
        resize(entry);
        const {ctx,canvas,mood}=entry,S=canvas.width,p=clamp(elapsed/(duration[mood]||1));
        let x=S*.5,y=S*.5,rotation=0;
        ctx.clearRect(0,0,S,S);
        if(!reduced.matches){
            if(mood==='attack'){x+=Math.sin(p*Math.PI)*S*.08;y-=Math.sin(p*Math.PI)*S*.07;rotation=-Math.sin(p*Math.PI)*.08;}
            if(mood==='hit'){x+=Math.sin(p*Math.PI*6)*(1-p)*S*.04;rotation=Math.sin(p*Math.PI)*.09;}
            if(mood==='lose'){y+=ease(p)*S*.045;rotation=-ease(p)*.035;}
            if(mood==='win')y-=Math.sin(p*Math.PI)*S*.07;
        }
        sprite(ctx,entry.image,atlasFor(mood),pose(mood,reduced.matches?1:p),x,y,S*.96,{rotation});
        if(mood==='hit'&&p<.8&&!reduced.matches)for(let i=0;i<3;i++)star(ctx,S*(.35+i*.15),S*.15+Math.sin(p*12+i)*S*.025,S*.03,1-p);
    }
    function cancel(entry) {if(entry.raf)cancelAnimationFrame(entry.raf);entry.raf=0;entry.token++;}
    function playEntry(entry,mood,force=false) {
        if(!force&&entry.mood===mood)return;
        cancel(entry);entry.mood=mood;entry.started=performance.now();const token=entry.token;
        load(atlasFor(mood)).then(img=>{
            if(!img||token!==entry.token||!entry.node.isConnected||!enabled)return;
            entry.image=img;
            if(!entry.canvas.isConnected)entry.node.append(entry.canvas);
            entry.node.classList.add('sparrow-canvas-ready');
            paint(entry,reduced.matches||document.hidden?(duration[mood]||0):0);
            if(reduced.matches||document.hidden||!duration[mood])return;
            const tick=now=>{
                entry.raf=0;
                if(token!==entry.token||!entry.node.isConnected||document.hidden||!enabled)return;
                const elapsed=Math.min(now-entry.started,duration[mood]);paint(entry,elapsed);
                if(elapsed<duration[mood])entry.raf=requestAnimationFrame(tick);
            };
            entry.raf=requestAnimationFrame(tick);
        });
    }
    function mount(node) {
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.className='sparrow-canvas';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mood:null,raf:0,token:0,image:null};pets.set(node,entry);return entry;
    }
    function play(node,mood='idle') {
        node=pet(node);if(!node||!enabled)return false;
        node.dataset.mood=mood;const entry=mount(node);if(entry)playEntry(entry,mood,true);return Boolean(entry);
    }
    function sync(root=document) {
        if(!enabled)return;
        for(const [node,entry] of pets)if(!node.isConnected){cancel(entry);pets.delete(node);}
        const nodes=[...root.querySelectorAll('.battle-pet.sparrow')];if(root.matches?.('.battle-pet.sparrow'))nodes.unshift(root);
        for(const node of nodes){const entry=mount(node);if(entry)playEntry(entry,node.dataset.mood||'idle');}
        for(const flight of [...flights])if(!flight.stage.isConnected)flight.finish();
    }
    function scheduleSync() {if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();});}
    function banner(ctx,W,H) {
        const font=Math.max(12,Math.min(23,W*.043));ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
        const text='LỐC XOÁY RÍU RÍT',w=Math.min(W-16,ctx.measureText(text).width+28),h=font+22,y=H*.34;
        ctx.fillStyle='#1f6248f5';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect((W-w)/2,y-h/2,w,h,12);ctx.fill();ctx.stroke();
        ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,y,W-32);
    }
    function ultimate({source,victim}={}) {
        const actor=pet(source),stage=source?.closest('#battle-stage');
        if(!enabled||!actor||!victim||!stage)return false;
        if(reduced.matches||document.hidden){play(actor,'win');return true;}
        const requestRevision=revision;
        load().then(img=>{
            if(!img||!enabled||requestRevision!==revision||!stage.isConnected||!actor.isConnected||document.hidden)return;
            for(const flight of [...flights])if(flight.stage===stage)flight.finish();
            const canvas=document.createElement('canvas');canvas.className='sparrow-ultimate-canvas';canvas.setAttribute('aria-hidden','true');
            const ctx=canvas.getContext('2d');if(!ctx)return;
            const bounds=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),b=(victim.querySelector('.battle-pet')||victim).getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5),size=a.width;
            if(!W||!H)return;
            canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);
            const A={x:a.left-bounds.left+a.width/2,y:a.top-bounds.top+a.height/2},B={x:b.left-bounds.left+b.width/2,y:Math.max(size*.72,Math.min(H-size*.72,b.top-bounds.top+b.height/2))};
            const flip=B.x<A.x,started=performance.now();let raf=0,done=false;
            const flight={stage,finish:()=>{
                if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();actor.classList.remove('sparrow-in-ultimate');
                stage.classList.remove('sparrow-ultimate-active');flights.delete(flight);
            }};
            actor.classList.add('sparrow-in-ultimate');stage.classList.add('sparrow-ultimate-active');stage.append(canvas);flights.add(flight);
            function draw(now) {
                raf=0;if(!enabled||!stage.isConnected||!actor.isConnected||document.hidden){flight.finish();return;}
                const t=Math.min(3,(now-started)/1000);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                let x=A.x,y=A.y,index=pose('windup',t/.65),rotation=0;
                if(t>=.95&&t<1.9){
                    const p=clamp((t-.95)/.8),travel=ease(p/.3),angle=p*Math.PI*4;
                    x=lerp(A.x,B.x,travel)+Math.cos(angle)*size*.28*Math.sin(p*Math.PI);
                    y=lerp(A.y,B.y,travel)-Math.sin(p*Math.PI)*size*.6+Math.sin(angle)*size*.12;
                    index=pose(t<1.6?'flight':'strike',t<1.6?(p*3)%1:(t-1.6)/.3);rotation=Math.sin(angle)*.08;
                    for(let k=0;k<5;k++){
                        const phase=angle+k*Math.PI*2/5,r=size*(.34+.11*Math.sin(p*Math.PI));
                        sprite(ctx,img,'ultimate',pose('flight',(p*3+k*.2)%1),B.x+Math.cos(phase)*r,B.y+Math.sin(phase)*r*.55-size*.12,size*.38,{flip,rotation:Math.sin(phase)*.12,alpha:Math.min(1,travel*.9)});
                    }
                    ctx.lineCap='round';
                    for(let k=0;k<5;k++){
                        const r=size*(.16+k*.08),start=angle+k*.5;
                        ctx.strokeStyle=k%2?'#fff9ed':'#ffbe73';ctx.globalAlpha=.7*travel;ctx.lineWidth=Math.max(1.5,size*.015);
                        ctx.beginPath();ctx.ellipse(B.x,B.y-size*.06,r,r*.52,-.3,start,start+Math.PI*1.35);ctx.stroke();
                    }
                    ctx.globalAlpha=1;
                    for(let k=0;k<8;k++){
                        const angle2=angle+k*Math.PI/4,r=size*(.4+k*.025);
                        feather(ctx,B.x+Math.cos(angle2)*r,B.y+Math.sin(angle2)*r*.62,size*.065,angle2+.5,travel*.8);
                        if(k%2===0){ctx.fillStyle='#1f6248';ctx.font=`700 ${Math.max(11,size*.14)}px Arial`;ctx.fillText('♪',B.x+Math.cos(angle2+.3)*r,B.y+Math.sin(angle2+.3)*r*.65);}
                    }
                }else if(t>=1.9){const p=ease((t-1.9)/.4);x=lerp(B.x,A.x,p);y=lerp(B.y,A.y,p)-Math.sin(p*Math.PI)*size*.3;index=pose('win',(t-1.9)/1.1);}
                else y-=Math.sin(t/.95*Math.PI)*size*.08;
                if(t>=1.75&&t<2.35){
                    const p=(t-1.75)/.6;
                    for(let k=0;k<12;k++){const a2=k*Math.PI/6,r=size*(.25+p*.9);star(ctx,B.x+Math.cos(a2)*r,B.y+Math.sin(a2)*r*.7,size*.045,1-p);}
                    if(t<2.05){ctx.fillStyle='#1f6248';ctx.font=`800 ${Math.max(12,size*.16)}px Arial`;ctx.textAlign='center';ctx.fillText('Chíp!',B.x,B.y-size*.45);}
                }
                x=Math.max(size*.52,Math.min(W-size*.52,x));y=Math.max(size*.52,Math.min(H-size*.52,y));
                sprite(ctx,img,'ultimate',index,x,y,size,{flip,rotation});
                if(t>=.65&&t<=1.55)banner(ctx,W,H);
                if(t>=3){flight.finish();return;}raf=requestAnimationFrame(draw);
            }
            raf=requestAnimationFrame(draw);
        });return true;
    }
    function hit({source,victim,final=false}={}) {
        if(!enabled)return false;
        const target=pet(victim),actor=pet(source);
        if(target)play(target,'hit');
        if(!actor)return false;
        play(actor,final?'ultimate':'attack');return final?ultimate({source,victim}):true;
    }
    function stop() {revision++;for(const entry of pets.values())cancel(entry);for(const flight of [...flights])flight.finish();}
    function configure(options={}) {
        stop();for(const name of ['asset','metadata','actionsAsset','frames','actionFrames'])if(name in options)settings[name]=options[name];
        if(options.modes)Object.assign(settings.modes,options.modes);
        for(const entry of pets.values())playEntry(entry,entry.node.dataset.mood||'idle',true);
    }
    function destroy() {
        enabled=false;observer?.disconnect();stop();
        for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('sparrow-canvas-ready');}pets.clear();
    }
    window.ArenaSparrowAnimation={mountManaged(root=document){enabled=true;sync(root);},configure,sync,play,hit,ultimate,stop,destroy,ready:()=>load().then(Boolean)};
    function start() {observer=new MutationObserver(scheduleSync);observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});sync();}
    if(!(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed))document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else for(const entry of pets.values())playEntry(entry,entry.node.dataset.mood||'idle',true);});
    window.addEventListener('pagehide',stop);
    window.addEventListener('resize',()=>{stop();for(const entry of pets.values()){if(entry.image)paint(entry,duration[entry.mood]||0);else playEntry(entry,entry.node.dataset.mood||'idle',true);}});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())playEntry(entry,entry.node.dataset.mood||'idle',true);});
})();
