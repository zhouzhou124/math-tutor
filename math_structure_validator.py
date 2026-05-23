"""
Math Structure Validator — 阻止错误 LaTeX 进入数据库

在存储前验证数学结构合法性。
Prompt 降低错误率，Validator 阻止错误入库。
"""

import re
from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixed: bool = False


def validate(text: str, fix: bool = True) -> ValidationReport:
    """
    验证 LaTeX 结构合法性，选择是否自动修复。

    检查项:
      R1: 重复 \left / \right
      R2: 重复 \limits
      R3: 转义换行符
      R4: 选项格式
      R5: 微分格式
      R6: 中文在数学模式内
      R7: 嵌套数学环境
      R8: 数学括号配对
    """
    report = ValidationReport()

    # R1: 重复 \left / \right
    if '\\left\\left' in text or '\\right\\right' in text:
        report.errors.append("R1: 重复 \\left 或 \\right")
        report.valid = False

    # R2: 重复 \limits
    if '\\limits\\limits' in text:
        report.errors.append("R2: 重复 \\limits")
        report.valid = False

    # R3: 转义换行符
    if '\\n' in text:
        report.errors.append("R3: 包含转义换行符 \\n")
        report.valid = False

    # R4: 裸选项格式
    if re.search(r'(?:^|\n)\s*[（(]\s*[A-D]\s*[）)]\s*(?!\$)', text):
        report.warnings.append("R4: 包含非规范选项格式 (A)")
    if re.search(r'(?:^|\n)\s*[A-D][.．、]\s*(?!\$)', text):
        report.warnings.append("R4: 包含非规范选项格式 A.")

    # R5: 裸微分
    if re.search(r'(?<!\\mathrm\{d\})[dD][xyztrsuvw](?=\s|$|\\|\)|\.|,)', text):
        if '\\mathrm{d}' not in text and '\\,\\mathrm{d}' not in text:
            report.warnings.append("R5: 包含非规范微分符号")

    # R6: 中文在数学模式内
    def _check_chinese_in_math(match):
        content = match.group(1)
        return any('一' <= c <= '鿿' for c in content)
    if any(_check_chinese_in_math(m) for m in re.finditer(r'\$([^$]+)\$', text)):
        report.warnings.append("R6: 中文在数学模式内")

    # R7: 嵌套数学环境
    if re.search(r'\$\$[^$]*\$[^$]+\$[^$]*\$\$', text):
        report.errors.append("R7: 嵌套数学环境 $$ $...$ $$")
        report.valid = False
    if re.search(r'\$\s*\$\$', text) or re.search(r'\$\$\s*\$', text):
        report.warnings.append("R7: $ 与 $$ 相邻，疑似嵌套")

    # R7b: LaTeX 命令转义损坏检测
    # 检测 \n 出现在 LaTeX 命令中间（如 \neq 变成了 \n eq）
    if re.search(r'\\[a-zA-Z]*\s+[a-zA-Z]+', text) and re.search(r'\\[a-zA-Z]', text):
        pass  # 合法：命令后跟空白+文本
    # 检测字面量 \n 出现在文本中（不应再有，normalizer 已处理）
    if '\\n' in text:
        report.warnings.append("R7b: 仍包含字面量 \\n 转义符")
    # 检测双反斜杠（可能是双重转义）
    if re.search(r'\\\\(?:neq|leq|geq|sum|int|frac|alpha|beta|gamma)', text):
        report.errors.append("R7b: LaTeX 命令双重转义（\\\\neq 等）")
        report.valid = False

    # R8: 数学括号配对（仅对 question 字段严格检查，answer/solution 宽松）
    # 花括号 — 全局检查
    brace_depth = 0
    for ch in text:
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
        if brace_depth < 0:
            brace_depth = 0
    if brace_depth != 0:
        report.errors.append(f"R8: 数学花括号不配对 (depth={brace_depth})")
        report.valid = False

    # $ 配对 — 跳过 $$ 后检查
    text_no_dd = text.replace('$$', '')
    single_dollars = text_no_dd.count('$')
    if single_dollars % 2 != 0:
        report.errors.append(f"R8: \$ 不配对 ({single_dollars}个)")
        report.valid = False

    return report


def validate_and_fix(text: str) -> tuple[str, ValidationReport]:
    """验证并自动修复"""
    from latex_normalizer import normalize_latex_style

    report = validate(text, fix=False)

    if not report.valid or report.warnings:
        # 尝试自动修复
        fixed = normalize_latex_style(text)
        report2 = validate(fixed, fix=False)

        if report2.valid and not report2.errors:
            report.fixed = True
            return fixed, report

    return text, report


def validate_entity(entity_dict: dict) -> ValidationReport:
    """验证整个题目实体的 LaTeX 结构"""
    report = ValidationReport()

    # 检查题目
    q_text = entity_dict.get("raw_question_text") or entity_dict.get("question", "")
    q_report = validate(q_text, fix=False)
    if not q_report.valid:
        report.errors.extend(f"[question] {e}" for e in q_report.errors)
        report.valid = False
    report.warnings.extend(f"[question] {w}" for w in q_report.warnings)

    # 检查答案（宽松：可能被截断，仅报告为 warning）
    a_text = entity_dict.get("standard_answer", "")
    if a_text:
        a_report = validate(a_text, fix=False)
        report.warnings.extend(f"[answer] {e}" for e in a_report.errors)
        report.warnings.extend(f"[answer] {w}" for w in a_report.warnings)

    # 检查解析（宽松：可能被截断）
    steps = entity_dict.get("solution_steps", [])
    for i, step in enumerate(steps):
        if step:
            s_report = validate(step, fix=False)
            report.warnings.extend(f"[step{i}] {e}" for e in s_report.errors)
            report.warnings.extend(f"[step{i}] {w}" for w in s_report.warnings)

    return report
