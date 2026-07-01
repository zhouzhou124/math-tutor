"""Regression tests for derivation-step text compile/render fixes."""

import re

import pytest


@pytest.mark.parametrize(
    "text,expect_types",
    [
        (
            r"\Rightarrow (xy)' = 0 因此本步得到结论：\\",
            {"text"},
        ),
        (
            r"(y = \frac{1}{x})",
            {"text"},
        ),
        (
            r"\Rightarrow xy = C 因此本步得到结论：\(xy = C\)",
            {"text"},
        ),
    ],
)
def test_normalize_text_block_math_derivation_samples(text, expect_types):
    from services.grading_adapter import normalize_text_block_math

    blocks = normalize_text_block_math(text)
    types = {b.get("type") for b in blocks}
    assert expect_types <= types
    for block in blocks:
        content = str(block.get("content") or "")
        if block.get("type") == "latex_display":
            assert "因此本步得到结论" not in content
            assert not content.rstrip().endswith("\\\\")
        if block.get("type") == "text" and "因此本步得到结论" in content:
            assert "：" in content or ":" in content


def test_paren_frac_wrapped_inline():
    from services.grading_adapter import normalize_text_block_math

    from services.grading_adapter import prepare_grading_math_for_render

    blocks = normalize_text_block_math(r"(y = \frac{1}{x})")
    assert len(blocks) == 1
    content = prepare_grading_math_for_render(blocks[0]["content"])
    assert r"\frac{1}{x}" in content
    assert "$" in content and "frac{1}{x}" in content


def test_bare_brace_fragment_not_literal_braces():
    from services.grading_adapter import normalize_inline_math_tokens, prepare_grading_math_for_render

    wrapped = normalize_inline_math_tokens("xy' + {y = 0}")
    assert r"\{y = 0\}" not in wrapped
    rendered = prepare_grading_math_for_render(wrapped)
    assert "$" in rendered
    assert "y = 0" in rendered


def test_repair_incomplete_derivation_strips_truncated_tail():
    from services.grading_adapter import repair_incomplete_derivation_math

    assert "Rightarrow" not in repair_incomplete_derivation_math(
        r"xy' + y = 0 \Rightarrow = -"
    )
    assert repair_incomplete_derivation_math(
        r"\ln|y| = -\ln|x| + \(C_1\) \Rightarrow \(y =\)"
    ).endswith(r"\(C_1\)")


def test_accept_fill_answer_rejects_incomplete():
    from services.grading_adapter import _accept_fill_answer

    assert _accept_fill_answer("y =") == ""
    assert _accept_fill_answer(r"\frac{1}{x}") != ""


def test_prepare_grading_math_renders_ln_chain():
    from services.grading_adapter import prepare_grading_math_for_render

    s = prepare_grading_math_for_render(
        r"\(\frac{dy}{y}\) = -\(\frac{dx}{x}\) \Rightarrow \ln|y| = -\ln|x| + C_1"
    )
    assert r"\(" not in s or s.count(r"\(") == 0
    assert "$" in s
    assert r"\frac{dy}{y}" in s
    assert r"\Rightarrow" in s


def test_repair_derivation_strips_trailing_backslash():
    from services.grading_adapter import repair_derivation_text_block

    assert repair_derivation_text_block(r"因此本步得到结论：\\").endswith("：")
    assert not repair_derivation_text_block(r"因此本步得到结论：\\").endswith("\\")


def test_normalize_math_delimiters_repairs_unbalanced():
    from services.grading_adapter import normalize_math_delimiters_in_text

    out = normalize_math_delimiters_in_text(r"由 \(xy = C 可知")
    assert r"\(" in out and r"\)" in out
    assert out.count(r"\(") == out.count(r"\)")


def test_strip_meta_echo_from_body():
    from services.grading_adapter import _normalize_step_derivation_meta

    reason = "注意到乘积求导公式，将原方程改写。"
    step = _normalize_step_derivation_meta({
        "reason": reason,
        "body_markdown": (
            f"{reason}\n\n"
            "关键变形为：\n\n"
            "$$\n(xy)' = 0\n$$\n\n"
            f"{reason}"
        ),
    })
    assert reason in step["reason"]
    assert reason not in step["body_markdown"]
    assert "关键变形" in step["body_markdown"]


