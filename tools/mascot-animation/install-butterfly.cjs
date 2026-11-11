#!/usr/bin/env node
/* Reproduce only the Butterfly integration without staging other chats' shared files.
 * Default: inspect. Run with --apply to add missing hooks. All five files are
 * planned and validated before the first write; unfamiliar/duplicate anchors stop.
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');

const args = process.argv.slice(2);
if (args.some(arg => !['--check', '--apply', '--help'].includes(arg)) ||
    (args.includes('--check') && args.includes('--apply'))) {
    console.error('Usage: node tools/mascot-animation/install-butterfly.cjs [--check | --apply]');
    process.exit(2);
}
if (args.includes('--help')) {
    console.log('Inspect Butterfly hooks (default --check); --apply adds missing hooks idempotently.');
    console.log('Requires the existing learning/arena application and the three Butterfly frontend files.');
    process.exit(0);
}
const apply = args.includes('--apply');
const root = path.resolve(__dirname, '..', '..');
const files = new Map();
const checks = [];
const assets = ['butterfly-renderer.js', 'butterfly-animation.js', 'butterfly-animation.css'];
const esc = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function file(relative) {
    if (!files.has(relative)) {
        const target = path.join(root, relative);
        const original = fs.readFileSync(target, 'utf8');
        files.set(relative, {relative, target, original, text: original.replace(/\r\n/g, '\n')});
    }
    return files.get(relative);
}
function matches(text, expression) {
    return [...text.matchAll(new RegExp(expression.source, expression.flags.includes('g')
        ? expression.flags : expression.flags + 'g'))];
}
function unique(text, expression, label) {
    const found = matches(text, expression);
    if (found.length !== 1) throw Error(`${label}: expected one anchor, found ${found.length}`);
    return found[0];
}
function replaceOne(entry, expression, replacement, label) {
    unique(entry.text, expression, `${entry.relative}: ${label}`);
    entry.text = entry.text.replace(expression, replacement);
}
function ensure(entry, label, expression, add) {
    const found = matches(entry.text, expression);
    if (found.length > 1) throw Error(`${entry.relative}: ${label} duplicated (${found.length})`);
    if (found.length) checks.push({file: entry.relative, hook: label, status: 'present'});
    else {
        add();
        unique(entry.text, expression, `${entry.relative}: inserted ${label}`);
        checks.push({file: entry.relative, hook: label, status: 'missing'});
    }
}
function addQuotedAssets(entry, label, insert) {
    const missing = [];
    for (const asset of assets) {
        const count = matches(entry.text, new RegExp(`['"]${esc(asset)}['"]`, 'g')).length;
        if (count > 1) throw Error(`${entry.relative}: ${asset} duplicated (${count})`);
        checks.push({file: entry.relative, hook: `${label}: ${asset}`, status: count ? 'present' : 'missing'});
        if (!count) missing.push(asset);
    }
    if (missing.length) insert(missing);
    for (const asset of assets) unique(entry.text, new RegExp(`['"]${esc(asset)}['"]`, 'g'), `${entry.relative}: ${asset}`);
}

try {
    // Check that applying hooks cannot knowingly create references to absent code/art.
    for (const asset of [...assets, 'arena-art/butterfly-poses.webp']) {
        if (!fs.existsSync(path.join(root, 'frontend', asset))) throw Error(`Missing prerequisite: frontend/${asset}`);
    }

    const api = file('backend/platform_api.py');
    ensure(api, 'Butterfly API choice', /MASCOT_NAMES\[['"]butterfly['"]\]\s*=\s*['"]Bướm['"]/g, () => {
        // Refuse a conflicting inline key rather than silently overriding its name.
        if (/['"]butterfly['"]\s*:/.test(api.text)) throw Error('backend/platform_api.py: inspect existing inline butterfly key manually');
        replaceOne(api, /^MASCOT_CODES = \{name: code for code, name in MASCOT_NAMES\.items\(\)\}/m,
            "MASCOT_NAMES['butterfly'] = 'Bướm'\n$&", 'reverse mascot mapping');
    });
    if (api.text.indexOf("MASCOT_NAMES['butterfly']") > api.text.indexOf('MASCOT_CODES =')) {
        throw Error('backend/platform_api.py: butterfly must be registered before MASCOT_CODES');
    }

    const server = file('backend/server.py');
    addQuotedAssets(server, 'HTTP asset', missing => {
        const block = 'ASSETS.update({"/" + file: file for file in\n' +
            `               (${missing.map(name => JSON.stringify(name)).join(', ')}${missing.length === 1 ? ',' : ''})})\n`;
        replaceOne(server, /^PAGES = \{/m, block + '$&', 'page map');
    });

    const index = file('frontend/index.html');
    ensure(index, 'Butterfly CSS', /<link rel="stylesheet" href="butterfly-animation\.css">/g, () => {
        replaceOne(index, /<link rel="stylesheet" href="learning\.css">/g,
            '$&\n    <link rel="stylesheet" href="butterfly-animation.css">', 'learning CSS');
    });
    for (const asset of assets.filter(name => name.endsWith('.js'))) {
        ensure(index, `script: ${asset}`, new RegExp(`<script src="${esc(asset)}" defer></script>`, 'g'), () => {
            replaceOne(index, /<script src="learning\.js" defer><\/script>/g,
                `<script src="${asset}" defer></script>\n    $&`, 'learning script');
        });
    }
    const rendererAt = index.text.indexOf('<script src="butterfly-renderer.js"');
    const runtimeAt = index.text.indexOf('<script src="butterfly-animation.js"');
    const learningAt = index.text.indexOf('<script src="learning.js"');
    if (!(rendererAt < runtimeAt && runtimeAt < learningAt)) throw Error('frontend/index.html: expected renderer → animation → learning script order');

    const build = file('scripts/build-pages.cjs');
    addQuotedAssets(build, 'static build asset', missing => {
        const block = `for (const asset of [${missing.map(name => `'${name}'`).join(', ')}]) {\n` +
            "    fs.copyFileSync(path.join(frontend, asset), path.join(output, asset));\n}\n";
        replaceOne(build, /^fs\.cpSync\(path\.join\(frontend, 'arena-art'\), path\.join\(output, 'arena-art'\), \{ recursive: true \}\);/m,
            block + '$&', 'arena artwork copy');
    });

    const learning = file('frontend/learning.js');
    ensure(learning, 'Butterfly display name', /butterfly\s*:\s*['"]Bướm['"]/g, () => {
        replaceOne(learning, /const petName = \(\) => \(\{/g, "$&butterfly:'Bướm',", 'pet name map');
    });
    const whitelist = unique(learning.text, /if\s*\(!\[[^\]\n]*\]\.includes\(state\.mascot\)\)/g, 'offline mascot whitelist');
    const whitelistHasButterfly = matches(whitelist[0], /['"]butterfly['"]/g).length;
    if (whitelistHasButterfly > 1) throw Error('frontend/learning.js: butterfly duplicated in whitelist');
    checks.push({file: learning.relative, hook: 'offline mascot whitelist', status: whitelistHasButterfly ? 'present' : 'missing'});
    if (!whitelistHasButterfly) learning.text = learning.text.replace(whitelist[0], whitelist[0].replace('[', "['butterfly',"));

    const choiceLine = unique(learning.text, /^.*heading\('Chọn linh vật'\).*$/gm, 'mascot choice cards');
    const choiceCount = matches(choiceLine[0], /\[['"]butterfly['"],\s*['"]Bướm['"]\]/g).length;
    if (choiceCount > 1) throw Error('frontend/learning.js: Butterfly choice card duplicated');
    checks.push({file: learning.relative, hook: 'Butterfly choice card', status: choiceCount ? 'present' : 'missing'});
    if (!choiceCount) {
        unique(choiceLine[0], /\$\{\[\[/g, 'choice card array');
        learning.text = learning.text.replace(choiceLine[0], choiceLine[0].replace('${[[', "${[['butterfly','Bướm'],["));
    }
    ensure(learning, 'Butterfly choice action', /'choose-butterfly'\s*:\s*async/g, () => {
        const action = "'choose-butterfly':async () => { if(live)await mutate('mascot',{mascot:'butterfly'});else {state.mascot = 'butterfly';save();}refresh(); },\n        ";
        replaceOne(learning, /'choose-sprout':async \(\) =>/g, action + '$&', 'sprout choice action');
    });

    // The common completion guard also serves other character animations.
    // Only add it when absent; never replace another chat's existing guard.
    ensure(learning, 'visual completion clock', /let\s+visualHp=null[^\n;]*\bcatFinaleUntil\s*=\s*0/g, () => {
        replaceOne(learning, /let visualHp=null;/g,
            'let visualHp=null,catFinaleUntil=0,catFinishTimer=null;', 'visual HP declaration');
    });
    unique(learning.text, /let\s+visualHp=null[^\n;]*\bcatFinishTimer\s*=\s*null/g, 'visual completion timer declaration');
    ensure(learning, 'resolved visual completion guard', /Date\.now\(\)<catFinaleUntil/g, () => {
        const guard = "\n        // Let an already resolved visual finish; server HP/score/deadlines stay authoritative.\n" +
            "        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<catFinaleUntil){\n" +
            "            if(!catFinishTimer)catFinishTimer=setTimeout(()=>{catFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},catFinaleUntil-Date.now()+40);\n" +
            "            return;\n        }";
        replaceOne(learning, /function finishBattle\(result\) \{/g, '$&' + guard, 'finishBattle');
    });
    ensure(learning, 'Butterfly attack/ultimate dispatch', /window\.ButterflyAnimation\?\.hit\(/g, () => {
        const dispatch = "\n        if(window.ButterflyAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){\n" +
            "            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);\n" +
            "            ArenaAudio.effect(final?'beam':'next');return;\n        }";
        replaceOne(learning, /function animateHit\(target,attacker,final\) \{/g, '$&' + dispatch, 'animateHit');
    });
    ensure(learning, 'Butterfly mount', /window\.ButterflyAnimation\?\.mount\(\);/g, () => {
        replaceOne(learning, /if\(typeof RabbitAnimation!=='undefined'\)RabbitAnimation\.mount\(\);/g,
            '$&\n        window.ButterflyAnimation?.mount();', 'rabbit animation mount');
    });
    ensure(learning, 'Butterfly destroy', /window\.ButterflyAnimation\?\.destroy\(\);/g, () => {
        replaceOne(learning, /function unmount\(\) \{/g,
            '$&\n        window.ButterflyAnimation?.destroy();', 'route unmount');
    });
    ensure(learning, 'visual completion timer cleanup', /clearTimeout\(catFinishTimer\);/g, () => {
        replaceOne(learning, /function unmount\(\) \{/g,
            '$&\n        clearTimeout(catFinishTimer);catFinishTimer=null;catFinaleUntil=0;', 'route unmount');
    });

    const planned = [...files.values()].filter(entry => entry.text !== entry.original.replace(/\r\n/g, '\n'));
    console.log(JSON.stringify({mode: apply ? 'apply' : 'check', root, checks,
        missing: checks.filter(check => check.status === 'missing').length,
        filesToChange: planned.map(entry => entry.relative)}, null, 2));
    if (!apply) {
        process.exitCode = planned.length ? 1 : 0;
    } else {
        // Finish every plan first, then reject concurrent edits before any write.
        for (const entry of files.values()) {
            if (fs.readFileSync(entry.target, 'utf8') !== entry.original) throw Error(`${entry.relative}: changed during planning; rerun`);
        }
        for (const entry of planned) {
            const content = entry.original.includes('\r\n') ? entry.text.replace(/\n/g, '\r\n') : entry.text;
            fs.writeFileSync(entry.target, content, 'utf8');
        }
        console.log(`Applied Butterfly integration to ${planned.length} file(s).`);
    }
} catch (error) {
    console.error(`Butterfly integration stopped: ${error.message}`);
    process.exitCode = 2;
}
