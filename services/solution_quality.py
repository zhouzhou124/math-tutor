"""Solution quality scorer — lightweight post-generation quality check.

Scores a generated solution on structure, completeness, and block purity.
Non-blocking: always returns a score, never raises.
"""

import re


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
        r"(?<!\\)mathrmd[txuyz]",
        r"\\(?:alphas|betas|gammas|deltas|epsilons|etas|thetas|iotas|kappas|"
        r"lambdas|mus|nus|xis|pis|rhos|sigmas|taus|upsilons|phis|chis|psis|omegas|"
        r"Gammas|Deltas|Thetas|Lambdas|Xis|Pis|Sigmas|Upsilons|Phis|Psis|Omegas|"
        r"varphis|varepsilons|varthetas|varkappas|varrhos|"
        r"alph|bet|gam|del|eps|the|lam|sig|ome)(?=[^A-Za-z]|$)",
        r"\\var[φϕ]",
        r"\\[φϕα-ωΑ-Ω](?=[^a-zA-Z]|$)",
        r"(?<!\\)mathrm\s*d\s*[txuyz](?=[^a-zA-Z]|$)",
        r"(?<![\\a-zA-Z])[φϕ]\s*[\(\[\{]",
        r"(?<![\\a-zA-Z])[φϕ]\s*[_^]",
        r"(?<![\\a-zA-Z])[φϕ]\s*\)",
        r"(?<![\\a-zA-Z])[αβγδεζηθικλμνξπρστυχψω]\s*[\(\[\{]",
        r"(?<![\\a-zA-Z])[αβγδεζηθικλμνξπρστυχψω]\s*[_^]",
        r"(?<![\\a-zA-Z])[αβγδεζηθικλμνξπρστυχψω]\s*[<>=+\-\*/]",
        r"(?<![\\a-zA-Z])[Α-Ω]\s*[\(\[\{^_]",
        r"(?<![\\,]mathrm\{d\})\)\s*d[xyztu](?![a-zA-Z])",
        r"\\(?:varphi|phi)\s*\([^)]*\)\s*d[xyztu](?![a-zA-Z])",
        r"(?<!\\mathrm\{d\})(?<!\\,)\\d[xyztu](?![a-zA-Z])",
        r"(?<![\\a-zA-Z])d[xyztu]d[xyztu](?![a-zA-Z])",
    ]
    return sum(len(re.findall(p, s)) for p in patterns)


def has_broken_latex_fragments(text: str) -> bool:
    return count_broken_latex_fragments(text) > 0


def structured_has_broken_latex(structured: dict | None) -> bool:
    """P19-3: Check if any latex block in _structured has broken LaTeX."""
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        for block in step.get("blocks") or []:
            content = str(block.get("content") or "")
            if "\ufffd" in content:
                return True
            if block.get("type") != "latex":
                continue
            if has_broken_latex_fragments(content):
                return True
    if has_broken_latex_fragments(str(structured.get("final_answer") or "")):
        return True
    return False


def structured_has_dirty_latex(structured: dict | None) -> bool:
    """P32.1: Check if any display field in structured solution contains dirty LaTeX."""
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("body_markdown", "derivation_markdown", "explanation", "conclusion", "body"):
            val = str(step.get(key) or "")
            if val and has_broken_latex_fragments(val):
                return True
        for block in step.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            content = str(block.get("content") or "")
            if content and has_broken_latex_fragments(content):
                return True
        for formula in step.get("formulas") or []:
            if not isinstance(formula, dict):
                continue
            latex = str(formula.get("latex") or "")
            if latex and has_broken_latex_fragments(latex):
                return True
    fa = structured.get("final_answer")
    if isinstance(fa, dict):
        content = str(fa.get("content") or "")
        if content and has_broken_latex_fragments(content):
            return True
    elif fa:
        if has_broken_latex_fragments(str(fa)):
            return True
    return False


