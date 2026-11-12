'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const nicknames = require('../frontend/nickname-policy.js');
assert.deepEqual(nicknames.policy, JSON.parse(fs.readFileSync(path.join(__dirname,'../backend/nickname-policy.json'),'utf8')),
    'Browser and backend must use the same nickname policy');
const accepted = ['Mầm Xanh','Nguyễn Phúc Long','Đức Dũng','Bùi Quốc Cường','Cúc','Dung','Đăng',
    'Du','Di','Dư','Các Bạn','Lớn','Lợn','Chim Cút','Bướm','Đèo Xanh','Dẻo Thơm','Lồng Đèn','Đĩa Xinh','Đụng Tay','Đụn Rơm','Sóc_5A','Bạn-123456','Khối 5','Chim Cut'];
const inappropriate = ['ĐỊT','đụ','đĩ','lồn','cặc','buồi','cứt','đéo','đụ1','l_ồ_n','đ_ụ','D C M','d-c-m',
    'đ ị t','D1T M3','ditme','du_ma','con cac','cailon','an-cut','đồ ngu','khốn nạn','VCL','FUCK','sh1t','bitch',
    'địtcon','lồncon','cặccon','cứtcon','đụcon'];
const phones = ['0912345678','+84 912 345 678','0084-912-345-678','Linh 0912345678','09.12.34.56.78',
    '０９１２３４５６７８','٠٩١٢٣٤٥٦٧٨','Linh 123 4567','không chín một hai ba bốn năm',
    'khong chin 1 hai 3 bon 5','Linh0chin1hai3bon5','123456'];
const invalid = [null,123,[],'','A','A'.repeat(41),'１２','abc@example.com','<img src=x>',
    'Bạn\u200bhọc','Bạn\nHọc','Bạn\tHọc','Bạn\u202ehọc','Bạn😀','___'];
for (const value of accepted) {assert.equal(nicknames.error(value),'',value);assert.equal(nicknames.safe(value),value);}
for (const value of inappropriate) assert.equal(nicknames.error(value),nicknames.policy.messages.inappropriate,value);
for (const value of phones) assert.equal(nicknames.error(value),nicknames.policy.messages.phone,value);
for (const value of invalid) assert.ok(nicknames.error(value),JSON.stringify(value));
for (const value of [...inappropriate,...phones,...invalid]) assert.equal(nicknames.safe(value),'Bạn học');
assert.equal(nicknames.normalize('  Nguyễn   Phúc Long  '),'Nguyễn Phúc Long');
assert.equal(nicknames.normalize('Đức Dũng'.normalize('NFD')),'Đức Dũng');
assert.equal(nicknames.normalize('Sóc１２'),'Sóc12');
console.log('Nickname browser policy: shared data and '+(accepted.length+inappropriate.length+phones.length+invalid.length)+' cases passed');
