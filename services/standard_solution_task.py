"""Shared standard-solution task layer for grading and retry flows."""

from __future__ import annotations

import html
import time
from typing import Any, Callable, Literal


StandardSolutionTaskResult = dict[str, Any]
TaskSource = Literal["grading", "retry"]


def _noop_status():
    class _Status:
        def write(self, *_args, **_kwargs):
            return None

        def update(self, *_args, **_kwargs):
            return None

    return _Status()


def _raw_solution_text(solution: dict[str, Any] | None) -> str:
    if not isinstance(solution, dict):
        return ""
    return str(solution.get("standard_answer") or solution.get("answer") or "")


def _issues_from_report(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return []
    return [str(item) for item in (report.get("issues") or []) if str(item)]


def _base_report(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "renderable": False,
        "complete": False,
        "detailed": False,
        "covers_requirements": False,
        "logically_plausible": False,
        "issues": [reason],
        "should_regenerate": True,
    }


def _cached_solution(
    selected_q: dict[str, Any],
) -> dict[str, Any] | None:
    from services.grading_adapter import (
        normalize_canonical_entry,
        normalize_standard_solution,
        normalize_solution_for_render,
        solution_has_substance,
    )
    from services.solution_quality import solution_quality_report

    pool = selected_q.get("canonical_solutions") or []
    for entry in pool:
        normalized = normalize_canonical_entry(entry, question=selected_q)
        if not solution_has_substance(normalized):
            continue
        sol = normalize_standard_solution({
            "standard_answer": normalized.get("standard_answer", ""),
            "total_score": selected_q.get("score", 10),
            "steps": normalized.get("steps", []),
            "_structured": normalized.get("structured"),
            "_canonical_ir": normalized.get("canonical_ir"),
            "_solution_ir": normalized.get("solution_ir") or normalized.get("canonical_ir"),
            "_ai_unverified": not normalized.get("reviewed", False),
        })
        sol = normalize_solution_for_render(sol)
        report = solution_quality_report(sol, selected_q)
        if report.get("ok"):
            sol["_quality_report"] = report
            sol["_should_regenerate"] = False
            sol["standard_solution_status"] = "ready"
            sol["standard_solution_error"] = ""
            sol["_cache_hit"] = True
            return sol

    cached = str(selected_q.get("standard_answer") or "").strip()
    if cached and solution_has_substance(cached):
        sol = normalize_standard_solution({
            "standard_answer": cached,
            "total_score": selected_q.get("score", 10),
            "steps": selected_q.get("solution_steps", []),
            "_ai_unverified": False,
        })
        sol = normalize_solution_for_render(sol)
        report = solution_quality_report(sol, selected_q)
        if report.get("ok"):
            sol["_quality_report"] = report
            sol["_should_regenerate"] = False
            sol["standard_solution_status"] = "ready"
            sol["standard_solution_error"] = ""
            sol["_cache_hit"] = True
            return sol
    return None


def _normalize_task_result(
    solution: dict[str, Any] | None,
    *,
    selected_q: dict[str, Any],
    raw_text: str,
    attempt_id: str | int | None,
    source: TaskSource,
    started_at: float,
    cache_hit: bool = False,
) -> StandardSolutionTaskResult:
    from services.grading_adapter import normalize_solution_for_render
    from services.solution_quality import solution_quality_report

    elapsed_ms = int((time.time() - started_at) * 1000)
    pre_report = solution.get("_quality_report") if isinstance(solution, dict) else None
    sol = normalize_solution_for_render(dict(solution or {}))
    existing_report = sol.get("_quality_report")
    compiled_report = sol.get("_compiled_quality_report")
    if isinstance(pre_report, dict) and pre_report.get("ok"):
        report = pre_report
    elif isinstance(existing_report, dict) and existing_report.get("ok"):
        report = existing_report
    elif (
        sol.get("_used_compiled_standard_answer")
        and isinstance(compiled_report, dict)
        and compiled_report.get("ok")
    ):
        report = compiled_report
    else:
        report = solution_quality_report(sol, selected_q)
    sol["_quality_report"] = report
    sol["_should_regenerate"] = bool(report.get("should_regenerate"))
    sol["should_regenerate"] = bool(report.get("should_regenerate"))
    sol["attempt_id"] = attempt_id
    sol["source"] = source
    sol["standard_solution_task_source"] = source
    sol["standard_solution_task_ms"] = elapsed_ms
    sol["standard_solution_cache_hit"] = bool(cache_hit)
    sol["standard_solution_issues"] = _issues_from_report(report)

    sol.setdefault("standard_solution_source", "legacy")
    sol.setdefault("_used_compiled_standard_answer", False)
    sol.setdefault("_compiled_standard_answer", sol.get("_compiled_standard_answer"))
    sol.setdefault("_compiled_quality_report", sol.get("_compiled_quality_report"))
    sol.setdefault("_compiled_fallback_reason", sol.get("_compiled_fallback_reason", ""))

    if report.get("ok"):
        sol["standard_solution_status"] = "ready"
        sol["standard_solution_error"] = ""
        return sol

    status = "failed" if not report.get("renderable", False) else "incomplete"
    issues = ", ".join(_issues_from_report(report)[:6]) or "quality_gate_failed"
    debug_text = raw_text or _raw_solution_text(solution) or _raw_solution_text(sol)
    sol["standard_solution_status"] = status
    sol["standard_solution_source"] = "failed"
    sol["standard_solution_error"] = (
        f"standard solution quality gate failed: {issues}"
    )
    sol["standard_answer"] = ""
    sol["steps"] = []
    sol["_structured"] = None
    sol["_debug_raw_standard_answer"] = html.escape(debug_text[:4000], quote=True)
    sol["_failed_raw_preview"] = html.escape(debug_text[:500], quote=True)
    sol["_failed_quality_report"] = report
    return sol


def build_standard_solution_task(
    question: str,
    *,
    selected_q: dict[str, Any] | None = None,
    ocr_data: dict[str, Any] | None = None,
    client: Any = None,
    status: Any = None,
    model: str | None = None,
    state: dict[str, Any] | None = None,
    force: bool = False,
    force_expansion: bool = False,
    attempt_id: str | int | None = None,
    source: TaskSource = "grading",
    builder: Callable[..., dict[str, Any]] | None = None,
) -> StandardSolutionTaskResult:
    """Build a standard solution through one shared task contract.

    ``builder`` is intentionally injectable so the UI can keep its current
    generator while both grading and retry share cache, quality and quarantine
    semantics here.
    """
    started_at = time.time()
    selected_q = selected_q or {}
    ocr_data = ocr_data or {}
    status = status or _noop_status()

    if not force:
        cached = _cached_solution(selected_q)
        if cached is not None:
            return _normalize_task_result(
                cached,
                selected_q=selected_q,
                raw_text=_raw_solution_text(cached),
                attempt_id=attempt_id,
                source=source,
                started_at=started_at,
                cache_hit=True,
            )

    if builder is None:
        return _normalize_task_result(
            {
                "success": True,
                "standard_answer": "",
                "total_score": selected_q.get("score", 10),
                "steps": [],
                "_quality_report": _base_report("missing_solution_builder"),
            },
            selected_q=selected_q,
            raw_text="",
            attempt_id=attempt_id,
            source=source,
            started_at=started_at,
            cache_hit=False,
        )

    solution = builder(
        question,
        ocr_data,
        selected_q,
        client,
        status,
        force_expansion=force_expansion,
        _state=state,
        model=model,
    )
    return _normalize_task_result(
        solution,
        selected_q=selected_q,
        raw_text=_raw_solution_text(solution),
        attempt_id=attempt_id,
        source=source,
        started_at=started_at,
        cache_hit=False,
    )
