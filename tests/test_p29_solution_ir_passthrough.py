"""P29-1: CanonicalIR/SolutionIR passthrough without behavior changes."""

import json


def _valid_solution_payload():
    standard_answer = (
        "步骤1：根据题意建立方程并写出关键关系 $x+1=2$。"
        "步骤2：利用等式性质化简可得 $x=1$，并把结果代回原方程验证左边等于右边。"
        "因此最终答案为 $x=1$。"
    )
    structured = {
        "steps": [
            {
                "label": "步骤1：建立方程",
                "body_markdown": "根据题意建立方程，关键关系为 $x+1=2$，这是后续求解的基础。",
                "blocks": [
                    {"type": "text", "content": "根据题意建立方程，这是后续求解的基础。"},
                    {"type": "latex", "content": "x+1=2"},
                ],
            },
            {
                "label": "步骤2：求解方程",
                "body_markdown": "利用等式性质两边同减 $1$，可得 $x=1$，因此得到最终答案。",
                "blocks": [
                    {"type": "text", "content": "利用等式性质两边同减 1，得到最终结果。"},
                    {"type": "latex", "content": "x=1"},
                ],
            },
        ],
        "final_answer": {"type": "latex", "content": "x=1"},
    }
    return standard_answer, structured


def test_normalize_standard_solution_preserves_solution_ir():
    from services.grading_adapter import normalize_standard_solution

    ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    out = normalize_standard_solution({
        "standard_answer": "x=1",
        "_solution_ir": ir,
    })

    assert out["_solution_ir"] == ir


def test_normalize_standard_solution_falls_back_to_canonical_ir():
    from services.grading_adapter import normalize_standard_solution

    canonical_ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    out = normalize_standard_solution({
        "standard_answer": "x=1",
        "_canonical_ir": canonical_ir,
    })

    assert out["_solution_ir"] == canonical_ir


def test_solver_agent_canonical_returns_solution_ir_equal_to_canonical_ir():
    from agents.solver_agent import SolverAgent

    canonical = {
        "agent": "solver",
        "question": {
            "text": "求 x+1=2 的解",
            "math_type": "数学一",
            "question_type": "解答题",
            "knowledge_points": ["方程"],
            "total_score": 10,
        },
        "proof_trace": {
            "steps": [
                {
                    "id": "s1",
                    "operation": "solve",
                    "input_state": "x+1=2",
                    "output_state": "x=1",
                    "justification": "等式两边同减 1",
                    "label": "求解方程",
                }
            ],
            "final_answer": "x=1",
        },
        "metadata": {},
    }

    class _Msg:
        content = json.dumps(canonical, ensure_ascii=False)

    class _Choice:
        message = _Msg()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    result = SolverAgent(_Client(), "fake-model")._solve_canonical(
        "求 x+1=2 的解", "数学一", "解答题", "方程"
    )

    assert result["success"] is True
    assert result["_solution_ir"] == result["_canonical_ir"]
    assert result["_solution_ir"]["proof_trace"]["steps"][0]["id"] == "s1"


def test_normalize_solution_for_render_does_not_drop_solution_ir():
    from services.grading_adapter import normalize_solution_for_render

    standard_answer, structured = _valid_solution_payload()
    ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    out = normalize_solution_for_render({
        "standard_answer": standard_answer,
        "_structured": structured,
        "_solution_ir": ir,
    })

    assert out["_solution_ir"] == ir
    assert out["_structured"] is not None


def test_solution_service_cache_maps_solution_ir():
    from services.grading_adapter import SOLUTION_FORMAT_VERSION
    from services.solution_service import SolutionService

    standard_answer, structured = _valid_solution_payload()
    ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    selected_q = {
        "question_id": "q1",
        "question_type": "解答题",
        "score": 10,
        "canonical_solutions": [{
            "standard_answer": standard_answer,
            "structured": structured,
            "solution_ir": ir,
            "format_version": SOLUTION_FORMAT_VERSION,
            "reviewed": True,
        }],
    }

    out = SolutionService().build(selected_q=selected_q)

    assert out["standard_solution_status"] == "ready"
    assert out["_solution_ir"] == ir


