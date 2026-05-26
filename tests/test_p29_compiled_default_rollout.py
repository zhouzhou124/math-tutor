"""P29-6: compiled CanonicalIR is on by default with safe fallback."""

import copy


def _valid_ir(step_count: int = 2):
    from tests.test_p29_ir_shadow_mode import _valid_ir as make_ir

    return make_ir(step_count=step_count)


def _valid_solution_payload():
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload as make_payload

    return make_payload()


def test_shadow_defaults_to_true(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["ir_shadow_enabled"] is True
    assert out["_compiled_standard_answer"].startswith("## 标准解答")


def test_compiled_output_defaults_to_true(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["_used_compiled_standard_answer"] is True
    assert out["standard_solution_source"] == "compiled_ir"
    assert out["standard_answer"].startswith("## 标准解答")


def test_default_compiled_ok_uses_compiled_ir(monkeypatch):
    from services.grading_adapter import normalize_standard_solution
    from services.solution_quality import solution_quality_report

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })
    report = solution_quality_report({"standard_answer": out["standard_answer"]})

    assert out["_compiled_quality_report"]["ok"] is True
    assert out["_used_compiled_standard_answer"] is True
    assert report["ok"] is True


def test_default_compiled_failure_falls_back_to_legacy(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(step_count=1),
    })

    assert out["standard_answer"] == "legacy answer"
    assert out["standard_solution_source"] == "legacy"
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"]


def test_default_bad_compiled_latex_falls_back_to_legacy(monkeypatch):
    import services.solution_markdown_compiler as compiler
    import services.solution_quality as quality
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)
    monkeypatch.setattr(compiler, "compile_canonical_ir_to_markdown", lambda ir: "$$$x=1$$$")
    monkeypatch.setattr(
        quality,
        "solution_quality_report",
        lambda solution, question=None: {
            "ok": True,
            "renderable": True,
            "complete": True,
            "detailed": True,
            "covers_requirements": True,
            "logically_plausible": True,
            "issues": [],
            "should_regenerate": False,
        },
    )

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["standard_answer"] == "legacy answer"
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"] == "compiled_bad_latex"


def test_compiled_and_legacy_failed_stays_failed_without_using_compiled(monkeypatch):
    from services.grading_adapter import normalize_solution_for_render

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)
    invalid_ir = _valid_ir()
    invalid_ir["proof_trace"]["steps"][0]["output_state"] = "$x=1$"

    out = normalize_solution_for_render({
        "standard_answer": r"步骤1：坏公式 \right 因此最终答案。",
        "_solution_ir": invalid_ir,
    })

    assert out["_used_compiled_standard_answer"] is False
    assert out["standard_solution_source"] == "failed"
    assert out["standard_solution_status"] == "failed"
    assert out["standard_answer"] == ""
    assert out["_compiled_fallback_reason"].startswith("canonical_ir_invalid")


def test_default_rollout_does_not_write_back_canonical_cache(monkeypatch):
    from services.grading_adapter import SOLUTION_FORMAT_VERSION
    from services.solution_service import SolutionService

    monkeypatch.delenv("ENABLE_SOLUTION_IR_SHADOW", raising=False)
    monkeypatch.delenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", raising=False)
    standard_answer, structured = _valid_solution_payload()
    selected_q = {
        "question_id": "q1",
        "question_type": "解答题",
        "score": 10,
        "canonical_solutions": [{
            "standard_answer": standard_answer,
            "structured": structured,
            "solution_ir": _valid_ir(),
            "format_version": SOLUTION_FORMAT_VERSION,
            "reviewed": True,
        }],
    }
    before = copy.deepcopy(selected_q)

    out = SolutionService().build(selected_q=selected_q)

    assert out["_used_compiled_standard_answer"] is True
    assert out["standard_solution_source"] == "compiled_ir"
    assert selected_q == before
