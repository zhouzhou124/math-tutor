
r"""latex_repair.py -- LaTeX repair module for AI-generated math output."""

import re
import unicodedata

_KATEX_BLOCK_ENVS = {
    "aligned", "alignedat", "gathered", "cases",
    "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix",
    "array", "split", "smallmatrix",
}
_ENV_REWRITE = {"eqnarray": "aligned", "eqnarray*": "aligned"}
_KATEX_STANDALONE = {"equation", "equation*"}
_MULTILINE_ENVS = _KATEX_BLOCK_ENVS | _KATEX_STANDALONE
_INLINE_SAFE_ENVS = {"pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix", "matrix", "smallmatrix", "cases"}
_DISPLAY_ONLY_ENVS = {"aligned", "alignedat", "gathered", "array", "split", "equation", "equation*"}


def repair_latex(text: str) -> str:
    r"""Main entry point: repair all known LaTeX issues in AI-generated text."""
    if not text:
        return text
    text = _normalize_unicode(text)
    text = _repair_fraction(text)
    text = _repair_frac_missing_denom(text)
    text = _fix_double_dollar_equations(text)
    text = _close_unclosed_environments(text)
    text = _unwrap_nested_math_environments(text)
    text = _convert_align_to_aligned(text)
    text = _fix_leaked_block_environments(text)
    text = _repair_orphaned_left_right(text)
    text = _fix_left_right(text)
    text = _balance_dollar_signs(text)
    return text


def _normalize_unicode(text):
    if not text:
        return text
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\ufffd", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    _fw = {ord("+"): "+", ord("-"): "-", ord("="): "=", ord("<"): "<", ord(">"): ">", ord("("): "(", ord(")"): ")", ord("["): "[", ord("]"): "]", ord("{"): "{", ord("}"): "}", ord("*"): "*", ord("/"): "/"}
    text = text.translate(_fw)
    _map = {"\u2260": r"\ne", "\u2264": r"\le", "\u2265": r"\ge", "\u00d7": r"\times", "\u00f7": r"\div", "\u00b1": r"\pm", "\u221e": r"\infty", "\u2202": r"\partial", "\u2211": r"\sum", "\u222b": r"\int", "\u2261": r"\equiv", "\u2248": r"\approx", "\u2192": r"\rightarrow", "\u21d2": r"\Rightarrow", "\u2200": r"\forall", "\u2203": r"\exists", "\u2208": r"\in"}
    for u, l in _map.items():
        text = text.replace(u, l)
    return text


def _repair_fraction(text):
    """Reattach orphaned denominator {..} to bare \\frac{..}."""
    if not text or r"\frac" not in text:
        return text
    frac_re = re.compile(r'\\frac(\{[^}]*\})([^{])')
    def _recover(m):
        body, after = m.group(1), m.group(2)
        rest = text[m.end()-1:]
        dm = re.search(r'\{([^}]{1,100})\}', rest)
        if dm and dm.start() < 200:
            return r"\frac" + body + dm.group(0) + after
        return m.group(0)
    return frac_re.sub(_recover, text)

def _repair_frac_missing_denom(text):
    r"""Detect \frac{num} without {den} and insert {?} placeholder.

    KaTeX crashes on \frac with only one argument. This detects the
    pattern and adds a safe {?} so rendering degrades gracefully.
    """
    if not text or "\\frac" not in text:
        return text
    # \frac{num} followed by optional whitespace then a non-{ char
    # The \s* absorbs whitespace so \frac{1} {2} is NOT matched
    pattern = re.compile(r"\\frac(\{[^}]*\})\s*([^{])")
    return pattern.sub(r"\\frac\1{?}\2", text)

def _repair_orphaned_left_right(text):
    """Remove orphaned \\right commands without preceding \\left."""
    if not text:
        return text
    segs = re.split(r'(\$\$.*?\$\$)', text, flags=re.DOTALL)
    res = []
    for s in segs:
        if s.startswith('$$'):
            res.append(s); continue
        lc = len(re.findall(r'\\left(?=\s*[(\[|{\\.])', s))
        rc = len(re.findall(r'\\right(?=\s*[)\]|}\\.])', s))
        if rc > lc:
            for _ in range(rc - lc):
                m = re.search(r'\\right(?:\s*[)\]|}\\.])', s)
                if m:
                    s = s[:m.start()] + s[m.end():]
        res.append(s)
    return ''.join(res)


