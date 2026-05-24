"""Question bank service — unified search, filter, pagination, recommendations.

Extracts query logic from question_bank_page so the UI only renders results.
"""

import re as _re
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════
#  LaTeX → plain-text preview
# ═══════════════════════════════════════════════

_DISPLAY_MATH_RE = _re.compile(r"\$\$(.*?)\$\$", _re.DOTALL)
_INLINE_MATH_RE = _re.compile(r"\$(.*?)\$", _re.DOTALL)
_LATEX_STRUCT_RE = _re.compile(r"\\begin\{[^}]+\}|\\end\{[^}]+\}")
_LATEX_CMD_RE = _re.compile(r"\\[a-zA-Z]+")


def latex_to_plain_preview(text: str, max_chars: int = 96) -> str:
    """Convert LaTeX source into a clean plain-text preview for card lists.

    Strips $ delimiters, replaces common LaTeX commands with readable
    equivalents, removes braces and structural commands.
    """
    if not text:
        return ""

    s = str(text)

    # Fix: $1.$ → 1.
    s = _re.sub(r"\$(\d+\s*[.．、])", r"\1", s)

    # Display math → placeholder to avoid long formulas
    s = _DISPLAY_MATH_RE.sub("【公式】", s)

    # Inline math: strip $ but keep inner content
    s = _INLINE_MATH_RE.sub(lambda m: m.group(1), s)

    # Common LaTeX → readable text
    _replacements = [
        (r"\frac", "分式"), (r"\dfrac", "分式"), (r"\tfrac", "分式"),
        (r"\partial", "偏导"), (r"\infty", "∞"), (r"\leq", "≤"),
        (r"\le", "≤"), (r"\geq", "≥"), (r"\ge", "≥"),
        (r"\sum", "求和"), (r"\int", "积分"), (r"\iint", "二重积分"),
        (r"\prod", "求积"), (r"\sqrt", "根号"), (r"\lim", "极限"),
        (r"\varphi", "φ"), (r"\lambda", "λ"), (r"\alpha", "α"),
        (r"\beta", "β"), (r"\theta", "θ"), (r"\pi", "π"),
        (r"\Rightarrow", "⇒"), (r"\rightarrow", "→"),
        (r"\cdot", "·"), (r"\times", "×"), (r"\neq", "≠"),
    ]
    for old, new in _replacements:
        s = s.replace(old, new)

    # Remove structural commands: \begin{...}, \end{...}
    s = _LATEX_STRUCT_RE.sub(" ", s)

    # Remove remaining LaTeX commands and braces
    s = s.replace("{", "").replace("}", "")
    s = _LATEX_CMD_RE.sub(" ", s)

    # Remove leftover $ signs
    s = s.replace("$", "")

    # Collapse whitespace
    s = _re.sub(r"\s+", " ", s).strip()

    # Remove leading question number artifacts
    s = _re.sub(r"^\d+\s*[.．、]\s*", "", s)

    if len(s) > max_chars:
        s = s[:max_chars].rstrip() + "…"

    return s


@dataclass
class QuestionQuery:
    keyword: str = ""
    years: list[int] = field(default_factory=list)
    volume: str = ""                          # 卷号（宇哥八套卷-卷一 等）
    subject: str = ""
    question_type: str = ""
    difficulty: str = ""
    knowledge_points: list[str] = field(default_factory=list)
    practiced: bool | None = None
    wrong_before: bool | None = None
    has_structured_solution: bool | None = None
    sort: str = "year_desc"
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════
#  Stable question identity
# ═══════════════════════════════════════════════

def ensure_question_identity(q: dict, source_index: int = 0) -> dict:
    """Guarantee every question has a stable question_id and source_index.

    Returns a copy; never mutates the original.
    """
    import hashlib

    item = dict(q or {})
    raw_id = item.get("question_id") or item.get("id") or item.get("qid") or ""

    if raw_id:
        item["question_id"] = str(raw_id)
    else:
        seed = "|".join([
            str(item.get("year", "")),
            str(item.get("subject", item.get("math_type", ""))),
            str(item.get("question_type", "")),
            str(source_index),
            str(item.get("question", ""))[:120],
        ])
        item["question_id"] = "q_" + hashlib.md5(seed.encode("utf-8")).hexdigest()[:12]

    item["_source_index"] = source_index
    return item


def build_search_text(q: dict) -> str:
    """Build a plain-text searchable string from a question, stripped of LaTeX."""
    parts = [
        str(q.get("question", "")),
        str(q.get("raw_question_text", "")),
        " ".join(q.get("knowledge_points", []) or []),
        str(q.get("year", "")),
        str(q.get("question_type", "")),
        str(q.get("difficulty", "")),
    ]
    return latex_to_plain_preview(" ".join(parts), max_chars=1000).lower()


# ═══════════════════════════════════════════════
#  Search
# ═══════════════════════════════════════════════

