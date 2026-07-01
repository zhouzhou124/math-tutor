from services.grading_adapter import (
    _blocks_from_text,
    _normalize_math_tokens,
    formula_requires_display_layout,
    normalize_text_block_math,
)


def test_latex_ne_command_is_not_treated_as_json_newline():
    normalized = _normalize_math_tokens(r"x\ne 0")

    assert normalized == r"x\ne 0"
    assert "\n" not in normalized
    assert not formula_requires_display_layout(r"x\ne 0")


def test_double_escaped_ne_command_is_repaired_before_layout_decision():
    normalized = _normalize_math_tokens(r"x\\ne 0")

    assert normalized == r"x\ne 0"
    assert "\n" not in normalized
    assert not formula_requires_display_layout(r"x\\ne 0")


def test_choice_piecewise_prose_keeps_short_formulas_inline():
    text = (
        r"由于含有 $\ln |x|$，要求 $|x|>0$，故定义域为 $x\ne 0$。"
        r"当 $x>0$ 时，$f(x)=\ln x$；当 $x<0$ 时，$f(x)=\ln(-x)$。"
    )

    blocks = normalize_text_block_math(text)

    assert blocks == [{"type": "text", "content": text}]
    assert all(block.get("type") != "latex_display" for block in blocks)


def test_blocks_from_text_does_not_fragment_ne_or_inline_formula_prose():
    text = r"左、右导数不相等（$-1\ne 1$），因此 $x=1$ 不是驻点。"

    blocks = _blocks_from_text(text)

    assert len(blocks) == 1
    assert blocks[0]["type"] == "text"
    assert r"-1\ne 1" in blocks[0]["content"]
    assert "\n" not in blocks[0]["content"]
