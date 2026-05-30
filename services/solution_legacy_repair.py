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


def _repair_mathrm_differential(text: str) -> str:
    r"""Fix stripped \mathrm{d}x patterns: mathrmdt → \mathrm{d}t.

    Only matches the specific stripped forms mathrmdt/mathrmdu/mathrmdx/mathrmdy/mathrmdz.
    Valid \mathrm{d}t is not modified (negative lookbehind).
    """
    s = str(text or "")
    s = re.sub(r'(?<!\\)mathrmd([txuyz])', r'\\mathrm{d}\1', s)
    return s


_GREEK_CORRUPTION_MAP = {
    "alphas": "alpha", "betas": "beta", "gammas": "gamma",
    "deltas": "delta", "epsilons": "epsilon", "etas": "eta",
    "thetas": "theta", "iotas": "iota", "kappas": "kappa",
    "lambdas": "lambda", "mus": "mu", "nus": "nu",
    "xis": "xi", "pis": "pi", "rhos": "rho",
    "sigmas": "sigma", "taus": "tau", "upsilons": "upsilon",
    "phis": "phi", "chis": "chi", "psis": "psi",
    "omegas": "omega",
    "Gammas": "Gamma", "Deltas": "Delta", "Thetas": "Theta",
    "Lambdas": "Lambda", "Xis": "Xi", "Pis": "Pi",
    "Sigmas": "Sigma", "Upsilons": "Upsilon", "Phis": "Phi",
    "Psis": "Psi", "Omegas": "Omega",
    "varphis": "varphi", "varepsilons": "varepsilon",
    "varthetas": "vartheta", "varkappas": "varkappa",
    "varrhos": "varrho",
    "alph": "alpha", "bet": "beta", "gam": "gamma",
    "del": "delta", "eps": "epsilon", "the": "theta",
    "lam": "lambda", "sig": "sigma", "ome": "omega",
}
_GREEK_CORRUPTION_RE = re.compile(
    r'\\(' + '|'.join(map(re.escape, sorted(_GREEK_CORRUPTION_MAP.keys(), key=len, reverse=True))) + r')(?=[^A-Za-z]|$)'
)


def _repair_corrupted_greek_commands(text: str) -> str:
    """Fix LLM-corrupted Greek commands in legacy text: \\alphas → \\alpha."""
    def _replace(m: re.Match) -> str:
        corrupted = m.group(1)
        fixed = _GREEK_CORRUPTION_MAP.get(corrupted)
        if fixed and fixed != corrupted:
            return '\\' + fixed
        return m.group(0)
    return _GREEK_CORRUPTION_RE.sub(_replace, text)


# P32.1: Unicode Greek character corruption
# \varφ → \varphi, \varϕ → \varphi, \φ → \phi, \λ → \lambda, etc.
_UNICODE_GREEK_MAP = {
    "φ": "phi", "ϕ": "phi", "α": "alpha", "β": "beta", "γ": "gamma",
    "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu",
    "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau",
    "υ": "upsilon", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta", "Λ": "Lambda",
    "Ξ": "Xi", "Π": "Pi", "Σ": "Sigma", "Υ": "Upsilon",
    "Φ": "Phi", "Ψ": "Psi", "Ω": "Omega",
}
# Match \var<char> where char is Unicode Greek
_VAR_UNICODE_RE = re.compile(r'\\var([φϕα-ωΑ-Ω])')
# Match \<unicode Greek> not part of a longer ASCII command
_UNICODE_GREEK_CMD_RE = re.compile(r'\\([φϕα-ωΑ-Ω])(?=[^a-zA-Z]|$)')


