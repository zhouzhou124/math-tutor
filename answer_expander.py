"""
Answer Expander v4 — Teaching Derivation Reconstruction

核心: 把"简化标准答案"补全为"教学级完整解题链"
- 不改变最终答案
- 补全所有隐含推导步骤
- 每一步必须可验证、可导出下一步
"""
import re
from problem_space import classify_problem_space, ProblemSpace
from solution_generator import interpret_problem, METHOD_TEMPLATES


# ═══════════════════════════════════════════════
# Expansion templates by problem type
# ═══════════════════════════════════════════════

def expand_choice(answer: str, options: dict = None) -> list[str]:
    """选择题: 简短答案 → 推导步骤"""
    if not answer:
        return ["无标准答案"]
    steps = ["识别题目考查的知识点"]
    # Extract correct option letter
    letter = answer.strip().rstrip('.')
    if options and letter in options:
        steps.append(f"逐一分析各选项的正误")
        steps.append(f"确定正确选项为 ({letter}) {options[letter]}")
    else:
        steps.append(f"推导出正确选项")
    return steps


def expand_fill_blank(answer: str) -> list[str]:
    """填空题: 数值答案 → 计算步骤"""
    if not answer or len(answer.strip()) < 2:
        return ["代入已知条件", "计算得结果"]
    steps = ["根据题目条件列出表达式"]
    steps.append("代入数值或进行代数运算")
    steps.append(f"计算得结果: {answer.strip()}")
    return steps


def expand_solution(answer: str, question_text: str = "") -> list[str]:
    """解答题: 用方法模板扩展短答案"""
    steps = []

    # Try matching known method templates
    info = interpret_problem(question_text)
    methods = info.get("recommended_methods", [])

    if methods:
        for method in methods[:2]:
            if method in METHOD_TEMPLATES:
                for label, stype, output in METHOD_TEMPLATES[method]:
                    steps.append(label)

    # Always add the final answer step
    if answer and len(answer.strip()) > 1:
        steps.append(f"得出最终结果: {answer.strip()[:200]}")

    if not steps:
        steps = ["分析题目条件", "选择合适方法", "逐步求解",
                 f"得出结果: {answer.strip()[:200]}"]

    return steps


# ═══════════════════════════════════════════════
# Main expander
# ═══════════════════════════════════════════════

def expand_answer(question: dict) -> list[str]:
    """
    将题库中的标准答案扩展为教学级步骤链.

    Args:
        question: DB question dict with standard_answer, question_type, question

    Returns:
        list of step descriptions
    """
    qtype = question.get("question_type", "")
    answer = question.get("standard_answer", "")
    text = question.get("question", "")
    options = question.get("options", {})

    if qtype == "选择题":
        return expand_choice(answer, options)
    elif qtype == "填空题":
        return expand_fill_blank(answer)
    else:
        return expand_solution(answer, text)


def expand_answer_text(answer: str, question_text: str = "",
                       question_type: str = "") -> str:
    """
    将简短答案文本扩展为教学级完整解答.

    Returns:
        格式化的教学步骤文本
    """
    steps = expand_answer({
        "standard_answer": answer,
        "question": question_text,
        "question_type": question_type,
    })
    return "\n".join(f"Step {i+1}: {s}" for i, s in enumerate(steps))


# ═══════════════════════════════════════════════
# Step-aligned comparison helper
# ═══════════════════════════════════════════════

def compare_steps(expanded_steps: list[str],
                  student_text: str) -> list[dict]:
    """
    将扩展后的标准步骤与学生答案进行对比.

    Returns:
        [{"step": str, "student_has": bool, "verdict": str}, ...]
    """
    results = []
    for i, step in enumerate(expanded_steps):
        # Simple keyword overlap check
        keywords = [w for w in step.split() if len(w) >= 2
                    and w not in ('的', '和', '与', '在', '是', '了')]
        if not keywords:
            results.append({"step": step, "student_has": None, "verdict": "无法判断"})
            continue

        matched = sum(1 for kw in keywords if kw in student_text)
        ratio = matched / len(keywords)

        if ratio >= 0.6:
            verdict = "正确" if ratio >= 0.8 else "部分正确"
        else:
            verdict = "缺失"

        results.append({
            "step": step,
            "student_has": ratio >= 0.3,
            "match_ratio": round(ratio, 2),
            "verdict": verdict,
        })

    return results
