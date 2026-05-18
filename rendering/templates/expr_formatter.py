"""
ExprFormatter — 表达式格式化器

═══════════════════════════════════════════════════════════════
职责
═══════════════════════════════════════════════════════════════

  将原始 LaTeX / 文本表达式格式化为人类友好的显示形式。

  功能:
    1. 清理 LaTeX 命令 (\\frac → 分数, \\sqrt → 根号, ...)
    2. 格式化约束条件 (x ≠ 0, x > 0, ...)
    3. 格式化等式关系 (lhs = rhs)
    4. 提取操作变量 (对 x 求导, 关于 y 的偏导)
    5. 提取代入点 (代入 x = 3)
    6. 提取公因子 (约去 x-1)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from typing import Optional


_LATEX_SYMBOL_MAP = {
    r"\frac": "",
    r"\sqrt": "√",
    r"\cdot": "·",
    r"\times": "×",
    r"\div": "÷",
    r"\neq": "≠",
    r"\leq": "≤",
    r"\geq": "≥",
    r"\approx": "≈",
    r"\equiv": "≡",
    r"\infty": "∞",
    r"\partial": "∂",
    r"\nabla": "∇",
    r"\forall": "∀",
    r"\exists": "∃",
    r"\in": "∈",
    r"\notin": "∉",
    r"\subset": "⊂",
    r"\supset": "⊃",
    r"\cup": "∪",
    r"\cap": "∩",
    r"\emptyset": "∅",
    r"\lambda": "λ",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\sigma": "σ",
    r"\omega": "ω",
    r"\phi": "φ",
    r"\psi": "ψ",
    r"\sum": "Σ",
    r"\prod": "Π",
    r"\int": "∫",
    r"\lim": "lim",
    r"\sin": "sin",
    r"\cos": "cos",
    r"\tan": "tan",
    r"\ln": "ln",
    r"\log": "log",
    r"\exp": "exp",
    r"\det": "det",
    r"\dim": "dim",
    r"\rank": "rank",
    r"\tr": "tr",
    r"\left": "",
    r"\right": "",
    r"\big": "",
    r"\Big": "",
    r"\bigg": "",
    r"\Bigg": "",
}

_STRIP_COMMANDS = {
    r"\displaystyle",
    r"\textstyle",
    r"\scriptstyle",
    r"\mathbb",
    r"\mathbf",
    r"\mathit",
    r"\mathrm",
    r"\mathcal",
    r"\mathfrak",
    r"\text",
    r"\mathrm",
}


class ExprFormatter:
    """
    表达式格式化器 — 将 LaTeX / 文本转为人类友好显示。

    用法:
      fmt = ExprFormatter()
      fmt.format_expr(r"\\frac{x^2-1}{x-1}")  → "分数 (x²-1)/(x-1)"
      fmt.format_constraint("x ≠ 0")            → "x ≠ 0"
      fmt.format_equation("f(x)", "2x+3")       → "f(x) = 2x+3"
    """

    def format_expr(self, expr: str) -> str:
        if not expr:
            return ""
        result = expr.strip()
        result = self._strip_latex_wrapper(result)
        result = self._replace_symbols(result)
        result = self._clean_superscripts(result)
        result = self._clean_subscripts(result)
        result = self._clean_braces(result)
        result = self._normalize_spaces(result)
        return result

    def format_constraint(self, constraint: str) -> str:
        if not constraint:
            return ""
        result = self.format_expr(constraint)
        if result and not any(op in result for op in ["≠", "≤", "≥", ">", "<", "∈", "∉"]):
            result = f"{result} ≠ 0"
        return result

    def format_equation(self, lhs: str, rhs: str) -> str:
        lhs_fmt = self.format_expr(lhs)
        rhs_fmt = self.format_expr(rhs)
        if not lhs_fmt:
            return rhs_fmt
        if not rhs_fmt:
            return lhs_fmt
        return f"{lhs_fmt} = {rhs_fmt}"

    def extract_variable(self, expr: str) -> str:
        if not expr:
            return ""
        m = re.search(r'[dD]/d([a-zA-Z])', expr)
        if m:
            return m.group(1)
        m = re.search(r'\\partial.*?/\\partial\s*([a-zA-Z])', expr)
        if m:
            return m.group(1)
        m = re.search(r"对\s*([a-zA-Z])\s*求导", expr)
        if m:
            return m.group(1)
        m = re.search(r"关于\s*([a-zA-Z])\s*的偏导", expr)
        if m:
            return m.group(1)
        m = re.search(r"关于\s*([a-zA-Z])\s*求", expr)
        if m:
            return m.group(1)
        return ""

    def extract_point(self, expr: str) -> str:
        if not expr:
            return ""
        m = re.search(r'[a-zA-Z]\s*=\s*([0-9\.\-]+)', expr)
        if m:
            return m.group(0)
        m = re.search(r'代入\s*([a-zA-Z]\s*=\s*[0-9\.\-]+)', expr)
        if m:
            return m.group(1)
        m = re.search(r'at\s+([a-zA-Z]\s*=\s*[0-9\.\-]+)', expr, re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    def extract_factor(self, input_expr: str, output_expr: str) -> str:
        if not input_expr or not output_expr:
            return ""
        in_clean = self.format_expr(input_expr)
        out_clean = self.format_expr(output_expr)
        m = re.search(r'\(([^)]+)\)', in_clean)
        if m:
            factor = m.group(1)
            if factor not in out_clean:
                return factor
        return ""

    def _strip_latex_wrapper(self, expr: str) -> str:
        for wrapper in ["$$", "$", "\\[", "\\]", "\\(", "\\)"]:
            expr = expr.replace(wrapper, "")
        expr = expr.strip()
        if expr.startswith("\\begin{") and "}" in expr:
            end_tag = expr[: expr.index("}") + 1]
            end_env = end_tag.replace("\\begin", "\\end")
            expr = expr.replace(end_tag, "").replace(end_env, "")
        return expr.strip()

    def _replace_symbols(self, expr: str) -> str:
        import re
        
        # ═══════════════════════════════════════════════
        # 关键修复：防止语义替换污染 LaTeX 命令
        # 问题：\sin x → \s ∈ x（\in 替换误伤 \sin）
        # 解决方案：使用正则表达式添加边界保护
        # ═══════════════════════════════════════════════
        
        for latex, readable in sorted(_LATEX_SYMBOL_MAP.items(), key=lambda x: -len(x[0])):
            # 对于 LaTeX 命令（以 \ 开头），使用负向后瞻确保前面不是 \
            # 使用负向前瞻确保后面不是字母（避免匹配更长的命令）
            if latex.startswith('\\'):
                # 命令名称（去掉 \）
                cmd_name = latex[1:]
                # 构建正则表达式：前面不是 \，后面不是字母
                pattern = re.compile(r'(?<!\\)' + re.escape(latex) + r'(?![a-zA-Z])')
                expr = pattern.sub(readable, expr)
            else:
                expr = expr.replace(latex, readable)
        
        for cmd in _STRIP_COMMANDS:
            if cmd.startswith('\\'):
                cmd_name = cmd[1:]
                pattern = re.compile(r'(?<!\\)' + re.escape(cmd) + r'(?![a-zA-Z])')
                expr = pattern.sub('', expr)
            else:
                expr = expr.replace(cmd, '')
        
        return expr

    def _clean_superscripts(self, expr: str) -> str:
        def _replace_sup(m):
            base = m.group(1)
            exp = m.group(2).strip()
            sup_map = {
                "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
                "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
                "n": "ⁿ",
            }
            if exp in sup_map:
                return f"{base}{sup_map[exp]}"
            return f"{base}^{exp}"

        expr = re.sub(r'(\w)\^{(\w)}', _replace_sup, expr)
        expr = re.sub(r'(\w)\^(\d)', _replace_sup, expr)
        return expr

    def _clean_subscripts(self, expr: str) -> str:
        def _replace_sub(m):
            base = m.group(1)
            sub = m.group(2).strip()
            sub_map = {
                "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
                "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
                "i": "ᵢ", "j": "ⱼ", "k": "ₖ",
            }
            if sub in sub_map:
                return f"{base}{sub_map[sub]}"
            return f"{base}_{sub}"

        expr = re.sub(r'(\w)_{(\w)}', _replace_sub, expr)
        return expr

    def _clean_braces(self, expr: str) -> str:
        # ═══════════════════════════════════════════════
        # 关键修复：保留上标/下标中的花括号
        # 问题：e^{*2} → e^*2（花括号被错误移除）
        # 解决方案：
        # 1. 先保护 ^_ 后面的花括号内容
        # 2. 然后移除其他花括号
        # 3. 最后恢复保护的内容
        # ═══════════════════════════════════════════════
        
        # 步骤1：保护上标/下标中的花括号内容
        protected = {}
        temp_expr = expr
        count = 0
        
        # 匹配 ^或_ 后面的花括号内容
        sup_sub_pattern = re.compile(r'([\^_])\{([^{}]*)\}')
        matches = list(sup_sub_pattern.finditer(temp_expr))
        
        for match in reversed(matches):
            full_match = match.group(0)  # 如 ^{*2}
            placeholder = f'\x00SUBSUB{count}\x00'
            temp_expr = temp_expr[:match.start()] + placeholder + temp_expr[match.end():]
            protected[placeholder] = full_match
            count += 1
        
        # 步骤2：移除其他地方的花括号
        temp_expr = re.sub(r'\{([^{}]*)\}', r'\1', temp_expr)
        
        # 步骤3：恢复上标/下标中的花括号内容
        for placeholder, original in protected.items():
            temp_expr = temp_expr.replace(placeholder, original)
        
        return temp_expr

    def _normalize_spaces(self, expr: str) -> str:
        expr = re.sub(r'\s+', ' ', expr)
        expr = expr.strip()
        expr = re.sub(r'\s*=\s*', ' = ', expr)
        expr = re.sub(r'\s*\+\s*', ' + ', expr)
        expr = re.sub(r'\s*-\s*(?!\d)', ' - ', expr)
        expr = re.sub(r'\s*,\s*', ', ', expr)
        return expr


_default_formatter = ExprFormatter()


def format_expr(expr: str) -> str:
    return _default_formatter.format_expr(expr)


def format_constraint(constraint: str) -> str:
    return _default_formatter.format_constraint(constraint)


def format_equation(lhs: str, rhs: str) -> str:
    return _default_formatter.format_equation(lhs, rhs)
