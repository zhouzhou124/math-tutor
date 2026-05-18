"""
Constraint Propagation Engine — 约束传播引擎

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  从已有约束出发，自动推导隐含约束。

  传播层次:
    L1. 规则传播 — 使用蕴含规则库 (implication_rules)
    L2. 符号传播 — 使用 SymPy 做精确符号推理
    L3. 传递传播 — 利用 IMPLIES 边的传递闭包

  流程:
    1. 遍历所有活跃约束
    2. 对每个约束应用蕴含规则 (L1)
    3. 对每个约束尝试 SymPy 符号推导 (L2)
    4. 沿 IMPLIES 边做传递闭包 (L3)
    5. 自动建立 CONTRADICTS 边
    6. 迭代直到不动点

  安全措施:
    - 最大迭代次数限制
    - 置信度衰减
    - 去重
    - 约束数量上限
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
from constraints.implication_rules import apply_rules, normalize_constraint

_MAX_ITERATIONS = 10
_CONFIDENCE_DECAY = 0.9
_MAX_CONSTRAINTS = 200


def propagate_constraints(graph: ConstraintGraph) -> PropagationResult:
    """
    执行约束传播，推导隐含约束。

    三层传播:
      L1. 规则传播 — 蕴含规则库
      L2. 符号传播 — SymPy 精确推理
      L3. 传递传播 — IMPLIES 传递闭包

    Returns:
        PropagationResult 包含新增约束列表
    """
    added_nodes = []
    seen_expressions = {n.expression for n in graph.nodes.values()}

    for iteration in range(_MAX_ITERATIONS):
        if len(graph.nodes) >= _MAX_CONSTRAINTS:
            break

        new_in_this_round = []
        active = graph.active_constraints()

        for node in active:
            _propagate_rules(graph, node, seen_expressions, added_nodes, new_in_this_round)

        _propagate_symbolic(graph, seen_expressions, added_nodes, new_in_this_round)

        _propagate_transitive(graph, seen_expressions, added_nodes, new_in_this_round)

        _detect_contradiction_edges(graph)

        if not new_in_this_round:
            break

    return PropagationResult(added=added_nodes)


def _propagate_rules(
    graph: ConstraintGraph,
    node: ConstraintNode,
    seen_expressions: set[str],
    added_nodes: list[ConstraintNode],
    new_in_this_round: list[ConstraintNode],
) -> None:
    derived = apply_rules(node.expression)

    for derived_expr, relation_type, rule_name in derived:
        if derived_expr in seen_expressions:
            existing = graph._find_by_expression(derived_expr)
            if existing and existing.id != node.id:
                already_has_edge = any(
                    e.source_id == node.id
                    and e.target_id == existing.id
                    and e.relation_type == relation_type
                    for e in graph.edges
                )
                if not already_has_edge:
                    graph.add_relation(node.id, existing.id, relation_type, rule_name)
            continue

        if len(graph.nodes) >= _MAX_CONSTRAINTS:
            return

        new_confidence = node.confidence * _CONFIDENCE_DECAY
        new_id = graph.add_derived_constraint(
            derived_expr,
            source_step=f"propagated:{rule_name}",
            confidence=new_confidence,
        )
        graph.add_relation(node.id, new_id, relation_type, rule_name)

        new_node = graph.get_node(new_id)
        if new_node:
            new_in_this_round.append(new_node)
            added_nodes.append(new_node)
            seen_expressions.add(derived_expr)


def _propagate_symbolic(
    graph: ConstraintGraph,
    seen_expressions: set[str],
    added_nodes: list[ConstraintNode],
    new_in_this_round: list[ConstraintNode],
) -> None:
    try:
        import sympy as sp
    except ImportError:
        return

    active = graph.active_constraints()
    parsed = []
    for node in active:
        p = _parse_constraint_sympy(node.expression)
        if p is not None:
            parsed.append((node, p))

    if not parsed:
        return

    assumptions = _build_assumptions(parsed)

    for node, constraint in parsed:
        derived_list = _symbolic_derive(constraint, assumptions)
        for derived_expr, relation_type in derived_list:
            norm = normalize_constraint(derived_expr)
            if norm in seen_expressions:
                existing = graph._find_by_expression(norm)
                if existing and existing.id != node.id:
                    already_has_edge = any(
                        e.source_id == node.id
                        and e.target_id == existing.id
                        and e.relation_type == relation_type
                        for e in graph.edges
                    )
                    if not already_has_edge:
                        graph.add_relation(node.id, existing.id, relation_type, "symbolic")
                continue

            if len(graph.nodes) >= _MAX_CONSTRAINTS:
                return

            new_confidence = node.confidence * _CONFIDENCE_DECAY
            new_id = graph.add_derived_constraint(
                norm,
                source_step="propagated:symbolic",
                confidence=new_confidence,
            )
            graph.add_relation(node.id, new_id, relation_type, "symbolic")

            new_node = graph.get_node(new_id)
            if new_node:
                new_in_this_round.append(new_node)
                added_nodes.append(new_node)
                seen_expressions.add(norm)


def _propagate_transitive(
    graph: ConstraintGraph,
    seen_expressions: set[str],
    added_nodes: list[ConstraintNode],
    new_in_this_round: list[ConstraintNode],
) -> None:
    implies_edges = [
        e for e in graph.edges
        if e.relation_type == ConstraintRelation.IMPLIES
    ]

    for edge_a in implies_edges:
        for edge_b in implies_edges:
            if edge_a.target_id != edge_b.source_id:
                continue
            source_node = graph.get_node(edge_a.source_id)
            target_node = graph.get_node(edge_b.target_id)
            if not source_node or not target_node:
                continue
            if source_node.id == target_node.id:
                continue

            already_has_edge = any(
                e.source_id == source_node.id
                and e.target_id == target_node.id
                for e in graph.edges
            )
            if already_has_edge:
                continue

            graph.add_relation(
                source_node.id, target_node.id,
                ConstraintRelation.IMPLIES,
                "transitive",
            )

            if not target_node.is_active:
                continue

            if source_node.expression == target_node.expression:
                continue

            if check_implication_transitive(source_node, target_node, graph):
                if target_node.status in (ConstraintStatus.ACTIVE, ConstraintStatus.DERIVED):
                    target_node.status = ConstraintStatus.REDUNDANT


def _detect_contradiction_edges(graph: ConstraintGraph) -> None:
    from constraints.implication_rules import check_conflict

    active = graph.active_constraints()
    for i, node_a in enumerate(active):
        for j, node_b in enumerate(active):
            if i >= j:
                continue

            existing = any(
                e.source_id == node_a.id
                and e.target_id == node_b.id
                and e.relation_type == ConstraintRelation.CONTRADICTS
                for e in graph.edges
            )
            if existing:
                continue

            conflict = check_conflict(node_a.expression, node_b.expression)
            if conflict:
                graph.contradicts(node_a.id, node_b.id, label=conflict)


def check_implication_transitive(
    source: ConstraintNode,
    target: ConstraintNode,
    graph: ConstraintGraph,
) -> bool:
    from constraints.implication_rules import check_implication
    return check_implication(source.expression, target.expression)


def _parse_constraint_sympy(expr_str: str):
    try:
        import sympy as sp
    except ImportError:
        return None

    expr_str = expr_str.strip()
    expr_str = expr_str.replace("^", "**")

    for op_str, op_fn in [
        (">=", lambda a, b: a >= b),
        ("<=", lambda a, b: a <= b),
        (">", lambda a, b: a > b),
        ("<", lambda a, b: a < b),
        ("=", lambda a, b: sp.Eq(a, b)),
        ("≠", lambda a, b: sp.Ne(a, b)),
    ]:
        parts = expr_str.split(op_str, 1)
        if len(parts) == 2:
            try:
                left = sp.sympify(parts[0].strip())
                right = sp.sympify(parts[1].strip())
                return op_fn(left, right)
            except Exception:
                pass
    return None


def _build_assumptions(parsed: list) -> dict:
    try:
        import sympy as sp
    except ImportError:
        return {}

    assumptions = {}
    for node, constraint in parsed:
        free_syms = constraint.free_symbols
        for sym in free_syms:
            name = str(sym)
            if name not in assumptions:
                assumptions[name] = sym
    return assumptions


def _symbolic_derive(constraint, assumptions: dict) -> list[tuple[str, ConstraintRelation]]:
    try:
        import sympy as sp
    except ImportError:
        return []

    results = []
    try:
        free_syms = list(constraint.free_symbols)
        if not free_syms:
            return []

        for sym in free_syms:
            name = str(sym)

            if sp.ask(sp.Q.positive(sym), assumptions=constraint) is True:
                results.append((f"{name} > 0", ConstraintRelation.IMPLIES))
            elif sp.ask(sp.Q.negative(sym), assumptions=constraint) is True:
                results.append((f"{name} < 0", ConstraintRelation.IMPLIES))

            if sp.ask(sp.Q.zero(sym), assumptions=constraint) is True:
                results.append((f"{name} = 0", ConstraintRelation.IMPLIES))
            elif sp.ask(sp.Q.nonzero(sym), assumptions=constraint) is True:
                results.append((f"{name} ≠ 0", ConstraintRelation.IMPLIES))

            if sp.ask(sp.Q.real(sym), assumptions=constraint) is True:
                results.append((f"{name} ∈ R", ConstraintRelation.IMPLIES))

            if sp.ask(sp.Q.integer(sym), assumptions=constraint) is True:
                results.append((f"{name} ∈ Z", ConstraintRelation.IMPLIES))

    except Exception:
        pass

    return results
