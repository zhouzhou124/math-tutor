"""
Fact — 事实系统核心数据结构

═══════════════════════════════════════════════════════════════
9 种事实类型
═══════════════════════════════════════════════════════════════

  CONSTRAINT  — 约束性事实: x > 0, n ∈ ℕ, f 定义在 [a,b]
  THEOREM     — 定理: 可导⇒连续, 介值定理, 罗尔定理
  DERIVED     — 推导事实: x² ≥ 0, f'(x) = 2x, ∫f = F(b)-F(a)
  ASSUMPTION  — 假设: 设 f 连续, 设 x > 0, 设方程有解
  CASE        — 分类讨论: 情况1: x > 0, 情况2: x = 0
  PROVED      — 已证事实: 已证 P(k)⇒P(k+1), 已证基础步骤
  GOAL        — 目标事实: 要证 sqrt(x²)=x, 要求 ∫f(x)dx
  DEFINITION  — 定义: f连续: ∀ε>0 ∃δ>0 ..., u=g(x) 换元定义
  DOMAIN      — 定义域: x ∈ ℝ⁺, n ∈ ℕ, t ∈ [0,1]

═══════════════════════════════════════════════════════════════
Consume/Produce 模式
═══════════════════════════════════════════════════════════════

  每个操作:
    consume facts → 需要哪些事实作为前提
    produce facts → 产生哪些新事实

  Fact 记录:
    consumed_by — 被哪些操作消耗
    produced_by — 由哪个操作产生

  这样可以:
    1. 追溯: "这个事实从哪来?" → produced_by 链
    2. 影响: "这个事实被谁用?" → consumed_by 链
    3. 失效: 前提事实失效 → 所有 consumed 它的操作的结果都失效

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class FactType(Enum):
    CONSTRAINT = "constraint"
    THEOREM = "theorem"
    DERIVED = "derived"
    ASSUMPTION = "assumption"
    CASE = "case"
    PROVED = "proved"
    GOAL = "goal"
    DEFINITION = "definition"
    DOMAIN = "domain"


class FactOrigin(Enum):
    GIVEN = auto()
    DERIVED = auto()
    COMPUTED = auto()
    INFERRED = auto()
    AXIOM = auto()
    ASSUMED = auto()


class FactEdgeType(Enum):
    DERIVES = "derives"
    IMPLIES = "implies"
    DEPENDS_ON = "depends_on"
    JUSTIFIES = "justifies"
    CONTRADICTS = "contradicts"
    EQUIVALENT = "equivalent"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"


_FACT_TYPE_PRIORITY = {
    FactType.THEOREM: 0,
    FactType.DEFINITION: 1,
    FactType.DOMAIN: 2,
    FactType.CONSTRAINT: 3,
    FactType.ASSUMPTION: 4,
    FactType.PROVED: 5,
    FactType.DERIVED: 6,
    FactType.CASE: 7,
    FactType.GOAL: 8,
}

_FACT_TYPE_STRENGTH = {
    FactType.PROVED: 10,
    FactType.THEOREM: 9,
    FactType.DEFINITION: 8,
    FactType.DOMAIN: 7,
    FactType.CONSTRAINT: 6,
    FactType.DERIVED: 5,
    FactType.ASSUMPTION: 4,
    FactType.CASE: 3,
    FactType.GOAL: 2,
}


@dataclass(frozen=True)
class Fact:
    """
    事实 — 推理链的一等公民。

    升级自 MathFact:
      - fact_type: 9 种事实类型 (替代粗粒度 FactOrigin)
      - consumed_by: 被哪些操作消耗
      - produced_by: 由哪个操作产生
      - scope_label: 作用域标签 (分类讨论分支)
      - retractable: 是否可撤销
      - metadata: 扩展元数据
    """

    expression: str
    fact_type: FactType = FactType.DERIVED
    origin: FactOrigin = FactOrigin.DERIVED
    source_operation: str = ""
    dependencies: tuple[str, ...] = ()
    confidence: float = 1.0
    justification: str = ""
    consumed_by: tuple[str, ...] = ()
    produced_by: str = ""
    scope_label: str = ""
    retractable: bool = False
    timestamp: str = ""
    metadata: dict = None

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        if self.fact_type == FactType.ASSUMPTION and self.origin != FactOrigin.GIVEN:
            object.__setattr__(self, "retractable", True)
        if self.fact_type == FactType.CASE:
            object.__setattr__(self, "retractable", True)

    @property
    def fingerprint(self) -> str:
        raw = f"{self.expression}::{self.fact_type.value}::{self.source_operation}::{':'.join(self.dependencies)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def is_certain(self) -> bool:
        return self.confidence >= 0.95

    @property
    def is_root(self) -> bool:
        return len(self.dependencies) == 0

    @property
    def is_assumed(self) -> bool:
        return self.origin in (FactOrigin.ASSUMED, FactOrigin.GIVEN)

    @property
    def is_proved(self) -> bool:
        return self.fact_type == FactType.PROVED

    @property
    def is_goal(self) -> bool:
        return self.fact_type == FactType.GOAL

    @property
    def is_case(self) -> bool:
        return self.fact_type == FactType.CASE

    @property
    def is_constraint(self) -> bool:
        return self.fact_type == FactType.CONSTRAINT

    @property
    def is_theorem(self) -> bool:
        return self.fact_type == FactType.THEOREM

    @property
    def is_definition(self) -> bool:
        return self.fact_type == FactType.DEFINITION

    @property
    def is_domain(self) -> bool:
        return self.fact_type == FactType.DOMAIN

    @property
    def strength(self) -> int:
        return _FACT_TYPE_STRENGTH.get(self.fact_type, 0)

    @property
    def type_priority(self) -> int:
        return _FACT_TYPE_PRIORITY.get(self.fact_type, 99)

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    @property
    def is_consumed(self) -> bool:
        return len(self.consumed_by) > 0

    @property
    def is_produced(self) -> bool:
        return bool(self.produced_by)

    def with_confidence(self, confidence: float) -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=self.fact_type,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=confidence,
            justification=self.justification,
            consumed_by=self.consumed_by,
            produced_by=self.produced_by,
            scope_label=self.scope_label,
            retractable=self.retractable,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def with_type(self, fact_type: FactType) -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=fact_type,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=self.confidence,
            justification=self.justification,
            consumed_by=self.consumed_by,
            produced_by=self.produced_by,
            scope_label=self.scope_label,
            retractable=self.retractable,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def consume(self, operation: str) -> Fact:
        if operation in self.consumed_by:
            return self
        return Fact(
            expression=self.expression,
            fact_type=self.fact_type,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=self.confidence,
            justification=self.justification,
            consumed_by=self.consumed_by + (operation,),
            produced_by=self.produced_by,
            scope_label=self.scope_label,
            retractable=self.retractable,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def produce(self, operation: str) -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=self.fact_type,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=self.confidence,
            justification=self.justification,
            consumed_by=self.consumed_by,
            produced_by=operation,
            scope_label=self.scope_label,
            retractable=self.retractable,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def invalidate(self, reason: str = "") -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=self.fact_type,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=0.0,
            justification=f"INVALIDATED: {reason}" if reason else "INVALIDATED",
            consumed_by=self.consumed_by,
            produced_by=self.produced_by,
            scope_label=self.scope_label,
            retractable=self.retractable,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def mark_proved(self, proof_method: str = "") -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=FactType.PROVED,
            origin=self.origin,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=1.0,
            justification=proof_method or self.justification,
            consumed_by=self.consumed_by,
            produced_by=self.produced_by,
            scope_label=self.scope_label,
            retractable=False,
            timestamp=self.timestamp,
            metadata=dict(self.metadata) if self.metadata else {},
        )

    def to_dict(self) -> dict:
        d: dict = {
            "expression": self.expression,
            "fingerprint": self.fingerprint,
            "fact_type": self.fact_type.value,
            "origin": self.origin.name,
        }
        if self.source_operation:
            d["source_operation"] = self.source_operation
        if self.dependencies:
            d["dependencies"] = list(self.dependencies)
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        if self.justification:
            d["justification"] = self.justification
        if self.consumed_by:
            d["consumed_by"] = list(self.consumed_by)
        if self.produced_by:
            d["produced_by"] = self.produced_by
        if self.scope_label:
            d["scope_label"] = self.scope_label
        if self.retractable:
            d["retractable"] = True
        if self.timestamp:
            d["timestamp"] = self.timestamp
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Fact:
        return cls(
            expression=d["expression"],
            fact_type=FactType(d.get("fact_type", "derived")),
            origin=FactOrigin[d.get("origin", "DERIVED")],
            source_operation=d.get("source_operation", d.get("source_step", "")),
            dependencies=tuple(d.get("dependencies", ())),
            confidence=d.get("confidence", 1.0),
            justification=d.get("justification", ""),
            consumed_by=tuple(d.get("consumed_by", ())),
            produced_by=d.get("produced_by", ""),
            scope_label=d.get("scope_label", ""),
            retractable=d.get("retractable", False),
            timestamp=d.get("timestamp", ""),
            metadata=d.get("metadata", None),
        )

    @classmethod
    def constraint(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.CONSTRAINT,
                   origin=FactOrigin.GIVEN, **kwargs)

    @classmethod
    def theorem(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.THEOREM,
                   origin=FactOrigin.AXIOM, confidence=1.0, **kwargs)

    @classmethod
    def derived(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.DERIVED,
                   origin=FactOrigin.DERIVED, **kwargs)

    @classmethod
    def assumption(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.ASSUMPTION,
                   origin=FactOrigin.ASSUMED, **kwargs)

    @classmethod
    def case(cls, expression: str, scope_label: str = "", **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.CASE,
                   origin=FactOrigin.ASSUMED, scope_label=scope_label, **kwargs)

    @classmethod
    def proved(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.PROVED,
                   origin=FactOrigin.DERIVED, confidence=1.0, **kwargs)

    @classmethod
    def goal(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.GOAL,
                   origin=FactOrigin.GIVEN, **kwargs)

    @classmethod
    def definition(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.DEFINITION,
                   origin=FactOrigin.AXIOM, confidence=1.0, **kwargs)

    @classmethod
    def domain(cls, expression: str, **kwargs) -> Fact:
        return cls(expression=expression, fact_type=FactType.DOMAIN,
                   origin=FactOrigin.GIVEN, confidence=1.0, **kwargs)


@dataclass(frozen=True)
class FactEdge:
    """
    事实推导边 — 记录事实之间的关系。

    8 种边类型:
      DERIVES      — A 推导出 B (计算/推导)
      IMPLIES      — A 蕴含 B (逻辑蕴含)
      DEPENDS_ON   — B 依赖于 A (依赖关系)
      JUSTIFIES    — A 证明/支持 B (证明关系)
      CONTRADICTS  — A 与 B 矛盾 (冲突)
      EQUIVALENT   — A 等价于 B (等价关系)
      SPECIALIZES  — A 是 B 的特例 (特化)
      GENERALIZES  — A 是 B 的推广 (泛化)
    """

    source_fp: str
    target_fp: str
    edge_type: FactEdgeType = FactEdgeType.DERIVES
    rule: str = ""
    confidence: float = 1.0

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source_fp}->{self.target_fp}::{self.edge_type.value}::{self.rule}"
        return hashlib.sha256(raw.encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        d: dict = {
            "source": self.source_fp,
            "target": self.target_fp,
            "edge_type": self.edge_type.value,
        }
        if self.rule:
            d["rule"] = self.rule
        if self.confidence < 1.0:
            d["confidence"] = self.confidence
        return d

    @classmethod
    def from_dict(cls, d: dict) -> FactEdge:
        return cls(
            source_fp=d["source"],
            target_fp=d["target"],
            edge_type=FactEdgeType(d.get("edge_type", "derives")),
            rule=d.get("rule", ""),
            confidence=d.get("confidence", 1.0),
        )
