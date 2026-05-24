#!/usr/bin/env python3
"""P11 Offline Grading Evaluation & Regression Suite.

Usage:
  python scripts/eval_grading.py                  # dry-run: structure + contract checks only
  python scripts/eval_grading.py --live            # full grading pipeline (needs API keys)
  python scripts/eval_grading.py --live --verbose  # full + per-question detail

The eval dataset lives at storage/eval_dataset.json.
Regression thresholds are defined in this file (REGRESSION_GATES).

Exit 0 = all gates pass, exit 1 = gate failure or script error.
"""

import json
import sys
import time as _time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVAL_DATASET = ROOT / "storage" / "eval_dataset.json"

# ═══════════════════════════════════════════════
#  Regression gates
# ═══════════════════════════════════════════════

REGRESSION_GATES = {
    "solution_quality_avg": 80,       # average quality score >= 80
    "grading_valid_pct": 95.0,        # grading contract valid % >= 95%
    "failure_rate_max": 3.0,          # failure rate <= 3%
    "answer_latency_avg_ms_max": 20000,   # avg latency <= 20s for 解答题
    "choice_latency_avg_ms_max": 2000,    # avg latency <= 2s for 选择题
}

# ═══════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════

def load_eval_dataset():
    with open(EVAL_DATASET, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["entries"]


def load_question(qid: str) -> dict | None:
    """Find a question in the bank by question_id."""
    from database.question_db import get_question_path
    path = get_question_path(qid)
    if not path or not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_ocr_data(entry: dict, question: dict) -> dict:
    return {
        "success": True,
        "question": question.get("question", ""),
        "student_answer": entry["student_answer"],
        "math_type": question.get("math_type", "数学一"),
        "question_type": entry["question_type"],
        "knowledge_point": ", ".join(question.get("knowledge_points", [])),
        "confidence": 1.0,
        "warnings": [],
    }


# ═══════════════════════════════════════════════
#  Dry-run: structure-only checks (no LLM)
# ═══════════════════════════════════════════════

def run_dry(entries: list[dict]) -> dict:
    """Validate eval dataset structure and question bank integrity."""
    results = []
    missing_qids = []
    schema_issues = []

    for entry in entries:
        required = ["eval_id", "question_id", "question_type", "student_answer",
                     "expected_score_range"]
        for key in required:
            if key not in entry:
                schema_issues.append(f"{entry.get('eval_id', '?')}: missing {key}")

        q = load_question(entry["question_id"])
        if q is None:
            missing_qids.append(entry["question_id"])
            continue

        # Verify question_type matches
        actual_type = q.get("question_type", "")
        if actual_type and actual_type != entry["question_type"]:
            schema_issues.append(
                f"{entry['eval_id']}: type mismatch — "
                f"eval={entry['question_type']}, bank={actual_type}"
            )

        results.append({
            "eval_id": entry["eval_id"],
            "question_id": entry["question_id"],
            "status": "dry_ok",
            "has_standard_answer": bool(q.get("standard_answer")),
            "has_canonical": bool(q.get("canonical_solutions")),
            "solution_quality_score": None,
            "grading_valid": None,
            "latency_ms": 0,
        })

    return {
        "mode": "dry",
        "total": len(entries),
        "checked": len(results),
        "missing_qids": missing_qids,
        "schema_issues": schema_issues,
        "results": results,
        "gates": {},  # not applicable in dry mode
    }


# ═══════════════════════════════════════════════
#  Live: full grading pipeline (needs LLM)
# ═══════════════════════════════════════════════

def run_live(entries: list[dict], verbose: bool = False) -> dict:
    """Run the full grading pipeline on each eval entry."""
    import os
    from services.grading_orchestrator import execute_grading
    from services.solution_quality import score_solution_quality
    from services.grading_quality import validate_grading_result_contract
    from services.grading_adapter import normalize_grading_result
    from services.solution_text_tools import solution_to_text

    # ── Init LLM client ──
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        return {"error": "LLM_API_KEY not set. Set it or run without --live for dry-run."}

    from config import LLM_BASE_URL, LLM_MODEL
    from llm_client import create_client
    client = create_client(api_key=api_key, base_url=LLM_BASE_URL, protocol="openai")
    model = LLM_MODEL

    results = []
    failures = 0
    cache_hits = 0
    total_latency_ms = 0
    sq_scores = []
    gv_valids = []
    score_in_range = 0
    error_type_correct = 0
    error_type_applicable = 0

    for entry in entries:
        q = load_question(entry["question_id"])
        if q is None:
            results.append({"eval_id": entry["eval_id"], "status": "missing_question"})
            failures += 1
            continue

        ocr_data = build_ocr_data(entry, q)
        state = {}

        t0 = _time.perf_counter()

        # Build solution wrapper (mimics _build_standard_solution)
        from services.solution_service import SolutionService
        from services.grading_adapter import normalize_standard_solution

        def build_solution_fn(**kw):
            svc = SolutionService(
                client=kw.get("client", client),
                model=kw.get("model", model),
            )
            solution = svc.build(
                question=kw.get("question", q.get("question", "")),
                selected_q=kw.get("selected_q", q),
                ocr_data=kw.get("ocr_data", ocr_data),
                force_expansion=kw.get("force_expansion", False),
            )
            if solution.get("_solved_from_cache"):
                nonlocal cache_hits
                cache_hits += 1
            return solution

        try:
            result = execute_grading(
                question=q.get("question", ""),
                student_ans=entry["student_answer"],
                ocr_data=ocr_data,
                selected_q=q,
                client=client,
                model=model,
                user_id="eval_runner",
                status_callback=None,
                state=state,
                build_solution_fn=build_solution_fn,
            )
        except Exception as exc:
            results.append({
                "eval_id": entry["eval_id"],
                "status": "failed",
                "error": str(exc)[:200],
            })
            failures += 1
            continue

        elapsed_ms = int((_time.perf_counter() - t0) * 1000)
        total_latency_ms += elapsed_ms

        gr = result.get("grading_result", {}) if result else {}
        solution = result.get("standard_answer", {}) if result else {}

        # ── Collect metrics ──
        sq = score_solution_quality(solution)
        sq_scores.append(sq["score"])

        gv = validate_grading_result_contract(gr, solution.get("total_score", 10))
        gv_valids.append(gv["valid"])

        # Score range check
        actual_score = gr.get("total", 0)
        lo, hi = entry["expected_score_range"]
        if lo <= actual_score <= hi:
            score_in_range += 1

        # Error type check
        expected_et = entry.get("expected_error_type")
        if expected_et:
            error_type_applicable += 1
            actual_et = (result.get("diagnosis_result", {}) or {}).get("error_type", "")
            if expected_et in actual_et or actual_et in expected_et:
                error_type_correct += 1

        status = "ok"
        if gr.get("engine") != entry.get("expected_engine", gr.get("engine")):
            status = "engine_mismatch"
        if not gv["valid"]:
            status = "contract_invalid"

        results.append({
            "eval_id": entry["eval_id"],
            "question_id": entry["question_id"],
            "status": status,
            "engine": gr.get("engine", "?"),
            "score": actual_score,
            "expected_range": entry["expected_score_range"],
            "solution_quality_score": sq["score"],
            "grading_valid": gv["valid"],
            "latency_ms": elapsed_ms,
            "timing": result.get("_timing", {}) if result else {},
        })

        if verbose:
            _sq_label = f"Q={sq['score']}" if sq else "Q=?"
            _gv_label = "✓" if gv["valid"] else "✗"
            print(
                f"  {entry['eval_id']:12s}  {status:18s}  "
                f"engine={gr.get('engine', '?'):15s}  "
                f"score={actual_score:.0f}/{solution.get('total_score', 10):.0f}  "
                f"{elapsed_ms:5d}ms  SQ={_sq_label}  GV={_gv_label}"
            )

    n = len([r for r in results if r["status"] not in ("failed", "missing_question")])
    sq_avg = sum(sq_scores) / len(sq_scores) if sq_scores else 0
    gv_pct = sum(1 for v in gv_valids if v) / len(gv_valids) * 100 if gv_valids else 0
    latency_avg = total_latency_ms / n if n > 0 else 0
    failure_pct = failures / len(entries) * 100

    # Per-type latency
    choice_times = [r["latency_ms"] for r in results
                    if r.get("status") not in ("failed", "missing_question")
                    and entry_for_result(r, entries).get("question_type") == "选择题"]
    answer_times = [r["latency_ms"] for r in results
                    if r.get("status") not in ("failed", "missing_question")
                    and entry_for_result(r, entries).get("question_type") in ("解答题", "证明题")]

    # ── Gate evaluation ──
    gates = {
        "solution_quality_avg": {
            "value": round(sq_avg, 1),
            "threshold": REGRESSION_GATES["solution_quality_avg"],
            "pass": sq_avg >= REGRESSION_GATES["solution_quality_avg"],
        },
        "grading_valid_pct": {
            "value": round(gv_pct, 1),
            "threshold": REGRESSION_GATES["grading_valid_pct"],
            "pass": gv_pct >= REGRESSION_GATES["grading_valid_pct"],
        },
        "failure_rate_max": {
            "value": round(failure_pct, 1),
            "threshold": REGRESSION_GATES["failure_rate_max"],
            "pass": failure_pct <= REGRESSION_GATES["failure_rate_max"],
        },
        "answer_latency_avg_ms_max": {
            "value": int(sum(answer_times) / len(answer_times)) if answer_times else 0,
            "threshold": REGRESSION_GATES["answer_latency_avg_ms_max"],
            "pass": (sum(answer_times) / len(answer_times) if answer_times else 0)
                    <= REGRESSION_GATES["answer_latency_avg_ms_max"],
        },
        "choice_latency_avg_ms_max": {
            "value": int(sum(choice_times) / len(choice_times)) if choice_times else 0,
            "threshold": REGRESSION_GATES["choice_latency_avg_ms_max"],
            "pass": (sum(choice_times) / len(choice_times) if choice_times else 0)
                    <= REGRESSION_GATES["choice_latency_avg_ms_max"],
        },
    }

    return {
        "mode": "live",
        "total": len(entries),
        "n_completed": n,
        "failures": failures,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / len(entries) * 100, 1),
        "solution_quality_avg": round(sq_avg, 1),
        "grading_valid_pct": round(gv_pct, 1),
        "failure_pct": round(failure_pct, 1),
        "score_in_range_pct": round(score_in_range / n * 100, 1) if n else 0,
        "error_type_accuracy_pct": (
            round(error_type_correct / error_type_applicable * 100, 1)
            if error_type_applicable else None
        ),
        "latency_avg_ms": latency_avg,
        "choice_latency_avg_ms": (
            int(sum(choice_times) / len(choice_times)) if choice_times else None
        ),
        "answer_latency_avg_ms": (
            int(sum(answer_times) / len(answer_times)) if answer_times else None
        ),
        "results": results,
        "gates": gates,
    }


