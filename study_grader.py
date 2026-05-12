"""
Study Grader — 四层解耦批改架构

  Layer 1 (Fast):      答案验证 → 最终答案是否正确
  Layer 2 (Structural): 步骤结构 → 与 canonical trace 对齐度
  Layer 3 (Semantic):   数学合法性 → 推导是否自洽
  Layer 4 (Teaching):   教学解释 → 从分析结果生成反馈

每层独立运行、独立评分、独立置信度。最终分 = 加权融合。
"""

import re

from solution_graph import SolutionGraph
from symbolic_executor import quick_compare, ErrorLevel, _HAS_SYMPY
from config import SCORING_WEIGHTS


def grade_student_answer(
    question: dict,
    student_text: str,
    solution_graph: SolutionGraph | None = None,
    client=None,
    model: str = "deepseek-chat",
    canonical_trace=None,
) -> dict:
    """四层解耦批改入口。"""
    qtype = question.get("question_type", "")
    std_answer = question.get("standard_answer", "")
    total_score = float(question.get("score", 10))

    # ── 选择/填空：只用 Fast Layer ──
    if qtype == "选择题":
        return _engine_a_choice(student_text, question, total_score)
    if qtype == "填空题":
        return _engine_a_fill(student_text, std_answer, total_score)

    # ── 解答/证明：四层独立评估 ──
    layer1 = _fast_layer(student_text, std_answer, question, total_score)
    layer2 = _structural_layer(student_text, canonical_trace, total_score)
    layer3 = _semantic_layer(student_text, total_score)
    layer4 = _teaching_layer(layer1, layer2, layer3, question)

    # ── 融合评分 ──
    # Layer weight: 答案 20% + 结构 40% + 合法性 40%
    final_score = (
        layer1["score"] * 0.2 +
        layer2["score"] * 0.4 +
        layer3["score"] * 0.4
    )

    return {
        "success": True,
        "total": round(final_score, 1),
        "step_score": round(final_score * 0.5, 1),
        "result_score": round(final_score * 0.5, 1),
        "step_analysis": layer2.get("step_details", []),
        "deductions": [],
        "comment": layer4.get("summary", ""),
        "engine": "4layer",
        "layers": {
            "fast": layer1,
            "structural": layer2,
            "semantic": layer3,
            "teaching": layer4,
        },
    }


# ═══════════════════════════════════════════════
#  Layer 1: Fast — 答案验证
# ═══════════════════════════════════════════════

def _fast_layer(student_text: str, std_answer: str,
                question: dict, total_score: float) -> dict:
    """
    仅检查最终答案是否与标准答案等价。
    不关心步骤、不关心过程、不调用 LLM。
    """
    if not student_text or not student_text.strip():
        return {
            "layer": "fast",
            "score": 0,
            "max_score": total_score,
            "match": False,
            "method": "empty",
            "confidence": 1.0,
            "detail": "未作答",
        }

    result = quick_compare(_extract_last_math(student_text), std_answer)
    match = result.get("equivalent", False)
    method = result.get("method", "unknown")

    # 分数：答对满分，答错 0 分
    score = total_score if match else 0

    return {
        "layer": "fast",
        "score": score,
        "max_score": total_score,
        "match": match,
        "method": method,
        "confidence": 1.0 if match else 0.9 if method != "string_norm" else 0.7,
        "detail": "答案正确" if match else (
            "答案与标准答案不等价" if method != "empty" else "未作答"
        ),
        "student_final": _extract_last_math(student_text),
        "standard_final": std_answer,
    }


# ═══════════════════════════════════════════════
#  Layer 2: Structural — 步骤结构
# ═══════════════════════════════════════════════

