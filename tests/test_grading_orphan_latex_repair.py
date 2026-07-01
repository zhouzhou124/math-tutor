from services.grading_adapter import (
    _normalize_block_list,
    _normalize_solution_block,
    normalize_text_block_math,
)


def test_orphan_left_right_wrappers_are_removed_from_display_formula():
    raw = (
        r"\iint\limits_{\Sigma} = -\left\iiint\limits_{\Omega} 6\, dV"
        r" - \iint\limits_{\Sigma_1}\right\right."
    )

    block = _normalize_solution_block({"type": "latex_display", "content": raw})

    assert block["type"] == "latex_display"
    assert r"\left\iiint" not in block["content"]
    assert r"\right" not in block["content"]
    assert r"\iiint\limits_{\Omega}" in block["content"]


def test_text_math_path_also_removes_orphan_right_wrapper():
    raw = (
        r"\iint\limits_{\Sigma} = -\left\iiint\limits_{\Omega} 6\, dV"
        r" - \iint\limits_{\Sigma_1}\right\right."
    )

    blocks = normalize_text_block_math(raw)

    assert blocks
    assert all(r"\right" not in str(block.get("content", "")) for block in blocks)


def test_orphan_cases_tail_is_removed_before_inline_wrapping():
    blocks = _normalize_block_list([{"type": "text", "content": r"dV=2\pi\end{cases}"}])

    assert blocks == [{"type": "latex_display", "content": r"dV=2\pi"}]


def test_display_row_spacing_marker_does_not_render_as_raw_latex():
    raw = (
        r"P\{M=m\}=\sum_{n=m}^{\infty}P\{N=n\}P\{M=m\mid N=n\}"
        r"\[4pt]=\sum_{n=m}^{\infty}\frac{(2e^2)^n}{n!}e^{-2e^2}"
    )

    block = _normalize_solution_block({"type": "latex_display", "content": raw})

    assert block["type"] == "latex_display"
    assert "[4pt]" not in block["content"]
    assert r"\[" not in block["content"]
    assert r"\mid N=n" in block["content"]


def test_cases_enumeration_tail_is_merged_into_condition_row():
    raw = (
        r"\begin{cases}"
        r"P\{N=n\}=\frac{(2e^2)^n}{n!}e^{-2e^2}\\"
        r" n=0\\ 1\\ 2\\ \ldots"
        r"\end{cases}"
    )

    block = _normalize_solution_block({"type": "latex_display", "content": raw})

    assert block["type"] == "cases"
    rows = block["rows"]
    assert len(rows) == 1
    assert rows[0]["expr"].endswith(r", n=0,1,2,\ldots")
