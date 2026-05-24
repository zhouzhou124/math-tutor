"""Mistake review service — priority scoring, review intervals, today queue.

Extracted from mistakes_page business logic so the UI layer only renders.
All functions are pure or take explicit dependencies.
"""

from datetime import datetime as _dt, timedelta as _td

# ── Review intervals (days) per mastery level ──
REVIEW_INTERVALS = [1, 3, 7, 14, 30]


def next_review_days(mastery_level: int) -> int:
    """Days until next review based on current mastery level."""
    idx = max(0, min(mastery_level, len(REVIEW_INTERVALS) - 1))
    return REVIEW_INTERVALS[idx]


def compute_next_review_at(mastery_level: int, from_date: str = "") -> str:
    """Compute the next review date as an ISO date string."""
    base = _dt.now() if not from_date else _dt.fromisoformat(from_date[:10])
    return (base + _td(days=next_review_days(mastery_level))).strftime("%Y-%m-%d")


def classify_mistake_severity(record: dict) -> str:
    """Return severity label: hot | warm | cool | done."""
    try:
        ratio = float(record.get("score", 0)) / max(float(record.get("max_score", 10)), 1)
    except (TypeError, ValueError):
        ratio = 0.5
    if ratio < 0.4:
        return "hot"
    if ratio < 0.7:
        return "warm"
    if ratio < 0.9:
        return "cool"
    return "done"


def compute_mistake_priority(record: dict) -> int:
    """Score a mistake record for review priority. Higher = more urgent.

    Factors:
      - Low score ratio: up to +40
      - Wrong count: up to +32
      - Recent: +10
      - Has weak points: +8
      - Mastered: -60
      - Archived: -100
    """
    score = 0

    try:
        total = float(record.get("max_score", 10) or 10)
        got = float(record.get("score", 0) or 0)
        ratio = got / total if total else 0
    except (TypeError, ValueError):
        ratio = 0.5

    if ratio < 0.4:
        score += 40
    elif ratio < 0.7:
        score += 25
    else:
        score += 10

    score += min(int(record.get("wrong_count", 1) or 1) * 8, 32)

    if record.get("is_recent", False):
        score += 10

    if record.get("weak_points"):
        score += 8

    status = record.get("status", "active")
    if status == "mastered":
        score -= 60
    if status == "archived":
        score -= 100

    return max(0, score)


def build_today_review_queue(records: list[dict], limit: int = 20) -> list[dict]:
    """Sort mistake records by priority, filter to actionable items.

    Active records only. Sorted by priority descending. Capped at `limit`.
    """
    actionable = [r for r in records if r.get("status", "active") in ("active", "reviewing")]
    scored = [(compute_mistake_priority(r), r) for r in actionable]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


def update_mastery(record: dict, mastered: bool) -> dict:
    """Update mastery fields after a review action.

    If mastered: increment mastery_level, set next review date.
    If failed again: decrement mastery_level, reset to active.
    """
    r = dict(record)
    level = int(r.get("mastery_level", 0) or 0)
    if mastered:
        level += 1
        r["mastery_level"] = level
        r["next_review_at"] = compute_next_review_at(level)
        if level >= 4:
            r["status"] = "mastered"
    else:
        level = max(0, level - 1)
        r["mastery_level"] = level
        r["status"] = "active"
        r["next_review_at"] = _dt.now().strftime("%Y-%m-%d")
    r["last_reviewed_at"] = _dt.now().strftime("%Y-%m-%d")
    return r


def merge_duplicate_mistakes(records: list[dict]) -> list[dict]:
    """Merge records with the same question_id into aggregated cards.

    Returns deduplicated list where each entry has:
      - wrong_count: total times missed
      - latest_score: most recent score
      - best_score: best score ever
      - history: list of {score, created_at} for each attempt
    """
    by_qid: dict[str, dict] = {}
    for r in records:
        qid = r.get("question_id", "")
        if qid not in by_qid:
            by_qid[qid] = dict(r)
            by_qid[qid]["wrong_count"] = 1
            by_qid[qid]["best_score"] = r.get("score", 0)
            by_qid[qid]["history"] = [{
                "score": r.get("score", 0),
                "created_at": r.get("timestamp", r.get("created_at", "")),
            }]
        else:
            entry = by_qid[qid]
            entry["wrong_count"] = entry.get("wrong_count", 1) + 1
            entry["latest_score"] = r.get("score", 0)
            best = entry.get("best_score", 0)
            entry["best_score"] = max(best, r.get("score", 0) or 0)
            entry["history"].append({
                "score": r.get("score", 0),
                "created_at": r.get("timestamp", r.get("created_at", "")),
            })
    return list(by_qid.values())


def build_mistake_card_vm(record: dict) -> dict:
    """Build a clean ViewModel for mistake card rendering.

    Returns a dict with plain-text preview (no LaTeX source), severity,
    and all display fields ready for render_mistake_card().
    """
    from services.question_bank_service import latex_to_plain_preview

    raw_preview = (
        record.get("question_preview")
        or record.get("question")
        or record.get("raw_question_text")
        or ""
    )
    vm = dict(record)
    vm["preview"] = latex_to_plain_preview(raw_preview, max_chars=96)
    vm["severity"] = classify_mistake_severity(record)
    vm["priority"] = compute_mistake_priority(record)
    return vm