def test_save_as_canonical_solution_persists_solution_ir(tmp_path, monkeypatch):
    from views.grading_page import save_as_canonical_solution
    import database.question_db as question_db

    path = tmp_path / "q1.json"
    path.write_text(
        json.dumps({
            "question_id": "q1",
            "question": "求 x+1=2 的解",
            "question_type": "解答题",
            "score": 10,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(question_db, "get_question_path", lambda qid: path)

    standard_answer, structured = _valid_solution_payload()
    solution_ir = {"proof_trace": {"steps": [{"id": "s1"}]}}

    ok = save_as_canonical_solution(
        {"question_id": "q1", "question_type": "解答题"},
        standard_answer,
        structured=structured,
        solution_ir=solution_ir,
    )

    assert ok is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["canonical_solutions"][0]["solution_ir"] == solution_ir


def test_save_as_canonical_solution_uses_canonical_ir_as_solution_ir(tmp_path, monkeypatch):
    from views.grading_page import save_as_canonical_solution
    import database.question_db as question_db

    path = tmp_path / "q1.json"
    path.write_text(
        json.dumps({
            "question_id": "q1",
            "question": "求 x+1=2 的解",
            "question_type": "解答题",
            "score": 10,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(question_db, "get_question_path", lambda qid: path)

    standard_answer, structured = _valid_solution_payload()
    canonical_ir = {"proof_trace": {"steps": [{"id": "s1"}]}}

    ok = save_as_canonical_solution(
        {"question_id": "q1", "question_type": "解答题"},
        standard_answer,
        structured=structured,
        canonical_ir=canonical_ir,
    )

    assert ok is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["canonical_solutions"][0]["canonical_ir"] == canonical_ir
    assert data["canonical_solutions"][0]["solution_ir"] == canonical_ir


def test_solution_from_canonical_entry_reads_solution_ir_and_legacy_cache_still_works():
    from views.grading_page import _solution_from_canonical_entry

    ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    sol = _solution_from_canonical_entry(
        {"standard_answer": "x=1", "solution_ir": ir},
        {"score": 10},
    )
    legacy = _solution_from_canonical_entry(
        {"standard_answer": "x=1"},
        {"score": 10},
    )

    assert sol["_solution_ir"] == ir
    assert legacy["standard_answer"] == "x=1"
    assert legacy["_solution_ir"] is None


def test_solution_from_canonical_entry_falls_back_to_canonical_ir():
    from views.grading_page import _solution_from_canonical_entry

    canonical_ir = {"proof_trace": {"steps": [{"id": "s1"}]}}
    sol = _solution_from_canonical_entry(
        {"standard_answer": "x=1", "canonical_ir": canonical_ir},
        {"score": 10},
    )

    assert sol["_canonical_ir"] == canonical_ir
    assert sol["_solution_ir"] == canonical_ir


def test_solution_ir_does_not_affect_structured_rendering(monkeypatch):
    import streamlit as st
    import renderers.math_render_policy as policy
    from latex_utils import render_structured_safe

    class _FakeContainer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    rendered = []
    monkeypatch.setattr(st, "container", lambda **kw: _FakeContainer())
    monkeypatch.setattr(st, "markdown", lambda *args, **kw: None)
    monkeypatch.setattr(policy, "render_grading_latex", lambda text: rendered.append(text))

    _, structured = _valid_solution_payload()
    solution = {
        **structured,
        "_solution_ir": {"proof_trace": {"steps": [{"id": "different"}]}},
    }

    render_structured_safe(solution)

    assert rendered
    assert "根据题意建立方程" in rendered[0]
    assert "different" not in "\n".join(rendered)


def test_old_format_canonical_entry_clears_solution_ir():
    from services.grading_adapter import normalize_canonical_entry

    entry = {
        "format_version": "old",
        "standard_answer": "x=1",
        "structured": {"steps": []},
        "canonical_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
        "solution_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
    }

    out = normalize_canonical_entry(entry, question={})

    assert "structured" not in out
    assert "canonical_ir" not in out
    assert "solution_ir" not in out
