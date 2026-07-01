from services.grading_adapter import (
    contains_raw_tex_outside_math,
    normalize_standard_solution_view,
    normalize_text_block_math,
)


def test_equivalent_infinitesimal_lim_frac_sqrt_in_prose():
    text = (
        r"等价无穷小定义：若 \lim_{x \to 0^+}\frac{f(x)}{\sqrt{x}}=1，"
        r"则f(x)与 \sqrt{x} 等价"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\lim_{x \to 0^+}\frac{f(x)}{\sqrt{x}}=1" in rendered.replace("$", "")
    assert r"\frac{f(x)}{\}" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_polar_coordinate_prose_does_not_wrap_chinese_inside_math():
    text = (
        r"采用极坐标变换 x = r\cos\theta, y = r\sin\theta，"
        r"则 x^2+y^2=r^2，面积元 dx dy = r dr d\theta。"
        r"区域D对应 r \in [0,1], \theta \in [-\pi/2, \pi/2]。"
    )

    blocks = normalize_text_block_math(text)

    assert len(blocks) == 1
    content = blocks[0]["content"]
    assert blocks[0]["type"] == "text"
    assert "采用极坐标变换" in content
    assert "区域D对应" in content
    assert r"$x = r\cos\theta, y = r\sin\theta$" in content
    assert r"$dx\,dy = r dr d\theta$" in content
    assert not contains_raw_tex_outside_math(content)


def test_bare_frac_pi_and_broken_int_fragment_are_repaired_in_prose():
    text = (
        r"凑微分 d(1+r^2)=2rdr，于是 \int,d。"
        r"代入上下限得\frac12$(\ln 2 - \ln 1)=\frac12\ln 2。"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\int,d" not in rendered
    assert r"\frac12" not in rendered
    assert r"\frac{1}{2}" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_pi_in_chinese_reason_stays_inline_not_raw_red():
    text = r"被积函数为常数，区间长度为 \pi，故积分为 \frac{1}{2}\ln 2 \cdot \pi = \frac{\pi}{2}\ln 2。"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\pi" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_reason_echo_is_removed_from_body_text():
    reason = r"采用极坐标变换 x = r\cos\theta, y = r\sin\theta，面积元 dx dy = r dr d\theta。"
    view = {
        "question_type": "解答题",
        "sections": [
            {
                "title": "步骤2",
                "reason": reason,
                "blocks": [{"type": "text", "content": reason + " 区域D对应 r \\in [0,1]。"}],
            }
        ],
    }

    normalized = normalize_standard_solution_view(view)

    assert normalized["sections"][0]["reason"]
    rendered = "\n".join(str(block.get("content", "")) for block in normalized["sections"][0]["blocks"])
    assert "采用极坐标变换" not in rendered
    assert "区域D对应" in rendered


def test_semantic_reason_rewrite_is_not_rendered_twice():
    reason = r"区域 D 关于 x 轴对称，被积函数中 \frac{xy}{1+x^2+y^2} 关于 y 是奇函数，该项积分为零，因此原积分仅剩第一项。"
    body = r"区域 D 关于 x 轴对称，被积函数中 \frac{xy}{1+y^2} 关于 y 是否奇函数，该项积分为零，因此原积分仅剩第一项。"
    view = {
        "question_type": "解答题",
        "sections": [
            {
                "title": "步骤1",
                "reason": reason,
                "blocks": [
                    {"type": "text", "content": body},
                    {"type": "latex_display", "content": r"I=\iint_D \frac{1}{1+x^2+y^2}\,dx\,dy"},
                ],
            }
        ],
    }

    normalized = normalize_standard_solution_view(view)

    texts = [block.get("content", "") for block in normalized["sections"][0]["blocks"] if block.get("type") == "text"]
    assert not any("区域 D 关于 x 轴对称" in text for text in texts)
    assert any(block.get("type") == "latex_display" for block in normalized["sections"][0]["blocks"])


def test_split_integral_dtheta_and_incomplete_tail_are_repaired():
    text = r"外层积分 \int_0^\pi $d\theta = \pi，故 I = \pi \cdot。"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\int_0^\pi d\theta" in rendered
    assert r"\cdot" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_render_math_text_keeps_chinese_reason_inline(monkeypatch):
    import renderers.components.grading_result as gr

    markdown_calls: list[str] = []
    monkeypatch.setattr(gr.st, "markdown", lambda body, **kwargs: markdown_calls.append(str(body)))

    gr.render_math_text(
        r"采用极坐标变换 x = r\cos\theta, y = r\sin\theta，积分区域为 0\le\theta\le\pi。"
    )

    rendered = "\n".join(markdown_calls)
    assert r"$x = r\cos\theta, y = r\sin\theta$" in rendered
    assert (r"0\le\theta\le\pi" in rendered) or (r"0\le \theta\le \pi" in rendered)
    assert r"x = r\cos\theta" not in rendered.replace(r"$x = r\cos\theta, y = r\sin\theta$", "")


def test_exp_function_rewrite_stays_one_inline_formula():
    text = (
        "\u5148\u5c06 f(x) \u6539\u5199\u4e3a "
        r"f(x)=\exp\(x \ln1+\frac{1}{x})."
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\exp\(" not in rendered
    assert r"$f(x)=\exp(x \ln(1+\frac{1}{x}))$" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_well_formed_nested_exp_formula_is_not_truncated():
    text = (
        "\u5148\u5c06 f(x) \u6539\u5199\u4e3a "
        r"f(x)=\exp(x \ln(1+\frac{1}{x}))."
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$f(x)=\exp(x \ln(1+\frac{1}{x}))$" in rendered
    assert r"$f(x)=\exp(x \ln(1+\frac{1}{x})$" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_statistics_title_math_is_formatted_inline():
    from renderers.components.grading_result import _format_solution_title

    title = "\u6b65\u9aa43: \u8ba1\u7b97 " + r"E(\overline{X}^2)"

    rendered = _format_solution_title(title)

    assert r"$E(\overline{X}^2)$" in rendered
    assert r"\overline{X}" not in rendered.replace(r"$E(\overline{X}^2)$", "")
    assert not contains_raw_tex_outside_math(rendered)


def test_statistics_reason_collapses_repeated_inline_delimiters():
    text = (
        "\u5229\u7528\u65b9\u5dee\u5c55\u5f00\u516c\u5f0f "
        r"\(\(\(E(X^2)=D(X)+(E(X))^2"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$E(X^2)=D(X)+(E(X))^2$" in rendered
    assert r"\(\(" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_overline_and_power_in_prose_are_inline_math():
    text = "\u5f97\u5230 " + r"\overline{X}" + " \u548c S^2 \u7684\u5206\u5e03\u4e0e\u72ec\u7acb\u6027"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$\overline{X}$" in rendered
    assert r"$S^2$" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_final_answer_text_command_demoted_and_numbered_items_split():
    text = (
        r"(1) f(t)=1-\mathrm{e}^{t}+t\mathrm{e}^{t}; "
        r"(2) \text{平均值}2"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$f(t)=1-\mathrm{e}^{t}+t\mathrm{e}^{t}$" in rendered
    assert r"\text" not in rendered
    assert "平均值2" in rendered
    assert "(2)" not in rendered.split("$", 2)[1]
    assert rendered.count("$") == 2
    assert not contains_raw_tex_outside_math(rendered)


def test_glued_bare_integral_and_existing_inline_span_keep_balanced_dollars():
    text = "外层积分 " + r"\int_0^\pi $d\theta=\pi$" + "，故 " + r"I=\pi\cdot。"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$\int_0^\pi d\theta=\pi$" in rendered
    assert rendered.count("$") % 2 == 0
    assert r"\cdot" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_cjk_raw_frac_stops_before_chinese_tail():
    text = "利用不等式" + r"\frac{2\ln(1+x)}{x}>\sin x" + "推出"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$\frac{2\ln(1+x)}{x}>\sin x$" in rendered
    assert "利用不等式" in rendered
    assert "推出" in rendered
    assert r"\sin x推出" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_cjk_pmatrix_environment_renders_as_latex_block():
    text = "分析选项D：" + r"\begin{pmatrix}A+B \\ BA+B^2\end{pmatrix}" + r"x=0"

    blocks = normalize_text_block_math(text)
    text_rendered = "\n".join(str(block.get("content", "")) for block in blocks if block.get("type") == "text")

    assert any(
        block.get("type") == "latex_display" and r"\begin{pmatrix}" in str(block.get("content", ""))
        for block in blocks
    )
    assert r"\begin{pmatrix}" not in text_rendered
    assert r"$x=0$" in text_rendered
    assert not contains_raw_tex_outside_math(text_rendered)


def test_cjk_quadratic_matrix_expression_keeps_relation_together():
    text = (
        "将二次曲面方程"
        + r"(x,y,z)A\begin{pmatrix}x\\y\\z\end{pmatrix}=1"
        + "化为标准方程"
    )

    blocks = normalize_text_block_math(text)
    latex_blocks = [
        str(block.get("content", ""))
        for block in blocks
        if block.get("type") == "latex_display"
    ]
    text_rendered = "\n".join(
        str(block.get("content", ""))
        for block in blocks
        if block.get("type") == "text"
    )

    assert any(
        "(x,y,z)A" in content
        and r"\begin{pmatrix}" in content
        and "=1" in content
        for content in latex_blocks
    )
    assert "(x,y,z)A" not in text_rendered
    assert "=1" not in text_rendered
    assert "化为标准方程" in text_rendered
    assert not contains_raw_tex_outside_math(text_rendered)


def test_fill_final_identity_glued_text_is_split():
    blocks = normalize_text_block_math(
        "由于被积函数非负且连续，积分非正只能函数恒为零，故 f(x)=x^2 f(x)-x^2=0"
    )
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "故 $f(x)=x^2$" in rendered
    assert "$f(x)-x^2=0$" in rendered
    assert "$f(x)=x^2 f(x)-x^2=0$" not in rendered


def test_glued_condition_after_equation_is_split_before_wrapping():
    blocks = normalize_text_block_math(
        "因此 y(1-0)=1 x\\gt1 时 y'-y=x-1"
    )
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "$y(1-0)=1$" in rendered
    assert "$x>1$" in rendered
    assert r"y(1-0)=1 x\gt1" not in rendered


def test_truncated_gamma_command_is_repaired_before_render():
    from services.solution_quality import has_broken_latex_fragments

    text = "计算数学期望 " + r"EX=\Gamm(3)=2"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\Gamma(3)" in rendered
    assert r"\Gamm(3)" not in rendered
    assert not has_broken_latex_fragments(rendered)


def test_probability_set_relations_are_wrapped_as_math():
    text = (
        "\u7531ABC = " + r"\emptyset" + "\u77e5AB" + r"\subseteq\overline C"
        + "\uff0c\u6545" + r"P(AB)\leP(\overline C)"
        + "\uff0c\u5373" + r"p^2 \le 1-p"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\leP" not in rendered
    assert r"\subseteq" in rendered
    assert r"\overline C" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_orphan_aligned_tail_and_fragment_markers_are_removed():
    text = (
        "\ufffdL2\ufffd\n"
        r"S(x)&=-\ln(1-x)-\frac{1}{2x}\ln\frac{1+x}{1-x}"
        "\n"
        r"\\&=-\ln(1-x^2)"
        "\n"
        r"\end{aligned}"
        "\n\ufffdL3\ufffd"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "\ufffdL2\ufffd" not in rendered
    assert "\ufffdL3\ufffd" not in rendered
    assert r"\end{aligned}" not in rendered or r"\begin{aligned}" in rendered
    assert any(
        block.get("type") == "latex_display"
        and r"\begin{aligned}" in str(block.get("content", ""))
        for block in blocks
    )


def test_orphan_end_aligned_does_not_render_as_raw_text():
    text = (
        "\u8ba1\u7b97\u57fa\u672c\u79ef\u5206\n"
        r"\int_0^\pi t\sin t\,dt &= \pi"
        "\n"
        r"\end{aligned}"
        "\n\u56e0\u6b64"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\end{aligned}" not in rendered or r"\begin{aligned}" in rendered
    assert not contains_raw_tex_outside_math(
        "\n".join(str(block.get("content", "")) for block in blocks if block.get("type") == "text")
    )


def test_trailing_single_backslash_in_formula_tail_is_removed():
    text = "\u8ba1\u7b97\u57fa\u672c\u79ef\u5206 " + r"\int_0^\pi\ " + "\u56e0\u6b64"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "\\int_0^\\pi\\" not in rendered
    assert not contains_raw_tex_outside_math(
        "\n".join(str(block.get("content", "")) for block in blocks if block.get("type") == "text")
    )


def test_de_step2_misused_cases_becomes_aligned_display():
    text = (
        "\u53d8\u5f62\u5e76\u79ef\u5206\u5c06\u53f3\u7aef\u6539\u5199\u6210"
        r"\frac{1-x}{x}=\frac{1}{x} - 1,"
        "\u4e24\u8fb9\u540c\u65f6\u4e0d\u5b9a\u79ef\u5206\uff1a"
        r"\frac{1-x}{x}=\frac{1}{x} - 1,"
        r"\begin{cases} \int \frac{\mathrm{d}y}{y} = \int \(\frac{1}{x} - 1\)\mathrm{d}x"
        r"\\C_1 \ln|y| = \ln|x| - x + \end{cases}"
    )

    blocks = normalize_text_block_math(text)
    text_rendered = "\n".join(
        str(block.get("content", "")) for block in blocks if block.get("type") == "text"
    )

    assert any(
        block.get("type") == "latex_display"
        and r"\begin{aligned}" in str(block.get("content", ""))
        and r"\int \frac{\mathrm{d}y}{y}" in str(block.get("content", ""))
        and r"C_1 \ln|y|" in str(block.get("content", ""))
        for block in blocks
    )
    assert not any(block.get("type") == "cases" for block in blocks)
    assert r"\frac{1-x}{x}=\frac{1}{x} - 1" in text_rendered
    assert not contains_raw_tex_outside_math(text_rendered)


def test_de_step3_l0_marker_and_duplicate_clause_are_removed():
    text = (
        "\u5316\u7b80\u5e76\u5199\u51fa\u901a\u89e3\u5c06\u4e0a\u5f0f\u6307\u6570\u5316\uff1a"
        r"$|y|=e^{\ln|x|-x+C_1} = e^{C_1}|x|e^{-x}$."
        "\u53bb\u6389\u7edd\u5bf9\u503c\u7b26\u53f7\u65f6\u5f15\u5165\u5e38\u6570"
        r"$C = \pm e^{C_1}$\uff08\u5b83\u53ef\u53d6\u4efb\u610f\u975e\u96f6\u5b9e\u6570\uff09\uff0c"
        r"\u5219\ufffdL0\ufffd\u53bb\u6389\u7edd\u5bf9\u503c\u7b26\u53f7\u65f6\u5f15\u5165\u5e38\u6570 $y = Cxe^{-x}$."
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "\ufffdL0\ufffd" not in rendered
    assert "L0" not in rendered
    assert rendered.count("\u53bb\u6389\u7edd\u5bf9\u503c\u7b26\u53f7\u65f6\u5f15\u5165\u5e38\u6570") == 1
    assert "$y = Cxe^{-x}$" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_implicit_function_equation_stack_becomes_aligned_display():
    text = (
        r"\begin{cases}"
        r"f(0)=0 \\"
        r"f'(0)=0"
        r"\end{cases}"
    )

    blocks = normalize_text_block_math(text)

    assert any(
        block.get("type") == "latex_display"
        and r"\begin{aligned}" in str(block.get("content", ""))
        and "f(0)" in str(block.get("content", ""))
        and "f'(0)" in str(block.get("content", ""))
        for block in blocks
    )
    assert not any(block.get("type") == "cases" for block in blocks)


def test_piecewise_condition_first_rows_pair_correctly():
    text = (
        r"f'(x)=\begin{cases}"
        r"x>0 \\"
        r"\frac{2x+\sin x+x\cos x}{2+\sin y} \\"
        r"x<0 \\"
        r"\frac{2x-\sin x-x\cos x}{2+\sin y}"
        r"\end{cases}"
    )

    blocks = normalize_text_block_math(text)
    cases = next((b for b in blocks if b.get("type") == "cases"), None)

    assert cases is not None
    rows = cases.get("rows") or []
    assert rows[0]["condition"] == "x>0"
    assert r"\frac{2x+\sin x+x\cos x}{2+\sin y}" in rows[0]["expr"]
    assert rows[1]["condition"] == "x<0"
    assert r"\frac{2x-\sin x-x\cos x}{2+\sin y}" in rows[1]["expr"]


def test_broken_lim_underscore_and_stray_tex_comma_in_cjk_prose():
    text = (
        "左、右导数不相等，故 "
        r"\lim_ 不存在"
        "；又 "
        r"f'(0)=0,\ f' 连续,\ f''(0) 不存在"
        "，选项 (C) 正确。"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"\lim_" not in rendered
    assert "极限不存在" in rendered
    assert r"\," not in rendered
    assert not contains_raw_tex_outside_math(rendered)
