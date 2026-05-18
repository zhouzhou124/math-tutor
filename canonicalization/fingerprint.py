"""
Semantic Fingerprint — 语义哈希/指纹

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  文本哈希无法识别数学等价：
    hash("x^2 - 1") ≠ hash("(x-1)(x+1)")

  语义哈希基于规范化后的标准形式：
    canonicalize("x^2 - 1") = "x**2 - 1"
    canonicalize("(x-1)(x+1)") = "x**2 - 1"
    → 同一语义哈希！

  用途：
    - Graph Matching: 快速判断两个节点是否等价
    - Diff: 比较两个状态的差异
    - Caching: 相同语义状态复用计算结果
    - Retrieval: 按语义检索历史步骤

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
from typing import Optional

from canonicalization.expression import (
    canonicalize_expression,
    CanonicalForm,
    parse_to_sympy,
)
from canonicalization.constraints import (
    canonicalize_constraint,
    canonicalize_constraint_set,
)


def expression_fingerprint(text: str) -> str:
    """
    计算表达式的语义指纹。

    基于展开形式规范化后取 SHA-256 前 16 位。

    Examples:
        >>> expression_fingerprint("x^2 - 1")
        >>> expression_fingerprint("(x-1)(x+1)")
        # 两者指纹相同
    """
    canonical = canonicalize_expression(text, CanonicalForm.EXPANDED)
    return _hash(canonical)


def expression_fingerprint_multi(text: str) -> dict[str, str]:
    """
    计算表达式的多形式指纹。

    返回展开、因式、简化三种指纹。
    任意一种匹配即视为等价。
    """
    from canonicalization.expression import canonicalize_expression_multi
    multi = canonicalize_expression_multi(text)
    return {form.value: _hash(s) for form, s in multi.items()}


def constraint_fingerprint(constraint: str) -> str:
    """
    计算约束的语义指纹。

    基于规范化后的标准形式。
    """
    canonical = canonicalize_constraint(constraint)
    return _hash(canonical)


def state_fingerprint(
    expressions: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
    assumptions: tuple[str, ...] = (),
    variable_scope: tuple[str, ...] = (),
) -> str:
    """
    计算数学状态的语义指纹。

    对每个组件规范化后组合哈希。
    语义等价的状态产生相同指纹。

    Args:
        expressions: 表达式文本元组
        constraints: 约束文本元组
        assumptions: 假设文本元组
        variable_scope: 变量作用域

    Returns:
        16 字符的语义哈希
    """
    canon_exprs = sorted(
        canonicalize_expression(e, CanonicalForm.EXPANDED) for e in expressions
    )
    canon_constraints = canonicalize_constraint_set(list(constraints))
    canon_assumptions = sorted(assumptions)
    canon_vars = sorted(variable_scope)

    parts = [
        "|".join(canon_exprs),
        "|".join(canon_constraints),
        "|".join(canon_assumptions),
        "|".join(canon_vars),
    ]
    raw = ";;".join(parts)
    return _hash(raw)


def states_are_equivalent(
    state_a_expressions: tuple[str, ...],
    state_a_constraints: tuple[str, ...],
    state_b_expressions: tuple[str, ...],
    state_b_constraints: tuple[str, ...],
) -> bool:
    """
    判断两个数学状态是否语义等价。

    基于：
      1. 语义指纹快速比较
      2. 逐表达式精确比较
    """
    fp_a = state_fingerprint(expressions=state_a_expressions, constraints=state_a_constraints)
    fp_b = state_fingerprint(expressions=state_b_expressions, constraints=state_b_constraints)

    if fp_a == fp_b:
        return True

    from canonicalization.expression import expressions_are_equivalent
    canon_a = sorted(canonicalize_expression(e, CanonicalForm.EXPANDED) for e in state_a_expressions)
    canon_b = sorted(canonicalize_expression(e, CanonicalForm.EXPANDED) for e in state_b_expressions)

    if len(canon_a) != len(canon_b):
        return False

    for ea, eb in zip(canon_a, canon_b):
        if ea != eb:
            if not expressions_are_equivalent(ea, eb):
                return False

    return True


def _hash(text: str) -> str:
    """SHA-256 前 16 位。"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
