'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');const {chromium}=require(process.env.PLAYWRIGHT_MODULE||path.resolve('work/battle-loading-release-20261113/src/node_modules/playwright'));
const root=path.resolve(__dirname,'../frontend'),out=path.resolve(__dirname,'../../artifacts/family-parent-ui');fs.mkdirSync(out,{recursive:true});
const checks=[],calls=[],errors=[];let state={authenticated:false},rev=0,badDelete=true,badReset=true;
const children=[{id:11,name:'Bé Mầm',nickname:'Bé Mầm',grade:5,mascotCode:'gau',pinSet:true},{id:12,name:'Bông',grade:3,mascotCode:'rabbit',pinSet:true}];
const gameLimits = new Map([
    [11, {duel: 4, capture_flag: null, animal_race: 2}],
    [12, {duel: null, capture_flag: 1, animal_race: null}]
]);
const gameLabels = {duel: 'Đấu trí', capture_flag: 'Cướp Cờ', animal_race: 'Đua Thú'};
const limitWrites = [];
let failLimitRead = true, failLimitWrite = true, delayedRead;
function session(scope='parent_full'){return {authenticated:true,scope,activeProfile:{type:'parent'},parentLocked:scope!=='parent_full',csrf:'csrf'+(++rev),context:'ctx'+rev,parentPinSet:true,onboarding:{needsChild:false,needsParentPin:false},family:{id:1,parentName:'Phụ huynh',email:'qa@example.test'},device:{id:'device-a',remember:true},children};}
const config={legalVersion:'private-fixture',passwordReset:{available:true,delivery:'local-test'},companions:[{code:'gau',name:'Gấu',artUrl:'/arena-art/badge-mascots/gau.webp'}]};
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});try{const page=await browser.newPage();await page.addInitScript(()=>{window.shellViews=[];window.AppShell={setView:v=>shellViews.push(v)};});page.on('pageerror',e=>errors.push(e.message));
await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1')return route.abort();if((u.pathname==='/nang-cap/'||u.pathname==='/tai-khoan/'))return route.fulfill({body:'<h1>Gói học cùng nội dung học sinh</h1>'});const file=path.join(root,u.pathname==='/gia-dinh/'?'family/index.html':u.pathname);try{return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':file.endsWith('.webp')?'image/webp':'image/svg+xml'});}catch{return route.fulfill({status:404,body:''});}});
await page.route('**/api/family/**',async route=>{const req=route.request(),url=new URL(req.url()),action=url.pathname.split('/api/family/')[1],body=req.postDataJSON();calls.push(action);let result=state,status=200;
if(action==='config')result=config;else if(action==='state')result=state;
else if(action==='register'){assert(!Object.hasOwn(body,'parentName'));assert(!body.child);assert(body.legalConsent.name==='Phụ huynh');state={...session(),children:[],onboarding:{needsChild:true,needsParentPin:false}};result=state;}
else if(action==='password/reset/request'){assert(body.email==='qa@example.test');result={ok:true};}
else if(action==='password/reset/confirm'){assert(body.token==='private-fixture-token');assert(body.newPassword===body.confirmPassword);if(badReset){status=400;result={error:'Liên kết không hợp lệ hoặc đã hết hạn.'};}else{state={authenticated:false};result={...state,ok:true};}}
else{assert(req.headers()['x-family-context']===state.context,'context '+action);if(req.method()==='POST')assert(req.headers()['x-csrf-token']===state.csrf,'csrf '+action);
if(action==='parent/overview')result={...state,overview:children.map((c,i)=>{const {pinSet,...row}=c;return {...row,membership:{label:'Free'},today:{completedLessons:i?0:2,answeredQuestions:i?0:8,submittedExams:0,timezone:'Asia/Ho_Chi_Minh'}};})};
else if(action==='children/game-limits'){
    assert.equal(state.scope, 'parent_full');
    const childId = body?.childId ?? Number(url.searchParams.get('childId'));
    assert(gameLimits.has(childId));
    const pendingRead = req.method() === 'GET' ? delayedRead : null;
    if (pendingRead) {
        pendingRead.signalStarted();
        await pendingRead.promise;
    }
    if (req.method() === 'GET' && failLimitRead) {
        failLimitRead = false;
        return route.fulfill({status: 503, json: {error: 'Chưa đọc được giới hạn.'}});
    }
    if (req.method() === 'POST') {
        assert.deepEqual(Object.keys(body.limits), Object.keys(gameLabels));
        limitWrites.push(body);
        if (failLimitWrite) {
            failLimitWrite = false;
            return route.fulfill({status: 503, json: {error: 'Chưa lưu được giới hạn.'}});
        }
        gameLimits.set(childId, body.limits);
    }
    const games = Object.entries(gameLimits.get(childId)).map(([id,limit]) => ({
        id, label: gameLabels[id], limit, used: childId===12 ? 2 : 0
    }));
    return route.fulfill({status: 200, json: {childId, day: '2026-11-19', maxLimit: 1000, games}}).catch(error => {
        if (!pendingRead) throw error;
    });
}
else if(action==='parent/select'){assert(body.childId===11);assert(state.scope==='parent_full');}
else if(action==='child/pin'){assert(state.scope==='parent_full');assert(body.childId===11);assert(body.noPin===true?body.pin===undefined:body.pin==='1234');children[0].pinSet=!body.noPin;result=state;}
else if(action==='children/add'){assert(state.scope==='parent_full');assert(body.noPin===true&&body.pin===undefined);assert(body.name==='Con không PIN');state={...state,children:[{id:13,name:body.name,grade:5,pinSet:false,mascotCode:'gau'}],onboarding:{needsChild:false,needsParentPin:false}};result={...state,addedChildId:13};}
else if(action==='select'){assert(body.childId===13);assert(body.pin==='');state={...state,scope:'child',activeProfile:{type:'child',childId:13}};result=state;}
else if(action==='devices')result={...state,devices:[{id:'device-a',name:'Máy hiện tại'},{id:'device-b',name:'Máy cũ'}]};
else if(action==='devices/revoke')assert(body.deviceId==='device-b');
else if(action==='parent/unlock'){assert(body.pin==='654321');state=session();result=state;}
else if(action==='account/delete'){assert(body.confirm==='XOA TAI KHOAN');if(badDelete){status=403;result={error:'PIN chưa đúng.'};}else{assert(body.pin==='654321');state={authenticated:false};result={authenticated:false,closed:true};}}
}await route.fulfill({status,json:result});});
const b=name=>page.getByRole('button',{name,exact:true}),ok=name=>checks.push(name),url='http://127.0.0.1:19129/gia-dinh/';
async function load(q=''){await page.goto(url+q);await page.locator('#family-view h2').waitFor();await page.waitForFunction(()=>!document.getElementById('family-view').hasAttribute('aria-busy'));}
async function nav(v){await page.evaluate(v=>FamilyApp.navigate(v),v);}
async function responsive(name){for(const [width,height]of [[320,720],[360,800],[390,844],[844,390],[768,1024],[1024,768],[1366,900],[1440,900]]){await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+' '+width);await page.screenshot({path:path.join(out,name+'-'+width+'x'+height+'.png'),fullPage:false});}ok(name+' responsive8');}
await load('?mode=register');assert(await page.locator('input[name=parentName]').count()===0);assert(await page.locator('input[name=confirm]').count()===1);await page.getByLabel('Email của ba mẹ').fill('qa@example.test');await page.getByLabel('Mật khẩu 5BMath',{exact:true}).fill('abcdef');await page.getByLabel('Nhập lại mật khẩu',{exact:true}).fill('ghijkl');await page.locator('input[name=consent]').check();await b('Tạo tài khoản').click();await page.getByText('Hai lần nhập mật khẩu chưa khớp.',{exact:true}).waitFor();assert(!calls.includes('register'));ok('register email password confirm no real name mismatch blocked');await page.getByLabel('Nhập lại mật khẩu',{exact:true}).fill('abcdef');await b('Tạo tài khoản').click();await page.getByRole('heading',{name:'Tạo góc học cho bé'}).waitFor();ok('adult signup consent generic name immediate child onboarding');
state={authenticated:false};await load();await b('Lấy lại mật khẩu').click();await page.getByLabel('Email của ba mẹ').fill('qa@example.test');await b('Gửi liên kết xác nhận').click();await page.getByText('Nếu email có tài khoản,',{exact:false}).waitFor();assert(!state.authenticated);ok('forgot local-test mailbox uniform message no session change');
await load('?reset=1#token=private-fixture-token');assert(!page.url().includes('token'));await page.getByLabel('Mật khẩu mới',{exact:true}).fill('abcdef');await page.getByLabel('Nhập lại mật khẩu mới').fill('ghijkl');await b('Xác nhận mật khẩu mới').click();await page.getByText('Hai lần nhập mật khẩu chưa khớp.',{exact:true}).waitFor();assert(!calls.includes('password/reset/confirm'));await page.getByLabel('Nhập lại mật khẩu mới').fill('abcdef');await b('Xác nhận mật khẩu mới').click();await page.getByText('Liên kết không hợp lệ hoặc đã hết hạn.',{exact:true}).waitFor();assert(await page.getByLabel('Mật khẩu mới',{exact:true}).inputValue()==='abcdef');badReset=false;await b('Xác nhận mật khẩu mới').click();await page.getByRole('heading',{name:'Chào ba mẹ!'}).waitFor();ok('reset fragment scrub confirm mismatch invalid link retry login after success');
state=session();await load('?view=parent');const cards=page.locator('.family-child-card');assert(await cards.count()===2);for(const card of await cards.all()){assert(await card.locator('button').count()===3);assert(await card.getByRole('button',{name:'Chọn gói học',exact:true}).count()===1);assert(await card.getByRole('button',{name:'Đổi mã PIN',exact:true}).count()===1);assert(await card.getByRole('button',{name:'Quản lý',exact:true}).count()===1);}assert((await cards.first().textContent()).includes('8'));assert((await cards.last().textContent()).includes('0'));assert(await page.locator('.family-header').isHidden());assert(await page.locator('.family-footer').isHidden());assert.equal(await page.locator('#family-view > :last-child').textContent(),'Thêm con');ok('overview child summaries, three actions per child, add child after all cards');await responsive('overview');await page.screenshot({path:path.join(out,'overview-desktop.png'),fullPage:true});

