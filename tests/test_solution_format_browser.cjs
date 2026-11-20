'use strict';
// Intercepted presentation fixtures. No login, live API, bank write, or paid service.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(path.resolve(__dirname,'../../../battle-loading-release-20261113/src/node_modules/playwright'));
const front=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/solution-format');
fs.mkdirSync(out,{recursive:true});
const application=fs.readFileSync(path.join(front,'app.js'),'utf8');
const appendRich=application.slice(application.indexOf('function appendRichContent('),application.indexOf('\nconst worksheet='));
const views=[{width:320,height:740},{width:390,height:844},{width:844,height:390},{width:768,height:1024},{width:1024,height:768},{width:1440,height:900}];
const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 160"><rect x="20" y="30" width="200" height="40" fill="#ffbe73"/><rect x="20" y="95" width="400" height="40" fill="#1f6248"/><text x="235" y="58" font-size="20">18 cm</text><text x="435" y="123" font-size="20">36 cm</text></svg>';
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const checks=[],errors=[];
try{
 for(const viewport of views){
  const page=await browser.newPage({viewport});page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',async route=>{const u=new URL(route.request().url());
   if(u.hostname!=='127.0.0.1')return route.abort();
   if(u.pathname.endsWith('.css'))return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(front,path.basename(u.pathname)))});
   if(u.pathname==='/api/owned-figure')return route.fulfill({contentType:'image/svg+xml',body:svg});
   return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/learning.css"><link rel="stylesheet" href="/local-pilot.css"><link rel="stylesheet" href="/solution-view.css"><link rel="stylesheet" href="/solution-format.css"></head><body class="learning-mode"><main style="padding:16px;max-width:1000px;margin:auto"><h1>Kiểm tra bố cục lời giải</h1><article id="portable" class="card card-pad solution"></article><article id="rich" class="card card-pad solution local-pilot" style="margin-top:24px"></article></main></body></html>'});
  });
  await page.goto('http://127.0.0.1:19201/qa-solutions/');
  for(const file of ['solution-view.js','solution-format.js'])await page.addScriptTag({content:fs.readFileSync(path.join(front,file),'utf8')});
  await page.addScriptTag({content:appendRich});
  const detail=await page.evaluate(()=>{
   const mathml='<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mfrac><mn>1</mn><mn>4</mn></mfrac><mo>+</mo><mfrac><mn>1</mn><mn>4</mn></mfrac><mo>=</mo><mfrac><mn>1</mn><mn>2</mn></mfrac></mrow></math>';
   const question={answer:'1/2',solution:[{type:'text',text:'Bước 1: Cộng hai phân số cùng mẫu số.\nGiữ nguyên mẫu số 4.'},{type:'math',latex:'1/4 + 1/4 = 1/2',mathml},{type:'text',text:'Kiểm tra: Kết quả bằng một nửa.\n\nVăn bản thử an toàn: <img src=x onerror="window.UNSAFE=1"> & 2,5 < 3.'},{type:'image',asset_id:7}]};
   const before=JSON.stringify(question);
   document.querySelector('#portable').innerHTML=StudySolution.render(question,{renderBlocks:blocks=>{const box=document.createElement('div');appendRichContent(box,blocks,[{id:7,url:'/api/owned-figure',alt:'Hai đoạn thẳng minh họa QA',width:600,height:160}]);return box.innerHTML;}});
   const richQuestion={answer:'18 cm',solution:[{type:'text',text:'Đối chiếu bảng và phép tính.'},{tag:'p',children:[{type:'text',text:'Giữ '},{tag:'strong',children:[{type:'text',text:'đúng đơn vị'}]},{type:'text',text:' trong mỗi bước; công thức '},{type:'math',latex:'1/2',mathml}]},{tag:'table',onclick:'window.UNSAFE=1',children:[{tag:'caption',children:[{type:'text',text:'Bảng minh họa QA'}]},{tag:'tbody',children:[{tag:'tr',children:[{tag:'th',children:[{type:'text',text:'Đại lượng'}]},{tag:'th',children:[{type:'text',text:'Kết quả'}]}]},{tag:'tr',children:[{tag:'td',children:[{type:'text',text:'Độ dài đoạn thẳng trong dữ liệu minh họa'}]},{tag:'td',children:[{type:'text',text:'18 cm'}]}]}]}]},{tag:'p',children:[{type:'text',text:'Đáp số: 18 cm.'}]}]};
   document.querySelector('#rich').innerHTML=StudySolution.render(richQuestion);
   const malicious=StudySolution.math({latex:'safe fallback',mathml:'<math xmlns="http://www.w3.org/1998/Math/MathML"><mtext onclick="window.UNSAFE=1">bad</mtext></math>'});
   return {unchanged:before===JSON.stringify(question),malicious};
  });
  assert(detail.unchanged);assert(!detail.malicious.includes('onclick'));assert(detail.malicious.includes('safe fallback'));
  assert.equal(await page.locator('#portable .study-solution-steps>li').count(),2);
  assert.equal(await page.locator('#portable math').count(),1);assert.equal(await page.locator('#rich math').count(),1);
  assert.equal(await page.locator('#rich table').count(),1);assert.equal(await page.locator('#rich .study-solution-content>p').count(),3);
  assert.equal(await page.locator('#rich [onclick]').count(),0);assert.equal(await page.locator('#portable img').count(),1);
  assert.equal(await page.locator('#portable img').getAttribute('src'),'/api/owned-figure');
  assert.equal(await page.locator('#portable .study-solution-final strong').textContent(),'1/2');
  assert.equal(await page.locator('#portable .study-solution-key').count(),2);
  assert.equal(await page.locator('#portable br').count(),1);
  assert.equal(await page.evaluate(()=>window.UNSAFE),undefined);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const geometry=await page.locator('#portable .study-solution-steps>li').evaluateAll(items=>items.map(item=>({font:parseFloat(getComputedStyle(item).fontSize),line:parseFloat(getComputedStyle(item).lineHeight),width:item.getBoundingClientRect().width,content:item.scrollWidth})));
  assert(geometry.every(item=>item.font>=16&&item.line/item.font>=1.7&&item.content<=item.width+1));
  await page.locator('#rich .study-solution-table').focus();assert(await page.locator('#rich .study-solution-table').evaluate(item=>item===document.activeElement));
  await page.locator('#portable').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`portable-${viewport.width}x${viewport.height}.png`),fullPage:true});
  checks.push({viewport,portableSteps:2,MathML:true,richTable:true,sourceNewlines:true,escapedHTML:true,answerEmphasis:true,authorizedFigure:true,noDocumentOverflow:true,geometry});await page.close();
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify({status:'PASS',network:'intercepted presentation fixture; not live API',checks,errors},null,2));console.log(JSON.stringify({status:'PASS',viewports:checks.length,errors}));
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
