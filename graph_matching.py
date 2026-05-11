"""
Graph Matching Engine v3.3 — NetworkX-based DAG alignment

核心: 不再比较"节点列表", 而是比较"解题拓扑结构"
- 类型匹配 (diff vs diff)
- 符号等价 (SymPy simplify)
- 依赖链验证 (求导→驻点→Hessian)
"""
import re
from typing import Optional
from solution_graph import SolutionGraph, GraphNode, GraphEdge

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    nx = None
    _HAS_NX = False

from symbolic_executor import (_HAS_SYMPY, ErrorLevel,
                                parse_expression, symbolic_compare)


# ═══════════════════════════════════════════════
# Graph utilities
# ═══════════════════════════════════════════════

def _build_nx_graph(sg: SolutionGraph):
    """Convert SolutionGraph to NetworkX DiGraph."""
    if not _HAS_NX:
        return None
    G = nx.DiGraph()
    for node in sg.nodes:
        G.add_node(node.id, type=node.type, label=node.label,
                   output=node.output, weight=node.weight,
                   required=node.required)
    for edge in sg.edges:
        G.add_edge(edge.source, edge.target)
    return G


def _match_node_type(student_type: str, standard_type: str) -> bool:
    """宽松类型匹配: 允许相近操作类型匹配"""
    if student_type == standard_type:
        return True
    # Equivalent types
    equivalents = {
        "differentiate": ["differentiate", "compute_derivative", "diff"],
        "solve_system": ["solve_system", "solve", "find_roots"],
        "hessian_test": ["hessian_test", "classify", "classify_critical"],
        "integrate": ["integrate", "compute_integral", "int"],
        "eigen_solve": ["eigen_solve", "eigenvalue", "diagonalize"],
        "apply_theorem": ["apply_theorem", "theorem", "prove"],
        "final_answer": ["final_answer", "conclusion", "result"],
    }
    for canonical, aliases in equivalents.items():
        if student_type in aliases and standard_type in aliases:
            return True
    return False


# ═══════════════════════════════════════════════
# DAG-aware Graph Matching
# ═══════════════════════════════════════════════

