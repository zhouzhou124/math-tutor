r"""
LaTeX Validator — LaTeX 结构合法性验证

职责:
  在渲染前检查 LaTeX 的结构合法性，防止非法 LaTeX 进入 UI 层。

  检查项:
    1. 花括号匹配: { }
    2. begin/end 环境匹配: \begin{...} \end{...}
    3. left/right 括号匹配: \left( \right) 等
    4. inline/block math 一致性
    5. aligned 等环境必须出现在 block math 内

  修复策略:
    - 自动修复可修复的问题（如补全缺失的 \\right.）
    - 对不可修复的问题返回错误报告
    - 修复后重新验证
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple


class ValidationSeverity(Enum):
    ERROR = auto()
    WARNING = auto()
    INFO = auto()


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    category: str
    message: str
    position: int = -1
    context: str = ""
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    fixed_latex: str = ""

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)


_BEGIN_ENV_RE = re.compile(r'\\begin\{(\w+)\}')
_END_ENV_RE = re.compile(r'\\end\{(\w+)\}')

_LEFT_COMMANDS = {
    r'\left(', r'\left[', r'\left\{', r'\left|', r'\left\|',
    r'\left<', r'\left.', r'\left\lfloor', r'\left\lceil',
    r'\left\langle',
}
_RIGHT_COMMANDS = {
    r'\right)', r'\right]', r'\right\}', r'\right|', r'\right\|',
    r'\right>', r'\right.', r'\right\rfloor', r'\right\rceil',
    r'\right\rangle',
}

_RIGHT_FOR_LEFT = {
    r'\left(': r'\right)',
    r'\left[': r'\right]',
    r'\left\{': r'\right\}',
    r'\left|': r'\right|',
    r'\left\|': r'\right\|',
    r'\left<': r'\right>',
    r'\left\lfloor': r'\right\rfloor',
    r'\left\lceil': r'\right\rceil',
    r'\left\langle': r'\right\rangle',
    r'\left.': r'\right.',
}

_BLOCK_ENVS = {
    'aligned', 'align', 'align*', 'gather', 'gather*', 'multline',
    'multline*', 'eqnarray', 'eqnarray*', 'cases', 'array',
    'matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix',
    'split', 'equation', 'equation*',
}

_INLINE_ENVS = {
    'text', 'mathrm', 'mathbf', 'mathit', 'mathsf', 'mathtt',
    'textrm', 'textbf', 'textit',
}


class LaTeXValidator:
    """
    LaTeX 结构合法性验证器。

    用法:
      validator = LaTeXValidator()
      result = validator.validate(latex_string)
      if not result.is_valid:
          print(result.issues)
      fixed = validator.validate_and_fix(latex_string)
    """

    def validate(self, latex: str) -> ValidationResult:
        if not latex or not latex.strip():
            return ValidationResult(is_valid=True, fixed_latex=latex)

        issues = []
        issues.extend(self._check_braces(latex))
        issues.extend(self._check_begin_end(latex))
        issues.extend(self._check_left_right(latex))
        issues.extend(self._check_block_env_in_inline(latex))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            fixed_latex=latex,
        )

    def validate_and_fix(self, latex: str) -> ValidationResult:
        if not latex or not latex.strip():
            return ValidationResult(is_valid=True, fixed_latex=latex)

        fixed = latex
        fixed = self._fix_braces(fixed)
        fixed = self._fix_begin_end(fixed)
        fixed = self._fix_left_right(fixed)
        fixed = self._fix_block_env_wrapping(fixed)

        recheck = self.validate(fixed)
        return ValidationResult(
            is_valid=recheck.is_valid,
            issues=recheck.issues,
            fixed_latex=fixed,
        )

    def _check_braces(self, latex: str) -> List[ValidationIssue]:
        issues = []
        depth = 0
        i = 0
        n = len(latex)

        while i < n:
            c = latex[i]
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth < 0:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="brace",
                        message=f"多余的 '}}' 在位置 {i}",
                        position=i,
                        context=latex[max(0, i - 10):i + 10],
                        auto_fixable=True,
                    ))
                    depth = 0
            i += 1

        if depth > 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="brace",
                message=f"缺少 {depth} 个 '}}'",
                position=len(latex),
                context=latex[-20:] if len(latex) > 20 else latex,
                auto_fixable=True,
            ))

        return issues

    def _check_begin_end(self, latex: str) -> List[ValidationIssue]:
        issues = []
        stack: List[Tuple[str, int]] = []

        for m in _BEGIN_ENV_RE.finditer(latex):
            env_name = m.group(1)
            stack.append((env_name, m.start()))

        for m in _END_ENV_RE.finditer(latex):
            env_name = m.group(1)
            if stack and stack[-1][0] == env_name:
                stack.pop()
            elif stack:
                expected = stack[-1][0]
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="begin_end",
                    message=f"\\end{{{env_name}}} 与 \\begin{{{expected}}} 不匹配",
                    position=m.start(),
                    context=latex[max(0, m.start() - 15):m.end() + 15],
                    auto_fixable=False,
                ))
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="begin_end",
                    message=f"多余的 \\end{{{env_name}}}",
                    position=m.start(),
                    context=latex[max(0, m.start() - 15):m.end() + 15],
                    auto_fixable=True,
                ))

        for env_name, pos in stack:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="begin_end",
                message=f"缺少 \\end{{{env_name}}}",
                position=pos,
                context=latex[max(0, pos - 10):pos + 30],
                auto_fixable=True,
            ))

        return issues

    def _check_left_right(self, latex: str) -> List[ValidationIssue]:
        issues = []
        stack: List[Tuple[str, int]] = []

        left_pattern = re.compile(r'\\left(?:\(|\[|\{|\\\||<|\.|\\lfloor|\\lceil|\\langle|)')
        right_pattern = re.compile(r'\\right(?:\)|\]|\\\||>|\.|\\rfloor|\\rceil|\\rangle|)')

        for m in left_pattern.finditer(latex):
            cmd = m.group(0)
            if cmd == r'\left':
                continue
            stack.append((cmd, m.start()))

        for m in right_pattern.finditer(latex):
            cmd = m.group(0)
            if cmd == r'\right':
                continue
            if stack:
                stack.pop()
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="left_right",
                    message=f"多余的 {cmd}，没有匹配的 \\left",
                    position=m.start(),
                    context=latex[max(0, m.start() - 15):m.end() + 15],
                    auto_fixable=True,
                ))

        for cmd, pos in stack:
            expected_right = _RIGHT_FOR_LEFT.get(cmd, r'\right.')
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="left_right",
                message=f"缺少 {expected_right} 来匹配 {cmd}",
                position=pos,
                context=latex[max(0, pos - 10):pos + 20],
                auto_fixable=True,
            ))

        return issues

    def _check_block_env_in_inline(self, latex: str) -> List[ValidationIssue]:
        issues = []

        inline_pattern = re.compile(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)')
        for m in inline_pattern.finditer(latex):
            content = m.group(1)
            for env in _BLOCK_ENVS:
                if f'\\begin{{{env}}}' in content:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="inline_block",
                        message=f"block 环境 \\begin{{{env}}} 出现在 inline math ($...$) 内",
                        position=m.start(),
                        context=content[:50],
                        auto_fixable=True,
                    ))

        return issues

    def _fix_braces(self, latex: str) -> str:
        depth = 0
        i = 0
        n = len(latex)

        while i < n:
            c = latex[i]
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth < 0:
                    latex = latex[:i] + latex[i + 1:]
                    depth = 0
                    continue
            i += 1

        if depth > 0:
            latex += '}' * depth

        return latex

    def _fix_begin_end(self, latex: str) -> str:
        stack: List[Tuple[str, int]] = []

        for m in _BEGIN_ENV_RE.finditer(latex):
            env_name = m.group(1)
            stack.append((env_name, m.start()))

        for m in _END_ENV_RE.finditer(latex):
            env_name = m.group(1)
            if stack and stack[-1][0] == env_name:
                stack.pop()
            elif stack:
                pass

        for env_name, _ in reversed(stack):
            latex += f'\\end{{{env_name}}}'

        return latex

    def _fix_left_right(self, latex: str) -> str:
        stack: List[Tuple[str, int]] = []

        left_pattern = re.compile(r'\\left(?:\(|\[|\{|\\\||<|\.|\\lfloor|\\lceil|\\langle|)')
        right_pattern = re.compile(r'\\right(?:\)|\]|\\\||>|\.|\\rfloor|\\rceil|\\rangle|)')

        for m in left_pattern.finditer(latex):
            cmd = m.group(0)
            if cmd == r'\left':
                continue
            stack.append((cmd, m.start()))

        for m in right_pattern.finditer(latex):
            cmd = m.group(0)
            if cmd == r'\right':
                continue
            if stack:
                stack.pop()

        for cmd, pos in reversed(stack):
            expected_right = _RIGHT_FOR_LEFT.get(cmd, r'\right.')
            latex += f' {expected_right}'

        return latex

    def _fix_block_env_wrapping(self, latex: str) -> str:
        for env in _BLOCK_ENVS:
            begin_tag = f'\\begin{{{env}}}'
            end_tag = f'\\end{{{env}}}'

            if begin_tag not in latex:
                continue

            if env in _INLINE_ENVS:
                continue

            idx = latex.find(begin_tag)
            before = latex[:idx].rstrip()

            in_block = False
            if before.endswith('$$'):
                in_block = True
            elif before.endswith('\\['):
                in_block = True
            elif '$$' in before and not before.rstrip().endswith('$$'):
                pass

            if not in_block:
                dollar_prefix = ''
                dollar_suffix = ''

                if idx > 0 and latex[idx - 1] == '$' and latex[idx - 2:idx - 1] != '$':
                    latex = latex[:idx - 1] + '$$' + latex[idx:]
                    end_idx = latex.find(end_tag)
                    if end_idx != -1:
                        after_end = end_idx + len(end_tag)
                        latex = latex[:after_end] + '$$' + latex[after_end:]
                else:
                    latex = latex[:idx] + '$$' + latex[idx:]
                    end_idx = latex.find(end_tag)
                    if end_idx != -1:
                        after_end = end_idx + len(end_tag)
                        latex = latex[:after_end] + '$$' + latex[after_end:]

        return latex