const dialog = page.locator('.family-child-management');
const manageFirst = cards.first().getByRole('button', {name: 'Quản lý', exact: true});
const manageLast = cards.last().getByRole('button', {name: 'Quản lý', exact: true});
const limitField = label => dialog.getByRole('spinbutton', {name: label, exact: true});
const saveLimits = dialog.getByRole('button', {name: 'Lưu giới hạn', exact: true});
await manageLast.click();
await page.getByRole('dialog', {name: 'Quản lý Bông', exact: true}).waitFor();
await dialog.getByRole('alert').filter({hasText: 'Chưa đọc được giới hạn.'}).waitFor();
assert(await saveLimits.isHidden());
await dialog.getByRole('button', {name: 'Thử lại', exact: true}).click();
await limitField('Cướp Cờ').waitFor();
assert.equal(await limitField('Đấu trí').inputValue(), '');
assert.equal(await limitField('Cướp Cờ').inputValue(), '1');
assert.equal(await limitField('Đua Thú').inputValue(), '');
assert.equal(await dialog.getByText('Đã dùng 2 lượt hôm nay', {exact: true}).count(), 3);
for (const [width,height] of [[320,720],[360,800],[390,844],[844,390],[768,1024],[1024,768],[1366,900],[1440,900]]) {
    await page.setViewportSize({width,height});
    const bounds = await dialog.boundingBox();
    assert(bounds.x>=12 && bounds.x+bounds.width<=width-12 && bounds.y>=12 && bounds.y+bounds.height<=height-12);
    assert(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth));
    assert((await saveLimits.boundingBox()).height>=44);
}
ok('game limits read failure and retry, Bông identity and usage, dialog six viewports');