def solution_has_dirty_latex(solution: dict | None) -> bool:
    """P32.1: Check if any display field in solution contains dirty LaTeX."""
    if not isinstance(solution, dict):
        return False
    text = str(solution.get("standard_answer") or solution.get("answer") or "")
    if text and has_broken_latex_fragments(text):
        return True
    for step in solution.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for key in ("content", "body_markdown", "derivation_markdown", "explanation", "conclusion", "body"):
            val = str(step.get(key) or "")
            if val and has_broken_latex_fragments(val):
                return True
        for block in step.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            content = str(block.get("content") or "")
            if content and has_broken_latex_fragments(content):
                return True
    if structured_has_dirty_latex(solution.get("_structured")):
        return True
    for block in solution.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        content = str(block.get("content") or "")
        if content and has_broken_latex_fragments(content):
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
        for key in ("body_markdown", "derivation_markdown", "explanation"):
            if step.get(key):
                parts.append(str(step.get(key)))
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
        r"\\frac\{\s*\}",
        r"\\frac\{[^{}]+\}(?!\s*\{)",
        r"(?m)^\s*\}\{\s*$",
        r"(?m)^\s*\}\s*$",
        r"\\frac\{[^{}]*$",
        r"\\left\s*\\begin\b",
        r"\$\$\$+",
        r"\\(?:textcolor|color)\s*\{\s*red\s*\}",
        r"<span[^>]+color\s*:\s*red",
        r"\\u0000A[2-5]",
        r"\x00A[2-5]",
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
        "\ufffd",
    ]
    count = sum(len(re.findall(p, s)) for p in patterns)

    if "\\right" in s and s.count("\\right") > s.count("\\left"):
        count += s.count("\\right") - s.count("\\left")

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

    for match in re.finditer(r"\$\$([\s\S]*?)\$\$", s):
        content = match.group(1)
        if "$" in content:
            count += 1
        stripped_text_cmd = re.sub(r"\\text\{[^}]*\}", "", content)
        if re.search(r"[\u4e00-\u9fff]", stripped_text_cmd):
            count += 1

    if re.search(r"\$\s*\\(?:begin|end)\{(?:aligned|cases|array|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|split|gathered)\}\s*\$", s):
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


def _step_derivation_text(step: dict | None) -> str:
    if not isinstance(step, dict):
        return ""
    parts: list[str] = []
    for key in ("body_markdown", "derivation_markdown", "explanation"):
        value = str(step.get(key) or "").strip()
        if value:
            parts.append(value)
    for block in step.get("blocks") or []:
        if isinstance(block, dict) and block.get("content"):
            parts.append(str(block.get("content") or ""))
    return "\n".join(parts)


_DERIVATION_MARKERS = [
    "因为", "由于", "由", "利用", "根据", "代入", "化简", "整理", "解得",
    "可得", "得到", "推出", "所以", "故", "从而", "递推", "初值", "特征方程",
    "why", "because", "therefore",
    "鍥犱负", "鐢变簬", "鐢?", "鍒╃敤", "鏍规嵁", "浠ｅ叆", "鍖栫畝",
    "鏁寸悊", "瑙ｅ緱", "鍙緱", "寰楀埌", "鎺ㄥ嚭", "鎵€浠?", "鏁?",
]
_CONCLUSION_ONLY_MARKERS = [
    "最终答案", "最终结论", "综上", "证毕", "故答案", "故选",
    "鏈€缁堢瓟妗?", "鏈€缁堢粨璁?", "缁间笂", "璇佹瘯", "鏁呯瓟妗?", "鏁呴€?",
]


def _has_formula_like_content(text: str) -> bool:
    s = str(text or "")
    return bool(
        "$" in s
        or "\\" in s
        or any(ch in s for ch in "=^_")
        or any(ch in s for ch in "≤≥≠∈→")
    )


