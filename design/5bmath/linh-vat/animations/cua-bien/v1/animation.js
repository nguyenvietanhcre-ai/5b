/* Cua biển: sideways scuttle, twin light pincers and a water bubble. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG;
 if(!C)throw new Error('Thiếu config.js.');
 const canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,DURATION=3,TAU=Math.PI*2;
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
 const mix=(a,b,u)=>a+(b-a)*u;
 const smooth=u=>{u=clamp(u);return u*u*(3-2*u);};
 const ease=u=>1-Math.pow(1-clamp(u),3);
 const modes={ultimate:'Song Càng Khóa Sóng',attack:'Tấn công · Càng bật sóng',hit:'Chịu đòn · Vững vàng trở lại',defeat:'Thua cuộc · Buồn một chút thôi'};
 let mode='ultimate',playing=false,clock=0,last=0,speed=1,raf=0,loaded=false;
 const images={};
 const controls={seek:document.getElementById('seek'),clock:document.getElementById('clock'),pause:document.getElementById('pause'),mode:document.getElementById('action')};
 document.title='Cua biển — Bốn animation · 5BMath';
 function load(key,url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{images[key]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được '+url));img.src=url;});}
 function rect(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.stroke();}}
 function text(str,x,y,size,color,weight=800,align='center'){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(str,x,y);}
 function star(x,y,r,color,angle=0,alpha=1){ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.43:r;i?ctx.lineTo(Math.cos(a)*rr,Math.sin(a)*rr):ctx.moveTo(Math.cos(a)*rr,Math.sin(a)*rr);}ctx.closePath();ctx.fillStyle=color;ctx.fill();ctx.restore();}
 function shadow(x,y,w,alpha=.18){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#173e2e';ctx.beginPath();ctx.ellipse(x,y,w,12,0,0,TAU);ctx.fill();ctx.restore();}
 function pose(index,x,y,size=1,alpha=1,angle=0){const p=window.ANIMATION_POSES.frames[index];const maxWidth=Math.max(...window.ANIMATION_POSES.frames.map(p=>p.width));const s=340/maxWidth*size;ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha*=alpha;ctx.drawImage(images.actor,p.left,p.top,p.width,p.height,-p.width*s/2,-p.height*s,p.width*s,p.height*s);ctx.restore();}
 function pincer(x,y,size,mirror=1,closing=0,alpha=1){ctx.save();ctx.translate(x,y);ctx.scale(mirror*size/100,size/100);ctx.globalAlpha*=alpha;ctx.shadowColor='#91f2e9';ctx.shadowBlur=20;ctx.lineWidth=5;ctx.lineJoin='round';ctx.fillStyle='#ffcf88';ctx.strokeStyle='#fff7d5';
  ctx.beginPath();ctx.moveTo(-7,52);ctx.bezierCurveTo(-62,37,-63,-15,-22,-44);ctx.bezierCurveTo(-28,-9,-13,1,0,12);ctx.bezierCurveTo(13,-3,25,-22,21,-46+closing*25);ctx.bezierCurveTo(70,-15,60,32,17,53);ctx.closePath();ctx.fill();ctx.stroke();
  ctx.fillStyle='#fff8dd';ctx.beginPath();ctx.ellipse(0,43,16,11,0,0,TAU);ctx.fill();ctx.restore();}
 function waterArc(cx,cy,r,alpha,t){ctx.save();ctx.globalAlpha*=alpha;ctx.lineCap='round';for(let i=0;i<3;i++){ctx.strokeStyle=['#e1fff7','#9eebe2','#53c8d5'][i];ctx.lineWidth=4+i*3;ctx.beginPath();ctx.ellipse(cx,cy,r+i*8,r*.78+i*7,0,Math.PI*.10+t*.2,Math.PI*1.93+t*.2);ctx.stroke();}ctx.restore();}
 function bubble(x,y,r,alpha){ctx.save();ctx.globalAlpha*=alpha;const gradient=ctx.createRadialGradient(x-r*.3,y-r*.4,2,x,y,r);gradient.addColorStop(0,'#f5fff71c');gradient.addColorStop(.6,'#a6f4e92a');gradient.addColorStop(1,'#6cded370');ctx.fillStyle=gradient;ctx.strokeStyle='#c9fff1';ctx.lineWidth=5;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.stroke();ctx.lineWidth=10;ctx.strokeStyle='#ffffffb8';ctx.beginPath();ctx.arc(x,y,r*.84,Math.PI*1.13,Math.PI*1.47);ctx.stroke();ctx.restore();}
 function opponent(t){let x=1020,y=597,angle=0,alpha=1,scale=1;
  if(mode==='ultimate'&&t>=1.4){const lift=smooth((t-1.4)/.32);y-=55*lift;scale=1-.08*lift;if(t>=1.75){const pop=ease((t-1.75)/.28);x+=45*pop;y-=18*Math.sin(pop*Math.PI);angle=.08*pop;alpha=1-.80*pop;}}
  if(mode==='attack'&&t>=.62){const u=clamp((t-.62)/.42);x+=25*Math.sin(u*Math.PI);angle=.05*Math.sin(u*Math.PI);}
  shadow(x,603,84,.18*alpha);ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.scale(scale,scale);ctx.globalAlpha=alpha;const img=images.opponent,sw=img.width/2;ctx.drawImage(img,sw,0,sw,img.height,-153,-306,306,306);ctx.restore();
 }
 function tracks(t,x,y){if(t<.95||t>1.7)return;const a=1-smooth((t-1.5)/.2);for(let i=3;i>=1;i--){pose(4+Math.floor((t-.95)*17)%4,x-i*56,y,1,(.20-i*.035)*a);pose(4+Math.floor((t-.95)*17)%4,x+i*46,y,1,(.13-i*.024)*a);}ctx.save();ctx.globalAlpha=.45*a;ctx.strokeStyle='#a7f1e3';ctx.lineWidth=4;ctx.lineCap='round';for(let i=0;i<7;i++){const yy=530+i*10,xx=x-180-i%3*27;ctx.beginPath();ctx.moveTo(xx-70,yy);ctx.lineTo(xx+20,yy);ctx.stroke();}ctx.restore();}
 function ultimateFX(t){if(t<.95||t>2.18)return;
  const gather=smooth((t-.95)/.55),close=smooth((t-1.46)/.29),fade=1-smooth((t-1.77)/.19),cx=1020,cy=420;
  waterArc(cx,cy,80+70*gather,.7*fade,t);
  if(t>1.15&&t<1.91){const width=mix(170,95,close);pincer(cx-width,cy,125,1,close,fade);pincer(cx+width,cy,125,-1,close,fade);}
  if(t>=1.40&&t<1.79){bubble(cx,cy,153*ease((t-1.4)/.18),fade);}
  if(t>=1.75){const u=clamp((t-1.75)/.43);for(let i=0;i<20;i++){const a=i*TAU/20+.10;const radius=40+ease(u)*(85+(i%3)*20);star(cx+Math.cos(a)*radius,cy+Math.sin(a)*radius,6+(1-u)*7,i%2?'#ffdb96':'#d6fff4',a+u,1-u);}for(let i=0;i<7;i++){const a=i*TAU/7+.2;const r=60+u*170;bubble(cx+Math.cos(a)*r,cy+Math.sin(a)*r,5+(i%3)*4,(1-u)*.75);}}
 }
 function banner(t){if(mode!=='ultimate'||t<.65||t>1.61)return;const show=ease((t-.65)/.15),fade=1-smooth((t-1.44)/.17);ctx.save();ctx.globalAlpha=fade;ctx.translate(640,211);ctx.scale(.9+.1*show,.9+.1*show);ctx.lineWidth=2;rect(-405,-45,810,90,25,'#153f31f5','#ffcf88');text('SONG CÀNG KHÓA SÓNG',0,0,44,'#fff4d5');pincer(-360,0,34,1,.5);pincer(360,0,34,-1,.5);ctx.restore();}
 function win(t){if(mode!=='ultimate'||t<1.9)return;const u=clamp((t-1.9)/.25);ctx.save();ctx.globalAlpha=ease(u);text('CHIẾN THẮNG!',640,205,60,'#fff4cc');text('Song Càng Khóa Sóng',640,262,26,'#ffda97');star(345,206,25,'#ffcf88',-.2);star(935,206,25,'#ffcf88',.2);ctx.restore();for(let i=0;i<40;i++){const a=i*2.4,p=t-1.9,speed=110+i%7*35,x=640+Math.cos(a)*speed*p,y=370+Math.sin(a)*speed*p+120*p*p;star(x,y,4+i%3,i%2?'#a9ead7':'#ffcf88',a+p,1-smooth((p-.6)/.5));}}
 function header(){ctx.fillStyle='#0c2c2680';ctx.fillRect(0,0,W,70);text('5BMath',38,36,24,'#fff5d9',800,'left');text('CUA BIỂN · ĐẤU TRÍ',W-38,36,18,'#effbe6',800,'right');}
 function draw(t){t=clamp(t,0,DURATION);ctx.clearRect(0,0,W,H);ctx.drawImage(images.background,0,0,W,H);const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#0b302680');shade.addColorStop(.5,'#0b302600');shade.addColorStop(1,'#0b302635');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  let index=0,x=300,y=600,angle=0,scale=1,phase='LẤY ĐÀ';
  if(mode==='ultimate'){
   if(t<.65){index=t<.2?0:t<.4?1:2;y+=Math.sin(t*12)*2;}
   else if(t<.95){index=3;x-=12*smooth((t-.65)/.3);}
   else if(t<1.45){const u=(t-.95)/.5;index=4+Math.floor(u*12)%4;x=mix(288,610,smooth(u));y-=5*Math.sin(u*8*Math.PI);}
   else if(t<1.9){index=8+Math.min(3,Math.floor((t-1.45)/.45*4));x=610;}
   else{index=12;x=610;y-=24*Math.sin(clamp((t-1.9)/.48)*Math.PI);}
   phase=t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG';
  }else if(mode==='attack'){
   if(t<.23){index=2;x-=8*smooth(t/.23);}else if(t<.80){const u=(t-.23)/.57;index=4+Math.min(3,Math.floor(u*4));x=mix(292,650,ease(u));y-=4*Math.sin(u*4*Math.PI);}else if(t<1.35){index=14;x=mix(650,300,smooth((t-.8)/.55));}phase=t<.23?'LẤY ĐÀ':t<.8?'BẬT CÀNG':'TRỞ VỀ TƯ THẾ';
  }else if(mode==='hit'){
   if(t<.12){index=0;}else if(t<.65){index=13;const u=(t-.12)/.53;x-=28*Math.sin(u*Math.PI);angle=-.045*Math.sin(u*Math.PI);}else if(t<1.25){index=14;}phase=t<.12?'CHUẨN BỊ':t<.65?'CHỊU ĐÒN':'VỮNG VÀNG TRỞ LẠI';
  }else{index=t<.3?14:15;y+=8*smooth(t/.4);phase='BUỒN MỘT CHÚT · CỐ GẮNG LẦN SAU';}
  ctx.save();opponent(t);if(mode==='ultimate')tracks(t,x,y);shadow(x,603,105);pose(index,x,y,scale,1,angle);
  if(mode==='ultimate')ultimateFX(t);
  if(mode==='attack'&&t>.42&&t<1.06){const u=clamp((t-.42)/.64);waterArc(mix(660,1015,ease(u)),450,30+u*20,1-u,t);}
  if(mode==='hit'&&t>.12&&t<.65){const u=(t-.12)/.53;for(let i=0;i<5;i++)star(x+Math.cos(i*TAU/5)*(50+u*80),410+Math.sin(i*TAU/5)*45,8,'#ffdb96',i+u,1-u);}
  ctx.restore();header();banner(t);win(t);
  if(mode!=='ultimate'){rect(320,115,640,64,22,'#153f31e8');text(modes[mode],640,147,30,'#fff2d1');}
  if(mode==='defeat'&&t>.4){const a=ease((t-.4)/.3);ctx.save();ctx.globalAlpha=a;rect(530,280,610,86,24,'#fff9ede8');text('Buồn một chút thôi…',835,309,26,'#203a32');text('Luyện tập thêm, lần sau mình sẽ làm tốt hơn!',835,341,20,'#1f6248',600);ctx.restore();}
  rect(380,650,520,40,20,'#153f31d9');text(phase,640,671,17,'#fff3d2');controls.seek.value=t;controls.clock.textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  return {time:t,t,mode,phase,pose:index,nameVisible:mode==='ultimate'&&t>=.65&&t<=1.61,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory:mode==='ultimate'&&t>=1.9};
 }
 function pause(){playing=false;if(raf){cancelAnimationFrame(raf);raf=0;}controls.pause.textContent='Tiếp tục';}
 function play(reset=false){if(!loaded)return;if(reset)clock=0;playing=true;last=performance.now();controls.pause.textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function selectMode(next,{autoplay=true}={}){if(!Object.hasOwn(modes,next))throw new Error('Animation không hợp lệ: '+next);pause();mode=next;clock=0;controls.mode.value=mode;document.querySelector('h1').textContent=modes[mode];if(loaded)draw(0);if(autoplay)play(true);return mode;}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(DURATION,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<DURATION)raf=requestAnimationFrame(tick);else pause();}
 const ready=Promise.all([load('actor',C.webpFile||C.poseFile),load('background',C.backgroundFile),load('opponent',C.opponentFile)]).then(()=>{if(!window.ANIMATION_POSES?.frames?.length)throw new Error('Chưa có poses.js; chạy prepare.');loaded=true;selectMode(new URLSearchParams(location.search).get('action')||'ultimate',{autoplay:false});if(!new URLSearchParams(location.search).has('export')&&!matchMedia('(prefers-reduced-motion: reduce)').matches)play(true);return true;});
 const api={ready,render:draw,renderAt:draw,pause,play,duration:DURATION,canvas,selectMode,setMode:selectMode,get mode(){return mode;},get playing(){return playing;},get time(){return clock;}};
 window.animationDemo=api;window.demo=api;
 document.getElementById('replay').onclick=()=>play(true);controls.pause.onclick=()=>playing?pause():play(clock>=DURATION);document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};controls.seek.oninput=e=>{pause();clock=Number(e.target.value);if(loaded)draw(clock);};controls.mode.onchange=e=>selectMode(e.target.value);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 ready.catch(error=>{pause();document.querySelector('.note').textContent=error.message;console.error(error);});
})();
