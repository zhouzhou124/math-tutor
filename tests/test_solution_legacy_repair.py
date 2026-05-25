"""P13-7: Solution legacy repair + polisher \text{中文} split tests."""

import pytest
from services.solution_legacy_repair import (
    repair_legacy_solution_text,
    normalize_final_choice_text,
)


class TestRepairLegacySolutionText:
    def test_removes_final_answer_before_step_heading(self):
        text = "最终答案： ## 步骤1：写出矩阵"
        out = repair_legacy_solution_text(text)
        assert "最终答案：" not in out
        assert "步骤1" in out

    def test_wraps_bare_lambda_arrow_line(self):
        text = (
            r"a=-4, \lambda_1=0, \lambda_2=\lambda_3=-6 "
            r"\Rightarrow \text{正交变换下标准型为} -6y_1^2-6y_2^2"
        )
        out = repair_legacy_solution_text(text)
        assert "$$" in out
        assert r"\lambda_1" in out

    def test_normalizes_text_choose(self):
        text = r"最终答案： a=-4, \text{选} (B)"
        out = repair_legacy_solution_text(text)
        assert r"\text{选}" not in out
        assert "选 B" in out

    def test_preserves_plain_text(self):
        text = "步骤1：首先写出矩阵 $A$ 的特征方程。"
        out = repair_legacy_solution_text(text)
        assert "步骤1" in out
        assert "矩阵" in out

    def test_collapses_blank_lines(self):
        text = "步骤1：\n\n\n\n步骤2："
        out = repair_legacy_solution_text(text)
        assert "\n\n\n\n" not in out


class TestNormalizeFinalChoiceText:
    def test_basic(self):
        out = normalize_final_choice_text(r"a=-4, \text{选} (B)")
        assert r"\text{选}" not in out
        assert "选 B" in out

    def test_chinese_paren(self):
        out = normalize_final_choice_text(r"a=-4, \text{选}（B）")
        assert "选 B" in out


class TestPolisherChineseTextSplit:
    def test_splits_chinese_text_in_latex_block(self):
        from services.solution_polisher import polish_solution
        sol = {
            "steps": [{
                "label": "步骤1",
                "blocks": [{
                    "type": "latex",
                    "display": "block",
                    "content": (
                        r"a=-4 \Rightarrow "
                        r"\text{正交变换下标准型为} "
                        r"-6y_1^2"
                    ),
                }]
            }]
        }
        out = polish_solution(sol)
        blocks = out["steps"][0]["blocks"]
        assert any(b["type"] == "text" and "正交变换" in b["content"]
                   for b in blocks)
        assert all("正交变换" not in b.get("content", "")
                   for b in blocks if b["type"] == "latex")

    def test_keeps_plain_latex_block(self):
        from services.solution_polisher import polish_solution
        sol = {
            "steps": [{
                "label": "步骤1",
                "blocks": [{
                    "type": "latex", "display": "block",
                    "content": r"\lambda_1=a+4",
                }]
            }]
        }
        out = polish_solution(sol)
        assert out["steps"][0]["blocks"][0]["content"] == r"\lambda_1=a+4"

    def test_no_chinese_text_no_change(self):
        from services.solution_polisher import polish_solution
        sol = {
            "steps": [{
                "label": "步骤1",
                "blocks": [
                    {"type": "latex", "display": "block",
                     "content": r"a=-4, \lambda_1=0"},
                    {"type": "text", "content": "所以结论成立。"},
                ]
            }]
        }
        out = polish_solution(sol)
        assert len(out["steps"][0]["blocks"]) == 2


class TestRealQuadraticSurfaceCase:
    def test_full_repair_chain(self):
        text = (
            "## 步骤4：\n"
            "写出标准型。\n"
            r"a=-4, \lambda_1=0, \lambda_2=\lambda_3=-6 "
            r"\Rightarrow \text{正交变换下标准型为} -6y_1^2-6y_2^2"
            "\n## 步骤5：\n"
            r"\text{正交变换下标准型为} -6y_1^2-6y_2^2 "
            r"\Rightarrow \text{选}(B)"
        )
        out = repair_legacy_solution_text(text)
        assert "$$" in out
        assert r"\text{选}" not in out
        assert "选 B" in out
        assert "步骤4" in out
        assert "步骤5" in out