def match_graphs(standard: SolutionGraph,
                 student_text: str,
                 student_graph: Optional[dict] = None) -> dict:
    """
    DAG级图对齐: 比较标准解题图与学生解题图。

    Returns:
        {
            "alignment_score": float,
            "matched": [str],
            "missing": [str],
            "extra": [str],
            "dependency_broken": [str],
            "structure_score": float,
            "execution_score": float,
            "total_score": float,
            "error_level": int,
        }
    """
    std_nodes = {n.id: n for n in standard.nodes}
    std_ids = set(std_nodes.keys())

    # Parse student graph if not provided
    if student_graph is None:
        from symbolic_executor import build_student_graph
        student_graph = build_student_graph(student_text)

    student_nodes = student_graph.get("nodes", [])

    # ── Step 1: Node type matching ──
    matched_std = set()
    matched_stu = []

    for sn in student_nodes:
        stu_type = sn.get("type", "")
        for nid, std_node in std_nodes.items():
            if nid in matched_std:
                continue
            if _match_node_type(stu_type, std_node.type):
                # Type matched — now check symbolic equivalence if math available
                if sn.get("math_content") and std_node.output:
                    result = symbolic_compare(sn["math_content"], std_node.output)
                    if result["equivalent"]:
                        matched_std.add(nid)
                        matched_stu.append((sn["id"], nid, result))
                        break
                elif not sn.get("math_content"):
                    # Student identified the step type but has no math → partial credit
                    matched_std.add(nid)
                    matched_stu.append((sn["id"], nid, None))
                    break

    missing = [nid for nid in std_ids if nid not in matched_std]
    extra = [sn["id"] for sn in student_nodes
             if not any(sn["id"] == ms[0] for ms in matched_stu)]

    # ── Step 2: Dependency chain check ──
    dependency_broken = []
    if _HAS_NX:
        G = _build_nx_graph(standard)
        if G:
            for nid in matched_std:
                predecessors = list(G.predecessors(nid))
                for pred in predecessors:
                    if pred not in matched_std:
                        dependency_broken.append(f"{pred}→{nid}")
                        break

    # ── Step 3: Scoring ──
    total_weight = sum(n.weight for n in standard.nodes)
    matched_weight = sum(std_nodes[nid].weight for nid in matched_std)

    # Execution score: did student produce correct math?
    exec_matches = sum(1 for _, _, r in matched_stu if r and r.get("equivalent"))
    exec_score = exec_matches / max(len(student_nodes), 1)

    # Structure score: are dependencies satisfied?
    struct_penalty = len(dependency_broken) * 0.15
    struct_score = max(0, matched_weight / max(total_weight, 0.01) - struct_penalty)

    # Alignment score
    alignment = len(matched_std) / max(len(std_ids), 1)

    if all(not sn.get("has_math", False) for sn in student_nodes) and len(student_nodes) > 0:
        error_level = ErrorLevel.LEVEL_0
    elif len(missing) > 0 and exec_score < 0.5:
        error_level = ErrorLevel.LEVEL_1
    elif dependency_broken:
        error_level = ErrorLevel.LEVEL_2
    else:
        error_level = ErrorLevel.CORRECT

    return {
        "alignment_score": round(alignment, 2),
        "matched": sorted(matched_std),
        "matched_pairs": matched_stu,
        "missing": missing,
        "extra": extra,
        "dependency_broken": dependency_broken,
        "structure_score": round(struct_score, 2),
        "execution_score": round(exec_score, 2),
        "total_score": round(min(struct_score + exec_score * 0.3, 1.0) * standard.total_score, 1),
        "max_score": standard.total_score,
        "error_level": error_level,
    }


# ═══════════════════════════════════════════════
# Quick DAG Topology Check
# ═══════════════════════════════════════════════

def check_topology(sg: SolutionGraph) -> dict:
    """验证 SolutionGraph 的 DAG 拓扑正确性"""
    issues = []
    # Check no cycles (should be a DAG)
    if _HAS_NX:
        G = _build_nx_graph(sg)
        if G:
            try:
                cycles = list(nx.simple_cycles(G))
                if cycles:
                    issues.append(f"DAG has cycles: {cycles}")
            except nx.NetworkXError as e:
                issues.append(f"Graph error: {e}")

    # Check all edge references valid
    node_ids = {n.id for n in sg.nodes}
    for edge in sg.edges:
        if edge.source not in node_ids:
            issues.append(f"Edge source {edge.source} not in nodes")
        if edge.target not in node_ids:
            issues.append(f"Edge target {edge.target} not in nodes")

    # Check no isolated nodes (unless single-step)
    if len(sg.nodes) > 1:
        connected = set()
        for e in sg.edges:
            connected.add(e.source)
            connected.add(e.target)
        isolated = node_ids - connected
        if isolated:
            issues.append(f"Isolated nodes (no edges): {isolated}")

    return {"valid": len(issues) == 0, "issues": issues}


# ═══════════════════════════════════════════════
# Scoring integration helper
# ═══════════════════════════════════════════════

def grade_with_graph(student_text: str,
                     solution_graph: SolutionGraph,
                     student_graph: Optional[dict] = None) -> dict:
    """
    One-shot grading: text → graph match → score + explanation.
    Wraps the full pipeline for API use.
    """
    # Edge case: empty answer → all nodes missing
    if not student_text or not student_text.strip():
        return {
            "score": 0.0,
            "max_score": solution_graph.total_score,
            "error_level": ErrorLevel.LEVEL_0,
            "error_label": ErrorLevel.LABELS[ErrorLevel.LEVEL_0],
            "matched_steps": [],
            "missing_steps": [n.id for n in solution_graph.nodes],
            "dependency_broken": [],
            "structure_score": 0.0,
            "execution_score": 0.0,
        }

    result = match_graphs(solution_graph, student_text, student_graph)

    return {
        "score": result["total_score"],
        "max_score": result["max_score"],
        "error_level": result["error_level"],
        "error_label": ErrorLevel.LABELS.get(result["error_level"], "未知"),
        "matched_steps": result["matched"],
        "missing_steps": result["missing"],
        "dependency_broken": result["dependency_broken"],
        "structure_score": result["structure_score"],
        "execution_score": result["execution_score"],
    }