def _structural_layer(student_text: str, canonical_trace,
                      total_score: float) -> dict:
    """
    检查学生步骤与 canonical trace 的结构对齐度。
    仅做图匹配，不做语义判断。
    无 canonical trace 时跳过。
    """
    if not canonical_trace or not canonical_trace.methods:
        return {
            "layer": "structural",
            "score": 0,
            "max_score": total_score,
            "coverage": 0,
            "correctness": 0,
            "confidence": 0,
            "detail": "无规范轨迹，跳过结构层",
            "matched_method": None,
            "step_details": [],
            "skipped": True,
        }

    from graph_matching import grade_with_graph

    best_score = 0
    best_result = None
    best_method = None

    for method in canonical_trace.methods:
        mg = method.graph
        if not mg or len(mg.nodes) <= 1:
            continue
        try:
            result = grade_with_graph(student_text, mg)
            s = result.get("score", 0)
            if s > best_score:
                best_score = s
                best_result = result
                best_method = method
        except Exception:
            continue

    if best_result is None:
        return {
            "layer": "structural",
            "score": 0,
            "max_score": total_score,
            "coverage": 0,
            "correctness": 0,
            "confidence": 0,
            "detail": "图匹配失败",
            "matched_method": None,
            "step_details": [],
        }

    matched_steps = best_result.get("matched_steps", [])
    step_details = [
        {
            "num": i + 1,
            "content": ms.get("label", ""),
            "judgment": ("正确" if ms.get("match_method") == "output_equivalent"
                         else "部分正确"),
            "score": f"{ms.get('weight', 0):.1f}",
            "comment": ms.get("standard_output", ""),
        }
        for i, ms in enumerate(matched_steps)
    ]

    return {
        "layer": "structural",
        "score": best_score,
        "max_score": total_score,
        "coverage": best_result.get("coverage", 0),
        "correctness": best_result.get("correctness", 0),
        "confidence": best_result.get("coverage", 0),
        "detail": best_result.get("error_label", ""),
        "matched_method": best_method.method_name if best_method else None,
        "step_details": step_details,
    }


# ═══════════════════════════════════════════════
#  Layer 3: Semantic — 数学合法性
# ═══════════════════════════════════════════════

def _semantic_layer(student_text: str, total_score: float) -> dict:
    """
    验证学生推导的数学合法性（不依赖任何 canonical trace）。
    只看：推导链是否内部自洽？每步是否数学合法？
    """
    from derivation_validator import validate_derivation
    from student_trace_extractor import extract_student_trace

    if not student_text or not student_text.strip():
        return {
            "layer": "semantic",
            "score": 0,
            "max_score": total_score,
            "validity": 0,
            "confidence": 1.0,
            "detail": "未作答",
            "issues": [],
        }

    trace = extract_student_trace(student_text)
    dv = validate_derivation(student_text, trace)

    validity = dv.get("validity_score", 0)
    score = validity * total_score

    return {
        "layer": "semantic",
        "score": round(score, 1),
        "max_score": total_score,
        "validity": validity,
        "confidence": 0.6 + validity * 0.3,
        "detail": dv.get("overall_assessment", ""),
        "issues": dv.get("issues", []),
        "step_count": dv.get("step_count", 0),
        "has_closure": dv.get("has_closure", False),
    }


# ═══════════════════════════════════════════════
#  Layer 4: Teaching — 教学解释
# ═══════════════════════════════════════════════

def _teaching_layer(layer1: dict, layer2: dict, layer3: dict,
                    question: dict) -> dict:
    """
    从前三层的分析结果中生成教学反馈。
    纯规则驱动，不调用 LLM（LLM 可在 app.py 层另行添加）。
    """
    fast_match = layer1.get("match", False)
    struct_cov = layer2.get("coverage", 0)
    validity = layer3.get("validity", 0)
    issues = layer3.get("issues", [])

    # 生成分层反馈
    feedbacks = []

    # Fast layer feedback
    if fast_match:
        feedbacks.append("最终答案正确。")
    else:
        feedbacks.append("最终答案与标准答案不等价，请检查计算结果。")

    # Structural layer feedback
    if struct_cov >= 0.8:
        feedbacks.append("步骤结构完整，与标准解法高度吻合。")
    elif struct_cov >= 0.5:
        feedbacks.append("步骤覆盖基本完整，部分细节可补充。")
    elif struct_cov > 0:
        feedbacks.append("步骤覆盖较低，建议补充中间推导过程。")

    # Semantic layer feedback
    if validity >= 0.9:
        feedbacks.append("推导逻辑严密，步骤衔接合理。")
    elif validity >= 0.7:
        feedbacks.append("推导基本合法，部分衔接可更紧密。")
    elif validity >= 0.5:
        feedbacks.append("推导存在不连贯之处，建议补充中间步骤。")
    else:
        feedbacks.append("推导链断裂，建议重新梳理解题思路。")

    # 具体问题
    for issue in issues[:3]:
        feedbacks.append(f"问题: {issue}")

    # 综合建议
    overall = " · ".join(feedbacks[:4])
    teaching_tip = _get_teaching_tip(fast_match, struct_cov, validity, question)

    return {
        "layer": "teaching",
        "summary": overall,
        "feedbacks": feedbacks,
        "teaching_tip": teaching_tip,
    }


