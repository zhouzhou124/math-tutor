"""P10 tests — model router, solution quality, grading quality, timing utils."""

import pytest
from services.model_router import route_model, ModelRoute
from services.solution_quality import score_solution_quality
from services.grading_quality import validate_grading_result_contract


# ═══════════════════════════════════════════════
#  Model router
# ═══════════════════════════════════════════════

class TestModelRouter:
    def test_choice_grading_is_local(self):
        r = route_model("choice_grading")
        assert r.model == "local"
        assert r.max_tokens == 0

    def test_fill_compare_is_local(self):
        r = route_model("fill_compare")
        assert r.model == "local"

    def test_hard_problem_solution_detail_uses_strong_model(self):
        r = route_model("solution_detail", difficulty="难")
        assert r.model == "deepseek-v4-pro"

    def test_easy_problem_solution_detail_uses_fast_model(self):
        r = route_model("solution_detail", difficulty="中等")
        assert r.model == "deepseek-chat"

    def test_diagnosis_uses_fast_model(self):
        r = route_model("diagnosis")
        assert r.model == "deepseek-chat"

    def test_default_route(self):
        r = route_model("unknown_task")
        assert r.model == "deepseek-chat"


# ═══════════════════════════════════════════════
#  Solution quality
# ═══════════════════════════════════════════════

def _make_block(typ: str, content: str, display: str = "inline") -> dict:
    return {"type": typ, "content": content, "display": display}


class TestSolutionQuality:
    def test_missing_final_answer_deducts(self):
        sol = {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [
                _make_block("text", "求导"),
                _make_block("latex", "f'(x) = 2x"),
            ]},
            {"label": "步骤2", "blocks": [
                _make_block("text", "令导数为零"),
                _make_block("latex", "2x = 0"),
            ]},
        ]}}
        q = score_solution_quality(sol)
        assert q["score"] < 90
        assert any("final_answer" in i for i in q["issues"])

    def test_chinese_in_latex_block_deducts(self):
        sol = {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [
                _make_block("text", "求导"),
                _make_block("latex", "f'(x) = 2x 所以"),
            ]},
        ], "final_answer": {"type": "latex", "content": "x=0"}}}
        q = score_solution_quality(sol)
        # "所以" in latex block should trigger issue
        assert any("中文" in i for i in q["issues"])

    def test_latex_cmd_in_text_block_deducts(self):
        sol = {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [
                _make_block("text", "求导 \\frac{d}{dx}"),
                _make_block("latex", "f'(x) = 2x"),
            ]},
        ], "final_answer": {"type": "latex", "content": "x=0"}}}
        q = score_solution_quality(sol)
        assert any("LaTeX" in i for i in q["issues"])

    def test_perfect_solution_scores_high(self):
        sol = {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [
                _make_block("text", "对函数求导"),
                _make_block("latex", "f'(x) = 2x - 2"),
            ]},
            {"label": "步骤2", "blocks": [
                _make_block("text", "令导数等于零，解方程"),
                _make_block("latex", "2x - 2 = 0 \\Rightarrow x = 1"),
            ]},
            {"label": "步骤3", "blocks": [
                _make_block("text", "代入原函数得极值"),
                _make_block("latex", "f(1) = 1 - 2 + 3 = 2"),
            ]},
        ], "final_answer": {"type": "latex", "content": "x=1, f(1)=2"}}}
        q = score_solution_quality(sol)
        assert q["score"] >= 90
        assert q["latex_blocks"] >= 3
        assert q["text_blocks"] >= 3

    def test_no_latex_blocks_deducts(self):
        sol = {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [_make_block("text", "说明")]},
            {"label": "步骤2", "blocks": [_make_block("text", "结论")]},
        ], "final_answer": {"type": "text", "content": "答案"}}}
        q = score_solution_quality(sol)
        assert any("缺少关键公式" in i for i in q["issues"])


# ═══════════════════════════════════════════════
#  Grading quality
# ═══════════════════════════════════════════════

class TestGradingQuality:
    def test_valid_result_passes(self):
        gr = {
            "total": 8, "step_score": 5, "result_score": 3,
            "deductions": [{"reason": "符号错误", "points": 2}],
            "comment": "步骤正确但最终符号有误",
            "step_analysis": [],
        }
        v = validate_grading_result_contract(gr, total_score=10)
        assert v["valid"]

    def test_score_out_of_range_reports_issue(self):
        gr = {"total": 15, "step_score": 10, "result_score": 5}
        v = validate_grading_result_contract(gr, total_score=10)
        assert not v["valid"]
        assert any("超出满分" in i for i in v["issues"])

    def test_negative_score_reports_issue(self):
        gr = {"total": -3}
        v = validate_grading_result_contract(gr, total_score=10)
        assert not v["valid"]
        assert any("负" in i for i in v["issues"])

    def test_low_score_without_deductions_reports_issue(self):
        gr = {"total": 3, "deductions": []}
        v = validate_grading_result_contract(gr, total_score=10)
        assert not v["valid"]
        assert any("扣分" in i for i in v["issues"])

    def test_non_perfect_without_comment_reports_issue(self):
        gr = {"total": 7, "deductions": [{"reason": "x", "points": 3}], "comment": ""}
        v = validate_grading_result_contract(gr, total_score=10)
        assert not v["valid"]
        assert any("评语" in i for i in v["issues"])

    def test_non_numeric_total_reports_issue(self):
        gr = {"total": "abc"}
        v = validate_grading_result_contract(gr, total_score=10)
        assert not v["valid"]
        assert any("不是数字" in i for i in v["issues"])


# ═══════════════════════════════════════════════
#  Timing utils
# ═══════════════════════════════════════════════

class TestTimingUtils:
    def test_timed_stage_records_ms(self):
        from services.timing_utils import timed_stage
        timing = {}
        with timed_stage(timing, "test"):
            pass
        assert "test_ms" in timing
        assert isinstance(timing["test_ms"], int)
        assert timing["test_ms"] >= 0

    def test_multiple_stages_all_recorded(self):
        from services.timing_utils import timed_stage
        timing = {}
        with timed_stage(timing, "a"):
            pass
        with timed_stage(timing, "b"):
            pass
        assert "a_ms" in timing
        assert "b_ms" in timing

    def test_format_timing_summary(self):
        from services.timing_utils import format_timing_summary
        timing = {"solution_ms": 8421, "grading_ms": 3760, "diagnosis_ms": 910}
        s = format_timing_summary(timing)
        assert "solution:8.4s" in s
        assert "grading:3.7s" in s or "grading:3.8s" in s
        assert "diagnosis:0.9s" in s
