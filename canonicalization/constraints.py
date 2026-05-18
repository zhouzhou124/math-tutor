"""
Constraint Canonicalization — 约束规范化

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  约束的文本表示不唯一：
    x > 0  ≡  0 < x
    x != 0  ≡  x ≠ 0  ≡  0 ≠ x
    x >= 0  ≡  x ≥ 0  ≡  0 ≤ x

  规范化目标：
    1. 符号统一（Unicode 标准化）
    2. 方向统一（变量在左，常数在右）
    3. 排序统一（相同约束集不同顺序 → 同一结果）
    4. 去重（冗余约束删除）
    5. 语义合并（等价约束合并）

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from typing import Optional

try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


_DIRECTION_FLIP = {
    ">": "<",
    "<": ">",
    "≥": "≤",
    "≤": "≥",
    "≠": "≠",
    "=": "=",
}


def canonicalize_constraint(constraint: str) -> str:
    """
    将单个约束规范化为标准形式。

    规则：
      1. 符号统一：!= → ≠, >= → ≥, <= → ≤
      2. 方向统一：0 < x → x > 0
      3. 空格统一
      4. 表达式部分规范化

    Examples:
        >>> canonicalize_constraint("0 < x")
        'x > 0'
        >>> canonicalize_constraint("x != 0")
        'x ≠ 0'
        >>> canonicalize_constraint("0 >= x")
        'x ≤ 0'
    """
    s = constraint.strip()
    s = s.replace("!=", "≠").replace("=/=", "≠")
    s = s.replace(">=", "≥").replace("=>", "≥")
    s = s.replace("<=", "≤").replace("=<", "≤")
    s = re.sub(r'\s+', ' ', s)

    s = _normalize_direction(s)
    s = _normalize_expression_parts(s)

    return s


def canonicalize_constraint_set(constraints: list[str]) -> list[str]:
    """
    规范化约束集：去重 + 排序 + 逐条规范化。

    Examples:
        >>> canonicalize_constraint_set(["x != 0", "0 < x", "x > 0"])
        ['x > 0', 'x ≠ 0']
    """
    canonical = [canonicalize_constraint(c) for c in constraints]
    unique = list(dict.fromkeys(canonical))
    unique.sort()
    return unique


def constraints_are_equivalent(constraint_a: str, constraint_b: str) -> bool:
    """
    判断两个约束是否语义等价。

    策略：
      1. 规范化后文本比较
      2. SymPy 符号验证
    """
    ca = canonicalize_constraint(constraint_a)
    cb = canonicalize_constraint(constraint_b)

    if ca == cb:
        return True

    if _HAS_SYMPY:
        return _sympy_constraint_equiv(ca, cb)

    return False


def _normalize_direction(constraint: str) -> str:
    """
    方向统一：变量在左，常数在右。

    "0 < x" → "x > 0"
    "0 ≥ x" → "x ≤ 0"
    "0 ≠ x" → "x ≠ 0"
    """
    patterns = [
        (r'^0\s*([<>≠=≥≤])\s*(\w+)$', _flip_constraint),
        (r'^(\d+\.?\d*)\s*([<>≥≤])\s*(\w+)$', _flip_numeric_constraint),
    ]

    for pattern, handler in patterns:
        m = re.match(pattern, constraint)
        if m:
            return handler(m)

    return constraint


def _flip_constraint(m: re.Match) -> str:
    op = m.group(1)
    var = m.group(2)
    flipped = _DIRECTION_FLIP.get(op, op)
    return f"{var} {flipped} 0"


def _flip_numeric_constraint(m: re.Match) -> str:
    num = m.group(1)
    op = m.group(2)
    var = m.group(3)
    flipped = _DIRECTION_FLIP.get(op, op)
    return f"{var} {flipped} {num}"


def _normalize_expression_parts(constraint: str) -> str:
    """
    规范化约束中的表达式部分。

    例如：x^2 → x**2（SymPy 格式）
    """
    s = constraint
    s = s.replace('^', '**')
    return s


def _sympy_constraint_equiv(ca: str, cb: str) -> bool:
    """使用 SymPy 验证约束等价。"""
    try:
        rel_ops = {'>', '<', '≥', '≤', '=', '≠'}

        def _parse_constraint(c: str) -> Optional[tuple]:
            for op in ['≥', '≤', '≠', '>', '<', '=']:
                if op in c:
                    parts = c.split(op, 1)
                    if len(parts) == 2:
                        left = sp.sympify(parts[0].strip(), evaluate=True)
                        right = sp.sympify(parts[1].strip(), evaluate=True)
                        return (left, op, right)
            return None

        pa = _parse_constraint(ca)
        pb = _parse_constraint(cb)

        if pa is None or pb is None:
            return False

        la, oa, ra = pa
        lb, ob, rb = pb

        if oa == ob:
            diff_l = sp.expand(la - lb)
            diff_r = sp.expand(ra - rb)
            return diff_l == sp.S.Zero and diff_r == sp.S.Zero

        if oa in ('>', '<') and ob in ('>', '<'):
            if oa != ob:
                diff_l = sp.expand(la - rb)
                diff_r = sp.expand(ra - lb)
                return diff_l == sp.S.Zero and diff_r == sp.S.Zero

        return False

    except Exception:
        return False