def test_dedupe_section_strips_reason_echo_from_blocks():
    from services.grading_adapter import dedupe_section_content

    view = dedupe_section_content({
        "question_type": "填空题",
        "sections": [{
            "title": "步骤1",
            "reason": "两边积分得到通解。",
            "blocks": [{"type": "text", "content": "两边积分得到通解。\n\n关键变形为：\n\n\\((xy)' = 0\\)"}],
        }],
    })
    content = view["sections"][0]["blocks"][0]["content"]
    assert "两边积分得到通解" not in content
    assert "关键变形" in content


def test_compile_no_cjk_in_latex_display():
    from services.grading_adapter import compile_text_block_to_math_blocks

    blocks = compile_text_block_to_math_blocks(
        r"\Rightarrow xy = C 因此本步得到结论：\(xy = C\)"
    )
    for block in blocks:
        if block.get("type") == "latex_display":
            assert "因此" not in str(block.get("content") or "")


@pytest.mark.parametrize(
    "raw",
    [
        r"极小值 -\frac{1}{e}",
        r"函数有极小值 -\frac{1}{e}",
    ],
)
def test_mixed_cjk_conclusion_splits_to_text_not_display(raw):
    from services.grading_adapter import _latex_display_blocks_without_cjk, _normalize_block_list

    blocks = _latex_display_blocks_without_cjk([{"type": "latex_display", "content": raw}])
    assert blocks
    assert all(b.get("type") != "latex_display" for b in blocks)
    for block in blocks:
        content = str(block.get("content") or "")
        if block.get("type") == "latex_display":
            pytest.fail(f"CJK still in latex_display: {content}")
        assert r"\frac{1}{e}" in content or r"\frac{1}{e}" in raw
    via_list = _normalize_block_list([{"type": "latex_display", "content": raw}])
    assert all(b.get("type") != "latex_display" or "极" not in str(b.get("content") or "") for b in via_list)


def test_partial_derivatives_comma_list_uses_cases_not_broken_aligned():
    """f_x/f_y comma lists must not become one aligned chain with glued LHS."""
    from latex_utils import normalize_derivation_formula_block

    raw = (
        r"f(x,y) = x^2(2 + y^2) + y \ln y, "
        r"f_x = 2x(2 + y^2), f_y = 2x^2y + \ln y + 1"
    )
    out = normalize_derivation_formula_block(raw)
    assert r"\begin{cases}" in out
    assert r"\begin{aligned}" not in out
    assert "f_x" in out and "f_y" in out
    assert ", f_x" not in out.replace("f_x =", "")
    assert ", f_y" not in out.replace("f_y =", "")


def test_prepare_grading_merges_plain_lhs_with_dollar_frac():
    from services.grading_adapter import prepare_grading_math_for_render

    out = prepare_grading_math_for_render(r"y = $\frac{1}{x}$")
    assert r"\frac{1}{x}" in out
    assert out.startswith("$y") and out.endswith("$")
    assert "y = $" not in out


def test_prepare_grading_splits_glued_frac_equations():
    from services.grading_adapter import prepare_grading_math_for_render

    raw = r"$xy' + y = 0 \frac{dy}{y} = -\frac{dx}{x}$"
    out = prepare_grading_math_for_render(raw)
    assert out.count("$") >= 4
    assert r"\frac{dy}{y}" in out
    assert "0 $" in out or out.startswith("$xy'")


def test_prepare_grading_drops_incomplete_dollar_span():
    from services.grading_adapter import prepare_grading_math_for_render

    assert prepare_grading_math_for_render(r"$y = $") == ""
    out = prepare_grading_math_for_render(r"$y=, y(1)=1C=1$")
    assert "C = 1" in out or "C=1" in out
    assert "$y = $" not in out


def test_proof_step_body_skips_duplicate_conclusion():
    from agents.solver_agent import _proof_step_body_markdown
    from types import SimpleNamespace

    step = SimpleNamespace(
        input_state=r"x^2 \int_1^{x^2} e^{-t^2} dt - \int_1^{x^2} t e^{-t^2} dt",
        output_state=r"x^2 \int_1^{x^2} e^{-t^2} dt - \int_1^{x^2} t e^{-t^2} dt",
    )
    body = _proof_step_body_markdown(step)
    assert body.count("因此本步得到结论") == 0
    assert body.count("关键变形为") == 1


