"""
Pass 0: Safe Normalize

纯函数风格，无副作用，完全确定性。
负责 Unicode 归一化、编码修复、空白标准化。
不改变数学语义。
"""

import re
import unicodedata
from .core import RepairPolicy, RepairTrace, WarningCode


# ═══════════════════════════════════════════════
# 字符映射表
# ═══════════════════════════════════════════════

# 全角 → 半角
_FULLWIDTH_TO_HALFWIDTH = str.maketrans({
    chr(c): chr(c - 0xFEE0)
    for c in range(0xFF01, 0xFF5F)
    if c not in (0xFF0D,)  # 保留全角破折号
})

# 中文标点 → 英文标点（仅在数学上下文中）
_CJK_PUNCT_TO_ASCII = {
    '，': ',',  '。': '.',  '；': ';',  '：': ':',
    '？': '?',  '！': '!',  '（': '(',  '）': ')',
    '【': '[',  '】': ']',  '《': '<',  '》': '>',
    '＂': '"',  '＇': "'",
}

# 常见OCR异体字/混淆字
_OCR_CHAR_FIXES = {
    # 空格/控制字符
    ' ': ' ',   # NBSP → 普通空格
    '​': '',    # 零宽空格 → 删除
    '‌': '',    # 零宽非连接符
    '‍': '',    # 零宽连接符
    '﻿': '',    # BOM
    ' ': '\n',  # 行分隔符
    ' ': '\n\n',# 段分隔符
    '\r': '\n',      # CR → LF
    # 常见OCR符号混淆
    '‘': "'",   # 左单引号
    '’': "'",   # 右单引号
    '“': '"',   # 左双引号
    '”': '"',   # 右双引号
    '‐': '-',        # 连字符 → 减号
    '‑': '-',        # 不间断连字符
    '‒': '-',
    '–': '-',        # en-dash
    '—': '-',        # em-dash
    '―': '-',        # horizontal bar
    '−': '-',        # 减号（数学用）
}


def apply(text: str, policy: RepairPolicy | None = None) -> tuple[str, RepairTrace]:
    """
    Safe Normalize 主入口。

    返回: (normalized_text, trace)
    纯函数：相同输入永远返回相同输出。
    """
    if policy is None:
        policy = RepairPolicy()

    trace = RepairTrace(
        pass_name="safe_normalize",
        input_snippet=text[:200] if text else "",
        char_count_before=len(text),
    )

    after = text

    # Step 1: Unicode NFC 归一化
    after = unicodedata.normalize('NFC', after)

    # Step 2: 控制字符清理
    for old, new in _OCR_CHAR_FIXES.items():
        if old in after:
            after = after.replace(old, new)

    # Step 3: 全角 ASCII → 半角（保留全角破折号和中文特有标点）
    after = _safe_fullwidth_to_halfwidth(after)

    # Step 4: 编码混用检测
    if _detect_encoding_mix(after):
        trace.warnings.append(WarningCode.encoding_mixed)

    # Step 5: 空白标准化
    after = _normalize_whitespace(after)

    # Step 6: 中文标点上下文修复
    after = _fix_cjk_punctuation_context(after)

    trace.output_snippet = after[:200] if after else ""
    trace.char_count_after = len(after)

    if after != text:
        trace.modifications.append(
            f"规范化: {trace.char_count_before - trace.char_count_after:+d}字符"
        )

    return after, trace


def _safe_fullwidth_to_halfwidth(text: str) -> str:
    """安全的全角→半角转换，保护数学语义"""
    # 不要转换：全角字母数字（在数学模式中）、全角括号（在【】标记中）
    # 只转换全角标点符号
    result = []
    math_depth = 0  # 追踪 $ 深度
    for ch in text:
        if ch == '$':
            math_depth ^= 1  # toggle

        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            if code == 0xFF0D:  # 全角破折号 → 保留
                result.append(ch)
            elif math_depth:
                # 数学模式内：转换全角字母数字
                half = chr(code - 0xFEE0)
                result.append(half)
            elif ch in '（）【】':
                # 中文上下文中保留全角括号
                result.append(ch)
            elif ch in '，。；：？！':
                # 中文标点保留
                result.append(ch)
            else:
                result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return ''.join(result)


def _detect_encoding_mix(text: str) -> bool:
    """检测 GBK/UTF-8 编码混用痕迹"""
    # 检查是否存在 UTF-8 BOM 残留 + GBK 乱码特征
    has_bom = text.startswith('﻿')
    has_garbled = bool(re.search(r'[\x80-\x9F]{2,}', text))
    return has_bom or has_garbled


def _normalize_whitespace(text: str) -> str:
    """空白标准化"""
    # 统一换行为 \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 连续3+空行 → 2空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # 行内连续空格 → 单空格
    lines = []
    for line in text.split('\n'):
        lines.append(re.sub(r'[ \t]+', ' ', line).strip(' '))
    # 去掉行尾空格（不改变换行数量）
    return '\n'.join(lines)


def _fix_cjk_punctuation_context(text: str) -> str:
    """
    修复中文标点在数学上下文中的使用。
    只在数学模式外才将中文标点保留为全角。
    """
    # 【答案】 和 【解析】 是结构化标记，必须保留全角
    # 不需要修改——_safe_fullwidth_to_halfwidth 已经保护了它们
    return text
