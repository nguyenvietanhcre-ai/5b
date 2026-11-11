/* 5BMath — Đại bàng / Sải Cánh Bão Táp. Canvas presentation only. */
(() => {
    'use strict';
    if(typeof window==='undefined'||window.EagleAnimation)return;
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    const pets=new Map(),flights=new Set(),sheets={};
    const durations={attack:1000,hit:1100,lose:3000,win:1600,ultimate:3000};
    const clamp=n=>Math.max(0,Math.min(1,n));
    const smooth=n=>{n=clamp(n);return n*n*(3-2*n);};
    const mix=(a,b,n)=>a+(b-a)*n;
    let loading,observer,queued=false,enabled=true;
    const eagle=node=>node?.matches?.('.battle-pet.eagle')?node:node?.querySelector?.('.battle-pet.eagle');
    function ready(){
        if(!loading)loading=Promise.all(['poses','states'].map(key=>new Promise((resolve,reject)=>{
            const img=new Image();img.onload=()=>{sheets[key]=img;resolve();};img.onerror=reject;
            img.src=new URL(`arena-art/eagle/${key}.webp`,document.baseURI).href;
        }))).catch(error=>{loading=null;throw error;});
        return loading;
    }
    function sprite(ctx,key,index,x,y,size,{flip=false,rotation=0,alpha=1}={}){
        const img=sheets[key];if(!img)return;
        const col=index%4,row=Math.floor(index/4),x0=Math.round(col*img.width/4),y0=Math.round(row*img.height/4);
        const w=Math.round((col+1)*img.width/4)-x0,h=Math.round((row+1)*img.height/4)-y0,scale=size/Math.max(w,h);
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(flip?-1:1,1);ctx.globalAlpha*=alpha;
        ctx.drawImage(img,x0,y0,w,h,-w*scale/2,-h*scale/2,w*scale,h*scale);ctx.restore();
    }
    function rowFrame(row,p){return row*4+Math.min(3,Math.floor(clamp(p)*4));}
    function paint(entry,time){
        const {canvas,ctx,node,mood}=entry,side=canvas.width,p=clamp(time/(durations[mood]||1));
        ctx.clearRect(0,0,side,side);let x=side/2,y=side/2,rotation=0,key='states',index=0;
        if(mood==='attack'){index=rowFrame(1,p);if(!reduced.matches){x+=Math.sin(p*Math.PI)*side*.09;y-=Math.sin(p*Math.PI)*side*.07;rotation=Math.sin(p*Math.PI)*.07;}}
        else if(mood==='hit'){index=rowFrame(2,p);if(!reduced.matches){x+=Math.sin(p*Math.PI*5)*(1-p)*side*.045;rotation=Math.sin(p*Math.PI)*-.06;}}
        else if(mood==='lose'){index=rowFrame(3,p);if(!reduced.matches)y+=smooth(p)*side*.025;}
        else if(mood==='win'){key='poses';index=rowFrame(3,p);if(!reduced.matches)y-=Math.sin(p*Math.PI)*side*.04;}
        else if(mood==='ultimate')return;
        sprite(ctx,key,index,x,y,side*.98,{rotation});
        if(mood==='hit'&&p<.75&&!reduced.matches){
            ctx.strokeStyle='#ffbe73';ctx.lineWidth=side*.012;
            for(let i=0;i<3;i++){const xx=side*(.3+i*.2),yy=side*.15+Math.sin(p*12+i)*side*.025;ctx.beginPath();ctx.moveTo(xx-5,yy);ctx.lineTo(xx+5,yy);ctx.moveTo(xx,yy-5);ctx.lineTo(xx,yy+5);ctx.stroke();}
        }
        node.dataset.eagleFrame=String(index);
    }
    function cancel(entry){if(entry.raf)cancelAnimationFrame(entry.raf);entry.raf=0;}
    function animate(entry,mood,force=false){
        if(!force&&entry.mood===mood)return;
        cancel(entry);entry.mood=mood;entry.started=performance.now();
        if(!sheets.states||mood==='ultimate')return;
        const duration=durations[mood]||0;
        if(reduced.matches||document.hidden||!duration){paint(entry,duration);return;}
        paint(entry,0);
        const tick=now=>{
            entry.raf=0;if(!enabled||!entry.node.isConnected||document.hidden)return;
            const elapsed=Math.min(duration,now-entry.started);paint(entry,elapsed);
            if(elapsed<duration)entry.raf=requestAnimationFrame(tick);
            else if(mood==='attack'||mood==='hit'){entry.node.dataset.mood='idle';animate(entry,'idle');}
        };
        entry.raf=requestAnimationFrame(tick);
    }
    function mountOne(node){
        if(pets.has(node))return pets.get(node);
        const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;canvas.className='eagle-canvas';canvas.setAttribute('aria-hidden','true');
        const ctx=canvas.getContext('2d');if(!ctx)return null;
        const entry={node,canvas,ctx,mood:null,raf:0};pets.set(node,entry);
        ready().then(()=>{if(!node.isConnected||!pets.has(node))return;node.append(canvas);node.classList.add('eagle-ready');animate(entry,node.dataset.mood||'idle',true);}).catch(()=>{node.classList.remove('eagle-ready');});
        return entry;
    }
    function mount(root=document){
        for(const [node,entry]of pets)if(!node.isConnected){cancel(entry);pets.delete(node);}
        const nodes=[...root.querySelectorAll('.battle-pet.eagle')];if(root.matches?.('.battle-pet.eagle'))nodes.unshift(root);
        for(const node of nodes){const entry=mountOne(node);if(entry)animate(entry,node.dataset.mood||'idle');}
        for(const flight of [...flights])if(!flight.stage.isConnected)flight.finish();
    }
    function wind(ctx,x,y,size,p,alpha=1,flip=false){
        ctx.save();ctx.translate(x,y);ctx.scale(flip?-1:1,1);ctx.globalAlpha=alpha;ctx.lineCap='round';
        for(let i=0;i<3;i++){
            ctx.strokeStyle=i%2?'#ffbe73':'#e8fff5';ctx.lineWidth=Math.max(1.5,size*.015*(1-i*.15));
            ctx.beginPath();ctx.ellipse(0,(i-1)*size*.07,size*(.24+p*.45),size*(.08+p*.14),-.4,-Math.PI*.8+p*.7,Math.PI*.7+p*.7);ctx.stroke();
        }ctx.restore();
    }
    function vTrail(ctx,x,y,size,flip,alpha){
        ctx.save();ctx.translate(x,y);ctx.scale(flip?-1:1,1);ctx.rotate(.2);ctx.lineCap='round';ctx.lineJoin='round';ctx.globalAlpha=alpha;
        for(let i=2;i>=0;i--){const d=i*size*.1;ctx.strokeStyle=i?'#ffbe7366':'#fff9ed';ctx.lineWidth=Math.max(2,size*(.012+i*.009));ctx.beginPath();ctx.moveTo(-size*.52-d,-size*.32-d);ctx.lineTo(-size*.1-d,size*.03-d);ctx.lineTo(size*.4-d,-size*.28-d);ctx.stroke();}ctx.restore();
    }
    function ultimate({source,victim}={}){
        const actor=eagle(source),stage=actor?.closest('#battle-stage');if(!actor||!stage||!victim)return false;
        if(reduced.matches||document.hidden){play(actor,'win');const target=eagle(victim);if(target)play(target,'lose');return true;}
        ready().then(()=>{
            if(!stage.isConnected||document.hidden)return;
            for(const old of [...flights])if(old.stage===stage)old.finish();
            const bounds=stage.getBoundingClientRect(),a=actor.getBoundingClientRect(),b=(victim.querySelector('.battle-pet')||victim).getBoundingClientRect();
            const W=bounds.width,H=bounds.height,dpr=Math.min(devicePixelRatio||1,1.5),size=a.width,flip=b.left<a.left;
            const from={x:a.left-bounds.left+a.width/2,y:a.top-bounds.top+a.height/2},to={x:b.left-bounds.left+b.width/2,y:b.top-bounds.top+b.height/2};
            const canvas=document.createElement('canvas');canvas.className='eagle-ultimate-canvas';canvas.setAttribute('aria-hidden','true');canvas.width=Math.max(1,Math.round(W*dpr));canvas.height=Math.max(1,Math.round(H*dpr));
            const ctx=canvas.getContext('2d');if(!ctx)return;
            let raf=0,done=false,impacted=false;const started=performance.now();
            const flight={stage,finish(){if(done)return;done=true;cancelAnimationFrame(raf);canvas.remove();actor.classList.remove('eagle-in-ultimate');stage.classList.remove('eagle-ultimate-active');flights.delete(flight);if(actor.isConnected)play(actor,'win');}};
            stage.classList.add('eagle-ultimate-active');actor.classList.add('eagle-in-ultimate');stage.append(canvas);flights.add(flight);
            function draw(now){
                raf=0;if(!enabled||!stage.isConnected||document.hidden){flight.finish();return;}
                const t=Math.min(3,(now-started)/1000);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
                if(t>=1.75&&!impacted){impacted=true;const target=eagle(victim);if(target?.isConnected)play(target,'lose');}
                let x=from.x,y=from.y,index=0,rotation=0;
                if(t<.95){const p=clamp(t/.95);index=rowFrame(0,p);y-=smooth(p)*size*.28;wind(ctx,x,y+size*.17,size,p,.65);}
                else if(t<1.75){const p=smooth((t-.95)/.8);x=mix(from.x,to.x,p);y=mix(from.y-size*.28,to.y,p)-Math.sin(p*Math.PI)*Math.min(H*.4,size*1.5);y=Math.max(size*.44,Math.min(H-size*.44,y));index=rowFrame(1,(t-.95)/.8);rotation=(flip?-1:1)*(.15+Math.sin(p*Math.PI)*.12);wind(ctx,x-size*(flip?-.22:.22),y,size,p,.85,flip);vTrail(ctx,x,y,size,flip,.9);}
                else if(t<1.9){x=to.x;y=to.y;index=rowFrame(2,(t-1.75)/.15);}
                else{const p=smooth((t-1.9)/.35);x=mix(to.x,from.x,p);y=mix(to.y,from.y,p)-Math.sin(p*Math.PI)*size*.3;index=rowFrame(3,(t-1.9)/1.1);}
                if(t>=1.55&&t<1.95){const p=clamp((t-1.55)/.4);for(const side of [-1,1])wind(ctx,mix(to.x+side*size*.65,to.x,smooth(p)),mix(to.y-size*.16,to.y,p),size*.9,p,1-p*.4,side<0);}
                if(t>=1.75&&t<2.4){const p=(t-1.75)/.65;wind(ctx,to.x,to.y,size*1.5,p,1-p,flip);ctx.save();ctx.globalAlpha=1-p;
                    for(let i=0;i<18;i++){const angle=i*Math.PI/9+p*4,r=size*(.15+p*.75);ctx.fillStyle=i%2?'#ffbe73':'#e8fff5';ctx.beginPath();ctx.ellipse(to.x+Math.cos(angle)*r,to.y+Math.sin(angle)*r*.65,size*.012+1,size*.035+1,angle+.4,0,Math.PI*2);ctx.fill();}ctx.restore();}
                y=Math.max(size*.44,Math.min(H-size*.44,y));
                sprite(ctx,'poses',index,x,y,size,{flip,rotation});
                if(t>=.65&&t<1.55){
                    const font=Math.max(12,Math.min(24,W*.045)),text='SẢI CÁNH BÃO TÁP';ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
                    const width=Math.min(W-24,ctx.measureText(text).width+22),height=font+18,top=H-height/2-12,center=W/2;
                    ctx.fillStyle='#1f6248f5';ctx.beginPath();ctx.roundRect(center-width/2,top-height/2,width,height,12);ctx.fill();ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.stroke();ctx.fillStyle='#fff9ed';ctx.fillText(text,center,top,width-14);
                }
                if(t>=3){flight.finish();return;}raf=requestAnimationFrame(draw);
            }raf=requestAnimationFrame(draw);
        }).catch(()=>{actor.classList.remove('eagle-in-ultimate');});return true;
    }
    function play(node,action='idle'){
        node=eagle(node);if(!node)return false;
        node.dataset.mood=action;const entry=mountOne(node);if(entry)animate(entry,action,true);return true;
    }
    function hit({source,victim,final=false}={}){
        const actor=eagle(source),target=eagle(victim);if(target&&!(actor&&final))play(target,final?'lose':'hit');
        if(!actor)return false;if(final){actor.dataset.mood='ultimate';return ultimate({source,victim});}return play(actor,'attack');
    }
    function stop(){for(const entry of pets.values())cancel(entry);for(const flight of [...flights])flight.finish();}
    function destroy(){enabled=false;observer?.disconnect();stop();for(const entry of pets.values()){entry.canvas.remove();entry.node.classList.remove('eagle-ready');}pets.clear();}
    window.EagleAnimation={ready,mount,play,hit,ultimate,stop,destroy};
    function start(){observer=new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;if(enabled)mount();});});observer.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});mount();}
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else for(const entry of pets.values())animate(entry,entry.node.dataset.mood||'idle',true);});
    window.addEventListener('pagehide',stop);window.addEventListener('resize',()=>{stop();for(const entry of pets.values())if(sheets.states)paint(entry,durations[entry.mood]||0);});
    reduced.addEventListener('change',()=>{stop();for(const entry of pets.values())animate(entry,entry.node.dataset.mood||'idle',true);});
})();
