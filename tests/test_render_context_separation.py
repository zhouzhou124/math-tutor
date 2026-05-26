"""P27: Question bank vs grading renderer separation regression tests."""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_question_bank_renderer_does_not_apply_ai_repair():
    from renderers.math_render_policy import render_question_bank_latex

    with patch("services.solution_legacy_repair.repair_legacy_solution_text") as mock:
        render_question_bank_latex(r"已知 $x=1$，求 $\frac{a}{b}$")
        mock.assert_not_called()


def test_grading_renderer_applies_ai_repair():
    from renderers.math_render_policy import render_grading_latex

    with patch(
        "services.solution_legacy_repair.repair_legacy_solution_text",
        side_effect=lambda s: s,
    ) as mock:
        render_grading_latex(r"步骤1：计算 $\frac{1}{2}$")
        mock.assert_called_once()


def test_normalize_does_not_corrupt_display_math_with_text_other():
    """\\text{其他} inside $$cases$$ must not become \\text{$其他$}."""
    from latex_normalizer import normalize_latex_style

    raw = (
        r"$$f(x) = \begin{cases} \lambda^2 x e^{-\lambda x}, & x>0 \\ 0, & \text{其他} \end{cases}$$"
        r"其中$\lambda>0$ 未知"
    )
    out = normalize_latex_style(raw)
    assert r"\text{$" not in out
    assert r"\text{其他}" in out


def test_parse_legacy_preserves_raw_stem_for_question_bank():
    from exam_parser.simple_parser import parse_latex_question
    from question_ast import parse_legacy
    from latex_utils import split_latex_text

    raw = (
        r"设总体 $X$ 的概率密度为"
        r"$$f(x) = \begin{cases} \lambda^2 x e^{-\lambda x}, & x>0 \\ 0, & \text{其他} \end{cases}$$"
        r"其中$\lambda>0$ 未知"
    )
    parsed = parse_latex_question(raw)
    q = {"question_type": "解答题", "raw_question_text": raw, **parsed}
    ast = parse_legacy(q)
    segs = split_latex_text(ast.stem)
    assert sum(1 for s in segs if s["type"] == "display_math") == 1
    assert any(s["type"] == "text" and "其中" in s["content"] for s in segs)


def test_question_bank_cjk_tail_after_display_math_stays_inline():
    """$$cases$$ 后的中文 + 多个 $...$ 不应被升级为 display。"""
    from latex_utils import split_latex_text

    text = (
        r"$$\begin{cases} x=1 \\ y=2 \end{cases}$$"
        r"因此函数在 $x=0$ 处取得极值，且 $f(x)=x^2$。"
    )
    segments = split_latex_text(text)
    display = [s for s in segments if s.get("type") == "display_math"]
    inline = [s for s in segments if s.get("type") == "inline_math"]
    text_segs = [s for s in segments if s.get("type") == "text"]

    assert len(display) == 1, segments
    assert any("x=0" in s.get("content", "") for s in inline), segments
    assert any("因此函数" in s.get("content", "") for s in text_segs), segments


def test_grading_solution_can_render_repaired_frac():
    from services.solution_legacy_repair import repair_broken_frac_blocks
    from latex_utils import split_latex_text

    broken = r"$\frac{1}{2}$"
    repaired = repair_broken_frac_blocks(broken)
    segments = split_latex_text(repaired)
    math = [s for s in segments if s.get("type") in ("inline_math", "display_math")]
    assert math, segments


def test_question_bank_broken_looking_text_not_auto_rewritten_by_ai_repair():
    from renderers.math_render_policy import render_question_bank_latex

    raw = r"$\frac{1}{2}$"
    with patch("services.solution_legacy_repair.repair_broken_frac_blocks") as frac_mock:
        with patch("services.solution_legacy_repair.clean_mojibake_tokens") as mojibake_mock:
            render_question_bank_latex(raw)
            frac_mock.assert_not_called()
            mojibake_mock.assert_not_called()


def test_render_ast_never_uses_st_latex_by_default():
    import inspect
    from latex_utils import render_ast

    src = inspect.getsource(render_ast)
    assert "use_st_latex" in src
    # Default path must not call st.latex when use_st_latex=False (the default).
    assert 'if use_st_latex:' in src or 'elif use_st_latex:' in src


def test_safe_render_requires_context():
    import pytest
    from latex_utils import safe_render

    with pytest.raises(ValueError, match="requires explicit context"):
        safe_render("x=1")


def test_no_triple_dollar_in_question_bank_segments():
    from latex_utils import split_latex_text, render_segments

    text = r"已知 $a=1$ 且 $$b=2$$ 以及 $c=3$"
    md = render_segments(split_latex_text(text))
    assert "$$$" not in md


def test_no_triple_dollar_in_grading_segments_after_repair():
    from renderers.math_render_policy import GRADING_POLICY, _apply_policy_repairs
    from latex_utils import split_latex_text, render_segments

    text = r"步骤1：$a=1$ 且 $$b=2$$"
    repaired = _apply_policy_repairs(text, GRADING_POLICY)
    md = render_segments(split_latex_text(repaired))
    assert "$$$" not in md
