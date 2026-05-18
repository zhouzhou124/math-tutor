"""Streamlit Exporter — Document → Streamlit 组件渲染

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  StreamlitExporter.export(document) → None (直接渲染到 Streamlit)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from rendering.document_ast import (
    BlockType,
    Document,
    DocumentNode,
    StepBlock,
    MatrixBlock,
    WarningBlock,
    ProofBlock,
)
from rendering.math_formatter import MathFormatter


_fmt = MathFormatter()


class StreamlitExporter:
    """Document → Streamlit 组件渲染导出器.

    与 LayoutEngine 不同，此导出器直接调用 st.* API，
    利用 Streamlit 原生组件（st.latex, st.error, st.warning 等）
    获得最佳交互体验。
    """

    def export(self, document: Document) -> None:
        """将 Document 渲染到 Streamlit."""
        import streamlit as st

        if document.title:
            st.title(document.title)

        for node in document.nodes:
            self._render_node(node)

    def export_nodes(self, nodes: list[DocumentNode]) -> None:
        """将 DocumentNode 列表渲染到 Streamlit."""
        for node in nodes:
            self._render_node(node)

    def _render_node(self, node: DocumentNode) -> None:
        import streamlit as st

        if node.type == BlockType.TITLE:
            st.subheader(str(node.content))

        elif node.type == BlockType.PARAGRAPH:
            self._render_paragraph(node)

        elif node.type == BlockType.DISPLAY_MATH:
            content = _strip_dollars(_fmt.normalize(str(node.content)))
            st.latex(content)

        elif node.type == BlockType.MATRIX:
            if isinstance(node.content, MatrixBlock):
                self._render_matrix(node.content)

        elif node.type == BlockType.WARNING:
            if isinstance(node.content, WarningBlock):
                self._render_warning(node)

        elif node.type == BlockType.OBLIGATION:
            self._render_obligation(node)

        elif node.type == BlockType.STEP:
            if isinstance(node.content, StepBlock):
                from views.components.step_card import render_step
                render_step(node.content)

        elif node.type == BlockType.PROOF:
            if isinstance(node.content, ProofBlock):
                from views.components.proof_box import render_obligation
                render_obligation(node.content)

        elif node.type == BlockType.CODE:
            st.code(str(node.content))

        elif node.type == BlockType.TABLE:
            st.markdown(str(node.content))

        else:
            st.markdown(str(node.content))

    def _render_paragraph(self, node: DocumentNode) -> None:
        import streamlit as st

        role = node.metadata.get("role", "")
        content = str(node.content)

        if role == "error_header":
            st.markdown(f"**{content}**")
        elif role == "error_explanation":
            st.markdown(content)
        elif role == "error_suggestion":
            st.info(content)
        elif role == "error_correction":
            st.success(content)
        elif role == "error_concept":
            st.caption(content)
        elif role == "obligation_item":
            st.markdown(content)
        elif role == "obligation_reason":
            st.caption(content)
        elif role == "obligation_summary":
            st.caption(content)
        else:
            st.markdown(content)

    def _render_matrix(self, mat: MatrixBlock) -> None:
        import streamlit as st

        label = mat.label or ""
        rows = mat.rows
        env = mat.environment or "pmatrix"

        n = len(rows)
        cols = max(len(r) for r in rows) if rows else 0

        latex_rows = []
        for row in rows:
            padded = row + ["0"] * (cols - len(row))
            latex_rows.append(" & ".join(str(c) for c in padded))
        body = " \\\\ ".join(latex_rows)

        expr = f"\\begin{{{env}}} {body} \\end{{{env}}}"
        if label:
            expr = f"{label} = {expr}"

        st.latex(expr)

    def _render_warning(self, node: DocumentNode) -> None:
        import streamlit as st

        if isinstance(node.content, WarningBlock):
            w = node.content
            icon = node.metadata.get("icon", "")
            if not icon:
                icon = "🚨" if w.is_critical else "❌" if w.is_error else "⚠️" if w.is_warning else "ℹ️"
            msg = f"{icon} {w.message}"
            if w.is_critical or w.is_error:
                st.error(msg)
            elif w.is_warning:
                st.warning(msg)
            else:
                st.info(msg)
            if w.suggestion:
                st.caption(f"💡 {w.suggestion}")

    def _render_obligation(self, node: DocumentNode) -> None:
        import streamlit as st

        role = node.metadata.get("role", "")
        content = str(node.content)
        if role == "obligation_header":
            st.markdown(f"**{content}**")
        elif role == "obligation_summary":
            st.caption(content)
        else:
            st.markdown(content)


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s
