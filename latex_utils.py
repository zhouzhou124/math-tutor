"""
latex_utils.py — LaTeX 结构化渲染引擎

结构化管道: LLM JSON → Pydantic validate → render_structured → st.latex / st.markdown
不再需要 regex 修复链（latex_repair, math_sanitizer 已退役）。
"""

import re
from dataclasses import dataclass, field
from latex_normalizer import normalize_latex_style, is_normalized, validate_normalization
from math_structure_validator import validate as validate_structure, ValidationReport


# ═══════════════════════════════════════════════
# 1. 括号匹配检查
# ═══════════════════════════════════════════════

# \left \right 可配对的分隔符映射
_LEFT_RIGHT_PAIRS = {
    '(': ')', ')': '(',
    '[': ']', ']': '[',
    '{': '}', '}': '{',
    '|': '|',
    '.': '.',       # \left. \right. 不可见分隔符
    '\\langle': '\\rangle',
    '\\rangle': '\\langle',
    '\\lfloor': '\\rfloor',
    '\\rfloor': '\\lfloor',
    '\\lceil': '\\rceil',
    '\\rceil': '\\lceil',
    '\\{': '\\}',
    '\\}': '\\{',
}


@dataclass
class BracketReport:
    """括号匹配检查报告"""
    valid: bool = True
    braces: dict = field(default_factory=lambda: {"open": 0, "close": 0, "depth": 0})
    parens: dict = field(default_factory=lambda: {"open": 0, "close": 0, "depth": 0})
    brackets: dict = field(default_factory=lambda: {"open": 0, "close": 0, "depth": 0})
    left_right: dict = field(default_factory=lambda: {"left": 0, "right": 0, "unpaired": []})
    issues: list = field(default_factory=list)


def check_brackets(s: str) -> BracketReport:
    """
    检查字符串中所有括号的配对情况。

    检查项:
      - {} 大括号（LaTeX 参数分隔符）
      - () 小括号
      - [] 方括号
      - \\left ... \\right 配对

    返回 BracketReport，包含每种括号的统计和问题列表。
    """
    report = BracketReport()

    if not s:
        return report

    # ── {} 检查 ──
    brace_depth = 0
    for i, c in enumerate(s):
        if c == '{' and (i == 0 or s[i-1] != '\\'):
            brace_depth += 1
            report.braces["open"] += 1
        elif c == '}' and (i == 0 or s[i-1] != '\\'):
            brace_depth -= 1
            report.braces["close"] += 1
            if brace_depth < 0:
                report.issues.append(f"第{i}位: 多余的 '}}' (深度={brace_depth})")
                report.valid = False
    report.braces["depth"] = brace_depth
    if brace_depth > 0:
        report.issues.append(f"缺少 {brace_depth} 个 '}}'")
        report.valid = False
    elif brace_depth < 0:
        report.issues.append(f"缺少 {-brace_depth} 个 '{{'")
        report.valid = False

    # ── () 检查 ──
    paren_depth = 0
    for i, c in enumerate(s):
        if c == '(' and (i == 0 or s[i-1] != '\\'):
            paren_depth += 1
            report.parens["open"] += 1
        elif c == ')' and (i == 0 or s[i-1] != '\\'):
            paren_depth -= 1
            report.parens["close"] += 1
            if paren_depth < 0:
                report.issues.append(f"第{i}位: 多余的 ')' (深度={paren_depth})")
                report.valid = False
    report.parens["depth"] = paren_depth
    if paren_depth > 0:
        report.issues.append(f"缺少 {paren_depth} 个 ')'")
        report.valid = False
    elif paren_depth < 0:
        report.issues.append(f"缺少 {-paren_depth} 个 '('")
        report.valid = False

    # ── [] 检查 ──
    bracket_depth = 0
    for i, c in enumerate(s):
        if c == '[' and (i == 0 or s[i-1] != '\\'):
            bracket_depth += 1
            report.brackets["open"] += 1
        elif c == ']' and (i == 0 or s[i-1] != '\\'):
            bracket_depth -= 1
            report.brackets["close"] += 1
            if bracket_depth < 0:
                report.issues.append(f"第{i}位: 多余的 ']' (深度={bracket_depth})")
                report.valid = False
    report.brackets["depth"] = bracket_depth
    if bracket_depth > 0:
        report.issues.append(f"缺少 {bracket_depth} 个 ']'")
        report.valid = False
    elif bracket_depth < 0:
        report.issues.append(f"缺少 {-bracket_depth} 个 '['")
        report.valid = False

    # ── \left \right 检查 ──
    left_count = len(re.findall(r'\\left(?=[(\[{|.\\])', s))
    right_count = len(re.findall(r'\\right(?=[)\]}|.\\])', s))
    report.left_right["left"] = left_count
    report.left_right["right"] = right_count

    if left_count != right_count:
        report.issues.append(
            f"\\left 有 {left_count} 个, \\right 有 {right_count} 个 (不匹配)"
        )
        report.valid = False

    # 提取 \leftX ... \rightY 配对并检查 X/Y 是否兼容
    left_right_pairs = re.findall(
        r'\\left([(\[{|.\\]|\\langle|\\lfloor|\\lceil|\\rangle|\\rfloor|\\rceil)'
        r'(.*?)'
        r'\\right([)\]}|.\\]|\\langle|\\lfloor|\\lceil|\\rangle|\\rfloor|\\rceil)',
        s, re.DOTALL
    )
    for left_delim, _, right_delim in left_right_pairs:
        expected_right = _LEFT_RIGHT_PAIRS.get(left_delim)
        if expected_right and expected_right != right_delim and left_delim != '.' and right_delim != '.':
            report.left_right.setdefault("unpaired", []).append(
                f"\\left{left_delim} 配 \\right{right_delim} (应配 \\right{expected_right})"
            )

    return report


# ═══════════════════════════════════════════════
# 2. 自动修复括号
# ═══════════════════════════════════════════════

# \left 对应的默认 \right 分隔符
_LEFT_TO_RIGHT = {
    '(': ')',
    '[': ']',
    '{': '}',
    '|': '|',
    '.': '.',
    '\\{': '\\}',
    '\\langle': '\\rangle',
    '\\lfloor': '\\rfloor',
    '\\lceil': '\\rceil',
}


def auto_fix_brackets(s: str) -> str:
    """
    自动修复括号配对问题。

    修复策略:
      1. \\left( → 补 \\right)
      2. 失衡 {} → 补全或删除多余
      3. 失衡 () → 补全
      4. 失衡 [] → 补全
    不做语义级修复，只做 token 级补全。
    """
    if not s:
        return s

    # ── Step 1: 配对 \left 和 \right ──
    s = _fix_left_right(s)

    # ── Step 2: 配对 {} ──
    s = _fix_braces(s)

    # ── Step 3: 配对 () ──
    s = _fix_parens(s)

    # ── Step 4: 配对 [] ──
    s = _fix_brackets_sq(s)

    return s


def _fix_left_right(s: str) -> str:
    """自动补全 \\left \\right 配对。"""
    lefts = list(re.finditer(r'\\left([(\[{|.\\]|\\langle|\\lfloor|\\lceil)', s))
    rights = list(re.finditer(r'\\right([)\]}|.\\]|\\rangle|\\rfloor|\\rceil)', s))

    if len(lefts) == len(rights):
        return s

    # 为每个未配对的 \left 找到应该在的位置补 \right
    # 策略：在包含该 \left 的 $...$ 闭合之前插入，或在行末
    result = s
    extra = len(lefts) - len(rights)
    if extra <= 0:
        return result

    # 从右向左处理多余的 \left
    for left_m in reversed(lefts[-extra:]):
        left_delim = left_m.group(1)
        right_delim = _LEFT_TO_RIGHT.get(left_delim, '.')
        left_pos = left_m.end()

        # 查找该 \left 之后最近的 $ 闭合符（如果在数学模式内）
        # 检测 \left 是否在 $...$ 块内
        before = result[:left_pos]
        inline_dollars = before.count('$') - before.count('$$') * 2
        # 简化处理：如果在 $ 内，找到后续最近的 $ 并在其前插入
        if inline_dollars % 2 == 1:
            # 在 $...$ 内，找下一个 $
            next_dollar = result.find('$', left_pos)
            if next_dollar >= 0:
                insert_pos = next_dollar
            else:
                insert_pos = len(result)
        else:
            # 不在 $ 内，在行末或下一个 $ 之前
            next_dollar = result.find('$', left_pos)
            if next_dollar >= 0:
                insert_pos = next_dollar
            else:
                insert_pos = len(result)

        result = result[:insert_pos] + f'\\right{right_delim} ' + result[insert_pos:]

    return result


def _fix_braces(s: str) -> str:
    """自动修复 {} 配对。

    Strategy (balanced between correctness and simplicity):
    1. Count total brace depth.
    2. If depth > 0 (missing closes), try to find the natural close
       position for the LAST unclosed brace by scanning for the nearest
       `` \\`` (space + backslash-command) or ``=`` at brace-level 0 after
       that opening brace.  If found, insert ``}`` there.
    3. Any remaining missing closes are appended at the very end.
    """
    if not s:
        return s

    depth = 0
    for c in s:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1

    if depth == 0:
        return s

    if depth < 0:
        result = s
        for _ in range(-depth):
            idx = result.rfind('}')
            if idx >= 0:
                result = result[:idx] + result[idx+1:]
        return result

    # depth > 0 — find the LAST unclosed { and try to place its }
    # before a natural break (space-backslash or = at same level).
    remaining = depth
    result = list(s)

    last_open = -1
    cur = 0
    for i, ch in enumerate(s):
        if ch == '{':
            if cur == remaining - 1:
                last_open = i
            cur += 1
        elif ch == '}':
            cur -= 1

    if last_open >= 0:
        scan_d = 0
        best = len(s)
        for j in range(last_open + 1, len(s)):
            cj = s[j]
            if cj == '{':
                scan_d += 1
            elif cj == '}':
                scan_d -= 1
            elif scan_d == 0:
                if cj == '=' and j > 0 and s[j-1] in ' \t\n\r':
                    best = j
                    break
                if (cj == '\\' and j > 0 and s[j-1] in ' \t\n\r'
                        and j + 1 < len(s) and s[j+1].isalpha()):
                    best = j - 1
                    break
        result.insert(best, '}')
        remaining -= 1

    result.extend(['}'] * remaining)
    return ''.join(result)


def _fix_parens(s: str) -> str:
    """自动修复 () 配对。"""
    depth = 0
    for c in s:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1

    if depth == 0:
        return s
    if depth > 0:
        return s + ')' * depth
    else:
        result = s
        for _ in range(-depth):
            idx = result.rfind(')')
            if idx >= 0:
                result = result[:idx] + result[idx+1:]
        return result


def _fix_brackets_sq(s: str) -> str:
    """自动修复 [] 配对。"""
    depth = 0
    for c in s:
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1

    if depth == 0:
        return s
    if depth > 0:
        return s + ']' * depth
    else:
        result = s
        for _ in range(-depth):
            idx = result.rfind(']')
            if idx >= 0:
                result = result[:idx] + result[idx+1:]
        return result


# ═══════════════════════════════════════════════
# 3. 清理 Markdown 污染
# ═══════════════════════════════════════════════

# Markdown 污染模式：这些不应进入 LaTeX 渲染器
_MD_POLLUTION = [
    # 步骤标记：步骤1：步骤一：Step 1: 等
    (re.compile(r'(?:步骤|第)\s*[一二三四五六七八九十\d]+\s*(?:步|题|问)?\s*[：:]\s*'), ''),
    # 纯数字步骤：1. 1、1) (1) 在行首
    (re.compile(r'(?:^|\n)\s*\d+[.、．)\]]\s*'), '\n'),
    # Markdown 标题
    (re.compile(r'^#{1,6}\s*', re.MULTILINE), ''),
    # 粗体/斜体标记（成对）
    (re.compile(r'\*\*([^*]+)\*\*'), r'\1'),
    (re.compile(r'\*([^*]+)\*'), r'\1'),
    (re.compile(r'__([^_]+)__'), r'\1'),
    (re.compile(r'_([^_]+)_'), r'\1'),
    # 行内代码
    (re.compile(r'`([^`]+)`'), r'\1'),
    # 解答/答案前缀
    (re.compile(r'(?:解|答|解析|答案|证明|分析)\s*[：:]\s*'), ''),
    # HTML 标签
    (re.compile(r'<[^>]+>'), ''),
    # Markdown 链接 [text](url)
    (re.compile(r'\[([^\]]+)\]\([^\)]+\)'), r'\1'),
    # 水平线
    (re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE), ''),
    # 引用标记
    (re.compile(r'^>\s*', re.MULTILINE), ''),
]


def clean_markdown(text: str) -> str:
    """
    清理 Markdown 污染，提取纯文本+LaTeX 内容。

    移除:
      - 步骤标记（步骤1：等）
      - Markdown 标题（###）
      - 粗体/斜体/代码标记
      - 解答前缀（解：答：等）
      - HTML 标签
      - 链接语法
      - 引用标记
    保留:
      - LaTeX 数学表达式 ($...$, $$...$$)
      - 纯文本内容
    """
    if not text:
        return text

    # Protect math regions before cleaning — Markdown patterns like _([^_]+)_
    # (italics) will otherwise destroy LaTeX subscripts like _{n+1}.
    math_regions = []
    def _protect(m):
        math_regions.append(m.group(0))
        return '\x00MATH' + str(len(math_regions) - 1) + '\x00'

    # Protect display math first (longer pattern), then inline
    result = re.sub(r'\$\$.*?\$\$', _protect, text, flags=re.DOTALL)
    result = re.sub(r'\$(?!\$).*?\$(?!\$)', _protect, result)

    for pattern, replacement in _MD_POLLUTION:
        result = pattern.sub(replacement, result)

    # Restore math regions
    for i, region in enumerate(math_regions):
        result = result.replace('\x00MATH' + str(i) + '\x00', region)

    # 清理多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()

    return result


# ═══════════════════════════════════════════════
# 4. 文本和公式分离（极重要）
# ═══════════════════════════════════════════════

@dataclass
class Segment:
    """内容片段"""
    type: str       # "text" | "inline_math" | "display_math"
    content: str


def repair_math_delimiters_for_render(text: str) -> str:
    """Repair common malformed dollar delimiters before parsing/rendering.

    A frequent edit/import mistake is ``$$$formula$``: one extra opening dollar
    before an otherwise inline formula. If left untouched, the splitter pairs
    the wrong dollars and leaks raw LaTeX into the preview. This repair is kept
    narrow so valid ``$...$`` and ``$$...$$`` blocks are not rewritten.
    """
    if text is None:
        return ""

    s = str(text)
    if "$$$" not in s:
        return s

    # Extra leading dollar before a display block: $$$x$$ -> $$x$$.
    s = re.sub(r'\${3}([^$\n]+?)\${2}(?!\$)', r'$$\1$$', s)
    # Extra two leading dollars before an inline block: $$$x$ -> $x$.
    s = re.sub(r'\${3}([^$\n]+?)\$(?!\$)', r'$\1$', s)
    return s


def _pre_wrap_bare_latex(text: str) -> str:
    """Wrap bare LaTeX commands in $ delimiters before they reach markdown.

    When LLM/OCR output contains LaTeX commands outside math delimiters,
    markdown eats the backslashes and KaTeX never sees them. This finds
    such fragments using balanced-brace parsing and wraps them in $...$.
    """
    if not text:
        return text

    # Protect existing $...$ and $$...$$ regions with placeholders
    # so we can still find and wrap bare LaTeX in the remaining text.
    protected = []
    def _protect_pwl(m):
        protected.append(m.group(0))
        return f'\x00L{len(protected)-1}\x00'
    text = re.sub(r'\$\$[^$]+\$\$', _protect_pwl, text)
    text = re.sub(r'\$[^$]+\$', _protect_pwl, text)

    # Find all \command positions that are candidates for wrapping
    cmd_positions = [(m.start(), m.group(0)) for m in re.finditer(r'\\[a-zA-Z]+|\\[!,:;]', text)]
    if not cmd_positions:
        # Restore protected regions before returning
        for i, block in enumerate(protected):
            text = text.replace(f'\x00L{i}\x00', block)
        return text

    # For each command, find the balanced-brace extent
    def _scan_math_extent(text, start):
        """Scan from start to find the full extent of a math expression.
        Tracks balanced {} and continues past operators/relations/brackets
        to include multi-arg commands like \\frac{a}{b}, matrix environments
        with & alignment, and chains like \\left(...\\right) + \\int_c^d.

        Safety: caps at 2000 chars and depth 50 to prevent runaway scans.
        Handles \\\\ (LaTeX line breaks) and matrix/align & characters.
        """
        pos = start
        L = min(len(text), start + 2000)
        depth = 0
        iterations = 0
        while pos < L and iterations < 2000:
            iterations += 1
            ch = text[pos]
            if ch == '{':
                depth += 1
                if depth > 50:
                    pos += 1
                    depth = 49
                    continue
            elif ch == '}':
                depth -= 1
                if depth <= 0:
                    pos += 1
                    depth = 0
                    after = text[pos:pos + 30].lstrip()
                    if after and (after[0] == '{' or
                                  after[0] == '[' or
                                  after[0] == '(' or
                                  re.match(r'[=<>+\-*/×÷±&|]', after) or
                                  re.match(r'\\[a-zA-Z]', after) or
                                  after[:2] == '\\\\' or
                                  re.match(r'[_^]', after) or
                                  re.match(r'[A-Za-z0-9]', after)):
                        # Continue scanning - don't search for the character
                        # as we're already positioned correctly
                        continue
                    break
            elif ch in '\\' and depth == 0:
                pass  # Another command at brace-level 0 — include it
            elif ch in ' \t' and depth == 0:
                after = text[pos + 1:pos + 30].lstrip()
                if after and (after[0] == '{' or
                              re.match(r'\\[a-zA-Z]', after) or
                              after[:2] == '\\\\' or
                              re.match(r'[=<>+\-*/×÷±&|]', after)):
                    pos += 1
                    continue
                if after and re.match(r'[A-Za-z0-9]', after[0]):
                    pos += 1
                    continue
                break
            elif ch in '\n\r' and depth == 0:
                # Continue past newlines inside multi-line environments
                # (matrix, align) — same continuation logic as spaces
                after = text[pos + 1:pos + 30].lstrip()
                if after and (after[0] == '{' or
                              after[0] == '[' or
                              after[0] == '(' or
                              re.match(r'[=<>+\-*/×÷±&|]', after) or
                              re.match(r'\\[a-zA-Z]', after) or
                              after[:2] == '\\\\' or
                              re.match(r'[_^]', after) or
                              re.match(r'[A-Za-z0-9]', after)):
                    pos += 1
                    continue
                break
            elif depth == 0 and ord(ch) > 127:
                break
            pos += 1
        return pos

    # Build output with wrapped fragments
    out = []
    cursor = 0
    for start, cmd in cmd_positions:
        if start < cursor:
            continue
        # Extend start backward to include leading alphanumeric/punctuation
        ext_start = start
        while ext_start > cursor:
            ch = text[ext_start - 1]
            if ch.isalnum() or ch in "'\"([{,.=":
                ext_start -= 1
            elif ch in '-+' and (ext_start - 1 == cursor or text[ext_start - 2] in ' \t'):
                ext_start -= 1
            else:
                break
        start = ext_start
        out.append(text[cursor:start])
        end = _scan_math_extent(text, start + len(cmd))
        fragment = text[start:end].strip()
        if fragment:
            # Never wrap CJK-containing fragments as display math —
            # they are mixed text+math and must stay inline.
            has_cjk = bool(re.search(r'[一-鿿]', fragment))
            if not has_cjk and _should_force_display_math(fragment):
                out.append(f'$$\n{fragment}\n$$')
            else:
                out.append(f'${fragment}$')
        else:
            out.append(text[start:end])
        cursor = end

    if not out:
        for i, block in enumerate(protected):
            text = text.replace(f'\x00L{i}\x00', block)
        return text

    out.append(text[cursor:])
    result = ''.join(out)
    # Restore protected $...$ and $$...$$ regions
    for i, block in enumerate(protected):
        result = result.replace(f'\x00L{i}\x00', block)
    return result


_SUBQUESTION_LABEL_RE = re.compile(
    r"^\(\s*(?:\d+|[一二三四五六七八九十百]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\s*\)$"
)


def _demote_subquestion_math_labels(segments: list[dict]) -> list[dict]:
    """Render $(1)$ / $(2)$ labels as text so adjacent math stays stable."""
    if not segments:
        return segments

    demoted = []
    for i, seg in enumerate(segments):
        if (
            isinstance(seg, dict)
            and seg.get("type") == "inline_math"
            and _SUBQUESTION_LABEL_RE.match(str(seg.get("content", "")).strip())
        ):
            label = str(seg.get("content", "")).strip()
            next_seg = segments[i + 1] if i + 1 < len(segments) else None
            suffix = " " if isinstance(next_seg, dict) and next_seg.get("type") == "inline_math" else ""
            demoted.append({"type": "text", "content": f"{label}{suffix}"})
            continue
        demoted.append(seg)

    merged = []
    for seg in demoted:
        if merged and seg.get("type") == "text" and merged[-1].get("type") == "text":
            merged[-1]["content"] += seg.get("content", "")
        else:
            merged.append(seg)
    return merged


