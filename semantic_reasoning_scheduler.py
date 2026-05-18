"""
Semantic Reasoning Scheduler — 基于语义的推理调度器

核心原则: 根据题目语义类型和复杂度动态分配推理资源。

推理级别:
  Level 0: 即时判分 (choice/fill-blank, <10ms)
  Level 1: 快速检查 (simple solution, answer match high, <100ms)
  Level 2: 标准推理 (graph matching, <2s)
  Level 3: 深度推理 (multi-method + LLM, <10s)
  Level 4: 完整链 (LLM semantic fallback, <30s)
"""

from enum import IntEnum
from typing import Optional

# 导入问题语义模块
try:
    from problem_semantics import QuestionIntent, ProblemSchema, parse_problem
except ImportError:
    from .problem_semantics import QuestionIntent, ProblemSchema, parse_problem


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


# 意图到推理级别的映射
INTENT_BUDGET_MAP = {
    # 计算类 - 通常可以快速匹配
    QuestionIntent.LIMIT_COMPUTATION: ReasoningBudget.STANDARD,
    QuestionIntent.SEQUENCE_LIMIT: ReasoningBudget.STANDARD,
    QuestionIntent.EQUATION_SOLVE: ReasoningBudget.FAST,
    QuestionIntent.SYSTEM_SOLVE: ReasoningBudget.STANDARD,
    QuestionIntent.FUNCTION_INTEGRAL: ReasoningBudget.STANDARD,
    
    # 证明类 - 需要更多推理
    QuestionIntent.PROPOSITION_JUDGEMENT: ReasoningBudget.DEEP,
    QuestionIntent.PROOF_DIRECT: ReasoningBudget.DEEP,
    QuestionIntent.PROOF_INDUCTION: ReasoningBudget.FULL,
    QuestionIntent.PROOF_CONTRADICTION: ReasoningBudget.FULL,
    QuestionIntent.COUNTEREXAMPLE: ReasoningBudget.FULL,
    QuestionIntent.PROOF_EXISTENCE: ReasoningBudget.FULL,
    
    # 判断类 - 中等推理
    QuestionIntent.LIMIT_EXISTENCE: ReasoningBudget.STANDARD,
    QuestionIntent.FUNCTION_CONTINUITY: ReasoningBudget.STANDARD,
    QuestionIntent.FUNCTION_DIFFERENTIABILITY: ReasoningBudget.STANDARD,
    QuestionIntent.SEQUENCE_CONVERGENCE: ReasoningBudget.DEEP,
    
    # 矩阵相关
    QuestionIntent.MATRIX_DETERMINANT: ReasoningBudget.FAST,
    QuestionIntent.MATRIX_INVERSE: ReasoningBudget.STANDARD,
    QuestionIntent.MATRIX_EIGEN: ReasoningBudget.STANDARD,
    
    # 默认
    QuestionIntent.UNKNOWN: ReasoningBudget.FULL,
}


def schedule_by_semantic(problem_schema: ProblemSchema, student_answer: str = "") -> ReasoningBudget:
    """
    根据问题语义结构决定推理深度。
    
    Args:
        problem_schema: 问题语义结构
        student_answer: 学生答案（可选）
    
    Returns:
        ReasoningBudget: 推理级别
    """
    # ── 无学生作答：INSTANT ──
    if not student_answer or not student_answer.strip():
        return ReasoningBudget.INSTANT
    
    # ── 根据题目意图类型决定 ──
    intent = problem_schema.question_type
    budget = INTENT_BUDGET_MAP.get(intent, ReasoningBudget.FULL)
    
    # ── 根据置信度调整 ──
    confidence = problem_schema.confidence
    if confidence < 0.5:
        # 置信度低，需要更深的推理
        new_level = min(budget.value + 1, ReasoningBudget.FULL.value)
        budget = ReasoningBudget(new_level)
    
    # ── 根据答案长度调整 ──
    answer_len = len(student_answer.strip())
    if answer_len > 1000:
        # 长答案可能需要更深推理
        new_level = min(budget.value + 1, ReasoningBudget.FULL.value)
        budget = ReasoningBudget(new_level)
    elif answer_len < 50:
        # 短答案可以快速处理
        new_level = max(budget.value - 1, ReasoningBudget.INSTANT.value)
        budget = ReasoningBudget(new_level)
    
    return budget


def schedule(text: str, student_answer: str = "") -> ReasoningBudget:
    """
    根据题目文本和学生作答，决定推理深度。
    
    这是兼容旧API的包装函数。
    
    Args:
        text: 题目文本
        student_answer: 学生答案（可选）
    
    Returns:
        ReasoningBudget: 推理级别
    """
    # 解析题目语义
    problem_schema = parse_problem(text)
    return schedule_by_semantic(problem_schema, student_answer)


