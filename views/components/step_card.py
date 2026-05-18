"""StepCard — 推理步骤卡片组件

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  render_step(step_block)         → StepBlock → 卡片
  render_step_dict(step_dict)     → dict → 卡片
  render_rich_step(rich_nodes)    → RichStep DocumentNode[] → 卡片

═══════════════════════════════════════════════════════════════
卡片布局
═══════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────┐
  │ 步骤二：验证变换组合                │
  │                                     │
  │ 📘 对矩阵 A 先进行：               │
  │   R₃ ← R₃ + R₁                     │
  │                                     │
  │ 对应初等矩阵：                      │
  │   P₂ = [1 0 1; 0 1 0; 0 0 1]      │
  │                                     │
  │ 因此：                              │
  │   P₂A = [...]                       │
  └─────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import streamlit as st

from rendering.document_ast import (
    BlockType,
    DocumentNode,
    StepBlock,
    MatrixBlock,
    WarningBlock,
    ProofBlock,
)
from rendering.rich_renderer import RichStepRenderer
from rendering.math_formatter import MathFormatter


_fmt = MathFormatter()
_rich = RichStepRenderer()


_LEGALITY_STYLE = {
    "valid": ("✅", "green"),
    "invalid": ("❌", "red"),
    "suspicious": ("⚠️", "orange"),
    "unknown": ("❓", "gray"),
}


def render_step(
    step: StepBlock,
    show_legality: bool = True,
    show_confidence: bool = False,
    collapsible: bool = False,
) -> None:
    """
    渲染 StepBlock 为卡片.

    Args:
        step:             StepBlock 实例
        show_legality:    是否显示合法性标记
        show_confidence:  是否显示置信度
        collapsible:      是否可折叠
    """
    if collapsible:
        container = st.expander(f"步骤 {step.step_id}: {step.title}", expanded=True)
    else:
        container = st.container()

    with container:
        _render_step_header(step, show_legality, show_confidence)
        _render_step_body(step)
        _render_step_obligations(step)


def render_step_dict(
    step: dict,
    show_legality: bool = True,
    collapsible: bool = False,
) -> None:
    """
    渲染 dict 步骤为卡片.

    支持的 dict 格式:
      {
        "step_id": "s1",
        "title": "验证变换组合",
        "operation": "row_reduce",
        "legality": "valid",
        "row_ops": ["R_3 <- R_3 + R_1"],
        "matrix_size": 3,
        "matrix_var": "A",
        "blocks": [{"type": "matrix", "rows": [[...]]}]
      }
    """
    row_ops = step.get("row_ops", [])
    matrix_size = step.get("matrix_size", 0)

    if row_ops and matrix_size:
        nodes = _rich.render_dict_step_rich(step, number=int(step.get("step_id", "1")[-1]) if step.get("step_id") else 1)
        _render_rich_nodes(nodes, step, show_legality, collapsible)
    else:
        sb = StepBlock(
            step_id=step.get("step_id", ""),
            title=step.get("title", ""),
            operation=step.get("operation", ""),
            legality=step.get("legality", "unknown"),
            input_expr=step.get("input_expr", ""),
            output_expr=step.get("output_expr", ""),
            proof_obligations=tuple(step.get("proof_obligations", [])),
        )
        render_step(sb, show_legality=show_legality, collapsible=collapsible)


def render_rich_step(
    nodes: list[DocumentNode],
    step_id: str = "",
    title: str = "",
    show_legality: bool = True,
    collapsible: bool = False,
) -> None:
    """渲染 RichStep DocumentNode[] 为卡片."""
    label = f"步骤 {step_id}" if step_id else "步骤"
    if title:
        label += f": {title}"

    if collapsible:
        container = st.expander(label, expanded=True)
    else:
        container = st.container()

    with container:
        for node in nodes:
            _render_node(node)


def render_steps(
    steps: Sequence[StepBlock],
    collapsible: bool = False,
) -> None:
    """批量渲染步骤列表."""
    for step in steps:
        render_step(step, collapsible=collapsible)


# ═══════════════════════════════════════════════════════════
# Internal
# ═══════════════════════════════════════════════════════════

def _render_step_header(step: StepBlock, show_legality: bool, show_confidence: bool) -> None:
    parts = []
    if step.step_id:
        parts.append(f"步骤 {step.step_id}")
    if step.title:
        parts.append(step.title)
    header = ": ".join(parts) if parts else "步骤"

    if show_legality and step.legality:
        icon, color = _LEGALITY_STYLE.get(step.legality, ("❓", "gray"))
        header += f" &nbsp; <span style='color:{color}'>{icon}</span>"

    st.markdown(f"**{header}**", unsafe_allow_html=True)

    if step.operation:
        st.caption(f"操作: {step.operation}")

    if show_confidence and hasattr(step, "confidence") and step.confidence is not None:
        st.progress(min(step.confidence, 1.0), text=f"置信度: {step.confidence:.0%}")


def _render_step_body(step: StepBlock) -> None:
    if step.input_expr:
        _render_expr("输入", step.input_expr)
    if step.output_expr:
        _render_expr("输出", step.output_expr)
    if step.children:
        for child in step.children:
            _render_node(child)


def _render_step_obligations(step: StepBlock) -> None:
    if not step.proof_obligations:
        return
    from views.components.proof_box import render_obligation
    render_obligation(step.proof_obligations, step_id=step.step_id)


def _render_expr(label: str, expr: str) -> None:
    if not expr:
        return
    normalized = _fmt.normalize(expr)
    normalized = _strip_dollars(normalized)
    st.markdown(f"**{label}**")
    st.latex(normalized)


def _render_node(node: DocumentNode) -> None:
    if node.type == BlockType.TITLE:
        st.subheader(str(node.content))

    elif node.type == BlockType.PARAGRAPH:
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

    elif node.type == BlockType.DISPLAY_MATH:
        content = _strip_dollars(_fmt.normalize(str(node.content)))
        st.latex(content)

    elif node.type == BlockType.MATRIX:
        if isinstance(node.content, MatrixBlock):
            _render_matrix(node.content)

    elif node.type == BlockType.WARNING:
        if isinstance(node.content, WarningBlock):
            _render_warning_inline(node)

    elif node.type == BlockType.OBLIGATION:
        content = str(node.content)
        role = node.metadata.get("role", "")
        if role == "obligation_header":
            st.markdown(f"**{content}**")
        elif role == "obligation_summary":
            st.caption(content)
        else:
            st.markdown(content)

    elif node.type == BlockType.STEP:
        if isinstance(node.content, StepBlock):
            render_step(node.content)

    elif node.type == BlockType.CODE:
        st.code(str(node.content))

    else:
        st.markdown(str(node.content))


def _render_matrix(mat: MatrixBlock) -> None:
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


def _render_warning_inline(node: DocumentNode) -> None:
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


def _render_rich_nodes(
    nodes: list[DocumentNode],
    step: dict,
    show_legality: bool,
    collapsible: bool,
) -> None:
    step_id = step.get("step_id", "")
    title = step.get("title", "")
    label = f"步骤 {step_id}" if step_id else "步骤"
    if title:
        label += f": {title}"

    if collapsible:
        container = st.expander(label, expanded=True)
    else:
        container = st.container()

    with container:
        if show_legality:
            legality = step.get("legality", "unknown")
            icon, color = _LEGALITY_STYLE.get(legality, ("❓", "gray"))
            st.markdown(f"<span style='color:{color}'>{icon}</span>", unsafe_allow_html=True)

        for node in nodes:
            _render_node(node)


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s
