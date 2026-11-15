"""Synthetic test source only, never installed by normal application startup."""
from .group_games import QuestionSource


def synthetic_source():
    questions = []
    for grade in range(1, 6):
        for index in range(15):
            left, right = index + 1, grade + 1
            question = {'id': f'SYNTHETIC-GROUP-G{grade}-{index}', 'revision': 1,
                        'purpose': 'group-games', 'grade': grade,
                        'text': f'[DỮ LIỆU TEST] Tính {left} + {right}.',
                        'responseMode': 'typed', 'answer': str(left+right), 'answerKind': 'number',
                        'inputGuide': {'instruction': 'Nhập một số. Câu giả dùng kiểm thử.'}}
            if index % 3 == 0:
                question.update(responseMode='choice', options=[str(left+right), str(left+right+1), str(left+right-1), str(left+right+2)])
            questions.append(question)
    return QuestionSource(questions, qa_only=True, revision='synthetic-qa-v1-not-reviewed')
