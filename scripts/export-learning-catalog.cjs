'use strict';
// Historical command retained as a guard. Public offline examples must never
// regenerate the private, versioned assessment bank in SQLite.
const fs = require('node:fs');
const path = require('node:path');
const catalogPath = path.join(__dirname, '../backend/learning-catalog.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
if (catalog.privateBankVersion !== 2 || catalog.questions || catalog.lessons?.length !== 20) {
    throw new Error('Catalog must contain lesson metadata only. Seed assessments with backend.question_bank.');
}
console.log(`Validated ${catalog.lessons.length} public lesson examples; private assessment bank stays in SQLite.`);
