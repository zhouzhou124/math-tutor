"""
facts — 事实系统

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学推理的本质: 事实的消耗与生产

    操作 consume facts → 操作 produce facts

  例如: 积分换元

    consume:
      u = g(x)           (DEFINITION)
      g differentiable   (THEOREM)
      dx relation        (DERIVED)

    produce:
      substitution valid (DERIVED)
      Jacobian introduced (DERIVED)
      back substitution obligation (DERIVED)

  之前: constraint/fact/obligation 混在一起
  现在: 三层分离

    ConstraintGraph — 约束 (不等式, 等式条件)
    FactGraph       — 事实 (定理, 定义, 推导结果, 假设)
    Obligations     — 义务 (待证明的命题)

  9 种事实类型:

    CONSTRAINT    — 约束性事实 (x > 0, n ∈ ℕ)
    THEOREM       — 定理 (可导 ⇒ 连续, 介值定理)
    DERIVED       — 推导事实 (x² ≥ 0, f'(x) = 2x)
    ASSUMPTION    — 假设 (设 f 连续, 设 x > 0)
    CASE          — 分类讨论事实 (情况1: x > 0)
    PROVED        — 已证事实 (已证 P(k) ⇒ P(k+1))
    GOAL          — 目标事实 (要证: sqrt(x²) = x)
    DEFINITION    — 定义 (f 连续: ∀ε>0 ∃δ>0 ...)
    DOMAIN        — 定义域事实 (x ∈ ℝ⁺, n ∈ ℕ)

═══════════════════════════════════════════════════════════════
"""

from facts.fact import (
    FactType,
    FactOrigin,
    Fact,
    FactEdge,
    FactEdgeType,
)
from facts.graph import (
    FactGraph,
    FactQuery,
    FactQueryResult,
    ConsumeProduceRecord,
)
from facts.consumer import (
    FactConsumer,
    FactProducer,
    ConsumeSpec,
    ProduceSpec,
    OperationFactFlow,
    ConsumeResult,
    FlowResult,
    BUILTIN_FLOWS,
)

__all__ = [
    "FactType",
    "FactOrigin",
    "Fact",
    "FactEdge",
    "FactEdgeType",
    "FactGraph",
    "FactQuery",
    "FactQueryResult",
    "ConsumeProduceRecord",
    "FactConsumer",
    "FactProducer",
    "ConsumeSpec",
    "ProduceSpec",
    "OperationFactFlow",
    "ConsumeResult",
    "FlowResult",
    "BUILTIN_FLOWS",
]