def normalize_inline_math_text(text: str) -> str:
    """Wrap bare math expressions in $...$ for proper LaTeX rendering.

    Handles patterns that _pre_wrap_bare_latex misses because they lack
    a backslash command prefix:
      - f'(x), g'(t)  — function with prime
      - e^{-t^2}      — exponential with superscript
      - x^2, x^{n+1} — variable with power
      - a_n, x_{n+1}  — variable with subscript
      - (-∞,-1), (1,+∞) — intervals with infinity
      - f(0)=1/2      — function evaluation equations

    Does NOT touch text already inside $...$ or $$...$$.
    Does NOT wrap ordinary Chinese text.
    """
    if not text:
        return text

    s = str(text)

    # Protect existing math regions
    protected: list[str] = []
    def _p(m):
        protected.append(m.group(0))
        return f'\x00P{len(protected) - 1}\x00'

    s = re.sub(r'\$\$[^$]+\$\$', _p, s, flags=re.S)
    s = re.sub(r'(?<!\$)\$(?!\$)[^$\n]+\$(?!\$)', _p, s)

    # P41.2: Protect LaTeX environments from being broken by inline patterns
    s, env_protected = protect_latex_environments(s)

    # Pattern 1: f'(x) or g'(t) — function name + prime + parens with math content
    s = re.sub(
        r"([a-zA-Z])'(\([^)]*\))",
        lambda m: f"${m.group(1)}'{m.group(2)}$",
        s,
    )

    # Pattern 2: f(0)=..., f(1)=..., g(x)=... — function evaluation equations
    s = re.sub(
        r'(?<!\$)([a-zA-Z])\((\d+)\)\s*=\s*([0-9a-zA-Z/+\-.*^{}]+(?:\([0-9a-zA-Z/+\-.*^{}]+\))*)',
        lambda m: f'${m.group(1)}({m.group(2)})={m.group(3)}$',
        s,
    )

    # Pattern 3: d / dx, d/dy — bare differential operators
    s = re.sub(
        r'(?<!\$)(?<![a-zA-Z])d\s*/\s*d([xyztu])(?![a-zA-Z])',
        lambda m: f'$\\frac{{d}}{{d{m.group(1)}}}$',
        s,
    )

    # Re-protect newly created $...$ regions
    s = re.sub(r'(?<!\$)\$(?!\$)[^$\n]+\$(?!\$)', _p, s)

    # Pattern 4: e^{-t^2}, e^{x}, e^{-x^2}, e^x — exponential expressions
    s = re.sub(
        r'(?<!\$)e(\^\{[^}]+\})(?!\$)',
        lambda m: f'$e{m.group(1)}$',
        s,
    )
    s = re.sub(
        r'(?<!\$)e\^([A-Za-z0-9])(?!\$)',
        lambda m: f'$e^{{{m.group(1)}}}$',
        s,
    )

    # P41 patterns (run before power/subscript to avoid conflicts):
    # Pattern 8: lim t → 0+, lim t->0+, lim_{t→0+} → \lim_{t\to0^+}
    s = re.sub(
        r'(?<!\$)(?<!\\)lim\s+([a-zA-Z])\s*(?:→|->|\\to)\s*0\s*\+(?!\$)',
        lambda m: f'$\\lim_{{{m.group(1)}\\to0^+}}$',
        s,
    )
    # lim t → 0 (without +)
    s = re.sub(
        r'(?<!\$)(?<!\\)lim\s+([a-zA-Z])\s*(?:→|->|\\to)\s*0(?!\$)(?![\^+\d])',
        lambda m: f'$\\lim_{{{m.group(1)}\\to0}}$',
        s,
    )
    # lim n → ∞
    s = re.sub(
        r'(?<!\$)(?<!\\)lim\s+([a-zA-Z])\s*(?:→|->|\\to)\s*(?:∞|\\infty)(?!\$)',
        lambda m: f'$\\lim_{{{m.group(1)}\\to\\infty}}$',
        s,
    )

    # Pattern 9: ∫_{-1}^1 or ∫_a^b → \int_{-1}^{1}
    s = re.sub(
        r'(?<!\$)(?<!\\)∫(\s*_[{-]?[^}^]*[}]?\s*\^[{]?[^}\s]*[}]?)',
        lambda m: f'$\\int{m.group(1).replace(" ", "")}$',
        s,
    )

    # Pattern 10: [u - u^3/3]_{-1}^{1} → \left[u-\frac{u^3}{3}\right]_{-1}^{1}
    s = re.sub(
        r'(?<!\$)(?<!\\left)\[([^\]]+)\]_\{([^}]*)\}\^\{([^}]*)\}',
        lambda m: f'$\\left[{m.group(1)}\\right]_{{{m.group(2)}}}^{{{m.group(3)}}}$',
        s,
    )

    # Re-protect newly created $...$ regions
    s = re.sub(r'(?<!\$)\$(?!\$)[^$\n]+\$(?!\$)', _p, s)

    # Pattern 5: x^2, x^{n+1} — variable with power
    s = re.sub(
        r'(?<!\$)(?<![a-zA-Z])([a-zA-Z])(\^(\{[^}]+\}|\d))(?!\$)(?![a-zA-Z}])',
        lambda m: f'${m.group(1)}{m.group(2)}$',
        s,
    )

    # Pattern 6: a_n, x_{n+1} — variable with subscript
    s = re.sub(
        r'(?<!\$)(?<![a-zA-Z])([a-zA-Z])(_(\{[^}]+\}|\d))(?!\$)(?![a-zA-Z}])',
        lambda m: f'${m.group(1)}{m.group(2)}$',
        s,
    )

    # Pattern 7: Intervals with infinity
    s = re.sub(
        r'(?<!\$)\(([+-]?∞|[+-]?\\infty)\s*,\s*([+-]?∞|[+-]?\\infty|[0-9.-]+)\)(?!\$)',
        lambda m: f'$({m.group(1)},{m.group(2)})$',
        s,
    )
    s = re.sub(
        r'(?<!\$)\(([0-9.-]+)\s*,\s*([+-]?∞|[+-]?\\infty)\)(?!\$)',
        lambda m: f'$({m.group(1)},{m.group(2)})$',
        s,
    )

    # Restore protected regions
    for i, region in enumerate(protected):
        s = s.replace(f'\x00P{i}\x00', region)

    # P41.2: Restore LaTeX environments
    s = restore_latex_environments(s, env_protected)

    return s


# ═══════════════════════════════════════════════
#  P41: Derivation formula canonicalization
# ═══════════════════════════════════════════════

# Re: top-level = signs (not inside braces, not \neq etc.)
_RE_TOPLEVEL_EQ = re.compile(r'(?<!\\)(?:=)(?!=)')
# Re: top-level ⇒ arrows
_RE_TOPLEVEL_ARROW = re.compile(r'(?:\\Rightarrow|\\Longrightarrow|⇒)')
# Re: trailing substitution annotation like ", (x=tu)" or " (x=tu)"
_RE_TRAILING_SUBSTITUTION = re.compile(
    r'\s*[,，]\s*[\(（]([a-zA-Z])\s*=\s*([a-zA-Z][^)）]*)[\)）]\s*$'
)
# Re: inline substitution like "(x=tu)" at end of formula
_RE_SUBSTITUTION_ANNOTATION = re.compile(
    r'[\(（]([a-zA-Z])\s*=\s*([a-zA-Z][^)）]*)[\)）]'
)
# Re: bare lim notation
_RE_BARE_LIM = re.compile(
    r'(?<!\\)(?<!\$)lim\s+([a-zA-Z])\s*(?:→|->|\\to)\s*([^\s,;]+)'
)
# Re: Chinese sentence inside latex (2+ CJK chars)
_RE_CHINESE_IN_LATEX = re.compile(r'[一-鿿]{2,}')

# P41.2: LaTeX environment protection
_LATEX_ENV_NAMES = (
    'aligned', 'align', 'alignat',
    'cases', 'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix',
    'array', 'gathered', 'split', 'multline', 'eqnarray',
)
_RE_LATEX_ENV = re.compile(
    r'\\begin\{(' + '|'.join(_LATEX_ENV_NAMES) + r')\}'
    r'[\s\S]*?'
    r'\\end\{\1\}',
)


def protect_latex_environments(text: str) -> tuple[str, dict]:
    """Replace \\begin{env}...\\end{env} blocks with placeholders.

    Returns (text_with_placeholders, {placeholder: original_content}).
    """
    if not text:
        return text, {}
    s = str(text)
    protected: dict[str, str] = {}
    counter = 0

    def _replace(m):
        nonlocal counter
        key = f'\x00LENV{counter}\x00'
        protected[key] = m.group(0)
        counter += 1
        return key

    s = _RE_LATEX_ENV.sub(_replace, s)
    return s, protected


def restore_latex_environments(text: str, protected: dict) -> str:
    """Restore placeholders back to original LaTeX environment content."""
    if not protected:
        return text
    s = str(text)
    for key, original in protected.items():
        s = s.replace(key, original)
    return s


def repair_aligned_environment(latex: str) -> str:
    r"""Repair common broken \begin{aligned}...\end{aligned} patterns.

    Handles:
    1. Escaped alignment markers: \&= → &=
    2. Missing \end{aligned}: try to append
    3. Orphan \end{aligned} without \begin: remove it
    4. First line missing alignment point: add \n after first line
    """
    if not latex:
        return latex
    s = str(latex).strip()

    has_begin = r'\begin{aligned}' in s or r'\begin{align}' in s
    has_end = r'\end{aligned}' in s or r'\end{align}' in s

    # Orphan end without begin
    if has_end and not has_begin:
        s = re.sub(r'\\end\{aligned\}', '', s)
        s = re.sub(r'\\end\{align\}', '', s)
        return s.strip()

    # Missing end — try to append
    if has_begin and not has_end:
        s = s.rstrip() + '\n\\end{aligned}'

    # Fix escaped alignment markers: \&= → &=
    s = s.replace(r'\&=', '&=')
    s = s.replace(r'\& ', '& ')

    # Fix first line missing alignment point
    begin_match = re.match(r'(\\begin\{aligned\})\s*(.*)', s, re.S)
    if begin_match:
        prefix = begin_match.group(1)
        rest = begin_match.group(2)
        lines = rest.split('\n')
        if lines:
            first_line = lines[0].strip()
            if first_line and '&' not in first_line and r'\\' not in first_line:
                # First line has no alignment point and no line break — check if
                # subsequent lines have &=, meaning first line is a "header" expr
                has_aligned_later = any('&' in l for l in lines[1:])
                if has_aligned_later:
                    lines[0] = first_line  # keep as-is, it's the LHS
                    # Ensure it has a line break
                    if len(lines) > 1:
                        s = prefix + '\n' + ' \\\\\n'.join(
                            l.strip() for l in lines if l.strip()
                        )
                        if not s.rstrip().endswith('\\end{aligned}'):
                            s = s.rstrip() + '\n\\end{aligned}'
                        return s

    # P41.3: Fix row spacing markers inside environments
    s = repair_latex_row_spacing_markers(s)

    return s


# P41.3: Row spacing marker patterns
# Matches \[6pt], \[4pt], \[.5em], \[1ex] etc. — broken spacing markers
# that lost a backslash and look like display math delimiters
_RE_BROKEN_ROW_SPACING = re.compile(
    r'(?<!\\)\\\[(\d*\.?\d+(?:pt|mm|cm|em|ex|baselineskip))\]'
)


def repair_latex_row_spacing_markers(latex: str) -> str:
    r"""Repair broken row spacing markers in LaTeX environments.

    Handles:
    1. \[6pt] → \\[6pt] (fix missing backslash)
    2. Inside cases: normalize all row spacing to plain \\
    3. Inside aligned: keep \\[6pt] as valid spacing

    Does NOT touch display math delimiters \[...\] (those have content,
    not just a dimension).
    """
    if not latex:
        return latex
    s = str(latex)

    # Fix broken spacing markers: \[6pt] → \\[6pt]
    s = _RE_BROKEN_ROW_SPACING.sub(r'\\\\[\1]', s)

    return s


def repair_cases_environment(latex: str) -> str:
    r"""Repair common broken \begin{cases}...\end{cases} patterns.

    Handles:
    1. Row spacing markers: \[6pt], \\[6pt] → \\ (plain line break)
    2. Missing & before conditions: add & separator
    3. Bare \[ inside cases (not spacing) → remove or fix
    """
    if not latex:
        return latex
    s = str(latex)

    # Only process if cases environment exists
    if r'\begin{cases}' not in s:
        return s

    # Fix row spacing inside cases: \\[6pt] → \\ and \[6pt] → \\
    # First fix broken ones (missing backslash)
    s = _RE_BROKEN_ROW_SPACING.sub(r'\\\\', s)
    # Then normalize valid spacing markers to plain \\
    s = re.sub(r'\\\\\[(\d+(?:\.\d+)?(?:pt|mm|cm|em|ex|baselineskip))\]', r'\\\\', s)

    # Fix lines missing & before conditions
    # Pattern: expression, condition (no &)
    # Inside cases, each line should be: expr, & condition \\
    lines = s.split('\n')
    result = []
    in_cases = False
    for line in lines:
        stripped = line.strip()
        if r'\begin{cases}' in stripped:
            in_cases = True
            result.append(line)
            continue
        if r'\end{cases}' in stripped:
            in_cases = False
            result.append(line)
            continue
        if in_cases and stripped and '&' not in stripped and r'\\' not in stripped:
            # Line in cases without & — might be: expr, condition
            # Try to split at last comma
            comma_pos = stripped.rfind(',')
            if comma_pos > 0:
                expr = stripped[:comma_pos + 1].strip()
                cond = stripped[comma_pos + 1:].strip()
                if cond:
                    stripped = f"{expr} & {cond}"
        result.append(stripped if in_cases else line)

    return '\n'.join(result)


_DERIVATION_LABEL_PREFIX_RE = re.compile(
    r"^(?:关键变形为|中间公式为|因此本步得到结论|已知条件可写为)[：:，,]?\s*",
)


def strip_derivation_label_prefix(text: str) -> str:
    """Remove step labels accidentally glued to display math."""
    s = str(text or "").strip()
    while s:
        m = _DERIVATION_LABEL_PREFIX_RE.match(s)
        if not m:
            break
        s = s[m.end() :].strip()
    return s


def repair_cases_amp_eq_rows(cases_body: str) -> str:
    r"""Turn ``f \\ &= v \\ g \\ &= h`` rows into ``f = v \\ g = h`` inside cases."""
    segments = re.split(r"\\\\", str(cases_body or ""))
    rows: list[str] = []
    pending = ""
    for segment in segments:
        seg = segment.strip()
        if not seg:
            continue
        if seg.startswith("&="):
            val = seg[2:].strip().rstrip(",")
            if pending:
                rows.append(f"{pending} = {val}")
                pending = ""
            elif val:
                rows.append(val)
            continue
        if "=" in seg and not seg.startswith("&"):
            rows.append(seg)
            pending = ""
            continue
        if pending:
            rows.append(pending)
        pending = seg
    if pending:
        rows.append(pending)
    return r" \\ ".join(rows)


def repair_nested_aligned_wrapping_cases(latex: str) -> str:
    """Unwrap invalid ``aligned`` wrappers around ``cases`` blocks."""
    s = str(latex or "").strip()

    def _unwrap(match: re.Match) -> str:
        body = repair_cases_amp_eq_rows(match.group(1))
        return f"\\begin{{cases}}\n{body}\n\\end{{cases}}"

    s = re.sub(
        r"\\begin\{aligned\}\s*\\begin\{cases\}(.*?)\\end\{cases\}\s*\\end\{aligned\}",
        _unwrap,
        s,
        flags=re.S,
    )
    s = re.sub(
        r"\\begin\{aligned\}\s*(\\begin\{cases\}.*?\\end\{cases\})\s*\\end\{aligned\}",
        r"\1",
        s,
        flags=re.S,
    )
    return s


_RE_ORPHAN_DERIV_LHS = re.compile(
    r"^[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)+$"
)


def _aligned_body_should_use_cases(body: str) -> bool:
    """True only for broken partial-derivative stacks, not normal derivation chains."""
    orphan_deriv = 0
    for segment in re.split(r"(?<!\\)\\\\", str(body or "")):
        seg = segment.strip().rstrip(",")
        if not seg:
            continue
        if "&=" in seg:
            if re.search(
                r",\s*[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)\s*$",
                seg,
            ):
                return True
            continue
        if "=" in seg:
            continue
        if _RE_ORPHAN_DERIV_LHS.match(seg):
            orphan_deriv += 1
    return orphan_deriv >= 2


def repair_aligned_equation_system(latex: str) -> str:
    r"""Turn broken multi-LHS ``aligned`` blocks (f_x \\ &= ... \\ f_y \\ &= ...) into ``cases``."""
    s = str(latex or "")

    def _convert(match: re.Match) -> str:
        body = match.group(1)
        if not _aligned_body_should_use_cases(body):
            return match.group(0)
        rows: list[str] = []
        pending_lhs = ""
        for segment in re.split(r"(?<!\\)\\\\", body):
            seg = segment.strip()
            if not seg:
                continue
            expanded = _expand_equation_clause(seg)
            if len(expanded) > 1:
                rows.extend(expanded)
                pending_lhs = ""
                continue
            if seg.startswith("&="):
                val = seg[2:].strip().rstrip(",")
                if pending_lhs:
                    rows.append(f"{pending_lhs} = {val}")
                    pending_lhs = ""
                elif val:
                    rows.append(val)
                continue
            if "&=" in seg:
                lhs, _, rhs = seg.partition("&=")
                lhs, rhs = lhs.strip(), rhs.strip().rstrip(",")
                if lhs and rhs:
                    rows.append(f"{lhs} = {rhs}")
                pending_lhs = ""
                continue
            if "=" in seg and not seg.startswith("&"):
                rows.append(seg.rstrip(","))
                pending_lhs = ""
                continue
            if pending_lhs:
                rows.append(pending_lhs.rstrip(","))
            pending_lhs = seg.rstrip(",")
        if pending_lhs:
            rows.append(pending_lhs.rstrip(","))
        if len(rows) >= 2 and all("=" in row for row in rows):
            return "\\begin{cases}\n" + " \\\\\n".join(rows) + "\n\\end{cases}"
        return match.group(0)

    return re.sub(
        r"\\begin\{aligned\}(.*?)\\end\{aligned\}",
        _convert,
        s,
        flags=re.S,
    )


def repair_orphan_left_right_and_env_tails(latex: str) -> str:
    r"""Remove wrapper fragments that make KaTeX expose red raw source."""
    if not latex:
        return latex
    s = str(latex)
    if r"\end{cases}" in s and r"\begin{cases}" not in s:
        s = s.replace(r"\end{cases}", "")
    s = re.sub(
        r"\\left\s*(?=\\(?![{}]|langle\b|lfloor\b|lceil\b|vert\b|Vert\b))",
        "",
        s,
    )
    s = re.sub(
        r"\\right\s*(?=\\(?![{}]|rangle\b|rfloor\b|rceil\b|vert\b|Vert\b))",
        "",
        s,
    )
    if r"\right" in s:
        left_count = len(re.findall(
            r"\\left(?:[()\[\]{}|.]|\\(?:langle|lfloor|lceil|vert|Vert))",
            s,
        ))
        right_count = len(re.findall(
            r"\\right(?:[)\]\}|.]|\\(?:rangle|rfloor|rceil|vert|Vert))",
            s,
        ))
        if right_count > left_count:
            extra = right_count - left_count

            def _drop_extra(match: re.Match) -> str:
                nonlocal extra
                if extra <= 0:
                    return match.group(0)
                extra -= 1
                return ""

            s = re.sub(
                r"\\right(?:[)\]\}|.]|\\(?:rangle|rfloor|rceil|vert|Vert))",
                _drop_extra,
                s,
                count=right_count - left_count,
            )
    return re.sub(r"\s{2,}", " ", s).strip()


def repair_system_display_latex(latex: str) -> str:
    """Repair display math used in AI derivation steps (cases, aligned, labels)."""
    s = strip_derivation_label_prefix(latex)
    if not s:
        return ""
    s = repair_orphan_left_right_and_env_tails(s)
    s = split_glued_display_equations(s)
    s = re.sub(r"\\\)\s*$", "", s.strip())
    s = re.sub(r"^\\\(", "", s)
    s = re.sub(r"(?<!\$)\$(?!\$)", "", s)
    s = re.sub(r"(?<!\\)\\backslash\s+", r"\\\\ ", s)
    s = repair_aligned_equation_system(s)
    s = repair_nested_aligned_wrapping_cases(s)

    def _fix_cases(match: re.Match) -> str:
        body = match.group(1)
        if "&=" in body:
            body = repair_cases_amp_eq_rows(body)
        body = _split_chained_cases_rows(body.strip())
        return f"\\begin{{cases}}\n{body}\n\\end{{cases}}"

    s = re.sub(r"\\begin\{cases\}(.*?)\\end\{cases\}", _fix_cases, s, flags=re.S)
    s = repair_cases_environment(s)
    if r"\begin{aligned}" in s or r"\begin{align}" in s:
        s = repair_aligned_environment(s)
    s = repair_orphan_left_right_and_env_tails(s)
    return s.strip()


# P41.4: Bare fraction patterns
# Matches: frac14, frac12, frac18, dfrac18, frac34, etc.
# Also: frac{1}{4}, dfrac{1}{8}
_RE_BARE_FRAC = re.compile(
    r'(?<!\\)(?:d?frac)(\d)(\d)'
)
_RE_BARE_FRAC_BRACES = re.compile(
    r'(?<!\\)(d?frac)\{(\d+)\}\{(\d+)\}'
)
# Stray d before frac: d frac14 → \frac{1}{4}
_RE_STRAY_D_FRAC = re.compile(
    r'(?<![a-zA-Z])d\s*(?:\\?\s*)?frac(\d)(\d)'
)
# Incomplete \ frac or \frac 14
_RE_INCOMPLETE_FRAC = re.compile(
    r'\\?\s*frac(\d)(\d)'
)


def repair_bare_fraction_commands(text: str) -> str:
    r"""Repair bare fraction commands in LaTeX.

    Handles:
    1. frac14 → \frac{1}{4}
    2. dfrac18 → \dfrac{1}{8}
    3. frac{1}{4} → \frac{1}{4} (already has braces but missing \)
    4. d frac18 → \frac{1}{8}
    5. \ frac14 → \frac{1}{4}
    """
    if not text:
        return text
    s = str(text)

    # Skip if no frac-like pattern
    if 'frac' not in s:
        return s

    # Protect existing \frac commands (already valid)
    # We need to NOT match \frac{...}{...} that's already correct
    # But DO match bare frac without backslash

    # Step 1: dfrac18 / frac14 → \dfrac{1}{8} / \frac{1}{4}
    def _replace_bare(m):
        cmd = m.group(0)
        # Extract the frac/dfrac prefix and two digits
        if cmd.startswith('d'):
            prefix = r'\dfrac'
            digits = cmd[5:]  # after "dfrac"
        else:
            prefix = r'\frac'
            digits = cmd[4:]  # after "frac"
        return f'{prefix}{{{digits[0]}}}{{{digits[1]}}}'

    # Match bare frac/dfrac followed by two digits, NOT preceded by backslash
    s = re.sub(r'(?<![\\a-zA-Z])(d?frac)(\d)(\d)', lambda m: f'\\{m.group(1)}{{{m.group(2)}}}{{{m.group(3)}}}', s)

    # Step 2: d frac18 → \frac{1}{8} (stray d)
    s = _RE_STRAY_D_FRAC.sub(lambda m: f'\\frac{{{m.group(1)}}}{{{m.group(2)}}}', s)

    # Step 3: \ frac14 → \frac{1}{4} (space after backslash)
    s = re.sub(r'\\\s*frac(\d)(\d)', lambda m: f'\\frac{{{m.group(1)}}}{{{m.group(2)}}}', s)

    # Step 4: frac{1}{4} without backslash → \frac{1}{4}
    s = re.sub(r'(?<![\\a-zA-Z])(d?frac)\{(\d+)\}\{(\d+)\}', lambda m: f'\\{m.group(1)}{{{m.group(2)}}}{{{m.group(3)}}}', s)

    # \frac\pi^2{2} → \frac{\pi^2}{2}
    s = re.sub(
        r'\\frac([A-Za-z]+)(\^[0-9]+)?\{([^{}]+)\}',
        lambda m: f'\\frac{{{m.group(1)}{m.group(2) or ""}}}{{{m.group(3)}}}',
        s,
    )

    return s