def test_dedupe_derivation_conclusion_blocks_removes_repeat_formula():
    from services.grading_adapter import _dedupe_derivation_conclusion_blocks

    formula = r"x^2 \int_1^{x^2} e^{-t^2} dt"
    blocks = _dedupe_derivation_conclusion_blocks([
        {"type": "text", "content": "关键变形为："},
        {"type": "latex_display", "content": rf"a \Rightarrow {formula}"},
        {"type": "text", "content": "因此本步得到结论："},
        {"type": "latex_display", "content": formula},
    ])
    types = [b["type"] for b in blocks]
    assert types.count("latex_display") == 1
    assert "因此本步得到结论" not in " ".join(
        str(b.get("content") or "") for b in blocks if b.get("type") == "text"
    )


def test_sanitize_display_latex_strips_nested_inline_delimiters():
    from services.grading_adapter import sanitize_display_latex

    raw = (
        r"\begin{aligned}"
        r"f_{\max} &= \frac{1}{2}\(1-\frac{1}{e}\),"
        r"\ f_{\min} &= 0"
        r"\end{aligned}"
    )
    out = sanitize_display_latex(raw)
    assert r"\(" not in out
    assert r"\frac{1}{2}" in out


def test_dedupe_repeated_sentences_in_derivation_prose():
    from services.grading_adapter import repair_derivation_text_block

    text = (
        "由 e^{-t^2}\\ge 0 知积分非负，故 f'(x)=0 时 x=0。"
        "由 e^{-t^2}\\ge 0 知积分非负，故 f'(x)=0 时 x=0。"
    )
    out = repair_derivation_text_block(text)
    assert out.count("由 e") == 1


def test_strip_trailing_incomplete_after_constants():
    from services.grading_adapter import _strip_trailing_incomplete_math_tail

    assert _strip_trailing_incomplete_math_tail("C = 1 y =").strip() == "C = 1"


def test_mixed_chinese_cases_splits_to_text_and_cases():
    from services.grading_adapter import normalize_text_block_math

    text = (
        "关键变形为："
        r"\begin{cases} f_x(x,y)=2x(2+y^2) \\ f_y(x,y)=2x^{2}y+\ln y+1 \end{cases}"
    )
    blocks = normalize_text_block_math(text)
    types = [b.get("type") for b in blocks]
    assert "text" in types
    assert "cases" in types
    cases = next(b for b in blocks if b.get("type") == "cases")
    exprs = [r["expr"] for r in cases.get("rows") or []]
    assert any("f_x" in e for e in exprs)
    assert any("f_y" in e for e in exprs)
    for block in blocks:
        if block.get("type") == "latex_display":
            assert "关键变形" not in str(block.get("content") or "")


def test_repair_aligned_wrapping_cases_for_display():
    from services.grading_adapter import sanitize_display_latex

    raw = (
        r"\begin{aligned}"
        r"\begin{cases} f_{xx}(x,y) \\"
        r" &= 2(2+y^{2}) \\ f_{xy}(x,y) \\"
        r" &= 4xy \\ f_{yy}(x,y) \\"
        r" &= 2x^{2}+\frac{1}{y} \end{cases}"
        r"\end{aligned}"
    )
    out = sanitize_display_latex(raw)
    assert r"\begin{aligned}" not in out or r"\begin{cases}" in out
    assert "&=" not in out
    assert "f_{xx}" in out


def test_trim_duplicate_glued_lhs():
    from services.grading_adapter import repair_derivation_text_block

    text = (
        r"AC-B^{2}=4+\frac{2}{e^{2}} \times e-0^{2} "
        r"AC-B^{2}=4e+\frac{2}{e}>0, A>0"
    )
    out = repair_derivation_text_block(text)
    assert out.count("AC-B") == 1


def test_trailing_backslash_paren_stripped_from_display():
    from services.grading_adapter import sanitize_display_latex

    out = sanitize_display_latex(
        r"f(0,e^{-1})=0^{2}(2+(e^{-1})^{2})+e^{-1}\ln(e^{-1})\)"
    )
    assert not out.endswith(r"\)")
    assert r"\ln" in out


def test_compile_text_block_preserves_display_math_block():
    from services.grading_adapter import compile_text_block_to_math_blocks

    body = (
        "中间公式为：\n\n"
        "$$\n"
        r"\begin{aligned} f_x \\ &= 2x(2+y^2), \\ f_y \\ &= 2x^2y+\ln y+1 \end{aligned}"
        "\n$$"
    )
    blocks = compile_text_block_to_math_blocks(body)
    assert any(b.get("type") == "cases" for b in blocks)
    assert not any(
        b.get("type") == "latex_display"
        and r"\begin{aligned}" in str(b.get("content") or "")
        for b in blocks
    )


