'use strict';
// Keep this policy data in sync with backend/nickname-policy.json.
const NicknamePolicy = (() => {
    const policy = {
    "version": 1,
    "minLength": 2,
    "maxLength": 40,
    "maxDigits": 6,
    "fallback": "Bạn học",
    "blockedWords": [
        "dit",
        "deo",
        "cc",
        "dcm",
        "dm",
        "dkm",
        "dmm",
        "cmm",
        "clm",
        "vcl",
        "vkl",
        "vl",
        "fuck",
        "fucking",
        "shit",
        "bitch",
        "asshole",
        "dick",
        "pussy",
        "cunt",
        "porn",
        "sex",
        "xxx"
    ],
    "blockedPhrases": [
        "dit me",
        "dit ma",
        "du me",
        "du ma",
        "con cac",
        "cai lon",
        "an cut",
        "do ngu",
        "thang ngu",
        "con ngu",
        "cho chet",
        "mat day",
        "khon nan",
        "loz",
        "lolz",
        "nigga",
        "nigger"
    ],
    "blockedCompacts": [
        "ditme",
        "ditma",
        "dume",
        "duma",
        "concac",
        "cailon",
        "ancut",
        "dongu",
        "thangngu",
        "conngu",
        "chochet",
        "matday",
        "khonnan"
    ],
    "numberWords": {
        "khong": "0",
        "linh": "0",
        "le": "0",
        "mot": "1",
        "hai": "2",
        "ba": "3",
        "bon": "4",
        "tu": "4",
        "nam": "5",
        "lam": "5",
        "sau": "6",
        "bay": "7",
        "tam": "8",
        "chin": "9"
    },
    "leet": {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "!": "i"
    },
    "blockedAccentedWords": [
        "đụ",
        "đĩ",
        "địt",
        "lồn",
        "cặc",
        "buồi",
        "cứt",
        "đéo"
    ],
    "allowedWords": [
        "đèo",
        "dẻo",
        "lồng",
        "đĩa",
        "đụng",
        "đụn"
    ],
    "messages": {
        "format": "Biệt danh cần 2–40 ký tự, có chữ cái; chỉ dùng chữ, số, dấu cách, gạch ngang hoặc gạch dưới.",
        "phone": "Biệt danh không được chứa số điện thoại hoặc từ 7 chữ số trở lên. Em hãy chọn tên khác để giữ riêng tư.",
        "inappropriate": "Biệt danh có từ ngữ chưa phù hợp. Em hãy chọn một tên thân thiện khác."
    }
};
    const help = 'Chọn biệt danh thân thiện, từ 2–40 ký tự và có chữ cái. Không dùng số điện thoại hoặc thông tin liên hệ.';
    const decimal = char => /^\p{Nd}$/u.test(char);
    const letter = char => /^\p{L}$/u.test(char);
    function normalize(value) {
        return [...value.normalize('NFKC')].map(char => {
            if (!decimal(char)) return char;
            const code = char.codePointAt(0);
            let start = code;
            while (decimal(String.fromCodePoint(start - 1))) start--;
            return String((code - start) % 10);
        }).join('').trim().replace(/\s+/gu, ' ').normalize('NFC');
    }
    const fold = value => value.toLowerCase().replaceAll('đ','d').normalize('NFD').replace(/\p{M}/gu,'');
    const quote = value => value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const spaced = value => [...value].map(quote).join('[ _-]*');
    const blocked = new RegExp([...policy.blockedWords,...policy.blockedPhrases.map(w=>w.replaceAll(' ','')),...policy.blockedCompacts].map(w=>'(?<![a-z])'+spaced(w)+'(?![a-z])').join('|'));
    const accented = new RegExp(policy.blockedAccentedWords.map(spaced).join('|'),'u');
    function error(value) {
        if (typeof value !== 'string') return policy.messages.format;
        const normalized = normalize(value), folded = fold(normalized);
        const digitCount = [...normalized].filter(decimal).length;
        let run = 0;
        for (const token of folded.match(/[a-z]+|[0-9]+/g) || []) {
            if (/^[0-9]+$/.test(token)) run += token.length;
            else if (Object.hasOwn(policy.numberWords,token)) run++;
            else run = 0;
            if (run > policy.maxDigits) return policy.messages.phone;
        }
        if (digitCount > policy.maxDigits || (digitCount && ![...normalized].some(letter))) return policy.messages.phone;
        const lower = normalized.toLowerCase();
        const text = lower.replace(/\p{L}+/gu, word => policy.allowedWords.includes(word) ? 'safe' : word);
        if (accented.test(text)) return policy.messages.inappropriate;
        const plain = fold(text), leet = [...plain].map(char=>policy.leet[char] || char).join('');
        if (blocked.test(plain) || blocked.test(leet)) return policy.messages.inappropriate;
        const length = [...normalized].length;
        if (/\p{C}/u.test(value) || length < policy.minLength || length > policy.maxLength || !/[a-z]/.test(folded) ||
            [...normalized].some(char=>!(' _-'.includes(char) || decimal(char) || (letter(char) && /^[a-z]$/.test(fold(char)))))) return policy.messages.format;
        return '';
    }
    const safe = value => error(value) ? policy.fallback : normalize(value);
    return Object.freeze({policy,help,normalize,error,safe});
})();
if (typeof module !== 'undefined') module.exports = NicknamePolicy;