await limitField('Đấu trí').fill('1001');
await saveLimits.click();
assert.equal(limitWrites.length, 0);
await limitField('Đấu trí').fill('0');
await limitField('Cướp Cờ').fill('');
await limitField('Đua Thú').fill('1000');
await saveLimits.click();
await dialog.getByRole('alert').filter({hasText: 'Chưa lưu được giới hạn.'}).waitFor();
assert.equal(await limitField('Đấu trí').inputValue(), '0');
assert.equal(await limitField('Cướp Cờ').inputValue(), '');
await saveLimits.click();
await dialog.waitFor({state: 'detached'});
assert.deepEqual(limitWrites.at(-1), {childId: 12, limits: {duel: 0, capture_flag: null, animal_race: 1000}});
assert(await manageLast.evaluate(el => document.activeElement === el));
await page.getByText('Đã lưu giới hạn lượt chơi cho Bông.', {exact: true}).waitFor();
await manageFirst.click();
await limitField('Đấu trí').waitFor();
assert.equal(await limitField('Đấu trí').inputValue(), '4');
await page.keyboard.press('Escape');
await dialog.waitFor({state: 'detached'});
assert(await manageFirst.evaluate(el => document.activeElement === el));
await manageLast.click();
await limitField('Đấu trí').waitFor();
assert.equal(await limitField('Đấu trí').inputValue(), '0');
ok('validates bounds, retries write with exact child and blank/zero semantics, focus restores, per-child persistence');

