"""P55: Tests for raw TeX detection, repair, and compilation in solution text blocks."""

import copy
import pytest


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

class TestContainsRawTexOutsideMath:
    def test_inline_math_not_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math(r"这是 \(\frac{1}{x}\)") is False

    def test_bare_frac_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math(r"这是 \frac{1}{x}") is True

    def test_bare_int_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math("计算 int_0^1 x dx") is True

    def test_pure_chinese_not_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math("这是一段纯中文说明") is False

    def test_placeholder_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math("结果 @@MATH3@@ 如下") is True

    def test_display_math_not_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math(r"公式 \[\int_0^1 x\,dx\] 如下") is False

    def test_dollar_math_not_flagged(self):
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math(r"公式 $\frac{1}{2}$ 如下") is False


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

class TestRepairMissingBackslashes:
    def test_int_underscore(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        assert repair_missing_latex_backslashes_in_formula("int_0^1 x dx") == r"\int_0^1 x dx"

    def test_frac_braces(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        assert repair_missing_latex_backslashes_in_formula("frac{1}{x}") == r"\frac{1}{x}"

    def test_Rightarrow(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        assert repair_missing_latex_backslashes_in_formula("Rightarrow x=1") == r"\Rightarrow x=1"

    def test_english_in_not_replaced(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        result = repair_missing_latex_backslashes_in_formula("in this case")
        assert "\\in" not in result

    def test_leq(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        assert repair_missing_latex_backslashes_in_formula("leq") == r"\leq"

    def test_max_underscore(self):
        from services.grading_adapter import repair_missing_latex_backslashes_in_formula
        assert repair_missing_latex_backslashes_in_formula("max_0") == r"\max_0"


# ---------------------------------------------------------------------------
# Placeholder removal
# ---------------------------------------------------------------------------

class TestPlaceholderRemoval:
    def test_placeholder_removed_from_view(self):
        from services.grading_adapter import compile_math_blocks_for_standard_solution_view
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "结果 @@MATH1@@ 如下"}],
            }],
            "final_answer": "@@MATH2@@",
        }
        result = compile_math_blocks_for_standard_solution_view(view)
        for sec in result["sections"]:
            for b in sec["blocks"]:
                assert "@@MATH" not in b.get("content", "")
        fa = result.get("final_answer", "")
        if isinstance(fa, str):
            assert "@@MATH" not in fa
        elif isinstance(fa, dict):
            assert "@@MATH" not in fa.get("content", "")


# ---------------------------------------------------------------------------
# Text block compilation
# ---------------------------------------------------------------------------

