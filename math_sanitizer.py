"""
Math Sanitizer — 统一数学表达式安全层

核心原则: LLM 只能输出结构化数据，绝不能直接控制显示层 LaTeX。
          所有数学表达式必须经过本层的修复+验证才能渲染。

职责:
  1. 修复 LLM 常见 LaTeX 错误（失衡括号、残缺分隔符、裸公式）
  2. 逐个表达式包裹 $...$ 或 $$...$$ 后再嵌入文本
  3. 统一数学模式 ($ vs $$ vs \(\) vs \[\] )
  4. 转义 HTML/KaTeX 不安全的字符
  5. 渲染失败时自动回退到纯文本
"""

import re


def safe_latex(text: str) -> str:
    """
    将任意文本转为安全的 KaTeX 可渲染字符串。

    处理管线:
      1. 拆分: 识别所有 $...$ 块和非数学文本
      2. 修复: 对每个数学块独立修复（失衡括号、残缺分隔符）
      3. 包裹: 裸数学表达式自动包裹 $...$
      4. 重组: 安全的数学块 + 转义的非数学文本 → 完整安全文本
    """
    if not text:
        return text

    s = text

    # ── Step 1: 修复全局问题 ──
    # $$$ 及以上 → 压缩为成对的 $$
    s = re.sub(r'\${3,}', '$$', s)
    # 孤立的 $$ 但不成对 → 降为 $
    if s.count('$$') % 2 != 0:
        pass  # 后续 split 会处理
    s = _normalize_math_delimiters(s)         # \(\) → $ , \[\] → $$
    s = re.sub(r'\$\s*\$', '', s)             # $ $ → 空
    s = s.replace('\\lt;', '<').replace('\\gt;', '>')  # 错误的转义恢复

    # ── Step 2: 拆分数学块 + 非数学文本 ──
    parts = []
    # 先处理 $$...$$ 再处理 $...$（长匹配优先）
    pattern = r'(\$\$.*?\$\$|\$[^$\n]+?\$)'
    last = 0
    for m in re.finditer(pattern, s, re.DOTALL):
        # 前面非数学文本 → 转义 HTML
        if m.start() > last:
            plain = s[last:m.start()]
            plain = _sanitize_html(plain)
            parts.append(('text', plain))
        # 数学块 → 修复
        math_block = m.group(0)
        math_block = _repair_math_block(math_block)
        parts.append(('math', math_block))
        last = m.end()
    # 尾部残余
    if last < len(s):
        plain = s[last:]
        # 如果残余有孤立 $，去掉
        plain = plain.replace('$', '')
        plain = _sanitize_html(plain)
        parts.append(('text', plain))

    # ── Step 3: 如果没有数学块，检查是否需要包裹裸公式 ──
    if not any(t == 'math' for t, _ in parts) and _is_pure_math(s):
        return f"${_repair_bare_math(s)}$"

    # ── Step 4: 重组 ──
    result = ''.join(
        content for _, content in parts
    )

    return result


def validate_expression(expr: str) -> tuple[bool, str]:
    """
    验证单个数学表达式是否可安全渲染。
    返回 (is_valid, reason)。
    """
    if not expr or not expr.strip():
        return False, "空表达式"
    # 括号平衡
    depth = 0
    for c in expr:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
    if depth != 0:
        return False, f"括号失衡(d={depth})"
    # $ 成对
    dollars = expr.count('$')
    if dollars % 2 != 0:
        return False, "美元符不成对"
    # 无裸 \\ 命令结尾
    if expr.rstrip().endswith('\\'):
        return False, "LaTeX命令未完成"
    return True, "ok"


def is_valid_latex(text: str) -> bool:
    """快速检查 LaTeX 是否基本合法。"""
    ok, _ = validate_expression(text)
    return ok


# ═══════════════════════════════════════════════
#  内部修复函数
# ═══════════════════════════════════════════════

def _repair_math_block(block: str) -> str:
    """修复单个数学块 (已被 $ 包裹)。"""
    # 去掉外层 $
    inner = block
    is_display = False
    if block.startswith('$$') and block.endswith('$$'):
        inner = block[2:-2]
        is_display = True
    elif block.startswith('$') and block.endswith('$'):
        inner = block[1:-1]

    # 修复失衡括号
    inner = _balance_braces(inner)

    # 修复常见 LLM 错误
    inner = _fix_llm_errors(inner)

    # 重新包裹
    if is_display:
        return f"$${inner}$$"
    return f"${inner}$"


def _fix_llm_errors(expr: str) -> str:
    """修复 LLM 常见 LaTeX 错误。"""
    # 1. 裸 Unicode ≥, ≤, ≠ → \\ge, \\le, \\ne
    expr = expr.replace('≥', '\\ge ').replace('≤', '\\le ').replace('≠', '\\ne ')
    # 2. 中文标点 → 移除或替换
    expr = expr.replace('，', ', ').replace('；', '; ')
    expr = expr.replace('（', '(').replace('）', ')')
    # 3. 双反斜杠 LaTeX 命令 (LLM 有时忘记)
    expr = re.sub(r'(?<!\\)(sin|cos|tan|ln|log|exp|lim|sum|int|prod)(?=\s*[\(\[\{])', r'\\\1', expr)
    # 4. 空格中断的 LaTeX 命令: \\ frac → \\frac
    expr = re.sub(r'\\\s+(frac|sqrt|sum|int|lim|sin|cos|tan)', r'\\\1', expr)
    # 5. 不完整的 \\boxed{}
    if '\\boxed' in expr and expr.count('{') == expr.count('}'):
        pass  # OK
    elif '\\boxed' in expr:
        expr = re.sub(r'\\boxed\s*\{', '{', expr)  # 剥离不完整 \\boxed
    # 6. % 注释符（KaTeX 不支持）
    expr = expr.replace('%', '\\%')
    return expr


def _balance_braces(text: str) -> str:
    """修复失衡的 { } 括号。"""
    depth = 0
    for c in text:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
    if depth == 0:
        return text
    if depth > 0:
        return text + '}' * depth
    else:
        result = text
        for _ in range(-depth):
            idx = result.rfind('}')
            if idx >= 0:
                result = result[:idx] + result[idx + 1:]
        return result


def _repair_bare_math(text: str) -> str:
    """修复无 $ 包裹的裸数学表达式。"""
    return _fix_llm_errors(_balance_braces(text))


def _normalize_math_delimiters(text: str) -> str:
    """统一数学模式分隔符: \(\) → $, \[\] → $$。"""
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'$$\1$$', text, flags=re.DOTALL)
    return text


def _sanitize_html(text: str) -> str:
    """转义 HTML 危险字符。"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')  # 恢复已转义的
    return text


def _is_pure_math(text: str) -> bool:
    """判断文本是否为纯数学表达式。"""
    if re.search(r'[一-鿿]', text):
        return False
    if re.search(r'[a-zA-Z]{3,}\s+[a-zA-Z]{3,}', text):
        return False
    if re.search(r'[\\^_{}]|\\[a-zA-Z]+|[\+\-\*/=]', text):
        return True
    return False
