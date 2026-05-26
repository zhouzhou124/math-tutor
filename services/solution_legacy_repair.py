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

_AI_META_HEADINGS = (
    "题目重述", "关键知识点", "易错提示", "常见误区",
    "秒杀技巧", "考查知识点", "薄弱知识点",
)
_DISPLAY_ENVS = (
    "aligned", "cases", "array", "matrix", "pmatrix", "bmatrix",
    "vmatrix", "Vmatrix", "split", "gathered",
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
    if not s or _is_already_math_line(s) or s.startswith("#") or "$" in s:
        return False

    has_latex = any(tok in s for tok in _LATEX_LINE_TOKENS)
    has_math_shape = any(c in s for c in "=_{}^\\")

    math_only = re.sub(r"\\text\{[^}]*\}", "", s)
    chinese_count = sum(1 for ch in math_only if '一' <= ch <= '鿿')
    latin_math_count = sum(1 for ch in s if ch in "\\_^=+-*/{}0123456789")

    return bool(has_latex and has_math_shape
                and latin_math_count >= 3 and chinese_count == 0)


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


def clean_orphan_problem_markers(text: str) -> str:
    """P15-3: Clean orphan formula tail fragments like (2.过), isolated sub-question markers."""
    if not text:
        return ""

    s = str(text)

    # (2.过), (2.证毕), (2.得证)
    s = re.sub(
        r"[（(]\s*\d+\s*[.。．、]\s*(过|证毕|得证)\s*[)）]?",
        r"\1",
        s,
    )

    # Isolated sub-question markers on their own line
    s = re.sub(
        r"(?m)^\s*[（(]\s*\d+\s*[)）]\s*[.。．、]?\s*$",
        "",
        s,
    )

    # Formula block followed by orphan (1)/(2) markers
    s = re.sub(
        r"(\$\$[\s\S]*?\$\$)\s*[（(]\s*\d+\s*[)）]\s*(?:[.。．、])?",
        r"\1\n",
        s,
    )

    # Isolated "过" is usually a truncation fragment
    s = re.sub(r"(?m)^\s*过\s*$", "", s)

    return re.sub(r"\n{3,}", "\n\n", s).strip()


def clean_mojibake_tokens(text: str) -> str:
    """P19-3: Remove encoding artifacts like �A0�, �L0�, �1� from AI output."""
    if not text:
        return ""
    s = str(text)
    s = re.sub(r"�[A-Za-z0-9]+�", "", s)
    s = s.replace("�", "")
    s = s.replace(" ", " ")
    return re.sub(r"[ \t]{2,}", " ", s)


def _drop_ai_meta_sections(text: str) -> str:
    """Remove AI-only metadata sections from standard answers."""
    lines = str(text or "").splitlines()
    out: list[str] = []
    skipping = False
    meta_re = re.compile(
        r"^\s*#{1,6}\s*(?:" + "|".join(map(re.escape, _AI_META_HEADINGS)) + r")\s*[:：]?.*$"
    )
    heading_re = re.compile(r"^\s*#{1,6}\s+")
    resume_re = re.compile(r"^\s*(?:#{1,6}\s*)?(?:步骤\s*\d+|第\s*\d+\s*步|最终答案|答案|解析)\b")

    for line in lines:
        if meta_re.match(line):
            skipping = True
            continue
        if skipping:
            if heading_re.match(line) or resume_re.match(line):
                skipping = False
            else:
                continue
        if not meta_re.match(line):
            out.append(line)
    return "\n".join(out)


def _repair_inline_display_env_delimiters(text: str) -> str:
    r"""Repair $\begin{aligned}$ / $\end{aligned}$ style display-env wrappers."""
    envs = "|".join(map(re.escape, _DISPLAY_ENVS))
    s = str(text or "")
    s = re.sub(
        rf"\$\s*(\\begin\{{(?:{envs})\}}[\s\S]*?\\end\{{(?:{envs})\}})\s*\$",
        lambda m: "$$\n" + m.group(1).strip() + "\n$$",
        s,
    )
    s = re.sub(rf"\$\s*(\\begin\{{(?:{envs})\}})\s*\$", r"$$\n\1", s)
    s = re.sub(rf"\$\s*(\\end\{{(?:{envs})\}})\s*\$", r"\1\n$$", s)
    return s


def _repair_fragmented_inline_math(text: str) -> str:
    r"""Fix AI fragments such as \to$\infty$ and x $\geq$ 0."""
    s = str(text or "")
    s = re.sub(
        r"(\\(?:to|rightarrow|leftarrow|Rightarrow|Leftarrow|Leftrightarrow))\s*\$\s*([^$\s]+)\s*\$",
        lambda m: m.group(1) + m.group(2),
        s,
    )
    relation = r"\\(?:geq|leq|neq|ne|in|notin|cdot|times|to|rightarrow|approx|sim)"
    atom = r"(?:\\[A-Za-z]+|[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?)"
    rhs = r"(?:\\[A-Za-z]+|[A-Za-z0-9_{}^+\-*/().,])+"
    s = re.sub(
        rf"(?<!\$)({atom})\s*\$\s*({relation})\s*\$\s*({rhs})",
        lambda m: f"${m.group(1)} {m.group(2)} {m.group(3)}$",
        s,
    )
    return s


def _repair_triple_dollars(text: str) -> str:
    s = str(text or "")
    s = re.sub(r"\${3}([^$\n]+?)\${2}(?!\$)", r"$$\1$$", s)
    s = re.sub(r"\${3}([^$\n]+?)\$(?!\$)", r"$\1$", s)
    return re.sub(r"\${3,}", "$$", s)


def sanitize_ai_solution_markdown(text: str) -> str:
    """Normalize AI standard-answer markdown before legacy parsing/render gates."""
    if not text:
        return ""
    s = str(text).replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\x00A[2-5]", "", s)
    s = re.sub(r"\\u0000A[2-5]", "", s)
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = _drop_ai_meta_sections(s)
    s = _repair_inline_display_env_delimiters(s)
    s = _repair_fragmented_inline_math(s)
    s = _repair_triple_dollars(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def repair_split_frac_denominator(text: str) -> str:
    r"""P19-3: Fix \frac{num} with denominator on next line.

    \frac{f(x)-f(u)}
    x-u
    →
    \frac{f(x)-f(u)}{x-u}
    """
    if not text:
        return ""
    s = str(text)
    # \frac{num}\n{den}
    s = re.sub(
        r"\\frac\{([^{}]+)\}\s*\n\s*\{([^{}]+)\}",
        lambda m: rf"\frac{{{m.group(1).strip()}}}{{{m.group(2).strip()}}}",
        s, flags=re.M,
    )
    # \frac{num}\nden  (plain denominator, looks math-like)
    _math_den = r"([A-Za-z0-9_\\+\-*/^().,\s]+)"
    s = re.sub(
        rf"\\frac\{{([^{{}}]+)\}}\s*\n\s*{_math_den}\s*(?=\n|$)",
        lambda m: rf"\frac{{{m.group(1).strip()}}}{{{m.group(2).strip()}}}",
        s, flags=re.M,
    )
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def repair_broken_frac_blocks(text: str) -> str:
    """P19-2: Repair AI-generated fractured \\frac structures.

    Typical broken pattern:
      \\frac{}
      x_3-x_2
      }{
      x_3-x_1
      }

    Repaired to:
      \\frac{x_3-x_2}{x_3-x_1}
    """
    if not text:
        return ""

    s = str(text)

    # Pattern 1: \\frac{}  numerator  }{  denominator  }
    s = re.sub(
        r"\\frac\{\}\s*\n?\s*([^{}\n]+?)\s*\n?\s*\}\{\s*\n?\s*([^{}\n]+?)\s*\n?\s*\}",
        lambda m: rf"\frac{{{m.group(1).strip()}}}{{{m.group(2).strip()}}}",
        s,
        flags=re.M,
    )

    # Pattern 2: \\frac{}  numerator  }  {  denominator  }  (spaces between braces)
    s = re.sub(
        r"\\frac\{\}\s*([^{}\n]+?)\s*\}\s*\{\s*([^{}\n]+?)\s*\}",
        lambda m: rf"\frac{{{m.group(1).strip()}}}{{{m.group(2).strip()}}}",
        s,
        flags=re.M,
    )

    # Clean orphan }{ and } on their own lines
    s = re.sub(r"(?m)^\s*\}\{\s*$", "", s)
    s = re.sub(r"(?m)^\s*\}\s*$", "", s)

    return re.sub(r"\n{3,}", "\n\n", s).strip()


def repair_legacy_solution_text(text: str) -> str:
    """Repair AI-generated legacy standard answer text.

    Fixes:
      0. Broken \\frac structures (P19-2)
      1. Orphan formula tail fragments like (2.过)
      2. "最终答案： ## 步骤1" → removes orphan label
      3. Bare LaTeX lines → wraps in $$
      4. \text{选}(B) → 选 B
      5. Collapses excessive blank lines
    """
    if not text:
        return ""

    s = sanitize_ai_solution_markdown(text)

    # ── 0. Clean mojibake first ──
    s = clean_mojibake_tokens(s)
    # ── 1. Repair broken fractions ──
    s = repair_broken_frac_blocks(s)
    # ── 2. Repair split-frac denominator ──
    s = repair_split_frac_denominator(s)

    # ── 3. Clean orphan markers ──
    s = clean_orphan_problem_markers(s)

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