def structured_step_has_derivation(step: dict | None) -> bool:
    text = _step_derivation_text(step)
    compact = "".join(str(text or "").split())
    if len(compact) < 35:
        return False
    has_marker = any(marker and marker in text for marker in _DERIVATION_MARKERS)
    has_formula = _has_formula_like_content(text)
    if has_marker and has_formula:
        return True
    conclusion_only = any(marker and marker in text for marker in _CONCLUSION_ONLY_MARKERS)
    return bool(len(compact) >= 80 and has_formula and not conclusion_only)


def structured_has_derivations(structured: dict | None) -> bool:
    if not isinstance(structured, dict):
        return False
    steps = [s for s in (structured.get("steps") or []) if isinstance(s, dict)]
    if not steps:
        return False
    return all(structured_step_has_derivation(step) for step in steps)


def _structured_requires_derivation_gate(structured: dict | None) -> bool:
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        _injected = step.get("_body_markdown_injected")
        if not _injected and step.get("body_markdown"):
            return True
        if step.get("derivation_markdown") and not _injected:
            return True
        if step.get("explanation"):
            return True
    return False


def _subparts_from_question(question: dict | None) -> list[str]:
    import re

    qtext = str((question or {}).get("question") or "")
    patterns = [
        r"(?m)^\s*[（(]\s*([1-9])\s*[)）]\s*",
        r"第\s*[（(]?\s*([1-9])\s*[)）]?\s*问",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, qtext))
    unique: list[str] = []
    for n in found:
        if n not in unique:
            unique.append(n)
    return unique


def structured_derivations_cover_subparts(
    structured: dict | None,
    question: dict | None = None,
) -> tuple[bool, list[str]]:
    subparts = _subparts_from_question(question)
    if len(subparts) < 2:
        return True, []
    covered = {n: False for n in subparts}
    for step in (structured or {}).get("steps") or []:
        if not isinstance(step, dict):
            continue
        text = "\n".join([str(step.get("label") or ""), _step_derivation_text(step)])
        compact = "".join(text.split())
        matched = []
        for n in subparts:
            markers = [
                f"({n})", f"（{n}）", f"第{n}问", f"第({n})问",
                f"第（{n}）问", f"锛?{n}锛?", f"绗琝{n}闂?",
            ]
            if any(marker in compact for marker in markers):
                matched.append(n)
        for n in matched:
            if structured_step_has_derivation(step):
                covered[n] = True
    missing = [n for n, ok in covered.items() if not ok]
    return not missing, missing


def solution_has_detailed_steps(solution: dict | None, question: dict | None = None) -> bool:
    if not isinstance(solution, dict):
        return False
    text = _combined_solution_text(solution)
    structured = solution.get("_structured")
    step_count = max(structured_step_count(structured), raw_step_count(text))
    q_type = _question_type(question)
    if _structured_requires_derivation_gate(structured):
        if not structured_has_derivations(structured):
            return False
        covers_parts, _ = structured_derivations_cover_subparts(structured, question)
        if not covers_parts:
            return False

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

    subparts = _subparts_from_question(q)
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
    structured = solution.get("_structured") if isinstance(solution, dict) else None
    if _structured_requires_derivation_gate(structured):
        if not structured_has_derivations(structured):
            issues.append("missing_derivation_body")
        subpart_ok, missing_derivation_parts = structured_derivations_cover_subparts(
            structured, question
        )
        if not subpart_ok:
            issues.append("missing_subpart_derivations:" + ",".join(missing_derivation_parts))
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


# ═══════════════════════════════════════════════
#  P35: Malformed final answer detection
# ═══════════════════════════════════════════════

_MALFORMED_INTERVAL_PATTERNS = [
    re.compile(r'\(\s*[-+]?\s*,\s*[-+]?\d*\s*\)'),
    re.compile(r'\(\s*,\s*[-+]?\d+\s*\)'),
    re.compile(r'\([-+]?(?:∞|\\infty)\s*,\s*[-+]?\d+(?!\s*\))'),
    re.compile(r'(?<!\()\d+\s*,\s*[-+]?(?:∞|\\infty)\)'),
    re.compile(r'\(\s*\)'),
]


