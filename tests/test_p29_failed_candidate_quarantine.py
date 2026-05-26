"""P29-6.1: failed regenerated candidates are quarantined, not rendered."""

import time as _time


def _bad_report(issues=None, *, renderable=False):
    return {
        "ok": False,
        "renderable": renderable,
        "complete": False,
        "detailed": False,
        "covers_requirements": False,
        "logically_plausible": False,
        "issues": issues or ["not_renderable"],
        "should_regenerate": True,
    }


def _wait_for(predicate, timeout=2.0):
    start = _time.time()
    while _time.time() - start < timeout:
        if predicate():
            return True
        _time.sleep(0.02)
    return False


def test_failed_candidate_is_saved_to_async_failed(monkeypatch):
    import views.grading_page as page
    import services.solution_quality as quality

    state = {"_solution_active_attempt_id": 1, "solution_attempt_id": 1}
    monkeypatch.setattr(page, "_solution_cache_hit", lambda selected_q: False)
    monkeypatch.setattr(
        page,
        "_build_standard_solution",
        lambda *args, **kw: {
            "standard_answer": r"<b>bad \right answer</b>",
            "steps": [{"content": "bad step"}],
            "_structured": {"steps": [{"blocks": [{"content": "bad structured"}]}]},
        },
    )
    monkeypatch.setattr(quality, "solution_quality_report", lambda *args, **kw: _bad_report())

    page._ensure_solution_async(
        {"question_id": "q1"}, "q", {}, object(), "model",
        _state=state, force=True, attempt_id=1,
    )

    assert _wait_for(lambda: state.get("_solution_status") == "failed")
    assert state["_async_solution_failed"]["standard_answer"] == ""
    assert "&lt;b&gt;bad" in state["_async_solution_failed"]["_debug_raw_standard_answer"]
    assert state["_failed_solution_attempt_id"] == 1
    assert state["_failed_quality_report"]["issues"] == ["not_renderable"]


def test_failed_raw_preview_is_html_escaped(monkeypatch):
    import views.grading_page as page
    import services.solution_quality as quality

    state = {"_solution_active_attempt_id": 1, "solution_attempt_id": 1}
    monkeypatch.setattr(page, "_solution_cache_hit", lambda selected_q: False)
    monkeypatch.setattr(
        page,
        "_build_standard_solution",
        lambda *args, **kw: {"standard_answer": '<span style="color:red">raw</span>'},
    )
    monkeypatch.setattr(quality, "solution_quality_report", lambda *args, **kw: _bad_report())

    page._ensure_solution_async(
        {"question_id": "q1"}, "q", {}, object(), "model",
        _state=state, force=True, attempt_id=1,
    )

    assert _wait_for(lambda: state.get("_failed_raw_preview"))
    assert '&lt;span style=&quot;color:red&quot;&gt;raw&lt;/span&gt;' == state["_failed_raw_preview"]


def test_no_ir_legacy_failed_hard_gate_clears_renderable_fields(monkeypatch):
    from services.grading_adapter import normalize_solution_for_render

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "false")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "false")

    out = normalize_solution_for_render({
        "standard_answer": r'<span style="color:red">\right</span>',
        "steps": [{"content": "bad"}],
        "_structured": {"steps": [{"blocks": [{"content": "bad"}]}]},
    })

    assert out["standard_solution_source"] == "failed"
    assert out["standard_solution_status"] == "failed"
    assert out["standard_answer"] == ""
    assert out["_structured"] is None
    assert out["steps"] == []
    assert "&lt;span" in out["_failed_raw_preview"]


def test_compiled_failed_legacy_ok_can_fallback_to_legacy(monkeypatch):
    from services.grading_adapter import normalize_solution_for_render
    from tests.test_p29_ir_shadow_mode import _valid_ir
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)
    answer, structured = _valid_solution_payload()

    out = normalize_solution_for_render({
        "standard_answer": answer,
        "_structured": structured,
        "_solution_ir": _valid_ir(step_count=1),
    })

    assert out["_used_compiled_standard_answer"] is False
    assert out["standard_solution_source"] == "legacy"
    assert out["standard_answer"] == answer
    assert out["standard_solution_status"] == "ready"
