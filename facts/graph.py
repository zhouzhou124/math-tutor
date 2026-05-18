"""
FactGraph — 事实推导图

═══════════════════════════════════════════════════════════════
核心能力
═══════════════════════════════════════════════════════════════

  1. 按类型查询 — 查找所有 THEOREM / CONSTRAINT / CASE 事实
  2. Consume/Produce — 操作消耗/生产事实的完整追踪
  3. 溯源 — 从任意事实回溯到根事实
  4. 级联失效 — 前提失效 → 所有依赖失效
  5. 冲突检测 — CONTRADICTS 边标记矛盾
  6. 作用域过滤 — 分类讨论分支的事实隔离

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from facts.fact import Fact, FactEdge, FactType, FactEdgeType, FactOrigin


@dataclass(frozen=True)
class FactQuery:
    """
    事实查询 — 灵活的条件组合查询。

    支持:
      - 按 fact_type 过滤
      - 按 expression 模式匹配
      - 按 scope_label 过滤
      - 按 confidence 阈值
      - 按 produced_by 过滤
      - 按 consumed_by 过滤
    """

    fact_type: Optional[FactType] = None
    expression_pattern: str = ""
    scope_label: str = ""
    min_confidence: float = 0.0
    produced_by: str = ""
    consumed_by: str = ""
    include_invalidated: bool = False

    def matches(self, fact: Fact) -> bool:
        if self.fact_type is not None and fact.fact_type != self.fact_type:
            return False
        if self.expression_pattern and self.expression_pattern not in fact.expression:
            return False
        if self.scope_label and fact.scope_label != self.scope_label:
            return False
        if fact.confidence < self.min_confidence:
            return False
        if not self.include_invalidated and fact.confidence == 0.0:
            return False
        if self.produced_by and fact.produced_by != self.produced_by:
            return False
        if self.consumed_by and self.consumed_by not in fact.consumed_by:
            return False
        return True


@dataclass(frozen=True)
class FactQueryResult:
    facts: tuple[Fact, ...] = ()
    total_count: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.facts

    @property
    def first(self) -> Optional[Fact]:
        return self.facts[0] if self.facts else None

    @property
    def expressions(self) -> tuple[str, ...]:
        return tuple(f.expression for f in self.facts)


@dataclass(frozen=True)
class ConsumeProduceRecord:
    """
    操作的 consume/produce 记录。

    记录一次操作消耗了哪些事实、生产了哪些事实。
    """

    operation: str
    consumed_fps: tuple[str, ...] = ()
    produced_fps: tuple[str, ...] = ()
    timestamp: str = ""

    @property
    def fingerprint(self) -> str:
        raw = f"{self.operation}::{':'.join(self.consumed_fps)}::{':'.join(self.produced_fps)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        d: dict = {"operation": self.operation}
        if self.consumed_fps:
            d["consumed"] = list(self.consumed_fps)
        if self.produced_fps:
            d["produced"] = list(self.produced_fps)
        if self.timestamp:
            d["timestamp"] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ConsumeProduceRecord:
        return cls(
            operation=d["operation"],
            consumed_fps=tuple(d.get("consumed", ())),
            produced_fps=tuple(d.get("produced", ())),
            timestamp=d.get("timestamp", ""),
        )


@dataclass
class FactGraph:
    """
    事实推导图 — 推理链的核心数据结构。

    升级自 world_state.FactGraph:
      - facts: Fact (含 fact_type, consumed_by, produced_by)
      - edges: FactEdge (含 edge_type: 8 种关系)
      - records: ConsumeProduceRecord (操作消耗/生产追踪)
      - 按类型查询
      - consume/produce 模式
      - 作用域过滤
    """

    facts: tuple[Fact, ...] = ()
    edges: tuple[FactEdge, ...] = ()
    records: tuple[ConsumeProduceRecord, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.facts

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def active_facts(self) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.confidence > 0.0)

    @property
    def certain_facts(self) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.is_certain)

    @property
    def root_facts(self) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.is_root and f.confidence > 0.0)

    @property
    def fact_map(self) -> dict[str, Fact]:
        return {f.fingerprint: f for f in self.facts}

    def fact_by_fp(self, fp: str) -> Optional[Fact]:
        for f in self.facts:
            if f.fingerprint == fp:
                return f
        return None

    def facts_by_expression(self, expression: str) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.expression == expression)

    def facts_by_type(self, fact_type: FactType) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.fact_type == fact_type)

    @property
    def constraints(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.CONSTRAINT)

    @property
    def theorems(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.THEOREM)

    @property
    def derived_facts(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.DERIVED)

    @property
    def assumptions(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.ASSUMPTION)

    @property
    def case_facts(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.CASE)

    @property
    def proved_facts(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.PROVED)

    @property
    def goal_facts(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.GOAL)

    @property
    def definitions(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.DEFINITION)

    @property
    def domain_facts(self) -> tuple[Fact, ...]:
        return self.facts_by_type(FactType.DOMAIN)

    def facts_by_scope(self, scope_label: str) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.scope_label == scope_label)

    def facts_by_producer(self, operation: str) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if f.produced_by == operation)

    def facts_by_consumer(self, operation: str) -> tuple[Fact, ...]:
        return tuple(f for f in self.facts if operation in f.consumed_by)

    def query(self, q: FactQuery) -> FactQueryResult:
        matched = tuple(f for f in self.facts if q.matches(f))
        return FactQueryResult(facts=matched, total_count=len(matched))

    def type_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for ft in FactType:
            count = len(self.facts_by_type(ft))
            if count > 0:
                summary[ft.value] = count
        return summary

    def dependents_of(self, fp: str) -> tuple[Fact, ...]:
        direct_fps = set()
        for e in self.edges:
            if e.source_fp == fp:
                direct_fps.add(e.target_fp)
        for f in self.facts:
            if fp in f.dependencies:
                direct_fps.add(f.fingerprint)
        return tuple(self.fact_by_fp(fp) for fp in direct_fps if self.fact_by_fp(fp))

    def provenance(self, fp: str) -> tuple[Fact, ...]:
        chain = []
        visited = set()
        current = self.fact_by_fp(fp)
        while current and current.fingerprint not in visited:
            chain.append(current)
            visited.add(current.fingerprint)
            if not current.dependencies:
                break
            current = self.fact_by_fp(current.dependencies[0])
        return tuple(chain)

    def provenance_full(self, fp: str) -> tuple[Fact, ...]:
        all_deps = set()
        queue = [fp]
        while queue:
            current_fp = queue.pop(0)
            if current_fp in all_deps:
                continue
            all_deps.add(current_fp)
            fact = self.fact_by_fp(current_fp)
            if fact:
                for dep in fact.dependencies:
                    if dep not in all_deps:
                        queue.append(dep)
                for e in self.edges:
                    if e.target_fp == current_fp and e.source_fp not in all_deps:
                        queue.append(e.source_fp)
        return tuple(self.fact_by_fp(fp) for fp in all_deps if self.fact_by_fp(fp))

    def cascade_invalidate(self, fp: str, reason: str = "") -> FactGraph:
        to_invalidate = {fp}
        queue = [fp]
        while queue:
            current = queue.pop(0)
            for f in self.facts:
                if current in f.dependencies and f.fingerprint not in to_invalidate:
                    to_invalidate.add(f.fingerprint)
                    queue.append(f.fingerprint)
            for e in self.edges:
                if e.source_fp == current and e.target_fp not in to_invalidate:
                    if e.edge_type in (
                        FactEdgeType.DERIVES, FactEdgeType.IMPLIES,
                        FactEdgeType.DEPENDS_ON, FactEdgeType.JUSTIFIES,
                    ):
                        to_invalidate.add(e.target_fp)
                        queue.append(e.target_fp)
        new_facts = tuple(
            f.invalidate(reason or f"依赖 {fp} 被撤销")
            if f.fingerprint in to_invalidate else f
            for f in self.facts
        )
        return FactGraph(facts=new_facts, edges=self.edges, records=self.records)

    def add_fact(self, fact: Fact, edge: Optional[FactEdge] = None) -> FactGraph:
        new_edges = self.edges + (edge,) if edge else self.edges
        return FactGraph(facts=self.facts + (fact,), edges=new_edges, records=self.records)

    def add_edge(self, edge: FactEdge) -> FactGraph:
        return FactGraph(facts=self.facts, edges=self.edges + (edge,), records=self.records)

    def remove_fact(self, fp: str) -> FactGraph:
        new_facts = tuple(f for f in self.facts if f.fingerprint != fp)
        new_edges = tuple(
            e for e in self.edges
            if e.source_fp != fp and e.target_fp != fp
        )
        return FactGraph(facts=new_facts, edges=new_edges, records=self.records)

    def consume_produce(
        self,
        operation: str,
        consumed_fps: tuple[str, ...] = (),
        produced_facts: tuple[Fact, ...] = (),
        produced_edges: tuple[FactEdge, ...] = (),
    ) -> FactGraph:
        """
        执行一次 consume/produce 操作。

        1. 标记被消耗的事实 (consumed_by += operation)
        2. 添加新生产的事实 (produced_by = operation)
        3. 添加推导边
        4. 记录 consume/produce 历史
        """
        import time as _time

        new_facts_list = list(self.facts)
        for f in self.facts:
            if f.fingerprint in consumed_fps:
                idx = new_facts_list.index(f)
                new_facts_list[idx] = f.consume(operation)

        produced_with_source = []
        for pf in produced_facts:
            produced_fact = pf.produce(operation)
            produced_with_source.append(produced_fact)
            new_facts_list.append(produced_fact)

        new_edges = list(self.edges) + list(produced_edges)
        for consumed_fp in consumed_fps:
            for pf in produced_with_source:
                new_edges.append(FactEdge(
                    source_fp=consumed_fp,
                    target_fp=pf.fingerprint,
                    edge_type=FactEdgeType.DERIVES,
                    rule=operation,
                    confidence=pf.confidence,
                ))

        record = ConsumeProduceRecord(
            operation=operation,
            consumed_fps=consumed_fps,
            produced_fps=tuple(pf.fingerprint for pf in produced_with_source),
            timestamp=_time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        return FactGraph(
            facts=tuple(new_facts_list),
            edges=tuple(new_edges),
            records=self.records + (record,),
        )

    def operation_history(self, operation: str) -> tuple[ConsumeProduceRecord, ...]:
        return tuple(r for r in self.records if r.operation == operation)

    def invalidate_by_operation(self, operation: str, reason: str = "") -> FactGraph:
        produced_fps = set()
        for r in self.records:
            if r.operation == operation:
                produced_fps.update(r.produced_fps)
        new_graph = self
        for fp in produced_fps:
            new_graph = new_graph.cascade_invalidate(fp, reason or f"操作 {operation} 的结果被撤销")
        return new_graph

    def contradictions(self) -> tuple[tuple[Fact, Fact], ...]:
        result = []
        for e in self.edges:
            if e.edge_type == FactEdgeType.CONTRADICTS:
                f1 = self.fact_by_fp(e.source_fp)
                f2 = self.fact_by_fp(e.target_fp)
                if f1 and f2:
                    result.append((f1, f2))
        return tuple(result)

    def mark_contradiction(self, fp1: str, fp2: str, rule: str = "") -> FactGraph:
        edge1 = FactEdge(
            source_fp=fp1, target_fp=fp2,
            edge_type=FactEdgeType.CONTRADICTS, rule=rule,
        )
        edge2 = FactEdge(
            source_fp=fp2, target_fp=fp1,
            edge_type=FactEdgeType.CONTRADICTS, rule=rule,
        )
        return FactGraph(
            facts=self.facts,
            edges=self.edges + (edge1, edge2),
            records=self.records,
        )

    def to_dict(self) -> dict:
        d: dict = {}
        if self.facts:
            d["facts"] = [f.to_dict() for f in self.facts]
        if self.edges:
            d["edges"] = [e.to_dict() for e in self.edges]
        if self.records:
            d["records"] = [r.to_dict() for r in self.records]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> FactGraph:
        facts = tuple(Fact.from_dict(f) for f in d.get("facts", []))
        edges = tuple(FactEdge.from_dict(e) for e in d.get("edges", []))
        records = tuple(ConsumeProduceRecord.from_dict(r) for r in d.get("records", []))
        return cls(facts=facts, edges=edges, records=records)

    @classmethod
    def empty(cls) -> FactGraph:
        return cls()

    @classmethod
    def from_legacy_tuple(cls, facts: tuple) -> FactGraph:
        """
        从旧版 MathFact tuple 构建，自动映射 origin → fact_type。
        """
        new_facts = []
        for f in facts:
            ft = FactType.DERIVED
            if hasattr(f, "origin"):
                origin_name = f.origin.name if hasattr(f.origin, "name") else str(f.origin)
                origin_map = {
                    "ASSUMED": FactType.ASSUMPTION,
                    "GIVEN": FactType.ASSUMPTION,
                    "DERIVED": FactType.DERIVED,
                    "COMPUTED": FactType.DERIVED,
                    "INFERRED": FactType.DERIVED,
                    "AXIOM": FactType.THEOREM,
                }
                ft = origin_map.get(origin_name, FactType.DERIVED)
            new_facts.append(Fact(
                expression=f.expression,
                fact_type=ft,
                origin=FactOrigin[f.origin.name] if hasattr(f, "origin") and hasattr(f.origin, "name") else FactOrigin.DERIVED,
                source_operation=f.source_operation if hasattr(f, "source_operation") else "",
                dependencies=f.dependencies if hasattr(f, "dependencies") else (),
                confidence=f.confidence if hasattr(f, "confidence") else 1.0,
                justification=f.justification if hasattr(f, "justification") else "",
            ))
        edges = []
        fact_map = {f.fingerprint: f for f in new_facts}
        for f in new_facts:
            for dep in f.dependencies:
                if dep in fact_map:
                    edges.append(FactEdge(
                        source_fp=dep,
                        target_fp=f.fingerprint,
                        edge_type=FactEdgeType.DERIVES,
                        rule=f.source_operation,
                        confidence=f.confidence,
                    ))
        return cls(facts=tuple(new_facts), edges=tuple(edges))
