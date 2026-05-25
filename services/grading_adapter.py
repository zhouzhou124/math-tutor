"""Grading result & solution adapters — unified data contracts.

All grading engines produce result dicts through normalize_grading_result()
so the renderer, error notebook, and persistence layers see the same shape.
"""

from __future__ import annotations
from typing import Any

# P19-4/P24: increment when canonical solution schema or quality contract changes
SOLUTION_FORMAT_VERSION = "p24_solution_quality_gate"


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
    return {
        "success": bool(raw.get("success", True)),
        "standard_answer": raw.get("standard_answer", raw.get("answer", "")),
        "total_score": int(raw.get("total_score", 10)),
        "steps": raw.get("steps") or [],
        "_structured": raw.get("_structured") or None,
        "_canonical_ir": raw.get("_canonical_ir") or None,
        "_ai_unverified": bool(raw.get("_ai_unverified", True)),
        "_ai_consistency_warning": bool(raw.get("_ai_consistency_warning")),
        "_solver_fallback": bool(raw.get("_solver_fallback")),
        "_solution_status": raw.get("_solution_status"),
    }


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


def normalize_solution_for_render(solution: dict[str, Any] | None) -> dict[str, Any]:
    """P19-3: Normalize + quarantine broken LaTeX before rendering."""
    from services.solution_quality import (
        structured_has_broken_latex, structured_has_real_content,
        has_broken_latex_fragments, solution_quality_report,
    )
    from services.solution_legacy_repair import repair_legacy_solution_text

    s = dict(solution or {})
    raw_text = str(s.get("standard_answer") or s.get("answer") or "")
    repaired = repair_legacy_solution_text(raw_text)
    s["standard_answer"] = repaired

    # If raw text is still broken after repair, fail fast
    if repaired and has_broken_latex_fragments(repaired):
        s["standard_solution_status"] = "failed"
        s["standard_solution_error"] = "标准解答包含损坏的 LaTeX 片段。"
        s["_structured"] = None
        return s

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
                s["standard_solution_status"] = "failed"
                s["standard_solution_error"] = "标准解答包含无法稳定渲染的公式。"
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
        s["standard_solution_status"] = "failed"
        s["standard_solution_error"] = "标准解答包含无法稳定渲染的公式。"

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
        entry["invalidated_reason"] = "old_solution_format"
        return entry

    solution_like = {
        "standard_answer": entry.get("standard_answer") or "",
        "_structured": entry.get("structured"),
        "_canonical_ir": entry.get("canonical_ir"),
    }

    report = solution_quality_report(solution_like, question)
    entry["quality_report"] = report
    if not report.get("ok", False):
        entry.pop("structured", None)
        entry.pop("canonical_ir", None)
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
