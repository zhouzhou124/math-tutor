"""Question-bank multipart layout regressions."""


def test_question_bank_policy_keeps_subquestions_on_separate_lines():
    from renderers.math_render_policy import _preserve_question_bank_subquestion_lines

    raw = (
        r"其中$\lambda>0$ 未知，$X_1,\dots,X_n$ 为样本."
        "\n"
        r"$(1)$ 求 $\lambda$ 的矩估计量；"
        "\n"
        r"$(2)$ 求 $\lambda$ 的最大似然估计量."
    )

    out = _preserve_question_bank_subquestion_lines(raw)

    assert "样本.\n\n$(1)$ 求" in out
    assert "估计量；\n\n$(2)$ 求" in out


def test_question_bank_render_markdown_separates_stem_and_subquestions(monkeypatch):
    import streamlit as st
    from renderers.math_render_policy import render_question_bank_latex

    markdown_calls: list[str] = []
    monkeypatch.setattr(st, "markdown", lambda body, *a, **kw: markdown_calls.append(body))
    monkeypatch.setattr(st, "text", lambda *a, **kw: None)
    monkeypatch.setattr(st, "latex", lambda *a, **kw: None)

    raw = (
        r"设总体 $X$ 的概率密度为"
        r"$$f(x)=\begin{cases}\lambda^2xe^{-\lambda x}, & x>0 \\ 0, & \text{其他}\end{cases}$$"
        "\n"
        r"其中$\lambda>0$ 未知，$X_1,\dots,X_n$ 为样本."
        "\n"
        r"$(1)$ 求 $\lambda$ 的矩估计量；"
        "\n"
        r"$(2)$ 求 $\lambda$ 的最大似然估计量."
    )

    render_question_bank_latex(raw)
    rendered = "\n".join(markdown_calls)

    assert "样本.\n\n(1) 求 $\\lambda$ 的矩估计量；" in rendered
    assert "矩估计量；\n\n(2) 求 $\\lambda$ 的最大似然估计量." in rendered
