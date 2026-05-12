"""
Derivation Validator — 数学推导合法性验证

核心思想: 不判断"学生是否对齐标准解"，而是判断"学生推导是否数学合法"。

这是 proof verification 思想在数学教育中的应用。
"""

import re
from symbolic_executor import symbolic_compare, _HAS_SYMPY, parse_expression


def validate_derivation(student_text: str, student_trace: dict = None) -> dict:
    """
    独立验证学生推导的数学合法性（不依赖任何 canonical trace）。

    检查维度:
      1. 步骤自洽性: 相邻步骤的 output → input 是否能合理衔接
      2. 操作合法性: 每步执行的运算对该步的输入是否合法
      3. 最终答案可达性: 从第一个 input 到最后一个 output 是否形成闭环

    Returns:
        {
            "valid": bool,
            "validity_score": float,       # 0-1，推导合法性总分
            "step_transitions": [dict],    # 每步转换检查
            "issues": [str],              # 合法性问题列表
            "overall_assessment": str,    # 总体评估
        }
    """
    steps = student_trace.get("steps", []) if student_trace else []
    if not steps:
        # 从文本自行提取步骤
        steps = _extract_steps_from_text(student_text)

    if len(steps) < 1:
        return {
            "valid": False,
            "validity_score": 0.0,
            "step_transitions": [],
            "issues": ["无法提取有效步骤"],
            "overall_assessment": "未检测到有效解题步骤",
        }

    # ── 1. 逐步骤自洽检查 ──
    transitions = []
    issues = []
    transition_scores = []

    for i in range(1, len(steps)):
        prev = steps[i - 1]
        curr = steps[i]
        result = _check_transition_validity(prev, curr)
        transitions.append(result)
        transition_scores.append(result["score"])
        if result["issue"]:
            issues.append(f"Step {i}→{i+1}: {result['issue']}")

    # ── 2. 整体推导闭环 ──
    has_start = bool(steps[0].get("input_state") or steps[0].get("output_state"))
    has_end = bool(steps[-1].get("output_state"))
    has_closure = has_start and has_end

    # ── 3. 评分 ──
    if transition_scores:
        avg_transition = sum(transition_scores) / len(transition_scores)
    else:
        avg_transition = 1.0  # 单步不扣分

    # 有闭环 + 步骤自洽 + 无重大问题
    validity_score = (
        avg_transition * 0.6 +
        (1.0 if has_closure else 0.5) * 0.2 +
        (1.0 if len(issues) <= 1 else max(0, 1.0 - len(issues) * 0.15)) * 0.2
    )
    validity_score = min(max(validity_score, 0.0), 1.0)

    return {
        "valid": validity_score >= 0.5,
        "validity_score": round(validity_score, 2),
        "step_transitions": transitions,
        "issues": issues,
        "has_closure": has_closure,
        "step_count": len(steps),
        "overall_assessment": _assess_validity(validity_score, len(issues)),
    }


