'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.resolve('work/battle-loading-release-20261113/src/node_modules/playwright'));
const frontend = path.resolve(__dirname, '../frontend');
const origin = 'http://127.0.0.1:19129';

async function main() {
    const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
    try {
        const page = await browser.newPage({viewport:{width:320,height:700}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/*', route => {
            const url = new URL(route.request().url());
            if (url.origin !== origin) return route.abort();
            if (url.pathname === '/gia-dinh/' || url.pathname === '/nang-cap/' || url.pathname === '/thanh-toan/') {
                return route.fulfill({contentType:'text/html; charset=utf-8', body:`<!doctype html>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="stylesheet" href="/app-shell.css"><main>Fixture</main>
                    <script src="/app-shell.js" defer></script>`});
            }
            if (url.pathname === '/app-shell.js' || url.pathname === '/app-shell.css') {
                const contentType = url.pathname.endsWith('.js') ? 'text/javascript; charset=utf-8' : 'text/css; charset=utf-8';
                return route.fulfill({contentType, body:fs.readFileSync(path.join(frontend, url.pathname))});
            }
            return route.fulfill({status:404});
        });
        await page.addInitScript(() => {
            let state = {};
            const reads = [];
            const publish = (context,count) => dispatchEvent(new CustomEvent('family-cart-updated',{detail:{context,count}}));
            window.fixture = {
                publish,
                setState(context, scope='parent_full', type='parent', childOnly=false) {
                    const previous = state;
                    state = context ? {authenticated:true, context, scope, activeProfile:{type}, children:[{id:1}], device:{childOnly}} : {};
                    dispatchEvent(new CustomEvent('family-state-updated',{detail:{state,previous}}));
                },
                readContexts: () => reads.map(read => read.context),
                resolve(index,count) { reads[index].resolve({cart:{items:Array.from({length:count}, () => ({quantity:10}))}}); },
                retains: 0
            };
            window.FamilyApp = {retainCart() { fixture.retains++; return true; }};
            window.FamilyProfiles = {
                get state(){return state;},
                profileOf(value){return value.activeProfile;},
                mount(host){const button=document.createElement('button');button.className='family-profile-trigger';button.textContent='Phụ huynh';host.append(button);},
                refresh(){return Promise.resolve(state);},
                request(action){
                    if (action!=='cart') throw new Error('Unexpected action '+action);
                    return new Promise(resolve => reads.push({resolve,context:state.context}));
                }
            };
        });

        const tab = page.locator('.app-bottom-tab--cart');
        const badge = tab.locator('[data-cart-badge]');
        const nav = page.locator('.app-bottom-nav');
        const setState = (...args) => page.evaluate(args => fixture.setState(...args),args);
        const publish = (...args) => page.evaluate(args => fixture.publish(...args),args);
        const resolve = (...args) => page.evaluate(args => fixture.resolve(...args),args);
        const readContexts = () => page.evaluate(() => fixture.readContexts());

        await page.goto(origin+'/gia-dinh/?view=cart');
        await setState('current');
        await tab.waitFor();
        assert.equal(await tab.getAttribute('href'), '/gia-dinh/?view=cart');
        assert.equal(await tab.getAttribute('aria-current'), 'page');
        assert.equal(await tab.getAttribute('aria-label'), 'Giỏ hàng');
        assert.equal(await badge.isHidden(), true);
        assert.deepEqual(await nav.locator(':scope > *').allTextContents(), ['Các con','Gói học','Giỏ hàng','Tài khoản','Phụ huynh']);
        const initialBounds = await tab.boundingBox();
        assert.ok(initialBounds.width>=44&&initialBounds.height>=44);
        assert.deepEqual(await readContexts(), ['current']);
        await publish('current',3);
        await resolve(0,1); // A read that was already in flight may carry an older snapshot.
        assert.equal(await badge.textContent(), '3');
        assert.equal(await tab.getAttribute('aria-label'), 'Giỏ hàng, 3 khoản');
        await tab.click();
        assert.equal(await page.evaluate(() => fixture.retains), 1);
        assert.equal(await badge.textContent(), '3');

        await page.evaluate(() => {
            dispatchEvent(new Event('focus'));
            document.dispatchEvent(new Event('visibilitychange'));
            AppShell.sync();
        });
        assert.deepEqual(await readContexts(), ['current','current']);
        await setState('locked','profiles');
        assert.equal(await tab.isVisible(), true);
        assert.equal(await badge.isHidden(), true);
        await resolve(1,4);
        await publish('current',9);
        assert.equal(await badge.textContent(), '');

        await setState('unlocked');
        await resolve(2,2);
        assert.equal(await badge.textContent(), '2');
        await publish('unlocked',0);
        assert.equal(await badge.isHidden(), true);
        assert.equal(await tab.getAttribute('aria-label'), 'Giỏ hàng');
        await publish('unlocked',1);
        await page.evaluate(() => dispatchEvent(new Event('family-access-invalidated')));
        await publish('unlocked',9);
        assert.equal(await badge.textContent(), '');
        await setState('parent-again');
        await setState('child','child','child');
        await resolve(3,5);
        assert.equal(await tab.count(),0);
        assert.equal(await nav.getAttribute('aria-label'),'Điều hướng học tập');
        await setState('restricted','parent_full','parent',true);
        assert.equal(await tab.count(),0);
        await setState('');
        assert.equal(await nav.count(),1);assert.equal(await nav.getAttribute('data-role'),'guest');assert.equal(await tab.count(),0);
        assert.deepEqual(await readContexts(), ['current','current','unlocked','parent-again']);

        for (const checkoutPath of ['/nang-cap/', '/thanh-toan/']) {
            await page.goto(origin+checkoutPath);
            await setState('locked','profiles');
            assert.equal(await nav.locator('[aria-current="page"]').textContent(),'Gói học');
            assert.equal(await badge.isHidden(),true);
            assert.deepEqual(await readContexts(), []);
        }
        assert.deepEqual(errors, []);
        console.log('Fixed cart navigation fixture passed');
    } finally {
        await browser.close();
    }
}

main().catch(error => { console.error(error); process.exitCode=1; });
