"""P31.1: GradingOrchestrator result contract tests.

Verifies that normalize_grading_result preserves grading fields,
the choice fast path includes steps, and execute_grading uses
the real total_score from the question.
"""

from services.grading_adapter import normalize_grading_result
from services.grading_orchestrator import _grade_choice_fast, execute_grading


# ── normalize_grading_result field preservation ──

def test_normalize_preserves_is_correct():
    raw = {"total": 5, "is_correct": True}
    result = normalize_grading_result(raw)
    assert result["is_correct"] is True


def test_normalize_preserves_is_correct_false():
    raw = {"total": 0, "is_correct": False}
    result = normalize_grading_result(raw)
    assert result["is_correct"] is False


def test_normalize_preserves_total_score():
    raw = {"total": 5, "total_score": 5}
    result = normalize_grading_result(raw)
    assert result["total_score"] == 5


def test_normalize_preserves_correct_answer():
    raw = {"total": 0, "correct_answer": "B"}
    result = normalize_grading_result(raw)
    assert result["correct_answer"] == "B"


def test_normalize_preserves_correct_option():
    raw = {"total": 5, "correct_option": "A"}
    result = normalize_grading_result(raw)
    assert result["correct_option"] == "A"


def test_normalize_preserves_student_answer():
    raw = {"total": 0, "student_answer": "C"}
    result = normalize_grading_result(raw)
    assert result["student_answer"] == "C"


def test_normalize_preserves_steps():
    steps = [{"label": "test", "score": 5}]
    raw = {"total": 5, "steps": steps}
    result = normalize_grading_result(raw)
    assert result["steps"] == steps


def test_normalize_preserves_needs_review():
    raw = {"total": None, "needs_review": True}
    result = normalize_grading_result(raw)
    assert result["needs_review"] is True


def test_normalize_preserves_error_type():
    raw = {"total": 0, "error_type": "choice_wrong"}
    result = normalize_grading_result(raw)
    assert result["error_type"] == "choice_wrong"


def test_normalize_preserves_engine():
    raw = {"total": 5, "engine": "choice_fast"}
    result = normalize_grading_result(raw)
    assert result["engine"] == "choice_fast"


def test_normalize_preserves_confidence():
    raw = {"total": 5, "confidence": 0.95}
    result = normalize_grading_result(raw)
    assert result["confidence"] == 0.95


def test_normalize_default_values_for_missing_fields():
    raw = {"total": 5}
    result = normalize_grading_result(raw)
    assert result["is_correct"] is None
    assert result["total_score"] is None
    assert result["correct_answer"] == ""
    assert result["steps"] == []
    assert result["needs_review"] is False
    assert result["error_type"] == ""


def test_normalize_does_not_overwrite_valid_values():
    raw = {
        "total": 5, "is_correct": True, "total_score": 10,
        "correct_answer": "A", "confidence": 0.8,
    }
    result = normalize_grading_result(raw)
    assert result["is_correct"] is True
    assert result["total_score"] == 10
    assert result["correct_answer"] == "A"
    assert result["confidence"] == 0.8


# ── Choice fast path steps ──

def test_choice_fast_correct_has_steps():
    selected_q = {"correct_option": "A", "score": 5}
    result = _grade_choice_fast(selected_q, "A")
    assert "steps" in result
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["label"] == "选择题判分"
    assert step["status"] == "correct"
    assert step["score"] == 5
    assert step["max_score"] == 5


def test_choice_fast_incorrect_has_steps():
    selected_q = {"correct_option": "A", "score": 5}
    result = _grade_choice_fast(selected_q, "B")
    assert "steps" in result
    step = result["steps"][0]
    assert step["status"] == "incorrect"
    assert step["score"] == 0
    assert step["max_score"] == 5


def test_choice_fast_correct_total_equals_total_score():
    selected_q = {"correct_option": "A", "score": 5}
    result = _grade_choice_fast(selected_q, "A")
    assert result["total"] == 5
    assert result["total_score"] == 5


