"""Original quiz data and exact arithmetic grading."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction

QUIZZES = {
 "practice": [
  {"answer": "<", "points": 1, "explanation": "6,7 = 6,70 nên 6,07 < 6,7."},
  {"answer": "=", "points": 1, "explanation": "Chữ số 0 tận cùng phần thập phân không đổi giá trị."},
  {"answer": "5,9", "points": 1, "explanation": "5,09 < 5,19 < 5,90."},
  {"interval": (Fraction(235,100), Fraction(236,100)), "points": 1,
   "explanation": "Ví dụ 2,355. Mọi số lớn hơn 2,35 và nhỏ hơn 2,36 đều được chấp nhận."}
 ],
 "exam": [
  {"answer": "<", "points": 1, "explanation": "7,9 = 7,90 nên 7,09 < 7,9."},
  {"number": Fraction(7,8), "points": 1, "explanation": "3/4 + 1/8 = 6/8 + 1/8 = 7/8."},
  {"number": Fraction(36), "points": 2, "explanation": "240 × 15 : 100 = 36."},
  {"number": Fraction(162), "points": 3,
   "explanation": "Nửa chu vi: 27 cm. Rộng: 9 cm. Dài: 18 cm. Diện tích: 162 cm²."},
  {"number": Fraction(247500), "points": 3,
   "explanation": "Sau tăng: 275.000 đồng. Sau giảm: 275.000 × 90 : 100 = 247.500 đồng."}
 ]
}

def parse_number(value):
    value = value.strip().replace(" ", "").replace(",", ".")
    if not value or len(value) > 70:
        return None
    try:
        if "/" in value:
            numerator, denominator = value.split("/")
            a, b = Decimal(numerator), Decimal(denominator)
            if not a.is_finite() or not b.is_finite() or b == 0:
                return None
            if abs(a.adjusted()) > 100 or abs(b.adjusted()) > 100:
                return None
            return Fraction(a) / Fraction(b)
        number = Decimal(value)
        if not number.is_finite() or abs(number.adjusted()) > 100:
            return None
        return Fraction(number)
    except (ValueError, ZeroDivisionError, InvalidOperation, OverflowError):
        return None

def grade(kind, answers):
    if kind not in QUIZZES:
        raise ValueError("Unknown quiz")
    questions = QUIZZES[kind]
    if not isinstance(answers, list) or len(answers) != len(questions):
        raise ValueError("Wrong number of answers")
    if any(not isinstance(a, str) or len(a) > 70 for a in answers):
        raise ValueError("Answers must be strings of at most 70 characters")
    results, earned = [], 0
    total = sum(q["points"] for q in questions)
    for q, answer in zip(questions, answers):
        if "answer" in q:
            correct = answer.strip() == q["answer"]
        else:
            n = parse_number(answer)
            if "interval" in q:
                low, high = q["interval"]
                correct = n is not None and low < n < high
            else:
                correct = n is not None and n == q["number"]
        points = q["points"] if correct else 0
        earned += points
        results.append({"correct": correct, "points": points, "explanation": q["explanation"]})
    return {"score": round(earned / total * 10, 2), "earned": earned,
            "total": total, "results": results}
