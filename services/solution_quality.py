"""Solution quality scorer — lightweight post-generation quality check.

Scores a generated solution on structure, completeness, and block purity.
Non-blocking: always returns a score, never raises.
"""


def score_solution_quality(solution: dict) -> dict:
    """Score the quality of a generated structured solution. 0-100 scale.

    Checks:
      - Step count
      - Final answer presence
      - LatexBlock purity (no Chinese, no markdown leaks)
      - TextBlock purity (no LaTeX commands)
      - Minimum formula count
      - Minimum explanation count
    """
    structured = solution.get("_structured") or {}
    steps = structured.get("steps") or []

    score = 100
    issues = []

    # ── Structural checks ──
    if len(steps) < 2:
        score -= 25
        issues.append("步骤数量偏少（<2步），可能缺少推导过程")

    if not structured.get("final_answer"):
        score -= 20
        issues.append("缺少最终答案（final_answer）")

    # ── Block-level purity checks ──
    latex_blocks = 0
    text_blocks = 0

    for step in steps:
        for b in step.get("blocks", []):
            t = b.get("type", "")
            content = b.get("content", "") or ""

            if t == "latex":
                latex_blocks += 1
                # LatexBlock must not contain Chinese outside \\text{}
                _stripped = _strip_text_cmd(content)
                if any('一' <= ch <= '鿿' for ch in _stripped):
                    score -= 10
                    issues.append("latex 块中含中文字符（应放入 text 块）")

            elif t == "text":
                text_blocks += 1
                if '\\' in content:
                    score -= 10
                    issues.append("text 块中含 LaTeX 命令（应放入 latex 块）")

    if latex_blocks == 0:
        score -= 20
        issues.append("缺少关键公式（无 latex 块）")

    if text_blocks == 0 and len(steps) >= 2:
        score -= 10
        issues.append("缺少文字说明（无 text 块）")

    # ── Deduplicate issues ──
    seen = set()
    unique = []
    for i in issues:
        if i not in seen:
            seen.add(i)
            unique.append(i)

    return {
        "score": max(0, min(100, score)),
        "issues": unique,
        "latex_blocks": latex_blocks,
        "text_blocks": text_blocks,
        "step_count": len(steps),
    }


def _strip_text_cmd(content: str) -> str:
    """Remove \\text{{...}} regions from LaTeX content for purity check."""
    import re
    return re.sub(r'\\text\{[^}]*\}', '', content)