def test_choice_fast_incorrect_total_is_zero():
    selected_q = {"correct_option": "A", "score": 5}
    result = _grade_choice_fast(selected_q, "B")
    assert result["total"] == 0
    assert result["total_score"] == 5


def test_choice_fast_uses_total_score_field():
    selected_q = {"correct_option": "A", "total_score": 8}
    result = _grade_choice_fast(selected_q, "A")
    assert result["total_score"] == 8
    assert result["total"] == 8


def test_choice_fast_uses_points_field():
    selected_q = {"correct_option": "A", "points": 3}
    result = _grade_choice_fast(selected_q, "A")
    assert result["total_score"] == 3


def test_choice_fast_defaults_to_5():
    selected_q = {"correct_option": "A"}
    result = _grade_choice_fast(selected_q, "A")
    assert result["total_score"] == 5


def test_choice_fast_has_correct_option():
    selected_q = {"correct_option": "B", "score": 5}
    result = _grade_choice_fast(selected_q, "A")
    assert result["correct_option"] == "B"
    assert result["correct_answer"] == "B"


def test_choice_fast_has_is_correct():
    selected_q = {"correct_option": "A", "score": 5}
    assert _grade_choice_fast(selected_q, "A")["is_correct"] is True
    assert _grade_choice_fast(selected_q, "B")["is_correct"] is False


# ── execute_grading contract ──

def test_execute_grading_choice_uses_question_score():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "score": 5,
        "knowledge_points": ["极限"],
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["total"] == 5
    assert gr["total_score"] == 5


def test_execute_grading_choice_wrong_total_zero():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="B",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["total"] == 0
    assert gr["total_score"] == 5


def test_execute_grading_choice_has_steps():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert "steps" in gr
    assert len(gr["steps"]) == 1


def test_execute_grading_choice_has_mistake_record_created():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    assert "mistake_record_created" in result
    assert result["mistake_record_created"] is False


def test_execute_grading_view_only():
    result = execute_grading(
        question="test", student_ans="",
        ocr_data={"question_type": "选择题"},
        selected_q={"question_type": "选择题"},
    )
    assert result["mode"] == "view_only"
    assert result["is_view_only"] is True
    assert result["mistake_record_created"] is False


def test_execute_grading_view_only_grading_result():
    result = execute_grading(
        question="test", student_ans="  ",
        ocr_data={"question_type": "填空题"},
        selected_q={"question_type": "填空题"},
    )
    gr = result["grading_result"]
    assert gr["total"] is None
    assert gr["view_only"] is True


def test_execute_grading_choice_with_total_score_field():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "total_score": 10,
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["total"] == 10
    assert gr["total_score"] == 10


def test_execute_grading_choice_result_has_is_correct():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "A",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["is_correct"] is True


def test_execute_grading_choice_result_has_correct_answer():
    selected_q = {
        "question_type": "选择题",
        "correct_option": "B",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["correct_answer"] == "B"


def test_execute_grading_choice_has_grading_method():
    selected_q = {
        "question_type": "选择题",
        "answer": "C",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="C",
        ocr_data={"question_type": "选择题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["grading_method"] == "local_choice_match"
    assert gr["correct_option"] == "C"


def test_execute_grading_fill_high_confidence_quick_compare():
    selected_q = {
        "question_type": "填空题",
        "answer": "2",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="2",
        ocr_data={"question_type": "填空题"},
        selected_q=selected_q,
    )
    gr = result["grading_result"]
    assert gr["is_correct"] is True
    assert gr["grading_method"] == "quick_compare"
    assert gr["total"] == 5


def test_execute_grading_fill_low_confidence_marks_escalation_without_client():
    selected_q = {
        "question_type": "填空题",
        "answer": "2",
        "score": 5,
    }
    result = execute_grading(
        question="test", student_ans="3",
        ocr_data={"question_type": "填空题"},
        selected_q=selected_q,
        client=None,
    )
    gr = result["grading_result"]
    assert gr["needs_review"] is True
    assert gr["grading_method"] == "quick_compare_escalated_llm"
    assert gr["correct_answer"] == "2"