# P41.4: Probability formula fragment patterns
_RE_ORPHAN_BANG = re.compile(r'^\s*!\s*$', re.M)
_RE_ORPHAN_SEMICOLON = re.sub  # not used directly
_RE_ORPHAN_STAR = re.compile(r'^\s*\*\*\s*$', re.M)
_RE_ORPHAN_DX_LINE = re.compile(r'^\s*(?:d[xyzt])\s*$', re.M)
_RE_BANG_BEFORE_PAREN = re.compile(r'!\s*(\()')
_RE_BANG_BEFORE_BRACE = re.compile(r'!\s*(\{)')


def repair_probability_formula_fragments(text: str) -> str:
    r"""Repair common probability formula fragments in LaTeX.

    Handles:
    1. Orphan ! on its own line → delete
    2. Orphan ** on its own line → delete
    3. Orphan dx/dy/dt on its own line → merge with previous line
    4. !( → \left( or just (
    5. !{ → \left\{ or just \{
    6. Event set semicolons: {X<=a; Y<=b} → {X\le a,\ Y\le b}
    7. F\n!\n(...) → F(...) (merge split function name)
    """
    if not text:
        return text
    s = str(text)

    # Remove orphan markers on their own line
    s = _RE_ORPHAN_BANG.sub('', s)
    s = _RE_ORPHAN_STAR.sub('', s)

    # Merge orphan dx/dy/dt lines with previous line
    def _merge_dx_line(m):
        # Find the line before this one
        start = m.start()
        before = s[:start].rstrip()
        after = s[m.end():]
        dx = m.group(0).strip()
        # Add \, before dx if not already there
        if not before.endswith(r'\,'):
            before += r'\,'
        return before + dx + after.lstrip('\n')

    # This is tricky with regex — use a simpler approach
    lines = s.split('\n')
    merged_lines = []
    for line in lines:
        stripped = line.strip()
        # Check if this line is just a differential
        if stripped in ('dx', 'dy', 'dz', 'dt', 'du', 'dv') and merged_lines:
            prev = merged_lines[-1].rstrip()
            if not prev.endswith(r'\,'):
                prev += r'\,'
            merged_lines[-1] = prev + stripped
        else:
            merged_lines.append(line)
    s = '\n'.join(merged_lines)

    # Fix !( → (  (remove stray bang before paren)
    s = _RE_BANG_BEFORE_PAREN.sub(r'\1', s)
    # Fix !{ → \{  (remove stray bang before brace, keep as set delimiter)
    s = _RE_BANG_BEFORE_BRACE.sub(r'\\' + r'\1', s)

    # Fix event set semicolons inside braces
    # Simple approach: replace ; with ,\  inside {...}
    result = []
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '{':
            depth += 1
            result.append(ch)
        elif ch == '}':
            depth -= 1
            result.append(ch)
        elif ch == ';' and depth > 0:
            result.append(r',\ ')
        else:
            result.append(ch)
        i += 1
    s = ''.join(result)

    # Clean up empty lines from removed markers
    s = re.sub(r'\n\s*\n', '\n', s)

    return s


def normalize_probability_derivation_block(text: str) -> str:
    r"""Normalize probability derivation blocks (CDF/PDF) to aligned format.

    Identifies patterns like:
    - F_Y(y)=P(...)=\int...\int...=...
    - f_Y(y)=\frac{d}{dy}F_Y(y)=...

    Converts multi-= chains to \begin{aligned}...\end{aligned}.
    """
    if not text:
        return text
    s = str(text).strip()

    # Only process if it looks like a probability derivation
    if not re.search(r'[FPf]_[A-Z]\(|\\frac\{d\}\{d[xyzt]\}', s):
        return s

    # If already has aligned, just repair
    if r'\begin{aligned}' in s:
        return repair_aligned_environment(s)

    # Count top-level = signs
    clean = re.sub(r'\{[^}]*\}', '', s)
    clean = re.sub(r'\\text\{[^}]*\}', '', clean)
    clean = re.sub(r'(?:\\neq|\\ne|\\geq|\\leq|\\approx|\\equiv|==)', '', clean)
    eq_count = len(_RE_TOPLEVEL_EQ.findall(clean))

    if eq_count >= 2:
        # Use the standard derivation normalization
        return normalize_derivation_formula_block(s)

    return s


def _split_top_level_commas(text: str) -> list[str]:
    """Split on commas at brace/paren depth zero (keeps ``f(x,y)`` intact)."""
    segments: list[str] = []
    depth_paren = 0
    depth_brace = 0
    current: list[str] = []
    for ch in str(text or ""):
        if ch == "{":
            depth_brace += 1
            current.append(ch)
        elif ch == "}":
            depth_brace = max(depth_brace - 1, 0)
            current.append(ch)
        elif ch == "(":
            depth_paren += 1
            current.append(ch)
        elif ch == ")":
            depth_paren = max(depth_paren - 1, 0)
            current.append(ch)
        elif ch == "," and depth_paren == 0 and depth_brace == 0:
            # LaTeX spacing commands (\, \; \: \!) are not list separators.
            if current and current[-1] == "\\":
                current.append(ch)
            else:
                segments.append("".join(current).strip())
                current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        segments.append(tail)
    return [seg for seg in segments if seg]


