"""LaTeX 修复器 — 自动修复 LLM 输出中的破损数学标记"""

import re


def repair_latex_delimiters(text: str) -> str:
    """修复不匹配的 $ 和 $$ 分隔符。

    1. 检测并补全未闭合的 $...$
    2. 检测并补全未闭合的 $$...$$
    3. 修复 $ 与 $$ 混淆的情况
    """
    if not text:
        return text

    s = text

    # 统计 $ 和 $$ 数量
    # 先处理 $$ (display math)
    display_count = s.count("$$")
    if display_count % 2 != 0:
        # 奇数个 $$：在末尾补一个
        s = s.rstrip() + "$$"

    # 移除 $$ 后再统计单 $
    temp = s.replace("$$", "")
    inline_count = temp.count("$")
    if inline_count % 2 != 0:
        # 奇数个 $：在末尾补一个
        s = s.rstrip() + "$"

    return s


def ensure_math_wrap(text: str) -> str:
    """确保所有数学表达式被 $...$ 包裹（用于非标准 LaTeX 输出）。

    检测裸的数学模式标记并包裹。
    重用 latex_normalizer 的 _wrap_bare_math_expressions 逻辑，
    在此基础上补充额外的修复。
    """
    if not text:
        return text

    # 修复1: 括号包裹的数学表达式 — (\frac...) → $(\frac...)$
    s = _wrap_bare_paren_expr(text)

    # 修复2: 独立数学表达式
    s = _wrap_independent_math(s)

    return s


def _wrap_bare_paren_expr(text: str) -> str:
    """包裹用括号括起来的裸数学表达式。"""
    # 保护已存在的 $ 区域
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00P{len(protected)-1}\x00'
    s = re.sub(r'\$\$[^$]+\$\$', _protect, text)
    s = re.sub(r'\$[^$]+\$', _protect, s)

    # 检测常见数学模式: (表达式) 其中表达式含 LaTeX 命令或 ^ _ 等
    # 例如: (ad-bc)^2 → $(ad-bc)^2$
    _MATH_PATTERNS = [
        r'(?<!\$)\('                  # 左括号（前面不是 $）
        r'([a-zA-Z0-9+\-*/=^_{}\\ ]+'  # 数学表达式内容
        r'(?:\\[a-zA-Z]+(?:\{[^}]*\})?'  # 可选 LaTeX 命令
        r'[a-zA-Z0-9+\-*/=^_{}\\ ]*)*)'
        r'\)(?!\$)'                   # 右括号（后面不是 $）
    ]
    for pat in _MATH_PATTERNS:
        s = re.sub(pat, lambda m: f'$({m.group(1)})$', s)

    # 恢复
    for i, block in enumerate(protected):
        s = s.replace(f'\x00P{i}\x00', block)

    return s


def _wrap_independent_math(text: str) -> str:
    """包裹独立的数学表达式（在一行中独占或前后有空格的）。"""
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00I{len(protected)-1}\x00'
    s = re.sub(r'\$\$[^$]+\$\$', _protect, text)
    s = re.sub(r'\$[^$]+\$', _protect, s)

    # 匹配包含 ^ 或 _ 的裸表达式（不在 $ 内）
    s = re.sub(
        r'(?<!\$)(?<!\w)([a-zA-Z]+[\^_]\{[^}]*\}(?:\^\{[^}]*\})?)(?!\w)(?!\$)',
        r'$\1$',
        s,
    )

    # 匹配 \frac{...}{...} 不在 $ 内
    s = re.sub(
        r'(?<!\$)(\\frac\{[^}]*\}\{[^}]*\})(?!\$)',
        r'$\1$',
        s,
    )

    # 匹配 \sum_{}^{}, \int_{}^{} 不在 $ 内
    s = re.sub(
        r'(?<!\$)(\\(?:sum|int|iint|oint|lim)\\limits?[_^]\{[^}]*\}[_^]\{[^}]*\})(?!\$)',
        r'$\1$',
        s,
    )

    # 恢复
    for i, block in enumerate(protected):
        s = s.replace(f'\x00I{i}\x00', block)

    return s


def repair_option_analysis_text(text: str) -> str:
    """专门修复选项分析中的 LaTeX 问题。

    常见问题：
    1. 选项内容截断导致 $ 不闭合
    2. \frac 后面缺参数
    3. 中文混排导致数学模式断裂
    """
    if not text:
        return text

    s = text

    # 闭合未完成的 \frac{...}{
    s = re.sub(r'(\\frac\{[^}]*)\{(?!\})', r'\1', s)  # 移除不完整的第二个参数

    # 闭合孤立的 { 或 }
    open_count = s.count('{') - s.count('\\{')
    close_count = s.count('}') - s.count('\\}')
    if open_count > close_count:
        s += '}' * (open_count - close_count)
    elif close_count > open_count:
        s = '{' * (close_count - open_count) + s

    # 修复 $ 不闭合
    s = repair_latex_delimiters(s)

    return s
