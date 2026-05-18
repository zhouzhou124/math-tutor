"""
Conflict Detector — 约束冲突检测器

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  约束冲突 = 后续推理全部污染的源头。

  必须：
    1. 在每一步操作后检测冲突
    2. 发现冲突立即报警
    3. 标记冲突约束
    4. 追溯冲突来源

  检测策略：
    - 规则匹配：使用 CONFLICT_RULES 快速检测已知矛盾模式
    - SymPy 验证：对符号约束做精确冲突检测
    - 传播检测：通过 INVALIDATES 边检测间接冲突
"""

from __future__ import annotations

from constraints.graph import (
    ConstraintGraph,
    ConstraintNode,
    ConstraintStatus,
    ConstraintRelation,
    ConflictReport,
)
from constraints.implication_rules import check_conflict


def detect_conflicts(graph: ConstraintGraph) -> ConflictReport:
    """
    检测约束图中的所有冲突。

    检测方式：
      1. 两两比较活跃约束，使用规则库检测矛盾
      2. 检查 INVALIDATES 边的间接冲突
      3. 标记冲突节点

    Returns:
        ConflictReport 包含冲突对和说明
    """
    conflicting_pairs = []
    explanations = []
    seen_pairs = set()

    active = graph.active_constraints()

    for i, node_a in enumerate(active):
        for j, node_b in enumerate(active):
            if i >= j:
                continue

            pair_key = (min(node_a.id, node_b.id), max(node_a.id, node_b.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            conflict_explanation = check_conflict(node_a.expression, node_b.expression)
            if conflict_explanation:
                conflicting_pairs.append((node_a.id, node_b.id))
                explanations.append(conflict_explanation)

                node_a.status = ConstraintStatus.CONFLICT
                node_b.status = ConstraintStatus.CONFLICT

    _detect_indirect_conflicts(graph, conflicting_pairs, explanations, seen_pairs)

    has_conflict = len(conflicting_pairs) > 0

    return ConflictReport(
        has_conflict=has_conflict,
        conflicting_pairs=conflicting_pairs,
        explanations=explanations,
    )


def _detect_indirect_conflicts(
    graph: ConstraintGraph,
    conflicting_pairs: list,
    explanations: list,
    seen_pairs: set,
) -> None:
    """
    检测通过 INVALIDATES / CONTRADICTS 边产生的间接冲突。
    """
    for edge in graph.edges:
        if edge.relation_type not in (ConstraintRelation.INVALIDATES, ConstraintRelation.CONTRADICTS):
            continue

        source = graph.get_node(edge.source_id)
        target = graph.get_node(edge.target_id)

        if not source or not target:
            continue
        if not source.is_active or not target.is_active:
            continue

        pair_key = (min(source.id, target.id), max(source.id, target.id))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        conflicting_pairs.append((source.id, target.id))
        if edge.relation_type == ConstraintRelation.CONTRADICTS:
            explanations.append(
                f"{source.expression} 与 {target.expression} 矛盾"
            )
        else:
            explanations.append(
                f"{source.expression} 否定了 {target.expression}"
            )

        source.status = ConstraintStatus.CONFLICT
        target.status = ConstraintStatus.CONFLICT
