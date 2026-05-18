"""
Rule DSL — 数学规则声明语言

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  现在的 Verifier 用 if/else 硬编码规则：

      if op == DIVIDE:
          check divisor != 0

  未来规则会爆炸，维护不了。

  解决方案：声明式规则语言。

  每条规则声明：
    1. 适用于什么操作 (op)
    2. 前提条件 (preconditions)
    3. 变换描述 (transformations)
    4. 后置条件 (postconditions)
    5. 生成的约束 (generated_constraints)
    6. 生成的子目标 (generated_subgoals)
    7. 可能丢失的约束 (may_lose)
    8. 可能引入的假设 (may_introduce)

  Rule Engine 自动：
    - 检查前提
    - 生成约束
    - 验证后置条件
    - 生成 proof obligations

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

from operations import Op


# ══════════════════════════════════════════════════════════════
# 1. Condition — 条件表达式
# ══════════════════════════════════════════════════════════════

class ConditionKind(Enum):
    CONSTRAINT_PRESENT = "constraint_present"
    CONSTRAINT_ABSENT = "constraint_absent"
    EXPRESSION_MATCHES = "expression_matches"
    VARIABLE_IN_SCOPE = "variable_in_scope"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Condition:
    """
    规则条件。

    类型：
      - CONSTRAINT_PRESENT: 约束存在于当前状态
      - CONSTRAINT_ABSENT: 约束不存在于当前状态
      - EXPRESSION_MATCHES: 表达式匹配某个模式
      - VARIABLE_IN_SCOPE: 变量在作用域内
      - CUSTOM: 自定义检查函数
    """
    kind: ConditionKind = ConditionKind.CONSTRAINT_PRESENT
    pattern: str = ""
    description: str = ""
    check_fn: Optional[Callable] = None

    def evaluate(self, context: RuleContext) -> bool:
        """在给定上下文中评估条件。"""
        if self.kind == ConditionKind.CONSTRAINT_PRESENT:
            return self._check_constraint_present(context)
        elif self.kind == ConditionKind.CONSTRAINT_ABSENT:
            return not self._check_constraint_present(context)
        elif self.kind == ConditionKind.EXPRESSION_MATCHES:
            return self._check_expression_matches(context)
        elif self.kind == ConditionKind.VARIABLE_IN_SCOPE:
            return self.pattern in context.variable_scope
        elif self.kind == ConditionKind.CUSTOM:
            if self.check_fn:
                return self.check_fn(context)
            return True
        return True

    def _check_constraint_present(self, context: RuleContext) -> bool:
        from canonicalization.constraints import constraints_are_equivalent
        for c in context.constraints:
            if constraints_are_equivalent(c, self.pattern):
                return True
        return False

    def _check_expression_matches(self, context: RuleContext) -> bool:
        for expr in context.expressions:
            if re.search(self.pattern, expr, re.IGNORECASE):
                return True
        return False


# ══════════════════════════════════════════════════════════════
# 2. RuleContext — 规则执行上下文
# ══════════════════════════════════════════════════════════════

@dataclass
class RuleContext:
    """规则执行时的上下文信息。"""
    op: Op = Op.COMPUTE
    expressions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    variable_scope: tuple[str, ...] = ()
    input_text: str = ""
    output_text: str = ""
    reasoning: str = ""
    goal: str = ""

    @classmethod
    def from_operation(cls, operation) -> RuleContext:
        """从 MathOperation 构建上下文。"""
        input_exprs = tuple(
            e.latex or e.raw_text or ""
            for e in operation.input_state.expressions
        )
        output_exprs = tuple(
            e.latex or e.raw_text or ""
            for e in operation.output_state.expressions
        )
        return cls(
            op=operation.op_type,
            expressions=input_exprs + output_exprs,
            constraints=operation.input_state.constraints,
            assumptions=operation.input_state.assumptions,
            variable_scope=operation.input_state.variable_scope,
            input_text=" ".join(input_exprs),
            output_text=" ".join(output_exprs),
            reasoning=operation.reasoning,
            goal=operation.goal,
        )


# ══════════════════════════════════════════════════════════════
# 3. ProofObligation — 证明义务
# ══════════════════════════════════════════════════════════════

class ObligationSeverity(Enum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class ProofObligation:
    """
    证明义务：规则应用后需要验证的命题。

    例如：
      - "除数不为零" — 必须证明
      - "换元函数单调" — 推荐证明
      - "回代原变量" — 信息提醒
    """
    description: str = ""
    severity: ObligationSeverity = ObligationSeverity.MANDATORY
    related_constraint: str = ""
    related_rule: str = ""

    @property
    def is_mandatory(self) -> bool:
        return self.severity == ObligationSeverity.MANDATORY


# ══════════════════════════════════════════════════════════════
# 4. RuleApplicationResult — 规则应用结果
# ══════════════════════════════════════════════════════════════

@dataclass
class RuleApplicationResult:
    """规则应用的结果。"""
    rule_name: str = ""
    applicable: bool = False
    preconditions_met: bool = True
    failed_preconditions: tuple[str, ...] = ()
    postconditions_met: bool = True
    failed_postconditions: tuple[str, ...] = ()
    generated_constraints: tuple[str, ...] = ()
    generated_subgoals: tuple[str, ...] = ()
    may_lose_constraints: tuple[str, ...] = ()
    may_introduce_assumptions: tuple[str, ...] = ()
    proof_obligations: tuple[ProofObligation, ...] = ()
    confidence: float = 1.0
    explanation: str = ""

    @property
    def is_valid(self) -> bool:
        return self.applicable and self.preconditions_met and self.postconditions_met

    @property
    def has_obligations(self) -> bool:
        return len(self.proof_obligations) > 0

    @property
    def mandatory_obligations(self) -> tuple[ProofObligation, ...]:
        return tuple(o for o in self.proof_obligations if o.is_mandatory)


# ══════════════════════════════════════════════════════════════
# 5. Rule — 核心规则数据结构
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Rule:
    """
    数学变换规则声明。

    声明式描述一条数学变换规则的所有属性：
      - 什么操作 (op)
      - 什么前提下可用 (preconditions)
      - 变换描述 (transformations)
      - 变换后的保证 (postconditions)
      - 变换生成的约束 (generated_constraints)
      - 变换生成的子目标 (generated_subgoals)
      - 可能丢失的约束 (may_lose)
      - 可能引入的假设 (may_introduce)
      - 证明义务 (proof_obligations)

    Example:
        Rule(
            name="divide_nonzero",
            op=Op.COMPUTE,
            description="除法要求除数不为零",
            preconditions=[
                Condition(kind=ConditionKind.CONSTRAINT_PRESENT, pattern="divisor ≠ 0"),
            ],
            generated_constraints=("divisor ≠ 0",),
            proof_obligations=[
                ProofObligation(description="证明除数不为零", severity=ObligationSeverity.MANDATORY),
            ],
        )
    """
    name: str = ""
    op: Op = Op.COMPUTE
    description: str = ""
    domain: str = "general"
    priority: int = 0

    preconditions: tuple[Condition, ...] = ()
    postconditions: tuple[Condition, ...] = ()
    transformations: tuple[str, ...] = ()

    generated_constraints: tuple[str, ...] = ()
    generated_subgoals: tuple[str, ...] = ()
    may_lose: tuple[str, ...] = ()
    may_introduce: tuple[str, ...] = ()

    proof_obligations: tuple[ProofObligation, ...] = ()

    confidence: float = 1.0

    def is_applicable(self, context: RuleContext) -> bool:
        """检查规则是否适用于给定上下文。"""
        if context.op != self.op:
            return False

        for cond in self.preconditions:
            if not cond.evaluate(context):
                return False

        return True

    def apply(self, context: RuleContext) -> RuleApplicationResult:
        """
        应用规则到给定上下文。

        自动：
          1. 检查前提条件
          2. 检查后置条件
          3. 生成约束
          4. 生成子目标
          5. 生成证明义务
        """
        if context.op != self.op:
            return RuleApplicationResult(
                rule_name=self.name,
                applicable=False,
                explanation=f"操作不匹配: 需要 {self.op.value}, 实际 {context.op.value}",
            )

        failed_pre = []
        for cond in self.preconditions:
            if not cond.evaluate(context):
                failed_pre.append(cond.description or cond.pattern)

        failed_post = []
        for cond in self.postconditions:
            if not cond.evaluate(context):
                failed_post.append(cond.description or cond.pattern)

        applicable = len(failed_pre) == 0

        lost = self._compute_lost_constraints(context)
        introduced = self._compute_introduced_assumptions(context)

        obligations = self._generate_obligations(context, failed_pre, lost)

        explanation_parts = []
        if applicable:
            explanation_parts.append(f"规则 '{self.name}' 适用")
        else:
            explanation_parts.append(f"规则 '{self.name}' 前提不满足: {', '.join(failed_pre)}")
        if lost:
            explanation_parts.append(f"可能丢失约束: {', '.join(lost)}")
        if introduced:
            explanation_parts.append(f"可能引入假设: {', '.join(introduced)}")
        if obligations:
            mandatory = [o for o in obligations if o.is_mandatory]
            if mandatory:
                explanation_parts.append(f"必须证明: {', '.join(o.description for o in mandatory)}")

        return RuleApplicationResult(
            rule_name=self.name,
            applicable=applicable,
            preconditions_met=len(failed_pre) == 0,
            failed_preconditions=tuple(failed_pre),
            postconditions_met=len(failed_post) == 0,
            failed_postconditions=tuple(failed_post),
            generated_constraints=self.generated_constraints,
            generated_subgoals=self.generated_subgoals,
            may_lose_constraints=tuple(lost),
            may_introduce_assumptions=tuple(introduced),
            proof_obligations=tuple(obligations),
            confidence=self.confidence if applicable else 0.0,
            explanation="; ".join(explanation_parts),
        )

    def _compute_lost_constraints(self, context: RuleContext) -> list[str]:
        """计算实际丢失的约束。"""
        from canonicalization.constraints import constraints_are_equivalent
        lost = []
        for may_lose_pattern in self.may_lose:
            found = False
            for c in context.constraints:
                if constraints_are_equivalent(c, may_lose_pattern):
                    found = True
                    break
            if not found:
                lost.append(may_lose_pattern)
        return lost

    def _compute_introduced_assumptions(self, context: RuleContext) -> list[str]:
        """计算实际引入的假设。"""
        introduced = []
        for assumption in self.may_introduce:
            if assumption not in context.assumptions:
                introduced.append(assumption)
        return introduced

    def _generate_obligations(
        self,
        context: RuleContext,
        failed_preconditions: list[str],
        lost_constraints: list[str],
    ) -> list[ProofObligation]:
        """生成证明义务。"""
        obligations = list(self.proof_obligations)

        for lost in lost_constraints:
            obligations.append(ProofObligation(
                description=f"证明约束 '{lost}' 在变换中未被违反",
                severity=ObligationSeverity.MANDATORY,
                related_constraint=lost,
                related_rule=self.name,
            ))

        for failed in failed_preconditions:
            obligations.append(ProofObligation(
                description=f"前提条件 '{failed}' 未满足",
                severity=ObligationSeverity.MANDATORY,
                related_rule=self.name,
            ))

        return obligations
