/* 5BMath Gấu: draw only presentation; combat remains owned by LearningApp. */
(() => {
 'use strict';
 const base=new URL('.',document.currentScript.src),records=new Map(),images={};
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const durations={idle:0,attack:.9,hit:1,ultimate:3,win:1.8,defeat:2.2};
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v)),ease=u=>{u=clamp(u);return u*u*(3-2*u);};
 let loading;
 function ready(){return loading||(loading=Promise.all(['ultimate','reactions'].map(kind=>new Promise((resolve,reject)=>{
  const img=new Image();img.onload=()=>{images[kind]=img;resolve();};img.onerror=()=>reject(new Error('Không tải được ảnh Gấu: '+kind));img.src=new URL('arena-art/gau-'+kind+'.webp',base).href;
 }))));}
 function stateAt(mode,t){
  t=clamp(Number(t)||0,0,durations[mode]||0);
  let sheet='reactions',index=12,dx=0,dy=0,angle=0;
  if(mode==='ultimate'){
   sheet='ultimate';index=t<.18?0:t<.36?1:t<.52?2:t<.65?3:t<.77?4:t<.88?5:t<1.07?6:t<1.36?7:t<1.58?8:t<1.75?9:t<1.9?10:t<2.03?11:t<2.18?12:t<2.4?13:t<2.65?14:15;
   dy=t>=2.18&&t<2.65?-20*Math.sin((t-2.18)/.47*Math.PI):0;
  }else if(mode==='attack'){index=Math.min(3,Math.floor(t/.225));dx=34*Math.sin(clamp(t/.9)*Math.PI);}
  else if(mode==='hit'){index=4+Math.min(3,Math.floor(t/.25));dx=-20*Math.sin(t*Math.PI);angle=-.07*Math.sin(t*Math.PI);}
  else if(mode==='defeat')index=8+Math.min(3,Math.floor(t/.55));
  else if(mode==='win')index=t<.3?14:15;
  return {mode,time:t,sheet,index,dx,dy,angle,nameVisible:mode==='ultimate'&&t>=.65&&t<1.6,attackStarted:mode==='ultimate'&&t>=.95,impact:mode==='ultimate'&&t>=1.75,victory:mode==='ultimate'&&t>=1.9};
 }
 function paw(ctx,x,y,size,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.translate(x,y);ctx.scale(size/100,size/100);ctx.fillStyle='#e6bc91';ctx.beginPath();ctx.ellipse(0,12,29,23,0,0,Math.PI*2);ctx.fill();for(const [px,py]of[[-31,-10],[-12,-27],[12,-27],[31,-10]]){ctx.beginPath();ctx.ellipse(px,py,11,15,px/100,0,Math.PI*2);ctx.fill();}ctx.restore();}
 function star(ctx,x,y,r,alpha=1){ctx.save();ctx.globalAlpha*=alpha;ctx.fillStyle='#ffbe73';ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.4:r;i?ctx.lineTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr):ctx.moveTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr);}ctx.closePath();ctx.fill();ctx.restore();}
 function drawActor(canvas,mode,t){
  const s=stateAt(mode,t),ctx=canvas.getContext('2d'),atlas=window.BEAR_FRAMES?.[s.sheet];
  if(!atlas||!images[s.sheet])return s;
  const f=atlas.frames[s.index],scale=382/atlas.frames[0].height,w=f.width*scale,h=f.height*scale;
  ctx.clearRect(0,0,512,512);ctx.save();ctx.translate(256+s.dx,468+s.dy);ctx.rotate(s.angle);ctx.imageSmoothingQuality='high';ctx.drawImage(images[s.sheet],f.left,f.top,f.width,f.height,-w/2,-h,w,h);ctx.restore();
  if(mode==='attack'&&t>.3&&t<.72){ctx.save();ctx.globalAlpha=Math.sin((t-.3)/.42*Math.PI)*.75;ctx.strokeStyle='#ffbe73';ctx.lineWidth=8;ctx.lineCap='round';ctx.beginPath();ctx.arc(350,260,70,-1.2,1.1);ctx.stroke();ctx.restore();}
  if(mode==='hit'&&t<.7)for(let i=0;i<3;i++)star(ctx,160+i*85,60+Math.sin(i+t*6)*12,12,(1-t/.7)*.8);
  if(mode==='ultimate'&&t>1.55&&t<2){const u=(t-1.55)/.45;ctx.save();ctx.globalAlpha=1-u;ctx.strokeStyle='#ffbe73';ctx.lineWidth=7;ctx.beginPath();ctx.ellipse(256,468,45+130*u,12+24*u,0,0,Math.PI*2);ctx.stroke();ctx.restore();}
  if(mode==='win'||(mode==='ultimate'&&t>=1.9)){for(let i=0;i<5;i++)star(ctx,95+i*80,80+(i%2)*35,9,.8);}
  canvas.dataset.bearFrame=String(s.index);canvas.dataset.bearState=mode;return s;
 }
 function makeOverlay(record){
  const stage=record.canvas.closest('.battle-stage');if(!stage)return;
  const layer=document.createElement('canvas');layer.className='bear-ultimate-overlay';layer.setAttribute('aria-hidden','true');stage.append(layer);record.overlay=layer;
 }
 function drawOverlay(record,t){
  const layer=record.overlay;if(!layer)return;
  const stage=layer.parentElement,rect=stage.getBoundingClientRect(),scale=Math.min(devicePixelRatio||1,1.5),w=rect.width,h=rect.height;
  if(layer.width!==Math.round(w*scale)||layer.height!==Math.round(h*scale)){layer.width=Math.round(w*scale);layer.height=Math.round(h*scale);}
  const ctx=layer.getContext('2d');ctx.setTransform(scale,0,0,scale,0,0);ctx.clearRect(0,0,w,h);
  const actor=record.canvas.getBoundingClientRect(),fighter=record.canvas.closest('.fighter'),other=stage.querySelector(fighter?.id==='fighter-me'?'#fighter-opponent .pet-body':'#fighter-me .pet-body');
  if(!other)return;const target=other.getBoundingClientRect(),a={x:actor.x-rect.x+actor.width*.5,y:actor.y-rect.y+actor.height*.91},b={x:target.x-rect.x+target.width*.5,y:target.y-rect.y+target.height*.84};
  if(t>=.65&&t<1.6){ctx.save();ctx.globalAlpha=clamp((t-.65)/.15)*clamp((1.6-t)/.15);const size=Math.min(23,w*.042);ctx.font='800 '+size+'px Arial,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#203a32';ctx.beginPath();ctx.roundRect(w*.07,h*.42,w*.86,size*2.5,12);ctx.fill();ctx.fillStyle='#fff9ed';ctx.fillText('CHƯỞNG GẤU ĐẠI LỰC',w/2,h*.42+size*1.25,w*.8);ctx.restore();}
  if(t>=1.55&&t<2.12){const u=clamp((t-1.55)/.2),fade=1-clamp((t-1.85)/.27);for(let i=0;i<9;i++){
   const p=(i+1)/10,local=clamp((u-p*.73)*5),x=a.x+(b.x-a.x)*p,y=a.y+(b.y-a.y)*p;
   ctx.save();ctx.globalAlpha=local*fade;ctx.fillStyle=i%2?'#c69f7c':'#dfb98b';ctx.strokeStyle='#a57d5e';ctx.lineWidth=2;const rw=Math.max(8,w*.028),rh=(8+(i%3)*5)*local;ctx.beginPath();ctx.roundRect(x-rw,y-rh,rw*2,rh+7,7);ctx.fill();ctx.stroke();ctx.restore();
  }}
  if(t>=1.75&&t<2.25){const u=(t-1.75)/.5;paw(ctx,b.x,b.y-h*.07,Math.min(125,w*.22)*(1+u*.5),(1-u)*.85);for(let i=0;i<9;i++){const a=i*Math.PI*2/9;star(ctx,b.x+Math.cos(a)*u*w*.23,b.y-h*.1+Math.sin(a)*u*h*.17,4+3*(1-u),1-u);}}
 }
 function stop(record){if(record.raf)cancelAnimationFrame(record.raf);record.raf=0;record.overlay?.remove();record.overlay=null;}
 function play(canvas,mode='idle',options={}){
  if(!canvas||!Object.hasOwn(durations,mode))return;
  let r=records.get(canvas);if(!r){r={canvas,raf:0,version:0};records.set(canvas,r);
   const pet=canvas.closest('.battle-pet.gau');
   if(pet){r.observer=new MutationObserver(()=>{const mood=pet.dataset.mood||'idle',next=mood==='lose'?'defeat':mood;if(Object.hasOwn(durations,next)&&next!==r.mode&&!(next==='attack'&&r.mode==='ultimate'))play(canvas,next);});r.observer.observe(pet,{attributes:true,attributeFilter:['data-mood']});}
  }
  stop(r);r.version++;const version=r.version;r.mode=mode;r.options=options;canvas.dataset.mode=mode;
  ready().then(()=>{
   if(version!==r.version||!canvas.isConnected)return;
   canvas.closest('.battle-pet')?.classList.add('bear-ready');
   if(reduced.matches||document.hidden||mode==='idle'){drawActor(canvas,mode,mode==='idle'?0:durations[mode]);options.onFinish?.();return;}
   if(mode==='ultimate')makeOverlay(r);
   const start=performance.now();
   function tick(now){r.raf=0;if(version!==r.version||!canvas.isConnected||document.hidden){stop(r);return;}const t=Math.min(durations[mode],(now-start)/1000);drawActor(canvas,mode,t);drawOverlay(r,t);if(t<durations[mode])r.raf=requestAnimationFrame(tick);else{stop(r);options.onFinish?.();}}
   r.raf=requestAnimationFrame(tick);
  }).catch(error=>{canvas.closest('.battle-pet')?.classList.remove('bear-ready');canvas.dataset.bearError=error.message;console.error(error);});
 }
 const nodes=root=>[...(root.matches?.('canvas[data-bear]')?[root]:[]),...root.querySelectorAll('canvas[data-bear]')];
 function mount(root=document){for(const c of nodes(root))if(!records.has(c))play(c,c.dataset.mode||'idle');for(const [c,r]of records)if(!c.isConnected){r.version++;r.observer?.disconnect();stop(r);records.delete(c);}}
 function unmount(root=document){for(const c of nodes(root)){const r=records.get(c);if(r){r.version++;r.observer?.disconnect();stop(r);records.delete(c);}}}
 document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const r of records.values()){stop(r);if(images.ultimate)drawActor(r.canvas,r.mode,durations[r.mode]);}});
 reduced.addEventListener('change',()=>{if(reduced.matches)for(const r of records.values()){stop(r);if(images.ultimate)drawActor(r.canvas,r.mode,durations[r.mode]);}});
 window.BearAnimation={mount,unmount,play,ready,stateAt,render:(canvas,mode,t)=>drawActor(canvas,mode,t),inspect:()=>[...records.values()].map(r=>({connected:r.canvas.isConnected,mode:r.mode,active:Boolean(r.raf)}))};
})();
