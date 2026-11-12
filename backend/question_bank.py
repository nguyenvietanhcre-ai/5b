"""Private, self-authored sample questions instantiated once in each database.

Public assets contain an independent offline demo. Instantiated answers are not
stored in the public repository. These samples are not an approved examination
syllabus; each item carries an explicit sample label in its review metadata.
"""
import json
import math
import secrets
from fractions import Fraction


BANK_VERSION = 2
MARKER = 'private_question_bank'
SAMPLE_LABEL = 'Mẫu tự biên soạn'


def _packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _number(value):
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else f'{value.numerator}/{value.denominator}'


def _decimal(cents):
    whole, remainder = divmod(cents, 100)
    return str(whole) if remainder == 0 else f'{whole},{remainder:02d}'.rstrip('0')


def _options(answer, rng):
    if answer in ('<', '=', '>'):
        return rng.sample(['<', '=', '>'], 3)
    value = Fraction(answer)
    candidates = {value}
    step = Fraction(1, value.denominator) if value.denominator != 1 else Fraction(1)
    for offset in (1, 2, -1, 3, -2, 4):
        item = value + step * offset
        if item >= 0:
            candidates.add(item)
        if len(candidates) == 4:
            break
    return rng.sample([_number(item) for item in sorted(candidates)], 4)


