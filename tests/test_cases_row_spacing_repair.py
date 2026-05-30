"""P41.3: Cases row spacing marker repair tests.

Covers:
1. repair_latex_row_spacing_markers
2. repair_cases_environment
3. detect_broken_cases_environment
4. Integration with sanitize pipeline
5. Renderer safety
6. Regression: display math delimiters not affected
"""
import pytest


# ═══════════════════════════════════════════════
#  repair_latex_row_spacing_markers
# ═══════════════════════════════════════════════

class TestRepairRowSpacingMarkers:

    def test_broken_6pt_fixed(self):
        import re
        from latex_utils import repair_latex_row_spacing_markers
        s = r"z<0 \[6pt]"
        result = repair_latex_row_spacing_markers(s)
        # Should have \\[6pt] (double backslash), not single-backslash \[6pt]
        assert r'\\[6pt]' in result
        # The broken pattern (single \ before [) should not exist standalone
        assert not re.search(r'(?<!\\)\\\[\d+pt\]', result)

    def test_broken_4pt_fixed(self):
        import re
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \[4pt]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[4pt]' in result
        assert not re.search(r'(?<!\\)\\\[\d+pt\]', result)

    def test_broken_em_fixed(self):
        import re
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \[.5em]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[.5em]' in result
        assert not re.search(r'(?<!\\)\\\[[\d.]+em\]', result)

    def test_broken_ex_fixed(self):
        import re
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \[1ex]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[1ex]' in result
        assert not re.search(r'(?<!\\)\\\[\d+ex\]', result)

    def test_valid_spacing_preserved(self):
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \\[6pt]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[6pt]' in result

    def test_display_delimiter_not_touched(self):
        """\\[...\\] with non-dimension content should not be modified."""
        from latex_utils import repair_latex_row_spacing_markers
        s = r"\[x^2 + y^2 = z^2\]"
        result = repair_latex_row_spacing_markers(s)
        assert result == s

    def test_empty_input(self):
        from latex_utils import repair_latex_row_spacing_markers
        assert repair_latex_row_spacing_markers("") == ""
        assert repair_latex_row_spacing_markers(None) is None

    def test_mm_spacing(self):
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \[2mm]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[2mm]' in result

    def test_cm_spacing(self):
        from latex_utils import repair_latex_row_spacing_markers
        s = r"expr \[1cm]"
        result = repair_latex_row_spacing_markers(s)
        assert r'\\[1cm]' in result


# ═══════════════════════════════════════════════
#  repair_cases_environment
# ═══════════════════════════════════════════════

class TestRepairCasesEnvironment:

    def test_spacing_normalized_to_double_backslash(self):
        from latex_utils import repair_cases_environment
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \[6pt]" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = repair_cases_environment(s)
        assert r'\begin{cases}' in result
        assert r'\end{cases}' in result

    def test_valid_spacing_also_normalized(self):
        from latex_utils import repair_cases_environment
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \\[6pt]" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = repair_cases_environment(s)
        # In cases, \\[6pt] should become just \\
        assert r'\\[6pt]' not in result

    def test_missing_ampersand_added(self):
        from latex_utils import repair_cases_environment
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, z<0 \\" + "\n"
            r"\frac{1}{3}, z>0" + "\n"
            r"\end{cases}"
        )
        result = repair_cases_environment(s)
        assert '&' in result

    def test_clean_cases_unchanged(self):
        from latex_utils import repair_cases_environment
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \\" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = repair_cases_environment(s)
        assert result == s

    def test_no_cases_unchanged(self):
        from latex_utils import repair_cases_environment
        s = r"\begin{aligned} x &= 1 \end{aligned}"
        result = repair_cases_environment(s)
        assert result == s

    def test_empty_input(self):
        from latex_utils import repair_cases_environment
        assert repair_cases_environment("") == ""
        assert repair_cases_environment(None) is None


# ═══════════════════════════════════════════════
#  Screenshot case: density function with \[6pt]
# ═══════════════════════════════════════════════

class TestScreenshotCase:

    def test_density_function_cases(self):
        """The canonical screenshot case: piecewise density with \\[6pt]."""
        import re
        from latex_utils import repair_cases_environment, repair_latex_row_spacing_markers
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{\sqrt{2\pi}}e^{-z^2/2}, & z<0 \[6pt]" + "\n"
            r"\frac{1}{2\sqrt z}e^{-2\sqrt z}, & 0\le z<1 \[6pt]" + "\n"
            r"e^{-2z}, & z>1" + "\n"
            r"\end{cases}"
        )
        repaired = repair_latex_row_spacing_markers(s)
        repaired = repair_cases_environment(repaired)
        # No broken \[6pt] pattern (single backslash before dimension)
        assert not re.search(r'(?<!\\)\\\[\d+pt\]', repaired)
        # Should still be valid cases
        assert r'\begin{cases}' in repaired
        assert r'\end{cases}' in repaired

    def test_sanitize_pipeline_fixes_cases(self):
        """Integration: sanitize_solution_before_display fixes \\[6pt] in cases."""
        import re
        from services.grading_adapter import sanitize_solution_before_display
        solution = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "latex_display",
                        "content": (
                            r"\begin{cases}" + "\n"
                            r"\frac{1}{2}, & z<0 \[6pt]" + "\n"
                            r"\frac{1}{3}, & z>0" + "\n"
                            r"\end{cases}"
                        ),
                    }],
                }],
                "final_answer": {"type": "text", "content": "答案"},
            }
        }
        result = sanitize_solution_before_display(solution)
        blocks = result["_structured"]["steps"][0]["blocks"]
        content = blocks[0]["content"]
        # No broken \[6pt] pattern should remain
        assert not re.search(r'(?<!\\)\\\[\d+pt\]', content)


