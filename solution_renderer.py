"""
SolutionRenderer — 将 CanonicalSolutionTrace 渲染为教学式步骤展示

核心职责：
  - CanonicalTrace → 教学式 Markdown（带直觉/为什么/替代方案）
  - 步骤树渲染
  - 方法切换渲染
  - 评分点可视化
"""

from solution_graph import CanonicalSolutionTrace, SolutionMethod, GraphNode


def render_method_overview(method: SolutionMethod) -> dict:
    """渲染方法总览信息。"""
    nodes = method.graph.nodes
    proc_nodes = [n for n in nodes if n.type != "final_answer"]
    final_node = next((n for n in nodes if n.type == "final_answer"), None)

    return {
        "method_name": method.method_name,
        "step_count": len(proc_nodes),
        "total_score": method.graph.total_score,
        "final_answer": method.final_answer,
        "knowledge_points": method.knowledge_points,
        "common_mistakes": method.common_mistakes,
        "fingerprint": method.fingerprint,
    }


def render_step(step: GraphNode, step_index: int) -> dict:
    """将单个 GraphNode 渲染为教学式步骤信息。"""
    info = {
        "index": step_index + 1,
        "id": step.id,
        "label": step.label or "",
        "type": step.type,
        "operation": step.operation or step.type,
        "weight": step.weight,
    }

    if step.input_state:
        info["input_state"] = step.input_state
    if step.output:
        info["output_state"] = step.output

    # 推断步骤类型中文名
    info["type_cn"] = _op_type_cn(step.operation or step.type)

    # 生成教学解释
    info["explanation"] = _generate_explanation(step)

    return info


def render_solution_chain(method: SolutionMethod) -> list[dict]:
    """渲染整个解法的步骤链。"""
    steps = []
    proc_nodes = [n for n in method.graph.nodes if n.type != "final_answer"]

    for i, node in enumerate(proc_nodes):
        step_info = render_step(node, i)
        # 标注关键步骤
        if node.weight >= 2.0:
            step_info["critical"] = True
        steps.append(step_info)

    # 最终答案
    final_node = next((n for n in method.graph.nodes if n.type == "final_answer"), None)
    final_answer = method.final_answer
    if final_node and final_node.output:
        final_answer = final_node.output

    return {
        "steps": steps,
        "final_answer": final_answer,
        "method_name": method.method_name,
    }


def render_all_methods(trace: CanonicalSolutionTrace) -> list[dict]:
    """渲染所有方法。"""
    return [
        {
            "overview": render_method_overview(m),
            "solution": render_solution_chain(m),
        }
        for m in trace.methods
    ]


def render_step_tree(method: SolutionMethod) -> dict:
    """渲染步骤依赖树。"""
    nodes = {n.id: n for n in method.graph.nodes}
    edges = method.graph.edges
    # 构建邻接表
    tree = {}
    for edge in edges:
        parent = nodes.get(edge.source)
        child = nodes.get(edge.target)
        if parent and child:
            if edge.source not in tree:
                tree[edge.source] = []
            tree[edge.source].append(edge.target)
    return {
        "nodes": {nid: nodes[nid] for nid in nodes},
        "tree": tree,
        "roots": [n.id for n in method.graph.nodes if n.id not in set(e.target for e in edges)],
    }


# ═══════════════════════════════════════════
#  教学解释生成
# ═══════════════════════════════════════════

def _op_type_cn(op: str) -> str:
    """操作类型 -> 中文名。"""
    return {
        "differentiate": "求导",
        "integrate": "积分",
        "compute_limit": "求极限",
        "partial_diff": "偏导数",
        "expand": "展开",
        "factor": "因式分解",
        "simplify": "化简",
        "substitute": "代换/换元",
        "collect": "合并同类项",
        "cancel": "约分",
        "solve_equation": "解方程",
        "solve_system": "解方程组",
        "matrix_op": "矩阵运算",
        "row_reduce": "行变换",
        "eigen_solve": "特征值/特征向量",
        "determinant": "行列式计算",
        "orthogonalize": "正交化",
        "quadratic_form": "二次型标准化",
        "expand_series": "级数展开",
        "convergence_test": "收敛性判别",
        "probability_calc": "概率计算",
        "expectation": "期望/方差",
        "mle_derive": "极大似然推导",
        "apply_theorem": "应用定理",
        "classify": "分类讨论",
        "final_answer": "最终答案",
        "compute": "计算",
        "define": "定义",
    }.get(op, op)


def _generate_explanation(node: GraphNode) -> str:
    """为步骤生成教学解释。"""
    op = node.operation or node.type
    label = node.label or ""
    inp = node.input_state or ""
    out = node.output or ""

    if op == "substitute" and inp and out:
        return f"由于表达式中含有特定结构，通过代换简化计算：从 ${inp}$ 出发进行变换"
    if op == "factor" and inp:
        return f"对表达式进行因式分解，将其化为乘积形式便于后续讨论"
    if op == "simplify":
        return "合并同类项、约分等操作，将表达式化为最简形式"
    if op == "integrate" and inp:
        return f"对被积函数 ${inp}$ 进行积分运算"
    if op == "differentiate" and inp:
        return f"对函数 ${inp}$ 求导，分析其增减性与极值"
    if op == "compute_limit":
        return "利用极限运算法则或等价无穷小求极限值"
    if op == "eigen_solve":
        return "构造并求解特征方程，得到特征值和特征向量"
    if op == "apply_theorem":
        return f"应用相关定理，将条件转化为可计算的形式"
    if op == "classify":
        return "根据参数不同取值进行分类讨论，确保每种情况都被覆盖"
    if out:
        return f"通过{_op_type_cn(op)}，得到 ${out}$"
    return f"执行{_op_type_cn(op)}运算"
