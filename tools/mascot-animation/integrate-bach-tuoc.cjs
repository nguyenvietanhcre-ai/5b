#!/usr/bin/env node
'use strict';
// Apply only the Bạch tuộc hooks to an existing learning-app checkout.
// Supports --check; computes every edit before writing and preserves other mascots.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),check=process.argv.includes('--check');
const plans=[];
function edit(relative,transform){
    const file=path.join(root,relative);
    if(!fs.existsSync(file))throw Error('Thiếu tệp ứng dụng: '+relative);
    const before=fs.readFileSync(file,'utf8'),after=transform(before);
    if(before!==after)plans.push({relative,file,after});
}
function insertBefore(source,anchor,text){
    if(!source.includes(anchor))throw Error('Không tìm thấy điểm tích hợp: '+anchor);
    return source.replace(anchor,text+anchor);
}
const branch=`        if(sourcePet?.classList.contains('octopus')&&typeof OctopusAnimation!=='undefined'){
            if(final)octopusFinaleUntil=Math.max(octopusFinaleUntil,Date.now()+3100);
            sourcePet.dataset.mood=final?'ultimate':'attack';source?.classList.add('attacking');
            const label=document.querySelector('#spell-announcement');if(label)label.textContent=final?'':'✦ Sóng tay Bạch tuộc';
            const impact=()=>{if(!victim?.isConnected||!victimPet)return;victim.dataset.spell='ink';victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(victimPet,final?'lose':'hit');};
            if(final)setTimeout(impact,1750);else impact();
            ArenaAudio.effect(final?'beam':'rock');
            setTimeout(()=>{
                source?.classList.remove('attacking');victim?.classList.remove('taking-hit');
                if(sourcePet.isConnected)sourcePet.dataset.mood='idle';
                if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';
                if(label?.isConnected)label.textContent='';
            },final?3000:1200);
            return;
        }
`;
edit('frontend/learning.js',source=>{
    let s=source;
    const nameLine=s.split(/\r?\n/).find(line=>line.includes('const petName ='));
    if(!nameLine)throw Error('Thiếu ánh xạ tên linh vật.');
    if(!nameLine.includes("octopus:'Bạch tuộc'"))s=s.replace(nameLine,nameLine.replace('({',"({octopus:'Bạch tuộc',"));
    const validLine=s.split(/\r?\n/).find(line=>line.includes('includes(state.mascot)'));
    if(!validLine)throw Error('Thiếu danh sách linh vật hợp lệ.');
    if(!validLine.includes("'octopus'"))s=s.replace(validLine,validLine.replace('if (![',"if (!['octopus',"));
    const options=s.split(/\r?\n/).find(line=>line.includes("heading('Chọn linh vật')"));
    if(!options)throw Error('Thiếu giao diện chọn linh vật.');
    if(!options.includes("['octopus','Bạch tuộc']"))s=s.replace(options,options.replace('${[[',"${[['octopus','Bạch tuộc'],["));
    if(!s.includes("'choose-octopus':"))s=insertBefore(s,"        'choose-rabbit':","        'choose-octopus':async () => { if(live)await mutate('mascot',{mascot:'octopus'});else {state.mascot = 'octopus';save();}refresh(); },\n");
    if(!s.includes('let octopusFinaleUntil='))s=insertBefore(s,'    let currentBattle = null;', '    let octopusFinaleUntil=0,octopusFinishTimer=null;\n');
    if(!s.includes("Date.now()<octopusFinaleUntil")){
        const anchor='    function finishBattle(result) {';
        const guard=`
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<octopusFinaleUntil){
            if(!octopusFinishTimer)octopusFinishTimer=setTimeout(()=>{octopusFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},octopusFinaleUntil-Date.now()+40);
            return;
        }`;
        if(!s.includes(anchor))throw Error('Thiếu luồng kết quả trận đấu.');
        s=s.replace(anchor,anchor+guard);
    }
    if(!s.includes('clearTimeout(octopusFinishTimer)')){
        const anchor='    function unmount() {';
        if(!s.includes(anchor))throw Error('Thiếu luồng đóng trang học tập.');
        s=s.replace(anchor,anchor+'\n        clearTimeout(octopusFinishTimer);octopusFinishTimer=null;octopusFinaleUntil=0;');
    }
    if(!s.includes("querySelector('.battle-pet.octopus'))octopusFinaleUntil")){
        const anchor='    function animateHit(target,attacker,final) {';
        if(!s.includes(anchor))throw Error('Thiếu luồng hiệu ứng chiến đấu.');
        s=s.replace(anchor,anchor+"\n        if(final&&document.querySelector(target)?.querySelector('.battle-pet.octopus'))octopusFinaleUntil=Date.now()+4100;");
    }
    if(!s.includes("sourcePet?.classList.contains('octopus')&&typeof OctopusAnimation")){
        s=insertBefore(s,"        const rabbitUltimate=final&&sourcePet?.classList.contains('rabbit')",branch);
    }
    return s;
});
edit('backend/platform_api.py',s=>s.includes("MASCOT_NAMES['octopus']")||/['"]octopus['"]\s*:/.test(s)?s:insertBefore(s,'MASCOT_CODES =',"MASCOT_NAMES['octopus'] = 'Bạch tuộc'\n"));
edit('frontend/index.html',source=>{
    let s=source;
    if(!s.includes('href="octopus-animation.css"'))s=insertBefore(s,'    <link rel="stylesheet" href="staff.css">','    <link rel="stylesheet" href="octopus-animation.css">\n');
    if(!s.includes('src="octopus-animation.js"'))s=insertBefore(s,'    <script src="learning.js" defer></script>','    <script src="octopus-animation.js" defer></script>\n');
    return s;
});
edit('backend/server.py',s=>s.includes('"octopus-animation.js"')?s:insertBefore(s,'PAGES = {',`ASSETS.update({"/" + file: file for file in
               ("octopus-animation.js", "octopus-animation.css", "arena-art/bach-tuoc-frames.json")})
`));
edit('scripts/build-pages.cjs',s=>s.includes("'octopus-animation.js'")?s:insertBefore(s,"fs.cpSync(path.join(frontend, 'arena-art')",`for (const asset of ['octopus-animation.js', 'octopus-animation.css']) {
    fs.copyFileSync(path.join(frontend, asset), path.join(output, asset));
}
`));
if(check){
    console.log(plans.length?'Cần áp dụng: '+plans.map(plan=>plan.relative).join(', '):'Bạch tuộc đã được tích hợp; không cần sửa tệp.');
    process.exitCode=plans.length?1:0;
}else{
    for(const plan of plans)fs.writeFileSync(plan.file,plan.after);
    console.log(plans.length?'Đã cập nhật '+plans.length+' tệp cho Bạch tuộc.':'Bạch tuộc đã được tích hợp; không sửa tệp.');
}
