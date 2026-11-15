"""Bounded, exact short-answer comparison; never evaluate student expressions."""
import re
import unicodedata

from .content import parse_number

MAX_ANSWER = 500
KINDS = ('auto', 'number', 'text', 'ordered', 'unordered')


def clean(value):
    return unicodedata.normalize('NFKC', str(value)).strip().replace('−', '-')


def number(value):
    value = clean(value)
    if not re.fullmatch(r'[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?(?:\s*/\s*[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?)?', value):
        return None
    return parse_number(value)


def scalar_equal(actual, expected, kind='auto'):
    if kind != 'text':
        expected_number = number(expected)
        if expected_number is not None:
            actual_number = number(actual)
            return actual_number is not None and actual_number == expected_number
        if kind == 'number':
            return False
    return clean(actual) == clean(expected)


def matches(actual, rule):
    if not isinstance(actual, str) or not actual.strip() or len(actual) > MAX_ANSWER:
        return False
    expected = rule.get('answer', '')
    kind = rule.get('answerKind', 'auto')
    if kind in ('ordered', 'unordered'):
        left, right = actual.split(';'), str(expected).split(';')
        if len(left) != len(right) or len(left) > 20:
            return False
        if kind == 'ordered':
            return all(scalar_equal(a, b) for a, b in zip(left, right))
        remaining = list(right)
        for value in left:
            found = next((i for i, item in enumerate(remaining) if scalar_equal(value, item)), None)
            if found is None:
                return False
            remaining.pop(found)
        return True
    return scalar_equal(actual, expected, kind)


def validate_rule(answer, kind='auto'):
    if kind not in KINDS or not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER:
        raise ValueError('Đáp án hoặc kiểu đáp án không hợp lệ.')
    if kind == 'number' and number(answer) is None:
        raise ValueError('Nhập đáp án số hoặc phân số hợp lệ, không kèm đơn vị.')
    if kind in ('ordered', 'unordered'):
        parts = answer.split(';')
        if not 2 <= len(parts) <= 20 or any(not part.strip() for part in parts):
            raise ValueError('Các đáp án cần ngăn cách bằng dấu chấm phẩy (;), tối đa 20 giá trị.')
    return {'answer':answer.strip(), 'answerKind':kind}


def requires_choice(question):
    """Structural author metadata, never infer a mathematical answer from prose."""
    if question.get('answerShape') in ('parts', 'objects', 'solutions'):
        return True
    if question.get('answerKind') in ('ordered', 'unordered'):
        return True
    if question.get('multipleAnswers') is True:
        return True
    for key in ('partCount', 'objectCount', 'answerCount'):
        if type(question.get(key)) is int and question[key] > 1:
            return True
    guide = question.get('inputGuide')
    labels = question.get('answerTargets', guide.get('labels', []) if isinstance(guide, dict) else [])
    if isinstance(labels, list) and len(labels) > 1:
        return True
    prompt = question.get('prompt', '')
    if isinstance(prompt, str):
        markers = set(re.findall(r'(?<!\w)([a-d])\)\s', prompt.lower()))
        return 'a' in markers and 'b' in markers
    return False


def response_mode(rule, fallback='typed'):
    return 'choice' if fallback == 'choice' or rule.get('responseType') == 'choice' else 'typed'


def question_correct(question, answer):
    rule = question.get('gradingRule', {'answer':question.get('answer', '')})
    if question.get('responseMode') == 'choice':
        return isinstance(answer, str) and answer == str(rule['answer'])
    return matches(answer, rule)


def validate_choices(answer, options, rationales, targets=None):
    if not isinstance(options, list) or len(options) != 4 or any(not isinstance(o, str) or not o.strip() or len(o) > MAX_ANSWER for o in options):
        raise ValueError('Nhập đúng 4 phương án đầy đủ, mỗi phương án tối đa 500 ký tự.')
    if answer not in options or len({clean(o) for o in options}) != 4:
        raise ValueError('Bốn phương án phải khác nhau và có đúng một phương án khớp đáp án chuẩn.')
    # Equivalent numeric strings cannot masquerade as different answers.
    for i, left in enumerate(options):
        for right in options[i+1:]:
            if scalar_equal(left, right):
                raise ValueError('Hai phương án có giá trị tương đương; cần sửa để chỉ có một đáp án đúng.')
    if not isinstance(rationales, list) or len(rationales) != 4 or any(not isinstance(v, str) or not 12 <= len(v.strip()) <= 2000 for v in rationales):
        raise ValueError('Ghi giải thích cho cả 4 phương án; phương án sai cần nêu lỗi giải cụ thể (12–2000 ký tự).')
    if targets:
        if not isinstance(targets, list) or len(targets)>20 or any(not isinstance(t,str) or not t.strip() or len(t)>60 for t in targets):
            raise ValueError('Nhãn các ý/đối tượng không hợp lệ.')
        for option in options:
            if any(clean(label).casefold()+':' not in clean(option).casefold() for label in targets):
                raise ValueError('Mỗi phương án phải ghi đủ nhãn và kết quả dạng Nhãn: đáp số, kể cả các phương án nhiễu.')
    return options


def propose_choices(components, mistakes):
    """Compose complete bundles from supplied, explainable errors; no random numbers.

    A draft suggestion is not an independent teacher approval or a publication.
    """
    if not isinstance(components,list) or not 1 <= len(components) <= 20:
        raise ValueError('Cần các thành phần đáp án có nhãn, giá trị và đơn vị.')
    labels = [c.get('label') if isinstance(c,dict) else None for c in components]
    if any(not isinstance(v,str) or not v.strip() for v in labels) or len(set(labels))!=len(labels):
        raise ValueError('Nhãn thành phần phải rõ ràng, không trùng nhau.')
    def bundle(values):
        if not isinstance(values,list) or len(values)!=len(components) or any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError('Phương án nhiễu phải có đủ kết quả của mọi ý/đối tượng.')
        return '; '.join(f"{c['label']}: {v}{(' '+c['unit']) if c.get('unit') else ''}" for c,v in zip(components,values))
    answer=bundle([c.get('value') for c in components])
    if not isinstance(mistakes,list) or len(mistakes)!=3 or any(not isinstance(m,dict) for m in mistakes):
        raise ValueError('Cần 3 lỗi giải có lý do; không tự bù số ngẫu nhiên cho đủ phương án.')
    vectors=[[c.get('value') for c in components]]+[m.get('values') for m in mistakes]
    options=[answer]+[bundle(values) for values in vectors[1:]]
    for i,left in enumerate(vectors):
        for right in vectors[i+1:]:
            if all(scalar_equal(a,b) for a,b in zip(left,right)):
                raise ValueError('Hai phương án có cùng bộ giá trị toán học; cần lỗi giải khác để chỉ có một đáp án đúng.')
    reasons=['Đối chiếu đủ các dữ kiện và các kết quả cần tìm.']+[m.get('reason') for m in mistakes]
    validate_choices(answer,options,reasons,labels)
    return {'answer':answer,'options':options,'choiceRationales':reasons,'reviewStatus':'draft-suggestions'}
