"""Question option tools — extract embedded (A)(B)(C)(D) from choice stems.

Fixes the common LaTeX import issue where choice options are concatenated
into the question stem text instead of being separated into the options dict.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

OPTION_MARK_RE = re.compile(
    r"(?P<mark>[\(（]\s*(?P<key>[A-D])\s*[\)）])",
    re.IGNORECASE,
)

# ── Patterns for LaTeX-wrapped option markers: $\(A\)$, $(A)$, \(A\), etc. ──
_LATEX_OPTION_PATTERNS = [
    # $\(A\)$ / $\(B\)$ — the most common broken form
    (re.compile(r"\$\\\(\s*([A-D])\s*\\\)\$", re.IGNORECASE),
     lambda m: f"({m.group(1).upper()})"),
    # \(A\) — bare LaTeX inline math
    (re.compile(r"\\\(\s*([A-D])\s*\\\)", re.IGNORECASE),
     lambda m: f"({m.group(1).upper()})"),
    # $(A)$ / $（A）$
    (re.compile(r"\$[\(（]\s*([A-D])\s*[\)）]\$", re.IGNORECASE),
     lambda m: f"({m.group(1).upper()})"),
    # $\mathrm{A}$ / $\text{A}$
    (re.compile(r"\$\\(?:mathrm|text)\{\s*([A-D])\s*\}\$", re.IGNORECASE),
     lambda m: f"({m.group(1).upper()})"),
]


def normalize_latex_option_markers(text: str) -> str:
    r"""Convert LaTeX-wrapped option markers to plain (A)(B)(C)(D).

    Handles: $\(A\)$ -> (A), $(A)$ -> (A), \(A\) -> (A),
             $\mathrm{A}$ -> (A), $\text{A}$ -> (A).

    This must run BEFORE extract_embedded_options_latex_safe so the regex
    can find the normalized markers.
    """
    if not text:
        return ""
    s = str(text)
    for pattern, repl in _LATEX_OPTION_PATTERNS:
        s = pattern.sub(repl, s)
    return s


def _normalize_option_key(key: str) -> str:
    return str(key or "").strip().upper()


def _normalize_options_dict(options: Any) -> dict[str, str]:
    """Normalize list/dict options into {A: ..., B: ..., C: ..., D: ...}."""
    if not options:
        return {}

    if isinstance(options, dict):
        out = {}
        for k, v in options.items():
            kk = _normalize_option_key(k)
            if kk in {"A", "B", "C", "D"}:
                out[kk] = str(v or "").strip()
        return out

    if isinstance(options, list):
        letters = ["A", "B", "C", "D"]
        out = {}
        for i, v in enumerate(options[:4]):
            out[letters[i]] = str(v or "").strip()
        return out

    return {}


def extract_embedded_options_latex_safe(text: str) -> tuple[str, dict[str, str]]:
    """Extract (A)...(B)...(C)...(D) from a LaTeX choice question stem.

    Supports both (A) and （A） markers. Only triggers when 3+ distinct
    option letters are found, to avoid false positives on single (A) references.

    Returns:
        (stem_text, {"A": "content", "B": "content", ...})
    """
    raw = normalize_latex_option_markers(str(text or "").strip())
    if not raw:
        return "", {}

    matches = list(OPTION_MARK_RE.finditer(raw))
    if not matches:
        return raw, {}

    keys: list[str] = []
    for m in matches:
        k = _normalize_option_key(m.group("key"))
        if k and k not in keys:
            keys.append(k)

    if len(keys) < 3:
        return raw, {}

    # Cut at the first option marker; everything before is the stem
    first = matches[0]
    stem = raw[: first.start()].strip()

    options: dict[str, str] = {}
    for idx, m in enumerate(matches):
        key = _normalize_option_key(m.group("key"))
        if key not in {"A", "B", "C", "D"}:
            continue
        if key in options:
            continue  # first occurrence wins

        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        content = content.strip("；;，, ")

        if content:
            options[key] = content

    if len(options) < 3:
        return raw, {}

    return stem, options


def _sync_clean_stem_fields(q: dict, stem: str, original: str) -> None:
    """After option extraction, sync ALL stem fields to the clean version.

    Many renderers/parsers read raw_question_text or latex_source before
    question, so every field that could contain the stem must be updated.
    """
    clean = str(stem or "").strip()
    q["question"] = clean
    q["stem"] = clean
    if "raw_question_text" in q:
        q["raw_question_text"] = clean
    if "latex_source" in q:
        q["latex_source"] = clean
    q["_original_question_with_options"] = original


def normalize_choice_question_options(question: dict[str, Any]) -> dict[str, Any]:
    """Normalize a choice question: extract embedded options from stem.

    - If the stem contains (A)...(B)...(C)...(D), extracts them to options.
    - Now works even without explicit question_type when 4+ options detected.
    - After extraction, syncs ALL stem fields so renderers don't read old text.
    - If existing options are present but embedded ones are found, embedded win.

    Returns a deep copy; never mutates the input.
    """
    q = deepcopy(question or {})

    raw_question = (
        q.get("question")
        or q.get("stem")
        or q.get("raw_question_text")
        or q.get("latex_source")
        or ""
    )

    stem, embedded_options = extract_embedded_options_latex_safe(raw_question)

    q_type = str(q.get("question_type") or q.get("type") or "")
    is_declared_choice = "选择" in q_type
    looks_like_choice = len(embedded_options) >= 4 or bool(q.get("options"))

    if not is_declared_choice and not looks_like_choice:
        return q

    if embedded_options:
        _sync_clean_stem_fields(q, stem, raw_question)
        q["options"] = embedded_options
        q["_options_extracted_from_stem"] = True
    else:
        existing = q.get("options")
        if existing:
            q["options"] = _normalize_options_dict(existing)

    return q