# ═══════════════════════════════════════════════
#  detect_broken_cases_environment
# ═══════════════════════════════════════════════

class TestDetectBrokenCases:

    def test_broken_spacing_detected(self):
        from services.solution_quality import detect_broken_cases_environment
        issues = detect_broken_cases_environment(r"z<0 \[6pt]")
        assert "broken_row_spacing_marker" in issues

    def test_valid_spacing_not_detected_as_broken(self):
        from services.solution_quality import detect_broken_cases_environment
        # \\[6pt] is valid spacing, should not be detected as broken
        issues = detect_broken_cases_environment(r"z<0 \\[6pt]")
        assert "broken_row_spacing_marker" not in issues

    def test_clean_cases_no_issues(self):
        from services.solution_quality import detect_broken_cases_environment
        s = (
            r"\begin{cases}"
            r"\frac{1}{2}, & z<0 \\"
            r"\frac{1}{3}, & z>0"
            r"\end{cases}"
        )
        issues = detect_broken_cases_environment(s)
        assert len(issues) == 0

    def test_empty_input(self):
        from services.solution_quality import detect_broken_cases_environment
        assert detect_broken_cases_environment("") == []
        assert detect_broken_cases_environment(None) == []


# ═══════════════════════════════════════════════
#  Environment protection: cases not broken by normalizers
# ═══════════════════════════════════════════════

class TestCasesProtection:

    def test_cases_not_broken_by_normalize_inline(self):
        from latex_utils import normalize_inline_math_text
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \\" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = normalize_inline_math_text(s)
        assert r'\begin{cases}' in result
        assert r'\end{cases}' in result

    def test_cases_not_broken_by_equation_formatter(self):
        from latex_utils import format_independent_equation_list
        s = (
            r"\begin{cases}" + "\n"
            r"a, b" + "\n"
            r"\end{cases}"
        )
        result = format_independent_equation_list(s)
        assert result == s

    def test_cases_preserved_by_splitter(self):
        from latex_utils import split_text_and_latex_mixed_block
        text = (
            "分段函数为：\n"
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \\" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}" + "\n"
            "所以结果成立。"
        )
        result = split_text_and_latex_mixed_block(text)
        latex_blocks = [b for b in result if b["type"] == "latex_display"]
        assert len(latex_blocks) >= 1
        assert r'\begin{cases}' in latex_blocks[0]["content"]
        assert r'\end{cases}' in latex_blocks[0]["content"]


# ═══════════════════════════════════════════════
#  Renderer safety
# ═══════════════════════════════════════════════

class TestRendererSafety:

    def test_validate_repair_fixes_spacing(self):
        import re
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \[6pt]" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = _validate_and_repair_latex_block(content)
        assert result is not None
        # No broken \[6pt] pattern should remain
        assert not re.search(r'(?<!\\)\\\[\d+pt\]', result)

    def test_clean_cases_passes_through(self):
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & z<0 \\" + "\n"
            r"\frac{1}{3}, & z>0" + "\n"
            r"\end{cases}"
        )
        result = _validate_and_repair_latex_block(content)
        assert result is not None


# ═══════════════════════════════════════════════
#  Regression: display math delimiters not affected
# ═══════════════════════════════════════════════

class TestRegressionDisplayDelimiter:

    def test_display_math_not_affected(self):
        """\\[...\\] with math content should not be treated as spacing."""
        from latex_utils import repair_latex_row_spacing_markers
        s = r"\[x^2 + y^2 = 1\]"
        result = repair_latex_row_spacing_markers(s)
        assert result == s

    def test_display_math_with_text_not_affected(self):
        from latex_utils import repair_latex_row_spacing_markers
        s = r"\[\frac{1}{2}\]"
        result = repair_latex_row_spacing_markers(s)
        assert result == s

    def test_aligned_env_not_affected(self):
        from latex_utils import repair_latex_row_spacing_markers
        s = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = repair_latex_row_spacing_markers(s)
        assert result == s

    def test_p41_derivation_chain_still_works(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"\frac{I(t)}{\pi t^3} = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx = 3\int_{-1}^{1} f(tu)(1-u^2)du"
        result = normalize_derivation_formula_block(text)
        assert r'\begin{aligned}' in result

    def test_p41_substitution_still_works(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"3\int_{-1}^{1} f(tu)(1-u^2)du, (x=tu)"
        result = normalize_derivation_formula_block(text)
        assert r'\quad (x=tu)' in result