def _repair_unicode_greek_commands(text: str) -> str:
    """P32.1: Fix Unicode Greek in LaTeX commands: \\varφ → \\varphi, \\φ → \\phi."""
    s = str(text or "")

    def _fix_var(m: re.Match) -> str:
        ch = m.group(1)
        name = _UNICODE_GREEK_MAP.get(ch)
        if name:
            return '\\var' + name
        return m.group(0)

    def _fix_bare(m: re.Match) -> str:
        ch = m.group(1)
        name = _UNICODE_GREEK_MAP.get(ch)
        if name:
            return '\\' + name
        return m.group(0)

    s = _VAR_UNICODE_RE.sub(_fix_var, s)
    s = _UNICODE_GREEK_CMD_RE.sub(_fix_bare, s)
    return s


# P32.1: Bare \mathrm variants for differential
# mathrmd t, mathrm d t, mathrm dt → \mathrm{d}t
_BARE_MATHRM_D_RE = re.compile(
    r'(?<!\\)mathrm\s*d\s*([txuyz])(?=[^a-zA-Z]|$)'
)


def _repair_bare_mathrm_differential(text: str) -> str:
    """P32.1: Fix bare \\mathrm d variants: mathrm dt → \\mathrm{d}t."""
    s = str(text or "")
    # Only match when not already properly formed (\mathrm{d}x)
    s = _BARE_MATHRM_D_RE.sub(r'\\mathrm{d}\1', s)
    return s


# P32.2: Standalone Unicode Greek normalization in math contexts
_MATH_GREEK_RE = re.compile(
    r'(?<![\\a-zA-Z])[φϕαβγδεζηθικλμνξπρστυχψωΑ-Ω](?=[\s]*[\(\)\[\]{}^_=<>/\+\-\*]|$)'
)


def _normalize_unicode_greek_math_symbols(text: str) -> str:
    """P32.2: Normalize standalone Unicode Greek in math contexts.

    In formula.latex / latex blocks: direct replacement.
    In body_markdown / standard_answer: only math-context patterns.
    Preserves legal \\varphi / \\phi (backslash prefix).
    """
    s = str(text or "")

    def _replace(m: re.Match) -> str:
        ch = m.group(0)
        name = _UNICODE_GREEK_MAP.get(ch)
        if name and name in ("phi", "varphi"):
            return '\\varphi'
        return '\\' + name if name else ch

    s = _MATH_GREEK_RE.sub(_replace, s)
    return s


def _normalize_unicode_greek_in_latex(text: str) -> str:
    """P32.2: Direct Unicode Greek → LaTeX in formula.latex / latex blocks.

    Replaces all standalone Unicode Greek characters unconditionally.
    Preserves legal \\varphi / \\phi (backslash prefix).
    """
    s = str(text or "")

    def _replace(m: re.Match) -> str:
        ch = m.group(1)
        name = _UNICODE_GREEK_MAP.get(ch)
        if name and name in ("phi", "varphi"):
            return '\\varphi'
        return '\\' + name if name else ch

    s = re.sub(r'(?<![\\a-zA-Z])([φϕα-ωΑ-Ω])', _replace, s)
    return s


# P32.2.1: Bare differential after closing paren or function call
# Matches: )dy, )dx, )dt, )du, )dz  and  \varphi(y)dy, f(t)dt, etc.
# Does NOT match inside words like "study", "ready", "today".
_BARE_DIFF_AFTER_PAREN_RE = re.compile(
    r'(?<!\\mathrm\{d\})(?<!\\,\\mathrm\{d\})'
    r'(?<=[\)])\s*d([xyztu])\b'
    r'(?![a-zA-Z])'
)
# Matches: f(t)dt, F(u)du, \varphi(x)dx — bare d after ) with no space
_BARE_DIFF_FUNC_CALL_RE = re.compile(
    r'(?<!\\mathrm\{d\})(?<!\\,\\mathrm\{d\})'
    r'(?<=[a-zA-Z\\])\)'
    r'\s*d([xyztu])\b'
    r'(?![a-zA-Z])'
)


