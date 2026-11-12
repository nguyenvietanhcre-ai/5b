'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const content = require('../frontend/learning-content.js');
const root = path.resolve(__dirname, '..');
const catalogPath = path.join(root, 'backend/learning-catalog.json');
const before = fs.readFileSync(catalogPath, 'utf8');
const catalog = JSON.parse(before);
assert.equal(catalog.privateBankVersion, 2);
assert.equal(catalog.lessons.length, 20);
assert.equal(Object.hasOwn(catalog, 'questions'), false);

const prompts = new Set();
const ids = new Set();
for (let grade = 1; grade <= 5; grade++) {
    for (const [topic] of content.topics[grade]) {
        for (let variant = 0; variant < 12; variant++) {
            for (let difficulty = 0; difficulty < 4; difficulty++) {
                const question = content.problem(grade, topic, variant, difficulty);
                assert.match(question.id, /^offline-demo-/);
                assert.equal(question.mode, 'offline-demo');
                assert.match(question.sampleLabel, /Mẫu ngoại tuyến/);
                assert.ok(question.options.includes(String(question.answer)));
                assert.equal(new Set(question.options).size, question.options.length);
                assert.ok(question.steps.length > 0);
                assert.equal(question.questionVersionId, undefined);
                assert.doesNotMatch(JSON.stringify(question), /BANK2-/);
                prompts.add(`${grade}:${question.text}`);
                ids.add(question.id);
            }
        }
    }
}
assert.equal(prompts.size, 22); // 19 single examples plus three decimal comparisons.
assert.equal(ids.size, 960); // Display variants remain explicitly demo identities.
const signs = new Set([0,1,2].map(v => content.problem(5,'decimal',v,0).answer));
assert.deepEqual([...signs].sort(), ['<','=','>'].sort());
execFileSync(process.execPath, ['scripts/export-learning-catalog.cjs'], {cwd:root, stdio:'pipe'});
assert.equal(fs.readFileSync(catalogPath, 'utf8'), before, 'Historical export command must not write assessment answers');
console.log('Public bank boundary: 22 isolated offline examples; no private catalog export.');
