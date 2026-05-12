"""
Reasoning Scheduler — 推理调度器

核心原则: 不是所有题都值得 heavy reasoning。
根据题型/复杂度/置信度动态分配推理资源。

推理级别:
  Level 0: 即时判分 (choice/fill-blank, <10ms)
  Level 1: 快速检查 (simple solution, answer match high, <100ms)
  Level 2: 标准推理 (graph matching, <2s)
  Level 3: 深度推理 (multi-method + LLM, <10s)
  Level 4: 完整链 (LLM semantic fallback, <30s)
"""

from enum import IntEnum


class ReasoningBudget(IntEnum):
    INSTANT = 0    # 选择题/填空题，规则引擎
    FAST = 1       # 答案匹配高置信度，快速通过
    STANDARD = 2   # 单方法图匹配
    DEEP = 3       # 多方法 + 分类
    FULL = 4       # LLM 语义 fallback


# 每种级别的超时和并发限制
BUDGET_CONFIG = {
    ReasoningBudget.INSTANT:  {"timeout_ms": 50,   "max_methods": 0,  "use_llm": False},
    ReasoningBudget.FAST:     {"timeout_ms": 500,   "max_methods": 1,  "use_llm": False},
    ReasoningBudget.STANDARD: {"timeout_ms": 3000,  "max_methods": 2,  "use_llm": False},
    ReasoningBudget.DEEP:     {"timeout_ms": 8000,  "max_methods": 3,  "use_llm": False},
    ReasoningBudget.FULL:     {"timeout_ms": 30000, "max_methods": 3,  "use_llm": True},
}


def schedule(question: dict, student_answer: str = "") -> ReasoningBudget:
    """
    根据题目特征和学生作答，决定推理深度。

    决策树:
      choice/fill-blank      → INSTANT
      答案为空               → INSTANT (无法批改)
      解答题 + 答案<100字    → FAST (短答案，快速检查)
      解答题 + 有 canonical  → STANDARD (有 trace 加速)
      解答题 + 无 canonical  → DEEP (需要多方法匹配)
      none of above          → FULL (LLM fallback)
    """
    q_type = question.get("question_type", "")

    # ── 选择题/填空题：永远 INSTANT ──
    if q_type in ("选择题", "填空题"):
        return ReasoningBudget.INSTANT

    # ── 无学生作答：INSTANT ──
    if not student_answer or not student_answer.strip():
        return ReasoningBudget.INSTANT

    # ── 解答题/证明题 按复杂度分层 ──
    answer_len = len(student_answer.strip())

    # 有 canonical_solutions 缓存 → STANDARD
    has_canonical = bool(question.get("canonical_solutions"))
    if has_canonical:
        if answer_len < 500:
            return ReasoningBudget.FAST
        return ReasoningBudget.STANDARD

    # 无 canonical → 需要更多推理
    if answer_len < 200:
        return ReasoningBudget.STANDARD  # 短答案，不需要多方法

    # 答案较长且无缓存 → DEEP
    return ReasoningBudget.DEEP


def get_timeout(budget: ReasoningBudget) -> int:
    """返回该级别的超时(ms)。"""
    return BUDGET_CONFIG.get(budget, {}).get("timeout_ms", 5000)


def get_max_methods(budget: ReasoningBudget) -> int:
    """返回该级别最多尝试的 canonical methods 数。"""
    return BUDGET_CONFIG.get(budget, {}).get("max_methods", 1)


def should_use_llm(budget: ReasoningBudget) -> bool:
    """该级别是否允许 LLM 调用。"""
    return BUDGET_CONFIG.get(budget, {}).get("use_llm", False)
