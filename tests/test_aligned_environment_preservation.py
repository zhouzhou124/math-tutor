"""P41.2: Aligned environment preservation tests.

Covers:
1. protect/restore helpers
2. repair_aligned_environment rules
3. Environment-aware split_text_and_latex_mixed_block
4. normalize_inline_math_text does not break aligned
5. format_independent_equation_list does not break aligned
6. detect_broken_latex_environment
7. Renderer safety (no raw aligned leakage)
8. Integration with sanitize pipeline
"""
import pytest


# ═══════════════════════════════════════════════
#  protect / restore helpers
# ═══════════════════════════════════════════════

class TestProtectRestoreLatexEnvironments:

    def test_protect_aligned(self):
        from latex_utils import protect_latex_environments, restore_latex_environments
        text = r"text \begin{aligned} x &= 1 \end{aligned} more"
        s, env_map = protect_latex_environments(text)
        assert r'\begin{aligned}' not in s
        assert r'\end{aligned}' not in s
        assert len(env_map) == 1
        restored = restore_latex_environments(s, env_map)
        assert restored == text

    def test_protect_cases(self):
        from latex_utils import protect_latex_environments, restore_latex_environments
        text = r"\begin{cases} x > 0 \\ x < 1 \end{cases}"
        s, env_map = protect_latex_environments(text)
        assert len(env_map) == 1
        restored = restore_latex_environments(s, env_map)
        assert restored == text

    def test_protect_multiple_envs(self):
        from latex_utils import protect_latex_environments, restore_latex_environments
        text = (
            r"\begin{aligned} x &= 1 \end{aligned}"
            r" and "
            r"\begin{cases} a \\ b \end{cases}"
        )
        s, env_map = protect_latex_environments(text)
        assert len(env_map) == 2
        restored = restore_latex_environments(s, env_map)
        assert restored == text

    def test_protect_empty(self):
        from latex_utils import protect_latex_environments
        s, env_map = protect_latex_environments("")
        assert s == ""
        assert env_map == {}

    def test_protect_none(self):
        from latex_utils import protect_latex_environments
        s, env_map = protect_latex_environments(None)
        assert s is None
        assert env_map == {}

    def test_protect_no_env(self):
        from latex_utils import protect_latex_environments
        text = "just plain text with \\frac{1}{2}"
        s, env_map = protect_latex_environments(text)
        assert s == text
        assert env_map == {}

    def test_protect_matrix(self):
        from latex_utils import protect_latex_environments, restore_latex_environments
        text = r"\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}"
        s, env_map = protect_latex_environments(text)
        assert len(env_map) == 1
        restored = restore_latex_environments(s, env_map)
        assert restored == text


# ═══════════════════════════════════════════════
#  repair_aligned_environment
# ═══════════════════════════════════════════════

class TestRepairAlignedEnvironment:

    def test_escaped_ampersand_fixed(self):
        from latex_utils import repair_aligned_environment
        s = r"\begin{aligned} \&= a^3+b^3 \end{aligned}"
        result = repair_aligned_environment(s)
        assert r'\&=' not in result
        assert '&=' in result

    def test_missing_end_appended(self):
        from latex_utils import repair_aligned_environment
        s = r"\begin{aligned} x &= 1 \\ y &= 2"
        result = repair_aligned_environment(s)
        assert r'\end{aligned}' in result

    def test_orphan_end_removed(self):
        from latex_utils import repair_aligned_environment
        s = r"x &= 1 \end{aligned}"
        result = repair_aligned_environment(s)
        assert r'\end{aligned}' not in result

    def test_first_line_no_alignment(self):
        """First line without &= but subsequent lines have &=."""
        from latex_utils import repair_aligned_environment
        s = (
            r"\begin{aligned}f(a,b) \\"
            r"\n&= 6\iint_D |x-y|\,d\sigma-(a^3+b^3)"
            r"\n\end{aligned}"
        )
        result = repair_aligned_environment(s)
        assert r'\begin{aligned}' in result
        assert r'\end{aligned}' in result
        # First line should be preserved, subsequent lines should have &=
        assert 'f(a,b)' in result

    def test_clean_aligned_unchanged(self):
        from latex_utils import repair_aligned_environment
        s = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = repair_aligned_environment(s)
        assert result == s

    def test_empty_input(self):
        from latex_utils import repair_aligned_environment
        assert repair_aligned_environment("") == ""
        assert repair_aligned_environment(None) is None


# ═══════════════════════════════════════════════
#  Environment-aware mixed block splitter
# ═══════════════════════════════════════════════

