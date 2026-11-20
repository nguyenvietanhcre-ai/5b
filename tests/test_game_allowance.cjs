'use strict';

const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

const source = readFileSync(join(__dirname, '../frontend/game-allowance.js'), 'utf8');
const ids = ['duel', 'capture_flag', 'animal_race'];

function fixture({role='child'}={}) {
    const calls = [];
    const timers = new Map();
    let ticket = 0;
    const window = new EventTarget();
    const document = new EventTarget();
    document.hidden = false;
    const api = {
        enabled:true, snapshot:{authenticated:true, account:{id:11}, csrf:'a'},
        familyState:{activeProfile:{type:role, childId:24}, scope:role}, familyContext:'test-child',
        request(path, body, options) {
            return new Promise((resolve, reject) => calls.push({path, body, options, resolve, reject}));
        },
    };
    const pending = (fn, duration) => { timers.set(++ticket, {fn, duration}); return ticket; };
    const clear = id => timers.delete(id);
    vm.runInNewContext(source, {
        window, document, PlatformAPI:api, AbortController, performance:{now:()=>321},
        setTimeout:pending, setInterval:pending, clearTimeout:clear, clearInterval:clear,
    });
    const counts = ids.map(id => ({dataset:{gameAllowanceCount:id}, parentElement:{dataset:{}}}));
    const feedback = {textContent:''};
    const retry = {hidden:true};
    const section = {
        dataset:{}, querySelectorAll:()=>counts,
        querySelector:selector=>selector === '[data-game-allowance-message]' ? feedback : retry,
    };
    const controls = [{disabled:false}, {disabled:true}];
    const root = Object.assign(new EventTarget(), {
        isConnected:true, querySelectorAll:selector=>selector === '[data-game-admission]' ? controls : [section],
    });
    const allowance = window.GameAllowance.mount('duel', root);
    function getTimer(duration) {
        const entry = [...timers].find(([,timer]) => timer.duration === duration);
        assert.ok(entry, `timer ${duration}ms`);
        return entry[1].fn;
    }
    return {allowance, calls, controls, counts, feedback, retry, section, api, window, document, getTimer};
}

function limits(duel, used=0, childId=24) {
    return {
        childId, day:'2026-11-19', timeZone:'Asia/Ho_Chi_Minh',
        serverTime:'2026-11-19T23:59:59.600+07:00', resetsAt:'2026-11-20T00:00:00.000+07:00',
        games:[{id:'duel',limit:duel,used,remaining:duel === null ? null : Math.max(0,duel-used)},
            {id:'capture_flag',limit:0,used:0,remaining:0}, {id:'animal_race',limit:null,used:1,remaining:null}],
    };
}

const settle = () => new Promise(resolve => setImmediate(resolve));

(async () => {
    const f = fixture();
    const [admission, unavailable] = f.controls;
    assert.equal(f.calls.length, 1);
    assert.ok(admission.disabled && unavailable.disabled);
    assert.equal(f.calls[0].path, 'game-limits');
    assert.equal(f.calls[0].body, undefined);
    assert.equal(f.calls[0].options.owner, 11);
    assert.equal(f.calls[0].options.expectedFamilyContext, 'test-child');
    assert.equal(f.calls[0].options.expectedCsrf, 'a');
    f.calls[0].resolve(limits(1));
    await settle();
    assert.deepEqual(f.counts.map(x=>x.textContent), ['Còn 1 lượt', 'Còn 0 lượt', 'Cha mẹ không giới hạn']);
    assert.ok(!admission.disabled && unavailable.disabled);

    const check = f.allowance.check();
    assert.equal(f.calls.length, 2, 'an admission rechecks the server');
    f.calls[1].resolve(limits(1, 1));
    assert.equal(await check, false);
    assert.match(f.feedback.textContent, /hết lượt.*Đấu trí/);
    assert.ok(admission.disabled && unavailable.disabled);

    f.getTimer(400)();
    assert.equal(f.counts[0].textContent, 'Đang tải…');
    assert.equal(f.calls.length, 3, 'time until day change comes from the server clock');
    f.calls[2].resolve(limits(1));
    await settle();
    assert.ok(!admission.disabled && unavailable.disabled);

    f.document.hidden = true;
    f.getTimer(15000)();
    assert.equal(f.calls.length, 3, 'hidden lobby did not poll');
    f.document.hidden = false;
    f.document.dispatchEvent(new Event('visibilitychange'));
    assert.equal(f.calls.length, 4);
    const refresh = f.allowance.refresh();
    assert.ok(f.calls[3].options.signal.aborted);
    f.calls[4].resolve(limits(0));
    await refresh;
    f.calls[3].resolve(limits(null));
    await settle();
    assert.match(f.feedback.textContent, /tạm khóa Đấu trí/);
    assert.ok(admission.disabled, 'a pre-mutation read cannot replace a later result');

    f.window.dispatchEvent(new Event('focus'));
    f.calls[5].reject(new Error('network'));
    await settle();
    assert.equal(f.section.dataset.gameAllowanceState, 'error');
    assert.equal(f.counts[0].textContent, 'Chưa rõ số lượt');
    assert.ok(!f.retry.hidden && admission.disabled);

    const mismatched = f.allowance.refresh();
    f.calls[6].resolve(limits(null, 0, 99));
    assert.equal(await mismatched, false);
    assert.equal(f.section.dataset.gameAllowanceState, 'error');
    f.window.dispatchEvent(new Event('focus'));
    f.api.familyContext = 'changed-child';
    f.window.dispatchEvent(new Event('family-state-updated'));
    assert.ok(f.calls[7].options.signal.aborted);
    f.calls[7].resolve(limits(null));
    await settle();
    assert.equal(f.section.dataset.gameAllowanceState, 'inactive');
    assert.ok(admission.disabled);
    assert.equal(fixture({role:'parent'}).calls.length, 0);
    console.log('Game allowance fixtures passed: base controls, fresh admission read, day reset, hidden/visible refresh, request supersession, errors, child/context guards, parent exclusion.');
})().catch(error=>{
    console.error(error);
    process.exitCode = 1;
});
