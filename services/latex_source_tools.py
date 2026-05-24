"""LaTeX source normalization & validation for question bank editing.

Cleans user-edited LaTeX source before saving, and warns about common issues.
"""

import re as _re


def normalize_question_latex_source(text: str) -> str:
    """Clean up question LaTeX source before saving to the bank.

    Fixes:
      - Question numbers wrapped in $...$ ($22.$ → 22.)
      - Missing variable in interval (-1\\le 1 → -1\\le x\\le 1)
      - Cases not wrapped in display math
      - Missing space between Chinese and $ delimiters
    """
    if not text:
        return text
    s = str(text).strip()

    # 1. Remove $ from question number: $22.$ → 22.
    s = _re.sub(r'^\$(\d+\s*[.．、])\$', r'\1', s)

    # 2. Fix missing variable in interval: -1\le 1 → -1\le x\le 1
    s = s.replace(r'-1\le 1', r'-1\le x\le 1')
    s = s.replace(r'-1 \le 1', r'-1 \le x \le 1')

    # 3. Cases without display math → wrap in $$
    if r'\begin{cases}' in s and '$$' not in s:
        s = _re.sub(
            r'(\\begin\{cases\}.*?\\end\{cases\})',
            r'$$\n\1\n$$',
            s, flags=_re.DOTALL,
        )

    # 4. Add space between Chinese and $ delimiters
    s = _re.sub(r'([一-鿿])\$', r'\1 $', s)
    s = _re.sub(r'\$([一-鿿])', r'$ \1', s)

    # 5. Normalize blank lines
    s = _re.sub(r'\n{3,}', '\n\n', s)

    return s.strip()


def validate_question_latex_source(text: str) -> list[str]:
    """Return warning messages for common LaTeX source issues."""
    issues = []
    if not text or not text.strip():
        return issues

    s = text.strip()

    if _re.search(r'^\$\d+\s*[.．、]', s):
        issues.append("题号不应放在 $...$ 中，例如请改为 22. 而不是 $22.$")

    dollar_count = s.count('$')
    if dollar_count % 2 != 0:
        issues.append("检测到 $ 数量为奇数，可能存在未闭合的行内公式。")

    if r'\begin{cases}' in s and '$$' not in s:
        issues.append("cases 环境建议使用 $$...$$ 独立包裹。")

    if r'\varphi' in s and '$' not in s:
        issues.append("检测到 LaTeX 命令 \\varphi，但可能没有用 $...$ 包裹。")

    if r'-1\le 1' in s or r'-1 \le 1' in s:
        issues.append("疑似条件缺少变量：-1 \\le 1 应为 -1 \\le x \\le 1。")

    return issues
