/* 5BMath Voi: DOM-free Canvas/WebP renderer shared by review and arena. */
(() => {
 'use strict';
 const TAU=Math.PI*2,clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
 const smooth=v=>{v=clamp(v);return v*v*(3-2*v);};
 const durations=Object.freeze({idle:2.4,attack:.9,hurt:.65,defeat:3,victory:3,ultimate:3});
 const colors=['#ffad9e','#ffce7b','#fcf0a6','#a9dbb1','#8cdbe4','#b5b9ef'];
 function sample(state='idle',time=0){
  const t=Math.max(0,Number(time)||0);let pose=0,sheet='reactions',dx=0,dy=0,rotation=0,scaleX=1,scaleY=1;
  if(state==='ultimate'){
   sheet='poses';
   if(t<.65){pose=Math.min(3,Math.floor(t/.65*4));dy=.018*Math.sin(t/.65*Math.PI);}
   else if(t<.95){pose=4+Math.min(3,Math.floor((t-.65)/.3*4));scaleX=1.02;scaleY=.98;}
   else if(t<1.9){pose=8+Math.min(3,Math.floor((t-.95)/.95*4));dx=-.013*Math.sin(clamp((t-.95)/.15)*Math.PI/2);rotation=-.022;}
   else{pose=12+Math.min(3,Math.floor((t-1.9)/1.1*4));dy=-.06*Math.sin(clamp((t-1.94)/.67)*Math.PI);}
  }else if(state==='attack'){const u=clamp(t/.9);pose=4+Math.min(3,Math.floor(u*4));dx=.1*Math.sin(u*Math.PI);dy=-.018*Math.sin(u*Math.PI);rotation=-.035*Math.sin(u*Math.PI);}
  else if(state==='hurt'){const u=clamp(t/.65);pose=8+Math.min(3,Math.floor(u*4));dx=-.055*Math.sin(u*Math.PI)+Math.sin(t*58)*.008*(1-u);rotation=.055*Math.sin(u*Math.PI);scaleY=1-.025*Math.sin(u*Math.PI);}
  else if(state==='defeat'){const u=clamp(t/3);pose=12+Math.min(3,Math.floor(u*4));dy=.025*smooth(u);rotation=-.018*smooth(u);}
  else if(state==='victory'){sheet='poses';pose=12+Math.min(3,Math.floor(clamp(t/.9)*4));dy=-.055*Math.sin(clamp(t/.8)*Math.PI);}
  else{pose=Math.floor((t%2.4)/2.4*4);dy=-.006*Math.sin(t*TAU/2.4);scaleY=1+.006*Math.sin(t*TAU/2.4);}
  return{state,time:t,sheet,pose,dx,dy,rotation,scaleX,scaleY};
 }
 function effectSample(state,time){const t=Math.max(0,Number(time)||0);return{bubbleLift:state==='ultimate'?smooth((t-1.34)/.42)*(1-smooth((t-1.9)/.18)):0,bubbleVisible:state==='ultimate'&&t>=1.28&&t<1.98,impact:state==='ultimate'?t>=1.75:state==='attack'&&t>=.4,nameVisible:state==='ultimate'&&t>=.65&&t<=1.62,attackStarted:state==='ultimate'&&t>=.95,victory:state==='ultimate'&&t>=1.9};}
 function star(ctx,x,y,r,color,rotation=0){ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.43:r,xx=Math.cos(a)*rr,yy=Math.sin(a)*rr;i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy);}ctx.closePath();ctx.fillStyle=color;ctx.fill();ctx.restore();}
 function droplet(ctx,x,y,size,color,rotation=0){ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(0,-size);ctx.bezierCurveTo(size,0,size*.7,size,0,size);ctx.bezierCurveTo(-size*.7,size,-size,0,0,-size);ctx.fill();ctx.restore();}
 function bubble(ctx,x,y,radius,alpha){
  ctx.save();ctx.globalAlpha*=alpha;const fill=ctx.createRadialGradient(x-radius*.35,y-radius*.38,0,x,y,radius);fill.addColorStop(0,'#f9fffe05');fill.addColorStop(.66,'#8bdde916');fill.addColorStop(.94,'#b5eafa40');fill.addColorStop(1,'#ffffffa0');ctx.fillStyle=fill;ctx.beginPath();ctx.arc(x,y,radius,0,TAU);ctx.fill();
  colors.forEach((color,i)=>{ctx.strokeStyle=color;ctx.lineWidth=Math.max(1.5,radius*.02);ctx.beginPath();ctx.arc(x,y,radius-1,i*TAU/6-.05,(i+1)*TAU/6+.05);ctx.stroke();});
  ctx.strokeStyle='#ffffffdd';ctx.lineWidth=radius*.035;ctx.lineCap='round';ctx.beginPath();ctx.arc(x,y,radius*.85,-2.6,-1.95);ctx.stroke();ctx.beginPath();ctx.arc(x,y,radius*.91,.45,.72);ctx.stroke();ctx.restore();
 }
 function create({posesImage,reactionsImage,posesFrames,reactionsFrames}){
  const frameSets={poses:posesFrames,reactions:reactionsFrames},images={poses:posesImage,reactions:reactionsImage||posesImage},maximum={};
  for(const key of ['poses','reactions']){if(!Array.isArray(frameSets[key])||frameSets[key].length!==16)throw new Error('Voi cần đủ 16 tư thế cho '+key);maximum[key]=Math.max(...frameSets[key].map(f=>f.height));}
  const ultimateTips=[[.30,.23],[.82,.85],[.78,.93],[.67,.71],[.67,.48],[.91,.20],[.94,.15],[.96,.16],[.96,.16],[.95,.08],[.95,.18],[.96,.23],[.95,.22],[.94,.07],[.96,.09],[.89,.12]];
  function trunkTip({state='idle',time=0,x=0,feet=0,height=220,facing=1}={}){
   const s=sample(state,time),f=frameSets[s.sheet][s.pose],scale=height/maximum[s.sheet],tip=s.sheet==='poses'?ultimateTips[s.pose]:[.9,.33];
   const lx=(tip[0]-.5)*f.width*scale*s.scaleX,ly=(tip[1]-1)*f.height*scale*s.scaleY,cs=Math.cos(s.rotation),sn=Math.sin(s.rotation),dir=facing<0?-1:1;
   return{x:x+s.dx*height*facing+dir*(lx*cs-ly*sn),y:feet+s.dy*height+lx*sn+ly*cs};
  }
  function drawActor(ctx,{state='idle',time=0,x=0,feet=0,height=220,facing=1,alpha=1}={}){
   const s=sample(state,time),f=frameSets[s.sheet][s.pose],scale=height/maximum[s.sheet],w=f.width*scale,h=f.height*scale;
   ctx.save();ctx.globalAlpha*=clamp(alpha);ctx.translate(x+s.dx*height*facing,feet+s.dy*height);ctx.scale(facing<0?-1:1,1);ctx.rotate(s.rotation);ctx.scale(s.scaleX,s.scaleY);ctx.drawImage(images[s.sheet],f.left,f.top,f.width,f.height,-w/2,-h,w,h);
   if(state==='hurt'&&time<.62){ctx.globalAlpha*=1-clamp(time/.65);for(let i=0;i<3;i++){const a=time*5+i*TAU/3;star(ctx,Math.cos(a)*height*.25,-height*.92+Math.sin(a)*height*.06,height*.025,'#ffdb8c',a);}}
   if(state==='defeat'&&time>.8){const u=((time-.8)%1.15)/1.15;ctx.globalAlpha*=Math.sin(u*Math.PI)*.8;droplet(ctx,height*.12,-height*.64+u*height*.15,height*.014,'#9fdaec');}
   ctx.restore();return{...s,trunkTip:trunkTip({state,time,x,feet,height,facing})};
  }
  function drawEffect(ctx,{state,time=0,from,to,targetHeight,intensity=1,maxLift,bubbleRadius}={}){
   if(!from||!to)return effectSample(state,time);
   const dx=to.x-from.x,dy=to.y-from.y,length=Math.max(1,Math.hypot(dx,dy)),th=targetHeight||Math.min(260,Math.max(70,length*.4)),t=Math.max(0,time),e=effectSample(state,t),unit=th/230;
   const peakLift=Number.isFinite(maxLift)?Math.min(th*.28,Math.max(0,maxLift)):th*.28;
   const radiusLimit=Number.isFinite(bubbleRadius)?Math.max(1,bubbleRadius):Infinity;
   ctx.save();ctx.globalAlpha*=clamp(intensity);
   if(state==='ultimate'){
    if(t<.95){const charge=smooth(t/.95),r=(10+16*charge)*unit;ctx.save();ctx.globalAlpha*=.4+charge*.5;bubble(ctx,from.x,from.y,r,.7);for(let i=0;i<8;i++){const a=i*TAU/8+t*4,rr=(58-30*charge)*unit;droplet(ctx,from.x+Math.cos(a)*rr,from.y+Math.sin(a)*rr*.6,(2+charge*2)*unit,'#b1ecf4',a);}ctx.restore();}
    if(t>=.95&&t<1.94){
     const reach=smooth((t-.95)/.39),fade=1-smooth((t-1.79)/.15),angle=Math.atan2(dy,dx);
     ctx.save();ctx.translate(from.x,from.y);ctx.rotate(angle);ctx.lineCap='round';
     const jetPath=(offset=0,wave=0)=>{ctx.beginPath();for(let i=0;i<=60;i++){const u=i/60*reach,x=u*length,y=-Math.sin(Math.PI*u)*Math.min(85*unit,length*.15)+offset+Math.sin(u*TAU*4-t*18)*wave*u;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}};
     ctx.globalAlpha*=fade;ctx.strokeStyle='#5cbcd330';ctx.lineWidth=42*unit;jetPath();ctx.stroke();const gradient=ctx.createLinearGradient(0,0,length,0);gradient.addColorStop(0,'#dcfbfd');gradient.addColorStop(.35,'#7ad4e5');gradient.addColorStop(.8,'#a8e9ef');gradient.addColorStop(1,'#eaffff');ctx.strokeStyle=gradient;ctx.lineWidth=19*unit;jetPath();ctx.stroke();
     for(let i=0;i<3;i++){ctx.strokeStyle=i===1?'#ffffffc0':'#58bddbaf';ctx.lineWidth=(i===1?3:4)*unit;jetPath((i-1)*5*unit,8*unit);ctx.stroke();}
     for(let i=0;i<15;i++){const u=((i*.137+t*1.17)%1)*reach,x=u*length,y=-Math.sin(Math.PI*u)*Math.min(85*unit,length*.15)+Math.sin(i*3+t*9)*20*unit;droplet(ctx,x,y,(2+i%3)*unit,'#d5faffc0',.8);}ctx.restore();
     const build=smooth((t-1.17)/.37),tw=th*.42*build,hh=th*.92*build;ctx.save();ctx.translate(to.x,to.y+th*.43);ctx.globalAlpha*=fade*.88;
     const water=ctx.createLinearGradient(0,-hh,0,0);water.addColorStop(0,'#c9f8ff22');water.addColorStop(.5,'#8bdbea55');water.addColorStop(1,'#65bfdc11');ctx.beginPath();ctx.moveTo(-tw,-hh);ctx.quadraticCurveTo(-tw*.1,-hh*.3,-tw*.15,0);ctx.quadraticCurveTo(0,12*unit,tw*.15,0);ctx.quadraticCurveTo(tw*.1,-hh*.3,tw,-hh);ctx.closePath();ctx.fillStyle=water;ctx.fill();
     for(let i=0;i<7;i++){const v=((i/7+t*.92)%1),y=-v*hh,rx=tw*(.15+v*.85);ctx.strokeStyle=i%2?'#efffffba':'#7fd9ece0';ctx.lineWidth=(3+v*2)*unit;ctx.beginPath();ctx.ellipse(Math.sin(t*9+v*5)*6*unit,y,rx,Math.max(2,rx*.2),-.08,0,TAU);ctx.stroke();}ctx.restore();
    }
    if(e.bubbleVisible){const grow=smooth((t-1.28)/.19),fade=1-smooth((t-1.9)/.08);bubble(ctx,to.x,to.y-peakLift*e.bubbleLift,Math.min(radiusLimit,th*.55*(.65+.35*grow)),grow*fade);}
    if(t>=1.9){
     const u=t-1.9,burst=clamp(u/.28),fade=1-smooth((u-.6)/.5),originY=to.y-peakLift;ctx.save();ctx.globalAlpha*=fade;
     if(u<.3){ctx.save();ctx.strokeStyle='#e8ffff';ctx.lineWidth=3*unit;ctx.globalAlpha*=1-burst;ctx.beginPath();ctx.arc(to.x,originY,Math.min(radiusLimit,th*(.55+burst*.25)),0,TAU);ctx.stroke();ctx.restore();}
     for(let i=0;i<30;i++){const a=i*TAU/30+.3,speed=(82+i%7*18)*unit,x=to.x+Math.cos(a)*speed*u,y=originY+Math.sin(a)*speed*u+100*unit*u*u;droplet(ctx,x,y,(3+i%3)*unit,colors[i%colors.length],Math.cos(a)*.55);}
     ctx.globalAlpha*=smooth(u/.2)*(1-smooth((u-.72)/.35))*.8;colors.forEach((color,i)=>{ctx.strokeStyle=color;ctx.lineWidth=6*unit;ctx.beginPath();ctx.arc(to.x,originY+th*.2,Math.min(radiusLimit,th*(.77+i*.027)),Math.PI*1.1,Math.PI*1.9);ctx.stroke();});ctx.restore();
    }
   }else if(state==='attack'&&t>=.18&&t<=.74){
    const u=clamp((t-.18)/.45),x=from.x+dx*smooth(u),y=from.y+dy*smooth(u)-Math.sin(u*Math.PI)*th*.12;ctx.save();ctx.globalAlpha*=Math.sin(u*Math.PI);
    for(let i=2;i>=0;i--)bubble(ctx,x-dx/length*i*12*unit,y-dy/length*i*12*unit,(13-i*2)*unit,.8-i*.18);
    if(u>.63)for(let i=0;i<7;i++){const a=i*TAU/7,r=th*.17*(u-.63)/.37;droplet(ctx,to.x+Math.cos(a)*r,to.y+Math.sin(a)*r,4*unit,'#bfedf1',a);}ctx.restore();
   }
   ctx.restore();return e;
  }
  return Object.freeze({drawActor,drawEffect,trunkTip,duration:state=>durations[state]||durations.idle,sample,effectSample});
 }
 window.VoiRenderer=Object.freeze({create,sample,effectSample,duration:state=>durations[state]||durations.idle});
})();