def schedule_with_schema(problem_schema: ProblemSchema, student_answer: str = "") -> ReasoningBudget:
    """
    使用预解析的问题语义结构决定推理深度。
    
    Args:
        problem_schema: 问题语义结构
        student_answer: 学生答案（可选）
    
    Returns:
        ReasoningBudget: 推理级别
    """
    return schedule_by_semantic(problem_schema, student_answer)


def get_timeout(budget: ReasoningBudget) -> int:
    """返回该级别的超时(ms)。"""
    return BUDGET_CONFIG.get(budget, {}).get("timeout_ms", 5000)


def get_max_methods(budget: ReasoningBudget) -> int:
    """返回该级别最多尝试的 canonical methods 数。"""
    return BUDGET_CONFIG.get(budget, {}).get("max_methods", 1)


def should_use_llm(budget: ReasoningBudget) -> bool:
    """该级别是否允许 LLM 调用。"""
    return BUDGET_CONFIG.get(budget, {}).get("use_llm", False)


# ──────────────────────────────────────────────────────────────
# 策略选择器
# ──────────────────────────────────────────────────────────────

def select_strategy(problem_schema: ProblemSchema) -> list[str]:
    """
    根据问题语义选择合适的解题策略。
    
    Args:
        problem_schema: 问题语义结构
    
    Returns:
        list[str]: 推荐的策略列表（按优先级排序）
    """
    intent = problem_schema.question_type
    topics = problem_schema.topics
    
    strategies = []
    
    # 根据题目类型选择策略
    if intent == QuestionIntent.PROPOSITION_JUDGEMENT:
        strategies.extend([
            "monotonicity_analysis",
            "continuity_analysis",
            "invertibility_analysis",
            "counterexample_search",
        ])
    
    elif intent == QuestionIntent.LIMIT_COMPUTATION:
        strategies.extend([
            "direct_substitution",
            "algebraic_manipulation",
            "lhopitals_rule",
            "taylor_expansion",
            "squeeze_theorem",
        ])
    
    elif intent == QuestionIntent.SEQUENCE_LIMIT:
        strategies.extend([
            "direct_computation",
            "recurrence_relation",
            "monotone_convergence",
            "cauchy_criterion",
        ])
    
    elif intent == QuestionIntent.PROOF_DIRECT:
        strategies.extend([
            "definition_application",
            "theorem_application",
            "construction_method",
        ])
    
    elif intent == QuestionIntent.FUNCTION_CONTINUITY:
        strategies.extend([
            "epsilon_delta",
            "limit_check",
            "composition_continuity",
        ])
    
    elif intent in [QuestionIntent.MATRIX_DETERMINANT, QuestionIntent.MATRIX_INVERSE]:
        strategies.extend([
            "gaussian_elimination",
            "cofactor_expansion",
            "block_matrix",
        ])
    
    else:
        strategies.append("general_reasoning")
    
    # 根据知识点调整策略优先级
    if any(t.name == "MONOTONICITY" for t in topics) and "monotonicity_analysis" in strategies:
        strategies.insert(0, strategies.pop(strategies.index("monotonicity_analysis")))
    
    if any(t.name == "CONTINUITY" for t in topics) and "continuity_analysis" in strategies:
        strategies.insert(0, strategies.pop(strategies.index("continuity_analysis")))
    
    return strategies


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        """设数列{x_n}满足 -\\frac{\\pi}{2}\\le x_n\\le \\frac{\\pi}{2}，
        则下列命题正确的是：
        A. 若 lim cos(sin x_n) 存在，则 lim x_n 存在
        B. 若 lim sin(cos x_n) 存在，则 lim x_n 存在""",
        
        """求极限：lim_{n→∞} \\frac{n^2 + 1}{2n^2 - n}""",
        
        """证明：若函数 f(x) 在 x=0 处连续，且 f(x+y) = f(x) + f(y)，则 f(x) = kx""",
    ]
    
    for i, text in enumerate(test_cases):
        schema = parse_problem(text)
        budget = schedule(text, "我的答案")
        strategies = select_strategy(schema)
        
        print(f"=== Test Case {i+1} ===")
        print(f"Question Type: {schema.question_type.name}")
        print(f"Confidence: {schema.confidence:.2f}")
        print(f"Recommended Budget: {budget.name}")
        print(f"Recommended Strategies: {strategies}")
        print()
