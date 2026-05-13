"""Test to understand the subscript issue."""
import re

# Test the problematic case
test_text = r"$a_1\cos x + b_1\sin x$"
print(f"Original: {test_text}")

# The issue is that a_1\cos is parsed as a_{1\cos} instead of a_1 \cos

# We need to add space after subscript if followed by a backslash command
pattern = r'_(\d+)(\\[a-zA-Z]+)'
fixed = re.sub(pattern, r'_{\1} \2', test_text)
print(f"Fixed: {fixed}")

# Test more cases
test_cases = [
    r"$a_1\cos x$",
    r"$b_1\sin x$",
    r"$a_1\cos x + b_1\sin x$",
    r"$x_2\tan x$",
]

print("\nTesting various cases:")
for tc in test_cases:
    fixed = re.sub(pattern, r'_{\1} \2', tc)
    print(f"  {tc} -> {fixed}")
