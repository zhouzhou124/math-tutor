"""Test to trace the duplicate cos/sin issue."""
import sys
sys.path.insert(0, '.')

from latex_normalizer import normalize_latex_style

# Test original input
original = r"$a_1 \cos x + b_1 \sin x$"
print(f"Original: {original}")

# Apply normalization step by step
result = original

# Step 1: _wrap_bare_math_expressions
print("\n1. After _wrap_bare_math_expressions:")
from latex_normalizer import _wrap_bare_math_expressions
result1 = _wrap_bare_math_expressions(result)
print(f"   {result1}")

# Step 2: _normalize_trig_functions  
print("\n2. After _normalize_trig_functions:")
from latex_normalizer import _normalize_trig_functions
result2 = _normalize_trig_functions(result1)
print(f"   {result2}")

# Full normalization
print("\nFull normalization:")
full = normalize_latex_style(original)
print(f"   {full}")

# Test without $ delimiters
print("\n\nTesting WITHOUT $ delimiters:")
original_no_dollar = r"a_1 \cos x + b_1 \sin x"
print(f"Original: {original_no_dollar}")
full_no_dollar = normalize_latex_style(original_no_dollar)
print(f"Normalized: {full_no_dollar}")
