"""Grading result & solution adapters — unified data contracts.

All grading engines produce result dicts through normalize_grading_result()
so the renderer, error notebook, and persistence layers see the same shape.
"""

from __future__ import annotations
import html
import os
import re
from typing import Any

# P19-4/P24: increment when canonical solution schema or quality contract changes
SOLUTION_FORMAT_VERSION = "p24_solution_quality_gate"
COMPILED_IR_VERSION = "p29_canonical_ir_markdown_v1"


def _flag_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _canonical_ir_for_solution(raw: dict[str, Any]) -> dict[str, Any] | None:
    ir = raw.get("_solution_ir") or raw.get("solution_ir") or raw.get("_canonical_ir")
    return ir if isinstance(ir, dict) else None


def _failed_compiled_report(error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "renderable": False,
        "complete": False,
        "detailed": False,
        "covers_requirements": False,
        "logically_plausible": False,
        "issues": [error or "ir_compile_failed"],
        "should_regenerate": True,
    }


def _compiled_output_fallback_reason(
    *,
    compiled: str,
    compiled_report: dict[str, Any],
    legacy_text: str,
) -> str:
    """Return empty string only when compiled output is safe to use."""
    compiled_text = str(compiled or "")
    if not compiled_text.strip():
        return "compiled_empty"
    if "$$$" in compiled_text:
        return "compiled_bad_latex"
    if "\x00" in compiled_text or "\ufffd" in compiled_text or "\\u0000" in compiled_text:
        return "compiled_control_chars"
    if compiled_text.count("$$") % 2 != 0:
        return "compiled_unpaired_display_math"
    if not compiled_report.get("renderable"):
        return "compiled_not_renderable"
    if not compiled_report.get("complete"):
        return "compiled_incomplete"
    if not compiled_report.get("ok"):
        return "compiled_quality_gate_failed"
    try:
        from services.solution_quality import has_broken_latex_fragments
        if has_broken_latex_fragments(compiled_text):
            return "compiled_bad_latex"
    except Exception:
        return "compiled_bad_latex"

    compiled_len = len(compiled_text.strip())
    legacy_len = len(str(legacy_text or "").strip())
    if legacy_len >= 200 and compiled_len < max(120, int(legacy_len * 0.5)):
        return "compiled_too_short"
    return ""


def _apply_solution_ir_shadow(solution: dict[str, Any]) -> dict[str, Any]:
    """Compile _solution_ir in shadow mode without affecting the normal path."""
    s = dict(solution or {})
    compiled_output_enabled = _flag_enabled("ENABLE_SOLUTION_IR_COMPILED_OUTPUT", default=True)
    shadow_enabled = _flag_enabled("ENABLE_SOLUTION_IR_SHADOW", default=True) or compiled_output_enabled

    s["ir_shadow_enabled"] = bool(shadow_enabled)
    s.setdefault("standard_solution_source", "legacy")
    s.setdefault("_used_compiled_standard_answer", False)
    if not shadow_enabled:
        return s

    s.setdefault("ir_compile_ok", False)
    s.setdefault("ir_compile_error", "")
    s.setdefault("compiled_renderable", False)
    s.setdefault("compiled_complete", False)
    s.setdefault("compiled_markdown_chars", 0)
    s.setdefault("legacy_markdown_chars", len(str(s.get("standard_answer") or s.get("answer") or "")))
    s.setdefault("_compiled_fallback_reason", "")

    ir = _canonical_ir_for_solution(s)
    if not isinstance(ir, dict):
        s["ir_compile_error"] = "missing_solution_ir"
        s["_compiled_fallback_reason"] = "missing_solution_ir"
        s["_compiled_quality_report"] = _failed_compiled_report("missing_solution_ir")
        return s

    try:
        import copy
        from semantic_output import validate_canonical_ir
        model, errors, _repairs = validate_canonical_ir(copy.deepcopy(ir))
        if errors or model is None:
            error = "canonical_ir_invalid:" + ",".join(str(e) for e in errors[:3])
            s["ir_compile_error"] = error
            s["_compiled_fallback_reason"] = error
            s["_compiled_quality_report"] = _failed_compiled_report(error)
            return s

        from services.solution_markdown_compiler import compile_canonical_ir_to_markdown
        from services.solution_quality import solution_quality_report

        canonical_dict = model.model_dump()
        compiled = compile_canonical_ir_to_markdown(canonical_dict)
        compiled_report = solution_quality_report({"standard_answer": compiled})

        s["_compiled_standard_answer"] = compiled
        s["_compiled_quality_report"] = compiled_report
        s["_compiled_from_ir"] = True
        s["_compiled_ir_version"] = COMPILED_IR_VERSION
        s["ir_compile_ok"] = bool(compiled_report.get("ok"))
        s["compiled_renderable"] = bool(compiled_report.get("renderable"))
        s["compiled_complete"] = bool(compiled_report.get("complete"))
        s["compiled_markdown_chars"] = len(compiled)
        legacy_text = str(s.get("standard_answer") or s.get("answer") or "")
        s["legacy_markdown_chars"] = len(legacy_text)
        s["ir_compile_error"] = "" if s["ir_compile_ok"] else "compiled_quality_gate_failed"

        fallback_reason = _compiled_output_fallback_reason(
            compiled=compiled,
            compiled_report=compiled_report,
            legacy_text=legacy_text,
        )
        s["_compiled_fallback_reason"] = fallback_reason
        if compiled_output_enabled and not fallback_reason:
            s["standard_answer"] = compiled
            s["standard_solution_source"] = "compiled_ir"
            s["_used_compiled_standard_answer"] = True
            s["_compiled_fallback_reason"] = ""
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:120]}"
        s["ir_compile_error"] = error
        s["_compiled_fallback_reason"] = error
        s["_compiled_quality_report"] = _failed_compiled_report(error)
        s["compiled_markdown_chars"] = 0
        s["legacy_markdown_chars"] = len(str(s.get("standard_answer") or s.get("answer") or ""))
    return s


