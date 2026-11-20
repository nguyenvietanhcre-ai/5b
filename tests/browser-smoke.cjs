'use strict';
/*
 * Real-browser integration smoke test. Run against a disposable QA database:
 *   npm ci
 *   npx playwright install --with-deps chromium
 *   BASE_URL=http://127.0.0.1:8803 npm run test:browser
 * The server must already be running. The test creates a unique student and
 * saves lesson progress/theme in that database; never target production.
 * Windows PowerShell: $env:BASE_URL='http://127.0.0.1:8803'; npm run test:browser
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {randomBytes} = require('node:crypto');
let chromium, localRuntime;
try { ({chromium} = require('playwright')); }
catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') throw error;
    localRuntime = require('../tools/mascot-animation/runtime.cjs');
    ({chromium} = localRuntime.getPackage('playwright'));
}
const base = new URL(process.env.BASE_URL || 'http://127.0.0.1:8765');
const output = path.resolve(__dirname, '..', 'work', 'browser-smoke');
const report = {scope:'Real browser and HTTP API against caller-provided QA database.', checks:[], errors:[]};
const url = route => new URL(route, base).href;
const login = 'smoke_' + Date.now().toString(36) + '_' + randomBytes(4).toString('hex');
const password = 'Smoke-' + randomBytes(18).toString('base64url');
const current = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'numeric',
}).formatToParts(new Date()).filter(part => ['year','month'].includes(part.type)).map(part => [part.type,Number(part.value)]));
const birthYear = current.year - (current.month < 7 ? 1 : 0) - 10;
let browser, page;
const viewportPairs = [[390,844],[844,390],[768,1024],[1024,768],[1440,900],[900,1440]];

async function open(target, route) {
    // DOMContentLoaded can precede stylesheet downloads with JavaScript off.
    // Measure the rendered layout after resources have actually loaded.
    const response = await target.goto(url(route), {waitUntil:'load'});
    assert.equal(response.status(),200,'Expected public/private route to return200: ' + route);
    await target.locator('h1').first().waitFor({state:'visible'});
}
async function session(context) {
    const response = await context.request.get(url('/api/v1/session'));
    assert.equal(response.status(),200,'Session API unavailable');
    return response.json();
}
async function noOverflow(target,label) {
    const dimensions = await target.evaluate(() => ({
        width:innerWidth,height:innerHeight,documentWidth:document.documentElement.scrollWidth,
    }));
    assert(dimensions.documentWidth <= dimensions.width + 1, label + ': horizontal overflow ' + JSON.stringify(dimensions));
    return dimensions;
}
function track(target) {
    target.on('pageerror', error => report.errors.push(error.message));
    target.setDefaultTimeout(15000);
}
async function loginThroughUI(target) {
    await target.locator('#account').click();
    await target.locator('#auth-form').waitFor();
    await target.locator('#auth-form [name=login]').fill(login);
    await target.locator('#auth-form [name=password]').fill(password);
    const response = target.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/login' && r.request().method() === 'POST');
    await target.locator('#auth-form button[type=submit]').click();
    assert((await response).ok(),'Login request failed');
    await target.waitForURL('**/goc-hoc-tap/');
    await target.locator('#learning-app h1').waitFor();
}

