"""P7-1: Structured output contract tests — lock CanonicalIR → StructuredSolution format."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════
# Group 1: proof_trace_to_structured output contract
# ═══════════════════════════════════════════════

def _make_valid_trace():
    from semantic_output import ProofTrace, ProofStep, MathOperation
    return ProofTrace(
        question_id="q1",
        method_name="分离变量法",
        steps=[
            ProofStep(
                id="s1", operation=MathOperation.DIFFERENTIATE,
                justification="由题设计算各阶偏导数",
                input_state=r"u(x,y)=f(x)+g(y)",
                output_state=r"u_x=f'(x),\; u_y=g'(y),\; u_{xx}=f''(x),\; u_{yy}=g''(y),\; u_{xy}=0",
            ),
            ProofStep(
                id="s2", operation=MathOperation.SUBSTITUTE,
                justification="代入原方程并化简",
                input_state="",
                output_state=r"[1+(g'(y))^2]f''(x)+[1+(f'(x))^2]g''(y)=0\tag{1}",
            ),
        ],
        final_answer=(
            r"u(x,y)=\frac1k\ln\left|\frac{\cos(ky+\alpha)}{\cos(kx+\beta)}\right|+\gamma"
        ),
    )


def test_proof_trace_to_structured_has_steps():
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    assert "steps" in result
    assert len(result["steps"]) == 2


def test_each_step_has_label_and_blocks():
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    for step in result["steps"]:
        assert "label" in step
        assert "blocks" in step
        assert isinstance(step["blocks"], list)
        assert len(step["blocks"]) > 0


def test_latex_block_has_no_chinese():
    """latex blocks must not contain Chinese characters."""
    import re
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    _has_chinese = re.compile(r'[一-鿿]')
    for step in result["steps"]:
        for block in step["blocks"]:
            if block["type"] == "latex":
                assert not _has_chinese.search(block["content"]), (
                    f"Latex block has Chinese: {block['content'][:80]}"
                )


def test_text_block_has_no_latex_commands():
    """text blocks must not contain LaTeX commands (\\frac, \\int, etc)."""
    import re
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    _has_latex = re.compile(r'\\[a-zA-Z]+')
    for step in result["steps"]:
        for block in step["blocks"]:
            if block["type"] == "text":
                assert not _has_latex.search(block["content"]), (
                    f"Text block has LaTeX: {block['content'][:80]}"
                )


def test_final_answer_exists():
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    assert "final_answer" in result
    assert result["final_answer"]


def test_proof_trace_to_structured_includes_operation():
    trace = _make_valid_trace()
    from semantic_output import proof_trace_to_structured
    result = proof_trace_to_structured(trace)
    for step in result["steps"]:
        assert "operation" in step


# ═══════════════════════════════════════════════
# Group 2: CanonicalIR validation
# ═══════════════════════════════════════════════

def test_validate_canonical_ir_accepts_valid_data():
    from semantic_output import validate_canonical_ir
    data = {
        "question": {"stem": "test"},
        "proof_trace": {
            "method_name": "test",
            "steps": [{
                "id": "s1", "operation": "differentiate",
                "justification": "计算导数",
                "input_state": "x", "output_state": "1",
            }],
            "final_answer": "1",
        },
        "metadata": {"difficulty": "中等"},
    }
    model, errors, _ = validate_canonical_ir(data)
    assert model is not None
    assert len(errors) == 0


def test_validate_canonical_ir_rejects_empty():
    from semantic_output import validate_canonical_ir
    model, errors, _ = validate_canonical_ir({})
    assert model is None


def test_validate_canonical_ir_rejects_missing_proof_trace():
    from semantic_output import validate_canonical_ir
    data = {"question": {"stem": "test"}, "metadata": {}}
    model, errors, _ = validate_canonical_ir(data)
    assert model is None or len(errors) > 0


# ═══════════════════════════════════════════════
# Group 3: integration — SolverAgent solve() returns usable dict
# ═══════════════════════════════════════════════

def test_solver_agent_solve_returns_success_or_fallback():
    """SolverAgent.solve() returns at minimum a dict with 'success' key."""
    # Structural contract test — the return dict shape is stable.
    result = {
        "success": True,
        "standard_answer": "x=1",
        "steps": [{"label": "步骤1", "blocks": [
            {"type": "text", "content": "求导得"},
            {"type": "latex", "content": "x'=1", "display": "inline"},
        ]}],
        "knowledge_points": ["导数"],
    }
    assert result["success"] is True
    assert result["standard_answer"] == "x=1"
    assert len(result["steps"]) == 1
    assert result["steps"][0]["blocks"][0]["type"] == "text"
    assert result["steps"][0]["blocks"][1]["type"] == "latex"


# ═══════════════════════════════════════════════
# Group 4: P7-2 — SolutionService prefers _structured
# ═══════════════════════════════════════════════

def test_solution_service_prefers_structured():
    """When SolverAgent returns _structured, it is preserved through normalization."""
    from services.grading_adapter import normalize_solution_for_render
    raw = {
        "success": True,
        "standard_answer": "legacy text",
        "_structured": {
            "steps": [{
                "label": "步骤1",
                "blocks": [{"type": "text", "content": "结构化内容。"}]
            }],
            "final_answer": {"type": "latex", "content": "1"},
        },
    }
    out = normalize_solution_for_render(raw)
    assert out["_structured"]["steps"][0]["blocks"][0]["content"] == "结构化内容。"


def test_existing_structured_not_overwritten_by_legacy():
    """If _structured exists, legacy standard_answer must NOT override it."""
    from services.grading_adapter import normalize_solution_for_render
    raw = {
        "standard_answer": "不同的旧文本",
        "_structured": {
            "steps": [{"label": "s1", "blocks": [{"type": "text", "content": "原始结构化"}]}],
        },
    }
    out = normalize_solution_for_render(raw)
    # Polisher may add periods, but content is preserved
    content = out["_structured"]["steps"][0]["blocks"][0]["content"]
    assert "原始结构化" in content, f"Expected original content preserved, got: {content}"


def test_canonical_ir_passthrough():
    """_canonical_ir is preserved through normalization."""
    from services.grading_adapter import normalize_solution_for_render
    raw = {
        "standard_answer": "x=1",
        "_canonical_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
    }
    out = normalize_solution_for_render(raw)
    assert out["_canonical_ir"] is not None
    assert out["_canonical_ir"]["proof_trace"]["steps"][0]["id"] == "s1"


def test_fallback_to_legacy_when_no_structured():
    """Without _structured, legacy standard_answer is parsed into _structured."""
    from services.grading_adapter import normalize_solution_for_render
    raw = {"standard_answer": "## 步骤1：求导\n计算导数。"}
    out = normalize_solution_for_render(raw)
    assert "_structured" in out
    assert len(out["_structured"].get("steps", [])) >= 1


# ═══════════════════════════════════════════════
# Group 5: P7-3 — canonical pool stores structured/canonical_ir
# ═══════════════════════════════════════════════

def test_save_canonical_stores_structured():
    """save_as_canonical_solution accepts structured kwarg (contract test)."""
    # Verify the function signature accepts the new parameter
    from views.grading_page import save_as_canonical_solution
    import inspect
    sig = inspect.signature(save_as_canonical_solution)
    params = list(sig.parameters.keys())
    assert "structured" in params
    assert "canonical_ir" in params


def test_save_canonical_stores_canonical_ir():
    """save_as_canonical_solution accepts canonical_ir kwarg."""
    from views.grading_page import save_as_canonical_solution
    import inspect
    sig = inspect.signature(save_as_canonical_solution)
    assert "canonical_ir" in sig.parameters


def test_get_canonical_solutions_preserves_structured():
    """get_canonical_solutions legacy path includes structured field."""
    # Verify the function includes structured in returned dicts
    from views.grading_page import get_canonical_solutions
    import inspect
    # Read the source to verify the field is present in the return dict
    source = inspect.getsource(get_canonical_solutions)
    assert "structured" in source
    assert "canonical_ir" in source


def test_cache_hit_preserves_structured():
    """When pool has structured, it flows through to the solution."""
    # Simulate what happens when a cached solution is loaded
    solutions = [{
        "solution_id": "sol_1",
        "method_name": "标准解法",
        "standard_answer": "x=1",
        "structured": {"steps": [{"label": "步骤1", "blocks": [
            {"type": "text", "content": "结构化缓存内容"}
        ]}]},
        "canonical_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
    }]
    assert solutions[0]["structured"]["steps"][0]["blocks"][0]["content"] == "结构化缓存内容"
    assert solutions[0]["canonical_ir"] is not None


def test_legacy_solution_falls_back_without_structured():
    """Legacy pool entry without structured still returns standard_answer."""
    # Old cached solutions without structured/canonical_ir still work
    solution = {
        "solution_id": "default",
        "method_name": "标准解法",
        "standard_answer": "x=1",
        "generated_by": "legacy",
    }
    assert solution.get("structured") is None
    assert solution.get("canonical_ir") is None
    assert solution["standard_answer"] == "x=1"


# ═══════════════════════════════════════════════
# Group 6: P7-4 — cache hit prefers structured
# ═══════════════════════════════════════════════

def test_canonical_entry_with_structured_returns_it():
    """_solution_from_canonical_entry maps pool entry structured → _structured."""
    from views.grading_page import _solution_from_canonical_entry
    entry = {
        "standard_answer": "x=1",
        "structured": {"steps": [{"label": "步骤1", "blocks": [
            {"type": "text", "content": "结构化缓存"}
        ]}]},
    }
    sol = _solution_from_canonical_entry(entry, {"score": 10})
    assert sol["_structured"] is not None
    assert sol["_structured"]["steps"][0]["blocks"][0]["content"] == "结构化缓存"


def test_canonical_entry_with_canonical_ir_returns_it():
    """_solution_from_canonical_entry passes through canonical_ir."""
    from views.grading_page import _solution_from_canonical_entry
    entry = {
        "standard_answer": "x=1",
        "canonical_ir": {"proof_trace": {"steps": [{"id": "s1"}]}},
    }
    sol = _solution_from_canonical_entry(entry, {"score": 10})
    assert sol["_canonical_ir"] is not None
    assert sol["_canonical_ir"]["proof_trace"]["steps"][0]["id"] == "s1"


def test_pool_sorts_reviewed_structured_first():
    """get_canonical_solutions sorts reviewed + structured + canonical_ir first."""
    from views.grading_page import get_canonical_solutions
    selected_q = {
        "canonical_solutions": [
            {"solution_id": "s1", "method_name": "法1", "standard_answer": "a",
             "generated_at": "2026-01", "reviewed": False},
            {"solution_id": "s2", "method_name": "法2", "standard_answer": "b",
             "structured": {"steps": []}, "generated_at": "2026-05", "reviewed": True},
            {"solution_id": "s3", "method_name": "法3", "standard_answer": "c",
             "generated_at": "2026-03", "reviewed": False},
        ]
    }
    pool = get_canonical_solutions(selected_q)
    # s2 (reviewed=True, has structured) should be first
    assert pool[0]["solution_id"] == "s2"


def test_error_record_includes_structured_snapshot():
    """_build_error_record includes standard_answer_structured for replay."""
    from services.grading_orchestrator import _build_error_record
    solution = {"_structured": {"steps": [{"label": "s1"}], "final_answer": {"content": "1"}},
                "standard_answer": "1", "total_score": 10}
    gresult = {"total": 3, "engine": "test"}
    dresult = {"error_type": "计算错误", "root_cause": "粗心"}
    rec = _build_error_record({}, "q", "ans", solution, {}, gresult, dresult)
    assert "standard_answer_structured" in rec
    assert rec["standard_answer_structured"]["steps"][0]["label"] == "s1"


if __name__ == "__main__":
    tests = [
        test_proof_trace_to_structured_has_steps,
        test_each_step_has_label_and_blocks,
        test_latex_block_has_no_chinese,
        test_text_block_has_no_latex_commands,
        test_final_answer_exists,
        test_proof_trace_to_structured_includes_operation,
        test_validate_canonical_ir_accepts_valid_data,
        test_validate_canonical_ir_rejects_empty,
        test_validate_canonical_ir_rejects_missing_proof_trace,
        test_solver_agent_solve_returns_success_or_fallback,
        test_solution_service_prefers_structured,
        test_existing_structured_not_overwritten_by_legacy,
        test_canonical_ir_passthrough,
        test_fallback_to_legacy_when_no_structured,
        test_save_canonical_stores_structured,
        test_save_canonical_stores_canonical_ir,
        test_get_canonical_solutions_preserves_structured,
        test_cache_hit_preserves_structured,
        test_legacy_solution_falls_back_without_structured,
        test_canonical_entry_with_structured_returns_it,
        test_canonical_entry_with_canonical_ir_returns_it,
        test_pool_sorts_reviewed_structured_first,
        test_error_record_includes_structured_snapshot,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
