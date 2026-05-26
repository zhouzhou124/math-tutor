#!/usr/bin/env python3
"""Evaluate CanonicalIR shadow compiler output without mutating cache."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_QUESTIONS_ROOT = ROOT / "storage" / "questions"
DEFAULT_REPORT_DIR = ROOT / "storage" / "eval_runs"
IR_KEYS = ("solution_ir", "_solution_ir", "canonical_ir", "_canonical_ir")


def _preview(value: Any, limit: int = 200) -> str:
    text = str(value or "")
    text = " ".join(text.split())
    return text[:limit]


def _entry_ir(entry: dict[str, Any]) -> dict[str, Any] | None:
    for key in IR_KEYS:
        value = entry.get(key)
        if isinstance(value, dict):
            return value
    return None


def _question_type(question: dict[str, Any]) -> str:
    return str(question.get("question_type") or question.get("type") or "")


def _matches_year(question: dict[str, Any], year: str | None) -> bool:
    if not year:
        return True
    year_s = str(year)
    for key in ("year", "exam_year", "source_year"):
        if str(question.get(key) or "") == year_s:
            return True
    haystack = " ".join(
        str(question.get(key) or "")
        for key in ("question_id", "id", "title", "source", "paper")
    )
    return year_s in haystack


def _solution_entries(question: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in question.get("canonical_solutions") or []:
        if isinstance(entry, dict):
            entries.append(entry)

    has_top_level_solution = bool(question.get("standard_answer") or _entry_ir(question))
    if has_top_level_solution:
        entries.append(question)
    return entries


def iter_solution_entries(
    questions_root: Path = DEFAULT_QUESTIONS_ROOT,
    *,
    question_type: str | None = None,
    year: str | None = None,
    limit: int | None = None,
):
    """Yield (question, entry) pairs from question JSON files."""
    emitted = 0
    for path in sorted(Path(questions_root).rglob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            question = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(question, dict):
            continue
        if question_type and _question_type(question) != question_type:
            continue
        if not _matches_year(question, year):
            continue

        for entry in _solution_entries(question):
            yield question, entry
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def _empty_report() -> dict[str, Any]:
    return {
        "ok": False,
        "renderable": False,
        "complete": False,
        "detailed": False,
        "covers_requirements": False,
        "logically_plausible": False,
        "issues": [],
        "should_regenerate": True,
    }


def _recommendation(
    *,
    has_ir: bool,
    ir_valid: bool,
    compiled_ok: bool,
    legacy_ok: bool,
) -> str:
    if has_ir and not ir_valid:
        return "invalid_ir"
    if compiled_ok and not legacy_ok:
        return "use_compiled"
    if legacy_ok:
        return "keep_legacy"
    return "regenerate"


def evaluate_solution_entry(question: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one cached solution entry without changing it."""
    from semantic_output import validate_canonical_ir
    from services.solution_markdown_compiler import compile_canonical_ir_to_markdown
    from services.solution_quality import solution_quality_report

    legacy_text = str(entry.get("standard_answer") or entry.get("answer") or "")
    legacy_report = solution_quality_report({"standard_answer": legacy_text}, question)

    ir = _entry_ir(entry)
    has_ir = isinstance(ir, dict)
    ir_valid = False
    ir_errors: list[str] = []
    compiled_report = _empty_report()
    compiled_markdown = ""
    compile_error = ""

    if has_ir:
        model, errors, _repairs = validate_canonical_ir(copy.deepcopy(ir))
        ir_errors = [str(e) for e in errors]
        ir_valid = model is not None and not errors
        if ir_valid and model is not None:
            try:
                compiled_markdown = compile_canonical_ir_to_markdown(model.model_dump())
                compiled_report = solution_quality_report({"standard_answer": compiled_markdown}, question)
            except Exception as exc:
                compile_error = f"{type(exc).__name__}: {str(exc)[:160]}"
                compiled_report["issues"] = [compile_error]

    compiled_ok = bool(compiled_report.get("ok"))
    legacy_ok = bool(legacy_report.get("ok"))
    recommendation = _recommendation(
        has_ir=has_ir,
        ir_valid=ir_valid,
        compiled_ok=compiled_ok,
        legacy_ok=legacy_ok,
    )

    return {
        "question_id": question.get("question_id") or question.get("id") or "",
        "question_type": _question_type(question),
        "has_ir": has_ir,
        "ir_valid": ir_valid,
        "ir_errors": ir_errors,
        "compile_error": compile_error,
        "compiled_renderable": bool(compiled_report.get("renderable")),
        "compiled_complete": bool(compiled_report.get("complete")),
        "compiled_ok": compiled_ok,
        "legacy_renderable": bool(legacy_report.get("renderable")),
        "legacy_complete": bool(legacy_report.get("complete")),
        "legacy_ok": legacy_ok,
        "compiled_chars": len(compiled_markdown),
        "legacy_chars": len(legacy_text),
        "compiled_preview": _preview(compiled_markdown),
        "legacy_preview": _preview(legacy_text),
        "recommendation": recommendation,
    }


