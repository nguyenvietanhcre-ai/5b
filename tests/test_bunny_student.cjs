'use strict';
// Browser UI and Player.js fixtures. No real Bunny traffic or learner data.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const playwright = path.resolve(__dirname, '../../../release-5bmath-20261115/repo/node_modules/playwright');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || playwright);
const front = path.resolve(__dirname, '../frontend');
const appOrigin = 'http://127.0.0.1:19138';
const bunnyOrigin = 'https://player.mediadelivery.net';
const guid = 'abcdefab-abcd-abcd-abcd-abcdefabcdef';
const viewports = [[320, 740], [390, 844], [844, 390], [768, 1024], [1024, 768], [1440, 900]];

const playerStub = `<!doctype html><meta charset="utf-8"><button>Phát video mẫu</button><script>
window.calls = [];
window.tell = (event, value) => parent.postMessage(JSON.stringify({
    event, value, context:'player.js', version:'0.1.0', listener:event === 'ready' ? undefined : 'lesson-'+event
}), '${appOrigin}');
addEventListener('message', event => {
    if (event.origin === '${appOrigin}' && event.source === parent) calls.push(JSON.parse(event.data));
});
tell('ready', {src:location.href});
</script>`;

const appStub = `<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/lesson-study.css">
<main id="lesson" style="max-width:960px;margin:auto;padding:10px"></main>
<script src="/bunny-player.js"></script><script src="/lesson-study.js"></script>
<script>
const historyStore = new Map(), calls = [];
let student, stop, pendingResponse, options, deferredAction;
function select(child, type='child') {
    student = {scope:type==='child'?'child':'parent_full', activeProfile:{type,childId:child}, context:type+'-'+child};
    PlatformAPI.familyState = type==='legacy' ? null : student;
    PlatformAPI.familyContext = type==='legacy' ? '' : student.context;
    PlatformAPI.snapshot = {authenticated:true,account:{id:child},csrf:'fixture-'+child};
    dispatchEvent(new CustomEvent('family-state-updated',{detail:{state:student}}));
}
function error(status) { return Object.assign(new Error('fixture internal error'),{status}); }
const PlatformAPI = {async request(action, body, guard) {
    const child = PlatformAPI.snapshot.account.id;
    if (guard.owner !== child || guard.expectedCsrf !== PlatformAPI.snapshot.csrf ||
        guard.expectedFamilyContext !== PlatformAPI.familyContext || guard.signal.aborted) throw error(403);
    const key = JSON.stringify([child,body.provider,body.lessonKey,body.revision]);
    calls.push({action,body:{...body},child,signal:guard.signal});
    if (deferredAction === action) {
        deferredAction = null;
        await new Promise(resolve => { pendingResponse = resolve; });
    }
    if (action.endsWith('/playback')) {
        if (options.error) throw error(options.error);
        const expiresAt = Math.floor(Date.now()/1000)+(options.expiresIn ?? 120);
        const embedUrl = (options.origin || '${bunnyOrigin}')+'/embed/17/${guid}?token='+'a'.repeat(64)+'&expires='+expiresAt;
        return {playback:{embedUrl,durationSeconds:50,positionSeconds:historyStore.get(key)||0,expiresAt}};
    }
    if (!guard.signal.aborted) historyStore.set(key,body.positionSeconds);
    return {positionSeconds:body.positionSeconds};
}};
select(1);
window.fixture = {
    select, calls, histories:()=>[...historyStore],
    render({provider='main',lessonKey='fixture.lesson',revision=2,bunnyVideo=true,...settings}={}) {
        stop?.();
        options = settings;
        const root=document.querySelector('#lesson');
        root.innerHTML=LessonStudy.render({bunnyVideo,videoRef:'/previous-legacy.mp4',
            materials:[{href:'/bai.pdf',download:'bai.pdf'}],exerciseAvailable:true})
            +'<section id="lesson-exercises" hidden><h2>Câu hỏi mẫu</h2></section>';
        stop=LessonStudy.mount(root,{videoLesson:{provider,lessonKey,revision,title:'Phân số'},
            onComplete:async()=>({completed:true})});
    },
    seed(child, provider, revision, position) {
        historyStore.set(JSON.stringify([child,provider,'fixture.lesson',revision]),position);
    },
    unmount(){ stop?.(); document.querySelector('#lesson').replaceChildren(); },
    defer(action){deferredAction=action;},
    waiting(){return Boolean(pendingResponse);},
    release(){pendingResponse?.(); pendingResponse=null;}
};
</script>`;

