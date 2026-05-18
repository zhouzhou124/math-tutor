"""
Transformation Verifier — 数学变换合法性验证器

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学步骤本质是状态变换：

      Input State  →  Transformation  →  Output State

  Transformation Verifier 验证的是"边"是否合法，而非"节点"是否正确。

  区别于 symbolic_executor.py 的"结果等价比较"：
    - symbolic_executor:  "你算出来的结果对不对？"  (答案比对)
    - TransformationVerifier: "这一步变换合不合法？" (推理验证)

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

                  ┌─────────────────┐
                  │ Operation Type  │
                  └────────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   Algebra Verifier             Calculus Verifier
             ▼                           ▼
  Linear Algebra Verifier       Logic Verifier
             ▼                           ▼
         Rule Engine        Constraint Engine
             ▼                           ▼
               Symbolic Equivalence Engine

═══════════════════════════════════════════════════════════════
与 MathIR 的集成
═══════════════════════════════════════════════════════════════

  TransformationVerifier.verify(operation: MathOperation)
      → VerificationResult
      → 更新 MathOperation.legality
      → 生成 ErrorAnnotation（如不合法）
      → 追踪约束变化（lost / introduced / subgoals）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from math_ir import (
    MathState,
    MathOperation,
    MathExpression,
    Legality,
    ErrorSeverity,
    ErrorAnnotation,
    ReasoningStep,
    StepType,
)
from operations import Op, normalize_op

try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


# ══════════════════════════════════════════════════════════════
# 1. ErrorType — 变换错误类型
# ══════════════════════════════════════════════════════════════

class ErrorType(Enum):
    VALID = "valid"
    EQUIVALENCE_BROKEN = "equivalence_broken"
    DOMAIN_CHANGED = "domain_changed"
    CONSTRAINT_LOST = "constraint_lost"
    ASSUMPTION_UNJUSTIFIED = "assumption_unjustified"
    WRONG_OPERATION = "wrong_operation"
    INCOMPLETE_TRANSFORM = "incomplete_transform"
    SIGN_ERROR = "sign_error"
    ARITHMETIC_ERROR = "arithmetic_error"
    RULE_MISAPPLICATION = "rule_misapplication"
    VARIABLE_SCOPE_ERROR = "variable_scope_error"
    DIVISION_BY_ZERO = "division_by_zero"
    BRANCH_MISSING = "branch_missing"
    DIRECTION_ERROR = "direction_error"
    UNKNOWN = "unknown"


# ══════════════════════════════════════════════════════════════
# 2. VerificationResult — 验证结果
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class VerificationResult:
    valid: bool = True
    legality: Legality = Legality.VALID
    confidence: float = 1.0
    error_type: Optional[ErrorType] = None
    violated_constraints: tuple[str, ...] = ()
    introduced_assumptions: tuple[str, ...] = ()
    lost_constraints: tuple[str, ...] = ()
    generated_subgoals: tuple[str, ...] = ()
    explanation: str = ""

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def is_suspect(self) -> bool:
        return self.legality == Legality.SUSPECT

    def to_dict(self) -> dict:
        d = {
            "valid": self.valid,
            "legality": self.legality.value,
            "confidence": self.confidence,
        }
        if self.error_type:
            d["error_type"] = self.error_type.value
        if self.violated_constraints:
            d["violated_constraints"] = list(self.violated_constraints)
        if self.introduced_assumptions:
            d["introduced_assumptions"] = list(self.introduced_assumptions)
        if self.lost_constraints:
            d["lost_constraints"] = list(self.lost_constraints)
        if self.generated_subgoals:
            d["generated_subgoals"] = list(self.generated_subgoals)
        if self.explanation:
            d["explanation"] = self.explanation
        return d

    @classmethod
    def from_dict(cls, d: dict) -> VerificationResult:
        return cls(
            valid=d.get("valid", True),
            legality=Legality(d.get("legality", "valid")),
            confidence=d.get("confidence", 1.0),
            error_type=ErrorType(d["error_type"]) if "error_type" in d and d["error_type"] else None,
            violated_constraints=tuple(d.get("violated_constraints", [])),
            introduced_assumptions=tuple(d.get("introduced_assumptions", [])),
            lost_constraints=tuple(d.get("lost_constraints", [])),
            generated_subgoals=tuple(d.get("generated_subgoals", [])),
            explanation=d.get("explanation", ""),
        )

    @classmethod
    def ok(cls, confidence: float = 1.0, explanation: str = "") -> VerificationResult:
        return cls(valid=True, legality=Legality.VALID, confidence=confidence, explanation=explanation)

    @classmethod
    def suspect(cls, confidence: float = 0.5, explanation: str = "",
                error_type: ErrorType = None,
                introduced_assumptions: tuple = (),
                generated_subgoals: tuple = ()) -> VerificationResult:
        return cls(
            valid=True,
            legality=Legality.SUSPECT,
            confidence=confidence,
            error_type=error_type,
            introduced_assumptions=introduced_assumptions,
            generated_subgoals=generated_subgoals,
            explanation=explanation,
        )

    @classmethod
    def invalid(cls, error_type: ErrorType, explanation: str = "",
                confidence: float = 0.9,
                violated_constraints: tuple = (),
                lost_constraints: tuple = ()) -> VerificationResult:
        return cls(
            valid=False,
            legality=Legality.INVALID,
            confidence=confidence,
            error_type=error_type,
            violated_constraints=violated_constraints,
            lost_constraints=lost_constraints,
            explanation=explanation,
        )

    @classmethod
    def unknown(cls, explanation: str = "") -> VerificationResult:
        return cls(
            valid=True,
            legality=Legality.UNKNOWN,
            confidence=0.0,
            error_type=ErrorType.UNKNOWN,
            explanation=explanation or "无法验证此变换",
        )


# ══════════════════════════════════════════════════════════════
# 3. SymbolicEquivalenceEngine — 符号等价引擎
# ══════════════════════════════════════════════════════════════

class SymbolicEquivalenceEngine:
    """
    验证 input_state 和 output_state 之间的符号等价性。

    分级策略（从快到慢）：
      L1: 字符串规范化比较
      L2: SymPy 数值采样
      L3: SymPy expand/factor
      L4: SymPy simplify（带超时保护）
    """

    @staticmethod
    def _parse(latex_or_text: str) -> Optional['sp.Expr']:
        if not _HAS_SYMPY or not latex_or_text:
            return None
        from symbolic_executor import parse_expression
        return parse_expression(latex_or_text)

    @staticmethod
    def _norm_str(s: str) -> str:
        return re.sub(r'\s+', '', s.lower().replace('$', '').replace('\\', ''))

    def check_equivalence(self, input_expr: str, output_expr: str) -> tuple[bool, float, str]:
        """
        检查两个表达式是否符号等价。

        Returns:
            (equivalent, confidence, method)
        """
        if not input_expr or not output_expr:
            return True, 0.0, "empty"

        if self._norm_str(input_expr) == self._norm_str(output_expr):
            return True, 1.0, "string_norm"

        if not _HAS_SYMPY:
            return True, 0.3, "no_sympy"

        expr_a = self._parse(input_expr)
        expr_b = self._parse(output_expr)

        if expr_a is None or expr_b is None:
            return True, 0.2, "parse_failed"

        diff = expr_a - expr_b

        try:
            import random
            free_vars = list(diff.free_symbols)
            if not free_vars:
                val = abs(float(diff.evalf()))
                if val < 1e-10:
                    return True, 0.95, "constant_eval"
            else:
                all_match = True
                for _ in range(7):
                    subs = {v: random.uniform(-2, 2) for v in free_vars}
                    try:
                        val = abs(float(diff.subs(subs).evalf()))
                        if val > 1e-8:
                            all_match = False
                            break
                    except Exception:
                        all_match = False
                        break
                if all_match:
                    return True, 0.85, "numeric_sample"
        except Exception:
            pass

        try:
            if sp.expand(diff) == 0:
                return True, 0.95, "expand"
        except Exception:
            pass

        try:
            if sp.factor(diff) == 0:
                return True, 0.95, "factor"
        except Exception:
            pass

        try:
            import concurrent.futures as _futures
            with _futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(lambda: sp.simplify(diff))
                result = future.result(timeout=5)
            if result == 0:
                return True, 0.9, "simplify"
        except Exception:
            pass

        return False, 0.9, "not_equivalent"

    def check_expression_in_output(self, input_expr: str, output_expr: str) -> tuple[bool, float, str]:
        """
        检查 input_expr 是否出现在 output_expr 中（子表达式包含关系）。
        用于验证化简、展开等变换。
        """
        if not input_expr or not output_expr:
            return True, 0.3, "empty"

        if self._norm_str(input_expr) == self._norm_str(output_expr):
            return True, 1.0, "identical"

        if not _HAS_SYMPY:
            return True, 0.3, "no_sympy"

        expr_a = self._parse(input_expr)
        expr_b = self._parse(output_expr)

        if expr_a is None or expr_b is None:
            return True, 0.2, "parse_failed"

        diff = expr_a - expr_b
        try:
            if sp.expand(diff) == 0 or sp.simplify(diff) == 0:
                return True, 0.95, "equivalent"
        except Exception:
            pass

        return False, 0.7, "not_contained"


# ══════════════════════════════════════════════════════════════
# 4. ConstraintEngine — 约束追踪引擎
# ══════════════════════════════════════════════════════════════

class ConstraintEngine:
    """
    追踪数学变换中的约束变化。

    职责：
      - 检测丢失的约束（如：开方丢失 x≥0）
      - 检测引入的假设（如：分部积分假设 u,v 可导）
      - 生成子目标（如：换元后需要回代）
    """

    CONSTRAINT_RULES: dict[Op, dict] = {
        Op.SIMPLIFY: {
            "may_lose": [
                ("sqrt(x^2) → x", "x ≥ 0"),
                ("|x| → x", "x ≥ 0"),
                ("x^2/a^2 → (x/a)^2", "a ≠ 0"),
            ],
            "may_introduce": [],
            "subgoals": [],
        },
        Op.CANCEL: {
            "may_lose": [
                ("a/a → 1", "a ≠ 0"),
                ("(x^2-1)/(x-1) → x+1", "x ≠ 1"),
            ],
            "may_introduce": [],
            "subgoals": [],
        },
        Op.INTEGRATE: {
            "may_lose": [],
            "may_introduce": [
                ("分部积分", "u, v 可导"),
                ("换元积分", "换元函数单调可导"),
                ("1/x 积分", "x ≠ 0"),
            ],
            "subgoals": [
                ("换元积分", "回代原变量"),
            ],
        },
        Op.COMPUTE_LIMIT: {
            "may_lose": [],
            "may_introduce": [
                ("洛必达法则", "0/0 或 ∞/∞ 型"),
                ("等价无穷小替换", "极限存在"),
            ],
            "subgoals": [],
        },
        Op.SOLVE_EQUATION: {
            "may_lose": [
                ("两边乘以 x", "x ≠ 0"),
                ("两边开方", "需讨论正负"),
            ],
            "may_introduce": [],
            "subgoals": [
                ("含绝对值方程", "分类讨论"),
                ("含参数方程", "参数讨论"),
            ],
        },
        Op.SOLVE_INEQUALITY: {
            "may_lose": [
                ("两边乘以负数", "不等号方向反转"),
            ],
            "may_introduce": [],
            "subgoals": [
                ("含参数不等式", "参数讨论"),
            ],
        },
        Op.DIFFERENTIATE: {
            "may_lose": [],
            "may_introduce": [
                ("隐函数求导", "F(x,y) 可导"),
                ("参数方程求导", "参数可导且 dx/dt ≠ 0"),
            ],
            "subgoals": [],
        },
        Op.SUBSTITUTE: {
            "may_lose": [],
            "may_introduce": [
                ("三角换元", "换元范围限制"),
            ],
            "subgoals": [
                ("换元", "回代"),
            ],
        },
        Op.ROW_REDUCE: {
            "may_lose": [],
            "may_introduce": [],
            "subgoals": [
                ("行变换", "回代求解"),
            ],
        },
        Op.CLASSIFY: {
            "may_lose": [],
            "may_introduce": [],
            "subgoals": [
                ("分类讨论", "需覆盖所有情况"),
                ("分类讨论", "各类互斥"),
            ],
        },
    }

    def analyze(self, operation: MathOperation) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """
        分析操作可能导致的约束变化。

        Returns:
            (lost_constraints, introduced_assumptions, generated_subgoals)
        """
        rules = self.CONSTRAINT_RULES.get(operation.op_type)
        if not rules:
            return (), (), ()

        lost = []
        introduced = []
        subgoals = []

        input_text = " ".join(
            e.latex or e.raw_text for e in operation.input_state.expressions
        )
        output_text = " ".join(
            e.latex or e.raw_text for e in operation.output_state.expressions
        )
        combined = f"{input_text} {operation.reasoning} {operation.goal}".lower()

        for pattern, constraint in rules.get("may_lose", []):
            if self._pattern_matches(pattern, combined):
                if constraint not in operation.input_state.constraints:
                    lost.append(constraint)

        for pattern, assumption in rules.get("may_introduce", []):
            if self._pattern_matches(pattern, combined):
                if assumption not in operation.input_state.assumptions:
                    introduced.append(assumption)

        for pattern, subgoal in rules.get("subgoals", []):
            if self._pattern_matches(pattern, combined):
                subgoals.append(subgoal)

        return tuple(lost), tuple(introduced), tuple(subgoals)

    @staticmethod
    def _pattern_matches(pattern: str, text: str) -> bool:
        p = pattern.lower()
        keywords = re.split(r'[，,、\s]+', p)
        return any(kw in text for kw in keywords if len(kw) >= 2)


# ══════════════════════════════════════════════════════════════
# 5. AlgebraVerifier — 代数变换验证器
# ══════════════════════════════════════════════════════════════

class AlgebraVerifier:
    """
    验证代数变换的合法性。

    覆盖操作：
      EXPAND, FACTOR, SIMPLIFY, SUBSTITUTE, COLLECT, CANCEL,
      SOLVE_EQUATION, SOLVE_SYSTEM, SOLVE_INEQUALITY
    """

    HANDLED_OPS = {
        Op.EXPAND, Op.FACTOR, Op.SIMPLIFY, Op.SUBSTITUTE,
        Op.COLLECT, Op.CANCEL, Op.SOLVE_EQUATION,
        Op.SOLVE_SYSTEM, Op.SOLVE_INEQUALITY,
    }

    def __init__(self, equiv_engine: SymbolicEquivalenceEngine,
                 constraint_engine: ConstraintEngine):
        self._equiv = equiv_engine
        self._constraints = constraint_engine

    def can_handle(self, op: Op) -> bool:
        return op in self.HANDLED_OPS

    def verify(self, operation: MathOperation) -> VerificationResult:
        op = operation.op_type

        if op in (Op.EXPAND, Op.FACTOR, Op.SIMPLIFY, Op.COLLECT):
            return self._verify_equivalence_transform(operation)

        if op == Op.CANCEL:
            return self._verify_cancel(operation)

        if op == Op.SUBSTITUTE:
            return self._verify_substitute(operation)

        if op in (Op.SOLVE_EQUATION, Op.SOLVE_SYSTEM):
            return self._verify_solve(operation)

        if op == Op.SOLVE_INEQUALITY:
            return self._verify_inequality(operation)

        return VerificationResult.unknown(f"代数验证器未覆盖操作: {op.value}")

    def _verify_equivalence_transform(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        if not input_expr or not output_expr:
            return VerificationResult.ok(confidence=0.5, explanation="缺少表达式，无法验证等价性")

        equiv, conf, method = self._equiv.check_equivalence(input_expr, output_expr)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if equiv:
            if lost:
                return VerificationResult.suspect(
                    confidence=conf * 0.8,
                    explanation=f"变换等价但丢失约束: {', '.join(lost)}",
                    error_type=ErrorType.CONSTRAINT_LOST,
                    introduced_assumptions=introduced,
                    generated_subgoals=subgoals,
                )
            if introduced:
                return VerificationResult.suspect(
                    confidence=conf * 0.9,
                    explanation=f"变换等价但引入假设: {', '.join(introduced)}",
                    error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                    introduced_assumptions=introduced,
                    generated_subgoals=subgoals,
                )
            return VerificationResult.ok(
                confidence=conf,
                explanation=f"代数变换合法 (method={method})",
            )
        else:
            return VerificationResult.invalid(
                error_type=ErrorType.EQUIVALENCE_BROKEN,
                explanation=f"代数变换不等价: {input_expr} → {output_expr}",
                confidence=conf,
                lost_constraints=lost,
            )

    def _verify_cancel(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        if not input_expr or not output_expr:
            return VerificationResult.ok(confidence=0.5, explanation="缺少表达式")

        lost, introduced, subgoals = self._constraints.analyze(operation)

        equiv, conf, method = self._equiv.check_equivalence(input_expr, output_expr)

        if equiv:
            if lost:
                return VerificationResult.suspect(
                    confidence=conf * 0.7,
                    explanation=f"约分等价但需注意约束: {', '.join(lost)}",
                    error_type=ErrorType.CONSTRAINT_LOST,
                    introduced_assumptions=introduced,
                    generated_subgoals=subgoals,
                )
            return VerificationResult.ok(confidence=conf, explanation=f"约分合法 (method={method})")
        else:
            return VerificationResult.invalid(
                error_type=ErrorType.EQUIVALENCE_BROKEN,
                explanation=f"约分不等价: {input_expr} → {output_expr}",
                confidence=conf,
                lost_constraints=lost,
            )

    def _verify_substitute(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if not input_expr or not output_expr:
            return VerificationResult.suspect(
                confidence=0.5,
                explanation="代入操作需人工验证",
                error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                introduced_assumptions=introduced,
                generated_subgoals=subgoals,
            )

        return VerificationResult.suspect(
            confidence=0.7,
            explanation="代入操作通常合法，但需确认换元范围",
            error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
            introduced_assumptions=introduced,
            generated_subgoals=subgoals,
        )

    def _verify_solve(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if not output_expr:
            return VerificationResult.ok(confidence=0.5, explanation="求解步骤缺少输出")

        if subgoals:
            return VerificationResult.suspect(
                confidence=0.7,
                explanation=f"求解需注意子目标: {', '.join(subgoals)}",
                generated_subgoals=subgoals,
                introduced_assumptions=introduced,
            )

        return VerificationResult.ok(confidence=0.8, explanation="求解步骤合法")

    def _verify_inequality(self, operation: MathOperation) -> VerificationResult:
        lost, introduced, subgoals = self._constraints.analyze(operation)

        if lost:
            return VerificationResult.invalid(
                error_type=ErrorType.DIRECTION_ERROR,
                explanation=f"解不等式可能改变方向: {', '.join(lost)}",
                confidence=0.8,
                lost_constraints=lost,
            )

        if subgoals:
            return VerificationResult.suspect(
                confidence=0.7,
                explanation=f"解不等式需注意: {', '.join(subgoals)}",
                generated_subgoals=subgoals,
            )

        return VerificationResult.ok(confidence=0.8, explanation="解不等式步骤合法")

    @staticmethod
    def _extract_latex(state: MathState) -> str:
        if state.expressions:
            return state.expressions[0].latex or state.expressions[0].raw_text
        return ""


# ══════════════════════════════════════════════════════════════
# 6. CalculusVerifier — 微积分变换验证器
# ══════════════════════════════════════════════════════════════

class CalculusVerifier:
    """
    验证微积分变换的合法性。

    覆盖操作：
      DIFFERENTIATE, PARTIAL_DIFF, INTEGRATE, COMPUTE_LIMIT,
      EXPAND_SERIES, SUM_SERIES, CONVERGENCE_TEST
    """

    HANDLED_OPS = {
        Op.DIFFERENTIATE, Op.PARTIAL_DIFF, Op.INTEGRATE,
        Op.COMPUTE_LIMIT, Op.EXPAND_SERIES, Op.SUM_SERIES,
        Op.CONVERGENCE_TEST,
    }

    def __init__(self, equiv_engine: SymbolicEquivalenceEngine,
                 constraint_engine: ConstraintEngine):
        self._equiv = equiv_engine
        self._constraints = constraint_engine

    def can_handle(self, op: Op) -> bool:
        return op in self.HANDLED_OPS

    def verify(self, operation: MathOperation) -> VerificationResult:
        op = operation.op_type

        if op in (Op.DIFFERENTIATE, Op.PARTIAL_DIFF):
            return self._verify_differentiate(operation)

        if op == Op.INTEGRATE:
            return self._verify_integrate(operation)

        if op == Op.COMPUTE_LIMIT:
            return self._verify_limit(operation)

        if op in (Op.EXPAND_SERIES, Op.SUM_SERIES, Op.CONVERGENCE_TEST):
            return self._verify_series(operation)

        return VerificationResult.unknown(f"微积分验证器未覆盖操作: {op.value}")

    def _verify_differentiate(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if not input_expr or not output_expr:
            return VerificationResult.ok(confidence=0.6, explanation="求导步骤缺少表达式")

        if _HAS_SYMPY:
            from symbolic_executor import parse_expression
            expr = parse_expression(input_expr)
            if expr is not None:
                try:
                    expected = sp.diff(expr)
                    student = parse_expression(output_expr)
                    if student is not None:
                        diff = sp.simplify(expected - student)
                        if diff == 0:
                            return VerificationResult.ok(
                                confidence=0.95,
                                explanation="求导结果正确",
                            )
                        else:
                            return VerificationResult.invalid(
                                error_type=ErrorType.RULE_MISAPPLICATION,
                                explanation=f"求导结果不正确: 期望 {expected}, 得到 {student}",
                                confidence=0.9,
                                introduced_assumptions=introduced,
                            )
                except Exception:
                    pass

            equiv, conf, method = self._equiv.check_equivalence(input_expr, output_expr)
            if not equiv:
                return VerificationResult.invalid(
                    error_type=ErrorType.EQUIVALENCE_BROKEN,
                    explanation=f"求导前后不等价: {input_expr} -> {output_expr}",
                    confidence=conf,
                )

        if introduced:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation=f"求导引入假设: {', '.join(introduced)}",
                error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                introduced_assumptions=introduced,
                generated_subgoals=subgoals,
            )

        return VerificationResult.suspect(
            confidence=0.6,
            explanation="无法符号验证求导，需人工确认",
        )

    def _verify_integrate(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if not input_expr or not output_expr:
            return VerificationResult.ok(confidence=0.5, explanation="积分步骤缺少表达式")

        if _HAS_SYMPY:
            from symbolic_executor import parse_expression
            expr = parse_expression(input_expr)
            student = parse_expression(output_expr)
            if expr is not None and student is not None:
                try:
                    expected = sp.integrate(expr)
                    diff = sp.simplify(expected - student)
                    if diff == 0:
                        if subgoals:
                            return VerificationResult.suspect(
                                confidence=0.85,
                                explanation=f"积分结果正确，但需注意: {', '.join(subgoals)}",
                                generated_subgoals=subgoals,
                                introduced_assumptions=introduced,
                            )
                        return VerificationResult.ok(confidence=0.9, explanation="积分结果正确")
                    else:
                        diff_check = sp.diff(student)
                        original_check = sp.simplify(diff_check - expr)
                        if original_check == 0:
                            if subgoals:
                                return VerificationResult.suspect(
                                    confidence=0.85,
                                    explanation="积分结果验证通过（求导还原），但需注意子目标",
                                    generated_subgoals=subgoals,
                                    introduced_assumptions=introduced,
                                )
                            return VerificationResult.ok(
                                confidence=0.9,
                                explanation="积分结果验证通过（求导还原）",
                            )
                        else:
                            return VerificationResult.invalid(
                                error_type=ErrorType.RULE_MISAPPLICATION,
                                explanation="积分结果不正确（求导不还原）",
                                confidence=0.9,
                                introduced_assumptions=introduced,
                            )
                except Exception:
                    pass

        if introduced:
            return VerificationResult.suspect(
                confidence=0.5,
                explanation=f"积分引入假设: {', '.join(introduced)}",
                error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                introduced_assumptions=introduced,
                generated_subgoals=subgoals,
            )

        return VerificationResult.suspect(
            confidence=0.5,
            explanation="无法符号验证积分，需人工确认",
            generated_subgoals=subgoals,
        )

    def _verify_limit(self, operation: MathOperation) -> VerificationResult:
        input_expr = self._extract_latex(operation.input_state)
        output_expr = self._extract_latex(operation.output_state)

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if introduced:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation=f"极限计算引入假设: {', '.join(introduced)}",
                error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                introduced_assumptions=introduced,
                generated_subgoals=subgoals,
            )

        return VerificationResult.suspect(
            confidence=0.6,
            explanation="极限计算需人工验证",
            generated_subgoals=subgoals,
        )

    def _verify_series(self, operation: MathOperation) -> VerificationResult:
        lost, introduced, subgoals = self._constraints.analyze(operation)

        return VerificationResult.suspect(
            confidence=0.5,
            explanation="级数操作需人工验证",
            generated_subgoals=subgoals,
        )

    @staticmethod
    def _extract_latex(state: MathState) -> str:
        if state.expressions:
            return state.expressions[0].latex or state.expressions[0].raw_text
        return ""


# ══════════════════════════════════════════════════════════════
# 7. LinearAlgebraVerifier — 线性代数变换验证器
# ══════════════════════════════════════════════════════════════

class LinearAlgebraVerifier:
    """
    验证线性代数变换的合法性。

    覆盖操作：
      MATRIX_OP, ROW_REDUCE, EIGEN_SOLVE, DETERMINANT,
      ORTHOGONALIZE, QUADRATIC_FORM
    """

    HANDLED_OPS = {
        Op.MATRIX_OP, Op.ROW_REDUCE, Op.EIGEN_SOLVE,
        Op.DETERMINANT, Op.ORTHOGONALIZE, Op.QUADRATIC_FORM,
        Op.CROSS_PRODUCT, Op.DOT_PRODUCT, Op.NORM,
    }

    def __init__(self, equiv_engine: SymbolicEquivalenceEngine,
                 constraint_engine: ConstraintEngine):
        self._equiv = equiv_engine
        self._constraints = constraint_engine

    def can_handle(self, op: Op) -> bool:
        return op in self.HANDLED_OPS

    def verify(self, operation: MathOperation) -> VerificationResult:
        op = operation.op_type

        lost, introduced, subgoals = self._constraints.analyze(operation)

        if op == Op.ROW_REDUCE:
            return VerificationResult.suspect(
                confidence=0.7,
                explanation="行变换保持方程组等价（初等行变换不改变解）",
                generated_subgoals=subgoals,
            )

        if op == Op.DETERMINANT:
            return VerificationResult.suspect(
                confidence=0.7,
                explanation="行列式计算需人工验证",
                generated_subgoals=subgoals,
            )

        if op == Op.EIGEN_SOLVE:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="特征值求解需人工验证",
                generated_subgoals=subgoals,
            )

        if op in (Op.CROSS_PRODUCT, Op.DOT_PRODUCT, Op.NORM):
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="向量运算需人工验证",
            )

        return VerificationResult.suspect(
            confidence=0.5,
            explanation=f"线性代数操作 {op.value} 需人工验证",
            generated_subgoals=subgoals,
        )


# ══════════════════════════════════════════════════════════════
# 8. LogicVerifier — 逻辑/证明变换验证器
# ══════════════════════════════════════════════════════════════

class LogicVerifier:
    """
    验证逻辑/证明类变换的合法性。

    覆盖操作：
      APPLY_THEOREM, CLASSIFY, INDUCTION_STEP, CONTRADICTION
    """

    HANDLED_OPS = {
        Op.APPLY_THEOREM, Op.CLASSIFY, Op.INDUCTION_STEP, Op.CONTRADICTION,
    }

    def __init__(self, constraint_engine: ConstraintEngine):
        self._constraints = constraint_engine

    def can_handle(self, op: Op) -> bool:
        return op in self.HANDLED_OPS

    def verify(self, operation: MathOperation) -> VerificationResult:
        op = operation.op_type
        lost, introduced, subgoals = self._constraints.analyze(operation)

        if op == Op.CLASSIFY:
            if subgoals:
                return VerificationResult.suspect(
                    confidence=0.7,
                    explanation=f"分类讨论需注意: {', '.join(subgoals)}",
                    error_type=ErrorType.BRANCH_MISSING,
                    generated_subgoals=subgoals,
                )
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="分类讨论需验证完备性和互斥性",
                error_type=ErrorType.BRANCH_MISSING,
                generated_subgoals=("需覆盖所有情况", "各类互斥"),
            )

        if op == Op.APPLY_THEOREM:
            if operation.theorem:
                return VerificationResult.suspect(
                    confidence=0.7,
                    explanation=f"应用定理: {operation.theorem}，需验证前提条件",
                    error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
                    introduced_assumptions=introduced or (f"定理 {operation.theorem} 的前提条件",),
                )
            return VerificationResult.suspect(
                confidence=0.5,
                explanation="应用定理但未指定定理名称",
                error_type=ErrorType.ASSUMPTION_UNJUSTIFIED,
            )

        if op == Op.INDUCTION_STEP:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="数学归纳法需验证: 基础步骤 + 归纳步骤",
                generated_subgoals=("验证基础步骤 n=n₀", "假设 n=k 成立", "证明 n=k+1 成立"),
            )

        if op == Op.CONTRADICTION:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="反证法需验证: 假设合理 + 矛盾推导完整",
                introduced_assumptions=("反证假设",),
            )

        return VerificationResult.unknown(f"逻辑验证器未覆盖操作: {op.value}")


# ══════════════════════════════════════════════════════════════
# 9. ProbabilityVerifier — 概率统计变换验证器
# ══════════════════════════════════════════════════════════════

class ProbabilityVerifier:
    """
    验证概率统计变换的合法性。

    覆盖操作：
      PROBABILITY_CALC, EXPECTATION, MLE_DERIVE,
      MOMENT_ESTIMATE, HYPOTHESIS_TEST
    """

    HANDLED_OPS = {
        Op.PROBABILITY_CALC, Op.EXPECTATION, Op.MLE_DERIVE,
        Op.MOMENT_ESTIMATE, Op.HYPOTHESIS_TEST,
    }

    def __init__(self, constraint_engine: ConstraintEngine):
        self._constraints = constraint_engine

    def can_handle(self, op: Op) -> bool:
        return op in self.HANDLED_OPS

    def verify(self, operation: MathOperation) -> VerificationResult:
        op = operation.op_type
        lost, introduced, subgoals = self._constraints.analyze(operation)

        if op == Op.MLE_DERIVE:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="极大似然估计需验证: 似然函数正确 + 对数变换 + 求导=0",
                generated_subgoals=("构造似然函数", "取对数", "求导令其为0", "验证极值"),
            )

        if op == Op.HYPOTHESIS_TEST:
            return VerificationResult.suspect(
                confidence=0.6,
                explanation="假设检验需验证: 原假设/备择假设 + 检验统计量 + 拒绝域",
                generated_subgoals=("建立假设", "选择检验统计量", "确定拒绝域", "做出判断"),
            )

        return VerificationResult.suspect(
            confidence=0.5,
            explanation=f"概率统计操作 {op.value} 需人工验证",
            generated_subgoals=subgoals,
        )


# ══════════════════════════════════════════════════════════════
# 10. TransformationVerifier — 主验证器
# ══════════════════════════════════════════════════════════════

class TransformationVerifier:
    """
    数学变换合法性验证器 — 系统从"答案比对"进入"数学推理验证"的关键组件。

    使用方式:
        verifier = TransformationVerifier()
        result = verifier.verify(operation)

    内部路由:
        1. 根据 op_type 分派到对应域验证器
        2. 域验证器调用规则引擎 + 约束引擎 + 符号等价引擎
        3. 汇总结果，返回 VerificationResult
    """

    def __init__(self):
        self._equiv_engine = SymbolicEquivalenceEngine()
        self._constraint_engine = ConstraintEngine()

        self._algebra = AlgebraVerifier(self._equiv_engine, self._constraint_engine)
        self._calculus = CalculusVerifier(self._equiv_engine, self._constraint_engine)
        self._linalg = LinearAlgebraVerifier(self._equiv_engine, self._constraint_engine)
        self._logic = LogicVerifier(self._constraint_engine)
        self._probability = ProbabilityVerifier(self._constraint_engine)
        self._rule_based = RuleBasedVerifier()

        self._verifiers = [
            self._algebra,
            self._calculus,
            self._linalg,
            self._logic,
            self._probability,
        ]

    def verify(self, operation: MathOperation) -> VerificationResult:
        """
        验证一个数学操作是否合法。

        Args:
            operation: 待验证的数学操作

        Returns:
            VerificationResult 包含合法性、置信度、错误类型、约束变化等
        """
        if operation.op_type in (Op.DEFINE, Op.FINAL_ANSWER, Op.COMPUTE):
            return VerificationResult.ok(
                confidence=0.9,
                explanation=f"通用操作 {operation.op_type.value} 无需变换验证",
            )

        for v in self._verifiers:
            if v.can_handle(operation.op_type):
                result = v.verify(operation)
                rule_result = self._rule_based.verify(operation)
                result = self._merge_results(result, rule_result)
                return self._post_process(result, operation)

        if self._rule_based.can_handle(operation.op_type):
            rule_result = self._rule_based.verify(operation)
            return self._post_process(rule_result, operation)

        return VerificationResult.unknown(
            f"无验证器覆盖操作: {operation.op_type.value}"
        )

    def verify_step(self, step: ReasoningStep) -> VerificationResult:
        """
        验证一个推理步骤中的操作是否合法。

        便捷方法：直接接受 ReasoningStep。
        """
        return self.verify(step.operation)

    def verify_trace(self, trace: 'ReasoningTrace') -> list[tuple[str, VerificationResult]]:
        """
        验证整条推理轨迹中所有操作步骤的合法性。

        Returns:
            [(step_id, VerificationResult), ...]
        """
        results = []
        for step in trace.steps:
            if step.step_type == StepType.OPERATION:
                result = self.verify(step.operation)
                results.append((step.step_id, result))
        return results

    def _post_process(self, result: VerificationResult,
                      operation: MathOperation) -> VerificationResult:
        """
        后处理：补充约束分析结果。
        """
        if result.is_valid and result.legality == Legality.VALID:
            return result

        lost, introduced, subgoals = self._constraint_engine.analyze(operation)

        if not result.lost_constraints and lost:
            return VerificationResult(
                valid=result.valid,
                legality=result.legality,
                confidence=result.confidence,
                error_type=result.error_type,
                violated_constraints=result.violated_constraints,
                introduced_assumptions=result.introduced_assumptions + introduced,
                lost_constraints=result.lost_constraints + lost,
                generated_subgoals=result.generated_subgoals + subgoals,
                explanation=result.explanation,
            )

        return result

    @staticmethod
    def _merge_results(primary: VerificationResult,
                       rule_result: VerificationResult) -> VerificationResult:
        """
        合并传统验证器结果和 Rule DSL 结果。

        策略：
          - 以传统验证器为主
          - Rule DSL 补充约束、假设、子目标
          - 如果 Rule DSL 发现传统验证器未发现的问题，降低置信度
        """
        extra_assumptions = tuple(
            a for a in rule_result.introduced_assumptions
            if a not in primary.introduced_assumptions
        )
        extra_subgoals = tuple(
            s for s in rule_result.generated_subgoals
            if s not in primary.generated_subgoals
        )
        extra_lost = tuple(
            c for c in rule_result.lost_constraints
            if c not in primary.lost_constraints
        )

        if not extra_assumptions and not extra_subgoals and not extra_lost:
            return primary

        confidence = primary.confidence
        if extra_lost:
            confidence *= 0.85
        if extra_assumptions:
            confidence *= 0.9

        legality = primary.legality
        if legality == Legality.VALID and (extra_lost or extra_assumptions):
            legality = Legality.SUSPECT

        return VerificationResult(
            valid=primary.valid,
            legality=legality,
            confidence=confidence,
            error_type=primary.error_type or rule_result.error_type,
            violated_constraints=primary.violated_constraints,
            introduced_assumptions=primary.introduced_assumptions + extra_assumptions,
            lost_constraints=primary.lost_constraints + extra_lost,
            generated_subgoals=primary.generated_subgoals + extra_subgoals,
            explanation=primary.explanation + ("; " + rule_result.explanation if rule_result.explanation else ""),
        )

    def annotate_operation(self, operation: MathOperation) -> tuple[MathOperation, VerificationResult]:
        """
        验证操作并返回带有更新 legality 的新 MathOperation。

        Returns:
            (annotated_operation, verification_result)
        """
        result = self.verify(operation)

        annotated = MathOperation(
            op_type=operation.op_type,
            input_state=operation.input_state,
            output_state=operation.output_state,
            theorem=operation.theorem,
            legality=result.legality,
            goal=operation.goal,
            strategy=operation.strategy,
            reasoning=operation.reasoning,
        )

        return annotated, result

    def annotate_step(self, step: ReasoningStep) -> tuple[ReasoningStep, VerificationResult]:
        """
        验证步骤并返回带有更新 legality 和 error 的新 ReasoningStep。

        Returns:
            (annotated_step, verification_result)
        """
        result = self.verify(step.operation)

        annotated_op = MathOperation(
            op_type=step.operation.op_type,
            input_state=step.operation.input_state,
            output_state=step.operation.output_state,
            theorem=step.operation.theorem,
            legality=result.legality,
            goal=step.operation.goal,
            strategy=step.operation.strategy,
            reasoning=step.operation.reasoning,
        )

        error = step.error
        if not result.is_valid:
            severity_map = {
                ErrorType.EQUIVALENCE_BROKEN: ErrorSeverity.REASONING,
                ErrorType.DOMAIN_CHANGED: ErrorSeverity.REASONING,
                ErrorType.CONSTRAINT_LOST: ErrorSeverity.REASONING,
                ErrorType.ASSUMPTION_UNJUSTIFIED: ErrorSeverity.REASONING,
                ErrorType.WRONG_OPERATION: ErrorSeverity.CONCEPTUAL,
                ErrorType.INCOMPLETE_TRANSFORM: ErrorSeverity.CALCULATION,
                ErrorType.SIGN_ERROR: ErrorSeverity.CALCULATION,
                ErrorType.ARITHMETIC_ERROR: ErrorSeverity.CALCULATION,
                ErrorType.RULE_MISAPPLICATION: ErrorSeverity.CONCEPTUAL,
                ErrorType.VARIABLE_SCOPE_ERROR: ErrorSeverity.CONCEPTUAL,
                ErrorType.DIVISION_BY_ZERO: ErrorSeverity.CONCEPTUAL,
                ErrorType.BRANCH_MISSING: ErrorSeverity.REASONING,
                ErrorType.DIRECTION_ERROR: ErrorSeverity.CONCEPTUAL,
            }
            severity = severity_map.get(result.error_type, ErrorSeverity.REASONING)
            error = ErrorAnnotation(
                severity=severity,
                error_type=result.error_type.value if result.error_type else "",
                description=result.explanation,
                root_cause=result.error_type.value if result.error_type else "",
            )

        annotated_step = ReasoningStep(
            step_id=step.step_id,
            step_type=step.step_type,
            operation=annotated_op,
            label=step.label,
            content=step.content,
            dependencies=step.dependencies,
            weight=step.weight,
            required=step.required,
            alternatives=step.alternatives,
            error=error,
            confidence=min(step.confidence, result.confidence),
            metadata=step.metadata,
        )

        return annotated_step, result


# ══════════════════════════════════════════════════════════════
# 11. RuleBasedVerifier — 基于规则 DSL 的验证器
# ══════════════════════════════════════════════════════════════

class RuleBasedVerifier:
    """
    基于 Rule DSL 的声明式验证器。

    替代硬编码 if/else，使用声明式规则 + Rule Engine 自动：
      - 检查前提条件
      - 生成约束
      - 验证后置条件
      - 生成 proof obligations

    使用方式：
        verifier = RuleBasedVerifier()
        result = verifier.verify(operation)
    """

    def __init__(self, registry: dict = None):
        from rules.engine import RuleEngine
        from rules.registry import RULES
        from rules.dsl import RuleContext

        self._engine = RuleEngine(registry or RULES)
        self._RuleContext = RuleContext

    def can_handle(self, op: Op) -> bool:
        return len(self._engine.rules_for_op(op)) > 0

    def verify(self, operation: MathOperation) -> VerificationResult:
        context = self._RuleContext.from_operation(operation)
        engine_result = self._engine.apply(context)

        return self._to_verification_result(engine_result)

    def _to_verification_result(self, engine_result) -> VerificationResult:
        """将 EngineResult 转换为 VerificationResult。"""
        if engine_result.is_valid:
            return VerificationResult.ok(
                confidence=engine_result.confidence,
                explanation=engine_result.explanation,
            )

        if engine_result.is_suspect:
            mandatory = engine_result.mandatory_obligations
            error_type = ErrorType.ASSUMPTION_UNJUSTIFIED
            if engine_result.may_lose_constraints:
                error_type = ErrorType.CONSTRAINT_LOST
            elif engine_result.may_introduce_assumptions:
                error_type = ErrorType.ASSUMPTION_UNJUSTIFIED
            elif mandatory:
                error_type = ErrorType.BRANCH_MISSING

            return VerificationResult.suspect(
                confidence=engine_result.confidence * 0.8,
                explanation=engine_result.explanation,
                error_type=error_type,
                introduced_assumptions=engine_result.may_introduce_assumptions,
                generated_subgoals=engine_result.generated_subgoals,
            )

        if engine_result.is_invalid:
            error_type = ErrorType.CONSTRAINT_LOST
            if engine_result.failed_preconditions:
                error_type = ErrorType.RULE_MISAPPLICATION

            return VerificationResult.invalid(
                error_type=error_type,
                explanation=engine_result.explanation,
                confidence=engine_result.confidence,
                violated_constraints=engine_result.failed_preconditions,
                lost_constraints=engine_result.may_lose_constraints,
            )

        return VerificationResult.unknown(engine_result.explanation)
