"""
LaTeX Style Normalizer — 确定性格式化层

原则:
  - 纯函数，无副作用，完全可复现
  - 不改变数学语义，只改变表示形式
  - 对所有输入（LLM输出、存储题目、用户输入）统一处理

管道位置:
  LLM Output → latex_normalizer → renderer → storage/display

适用场景:
  - OCR Repair 后处理
  - AI 生成内容规范化
  - 用户输入清理
  - 存储前标准化
  - 渲染前预处理
"""

import re

# ═══════════════════════════════════════════════
# 规则列表（按顺序应用）
# ═══════════════════════════════════════════════

def normalize_latex_style(text: str) -> str:
    """
    主入口: 统一规范化 LaTeX 风格。

    返回规范化后的文本。
    纯函数：相同输入永远返回相同输出。
    """
    if not text:
        return text

    s = text

    # ── 0. 基础清理: 转义换行符、嵌套数学环境 ──
    s = _remove_escaped_newlines(s)
    s = _fix_nested_math(s)

    # ── 0.5. R0: 特定模式 $ 包裹（仅安全模式）──
    s = _wrap_bare_math_expressions(s)

    # ── 1. 选项标签: (A) / A. / （A） → $\left(\mathrm{A}\right)$ ──
    s = _normalize_choice_options(s)

    # ── 2. 求和: \sum_{...}^{...} → \sum\limits_{...}^{...} ──
    s = _normalize_summation(s)

    # ── 3. 积分: \int_{...}^{...} → \int\limits_{...}^{...} ──
    s = _normalize_integral(s)

    # ── 4. 微分: dx → \,\mathrm{d}x ──
    s = _normalize_differential(s)

    # ── 5. 极限: \lim_{...} → \lim\limits_{...} ──
    s = _normalize_limit(s)

    # ── 6. 三角函数: sin → \sin ──
    s = _normalize_trig_functions(s)

    # ── 7. 可伸缩括号: (...) → \left( ... \right) ──
    s = _normalize_delimiters(s)

    # ── 8. 中文必须在数学模式外 ──
    s = _fix_chinese_in_math(s)

    # ── 9. KaTeX 不兼容命令替换 ──
    s = _normalize_katex_compat(s)

    # ── 10. 规范化运算符: \ne→\neq, \le→\leq, \ge→\geq ──
    s = _normalize_operators(s)

    # ── 12. 去重: \left\left → \left, \limits\limits → \limits ──
    s = _dedup_commands(s)

    # ── 13. 空行/空白规范化 ──
    s = _normalize_whitespace(s)

    return s


# ═══════════════════════════════════════════════
# 规则实现
# ═══════════════════════════════════════════════

def _normalize_choice_options(text: str) -> str:
    """统一选择题选项格式为 $\left(\mathrm{A}\right)$，每个选项独占一行"""

    # Step 1: 确保已有的 \left(\mathrm{A}\right) 被 $ 包裹（不带 $ 的版本）
    for letter in 'ABCD':
        text = re.sub(
            r'(?<!\$)\\left\(\\mathrm\{' + letter + r'\}\\right\)(?!\$|\.)',
            lambda m, L=letter: r'$\left(\\mathrm{' + L + r'}\right)$',
            text,
        )

    # Step 2: （A）xxx 或 (A)xxx → $\left(\mathrm{A}\right)$ xxx
    text = re.sub(
        r'(?:^|\n)\s*[（(]\s*([A-D])\s*[）)](?!\$)',
        lambda m: '\n$\\left(\\mathrm{' + m.group(1) + '}\\right)$ ',
        text,
    )

    # Step 3: A.xxx / A．xxx / A、xxx → $\left(\mathrm{A}\right)$ xxx
    text = re.sub(
        r'(?:^|\n)\s*([A-D])[.．、]\s*(?!\$)',
        lambda m: '\n$\\left(\\mathrm{' + m.group(1) + '}\\right)$ ',
        text,
    )

    # Step 4: 确保每个选项独占一行（仅在非行首时加换行）
    text = re.sub(
        r'(?<!\n)\$\\left\(\\mathrm\{([A-D])\}\\right\)\$',
        lambda m: '\n$\\left(\\mathrm{' + m.group(1) + '}\\right)$',
        text,
    )

    # Step 5: 拆分同行选项 — 用 \qquad/\quad 连接的选项 → 各占一行
    for sep in ['\\\\qquad', '\\\\quad']:
        # 匹配: option1_text sep option2_marker
        text = re.sub(
            r'(\$\\left\(\\mathrm\{([A-D])\}\\right\)\$[^$\n]+?)' + sep + r'\s*(\$\\left\(\\mathrm\{([A-D])\}\\right\)\$)',
            lambda m: m.group(1) + '\n' + m.group(3),
            text,
        )

    # Step 6: 清理多余空行和行首空行
    text = re.sub(r'\n{3,}', r'\n\n', text)
    text = text.lstrip('\n')

    return text


