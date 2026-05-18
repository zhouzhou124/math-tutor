"""
Math Formatter — LaTeX 正规化与格式化引擎

═══════════════════════════════════════════════════════════════
职责
═══════════════════════════════════════════════════════════════

  在渲染流水线中，将"原始 LaTeX / 内部表达式"转换为
  "可显示的规范 LaTeX"。

  与 normalizer.py 的区别:
    normalizer.py — 题目文本的 token 级修复 (OCR/LLM 输出)
    MathFormatter — 渲染层的结构化格式化 (显示优化)

  四大功能:
    1. LaTeX normalize  — 矩阵换行、等号对齐、环境正规化
    2. Auto display math — 检测数学环境，自动包裹 $$...$$
    3. Long formula break — 长公式自动换行 \begin{aligned}
    4. Matrix formatter  — Matrix(...) / 原始数据 → \begin{bmatrix}

═══════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════

  from rendering.math_formatter import MathFormatter

  fmt = MathFormatter()

  # 1. LaTeX 正规化
  fmt.normalize(r"P_1=\begin{pmatrix}0&1&0\\1&0&0\\0&0&1\end{pmatrix}")
  # → "P_1 =\n\\begin{pmatrix}\n0 & 1 & 0 \\\\\n1 & 0 & 0 \\\\\n0 & 0 & 1\n\\end{pmatrix}"

  # 2. 自动 display math
  fmt.auto_display(r"\begin{pmatrix}1&0\\0&1\end{pmatrix}")
  # → "$$\n\\begin{pmatrix}\n1 & 0 \\\\\n0 & 1\n\\end{pmatrix}\n$$"

  # 3. 长公式换行
  fmt.break_long_formula(r"A=B=C=D=E")
  # → "\\begin{aligned}\nA &= B = C \\\\\n  &= D = E\n\\end{aligned}"

  # 4. 矩阵格式化
  fmt.format_matrix([[1,0,0],[0,1,0],[0,0,1]])
  # → "\\begin{bmatrix}\n1 & 0 & 0 \\\\\n0 & 1 & 0 \\\\\n0 & 0 & 1\n\\end{bmatrix}"

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence


_DISPLAY_ENVS = frozenset({
    "pmatrix", "bmatrix", "vmatrix", "matrix",
    "cases", "aligned", "align", "align*",
    "array", "gather", "gather*", "multline", "multline*",
    "split", "equation", "equation*",
})

_MATRIX_ENVS = frozenset({
    "pmatrix", "bmatrix", "vmatrix", "matrix",
})

_EQ_CHAIN_PATTERN = re.compile(
    r'((?:[^=\\]|\\.)+?)\s*=\s*((?:[^=\\]|\\.)+?)\s*=\s*((?:[^=\\]|\\.)+)')
_EQ_CHAIN_GLOBAL = re.compile(
    r'(?<!=)\s*=\s*(?!=)')

_MATRIX_LITERAL_PATTERN = re.compile(
    r'Matrix\(\s*\[(.*?)\]\s*\)', re.S)

_NDARRAY_PATTERN = re.compile(
    r'(?:array|ndarray|tensor)\(\s*\[(.*?)\]\s*\)', re.S)


@dataclass(frozen=True)
class FormatterConfig:
    matrix_env: str = "bmatrix"
    indent_str: str = "  "
    eq_chain_threshold: int = 3
    formula_line_width: int = 60
    add_spaces_around_eq: bool = True
    matrix_col_sep: str = " & "
    matrix_row_sep: str = " \\\\\n"
    wrap_display_math: bool = True
    normalize_matrices: bool = True
    break_long_formulas: bool = True


class MathFormatter:
    """
    Math Formatter — LaTeX 正规化与格式化引擎。

    四大入口:
      normalize(latex)        → 正规化 LaTeX
      auto_display(latex)     → 自动 display math 包裹
      break_long_formula(lat) → 长公式换行
      format_matrix(data)     → 矩阵格式化
    """

    def __init__(self, config: FormatterConfig = None):
        self.config = config or FormatterConfig()

    def format(self, latex: str) -> str:
        """
        全流程格式化: normalize → auto_display → break_long.
        """
        if not latex or not latex.strip():
            return latex or ""

        result = self.normalize(latex)
        result = self.auto_display(result)
        if self.config.break_long_formulas:
            result = self.break_long_formula(result)
        return result

    # ═══════════════════════════════════════════════════════════
    # 1. LaTeX Normalize
    # ═══════════════════════════════════════════════════════════

    def normalize(self, latex: str) -> str:
        """
        LaTeX 正规化:
          - 矩阵环境换行美化
          - 等号前后加空格
          - 修复 \\begin/\\end 配对
          - 清理多余空格
        """
        if not latex or not latex.strip():
            return latex or ""

        result = latex.strip()

        result = self._normalize_matrix_envs(result)
        result = self._normalize_cases_envs(result)
        result = self._normalize_eq_spacing(result)
        result = self._normalize_whitespace(result)
        result = self._normalize_matrix_literal(result)
        result = self._normalize_ndarray_literal(result)

        return result

    def _normalize_matrix_envs(self, latex: str) -> str:
        """
        矩阵环境正规化:
          P_1=\\begin{pmatrix}0&1&0\\\\1&0&0\\\\0&0&1\\end{pmatrix}
          →
          P_1 =
          \\begin{pmatrix}
            0 & 1 & 0 \\\\
            1 & 0 & 0 \\\\
            0 & 0 & 1
          \\end{pmatrix}
        """
        for env in _MATRIX_ENVS:
            result = self._normalize_one_env(latex, env)
            if result != latex:
                latex = result
        return latex

    def _normalize_one_env(self, latex: str, env: str) -> str:
        begin_tag = f"\\begin{{{env}}}"
        end_tag = f"\\end{{{env}}}"

        result = []
        pos = 0

        while pos < len(latex):
            begin_idx = latex.find(begin_tag, pos)
            if begin_idx == -1:
                result.append(latex[pos:])
                break

            end_idx = latex.find(end_tag, begin_idx + len(begin_tag))
            if end_idx == -1:
                result.append(latex[pos:])
                break

            before_text = latex[pos:begin_idx]
            content = latex[begin_idx + len(begin_tag):end_idx]

            stripped_before = before_text.rstrip()
            if stripped_before and not stripped_before.endswith("\n"):
                char_before = stripped_before[-1]
                if char_before == "=":
                    before_text = stripped_before[:-1].rstrip() + " =\n"
                elif char_before not in ("$", "}", "{"):
                    before_text = stripped_before + "\n"

            result.append(before_text)

            formatted_content = self._format_matrix_content(content)

            indent = self.config.indent_str
            lines = formatted_content.split("\n")
            indented = "\n".join(
                indent + line if line.strip() else line
                for line in lines
            )

            result.append(begin_tag + "\n")
            result.append(indented + "\n")
            result.append(end_tag)

            pos = end_idx + len(end_tag)

        return "".join(result)

    def _format_matrix_content(self, content: str) -> str:
        """
        矩阵内容格式化:
          "0&1&0\\\\1&0&0\\\\0&0&1"
          →
          "0 & 1 & 0 \\\\
             1 & 0 & 0 \\\\
             0 & 0 & 1"
        """
        content = content.strip()

        content = re.sub(r'\s*\\\\\s*', '\n', content)
        content = re.sub(r'\s*&\s*', ' & ', content)

        rows = [row.strip() for row in content.split("\n") if row.strip()]

        formatted_rows = []
        for row in rows:
            row = re.sub(r'\s+', ' ', row)
            formatted_rows.append(row)

        return " \\\\\n".join(formatted_rows)

    def _normalize_cases_envs(self, latex: str) -> str:
        begin_tag = "\\begin{cases}"
        end_tag = "\\end{cases}"

        result = []
        pos = 0

        while pos < len(latex):
            begin_idx = latex.find(begin_tag, pos)
            if begin_idx == -1:
                result.append(latex[pos:])
                break

            end_idx = latex.find(end_tag, begin_idx + len(begin_tag))
            if end_idx == -1:
                result.append(latex[pos:])
                break

            before_text = latex[pos:begin_idx]
            result.append(before_text)
            content = latex[begin_idx + len(begin_tag):end_idx]

            content = re.sub(r'\s*\\\\\s*', '\n', content)
            rows = [r.strip() for r in content.split("\n") if r.strip()]
            indent = self.config.indent_str
            indented = " \\\\\n".join(indent + r for r in rows)

            result.append(begin_tag + "\n")
            result.append(indented + "\n")
            result.append(end_tag)

            pos = end_idx + len(end_tag)

        return "".join(result)

    def _normalize_eq_spacing(self, latex: str) -> str:
        """
        等号前后加空格 (仅不在环境内部时).
          A=B → A = B
          但 \\begin{aligned} 内部保持原样.
        """
        in_env = False
        result = []
        i = 0
        while i < len(latex):
            if latex[i:].startswith("\\begin{"):
                in_env = True
            elif latex[i:].startswith("\\end{"):
                in_env = False

            if not in_env and self.config.add_spaces_around_eq:
                if latex[i] == '=' and i > 0 and i < len(latex) - 1:
                    prev = result[-1] if result else ""
                    next_ch = latex[i + 1] if i + 1 < len(latex) else ""
                    if prev != ' ' and prev != '=' and next_ch != '=':
                        result.append(' = ')
                        i += 1
                        continue

            result.append(latex[i])
            i += 1

        return "".join(result)

    def _normalize_whitespace(self, latex: str) -> str:
        result = re.sub(r'[ \t]+', ' ', latex)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _normalize_matrix_literal(self, latex: str) -> str:
        """
        Matrix([[1,0],[0,1]]) → \\begin{bmatrix}1 & 0 \\\\ 0 & 1\\end{bmatrix}
        """
        pattern = re.compile(r'Matrix\(\s*(\[[\s\S]*?\])\s*\)')
        def _replace(m):
            inner = m.group(1)
            rows = self._parse_nested_list(inner)
            if rows:
                return self.format_matrix(rows, env=self.config.matrix_env)
            return m.group(0)

        return pattern.sub(_replace, latex)

    def _normalize_ndarray_literal(self, latex: str) -> str:
        """
        array([[1,0],[0,1]]) / ndarray(...) → \\begin{bmatrix}...\\end{bmatrix}
        """
        def _replace(m):
            inner = m.group(1)
            rows = self._parse_nested_list(inner)
            if rows:
                return self.format_matrix(rows, env=self.config.matrix_env)
            return m.group(0)

        return _NDARRAY_PATTERN.sub(_replace, latex)

    def _parse_nested_list(self, text: str) -> list[list[str]]:
        """
        解析嵌套列表字符串: "[[1,0,0],[0,1,0],[0,0,1]]"
        → [["1","0","0"],["0","1","0"],["0","0","1"]]
        """
        text = text.strip()
        if not text.startswith("["):
            return []

        rows = []
        depth = 0
        current_row = ""
        for ch in text:
            if ch == '[':
                depth += 1
                if depth == 2:
                    current_row = ""
                    continue
            elif ch == ']':
                depth -= 1
                if depth == 1:
                    if current_row.strip():
                        elements = [e.strip() for e in current_row.split(",") if e.strip()]
                        rows.append(elements)
                    current_row = ""
                    continue
            elif ch == ',' and depth == 1:
                continue

            if depth >= 2:
                current_row += ch

        return rows if rows else []

    # ═══════════════════════════════════════════════════════════
    # 2. Auto Display Math
    # ═══════════════════════════════════════════════════════════

    def auto_display(self, latex: str) -> str:
        if not latex or not latex.strip():
            return latex or ""

        if not self.config.wrap_display_math:
            return latex

        stripped = latex.strip()

        if self._is_already_display(stripped):
            return latex

        if self._needs_display_math(stripped):
            inner = self.normalize(stripped) if self.config.normalize_matrices else stripped
            return f"$$\n{inner}\n$$"

        return latex

    def _is_already_display(self, latex: str) -> bool:
        if latex.startswith("$$") and latex.endswith("$$"):
            return True
        if latex.startswith("\\[") and latex.endswith("\\]"):
            return True
        return False

    def _extract_env_name(self, latex: str) -> str:
        m = re.match(r'\\begin\{(\w+)\}', latex)
        return m.group(1) if m else ""

    def _needs_display_math(self, latex: str) -> bool:
        for env in _DISPLAY_ENVS:
            if f"\\begin{{{env}}}" in latex:
                return True

        display_commands = [
            r"\int", r"\sum", r"\prod",
            r"\lim", r"\inf", r"\sup",
            r"\oint", r"\iint", r"\iiint",
        ]
        for cmd in display_commands:
            if cmd in latex:
                return True

        if r"\frac" in latex and len(latex) > 20:
            return True

        if latex.count(r"\frac") >= 2:
            return True

        if r"\sqrt" in latex and r"\frac" in latex:
            return True

        if r"\begin{split}" in latex:
            return True

        return False

    # ═══════════════════════════════════════════════════════════
    # 3. Long Formula Line Breaking
    # ═══════════════════════════════════════════════════════════

    def break_long_formula(self, latex: str) -> str:
        """
        长公式自动换行:
          A = B = C = D = E
          →
          \\begin{aligned}
          A &= B = C \\\\
            &= D = E
          \\end{aligned}
        """
        if not latex or not latex.strip():
            return latex or ""

        stripped = latex.strip()

        if self._is_in_aligned_env(stripped):
            return latex

        if not self._has_eq_chain(stripped):
            return latex

        if len(stripped) <= self.config.formula_line_width:
            eq_count = self._count_equals(stripped)
            if eq_count < self.config.eq_chain_threshold:
                return latex

        return self._break_at_equals(stripped)

    def _is_in_aligned_env(self, latex: str) -> bool:
        return bool(re.search(r'\\begin\{align', latex))

    def _has_eq_chain(self, latex: str) -> bool:
        return self._count_equals(latex) >= 2

    def _count_equals(self, latex: str) -> int:
        in_cmd = False
        count = 0
        i = 0
        while i < len(latex):
            if latex[i] == '\\':
                in_cmd = True
                i += 2
                continue
            if in_cmd:
                if not latex[i].isalpha():
                    in_cmd = False
                else:
                    i += 1
                    continue
            if latex[i] == '=' and (i + 1 >= len(latex) or latex[i + 1] != '=') and (i == 0 or latex[i - 1] != '='):
                count += 1
            i += 1
        return count

    def _break_at_equals(self, latex: str) -> str:
        parts = self._split_at_equals(latex)
        if len(parts) < 3:
            return latex

        lhs = parts[0].strip()
        rhs_parts = [p.strip() for p in parts[1:]]

        lines = []
        lines.append(f"{lhs} &= {rhs_parts[0]}")

        for rhs in rhs_parts[1:]:
            lines.append(f"  &= {rhs}")

        if len(lines) <= 1:
            return latex

        body = " \\\\\n".join(lines)
        return f"\\begin{{aligned}}\n{body}\n\\end{{aligned}}"

    def _split_at_equals(self, latex: str) -> list[str]:
        """
        在 = 处拆分，但跳过 \\=, ==, !=, <=, >= 等.
        """
        parts = []
        current = []
        i = 0
        while i < len(latex):
            if latex[i] == '\\':
                current.append(latex[i])
                if i + 1 < len(latex):
                    current.append(latex[i + 1])
                i += 2
                continue

            if latex[i] == '=':
                if i + 1 < len(latex) and latex[i + 1] == '=':
                    current.append('==')
                    i += 2
                    continue
                if i > 0 and latex[i - 1] in ('!', '<', '>', '~'):
                    current.append('=')
                    i += 1
                    continue
                parts.append("".join(current))
                current = []
            else:
                current.append(latex[i])
            i += 1

        if current:
            parts.append("".join(current))

        return parts

    # ═══════════════════════════════════════════════════════════
    # 4. Matrix Formatter
    # ═══════════════════════════════════════════════════════════

    def format_matrix(
        self,
        data: Sequence[Sequence] | None = None,
        env: str = "",
        label: str = "",
    ) -> str:
        """
        矩阵格式化:
          format_matrix([[1,0,0],[0,1,0],[0,0,1]])
          →
          \\begin{bmatrix}
          1 & 0 & 0 \\\\
          0 & 1 & 0 \\\\
          0 & 0 & 1
          \\end{bmatrix}
        """
        if data is None:
            return ""

        env = env or self.config.matrix_env

        rows_latex = []
        for row in data:
            elements = [str(e) for e in row]
            rows_latex.append(self.config.matrix_col_sep.join(elements))

        body = " \\\\\n".join(rows_latex)

        result = f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

        if label:
            result = f"{label} =\n{result}"

        return result

    def format_vector(
        self,
        data: Sequence | None = None,
        env: str = "pmatrix",
        is_column: bool = True,
    ) -> str:
        """
        向量格式化:
          format_vector([1, 2, 3], is_column=True)
          → \\begin{pmatrix} 1 \\\\ 2 \\\\ 3 \\end{pmatrix}

          format_vector([1, 2, 3], is_column=False)
          → \\begin{pmatrix} 1 & 2 & 3 \\end{pmatrix}
        """
        if data is None:
            return ""

        if is_column:
            rows = [str(e) for e in data]
            body = " \\\\\n".join(rows)
        else:
            body = " & ".join(str(e) for e in data)

        return f"\\begin{{{env}}}\n{body}\n\\end{{{env}}}"

    def format_augmented_matrix(
        self,
        left: Sequence[Sequence],
        right: Sequence[Sequence],
        env: str = "array",
    ) -> str:
        """
        增广矩阵格式化:
          [A | b] → \\begin{array}{ccc|c} ... \\end{array}
        """
        if not left or not right:
            return ""

        n_cols_left = len(left[0]) if left else 0
        col_spec = "c" * n_cols_left + "|" + "c"

        rows_latex = []
        for l_row, r_row in zip(left, right):
            elements = [str(e) for e in l_row] + [str(e) for e in r_row]
            rows_latex.append(" & ".join(elements))

        body = " \\\\\n".join(rows_latex)
        return f"\\begin{{{env}}}{{{col_spec}}}\n{body}\n\\end{{{env}}}"

    def format_determinant(
        self,
        data: Sequence[Sequence] | None = None,
    ) -> str:
        """
        行列式格式化:
          format_determinant([[a,b],[c,d]])
          → \\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}
        """
        return self.format_matrix(data, env="vmatrix")

    # ═══════════════════════════════════════════════════════════
    # 5. 便捷函数
    # ═══════════════════════════════════════════════════════════

    def format_equation(
        self,
        lhs: str,
        rhs: str,
        aligned: bool = False,
        label: str = "",
    ) -> str:
        """
        等式格式化:
          format_equation("f(x)", "2x+3")
          → "f(x) = 2x+3"

          format_equation("f(x)", "2x+3", aligned=True)
          → "f(x) &= 2x+3"
        """
        if aligned:
            eq_str = f"{lhs} &= {rhs}"
        else:
            eq_str = f"{lhs} = {rhs}"

        if label:
            return f"\\tag{{{label}}} {eq_str}"
        return eq_str

    def format_system(
        self,
        equations: list[tuple[str, str]],
        label: str = "",
    ) -> str:
        """
        方程组格式化:
          format_system([("2x+y","5"),("x-y","1")])
          → \\begin{cases} 2x+y = 5 \\\\ x-y = 1 \\end{cases}
        """
        rows = []
        for lhs, rhs in equations:
            rows.append(f"  {lhs} &= {rhs}")
        body = " \\\\\n".join(rows)

        result = f"\\begin{{cases}}\n{body}\n\\end{{cases}}"
        if label:
            result = f"{label}: " + result
        return result

    def format_piecewise(
        self,
        branches: list[tuple[str, str]],
        label: str = "",
    ) -> str:
        """
        分段函数格式化:
          format_piecewise([("x^2","x>0"),("0","x\\leq 0")])
          → \\begin{cases} x^2, & x > 0 \\\\ 0, & x \\leq 0 \\end{cases}
        """
        rows = []
        for expr, condition in branches:
            rows.append(f"  {expr}, & {condition}")
        body = " \\\\\n".join(rows)

        result = f"\\begin{{cases}}\n{body}\n\\end{{cases}}"
        if label:
            result = f"{label} = " + result
        return result


_default_formatter = MathFormatter()


def normalize(latex: str) -> str:
    return _default_formatter.normalize(latex)


def auto_display(latex: str) -> str:
    return _default_formatter.auto_display(latex)


def break_long_formula(latex: str) -> str:
    return _default_formatter.break_long_formula(latex)


def format_matrix(
    data: Sequence[Sequence] | None = None,
    env: str = "",
    label: str = "",
) -> str:
    return _default_formatter.format_matrix(data, env=env, label=label)


def format_vector(
    data: Sequence | None = None,
    env: str = "pmatrix",
    is_column: bool = True,
) -> str:
    return _default_formatter.format_vector(data, env=env, is_column=is_column)


def format_determinant(
    data: Sequence[Sequence] | None = None,
) -> str:
    return _default_formatter.format_determinant(data)


def format_equation(lhs: str, rhs: str, aligned: bool = False, label: str = "") -> str:
    return _default_formatter.format_equation(lhs, rhs, aligned=aligned, label=label)


def format_system(equations: list[tuple[str, str]], label: str = "") -> str:
    return _default_formatter.format_system(equations, label=label)


def format_piecewise(branches: list[tuple[str, str]], label: str = "") -> str:
    return _default_formatter.format_piecewise(branches, label=label)
