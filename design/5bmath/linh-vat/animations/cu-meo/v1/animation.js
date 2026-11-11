/* Cú mèo: moonlit flight, curved wing shadows and four independent actions. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,P=window.ANIMATION_POSES,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const PI=Math.PI,W=1280,H=720,DURATION=3,assets={},reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const clamp=n=>Math.max(0,Math.min(1,n)),mix=(a,b,u)=>a+(b-a)*u,smooth=n=>{n=clamp(n);return n*n*(3-2*n);};
 const labels={ultimate:'Ánh Mắt Đêm Trăng',attack:'Tấn công · Lướt cánh',hit:'Chịu đòn',defeat:'Buồn khi thua cuộc'};
 let mode='ultimate',playing=false,time=0,last=0,speed=1,raf=0;
 document.title='Cú mèo — Ánh Mắt Đêm Trăng · 5BMath';document.querySelector('h1').textContent=labels.ultimate;document.querySelector('header p').textContent='Cú mèo · Bốn hoạt cảnh Canvas + WebP';
 function load(key,src){return new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>{assets[key]=i;resolve();};i.onerror=()=>reject(Error('Không tải được '+src));i.src=src;});}
 function text(s,x,y,size=24,color='#fff9ed'){ctx.fillStyle=color;ctx.font=`800 ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(s,x,y);}
 function pill(x,y,w,h,color){ctx.fillStyle=color;ctx.beginPath();ctx.roundRect(x,y,w,h,22);ctx.fill();}
 function star(x,y,r,alpha=1){ctx.save();ctx.translate(x,y);ctx.globalAlpha*=alpha;ctx.fillStyle='#ffdc92';ctx.beginPath();for(let i=0;i<10;i++){const a=-PI/2+i*PI/5,d=i%2?r*.43:r;ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d);}ctx.closePath();ctx.fill();ctx.restore();}
 function crescent(x,y,r,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.strokeStyle='#fff1c3';ctx.lineWidth=7;ctx.lineCap='round';ctx.beginPath();ctx.arc(x,y,r,PI*.26,PI*1.74);ctx.stroke();ctx.restore();}
 function pose(index,x,feet,height=300,alpha=1,rotation=0){const f=P.frames[index],scale=height/274;ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.drawImage(assets.owl,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);ctx.restore();}
 function shadow(x,y,width=85,alpha=.17){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#102d2c';ctx.beginPath();ctx.ellipse(x,y,width,12,0,0,PI*2);ctx.fill();ctx.restore();}
 function opponent(t){const hit=mode==='ultimate'?smooth((t-1.75)/.15):mode==='attack'?smooth((t-.5)/.18):0,x=1000+hit*35,y=604-Math.sin(hit*PI)*27;shadow(x,607);ctx.save();ctx.translate(x,y);ctx.rotate(hit*.08);const i=assets.opponent;ctx.drawImage(i,i.width/2,0,i.width/2,i.height,-145,-290,290,290);ctx.restore();}
 function night(t){if(mode!=='ultimate')return;const alpha=.62*smooth(t/.62)*(1-smooth((t-2.15)/.8));ctx.fillStyle=`rgba(10,23,53,${alpha})`;ctx.fillRect(0,0,W,H);for(let i=0;i<18;i++)star(75+(i*197)%1140,190+(i*71)%260,2+i%3,alpha*.85);crescent(1090,210,55,alpha);}
 function moonStrike(t){if(t<1.18||t>2.45)return;const open=smooth((t-1.18)/.57),fade=1-smooth((t-1.86)/.59);ctx.save();ctx.globalAlpha=fade;ctx.shadowColor='#fff0b4';ctx.shadowBlur=18;ctx.strokeStyle='#fff1c3';ctx.lineWidth=9;ctx.lineCap='round';
  for(const side of [-1,1]){ctx.save();ctx.translate(1000,450);ctx.scale(side,1);ctx.beginPath();ctx.ellipse(0,0,130,154,0,-PI/2,-PI/2+PI*open);ctx.stroke();ctx.restore();}
  if(t>=1.75){const u=clamp((t-1.75)/.65);ctx.globalAlpha=fade*(1-u)*.45;ctx.fillStyle='#fff5d4';ctx.beginPath();ctx.ellipse(1000,450,135,158,0,0,PI*2);ctx.fill();ctx.globalAlpha=1;for(let i=0;i<12;i++){const a=i*PI/6;star(1000+Math.cos(a)*(35+u*170),450+Math.sin(a)*(35+u*160),8,1-u);}}
  ctx.restore();
 }
 function eyes(x,y,alpha){ctx.save();ctx.globalAlpha=alpha*.6;ctx.fillStyle='#ffeb9e';ctx.shadowColor='#fff2a4';ctx.shadowBlur=22;for(const dx of [-34,34]){ctx.beginPath();ctx.ellipse(x+dx,y-192,13,17,0,0,PI*2);ctx.fill();}ctx.restore();}
 function ultimate(t){let index=0,x=265,y=605;
  if(t<.95){index=Math.min(3,Math.floor(t/.95*4));y-=10*Math.sin(t/.95*PI);}
  else if(t<1.75){const u=(t-.95)/.8;x=mix(265,1050,smooth(u));y=605-140*Math.sin(u*PI);index=4+Math.min(3,Math.floor(u*4));for(let i=3;i>=1;i--)pose(index,x-i*52,y+i*8,300,.13/(i*.6));}
  else if(t<1.9){index=7;x=1050;y=605-35*Math.sin((t-1.75)/.15*PI);}
  else{const u=smooth((t-1.9)/.32);x=mix(1050,650,u);index=12+Math.min(3,Math.floor((t-1.9)/1.1*4));y=605-22*Math.sin(u*PI);}
  shadow(x,611,84,Math.max(.04,.17-(605-y)/1200));pose(index,x,y);if(t>.35&&t<1.18)eyes(x,y,Math.sin(clamp((t-.35)/.83)*PI));moonStrike(t);
  if(t>=.65&&t<1.63){ctx.save();ctx.globalAlpha=smooth((t-.65)/.12)*(1-smooth((t-1.5)/.13));pill(206,175,868,84,'#16342ef5');crescent(257,217,22);text('ÁNH MẮT ĐÊM TRĂNG',655,217,43,'#fff0c6');ctx.restore();}
  if(t>=1.9){ctx.save();ctx.globalAlpha=smooth((t-1.9)/.22);text('CHIẾN THẮNG!',640,213,57,'#fff1c9');text('Ánh Mắt Đêm Trăng',640,270,25,'#ffe1a6');for(let i=0;i<12;i++){const a=i*PI/6;star(650+Math.cos(a)*(150+(t-1.9)*100),380+Math.sin(a)*110,8,1-(t-1.9)*.45);}ctx.restore();}return index;
 }
 function action(t){const u=clamp(t/(mode==='attack'?1.2:mode==='hit'?.9:2.4));let index=0,x=425,y=605,rotation=0;
  if(mode==='attack'){index=u<.18?3:u<.75?4+Math.min(3,Math.floor((u-.18)/.57*4)):12;const travel=Math.sin(u*PI);x+=travel*230;y-=travel*80;}
  if(mode==='hit'){index=u<.45?8:u<.88?9:0;x+=Math.sin(u*PI*5)*(1-u)*24;rotation=Math.sin(u*PI)*.07;if(u<.8)for(let i=0;i<3;i++)star(365+i*55,260+Math.sin(u*9+i)*12,12,1-u);}
  if(mode==='defeat'){index=u<.4?10:11;y+=smooth(u)*14;}
  shadow(x,615);pose(index,x,y,310,1,rotation);text(labels[mode],640,220,42,'#fff4d4');if(mode==='defeat')text('Mình thử lại nhé!',680,296,27,'#ffe1a6');return index;
 }
 function draw(t){t=Math.max(0,Math.min(DURATION,t));ctx.drawImage(assets.bg,0,0,W,H);ctx.fillStyle='#092b3238';ctx.fillRect(0,0,W,H);night(t);opponent(t);const index=mode==='ultimate'?ultimate(t):action(t);pill(32,24,220,48,'#163c31d9');text('5BMath · Cú mèo',142,48,22);const phase=mode!=='ultimate'?labels[mode]:t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG';pill(425,650,430,42,'#163c31d9');text(phase,640,672,17);document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';return {t,time:t,mode,pose:index,phase,nameVisible:mode==='ultimate'&&t>=.65&&t<1.63,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory:mode==='ultimate'&&t>=1.9};}
 function pause(){playing=false;cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)time=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;time=Math.min(3,time+Math.max(0,(now-last)/1000)*speed);last=now;draw(time);if(time<3)raf=requestAnimationFrame(tick);else pause();}
 function setMode(value){if(!labels[value])throw Error('Trạng thái không hợp lệ');pause();mode=value;time=0;document.querySelector('h1').textContent=labels[mode];document.getElementById('action').value=mode;draw(0);}
 const ready=Promise.all([load('owl',C.webpFile),load('bg',C.backgroundFile),load('opponent',C.opponentFile)]).then(()=>{draw(0);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,duration:DURATION,setMode,getState:()=>({playing,time,mode,raf})};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(time>=3);document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('seek').oninput=e=>{pause();time=Number(e.target.value);draw(time);};document.getElementById('action').onchange=e=>{setMode(e.target.value);if(!reduced.matches)play(true);};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{if(reduced.matches)pause();});ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