def _normalize_summation(text: str) -> str:
    """\sum_{a}^{b} → \sum\limits_{a}^{b}"""
    text = text.replace('\\sum_{', '\\sum\\limits_{')
    text = text.replace('\\sum _{', '\\sum\\limits_{')
    return text


def _normalize_integral(text: str) -> str:
    r"""\int_{a}^{b} → \int\limits_{a}^{b}"""
    for cmd in ['\\int', '\\iint', '\\iiint', '\\oint']:
        text = text.replace(cmd + '_{', cmd + '\\limits_{')
        text = text.replace(cmd + ' _{', cmd + '\\limits_{')
    return text


def _normalize_differential(text: str) -> str:
    """dx → \,\mathrm{d}x (仅在数学模式内)"""
    # 替换数学模式内的裸 dx
    for var in ['x', 'y', 'z', 't', 'r', 's', 'u', 'v', 'w']:
        # 在 $...$ 内替换
        def _replace_in_math(match):
            content = match.group(1)
            # 只替换前面有空格的 dx
            content = content.replace(' d' + var, r' \,\mathrm{d}' + var)
            content = content.replace(' d' + var + ' ', r' \,\mathrm{d}' + var + ' ')
            return '$' + content + '$'
        text = re.sub(r'\$([^$]+)\$', _replace_in_math, text)
    return text


def _normalize_limit(text: str) -> str:
    """\lim_{a \to b} → \lim\limits_{a \to b}"""
    text = text.replace('\\lim_{', '\\lim\\limits_{')
    text = text.replace('\\lim _{', '\\lim\\limits_{')
    return text


def _normalize_trig_functions(text: str) -> str:
    """sin → \sin, cos → \cos 等（仅在数学模式内）"""
    trig_map = {
        'sin': r'\sin', 'cos': r'\cos', 'tan': r'\tan',
        'cot': r'\cot', 'sec': r'\sec', 'csc': r'\csc',
        'arcsin': r'\arcsin', 'arccos': r'\arccos', 'arctan': r'\arctan',
        'ln': r'\ln', 'log': r'\log', 'exp': r'\exp',
        'lim': r'\lim', 'max': r'\max', 'min': r'\min',
        'sup': r'\sup', 'inf': r'\inf', 'det': r'\det',
    }
    # 只在数学模式 $...$ 中替换（使用 lambda 避免 replacement 中的反斜杠转义问题）
    def _replace_in_math(match):
        content = match.group(1)
        for old, new in trig_map.items():
            pattern = re.compile(r'(?<![a-zA-Z\\])' + old + r'(?![a-zA-Z])')
            content = pattern.sub(lambda m: new, content)
        return f'${content}$'

    text = re.sub(r'\$([^$]+)\$', _replace_in_math, text)
    return text


def _normalize_delimiters(text: str) -> str:
    """(...) → \left( ... \right) 当包含分数、积分等复杂内容时"""
    # 保守策略：只在内容明显需要伸缩时才替换
    # 检测包含 \frac, \sum, \int, 矩阵等情况
    def _should_scale(content: str) -> bool:
        return bool(re.search(r'\\frac|\\sum|\\int|\\\\|\\begin\{', content))

    def _replace_parens(match):
        content = match.group(1)
        if _should_scale(content):
            return r'\left(' + content + r'\right)'
        return '(' + content + ')'

    # 对 (...) 在数学模式中进行替换
    text = re.sub(
        r'(?<!\\)\$([^$]+)\$',
        lambda m: '$' + re.sub(r'\(([^()]*(?:\([^()]*\)[^()]*)*)\)', _replace_parens, m.group(1)) + '$',
        text,
    )
    return text


