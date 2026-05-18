"""
Implication Rules — 数学约束蕴含规则库

═══════════════════════════════════════════════════════════════
设计思想
═══════════════════════════════════════════════════════════════

  蕴含规则定义约束之间的推导关系。

  每条规则：
    premise: 前提约束（正则匹配）
    conclusions: 可推出的结论列表
    relation: 蕴含关系类型

  规则分类：
    1. 不等式蕴含（x > 0 ⟹ x ≠ 0）
    2. 定义域蕴含（分母 ≠ 0 ⟹ 表达式有定义）
    3. 函数性质蕴含（连续 ⟹ 极限存在）
    4. 等价关系（|x| = x ⟺ x ≥ 0）
    5. 否定关系（x > 0 ⟹ ¬(x < 0)）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from constraints.graph import ConstraintRelation


# ══════════════════════════════════════════════════════════════
# 0. 表达式规范化
# ══════════════════════════════════════════════════════════════

def normalize_constraint(expr: str) -> str:
    """规范化约束表达式，使 ASCII 和 Unicode 符号等价。"""
    s = expr.strip()
    s = s.replace("!=", "≠").replace("=/=", "≠")
    s = s.replace(">=", "≥").replace("=>", "≥")
    s = s.replace("<=", "≤").replace("=<", "≤")
    s = re.sub(r'\s+', ' ', s)
    return s


# ══════════════════════════════════════════════════════════════
# 1. ImplicationRule — 蕴含规则
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ImplicationRule:
    name: str
    premise_pattern: str
    conclusions: tuple[str, ...]
    relation_type: ConstraintRelation = ConstraintRelation.IMPLIES
    priority: int = 0
    domain: str = "general"

    def matches(self, expression: str) -> Optional[dict]:
        norm = normalize_constraint(expression)
        m = re.search(self.premise_pattern, norm, re.IGNORECASE)
        if m:
            return m.groupdict()
        return None

    def apply(self, expression: str, groups: dict) -> list[str]:
        results = []
        for template in self.conclusions:
            try:
                result = template.format(**groups)
                results.append(result)
            except (KeyError, IndexError):
                pass
        return results


# ══════════════════════════════════════════════════════════════
# 2. 内置蕴含规则库
# ══════════════════════════════════════════════════════════════

IMPLICATION_RULES: list[ImplicationRule] = [

    # ── 不等式蕴含 ──
    ImplicationRule(
        name="strict_pos_implies_nonzero",
        premise_pattern=r"^(?P<var>\w+)\s*>\s*0$",
        conclusions=("{var} ≠ 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=10,
        domain="inequality",
    ),
    ImplicationRule(
        name="strict_neg_implies_nonzero",
        premise_pattern=r"^(?P<var>\w+)\s*<\s*0$",
        conclusions=("{var} ≠ 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=10,
        domain="inequality",
    ),
    ImplicationRule(
        name="strict_pos_implies_neg_invalid",
        premise_pattern=r"^(?P<var>\w+)\s*>\s*0$",
        conclusions=("¬({var} < 0)",),
        relation_type=ConstraintRelation.INVALIDATES,
        priority=10,
        domain="inequality",
    ),
    ImplicationRule(
        name="strict_neg_implies_pos_invalid",
        premise_pattern=r"^(?P<var>\w+)\s*<\s*0$",
        conclusions=("¬({var} > 0)",),
        relation_type=ConstraintRelation.INVALIDATES,
        priority=10,
        domain="inequality",
    ),
    ImplicationRule(
        name="nonneg_implies_pos_or_zero",
        premise_pattern=r"^(?P<var>\w+)\s*≥\s*0$",
        conclusions=("{var} ≠ 0", "¬({var} < 0)"),
        relation_type=ConstraintRelation.IMPLIES,
        priority=8,
        domain="inequality",
    ),
    ImplicationRule(
        name="nonpos_implies_neg_or_zero",
        premise_pattern=r"^(?P<var>\w+)\s*≤\s*0$",
        conclusions=("¬({var} > 0)",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=8,
        domain="inequality",
    ),

    # ── 定义域蕴含 ──
    ImplicationRule(
        name="sqrt_requires_nonneg",
        premise_pattern=r"sqrt\((?P<expr>[^)]+)\)\s*有定义",
        conclusions=("{expr} ≥ 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=9,
        domain="domain",
    ),
    ImplicationRule(
        name="division_requires_nonzero",
        premise_pattern=r"分母\s*(?P<var>\w+)\s*≠\s*0",
        conclusions=("{var} ≠ 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=9,
        domain="domain",
    ),
    ImplicationRule(
        name="log_requires_positive",
        premise_pattern=r"log\((?P<expr>[^)]+)\)\s*有定义",
        conclusions=("{expr} > 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=9,
        domain="domain",
    ),
    ImplicationRule(
        name="ln_requires_positive",
        premise_pattern=r"ln\((?P<expr>[^)]+)\)\s*有定义",
        conclusions=("{expr} > 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=9,
        domain="domain",
    ),

    # ── 函数性质蕴含 ──
    ImplicationRule(
        name="differentiable_implies_continuous",
        premise_pattern=r"(?P<func>\w+)\s*可导",
        conclusions=("{func} 连续",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=7,
        domain="calculus",
    ),
    ImplicationRule(
        name="continuous_implies_limit_exists",
        premise_pattern=r"(?P<func>\w+)\s*连续",
        conclusions=("{func} 极限存在",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=6,
        domain="calculus",
    ),

    # ── 等价关系 ──
    ImplicationRule(
        name="abs_x_eq_x_equiv_x_nonneg",
        premise_pattern=r"\|(?P<var>\w+)\|\s*=\s*(?P=var)",
        conclusions=("{var} ≥ 0",),
        relation_type=ConstraintRelation.EQUIVALENT,
        priority=10,
        domain="equivalence",
    ),
    ImplicationRule(
        name="x_squared_pos_implies_x_nonzero",
        premise_pattern=r"^(?P<var>\w+)\^2\s*>\s*0$",
        conclusions=("{var} ≠ 0",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=9,
        domain="inequality",
    ),

    # ── 集合蕴含 ──
    ImplicationRule(
        name="integer_implies_real",
        premise_pattern=r"^(?P<var>\w+)\s*∈\s*Z$",
        conclusions=("{var} ∈ R",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=5,
        domain="set",
    ),
    ImplicationRule(
        name="natural_implies_positive",
        premise_pattern=r"^(?P<var>\w+)\s*∈\s*N$",
        conclusions=("{var} > 0", "{var} ∈ Z",),
        relation_type=ConstraintRelation.IMPLIES,
        priority=5,
        domain="set",
    ),
]


# ══════════════════════════════════════════════════════════════
# 3. 冲突规则 — 直接矛盾对
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConflictRule:
    name: str
    pattern_a: str
    pattern_b: str
    explanation: str

    def check(self, expr_a: str, expr_b: str) -> bool:
        na = normalize_constraint(expr_a)
        nb = normalize_constraint(expr_b)
        ma = re.search(self.pattern_a, na, re.IGNORECASE)
        mb = re.search(self.pattern_b, nb, re.IGNORECASE)
        if ma and mb:
            ga = ma.groupdict()
            gb = mb.groupdict()
            if ga.get("var") and gb.get("var") and ga["var"] == gb["var"]:
                return True
        ma2 = re.search(self.pattern_b, na, re.IGNORECASE)
        mb2 = re.search(self.pattern_a, nb, re.IGNORECASE)
        if ma2 and mb2:
            ga2 = ma2.groupdict()
            gb2 = mb2.groupdict()
            if ga2.get("var") and gb2.get("var") and ga2["var"] == gb2["var"]:
                return True
        return False


CONFLICT_RULES: list[ConflictRule] = [
    ConflictRule(
        name="pos_neg_conflict",
        pattern_a=r"^(?P<var>\w+)\s*>\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*<\s*0$",
        explanation="{var} 不能同时 > 0 和 < 0",
    ),
    ConflictRule(
        name="pos_zero_conflict",
        pattern_a=r"^(?P<var>\w+)\s*>\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*=\s*0$",
        explanation="{var} 不能同时 > 0 和 = 0",
    ),
    ConflictRule(
        name="neg_zero_conflict",
        pattern_a=r"^(?P<var>\w+)\s*<\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*=\s*0$",
        explanation="{var} 不能同时 < 0 和 = 0",
    ),
    ConflictRule(
        name="nonzero_zero_conflict",
        pattern_a=r"^(?P<var>\w+)\s*≠\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*=\s*0$",
        explanation="{var} 不能同时 ≠ 0 和 = 0",
    ),
    ConflictRule(
        name="nonneg_strict_neg_conflict",
        pattern_a=r"^(?P<var>\w+)\s*≥\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*<\s*0$",
        explanation="{var} 不能同时 ≥ 0 和 < 0",
    ),
    ConflictRule(
        name="nonpos_strict_pos_conflict",
        pattern_a=r"^(?P<var>\w+)\s*≤\s*0$",
        pattern_b=r"^(?P<var>\w+)\s*>\s*0$",
        explanation="{var} 不能同时 ≤ 0 和 > 0",
    ),
]


# ══════════════════════════════════════════════════════════════
# 5. 蕴含检测 — A 蕴含 B？
# ══════════════════════════════════════════════════════════════

def check_implication(expr_a: str, expr_b: str) -> bool:
    """
    检查 expr_a 是否蕴含 expr_b。

    使用规则库 + SymPy 符号验证。
    规范化后再比较，使 != 和 ≠ 等价。
    """
    norm_b = normalize_constraint(expr_b)
    for rule in IMPLICATION_RULES:
        if rule.relation_type not in (ConstraintRelation.IMPLIES, ConstraintRelation.EQUIVALENT):
            continue
        groups = rule.matches(expr_a)
        if groups:
            derived = rule.apply(expr_a, groups)
            for d in derived:
                if normalize_constraint(d) == norm_b:
                    return True

    if _check_implication_sympy(expr_a, expr_b):
        return True

    return False


def check_equivalence(expr_a: str, expr_b: str) -> bool:
    """检查两个约束是否等价。"""
    if normalize_constraint(expr_a) == normalize_constraint(expr_b):
        return True

    if check_implication(expr_a, expr_b) and check_implication(expr_b, expr_a):
        return True

    for rule in IMPLICATION_RULES:
        if rule.relation_type != ConstraintRelation.EQUIVALENT:
            continue
        groups_a = rule.matches(expr_a)
        if groups_a:
            derived = rule.apply(expr_a, groups_a)
            for d in derived:
                if normalize_constraint(d) == normalize_constraint(expr_b):
                    return True
        groups_b = rule.matches(expr_b)
        if groups_b:
            derived = rule.apply(expr_b, groups_b)
            for d in derived:
                if normalize_constraint(d) == normalize_constraint(expr_a):
                    return True

    return False


def check_conflict(expr_a: str, expr_b: str) -> Optional[str]:
    """检查两个约束是否冲突。返回冲突说明或 None。"""
    for rule in CONFLICT_RULES:
        if rule.check(expr_a, expr_b):
            ma = re.search(rule.pattern_a, expr_a, re.IGNORECASE)
            if not ma:
                ma = re.search(rule.pattern_b, expr_a, re.IGNORECASE)
            var = ma.groupdict().get("var", "?") if ma else "?"
            return rule.explanation.format(var=var)

    if _check_conflict_sympy(expr_a, expr_b):
        return f"{expr_a} 与 {expr_b} 矛盾"

    return None


def apply_rules(expression: str) -> list[tuple[str, ConstraintRelation, str]]:
    """
    对一个约束表达式应用所有蕴含规则。

    Returns:
        [(derived_expression, relation_type, rule_name), ...]
    """
    results = []
    for rule in IMPLICATION_RULES:
        groups = rule.matches(expression)
        if groups:
            derived = rule.apply(expression, groups)
            for d in derived:
                results.append((d, rule.relation_type, rule.name))
    return results


try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


def _parse_constraint(expr_str: str) -> Optional[tuple]:
    if not _HAS_SYMPY:
        return None
    expr_str = expr_str.strip()
    for op_str, op_fn in [
        (">=", lambda a, b: a >= b), ("<=", lambda a, b: a <= b),
        (">", lambda a, b: a > b), ("<", lambda a, b: a < b),
        ("=", lambda a, b: sp.Eq(a, b)), ("≠", lambda a, b: sp.Ne(a, b)),
    ]:
        parts = expr_str.split(op_str, 1)
        if len(parts) == 2:
            try:
                left = sp.sympify(parts[0].strip())
                right = sp.sympify(parts[1].strip())
                return op_fn(left, right)
            except Exception:
                pass
    return None


def _check_implication_sympy(expr_a: str, expr_b: str) -> bool:
    if not _HAS_SYMPY:
        return False
    try:
        ca = _parse_constraint(expr_a)
        cb = _parse_constraint(expr_b)
        if ca is not None and cb is not None:
            result = sp.ask(cb, assumptions=sp.Q.real(sp.Symbol('x')))
            if result is True:
                return True
    except Exception:
        pass
    return False


def _check_conflict_sympy(expr_a: str, expr_b: str) -> bool:
    if not _HAS_SYMPY:
        return False
    try:
        ca = _parse_constraint(expr_a)
        cb = _parse_constraint(expr_b)
        if ca is not None and cb is not None:
            combined = sp.And(ca, cb)
            if combined == False:
                return True
    except Exception:
        pass
    return False