def _fix_double_dollar_equations(text):
    if not text:
        return text
    return re.sub(r'^\$\$\s*$', '', text, flags=re.MULTILINE)


def _close_unclosed_environments(text):
    if not text:
        return text
    be = re.compile(r"\\begin\{(\w+\*?)\}")
    en = re.compile(r"\\end\{(\w+\*?)\}")
    stack = [(m.group(1), m.start()) for m in be.finditer(text)]
    uc = list(stack)
    for m in en.finditer(text):
        for i in range(len(uc)-1, -1, -1):
            if uc[i][0] == m.group(1):
                uc.pop(i); break
    if not uc:
        return text
    return text + ''.join(f"\\end{{{e}}}" for e, _ in reversed(uc))


def _unwrap_nested_math_environments(text):
    if not text:
        return text
    text = re.sub(r'\$\$\s*\$\$', '', text)
    return re.sub(r'\$\$\s*\$\$(.*?)\$\$\s*\$\$', r'$$\1$$', text, flags=re.DOTALL)


def _convert_align_to_aligned(text):
    if not text:
        return text
    for env in ("align*", "align", "gather*", "gather", "eqnarray*", "eqnarray"):
        bt, et = f"\\begin{{{env}}}", f"\\end{{{env}}}"
        if bt not in text:
            continue
        target = _ENV_REWRITE.get(env, "aligned")
        pat = re.compile(re.escape(bt) + r'(.*?)' + re.escape(et), re.DOTALL)
        res, last = [], 0
        for m in pat.finditer(text):
            before = text[:m.start()]
            dd = before.rfind("$$")
            dde = before.rfind("$$", dd+1) if dd >= 0 else -1
            res.append(text[last:m.start()])
            c = m.group(1)
            if dd >= 0 and (dde < 0 or dd > dde):
                res.append(f"\\begin{{{target}}}{c}\\end{{{target}}}")
            else:
                res.append(f"$$\n\\begin{{{target}}}{c}\\end{{{target}}}\n$$")
            last = m.end()
        if res:
            res.append(text[last:])
            text = "".join(res)
    return text


def _fix_leaked_block_environments(text):
    if not text:
        return text
    segs = re.split(r'(\$\$.*?\$\$)', text, flags=re.DOTALL)
    for env in _DISPLAY_ONLY_ENVS:
        bt, et = f"\\begin{{{env}}}", f"\\end{{{env}}}"
        for i, s in enumerate(segs):
            if s.startswith("$$") or bt not in s:
                continue
            bp = re.compile(re.escape(bt) + r'(.*?)' + re.escape(et), re.DOTALL)
            for m in bp.finditer(s):
                segs[i] = s[:m.start()] + f"$$\n{m.group(0)}\n$$" + s[m.end():]
                s = segs[i]
        text = "".join(segs)
    return text


def _fix_left_right(text):
    if not text:
        return text
    lr = re.compile(r'\\left(?=\s*[(\[|{\\.]|\s*\\langle|\s*\\lfloor|\s*\\lceil)')
    rr = re.compile(r'\\right(?=\s*[)\]|}\\.]|\s*\\rangle|\s*\\rfloor|\s*\\rceil)')
    lc = len(lr.findall(text))
    rc = len(rr.findall(text))
    if lc <= rc:
        return text
    parts, last, depth = [], 0, 0
    for m in lr.finditer(text):
        depth += 1
        if depth > rc:
            pos = m.end()
            nd = text.find("$$", pos)
            if nd >= 0:
                parts.append(text[last:nd])
                parts.append(r" \right.")
                last = nd
            else:
                parts.append(text[last:pos])
                parts.append(r"\right.")
                parts.append(text[pos:])
                last = len(text)
    if last < len(text):
        parts.append(text[last:])
    return "".join(parts) if parts else text


