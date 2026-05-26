"""Policy-driven LaTeX rendering — separate question bank vs grading paths."""

from __future__ import annotations

import re
from typing import Any

from renderers.math_render_context import MathRenderContext

QUESTION_BANK_POLICY: dict[str, Any] = {
    "allow_ai_repair": False,
    "allow_broken_frac_repair": False,
    "allow_mojibake_cleanup": False,
    "force_cjk_inline": True,
    "normalize_subquestion_markers": True,
    "use_st_latex": False,
    "preserve_source_layout": True,
    "clean_markdown": True,
}

GRADING_POLICY: dict[str, Any] = {
    "allow_ai_repair": True,
    "allow_broken_frac_repair": True,
    "allow_mojibake_cleanup": True,
    "force_cjk_inline": True,
    "normalize_subquestion_markers": True,
    "use_st_latex": False,
    "preserve_source_layout": False,
    "clean_markdown": True,
}

_POLICY_BY_CONTEXT = {
    MathRenderContext.QUESTION_BANK: QUESTION_BANK_POLICY,
    MathRenderContext.GRADING: GRADING_POLICY,
}


def policy_for_context(context: MathRenderContext) -> dict[str, Any]:
    return _POLICY_BY_CONTEXT[context]


def _apply_policy_repairs(text: str, policy: dict[str, Any]) -> str:
    if policy.get("allow_ai_repair"):
        from services.solution_legacy_repair import repair_legacy_solution_text

        return repair_legacy_solution_text(text)

    updated = text
    if policy.get("allow_mojibake_cleanup"):
        from services.solution_legacy_repair import clean_mojibake_tokens

        updated = clean_mojibake_tokens(updated)
    if policy.get("allow_broken_frac_repair"):
        from services.solution_legacy_repair import repair_broken_frac_blocks

        updated = repair_broken_frac_blocks(updated)
    return updated


_SUBQUESTION_LINE_RE = re.compile(
    r"(?m)^[ \t]*(\$\(\s*(?:\d+|[一二三四五六七八九十百]+)\s*\)\$|\(\s*(?:\d+|[一二三四五六七八九十百]+)\s*\))\s*"
)


def _preserve_question_bank_subquestion_lines(text: str) -> str:
    """Keep authored multipart question labels as separate Markdown paragraphs."""
    if not text:
        return text

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    cursor = 0
    for match in _SUBQUESTION_LINE_RE.finditer(normalized):
        out.append(normalized[cursor:match.start()])
        label = match.group(1).strip()
        prefix = "" if match.start() == 0 else "\n\n"
        out.append(f"{prefix}{label} ")
        cursor = match.end()
    out.append(normalized[cursor:])

    result = "".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def render_latex_with_policy(text: str, policy: dict[str, Any]) -> None:
    """Render plain text/math using AST pipeline and the supplied policy."""
    from latex_utils import (
        _preprocess_latex,
        clean_markdown,
        render_ast,
        split_latex_text,
    )

    if not text:
        return
    if not isinstance(text, str):
        text = str(text)

    text = _preprocess_latex(text)
    text = _apply_policy_repairs(text, policy)

    if policy.get("clean_markdown", True):
        text = clean_markdown(text)

    if policy.get("preserve_source_layout"):
        text = _preserve_question_bank_subquestion_lines(text)

    segments = split_latex_text(text)
    render_ast(segments, use_st_latex=policy.get("use_st_latex", False))


def render_question_bank_latex(text: str) -> None:
    return render_latex_with_policy(text, QUESTION_BANK_POLICY)


def render_grading_latex(text: str) -> None:
    return render_latex_with_policy(text, GRADING_POLICY)


def render_latex_for_context(text: str, context: MathRenderContext) -> None:
    return render_latex_with_policy(text, policy_for_context(context))