def _top_reasons(counter: Counter[str], n: int = 5) -> list[dict[str, Any]]:
    return [{"reason": reason, "count": count} for reason, count in counter.most_common(n)]


def build_report(
    questions_root: Path = DEFAULT_QUESTIONS_ROOT,
    *,
    question_type: str | None = None,
    year: str | None = None,
    limit: int | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Run the dry-run shadow evaluation over matching solution entries."""
    samples = [
        evaluate_solution_entry(question, entry)
        for question, entry in iter_solution_entries(
            questions_root,
            question_type=question_type,
            year=year,
            limit=limit,
        )
    ]

    invalid_reasons: Counter[str] = Counter()
    compile_reasons: Counter[str] = Counter()
    for sample in samples:
        for reason in sample.get("ir_errors") or []:
            invalid_reasons[reason] += 1
        if sample.get("compile_error"):
            compile_reasons[sample["compile_error"]] += 1

    summary = {
        "total_entries": len(samples),
        "entries_with_ir": sum(1 for s in samples if s["has_ir"]),
        "ir_valid_count": sum(1 for s in samples if s["ir_valid"]),
        "compile_success_count": sum(
            1 for s in samples
            if s["has_ir"] and s["ir_valid"] and not s.get("compile_error")
        ),
        "compiled_renderable_count": sum(1 for s in samples if s["compiled_renderable"]),
        "compiled_complete_count": sum(1 for s in samples if s["compiled_complete"]),
        "compiled_ok_count": sum(1 for s in samples if s["compiled_ok"]),
        "legacy_ok_count": sum(1 for s in samples if s["legacy_ok"]),
        "compiled_better_count": sum(
            1 for s in samples if s["has_ir"] and s["compiled_ok"] and not s["legacy_ok"]
        ),
        "compiled_worse_count": sum(
            1 for s in samples if s["has_ir"] and s["legacy_ok"] and not s["compiled_ok"]
        ),
        "invalid_ir_reasons": _top_reasons(invalid_reasons, top_n),
        "compile_error_reasons": _top_reasons(compile_reasons, top_n),
    }
    return {
        "mode": "solution_ir_shadow_dry_run",
        "filters": {
            "limit": limit,
            "question_type": question_type,
            "year": year,
        },
        "summary": summary,
        "samples": samples,
    }


def save_report(report: dict[str, Any], report_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"solution_ir_shadow_{timestamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_summary(report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    print("Solution IR shadow evaluation")
    for key in (
        "total_entries",
        "entries_with_ir",
        "ir_valid_count",
        "compile_success_count",
        "compiled_renderable_count",
        "compiled_complete_count",
        "compiled_ok_count",
        "legacy_ok_count",
        "compiled_better_count",
        "compiled_worse_count",
    ):
        print(f"{key}: {summary.get(key, 0)}")
    for key in ("invalid_ir_reasons", "compile_error_reasons"):
        reasons = summary.get(key) or []
        if reasons:
            print(f"{key}:")
            for item in reasons:
                print(f"  {item['reason']}: {item['count']}")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run evaluation for CanonicalIR compiled standard answers."
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--type", dest="question_type", default=None)
    parser.add_argument("--year", default=None)
    parser.add_argument("--save-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        DEFAULT_QUESTIONS_ROOT,
        question_type=args.question_type,
        year=args.year,
        limit=args.limit,
    )
    print_summary(report)
    if args.save_report:
        path = save_report(report, DEFAULT_REPORT_DIR)
        print(f"report_saved: {_display_path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
