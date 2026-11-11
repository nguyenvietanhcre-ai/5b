/* Sao biển / v1. Private authoring copy; Canvas uses WebP atlases only. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG, canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 if(!C)throw new Error('Thiếu cấu hình animation Sao biển.');
 const W=1280,H=720,DURATION=3,PI=Math.PI,TAU=PI*2;
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),mix=(a,b,u)=>a+(b-a)*u;
 const smooth=u=>{u=clamp(u);return u*u*(3-2*u);},out=u=>1-Math.pow(1-clamp(u),3);
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const labels={ultimate:C.ultimateName,attack:'Tấn công · Sóng sao',hit:'Chịu đòn · Lắc mình hồi phục',lose:'Thua cuộc · Buồn rồi cố gắng tiếp'};
 const initial=new URLSearchParams(location.search).get('mode');
 let mode=Object.hasOwn(labels,initial)?initial:'ultimate',playing=false,clock=0,last=0,speed=1,raf=0;
 const assets={};
 function load(name,src){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{assets[name]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được '+src));img.src=src;});}
 function rounded(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.stroke();}}
 function text(str,x,y,size,color,weight=800,align='center'){ctx.font=`${weight} ${size}px Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(str,x,y);}
 function star(x,y,r,color,rotation=0,alpha=1){ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.beginPath();for(let i=0;i<10;i++){const a=-PI/2+i*PI/5,rr=i%2?r*.43:r;i?ctx.lineTo(Math.cos(a)*rr,Math.sin(a)*rr):ctx.moveTo(Math.cos(a)*rr,Math.sin(a)*rr);}ctx.closePath();ctx.fillStyle=color;ctx.fill();ctx.restore();}
 function shadow(x,y,w,alpha=.18){ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='#183e35';ctx.beginPath();ctx.ellipse(x,y,w,12,0,0,TAU);ctx.fill();ctx.restore();}
 function sprite(atlas,index,x,y,height,alpha=1,rotation=0){const manifest=atlas==='actor'?window.ANIMATION_POSES:window.ANIMATION_REACTIONS,f=manifest.frames[index],width=height*f.width/f.height;ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.rotate(rotation);ctx.drawImage(assets[atlas],f.left,f.top,f.width,f.height,-width/2,-height/2,width,height);ctx.restore();}
 function orb(x,y,r,alpha=.6,color='#ffe8a4'){ctx.save();ctx.globalAlpha*=alpha;const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color);g.addColorStop(.32,color+'99');g.addColorStop(1,color+'00');ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);ctx.restore();}
 function opponent(t){let x=1000,y=585,rotation=0,alpha=1;const impact=mode==='ultimate'?clamp((t-1.75)/.22):mode==='attack'?clamp((t-.7)/.22):0;
  if(impact>0){x+=impact*26;y-=Math.sin(impact*PI)*20;rotation=impact*.08;}
  if(mode==='ultimate'&&t>1.9)alpha=1-.55*smooth((t-1.9)/.35);
  shadow(x,603,80,alpha*.17);ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha=alpha;const img=assets.opponent,sw=img.width/2;ctx.drawImage(img,sw,0,sw,img.height,-145,-290,290,290);ctx.restore();
 }
 function healthbar(x,name,pct,color,side){rounded(x,90,300,66,21,'#163f33ed','#d7e6bc70');text(name,x+20,111,21,'#fff9ed',800,'left');rounded(x+20,132,260,10,5,'#ffffff26');rounded(x+20,132,Math.max(1,260*clamp(pct)),10,5,color);text(side,x+280,110,12,'#d2e6c9',600,'right');}
 function banner(t){if(mode!=='ultimate'||t<.65||t>1.59)return;const a=out((t-.65)/.14)*(1-clamp((t-1.44)/.15));ctx.save();ctx.globalAlpha=a;rounded(251,172,778,91,28,'#153f31f5','#ffcc88');text(C.ultimateName.toLocaleUpperCase('vi-VN'),640,220,43,'#fff2ca');star(293,217,17,'#ffce84');star(987,217,17,'#ffce84');ctx.restore();}
 function charge(t){if(t>.98)return;const q=smooth(t/.95);for(let i=0;i<5;i++){const a=-PI/2+i*TAU/5;star(285+Math.cos(a)*(132-38*q),428+Math.sin(a)*(132-38*q),4+5*q,'#fff2bb',a,.2+.65*q);}orb(285,430,180,.06+.10*q);}
 function orbitPoints(t){const p=clamp((t-.95)/.6),spin=reduced.matches?0:TAU*.72*p;return Array.from({length:5},(_,i)=>{const a=-PI/2+i*TAU/5+spin;return {x:mix(285,1000,smooth(p))+Math.cos(a)*mix(115,155,p),y:mix(425,492,smooth(p))+Math.sin(a)*mix(100,82,p),angle:a};});}
 function clones(t){if(t<.48||t>1.9)return;const alpha=smooth((t-.48)/.18)*(1-smooth((t-1.73)/.17)),points=orbitPoints(t);
  for(const p of points){ctx.save();ctx.shadowBlur=18;ctx.shadowColor='#ffe9a9';orb(p.x,p.y,68,alpha*.14);sprite('actor',7,p.x,p.y,83,alpha*.74,p.angle*.03);ctx.restore();}
 }
 function pentagram(t){if(t<1.35||t>2.04)return;const q=smooth((t-1.35)/.24),fade=1-clamp((t-1.88)/.16);ctx.save();ctx.translate(1000,586);ctx.scale(1,.38);ctx.globalAlpha=fade;ctx.strokeStyle='#ffe7a0';ctx.lineWidth=5;ctx.shadowColor='#ffd275';ctx.shadowBlur=20;
  const points=Array.from({length:5},(_,i)=>{const a=-PI/2+i*TAU/5;return{x:Math.cos(a)*177,y:Math.sin(a)*177};});ctx.beginPath();ctx.ellipse(0,0,191,191,0,0,TAU);ctx.stroke();ctx.beginPath();const order=[0,2,4,1,3,0],segments=q*5;ctx.moveTo(points[0].x,points[0].y);for(let j=0;j<5;j++){const u=clamp(segments-j),a=points[order[j]],b=points[order[j+1]];ctx.lineTo(mix(a.x,b.x,u),mix(a.y,b.y,u));if(u<1)break;}ctx.stroke();ctx.restore();
 }
 function column(t){if(t<1.64||t>2.15)return;const growth=out((t-1.64)/.11),fade=1-clamp((t-1.87)/.28),height=360*growth;ctx.save();ctx.globalAlpha=fade*.75;const g=ctx.createLinearGradient(878,0,1122,0);g.addColorStop(0,'#ffe5a000');g.addColorStop(.28,'#ffe8aa65');g.addColorStop(.5,'#fff9dda8');g.addColorStop(.72,'#ffe8aa65');g.addColorStop(1,'#ffe5a000');ctx.fillStyle=g;ctx.fillRect(878,592-height,244,height);ctx.strokeStyle='#fff2c3';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(938,592);ctx.lineTo(938,592-height);ctx.moveTo(1062,592);ctx.lineTo(1062,592-height);ctx.stroke();ctx.restore();orb(1000,490,170,fade*.20);}
 function starburst(t){if(t<1.75)return;const p=t-1.75,fade=1-clamp((p-.50)/.65);for(let i=0;i<35;i++){const a=i*2.399963,v=90+(i*39)%180,delay=(i%5)*.018,u=Math.max(0,p-delay);star(1000+Math.cos(a)*v*u,458+Math.sin(a)*v*u+80*u*u,4+(i%4)*2,i%3?'#ffe19b':'#fff6d0',a+u*(i%2?2:-2),fade);}}
 function ultimate(t){charge(t);pentagram(t);opponent(t);clones(t);
  let index=0,height=285,x=285,y=445,rotation=0;
  if(t<.65){index=Math.min(2,Math.floor(t/.22));height*=1-.04*Math.sin(t/.65*PI);}
  else if(t<.95){index=3;height*=1+.035*smooth((t-.65)/.3);}
  else if(t<1.55){index=4+Math.min(3,Math.floor((t-.95)/.6*4));y-=22*smooth((t-.95)/.6);rotation=reduced.matches?0:.045*Math.sin((t-.95)*7);}
  else if(t<1.9){index=8+Math.min(3,Math.floor((t-1.55)/.35*4));y-=22;}
  else {const u=t-1.9;index=u<.18?12:u<.44?13:u<.72?14:15;rotation=reduced.matches?0:.10*Math.sin(clamp(u/.55)*TAU);y-=reduced.matches?0:24*Math.sin(clamp(u/.75)*PI);}
  shadow(x,603,92,.19);sprite('actor',index,x,y,height,1,rotation);column(t);starburst(t);
  if(t>=1.9){const fade=out((t-1.9)/.18);ctx.save();ctx.globalAlpha=fade;text('CHIẾN THẮNG!',640,209,57,'#fff3ca',900);text('Năm cánh nhỏ · Một ánh sáng lớn',640,260,23,'#ffe4a9',700);star(379,208,19,'#ffd487',-.15);star(901,208,19,'#ffd487',.15);ctx.restore();}
  return index;
 }
 function reaction(t){opponent(t);let index=12,x=285,y=445,rotation=0,height=285;
  if(mode==='attack'){const u=clamp((t-.15)/.7);index=t<.15?12:t<.85?Math.min(3,Math.floor(u*4)):12+Math.min(3,Math.floor((t-.85)/.55));x+=65*Math.sin(u*PI);rotation=reduced.matches?0:.16*Math.sin(u*PI);if(t>.43&&t<.93){const q=clamp((t-.43)/.5);for(let k=0;k<3;k++){const xx=mix(390,990,clamp(q-k*.07));star(xx,440,23-k*4,'#ffe3a3',q*TAU,.9-k*.22);}if(q>.53)orb(1000,450,100,.2*(1-q));}}
  if(mode==='hit'){const u=clamp((t-.2)/1.1);index=t<.2?12:t<1.3?4+Math.min(3,Math.floor(u*4)):12+Math.min(3,Math.floor((t-1.3)/.4));x-=34*Math.sin(u*PI);rotation=reduced.matches?0:-.10*Math.sin(u*PI*3)*(1-u);if(t>.2&&t<.9){const q=(t-.2)/.7;for(let i=0;i<3;i++)star(x+(i-1)*45,275+Math.sin(q*5+i)*8,9,'#fff0b5',q*2,1-q);}}
  if(mode==='lose'){const u=clamp(t/1.65);index=8+Math.min(3,Math.floor(u*4));y+=29*smooth(u);rotation=reduced.matches?0:-.025*Math.sin(u*PI);height*=1-.035*smooth(u);}
  shadow(x,603,90);sprite('reactions',index,x,y,height,1,rotation);
  const copy=mode==='attack'?'SÓNG SAO':mode==='hit'?'MÌNH VẪN ỔN!':'LẦN SAU MÌNH CÙNG CỐ GẮNG!';text(copy,640,220,mode==='lose'?37:49,'#fff2cf',900);if(mode==='lose')text('Buồn một chút, rồi thử lại nhé.',640,271,23,'#ffe5b1',600);
  return index;
 }
 function draw(t){t=clamp(t,0,DURATION);ctx.drawImage(assets.bg,0,0,W,H);const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#0c2c26a8');shade.addColorStop(.46,'#0c2c2600');shade.addColorStop(1,'#08261a24');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  const index=mode==='ultimate'?ultimate(t):reaction(t),victory=mode==='ultimate'&&t>=1.9;
  ctx.save();ctx.globalAlpha=mode==='ultimate'?1-clamp((t-1.9)/.2):1;const opponentHp=mode==='ultimate'?.16*(1-smooth((t-1.75)/.14)):mode==='attack'?.72-.12*smooth((t-.7)/.2):.72;const hp=mode==='hit'?.72-.12*smooth((t-.2)/.18):mode==='lose'?.13*(1-smooth(t/.4)):.72;healthbar(88,C.name,hp,'#a9dc8e','BẠN');healthbar(892,'Cáo Nâu',opponentHp,'#ffbe73','ĐỐI THỦ');ctx.restore();banner(t);
  text('5BMath',46,36,24,'#fff5d9',800,'left');text('ĐẤU TRÍ · SAO BIỂN',W-46,36,15,'#e8f1db',800,'right');
  const phase=mode==='ultimate'?(t<.95?'LẤY ĐÀ':t<1.9?'NGŨ TINH HỘI TỤ':'CHIẾN THẮNG'):mode==='attack'?'TẤN CÔNG':mode==='hit'?'CHỊU ĐÒN · HỒI PHỤC':'BUỒN KHI THUA CUỘC';rounded(430,650,420,40,20,'#153f31df');text(phase,640,671,15,'#fff3d2',800);
  document.getElementById('seek').value=t;document.getElementById('clock').textContent=t.toFixed(2).replace('.',',')+' / 3,00 s';
  return {time:t,t,mode,phase,pose:index,atlas:mode==='ultimate'?'ultimate':'reactions',nameVisible:mode==='ultimate'&&t>=.65&&t<=1.59,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory,cloneCount:mode==='ultimate'&&t>=.48&&t<=1.9?5:0};
 }
 function pause(){playing=false;if(raf){cancelAnimationFrame(raf);raf=0;}document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(DURATION,clock+Math.max(0,(now-last)/1000)*speed);last=now;draw(clock);if(clock<DURATION)raf=requestAnimationFrame(tick);else pause();}
 function setMode(next){if(!Object.hasOwn(labels,next))throw new Error('Trạng thái Sao biển không hợp lệ.');pause();mode=next;clock=0;document.getElementById('mode').value=mode;document.querySelector('h1').textContent=labels[mode];canvas.setAttribute('aria-label',labels[mode]+' của Sao biển.');draw(0);return mode;}
 const ready=Promise.all([load('actor',C.webpFile||C.poseFile),load('reactions',C.reactionsFile||'assets/reactions.webp'),load('bg',C.backgroundFile),load('opponent',C.opponentFile)]).then(()=>{if(!window.ANIMATION_POSES?.frames||!window.ANIMATION_REACTIONS?.frames)throw new Error('Thiếu metadata của hai atlas.');setMode(mode);if(!new URLSearchParams(location.search).has('export')&&!reduced.matches)play(true);});
 window.animationDemo={ready,render:draw,pause,duration:DURATION,play,setMode,get mode(){return mode;},get playing(){return playing;}};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=DURATION);document.getElementById('speed').onchange=e=>{speed=Number(e.target.value);};document.getElementById('mode').onchange=e=>{setMode(e.target.value);if(!reduced.matches)play(true);};document.getElementById('seek').oninput=e=>{pause();clock=Number(e.target.value);draw(clock);};
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});reduced.addEventListener('change',()=>{if(reduced.matches)pause();});
 ready.catch(e=>{document.querySelector('.note').textContent=e.message;console.error(e);});
})();
