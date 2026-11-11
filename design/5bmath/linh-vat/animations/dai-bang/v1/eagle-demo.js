/* Đại bàng: bird choreography, deterministic Canvas timeline for review/export. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,PI=Math.PI,assets={},clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
 const lerp=(a,b,p)=>a+(b-a)*p,smooth=n=>{n=clamp(n);return n*n*(3-2*n);};
 let mode='ultimate',clock=0,playing=false,raf=0,last=0,speed=1;
 const lengths={ultimate:3,attack:1,hit:1.1,defeat:3,idle:3};
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 document.title='Đại bàng — Sải Cánh Bão Táp · 5BMath';
 document.querySelector('h1').textContent=C.ultimateName;
 document.querySelector('header p').textContent='Đại bàng · Chiêu cuối, tấn công, chịu đòn và buồn khi thua';
 document.querySelector('.note').textContent='Canvas + WebP · Không có âm thanh · Hoạt cảnh không quyết định sát thương trong game.';
 function load(key,url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{assets[key]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được '+url));img.src=url;});}
 function label(value,x,y,size,color='#fff9ed'){ctx.fillStyle=color;ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`800 ${size}px Arial,sans-serif`;ctx.fillText(value,x,y);}
 function box(x,y,w,h,color){ctx.fillStyle=color;ctx.beginPath();ctx.roundRect(x,y,w,h,20);ctx.fill();}
 function feather(x,y,size,angle,alpha=1){ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;ctx.fillStyle='#fff0c5';ctx.beginPath();ctx.ellipse(0,0,size*.28,size,0,0,PI*2);ctx.fill();ctx.strokeStyle='#c28f51';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(0,size);ctx.lineTo(0,-size*.7);ctx.stroke();ctx.restore();}
 function sprite(sheet,index,x,feet,height=280,rotation=0,alpha=1){
  const map=sheet==='actor'?window.ANIMATION_POSES:window.EAGLE_STATES,f=map.frames[index];
  // Scale from grid height, preserving body size across wing positions and crouches.
  const scale=height/(map.height/4*.8);ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,feet);ctx.rotate(rotation);
  ctx.drawImage(assets[sheet],f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);ctx.restore();
 }
 function wind(x,y,r,p,alpha=1,mirror=1){ctx.save();ctx.translate(x,y);ctx.scale(mirror,1);ctx.globalAlpha*=alpha;ctx.lineCap='round';
  for(let i=0;i<4;i++){ctx.strokeStyle=i%2?'#ffe0a2':'#e4fff0';ctx.lineWidth=7-i;ctx.beginPath();ctx.ellipse(0,(i-1.5)*18,r*(.55+i*.1),r*(.19+i*.025),-.25,-PI*.75+p,PI*.65+p);ctx.stroke();}ctx.restore();
 }
 function background(){ctx.drawImage(assets.bg,0,0,W,H);const grad=ctx.createLinearGradient(0,0,0,H);grad.addColorStop(0,'#102f2eb0');grad.addColorStop(.48,'#102f2e00');grad.addColorStop(1,'#102f2e40');ctx.fillStyle=grad;ctx.fillRect(0,0,W,H);label('5BMath',96,38,24);label('ĐẤU TRÍ · ĐẠI BÀNG',1080,38,18);}
 function opponent(t){const hit=mode==='ultimate'&&t>=1.75,p=hit?smooth((t-1.75)/.4):0;ctx.save();ctx.globalAlpha=1-p*.6;ctx.translate(1050+p*30,598);ctx.rotate(p*.08);const img=assets.reference;ctx.drawImage(img,img.width/2,0,img.width/2,img.height,-145,-290,290,290);ctx.restore();}
 function flight(t){let x=248,y=600,index=0,rotation=0;
  if(t<.65){index=Math.min(3,Math.floor(t/.65*4));y+=Math.sin(t/.65*PI)*10;}
  else if(t<.95){const p=smooth((t-.65)/.3);x=lerp(248,378,p);y=lerp(600,425,p);index=4+Math.min(3,Math.floor(p*4));}
  else if(t<1.35){const p=smooth((t-.95)/.4);x=lerp(378,610,p);y=lerp(425,340,p);index=4+Math.floor(p*3);rotation=-.08;}
  else if(t<1.75){const p=smooth((t-1.35)/.4);x=lerp(610,905,p);y=lerp(340,580,p);index=p<.55?8:9;rotation=.12;}
  else if(t<1.9){index=t<1.82?10:11;x=905;y=580;}
  else{const p=smooth((t-1.9)/.5);x=lerp(905,700,p);y=lerp(580,600,p)-Math.sin(p*PI)*35;index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));}
  return {x,y,index,rotation};
 }
 function track(t){if(t<.95||t>1.91)return;ctx.save();ctx.globalAlpha=.6*(1-smooth((t-1.7)/.21));ctx.strokeStyle='#ffdd98';ctx.lineWidth=12;ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(378,425);ctx.lineTo(610,340);if(t>=1.35)ctx.lineTo(flight(Math.min(t,1.75)).x,flight(Math.min(t,1.75)).y-100);ctx.stroke();ctx.lineWidth=3;ctx.strokeStyle='#fff8df';ctx.stroke();ctx.restore();}
 function storm(t){if(t<1.72||t>2.45)return;const p=clamp((t-1.72)/.73),alpha=(1-p)*.9;
  wind(1010,445,80+p*130,p*3,alpha,1);wind(1090,455,80+p*130,-p*3,alpha,-1);
  for(let i=0;i<24;i++){const a=i*2.4+p*6,r=35+p*(100+i%4*18);feather(1050+Math.cos(a)*r,450+Math.sin(a)*r*.7,9+i%3*3,a,alpha);}
 }
 function title(t){if(t<.65||t>1.55)return;ctx.save();ctx.globalAlpha=Math.min(1,(t-.65)/.08,Math.max(0,(1.55-t)/.12));box(260,630,760,74,'#153f31f5');ctx.strokeStyle='#ffbe73';ctx.lineWidth=2;ctx.stroke();label('SẢI CÁNH BÃO TÁP',640,668,43,'#fff0c9');feather(298,667,18,-.4);feather(982,667,18,.4);ctx.restore();}
 function victory(t){if(t<1.9)return;ctx.save();ctx.globalAlpha=smooth((t-1.9)/.18);box(410,145,460,77,'#153f31ee');label('CHIẾN THẮNG!',640,184,42,'#fff0c9');for(let i=0;i<24;i++){const p=t-1.9,a=i*2.4,r=90+p*(60+i*5);feather(700+Math.cos(a)*r,380+Math.sin(a)*r*.6+p*45,7+i%3*2,a+p,clamp(1-p*.7));}ctx.restore();}
 function draw(time){const duration=lengths[mode],t=clamp(time,0,duration);background();opponent(t);let index=0;
  if(mode==='ultimate'){
   track(t);const f=flight(t);index=f.index;sprite('actor',index,f.x,f.y,270,f.rotation);storm(t);title(t);victory(t);
  }else{
   const p=t/duration;let x=550,y=600,rot=0;
   if(mode==='attack'){index=4+Math.min(3,Math.floor(p*4));x+=Math.sin(p*PI)*105;y-=Math.sin(p*PI)*32;if(p>.25&&p<.8)wind(x+145,y-130,70,p*2,(1-p)*.8);}
   else if(mode==='hit'){index=8+Math.min(3,Math.floor(p*4));x-=Math.sin(p*PI)*42;rot=-.07*Math.sin(p*PI);}
   else if(mode==='defeat'){index=12+Math.min(3,Math.floor(Math.min(1,p*2)*4));y+=smooth(p)*6;}
   else index=Math.floor(t*2)%4;
   sprite('states',index,x,y,310,rot);const names={idle:'SẴN SÀNG',attack:'TẤN CÔNG · VỖ CÁNH',hit:'CHỊU ĐÒN · LẤY LẠI THĂNG BẰNG',defeat:'THUA CUỘC · MÌNH SẼ THỬ LẠI'};box(260,165,760,70,'#153f31ee');label(names[mode],640,200,29);
  }
  const phase=mode==='ultimate'?(t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG'):mode;
  if(mode!=='ultimate'||t<.65||t>1.55){box(440,652,400,40,'#153f31cc');label(mode==='ultimate'?phase:({idle:'SẴN SÀNG',attack:'TẤN CÔNG',hit:'CHỊU ĐÒN',defeat:'BUỒN KHI THUA'})[mode],640,673,16);}
  document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / '+duration.toFixed(2).replace('.',',')+' s';
  return {time:t,t,mode,phase,pose:index,nameVisible:mode==='ultimate'&&t>=.65&&t<=1.55,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory:mode==='ultimate'&&t>=1.9};
 }
 function pause(){playing=false;cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset||clock>=lengths[mode])clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(lengths[mode],clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<lengths[mode])raf=requestAnimationFrame(tick);else pause();}
 function select(next){pause();mode=next;clock=0;document.getElementById('seek').max=lengths[mode];document.getElementById('action').value=next;draw(0);if(!reduced.matches)play(true);}
 const ready=Promise.all([load('actor',C.webpFile),load('states','assets/states.webp'),load('bg',C.backgroundFile),load('reference',C.opponentFile)]).then(()=>{draw(0);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,select,duration:3,get state(){return {playing,mode,clock,raf};}};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play();
 document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};
 document.getElementById('action').onchange=e=>select(e.target.value);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{pause();draw(clock);});
 ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
