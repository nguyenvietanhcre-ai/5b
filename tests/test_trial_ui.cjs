'use strict';
// Candidate-only UI smoke. All network is fulfilled from owned files/fixtures.
const fs = require('fs'), path = require('path'), assert = require('assert');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || path.resolve(__dirname, '../../../battle-loading-release-20261113/src/node_modules/playwright'));
const frontend = path.resolve(__dirname, '../frontend');
const output = path.resolve(__dirname, '../../artifacts/trial-ui');
const content = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../backend/trial-content.json'), 'utf8'));
fs.mkdirSync(output, {recursive: true});
const modes = ['bot', 'capture_flag', 'animal_race'];
const calls = [], errors = [], checks = [];
let state = null, generation = 0, expired = false;
function fresh() {
  const time = Date.now();
  return {demo: true, csrf: 'fixture-csrf', serverTime: time,
    session: {id: `fixture-${++generation}`, generation, createdAt: time,
      idleWarnAt: time + 1680000, idleExpiresAt: time + 1800000, absoluteExpiresAt: time + 86400000},
    lesson: content.lesson, activities: {}, preferences: {theme: 'garden', mascot: 'sprout'},
    fixtures: {children: [{name: 'Mầm mẫu', grade: 5}, {name: 'Bông mẫu', grade: 3}]}};
}
function finished(mode) {
  return {id: `fixture-${mode}`, mode, status: 'finished', total: mode === 'bot' ? 20 : 5,
    index: 5, score: 5, results: [], game: mode === 'practice' ? undefined : {status: 'finished'}};
}
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try {
    const page = await browser.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.hostname !== '127.0.0.1') return route.abort();
      if (url.pathname.startsWith('/api/')) {
        const action = url.pathname.replace('/api/trial/', '');
        calls.push({action, method: request.method()});
        assert(!/^(keep|claim|history|trial-history)(\/|$)/.test(action), `UI called retired ${action}`);
        let payload, status = 200;
        if (action === 'config') payload = {pilotGrade: 5, modes: modes.map(key => ({key, ready: true}))};
        else if (action === 'state') {payload = state || {error: expired ? 'Phiên trải nghiệm đã hết hạn.' : 'Bắt đầu phiên mẫu.'}; status = state ? 200 : expired ? 410 : 401;}
        else if (action === 'session' || action === 'reset') {state = fresh(); expired = false; payload = state;}
        else if (action === 'end') {state = null; payload = {ended: true};}
        else if (action === 'practice/start') {state.activities.practice = finished('practice'); payload = state;}
        else if (action === 'bot/start' || action === 'game/start') {
          const mode = action === 'bot/start' ? 'bot' : request.postDataJSON().mode;
          state.activities[mode] = finished(mode); payload = state;
        } else if (action === 'order/preview') payload = {demo: true, previewOnly: true};
        else if (action === 'lesson/complete') {state.lessonComplete = true; payload = state;}
        else if (action === 'preferences') {state.preferences = request.postDataJSON(); payload = state;}
        else if (action === 'activity') payload = state;
        else throw new Error(`Unexpected trial action ${action}`);
        return route.fulfill({status, json: payload});
      }
      const relative = url.pathname === '/trai-nghiem/' ? '/trial-experience/index.html' : decodeURIComponent(url.pathname);
      const file = path.join(frontend, relative);
      assert(file.startsWith(frontend + path.sep));
      try {
        const type = file.endsWith('.html') ? 'text/html' : file.endsWith('.css') ? 'text/css' : file.endsWith('.js') ? 'text/javascript' : file.endsWith('.svg') ? 'image/svg+xml' : 'image/webp';
        return route.fulfill({body: fs.readFileSync(file), contentType: type});
      } catch { return route.fulfill({status: 404, body: ''}); }
    });
    await page.goto('http://127.0.0.1:19126/trai-nghiem/');
    await page.waitForFunction(() => document.querySelector('#trial-start') && !document.querySelector('#trial-message').textContent);
    await page.locator('#trial-start').click();
    await page.locator('#trial-workspace').waitFor({state: 'visible'});
    assert.equal(await page.locator('[data-tab]').count(), 3);
    const sizes = [[360,800],[800,360],[390,844],[844,390],[768,1024],[1024,768],[1440,900]];
    for (const [width,height] of sizes) {
      await page.setViewportSize({width,height});
      for (const tab of ['learn','bot','family']) {
        await page.locator(`[data-tab="${tab}"]`).click();
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow ${tab} ${width}x${height}`);
        assert.equal(await page.getByRole('button', {name: /Giữ bài|lưu bài|Xem bài đã giữ/i}).count(), 0);
      }
      await page.screenshot({path: path.join(output, `${width}x${height}.png`), fullPage: true});
    }
    checks.push('7 viewports x 3 tabs: no horizontal overflow; no keep controls');
    await page.locator('[data-action="order-preview"]').click();
    await page.locator('.trial-preview-note').waitFor({state: 'visible'});
    checks.push('family fixture/order preview remains available');
    await page.locator('[data-tab="learn"]').click();
    await page.locator('[data-action="practice"]').first().click();
    await page.locator('#trial-practice .trial-result').waitFor({state: 'visible'});
    assert.equal(await page.locator('#trial-practice [data-action="practice"]').count(), 1);
    checks.push('practice completion offers retry without keep CTA');
    await page.locator('[data-tab="bot"]').click();
    for (const mode of modes) {
      await page.locator(`#trial-bot-lobby [data-mode="${mode}"]`).click();
      await page.locator(`#trial-bot[data-mode="${mode}"] .trial-result`).waitFor({state: 'visible'});
    }
    checks.push('all 3 game lobbies/completion retry controls render');
    await page.locator('[data-action="reset"]').click();
    await page.locator('#trial-confirm-ok').click();
    await page.waitForFunction(() => document.querySelector('#trial-message').textContent === 'Đã bắt đầu phiên mẫu mới.');
    await page.locator('#trial-workspace [data-action="end"]').click();
    await page.locator('#trial-confirm-ok').click();
    await page.locator('#trial-ended').waitFor({state: 'visible'});
    assert.equal(await page.locator('#trial-ended button').count(), 1);
    checks.push('reset/end dialogs work; ended view offers only restart');
    expired = true;
    await page.reload();
    await page.locator('#trial-ended').waitFor({state: 'visible'});
    assert.equal(await page.locator('#trial-ended button').count(), 1);
    checks.push('expired boot no longer polls legacy keep API');
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'RESULT.json'), JSON.stringify({status:'PASS', checks, calls, pageErrors: errors, network:'all local files or mocked fixtures; no real server/DB'}, null, 2));
    process.stdout.write(JSON.stringify({status:'PASS', checks, pageErrors: errors}));
  } finally { await browser.close(); }
})().catch(error => {fs.writeFileSync(path.join(output, 'ERROR.txt'), error.stack); console.error(error); process.exitCode = 1;});