def _annotate_solution_quality_issues(
    s: dict[str, Any],
    *,
    raw_text: str = "",
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record quality issues for optional regen; never clear content for display."""
    report = dict(report or {})
    s["_failed_quality_report"] = report
    s["_quality_report"] = report
    s["_should_regenerate"] = bool(report.get("should_regenerate"))
    if raw_text:
        s["_failed_raw_preview"] = html.escape(str(raw_text)[:500], quote=True)
    if not s.get("standard_solution_status"):
        if not report.get("renderable", False):
            s["standard_solution_status"] = "failed"
        elif not report.get("ok", False):
            s["standard_solution_status"] = "incomplete"
        else:
            s["standard_solution_status"] = "ready"
    return s


def _quarantine_solution_for_failed_render(
    s: dict[str, Any],
    *,
    raw_text: str = "",
    report: dict[str, Any] | None = None,
    status: str = "failed",
) -> dict[str, Any]:
    """P29: drop renderable fields when quality gate blocks display."""
    debug_text = raw_text or str(s.get("standard_answer") or s.get("answer") or "")
    if report is not None:
        _annotate_solution_quality_issues(s, raw_text=debug_text, report=report)
    issues = ", ".join(str(i) for i in ((report or s.get("_quality_report") or {}).get("issues") or [])[:6])
    s["standard_solution_status"] = status
    s["standard_solution_source"] = "failed"
    s["standard_solution_error"] = f"standard solution quality gate failed: {issues or 'not_renderable'}"
    s["standard_answer"] = ""
    s["steps"] = []
    s["_structured"] = None
    s["_debug_raw_standard_answer"] = html.escape(debug_text[:4000], quote=True)
    s["_failed_raw_preview"] = html.escape(debug_text[:500], quote=True)
    return s


def _requires_hard_render_quarantine(
    s: dict[str, Any],
    *,
    raw_text: str = "",
    report: dict[str, Any] | None = None,
) -> bool:
    """Hard quarantine only for unsafe HTML or compiled-IR hard failures."""
    report = dict(report or {})
    if report.get("renderable", False):
        return False
    text = str(raw_text or s.get("standard_answer") or s.get("answer") or "")
    if re.search(r"<\s*(?:span|script|style|iframe|object|embed|link|meta|svg|math|b|i|u|font)\b", text, re.I):
        return True
    fallback = str(s.get("_compiled_fallback_reason") or "")
    if fallback.startswith("canonical_ir_invalid"):
        return True
    return False


def _maybe_quarantine_solution_for_render(
    s: dict[str, Any],
    *,
    raw_text: str = "",
    report: dict[str, Any],
) -> dict[str, Any]:
    if not _requires_hard_render_quarantine(s, raw_text=raw_text, report=report):
        _annotate_solution_quality_issues(s, raw_text=raw_text, report=report)
        return s
    return _quarantine_solution_for_failed_render(s, raw_text=raw_text, report=report)


def normalize_grading_result(raw: dict[str, Any] | None, engine: str = "") -> dict[str, Any]:
    """Normalize grading result dict from any engine into a stable contract."""
    raw = dict(raw or {})

    total = raw.get("total", raw.get("score", 0))
    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0.0

    confidence = raw.get("confidence", 1.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 1.0

    normalized = {
        "success": bool(raw.get("success", True)),
        "total": total,
        "step_score": float(raw.get("step_score", 0) or 0),
        "result_score": float(raw.get("result_score", 0) or 0),
        "step_analysis": raw.get("step_analysis") or [],
        "deductions": raw.get("deductions") or [],
        "comment": raw.get("comment", ""),
        "method_matched": raw.get("method_matched", ""),
        "method_family": raw.get("method_family", ""),
        "tier": raw.get("tier", ""),
        "confidence": confidence,
        "engine": raw.get("engine") or raw.get("_engine") or engine or "unknown",
        "_obligation_warning": raw.get("_obligation_warning", ""),
        "_matched_from_pool": raw.get("_matched_from_pool", False),
        "_fast_path": raw.get("_fast_path", False),
        "_hide_until_solution_ready": raw.get("_hide_until_solution_ready", False),
        "standard_solution_status": raw.get("standard_solution_status"),
        "view_only": raw.get("view_only", False),
        "hide_score_card": raw.get("hide_score_card", False),
        "hide_diagnosis": raw.get("hide_diagnosis", False),
    }
    normalized.update({
        "is_correct": raw.get("is_correct", None),
        "total_score": raw.get("total_score", None),
        "correct_answer": raw.get("correct_answer", ""),
        "correct_option": raw.get("correct_option", ""),
        "student_answer": raw.get("student_answer", ""),
        "steps": raw.get("steps") or [],
        "needs_review": bool(raw.get("needs_review", False)),
        "error_type": raw.get("error_type", ""),
        "grading_method": raw.get("grading_method", raw.get("method", "")),
        "answer_source_field": raw.get("answer_source_field", ""),
        "answer_source_issues": raw.get("answer_source_issues", []),
        "quick_compare_confidence": raw.get("quick_compare_confidence"),
        "quick_compare_status": raw.get("quick_compare_status", ""),
        "ok": raw.get("ok", raw.get("is_correct", None)),
    })
    return normalized


def _coerce_question_type(question_type: str | None) -> str:
    q_type = str(question_type or "").strip()
    if "选择" in q_type:
        return "选择题"
    if "填空" in q_type:
        return "填空题"
    if "证明" in q_type:
        return "证明题"
    if "解答" in q_type or "计算" in q_type:
        return "解答题"
    return q_type or "未知题型"


_NLATEX_CMD_RE = re.compile(r"\\n[a-zA-Z]+")


def _unescape_json_newlines(text: str) -> str:
    """Turn literal ``\\n`` into newlines without breaking ``\\neq``, ``\\nabla``, etc."""
    s = str(text or "")
    slots: list[str] = []

    def _stash(match: re.Match) -> str:
        slots.append(match.group(0))
        return f"\x00NL{len(slots) - 1}\x00"

    s = _NLATEX_CMD_RE.sub(_stash, s)
    s = s.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    for idx, tok in enumerate(slots):
        s = s.replace(f"\x00NL{idx}\x00", tok, 1)
    return s


def _plain_text(value: Any) -> str:
    text = _unescape_json_newlines(str(value or ""))
    text = text.replace("$$", "")
    import re
    text = re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", r"\\(\1\\)", text, flags=re.S)
    return text.strip()


_STEP_TITLE_PREFIX_RE = re.compile(r"^步骤\s*\d+\s*[：:]\s*")
_GOAL_REASON_BODY_RE = re.compile(
    r"推导目标[：:]\s*(.+?)(?:[。．]\s*|\n+)\s*推导理由[：:]\s*(.+?)(?:[。．]\s*|\n+)(.*)",
    re.S,
)


def _strip_step_title_prefix(text: str) -> str:
    return _STEP_TITLE_PREFIX_RE.sub("", str(text or "").strip()).strip()


def _title_core(title: str) -> str:
    return _strip_step_title_prefix(str(title or "").strip())


def _goal_redundant_with_title(goal: str, title: str) -> bool:
    g = _norm_for_compare(_title_core(goal))
    t = _norm_for_compare(_title_core(title))
    if not g or not t:
        return False
    return g == t or g in t or t in g


_DERIVATION_MATH_TAIL_RE = re.compile(
    r"(?:关键变形为|中间公式为|因此本步得到结论|已知条件可写为)[：:].*",
    re.S,
)


def _strip_reason_display_tail(text: str) -> str:
    """Keep prose-only reason; display math belongs in blocks."""
    s = str(text or "").strip()
    if not s:
        return ""
    s = _DERIVATION_MATH_TAIL_RE.sub("", s).strip()
    if r"\begin{" in s:
        idx = s.find(r"\begin{")
        before = s[:idx].strip().rstrip("：:，,")
        s = before if before and _has_cjk(before) else ""
    return s.rstrip("：:，, \n")


def _extract_goal_reason_from_body(body: str) -> tuple[str, str, str]:
    """Split legacy body_markdown preamble into goal, reason, and remaining math body."""
    text = str(body or "").strip()
    if not text.startswith("推导目标"):
        return "", "", text
    match = _GOAL_REASON_BODY_RE.match(text)
    if not match:
        return "", "", text
    goal = match.group(1).strip().rstrip("。．")
    reason = match.group(2).strip().rstrip("。．")
    rest = match.group(3).strip()
    return goal, reason, rest


def _normalize_step_derivation_meta(step: dict[str, Any]) -> dict[str, Any]:
    """Populate goal/reason on a structured step and keep body_markdown math-only."""
    step = dict(step or {})
    goal = _strip_step_title_prefix(_plain_text(step.get("goal", "")))
    reason = _plain_text(step.get("reason") or step.get("justification") or "")
    body = str(
        step.get("body_markdown")
        or step.get("derivation_markdown")
        or ""
    ).strip()
    if body:
        parsed_goal, parsed_reason, rest = _extract_goal_reason_from_body(body)
        if parsed_goal and not goal:
            goal = _strip_step_title_prefix(parsed_goal)
        if parsed_reason and not reason:
            reason = parsed_reason
        if rest.strip():
            body = rest.strip()
    if reason and body:
        body = _strip_meta_echo_from_text(body, reason)
    if goal and body:
        body = _strip_meta_echo_from_text(body, goal)
    if body:
        body = _dedupe_paragraphs_in_text(body)
    label = str(step.get("label") or "").strip()
    if goal and _goal_redundant_with_title(goal, label):
        goal = ""
    if goal:
        step["goal"] = goal
    if reason:
        step["reason"] = reason
    if body:
        step["body_markdown"] = body
        step["derivation_markdown"] = body
    return step


def _strip_display_delimiters(value: Any) -> str:
    text = _unescape_json_newlines(str(value or "")).strip()
    if text.startswith("$$") and text.endswith("$$"):
        text = text[2:-2].strip()
    if text.startswith("\\[") and text.endswith("\\]"):
        text = text[2:-2].strip()
    return text.replace("$$", "").strip()


def _looks_like_latex_display(text: str) -> bool:
    s = str(text or "")
    return any(marker in s for marker in ("\\begin{", "\\frac", "\\int", "\\sum", "\\lim", "\\sqrt"))


def normalize_differential_tokens(latex: str) -> str:
    """Normalize common two-variable differential fragments deterministically."""
    s = str(latex or "")
    s = re.sub(r"\\,\s*dxdy\b", r"\\,dx\\,dy", s)
    s = re.sub(r"\bd\s*x\s*d\s*y\b", r"dx\\,dy", s)
    s = re.sub(r"\bdx\s+dy\b", r"dx\\,dy", s)
    s = re.sub(r"\bdxdy\b", r"dx\\,dy", s)
    return s


def normalize_cases_spacing(latex: str) -> str:
    """Remove AI-generated cases row-spacing fragments such as [2mm]."""
    s = str(latex or "")
    s = re.sub(r"\\\\\s*\[[^\]]*mm\]", r"\\\\", s)
    s = re.sub(r"\\\s*\[[^\]]*mm\]", "", s)
    s = re.sub(r",\s*\[[^\]]*mm\]\s*", r"\\\\\n", s)
    s = re.sub(r"\s*\[[^\]]*mm\]\s*", "", s)
    return s


def balance_inline_math_delimiters(text: str) -> str:
    """Balance \\( \\) without rewriting $...$ (grading render uses dollars)."""
    s = _unescape_json_newlines(str(text or ""))
    s = s.replace(r"\\(", r"\(").replace(r"\\)", r"\)")
    open_count = s.count(r"\(")
    close_count = s.count(r"\)")
    if open_count > close_count:
        s += r"\)" * (open_count - close_count)
    elif close_count > open_count:
        extra = close_count - open_count
        while extra > 0 and r"\)" in s:
            pos = s.rfind(r"\)")
            if pos < 0:
                break
            s = s[:pos] + s[pos + 2 :]
            extra -= 1
    return s


def normalize_math_delimiters_in_text(text: str) -> str:
    """Normalize inline/display delimiters that appear inside text blocks."""
    s = _unescape_json_newlines(str(text or ""))
    s = s.replace(r"\\(", r"\(").replace(r"\\)", r"\)")
    s = s.replace(r"\\[", r"\[").replace(r"\\]", r"\]")
    display_slots: list[str] = []

    def _stash_display(match: re.Match) -> str:
        display_slots.append(match.group(1))
        return f"\x00DD{len(display_slots) - 1}\x00"

    s = re.sub(r"\$\$(.*?)\$\$", _stash_display, s, flags=re.S)
    s = re.sub(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", r"\\(\1\\)", s, flags=re.S)
    for idx, block in enumerate(display_slots):
        s = s.replace(f"\x00DD{idx}\x00", f"$${block}$$")
    return balance_inline_math_delimiters(s)


_DERIVATION_CONCLUSION_RE = re.compile(r"因此本步得到结论[：:]")


def _is_incomplete_math_expr(text: str) -> bool:
    """True when a formula string is truncated (e.g. 'y =', '= -', trailing \\Rightarrow)."""
    s = str(text or "").strip()
    if not s:
        return True
    stripped = re.sub(r"\\+$", "", s).strip()
    # Short uppercase LHS prefixes (A=, I_1=) are merged with the next display block.
    if re.match(r"^[A-Z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*$", stripped):
        return False
    if re.match(r"^(?:=\s*[-+]?\s*|\d+\s*=\s*|\\Rightarrow\s*=\s*[-+]?\s*)$", stripped):
        return True
    if re.match(r"^[a-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*$", stripped):
        return True
    if re.match(r"^[A-Za-z]'{0,3}\([^)]*\)\s*=\s*$", stripped):
        return True
    if re.search(
        r"\\Rightarrow\s*(?:=\s*[-+]?\s*)?(?:\\\(\s*[A-Za-z]+\s*=\s*\\\)?)?\s*$",
        stripped,
    ):
        return True
    if stripped.endswith(r"\(") or stripped.endswith("("):
        return True
    if stripped.endswith("\\") and not re.search(r"\\[a-zA-Z]+\s*$", stripped):
        return True
    return False


def repair_incomplete_derivation_math(text: str) -> str:
    """Strip truncated \\Rightarrow tails and orphan '= -' / 'y =' lines."""
    s = _unescape_json_newlines(str(text or ""))
    if not s.strip():
        return ""
    s = re.sub(
        r"\\Rightarrow\s*\\\(\s*[A-Za-z]+\s*=\s*\\\)\s*",
        r"\\Rightarrow ",
        s,
    )
    s = re.sub(r"\\Rightarrow\s*\\\(\s*[A-Za-z]+\s*=\s*$", "", s, flags=re.M)
    s = re.sub(r"\\Rightarrow\s*=\s*[-+]?\s*", "", s)
    s = re.sub(r"(?<=[^\n])\s*\\Rightarrow\s*$", "", s, flags=re.M)
    if "\n" in s:
        kept: list[str] = []
        for line in s.splitlines():
            stripped = line.strip()
            if not stripped:
                kept.append(line)
                continue
            if _is_incomplete_math_expr(stripped):
                continue
            kept.append(line)
        s = "\n".join(kept)
    elif _is_incomplete_math_expr(s):
        return ""
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _dedupe_repeated_sentences(text: str) -> str:
    """Drop consecutive duplicate sentences (common in long AI derivation prose)."""
    s = str(text or "").strip()
    if not s:
        return ""
    parts = re.split(r"(?<=[。．!！?？;；])\s*", s)
    kept: list[str] = []
    last_norm = ""
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        norm = _norm_for_compare(chunk)
        if norm and norm == last_norm:
            continue
        kept.append(chunk)
        last_norm = norm
    return "".join(kept).strip() if kept else s


def _needs_display_latex_sanitize(latex: str) -> bool:
    s = str(latex or "")
    return any(
        marker in s
        for marker in (
            r"\(",
            r"\)",
            r"\backslash",
            r"\begin{aligned}",
            r"\begin{align}",
            r"\begin{cases}",
            r"\end{cases}",
            r"\left",
            r"\right",
            r"\text{",
            "关键变形",
            "中间公式",
            "因此本步",
        )
    ) or bool(re.search(r"(?<!\\)\\\[\d*\.?\d+(?:pt|mm|cm|em|ex|baselineskip)\]", s))


def sanitize_display_latex(latex: str) -> str:
    """Normalize display-math payloads before KaTeX (strip nested inline delimiters)."""
    s = str(latex or "").strip()
    if not s:
        return ""
    for _ in range(4):
        if r"\(" not in s and r"\)" not in s:
            break
        s = re.sub(r"\\\((.*?)\\\)", r"\1", s, flags=re.S)
    s = re.sub(
        r"(?<!\\)\\\[\d*\.?\d+(?:pt|mm|cm|em|ex|baselineskip)\]\s*",
        " ",
        s,
    )
    s = re.sub(r"(?<!\\)\\backslash\s+", r"\\\\ ", s)
    s = normalize_broken_formula_delimiters(normalize_differential_tokens(s))
    try:
        from latex_utils import repair_system_display_latex
        repaired = repair_system_display_latex(s).replace(r"\mid,", r"\mid ")
        return re.sub(r"(\\mid)\s{2,}", r"\1 ", repaired)
    except Exception:
        return s.strip()


def _finalize_display_latex(latex: str) -> str:
    s = str(latex or "").strip()
    if not s:
        return ""
    if _needs_display_latex_sanitize(s):
        s = sanitize_display_latex(s)
    else:
        s = normalize_broken_formula_delimiters(normalize_differential_tokens(s))
    s = _repair_cases_environments_in_text(s)
    s = _repair_orphan_alignment_environment_markers(s, allow_wrap=True)
    return s


def _cases_rows_are_derivation_chain(rows: list[str]) -> bool:
    """True when AI misuses cases for a multi-step equation chain."""
    if len(rows) < 2:
        return False
    for row in rows:
        s = str(row or "").strip()
        if not s or not re.search(r"(?<![<>!=])=", s):
            return False
        if _looks_like_cases_condition(s):
            return False
    return any(re.search(r"\\(?:int|ln|log|frac|sum|lim)", str(r or "")) for r in rows)


def _cases_rows_are_equation_stack(rows: list[str]) -> bool:
    """True when cases holds stacked equalities like ``f(0)=0 \\\\ f'(0)=0``."""
    if len(rows) < 2:
        return False
    for row in rows:
        s = str(row or "").strip()
        if not s or not re.search(r"(?<![<>!=])=", s):
            return False
        if _looks_like_cases_condition(s):
            return False
    return True


def _rows_to_aligned_latex(rows: list[str]) -> str:
    aligned_rows: list[str] = []
    for row in rows:
        r = str(row or "").strip().lstrip("&=").strip()
        if not r:
            continue
        if "&" in r:
            aligned_rows.append(r)
        elif "=" in r:
            lhs, _, rhs = r.partition("=")
            aligned_rows.append(f"{lhs.strip()} &= {rhs.strip()}")
        else:
            aligned_rows.append(r)
    if not aligned_rows:
        return ""
    return "\\begin{aligned}\n" + " \\\\\n".join(aligned_rows) + "\n\\end{aligned}"


def _repair_cases_environment_body(body: str) -> str:
    """Strip nested inline delimiters and fix truncated tails inside cases."""
    s = str(body or "")
    s = re.sub(r"\\\((.*?)\\\)", r"(\1)", s, flags=re.S)
    s = re.sub(r"\\\[(.*?)\\\]", r"\1", s, flags=re.S)
    s = re.sub(r"(\\ln\|[^|]+\|\s*[-+]\s*x\s*)\+\s*$", r"\1+ C", s, flags=re.M)
    s = re.sub(r"([+\-=])\s*$", lambda m: "+ C" if m.group(1) == "+" else m.group(0), s, flags=re.M)
    return s.strip()


def _repair_cases_environments_in_text(text: str) -> str:
    """Repair broken cases blocks; convert derivation chains to aligned."""
    s = str(text or "")
    if r"\begin{cases}" not in s:
        return s

    def repl(match: re.Match) -> str:
        body = _repair_cases_environment_body(match.group(1))
        rows = [part.strip() for part in re.split(r"\\\\", body) if part.strip()]
        if _cases_rows_are_derivation_chain(rows) or _cases_rows_are_equation_stack(rows):
            aligned = _rows_to_aligned_latex(rows)
            if aligned:
                return aligned
        return "\\begin{cases}\n" + body + "\n\\end{cases}"

    return re.sub(r"\\begin\{cases\}(.*?)\\end\{cases\}", repl, s, flags=re.S)


def _cases_env_to_rows(env: str) -> list[str]:
    match = re.search(r"\\begin\{cases\}(.*?)\\end\{cases\}", str(env or ""), flags=re.S)
    if not match:
        return []
    rows: list[str] = []
    for part in re.split(r"\\\\", _repair_cases_environment_body(match.group(1))):
        line = part.strip()
        if line.startswith("&="):
            line = line[2:].strip()
        line = line.lstrip("&").strip()
        if line:
            rows.append(line)
    return _merge_cases_enumeration_rows(rows)


def _looks_like_cases_condition(row: str) -> bool:
    s = str(row or "").strip()
    if not s or "\n" in s:
        return False
    if r"\text" in s:
        return True
    relation = r"(?:<=|>=|<|>|=|≤|≥|\\leq?|\\geq?)"
    if not re.search(relation, s):
        return False
    # Conditions are usually short domain clauses, not full derivation equations.
    if any(marker in s for marker in (r"\int", r"\sum", r"\lim", r"\frac", r"\begin")):
        return False
    if re.search(r"\\(?:ln|log|exp|sin|cos|tan)", s):
        return False
    if "|" in s or re.search(r"C_\d", s):
        return False
    if re.search(r"[A-Za-z]+'?(?:_\{[^{}]+\}|_\d+|\([^)]*\))\s*=", s):
        return False
    if re.search(r"\bf\s*\([^)]*\)\s*=", s):
        return False
    if len(s) > 48:
        return False
    return True


def _pair_alternating_cases_rows(rows: list[str]) -> list[dict[str, str]]:
    """Turn ``expr \\ condition`` or ``condition \\ expr`` alternation into cases rows."""
    cleaned = [str(row or "").strip() for row in rows if str(row or "").strip()]
    if not cleaned:
        return []

    def _append_expr_first() -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        idx = 0
        while idx < len(cleaned):
            expr = cleaned[idx]
            cond = ""
            if idx + 1 < len(cleaned) and _looks_like_cases_condition(cleaned[idx + 1]):
                cond = cleaned[idx + 1]
                idx += 2
            else:
                idx += 1
            if expr and not (_looks_like_cases_condition(expr) and not cond):
                out.append({"expr": expr, "condition": cond})
        return out

    if (
        len(cleaned) >= 2
        and _looks_like_cases_condition(cleaned[0])
        and not _looks_like_cases_condition(cleaned[1])
    ):
        out: list[dict[str, str]] = []
        idx = 0
        while idx < len(cleaned):
            if (
                idx + 1 < len(cleaned)
                and _looks_like_cases_condition(cleaned[idx])
                and not _looks_like_cases_condition(cleaned[idx + 1])
            ):
                out.append({"expr": cleaned[idx + 1], "condition": cleaned[idx]})
                idx += 2
            elif _looks_like_cases_condition(cleaned[idx]):
                idx += 1
            else:
                out.append({"expr": cleaned[idx], "condition": ""})
                idx += 1
        return out

    return _append_expr_first()


def _extract_lhs_before_cases(latex: str, env_start: int) -> str:
    prefix = str(latex or "")[:env_start].strip()
    if not prefix:
        return ""
    prefix = prefix.rstrip()
    if not prefix.endswith("="):
        return ""
    lhs = prefix[:-1].strip()
    lhs = re.split(r"\\\\|\n", lhs)[-1].strip()
    if not lhs or _has_cjk(lhs):
        return ""
    return normalize_cases_spacing(_strip_display_delimiters(_normalize_math_tokens(lhs)))


def _expand_cases_environment_expression_span(text: str, match: re.Match) -> tuple[int, int]:
    """Include the lhs of ``lhs = \begin{cases}`` when splitting mixed text."""
    start = match.start()
    while start > 0 and _is_math_expr_char(text[start - 1]):
        start -= 1
    return start, match.end()


def _merge_cases_enumeration_rows(rows: list[str]) -> list[str]:
    r"""Merge ``n=0 \\ 1 \\ 2 \\ \ldots`` tails back into the formula row."""
    merged: list[str] = []
    idx = 0
    while idx < len(rows):
        cur = str(rows[idx] or "").strip()
        if (
            merged
            and re.fullmatch(r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*[-+]?\d+", cur)
        ):
            enum = [cur]
            idx += 1
            while idx < len(rows):
                nxt = str(rows[idx] or "").strip()
                if re.fullmatch(r"[-+]?\d+|\\(?:ldots|cdots|dots)|\.\.\.", nxt):
                    enum.append(nxt)
                    idx += 1
                    continue
                break
            if len(enum) >= 2:
                merged[-1] = f"{merged[-1]}, {','.join(enum)}"
                continue
            merged.append(cur)
            continue
        merged.append(cur)
        idx += 1
    return merged


def _split_cases_environments_to_blocks(latex: str) -> list[dict[str, Any]]:
    s = _finalize_display_latex(latex)
    if not s or r"\begin{cases}" not in s:
        return []
    envs = re.findall(r"\\begin\{cases\}.*?\\end\{cases\}", s, flags=re.S)
    if not envs:
        return []
    blocks: list[dict[str, Any]] = []
    for env in envs:
        rows = _cases_env_to_rows(env)
        if rows:
            env_start = s.find(env)
            blocks.append({
                "type": "cases",
                "lhs": _extract_lhs_before_cases(s, env_start),
                "rows": _pair_alternating_cases_rows(rows),
            })
        else:
            blocks.append(_view_block_for_latex(env))
    return blocks


def _should_split_mixed_derivation_text(text: str) -> bool:
    s = str(text or "")
    if r"\begin{" in s:
        return True
    return _has_cjk(s) and bool(re.search(r"\\[a-zA-Z]|[_^{}=]", s))


def _normalize_mixed_derivation_text_blocks(text: str) -> list[dict[str, Any]]:
    if _has_cjk(text):
        return normalize_text_block_math(text)
    from latex_utils import split_text_and_latex_mixed_block

    blocks: list[dict[str, Any]] = []
    for block in split_text_and_latex_mixed_block(text):
        if block.get("type") == "latex_display":
            blocks.extend(_split_cases_environments_to_blocks(block.get("content", "")) or [
                _view_block_for_latex(_finalize_display_latex(block.get("content", "")))
            ])
        else:
            content = str(block.get("content") or "").strip()
            if content:
                blocks.append({
                    "type": "text",
                    "content": _wrap_inline_math_fragments(_normalize_math_tokens(content)),
                })
    return consolidate_view_blocks(blocks)


def _latex_display_rhs(norm_content: str) -> str:
    """Trailing state after the last implication arrow in a normalized formula."""
    s = str(norm_content or "").strip()
    for sep in ("\\Rightarrow", "Rightarrow", "⇒", "=>"):
        if sep in s:
            s = s.split(sep)[-1]
    return s.strip()


def _aligned_final_equation(content: str) -> str:
    """Rebuild ``subject = rhs`` from the last row of an aligned derivation chain."""
    s = str(content or "")
    if r"\begin{aligned}" not in s and r"\begin{align}" not in s:
        return ""
    m = re.search(r"\\begin\{(?:aligned|align\*?)\}(.*?)\\end\{(?:aligned|align\*?)\}", s, re.S)
    if not m:
        return ""
    rows = [row.strip() for row in re.split(r"(?<!\\)\\\\", m.group(1)) if row.strip()]
    if not rows:
        return ""
    head = rows[0]
    last = rows[-1]
    subj = ""
    rhs = ""
    hm = re.match(r"^(.+?)\s*&(?:=|\\Rightarrow|\\Longrightarrow|⇒)?\s*(.+)$", head)
    if hm:
        subj = hm.group(1).strip()
    elif "=" in head:
        subj, _ = head.split("=", 1)
        subj = subj.strip()
    if last.startswith("&"):
        rhs = re.sub(r"^&(?:=|\\Rightarrow|\\Longrightarrow|⇒)?\s*", "", last).strip()
    elif "=" in last:
        rhs = last.split("=", 1)[1].strip()
    else:
        rhs = last.strip()
    if not subj or not rhs:
        return ""
    return _norm_for_compare(f"{subj} = {rhs}")


_STEP_KINDS_KEEP_CONCLUSION = frozenset({"conclusion", "final_fill"})


def _cases_final_equation(content: str) -> str:
    """Normalized last row from a cases environment."""
    s = str(content or "")
    m = re.search(r"\\begin\{cases\}(.*?)\\end\{cases\}", s, re.S)
    if not m:
        return ""
    rows = [r.strip() for r in re.split(r"(?<!\\)\\\\", m.group(1)) if r.strip()]
    if not rows:
        return ""
    last = rows[-1].lstrip("&").strip()
    if last.startswith("&="):
        last = last[2:].strip()
    return _norm_for_compare(last)


def _dedupe_derivation_conclusion_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove '因此本步得到结论' + formula when it repeats the prior display block."""
    out: list[dict[str, Any]] = []
    last_display = ""
    idx = 0
    while idx < len(blocks):
        block = blocks[idx]
        if not isinstance(block, dict):
            idx += 1
            continue
        if (
            block.get("type") == "text"
            and idx + 1 < len(blocks)
            and blocks[idx + 1].get("type") == "latex_display"
        ):
            label = str(block.get("content") or "").strip()
            if (
                _DERIVATION_CONCLUSION_RE.match(label)
                or re.fullmatch(r"因此本步得到结论[：:]\s*", label)
            ):
                idx += 1
                continue
            if re.fullmatch(r"中间公式为[：:]\s*", label):
                nxt = _norm_for_compare(blocks[idx + 1].get("content"))
                rhs_prev = _latex_display_rhs(last_display)
                if (
                    nxt == last_display
                    or (rhs_prev and (nxt == rhs_prev or _similar_text(nxt, rhs_prev)))
                    or (last_display and nxt and nxt in last_display)
                ):
                    idx += 2
                    continue
        if (
            block.get("type") == "latex_display"
            and out
            and out[-1].get("type") == "latex_display"
        ):
            prev_raw = str(out[-1].get("content") or "")
            cur = _norm_for_compare(block.get("content"))
            prev = _norm_for_compare(prev_raw)
            aligned_tail = _aligned_final_equation(prev_raw)
            if aligned_tail and (cur == aligned_tail or _similar_text(cur, aligned_tail)):
                idx += 1
                continue
            if cur == prev or (prev and cur and cur in prev):
                idx += 1
                continue
        if (
            block.get("type") == "latex_display"
            and out
            and out[-1].get("type") == "cases"
        ):
            prev_rows = [
                str((r.get("expr") if isinstance(r, dict) else r) or "")
                for r in (out[-1].get("rows") or [])
            ]
            cur = _norm_for_compare(block.get("content"))
            if prev_rows:
                last_row = _norm_for_compare(prev_rows[-1])
                if cur == last_row or _similar_text(cur, last_row):
                    idx += 1
                    continue
            cases_tail = _cases_final_equation(
                "\\begin{cases}\n"
                + " \\\\\n".join(str(r.get("expr") if isinstance(r, dict) else r) for r in (out[-1].get("rows") or []))
                + "\n\\end{cases}"
            )
            if cases_tail and (cur == cases_tail or _similar_text(cur, cases_tail)):
                idx += 1
                continue
        if block.get("type") == "latex_display":
            last_display = _norm_for_compare(block.get("content"))
        out.append(block)
        idx += 1
    return out


def _trim_duplicate_glued_formula(text: str) -> str:
    """When AI glues the same LHS twice (AC-B^2=... AC-B^2=...), keep the latter."""
    s = str(text or "").strip()
    if not s:
        return ""
    lhs_eq = re.finditer(
        r"(?<![\\=])"
        r"([A-Za-z](?:[A-Za-z0-9]*(?:[-+][A-Za-z0-9]+)?)*"
        r"(?:\^\{[^{}]+\}|_\{[^{}]+\})*)\s*=",
        s,
    )
    seen: list[tuple[str, int]] = []
    for match in lhs_eq:
        lhs = match.group(1).strip()
        if len(lhs) < 2 and "^" not in lhs and "_" not in lhs and "-" not in lhs[1:]:
            continue
        if seen and seen[-1][0] == lhs:
            gap = s[seen[-1][1] : match.start()]
            if _has_cjk(gap) or "。" in gap or "，" in gap:
                seen.append((lhs, match.start()))
                continue
            return s[match.start() :].strip()
        seen.append((lhs, match.start()))
    return s


def _repair_glued_final_identity(text: str) -> str:
    """Split glued final relation like '故 f(x)=x^2 f(x)-x^2=0'."""
    s = str(text or "")
    if not s:
        return ""

    def repl(match: re.Match) -> str:
        prefix = match.group("prefix")
        lhs = match.group("lhs").strip()
        rhs = match.group("rhs").strip()
        return f"{prefix} \\({lhs}={rhs}\\)。由 \\({lhs}-{rhs}=0\\) 得 \\({lhs}={rhs}\\)"

    return re.sub(
        r"(?P<prefix>故|因此|所以)\s*"
        r"(?P<lhs>[A-Za-z]'{0,3}\([^)]*\))\s*=\s*"
        r"(?P<rhs>[A-Za-z0-9\\{}_^+\-*/().]+)\s+"
        r"(?P=lhs)\s*-\s*(?P=rhs)\s*=\s*0",
        repl,
        s,
    )


_CJK_LEADING_PUNCT_RE = re.compile(r"^[，。、；：,.;)\]】》」]\s*")


_CONDITION_RELATION_RE = r"(?:<=|>=|<|>|=|≤|≥|\\leq?|\\geq?)"


def _repair_glued_condition_after_equation(text: str) -> str:
    """Split ``formula=value x>1 时`` before inline-math wrapping."""
    s = str(text or "")
    if not s:
        return ""
    s = s.replace(r"\gt", ">").replace(r"\lt", "<")

    condition = (
        r"[A-Za-z](?:\([^)]*\))?\s*"
        + _CONDITION_RELATION_RE
        + r"\s*[-+]?(?:\d+(?:\.\d+)?|[A-Za-z](?:\^\{[^{}]+\})?)"
    )

    def repl(match: re.Match) -> str:
        eq = match.group("eq").strip()
        cond = match.group("cond").strip()
        cue = match.group("cue") or "当"
        return f"{eq}。{cue}{cond} "

    return re.sub(
        r"(?P<eq>[A-Za-z]'{0,3}\([^)]*\)\s*=\s*[^，。；;\n\s]+)\s+"
        r"(?P<cue>当|若|在)?\s*"
        r"(?P<cond>" + condition + r")\s*(?=时|時)",
        repl,
        s,
    )


def _is_math_only_line(line: str) -> bool:
    s = str(line or "").strip()
    if not s or _has_cjk(s):
        return False
    return bool(re.search(r"[\\$=^_{}]|\\\(|\\\)", s))


def _merge_cjk_prose_lines(text: str) -> str:
    """Keep Chinese narrative in continuous lines; avoid orphan punctuation/math lines."""
    s = _unescape_json_newlines(str(text or ""))
    if not s or "\n" not in s:
        return s
    merged: list[str] = []
    for line in s.split("\n"):
        stripped = line.strip()
        if not stripped:
            if merged and merged[-1] != "":
                merged.append("")
            continue
        attach = False
        if merged and _CJK_LEADING_PUNCT_RE.match(stripped):
            attach = True
        if merged and _has_cjk(merged[-1]) and _is_math_only_line(stripped):
            attach = True
        if attach:
            merged[-1] = (merged[-1].rstrip() + stripped).strip()
        else:
            merged.append(stripped)
    return "\n".join(merged)


def _prepare_prose_math_text(text: str) -> str:
    """Wrap inline math in prose; caller must run repair_derivation_text_block first."""
    raw = str(text or "").strip()
    raw = _demote_bare_cjk_text_commands(raw)
    dollar_spans: list[str] = []

    def protect_dollar_span(match: re.Match) -> str:
        dollar_spans.append(match.group(0))
        return f"@@DOLLARMATH{len(dollar_spans) - 1}@@"

    if _has_cjk(raw) and "$" in raw:
        raw = re.sub(r"\$\$.*?\$\$|\$[^$\n]+\$", protect_dollar_span, raw, flags=re.S)
    normalized = normalize_inline_math_tokens(
        balance_inline_math_delimiters(
            _normalize_math_tokens(raw)
        )
    )
    for idx, value in enumerate(dollar_spans):
        normalized = normalized.replace(f"@@DOLLARMATH{idx}@@", value)
    if _has_cjk(normalized):
        normalized = re.sub(r"\\\((.*?)\\\)", r"$\1$", normalized, flags=re.S)
        normalized = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", normalized, flags=re.S)
        normalized = _repair_malformed_dollar_spans(normalized)
        normalized = _merge_adjacent_integral_differential_dollar_spans(normalized)
        normalized = _merge_plain_lhs_with_dollar_math(normalized)
        normalized = _split_glued_equations_in_dollar_spans(normalized)
        return normalized
    return prepare_grading_math_for_render(normalized)


_LATEX_ENV_NAMES = (
    "aligned", "align", "align*", "cases",
    "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix",
)
_LATEX_ENV_BLOCK_RE = re.compile(
    r"(\\begin\{(?P<env>" + "|".join(re.escape(name) for name in _LATEX_ENV_NAMES) + r")\}"
    r".*?\\end\{(?P=env)\})",
    re.S | re.I,
)


_MATRIX_ENV_NAMES = {"matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix"}


def _is_math_expr_char(ch: str) -> bool:
    if not ch:
        return False
    if "\u4e00" <= ch <= "\u9fff":
        return False
    return bool(re.match(r"[A-Za-z0-9\\{}()\[\],.;:_^+\-*/=<>|'\s]", ch))


def _expand_latex_environment_expression_span(text: str, match: re.Match) -> tuple[int, int]:
    env = str(match.group("env") or "")
    if env == "cases":
        return _expand_cases_environment_expression_span(text, match)
    if env not in _MATRIX_ENV_NAMES:
        return match.start(), match.end()

    start = match.start()
    while start > 0 and _is_math_expr_char(text[start - 1]):
        start -= 1
    end = match.end()
    probe = end
    while probe < len(text) and text[probe].isspace():
        probe += 1
    if probe < len(text) and text[probe] in "=<>+-":
        end = probe + 1
        while end < len(text) and _is_math_expr_char(text[end]):
            end += 1
    return start, end


def _split_text_with_latex_environments(text: str) -> list[dict[str, Any]]:
    """Extract display env blocks; keep surrounding Chinese as continuous text."""
    s = str(text or "").strip()
    if not s:
        return []
    blocks: list[dict[str, Any]] = []
    pos = 0
    for match in _LATEX_ENV_BLOCK_RE.finditer(s):
        expr_start, expr_end = _expand_latex_environment_expression_span(s, match)
        if expr_start < pos:
            expr_start = match.start()
        prefix = s[pos : expr_start].strip()
        if prefix:
            blocks.append({"type": "text", "content": _prepare_prose_math_text(prefix)})
        env = _finalize_display_latex(s[expr_start:expr_end].strip())
        split_cases = _split_cases_environments_to_blocks(env)
        if split_cases:
            blocks.extend(split_cases)
        else:
            blocks.append(_view_block_for_latex(env))
        pos = expr_end
    suffix = s[pos:].strip()
    if suffix:
        blocks.append({"type": "text", "content": _prepare_prose_math_text(suffix)})
    if not blocks:
        blocks.append({"type": "text", "content": _prepare_prose_math_text(s)})
    return blocks


def _attach_lhs_to_display_latex(lhs: str, latex: str) -> str:
    from latex_utils import repair_system_display_latex

    lhs_clean = (
        str(lhs or "")
        .replace(r"\(", "")
        .replace(r"\)", "")
        .strip()
        .rstrip("=")
        .strip()
    )
    s = repair_system_display_latex(str(latex or "").strip())
    if not lhs_clean:
        return s
    m = re.search(r"\\begin\{aligned\}(.*?)\\end\{aligned\}", s, flags=re.S)
    if m:
        body = m.group(1).strip()
        segments = [seg.strip() for seg in re.split(r"(?<!\\)\\\\", body) if seg.strip()]
        if not segments:
            return s
        first = segments[0]
        if "&=" in first:
            before_amp, after_amp = first.split("&=", 1)
            if not before_amp.strip():
                segments[0] = f"{lhs_clean} &={after_amp}"
            else:
                segments[0] = first
        elif first.startswith("&"):
            segments[0] = f"{lhs_clean} {first}"
        else:
            rhs = first.lstrip("=").strip()
            segments[0] = f"{lhs_clean} &= {rhs}" if rhs else f"{lhs_clean} &="
        new_body = " \\\\\n".join(segments)
        return f"\\begin{{aligned}}\n{new_body}\n\\end{{aligned}}"
    if r"\begin{cases}" in s:
        return s
    rhs = s.lstrip("=").strip()
    if should_render_formula_inline(f"{lhs_clean} = {rhs}"):
        return f"${lhs_clean} = {rhs}$"
    return f"\\begin{{aligned}}\n{lhs_clean} &= {rhs}\n\\end{{aligned}}"


def repair_derivation_text_block(text: str) -> str:
    """Repair common AI derivation step text before math normalization."""
    s = _unescape_json_newlines(str(text or "")).strip()
    if not s:
        return ""
    s = _drop_llm_fragment_markers(s)
    try:
        from services.solution_legacy_repair import _repair_corrupted_greek_commands

        s = _repair_corrupted_greek_commands(s)
    except Exception:
        pass
    s = _repair_glued_final_identity(s)
    s = _repair_glued_condition_after_equation(s)
    s = _trim_duplicate_glued_formula(s)
    s = _dedupe_repeated_sentences(s)
    s = _demote_stray_tex_commas_in_cjk_prose(s)
    s = re.sub(r"(因此本步得到结论[：:])\s*\\+\s*$", r"\1", s)
    s = re.sub(r"([：:])\s*\\+\s*$", r"\1", s)

    def _wrap_paren_formula(match: re.Match) -> str:
        inner = match.group(1).strip()
        if _has_cjk(inner):
            return match.group(0)
        if re.search(r"\\(?:frac|dfrac|tfrac|sqrt|int|sum|lim)|[=^_{}]", inner):
            return rf"\({inner}\)"
        return match.group(0)

    def _wrap_stat_function_formula(match: re.Match) -> str:
        func, inner = match.group(1).strip(), match.group(2).strip()
        if _has_cjk(inner):
            return match.group(0)
        if re.search(r"\\[A-Za-z]+|[=^_{}]", inner):
            return rf"\({func}({inner})\)"
        return match.group(0)

    s = re.sub(
        r"\b(E|D|P|Var|Cov)\s*\(([^()]*\\[^()]+[^()]*)\)",
        _wrap_stat_function_formula,
        s,
    )
    s = re.sub(r"(?<![\\A-Za-z])\(([^()]*\\[^()]+[^()]*)\)", _wrap_paren_formula, s)
    s = _repair_bare_paren_math_eq(s)
    s = re.sub(r"(?m)(\\Rightarrow[^\n]*?)\\+\s*$", r"\1", s)
    s = re.sub(r"(?m)^\s*\\Rightarrow\s*\\\(\s*[A-Za-z]+\s*=\s*\\\)\s*$", "", s)
    if _DERIVATION_CONCLUSION_RE.search(s):
        s = _DERIVATION_CONCLUSION_RE.sub(lambda m: m.group(0) + "\n", s, count=1)
    s = repair_incomplete_derivation_math(s)
    s = _strip_trailing_incomplete_math_tail(s)
    s = _repair_cases_environments_in_text(s)
    return _merge_cjk_prose_lines(s)


def _repair_bare_paren_math_eq(text: str) -> str:
    """Wrap bare (y = 0) style fragments that lost \\( \\) delimiters."""

    def repl(match: re.Match) -> str:
        lhs, rhs = match.group(1).strip(), match.group(2).strip()
        chunk = match.group(0)
        if _has_cjk(chunk) or "\\" in lhs:
            return chunk
        if re.search(r"\\frac|\\Rightarrow|'", rhs + lhs):
            return rf"\({lhs} = {rhs}\)"
        return chunk

    return re.sub(r"(?<!\\)\(\s*([^()=]{1,40})\s*=\s*([^()]{1,120})\)", repl, text)


def _dedupe_paragraphs_in_text(text: str) -> str:
    """Remove duplicate paragraphs while preserving order."""
    parts = re.split(r"\n\s*\n", str(text or "").strip())
    seen: list[str] = []
    kept: list[str] = []
    for part in parts:
        norm = _norm_for_compare(part)
        if not norm:
            continue
        if norm in seen:
            continue
        seen.append(norm)
        kept.append(part.strip())
    return "\n\n".join(kept)


def _strip_meta_echo_from_text(text: str, meta: str) -> str:
    """Remove paragraphs that repeat section goal/reason meta."""
    meta_plain = _plain_text(meta)
    if not meta_plain:
        return str(text or "")
    t = str(text or "").strip()
    if not t:
        return ""
    t_norm = _norm_for_compare(t)
    meta_norm = _norm_for_compare(meta_plain)
    if t_norm and meta_norm and t_norm == meta_norm:
        return ""
    if t.startswith(meta_plain):
        t = t[len(meta_plain):].lstrip("。．\n ，,;；")
    else:
        meta_cjk = _cjk_for_overlap(meta_plain)
        text_cjk = _cjk_for_overlap(t)
        if meta_cjk and text_cjk.startswith(meta_cjk) and len(text_cjk) > len(meta_cjk):
            sentence_end = min(
                [pos for pos in (t.find("。"), t.find("．")) if pos >= 0],
                default=-1,
            )
            if sentence_end >= 0:
                t = t[sentence_end + 1 :].lstrip("。．\n ，,;；")
    parts = re.split(r"\n\s*\n", t)
    meta_norm = _norm_for_compare(meta_plain)
    kept = []
    for part in parts:
        pn = _norm_for_compare(part)
        if pn and pn == meta_norm:
            continue
        if pn and meta_norm and len(pn) >= 12 and pn in meta_norm:
            continue
        kept.append(part.strip())
    return _dedupe_paragraphs_in_text("\n\n".join(kept))


def repair_ai_grading_math_artifacts(text: str) -> str:
    """Repair AI-grading-only math artifacts before block normalization."""
    s = str(text or "")
    if not s:
        return ""
    s = _unescape_json_newlines(s)
    s = _normalize_unicode_math_symbols_for_grading(s)
    s = _drop_llm_fragment_markers(s)
    s = re.sub(r"\\lim_\s*不存在", "极限不存在", s)
    s = re.sub(r"\\lim_\s*(?=[\u4e00-\u9fff，。；、,\s]|$)", "", s)
    s = _repair_constant_absorption_artifacts(s)
    s = _drop_malformed_integral_shorthand_lines(s)
    s = re.sub(r"@@MATH\d+@@", "", s)
    s = re.sub(r"(?m)^\s*\\\s*$", "", s)
    s = re.sub(r"(?m)(?<!\\)\\\s*$", "", s)
    s = s.replace(r"\\(", r"\(").replace(r"\\)", r"\)")
    s = s.replace(r"\\[", r"\[").replace(r"\\]", r"\]")
    s = re.sub(
        r"\\\\(?=(?:frac|dfrac|tfrac|int|iint|sum|lim|exp|ln|log|sin|cos|ne|neq|nabla|notin|Rightarrow|Leftarrow|rightarrow|leftarrow|begin|end|left|right)\b)",
        r"\\",
        s,
    )
    s = re.sub(r"(?:\\\(\s*){2,}", r"\(", s)
    s = re.sub(r"(?:\s*\\\)){2,}", r"\)", s)
    s = re.sub(
        r"\\(exp|ln|log|sin|cos|tan)\s*\\\(",
        r"\\\1(",
        s,
    )
    s = re.sub(
        r"(\\(?:exp|ln|log|sin|cos|tan)\([^，。；\n]*?)\\\)",
        r"\1)",
        s,
    )
    s = re.sub(
        r"\\ln\s*1\s*\+\s*(\\(?:d?frac|tfrac)\{[^{}]+\}\{[^{}]+\})",
        r"\\ln(1+\1)",
        s,
    )
    s = re.sub(r"\(\s*(\\(?:int|iint|sum|lim))\s*\)", r"\1", s)
    s = re.sub(r"(\\(?:int|iint|sum|lim))\s*\)", r"\1", s)
    s = re.sub(
        r"\(\s*(\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\}(?:\{[^{}]+\})?)\)\)",
        r"(\1)",
        s,
    )
    s = re.sub(
        r"\\\((\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\}(?:\{[^{}]+\})?)\)\s*\\\)",
        r"\\(\1\\)",
        s,
    )
    s = re.sub(
        r"\$\s*(\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\}(?:\{[^{}]+\})?)\)\s*\$",
        r"$\\1$",
        s,
    )
    s = re.sub(r"\\\((\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\}\{[^{}]+\})\)", r"\1", s)
    s = re.sub(r"\\\((\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\})\)", r"\1", s)
    s = re.sub(r"=\s*=\s*\\Rightarrow", r"=\\Rightarrow", s)
    s = re.sub(r"\\{\s*\\Rightarrow\s*\\}", r"\\Rightarrow", s)
    s = re.sub(r"\\Rightarrow", r" \\Rightarrow ", s)
    if not _has_cjk(s):
        s = re.sub(r"(?<!\\),?\s+\b(d[xytuv])\b", r"\\,\1", s)
    s = re.sub(r"\\\\\s*(d[xytuv])\b", r"\\,\1", s)
    s = re.sub(
        r"\\\\(?=(?:frac|dfrac|tfrac|int|iint|sum|lim|exp|ln|log|sin|cos|ne|neq|nabla|notin|Rightarrow|Leftarrow|rightarrow|leftarrow|begin|end|left|right)\b)",
        r"\\",
        s,
    )
    s = re.sub(
        r"\\(theta|lambda|alpha|beta|gamma|delta|mu|pi|rho|sigma|phi|omega)(?=[A-Za-z])",
        r"\\\1 ",
        s,
    )
    s = re.sub(r"\\(leq?|geq?|neq?|perp)(?=[A-Z(\\])", r"\\\1 ", s)
    s = re.sub(
        r"\\(d?frac)(\d)(\d)",
        lambda m: rf"\{m.group(1)}{{{m.group(2)}}}{{{m.group(3)}}}",
        s,
    )
    s = re.sub(
        r"(\\d?frac\{[^{}]+\}\{[^{}]+\})\$(?=\s*[\(\[])",
        r"\1",
        s,
    )
    s = re.sub(
        r"(\\(?:i?i?int|sum|lim)(?:_\{?[^{}\s$]+\}?|\^\{?[^{}\s$]+\}?)*?)\s*\$\s*(d(?:[A-Za-z]|\\[A-Za-z]+))",
        r"\1 \2",
        s,
    )
    s = re.sub(
        r"(?:，|,)?\s*故\s+[A-Za-z]\s*=\s*\\pi\s*\\cdot\s*[。．]?\s*$",
        "",
        s,
    )
    s = re.sub(r"\\int\s*,\s*d(?:[A-Za-z])?\b", "", s)
    if r"\end{cases}" in s and r"\begin{cases}" not in s:
        s = s.replace(r"\end{cases}", "")
    s = _repair_cases_environments_in_text(s)
    s = _repair_orphan_alignment_environment_markers(s, allow_wrap=False)
    s = re.sub(
        r"\\left\s*(?=\\(?![{}]|langle\b|lfloor\b|lceil\b|vert\b|Vert\b))",
        "",
        s,
    )
    s = re.sub(
        r"\\right\s*(?=\\(?![{}]|rangle\b|rfloor\b|rceil\b|vert\b|Vert\b))",
        "",
        s,
    )
    if r"\right" in s and r"\left" not in s:
        s = re.sub(
            r"\\right(?:[)\]\}|.]|\\(?:rangle|rfloor|rceil|vert|Vert))",
            "",
            s,
        )
    s = re.sub(r"\s{2,}", " ", s)
    s = repair_incomplete_derivation_math(s)
    return _repair_orphan_alignment_environment_markers(s, allow_wrap=False)


def _normalize_math_tokens(text: str) -> str:
    s = normalize_math_delimiters_in_text(
        repair_ai_grading_math_artifacts(repair_derivation_text_block(text))
    )
    s = s.replace(r"\infy", r"\infty").replace(r"\lnfty", r"\infty")
    s = re.sub(
        r"(?<!\\)\b(sin|cos|tan|sec|csc|cot)\b(?=\s*(?:[A-Za-z0-9(\\{]|$))",
        r"\\\1",
        s,
    )
    s = re.sub(
        r"\\(sin|cos|tan|sec|csc|cot)\s+(?=[A-Za-z0-9])",
        r"\\\1{} ",
        s,
    )
    s = re.sub(r"\\lim_([A-Za-z])\s*\\to\s*", r"\\lim_{\1\\to", s)
    s = re.sub(r"\\lim_\s*不存在", "极限不存在", s)
    s = re.sub(r"\\lim_\s*(?=[\u4e00-\u9fff，。；、,\s]|$)", "极限", s)
    s = re.sub(r"([A-Za-z])_\\\{([^{}]+)\\\}", r"\1_{\2}", s)
    s = re.sub(r"([A-Za-z])_\[([^\[\]]+)\]", r"\1_{\2}", s)
    return normalize_cases_spacing(normalize_differential_tokens(s))


# Unified layout rules for AI grading (inline in Chinese text vs dedicated display row).
_MAX_INLINE_FORMULA_CHARS = 44
_FORMULA_DISPLAY_MARKERS = (
    r"\begin",
    r"\\",
    r"\iint",
    r"\iiint",
    r"\oint",
    r"\cases",
    "matrix",
    r"\sqrt[",
)


def formula_requires_display_layout(latex: str) -> bool:
    """True when a formula should render as latex_display (not \\( ... \\) in text)."""
    s = _strip_display_delimiters(_normalize_math_tokens(latex))
    if not s:
        return False
    if _has_cjk(s):
        return False
    if "$$" in s or r"\[" in s or r"\]" in s:
        return True
    if "\n" in s or len(s) > _MAX_INLINE_FORMULA_CHARS:
        return True
    if any(marker in s for marker in _FORMULA_DISPLAY_MARKERS):
        return True
    if s.count("=") >= 3:
        return True
    return False


def should_render_formula_inline(latex: str) -> bool:
    return not formula_requires_display_layout(latex)


def _block_is_explicit_display(block: dict[str, Any]) -> bool:
    """LLM/schema explicit block layout (type=latex + display=block, or latex_display)."""
    btype = str(block.get("type") or "text")
    if btype == "latex_display":
        return True
    if btype != "latex":
        return False
    return str(block.get("display") or "inline").lower() == "block"


def _block_is_explicit_inline(block: dict[str, Any]) -> bool:
    """Structured block marked inline — must not promote to latex_display."""
    btype = str(block.get("type") or "text")
    if btype in {"latex_inline", "inline_math"}:
        return True
    if btype == "latex":
        return str(block.get("display") or "inline").lower() != "block"
    return False


def _block_is_inline_latex(block: dict[str, Any]) -> bool:
    """True when a block carries inline (not display-row) math."""
    if not isinstance(block, dict):
        return False
    if _block_is_explicit_inline(block):
        return True
    btype = str(block.get("type") or "text")
    if btype == "latex_display":
        content = str(block.get("content") or "").strip()
        return bool(content) and not formula_requires_display_layout(content)
    return False


def _inline_latex_block_to_span(block: dict[str, Any]) -> str | None:
    content = str(block.get("content") or "").strip()
    if not content:
        return None
    # Keep \\left/\\right for inline prose; do not run display-only delimiter repair.
    latex = normalize_differential_tokens(
        _strip_display_delimiters(_normalize_math_tokens(content))
    ).strip()
    if not latex:
        return None
    if _block_is_explicit_inline(block):
        return f"${latex}$"
    if str(block.get("type") or "") == "latex_display" and formula_requires_display_layout(latex):
        return None
    if formula_requires_display_layout(latex):
        return None
    return f"${latex}$"


def _view_block_for_latex(latex: str, *, force_display: bool = False, force_inline: bool = False) -> dict[str, Any]:
    if force_inline or (not force_display and not formula_requires_display_layout(latex)):
        return {"type": "text", "content": f"${latex}$"}
    return {"type": "latex_display", "content": latex}


def _merge_plain_lhs_with_dollar_math(text: str) -> str:
    """Merge ``y = $\\frac{1}{x}$`` into a single ``$y = \\frac{1}{x}$`` span."""

    def repl(match: re.Match) -> str:
        lhs, inner = match.group(1).strip(), match.group(2).strip()
        if _has_cjk(lhs) or not inner:
            return match.group(0)
        joiner = " " if inner.startswith("\\") and not lhs.endswith(" ") else ""
        return f"${lhs}{joiner}{inner}$"

    return re.sub(
        r"(?<![\$\\])([A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*)\$([^$]+)\$",
        repl,
        text,
    )


def _split_glued_equations_in_dollar_spans(text: str) -> str:
    """Split ``$xy' + y = 0 \\frac{dy}{y}$`` into separate inline math spans."""

    def repl(match: re.Match) -> str:
        inner = match.group(1)
        parts = re.split(
            r"(?<=[0-9\)\'])\s*(?=\\(?:frac|dfrac|tfrac)\{)",
            inner,
        )
        if len(parts) <= 1:
            parts = re.split(
                r"(?<=[}\d^x\)])\s+(?=[A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?'?\s*=)",
                inner,
            )
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) <= 1:
            return match.group(0)
        return " ".join(f"${part}$" for part in parts)

    return re.sub(r"\$([^$\n]+)\$", repl, text)


def _repair_malformed_dollar_spans(text: str) -> str:
    """Drop empty ``$y = $`` spans and fix glued constants like ``1C=1``."""
    s = str(text or "")
    s = re.sub(r"(?<!\$)\$([^$\n]+)\$\$(?!\$)", r"$\1$", s)

    def fix_inner(match: re.Match) -> str:
        inner = match.group(1)
        inner = inner.replace(r"\(", "").replace(r"\)", "")
        if _is_incomplete_math_expr(inner.strip()):
            return ""
        inner = re.sub(r"=\s*,\s*", "= ", inner)
        inner = re.sub(r"(\d)([A-Z])\s*=", r"\1, \2 = ", inner)
        inner = re.sub(r"([)\d])\s*([A-Z])\s*=", r"\1, \2 = ", inner)
        inner = inner.strip(" ，,;；")
        if _is_incomplete_math_expr(inner):
            return ""
        return f"${inner}$"

    s = re.sub(r"(?<!\$)\$([^$\n]+)\$(?!\$)", fix_inner, s)
    if s.count("$") % 2:
        s = re.sub(r"\$\s*$", "", s, count=1)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def _merge_adjacent_integral_differential_dollar_spans(text: str) -> str:
    r"""Merge ``$\int...$ $d\theta=...$`` created while protecting existing math."""
    s = str(text or "")
    if r"\int" not in s and r"\iint" not in s and r"\oint" not in s:
        return s
    return re.sub(
        r"\$(\\(?:i?i?int|oint)[^$\n]*?)\$\s*\$(d(?:[A-Za-z]|\\[A-Za-z]+)[^$\n]*)\$",
        lambda m: f"${m.group(1).strip()} {m.group(2).strip()}$",
        s,
    )


def _strip_trailing_incomplete_math_tail(text: str) -> str:
    """Remove trailing orphan ``y =`` after an otherwise complete formula tail."""
    s = str(text or "").strip()
    if not s or _has_cjk(s) and not re.search(r"[=\\$]", s):
        return s
    tail = re.search(
        r"(.+?)\s+([a-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*)$",
        s,
    )
    if not tail:
        return s
    head, orphan = tail.group(1), tail.group(2)
    if _is_incomplete_math_expr(orphan.strip()) and (
        re.search(
            r"\\frac|\\ln|\\int|[A-Za-z]\([^)]*\)\s*=\s*[^=]+",
            head,
        )
        or re.search(r"(?:[A-Z]|C)\s*=\s*[-+]?\d+", head)
    ):
        return head.strip()
    return s


def prepare_grading_math_for_render(text: str) -> str:
    """Convert normalized grading math to $ delimiters Streamlit/KaTeX parse."""
    s = repair_incomplete_derivation_math(str(text or ""))
    if not s.strip():
        return ""
    s = _repair_malformed_dollar_spans(s)
    s = _strip_trailing_incomplete_math_tail(s)
    s = _merge_plain_lhs_with_dollar_math(s)
    s = _split_glued_equations_in_dollar_spans(s)
    # Undo erroneous \{y = 0\} literals from older wrap_event behavior.
    s = re.sub(
        r"\\\(\s*\\\{([^{}]+)\\\}\s*\\\)",
        lambda m: rf"\({m.group(1).strip()}\)",
        s,
    )
    s = re.sub(r"\\\{([^{}\\]*=[^{}\\]*)\\\}", r"\1", s)
    s = re.sub(r"=\s*=\s*\\Rightarrow", r"=\\Rightarrow", s)
    s = re.sub(r"\\{\s*\\Rightarrow\s*\\}", r"\\Rightarrow", s)
    s = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", s, flags=re.S)
    s = re.sub(r"\\\((.*?)\\\)", r"$\1$", s, flags=re.S)
    try:
        from latex_utils import _pre_wrap_bare_latex, repair_math_delimiters_for_render

        s = _pre_wrap_bare_latex(s)
        s = repair_math_delimiters_for_render(s)
    except Exception:
        pass
    s = re.sub(r"\$\s*\$", "", s)
    s = _merge_plain_lhs_with_dollar_math(s)
    s = _split_glued_equations_in_dollar_spans(s)
    s = re.sub(r"=\s*(\\(?:frac|dfrac|tfrac)\{)", r"= \1", s)
    return s


def _looks_like_math_fragment(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return False
    if any(marker in s for marker in (r"\frac", r"\sum", r"\lim", r"\iint", r"\int", r"\sqrt", r"\max", r"\min")):
        return True
    if re.search(r"[A-Za-z]_\{[^{}]+\}|[A-Za-z]\s*=", s):
        return True
    if re.search(r"\\?[A-Za-z]+\([^)]*\)\s*[<>=]", s):
        return True
    return False


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def _coerce_formula_like_text_to_latex(text: str) -> str:
    """Convert formula-only malformed text into a latex_display payload."""
    original = str(text or "")
    raw = repair_ai_grading_math_artifacts(text)
    if not raw.strip() or _has_cjk(raw):
        return ""
    needs_display_repair = (
        "@@MATH" in original
        or "$" in original
        or original.count(r"\(") != original.count(r"\)")
        or bool(re.match(r"^\s*d(?:[VSxyzuvt]|[A-Z])\s*=", raw))
        or any(marker in raw for marker in (
            r"\int", r"\iint", r"\sum", r"\lim", r"\ln", r"\Rightarrow", r"\Leftarrow",
        ))
        or (raw.count("=") >= 2 and any(marker in raw for marker in (r"\frac", r"\Rightarrow", r"\ln")))
    )
    if not needs_display_repair:
        return ""
    if not any(marker in raw for marker in (
        "\\frac", "\\dfrac", "\\int", "\\iint", "\\sum", "\\lim",
        "\\Rightarrow", "\\Leftarrow", "^", "_", "=",
    )):
        return ""
    latex = raw.strip()
    latex = re.sub(r"^\$+(.*?)\$+$", r"\1", latex, flags=re.S)
    latex = latex.replace("$$", "")
    if latex.count(r"\(") != latex.count(r"\)"):
        latex = latex.replace(r"\(", "").replace(r"\)", "")
    latex = re.sub(r"\\\((.*?)\\\)", r"\1", latex, flags=re.S)
    latex = re.sub(r"\\\[(.*?)\\\]", r"\1", latex, flags=re.S)
    latex = latex.replace("$", "")
    latex = repair_missing_latex_backslashes_in_formula(latex)
    latex = normalize_integral_differentials(latex)
    latex = normalize_broken_formula_delimiters(latex)
    latex = normalize_differential_tokens(latex)
    latex = re.sub(r"\\\\\s*(d[xytuv])\b", r"\\,\1", latex)
    latex = latex.strip(" ，,。；;")
    while latex.endswith(")") and latex.count("(") < latex.count(")"):
        latex = latex[:-1].rstrip()
    latex = re.sub(
        r"\(\s*(\\(?:frac|dfrac|tfrac|sqrt)\{[^{}]+\}(?:\{[^{}]+\})?)\s*\)",
        r"\1",
        latex,
    )
    latex = re.sub(r"\\\((.*?)\\\)", r"\1", latex, flags=re.S)
    if not latex or latex.count("{") != latex.count("}"):
        return ""
    latex = repair_incomplete_derivation_math(latex)
    latex = _repair_orphan_alignment_environment_markers(latex, allow_wrap=True)
    if _is_incomplete_math_expr(latex):
        return ""
    return latex


_CJK_FORMULA_ASSIGNMENT_RE = re.compile(
    r"(?<![$\\(])\b(?:[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+|\([^)]*\))?|D\([^)]*\)|1-p)"
    r"\s*=\s*(?:(?![;；。\u4e00-\u9fff\n]).)+"
)
_CJK_FUNCTION_RELATION_RE = re.compile(
    r"(?<![$\\(])\b[A-Za-z]'{0,3}\([^()\u4e00-\u9fff]*\)"
    r"(?:\s*[-+]\s*[A-Za-z]'{0,3}\([^()\u4e00-\u9fff]*\))*"
    r"\s*(?:=|\\le|\\ge|<|>|≤|≥)\s*[^，。；、;\n\u4e00-\u9fff]+"
)
_MATH_RELATION_REPAIRS = (
    re.compile(
        r"(?<![$\\(])(?:\\int|∫)\s*[^，。；、;\n\u4e00-\u9fff]*?"
        r"d[A-Za-z]\s*=\s*[^，。；、;\n\u4e00-\u9fff]+"
    ),
    re.compile(
        r"(?<![$\\(])(?:\\?ln\s*\|[^|，。；、;\n\u4e00-\u9fff]+\|)"
        r"\s*=\s*[^，。；、;\n\u4e00-\u9fff]+"
    ),
)


def _normalize_unicode_math_symbols_for_grading(text: str) -> str:
    s = str(text or "")
    return (
        s.replace("∫", r"\int ")
        .replace("±", r"\pm ")
        .replace("≤", r"\le ")
        .replace("≥", r"\ge ")
    )


def _demote_stray_tex_commas_in_cjk_prose(text: str) -> str:
    """Replace literal ``\\,`` outside math delimiters in Chinese prose."""
    s = str(text or "")
    if not _has_cjk(s) or r"\," not in s:
        return s
    parts = re.split(r"(\$\$.*?\$\$|\$[^$\n]+\$)", s, flags=re.S)
    rebuilt: list[str] = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            rebuilt.append(part)
        else:
            rebuilt.append(part.replace(r"\,", ", "))
    return "".join(rebuilt)


def _repair_constant_absorption_artifacts(text: str) -> str:
    s = str(text or "")
    s = re.sub(
        r"(y\s*=\s*C\s*x\s*e\^\{-x\})\s*C\s*=\s*(?:\\pm|±)\s*e\^\{?C_?1\}?",
        r"\1",
        s,
    )
    s = re.sub(r"(C\s*x\s*e\^\{-x\})\s*C\b", r"\1", s)
    s = re.sub(
        r"(去掉绝对值符号时引入常数[^，。；\n]{0,120}?[）\)]?[，,、\s]*则\s*)"
        r"去掉绝对值符号时引入常数\s*",
        r"\1",
        s,
    )
    return s


def _drop_malformed_integral_shorthand_lines(text: str) -> str:
    lines: list[str] = []
    for line in str(text or "").splitlines():
        compact = line.strip()
        if ",d" in compact and "=" not in compact and re.search(r"\([^()\n]+\)\s*,d", compact):
            continue
        lines.append(line)
    return "\n".join(lines)


def _drop_llm_fragment_markers(text: str) -> str:
    """Remove leaked LLM fragment markers such as ``�L2�`` or bare ``L0``."""
    s = str(text or "")
    if not s:
        return ""
    return re.sub(r"(?:\ufffd|\?)*L\d+(?:\ufffd|\?)*", "", s)


def _repair_orphan_alignment_environment_markers(text: str, *, allow_wrap: bool = False) -> str:
    """Repair orphan aligned/align markers before KaTeX sees them."""
    s = _drop_llm_fragment_markers(str(text or ""))
    if not s:
        return ""
    s = s.replace(r"\&=", "&=").replace(r"\&", "&")
    envs = ("aligned", "align", "align*")
    for env in envs:
        begin = rf"\begin{{{env}}}"
        end = rf"\end{{{env}}}"
        if end in s and begin not in s:
            s = s.replace(end, "")
        if begin in s and end not in s:
            s = s.rstrip() + "\n" + end
    if allow_wrap and not _has_cjk(s) and r"\begin{" not in s:
        has_alignment = "&" in s or re.search(r"(?<!\\)\\\\", s) is not None
        has_formula = bool(re.search(r"\\(?:frac|int|sum|lim|ln|sin|cos)|[=<>^_]", s))
        if has_alignment and has_formula:
            rows = [part.strip() for part in re.split(r"(?<!\\)\\\\|\n+", s) if part.strip()]
            if len(rows) >= 2 or "&" in s:
                body = " \\\\\n".join(rows)
                s = "\\begin{aligned}\n" + body + "\n\\end{aligned}"
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _wrap_math_relations_in_prose(text: str) -> str:
    s = str(text or "")
    if not s:
        return s

    def repl(match: re.Match) -> str:
        raw = match.group(0)
        if "$" in raw or raw.startswith(r"\("):
            return raw
        core, suffix = _strip_formula_assignment_trailing_punctuation(raw)
        normalized = repair_missing_latex_backslashes_in_formula(
            _strip_display_delimiters(repair_ai_grading_math_artifacts(core))
        )
        normalized = normalize_integral_differentials(normalize_differential_tokens(normalized)).strip()
        if not normalized or _has_cjk(normalized):
            return raw
        if _is_incomplete_math_expr(normalized):
            return raw
        return rf"\({normalized}\){suffix}"

    for pattern in _MATH_RELATION_REPAIRS:
        s = pattern.sub(repl, s)
    return s


def _wrap_function_relations_in_cjk_prose(text: str) -> str:
    s = str(text or "")
    if not s or not _has_cjk(s):
        return s

    def repl(match: re.Match) -> str:
        raw = match.group(0)
        if "$" in raw or raw.startswith(r"\("):
            return raw
        core, suffix = _strip_formula_assignment_trailing_punctuation(raw)
        normalized = normalize_differential_tokens(
            _strip_display_delimiters(repair_ai_grading_math_artifacts(core))
        ).strip()
        if not normalized or _has_cjk(normalized):
            return raw
        if _is_incomplete_math_expr(normalized):
            return raw
        return rf"\({normalized}\){suffix}"

    return _CJK_FUNCTION_RELATION_RE.sub(repl, s)


def _strip_formula_assignment_trailing_punctuation(formula: str) -> tuple[str, str]:
    core = str(formula or "").rstrip()
    suffix = ""
    while core.endswith((".", ",", ";", ":")):
        suffix = core[-1] + suffix
        core = core[:-1].rstrip()
    return core, suffix


_CJK_TEXT_COMMAND_RE = re.compile(r"\\text\s*\{([^{}]*[\u4e00-\u9fff][^{}]*)\}")
_INLINE_OR_DISPLAY_MATH_RE = re.compile(
    r"\\\(.*?\\\)|\\\[.*?\\\]|\$\$.*?\$\$|\$[^$\n]+\$",
    re.S,
)


def _demote_bare_cjk_text_commands(text: str) -> str:
    """Turn bare ``\text{中文}`` prose into plain Chinese outside math spans."""
    s = str(text or "")
    if r"\text" not in s:
        return s

    protected: list[str] = []

    def protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"@@TEXTMATH{len(protected) - 1}@@"

    work = _INLINE_OR_DISPLAY_MATH_RE.sub(protect, s)
    work = _CJK_TEXT_COMMAND_RE.sub(lambda m: m.group(1).strip(), work)
    for idx, value in enumerate(protected):
        work = work.replace(f"@@TEXTMATH{idx}@@", value)
    return work


def _wrap_formula_assignments_in_cjk_prose(text: str) -> str:
    """Wrap full assignment formulas in Chinese prose before generic regexes split them."""
    s = str(text or "")
    if not s or not _has_cjk(s):
        return s

    def repl(match: re.Match) -> str:
        raw = match.group(0)
        if "$" in raw or raw.startswith(r"\("):
            return raw
        core, suffix = _strip_formula_assignment_trailing_punctuation(raw)
        normalized = normalize_differential_tokens(
            _strip_display_delimiters(repair_ai_grading_math_artifacts(core))
        ).strip()
        if not normalized or _has_cjk(normalized):
            return raw
        if _is_incomplete_math_expr(normalized):
            return raw
        return rf"\({normalized}\){suffix}"

    return _CJK_FORMULA_ASSIGNMENT_RE.sub(repl, s)


def _wrap_probability_set_relations_in_cjk_prose(text: str) -> str:
    r"""Wrap probability/set relations such as ``P(A)\le P(\overline C)``."""
    s = str(text or "")
    if not s or not _has_cjk(s):
        return s
    s = re.sub(r"\\(leq?|geq?|neq?|perp)(?=[A-Z(\\])", r"\\\1 ", s)

    relation_patterns = (
        r"(?<![\\A-Za-z])(?:[A-Za-z]{2,}|[A-Za-z]\([^()\u4e00-\u9fff]*\))\s*=\s*\\emptyset",
        r"(?<![\\A-Za-z])(?:[A-Za-z](?:\^\{?[-+]?\d+\}?)?|[A-Za-z][A-Za-z0-9]*(?:\([^()\u4e00-\u9fff]*\))?)"
        r"\s*\\(?:subseteq|subset|leq?|geq?|perp)\s*"
        r"(?:[A-Za-z]+(?:\([^()\u4e00-\u9fff]*\))?|\\overline\s*\{?[^，。；;\n\u4e00-\u9fff]+|[^，。；;\n\u4e00-\u9fff]+)",
    )

    def repl(match: re.Match) -> str:
        raw = match.group(0)
        if "$" in raw or raw.startswith(r"\("):
            return raw
        core, suffix = _strip_formula_assignment_trailing_punctuation(raw)
        normalized = normalize_differential_tokens(
            _strip_display_delimiters(repair_ai_grading_math_artifacts(core))
        ).strip()
        if not normalized or _has_cjk(normalized) or _is_incomplete_math_expr(normalized):
            return raw
        return rf"\({normalized}\){suffix}"

    for relation in relation_patterns:
        s = re.sub(relation, repl, s)
    return s


def _read_balanced_brace_group(text: str, open_pos: int) -> tuple[str, int] | None:
    """Return ``{...}`` span starting at *open_pos*, or None if unbalanced."""
    if open_pos >= len(text) or text[open_pos] != "{":
        return None
    depth = 0
    idx = open_pos
    while idx < len(text):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_pos : idx + 1], idx + 1
        idx += 1
    return None


def _wrap_compound_lim_frac_expressions(text: str, wrap) -> str:
    """Wrap ``\\lim_{...}\\frac{...}{...}=...`` before fragment regexes split subscripts."""
    s = str(text or "")
    if not s or r"\lim_" not in s:
        return s
    out: list[str] = []
    pos = 0
    for match in re.finditer(r"\\lim_", s):
        out.append(s[pos : match.start()])
        cursor = match.end()
        sub = _read_balanced_brace_group(s, cursor)
        if not sub:
            out.append(match.group(0))
            pos = match.end()
            continue
        _, cursor = sub
        frac_match = re.match(r"\\d?frac", s[cursor:])
        if frac_match:
            cursor += frac_match.end()
            num = _read_balanced_brace_group(s, cursor)
            den = _read_balanced_brace_group(s, num[1]) if num else None
            if num and den:
                cursor = den[1]
        tail = re.match(r"\s*=[^，。；、\n\u4e00-\u9fff]*", s[cursor:])
        if tail:
            cursor += tail.end()
        expr = s[match.start() : cursor]
        out.append(wrap(expr) if expr.strip() else s[match.start() : cursor])
        pos = cursor
    out.append(s[pos:])
    return "".join(out)


def _wrap_balanced_frac_expressions(text: str, wrap) -> str:
    """Wrap ``\\frac{...}{...}`` spans that may contain nested ``\\sqrt{...}``."""
    s = str(text or "")
    if not s or r"\frac" not in s and r"\dfrac" not in s and r"\tfrac" not in s:
        return s
    out: list[str] = []
    pos = 0
    for match in re.finditer(r"\\d?frac", s):
        out.append(s[pos : match.start()])
        cursor = match.end()
        num = _read_balanced_brace_group(s, cursor)
        den = _read_balanced_brace_group(s, num[1]) if num else None
        if not num or not den:
            out.append(match.group(0))
            pos = match.end()
            continue
        if num.count("{") <= 1 and den.count("{") <= 1 and r"\sqrt" not in num and r"\sqrt" not in den:
            out.append(s[pos : den[1]])
            pos = den[1]
            continue
        cursor = den[1]
        tail = re.match(r"\s*=\s*[^\\，。；、\n\u4e00-\u9fff]+", s[cursor:])
        if tail:
            cursor += tail.end()
        expr = s[match.start() : cursor]
        out.append(wrap(expr) if expr.strip() else s[match.start() : cursor])
        pos = cursor
    out.append(s[pos:])
    return "".join(out)


def normalize_inline_math_tokens(text: str) -> str:
    s = str(text or "")
    protected: list[str] = []

    def protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"@@MATH{len(protected) - 1}@@"

    def protect_inline(value: str) -> str:
        value = re.sub(r"\\\(.*?\\\)", protect, value, flags=re.S)
        return re.sub(r"\$\$.*?\$\$|\$[^$\n]+\$|\\\[.*?\\\]", protect, value, flags=re.S)

    if _has_cjk(s):
        s = _demote_bare_cjk_text_commands(s)
        s = _wrap_math_relations_in_prose(s)
        s = _wrap_function_relations_in_cjk_prose(s)
        s = _wrap_probability_set_relations_in_cjk_prose(s)
        s = _wrap_formula_assignments_in_cjk_prose(s)
    else:
        s = _wrap_math_relations_in_prose(s)
    s = protect_inline(s)

    def wrap(value: str) -> str:
        inner = _normalize_math_tokens(value.strip())
        if not inner or inner.startswith(r"\(") or inner.startswith("$$") or inner.startswith("@@MATH"):
            return value
        return rf"\({inner}\)"

    def wrap_event(match: re.Match) -> str:
        inner = match.group(1).strip()
        # LaTeX-escaped \{...\} from source — keep brace literals inside math.
        if match.group(0).startswith(r"\{") and not match.group(0).startswith("{"):
            if not inner.startswith(r"\{"):
                inner = r"\{" + inner
            if match.group(0).endswith(r"\}") and not inner.endswith(r"\}"):
                inner += r"\}"
        # Bare AI braces like {y = 0} — wrap as inline math, not \{...\} literals.
        return wrap(inner)

    s = re.sub(r"\\\{([^{}\u4e00-\u9fff]*(?:\\[A-Za-z]+|[A-Za-z]_\{|[<>=])[^{}\u4e00-\u9fff]*)\\\}", wrap_event, s)
    s = protect_inline(s)
    s = re.sub(
        r"(?<!_)\{([^{}\u4e00-\u9fff]*(?:\\[A-Za-z]+|[A-Za-z]_\{|[<>=])[^{}\u4e00-\u9fff]*)\}",
        wrap_event,
        s,
    )
    s = protect_inline(s)
    s = _wrap_compound_lim_frac_expressions(s, wrap)
    s = protect_inline(s)
    if r"\sqrt" in s:
        s = _wrap_balanced_frac_expressions(s, wrap)
        s = protect_inline(s)
    patterns = [
        r"\b[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+|\([^)]*\))?\s*\\sim\s*(?:\\mathrm\{[^{}]+\}\([^)]*\)|[^，。；、\s]+)",
        r"\b(?:E|D|P|Var|Cov)\s*\([^()\u4e00-\u9fff]*(?:\\[A-Za-z]+|[_^=])[^()\u4e00-\u9fff]*\)",
        r"\b[A-Za-z]'{0,3}\([^()\u4e00-\u9fff]*\)(?:\s*[-+]\s*[A-Za-z]'{0,3}\([^()\u4e00-\u9fff]*\))*\s*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"\b[A-Za-z]'{0,3}\([^()\u4e00-\u9fff]*\)\s*(?:\\le|\\ge|<|>|≤|≥)\s*[^，。；、\n\u4e00-\u9fff]+",
        r"\\(?:sin|cos|tan|sec|csc|cot)(?:\{\})?\s*(?:\([^()\u4e00-\u9fff]*\)|[A-Za-z0-9]+)(?:\s*(?:[-+]|\\le|\\ge|<|>|=)\s*[^，。；、\n\u4e00-\u9fff]+)?",
        r"(?<!\\)\b(?:sin|cos|tan|sec|csc|cot)\s*(?:\([^()\u4e00-\u9fff]*\)|[A-Za-z0-9]+)(?:\s*(?:[-+]|\\le|\\ge|<|>|=)\s*[^，。；、\n\u4e00-\u9fff]+)?",
        r"(?<!\\\()\\(?:i?i?int|sum|lim)(?:_\{?[^{}\s，。；、\u4e00-\u9fff]+\}?|\^\{?[^{}\s，。；、\u4e00-\u9fff]+\}?)*\s*d(?:[A-Za-z]|\\[A-Za-z]+)\s*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"(?<!\\\()\\d?frac\{[^{}]+\}\{[^{}]+\}(?:[^，。；、\n\u4e00-\u9fff]*)",
        r"\b(?:[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+|\([^)]*\))?|D\([^)]*\)|1-p)\s*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"\bd[A-Za-z](?:\\,)?\s*d[A-Za-z]\s*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?'?\s*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"\b[A-Za-z][A-Za-z0-9_{}^+\-*/\\\s]*=\s*[^，。；、\n\u4e00-\u9fff]+",
        r"(?:[0-9A-Za-z]|\\(?:theta|lambda|alpha|beta|gamma|delta|mu|pi|rho|sigma|phi|omega))(?:\s*(?:\\le|\\ge|<|>)\s*(?:[0-9A-Za-z]|\\(?:theta|lambda|alpha|beta|gamma|delta|mu|pi|rho|sigma|phi|omega)))+",
        r"(?:\\(?:theta|lambda|alpha|beta|gamma|delta|mu|pi|rho|sigma|phi|omega)|[A-Za-z])\s*\\(?:in|notin)\s*[^，。；、\n\u4e00-\u9fff]+",
        r"\b[A-Za-z](?:\^\{?[-+]?[A-Za-z0-9]+\}?|_\{[^{}]+\}|_[A-Za-z0-9]+)+",
        r"\b[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)(?:\([^)]*\))?",
        r"(?<!\\\()\\(?:sum|lim|iint|int|sqrt|max|min|ln|sin|cos|tan|sec|csc|cot|exp|overline|underline|mathrm|infty)(?:\{[^{}]*\}|\([^)]*\)|_[^\s，。；、\u4e00-\u9fff]+|[^\s，。；、\u4e00-\u9fff]*)*",
    ]
    for pattern in patterns:
        s = re.sub(pattern, lambda m: wrap(m.group(0)), s)
        s = protect_inline(s)
    s = re.sub(r"(?<!\\\()\\(?:pi|sim|le|ge|in|to|infty)(?![A-Za-z])", lambda m: wrap(m.group(0)), s)
    s = protect_inline(s)
    for idx, value in enumerate(protected):
        s = s.replace(f"@@MATH{idx}@@", value)
    return s


def _wrap_inline_math_fragments(text: str) -> str:
    return normalize_inline_math_tokens(text)


def _contains_display_math(text: str) -> bool:
    s = str(text or "")
    return bool(re.search(r"\$\$.*?\$\$|\\\[.*?\\\]", s, flags=re.S))


def _split_derivation_conclusion_blocks(text: str) -> list[dict[str, Any]] | None:
    """Split '因此本步得到结论' label from surrounding math when mixed in one string."""
    s = str(text or "").strip()
    match = _DERIVATION_CONCLUSION_RE.search(s)
    if not match:
        return None
    blocks: list[dict[str, Any]] = []
    before = s[: match.start()].strip()
    after = s[match.end() :].strip()
    if before:
        before_norm = _normalize_math_tokens(before)
        coerced_before = _coerce_formula_like_text_to_latex(before_norm)
        if coerced_before and not _has_cjk(coerced_before):
            blocks.append(_view_block_for_latex(coerced_before))
        else:
            blocks.extend(normalize_text_block_math(before))
    if after:
        if not after.strip("\\ \n\t"):
            blocks.append({"type": "text", "content": match.group(0)})
        else:
            after_norm = _normalize_math_tokens(after)
            coerced = _coerce_formula_like_text_to_latex(after_norm)
            if coerced and not _has_cjk(coerced):
                blocks.append(_view_block_for_latex(coerced))
            else:
                blocks.append({"type": "text", "content": _wrap_inline_math_fragments(after_norm)})
    else:
        blocks.append({"type": "text", "content": match.group(0)})
    if not blocks:
        blocks.append({"type": "text", "content": match.group(0)})
    return blocks


_CJK_MATH_PREFIX_RE = re.compile(
    r"^([\u4e00-\u9fff][\u4e00-\u9fff\s，。：、；：「」《》]*)\s*(.+)$",
    flags=re.S,
)


def _split_cjk_latex_mixed_content(text: str) -> list[dict[str, Any]] | None:
    """Split ``极小值 -\\frac{1}{e}`` into text + inline math (never one latex_display)."""
    s = str(text or "").strip()
    if not s or not _has_cjk(s):
        return None
    if not re.search(r"\\[a-zA-Z{]|\\frac|[_^]|\\\(|\$", s):
        return [{"type": "text", "content": s}]
    match = _CJK_MATH_PREFIX_RE.match(s)
    if not match:
        return None
    zh, tail = match.group(1).strip(), match.group(2).strip()
    if not zh or not tail or _has_cjk(tail):
        return None
    tail_norm = normalize_differential_tokens(_strip_display_delimiters(tail))
    if not tail_norm:
        return [{"type": "text", "content": zh}]
    if should_render_formula_inline(tail_norm):
        math_part = _wrap_inline_math_fragments(tail_norm)
    elif formula_requires_display_layout(tail_norm):
        return [
            {"type": "text", "content": zh},
            {"type": "latex_display", "content": _finalize_display_latex(tail_norm)},
        ]
    else:
        math_part = _wrap_inline_math_fragments(tail_norm)
    return [{"type": "text", "content": f"{zh} {math_part}".strip()}]


def _latex_display_blocks_without_cjk(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Never keep Chinese prose inside latex_display blocks."""
    out: list[dict[str, Any]] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "latex_display" and _has_cjk(str(block.get("content") or "")):
            content = str(block.get("content") or "")
            split = _split_cjk_latex_mixed_content(content)
            if split:
                out.extend(split)
                continue
            split = _split_derivation_conclusion_blocks(content)
            if split:
                out.extend(split)
                continue
            out.extend(normalize_text_block_math(content))
            continue
        out.append(block)
    return out


def normalize_text_block_math(text: str, *, _depth: int = 0) -> list[dict[str, Any]]:
    """Split and normalize a text block into natural text plus pure formula blocks."""
    repaired = repair_derivation_text_block(text)
    split_blocks = _split_derivation_conclusion_blocks(repaired)
    if split_blocks is not None:
        return consolidate_view_blocks(split_blocks)
    if re.search(r"\\begin\{(?:aligned|align\*?|cases)\}", repaired, re.I):
        return consolidate_view_blocks(_split_text_with_latex_environments(repaired))
    if _has_cjk(repaired) and contains_raw_tex_outside_math(repaired):
        if re.search(r"\\begin\{", repaired):
            return consolidate_view_blocks(_split_text_with_latex_environments(repaired))
        content = _prepare_prose_math_text(repaired)
        if contains_raw_tex_outside_math(content):
            if _depth >= 1:
                if content.strip():
                    return consolidate_view_blocks([{"type": "text", "content": content}])
                return []
            return consolidate_view_blocks(
                compile_text_block_to_math_blocks(repaired, _depth=_depth + 1)
            )
        if content.strip():
            return consolidate_view_blocks([{"type": "text", "content": content}])
        return []
    if _has_cjk(repaired) or not contains_raw_tex_outside_math(repaired):
        content = _prepare_prose_math_text(repaired)
        if content.strip():
            return consolidate_view_blocks([{"type": "text", "content": content}])
        return []
    if _should_split_mixed_derivation_text(repaired):
        return _normalize_mixed_derivation_text_blocks(repaired)
    raw = _normalize_math_tokens(repaired)
    blocks: list[dict[str, Any]] = []
    pos = 0
    for match in re.finditer(r"\$\$(.*?)\$\$|\\\[(.*?)\\\]", raw, flags=re.S):
        prefix = raw[pos:match.start()].strip()
        if prefix:
            if _is_orphan_lhs(prefix):
                blocks.append({"type": "text", "content": prefix})
            else:
                blocks.append({"type": "text", "content": _wrap_inline_math_fragments(prefix)})
        latex = match.group(1) if match.group(1) is not None else match.group(2)
        latex = normalize_differential_tokens(_strip_display_delimiters(latex))
        if latex:
            if should_render_formula_inline(latex):
                blocks.append({"type": "text", "content": f"${latex}$"})
            else:
                blocks.append({"type": "latex_display", "content": latex})
        pos = match.end()
    suffix = raw[pos:].strip()
    if suffix:
        if _is_orphan_lhs(suffix):
            blocks.append({"type": "text", "content": suffix})
        elif _contains_display_math(suffix):
            blocks.extend(normalize_text_block_math(suffix, _depth=_depth))
        else:
            coerced_suffix = _coerce_formula_like_text_to_latex(suffix)
            if coerced_suffix and not _has_cjk(coerced_suffix):
                blocks.append(_view_block_for_latex(coerced_suffix))
            elif r"\begin{" in suffix and not any("\u4e00" <= ch <= "\u9fff" for ch in suffix):
                blocks.append({"type": "latex_display", "content": _strip_display_delimiters(suffix)})
            else:
                blocks.append({"type": "text", "content": _wrap_inline_math_fragments(suffix)})
    blocks = [b for b in blocks if str(b.get("content") or b.get("items") or b.get("rows") or "").strip()]
    return consolidate_view_blocks(blocks)


_ORPHAN_LHS_RE = re.compile(
    r"^\s*(?:"
    r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?\s*=\s*"
    r"|I_\d+\s*=\s*"
    r"|f\([^)]*\)\s*=\s*"
    r"|a_n\s*=\s*"
    r"|=\s*[-+]?\s*"
    r"|\d+\s*=\s*"
    r")\s*$"
)

_ORPHAN_SYMBOL_RE = re.compile(
    r"^\s*(?:"
    r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?"
    r"|f_[xyzw]"
    r")\s*$"
)


def _is_orphan_lhs(text: str) -> bool:
    s = str(text or "").replace(r"\(", "").replace(r"\)", "").strip()
    return bool(_ORPHAN_LHS_RE.match(s) or _ORPHAN_SYMBOL_RE.match(s))


def _should_merge_text_fragments(prev: str, nxt: str) -> bool:
    """Merge only fragment pairs (orphan punct/math tails), not full derivation steps."""
    p, n = str(prev or "").strip(), str(nxt or "").strip()
    if not p or not n:
        return False
    if _CJK_LEADING_PUNCT_RE.match(n):
        return True
    if _has_cjk(p) and _is_math_only_line(n):
        return True
    if _is_orphan_lhs(p) or _is_orphan_lhs(n):
        return True
    if _has_cjk(p) and _has_cjk(n):
        han_in_n = len(re.findall(r"[\u4e00-\u9fff]", n))
        if len(p) <= 4 or len(n) <= 3:
            return True
        if p.rstrip().endswith("$") and len(n) <= 6 and han_in_n <= 2:
            return True
        return False
    return len(p) < 24 or len(n) < 24


def consolidate_view_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge fragment text blocks; attach orphan LHS labels to display math."""
    merged = merge_inline_structured_blocks(list(blocks or []))
    merged = merge_orphan_lhs_with_formula_blocks(_latex_display_blocks_without_cjk(merged))
    merged = merge_inline_structured_blocks(merged)
    out: list[dict[str, Any]] = []
    text_buf: list[str] = []

    def _flush_text() -> None:
        if not text_buf:
            return
        joined = "\n\n".join(p for p in text_buf if str(p).strip())
        if joined.strip():
            out.append({"type": "text", "content": joined})
        text_buf.clear()

    for block in merged:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            content = str(block.get("content") or "")
            if text_buf and not _should_merge_text_fragments(text_buf[-1], content):
                _flush_text()
            text_buf.append(content)
        else:
            _flush_text()
            out.append(block)
    _flush_text()
    return _dedupe_derivation_conclusion_blocks(out)


def merge_orphan_lhs_with_formula_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    idx = 0
    while idx < len(blocks):
        block = blocks[idx]
        if (
            isinstance(block, dict)
            and block.get("type") == "text"
            and _is_orphan_lhs(str(block.get("content") or ""))
            and idx + 1 < len(blocks)
            and isinstance(blocks[idx + 1], dict)
            and blocks[idx + 1].get("type") in {"latex_display", "equation_group", "derivation_chain"}
        ):
            lhs = str(block.get("content") or "").replace(r"\(", "").replace(r"\)", "").strip()
            nxt = dict(blocks[idx + 1])
            if nxt.get("type") == "latex_display":
                content = normalize_differential_tokens(str(nxt.get("content") or "").strip())
                nxt["content"] = _attach_lhs_to_display_latex(lhs, content)
                merged.append(nxt)
            else:
                items = [str(item).strip() for item in (nxt.get("items") or [])]
                if items and not items[0].startswith(lhs):
                    items[0] = lhs + items[0]
                nxt["items"] = items
                merged.append(nxt)
            idx += 2
            continue
        merged.append(block)
        idx += 1
    pruned: list[dict[str, Any]] = []
    skip = 0
    while skip < len(merged):
        block = merged[skip]
        if (
            skip + 1 < len(merged)
            and isinstance(block, dict)
            and block.get("type") == "text"
            and _is_orphan_lhs(str(block.get("content") or ""))
            and merged[skip + 1].get("type") in {"latex_display", "equation_group", "derivation_chain"}
        ):
            skip += 1
            continue
        pruned.append(block)
        skip += 1
    return pruned


def _solution_text(solution: dict[str, Any] | None) -> str:
    if not isinstance(solution, dict):
        return ""
    return str(solution.get("standard_answer") or solution.get("answer") or "").strip()


def _choice_letter(text: str) -> str:
    import re
    m = re.search(r"[A-D]", str(text or "").upper())
    return m.group(0) if m else str(text or "").strip()


def _normalize_solution_block(block: dict[str, Any] | str) -> dict[str, Any] | None:
    if isinstance(block, str):
        formula_latex = _coerce_formula_like_text_to_latex(block)
        if formula_latex:
            return {"type": "latex_display", "content": formula_latex}
        content = _plain_text(_normalize_math_tokens(block))
        if not content:
            return None
        if "\\begin{" in content or content.startswith("\\["):
            return {"type": "latex_display", "content": normalize_differential_tokens(_strip_display_delimiters(content))}
        return {"type": "text", "content": content}
    if not isinstance(block, dict):
        return None

    btype = str(block.get("type") or "text")
    content = block.get("content", "")
    if btype in {"latex_display", "latex"}:
        latex = _finalize_display_latex(
            normalize_differential_tokens(_strip_display_delimiters(_normalize_math_tokens(content)))
        )
        if not latex:
            return None
        case_blocks = _split_cases_environments_to_blocks(latex)
        if case_blocks:
            return case_blocks[0] if len(case_blocks) == 1 else case_blocks
        if _block_is_explicit_inline(block):
            return {"type": "text", "content": f"${latex}$"}
        if btype == "latex_display" and should_render_formula_inline(latex):
            return {"type": "text", "content": f"${latex}$"}
        return _view_block_for_latex(
            latex,
            force_display=_block_is_explicit_display(block),
        )
    if btype == "equation_group":
        items = [
            _finalize_display_latex(
                normalize_differential_tokens(_strip_display_delimiters(_normalize_math_tokens(i)))
            )
            for i in block.get("items") or []
            if str(i).strip()
        ]
        return {"type": "equation_group", "items": items, "layout": block.get("layout", "vertical")} if items else None
    if btype == "derivation_chain":
        items = [
            _finalize_display_latex(
                normalize_differential_tokens(_strip_display_delimiters(_normalize_math_tokens(i)))
            )
            for i in block.get("items") or []
            if str(i).strip()
        ]
        return {"type": "derivation_chain", "items": items} if items else None
    if btype == "cases":
        rows = []
        from latex_utils import normalize_derivation_formula_block
        for row in block.get("rows") or []:
            if isinstance(row, dict):
                expr = normalize_derivation_formula_block(
                    _normalize_math_tokens(row.get("expr") or row.get("value") or "")
                )
                if r"\begin{cases}" in expr:
                    rows.extend({"expr": r.strip(), "condition": ""} for r in _cases_env_to_rows(expr))
                else:
                    rows.append({
                        **row,
                        "expr": normalize_cases_spacing(expr),
                        "condition": normalize_cases_spacing(_normalize_math_tokens(row.get("condition") or "")),
                    })
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                rows.append([
                    normalize_cases_spacing(_normalize_math_tokens(row[0])),
                    normalize_cases_spacing(_normalize_math_tokens(row[1])),
                ])
            else:
                rows.append(row)
        return {
            "type": "cases",
            "lhs": normalize_cases_spacing(_strip_display_delimiters(_normalize_math_tokens(block.get("lhs", "")))),
            "rows": rows,
        }

    text = _plain_text(content)
    if not text:
        return None
    formula_latex = _coerce_formula_like_text_to_latex(text)
    if formula_latex:
        return {"type": "latex_display", "content": _finalize_display_latex(formula_latex)}
    if "\\begin{" in text and _looks_like_latex_display(text):
        return {
            "type": "latex_display",
            "content": _finalize_display_latex(
                normalize_differential_tokens(_strip_display_delimiters(text))
            ),
        }
    return {"type": "text", "content": normalize_inline_math_tokens(_normalize_math_tokens(text))}


def _blocks_from_text(text: str) -> list[dict[str, Any]]:
    import re
    raw = _normalize_math_tokens(text)
    blocks: list[dict[str, Any]] = []
    pos = 0
    for match in re.finditer(r"\$\$(.*?)\$\$|\\\[(.*?)\\\]", raw, flags=re.S):
        prefix = raw[pos:match.start()].strip()
        if prefix:
            _append_normalized_blocks(blocks, _normalize_solution_block(prefix))
        latex = match.group(1) if match.group(1) is not None else match.group(2)
        _append_normalized_blocks(
            blocks,
            _view_block_for_latex(_finalize_display_latex(latex), force_display=True),
        )
        pos = match.end()
    suffix = raw[pos:].strip()
    if suffix:
        _append_normalized_blocks(blocks, _normalize_solution_block(suffix))
    return consolidate_view_blocks(blocks)


def _legacy_steps_to_structured(
    solution: dict[str, Any] | None,
    *,
    default_kind: str = "reasoning",
) -> dict[str, Any] | None:
    """Map legacy ``steps`` arrays into the same structured contract as 解答题."""
    steps_out: list[dict[str, Any]] = []
    for idx, raw in enumerate((solution or {}).get("steps") or []):
        if isinstance(raw, dict):
            steps_out.append(
                _normalize_step_derivation_meta({
                    "label": raw.get("label") or f"步骤{idx + 1}",
                    "body_markdown": raw.get("body_markdown")
                    or raw.get("derivation_markdown")
                    or raw.get("content")
                    or "",
                    "goal": raw.get("goal", ""),
                    "reason": raw.get("reason") or raw.get("justification", ""),
                    "blocks": raw.get("blocks") or [],
                    "conclusion": raw.get("conclusion", ""),
                    "operation": raw.get("operation") or default_kind,
                })
            )
        elif isinstance(raw, str) and raw.strip():
            steps_out.append(
                _normalize_step_derivation_meta({
                    "label": f"步骤{idx + 1}",
                    "body_markdown": raw.strip(),
                    "operation": default_kind,
                })
            )
    return {"steps": steps_out} if steps_out else None


def _resolve_structured_for_view(
    solution: dict[str, Any] | None,
    question_type: str | None,
    grading_result: dict[str, Any] | None = None,
    *,
    default_kind: str = "reasoning",
) -> dict[str, Any] | None:
    """Prefer structured steps; fall back to type-specific or legacy step builders."""
    sol = solution or {}
    structured = sol.get("_structured")
    if _has_structured_steps(structured):
        return structured
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    built = build_question_type_structured_solution(sol, q_type, grading_result)
    if _has_structured_steps(built):
        return built
    return _legacy_steps_to_structured(sol, default_kind=default_kind)


def _structured_to_sections(structured: dict[str, Any] | None, default_kind: str = "reasoning") -> list[dict[str, Any]]:
    if not isinstance(structured, dict):
        return []
    sections: list[dict[str, Any]] = []
    for idx, step in enumerate(structured.get("steps") or []):
        if not isinstance(step, dict):
            continue
        step = _normalize_step_derivation_meta(step)
        raw_blocks = step.get("blocks") or []
        if not raw_blocks:
            raw_text = step.get("body_markdown") or step.get("derivation_markdown") or step.get("content") or step.get("explanation") or ""
            if not raw_text:
                fallback_parts = []
                has_meta = bool(
                    _strip_step_title_prefix(_plain_text(step.get("goal", "")))
                    or _plain_text(step.get("reason") or step.get("justification") or "")
                )
                for key, label in (
                    ("goal", "推导目标"),
                    ("reason", "推导理由"),
                    ("justification", "推导理由"),
                    ("conclusion", "本步结论"),
                ):
                    if has_meta and key in {"goal", "reason", "justification"}:
                        continue
                    value = _plain_text(step.get(key, ""))
                    if key == "goal":
                        value = _strip_step_title_prefix(value)
                    if value and f"{label}：{value}" not in fallback_parts:
                        fallback_parts.append(f"{label}：{value}")
                raw_text = "\n\n".join(fallback_parts)
            raw_blocks = _blocks_from_text(raw_text)
        blocks = []
        for block in raw_blocks:
            _append_normalized_blocks(blocks, _normalize_solution_block(block))
        goal = _strip_step_title_prefix(_plain_text(step.get("goal", "")))
        reason = _plain_text(step.get("reason") or step.get("justification") or "")
        conclusion = _plain_text(step.get("conclusion", ""))
        if blocks or goal or reason or conclusion:
            title = str(step.get("label") or f"步骤{idx + 1}").strip()
            sections.append({
                "title": title,
                "kind": str(step.get("operation") or default_kind),
                "blocks": blocks,
                "goal": goal,
                "reason": reason,
                "conclusion": conclusion,
            })
    return sections


def _legacy_sections(text: str, *, title: str, kind: str) -> list[dict[str, Any]]:
    blocks = _blocks_from_text(text)
    return [{"title": title, "kind": kind, "blocks": blocks, "conclusion": ""}] if blocks else []


def _blocks_from_value(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        blocks: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("content") or item.get("text") or item.get("reason") or item.get("value") or ""
                normalized = _normalize_solution_block({"type": item.get("type", "text"), "content": text})
                if isinstance(normalized, list):
                    blocks.extend(normalized)
                elif isinstance(normalized, dict):
                    if normalized.get("type") == "text":
                        blocks.extend(normalize_text_block_math(str(normalized.get("content") or "")))
                    else:
                        blocks.append(normalized)
            else:
                blocks.extend(_blocks_from_text(str(item)))
        return consolidate_view_blocks(blocks)
    return _blocks_from_text(str(value))


def _append_section(sections: list[dict[str, Any]], title: str, kind: str, value: Any, *, conclusion: str = "") -> None:
    blocks = _blocks_from_value(value)
    if blocks or conclusion:
        sections.append({
            "title": title,
            "kind": kind,
            "blocks": blocks,
            "conclusion": _plain_text(conclusion),
        })


def _section_to_structured_step(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(section.get("title") or "步骤").strip(),
        "operation": str(section.get("kind") or "reasoning"),
        "blocks": _normalize_block_list(section.get("blocks") or []),
        "conclusion": _plain_text(section.get("conclusion", "")),
    }


def _has_structured_steps(structured: Any) -> bool:
    return isinstance(structured, dict) and bool(structured.get("steps"))


def _extract_marked_final_answer(text: str, question_type: str | None = None) -> str:
    q_type = _coerce_question_type(question_type)
    limit = {"选择题": 80, "填空题": 120, "解答题": 200, "证明题": 160}.get(q_type, 160)
    raw = _normalize_math_tokens(text)
    if not raw.strip():
        return ""
    if len(raw) > limit and any(marker in raw for marker in ("步骤1", "步骤2", "关键计算", "选项分析", "##")):
        pass
    patterns = [
        r"(?:最终答案|答案|结论)\s*[：:为是]?\s*([^\n。；;]+)",
        r"(故选)\s*([A-D])",
        r"(?:综上|因此)\s*[，,]?\s*([^\n。；;]{1," + str(limit) + r"})",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, raw):
            candidate = (m.group(2) if pattern.startswith("(故选)") and m.lastindex and m.lastindex >= 2 else m.group(1)).strip()
            candidate = candidate.strip(" ：:，,。.;；")
            if 0 < len(candidate) <= limit:
                return candidate
    short = raw.strip()
    if len(short) <= limit and not any(marker in short for marker in ("步骤1", "步骤2", "关键计算", "选项分析", "##")):
        if q_type in {"选择题", "填空题"} or _looks_like_latex_display(short):
            return short
    return ""


def _extract_final_answer(solution: dict[str, Any], question_type: str | None = None) -> dict[str, Any]:
    structured = solution.get("_structured")
    if isinstance(structured, dict):
        fa = structured.get("final_answer")
        if isinstance(fa, dict) and fa.get("content"):
            return _normalize_solution_block({"type": fa.get("type", "text"), "content": fa.get("content")}) or {
                "type": "text", "content": _plain_text(fa.get("content"))
            }
        if isinstance(fa, str) and fa.strip():
            return {"type": "text", "content": _plain_text(fa)}
    text = _solution_text(solution)
    candidate = _extract_marked_final_answer(text, question_type)
    if candidate and _looks_like_latex_display(candidate):
        return {"type": "latex_display", "content": _strip_display_delimiters(candidate)}
    return {"type": "text", "content": _plain_text(candidate)} if candidate else {}


def _option_analysis_sections(solution: dict[str, Any]) -> list[dict[str, Any]]:
    choice_solution = solution.get("choice_solution") or solution.get("_choice_solution") or {}
    option_analysis = choice_solution.get("option_analysis") if isinstance(choice_solution, dict) else None
    if not isinstance(option_analysis, dict):
        option_analysis = solution.get("option_analysis") if isinstance(solution.get("option_analysis"), dict) else None
    if not isinstance(option_analysis, dict):
        return []
    blocks = []
    for key in ("A", "B", "C", "D"):
        value = option_analysis.get(key)
        if value:
            blocks.append({"type": "text", "content": _plain_text(f"{key}：{value}")})
    return [{"title": "选项分析", "kind": "option_analysis", "blocks": blocks, "conclusion": ""}] if blocks else []


def _choice_payload(solution: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    choice_solution = solution.get("choice_solution") or solution.get("_choice_solution") or {}
    if isinstance(choice_solution, dict):
        payload.update(choice_solution)
    for key in (
        "answer", "correct_answer", "correct_option", "choice_answer",
        "core_reason", "calculation_steps", "calculation",
        "option_analysis", "conclusion", "thought_process",
    ):
        if key in solution and solution.get(key) not in (None, ""):
            payload.setdefault(key, solution.get(key))
    return payload


def _extract_choice_conclusion_letter(text: str) -> str:
    raw = str(text or "")
    if not raw.strip():
        return ""
    patterns = [
        r"(?:正确选项|正确答案|标准答案|最终答案|答案)\s*[：:为是]?\s*[（(]?\s*([A-D])\s*[）)]?",
        r"(?:故选|应选|选择|选)\s*[（(]?\s*([A-D])\s*[）)]?",
        r"选项\s*[（(]?\s*([A-D])\s*[）)]?\s*(?:正确|符合|匹配|成立)",
        r"([A-D])\s*(?:项|选项)\s*(?:正确|符合|匹配|成立)",
    ]
    candidates: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, raw, flags=re.I):
            candidates.append((match.start(), match.group(1).upper()))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _option_analysis_blocks(option_analysis: Any, correct: str = "") -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    correct = str(correct or "").strip().upper()
    if isinstance(option_analysis, dict):
        iterable = [(str(k).upper(), v) for k, v in option_analysis.items()]
    elif isinstance(option_analysis, list):
        iterable = []
        for item in option_analysis:
            if isinstance(item, dict):
                key = str(item.get("option") or item.get("label") or item.get("key") or "").upper()
                value = item.get("reason") or item.get("analysis") or item.get("content") or item.get("text") or ""
                iterable.append((key, value))
            else:
                iterable.append(("", item))
    else:
        return []
    for key, value in iterable:
        if not value:
            continue
        mark = "✅ 正确" if key and key == correct else "❌ 错误" if key in {"A", "B", "C", "D"} and correct else ""
        prefix = f"{key} {mark}：" if key else ""
        blocks.extend(_blocks_from_text(prefix + _plain_text(value)))
    return blocks


_CHOICE_INLINE_SECTION_TITLES: dict[str, tuple[str, str]] = {
    "解题思路": ("核心依据", "reasoning"),
    "核心思路": ("核心依据", "reasoning"),
    "核心依据": ("核心依据", "reasoning"),
    "关键计算": ("关键计算", "calculation"),
    "计算过程": ("关键计算", "calculation"),
    "选项分析": ("选项分析", "option_analysis"),
    "选项解析": ("选项分析", "option_analysis"),
    "知识点": ("知识点", "knowledge"),
    "关键知识点": ("知识点", "knowledge"),
    "考查知识点": ("知识点", "knowledge"),
    "常见误区": ("常见误区", "common_traps"),
    "易错提示": ("常见误区", "common_traps"),
    "秒杀技巧": ("秒杀技巧", "fast_method"),
    "快速方法": ("秒杀技巧", "fast_method"),
    "最终答案": ("最终结论", "conclusion"),
    "最终结论": ("最终结论", "conclusion"),
    "结论": ("最终结论", "conclusion"),
}

_CHOICE_INLINE_SECTION_RE = re.compile(
    r"(?:[【\[]\s*(?P<bracket>"
    + "|".join(re.escape(k) for k in sorted(_CHOICE_INLINE_SECTION_TITLES, key=len, reverse=True))
    + r")\s*[】\]]|(?:^|\n)\s*#{1,6}\s*(?P<heading>"
    + "|".join(re.escape(k) for k in sorted(_CHOICE_INLINE_SECTION_TITLES, key=len, reverse=True))
    + r")\s*(?:\n|$))"
)


_FILL_INLINE_SECTION_TITLES: dict[str, tuple[str, str]] = {
    "解题思路": ("解题思路", "reasoning"),
    "核心思路": ("解题思路", "reasoning"),
    "核心依据": ("解题思路", "reasoning"),
    "关键条件": ("关键条件", "condition"),
    "关键计算": ("关键计算", "calculation"),
    "计算过程": ("关键计算", "calculation"),
    "答案形式": ("答案形式", "answer_form"),
    "知识点": ("知识点", "knowledge"),
    "关键知识点": ("知识点", "knowledge"),
    "考查知识点": ("知识点", "knowledge"),
    "常见误区": ("常见误区", "common_traps"),
    "易错提示": ("常见误区", "common_traps"),
    "巩固建议": ("巩固建议", "suggestion"),
    "提分建议": ("巩固建议", "suggestion"),
    "最终答案": ("最终填空", "final_fill"),
    "最终结论": ("最终填空", "final_fill"),
    "结论": ("最终填空", "final_fill"),
}

_FILL_INLINE_SECTION_RE = re.compile(
    r"(?:[【\[]\s*(?P<bracket>"
    + "|".join(re.escape(k) for k in sorted(_FILL_INLINE_SECTION_TITLES, key=len, reverse=True))
    + r")\s*[】\]]|(?:^|\n)\s*#{1,6}\s*(?P<heading>"
    + "|".join(re.escape(k) for k in sorted(_FILL_INLINE_SECTION_TITLES, key=len, reverse=True))
    + r")\s*(?:\n|$))"
)


def _split_choice_inline_labeled_sections(text: str) -> list[dict[str, Any]]:
    """Split AI choice prose when it embeds labels like 【知识点】 in one block."""
    raw = _normalize_math_tokens(text)
    if not raw.strip():
        return []
    matches = list(_CHOICE_INLINE_SECTION_RE.finditer(raw))
    if not matches:
        return []

    sections: list[dict[str, Any]] = []
    used: dict[str, int] = {}

    def _append(title: str, kind: str, content: str) -> None:
        chunk = content.strip(" \n\t：:，,。；;")
        if not chunk:
            return
        count = used.get(title, 0) + 1
        used[title] = count
        unique_title = title if count == 1 else f"{title}{count}"
        blocks = _blocks_from_text(chunk)
        if blocks:
            sections.append({
                "title": unique_title,
                "kind": kind,
                "blocks": blocks,
                "conclusion": "",
            })

    prefix = raw[:matches[0].start()].strip()
    if prefix:
        _append("核心依据", "reasoning", prefix)

    for idx, match in enumerate(matches):
        label = (match.group("bracket") or match.group("heading") or "").strip()
        title, kind = _CHOICE_INLINE_SECTION_TITLES.get(label, ("核心依据", "reasoning"))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        _append(title, kind, raw[start:end])
    return sections


def _expand_choice_inline_labeled_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for section in sections or []:
        text = "\n".join(
            _block_text(block)
            for block in section.get("blocks") or []
            if isinstance(block, dict)
        )
        split = _split_choice_inline_labeled_sections(text)
        if split:
            expanded.extend(split)
        else:
            expanded.append(section)
    return expanded


def _split_fill_inline_labeled_sections(text: str) -> list[dict[str, Any]]:
    """Split AI fill-in prose when labels like 【知识点】 are embedded in one block."""
    raw = _normalize_math_tokens(text)
    if not raw.strip():
        return []
    matches = list(_FILL_INLINE_SECTION_RE.finditer(raw))
    if not matches:
        return []

    sections: list[dict[str, Any]] = []
    used: dict[str, int] = {}

    def _append(title: str, kind: str, content: str) -> None:
        chunk = content.strip(" \n\t：:，,。；;")
        if not chunk:
            return
        count = used.get(title, 0) + 1
        used[title] = count
        unique_title = title if count == 1 else f"{title}{count}"
        blocks = _blocks_from_text(chunk)
        if blocks:
            sections.append({
                "title": unique_title,
                "kind": kind,
                "blocks": blocks,
                "conclusion": "",
            })

    prefix = raw[:matches[0].start()].strip()
    if prefix:
        _append("解题思路", "reasoning", prefix)

    for idx, match in enumerate(matches):
        label = (match.group("bracket") or match.group("heading") or "").strip()
        title, kind = _FILL_INLINE_SECTION_TITLES.get(label, ("解题思路", "reasoning"))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        _append(title, kind, raw[start:end])
    return sections


def _expand_fill_inline_labeled_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for section in sections or []:
        text = "\n".join(
            _block_text(block)
            for block in section.get("blocks") or []
            if isinstance(block, dict)
        )
        split = _split_fill_inline_labeled_sections(text)
        if split:
            expanded.extend(split)
        else:
            expanded.append(section)
    return expanded


def _structured_choice_has_inline_labels(structured: dict[str, Any] | None) -> bool:
    if not isinstance(structured, dict):
        return False
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        candidates = [
            str(step.get("label") or ""),
            str(step.get("body_markdown") or ""),
            str(step.get("derivation_markdown") or ""),
            str(step.get("explanation") or ""),
        ]
        for block in step.get("blocks") or []:
            if isinstance(block, dict):
                candidates.append(_block_text(block))
        if any(_CHOICE_INLINE_SECTION_RE.search(text) for text in candidates if text):
            return True
    return False


def _choice_structured_lacks_semantic_sections(structured: dict[str, Any] | None) -> bool:
    """True when legacy polish produced generic 步骤N labels without choice section titles."""
    steps = [step for step in (structured or {}).get("steps") or [] if isinstance(step, dict)]
    if not steps:
        return True
    labels = [str(step.get("label") or "").strip() for step in steps]
    if any(marker in label for label in labels for marker in ("核心", "关键", "选项", "最终", "思路", "依据")):
        return False
    generic = [label for label in labels if re.match(r"^步骤\s*\d+$", label)]
    if len(generic) >= 3:
        return False
    return len(generic) <= 2 and len(steps) <= 2


def _structured_choice_sections(structured: dict[str, Any] | None) -> list[dict[str, Any]]:
    sections = _structured_to_sections(structured, "reasoning")
    normalized: list[dict[str, Any]] = []
    for section in sections:
        split_sections = _expand_choice_inline_labeled_sections([section])
        if len(split_sections) > 1 or (split_sections and split_sections[0] is not section):
            normalized.extend(split_sections)
            continue
        title = str(section.get("title") or "")
        text = title + " " + " ".join(_block_text(b) for b in section.get("blocks") or [])
        has_option_letter = bool(re.search(r"(?:^|[\s（(，,。；;：:])(?:选项)?[A-D](?:[\s）).：:项]|$)", text))
        has_option_judgement = any(marker in text for marker in ("正确", "错误", "符合", "不对", "排除", "成立", "不成立"))
        if "选项分析" in title or (has_option_letter and has_option_judgement):
            section["title"] = "选项分析"
            section["kind"] = "option_analysis"
        elif any(marker in text for marker in ("计算", "代入", "概率", "方差", "分布", "求得", "化简")):
            section["title"] = "关键计算"
            section["kind"] = "calculation"
        elif any(marker in text for marker in ("故选", "答案为", "正确选项")):
            section["title"] = "最终结论"
            section["kind"] = "conclusion"
        else:
            section["title"] = "核心依据" if not normalized else title or "核心依据"
            section["kind"] = section.get("kind") or "reasoning"
        normalized.append(section)
    return normalized


def _legacy_choice_sections(text: str, answer: str | None = None) -> list[dict[str, Any]]:
    bracket_sections = _split_choice_inline_labeled_sections(text)
    if bracket_sections:
        return bracket_sections

    raw = _normalize_math_tokens(text)
    if not raw or not any(marker in raw for marker in ("步骤", "核心", "思路", "计算", "选项", "故选", "答案", "应选", "选 ")):
        return []

    markers: list[tuple[int, str]] = []
    marker_specs = [
        ("核心依据", r"(?:##\s*)?(?:步骤[一1]|一[、.．]|Ⅰ[.．]|1[.．、])\s*(?:核心|思路|依据)?|本题为选择题|核心思路"),
        ("关键计算", r"(?:##\s*)?(?:步骤[二2]|二[、.．]|Ⅱ[.．]|2[.．、])\s*(?:关键)?计算|实际计算结果为|关键计算|计算过程"),
        ("选项分析", r"(?:##\s*)?(?:步骤[三3]|三[、.．]|Ⅲ[.．]|3[.．、])?\s*选项分析|选项中若出现|选项[ABCD]|[（(]?[ABCD][）).：:项]\s*.*?(?:正确|错误|符合|不对)"),
        ("最终结论", r"(?:因此|所以)?\s*(?:答案[为是]|正确答案[为是]|正确选项[为是]|故选|选|应选)\s*[A-D]"),
    ]
    for title, pattern in marker_specs:
        match = re.search(pattern, raw, flags=re.S)
        if match:
            markers.append((match.start(), title))
    if not markers:
        return []
    markers = sorted(markers, key=lambda item: item[0])
    if markers[0][0] > 0:
        markers.insert(0, (0, "核心依据"))

    sections: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for idx, (start, title) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(raw)
        chunk = raw[start:end].strip()
        if not chunk:
            continue
        unique_title = title
        if unique_title in seen_titles:
            unique_title = f"{title}{len(seen_titles) + 1}"
        seen_titles.add(unique_title)
        blocks = _blocks_from_text(chunk)
        if title == "选项分析":
            option_blocks = []
            for opt_match in re.finditer(r"(?:选项)?[（(]?([A-D])[）).：:项]?\s*([^ABCD\n。；;]*(?:正确|错误|符合|不对)[^ABCD\n。；;]*)", chunk):
                letter, reason = opt_match.group(1), opt_match.group(2).strip(" ：:，,。")
                if reason:
                    mark = "✅ 正确" if str(answer or "").upper() == letter else "❌ 错误" if answer else ""
                    option_blocks.extend(_blocks_from_text(f"{letter} {mark}：{reason}"))
            if option_blocks:
                blocks = option_blocks
        if blocks:
            sections.append({
                "title": unique_title,
                "kind": {
                    "核心依据": "reasoning",
                    "关键计算": "calculation",
                    "选项分析": "option_analysis",
                    "最终结论": "conclusion",
                }.get(title, "reasoning"),
                "blocks": blocks,
                "conclusion": "",
            })
    return sections


def build_choice_solution_view(
    solution: dict[str, Any],
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gr = grading_result or {}
    payload = _choice_payload(solution)
    trusted_answer_text = (
        gr.get("correct_option")
        or gr.get("correct_answer")
        or payload.get("correct_option")
        or payload.get("correct_answer")
        or payload.get("choice_answer")
        or payload.get("answer")
    )
    answer_text = (
        trusted_answer_text
        or _solution_text(solution)
    )
    trusted_correct = _choice_letter(trusted_answer_text)
    correct = _choice_letter(answer_text)
    student = gr.get("student_answer", "")
    sections = []
    structured = _resolve_structured_for_view(solution, "选择题", gr, default_kind="reasoning")
    if _has_structured_steps(structured) and (
        not _choice_structured_lacks_semantic_sections(structured)
        or _structured_choice_has_inline_labels(structured)
    ):
        sections.extend(_structured_choice_sections(structured))
    else:
        if payload.get("core_reason"):
            _append_section(sections, "核心依据", "reasoning", payload.get("core_reason"))
        elif payload.get("thought_process"):
            _append_section(sections, "核心依据", "reasoning", payload.get("thought_process"))
        if payload.get("calculation_steps"):
            _append_section(sections, "关键计算", "calculation", payload.get("calculation_steps"))
        elif payload.get("calculation"):
            _append_section(sections, "关键计算", "calculation", payload.get("calculation"))
        option_blocks = _option_analysis_blocks(payload.get("option_analysis"), correct)
        if option_blocks:
            sections.append({"title": "选项分析", "kind": "option_analysis", "blocks": option_blocks, "conclusion": ""})
        if payload.get("conclusion"):
            _append_section(sections, "最终结论", "conclusion", payload.get("conclusion"))
    sections = _expand_choice_inline_labeled_sections(sections)
    if not sections and len(_solution_text(solution)) > 1 and _solution_text(solution).upper() != correct:
        sections.extend(_legacy_choice_sections(_solution_text(solution), correct))
        if not sections:
            sections.extend(_legacy_sections(_solution_text(solution), title="核心依据", kind="reasoning"))
    sections = _expand_choice_inline_labeled_sections(sections)
    if not any(s.get("kind") == "option_analysis" for s in sections):
        sections.extend(_option_analysis_sections(solution))
    if correct and not sections:
        sections.append({
            "title": "核心依据",
            "kind": "reasoning",
            "blocks": [{"type": "text", "content": "详细解析暂未生成。"}],
            "conclusion": "",
        })
    section_text = "\n".join(
        " ".join(_block_text(block) for block in section.get("blocks") or [])
        + "\n"
        + str(section.get("conclusion") or "")
        for section in sections
    )
    generated_choice = _extract_choice_conclusion_letter(section_text or _solution_text(solution))
    if trusted_correct and generated_choice and generated_choice != trusted_correct:
        sections = [{
            "title": "答案一致性提示",
            "kind": "consistency_warning",
            "blocks": [{
                "type": "text",
                "content": (
                    f"AI 生成解析的结论为 {generated_choice}，"
                    f"与题库标准答案 {trusted_correct} 不一致。已停止展示本次解析，请人工复核标准答案。"
                ),
            }],
            "conclusion": "",
        }]
        correct = trusted_correct
    final_content = f"故选 \\({correct}\\)。" if correct else "详细解析暂未生成，可重新生成标准解答。"
    return {
        "question_type": "选择题",
        "answer_card": {
            "correct_answer": correct,
            "student_answer": student,
            "is_correct": gr.get("is_correct"),
        },
        "sections": sections,
        "final_answer": {"type": "text", "content": final_content},
        "meta": {"source": "standard_solution_view"},
    }


def _has_step_markers(text: str) -> bool:
    return bool(re.search(r"步骤\s*[一二三四五六七八九十\d]|##|关键计算|选项分析", str(text or "")))


def is_choice_solution_stub(
    solution: dict | None,
    grading_result: dict | None = None,
) -> bool:
    """True when only the correct option line is available, not a full derivation."""
    q_type = _coerce_question_type(
        (solution or {}).get("question_type")
        or (grading_result or {}).get("question_type")
    )
    if q_type != "选择题":
        return False
    payload = (solution or {}).get("choice_solution") or {}
    if isinstance(payload, dict) and str(payload.get("thought_process") or "").strip():
        return False
    structured = (solution or {}).get("_structured") if isinstance(solution, dict) else None
    if isinstance(structured, dict) and (structured.get("steps") or []):
        return False
    text = _solution_text(solution)
    if _has_step_markers(text):
        return False
    stripped = text.strip()
    if not stripped:
        return True
    if re.match(r"^正确选项\s*[:：]", stripped) and len(stripped) < 320:
        return True
    return len(stripped) < 100


def _looks_like_long_explanation(text: str) -> bool:
    s = str(text or "").strip()
    chinese_count = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")
    return chinese_count >= 18 or len(s) > 120


def _accept_fill_answer(value: Any) -> str:
    candidate = _strip_display_delimiters(_normalize_math_tokens(value)).strip()
    candidate = candidate.replace("$", "").strip()
    while candidate.startswith(r"\(") and candidate.endswith(r"\)"):
        candidate = candidate[2:-2].strip()
    candidate = re.sub(r"^(?:答案|最终答案|故填|填)\s*[：:为]?\s*", "", candidate).strip()
    candidate = candidate.strip(" 。；;，,")
    if not candidate or len(candidate) > 120:
        return ""
    if _has_step_markers(candidate):
        return ""
    if _looks_like_long_explanation(candidate) and not _looks_like_latex_display(candidate):
        return ""
    if _is_incomplete_math_expr(candidate):
        return ""
    return candidate


def extract_fill_final_answer(
    solution: dict[str, Any] | None,
    grading_result: dict[str, Any] | None = None,
) -> str | None:
    sol = solution or {}
    gr = grading_result or {}
    for value in (
        gr.get("correct_answer"),
        sol.get("correct_answer"),
        sol.get("answer"),
        sol.get("final_answer"),
    ):
        accepted = _accept_fill_answer(value)
        if accepted:
            return accepted
    structured = sol.get("_structured")
    if isinstance(structured, dict):
        fa = structured.get("final_answer")
        if isinstance(fa, dict):
            accepted = _accept_fill_answer(fa.get("content") or fa.get("value"))
        else:
            accepted = _accept_fill_answer(fa)
        if accepted:
            return accepted
    text = _solution_text(sol)
    for pattern in (
        r"(?:最终答案|故填|填)\s*[：:为]?\s*([^\n。；;]+)",
        r"答案\s*[：:]\s*([^\n。；;]+)",
        r"(?:因此|所以)\s*[，,]?\s*([^\n。；;]{1,120})",
    ):
        for match in re.finditer(pattern, text):
            accepted = _accept_fill_answer(match.group(1))
            if accepted:
                return accepted
    accepted = _accept_fill_answer(text)
    return accepted or None


def build_question_type_structured_solution(
    solution: dict[str, Any] | None,
    question_type: str | None,
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a lightweight _structured contract from type-specific fields.

    This is used only for AI grading solution display. It does not alter the
    question-bank renderer and does not branch on question source.
    """
    sol = dict(solution or {})
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    gr = grading_result or {}
    sections: list[dict[str, Any]] = []

    if q_type == "选择题":
        payload = _choice_payload(sol)
        answer_text = (
            gr.get("correct_option")
            or gr.get("correct_answer")
            or payload.get("correct_option")
            or payload.get("correct_answer")
            or payload.get("choice_answer")
            or payload.get("answer")
        )
        correct = _choice_letter(answer_text)
        if payload.get("core_reason"):
            _append_section(sections, "核心依据", "reasoning", payload.get("core_reason"))
        elif payload.get("thought_process"):
            _append_section(sections, "核心依据", "reasoning", payload.get("thought_process"))
        if payload.get("calculation_steps"):
            _append_section(sections, "关键计算", "calculation", payload.get("calculation_steps"))
        elif payload.get("calculation"):
            _append_section(sections, "关键计算", "calculation", payload.get("calculation"))
        option_blocks = _option_analysis_blocks(payload.get("option_analysis"), correct)
        if option_blocks:
            sections.append({
                "title": "选项分析",
                "kind": "option_analysis",
                "blocks": option_blocks,
                "conclusion": "",
            })
        conclusion = payload.get("conclusion") or (f"故选 {correct}" if correct and sections else "")
        if conclusion:
            _append_section(sections, "最终结论", "conclusion", conclusion)
        final_answer = {"type": "text", "content": conclusion} if conclusion else None

    elif q_type == "填空题":
        correct = extract_fill_final_answer(sol, gr) or ""
        if sol.get("key_conditions"):
            _append_section(sections, "关键条件", "condition", sol.get("key_conditions"))
        if sol.get("calculation_steps"):
            _append_section(sections, "关键计算", "calculation", sol.get("calculation_steps"))
        elif sol.get("calculation"):
            _append_section(sections, "关键计算", "calculation", sol.get("calculation"))
        if sol.get("answer_form_note"):
            _append_section(sections, "答案形式", "answer_form", sol.get("answer_form_note"))
        conclusion = sol.get("conclusion") or (f"故填 {correct}" if correct else "")
        if conclusion and sections:
            _append_section(sections, "最终填空", "final_fill", conclusion)
        final_answer = (
            {"type": "latex_display", "content": _strip_display_delimiters(correct)}
            if correct else None
        )

    else:
        return None

    if not sections:
        return None
    return {
        "steps": [_section_to_structured_step(section) for section in sections],
        "final_answer": final_answer,
        "metadata": {"question_type": q_type},
    }


def _without_final_answer_text(text: str, final_answer: str | None) -> str:
    s = str(text or "")
    if final_answer:
        s = s.replace(str(final_answer), "")
    s = re.sub(r"(?:最终答案|故填|填)\s*[：:为]?\s*[^\n。；;]+[。；;]?", "", s)
    s = re.sub(r"最终\s*", "", s)
    s = re.sub(r"答案\s*[：:]\s*[^\n。；;]+[。；;]?", "", s)
    return s.strip()


def _legacy_fill_sections(text: str, final_answer: str | None = None) -> list[dict[str, Any]]:
    bracket_sections = _split_fill_inline_labeled_sections(text)
    if bracket_sections:
        return bracket_sections

    raw = _without_final_answer_text(_normalize_math_tokens(text), final_answer)
    if not raw:
        return []
    marker_specs = [
        ("关键条件", "condition", r"由题意|根据|已知|设|令"),
        ("关键计算", "calculation", r"计算|化简|得|推出|代入|求得"),
        ("答案形式", "answer_form", r"答案可写为|等价|可写为|化简为|同样可写|注意"),
        ("最终填空", "final_fill", r"答案|最终答案|故填|填"),
    ]
    markers: list[tuple[int, str, str]] = []
    for title, kind, pattern in marker_specs:
        match = re.search(pattern, raw)
        if match:
            markers.append((match.start(), title, kind))
    if not markers:
        if len(raw) <= 220 or not _has_step_markers(raw):
            return _legacy_sections(raw, title="关键计算", kind="calculation")
        return []
    markers = sorted(markers, key=lambda item: item[0])
    if markers[0][0] > 0:
        markers.insert(0, (0, "关键条件", "condition"))
    sections: list[dict[str, Any]] = []
    used: set[str] = set()
    for idx, (start, title, kind) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(raw)
        chunk = raw[start:end].strip(" 。；;\n")
        if not chunk:
            continue
        if title == "最终填空" and re.search(r"答案可写为|可写为|等价|化简为|同样可写", chunk):
            title, kind = "答案形式", "answer_form"
        unique = title if title not in used else f"{title}{len(used) + 1}"
        used.add(unique)
        blocks = _blocks_from_text(chunk)
        if blocks:
            sections.append({"title": unique, "kind": kind, "blocks": blocks, "conclusion": ""})
    return sections


def build_fill_solution_view(
    solution: dict[str, Any],
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gr = grading_result or {}
    correct = extract_fill_final_answer(solution, gr) or ""
    structured = _resolve_structured_for_view(solution, "填空题", gr, default_kind="calculation")
    sections = _structured_to_sections(structured, "calculation")
    sections = _expand_fill_inline_labeled_sections(sections)
    if not sections:
        if solution.get("key_conditions"):
            _append_section(sections, "关键条件", "condition", solution.get("key_conditions"))
        if solution.get("calculation_steps"):
            _append_section(sections, "关键计算", "calculation", solution.get("calculation_steps"))
        elif solution.get("calculation"):
            _append_section(sections, "关键计算", "calculation", solution.get("calculation"))
        if solution.get("answer_form_note"):
            _append_section(sections, "答案形式", "answer_form", solution.get("answer_form_note"))
    if not sections and _solution_text(solution) and _solution_text(solution) != str(correct):
        sections = _legacy_fill_sections(_solution_text(solution), correct)
    sections = _expand_fill_inline_labeled_sections(sections)
    if not sections and correct:
        sections.append({
            "title": "关键计算",
            "kind": "calculation",
            "blocks": [{"type": "text", "content": "详细解析暂未生成。"}],
            "conclusion": "",
        })
    elif sections and (gr.get("quick_compare_confidence") is not None or gr.get("quick_compare_status")):
        sections.append({
            "title": "答案形式",
            "kind": "answer_form",
            "blocks": [{"type": "text", "content": "可接受与标准答案等价的化简形式。"}],
            "conclusion": "",
        })
    return {
        "question_type": "填空题",
        "answer_card": {
            "correct_answer": _strip_display_delimiters(correct),
            "student_answer": gr.get("student_answer", ""),
            "is_equivalent": gr.get("is_correct", gr.get("ok")),
            "confidence": gr.get("quick_compare_confidence", gr.get("confidence")),
        },
        "sections": sections,
        "final_answer": {},
        "meta": {"source": "standard_solution_view"},
    }


def build_solution_problem_view(
    solution: dict[str, Any],
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gr = grading_result or {}
    structured = _resolve_structured_for_view(solution, "解答题", gr, default_kind="reasoning")
    sections = _structured_to_sections(structured, "reasoning")
    if not sections:
        sections = _legacy_sections(_solution_text(solution), title="步骤化推导", kind="reasoning")
    return {
        "question_type": "解答题",
        "answer_card": {
            "score": gr.get("total"),
            "total_score": gr.get("total_score") or solution.get("total_score"),
        },
        "sections": sections,
        "final_answer": _extract_final_answer(solution, "解答题"),
        "meta": {"source": "standard_solution_view"},
    }


def build_proof_solution_view(
    solution: dict[str, Any],
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured = _resolve_structured_for_view(solution, "证明题", grading_result, default_kind="proof_chain")
    sections = _structured_to_sections(structured, "proof_chain")
    if not sections:
        sections = _legacy_sections(_solution_text(solution), title="逻辑链", kind="proof_chain")
    if sections and sections[0].get("title") != "证明目标":
        first_text = _plain_text(solution.get("proof_goal") or "要证明题设命题成立。")
        sections.insert(0, {
            "title": "证明目标",
            "kind": "proof_goal",
            "blocks": [{"type": "text", "content": first_text}],
            "conclusion": "",
        })
    conclusion = _extract_final_answer(solution, "证明题")
    if not conclusion:
        for section in reversed(sections):
            text = str(section.get("conclusion") or "").strip()
            if text:
                conclusion = {"type": "text", "content": text}
                break
    conclusion_text = str((conclusion or {}).get("content") or "")
    explicit_done = any(marker in conclusion_text or marker in _solution_text(solution) for marker in ("得证", "证毕", "命题成立", "原命题成立"))
    return {
        "question_type": "证明题",
        "answer_card": {"proof_status": "命题成立" if explicit_done else "证明过程"},
        "sections": sections,
        "final_answer": conclusion if conclusion else {"type": "text", "content": "结论见上述证明过程。"},
        "meta": {"source": "standard_solution_view"},
    }


def build_generic_solution_view(
    solution: dict[str, Any],
    question_type: str,
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured = _resolve_structured_for_view(solution, question_type, grading_result, default_kind="reasoning")
    sections = _structured_to_sections(structured, "reasoning")
    if not sections:
        sections = _legacy_sections(_solution_text(solution), title="标准解答", kind="reasoning")
    return {
        "question_type": question_type,
        "answer_card": {},
        "sections": sections,
        "final_answer": _extract_final_answer(solution, question_type),
        "meta": {"source": "standard_solution_view"},
    }


def _norm_for_compare(value: Any) -> str:
    s = str(value or "")
    s = re.sub(r"\\\(|\\\)|\$\$|\$|\\\[|\\\]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.strip("。；;，,：:")


def _similar_text(a: Any, b: Any) -> bool:
    aa, bb = _norm_for_compare(a), _norm_for_compare(b)
    if not aa or not bb:
        return False
    if aa in bb or bb in aa:
        return True
    return False


# ---------------------------------------------------------------------------
# P55: Raw TeX detection, repair, and compilation for solution text blocks
# ---------------------------------------------------------------------------

# P55-hotfix: Feature flag — default OFF because compile_text_block_to_math_blocks
# can catastrophically fragment text into single-character blocks.
ENABLE_SOLUTION_PROOF_MATH_COMPILER = _flag_enabled(
    "ENABLE_SOLUTION_PROOF_MATH_COMPILER", default=False
)


def is_compiled_view_safe(original_view: dict[str, Any], compiled_view: dict[str, Any]) -> bool:
    """P55-hotfix: Integrity guard — detect if compilation destroyed content."""
    import unicodedata

    def _count_cjk(d: dict) -> int:
        text = ""
        for sec in d.get("sections", []):
            for b in sec.get("blocks", []):
                text += str(b.get("content", ""))
            text += str(sec.get("conclusion", ""))
        fa = d.get("final_answer", "")
        if isinstance(fa, dict):
            text += str(fa.get("content", ""))
        elif isinstance(fa, str):
            text += fa
        return sum(1 for ch in text if unicodedata.category(ch).startswith("Lo"))

    def _total_text_len(d: dict) -> int:
        text = ""
        for sec in d.get("sections", []):
            for b in sec.get("blocks", []):
                text += str(b.get("content", ""))
            text += str(sec.get("conclusion", ""))
        fa = d.get("final_answer", "")
        if isinstance(fa, dict):
            text += str(fa.get("content", ""))
        elif isinstance(fa, str):
            text += fa
        return len(text)

    def _count_short_text_blocks(d: dict) -> tuple[int, int]:
        """Returns (short_count, total_text_count) for text blocks with len <= 2."""
        short = 0
        total = 0
        for sec in d.get("sections", []):
            for b in sec.get("blocks", []):
                if b.get("type") == "text":
                    total += 1
                    if len(str(b.get("content", "")).strip()) <= 2:
                        short += 1
        return short, total

    def _has_orphan_symbol_blocks(d: dict) -> int:
        """Count blocks that are just orphan symbols."""
        orphans = {"()", "(", ")", ".", "。", "步", "骤", "=", "+", "-"}
        count = 0
        for sec in d.get("sections", []):
            for b in sec.get("blocks", []):
                if b.get("type") == "text" and str(b.get("content", "")).strip() in orphans:
                    count += 1
        return count

    # 1. CJK retention
    orig_cjk = _count_cjk(original_view)
    comp_cjk = _count_cjk(compiled_view)
    if orig_cjk >= 20 and comp_cjk / max(orig_cjk, 1) < 0.85:
        return False

    # 2. Total text length retention
    orig_len = _total_text_len(original_view)
    comp_len = _total_text_len(compiled_view)
    if orig_len >= 100 and comp_len / max(orig_len, 1) < 0.70:
        return False

    # 3. Fragmentation: too many very short text blocks
    short_count, total_text = _count_short_text_blocks(compiled_view)
    if short_count > 20:
        return False
    if total_text > 0 and short_count / total_text > 0.50:
        return False

    # 4. Orphan symbol detection
    if _has_orphan_symbol_blocks(compiled_view) > 5:
        return False

    # 5. Section count explosion
    orig_sections = len(original_view.get("sections", []))
    comp_sections = len(compiled_view.get("sections", []))
    if orig_sections > 0 and comp_sections > orig_sections * 3:
        return False

    # 6. Empty content detection
    if orig_cjk > 0 and comp_cjk == 0:
        return False

    return True


def choose_safe_compiled_view(original_view: dict[str, Any], compiled_view: dict[str, Any]) -> dict[str, Any]:
    """P55-hotfix: Return compiled view only if it passes integrity check."""
    if is_compiled_view_safe(original_view, compiled_view):
        return compiled_view
    return original_view

# Patterns that indicate raw TeX outside math delimiters
_RAW_TEX_OUTSIDE_PATTERNS = [
    r'\\frac\b', r'\\dfrac\b', r'\\tfrac\b', r'\\binom\b',
    r'\\int\b', r'\\iint\b', r'\\oint\b',
    r'\\sum\b', r'\\prod\b', r'\\lim\b',
    r'\\ln\b', r'\\log\b', r'\\sin\b', r'\\cos\b', r'\\tan\b',
    r'\\sec\b', r'\\csc\b', r'\\cot\b',
    r'\\arcsin\b', r'\\arccos\b', r'\\arctan\b',
    r'\\max\b', r'\\min\b',
    r'\\Rightarrow\b', r'\\Leftarrow\b', r'\\rightarrow\b', r'\\leftarrow\b',
    r'\\left\b', r'\\right\b',
    r'\\begin\s*\{', r'\\end\s*\{',
    r'\\mathrm\s*\{', r'\\mathbf\s*\{', r'\\mathbb\s*\{', r'\\mathcal\s*\{',
    r'\\text\s*\{', r'\\displaystyle\b',
    r'\\sqrt\b', r'\\overline\b', r'\\underline\b',
    r'\\partial\b', r'\\nabla\b', r'\\infty\b',
    r'\\alpha\b', r'\\beta\b', r'\\gamma\b', r'\\delta\b', r'\\epsilon\b',
    r'\\theta\b', r'\\lambda\b', r'\\mu\b', r'\\pi\b', r'\\sigma\b',
    r'\\phi\b', r'\\omega\b',
    r'\\leq?\b', r'\\geq?\b', r'\\neq?\b', r'\\approx\b', r'\\equiv\b',
    r'\\perp\b',
    r'\\pm\b', r'\\mp\b', r'\\times\b', r'\\cdot\b', r'\\circ\b',
    r'\\subset\b', r'\\subseteq\b', r'\\cup\b', r'\\cap\b',
    r'\\forall\b', r'\\exists\b',
    # Bare tokens without backslash
    r'(?<![\\a-zA-Z])int_', r'(?<![\\a-zA-Z])frac\s*\{', r'(?<![\\a-zA-Z])dfrac\s*\{',
    r'(?<![\\a-zA-Z])Rightarrow\b', r'(?<![\\a-zA-Z])rightarrow\b',
    r'@@MATH\d+@@',
]
_RAW_TEX_RE_OUTSIDE = re.compile('|'.join(_RAW_TEX_OUTSIDE_PATTERNS))


def contains_raw_tex_outside_math(text: str) -> bool:
    """Detect raw TeX commands outside \\( ... \\), \\[ ... \\], $...$."""
    s = str(text or "")
    if not s.strip():
        return False
    # Strip existing math delimiters to avoid false positives
    stripped = re.sub(r'\\\((?:[^)]|\\.)*\\\)', '', s, flags=re.S)
    stripped = re.sub(r'\\\[(?:[^\]]|\\.)*\\\]', '', stripped, flags=re.S)
    stripped = re.sub(r'\$\$(.*?)\$\$', '', stripped, flags=re.S)
    stripped = re.sub(r'\$[^$]+\$', '', stripped)
    return bool(_RAW_TEX_RE_OUTSIDE.search(stripped))


# Tokens that should get a backslash prefix when found bare in formula fragments
_BARE_LATEX_TOKEN_MAP = {
    'frac': r'\frac', 'dfrac': r'\dfrac', 'tfrac': r'\tfrac',
    'binom': r'\binom', 'sqrt': r'\sqrt',
    'int': r'\int', 'iint': r'\iint', 'oint': r'\oint',
    'sum': r'\sum', 'prod': r'\prod', 'lim': r'\lim',
    'ln': r'\ln', 'log': r'\log',
    'sin': r'\sin', 'cos': r'\cos', 'tan': r'\tan',
    'sec': r'\sec', 'csc': r'\csc', 'cot': r'\cot',
    'arcsin': r'\arcsin', 'arccos': r'\arccos', 'arctan': r'\arctan',
    'max': r'\max', 'min': r'\min',
    'Rightarrow': r'\Rightarrow', 'Leftarrow': r'\Leftarrow',
    'rightarrow': r'\rightarrow', 'leftarrow': r'\leftarrow',
    'partial': r'\partial', 'nabla': r'\nabla', 'infty': r'\infty',
    'alpha': r'\alpha', 'beta': r'\beta', 'gamma': r'\gamma',
    'delta': r'\delta', 'epsilon': r'\epsilon', 'theta': r'\theta',
    'lambda': r'\lambda', 'mu': r'\mu', 'pi': r'\pi',
    'sigma': r'\sigma', 'phi': r'\phi', 'omega': r'\omega',
    'leq': r'\leq', 'geq': r'\geq', 'neq': r'\neq',
    'le': r'\le', 'ge': r'\ge', 'ne': r'\ne',
    'perp': r'\perp',
    'pm': r'\pm', 'mp': r'\mp', 'times': r'\times',
    'cdot': r'\cdot', 'circ': r'\circ',
    'subset': r'\subset', 'subseteq': r'\subseteq',
    'cup': r'\cup', r'cap': r'\cap', 'emptyset': r'\emptyset',
    'forall': r'\forall', 'exists': r'\exists',
    'mathrm': r'\mathrm', 'mathbf': r'\mathbf', 'mathbb': r'\mathbb',
    'text': r'\text', 'quad': r'\quad', 'qquad': r'\qquad',
    'begin': r'\begin', 'end': r'\end',
    'left': r'\left', 'right': r'\right',
    'displaystyle': r'\displaystyle',
}

# Only match tokens that are clearly bare LaTeX (not English words in context)
# Requires: token preceded by non-alpha/non-backslash, followed by non-alpha or end
_BARE_TOKEN_RE = re.compile(
    r'(?<![\\a-zA-Z])(' + '|'.join(re.escape(k) for k in _BARE_LATEX_TOKEN_MAP) + r')(?=[^a-zA-Z]|$)'
)

# Tokens that are safe to auto-repair (won't false-positive on English)
_SAFE_BARE_TOKENS = {
    'frac', 'dfrac', 'tfrac', 'binom', 'sqrt',
    'int', 'iint', 'oint', 'sum', 'prod', 'lim',
    'ln', 'log', 'sin', 'cos', 'tan', 'sec', 'csc', 'cot',
    'arcsin', 'arccos', 'arctan',
    'max', 'min',
    'Rightarrow', 'Leftarrow', 'rightarrow', 'leftarrow',
    'partial', 'nabla', 'infty',
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta',
    'lambda', 'mu', 'pi', 'sigma', 'phi', 'omega',
    'leq', 'geq', 'neq', 'le', 'ge', 'ne',
    'perp',
    'pm', 'mp', 'times', 'cdot', 'circ',
    'subset', 'subseteq', 'cup', 'cap', 'emptyset',
    'forall', 'exists',
    'mathrm', 'mathbf', 'mathbb', 'mathcal',
    'begin', 'end', 'left', 'right', 'displaystyle',
}

_SAFE_BARE_TOKEN_RE = re.compile(
    r'(?<![\\a-zA-Z])(' + '|'.join(re.escape(k) for k in _SAFE_BARE_TOKENS) + r')(?=[^a-zA-Z]|$)'
)


def repair_missing_latex_backslashes_in_formula(fragment: str) -> str:
    """Fix bare LaTeX tokens in a formula fragment. NOT for entire Chinese paragraphs."""
    if not fragment or not isinstance(fragment, str):
        return fragment

    def _replace(m):
        token = m.group(1)
        return _BARE_LATEX_TOKEN_MAP.get(token, m.group(0))

    return _SAFE_BARE_TOKEN_RE.sub(_replace, fragment)


def normalize_integral_differentials(text: str) -> str:
    """Fix dxdy → dx\\,dy in formula fragments."""
    if not text or not isinstance(text, str):
        return text
    return re.sub(r'\b(d[a-z])(d[a-z])\b', lambda m: f'{m.group(1)}\\,{m.group(2)}', text)


def normalize_broken_formula_delimiters(fragment: str) -> str:
    """Fix broken math delimiters in formula fragments. NOT for entire Chinese paragraphs."""
    if not fragment or not isinstance(fragment, str):
        return fragment
    s = fragment
    # \\displaystyle\\(...\\) → \\(...\\)
    s = re.sub(r'\\displaystyle\s*\\\(', r'\\(', s)
    # \\displaystyle frac → frac (strip displaystyle prefix)
    s = re.sub(r'\\displaystyle\s+(?=\\[a-zA-Z])', '', s)
    # Stray $$ (not paired display math)
    if s.count('$$') % 2 != 0:
        s = s.replace('$$', '')
    # Mixed delimiters: \\( ... $ or $ ... \\)
    s = re.sub(r'\\\(\s*([^)]*?)\s*\$', r'\\(\1\\)', s)
    s = re.sub(r'\$\s*([^$]*?)\s*\\\)', r'\\(\1\\)', s)
    # Orphan \\left / \\right → keep plain parens
    s = re.sub(r'\\left\s*([(\[{])', r'\1', s)
    s = re.sub(r'\\right\s*([)\]}])', r'\1', s)
    # Fix double bar: || dt → |\\,dt  (e.g., \\ln|x-t|| dt → \\ln|x-t|\\,dt)
    s = re.sub(r'\|\|\s*(d[a-z])\b', r'|\\,\1', s)
    # dt/dx/du at end of integral expression → \\,dt/\\,dx/\\,du
    s = re.sub(r'(?<=\w)\s+(d[a-z])\b(?=\s*[,.，。;；]?\s*$)', r'\\,\1', s)
    return s


_PLACEHOLDER_RE = re.compile(r'@@MATH\d+@@')


def _clean_text_string(text: str) -> str:
    """Clean a text string: remove placeholders, repair bare tokens."""
    if not text or not isinstance(text, str):
        return text or ""
    s = _PLACEHOLDER_RE.sub('', text)
    s = repair_missing_latex_backslashes_in_formula(s)
    s = normalize_integral_differentials(s)
    s = normalize_broken_formula_delimiters(s)
    return s.strip()


def _is_formula_candidate(text: str) -> bool:
    """Check if text fragment looks like a formula candidate."""
    s = str(text or "").strip()
    if not s:
        return False
    # Contains = (but not just Chinese with =)
    if re.search(r'[=≈≡≠]', s) and re.search(r'[a-zA-Z0-9_{}^()\\]', s):
        return True
    # Contains bare LaTeX tokens
    if _SAFE_BARE_TOKEN_RE.search(s):
        return True
    # Contains formula-like patterns
    formula_signals = [
        r'int_', r'frac\{', r'dfrac\{', r'\\frac', r'\\int', r'\\ln',
        r'\\max_', r'\\lim', r'f\(x\)', r"f'\\(x\\)", r'[A-Z]_[0-9]',
        r'\\Rightarrow', r'\\left', r'\\right', r'\\begin', r'\\end',
    ]
    for sig in formula_signals:
        if re.search(sig, s):
            return True
    return False


def _should_promote_to_display(text: str) -> bool:
    """Check if a formula fragment should be latex_display (not inline)."""
    return formula_requires_display_layout(text)


def compile_text_block_to_math_blocks(text: str, *, _depth: int = 0) -> list[dict[str, Any]]:
    """Split a text block into text + latex_display + degraded_code blocks.

    P55-hotfix: Non-destructive. Only splits when clear formula matches found.
    Returns original text as single block if no good matches.
    """
    if not text or not isinstance(text, str):
        return [{"type": "text", "content": text or ""}]

    # Step 1: Remove placeholders
    s = _PLACEHOLDER_RE.sub('', text)
    if not s.strip():
        return [{"type": "text", "content": ""}]

    if _depth >= 1:
        prepared = _prepare_prose_math_text(s) if _has_cjk(s) else s
        fallback = prepared or s
        return [{"type": "text", "content": fallback}] if fallback.strip() else []

    if _has_cjk(s) and contains_raw_tex_outside_math(s):
        if re.search(r"\\begin\{", s):
            return normalize_text_block_math(s, _depth=_depth + 1)
        prepared = _prepare_prose_math_text(s)
        if not contains_raw_tex_outside_math(prepared):
            return [{"type": "text", "content": prepared or s}]
        # Fall through to the conservative raw-TeX splitter.
    elif _has_cjk(s) and not re.search(r"\$\$|\\begin\{", s):
        prepared = _prepare_prose_math_text(s)
        return [{"type": "text", "content": prepared or s}]

    # Display math / environments must use the full derivation splitter, not regex fragments.
    if re.search(r"\$\$|\\begin\{", s):
        return normalize_text_block_math(s, _depth=_depth + 1)

    # Step 2: Quick check — if no raw TeX, return as-is
    if not contains_raw_tex_outside_math(s):
        return [{"type": "text", "content": s}]

    # Step 3: Try to split into formula + non-formula segments
    blocks: list[dict[str, Any]] = []
    _split_and_compile_part(s, blocks)

    # Step 4: Safety check — if we produced too many tiny blocks, discard and return original
    if len(blocks) > 1:
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        short_blocks = [b for b in text_blocks if len(str(b.get("content", "")).strip()) <= 2]
        if len(short_blocks) > 5 or (text_blocks and len(short_blocks) / len(text_blocks) > 0.5):
            # Too fragmented — return original text unchanged
            return [{"type": "text", "content": text}]

    # Step 5: Filter empty blocks; never keep CJK inside latex_display
    blocks = _latex_display_blocks_without_cjk(
        [b for b in blocks if str(b.get("content", "")).strip()]
    )

    return blocks if blocks else [{"type": "text", "content": text}]


def _split_and_compile_part(text: str, blocks: list[dict[str, Any]]):
    """Split a text part containing raw TeX into text + formula blocks.

    P55-hotfix: Non-destructive — only extract clear formula matches (min 5 chars).
    If no good match found, return original text as-is.
    """
    MIN_FORMULA_LEN = 5

    # Only match clear formula patterns — NOT single characters
    formula_pattern = re.compile(
        r'('
        r'(?:int_[0-9a-zA-Z^]+\s*[0-9a-zA-Z^,()\s]*)'  # int_0^1 ...
        r'|(?:d?frac\{[^}]*\}\{[^}]*\})'  # frac{1}{x} / dfrac{1}{x}
        r'|(?:\\(?:frac|int|sum|lim|ln|sin|cos|max|min|Rightarrow|Leftarrow)\s*\{?[^,，。;；\n]{2,})'  # \frac{...} etc
        r'|(?:\\(?:left|right|begin|end)\s*[({\[][^,，。;；\n]{2,})'  # \left( ... \end{
        r'|(?:[A-Za-z_]\([^)]*\)\s*=\s*[^,，。;；\n]{2,})'  # f(x)=...
        r'|(?:[A-Z]_[0-9a-zA-Z]+\s*=\s*[^,，。;；\n]{2,})'  # A_1=..., I_1=...
        r')'
    )

    last_end = 0
    found_any = False
    for m in formula_pattern.finditer(text):
        formula = m.group(1).strip()
        cjk_tail = ""
        cjk_match = re.search(r"[\u4e00-\u9fff].*$", formula)
        if cjk_match:
            cjk_tail = formula[cjk_match.start():].strip()
            formula = formula[:cjk_match.start()].rstrip()
        if len(formula) < MIN_FORMULA_LEN:
            continue
        found_any = True
        start, end = m.start(), m.end()
        # Text before this formula
        before = text[last_end:start]
        if before.strip():
            blocks.append({"type": "text", "content": before})
        elif before:  # preserve whitespace
            blocks.append({"type": "text", "content": before})

        # Repair the formula
        repaired = repair_missing_latex_backslashes_in_formula(formula)
        repaired = normalize_integral_differentials(repaired)
        repaired = normalize_broken_formula_delimiters(repaired)

        view_block = _view_block_for_latex(repaired)
        if view_block.get("type") == "latex_display" and _has_cjk(repaired):
            blocks.append({"type": "text", "content": _wrap_inline_math_fragments(repaired)})
        else:
            blocks.append(view_block)
        if cjk_tail:
            blocks.append({"type": "text", "content": cjk_tail})
        last_end = end

    if found_any:
        # Text after last formula
        after = text[last_end:]
        if after.strip():
            # Don't recurse — just keep remaining text as-is
            blocks.append({"type": "text", "content": after})
    else:
        # No formula pattern matched — return original text unchanged (non-destructive)
        blocks.append({"type": "text", "content": text})


def _strip_raw_tex_keep_chinese(text: str) -> str:
    """Strip raw TeX commands but keep Chinese text. Last resort."""
    s = str(text or "")
    # Remove common raw TeX commands
    s = re.sub(r'\\(?:frac|dfrac|int|sum|lim|ln|sin|cos|max|min|Rightarrow|left|right|begin|end|displaystyle)\b[^，。;；\n]*', '', s)
    s = re.sub(r'@@MATH\d+@@', '', s)
    # Clean up leftover whitespace
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s


def clean_latex_block(block: dict[str, Any]) -> dict[str, Any]:
    """Clean a latex_display/latex_inline/equation_group block."""
    if not isinstance(block, dict):
        return block
    b = dict(block)
    content = b.get("content", "")
    if isinstance(content, str):
        content = _PLACEHOLDER_RE.sub('', content)
        b["content"] = content
    # Also clean items for equation_group/derivation_chain
    items = b.get("items")
    if isinstance(items, list):
        b["items"] = [_PLACEHOLDER_RE.sub('', str(it)) for it in items]
    return b


def compile_math_blocks_for_standard_solution_view(view: dict[str, Any]) -> dict[str, Any]:
    """P55: Compile raw text blocks into clean structured blocks. Deep copies input."""
    import copy
    v = copy.deepcopy(view)

    for section in v.get("sections", []):
        new_blocks: list[dict[str, Any]] = []
        for block in section.get("blocks", []):
            btype = block.get("type", "")
            if btype == "text":
                content = str(block.get("content") or "")
                new_blocks.extend(compile_text_block_to_math_blocks(content))
            else:
                new_blocks.append(clean_latex_block(block))
        section["blocks"] = _latex_display_blocks_without_cjk(new_blocks)

        # Clean conclusion
        conclusion = section.get("conclusion")
        if isinstance(conclusion, str) and conclusion.strip():
            section["conclusion"] = _clean_text_string(conclusion)

    # Clean final_answer — but don't turn empty dict into {"content": ""}
    fa = v.get("final_answer")
    if isinstance(fa, str) and fa.strip():
        v["final_answer"] = _clean_text_string(fa)
    elif isinstance(fa, dict):
        content = fa.get("content", "")
        if isinstance(content, str) and content.strip():
            fa["content"] = _clean_text_string(content)

    return v


def normalize_section_meta(section: dict[str, Any]) -> dict[str, Any]:
    sec = dict(section or {})
    title = re.sub(r"^(步骤\d+[：:]\s*){2,}", lambda m: m.group(1), str(sec.get("title") or "解答").strip())
    sec["title"] = title
    if "最终" in title or title in {"结论", "最终结论"} or sec.get("kind") == "conclusion":
        sec["goal"] = ""
        sec["reason"] = ""
    for key in ("goal", "reason", "conclusion"):
        value = _plain_text(sec.get(key, ""))
        if key in {"goal", "reason"} and (("最终" in title) or title in {"结论", "最终结论"} or sec.get("kind") == "conclusion"):
            sec[key] = ""
            continue
        if value and title and value.startswith(title):
            value = value[len(title):].lstrip(" ：:，,。")
        if key == "goal":
            value = _strip_step_title_prefix(value)
            if _goal_redundant_with_title(value, title):
                value = ""
        if value and key == "reason":
            value = _strip_reason_display_tail(
                _prepare_prose_math_text(repair_derivation_text_block(value))
            )
        elif value and key == "goal":
            value = _prepare_prose_math_text(repair_derivation_text_block(value))
        sec[key] = value
    return sec


def _append_normalized_blocks(out: list[dict[str, Any]], normalized: Any) -> None:
    if isinstance(normalized, list):
        for item in normalized:
            if isinstance(item, dict) and item:
                out.append(item)
    elif isinstance(normalized, dict) and normalized:
        out.append(normalized)


def _normalize_block_list(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Coalesce prose + latex_display chains before demoting display math to $...$ text.
    blocks = consolidate_view_blocks(list(blocks or []))
    out: list[dict[str, Any]] = []
    for block in blocks:
        normalized = _normalize_solution_block(block)
        if isinstance(normalized, list):
            for item in normalized:
                if isinstance(item, dict) and item.get("type") == "text":
                    out.extend(normalize_text_block_math(str(item.get("content") or "")))
                elif isinstance(item, dict):
                    out.append(item)
        elif isinstance(normalized, dict):
            if normalized.get("type") == "text":
                out.extend(normalize_text_block_math(str(normalized.get("content") or "")))
            else:
                out.append(normalized)
    return consolidate_view_blocks(out)


def _block_text(block: dict[str, Any]) -> str:
    if not isinstance(block, dict):
        return ""
    if block.get("type") in {"equation_group", "derivation_chain"}:
        return " ".join(str(i) for i in block.get("items") or [])
    if block.get("type") == "cases":
        return str(block.get("lhs") or "") + " " + " ".join(str(r) for r in block.get("rows") or [])
    return str(block.get("content") or "")


def _is_labeled_meta_block(text: str) -> bool:
    t = str(text or "").strip()
    return any(
        t.startswith(prefix)
        for prefix in ("推导目标", "推导理由", "本步结论", "结论：", "目标：", "依据：")
    )


def _is_derivation_label_only_block(text: str) -> bool:
    t = re.sub(r"[：:\s]+$", "", str(text or "").strip())
    if _DERIVATION_CONCLUSION_RE.match(t) or t == "因此本步得到结论":
        return True
    return t in {
        "关键变形为",
        "中间公式为",
        "非齐次项",
        "推导目标",
        "推导理由",
    }


def _latex_display_to_inline_span(latex: str) -> str | None:
    s = normalize_differential_tokens(_strip_display_delimiters(str(latex or ""))).strip()
    if not s or formula_requires_display_layout(s):
        return None
    return f"${s}$"


def _text_is_inline_math_only(content: str) -> bool:
    s = str(content or "").strip()
    return bool(re.fullmatch(r"\$[^$\n]+\$", s))


_DERIVATION_META_LABELS = frozenset({
    "关键变形为",
    "中间公式为",
    "因此本步得到结论",
    "已知条件可写为",
    "推导目标",
    "推导理由",
    "本步结论",
})


def _text_is_derivation_meta_label(content: str) -> bool:
    t = re.sub(r"[：:\s]+$", "", str(content or "").strip())
    return t in _DERIVATION_META_LABELS or any(t.endswith(label) for label in _DERIVATION_META_LABELS)


def merge_inline_structured_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge text + inline latex + text chains into one text block with $...$ spans."""
    if not blocks:
        return blocks
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(blocks):
        cur = blocks[i]
        if not isinstance(cur, dict) or cur.get("type") != "text":
            out.append(cur)
            i += 1
            continue
        merged = str(cur.get("content") or "")
        if _text_is_derivation_meta_label(merged):
            out.append(cur)
            i += 1
            continue
        j = i + 1
        changed = False
        while j < len(blocks):
            nxt = blocks[j]
            if not isinstance(nxt, dict):
                break
            if _block_is_inline_latex(nxt):
                span = _inline_latex_block_to_span(nxt)
                if not span:
                    break
                merged += span
                changed = True
                j += 1
                continue
            if nxt.get("type") == "text":
                nxt_content = str(nxt.get("content") or "")
                if _text_is_derivation_meta_label(nxt_content):
                    break
                if changed or _text_is_inline_math_only(nxt_content):
                    merged += nxt_content
                    changed = True
                    j += 1
                    continue
                break
            break
        if changed:
            if _has_cjk(merged):
                content = _prepare_prose_math_text(merged)
            else:
                content = prepare_grading_math_for_render(merged)
            out.append({"type": "text", "content": content or merged})
            i = j
        else:
            out.append(cur)
            i += 1
    return out


def _coalesce_prose_inline_math_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible alias for merge_inline_structured_blocks."""
    return merge_inline_structured_blocks(blocks)


def _latex_plain_for_compare(latex: str) -> str:
    s = str(latex or "")
    s = re.sub(r"\\begin\{[a-zA-Z*]+\}|\\end\{[a-zA-Z*]+\}", " ", s)
    s = re.sub(r"\\\\|&=?", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[{}$\\]", "", s)
    return _norm_for_compare(s)


def _block_similar_to_latex(text: str, latex: str) -> bool:
    t = _norm_for_compare(_plain_text(text))
    l = _latex_plain_for_compare(latex)
    if not t or not l:
        return False
    if t in l or l in t:
        return True
    if len(t) >= 40 and t[: min(80, len(t))] in l:
        return True
    return False


def _cjk_for_overlap(text: str) -> str:
    s = _plain_text(text)
    s = re.sub(r"\$[^$]*\$|\\\([^)]*\\\)|\\\[[\s\S]*?\\\]", "", s)
    return "".join(re.findall(r"[\u4e00-\u9fff]+", s))


def _text_block_covers_reason(reason: str, block_text: str) -> bool:
    if _similar_text(reason, block_text):
        return True
    rn = _cjk_for_overlap(reason)
    bn = _cjk_for_overlap(block_text)
    return bool(rn and bn and len(rn) >= 10 and (rn in bn or bn in rn))


def _text_block_repeats_reason(reason: str, block_text: str) -> bool:
    rn = _cjk_for_overlap(reason)
    bn = _cjk_for_overlap(block_text)
    if not rn or not bn or min(len(rn), len(bn)) < 10:
        return False
    if rn in bn or bn in rn:
        return True
    try:
        from difflib import SequenceMatcher

        return SequenceMatcher(None, rn, bn).ratio() >= 0.82
    except Exception:
        common = sum(1 for ch in set(rn) if ch in bn)
        return common / max(1, len(set(rn))) >= 0.82


def _blocks_substantially_overlap_body(blocks: list[Any], body: str) -> bool:
    combined = "\n".join(
        _plain_text(_block_text(b) if isinstance(b, dict) else str(b))
        for b in blocks or []
        if b
    )
    bn = _norm_for_compare(combined)
    dn = _norm_for_compare(body)
    if not dn:
        return bool(bn)
    if bn == dn or dn in bn:
        return True
    if len(dn) >= 30 and bn and dn[: min(60, len(dn))] in bn:
        return True
    return False


def dedupe_section_content(view: dict[str, Any]) -> dict[str, Any]:
    v = dict(view or {})
    sections = []
    last_section_conclusion = ""
    for raw_sec in v.get("sections") or []:
        raw_conclusion = _plain_text(raw_sec.get("conclusion", "")) if isinstance(raw_sec, dict) else ""
        sec = normalize_section_meta(raw_sec)
        last_section_conclusion = raw_conclusion
        blocks = list(sec.get("blocks") or [])
        reason = str(sec.get("reason") or "").strip()
        goal = str(sec.get("goal") or "").strip()
        if _goal_redundant_with_title(goal, sec.get("title", "")):
            sec["goal"] = ""
            goal = ""
        if blocks and reason:
            cleaned_reason = _strip_reason_display_tail(reason)
            if any(
                _text_block_covers_reason(cleaned_reason, _block_text(b))
                for b in blocks
                if isinstance(b, dict) and b.get("type") != "text"
            ):
                cleaned_reason = ""
            sec["reason"] = cleaned_reason
            reason = cleaned_reason
        cleaned: list[dict[str, Any]] = []
        for idx, b in enumerate(blocks):
            if b.get("type") == "text":
                content = str(b.get("content") or "")
                if reason:
                    content = _strip_meta_echo_from_text(content, reason)
                    if content and _text_block_repeats_reason(reason, content):
                        continue
                    if content and _similar_text(content, reason):
                        continue
                if goal:
                    content = _strip_meta_echo_from_text(content, goal)
                    if content and _similar_text(content, goal):
                        continue
                content = _dedupe_paragraphs_in_text(content)
                if not content.strip() or _is_derivation_label_only_block(content):
                    continue
                if idx + 1 < len(blocks) and blocks[idx + 1].get("type") == "latex_display":
                    if _block_similar_to_latex(content, str(blocks[idx + 1].get("content") or "")):
                        continue
                b = dict(b)
                b["content"] = content
            cleaned.append(b)
        blocks = cleaned
        if sec.get("conclusion") and blocks:
            conc = str(sec.get("conclusion") or "")
            display_blocks = [
                b for b in blocks
                if isinstance(b, dict) and b.get("type") in {"latex_display", "equation_group", "cases", "derivation_chain"}
            ]
            if display_blocks and any(_similar_text(conc, _block_text(b)) for b in display_blocks):
                sec["conclusion"] = ""
            elif _similar_text(conc, _block_text(blocks[-1])) and not _is_labeled_meta_block(_block_text(blocks[-1])):
                sec["conclusion"] = ""
        # P55: Deduplicate consecutive identical latex_display blocks
        deduped: list[dict[str, Any]] = []
        for b in blocks:
            if (deduped
                    and b.get("type") in {"latex_display", "equation_group"}
                    and deduped[-1].get("type") == b.get("type")
                    and _norm_for_compare(deduped[-1].get("content")) == _norm_for_compare(b.get("content"))):
                continue
            deduped.append(b)
        sec["blocks"] = _dedupe_derivation_conclusion_blocks(deduped)
        sections.append(sec)
    v["sections"] = sections
    final_answer = v.get("final_answer") or {}
    final_content = final_answer.get("content") if isinstance(final_answer, dict) else final_answer
    answer_card = v.get("answer_card") if isinstance(v.get("answer_card"), dict) else {}
    correct_choice = str(answer_card.get("correct_answer") or answer_card.get("correct_option") or "").strip().upper()
    if correct_choice and _coerce_question_type(v.get("question_type")) == "选择题":
        normalized_final = _norm_for_compare(final_content).upper()
        if normalized_final in {correct_choice, f"故选{correct_choice}", f"正确选项为{correct_choice}"}:
            v["final_answer"] = {}
            final_content = ""
    if final_content and sections:
        last = sections[-1]
        haystacks = [last_section_conclusion, last.get("conclusion", "")] + [
            _block_text(b) for b in last.get("blocks") or []
        ]
        if any(_similar_text(final_content, h) for h in haystacks):
            v["final_answer"] = {}
    return v


def normalize_standard_solution_view(view: dict[str, Any]) -> dict[str, Any]:
    """Normalize standard solution view before rendering without changing canonical data."""
    v = dict(view or {})
    v["question_type"] = _coerce_question_type(v.get("question_type"))
    normalized_sections = []
    for section in v.get("sections") or []:
        sec = normalize_section_meta(section)
        sec["blocks"] = _normalize_block_list(sec.get("blocks") or [])
        normalized_sections.append(sec)
    v["sections"] = normalized_sections
    final_answer = v.get("final_answer")
    if isinstance(final_answer, dict):
        fa = _normalize_solution_block(final_answer)
        v["final_answer"] = fa or {}
    elif isinstance(final_answer, str) and final_answer.strip():
        v["final_answer"] = {"type": "text", "content": _plain_text(_normalize_math_tokens(final_answer))}
    else:
        v["final_answer"] = {}
    v = dedupe_section_content(v)
    if ENABLE_SOLUTION_PROOF_MATH_COMPILER or _view_has_raw_tex_in_text_blocks(v):
        compiled = compile_math_blocks_for_standard_solution_view(v)
        v = choose_safe_compiled_view(v, compiled)
    return dedupe_section_content(v)


def _view_has_raw_tex_in_text_blocks(view: dict[str, Any]) -> bool:
    """True when any text block still contains TeX outside math delimiters."""
    for section in view.get("sections") or []:
        for block in section.get("blocks") or []:
            if block.get("type") == "text" and contains_raw_tex_outside_math(str(block.get("content") or "")):
                return True
    return False


def _normalize_structured_block_types(structured: dict[str, Any] | None) -> dict[str, Any] | None:
    """Map legacy structured block types to the grading view contract."""
    if not isinstance(structured, dict):
        return structured
    out = dict(structured)
    steps: list[Any] = []
    for step in out.get("steps") or []:
        if not isinstance(step, dict):
            steps.append(step)
            continue
        s = dict(step)
        blocks: list[dict[str, Any]] = []
        for block in s.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            b = dict(block)
            btype = str(b.get("type") or "text")
            if btype == "latex":
                if str(b.get("display") or "inline").lower() == "block":
                    b["type"] = "latex_display"
            elif btype in {"latex_inline", "inline_math"}:
                content = str(b.get("content") or "").strip()
                b = {
                    "type": "latex",
                    "display": "inline",
                    "content": content,
                }
            blocks.append(b)
        s["blocks"] = blocks
        steps.append(s)
    out["steps"] = steps
    fa = out.get("final_answer")
    if isinstance(fa, dict) and fa.get("type") == "latex":
        fa = dict(fa)
        if str(fa.get("display") or "inline").lower() == "block":
            fa["type"] = "latex_display"
        out["final_answer"] = fa
    return out


def _legacy_display_title(question_type: str | None) -> str:
    q_type = _coerce_question_type(question_type)
    return {
        "选择题": "选项解析",
        "填空题": "填空推导",
        "证明题": "证明过程",
        "解答题": "解答",
        "计算题": "解答",
    }.get(q_type, "标准解答")


def _structured_richness(structured: Any) -> int:
    """Score structured payloads so the fullest derivation wins (3289443-style)."""
    if not isinstance(structured, dict) or not _has_structured_steps(structured):
        return 0
    score = 0
    for step in structured.get("steps") or []:
        if not isinstance(step, dict):
            continue
        score += 10
        score += len(_step_body_text(step)) // 24
        score += len(step.get("blocks") or []) * 2
        if str(step.get("goal") or "").strip():
            score += 6
        if str(step.get("reason") or step.get("justification") or "").strip():
            score += 6
        if str(step.get("conclusion") or "").strip():
            score += 4
    return score


def _pick_richest_structured(*candidates: Any) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0
    for candidate in candidates:
        score = _structured_richness(candidate)
        if score > best_score:
            best_score = score
            best = candidate
    return best if isinstance(best, dict) else None


def _try_build_structured_from_legacy_text(
    solution: dict[str, Any] | None,
    question_type: str | None = None,
) -> dict[str, Any] | None:
    """Same legacy→structured path 解答题 used at 3289443 (from_legacy_text + polish)."""
    from services.solution_legacy_repair import repair_legacy_solution_text

    sol = dict(solution or {})
    text = repair_legacy_solution_text(_solution_text(sol))
    if not text.strip() or is_empty_shell(text):
        return None
    if not (solution_has_substance(text) or _has_step_markers(text)):
        return None
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    if q_type == "选择题" and len(text.strip()) <= 80 and not _has_step_markers(text):
        return None
    if q_type == "填空题":
        short_answer = extract_fill_final_answer(sol) or ""
        if (
            short_answer
            and not _has_step_markers(text)
            and len(text.strip()) <= len(short_answer) + 48
        ):
            return None
    try:
        from latex_utils import from_legacy_text
        from services.solution_polisher import polish_solution

        polished = polish_solution(
            from_legacy_text(text, title=_legacy_display_title(q_type))
        )
        return polished if _has_structured_steps(polished) else None
    except Exception:
        return None


def ensure_structured_for_display(
    solution: dict[str, Any] | None,
    question_type: str | None = None,
) -> dict[str, Any]:
    """Sanitize and pick the richest _structured steps before building the student view."""
    import copy

    sol = copy.deepcopy(dict(solution or {}))
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    default_kind = {
        "选择题": "reasoning",
        "填空题": "calculation",
        "证明题": "proof_chain",
    }.get(q_type, "reasoning")

    chosen = _pick_richest_structured(
        sol.get("_structured"),
        build_question_type_structured_solution(sol, q_type),
        _try_build_structured_from_legacy_text(sol, q_type),
        _legacy_steps_to_structured(sol, default_kind=default_kind),
    )
    if chosen:
        sol["_structured"] = _normalize_structured_block_types(
            _ensure_body_markdown_blocks(chosen)
        )
    return sanitize_solution_before_display(sol)


def build_answer_only_view(
    solution: dict[str, Any] | None,
    question_type: str,
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sol = dict(solution or {})
    gr = grading_result or {}
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    correct = gr.get("correct_option") or gr.get("correct_answer") or sol.get("final_answer") or _solution_text(sol)
    if q_type == "选择题":
        correct = _choice_letter(str(correct))
        final = {"type": "text", "content": f"故选 \\({correct}\\)。"} if correct else {}
        card = {"correct_answer": correct, "student_answer": gr.get("student_answer", ""), "is_correct": gr.get("is_correct")}
    elif q_type == "填空题":
        correct = _strip_display_delimiters(correct)
        final = {"type": "latex_display", "content": correct} if correct else {}
        card = {"correct_answer": correct, "student_answer": gr.get("student_answer", ""), "is_equivalent": gr.get("is_correct", gr.get("ok"))}
    elif q_type == "证明题":
        final = _extract_final_answer(sol, q_type) or {"type": "text", "content": "结论见上述证明过程。"}
        card = {"proof_status": "证明过程"}
    else:
        final = _extract_final_answer(sol, q_type)
        card = {"score": gr.get("total"), "total_score": gr.get("total_score") or sol.get("total_score")}
    sections = []
    if correct:
        sections.append({
            "title": "标准解答",
            "kind": "answer_only",
            "blocks": [{"type": "text", "content": "详细解析暂未生成。"}],
            "conclusion": "",
        })
    return normalize_standard_solution_view({
        "question_type": q_type,
        "answer_card": card,
        "sections": sections,
        "final_answer": final,
        "meta": {"source": "answer_only_view"},
    })


def build_standard_solution_view(
    solution: dict[str, Any] | None,
    question_type: str,
    grading_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a student-facing standard solution view, routed only by question type.

    P55: Pipeline is ensure structured → normalize → [compile if flag/raw TeX] → dedupe.
    """
    sol = ensure_structured_for_display(solution, question_type)
    existing = sol.get("standard_solution_view")
    if isinstance(existing, dict):
        return dedupe_section_content(normalize_standard_solution_view(existing))
    q_type = _coerce_question_type(question_type or sol.get("question_type"))
    if q_type == "选择题":
        view = build_choice_solution_view(sol, grading_result)
    elif q_type == "填空题":
        view = build_fill_solution_view(sol, grading_result)
    elif q_type == "证明题":
        view = build_proof_solution_view(sol, grading_result)
    elif q_type in {"解答题", "计算题"}:
        view = build_solution_problem_view(sol, grading_result)
    else:
        view = build_generic_solution_view(sol, q_type, grading_result)
    return dedupe_section_content(normalize_standard_solution_view(view))


def normalize_standard_solution(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize standard solution dict into a stable contract."""
    raw = dict(raw or {})
    q_type = _coerce_question_type(raw.get("question_type") or raw.get("type"))
    structured = raw.get("_structured") or None
    if not _has_structured_steps(structured):
        structured = build_question_type_structured_solution(raw, q_type)
    normalized = {
        "success": bool(raw.get("success", True)),
        "question_type": q_type if q_type != "未知题型" else raw.get("question_type"),
        "standard_answer": raw.get("standard_answer", raw.get("answer", "")),
        "total_score": int(raw.get("total_score", 10)),
        "steps": raw.get("steps") or [],
        "_structured": structured,
        "_canonical_ir": raw.get("_canonical_ir") or None,
        "_solution_ir": (
            raw.get("_solution_ir")
            or raw.get("solution_ir")
            or raw.get("_canonical_ir")
            or None
        ),
        "_ai_unverified": bool(raw.get("_ai_unverified", True)),
        "_ai_consistency_warning": bool(raw.get("_ai_consistency_warning")),
        "_solver_fallback": bool(raw.get("_solver_fallback")),
        "_solution_status": raw.get("_solution_status"),
        "standard_solution_status": raw.get("standard_solution_status"),
        "standard_solution_error": raw.get("standard_solution_error", ""),
        "_quality_report": raw.get("_quality_report"),
        "_should_regenerate": bool(raw.get("_should_regenerate", False)),
    }
    return _apply_solution_ir_shadow(normalized)


def solution_has_substance(text_or_dict: str | dict[str, Any] | None) -> bool:
    """Check if a solution has enough content to be useful."""
    if isinstance(text_or_dict, dict):
        text = str(text_or_dict.get("standard_answer") or text_or_dict.get("answer") or "")
        # Also check _structured for steps content
        structured = text_or_dict.get("_structured")
        if isinstance(structured, dict):
            for step in structured.get("steps") or []:
                for block in (step.get("blocks") or []):
                    if str(block.get("content", "")).strip():
                        return True
    else:
        text = str(text_or_dict or "")
    text = text.strip()
    if len(text) >= 80:
        meta_markers = ["## 关键知识点", "## 常见错误", "## 薄弱知识点"]
        if all(m in text for m in meta_markers) and "步骤" not in text:
            return False
        return True
    return False


def is_empty_shell(text: str | None) -> bool:
    """Detect LLM metadata-only output (headings without step derivation)."""
    s = str(text or "").strip()
    if not s:
        return True
    markers = ["关键知识点", "易错提示", "常见错误", "薄弱知识点", "考查知识点"]
    found = sum(1 for m in markers if m in s)
    return found >= 2 and "步骤" not in s and len(s) < 500


def _step_body_text(step: dict[str, Any]) -> str:
    if not isinstance(step, dict):
        return ""
    for key in ("body_markdown", "derivation_markdown", "explanation"):
        value = str(step.get(key) or "").strip()
        if value:
            return value
    parts: list[str] = []
    for block in step.get("blocks") or []:
        if isinstance(block, dict) and block.get("content"):
            parts.append(str(block.get("content")))
    return "\n\n".join(parts).strip()


def _ensure_body_markdown_blocks(structured: dict[str, Any] | None) -> dict[str, Any] | None:
    """Make body_markdown render first while preserving legacy blocks."""
    if not isinstance(structured, dict):
        return structured
    structured = dict(structured)
    steps = []
    for raw_step in structured.get("steps") or []:
        if not isinstance(raw_step, dict):
            steps.append(raw_step)
            continue
        step = _normalize_step_derivation_meta(dict(raw_step))
        body = str(
            step.get("body_markdown")
            or step.get("derivation_markdown")
            or step.get("explanation")
            or ""
        ).strip()
        if body:
            step.setdefault("body_markdown", body)
            step.setdefault("derivation_markdown", body)
            blocks = list(step.get("blocks") or [])
            body_already_present = any(
                isinstance(block, dict)
                and block.get("_source") == "body_markdown"
                for block in blocks
            )
            if not body_already_present and not _blocks_substantially_overlap_body(blocks, body):
                parsed_body = _blocks_from_text(body)
                body_blocks = [
                    {**b, "_source": "body_markdown"}
                    for b in parsed_body
                    if isinstance(b, dict) and b
                ] or [{
                    "type": "text",
                    "content": body,
                    "display": "inline",
                    "_source": "body_markdown",
                }]
                step["blocks"] = body_blocks + [
                    b for b in blocks
                    if not (isinstance(b, dict) and b.get("_source") == "body_markdown")
                ]
            elif body and blocks:
                step["blocks"] = [
                    b for b in blocks
                    if not (isinstance(b, dict) and b.get("_source") == "body_markdown")
                ]
        steps.append(step)
    structured["steps"] = steps
    return structured


# ═══════════════════════════════════════════════
#  P32/P36: Display sanitization helpers
# ═══════════════════════════════════════════════

def _repair_text_field(text: str) -> str:
    """P32.1/P32.2/P32.2.1/P36: Apply all LaTeX repairs to a single text field."""
    from services.solution_legacy_repair import (
        _repair_mathrm_differential,
        _repair_corrupted_greek_commands,
        _repair_unicode_greek_commands,
        _repair_bare_mathrm_differential,
        _normalize_unicode_greek_math_symbols,
        _repair_bare_differential_in_math_context,
        _repair_backslash_bare_differential,
        _repair_consecutive_bare_differential,
    )
    s = _unescape_json_newlines(str(text or ""))
    s = _repair_mathrm_differential(s)
    s = _repair_corrupted_greek_commands(s)
    s = _repair_unicode_greek_commands(s)
    s = _repair_bare_mathrm_differential(s)
    s = _normalize_unicode_greek_math_symbols(s)
    s = _repair_bare_differential_in_math_context(s)
    s = _repair_backslash_bare_differential(s)
    s = _repair_consecutive_bare_differential(s)
    return s


def _repair_formula_latex_field(text: str) -> str:
    """P32.2/P32.2.1/P36: Apply repairs to a formula.latex field."""
    from services.solution_legacy_repair import (
        _repair_mathrm_differential,
        _repair_corrupted_greek_commands,
        _repair_unicode_greek_commands,
        _repair_bare_mathrm_differential,
        _normalize_unicode_greek_in_latex,
        _repair_bare_differential_in_math_context,
        _repair_backslash_bare_differential,
        _repair_consecutive_bare_differential,
    )
    s = str(text or "")
    s = _repair_mathrm_differential(s)
    s = _repair_corrupted_greek_commands(s)
    s = _repair_unicode_greek_commands(s)
    s = _repair_bare_mathrm_differential(s)
    s = _normalize_unicode_greek_in_latex(s)
    s = _repair_bare_differential_in_math_context(s)
    s = _repair_backslash_bare_differential(s)
    s = _repair_consecutive_bare_differential(s)
    return s


def _repair_text_in_dict(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Apply repairs to specific keys in a dict (in-place)."""
    for key in keys:
        if key in d and isinstance(d[key], str) and d[key]:
            d[key] = _repair_text_field(d[key])
    return d


def sanitize_structured_solution_for_render(solution: dict[str, Any]) -> dict[str, Any]:
    """P32.1: Recursively sanitize all display fields in a structured solution."""
    import copy
    s = copy.deepcopy(dict(solution or {}))

    for key in ("standard_answer", "answer"):
        if isinstance(s.get(key), str) and s[key]:
            s[key] = _repair_text_field(s[key])

    _STEP_TEXT_KEYS = (
        "content", "body", "body_markdown", "derivation_markdown",
        "explanation", "conclusion",
    )
    for step in s.get("steps") or []:
        if not isinstance(step, dict):
            continue
        _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
        for block in step.get("blocks") or []:
            if isinstance(block, dict) and block.get("content"):
                block["content"] = _repair_text_field(block["content"])

    structured = s.get("_structured")
    if isinstance(structured, dict):
        for step in structured.get("steps") or []:
            if not isinstance(step, dict):
                continue
            _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
            for block in step.get("blocks") or []:
                if isinstance(block, dict) and block.get("content"):
                    block["content"] = _repair_text_field(block["content"])
            for formula in step.get("formulas") or []:
                if isinstance(formula, dict) and formula.get("latex"):
                    formula["latex"] = _repair_formula_latex_field(formula["latex"])
        fa = structured.get("final_answer")
        if isinstance(fa, dict) and fa.get("content"):
            fa["content"] = _repair_text_field(fa["content"])

    for block in s.get("blocks") or []:
        if isinstance(block, dict) and block.get("content"):
            block["content"] = _repair_text_field(block["content"])

    return s


def sanitize_solution_before_display(solution: dict[str, Any]) -> dict[str, Any]:
    """P36+P41: Final sanitization pass before rendering standard solution."""
    import copy
    from services.solution_legacy_repair import (
        _repair_backslash_bare_differential,
        _repair_consecutive_bare_differential,
    )

    s = sanitize_structured_solution_for_render(solution)

    def _p36_repair(text: str) -> str:
        t = str(text or "")
        t = _repair_backslash_bare_differential(t)
        t = _repair_consecutive_bare_differential(t)
        return t

    def _p36_repair_formula(text: str) -> str:
        from services.solution_legacy_repair import _normalize_unicode_greek_in_latex
        t = str(text or "")
        t = _repair_backslash_bare_differential(t)
        t = _repair_consecutive_bare_differential(t)
        t = _normalize_unicode_greek_in_latex(t)
        return t

    # P41: derivation formula canonicalization
    def _p41_repair_latex_display(text: str) -> str:
        from latex_utils import (
            normalize_derivation_formula_block, repair_aligned_environment,
            repair_cases_environment, repair_latex_row_spacing_markers,
            repair_bare_fraction_commands, repair_probability_formula_fragments,
        )
        t = str(text or "")
        t = _p36_repair_formula(t)
        # P41.4: Fix bare fractions first
        t = repair_bare_fraction_commands(t)
        # P41.4: Fix probability formula fragments (orphan !, dx lines, etc.)
        t = repair_probability_formula_fragments(t)
        # P41.3: Fix row spacing markers
        t = repair_latex_row_spacing_markers(t)
        # P41.3: Repair cases environments
        if r'\begin{cases}' in t:
            t = repair_cases_environment(t)
        # P41.2: Repair aligned environments before normalization
        if r'\begin{aligned}' in t or r'\begin{align}' in t:
            t = repair_aligned_environment(t)
        t = normalize_derivation_formula_block(t)
        return t

    def _p41_repair_text(text: str) -> str:
        from latex_utils import normalize_inline_math_text
        t = str(text or "")
        t = _p36_repair(t)
        t = normalize_inline_math_text(t)
        return t

    for key in ("standard_answer", "answer"):
        if isinstance(s.get(key), str) and s[key]:
            s[key] = _p36_repair(s[key])

    fa = s.get("final_answer")
    if isinstance(fa, dict) and fa.get("content"):
        fa["content"] = _p36_repair(fa["content"])
    elif isinstance(fa, str) and fa:
        s["final_answer"] = _p36_repair(fa)

    _STEP_TEXT_KEYS = (
        "content", "body", "body_markdown", "derivation_markdown",
        "explanation", "conclusion",
    )
    def _p41_repair_block_content(block: dict) -> None:
        """P41: Apply appropriate repair based on block type."""
        content = block.get("content")
        if not content:
            return
        btype = block.get("type", "")
        display = block.get("display", "")
        if btype == "latex_display" or (btype == "latex" and display == "block"):
            block["content"] = _p41_repair_latex_display(content)
        elif btype == "text":
            block["content"] = _p41_repair_text(content)
        else:
            block["content"] = _p36_repair(content)

    for step_list_key in ("steps",):
        for step in s.get(step_list_key) or []:
            if not isinstance(step, dict):
                continue
            _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
            for block in step.get("blocks") or []:
                if isinstance(block, dict) and block.get("content"):
                    _p41_repair_block_content(block)
            for formula in step.get("formulas") or []:
                if isinstance(formula, dict) and formula.get("latex"):
                    formula["latex"] = _p41_repair_latex_display(formula["latex"])

    structured = s.get("_structured")
    if isinstance(structured, dict):
        for step in structured.get("steps") or []:
            if not isinstance(step, dict):
                continue
            _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
            for block in step.get("blocks") or []:
                if isinstance(block, dict) and block.get("content"):
                    _p41_repair_block_content(block)
            for formula in step.get("formulas") or []:
                if isinstance(formula, dict) and formula.get("latex"):
                    formula["latex"] = _p41_repair_latex_display(formula["latex"])
        sfa = structured.get("final_answer")
        if isinstance(sfa, dict) and sfa.get("content"):
            sfa["content"] = _p41_repair_text(sfa["content"])

    for block in s.get("blocks") or []:
        if isinstance(block, dict) and block.get("content"):
            _p41_repair_block_content(block)
    for formula in s.get("formulas") or []:
        if isinstance(formula, dict) and formula.get("latex"):
            formula["latex"] = _p41_repair_latex_display(formula["latex"])

    return s


def normalize_solution_for_render(solution: dict[str, Any] | None) -> dict[str, Any]:
    """P19-3: Normalize + quarantine broken LaTeX before rendering."""
    from services.solution_quality import (
        structured_has_broken_latex, structured_has_real_content,
        has_broken_latex_fragments, solution_quality_report,
    )
    from services.solution_legacy_repair import repair_legacy_solution_text

    s = _apply_solution_ir_shadow(dict(solution or {}))
    raw_text = str(s.get("standard_answer") or s.get("answer") or "")
    repaired = repair_legacy_solution_text(raw_text)
    s["standard_answer"] = repaired
    if isinstance(s.get("_structured"), dict):
        s["_structured"] = _ensure_body_markdown_blocks(s.get("_structured"))

    if repaired and has_broken_latex_fragments(repaired):
        report = _failed_compiled_report("not_renderable")
        report["issues"] = ["not_renderable"]
        return _maybe_quarantine_solution_for_render(
            s,
            raw_text=raw_text or repaired,
            report=report,
        )

    # Check existing _structured — drop if broken or empty
    structured = s.get("_structured")
    if structured is not None:
        if structured_has_broken_latex(structured):
            s["_structured"] = None
            s["_structured_dropped_reason"] = "broken_latex"
        elif not structured_has_real_content(structured):
            s["_structured"] = None
            s["_structured_dropped_reason"] = "empty_structured"
        else:
            report = solution_quality_report(s)
            return _maybe_quarantine_solution_for_render(
                s,
                raw_text=raw_text or repaired,
                report=report,
            )

    # Build structured from repaired text
    if not repaired.strip():
        s["standard_solution_status"] = "pending"
        s["_structured"] = None
        return s

    try:
        from latex_utils import from_legacy_text
        from services.solution_polisher import polish_solution
        structured = from_legacy_text(repaired)
        structured = polish_solution(structured)
        structured = _ensure_body_markdown_blocks(structured)

        if structured_has_broken_latex(structured):
            s["standard_solution_status"] = "failed"
            s["standard_solution_error"] = "结构化解答中仍含损坏 LaTeX。"
            s["_structured"] = None
        else:
            s["_structured"] = structured
            s["standard_solution_status"] = "ready"

    except Exception as exc:
        s["standard_solution_status"] = "failed"
        s["standard_solution_error"] = str(exc)
        s["_structured"] = None

    report = solution_quality_report(s)
    return _maybe_quarantine_solution_for_render(
        s,
        raw_text=raw_text or repaired,
        report=report,
    )


def normalize_canonical_entry(entry: dict[str, Any] | None,
                               question: dict[str, Any] | None = None) -> dict[str, Any]:
    """P19-5: Invalidate old-format or incomplete canonical cache entries.

    Drops structured and canonical_ir from entries saved before the
    current format version OR with incomplete/broken solutions.
    """
    from services.solution_quality import solution_quality_report
    entry = dict(entry or {})

    if entry.get("format_version") != SOLUTION_FORMAT_VERSION:
        entry.pop("structured", None)
        entry.pop("canonical_ir", None)
        entry.pop("solution_ir", None)
        entry["invalidated_reason"] = "old_solution_format"
        return entry

    solution_like = {
        "standard_answer": entry.get("standard_answer") or "",
        "_structured": entry.get("structured"),
        "_canonical_ir": entry.get("canonical_ir"),
        "_solution_ir": entry.get("solution_ir") or entry.get("canonical_ir"),
    }

    report = solution_quality_report(solution_like, question)
    entry["quality_report"] = report
    if not report.get("ok", False):
        entry.pop("structured", None)
        entry.pop("canonical_ir", None)
        entry.pop("solution_ir", None)
        entry["invalidated"] = True
        entry["invalidated_reason"] = "quality_gate_failed"

    return entry


def canonical_entry_to_solution(
    entry: dict[str, Any] | None,
    question: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt a canonical pool entry into the standard solution contract."""
    normalized = normalize_canonical_entry(entry, question=question)
    canonical_ir = normalized.get("canonical_ir")
    solution_ir = normalized.get("solution_ir") or canonical_ir
    return {
        "success": True,
        "standard_answer": normalized.get("standard_answer", ""),
        "total_score": (question or {}).get("score", 10),
        "steps": normalized.get("steps") or [],
        "_structured": normalized.get("structured"),
        "_canonical_ir": canonical_ir,
        "_solution_ir": solution_ir,
        "_ai_unverified": not bool(normalized.get("reviewed", False)),
        "standard_solution_source": "canonical",
        "_canonical_entry": normalized,
    }


def normalize_error_record(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize error record dict into a stable contract."""
    raw = dict(raw or {})
    def _i(v, d=0):
        try: return int(float(v))
        except: return d
    def _f(v, d=0.0):
        try: return float(v)
        except: return d
    return {
        **raw,
        "question_id": str(raw.get("question_id") or raw.get("qid") or ""),
        "student_answer": str(raw.get("student_answer") or ""),
        "score": _i(raw.get("score")),
        "max_score": _i(raw.get("max_score"), 10),
        "is_correct": bool(raw.get("is_correct", False)),
        "error_type": str(raw.get("error_type") or "unknown"),
        "root_cause": str(raw.get("root_cause") or ""),
        "weak_points": list(raw.get("weak_points") or []),
        "recommendations": list(raw.get("recommendations") or []),
        "knowledge_points": list(raw.get("knowledge_points") or []),
        "common_mistakes": list(raw.get("common_mistakes") or []),
        "engine": str(raw.get("engine") or "unknown"),
        "confidence": _f(raw.get("confidence"), 1.0),
        "timestamp": str(raw.get("timestamp") or ""),
        "question_preview": str(raw.get("question_preview") or ""),
        "wrong_reason_short": str(raw.get("wrong_reason_short") or ""),
        "semantic_tags": list(raw.get("semantic_tags") or []),
        "status": str(raw.get("status") or "active"),
        "wrong_count": int(raw.get("wrong_count") or 1),
    }
