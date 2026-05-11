"""
Pass 1: Layout Recovery

纯函数风格，恢复 OCR 崩溃的行结构。

5条规则:
  规则1 — 选项断行恢复: ([ABCD])[.．、] → 前面插入 \n
  规则2 — 题号断行恢复: (\d+)[.．] → 前面插入 \n\n (非小数/分数/年份)
  规则3 — 答案解析边界: 【答案】【解析】【解】【分析】→ 前后强制换行
  规则4 — 数学环境保护: $...$ $$...$$ \[...\] 内部跳过所有换行逻辑
  规则5 — 数学表达跨行合并: \int \sum \lim \frac = + - ( [ { 行尾
                            或 dx dy = + - ) ] } \right 行首 → 合并
"""

import re
from .core import RepairPolicy, RepairTrace, WarningCode

# ═══════════════════════════════════════════════
# 常量定义
# ═══════════════════════════════════════════════

# 选项模式
_OPTION_PATTERN = re.compile(r'([ABCD])[.．、]')

# 题号模式: 数字+点号，排除小数、分数、年份
_QUESTION_NUM_PATTERN = re.compile(
    r'(?<!\d)(?<!\d\.)(?<!\d/)(\d{1,2})[.．](?!\d)',
)

# 答案解析标记
_ANSWER_SOLUTION_MARKERS = [
    re.compile(r'(【答案】)'),
    re.compile(r'(【解析】)'),
    re.compile(r'(【解】)(?!析)'),
    re.compile(r'(【分析】)'),
    re.compile(r'(【详解】)'),
]

# 行尾数学标记（需要与下一行合并）
_MATH_LINE_END = re.compile(
    r'(\\int|\\sum|\\lim|\\frac|\\iint|\\iiint|\\oint|\\prod|'
    r'\\bigcap|\\bigcup|\\bigvee|\\bigwedge|'
    r'[=+\-*/^]|'
    r'[([{＜]|'
    r'\\left[([{.]|'
    r'\\begin\{[^}]*\}|'
    r'\\\\|\\,|\\;|\\:|\\!)\s*$'
)

# 行首数学标记（应与上一行合并）
_MATH_LINE_START = re.compile(
    r'^\s*(dx|dy|dz|dt|dr|ds|du|dv|dw|'
    r'[=+\-*/^]|'
    r'[)\]}>]|'
    r'\\right[)\]}.]|'
    r'\\end\{[^}]*\})'
)

# LaTeX 数学环境
_MATH_ENV_PATTERN = re.compile(
    r'(\$\$.*?\$\$|\$[^$]*?\$|\\\[.*?\\\]|\\\(.*?\\\))',
    re.DOTALL,
)

# 数学环境保护标记
_MATH_PROTECT_PLACEHOLDER = '\x00MATH{0}\x00'


def apply(text: str, policy: RepairPolicy | None = None) -> tuple[str, RepairTrace]:
    """
    Layout Recovery 主入口。

    返回: (recovered_text, trace)
    纯函数：相同输入永远返回相同输出。
    """
    if policy is None:
        policy = RepairPolicy()

    trace = RepairTrace(
        pass_name="layout_recovery",
        input_snippet=text[:200] if text else "",
        char_count_before=len(text),
    )

    if not policy.enable_layout_recovery:
        trace.output_snippet = text[:200]
        trace.char_count_after = len(text)
        return text, trace

    after = text
    mods = []

    # Step 0: 保护数学环境（提取出去，处理完再放回来）
    math_blocks = []
    def _protect(m):
        math_blocks.append(m.group(0))
        return _MATH_PROTECT_PLACEHOLDER.format(len(math_blocks) - 1)

    after = _MATH_ENV_PATTERN.sub(_protect, after)

    # Step 1: 规则3 — 答案/解析边界换行（在选项恢复之前）
    after, mod_r3 = _rule3_answer_boundary(after)
    if mod_r3:
        mods.append(mod_r3)

    # Step 2: 规则1 — 选项断行
    after, mod_r1 = _rule1_option_break(after)
    if mod_r1:
        mods.append(mod_r1)

    # Step 3: 规则2 — 题号断行
    after, mod_r2 = _rule2_question_break(after)
    if mod_r2:
        mods.append(mod_r2)

    # Step 4: 规则5 — 数学表达跨行合并（仅在 enable_math_merge 时）
    if policy.enable_math_merge:
        after, mod_r5 = _rule5_math_merge(after)
        if mod_r5:
            mods.append(mod_r5)

    # Step 5: 恢复数学环境
    for i, block in enumerate(math_blocks):
        after = after.replace(_MATH_PROTECT_PLACEHOLDER.format(i), block, 1)

    trace.modifications = mods
    trace.output_snippet = after[:200] if after else ""
    trace.char_count_after = len(after)

    # 检测行结构崩塌程度
    original_lines = text.count('\n')
    recovered_lines = after.count('\n')
    if recovered_lines < original_lines * 0.3:
        trace.warnings.append(WarningCode.layout_collapsed)

    return after, trace