def entry_for_result(result: dict, entries: list[dict]) -> dict:
    for e in entries:
        if e["eval_id"] == result["eval_id"]:
            return e
    return {}


# ═══════════════════════════════════════════════
#  Report
# ═══════════════════════════════════════════════

def print_report(report: dict):
    print()
    print("=" * 60)
    print("  P11 Grading Evaluation Report")
    print("=" * 60)
    print(f"  Mode:        {report['mode']}")
    print(f"  Total cases: {report['total']}")

    if report["mode"] == "dry":
        print(f"  Checked:     {report['checked']}")
        if report["missing_qids"]:
            print(f"  MISSING QIDs: {report['missing_qids']}")
        if report["schema_issues"]:
            print(f"  SCHEMA ISSUES:")
            for i in report["schema_issues"]:
                print(f"    - {i}")
        print()
        print("  Dry-run complete. Run with --live for full pipeline evaluation.")
        return

    print(f"  Completed:   {report['n_completed']}")
    print(f"  Failures:    {report['failures']}")
    print(f"  Cache hits:  {report['cache_hits']} ({report['cache_hit_rate']}%)")
    print()
    print("─" * 40)
    print("  Metrics")
    print("─" * 40)
    print(f"  Solution quality avg:     {report['solution_quality_avg']}/100")
    print(f"  Grading contract valid:   {report['grading_valid_pct']}%")
    print(f"  Score in expected range:  {report['score_in_range_pct']}%")
    if report.get("error_type_accuracy_pct") is not None:
        print(f"  Error type accuracy:      {report['error_type_accuracy_pct']}%")
    print(f"  Failure rate:             {report['failure_pct']}%")
    print(f"  Avg latency (all):        {report['latency_avg_ms']}ms")
    if report.get("choice_latency_avg_ms"):
        print(f"  Avg latency (选择题):     {report['choice_latency_avg_ms']}ms")
    if report.get("answer_latency_avg_ms"):
        print(f"  Avg latency (解答题):     {report['answer_latency_avg_ms']}ms")
    print()
    print("─" * 40)
    print("  Regression Gates")
    print("─" * 40)

    all_pass = True
    for gate_name, gate in (report.get("gates") or {}).items():
        icon = "✓" if gate["pass"] else "✗ FAIL"
        print(f"  {icon}  {gate_name}: {gate['value']} "
              f"(threshold: {gate['threshold']})")
        if not gate["pass"]:
            all_pass = False

    print()
    if all_pass:
        print("  ALL GATES PASS")
    else:
        print("  GATE FAILURES DETECTED — review results above")
    print("=" * 60)


# ═══════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════

def save_run(report: dict):
    """Persist a live eval run to storage/eval_runs/ for trend tracking."""
    runs_dir = ROOT / "storage" / "eval_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Add git context
    import subprocess
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), text=True,
        ).strip()
    except Exception:
        commit = "unknown"

    from config import LLM_MODEL
    report["_meta"] = {
        "git_commit": commit,
        "model": LLM_MODEL,
        "prompt_version": "v2",
    }

    ts = _time.strftime("%Y-%m-%d_%H%M%S")
    out_path = runs_dir / f"eval_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  Run saved to {out_path.relative_to(ROOT)}")


def main():
    args = set(sys.argv[1:])
    live = "--live" in args
    verbose = "--verbose" in args

    entries = load_eval_dataset()
    print(f"Loaded {len(entries)} eval cases from {EVAL_DATASET.name}")

    if live:
        report = run_live(entries, verbose=verbose)
        save_run(report)
    else:
        report = run_dry(entries)

    print_report(report)

    if report.get("gates"):
        all_pass = all(g["pass"] for g in report["gates"].values())
        if not all_pass:
            sys.exit(1)

    if report.get("missing_qids"):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
