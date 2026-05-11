"""
Pass 3: Validator

纯函数风格。验证修复后文本的质量和保真度。

三项检查:
  A. 结构合法性 — LaTeX配对、中文占比、异常字符率
  B. 保真度评分 — 长度漂移、数学对象漂移、数字漂移
  C. 数学合法性 — 栈机检查括号配对 + command arity

输出:
  - ValidationResult（结构检查结果）
  - FidelityScore（保真度结果）
  - resolved_warnings: 修复前有、修复后消失的警告
  - introduced_warnings: 修复前没有、修复后新出现的警告
"""

import re
from .core import (
    RepairPolicy, RepairTrace, WarningCode,
    ValidationResult, FidelityScore,
)
from .utils import count_math_objects


def validate(text: str, pre_warnings: list[WarningCode] | None = None,
             policy: RepairPolicy | None = None) -> tuple[ValidationResult, RepairTrace]:
    """
    主入口：对文本进行完整验证。

    返回: (ValidationResult, trace)
    """
    if policy is None:
        policy = RepairPolicy()
    if pre_warnings is None:
        pre_warnings = []

    trace = RepairTrace(
        pass_name="validator",
        input_snippet=text[:200] if text else "",
        char_count_before=len(text),
    )

    result = ValidationResult()
    new_warnings: list[WarningCode] = []

    # ── A: 结构合法性 ──
    result.quality_score = _compute_quality_score(text)

    # LaTeX 括号配对
    math_issues = _check_math_brackets(text)
    if math_issues:
        new_warnings.append(WarningCode.math_bracket_unbalanced)
        result.details["unmatched_braces"] = math_issues.get("braces", 0)
        result.details["unmatched_dollars"] = math_issues.get("dollars", 0)
        result.math_valid = False
    else:
        result.math_valid = True

    # 中文占比
    chinese_ratio = _compute_chinese_ratio(text)
    result.details["chinese_ratio"] = round(chinese_ratio, 3)

    # OCR 异常字符率
    garbage_ratio = _compute_garbage_ratio(text)
    result.details["ocr_garbage_ratio"] = round(garbage_ratio, 4)
    if garbage_ratio > 0.10:
        new_warnings.append(WarningCode.ocr_unrecoverable)
        result.quality_score *= 0.7

    # 题号检测
    question_nums = _detect_question_numbers(text)
    result.question_count = len(question_nums)
    gaps = _find_question_gaps(question_nums)
    if gaps:
        new_warnings.append(WarningCode.question_gap)
        result.details["question_gaps"] = gaps

    # 答案检测
    answer_count = len(re.findall(r'【答案】', text))
    result.answer_count = answer_count
    if answer_count == 0 and result.question_count > 3:
        new_warnings.append(WarningCode.answer_missing)

    # 选项检测
    result.option_count = len(re.findall(r'\b([ABCD])[.．、]\s', text))
    option_set = set(re.findall(r'\b([ABCD])[.．、]\s', text))
    if {'A', 'B', 'D'} == option_set or {'A', 'C', 'D'} == option_set:
        new_warnings.append(WarningCode.missing_option)
        result.details["option_gaps"] = list({'A', 'B', 'C', 'D'} - option_set)

    # 数学语法断裂检测
    broken_count = _count_broken_math(text)
    if broken_count > 0:
        new_warnings.append(WarningCode.math_syntax_broken)
        result.details["broken_math"] = broken_count

    # ── 警告分类 ──
    pre_set = set(pre_warnings)
    post_set = set(new_warnings)
    result.warnings = new_warnings
    trace.warnings = new_warnings

    # ── manual_review 判定 ──
    if (garbage_ratio > policy.max_unrecoverable_ratio or
        not result.math_valid or
        result.quality_score < 0.35):
        result.needs_manual_review = True
        if garbage_ratio > 0.3:
            result.failure_mode = "ocr_unrecoverable: 乱码率过高"
        elif not result.math_valid:
            result.failure_mode = "math_structure: LaTeX结构损坏"
        else:
            result.failure_mode = "low_quality: 综合质量过低"

    trace.modifications = [
        f"质量评分: {result.quality_score:.2f}",
        f"题号: {result.question_count}",
        f"答案: {answer_count}",
    ]

    return result, trace


def compute_fidelity(original: str, repaired: str) -> FidelityScore:
    """
    计算保真度评分。
    比较修复前后的信息量变化。
    """
    score = FidelityScore()

    if not original:
        score.status = "manual_review"
        return score

    # 长度比
    score.length_ratio = len(repaired) / max(len(original), 1)

    # 数学对象漂移
    orig_math = count_math_objects(original)
    rep_math = count_math_objects(repaired)
    score.math_object_drift = (
        abs(orig_math - rep_math) / max(orig_math, 1)
        if orig_math > 0 else 0.0
    )

    # 数字漂移
    orig_nums = len(re.findall(r'\d+', original))
    rep_nums = len(re.findall(r'\d+', repaired))
    score.numeric_drift = (
        abs(orig_nums - rep_nums) / max(orig_nums, 1)
        if orig_nums > 0 else 0.0
    )

    # 题号漂移
    orig_q = len(_detect_question_numbers(original))
    rep_q = len(_detect_question_numbers(repaired))
    score.question_count_drift = rep_q - orig_q

    # 状态判定
    if (score.math_object_drift > 0.20 or
        abs(score.question_count_drift) > 2):
        score.status = "manual_review"
    elif (score.length_ratio < 0.50 or score.length_ratio > 1.50):
        score.status = "manual_review"
    elif (score.math_object_drift > 0.10 or
          score.numeric_drift > 0.15):
        score.status = "warning"
    else:
        score.status = "ok"

    return score


