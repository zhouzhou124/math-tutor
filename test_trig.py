"""Test trig function rendering without $ delimiters."""
import sys
sys.path.insert(0, '.')

from latex_normalizer import normalize_latex_style

# Test cases without $ delimiters
test_cases = [
    "2sin x",
    "2cos x",
    "2πsin x",
    "2πcos x",
    "a_1cos x + b_1sin x",
]

print("Testing trig functions without $ delimiters:")
print("=" * 60)
for tc in test_cases:
    normalized = normalize_latex_style(tc)
    print(f"Input:    {tc}")
    print(f"Output:   {normalized}")
    print()

# Test with $ delimiters
print("\n" + "=" * 60)
print("Testing trig functions WITH $ delimiters:")
print("=" * 60)
for tc in test_cases:
    tc_with_dollar = f"${tc}$"
    normalized = normalize_latex_style(tc_with_dollar)
    print(f"Input:    {tc_with_dollar}")
    print(f"Output:   {normalized}")
    print()
