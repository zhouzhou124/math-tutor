"""Gold-standard LaTeX pipeline tests — lock critical rendering behaviors."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════
# Group 1: Mixed existing math + bare LaTeX
# ═══════════════════════════════════════════════

def test_mixed_existing_math_and_bare_latex():
    r"""已知 $x=1$，求 \frac{a}{b} — existing math must be preserved as math segment."""
    from latex_utils import split_latex_text
    text = r"已知 $x=1$，求 \frac{a}{b}"
    segments = split_latex_text(text)
    # The $x=1$ should be an inline_math segment (content without $ delimiters)
    math_segments = [
        s for s in segments
        if isinstance(s, dict) and s.get("type") in ("inline_math", "display_math")
    ]
    assert len(math_segments) >= 1, (
        f"Must have at least one math segment: {segments}"
    )
    # Verify x=1 is in a math segment
    has_x1 = any("x=1" in s.get("content", "") for s in math_segments)
    assert has_x1, f"x=1 must be in a math segment: {math_segments}"


def test_bare_frac_gets_wrapped_when_mixed():
    r"""\frac{a}{b} after $x=1$ must end up inside math delimiters."""
    from latex_utils import _pre_wrap_bare_latex
    text = r"已知 $x=1$，求 \frac{a}{b}"
    result = _pre_wrap_bare_latex(text)
    # After wrapping, \frac should be inside $...$ or $$
    import re
    math_regions = re.findall(r'\$[^$]+\$|\$\$[^$]+\$\$', result)
    # At minimum, \frac should appear within a math region
    found = any(r'\frac' in m for m in math_regions)
    assert found, f"After wrapping, \\frac must be inside math delimiters: {result[:200]}"


# ═══════════════════════════════════════════════
# Group 2: Chinese text must not be wrapped as math
# ═══════════════════════════════════════════════

def test_do_not_wrap_chinese_sentence_as_math():
    r"""因此函数在 $x=0$ 处取得极值。— Chinese text stays outside $."""
    from latex_utils import split_latex_text
    text = r"因此函数在 $x=0$ 处取得极值。"
    segments = split_latex_text(text)
    text_segments = [
        s for s in segments
        if isinstance(s, dict) and s.get("type") == "text"
    ]
    assert any("因此函数" in s.get("content", "") for s in text_segments), (
        f"Chinese text must stay in text segments: {segments}"
    )


def test_chinese_only_text_not_wrapped():
    """纯中文不包裹为数学"""
    from views.grading_page import _wrap_ascii_math
    text = "这是纯中文文本没有任何公式"
    result = _wrap_ascii_math(text)
    assert result == text, f"Pure Chinese must not be wrapped: {result}"


# ═══════════════════════════════════════════════
# Group 3: No double-escape LaTeX commands
# ═══════════════════════════════════════════════

def test_no_double_escape_latex_command():
    r"""$\frac{1}{2}$ must not become $\frac{1}{2}$ with \\frac."""
    from latex_normalizer import normalize_latex_style
    text = r"$\frac{1}{2}$"
    result = normalize_latex_style(text)
    # After normalization, should NOT have double backslash before frac
    assert r"\\frac" not in result, (
        f"Normalized text must not have double-escaped commands: {result}"
    )


def test_no_double_escape_inline_math():
    r"""$x^2 + y^2$ stays as single-escaped, not $x^2 + y^2$ with \\."""
    from latex_normalizer import normalize_latex_style
    text = r"$x^2 + y^2$"
    result = normalize_latex_style(text)
    assert r"\\" not in result, (
        f"Normalized math must not have stray backslashes: {repr(result)}"
    )


# ═══════════════════════════════════════════════
# Group 4: Text block with formula is split correctly
# ═══════════════════════════════════════════════

def test_text_block_with_formula_is_split_not_raw_markdown():
    r"""由 \lim_{x\to0}\frac{\sin x}{x}=1 可知 — must produce math segment."""
    from latex_utils import split_latex_text
    text = r"由 \lim_{x\to0}\frac{\sin x}{x}=1 可知"
    segments = split_latex_text(text)
    math_segments = [
        s for s in segments
        if isinstance(s, dict) and s.get("type") in ("inline_math", "display_math")
    ]
    assert len(math_segments) > 0, (
        f"Must have at least one math segment: {segments}"
    )


# ═══════════════════════════════════════════════
# Group 5: Expression integrity — no fragmentation
# ═══════════════════════════════════════════════

def test_expression_not_fragmented_by_subscript_wrapping():
    r"""f'_x(x_0,y_0) must stay as one $ block, not split into pieces."""
    from views.grading_page import _wrap_ascii_math, _wrap_unicode_math
    from latex_normalizer import normalize_latex_style

    text = r"f'_x(x_0,y_0) = 0"
    result = normalize_latex_style(text)
    result = _wrap_unicode_math(result)
    result = _wrap_ascii_math(result)

    import re
    blocks = re.findall(r'\$[^$]+\$', result)
    # Should be one block: $f'_x(x_0,y_0) = 0$, not three: $f'_x($, $x_0$, etc.
    has_full = any("f'_x(x_0,y_0)" in b for b in blocks)
    assert has_full, (
        f"Expression must be one $ block, not fragmented: {blocks}"
    )


