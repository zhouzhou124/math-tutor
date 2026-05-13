"""Test to verify the subscript fix."""
import sys
sys.path.insert(0, '.')

from latex_normalizer import normalize_latex_style
from question_ast import _extract_stem_and_options

# Test the problematic case
test_text = "$4.$ 若 $\int_{-\pi}^{\pi} (x - a_1 \cos x - b_1 \sin x)^2 dx = \min\limits_{a,b \in \\mathbf{R}} \\left\\{ \\int_{-\pi}^{\pi} (x - a \\cos x - b \\sin x)^2 dx \\right\\}$，则 $a_1 \\cos x + b_1 \\sin x =$ $( )$ $(A)$ $2\\sin x$ \\qquad$(B)$ $2\\cos x$ \\qquad $(C)$ $2\\pi\\sin x$ \\qquad$(D)$ $2\\pi\\cos x$"

print("Testing the fix for subscript spacing:")
print("=" * 80)
print(f"Original text:\n{test_text}\n")

# Test normalize_latex_style
normalized = normalize_latex_style(test_text)
print(f"Normalized text:\n{normalized}\n")

# Test parsing
stem, options = _extract_stem_and_options(normalized)

print(f"Extracted Stem:\n{stem}")
print(f"\nExtracted Options:")
for opt in options:
    print(f"  ({opt.label}): {opt.content}")

print("\n" + "=" * 80)
# Check if subscripts are correctly formatted
for opt in options:
    if 'a_1' in opt.content or 'b_1' in opt.content:
        print(f"WARNING: Option ({opt.label}) still has unbraced subscript: {opt.content}")
    else:
        print(f"OK: Option ({opt.label}) subscripts are properly formatted")
