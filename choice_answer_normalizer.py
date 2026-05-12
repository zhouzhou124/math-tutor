"""选择题答案标准化与判分 — 严格集合比较"""

import re


def normalize_choice_answer(ans: str) -> list[str]:
    """将学生答案标准化为有序去重字母列表。

    "B"     → ["B"]
    "BC"    → ["B","C"]
    " B C " → ["B","C"]
    "选B"    → ["B"]
    "b"     → ["B"]
    """
    if not ans:
        return []
    choices = re.findall(r'[A-Da-d]', str(ans).upper())
    return sorted(set(choices))


def compare_choice_answer(student_answer: str, correct_answer: str) -> dict:
    """严格集合比较选择题答案。

    Returns:
        {
            "is_correct": bool,
            "student_choices": ["A", ...],
            "correct_choices": ["D", ...],
        }
    """
    student_set = normalize_choice_answer(student_answer)
    correct_set = normalize_choice_answer(correct_answer)
    return {
        "is_correct": student_set == correct_set,
        "student_choices": student_set,
        "correct_choices": correct_set,
    }
