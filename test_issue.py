"""Test to understand the issue with $ delimiters."""
import re

def _has_chinese(content: str) -> bool:
    return any('一' <= c <= '鿿' for c in content)

def _clean(content: str) -> str:
    """Strip $ wrappers while preserving internal math delimiters."""
    c = content.strip()

    has_chinese = _has_chinese(c)
    
    if has_chinese:
        # For mixed text+math content, only strip outer $ wrapper
        # Preserve internal $ delimiters for math expressions
        if c.startswith("$$") and c.endswith("$$"):
            c = c[2:-2].strip()
        elif c.startswith("$") and c.endswith("$") and c.count("$") == 2:
            c = c[1:-1].strip()
        # Keep internal $ as-is for mixed content
    else:
        # For pure math content, strip all $ wrappers
        while c.startswith("$$"):
            c = c[2:].strip()
        while c.endswith("$$"):
            c = c[:-2].strip()
        while c.startswith("$"):
            c = c[1:].strip()
        while c.endswith("$"):
            c = c[:-1].strip()

    # Strip trailing punctuation
    c = re.sub(r"[。；;．]+$", "", c).strip()

    # Fix \frac without braces: \frac12 → \frac{1}{2}
    c = re.sub(r'\\frac(\d)(\d)', r'\\frac{\1}{\2}', c)

    return c

# Test the actual input
test_content = "$(A)$ 当 $f'(x) \ge 0$ 时，$f(x) \ge g(x)$"
print(f"Original: {test_content}")
print(f"Has Chinese: {_has_chinese(test_content)}")
print(f"$ count: {test_content.count('$')}")
cleaned = _clean(test_content)
print(f"Cleaned: {cleaned}")

# Test case where $ is missing at the end
test_content2 = "$(A)$ 当 $f'(x) \ge 0$ 时，$f(x) \ge g(x)"
print(f"\nOriginal2: {test_content2}")
print(f"$ count: {test_content2.count('$')}")
cleaned2 = _clean(test_content2)
print(f"Cleaned2: {cleaned2}")