def _balance_dollar_signs(text):
    if not text:
        return text
    dbs = re.findall(r'\$\$.*?\$\$', text, re.DOTALL)
    t = text
    for i, b in enumerate(dbs):
        t = t.replace(b, f"\x00DD{i}\x00", 1)
    if t.count("$") % 2:
        idx = t.rfind("$")
        if idx >= 0:
            t = t[:idx] + t[idx+1:]
    for i, b in enumerate(dbs):
        t = t.replace(f"\x00DD{i}\x00", b, 1)
    if t.count("$$") % 2:
        idx = t.rfind("$$")
        if idx >= 0:
            t = t[:idx] + t[idx+2:]
    return t


def has_unclosed_environments(text):
    if not text:
        return False
    be = re.findall(r'\\begin\{(\w+\*?)\}', text)
    en = re.findall(r'\\end\{(\w+\*?)\}', text)
    bc, ec = {}, {}
    for b in be:
        bc[b] = bc.get(b, 0) + 1
    for e in en:
        ec[e] = ec.get(e, 0) + 1
    return any(ec.get(e, 0) != c for e, c in bc.items())


def has_nested_math(text):
    if not text:
        return False
    if re.search(r'\$\$\$', text):
        return True
    be = "|".join(_MULTILINE_ENVS)
    p = re.compile(r"(?<!\$)\$(?!\$)[^$\n]*?\\begin\{(?:" + be + r")\}")
    return bool(re.search(p, text))


def _repair_math_spacing(text):
    r"""Fix common math-mode spacing issues that cause rendering failures.

    Repairs:
    1. Bare \left without delimiter ? \left.
    2. Bare \right without delimiter ? \right.
    3. Space between _ or ^ and single-char argument: x _ i ? x_{i}
    4. Normalize space before brace in scripts: _ { ? _{, ^ { ? ^{
    """
    if not text:
        return text

    # 1-2: Bare \left or \right ? not followed by any valid delimiter
    # Valid \left delimiters: ( [ { | . \langle \lfloor \lceil \
    text = re.sub(r'\\left(?![\s]*[(\[{|.\\]|\\langle|\\lfloor|\\lceil)', r'\\left.', text)
    text = re.sub(r'\\right(?![\s]*[)\]}|.\\]|\\rangle|\\rfloor|\\rceil)', r'\\right.', text)

    # 3: Fix _ ^ spacing inside math segments
    def _fix_scripts(body):
        # x _ i ? x_{i}
        body = re.sub(r'([a-zA-Z0-9\\)\]}])\s+_\s+([a-zA-Z0-9])', r'\1_{\2}', body)
        body = re.sub(r'([a-zA-Z0-9\\)\]}])\s+\^\s+([a-zA-Z0-9])', r'\1^{\2}', body)
        # Normalize _ { ? _{  and  ^ { ? ^{
        body = re.sub(r'_\s+\{', r'_{', body)
        body = re.sub(r'\^\s+\{', r'^{', body)
        return body

    # Process display math: $$...$$
    segs = re.split(r'(\$\$.*?\$\$)', text, flags=re.DOTALL)
    res = []
    for s in segs:
        if s.startswith('$$'):
            res.append(_fix_scripts(s))
        else:
            # Process inline math: $...$
            inline_segs = re.split(r'(\$[^$\n]{1,2000}?\$)', s)
            inline_res = []
            for i, iseg in enumerate(inline_segs):
                if iseg.startswith('$') and iseg.endswith('$') and len(iseg) > 1:
                    # Keep delimiters, fix interior
                    inner = iseg[1:-1]
                    fixed_inner = _fix_scripts(inner)
                    inline_res.append('$' + fixed_inner + '$')
                else:
                    inline_res.append(iseg)
            res.append(''.join(inline_res))
    return ''.join(res)


def repair_latex_strict(text: str) -> str:
    r"""Stricter LaTeX repair with spacing fixes and validation pass.

    Extends repair_latex() with:
    - Math-mode spacing fixes (_repair_math_spacing)
    - Second-pass repair if issues remain after first pass
    """
    if not text:
        return text

    text = repair_latex(text)
    text = _repair_math_spacing(text)

    # Second pass if issues remain after first repair
    if has_unclosed_environments(text) or has_nested_math(text):
        text = repair_latex(text)

    return text
