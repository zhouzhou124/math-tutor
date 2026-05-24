"""Path-level business tests — verify grading flow logic without real LLM."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════
# Group 1: solution_has_substance
# ═══════════════════════════════════════════════

def test_solution_has_substance_empty():
    from services.grading_adapter import solution_has_substance
    assert not solution_has_substance({"standard_answer": ""})


def test_solution_has_substance_short():
    from services.grading_adapter import solution_has_substance
    assert not solution_has_substance({"standard_answer": "x=1"})


def test_solution_has_substance_long():
    from services.grading_adapter import solution_has_substance
    ans = "## 步骤1：分析\n" + "详细推导" * 30
    assert solution_has_substance({"standard_answer": ans})


def test_solution_has_substance_structured():
    from services.grading_adapter import solution_has_substance
    blocks = [{"type": "latex", "content": "x = " + "1" * 100}]
    struc = {"steps": [{"label": "步骤1", "blocks": blocks}]}
    assert solution_has_substance({"standard_answer": "", "_structured": struc})


# ═══════════════════════════════════════════════
# Group 2: is_empty_shell
# ═══════════════════════════════════════════════

def test_is_empty_shell_metadata_only():
    from services.grading_adapter import is_empty_shell
    text = "## 关键知识点\n- 积分\n## 易错提示\n- 符号错误"
    assert is_empty_shell(text)


def test_is_empty_shell_with_steps():
    from services.grading_adapter import is_empty_shell
    text = "## 关键知识点\n## 步骤1：求导\n详细计算\n## 最终答案\nx=1"
    assert not is_empty_shell(text)


def test_is_empty_shell_plain_text():
    from services.grading_adapter import is_empty_shell
    assert not is_empty_shell("这是普通答案文字")


# ═══════════════════════════════════════════════
# Group 3: normalize_error_record contract
# ═══════════════════════════════════════════════

def test_normalize_error_record_required_keys():
    from services.grading_adapter import normalize_error_record
    rec = normalize_error_record({"question_id": "q1"})
    required = ["question_id", "student_answer", "score", "max_score",
                "is_correct", "error_type", "weak_points", "recommendations",
                "knowledge_points", "engine", "confidence", "timestamp",
                "question_preview", "wrong_reason_short", "semantic_tags"]
    for k in required:
        assert k in rec, f"Missing: {k}"


def test_normalize_error_record_coerces_types():
    from services.grading_adapter import normalize_error_record
    rec = normalize_error_record({})
    assert isinstance(rec["score"], int)
    assert isinstance(rec["confidence"], float)
    assert isinstance(rec["weak_points"], list)
    assert isinstance(rec["semantic_tags"], list)


def test_normalize_error_record_preserves_fields():
    from services.grading_adapter import normalize_error_record
    raw = {
        "question_id": "q1", "student_answer": "ans", "score": 3,
        "max_score": 10, "is_correct": False, "error_type": "计算错误",
        "wrong_reason_short": "忘了加C", "question_preview_hash": "a3f2",
        "render_cost_level": "HIGH",
    }
    rec = normalize_error_record(raw)
    assert rec["question_id"] == "q1"
    assert rec["score"] == 3
    assert rec["wrong_reason_short"] == "忘了加C"
    assert rec["render_cost_level"] == "HIGH"


# ═══════════════════════════════════════════════
# Group 4: normalize_solution_for_render
# ═══════════════════════════════════════════════

def test_normalize_solution_for_render_adds_structured():
    from services.grading_adapter import normalize_solution_for_render
    s = normalize_solution_for_render({"standard_answer": "x=1"})
    assert "_structured" in s


def test_normalize_solution_for_render_preserves_existing_structured():
    from services.grading_adapter import normalize_solution_for_render
    s = normalize_solution_for_render({
        "standard_answer": "x=1",
        "_structured": {"steps": [{"label": "step"}]},
    })
    # Polisher normalizes labels → "步骤1", but preserves step data
    assert s["_structured"]["steps"][0]["label"] in ("step", "步骤1")


# ═══════════════════════════════════════════════
# Group 5: grading adapter contract preservation
# ═══════════════════════════════════════════════

def test_grading_result_preserves_method_matched():
    from services.grading_adapter import normalize_grading_result
    r = normalize_grading_result({"total": 8, "method_matched": "柯西法"})
    assert r["method_matched"] == "柯西法"


def test_grading_result_preserves_obligation_warning():
    from services.grading_adapter import normalize_grading_result
    r = normalize_grading_result({"total": 6, "_obligation_warning": "缺步骤"})
    assert r["_obligation_warning"] == "缺步骤"


def test_solution_preserves_ai_flags():
    from services.grading_adapter import normalize_standard_solution
    s = normalize_standard_solution({
        "_ai_unverified": True, "_ai_consistency_warning": True,
        "_solver_fallback": True,
    })
    assert s["_ai_unverified"] is True
    assert s["_ai_consistency_warning"] is True
    assert s["_solver_fallback"] is True


# ═══════════════════════════════════════════════
# Group 6: grading_task_runner
# ═══════════════════════════════════════════════

def test_restore_results_to_plain_state():
    """restore_results_to_session works with a plain dict (not st.session_state)."""
    from services.grading_task_runner import restore_results_to_session
    import json

    state = {}
    gr_json = json.dumps({"total": 8, "engine": "test"})
    sa_json = json.dumps({"standard_answer": "x=1"})
    task = {
        "grading_result_json": gr_json,
        "standard_answer_json": sa_json,
        "task_id": "task_1",
        "user_id": "u1",
        "selected_q_json": None,
        "error_record_json": None,
    }
    restore_results_to_session(task, session_state=state, memory=None)
    assert state["answer_view_mode"] is True
    assert state["grading_result"]["total"] == 8
    assert state["standard_answer"]["standard_answer"] == "x=1"


# ═══════════════════════════════════════════════
# Group 7: SolutionPolisher
# ═══════════════════════════════════════════════

def test_polisher_removes_leading_punctuation():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "，化简得"}
    ]}]}
    out = polish_solution(sol)
    assert out["steps"][0]["blocks"][0]["content"].startswith("化简得")


def test_polisher_drops_punctuation_only_block():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "。"},
        {"type": "text", "content": "代入原方程"}
    ]}]}
    out = polish_solution(sol)
    assert len(out["steps"][0]["blocks"]) == 1


def test_polisher_merges_adjacent_text_blocks():
    from services.solution_polisher import merge_adjacent_text_blocks
    blocks = [
        {"type": "text", "content": "代入原方程"},
        {"type": "text", "content": "化简得"},
    ]
    out = merge_adjacent_text_blocks(blocks)
    assert "代入原方程" in out[0]["content"]
    assert "化简得" in out[0]["content"]


def test_polisher_drops_orphan_formula_number():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "。"},
        {"type": "text", "content": "(1)"},
        {"type": "text", "content": "代入原方程"},
    ]}]}
    out = polish_solution(sol)
    contents = [b["content"] for b in out["steps"][0]["blocks"] if b["type"] == "text"]
    assert "(1)" not in " ".join(contents)
    assert any("代入原方程" in c for c in contents)


def test_polisher_keeps_latex_blocks():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "代入得"},
        {"type": "latex", "display": "block", "content": "x=1"}
    ]}]}
    out = polish_solution(sol)
    assert out["steps"][0]["blocks"][1]["type"] == "latex"
    assert out["steps"][0]["blocks"][1]["content"] == "x=1"


def test_polisher_strips_bullet_prefix():
    from services.solution_polisher import strip_bullet_prefix
    assert strip_bullet_prefix("• 代入原方程") == "代入原方程"



def test_polisher_keeps_formula_tag_inside_latex():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "latex", "display": "block", "content": r"x=1 \tag{1}"}
    ]}]}
    out = polish_solution(sol)
    assert out["steps"][0]["blocks"][0]["content"] == r"x=1 \tag{1}"


# ═══════════════════════════════════════════════
# Group 8: P6-4 — context-aware periods + spacing artifacts
# ═══════════════════════════════════════════════

def test_polisher_no_period_before_inline_latex():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "将"},
        {"type": "latex", "display": "inline", "content": "a,Aa,A^2"},
        {"type": "text", "content": "用特征向量基线性表示"},
    ]}]}
    out = polish_solution(sol)
    blocks = out["steps"][0]["blocks"]
    assert blocks[0]["content"] == "将"
    assert blocks[2]["content"].startswith("用特征向量基线性表示")


def test_polisher_no_period_connector_before_inline():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "因为"},
        {"type": "latex", "display": "inline", "content": "x_1,x_2,x_3"},
        {"type": "text", "content": "是实对称矩阵的特征向量"},
    ]}]}
    out = polish_solution(sol)
    assert out["steps"][0]["blocks"][0]["content"] == "因为"


def test_polisher_adds_period_for_complete_sentence():
    from services.solution_polisher import polish_solution
    sol = {"steps": [{"label": "步骤1", "blocks": [
        {"type": "text", "content": "因此矩阵可逆"},
    ]}]}
    out = polish_solution(sol)
    assert out["steps"][0]["blocks"][0]["content"] == "因此矩阵可逆。"


def test_clean_latex_spacing_double_slash():
    from latex_utils import clean_latex_spacing_artifacts
    s = clean_latex_spacing_artifacts("a\\\\[2mm]b")
    assert "[2mm]" not in s


def test_clean_latex_spacing_bare():
    from latex_utils import clean_latex_spacing_artifacts
    s = clean_latex_spacing_artifacts("a [2mm] b")
    assert "[2mm]" not in s


if __name__ == "__main__":
    tests = [
        test_solution_has_substance_empty,
        test_solution_has_substance_short,
        test_solution_has_substance_long,
        test_solution_has_substance_structured,
        test_is_empty_shell_metadata_only,
        test_is_empty_shell_with_steps,
        test_is_empty_shell_plain_text,
        test_normalize_error_record_required_keys,
        test_normalize_error_record_coerces_types,
        test_normalize_error_record_preserves_fields,
        test_normalize_solution_for_render_adds_structured,
        test_normalize_solution_for_render_preserves_existing_structured,
        test_grading_result_preserves_method_matched,
        test_grading_result_preserves_obligation_warning,
        test_solution_preserves_ai_flags,
        test_restore_results_to_plain_state,
        test_polisher_removes_leading_punctuation,
        test_polisher_drops_punctuation_only_block,
        test_polisher_merges_adjacent_text_blocks,
        test_polisher_keeps_latex_blocks,
        test_polisher_strips_bullet_prefix,
        test_polisher_drops_orphan_formula_number,
        test_polisher_keeps_formula_tag_inside_latex,
        test_polisher_no_period_before_inline_latex,
        test_polisher_no_period_connector_before_inline,
        test_polisher_adds_period_for_complete_sentence,
        test_clean_latex_spacing_double_slash,
        test_clean_latex_spacing_bare,
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
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