def test_frac_not_split_across_math_blocks():
    r"""\frac{1}{2} must stay as one math block."""
    from views.grading_page import _wrap_ascii_math
    import re

    text = r"\frac{1}{2} is a fraction"
    result = _wrap_ascii_math(text)
    blocks = re.findall(r'\$[^$]+\$', result)
    has_frac = any(r'\frac{1}{2}' in b for b in blocks)
    assert has_frac, f"\\frac{{1}}{{2}} must be in one block: {blocks}"


# ═══════════════════════════════════════════════
# Group 6: _pre_wrap_bare_latex early-return fix
# ═══════════════════════════════════════════════

def test_pre_wrap_does_not_return_early_on_existing_math():
    r"""Even if $x=1$ exists, bare \frac{a}{b} later must still be wrapped."""
    from latex_utils import _pre_wrap_bare_latex
    text = r"已知 $x=1$，求 \frac{a}{b}"
    result = _pre_wrap_bare_latex(text)
    # Before fix: returned text unchanged because $...$ exists
    # After fix: wraps \frac{a}{b} in $...$ even though $x=1$ is present
    import re
    math_regions = re.findall(r'\$[^$]+\$|\$\$[^$]+\$\$', result)
    found = any(r'\frac' in m for m in math_regions)
    assert found, (
        f"Bare \\frac must be wrapped even with existing $...$: {result[:200]}"
    )


# ═══════════════════════════════════════════════
# Group 7: Anti-regression — don't over-wrap
# ═══════════════════════════════════════════════

def test_plain_chinese_with_parentheses_not_math():
    """由题意可知（不是选项）函数连续。— parentheses in Chinese not math."""
    from latex_utils import split_latex_text
    text = "由题意可知（不是选项）函数连续。"
    segments = split_latex_text(text)
    for s in segments:
        if isinstance(s, dict) and "不是选项" in s.get("content", ""):
            assert s["type"] == "text", (
                f"Chinese parenthetical must be text, got {s['type']}: {s}"
            )


def test_existing_display_math_not_rewrapped():
    r"""因此 $$\frac{1}{2}$$ 成立 — no triple $$$ from double-wrapping."""
    from latex_utils import split_latex_text
    text = r"因此 $$\frac{1}{2}$$ 成立"
    segments = split_latex_text(text)
    rendered = " ".join(
        s.get("content", s) if isinstance(s, dict) else str(s)
        for s in segments
    )
    assert "$$$" not in rendered, (
        f"Display math must not become triple $$$: {rendered}"
    )


def test_subquestion_number_before_formula_renders_stably():
    r"""$(2)$ $F\left(...\right)$ must not become adjacent dollar math."""
    from latex_utils import split_latex_text, render_segments

    text = r"$(2)$ $F\left( -\frac{1}{2}, 4 \right)$."
    segments = split_latex_text(text)

    assert segments[0]["type"] == "text"
    assert "(2)" in segments[0]["content"]
    assert any(
        s["type"] == "inline_math" and r"\frac{1}{2}" in s["content"]
        for s in segments
    ), f"Formula must remain intact: {segments}"

    rendered = render_segments(segments)
    assert "$$$" not in rendered, f"Must not generate triple dollars: {rendered}"


