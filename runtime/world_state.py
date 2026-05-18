"""
WorldState — 统一数学世界状态

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学推理本质: 世界状态的演化

    State_t
      → 引入正数约束
      → 允许绝对值消去
      → State_{t+1}

  RuntimeState 已经很强，但不够统一:

    代数推导    — 部分支持
    微积分      — 部分支持
    证明题      — 不统一
    分类讨论    — 不统一
    子目标      — 不统一
    证明上下文  — 不统一

  WorldState 统一所有数学推理类型:

    expressions    — 数学表达式
    constraints    — 约束图 (ConstraintGraph)
    assumptions    — 结构化假设 (Assumption)
    obligations    — 证明义务 (ProofObligation)
    goals          — 目标/子目标 (Goal)
    facts          — 事实推导图 (FactGraph)
    domains        — 定义域注册表 (DomainRegistry)
    scope          — 变量作用域 (VariableScope)
    proof_context  — 证明上下文 (ProofContext)
    metadata       — 状态元数据 (StateMetadata)
    fingerprint    — 语义指纹

  设计原则:
    1. 不可变核心 — WorldState 本身不可变，修改产生新版本
    2. 图驱动 — constraints 用 ConstraintGraph，facts 用 FactGraph
    3. 目标导向 — goals 追踪推理目标及其分解
    4. 证明感知 — proof_context 追踪证明策略和定理使用
    5. 作用域管理 — scope 支持嵌套变量绑定
    6. 向后兼容 — 提供 from_runtime_state() / to_runtime_state() 桥接

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from math_ir import MathExpression, MathState, ExprCategory
from constraints.graph import (
    ConstraintGraph,
    ConstraintNode,
    ConstraintStatus,
    ConstraintRelation,
    ConflictReport,
)
from operations import Op
from facts.fact import Fact, FactType, FactOrigin, FactEdge, FactEdgeType
from facts.graph import FactGraph, FactQuery, FactQueryResult, ConsumeProduceRecord
from facts.consumer import (
    FactConsumer, FactProducer, ConsumeSpec, ProduceSpec,
    OperationFactFlow, ConsumeResult, FlowResult, BUILTIN_FLOWS,
)


class ObligationStatus(Enum):
    PENDING = auto()
    DISCHARGED = auto()
    WAIVED = auto()
    VIOLATED = auto()


class DomainKind(Enum):
    REAL = "real"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NONNEGATIVE = "nonnegative"
    NONPOSITIVE = "nonpositive"
    NONZERO = "nonzero"
    INTEGER = "integer"
    NATURAL = "natural"
    COMPLEX = "complex"
    OPEN_INTERVAL = "open_interval"
    CLOSED_INTERVAL = "closed_interval"
    CUSTOM = "custom"


class GoalStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    ACHIEVED = auto()
    FAILED = auto()
    DEFERRED = auto()


class GoalKind(Enum):
    PROVE = "prove"
    COMPUTE = "compute"
    SOLVE = "solve"
    SIMPLIFY = "simplify"
    VERIFY = "verify"
    EXPLORE = "explore"


class ProofStrategy(Enum):
    DIRECT = "direct"
    CONTRADICTION = "contradiction"
    INDUCTION = "induction"
    CONSTRUCTION = "construction"
    EXHAUSTION = "exhaustion"
    EQUIVALENCE = "equivalence"


class ProofPhase(Enum):
    NOT_STARTED = auto()
    ANALYZING = auto()
    PLANNING = auto()
    EXECUTING = auto()
    VERIFYING = auto()
    COMPLETED = auto()
    FAILED = auto()


class AssumptionKind(Enum):
    GIVEN = "given"
    HYPOTHESIS = "hypothesis"
    AXIOM = "axiom"
    CONVENTION = "convention"
    CASE_ASSUMPTION = "case_assumption"
    TEMPORARY = "temporary"


@dataclass(frozen=True)
class Assumption:
    """
    结构化假设 — 替代扁平 str。

    升级点:
      - kind: 区分已知条件/假设/公理/分类讨论假设
      - retractable: 是否可撤销 (分类讨论假设可撤销)
      - confidence: 置信度 (公理=1.0, 假设<1.0)
      - source: 来源 (题目/推导/分类讨论分支)
    """

    proposition: str
    kind: AssumptionKind = AssumptionKind.GIVEN
    confidence: float = 1.0
    retractable: bool = False
    source: str = ""
    label: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if self.kind == AssumptionKind.CASE_ASSUMPTION:
            object.__setattr__(self, "retractable", True)
        if self.kind == AssumptionKind.TEMPORARY:
            object.__setattr__(self, "retractable", True)
        if self.kind == AssumptionKind.AXIOM:
            object.__setattr__(self, "confidence", 1.0)

    @property
    def fingerprint(self) -> str:
        raw = f"{self.proposition}::{self.kind.value}::{self.source}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def is_certain(self) -> bool:
        return self.confidence >= 0.95 and self.kind in (
            AssumptionKind.GIVEN, AssumptionKind.AXIOM, AssumptionKind.CONVENTION,
        )

    @property
    def is_hypothesis(self) -> bool:
        return self.kind in (AssumptionKind.HYPOTHESIS, AssumptionKind.CASE_ASSUMPTION)

    def with_confidence(self, confidence: float) -> Assumption:
        return Assumption(
            proposition=self.proposition,
            kind=self.kind,
            confidence=confidence,
            retractable=self.retractable,
            source=self.source,
            label=self.label,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "proposition": self.proposition,
            "kind": self.kind.value,
            "confidence": self.confidence,
        }
        if self.retractable:
            d["retractable"] = True
        if self.source:
            d["source"] = self.source
        if self.label:
            d["label"] = self.label
        if self.timestamp:
            d["timestamp"] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Assumption:
        return cls(
            proposition=d["proposition"],
            kind=AssumptionKind(d.get("kind", "given")),
            confidence=d.get("confidence", 1.0),
            retractable=d.get("retractable", False),
            source=d.get("source", ""),
            label=d.get("label", ""),
            timestamp=d.get("timestamp", ""),
        )


@dataclass(frozen=True)
class Goal:
    """
    目标/子目标 — 追踪推理目标。

    数学推理是目标驱动的:
      - 证明题: 目标 = "证明 P(n) 对所有 n 成立"
      - 计算题: 目标 = "计算 ∫f(x)dx"
      - 方程题: 目标 = "求解 f(x) = 0"

    子目标分解:
      主目标: "证明不等式"
        子目标1: "证明左式 ≥ 右式"
          子子目标1: "证明中间量 ≥ 0"
          子子目标2: "证明中间量 ≤ 差值"
        子目标2: "验证等号条件"

    目标状态机:
      PENDING → IN_PROGRESS → ACHIEVED
                            → FAILED
                            → DEFERRED
    """

    description: str
    kind: GoalKind = GoalKind.PROVE
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5
    parent_id: str = ""
    subgoal_ids: tuple[str, ...] = ()
    strategy: ProofStrategy = ProofStrategy.DIRECT
    progress: float = 0.0
    label: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))

    @property
    def id(self) -> str:
        raw = f"{self.description}::{self.kind.value}::{self.parent_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def is_root(self) -> bool:
        return not self.parent_id

    @property
    def is_leaf(self) -> bool:
        return not self.subgoal_ids

    @property
    def is_terminal(self) -> bool:
        return self.status in (GoalStatus.ACHIEVED, GoalStatus.FAILED)

    @property
    def is_active(self) -> bool:
        return self.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)

    def with_status(self, status: GoalStatus, progress: float = -1.0) -> Goal:
        return Goal(
            description=self.description,
            kind=self.kind,
            status=status,
            priority=self.priority,
            parent_id=self.parent_id,
            subgoal_ids=self.subgoal_ids,
            strategy=self.strategy,
            progress=progress if progress >= 0 else self.progress,
            label=self.label,
            timestamp=self.timestamp,
        )

    def with_subgoal(self, subgoal_id: str) -> Goal:
        return Goal(
            description=self.description,
            kind=self.kind,
            status=self.status,
            priority=self.priority,
            parent_id=self.parent_id,
            subgoal_ids=self.subgoal_ids + (subgoal_id,),
            strategy=self.strategy,
            progress=self.progress,
            label=self.label,
            timestamp=self.timestamp,
        )

    def with_strategy(self, strategy: ProofStrategy) -> Goal:
        return Goal(
            description=self.description,
            kind=self.kind,
            status=self.status,
            priority=self.priority,
            parent_id=self.parent_id,
            subgoal_ids=self.subgoal_ids,
            strategy=strategy,
            progress=self.progress,
            label=self.label,
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "description": self.description,
            "kind": self.kind.value,
            "status": self.status.name,
            "priority": self.priority,
        }
        if self.parent_id:
            d["parent_id"] = self.parent_id
        if self.subgoal_ids:
            d["subgoal_ids"] = list(self.subgoal_ids)
        if self.strategy != ProofStrategy.DIRECT:
            d["strategy"] = self.strategy.value
        if self.progress > 0:
            d["progress"] = self.progress
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Goal:
        return cls(
            description=d["description"],
            kind=GoalKind(d.get("kind", "prove")),
            status=GoalStatus[d.get("status", "PENDING")],
            priority=d.get("priority", 5),
            parent_id=d.get("parent_id", ""),
            subgoal_ids=tuple(d.get("subgoal_ids", ())),
            strategy=ProofStrategy(d.get("strategy", "direct")),
            progress=d.get("progress", 0.0),
            label=d.get("label", ""),
        )


MathFact = Fact


@dataclass(frozen=True)
class VariableBinding:
    """
    变量绑定 — 记录变量的完整信息。
    """

    name: str
    domain: DomainKind = DomainKind.REAL
    bounds: tuple[float, ...] = ()
    introduced_at: str = ""
    scope_depth: int = 0
    source: str = ""

    @property
    def description(self) -> str:
        kind_desc = {
            DomainKind.REAL: "∈ ℝ",
            DomainKind.POSITIVE: "> 0",
            DomainKind.NEGATIVE: "< 0",
            DomainKind.NONNEGATIVE: "≥ 0",
            DomainKind.NONPOSITIVE: "≤ 0",
            DomainKind.NONZERO: "≠ 0",
            DomainKind.INTEGER: "∈ ℤ",
            DomainKind.NATURAL: "∈ ℕ",
            DomainKind.COMPLEX: "∈ ℂ",
        }
        if self.domain in (DomainKind.OPEN_INTERVAL, DomainKind.CLOSED_INTERVAL):
            if len(self.bounds) == 2:
                bracket = "(" if self.domain == DomainKind.OPEN_INTERVAL else "["
                bracket_r = ")" if self.domain == DomainKind.OPEN_INTERVAL else "]"
                return f"{self.name} ∈ {bracket}{self.bounds[0]}, {self.bounds[1]}{bracket_r}"
            return f"{self.name} {self.domain.value}"
        return f"{self.name} {kind_desc.get(self.domain, self.domain.value)}"

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "domain": self.domain.value}
        if self.bounds:
            d["bounds"] = list(self.bounds)
        if self.introduced_at:
            d["introduced_at"] = self.introduced_at
        if self.scope_depth > 0:
            d["scope_depth"] = self.scope_depth
        if self.source:
            d["source"] = self.source
        return d

    @classmethod
    def from_dict(cls, d: dict) -> VariableBinding:
        return cls(
            name=d["name"],
            domain=DomainKind(d.get("domain", "real")),
            bounds=tuple(d.get("bounds", ())),
            introduced_at=d.get("introduced_at", ""),
            scope_depth=d.get("scope_depth", 0),
            source=d.get("source", ""),
        )


@dataclass(frozen=True)
class VariableScope:
    """
    变量作用域 — 支持嵌套的变量管理。

    升级点:
      - 显式绑定: 每个变量有完整的绑定信息
      - 作用域嵌套: 分类讨论/子证明可引入局部变量
      - 引入追踪: 记录变量在哪一步被引入
    """

    bindings: tuple[VariableBinding, ...] = ()
    depth: int = 0

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(b.name for b in self.bindings)

    @property
    def is_empty(self) -> bool:
        return not self.bindings

    def binding_of(self, name: str) -> Optional[VariableBinding]:
        for b in self.bindings:
            if b.name == name:
                return b
        return None

    def domain_of(self, name: str) -> DomainKind:
        b = self.binding_of(name)
        return b.domain if b else DomainKind.REAL

    def has_variable(self, name: str) -> bool:
        return self.binding_of(name) is not None

    def introduce(self, name: str, domain: DomainKind = DomainKind.REAL,
                  bounds: tuple[float, ...] = (),
                  source: str = "") -> VariableScope:
        new_binding = VariableBinding(
            name=name, domain=domain, bounds=bounds,
            introduced_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            scope_depth=self.depth,
            source=source,
        )
        existing = tuple(b for b in self.bindings if b.name != name)
        return VariableScope(bindings=existing + (new_binding,), depth=self.depth)

    def restrict(self, name: str, new_domain: DomainKind,
                 source: str = "") -> VariableScope:
        new_bindings = []
        for b in self.bindings:
            if b.name == name:
                new_bindings.append(VariableBinding(
                    name=name, domain=new_domain, bounds=b.bounds,
                    introduced_at=b.introduced_at,
                    scope_depth=b.scope_depth,
                    source=source or b.source,
                ))
            else:
                new_bindings.append(b)
        return VariableScope(bindings=tuple(new_bindings), depth=self.depth)

    def push_scope(self) -> VariableScope:
        return VariableScope(bindings=self.bindings, depth=self.depth + 1)

    def pop_scope(self) -> VariableScope:
        new_bindings = tuple(b for b in self.bindings if b.scope_depth < self.depth)
        return VariableScope(bindings=new_bindings, depth=max(0, self.depth - 1))

    def to_dict(self) -> dict:
        return {
            "bindings": [b.to_dict() for b in self.bindings],
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, d: dict) -> VariableScope:
        bindings = tuple(VariableBinding.from_dict(b) for b in d.get("bindings", []))
        return cls(bindings=bindings, depth=d.get("depth", 0))

    @classmethod
    def empty(cls) -> VariableScope:
        return cls()


@dataclass(frozen=True)
class ProofContext:
    """
    证明上下文 — 追踪证明策略和定理使用。

    证明题需要:
      - 策略选择: 直接证明/反证法/数学归纳法/构造法
      - 定理追踪: 已用了哪些定理
      - 阶段管理: 分析→规划→执行→验证
      - 失败记录: 哪些策略失败了，避免重复

    分类讨论也需要:
      - 当前分支
      - 已完成分支
      - 待处理分支
    """

    strategy: ProofStrategy = ProofStrategy.DIRECT
    phase: ProofPhase = ProofPhase.NOT_STARTED
    theorems_used: tuple[str, ...] = ()
    failed_strategies: tuple[str, ...] = ()
    current_branch: str = ""
    completed_branches: tuple[str, ...] = ()
    pending_branches: tuple[str, ...] = ()
    proof_log: tuple[str, ...] = ()

    @property
    def is_proving(self) -> bool:
        return self.phase in (
            ProofPhase.ANALYZING, ProofPhase.PLANNING,
            ProofPhase.EXECUTING, ProofPhase.VERIFYING,
        )

    @property
    def is_completed(self) -> bool:
        return self.phase == ProofPhase.COMPLETED

    @property
    def branch_count(self) -> int:
        return len(self.completed_branches) + len(self.pending_branches) + (1 if self.current_branch else 0)

    @property
    def all_branches_done(self) -> bool:
        return not self.pending_branches and not self.current_branch

    def with_strategy(self, strategy: ProofStrategy) -> ProofContext:
        return ProofContext(
            strategy=strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def with_phase(self, phase: ProofPhase) -> ProofContext:
        return ProofContext(
            strategy=self.strategy,
            phase=phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def use_theorem(self, theorem: str) -> ProofContext:
        if theorem in self.theorems_used:
            return self
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used + (theorem,),
            failed_strategies=self.failed_strategies,
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def fail_strategy(self, strategy: str) -> ProofContext:
        if strategy in self.failed_strategies:
            return self
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies + (strategy,),
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def enter_branch(self, branch: str) -> ProofContext:
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def complete_branch(self) -> ProofContext:
        if not self.current_branch:
            return self
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch="",
            completed_branches=self.completed_branches + (self.current_branch,),
            pending_branches=self.pending_branches,
            proof_log=self.proof_log,
        )

    def add_pending_branch(self, branch: str) -> ProofContext:
        if branch in self.pending_branches:
            return self
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches + (branch,),
            proof_log=self.proof_log,
        )

    def next_branch(self) -> ProofContext:
        if not self.pending_branches:
            return self
        branch = self.pending_branches[0]
        remaining = self.pending_branches[1:]
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=branch,
            completed_branches=self.completed_branches,
            pending_branches=remaining,
            proof_log=self.proof_log,
        )

    def log(self, message: str) -> ProofContext:
        return ProofContext(
            strategy=self.strategy,
            phase=self.phase,
            theorems_used=self.theorems_used,
            failed_strategies=self.failed_strategies,
            current_branch=self.current_branch,
            completed_branches=self.completed_branches,
            pending_branches=self.pending_branches,
            proof_log=self.proof_log + (f"[{time.strftime('%H:%M:%S')}] {message}",),
        )

    def to_dict(self) -> dict:
        d: dict = {
            "strategy": self.strategy.value,
            "phase": self.phase.name,
        }
        if self.theorems_used:
            d["theorems_used"] = list(self.theorems_used)
        if self.failed_strategies:
            d["failed_strategies"] = list(self.failed_strategies)
        if self.current_branch:
            d["current_branch"] = self.current_branch
        if self.completed_branches:
            d["completed_branches"] = list(self.completed_branches)
        if self.pending_branches:
            d["pending_branches"] = list(self.pending_branches)
        if self.proof_log:
            d["proof_log"] = list(self.proof_log)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ProofContext:
        return cls(
            strategy=ProofStrategy(d.get("strategy", "direct")),
            phase=ProofPhase[d.get("phase", "NOT_STARTED")],
            theorems_used=tuple(d.get("theorems_used", ())),
            failed_strategies=tuple(d.get("failed_strategies", ())),
            current_branch=d.get("current_branch", ""),
            completed_branches=tuple(d.get("completed_branches", ())),
            pending_branches=tuple(d.get("pending_branches", ())),
            proof_log=tuple(d.get("proof_log", ())),
        )

    @classmethod
    def empty(cls) -> ProofContext:
        return cls()


@dataclass(frozen=True)
class ProofObligation:
    proposition: str
    status: ObligationStatus = ObligationStatus.PENDING
    source_step: str = ""
    reason: str = ""
    discharged_by: str = ""
    priority: int = 0

    @property
    def is_pending(self) -> bool:
        return self.status == ObligationStatus.PENDING

    @property
    def is_discharged(self) -> bool:
        return self.status == ObligationStatus.DISCHARGED

    def with_status(self, status: ObligationStatus, discharged_by: str = "",
                    reason: str = "") -> ProofObligation:
        return ProofObligation(
            proposition=self.proposition,
            status=status,
            source_step=self.source_step,
            reason=reason or self.reason,
            discharged_by=discharged_by or self.discharged_by,
            priority=self.priority,
        )

    def to_dict(self) -> dict:
        d: dict = {"proposition": self.proposition, "status": self.status.name}
        if self.source_step:
            d["source_step"] = self.source_step
        if self.reason:
            d["reason"] = self.reason
        if self.discharged_by:
            d["discharged_by"] = self.discharged_by
        if self.priority != 0:
            d["priority"] = self.priority
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ProofObligation:
        return cls(
            proposition=d["proposition"],
            status=ObligationStatus[d.get("status", "PENDING")],
            source_step=d.get("source_step", ""),
            reason=d.get("reason", ""),
            discharged_by=d.get("discharged_by", ""),
            priority=d.get("priority", 0),
        )


@dataclass(frozen=True)
class DomainEntry:
    variable: str
    kind: DomainKind = DomainKind.REAL
    bounds: tuple[float, ...] = ()
    source: str = ""

    @property
    def description(self) -> str:
        kind_desc = {
            DomainKind.REAL: "∈ ℝ",
            DomainKind.POSITIVE: "> 0",
            DomainKind.NEGATIVE: "< 0",
            DomainKind.NONNEGATIVE: "≥ 0",
            DomainKind.NONPOSITIVE: "≤ 0",
            DomainKind.NONZERO: "≠ 0",
            DomainKind.INTEGER: "∈ ℤ",
            DomainKind.NATURAL: "∈ ℕ",
            DomainKind.COMPLEX: "∈ ℂ",
        }
        if self.kind in (DomainKind.OPEN_INTERVAL, DomainKind.CLOSED_INTERVAL):
            if len(self.bounds) == 2:
                bracket = "(" if self.kind == DomainKind.OPEN_INTERVAL else "["
                bracket_r = ")" if self.kind == DomainKind.OPEN_INTERVAL else "]"
                return f"{self.variable} ∈ {bracket}{self.bounds[0]}, {self.bounds[1]}{bracket_r}"
            return f"{self.variable} {self.kind.value}"
        return f"{self.variable} {kind_desc.get(self.kind, self.kind.value)}"

    def to_dict(self) -> dict:
        d: dict = {"variable": self.variable, "kind": self.kind.value}
        if self.bounds:
            d["bounds"] = list(self.bounds)
        if self.source:
            d["source"] = self.source
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DomainEntry:
        return cls(
            variable=d["variable"],
            kind=DomainKind(d.get("kind", "real")),
            bounds=tuple(d.get("bounds", ())),
            source=d.get("source", ""),
        )


@dataclass
class DomainRegistry:
    entries: dict[str, DomainEntry] = field(default_factory=dict)

    def register(self, variable: str, kind: DomainKind = DomainKind.REAL,
                 bounds: tuple[float, ...] = (), source: str = "") -> None:
        self.entries[variable] = DomainEntry(
            variable=variable, kind=kind, bounds=bounds, source=source,
        )

    def lookup(self, variable: str) -> Optional[DomainEntry]:
        return self.entries.get(variable)

    def domain_of(self, variable: str) -> DomainKind:
        entry = self.entries.get(variable)
        return entry.kind if entry else DomainKind.REAL

    def all_variables(self) -> list[str]:
        return list(self.entries.keys())

    def restrict(self, variable: str, new_kind: DomainKind,
                 source: str = "") -> DomainRegistry:
        new_entries = dict(self.entries)
        old = new_entries.get(variable)
        bounds = old.bounds if old else ()
        new_entries[variable] = DomainEntry(
            variable=variable, kind=new_kind, bounds=bounds,
            source=source or (old.source if old else ""),
        )
        return DomainRegistry(entries=new_entries)

    def to_dict(self) -> dict:
        return {v: e.to_dict() for v, e in self.entries.items()}

    @classmethod
    def from_dict(cls, d: dict) -> DomainRegistry:
        entries = {v: DomainEntry.from_dict(e) for v, e in d.items()}
        return cls(entries=entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, variable: str) -> bool:
        return variable in self.entries


class VerificationResult(Enum):
    PASS = auto()
    FAIL = auto()
    WARNING = auto()
    SKIPPED = auto()
    PENDING = auto()


@dataclass(frozen=True)
class ExecutionEvent:
    operation: str = ""
    input_state_hash: str = ""
    output_state_hash: str = ""
    verification_result: VerificationResult = VerificationResult.PENDING
    generated_constraints: tuple[str, ...] = ()
    generated_obligations: tuple[str, ...] = ()
    timestamp: str = ""
    duration_ms: float = 0.0
    message: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))

    @property
    def is_verified(self) -> bool:
        return self.verification_result in (
            VerificationResult.PASS, VerificationResult.WARNING,
        )

    @property
    def is_failed(self) -> bool:
        return self.verification_result == VerificationResult.FAIL

    def to_dict(self) -> dict:
        d: dict = {
            "operation": self.operation,
            "verification_result": self.verification_result.name,
        }
        if self.input_state_hash:
            d["input_state_hash"] = self.input_state_hash
        if self.output_state_hash:
            d["output_state_hash"] = self.output_state_hash
        if self.generated_constraints:
            d["generated_constraints"] = list(self.generated_constraints)
        if self.generated_obligations:
            d["generated_obligations"] = list(self.generated_obligations)
        if self.timestamp:
            d["timestamp"] = self.timestamp
        if self.duration_ms > 0:
            d["duration_ms"] = self.duration_ms
        if self.message:
            d["message"] = self.message
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ExecutionEvent:
        return cls(
            operation=d.get("operation", ""),
            input_state_hash=d.get("input_state_hash", d.get("input_fingerprint", "")),
            output_state_hash=d.get("output_state_hash", d.get("output_fingerprint", "")),
            verification_result=VerificationResult[d.get("verification_result", "PENDING")],
            generated_constraints=tuple(d.get("generated_constraints", ())),
            generated_obligations=tuple(d.get("generated_obligations", ())),
            timestamp=d.get("timestamp", ""),
            duration_ms=d.get("duration_ms", 0.0),
            message=d.get("message", ""),
        )


@dataclass(frozen=True)
class StateMetadata:
    """
    状态元数据 — 升级自 RuntimeMetadata。

    新增:
      - version: 2 (WorldState 版本)
      - source_chain: 来源链 (完整的状态演化路径)
      - semantic_hash: 语义指纹 (缓存)
      - tags: 标签 (分类/检索)
    """

    version: int = 2
    created_at: str = ""
    parent_fingerprint: str = ""
    source_operation: str = ""
    source_step_id: str = ""
    source_chain: tuple[str, ...] = ()
    semantic_hash: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", time.strftime("%Y-%m-%dT%H:%M:%S"))

    def to_dict(self) -> dict:
        d: dict = {"version": self.version, "created_at": self.created_at}
        if self.parent_fingerprint:
            d["parent_fingerprint"] = self.parent_fingerprint
        if self.source_operation:
            d["source_operation"] = self.source_operation
        if self.source_step_id:
            d["source_step_id"] = self.source_step_id
        if self.source_chain:
            d["source_chain"] = list(self.source_chain)
        if self.semantic_hash:
            d["semantic_hash"] = self.semantic_hash
        if self.tags:
            d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> StateMetadata:
        return cls(
            version=d.get("version", 2),
            created_at=d.get("created_at", ""),
            parent_fingerprint=d.get("parent_fingerprint", ""),
            source_operation=d.get("source_operation", ""),
            source_step_id=d.get("source_step_id", ""),
            source_chain=tuple(d.get("source_chain", ())),
            semantic_hash=d.get("semantic_hash", ""),
            tags=tuple(d.get("tags", ())),
        )


@dataclass(frozen=True)
class WorldState:
    """
    统一数学世界状态 — 替代 RuntimeState。

    核心升级:
      1. assumptions: str → Assumption (结构化，可撤销)
      2. goals: 新增 (目标/子目标追踪)
      3. facts: tuple[MathFact] → FactGraph (图结构，显式边)
      4. scope: 计算属性 → VariableScope (结构化，嵌套)
      5. proof_context: 新增 (证明策略/分类讨论)
      6. metadata: RuntimeMetadata → StateMetadata (来源链/语义指纹)

    不变:
      expressions, constraints, obligations, domains 保持兼容
    """

    expressions: tuple[MathExpression, ...] = ()
    constraints: ConstraintGraph = field(default_factory=ConstraintGraph)
    assumptions: tuple[Assumption, ...] = ()
    obligations: tuple[ProofObligation, ...] = ()
    goals: tuple[Goal, ...] = ()
    facts: FactGraph = field(default_factory=FactGraph.empty)
    domains: DomainRegistry = field(default_factory=DomainRegistry)
    scope: VariableScope = field(default_factory=VariableScope.empty)
    proof_context: ProofContext = field(default_factory=ProofContext.empty)
    metadata: StateMetadata = field(default_factory=StateMetadata)

    @property
    def is_empty(self) -> bool:
        return (
            not self.expressions
            and not self.constraints.nodes
            and not self.assumptions
            and not self.obligations
            and not self.goals
            and self.facts.is_empty
        )

    @property
    def fingerprint(self) -> str:
        expr_parts = "|".join(e.latex or e.raw_text or "" for e in self.expressions)
        constraint_parts = "|".join(sorted(self.constraints.active_expressions()))
        assumption_parts = "|".join(a.proposition for a in self.assumptions)
        goal_parts = "|".join(f"{g.description}:{g.status.name}" for g in self.goals)
        fact_parts = "|".join(f.expression for f in self.facts.facts)
        domain_parts = "|".join(
            f"{v}:{e.kind.value}" for v, e in self.domains.entries.items()
        )
        obligation_parts = "|".join(
            f"{o.proposition}:{o.status.name}" for o in self.obligations
        )
        scope_parts = "|".join(
            f"{b.name}:{b.domain.value}" for b in self.scope.bindings
        )
        proof_parts = f"{self.proof_context.strategy.value}:{self.proof_context.phase.name}"
        raw = ";;".join([
            expr_parts, constraint_parts, assumption_parts,
            goal_parts, fact_parts, domain_parts, obligation_parts,
            scope_parts, proof_parts,
        ])
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def active_constraints(self) -> list[str]:
        return self.constraints.active_expressions()

    @property
    def pending_obligations(self) -> list[ProofObligation]:
        return [o for o in self.obligations if o.is_pending]

    @property
    def active_goals(self) -> tuple[Goal, ...]:
        return tuple(g for g in self.goals if g.is_active)

    @property
    def root_goals(self) -> tuple[Goal, ...]:
        return tuple(g for g in self.goals if g.is_root)

    @property
    def certain_facts(self) -> tuple[MathFact, ...]:
        return self.facts.certain_facts

    @property
    def variable_names(self) -> tuple[str, ...]:
        return self.scope.variable_names

    @property
    def assumption_propositions(self) -> tuple[str, ...]:
        return tuple(a.proposition for a in self.assumptions)

    def with_expression(self, expr: MathExpression) -> WorldState:
        return WorldState(
            expressions=self.expressions + (expr,),
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_expression",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_constraint(self, expression: str, source_step: str = "",
                        status: ConstraintStatus = ConstraintStatus.ACTIVE) -> WorldState:
        new_graph = ConstraintGraph.from_dict(self.constraints.to_dict())
        new_graph.add_constraint(expression, source_step=source_step, status=status)
        return WorldState(
            expressions=self.expressions,
            constraints=new_graph,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_constraint",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_assumption(self, assumption: Assumption) -> WorldState:
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions + (assumption,),
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_assumption",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_goal(self, goal: Goal) -> WorldState:
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals + (goal,),
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_goal",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def update_goal(self, goal_id: str, status: Optional[GoalStatus] = None,
                    progress: float = -1.0,
                    strategy: Optional[ProofStrategy] = None) -> WorldState:
        new_goals = []
        for g in self.goals:
            if g.id == goal_id:
                updated = g
                if status is not None:
                    updated = updated.with_status(status, progress)
                if strategy is not None:
                    updated = updated.with_strategy(strategy)
                new_goals.append(updated)
            else:
                new_goals.append(g)
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=tuple(new_goals),
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="update_goal",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_fact(self, fact: MathFact, edge: Optional[FactEdge] = None) -> WorldState:
        new_facts = self.facts.add_fact(fact, edge)
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=new_facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="derive_fact",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_obligation(self, obligation: ProofObligation) -> WorldState:
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations + (obligation,),
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_obligation",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def discharge_obligation(self, proposition: str,
                             discharged_by: str = "") -> WorldState:
        new_obligations = []
        for o in self.obligations:
            if o.proposition == proposition and o.is_pending:
                new_obligations.append(
                    o.with_status(ObligationStatus.DISCHARGED, discharged_by)
                )
            else:
                new_obligations.append(o)
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=tuple(new_obligations),
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="discharge_obligation",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_domain(self, variable: str, kind: DomainKind = DomainKind.REAL,
                    bounds: tuple[float, ...] = (),
                    source: str = "") -> WorldState:
        new_domains = self.domains.restrict(variable, kind, source)
        if variable not in self.domains:
            new_domains.register(variable, kind, bounds, source)
        new_scope = self.scope.introduce(variable, kind, bounds, source)
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=new_domains,
            scope=new_scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="set_domain",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_proof_context(self, proof_context: ProofContext) -> WorldState:
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="update_proof_context",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_scope(self, scope: VariableScope) -> WorldState:
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=self.facts,
            domains=self.domains,
            scope=scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="update_scope",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def cascade_invalidate(self, fp: str, reason: str = "") -> WorldState:
        new_facts = self.facts.cascade_invalidate(fp, reason)
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=new_facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="cascade_invalidate",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def retract_assumption(self, proposition: str) -> WorldState:
        new_assumptions = tuple(
            a for a in self.assumptions
            if a.proposition != proposition or not a.retractable
        )
        retracted = tuple(
            a for a in self.assumptions
            if a.proposition == proposition and a.retractable
        )
        new_facts = self.facts
        for a in retracted:
            matching = self.facts.facts_by_expression(a.proposition)
            for f in matching:
                new_facts = new_facts.cascade_invalidate(
                    f.fingerprint, reason=f"假设 '{a.proposition}' 被撤销"
                )
        return WorldState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=new_assumptions,
            obligations=self.obligations,
            goals=self.goals,
            facts=new_facts,
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="retract_assumption",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def with_constraints_propagated(self) -> WorldState:
        new_graph = ConstraintGraph.from_dict(self.constraints.to_dict())
        new_graph.full_process()
        new_fact_list = list(self.facts.facts)
        new_edges = list(self.facts.edges)
        for node in new_graph.active_constraints():
            if node.status == ConstraintStatus.DERIVED:
                already = any(f.expression == node.expression for f in new_fact_list)
                if not already:
                    dep_fps = tuple(
                        f.fingerprint for f in self.facts.facts
                        if f.expression == node.source_step or f.source_operation == "add_constraint"
                    )[:3]
                    new_fact = Fact(
                        expression=node.expression,
                        fact_type=FactType.DERIVED,
                        source_operation="constraint_propagation",
                        dependencies=dep_fps,
                        origin=FactOrigin.INFERRED,
                        confidence=node.confidence,
                        justification="constraint_propagation",
                    )
                    new_fact_list.append(new_fact)
                    for dep in dep_fps:
                        new_edges.append(FactEdge(
                            source_fp=dep,
                            target_fp=new_fact.fingerprint,
                            edge_type=FactEdgeType.DERIVES,
                            rule="constraint_propagation",
                            confidence=node.confidence,
                        ))
        conflict_report = new_graph.detect_conflicts()
        new_obligations = list(self.obligations)
        if conflict_report.has_conflict:
            for pair, explanation in zip(conflict_report.conflicting_pairs,
                                          conflict_report.explanations):
                new_obligations.append(ProofObligation(
                    proposition=f"解决约束冲突: {explanation}",
                    status=ObligationStatus.PENDING,
                    reason=explanation,
                    priority=10,
                ))
        return WorldState(
            expressions=self.expressions,
            constraints=new_graph,
            assumptions=self.assumptions,
            obligations=tuple(new_obligations),
            goals=self.goals,
            facts=FactGraph(facts=tuple(new_fact_list), edges=tuple(new_edges)),
            domains=self.domains,
            scope=self.scope,
            proof_context=self.proof_context,
            metadata=StateMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="propagate_constraints",
                source_chain=self.metadata.source_chain + (self.fingerprint,),
            ),
        )

    def semantic_hash(self) -> str:
        expr_texts = tuple(e.latex or e.raw_text or "" for e in self.expressions)
        constraint_texts = tuple(self.constraints.active_expressions())
        try:
            from canonicalization.fingerprint import (
                state_fingerprint,
                expression_fingerprint,
            )
            base_hash = state_fingerprint(
                expressions=expr_texts,
                constraints=constraint_texts,
                assumptions=self.assumption_propositions,
                variable_scope=self.variable_names,
            )
        except ImportError:
            base_hash = self.fingerprint

        domain_parts = sorted(
            f"{v}:{e.kind.value}" for v, e in self.domains.entries.items()
        )
        fact_parts = sorted(
            f"{f.expression}:{f.confidence}" for f in self.facts.facts
        )
        goal_parts = sorted(
            f"{g.description}:{g.status.name}" for g in self.goals
        )
        obligation_parts = sorted(
            f"{o.proposition}:{o.status.name}" for o in self.obligations
        )
        scope_parts = sorted(
            f"{b.name}:{b.domain.value}" for b in self.scope.bindings
        )
        proof_part = f"{self.proof_context.strategy.value}:{self.proof_context.phase.name}"

        extended_raw = ";;".join([
            base_hash,
            "|".join(domain_parts),
            "|".join(fact_parts),
            "|".join(goal_parts),
            "|".join(obligation_parts),
            "|".join(scope_parts),
            proof_part,
        ])
        return hashlib.sha256(extended_raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d: dict = {}
        if self.expressions:
            d["expressions"] = [e.to_dict() for e in self.expressions]
        if self.constraints.nodes:
            d["constraints"] = self.constraints.to_dict()
        if self.assumptions:
            d["assumptions"] = [a.to_dict() for a in self.assumptions]
        if self.obligations:
            d["obligations"] = [o.to_dict() for o in self.obligations]
        if self.goals:
            d["goals"] = [g.to_dict() for g in self.goals]
        if not self.facts.is_empty:
            d["facts"] = self.facts.to_dict()
        if self.domains.entries:
            d["domains"] = self.domains.to_dict()
        if not self.scope.is_empty:
            d["scope"] = self.scope.to_dict()
        if self.proof_context != ProofContext.empty():
            d["proof_context"] = self.proof_context.to_dict()
        d["metadata"] = self.metadata.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> WorldState:
        exprs = tuple(
            MathExpression.from_dict(e) for e in d.get("expressions", [])
        )
        constraints = ConstraintGraph.from_dict(d["constraints"]) if "constraints" in d else ConstraintGraph()
        assumptions = tuple(
            Assumption.from_dict(a) for a in d.get("assumptions", [])
        )
        obligations = tuple(
            ProofObligation.from_dict(o) for o in d.get("obligations", [])
        )
        goals = tuple(Goal.from_dict(g) for g in d.get("goals", []))
        facts = FactGraph.from_dict(d["facts"]) if "facts" in d else FactGraph.empty()
        domains = DomainRegistry.from_dict(d["domains"]) if "domains" in d else DomainRegistry()
        scope = VariableScope.from_dict(d["scope"]) if "scope" in d else VariableScope.empty()
        proof_context = ProofContext.from_dict(d["proof_context"]) if "proof_context" in d else ProofContext.empty()
        metadata = StateMetadata.from_dict(d["metadata"]) if "metadata" in d else StateMetadata()
        return cls(
            expressions=exprs,
            constraints=constraints,
            assumptions=assumptions,
            obligations=obligations,
            goals=goals,
            facts=facts,
            domains=domains,
            scope=scope,
            proof_context=proof_context,
            metadata=metadata,
        )

    @classmethod
    def empty(cls) -> WorldState:
        return cls()

    @classmethod
    def from_runtime_state(cls, state: "RuntimeState") -> WorldState:
        from runtime.state import RuntimeState as _RS
        if not isinstance(state, _RS):
            raise TypeError(f"Expected RuntimeState, got {type(state)}")
        assumptions = tuple(
            Assumption(proposition=a, kind=AssumptionKind.GIVEN, confidence=1.0)
            for a in state.assumptions
        )
        facts = FactGraph.from_legacy_tuple(state.derived_facts)
        scope = VariableScope.empty()
        for v in state.domains.all_variables():
            scope = scope.introduce(v, state.domains.domain_of(v))
        return cls(
            expressions=state.expressions,
            constraints=state.constraints,
            assumptions=assumptions,
            obligations=state.obligations,
            goals=(),
            facts=facts,
            domains=state.domains,
            scope=scope,
            proof_context=ProofContext.empty(),
            metadata=StateMetadata(
                version=2,
                parent_fingerprint=state.metadata.parent_fingerprint,
                source_operation=state.metadata.source_operation,
                source_step_id=state.metadata.source_step_id,
                tags=state.metadata.tags,
            ),
        )

    def to_runtime_state(self) -> "RuntimeState":
        from runtime.state import (
            RuntimeState as _RS,
            MathFact as _MF,
            ProofObligation as _PO,
            ObligationStatus as _OS,
            DomainKind as _DK,
            DomainEntry as _DE,
            DomainRegistry as _DR,
            FactOrigin as _FO,
            RuntimeMetadata as _RM,
            ExecutionEvent as _EE,
            VerificationResult as _VR,
        )
        assumption_strs = tuple(a.proposition for a in self.assumptions)
        old_facts = tuple(
            _MF(
                expression=f.expression,
                source_operation=f.source_operation,
                dependencies=f.dependencies,
                confidence=f.confidence,
                origin=_FO[f.origin.name],
                justification=f.justification,
                timestamp=f.timestamp,
            )
            for f in self.facts.facts
        )
        old_obligations = tuple(
            _PO(
                proposition=o.proposition,
                status=_OS[o.status.name],
                source_step=o.source_step,
                reason=o.reason,
                discharged_by=o.discharged_by,
                priority=o.priority,
            )
            for o in self.obligations
        )
        old_domains = _DR()
        for v, e in self.domains.entries.items():
            old_domains.register(
                v, _DK(e.kind.value), e.bounds, e.source,
            )
        return _RS(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=assumption_strs,
            domains=old_domains,
            obligations=old_obligations,
            derived_facts=old_facts,
            execution_history=(),
            metadata=_RM(
                parent_fingerprint=self.metadata.parent_fingerprint,
                source_operation=self.metadata.source_operation,
                source_step_id=self.metadata.source_step_id,
                tags=self.metadata.tags,
            ),
        )

    @classmethod
    def from_math_state(cls, state: MathState) -> WorldState:
        constraint_graph = ConstraintGraph.from_strings(list(state.constraints))
        domains = DomainRegistry()
        scope = VariableScope.empty()
        for v in state.variable_scope:
            domains.register(v, DomainKind.REAL)
            scope = scope.introduce(v, DomainKind.REAL)
        assumptions = tuple(
            Assumption(proposition=a, kind=AssumptionKind.GIVEN, confidence=1.0)
            for a in state.assumptions
        )
        return cls(
            expressions=state.expressions,
            constraints=constraint_graph,
            assumptions=assumptions,
            domains=domains,
            scope=scope,
        )

    def to_math_state(self) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumption_propositions,
            constraints=tuple(self.constraints.active_expressions()),
            variable_scope=self.variable_names,
        )

    def summary(self) -> dict:
        return {
            "expressions": len(self.expressions),
            "constraints": len(self.constraints.nodes),
            "active_constraints": len(self.constraints.active_constraints()),
            "assumptions": len(self.assumptions),
            "obligations": len(self.obligations),
            "pending_obligations": len(self.pending_obligations),
            "goals": len(self.goals),
            "active_goals": len(self.active_goals),
            "facts": self.facts.fact_count,
            "certain_facts": len(self.certain_facts),
            "domains": len(self.domains),
            "scope_variables": len(self.scope.bindings),
            "proof_strategy": self.proof_context.strategy.value,
            "proof_phase": self.proof_context.phase.name,
            "branches": self.proof_context.branch_count,
            "fingerprint": self.fingerprint,
            "semantic_hash": self.semantic_hash(),
            "source_chain_depth": len(self.metadata.source_chain),
        }
