/* 5BMath Bướm. Pure Canvas drawing shared by the game and the review demo. */
(() => {
    'use strict';
    const TAU = Math.PI * 2;
    const colours = ['#FFBE73','#F59E96','#C7A7E8','#8BC9C7','#AED58E','#FFE2A1'];
    const clamp = value => Math.max(0, Math.min(1, value));
    const smooth = value => { value = clamp(value); return value * value * (3 - 2 * value); };
    const mix = (a,b,u) => a + (b-a)*u;
    function state(t) {
        return { nameVisible:t >= .65, attackStarted:t >= .95, victory:t >= 1.9 };
    }
    function pose(ctx,image,index,x,y,size,rotation=0,flip=false) {
        index = Math.max(0,Math.min(15,Math.floor(index)));
        const col=index%4,row=Math.floor(index/4);
        const left=Math.round(col*image.width/4),top=Math.round(row*image.height/4);
        const width=Math.round((col+1)*image.width/4)-left,height=Math.round((row+1)*image.height/4)-top;
        ctx.save(); ctx.translate(x,y);ctx.rotate(rotation);if(flip)ctx.scale(-1,1);
        ctx.drawImage(image,left,top,width,height,-size/2,-size/2,size,size);ctx.restore();
    }
    function butterfly(ctx,x,y,size,colour,rotation=0,spread=1,alpha=1) {
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.scale(size/20,size/20);ctx.globalAlpha*=alpha;
        ctx.fillStyle=colour;
        for(const side of [-1,1]){
            ctx.beginPath();ctx.ellipse(side*5*spread,-3,5.7*spread,7,-side*.46,0,TAU);ctx.fill();
            ctx.beginPath();ctx.ellipse(side*4*spread,5,4.3*spread,4.8,side*.5,0,TAU);ctx.fill();
        }
        ctx.fillStyle='#FFF9ED';ctx.beginPath();ctx.ellipse(0,1,1.2,6,0,0,TAU);ctx.fill();
        ctx.restore();
    }
    function star(ctx,x,y,size,colour,alpha=1,rotation=0) {
        ctx.save();ctx.translate(x,y);ctx.rotate(rotation);ctx.globalAlpha*=alpha;ctx.fillStyle=colour;ctx.beginPath();
        for(let j=0;j<10;j++){
            const a=j*Math.PI/5-Math.PI/2,r=j%2?size*.42:size;
            if(j)ctx.lineTo(Math.cos(a)*r,Math.sin(a)*r);else ctx.moveTo(Math.cos(a)*r,Math.sin(a)*r);
        }
        ctx.closePath();ctx.fill();ctx.restore();
    }
    function title(ctx,t,width,height,options) {
        if(t<.65||t>1.74||options.title===false)return;
        const alpha=smooth((t-.65)/.12)*(1-smooth((t-1.62)/.12));
        const font=Math.max(15,Math.min(width*.04,45)),label='VŨ ĐIỆU NGÀN CÁNH';
        ctx.save();ctx.globalAlpha*=alpha;ctx.font=`800 ${font}px Arial,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
        const boxWidth=Math.min(width*.88,ctx.measureText(label).width+font*2),boxHeight=font*1.9;
        const x=width/2,y=height*.17;
        ctx.fillStyle='#1F6248';ctx.strokeStyle='#FFBE73';ctx.lineWidth=2;ctx.beginPath();
        ctx.roundRect(x-boxWidth/2,y-boxHeight/2,boxWidth,boxHeight,boxHeight*.3);ctx.fill();ctx.stroke();
        ctx.fillStyle='#FFF9ED';ctx.fillText(label,x,y,boxWidth-font*.6);ctx.restore();
    }
    function effects(ctx,t,source,target,options={}) {
        const w=ctx.canvas.width,h=ctx.canvas.height,unit=Math.min(w,h),right=target.x>=source.x?1:-1;
        const cx=mix(source.x,target.x,.52),cy=Math.max(h*.37,Math.min(source.y,target.y)-unit*.12);
        const size=unit*.23,fade=1-smooth((t-2.32)/.5);
        const count=options.lowQuality?48:128;
        const reduced=options.reducedMotion===true;
        ctx.save();
        if(t<1.78){
            const charge=smooth(t/.65),merge=smooth((t-.95)/.5),open=1+.45*smooth((t-1.45)/.3);
            // A softly outlined four-wing silhouette makes the assembled swarm legible.
            if(merge>.05){
                ctx.save();ctx.lineWidth=unit*.0025;
                for(const side of [-1,1])for(const lower of [false,true]){
                    ctx.globalAlpha=merge*(1-smooth((t-1.7)/.08));
                    ctx.fillStyle=lower?'#AED58E19':'#FFBE731d';ctx.strokeStyle=lower?'#AED58E7a':'#FFE2A18a';
                    ctx.beginPath();ctx.ellipse(cx+side*size*(lower?.49:.69)*open,cy+size*(lower?.55:-.43),size*(lower?.47:.66)*open,size*(lower?.48:.77),0,0,TAU);ctx.fill();ctx.stroke();
                }
                ctx.restore();
            }
            // Four lobes made from tiny butterfly silhouettes, not another animal's attack.
            for(let i=0;i<count;i++){
                const n=i/count,side=i%2?-1:1,lower=i%4>=2,a=(Math.floor(i/4)*2.399963229728653);
                const ring=.35+.65*((i*37)%101)/100;
                const lobeX=side*size*(lower?.49:.69)*open,lobeY=size*(lower?.55:-.43);
                const wingX=cx+lobeX+Math.cos(a)*size*(lower?.47:.66)*ring*open;
                const wingY=cy+lobeY+Math.sin(a)*size*(lower?.48:.77)*ring;
                const orbit=a+(reduced?0:t*3.8),travel=smooth((t-.28-n*.26)/.65);
                const swirlX=mix(source.x,target.x,travel)+Math.cos(orbit)*unit*(.06+.12*travel);
                const swirlY=mix(source.y,target.y-unit*.12,travel)+Math.sin(orbit)*unit*.13;
                const x=mix(swirlX,wingX,merge),y=mix(swirlY,wingY,merge);
                const alpha=charge*(.36+.55*merge)*(1-smooth((t-1.7)/.08));
                butterfly(ctx,x,y,unit*(.014+.006*(i%3)),colours[i%6],Math.sin(a)*.35,
                    reduced?1:.7+.3*Math.cos(t*22+i),alpha);
            }
            if(t>1.25){
                ctx.save();ctx.globalAlpha=smooth((t-1.25)/.22)*.55;ctx.strokeStyle='#FFF1C5';ctx.lineWidth=unit*.006;
                ctx.beginPath();ctx.ellipse(cx,cy,size*.045,size*.65,0,0,TAU);ctx.stroke();ctx.restore();
            }
        }
        if(t>=1.65&&t<2.55){
            const u=clamp((t-1.65)/.55),x=mix(cx,target.x,smooth(u)),y=mix(cy,target.y,smooth(u));
            ctx.save();ctx.globalAlpha=(1-smooth((t-2.08)/.47))*.82;ctx.lineCap='round';
            for(let k=0;k<6;k++){
                ctx.strokeStyle=colours[k];ctx.lineWidth=unit*.012;
                const arc=right<0?Math.PI:0;
                ctx.beginPath();ctx.ellipse(x,y,size*(.55+u*1.5)+k*unit*.014,size*(.78+u*.82)+k*unit*.014,0,arc-1.12,arc+1.12);
                ctx.stroke();
            }
            ctx.restore();
            if(t>=1.75){
                const burst=clamp((t-1.75)/.65),number=options.lowQuality?12:24;
                for(let i=0;i<number;i++){
                    const a=i/number*TAU,dist=(.035+burst*.23)*unit;
                    star(ctx,target.x+Math.cos(a)*dist,target.y+Math.sin(a)*dist,unit*.012*(1-burst*.5),colours[i%6],1-burst,a);
                }
            }
        }
        if(t>=1.9){
            for(let i=0;i<(options.lowQuality?12:30);i++){
                const a=i*2.399963229728653,u=t-1.9,drift=reduced?0:u;
                const x=source.x+Math.cos(a)*(unit*.065+drift*unit*.15),y=source.y+Math.sin(a)*unit*.1-drift*unit*.13;
                butterfly(ctx,x,y,unit*.018,colours[i%6],Math.sin(a)*.4,1,fade*.7);
            }
        }
        title(ctx,t,w,h,options);ctx.restore();
    }
    window.ButterflyRenderer={pose,effects,state,butterfly,star};
})();
