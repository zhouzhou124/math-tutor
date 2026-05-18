import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Step 1: importing UnifiedRenderer...")
from rendering.unified_renderer import UnifiedRenderer
print("Step 2: creating instance...")
renderer = UnifiedRenderer()
print("Step 3: rendering plain text...")
tree = renderer.render("plain text")
print("Step 4: done -", type(tree).__name__)
