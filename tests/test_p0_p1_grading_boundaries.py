import inspect
from pathlib import Path


def test_only_one_get_canonical_solutions_definition():
    source = Path("views/grading_page.py").read_text(encoding="utf-8")
    assert source.count("def get_canonical_solutions(") == 1


def test_find_best_canonical_match_uses_adapter_not_raw_standard_answer():
    from views.grading_page import find_best_canonical_match

    source = inspect.getsource(find_best_canonical_match)
    assert "canonical_entry_to_solution" in source
    assert 'sol.get("standard_answer"' not in source
    assert "sol.get('standard_answer'" not in source


def test_canonical_entry_to_solution_reuses_normalize_canonical_entry():
    from services.grading_adapter import (
        SOLUTION_FORMAT_VERSION,
        canonical_entry_to_solution,
        normalize_canonical_entry,
    )

    source = inspect.getsource(canonical_entry_to_solution)
    assert "normalize_canonical_entry" in source
    entry = {
        "format_version": SOLUTION_FORMAT_VERSION,
        "standard_answer": "步骤1：建立方程。步骤2：解出结果。最终答案为 $x=1$。" + "x" * 140,
        "solution_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
        "reviewed": True,
    }
    normalized = normalize_canonical_entry(entry, question={"question_type": "解答题"})
    solution = canonical_entry_to_solution(entry, {"score": 10, "question_type": "解答题"})
    assert solution["standard_answer"] == normalized["standard_answer"]
    assert solution["_solution_ir"] == normalized["solution_ir"]
    assert solution["_ai_unverified"] is False


def test_renderer_has_no_page_state_writes_or_rerun():
    import renderers.components.grading_result as mod

    source = inspect.getsource(mod)
    assert "st.rerun" not in source
    assert 'st.session_state["' not in source
    assert "st.session_state['" not in source
    assert "st.session_state.selected_question" not in source
    assert "st.session_state.page" not in source


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _EventRecorder:
    def __init__(self):
        self.session_state = {}

    def container(self, *args, **kwargs):
        return _Ctx()

    def columns(self, n):
        return [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]

    def button(self, *args, **kwargs):
        return True

    def markdown(self, *args, **kwargs):
        return None

    def success(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def caption(self, *args, **kwargs):
        return None


def test_recommendation_renderer_returns_navigation_event(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _EventRecorder()
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(
        "similar_question_recommender.recommend_similar",
        lambda **kwargs: [{"question_id": "q1", "question_type": "解答题", "year": "2026"}],
    )
    events = mod.render_recommendations(
        {"weak_points": ["换元积分"]},
        question_db=object(),
        current_question={"question_id": "q0", "raw_question_text": "题"},
        is_correct=False,
    )
    assert events == [{
        "type": "open_practice_question",
        "question": {"question_id": "q1", "question_type": "解答题", "year": "2026"},
    }]


def test_business_normalize_latex_returns_str():
    from services.latex_normalization import normalize_latex

    out = normalize_latex(r"\frac12")
    assert isinstance(out, str)


def test_business_code_does_not_import_ast_normalize_latex():
    roots = [Path("views"), Path("services"), Path("agents")]
    source = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for root in roots
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    )
    assert "from latex.normalizer import normalize_latex" not in source
    assert "from latex_engine.normalizer import normalize_latex" not in source
