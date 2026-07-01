"""Glued multi-equation split for Taylor/limit derivations."""


def test_glued_sin_expressions_split_to_cases():
    from latex_utils import normalize_derivation_formula_block

    glued = (
        r"\sin x = x - \frac{x^3}{6} + \frac{x^5}{120} + o(x^5)"
        r" \sin(\sin x) = x - \frac{x^3}{3} + \frac{x^5}{10} + o(x^5)"
    )
    out = normalize_derivation_formula_block(glued)
    assert r"\begin{cases}" in out
    assert out.count(r"\sin(\sin x)") == 1


def test_glued_limit_after_order_term_splits():
    from latex_utils import normalize_derivation_formula_block

    glued = (
        r"= \frac{1}{6}x^4 + o(x^4)"
        r" \lim_{x \to 0} \frac{\frac{1}{6}x^4 + o(x^4)}{x^4} = \frac{1}{6}"
    )
    out = normalize_derivation_formula_block(glued)
    assert r"\lim_" in out
    assert r"\begin{cases}" in out or r"\begin{aligned}" in out