def detect_malformed_final_answer(solution: dict | None) -> list[str]:
    """P35: Detect malformed intervals and empty values in final answer."""
    if not isinstance(solution, dict):
        return []
    issues: list[str] = []
    texts: list[str] = []
    fa = solution.get("final_answer")
    if isinstance(fa, dict):
        texts.append(str(fa.get("content") or ""))
    elif fa:
        texts.append(str(fa))
    structured = solution.get("_structured")
    if isinstance(structured, dict):
        sfa = structured.get("final_answer")
        if isinstance(sfa, dict):
            texts.append(str(sfa.get("content") or ""))
        elif sfa:
            texts.append(str(sfa))
    for text in texts:
        for pat in _MALFORMED_INTERVAL_PATTERNS:
            if pat.search(text):
                issues.append("malformed_final_answer")
                return issues
    return issues


def detect_unformatted_equation_list(solution: dict | None) -> list[str]:
    """P35.1: Detect unformatted independent equation lists."""
    if not isinstance(solution, dict):
        return []
    issues: list[str] = []
    try:
        from latex_utils import is_independent_equation_list
        structured = solution.get("_structured")
        if isinstance(structured, dict):
            for step in structured.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                for block in step.get("blocks") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "latex" and is_independent_equation_list(str(block.get("content") or "")):
                        issues.append("unformatted_equation_list")
                        return issues
    except Exception:
        pass
    return issues


def detect_invalid_formula_source(solution: dict | None) -> list[str]:
    """P37.2: Detect raw/invalid formula sources."""
    if not isinstance(solution, dict):
        return []
    issues: list[str] = []
    try:
        from latex_utils import is_raw_or_invalid_latex_formula
        structured = solution.get("_structured")
        if isinstance(structured, dict):
            for step in structured.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                for block in step.get("blocks") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "latex" and is_raw_or_invalid_latex_formula(str(block.get("content") or "")):
                        issues.append("invalid_formula_source")
                        return issues
    except Exception:
        pass
    return issues


_RAW_SOURCE_LEAK_PATTERNS = [
    re.compile(r'##\s*步骤'),
    re.compile(r'##\s*关键知识点'),
    re.compile(r'##\s*易错提示'),
    re.compile(r'##\s*常见误区'),
    re.compile(r'##\s*秒杀技巧'),
    re.compile(r'<span[^>]+>'),
    re.compile(r'</span>'),
]


def detect_student_raw_source_leak(text: str) -> bool:
    """P37.6.3: Detect raw source leak in student-facing fields."""
    s = str(text or "")
    for pat in _RAW_SOURCE_LEAK_PATTERNS:
        if pat.search(s):
            return True
    return False


def structured_has_raw_source_leak(structured: dict | None) -> bool:
    """P37.6.3: Check if structured solution has raw source leak."""
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for block in step.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            content = str(block.get("content") or "")
            if content and detect_student_raw_source_leak(content):
                return True
    return False


# ═══════════════════════════════════════════════
#  P41: Derivation formula quality detection
# ═══════════════════════════════════════════════

_DETACHED_SUBSTITUTION_PATTERNS = [
    re.compile(r'^\s*[\(（]\s*[a-zA-Z]\s*$'),          # "(x" alone
    re.compile(r'^\s*=\s*[a-zA-Z][^)）]*[\)）]\s*$'),   # "=tu)" alone
    re.compile(r'^\s*[\(（]\s*[a-zA-Z]\s*=\s*$'),       # "(x =" alone
]

