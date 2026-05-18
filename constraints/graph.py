"""
ConstraintGraph — 约束传播图

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  约束之间不是扁平列表，而是存在推导关系的图结构。

  例如：
      x > 0  ──implies──>  x ≠ 0  ──implies──>  sqrt(x) 合法

  ConstraintGraph 将约束建模为有向图：
    - 节点 = 约束断言
    - 边   = 约束间关系（蕴含、等价、依赖、生成、否定）

  支持：
    - 约束传播（自动推导隐含约束）
    - 冗余删除（被蕴含的约束自动标记）
    - 等价合并（等价约束归为一组）
    - 冲突检测（矛盾约束立即报警）
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# 1. ConstraintRelation — 约束间关系类型
# ══════════════════════════════════════════════════════════════

class ConstraintRelation(Enum):
    IMPLIES = "implies"
    EQUIVALENT = "equivalent"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    GENERATED_BY = "generated_by"
    INVALIDATES = "invalidates"


# ══════════════════════════════════════════════════════════════
# 2. ConstraintStatus — 约束状态
# ══════════════════════════════════════════════════════════════

class ConstraintStatus(Enum):
    ACTIVE = "active"
    REDUNDANT = "redundant"
    CONFLICT = "conflict"
    DERIVED = "derived"
    ASSUMED = "assumed"
    INVALIDATED = "invalidated"


# ══════════════════════════════════════════════════════════════
# 3. ConstraintNode — 约束节点
# ══════════════════════════════════════════════════════════════

@dataclass
class ConstraintNode:
    id: str = ""
    expression: str = ""
    relation: str = ""
    source_step: str = ""
    confidence: float = 1.0
    status: ConstraintStatus = ConstraintStatus.ACTIVE

    def __post_init__(self):
        if not self.id:
            raw = f"{self.expression}:{self.relation}"
            self.id = "c_" + hashlib.md5(raw.encode()).hexdigest()[:8]

    @property
    def is_active(self) -> bool:
        return self.status == ConstraintStatus.ACTIVE

    @property
    def is_conflict(self) -> bool:
        return self.status == ConstraintStatus.CONFLICT

    @property
    def is_redundant(self) -> bool:
        return self.status == ConstraintStatus.REDUNDANT

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "expression": self.expression,
            "status": self.status.value,
        }
        if self.relation:
            d["relation"] = self.relation
        if self.source_step:
            d["source_step"] = self.source_step
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ConstraintNode:
        return cls(
            id=d.get("id", ""),
            expression=d.get("expression", ""),
            relation=d.get("relation", ""),
            source_step=d.get("source_step", ""),
            confidence=d.get("confidence", 1.0),
            status=ConstraintStatus(d.get("status", "active")),
        )


# ══════════════════════════════════════════════════════════════
# 4. ConstraintEdge — 约束边
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConstraintEdge:
    source_id: str = ""
    target_id: str = ""
    relation_type: ConstraintRelation = ConstraintRelation.IMPLIES
    label: str = ""

    def to_dict(self) -> dict:
        d = {
            "source": self.source_id,
            "target": self.target_id,
            "relation_type": self.relation_type.value,
        }
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ConstraintEdge:
        return cls(
            source_id=d.get("source", ""),
            target_id=d.get("target", ""),
            relation_type=ConstraintRelation(d.get("relation_type", "implies")),
            label=d.get("label", ""),
        )


# ══════════════════════════════════════════════════════════════
# 5. ConflictReport — 冲突报告
# ══════════════════════════════════════════════════════════════

@dataclass
class ConflictReport:
    has_conflict: bool = False
    conflicting_pairs: list[tuple[str, str]] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "has_conflict": self.has_conflict,
            "conflicting_pairs": self.conflicting_pairs,
            "explanations": self.explanations,
        }


# ══════════════════════════════════════════════════════════════
# 6. PropagationResult — 传播结果
# ══════════════════════════════════════════════════════════════

@dataclass
class PropagationResult:
    added: list[ConstraintNode] = field(default_factory=list)
    removed_redundant: list[str] = field(default_factory=list)
    merged_equivalent: list[tuple[str, str]] = field(default_factory=list)
    conflicts: ConflictReport = field(default_factory=ConflictReport)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed_redundant or self.merged_equivalent or self.conflicts.has_conflict)

    def to_dict(self) -> dict:
        return {
            "added": [n.to_dict() for n in self.added],
            "removed_redundant": self.removed_redundant,
            "merged_equivalent": self.merged_equivalent,
            "conflicts": self.conflicts.to_dict(),
        }


# ══════════════════════════════════════════════════════════════
# 7. ConstraintGraph — 约束传播图
# ══════════════════════════════════════════════════════════════

class ConstraintGraph:
    """
    约束传播图 — 将约束建模为有向图结构。

    核心能力：
      - add_constraint(): 添加约束节点
      - add_relation(): 添加约束间关系
      - propagate(): 执行约束传播（推导隐含约束）
      - simplify(): 删除冗余 + 合并等价
      - detect_conflicts(): 检测矛盾约束
      - active_constraints(): 获取所有活跃约束
    """

    def __init__(self):
        self.nodes: dict[str, ConstraintNode] = {}
        self.edges: list[ConstraintEdge] = []

    def add_constraint(self, expression: str, relation: str = "",
                       source_step: str = "", confidence: float = 1.0,
                       status: ConstraintStatus = ConstraintStatus.ACTIVE) -> str:
        existing = self._find_by_expression(expression)
        if existing:
            return existing.id

        node = ConstraintNode(
            expression=expression,
            relation=relation,
            source_step=source_step,
            confidence=confidence,
            status=status,
        )
        self.nodes[node.id] = node
        return node.id

    def add_assumed_constraint(self, expression: str, source_step: str = "") -> str:
        return self.add_constraint(
            expression=expression,
            source_step=source_step,
            status=ConstraintStatus.ASSUMED,
        )

    def add_derived_constraint(self, expression: str, source_step: str = "",
                               confidence: float = 0.9) -> str:
        return self.add_constraint(
            expression=expression,
            source_step=source_step,
            confidence=confidence,
            status=ConstraintStatus.DERIVED,
        )

    def add_relation(self, source_id: str, target_id: str,
                     relation_type: ConstraintRelation = ConstraintRelation.IMPLIES,
                     label: str = "") -> None:
        if source_id not in self.nodes or target_id not in self.nodes:
            return
        for e in self.edges:
            if e.source_id == source_id and e.target_id == target_id and e.relation_type == relation_type:
                return
        self.edges.append(ConstraintEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            label=label,
        ))
        if relation_type == ConstraintRelation.EQUIVALENT:
            self.edges.append(ConstraintEdge(
                source_id=target_id,
                target_id=source_id,
                relation_type=ConstraintRelation.EQUIVALENT,
                label=label,
            ))

    def implies(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.IMPLIES, label)

    def equivalent(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.EQUIVALENT, label)

    def depends_on(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.DEPENDS_ON, label)

    def generated_by(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.GENERATED_BY, label)

    def invalidates(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.INVALIDATES, label)

    def contradicts(self, source_id: str, target_id: str, label: str = "") -> None:
        self.add_relation(source_id, target_id, ConstraintRelation.CONTRADICTS, label)
        self.add_relation(target_id, source_id, ConstraintRelation.CONTRADICTS, label)

    def get_node(self, node_id: str) -> Optional[ConstraintNode]:
        return self.nodes.get(node_id)

    def get_implied_by(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.target_id == node_id and e.relation_type == ConstraintRelation.IMPLIES:
                result.append(e.source_id)
        return result

    def get_implied_targets(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.source_id == node_id and e.relation_type == ConstraintRelation.IMPLIES:
                result.append(e.target_id)
        return result

    def get_equivalents(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if (e.source_id == node_id or e.target_id == node_id) and e.relation_type == ConstraintRelation.EQUIVALENT:
                other = e.target_id if e.source_id == node_id else e.source_id
                if other != node_id and other not in result:
                    result.append(other)
        return result

    def get_invalidated_by(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.source_id == node_id and e.relation_type == ConstraintRelation.INVALIDATES:
                result.append(e.target_id)
        return result

    def get_contradictions(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.source_id == node_id and e.relation_type == ConstraintRelation.CONTRADICTS:
                other = e.target_id
                if other not in result:
                    result.append(other)
        return result

    def get_dependents(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.target_id == node_id and e.relation_type == ConstraintRelation.DEPENDS_ON:
                result.append(e.source_id)
        return result

    def get_generated_by(self, node_id: str) -> list[str]:
        result = []
        for e in self.edges:
            if e.source_id == node_id and e.relation_type == ConstraintRelation.GENERATED_BY:
                result.append(e.target_id)
        return result

    def active_constraints(self) -> list[ConstraintNode]:
        return [n for n in self.nodes.values()
                if n.status in (ConstraintStatus.ACTIVE, ConstraintStatus.ASSUMED, ConstraintStatus.DERIVED)]

    def all_constraints(self) -> list[ConstraintNode]:
        return list(self.nodes.values())

    def active_expressions(self) -> list[str]:
        return [n.expression for n in self.active_constraints()]

    def propagate(self) -> PropagationResult:
        from constraints.propagation import propagate_constraints
        return propagate_constraints(self)

    def simplify(self) -> PropagationResult:
        from constraints.simplifier import simplify_graph
        return simplify_graph(self)

    def detect_conflicts(self) -> ConflictReport:
        from constraints.conflict_detector import detect_conflicts
        return detect_conflicts(self)

    def full_process(self) -> PropagationResult:
        prop_result = self.propagate()
        simp_result = self.simplify()
        conflict_report = self.detect_conflicts()

        return PropagationResult(
            added=prop_result.added,
            removed_redundant=simp_result.removed_redundant,
            merged_equivalent=simp_result.merged_equivalent,
            conflicts=conflict_report,
        )

    def _find_by_expression(self, expression: str) -> Optional[ConstraintNode]:
        for n in self.nodes.values():
            if n.expression == expression:
                return n
        return None

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ConstraintGraph:
        graph = cls()
        for nd in d.get("nodes", []):
            node = ConstraintNode.from_dict(nd)
            graph.nodes[node.id] = node
        for ed in d.get("edges", []):
            graph.edges.append(ConstraintEdge.from_dict(ed))
        return graph

    @classmethod
    def from_strings(cls, constraints: list[str], source_step: str = "") -> ConstraintGraph:
        graph = cls()
        for c in constraints:
            graph.add_constraint(c, source_step=source_step)
        return graph

    def to_string_list(self) -> list[str]:
        return self.active_expressions()

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        status_style = {
            ConstraintStatus.ACTIVE: "style fill:#D1FAE5,stroke:#059669",
            ConstraintStatus.ASSUMED: "style fill:#FEF3C7,stroke:#D97706",
            ConstraintStatus.DERIVED: "style fill:#E0E7FF,stroke:#4F46E5",
            ConstraintStatus.REDUNDANT: "style fill:#F3F4F6,stroke:#9CA3AF",
            ConstraintStatus.CONFLICT: "style fill:#FEE2E2,stroke:#DC2626",
            ConstraintStatus.INVALIDATED: "style fill:#F9FAFB,stroke:#6B7280",
        }
        for n in self.nodes.values():
            label = n.expression.replace('"', "'")
            lines.append(f'    {n.id}["{label}"]')
            style = status_style.get(n.status)
            if style:
                lines.append(f'    {n.id} {style}')
        for e in self.edges:
            arrow_map = {
                ConstraintRelation.IMPLIES: "-->",
                ConstraintRelation.EQUIVALENT: "---",
                ConstraintRelation.DEPENDS_ON: "-.->",
                ConstraintRelation.CONTRADICTS: "-x->",
                ConstraintRelation.GENERATED_BY: "==>",
                ConstraintRelation.INVALIDATES: "-x->",
            }
            arrow = arrow_map.get(e.relation_type, "-->")
            edge_label = f"|{e.relation_type.value}|" if not e.label else f"|{e.label}|"
            lines.append(f'    {e.source_id} {arrow}{edge_label} {e.target_id}')
        return "\n".join(lines)

    def __repr__(self) -> str:
        active = len(self.active_constraints())
        total = len(self.nodes)
        return f"ConstraintGraph(nodes={total}, active={active}, edges={len(self.edges)})"
