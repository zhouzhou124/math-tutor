import streamlit as st
from typing import Optional, Sequence
from .render_ir import (
    RenderNode, RenderType, RenderTree,
    TextNode, InlineMathNode, BlockMathNode, AlignNode,
    MatrixNode, CasesNode, StepNode, ProofNode, WarningNode,
    ObligationNode, FinalAnswerNode, ListNode, TableNode,
    DividerNode, CodeNode, ExpanderNode, ColumnsNode, ContainerNode
)


class StreamlitRenderer:
    """
    将 Render IR 直接渲染到 Streamlit。

    管道:
      Document AST
        → DocumentToIRConverter
        → RenderTree (Render IR)
        → StreamlitRenderer (直接调用 st.*)
        → Streamlit UI

    关键特点:
      - 不走 Markdown 字符串（保留语义）
      - 直接调用 st.latex() / st.markdown() / st.expander()
      - metadata 原样传递（step_id, proof dependency, etc.）
    """

    def __init__(self, config: dict = None):
        self._config = config or {}

    def render(self, tree: RenderTree) -> None:
        """渲染整个 RenderTree"""
        self._render_node(tree.root)

    def render_node(self, node: RenderNode) -> None:
        """渲染单个节点"""
        self._render_node(node)

    def _render_node(self, node: RenderNode) -> None:
        handlers = {
            RenderType.TEXT: self._render_text,
            RenderType.INLINE_MATH: self._render_inline_math,
            RenderType.BLOCK_MATH: self._render_block_math,
            RenderType.ALIGN: self._render_align,
            RenderType.MATRIX: self._render_matrix,
            RenderType.CASES: self._render_cases,
            RenderType.STEP: self._render_step,
            RenderType.PROOF: self._render_proof,
            RenderType.WARNING: self._render_warning,
            RenderType.OBLIGATION: self._render_obligation,
            RenderType.FINAL_ANSWER: self._render_final_answer,
            RenderType.LIST: self._render_list,
            RenderType.TABLE: self._render_table,
            RenderType.DIVIDER: self._render_divider,
            RenderType.CODE: self._render_code,
            RenderType.EXPANDER: self._render_expander,
            RenderType.COLUMNS: self._render_columns,
            RenderType.CONTAINER: self._render_container,
        }

        handler = handlers.get(node.type, self._render_text)
        handler(node)

    def _render_text(self, node: RenderNode) -> None:
        if isinstance(node, TextNode):
            text = node.text
        else:
            text = str(node.content) if node.content else ""

        if text.strip():
            st.markdown(text, unsafe_allow_html=True)

    def _render_inline_math(self, node: RenderNode) -> None:
        if isinstance(node, InlineMathNode):
            latex = node.latex
        else:
            latex = str(node.content)

        if latex:
            st.markdown(f"${latex}$", unsafe_allow_html=True)

    def _render_block_math(self, node: RenderNode) -> None:
        if isinstance(node, BlockMathNode):
            latex = node.latex
        else:
            latex = str(node.content)

        if latex:
            st.latex(latex)

    def _render_align(self, node: RenderNode) -> None:
        if isinstance(node, AlignNode):
            latex = node.latex
        else:
            latex = str(node.content)

        if latex:
            if "\\begin{" not in latex:
                latex = f"\\begin{{aligned}}{latex}\\end{{aligned}}"
            st.latex(latex)

    def _render_matrix(self, node: RenderNode) -> None:
        if isinstance(node, MatrixNode):
            rows = node.rows
            env = node.environment or "pmatrix"
            label = node.label
        else:
            rows = node.content if isinstance(node.content, list) else []
            env = node.metadata.get("environment", "pmatrix")
            label = node.metadata.get("label", "")

        if not rows:
            return

        latex_rows = []
        for row in rows:
            if isinstance(row, (list, tuple)):
                latex_rows.append(" & ".join(str(cell) for cell in row))
            else:
                latex_rows.append(str(row))

        latex_content = " \\\\ ".join(latex_rows)
        latex = f"\\begin{{{env}}}{latex_content}\\end{{{env}}}"

        if label:
            latex += f"\\tag{{{label}}}"

        st.latex(latex)

    def _render_cases(self, node: RenderNode) -> None:
        if isinstance(node, CasesNode):
            latex = node.latex
        else:
            latex = str(node.content)

        if latex:
            if "\\begin{cases}" not in latex:
                st.latex(f"\\begin{{cases}}{latex}\\end{{cases}}")
            else:
                st.latex(latex)

    def _render_step(self, node: RenderNode) -> None:
        if not isinstance(node, StepNode):
            return

        with st.container(border=True):
            header_parts = []

            if node.title:
                header_parts.append(f"**{node.title}**")

            if node.metadata.get("operation"):
                op_name = _OP_DISPLAY(node.metadata.get("operation", ""))
                if op_name:
                    header_parts.append(f"`{op_name}`")

            legality = node.metadata.get("legality", "unknown")
            legality_sym = _LEGALITY_SYMBOL.get(legality, "")
            if legality_sym:
                header_parts.append(legality_sym)

            if header_parts:
                st.markdown(" ".join(header_parts))

            if node.metadata.get("explanation"):
                st.caption(node.metadata.get("explanation"))

            if node.metadata.get("input_expr"):
                st.markdown(f"输入: ${node.metadata.get('input_expr')}$")

            if node.metadata.get("output_expr"):
                st.latex(node.metadata.get("output_expr"))

            if node.metadata.get("theorem_used"):
                st.caption(f"*应用定理: {node.metadata.get('theorem_used')}*")

            for child in node.children:
                self._render_node(child)

    def _render_proof(self, node: RenderNode) -> None:
        if not isinstance(node, ProofNode):
            return

        strategy = node.strategy or "direct"
        goal = node.goal or ""
        assumptions = node.assumptions or ()
        pending = node.pending_obligations or ()

        st.markdown(f"**证明** (策略: {strategy})")

        if goal:
            st.markdown(f"**目标**: {goal}")

        if assumptions:
            st.markdown("**假设**:")
            for assumption in assumptions:
                st.markdown(f"  - {assumption}")

        if pending:
            st.markdown("**待证**:")
            for p in pending:
                st.markdown(f"  - {p}")

        for child in node.children:
            self._render_node(child)

    def _render_warning(self, node: RenderNode) -> None:
        if not isinstance(node, WarningNode):
            severity = node.metadata.get("severity", "warning")
            message = str(node.content)
            suggestion = node.metadata.get("suggestion", "")
        else:
            severity = node.severity
            message = node.message
            suggestion = node.suggestion

        icon_map = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️", "minor": "ℹ️"}
        icon = icon_map.get(severity, "⚠️")

        if severity == "critical":
            alert_type = "error"
        elif severity == "error":
            alert_type = "error"
        elif severity == "warning":
            alert_type = "warning"
        else:
            alert_type = "info"

        st.alert(f"{icon} {message}" + (f"\n\n💡 {suggestion}" if suggestion else ""), variant=alert_type)

    def _render_obligation(self, node: RenderNode) -> None:
        if isinstance(node, ObligationNode):
            text = node.text
            discharged = node.discharged
        else:
            text = str(node.content)
            discharged = node.metadata.get("discharged", False)

        icon = "✅" if discharged else "⏳"
        st.markdown(f"{icon} **{text}**" + (" (已证明)" if discharged else " (待证明)"))

    def _render_final_answer(self, node: RenderNode) -> None:
        if isinstance(node, FinalAnswerNode):
            answer = node.answer
            answer_expr = node.answer_expr
            is_boxed = node.is_boxed
        else:
            answer = str(node.content)
            answer_expr = node.metadata.get("answer_expr", "")
            is_boxed = node.metadata.get("is_boxed", True)

        st.markdown("**📌 答案**")

        if answer_expr:
            if is_boxed:
                st.latex(f"\\boxed{{{answer_expr}}}")
            else:
                st.latex(answer_expr)

        if answer and answer != answer_expr:
            st.markdown(answer)

    def _render_list(self, node: RenderNode) -> None:
        if isinstance(node, ListNode):
            items = node.items
        elif isinstance(node.content, (list, tuple)):
            items = tuple(str(item) for item in node.content)
        else:
            items = (str(node.content),)

        for item in items:
            st.markdown(f"- {item}")

    def _render_table(self, node: RenderNode) -> None:
        if isinstance(node, TableNode):
            headers = node.headers
            rows = node.rows
            caption = node.caption
        elif hasattr(node.content, "headers"):
            headers = tuple(node.content.headers)
            rows = tuple(tuple(r) for r in node.content.rows)
            caption = node.content.caption
        else:
            return

        if headers:
            cols = st.columns(len(headers))
            for i, h in enumerate(headers):
                cols[i].markdown(f"**{h}**")

        for row in rows:
            cols = st.columns(len(row) if rows else 0)
            for i, cell in enumerate(row):
                cols[i].markdown(str(cell))

        if caption:
            st.caption(caption)

    def _render_divider(self, node: RenderNode) -> None:
        st.divider()

    def _render_code(self, node: RenderNode) -> None:
        if isinstance(node, CodeNode):
            code = node.code
            language = node.language
        else:
            code = str(node.content)
            language = node.metadata.get("language", "")

        st.code(code, language=language)

    def _render_expander(self, node: RenderNode) -> None:
        if isinstance(node, ExpanderNode):
            label = node.label
            expanded = node.expanded
            child = node.child
        else:
            label = str(node.content)
            expanded = node.metadata.get("expanded", False)
            child = node.children[0] if node.children else None

        with st.expander(label, expanded=expanded):
            if child:
                self._render_node(child)

    def _render_columns(self, node: RenderNode) -> None:
        if isinstance(node, ColumnsNode):
            column_count = node.column_count
            columns = node.columns
        else:
            column_count = int(node.content) if node.content else 2
            columns = node.children

        if column_count <= 0:
            column_count = 2

        cols = st.columns(min(column_count, len(columns)) if columns else column_count)

        for i, col_node in enumerate(columns[:column_count]):
            with cols[i]:
                self._render_node(col_node)

    def _render_container(self, node: RenderNode) -> None:
        border = node.metadata.get("border", False)
        child = node.children[0] if node.children else None

        if border:
            with st.container(border=True):
                if child:
                    self._render_node(child)
        else:
            with st.container():
                if child:
                    self._render_node(child)


_OP_DISPLAY = {
    "matrix_multiply": "矩阵乘法",
    "matrix_add": "矩阵加法",
    "matrix_subtract": "矩阵减法",
    "transpose": "转置",
    "inverse": "求逆",
    "determinant": "行列式",
    "eigenvalue": "特征值",
    "rank": "矩阵秩",
    "substitute": "代入",
    "simplify": "化简",
    "expand": "展开",
    "factor": "因式分解",
    "solve": "求解",
    "differentiate": "求导",
    "integrate": "积分",
}

_LEGALITY_SYMBOL = {
    "legal": "✅",
    "illegal": "❌",
    "unknown": "❓",
}


def render_ir(tree: RenderTree) -> None:
    """便捷函数：渲染 RenderTree 到 Streamlit"""
    renderer = StreamlitRenderer()
    renderer.render(tree)


def render_ir_node(node: RenderNode) -> None:
    """便捷函数：渲染单个 RenderNode 到 Streamlit"""
    renderer = StreamlitRenderer()
    renderer.render_node(node)