_TEXT_IN_LATEX_DISPLAY = re.compile(r'[一-鿿]{4,}')
_BARE_LIMIT_NOTATION = re.compile(r'(?<!\\)(?<!_)lim\s+[a-zA-Z]\s*(?:→|->)')
_MULTI_EQ_NO_ALIGNED = re.compile(r'(?<!\\)=(?!=).*?(?<!\\)=(?!=)')
_COMMA_SUBSTITUTION = re.compile(
    r'[,，]\s*[\(（][a-zA-Z]\s*=\s*[a-zA-Z][^)）]*[\)）]'
)


def detect_broken_derivation_formula_block(text: str) -> list[str]:
    """P41: Detect broken derivation formula patterns.

    Returns list of issue names (empty if clean):
    - detached_substitution_annotation: "(x" / "=tu)" split fragments
    - text_inside_latex_display: Chinese sentences in display math
    - raw_limit_notation: bare "lim t → 0+" not converted to \\lim
    - unaligned_derivation_chain: multiple = without aligned environment
    - comma_annotation_in_formula: ", (x=tu)" should be \\quad
    """
    s = str(text or "")
    if not s.strip():
        return []

    issues = []

    # Check for detached substitution fragments
    lines = s.split('\n')
    for line in lines:
        for pat in _DETACHED_SUBSTITUTION_PATTERNS:
            if pat.search(line):
                issues.append("detached_substitution_annotation")
                break

    # Check for Chinese in display math context
    if re.search(r'\$\$|\\\[|\\begin\{aligned', s):
        # Only check non-text regions
        cleaned = re.sub(r'\\text\{[^}]*\}', '', s)
        if _TEXT_IN_LATEX_DISPLAY.search(cleaned):
            issues.append("text_inside_latex_display")

    # Check for bare lim notation
    if _BARE_LIMIT_NOTATION.search(s):
        issues.append("raw_limit_notation")

    # Check for multi-= without aligned
    if r'\begin{aligned}' not in s and r'\begin{align}' not in s:
        clean = re.sub(r'\{[^}]*\}', '', s)
        clean = re.sub(r'(?:\\neq|\\ne|\\geq|\\leq|\\approx|\\equiv|==)', '', clean)
        if len(re.findall(r'(?<!\\)=(?!=)', clean)) >= 3:
            issues.append("unaligned_derivation_chain")

    # Check for comma substitution annotation
    if _COMMA_SUBSTITUTION.search(s):
        issues.append("comma_annotation_in_formula")

    return issues


# P41.2: LaTeX environment detection
_RE_ALIGNED_BEGIN = re.compile(r'\\begin\{aligned\}')
_RE_ALIGNED_END = re.compile(r'\\end\{aligned\}')
_RE_ESCAPED_AMP = re.compile(r'\\&=')
_RE_ORPHAN_AMP_EQ = re.compile(r'(?<!\\)&=\s')


def detect_broken_latex_environment(text: str) -> list[str]:
    """P41.2: Detect broken LaTeX environment patterns.

    Returns list of issue names (empty if clean):
    - orphan_aligned_begin: has \\begin{aligned} without \\end{aligned}
    - orphan_aligned_end: has \\end{aligned} without \\begin{aligned}
    - escaped_alignment_marker: has \\&= instead of &=
    - aligned_environment_in_text_block: aligned env found in what should be text
    - orphan_alignment_marker: standalone &= without surrounding aligned env
    - unclosed_latex_environment: generic unclosed env
    """
    s = str(text or "")
    if not s.strip():
        return []

    issues = []
    begins = _RE_ALIGNED_BEGIN.findall(s)
    ends = _RE_ALIGNED_END.findall(s)

    if len(begins) > len(ends):
        issues.append("orphan_aligned_begin")
    elif len(ends) > len(begins):
        issues.append("orphan_aligned_end")

    if _RE_ESCAPED_AMP.search(s):
        issues.append("escaped_alignment_marker")

    # Orphan &= outside of aligned environment
    if not begins and _RE_ORPHAN_AMP_EQ.search(s):
        issues.append("orphan_alignment_marker")

    return issues


