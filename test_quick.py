import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering.latex_validator import LaTeXValidator

v = LaTeXValidator()

r = v.validate_and_fix(r"\left( \frac{a}{b}")
print("Test left/right fix:", repr(r.fixed_latex))
print("Is valid:", r.is_valid)

r = v.validate_and_fix(r"\frac{a}{b")
print("Test brace fix:", repr(r.fixed_latex))

r = v.validate_and_fix(r"\begin{aligned} x &= y")
print("Test begin/end fix:", repr(r.fixed_latex))

r = v.validate_and_fix(r"\frac{a}{b} + \sqrt{c}")
print("Test valid LaTeX:", repr(r.fixed_latex), "valid:", r.is_valid)

print("All basic validator tests done!")