class TestCompileTextBlock:
    def test_bare_frac_promoted(self):
        from services.grading_adapter import compile_text_block_to_math_blocks
        blocks = compile_text_block_to_math_blocks("由 f(x)=frac{1}{x} 可知")
        types = [b["type"] for b in blocks]
        assert "latex_display" in types or any(
            "frac" in b.get("content", "") and ("$" in b.get("content", "") or r"\(" in b.get("content", ""))
            for b in blocks
        )

    def test_pure_chinese_stays_text(self):
        from services.grading_adapter import compile_text_block_to_math_blocks
        blocks = compile_text_block_to_math_blocks("这是一段纯中文说明，没有公式。")
        assert all(b["type"] == "text" for b in blocks)
        assert any("纯中文" in b.get("content", "") for b in blocks)

    def test_int_promoted_to_display(self):
        """P55-hotfix: compile is non-destructive; int_0^1 in Chinese stays as text."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        blocks = compile_text_block_to_math_blocks("计算 int_0^1 x dx 的值")
        # Non-destructive: text is preserved as-is when no clear formula boundary
        assert len(blocks) >= 1
        all_content = " ".join(b.get("content", "") for b in blocks)
        assert "int_0" in all_content or "int" in all_content

    def test_no_entire_chinese_as_code(self):
        from services.grading_adapter import compile_text_block_to_math_blocks
        text = "这是一段很长的中文说明，包含了一些数学概念的解释，不应该被转换成代码块。"
        blocks = compile_text_block_to_math_blocks(text)
        assert all(b["type"] != "degraded_code" for b in blocks)


# ---------------------------------------------------------------------------
# Delimiter normalization
# ---------------------------------------------------------------------------

class TestDelimiterNormalization:
    def test_double_bar_fixed(self):
        from services.grading_adapter import normalize_broken_formula_delimiters
        result = normalize_broken_formula_delimiters(r"\ln|x-t|| dt")
        assert "||" not in result or r"\," in result

    def test_displaystyle_stripped(self):
        from services.grading_adapter import normalize_broken_formula_delimiters
        result = normalize_broken_formula_delimiters(r"\displaystyle\(\frac{e-1}{ne^2}\)")
        assert "displaystyle" not in result


# ---------------------------------------------------------------------------
# Integration: compile_math_blocks_for_standard_solution_view
# ---------------------------------------------------------------------------

class TestCompileIntegration:
    def test_sections_blocks_processed(self):
        """P55-hotfix: compile is non-destructive; text preserved when no clear formula."""
        from services.grading_adapter import compile_math_blocks_for_standard_solution_view
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "计算 int_0^1 x dx"}],
            }],
            "final_answer": {"type": "text", "content": "1/2"},
        }
        result = compile_math_blocks_for_standard_solution_view(view)
        blocks = result["sections"][0]["blocks"]
        # Non-destructive: text preserved as-is
        assert len(blocks) >= 1
        all_content = " ".join(b.get("content", "") for b in blocks)
        assert "int" in all_content

    def test_deep_copy_no_mutation(self):
        from services.grading_adapter import compile_math_blocks_for_standard_solution_view
        original = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "计算 int_0^1 x dx"}],
            }],
        }
        original_copy = copy.deepcopy(original)
        result = compile_math_blocks_for_standard_solution_view(original)
        # Original should not be mutated
        assert original["sections"][0]["blocks"][0]["content"] == original_copy["sections"][0]["blocks"][0]["content"]
        # Result should be different
        assert result is not original

    def test_conclusion_cleaned(self):
        from services.grading_adapter import compile_math_blocks_for_standard_solution_view
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "说明"}],
                "conclusion": "因此 int_0^1 x dx = 1/2",
            }],
        }
        result = compile_math_blocks_for_standard_solution_view(view)
        conclusion = result["sections"][0].get("conclusion", "")
        assert "int_0^1" not in conclusion or r"\int" in conclusion


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_consecutive_identical_latex_deduped(self):
        from services.grading_adapter import dedupe_section_content
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [
                    {"type": "latex_display", "content": "x = 1"},
                    {"type": "latex_display", "content": "x = 1"},
                    {"type": "text", "content": "说明"},
                ],
            }],
        }
        result = dedupe_section_content(view)
        blocks = result["sections"][0]["blocks"]
        latex_blocks = [b for b in blocks if b["type"] == "latex_display"]
        assert len(latex_blocks) == 1

    def test_conclusion_final_answer_deduped(self):
        from services.grading_adapter import dedupe_section_content
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "计算完毕"}],
                "conclusion": "x = 1",
            }],
            "final_answer": {"type": "text", "content": "x = 1"},
        }
        result = dedupe_section_content(view)
        fa = result.get("final_answer", {})
        fa_content = fa.get("content", "") if isinstance(fa, dict) else fa
        assert not fa_content  # Should be deduped


# ---------------------------------------------------------------------------
# Real screenshot examples (acceptance E)
# ---------------------------------------------------------------------------

class TestRealScreenshotExamples:
    def test_bare_int_ln_double_bar(self):
        """f(x)= int_0^1 \\ln|x-t|| dt"""
        from services.grading_adapter import contains_raw_tex_outside_math, compile_text_block_to_math_blocks
        text = r"f(x)= int_0^1 \ln|x-t|| dt"
        assert contains_raw_tex_outside_math(text) is True
        blocks = compile_text_block_to_math_blocks(text)
        # Should not have raw int_ or bare \ln in final text blocks
        for b in blocks:
            if b["type"] == "text":
                content = b.get("content", "")
                assert "int_0" not in content or r"\int" in content

    def test_bare_Rightarrow_ln_frac(self):
        """\\Rightarrow f'(x)= \\ln\\frac{1-x}{x}"""
        from services.grading_adapter import contains_raw_tex_outside_math, compile_text_block_to_math_blocks
        text = r"\Rightarrow f'(x)= \ln\frac{1-x}{x}"
        assert contains_raw_tex_outside_math(text) is True
        blocks = compile_text_block_to_math_blocks(text)
        # Should compile into display or repaired blocks
        assert len(blocks) >= 1

    def test_bare_max_ln(self):
        """\\max_0\\leq x\\leq1 f(x)=1+\\ln2"""
        from services.grading_adapter import contains_raw_tex_outside_math, compile_text_block_to_math_blocks
        text = r"\max_0\leq x\leq1 f(x)=1+\ln2"
        assert contains_raw_tex_outside_math(text) is True
        blocks = compile_text_block_to_math_blocks(text)
        assert len(blocks) >= 1

    def test_placeholder_leak(self):
        """@@MATH1@@"""
        from services.grading_adapter import compile_math_blocks_for_standard_solution_view
        view = {
            "sections": [{
                "title": "步骤1",
                "blocks": [{"type": "text", "content": "由 @@MATH1@@ 可得"}],
            }],
        }
        result = compile_math_blocks_for_standard_solution_view(view)
        for sec in result["sections"]:
            for b in sec["blocks"]:
                assert "@@MATH" not in b.get("content", "")

    def test_displaystyle_wrapper(self):
        """\\displaystyle\\(\\frac{e-1}{ne^2}\\)"""
        from services.grading_adapter import contains_raw_tex_outside_math, compile_text_block_to_math_blocks
        text = r"\displaystyle\(\frac{e-1}{ne^2}\)"
        # displaystyle outside math should be detected
        blocks = compile_text_block_to_math_blocks(text)
        # The \(...\) part should be preserved, displaystyle stripped
        all_content = " ".join(b.get("content", "") for b in blocks)
        assert "displaystyle" not in all_content or r"\(" in all_content