def _repair_bare_differential_in_math_context(text: str) -> str:
    r"""P32.2.1: Fix bare dy/dx/dt/du/dz after ) in math context.

    Converts:
      )dy → )\,\\mathrm{d}y
      \\varphi(y)dy → \\varphi(y)\\,\\mathrm{d}y
      f(t)dt → f(t)\\,\\mathrm{d}t

    Preserves:
      study, ready, today (words containing dy/dt)
      legal \\,\\mathrm{d}y (already repaired)
    """
    s = str(text or "")
    s = _BARE_DIFF_AFTER_PAREN_RE.sub(r'\\,\\mathrm{d}\1', s)
    return s


def _repair_bare_differential(text: str) -> str:
    r"""Fix bare dx/dt in integral context → \mathrm{d}x / \mathrm{d}t.

    Only repairs inside $$...$$ or $...$ math blocks where bare d before
    a variable is almost certainly a differential, not a plain letter.
    """
    s = str(text or "")

    def _fix_in_math(m: re.Match) -> str:
        block = m.group(0)
        # Bare d + single letter, not already \mathrm{d}
        block = re.sub(
            r'(?<![\\A-Za-z])d([xyztruvws])\b',
            r'\\mathrm{d}\1',
            block,
        )
        return block

    # Fix inside $$...$$ display math
    s = re.sub(r'\$\$[\s\S]*?\$\$', _fix_in_math, s)
    # Fix inside $...$ inline math (non-greedy)
    s = re.sub(r'(?<!\$)\$(?!\$)[^$\n]+\$(?!\$)', _fix_in_math, s)
    return s


# P36: Bare \dx / \dy / \dt — backslash + bare d + variable, NOT a LaTeX command
# Matches \dx, \dy, \dt, \du, \dz but NOT \delta, \dim, \det, etc.
_BARE_BACKSLASH_DIFF_RE = re.compile(
    r'\\d([xyztu])(?![a-zA-Z])'
)


def _repair_backslash_bare_differential(text: str) -> str:
    r"""P36: Fix \dx → \,\mathrm{d}x, \dy → \,\mathrm{d}y, etc.

    Matches \\dx, \\dy, \\dt, \\du, \\dz that are NOT part of longer
    LaTeX commands (e.g. \\delta, \\dim, \\det are preserved).
    """
    s = str(text or "")
    return _BARE_BACKSLASH_DIFF_RE.sub(r'\\,\\mathrm{d}\1', s)


# P36: Consecutive bare differentials — dxdy, dydx, dtdx, etc.
# Only matches inside math context (after ) or in LaTeX fields).
_CONSECUTIVE_BARE_DIFF_RE = re.compile(
    r'(?<![\\a-zA-Z])d([xyztu])d([xyztu])(?![a-zA-Z])'
)


def _repair_consecutive_bare_differential(text: str) -> str:
    r"""P36: Fix dxdy → \,\mathrm{d}x\,\mathrm{d}y, dydx → \,\mathrm{d}y\,\mathrm{d}x, etc."""
    s = str(text or "")
    return _CONSECUTIVE_BARE_DIFF_RE.sub(r'\\,\\mathrm{d}\1\\,\\mathrm{d}\2', s)


_MIN_ALIGN_LEN = 120
_ALIGN_MAX_EQ = 6


