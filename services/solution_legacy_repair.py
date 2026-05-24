"""Solution legacy repair — fix AI-generated standard answer text boundary issues.

Handles:
  1. "最终答案： ## 步骤1"  — removes orphan final-answer label before step headings
  2. Bare LaTeX formula lines not wrapped in $$...$$ — wraps them for KaTeX
  3. "\\text{选} (B)" in final answer — normalizes to "选 B"
"""

from __future__ import annotations

import re


_LATEX_LINE_TOKENS = (
    r"\lambda", r"\alpha", r"\beta",
    r"\Rightarrow", r"\Leftrightarrow", r"\frac",
    r"\begin", r"\end", r"\text",
    r"\neq", r"\leq", r"\geq", r"\approx",
)


def _is_already_math_line(line: str) -> bool:
    s = str(line or "").strip()
    return (
        s.startswith("$$") or s.endswith("$$")
        or s.startswith(r"\[") or s.endswith(r"\]")
        or (s.startswith("$") and s.endswith("$") and len(s) >= 2)
    )


def _looks_like_bare_formula_line(line: str) -> bool:
    """Check if a line looks like bare LaTeX that needs $$ wrapping."""
    s = str(line or "").strip()
    if not s or _is_already_math_line(s) or s.startswith("#"):
        return False

    has_latex = any(tok in s for tok in _LATEX_LINE_TOKENS)
    has_math_shape = any(c in s for c in "=_{}^\\")

    chinese_count = sum(1 for ch in s if '一' <= ch <= '鿿')
    latin_math_count = sum(1 for ch in s if ch in "\\_^=+-*/{}0123456789")

    return bool(has_latex and has_math_shape
                and latin_math_count >= 3 and chinese_count <= 20)


def _wrap_bare_formula_lines(text: str) -> str:
    lines = str(text or "").splitlines()
    out: list[str] = []
    in_display = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("$$"):
            in_display = not in_display
            out.append(line)
            continue

        if in_display:
            out.append(line)
            continue

        if _looks_like_bare_formula_line(line):
            out.append("$$\n" + stripped + "\n$$")
        else:
            out.append(line)

    return "\n".join(out)


def normalize_final_choice_text(text: str) -> str:
    r"""Normalize \text{选} (B) → 选 B in final answers."""
    if not text:
        return text
    s = str(text)
    s = re.sub(
        r"\\text\{\s*选\s*\}\s*[\(（]\s*([A-D])\s*[\)）]",
        lambda m: f"选 {m.group(1).upper()}",
        s,
        flags=re.I,
    )
    return s


def repair_legacy_solution_text(text: str) -> str:
    """Repair AI-generated legacy standard answer text.

    Fixes:
      1. "最终答案： ## 步骤1" → removes orphan label
      2. Bare LaTeX lines → wraps in $$
      3. \text{选}(B) → 选 B
      4. Collapses excessive blank lines
    """
    if not text:
        return ""

    s = str(text).replace("\r\n", "\n").replace("\r", "\n")

    # ── 1. "最终答案：" glued before step heading ──
    s = re.sub(
        r"最终答案\s*[:：]\s*(?=\s*#{1,6}\s*步骤\s*\d+)",
        "",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"(?m)^\s*最终答案\s*[:：]\s*$\n(?=\s*(?:#{1,6}\s*)?步骤\s*\d+)",
        "",
        s,
        flags=re.I,
    )

    # ── 2. Normalize markdown step headings ──
    s = re.sub(r"(?m)^\s*#{1,6}\s*(步骤\s*\d+\s*[:：]?)", r"\1", s)

    # ── 3. Normalize \text{选}(B) ──
    s = normalize_final_choice_text(s)

    # ── 4. Wrap bare formula lines ──
    s = _wrap_bare_formula_lines(s)

    # ── 5. Collapse excessive blank lines ──
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s.strip()
