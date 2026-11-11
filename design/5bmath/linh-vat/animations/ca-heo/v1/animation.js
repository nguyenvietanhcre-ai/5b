/* Cá heo — bespoke Canvas choreography. PNG originals stay in source/. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,DURATION=3,PI=Math.PI,TAU=PI*2,colors=['#f8b9cb','#ffbe73','#fff0a9','#aee4bd','#98e2f2','#bcbbf5'];
 const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n)),lerp=(a,b,u)=>a+(b-a)*u,smooth=n=>{const u=clamp(n);return u*u*(3-2*u);},out=n=>1-Math.pow(1-clamp(n),3);
 const assets={},labels={ultimate:'Sóng Âm Cầu Vồng',attack:'Tấn công',hurt:'Chịu đòn',lose:'Buồn bã khi thua'};
 let mode='ultimate',clock=0,speed=1,playing=false,last=0,raf=0;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 document.title='Cá heo — Sóng Âm Cầu Vồng · 5BMath';
 function load(key,url){return new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{assets[key]=im;resolve();};im.onerror=()=>reject(new Error('Không tải được '+url));im.src=url;});}
 function rect(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.stroke();}}
 function text(s,x,y,size,color='#fff9ed',weight=800){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(s,x,y);}
 function ellipse(x,y,rx,ry,fill,stroke){ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,TAU);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.stroke();}}
 function sparkle(x,y,r,color,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(x,y-r);ctx.quadraticCurveTo(x+r*.18,y-r*.18,x+r,y);ctx.quadraticCurveTo(x+r*.18,y+r*.18,x,y+r);ctx.quadraticCurveTo(x-r*.18,y+r*.18,x-r,y);ctx.quadraticCurveTo(x-r*.18,y-r*.18,x,y-r);ctx.fill();ctx.restore();}
 function bubble(x,y,r,color='#b8f0ee',alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.lineWidth=2.5;ellipse(x,y,r,r,color+'22',color);ellipse(x-r*.3,y-r*.32,r*.14,r*.09,'#ffffffc0');ctx.restore();}
 function ring(x,y,r,alpha=1,color='#b5eef3',width=4){ctx.save();ctx.globalAlpha*=alpha;ctx.lineWidth=width;ellipse(x,y,r*.34,r,null,color);ctx.restore();}
 function ripple(x,y,r,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.lineWidth=3;ellipse(x,y,r,r*.18,null,'#dbffff');ellipse(x,y,r*.72,r*.11,null,'#8ce0ec');ctx.restore();}
 function dolphin(index,x,y,scale=1,rotation=0,alpha=1,sheet='actor'){
  const im=assets[sheet];let f;
  if(sheet==='actor')f=window.ANIMATION_POSES.frames[index];
  else {const x0=Math.round(index%4*im.width/4),x1=Math.round((index%4+1)*im.width/4),y0=Math.round(Math.floor(index/4)*im.height/4),y1=Math.round((Math.floor(index/4)+1)*im.height/4);f={left:x0,top:y0,width:x1-x0,height:y1-y0};}
  const unit=sheet==='actor'?1.13:350/(im.width/4);ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.drawImage(im,f.left,f.top,f.width,f.height,-f.width*unit*scale/2,-f.height*unit*scale/2,f.width*unit*scale,f.height*unit*scale);ctx.restore();
 }
 function scenery(t){
  ctx.drawImage(assets.bg,0,0,W,H);const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#123f3be8');shade.addColorStop(.44,'#144c4250');shade.addColorStop(1,'#123f3b00');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  const sea=ctx.createLinearGradient(0,526,0,H);sea.addColorStop(0,'#8ad7d9');sea.addColorStop(.12,'#4faeb6');sea.addColorStop(1,'#255c67');ctx.beginPath();ctx.moveTo(0,H);ctx.lineTo(0,553);for(let x=0;x<=W;x+=12)ctx.lineTo(x,553+Math.sin(x*.012+t*2.1)*8+Math.sin(x*.025-t*1.6)*3);ctx.lineTo(W,H);ctx.closePath();ctx.fillStyle=sea;ctx.fill();
  ctx.lineWidth=2;for(let j=0;j<5;j++){ctx.strokeStyle=j%2?'#d5f1dc50':'#b4e9e875';ctx.beginPath();for(let x=0;x<=W;x+=10){const y=580+j*26+Math.sin(x*.014+t*1.4+j)*5;x?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();}for(let i=0;i<8;i++)sparkle(100+i*157+(i%2)*18,593+(i%3)*30,3+i%2,'#e1fff1',.4);
 }
 function opponent(t){
  const hit=mode==='ultimate'?out((t-1.75)/.18):mode==='attack'?out((t-1.1)/.18):0,fade=mode==='ultimate'?1-clamp((t-1.95)/.45)*.72:1;
  ctx.save();ctx.globalAlpha=fade;const x=1030+hit*24,y=465-Math.sin(hit*PI)*13;ellipse(x,578,80,12,'#133e3b30');ctx.translate(x,y);ctx.rotate(hit*.10);const im=assets.reference,sw=im.width/2;ctx.drawImage(im,sw,0,sw,im.height,-145,-140,290,290);ctx.restore();
  if(hit&&t<(mode==='ultimate'?2.18:1.7)){const u=clamp((t-(mode==='ultimate'?1.75:1.1))/.42);for(let i=0;i<7;i++){const a=i/7*TAU;sparkle(1030+Math.cos(a)*(35+u*100),430+Math.sin(a)*(30+u*76),7,colors[i%6],1-u);}}
 }
 function health(x,label,value,color){ctx.save();rect(x,76,290,70,20,'#173f3cda','#c3e0c55c');ctx.textAlign='left';ctx.textBaseline='middle';ctx.font='800 22px Arial';ctx.fillStyle='#fff9ed';ctx.fillText(label,x+20,104);rect(x+20,122,250,9,5,'#ffffff28');if(value>0)rect(x+20,122,250*value,9,5,color);ctx.restore();}
 function banner(t){if(mode!=='ultimate'||t<.65||t>1.55)return;const a=out((t-.65)/.13)*(1-clamp((t-1.43)/.12));ctx.save();ctx.globalAlpha=a;ctx.translate(640,208);ctx.scale(.94+.06*out((t-.65)/.18),1);ctx.lineWidth=2;rect(-395,-45,790,90,28,'#19463ef5','#bbe6df');text('SÓNG ÂM CẦU VỒNG',0,0,44,'#fff4d5');for(const x of [-350,350]){ring(x,0,16,1,'#ffcf9a',2);ring(x,0,25,.7,'#a9e8e2',2);}ctx.restore();}
 function gathering(t){if(t>.95)return;const u=clamp(t/.95);for(let i=0;i<4;i++){const p=(u+i*.2)%1,alpha=Math.sin(p*PI)*(.35+u*.4);ring(430+p*30,470-p*16,12+p*36,alpha,colors[i%6],2.5);}ripple(300,565,75+Math.sin(t*8)*12,.55);}
 function soundAndSphere(t){
  if(t<.95||t>1.94)return;const u=clamp((t-.95)/.8),centerX=lerp(660,1005,out(u)),centerY=439;
  for(let i=0;i<6;i++){const p=clamp((t-(.98+i*.055))/.56);if(!p)continue;const x=lerp(470+i*5,centerX,p),r=lerp(20+i*6,76-i*5,p);ring(x,lerp(428,centerY,p),r,(1-clamp((t-1.66)/.17))*.78,colors[i%6],3.8);}
  if(t>=1.30&&t<1.80){const p=out((t-1.30)/.45),r=26+70*p;ctx.save();ctx.globalAlpha=1-clamp((t-1.75)/.05);const g=ctx.createRadialGradient(centerX-r*.25,centerY-r*.3,4,centerX,centerY,r);g.addColorStop(0,'#edfffecb');g.addColorStop(.45,'#b5edf4a0');g.addColorStop(.86,'#7fcded70');g.addColorStop(1,'#d9f9f6df');ellipse(centerX,centerY,r,r,g,'#e0fff9');ctx.lineWidth=4;for(let i=0;i<6;i++){ctx.strokeStyle=colors[i];ctx.beginPath();ctx.arc(centerX,centerY,r*(.7+.04*i),-1.5+i*.85,-.82+i*.85);ctx.stroke();}ellipse(centerX-r*.32,centerY-r*.35,r*.18,r*.09,'#ffffffb0');ctx.restore();}
 }
 function burst(t,start=1.75,amount=38){if(t<start)return;const u=t-start;if(u>1.25)return;for(let i=0;i<amount;i++){const a=i*2.39996,v=95+(i*47)%250,p=clamp(u/.9),x=1005+Math.cos(a)*v*u,y=440+Math.sin(a)*v*u+70*u*u,alpha=clamp((1.25-u)/.55);bubble(x,y,(5+i%6*2)*(1-.22*p),colors[i%6],alpha);if(i%6===0)sparkle(x+9,y-9,7,colors[(i+2)%6],alpha);}}
 function splash(x,t,start){const u=t-start;if(u<0||u>.65)return;const q=u/.65;ripple(x,565,40+q*110,1-q);for(let i=0;i<12;i++){const a=PI+(.12+i/11*.76)*PI,v=65+(i*37)%120;bubble(x+Math.cos(a)*v*q,558+Math.sin(a)*v*q+60*q*q,3+i%3,'#d0f7f2',1-q);}}
 function ending(t){if(mode!=='ultimate'||t<1.9)return;const u=out((t-1.9)/.28);ctx.save();ctx.globalAlpha=u;ctx.shadowColor='#183e35';ctx.shadowBlur=12;text('CHIẾN THẮNG!',640,208,62,'#fff2c7');ctx.shadowBlur=0;text('Một cú nhảy, ngàn sắc màu!',640,262,22,'#e6f9e7',700);sparkle(335,207,23,'#ffcf8e');sparkle(945,207,23,'#bce9e3');ctx.restore();for(let i=0;i<12;i++){const q=(t-1.9)*.75,px=430+(i*113)%430,py=430-q*(65+(i*23)%110);bubble(px,py,5+i%5,colors[i%6],Math.min(1,q*4)*clamp((3.2-t)/.5));}}
 function ultimate(t){
  gathering(t);let index=0,x=300,y=483,rotation=0,scale=1;
  if(t<.65){index=Math.min(2,Math.floor(t/.23));y+=Math.sin(t*9)*5;rotation=-.04*Math.sin(t*6);}
  else if(t<.95){index=3;const u=(t-.65)/.3;x-=12*smooth(u);y+=9*Math.sin(u*PI);}
  else if(t<1.55){const u=(t-.95)/.6;index=4+Math.min(4,Math.floor(u*5));x=lerp(288,580,smooth(u));y=488-112*Math.sin(u*PI);rotation=TAU*smooth(u);scale=.98;for(let i=2;i>0;i--)dolphin(index,x-i*24,y+i*6,scale,rotation,.045*(3-i));}
  else if(t<1.9){index=t<1.69?9:10;x=lerp(580,615,smooth((t-1.55)/.35));y=488-5*Math.sin(t*14);}
  else {const u=t-1.9;x=lerp(615,555,smooth(u/.5));index=u<.16?12:u<.42?13:u<.73?14:15;y=488-43*Math.sin(clamp((u-.1)/.7)*PI);}
  dolphin(index,x,y,scale,rotation);soundAndSphere(t);burst(t);splash(300,t,.95);splash(570,t,1.95);ending(t);return index;
 }
 function action(t){let index=0,x=340,y=485,rotation=0;
  if(mode==='attack'){
   if(t<.45){index=Math.min(3,Math.floor(t/.12));x-=smooth(t/.45)*20;}
   else if(t<1.15){const u=(t-.45)/.7;index=4+Math.min(2,Math.floor(u*3));x=lerp(320,675,out(u));y-=Math.sin(u*PI)*42;rotation=-.08*Math.sin(u*PI);for(let i=0;i<4;i++){const p=clamp((t-(.6+i*.07))/.55);if(p)ring(lerp(x+95,1010,p),455,16+p*30,(1-p)*.85,colors[i%6],3);}}
   else {index=7;const u=smooth((t-1.3)/.85);x=lerp(675,340,u);y-=Math.sin(u*PI)*15;}burst(t,1.1,17);splash(670,t,1.3);
  } else if(mode==='hurt'){
   const u=clamp((t-.35)/1.25);index=t<.35?0:8+Math.min(3,Math.floor(u*4));x-=Math.sin(u*PI)*60;y+=Math.sin(u*PI)*15;rotation=.13*Math.sin(u*PI);if(t>=.35&&t<.85){const p=(t-.35)/.5;for(let i=0;i<6;i++){const a=i/6*TAU;sparkle(x+Math.cos(a)*(55+p*60),y+Math.sin(a)*(45+p*45),7,colors[i%6],1-p);}}
  } else {const u=clamp(t/1.8);index=12+Math.min(3,Math.floor(u*4));y+=out(u)*35;rotation=.04*out(u);if(t>.8){const p=clamp((t-.8)/1.9);bubble(x+52,455+p*55,5,'#bce8f0',Math.sin(p*PI)*.55);}}
  ripple(x,565,80,.5);dolphin(index,x,y,1,rotation,1,'actions');
  if(mode==='lose'){text('Mình sẽ thử lại!',850,254,42,'#fff1cb');text('Nghỉ một chút rồi cùng luyện tập nhé.',850,305,24,'#d6eee0',600);}else {text(mode==='attack'?'TẤN CÔNG':'CHỊU ĐÒN',640,214,43,'#fff1cf');text(mode==='attack'?'Lướt nhanh · Sóng âm nhỏ':'Lùi nhẹ · Lấy lại thăng bằng',640,260,23,'#d3eee3',600);}return index;
 }
 function draw(t){
  t=clamp(Number(t)||0,0,DURATION);scenery(t);opponent(t);const index=mode==='ultimate'?ultimate(t):action(t);health(74,'Cá heo',mode==='hurt'?.50:mode==='lose'?.03:.74,'#aee3b6');health(916,'Cáo Nâu',mode==='ultimate'?.18*(1-smooth((t-1.75)/.15)):mode==='attack'?.58-.18*smooth((t-1.1)/.15):.76,'#ffbe73');banner(t);ctx.save();ctx.textAlign='left';ctx.font='800 24px Arial';ctx.fillStyle='#fff1d5';ctx.fillText('5BMath',45,35);ctx.restore();const phase=mode==='ultimate'?(t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG'):labels[mode].toLocaleUpperCase('vi-VN');rect(450,650,380,42,21,'#123f3bdc');text(phase,640,672,17,'#fff4d7');document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';return {t,time:t,mode,phase,pose:index,nameVisible:mode==='ultimate'&&t>=.65&&t<=1.55,attackStarted:mode==='ultimate'?t>=.95:mode==='attack'&&t>=.45,impact:mode==='ultimate'?t>=1.75:mode==='attack'&&t>=1.1,victory:mode==='ultimate'&&t>=1.9};
 }
 function pause(){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 function setMode(value){if(!labels[value])throw new Error('Chế độ animation không hợp lệ');pause();mode=value;clock=0;document.getElementById('mode').value=mode;document.querySelector('header p').textContent=mode==='ultimate'?'Cá heo · Lấy đà → lộn vòng → cầu nước → bọt cầu vồng':'Cá heo · '+labels[mode];draw(0);return mode;}
 const ready=Promise.all([load('actor',C.webpFile||C.poseFile),load('actions','assets/actions.webp'),load('bg',C.backgroundFile),load('reference',C.opponentFile)]).then(()=>{if(!window.ANIMATION_POSES)throw new Error('Thiếu poses.js');draw(0);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,setMode,duration:DURATION,get mode(){return mode;},get playing(){return playing;}};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};document.getElementById('mode').onchange=e=>{setMode(e.target.value);if(!reduced.matches)play(true);};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{if(reduced.matches)pause();});ready.catch(error=>{document.querySelector('.note').textContent=error.message;console.error(error);});
})();
