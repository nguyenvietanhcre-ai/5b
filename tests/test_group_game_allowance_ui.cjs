'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(path.resolve(__dirname, '../../../battle-loading-release-20261113/src/node_modules/playwright'));

const front = path.resolve(__dirname, '../frontend');
const screens = [[320, 740], [390, 844], [844, 390], [768, 1024], [1920, 1080]];
const quick = '[data-group-action="quick"]';
const listed = '#group-open-room-list [data-group-action="join"]';
const join = '#group-join-form button[type="submit"]';
const friendsTab = '[data-group-lobby-tab="friends"]';
const create = '[data-group-action="create-friends"]';
const confirm = '[data-preflight-confirm]';
const retry = '[data-game-allowance-retry]';

async function run() {
    const browser = await chromium.launch({ headless:true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe' });
    try {
        const page = await browser.newPage();
        const errors = [], checks = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/*', route => {
            const url = new URL(route.request().url());
            if (url.hostname !== '127.0.0.1') return route.abort();
            if (url.pathname === '/') {
                const sheets = ['styles','learning','arena-shared','group-games','game-allowance'];
                return route.fulfill({ contentType:'text/html; charset=utf-8', body:`<!doctype html><html lang="vi"><head><meta charset="utf-8"><base href="/"><meta name="viewport" content="width=device-width,initial-scale=1">${sheets.map(sheet => `<link rel="stylesheet" href="/${sheet}.css">`).join('')}</head><body class="learning-mode"><main id="app"></main></body></html>` });
            }
            try {
                const contentType = url.pathname.endsWith('.js') ? 'text/javascript; charset=utf-8' : url.pathname.endsWith('.css') ? 'text/css; charset=utf-8' : 'image/webp';
                return route.fulfill({ body:fs.readFileSync(path.join(front, url.pathname)), contentType });
            } catch { return route.fulfill({ status:404, body:'' }); }
        });
        await page.goto('http://127.0.0.1:19137/');
        await page.evaluate(() => {
            const ids = ['duel','capture_flag','animal_race'];
            const names = ['Đấu trí','Cướp Cờ','Đua Thú'];
            window.fixture = { calls:[], limits:[null,0,2], used:[0,0,2], ready:true, hold:false, fail:false, admissionError:false };
            const data = window.fixture;
            const players = [{ studentId:7, name:'Mầm QA', mascot:'sprout', mine:true, steps:0 }];
            window.ArenaAudio = { setActive() {}, mount() {}, button() { return ''; } };
            window.PlatformAPI = {
                enabled:true,
                snapshot:{ authenticated:true, name:'Mầm QA', account:{id:17,membership:'Free'}, csrf:'fixture-csrf', gameLimitsUnlimited:true, state:{mascot:'sprout', points:80} },
                familyContext:'fixture-context',
                familyState:{ activeProfile:{type:'child',childId:7}, scope:'child' },
                request:async (action, body, options) => {
                    data.calls.push({ action, body, owner:options?.owner, context:options?.expectedFamilyContext });
                    if (action === 'game-limits') {
                        if (data.hold) { data.hold = false; await new Promise(resolve => data.release = resolve); }
                        if (data.fail) throw new Error('Lỗi kiểm thử');
                        return {
                            childId:7, day:'2026-11-19', timeZone:'Asia/Ho_Chi_Minh',
                            serverTime:'2026-11-19T15:30:00+07:00', resetsAt:'2026-11-20T00:00:00+07:00',
                            games:ids.map((id, index) => ({ id, label:names[index], limit:data.limits[index], used:data.used[index], remaining:data.limits[index] === null ? null : Math.max(0, data.limits[index] - data.used[index]) })),
                        };
                    }
                    if (action === 'group-games/catalogue') return { ready:true, modes:[{key:'capture_flag',ready:data.ready},{key:'animal_race',ready:data.ready}], playModes:['human','bot'] };
                    if (action.startsWith('group-games/rooms?')) return { rooms:[{id:'another',code:'ABCD8451',grade:5,playerCount:2}] };
                    if (action === 'group-games/join' && data.admissionError) {
                        data.admissionError = false;
                        data.limits[2] = 0;
                        throw Object.assign(new Error('Em đã dùng hết lượt Đua Thú hôm nay theo giới hạn của phụ huynh.'), {status:429,details:{code:'parent_game_limit'}});
                    }
                    if (action === 'group-games/rooms' && body) {
                        data.used[ids.indexOf(body.mode)]++;
                        data.room = { id:'known-room', mode:body.mode, code:'C0FFEE12', status:'waiting', playMode:'human', meStudentId:7, serverTime:Date.now(), waitingExpiresAt:Date.now()+300000, players, rankings:[], mapIndex:0, round:0 };
                        return { room:data.room, gameClaim:{claimId:'claim'} };
                    }
                    if (action === 'group-games/rooms/known-room/answer') {
                        data.room.players[0].answered = true;
                        return { room:data.room };
                    }
                    if (action === 'group-games/rooms/known-room') return { room:data.room };
                    if (action === 'group-games/rooms/known-room/leave') return {};
                    if (action === 'arena' && body?.action === 'list') return { rooms:[] };
                    throw new Error('Unexpected fixture request '+action);
                },
            };
        });
        for (const file of ['nickname-policy.js','learning-content.js','game-rules.js','arena-art/badge-mascots/data.js','arena-art/badge-mascots/runtime.js','arena-shared.js','game-allowance.js','group-games.js','ui-controls.js','question-frame.js','practice-scratchpad.js','learning-modules/study.js','learning-modules/practice.js','learning-modules/profile.js','learning-modules/classroom.js','learning-modules/commerce.js','learning-modules/arena.js','learning.js']) await page.addScriptTag({ url:'/'+file });
        const lobby = (mode, room) => page.evaluate(async ([game, roomId]) => {
            FivePlayerGames.unmount();
            history.replaceState(null,'','/dau-tri/?'+new URLSearchParams({game,...(roomId ? {room:roomId} : {})}));
            document.querySelector('#app').innerHTML = FivePlayerGames.shell('arena');
            await FivePlayerGames.mount('arena');
        }, [mode, room]);
        const notice = '[data-game-allowance-message]';
        const called = action => page.evaluate(name => fixture.calls.filter(call => call.action === name).length, action);
        const admissions = () => page.evaluate(() => fixture.calls.filter(call => call.body && /group-games\/(rooms|quick|join)$/.test(call.action)).length);
        const waitBlocked = (selector, blocked) => page.waitForFunction(([target, disabled]) => document.querySelector(target)?.disabled === disabled, [selector, blocked]);
        const waitNotice = pattern => page.getByRole('status').filter({hasText:pattern}).first().waitFor();
        const checkMascotCard = async mode => {
            const card = page.getByRole('region',{name:'Thông tin linh vật'});
            assert.equal(await card.count(), 1);
            assert.equal(await card.locator(`[data-game-allowance="${mode}"]`).count(), 1);
            assert.equal(await page.locator('[data-game-allowance]').count(), 1);
            assert.equal(await card.locator('.arena-player-pet').evaluate(pet => pet.tagName), 'DIV');
            assert.equal(await card.locator('.arena-player-pet .mascot-art').count(), 1);
            assert.equal(await card.locator('.arena-player-pet small').textContent(), '80 kinh nghiệm');
            assert.equal(await card.getByRole('progressbar',{name:'Tiến độ linh vật'}).getAttribute('aria-valuenow'), '0');
            assert.equal(await card.locator('a, .arena-player-pet[tabindex], .arena-player-pet[role="link"], .arena-player-pet[onclick]').count(), 0);
            assert.equal(await card.locator('[data-game-allowance-count]').getAttribute('data-game-allowance-count'),mode);
            assert.deepEqual(await card.locator('[data-game-allowance-count]').evaluateAll(items => items.map(item => item.dataset.gameAllowanceCount)), [mode]);
            assert.equal(await card.getByText('✦ Không giới hạn',{exact:true}).count(), 0);
            for (const [width,height] of screens) {
                await page.setViewportSize({width,height});
                assert(await card.evaluate(node => {
                    const bounds = node.getBoundingClientRect();
                    return document.documentElement.scrollWidth <= innerWidth && [...node.querySelectorAll('[data-game-allowance-count]')].every(item => {
                        const tile = item.getBoundingClientRect();
                        return tile.left >= bounds.left && tile.right <= bounds.right && item.scrollWidth <= item.clientWidth;
                    });
                }), `quota fits the ${mode} mascot card at ${width} × ${height}`);
            }
        };

        await page.evaluate(() => {
            history.replaceState(null,'','/dau-tri/');
            const host = {progress:{name:'Mầm QA'}, toast() {}};
            LearningApp.configure(host);
            document.querySelector('#app').innerHTML = LearningApp.render('arena');
            LearningApp.mount('arena');
        });
        await page.getByText('Không giới hạn',{exact:true}).waitFor();
        await checkMascotCard('duel');
        await page.evaluate(() => LearningApp.unmount());

        await lobby('capture_flag');
        await waitNotice(/Cha mẹ đang tạm khóa Cướp Cờ/);
        await checkMascotCard('capture_flag');
        assert.equal(await page.locator('[data-game-allowance-count="capture_flag"]').textContent(), 'Còn 0 lượt');
        assert.equal(await page.locator('[data-game-allowance-count]').getAttribute('data-game-allowance-count'), 'capture_flag');
        const initialButtons = await page.locator('[data-game-admission]').evaluateAll(buttons => buttons.map(button => button.disabled));
        assert.deepEqual(initialButtons, [true,true,true,true,true]);
        await page.locator('#group-room-search').fill('845');
        assert(await page.locator(listed).isDisabled());
        await page.locator(friendsTab).click();
        await page.locator('#group-room-code').fill('ABCD8451');
        await page.locator('#group-room-code').press('Enter');
        await page.locator('#group-join-form').evaluate(form => form.dispatchEvent(new Event('submit', {bubbles:true,cancelable:true})));
        assert.equal(await admissions(), 0);
        checks.push('Zero limit, current game compact count, five disabled controls, list rerender and Enter guard');

        await lobby('animal_race');
        await waitNotice(/Em đã hết lượt Đua Thú hôm nay/);
        await checkMascotCard('animal_race');
        checks.push('All three mascot cards contain their quota once, have no profile link, retain XP, and fit five viewport sizes');
        assert(await page.locator(quick).isDisabled());
        await page.evaluate(() => {fixture.limits[2] = null; fixture.ready = false;});
        await page.locator('[data-group-action="refresh"]').click();
        await page.waitForFunction(() => document.querySelector('[data-game-allowance-count="animal_race"]')?.textContent === 'Không giới hạn');
        assert(await page.locator(listed).isDisabled());
        assert(await page.locator(quick).isDisabled());
        checks.push('Used-up message, unlimited refresh, and base catalogue availability preserved');

        await page.evaluate(() => {fixture.ready = true; fixture.limits[1] = 1;});
        await lobby('capture_flag');
        await waitBlocked(quick, false);
        await page.evaluate(() => {fixture.limits[1] = 0;});
        await page.locator(quick).click();
        await waitNotice(/Cha mẹ đang tạm khóa Cướp Cờ/);
        assert.equal(await admissions(), 0);
        await page.evaluate(() => {fixture.limits[1] = 1; dispatchEvent(new Event('focus'));});
        await waitBlocked(quick, false);
        await page.locator(friendsTab).click();
        await page.locator(create).click();
        await page.evaluate(() => {fixture.limits[1] = 0;});
        await page.locator(confirm).click();
        await page.locator('[data-preflight-allowance]').filter({hasText:/Cha mẹ đang tạm khóa Cướp Cờ/}).waitFor();
        assert(await page.locator(confirm).isDisabled());
        assert.equal(await admissions(), 0);
        await page.setViewportSize({width:320,height:740});
        assert(await page.locator('.group-preflight-dialog').evaluate(dialog => dialog.getBoundingClientRect().right <= innerWidth));
        await page.evaluate(() => {fixture.limits[1] = 1; dispatchEvent(new Event('focus'));});
        await waitBlocked(confirm, false);
        await page.evaluate(() => {fixture.hold = true;});
        await page.locator(confirm).click();
        await page.waitForFunction(() => typeof fixture.release === 'function');
        await page.locator('.group-preflight-dialog [value="cancel"]').click();
        await page.evaluate(() => fixture.release());
        await page.waitForFunction(() => !document.querySelector('.group-preflight-dialog'));
        assert.equal(await admissions(), 0);
        checks.push('Fresh quick/confirmation reads, parent change inside dialog, and cancellation during quota read');

        await page.locator('[data-group-lobby-tab="quick"]').click();
        await page.locator('#group-room-search').fill('ABCD');
        await page.evaluate(() => {fixture.admissionError = true;});
        const readsBeforeCrossGameError=await called('game-limits');
        await page.locator(listed).click();
        await page.locator('#group-error').filter({hasText:/hết lượt Đua Thú/}).waitFor();
        await page.waitForFunction(before=>fixture.calls.filter(call=>call.action==='game-limits').length>before,readsBeforeCrossGameError);assert.equal(await page.locator('[data-game-allowance-count="capture_flag"]').textContent(),'Còn 1 lượt');
        assert.equal(await called('group-games/join'), 1);
        await page.locator(friendsTab).click();
        await page.evaluate(() => {fixture.fail = true; dispatchEvent(new Event('focus'));});
        await page.locator(retry).waitFor();
        assert((await page.locator(retry).boundingBox()).height >= 44);
        assert(await page.locator(join).isDisabled());
        await page.evaluate(() => {fixture.fail = false;});
        await page.locator(retry).click();
        await waitBlocked(join, false);
        await page.locator(create).click();
        const readsBeforeConfirm = await called('game-limits');
        await page.locator(confirm).click();
        await page.locator('.group-joined-list').waitFor();
        assert.equal(await called('game-limits'), readsBeforeConfirm+2);
        assert.equal(await called('group-games/rooms'), 1);
        assert(await page.locator('[data-group-action="leave"]').isEnabled());
        assert.equal(await page.locator(notice).count(), 0);
        checks.push('Cross-game 429 displays actual game and refreshes counts, retry button, successful create refresh and waiting-room leave');

        const beforeResume = await called('game-limits');
        await lobby('capture_flag', 'known-room');
        assert.equal(await called('game-limits'), beforeResume);
        assert(await page.locator('[data-group-action="leave"]').isEnabled());
        await page.evaluate(() => {
            fixture.room.status = 'playing'; fixture.room.round = 1;
            fixture.room.question = {text:'1 + 1 = ?',responseMode:'typed'};
            fixture.room.deadline = Date.now()+30000;
        });
        await page.locator('#group-typed-answer').fill('2');
        await page.locator('#group-answer-form [type="submit"]').click();
        await page.waitForFunction(() => fixture.calls.some(call => call.action === 'group-games/rooms/known-room/answer'));
        assert.equal(await called('game-limits'), beforeResume);
        await page.evaluate(() => {
            PlatformAPI.familyState = {activeProfile:{type:'parent'},scope:'parent_full'};
            PlatformAPI.snapshot.familyParent = true;
        });
        await lobby('capture_flag');
        assert.equal(await called('game-limits'), beforeResume);
        checks.push('Exhausted child can resume and answer in known room; parent does not request child projection');
        assert.deepEqual(errors, []);
        console.log(JSON.stringify({ status:'PASS', checks, pageErrors:errors }));
    } finally { await browser.close(); }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
