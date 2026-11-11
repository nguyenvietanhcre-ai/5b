/* Reapply ONLY the owl hooks to the current shared file; never restores a stale file. */
const fs=require('node:fs'),path=require('node:path');
const root=process.cwd();
const reportDirectory=path.join(root,'work/mascot-animation/cu-meo/v1');
const filename=path.join(root,'frontend/learning.js');
let source=fs.readFileSync(filename,'utf8');
const before=source;
const edits=[];
function replaceOnce(find,replacement) {
    if(!source.includes(find))throw Error('Owl integration anchor missing: '+find.slice(0,90));
    source=source.replace(find,replacement);edits.push({find,replacement});
}
if(!source.includes("'cu-meo':'Cú mèo'"))replaceOnce('const petName = () => ({',"const petName = () => ({'cu-meo':'Cú mèo',");
const allow=source.match(/if \(!\[([^\n]+)\]\.includes\(state\.mascot\)\)/);
if(!allow)throw Error('Missing mascot allowlist');
if(!allow[1].includes("'cu-meo'"))replaceOnce(allow[0],"if (!['cu-meo',"+allow[1]+"].includes(state.mascot))");
if(!source.includes("['cu-meo','Cú mèo']"))replaceOnce("['sprout','Mầm Sách'],","['sprout','Mầm Sách'],['cu-meo','Cú mèo'],");
if(!source.includes("'choose-cu-meo':"))replaceOnce("        'choose-sprout':","        'choose-cu-meo':async () => { if(live)await mutate('mascot',{mascot:'cu-meo'});else {state.mascot = 'cu-meo';save();}refresh(); },\n        'choose-sprout':");
if(!source.includes('const owlRefreshHp='))replaceOnce("                const changed=!currentBattle||result.battle.index!==currentBattle.index;","                const changed=!currentBattle||result.battle.index!==currentBattle.index;\n                const owlRefreshHp=changed&&currentRoute==='battle'&&currentBattle?.id===result.battle.id&&(state.mascot==='cu-meo'||result.battle.opponentMascot==='cu-meo')?visualHp?.slice():null;");
if(!source.includes("if(owlRefreshHp&&currentRoute==='battle')"))replaceOnce("                if(currentRoute!=='battle')go('battle');else if(changed){refresh();setTimeout(()=>ArenaAudio.effect('next'),100);}else updateBattleVisuals();","                if(currentRoute!=='battle')go('battle');else if(changed){refresh();setTimeout(()=>ArenaAudio.effect('next'),100);}else updateBattleVisuals();\n                if(owlRefreshHp&&currentRoute==='battle'){visualHp=owlRefreshHp;updateBattleVisuals();}");
if(!source.includes('let owlFinaleUntil=0,owlFinishTimer=null;'))replaceOnce('    function animateHit(target,attacker,final) {','    let owlFinaleUntil=0,owlFinishTimer=null;\n    function animateHit(target,attacker,final) {');
if(!source.includes("if(final&&[target,attacker].some(selector=>document.querySelector(selector)?.querySelector('.battle-pet.cu-meo')))")){
    const anchor=source.includes('    function dispatchBattleHit(target,attacker,final) {')?'    function dispatchBattleHit(target,attacker,final) {':'    function animateHit(target,attacker,final) {';
    replaceOnce(anchor,anchor+"\n        if(final&&[target,attacker].some(selector=>document.querySelector(selector)?.querySelector('.battle-pet.cu-meo')))owlFinaleUntil=Math.max(owlFinaleUntil,Date.now()+3100);");
}
if(!source.includes('OwlAnimation.hit({source:owlSource,victim:owlVictim,final})'))replaceOnce('    function animateHit(target,attacker,final) {',`    function animateHit(target,attacker,final) {
        const owlSource=document.querySelector(attacker),owlVictim=document.querySelector(target);
        if(typeof OwlAnimation!=='undefined'&&OwlAnimation.hit({source:owlSource,victim:owlVictim,final})){
            if(final)owlFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':'next');return;
        }`);
if(!source.includes('Date.now()<owlFinaleUntil'))replaceOnce('    function finishBattle(result) {',`    function finishBattle(result) {
        // Visual completion only; authoritative damage, score and deadlines stay unchanged.
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<owlFinaleUntil){
            if(!owlFinishTimer)owlFinishTimer=setTimeout(()=>{owlFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},owlFinaleUntil-Date.now()+30);
            return;
        }`);
if(!source.includes("if(typeof OwlAnimation!=='undefined')OwlAnimation.mount();"))replaceOnce("        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.mount();","        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.mount();\n        if(typeof OwlAnimation!=='undefined')OwlAnimation.mount();");
if(!source.includes("if(typeof OwlAnimation!=='undefined')OwlAnimation.destroy();"))replaceOnce('    function unmount() {',`    function unmount() {
        clearTimeout(owlFinishTimer);owlFinishTimer=null;owlFinaleUntil=0;
        if(typeof OwlAnimation!=='undefined')OwlAnimation.destroy();`);
if(edits.length) {
    for(const [folder,text]of [['integration-base',before],['integration-after',source]]) {
        const target=path.join(reportDirectory,folder,'frontend/learning.js');fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,text);
    }
    fs.writeFileSync(filename,source);
    fs.writeFileSync(path.join(reportDirectory,'owl-learning-edits.json'),JSON.stringify({schema:1,file:'frontend/learning.js',edits},null,2)+'\n');
}
console.log(JSON.stringify({file:'frontend/learning.js',changes:edits.length,alreadyApplied:!edits.length}));