def _repair_long_formula_aligned(text: str) -> str:
    r"""Wrap long multi-= display formulas in \begin{aligned}...\end{aligned}.

    If a $$...$$ block is long (>120 chars) and contains multiple = signs,
    split at = and wrap in aligned environment for proper line-breaking.
    Skips blocks that already contain \begin{...} or \left.
    """
    s = str(text or "")

    def _align_block(m: re.Match) -> str:
        block = m.group(0)
        inner = block[2:-2].strip()  # strip $$
        if not inner:
            return block
        # Skip if already has environment or left/right
        if r'\begin{' in inner or r'\left' in inner:
            return block
        # Count = signs (not inside \text{}, not ==, not \neq, etc.)
        clean = re.sub(r'\\text\{[^}]*\}', '', inner)
        clean = re.sub(r'(?:\\neq|\\ne|\\geq|\\leq|\\approx|\\equiv|==)', '', clean)
        eq_count = clean.count('=')
        if eq_count < 2 or len(inner) < _MIN_ALIGN_LEN:
            return block
        if eq_count > _ALIGN_MAX_EQ:
            return block
        # Split at = and wrap in aligned
        parts = re.split(r'\s*=\s*', inner, maxsplit=_ALIGN_MAX_EQ)
        if len(parts) < 2:
            return block
        lines = [parts[0].strip()]
        for part in parts[1:]:
            lines.append("&= " + part.strip())
        aligned = r'\begin{aligned}' + ' \\\\\n'.join(lines) + r'\end{aligned}'
        return '$$\n' + aligned + '\n$$'

    return re.sub(r'\$\$[\s\S]*?\$\$', _align_block, s)


def _repair_nested_inline_math_in_display(text: str) -> str:
    """P37.5: Remove $...$ wrappers inside $$...$$ or \\[...\\] display blocks.

    AI sometimes outputs:  $$ y = $C_1$ e^x + $C_2$ e^{2x} $$
    Should be:             $$ y = C_1 e^x + C_2 e^{2x} $$

    Only operates inside display math blocks — normal text $...$ untouched.
    """
    def _strip_inner_dollars(block: str) -> str:
        # Remove $...$ wrappers inside the block, keeping the content
        s = re.sub(r'\$([^$\n]+?)\$', r'\1', block)
        # Also handle multiline $...$ (with DOTALL)
        s = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', r'\1', s, flags=re.DOTALL)
        # Strip $ adjacent to \begin{...} or \end{...}
        s = re.sub(r'\\(begin\{[^}]+\})\$', r'\\\1', s)
        s = re.sub(r'\$\\(end\{[^}]+\})', r'\\\1', s)
        # Strip standalone $ on their own lines
        s = re.sub(r'(?m)^\s*\$\s*$', '', s)
        return s

    def _fix_display_dd(match: re.Match) -> str:
        return _strip_inner_dollars(match.group(0))

    def _fix_display_bracket(match: re.Match) -> str:
        return _strip_inner_dollars(match.group(0))

    s = re.sub(r'\$\$[\s\S]*?\$\$', _fix_display_dd, text)
    s = re.sub(r'\\\[[\s\S]*?\\\]', _fix_display_bracket, s)
    return s


_CHINESE_LINE_STARTS = (
    "原非齐次", "原齐次", "因此", "于是", "其中", "结论", "步骤",
    "##", "**步骤", "**最终", "**解", "**证明", "综上", "故",
    "所以", "即证", "得证", "证毕", "将", "代入", "由题",
)


