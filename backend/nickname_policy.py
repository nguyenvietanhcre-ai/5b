"""A shared, conservative nickname policy for student-facing identities.

The data is mirrored in the browser with a parity check. Existing records are
masked when read; this module never changes stored student identities.
"""
import json
import re
import unicodedata
from pathlib import Path


POLICY = json.loads(Path(__file__).with_name('nickname-policy.json').read_text(encoding='utf-8'))


def normalize_nickname(value):
    value = unicodedata.normalize('NFKC', value)
    value = ''.join(str(unicodedata.decimal(char)) if char.isdecimal() else char for char in value)
    return unicodedata.normalize('NFC', ' '.join(value.split()))


def _fold(value):
    return ''.join(char for char in unicodedata.normalize('NFD', value.lower().replace('đ', 'd'))
                   if not unicodedata.category(char).startswith('M'))


def _word_pattern(word):
    return r'(?<![a-z])' + r'[ _-]*'.join(map(re.escape, word)) + r'(?![a-z])'


_BAD_PATTERN = re.compile('|'.join(_word_pattern(word) for word in
    POLICY['blockedWords'] + [word.replace(' ', '') for word in POLICY['blockedPhrases']] + POLICY['blockedCompacts']))
_ACCENTED_PATTERN = re.compile('|'.join(r'[ _-]*'.join(map(re.escape, word))
    for word in POLICY['blockedAccentedWords']))
_LEET = str.maketrans(POLICY['leet'])
_ALLOWED = set(POLICY['allowedWords'])


def nickname_error(value):
    if not isinstance(value, str):
        return POLICY['messages']['format']
    normalized = normalize_nickname(value)
    folded = _fold(normalized)
    digit_count = sum(char.isdecimal() for char in normalized)
    numeric_run = 0
    for token in re.findall(r'[a-z]+|[0-9]+', folded):
        if token.isascii() and token.isdecimal():
            numeric_run += len(token)
        elif token in POLICY['numberWords']:
            numeric_run += 1
        else:
            numeric_run = 0
        if numeric_run > POLICY['maxDigits']:
            return POLICY['messages']['phone']
    if digit_count > POLICY['maxDigits'] or (digit_count and not any(char.isalpha() for char in normalized)):
        return POLICY['messages']['phone']
    # Preserve complete benign words before looking for unmistakable accented
    # profanity inside concatenated nicknames (lồng versus lồn, for example).
    lower = normalized.lower()
    text = re.sub(r'[^\W\d_]+', lambda match: 'safe' if match.group() in _ALLOWED else match.group(), lower)
    if _ACCENTED_PATTERN.search(text):
        return POLICY['messages']['inappropriate']
    folded = _fold(text)
    if _BAD_PATTERN.search(folded) or _BAD_PATTERN.search(folded.translate(_LEET)):
        return POLICY['messages']['inappropriate']
    if (any(unicodedata.category(char).startswith('C') for char in value)
            or not POLICY['minLength'] <= len(normalized) <= POLICY['maxLength']
            or not re.search('[a-z]', _fold(normalized))
            or any(char not in ' _-' and not char.isdecimal()
                   and not (char.isalpha() and re.fullmatch('[a-z]', _fold(char))) for char in normalized)):
        return POLICY['messages']['format']
    return ''


def validate_nickname(value):
    error = nickname_error(value)
    if error:
        raise ValueError(error)
    return normalize_nickname(value)


def safe_nickname(value):
    return POLICY['fallback'] if nickname_error(value) else normalize_nickname(value)
