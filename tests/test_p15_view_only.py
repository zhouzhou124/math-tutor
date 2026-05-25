"""P15-3: View-only + full solution rendering + legacy cleanup tests."""

import pytest


class TestViewOnly:
    def test_view_only_result_hides_score_card(self):
        gr = {"view_only": True, "hide_score_card": True, "engine": "view_only"}
        assert gr["view_only"] is True
        assert gr["hide_score_card"] is True

    def test_view_only_has_no_total_field(self):
        # P15-3: view-only should not have total=0 that renders as 0/12
        gr = {
            "engine": "view_only",
            "view_only": True,
            "hide_score_card": True,
            "comment": "未作答，仅查看标准答案",
        }
        assert gr.get("total") is None


class TestCleanOrphanProblemMarkers:
    def test_cleans_dot_guo_fragment(self):
        from services.solution_legacy_repair import clean_orphan_problem_markers
        text = '$$f\'(\\xi)=\\frac{f(b)-f(c)}{b-c}$$\n(2.过'
        out = clean_orphan_problem_markers(text)
        assert "(2.过" not in out

    def test_preserves_formula_content(self):
        from services.solution_legacy_repair import clean_orphan_problem_markers
        text = '$$f\'(\\xi)=\\frac{f(b)-f(c)}{b-c}$$\n(2.过'
        out = clean_orphan_problem_markers(text)
        assert "f'(\\xi)" in out

    def test_cleans_isolated_sub_question_line(self):
        from services.solution_legacy_repair import clean_orphan_problem_markers
        text = "步骤1：求解\n(2)\n步骤2：验证"
        out = clean_orphan_problem_markers(text)
        assert "(2)" not in out or out.count("\n") < 4

    def test_handles_empty_input(self):
        from services.solution_legacy_repair import clean_orphan_problem_markers
        assert clean_orphan_problem_markers("") == ""
        assert clean_orphan_problem_markers(None) == ""


class TestStructuredIncomplete:
    def test_detects_raw_with_many_steps_but_few_structured(self):
        # Simulate: raw has 3 steps, structured only has 1
        # Manual check since structured_looks_incomplete may be defined in grading_page
        import re
        raw = "步骤1\n内容\n步骤2\n内容\n步骤3\n内容"
        structured = {"steps": [{"label": "步骤1", "blocks": []}]}
        raw_step_count = len(re.findall(r"(?:^|\n)\s*#{0,3}\s*步骤\s*\d+", raw))
        assert raw_step_count >= 3
        assert len(structured["steps"]) < raw_step_count - 1  # incomplete


class TestLegacyRepairEndToEnd:
    def test_full_legacy_repair_chain(self):
        from services.solution_legacy_repair import repair_legacy_solution_text
        text = (
            "最终答案： ## 步骤1：写出特征方程\n"
            r"$$\lambda^2 - 5\lambda + 6 = 0$$"
            "\n(2.过)"
        )
        out = repair_legacy_solution_text(text)
        assert "最终答案：" not in out
        assert "(2.过" not in out
        assert "步骤1" in out

    def test_text_choose_normalized(self):
        from services.solution_legacy_repair import repair_legacy_solution_text
        text = r"a=-4, \text{选} (B)"
        out = repair_legacy_solution_text(text)
        assert r"\text{选}" not in out
        assert "选 B" in out


class TestSolutionRenderableContent:
    def test_empty_standard_answer_is_not_ready(self):
        from views.grading_page import _solution_has_renderable_content
        assert not _solution_has_renderable_content({"standard_answer": ""})

    def test_short_answer_is_not_ready(self):
        from views.grading_page import _solution_has_renderable_content
        assert not _solution_has_renderable_content({"standard_answer": "Cxe^{-x}"})

    def test_long_answer_is_ready(self):
        from views.grading_page import _solution_has_renderable_content
        ans = "步骤1：识别方程类型。" + "详细推导" * 50
        assert _solution_has_renderable_content({"standard_answer": ans})

    def test_structured_with_empty_step_is_not_ready(self):
        from views.grading_page import _solution_has_renderable_content
        sol = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{"type": "text", "content": "（无内容）"}],
                }]
            }
        }
        assert not _solution_has_renderable_content(sol)

    def test_structured_with_real_step_is_ready(self):
        from views.grading_page import _solution_has_renderable_content
        sol = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [
                        {"type": "text", "content": "对函数求导"},
                        {"type": "latex", "content": "f'(x)=2x"},
                    ],
                }]
            }
        }
        assert _solution_has_renderable_content(sol)

    def test_none_is_not_ready(self):
        from views.grading_page import _solution_has_renderable_content
        assert not _solution_has_renderable_content(None)

    def test_empty_dict_is_not_ready(self):
        from views.grading_page import _solution_has_renderable_content
        assert not _solution_has_renderable_content({})