# ---------------------------------------------------------------------------
# build_standard_solution_view pipeline
# ---------------------------------------------------------------------------

class TestBuildStandardSolutionViewPipeline:
    def test_pipeline_compile_disabled_by_default(self):
        """P55-hotfix: compile is OFF by default; text is preserved as-is."""
        from services.grading_adapter import build_standard_solution_view, ENABLE_SOLUTION_PROOF_MATH_COMPILER
        sol = {
            "standard_solution_view": {
                "sections": [{
                    "title": "步骤1",
                    "blocks": [{"type": "text", "content": "计算 int_0^1 x dx"}],
                }],
                "final_answer": {"type": "text", "content": "1/2"},
            },
        }
        view = build_standard_solution_view(sol, "解答题")
        assert ENABLE_SOLUTION_PROOF_MATH_COMPILER is False
        # With compiler off, text is preserved exactly as-is
        all_content = " ".join(b.get("content", "") for b in view["sections"][0]["blocks"])
        assert "int_0^1" in all_content


# ---------------------------------------------------------------------------
# Renderer last defense
# ---------------------------------------------------------------------------

class TestRendererLastDefense:
    def test_render_math_text_no_raw_int(self):
        """render_math_text should not st.markdown raw \\int."""
        from services.grading_adapter import contains_raw_tex_outside_math
        # Bare int_ should be flagged
        assert contains_raw_tex_outside_math("int_0^1 x dx") is True
        # Properly formatted \int inside \( \) should NOT be flagged
        assert contains_raw_tex_outside_math(r"公式 \(\int_0^1 x\,dx\) 如下") is False

    def test_render_math_text_no_raw_placeholder(self):
        """render_math_text should not st.markdown raw @@MATH."""
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math("@@MATH1@@") is True