# Unicode 带圈数字 ①-⑳
_CIRCLED_NUMBERS = {
    '1': '①', '2': '②', '3': '③', '4': '④', '5': '⑤',
    '6': '⑥', '7': '⑦', '8': '⑧', '9': '⑨', '10': '⑩',
    '11': '⑪', '12': '⑫', '13': '⑬', '14': '⑭', '15': '⑮',
    '16': '⑯', '17': '⑰', '18': '⑱', '19': '⑲', '20': '⑳',
}


def _normalize_katex_compat(text: str) -> str:
    """替换 KaTeX 不支持的 LaTeX 命令 + HTML 安全转义"""
    # \textcircled{N} → Unicode 带圈数字 ①-⑳
    for num, circled in _CIRCLED_NUMBERS.items():
        text = text.replace(f'\\textcircled{{{num}}}', circled)
    for num, circled in _CIRCLED_NUMBERS.items():
        text = text.replace(f'\\textcircled{num}', circled)

    # 数学模式内的 < 和 > → \lt 和 \gt（避免被 Streamlit HTML 解析器误食）
    def _fix_lt_gt_in_math(match):
        content = match.group(1)
        content = content.replace('<', r'\lt ')
        content = content.replace('>', r'\gt ')
        # 修复多余的 \lt\lt → \lt \lt
        content = content.replace(r'\lt \lt', r'\lt \lt')
        return '$' + content + '$'

    text = re.sub(r'\$([^$]+)\$', _fix_lt_gt_in_math, text)

    # 同样处理 $$...$$ 块
    def _fix_lt_gt_in_display(match):
        content = match.group(1)
        content = content.replace('<', r'\lt ')
        content = content.replace('>', r'\gt ')
        return '$$' + content + '$$'

    text = re.sub(r'\$\$([^$]+)\$\$', _fix_lt_gt_in_display, text)
    return text


# ═══════════════════════════════════════════════
# R0: 裸数学表达式包裹
# ═══════════════════════════════════════════════

def _wrap_bare_math_expressions(text: str) -> str:
    """
    R0: 安全模式 — 仅包裹明确且独立的不在 $ 内的数学标记。
    不处理 LaTeX 命令序列（太容易断裂），只处理独立标记。
    """
    # 保护已有 $...$ 和 $$...$$ 区域
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00M{len(protected)-1}\x00'
    text = re.sub(r'\$\$[^$]+\$\$', _protect, text)
    text = re.sub(r'\$[^$]+\$', _protect, text)

    # 模式1: 不在 $ 内的 \left(\mathrm{X}\right) → 完整包裹
    text = re.sub(
        r'(?<!\$)(\\left\(\\mathrm\{([A-D])\}\\right\))(?!\$)',
        lambda m: '$' + m.group(1) + '$',
        text,
    )

    # 模式2: (i) 和 (ii) 作为级数标签
    text = re.sub(
        r'(?<!\$)(?<!\w)\(i+\)(?!\w)(?!\$)',
        lambda m: f'${m.group(0)}$',
        text,
    )

    # 模式3: 不在 $ 内的 \underline{\qquad} → 包裹 $
    text = re.sub(
        r'(?<!\$)\\underline\{[^}]*\}(?!\$)',
        lambda m: '$' + m.group(0) + '$',
        text,
    )

    # 恢复保护区域
    for i, block in enumerate(protected):
        text = text.replace(f'\x00M{i}\x00', block)

    return text


# ═══════════════════════════════════════════════
# 新增规则: 去重 + 中文 + 嵌套修复
# ═══════════════════════════════════════════════

def _remove_escaped_newlines(text: str) -> str:
    """
    安全移除字面量 \\n 转义符。
    关键：\\n 只在不是 LaTeX 命令一部分时才替换。
    \\neq, \\ne, \\nearrow 等命令中的 \\n 必须保留。
    """
    # 先保护所有 LaTeX 命令（以 \ 开头后跟字母的）
    _LATEX_CMD = re.compile(r'(\\[a-zA-Z]+)')
    protected_cmds = {}
    counter = [0]
    def _protect_cmd(m):
        cmd = m.group(0)
        key = f'\x00C{counter[0]}\x00'
        protected_cmds[key] = cmd
        counter[0] += 1
        return key
    text = _LATEX_CMD.sub(_protect_cmd, text)

    # 现在安全替换剩余的 \n
    text = text.replace('\\n\\n\\n', '\n\n')
    text = text.replace('\\n\\n', '\n\n')
    text = text.replace('\\n', ' ')

    # 恢复 LaTeX 命令
    for key, cmd in protected_cmds.items():
        text = text.replace(key, cmd)

    return text


