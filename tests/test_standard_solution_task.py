"""P30: shared standard-solution task layer."""

import html


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


def _valid_ir(step_count=2):
    from tests.test_p29_ir_shadow_mode import _valid_ir as make_ir

    return make_ir(step_count=step_count)


def test_grading_path_uses_shared_task(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )
    calls = {"builder": 0}

    def builder(*args, **kwargs):
        calls["builder"] += 1
        return {
            "standard_answer": "legacy derivation text " * 10,
            "_solution_ir": _valid_ir(),
        }

    result = build_standard_solution_task(
        "q",
        selected_q={"question_id": "q1"},
        source="grading",
        builder=builder,
    )

    assert calls["builder"] == 1
    assert result["source"] == "grading"
    assert result["standard_solution_task_source"] == "grading"
    assert result["standard_solution_status"] == "ready"


def test_retry_path_uses_shared_task(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )

    result = build_standard_solution_task(
        "q",
        selected_q={"question_id": "q1"},
        force=True,
        force_expansion=True,
        attempt_id="a1",
        source="retry",
        builder=lambda *a, **k: {
            "standard_answer": "retry derivation text " * 10,
            "_solution_ir": _valid_ir(),
        },
    )

    assert result["source"] == "retry"
    assert result["attempt_id"] == "a1"
    assert result["standard_solution_status"] == "ready"


def test_retry_force_bypasses_cache(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    calls = {"cache": 0, "builder": 0}

    def cache(_selected_q):
        calls["cache"] += 1
        return {"standard_answer": "cached answer", "_quality_report": _ok_report()}

    def builder(*args, **kwargs):
        calls["builder"] += 1
        return {
            "standard_answer": "fresh derivation text " * 10,
            "_solution_ir": _valid_ir(),
        }

    monkeypatch.setattr("services.standard_solution_task._cached_solution", cache)

    result = build_standard_solution_task(
        "q",
        selected_q={"question_id": "q1"},
        force=True,
        source="retry",
        builder=builder,
    )

    assert calls["cache"] == 0
    assert calls["builder"] == 1
    assert result["standard_solution_cache_hit"] is False


def test_grading_can_hit_cache_without_builder(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: {
            "standard_answer": "cached derivation text " * 10,
            "standard_solution_status": "ready",
            "_quality_report": _ok_report(),
        },
    )
    calls = {"builder": 0}

    result = build_standard_solution_task(
        "q",
        selected_q={"question_id": "q1"},
        source="grading",
        builder=lambda *a, **k: calls.__setitem__("builder", calls["builder"] + 1),
    )

    assert calls["builder"] == 0
    assert result["standard_solution_cache_hit"] is True
    assert result["standard_solution_status"] == "ready"


def test_compiled_ir_ok_fields_are_consistent_for_grading_and_retry(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )

    def builder(*args, **kwargs):
        return {"standard_answer": "legacy answer", "_solution_ir": _valid_ir()}

    grading = build_standard_solution_task(
        "q", selected_q={"question_id": "q1"}, source="grading", builder=builder
    )
    retry = build_standard_solution_task(
        "q", selected_q={"question_id": "q1"}, source="retry", builder=builder
    )

    common_fields = [
        "standard_solution_status",
        "standard_solution_source",
        "_used_compiled_standard_answer",
        "_compiled_quality_report",
        "_compiled_fallback_reason",
    ]
    for field in common_fields:
        assert grading[field] == retry[field]
    assert grading["standard_solution_source"] == "compiled_ir"


def test_compiled_failed_legacy_ok_falls_back_for_both_paths(monkeypatch):
    from services.grading_adapter import normalize_solution_for_render
    from services.standard_solution_task import build_standard_solution_task
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )
    answer, structured = _valid_solution_payload()

    def builder(*args, **kwargs):
        return normalize_solution_for_render({
            "standard_answer": answer,
            "_structured": structured,
            "_solution_ir": _valid_ir(step_count=1),
        })

    grading = build_standard_solution_task("q", selected_q={}, source="grading", builder=builder)
    retry = build_standard_solution_task("q", selected_q={}, source="retry", builder=builder)

    assert grading["standard_solution_source"] == "legacy"
    assert retry["standard_solution_source"] == "legacy"
    assert grading["standard_solution_status"] == "ready"
    assert retry["standard_solution_status"] == "ready"


def test_no_ir_legacy_failed_hard_gate_for_both_paths(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )

    def builder(*args, **kwargs):
        return {
            "standard_answer": r'<span style="color:red">\right</span>',
            "steps": [{"content": "bad"}],
            "_structured": {"steps": [{"blocks": [{"content": "bad"}]}]},
        }

    grading = build_standard_solution_task("q", selected_q={}, source="grading", builder=builder)
    retry = build_standard_solution_task("q", selected_q={}, source="retry", builder=builder)

    for result in (grading, retry):
        assert result["standard_solution_source"] == "failed"
        assert result["standard_solution_status"] == "failed"
        assert result["standard_answer"] == ""
        assert result["steps"] == []
        assert result["_structured"] is None


def test_failed_candidate_goes_to_debug_not_display(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )
    raw = '<span style="color:red">bad</span>'

    result = build_standard_solution_task(
        "q",
        selected_q={},
        source="retry",
        builder=lambda *a, **k: {"standard_answer": raw},
    )

    assert result["standard_answer"] == ""
    assert result["steps"] == []
    assert result["_structured"] is None
    assert html.escape(raw, quote=True) in result["_debug_raw_standard_answer"]


def test_retry_shared_task_does_not_call_grading_diagnosis_or_mistake(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )
    forbidden = {"called": False}

    def builder(*args, **kwargs):
        return {"standard_answer": "retry derivation text " * 10, "_solution_ir": _valid_ir()}

    result = build_standard_solution_task(
        "q", selected_q={}, source="retry", builder=builder
    )

    assert forbidden["called"] is False
    assert result["source"] == "retry"
    assert result["standard_solution_status"] == "ready"


def test_attempt_id_is_carried_for_retry(monkeypatch):
    from services.standard_solution_task import build_standard_solution_task

    monkeypatch.setattr(
        "services.standard_solution_task._cached_solution",
        lambda selected_q: None,
    )

    result = build_standard_solution_task(
        "q",
        selected_q={},
        source="retry",
        attempt_id="new-attempt",
        builder=lambda *a, **k: {
            "standard_answer": "attempt derivation text " * 10,
            "_solution_ir": _valid_ir(),
        },
    )

    assert result["attempt_id"] == "new-attempt"
