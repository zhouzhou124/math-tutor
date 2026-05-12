"""
Graph Matching Engine v4 — 简化版 DAG 对齐

v4 原则:
  - 图匹配是加速器，不是主裁判
  - 不对依赖顺序扣分（学生写作顺序 ≠ 逻辑顺序）
  - 不对缺失步骤过度惩罚（学生常跳步）
  - 图匹配置信度低时，由 Engine B (LLM 语义) 兜底
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
from operations import ops_compatible


# ═══════════════════════════════════════════════
#  Graph utilities
# ═══════════════════════════════════════════════

def _build_nx_graph(sg: SolutionGraph):
    if not _HAS_NX:
        return None
    G = nx.DiGraph()
    for node in sg.nodes:
        G.add_node(node.id, type=node.type, label=node.label,
                   output=node.output, weight=node.weight)
    for edge in sg.edges:
        G.add_edge(edge.source, edge.target)
    return G


def _match_op_type(student_type: str, standard_type: str) -> bool:
    """宽松操作类型匹配（v4: 一切通过 ops_compatible）。"""
    return ops_compatible(student_type, standard_type)


# ═══════════════════════════════════════════════
#  Core: Simplified Graph Matching
# ═══════════════════════════════════════════════

def match_graphs(standard: SolutionGraph,
                 student_text: str,
                 student_graph: Optional[dict] = None,
                 student_trace: Optional[dict] = None) -> dict:
    """
    简化版图对齐。两维度评分：覆盖度 + 正确度。

    不做：依赖链惩罚、跳步惩罚、顺序惩罚。
    做：  宽松类型匹配 + 符号等价检查 + output 文本覆盖。

    Returns:
        {
            "matched_steps": [dict],   # 每个匹配到的步骤
            "missing_count": int,       # 未匹配到的标准步骤
            "coverage": float,          # 步骤覆盖度 (0-1)
            "correctness": float,       # 数学正确度 (0-1)
            "score": float,             # 综合分
            "max_score": float,
        }
    """
    std_nodes = {n.id: n for n in standard.nodes}
    matched_std = set()
    matched_steps = []  # list of matched info dicts

    # Parse student graph if not provided
    if student_graph is None:
        from symbolic_executor import build_student_graph
        student_graph = build_student_graph(student_text)
    student_nodes = student_graph.get("nodes", [])

    # ── Phase 1: Output-based matching (most robust) ──
    # 不关心 type，直接用学生 output 匹配标准 output
    for sn in student_nodes:
        stu_output = (sn.get("output") or sn.get("math_content") or "").strip()
        if not stu_output:
            continue
        for nid, std_node in std_nodes.items():
            if nid in matched_std:
                continue
            if not std_node.output:
                continue
            # 符号等价检查，失败时回退到字符串匹配
            result = symbolic_compare(stu_output, std_node.output)
            equivalent = result.get("equivalent", False)
            if not equivalent and _HAS_SYMPY is False:
                # 无 SymPy：做简单规范化后字符串比较
                def _norm(s):
                    return re.sub(r'\s+', '', s.lower().replace('$', ''))
                equivalent = _norm(stu_output) == _norm(std_node.output)
            if equivalent:
                matched_std.add(nid)
                matched_steps.append({
                    "node_id": nid,
                    "student_id": sn.get("id", ""),
                    "student_output": stu_output,
                    "standard_output": std_node.output,
                    "label": std_node.label or std_node.type,
                    "weight": std_node.weight,
                    "matched": True,
                    "match_method": "output_equivalent",
                })
                break

    # ── Phase 2: Type-based matching for remaining ──
    for sn in student_nodes:
        if any(ms.get("student_id") == sn.get("id") for ms in matched_steps):
            continue
        stu_type = sn.get("type", "")
        stu_output = (sn.get("output") or sn.get("math_content") or "").strip()

        for nid, std_node in std_nodes.items():
            if nid in matched_std:
                continue
            if _match_op_type(stu_type, std_node.type):
                # 符号重叠检查（宽松）
                if stu_output and std_node.output:
                    stu_syms = set(re.findall(r'[a-zA-Z]+|\\[a-zA-Z]+', stu_output))
                    std_syms = set(re.findall(r'[a-zA-Z]+|\\[a-zA-Z]+', std_node.output))
                    if stu_syms and std_syms and len(stu_syms & std_syms) >= 1:
                        matched_std.add(nid)
                        matched_steps.append({
                            "node_id": nid,
                            "student_id": sn.get("id", ""),
                            "student_output": stu_output,
                            "standard_output": std_node.output,
                            "label": std_node.label or std_node.type,
                            "weight": std_node.weight,
                            "matched": True,
                            "match_method": "type_symbol_overlap",
                        })
                        break

    # ── Step 2.5: Error Propagation Analysis ──
    # 找到根错误节点 → 下游级联节点不重复扣分
    missing_ids = set(std_nodes.keys()) - matched_std
    root_errors = set()       # 根因错误
    cascaded_errors = set()   # 级联错误（由上游错误导致）

    if missing_ids:
        # 构建节点依赖拓扑
        all_ids = std_nodes.keys()
        incoming = {nid: set() for nid in all_ids}
        for edge in standard.edges:
            if edge.target in incoming:
                incoming[edge.target].add(edge.source)

        for nid in missing_ids:
            # 如果所有前驱都已匹配 → 这是根错误
            preds = incoming.get(nid, set())
            if not preds or preds.issubset(matched_std):
                root_errors.add(nid)
            else:
                # 至少有一个前驱也缺失 → 可能是级联错误
                if preds & missing_ids:
                    cascaded_errors.add(nid)
                else:
                    root_errors.add(nid)

    # ── Scoring (3-dimension: graph + correctness + independent) ──
    total_weight = sum(n.weight for n in standard.nodes)
    matched_count = len(matched_std)
    matched_weight = sum(m.get("weight", 0) for m in matched_steps)

    # 级联节点权重折半
    cascaded_weight = sum(std_nodes[nid].weight for nid in cascaded_errors
                          if nid in std_nodes)
    effective_coverage = (matched_weight + cascaded_weight * 0.5) / max(total_weight, 0.01)
    coverage = min(effective_coverage, 1.0)

    # Correctness: 匹配到的步骤中数学正确的比例
    output_equiv_count = sum(1 for m in matched_steps
                             if m.get("match_method") == "output_equivalent")
    correctness = output_equiv_count / max(len(matched_steps), 1) if matched_steps else 0.0

    # ── Independent verification（不依赖 canonical trace）──
    # 使用 Derivation Validator 判断"推导是否合法"，而非"是否对齐标准解"
    if student_trace:
        from derivation_validator import validate_derivation
        dv = validate_derivation(student_text, student_trace)
        derivation_validity = dv["validity_score"]  # 0-1
    else:
        derivation_validity = _check_self_consistency(student_nodes)

    # 最终答案验证
    final_match = _check_final_answer(student_text, standard) if student_text else False

    # 独立验证分 = 推导合法性(60%) + 答案正确(40%)
    independent = (derivation_validity * 0.6 + (1.0 if final_match else 0.0) * 0.4)

    # Final score: canonical 参考 (70%) + independent 验证 (30%)
    # Canonical trace 是加速器，不是唯一真理
    canonical_score = (coverage * 0.5 + correctness * 0.5)
    score = (canonical_score * 0.7 + independent * 0.3) * standard.total_score

    return {
        "score": round(score, 1),
        "max_score": standard.total_score,
        "coverage": round(coverage, 2),
        "effective_coverage": round(effective_coverage, 2),
        "correctness": round(correctness, 2),
        "independent": round(independent, 2),
        "final_match": final_match,
        "self_consistency": round(self_consistency, 2),
        "canonical_score": round(canonical_score, 2),
        "matched_count": matched_count,
        "total_nodes": len(std_nodes.keys()),
        "missing_count": len(missing_ids),
        "matched_steps": matched_steps,
        "root_errors": sorted(root_errors - cascaded_errors),
        "cascaded_errors": sorted(cascaded_errors),
        "error_label": _score_label(coverage, correctness),
    }


def _check_final_answer(student_text: str, standard: SolutionGraph) -> bool:
    """
    独立验证：学生最终答案是否与标准答案等价。
    不依赖图匹配结果，只检查数学事实。
    """
    std_final = standard.final_answer or ""
    if not std_final or not student_text:
        return False
    # 取学生最后几行的数学内容
    import re
    lines = student_text.strip().split('\n')
    last_math = '\n'.join(lines[-3:])
    math_exprs = re.findall(r'\$([^$]+)\$', last_math)
    if not math_exprs:
        math_exprs = [last_math]
    student_final = math_exprs[-1].strip() if math_exprs else ""
    if not student_final:
        return False
    result = symbolic_compare(student_final, std_final)
    return result.get("equivalent", False)


def _check_self_consistency(student_nodes: list[dict]) -> float:
    """
    独立验证：学生自己的步骤是否内部自洽。
    检查相邻步骤的 output → input 链。
    返回 0.0 ~ 1.0。
    """
    if not student_nodes or len(student_nodes) < 2:
        return 1.0  # 单步或空，不扣分

    consistent = 0
    total = 0
    for i in range(1, len(student_nodes)):
        prev_out = (student_nodes[i - 1].get("output") or
                    student_nodes[i - 1].get("math_content") or "").strip()
        curr_inp = student_nodes[i].get("input_state", "").strip()

        # 有前一步输出和下一步输入 → 检查是否相关
        if prev_out and curr_inp:
            total += 1
            result = symbolic_compare(prev_out, curr_inp)
            if result.get("equivalent"):
                consistent += 1
            else:
                # 即使不等价，检查是否有共同的符号（可能有中间变形）
                prev_syms = set(re.findall(r'[a-zA-Z]+', prev_out))
                curr_syms = set(re.findall(r'[a-zA-Z]+', curr_inp))
                if prev_syms and curr_syms and len(prev_syms & curr_syms) >= 1:
                    consistent += 0.5  # 半匹配
        elif prev_out:
            # 有前一步输出但无显式 input_state → 检查是否包含数学符号
            total += 0.5
            if any(c in prev_out for c in '=∫∑∏√∂'):
                consistent += 0.3  # 有数学操作，部分自洽

    return consistent / max(total, 1)


def _score_label(coverage: float, correctness: float) -> str:
    """生成人类可读的评分标签。"""
    avg = (coverage + correctness) / 2
    if avg >= 0.9:
        return "解题完整，数学正确"
    elif avg >= 0.7:
        return "基本正确，部分步骤可完善"
    elif avg >= 0.5:
        return "部分正确，有步骤缺失或计算错误"
    elif avg >= 0.3:
        return "步骤不完整，存在多处错误"
    else:
        return "解题过程严重不完整"


# ═══════════════════════════════════════════════
#  Convenience wrappers
# ═══════════════════════════════════════════════

def grade_with_graph(student_text: str,
                     solution_graph: SolutionGraph,
                     student_graph: Optional[dict] = None,
                     student_trace: Optional[dict] = None) -> dict:
    """一站式图匹配评分。"""
    return match_graphs(solution_graph, student_text, student_graph, student_trace)


def diagnose_error_propagation(sg: SolutionGraph, graph_result: dict) -> dict:
    """
    错误传播分析（v4: 仅信息性，不影响评分）。
    返回: {severity, root_nodes, affected_nodes, cause}
    """
    matched_ids = set(m.get("node_id", "") for m in graph_result.get("matched_steps", []))
    all_ids = {n.id for n in sg.nodes}
    missing = all_ids - matched_ids

    if not missing:
        return {"severity": "none", "root_nodes": [], "affected_nodes": [], "cause": ""}

    # 找到缺失节点中"入度为0"的（根因）
    roots = []
    for nid in missing:
        is_root = True
        for edge in sg.edges:
            if edge.target == nid and edge.source not in missing:
                is_root = False
                break
        if is_root:
            roots.append(nid)

    severity = "high" if len(roots) >= 2 else "medium" if roots else "low"

    return {
        "severity": severity,
        "root_nodes": roots,
        "affected_nodes": sorted(missing),
        "cause": f"缺失 {len(missing)} 个步骤" if missing else "",
    }


# ═══════════════════════════════════════════════
#  DAG Topology Check
# ═══════════════════════════════════════════════

def check_topology(sg: SolutionGraph) -> dict:
    """验证 SolutionGraph 的 DAG 拓扑正确性。"""
    if not _HAS_NX:
        return {"valid": True, "reason": "无 NetworkX，跳过拓扑检查"}
    G = _build_nx_graph(sg)
    if G is None:
        return {"valid": True, "reason": "空图"}
    issues = []
    try:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            issues.append(f"发现循环: {cycles}")
    except Exception:
        pass
    isolated = [nid for nid in G.nodes if G.degree(nid) == 0]
    if isolated:
        issues.append(f"孤立节点: {isolated}")
    edge_refs = {e.source for e in sg.edges} | {e.target for e in sg.edges}
    missing = [n.id for n in sg.nodes if n.id not in edge_refs and n.id not in isolated]
    if missing:
        issues.append(f"边引用缺失节点: {missing}")
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "reason": "拓扑正确" if not issues else "; ".join(issues),
    }


# ═══════════════════════════════════════════════
#  Solution Graph Renderer (exam / teaching)
# ═══════════════════════════════════════════════

def render_solution_graph(sg: SolutionGraph, mode: str = "exam") -> str:
    """渲染解题图。exam 模式简洁，teaching 模式详细。"""
    lines = []
    if mode == "teaching":
        lines.append(f"## 解题步骤 (共 {len(sg.nodes)} 步，满分 {sg.total_score} 分)")
    else:
        lines.append(f"## 解答 (满分 {sg.total_score} 分)")

    for i, node in enumerate(sg.nodes, 1):
        if node.type == "final_answer":
            lines.append(f"\n### 最终答案")
            if node.output:
                lines.append(f"$${node.output}$$")
        else:
            prefix = f"{i}. " if mode == "exam" else f"### 步骤 {i}：{node.label or node.type}\n"
            lines.append(prefix)
            if node.output and mode == "teaching":
                lines.append(f"$${node.output}$$")
            if node.input_state and mode == "teaching":
                lines.append(f"输入：${node.input_state}$  → 输出：${node.output}$")
    return "\n".join(lines) if lines else "（空图）"
