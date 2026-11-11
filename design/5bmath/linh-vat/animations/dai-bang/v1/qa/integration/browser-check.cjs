const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
let projectRoot=__dirname;while(!fs.existsSync(path.join(projectRoot,'frontend/app.js'))){const parent=path.dirname(projectRoot);if(parent===projectRoot)throw Error('Run inside the 5BMath project');projectRoot=parent;}const {getPackage,chromePath}=require(path.join(projectRoot,'tools/mascot-animation/runtime.cjs'));
const {chromium}=getPackage('playwright');
const root=path.join(projectRoot,'frontend');
const html=`<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/eagle-animation.css"><style>
body{margin:0;background:#fff9ed;color:#203a32;font:16px Arial}#battle-stage{position:relative;width:min(100vw,680px);height:min(100vw,680px);margin:auto;background:#c7e3cb;overflow:hidden;border-radius:16px}
.fighter{position:absolute;width:36%;left:5%;bottom:5%}.fighter.right{left:auto;right:5%;top:5%;bottom:auto}.battle-pet{display:block;position:relative;aspect-ratio:1;width:100%}.mascot-art{display:block;width:100%;height:100%}.right .battle-pet{transform:scaleX(-1)}.fox{background:#ffbe73;border-radius:50%;}h1{text-align:center;font-size:20px}</style><script src="/eagle-animation.js" defer></script></head><body class="learning-mode"><h1>Đại bàng — Canvas + WebP</h1><div id="battle-stage"><div class="fighter" id="fighter-me"><span class="battle-pet eagle" data-mood="idle" role="img" aria-label="Đại bàng"><span class="mascot-art eagle"></span></span></div><div class="fighter right" id="fighter-opponent"><span class="battle-pet fox" role="img" aria-label="Đối thủ thử nghiệm"></span></div></div></body></html>`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:chromePath()});
 const report={viewports:[],errors:[],requests:[]};
 const context=await browser.newContext();
 await context.route('http://eagle.test/**',async route=>{const u=new URL(route.request().url());if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:html});
  const file=path.resolve(root,'.'+u.pathname);if(!file.startsWith(root+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:'missing'});
  return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'image/webp'});});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>report.requests.push(r.url()));
 await page.goto('http://eagle.test/');await page.evaluate(()=>EagleAnimation.ready());await page.waitForSelector('.eagle-ready');
 for(const [width,height]of [[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){
  await page.setViewportSize({width,height});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
  await page.screenshot({path:path.join(__dirname,`viewport-${width}x${height}.png`)});report.viewports.push({width,height,overflow});
 }
 const pet=()=>page.locator('.battle-pet.eagle');
 await page.evaluate(()=>EagleAnimation.play(document.querySelector('.eagle'),'attack'));await page.waitForTimeout(400);
 assert(Number(await pet().getAttribute('data-eagle-frame'))>=4);await page.waitForTimeout(750);assert.equal(await pet().getAttribute('data-mood'),'idle');
 await page.evaluate(()=>EagleAnimation.play(document.querySelector('.eagle'),'hit'));await page.waitForTimeout(400);assert(Number(await pet().getAttribute('data-eagle-frame'))>=8);
 await page.evaluate(()=>EagleAnimation.play(document.querySelector('.eagle'),'lose'));await page.waitForTimeout(3100);assert.equal(await pet().getAttribute('data-eagle-frame'),'15');
 await page.screenshot({path:path.join(__dirname,'defeat.png')});
 await page.evaluate(()=>EagleAnimation.hit({source:document.querySelector('#fighter-me'),victim:document.querySelector('#fighter-opponent'),final:true}));
 await page.waitForSelector('.eagle-ultimate-canvas');
 for(const [wait,name]of [[740,'name'],[560,'dive'],[500,'impact'],[750,'celebrate']]){await page.waitForTimeout(wait);await page.screenshot({path:path.join(__dirname,`ultimate-${name}.png`)});}
 await page.waitForTimeout(650);assert.equal(await page.locator('.eagle-ultimate-canvas').count(),0);
 assert.equal(await pet().getAttribute('data-mood'),'win');
 await page.emulateMedia({reducedMotion:'reduce'});await page.evaluate(()=>EagleAnimation.hit({source:document.querySelector('#fighter-me'),victim:document.querySelector('#fighter-opponent'),final:true}));await page.waitForTimeout(50);
 assert.equal(await page.locator('.eagle-ultimate-canvas').count(),0);assert.equal(await pet().getAttribute('data-mood'),'win');
 await page.evaluate(()=>{EagleAnimation.destroy();document.querySelector('.eagle').remove();});assert.equal(await page.locator('.eagle-canvas').count(),0);
 assert.equal(report.errors.length,0);assert.equal(report.requests.filter(s=>/\.(gif|mp4)/.test(s)).length,0);
 report.checks=['attack→idle','hit row','defeat final row','ultimate finite 3s','five viewports','reduced motion','destroy','no video/GIF loads'];
 fs.writeFileSync(path.join(__dirname,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
