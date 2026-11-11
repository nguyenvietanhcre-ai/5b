/* Mầm Sách: shared Canvas choreography, standalone review controls. */
(() => {
    'use strict';
    const config=window.ANIMATION_CONFIG,api=window.MamSachAnimation;
    const canvas=document.getElementById('stage'),ctx=canvas.getContext('2d');
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');
    const seek=document.getElementById('seek'),clock=document.getElementById('clock'),pauseButton=document.getElementById('pause');
    const modeControl=document.getElementById('mode'),speedControl=document.getElementById('speed');
    const W=1280,H=720,duration=3,from={x:310,y:470},to={x:950,y:443},size=350;
    let mode='ultimate',time=0,playing=false,raf=0,previous=0,state={};
    const images={};
    api.configure({asset:config.poseFile,frames:window.ANIMATION_POSES.frames});
    const image=(key,url)=>new Promise((resolve,reject)=>{
        const img=new Image();img.onload=()=>{images[key]=img;resolve(img);};img.onerror=()=>reject(new Error('Không tải được ảnh '+url));img.src=url;
    });
    function cover(img){const k=Math.max(W/img.naturalWidth,H/img.naturalHeight);ctx.drawImage(img,(W-img.naturalWidth*k)/2,(H-img.naturalHeight*k)/2,img.naturalWidth*k,img.naturalHeight*k);}
    function fox(lift=0,hit=false){
        const img=images.opponent,cropW=img.naturalWidth/2,cropH=img.naturalHeight,scale=340/Math.max(cropW,cropH);
        ctx.save();ctx.translate(to.x,to.y-lift);ctx.scale(-1,1);ctx.rotate(hit?.06:0);
        ctx.drawImage(img,cropW,0,cropW,cropH,-cropW*scale/2,-cropH*scale/2,cropW*scale,cropH*scale);ctx.restore();
    }
    function groundShadow(x,y,width,opacity=.2){ctx.save();ctx.fillStyle=`rgba(15,48,33,${opacity})`;ctx.beginPath();ctx.ellipse(x,y,width,width*.16,0,0,Math.PI*2);ctx.fill();ctx.restore();}
    function render(t=0){
        time=Math.max(0,Math.min(duration,Number(t)||0));ctx.clearRect(0,0,W,H);
        if(images.background)cover(images.background);else{ctx.fillStyle='#e4ebcd';ctx.fillRect(0,0,W,H);}
        ctx.save();const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#153a2b22');shade.addColorStop(1,'#153a2b55');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);ctx.restore();
        groundShadow(from.x,from.y+147,120);groundShadow(to.x,to.y+147,105);
        if(mode==='ultimate'){
            // Render tree behind opponent, then place the lifted fox in the canopy.
            state=api.renderUltimate(ctx,time,W,H,{from,to,size,targetSize:340,drawActor:true,motion:!reduced.matches});
            fox(state.targetLift,time>=1.75&&time<2.05);
        }else{
            const actorTime=Math.min(time,mode==='attack'?1.1:mode==='hurt'?1.05:2.4);
            state=api.renderPet(ctx,{mode,time:actorTime,x:from.x,y:from.y,size,motion:!reduced.matches});
            fox();
            if(mode==='attack')api.renderAttack(ctx,actorTime,W,H,{from,to,size});
            state={...state,nameVisible:false,attackStarted:mode==='attack'&&time>=.18,victory:false};
        }
        state={...state,time,mode,playing};
        seek.value=String(time);clock.textContent=time.toFixed(2).replace('.',',')+' / 3,00 s';
        canvas.dataset.mode=mode;canvas.dataset.time=String(time);
        return state;
    }
    function pause(){cancelAnimationFrame(raf);raf=0;playing=false;pauseButton.textContent='Tiếp tục';state.playing=false;}
    function play(){
        if(time>=duration)time=0;
        cancelAnimationFrame(raf);playing=true;pauseButton.textContent='Tạm dừng';previous=performance.now();
        const tick=now=>{raf=0;if(!playing||document.hidden)return;const speed=Number(speedControl.value)||1;time=Math.min(duration,time+(now-previous)/1000*speed);previous=now;render(time);if(time<duration)raf=requestAnimationFrame(tick);else pause();};
        raf=requestAnimationFrame(tick);
    }
    function setMode(value){pause();mode=['ultimate','attack','hurt','defeat'].includes(value)?value:'ultimate';modeControl.value=mode;render(0);return state;}
    const ready=Promise.all([api.ready(),image('background',config.backgroundFile),image('opponent',config.opponentFile)]).then(values=>{
        if(!values[0])throw new Error('Không tải được WebP Mầm Sách');
        render(0);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play();return true;
    });
    window.animationDemo={ready,render,pause,play,resume:play,setMode,config,duration,
        get state(){return state;},get time(){return time;},get playing(){return playing;}};
    document.getElementById('replay').addEventListener('click',()=>{pause();render(0);play();});
    pauseButton.addEventListener('click',()=>playing?pause():play());
    seek.addEventListener('input',()=>{pause();render(seek.value);});
    modeControl.addEventListener('change',()=>{setMode(modeControl.value);if(!reduced.matches)play();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
    window.addEventListener('pagehide',pause);reduced.addEventListener('change',()=>{pause();render(time);});
})();