_MATH_BINDING_ID = r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9]+)?(?:'+)?"
_RE_GLUE_BINDING = re.compile(rf"\s+({_MATH_BINDING_ID})\s*=")
_RE_DIFFERENTIAL_PREFIX = re.compile(r"(?:\\mathrm\{d\}|(?<![a-zA-Z])d)[xyztu]?\s*$")
_RE_LABELED_EQUATION = re.compile(rf"^[^\s=]+:\s*.+=", re.S)


def _top_level_equals_positions(text: str) -> list[int]:
    positions: list[int] = []
    depth = 0
    for i, ch in enumerate(str(text or "")):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(depth - 1, 0)
        elif ch == "=" and depth == 0 and (i == 0 or text[i - 1] != "\\") and (i + 1 >= len(text) or text[i + 1] != "="):
            positions.append(i)
    return positions


def _find_eq_index_from(text: str, start: int) -> int:
    positions = _top_level_equals_positions(text)
    for pos in positions:
        if pos >= start:
            return pos
    return -1


def _clause_is_annotation(clause: str) -> bool:
    """Clause with no binding (e.g. endpoint range) — not part of an equation chain."""
    c = str(clause or "").strip()
    if not c:
        return True
    if _top_level_equals_positions(c):
        return False
    if re.search(r"\\to|→|⇒|\\(?:Rightarrow|Longrightarrow)", c):
        return True
    if re.match(r"^\([^)]*\)$", c):
        return True
    return False


def _binding_identifier_before_equals(text: str, eq_pos: int) -> tuple[bool, str]:
    """True when ``=`` binds a new symbol on its left (independent equation), not mid-expression."""
    left = str(text[:eq_pos] or "").rstrip()
    if not left:
        return False, ""
    m = re.search(rf"({_MATH_BINDING_ID})$", left)
    if not m:
        return False, ""
    ident = m.group(1)
    prefix = left[: m.start()]
    if _RE_DIFFERENTIAL_PREFIX.search(prefix.rstrip()):
        return False, ident
    if not prefix:
        return True, ident
    prev = prefix[-1]
    if prev in "([{,\\:+-*/^&|=":
        return True, ident
    if prev.isdigit() or prev.isalpha() or prev in ")}]":
        return False, ident
    return True, ident


def _split_glued_subject_restarts(text: str) -> list[str]:
    """Two complete equations written back-to-back: ``... dx I = ...``."""
    s = str(text or "").strip()
    for m in _RE_GLUE_BINDING.finditer(s):
        eq_pos = m.start(1) + len(m.group(1))
        while eq_pos < len(s) and s[eq_pos].isspace():
            eq_pos += 1
        if eq_pos >= len(s) or s[eq_pos] != "=":
            continue
        is_binding, ident = _binding_identifier_before_equals(s, eq_pos)
        left = s[: m.start()].strip()
        right = s[m.start(1) :].strip()
        if re.fullmatch(r"\\[A-Za-z]+", left):
            continue
        if not right.count("="):
            continue
        if re.fullmatch(r"[^\s=]+:", left):
            continue
        if re.search(r"[^\s=]:\s*$", left):
            continue
        if left.rstrip().endswith((r"\Rightarrow", r"\Longrightarrow", "⇒")):
            continue
        trailing = left.rstrip()
        if re.search(rf"d[xyztu]\s+{re.escape(ident)}\s*$", trailing):
            continue
        if left.count("=") >= 1 and is_binding:
            return [left, right]
        if left.count("=") == 0 and ident and "_" in ident and re.match(
            r"^[0-9A-Za-z\\^_{}()+\-.* ]+$", left
        ):
            return [left, right]
        if left.count("=") == 0 and is_binding and re.match(
            r"^[0-9A-Za-z\\^_{}()+\-.* ]+$", left
        ):
            return [left, right]
    return []


def _split_numeric_coefficient_glued(text: str) -> list[str]:
    """``B = -2y = C`` → ``B = -2`` and ``y = C`` (coefficient then new symbol)."""
    s = str(text or "").strip()
    m = re.match(rf"^(.+?) = (-?\d+)({_MATH_BINDING_ID}) = (.+)$", s)
    if not m:
        return []
    return [f"{m.group(1).strip()} = {m.group(2)}", f"{m.group(3)} = {m.group(4).strip()}"]


def _is_rewrite_chain(clause: str) -> bool:
    """Same subject rewritten: ``a = b = c`` or ``f_x = expr1 = expr2``, not multiple bindings."""
    s = str(clause or "").strip()
    positions = _top_level_equals_positions(s)
    if len(positions) < 2:
        return False
    subject = s[: positions[0]].strip()
    if not subject or ":" in subject.split("=")[0]:
        return False
    for i in range(1, len(positions)):
        prev_rhs = s[positions[i - 1] + 1 : positions[i]].strip()
        is_binding, ident = _binding_identifier_before_equals(s, positions[i])
        if not is_binding:
            before_eq = s[:positions[i]].rstrip()
            if _RE_DIFFERENTIAL_PREFIX.search(before_eq) or re.search(
                r"(?:\\mathrm\{d\}|(?<![a-zA-Z])d)[xyztu]\s*$", before_eq
            ):
                continue
            return False
        if ident != prev_rhs:
            return False
    return True


_RE_GLUE_EXPR_HEAD = re.compile(
    r"(?:\\lim(?:_\{[^{}]+\})?"
    r"|\\(?:sin|cos|tan|log|ln|exp|sec|csc|cot|arcsin|arccos|arctan|sinh|cosh|tanh)\b"
    r"|\("
    rf"|{_MATH_BINDING_ID}"
    r")",
    re.S,
)


def _looks_like_equation_restart(tail: str) -> bool:
    t = str(tail or "").lstrip()
    if not t or "=" not in t:
        return False
    if re.match(r"d[xyztu](?:\\mathrm|\s|$|=)", t):
        return False
    if re.match(r"\d", t):
        return False
    if t.startswith("("):
        return False
    if t.startswith("\\"):
        return bool(
            re.match(r"\\(?:lim(?:_\{[^{}]+\})?|(?:sin|cos|tan|log|ln|exp)\b)", t)
            or t.startswith("\\(")
        )
    return bool(re.match(rf"({_MATH_BINDING_ID})\s*(?:_|\^|\{{|\(|\s)*=", t))


def _split_glued_expression_restarts(text: str) -> list[str]:
    """Split back-to-back equations like ``... + o(x^5) \\sin(\\sin x) = ...``."""
    s = str(text or "").strip()
    if not s or len(_top_level_equals_positions(s)) < 2:
        return []
    split_points: list[int] = []
    for m in re.finditer(r"o\s*\([^)]+\)", s):
        end = m.end()
        tail = s[end:]
        if not _looks_like_equation_restart(tail):
            continue
        sp = end
        while sp < len(s) and s[sp].isspace():
            sp += 1
        if sp < len(s) and (not split_points or split_points[-1] != sp):
            split_points.append(sp)
    if not split_points:
        return []
    parts: list[str] = []
    last = 0
    for sp in split_points:
        chunk = s[last:sp].strip().rstrip(",")
        if chunk:
            parts.append(chunk)
        last = sp
    tail = s[last:].strip().rstrip(",")
    if tail:
        parts.append(tail)
    return parts if len(parts) >= 2 else []


def _split_independent_bindings(clause: str) -> list[str]:
    """Split a clause with multiple top-level bindings into separate equations."""
    s = str(clause or "").strip()
    positions = _top_level_equals_positions(s)
    if len(positions) <= 1:
        return [s]
    rows: list[str] = []
    lhs = s[: positions[0]].strip()
    for i in range(len(positions)):
        rhs_end = positions[i + 1] if i + 1 < len(positions) else len(s)
        rhs = s[positions[i] + 1 : rhs_end].strip().rstrip(",")
        if i == 0:
            rows.append(f"{lhs} = {rhs}")
            continue
        is_binding, ident = _binding_identifier_before_equals(s, positions[i])
        prev_rhs = s[positions[i - 1] + 1 : positions[i]].strip()
        if is_binding and ident != prev_rhs:
            m = re.fullmatch(rf"(-?\d+)({_MATH_BINDING_ID})", prev_rhs)
            if m and m.group(2) == ident:
                rows[-1] = f"{lhs} = {m.group(1)}"
                lhs = ident
                rows.append(f"{lhs} = {rhs}")
                continue
            lhs = ident
        rows.append(f"{lhs} = {rhs}")
    return rows


def _expand_equation_clause(clause: str, _depth: int = 0) -> list[str]:
    """Decompose one comma-free clause into independent equations or leave chain intact."""
    s = str(clause or "").strip()
    if not s:
        return []
    if _depth > 12:
        return [s]
    if _RE_LABELED_EQUATION.match(s):
        return [s]
    expr_glued = _split_glued_expression_restarts(s)
    if expr_glued:
        out: list[str] = []
        for part in expr_glued:
            out.extend(_expand_equation_clause(part, _depth + 1))
        return out
    glued = _split_glued_subject_restarts(s)
    if glued:
        out: list[str] = []
        for part in glued:
            out.extend(_expand_equation_clause(part, _depth + 1))
        return out
    numeric = _split_numeric_coefficient_glued(s)
    if numeric:
        return numeric
    if _is_rewrite_chain(s):
        return [s]
    if len(_top_level_equals_positions(s)) >= 2:
        return _split_independent_bindings(s)
    return [s]


def _to_aligned_chain(clause: str) -> str:
    parts = _split_at_toplevel_operators(clause)
    if len(parts) < 2:
        return clause
    lines: list[str] = []
    head = parts[0].strip()
    first_tail = parts[1].strip()
    if first_tail.startswith("="):
        lines.append(f"{head} &= {first_tail[1:].strip()}")
    elif first_tail.startswith(("&=", "&", "\\Rightarrow", "\\Longrightarrow", "⇒")):
        lines.append(f"{head} {first_tail}")
    else:
        lines.append(head)
        lines.append("&= " + first_tail)
    for part in parts[2:]:
        p = part.strip()
        if p.startswith(("=", "\\Rightarrow", "\\Longrightarrow", "⇒")):
            p = "&" + p if not p.startswith("&") else p
        elif _RE_TOPLEVEL_EQ.match(p):
            p = "&" + p
        elif _RE_TOPLEVEL_ARROW.match(p):
            p = "&" + p
        else:
            p = "&= " + p
        lines.append(p)
    return "\\begin{aligned}\n" + " \\\\\n".join(lines) + "\n\\end{aligned}"


def _format_math_structure_display(text: str) -> str:
    """Classify by math logic: rewrite chains → aligned; independent bindings → cases; annotations → quad."""
    s = str(text or "").strip()
    if not s:
        return s
    clauses = _split_top_level_commas(s)
    equations: list[str] = []
    annotations: list[str] = []
    for clause in clauses:
        c = clause.strip()
        if not c:
            continue
        if _clause_is_annotation(c):
            annotations.append(c)
            continue
        for expanded in _expand_equation_clause(c):
            equations.append(expanded)
    if not equations:
        return s
    quad = (" \\quad " + ", ".join(annotations)) if annotations else ""
    if len(equations) == 1 and _is_rewrite_chain(equations[0]):
        return _to_aligned_chain(equations[0]) + quad
    if len(equations) >= 2:
        body = " \\\\\n".join(equations)
        return f"\\begin{{cases}}\n{body}\n\\end{{cases}}" + quad
    return equations[0] + quad


def split_glued_display_equations(latex: str) -> str:
    """Pre-split back-to-back equations before structural formatting."""
    s = str(latex or "").strip()
    if not s or r"\begin{cases}" in s or r"\begin{aligned}" in s:
        return s
    clauses = _split_top_level_commas(s)
    if len(clauses) > 1:
        parts: list[str] = []
        for clause in clauses:
            c = str(clause or "").strip()
            if not c:
                continue
            glued = _split_glued_subject_restarts(c)
            if glued:
                parts.append(", ".join(glued))
            else:
                numeric = _split_numeric_coefficient_glued(c)
                parts.append(", ".join(numeric) if numeric else c)
        return ", ".join(parts)
    expr_glued = _split_glued_expression_restarts(s)
    if expr_glued:
        return ", ".join(expr_glued)
    glued = _split_glued_subject_restarts(s)
    if glued:
        return ", ".join(glued)
    numeric = _split_numeric_coefficient_glued(s)
    if numeric:
        return ", ".join(numeric)
    return s


def _split_chained_cases_rows(cases_body: str) -> str:
    """Split case rows that accidentally contain multiple independent bindings."""
    segments = re.split(r"(?<!\\)\\\\", str(cases_body or ""))
    rows: list[str] = []
    for segment in segments:
        seg = segment.strip().rstrip(",")
        if not seg:
            continue
        rows.extend(_expand_equation_clause(seg))
    if len(rows) >= 2:
        return " \\\\\n".join(rows)
    return str(cases_body or "").strip()


def _try_independent_equations_cases_block(text: str) -> str | None:
    """Comma-separated clauses → structural display (cases / aligned / quad)."""
    segments = _split_top_level_commas(str(text or ""))
    if len(segments) < 2:
        return None
    formatted = _format_math_structure_display(text)
    if formatted != text.strip() and (r"\begin{cases}" in formatted or r"\begin{aligned}" in formatted):
        return formatted
    return None


def normalize_derivation_formula_block(text: str) -> str:
    """P41: Normalize a derivation formula block for display.

    1. Strip outer $$ / \\[ \\].
    2. Detect multi-= derivation chains → convert to aligned.
    3. Convert trailing substitution ", (x=tu)" → "\\quad (x=tu)".
    4. Normalize bare lim notation.
    """
    if not text:
        return text
    s = str(text).strip()

    # 1. Strip outer delimiters
    if s.startswith('$$') and s.endswith('$$'):
        s = s[2:-2].strip()
    elif s.startswith('\\[') and s.endswith('\\]'):
        s = s[2:-2].strip()

    # If already has aligned environment, repair multi-LHS chaos → cases when needed
    if r'\begin{aligned}' in s or r'\begin{align}' in s:
        s = repair_aligned_equation_system(s)
        return repair_aligned_environment(s)

    s = _normalize_tex_spacing_before_binding(s)

    # 2. Normalize bare lim notation
    s = _RE_BARE_LIM.sub(
        lambda m: f'\\lim_{{{m.group(1)}\\to{m.group(2)}}}', s
    )

    # 3. Handle trailing substitution annotation: ", (x=tu)" → "\quad (x=tu)"
    m_sub = _RE_TRAILING_SUBSTITUTION.search(s)
    if m_sub:
        s = _RE_TRAILING_SUBSTITUTION.sub('', s).rstrip()
        s += f'\\quad ({m_sub.group(1)}={m_sub.group(2)})'

    s = split_glued_display_equations(s)
    s = re.sub(
        rf"((?:\\mathrm{{d}}|(?<![a-zA-Z])d)[xyztu])\s+({_MATH_BINDING_ID})\s*(?=$|[,\s])",
        r"\1",
        s,
    )

    if re.search(r"\\(?:Rightarrow|Longrightarrow)|⇒", s) and len(_split_top_level_commas(s)) == 1:
        return _to_aligned_chain(s)

    if len(_top_level_equals_positions(s)) >= 2 and len(_split_top_level_commas(s)) == 1:
        return _to_aligned_chain(s)

    formatted = _format_math_structure_display(s)
    if formatted != s and (r"\begin{cases}" in formatted or r"\begin{aligned}" in formatted or r"\quad" in formatted):
        return formatted

    if _is_rewrite_chain(s):
        return _to_aligned_chain(s)

    return s


def _normalize_tex_spacing_before_binding(text: str) -> str:
    """Turn malformed TeX spacing before a new binding into a separator."""
    s = str(text or "")
    return re.sub(
        rf"(?:\\(?:,|;|:|!|quad|qquad)|\\\s+|\\\\\s*)\s*({_MATH_BINDING_ID})\s*=",
        r", \1=",
        s,
    )


def _split_at_toplevel_operators(text: str) -> list[str]:
    """Split formula at top-level = and ⇒ arrows, respecting brace depth."""
    parts = []
    depth = 0
    current = []
    i = 0
    s = text
    while i < len(s):
        ch = s[i]
        if ch == '{':
            depth += 1
            current.append(ch)
        elif ch == '}':
            depth -= 1
            current.append(ch)
        elif depth == 0:
            # Check for ⇒ or = at top level
            if s[i:].startswith('\\Rightarrow') or s[i:].startswith('\\Longrightarrow'):
                if current:
                    parts.append(''.join(current))
                # Find the arrow
                arrow_match = re.match(r'\\Longrightarrow|\\Rightarrow', s[i:])
                if arrow_match:
                    parts.append(arrow_match.group(0))
                    i += len(arrow_match.group(0))
                    current = []
                    continue
            elif ch == '=' and (i == 0 or s[i-1] != '\\') and (i + 1 < len(s) and s[i+1] != '='):
                # Top-level =
                if current:
                    parts.append(''.join(current))
                parts.append('=')
                i += 1
                current = []
                continue
            else:
                current.append(ch)
        else:
            current.append(ch)
        i += 1
    if current:
        parts.append(''.join(current))

    # Merge: each "=" or arrow should be prepended to the next part
    merged = []
    i = 0
    while i < len(parts):
        if parts[i] in ('=', '\\Rightarrow', '\\Longrightarrow') and i + 1 < len(parts):
            merged.append(parts[i] + ' ' + parts[i + 1])
            i += 2
        else:
            merged.append(parts[i])
            i += 1
    return merged


def split_text_and_latex_mixed_block(text: str) -> list[dict]:
    """P41: Split a mixed Chinese+formula block into clean text and latex blocks.

    Rules:
    1. Chinese prose stays in text blocks.
    2. Pure formulas go to latex_display blocks.
    3. Trailing substitution ", (x=tu)" → "\\quad (x=tu)" inside latex.
    4. If unsafe to split, return original as text block.
    5. P41.2: LaTeX environments (aligned, cases, etc.) are extracted first
       as complete latex_display blocks, never split across lines.
    """
    if not text:
        return []
    s = str(text).strip()

    # Quick check: if no LaTeX-like content, return as text
    if not re.search(r'[\\{}^_=∫∑∏]|(?:frac|int|lim|sum|begin|end)', s):
        return [{"type": "text", "content": s}]

    # P41.2: Extract complete LaTeX environments first
    s_protected, env_map = protect_latex_environments(s)
    if env_map:
        # Process around the placeholders
        result = []
        # Split by placeholders to separate env content from surrounding text
        parts = re.split(r'(\x00LENV\d+\x00)', s_protected)
        for part in parts:
            part_stripped = part.strip()
            if not part_stripped:
                continue
            if part_stripped.startswith('\x00LENV') and part_stripped.endswith('\x00'):
                # This is a protected environment
                original = env_map.get(part_stripped, part_stripped)
                # P41.4: Fix bare fractions and probability fragments
                repaired = repair_bare_fraction_commands(original)
                repaired = repair_probability_formula_fragments(repaired)
                # P41.3: Fix row spacing and cases before aligned repair
                repaired = repair_latex_row_spacing_markers(repaired)
                repaired = repair_system_display_latex(repaired)
                result.append({"type": "latex_display", "content": repaired})
            else:
                # Surrounding text — process it for text/formula split
                sub_blocks = _split_text_and_latex_no_env(part_stripped)
                result.extend(sub_blocks)
        return result if result else [{"type": "text", "content": s}]

    return _split_text_and_latex_no_env(s)


def _split_text_and_latex_no_env(s: str) -> list[dict]:
    """Inner helper for split_text_and_latex_mixed_block — no env extraction."""
    # Split by lines
    lines = s.split('\n')
    result = []
    formula_buf = []
    text_buf = []

    def _flush_text():
        if text_buf:
            merged = '\n'.join(text_buf).strip()
            if merged:
                result.append({"type": "text", "content": merged})
            text_buf.clear()

    def _flush_formula():
        if formula_buf:
            merged = '\n'.join(formula_buf).strip()
            if merged:
                normalized = normalize_derivation_formula_block(merged)
                result.append({"type": "latex_display", "content": normalized})
            formula_buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if line is mostly formula
        has_latex_cmd = bool(re.search(r'[\\{}^_=]|(?:frac|int|lim|sum|begin|end)', stripped))
        chinese_chars = len(re.findall(r'[一-鿿]', stripped))
        total_chars = len(stripped.replace(' ', ''))

        if has_latex_cmd and chinese_chars == 0:
            # Pure formula line (no CJK)
            _flush_text()
            formula_buf.append(stripped)
        else:
            # Chinese prose and/or mixed CJK+LaTeX — keep as text, never latex_display
            _flush_formula()
            text_buf.append(stripped)

    _flush_text()
    _flush_formula()

    return result if result else [{"type": "text", "content": s}]


def split_latex_text(text: str) -> list[dict]:
    """
    将混合内容分离为文本和公式片段列表。

    这是渲染管道的关键第一步——文本和公式必须分开处理，
    避免 Markdown 标记进入 KaTeX 渲染器，也避免 LaTeX 命令被文本解析器误食。

    返回:
      [
        {"type": "text", "content": "这是文字"},
        {"type": "inline_math", "content": "x^2 + y^2 = 1"},
        {"type": "text", "content": "更多文字"},
        {"type": "display_math", "content": "\\int_0^\\infty f(x)dx"},
      ]

    渲染时:
      - type=text       → st.markdown() 或 st.text()
      - type=inline_math → st.latex() 或 st.markdown("$...$")
      - type=display_math → st.latex() 或 st.markdown("$$...$$")
    """
    if not text:
        return []

    text = repair_math_delimiters_for_render(text)

    # Step 1: Wrap entire lines that look like standalone math in $$...$$
    text = _normalize_math_lines_for_split(text)

    # Step 2: Wrap remaining bare LaTeX commands inside text lines in $...$
    text = _pre_wrap_bare_latex(text)

    # Step 2.5: Normalize sub-question markers $(1)$, $(2)$ → (1), (2)
    # These are NOT math — they're question part labels. Converting them
    # prevents false inline_math segments that KaTeX renders as display.
    text = re.sub(r'\$\((\d+)\)\$', r'(\1)', text)

    # 清理未被正确恢复的占位符
    # 这些占位符来自 latex_normalizer._wrap_bare_math_expressions 或 ocr_repair.layout_recovery
    # 格式: \x00M{i}\x00 或 \x00MATH{i}\x00
    text = re.sub(r'\x00M\d+\x00', '', text)
    text = re.sub(r'\x00MATH\d+\x00', '', text)

    # 修复丢失的反斜杠
    # 常见的 LaTeX 命令可能在数据存储/传输过程中丢失反斜杠
    # 检测并恢复这些命令前的反斜杠
    latex_commands = [
        # 环境命令
        'begin', 'end',
        # 运算符名称
        'operatorname',
        # 极限相关
        'limsup', 'liminf', 'varlimsup', 'varliminf',
        # 三角函数（反三角函数）
        'arcsin', 'arccos', 'arctan', 'arccot', 'arcsec', 'arccsc',
        'arcsinh', 'arccosh', 'arctanh', 'arccoth', 'arcsech', 'arccsch',
        # 字体命令
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb',
        # 省略号
        'ldots', 'cdots', 'vdots', 'ddots',
        # 箭头
        'Rightarrow', 'Leftarrow', 'leftrightarrow', 'Leftrightarrow',
        'rightarrow', 'leftarrow', 'mapsto', 'hookleftarrow', 'hookrightarrow',
        'xrightarrow', 'xleftarrow', 'xRightarrow', 'xLeftarrow',
        # 大括号命令
        'Biggl', 'biggr', 'Biggr', 'Big', 'bigg', 'bigl', 'bigr',
        # 符号
        'partial', 'nabla', 'triangle', 'square', 'diamond', 'circ', 'bullet',
        'oplus', 'otimes', 'odot', 'coprod', 'bigcup', 'bigcap', 'bigsqcup',
        'subseteq', 'supseteq', 'approx', 'cong', 'equiv', 'sim', 'simeq',
        # 数学函数
        'frac', 'dfrac', 'cfrac', 'tfrac', 'sqrt', 'root', 'abs', 'norm',
        'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
        'sinh', 'cosh', 'tanh', 'coth', 'sech', 'csch',
        'log', 'ln', 'exp', 'lg', 'min', 'max', 'sum', 'prod', 'int',
        'oint', 'iint', 'iiint', 'iiiint', 'idotsint',
        'lim', 'inf', 'sup', 'arg', 'dim', 'deg', 'det', 'rank',
        # 上标下标等
        'over', 'atop', 'choose', 'binom', 'hat', 'widehat', 'tilde', 'widetilde',
        'bar', 'vec', 'dot', 'ddot', 'prime', 'dagger', 'ddagger',
        # 运算符
        'cdot', 'times', 'div', 'pm', 'mp', 'cap', 'cup', 'setminus',
        # 关系符号
        'leq', 'geq', 'neq', 'equiv', 'sim', 'simeq', 'approx', 'cong',
        'in', 'notin', 'ni', 'exists', 'forall', 'emptyset', 'infty',
        'to', 'partial', 'nabla',
        # 希腊字母（小写）
        'pi', 'theta', 'phi', 'psi', 'omega', 'alpha', 'beta', 'gamma', 'delta',
        'epsilon', 'zeta', 'eta', 'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi',
        'rho', 'sigma', 'tau', 'upsilon', 'chi',
        # 希腊字母（大写）
        'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 'Pi', 'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega',
        # 括号命令
        'left', 'right', 'middle',
        # 比较符号简写
        'le', 'ge', 'lt', 'gt',
        # 矩阵环境
        'bmatrix', 'matrix', 'pmatrix', 'vmatrix', 'Vmatrix', 'aligned', 'cases', 'array',
        # 堆叠命令
        'substack', 'underset', 'overset',
        # 其他常用
        'cdot', 'times', 'sum', 'prod', 'int', 'lim', 'sqrt',
        # 方程组相关
        'cases', 'aligned', 'gathered', 'split',
        # 特殊符号
        'aleph', 'beth', 'gimel', 'daleth',
        # 箭头扩展
        'longrightarrow', 'longleftarrow', 'Longrightarrow', 'Longleftarrow',
        'leftharpoonup', 'leftharpoondown', 'rightharpoonup', 'rightharpoondown',
        # 括号扩展
        'bigl', 'bigr', 'Bigl', 'Bigr',
        # 分数和根号
        'cfrac', 'dfrac', 'tfrac', 'root',
        # 求和积分
        'sum', 'prod', 'int', 'oint', 'iint', 'iiint', 'idotsint',
        # 极限
        'lim', 'liminf', 'limsup', 'varliminf', 'varlimsup',
        # 模运算
        'mod', 'pmod', 'bmod',
        # 对齐
        'hfill', 'vfill', 'hspace', 'vspace',
        # 文本模式
        'text', 'mbox', 'fbox',
        # 空格
        'quad', 'qquad', 'enspace', 'thinspace', 'negthinspace', 'medspace', 'negmedspace',
        # 颜色
        'color', 'textcolor', 'colorbox', 'fcolorbox',
    ]
    
    # 按命令长度降序排序，优先匹配长命令
    latex_commands.sort(key=len, reverse=True)
    
    # 先保护所有已存在的反斜杠命令（包括不在列表中的命令）
    # 这可以防止像 \begin 被错误地拆分成 \beg\in
    protected = {}
    temp_text = text
    cmd_count = 0
    
    # 匹配所有 \命令形式（\后面跟字母）
    # 使用占位符保护它们
    matches = list(re.finditer(r'\\[a-zA-Z]+', temp_text))
    # 从后往前处理，避免位置偏移
    for match in reversed(matches):
        full_cmd = match.group(0)  # 如 \begin, \frac 等
        placeholder = f'\x00CMD{cmd_count}\x00'
        temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
        protected[placeholder] = full_cmd
        cmd_count += 1
    
    # 然后恢复丢失反斜杠的命令
    cmd_pattern = r'(?<!\\)(' + '|'.join(re.escape(cmd) for cmd in latex_commands) + r')(?=\s|$|{|_|^|\(|\)|\+|\-|\*|\/|=|<|>|,|\.)'
    temp_text = re.sub(cmd_pattern, r'\\\1', temp_text)
    
    # 最后恢复被保护的命令
    for placeholder, original in protected.items():
        temp_text = temp_text.replace(placeholder, original)
    
    text = temp_text

    # 处理裸LaTeX数学表达式（没有被$包裹的）
    # 方法：找到所有不在 $...$ 或 $$...$$ 中的连续数学表达式区域，并用 $ 包裹
    
    # 先找到所有已存在的 $$...$$ 和 $...$ 区域
    # 创建标记数组，标记哪些位置在数学区域内
    in_math_region = [False] * len(text)
    
    # 匹配 $$...$$（使用非贪婪模式）
    double_dollar_pattern = r'\$\$.*?\$\$'
    for m in re.finditer(double_dollar_pattern, text, re.DOTALL):
        for i in range(m.start(), m.end()):
            if i < len(in_math_region):
                in_math_region[i] = True
    
    # 匹配 $...$（单行），但排除在$$区域内的
    # 使用负向前瞻和负向后顾来排除$$内部的$
    single_dollar_pattern = r'(?<!\$)\$[^$\n]+?\$(?!\$)'
    for m in re.finditer(single_dollar_pattern, text):
        # 检查是否在$$区域内
        is_in_double = False
        for i in range(m.start(), min(m.end(), len(in_math_region))):
            if in_math_region[i]:
                is_in_double = True
                break
        if not is_in_double:
            for i in range(m.start(), min(m.end(), len(in_math_region))):
                in_math_region[i] = True
    
    # 匹配连续的裸数学表达式区域
    # 支持：\命令、花括号内容、数字、字母、下划线、上标、运算符、空格等
    # 现在支持以字母开头的表达式（如 S\left(...\right)）
    
    def find_math_expression(text, start_pos):
        r"""从指定位置开始查找完整的数学表达式，处理嵌套花括号和\begin...\end环境"""
        pos = start_pos
        length = len(text)
        brace_count = 0
        in_math = False
        math_start = -1
        
        # 定义数学命令前缀（以反斜杠开头）
        cmd_pattern = re.compile(r'\\[a-zA-Z]+')
        
        # 追踪\begin环境的嵌套
        begin_stack = []
        
        while pos < length:
            char = text[pos]
            
            if char == '{':
                brace_count += 1
                if not in_math:
                    in_math = True
                    math_start = pos
                    # 向前查找是否有 \命令 在 { 之前
                    temp_pos = pos - 1
                    while temp_pos >= 0 and text[temp_pos] in ' \t':
                        temp_pos -= 1
                    if temp_pos >= 0:
                        # 检查是否是 \命令
                        cmd_match = cmd_pattern.search(text, max(0, temp_pos - 10), temp_pos + 1)
                        if cmd_match and cmd_match.end() >= temp_pos:
                            math_start = cmd_match.start()
            elif char == '}':
                brace_count -= 1
                # 如果在 \begin 环境中，只在环境结束时才返回
                if in_math and brace_count == 0 and not begin_stack:
                    # 找到匹配的闭合花括号，继续检查后面是否还有数学内容
                    end_pos = pos + 1
                    # 检查后面是否有 \right 等命令
                    while end_pos < length:
                        # 跳过空格和换行
                        if text[end_pos] in ' \t\n\r':
                            end_pos += 1
                            continue
                        # 检查是否是 \right 或其他命令
                        right_match = cmd_pattern.match(text, end_pos)
                        if right_match and right_match.group(0) in ('\\right', '\\left'):
                            # 继续查找直到匹配的花括号或括号
                            temp_pos = right_match.end()
                            inner_brace = 0
                            while temp_pos < length:
                                if text[temp_pos] == '{':
                                    inner_brace += 1
                                elif text[temp_pos] == '}':
                                    inner_brace -= 1
                                    if inner_brace == 0:
                                        end_pos = temp_pos + 1
                                        break
                                elif text[temp_pos] in '()[]|' and inner_brace == 0:
                                    end_pos = temp_pos + 1
                                    break
                                temp_pos += 1
                            if temp_pos >= length:
                                end_pos = length
                        else:
                            break
                    return (math_start, end_pos)
            elif char == '\\' and pos + 1 < length and text[pos + 1].isalpha():
                # 找到反斜杠命令，开始数学区域
                cmd_match = cmd_pattern.match(text, pos)
                if cmd_match:
                    cmd = cmd_match.group(0)
                    
                    # 处理 \begin{环境名}
                    if cmd == '\\begin':
                        if not in_math:
                            in_math = True
                            math_start = pos
                        # 查找环境名
                        temp_pos = cmd_match.end()
                        # 跳过空格和换行
                        while temp_pos < length and text[temp_pos] in ' \t\n\r':
                            temp_pos += 1
                        # 找到 { 并解析环境名
                        if temp_pos < length and text[temp_pos] == '{':
                            temp_pos += 1
                            env_name = ''
                            while temp_pos < length and text[temp_pos] != '}':
                                env_name += text[temp_pos]
                                temp_pos += 1
                            begin_stack.append(env_name)
                            # 跳过 } 后面的内容，继续查找
                            temp_pos += 1
                            # 处理环境内部内容，包括换行符 \\
                            inner_brace_count = 0
                            while temp_pos < length:
                                if text[temp_pos] == '{':
                                    inner_brace_count += 1
                                elif text[temp_pos] == '}':
                                    inner_brace_count -= 1
                                elif text[temp_pos] == '\\' and temp_pos + 1 < length:
                                    # 检查是否是 \\ 换行符
                                    if text[temp_pos + 1] == '\\':
                                        temp_pos += 2
                                        continue
                                    # 检查是否是 \end
                                    end_match = cmd_pattern.match(text, temp_pos)
                                    if end_match and end_match.group(0) == '\\end':
                                        # 找到 \end，让外层循环处理
                                        temp_pos -= 1
                                        break
                                temp_pos += 1
                        pos = temp_pos - 1  # 让循环继续处理
                    
                    # 处理 \end{环境名}
                    elif cmd == '\\end':
                        # 查找环境名
                        temp_pos = cmd_match.end()
                        while temp_pos < length and text[temp_pos] in ' \t\n\r':
                            temp_pos += 1
                        if temp_pos < length and text[temp_pos] == '{':
                            temp_pos += 1
                            env_name = ''
                            while temp_pos < length and text[temp_pos] != '}':
                                env_name += text[temp_pos]
                                temp_pos += 1
                            # 弹出匹配的 \begin
                            if begin_stack and begin_stack[-1] == env_name:
                                begin_stack.pop()
                            # 如果栈为空，说明这是环境的结束
                            if not begin_stack and in_math:
                                return (math_start, temp_pos + 1)
                        pos = temp_pos - 1  # 让循环继续处理
                    
                    elif not in_math:
                        in_math = True
                        math_start = pos
                        pos = cmd_match.end() - 1  # 让循环继续处理
            
            pos += 1
        
        # 如果还在数学区域中，返回找到的部分
        if in_math and math_start >= 0:
            return (math_start, pos)
        
        return None
    
    # 扫描文本，找到所有裸数学表达式区域
    bare_matches = []
    pos = 0
    while pos < len(text):
        # 跳过空白
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        
        # 检查当前位置是否在已标记的数学区域内
        if pos < len(in_math_region) and in_math_region[pos]:
            pos += 1
            continue
        
        # 检查是否以 \ 开头或字母开头后跟 \
        if pos < len(text):
            if text[pos] == '\\' and pos + 1 < len(text) and text[pos + 1].isalpha():
                result = find_math_expression(text, pos)
                if result:
                    start, end = result
                    # 检查是否完全在非数学区域内
                    is_valid = True
                    for i in range(start, min(end, len(in_math_region))):
                        if in_math_region[i]:
                            is_valid = False
                            break
                    if is_valid:
                        content = text[start:end].strip()
                        # 排除纯间距命令
                        skip_commands = {'\\quad', '\\qquad', '\\hspace', '\\vspace', '\\hfill', '\\vfill'}
                        if content and len(content) > 1 and content not in skip_commands:
                            bare_matches.append((start, end))
                    pos = end
                    continue
            elif text[pos].isalpha():
                # 检查字母后面是否紧跟 \ 命令（如 S\left）
                temp_pos = pos + 1
                while temp_pos < len(text) and text[temp_pos] in ' \t':
                    temp_pos += 1
                if temp_pos < len(text) and text[temp_pos] == '\\':
                    # 这是一个以字母开头的数学表达式
                    result = find_math_expression(text, temp_pos)
                    if result:
                        start, end = result
                        # 扩展开始位置到字母
                        start = pos
                        # 检查是否完全在非数学区域内
                        is_valid = True
                        for i in range(start, min(end, len(in_math_region))):
                            if in_math_region[i]:
                                is_valid = False
                                break
                        if is_valid:
                            content = text[start:end].strip()
                            if content and len(content) > 1:
                                bare_matches.append((start, end))
                        pos = end
                        continue
        
        pos += 1
    
    # 如果找到裸数学表达式，用$包裹它们（从后往前处理避免位置偏移）
    if bare_matches:
        new_text = text
        # 按位置从后往前处理
        for start, end in reversed(bare_matches):
            # 在匹配前后添加$
            new_text = new_text[:start] + '$' + new_text[start:end] + '$' + new_text[end:]
        text = new_text

    # 在选择题选项之间添加换行符，使每个选项独立一行
    # 匹配模式: (A)...(B)... → 在 (B) 前添加换行
    # 支持的格式: (A) （A） A) A. A、 A．
    # 选项标签通常出现在 \qquad 或 \quad 之后，或者行首，而不是数学表达式中间
    # 使用正向后瞻确保前面是 \qquad 或 \quad 或行首

    # 先处理 \qquad 或 \quad 之后的选项
    text = re.sub(r'(\\qquad|\\quad)\s*\(([A-D])\)', r'\1\n(\2)', text)

    # 处理行首的选项标签（前面是换行或字符串开头）
    text = re.sub(r'(?<=\n)\s*\(([A-D])\)', r'\n(\1)', text)
    text = re.sub(r'^\s*\(([A-D])\)', r'\n(\1)', text)

    # 处理中文括号格式
    text = re.sub(r'(\\qquad|\\quad)\s*（([A-D])）', r'\1\n（\2）', text)

    # 处理不带左括号的选项格式 A) 或 A. 或 A、
    text = re.sub(r'(\\qquad|\\quad)\s*([A-D][)．、。])', r'\1\n\2', text)

    segments = []
    # 先匹配 $$...$$（长匹配优先），再匹配 $...$
    pattern = r'(\$\$.*?\$\$|\$[^$\n]+?\$)'
    last = 0

    for m in re.finditer(pattern, text, re.DOTALL):
        # 前面的纯文本
        if m.start() > last:
            plain = text[last:m.start()]
            # 保留换行符和内部格式，只去除首尾多余的空白（不包括换行）
            lines = plain.split('\n')
            # 去除开头空行，保留结尾换行符
            if lines and not lines[0].strip():
                lines = lines[1:]
            # 去除每行开头的多余空格
            lines = [line.lstrip() if i > 0 else line for i, line in enumerate(lines)]
            plain = '\n'.join(lines)
            if plain:
                segments.append({"type": "text", "content": plain})

        math_block = m.group(0)
        if math_block.startswith('$$') and math_block.endswith('$$'):
            inner = math_block[2:-2].strip()
            if inner:
                segments.append({"type": "display_math", "content": inner})
        elif math_block.startswith('$') and math_block.endswith('$'):
            inner = math_block[1:-1].strip()
            if inner:
                segments.append({"type": "inline_math", "content": inner})

        last = m.end()

    # 尾部残余文本
    if last < len(text):
        plain = text[last:]
        # 保留换行符，只去除尾部多余空格（不包括换行）
        lines = plain.split('\n')
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        plain = '\n'.join(lines)
        # 清除残余的孤立 $
        plain = plain.replace('$', '')
        if plain:
            segments.append({"type": "text", "content": plain})

    # 合并相邻的短文本片段，避免过度分割
    # 当连续的文本片段都很短时，合并成一个片段
    if segments:
        merged = []
        current_text = []
        for seg in segments:
            if seg["type"] == "text":
                # 检查是否是短文本（少于20个字符且不是空行）
                content = seg["content"].strip()
                if len(content) < 20 and content:
                    current_text.append(seg["content"])
                else:
                    # 合并之前累积的短文本
                    if current_text:
                        merged.append({"type": "text", "content": ''.join(current_text)})
                        current_text = []
                    merged.append(seg)
            else:
                # 非文本类型，先合并累积的短文本
                if current_text:
                    merged.append({"type": "text", "content": ''.join(current_text)})
                    current_text = []
                merged.append(seg)
        # 处理剩余的短文本
        if current_text:
            merged.append({"type": "text", "content": ''.join(current_text)})
        segments = merged

    return _demote_subquestion_math_labels(segments)


def render_segments(segments: list[dict]) -> str:
    """
    将分离后的片段重新组装为可渲染的字符串。

    text → 原样输出
    inline_math → $...$
    display_math → $$...$$
    """
    parts = []
    for seg in segments:
        t = seg["type"]
        c = seg["content"]
        if t == "text":
            parts.append(c)
        elif t == "inline_math":
            parts.append(f"${c}$")
        elif t == "display_math":
            parts.append(f"$$\n{c}\n$$")
    return '\n\n'.join(parts)


def has_math(text: str) -> bool:
    """快速判断文本是否包含数学内容。"""
    if not text:
        return False
    return bool(re.search(r'[\$\\\^_{}]|\\[a-zA-Z]+', text))


def _strip_math_delimiters(text: str) -> str:
    """Remove Markdown/KaTeX math delimiters from a string intended for st.latex()."""
    if not text:
        return text

    s = str(text).strip()
    # LLMs often put only an opening $$ in JSON latex blocks. st.latex() is
    # already in math mode, so all delimiter dollars are display pollution here.
    while s.startswith("$$"):
        s = s[2:].lstrip()
    while s.endswith("$$"):
        s = s[:-2].rstrip()
    while s.startswith("$"):
        s = s[1:].lstrip()
    while s.endswith("$"):
        s = s[:-1].rstrip()
    return s.replace("$$", "").replace("$", "").strip()


# ── P32: Greek command corruption repair ──

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
    "phi": "phi",
}
_GREEK_CORRUPTION_RE = re.compile(
    r'\\(' + '|'.join(map(re.escape, sorted(_GREEK_CORRUPTION_MAP.keys(), key=len, reverse=True))) + r')(?=[^A-Za-z]|$)'
)


