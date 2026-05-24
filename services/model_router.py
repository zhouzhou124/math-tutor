"""Model router — task-based model selection for cost/speed optimization.

Routes each grading sub-task to the appropriate model tier:
  - local:      no LLM call (regex, symbolic compare)
  - fast model: deepseek-chat for skeleton, diagnosis, simple tasks
  - strong model: deepseek-v4-pro for detailed derivation, semantic grading
"""

from dataclasses import dataclass


@dataclass
class ModelRoute:
    model: str          # "local", "deepseek-chat", "deepseek-v4-pro", etc.
    max_tokens: int
    temperature: float
    reason: str = ""


def route_model(task: str, difficulty: str = "中等",
                question_type: str = "") -> ModelRoute:
    """Return the recommended model route for a grading sub-task.

    Args:
        task: one of "choice_grading", "fill_compare", "solution_skeleton",
              "solution_detail", "diagnosis", "grading", "structured_repair"
        difficulty: "基础", "中等", "较难", "难题"
        question_type: "选择题", "填空题", "解答题", "证明题"
    """

    # ── Local-only (no LLM) ──
    if task == "choice_grading":
        return ModelRoute(
            model="local", max_tokens=0, temperature=0,
            reason="选择题本地判分：选项字母比对",
        )

    if task == "fill_compare":
        return ModelRoute(
            model="local", max_tokens=0, temperature=0,
            reason="填空题符号比对：symbolic quick_compare",
        )

    # ── Fast model (cheap, high throughput) ──
    if task == "solution_skeleton":
        if question_type in ("选择题", "填空题"):
            return ModelRoute(
                model="deepseek-chat", max_tokens=800, temperature=0.2,
                reason="选填题解答骨架：简短即可",
            )
        return ModelRoute(
            model="deepseek-chat", max_tokens=1000, temperature=0.2,
            reason="解答题骨架：快速生成步骤框架",
        )

    if task == "diagnosis":
        return ModelRoute(
            model="deepseek-chat", max_tokens=1200, temperature=0.2,
            reason="错因诊断：快模型足够分析错误模式",
        )

    if task == "structured_repair":
        return ModelRoute(
            model="deepseek-chat", max_tokens=600, temperature=0.1,
            reason="JSON 修复：快模型即可修正格式",
        )

    # ── Strong model (expensive, high quality) ──
    if task == "solution_detail":
        if difficulty in ("难", "较难"):
            return ModelRoute(
                model="deepseek-v4-pro", max_tokens=4096, temperature=0.15,
                reason="复杂题详细推导：需要强推理能力",
            )
        return ModelRoute(
            model="deepseek-chat", max_tokens=2800, temperature=0.15,
            reason="普通题详细推导",
        )

    if task == "grading":
        if difficulty in ("难", "较难"):
            return ModelRoute(
                model="deepseek-v4-pro", max_tokens=3000, temperature=0.1,
                reason="复杂题语义批改：需要强推理",
            )
        return ModelRoute(
            model="deepseek-chat", max_tokens=2000, temperature=0.1,
            reason="普通题语义批改",
        )

    # ── Default ──
    return ModelRoute(
        model="deepseek-chat", max_tokens=2000, temperature=0.2,
        reason="默认路由",
    )