def _repair_unclosed_display_math_blocks(text: str) -> str:
    """P37.5: Fix unclosed $$ display math blocks.

    Handles two common AI output patterns:
    1. $$ opens but Chinese text starts before closing $$
       → insert $$ before the Chinese text line
    2. Odd number of $$ in the entire text
       → append $$ at the end

    Only operates on legacy markdown — never used for question bank rendering.
    """
    lines = text.split('\n')
    result: list[str] = []
    in_display = False

    for line in lines:
        stripped = line.strip()
        # Count $$ in this line (each $$ toggles state)
        dd_count = stripped.count('$$')

        if in_display:
            if dd_count % 2 == 1:
                # Closing $$ found on this line
                in_display = False
            else:
                # Still inside display block — check if Chinese text starts
                is_chinese_start = any(stripped.startswith(m) for m in _CHINESE_LINE_STARTS)
                if is_chinese_start and stripped:
                    # Close the display block before this line
                    result.append('$$')
                    result.append('')
                    in_display = False
        else:
            if dd_count % 2 == 1:
                # Opening $$ found (odd count on this line)
                in_display = True

        result.append(line)

    # If still open at the end, close it
    if in_display:
        result.append('$$')

    return '\n'.join(result)


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

    # ── P30.4: Fix stripped differential commands ──
    s = _repair_mathrm_differential(s)

    # ── P32: Fix corrupted Greek commands ──
    s = _repair_corrupted_greek_commands(s)

    # ── P32.1: Fix Unicode Greek commands (\varφ → \varphi) ──
    s = _repair_unicode_greek_commands(s)

    # ── P32.1: Fix bare \mathrm d variants ──
    s = _repair_bare_mathrm_differential(s)

    # ── P32.2: Normalize standalone Unicode Greek in math contexts ──
    s = _normalize_unicode_greek_math_symbols(s)

    # ── P32.2.1: Fix bare dy/dx/dt after ) in math context ──
    s = _repair_bare_differential_in_math_context(s)

    # ── P32: Fix bare dx/dt in integral context ──
    s = _repair_bare_differential(s)

    # ── P36: Fix \dx → \,\mathrm{d}x ──
    s = _repair_backslash_bare_differential(s)

    # ── P36: Fix dxdy → \,\mathrm{d}x\,\mathrm{d}y ──
    s = _repair_consecutive_bare_differential(s)

    # ── P32: Wrap long multi-= display formulas in aligned ──
    s = _repair_long_formula_aligned(s)

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

    # ── P37.5: Fix nested $ inside $$ display blocks ──
    s = _repair_nested_inline_math_in_display(s)

    # ── P37.5: Fix unclosed $$ display blocks ──
    s = _repair_unclosed_display_math_blocks(s)

    # ── 4. Wrap bare formula lines ──
    s = _wrap_bare_formula_lines(s)

    # ── 5. Collapse excessive blank lines ──
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s.strip()


# ── P37.6: Extra aggressive repair helpers ──

def _strip_orphan_display_close(text: str) -> str:
    """Strip orphan $$ close markers (lines that are just $$ with no matching open).

    Uses a state machine: toggles between open/closed on standalone $$ lines.
    Only removes standalone $$ that would close when not open (orphan closes).
    Inline $$ (mixed with other content) always kept.
    """
    lines = text.split('\n')
    result: list[str] = []
    in_display = False
    for line in lines:
        stripped = line.strip()
        if stripped == '$$':
            if in_display:
                # Closing a display block — keep
                in_display = False
                result.append(line)
            else:
                # Opening a display block — keep (may be paired later)
                in_display = True
                result.append(line)
        else:
            # Non-standalone $$ lines: count to track state
            dd_count = stripped.count('$$')
            if dd_count % 2 == 1:
                in_display = not in_display
            result.append(line)
    return '\n'.join(result)


def _collapse_empty_display_blocks(text: str) -> str:
    """Collapse $$\n$$ empty display blocks."""
    return re.sub(r'\$\$\s*\n\s*\$\$', '', text)


def _wrap_bare_aligned_blocks(text: str) -> str:
    r"""Wrap bare \begin{aligned}...\end{aligned} blocks in $$...$$.

    AI sometimes outputs \begin{aligned}...\end{aligned} without $$ wrapping.
    """
    def _wrap_match(m: re.Match) -> str:
        return '$$\n' + m.group(0) + '\n$$'

    # Match \begin{aligned}...\end{aligned} not already inside $$...$$
    # Use negative lookbehind/lookahead for $$
    return re.sub(
        r'(?<!\$\$)\s*(\\begin\{aligned\}[\s\S]*?\\end\{aligned\})\s*(?!\$\$)',
        _wrap_match,
        text,
    )


def _strip_orphan_display_after_inline_math(text: str) -> str:
    """Remove standalone $$ that appears right after a line ending with $.

    Pattern: inline math ends with $, then $$ on next line is orphan.
    """
    lines = text.split('\n')
    result: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '$$' and result:
            prev = result[-1].rstrip()
            if prev.endswith('$') and not prev.endswith('$$'):
                # Previous line ends with $ (inline math close) — skip this orphan $$
                continue
        result.append(line)
    return '\n'.join(result)


