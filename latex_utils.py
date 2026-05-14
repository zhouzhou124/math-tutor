"""
latex_utils.py — 统一LaTeX工具集

集中管理所有 LaTeX 处理函数，提供单一导入点。
所有需要处理数学内容的地方都应从这里导入。

架构:
  Layer 0 — LLM 输出结构化 JSON（不再输出 markdown）
  Layer 1 — schema 验证 + 从旧格式转换
  Layer 2 — render_structured() 控制全部显示

完整管道: structured JSON → validate → render_structured

子模块来源:
  math_sanitizer       — 安全层（分隔符修复、HTML转义、裸公式包裹）
  latex_normalizer     — 风格规范化（15条确定性规则）
  latex_repair         — LLM输出修复（破损标记、选项分析）
  math_structure_validator — 入库前结构验证
"""

import re
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════
# Re-exports: math_sanitizer
# ═══════════════════════════════════════════════
from math_sanitizer import safe_latex, is_valid_latex, validate_expression

# ═══════════════════════════════════════════════
# Re-exports: latex_normalizer
# ═══════════════════════════════════════════════
from latex_normalizer import normalize_latex_style, is_normalized, validate_normalization

# ═══════════════════════════════════════════════
# Re-exports: latex_repair
# ═══════════════════════════════════════════════
from latex_repair import (
    repair_latex_delimiters,
    ensure_math_wrap,
    repair_option_analysis_text,
)

# ═══════════════════════════════════════════════
# Re-exports: math_structure_validator
# ═══════════════════════════════════════════════
from math_structure_validator import validate as validate_structure, ValidationReport


# ═══════════════════════════════════════════════
# 管道便捷函数
# ═══════════════════════════════════════════════

def process_latex(text: str) -> str:
    """
    完整 LaTeX 处理管道: repair → sanitize → normalize。

    适用于所有不可信来源（LLM输出、用户输入、OCR结果）。
    纯函数，相同输入永远返回相同输出。
    """
    if not text:
        return text
    text = repair_latex_delimiters(text)
    text = safe_latex(text)
    text = normalize_latex_style(text)
    return text


