/* Bạch tuộc: authored ink veil, eight magical arms and eight water spheres. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG,W=1280,H=720,PI=Math.PI,DURATION=3;
 const canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),mix=(a,b,u)=>a+(b-a)*u;
 const smooth=u=>{u=clamp(u);return u*u*(3-2*u);};
 const labels={ultimate:'Tám Tay Ảo Thuật',attack:'Tấn công · Bóng nước',hit:'Chịu đòn · Bình tĩnh trở lại',lose:'Thua cuộc · Thử lại nhé!'};
 let mode=new URLSearchParams(location.search).get('mode')||'ultimate';if(!labels[mode])mode='ultimate';
 let playing=false,clock=0,last=0,speed=1,raf=0;const assets={};
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const load=(name,src)=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{assets[name]=img;resolve();};img.onerror=()=>reject(Error('Không tải được '+src));img.src=src;});
 function rect(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();}}
 function text(str,x,y,size,color='#fff9ed',weight=800,align='center'){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(str,x,y);}
 function star(x,y,r,color,rot=0,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rot);ctx.beginPath();for(let i=0;i<10;i++){const a=-PI/2+i*PI/5,rr=i%2?r*.44:r;i?ctx.lineTo(Math.cos(a)*rr,Math.sin(a)*rr):ctx.moveTo(Math.cos(a)*rr,Math.sin(a)*rr);}ctx.closePath();ctx.fillStyle=color;ctx.fill();ctx.restore();}
 function shadow(x,y,w,alpha=.2){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#16392a';ctx.beginPath();ctx.ellipse(x,y,w,13,0,0,2*PI);ctx.fill();ctx.restore();}
 function pose(index,x,feet,size=1,alpha=1,rotation=0){const f=window.ANIMATION_POSES.frames[index],s=1.16*size;ctx.save();ctx.translate(x,feet);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.drawImage(assets.actor,f.left,f.top,f.width,f.height,-f.width*s/2,-f.height*s,f.width*s,f.height*s);ctx.restore();}
 function bubble(x,y,r,alpha=1){ctx.save();ctx.globalAlpha*=alpha;const g=ctx.createRadialGradient(x-r*.35,y-r*.4,1,x,y,r);g.addColorStop(0,'#f1ffffc0');g.addColorStop(.65,'#7ddfe87a');g.addColorStop(1,'#369bcaaa');ctx.fillStyle=g;ctx.strokeStyle='#d7fbff';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,Math.max(.1,r),0,2*PI);ctx.fill();ctx.stroke();ctx.lineWidth=4;ctx.beginPath();ctx.arc(x,y,r*.64,PI*1.14,PI*1.48);ctx.stroke();ctx.restore();}
 function ink(t,x,y){if(t<.35||t>1.45)return;const u=clamp((t-.35)/1.1),a=Math.sin(PI*u)*.85;ctx.save();ctx.globalAlpha=a;for(let i=0;i<9;i++){const angle=i*2.4+u*.5,r=75+u*112,px=x+Math.cos(angle)*r*.52,py=y+Math.sin(angle)*r*.42;const g=ctx.createRadialGradient(px,py,0,px,py,r);g.addColorStop(0,'#655085e8');g.addColorStop(.64,'#8063a9b0');g.addColorStop(1,'#8063a900');ctx.fillStyle=g;ctx.beginPath();ctx.arc(px,py,r,0,2*PI);ctx.fill();}ctx.restore();}
 function opponent(t,impact=1.75){const u=clamp((t-impact)/.3),x=1005+18*Math.sin(u*PI),feet=588-10*Math.sin(u*PI);shadow(x,591,90,.18);ctx.save();ctx.translate(x,feet);ctx.rotate(u*.05);const img=assets.opponent;ctx.drawImage(img,img.width/2,0,img.width/2,img.height,-164,-328,328,328);ctx.restore();if(u>0&&u<1)for(let i=0;i<6;i++){const a=i*2*PI/6+u;star(x+Math.cos(a)*u*100,feet-145+Math.sin(a)*u*85,9,'#ffe0a2',a,1-u);}}
 function sparkle(t,x,y,start=1.75){if(t<start||t>start+.65)return;const u=(t-start)/.65;ctx.save();ctx.globalAlpha=1-u;ctx.strokeStyle='#b0f1f5';ctx.lineWidth=6*(1-u)+1;ctx.beginPath();ctx.ellipse(x,y,25+u*170,20+u*135,0,0,PI*2);ctx.stroke();ctx.restore();for(let i=0;i<24;i++){const a=i*PI*2/24;star(x+Math.cos(a)*(24+u*180),y+Math.sin(a)*(20+u*130),5+(1-u)*8,i%2?'#fff5d5':'#bdeef3',a,1-u);}}
 function magicArms(t){if(t<.95||t>=1.9)return 0;const appear=smooth((t-.95)/.18),vanish=1-smooth((t-1.75)/.15),u=clamp((t-1.15)/.6),collapse=smooth(u);const cx=1000,cy=430;
  for(let i=0;i<8;i++){const a=i*PI/4,r=158,rootX=cx+Math.cos(a)*r,rootY=cy+Math.sin(a)*r*.78,tipX=cx+Math.cos(a)*(r-57),tipY=cy+Math.sin(a)*(r-57)*.78;ctx.save();ctx.globalAlpha=appear*vanish;ctx.lineCap='round';ctx.lineWidth=24;ctx.strokeStyle='#b08bc7';ctx.beginPath();ctx.moveTo(rootX,rootY);ctx.quadraticCurveTo(rootX-Math.sin(a)*30,rootY+Math.cos(a)*26,tipX,tipY);ctx.stroke();ctx.lineWidth=9;ctx.strokeStyle='#d6b2e2';ctx.beginPath();ctx.moveTo(rootX-3,rootY-3);ctx.quadraticCurveTo(rootX-Math.sin(a)*25,rootY+Math.cos(a)*20,tipX,tipY-3);ctx.stroke();for(let j=0;j<3;j++){const q=.4+j*.2;ctx.fillStyle='#fff0c9';ctx.beginPath();ctx.arc(mix(rootX,tipX,q),mix(rootY,tipY,q)+5,4,0,PI*2);ctx.fill();}ctx.restore();bubble(mix(tipX,cx,collapse),mix(tipY,cy,collapse),22-5*collapse,appear*vanish);}
  return 8;
 }
 function banner(t){if(mode!=='ultimate'||t<.65||t>1.56)return;const a=smooth((t-.65)/.12)*(1-smooth((t-1.4)/.16));ctx.save();ctx.globalAlpha=a;rect(243,159,794,90,27,'#233e36f5','#ffbe73');text('TÁM TAY ẢO THUẬT',640,206,45);star(288,205,18,'#ffce8d');star(992,205,18,'#ffce8d');ctx.restore();}
 function confetti(t){if(t<1.9)return;const u=t-1.9;for(let i=0;i<42;i++){const a=i*2.399,delay=i%5*.02,p=Math.max(0,u-delay),v=140+(i*47)%240,x=600+Math.cos(a)*v*p,y=410+Math.sin(a)*v*p+110*p*p;star(x,y,4+i%4,['#ffd49b','#b9de9f','#fff4ce','#d6b7e4'][i%4],p*3,clamp(1-(p-.65)/.5));}}
 function draw(t){t=clamp(t,0,3);ctx.drawImage(assets.bg,0,0,W,H);const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#10372d9c');shade.addColorStop(.55,'#10372d00');shade.addColorStop(1,'#10372d40');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  let index=0,x=285,feet=590,alpha=1,rotation=0,phase='',spheres=0;
  if(mode==='ultimate'){
   opponent(t);index=t<.65?Math.min(3,Math.floor(t/.65*4)):t<1.9?4+Math.min(3,Math.floor((t-.65)/1.25*4)):12+Math.min(1,Math.floor((t-1.9)/.55));
   alpha=t<.65?1:t<.95?1-smooth((t-.65)/.3):t<1.9?0:smooth((t-1.9)/.18);
   if(t>=1.9){x=mix(285,610,smooth((t-1.9)/.28));feet-=34*Math.sin(clamp((t-1.9)/.7)*PI);}
   shadow(x,598,98,.18*alpha);pose(index,x,feet,1,alpha);ink(t,285,451);spheres=magicArms(t);sparkle(t,1000,430);confetti(t);
   phase=t<.95?'LẤY ĐÀ':t<1.9?'ĐÒN QUYẾT ĐỊNH':'CHIẾN THẮNG';
   if(t>=1.9){ctx.save();ctx.globalAlpha=smooth((t-1.9)/.18);text('CHIẾN THẮNG!',640,190,58);text('Tám tay cùng gieo niềm vui',640,243,24,'#ffe3ad');ctx.restore();}
  }else if(mode==='attack'){
   opponent(t,1.25);index=t<.35?8:t<1.45?9:0;x+=Math.sin(clamp(t/1.45)*PI)*45;rotation=-.04*Math.sin(clamp(t/1.45)*PI);shadow(x,598,98);pose(index,x,feet,1,1,rotation);
   if(t>=.55&&t<1.3){const u=clamp((t-.55)/.7);bubble(mix(425,1000,smooth(u)),mix(450,430,u)-55*Math.sin(u*PI),30,1-smooth((t-1.25)/.05));spheres=1;}sparkle(t,1000,430,1.25);phase=t<.55?'LẤY ĐÀ':t<1.45?'TUNG BÓNG NƯỚC':'SẴN SÀNG';
   text('Bóng nước tinh nghịch',640,203,43);
  }else if(mode==='hit'){
   opponent(0,4);index=t<.4?0:t<.95?10:t<1.7?11:0;const u=clamp((t-.4)/1.3);x-=28*Math.sin(u*PI);rotation=.07*Math.sin(u*PI);shadow(x,598,98);pose(index,x,feet,1,1,rotation);
   if(t>.1&&t<.5){const u=clamp((t-.1)/.4);bubble(mix(900,345,u),445,24,1);}sparkle(t,320,450,.48);phase=t<.4?'CHUẨN BỊ':t<1.7?'CHỊU ĐÒN':'BÌNH TĨNH TRỞ LẠI';text('Hít thở, mình tiếp tục nào!',640,203,43);
  }else{
   x=640;feet=602+6*smooth(t/1.5);index=t<.6?14:15;shadow(x,615,104);pose(index,x,feet,1.15);phase=t<.6?'BUỒN MỘT CHÚT':'THỬ LẠI NHÉ!';text('Mỗi lần thử, mình lại tiến bộ',640,194,43);text('Bạch tuộc nghỉ một chút rồi chơi tiếp nhé.',640,246,23,'#ffe3ad');
  }
  banner(t);text('5BMath',45,37,24,'#fff5d9',800,'left');text('BẠCH TUỘC',1235,37,17,'#e8f1db',800,'right');
  rect(406,650,468,40,20,'#193f33df');text(phase,640,671,16);
  document.getElementById('seek').value=String(t);document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  const state={time:t,t,mode,phase,pose:index,actorAlpha:alpha,spheres,arms:mode==='ultimate'&&t>=.95&&t<1.9?8:0,nameVisible:mode==='ultimate'&&t>=.65&&t<=1.56,attackStarted:t>=.95,impact:t>=1.75,victory:mode==='ultimate'&&t>=1.9,playing};window.animationDemo.state=state;return state;
 }
 function pause(){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function setMode(value){if(!labels[value])throw Error('Trạng thái không hợp lệ');pause();mode=value;clock=0;document.getElementById('mode').value=mode;document.querySelector('h1').textContent=labels[mode];document.title='Bạch tuộc · '+labels[mode]+' · 5BMath';draw(0);return mode;}
 const ready=Promise.all([load('actor',C.webpFile),load('bg',C.backgroundFile),load('opponent',C.opponentFile)]).then(()=>{setMode(mode);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,play,setMode,duration:DURATION,inspect:()=>({mode,clock,playing,raf:!!raf,speed,reducedMotion:reduced.matches})};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);
 document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};document.getElementById('speed').onchange=e=>speed=Number(e.target.value);
 document.getElementById('mode').value=mode;document.getElementById('mode').onchange=e=>{setMode(e.target.value);if(!reduced.matches)play(true);};
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{if(reduced.matches)pause();});
 ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
