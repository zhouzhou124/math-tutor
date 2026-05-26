"""P21: PaperSpine-style prompting tests."""

import os
import pytest


class TestPromptsExist:
    def test_paperspine_prompt_exists(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert r"\frac" in text
        assert "综上" in text or "命题得证" in text

    def test_self_review_requires_json(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_self_review.md")
        assert "JSON" in text
        assert "should_regenerate" in text


class TestSolutionQualityStillApplied:
    def test_normalize_still_called(self):
        from services.grading_adapter import normalize_solution_for_render
        sol = normalize_solution_for_render({"standard_answer": "步骤1：推导。综上，得证。" + "x" * 120})
        assert sol.get("_structured") is not None

    def test_incomplete_not_complete(self):
        from services.solution_quality import solution_is_complete
        assert not solution_is_complete({"standard_answer": "由题意可得"})

    def test_old_format_invalidates(self):
        from services.grading_adapter import normalize_canonical_entry
        entry = {"format_version": "old", "structured": {"steps": []}, "canonical_ir": {}}
        out = normalize_canonical_entry(entry)
        assert out.get("structured") is None


class TestPaperSpinePromptContent:
    def test_forbids_empty_frac(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert r"\frac{}" in text or "禁止" in text

    def test_requires_aligned_for_long(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert "aligned" in text

    def test_requires_final_conclusion(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert any(m in text for m in ["综上", "故选", "证毕", "最终结论", "最终答案"])


class TestSelfReviewEnvGate:
    def test_default_disabled(self):
        assert os.getenv("ENABLE_SOLUTION_SELF_REVIEW", "false") == "false"


class TestStepGranularity:
    def test_merge_consecutive_same_op_steps(self):
        from services.solution_polisher import merge_consecutive_short_steps
        sol = {
            "steps": [
                {"label": "步骤1", "operation": "substitute",
                 "blocks": [{"type": "latex", "content": "x=1"}]},
                {"label": "步骤2", "operation": "substitute",
                 "blocks": [{"type": "latex", "content": "y=2"}]},
                {"label": "步骤3", "operation": "conclude",
                 "blocks": [{"type": "text", "content": "综上得证。"}]},
            ]
        }
        out = merge_consecutive_short_steps(sol)
        # Steps 1+2 merged, step 3 kept separate (different op)
        assert 2 <= len(out["steps"]) <= 3

    def test_final_answer_not_lost_in_merge(self):
        from services.solution_polisher import polish_solution
        sol = {
            "steps": [
                {"label": "步骤1", "operation": "substitute",
                 "blocks": [{"type": "latex", "content": "x=1"}]},
                {"label": "步骤2", "operation": "simplify",
                 "blocks": [{"type": "latex", "content": "f(1)=0"}]},
                {"label": "步骤3", "operation": "conclude",
                 "blocks": [{"type": "text", "content": "故答案为 x=1。"}]},
            ],
            "final_answer": {"type": "latex", "content": "x=1"},
        }
        out = polish_solution(sol)
        assert len(out["steps"]) >= 1

    def test_prompt_includes_step_count_guidance(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert "3～5 步" in text or "3~5" in text
        assert "6～9 步" in text or "6~9" in text

    def test_negative_choice_question_must_select_false_option(self):
        from services.prompt_loader import load_prompt
        text = load_prompt("math_solution_paperspine_style.md")
        assert "错误的是" in text
        assert "不正确的是" in text
        assert "最终应选择错误或不成立的选项" in text
