import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_latex_validator():
    print("=" * 60)
    print("Test 1: LaTeXValidator")
    print("=" * 60)

    from rendering.latex_validator import LaTeXValidator

    validator = LaTeXValidator()

    result = validator.validate(r"\frac{a}{b")
    print(f"  brace mismatch: valid={result.is_valid}, issues={len(result.issues)}")
    assert not result.is_valid

    fixed = validator.validate_and_fix(r"\frac{a}{b")
    print(f"  fixed: '{fixed.fixed_latex}'")
    assert "}" in fixed.fixed_latex

    result = validator.validate(r"\begin{aligned} x &= y")
    print(f"  begin/end mismatch: valid={result.is_valid}, issues={len(result.issues)}")
    assert not result.is_valid

    fixed = validator.validate_and_fix(r"\begin{aligned} x &= y")
    print(f"  fixed: '{fixed.fixed_latex}'")
    assert r"\end{aligned}" in fixed.fixed_latex

    result = validator.validate(r"\left( \frac{a}{b}")
    print(f"  left/right mismatch: valid={result.is_valid}, issues={len(result.issues)}")
    assert not result.is_valid

    fixed = validator.validate_and_fix(r"\left( \frac{a}{b}")
    print(f"  fixed: '{fixed.fixed_latex}'")
    assert r"\right" in fixed.fixed_latex

    latex = r"y=e^{-\int P(x)\,dx} \left( \int Q(x)e^{\int P(x)\,dx}\,dx + C \right."
    result = validator.validate(latex)
    print(f"  user reported error: valid={result.is_valid}, issues={len(result.issues)}")

    result = validator.validate(r"\frac{a}{b} + \sqrt{c}")
    print(f"  valid LaTeX: valid={result.is_valid}")
    assert result.is_valid

    print("  [PASS] LaTeXValidator\n")


def test_structured_latex_renderer():
    print("=" * 60)
    print("Test 2: StructuredLatexRenderer")
    print("=" * 60)

    from rendering.structured_latex_renderer import (
        LatexRenderer, Equation, AlignedBlock, AlignedLine,
        CasesBlock, ProofIR, ProofStepIR,
    )

    renderer = LatexRenderer()

    eq = Equation(lhs="x^2", rhs="4")
    print(f"  Equation.to_latex(): '{eq.to_latex()}'")
    assert "&=" in eq.to_latex()

    block = AlignedBlock(lines=[
        AlignedLine(content="x^2 + y^2 &= r^2", annotation="def"),
        AlignedLine(content="&= 1", annotation=""),
    ])
    full = block.to_full_latex()
    print(f"  AlignedBlock.to_full_latex(): '{full}'")
    assert r"\begin{aligned}" in full
    assert r"\end{aligned}" in full

    cases = CasesBlock(cases=[
        ("f(x)", "x > 0"),
        ("0", r"x \leq 0"),
    ])
    full = cases.to_full_latex()
    print(f"  CasesBlock.to_full_latex(): '{full}'")
    assert r"\begin{cases}" in full

    proof = ProofIR(
        steps=[
            ProofStepIR(before="x^2", after="4", rule="sqrt"),
            ProofStepIR(before="x", after=r"\pm 2", rule="solve"),
        ],
        conclusion=r"x = \pm 2",
    )
    aligned = proof.to_aligned_block()
    full = aligned.to_full_latex()
    print(f"  ProofIR -> AlignedBlock: '{full}'")
    assert r"\begin{aligned}" in full
    assert r"\boxed" in full

    node = renderer.render_aligned(block)
    print(f"  render_aligned -> node type: {node.type}")
    from rendering.render_ir import RenderType
    assert node.type == RenderType.ALIGN

    node = renderer.render_equation("x^2", "4")
    print(f"  render_equation -> node type: {node.type}")
    assert node.type == RenderType.ALIGN

    print("  [PASS] StructuredLatexRenderer\n")


def test_rewrite_trace_pipeline():
    print("=" * 60)
    print("Test 3: RewriteTrace -> Render IR pipeline")
    print("=" * 60)

    from latex_engine.trace import RewriteTrace, RewriteStep, RewriteLocation

    trace = RewriteTrace(
        steps=[
            RewriteStep(
                rule="simplify",
                before="x^2 + 2x + 1",
                after="(x+1)^2",
            ),
            RewriteStep(
                rule="expand",
                before="(x+1)^2",
                after="x^2 + 2x + 1",
            ),
        ],
        final_expr="(x+1)^2",
    )

    latex = trace.to_latex()
    print(f"  to_latex(): '{latex}'")
    assert r"\begin{aligned}" in latex or r"\begin{align" in latex
    assert r"\end{aligned}" in latex or r"\end{align" in latex

    from rendering.structured_latex_renderer import LatexRenderer
    renderer = LatexRenderer()
    nodes = renderer.render_proof_trace(trace)
    print(f"  render_proof_trace -> {len(nodes)} nodes")
    assert len(nodes) > 0

    from rendering.unified_renderer import UnifiedRenderer
    ur = UnifiedRenderer()
    tree = ur.render(trace)
    print(f"  UnifiedRenderer.render(trace) -> tree type: {type(tree).__name__}")

    print("  [PASS] RewriteTrace pipeline\n")


