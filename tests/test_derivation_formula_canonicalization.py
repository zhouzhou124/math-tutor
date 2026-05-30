"""P41: Derivation formula canonicalization tests.

Covers:
1. Multi-= derivation chain → aligned
2. Trailing substitution ", (x=tu)" → \quad (x=tu)
3. Detached substitution fragments detection
4. Chinese in latex_display detection
5. Bare lim notation normalization
6. ∫ notation normalization
7. [u-u^3/3] bracket normalization
8. normalize不影响普通中文正文
9. Key derivation case: I(t)/πt^3 chain
10. split_text_and_latex_mixed_block
"""
import pytest


# ═══════════════════════════════════════════════
#  normalize_derivation_formula_block
# ═══════════════════════════════════════════════

class TestNormalizeDerivationFormulaBlock:

    def test_multi_eq_to_aligned(self):
        """Multiple = signs should be converted to aligned environment."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"\frac{I(t)}{\pi t^3} = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx = 3\int_{-1}^{1} f(tu)(1-u^2)du"
        result = normalize_derivation_formula_block(input_text)
        assert r'\begin{aligned}' in result
        assert r'\end{aligned}' in result
        assert '&=' in result

    def test_substitution_to_quad(self):
        """, (x=tu) should become \quad (x=tu)."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"3\int_{-1}^{1} f(tu)(1-u^2)du, (x=tu)"
        result = normalize_derivation_formula_block(input_text)
        assert r'\quad (x=tu)' in result
        assert ', (x=tu)' not in result

    def test_strip_outer_dollars(self):
        """Outer $$ should be stripped."""
        from latex_utils import normalize_derivation_formula_block
        input_text = "$$\\frac{1}{2}$$"
        result = normalize_derivation_formula_block(input_text)
        assert not result.startswith('$$')
        assert r'\frac{1}{2}' in result

    def test_strip_outer_brackets(self):
        """Outer \\[ \\] should be stripped."""
        from latex_utils import normalize_derivation_formula_block
        input_text = "\\[\\frac{1}{2}\\]"
        result = normalize_derivation_formula_block(input_text)
        assert not result.startswith('\\[')
        assert r'\frac{1}{2}' in result

    def test_already_aligned_unchanged(self):
        """Already aligned blocks should not be modified."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        result = normalize_derivation_formula_block(input_text)
        assert r'\begin{aligned}' in result
        assert result == input_text

    def test_single_eq_no_aligned(self):
        """Single = should not trigger aligned conversion."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"x = 1"
        result = normalize_derivation_formula_block(input_text)
        assert r'\begin{aligned}' not in result

    def test_bare_lim_normalized(self):
        """Bare lim notation should be normalized."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"lim t \to 0^+"
        result = normalize_derivation_formula_block(input_text)
        assert r'\lim' in result

    def test_empty_input(self):
        """Empty input should return empty."""
        from latex_utils import normalize_derivation_formula_block
        assert normalize_derivation_formula_block("") == ""
        assert normalize_derivation_formula_block(None) is None

    def test_chain_with_arrow(self):
        """Chain with ⇒ should be converted to aligned."""
        from latex_utils import normalize_derivation_formula_block
        input_text = r"x = 1 \Rightarrow y = 2 \Rightarrow z = 3"
        result = normalize_derivation_formula_block(input_text)
        assert r'\begin{aligned}' in result


# ═══════════════════════════════════════════════
#  I(t)/πt^3 canonical case
# ═══════════════════════════════════════════════

class TestCanonicalCase:

    def test_it_over_pi_t3_chain(self):
        """The specific screenshot case: I(t)/πt^3 derivation chain."""
        from latex_utils import normalize_derivation_formula_block
        input_text = (
            r"\frac{I(t)}{\pi t^3}"
            r" = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx"
            r" = 3\int_{-1}^{1} f(tu)(1-u^2)du"
        )
        result = normalize_derivation_formula_block(input_text)
        assert r'\begin{aligned}' in result
        assert r'\frac{I(t)}{\pi t^3}' in result
        assert '&=' in result

    def test_it_over_pi_t3_with_substitution(self):
        """Chain with trailing substitution annotation."""
        from latex_utils import normalize_derivation_formula_block
        input_text = (
            r"3\int_{-1}^{1} f(tu)(1-u^2)du, (x=tu)"
        )
        result = normalize_derivation_formula_block(input_text)
        assert r'\quad (x=tu)' in result


# ═══════════════════════════════════════════════
#  split_text_and_latex_mixed_block
# ═══════════════════════════════════════════════

class TestSplitTextAndLatexMixedBlock:

    def test_chinese_and_formula_split(self):
        """Chinese prose and formula should be split into separate blocks."""
        from latex_utils import split_text_and_latex_mixed_block
        text = "因此本步得到结论：\n\\frac{I(t)}{\\pi t^3}=3\\int_{-1}^{1} f(tu)(1-u^2)du"
        result = split_text_and_latex_mixed_block(text)
        assert len(result) >= 2
        # First block should be text
        assert result[0]["type"] == "text"
        assert "因此本步得到结论" in result[0]["content"]
        # Last block should be latex_display
        assert result[-1]["type"] == "latex_display"
        assert "frac" in result[-1]["content"] or "int" in result[-1]["content"]

    def test_pure_formula_returns_latex(self):
        """Pure formula should return as latex_display."""
        from latex_utils import split_text_and_latex_mixed_block
        text = "\\frac{I(t)}{\\pi t^3} = 3\\int_{-1}^{1} f(tu)(1-u^2)du"
        result = split_text_and_latex_mixed_block(text)
        assert any(b["type"] == "latex_display" for b in result)

    def test_pure_text_returns_text(self):
        """Pure Chinese text should return as text block."""
        from latex_utils import split_text_and_latex_mixed_block
        text = "因此本步得到结论，利用换元法化简积分。"
        result = split_text_and_latex_mixed_block(text)
        assert len(result) == 1
        assert result[0]["type"] == "text"

    def test_empty_input(self):
        """Empty input should return empty list."""
        from latex_utils import split_text_and_latex_mixed_block
        assert split_text_and_latex_mixed_block("") == []


# ═══════════════════════════════════════════════
#  normalize_inline_math_text enhancements
# ═══════════════════════════════════════════════

class TestNormalizeInlineMathEnhancements:

    def test_bare_lim_t_to_0_plus(self):
        """lim t → 0+ should become \\lim_{t\\to0^+}."""
        from latex_utils import normalize_inline_math_text
        result = normalize_inline_math_text("lim t → 0+")
        assert r'\lim' in result
        assert r'\to0^+' in result

    def test_bare_lim_arrow_notation(self):
        """lim t->0+ should become \\lim_{t\\to0^+}."""
        from latex_utils import normalize_inline_math_text
        result = normalize_inline_math_text("lim t->0+")
        assert r'\lim' in result

    def test_bare_lim_n_to_infty(self):
        """lim n → ∞ should become \\lim_{n\\to\\infty}."""
        from latex_utils import normalize_inline_math_text
        result = normalize_inline_math_text("lim n → ∞")
        assert r'\lim' in result
        assert r'\infty' in result

    def test_integral_notation(self):
        """∫_{-1}^1 should be normalized."""
        from latex_utils import normalize_inline_math_text
        result = normalize_inline_math_text("∫_{-1}^1")
        assert r'\int' in result

    def test_bracket_eval(self):
        """[u-u^3/3]_{-1}^{1} should be normalized."""
        from latex_utils import normalize_inline_math_text
        result = normalize_inline_math_text("[u-u^3/3]_{-1}^{1}")
        assert r'\left[' in result or r'\left\[' in result

    def test_chinese_text_not_affected(self):
        """Normal Chinese text should not be modified."""
        from latex_utils import normalize_inline_math_text
        text = "因此本步利用换元法化简积分得到结论。"
        result = normalize_inline_math_text(text)
        assert result == text

    def test_existing_math_not_double_wrapped(self):
        """Existing $...$ should not be double-wrapped."""
        from latex_utils import normalize_inline_math_text
        text = "$x^2 + y^2$"
        result = normalize_inline_math_text(text)
        assert result.count('$') <= 2  # at most one pair


# ═══════════════════════════════════════════════
#  detect_broken_derivation_formula_block
# ═══════════════════════════════════════════════

class TestDetectBrokenDerivation:

    def test_detached_substitution_detected(self):
        """Detached "(x" fragment should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        issues = detect_broken_derivation_formula_block("(x")
        assert "detached_substitution_annotation" in issues

    def test_detached_closing_paren_detected(self):
        """Detached "=tu)" fragment should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        issues = detect_broken_derivation_formula_block("=tu)")
        assert "detached_substitution_annotation" in issues

    def test_chinese_in_latex_display_detected(self):
        """Chinese sentences in display math should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        text = "$$\\frac{1}{2} = 因此我们得到结论是正确的$$"
        issues = detect_broken_derivation_formula_block(text)
        assert "text_inside_latex_display" in issues

    def test_bare_lim_detected(self):
        """Bare 'lim t → 0+' should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        issues = detect_broken_derivation_formula_block("lim t → 0+")
        assert "raw_limit_notation" in issues

    def test_multi_eq_no_aligned_detected(self):
        """Multiple = without aligned should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        text = r"\frac{a}{b} = c = d = e"
        issues = detect_broken_derivation_formula_block(text)
        assert "unaligned_derivation_chain" in issues

    def test_comma_substitution_detected(self):
        """, (x=tu) should be detected."""
        from services.solution_quality import detect_broken_derivation_formula_block
        text = r"\int f(x) dx, (x=tu)"
        issues = detect_broken_derivation_formula_block(text)
        assert "comma_annotation_in_formula" in issues

    def test_clean_formula_no_issues(self):
        """Clean formula should have no issues."""
        from services.solution_quality import detect_broken_derivation_formula_block
        text = r"\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}"
        issues = detect_broken_derivation_formula_block(text)
        assert len(issues) == 0

    def test_empty_input(self):
        """Empty input should return no issues."""
        from services.solution_quality import detect_broken_derivation_formula_block
        assert detect_broken_derivation_formula_block("") == []
        assert detect_broken_derivation_formula_block(None) == []