# ═══════════════════════════════════════════════
# 规则实现
# ═══════════════════════════════════════════════

def _rule1_option_break(text: str) -> tuple[str, str]:
    """规则1: 选项断行恢复"""
    count = 0
    lines = text.split('\n')
    result_lines = []

    for line in lines:
        stripped = line.strip()
        # 在选项字母前插入换行（非行首情况）
        # 找行内所有选项位置
        matches = list(_OPTION_PATTERN.finditer(stripped))
        if len(matches) >= 2:
            # 有多个选项在同一行 → 逐个分割
            parts = []
            last_end = 0
            for m in matches:
                if m.start() > last_end:
                    parts.append(stripped[last_end:m.start()].strip())
                parts.append(stripped[m.start():m.end() - len(m.group(0)) + len(m.group(1))].strip() + m.group(0)[len(m.group(1)):])
                last_end = m.end()
            if last_end < len(stripped):
                parts.append(stripped[last_end:].strip())
            result_lines.extend(p for p in parts if p)
            count += len(matches) - 1
        else:
            result_lines.append(line)

    new_text = '\n'.join(result_lines)
    mod = f"选项断行: 插入{count}处换行" if count > 0 else ""
    return new_text, mod


def _rule2_question_break(text: str) -> tuple[str, str]:
    """规则2: 题号断行恢复"""
    count = 0
    lines = text.split('\n')
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result_lines.append(line)
            continue

        # 检查是否包含题号
        matches = list(_QUESTION_NUM_PATTERN.finditer(stripped))
        if matches:
            # 取第一个题号（通常就是题目编号）
            m = matches[0]
            num_str = m.group(1)
            # 排除年份
            if 1900 <= int(num_str) <= 2100:
                result_lines.append(line)
                continue
            # 如果题号在行首附近，不需要处理
            if m.start() <= 5:
                result_lines.append(line)
                continue
            # 在题号前插入换行
            before = stripped[:m.start()].strip()
            after_q = stripped[m.start():].strip()
            if before:
                result_lines.append(before)
                count += 1
            result_lines.append(after_q)
        else:
            result_lines.append(line)

    new_text = '\n'.join(result_lines)
    mod = f"题号断行: 插入{count}处换行" if count > 0 else ""
    return new_text, mod


def _rule3_answer_boundary(text: str) -> tuple[str, str]:
    """规则3: 答案解析边界强制换行"""
    count = 0
    for marker_re in _ANSWER_SOLUTION_MARKERS:
        # 确保 marker 前后有换行
        def _replace(m):
            nonlocal count
            count += 1
            return '\n' + m.group(0).strip() + '\n'
        text = marker_re.sub(_replace, text)
    # 清理重复换行（保留最多2个）
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    mod = f"答案边界: 修复{count}处" if count > 0 else ""
    return text, mod


def _rule5_math_merge(text: str) -> tuple[str, str]:
    """规则5: 数学表达跨行合并"""
    count = 0
    lines = text.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        if i + 1 < len(lines):
            next_line = lines[i + 1].lstrip()
            # 当前行以数学符号结尾 或 下一行以数学续行符开头
            if (_MATH_LINE_END.search(line) or _MATH_LINE_START.search(next_line)):
                # 合并
                merged = line.rstrip() + next_line
                result.append(merged)
                i += 2
                count += 1
                continue
        result.append(line)
        i += 1

    new_text = '\n'.join(result)
    mod = f"跨行合并: 合并{count}处" if count > 0 else ""
    return new_text, mod
