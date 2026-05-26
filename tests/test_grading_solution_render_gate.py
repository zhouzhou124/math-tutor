"""Regression tests for blocking bad AI standard-solution rendering."""


class _FakeExpander:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_missing_subparts_status_blocks_step_rendering():
    from views.grading_page import (
        _should_block_standard_solution_render,
        _standard_solution_gate_message,
    )

    solution = {
        "standard_solution_status": "incomplete",
        "_structured": {"steps": [{"label": "s1", "blocks": [{"type": "text", "content": "partial"}]}]},
        "_quality_report": {"issues": ["missing_subparts:1,2"]},
    }

    assert _should_block_standard_solution_render({}, solution)
    assert _standard_solution_gate_message(solution, "incomplete") == "标准解答生成不完整，缺少第 1、2 小问"


def test_broken_latex_status_blocks_step_rendering():
    from services.grading_adapter import normalize_solution_for_render
    from views.grading_page import _should_block_standard_solution_render

    solution = normalize_solution_for_render({
        "standard_answer": r"步骤1：坏公式 $\left\begin{array}{cc}1&0\\0&1\end{array}\right$ 因此最终答案。",
        "_structured": {
            "steps": [{
                "label": "s1",
                "blocks": [{"type": "latex", "content": r"\left\begin{array}{cc}1&0\\0&1\end{array}"}],
            }]
        },
    })

    assert solution["standard_solution_status"] == "failed"
    assert _should_block_standard_solution_render({}, solution)


def test_failed_status_renders_retry_button(monkeypatch):
    import streamlit as st
    from views.grading_page import _render_standard_solution_gate_failure

    calls = {"warnings": [], "buttons": []}
    monkeypatch.setattr(st, "warning", lambda msg: calls["warnings"].append(msg))
    monkeypatch.setattr(st, "button", lambda label, **kw: calls["buttons"].append(label) or False)
    monkeypatch.setattr(st, "expander", lambda *args, **kw: _FakeExpander())
    monkeypatch.setattr(st, "markdown", lambda *args, **kw: None)

    _render_standard_solution_gate_failure(
        {"standard_solution_status": "failed", "standard_solution_error": "not_renderable"},
        selected_q={"question_id": "q1"},
        status="failed",
    )

    assert calls["warnings"] == ["标准解答生成失败，请重新生成标准解答"]
    assert calls["buttons"] == ["重新生成标准解答"]


def test_retry_click_marks_stale_solution_pending(monkeypatch):
    import pytest
    import streamlit as st
    from views.grading_page import (
        _render_standard_solution_gate_failure,
        _standard_solution_status,
    )

    state = {
        "standard_answer": {"standard_solution_status": "incomplete"},
        "grading_result": {"standard_solution_status": "incomplete"},
        "_async_solution": {"standard_solution_status": "failed"},
        "_solution_running_q1": True,
        "_solution_active_hash": "old",
        "standard_answer_structured": {"steps": []},
    }
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(st, "warning", lambda *args, **kw: None)
    monkeypatch.setattr(st, "button", lambda *args, **kw: True)
    monkeypatch.setattr(st, "expander", lambda *args, **kw: _FakeExpander())
    monkeypatch.setattr(st, "markdown", lambda *args, **kw: None)
    monkeypatch.setattr(
        st,
        "rerun",
        lambda: (_ for _ in ()).throw(RuntimeError("rerun")),
    )

    with pytest.raises(RuntimeError, match="rerun"):
        _render_standard_solution_gate_failure(
            {"standard_solution_status": "incomplete"},
            selected_q={"question_id": "q1"},
            status="incomplete",
        )

    assert state["_solution_status"] == "pending"
    assert state["standard_answer"]["standard_solution_status"] == "pending"
    assert state["grading_result"]["standard_solution_status"] == "pending"
    assert state["grading_result"]["_hide_until_solution_ready"] is True
    assert "_async_solution" not in state
    assert "_solution_running_q1" not in state
    assert "_solution_active_hash" not in state
    assert "standard_answer_structured" not in state
    assert _standard_solution_status(
        state["grading_result"],
        state["standard_answer"],
        _state=state,
    ) == "pending"


def test_pending_solution_status_yields_to_async_failure():
    from views.grading_page import _standard_solution_status

    state = {"_solution_status": "failed"}
    gr = {"standard_solution_status": "pending"}
    sa = {"standard_solution_status": "pending"}

    assert _standard_solution_status(gr, sa, _state=state) == "failed"


def test_raw_broken_text_is_escaped_and_debug_only(monkeypatch):
    import streamlit as st
    from views.grading_page import _render_standard_solution_gate_failure

    calls = {"warnings": [], "markdown": []}
    raw = r'<span style="color:red">\left\begin{array}</span> �A0�'
    monkeypatch.setattr(st, "warning", lambda msg: calls["warnings"].append(msg))
    monkeypatch.setattr(st, "button", lambda label, **kw: False)
    monkeypatch.setattr(st, "expander", lambda *args, **kw: _FakeExpander())
    monkeypatch.setattr(st, "markdown", lambda body, **kw: calls["markdown"].append(body))

    _render_standard_solution_gate_failure(
        {"standard_solution_status": "failed", "standard_answer": raw},
        selected_q={},
        status="failed",
    )

    assert raw not in "\n".join(calls["warnings"])
    debug_html = "\n".join(calls["markdown"])
    assert "&lt;span style=\\&quot;color:red\\&quot;&gt;" in debug_html
    assert "left" in debug_html
    assert "begin{array}" in debug_html
    assert raw not in debug_html


def test_missing_subparts_marks_solution_incomplete(monkeypatch):
    from agents.solver_agent import SolverAgent
    import services.solution_quality as solution_quality
    from services.solution_service import SolutionService

    answer = "步骤1：先分析第一问。步骤2：继续计算第一问。因此，最终答案为 $1$。" + "x" * 160

    def fake_quality_report(solution, question=None):
        return {
            "ok": False,
            "renderable": True,
            "complete": False,
            "detailed": True,
            "covers_requirements": False,
            "logically_plausible": True,
            "issues": ["missing_subparts:1,2"],
            "should_regenerate": True,
        }

    monkeypatch.setattr(
        SolverAgent,
        "solve",
        lambda self, **kw: {"success": True, "standard_answer": answer, "steps": []},
    )
    monkeypatch.setattr(solution_quality, "solution_quality_report", fake_quality_report)

    service = SolutionService(client=object(), model="test")
    result = service.build(
        question="",
        selected_q={
            "question_type": "解答题",
            "question": "（1）求极限；（2）证明单调性。",
            "score": 10,
        },
        ocr_data={},
    )

    assert result["standard_solution_status"] == "failed"
    assert result["standard_solution_source"] == "failed"
    assert result["standard_answer"] == ""
    assert result["_structured"] is None
    assert result["steps"] == []
    assert "missing_solution_ir" in result["standard_solution_error"] or result["_mandatory_ir_failed"]
