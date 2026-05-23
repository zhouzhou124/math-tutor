"""validators.py — Pre-storage LaTeX validation layer.

Runs before DB insert. Catches broken LaTeX early.
"""
import re
from dataclasses import dataclass, field
from math_sanitizer import safe_latex, is_valid_latex
from database.question_schema import get_raw_question


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixed_fields: dict = field(default_factory=dict)  # field → fixed value


def _check_braces(text: str) -> list[str]:
    """Check { } pairing."""
    errors = []
    depth = 0
    for i, c in enumerate(text):
        if c == '{' and (i == 0 or text[i-1] != '\\'):
            depth += 1
        elif c == '}' and (i == 0 or text[i-1] != '\\'):
            depth -= 1
        if depth < 0:
            errors.append(f"多余的 '}}' 在位置 {i}")
            depth = 0
    if depth > 0:
        errors.append(f"缺少 {depth} 个 '}}'")
    return errors


def _check_dollars(text: str) -> list[str]:
    """Check $ pairing."""
    errors = []
    # Count $$ and $ separately
    display = text.count("$$")
    if display % 2 != 0:
        errors.append(f"$$ 不成对 ({display} 个)")
    # Remove $$ blocks, then check $
    temp = text.replace("$$", "")
    inline = temp.count("$")
    if inline % 2 != 0:
        errors.append(f"$ 不成对 ({inline} 个)")
    return errors


def _check_katex_compat(text: str) -> list[str]:
    """Check for KaTeX-incompatible commands."""
    warnings = []
    # Commands that KaTeX doesn't support
    unsupported = [
        r'\textcircled', r'\xrightarrow', r'\xleftarrow',
        r'\ddfrac', r'\tfrac',
    ]
    for cmd in unsupported:
        if cmd in text:
            warnings.append(f"KaTeX 可能不支持: {cmd}")
    return warnings


def validate_question_stem(stem: str) -> ValidationResult:
    """Validate the question stem text."""
    result = ValidationResult()

    if not stem or not stem.strip():
        result.errors.append("题干为空")
        result.valid = False
        return result

    # Brace check
    result.errors.extend(_check_braces(stem))

    # Dollar check
    result.errors.extend(_check_dollars(stem))

    # KaTeX compat
    result.warnings.extend(_check_katex_compat(stem))

    # Quick LaTeX validity
    if not is_valid_latex(stem):
        result.warnings.append("题干 LaTeX 可能不合法")

    result.valid = len(result.errors) == 0
    return result


def validate_option_content(content: str) -> ValidationResult:
    """Validate a single option's LaTeX content."""
    result = ValidationResult()

    if not content or not content.strip():
        result.errors.append("选项内容为空")
        result.valid = False
        return result

    # Strip $ wrappers for checking
    c = content.strip()
    inner = c
    while inner.startswith("$$") or inner.startswith("$"):
        inner = inner[1:].strip() if inner.startswith("$") and not inner.startswith("$$") else (
            inner[2:].strip() if inner.startswith("$$") else inner[1:].strip()
        )
    while inner.endswith("$$") or inner.endswith("$"):
        inner = inner[:-1].strip() if inner.endswith("$") and not inner.endswith("$$") else (
            inner[:-2].strip() if inner.endswith("$$") else inner[:-1].strip()
        )

    if not inner:
        result.errors.append("选项内容仅含 $ 符号")
        result.valid = False
        return result

    # Brace check on inner content
    result.errors.extend(_check_braces(inner))

    # Fix common \frac without braces
    if re.search(r'\\frac\d[^{]', inner):
        result.warnings.append("\\frac 缺少花括号，已自动修复")
        fixed = re.sub(r'\\frac(\d)(\d)', r'\\frac{\1}{\2}', inner)
        result.fixed_fields["content"] = fixed

    result.valid = len(result.errors) == 0
    return result


def validate_question(q: dict) -> ValidationResult:
    """Validate a full question before storage.

    Checks:
      1. Stem LaTeX (braces, dollars, KaTeX compat)
      2. Option content (each option individually)
      3. Answer format
    """
    result = ValidationResult()

    # 1. Stem
    stem = get_raw_question(q) or q.get("stem", "")
    stem_result = validate_question_stem(stem)
    result.errors.extend(stem_result.errors)
    result.warnings.extend(stem_result.warnings)

    # 2. Options
    options = q.get("options") or {}
    if isinstance(options, dict):
        for label, content in options.items():
            opt_result = validate_option_content(content)
            for err in opt_result.errors:
                result.errors.append(f"选项 {label}: {err}")
            for warn in opt_result.warnings:
                result.warnings.append(f"选项 {label}: {warn}")
            if opt_result.fixed_fields:
                result.fixed_fields[label] = opt_result.fixed_fields["content"]
    elif isinstance(options, list):
        for opt in options:
            label = opt.label if hasattr(opt, 'label') else opt.get('label', '?')
            content = opt.content if hasattr(opt, 'content') else opt.get('content', '')
            opt_result = validate_option_content(content)
            for err in opt_result.errors:
                result.errors.append(f"选项 {label}: {err}")
            for warn in opt_result.warnings:
                result.warnings.append(f"选项 {label}: {warn}")

    # 3. Answer
    answer = q.get("standard_answer", "") or q.get("answer", "")
    if answer:
        ans_result = validate_option_content(answer)
        for err in ans_result.errors:
            result.errors.append(f"答案: {err}")

    result.valid = len(result.errors) == 0
    return result


def validate_and_repair(q: dict) -> tuple[dict, ValidationResult]:
    """Validate and attempt to repair a question before storage.

    Returns (repaired_q, result).
    """
    result = validate_question(q)
    repaired = dict(q)

    # Deep copy options to avoid mutating the original via shared dict ref
    raw_options = repaired.get("options")
    if isinstance(raw_options, dict):
        repaired["options"] = dict(raw_options)
    elif isinstance(raw_options, list):
        repaired["options"] = list(raw_options)

    # Apply fixes from validation
    if result.fixed_fields:
        options = repaired.get("options") or {}
        for label, fixed_content in result.fixed_fields.items():
            if isinstance(options, dict) and label in options:
                options[label] = fixed_content
            elif isinstance(options, list):
                for opt in options:
                    if (hasattr(opt, 'label') and opt.label == label) or opt.get('label') == label:
                        if hasattr(opt, 'content'):
                            opt.content = fixed_content
                        else:
                            opt['content'] = fixed_content
        repaired["options"] = options

    # Try safe_latex on stem — only touch backward-compat 'question' field,
    # never overwrite raw_question_text.
    stem = get_raw_question(repaired) or repaired.get("stem", "")
    if stem:
        try:
            repaired_stem = safe_latex(stem)
            if repaired_stem != stem:
                # Write to backward-compat 'question' only if no raw field exists yet
                if not repaired.get("raw_question_text"):
                    repaired["question"] = repaired_stem
                result.warnings.append("题干已通过 safe_latex 修复")
        except Exception:
            pass

    return repaired, result
