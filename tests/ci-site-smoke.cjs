const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require('playwright');
const H=path.resolve(__dirname,'../work/ci-site-smoke'),B=(process.env.BASE_URL||'http://127.0.0.1:8765').replace(/\/$/,''),edge=process.argv.includes('--edge'),out=path.join(H,'artifacts',edge?'edge':'chrome');fs.mkdirSync(out,{recursive:true});
const sizes=[[320,720],[390,844],[844,390],[768,1024],[1024,768],[1440,900]];
(async()=>{const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe'}:{})}),cases=[],errors=[];
try{const c=await browser.newContext({serviceWorkers:'block'});await c.route('**/*',r=>new URL(r.request().url()).origin===B?r.continue():r.abort());const p=await c.newPage();p.setDefaultTimeout(30000);p.on('pageerror',e=>errors.push(e.message));
async function family(action,body){const r=await c.request.get(B+'/api/family/state');assert.equal(r.status(),200);const s=await r.json();const response=await c.request.post(B+'/api/family/'+action,{headers:{Origin:B,'X-CSRF-Token':s.csrf||'','X-Family-Context':s.context||''},data:body});const v=await response.json();assert.equal(response.status(),200,action+': '+(v.error||response.status()));return v;}
async function layout(role,route,label){await p.goto(B+route);await p.waitForFunction(()=>!document.documentElement.classList.contains('page-loading'));if(role)await p.waitForFunction(role=>document.querySelector('.app-bottom-nav')?.dataset.role===role,role);
 for(const[width,height]of sizes){await p.setViewportSize({width,height});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label+' overflow '+width);
  if(role){assert.equal(await p.locator('.app-bottom-nav').count(),1);const n=await p.locator('.app-bottom-nav').boundingBox();assert(n.x>=0&&n.y>=0&&n.width<=width&&n.y+n.height<=height+1);for(const a of await p.locator('.app-bottom-tab').all()){const box=await a.boundingBox();assert(box.width>=44&&box.height>=44);}}
  else assert.equal(await p.locator('.app-bottom-nav').count(),0);
  await p.screenshot({path:path.join(out,label+'-'+width+'x'+height+'.png'),fullPage:false});cases.push({role:role||'public',route,width,height,noOverflow:true});
 }
}
await layout(null,'/','home');await layout('guest','/hoc-theo-tuan/','guest-study');assert.equal(await p.locator('.app-bottom-tab').count(),4);
for(const route of ['/backend/curriculum-samples.json','/.git/config','/docs/PROJECT_MEMORY.md'])assert.equal((await c.request.get(B+route)).status(),404);
const cfg=await(await c.request.get(B+'/api/family/config')).json(),email='browser-'+crypto.randomBytes(7).toString('hex')+'@example.test',password=crypto.randomBytes(18).toString('hex');const legalConsent={accepted:true,version:cfg.legalVersion,name:'Phụ huynh QA',contact:email,role:'parent'};
await family('register',{email,password,requestKey:crypto.randomUUID(),legalConsent});await family('parent/pin/setup',{pin:'654321'});const kid=await family('children/add',{name:'Mầm lớp 5',grade:5,birthYear:2016,mascot:'cat',noPin:true,requestKey:crypto.randomUUID(),legalConsent});
await layout('parent','/gia-dinh/','parent-family');assert(await p.getByRole('link',{name:/Giỏ hàng/}).isVisible());
await family('select',{childId:kid.addedChildId});await layout('child','/hoc-theo-tuan/','child-study');await layout('child','/thi-thu/','child-practice');await layout('child','/dau-tri/','child-games');await layout('child','/tai-khoan/','child-profile');
const scripts=await p.evaluate(()=>typeof RuntimeAssets==='object'?RuntimeAssets.inspect().scripts:[]);assert.equal(new Set(scripts).size,scripts.length);
await layout(null,'/trai-nghiem/','trial');
await family('logout',{});await p.goto(B+'/gia-dinh/');
await p.getByLabel('Email của ba mẹ').fill(email);await p.getByLabel('Mật khẩu 5BMath',{exact:true}).fill(password);
const loggedIn=p.waitForResponse(r=>new URL(r.url()).pathname==='/api/family/login'&&r.request().method()==='POST');
await p.locator('form').getByRole('button',{name:'Đăng nhập',exact:true}).click();
const loginResponse=await loggedIn;assert.equal(loginResponse.status(),200);assert.equal((await loginResponse.json()).authenticated,true);
await p.waitForFunction(()=>window.FamilyProfiles?.state.authenticated===true);
const fresh=await(await c.request.get(B+'/api/family/state')).json();assert.equal(fresh.authenticated,true);assert.notEqual(fresh.scope,'parent_full');
await family('select',{childId:kid.addedChildId});const selected=await(await c.request.get(B+'/api/family/state')).json();assert.equal(selected.selectedChildId,kid.addedChildId);

assert.deepEqual(errors,[]);const report={status:'passed',browser:edge?'Edge':'Chrome',cases,errors,syntheticDataOnly:true,realBankTransactions:0,realVideosCreated:0};fs.writeFileSync(path.join(H,edge?'BROWSER-EDGE-QA.json':'BROWSER-QA.json'),JSON.stringify(report,null,2));console.log('PASS '+report.browser+' '+cases.length+' page/role/viewports, no JS errors');
}finally{await browser.close();}})().catch(e=>{fs.writeFileSync(path.join(H,edge?'BROWSER-EDGE-FAILURE.txt':'BROWSER-FAILURE.txt'),e.stack);console.error(e);process.exit(1)});
