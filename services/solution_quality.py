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


# ═══════════════════════════════════════════════
#  P19-2: Broken LaTeX fragment detection
# ═══════════════════════════════════════════════

def count_broken_latex_fragments(text: str) -> int:
    """Count structural LaTeX issues in generated answer text."""
    s = str(text or "")
    patterns = [
        r"\\frac\{\}",                 # empty numerator
        r"\\frac\{[^{}]+\}(?!\s*\{)",  # \frac{num} without {den}
        r"(?m)^\s*\}\{\s*$",           # orphan }{ on its own line
        r"(?m)^\s*\}\s*$",             # orphan } on its own line
        r"\\frac\{[^{}]*$",            # unclosed frac
        r"�",                          # encoding artifact
    ]
    import re
    return sum(len(re.findall(p, s)) for p in patterns)


def has_broken_latex_fragments(text: str) -> bool:
    return count_broken_latex_fragments(text) > 0


def structured_has_broken_latex(structured: dict | None) -> bool:
    """P19-3: Check if any latex block in _structured has broken LaTeX."""
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        for block in step.get("blocks") or []:
            if block.get("type") != "latex":
                continue
            if has_broken_latex_fragments(str(block.get("content") or "")):
                return True
    if has_broken_latex_fragments(str(structured.get("final_answer") or "")):
        return True
    return False


def structured_has_real_content(structured: dict | None) -> bool:
    """P19-3: Check if structured has at least one non-empty block."""
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        for block in step.get("blocks") or []:
            c = str(block.get("content") or "").strip()
            if c and c not in {"无内容", "（无内容）", "(无内容)"}:
                return True
    fa = str(structured.get("final_answer") or "").strip()
    return bool(fa and fa not in {"无内容", "（无内容）", "(无内容)"})


def solution_is_renderable(solution: dict | None) -> bool:
    """P19-3: Full gate — solution must have clean content to be renderable."""
    if not isinstance(solution, dict):
        return False
    text = str(solution.get("standard_answer") or solution.get("answer") or "")
    if has_broken_latex_fragments(text):
        return False
    structured = solution.get("_structured")
    if structured_has_broken_latex(structured):
        return False
    if structured_has_real_content(structured):
        return True
    if raw_step_count(text) >= 2 and len(text.strip()) >= 40:
        return True
    return len(text.strip()) >= 80


# ═══════════════════════════════════════════════
#  P19-5: Solution completeness gate
# ═══════════════════════════════════════════════

_FINAL_MARKERS = ["综上", "故", "因此", "即证", "得证", "证毕", "最终答案"]
_CHOICE_MARKERS = ["故选", "正确选项", "答案为"]
_FILL_MARKERS = ["最终答案", "填空答案", "故答案为"]
_EMPTY_MARKERS = {"", "无内容", "（无内容）", "(无内容)", "暂无可用标准解答。"}
_TRUNCATION_ENDINGS = [
    "由", "故", "因此", "所以", "可得", "从而", "即", "则",
    "=", "≤", "≥", "+", "-", r"\frac", r"\begin",
]


def structured_step_count(structured: dict | None) -> int:
    if not isinstance(structured, dict):
        return 0
    return len(structured.get("steps") or [])


def structured_has_final_answer(structured: dict | None) -> bool:
    if not isinstance(structured, dict):
        return False
    fa = str(structured.get("final_answer") or "").strip()
    if fa and fa not in _EMPTY_MARKERS:
        return True
    steps = structured.get("steps") or []
    tail = "\n".join(
        str(block.get("content") or "")
        for step in steps[-2:]
        for block in (step.get("blocks") or [])
    )
    return any(m in tail for m in _FINAL_MARKERS)


