"""question_ast.py — Question Abstract Syntax Tree

Structured question data — NOT a flat markdown blob.

Each question type has its own AST node.
Renderers consume the AST, not raw text.
"""
import re
import json as _json
from latex_utils import normalize_latex_style
from dataclasses import dataclass, field
from typing import Optional as _Optional


# ============================================================
# AST Nodes
# ============================================================

@dataclass
class ChoiceOption:
    label: str            # "A", "B", "C", "D"
    content: str          # LaTeX, e.g. "k=2, c=-\\frac12"


@dataclass
class QuestionStem:
    """Parsed question stem — text + optional inline math."""
    text: str             # Clean text with inline math markers preserved


@dataclass
class SolutionStep:
    label: str = ""       # "步骤1"
    content: str = ""     # LaTeX / text
    operation: str = ""   # "differentiate", "solve", etc.


@dataclass
class QuestionAST:
    """Base AST node — common fields for all question types."""
    question_id: str
    question_type: str              # "选择题" | "填空题" | "解答题" | "证明题"
    stem: str = ""                  # Pure question text (no options mixed in)
    answer: str = ""                # Correct answer
    analysis: str = ""              # Solution / explanation
    year: str = ""
    category: str = ""
    score: str = ""
    difficulty: str = "中等"
    knowledge_points: list = field(default_factory=list)
    # Type-specific fields
    options: list = field(default_factory=list)    # list[ChoiceOption] for choice
    steps: list = field(default_factory=list)      # list[SolutionStep] for solution/proof


# ============================================================
# Parser: legacy flat text → AST
# ============================================================

