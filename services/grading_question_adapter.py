"""Grading question adapter — normalize question fields for the grading pipeline.

Ensures real-exam and mock/simulation questions use the same field access
patterns when entering the grading pipeline.  The adapter does NOT modify
the original question dict; it returns extracted values.

P31: Use real-exam grading pipeline for both real and mock questions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── Field resolution helpers ──

def _normalize_choice_answer(ans: str) -> str:
    """Extract A-D letter from answer string."""
    text = str(ans or "").strip().upper()
    if not text:
        return ""
    m = re.search(r"(?:答案|正确选项|故选|选|^|\(|（)\s*[:：]?\s*([A-D])(?:\)|）|$|[\s。；;，,])", text)
    if m:
        return m.group(1)
    if len(text) <= 3:
        m = re.search(r"[A-D]", text)
        return m.group(0) if m else ""
    return ""


def _get_nested(question: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = question
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _first_text_field(
    question: dict[str, Any],
    fields: list[tuple[str, tuple[str, ...]]],
) -> tuple[str, str]:
    for name, path in fields:
        value = _get_nested(question, path)
        if value is None:
            continue
        text = str(value or "").strip()
        if text:
            return text, name
    return "", ""


def _looks_like_solution_text(text: str) -> bool:
    markers = ("步骤", "解答", "解析", "证明", "过程", "##", "\n")
    return any(marker in str(text or "") for marker in markers)


def resolve_correct_answer(
    question: dict[str, Any] | None,
    question_type: str | None = None,
) -> dict[str, Any]:
    """Resolve the canonical answer without branching by real/mock source."""
    q = dict(question or {})
    q_type = str(question_type or q.get("question_type") or "")

    if "选择" in q_type:
        fields = [
            ("correct_option", ("correct_option",)),
            ("correct_answer", ("correct_answer",)),
            ("answer", ("answer",)),
            ("standard_answer", ("standard_answer",)),
            ("solution.answer", ("solution", "answer")),
            ("metadata.correct_option", ("metadata", "correct_option")),
            ("choices.correct", ("choices", "correct")),
        ]
        issues: list[str] = []
        for source_field, path in fields:
            value = _get_nested(q, path)
            if value is None or str(value or "").strip() == "":
                continue
            text = str(value or "").strip()
            option = _normalize_choice_answer(text)
            if option:
                return {
                    "answer": option,
                    "correct_option": option,
                    "answer_text": text,
                    "source_field": source_field,
                    "ok": True,
                    "issues": [],
                }
            issues.append(f"{source_field}:unparseable_choice")
        return {
            "answer": "",
            "correct_option": "",
            "answer_text": "",
            "source_field": "",
            "ok": False,
            "issues": issues or ["missing_choice_answer"],
        }

    if "填空" in q_type:
        text, source_field = "", ""
        for name, path in [
            ("answer", ("answer",)),
            ("correct_answer", ("correct_answer",)),
            ("standard_answer", ("standard_answer",)),
            ("final_answer", ("final_answer",)),
            ("solution.answer", ("solution", "answer")),
            ("metadata.answer", ("metadata", "answer")),
        ]:
            value = _get_nested(q, path)
            candidate = str(value or "").strip()
            if not candidate:
                continue
            if name == "standard_answer" and _looks_like_solution_text(candidate):
                continue
            text, source_field = candidate, name
            break
    else:
        text, source_field = _first_text_field(q, [
            ("standard_answer", ("standard_answer",)),
            ("solution", ("solution",)),
            ("final_answer", ("final_answer",)),
            ("answer", ("answer",)),
            ("correct_answer", ("correct_answer",)),
        ])

    return {
        "answer": text,
        "correct_option": None,
        "answer_text": text,
        "source_field": source_field,
        "ok": bool(text),
        "issues": [] if text else ["missing_answer"],
    }


def resolve_correct_option(selected_q: dict[str, Any]) -> str:
    """Resolve the correct option letter for a choice question.

    Tries fields in priority order:
    1. correct_option  (standard field)
    2. answer          (if it looks like A/B/C/D)
    3. correct_answer  (if it looks like A/B/C/D)
    4. standard_answer (if it looks like A/B/C/D)
    5. _original_answer (if it looks like A/B/C/D)

    Returns empty string if none found.
    """
    return str(resolve_correct_answer(selected_q, "选择题").get("correct_option") or "")


def resolve_final_answer(selected_q: dict[str, Any]) -> str:
    """Resolve the final answer value for a fill/free-response question.

    Tries fields in priority order:
    1. final_answer     (standard field)
    2. _original_answer (legacy field)
    3. answer           (generic)
    4. correct_answer   (generic)
    5. standard_answer  (if it looks like a short answer, not a full solution)

    Returns empty string if none found.
    """
    for key in ("answer", "correct_answer", "standard_answer", "final_answer", "_original_answer"):
        val = str(selected_q.get(key, "") or "").strip()
        if val and (
            key != "standard_answer"
            or (len(val) < 100 and not _looks_like_solution_text(val))
        ):
            return val

    return ""


def resolve_question_source(selected_q: dict[str, Any]) -> str:
    """Determine question source from metadata.

    Returns: "real_exam", "mock", "manual", or "unknown".
    """
    src = str(selected_q.get("source", "") or "").lower()
    qid = str(selected_q.get("question_id", "") or "")

    if "mock" in src or "simulation" in src:
        return "mock"
    if "宇哥" in qid or "合工大" in qid or "hegongda" in src or "zhangyu" in src:
        return "mock"
    if "manual" in src:
        return "manual"
    if src:
        return "real_exam"
    # Default: treat as real exam (most questions are)
    return "real_exam"


# ── Normalized grading input ──

@dataclass
class GradingQuestionInput:
    """Unified question input for the grading pipeline.

    All grading functions should consume this instead of raw question dicts.
    """
    question_id: str = ""
    source: str = "unknown"          # real_exam | mock | manual | unknown
    source_type: str = "unknown"     # real_exam | mock | manual | unknown
    source_name: str = ""
    question_type: str = ""          # 选择题 | 填空题 | 解答题 | 证明题
    question_text: str = ""          # stem text
    options: dict | list | None = None
    correct_option: str = ""         # A/B/C/D for choice questions
    correct_answer: str = ""
    answer_source_field: str = ""
    answer_resolution_issues: list[str] = field(default_factory=list)
    final_answer: str = ""           # short answer for fill questions
    standard_answer: str = ""        # full solution text
    knowledge_points: list[str] = field(default_factory=list)
    difficulty: str = "中等"
    score: float = 10.0
    canonical_solutions: list | None = None
    solution_metadata: dict | None = None
    raw_question: dict = field(default_factory=dict)  # original dict, read-only


def normalize_to_grading_input(
    question: dict[str, Any] | None,
    *,
    source: str | None = None,
) -> GradingQuestionInput:
    """Normalize any question dict into a GradingQuestionInput.

    Works for real exams, mock/simulations, and manual imports.
    Does NOT modify the original question dict.
    """
    q = dict(question or {})

    resolved_source = source or resolve_question_source(q)
    q_type = str(q.get("question_type", "") or "")
    resolved_answer = resolve_correct_answer(q, q_type)

    return GradingQuestionInput(
        question_id=str(q.get("question_id", "") or ""),
        source=resolved_source,
        source_type=resolved_source,
        source_name=str(q.get("source") or q.get("category") or q.get("source_name") or ""),
        question_type=q_type,
        question_text=str(q.get("question", "") or q.get("question_text", "") or ""),
        options=q.get("options"),
        correct_option=str(resolved_answer.get("correct_option") or ""),
        correct_answer=str(resolved_answer.get("answer") or ""),
        answer_source_field=str(resolved_answer.get("source_field") or ""),
        answer_resolution_issues=list(resolved_answer.get("issues") or []),
        final_answer=resolve_final_answer(q),
        standard_answer=str(q.get("standard_answer", "") or ""),
        knowledge_points=list(q.get("knowledge_points", []) or []),
        difficulty=str(q.get("difficulty", "中等") or "中等"),
        score=float(q.get("score") or q.get("total_score") or 10),
        canonical_solutions=q.get("canonical_solutions"),
        solution_metadata=q.get("solution_metadata"),
        raw_question=q,
    )
