"""P29-4: CanonicalIR compiler shadow mode tests."""


def _valid_ir(step_count: int = 2):
    steps = [
        {
            "id": "s1",
            "operation": "transform",
            "input_state": "x+1=2",
            "output_state": "x=1",
            "justification": "根据等式性质两边同减 1，得到方程的解。",
            "label": "求解方程",
        }
    ]
    if step_count >= 2:
        steps.append({
            "id": "s2",
            "operation": "check",
            "input_state": "x=1",
            "output_state": "1+1=2",
            "justification": "代回原方程验证左边等于右边，因此结果成立。",
            "label": "验证结果",
        })
    return {
        "agent": "solver",
        "question": {
            "text": "求方程的解。",
            "math_type": "数学一",
            "question_type": "解答题",
            "knowledge_points": ["方程"],
            "total_score": 10,
        },
        "proof_trace": {
            "steps": steps,
            "final_answer": "x=1",
        },
        "metadata": {},
    }


def _valid_structured():
    return {
        "steps": [
            {
                "label": "步骤1：求解方程",
                "body_markdown": "根据等式性质两边同减 $1$，得到方程的解 $x=1$。",
                "blocks": [
                    {"type": "text", "content": "根据等式性质两边同减 1，得到方程的解。"},
                    {"type": "latex", "content": "x=1"},
                ],
            },
            {
                "label": "步骤2：验证结果",
                "body_markdown": "代回原方程验证左边等于右边，因此结果成立。",
                "blocks": [
                    {"type": "text", "content": "代回原方程验证左边等于右边，因此结果成立。"},
                    {"type": "latex", "content": "1+1=2"},
                ],
            },
        ],
        "final_answer": {"type": "latex", "content": "x=1"},
    }


def test_shadow_flag_off_does_not_compile(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "false")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "false")

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["ir_shadow_enabled"] is False
    assert "_compiled_standard_answer" not in out
    assert out.get("_used_compiled_standard_answer") is not True
    assert out["standard_solution_source"] == "legacy"


def test_shadow_flag_on_generates_compiled_answer(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "true")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "false")

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["ir_shadow_enabled"] is True
    assert out["_compiled_from_ir"] is True
    assert out["_compiled_standard_answer"].startswith("## 标准解答")
    assert out["_compiled_quality_report"]["ok"] is True
    assert out["standard_answer"] == "legacy answer"


def test_shadow_mode_does_not_replace_standard_answer(monkeypatch):
    from services.grading_adapter import normalize_solution_for_render

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "true")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "false")

    out = normalize_solution_for_render({
        "standard_answer": "步骤1：旧答案足够长，先根据题意建立方程。步骤2：继续推导，因此最终答案为 $x=1$。",
        "_structured": _valid_structured(),
        "_solution_ir": _valid_ir(),
    })

    assert out["_compiled_standard_answer"]
    assert "旧答案足够长" in out["standard_answer"]


def test_compiled_output_flag_replaces_only_when_quality_passes(monkeypatch):
    from services.grading_adapter import normalize_standard_solution
    from services.solution_quality import solution_quality_report

    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "true")

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["ir_shadow_enabled"] is True
    assert out["_compiled_quality_report"]["ok"] is True
    assert out["standard_answer"].startswith("## 标准解答")
    assert out["standard_solution_source"] == "compiled_ir"
    assert out["_used_compiled_standard_answer"] is True
    assert out["_compiled_fallback_reason"] == ""
    assert solution_quality_report({"standard_answer": out["standard_answer"]})["ok"] is True


def test_compiled_output_flag_does_not_replace_when_quality_fails(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "true")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "true")

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(step_count=1),
    })

    assert out["_compiled_quality_report"]["ok"] is False
    assert out["standard_answer"] == "legacy answer"
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"]


def test_compiled_output_flag_does_not_replace_when_not_renderable(monkeypatch):
    import services.solution_quality as quality
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "true")
    monkeypatch.setattr(
        quality,
        "solution_quality_report",
        lambda solution, question=None: {
            "ok": False,
            "renderable": False,
            "complete": True,
            "detailed": True,
            "covers_requirements": True,
            "logically_plausible": True,
            "issues": ["not_renderable"],
            "should_regenerate": True,
        },
    )

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["standard_answer"] == "legacy answer"
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"] == "compiled_not_renderable"


def test_compiled_output_flag_does_not_replace_when_incomplete(monkeypatch):
    import services.solution_quality as quality
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "true")
    monkeypatch.setattr(
        quality,
        "solution_quality_report",
        lambda solution, question=None: {
            "ok": False,
            "renderable": True,
            "complete": False,
            "detailed": True,
            "covers_requirements": False,
            "logically_plausible": True,
            "issues": ["incomplete"],
            "should_regenerate": True,
        },
    )

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": _valid_ir(),
    })

    assert out["standard_answer"] == "legacy answer"
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"] == "compiled_incomplete"


def test_compiled_output_flag_does_not_replace_when_compiled_too_short(monkeypatch):
    import services.solution_quality as quality
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "true")
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
        "standard_answer": "legacy answer " * 40,
        "_solution_ir": _valid_ir(),
    })

    assert out["standard_answer"].startswith("legacy answer")
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"] == "compiled_too_short"


def test_invalid_solution_ir_records_failure_without_raising(monkeypatch):
    from services.grading_adapter import normalize_standard_solution

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "true")
    invalid_ir = _valid_ir()
    invalid_ir["proof_trace"]["steps"][0]["output_state"] = "$x=1$"

    out = normalize_standard_solution({
        "standard_answer": "legacy answer",
        "_solution_ir": invalid_ir,
    })

    assert out["ir_compile_ok"] is False
    assert "canonical_ir_invalid" in out["ir_compile_error"]
    assert out["_compiled_quality_report"]["ok"] is False
    assert "_compiled_standard_answer" not in out
    assert out["_used_compiled_standard_answer"] is False
    assert out["_compiled_fallback_reason"].startswith("canonical_ir_invalid")


def test_cache_solution_ir_runs_shadow_compiler(monkeypatch):
    from services.grading_adapter import SOLUTION_FORMAT_VERSION
    from services.solution_service import SolutionService
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload

    monkeypatch.setenv("ENABLE_SOLUTION_IR_SHADOW", "true")
    monkeypatch.setenv("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", "false")

    standard_answer, structured = _valid_solution_payload()
    standard_answer = (
        f"{standard_answer} 这个旧答案只作为缓存文本保留，"
        "shadow 编译结果不会覆盖它。"
    )
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

    out = SolutionService().build(selected_q=selected_q)

    assert out["standard_solution_status"] == "ready"
    assert out["_compiled_standard_answer"].startswith("## 标准解答")
    assert "缓存文本" in out["standard_answer"]
