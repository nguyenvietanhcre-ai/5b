/* 5BMath — Cú mèo / Ánh Mắt Đêm Trăng. Canvas presentation only. */
const OwlAnimation = (() => {
    'use strict';
    const asset = 'arena-art/owl/poses.webp';
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const durations = {idle:0,attack:1000,hit:1050,lose:2200,win:1100,ultimate:3000};
    const active = new Map(), mounted = new Map(), requests = new WeakMap(), moods = new WeakMap(), timers = new Set(), presentations = new Set();
    let atlas, bounds, loading, observer, raf = 0, generation = 0;
    const clamp = x => Math.max(0,Math.min(1,x));
    const ease = x => {x=clamp(x);return x*x*(3-2*x);};
    const lerp = (a,b,t) => a+(b-a)*t;
    const isOwl = node => Boolean(node?.classList.contains('cu-meo'));

    function ready() {
        if (loading) return loading;
        const image = new Promise((resolve,reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => reject(Error('Không tải được tư thế Cú mèo.'));
            img.src = new URL(asset,document.baseURI).href;
        });
        const frames = fetch(new URL('arena-art/owl/poses.json',document.baseURI)).then(r => r.ok?r.json():null).catch(() => null);
        loading = Promise.all([image,frames]).then(([img,manifest]) => {
            atlas=img;
            bounds=manifest?.frames?.length===16?manifest.frames:null;
            if (bounds) {
                const maxHeight=Math.max(...bounds.map(f=>f.height));
                const maxWidth=Math.max(...bounds.map(f=>f.width));
                bounds=bounds.map(f=>({...f,scaleHeight:Math.max(maxHeight,maxWidth)}));
            }
        }).catch(error => {loading=null;throw error;});
        return loading;
    }
    function frame(index) {
        index=Math.max(0,Math.min(15,Number.isFinite(index)?Math.floor(index):0));
        if(bounds) return bounds[index];
        const left=Math.round(index%4*atlas.naturalWidth/4),top=Math.round(Math.floor(index/4)*atlas.naturalHeight/4);
        const width=Math.round((index%4+1)*atlas.naturalWidth/4)-left;
        const height=Math.round((Math.floor(index/4)+1)*atlas.naturalHeight/4)-top;
        return {left,top,width,height,scaleHeight:Math.max(width,height)};
    }
    function sprite(ctx,index,x,feet,size,{alpha=1,flip=false,rotation=0}={}) {
        if(!atlas)return;
        const f=frame(index),scale=size/f.scaleHeight;
        ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(atlas,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);
        ctx.restore();
    }
    function star(ctx,x,y,r,alpha=1) {
        ctx.save();ctx.globalAlpha*=clamp(alpha);ctx.translate(x,y);ctx.fillStyle='#ffcf7b';ctx.beginPath();
        for(let i=0;i<8;i++) {const a=i*Math.PI/4-Math.PI/2,d=i%2?r*.27:r;ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d);}
        ctx.closePath();ctx.fill();ctx.restore();
    }
    function canvasFor(node) {
        let canvas=mounted.get(node);
        if(!canvas) {
            canvas=document.createElement('canvas');canvas.className='owl-canvas';canvas.width=384;canvas.height=384;
            canvas.setAttribute('aria-hidden','true');node.append(canvas);mounted.set(node,canvas);
        }
        return canvas;
    }
    function drawPet(node,action,milliseconds) {
        const canvas=canvasFor(node),ctx=canvas.getContext('2d');if(!ctx)return;
        ctx.clearRect(0,0,384,384);
        const u=clamp(milliseconds/(durations[action]||1));
        let index=0,x=192,feet=363,rotation=0;
        if(action==='attack') {index=4+Math.min(3,Math.floor(u*4));x+=Math.sin(u*Math.PI)*27;feet-=Math.sin(u*Math.PI)*35;}
        else if(action==='hit') {index=u<.42?8:9;x+=Math.sin(u*Math.PI*5)*(1-u)*12;rotation=Math.sin(u*Math.PI)*-.07;}
        else if(action==='lose') {index=u<.35?9:u<.7?10:11;feet+=ease(u)*9;}
        else if(action==='win') {index=12+Math.min(3,Math.floor(u*4));feet-=Math.sin(u*Math.PI)*12;}
        sprite(ctx,index,x,feet,330,{rotation});
        if(action==='hit'&&u<.82)for(let i=0;i<3;i++)star(ctx,150+i*43,45+Math.sin(u*10+i)*9,9,1-u);
    }
    function overlayFor(node) {
        const stage=node.closest('#battle-stage'),fighter=node.closest('.fighter');
        const target=stage?.querySelector(fighter?.id==='fighter-me'?'#fighter-opponent .battle-pet':'#fighter-me .battle-pet');
        if(!stage||!target)return null;
        const canvas=document.createElement('canvas');canvas.className='owl-ultimate-canvas';canvas.setAttribute('aria-hidden','true');
        stage.append(canvas);stage.classList.add('owl-ultimate-active');node.classList.add('owl-in-ultimate');
        return {stage,canvas,target};
    }
    function drawUltimate(job,milliseconds) {
        const {stage,canvas,target}=job.overlay,box=stage.getBoundingClientRect();
        if(box.width<=0||box.height<=0)return;
        const W=768,H=768*box.height/box.width;
        const pixelScale=Math.min(1.5,devicePixelRatio||1)*Math.min(1,box.width/W);
        const cw=Math.max(1,Math.round(W*pixelScale)),ch=Math.max(1,Math.round(H*pixelScale));
        if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch;}
        const ctx=canvas.getContext('2d');if(!ctx)return;
        ctx.setTransform(canvas.width/W,0,0,canvas.height/H,0,0);ctx.clearRect(0,0,W,H);
        const point=node=>{const r=node.getBoundingClientRect();return {x:(r.x-box.x+r.width/2)/box.width*W,y:(r.y-box.y+r.height)/box.height*H,size:r.width/box.width*W};};
        const a=point(job.node),b=point(target),t=milliseconds/1000;
        const night=ease(t/.55)*(1-ease((t-2.1)/.9));
        ctx.fillStyle=`rgba(18,29,62,${night*.78})`;ctx.fillRect(0,0,W,H);
        for(let i=0;i<18;i++)star(ctx,26+(i*137)%716,H*(.09+(i*7%16)*.037),i%3===0?4:2,night*.8);
        let x=a.x,feet=a.y,index=0,rotation=0;
        if(t<.95) {index=Math.min(3,Math.floor(t/.95*4));feet-=Math.sin(t/.95*Math.PI)*a.size*.035;}
        else if(t<1.75) {
            const u=clamp((t-.95)/.8),p=ease(u);
            x=lerp(a.x,b.x,p);feet=lerp(a.y,b.y,p)-Math.sin(u*Math.PI)*Math.min(H*.22,a.size*.75);
            index=4+Math.min(3,Math.floor(u*4));rotation=Math.sin(u*Math.PI)*-.08;
            for(let i=3;i>0;i--) {
                const q=clamp(p-i*.07);
                sprite(ctx,index,lerp(a.x,b.x,q),lerp(a.y,b.y,q)-Math.sin(q*Math.PI)*a.size*.55,a.size*.94,{alpha:.10+(3-i)*.04,flip:b.x<a.x});
            }
        } else if(t<1.9) {x=b.x;feet=b.y;index=7;}
        else {
            const u=ease((t-1.9)/.38);x=lerp(b.x,a.x,u);feet=lerp(b.y,a.y,u)-Math.sin(u*Math.PI)*a.size*.23;
            index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));
        }
        if(t>=1.28&&t<2.48) {
            const u=clamp((t-1.28)/.47),fade=1-ease((t-1.94)/.54),r=b.size*(.40+.17*u),cx=b.x,cy=b.y-b.size*.45;
            // Two dark wing arcs close into a moon around the target, followed by a warm flash.
            ctx.save();ctx.globalAlpha=fade;ctx.lineCap='round';
            for(const side of [-1,1]) {
                ctx.strokeStyle='#736b9b';ctx.lineWidth=b.size*.075;ctx.beginPath();
                ctx.arc(cx,cy,r,side<0?Math.PI:0,(side<0?Math.PI:0)+Math.PI*u);ctx.stroke();
                ctx.strokeStyle='#fff0b4';ctx.lineWidth=b.size*.025;ctx.stroke();
            }
            if(t>=1.75) {
                const p=clamp((t-1.75)/.62);
                ctx.fillStyle=`rgba(255,241,188,${(1-p)*.32})`;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();
                for(let i=0;i<12;i++){const angle=i*Math.PI/6;star(ctx,cx+Math.cos(angle)*(r+p*b.size*.45),cy+Math.sin(angle)*(r+p*b.size*.45),6+4*(1-p),1-p);}
            }
            ctx.restore();
        }
        sprite(ctx,index,x,feet,a.size*.94,{flip:b.x<a.x,rotation});
        if(t>=.25&&t<1.1) {
            const glow=ease((t-.25)/.4)*(1-ease((t-.95)/.15));
            ctx.save();ctx.globalAlpha=glow*.25;ctx.fillStyle='#fff0b4';ctx.shadowColor='#ffda87';ctx.shadowBlur=12;
            for(const eye of [-1,1]) {ctx.beginPath();ctx.ellipse(x+eye*a.size*.12,feet-a.size*.59,a.size*.055,a.size*.049,0,0,Math.PI*2);ctx.fill();}
            ctx.restore();
        }
        if(t>=.65&&t<1.9) {
            const text='ÁNH MẮT ĐÊM TRĂNG',font=25;
            ctx.save();ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
            const width=Math.min(W-30,ctx.measureText(text).width+40),y=H*.30;
            ctx.fillStyle='#1f6248';ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect((W-width)/2,y-24,width,48,14);ctx.fill();ctx.stroke();
            ctx.fillStyle='#fff9ed';ctx.fillText(text,W/2,y,W-50);ctx.restore();
        }
    }
    function cleanJob(job) {
        job.overlay?.canvas.remove();job.node.classList.remove('owl-in-ultimate');
        if(job.overlay&&!job.overlay.stage.querySelector('.owl-ultimate-canvas'))job.overlay.stage.classList.remove('owl-ultimate-active');
    }
    function tick(now) {
        raf=0;if(document.hidden)return;
        for(const [node,job]of active) {
            if(!node.isConnected){cleanJob(job);active.delete(node);mounted.delete(node);continue;}
            const t=Math.max(0,Math.min(durations[job.action],now-job.started));
            if(job.overlay)drawUltimate(job,t);else drawPet(node,job.action,t);
            if(t>=durations[job.action]) {
                cleanJob(job);active.delete(node);
                const next=job.action==='ultimate'?'win':['lose','win'].includes(job.action)?job.action:'idle';
                node.dataset.mood=next;drawPet(node,next,durations[next]||0);
            }
        }
        if(active.size)raf=requestAnimationFrame(tick);
    }
    function play(node,action='idle') {
        if(!isOwl(node))return false;
        if(action==='defeat')action='lose';
        if(!(action in durations))action='idle';
        moods.set(node,action);node.dataset.mood=action;
        const version=generation,request={};requests.set(node,request);
        ready().then(()=>{
            if(version!==generation||requests.get(node)!==request||!node.isConnected)return;
            if(active.has(node)){cleanJob(active.get(node));active.delete(node);}
            node.classList.add('owl-ready');
            if(action==='idle'||reduced.matches||document.hidden) {
                const pose=action==='ultimate'?'win':action;drawPet(node,pose,durations[pose]||0);return;
            }
            const job={node,action,started:performance.now(),overlay:action==='ultimate'?overlayFor(node):null};
            if(action==='ultimate'&&!job.overlay){drawPet(node,'win',durations.win);return;}
            active.set(node,job);if(!raf)raf=requestAnimationFrame(tick);
        }).catch(()=>{if(requests.get(node)===request){node.classList.remove('owl-ready');node.dataset.mood='idle';}});
        return true;
    }
    function mount(root=document) {
        for(const [node]of mounted)if(!node.isConnected){const job=active.get(node);if(job)cleanJob(job);active.delete(node);mounted.delete(node);}
        for(const node of root.querySelectorAll('.battle-pet.cu-meo'))play(node,node.dataset.mood||'idle');
        if (!observer && !(typeof RuntimeAssets !== 'undefined' && RuntimeAssets.managed)) {
            observer=new MutationObserver(changes=>{
                for(const change of changes) {
                    if(change.type==='attributes'&&isOwl(change.target)&&moods.get(change.target)!==change.target.dataset.mood)play(change.target,change.target.dataset.mood||'idle');
                    for(const node of change.addedNodes||[])if(node.nodeType===1) {
                        if(node.matches('.battle-pet.cu-meo'))play(node,node.dataset.mood||'idle');
                        for(const pet of node.querySelectorAll('.battle-pet.cu-meo'))play(pet,pet.dataset.mood||'idle');
                    }
                }
                for(const [node]of mounted)if(!node.isConnected){const job=active.get(node);if(job)cleanJob(job);active.delete(node);mounted.delete(node);}
            });
            observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});
        }
    }
    function later(callback,delay) {
        const timer=setTimeout(()=>{timers.delete(timer);callback();},delay);timers.add(timer);
    }
    function terminal(node,action) {
        if(!node?.isConnected)return;
        requests.set(node,{});
        const job=active.get(node);if(job){cleanJob(job);active.delete(node);}
        moods.set(node,action);node.dataset.mood=action;
        if(atlas&&isOwl(node)){node.classList.add('owl-ready');drawPet(node,action,durations[action]||0);}
        else if(isOwl(node)&&observer)play(node,action);
    }
    function settle(presentation) {
        const {source,victim,actor,target,final}=presentation;
        source.classList.remove('attacking');victim?.classList.remove('taking-hit');
        terminal(actor,final?'win':'idle');
        terminal(target,final?'lose':'idle');
        if(target?.isConnected&&typeof RabbitAnimation!=='undefined')RabbitAnimation.play(target,final?'lose':'idle');
        presentations.delete(presentation);
    }
    function hit({source,victim,final=false}={}) {
        const actor=source?.querySelector('.battle-pet.cu-meo'),target=victim?.querySelector('.battle-pet');
        if(!actor)return false;
        const presentation={source,victim,actor,target,final};presentations.add(presentation);
        const stage=actor.closest('#battle-stage');
        source.classList.add('attacking');play(actor,final?'ultimate':'attack');
        const impact=()=>{
            if(!target?.isConnected)return;
            victim.dataset.spell='owl';victim.classList.add('taking-hit');target.dataset.mood=final?'lose':'hit';
            if(isOwl(target))play(target,final?'lose':'hit');
            if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(target,final?'lose':'hit');
            const bear=target.querySelector('canvas[data-bear]');
            if(bear&&typeof BearAnimation!=='undefined')BearAnimation.play(bear,final?'defeat':'hit');
        };
        if(typeof ArenaVoi!=='undefined'&&source.id&&victim?.id)ArenaVoi.notifyVictim('#'+victim.id,'#'+source.id,final);
        if(final)later(impact,1750);else impact();
        const label=stage?.querySelector('#spell-announcement');if(label)label.textContent='';
        later(()=>settle(presentation),final?3000:1100);
        return true;
    }
    function destroy() {
        generation++;cancelAnimationFrame(raf);raf=0;
        observer?.disconnect();observer=null;for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const presentation of [...presentations])settle(presentation);
        for(const job of active.values())cleanJob(job);active.clear();
        for(const [node,canvas]of mounted){canvas.remove();node.classList.remove('owl-ready','owl-in-ultimate');}mounted.clear();
    }
    document.addEventListener('visibilitychange',()=>{
        if(!document.hidden)return;
        cancelAnimationFrame(raf);raf=0;
        for(const timer of timers)clearTimeout(timer);timers.clear();
        for(const presentation of [...presentations])settle(presentation);
        for(const [node,job]of [...active])terminal(node,job.action==='ultimate'?'win':['lose','win'].includes(job.action)?job.action:'idle');
    });
    reduced.addEventListener('change',()=>{for(const [node,job]of [...active]){cleanJob(job);active.delete(node);play(node,job.action);}});
    window.addEventListener('pagehide',destroy);
    return {ready,mount,play,hit,destroy,duration:action=>durations[action]||0};
})();
