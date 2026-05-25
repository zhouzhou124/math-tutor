"""P25: Solution coverage analysis — classify question answer completeness.

Classifies each question into one of four states:
  no_answer           — no answer at all
  answer_only         — has short answer but no detailed solution
  has_detailed_solution — has long standard_answer (>=120 chars)
  has_structured_solution — has canonical_solutions pool entry with structured
"""

from __future__ import annotations


def classify_question_solution_state(q: dict) -> str:
    """Classify a single question's solution state."""
    if not isinstance(q, dict):
        return "no_answer"

    pool = q.get("canonical_solutions") or []
    for entry in pool:
        if entry.get("structured") or entry.get("canonical_ir"):
            return "has_structured_solution"
        ans = entry.get("standard_answer") or ""
        if len(ans.strip()) >= 120:
            return "has_detailed_solution"

    ans = (q.get("standard_answer") or "").strip()
    if len(ans) >= 120:
        return "has_detailed_solution"

    if q.get("raw_answer_text") or q.get("final_answer") or q.get("correct_option"):
        return "answer_only"

    return "no_answer"


def compute_solution_coverage(question_db) -> dict:
    """Analyze solution coverage across all questions.

    Returns:
        {"total": N, "no_answer": N, "answer_only": N,
         "has_detailed_solution": N, "has_structured_solution": N}
    """
    counts = {
        "total": 0, "no_answer": 0, "answer_only": 0,
        "has_detailed_solution": 0, "has_structured_solution": 0,
    }
    try:
        results = question_db.search(limit=10000)
    except Exception:
        results = []

    for q in results:
        counts["total"] += 1
        state = classify_question_solution_state(q)
        counts[state] = counts.get(state, 0) + 1

    total = counts["total"]
    counts["answer_coverage_pct"] = round(
        (total - counts["no_answer"]) / max(total, 1) * 100, 1
    )
    counts["detailed_coverage_pct"] = round(
        (counts["has_detailed_solution"] + counts["has_structured_solution"])
        / max(total, 1) * 100, 1
    )
    return counts


def build_solution_backfill_candidates(
    question_db, limit: int = 20, filters: dict = None,
) -> list[dict]:
    """Return questions that need detailed solution generation.

    Filters out questions that already have structured or detailed solutions.
    """
    filters = filters or {}
    try:
        results = question_db.search(limit=500, **filters)
    except Exception:
        return []

    candidates = []
    for q in results:
        state = classify_question_solution_state(q)
        if state in ("no_answer", "answer_only"):
            candidates.append({
                "question_id": q.get("question_id", ""),
                "question_type": q.get("question_type", "?"),
                "knowledge_points": q.get("knowledge_points", []),
                "current_state": state,
            })

    return candidates[:limit]
