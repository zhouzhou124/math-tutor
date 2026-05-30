"""P41.4: Probability formula fragment repair tests.

Covers:
1. repair_bare_fraction_commands
2. repair_probability_formula_fragments
3. normalize_probability_derivation_block
4. detect_probability_formula_fragment_leak
5. Integration with sanitize pipeline
6. Renderer safety
7. Regression
"""
import pytest


# ═══════════════════════════════════════════════
#  repair_bare_fraction_commands
# ═══════════════════════════════════════════════

class TestRepairBareFraction:

    def test_frac14_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands("frac14")
        assert r'\frac{1}{4}' in result

    def test_frac12_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands("frac12")
        assert r'\frac{1}{2}' in result

    def test_dfrac18_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands("dfrac18")
        assert r'\dfrac{1}{8}' in result

    def test_frac34_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands("frac34")
        assert r'\frac{3}{4}' in result

    def test_bare_frac_with_braces_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands(r"frac{1}{4}")
        assert r'\frac{1}{4}' in result

    def test_dfrac_with_braces_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands(r"dfrac{1}{8}")
        assert r'\dfrac{1}{8}' in result

    def test_stray_d_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands("d frac14")
        assert r'\frac{1}{4}' in result

    def test_backslash_space_frac_fixed(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands(r"\ frac14")
        assert r'\frac{1}{4}' in result

    def test_valid_frac_not_changed(self):
        from latex_utils import repair_bare_fraction_commands
        s = r"\frac{1}{4}"
        result = repair_bare_fraction_commands(s)
        assert result == s

    def test_no_frac_unchanged(self):
        from latex_utils import repair_bare_fraction_commands
        s = "just plain text"
        result = repair_bare_fraction_commands(s)
        assert result == s

    def test_empty_input(self):
        from latex_utils import repair_bare_fraction_commands
        assert repair_bare_fraction_commands("") == ""
        assert repair_bare_fraction_commands(None) is None

    def test_frac_in_expression(self):
        from latex_utils import repair_bare_fraction_commands
        result = repair_bare_fraction_commands(r"frac14 + frac12 = frac34")
        assert r'\frac{1}{4}' in result
        assert r'\frac{1}{2}' in result
        assert r'\frac{3}{4}' in result

    def test_cases_with_bare_frac(self):
        from latex_utils import repair_bare_fraction_commands
        s = (
            r"\begin{cases}" + "\n"
            r"frac12, & x<0 \\" + "\n"
            r"frac14, & x>0" + "\n"
            r"\end{cases}"
        )
        result = repair_bare_fraction_commands(s)
        assert r'\frac{1}{2}' in result
        assert r'\frac{1}{4}' in result


# ═══════════════════════════════════════════════
#  repair_probability_formula_fragments
# ═══════════════════════════════════════════════

class TestRepairProbabilityFragments:

    def test_orphan_bang_removed(self):
        from latex_utils import repair_probability_formula_fragments
        s = "F(y)\n!\n=P(...)"
        result = repair_probability_formula_fragments(s)
        assert '!\n' not in result
        assert 'F(y)' in result

    def test_orphan_star_removed(self):
        from latex_utils import repair_probability_formula_fragments
        s = "expr\n**\nmore"
        result = repair_probability_formula_fragments(s)
        assert '**' not in result

    def test_orphan_dx_merged(self):
        from latex_utils import repair_probability_formula_fragments
        s = r"\int_0^1 \frac12" + "\n" + "dx"
        result = repair_probability_formula_fragments(s)
        assert 'dx' in result
        # dx should be on the same line as the integral
        lines = result.strip().split('\n')
        assert len(lines) == 1

    def test_orphan_dy_merged(self):
        from latex_utils import repair_probability_formula_fragments
        s = r"\frac{d}{dy}F(y)" + "\n" + "dy"
        result = repair_probability_formula_fragments(s)
        lines = result.strip().split('\n')
        assert len(lines) == 1

    def test_bang_before_paren_removed(self):
        from latex_utils import repair_probability_formula_fragments
        s = r"F!(x)"
        result = repair_probability_formula_fragments(s)
        assert '!(' not in result
        assert 'F(x)' in result or r'F\left(' in result

    def test_event_semicolon_replaced(self):
        from latex_utils import repair_probability_formula_fragments
        s = r"\{X\le a; Y\le b\}"
        result = repair_probability_formula_fragments(s)
        assert ';' not in result
        assert ',' in result

    def test_clean_input_unchanged(self):
        from latex_utils import repair_probability_formula_fragments
        s = r"\frac{1}{4} + \frac{1}{2}"
        result = repair_probability_formula_fragments(s)
        assert result == s

    def test_empty_input(self):
        from latex_utils import repair_probability_formula_fragments
        assert repair_probability_formula_fragments("") == ""
        assert repair_probability_formula_fragments(None) is None


# ═══════════════════════════════════════════════
#  Screenshot cases
# ═══════════════════════════════════════════════

class TestScreenshotCases:

    def test_cdf_two_integrals(self):
        """F_Y(y) = integral + integral should become aligned."""
        from latex_utils import normalize_derivation_formula_block
        s = (
            r"F_Y(y)"
            r"=\int_{-\sqrt{y}}^{0}\frac12\,dx"
            r"+\int_0^{\sqrt{y}}\frac14\,dx"
            r"=\frac34\sqrt{y}"
        )
        result = normalize_derivation_formula_block(s)
        assert r'\begin{aligned}' in result
        assert r'\int' in result

    def test_pdf_derivative(self):
        """f_Y(y) = d/dy F_Y(y) should become aligned."""
        from latex_utils import normalize_derivation_formula_block
        s = (
            r"f_Y(y)"
            r"=\frac{d}{dy}\left(\frac34\sqrt{y}\right)"
            r"=\frac{3}{8\sqrt{y}}"
        )
        result = normalize_derivation_formula_block(s)
        assert r'\begin{aligned}' in result

    def test_bare_frac_in_cdf(self):
        """CDF with bare frac14 should be fixed."""
        from latex_utils import repair_bare_fraction_commands
        s = r"F_Y(y)=\int_0^y frac14\,dx"
        result = repair_bare_fraction_commands(s)
        assert r'\frac{1}{4}' in result
        assert 'frac14' not in result

    def test_f_with_orphan_bang(self):
        """F(x) with orphan ! should be fixed."""
        from latex_utils import repair_probability_formula_fragments
        s = r"F" + "\n" + "!" + "\n" + r"\left(\frac12,4\right)"
        result = repair_probability_formula_fragments(s)
        assert '!\n' not in result

    def test_sanitize_pipeline_fixes_bare_frac(self):
        """Integration: sanitize fixes bare frac in latex_display."""
        from services.grading_adapter import sanitize_solution_before_display
        solution = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "latex_display",
                        "content": r"F_Y(y)=\int_0^y frac14\,dx=\frac12",
                    }],
                }],
                "final_answer": {"type": "text", "content": "答案"},
            }
        }
        result = sanitize_solution_before_display(solution)
        blocks = result["_structured"]["steps"][0]["blocks"]
        content = blocks[0]["content"]
        assert 'frac14' not in content
        assert r'\frac{1}{4}' in content