def _get_teaching_tip(fast_match: bool, struct_cov: float,
                      validity: float, question: dict) -> str:
    """生成教学建议。"""
    kp = ", ".join(question.get("knowledge_points", [])[:2]) or "此知识点"
    if fast_match and validity >= 0.8:
        return f"掌握良好！可以尝试更复杂的「{kp}」题目。"
    if fast_match and validity < 0.7:
        return f"答案对但推导不规范，建议规范书写「{kp}」的解题过程。"
    if not fast_match and validity >= 0.7:
        return f"思路基本正确但结果不对，检查「{kp}」计算细节。"
    if struct_cov < 0.3 and validity < 0.5:
        return f"建议重新学习「{kp}」的基础知识和典型例题。"
    return f"建议针对「{kp}」进行专项练习。"


# ═══════════════════════════════════════════════
#  Engine A — 选择/填空
# ═══════════════════════════════════════════════

def _engine_a_choice(student_text: str, question: dict, total_score: float) -> dict:
    """选择题：鲁棒归一化后严格比对。"""
    import re as _re
    correct_option = question.get("correct_option", "").strip().upper()
    stu = (student_text or "").strip()

    def _normalize(text: str) -> str:
        t = text.strip().upper()
        t = t.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
        t = t.replace("[", "").replace("]", "").replace("【", "").replace("】", "")
        t = _re.sub(r'答案[：:]?\s*', '', t)
        t = _re.sub(r'选[择项]?\s*', '', t)
        return "".join(_re.findall(r'[A-D]', t))

    stu_norm = _normalize(stu)
    correct_norm = _normalize(correct_option)
    is_single_choice = len(correct_norm) == 1

    if is_single_choice and len(stu_norm) > 1:
        return {
            "success": False, "total": 0, "step_score": 0, "result_score": 0,
            "step_analysis": [], "deductions": [],
            "comment": f"⚠️ 非法输入：你输入了多个选项（{stu_norm}），但这是单选题。",
            "engine": "engine_a", "illegal_input": True,
        }

    is_correct = (stu_norm == correct_norm)
    score = total_score if is_correct else 0.0
    return {
        "success": True, "total": score, "step_score": score, "result_score": 0,
        "step_analysis": [], "deductions": (
            [] if is_correct
            else [{"reason": f"选项错误: 识别为 {stu_norm or '无'}, 应为 {correct_norm}"}]
        ),
        "comment": f"正确，选项 {correct_norm}" if is_correct else f"错误，正确选项为 {correct_norm}",
        "engine": "engine_a",
    }


def _engine_a_fill(student_text: str, std_answer: str, total_score: float) -> dict:
    """填空题：SymPy 符号等价比较（带定义域意识）。"""
    stu = (student_text or "").strip()
    result = quick_compare(stu, std_answer)
    is_correct = result["equivalent"]
    score = total_score if is_correct else 0.0
    return {
        "success": True, "total": score, "step_score": score, "result_score": 0,
        "step_analysis": [], "deductions": (
            [] if is_correct
            else [{"reason": f"答案不等价: {result.get('difference', '')}"}]
        ),
        "comment": "正确" if is_correct else f"错误，标准答案为 {std_answer[:100]}",
        "engine": "engine_a",
    }


# ═══════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════

def _extract_last_math(text: str) -> str:
    """从文本末尾提取最后一个数学表达式。"""
    math_exprs = re.findall(r'\$([^$]+)\$', text)
    if not math_exprs:
        math_exprs = re.findall(r'\\boxed\{[^}]+\}', text)
        if math_exprs:
            return math_exprs[-1].replace(r'\boxed', '').strip('{}')
    return math_exprs[-1] if math_exprs else text.strip().split('\n')[-1][:200]
