import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering.structured_latex_renderer import (
    LatexRenderer, Equation, AlignedBlock, AlignedLine,
    CasesBlock, ProofIR, ProofStepIR,
)

renderer = LatexRenderer()

eq = Equation(lhs="x^2", rhs="4")
print("Equation.to_latex():", repr(eq.to_latex()))

block = AlignedBlock(lines=[
    AlignedLine(content="x^2 + y^2 &= r^2", annotation="def"),
    AlignedLine(content="&= 1", annotation=""),
])
full = block.to_full_latex()
print("AlignedBlock:", repr(full))

cases = CasesBlock(cases=[
    ("f(x)", "x > 0"),
    ("0", r"x \leq 0"),
])
full = cases.to_full_latex()
print("CasesBlock:", repr(full))

proof = ProofIR(
    steps=[
        ProofStepIR(before="x^2", after="4", rule="sqrt"),
        ProofStepIR(before="x", after=r"\pm 2", rule="solve"),
    ],
    conclusion=r"x = \pm 2",
)
aligned = proof.to_aligned_block()
full = aligned.to_full_latex()
print("ProofIR:", repr(full))

node = renderer.render_aligned(block)
print("render_aligned type:", node.type)

node = renderer.render_equation("x^2", "4")
print("render_equation type:", node.type)

print("StructuredLatexRenderer tests done!")
