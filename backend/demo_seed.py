"""Create five fictional accounts, five test cases and five rich math questions."""

import argparse
import json
import random
import sqlite3
from contextlib import closing
from pathlib import Path
from backend.database import execute_sql, initialize
from backend.rich_content import validate_blocks

DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / 'work/database/5bmath-demo.sqlite3'
DEMO_TIME = '2026-11-11T02:00:00Z'
FIRST_ID = 900001


def text(value):
    return {'type': 'text', 'text': value}


def math(latex, elements):
    return {
        'type': 'math', 'latex': latex,
        'mathml': '<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">' + elements + '</math>'
    }


def samples():
    return [
        (
            'Cộng phân số', 1,
            [text('Tính tổng hai phân số.'), math(r'\frac{3}{4}+\frac{1}{8}', '<mfrac><mn>3</mn><mn>4</mn></mfrac><mo>+</mo><mfrac><mn>1</mn><mn>8</mn></mfrac>')],
            [text('Quy đồng mẫu số rồi cộng tử số.'), math(r'\frac{6}{8}+\frac{1}{8}=\frac{7}{8}', '<mfrac><mn>6</mn><mn>8</mn></mfrac><mo>+</mo><mfrac><mn>1</mn><mn>8</mn></mfrac><mo>=</mo><mfrac><mn>7</mn><mn>8</mn></mfrac>')],
            '7/8'
        ),
        (
            'Tỉ số phần trăm', 2,
            [text('Tìm 15% của 240.')],
            [text('Nhân số đã cho với 15 rồi chia cho 100.'), math('240 \\times 15 : 100 = 36', '<mn>240</mn><mo>×</mo><mn>15</mn><mo>:</mo><mn>100</mn><mo>=</mo><mn>36</mn>')],
            '36'
        ),
        (
            'Diện tích hình chữ nhật', 2,
            [text('Tính diện tích hình chữ nhật có kích thước như hình.'), {'type': 'image', 'asset_id': FIRST_ID}],
            [text('Lấy chiều dài nhân chiều rộng.'), math('18 \\times 9 = 162 \\text{ cm}^2', '<mn>18</mn><mo>×</mo><mn>9</mn><mo>=</mo><mn>162</mn><msup><mtext> cm</mtext><mn>2</mn></msup>'), {'type': 'image', 'asset_id': FIRST_ID}],
            '162'
        ),
        (
            'Hai lần thay đổi phần trăm', 3,
            [text('Một món đồ giá 250.000 đồng tăng 10%, sau đó giảm 10%. Tính giá cuối cùng.')],
            [text('Tính lần lượt trên giá của từng giai đoạn.'), math('250000 \\times 1{,}1 \\times 0{,}9 = 247500', '<mn>250000</mn><mo>×</mo><mn>1,1</mn><mo>×</mo><mn>0,9</mn><mo>=</mo><mn>247500</mn>')],
            '247500'
        ),
        (
            'Quy luật số lẻ', 4,
            [text('Tính tổng năm số lẻ đầu tiên.'), math('1+3+5+7+9', '<mn>1</mn><mo>+</mo><mn>3</mn><mo>+</mo><mn>5</mn><mo>+</mo><mn>7</mn><mo>+</mo><mn>9</mn>')],
            [text('Tổng n số lẻ đầu tiên bằng n nhân n.'), math('1+3+5+7+9=5^2=25', '<mn>1</mn><mo>+</mo><mn>3</mn><mo>+</mo><mn>5</mn><mo>+</mo><mn>7</mn><mo>+</mo><mn>9</mn><mo>=</mo><msup><mn>5</mn><mn>2</mn></msup><mo>=</mo><mn>25</mn>')],
            '25'
        ),
    ]


def literal(value):
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + value.replace("'", "''") + "'"


def encode(value):
    return json.dumps(value, ensure_ascii=False)