class TestSplitMixedBlockWithEnvironments:

    def test_aligned_not_split_across_lines(self):
        """Complete aligned environment should stay as one latex_display block."""
        from latex_utils import split_text_and_latex_mixed_block
        text = (
            r"关键变形为："
            r"\begin{aligned}f(a,b) &= a^3+b^3 \\ D &= \{(x,y)\mid 0\le x\le a\}\end{aligned}"
            r"因此得到结论。"
        )
        result = split_text_and_latex_mixed_block(text)
        # Should have: text, latex_display, text
        assert len(result) >= 2
        latex_blocks = [b for b in result if b["type"] == "latex_display"]
        assert len(latex_blocks) >= 1
        assert r'\begin{aligned}' in latex_blocks[0]["content"]
        assert r'\end{aligned}' in latex_blocks[0]["content"]

    def test_cases_not_split(self):
        from latex_utils import split_text_and_latex_mixed_block
        text = r"当 x>0 时：\begin{cases} x^2 \\ x^3 \end{cases} 所以成立。"
        result = split_text_and_latex_mixed_block(text)
        latex_blocks = [b for b in result if b["type"] == "latex_display"]
        assert len(latex_blocks) >= 1
        assert r'\begin{cases}' in latex_blocks[0]["content"]
        assert r'\end{cases}' in latex_blocks[0]["content"]

    def test_pure_text_no_env(self):
        from latex_utils import split_text_and_latex_mixed_block
        text = "因此本步利用换元法化简积分得到结论。"
        result = split_text_and_latex_mixed_block(text)
        assert len(result) == 1
        assert result[0]["type"] == "text"

    def test_empty_input(self):
        from latex_utils import split_text_and_latex_mixed_block
        assert split_text_and_latex_mixed_block("") == []

    def test_env_between_text_blocks(self):
        """Environment surrounded by Chinese text should produce 3 blocks."""
        from latex_utils import split_text_and_latex_mixed_block
        text = (
            "计算得：\n"
            r"\begin{aligned}" + "\n"
            r"x &= 1 \\" + "\n"
            r"y &= 2" + "\n"
            r"\end{aligned}" + "\n"
            "代入验证。"
        )
        result = split_text_and_latex_mixed_block(text)
        types = [b["type"] for b in result]
        assert "text" in types
        assert "latex_display" in types
        # The aligned block should be intact
        for b in result:
            if b["type"] == "latex_display":
                assert r'\begin{aligned}' in b["content"]
                assert r'\end{aligned}' in b["content"]


# ═══════════════════════════════════════════════
#  normalize_inline_math_text does not break aligned
# ═══════════════════════════════════════════════

class TestNormalizeInlineMathPreservesAligned:

    def test_aligned_not_broken(self):
        from latex_utils import normalize_inline_math_text
        text = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = normalize_inline_math_text(text)
        assert r'\begin{aligned}' in result
        assert r'\end{aligned}' in result
        assert '&=' in result

    def test_cases_not_broken(self):
        from latex_utils import normalize_inline_math_text
        text = r"\begin{cases} x > 0 \\ x < 1 \end{cases}"
        result = normalize_inline_math_text(text)
        assert r'\begin{cases}' in result
        assert r'\end{cases}' in result

    def test_text_around_env_preserved(self):
        from latex_utils import normalize_inline_math_text
        text = r"因此 \begin{aligned} x &= 1 \end{aligned} 得证。"
        result = normalize_inline_math_text(text)
        assert r'\begin{aligned}' in result
        assert r'\end{aligned}' in result
        assert "因此" in result
        assert "得证" in result

    def test_matrix_not_broken(self):
        from latex_utils import normalize_inline_math_text
        text = r"\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}"
        result = normalize_inline_math_text(text)
        assert r'\begin{pmatrix}' in result
        assert r'\end{pmatrix}' in result


# ═══════════════════════════════════════════════
#  format_independent_equation_list preserves aligned
# ═══════════════════════════════════════════════

class TestFormatEquationListPreservesAligned:

    def test_existing_aligned_not_reformatted(self):
        from latex_utils import format_independent_equation_list
        text = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = format_independent_equation_list(text)
        assert result == text

    def test_cases_not_reformatted(self):
        from latex_utils import format_independent_equation_list
        text = r"\begin{cases} a, b \end{cases}"
        result = format_independent_equation_list(text)
        assert result == text


# ═══════════════════════════════════════════════
#  normalize_derivation_formula_block preserves aligned
# ═══════════════════════════════════════════════

