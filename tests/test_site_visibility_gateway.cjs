'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const source=fs.readFileSync('scripts/pages-worker.mjs','utf8').replace('const liveBackend = false; // BUILD_LIVE_BACKEND','const liveBackend = true; // BUILD_LIVE_BACKEND');
 const worker=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
 let hidden=false,assets=0,checks=0,mutations=0;
 const env={ASSETS:{fetch:async r=>{assets++;return new Response('normal '+new URL(r.url).pathname,{status:200});}},BACKEND:{fetch:async r=>{const p=new URL(r.url).pathname;if(p==='/api/site-visibility/check'){checks++;return hidden?new Response('Hệ thống đang được cập nhật, vui lòng quay lại sau.',{status:503,headers:{'Content-Type':'text/html','X-5BMath-Maintenance':'1','Cache-Control':'no-store'}}):new Response(null,{status:204});}if(r.method==='POST')mutations++;return new Response('admin or operational',{status:200});}}};
 for(const path of ['/','/app.js','/unknown/','/api/v1/preferences','/api/local-pilot/catalogue','/robots.txt','/sitemap.xml']){
  hidden=true;const old=assets,oldWrites=mutations;const r=await worker.fetch(new Request('https://5bmath.vn'+path,{method:'POST',body:'original bytes'}),env);assert.equal(r.status,503);assert.match(await r.text(),/Hệ thống/);assert.equal(assets,old);assert.equal(mutations,oldWrites);
 }
 const head=await worker.fetch(new Request('https://5bmath.vn/unknown',{method:'HEAD'}),env);assert.equal(head.status,503);assert.equal(await head.text(),'');
 for(const path of ['/quan-tri/bao-tri/','/api/staff/site-visibility','/api/staff/site-visibility/session','/api/staff/site-visibility/login']){const old=checks;assert.equal((await worker.fetch(new Request('https://5bmath.vn'+path),env)).status,200);assert.equal(checks,old);}
 for(const[path,method]of [['/api/health','GET'],['/api/webhooks/sepay','POST']]){const old=checks;assert.equal((await worker.fetch(new Request('https://5bmath.vn'+path,{method}),env)).status,200);assert.equal(checks,old);}
 hidden=false;const normal=await worker.fetch(new Request('https://5bmath.vn/'),env);assert.equal(await normal.text(),'normal /');
 const failed={...env,BACKEND:{fetch:async()=>{throw Error('unavailable');}}};assert.equal((await worker.fetch(new Request('https://5bmath.vn/'),failed)).status,503);assert.equal((await worker.fetch(new Request('https://5bmath.vn/'),{})).status,503);
 const unavailable={...env,BACKEND:{fetch:async()=>Response.json({error:'storage unavailable'},{status:503})}};
 const fallback=await worker.fetch(new Request('https://5bmath.vn/lesson/'),unavailable);assert.equal(fallback.status,503);assert.match(fallback.headers.get('Content-Type'),/text\/html/);assert.match(await fallback.text(),/Hệ thống đang được cập nhật/);
 console.log('PASS: all URL classes intercepted before assets/mutations; recovery, health and signed webhook routing preserved; public restoration and fail-closed gateway');
})().catch(e=>{console.error(e);process.exitCode=1;});
