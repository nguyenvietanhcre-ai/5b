/* Thỏ — Canvas/WebP review. No game rules. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,PI=Math.PI,DURATION=3,assets={};
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),mix=(a,b,u)=>a+(b-a)*u;
 const ease=u=>{u=clamp(u);return u*u*(3-2*u);};
 let action='ultimate',playing=false,clock=0,last=0,speed=1,raf=0;
 const labels={ultimate:'Cú Nhảy Trăng Rằm',attack:'Tấn công',hit:'Chịu đòn',lose:'Buồn bã khi thua cuộc'};
 document.title='Thỏ · Bộ chuyển động · 5BMath';
 document.querySelector('h1').textContent=labels.ultimate;
 document.querySelector('header p').textContent='Thỏ · Canvas + WebP · Bốn hoạt cảnh';
 function load(key,src){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{assets[key]=im;resolve();};im.onerror=()=>reject(new Error('Không tải được '+src));im.src=src;});}
 function rect(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fillStyle=fill;ctx.fill();if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();}}
 function text(str,x,y,size=24,color='#fff9ed',weight=800){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(str,x,y);}
 function star(x,y,r,a=0,alpha=1){ctx.save();ctx.translate(x,y);ctx.rotate(a);ctx.globalAlpha*=alpha;ctx.beginPath();for(let i=0;i<10;i++){const ang=-PI/2+i*PI/5,rad=i%2?r*.42:r;i?ctx.lineTo(Math.cos(ang)*rad,Math.sin(ang)*rad):ctx.moveTo(Math.cos(ang)*rad,Math.sin(ang)*rad);}ctx.closePath();ctx.fillStyle='#ffdb8c';ctx.fill();ctx.restore();}
 function shadow(x,y,width=70,alpha=.2){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#183c2f';ctx.beginPath();ctx.ellipse(x,y,width,11,0,0,PI*2);ctx.fill();ctx.restore();}
 function pose(index,x,feet,size=1,rotation=0){const extra=action!=='ultimate',meta=extra?window.RABBIT_ACTIONS:window.ANIMATION_POSES;const f=meta.frames[index],scale=310/Math.max(...meta.frames.map(v=>v.height))*size;ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);ctx.drawImage(extra?assets.actions:assets.actor,f.left,f.top,f.width,f.height,-f.width*scale/2,-f.height*scale,f.width*scale,f.height*scale);ctx.restore();}
 function moon(t){if(t<.22||t>1.82)return;const a=ease((t-.22)/.5)*(1-ease((t-1.52)/.3));ctx.save();ctx.globalAlpha=a;const g=ctx.createRadialGradient(620,273,60,620,273,190);g.addColorStop(0,'#fff7d9');g.addColorStop(.75,'#ffe5a4');g.addColorStop(1,'#ffe5a400');ctx.fillStyle=g;ctx.fillRect(425,78,390,390);ctx.fillStyle='#fff1c7';ctx.beginPath();ctx.arc(620,273,136,0,PI*2);ctx.fill();ctx.fillStyle='#e5d39a55';for(const [x,y,r]of[[575,220,21],[659,303,32],[574,333,14]]){ctx.beginPath();ctx.arc(x,y,r,0,PI*2);ctx.fill();}ctx.restore();}
 function cushion(t){if(t<1.52)return;const u=ease((t-1.52)/.23);ctx.save();ctx.globalAlpha=u;ctx.fillStyle='#ffdf98';ctx.beginPath();ctx.ellipse(790,594,106,23,0,0,PI*2);ctx.fill();ctx.fillStyle='#fff1c7';ctx.beginPath();ctx.ellipse(790,587,100,20,0,0,PI*2);ctx.fill();ctx.restore();}
 function rings(t){if(t<1.75||t>2.32)return;const u=clamp((t-1.75)/.57);ctx.save();for(let k=0;k<3;k++){const p=clamp(u-k*.12);if(!p)continue;ctx.globalAlpha=(1-p)*.9;ctx.strokeStyle=k%2?'#fff6d0':'#ffce7c';ctx.lineWidth=7-3*p;ctx.beginPath();ctx.ellipse(790,592,35+p*430,10+p*82,0,0,PI*2);ctx.stroke();}ctx.restore();for(let i=0;i<18;i++){const a=i*2*PI/18;star(790+Math.cos(a)*u*310,560+Math.sin(a)*u*135,7,a+u,1-u);}}
 function fox(t){const hit=action==='ultimate'?clamp((t-1.75)/.4):action==='attack'?clamp((t-.55)/.4):0;const fade=action==='ultimate'?1-ease((t-2.0)/.45)*.78:1;const x=1030+hit*35,y=601-65*Math.sin(hit*PI);shadow(x,604,75,.16*fade);ctx.save();ctx.globalAlpha=fade;ctx.translate(x,y);ctx.rotate(.15*Math.sin(hit*PI));const im=assets.reference;ctx.drawImage(im,im.width/2,0,im.width/2,im.height,-137,-274,274,274);ctx.restore();if(hit>0&&hit<1)for(let i=0;i<6;i++){const a=i*PI/3+t*2;star(x+Math.cos(a)*94,y-190+Math.sin(a)*45,10,a,Math.sin(hit*PI));}}
 function banner(t){if(action!=='ultimate'||t<.65||t>1.55)return;ctx.save();ctx.globalAlpha=ease((t-.65)/.12)*(1-ease((t-1.42)/.13));rect(194,22,892,66,22,'#153f31f2','#ffbe73');text('CÚ NHẢY TRĂNG RẰM',640,56,39,'#fff1c7');star(234,56,13);star(1046,56,13);ctx.restore();}
 function celebration(t){if(action!=='ultimate'||t<1.9)return;const u=clamp((t-1.9)/1.1);ctx.save();ctx.globalAlpha=ease(u*5);text('CHIẾN THẮNG!',640,199,58,'#fff2cb');text('Cú Nhảy Trăng Rằm',640,251,26,'#ffe2a6');ctx.restore();for(let i=0;i<32;i++){const a=i*2.39996,p=clamp(u-(i%5)*.035),r=100+p*(130+i%4*26);star(660+Math.cos(a)*r,365+Math.sin(a)*r+p*p*140,4+i%4,a+p,1-p*.8);}}
 function draw(t){t=clamp(t,0,3);ctx.drawImage(assets.bg,0,0,W,H);const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'#113e30a8');g.addColorStop(.7,'#113e3010');g.addColorStop(1,'#113e3040');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
  ctx.save();let index=0,x=270,y=600,s=1,rotation=0,phase='LẤY ĐÀ';
  if(action==='ultimate'){
   moon(t);cushion(t);fox(t);
   if(t<.65){index=Math.min(2,Math.floor(t/.22));s=1-.025*Math.sin(t*PI/.65);}
   else if(t<.95){index=3;s=.97;x-=10*ease((t-.65)/.3);}
   else if(t<1.75){const u=(t-.95)/.8;index=4+Math.min(3,Math.floor(u*4));x=mix(260,790,ease(u));y=600-215*Math.sin(u*PI);rotation=-.06*Math.sin(u*PI);phase='ĐÒN QUYẾT ĐỊNH';for(let i=0;i<6;i++)star(x-40-i*21,y-55+i*9,4,i+t,.3*(1-i/6));}
   else if(t<1.9){index=8+Math.min(3,Math.floor((t-1.75)/.15*4));x=790;phase='ĐÒN QUYẾT ĐỊNH';s=1-.055*Math.sin((t-1.75)/.15*PI);}
   else{const u=(t-1.9)/1.1;index=12+Math.min(3,Math.floor(u*4));x=790;y=600-26*Math.sin(clamp(u*2)*PI);phase='CHIẾN THẮNG';}
   shadow(x,605,70*(1-(600-y)/600),.17);pose(index,x,y,s,rotation);rings(t);banner(t);celebration(t);
  }else{
   fox(t);x=455;phase=action==='attack'?'TẤN CÔNG':action==='hit'?'CHỊU ĐÒN':'THUA CUỘC';
   if(action==='attack'){const u=clamp(t/1.2);index=4+Math.min(3,Math.floor(u*4));x+=400*Math.sin(u*PI);y-=52*Math.sin(u*PI);if(u>=1)index=0;}
   if(action==='hit'){const u=clamp(t/1.2);index=8+Math.min(3,Math.floor(u*4));x-=35*Math.sin(u*PI);rotation=.12*Math.sin(u*PI);if(t<.8)for(let i=0;i<4;i++)star(x+Math.cos(i*PI/2+t*5)*95,y-260+Math.sin(i*PI/2+t*5)*35,9,i+t,1-t/.8);}
   if(action==='lose'){index=12+Math.min(3,Math.floor(t/.55));y+=4*ease(t/.8);text('Mình thử lại nhé!',640,150,42,'#fff1d6');}
   shadow(x,605);pose(index,x,y,1,rotation);if(action!=='lose')text(labels[action],640,150,42);
  }
  ctx.restore();rect(484,650,312,40,20,'#153f31dc');text(phase,640,671,16);ctx.textAlign='left';ctx.font='800 24px Arial';ctx.fillStyle='#fff9ed';ctx.fillText('5BMath',42,32);
  document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  return {t,time:t,action,phase,pose:index,nameVisible:action==='ultimate'&&t>=.65&&t<=1.55,attackStarted:action==='ultimate'&&t>=.95,impact:action==='ultimate'&&t>=1.75,victory:action==='ultimate'&&t>=1.9};
 }
 function pause(){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+(now-last)/1000*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 function setAction(value,autoplay=false){if(!labels[value])throw new Error('Unknown action');pause();action=value;clock=0;document.querySelector('h1').textContent=labels[value];document.getElementById('action').value=value;draw(0);if(autoplay)play(true);}
 const ready=Promise.all([load('actor',C.webpFile),load('actions','assets/actions.webp'),load('bg',C.backgroundFile),load('reference',C.opponentFile)]).then(()=>{draw(0);if(!new URLSearchParams(location.search).has('export')&&!matchMedia('(prefers-reduced-motion: reduce)').matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,setAction,duration:DURATION};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};document.getElementById('action').onchange=e=>setAction(e.target.value,!matchMedia('(prefers-reduced-motion: reduce)').matches);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
