"""
Rubric Builder — 从规范解题轨迹自动生成评分标准

核心职责：
  - 将 CanonicalSolutionTrace 转换为逐步骤评分细则
  - 分配 70% 过程分 + 30% 结果分
  - 标记关键步骤和常见错误类型
"""

from dataclasses import dataclass, field


@dataclass
class RubricItem:
    """单个评分项"""
    step_id: str
    label: str
    score: float
    is_critical: bool = False
    error_type_hint: str = ""  # from ERROR_TYPES


def build_rubric(trace, total_score: int) -> list[RubricItem]:
    """
    从规范解题轨迹生成评分细则。

    Args:
        trace: CanonicalSolutionTrace 实例
        total_score: 满分值

    Returns:
        list[RubricItem] — 按步骤顺序排列的评分项
    """
    best = trace.best_method()
    if not best:
        return []

    graph = best.graph
    nodes = graph.nodes
    if not nodes:
        return []

    step_budget = round(total_score * 0.7, 1)
    result_budget = round(total_score * 0.3, 1)

    # 分离 final_answer 节点和过程节点
    process_nodes = [n for n in nodes if n.type != "final_answer"]
    final_nodes = [n for n in nodes if n.type == "final_answer"]

    # 收集常见错误知识点（用于标记 critical）
    mistake_kp = set()
    for m in best.common_mistakes:
        mistake_kp.add(m)

    items = []

    if process_nodes:
        # 按 weight 分配过程分
        total_weight = sum(n.weight for n in process_nodes)
        if total_weight <= 0:
            # 均分
            per_step = round(step_budget / len(process_nodes), 1)
            for n in process_nodes:
                n.weight = per_step
            total_weight = step_budget

        for n in process_nodes:
            score = round(step_budget * n.weight / total_weight, 1) if total_weight > 0 else 0
            is_critical = n.weight >= (total_weight / len(process_nodes)) * 1.5

            # 从 operation 推断常见错误类型
            error_hint = _infer_error_type(n.type)

            items.append(RubricItem(
                step_id=n.id,
                label=n.label or n.type,
                score=score,
                is_critical=is_critical,
                error_type_hint=error_hint,
            ))

    # 最终答案节点
    if final_nodes:
        items.append(RubricItem(
            step_id=final_nodes[-1].id,
            label="最终答案",
            score=result_budget,
            is_critical=True,
            error_type_hint="运算错误",
        ))
    elif items:
        # 没有 final_answer 节点，把结果分加到最后一个过程步骤
        items[-1].score = round(items[-1].score + result_budget, 1)

    # 修正舍入误差
    actual_total = sum(i.score for i in items)
    if abs(actual_total - total_score) > 0.1 and items:
        items[-1].score = round(items[-1].score + (total_score - actual_total), 1)

    return items


def _infer_error_type(operation: str) -> str:
    """根据操作类型推断最常见的错误类型"""
    mapping = {
        "differentiate": "公式记忆错误",
        "integrate": "公式记忆错误",
        "compute_limit": "运算错误",
        "simplify": "计算粗心",
        "solve_system": "运算错误",
        "substitute": "计算粗心",
        "matrix_op": "运算错误",
        "eigen_solve": "概念错误",
        "orthogonalize": "概念错误",
        "quadratic_form": "概念错误",
        "apply_theorem": "概念错误",
        "expand_series": "公式记忆错误",
        "classify": "概念错误",
        "probability_calc": "概念错误",
        "expectation": "公式记忆错误",
        "mle_derive": "推导错误",
        "moment_estimate": "推导错误",
        "final_answer": "运算错误",
    }
    return mapping.get(operation, "运算错误")