def seed_sql():
    statements = []

    def insert(table, values):
        columns = ', '.join(values)
        encoded = ', '.join(literal(value) for value in values.values())
        if table == 'account_referrals':
            sql = f'INSERT INTO {table} ({columns}) SELECT {encoded} WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE id = {values["id"]});'
        else:
            sql = f'INSERT INTO {table} ({columns}) VALUES ({encoded}) ON CONFLICT DO NOTHING;'
        statements.append(sql)

    insert('academic_years', {
        'id': 2026, 'label': '2026–2027', 'grade_effective_from': '2026-07-01',
        'instruction_starts_on': '2026-09-05', 'ends_on': '2027-06-30'
    })
    for offset, name in enumerate(['An mẫu', 'Bình mẫu', 'Chi mẫu', 'Dũng mẫu', 'Em mẫu']):
        identifier = FIRST_ID + offset
        insert('accounts', {
            'id': identifier, 'account_code': f'DEMO-{offset + 1:02}',
            'login_identifier': f'demo-{offset + 1:02}@example.invalid', 'birth_year': 2016,
            'invite_code': f'DEMO-INVITE-{offset + 1:02}', 'is_demo': 1,
            'created_at': '2026-11-01T02:00:00Z',
            'vip_expires_at': '2027-01-31T02:00:00Z' if offset == 0 else None
        })
        insert('students', {
            'id': identifier, 'account_id': identifier, 'student_code': f'DEMO-HS-{offset + 1:02}',
            'full_name': name, 'grade_level': 5
        })
        insert('student_grades', {'student_id': identifier, 'academic_year_id': 2026, 'grade_id': 5})
    insert('teachers', {'id': FIRST_ID, 'full_name': 'Giáo viên mẫu', 'birth_year': 1990, 'bio': 'Dữ liệu minh họa để kiểm thử.'})
    insert('online_classes', {
        'id': FIRST_ID, 'teacher_id': FIRST_ID, 'grade_id': 5, 'academic_year_id': 2026, 'name': 'Lớp mẫu khối 5'
    })
    insert('class_enrollments', {
        'id': FIRST_ID, 'student_id': FIRST_ID + 4, 'class_id': FIRST_ID, 'joined_at': '2026-11-01T02:00:00Z'
    })
    insert('access_entitlements', {
        'id': FIRST_ID, 'account_id': FIRST_ID + 4, 'enrollment_id': FIRST_ID,
        'kind': 'internal', 'starts_at': '2026-11-01T02:00:00Z'
    })
    for offset, (inviter, invitee) in enumerate([(0, 1), (2, 3), (4, 2)]):
        insert('account_referrals', {
            'id': FIRST_ID + offset, 'inviter_account_id': FIRST_ID + inviter,
            'invitee_account_id': FIRST_ID + invitee, 'invite_code': f'DEMO-INVITE-{inviter + 1:02}',
            'registered_at': '2026-11-01T02:00:00Z'
        })

    image = Path(__file__).resolve().parent.parent / 'frontend/demo-rectangle.svg'
    insert('media_assets', {
        'id': FIRST_ID, 'storage_key': 'demo/rectangle.svg', 'url': '/demo-rectangle.svg',
        'mime_type': 'image/svg+xml', 'width': 480, 'height': 240,
        'byte_size': image.stat().st_size, 'alt_text': 'Hình chữ nhật có chiều dài 18 cm và chiều rộng 9 cm.'
    })
    for offset, (title, difficulty, prompt, solution, answer) in enumerate(samples()):
        identifier = FIRST_ID + offset
        validate_blocks(prompt)
        validate_blocks(solution)
        insert('topics', {'id': identifier, 'grade_id': 5, 'title': title})
        insert('lessons', {
            'id': identifier, 'grade_id': 5, 'topic_id': identifier, 'kind': 'topic',
            'title': title, 'body_json': encode(solution)
        })
        insert('questions', {'id': identifier, 'grade_id': 5, 'topic_id': identifier, 'question_code': f'DEMO-Q-{offset + 1:02}'})
        insert('question_versions', {
            'id': identifier, 'question_id': identifier, 'revision': 1, 'difficulty': difficulty,
            'curriculum_week': 1, 'prompt_json': encode(prompt), 'solution_steps_json': encode(solution),
            'grading_rule_json': encode({'kind': 'exact_number', 'answer': answer}),
            'status': 'published'
        })
        if offset == 2:
            insert('question_assets', {'question_version_id': identifier, 'asset_id': FIRST_ID})

    insert('exam_forms', {
        'id': FIRST_ID, 'grade_id': 5, 'form_code': 'DEMO-FORM-G5', 'version': 1,
        'purpose': 'Kiểm thử dữ liệu mẫu', 'selection_mode': 'fixed_topics', 'question_count': 5,
        'duration_minutes': 15, 'difficulty_mix_json': '[0.2,0.4,0.2,0.2]', 'required_access': 'regular'
    })
    for offset in range(5):
        insert('exam_form_topics', {'form_id': FIRST_ID, 'topic_id': FIRST_ID + offset, 'grade_id': 5, 'weight': 1})
        insert('exams', {
            'id': FIRST_ID + offset, 'exam_code': f'DEMO-EXAM-{offset + 1:02}', 'version': 1,
            'title': f'Đề mẫu {offset + 1}', 'grade_level': 5, 'duration_minutes': 15,
            'status': 'published', 'form_id': FIRST_ID, 'academic_year_id': 2026,
            'owner_student_id': FIRST_ID + offset, 'created_at': DEMO_TIME
        })
        for position, question in enumerate(random.Random(offset).sample(range(FIRST_ID, FIRST_ID + 5), 5), 1):
            insert('exam_items', {'exam_id': FIRST_ID + offset, 'position': position, 'question_version_id': question, 'max_points': 2})

    # The repeated reference and the renewal exercise two different retry paths.
    for account, reference in [(1, 'DEMO-FIRST-B'), (1, 'DEMO-FIRST-B'), (1, 'DEMO-RENEW-B'), (3, 'DEMO-FIRST-D'), (2, 'DEMO-FIRST-C')]:
        insert('vip_purchases', {'account_id': FIRST_ID + account, 'payment_ref': reference, 'months': 1, 'confirmed_at': DEMO_TIME})
    return '\n'.join(statements) + '\n'


def seed(path):
    initialize(path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        with connection:
            collision = connection.execute(
                "SELECT 1 FROM accounts WHERE id BETWEEN ? AND ? AND is_demo <> 1",
                (FIRST_ID, FIRST_ID + 4)
            ).fetchone()
            if collision:
                raise ValueError('Reserved demo account IDs are occupied')
            execute_sql(connection, seed_sql())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--export-sql', type=Path)
    arguments = parser.parse_args()
    if arguments.export_sql:
        arguments.export_sql.parent.mkdir(parents=True, exist_ok=True)
        arguments.export_sql.write_text(seed_sql(), encoding='utf-8')
        print(arguments.export_sql)
    else:
        seed(arguments.database)
        print(f'Seeded five fictional test cases at {arguments.database}')
