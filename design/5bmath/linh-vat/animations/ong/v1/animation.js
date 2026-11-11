/* Ong v1: shared Canvas renderer with the real game, WebP only. */
(() => {
 'use strict';
 const C=window.ANIMATION_CONFIG, api=window.ArenaBeeAnimation;
 const canvas=document.getElementById('stage'),ctx=canvas.getContext('2d',{alpha:false});
 const W=1280,H=720,D=3,clamp=v=>Math.max(0,Math.min(1,v));
 let mode='ultimate',clock=0,speed=1,playing=false,raf=0,last=0,bg,fox;
 document.title='Ong · Lục Giác Hoàng Kim';
 document.querySelector('h1').textContent=C.ultimateName;
 document.querySelector('header p').textContent='Ong · Đàn ong → tổ lục giác → giọt mật';
 document.querySelector('.note').textContent='Canvas + WebP dùng chung với game. Chọn trạng thái để xem bốn animation. Chưa có âm thanh riêng cho Ong.';
 document.querySelector('.beats').innerHTML='<div class="beat"><strong>0–0,95 s · Gọi đàn</strong>Ong vo ve, lục giác hiện dần; tên chiêu từ 0,65 giây.</div><div class="beat"><strong>0,95–1,90 s · Kết tổ</strong>Đàn ong khép các ô lục giác quanh Cáo Nâu; bung mật lúc 1,75 giây.</div><div class="beat"><strong>1,90–3,00 s · Ăn mừng</strong>Ong lượn vui, giọt mật và sao tan dần.</div>';
 const selector=document.createElement('select');selector.id='mode';selector.setAttribute('aria-label','Trạng thái Ong');
 for(const [value,label] of [['ultimate','Chiêu cuối'],['attack','Tấn công'],['hit','Chịu đòn'],['lose','Buồn khi thua']]){const option=document.createElement('option');option.value=value;option.textContent=label;selector.append(option);}
 document.querySelector('.controls').prepend(selector);
 function load(url){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error('Không tải được '+url));img.src=url;});}
 function text(str,x,y,size=28,color='#fff9ed'){ctx.font=`800 ${size}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(str,x,y);}
 function foxAt(t){const p=mode==='ultimate'?clamp((t-1.75)/.3):mode==='attack'?clamp((t-.45)/.4):0;ctx.save();ctx.translate(990+20*Math.sin(p*Math.PI),463-15*Math.sin(p*Math.PI));ctx.rotate(p*.06);ctx.drawImage(fox,fox.width/2,0,fox.width/2,fox.height,-170,-170,340,340);ctx.restore();}
 function draw(t){
  clock=Math.max(0,Math.min(D,t));ctx.drawImage(bg,0,0,W,H);
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'#102e24bb');shade.addColorStop(.5,'#102e2420');shade.addColorStop(1,'#102e2450');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  text('5BMath',106,42,27);text('ONG · CANVAS + WEBP',1015,42,18);
  foxAt(clock);
  let state;
  if(mode==='ultimate'){
   state=api.renderUltimate(ctx,clock,W,H,{from:{x:295,y:470},to:{x:990,y:450},size:300,showName:true});
   state.victory=clock>=1.9;
   if(state.victory){text('CHIẾN THẮNG!',W/2,153,56,'#fff0bc');text(C.ultimateName,W/2,210,25,'#ffd27b');}
  }else{
   const duration={attack:.9,hit:1.1,lose:2.2}[mode],p=clamp(clock/duration),pose=api.sample(mode,Math.min(clock,duration));
   let x=330,y=464,rotation=0;
   if(mode==='attack'){x+=Math.sin(p*Math.PI)*230;y-=Math.sin(p*Math.PI)*28;rotation=-Math.sin(p*Math.PI)*.08;}
   if(mode==='hit'){x+=Math.sin(p*Math.PI*6)*(1-p)*14;rotation=Math.sin(p*Math.PI)*.08;}
   if(mode==='lose')y+=p*25;
   api.drawSprite(ctx,pose,x,y,330,{rotation});
   text({attack:'TẤN CÔNG',hit:'CHỊU ĐÒN',lose:'BUỒN KHI THUA'}[mode],W/2,172,43);
   if(mode==='lose')text('Lần sau mình cùng cố gắng nhé!',W/2,236,25,'#fff0bc');
   state={time:clock,pose,phase:mode,nameVisible:false,attackStarted:mode==='attack',victory:false};
  }
  const phase=mode==='ultimate'?(clock<.95?'GỌI ĐÀN':clock<1.9?'LỤC GIÁC KHÉP LẠI':'MẬT VÀ SAO'):({attack:'BAY TỚI → RA ĐÒN → HỒI TƯ THẾ',hit:'GIẬT MÌNH → LÙI LẠI → HỒI PHỤC',lose:'HẠ CÁNH → CÚI ĐẦU → GIỮ TƯ THẾ BUỒN'}[mode]);
  ctx.fillStyle='#153f31de';ctx.beginPath();ctx.roundRect(270,640,740,48,24);ctx.fill();text(phase,W/2,664,19);
  document.getElementById('seek').value=clock;document.getElementById('clock').textContent=clock.toFixed(2).replace('.',',')+' / 3,00 s';
  return {...state,t:clock,phase,mode};
 }
 function pause(){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;document.getElementById('pause').textContent='Tiếp tục';}
 function play(reset=false){if(reset)clock=0;playing=true;last=performance.now();document.getElementById('pause').textContent='Tạm dừng';if(!raf)raf=requestAnimationFrame(tick);}
 function tick(now){raf=0;if(!playing)return;clock=Math.min(3,clock+(now-last)/1000*speed);last=now;draw(clock);if(clock<3)raf=requestAnimationFrame(tick);else pause();}
 api.configure({asset:new URL(C.webpFile,location.href).href,frames:window.ANIMATION_POSES.frames});
 const ready=Promise.all([api.ready(),load(C.backgroundFile),load(C.opponentFile)]).then(([atlas,b,f])=>{if(!atlas)throw new Error('Thiếu WebP Ong');bg=b;fox=f;draw(0);if(!new URLSearchParams(location.search).has('export')&&!matchMedia('(prefers-reduced-motion: reduce)').matches)play(true);});
 function setMode(value){pause();mode=value;selector.value=value;draw(0);}
 window.animationDemo={ready,render:draw,pause,play,setMode,duration:D};
 document.getElementById('replay').onclick=()=>play(true);document.getElementById('pause').onclick=()=>playing?pause():play(clock>=3);
 document.getElementById('seek').oninput=e=>{pause();draw(Number(e.target.value));};document.getElementById('speed').onchange=e=>speed=Number(e.target.value);
 selector.onchange=e=>{setMode(e.target.value);play(true);};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
 ready.catch(error=>{document.querySelector('.note').textContent=error.message;console.error(error);});
})();
