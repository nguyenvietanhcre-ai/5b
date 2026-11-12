'use strict';
// Original, quiet pentatonic loop and synthesized interface sounds. No downloads.
const ArenaAudio = (() => {
    let context, loop, active=false, step=0, muted=false;
    try { muted=localStorage.getItem('5bmath-arena-muted')==='1'; } catch {}
    function tone(frequency,duration=.13,volume=.04,type='sine',offset=0) {
        if(!context || context.state!=='running' || muted || !active || document.hidden)return;
        const oscillator=context.createOscillator(),gain=context.createGain(),at=context.currentTime+offset;
        oscillator.type=type;oscillator.frequency.setValueAtTime(frequency,at);
        gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(volume,at+.015);
        gain.gain.exponentialRampToValueAtTime(.0001,at+duration);
        oscillator.connect(gain);gain.connect(context.destination);oscillator.start(at);oscillator.stop(at+duration+.01);
    }
    function music() {
        const melody=[523,659,784,659,587,659,880,784,659,523,587,659,784,659,587,523];
        tone(melody[step%melody.length],.4,.018);
        if(step%4===0)tone([131,175,147,131][Math.floor(step/4)%4],.7,.022,'triangle');
        step++;
    }
    async function unlock() {
        if(!active || document.hidden || muted)return;
        if(!context)context=new (window.AudioContext||window.webkitAudioContext)();
        try {await context.resume();} catch {}
        if(!loop){music();loop=setInterval(music,360);}
    }
    function stop() {clearInterval(loop);loop=null;if(context?.state==='running')context.suspend().catch(()=>{});}
    function setActive(value) {active=value;if(value)unlock();else stop();}
    function effect(kind='tap') {
        if(kind==='hit'){tone(130,.2,.08,'triangle');tone(65,.3,.06,'sine',.06);}
        else if(kind==='rock'){tone(95,.28,.07,'triangle',.15);tone(60,.35,.04,'sine',.4);}
        else if(kind==='vine'){[330,392,494].forEach((f,i)=>tone(f,.3,.035,'sine',i*.12));}
        else if(kind==='lightning'){tone(1175,.12,.035,'sawtooth');tone(1568,.15,.025,'triangle',.12);tone(120,.25,.055,'sine',.22);}
        else if(kind==='win'){[523,659,784,1047].forEach((f,i)=>tone(f,.35,.06,'triangle',i*.12));}
        else if(kind==='lose'){[392,330,262].forEach((f,i)=>tone(f,.4,.04,'triangle',i*.2));}
        else if(kind==='beam'){[196,262,392,523,784,1047].forEach((f,i)=>tone(f,.65,.05,'sawtooth',i*.07));}
        else if(kind==='count')tone(660,.15,.06,'triangle');
        else if(kind==='go'){tone(1047,.4,.07,'triangle');}
        else if(kind==='wrong')tone(185,.2,.045,'triangle');
        else if(kind==='next'){tone(659,.12,.04);tone(880,.2,.04,'sine',.1);}
        else tone(760,.065,.025);
    }
    document.addEventListener('pointerdown',()=>{unlock();if(active)effect();});
    document.addEventListener('keydown',()=>unlock());
    document.addEventListener('visibilitychange',()=>document.hidden?stop():unlock());
    window.addEventListener('pagehide',stop);
    return {setActive,effect,get muted(){return muted;},toggle(){muted=!muted;try{localStorage.setItem('5bmath-arena-muted',muted?'1':'0');}catch{}if(muted)stop();else unlock();return muted;}};
})();