class TestRepairBrokenFrac:
    def test_repair_frac_multiline(self):
        from services.solution_legacy_repair import repair_broken_frac_blocks
        text = r"""
\leq \frac{}
x_3-x_2
}{
x_3-x_1
} f(x_1)
"""
        out = repair_broken_frac_blocks(text)
        assert r"\frac{x_3-x_2}{x_3-x_1}" in out
        assert r"\frac{}" not in out
        assert "}{\n" not in out

    def test_repair_frac_inline(self):
        from services.solution_legacy_repair import repair_broken_frac_blocks
        text = r"\frac{} x_2-x_1 }{ x_3-x_1 } f(x_3)"
        out = repair_broken_frac_blocks(text)
        assert r"\frac{x_2-x_1}{x_3-x_1}" in out

    def test_normal_frac_unchanged(self):
        from services.solution_legacy_repair import repair_broken_frac_blocks
        text = r"\frac{x_3-x_2}{x_3-x_1}"
        out = repair_broken_frac_blocks(text)
        assert r"\frac{x_3-x_2}{x_3-x_1}" in out

    def test_full_legacy_repair_includes_frac_fix(self):
        from services.solution_legacy_repair import repair_legacy_solution_text
        text = r"""
步骤1：由凸函数定义
\leq \frac{}
x_3-x_2
}{
x_3-x_1
} f(x_1)
"""
        out = repair_legacy_solution_text(text)
        assert r"\frac{x_3-x_2}{x_3-x_1}" in out
        assert "步骤1" in out

    def test_empty_input(self):
        from services.solution_legacy_repair import repair_broken_frac_blocks
        assert repair_broken_frac_blocks("") == ""


class TestBrokenLatexFragmentDetection:
    def test_detects_empty_frac(self):
        from services.solution_quality import count_broken_latex_fragments
        assert count_broken_latex_fragments(r"\frac{} x }{ y }") > 0

    def test_clean_text_scores_zero(self):
        from services.solution_quality import count_broken_latex_fragments
        assert count_broken_latex_fragments(r"\frac{x}{y} + \frac{a}{b}") == 0

    def test_has_broken_helper(self):
        from services.solution_quality import has_broken_latex_fragments
        assert has_broken_latex_fragments(r"\frac{}") is True
        assert has_broken_latex_fragments(r"\frac{x}{y}") is False

    def test_orphan_brace_line_detected(self):
        from services.solution_quality import count_broken_latex_fragments
        text = "步骤1\n}\n{"
        assert count_broken_latex_fragments(text) >= 1

    def test_half_frac_detected(self):
        from services.solution_quality import count_broken_latex_fragments
        assert count_broken_latex_fragments(r"\frac{f(x)-f(u)}") > 0


class TestMojibakeAndSplitFrac:
    def test_clean_mojibake_tokens(self):
        from services.solution_legacy_repair import clean_mojibake_tokens
        text = "两式相加 �A0� 代入已知不等式"
        out = clean_mojibake_tokens(text)
        assert "�" not in out
        assert "两式相加" in out

    def test_repair_split_frac_with_braced_denominator(self):
        from services.solution_legacy_repair import repair_split_frac_denominator
        text = r"\frac{f(x_3)-f(x_1)}" + "\n" + r"{x_3-x_1}"
        out = repair_split_frac_denominator(text)
        assert r"\frac{f(x_3)-f(x_1)}{x_3-x_1}" in out

    def test_repair_split_frac_with_plain_denominator(self):
        from services.solution_legacy_repair import repair_split_frac_denominator
        text = r"\frac{f(x_0)-f(u)}" + "\n" + r"x_0-u"
        out = repair_split_frac_denominator(text)
        assert r"\frac{f(x_0)-f(u)}{x_0-u}" in out

    def test_full_repair_cleans_mojibake_and_split_frac(self):
        from services.solution_legacy_repair import repair_legacy_solution_text
        text = "得 �A0� " + r"\frac{f(x_0)-f(u)}" + "\n" + "x_0-u"
        out = repair_legacy_solution_text(text)
        assert "�" not in out
        assert r"\frac{f(x_0)-f(u)}{x_0-u}" in out