def test_body_markdown_parsed_into_display_blocks():
    from services.grading_adapter import _ensure_body_markdown_blocks

    structured = _ensure_body_markdown_blocks({
        "steps": [{
            "label": "步骤1",
            "body_markdown": (
                "中间公式为：\n\n$$\nf_x=2x(2+y^2)\n$$\n\n"
                "因此本步得到结论：\n\n$$\nf_y=2x^2y+\\ln y+1\n$$"
            ),
        }],
    })
    blocks = structured["steps"][0]["blocks"]
    types = [b.get("type") for b in blocks]
    assert "text" in types
    assert "latex_display" in types or "cases" in types
    assert all(
        r"\begin{aligned}" not in str(b.get("content") or "")
        for b in blocks
        if b.get("type") == "text"
    )


def test_repair_aligned_equation_system_to_cases():
    from latex_utils import repair_system_display_latex

    raw = (
        r"\begin{aligned}"
        r"f_x \\"
        r"&= 2x(2+y^2), \\ f_y \\"
        r"&= 2x^2 y + \ln y + 1"
        r"\end{aligned}"
    )
    out = repair_system_display_latex(raw)
    assert r"\begin{cases}" in out
    assert "f_x" in out and "f_y" in out
    assert r"\begin{aligned}" not in out


def test_merge_cjk_prose_lines_rejoins_orphan_punctuation():
    from services.grading_adapter import _merge_cjk_prose_lines

    raw = "由 $f_x=0$ 得\n，因为 $2+y^2>0$\n，故必有 $x=0$。"
    out = _merge_cjk_prose_lines(raw)
    assert "\n，" not in out
    assert "，因为" in out


def test_normalize_text_block_math_keeps_chinese_narrative_single_text():
    from services.grading_adapter import normalize_text_block_math

    text = (
        "由 $f_x=0$ 得 $2x(2+y^2)=0$，因为 $2+y^2>0$，故必有 $x=0$。"
        "代入 $f_y=0$ 解得 $\\ln y=-1$。"
    )
    blocks = normalize_text_block_math(text)
    text_blocks = [b for b in blocks if b.get("type") == "text"]
    assert len(text_blocks) == 1
    content = text_blocks[0]["content"]
    assert "，因为" in content
    assert not content.strip().startswith("，")


def test_lilei_vol6_q17_standard_solution_view_no_recursion():
    import json
    from pathlib import Path

    from services.grading_adapter import build_standard_solution_view

    path = Path("storage/questions/simulations4/26李擂八套卷-卷六-017.json")
    q = json.loads(path.read_text(encoding="utf-8"))
    solution = {
        "success": True,
        "standard_answer": q["standard_answer"],
        "total_score": q["score"],
        "steps": q["solution_steps"],
    }
    view = build_standard_solution_view(solution, "解答题", {})
    assert len(view.get("sections") or []) >= 4
    joined = " ".join(
        str(b.get("content") or "")
        for s in view.get("sections") or []
        for b in s.get("blocks") or []
    )
    assert "详细解析暂未生成" not in joined
    assert "分部积分" in joined or "V_1" in joined


def test_attach_lhs_to_display_aligned_first_row():
    from services.grading_adapter import _attach_lhs_to_display_latex

    out = _attach_lhs_to_display_latex(
        "A",
        r"\begin{aligned} f_{xx}(0,e^{-1}) \\ &= 4+2e^{-2}>0 \end{aligned}",
    )
    assert "A &=" in out or "A&=" in out.replace(" ", "")
    assert out.strip().startswith(r"\begin{aligned}")
    assert not re.search(r"^A\s*\\\\", out, re.M)


def test_consolidate_view_blocks_merges_orphan_fragment_text():
    from services.grading_adapter import consolidate_view_blocks

    blocks = consolidate_view_blocks([
        {"type": "text", "content": "由 $f_x=0$ 得"},
        {"type": "text", "content": "，因为 $2+y^2>0$"},
    ])
    assert len([b for b in blocks if b.get("type") == "text"]) == 1
    assert "，因为" in blocks[0]["content"]


def test_aligned_chain_first_line_has_lhs_ampersand():
    from latex_utils import normalize_derivation_formula_block

    out = normalize_derivation_formula_block(r"f_x = 2x(2+y^2) = 4x + 2xy^2")
    assert r"\begin{aligned}" in out
    first_row = out.split("\\\\")[0]
    assert "f_x" in first_row and "&=" in first_row
