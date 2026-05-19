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

    # ── 0. 基础清理: 转义换行符、嵌套数学环境、LaTeX 分隔符 ──
    s = _remove_escaped_newlines(s)
    s = _fix_triple_dollars(s)
    s = _convert_latex_delimiters(s)
    s = _fix_nested_math(s)

    # ── 1. 选项标签: (A) / A. / （A） → $\left(\mathrm{A}\right)$ ──
    # 注意：必须在 _wrap_bare_math_expressions 之前执行，因为后者会把 $...$ 替换为占位符
    # 导致选项标签无法正确匹配
    s = _normalize_choice_options(s)

    # ── 0.5. R0: 特定模式 $ 包裹（仅安全模式）──
    s = _wrap_bare_math_expressions(s)

    # ── 2. 求和: \sum_{...}^{...} → \sum\limits_{...}^{...} ──
    s = _normalize_summation(s)

    # ── 3. 积分: \int_{...}^{...} → \int\limits_{...}^{...} ──
    s = _normalize_integral(s)

    # ── 4. 微分: dx → \,\mathrm{d}x ──
    s = _normalize_differential(s)

    # ── 5. 极限: \lim_{...} → \lim\limits_{...} ──
    s = _normalize_limit(s)

    # ── 5.5. 下标间距: a_1\cos → a_{1} \cos ──
    s = _fix_subscript_spacing(s)

    # ── 6. 三角函数: sin → \sin ──
    s = _normalize_trig_functions(s)

    # ── 7. 可伸缩括号: (...) → \left( ... \right) ──
    s = _normalize_delimiters(s)

    # ── 7.5. 修复 \bigl\left 冲突 ──
    s = _fix_big_left_conflict(s)

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
    r"""统一选择题选项格式为 $\left(\mathrm{A}\right)$，每个选项独占一行"""

    # 预处理：将空的数学表达式 $( )$ 或 $( )$ 转换为普通文本
    text = re.sub(r'\$\s*\(\s*\)\$', '( )', text)
    text = re.sub(r'\$\(\s*\)\$', '( )', text)

    # ⭐⭐⭐ 完美！完美！完美！最终完美方案！⭐⭐⭐
    temp = text
    
    # 策略：先处理小问编号 \(数字\)，再处理选项标签
    
    # 1. 首先处理 \(数字\) 格式（LaTeX 原始格式）- 转换为 $(数字)$
    # 必须在行首或换行后，避免匹配数学表达式中的括号
    temp = re.sub(
        r'(?<=\n)\s*\\\((\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\\\)',
        r'\n$(\1)$',
        temp
    )
    temp = re.sub(
        r'^\s*\\\((\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\\\)',
        r'$(\1)$',
        temp
    )
    
    # 2. 然后处理 \qquad 和 \quad 分隔符后跟选项标签
    temp = re.sub(r'\\qquad(\s*)\$?[（(]\s*([A-D])\s*[）)]?\$?', r'\n\1$\\left(\\mathrm{\2}\\right)$', temp)
    temp = re.sub(r'\\quad(\s*)\$?[（(]\s*([A-D])\s*[）)]?\$?', r'\n\1$\\left(\\mathrm{\2}\\right)$', temp)
    
    # 3. 处理单独一行的选项标签
    for letter in 'ABCD':
        temp = re.sub(
            r'(?<![^\n])(\s*)\$?[（(]\s*' + letter + r'\s*[）)]?\$?',
            lambda m: f'{m.group(1)}$\\left(\\mathrm{{{letter}}}\\right)$',
            temp
        )
    
    text = temp
    
    # 然后处理 $(数字)$ 格式 - 必须在行首或换行后
    text = re.sub(
        r'(?<=\n)\s*\$\((\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\)\$',
        r'\n$(\1)$',
        text
    )
    # 处理行首的 $(数字)$ 格式
    text = re.sub(
        r'^\s*\$\((\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\)\$',
        r'$(\1)$',
        text
    )
    
    # 然后处理 (数字) 格式 - 必须在行首或换行后，且前面不能是字母或数字
    text = re.sub(
        r'(?<=\n)\s*[（(]\s*(\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\s*[）)]',
        lambda m: f'\n({m.group(1)})',
        text
    )
    # 处理行首的 (数字) 格式
    text = re.sub(
        r'^\s*[（(]\s*(\d+|[ⅠⅡⅢⅣⅤⅥⅧⅨⅩ]+)\s*[）)]',
        lambda m: f'({m.group(1)})',
        text
    )
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', r'\n\n', text)
    text = text.lstrip('\n')
    
    return text


