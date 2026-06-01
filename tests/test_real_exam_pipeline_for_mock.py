r"""P31: Real-exam pipeline for mock questions tests.

Tests that mock/simulation questions use the same grading pipeline as real exams.
"""

from services.grading_question_adapter import (
    normalize_to_grading_input,
    resolve_correct_option,
    resolve_final_answer,
)


# ── Helpers ──

def _real_choice():
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


def _mock_choice():
    return {
        "question_id": "宇哥八套卷-卷一-001",
        "question_type": "选择题",
        "question": "下列极限存在的是...",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "answer": "B",
        "standard_answer": "B",
        "knowledge_points": ["极限"],
        "difficulty": "中等",
        "score": 5,
        "source": "import_zhangyu_v1",
    }


def _real_fill():
    return {
        "question_id": "2026-数一-001",
        "question_type": "填空题",
        "question": "求极限...",
        "final_answer": "2",
        "_original_answer": "2",
        "standard_answer": "详细解答...",
        "knowledge_points": ["极限"],
        "difficulty": "中等",
        "score": 5,
    }


def _mock_fill():
    return {
        "question_id": "合工大超越-卷一-011",
        "question_type": "填空题",
        "question": "求定积分...",
        "standard_answer": "e^2 - 1",
        "knowledge_points": ["积分"],
        "difficulty": "中等",
        "score": 5,
        "source": "import_hegongda",
    }


# ── Test 1: Real and mock choice use same resolve_correct_option ──

def test_real_mock_choice_same_resolve():
    real = _real_choice()
    mock = _mock_choice()

    real_opt = resolve_correct_option(real)
    mock_opt = resolve_correct_option(mock)

    assert real_opt == "C"
    assert mock_opt == "B"
    # Both resolved by the same function — no mock-specific branch


# ── Test 2: Real and mock fill use same resolve_final_answer ──

def test_real_mock_fill_same_resolve():
    real = _real_fill()
    mock = _mock_fill()

    real_ans = resolve_final_answer(real)
    mock_ans = resolve_final_answer(mock)

    assert real_ans == "2"
    assert mock_ans == "e^2 - 1"
    # Both resolved by the same function


# ── Test 3: Both go through normalize_to_grading_input ──

def test_both_normalize_same_function():
    real_gq = normalize_to_grading_input(_real_choice())
    mock_gq = normalize_to_grading_input(_mock_choice())

    # Same type, same structure
    assert real_gq.question_type == mock_gq.question_type == "选择题"
    assert real_gq.correct_option  # non-empty
    assert mock_gq.correct_option  # non-empty
    # Different source metadata
    assert real_gq.source == "real_exam"
    assert mock_gq.source == "mock"


# ── Test 4: Mock fill with no final_answer resolves from standard_answer ──

def test_mock_fill_resolves_from_standard_answer():
    mock = _mock_fill()
    gq = normalize_to_grading_input(mock)
    # standard_answer is short, so it's used as final_answer
    assert gq.final_answer == "e^2 - 1"


# ── Test 5: Mock choice with answer field resolves correctly ──

def test_mock_choice_resolves_from_answer_field():
    mock = _mock_choice()
    gq = normalize_to_grading_input(mock)
    assert gq.correct_option == "B"


# ── Test 6: Empty submission check works for both ──

def test_empty_submission_both():
    from config import is_user_answer_empty
    assert is_user_answer_empty("") is True
    assert is_user_answer_empty("A") is False
    # Same function for both real and mock


# ── Test 7: source preserved in GradingQuestionInput ──

def test_source_preserved():
    real = normalize_to_grading_input(_real_choice())
    mock = normalize_to_grading_input(_mock_choice())
    assert real.source == "real_exam"
    assert mock.source == "mock"


# ── Test 8: Mock no correct_option → empty string, not crash ──

def test_mock_no_correct_option():
    mock = {
        "question_id": "test-001",
        "question_type": "选择题",
        "question": "test",
        "options": {"A": "1", "B": "2"},
        # No correct_option, no answer, no correct_answer
    }
    gq = normalize_to_grading_input(mock)
    assert gq.correct_option == ""


# ── Test 9: Mock no final_answer → empty string, not crash ──

def test_mock_no_final_answer():
    mock = {
        "question_id": "test-002",
        "question_type": "填空题",
        "question": "test",
        # No final_answer, no _original_answer, no answer
        "standard_answer": "a very long solution " * 20,  # too long to use as answer
    }
    gq = normalize_to_grading_input(mock)
    assert gq.final_answer == ""


# ── Test 10: Question bank rendering unchanged ──

def test_question_bank_rendering_unchanged():
    import importlib
    mod = importlib.import_module("views.question_bank_page")
    assert hasattr(mod, "render_question_bank_page")
