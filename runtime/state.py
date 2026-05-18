"""
RuntimeState — 可执行数学状态

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  MathState 是静态快照，RuntimeState 是可执行状态。

  区别:
    MathState:  expressions + assumptions + constraints + variable_scope
                → 纯数据，无执行能力，无推导记忆

    RuntimeState: expressions + constraints(图) + assumptions + domains
                  + obligations + derived_facts + execution_history + metadata
                → 可执行，可推导，可回滚，可诊断

  数学本质:
    数学推理 = facts accumulation + constraint propagation + obligation discharge
    不是: 字符串步骤列表

  设计原则:
    1. 不可变核心 — RuntimeState 本身不可变，修改产生新版本
    2. 约束图驱动 — constraints 使用 ConstraintGraph，不是扁平列表
    3. 事实累积 — derived_facts 记录所有推导出的事实
    4. 义务追踪 — obligations 追踪待证明的命题
    5. 历史可溯 — execution_history 记录每一步变换
    6. 向后兼容 — 提供 from_math_state() / to_math_state() 桥接

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


class FactOrigin(Enum):
    ASSUMED = auto()
    DERIVED = auto()
    COMPUTED = auto()
    INFERRED = auto()
    AXIOM = auto()


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


@dataclass(frozen=True)
class MathFact:
    """
    数学事实 — 推理链的基本单元。

    数学推理本质:
      旧 facts → 推导 → 新 facts

    每个事实知道:
      - 自己是什么 (expression)
      - 怎么来的 (source_operation + dependencies)
      - 多可信 (confidence)
      - 何时产生 (timestamp)

    dependencies 是关键:
      它形成事实推导图 (Fact Derivation Graph)
      - 追溯: "为什么这个事实成立?" → 沿 dependencies 回溯
      - 级联失效: "这个前提错了" → 所有依赖它的事实都不可信
      - 诊断: "错误从哪来?" → 找到推导链的根事实
    """

    expression: str
    source_operation: str = ""
    dependencies: tuple[str, ...] = ()
    confidence: float = 1.0
    origin: FactOrigin = FactOrigin.DERIVED
    justification: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))

    @property
    def fingerprint(self) -> str:
        raw = f"{self.expression}::{self.source_operation}::{':'.join(self.dependencies)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def is_certain(self) -> bool:
        return self.confidence >= 0.95

    @property
    def is_assumed(self) -> bool:
        return self.origin == FactOrigin.ASSUMED

    @property
    def is_root(self) -> bool:
        return len(self.dependencies) == 0

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    def with_confidence(self, confidence: float) -> MathFact:
        return MathFact(
            expression=self.expression,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=confidence,
            origin=self.origin,
            justification=self.justification,
            timestamp=self.timestamp,
        )

    def invalidate(self, reason: str = "") -> MathFact:
        return MathFact(
            expression=self.expression,
            source_operation=self.source_operation,
            dependencies=self.dependencies,
            confidence=0.0,
            origin=self.origin,
            justification=f"INVALIDATED: {reason}" if reason else "INVALIDATED",
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict:
        d = {
            "expression": self.expression,
            "fingerprint": self.fingerprint,
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
        if self.timestamp:
            d["timestamp"] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, d: dict) -> MathFact:
        return cls(
            expression=d["expression"],
            source_operation=d.get("source_operation", d.get("source_step", "")),
            dependencies=tuple(d.get("dependencies", ())),
            confidence=d.get("confidence", 1.0),
            origin=FactOrigin[d.get("origin", "DERIVED")],
            justification=d.get("justification", ""),
            timestamp=d.get("timestamp", ""),
        )


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
        d = {
            "proposition": self.proposition,
            "status": self.status.name,
        }
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
        d = {"variable": self.variable, "kind": self.kind.value}
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
    """
    执行事件 — 记录一次状态变换的完整信息。

    每次操作 (Op) 作用于 RuntimeState 都会产生一个 ExecutionEvent:
      - operation: 执行了什么操作
      - input_state_hash / output_state_hash: 变换前后的状态指纹
      - verification_result: 操作结果是否通过验证
      - generated_constraints: 本次操作产生的新约束
      - generated_obligations: 本次操作产生的新证明义务

    这些事件构成 execution_history，用于:
      - 回滚: 回退到任意历史状态
      - 诊断: 定位哪一步出错
      - 审计: 完整的推理轨迹
    """

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
            VerificationResult.PASS,
            VerificationResult.WARNING,
        )

    @property
    def is_failed(self) -> bool:
        return self.verification_result == VerificationResult.FAIL

    def to_dict(self) -> dict:
        d = {
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
class RuntimeMetadata:
    version: int = 1
    created_at: str = ""
    parent_fingerprint: str = ""
    source_operation: str = ""
    source_step_id: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(self, "created_at", time.strftime("%Y-%m-%dT%H:%M:%S"))

    def to_dict(self) -> dict:
        d = {"version": self.version, "created_at": self.created_at}
        if self.parent_fingerprint:
            d["parent_fingerprint"] = self.parent_fingerprint
        if self.source_operation:
            d["source_operation"] = self.source_operation
        if self.source_step_id:
            d["source_step_id"] = self.source_step_id
        if self.tags:
            d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> RuntimeMetadata:
        return cls(
            version=d.get("version", 1),
            created_at=d.get("created_at", ""),
            parent_fingerprint=d.get("parent_fingerprint", ""),
            source_operation=d.get("source_operation", ""),
            source_step_id=d.get("source_step_id", ""),
            tags=tuple(d.get("tags", ())),
        )


@dataclass(frozen=True)
class RuntimeState:
    expressions: tuple[MathExpression, ...] = ()
    constraints: ConstraintGraph = field(default_factory=ConstraintGraph)
    assumptions: tuple[str, ...] = ()
    domains: DomainRegistry = field(default_factory=DomainRegistry)
    obligations: tuple[ProofObligation, ...] = ()
    derived_facts: tuple[MathFact, ...] = ()
    execution_history: tuple[ExecutionEvent, ...] = ()
    metadata: RuntimeMetadata = field(default_factory=RuntimeMetadata)

    @property
    def is_empty(self) -> bool:
        return (
            not self.expressions
            and not self.constraints.nodes
            and not self.assumptions
            and not self.obligations
            and not self.derived_facts
        )

    @property
    def fingerprint(self) -> str:
        expr_parts = "|".join(e.latex or e.raw_text or "" for e in self.expressions)
        constraint_parts = "|".join(sorted(self.constraints.active_expressions()))
        assumption_parts = "|".join(self.assumptions)
        fact_parts = "|".join(f.expression for f in self.derived_facts)
        domain_parts = "|".join(
            f"{v}:{e.kind.value}" for v, e in self.domains.entries.items()
        )
        obligation_parts = "|".join(
            f"{o.proposition}:{o.status.name}" for o in self.obligations
        )
        raw = ";;".join([
            expr_parts, constraint_parts, assumption_parts,
            fact_parts, domain_parts, obligation_parts,
        ])
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def active_constraints(self) -> list[str]:
        return self.constraints.active_expressions()

    @property
    def pending_obligations(self) -> list[ProofObligation]:
        return [o for o in self.obligations if o.is_pending]

    @property
    def certain_facts(self) -> list[MathFact]:
        return [f for f in self.derived_facts if f.is_certain]

    @property
    def root_facts(self) -> list[MathFact]:
        return [f for f in self.derived_facts if f.is_root]

    @property
    def fact_fingerprints(self) -> dict[str, MathFact]:
        return {f.fingerprint: f for f in self.derived_facts}

    def fact_by_fingerprint(self, fp: str) -> Optional[MathFact]:
        for f in self.derived_facts:
            if f.fingerprint == fp:
                return f
        return None

    def fact_provenance(self, fp: str) -> list[MathFact]:
        chain = []
        visited = set()
        current = self.fact_by_fingerprint(fp)
        while current and current.fingerprint not in visited:
            chain.append(current)
            visited.add(current.fingerprint)
            if not current.dependencies:
                break
            current = self.fact_by_fingerprint(current.dependencies[0])
        return chain

    def fact_dependents(self, fp: str) -> list[MathFact]:
        return [f for f in self.derived_facts if fp in f.dependencies]

    def cascade_invalidate(self, fp: str, reason: str = "") -> RuntimeState:
        to_invalidate = {fp}
        queue = [fp]
        while queue:
            current = queue.pop(0)
            for f in self.derived_facts:
                if current in f.dependencies and f.fingerprint not in to_invalidate:
                    to_invalidate.add(f.fingerprint)
                    queue.append(f.fingerprint)
        new_facts = []
        for f in self.derived_facts:
            if f.fingerprint in to_invalidate:
                new_facts.append(f.invalidate(reason or f"依赖 {fp} 被撤销"))
            else:
                new_facts.append(f)
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=self.obligations,
            derived_facts=tuple(new_facts),
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="cascade_invalidate",
            ),
        )

    @property
    def variable_scope(self) -> tuple[str, ...]:
        vars_set = set()
        for e in self.expressions:
            if e.raw_text:
                import re
                found = re.findall(r'[a-zA-Z]\w*', e.raw_text)
                vars_set.update(found)
        for v in self.domains.all_variables():
            vars_set.add(v)
        return tuple(sorted(vars_set))

    def with_expression(self, expr: MathExpression) -> RuntimeState:
        return RuntimeState(
            expressions=self.expressions + (expr,),
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=self.obligations,
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_expression",
            ),
        )

    def with_constraint(self, expression: str, source_step: str = "",
                        status: ConstraintStatus = ConstraintStatus.ACTIVE) -> RuntimeState:
        new_graph = ConstraintGraph.from_dict(self.constraints.to_dict())
        new_graph.add_constraint(expression, source_step=source_step, status=status)
        return RuntimeState(
            expressions=self.expressions,
            constraints=new_graph,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=self.obligations,
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_constraint",
            ),
        )

    def with_assumption(self, assumption: str) -> RuntimeState:
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions + (assumption,),
            domains=self.domains,
            obligations=self.obligations,
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_assumption",
            ),
        )

    def with_derived_fact(self, fact: MathFact) -> RuntimeState:
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=self.obligations,
            derived_facts=self.derived_facts + (fact,),
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="derive_fact",
            ),
        )

    def with_obligation(self, obligation: ProofObligation) -> RuntimeState:
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=self.obligations + (obligation,),
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="add_obligation",
            ),
        )

    def with_domain(self, variable: str, kind: DomainKind = DomainKind.REAL,
                    bounds: tuple[float, ...] = (), source: str = "") -> RuntimeState:
        new_domains = self.domains.restrict(variable, kind, source)
        if variable not in self.domains:
            new_domains.register(variable, kind, bounds, source)
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=new_domains,
            obligations=self.obligations,
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="set_domain",
            ),
        )

    def with_constraints_propagated(self) -> RuntimeState:
        new_graph = ConstraintGraph.from_dict(self.constraints.to_dict())
        new_graph.full_process()
        new_facts = list(self.derived_facts)
        for node in new_graph.active_constraints():
            if node.status == ConstraintStatus.DERIVED:
                already = any(f.expression == node.expression for f in new_facts)
                if not already:
                    dep_fps = tuple(
                        f.fingerprint for f in self.derived_facts
                        if f.expression == node.source_step or f.source_operation == "add_constraint"
                    )[:3]
                    new_facts.append(MathFact(
                        expression=node.expression,
                        source_operation="constraint_propagation",
                        dependencies=dep_fps,
                        origin=FactOrigin.INFERRED,
                        confidence=node.confidence,
                        justification="constraint_propagation",
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
        return RuntimeState(
            expressions=self.expressions,
            constraints=new_graph,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=tuple(new_obligations),
            derived_facts=tuple(new_facts),
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="propagate_constraints",
            ),
        )

    def discharge_obligation(self, proposition: str,
                             discharged_by: str = "") -> RuntimeState:
        new_obligations = []
        for o in self.obligations:
            if o.proposition == proposition and o.is_pending:
                new_obligations.append(
                    o.with_status(ObligationStatus.DISCHARGED, discharged_by)
                )
            else:
                new_obligations.append(o)
        return RuntimeState(
            expressions=self.expressions,
            constraints=self.constraints,
            assumptions=self.assumptions,
            domains=self.domains,
            obligations=tuple(new_obligations),
            derived_facts=self.derived_facts,
            execution_history=self.execution_history,
            metadata=RuntimeMetadata(
                parent_fingerprint=self.fingerprint,
                source_operation="discharge_obligation",
            ),
        )

    def to_dict(self) -> dict:
        d = {}
        if self.expressions:
            d["expressions"] = [e.to_dict() for e in self.expressions]
        if self.constraints.nodes:
            d["constraints"] = self.constraints.to_dict()
        if self.assumptions:
            d["assumptions"] = list(self.assumptions)
        if self.domains.entries:
            d["domains"] = self.domains.to_dict()
        if self.obligations:
            d["obligations"] = [o.to_dict() for o in self.obligations]
        if self.derived_facts:
            d["derived_facts"] = [f.to_dict() for f in self.derived_facts]
        if self.execution_history:
            d["execution_history"] = [e.to_dict() for e in self.execution_history]
        d["metadata"] = self.metadata.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> RuntimeState:
        exprs = tuple(
            MathExpression.from_dict(e) for e in d.get("expressions", [])
        )
        constraints = ConstraintGraph.from_dict(d["constraints"]) if "constraints" in d else ConstraintGraph()
        domains = DomainRegistry.from_dict(d["domains"]) if "domains" in d else DomainRegistry()
        obligations = tuple(
            ProofObligation.from_dict(o) for o in d.get("obligations", [])
        )
        facts = tuple(MathFact.from_dict(f) for f in d.get("derived_facts", []))
        history = tuple(ExecutionEvent.from_dict(e) for e in d.get("execution_history", []))
        metadata = RuntimeMetadata.from_dict(d["metadata"]) if "metadata" in d else RuntimeMetadata()
        return cls(
            expressions=exprs,
            constraints=constraints,
            assumptions=tuple(d.get("assumptions", [])),
            domains=domains,
            obligations=obligations,
            derived_facts=facts,
            execution_history=history,
            metadata=metadata,
        )

    @classmethod
    def empty(cls) -> RuntimeState:
        return cls()

    @classmethod
    def from_math_state(cls, state: MathState) -> RuntimeState:
        constraint_graph = ConstraintGraph.from_strings(list(state.constraints))
        domains = DomainRegistry()
        for v in state.variable_scope:
            domains.register(v, DomainKind.REAL)
        return cls(
            expressions=state.expressions,
            constraints=constraint_graph,
            assumptions=state.assumptions,
            domains=domains,
        )

    def to_math_state(self) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumptions,
            constraints=tuple(self.constraints.active_expressions()),
            variable_scope=self.variable_scope,
        )

    def semantic_hash(self) -> str:
        """
        语义哈希 — 基于规范化形式的状态指纹。

        与 fingerprint 的区别:
          fingerprint: 原始文本哈希，x^2-1 ≠ (x-1)(x+1)
          semantic_hash: 规范化哈希，x^2-1 == (x-1)(x+1)

        覆盖范围:
          expressions  — 规范化展开形式
          constraints  — 规范化约束集
          assumptions  — 排序后
          domains      — 变量域排序后
          derived_facts — 事实表达式排序后
          obligations  — 命题排序后

        用途:
          - cache: 相同语义状态复用计算结果
          - retrieval: 按语义检索历史步骤
          - graph matching: 快速判断两个节点是否等价
        """
        from canonicalization.fingerprint import (
            state_fingerprint,
            expression_fingerprint,
            constraint_fingerprint,
        )

        expr_texts = tuple(e.latex or e.raw_text or "" for e in self.expressions)
        constraint_texts = tuple(self.constraints.active_expressions())

        base_hash = state_fingerprint(
            expressions=expr_texts,
            constraints=constraint_texts,
            assumptions=self.assumptions,
            variable_scope=self.variable_scope,
        )

        domain_parts = sorted(
            f"{v}:{e.kind.value}" for v, e in self.domains.entries.items()
        )
        fact_parts = sorted(
            expression_fingerprint(f.expression) for f in self.derived_facts
        )
        obligation_parts = sorted(
            f"{o.proposition}:{o.status.name}" for o in self.obligations
        )

        extended_raw = ";;".join([
            base_hash,
            "|".join(domain_parts),
            "|".join(fact_parts),
            "|".join(obligation_parts),
        ])
        return hashlib.sha256(extended_raw.encode()).hexdigest()[:16]

    @property
    def canonical_hash(self) -> str:
        """
        完整语义指纹 — 包含所有字段的规范化哈希。

        与 semantic_hash 的区别:
          semantic_hash: 覆盖核心数学内容 (表达式/约束/事实/义务/域)
          canonical_hash: 覆盖全部字段，包括 execution_history

        用途:
          - cycle detection: 检测推理是否回到之前的状态
          - 完整状态比较: 两个 RuntimeState 是否完全等价
          - graph matching: 推导图中的精确节点匹配
        """
        expr_hash = self.semantic_hash()

        history_parts = sorted(
            f"{e.operation}:{e.input_state_hash[:8]}:{e.output_state_hash[:8]}:{e.verification_result.name}"
            for e in self.execution_history
        )

        metadata_raw = f"{self.metadata.version}:{self.metadata.parent_fingerprint}:{self.metadata.source_operation}"

        full_raw = ";;".join([
            expr_hash,
            "|".join(history_parts),
            metadata_raw,
        ])
        return hashlib.sha256(full_raw.encode()).hexdigest()[:20]

    def is_semantically_equivalent(self, other: RuntimeState) -> bool:
        if self.semantic_hash() == other.semantic_hash():
            return True
        from canonicalization.fingerprint import states_are_equivalent
        return states_are_equivalent(
            tuple(e.latex or e.raw_text or "" for e in self.expressions),
            tuple(self.constraints.active_expressions()),
            tuple(e.latex or e.raw_text or "" for e in other.expressions),
            tuple(other.constraints.active_expressions()),
        )

    def summary(self) -> dict:
        return {
            "expressions": len(self.expressions),
            "constraints": len(self.constraints.nodes),
            "active_constraints": len(self.constraints.active_constraints()),
            "assumptions": len(self.assumptions),
            "domains": len(self.domains),
            "obligations": len(self.obligations),
            "pending_obligations": len(self.pending_obligations),
            "derived_facts": len(self.derived_facts),
            "certain_facts": len(self.certain_facts),
            "execution_events": len(self.execution_history),
            "fingerprint": self.fingerprint,
            "semantic_hash": self.semantic_hash(),
            "canonical_hash": self.canonical_hash,
        }