def test_choice_label_is_not_demoted_as_subquestion_number():
    r"""$(A)$ is a choice label, not the numeric subquestion pattern."""
    from latex_utils import split_latex_text

    segments = split_latex_text(r"$(A)$ $x=1$")
    assert segments[0]["type"] == "inline_math"
    assert segments[0]["content"] == "(A)"


# ═══════════════════════════════════════════════
# Group 8: P1 structural fixes
# ═══════════════════════════════════════════════

def test_latex_protector_nested_calls_do_not_overwrite_mapping():
    """Nested protect_latex calls must not cross-contaminate."""
    from rendering.latex_protector import LaTeXProtector

    p1 = LaTeXProtector()
    p2 = LaTeXProtector()

    a = p1.protect(r"\sin x")
    b = p2.protect(r"\sqrt{x}")

    assert p1.restore(a) == r"\sin x", f"p1 restore failed: {p1.restore(a)}"
    assert p2.restore(b) == r"\sqrt{x}", f"p2 restore failed: {p2.restore(b)}"


def test_grading_service_raises_without_agent():
    """GradingService without agent must raise NotImplementedError."""
    import tempfile, shutil
    from pathlib import Path
    from services.grading_service import GradingService
    tmp = tempfile.mkdtemp()
    try:
        db_path = Path(tmp) / "test.db"
        data_dir = Path(tmp) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        svc = GradingService(db_path, data_dir)
        svc.grade_answer("u1", "q1", "ans")
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════
# Group 9: Display math enforcement (anti-red-formula)
# ═══════════════════════════════════════════════

def test_tagged_equation_forces_display_math():
    r"""\tag{1} equations must be block-level, not inline."""
    from latex_utils import from_legacy_text
    text = r"\bigl[1+g'(y)^2\bigr]f''(x)+\bigl[1+f'(x)^2\bigr]g''(y)=0. \tag{1}"
    structured = from_legacy_text("步骤1：" + text)
    blocks = structured["steps"][0]["blocks"]
    assert any(b["type"] == "latex" and b.get("display") == "block" for b in blocks), (
        f"Tagged equation must be display_math: {blocks}"
    )


def test_long_equation_forces_display_math():
    r"""Long equations with = and 55+ chars must be display_math."""
    from latex_utils import from_legacy_text
    text = r"\frac{f''(x)}{1+f'(x)^2}=-\frac{g''(y)}{1+g'(y)^2}=C"
    structured = from_legacy_text("步骤1：" + text)
    blocks = structured["steps"][0]["blocks"]
    assert any(b["type"] == "latex" and b.get("display") == "block" for b in blocks), (
        f"Long equation must be display_math: {blocks}"
    )


def test_display_formula_tail_text_removed_after_tag():
    r"""\tag{1} 即 — the trailing Chinese text must be stripped."""
    from latex_utils import sanitize_latex_for_render
    text = r"\bigl[1+g'(y)^2\bigr]f''(x)=0. \tag{1} 即"
    fixed = sanitize_latex_for_render(text)
    assert "即" not in fixed, f"Trailing Chinese must be removed: {repr(fixed)}"


def test_integral_line_not_rendered_as_plain_text():
    r"""Long integral formulas must be display_math, not text."""
    from latex_utils import from_legacy_text
    text = r"f(x)=-\int \tan(Cx+A)\,dx=-\frac{1}{C}\ln|\cos(Cx+A)|+B_1,\tag{5}"
    structured = from_legacy_text("步骤3：" + text)
    blocks = structured["steps"][0]["blocks"]
    assert any(b["type"] == "latex" and b.get("display") == "block" for b in blocks), (
        f"Integral line must be display_math: {blocks}"
    )


def test_force_display_math_detects_bigl():
    r"""\bigl triggers display_math via _should_force_display_math."""
    from latex_utils import _should_force_display_math
    assert _should_force_display_math(r"\bigl[1+g'(y)^2\bigr]f''(x)=0")
    assert not _should_force_display_math(r"x=1")


# ═══════════════════════════════════════════════
# Group 10: Tag extraction
# ═══════════════════════════════════════════════

def test_split_latex_tag():
    from latex_utils import split_latex_tag
    body, tag = split_latex_tag(r"x+y=0 \tag{1}")
    assert body == "x+y=0"
    assert tag == "1"


