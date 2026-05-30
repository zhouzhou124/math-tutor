"""Grading result & solution adapters — unified data contracts.

All grading engines produce result dicts through normalize_grading_result()
so the renderer, error notebook, and persistence layers see the same shape.
"""

from __future__ import annotations
import html
import os
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


def _quarantine_failed_legacy_solution(
    s: dict[str, Any],
    *,
    raw_text: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Clear unsafe legacy answer while preserving escaped debug preview."""
    s["standard_solution_source"] = "failed"
    s["standard_solution_status"] = "failed"
    issues = "、".join(str(i) for i in (report.get("issues") or [])[:4]) or "quality_gate_failed"
    s["standard_solution_error"] = f"标准解答质量门禁未通过：{issues}。"
    s["_failed_quality_report"] = report
    s["_failed_raw_preview"] = html.escape(str(raw_text or "")[:500], quote=True)
    s["standard_answer"] = ""
    s["_structured"] = None
    s["steps"] = []
    return s


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

    return {
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


def normalize_standard_solution(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize standard solution dict into a stable contract."""
    raw = dict(raw or {})
    normalized = {
        "success": bool(raw.get("success", True)),
        "standard_answer": raw.get("standard_answer", raw.get("answer", "")),
        "total_score": int(raw.get("total_score", 10)),
        "steps": raw.get("steps") or [],
        "_structured": raw.get("_structured") or None,
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
        step = dict(raw_step)
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
            if not body_already_present:
                step["blocks"] = [
                    {
                        "type": "text",
                        "content": body,
                        "display": "inline",
                        "_source": "body_markdown",
                    }
                ] + blocks
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
    s = str(text or "")
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
    """P36: Final sanitization pass before rendering standard solution."""
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
    for step_list_key in ("steps",):
        for step in s.get(step_list_key) or []:
            if not isinstance(step, dict):
                continue
            _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
            for block in step.get("blocks") or []:
                if isinstance(block, dict) and block.get("content"):
                    block["content"] = _p36_repair(block["content"])
            for formula in step.get("formulas") or []:
                if isinstance(formula, dict) and formula.get("latex"):
                    formula["latex"] = _p36_repair_formula(formula["latex"])

    structured = s.get("_structured")
    if isinstance(structured, dict):
        for step in structured.get("steps") or []:
            if not isinstance(step, dict):
                continue
            _repair_text_in_dict(step, list(_STEP_TEXT_KEYS))
            for block in step.get("blocks") or []:
                if isinstance(block, dict) and block.get("content"):
                    block["content"] = _p36_repair(block["content"])
            for formula in step.get("formulas") or []:
                if isinstance(formula, dict) and formula.get("latex"):
                    formula["latex"] = _p36_repair_formula(formula["latex"])
        sfa = structured.get("final_answer")
        if isinstance(sfa, dict) and sfa.get("content"):
            sfa["content"] = _p36_repair(sfa["content"])

    for block in s.get("blocks") or []:
        if isinstance(block, dict) and block.get("content"):
            block["content"] = _p36_repair(block["content"])
    for formula in s.get("formulas") or []:
        if isinstance(formula, dict) and formula.get("latex"):
            formula["latex"] = _p36_repair_formula(formula["latex"])

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

    # If raw text is still broken after repair, fail fast
    if repaired and has_broken_latex_fragments(repaired):
        report = _failed_compiled_report("not_renderable")
        report["issues"] = ["not_renderable"]
        s["_quality_report"] = report
        s["_should_regenerate"] = True
        return _quarantine_failed_legacy_solution(s, raw_text=raw_text or repaired, report=report)

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
            # Clean structured: keep it, but still attach the quality report below.
            report = solution_quality_report(s)
            s["_quality_report"] = report
            s["_should_regenerate"] = bool(report.get("should_regenerate"))
            if not report.get("renderable", False):
                return _quarantine_failed_legacy_solution(s, raw_text=raw_text or repaired, report=report)
            elif not report.get("ok", False):
                s["standard_solution_status"] = "incomplete"
                issues = "、".join(report.get("issues", [])[:4]) or "quality_gate_failed"
                s["standard_solution_error"] = f"标准解答生成不完整：{issues}。"
            elif not s.get("standard_solution_status"):
                s["standard_solution_status"] = "ready"
            return s

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
    s["_quality_report"] = report
    s["_should_regenerate"] = bool(report.get("should_regenerate"))
    if not report.get("renderable", False):
        return _quarantine_failed_legacy_solution(s, raw_text=raw_text or repaired, report=report)
    elif not report.get("ok", False):
        s["standard_solution_status"] = "incomplete"
        issues = "、".join(report.get("issues", [])[:4]) or "quality_gate_failed"
        s["standard_solution_error"] = f"标准解答生成不完整：{issues}。"

    return s


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
