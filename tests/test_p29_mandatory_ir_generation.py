"""P29-6.2: newly generated standard answers must be IR-backed."""


def _valid_ir():
    from tests.test_p29_ir_shadow_mode import _valid_ir as make_ir

    return make_ir()


def _legacy_answer():
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload

    answer, _structured = _valid_solution_payload()
    return answer


def _legacy_ok_markdown():
    from semantic_output import validate_canonical_ir
    from services.solution_markdown_compiler import compile_canonical_ir_to_markdown

    model, errors, _ = validate_canonical_ir(_valid_ir())
    assert not errors
    return compile_canonical_ir_to_markdown(model.model_dump())


def test_new_generation_without_ir_retries_once(monkeypatch):
    from agents.solver_agent import SolverAgent
    from services.solution_service import SolutionService

    calls = []

    def fake_solve(self, **kwargs):
        calls.append(kwargs["question"])
        if len(calls) == 1:
            return {"success": True, "standard_answer": _legacy_answer(), "steps": []}
        ir = _valid_ir()
        return {
            "success": True,
            "standard_answer": "legacy answer",
            "steps": [],
            "_canonical_ir": ir,
            "_solution_ir": ir,
        }

    monkeypatch.setattr(SolverAgent, "solve", fake_solve)

    result = SolutionService(client=object(), model="m").build(
        question="求方程的解。",
        selected_q={"question_type": "解答题", "score": 10},
        ocr_data={},
    )

    assert len(calls) == 2
    assert "missing_solution_ir" in calls[1]
    assert result["standard_solution_source"] == "compiled_ir"
    assert result["_used_compiled_standard_answer"] is True
    assert result["standard_solution_status"] == "ready"


def test_retry_still_without_ir_fails_and_clears_render_fields(monkeypatch):
    from agents.solver_agent import SolverAgent
    from services.solution_service import SolutionService

    monkeypatch.setattr(
        SolverAgent,
        "solve",
        lambda self, **kw: {
            "success": True,
            "standard_answer": '<span style="color:red">legacy only</span>' + _legacy_answer(),
            "steps": [{"content": "legacy step"}],
            "_structured": {"steps": [{"blocks": [{"content": "legacy structured"}]}]},
        },
    )

    result = SolutionService(client=object(), model="m").build(
        question="求方程的解。",
        selected_q={"question_type": "解答题", "score": 10},
        ocr_data={},
    )

    assert result["standard_solution_status"] == "failed"
    assert result["standard_solution_source"] == "failed"
    assert result["standard_answer"] == ""
    assert result["steps"] == []
    assert result["_structured"] is None
    assert result["_should_regenerate"] is True
    assert "&lt;span" in result["_failed_raw_preview"]


def test_retry_with_valid_ir_becomes_compiled_ready(monkeypatch):
    from agents.solver_agent import SolverAgent
    from services.solution_service import SolutionService

    calls = {"n": 0}

    def fake_solve(self, **kwargs):
        calls["n"] += 1
        ir = _valid_ir()
        if calls["n"] == 1:
            return {"success": True, "standard_answer": _legacy_answer(), "steps": []}
        return {
            "success": True,
            "standard_answer": "legacy answer",
            "_canonical_ir": ir,
            "_solution_ir": ir,
            "steps": [],
        }

    monkeypatch.setattr(SolverAgent, "solve", fake_solve)

    result = SolutionService(client=object(), model="m").build(
        question="求方程的解。",
        selected_q={"question_type": "解答题", "score": 10},
        ocr_data={},
    )

    assert result["standard_solution_status"] == "ready"
    assert result["standard_solution_source"] == "compiled_ir"
    assert result["standard_answer"].startswith("## 标准解答")


def test_legacy_ok_new_generation_without_ir_is_not_cached(monkeypatch):
    import views.grading_page as page

    called = {"saved": False}
    monkeypatch.setattr(
        page,
        "save_as_canonical_solution",
        lambda *args, **kwargs: called.__setitem__("saved", True) or True,
    )

    ok = page._cache_detailed_answer(
        {"question_id": "q1"},
        _legacy_answer(),
        model="m",
        solution={"standard_answer": _legacy_answer()},
    )

    assert ok is False
    assert called["saved"] is False


def test_old_legacy_cache_ok_still_displays_compatibly(monkeypatch):
    from services.solution_service import SolutionService

    result = SolutionService(client=object(), model="m").build(
        selected_q={
            "question_id": "q1",
            "question_type": "解答题",
            "score": 10,
            "standard_answer": _legacy_ok_markdown(),
        },
        ocr_data={},
    )

    assert result["standard_solution_status"] == "ready"
    assert result["standard_solution_source"] in ("legacy", "compiled_ir")
    assert result["standard_answer"]


def test_mandatory_ir_failed_state_blocks_render_fields(monkeypatch):
    from agents.solver_agent import SolverAgent
    from services.solution_service import SolutionService
    from views.grading_page import _should_block_standard_solution_render

    monkeypatch.setattr(
        SolverAgent,
        "solve",
        lambda self, **kw: {"success": True, "standard_answer": _legacy_answer(), "steps": []},
    )

    result = SolutionService(client=object(), model="m").build(
        question="求方程的解。",
        selected_q={"question_type": "解答题", "score": 10},
        ocr_data={},
    )

    assert _should_block_standard_solution_render({}, result)
    assert result["standard_answer"] == ""
    assert result["steps"] == []
    assert result["_structured"] is None