def test_split_latex_tag_without_tag():
    from latex_utils import split_latex_tag
    body, tag = split_latex_tag(r"x+y=0")
    assert body == "x+y=0"
    assert tag is None


def test_split_latex_tag_with_aligned():
    from latex_utils import split_latex_tag
    latex = r"\begin{aligned}a&=b\\c&=d\end{aligned}\tag{2}"
    body, tag = split_latex_tag(latex)
    assert r"\begin{aligned}" in body
    assert tag == "2"


def test_long_tagged_formula_uses_below():
    from latex_utils import _is_long_tagged_formula
    # ~50 chars, single line — should be side-by-side
    body = r"\frac{f''(x)}{1+f'(x)^2}=-\frac{g''(y)}{1+g'(y)^2}"
    assert _is_long_tagged_formula(body) is False

    # >70 chars — should use below layout
    long_body = r"f(x)=-\int\tan(Cx+A)\,dx=-\frac{1}{C}\ln|\cos(Cx+A)|+B_1,\quad g(y)=\frac{1}{C}\ln|\cos(Cy-D)|+B_2"
    assert _is_long_tagged_formula(long_body) is True


def test_aligned_tagged_formula_uses_below():
    from latex_utils import _is_long_tagged_formula
    body = r"\begin{aligned}a&=b\\c&=d\end{aligned}"
    assert _is_long_tagged_formula(body) is True


if __name__ == "__main__":
    tests = [
        test_mixed_existing_math_and_bare_latex,
        test_bare_frac_gets_wrapped_when_mixed,
        test_do_not_wrap_chinese_sentence_as_math,
        test_chinese_only_text_not_wrapped,
        test_no_double_escape_latex_command,
        test_no_double_escape_inline_math,
        test_text_block_with_formula_is_split_not_raw_markdown,
        test_expression_not_fragmented_by_subscript_wrapping,
        test_frac_not_split_across_math_blocks,
        test_pre_wrap_does_not_return_early_on_existing_math,
        test_plain_chinese_with_parentheses_not_math,
        test_existing_display_math_not_rewrapped,
        test_subquestion_number_before_formula_renders_stably,
        test_choice_label_is_not_demoted_as_subquestion_number,
        test_latex_protector_nested_calls_do_not_overwrite_mapping,
        test_grading_service_raises_without_agent,
        test_tagged_equation_forces_display_math,
        test_long_equation_forces_display_math,
        test_display_formula_tail_text_removed_after_tag,
        test_integral_line_not_rendered_as_plain_text,
        test_force_display_math_detects_bigl,
        test_split_latex_tag,
        test_split_latex_tag_without_tag,
        test_split_latex_tag_with_aligned,
        test_long_tagged_formula_uses_below,
        test_aligned_tagged_formula_uses_below,
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


# ═══════════════════════════════════════════════
#  Inline math preservation tests
# ═══════════════════════════════════════════════

def test_inline_theta_stays_inline():
    """$\\theta$ with CJK text must remain inline_math, not display_math."""
    from latex_utils import split_latex_text
    text = r"其中 $\theta$ 是未知参数"
    segs = split_latex_text(text)
    types = {s["type"] for s in segs}
    assert "display_math" not in types, f"Should have no display_math: {types}"
    assert any(s["type"] == "inline_math" and "theta" in s["content"] for s in segs)


def test_multiple_inline_math_not_merged():
    """$x=1$, $y=2$, $z$ must be three separate inline_math segments."""
    from latex_utils import split_latex_text
    text = r"已知 $x=1$, $y=2$, 求 $z$"
    segs = split_latex_text(text)
    inline_count = sum(1 for s in segs if s["type"] == "inline_math")
    assert inline_count == 3, f"Expected 3 inline_math, got {inline_count}: {segs}"


def test_inline_math_after_display_math():
    """Display math then inline math must keep inline as inline."""
    from latex_utils import split_latex_text
    text = r"$$\int_0^1 f(x)dx$$ 其中 $x$ 是变量"
    segs = split_latex_text(text)
    has_display = any(s["type"] == "display_math" for s in segs)
    has_inline = any(s["type"] == "inline_math" and "x" in s["content"] for s in segs)
    assert has_display and has_inline, f"display={has_display} inline={has_inline}"
