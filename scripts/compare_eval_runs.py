#!/usr/bin/env python3
"""P12 Eval Trend Comparison — diff two eval run JSON files.

Usage:
  python scripts/compare_eval_runs.py old.json new.json
  python scripts/compare_eval_runs.py storage/eval_runs/eval_2026-05-25_120000.json \\
                                    storage/eval_runs/eval_2026-05-26_120000.json

Answers:
  - Did quality improve or degrade?
  - Which questions regressed?
  - Did latency change?
  - Did error type accuracy change?
"""

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_metric(name: str, old_val, new_val, unit: str = "",
                   higher_is_better: bool = True) -> dict:
    """Compare a single metric between two runs."""
    if old_val is None or new_val is None:
        return {"name": name, "old": old_val, "new": new_val,
                "delta": None, "direction": "n/a", "unit": unit}

    delta = new_val - old_val
    if abs(old_val) > 0.001:
        pct = delta / abs(old_val) * 100
    else:
        pct = 0

    if higher_is_better:
        direction = "↑ better" if delta > 0 else ("↓ worse" if delta < 0 else "— same")
    else:
        direction = "↓ better" if delta < 0 else ("↑ worse" if delta > 0 else "— same")

    return {
        "name": name,
        "old": old_val, "new": new_val,
        "delta": delta, "delta_pct": round(pct, 1),
        "direction": direction, "unit": unit,
    }


def compare_per_question(old_results: list, new_results: list) -> list:
    """Find questions that regressed between runs."""
    old_by_id = {r["eval_id"]: r for r in old_results}
    new_by_id = {r["eval_id"]: r for r in new_results}

    regressions = []
    improvements = []

    for eid in sorted(set(old_by_id) & set(new_by_id)):
        old_r = old_by_id[eid]
        new_r = new_by_id[eid]

        old_score = old_r.get("solution_quality_score") or 0
        new_score = new_r.get("solution_quality_score") or 0
        old_lat = old_r.get("latency_ms") or 0
        new_lat = new_r.get("latency_ms") or 0

        q_delta = new_score - old_score
        entry = {
            "eval_id": eid,
            "old_quality": old_score,
            "new_quality": new_score,
            "quality_delta": q_delta,
            "old_latency_ms": old_lat,
            "new_latency_ms": new_lat,
            "old_status": old_r.get("status", "?"),
            "new_status": new_r.get("status", "?"),
        }

        if q_delta < -10:
            regressions.append(entry)
        elif q_delta > 10:
            improvements.append(entry)

    return regressions, improvements


def print_comparison(old: dict, new: dict):
    """Pretty-print comparison report."""
    old_meta = old.get("_meta", {})
    new_meta = new.get("_meta", {})

    print()
    print("=" * 66)
    print("  P12 Eval Trend Comparison")
    print("=" * 66)
    print(f"  Old: {old_meta.get('git_commit', '?')}  model={old_meta.get('model', '?')}")
    print(f"  New: {new_meta.get('git_commit', '?')}  model={new_meta.get('model', '?')}")
    print()

    if old.get("mode") != "live" or new.get("mode") != "live":
        print("  Both runs must be --live for comparison.")
        return

    # ── Aggregate metrics ──
    metrics = [
        compare_metric("Solution Quality Avg", old.get("solution_quality_avg"),
                       new.get("solution_quality_avg"), higher_is_better=True),
        compare_metric("Grading Valid %", old.get("grading_valid_pct"),
                       new.get("grading_valid_pct"), unit="%", higher_is_better=True),
        compare_metric("Score in Range %", old.get("score_in_range_pct"),
                       new.get("score_in_range_pct"), unit="%", higher_is_better=True),
        compare_metric("Error Type Accuracy %", old.get("error_type_accuracy_pct"),
                       new.get("error_type_accuracy_pct"), unit="%", higher_is_better=True),
        compare_metric("Failure Rate %", old.get("failure_pct"),
                       new.get("failure_pct"), unit="%", higher_is_better=False),
        compare_metric("Cache Hit Rate %", old.get("cache_hit_rate"),
                       new.get("cache_hit_rate"), unit="%", higher_is_better=True),
        compare_metric("Avg Latency (ms)", old.get("latency_avg_ms"),
                       new.get("latency_avg_ms"), unit="ms", higher_is_better=False),
        compare_metric("解答题 Avg Latency (ms)", old.get("answer_latency_avg_ms"),
                       new.get("answer_latency_avg_ms"), unit="ms", higher_is_better=False),
        compare_metric("选择题 Avg Latency (ms)", old.get("choice_latency_avg_ms"),
                       new.get("choice_latency_avg_ms"), unit="ms", higher_is_better=False),
    ]

    print("─" * 66)
    print(f"  {'Metric':<28s} {'Old':>10s} {'New':>10s} {'Δ':>10s}  Direction")
    print("─" * 66)
    for m in metrics:
        old_s = f"{m['old']}{m['unit']}" if m['old'] is not None else "n/a"
        new_s = f"{m['new']}{m['unit']}" if m['new'] is not None else "n/a"
        if m['delta'] is not None:
            delta_s = f"{m['delta']:+.1f}{m['unit']}"
        else:
            delta_s = "n/a"
        print(f"  {m['name']:<28s} {old_s:>10s} {new_s:>10s} {delta_s:>10s}  {m['direction']}")

    # ── Per-question regression ──
    old_results = old.get("results", [])
    new_results = new.get("results", [])
    regressions, improvements = compare_per_question(old_results, new_results)

    if regressions:
        print()
        print(f"  REGRESSIONS ({len(regressions)} questions, quality drop >10):")
        for r in regressions:
            print(f"    {r['eval_id']:12s}  Q: {r['old_quality']}→{r['new_quality']} "
                  f"({r['quality_delta']:+d})  "
                  f"status: {r['old_status']}→{r['new_status']}")

    if improvements:
        print()
        print(f"  IMPROVEMENTS ({len(improvements)} questions, quality gain >10):")
        for r in improvements:
            print(f"    {r['eval_id']:12s}  Q: {r['old_quality']}→{r['new_quality']} "
                  f"({r['quality_delta']:+d})")

    # ── Gate comparison ──
    old_gates = old.get("gates", {})
    new_gates = new.get("gates", {})
    if old_gates and new_gates:
        old_all_pass = all(g["pass"] for g in old_gates.values())
        new_all_pass = all(g["pass"] for g in new_gates.values())
        print()
        if old_all_pass and new_all_pass:
            print("  Gates: both pass")
        elif old_all_pass and not new_all_pass:
            print("  Gates: OLD pass → NEW FAIL ✗")
        elif not old_all_pass and new_all_pass:
            print("  Gates: OLD fail → NEW PASS ✓")
        else:
            print("  Gates: both fail")

    print("=" * 66)


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_eval_runs.py <old.json> <new.json>")
        print("       python scripts/compare_eval_runs.py storage/eval_runs/old.json new.json")
        sys.exit(2)

    old_path, new_path = sys.argv[1], sys.argv[2]

    if not Path(old_path).exists():
        print(f"File not found: {old_path}")
        sys.exit(1)
    if not Path(new_path).exists():
        print(f"File not found: {new_path}")
        sys.exit(1)

    old = load(old_path)
    new = load(new_path)
    print_comparison(old, new)


if __name__ == "__main__":
    main()
