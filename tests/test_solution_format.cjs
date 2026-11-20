'use strict';
const assert = require('node:assert/strict');
const {render} = require('../frontend/solution-format.js');
const check = [];
function test(name, run) { run(); check.push(name); }
test('review payload has distinct original steps and emphasized answer, including zero', () => {
    const q = Object.freeze({solution: Object.freeze([{type:'text',text:'Một phần: 24 : 4 = 6 cm.'},{type:'text',text:'Dây đỏ dài 6 × 3 = 18 cm.'}]),answer:0});
    const html = render(q);
    assert.equal((html.match(/<li>/g)||[]).length,2);
    assert(html.includes('24 : 4 = 6 cm.'));
    assert(html.includes('<strong>0</strong>'));
});
test('newlines and blank paragraphs remain explicit without splitting prose or decimal punctuation', () => {
    const html = render({steps:['Bước 1: Tính 2,5 × 4 = 10. Giữ nguyên câu.\nDòng thứ hai.\n\nKiểm tra: 10 : 4 = 2,5.']});
    assert.equal((html.match(/<li>/g)||[]).length,1);
    assert.equal((html.match(/study-solution-paragraph/g)||[]).length,2);
    assert(html.includes('<br>Dòng thứ hai.'));
    assert(html.includes('2,5 × 4 = 10. Giữ nguyên câu.'));
    assert(html.includes('study-solution-key'));
});
test('HTML text and unknown tag attributes cannot execute', () => {
    const html = render({answer:'<img src=x onerror=alert(1)>',solution:[{type:'element',tag:'script',src:'javascript:alert(1)',children:[{type:'text',text:'<svg onload=alert(1)>'}]}]});
    assert(!html.includes('<script'));
    assert(!html.includes('<img'));
    assert(!html.includes('<svg'));
    assert(html.includes('&lt;svg'));
    assert(html.includes('&lt;img'));
});
test('formula and authorized media stay with preceding step and all payload stays immutable', () => {
    const q = {answer:'1/2',solution:[{type:'text',text:'Tính tổng hai phân số.'},{type:'math',latex:'1/4 + 1/4 = 1/2'},{type:'image',asset_id:7},{type:'text',text:'Đáp số: 1/2.'}]};
    const before = JSON.stringify(q),seen = [];
    const html = render(q,{renderBlocks:nodes=>{seen.push(...nodes);return '<span>safe renderer output</span>';}});
    assert.equal((html.match(/<li>/g)||[]).length,2);
    assert.deepEqual(seen,[q.solution[1],q.solution[2]]);
    assert.equal(JSON.stringify(q),before);
    assert(html.includes('solution-answer'));
});
test('rich table and emphasis retain AST order with a keyboard accessible scroll region', () => {
    const html = render({solution:[{type:'text',text:'Đối chiếu bảng.'},{type:'element',tag:'table',children:[{tag:'tbody',children:[{tag:'tr',children:[{tag:'th',children:[{type:'text',text:'Độ dài'}]},{tag:'td',children:[{tag:'strong',children:[{type:'text',text:'18 cm'}]}]}]}]}]}]});
    assert(html.indexOf('Đối chiếu bảng.')<html.indexOf('<table>'));
    assert(html.includes('<strong>18 cm</strong>'));
    assert(html.includes('tabindex="0" role="region"'));
});
test('solution preference avoids duplicating legacy steps and optional answer remains outside pilot disclosure', () => {
    const html = render({solution:[{type:'text',text:'Nguồn chính.'}],steps:['Không lặp.'],answer:'18'},{includeAnswer:false});
    assert(html.includes('Nguồn chính.'));
    assert(!html.includes('Không lặp.'));
    assert(!html.includes('study-solution-final'));
});
console.log(JSON.stringify({status:'PASS',checks:check.length,names:check}));