# ═══════════════════════════════════════════════
#  sanitize pipeline integration
# ═══════════════════════════════════════════════

class TestSanitizePipelineIntegration:

    def test_latex_display_block_gets_normalized(self):
        """latex_display blocks should get derivation normalization."""
        from services.grading_adapter import sanitize_solution_before_display
        solution = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "latex_display",
                        "content": r"\frac{I(t)}{\pi t^3} = \frac{3}{t^3}\int_{-t}^{t} f(x)(t^2-x^2)dx = 3\int_{-1}^{1} f(tu)(1-u^2)du",
                    }],
                }],
                "final_answer": {"type": "text", "content": "答案"},
            }
        }
        result = sanitize_solution_before_display(solution)
        blocks = result["_structured"]["steps"][0]["blocks"]
        # Should have aligned environment after normalization
        content = blocks[0]["content"]
        assert r'\begin{aligned}' in content or '&=' in content

    def test_text_block_gets_inline_normalization(self):
        """text blocks should get inline math normalization."""
        from services.grading_adapter import sanitize_solution_before_display
        solution = {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "text",
                        "content": "当 lim t → 0+ 时，得到结果。",
                    }],
                }],
                "final_answer": {"type": "text", "content": "答案"},
            }
        }
        result = sanitize_solution_before_display(solution)
        blocks = result["_structured"]["steps"][0]["blocks"]
        content = blocks[0]["content"]
        assert r'\lim' in content