await page.evaluate(() => { window.oldLimitForm = document.querySelector('.family-child-management form'); });
state = session('profiles');
await page.evaluate(() => FamilyProfiles.refresh());
await dialog.waitFor({state: 'detached'});
const pinDialog = page.locator('.family-profile-dialog');
await pinDialog.waitFor();
assert.equal(await cards.count(), 0);
await pinDialog.locator('input[name=pin]').fill('654321');
await pinDialog.locator('button[type=submit]').click();
await manageLast.waitFor();
assert.equal(await dialog.count(), 0);
await page.evaluate(() => oldLimitForm.dispatchEvent(new Event('submit', {cancelable:true})));
assert.equal(limitWrites.length, 2);
ok('PIN expiry removes limit dialog and prevents a detached form write after unlock');

let releaseRead, signalStarted;
const readStarted = new Promise(resolve => { signalStarted=resolve; });
delayedRead = {signalStarted, promise: new Promise(resolve => { releaseRead=resolve; })};
await manageFirst.click();
await dialog.getByRole('status').filter({hasText:'Đang tải giới hạn lượt chơi'}).waitFor();
await readStarted;
await page.evaluate(() => dispatchEvent(new CustomEvent('family-access-invalidated')));
await dialog.waitFor({state:'detached'});
releaseRead();
await b('Mở lại gia đình').click();
await manageFirst.waitFor();
assert.equal(await dialog.count(), 0);
assert.equal(limitWrites.length, 2);
delayedRead = null;
ok('profile invalidation closes loading dialog and discards stale read, no hidden write');