def _repair_corrupted_greek_commands(text: str) -> str:
    """Fix LLM-corrupted Greek LaTeX commands: \\alphas → \\alpha, etc."""
    def _replace(m: re.Match) -> str:
        corrupted = m.group(1)
        fixed = _GREEK_CORRUPTION_MAP.get(corrupted)
        if fixed and fixed != corrupted:
            return '\\' + fixed
        return m.group(0)
    return _GREEK_CORRUPTION_RE.sub(_replace, text)


def sanitize_latex_for_render(text: str) -> str:
    """Normalize arbitrary LLM LaTeX into a string safe for st.latex().

    This is intentionally conservative: it does not solve math, it only removes
    delimiters/escape pollution and repairs token-level issues that commonly make
    KaTeX show raw red source instead of rendered math.
    """
    if text is None:
        return ""

    s = _strip_math_delimiters(str(text))
    if not s:
        return ""

    # Fix Python/JSON escape-sequence corruption of common LaTeX commands.
    # When LaTeX passes through non-raw-string Python or improperly escaped JSON,
    # \f → form feed (\x0c), \b → backspace (\x08), \t → tab (\x09), etc.
    # This destroys \frac, \begin, \times, \theta and many other commands.
    # We use str.replace with the control char + common following letters.
    _bs = chr(92)  # backslash
    _escape_fixes = [
        ('\x0c', _bs + 'f'),   # form feed  → \f (frac, flat, forall, ...)
        ('\x08', _bs + 'b'),   # backspace  → \b (begin, binom, bar, big, ...)
    ]
    for _corrupted, _prefix in _escape_fixes:
        s = s.replace(_corrupted, _prefix)

    # Tab (\x09) → only fix if followed by known LaTeX letters
    for _suffix in ('imes', 'ext', 'an', 'heta', 'au', 'ilde', 'frac', 'o'):
        s = s.replace('\x09' + _suffix, _bs + 't' + _suffix)

    # Newline (\x0a) in math context → restore \n command
    for _suffix in ('eq ', 'eq.', 'eq,', 'eq;', 'otin', 'abla'):
        s = s.replace('\x0a' + _suffix, _bs + 'n' + _suffix)
    # Bare \ne (newline + 'e' without more letters → likely \ne)
    s = s.replace('\x0ae ', _bs + 'ne ')
    s = s.replace('\x0ae,', _bs + 'ne,')

    # Carriage return (\x0d) → restore \r commands
    for _suffix in ('ight', 'ho', 'ightarrow', 'ightharpoonup'):
        s = s.replace('\x0d' + _suffix, _bs + 'r' + _suffix)

    # JSON or Markdown escape leftovers.
    s = s.replace("\\\\(", "\\(").replace("\\\\)", "\\)")
    s = s.replace("\\\\[", "\\[").replace("\\\\]", "\\]")
    s = s.replace("\\'", "'")

    # Double-escaped commands: \\frac, \\lim, \\alpha -> \frac, \lim, \alpha.
    # Preserve matrix row separators because they are followed by whitespace or &,
    # not a command letter.
    s = re.sub(r'\\\\(?=[A-Za-z])', r'\\', s)

    # Quantifier + variable frequently arrives glued as \forallx or \existsx_1.
    s = re.sub(r'\\(forall|exists)(?=([A-Za-z]|[A-Za-z]_\d|[A-Za-z]_\{))', r'\\\1 ', s)

    # Common textual shorthands that KaTeX handles better with explicit spacing.
    s = re.sub(r'\\in(?=\()', r'\\in ', s)
    s = re.sub(r'\\to(?=[A-Za-z0-9])', r'\\to ', s)
    # Relation arrows are sometimes glued to the next symbol, e.g.
    # "\Rightarrowf(0)" becomes an unknown KaTeX command and renders red.
    s = re.sub(
        r'\\(Rightarrow|Leftarrow|Leftrightarrow|Longrightarrow|Longleftarrow|Longleftrightarrow|rightarrow|leftarrow)(?=[A-Za-z])',
        r'\\\1 ',
        s,
    )

    # Some LLMs emit \neq split by markdown fragments; normalize common variants.
    s = s.replace("\\ne q", "\\ne").replace("\\neq", "\\ne")

    # Remove outer \( \) / \[ \] if they slipped through.
    if s.startswith("\\(") and s.endswith("\\)"):
        s = s[2:-2].strip()
    if s.startswith("\\[") and s.endswith("\\]"):
        s = s[2:-2].strip()

    # LLMs occasionally glue spacing commands to the next variable, e.g.
    # "\qquadb" instead of "\qquad b". KaTeX treats the glued form as an
    # unknown command and renders it as red raw source.
    s = re.sub(r'\\(qquad|quad)(?=[A-Za-z])', r'\\\1 ', s)
    s = re.sub(r'\\,(?=[A-Za-z])', r'\\, ', s)

    # P32: Fix corrupted Greek commands (\alphas → \alpha, etc.)
    s = _repair_corrupted_greek_commands(s)

    # Plain R after membership is meant as the real-number set in generated
    # solutions. Normalize the common bare form before rendering.
    s = re.sub(r'\\in\s+R\b', r'\\in \\mathbb{R}', s)

    s = _clean_formula_tail(auto_fix_brackets(s))
    return s.strip()


# ═══════════════════════════════════════════════
# P37.2: Raw/invalid formula hard gate
# ═══════════════════════════════════════════════

_INVALID_FORMULA_PATTERNS = [
    re.compile(r'\\int[A-Z][a-z]+'),
    re.compile(r'(?<!\\mathrm\{d\})(?<!\\,)\\d[xyztu](?![a-zA-Z])'),
    re.compile(r'\\frac\\partial'),
    re.compile(r'\\partial\s*\{[^}]*\}(?!\s*\{)'),
    re.compile(r'\\mathrm\{d\}[xyztu]\s+[a-zA-Z]'),
    re.compile(r'\$\S+\$\s*\('),
    re.compile(r'(?m)^\s*\$\$\s*$'),
    re.compile(r'(?m)^\s*\\Rightarrow\s*$'),
    re.compile(r'(?s)\\begin\{[^}]*\}(?!.*?\\end\{)'),
    re.compile(r'(?<![\\a-zA-Z])int_\d'),
    re.compile(r'(?<![\\a-zA-Z])frac\{'),
    re.compile(r'(?<![\\a-zA-Z])partial\s+[a-zA-Z]'),
    re.compile(r'\\var[φϕ]'),
    re.compile(r'\\[φϕ]'),
    re.compile(r'\\frac\{\s*\\partial\s*\}[^{]'),
    re.compile(r'(?<!\\)mathrmd[txuyz]'),
]


def is_raw_or_invalid_latex_formula(text: str) -> bool:
    """Check if a formula string contains raw or invalid LaTeX."""
    if not text:
        return False
    s = str(text).strip()
    if not s:
        return False
    for pat in _INVALID_FORMULA_PATTERNS:
        if pat.search(s):
            return True
    return False


def try_repair_formula(text: str) -> str | None:
    """Attempt to repair a raw/invalid formula. Returns repaired text or None if unrepairable."""
    if not text:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = sanitize_latex_for_render(s)
    s = re.sub(r'\\var[φϕ]', r'\\varphi', s)
    s = re.sub(r'\\[φ]', r'\\phi', s)
    s = re.sub(r'(?<!\\)mathrmd([txuyz])', r'\\mathrm{d}\1', s)
    s = re.sub(r'\\int([A-Z])([a-z]+)', r'\\int_{\\mathrm{\1}}', s)
    s = re.sub(r'\\frac\\partial', r'\\frac{\\partial}', s)
    if is_raw_or_invalid_latex_formula(s):
        return None
    return s


_MATHY_COMMAND_RE = re.compile(
    r'\\(?:'
    r'frac|dfrac|tfrac|cfrac|sqrt|lim|sum|prod|int|iint|iiint|oint|'
    r'sin|cos|tan|cot|sec|csc|ln|log|exp|arcsin|arccos|arctan|'
    r'forall|exists|in|notin|subset|subseteq|cup|cap|to|Rightarrow|'
    r'Leftarrow|rightarrow|leftarrow|leq|geq|ne|neq|approx|sim|'
    r'alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|xi|rho|'
    r'sigma|phi|omega|Gamma|Delta|Theta|Lambda|Pi|Sigma|Omega|'
    r'begin|end|boxed|left|right|mathrm|mathbf|mathbb|mathcal'
    r')(?=\b|[_{([<\s]|$)'
)


def _looks_like_standalone_math(line: str) -> bool:
    """Heuristic for lines that should be rendered as one display formula."""
    s = (line or "").strip()
    if not s:
        return False

    raw = _strip_math_delimiters(s)
    if not raw:
        return False

    # A line containing CJK text is never standalone display math \u2014 it's
    # mixed text+math that should be split by $...$ delimiters, not wrapped
    # entirely in $$...$$. Lines starting with $ like $(1)$, $(2)$ are
    # inline sub-question markers, not display math wrappers.
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', raw))
    if has_cjk:
        return False

    # 判断是否是短的简单表达式（如 f(x), f(0)=0, f'(x)=2x-2）
    # 这些应该作为 inline math 处理，而不是独立的块级公式
    if len(raw) < 30:
        # 检查是否包含等号或箭头
        if '=' in raw or '→' in raw or '\\to' in raw:
            # 简单的赋值或等式，作为 inline math
            return False
        # 简单的函数表达式如 f(x), g'(x) 等
        if re.match(r'^[a-zA-Z]+\'?\([^)]*\)$', raw):
            return False
        # 简单的区间表示如 [0,2]
        if re.match(r'^\[?\s*\d+\s*,\s*\d+\s*\]?$', raw):
            return False

    # 只有复杂的数学命令才触发块级公式识别
    # 排除简单的函数如 ln, sin, cos 等，它们应该作为 inline math
    complex_commands = [r'\\frac', r'\\dfrac', r'\\sum', r'\\prod', r'\\int', 
                        r'\\iint', r'\\iiint', r'\\oint', r'\\sqrt', r'\\lim',
                        r'\\begin', r'\\left', r'\\right', r'\\boxed', r'\\int_', r'\\sum_']
    has_complex_command = any(cmd in raw for cmd in complex_commands)
    
    if has_complex_command:
        return True

    # Unicode 数学符号：只有大型运算符才作为块级公式
    if re.search(r'[∑∫∏√∞]', raw):
        return True

    # 对于其他情况，不作为独立的块级公式
    # 它们会在后续的 split_latex_text 中被正确处理为 inline math
    return False


def _normalize_math_lines_for_split(text: str) -> str:
    """Wrap standalone math lines and repair unbalanced delimiters before splitting."""
    if not text:
        return text

    normalized_lines = []
    for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = line.strip()
        # Never re-wrap lines that already have $$...$$ or $...$ delimiters
        already_wrapped = (
            stripped.startswith("$$") or stripped.startswith("$")
            or stripped.startswith(r"\[") or stripped.startswith(r"\(")
        )
        if not already_wrapped and _looks_like_standalone_math(stripped):
            latex = sanitize_latex_for_render(stripped)
            normalized_lines.append(f"$$\n{latex}\n$$" if latex else "")
        else:
            normalized_lines.append(line)

    out = "\n".join(normalized_lines)

    # Merge consecutive short text lines into paragraphs.
    # LLMs often break a sentence across multiple lines ("曲线\n的渐近线"),
    # causing st.markdown to render a line break mid-sentence.
    out = _merge_short_text_lines(out)

    return out


def _merge_short_text_lines(text: str) -> str:
    """Merge consecutive short non-math lines into paragraphs.

    Protects math structure from being damaged by over-eager merging:
      - Display math ($$...$$) is never merged
      - Lines with inline math ($...$) flush the buffer to keep math context
      - List items (1. 2. ①) start new blocks
      - Structural markers (证明：解：定理：) start new blocks
      - Sentence-ending lines (。！？) flush when long enough
    """
    _SENTENCE_END = re.compile(r'[。！？.!?]$')
    _BLANK = re.compile(r'^\s*$')
    _LIST_ITEM = re.compile(r'^\s*(?:\d+[.、．)]|\(?\d+\)|[①②③④⑤⑥⑦⑧⑨⑩])')
    _STRUCT_MARKER = re.compile(
        r'^\s*(?:证明|解|答|解析|定理|引理|推论|定义|注|分析|已知|求证|求|试证|试求)\s*[：:]\s*'
    )
    _HAS_INLINE_MATH = re.compile(r'(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)')

    lines = text.split('\n')
    merged = []
    buf = []

    def _flush_buf():
        if buf:
            merged.append(''.join(buf))
            buf.clear()

    for line in lines:
        stripped = line.strip()

        # Structural boundaries: never merge across these
        is_boundary = (
            stripped.startswith('$$') or         # display math
            _BLANK.match(stripped) or            # blank line
            _LIST_ITEM.match(stripped) or        # list item
            _STRUCT_MARKER.match(stripped)       # 证明：/ 解：/ 定理：
        )

        if is_boundary:
            _flush_buf()
            merged.append(line)
            continue

        # Line with inline math: flush buffer first, then add as its own line
        # to prevent math from being buried in merged text
        if _HAS_INLINE_MATH.search(stripped):
            _flush_buf()
            merged.append(line)
            continue

        # Sentence-ending line: flush as a complete paragraph
        if _SENTENCE_END.search(stripped):
            _flush_buf()
            merged.append(line)
            continue

        # Otherwise: short continuation text, merge with buffer
        buf.append(line)

    _flush_buf()
    return '\n'.join(merged)


# ═══════════════════════════════════════════════
# 5. AST-first 渲染器（推荐）
# ═══════════════════════════════════════════════

def _is_inline_math(content: str) -> bool:
    """Determine if a LaTeX expression should render as inline ($...$) or block (display).

    Rules (order matters):
      - Contains \\begin, \\\\, \\displaystyle, align, cases, array → block
      - Contains multi-line content → block
      - Contains display-oriented commands (\\sum, \\int, \\prod) with limits → block
      - Otherwise → inline

    Length is NOT used as a heuristic — it causes adjacent formulas of similar
    type but different length to render inconsistently. The segment type already
    encodes the author's intent: display_math always renders as st.latex(),
    inline_math always renders as st.markdown("$...$").
    """
    _bs = chr(92)
    # Structural block markers — always force display mode
    _block_cmds = [
        _bs + 'begin', _bs + 'displaystyle',
        _bs + 'align', _bs + 'cases', _bs + 'array',
    ]
    for cmd in _block_cmds:
        if cmd in content:
            return False
    # LaTeX line breaks
    if _bs + _bs in content:
        return False
    # Multi-line content
    if '\n' in content:
        return False
    return True


# ── P35.1: Independent equation list detection & formatting ──────────────

def is_independent_equation_list(latex: str) -> bool:
    """Detect comma-separated independent equations that would render as a broken chain."""
    if not latex or not isinstance(latex, str):
        return False
    s = latex.strip()
    if any(env in s for env in (
        "\\begin{aligned}", "\\begin{align}", "\\begin{eqnarray}",
        "\\begin{gather}", "\\begin{multline}", "\\begin{cases}",
    )):
        return False
    if "\\Rightarrow" in s or "⇒" in s:
        return False
    segments = _split_top_level_commas(s)
    if len(segments) < 2:
        return False
    eq_segments = 0
    for seg in segments:
        if not seg:
            return False
        eq_pos = _find_top_level_equals(seg)
        if eq_pos < 1:
            return False
        lhs = seg[:eq_pos].strip()
        rhs = seg[eq_pos + 1:].strip()
        if not lhs or not rhs:
            return False
        eq_segments += 1
    return eq_segments >= 2


