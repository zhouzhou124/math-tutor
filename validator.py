"""
Validator — LaTeX/Markdown 结构合法性检查引擎

在入库前运行，拒绝非法结构。
所有检查都是 deterministic，零 LLM 调用。
"""
import re

ENVIRONMENTS = [
    "pmatrix", "bmatrix", "matrix", "vmatrix",
    "cases", "aligned", "array",
]


def validate_inline_math(text: str) -> bool:
    """检查 $ 是否配对（排除 $$）."""
    stripped = text.replace("$$", "")
    return stripped.count("$") % 2 == 0


def validate_display_math(text: str) -> bool:
    """检查 $$ 是否配对."""
    return text.count("$$") % 2 == 0


def validate_environments(text: str) -> bool:
    """检查 \\begin 和 \\end 数量是否匹配."""
    begins = sum(len(re.findall(rf"\\begin{{{env}}}", text)) for env in ENVIRONMENTS)
    ends = sum(len(re.findall(rf"\\end{{{env}}}", text)) for env in ENVIRONMENTS)
    return begins == ends


def validate_no_triple_dollar(text: str) -> bool:
    """检查是否有 $\\$\\$（非法）."""
    return "$$$" not in text


def validate_no_double_backslash_cmd(text: str) -> bool:
    """检查是否有双反斜杠 LaTeX 命令（例如 \\\\frac）."""
    return not bool(re.search(r'\\\\(frac|begin|end|text|operatorname|int|sum|lim)', text))


def validate_underline(text: str) -> bool:
    """检查是否有空 \\underline{}."""
    return not bool(re.search(r'\\underline\{\s*\}', text))


def validate_question_number(text: str) -> bool:
    """检查是否以 $N.$ 开头."""
    return bool(re.match(r'\$\d{1,2}\.\$', text))


def validate(text: str, strict: bool = True) -> dict:
    """
    运行所有合法性检查。

    Returns:
        {"valid": bool, "errors": [str], "warnings": [str]}
    """
    errors = []
    warnings = []

    if not validate_inline_math(text):
        warnings.append("Possible unbalanced inline math ($) — verify manually")

    if not validate_display_math(text):
        errors.append("Unbalanced display math ($$)")

    if not validate_environments(text):
        errors.append("Unbalanced \\begin/\\end environments")

    if not validate_no_triple_dollar(text):
        errors.append("Triple dollar sign ($$$) detected")

    if not validate_question_number(text):
        warnings.append("Missing question number ($N.$)")

    if validate_no_double_backslash_cmd(text):
        pass  # OK
    else:
        warnings.append("Double-backslash LaTeX commands detected")

    if validate_underline(text):
        pass  # OK
    else:
        warnings.append("Empty \\underline{} detected")

    valid = len(errors) == 0

    return {"valid": valid, "errors": errors, "warnings": warnings}
