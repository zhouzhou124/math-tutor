"""
Constraint Simplifier — 约束简化器

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  约束图中存在大量冗余和等价，需要简化。
  否则约束会爆炸。

  简化操作:
    1. 冗余删除: 如果 A 蕴含 B，则 B 是冗余的
       例: x > 0 蕴含 x ≠ 0 → 删除 x ≠ 0

    2. 等价合并: 如果 A 等价于 B，合并为一个代表
       例: |x| = x 等价于 x ≥ 0 → 保留 x ≥ 0

    3. 语义合并: 同一变量的多个约束合并为最强约束
       例: x > 0 + x ≠ 0 → x > 0 (更强蕴含更弱)

    4. 传递简化: 利用传递闭包删除中间节点
       例: A→B→C 且 A→C → B 可标记冗余

    5. 无效标记: 被 INVALIDATES/CONTRADICTS 边指向的约束标记

    6. 爆炸防护: 约束数量超过阈值时自动清理最弱约束

  原则:
    - 保留信息量最大的约束 (strict > non-strict > nonzero)
    - 保留原始约束 (ASSUMED/ACTIVE 优先于 DERIVED)
    - 删除被蕴含的弱约束
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from constraints.graph import (
    ConstraintGraph,
    ConstraintNode,
    ConstraintStatus,
    ConstraintRelation,
    PropagationResult,
)
from constraints.implication_rules import check_implication, check_equivalence


_PRIORITY = {
    ConstraintStatus.ASSUMED: 3,
    ConstraintStatus.ACTIVE: 2,
    ConstraintStatus.DERIVED: 1,
    ConstraintStatus.REDUNDANT: 0,
    ConstraintStatus.CONFLICT: 0,
    ConstraintStatus.INVALIDATED: 0,
}

_STRENGTH = {
    "strict_pos": 5,
    "strict_neg": 5,
    "nonneg": 4,
    "nonpos": 4,
    "nonzero": 3,
    "equality": 2,
    "set_membership": 1,
    "general": 0,
}

_MAX_ACTIVE_CONSTRAINTS = 50


def simplify_graph(graph: ConstraintGraph) -> PropagationResult:
    """
    简化约束图: 删除冗余 + 合并等价 + 语义合并 + 传递简化 + 爆炸防护。

    Returns:
        PropagationResult 包含被删除的冗余约束和被合并的等价对
    """
    removed_redundant = []
    merged_equivalent = []

    _mark_invalidated(graph)
    _mark_contradicted(graph)

    _semantic_merge(graph, removed_redundant, merged_equivalent)

    active = graph.active_constraints()
    for i, node_a in enumerate(active):
        if node_a.status not in (ConstraintStatus.ACTIVE, ConstraintStatus.ASSUMED, ConstraintStatus.DERIVED):
            continue
        for j, node_b in enumerate(active):
            if i >= j:
                continue
            if node_b.status not in (ConstraintStatus.ACTIVE, ConstraintStatus.ASSUMED, ConstraintStatus.DERIVED):
                continue

            if check_equivalence(node_a.expression, node_b.expression):
                survivor, removed = _choose_survivor(node_a, node_b)
                if survivor and removed:
                    graph.equivalent(survivor.id, removed.id)
                    removed.status = ConstraintStatus.REDUNDANT
                    removed_redundant.append(removed.id)
                    merged_equivalent.append((survivor.id, removed.id))
                    continue

            if check_implication(node_a.expression, node_b.expression):
                node_b.status = ConstraintStatus.REDUNDANT
                removed_redundant.append(node_b.id)
                graph.implies(node_a.id, node_b.id)
                continue

            if check_implication(node_b.expression, node_a.expression):
                node_a.status = ConstraintStatus.REDUNDANT
                removed_redundant.append(node_a.id)
                graph.implies(node_b.id, node_a.id)
                continue

    _transitive_simplify(graph, removed_redundant)

    _explosion_protection(graph, removed_redundant)

    return PropagationResult(
        removed_redundant=removed_redundant,
        merged_equivalent=merged_equivalent,
    )


def _mark_invalidated(graph: ConstraintGraph) -> None:
    for edge in graph.edges:
        if edge.relation_type == ConstraintRelation.INVALIDATES:
            target = graph.get_node(edge.target_id)
            if target and target.is_active:
                target.status = ConstraintStatus.INVALIDATED


def _mark_contradicted(graph: ConstraintGraph) -> None:
    for edge in graph.edges:
        if edge.relation_type == ConstraintRelation.CONTRADICTS:
            source = graph.get_node(edge.source_id)
            target = graph.get_node(edge.target_id)
            if source and target and source.is_active and target.is_active:
                source.status = ConstraintStatus.CONFLICT
                target.status = ConstraintStatus.CONFLICT


def _semantic_merge(
    graph: ConstraintGraph,
    removed_redundant: list[str],
    merged_equivalent: list[tuple[str, str]],
) -> None:
    """
    语义合并 — 同一变量的多个约束合并为最强约束。

    例: x > 0 + x ≠ 0 → x > 0 (更强蕴含更弱)
    例: x > 0 + x ≥ 0 → x > 0 (strict > non-strict)
    """
    var_groups: dict[str, list[ConstraintNode]] = {}
    for node in graph.active_constraints():
        var = _extract_variable(node.expression)
        if var:
            if var not in var_groups:
                var_groups[var] = []
            var_groups[var].append(node)

    for var, nodes in var_groups.items():
        if len(nodes) <= 1:
            continue

        ranked = sorted(nodes, key=lambda n: (
            _PRIORITY.get(n.status, 0),
            _constraint_strength(n.expression),
        ), reverse=True)

        strongest = ranked[0]
        for weaker in ranked[1:]:
            if check_implication(strongest.expression, weaker.expression):
                weaker.status = ConstraintStatus.REDUNDANT
                removed_redundant.append(weaker.id)
                graph.implies(strongest.id, weaker.id)
                merged_equivalent.append((strongest.id, weaker.id))


def _transitive_simplify(
    graph: ConstraintGraph,
    removed_redundant: list[str],
) -> None:
    """
    传递简化 — 利用传递闭包删除中间节点。

    如果 A→B→C 且 A→C (直接边)，则 B 在 A→C 路径上是冗余的。
    """
    implies_edges = [
        e for e in graph.edges
        if e.relation_type == ConstraintRelation.IMPLIES
    ]

    for edge in implies_edges:
        source = graph.get_node(edge.source_id)
        target = graph.get_node(edge.target_id)
        if not source or not target:
            continue

        intermediate_edges = [
            e for e in implies_edges
            if e.source_id == edge.source_id and e.target_id != edge.target_id
        ]

        for mid_edge in intermediate_edges:
            mid_node = graph.get_node(mid_edge.target_id)
            if not mid_node:
                continue

            has_path = any(
                e.source_id == mid_node.id and e.target_id == edge.target_id
                for e in implies_edges
            )

            if has_path and mid_node.status == ConstraintStatus.DERIVED:
                if check_implication(source.expression, target.expression):
                    mid_node.status = ConstraintStatus.REDUNDANT
                    if mid_node.id not in removed_redundant:
                        removed_redundant.append(mid_node.id)


def _explosion_protection(
    graph: ConstraintGraph,
    removed_redundant: list[str],
) -> None:
    """
    爆炸防护 — 约束数量超过阈值时自动清理最弱约束。

    清理策略:
      1. 先清理 DERIVED + 低置信度
      2. 再清理 DERIVED + 高置信度
      3. 不清理 ASSUMED/ACTIVE
    """
    active = graph.active_constraints()
    if len(active) <= _MAX_ACTIVE_CONSTRAINTS:
        return

    derived = [n for n in active if n.status == ConstraintStatus.DERIVED]
    derived.sort(key=lambda n: n.confidence)

    to_remove = len(active) - _MAX_ACTIVE_CONSTRAINTS
    for node in derived[:to_remove]:
        node.status = ConstraintStatus.REDUNDANT
        removed_redundant.append(node.id)


def _extract_variable(expression: str) -> str:
    import re
    m = re.match(r"^(\w+)\s*[><=≠≥≤]", expression.strip())
    if m:
        return m.group(1)
    m = re.match(r"^(\w+)\s*∈", expression.strip())
    if m:
        return m.group(1)
    return ""


def _constraint_strength(expression: str) -> int:
    expr = expression.strip()

    if ">" in expr and "≥" not in expr:
        return _STRENGTH["strict_pos"]
    if "<" in expr and "≤" not in expr:
        return _STRENGTH["strict_neg"]
    if "≥" in expr:
        return _STRENGTH["nonneg"]
    if "≤" in expr:
        return _STRENGTH["nonpos"]
    if "≠" in expr:
        return _STRENGTH["nonzero"]
    if "=" in expr and "≠" not in expr:
        return _STRENGTH["equality"]
    if "∈" in expr:
        return _STRENGTH["set_membership"]

    return _STRENGTH["general"]


def _choose_survivor(a: ConstraintNode, b: ConstraintNode) -> tuple[ConstraintNode, ConstraintNode]:
    pa = _PRIORITY.get(a.status, 0)
    pb = _PRIORITY.get(b.status, 0)

    if pa > pb:
        return a, b
    if pb > pa:
        return b, a

    sa = _constraint_strength(a.expression)
    sb = _constraint_strength(b.expression)
    if sa > sb:
        return a, b
    if sb > sa:
        return b, a

    la = len(a.expression)
    lb = len(b.expression)
    if la <= lb:
        return a, b
    return b, a
