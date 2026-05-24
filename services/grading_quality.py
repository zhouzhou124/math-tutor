"""Grading result contract validator — post-grading sanity checks.

Validates that grading result dicts conform to the expected contract.
Non-blocking: always returns a dict, never raises.
"""


def validate_grading_result_contract(gr: dict, total_score: int = 10) -> dict:
    """Validate a grading result dict against the contract.

    Checks:
      - total is numeric and in [0, total_score]
      - step_score + result_score not obviously wrong
      - low scores have deductions
      - non-perfect scores have comments
    """
    issues = []

    # ── total must be numeric and within range ──
    total = gr.get("total", 0)
    try:
        total = float(total)
    except (TypeError, ValueError):
        issues.append("total 不是数字")
        total = 0

    if total < 0:
        issues.append(f"分数为负 ({total})")
    if total > total_score + 0.01:
        issues.append(f"分数超出满分 (total={total}, max={total_score})")

    # ── step_score + result_score sanity ──
    step_score = float(gr.get("step_score", 0) or 0)
    result_score = float(gr.get("result_score", 0) or 0)
    if step_score + result_score > total_score + 0.5:
        issues.append(
            f"步骤分({step_score}) + 结果分({result_score}) 超出满分({total_score})"
        )

    # ── Low score without deductions is suspicious ──
    if total < total_score * 0.6:
        deductions = gr.get("deductions") or []
        if not deductions:
            issues.append("低分但无扣分项（deductions 为空）")

    # ── Non-perfect score without comment ──
    if total < total_score * 0.9:
        comment = (gr.get("comment") or "").strip()
        if not comment:
            issues.append("非满分但缺少评语（comment 为空）")

    # ── step_analysis should be a list ──
    step_analysis = gr.get("step_analysis")
    if step_analysis is not None and not isinstance(step_analysis, list):
        issues.append("step_analysis 不是列表")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total": total,
        "max_score": total_score,
    }