def _find_top_level_equals(s: str) -> int:
    """Find the first '=' at brace depth 0. Returns -1 if not found."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(depth - 1, 0)
        elif ch == "=" and depth == 0:
            return i
    return -1


def format_independent_equation_list(latex: str) -> str:
    """Format comma-separated independent equations as a cases block (one equation per row)."""
    if not latex or not isinstance(latex, str):
        return latex
    s = latex.strip()

    # P41.2: Don't break existing LaTeX environments
    if _RE_LATEX_ENV.search(s):
        return s
    cases_block = _try_independent_equations_cases_block(s)
    if cases_block:
        return cases_block
    return s


def _try_format_equation_list(content: str) -> str | None:
    """If content is an independent equation list, return formatted aligned version."""
    if is_independent_equation_list(content):
        return format_independent_equation_list(content)
    return None


def _inject_katex_css() -> None:
    """Inject KaTeX display fix CSS once per session.

    Fixes:
      - Prevent overflow:hidden from clipping superscripts/radicals
      - Ensure display math has consistent margins
      - Set adequate line-height for inline math with CJK text
    """
    import streamlit as st
    if st.session_state.get("_katex_css_injected"):
        return
    st.session_state["_katex_css_injected"] = True
    st.markdown("""
        <style>
        /* Prevent clipping of superscripts, radicals, and fractions */
        .katex-display,
        .katex-display > .katex {
            overflow: visible !important;
        }
        .katex {
            overflow: visible !important;
        }
        /* Ensure display math has breathing room */
        .katex-display {
            margin: 0.75em 0 !important;
        }
        /* Prevent display-math centering from bleeding into following CJK text */
        [data-testid="stMarkdownContainer"] {
            text-align: left !important;
        }
        /* Fix CJK + inline math baseline */
        .katex-html {
            overflow: visible !important;
        }
        /* Ensure Streamlit containers don't clip math */
        [data-testid="stVerticalBlock"] .katex-display {
            overflow: visible !important;
            max-width: 100%;
        }
        @media (max-width: 768px) {
            .katex-display,
            [data-testid="stVerticalBlock"] .katex-display,
            [data-testid="stLatex"] {
                max-width: 100% !important;
                overflow-x: auto !important;
                overflow-y: visible !important;
                white-space: nowrap !important;
                -webkit-overflow-scrolling: touch;
                touch-action: pan-x;
            }
            .katex-display > .katex,
            .katex-display .katex-html,
            [data-testid="stLatex"] .katex,
            [data-testid="stLatex"] .katex-html {
                max-width: none !important;
                overflow: visible !important;
                white-space: nowrap !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)


def render_ast(segments: list[dict], *, use_st_latex: bool = False) -> None:
    """
    AST-first 渲染器：inline vs block 严格区分。

    关键：连续的 text + inline_math 合并为单个 st.markdown() 调用。
    display_math 在单独调用 flush 关闭前一个 markdown 段落后，
    用 st.markdown("$$...$$") 独立渲染，避免块级居中污染后续中文。

    分派规则:
      - text + inline_math → 合并 → st.markdown(连续段落)
      - display_math       → 先 flush → st.markdown("$$...$$")
      - latex (兼容)       → 先 flush → inline 用 $...$，block 用 $$...$$

    使用示例:
        from latex_utils import split_latex_text, render_ast
        segments = split_latex_text(raw_text)
        render_ast(segments)
    """
    import streamlit as st

    _inject_katex_css()

    # 合并连续的 text + inline_math 为单个 markdown 块
    buf = []
    def _flush():
        if buf:
            md = "".join(buf)
            md = md.rstrip('\n').lstrip()
            if md:
                try:
                    st.markdown(md)
                except Exception:
                    st.text(md[:500])
            buf.clear()

    last_was_inline_math = False
    for seg in segments:
        t = seg["type"]
        c = seg["content"]
        if not c:
            continue
        try:
            if t == "text":
                buf.append(c)
                last_was_inline_math = False
            elif t == "inline_math":
                c = sanitize_latex_for_render(c)
                if not c:
                    continue
                # 在连续的 inline_math 之间添加空格，避免 $$ 相邻
                if last_was_inline_math:
                    buf.append(" ")
                buf.append(f"${c}$")
                last_was_inline_math = True
            elif t == "display_math":
                _flush()
                c = sanitize_latex_for_render(c)
                if not c:
                    continue
                # P35.1: detect independent equation list → aligned group
                formatted = _try_format_equation_list(c)
                if formatted is not None:
                    c = formatted
                # Use st.markdown instead of st.latex to keep display math
                # in the markdown flow and prevent block-element centering
                # from bleeding into subsequent CJK inline text.
                st.markdown(f"$$\n{c}\n$$")
                last_was_inline_math = False
            elif t == "latex":
                _flush()
                c = sanitize_latex_for_render(c)
                if not c:
                    continue
                if _is_inline_math(c):
                    st.markdown(f"${c}$")
                elif use_st_latex:
                    st.latex(c)
                else:
                    st.markdown(f"$$\n{c}\n$$")
                last_was_inline_math = False
        except Exception:
            try:
                st.text(c[:500])
            except Exception:
                pass
    _flush()


def render_latex_ast(text: str) -> None:
    """
    一键 AST 渲染：clean_markdown → split → render_ast。

    这是完整管道的终极入口：
      1. clean_markdown  — 清理 Markdown 污染
      2. split_latex_text — 分离文本和公式为 AST
      3. render_ast       — AST-first 渲染

    替代旧的 render_latex() 中 safe_latex → normalize_latex_style → st.markdown
    的单通道做法。
    """
    if not text:
        return
    text = clean_markdown(text)
    segments = split_latex_text(text)
    render_ast(segments)


def safe_latex(text: str) -> str:
    """Backward-compatible safe LaTeX sanitizer used by legacy renderers."""
    try:
        from math_sanitizer import safe_latex as _safe_latex
        return _safe_latex(text)
    except Exception:
        if not text:
            return text
        return auto_fix_brackets(normalize_latex_style(str(text)))


# ═══════════════════════════════════════════════════════════════
# 6. 结构化数学渲染 — 根本解决方案
# ═══════════════════════════════════════════════════════════════
#
# 核心原则:
#   LLM 不输出 markdown，只输出结构化 JSON。
#   Renderer 控制全部显示。
#
# 架构:
#   LLM → StructuredSolution (JSON) → render_structured() → Streamlit
#
# 与旧方案的区别:
#   旧: LLM → markdown 文本 → repair → sanitize → normalize → st.markdown
#   新: LLM → 结构化 JSON → 每个 block 走自己的渲染通道
# ═══════════════════════════════════════════════════════════════

import json as _json
from enum import Enum as _Enum
from typing import Optional as _Optional


class MathOperation(str, _Enum):
    """数学操作类型 — 决定渲染样式"""
    CLASSIFY = "classify"               # 识别题型
    RECALL = "recall"                   # 回忆公式/定理
    SUBSTITUTE = "substitute"           # 代入
    SIMPLIFY = "simplify"               # 化简
    EXPAND = "expand"                   # 展开
    FACTOR = "factor"                   # 因式分解
    DIFFERENTIATE = "differentiate"     # 求导
    INTEGRATE = "integrate"             # 积分
    SOLVE = "solve"                     # 求解
    EVALUATE = "evaluate"               # 计算/求值
    APPLY_THEOREM = "apply_theorem"     # 应用定理
    TRANSFORM = "transform"             # 变换
    CONCLUDE = "conclude"               # 得出结论
    CHECK = "check"                     # 验证


# operation → 中文标签 + 颜色
_OP_META = {
    "classify":        ("识别题型", "#6b7280"),
    "recall":          ("回忆定理", "#2563eb"),
    "substitute":      ("代入",     "#7c3aed"),
    "simplify":        ("化简",     "#059669"),
    "expand":          ("展开",     "#059669"),
    "factor":          ("因式分解", "#059669"),
    "differentiate":   ("求导",     "#d97706"),
    "integrate":       ("积分",     "#d97706"),
    "solve":           ("求解",     "#dc2626"),
    "evaluate":        ("计算",     "#dc2626"),
    "apply_theorem":   ("应用定理", "#2563eb"),
    "transform":       ("变换",     "#7c3aed"),
    "conclude":        ("结论",     "#0891b2"),
    "check":           ("验证",     "#0891b2"),
}


@dataclass
class MathBlock:
    """
    数学内容块 — 最小渲染单元。

    LLM 输出的每个 block 要么是 text，要么是 latex，绝不混合。
    """
    type: str                           # "text" | "latex"
    content: str                        # 内容
    display: str = "inline"             # "inline" | "block" | "hidden"
    operation: str = ""                 # MathOperation 值，可选


@dataclass
class MathStep:
    """解题步骤 — 包含多个 MathBlock + 一个操作标签"""
    blocks: list                        # list[MathBlock]
    label: str = ""                     # "步骤1", "步骤2", ...
    operation: str = ""                 # 本步骤的主操作类型


@dataclass
class StructuredSolution:
    """
    结构化解题方案 — LLM 应输出的唯一格式。

    LLM 不应输出 markdown，而应输出此结构。
    Renderer 控制全部显示。

    示例:
        {
          "steps": [
            {
              "label": "步骤1",
              "blocks": [
                {"type": "text", "content": "识别极限类型"},
                {"type": "latex", "content": "\\lim_{x\\to 0} \\frac{\\sin x}{x}", "display": "block"},
                {"type": "text", "content": "这是 0/0 型极限"}
              ],
              "operation": "classify"
            },
            {
              "label": "步骤2",
              "blocks": [
                {"type": "text", "content": "应用洛必达法则"},
                {"type": "latex", "content": "\\lim_{x\\to 0} \\frac{\\sin x}{x} = 1", "display": "block"}
              ],
              "operation": "apply_theorem"
            }
          ],
          "final_answer": {
            "type": "latex",
            "content": "1"
          },
          "metadata": {
            "knowledge_points": ["极限", "洛必达法则"],
            "difficulty": "中等"
          }
        }
    """
    steps: list                          # list[MathStep]
    final_answer: _Optional[dict] = None # MathBlock dict
    metadata: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════
# 6a. 结构化方案构建器
# ═══════════════════════════════════════════════

def make_block(type: str, content: str, display: str = "inline", operation: str = "") -> dict:
    """创建一个 MathBlock dict。"""
    block = {"type": type, "content": content}
    if display != "inline":
        block["display"] = display
    if operation:
        block["operation"] = operation
    return block


def make_text(text: str) -> dict:
    """快捷创建 text block。"""
    return make_block("text", text)


def make_latex(expr: str, display: str = "inline") -> dict:
    """快捷创建 latex block。"""
    return make_block("latex", expr, display=display)


def make_step(label: str, blocks: list, operation: str = "") -> dict:
    """创建一个 MathStep dict。"""
    step = {"label": label, "blocks": blocks}
    if operation:
        step["operation"] = operation
    return step


def make_solution(steps: list, final_answer: dict = None, metadata: dict = None) -> dict:
    """创建一个 StructuredSolution dict。"""
    sol = {"steps": steps}
    if final_answer:
        sol["final_answer"] = final_answer
    if metadata:
        sol["metadata"] = metadata
    return sol


# ═══════════════════════════════════════════════
# 6b. 结构化方案验证
# ═══════════════════════════════════════════════

def validate_structured(solution: dict) -> tuple[bool, list[str]]:
    """
    验证结构化解题方案是否合法。

    返回 (is_valid, errors)。
    """
    errors = []

    if not isinstance(solution, dict):
        return False, ["solution 必须是 dict"]

    if "steps" not in solution:
        errors.append("缺少 'steps' 字段")
        return False, errors

    if not isinstance(solution["steps"], list) or len(solution["steps"]) == 0:
        errors.append("'steps' 必须是非空 list")
        return False, errors

    valid_types = {"text", "latex", "latex_display", "latex_inline"}
    valid_displays = {"inline", "block", "hidden"}
    valid_operations = set(_OP_META.keys())

    for i, step in enumerate(solution["steps"]):
        if not isinstance(step, dict):
            errors.append(f"steps[{i}] 必须是 dict")
            continue

        if "blocks" not in step:
            errors.append(f"steps[{i}] 缺少 'blocks'")
            continue

        blocks = step["blocks"]
        if not isinstance(blocks, list):
            errors.append(f"steps[{i}].blocks 必须是 list")
            continue

        for j, block in enumerate(blocks):
            if not isinstance(block, dict):
                errors.append(f"steps[{i}].blocks[{j}] 必须是 dict")
                continue

            t = block.get("type", "")
            if t not in valid_types:
                errors.append(f"steps[{i}].blocks[{j}].type='{t}' 无效，必须是 text 或 latex")

            if "content" not in block:
                errors.append(f"steps[{i}].blocks[{j}] 缺少 'content'")

            d = block.get("display", "inline")
            if d not in valid_displays:
                errors.append(f"steps[{i}].blocks[{j}].display='{d}' 无效")

            op = block.get("operation", "")
            if op and op not in valid_operations:
                errors.append(f"steps[{i}].blocks[{j}].operation='{op}' 无效")

        op = step.get("operation", "")
        if op and op not in valid_operations:
            errors.append(f"steps[{i}].operation='{op}' 无效")

    if "final_answer" in solution and solution["final_answer"]:
        fa = solution["final_answer"]
        if isinstance(fa, dict):
            _fa_valid_types = valid_types | {"choice", "formula", "multi_part"}
            if fa.get("type") not in _fa_valid_types:
                errors.append("final_answer.type 无效")
            if "content" not in fa:
                errors.append("final_answer 缺少 'content'")

    return len(errors) == 0, errors


# ═══════════════════════════════════════════════
# 6b2. Pydantic Schema + 自动修复（Phase 3）
# ═══════════════════════════════════════════════

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional as _PydanticOptional, Union, Annotated
from pydantic import Discriminator

_VALID_DISPLAYS = Literal["inline", "block", "hidden"]
_VALID_OPERATIONS = Literal[
    "classify", "recall", "substitute", "simplify", "expand", "factor",
    "differentiate", "integrate", "solve", "evaluate", "apply_theorem",
    "transform", "conclude", "check", "",
]

# LLM常见的operation拼写错误 → 自动映射
_OPERATION_ALIASES = {
    "applytheorem": "apply_theorem",
    "finalanswer": "",
    "differentation": "differentiate",
    "intergrate": "integrate",
    "eval": "evaluate",
    "simpify": "simplify",
    "substitution": "substitute",
    "diff": "differentiate",
    "int": "integrate",
    "expand_series": "expand",
}


class LatexBlock(BaseModel):
    """Pure LaTeX block. Content is a standalone renderable expression.

    RULES (violations are auto-fixed or rejected):
      - NO Chinese characters (these go in TextBlock)
      - NO $ delimiters (st.latex() is already in math mode)
      - NO markdown syntax (*, _, #, -, bullets)
      - NO natural language explanation words
      - NO emoji
    """
    type: Literal["latex"] = "latex"
    content: str = Field(..., min_length=1)
    display: _VALID_DISPLAYS = "inline"

    @field_validator("content", mode="after")
    @classmethod
    def enforce_purity(cls, v: str) -> str:
        import re, logging
        log = logging.getLogger("latex_utils")
        v = v.strip()

        # 1. Strip $ delimiters (fatal if nested)
        if '$' in v:
            log.warning("LatexBlock: stripped $ delimiters. Content: %s", v[:80])
            v = v.replace('$$', '').replace('$', '').strip()

        # 2. Fix double-escaped LaTeX: \\frac → \frac
        v = re.sub(r'\\\\([a-zA-Z]+)', r'\\\1', v)

        # 3. Strip markdown syntax
        if re.search(r'^\s*[-*#]\s|\*\*|__|\b(bullet|emoji)\b', v):
            log.warning("LatexBlock: stripped markdown syntax. Content: %s", v[:80])
            v = re.sub(r'^\s*[-*#]\s+', '', v)
            v = v.replace('**', '').replace('__', '')

        # 4. Remove emoji (safe range: only emoji blocks, NOT overlapping CJK)
        v = re.sub(r'[\U0001F300-\U0001F9FF☀-➿⭐]', '', v)

        # 5. Hard reject: Chinese OUTSIDE \\text{{}} → error
        # (Chinese inside \\text{{}} is valid LaTeX, e.g. \\text{{线性无关}})
        if _has_chinese(v):
            raise ValueError(
                f"LatexBlock contains Chinese characters (outside \\text{{}}). "
                f"Move natural language to a TextBlock. Content: {v[:80]}"
            )

        # 6. Hard reject: natural language OUTSIDE \\text{{}}
        v_notext = re.sub(r'\\text\{[^}]*\}', '', v)
        if re.search(r'(?:设|令|则|因此|所以|代入|得到|解得|求|计算|展开|合并|化简|整理|移项|配方|构造|假设|定义|记|取|作|由|根据|利用|应用|考虑|注意|显然|易知)', v_notext):
            raise ValueError(
                f"LatexBlock contains natural language. "
                f"Move explanation to a TextBlock. Content: {v[:80]}"
            )

        return v.strip()

    model_config = {"extra": "ignore"}


class TextBlock(BaseModel):
    """Pure text block. Content is natural language. ZERO LaTeX commands allowed.

    RULES: \\frac, \\int, \\sum, etc. are FORBIDDEN in text blocks.
    These must go in separate LatexBlocks.
    """
    type: Literal["text"] = "text"
    content: str = Field(..., min_length=1)

    @field_validator("content", mode="after")
    @classmethod
    def reject_latex_commands(cls, v: str) -> str:
        import re
        # Any LaTeX command (backslash + letters) in text block → reject
        if re.search(r'\\[a-zA-Z]+', v):
            raise ValueError(
                f"TextBlock contains LaTeX commands. "
                f"Move math expressions to a LatexBlock. Content: {v[:80]}"
            )
        # $ delimiters in text → reject
        if '$' in v:
            raise ValueError(
                f"TextBlock contains $ delimiters. "
                f"Math must be in a separate LatexBlock. Content: {v[:80]}"
            )
        return v

    model_config = {"extra": "ignore"}


# Discriminated union: LLM must choose exactly one block type
SolutionBlock = Annotated[
    Union[LatexBlock, TextBlock],
    Discriminator("type"),
]


class MathStepPydantic(BaseModel):
    """One solution step containing separated text and latex blocks."""
    label: str = ""
    blocks: list[SolutionBlock] = Field(..., min_length=1)
    operation: str = ""

    @field_validator("label", mode="after")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return "步骤"
        return v

    model_config = {"extra": "ignore"}


class FinalAnswerPydantic(BaseModel):
    """Final answer block — usually a single LaTeX expression."""
    type: Literal["latex", "text"] = "latex"
    content: str = Field(..., min_length=1)

    model_config = {"extra": "ignore"}


class SolutionMetadataPydantic(BaseModel):
    """Optional metadata."""
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: str = "中等"
    total_score: float = 10.0
    common_mistakes: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class StructuredSolutionPydantic(BaseModel):
    """THE only format LLM should output. Validated at system boundary."""
    steps: list[MathStepPydantic] = Field(..., min_length=1)
    final_answer: _PydanticOptional[FinalAnswerPydantic] = None
    metadata: SolutionMetadataPydantic = Field(default_factory=SolutionMetadataPydantic)

    model_config = {"extra": "ignore"}

    @classmethod
    def from_llm_output(cls, data: dict) -> "StructuredSolutionPydantic":
        """THE single entry point. Validates + repairs LLM output. Raises on unrepairable input."""
        model, errors, _ = validate_and_repair(data)
        if errors:
            raise ValueError(f"StructuredSolution validation failed: {'; '.join(errors[:5])}")
        _assert_no_double_escape(model)
        return model

    @classmethod
    def model_validate_strict(cls, data: dict) -> "StructuredSolutionPydantic":
        """Like from_llm_output but without auto-repair — strict validation only."""
        return cls(**data)


def _assert_no_double_escape(model: StructuredSolutionPydantic) -> None:
    """Catch double-escaped LaTeX early. \\\\frac in content means escape was applied twice."""
    import re
    _double_escape_re = re.compile(r'\\\\[a-zA-Z]+')
    for i, step in enumerate(model.steps):
        for j, block in enumerate(step.blocks):
            content = block.content if hasattr(block, 'content') else ''
            if _double_escape_re.search(content):
                import logging
                logging.getLogger(__name__).warning(
                    "Double-escaped LaTeX detected in steps[%d].blocks[%d]: %s",
                    i, j, content[:80]
                )


def _has_chinese(s: str) -> bool:
    """Check if string contains Chinese characters OUTSIDE of \\text{{}} commands.

    Chinese inside \\text{{...}} is valid LaTeX and should not be flagged.
    """
    import re
    if not re.search(r'[一-鿿]', s):
        return False
    # Remove \\text{{...}} protected regions before checking
    protected = re.sub(r'\\text\{[^}]*\}', '', s)
    return bool(re.search(r'[一-鿿]', protected))


def _split_mixed_latex_block(content: str, display: str = "inline") -> list[dict]:
    """Split a latex block that illegally contains Chinese text.

    Uses split_latex_text to separate natural language from LaTeX,
    then converts segments to proper text/latex blocks.
    """
    try:
        segments = split_latex_text(content)
    except Exception:
        # Can't split → convert entire block to text
        return [{"type": "text", "content": content}]

    result = []
    for seg in segments:
        t = seg.get("type", "text")
        c = seg.get("content", "").strip()
        if not c:
            continue
        if t in ("inline_math", "display_math"):
            result.append({"type": "latex", "content": c, "display": display})
        else:
            result.append({"type": "text", "content": c})
    return result if result else [{"type": "text", "content": content}]


def _restore_bare_latex_commands(content: str) -> str:
    """Restore backslash to bare LaTeX commands that lost it (JSON escape corruption)."""
    import re as _re

    boundary_cmds = [
        'int', 'iint', 'oint', 'lim', 'ln', 'sin', 'cos', 'tan',
        'cot', 'sec', 'csc', 'log', 'exp', 'sum', 'prod',
    ]
    safe_cmds = [
        'begin', 'end', 'Rightarrow', 'Leftarrow', 'rightarrow', 'leftarrow',
        'cdot', 'times', 'neq', 'leq', 'geq', 'operatorname',
        'frac', 'dfrac', 'sqrt', 'partial', 'nabla', 'infty',
        'alpha', 'beta', 'gamma', 'delta', 'sigma', 'phi', 'omega',
        'lambda', 'theta', 'pi', 'left', 'right', 'mathrm',
    ]

    for cmd in boundary_cmds:
        content = _re.sub(rf'(?<!\\)\b{_re.escape(cmd)}\b', lambda m, _cmd=cmd: f'\\{_cmd}', content)

    for cmd in safe_cmds:
        if cmd in content and f'\\{cmd}' not in content:
            content = content.replace(cmd, f'\\{cmd}')

    return content


def validate_and_repair(data: dict) -> tuple[StructuredSolutionPydantic | None, list[str], list[str]]:
    """Validate + auto-repair LLM JSON output against Pydantic schema.

    Returns:
        (model, errors, repair_log)
        - model: validated Pydantic model, or None if unrepairable
        - errors: remaining validation errors (empty = success)
        - repair_log: what was fixed
    """
    repairs = []

    if not isinstance(data, dict):
        return None, ["input must be a dict"], []

    # ── Repair 1: drop root-level extra fields ──
    allowed_root = {"steps", "final_answer", "metadata"}
    extra_root = [k for k in data if k not in allowed_root]
    if extra_root:
        repairs.append(f"dropped extra root fields: {extra_root}")
        data = {k: v for k, v in data.items() if k in allowed_root}

    # ── Repair 2: ensure steps is a list ──
    if "steps" not in data:
        return None, ["missing required field: steps"], repairs
    if not isinstance(data["steps"], list):
        return None, [f"steps must be a list, got {type(data['steps']).__name__}"], repairs

    # ── Repair 3: fix each step ──
    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            repairs.append(f"steps[{i}]: replaced non-dict with empty step")
            data["steps"][i] = {"label": f"步骤{i+1}", "blocks": [{"type": "text", "content": "(empty)"}]}
            continue

        # drop extra fields
        allowed_step = {"label", "blocks", "operation"}
        extra_step = [k for k in step if k not in allowed_step]
        if extra_step:
            repairs.append(f"steps[{i}]: dropped extra fields: {extra_step}")
            for k in extra_step:
                step.pop(k, None)

        # auto-fix common LLM operation typos
        op = step.get("operation", "")
        _valid_op_set = {"classify", "recall", "substitute", "simplify", "expand", "factor",
                         "differentiate", "integrate", "solve", "evaluate", "apply_theorem",
                         "transform", "conclude", "check", ""}
        if op and op not in _valid_op_set:
            alias = _OPERATION_ALIASES.get(op)
            if alias is not None:
                step["operation"] = alias
                repairs.append(f"steps[{i}]: operation '{op}' -> '{alias}'")
            else:
                step["operation"] = "simplify"
                repairs.append(f"steps[{i}]: operation '{op}' -> 'simplify'")

        # auto-fill label
        if not step.get("label"):
            step["label"] = f"步骤{i+1}"
            repairs.append(f"steps[{i}]: auto-filled label")

        # ensure blocks is a list
        if "blocks" not in step:
            repairs.append(f"steps[{i}]: added empty blocks")
            step["blocks"] = [{"type": "text", "content": "(missing)"}]
        elif not isinstance(step["blocks"], list):
            repairs.append(f"steps[{i}]: blocks replaced (was {type(step['blocks']).__name__})")
            step["blocks"] = [{"type": "text", "content": str(step["blocks"])}]

        # ── Repair 4: fix each block ──
        for j, block in enumerate(step["blocks"]):
            if not isinstance(block, dict):
                repairs.append(f"steps[{i}].blocks[{j}]: replaced non-dict")
                step["blocks"][j] = {"type": "text", "content": str(block)}
                continue

            # auto-fix type: anything not "latex" or "text" becomes "text"
            bt = block.get("type", "")
            if bt not in ("text", "latex"):
                old = bt or "missing"
                block["type"] = "text"
                repairs.append(f"steps[{i}].blocks[{j}]: type '{old}' -> 'text'")

            # ── Hard rule: latex block must NOT contain natural language ──
            if block.get("type") == "latex":
                content = block.get("content", "")
                import re as _re2
                has_chinese = _has_chinese(content)
                # Check natural language OUTSIDE \text{} (same protection as _has_chinese)
                content_no_text = _re2.sub(r'\\text\{[^}]*\}', '', content)
                has_natural = bool(_re2.search(
                    r'(?:设|令|则|因此|所以|代入|得到|解得|求|计算|展开|合并|化简'
                    r'|整理|移项|配方|构造|假设|定义|记|取|作|由|根据|利用|应用'
                    r'|考虑|注意|显然|易知|解得|其中|于是|从而|进而|即)',
                    content_no_text
                ))
                if has_chinese or has_natural:
                    new_blocks = _split_mixed_latex_block(content, block.get("display", "inline"))
                    step["blocks"][j:j+1] = new_blocks
                    reason = "Chinese" if has_chinese else "natural language"
                    repairs.append(
                        f"steps[{i}].blocks[{j}]: latex block had {reason}, "
                        f"split into {len(new_blocks)} blocks"
                    )
                    continue

            # latex block: strip $ delimiters, fix display, restore lost backslashes
            if block.get("type") == "latex":
                if block.get("display") not in ("inline", "block", "hidden"):
                    block["display"] = "inline"
                content = block.get("content", "")
                if content.strip():
                    content = content.strip()
                    # Fix lost backslashes: bare LaTeX commands (from JSON escape corruption)
                    # e.g., "begin{pmatrix}" → "\\begin{pmatrix}"
                    # "end{pmatrix}" → "\\end{pmatrix}"
                    # "frac12" → "\\frac{1}{2}" (harder, just flag)
                    for bare_cmd in ['begin', 'end', 'Rightarrow', 'Leftarrow', 'rightarrow',
                                     'leftarrow', 'cdot', 'times', 'neq', 'leq', 'geq']:
                        if bare_cmd in content and f'\\{bare_cmd}' not in content:
                            content = content.replace(bare_cmd, f'\\{bare_cmd}')
                            repairs.append(
                                f"steps[{i}].blocks[{j}]: restored \\\\{bare_cmd} (backslash was lost)"
                            )
                    # Hard rule: strip ALL $ from latex blocks (st.latex() is already in math mode)
                    if '$' in content:
                        repairs.append(
                            f"steps[{i}].blocks[{j}]: stripped $ delimiters from latex block "
                            f"(LLM must NOT output $ in latex content)"
                        )
                        content = content.replace('$$', '').replace('$', '').strip()
                    block["content"] = content
                # drop non-latex fields
                for k in list(block.keys()):
                    if k not in ("type", "content", "display"):
                        block.pop(k, None)

            # text block: drop display (not a text field)
            if block.get("type") == "text":
                block.pop("display", None)
                block.pop("operation", None)

            # auto-fix missing content
            if not block.get("content", "").strip():
                block["content"] = "(empty)"
                repairs.append(f"steps[{i}].blocks[{j}]: filled empty content")

    # ── Repair 5: fix final_answer ──
    fa = data.get("final_answer")
    if fa is not None and isinstance(fa, dict):
        if fa.get("type") not in ("text", "latex"):
            fa["type"] = "latex"
            repairs.append("final_answer: fixed type -> latex")
        if not fa.get("content", "").strip():
            repairs.append("final_answer: removed (empty content)")
            data.pop("final_answer", None)
        # drop extra fields
        allowed_fa = {"type", "content"}
        extra_fa = [k for k in fa if k not in allowed_fa]
        if extra_fa:
            repairs.append(f"final_answer: dropped extra: {extra_fa}")
            for k in extra_fa:
                fa.pop(k, None)

    # ── Repair 6: fix metadata ──
    meta = data.get("metadata")
    if meta is not None and isinstance(meta, dict):
        allowed_meta = {"knowledge_points", "difficulty", "total_score", "common_mistakes"}
        extra_meta = [k for k in meta if k not in allowed_meta]
        if extra_meta:
            repairs.append(f"metadata: dropped extra: {extra_meta}")
            for k in extra_meta:
                meta.pop(k, None)
        # coerce types
        diff_val = meta.get("difficulty")
        if diff_val is not None and not isinstance(diff_val, str):
            meta["difficulty"] = str(diff_val)
            repairs.append("metadata: coerced difficulty to str")
        if "total_score" in meta:
            try:
                meta["total_score"] = float(meta["total_score"])
            except (ValueError, TypeError):
                meta["total_score"] = 10.0
                repairs.append("metadata: total_score invalid, defaulted to 10")
        if "knowledge_points" in meta and not isinstance(meta["knowledge_points"], list):
            if isinstance(meta["knowledge_points"], str):
                meta["knowledge_points"] = [meta["knowledge_points"]]
            else:
                meta["knowledge_points"] = []
            repairs.append("metadata: fixed knowledge_points type")
        if "common_mistakes" in meta and not isinstance(meta["common_mistakes"], list):
            if isinstance(meta["common_mistakes"], str):
                meta["common_mistakes"] = [meta["common_mistakes"]]
            else:
                meta["common_mistakes"] = []
            repairs.append("metadata: fixed common_mistakes type")

    # ── Final validation ──
    try:
        model = StructuredSolutionPydantic(**data)
        return model, [], repairs
    except Exception as e:
        return None, [str(e)], repairs


# ═══════════════════════════════════════════════
# 6d. 旧格式转换 — 从混合 text 到结构化方案
# ═══════════════════════════════════════════════

# Metadata section headings that should be stripped from step content
_META_HEADINGS = (
    r'关键知识点|易错提示|常见误区|秒杀技巧|'
    r'结论|标准答案|题目重述|最终答案|'
    r'题型补充|知识点总结|注意事项|解题技巧'
)

def from_legacy_text(text: str, title: str = "解答") -> dict:
    """
    将旧的混合文本格式转换为 StructuredSolution。

    流程:
      1. 在原始文本中检测步骤边界（"步骤N" / "第N步" 等）
      2. 按边界拆分为多个 chunk
      3. 每个 chunk: clean_markdown → split_latex_text → 构建 blocks
      4. 组装 StructuredSolution
    """
    if not text:
        return make_solution(steps=[make_step("", [make_text("(无内容)")])])

    # Match step markers with full Chinese number support.
    # Pattern groups:
    #   1. "步骤N：" / "第N步：" (Arabic or Chinese digits)
    #   2. "### 步骤N：" (Markdown heading)
    #   3. "N. " / "N、" at line start (but ONLY when N≤20 to avoid false
    #      matches with LaTeX equation numbers or year references)
    _CN_NUM = r'[一二三四五六七八九十]{1,3}'
    _STEP_RE = re.compile(
        r'(?:步骤|第)\s*(\d+|' + _CN_NUM + r')\s*(?:步|题|问)?\s*[：:]\s*|'
        r'(?:###\s*)?步骤\s*(\d+|' + _CN_NUM + r')\s*[：:]\s*|'
        r'(?:^|\n)\s*(\d{1,2})\s*[.、．)]\s+(?=[一-鿿])',
        re.MULTILINE,
    )
    # Map Chinese number strings to ints
    _CN_MAP = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
               '十一': 11, '十二': 12}

    # Step 1: 检测步骤边界
    step_boundaries = []  # [(step_num, start_pos, end_pos)]
    for m in _STEP_RE.finditer(text):
        num_str = m.group(1) or m.group(2) or m.group(3)
        if num_str:
            if num_str.isdigit():
                step_num = int(num_str)
            else:
                step_num = _CN_MAP.get(num_str, 0)
            if step_num > 0:
                step_boundaries.append((step_num, m.start(), m.end()))

    if not step_boundaries:
        # 没有步骤标记 — 尝试用加粗标题（**xxx**：）作为fallback步骤边界
        _BOLD_STEP_RE = re.compile(r'\*\*(.+?)\*\*\s*[：:]\s*')
        bold_markers = list(_BOLD_STEP_RE.finditer(text))
        if len(bold_markers) >= 2:
            # Use bold headers as pseudo-step boundaries
            fallback_steps = []
            for i, bm in enumerate(bold_markers):
                label = bm.group(1).strip()
                b_start = bm.end()
                b_end = bold_markers[i+1].start() if i+1 < len(bold_markers) else len(text)
                chunk = text[b_start:b_end].strip()
                # Apply same processing as regular steps
                chunk = re.sub(r'\\\(\s*(.+?)\s*\\\)', r'$\1$', chunk, flags=re.DOTALL)
                chunk = re.sub(r'\\\[\s*(.+?)\s*\\\]', r'$$\1$$', chunk, flags=re.DOTALL)
                chunk = _pre_wrap_bare_latex(chunk)
                chunk = re.sub(
                    r'(?:^|\n+)#{1,3}\s*(?:' + _META_HEADINGS + r')\s*\n.*$',
                    '', chunk, flags=re.DOTALL,
                )
                cleaned = clean_markdown(chunk)
                segments = split_latex_text(cleaned)
                blocks = _segments_to_blocks(segments)
                if blocks:
                    fallback_steps.append(make_step(label, blocks))
            if len(fallback_steps) >= 2:
                return make_solution(steps=fallback_steps)

        # Still no steps — treat entire text as one step, but strip metadata
        cleaned_text = text
        cleaned_text = re.sub(
            r'(?:^|\n+)#{1,3}\s*(?:' + _META_HEADINGS + r')\s*\n.*$',
            '', cleaned_text, flags=re.DOTALL,
        )
        cleaned = clean_markdown(cleaned_text)
        segments = split_latex_text(cleaned)
        blocks = _segments_to_blocks(segments)
        return make_solution(steps=[make_step("", blocks)])

    # Step 2: 按边界拆分
    steps = []
    seen_step_nums = set()  # 记录已处理的步骤号，避免重复
    
    for i, (step_num, start, end) in enumerate(step_boundaries):
        # 跳过重复的步骤号
        if step_num in seen_step_nums:
            continue
        seen_step_nums.add(step_num)
        
        # 本步骤内容：从标记结束到下一个标记开始
        next_start = step_boundaries[i + 1][1] if i + 1 < len(step_boundaries) else len(text)
        chunk = text[end:next_start].strip()

        # Convert LaTeX delimiters BEFORE clean_markdown (which protects $...$
        # but doesn't recognize \(...\) as math, causing subscript corruption).
        chunk = re.sub(r'\\\(\s*(.+?)\s*\\\)', r'$\1$', chunk, flags=re.DOTALL)
        chunk = re.sub(r'\\\[\s*(.+?)\s*\\\]', r'$$\1$$', chunk, flags=re.DOTALL)

        # Wrap bare LaTeX commands (like \frac, \sqrt) in $...$ so
        # clean_markdown protects them as math regions and doesn't split
        # fractions across lines.
        chunk = _pre_wrap_bare_latex(chunk)

        # Strip trailing metadata sections.
        chunk = re.sub(
            r'(?:^|\n+)#{1,3}\s*(?:' + _META_HEADINGS + r')\s*\n.*$',
            '', chunk, flags=re.DOTALL,
        )

        # Step 3: 清理 + 分离 + 构建 blocks
        cleaned = clean_markdown(chunk)
        segments = split_latex_text(cleaned)
        blocks = _segments_to_blocks(segments)

        steps.append(make_step(f"步骤{step_num}", blocks))

    return make_solution(steps=steps)


