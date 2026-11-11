/* Cáo Nâu / v1: distinct tail feint, flank and autumn vortex choreography. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,DURATION=3,PI=Math.PI,assets={};
 const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v)),mix=(a,b,u)=>a+(b-a)*u;
 const smooth=u=>{u=clamp(u);return u*u*(3-2*u);},out=u=>1-(1-clamp(u))**3;
 const modes={ultimate:'Lốc Đuôi Tinh Quái',attack:'Quét đuôi tinh nghịch',hit:'Cáo Nâu chịu đòn',lose:'Cáo Nâu khi thua cuộc'};
 let mode=new URLSearchParams(location.search).get('mode')||'ultimate';if(!modes[mode])mode='ultimate';
 let clock=0,playing=false,last=0,speed=1,raf=0;
 function load(name,src){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{assets[name]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được '+src));img.src=src;});}
 function box(x,y,w,h,r,color,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(color){ctx.fillStyle=color;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();}}
 function text(s,x,y,size=24,color='#fff9ed',weight=800,align='center'){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(s,x,y);}
 function shadow(x,y,w=90,a=.16){ctx.save();ctx.globalAlpha=a;ctx.fillStyle='#173b2a';ctx.beginPath();ctx.ellipse(x,y,w,11,0,0,PI*2);ctx.fill();ctx.restore();}
 function leaf(x,y,size=16,angle=0,color='#ffbe73',alpha=1){ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(-size,0);ctx.bezierCurveTo(-size*.6,-size*.8,size*.7,-size*.7,size,0);ctx.bezierCurveTo(size*.3,size*.8,-size*.6,size*.65,-size,0);ctx.fill();ctx.strokeStyle='#a65f32';ctx.lineWidth=Math.max(1,size*.06);ctx.beginPath();ctx.moveTo(-size*.85,0);ctx.lineTo(size*.8,0);ctx.stroke();ctx.restore();}
 function sprite(index,x,feet,height=320,{alpha=1,rotation=0,reactions=false}={}){
  const atlas=reactions?assets.reactions:assets.actor,meta=reactions?window.FOX_REACTIONS:window.ANIMATION_POSES;
  const f=meta?.frames?.[index];if(!f)return;
  const scale=height/Math.max(f.height,f.width*.88);
  ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);ctx.globalAlpha*=alpha;
  ctx.drawImage(atlas,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);ctx.restore();
 }
 function opponent(t,react=true){
  let lift=0,rot=0,x=930;
  if(react&&t>=1.61){const u=clamp((t-1.61)/.29),settle=clamp((t-1.9)/.48);lift=88*Math.sin(u*PI/2)*(1-smooth(settle));rot=Math.sin(u*PI*2)*.08*(1-settle);x+=Math.sin(u*PI*2)*14*(1-settle);}
  shadow(x,600,88*(1-lift/180),.16*(1-lift/150));
  const img=assets.reference;ctx.save();ctx.translate(x,598-lift);ctx.rotate(rot);
  ctx.drawImage(img,0,0,img.width/2,img.height,-160,-320,320,320);ctx.restore();
 }
 function background(){ctx.clearRect(0,0,W,H);ctx.drawImage(assets.bg,0,0,W,H);const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'#082c26b8');g.addColorStop(.45,'#102f1b12');g.addColorStop(1,'#13382926');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);}
 function healthbar(x,label,color,pct){box(x,80,300,64,18,'#153f31e8','#c8d6a94d');text(label,x+18,102,20,'#fff9ed',800,'left');box(x+18,122,264,9,5,'#ffffff33');box(x+18,122,Math.max(1,264*pct),9,5,color);}
 function leavesGather(t){if(t>=1.9)return;const alpha=1-clamp((t-1.54)/.36);for(let i=0;i<12;i++){const p=clamp((t-.12-i*.035)/.5),a=i*2.399+t*3,x=mix(70+i*32,300+Math.cos(a)*85,out(p)),y=mix(640,550+Math.sin(a)*35,out(p));leaf(x,y,8+i%3*3,a,'#ffc079',p*alpha*.8);}}
 function vortex(t,front){
  if(t<1.25||t>=2.05)return;
  const p=clamp((t-1.25)/.5),fade=1-clamp((t-1.82)/.23),cx=930,cy=485;
  ctx.save();ctx.globalAlpha=fade;
  for(let i=0;i<50;i++){const h=i/49,a=i*.58-t*14,side=Math.sin(a);if((side>0)!==front)continue;const r=(28+h*130)*out(p),x=cx+Math.cos(a)*r,y=cy+75-h*260;
   leaf(x,y,(7+i%4*2)*(front?1:.72),a+.7,i%3?'#ffbf73':'#e39145',(.5+.5*p)*(front?1:.6));
  }
  ctx.strokeStyle='#ffe1a3';ctx.lineWidth=front?4:2;ctx.globalAlpha*=.55;ctx.beginPath();
  for(let i=0;i<=70;i++){const h=i/70,a=h*PI*6-t*9,side=Math.sin(a),r=(28+h*125)*out(p),x=cx+Math.cos(a)*r,y=cy+75-h*260;if((side>0)!==front){ctx.moveTo(x,y);continue;}ctx.lineTo(x,y);}ctx.stroke();ctx.restore();
 }
 function tailArc(t,x,y){if(t<1.43||t>1.83)return;const u=(t-1.43)/.4;ctx.save();ctx.globalAlpha=Math.sin(u*PI)*.8;ctx.lineWidth=13;ctx.lineCap='round';ctx.strokeStyle='#ffcf89';ctx.beginPath();ctx.ellipse(x,y-130,125,65,-.1,PI*.8+u*3,PI*1.8+u*3);ctx.stroke();ctx.restore();}
 function fireworks(t){if(t<1.9)return;const u=t-1.9;for(let i=0;i<58;i++){const a=i*2.399,v=140+i%9*37,p=Math.max(0,u-i%5*.016),x=930+Math.cos(a)*v*p,y=385+Math.sin(a)*v*p+155*p*p;leaf(x,y,7+i%4*2,a+p*3,i%3?'#ffbe73':'#c3d88c',clamp(1-(p-.45)/.68));}}
 function title(t){if(mode!=='ultimate'||t<.65||t>1.65)return;const a=out((t-.65)/.14)*(1-clamp((t-1.48)/.17));ctx.save();ctx.globalAlpha=a;const s=.92+.08*out((t-.65)/.16);ctx.translate(640,212);ctx.scale(s,s);box(-408,-48,816,96,28,'#153f31f5','#ffbe73');text('LỐC ĐUÔI TINH QUÁI',0,2,45,'#fff3d2');leaf(-356,0,20,-.5);leaf(356,0,20,.5);ctx.restore();}
 function victory(t){if(t<1.9||mode!=='ultimate')return;ctx.save();ctx.globalAlpha=out((t-1.9)/.16);text('CHIẾN THẮNG!',640,209,62,'#fff4ce');text('LỐC ĐUÔI TINH QUÁI',640,267,22,'#ffe1a3');ctx.restore();}
 function foxState(t){
  let index=0,x=278,y=600,height=320,rotation=0;
  if(t<.65){index=t<.2?0:t<.43?1:2;x+=Math.sin(t*12)*9;}
  else if(t<.95){index=3;x-=16*smooth((t-.65)/.3);}
  else if(t<1.43){const u=(t-.95)/.48;x=mix(262,1105,smooth(u));y=600-65*Math.sin(u*PI);height=320-35*Math.sin(u*PI);index=4+Math.min(3,Math.floor(u*4));}
  else if(t<1.9){const u=(t-1.43)/.47;index=8+Math.min(3,Math.floor(u*4));x=mix(1105,1020,smooth(u));y=598-14*Math.sin(u*PI);rotation=Math.sin(u*PI*2)*.045;}
  else{const u=(t-1.9)/1.1;index=u<.12?12:u<.46?13:u<.7?14:15;x=mix(1020,650,out(u/.7));y=600-47*Math.sin(clamp((u-.05)/.5)*PI);}
  return {index,x,y,height,rotation};
 }
 function drawUltimate(t){
  const f=foxState(t);leavesGather(t);vortex(t,false);
  // The dart passes behind Mầm Sách; after the pivot the fox returns to foreground.
  if(t>=.95&&t<1.43){shadow(f.x,602,75,.17);sprite(f.index,f.x,f.y,f.height,{rotation:f.rotation});opponent(t);}
  else{opponent(t);shadow(f.x,602,85,.18);sprite(f.index,f.x,f.y,f.height,{rotation:f.rotation});}
  tailArc(t,f.x,f.y);vortex(t,true);fireworks(t);
  const a=1-clamp((t-1.9)/.16);ctx.save();ctx.globalAlpha=a;healthbar(88,'Cáo Nâu','#add88e',.72);healthbar(892,'Mầm Sách','#ffbe73',.16*(1-smooth((t-1.75)/.15)));ctx.restore();title(t);victory(t);
  return f.index;
 }
 function drawReaction(t){
  const p=clamp(t/(mode==='lose'?1.8:1.15)),base=mode==='attack'?0:mode==='hit'?4:8;
  let index=base+Math.min(3,Math.floor(p*4)),x=590,y=610,rotation=0;
  if(mode==='attack'){x+=Math.sin(clamp(t/1.15)*PI)*150;rotation=-Math.sin(p*PI)*.045;opponent(t,false);if(t>.45&&t<.95){for(let i=0;i<8;i++){const u=(t-.45)/.5;leaf(720+u*140-i*12,490+Math.sin(i*2.1)*36,7+i%3*2,i+u*4,'#ffbe73',Math.sin(u*PI));}}}
  if(mode==='hit'){x+=Math.sin(p*PI*4)*14*(1-p);rotation=Math.sin(p*PI)*.075;}
  if(mode==='lose')y+=18*smooth(p);
  shadow(x,621,100,.16);sprite(index,x,y,340,{reactions:true,rotation});
  text(modes[mode].toLocaleUpperCase('vi-VN'),640,182,38,'#fff4cf');
  text(mode==='lose'?'Mình nghỉ một chút rồi thử lại nhé!':mode==='hit'?'Hít thở, lấy lại thăng bằng.':'Một cú quét đuôi nhanh và gọn.',640,232,22,'#f5edce',600);
  return index;
 }
 function draw(t){
  t=clamp(t,0,3);background();const index=mode==='ultimate'?drawUltimate(t):drawReaction(t);
  text('5BMath',46,36,24,'#fff5d9',800,'left');text('CÁO NÂU',1234,36,16,'#f0f1d9',800,'right');
  const phase=mode==='ultimate'?(t<.95?'LẤY ĐÀ':t<1.9?'LỐC LÁ CAM':'CHIẾN THẮNG'):mode==='attack'?'TẤN CÔNG':mode==='hit'?'CHỊU ĐÒN':'BUỒN KHI THUA';
  box(440,651,400,40,20,'#153f31df');text(phase,640,672,15,'#fff3d2');
  document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  return {time:t,t,mode,phase,pose:index,nameVisible:mode==='ultimate'&&t>=.65&&t<=1.65,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory:mode==='ultimate'&&t>=1.9};
 }
 function pause(){playing=false;if(raf){cancelAnimationFrame(raf);raf=0;}document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 function setMode(value){if(!modes[value])throw new Error('Động tác không hợp lệ: '+value);mode=value;pause();clock=0;document.getElementById('mode').value=mode;document.querySelector('h1').textContent=modes[mode];document.title=modes[mode]+' · Cáo Nâu · 5BMath';canvas.setAttribute('aria-label',modes[mode]+' của Cáo Nâu.');if(assets.actor)draw(0);}
 const ready=Promise.all([load('actor',C.webpFile||C.poseFile),load('reactions',C.reactionsFile||'assets/reactions.webp'),load('bg',C.backgroundFile),load('reference',C.opponentFile)]).then(()=>{
  if(!window.ANIMATION_POSES?.frames||!window.FOX_REACTIONS?.frames)throw new Error('Thiếu metadata tư thế.');setMode(mode);if(!new URLSearchParams(location.search).has('export')&&!matchMedia('(prefers-reduced-motion: reduce)').matches)play(true);
 });
 window.animationDemo={ready,render:draw,pause,play,duration:DURATION,setMode,get mode(){return mode;},config:C};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);
 document.getElementById('mode').onchange=e=>{setMode(e.target.value);if(!matchMedia('(prefers-reduced-motion: reduce)').matches)play(true);};
 document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