def structured_text(structured: dict | None) -> str:
    """Flatten structured solution text for lightweight completeness checks."""
    if not isinstance(structured, dict):
        return ""
    parts = []
    for step in structured.get("steps") or []:
        if isinstance(step, dict):
            parts.append(str(step.get("label") or ""))
            for block in step.get("blocks") or []:
                if isinstance(block, dict):
                    parts.append(str(block.get("content") or ""))
    fa = structured.get("final_answer")
    if isinstance(fa, dict):
        parts.append(str(fa.get("content") or ""))
    else:
        parts.append(str(fa or ""))
    return "\n".join(p for p in parts if p)


def raw_has_final_marker(text: str) -> bool:
    s = str(text or "")
    return any(m in s for m in _FINAL_MARKERS)


def looks_truncated(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    if any(s.endswith(x) for x in _TRUNCATION_ENDINGS):
        return True
    if s.count("$$") % 2 == 1:
        return True
    return False


def question_requires_proof_completion(question: dict | None) -> bool:
    q = str((question or {}).get("question") or "")
    qt = str((question or {}).get("question_type") or "")
    return "证明" in q or "证明" in qt


def _has_any_marker(text: str, markers: list[str]) -> bool:
    s = str(text or "")
    return any(m in s for m in markers)


def solution_is_complete(
    solution: dict | None,
    question: dict | None = None,
) -> bool:
    if not isinstance(solution, dict):
        return False
    text = str(solution.get("standard_answer") or solution.get("answer") or "").strip()
    structured = solution.get("_structured")
    if text in _EMPTY_MARKERS:
        return False
    if looks_truncated(text):
        return False
    sc = structured_step_count(structured)
    if sc <= 0 and len(text) < 120:
        return False

    q_type = str((question or {}).get("question_type") or "")
    has_final = structured_has_final_answer(structured) or raw_has_final_marker(text)
    combined = "\n".join([text, structured_text(structured)])

    # 证明题：≥2 步骤 + 最终结论
    if question_requires_proof_completion(question):
        return sc >= 2 and has_final

    # 选择题：必须解释正确选项
    if "选择" in q_type:
        return sc >= 2 and has_final and _has_any_marker(combined, _CHOICE_MARKERS + ["A", "B", "C", "D"])

    # 填空题：必须有最终答案
    if "填空" in q_type:
        return sc >= 2 and has_final and _has_any_marker(combined, _FILL_MARKERS + ["答案"])

    # 解答题/通用：有足够内容 + 结论
    if len(text) >= 120:
        return has_final
    return False


# ============================================================================
#  P24: Unified standard-solution quality gate
# ============================================================================

_FINAL_MARKERS = [
    "最终答案", "最终结论", "综上", "故", "因此", "所以",
    "即证", "得证", "证毕", "命题得证", "正确选项", "答案为",
]
_CHOICE_MARKERS = ["正确选项", "故选", "选", "答案为"]
_FILL_MARKERS = ["最终答案", "填空答案", "故答案为", "答案为"]
_EMPTY_MARKERS = {
    "", "无内容", "（无内容）", "(无内容)", "暂无可用标准解答。",
    "暂无标准答案", "解答生成失败", "请配置 API Key",
}
_BAD_DRAFT_MARKERS = [
    "此路不通", "不对，", "换一种思路", "重新来", "草稿",
    "无法确定", "我无法", "抱歉", "作为AI",
]
_TRUNCATION_ENDINGS = [
    "由", "故", "因此", "所以", "可得", "从而", "即", "则",
    "=", "≤", "≥", "+", "-", r"\frac", r"\begin", r"\left",
]


def _solution_text(solution: dict | None) -> str:
    if not isinstance(solution, dict):
        return ""
    return str(solution.get("standard_answer") or solution.get("answer") or "").strip()


def _structured_text(structured: dict | None) -> str:
    if not isinstance(structured, dict):
        return ""
    parts: list[str] = []
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if step.get("label"):
            parts.append(str(step.get("label")))
        for block in step.get("blocks") or []:
            if isinstance(block, dict) and block.get("content"):
                parts.append(str(block.get("content")))
    fa = structured.get("final_answer")
    if isinstance(fa, dict):
        parts.append(str(fa.get("content") or ""))
    elif fa:
        parts.append(str(fa))
    return "\n".join(parts)


def _combined_solution_text(solution: dict | None) -> str:
    if not isinstance(solution, dict):
        return ""
    return "\n".join(
        part for part in [
            _solution_text(solution),
            _structured_text(solution.get("_structured")),
        ] if part
    )


def count_broken_latex_fragments(text: str) -> int:
    """Count structural LaTeX issues that commonly break rendering."""
    import re

    s = str(text or "")
    patterns = [
        r"\\frac\{\}",
        r"\\frac\{[^{}]+\}(?!\s*\{)",
        r"(?m)^\s*\}\{\s*$",
        r"(?m)^\s*\}\s*$",
        r"\\frac\{[^{}]*$",
        "\ufffd",
    ]
    count = sum(len(re.findall(p, s)) for p in patterns)

    # Math delimiters should be balanced after display blocks are removed.
    if s.count("$$") % 2:
        count += 1
    no_display = re.sub(r"\$\$.*?\$\$", "", s, flags=re.S)
    if no_display.count("$") % 2:
        count += 1

    # Braces inside LaTeX commands should not obviously underflow.
    depth = 0
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                count += 1
                depth = 0
    if depth:
        count += 1
    return count


def has_broken_latex_fragments(text: str) -> bool:
    return count_broken_latex_fragments(text) > 0


def raw_has_final_marker(text: str) -> bool:
    s = str(text or "")
    return any(marker in s for marker in _FINAL_MARKERS)


def looks_truncated(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    if any(s.endswith(x) for x in _TRUNCATION_ENDINGS):
        return True
    if s.count("$$") % 2 == 1:
        return True
    return False


def structured_step_count(structured: dict | None) -> int:
    if not isinstance(structured, dict):
        return 0
    return len([s for s in (structured.get("steps") or []) if isinstance(s, dict)])


def raw_step_count(text: str) -> int:
    import re

    s = str(text or "")
    patterns = [
        r"(?:\#{1,3}\s*)?步骤\s*\d+",
        r"(?:\#{1,3}\s*)?第\s*\d+\s*步",
        r"(?:\#{1,3}\s*)?Step\s*\d+",
    ]
    return max((len(re.findall(p, s, flags=re.I)) for p in patterns), default=0)


def structured_has_final_answer(structured: dict | None) -> bool:
    if not isinstance(structured, dict):
        return False
    fa = structured.get("final_answer")
    if isinstance(fa, dict):
        content = str(fa.get("content") or "").strip()
    else:
        content = str(fa or "").strip()
    if content and not any(empty in content for empty in _EMPTY_MARKERS):
        return True
    return raw_has_final_marker(_structured_text(structured))


def question_requires_proof_completion(question: dict | None) -> bool:
    q = str((question or {}).get("question") or "")
    qt = str((question or {}).get("question_type") or "")
    return "证明" in q or "证明" in qt


def _question_type(question: dict | None) -> str:
    return str((question or {}).get("question_type") or "")


def _has_any_marker(text: str, markers: list[str]) -> bool:
    return any(m in str(text or "") for m in markers)


def solution_has_detailed_steps(solution: dict | None, question: dict | None = None) -> bool:
    if not isinstance(solution, dict):
        return False
    text = _combined_solution_text(solution)
    structured = solution.get("_structured")
    step_count = max(structured_step_count(structured), raw_step_count(text))
    q_type = _question_type(question)

    if "选择" in q_type:
        return step_count >= 2 or len(text) >= 260
    if "填空" in q_type:
        return step_count >= 2 or len(text) >= 220
    if question_requires_proof_completion(question):
        return step_count >= 2
    return step_count >= 2 or len(text) >= 260


def solution_covers_question_requirements(
    solution: dict | None,
    question: dict | None = None,
) -> tuple[bool, list[str]]:
    import re

    issues: list[str] = []
    text = _combined_solution_text(solution)
    q = question or {}
    q_type = _question_type(q)

    subparts = sorted(set(re.findall(r"[（(]\s*([1-9])\s*[)）]", str(q.get("question") or ""))))
    if len(subparts) >= 2:
        missing = [
            n for n in subparts
            if not re.search(rf"(?:[（(]\s*{n}\s*[)）]|第\s*{n}\s*[问步])", text)
        ]
        if missing:
            issues.append("missing_subparts:" + ",".join(missing))

    options = q.get("options") or {}
    if "选择" in q_type and isinstance(options, dict) and len(options) >= 3:
        mentioned = {
            letter for letter in options
            if re.search(rf"(?:选项\s*)?{re.escape(str(letter))}\b", text)
        }
        if len(mentioned) < min(3, len(options)):
            issues.append("choice_options_not_analyzed")

    if question_requires_proof_completion(q) and not raw_has_final_marker(text):
        issues.append("proof_missing_final_conclusion")

    return not issues, issues


def solution_is_logically_plausible(solution: dict | None) -> tuple[bool, list[str]]:
    text = _combined_solution_text(solution)
    issues: list[str] = []
    if any(marker in text for marker in _BAD_DRAFT_MARKERS):
        issues.append("contains_draft_or_uncertainty_marker")
    if any(empty in text for empty in _EMPTY_MARKERS if empty):
        issues.append("contains_empty_or_failure_marker")
    if text.count("## 关键知识点") >= 1 and raw_step_count(text) == 0:
        issues.append("metadata_only_solution")
    return not issues, issues


def solution_is_renderable(solution: dict | None) -> bool:
    if not isinstance(solution, dict):
        return False
    text = _solution_text(solution)
    structured = solution.get("_structured")
    if has_broken_latex_fragments(text):
        return False
    if structured_has_broken_latex(structured):
        return False
    if structured_has_real_content(structured):
        return True
    if raw_step_count(text) >= 2 and len(text.strip()) >= 40:
        return True
    return len(text.strip()) >= 80


def solution_is_complete(solution: dict | None, question: dict | None = None) -> bool:
    if not isinstance(solution, dict):
        return False
    text = _combined_solution_text(solution)
    raw = _solution_text(solution)
    if not text or any(raw == empty for empty in _EMPTY_MARKERS):
        return False
    if looks_truncated(raw or text):
        return False
    if not solution_has_detailed_steps(solution, question):
        return False

    structured = solution.get("_structured")
    has_final = structured_has_final_answer(structured) or raw_has_final_marker(text)
    q_type = _question_type(question)

    if question_requires_proof_completion(question):
        return has_final
    if "选择" in q_type:
        return has_final and (
            _has_any_marker(text, _CHOICE_MARKERS)
            or structured_has_final_answer(structured)
        )
    if "填空" in q_type:
        return has_final and (
            _has_any_marker(text, _FILL_MARKERS)
            or structured_has_final_answer(structured)
        )
    return has_final


def solution_quality_report(solution: dict | None, question: dict | None = None) -> dict:
    """Return a strict, actionable quality report for generated standard answers."""
    issues: list[str] = []
    renderable = solution_is_renderable(solution)
    if not renderable:
        issues.append("not_renderable")
    complete = solution_is_complete(solution, question)
    if not complete:
        issues.append("incomplete")
    detailed = solution_has_detailed_steps(solution, question)
    if not detailed:
        issues.append("missing_detailed_steps")
    covers, cover_issues = solution_covers_question_requirements(solution, question)
    issues.extend(cover_issues)
    plausible, logic_issues = solution_is_logically_plausible(solution)
    issues.extend(logic_issues)

    unique: list[str] = []
    for issue in issues:
        if issue not in unique:
            unique.append(issue)

    ok = renderable and complete and detailed and covers and plausible
    return {
        "ok": ok,
        "renderable": renderable,
        "complete": complete,
        "detailed": detailed,
        "covers_requirements": covers,
        "logically_plausible": plausible,
        "issues": unique,
        "should_regenerate": not ok,
    }
