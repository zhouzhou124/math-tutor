import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering.unified_renderer import UnifiedRenderer

renderer = UnifiedRenderer()

tree = renderer.render("plain text")
print("plain text:", type(tree).__name__)

tree = renderer.render(r"formula $x^2 + y^2 = r^2$ here")
print("with LaTeX:", type(tree).__name__)

tree = renderer.render(r"compute \frac{1}{2} + \frac{1}{3}")
print("bare LaTeX:", type(tree).__name__)

text = r"$$\begin{aligned} x &= 1 \\ y &= 2 \end{aligned}$$"
tree = renderer.render(text)
print("aligned env:", type(tree).__name__)

text = r"$\begin{aligned} x &= y \end{aligned}$"
tree = renderer.render(text)
print("inline aligned:", type(tree).__name__)

text = r"$$\left( \frac{a}{b}$$"
tree = renderer.render(text)
print("mismatched left/right:", type(tree).__name__)

print("UnifiedRenderer text mode test done!")