def classify_warnings(pre_warnings: list[WarningCode],
                      post_warnings: list[WarningCode]) -> tuple[list[WarningCode], list[WarningCode]]:
    """分类警告: resolved vs introduced"""
    pre_set = set(pre_warnings)
    post_set = set(post_warnings)
    resolved = list(pre_set - post_set)
    introduced = list(post_set - pre_set)
    return resolved, introduced


# ═══════════════════════════════════════════════
# 内部辅助函数
# ═══════════════════════════════════════════════

def _compute_quality_score(text: str) -> float:
    """综合质量评分 0-1"""
    if not text:
        return 0.0
    score = 1.0

    # 空行比例（正常 5-20%）
    lines = text.split('\n')
    empty_ratio = sum(1 for l in lines if not l.strip()) / max(len(lines), 1)
    if empty_ratio > 0.40:
        score *= 0.8

    # 异常字符比例
    garbage_ratio = _compute_garbage_ratio(text)
    if garbage_ratio > 0.05:
        score *= (1.0 - garbage_ratio * 2)

    # 行平均长度（正常 20-80 字符）
    non_empty = [l for l in lines if l.strip()]
    if non_empty:
        avg_len = sum(len(l) for l in non_empty) / len(non_empty)
        if avg_len < 10:
            score *= 0.7
        elif avg_len > 200:
            score *= 0.8

    return max(0.0, min(1.0, score))


def _compute_chinese_ratio(text: str) -> float:
    """汉字占比"""
    if not text:
        return 0.0
    chinese = sum(1 for ch in text if '一' <= ch <= '鿿')
    return chinese / len(text)


def _compute_garbage_ratio(text: str) -> float:
    """计算异常字符比例"""
    if not text:
        return 0.0
    # 统计非标准字符
    garbage = 0
    for ch in text:
        if ch in '\n\r\t ':
            continue
        if not (ch.isascii() or
                '一' <= ch <= '鿿' or
                '　' <= ch <= '〿' or
                '＀' <= ch <= '￯' or
                ch in '【】（）《》、，。；：？！“”''—…～·'):
            garbage += 1
    return garbage / max(len(text), 1)


def _check_math_brackets(text: str) -> dict:
    """检查数学括号配对"""
    issues = {}

    # 全文本花括号配对（LaTeX命令的{}也计入）
    brace_depth = 0
    i = 0
    while i < len(text):
        # 跳过转义
        if text[i] == '\\' and i + 1 < len(text):
            # LaTeX 命令 — 这些后面跟的 { } 是合法的数学括号
            cmd_end = i + 1
            while cmd_end < len(text) and text[cmd_end].isalpha():
                cmd_end += 1
            i = cmd_end
            continue
        if text[i] == '{':
            brace_depth += 1
        elif text[i] == '}':
            brace_depth -= 1
        if brace_depth < 0:
            brace_depth = 0
            issues.setdefault("unmatched_close_braces", 0)
            issues["unmatched_close_braces"] += 1
        i += 1

    if brace_depth != 0:
        issues["braces"] = brace_depth

    # $ 配对（排除 $$）
    text_for_dollars = text
    # 先移除所有 $$
    dollar_pairs = text_for_dollars.count('$$')
    if dollar_pairs % 2 != 0:
        issues["double_dollars"] = dollar_pairs % 2
    # 移除 $$ 后统计 单$
    text_no_doubles = text_for_dollars.replace('$$', '')
    single_dollars = text_no_doubles.count('$')
    if single_dollars % 2 != 0:
        issues["dollars"] = single_dollars % 2

    return issues


def _detect_question_numbers(text: str) -> list[int]:
    """检测文本中的题号"""
    patterns = [
        re.compile(r'【(\d{1,2})】'),                          # 【1】 【22】
        re.compile(r'(?:^|\n)[（(](\d{1,2})[）)]'),            # (1) 行首
        re.compile(r'(?:^|\n)\s*(\d{1,2})[．.]'),              # 1． 行首(不要求后有空格)
        re.compile(r'[（(](\d{1,2})[）)]'),                     # (1) 任意位置
    ]
    all_nums = set()
    for pat in patterns:
        for m in pat.finditer(text):
            num = int(m.group(1))
            if 1 <= num <= 30:
                all_nums.add(num)
    return sorted(all_nums)


def _find_question_gaps(nums: list[int]) -> list[int]:
    """找出题号缺口"""
    if len(nums) < 2:
        return []
    gaps = []
    for i in range(1, len(nums)):
        gap = nums[i] - nums[i - 1]
        if gap > 1:
            for missing in range(nums[i - 1] + 1, nums[i]):
                gaps.append(missing)
    return gaps




def _count_broken_math(text: str) -> int:
    """检测断裂的数学语法"""
    count = 0
    # 检测 \frac 但缺少参数
    count += len(re.findall(r'\\frac(?![{])', text))
    # 检测 \sqrt 但缺少参数
    count += len(re.findall(r'\\sqrt(?![{])', text))
    # 检测孤立的花括号
    count += len(re.findall(r'(?<!\\)\{(?![^{}]*\})', text))
    return count