# P41.3: Cases environment detection
_RE_BROKEN_SPACING_IN_TEXT = re.compile(
    r'(?<!\\)\\\[\d*\.?\d+(?:pt|mm|cm|em|ex|baselineskip)\]'
)
_RE_CASES_ENV = re.compile(r'\\begin\{cases\}')
_RE_BARE_BRACKET_IN_CASES = re.compile(r'(?<!\\)\\\[(?!\d+(?:\.\d+)?(?:pt|mm|cm|em|ex))')


def detect_broken_cases_environment(text: str) -> list[str]:
    """P41.3: Detect broken cases environment patterns.

    Returns list of issue names (empty if clean):
    - broken_row_spacing_marker: \\[6pt] or \\[4pt] etc.
    - cases_missing_alignment_ampersand: cases line has condition but no &
    - cases_environment_in_text_block: cases found in text context
    - orphan_display_delimiter_in_cases: bare \\[ or \\] inside cases
    """
    s = str(text or "")
    if not s.strip():
        return []

    issues = []

    # Check for broken row spacing markers
    if _RE_BROKEN_SPACING_IN_TEXT.search(s):
        issues.append("broken_row_spacing_marker")

    # Check cases-specific issues
    if r'\begin{cases}' in s:
        # Extract cases body
        cases_match = re.search(r'\\begin\{cases\}(.*?)\\end\{cases\}', s, re.S)
        if cases_match:
            body = cases_match.group(1)
            lines = [l.strip() for l in body.split('\\\\') if l.strip()]
            for line in lines:
                # Check for bare \[ inside cases (not spacing)
                if _RE_BARE_BRACKET_IN_CASES.search(line):
                    issues.append("orphan_display_delimiter_in_cases")
                    break

            # Check for lines with conditions but no &
            for line in lines:
                if ',' in line and '&' not in line:
                    # Might be: expr, condition
                    parts = line.split(',')
                    if len(parts) >= 2:
                        last_part = parts[-1].strip()
                        # If last part looks like a condition (has <, >, \le, etc.)
                        if re.search(r'[<>≤≥\\le|\\ge|\\lt|\\gt]', last_part):
                            issues.append("cases_missing_alignment_ampersand")
                            break

    return issues


# P41.4: Probability formula fragment detection
_RE_BARE_FRAC_PATTERN = re.compile(r'(?<![\\a-zA-Z])d?frac\d\d')
_RE_ORPHAN_DX = re.compile(r'^\s*(?:d[xyzt])\s*$', re.M)
_RE_ORPHAN_BANG_LINE = re.compile(r'^\s*!\s*$', re.M)
_RE_ORPHAN_SEMI_LINE = re.compile(r'^\s*;\s*$', re.M)
_RE_BANG_BEFORE_PAREN = re.compile(r'!\s*[\({]')


def detect_probability_formula_fragment_leak(text: str) -> list[str]:
    """P41.4: Detect probability formula fragment patterns.

    Returns list of issue names (empty if clean):
    - bare_fraction_command: frac14 / dfrac18 without backslash
    - orphan_differential_line: dx/dy/dt on its own line
    - orphan_marker_bang: standalone ! or !( / !{
    - orphan_semicolon_line: standalone ; on its own line
    - broken_left_marker: ! before ( or { (should be \\left)
    - fragmented_cdf_pdf_formula: CDF/PDF derivation not in aligned
    """
    s = str(text or "")
    if not s.strip():
        return []

    issues = []

    if _RE_BARE_FRAC_PATTERN.search(s):
        issues.append("bare_fraction_command")

    if _RE_ORPHAN_DX.search(s):
        issues.append("orphan_differential_line")

    if _RE_ORPHAN_BANG_LINE.search(s):
        issues.append("orphan_marker_bang")

    if _RE_ORPHAN_SEMI_LINE.search(s):
        issues.append("orphan_semicolon_line")

    if _RE_BANG_BEFORE_PAREN.search(s):
        issues.append("broken_left_marker")

    return issues
