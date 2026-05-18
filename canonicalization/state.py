"""
State Canonicalization — 数学状态规范化 Pipeline

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  canonicalize_state() 是整个规范化系统的入口。

  Pipeline:
    ┌───────────────────────────┐
    │  Raw MathState            │
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  1. Expression Canonical. │  展开标准化 + 项排序
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  2. Constraint Canonical. │  符号统一 + 方向统一 + 去重
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  3. Variable Renaming     │  统一变量命名（可选）
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  4. Structural Sorting    │  表达式/约束/假设排序
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  5. Semantic Compression  │  等价项合并 + 冗余删除
    └────────────┬──────────────┘
                 │
    ┌────────────▼──────────────┐
    │  Canonical MathState      │
    └───────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from canonicalization.expression import (
    canonicalize_expression,
    CanonicalForm,
    expressions_are_equivalent,
)
from canonicalization.constraints import (
    canonicalize_constraint,
    canonicalize_constraint_set,
    constraints_are_equivalent,
)
from canonicalization.fingerprint import state_fingerprint


@dataclass(frozen=True)
class CanonicalizationResult:
    original_fingerprint: str
    canonical_fingerprint: str
    expressions_changed: bool
    constraints_changed: bool
    expressions_removed: int
    constraints_removed: int
    equivalent: bool


def canonicalize_state(
    expressions: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
    assumptions: tuple[str, ...] = (),
    variable_scope: tuple[str, ...] = (),
    form: CanonicalForm = CanonicalForm.EXPANDED,
) -> dict:
    """
    执行完整的数学状态规范化 Pipeline。

    Returns:
        dict 包含规范化后的各组件和元信息

    Example:
        >>> result = canonicalize_state(
        ...     expressions=("x^2 - 1",),
        ...     constraints=("x > 0", "0 < x"),
        ... )
        >>> result['expressions']
        ('x**2 - 1',)
        >>> result['constraints']
        ('x > 0',)  # 去重
    """
    original_fp = state_fingerprint(expressions, constraints, assumptions, variable_scope)

    canon_exprs = _canonicalize_expressions(expressions, form)
    canon_constraints = _canonicalize_constraints(constraints)
    canon_assumptions = _canonicalize_assumptions(assumptions)
    canon_vars = _canonicalize_variables(variable_scope)

    canon_exprs = _remove_duplicate_expressions(canon_exprs)
    canon_constraints = _remove_duplicate_constraints(canon_constraints)

    canon_exprs = tuple(sorted(canon_exprs))
    canon_constraints = tuple(sorted(canon_constraints))
    canon_assumptions = tuple(sorted(canon_assumptions))
    canon_vars = tuple(sorted(canon_vars))

    canonical_fp = state_fingerprint(canon_exprs, canon_constraints, canon_assumptions, canon_vars)

    return {
        'expressions': canon_exprs,
        'constraints': canon_constraints,
        'assumptions': canon_assumptions,
        'variable_scope': canon_vars,
        'original_fingerprint': original_fp,
        'canonical_fingerprint': canonical_fp,
        'changed': original_fp != canonical_fp,
    }


def _canonicalize_expressions(
    expressions: tuple[str, ...],
    form: CanonicalForm,
) -> list[str]:
    """规范化所有表达式。"""
    result = []
    for expr in expressions:
        canon = canonicalize_expression(expr, form)
        result.append(canon)
    return result


def _canonicalize_constraints(constraints: tuple[str, ...]) -> list[str]:
    """规范化所有约束。"""
    return canonicalize_constraint_set(list(constraints))


def _canonicalize_assumptions(assumptions: tuple[str, ...]) -> list[str]:
    """规范化假设（简单去空格 + 排序）。"""
    return [a.strip() for a in assumptions if a.strip()]


def _canonicalize_variables(variable_scope: tuple[str, ...]) -> list[str]:
    """规范化变量作用域。"""
    return [v.strip() for v in variable_scope if v.strip()]


def _remove_duplicate_expressions(expressions: list[str]) -> list[str]:
    """去除语义重复的表达式。"""
    seen = []
    result = []
    for expr in expressions:
        is_dup = False
        for existing in seen:
            if expressions_are_equivalent(expr, existing):
                is_dup = True
                break
        if not is_dup:
            seen.append(expr)
            result.append(expr)
    return result


def _remove_duplicate_constraints(constraints: list[str]) -> list[str]:
    """去除语义重复的约束。"""
    seen = []
    result = []
    for c in constraints:
        is_dup = False
        for existing in seen:
            if constraints_are_equivalent(c, existing):
                is_dup = True
                break
        if not is_dup:
            seen.append(c)
            result.append(c)
    return result
