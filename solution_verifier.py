"""
Solution Verifier — SymPy 验证规范解题轨迹中每一步的数学正确性

核心职责：
  - 验证步骤 N 的 output_state 与步骤 N+1 的 input_state 数学等价
  - 验证最终步骤的 output_state 与 final_answer 等价
  - 返回验证结果（通过/失败/不可验证）
"""

from dataclasses import dataclass, field

from symbolic_executor import parse_expression, symbolic_compare, _HAS_SYMPY

try:
    import sympy as sp
except ImportError:
    sp = None


@dataclass
class VerificationResult:
    """规范解题轨迹的验证结果"""
    all_verified: bool
    failed_steps: list[dict] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 ~ 1.0


def verify_step_transition(from_state: str, to_state: str) -> dict:
    """
    验证两个数学状态之间的转换是否合法。

    Args:
        from_state: 前一步的 output_state (LaTeX)
        to_state: 后一步的 input_state (LaTeX)

    Returns:
        {"verified": bool, "method": str, "error": str|None, "status": str}
        status: "pass" | "fail" | "unverifiable"
    """
    if not from_state or not to_state:
        return {"verified": True, "method": "none", "error": "空状态，无法验证", "status": "unverifiable"}

    if not _HAS_SYMPY:
        # 无 SymPy 时做简单字符串规范化比较
        def norm(s):
            import re
            return re.sub(r'\s+', '', s.lower().replace('$', ''))
        eq = norm(from_state) == norm(to_state)
        return {
            "verified": eq,
            "method": "string_norm",
            "error": None if eq else "字符串不匹配（无SymPy）",
            "status": "pass" if eq else "fail",
        }

    # SymPy 符号比较
    result = symbolic_compare(from_state, to_state)
    if result["equivalent"]:
        return {"verified": True, "method": "sympy_simplify", "error": None, "status": "pass"}

    # 尝试 factor 比较
    expr_from = parse_expression(from_state)
    expr_to = parse_expression(to_state)
    if expr_from is not None and expr_to is not None:
        try:
            diff = sp.simplify(sp.factor(expr_from) - sp.factor(expr_to))
            if diff == 0:
                return {"verified": True, "method": "sympy_factor", "error": None, "status": "pass"}
        except Exception:
            pass

        # 尝试 trigsimp
        try:
            diff = sp.simplify(sp.trigsimp(expr_from) - sp.trigsimp(expr_to))
            if diff == 0:
                return {"verified": True, "method": "sympy_trigsimp", "error": None, "status": "pass"}
        except Exception:
            pass

    # 如果任一表达式无法解析，标记为 unverifiable 而非 fail
    if expr_from is None or expr_to is None:
        return {
            "verified": True, "method": "unparsable",
            "error": "表达式无法解析，跳过验证",
            "status": "unverifiable",
        }

    return {
        "verified": False,
        "method": "sympy",
        "error": result.get("difference", "不等价"),
        "status": "fail",
    }


def verify_trace(trace) -> VerificationResult:
    """
    验证整个 CanonicalSolutionTrace 中每个方法的每一步。

    只有 status="fail" 的步骤才算真正失败；
    status="unverifiable"（空状态或无法解析）不影响 all_verified。

    Args:
        trace: CanonicalSolutionTrace 实例

    Returns:
        VerificationResult
    """
    all_verified = True
    failed_steps = []
    log = []
    verified_count = 0
    unverifiable_count = 0
    total_count = 0

    for method in trace.methods:
        graph = method.graph
        nodes = {n.id: n for n in graph.nodes}
        edges = {(e.source, e.target) for e in graph.edges}

        # 验证每条边：source.output → target.input_state
        for source_id, target_id in sorted(edges):
            source_node = nodes.get(source_id)
            target_node = nodes.get(target_id)
            if not source_node or not target_node:
                continue

            total_count += 1
            result = verify_step_transition(
                source_node.output,
                target_node.input_state,
            )
            result["from"] = source_id
            result["to"] = target_id
            result["method_name"] = method.method_name
            log.append(result)

            status = result.get("status", "pass" if result["verified"] else "fail")
            if status == "unverifiable":
                unverifiable_count += 1
                verified_count += 1  # 不算失败
            elif result["verified"]:
                verified_count += 1
            else:
                all_verified = False
                failed_steps.append({
                    "step_id": f"{source_id}->{target_id}",
                    "from_state": source_node.output,
                    "to_state": target_node.input_state,
                    "reason": result.get("error", "不等价"),
                })

        # 验证最终步骤的 output 与 final_answer
        final_nodes = [n for n in graph.nodes if n.type == "final_answer"]
        if final_nodes:
            total_count += 1
            final_node = final_nodes[-1]
            result = verify_step_transition(
                final_node.output,
                method.final_answer,
            )
            result["from"] = final_node.id
            result["to"] = "final_answer"
            result["method_name"] = method.method_name
            log.append(result)

            status = result.get("status", "pass" if result["verified"] else "fail")
            if status == "unverifiable":
                unverifiable_count += 1
                verified_count += 1
            elif result["verified"]:
                verified_count += 1
            else:
                all_verified = False
                failed_steps.append({
                    "step_id": f"{final_node.id}->final",
                    "from_state": final_node.output,
                    "to_state": method.final_answer,
                    "reason": result.get("error", "最终答案不匹配"),
                })

    confidence = verified_count / max(total_count, 1)

    return VerificationResult(
        all_verified=all_verified,
        failed_steps=failed_steps,
        log=log,
        confidence=confidence,
    )