def search_questions(db, query: QuestionQuery, user_id: str = "") -> dict:
    """Unified question search with stable identity, filters, sort, and pagination.

    Returns:
        {"items": [{"question_id", "source_index", "display_index", "question", "vm"}, ...],
         "total": N, "page": P, "page_size": S, "total_pages": T}
    """
    # ── Fetch all questions (lightweight; db.search with limit=500) ──
    try:
        results = db.search(limit=500)
    except Exception:
        results = []

    # ── Normalize choice questions: extract embedded options from stems ──
    from services.question_option_tools import normalize_choice_question_options
    normalized = [normalize_choice_question_options(q) for q in results]

    # ── Stable identity — source_index = position in full result set ──
    indexed = [ensure_question_identity(q, source_index=i) for i, q in enumerate(normalized)]

    # ── All filters applied post-indexing so source_index stays stable ──
    if query.subject:
        indexed = [r for r in indexed if r.get("math_type") == query.subject or r.get("category") == query.subject]
    if query.volume:
        indexed = [r for r in indexed if r.get("volume") == query.volume]
    if query.question_type:
        indexed = [r for r in indexed if r.get("question_type") == query.question_type]
    if query.difficulty:
        indexed = [r for r in indexed if r.get("difficulty") == query.difficulty]
    if query.knowledge_points:
        kp = query.knowledge_points[0]
        indexed = [r for r in indexed if kp in (r.get("knowledge_points") or [])]

    if query.keyword:
        kw = query.keyword.lower().strip()
        indexed = [q for q in indexed if kw in build_search_text(q)]

    year_filter = set(query.years) if query.years else None
    if year_filter:
        indexed = [r for r in indexed if r.get("year") in year_filter]

    if query.has_structured_solution is True:
        indexed = [r for r in indexed if r.get("canonical_solutions")]
    elif query.has_structured_solution is False:
        indexed = [r for r in indexed if not r.get("canonical_solutions")]

    # ── Sort ──
    if query.sort == "year_desc":
        indexed.sort(key=lambda r: r.get("year", 0) or 0, reverse=True)
    elif query.sort == "year_asc":
        indexed.sort(key=lambda r: r.get("year", 0) or 0)
    elif query.sort == "difficulty":
        diff_order = {"基础": 0, "中等": 1, "较难": 2, "难": 3, "难题": 3}
        indexed.sort(key=lambda r: diff_order.get(r.get("difficulty", ""), 99))

    total = len(indexed)
    total_pages = max(1, (total + query.page_size - 1) // query.page_size)
    page = max(1, int(query.page or 1))
    page_size = max(1, int(query.page_size or 10))
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    page_questions = indexed[start:end]

    # ── Build structured items ──
    items = []
    for local_idx, q in enumerate(page_questions):
        display_index = start + local_idx + 1
        vm = build_question_card_vm(q)
        vm["question_id"] = q["question_id"]
        vm["source_index"] = q["_source_index"]
        vm["display_index"] = display_index

        items.append({
            "question_id": q["question_id"],
            "source_index": q["_source_index"],
            "display_index": display_index,
            "question": q,
            "vm": vm,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_similar_questions(db, mistake_record: dict, limit: int = 5,
                          exclude_qid: str = "") -> list[dict]:
    """Find questions similar to a mistake record's knowledge points.

    Returns list of question dicts (not items — raw questions for caller).
    """
    kps = mistake_record.get("knowledge_points", [])
    qtype = mistake_record.get("question_type", "")
    difficulty = mistake_record.get("difficulty", "")

    query = QuestionQuery(
        knowledge_points=kps[:3] if kps else [],
        question_type=qtype,
        difficulty=difficulty,
        page_size=limit,
    )

    result = search_questions(db, query)
    items = [it["question"] for it in result["items"]]

    if exclude_qid:
        items = [r for r in items if r.get("question_id") != exclude_qid]

    if len(items) < limit and difficulty:
        query2 = QuestionQuery(
            knowledge_points=kps[:2] if kps else [],
            question_type=qtype,
            page_size=limit,
        )
        r2 = search_questions(db, query2)
        existing_ids = {r.get("question_id") for r in items}
        extra = [it["question"] for it in r2["items"]
                 if it["question_id"] not in existing_ids
                 and it["question_id"] != exclude_qid]
        items.extend(extra)

    return items[:limit]


def build_question_card_vm(question: dict, user_stats: dict | None = None) -> dict:
    """Build a ViewModel dict for question card rendering.

    Fields:
      - preview: clean plain-text preview (no LaTeX source)
      - raw_question: original LaTeX source (for full rendering)
      - status_chips: list of (label, color) for learning status
    """
    raw_q = question.get("raw_question_text") or question.get("question") or ""
    existing_preview = question.get("question_preview") or ""

    vm = dict(question)
    vm["raw_question"] = raw_q
    vm["preview"] = existing_preview or latex_to_plain_preview(raw_q)
    vm["question_preview"] = vm["preview"]  # backward compat
    vm["status_chips"] = []

    stats = user_stats or {}
    if stats.get("practiced"):
        vm["status_chips"].append(("已练", "blue"))
    if stats.get("graded"):
        vm["status_chips"].append(("已批改", "green"))
    if stats.get("wrong_count", 0) > 0:
        vm["status_chips"].append((f"曾错{stats['wrong_count']}次", "red" if stats["wrong_count"] >= 2 else "orange"))
    if stats.get("mastered"):
        vm["status_chips"].append(("已掌握", "green"))
    if question.get("canonical_solutions"):
        vm["status_chips"].append(("有解析", "blue"))

    return vm