def sample_problem(grade, topic, difficulty, variant, rng=None):
    """Compose grade-bounded arithmetic/word problems, never from a client seed."""
    rng = rng or secrets.SystemRandom()
    a = rng.randint(2, 8 if grade == 1 else 24 if grade == 2 else 80)
    b = rng.randint(1, 5 if grade == 1 else 9)
    c = rng.randint(1, 4 if grade == 1 else 8)
    steps = []
    if topic == 'decimal':
        unit = 10 if difficulty == 0 else 1
        left = rng.randint(20, 950) // unit * unit
        delta = (-unit, 0, unit)[variant % 3]
        if difficulty < 2:
            right = left + delta
            text = f'Điền dấu thích hợp: {_decimal(left)} … {_decimal(right)}.'
            if delta == 0:
                equal_text = _decimal(right) + ('0' if right % 100 else ',0')
                text = f'Điền dấu thích hợp: {_decimal(left)} … {equal_text}.'
            steps = ['So sánh phần nguyên, rồi lần lượt từng hàng sau dấu phẩy.']
        elif difficulty == 2:
            extra = rng.randint(11, 99)
            right = left + extra + delta
            text = f'Điền dấu thích hợp: ({_decimal(left)} + {_decimal(extra)}) … {_decimal(right)}.'
            steps = [f'Tổng bên trái là {_decimal(left)} + {_decimal(extra)} = {_decimal(left + extra)}.']
            left += extra
        else:
            factor, reduction = rng.randint(2, 4), rng.randint(1, min(19, left))
            right = left * factor - reduction + delta
            text = f'Điền dấu thích hợp: ({_decimal(left)} × {factor} − {_decimal(reduction)}) … {_decimal(right)}.'
            steps = [f'Tính tích trước: {_decimal(left)} × {factor} = {_decimal(left * factor)}.',
                     f'Bên trái bằng {_decimal(left * factor)} − {_decimal(reduction)} = {_decimal(left * factor - reduction)}.']
            left = left * factor - reduction
        answer = '<' if left < right else '>' if left > right else '='
        steps.append(f'Vậy dấu cần điền là {answer}.')
    elif topic == 'fraction':
        d = rng.choice([8, 10, 12, 16, 20, 24])
        numerator = rng.randint(1, d // 3)
        other = rng.randint(1, d // 3)
        if difficulty == 0:
            answer = Fraction(numerator + other, d)
            text = f'Tính {numerator}/{d} + {other}/{d}.'
            steps = [f'Hai phân số cùng mẫu: cộng tử số {numerator} + {other} = {numerator + other}, giữ mẫu {d}.',
                     f'Rút gọn được {_number(answer)}.']
        elif difficulty == 1:
            answer = 1 - Fraction(numerator + other, d)
            text = f'Tính 1 − {numerator}/{d} − {other}/{d}.'
            steps = [f'Viết 1 = {d}/{d}.', f'Tử số còn lại là {d} − {numerator} − {other} = {d - numerator - other}.',
                     f'Kết quả rút gọn là {_number(answer)}.']
        elif difficulty == 2:
            denominator = rng.choice([3, 4, 5, 6])
            answer = Fraction(numerator, d) + Fraction(1, denominator)
            common = math.lcm(d, denominator)
            text = f'Tính {numerator}/{d} + 1/{denominator}.'
            steps = [f'Chọn mẫu số chung {common}.',
                     f'Cộng hai tử số sau quy đồng: {numerator * (common // d)} + {common // denominator} = {int(answer * common)}.',
                     f'Rút gọn được {_number(answer)}.']
        else:
            d1, d2 = rng.choice([(2, 4), (3, 6), (4, 8), (3, 4), (5, 10)])
            length = math.lcm(d1, d2) * rng.randint(3, 18)
            first, second = length // d1, length // d2
            answer = length - first - second
            text = f'Dải ruy băng dài {length} cm. Lần đầu cắt {1}/{d1} dải ban đầu, lần sau cắt {1}/{d2} dải ban đầu. Còn lại bao nhiêu cm?'
            steps = [f'Lần đầu cắt {length} : {d1} = {first} (cm).',
                     f'Lần sau cắt {length} : {d2} = {second} (cm).',
                     f'Còn lại {length} − {first} − {second} = {answer} (cm).']
        answer = _number(answer)
    elif topic == 'percent':
        base = rng.randint(4, 36) * 400
        percent = rng.choice([10, 20, 25, 50])
        part = base * percent // 100
        if difficulty == 0:
            answer = part
            text = f'Tìm {percent}% của {base}.'
            steps = [f'Giá trị cần tìm là {base} × {percent} : 100 = {answer}.']
        elif difficulty == 1:
            answer = base - part
            text = f'Thư viện có {base} quyển sách, đã cho mượn {percent}% số sách. Còn bao nhiêu quyển chưa cho mượn?'
            steps = [f'Đã cho mượn {base} × {percent} : 100 = {part} (quyển).',
                     f'Chưa cho mượn {base} − {part} = {answer} (quyển).']
        elif difficulty == 2:
            answer = base
            text = f'{percent}% số cây trong vườn là {part} cây. Vườn có tất cả bao nhiêu cây?'
            steps = [f'1% số cây là {part} : {percent} = {Fraction(part, percent)} (cây).',
                     f'Tất cả có {part} : {percent} × 100 = {base} (cây).']
        else:
            second_percent = rng.choice([20, 25, 50])
            remainder = base - part
            second = remainder * second_percent // 100
            answer = remainder - second
            text = f'Kho có {base} kg gạo. Lần đầu bán {percent}% số gạo ban đầu; lần sau bán {second_percent}% số gạo còn lại. Kho còn bao nhiêu kg gạo?'
            steps = [f'Sau lần đầu còn {base} − {base} × {percent} : 100 = {remainder} (kg).',
                     f'Lần sau bán {remainder} × {second_percent} : 100 = {second} (kg).',
                     f'Cuối cùng còn {remainder} − {second} = {answer} (kg).']
    elif topic in ('area', 'perimeter'):
        width = rng.randint(4, 25)
        length = width + rng.randint(2, 24)
        perimeter = (length + width) * 2
        if topic == 'area':
            if difficulty == 0:
                answer = length * width
                text = f'Mảnh vườn hình chữ nhật dài {length} m, rộng {width} m. Diện tích bằng bao nhiêu m²?'
                steps = [f'Diện tích là {length} × {width} = {answer} (m²).']
            elif difficulty == 1:
                answer = length * width
                text = f'Hình chữ nhật có chu vi {perimeter} cm và chiều rộng {width} cm. Tính diện tích theo cm².'
                steps = [f'Nửa chu vi là {perimeter} : 2 = {length + width} (cm).',
                         f'Chiều dài là {length + width} − {width} = {length} (cm).',
                         f'Diện tích là {length} × {width} = {answer} (cm²).']
            elif difficulty == 2:
                answer = perimeter
                text = f'Hình chữ nhật có diện tích {length * width} cm², rộng {width} cm. Chu vi bằng bao nhiêu cm?'
                steps = [f'Chiều dài là {length * width} : {width} = {length} (cm).',
                         f'Chu vi là ({length} + {width}) × 2 = {perimeter} (cm).']
            else:
                border = rng.randint(1, min(3, (width - 1) // 2))
                answer = (length - border * 2) * (width - border * 2)
                text = f'Vườn hình chữ nhật dài {length} m, rộng {width} m. Làm lối đi rộng {border} m sát bốn cạnh, ở bên trong vườn. Diện tích phần trồng cây còn lại là bao nhiêu m²?'
                steps = [f'Mỗi kích thước giảm hai lần bề rộng lối đi: {border} × 2 = {border * 2} (m).',
                         f'Phần trồng cây dài {length - border * 2} m và rộng {width - border * 2} m.',
                         f'Diện tích còn lại là {length - border * 2} × {width - border * 2} = {answer} (m²).']
        elif difficulty == 0:
            answer = perimeter
            text = f'Hình chữ nhật dài {length} cm, rộng {width} cm. Tính chu vi theo cm.'
            steps = [f'Chu vi là ({length} + {width}) × 2 = {answer} (cm).']
        elif difficulty == 1:
            answer = width
            text = f'Hình chữ nhật có chu vi {perimeter} cm, dài {length} cm. Chiều rộng bằng bao nhiêu cm?'
            steps = [f'Nửa chu vi là {perimeter} : 2 = {length + width} (cm).',
                     f'Chiều rộng là {length + width} − {length} = {width} (cm).']
        elif difficulty == 2:
            extra = rng.randint(1, 8)
            answer = (length + width + extra) * 2
            text = f'Hình chữ nhật dài {length} cm, rộng {width} cm. Tăng chiều dài thêm {extra} cm, giữ chiều rộng. Chu vi mới bằng bao nhiêu cm?'
            steps = [f'Chiều dài mới là {length} + {extra} = {length + extra} (cm).',
                     f'Chu vi mới là ({length + extra} + {width}) × 2 = {answer} (cm).']
        else:
            answer = width
            difference = length - width
            text = f'Hình chữ nhật có chu vi {perimeter} cm. Chiều dài hơn chiều rộng {difference} cm. Chiều rộng bằng bao nhiêu cm?'
            steps = [f'Tổng chiều dài và chiều rộng là {perimeter} : 2 = {length + width} (cm).',
                     f'Bớt phần hơn của chiều dài, được hai lần chiều rộng: {length + width} − {difference} = {width * 2} (cm).',
                     f'Chiều rộng là {width * 2} : 2 = {width} (cm).']
    elif topic == 'compare':
        left = rng.randint(1, 19)
        delta = (-1, 0, 1)[variant % 3]
        right = max(0, min(20, left + delta))
        if difficulty == 0:
            text = f'Điền dấu thích hợp: {left} … {right}.'
        elif difficulty == 1:
            part = rng.randint(0, left)
            text = f'Điền dấu thích hợp: ({part} + {left - part}) … {right}.'
        elif difficulty == 2:
            large = rng.randint(left, 20)
            text = f'Điền dấu thích hợp: ({large} − {large - left}) … {right}.'
        else:
            part = rng.randint(0, left)
            right_part = rng.randint(0, right)
            text = f'Điền dấu thích hợp: ({part} + {left - part}) … ({right_part} + {right - right_part}).'
        answer = '<' if left < right else '>' if left > right else '='
        steps = [f'Tính từng vế được {left} và {right}.', f'Vậy dấu cần điền là {answer}.']
    elif topic == 'missing':
        a = rng.randint(1, 10 if grade == 1 else 70)
        b = rng.randint(1, 5 if grade == 1 else 25)
        if grade == 1:
            c = min(c, a + b)
        if difficulty == 0:
            answer = a
            text = f'Tìm số điền vào ô trống: □ + {b} = {a + b}.'
            steps = [f'Số hạng chưa biết là {a + b} − {b} = {a}.']
        elif difficulty == 1:
            answer = b
            text = f'Tìm số điền vào ô trống: {a + b} − □ = {a}.'
            steps = [f'Số bị bớt đi là {a + b} − {a} = {b}.']
        elif difficulty == 2:
            if grade == 1:
                answer = a
                text = f'Một số được cộng {b} rồi bớt {c} thì còn {a + b - c}. Số ban đầu là bao nhiêu?'
                steps = [f'Trước khi bớt {c}, có {a + b - c} + {c} = {a + b}.', f'Số ban đầu là {a + b} − {b} = {a}.']
            else:
                answer = a
                text = f'Một số được cộng {b} rồi nhân {c} thì được {(a + b) * c}. Tìm số ban đầu.'
                steps = [f'Trước khi nhân, có {(a + b) * c} : {c} = {a + b}.', f'Số ban đầu là {a + b} − {b} = {a}.']
        else:
            answer = a
            if grade == 1:
                extra = rng.randint(1, 3)
                result = a + b - c + extra
                text = f'Một số được cộng {b}, bớt {c}, rồi cộng {extra} thì được {result}. Số ban đầu là bao nhiêu?'
                steps = [f'Lần ngược: {result} − {extra} = {a + b - c}.',
                         f'Trước khi bớt: {a + b - c} + {c} = {a + b}.',
                         f'Số ban đầu là {a + b} − {b} = {a}.']
            else:
                factor = rng.randint(2, 5)
                result = (a + b) * factor - c
                text = f'Một số được cộng {b}, nhân {factor}, rồi bớt {c} thì được {result}. Số ban đầu là bao nhiêu?'
                steps = [f'Lần ngược: {result} + {c} = {(a + b) * factor}.',
                         f'Trước khi nhân: {(a + b) * factor} : {factor} = {a + b}.',
                         f'Số ban đầu là {a + b} − {b} = {a}.']
    elif topic in ('multiply', 'divide'):
        a = rng.randint(2, 9) if grade == 2 else rng.randint(12, 89) if grade == 3 else rng.randint(21, 180)
        b = rng.randint(2, 9)
        if topic == 'multiply':
            if difficulty == 0:
                answer = a * b
                text = f'Tính {a} × {b}.'
                steps = [f'{a} × {b} = {answer}.']
            elif difficulty == 1:
                answer = a * b
                text = f'Mỗi hộp có {a} chiếc bút. Có {b} hộp như vậy. Có tất cả bao nhiêu chiếc bút?'
                steps = [f'{b} hộp có {a} × {b} = {answer} (chiếc bút).']
            elif difficulty == 2:
                answer = a * b + c
                text = f'Có {b} hộp, mỗi hộp {a} chiếc bút, và {c} chiếc bút rời. Có tất cả bao nhiêu chiếc bút?'
                steps = [f'Trong các hộp có {a} × {b} = {a * b} (chiếc).', f'Tất cả có {a * b} + {c} = {answer} (chiếc).']
            else:
                sold = rng.randint(1, b - 1)
                answer = (b - sold) * a + c
                text = f'Có {b} hộp bánh, mỗi hộp {a} cái, và {c} cái bánh rời. Bán {sold} hộp nguyên. Còn bao nhiêu cái bánh?'
                steps = [f'Còn {b} − {sold} = {b - sold} (hộp).', f'Bánh trong hộp còn {(b - sold)} × {a} = {(b - sold) * a} (cái).', f'Tính cả bánh rời: {(b - sold) * a} + {c} = {answer} (cái).']
        elif difficulty == 0:
            answer = a
            text = f'Tính {a * b} : {b}.'
            steps = [f'Vì {a} × {b} = {a * b}, nên thương là {a}.']
        elif difficulty == 1:
            answer = a
            text = f'Chia đều {a * b} quyển vở cho {b} bạn. Mỗi bạn được bao nhiêu quyển vở?'
            steps = [f'Mỗi bạn được {a * b} : {b} = {a} (quyển).']
        elif difficulty == 2:
            answer = a
            text = f'Có {a * b + c} viên bi, lấy riêng {c} viên rồi chia đều phần còn lại vào {b} túi. Mỗi túi có bao nhiêu viên?'
            steps = [f'Phần đem chia là {a * b + c} − {c} = {a * b} (viên).', f'Mỗi túi có {a * b} : {b} = {a} (viên).']
        else:
            if grade == 2:
                b = min(b, 7)
            extra_groups = rng.randint(1, 9 - b) if grade == 2 else rng.randint(1, 4)
            answer = a * (b + extra_groups)
            text = f'Chia đều {a * b} viên bi vào {b} túi. Muốn có {b + extra_groups} túi với số bi mỗi túi như cũ thì cần tất cả bao nhiêu viên?'
            steps = [f'Mỗi túi có {a * b} : {b} = {a} (viên).', f'{b + extra_groups} túi cần {a} × {b + extra_groups} = {answer} (viên).']
    elif topic in ('add', 'subtract'):
        if grade == 2:
            a = rng.randint(11, 65)
            b = rng.randint(2, min(24, 95 - a))
            c = rng.randint(1, min(8, 100 - a - b))
        elif grade == 1:
            c = min(c, a + b)
        if topic == 'add':
            if difficulty == 0:
                answer = a + b
                text = f'Tính {a} + {b}.'
                steps = [f'{a} + {b} = {answer}.']
            elif difficulty == 1:
                answer = a + b
                text = f'Lan có {a} nhãn vở, được tặng thêm {b} nhãn vở. Lan có tất cả bao nhiêu nhãn vở?'
                steps = [f'Tất cả có {a} + {b} = {answer} (nhãn vở).']
            elif difficulty == 2:
                answer = a + b + c
                text = f'Tính {a} + {b} + {c}.'
                steps = [f'Cộng hai số đầu: {a} + {b} = {a + b}.', f'Cộng tiếp: {a + b} + {c} = {answer}.']
            else:
                answer = a + b - c
                text = f'Giỏ có {a} quả cam, thêm {b} quả rồi lấy ra {c} quả. Giỏ còn bao nhiêu quả cam?'
                steps = [f'Sau khi thêm, có {a} + {b} = {a + b} (quả).', f'Sau khi lấy ra, còn {a + b} − {c} = {answer} (quả).']
        else:
            total = a + b + c
            if difficulty == 0:
                answer = a + c
                text = f'Tính {total} − {b}.'
                steps = [f'{total} − {b} = {answer}.']
            elif difficulty == 1:
                answer = a + c
                text = f'Có {total} quyển vở, đã dùng {b} quyển. Còn lại bao nhiêu quyển vở?'
                steps = [f'Còn lại {total} − {b} = {answer} (quyển).']
            elif difficulty == 2:
                answer = a
                text = f'Tính {total} − {b} − {c}.'
                steps = [f'{total} − {b} = {a + c}.', f'{a + c} − {c} = {answer}.']
            else:
                answer = b
                text = f'Có {total} bông hoa, tặng lần đầu {c} bông, lần sau tặng thêm một số bông thì còn {a} bông. Lần sau đã tặng bao nhiêu bông?'
                steps = [f'Sau lần đầu còn {total} − {c} = {a + b} (bông).', f'Lần sau tặng {a + b} − {a} = {b} (bông).']
    else:
        raise ValueError('Unknown sample question topic')
    answer = str(answer)
    return {'text': text, 'answer': answer, 'options': _options(answer, rng), 'steps': steps,
            'difficulty': difficulty, 'grade': grade, 'topic': topic, 'sampleLabel': SAMPLE_LABEL}


def seed_question_bank(db, catalog):
    """Keep old history, retire leaked seeds once, never republish admin withdrawals."""
    if db.execute('SELECT 1 FROM system_settings WHERE name=?', (MARKER,)).fetchone():
        return
    rng = secrets.SystemRandom()
    seen = {(lesson['grade'], lesson['example']['text']) for lesson in catalog['lessons'] if lesson.get('example')}
    seeded = 0
    for lesson in catalog['lessons']:
        grade, topic = lesson['grade'], lesson['topic']
        topic_id = db.execute('SELECT id FROM topics WHERE grade_id=? AND client_key=?', (grade, topic)).fetchone()[0]
        for difficulty in range(4):
            for variant in range(12):
                legacy = f'BANK-{grade}-{topic}-{difficulty}-{variant}'
                # Version 1 was generated by the old public browser recipes.
                # Preserve genuinely edited teacher versions under the same
                # question identity; retire unchanged copies of exposed work.
                db.execute("UPDATE question_versions SET status='retired' WHERE question_id IN "
                    '(SELECT id FROM questions WHERE question_code=?) AND (revision=1 OR EXISTS '
                    '(SELECT 1 FROM question_versions leaked WHERE leaked.question_id=question_versions.question_id '
                    'AND leaked.revision=1 AND leaked.prompt_json=question_versions.prompt_json '
                    "AND json_extract(leaked.grading_rule_json,'$.answer')=json_extract(question_versions.grading_rule_json,'$.answer')))", (legacy,))
                for attempt in range(2000):
                    question = sample_problem(grade, topic, difficulty, variant, rng)
                    if (grade, question['text']) not in seen:
                        break
                else:
                    raise ValueError('Not enough distinct self-authored sample questions')
                seen.add((grade, question['text']))
                identity = db.execute('INSERT INTO questions(grade_id,topic_id,question_code) VALUES (?,?,?)',
                    (grade, topic_id, 'BANK2-' + secrets.token_hex(16).upper())).lastrowid
                db.execute('INSERT INTO question_versions(question_id,revision,difficulty,curriculum_week,prompt_json,'
                    'grading_rule_json,solution_steps_json,hints_json,status,options_json) VALUES (?,1,?,?,?,?,?,?,\'published\',?)',
                    (identity, difficulty + 1, lesson['week'], _packed([{'type':'text','text':question['text']}]),
                     _packed({'answer':question['answer']}), _packed([{'type':'text','text':value} for value in question['steps']]),
                     _packed([{'type':'text','text':lesson['theory']}, {'type':'text','text':SAMPLE_LABEL}]), _packed(question['options'])))
                seeded += 1
    db.execute('INSERT INTO system_settings(name,value_json,updated_at) VALUES (?,?,strftime(\'%Y-%m-%dT%H:%M:%SZ\',\'now\'))',
               (MARKER, _packed({'version':BANK_VERSION, 'sample':True, 'seededCount':seeded})))


def published_version_ids(db, grade, difficulty, max_week=35, topic='', exact_week=None):
    """The shared exam/Arena source, using the latest currently published version."""
    return [row[0] for row in db.execute('SELECT v.id FROM questions q JOIN question_versions v ON v.question_id=q.id '
        "JOIN topics t ON t.id=q.topic_id WHERE q.grade_id=? AND v.status='published' "
        'AND (? IS NULL OR v.difficulty=?) AND v.curriculum_week<=? AND t.client_key IS NOT NULL '
        "AND (?='' OR t.client_key=?) AND (? IS NULL OR v.curriculum_week=?) "
        "AND v.revision=(SELECT max(latest.revision) FROM question_versions latest WHERE latest.question_id=q.id AND latest.status='published')",
        (grade, difficulty, difficulty, max_week, topic, topic, exact_week, exact_week))]


def arena_questions(db, grade, difficulty, scope='weekly', max_week=35):
    from .arena import ArenaError
    levels = (1, 2) if difficulty == 0 else (min(4, difficulty + 1),)
    ids = []
    for level in levels:
        ids.extend(published_version_ids(db, grade, level, max_week if scope == 'weekly' else 35))
    rng = secrets.SystemRandom()
    if len(ids) < 20:
        raise ArenaError('Chưa đủ câu hỏi đã phát hành cho trận đấu. Thầy cô cần bổ sung ngân hàng câu hỏi.', 503)
    rows = []
    for identity in rng.sample(ids, 20):
        row = db.execute('SELECT v.*,q.question_code,t.title topic_title FROM question_versions v JOIN questions q ON q.id=v.question_id '
                         'JOIN topics t ON t.id=q.topic_id WHERE v.id=?', (identity,)).fetchone()
        text = ' '.join(block.get('text', '') for block in json.loads(row['prompt_json']) if block.get('type') == 'text')
        options = [str(value) for value in json.loads(row['options_json'])]
        answer = str(json.loads(row['grading_rule_json']).get('answer', ''))
        if not text or answer not in options or len(set(options)) < 2:
            raise ArenaError('Có câu hỏi chưa đủ dữ liệu cho Đấu trí. Thầy cô cần kiểm tra câu hỏi đã phát hành.', 503)
        rows.append({'id':str(identity), 'questionVersionId':identity, 'text':text, 'answer':answer,
            'options':rng.sample(options, len(options)), 'difficulty':row['difficulty'] - 1,
            'steps':[block.get('text','') for block in json.loads(row['solution_steps_json']) if block.get('type') == 'text'],
            'topicTitle':row['topic_title'],
            **({'sampleLabel':SAMPLE_LABEL} if row['question_code'].startswith('BANK2-') else {})})
    return rows
