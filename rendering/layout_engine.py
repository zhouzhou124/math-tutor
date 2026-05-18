"""
Layout Engine — 数学布局引擎

═══════════════════════════════════════════════════════════════
职责
═══════════════════════════════════════════════════════════════

  将 Document AST 转换为目标格式。

  输入:  Document (Document AST)
  输出:  LayoutResult (markdown / latex / html 字符串)

  三种布局器:
    MarkdownLayout — Markdown + KaTeX ($...$ / $$...$$)
    LatexLayout   — 纯 LaTeX 文档
    HtmlLayout    — HTML + MathJax

  不关心:
    - 语义 (由 Semantic Renderer 负责)
    - 数据来源 (MathIR / WorldState / dict)
    - Streamlit 组件

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rendering.document_ast import (
    BlockType,
    MathDisplayStyle,
    DocumentNode,
    Document,
    StepBlock,
    ProofBlock,
    MatrixBlock,
    EquationBlock,
    WarningBlock,
    TableBlock,
)
from rendering.math_formatter import MathFormatter

from operations import op_display_cn as _op_display_cn


def _OP_DISPLAY(op_value: str) -> str:
    return _op_display_cn(op_value)

_LEGALITY_SYMBOL = {
    "valid": "✓",
    "suspect": "⚠",
    "invalid": "✗",
    "unknown": "",
}


@dataclass(frozen=True)
class LayoutResult:
    content: str = ""
    format: str = "markdown"
    metadata: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.content.strip()

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1

    def __str__(self) -> str:
        return self.content


class MarkdownLayout:
    """
    Markdown 布局器 — Document AST → Markdown + KaTeX

    规则:
      - TITLE       → # / ## 标题
      - PARAGRAPH   → 段落文本
      - INLINE_MATH → $...$
      - DISPLAY_MATH → $$...$$
      - STEP        → 带操作徽章的步骤块
      - WARNING     → > ⚠ 引用块
      - PROOF       → 证明环境
      - MATRIX      → $$ \\begin{pmatrix} ... $$
      - EQUATION    → $$ ... = ... $$
      - LIST        → - 列表
      - TABLE       → Markdown 表格
      - DIVIDER     → ---
      - FINAL_ANSWER → **📌 答案** + $$ \\boxed{...} $$
    """

    def __init__(self, math_formatter: MathFormatter = None):
        self._fmt = math_formatter or MathFormatter()

    def layout(self, doc: Document) -> LayoutResult:
        parts = []

        if doc.title:
            parts.append(f"# {doc.title}")
            parts.append("")

        for node in doc.nodes:
            block = self._layout_node(node)
            if block:
                parts.append(block)

        content = "\n\n".join(parts)
        return LayoutResult(content=content, format="markdown")

    def _layout_node(self, node: DocumentNode) -> str:
        handler = {
            BlockType.TITLE: self._layout_title,
            BlockType.PARAGRAPH: self._layout_paragraph,
            BlockType.INLINE_MATH: self._layout_inline_math,
            BlockType.DISPLAY_MATH: self._layout_display_math,
            BlockType.STEP: self._layout_step,
            BlockType.WARNING: self._layout_warning,
            BlockType.PROOF: self._layout_proof,
            BlockType.MATRIX: self._layout_matrix,
            BlockType.EQUATION: self._layout_equation,
            BlockType.LIST: self._layout_list,
            BlockType.TABLE: self._layout_table,
            BlockType.DIVIDER: self._layout_divider,
            BlockType.CODE: self._layout_code,
            BlockType.CASE_BRANCH: self._layout_case_branch,
            BlockType.FINAL_ANSWER: self._layout_final_answer,
            BlockType.OBLIGATION: self._layout_obligation,
        }.get(node.type)

        if handler:
            return handler(node)
        return ""

    def _layout_title(self, node: DocumentNode) -> str:
        return f"## {node.content}"

    def _layout_paragraph(self, node: DocumentNode) -> str:
        return str(node.content) if node.content else ""

    def _layout_inline_math(self, node: DocumentNode) -> str:
        return f"${node.content}$"

    def _layout_display_math(self, node: DocumentNode) -> str:
        formatted = self._fmt.normalize(str(node.content))
        role = node.metadata.get("role", "")
        prefix = node.metadata.get("prefix", "")
        suffix = node.metadata.get("suffix", "")
        if not formatted.startswith("$$"):
            formatted = self._fmt.auto_display(formatted)
            if formatted.startswith("$$"):
                if prefix or suffix:
                    return f"{prefix}{formatted}{suffix}"
                return formatted
        result = f"$$\n{formatted}\n$$"
        if prefix or suffix:
            return f"{prefix}{result}{suffix}"
        return result

    def _layout_step(self, node: DocumentNode) -> str:
        if not isinstance(node.content, StepBlock):
            return str(node.content) if node.content else ""

        step = node.content
        parts = []

        header_parts = [f"**{step.title}**"]

        op_name = _OP_DISPLAY(step.operation) if step.operation else ""
        if op_name:
            header_parts.append(f"`{op_name}`")

        legality_sym = _LEGALITY_SYMBOL.get(step.legality, "")
        if legality_sym:
            header_parts.append(legality_sym)

        parts.append(" ".join(header_parts))

        if step.explanation:
            parts.append(step.explanation)

        if step.input_expr:
            parts.append(f"输入: ${step.input_expr}$")

        if step.output_expr:
            parts.append(f"$$\n{step.output_expr}\n$$")

        if step.theorem_used:
            parts.append(f"*应用定理: {step.theorem_used}*")

        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)

        return "\n\n".join(parts)

    def _layout_warning(self, node: DocumentNode) -> str:
        if isinstance(node.content, WarningBlock):
            w = node.content
            icon = node.metadata.get("icon", "")
            if not icon:
                icon = "🚨" if w.is_critical else "❌" if w.is_error else "⚠️" if w.is_warning else "ℹ️"
            lines = [f"> {icon} {w.message}"]
            if w.suggestion:
                lines.append(f"> 💡 {w.suggestion}")
            return "\n".join(lines)
        return f"> ⚠️ {node.content}"

    def _layout_proof(self, node: DocumentNode) -> str:
        if isinstance(node.content, ProofBlock):
            p = node.content
            parts = [f"**证明** (策略: {p.strategy})"]
            if p.goal:
                parts.append(f"目标: {p.goal}")
            if p.assumptions:
                parts.append("假设:")
                for a in p.assumptions:
                    parts.append(f"  - {a}")
            if p.pending_obligations:
                parts.append("待证:")
                for o in p.pending_obligations:
                    parts.append(f"  - {o}")
            return "\n".join(parts)
        return f"**证明**: {node.content}"

    def _layout_matrix(self, node: DocumentNode) -> str:
        if isinstance(node.content, MatrixBlock):
            m = node.content
            rows = [list(row) for row in m.rows]
            env = m.environment or "pmatrix"
            label = m.label or ""
            formatted = self._fmt.format_matrix(rows, env=env, label=label)
            return f"$$\n{formatted}\n$$"
        return str(node.content)

    def _layout_equation(self, node: DocumentNode) -> str:
        if isinstance(node.content, EquationBlock):
            eq = node.content
            label = f"\\tag{{{eq.label}}}" if eq.label else ""
            eq_str = f"{eq.lhs} = {eq.rhs}{label}"
            formatted = self._fmt.normalize(eq_str)
            if self._fmt._has_eq_chain(formatted) and len(formatted) > self._fmt.config.formula_line_width:
                formatted = self._fmt.break_long_formula(formatted)
            return f"$$\n{formatted}\n$$"
        return f"$$\n{node.content}\n$$"

    def _layout_list(self, node: DocumentNode) -> str:
        if isinstance(node.content, (list, tuple)):
            return "\n".join(f"- {item}" for item in node.content)
        return f"- {node.content}"

    def _layout_table(self, node: DocumentNode) -> str:
        if isinstance(node.content, TableBlock):
            t = node.content
            if not t.headers and not t.rows:
                return ""
            parts = []
            if t.headers:
                parts.append("| " + " | ".join(t.headers) + " |")
                parts.append("| " + " | ".join("---" for _ in t.headers) + " |")
            for row in t.rows:
                parts.append("| " + " | ".join(str(c) for c in row) + " |")
            if t.caption:
                parts.append(f"*{t.caption}*")
            return "\n".join(parts)
        return str(node.content)

    def _layout_divider(self, node: DocumentNode) -> str:
        return "---"

    def _layout_code(self, node: DocumentNode) -> str:
        lang = node.metadata.get("language", "")
        return f"```{lang}\n{node.content}\n```"

    def _layout_case_branch(self, node: DocumentNode) -> str:
        label = node.metadata.get("case_label", "")
        parts = [f"**情况: {label}**"] if label else []
        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)
        return "\n\n".join(parts)

    def _layout_final_answer(self, node: DocumentNode) -> str:
        highlight = node.metadata.get("highlight", True)
        content = str(node.content) if node.content else ""
        if not content:
            return ""
        if highlight:
            return f"**📌 答案**\n\n$$\n\\boxed{{{content}}}\n$$"
        return f"**答案**: ${content}$"

    def _layout_obligation(self, node: DocumentNode) -> str:
        role = node.metadata.get("role", "")
        if role == "obligation_header":
            return f"> {node.content}"
        if role == "obligation_summary":
            return f"> {node.content}"
        return f"> 📋 {node.content}"


class LatexLayout:
    """
    LaTeX 布局器 — Document AST → 纯 LaTeX 文档
    """

    def __init__(self, math_formatter: MathFormatter = None):
        self._fmt = math_formatter or MathFormatter()

    def layout(self, doc: Document) -> LayoutResult:
        parts = []

        if doc.title:
            parts.append(f"\\section{{{doc.title}}}")

        for node in doc.nodes:
            block = self._layout_node(node)
            if block:
                parts.append(block)

        content = "\n\n".join(parts)
        return LayoutResult(content=content, format="latex")

    def _layout_node(self, node: DocumentNode) -> str:
        handler = {
            BlockType.TITLE: self._layout_title,
            BlockType.PARAGRAPH: self._layout_paragraph,
            BlockType.INLINE_MATH: self._layout_inline_math,
            BlockType.DISPLAY_MATH: self._layout_display_math,
            BlockType.STEP: self._layout_step,
            BlockType.WARNING: self._layout_warning,
            BlockType.PROOF: self._layout_proof,
            BlockType.MATRIX: self._layout_matrix,
            BlockType.EQUATION: self._layout_equation,
            BlockType.LIST: self._layout_list,
            BlockType.TABLE: self._layout_table,
            BlockType.DIVIDER: self._layout_divider,
            BlockType.CODE: self._layout_code,
            BlockType.CASE_BRANCH: self._layout_case_branch,
            BlockType.FINAL_ANSWER: self._layout_final_answer,
            BlockType.OBLIGATION: self._layout_obligation,
        }.get(node.type)

        if handler:
            return handler(node)
        return ""

    def _layout_title(self, node: DocumentNode) -> str:
        return f"\\subsection{{{node.content}}}"

    def _layout_paragraph(self, node: DocumentNode) -> str:
        return str(node.content)

    def _layout_inline_math(self, node: DocumentNode) -> str:
        return f"${node.content}$"

    def _layout_display_math(self, node: DocumentNode) -> str:
        formatted = self._fmt.normalize(str(node.content))
        return f"\\[\n{formatted}\n\\]"

    def _layout_step(self, node: DocumentNode) -> str:
        if not isinstance(node.content, StepBlock):
            return str(node.content) if node.content else ""

        step = node.content
        parts = []

        op_name = _OP_DISPLAY(step.operation) if step.operation else ""
        title = step.title
        if op_name:
            title += f" ({op_name})"

        parts.append(f"\\textbf{{{title}}}")

        if step.explanation:
            parts.append(step.explanation)

        if step.input_expr:
            parts.append(f"输入: ${step.input_expr}$")

        if step.output_expr:
            parts.append(f"\\[\n{step.output_expr}\n\\]")

        if step.theorem_used:
            parts.append(f"\\textit{{应用定理: {step.theorem_used}}}")

        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)

        return "\n\n".join(parts)

    def _layout_warning(self, node: DocumentNode) -> str:
        if isinstance(node.content, WarningBlock):
            w = node.content
            icon = node.metadata.get("icon", "")
            if not icon:
                icon = "🚨" if w.is_critical else "❌" if w.is_error else "⚠️" if w.is_warning else "ℹ️"
            return f"\\textit{{{icon} {w.message}}}"
        return f"\\textit{{⚠️ {node.content}}}"

    def _layout_proof(self, node: DocumentNode) -> str:
        if isinstance(node.content, ProofBlock):
            p = node.content
            parts = [f"\\begin{{proof}}"]
            if p.goal:
                parts.append(f"目标: {p.goal}")
            parts.append(f"\\end{{proof}}")
            return "\n".join(parts)
        return f"\\begin{{proof}}\n{node.content}\n\\end{{proof}}"

    def _layout_matrix(self, node: DocumentNode) -> str:
        if isinstance(node.content, MatrixBlock):
            m = node.content
            rows = [list(row) for row in m.rows]
            env = m.environment or "pmatrix"
            formatted = self._fmt.format_matrix(rows, env=env, label=m.label or "")
            return f"\\[\n{formatted}\n\\]"
        return str(node.content)

    def _layout_equation(self, node: DocumentNode) -> str:
        if isinstance(node.content, EquationBlock):
            eq = node.content
            label = f"\\label{{{eq.label}}}" if eq.label else ""
            return f"\\begin{{equation}}\n{eq.lhs} = {eq.rhs}{label}\n\\end{{equation}}"
        return f"\\[\n{node.content}\n\\]"

    def _layout_list(self, node: DocumentNode) -> str:
        if isinstance(node.content, (list, tuple)):
            items = [f"  \\item {item}" for item in node.content]
            return "\\begin{itemize}\n" + "\n".join(items) + "\n\\end{itemize}"
        return f"\\begin{{itemize}}\n  \\item {node.content}\n\\end{{itemize}}"

    def _layout_table(self, node: DocumentNode) -> str:
        if isinstance(node.content, TableBlock):
            t = node.content
            if not t.headers and not t.rows:
                return ""
            ncols = len(t.headers) if t.headers else len(t.rows[0]) if t.rows else 0
            col_spec = "|" + "|".join(["c"] * ncols) + "|"
            parts = [f"\\begin{{tabular}}{{{col_spec}}}"]
            parts.append("\\hline")
            if t.headers:
                parts.append(" & ".join(t.headers) + " \\\\")
                parts.append("\\hline")
            for row in t.rows:
                parts.append(" & ".join(str(c) for c in row) + " \\\\")
            parts.append("\\hline")
            parts.append("\\end{tabular}")
            return "\n".join(parts)
        return str(node.content)

    def _layout_divider(self, node: DocumentNode) -> str:
        return "\\noindent\\rule{\\textwidth}{0.4pt}"

    def _layout_code(self, node: DocumentNode) -> str:
        return f"\\begin{{verbatim}}\n{node.content}\n\\end{{verbatim}}"

    def _layout_case_branch(self, node: DocumentNode) -> str:
        label = node.metadata.get("case_label", "")
        parts = [f"\\textbf{{情况: {label}}}"] if label else []
        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)
        return "\n\n".join(parts)

    def _layout_final_answer(self, node: DocumentNode) -> str:
        content = str(node.content) if node.content else ""
        if not content:
            return ""
        return f"\\[\n\\boxed{{{content}}}\n\\]"

    def _layout_obligation(self, node: DocumentNode) -> str:
        role = node.metadata.get("role", "")
        if role == "obligation_header":
            return f"\\textbf{{{node.content}}}"
        if role == "obligation_summary":
            return f"\\textit{{{node.content}}}"
        return f"\\textit{{📋 {node.content}}}"


class HtmlLayout:
    """
    HTML 布局器 — Document AST → HTML + MathJax
    """

    def __init__(self, math_formatter: MathFormatter = None):
        self._fmt = math_formatter or MathFormatter()

    def layout(self, doc: Document) -> LayoutResult:
        parts = []

        if doc.title:
            parts.append(f"<h1>{doc.title}</h1>")

        for node in doc.nodes:
            block = self._layout_node(node)
            if block:
                parts.append(block)

        content = "\n".join(parts)
        return LayoutResult(content=content, format="html")

    def _layout_node(self, node: DocumentNode) -> str:
        handler = {
            BlockType.TITLE: self._layout_title,
            BlockType.PARAGRAPH: self._layout_paragraph,
            BlockType.INLINE_MATH: self._layout_inline_math,
            BlockType.DISPLAY_MATH: self._layout_display_math,
            BlockType.STEP: self._layout_step,
            BlockType.WARNING: self._layout_warning,
            BlockType.PROOF: self._layout_proof,
            BlockType.MATRIX: self._layout_matrix,
            BlockType.EQUATION: self._layout_equation,
            BlockType.LIST: self._layout_list,
            BlockType.TABLE: self._layout_table,
            BlockType.DIVIDER: self._layout_divider,
            BlockType.CODE: self._layout_code,
            BlockType.CASE_BRANCH: self._layout_case_branch,
            BlockType.FINAL_ANSWER: self._layout_final_answer,
            BlockType.OBLIGATION: self._layout_obligation,
        }.get(node.type)

        if handler:
            return handler(node)
        return ""

    def _layout_title(self, node: DocumentNode) -> str:
        return f"<h2>{node.content}</h2>"

    def _layout_paragraph(self, node: DocumentNode) -> str:
        return f"<p>{node.content}</p>"

    def _layout_inline_math(self, node: DocumentNode) -> str:
        return f"\\({node.content}\\)"

    def _layout_display_math(self, node: DocumentNode) -> str:
        formatted = self._fmt.normalize(str(node.content))
        return f"\\[\n{formatted}\n\\]"

    def _layout_step(self, node: DocumentNode) -> str:
        if not isinstance(node.content, StepBlock):
            return f"<p>{node.content}</p>" if node.content else ""

        step = node.content
        parts = []

        op_name = _OP_DISPLAY(step.operation) if step.operation else ""
        legality_class = {
            "valid": "step-valid",
            "suspect": "step-suspect",
            "invalid": "step-invalid",
            "unknown": "",
        }.get(step.legality, "")

        header = f'<div class="math-step {legality_class}">'
        title = step.title
        if op_name:
            title += f' <span class="op-badge">{op_name}</span>'
        parts.append(header)
        parts.append(f'<h3>{title}</h3>')

        if step.explanation:
            parts.append(f'<p class="step-explanation">{step.explanation}</p>')

        if step.input_expr:
            parts.append(f'<p>输入: \\({step.input_expr}\\)</p>')

        if step.output_expr:
            parts.append(f'\\[\n{step.output_expr}\n\\]')

        if step.theorem_used:
            parts.append(f'<p class="theorem"><em>应用定理: {step.theorem_used}</em></p>')

        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)

        parts.append('</div>')
        return "\n".join(parts)

    def _layout_warning(self, node: DocumentNode) -> str:
        if isinstance(node.content, WarningBlock):
            w = node.content
            icon = node.metadata.get("icon", "")
            if not icon:
                icon = "🚨" if w.is_critical else "❌" if w.is_error else "⚠️" if w.is_warning else "ℹ️"
            css_class = "critical" if w.is_critical else "error" if w.is_error else "warning" if w.is_warning else "info"
            msg = f'<div class="alert alert-{css_class}">{icon} {w.message}'
            if w.suggestion:
                msg += f'<br><em>💡 {w.suggestion}</em>'
            msg += '</div>'
            return msg
        return f'<div class="alert alert-warning">⚠️ {node.content}</div>'

    def _layout_proof(self, node: DocumentNode) -> str:
        if isinstance(node.content, ProofBlock):
            p = node.content
            parts = ['<div class="proof">']
            parts.append(f'<h3>证明 (策略: {p.strategy})</h3>')
            if p.goal:
                parts.append(f'<p>目标: {p.goal}</p>')
            if p.assumptions:
                parts.append('<ul>')
                for a in p.assumptions:
                    parts.append(f'<li>{a}</li>')
                parts.append('</ul>')
            parts.append('</div>')
            return "\n".join(parts)
        return f'<div class="proof"><p>{node.content}</p></div>'

    def _layout_matrix(self, node: DocumentNode) -> str:
        if isinstance(node.content, MatrixBlock):
            m = node.content
            rows = [list(row) for row in m.rows]
            env = m.environment or "pmatrix"
            formatted = self._fmt.format_matrix(rows, env=env, label=m.label or "")
            return f'\\[\n{formatted}\n\\]'
        return f'<p>{node.content}</p>'

    def _layout_equation(self, node: DocumentNode) -> str:
        if isinstance(node.content, EquationBlock):
            eq = node.content
            return f'\\[\n{eq.lhs} = {eq.rhs}\n\\]'
        return f'\\[\n{node.content}\n\\]'

    def _layout_list(self, node: DocumentNode) -> str:
        if isinstance(node.content, (list, tuple)):
            items = "".join(f"<li>{item}</li>" for item in node.content)
            return f"<ul>{items}</ul>"
        return f"<ul><li>{node.content}</li></ul>"

    def _layout_table(self, node: DocumentNode) -> str:
        if isinstance(node.content, TableBlock):
            t = node.content
            if not t.headers and not t.rows:
                return ""
            parts = ['<table>']
            if t.headers:
                parts.append('<thead><tr>')
                for h in t.headers:
                    parts.append(f'<th>{h}</th>')
                parts.append('</tr></thead>')
            if t.rows:
                parts.append('<tbody>')
                for row in t.rows:
                    parts.append('<tr>')
                    for c in row:
                        parts.append(f'<td>{c}</td>')
                    parts.append('</tr>')
                parts.append('</tbody>')
            parts.append('</table>')
            return "\n".join(parts)
        return f'<p>{node.content}</p>'

    def _layout_divider(self, node: DocumentNode) -> str:
        return "<hr>"

    def _layout_code(self, node: DocumentNode) -> str:
        lang = node.metadata.get("language", "")
        return f'<pre><code class="language-{lang}">{node.content}</code></pre>'

    def _layout_case_branch(self, node: DocumentNode) -> str:
        label = node.metadata.get("case_label", "")
        parts = [f'<div class="case-branch">']
        if label:
            parts.append(f'<h3>情况: {label}</h3>')
        for child in node.children:
            child_text = self._layout_node(child)
            if child_text:
                parts.append(child_text)
        parts.append('</div>')
        return "\n".join(parts)

    def _layout_final_answer(self, node: DocumentNode) -> str:
        content = str(node.content) if node.content else ""
        if not content:
            return ""
        highlight = node.metadata.get("highlight", True)
        if highlight:
            return f'<div class="final-answer"><h3>📌 答案</h3>\\[\n\\boxed{{{content}}}\n\\]</div>'
        return f'<p><strong>答案:</strong> \\({content}\\)</p>'

    def _layout_obligation(self, node: DocumentNode) -> str:
        role = node.metadata.get("role", "")
        if role == "obligation_header":
            return f'<div class="obligation-header">{node.content}</div>'
        if role == "obligation_summary":
            return f'<div class="obligation-summary">{node.content}</div>'
        return f'<div class="obligation">📋 {node.content}</div>'


class LayoutEngine:
    """
    布局引擎 — 根据格式选择布局器。
    """

    _LAYOUTS = {
        "markdown": MarkdownLayout,
        "latex": LatexLayout,
        "html": HtmlLayout,
    }

    def __init__(self, math_formatter: MathFormatter = None):
        self._fmt = math_formatter or MathFormatter()

    def layout(self, doc: Document, format: str = "markdown") -> LayoutResult:
        layout_cls = self._LAYOUTS.get(format)
        if not layout_cls:
            raise ValueError(f"Unknown format: {format}. Available: {list(self._LAYOUTS.keys())}")
        layouter = layout_cls(math_formatter=self._fmt)
        return layouter.layout(doc)

    def layout_all(self, doc: Document) -> dict[str, LayoutResult]:
        return {
            fmt: self.layout(doc, fmt)
            for fmt in self._LAYOUTS
        }
