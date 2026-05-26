"""P29-6.1: retry forces regeneration and isolates attempts."""

import time as _time


class _FakeExpander:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _ok_report():
    return {
        "ok": True,
        "renderable": True,
        "complete": True,
        "detailed": True,
        "covers_requirements": True,
        "logically_plausible": True,
        "issues": [],
        "should_regenerate": False,
    }


def _bad_report():
    return {
        "ok": False,
        "renderable": False,
        "complete": False,
        "detailed": False,
        "covers_requirements": False,
        "logically_plausible": False,
        "issues": ["not_renderable"],
        "should_regenerate": True,
    }


def _wait_for(predicate, timeout=2.0):
    start = _time.time()
    while _time.time() - start < timeout:
        if predicate():
            return True
        _time.sleep(0.02)
    return False


def test_retry_marks_force_resets_poll_and_increments_attempt(monkeypatch):
    import pytest
    import streamlit as st
    import views.grading_page as page

    state = {
        "solution_attempt_id": 2,
        "_poll_start": 11,
        "_solution_error": "old",
        "_async_solution": {"old": True},
        "_async_solution_failed": {"old": True},
        "standard_answer": {"standard_solution_status": "failed"},
        "grading_result": {"standard_solution_status": "failed"},
    }
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(page.time, "time", lambda: 123.0)
    monkeypatch.setattr(st, "warning", lambda *args, **kw: None)
    monkeypatch.setattr(st, "caption", lambda *args, **kw: None)
    monkeypatch.setattr(st, "button", lambda *args, **kw: True)
    monkeypatch.setattr(st, "expander", lambda *args, **kw: _FakeExpander())
    monkeypatch.setattr(st, "markdown", lambda *args, **kw: None)
    monkeypatch.setattr(st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))

    with pytest.raises(RuntimeError, match="rerun"):
        page._render_standard_solution_gate_failure(
            {"standard_solution_status": "failed"},
            selected_q={"question_id": "q1"},
            status="failed",
        )

    assert state["force_regenerate_solution"] is True
    assert state["solution_attempt_id"] == 3
    assert state["_solution_active_attempt_id"] == 3
    assert state["_poll_start"] == 123.0
    assert state["_solution_status"] == "pending"
    assert state["_solution_error"] is None
    assert "_async_solution" not in state
    assert "_async_solution_failed" not in state


def test_force_true_bypasses_solution_cache_hit(monkeypatch):
    import views.grading_page as page
    import services.solution_quality as quality

    calls = {"build": 0}
    state = {"_solution_active_attempt_id": 1, "solution_attempt_id": 1}
    monkeypatch.setattr(page, "_solution_cache_hit", lambda selected_q: True)
    monkeypatch.setattr(
        page,
        "_build_standard_solution",
        lambda *args, **kw: calls.__setitem__("build", calls["build"] + 1)
        or {"standard_answer": "步骤1：完整推导。" * 10, "standard_solution_status": "ready"},
    )
    monkeypatch.setattr(quality, "solution_quality_report", lambda *args, **kw: _ok_report())

    task = page._ensure_solution_async(
        {"question_id": "q1"}, "q", {}, object(), "model",
        _state=state, force=True, attempt_id=1,
    )

    assert task == "q1"
    assert _wait_for(lambda: calls["build"] == 1)
    assert _wait_for(lambda: state.get("_solution_status") == "ready")
    assert state["force_regenerate_solution"] is False


def test_force_false_keeps_cache_hit_behavior(monkeypatch):
    import views.grading_page as page

    calls = {"build": 0}
    state = {}
    monkeypatch.setattr(page, "_solution_cache_hit", lambda selected_q: True)
    monkeypatch.setattr(
        page,
        "_build_standard_solution",
        lambda *args, **kw: calls.__setitem__("build", calls["build"] + 1) or {},
    )

    task = page._ensure_solution_async(
        {"question_id": "q1"}, "q", {}, object(), "model",
        _state=state, force=False,
    )

    assert task is None
    assert calls["build"] == 0
    assert state["_solution_status"] == "ready"


def test_old_attempt_result_cannot_overwrite_new_attempt(monkeypatch):
    import views.grading_page as page
    import services.solution_quality as quality

    state = {"_solution_active_attempt_id": 2, "solution_attempt_id": 2}
    monkeypatch.setattr(page, "_solution_cache_hit", lambda selected_q: False)
    monkeypatch.setattr(
        page,
        "_build_standard_solution",
        lambda *args, **kw: {"standard_answer": "old attempt answer", "standard_solution_status": "ready"},
    )
    monkeypatch.setattr(quality, "solution_quality_report", lambda *args, **kw: _ok_report())

    page._ensure_solution_async(
        {"question_id": "q1"}, "q", {}, object(), "model",
        _state=state, force=True, attempt_id=1,
    )

    assert _wait_for(lambda: state.get("_solution_running_q1") is True)
    assert "_async_solution" not in state
    assert state.get("_solution_status") != "ready"
