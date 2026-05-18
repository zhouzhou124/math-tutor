import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering.unified_renderer import UnifiedRenderer

renderer = UnifiedRenderer()

print("Test 1: plain text")
tree = renderer.render("plain text")
print("  ->", type(tree).__name__)

print("Test 2: with LaTeX")
tree = renderer.render(r"formula $x^2 + y^2 = r^2$ here")
print("  ->", type(tree).__name__)

print("Test 3: bare LaTeX")
tree = renderer.render(r"compute \frac{1}{2} + \frac{1}{3}")
print("  ->", type(tree).__name__)

print("Test 4: aligned env")
text = r"$$\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}$$"
tree = renderer.render(text)
print("  ->", type(tree).__name__)

print("Test 5: mismatched left/right")
text = r"$$\left( \frac{a}{b}$$"
tree = renderer.render(text)
print("  ->", type(tree).__name__)

print("All UnifiedRenderer tests done!")