(async () => {
    fs.mkdirSync(output,{recursive:true});
    const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || process.env.CHROME_PATH ||
        (process.platform === 'win32' ? (localRuntime || require('../tools/mascot-animation/runtime.cjs')).chromePath() : undefined);
    browser = await chromium.launch({headless:true,...(executablePath ? {executablePath} : {})});
    try {
        // Public content is readable without JavaScript and keeps production canonical URLs.
        const plain = await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
        await plain.route('https://fonts.googleapis.com/**', route => route.abort());
        await plain.route('https://fonts.gstatic.com/**', route => route.abort());
        const plainPage = await plain.newPage();track(plainPage);
        for (const [route,title,canonical] of [
            ['/',/Học Toán lớp 5/,'https://5bmath.vn/'],
            ['/so-sanh-so-thap-phan/',/So sánh số thập phân/,'https://5bmath.vn/so-sanh-so-thap-phan/'],
        ]) {
            await open(plainPage,route);
            assert.match(await plainPage.locator('h1').innerText(),title);
            assert.equal(await plainPage.locator('link[rel=canonical]').getAttribute('href'),canonical);
            assert((await plainPage.locator('main').innerText()).length > 300,'Main HTML lacks readable content without JavaScript');
            await noOverflow(plainPage,'No-JS ' + route);
        }
        const absent = await plain.request.get(url('/smoke-page-that-does-not-exist/'));
        assert.equal(absent.status(),404,'Unknown URL must return404');
        await plain.close();
        report.checks.push('Public home/lesson readable without JavaScript; canonical HTTPS,404 and phone layout.');

        const context = await browser.newContext({viewport:{width:390,height:844}});
        // Fonts are not part of this app/API contract and must not require public internet in CI.
        await context.route('https://fonts.googleapis.com/**', route => route.abort());
        await context.route('https://fonts.gstatic.com/**', route => route.abort());
        page = await context.newPage();track(page);
        await open(page,'/');
        await page.waitForLoadState('load');
        const resources = await page.evaluate(() => performance.getEntriesByType('resource').map(item => new URL(item.name).pathname));
        assert(!resources.some(name => /\/(?:staff|learning(?:-content)?|.*animation|arena-.*|bear-frames|butterfly-renderer)\.(?:js|css)$/.test(name)),
            'Anonymous home eagerly downloaded private learning/staff/game modules');
        assert.equal((await session(context)).authenticated,false);
        await page.locator('#account').click();
        await page.locator('#auth-switch').click();
        await page.locator('#auth-form [name=login]').fill(login);
        await page.locator('#auth-form [name=password]').fill(password);
        await page.locator('#auth-form [name=name]').fill('Mầm Xanh');
        await page.locator('#auth-form [name=birthYear]').fill(String(birthYear));
        const registration = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/register' && r.request().method() === 'POST');
        await page.locator('#auth-form button[type=submit]').click();
        const registered = await registration;
        assert(registered.ok(),'Unique QA registration failed with status ' + registered.status());
        await page.waitForURL('**/goc-hoc-tap/');
        await page.locator('#learning-app h1').waitFor();
        const owner = (await session(context)).account.id;
        await open(page,'/so-sanh-so-thap-phan/');
        const completion = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/lessons/public-decimal/complete' && r.request().method() === 'POST');
        await page.locator('[data-complete=decimal]').click();
        const completed = await completion;
        assert(completed.ok(),'Public lesson completion failed');
        const saved = await completed.json();
        assert.equal(saved.account.id,owner);
        assert(saved.state.completed['public-decimal'],'Server response did not persist canonical lesson completion');
        await page.reload({waitUntil:'domcontentloaded'});
        await page.waitForFunction(() => document.querySelector('[data-complete=decimal]')?.textContent.includes('Đã học xong'));
        assert((await session(context)).state.completed['public-decimal'],'Progress lost after reload');
        report.checks.push('Anonymous home skips staff/renderers; real UI registration, canonical completion POST and reload persist for owner.');

        await open(page,'/tai-khoan/');
        await page.locator('#appearance-form').waitFor();
        assert.match(await page.locator('meta[name=robots]').getAttribute('content'),/noindex/);
        await page.getByText('03 · Mầm Sách 3D',{exact:true}).click();
        const preference = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/preferences' && r.request().method() === 'POST');
        await page.locator('#appearance-form button[type=submit]').click();
        assert((await preference).ok(),'Theme save request failed');
        await page.waitForFunction(() => document.querySelector('#appearance-status')?.textContent.includes('Đã lưu'));
        await page.reload({waitUntil:'domcontentloaded'});
        await page.locator('#appearance-form').waitFor();
        assert.equal(await page.locator('html').getAttribute('data-theme'),'clay-sprout');
        assert.equal((await session(context)).state.theme,'clay-sprout');
        const layouts = [];
        for (const [width,height] of viewportPairs) {
            await page.setViewportSize({width,height});
            layouts.push(await noOverflow(page,'Account'));
            assert.equal(await page.locator('#appearance-form button[type=submit]').count(),1,'Theme controls missing at a narrow viewport');
        }
        report.layouts = layouts;
        report.checks.push('Private account noindex; theme selection/save survives reload; six phone/tablet/desktop orientations fit.');

        // Leaving an account must remove its progress from the anonymous view.
        const logout = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/logout' && r.request().method() === 'POST');
        await page.locator('[data-learning=logout]').click();
        assert((await logout).ok(),'Logout request failed');
        await page.waitForURL(url('/'));
        assert.equal((await session(context)).authenticated,false);
        await open(page,'/so-sanh-so-thap-phan/');
        await page.waitForLoadState('load');
        assert.equal(await page.locator('[data-complete=decimal]').innerText(),'Đánh dấu đã học','Anonymous view inherited prior account progress');
        await loginThroughUI(page);
        await open(page,'/so-sanh-so-thap-phan/');
        await page.waitForFunction(() => document.querySelector('[data-complete=decimal]')?.textContent.includes('Đã học xong'));
        assert.equal((await session(context)).account.id,owner,'Relogin restored wrong account');
        await open(page,'/tai-khoan/');
        await page.locator('#appearance-form').waitFor();
        assert.equal(await page.locator('html').getAttribute('data-theme'),'clay-sprout');
        report.checks.push('UI logout clears anonymous progress; UI login restores the same owner progress and saved appearance.');
        assert.deepEqual(report.errors,[],'Unexpected JavaScript page errors');
        report.status = 'passed';
        console.log(JSON.stringify({status:report.status,checks:report.checks,viewports:viewportPairs.length,errors:report.errors},null,2));
        await context.close();
    } catch (error) {
        report.status = 'failed';report.failure = error.message;
        if(page && !page.isClosed())await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(() => {});
        throw error;
    } finally {
        fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));
        await browser.close();
    }
})().catch(error => {console.error(error.stack);process.exitCode = 1;});