def _extract_stem_and_options(text: str) -> tuple[str, list[ChoiceOption]]:
    """Extract stem text and choice options from legacy question text.

    Handles formats:
      $(A)$ content \\qquad $(B)$ content
      (A) content (B) content
      A. content  B. content
    """
    options = []
    stem = text

    # 预处理：先把 \qquad 和 \quad 替换为换行，这样选项就会出现在单独的行
    processed_text = text.replace('\\qquad', '\n').replace('\\quad', '\n')

    # Pattern 1: $(A)$ content \\qquad $(B)$ content  etc.
    # 重要：只匹配行首或换行后的选项标签，避免匹配数学表达式中的括号（如 P(B)）
    # Note: 不在末尾匹配 $，避免吃掉后面选项内容开头的 $
    opt_pattern = re.compile(
        r'(?:^|\n)(?:\s*\$\\left\(\\mathrm\{([A-D])\}\\right\))'
        r'|'
        r'(?:^|\n)(?:\s*\$\(([A-D])\))'
        r'|'
        r'(?:^|\n)(?:\s*[（(]\s*([A-D])\s*[）)])'
    )

    # Find all option markers with positions
    markers = []
    for m in opt_pattern.finditer(processed_text):
        label = m.group(1) or m.group(2) or m.group(3)
        if label and label not in [x[0] for x in markers]:
            markers.append((label, m.start(), m.end()))

    if len(markers) >= 2:
        # First marker position = end of stem
        stem_end = markers[0][1]
        stem = processed_text[:stem_end].strip()
        # Remove trailing number prefix like "1. " or "$1.$"
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', stem)

        # Extract option content between markers
        for i, (label, start, end) in enumerate(markers):
            next_start = markers[i + 1][1] if i + 1 < len(markers) else len(processed_text)
            content = processed_text[end:next_start].strip()
            # Clean up separators
            content = re.sub(r'\\qquad|\\quad', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            # Handle the case where label is formatted as $\left(\mathrm{A}\right)$
            # and is directly followed by $$ content (no space)
            # This causes the two $ signs to merge, leaving an extra $ at the start
            # e.g., $\left(\mathrm{A}\right)$$$content$$ -> match gives $content$$
            # If content starts with $$, it's correct. If it starts with $ but not $$,
            # it means there's an extra $ that should be removed
            if content.startswith('$') and len(content) > 1 and not content.startswith('$$'):
                content = content[1:].strip()
            # LaTeX post-processing: normalize + preserve $ delimiters
            content = normalize_latex_style(content)
            # Preserve all $ delimiters - the renderer will handle them appropriately
            options.append(ChoiceOption(label=label, content=content))

    # Deduplicate by label (keep first occurrence)
    seen = set()
    deduped = []
    for o in options:
        if o.label not in seen:
            seen.add(o.label)
            deduped.append(o)

    return stem, deduped


def _extract_answer(text: str, qtype: str) -> str:
    """Extract answer from text based on question type."""
    # Choice: look for "正确选项" or check the correct_option field
    m = re.search(r'(?:正确选项|答案|选)\s*[：:]\s*([A-D])', text)
    if m:
        return m.group(1)
    # Fill/Solution: look for answer markers
    m = re.search(r'(?:答案|答|解)\s*[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        return m.group(1).strip()
    return ""


def parse_legacy(q: dict) -> QuestionAST:
    """Convert a legacy QuestionDB dict into a QuestionAST.

    The legacy format stores the entire question as a single LaTeX string
    in q['question'], with options/answers embedded inline.
    This parser decomposes it into structured fields.
    """
    qid = q.get("question_id", "?")
    qtype = q.get("question_type", "")
    raw_text = q.get("question", "")
    raw_answer = q.get("standard_answer", "")
    correct = q.get("correct_option", "")
    options_raw = q.get("options") or {}
    steps_raw = q.get("solution_steps") or []

    # Parse stem + options from raw text
    stem = raw_text
    options = []

    if qtype == "选择题":
        stem, options = _extract_stem_and_options(raw_text)
        # Use existing options dict if the parser didn't find inline options
        if not options and options_raw:
            for label in "ABCDEFGH":
                if label in options_raw:
                    content = options_raw[label]
                    # Preserve $ delimiters - the renderer will handle them appropriately
                    c = content.strip()
                    # Handle legacy "1706" marker (single pair only)
                    if c.startswith("1706") and c.endswith("1706") and c.count("1706") == 2:
                        c = c[2:-2].strip()
                    content = c
                    options.append(ChoiceOption(label=label, content=normalize_latex_style(content)))
        answer = correct or raw_answer

    elif qtype == "填空题":
        answer = raw_answer
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', raw_text)

    elif qtype in ("解答题", "证明题"):
        answer = raw_answer
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', raw_text)
        if not answer and raw_text:
            answer = _extract_answer(raw_text, qtype)

    else:
        answer = raw_answer

    # Parse solution steps
    steps = []
    for s in steps_raw:
        if isinstance(s, dict):
            steps.append(SolutionStep(
                label=s.get("label", ""),
                content=s.get("content", ""),
                operation=s.get("operation", ""),
            ))
        elif isinstance(s, str):
            steps.append(SolutionStep(content=s))

    # Normalize LaTeX: wrap bare math, fix stray $, unify delimiters
    stem = normalize_latex_style(stem.strip()) if stem else ""
    answer = normalize_latex_style(answer.strip()) if answer else ""

    return QuestionAST(
        question_id=qid,
        question_type=qtype,
        stem=stem,
        answer=answer.strip() if answer else "",
        analysis=raw_answer.strip() if raw_answer else "",
        year=str(q.get("year", "")),
        category=q.get("category", ""),
        score=str(q.get("score", "")),
        difficulty=q.get("difficulty", "中等"),
        knowledge_points=q.get("knowledge_points") or q.get("tags") or [],
        options=options,
        steps=steps,
    )


# ============================================================
# Serialization
# ============================================================

def ast_to_dict(ast: QuestionAST) -> dict:
    """Convert QuestionAST back to a plain dict (for JSON storage)."""
    return {
        "question_id": ast.question_id,
        "question_type": ast.question_type,
        "stem": ast.stem,
        "options": [{"label": o.label, "content": o.content} for o in ast.options],
        "answer": ast.answer,
        "analysis": ast.analysis,
        "steps": [
            {"label": s.label, "content": s.content, "operation": s.operation}
            for s in ast.steps
        ],
        "year": ast.year,
        "category": ast.category,
        "score": ast.score,
        "difficulty": ast.difficulty,
        "knowledge_points": ast.knowledge_points,
    }


def ast_to_json(ast: QuestionAST) -> str:
    """Serialize QuestionAST to JSON string."""
    return _json.dumps(ast_to_dict(ast), ensure_ascii=False, indent=2)


# ============================================================
# Legacy dict adapter (for backward compatibility)
# ============================================================

def ast_to_legacy_dict(ast: QuestionAST) -> dict:
    """Convert AST back to a dict compatible with legacy renderers.

    This allows gradual migration — renderers that expect q['question']
    will still work while we transition to AST-native rendering.
    """
    # Rebuild the full question text
    parts = [ast.stem]
    if ast.options:
        opt_parts = []
        for i, opt in enumerate(ast.options):
            opt_parts.append(
                f"$(\\left(\\mathrm{{{opt.label}}}\\right))$ {opt.content}"
            )
        parts.append("  ".join(opt_parts))

    full_text = "\n\n".join(parts)

    return {
        "question_id": ast.question_id,
        "question_type": ast.question_type,
        "question": full_text,
        "standard_answer": ast.answer,
        "correct_option": ast.answer if ast.question_type == "选择题" else "",
        "options": {o.label: o.content for o in ast.options} if ast.options else {},
        "solution_steps": [
            {"label": s.label, "content": s.content, "operation": s.operation}
            for s in ast.steps
        ],
        "year": ast.year,
        "category": ast.category,
        "score": ast.score,
        "difficulty": ast.difficulty,
        "knowledge_points": ast.knowledge_points,
        "tags": ast.knowledge_points,
    }