def repair_legacy_solution_text_aggressive(text: str) -> str:
    """P37.6: Aggressive legacy repair with swapped repair order.

    Key difference from repair_legacy_solution_text: runs
    _repair_unclosed_display_math_blocks BEFORE _repair_nested_inline_math_in_display.
    Rationale: unclosed $$ blocks prevent the nested-inline regex from finding
    complete $...$ patterns.

    Also strips orphan $$ close markers and collapses empty display blocks.
    """
    if not text:
        return ""

    # First try normal repair
    normal = repair_legacy_solution_text(text)
    from services.solution_quality import has_broken_latex_fragments, count_broken_latex_fragments
    if not has_broken_latex_fragments(normal):
        return normal

    # Normal repair still has broken LaTeX — try with swapped order
    s = sanitize_ai_solution_markdown(text)

    # P37.6: Pre-preprocessing cleanup on raw text
    s = _strip_orphan_display_after_inline_math(s)
    s = _wrap_bare_aligned_blocks(s)

    # Same pre-processing as normal repair
    s = _repair_mathrm_differential(s)
    s = _repair_corrupted_greek_commands(s)
    s = _repair_unicode_greek_commands(s)
    s = _repair_bare_mathrm_differential(s)
    s = _normalize_unicode_greek_math_symbols(s)
    s = _repair_bare_differential_in_math_context(s)
    s = _repair_bare_differential(s)
    s = _repair_backslash_bare_differential(s)
    s = _repair_consecutive_bare_differential(s)
    s = _repair_long_formula_aligned(s)
    s = clean_mojibake_tokens(s)
    s = repair_broken_frac_blocks(s)
    s = repair_split_frac_denominator(s)
    s = clean_orphan_problem_markers(s)
    s = re.sub(
        r"最终答案\s*[:：]\s*(?=\s*#{1,6}\s*步骤\s*\d+)",
        "", s, flags=re.I,
    )
    s = re.sub(
        r"(?m)^\s*最终答案\s*[:：]\s*$\n(?=\s*(?:#{1,6}\s*)?步骤\s*\d+)",
        "", s, flags=re.I,
    )
    s = re.sub(r"(?m)^\s*#{1,6}\s*(步骤\s*\d+\s*[:：]?)", r"\1", s)
    s = normalize_final_choice_text(s)

    # ── P37.6: Multi-pass repair for complex broken patterns ──
    # Pass 0a: strip orphan $$ after inline math (prev line ends with $)
    s = _strip_orphan_display_after_inline_math(s)
    # Pass 0b: wrap bare \begin{aligned}...\end{aligned} in $$...$$
    s = _wrap_bare_aligned_blocks(s)
    # Pass 1: repair unclosed (pairs orphan $$ with later $$)
    s = _repair_unclosed_display_math_blocks(s)
    # Pass 2: collapse empty display blocks created by pairing
    s = _collapse_empty_display_blocks(s)
    # Pass 3: strip orphan close markers (after empty blocks removed)
    s = _strip_orphan_display_close(s)
    # Pass 4: repair unclosed again (in case stripping revealed new unclosed)
    s = _repair_unclosed_display_math_blocks(s)
    # Pass 5: nested inline math (after display structure is clean)
    s = _repair_nested_inline_math_in_display(s)

    # ── Final cleanup ──
    # Do NOT run _wrap_bare_formula_lines here — it re-wraps bare \begin{aligned}
    # lines that were just fixed by the multi-pass repair, breaking them again.
    s = re.sub(r"\n{3,}", "\n\n", s)

    result = s.strip()

    # Return whichever is better (compare broken fragment counts)
    result_count = count_broken_latex_fragments(result)
    if result_count == 0:
        return result

    normal_count = count_broken_latex_fragments(normal)
    if result_count < normal_count:
        return result

    # Normal is same or better
    return normal