def _normalize_summation(text: str) -> str:
    r"""\sum_{a}^{b} → \sum\limits_{a}^{b}"""
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
    r"""dx → \,\mathrm{d}x (仅在数学模式内)"""
    if not text:
        return text
    
    # ═══════════════════════════════════════════════
    # 关键保护步骤：防止 \sqrt 被错误转换
    # \sqrt → \s + qrt → 如果 s 后跟空格和变量，会被误认为 ds
    # ═══════════════════════════════════════════════
    
    # 先保护所有已存在的 \命令，避免被错误处理
    # 使用占位符保护 \sin, \sqrt, \s, \d 等命令
    protected = {}
    temp_text = text
    cmd_count = 0
    
    # 匹配所有 \命令形式（\后面跟字母）
    cmd_pattern = re.compile(r'\\[a-zA-Z]+')
    matches = list(cmd_pattern.finditer(temp_text))
    
    # 从后往前处理，避免位置偏移
    for match in reversed(matches):
        full_cmd = match.group(0)  # 如 \sin, \sqrt, \s 等
        placeholder = f'\x00DIFF{cmd_count}\x00'
        temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
        protected[placeholder] = full_cmd
        cmd_count += 1
    
    # 替换数学模式内的裸 dx（只替换前面有空格的，避免误处理 \mathrm{d} 中的 d）
    for var in ['x', 'y', 'z', 't', 'r', 's', 'u', 'v', 'w']:
        # 在 $...$ 内替换
        def _replace_in_math(match):
            content = match.group(1)
            # 只替换前面有空格的 dx（避免误处理 \mathrm{d}x 或其他命令）
            content = content.replace(' d' + var, r' \,\mathrm{d}' + var)
            content = content.replace(' d' + var + ' ', r' \,\mathrm{d}' + var + ' ')
            return '$' + content + '$'
        temp_text = re.sub(r'\$([^$]+)\$', _replace_in_math, temp_text)
    
    # 恢复被保护的命令
    for placeholder, original in protected.items():
        temp_text = temp_text.replace(placeholder, original)
    
    return temp_text


def _normalize_limit(text: str) -> str:
    """\lim_{a \to b} → \lim\limits_{a \to b}"""
    text = text.replace('\\lim_{', '\\lim\\limits_{')
    text = text.replace('\\lim _{', '\\lim\\limits_{')
    return text


def _fix_subscript_spacing(text: str) -> str:
    """Fix missing space after numeric subscripts followed by backslash commands.
    
    Example: a_1\cos → a_{1} \cos
    This prevents a_1\cos from being parsed as a_{1\cos}.
    """
    # 跳过此函数，因为它会破坏长数学表达式
    # 在需要时手动添加空格
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
            # 匹配没有反斜杠前缀的函数名
            # 负向预查确保前面不是字母或反斜杠，后面不是字母
            pattern = re.compile(r'(?<![a-zA-Z\\])' + old + r'(?![a-zA-Z])')
            content = pattern.sub(lambda m: new, content)
        return f'${content}$'

    text = re.sub(r'\$([^$]+)\$', _replace_in_math, text)
    return text


