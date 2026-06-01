r"""P31: Integration tests for adapter usage in grading pipeline.

Tests that mock/simulation questions with non-standard field names
(answer, correct_answer, _original_answer, standard_answer) correctly
enter the same grading pipeline as real exam questions.
"""

import re


# ── Helpers ──

class _Status:
    """Minimal status mock for _build_standard_solution."""
    def write(self, msg):
        pass


def _mock_choice_answer_field():
    """Mock question: correct answer in 'answer' field, not 'correct_option'."""
    return {
        "question_id": "宇哥八套卷-卷一-001",
        "question_type": "选择题",
        "question": "下列极限存在的是...",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "answer": "B",
        "standard_answer": "B",
        "knowledge_points": ["极限"],
        "difficulty": "中等",
        "score": 5,
        "source": "import_zhangyu_v1",
    }


def _mock_choice_correct_answer_field():
    """Mock question: correct answer in 'correct_answer' field."""
    return {
        "question_id": "模拟-002",
        "question_type": "选择题",
        "question": "求导...",
        "options": {"A": "cos x", "B": "sin x", "C": "-sin x", "D": "tan x"},
        "correct_answer": "C",
        "standard_answer": "C",
        "knowledge_points": ["导数"],
        "difficulty": "中等",
        "score": 5,
    }


def _real_choice():
    """Real exam choice question with correct_option field."""
    return {
        "question_id": "2026-数一-010",
        "question_type": "选择题",
        "question": "设函数f(x)在x=0处可导...",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["导数"],
        "difficulty": "中等",
        "score": 5,
    }


# ── Test 1: _build_standard_solution resolves correct option from 'answer' field ──

def test_build_standard_solution_resolves_from_answer_field():
    """_build_standard_solution should find the correct option even when it's
    stored in 'answer' instead of 'correct_option'."""
    from views.grading_page import _build_standard_solution

    mock_q = _mock_choice_answer_field()
    # Remove standard_answer so the function must derive it from correct option
    mock_q["standard_answer"] = ""

    solution = _build_standard_solution(
        question=mock_q["question"],
        ocr_data={"question_type": "选择题"},
        selected_q=mock_q,
        client=None,
        status=_Status(),
        _state={},
    )

    known = solution.get("standard_answer", "")
    # Should contain "B" as the correct option
    assert "B" in known, f"Expected 'B' in standard_answer, got: {known}"


# ── Test 2: Fast-path gate triggers for mock question with 'answer' field ──

def test_fast_path_gate_triggers_for_mock_answer_field():
    """Fast-path should trigger for mock questions where answer is in 'answer' field,
    not just 'correct_option'."""
    from views.grading_page import _grade_choice_fast
    from services.grading_question_adapter import resolve_correct_option

    mock_q = _mock_choice_answer_field()
    # Verify the adapter resolves correctly
    assert resolve_correct_option(mock_q) == "B"
    # Fast path should grade correctly
    result = _grade_choice_fast(mock_q, "B", {})
    assert result["grading_result"]["total"] == 5
    assert result["grading_result"]["engine"] == "choice_fast"


# ── Test 3: Engine A fallback grades mock choice question correctly ──

def test_engine_a_fallback_grades_mock_choice():
    """Engine A (rule engine) should grade mock choice questions correctly
    even when correct_option is not the primary field."""
    from views.grading_page import _grade_choice_fast

    mock_q = _mock_choice_correct_answer_field()
    # Correct answer
    result_correct = _grade_choice_fast(mock_q, "C", {})
    assert result_correct["grading_result"]["total"] == 5
    # Wrong answer
    result_wrong = _grade_choice_fast(mock_q, "A", {})
    assert result_wrong["grading_result"]["total"] == 0
    assert "C" in result_wrong["grading_result"]["comment"]


# ── Test 4: Diagnosis shows correct option for mock question ──

def test_diagnosis_shows_correct_option_for_mock():
    """When a mock question is graded wrong, the diagnosis should show the
    correct option resolved from alternative fields."""
    from views.grading_page import _grade_choice_fast

    mock_q = _mock_choice_answer_field()
    result = _grade_choice_fast(mock_q, "A", {})
    assert result["grading_result"]["total"] == 0
    # The comment should mention the correct answer "B"
    comment = result["grading_result"].get("comment", "")
    assert "B" in comment, f"Expected 'B' in comment, got: {comment!r}"


# ── Test 5: Real exam correct_option field still works ──

def test_real_exam_correct_option_still_works():
    """Regression guard: real exam questions with correct_option field
    must continue to grade correctly."""
    from views.grading_page import _grade_choice_fast

    real_q = _real_choice()
    # Correct answer
    result_correct = _grade_choice_fast(real_q, "C", {})
    assert result_correct["grading_result"]["total"] == 5
    assert result_correct["grading_result"]["engine"] == "choice_fast"
    # Wrong answer
    result_wrong = _grade_choice_fast(real_q, "A", {})
    assert result_wrong["grading_result"]["total"] == 0
    assert "C" in result_wrong["grading_result"]["comment"]


def test_resolve_correct_answer_choice_priority_variants():
    from services.grading_question_adapter import resolve_correct_answer

    assert resolve_correct_answer({"question_type": "选择题", "correct_option": "B"}, "选择题")["correct_option"] == "B"
    assert resolve_correct_answer({"question_type": "选择题", "answer": "C"}, "选择题")["correct_option"] == "C"
    assert resolve_correct_answer({"question_type": "选择题", "correct_answer": "答案：D"}, "选择题")["correct_option"] == "D"
    assert resolve_correct_answer({"question_type": "选择题", "standard_answer": "故选 A"}, "选择题")["correct_option"] == "A"


def test_grade_choice_fast_missing_answer_needs_review():
    from views.grading_page import _grade_choice_fast

    result = _grade_choice_fast({"question_type": "选择题", "score": 5}, "A", {})
    gr = result["grading_result"]
    assert gr["needs_review"] is True
    assert gr["error_type"] == "standard_answer_missing"
    assert gr["total"] is None
