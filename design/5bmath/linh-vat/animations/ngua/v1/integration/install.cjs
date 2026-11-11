'use strict';
// Apply only the horse addon to an existing 5BMath game checkout/snapshot.
// Usage: node <this-file> <target-root>. Never changes database or battle rules.
const fs=require('node:fs'),path=require('node:path');
const sourceRoot=path.resolve(__dirname,'../../../../../../..');
const target=path.resolve(process.argv[2]||'.');
if(!fs.existsSync(path.join(target,'frontend/learning.js'))||!fs.existsSync(path.join(target,'backend/server.py')))throw new Error('Target must contain the existing 5BMath game');
const read=name=>fs.readFileSync(path.join(target,name),'utf8');
const write=(name,value)=>fs.writeFileSync(path.join(target,name),value);
let html=read('frontend/index.html');
if(!html.includes('href="horse-animation.css"'))html=html.replace('<link rel="stylesheet" href="learning.css">','<link rel="stylesheet" href="learning.css">\n    <link rel="stylesheet" href="horse-animation.css">');
if(!html.includes('src="horse-animation.js"'))html=html.replace('<script src="learning.js" defer></script>','<script src="horse-animation.js" defer></script>\n    <script src="learning.js" defer></script>');
write('frontend/index.html',html);
let server=read('backend/server.py');
if(!server.includes('/arena-art/horse/v1/'))server=server.replace('PAGES = {','ASSETS.update({"/" + name: name for name in ("horse-animation.js", "horse-animation.css")})\nASSETS.update({"/arena-art/horse/v1/" + name: "arena-art/horse/v1/" + name\n               for name in ("poses.webp", "reactions.webp", "poses.json", "reactions.json")})\nPAGES = {');
// Existing server uses an explicit suffix dictionary. JSON stays on the allowlist.
if(!server.includes('".json": "application/json"')&&!server.includes('".json":"application/json"'))server=server.replace(/("\.webp"\s*:\s*"image\/webp")/,'$1, ".json": "application/json"');
write('backend/server.py',server);
let learning=read('frontend/learning.js');
const hasHook=learning.includes('window.HorseAnimation?.hit(');
if(!hasHook){
 if(!learning.includes('function finishBattle(result) {')||!learning.includes('function animateHit(target,attacker,final) {'))throw new Error('Unsupported game version; no files outside target changed');
 const useExistingDelay=/let[^;]*catFinaleUntil\s*=/.test(learning);
 const deadline=useExistingDelay?'catFinaleUntil':'horseFinaleUntil';
 if(!useExistingDelay)learning=learning.replace('    function finishBattle(result) {','    let horseFinaleUntil=0,horseFinishTimer=null;\n    function finishBattle(result) {\n        if(Date.now()<horseFinaleUntil){clearTimeout(horseFinishTimer);horseFinishTimer=setTimeout(()=>finishBattle(result),horseFinaleUntil-Date.now()+40);return;}');
 learning=learning.replace('    function animateHit(target,attacker,final) {','    function animateHit(target,attacker,final) {\n        if(window.HorseAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){\n            if(final)'+deadline+'=Math.max('+deadline+',Date.now()+3100);\n            ArenaAudio.effect(final?\'beam\':\'rock\');return;\n        }');
 write('frontend/learning.js',learning);
}
for(const name of ['horse-animation.js','horse-animation.css','arena-art/horse/v1/poses.webp','arena-art/horse/v1/reactions.webp','arena-art/horse/v1/poses.json','arena-art/horse/v1/reactions.json']){
 const destination=path.join(target,'frontend',name);fs.mkdirSync(path.dirname(destination),{recursive:true});
 if(path.resolve(destination)!==path.resolve(sourceRoot,'frontend',name))fs.copyFileSync(path.join(sourceRoot,'frontend',name),destination);
}
process.stdout.write(JSON.stringify({target,sourceRoot,hookAdded:!hasHook,scope:'Horse Canvas/WebP, explicit assets, local appearance, visual finale delay only'})+'\n');