class TestNormalizeDerivationPreservesAligned:

    def test_existing_aligned_repaired_not_replaced(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = normalize_derivation_formula_block(text)
        assert r'\begin{aligned}' in result
        assert r'\end{aligned}' in result

    def test_broken_aligned_gets_repaired(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"\begin{aligned} \&= a^3+b^3 \end{aligned}"
        result = normalize_derivation_formula_block(text)
        assert r'\&=' not in result
        assert '&=' in result

    def test_no_env_chain_gets_converted(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"x = 1 = 2 = 3"
        result = normalize_derivation_formula_block(text)
        assert r'\begin{aligned}' in result


# ═══════════════════════════════════════════════
#  detect_broken_latex_environment
# ═══════════════════════════════════════════════

class TestDetectBrokenLatexEnvironment:

    def test_orphan_begin_detected(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment(r"\begin{aligned} x &= 1")
        assert "orphan_aligned_begin" in issues

    def test_orphan_end_detected(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment(r"x &= 1 \end{aligned}")
        assert "orphan_aligned_end" in issues

    def test_escaped_amp_detected(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment(r"\begin{aligned} \&= x \end{aligned}")
        assert "escaped_alignment_marker" in issues

    def test_orphan_amp_detected(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment("x &= 1")
        assert "orphan_alignment_marker" in issues

    def test_clean_aligned_no_issues(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment(r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}")
        assert len(issues) == 0

    def test_empty_input(self):
        from services.solution_quality import detect_broken_latex_environment
        assert detect_broken_latex_environment("") == []
        assert detect_broken_latex_environment(None) == []

    def test_clean_cases_no_issues(self):
        from services.solution_quality import detect_broken_latex_environment
        issues = detect_broken_latex_environment(r"\begin{cases} x > 0 \end{cases}")
        assert len(issues) == 0


# ═══════════════════════════════════════════════
#  Screenshot case: the canonical broken aligned
# ═══════════════════════════════════════════════

class TestScreenshotCase:

    def test_broken_aligned_from_screenshot(self):
        """The case that caused raw \\begin{aligned} to leak to student view."""
        from latex_utils import split_text_and_latex_mixed_block
        text = (
            "关键变形为：\n"
            r"\begin{aligned}f(a,b) \\" + "\n"
            r"&= 6\iint_D |x-y|\,d\sigma-(a^3+b^3),\\" + "\n"
            r"D &= \{(x,y)\mid 0\le x\le a,\ 0\le y\le b\}" + "\n"
            r"\end{aligned}" + "\n"
            "因此得到结论。"
        )
        result = split_text_and_latex_mixed_block(text)
        # Must not have raw \begin{aligned} in any text block
        for b in result:
            if b["type"] == "text":
                assert r'\begin{aligned}' not in b["content"]
                assert r'\end{aligned}' not in b["content"]
        # Must have at least one latex_display with aligned
        latex_blocks = [b for b in result if b["type"] == "latex_display"]
        assert len(latex_blocks) >= 1
        assert r'\begin{aligned}' in latex_blocks[0]["content"]
        assert r'\end{aligned}' in latex_blocks[0]["content"]

    def test_sanitize_pipeline_repairs_aligned(self):
        """Integration: sanitize_solution_before_display repairs broken aligned."""
        from services.grading_adapter import sanitize_solution_before_display
        solution = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "latex_display",
                        "content": r"\begin{aligned} \&= a^3+b^3 \end{aligned}",
                    }],
                }],
                "final_answer": {"type": "text", "content": "答案"},
            }
        }
        result = sanitize_solution_before_display(solution)
        blocks = result["_structured"]["steps"][0]["blocks"]
        content = blocks[0]["content"]
        # Escaped & should be fixed
        assert r'\&=' not in content
        assert '&=' in content


# ═══════════════════════════════════════════════
#  Renderer safety
# ═══════════════════════════════════════════════

class TestRendererSafety:

    def test_validate_repair_handles_escaped_amp(self):
        """_validate_and_repair_latex_block should fix \\&=."""
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = r"\begin{aligned} \&= a^3+b^3 \end{aligned}"
        result = _validate_and_repair_latex_block(content)
        assert result is not None
        assert r'\&=' not in result

    def test_validate_repair_handles_orphan_begin(self):
        """_validate_and_repair_latex_block should fix missing end."""
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = r"\begin{aligned} x &= 1"
        result = _validate_and_repair_latex_block(content)
        # Should either be repaired (has end) or None (unrepairable)
        if result is not None:
            assert r'\end{aligned}' in result

    def test_clean_aligned_passes_through(self):
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = _validate_and_repair_latex_block(content)
        assert result is not None
        assert r'\begin{aligned}' in result


# ═══════════════════════════════════════════════
#  Regression: P41.1 tests still pass
# ═══════════════════════════════════════════════

class TestP41Regression:

    def test_derivation_chain_still_converts(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"\frac{I(t)}{\pi t^3} = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx = 3\int_{-1}^{1} f(tu)(1-u^2)du"
        result = normalize_derivation_formula_block(text)
        assert r'\begin{aligned}' in result

    def test_substitution_still_converts(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"3\int_{-1}^{1} f(tu)(1-u^2)du, (x=tu)"
        result = normalize_derivation_formula_block(text)
        assert r'\quad (x=tu)' in result

    def test_chinese_text_not_affected(self):
        from latex_utils import normalize_inline_math_text
        text = "因此本步利用换元法化简积分得到结论。"
        result = normalize_inline_math_text(text)
        assert result == text