(async () => {
    const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
    const browser = await chromium.launch({headless:true, executablePath:chrome});
    try {
        const page = await browser.newPage();
        const errors = [], blocked = [];
        let embedRequests = 0;
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/*', route => {
            const url = new URL(route.request().url());
            if (url.origin === bunnyOrigin) {
                embedRequests++;
                return route.fulfill({body:playerStub,contentType:'text/html; charset=utf-8'});
            }
            if (url.origin !== appOrigin) {
                if (!['fonts.gstatic.com','fonts.googleapis.com'].includes(url.hostname)) blocked.push(url.origin);
                return route.abort();
            }
            if (url.pathname === '/') return route.fulfill({body:appStub,contentType:'text/html; charset=utf-8'});
            const asset = path.join(front,url.pathname);
            if (fs.existsSync(asset) && fs.statSync(asset).isFile()) return route.fulfill({path:asset});
            return route.fulfill({status:404,body:''});
        });
        const status = page.locator('[data-bunny-status]');
        const toggle = page.locator('[data-bunny-toggle]');
        const iframe = page.locator('[data-bunny-frame] iframe');
        const render = settings => page.evaluate(value => fixture.render(value), settings);
        const switchTo = (id,type) => page.evaluate(([child,scope]) => fixture.select(child,scope),[id,type]);
        const frame = () => page.frame({url:/^https:\/\/player\.mediadelivery\.net\/embed\//});
        const tell = (event,value) => frame().evaluate(([name,data]) => tell(name,data),[event,value]);
        const methodCalls = () => frame().evaluate(() => calls);
        const count = action => page.evaluate(name => fixture.calls.filter(call => call.action===name).length,action);
        const capture = name => page.evaluate(action => fixture.calls.filter(call => call.action===action).map(
            ({body,child,signal}) => ({body,child,aborted:signal.aborted})),name);
        const playback = 'lesson-videos/playback', progress = 'lesson-videos/progress';
        const waitBridge = () => frame().waitForFunction(
            () => calls.some(msg=>msg.method==='addEventListener'&&msg.value==='timeupdate'&&msg.version==='0.1.0'));
        const open = async () => {
            await toggle.click();
            await iframe.waitFor();
            await page.getByRole('button',{name:'Đóng video',exact:true}).waitFor();
            await waitBridge();
        };
        await page.goto(appOrigin);
        await page.evaluate(() => fixture.seed(1,'main',2,17));
        await render();
        assert.equal(embedRequests,0);
        assert.equal(await count(playback),0);
        assert.equal(await iframe.count(),0);
        assert(!(await page.locator('#lesson').innerHTML()).includes(guid));
        assert.equal(await page.locator('a[href$="previous-legacy.mp4"]').count(),0);
        await toggle.focus();
        await page.keyboard.press('Enter');
        await page.getByRole('button',{name:'Đóng video',exact:true}).waitFor();
        await waitBridge();
        assert.equal(await count(playback),1);
        assert.equal(embedRequests,1);
        const embed = new URL(await iframe.getAttribute('src'));
        assert.equal(embed.origin,bunnyOrigin);
        for (const key of ['autoplay','rememberSettings','rememberPosition']) assert.equal(embed.searchParams.get(key),'false');
        assert.equal(await iframe.getAttribute('referrerpolicy'),'strict-origin-when-cross-origin');
        assert.equal(await iframe.getAttribute('title'),'Video bài giảng Phân số');
        await page.waitForFunction(() => document.activeElement?.tagName==='IFRAME');
        for (const [width,height] of viewports) {
            await page.setViewportSize({width,height});
            assert(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth+1));
            for (const item of await page.locator('[data-bunny-toggle],.lesson-study-actions .btn').all()) {
                const box = await item.boundingBox();
                assert(box && box.width>=44 && box.height>=44);
            }
            const box = await iframe.boundingBox();
            assert(box && Math.abs(box.width/box.height-16/9)<.03);
        }
        assert.deepEqual((await methodCalls()).filter(msg=>msg.method==='setCurrentTime').map(msg=>msg.value),[17]);
        assert((await methodCalls()).some(msg=>msg.method==='addEventListener'&&msg.value==='timeupdate'));
        assert.equal(await page.getByRole('link',{name:'Tải tài liệu'}).getAttribute('download'),'bai.pdf');
        assert(await page.locator('#lesson-exercises').isHidden());
        await page.getByRole('button',{name:'Làm bài tập'}).click();
        assert(await page.locator('#lesson-exercises').isVisible());
        // No writes from a forged source, wrong origin, bad position or initialization.
        await page.evaluate(({allowed})=>{
            const win=document.querySelector('iframe').contentWindow;
            for(const [origin,source] of [[allowed,window],['https://untrusted.test',win]]) {
                for(const event of ['play','timeupdate']) dispatchEvent(new MessageEvent('message',{origin,source,
                    data:{context:'player.js',event,value:{seconds:41,duration:50}}}));
            }
        },{allowed:bunnyOrigin});
        await tell('timeupdate',{seconds:2,duration:50});
        await tell('play');
        for (const seconds of [-1, 70, '21', null]) await tell('timeupdate',{seconds,duration:50});
        assert.equal(await count(progress),0);
        await tell('timeupdate',{seconds:22.3,duration:50});
        await page.waitForFunction(() => fixture.calls.some(call=>call.action.endsWith('/progress')));
        for (const seconds of [24, 25, 26]) await tell('timeupdate',{seconds,duration:50});
        await tell('ended');
        await page.waitForFunction(() => fixture.calls.some(call=>call.body.positionSeconds===26),null,{timeout:12000});
        assert.deepEqual((await capture(progress)).map(({body})=>body.positionSeconds),[22,26]);
        assert(await page.getByRole('button',{name:'Đánh dấu đã học'}).isEnabled());

        // Switch siblings while a progress write is in flight, then restore only matching bindings.
        await page.evaluate(() => fixture.defer('lesson-videos/progress'));
        await tell('timeupdate',{seconds:28,duration:50});
        await page.waitForFunction(()=>fixture.waiting(),null,{timeout:12000});
        await tell('timeupdate',{seconds:30,duration:50});
        await switchTo(2);
        assert.equal(await iframe.count(),0);
        assert(await toggle.isDisabled());
        assert.equal((await capture(progress)).at(-1).aborted,true);
        await page.evaluate(() => fixture.release());
        await render();
        await open();
        assert.deepEqual((await methodCalls()).filter(msg=>msg.method==='setCurrentTime'),[]);
        await tell('play');
        await tell('timeupdate',{seconds:8,duration:50});
        await page.waitForFunction(()=>fixture.calls.some(call=>call.child===2&&call.body.positionSeconds===8));
        assert(!(await capture(progress)).some(item=>item.child===2&&item.body.positionSeconds>8));
        await switchTo(1);
        await render({provider:'native'});
        await open();
        assert.deepEqual((await methodCalls()).filter(msg=>msg.method==='setCurrentTime'),[]);
        await render({revision:3});
        await open();
        assert.deepEqual((await methodCalls()).filter(msg=>msg.method==='setCurrentTime'),[]);
        await render();
        await open();
        assert.deepEqual((await methodCalls()).filter(msg=>msg.method==='setCurrentTime').map(msg=>msg.value),[26]);

        // Remove a player when the page is hidden, and discard a late signed response after unmount.
        await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide')));
        assert.equal(await iframe.count(),0);
        await toggle.focus();
        await page.keyboard.press('Enter');
        await page.getByRole('button',{name:'Đóng video',exact:true}).waitFor();
        await render();
        await page.evaluate(() => fixture.defer('lesson-videos/playback'));
        await toggle.click();
        await page.waitForFunction(() => fixture.waiting());
        await page.evaluate(() => fixture.unmount());
        assert.equal((await capture(playback)).at(-1).aborted,true);
        await page.evaluate(() => fixture.release());
        assert.equal(await iframe.count(),0);

        // A parent receives no learner calls, and server or embed errors keep reading resources available.
        await switchTo(2,'parent');
        const before = await count(playback);
        await render();
        assert(await toggle.isDisabled());
        assert.equal(await count(playback),before);
        await switchTo(2);
        for(const [failure,word] of [[403,'quyền xem'],[409,'đang được chuẩn bị'],[503,'chưa sẵn sàng']]) {
            await render({error:failure});
            await toggle.click();
            await page.waitForFunction(pattern=>document.querySelector('[data-bunny-status]').textContent.includes(pattern),word);
            assert.equal(await iframe.count(),0);
            assert(await toggle.isEnabled());
            assert(await page.getByRole('link',{name:'Tải tài liệu'}).isVisible());
        }
        const embedsBefore = embedRequests;
        await render({origin:'https://player.mediadelivery.net.untrusted.test'});
        await toggle.click();
        await page.waitForFunction(()=>document.querySelector('[data-bunny-status]').textContent.includes('không khả dụng'));
        assert.equal(embedRequests,embedsBefore);
        assert.equal(await iframe.count(),0);
        await render({expiresIn:2});
        await open();
        await iframe.waitFor({state:'detached',timeout:4000});
        assert((await status.textContent()).includes('hết hạn'));
        await render();
        await open();
        await tell('error',{code:1});
        await iframe.waitFor({state:'detached'});
        assert((await status.textContent()).includes('chưa phát được'));

        // Lesson-only admission works for standalone learners with the empty context pinned.
        await switchTo(3,'legacy');
        await render();
        await open();
        await page.evaluate(()=>document.querySelector('[data-bunny-frame] iframe').remove());
        await page.getByRole('button',{name:'Mở video',exact:true}).waitFor();
        assert.equal((await capture(playback)).at(-1).aborted,true);

        await render({bunnyVideo:false});
        assert.equal(await toggle.count(),0);
        assert.equal(await page.locator('video').getAttribute('src'),appOrigin+'/previous-legacy.mp4');
        assert.equal(await page.locator('a[href$="previous-legacy.mp4"]').count(),1);
        assert.deepEqual(blocked,[]);
        assert.deepEqual(errors,[]);
        assert.deepEqual(await page.evaluate(()=>[localStorage.length,sessionStorage.length]),[0,0]);
        console.log(JSON.stringify({status:'PASS',viewportChecks:viewports.length,fixtureOnly:true,
            progressWrites:await count(progress),embedRequests,errors}));
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode=1; });