await nav('addchild');await page.getByLabel('Tên gọi của con').fill('Nháp giữ nguyên');await page.getByLabel('Tên gọi của con').focus();await page.evaluate(()=>{window.draft=document.querySelector('input[name=nickname]');window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'));});assert(await page.evaluate(()=>draft===document.activeElement&&draft.isConnected));ok('shell addchild preserves draft exact DOM focus on resume');await responsive('addchild');
state=session('profiles');await page.evaluate(()=>FamilyProfiles.refresh());await page.locator('dialog[open]').waitFor();assert(await page.locator('input[name=nickname]').count()===0);await page.locator('dialog input[name=pin]').fill('654321');await page.locator('dialog form button[type=submit]').click();await page.getByLabel('Tên gọi của con').waitFor();assert(await page.getByLabel('Tên gọi của con').inputValue()==='Nháp giữ nguyên');assert(await page.evaluate(()=>shellViews.at(-1).view)==='addchild','restored draft must restore active shell tab');assert(await page.evaluate(()=>draft===document.querySelector('input[name=nickname]')),'same draft DOM after PIN');ok('parent expiry restores exact draft DOM and addchild active tab after PIN');
await nav('devices');await page.evaluate(()=>{window.accountDeviceButton=[...document.querySelectorAll('#family-view button')].find(b=>b.textContent==='Thu hồi thiết bị');accountDeviceButton.focus();});state=session('profiles');await page.evaluate(()=>FamilyProfiles.refresh());await page.locator('dialog[open]').waitFor();assert(await page.locator('.family-account-devices').count()===0);await page.locator('dialog input[name=pin]').fill('654321');await page.locator('dialog form button[type=submit]').click();await page.locator('.family-account-devices').waitFor();assert(await page.evaluate(()=>accountDeviceButton.isConnected&&document.activeElement===accountDeviceButton));assert(await page.evaluate(()=>shellViews.at(-1).view)==='account');await b('Thu hồi thiết bị').click();assert(calls.includes('devices/revoke'));ok('account devices restore exact DOM focus after parent expiry then revoke exact opaque target');await responsive('devices');await b('Đăng xuất tất cả thiết bị').click();await b('Giữ đăng nhập').click();await page.getByRole('heading',{name:'Thiết bị đăng nhập',exact:true}).waitFor();assert(!calls.includes('devices/logout-all'));ok('logout all cancel returns account device section and preserves sessions');
await nav('account');assert(await page.locator('#family-view').getByRole('link',{name:'Trang chủ',exact:true}).count()===0);await b('Đổi mật khẩu').click();assert(await page.getByLabel('Mật khẩu mới',{exact:true}).getAttribute('minlength')==='6');assert(!calls.includes('parent/reauth'));ok('account password min6 no password reauth');await nav('account');await b('Xóa tài khoản').click();await responsive('delete account');await page.locator('#family-view input[name=pin]').fill('000000');await b('Xác nhận xóa tài khoản').click();assert(!calls.includes('account/delete'));await page.locator('input[name=confirm]').check();await b('Xác nhận xóa tài khoản').click();await page.getByText('PIN chưa đúng.',{exact:true}).waitFor();badDelete=false;await page.locator('#family-view input[name=pin]').fill('654321');await b('Xác nhận xóa tài khoản').click();await page.getByRole('heading',{name:'Chào ba mẹ!'}).waitFor();ok('closure requires explicit confirmation plus PIN wrong retry no false purge promise');
state=session();await load('?view=parent');await cards.first().getByRole('button',{name:'Chọn gói học'}).click();await page.waitForURL('**/nang-cap/');assert(state.scope==='parent_full');ok('plan selects child beneficiary retaining parent identity');state=session();await load('?reset=1#token=private-fixture-token');await page.getByRole('heading',{name:'Đặt mật khẩu mới',exact:true}).waitFor();assert(!page.url().includes('token'));ok('reset link opens confirmation even while signed in');state={...session('profiles'),parentPinSet:false,onboarding:{needsParentPin:true,needsChild:false,canSetupParentPin:true}};await load('?view=parent');await page.getByRole('heading',{name:'Đặt PIN phụ huynh',exact:true}).waitFor();ok('legacy family missing PIN bootstrap remains reachable');state=session();await load('?view=parent');await page.getByRole('heading',{name:'Các con',exact:true}).waitFor();assert(await b('Thêm con').count()===1);assert((await cards.first().textContent()).includes('Có mã PIN'),'state pinSet true on overview card');assert(await page.getByText('Về tổng quan',{exact:true}).count()===0);await cards.first().getByRole('button',{name:'Đổi mã PIN'}).click();assert(await page.locator('input[name=noPin]').isChecked()===false,'state pinSet true must keep noPin checkbox off when overview omits pinSet');await page.locator('input[name=noPin]').check();assert(await page.locator('#family-view input[name=pin]').isDisabled());await b('Lưu lựa chọn').click();await page.getByRole('heading',{name:'Các con',exact:true}).waitFor();assert((await cards.first().textContent()).includes('Không dùng mã PIN'));ok('children view add button concise PIN status remove PIN explicit noPin parent full');
await cards.first().getByRole('button',{name:'Đổi mã PIN'}).click();assert(await page.locator('input[name=noPin]').isChecked());await page.locator('input[name=noPin]').uncheck();await page.locator('#family-view input[name=pin]').fill('1234');await b('Lưu lựa chọn').click();await page.getByRole('heading',{name:'Các con',exact:true}).waitFor();ok('overview omits pinSet but state true and false drive card and settings; PIN restored');
await nav('devices');assert(await page.getByRole('heading',{name:'Thiết bị đăng nhập',exact:true}).count()===1);assert(await page.getByRole('heading',{name:'Tài khoản phụ huynh',exact:true}).count()===1);assert(await b('Cách sử dụng máy này').count()===0);assert(await b('Đăng xuất máy này').count()===1);assert(await page.getByText('Về tổng quan',{exact:true}).count()===0);await nav('account');assert(await b('Đăng xuất máy này').count()===1);assert(await page.getByText('Về tổng quan',{exact:true}).count()===0);await b('Đổi PIN phụ huynh').click();assert(await page.locator('input[name=noPin]').count()===0);assert(await page.locator('#family-view input[name=pin]').getAttribute('pattern')==='[0-9]{6}');ok('devices merged into Account current logout retained parent PIN mandatory');
state={...session(),children:[],onboarding:{needsChild:true,needsParentPin:false}};await load('?view=parent');await page.getByLabel('Tên gọi của con').fill('Con không PIN');await page.getByLabel('Năm sinh của con').fill('2016');await page.locator('input[name=mascot]').check();await page.locator('input[name=noPin]').check();await page.locator('input[name=consent]').check();assert(await page.locator('#family-view input[name=pin]').isDisabled());await b('Tạo hồ sơ và vào học').click();await page.waitForURL('**/tai-khoan/');ok('deliberate no PIN creation sends explicit noPin and first child enters personal route');assert(errors.length===0,errors.join('\n'));const result={passed:true,checks,count:checks.length,responsiveViewportChecks:32,jsErrors:errors,requests:calls,realDatabase:false,realNetwork:false};fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser.close();}})().catch(e=>{fs.writeFileSync(path.join(out,'FAILURE.txt'),e.stack);console.error(e);process.exitCode=1;});
