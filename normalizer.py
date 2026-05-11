"""
Normalizer — LaTeX AST 结构修复引擎

两层架构:
  Layer 1 (Prompt): 语义结构化 — LLM 负责
  Layer 2 (Normalizer): token 级修复 — 确定性引擎负责

处理顺序（重要）:
1. 中文标点转英文
2. display math 内 \int/\sum → \limits (context-aware)
3. bare begin/end → $$ 包裹 (M101/M102)
4. matrix 内单反斜杠修复 (M105)
5. display math 内 stray $ 移除 (M104)
6. display math 后标点/中文处理 (M103)
7. 选择题 matrix 分离 (M106)
8. 子题间距修复
9. 反斜杠归一化
10. 题号强制注入

原则:
- Prompt 层: 数学语义 — LLM 负责
- Normalizer 层: token 修复 + LaTeX 规范化 — 确定性引擎负责
══════════════════════════════════════════════════
 双层架构:
   Layer 1 — Raw LaTeX (只读, 原始源码永久保存)
   Layer 2 — Display LaTeX (Normalizer 产出, 允许版式美化)
══════════════════════════════════════════════════

 Normalizer 允许 (Deterministic Formatting):
   ✅ 空格规范化 / 括号规范化 / 标点转英文
   ✅ 数学环境闭合 / 题号强制注入
   ✅ display ∫→∫limits / ≠→ne
   ✅ 子题间距 / display math 边界
   ✅ OCR碎片修复

 Normalizer 禁止 (Semantic Changes):
   ❌ 1-e^{-x^2/(2θ^2)} → e^{-x^2/2θ^2} (数学改写)
   ❌ 删除条件 / 改变题意
   ❌ pmatrix→diag / frac12→0.5 (等价压缩)
   ❌ array→cases (源码重写)
   ❌ 长表达式摘要/压缩/优化

 设计原则:
   - AI(Prompt) 只负责: 解题、批改、分析
   - Normalizer 只负责: 确定性 LaTeX 版式规范化
   - 两者永不交叉
"""
import re

ENVIRONMENTS = [
    "pmatrix", "bmatrix", "matrix", "vmatrix",
    "cases", "aligned", "array",
]


# ═══════════════════════════════════════════════
# ① 中文标点转英文
# ═══════════════════════════════════════════════

def normalize_punctuation(text: str) -> str:
    mapping = {"，": ",", "；": ";", "。": ".", "：": ":",
               "（": "(", "）": ")", "【": "[", "】": "]"}
    for zh, en in mapping.items():
        text = text.replace(zh, en)
    return text


# ═══════════════════════════════════════════════
# ② Context-aware limits: display math → \int\limits, inline → 保持
# ═══════════════════════════════════════════════

def normalize_limits(text: str) -> str:
    """
    Context-aware: 仅在 display math $$...$$ 内给 \int/\sum/\prod 加 \limits.
    行内 $...$ 保持原样（避免破坏行高和排版）.
    """
    # Find all display math blocks
    def _add_limits_in_block(match):
        inner = match.group(1)
        for cmd in ['int', 'sum', 'prod']:
            # \int → \int\limits (only if not already \int\limits or \int_{}^{})
            inner = re.sub(
                rf'\\{cmd}(?!\s*\\limits|\s*_)',
                rf'\\{cmd}\\limits ',
                inner
            )
        return '$$\n' + inner.strip() + '\n$$'

    text = re.sub(r'\$\$(.+?)\$\$', _add_limits_in_block, text, flags=re.S)
    return text


# ═══════════════════════════════════════════════
# ③ M101/M102: bare \begin{env} → $$ 包裹
# ═══════════════════════════════════════════════

def wrap_bare_environments(text: str) -> str:
    """
    M101: 检测 \begin{env} 不在 math mode → 自动补 $$
    M102: matrix/cases 强制 block 化
    """
    for env in ENVIRONMENTS:
        # Pattern: \begin{env} NOT inside $...$ or $$...$$
        # We find \begin{env} and check if it's inside a math delimiter
        pattern = rf"\\begin{{{env}}}"
        result = []
        last_end = 0
        for m in re.finditer(pattern, text):
            start = m.start()
            # Check if inside math mode: count $ before this position
            prefix = text[:start]
            # Count $$ blocks before this position
            display_opens = len(re.findall(r'\$\$', prefix))
            # If odd number of $$, we're inside display math — OK
            # If even, check inline $
            stripped = re.sub(r'\$\$', '', prefix)
            inline_dollars = stripped.count('$')
            in_math = (display_opens % 2 == 1) or (inline_dollars % 2 == 1)
            if not in_math:
                # Not in math mode — wrap in $$
                # Find matching \end{env}
                end_tag = rf"\\end{{{env}}}"
                end_m = re.search(end_tag, text[start:])
                if end_m:
                    end_pos = start + end_m.end()
                    # Add text before, then wrapped block
                    result.append(text[last_end:start])
                    inner = text[start:end_pos]
                    result.append(f'$$\n{inner}\n$$')
                    last_end = end_pos
        if result:
            # Append remaining text
            result.append(text[last_end:])
            text = ''.join(result)
    return text


# ═══════════════════════════════════════════════
# ③ M105: matrix 内单反斜杠 → \\
# ═══════════════════════════════════════════════