# ═══════════════════════════════════════════════
# v4: Error Propagation Graph
# ═══════════════════════════════════════════════

def diagnose_error_propagation(solution_graph: SolutionGraph,
                               match_result: dict) -> dict:
    """
    v4核心: 错误不是"点", 而是"路径断裂".

    分析 missing step 对后续步骤的级联影响 (propagation).
    """
    std_nodes = {n.id: n for n in solution_graph.nodes}
    # Accept both "missing" and "missing_steps" keys
    missing = set(match_result.get("missing_steps", match_result.get("missing", [])))
    broken_edges = match_result.get("dependency_broken", [])

    # Compute propagation: which later steps are impacted by each missing step?
    propagation = {}
    for nid in missing:
        impacted = set()
        # Find all downstream nodes that depend on this node
        for edge in solution_graph.edges:
            if edge.source == nid:
                impacted.add(edge.target)
                # Recursively find transitive dependencies
                queue = [edge.target]
                while queue:
                    curr = queue.pop(0)
                    for e in solution_graph.edges:
                        if e.source == curr:
                            impacted.add(e.target)
                            queue.append(e.target)
        propagation[nid] = sorted(impacted)

    # Classify error severity
    if not missing and not broken_edges:
        severity = "none"
        error_type = "correct"
    elif len(missing) <= 1 and not broken_edges:
        severity = "low"
        error_type = "node_error"
    elif broken_edges:
        severity = "high"
        error_type = "methodology_failure"
    else:
        severity = "medium"
        error_type = "edge_break"

    # Find root cause
    root_nodes = []
    for nid in missing:
        is_root = True
        for edge in solution_graph.edges:
            if edge.target == nid and edge.source in missing:
                is_root = False
                break
        if is_root:
            root_nodes.append(nid)

    return {
        "error_type": error_type,
        "severity": severity,
        "root_nodes": root_nodes,
        "propagation": propagation,
        "broken_edges": broken_edges,
        "cause": (
            "method not recognized" if error_type == "methodology_failure" else
            "step computation error" if error_type == "node_error" else
            "derivation chain broken" if error_type == "edge_break" else
            "all steps correct"
        ),
    }


# ═══════════════════════════════════════════════
# v4: Dual-mode renderer (Exam / Teaching)
# ═══════════════════════════════════════════════

def render_solution_graph(sg: SolutionGraph,
                          mode: str = "teaching") -> dict:
    """
    v4 UI双模渲染:
    - exam:    紧凑 → 答案 + 关键步骤
    - teaching: 展开 → 完整推导树 + 每步解释
    """
    if mode == "exam":
        return {
            "mode": "exam",
            "final_answer": sg.final_answer,
            "key_steps": [
                {"step": i+1, "label": n.label}
                for i, n in enumerate(sg.nodes) if n.type in
                ("final_answer", "conclude", "solve", "eigen_solve")
            ],
            "total_steps": len(sg.nodes),
        }
    else:
        return {
            "mode": "teaching",
            "final_answer": sg.final_answer,
            "steps": [
                {
                    "step": i+1,
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "output": n.output,
                    "depends_on": n.input_refs,
                    "weight": n.weight,
                }
                for i, n in enumerate(sg.nodes)
            ],
            "edges": [[e.source, e.target] for e in sg.edges],
            "total_steps": len(sg.nodes),
        }