def _check_transition_validity(prev_step: dict, curr_step: dict) -> dict:
    """
    检查两步之间的推导是否合法。

    策略（从严格到宽松）：
      1. 符号等价: prev.output == curr.input
      2. 符号包含: prev.output 的符号 ⊆ curr.input 的符号（可能合并了其他信息）
      3. 操作合法性: prev.output 经过 curr.operation 能否到达 curr.output
      4. 文本语义: prev 和 curr 的文本描述是否有逻辑连续性
    """
    prev_out = (prev_step.get("output_state") or "").strip()
    curr_inp = (curr_step.get("input_state") or "").strip()
    curr_out = (curr_step.get("output_state") or "").strip()
    curr_op = curr_step.get("operation", "compute")

    # 空状态 → 跳过（无法判断）
    if not prev_out or not curr_inp:
        if prev_out and not curr_inp:
            # 有前一步输出但无显式 input → 检查是否有符号连续性
            prev_syms = set(re.findall(r'[a-zA-Z]+|\\[a-zA-Z]+', prev_out))
            curr_syms = set(re.findall(r'[a-zA-Z]+|\\[a-zA-Z]+', curr_out))
            if prev_syms and curr_syms and len(prev_syms & curr_syms) >= 1:
                return {"score": 0.7, "method": "symbol_continuity", "issue": None}
            return {"score": 0.5, "method": "unverifiable", "issue": "无法验证步骤衔接"}
        return {"score": 0.5, "method": "unverifiable", "issue": None}

    # 策略1: 符号等价
    result = symbolic_compare(prev_out, curr_inp)
    if result.get("equivalent"):
        return {"score": 1.0, "method": "symbolic_equivalent", "issue": None}

    # 策略2: 符号包含
    prev_syms = set(re.findall(r'[a-zA-Z]+', prev_out))
    curr_syms = set(re.findall(r'[a-zA-Z]+', curr_inp))
    if prev_syms and prev_syms.issubset(curr_syms):
        return {"score": 0.8, "method": "symbol_containment", "issue": None}

    # 策略3: 有共同符号 + 操作合法
    if prev_syms and curr_syms and prev_syms & curr_syms:
        # 检查通过当前操作能否产生 curr_out
        if _HAS_SYMPY and prev_out and curr_out:
            p_expr = parse_expression(prev_out)
            c_expr = parse_expression(curr_out)
            if p_expr and c_expr:
                # 求导操作: diff(prev) == curr
                if curr_op in ("differentiate", "diff", "partial_diff"):
                    try:
                        import sympy as sp
                        result_expr = sp.diff(p_expr)
                        if sp.simplify(result_expr - c_expr) == 0:
                            return {"score": 1.0, "method": "operation_verified", "issue": None}
                    except Exception:
                        pass
                # 积分操作: integrate(prev) == curr
                if curr_op == "integrate":
                    try:
                        import sympy as sp
                        # 只做简单检查：对 curr 求导是否回到 prev
                        result_expr = sp.diff(c_expr)
                        if sp.simplify(result_expr - p_expr) == 0:
                            return {"score": 1.0, "method": "integration_verified", "issue": None}
                    except Exception:
                        pass

        # 符号部分重叠但不等价
        overlap = len(prev_syms & curr_syms)
        total = max(len(prev_syms | curr_syms), 1)
        ratio = overlap / total
        if ratio >= 0.3:
            return {"score": 0.6, "method": "partial_symbol_overlap", "issue": None}

    # 策略4: 完全没有符号关联
    return {
        "score": 0.2,
        "method": "no_connection",
        "issue": f"推导跳跃过大: '{prev_out[:40]}' 与 '{curr_inp[:40]}' 无关联",
    }


def _extract_steps_from_text(text: str) -> list[dict]:
    """从原始文本提取步骤。"""
    if not text or not text.strip():
        return []
    steps = []
    lines = text.strip().split('\n')
    current = {"output_state": ""}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+[\s\.、．]', line) or re.match(r'^[一二三四五六七八九十]+[、．\s]', line):
            if current.get("output_state"):
                steps.append(current)
            current = {"output_state": _extract_math(line)}
        else:
            math = _extract_math(line)
            if math:
                current["output_state"] = math
    if current.get("output_state"):
        steps.append(current)
    return steps


def _extract_math(text: str) -> str:
    """从文本提取数学表达式。"""
    m = re.findall(r'\$([^$]+)\$', text)
    if m:
        return m[-1]
    m = re.findall(r'=([^=\n]+)', text)
    if m:
        return m[-1].strip()
    return text.strip()[:100]


def _assess_validity(score: float, issue_count: int) -> str:
    """生成合法性评估文本。"""
    if score >= 0.9:
        return "推导逻辑严密，步骤衔接合理"
    elif score >= 0.7:
        return "推导基本合法，部分衔接可更严密"
    elif score >= 0.5:
        return f"推导存在 {issue_count} 处问题，但整体可理解"
    elif score >= 0.3:
        return f"推导存在 {issue_count} 处断裂，建议补充中间步骤"
    else:
        return "推导链严重断裂，步骤间缺乏逻辑联系"
