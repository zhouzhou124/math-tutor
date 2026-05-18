"""
Expression Canonicalization — 表达式规范化

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学等价的表达式可能有无数种文本表示：
    x^2 - 1  ≡  (x-1)(x+1)  ≡  (x+1)(x-1)  ≡  -1 + x^2

  Graph Matching 需要一个统一的"标准形式"来判断两个状态是否等价。

  规范化 Pipeline:
    1. Parse: 文本 → SymPy Expr
    2. Expand: 展开为标准多项式形式
    3. Sort: 项排序（SymPy 内置）
    4. Normalize: 系数归一化、符号统一
    5. Serialize: 回到文本

  多策略支持:
    - EXPANDED: 展开形式  a^2+2ab+b^2
    - FACTORED: 因式形式  (a+b)^2
    - SIMPLIFIED: 最简形式

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


class CanonicalForm(Enum):
    EXPANDED = "expanded"
    FACTORED = "factored"
    SIMPLIFIED = "simplified"


def _preprocess(text: str) -> str:
    """将常见数学文本预处理为 SymPy 可解析的形式。"""
    s = text.strip()
    s = s.replace('$', '').replace('$$', '')
    s = s.replace('^', '**')
    s = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', s)
    s = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', s)
    s = re.sub(r'\)\(', ')*(', s)
    s = re.sub(r'(\d)\(', r'\1*(', s)
    s = re.sub(r'\)(\d)', r')*\1', s)
    s = s.replace(r'\frac', '')
    s = s.replace(r'\sqrt', 'sqrt')
    s = s.replace(r'\sin', 'sin').replace(r'\cos', 'cos').replace(r'\tan', 'tan')
    s = s.replace(r'\ln', 'ln').replace(r'\log', 'log')
    s = s.replace(r'\pi', 'pi')
    s = s.replace('{', '(').replace('}', ')')
    s = re.sub(r'\s+', ' ', s)
    return s


def parse_to_sympy(text: str) -> Optional['sp.Expr']:
    """将数学文本解析为 SymPy 表达式。"""
    if not _HAS_SYMPY or not text or not text.strip():
        return None
    s = _preprocess(text)
    try:
        expr = sp.sympify(s, evaluate=True)
        return expr
    except (sp.SympifyError, TypeError, SyntaxError, ValueError):
        return None


def canonicalize_expression(
    text: str,
    form: CanonicalForm = CanonicalForm.EXPANDED,
) -> str:
    """
    将数学表达式规范化为标准形式。

    Args:
        text: 数学表达式文本
        form: 目标规范形式

    Returns:
        规范化后的表达式文本

    Examples:
        >>> canonicalize_expression("(x-1)(x+1)")
        'x**2 - 1'
        >>> canonicalize_expression("b + a")
        'a + b'
        >>> canonicalize_expression("-1 + x**2")
        'x**2 - 1'
    """
    if not text or not text.strip():
        return text.strip()

    expr = parse_to_sympy(text)
    if expr is None:
        return _fallback_canonicalize(text)

    if form == CanonicalForm.EXPANDED:
        canonical = sp.expand(expr)
    elif form == CanonicalForm.FACTORED:
        canonical = sp.factor(expr)
    elif form == CanonicalForm.SIMPLIFIED:
        canonical = sp.simplify(expr)
    else:
        canonical = sp.expand(expr)

    return str(canonical)


def canonicalize_expression_multi(text: str) -> dict[CanonicalForm, str]:
    """
    返回表达式的多种规范形式。

    用于等价判断：如果任一形式匹配，则等价。
    """
    result = {}
    expr = parse_to_sympy(text)
    if expr is None:
        normalized = _fallback_canonicalize(text)
        result[CanonicalForm.EXPANDED] = normalized
        result[CanonicalForm.FACTORED] = normalized
        result[CanonicalForm.SIMPLIFIED] = normalized
        return result

    try:
        result[CanonicalForm.EXPANDED] = str(sp.expand(expr))
    except Exception:
        result[CanonicalForm.EXPANDED] = str(expr)

    try:
        result[CanonicalForm.FACTORED] = str(sp.factor(expr))
    except Exception:
        result[CanonicalForm.FACTORED] = result[CanonicalForm.EXPANDED]

    try:
        result[CanonicalForm.SIMPLIFIED] = str(sp.simplify(expr))
    except Exception:
        result[CanonicalForm.SIMPLIFIED] = result[CanonicalForm.EXPANDED]

    return result


def expressions_are_equivalent(text_a: str, text_b: str) -> bool:
    """
    判断两个表达式是否数学等价。

    策略：
      1. 展开形式比较
      2. 因式形式比较
      3. SymPy 精确等价 (a - b == 0)
      4. 数值采样验证
    """
    if not _HAS_SYMPY:
        return _fallback_canonicalize(text_a) == _fallback_canonicalize(text_b)

    expr_a = parse_to_sympy(text_a)
    expr_b = parse_to_sympy(text_b)

    if expr_a is None or expr_b is None:
        return _fallback_canonicalize(text_a) == _fallback_canonicalize(text_b)

    try:
        diff = sp.expand(expr_a - expr_b)
        if diff == sp.S.Zero:
            return True
    except Exception:
        pass

    try:
        if sp.expand(expr_a) == sp.expand(expr_b):
            return True
    except Exception:
        pass

    try:
        if sp.factor(expr_a) == sp.factor(expr_b):
            return True
    except Exception:
        pass

    return _numeric_equivalence_check(expr_a, expr_b)


def _numeric_equivalence_check(
    expr_a: 'sp.Expr',
    expr_b: 'sp.Expr',
    n_samples: int = 7,
    radius: float = 3.0,
) -> bool:
    """数值采样验证等价性。"""
    import random

    all_vars = list(expr_a.free_symbols | expr_b.free_symbols)
    if not all_vars:
        try:
            return abs(float((expr_a - expr_b).evalf())) < 1e-10
        except Exception:
            return False

    for _ in range(n_samples):
        subs = {v: random.uniform(-radius, radius) for v in all_vars}
        try:
            val_a = float(expr_a.subs(subs).evalf())
            val_b = float(expr_b.subs(subs).evalf())
            if abs(val_a - val_b) > 1e-6 * max(1.0, abs(val_a), abs(val_b)):
                return False
        except Exception:
            continue

    return True


def _fallback_canonicalize(text: str) -> str:
    """
    无 SymPy 时的文本规范化回退方案。

    处理：
      - 空格统一
      - 大小写统一
      - 运算符统一
      - 简单项排序
    """
    s = text.strip()
    s = s.replace('^', '**')
    s = re.sub(r'\s+', ' ', s)

    s = s.replace('!=', '≠').replace('<>', '≠')
    s = s.replace('>=', '≥').replace('=>', '≥')
    s = s.replace('<=', '≤').replace('=<', '≤')

    terms = _split_terms(s)
    terms.sort()
    return ' + '.join(terms)


def _split_terms(text: str) -> list[str]:
    """将表达式拆分为项（简单回退方案）。"""
    s = text.replace('-', '+-')
    parts = [p.strip() for p in s.split('+') if p.strip()]
    return parts