def test_equality_proof_pipeline():
    print("=" * 60)
    print("Test 4: EqualityProof -> Render IR pipeline")
    print("=" * 60)

    from latex_engine.trace import EqualityProof, ProofStep

    proof = EqualityProof(
        steps=[
            ProofStep(before="x^2 - 4", after="(x-2)(x+2)", theorem="factor"),
            ProofStep(before="(x-2)(x+2) = 0", after=r"x=2 \text{ or } x=-2", theorem="zero"),
        ],
        conclusion=r"x = \pm 2",
        assumptions=[r"x \in \mathbb{R}"],
    )

    latex = proof.to_latex()
    print(f"  to_latex(): '{latex}'")
    assert r"\begin{aligned}" in latex or r"\begin{align" in latex

    from rendering.structured_latex_renderer import LatexRenderer
    renderer = LatexRenderer()
    nodes = renderer.render_equality_proof(proof)
    print(f"  render_equality_proof -> {len(nodes)} nodes")
    assert len(nodes) > 0

    print("  [PASS] EqualityProof pipeline\n")


def test_unified_renderer_text_mode():
    print("=" * 60)
    print("Test 5: UnifiedRenderer text mode (with validation)")
    print("=" * 60)

    from rendering.unified_renderer import UnifiedRenderer

    renderer = UnifiedRenderer()

    tree = renderer.render("plain text")
    print(f"  plain text -> tree: {type(tree).__name__}")

    tree = renderer.render(r"formula $x^2 + y^2 = r^2$ here")
    print(f"  with LaTeX -> tree: {type(tree).__name__}")

    tree = renderer.render(r"compute \frac{1}{2} + \frac{1}{3}")
    print(f"  bare LaTeX -> tree: {type(tree).__name__}")

    text = r"$$\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}$$"
    tree = renderer.render(text)
    print(f"  aligned env -> tree: {type(tree).__name__}")

    text = r"$\begin{aligned} x &= y \end{aligned}$"
    tree = renderer.render(text)
    print(f"  inline aligned -> tree: {type(tree).__name__}")

    text = r"$$\left( \frac{a}{b}$$"
    tree = renderer.render(text)
    print(f"  mismatched left/right -> tree: {type(tree).__name__}")

    print("  [PASS] UnifiedRenderer text mode\n")


def test_user_reported_errors():
    print("=" * 60)
    print("Test 6: User reported error scenarios")
    print("=" * 60)

    from rendering.latex_validator import LaTeXValidator
    from rendering.structured_latex_renderer import LatexRenderer, AlignedBlock, AlignedLine

    validator = LaTeXValidator()
    renderer = LatexRenderer()

    latex1 = r"y=e^{-\int P(x)\,dx} \left( \int Q(x)e^{\int P(x)\,dx}\,dx + C \right."
    result = validator.validate_and_fix(latex1)
    print(f"  error1 right. mismatch: fixed='{result.fixed_latex[:80]}...'")
    recheck = validator.validate(result.fixed_latex)
    print(f"    recheck: valid={recheck.is_valid}")

    latex2 = r"$\begin{aligned} x &= y \end{aligned}$"
    result = validator.validate_and_fix(latex2)
    print(f"  error2 inline aligned: fixed='{result.fixed_latex[:80]}...'")
    if "$$" in result.fixed_latex:
        print(f"    fixed with $$ wrapping: OK")
    else:
        print(f"    no $$ wrapping: WARN (ContentClassifier handles)")

    latex3 = r"\begin{aligned} x &= y + z"
    result = validator.validate_and_fix(latex3)
    print(f"  error3 missing end: fixed='{result.fixed_latex[:80]}...'")
    assert r"\end{aligned}" in result.fixed_latex

    latex4 = r"\frac{a+b}{c-d"
    result = validator.validate_and_fix(latex4)
    print(f"  error4 brace mismatch: fixed='{result.fixed_latex}'")
    assert result.fixed_latex.count("{") == result.fixed_latex.count("}")

    block = AlignedBlock(lines=[
        AlignedLine(content=r"y &= e^{-\int P(x)\,dx} \left( \int Q(x)e^{\int P(x)\,dx}\,dx + C \right)", annotation="general solution"),
    ])
    full = block.to_full_latex()
    print(f"  structured aligned: '{full[:80]}...'")
    assert r"\begin{aligned}" in full
    assert r"\end{aligned}" in full

    node = renderer.render_aligned(block)
    from rendering.render_ir import RenderType
    assert node.type == RenderType.ALIGN
    print(f"    -> Render IR type: ALIGN OK")

    print("  [PASS] User reported errors\n")


if __name__ == "__main__":
    tests = [
        ("Test 1", test_latex_validator),
        ("Test 2", test_structured_latex_renderer),
        ("Test 3", test_rewrite_trace_pipeline),
        ("Test 4", test_equality_proof_pipeline),
        ("Test 5", test_unified_renderer_text_mode),
        ("Test 6", test_user_reported_errors),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