def _fix_big_left_conflict(text: str) -> str:
    r"""修复 \bigl\left 和 \bigr\right 冲突。

    LLM 有时会错误地同时输出固定尺寸和自适应尺寸命令:
      \bigl\left( ... \bigr\right)  →  \left( ... \right)
      \left\bigl( ... \right\bigr)  →  \left( ... \right)

    \big* 系列和 \left/\right 是互斥的，同时出现会导致 KaTeX 渲染失败。
    策略：保留 \left/\right（自适应），移除前缀/后缀的 \big*。
    """
    # \big* 变体 + \left  →  \left
    text = re.sub(r'\\big[lr]?\\left', r'\\left', text)
    # \big* 变体 + \right  →  \right
    text = re.sub(r'\\big[lr]?\\right', r'\\right', text)
    # \left + \big* 变体  →  \left
    text = re.sub(r'\\left\\big[lr]?', r'\\left', text)
    # \right + \big* 变体  →  \right
    text = re.sub(r'\\right\\big[lr]?', r'\\right', text)

    # 大写版本: \Bigl, \biggl, \Biggl 等
    text = re.sub(r'\\Big[lr]?\\left', r'\\left', text)
    text = re.sub(r'\\Big[lr]?\\right', r'\\right', text)
    text = re.sub(r'\\bigg[lr]?\\left', r'\\left', text)
    text = re.sub(r'\\bigg[lr]?\\right', r'\\right', text)
    text = re.sub(r'\\Bigg[lr]?\\left', r'\\left', text)
    text = re.sub(r'\\Bigg[lr]?\\right', r'\\right', text)

    # 反向: \left\Bigl 等
    text = re.sub(r'\\left\\Big[lr]?', r'\\left', text)
    text = re.sub(r'\\right\\Big[lr]?', r'\\right', text)
    text = re.sub(r'\\left\\bigg[lr]?', r'\\left', text)
    text = re.sub(r'\\right\\bigg[lr]?', r'\\right', text)
    text = re.sub(r'\\left\\Bigg[lr]?', r'\\left', text)
    text = re.sub(r'\\right\\Bigg[lr]?', r'\\right', text)

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

    # 定义通用的 lt/gt 修复函数
    def _fix_lt_gt(content):
        # 处理双重转义的情况：&amp;lt; → &lt; → <
        content = content.replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')
        content = content.replace('&amp;lt', '&lt;').replace('&amp;gt', '&gt;')
        # 处理单重转义的情况：&lt; → <
        content = content.replace('&lt;', '<').replace('&gt;', '>')
        content = content.replace('&lt', '<').replace('&gt', '>')
        # 然后转换为 LaTeX 命令
        content = content.replace('<', r'\lt ')
        content = content.replace('>', r'\gt ')
        # 修复多余的 \lt\lt → \lt \lt
        content = content.replace(r'\lt\lt', r'\lt \lt')
        content = content.replace(r'\gt\gt', r'\gt \gt')
        return content

    # 数学模式内的 < 和 > → \lt 和 \gt（避免被 Streamlit HTML 解析器误食）
    def _fix_lt_gt_in_math(match):
        content = match.group(1)
        content = _fix_lt_gt(content)
        return '$' + content + '$'

    text = re.sub(r'\$([^$]+)\$', _fix_lt_gt_in_math, text)

    # 同样处理 $$...$$ 块
    def _fix_lt_gt_in_display(match):
        content = match.group(1)
        content = _fix_lt_gt(content)
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
    # 保护已有 $...$、$$...$$ 和 \(...\)、\[...\] 区域
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00M{len(protected)-1}\x00'
    text = re.sub(r'\$\$[^$]+\$\$', _protect, text)
    text = re.sub(r'\$[^$]+\$', _protect, text)
    # 保护 \(...\) 和 \[...\] 格式
    text = re.sub(r'\\\[.+?\\\]', _protect, text, flags=re.DOTALL)
    text = re.sub(r'\\\(.+?\\\)', _protect, text, flags=re.DOTALL)

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

    # 模式4: 不在 $ 内的裸 LaTeX 运算符 → 包裹 $
    _bs = chr(92)  # backslash char
    # Longer commands first to prevent partial matches (e.g. \infty before \in)
    _bare_ops = [
        'Leftrightarrow', 'longrightarrow', 'Leftarrow', 'Longrightarrow',
        'rightarrow', 'leftarrow', 'mapsto', 'Rightarrow',
        'subseteq', 'subset', 'notin',
        'emptyset', 'approx', 'equiv',
        'partial', 'nabla', 'infty',
        'times', 'cdot', 'div',
        'forall', 'exists', 'setminus',
        'neq', 'ge', 'le', 'gt', 'lt', 'pm', 'mp',
        'to', 'in', 'cup', 'cap', 'sim',
    ]
    for _op in _bare_ops:
        _cmd = _bs + _op
        # Use \b for word boundary to avoid partial matches
        _safe_cmd = re.escape(_cmd)
        text = re.sub(
            rf'(?<!\$){_safe_cmd}\b(?!\$)',
            lambda m, c=_cmd: '$' + c + '$',
            text,
        )

    # 模式4.5: 不在 $ 内的下标表达式 → 包裹 $
    # 匹配: a_1, b_1, x_0, a_{1}, x_{yz} 等
    # 先匹配带大括号的下标: a_{123}
    text = re.sub(
        r'(?<!\$)(\b[a-zA-Z]_\{[^{}]+\}\b)(?!\$)',
        lambda m: '$' + m.group(1) + '$',
        text,
    )
    # 再匹配简单下标: a_1
    text = re.sub(
        r'(?<!\$)(\b[a-zA-Z]_\d+\b)(?!\$)',
        lambda m: '$' + m.group(1) + '$',
        text,
    )

    # 模式5: 不在 $ 内的三角函数表达式 → 包裹 $
    # 匹配模式: 数字/变量 + sin/cos/tan 等 + 变量
    _trig_funcs = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc']
    for _func in _trig_funcs:
        # 匹配: 数字紧跟三角函数（如 2sin x, 2πsin x）
        text = re.sub(
            rf'(?<!\$)(\b[\dπ]+(?:\.\d+)?{_func}\s*[a-zA-Z])',
            lambda m: '$' + m.group(1) + '$',
            text,
        )
        # 匹配: 数字 sin x, x sin x, 2π sin x 等模式
        text = re.sub(
            rf'(?<!\$)(\b[\dπ]+(?:\.\d+)?\s*{_func}\s*[a-zA-Z])',
            lambda m: '$' + m.group(1) + '$',
            text,
        )
        # 匹配: 变量 sin x 模式
        text = re.sub(
            rf'(?<!\$)(\b[a-zA-Z]\s*{_func}\s*[a-zA-Z])',
            lambda m: '$' + m.group(1) + '$',
            text,
        )
        # 匹配: 下标变量紧跟三角函数模式，如 a_1cos x
        text = re.sub(
            rf'(?<!\$)(\b[a-zA-Z]_\d+\s*{_func}\s*[a-zA-Z])',
            lambda m: '$' + m.group(1) + '$',
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
        if not any('一' <= c <= '鿿' for c in content):
            return match.group(0)
        # 仅处理含 LaTeX 命令的长数学块，避免拆分短中文块如 $在展开式中$
        has_latex = '\\' in content or '^' in content or '_' in content
        if not has_latex or len(content) < 10:
            return match.group(0)
        # 将内容拆分为: 纯数学段 + 纯中文段
        segments = re.split(r'([一-鿿＀-￯]+(?:[，。、；：！？]|[一-鿿])*)', content)
        segments = [s for s in segments if s]
        if not segments:
            return match.group(0)
        parts = []
        for seg in segments:
            is_chinese = any('一' <= c <= '鿿' for c in seg)
            if is_chinese:
                parts.append(seg)  # 中文作为纯文本
            else:
                parts.append(f'${seg.strip()}$')  # 数学保留 $ 包裹
        return ''.join(parts)
    text = re.sub(r'\$([^$]+)\$', _fix, text)
    return text


def _fix_triple_dollars(text: str) -> str:
    """修复 $$$ (三重$) 分隔符。
    $$$ 通常出现在 display math 关闭后紧跟内容时:
      $$内容$$$后续 → $$内容$$ 后续
    策略: 非$字符后的 $$$ → $$ (确保前面的 display math 正确关闭)
    """
    if '$$$' not in text:
        return text
    s = re.sub(r'(?<!\$)\${3}', '$$', text)
    return s


def _convert_latex_delimiters(text: str) -> str:
    """将标准 LaTeX 分隔符转换为 KaTeX 兼容格式。

    \\[...\\] → $$...$$ (display math)
    \\(...\\) → $...$ (inline math)
    """
    # \[...\] → $$...$$  (display math)
    text = re.sub(r'\\\[(.+?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # \(...\) → $...$  (inline math)
    # 但要排除列表编号如 \(1\), \(2\), \(Ⅰ\), \(Ⅱ\) 等
    # 这些应该保持原样，不应该转换为数学表达式
    def _convert_if_not_list_number(match):
        content = match.group(1)
        # 检查是否是列表编号（纯数字或罗马数字）
        if re.match(r'^\s*(\d+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\s*$', content):
            # 是列表编号，保持原样
            return match.group(0)
        # 是真正的数学表达式，转换为 $...$
        return f'${content}$'
    
    text = re.sub(r'\\\((.+?)\\\)', _convert_if_not_list_number, text, flags=re.DOTALL)
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
