/* Bướm review player: the same pure renderer is packaged with the local game. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,R=window.ButterflyRenderer,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=canvas.width,H=canvas.height,assets={},clamp=n=>Math.max(0,Math.min(1,n));
 let mode='ultimate',playing=false,clock=0,last=0,speed=1,raf=0;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function load(name,src){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{assets[name]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được '+src));img.src=src;});}
 function text(label,x,y,size,colour='#FFF9ED',weight=700){ctx.fillStyle=colour;ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(label,x,y);}
 function label(label,x,y,width=270){ctx.fillStyle='#1F6248e8';ctx.beginPath();ctx.roundRect(x-width/2,y-24,width,48,18);ctx.fill();text(label,x,y,21);}
 function opponent(t){
  const p=mode==='ultimate'?clamp((t-1.75)/.35):mode==='attack'?clamp((t-.45)/.25):0;
  ctx.save();ctx.translate(1030+Math.sin(p*Math.PI)*30,485);ctx.rotate(Math.sin(p*Math.PI)*.1);
  const img=assets.opponent;ctx.drawImage(img,img.width/2,0,img.width/2,img.height,-155,-155,310,310);ctx.restore();
 }
 function draw(t){
  t=Math.max(0,Math.min(3,t));ctx.clearRect(0,0,W,H);ctx.drawImage(assets.bg,0,0,W,H);
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#173D35ba');shade.addColorStop(.5,'#173D3512');shade.addColorStop(1,'#173D3560');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  text('5BMath · BƯỚM',190,44,26);text('VƯỜN TOÁN · ĐẤU TRÍ',1062,44,17);
  opponent(t);
  let index=0,x=300,y=450,size=350,rotation=0;
  if(mode==='ultimate'){
   if(t<.65){index=Math.floor(t*7)%3;y-=Math.sin(t*Math.PI/.65)*15;}
   else if(t<.95){index=8;size*=.97;y-=18;}
   else if(t<1.9){index=t<1.4?9:10;x+=Math.sin(clamp((t-.95)/.95)*Math.PI)*55;y-=20+Math.sin((t-.95)*Math.PI/.95)*36;rotation=Math.sin((t-.95)*5)*.05;}
   else{index=t<2.2?10:11;y-=30+Math.sin((t-1.9)*Math.PI/1.1)*15;}
   R.effects(ctx,t,{x:300,y:450,size},{x:1030,y:485,size:310},{reducedMotion:reduced.matches});
  }else if(mode==='attack'){
   const u=clamp(t/1.2);index=t<1.2?4+Math.min(3,Math.floor(u*4)):0;x+=Math.sin(u*Math.PI)*420;y-=Math.sin(u*Math.PI)*58;rotation=-Math.sin(u*Math.PI)*.12;
   if(t<1.2)for(let i=0;i<16;i++){
    const progress=clamp((t-i*.022)/.65);R.butterfly(ctx,300+progress*700,460-Math.sin(progress*Math.PI)*92+i%3*9,12+i%3*3,['#FFBE73','#AED58E','#FFE2A1'][i%3],0,1,(1-progress)*.7);
   }
  }else if(mode==='hit'){
   const u=clamp(t/1.2);index=t<.5?12:t<1.2?13:0;x-=Math.sin(u*Math.PI)*26;rotation=Math.sin(u*Math.PI*5)*(1-u)*.09;
   if(t<1.2)for(let i=0;i<4;i++)R.star(ctx,x-60+i*42,265+Math.sin(t*8+i)*10,12,'#FFE2A1',1-u,t);
  }else if(mode==='lose'){
   const u=clamp(t/1.4);index=t<.6?14:15;y+=u*10;rotation=-u*.05;
  }
  ctx.save();ctx.fillStyle='#123A2B26';ctx.beginPath();ctx.ellipse(x,610,84,10,0,0,Math.PI*2);ctx.fill();ctx.restore();
  R.pose(ctx,assets.actor,index,x,y,size,rotation);
  label('Bướm',300,611);label('Cáo Nâu · minh họa',1030,611,330);
  let phase=mode==='ultimate'?(t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG'):({attack:'TẤN CÔNG · VỖ CÁNH',hit:'CHỊU ĐÒN · HỒI PHỤC',lose:'THUA CUỘC · CỐ LÊN NÀO'}[mode]);
  if(mode==='ultimate'&&t>=1.9){ctx.save();ctx.globalAlpha=clamp((t-1.9)/.18);text('CHIẾN THẮNG!',640,128,53,'#FFF3CA',800);text('Vũ Điệu Ngàn Cánh',640,182,25,'#FFE2A1');ctx.restore();}
  label(phase,640,675,440);
  document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  return {time:t,t,mode,phase,pose:index,...R.state(t),impact:t>=1.75};
 }
 function pause(){playing=false;if(raf){cancelAnimationFrame(raf);raf=0;}document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 function setMode(value){if(!['ultimate','attack','hit','lose'].includes(value))throw new Error('Trạng thái không hợp lệ');pause();mode=value;clock=0;document.getElementById('mode').value=value;draw(0);}
 const ready=Promise.all([load('actor',C.webpFile),load('bg',C.backgroundFile),load('opponent',C.opponentFile)]).then(()=>{draw(0);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,setMode,duration:3,get mode(){return mode;},get playing(){return playing;}};
 document.getElementById('replay').onclick=()=>play(true);
 document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);
 document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};
 document.getElementById('mode').onchange=e=>{setMode(e.target.value);play(true);};
 document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 ready.catch(error=>{document.querySelector('.note').textContent=error.message;console.error(error);});
})();