# ═══════════════════════════════════════════════
#  detect_probability_formula_fragment_leak
# ═══════════════════════════════════════════════

class TestDetectProbabilityFragments:

    def test_bare_frac_detected(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        issues = detect_probability_formula_fragment_leak("frac14")
        assert "bare_fraction_command" in issues

    def test_orphan_dx_detected(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        issues = detect_probability_formula_fragment_leak("dx")
        assert "orphan_differential_line" in issues

    def test_orphan_bang_detected(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        issues = detect_probability_formula_fragment_leak("!")
        assert "orphan_marker_bang" in issues

    def test_bang_before_paren_detected(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        issues = detect_probability_formula_fragment_leak(r"F!(x)")
        assert "broken_left_marker" in issues

    def test_clean_input_no_issues(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        issues = detect_probability_formula_fragment_leak(r"\frac{1}{4} + \frac{1}{2}")
        assert len(issues) == 0

    def test_empty_input(self):
        from services.solution_quality import detect_probability_formula_fragment_leak
        assert detect_probability_formula_fragment_leak("") == []
        assert detect_probability_formula_fragment_leak(None) == []


# ═══════════════════════════════════════════════
#  Renderer safety
# ═══════════════════════════════════════════════

class TestRendererSafety:

    def test_validate_repairs_bare_frac(self):
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = r"F_Y(y)=\int_0^y frac14\,dx"
        result = _validate_and_repair_latex_block(content)
        assert result is not None
        assert 'frac14' not in result

    def test_validate_repairs_orphan_bang(self):
        from latex_utils import repair_probability_formula_fragments
        content = "F(y)\n!\n=P(...)"
        repaired = repair_probability_formula_fragments(content)
        # Orphan bang should be removed
        assert '!\n' not in repaired
        assert 'F(y)' in repaired

    def test_clean_latex_passes_through(self):
        from renderers.components.grading_result import _validate_and_repair_latex_block
        content = r"\frac{1}{4} + \frac{1}{2} = \frac{3}{4}"
        result = _validate_and_repair_latex_block(content)
        assert result is not None
        assert result == content


# ═══════════════════════════════════════════════
#  Environment protection: fractions not broken
# ═══════════════════════════════════════════════

class TestFractionProtection:

    def test_valid_frac_not_broken_by_inline_normalize(self):
        from latex_utils import normalize_inline_math_text
        s = r"\frac{1}{4}"
        result = normalize_inline_math_text(s)
        assert r'\frac{1}{4}' in result

    def test_cases_with_valid_frac_not_broken(self):
        from latex_utils import normalize_inline_math_text
        s = (
            r"\begin{cases}" + "\n"
            r"\frac{1}{2}, & x<0 \\" + "\n"
            r"\frac{1}{4}, & x>0" + "\n"
            r"\end{cases}"
        )
        result = normalize_inline_math_text(s)
        assert r'\begin{cases}' in result
        assert r'\frac{1}{2}' in result
        assert r'\frac{1}{4}' in result


# ═══════════════════════════════════════════════
#  Regression: P41.1-P41.3 still work
# ═══════════════════════════════════════════════

class TestRegression:

    def test_derivation_chain_still_works(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"\frac{I(t)}{\pi t^3} = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx = 3\int_{-1}^{1} f(tu)(1-u^2)du"
        result = normalize_derivation_formula_block(text)
        assert r'\begin{aligned}' in result

    def test_substitution_still_works(self):
        from latex_utils import normalize_derivation_formula_block
        text = r"3\int_{-1}^{1} f(tu)(1-u^2)du, (x=tu)"
        result = normalize_derivation_formula_block(text)
        assert r'\quad (x=tu)' in result

    def test_aligned_env_preserved(self):
        from latex_utils import normalize_inline_math_text
        s = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = normalize_inline_math_text(s)
        assert r'\begin{aligned}' in result

    def test_cases_spacing_repaired(self):
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

    def test_chinese_text_not_affected(self):
        from latex_utils import normalize_inline_math_text
        text = "因此本步利用换元法化简积分得到结论。"
        result = normalize_inline_math_text(text)
        assert result == text