def _fix_nested_math(text: str) -> str:
    """修复嵌套数学环境: $$ $x$ $$ → $$ x $$"""
    # $$...$$ 内不应再包含 $...$
    def _fix_display(match):
        content = match.group(1)
        # 移除内部的 $ 标记
        content = content.replace('$', '')
        return '$$' + content + '$$'
    text = re.sub(r'\$\$([^$]*\$[^$]*\$[^$]*)\$\$', _fix_display, text)
    # 也处理 $$...$$ 和 $...$ 相邻的情况
    text = re.sub(r'\$\$\s*\$([^$]+)\$\s*\$\$', r'$$\1$$', text)
    return text


def _fix_chinese_in_math(text: str) -> str:
    """确保中文不在数学模式内: $x=0是极值点$ → $x=0$ 是极值点"""
    def _fix(match):
        content = match.group(1)
        # 如果数学模式内包含中文字符，尝试修复
        if any('一' <= c <= '鿿' for c in content):
            # 在中文前关闭 $，中文后重新打开 $
            fixed = re.sub(r'([一-鿿]+)', r'$\1$', content)
            # 修复可能产生的 $$ 嵌套
            fixed = fixed.replace('$$$', '$')
            return '$' + fixed + '$'
        return match.group(0)
    text = re.sub(r'\$([^$]+)\$', _fix, text)
    return text


def _normalize_operators(text: str) -> str:
    """规范化运算符为长格式（避免转义损坏）"""
    # \ne → \neq （仅当不是 \nearrow 等命令的一部分时）
    text = re.sub(r'(?<!\\)\\ne(?![a-zA-Z])', r'\\neq', text)
    # \le → \leq （仅当不是 \left 等命令的一部分时）
    text = re.sub(r'(?<!\\)\\le(?![a-zA-Z])', r'\\leq', text)
    # \ge → \geq
    text = re.sub(r'(?<!\\)\\ge(?![a-zA-Z])', r'\\geq', text)
    return text


def _dedup_commands(text: str) -> str:
    """去重 + 修复双重转义 + 通用反斜杠清理"""
    # 通用双重转义修复: \\[a-zA-Z]+ → \[a-zA-Z]+
    # 匹配 \\ 后跟字母（LaTeX 命令），替换为单反斜杠
    text = re.sub(r'\\\\([a-zA-Z]+)', r'\\\1', text)

    # \left\left( → \left(
    while '\\left\\left' in text:
        text = text.replace('\\left\\left', '\\left')
    # \right\right) → \right)
    while '\\right\\right' in text:
        text = text.replace('\\right\\right', '\\right')
    # \limits\limits → \limits
    while '\\limits\\limits' in text:
        text = text.replace('\\limits\\limits', '\\limits')
    return text


def _normalize_whitespace(text: str) -> str:
    """空白规范化"""
    # 统一换行
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 连续3+空行 → 2空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # 行尾空格
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    return text


# ═══════════════════════════════════════════════
# 验证
# ═══════════════════════════════════════════════

def is_normalized(text: str) -> bool:
    """检查文本是否已规范化"""
    return normalize_latex_style(text) == text

def validate_normalization(text: str) -> dict:
    """验证规范化结果，返回问题列表"""
    issues = []
    # 检查选项格式
    if re.search(r'(?:^|\n)\s*[A-D][.．、]', text):
        issues.append("包含非规范选项格式 (A./A．/A、)")
    # 检查求和
    if re.search(r'\\sum\s*_\s*\{', text):
        issues.append("包含非规范求和 \\sum_{}")
    # 检查积分
    if re.search(r'\\int\s*_\s*\{', text):
        issues.append("包含非规范积分 \\int_{}")
    # 检查极限
    if re.search(r'\\lim\s*_\s*\{', text):
        issues.append("包含非规范极限 \\lim_{}")
    return {"normalized": len(issues) == 0, "issues": issues}