def fix_single_backslash_in_env(text: str) -> str:
    """
    M105: 在 matrix/cases 内部，孤立的 \ 后跟数字/字母 → \\
    模式: } 1 \ 2 \ 3 {  → } 1 \\ 2 \\ 3 {
    """
    for env in ENVIRONMENTS:
        pattern = rf"(\\begin{{{env}}})(.+?)(\\end{{{env}}})"
        def repl(m):
            content = m.group(2)
            # Fix single \ between digits or letters inside matrix
            # Pattern: digit \ digit → digit \\ digit
            content = re.sub(r'(\d)\s*\\(\s*\d)', r'\1 \\\\ \2', content)
            content = re.sub(r'([a-zA-Z])\s*\\(\s*[a-zA-Z])', r'\1 \\\\ \2', content)
            return m.group(1) + content + m.group(3)
        text = re.sub(pattern, repl, text, flags=re.S)
    return text


# ═══════════════════════════════════════════════
# ④ M104: display math 内 stray $ 移除
# ═══════════════════════════════════════════════

def fix_display_stray_dollar(text: str) -> str:
    """
    M104/M109/M110: display math 内禁止 inline math
    $$...$...$$ → 移除内部的 stray $
    维护 math mode stack：display math 内不补 $
    """
    def repl(m):
        inner = m.group(1)
        inner = inner.replace('$', '')
        return '$$\n' + inner.strip() + '\n$$'
    text = re.sub(r'\$\$(.+?)\$\$', repl, text, flags=re.S)
    return text


# ═══════════════════════════════════════════════
# ⑤ M103: display math 后中文/标点处理
# ═══════════════════════════════════════════════

def repair_display_math(text: str) -> str:
    # DM-P2: $$...$$. → $$...\n.$$ (trailing punct inside)
    text = re.sub(r'\$\$([^$]+?)\$\$([.,;:，。；：])', r'$$\1\n\2$$', text)
    # DM-P1: $$...$$令 → break before Chinese
    text = re.sub(r'\$\$([^$]+?)\$\$([一-鿿])', r'$$\1\n$$\n\n\2', text)
    # $$ (A) → $ (A)
    text = re.sub(r"\$\$\s*\(", r"$ (", text)
    return text


# ═══════════════════════════════════════════════
# ⑥ M106: 选择题 matrix 分离
# ═══════════════════════════════════════════════

def split_choice_matrix(text: str) -> str:
    """
    M106: $ (A) $ content\begin{pmatrix}... → $ (A) $\n\n$$\ncontent\begin{pmatrix}...\n$$
    Detects choice option label followed by inline matrix and splits them.
    """
    for env in ENVIRONMENTS:
        pattern = rf'(\$ \([A-D]\) \$)\s*(.+?\\begin{{{env}}}.*?\\end{{{env}}}.*?)(?=\n|$)'
        def repl(m):
            label = m.group(1)
            content = m.group(2).strip()
            return f'{label}\n\n$$\n{content}\n$$'
        text = re.sub(pattern, repl, text, flags=re.S)
    return text


# ═══════════════════════════════════════════════
# ⑦ 子题间距
# ═══════════════════════════════════════════════

def repair_subquestions(text: str) -> str:
    text = re.sub(r"([^\n])\n*(\$\(\d+\)\$)", r"\1\n\n\2", text)
    text = re.sub(r"(\$\(\d+\)\$[^\n]*)\n(\$\(\d+\)\$)", r"\1\n\n\2", text)
    return text


# ═══════════════════════════════════════════════
# ⑧ 反斜杠归一化
# ═══════════════════════════════════════════════

def collapse_double_backslash(text: str) -> str:
    return re.sub(r'\\\\([a-zA-Z])', r'\\\1', text)


def normalize_neq(text: str) -> str:
    return text.replace(r'\neq', r'\ne')


# ═══════════════════════════════════════════════
# ⑨ 题号强制注入
# ═══════════════════════════════════════════════

def normalize_question_number(text: str, question_number: int = 1) -> str:
    if re.match(r'\$\d{1,2}\.\$', text):
        return text
    return f'${question_number}.$ ' + text


# ═══════════════════════════════════════════════
# ⑩ 平衡检查
# ═══════════════════════════════════════════════

def check_math_balance(text: str):
    stripped = text.replace("$$", "")
    if stripped.count("$") % 2 != 0:
        print("WARNING: inline math may be unclosed")
    for env in ENVIRONMENTS:
        b = len(re.findall(rf"\\begin{{{env}}}", text))
        e = len(re.findall(rf"\\end{{{env}}}", text))
        if b != e:
            print(f"WARNING: {env} unclosed ({b} begin, {e} end)")


# ═══════════════════════════════════════════════
# 总入口
# ═══════════════════════════════════════════════

def fix_broken_dollar_placeholder(text: str) -> str:
    """=$$( )$ → = $( )$  and similar broken answer-placeholder patterns."""
    text = text.replace('=$$( )$', '= $( )$')
    text = text.replace('=$$$( )$', '= $( )$')
    text = text.replace('$$$( )$', '$( )$')
    return text


def fix_option_missing_dollar(text: str) -> str:
    """$(A)$ content$ → $(A)$ $content$ (missing opening $ before math)"""
    import re
    for label in ['A', 'B', 'C', 'D']:
        text = re.sub(
            rf'(\$\({label}\)\$) ([\[\(\d\-\+].*?)\$',
            r'\1 $\2$',
            text
        )
    return text


def normalize(text: str, question_number: int = 1) -> str:
    text = normalize_punctuation(text)
    text = normalize_limits(text)            # Context-aware \int → \int\limits
    text = fix_broken_dollar_placeholder(text)
    text = fix_option_missing_dollar(text)
    text = wrap_bare_environments(text)      # M101/M102
    text = fix_single_backslash_in_env(text) # M105
    text = fix_display_stray_dollar(text)    # M104
    text = repair_display_math(text)         # M103
    text = split_choice_matrix(text)         # M106
    text = repair_subquestions(text)
    text = collapse_double_backslash(text)
    text = normalize_neq(text)
    text = normalize_question_number(text, question_number)
    check_math_balance(text)
    return text
