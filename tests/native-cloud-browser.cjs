'use strict';
// Runs only against the local workerd fixture; never against a remote website.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const cfg=JSON.parse(process.env.NATIVE_BROWSER_CONFIG||'{}');
const root=path.resolve(__dirname,'..'),output=path.join(cfg.directory,'site');
const upstream=new URL(cfg.workerOrigin);
assert.equal(upstream.hostname,'127.0.0.1');assert.notEqual(upstream.port,'8765');
const built=spawnSync(process.execPath,[path.join(root,'scripts/build-pages.cjs'),output,'cloudflare-live'],{cwd:root,encoding:'utf8',windowsHide:true});
assert.equal(built.status,0,built.stderr);
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{
 if(req.url.startsWith('/api/')){
  const headers={...req.headers,host:upstream.host};if(headers.origin)headers.origin=upstream.origin;
  const target=http.request(new URL(req.url,upstream),{method:req.method,headers},response=>{res.writeHead(response.statusCode,response.headers);response.pipe(res);});
  target.on('error',()=>{res.writeHead(502);res.end('Local QA proxy error');});req.pipe(target);return;
 }
 let file=path.resolve(output,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));
 if(!file.startsWith(output+path.sep)&&file!==output){res.writeHead(404);res.end();return;}
 if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,'index.html');
 if(!fs.existsSync(file)){res.writeHead(404);res.end();return;}
 res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
});
(async()=>{
 const report={status:'running',scope:'Browser + local proxy + isolated actual workerd only',views:[],errors:[]};let browser;
 try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
  const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
  page.on('pageerror',e=>report.errors.push(e.message));
  await page.goto(base+'/',{waitUntil:'domcontentloaded'});await page.locator('#account').click();await page.locator('#auth-form').waitFor();
  await page.locator('#auth-form [name=login]').fill(cfg.login);await page.locator('#auth-form [name=password]').fill(cfg.password);
  await page.locator('#auth-form button[type=submit]').click();await page.waitForURL('**/goc-hoc-tap/');
  const routes=['/goc-hoc-tap/','/chuyen-de/','/bai-giang/?knowledgeLesson='+cfg.lessonKey,'/thi-thu/','/lam-de/?pilotExam='+cfg.examId,'/nang-cap/','/tra-cuu-cau-hoi/?code='+cfg.code];
  for(const [width,height] of [[390,844],[844,390],[768,1024],[1440,900]]){
   await page.setViewportSize({width,height});
   for(const route of routes){
    await page.goto(base+route,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>typeof PlatformAPI!=='undefined'&&PlatformAPI.snapshot.authenticated===true);
    await page.locator('h1').first().waitFor();await page.waitForTimeout(250);
    if(route.startsWith('/chuyen-de/')||route.startsWith('/thi-thu/')||route.startsWith('/lam-de/')||route.startsWith('/bai-giang/'))await page.waitForFunction(()=>{const p=document.querySelector('#local-pilot');return p&&p.innerText.length>80&&!p.innerText.includes('Đang tải học liệu');});
    const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,h1:document.querySelector('h1')?.textContent,localPilot:!!document.querySelector('#local-pilot')}));
    assert(metrics.overflow<=1,JSON.stringify({route,width,height,...metrics}));report.views.push({route,width,height,...metrics});
    if(route.startsWith('/lam-de/')||route==='/nang-cap/')await page.screenshot({path:path.join(cfg.directory,`browser-${route.startsWith('/lam-de/')?'exam':'plans'}-${width}x${height}.png`),fullPage:true});
   }
  }
  const adminContext=await browser.newContext(),adminPage=await adminContext.newPage();adminPage.on('pageerror',e=>report.errors.push(e.message));
  const login=await adminContext.request.post(base+'/api/staff/login',{data:cfg.admin,headers:{Origin:base}});assert(login.ok());
  for(const [width,height] of [[390,844],[844,390],[768,1024],[1440,900]]){
   await adminPage.setViewportSize({width,height});
   await adminPage.goto(base+'/quan-tri/#management',{waitUntil:'domcontentloaded'});
   await adminPage.getByRole('heading',{name:'Trung tâm điều hành',exact:true}).waitFor();await adminPage.waitForTimeout(250);
   const overflow=await adminPage.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert(overflow<=1,'Admin overflow '+width+' '+overflow);
   report.views.push({route:'/quan-tri/#management',width,height,overflow});
   await adminPage.screenshot({path:path.join(cfg.directory,`browser-admin-${width}x${height}.png`),fullPage:true});
  }
  assert.deepEqual(report.errors,[]);report.status='passed';
 }catch(error){report.error=String(error);throw error;}
 finally{if(browser)await browser.close();server.close();fs.writeFileSync(path.join(cfg.directory,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,views:report.views.length,errors:report.errors,error:report.error}));}
})().catch(error=>{console.error(String(error));process.exitCode=1;});