def clean_latex(text: str) -> str:
    """轻量管道: sanitize → normalize（跳过 repair）。"""
    if not text:
        return text
    text = safe_latex(text)
    text = normalize_latex_style(text)
    return text


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
    """自动修复 {} 配对。"""
    depth = 0
    for c in s:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1

    if depth == 0:
        return s
    if depth > 0:
        return s + '}' * depth
    else:
        # 从尾部删除多余的 }
        result = s
        for _ in range(-depth):
            idx = result.rfind('}')
            if idx >= 0:
                result = result[:idx] + result[idx+1:]
        return result


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

    result = text
    for pattern, replacement in _MD_POLLUTION:
        result = pattern.sub(replacement, result)

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

    # 清理未被正确恢复的占位符
    # 这些占位符来自 latex_normalizer._wrap_bare_math_expressions 或 ocr_repair.layout_recovery
    # 格式: \x00M{i}\x00 或 \x00MATH{i}\x00
    text = re.sub(r'\x00M\d+\x00', '', text)
    text = re.sub(r'\x00MATH\d+\x00', '', text)

    # ── Step 1: 修复被分割的命令 ──
    # 例如: \s in x → \sin x, \c os x → \cos x
    # 注意：替换字符串必须使用原始字符串 r''，否则 \s 会被解释为空白字符
    split_cmds = [
        (r'\arcsin', r'\\arcs\s*in'),
        (r'\arccos', r'\\arcc\s*os'),
        (r'\arctan', r'\\arct\s*an'),
        (r'\arccot', r'\\arcc\s*ot'),
        (r'\arcsec', r'\\arcsec'),
        (r'\arccsc', r'\\arccsc'),
        (r'\sinh', r'\\sin\s*h'),
        (r'\cosh', r'\\cos\s*h'),
        (r'\tanh', r'\\tan\s*h'),
        (r'\coth', r'\\cot\s*h'),
        (r'\sech', r'\\sec\s*h'),
        (r'\csch', r'\\csc\s*h'),
        (r'\limsup', r'\\lim\s*sup'),
        (r'\liminf', r'\\lim\s*inf'),
        (r'\varlimsup', r'\\varlim\s*sup'),
        (r'\varliminf', r'\\varlim\s*inf'),
        (r'\sin', r'\\s\s*in'),
        (r'\cos', r'\\c\s*os'),
        (r'\tan', r'\\t\s*an'),
        (r'\cot', r'\\c\s*ot'),
        (r'\sec', r'\\s\s*ec'),
        (r'\csc', r'\\c\s*sc'),
        (r'\log', r'\\l\s*og'),
        (r'\ln', r'\\l\s*n'),
        (r'\exp', r'\\e\s*xp'),
        (r'\min', r'\\m\s*in'),
        (r'\max', r'\\m\s*ax'),
        (r'\sup', r'\\s\s*up'),
        (r'\inf', r'\\i\s*nf'),
        (r'\det', r'\\d\s*et'),
        (r'\dim', r'\\d\s*im'),
        (r'\deg', r'\\d\s*eg'),
        (r'\arg', r'\\a\s*rg'),
        (r'\rank', r'\\r\s*ank'),
    ]
    
    for target, pattern in split_cmds:
        # 使用 lambda 函数避免替换字符串被解析为模板
        text = re.sub(pattern, lambda m, t=target: t, text)

    # ── Step 2: Unicode数学符号转换为LaTeX命令 ──
    unicode_to_latex = {
        '∈': r'\in',
        '∉': r'\notin',
        '⊂': r'\subset',
        '⊃': r'\supset',
        '⊆': r'\subseteq',
        '⊇': r'\supseteq',
        '∩': r'\cap',
        '∪': r'\cup',
        '∅': r'\emptyset',
        '∞': r'\infty',
        '≤': r'\leq',
        '≥': r'\geq',
        '≠': r'\neq',
        '≡': r'\equiv',
        '≈': r'\approx',
        '∼': r'\sim',
        '≃': r'\simeq',
        '≅': r'\cong',
        '→': r'\rightarrow',
        '←': r'\leftarrow',
        '⇒': r'\Rightarrow',
        '⇐': r'\Leftarrow',
        '⇔': r'\Leftrightarrow',
        '↔': r'\leftrightarrow',
        '×': r'\times',
        '·': r'\cdot',
        '÷': r'\div',
        '±': r'\pm',
        '∓': r'\mp',
        '∀': r'\forall',
        '∃': r'\exists',
        '∂': r'\partial',
        '∇': r'\nabla',
        '√': r'\sqrt',
        '∑': r'\sum',
        '∏': r'\prod',
        '∫': r'\int',
        '∬': r'\iint',
        '∭': r'\iiint',
        '∮': r'\oint',
        '∠': r'\angle',
        '⊥': r'\perp',
        '∥': r'\parallel',
        '△': r'\triangle',
        '□': r'\square',
        '°': r'^\circ',
        '′': r'\prime',
        '″': r'\prime\prime',
        'α': r'\alpha',
        'β': r'\beta',
        'γ': r'\gamma',
        'δ': r'\delta',
        'ε': r'\epsilon',
        'ζ': r'\zeta',
        'η': r'\eta',
        'θ': r'\theta',
        'ι': r'\iota',
        'κ': r'\kappa',
        'λ': r'\lambda',
        'μ': r'\mu',
        'ν': r'\nu',
        'ξ': r'\xi',
        'π': r'\pi',
        'ρ': r'\rho',
        'σ': r'\sigma',
        'τ': r'\tau',
        'υ': r'\upsilon',
        'φ': r'\phi',
        'χ': r'\chi',
        'ψ': r'\psi',
        'ω': r'\omega',
        'Γ': r'\Gamma',
        'Δ': r'\Delta',
        'Θ': r'\Theta',
        'Λ': r'\Lambda',
        'Ξ': r'\Xi',
        'Π': r'\Pi',
        'Σ': r'\Sigma',
        'Υ': r'\Upsilon',
        'Φ': r'\Phi',
        'Ψ': r'\Psi',
        'Ω': r'\Omega',
    }
    
    # 只在数学模式外替换Unicode符号
    protected_math = []
    def _protect_math(m):
        protected_math.append(m.group(0))
        return f'\x00MATH{len(protected_math)-1}\x00'
    
    temp_text = re.sub(r'\$\$.*?\$\$', _protect_math, text, flags=re.DOTALL)
    temp_text = re.sub(r'(?<!\$)\$[^$\n]+?\$(?!\$)', _protect_math, temp_text)
    
    for unicode_char, latex_cmd in unicode_to_latex.items():
        temp_text = temp_text.replace(unicode_char, latex_cmd)
    
    for i, block in enumerate(protected_math):
        temp_text = temp_text.replace(f'\x00MATH{i}\x00', block)
    
    text = temp_text

    # ── Step 3: 恢复丢失的反斜杠 ──
    # 常见的 LaTeX 命令可能在数据存储/传输过程中丢失反斜杠
    # 检测并恢复这些命令前的反斜杠
    latex_commands = [
        'limsup', 'liminf', 'varlimsup', 'varliminf',
        'arcsin', 'arccos', 'arctan', 'arccot', 'arcsec', 'arccsc',
        'arcsinh', 'arccosh', 'arctanh', 'arccoth', 'arcsech', 'arccsch',
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb',
        'ldots', 'cdots', 'vdots', 'ddots',
        'Rightarrow', 'Leftarrow', 'leftrightarrow', 'Leftrightarrow',
        'rightarrow', 'leftarrow', 'mapsto', 'hookleftarrow', 'hookrightarrow',
        'Biggl', 'biggr', 'Biggr',
        'partial', 'nabla', 'triangle', 'square', 'diamond', 'circ', 'bullet',
        'oplus', 'otimes', 'odot', 'coprod', 'bigcup', 'bigcap', 'bigsqcup',
        'subseteq', 'supseteq', 'approx', 'cong', 'equiv', 'sim', 'simeq',
        'triangle', 'square', 'diamond', 'circ', 'bullet',
        'frac', 'dfrac', 'cfrac', 'tfrac', 'sqrt', 'root', 'abs', 'norm',
        'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
        'sinh', 'cosh', 'tanh', 'coth', 'sech', 'csch',
        'log', 'ln', 'exp', 'lg', 'min', 'max', 'sum', 'prod', 'int',
        'oint', 'iint', 'iiint', 'iiiint', 'idotsint',
        'lim', 'inf', 'sup', 'arg', 'dim', 'deg', 'det', 'rank',
        'over', 'atop', 'choose', 'binom', 'hat', 'widehat', 'tilde', 'widetilde',
        'bar', 'vec', 'dot', 'ddot', 'prime', 'dagger', 'ddagger',
        'cdot', 'times', 'div', 'pm', 'mp', 'cap', 'cup', 'setminus',
        'leq', 'geq', 'neq', 'equiv', 'sim', 'simeq', 'approx', 'cong',
        'in', 'notin', 'ni', 'exists', 'forall', 'emptyset', 'infty',
        'to', 'partial', 'nabla',
        'pi', 'theta', 'phi', 'psi', 'omega', 'alpha', 'beta', 'gamma', 'delta',
        'epsilon', 'zeta', 'eta', 'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi',
        'rho', 'sigma', 'tau', 'upsilon', 'chi',
        'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 'Pi', 'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega',
        'left', 'right', 'middle', 'Big', 'bigg',
        'le', 'ge', 'lt', 'gt',
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
    # 模式：从\命令开始，匹配所有连续的数学内容直到遇到中文或标点
    # 支持：\命令、花括号内容、数字、字母、下划线、上标、运算符、空格等
    # 注意：连字符必须放在字符类的开头或结尾，或者转义
    bare_math_pattern = r'\\[a-zA-Z]+(?:\{[^{}]*\})*(?:\{[^{}]*\})?(?:[-\w_^^{} \s+*/=<>()\[\]|\\]+|\\[a-zA-Z]+(?:\{[^{}]*\})*(?:\{[^{}]*\})?)*'
    
    # 排除的纯间距命令（这些不是数学表达式）
    skip_commands = {'\\quad', '\\qquad', '\\hspace', '\\vspace', '\\hfill', '\\vfill'}
    
    # 扫描文本，找到所有裸数学表达式区域
    bare_matches = []
    for match in re.finditer(bare_math_pattern, text):
        # 检查匹配是否完全在非数学区域内
        is_in_math = False
        for i in range(match.start(), min(match.end(), len(in_math_region))):
            if in_math_region[i]:
                is_in_math = True
                break
        if not is_in_math:
            # 只保留看起来像数学表达式的匹配
            content = match.group(0).strip()
            if content and len(content) > 1:
                # 排除纯间距命令
                if content not in skip_commands:
                    bare_matches.append(match)
    
    # 如果找到裸数学表达式，用$包裹它们（从后往前处理避免位置偏移）
    if bare_matches:
        new_text = text
        # 按位置从后往前处理
        for match in reversed(bare_matches):
            # 在匹配前后添加$
            new_text = new_text[:match.start()] + '$' + new_text[match.start():match.end()] + '$' + new_text[match.end():]
        text = new_text

    # 在选择题选项之间添加换行符，使每个选项独立一行
    # 匹配模式: (A)...(B)... → 在 (B) 前添加换行
    # 支持的格式: (A) （A） A) A. A、 A．
    # 选项标签通常出现在 \qquad 或 \quad 之后，或者行首，而不是数学表达式中间
    # 使用正向后瞻确保前面是 \qquad 或 \quad 或行首

    # 先处理 \qquad 或 \quad 之后的选项
    text = re.sub(r'(\\qquad|\\quad)\s*\([A-D]\)', lambda m: m.group(1) + '\n(' + m.group(2) if len(m.groups()) > 1 else m.group(1) + '\n(', text)
    
    # 处理行首的选项标签（前面是换行或字符串开头）
    text = re.sub(r'(?<=\n)\s*\([A-D]\)', lambda m: '\n' + m.group(0), text)
    text = re.sub(r'^\s*\([A-D]\)', lambda m: '\n' + m.group(0), text)
    
    # 处理中文括号格式
    text = re.sub(r'(\\qquad|\\quad)\s*（[A-D]）', lambda m: m.group(1) + '\n' + m.group(2), text)
    
    # 处理不带左括号的选项格式 A) 或 A. 或 A、
    text = re.sub(r'(\\qquad|\\quad)\s*([A-D][)．、。])', lambda m: m.group(1) + '\n' + m.group(2), text)

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

    return segments


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


# ═══════════════════════════════════════════════
# 5. AST-first 渲染器（推荐）
# ═══════════════════════════════════════════════

def _is_inline_math(content: str) -> bool:
    """判断 LaTeX 表达式是否应为 inline 模式。

    规则:
      - 长度 >= 80 → block
      - 含 \\begin, \\\\ (LaTeX 换行), align, cases, array → block
      - 含 \\displaystyle, \\sum, \\int, \\prod, 嵌套 \\frac → block
      - 否则 → inline
    """
    if len(content) >= 80:
        return False
    # LaTeX 换行符：两个连续反斜杠
    if chr(92) + chr(92) in content:
        return False
    # 其他 block 模式标记
    _bs = chr(92)  # backslash
    _block_cmds = [
        _bs + 'begin', _bs + 'displaystyle',
        _bs + 'sum', _bs + 'int', _bs + 'prod',
        _bs + 'lim' + _bs + 'limits',  # \lim\limits
        'align', 'cases', 'array',
    ]
    for cmd in _block_cmds:
        if cmd in content:
            return False
    if '\n' in content:
        return False
    return True


def render_ast(segments: list[dict]) -> None:
    """
    AST-first 渲染器：inline vs block 严格区分。

    关键：连续的 text + inline_math 合并为单个 st.markdown() 调用，
    避免每个片段单独渲染导致的换行碎片化。

    分派规则:
      - text + inline_math → 合并 → st.markdown(连续段落)
      - display_math       → st.latex(content)
      - latex (兼容)       → 智能检测

    使用示例:
        from latex_utils import split_latex_text, render_ast
        segments = split_latex_text(raw_text)
        render_ast(segments)
    """
    import streamlit as st

    # 合并连续的 text + inline_math 为单个 markdown 块
    buf = []
    def _flush():
        if buf:
            md = "".join(buf)
            # 只去除首尾空白字符，保留换行符
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
                # 在连续的 inline_math 之间添加空格，避免 $$ 相邻
                if last_was_inline_math:
                    buf.append(" ")
                buf.append(f"${c}$")
                last_was_inline_math = True
            elif t == "display_math":
                _flush()
                st.latex(c)
                last_was_inline_math = False
            elif t == "latex":
                _flush()
                if _is_inline_math(c):
                    st.markdown(f"${c}$")
                else:
                    st.latex(c)
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

    valid_types = {"text", "latex"}
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
            if fa.get("type") not in valid_types:
                errors.append("final_answer.type 无效")
            if "content" not in fa:
                errors.append("final_answer 缺少 'content'")

    return len(errors) == 0, errors


# ═══════════════════════════════════════════════
# 6c. 结构化渲染器 — 根本解决方案的核心
# ═══════════════════════════════════════════════

def render_structured(solution: dict) -> None:
    """
    结构化数学渲染器 — 根本解决方案。

    LLM 输出结构化 JSON，Renderer 控制全部显示。
    不是 markdown-first，而是 structure-first。

    渲染规则:
      - 每个 step → 一个带标签+操作徽章的容器
      - text block → st.markdown()
      - latex block (inline) → st.markdown("$...$")
      - latex block (block) → st.latex()
      - final_answer → 高亮答案框

    使用:
        solution = {
            "steps": [
                {"label": "步骤1", "blocks": [...], "operation": "classify"},
            ],
            "final_answer": {"type": "latex", "content": "1"}
        }
        render_structured(solution)
    """
    import streamlit as st

    # 验证
    is_valid, errors = validate_structured(solution)
    if not is_valid:
        st.error(f"结构化方案验证失败: {'; '.join(errors)}")

    # ── 渲染每个步骤 ──
    for i, step in enumerate(solution.get("steps", [])):
        label = step.get("label", f"步骤{i+1}")
        operation = step.get("operation", "")
        blocks = step.get("blocks", [])

        # 步骤标题行：标签 + 操作徽章
        op_label, op_color = _OP_META.get(operation, ("", ""))
        if op_label:
            st.markdown(
                f"**{label}** &nbsp; "
                f"<span style='color:{op_color};border:1px solid {op_color};"
                f"border-radius:4px;padding:1px 8px;font-size:0.8em;'>{op_label}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{label}**")

        # 渲染本步骤的 blocks
        for block in blocks:
            _render_block(block)

        # 步骤间分隔
        if i < len(solution["steps"]) - 1:
            st.markdown("---")

    # ── 渲染最终答案 ──
    fa = solution.get("final_answer")
    if fa and fa.get("content"):
        st.markdown("---")
        st.markdown("**📌 答案**")
        _render_block(fa, highlight=True)

    # ── 渲染元数据 ──
    meta = solution.get("metadata")
    if meta:
        kps = meta.get("knowledge_points", [])
        if kps:
            tags = " ".join(
                f"<span style='background:#f3f4f6;padding:2px 8px;border-radius:12px;font-size:0.8em;'>{kp}</span>"
                for kp in kps
            )
            st.markdown(f"**知识点**: {tags}", unsafe_allow_html=True)


def _render_block(block: dict, highlight: bool = False) -> None:
    """渲染单个 MathBlock。"""
    import streamlit as st

    t = block.get("type", "text")
    c = block.get("content", "")
    display = block.get("display", "inline")

    if not c:
        return

    try:
        if t == "text":
            if highlight:
                st.markdown(f"**{c}**")
            else:
                st.markdown(c)

        elif t == "latex":
            if display == "block":
                if highlight:
                    st.latex(f"\\boxed{{{c}}}")
                else:
                    st.latex(c)
            else:
                if highlight:
                    st.markdown(f"$\\boxed{{{c}}}$")
                else:
                    st.markdown(f"${c}$")

    except Exception:
        try:
            st.text(c[:500])
        except Exception:
            pass


# ═══════════════════════════════════════════════
# 6d. 旧格式转换 — 从混合 text 到结构化方案
# ═══════════════════════════════════════════════

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

    _STEP_RE = re.compile(r'(?:步骤|第)\s*(\d+)\s*(?:步|题|问)?\s*[：:]\s*')

    # Step 1: 检测步骤边界
    step_boundaries = []  # [(step_num, start_pos, end_pos)]
    for m in _STEP_RE.finditer(text):
        step_boundaries.append((int(m.group(1)), m.start(), m.end()))

    if not step_boundaries:
        # 没有步骤标记，整段作为一个 step
        cleaned = clean_markdown(text)
        segments = split_latex_text(cleaned)
        blocks = _segments_to_blocks(segments)
        return make_solution(steps=[make_step("", blocks)])

    # Step 2: 按边界拆分
    steps = []
    for i, (step_num, start, end) in enumerate(step_boundaries):
        # 本步骤内容：从标记结束到下一个标记开始
        next_start = step_boundaries[i + 1][1] if i + 1 < len(step_boundaries) else len(text)
        chunk = text[end:next_start].strip()

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
            blocks.append(make_latex(c, display="inline"))
        elif t == "display_math":
            blocks.append(make_latex(c, display="block"))
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
            # 纯文本 → 直接 UI 层
            if highlight:
                st.markdown(f"**{c}**")
            else:
                st.markdown(c)

        elif t == "latex":
            # ── Layer 3: 安全层 ──
            safe = safe_latex(f"${c}$")  # 临时包裹以通过 sanitize
            # 去除 safe_latex 添加的外层 $...$
            if safe.startswith("$") and safe.endswith("$"):
                safe = safe[1:-1]

            # ── Layer 4: UI 层 ──
            if display == "block":
                if highlight:
                    st.latex(f"\\boxed{{{safe}}}")
                else:
                    st.latex(safe)
            else:
                if highlight:
                    st.markdown(f"$\\boxed{{{safe}}}$")
                else:
                    st.markdown(f"${safe}$")

    except Exception:
        try:
            st.text(c[:500])
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

        # Layer 2: 操作徽章
        op_label, op_color = _OP_META.get(operation, ("", ""))
        if op_label:
            st.markdown(
                f"**{label}** &nbsp; "
                f"<span style='color:{op_color};border:1px solid {op_color};"
                f"border-radius:4px;padding:1px 8px;font-size:0.8em;'>{op_label}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{label}**")

        # Layer 3-4: 渲染每个 block
        for block in blocks:
            _render_block_safe(block)

        if i < len(solution["steps"]) - 1:
            st.markdown("---")

    # ── final_answer ──
    fa = solution.get("final_answer")
    if fa and fa.get("content"):
        st.markdown("---")
        st.markdown("**答案**")
        _render_block_safe(fa, highlight=True)

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
      - $\left(\mathrm{A}\right)$ 内容
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