def _segments_to_blocks(segments: list[dict]) -> list[dict]:
    """将 split_latex_text 的 segments 转换为 MathBlock dict 列表。"""
    blocks = []
    for seg in segments:
        t = seg["type"]
        c = seg["content"]
        if t == "text":
            blocks.append(make_text(c))
        elif t == "inline_math":
            blocks.append(make_latex(sanitize_latex_for_render(c), display="inline"))
        elif t == "display_math":
            blocks.append(make_latex(sanitize_latex_for_render(c), display="block"))
    return blocks


def from_legacy_json(json_str: str) -> dict:
    """
    从 JSON 字符串解析 StructuredSolution。

    如果解析失败，回退到 from_legacy_text 处理。
    """
    try:
        data = _json.loads(json_str)
        is_valid, _ = validate_structured(data)
        if is_valid:
            return data
    except Exception:
        pass
    # 回退：当作文本处理
    return from_legacy_text(json_str)


# ═══════════════════════════════════════════════
# 6e. LLM 结构化输出 Prompt 模板
# ═══════════════════════════════════════════════

STRUCTURED_OUTPUT_PROMPT = r"""
# 输出格式（必须严格遵守）

你必须只输出一个 JSON 对象，不要输出任何 markdown 或额外文本。

## JSON Schema

```json
{
  "steps": [
    {
      "label": "步骤1",
      "blocks": [
        {"type": "text", "content": "识别题型：这是一道极限计算题"},
        {"type": "latex", "content": "\\lim_{x\\to 0} \\frac{\\sin x}{x}", "display": "block"},
        {"type": "text", "content": "这是 0/0 型未定式"}
      ],
      "operation": "classify"
    },
    {
      "label": "步骤2",
      "blocks": [
        {"type": "text", "content": "应用洛必达法则，分子分母分别求导"},
        {"type": "latex", "content": "\\lim_{x\\to 0} \\frac{\\sin x}{x} = \\lim_{x\\to 0} \\frac{\\cos x}{1} = 1", "display": "block"}
      ],
      "operation": "apply_theorem"
    }
  ],
  "final_answer": {
    "type": "latex",
    "content": "1"
  },
  "metadata": {
    "knowledge_points": ["极限", "洛必达法则"],
    "difficulty": "中等"
  }
}
```

## 字段说明

- **steps**: 解题步骤数组（必填）
  - **label**: 步骤标签，如 "步骤1"（必填）
  - **operation**: 操作类型（可选），必须是以下之一：
    classify, recall, substitute, simplify, expand, factor,
    differentiate, integrate, solve, evaluate, apply_theorem,
    transform, conclude, check
  - **blocks**: 内容块数组（必填）
    - **type**: "text" 或 "latex"（必填）
    - **content**: 纯文本或 LaTeX 表达式（必填）
    - **display**: "inline" 或 "block"（可选，默认 inline）

- **final_answer**: 最终答案（可选）
- **metadata**: 元信息（可选）
  - **knowledge_points**: 知识点列表
  - **difficulty**: 难度等级

## 核心规则

1. **文本和公式绝对分离**：text block 中不允许有任何 LaTeX 命令，latex block 中不允许有中文或英文解释
2. **LaTeX 必须完整**：每个 latex block 是独立的、可独立渲染的完整表达式
3. **不需要 $ 分隔符**：latex content 中不要加 $...$，系统会自动添加
4. **display=block 用于重要公式**：关键推导步骤使用 block 显示，简短公式用 inline
5. **每个步骤一个 operation**：标注本步骤的核心数学操作
"""


# ═══════════════════════════════════════════════════════════════
# 7. 四层解耦架构 — 最终结构
# ═══════════════════════════════════════════════════════════════
#
#   Layer 1: 推理层 → CanonicalTrace
#     - 数学语义、解题逻辑、知识点
#     - 输入: LLM JSON 或 SolutionGraph DAG
#     - 输出: StructuredSolution (统一中间格式)
#
#   Layer 2: 渲染层 → Renderer
#     - 控制全部显示决策
#     - 决定: 布局、颜色、徽章、步骤顺序、display/block
#     - 不做: token 修复、Streamlit 调用
#
#   Layer 3: 安全层 → sanitize_latex
#     - Token 级安全处理
#     - 修复: 失衡括号、破损分隔符、HTML 不安全字符
#     - 纯函数，相同输入永远相同输出
#
#   Layer 4: UI层 → st.latex / st.markdown
#     - Streamlit 原生渲染
#     - 不做任何逻辑处理
#
#   数据流（单向，上层不依赖下层实现）:
#     CanonicalTrace → Renderer → sanitize_latex → st.latex
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════
# 7a. 推理层 — CanonicalTrace
# ═══════════════════════════════════════════════

# CanonicalTrace 是推理层的输出契约。
# 可以是:
#   1. StructuredSolution dict (LLM 直接输出)
#   2. CanonicalSolutionTrace 对象 (solution_graph.py 的 DAG)
#   3. SolutionGraph 对象 (单个解法的 DAG)
#
# 统一入口: as_canonical() 将任意格式归一化为 StructuredSolution dict。

# GraphNode type → MathOperation 映射
_GRAPH_NODE_TO_OP = {
    "differentiate":     "differentiate",
    "integrate":         "integrate",
    "iintegrate":        "integrate",
    "simplify":          "simplify",
    "expand":            "expand",
    "factor":            "factor",
    "solve_equation":    "solve",
    "solve_inequality":  "solve",
    "substitute":        "substitute",
    "evaluate":          "evaluate",
    "apply_theorem":     "apply_theorem",
    "conclude":          "conclude",
    "check":             "check",
    "transform":         "transform",
    "classify":          "classify",
    "recall":            "recall",
    "limit_calc":        "evaluate",
    "derivative_calc":   "differentiate",
    "integral_calc":     "integrate",
    "series_expand":     "expand",
    "taylor_expand":     "expand",
    "probability_calc":  "evaluate",
    "eigen_solve":       "solve",
    "orthogonalize":     "transform",
}


def graph_to_structured(source) -> dict:
    """
    将 SolutionGraph 或 CanonicalSolutionTrace 转换为 StructuredSolution。

    这是 DAG 推理路径和 LLM 渲染路径之间的桥梁。
    输入可以是:
      - CanonicalSolutionTrace (solution_graph.py)
      - SolutionGraph (solution_graph.py)
      - SolutionMethod (solution_graph.py)

    返回 StructuredSolution dict，可直接传入 render_structured()。
    """
    # 尝试导入 solution_graph 类型
    try:
        from solution_graph import (
            CanonicalSolutionTrace, SolutionGraph, SolutionMethod, GraphNode,
        )
    except ImportError:
        return make_solution(steps=[make_step("", [make_text("(无法导入 solution_graph)")])])

    # 归一化: 提取 SolutionGraph
    graph = None
    method_name = ""
    if isinstance(source, CanonicalSolutionTrace):
        best = source.best_method()
        if best:
            graph = best.graph
            method_name = best.method_name
    elif isinstance(source, SolutionMethod):
        graph = source.graph
        method_name = source.method_name
    elif isinstance(source, SolutionGraph):
        graph = source
    else:
        return make_solution(steps=[make_step("", [make_text("(不支持的输入类型)")])])

    if graph is None or not graph.nodes:
        return make_solution(steps=[make_step("", [make_text("(空图)")])])

    # 构建步骤: 每个 GraphNode → 一个 MathStep
    steps = []
    for i, node in enumerate(graph.nodes):
        blocks = []

        # 节点标签作为 text block
        if node.label:
            blocks.append(make_text(node.label))

        # 节点输出作为 latex block (display=block)
        if node.output:
            blocks.append(make_latex(node.output, display="block"))

        # 映射操作类型
        op = _GRAPH_NODE_TO_OP.get(node.type, "")

        label = f"步骤{i+1}"
        steps.append(make_step(label, blocks, operation=op))

    # 最终答案
    final_answer = None
    if graph.final_answer:
        final_answer = make_latex(graph.final_answer)

    sol = make_solution(steps=steps, final_answer=final_answer)
    if method_name:
        sol.setdefault("metadata", {})["method_name"] = method_name

    return sol


def as_canonical(source) -> dict:
    """
    将任意来源归一化为 CanonicalTrace (StructuredSolution dict)。

    支持的输入:
      - dict: 已是 StructuredSolution → 验证后直接返回
      - str:  旧文本 → from_legacy_text 转换
      - CanonicalSolutionTrace / SolutionGraph / SolutionMethod → graph_to_structured
    """
    if isinstance(source, dict):
        is_valid, _ = validate_structured(source)
        if is_valid:
            return source
        # 不是合法的 structured solution，当作文本处理
        return from_legacy_text(str(source))

    if isinstance(source, str):
        return from_legacy_text(source)

    # 尝试 DAG 类型
    return graph_to_structured(source)


# ═══════════════════════════════════════════════
# 7b. 渲染层 + 安全层 + UI层 — 四层管道
# ═══════════════════════════════════════════════

_DISPLAY_ENV_NAMES = (
    "cases", "aligned", "matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix",
    "array", "split", "gathered",
)
_DISPLAY_ENV_RE = re.compile(
    r"\\begin\{(" + "|".join(re.escape(n) for n in _DISPLAY_ENV_NAMES) + r")\}"
)


def _normalize_fragmented_display_latex(content: str) -> str:
    """Repair common LLM splits inside display environments before KaTeX."""
    s = str(content or "").strip()
    if not s:
        return ""

    if not _DISPLAY_ENV_RE.search(s):
        s = _normalize_tex_spacing_before_binding(s)
    s = re.sub(r'\\(qquad|quad)(?=[A-Za-z])', r'\\\1 ', s)
    s = re.sub(r'\\in\s+R\b', r'\\in \\mathbb{R}', s)
    s = re.sub(r'(?<!\\)\\(?![A-Za-z{}\[\]\\,;:!])', r'\\\\', s)
    s = re.sub(r'\\\\\s*,', r'\\\\', s)
    return s.strip()


def _split_display_environment_tail(content: str, env: str) -> tuple[str, str]:
    r"""Split content at the first matching \end{env}, preserving tail text."""
    s = str(content or "")
    marker = rf"\end{{{env}}}"
    idx = s.find(marker)
    if idx < 0:
        return s, ""
    end = idx + len(marker)
    return s[:end], s[end:].strip()


def _looks_like_standalone_ascii_math_text(content: str) -> bool:
    """Detect text blocks like D_n=2a or x_2 that should be inline math."""
    s = str(content or "").strip()
    if not s or len(s) > 120:
        return False
    if any('\u4e00' <= ch <= '\u9fff' for ch in s):
        return False
    if re.search(r'[A-Za-z]{4,}', s) and not re.search(r'\\[A-Za-z]+', s):
        return False
    if re.fullmatch(r'[\s.,;:，。、；：()（）]+', s):
        return False
    return bool(re.search(r'(\\[A-Za-z]+|[A-Za-z]_\w|[A-Za-z]\d|[=^_]|\\in\b)', s))


def _normalize_standalone_ascii_math_text(content: str) -> str:
    """Small display-only cleanup for ASCII math emitted as text."""
    s = str(content or "").strip()
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r'\b([A-Za-z])(\d+)\b', r'\1_\2', s)
    s = re.sub(r'\\in\s+R\b', r'\\in \\mathbb{R}', s)
    return s


