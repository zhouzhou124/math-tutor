"""Test trig function rendering fix."""
import sys
sys.path.insert(0, '.')

from latex_normalizer import normalize_latex_style
from question_ast import _extract_stem_and_options

# Test the problematic case from the second screenshot
test_text = "$4.$ 若 $\int_{-\pi}^{\pi} (x - a_1 \cos x - b_1 \sin x)^2 dx = \min\limits_{a,b \in \\mathbf{R}} \\left\\{ \\int_{-\pi}^{\pi} (x - a \\cos x - b \\sin x)^2 dx \\right\\}$，则 $a_1 \\cos x + b_1 \\sin x =$ $( )$ $(A)$ $2\\sin x$ \\qquad$(B)$ $2\\cos x$ \\qquad $(C)$ $2\\pi\\sin x$ \\qquad$(D)$ $2\\pi\\cos x$"

print("Testing trig function rendering fix:")
print("=" * 80)

# Step 1: Normalize the text
normalized = normalize_latex_style(test_text)
print(f"After normalization:\n{normalized}\n")

# Step 2: Parse stem and options
stem, options = _extract_stem_and_options(normalized)

print(f"Extracted Stem:\n{stem}")
print(f"\nExtracted Options:")
for opt in options:
    print(f"  ({opt.label}): {opt.content}")

print("\n" + "=" * 80)
print("Verification:")

# Check options for proper rendering
all_ok = True
for opt in options:
    content = opt.content
    # Check for $ delimiters
    if '$' in content:
        print(f"OK: Option ({opt.label}) has $ delimiters")
    else:
        print(f"FAIL: Option ({opt.label}) missing $ delimiters")
        all_ok = False
    
    # Check for proper trig commands (\sin, \cos)
    if '\\sin' in content or '\\cos' in content:
        print(f"OK: Option ({opt.label}) has proper trig commands")
    else:
        print(f"FAIL: Option ({opt.label}) missing proper trig commands")
        all_ok = False

print("\n" + "=" * 80)
print(f"All checks passed: {all_ok}")
