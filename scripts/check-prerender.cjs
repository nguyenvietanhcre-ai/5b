'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {randomUUID} = require('node:crypto');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'work', 'prerender-check-' + randomUUID());
const built = spawnSync(process.execPath, [path.join(__dirname, 'build-pages.cjs'), output, 'python'], {stdio: 'inherit'});
if (built.status) process.exit(built.status);
const expected = path.join(root, 'frontend', 'public-pages');
function walk(directory, relative = '') {
    for (const entry of fs.readdirSync(path.join(directory, relative), {withFileTypes: true})) {
        const name = path.join(relative, entry.name);
        if (entry.isDirectory()) walk(directory, name);
        else if (!fs.existsSync(path.join(expected, name)) ||
            !fs.readFileSync(path.join(directory, name)).equals(fs.readFileSync(path.join(expected, name)))) {
            throw new Error('Public HTML is stale: ' + name + '. Rebuild frontend/public-pages with target python.');
        }
    }
}
walk(output);
console.log('Python public HTML matches the shared static renderer');