def _unwrap_outer_latex_command(content: str, command: str) -> str:
    """Remove one outer LaTeX command wrapper when it encloses all content."""
    s = str(content or "").strip()
    prefix = f"\\{command}{{"
    if not s.startswith(prefix) or not s.endswith("}"):
        return s

    depth = 0
    start = len(prefix) - 1
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{" and (i == 0 or s[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or s[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                if i == len(s) - 1:
                    return s[len(prefix):-1].strip()
                return s
    return s


def _normalize_final_answer_content(content: str) -> str:
    """Normalize final_answer content before choosing a render path."""
    s = str(content or "").strip()
    for command in ("boxed", "fbox"):
        unwrapped = _unwrap_outer_latex_command(s, command)
        if unwrapped != s:
            s = unwrapped
            break
    return s.strip()


def _final_answer_needs_mixed_renderer(content: str) -> bool:
    """True when final_answer is prose plus math, not a single formula."""
    s = str(content or "")
    if not s.strip():
        return False
    if any('\u4e00' <= ch <= '\u9fff' for ch in s):
        return True
    if any(token in s for token in ("\\[", "\\]", "$$", "\\(", "\\)")):
        return True
    return False


def _render_final_answer_safe(final_answer: dict) -> None:
    """Render structured final_answer without exposing raw red LaTeX."""
    content = _normalize_final_answer_content(final_answer.get("content", ""))
    if not content:
        return

    fa_type = final_answer.get("type", "text")
    if fa_type == "latex" and not _final_answer_needs_mixed_renderer(content):
        _render_blocks_safe([{**final_answer, "content": content}], highlight=True)
        return

    try:
        from renderers.math_render_policy import render_grading_latex
        render_grading_latex(content)
    except Exception:
        render_ast(split_latex_text(content))


def _repair_solution_blocks_for_render(blocks: list[dict]) -> list[dict]:
    """Make generated solution blocks renderable without changing meaning."""
    repaired: list[dict] = []
    source = [b for b in (blocks or []) if isinstance(b, dict)]
    i = 0

    while i < len(source):
        block = source[i]
        content = str(block.get("content") or "")
        display = block.get("display", "inline")
        env_match = _DISPLAY_ENV_RE.search(content)

        if env_match:
            env = env_match.group(1)
            env_end = rf"\end{{{env}}}"
            prefix = content[:env_match.start()].strip()
            if block.get("type") == "latex" and prefix and env_end in content:
                fixed = _normalize_fragmented_display_latex(content)
                next_block = dict(block)
                next_block["content"] = fixed
                next_block["display"] = "block"
                repaired.append(next_block)
                i += 1
                continue

            collected = content
            i += 1
            while env_end not in collected and i < len(source):
                next_content = str(source[i].get("content") or "")
                collected = (collected.rstrip() + "\n" + next_content.lstrip()).strip()
                i += 1

            latex_part, tail = _split_display_environment_tail(collected, env)
            latex_part = _normalize_fragmented_display_latex(latex_part)
            if latex_part and env_end in latex_part:
                repaired.append({
                    "type": "latex",
                    "display": "block",
                    "content": latex_part,
                })
                if tail:
                    repaired.extend(_segments_to_blocks(split_latex_text(tail)))
                continue

            repaired.append({"type": "text", "content": collected})
            continue

        if block.get("type") == "latex":
            fixed = _normalize_fragmented_display_latex(content)
            next_block = dict(block)
            next_block["content"] = fixed
            if _DISPLAY_ENV_RE.search(fixed):
                next_block["display"] = "block"
            repaired.append(next_block)
        elif _looks_like_standalone_ascii_math_text(content):
            repaired.append({
                "type": "latex",
                "display": display if display in ("inline", "block") else "inline",
                "content": _normalize_standalone_ascii_math_text(content),
            })
        else:
            repaired.append(block)
        i += 1

    return repaired


def _render_blocks_safe(blocks: list[dict], highlight: bool = False) -> None:
    """Render MathBlock list — merge consecutive text + inline latex into one paragraph.

    Each separate st.markdown() creates a block-level element in Streamlit.
    LLM/legacy pipelines often emit one block per word or formula; without merging,
    sentences break across many lines (the grading-page line-break bug).
    """
    import streamlit as st

    blocks = _repair_solution_blocks_for_render(blocks or [])

    buf: list[str] = []
    last_was_inline = False

    def _flush() -> None:
        nonlocal last_was_inline
        if not buf:
            return
        md = "".join(buf).strip()
        if not md:
            buf.clear()
            last_was_inline = False
            return
        try:
            if highlight and "$" not in md:
                st.markdown(f"**{md}**")
            else:
                st.markdown(md)
        except Exception:
            # st.markdown can fail on complex LaTeX; fall back through
            # safe_render → plain text, never truncating user-visible content.
            try:
                from renderers.math_render_policy import render_grading_latex
                render_grading_latex(md)
            except Exception:
                try:
                    st.text(md)
                except Exception:
                    pass
        buf.clear()
        last_was_inline = False

    for block in blocks or []:
        t = block.get("type", "text")
        c = block.get("content", "")
        display = block.get("display", "inline")
        if not c:
            continue
        try:
            if t == "text":
                if has_math(str(c)):
                    _flush()
                    _render_block_safe(block, highlight=highlight)
                else:
                    buf.append(str(c))
                    last_was_inline = False
            elif t == "latex":
                c = sanitize_latex_for_render(c)
                if not c:
                    continue
                if display == "block" or not _is_inline_math(c):
                    _flush()
                    _render_block_safe(block, highlight=highlight)
                else:
                    if last_was_inline:
                        buf.append(" ")
                    buf.append(f"${c}$")
                    last_was_inline = True
        except Exception:
            _flush()
            try:
                _render_block_safe(block, highlight=highlight)
            except Exception:
                pass

    _flush()


def _render_block_safe(block: dict, highlight: bool = False) -> None:
    """
    渲染单个 MathBlock — 经过完整的安全层。

    管道:
      Layer 2 (Renderer) — 决定 display 策略
      Layer 3 (Safety)    — safe_latex() token 级修复
      Layer 4 (UI)        — st.latex() / st.markdown()
    """
    import streamlit as st

    t = block.get("type", "text")
    c = block.get("content", "")
    display = block.get("display", "inline")

    if not c:
        return

    try:
        if t == "text":
            # Text blocks may still contain LLM-leaked LaTeX. Route them
            # through the mixed renderer instead of letting Markdown expose raw
            # backslash commands.
            if has_math(str(c)):
                render_ast(split_latex_text(str(c)))
            elif highlight:
                st.markdown(f"**{c}**")
            else:
                st.markdown(c)

        elif t == "latex":
            c = sanitize_latex_for_render(c)
            if not c:
                return
            if display == "block":
                if highlight:
                    st.latex(f"\\boxed{{{c}}}")
                else:
                    st.latex(c)
            else:
                if highlight:
                    st.latex(f"\\boxed{{{c}}}")
                else:
                    if _is_inline_math(c):
                        st.markdown(f"${c}$")
                    else:
                        st.latex(c)

    except Exception:
        try:
            if t == "latex":
                # Don't show raw LaTeX code (red garbled text).
                # Try inline markdown math first, then plain text.
                sc = sanitize_latex_for_render(c) or str(c)
                try:
                    st.markdown(f"${sc}$")
                except Exception:
                    st.text(sc)
            else:
                render_ast(split_latex_text(str(c)))
        except Exception:
            pass


def render_structured_safe(solution: dict) -> None:
    """
    四层解耦渲染器 — 推荐入口。

    Layer 1 (CanonicalTrace): 验证结构化方案
    Layer 2 (Renderer):       决定布局、徽章、颜色
    Layer 3 (Safety):         每个 latex block 经过 safe_latex()
    Layer 4 (UI):             st.latex() / st.markdown()

    这是 render_structured() 的安全增强版，
    在 Layer 3 显式调用 safe_latex() 确保 token 安全。
    """
    import streamlit as st

    _inject_katex_css()

    # ── Layer 1: 验证 CanonicalTrace ──
    is_valid, errors = validate_structured(solution)
    if not is_valid:
        st.error(f"验证失败: {'; '.join(errors)}")
        return

    # ── Layer 2-4: 渲染每个步骤 ──
    for i, step in enumerate(solution.get("steps", [])):
        label = step.get("label", f"步骤{i+1}")
        operation = step.get("operation", "")
        blocks = step.get("blocks", [])

        # Step header: label with subtle operation badge
        op_label, op_color = _OP_META.get(operation, ("", ""))
        with st.container(border=True):
            if op_label:
                st.markdown(
                    f"**{label}** &nbsp;"
                    f"<span style='color:{op_color};background:{op_color}15;"
                    f"border:1px solid {op_color}40;border-radius:4px;"
                    f"padding:1px 8px;font-size:0.75em;'>{op_label}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{label}**")

            body = str(
                step.get("body_markdown")
                or step.get("derivation_markdown")
                or step.get("explanation")
                or ""
            ).strip()
            if body:
                try:
                    from renderers.math_render_policy import render_grading_latex
                    render_grading_latex(body)
                except Exception:
                    render_ast(split_latex_text(body))
            else:
                _render_blocks_safe(blocks)

    # ── final_answer ──
    fa = solution.get("final_answer")
    if fa and fa.get("content"):
        with st.container(border=True):
            st.markdown("**📌 答案**")
            _render_final_answer_safe(fa)

    # ── metadata ──
    meta = solution.get("metadata")
    if meta:
        kps = meta.get("knowledge_points", [])
        if kps:
            tags = " ".join(
                f"<span style='background:#f3f4f6;padding:2px 8px;border-radius:12px;font-size:0.8em;'>{kp}</span>"
                for kp in kps
            )
            st.markdown(f"**知识点**: {tags}", unsafe_allow_html=True)


def pipeline_canonical(source) -> None:
    """
    四层解耦完整管道 — 最终推荐入口。

    用法:
        # 从 LLM JSON
        pipeline_canonical(llm_json_dict)

        # 从旧文本
        pipeline_canonical("步骤1：设 $f(x)=x^2$...")

        # 从 DAG
        pipeline_canonical(canonical_trace)

    管道:
        Layer 1: as_canonical(source) → StructuredSolution
        Layer 2: render_structured_safe() — 渲染决策 + 遍历
        Layer 3: _render_block_safe() → safe_latex() — token 安全
        Layer 4: st.latex() / st.markdown() — 原生渲染
    """
    if source is None:
        return

    # Layer 1: 归一化为 CanonicalTrace
    trace = as_canonical(source)

    # Layer 2-4: 安全渲染
    render_structured_safe(trace)


# 保持旧函数兼容: render_structured 现在委托给安全版
def render_structured(solution: dict) -> None:
    """向后兼容包装器，委托给 render_structured_safe。"""
    render_structured_safe(solution)


# ═══════════════════════════════════════════════════════════════
# 8. 选择题渲染 — st.columns 替代 markdown table
# ═══════════════════════════════════════════════════════════════
#
# Markdown table 对 KaTeX 支持很差，尤其是 \frac、\int 等复杂命令。
# 推荐方案: st.columns + st.latex() 逐个渲染选项。
#
# 布局:
#   st.markdown(题干)
#   col1, col2 = st.columns(2)
#   with col1:
#       st.latex(r"(A) ...")
#       st.latex(r"(C) ...")
#   with col2:
#       st.latex(r"(B) ...")
#       st.latex(r"(D) ...")
# ═══════════════════════════════════════════════════════════════

# 选项标签正则
_OPTION_LABEL_RE = re.compile(
    r'(?:'
    r'\\left\(\\mathrm\{([A-D])\}\\right\)'     # $\left(\mathrm{A}\right)$
    r'|'
    r'\$?\\left\(\\mathrm\{([A-D])\}\\right\)\$?' # with optional $
    r'|'
    r'[（(]\s*([A-D])\s*[）)]'                    # (A) or （A）
    r'|'
    r'(?:^|\n)\s*([A-D])[.．、)\]]\s*'            # A. or A．or A、or A)
    r')'
)

# 单个选项匹配: 标签 + 内容（直到下一个选项标签或文本结束）
_OPTION_RE = re.compile(
    r'(?:\\left\(\\mathrm\{([A-D])\}\\right\)'   # $\left(\mathrm{A}\right)$
    r'|\$?\\left\(\\mathrm\{([A-D])\}\\right\)\$?'
    r'|[（(]\s*([A-D])\s*[）)]'
    r'|(?:^|\n)\s*([A-D])[.．、)\]]\s*'
    r')'
    r'\s*'
    r'((?:(?!'
    r'(?:\\left\(\\mathrm\{[A-D]\}\\right\)'      # 不下一个标签
    r'|\$?\\left\(\\mathrm\{[A-D]\}\\right\)\$?'
    r'|[（(]\s*[A-D]\s*[）)]'
    r'|(?:^|\n)\s*[A-D][.．、)\]]'
    r')'
    r').)*)',
    re.DOTALL,
)


def extract_choices(text: str) -> list[dict]:
    """
    从文本中提取选择题选项。

    支持的格式:
      - $\\left(\\mathrm{A}\\right)$ 内容
      - (A) 内容  /  （A）内容
      - A. 内容  /  A．内容  /  A、内容  /  A) 内容
      - A 内容 (同行)

    返回:
      [{"label": "A", "content": "k=2, c=-\\frac12"}, ...]

    若无选项则返回空列表。
    """
    if not text:
        return []

    options = []
    seen_labels = set()

    # 策略: 先找所有选项标签位置，然后提取标签间的内容
    # 简化版: 用 split 方式处理常见格式

    # 格式1: $\left(\mathrm{X}\right)$ 格式
    pattern1 = re.compile(
        r'\$?\\left\(\\mathrm\{([A-D])\}\\right\)\$?\s*([^$]+?)(?='
        r'\$?\\left\(\\mathrm\{[A-D]\}\\right\)|$)'
    )
    for m in pattern1.finditer(text):
        label = m.group(1)
        content = m.group(2).strip()
        if label not in seen_labels:
            options.append({"label": label, "content": content})
            seen_labels.add(label)

    if len(options) >= 2:
        return options

    # 格式2: (A) / （A）格式
    options = []
    seen_labels = set()
    pattern2 = re.compile(r'[（(]\s*([A-D])\s*[）)]\s*([^（(]+?)(?=[（(]\s*[A-D]\s*[）)]|$)')
    for m in pattern2.finditer(text):
        label = m.group(1)
        content = m.group(2).strip()
        if label not in seen_labels:
            options.append({"label": label, "content": content})
            seen_labels.add(label)

    if len(options) >= 2:
        return options

    # 格式3: A. / A．/ A、/ A) 格式
    options = []
    seen_labels = set()
    pattern3 = re.compile(r'(?:^|\n)\s*([A-D])[.．、)\]]\s*([^\n]+)')
    for m in pattern3.finditer(text):
        label = m.group(1)
        content = m.group(2).strip()
        if label not in seen_labels:
            options.append({"label": label, "content": content})
            seen_labels.add(label)

    return options


def _parse_option_content(content: str) -> str:
    """清理选项内容：去除 $ 包裹，trim 空白，去除尾部标点。"""
    c = content.strip()
    # 去除外层的 $...$ 或 $$...$$
    if c.startswith('$$') and c.endswith('$$'):
        c = c[2:-2].strip()
    elif c.startswith('$') and c.endswith('$'):
        c = c[1:-1].strip()
    # 去除尾部中文句号/分号
    c = re.sub(r'[。；;．]+$', '', c)
    return c.strip()


def render_choices(question_text: str, options: list[dict], cols: int = 2) -> None:
    """
    选择题渲染器 — 使用 st.columns 替代 markdown table。

    渲染流程:
      1. st.markdown(题干) — 题干文本（支持 inline $...$ 数学）
      2. st.columns(N) — N 列布局
      3. 每列: st.latex() — 逐个渲染选项（数学渲染，不经过 markdown table）

    示例:
        render_choices(
            r\"\"\"
            (1) 已知极限 $\\lim_{x\\to0}\\frac{x-\\arctan x}{x^k}=c$，
            其中 $k,c$ 为常数，且 $c\\ne0$，则（ ）
            \"\"\",
            [
                {"label": "A", "content": "k=2, c=-\\frac12"},
                {"label": "B", "content": "k=2, c=\\frac12"},
                {"label": "C", "content": "k=3, c=-\\frac13"},
                {"label": "D", "content": "k=3, c=\\frac13"},
            ],
            cols=2,
        )

    输出:
      col1: (A) k=2, c=-1/2  (C) k=3, c=-1/3
      col2: (B) k=2, c=1/2   (D) k=3, c=1/3
    """
    import streamlit as st

    if not options:
        if question_text:
            st.markdown(question_text)
        return

    # ── 渲染题干 ──
    if question_text:
        try:
            st.markdown(question_text)
        except Exception:
            st.text(question_text[:500])

    # ── 渲染选项: N 列布局 ──
    columns = st.columns(cols)
    for i, opt in enumerate(options):
        label = opt.get("label", "")
        content = _parse_option_content(opt.get("content", ""))
        if not content and not label:
            continue

        col_idx = i % cols
        with columns[col_idx]:
            # 构建 LaTeX 表达式
            latex_str = f"({label})\\ {content}" if label else content
            # ── Layer 3: 安全层 ──
            try:
                safe = safe_latex(f"${latex_str}$")
                if safe.startswith("$") and safe.endswith("$"):
                    safe = safe[1:-1]
                # 选项公式是 inline math，不是 block
                if _is_inline_math(safe):
                    st.markdown(f"${safe}$")
                else:
                    st.latex(safe)
            except Exception:
                try:
                    st.text(latex_str[:500])
                except Exception:
                    pass


def render_choice_question(text: str, cols: int = 2) -> None:
    """
    一键选择题渲染：自动从文本中提取题干和选项并渲染。

    流程:
      1. extract_choices(text) — 提取选项
      2. 题干 = text 中删除选项部分
      3. render_choices(题干, 选项, cols) — column 布局渲染
    """
    if not text:
        return

    options = extract_choices(text)

    if not options:
        # 没有检测到选项，回退到普通渲染
        import streamlit as st
        try:
            st.markdown(text)
        except Exception:
            st.text(text[:500])
        return

    # 题干: 删除选项文本
    stem = text
    for opt in options:
        label = opt["label"]
        content = opt.get("content", "")
        # 尝试删除已知格式的选项
        for pat in [
            rf'\$?\\left\(\\mathrm\{{{label}\}}\\right\)\$?\s*{re.escape(content)}',
            rf'[（(]\s*{label}\s*[）)]\s*{re.escape(content)}',
            rf'\n\s*{label}[.．、)\]]\s*{re.escape(content)}',
        ]:
            try:
                stem = re.sub(pat, '', stem)
            except re.error:
                pass

    stem = stem.strip()
    render_choices(stem, options, cols=cols)


# ═══════════════════════════════════════════════
# 9. 统一渲染入口 — safe_render (修复渲染混乱的核心)
# ═══════════════════════════════════════════════
#
# 问题根源:
#   OCR/用户输入 → 直接 st.markdown() → LaTeX 源码显示
#
# 解决方案:
#   OCR/用户输入 → UnifiedRenderer (语义驱动渲染)
#
# 完整管道:
#   原始文本
#     → LaTeXFixer.fix()        # 修复双反斜杠、OCR符号、花括号平衡
#     → clean_markdown()         # 清理 Markdown 污染
#     → DocumentParser           # 文本 → Document AST (语义分类)
#     → LayoutEngine             # Document AST → Markdown/LaTeX
#     → Frontend Render          # st.latex / st.markdown
#
# 关键升级:
#   - 不再使用 regex split (无法处理嵌套)
#   - 使用 ContentClassifier 做语义分类
#   - 使用 DocumentParser 构建结构化 AST
#   - 使用 LayoutEngine 做 proper layout
#
# 使用方式:
#   from latex_utils import safe_render
#   safe_render(student_answer, role="student_answer")
# ═══════════════════════════════════════════════

# 渲染器单例缓存
_renderer_instance = None

def _get_renderer():
    """获取渲染器单例，避免重复初始化"""
    global _renderer_instance
    if _renderer_instance is None:
        from rendering.unified_renderer import UnifiedRenderer
        _renderer_instance = UnifiedRenderer()
    return _renderer_instance

def _preprocess_latex(text: str) -> str:
    """Replace KaTeX-unsupported LaTeX commands before rendering.

    Runs BEFORE any rendering pipeline so downstream code never sees
    commands that KaTeX cannot handle.
    """
    if not text:
        return text
    import re as _re
    # \textcircled{n} → Unicode circled digit (KaTeX doesn't support \textcircled)
    _CIRCLED_MAP = {str(i): chr(0x245F + i) for i in range(1, 10)}
    text = _re.sub(
        r'\\textcircled\s*\{\s*(\d)\s*\}',
        lambda m: _CIRCLED_MAP.get(m.group(1), m.group(1)),
        text,
    )
    # \textcircled{anything else} → (anything)
    text = _re.sub(r'\\textcircled\s*\{([^}]*)\}', r'(\1)', text)
    return text


def safe_render(text: str, role: str = "", *, context=None) -> None:
    """
    统一渲染入口 — 必须显式传入 context，禁止无上下文自动猜测。

    请优先使用:
      - render_question_bank_latex()  真题库（严格保真）
      - render_grading_latex()        AI 批改（容错修复）

    context 取值: MathRenderContext.QUESTION_BANK 或 MathRenderContext.GRADING
    """
    if context is None:
        raise ValueError(
            "safe_render requires explicit context=MathRenderContext.QUESTION_BANK "
            "or MathRenderContext.GRADING. Use render_question_bank_latex() / "
            "render_grading_latex() instead."
        )

    from renderers.math_render_policy import render_latex_for_context

    # role is kept for backward-compatible call signatures; policy drives behavior.
    _ = role
    render_latex_for_context(text, context)


def safe_render_markdown(text: str, role: str = "") -> str:
    """
    返回处理后的 Markdown 字符串（用于需要返回内容的场景）。

    与 safe_render 的区别:
      - safe_render: 直接渲染到 Streamlit (void 函数)
      - safe_render_markdown: 返回处理后的字符串，可进一步处理

    管道: fix → clean → DocumentParser → LayoutEngine

    性能优化:
      - 使用单例模式复用渲染器实例
    """
    if not text:
        return text

    if not isinstance(text, str):
        text = str(text)

    try:
        renderer = _get_renderer()
        return renderer.render(text, role=role)
    except Exception:
        import traceback
        traceback.print_exc()
        return text


# ═══════════════════════════════════════════════
#  P16: tag extraction + display math helpers
# ═══════════════════════════════════════════════

_TAG_RE = re.compile(r"(?s)^(.*?)(?:\s*\\tag\{([^{}]+)\})\s*$")


def split_latex_tag(latex: str) -> tuple:
    """Split 'x+y=0 \\tag{1}' into ('x+y=0', '1')."""
    if not latex:
        return latex, None
    s = str(latex).strip()
    m = _TAG_RE.match(s)
    if not m:
        return s, None
    body = m.group(1).strip()
    tag = m.group(2).strip() if m.group(2) else None
    return body, tag


def _is_long_tagged_formula(body: str) -> bool:
    """True if formula is long enough to need tag-below layout."""
    s = str(body or "").replace("\n", "").strip()
    return len(s) > 70 or r"\begin{aligned}" in s or r"\\" in s


_MATHY_COMMAND_RE = re.compile(
    r'\\(?:'
    r'frac|dfrac|tfrac|cfrac|sqrt|lim|sum|prod|int|iint|iiint|oint|'
    r'sin|cos|tan|cot|sec|csc|ln|log|exp|arcsin|arccos|arctan|'
    r'forall|exists|in|notin|subset|subseteq|cup|cap|to|Rightarrow|'
    r'Leftarrow|rightarrow|leftarrow|leq|geq|ne|neq|approx|sim|'
    r'alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|xi|rho|'
    r'sigma|phi|omega|Gamma|Delta|Theta|Lambda|Pi|Sigma|Omega|'
    r'begin|end|boxed|left|right|mathrm|mathbf|mathbb|mathcal'
    r')(?=\b|[_{([<\s]|$)'
)


def _should_force_display_math(fragment: str) -> bool:
    """Heuristic: should this fragment render as display (block) math?"""
    s = str(fragment or "").strip()
    if not s:
        return False
    if r'\begin' in s or r'\end' in s:
        return True
    if '\n' in s and len(s) >= 40:
        return True
    if r'\tag' in s:
        return True
    if r'\sum' in s or r'\int' in s or r'\iint' in s or r'\prod' in s:
        if '_' in s or '^' in s:
            return True
    if r'\frac' in s and len(s) >= 30:
        return True
    if r'\bigl' in s or r'\Bigl' in s or r'\biggl' in s:
        return True
    return False


def clean_latex_spacing_artifacts(s: str) -> str:
    """Remove LaTeX spacing artifacts: \\[2mm], [2mm], \\[1em], etc."""
    if not s:
        return s
    s = re.sub(r"\\\\\s*\[[0-9.]+\s*(?:mm|em|ex|pt)\]", r"\\\\", s)
    s = re.sub(r"\\\s*\[[0-9.]+\s*(?:mm|em|ex|pt)\]", "", s)
    s = re.sub(r"(?<!\\)\[[0-9.]+\s*(?:mm|em|ex|pt)\]", "", s)
    return s


def _clean_formula_tail(s: str) -> str:
    """Remove Chinese punctuation and trailing text after \\tag{} from display formulas."""
    if not s:
        return s
    s = s.strip()
    s = s.rstrip("，。；：、")
    m = re.search(r"(.*?\\tag\{[^}]+\})", s)
    if m:
        return m.group(1).strip()
    return s
