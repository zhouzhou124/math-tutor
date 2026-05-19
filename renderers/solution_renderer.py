"""solution_renderer.py — 解答步骤渲染器"""

import streamlit as st
from latex_utils import split_latex_text, render_ast, sanitize_latex_for_render

_OP_COLORS = {
    "classify": ("识别题型", "#6b7280"),
    "recall": ("回忆定理", "#2563eb"),
    "substitute": ("代入", "#7c3aed"),
    "simplify": ("化简", "#059669"),
    "expand": ("展开", "#059669"),
    "factor": ("因式分解", "#059669"),
    "differentiate": ("求导", "#d97706"),
    "integrate": ("积分", "#d97706"),
    "solve": ("求解", "#dc2626"),
    "evaluate": ("计算", "#dc2626"),
    "apply_theorem": ("应用定理", "#2563eb"),
    "transform": ("变换", "#7c3aed"),
    "conclude": ("结论", "#0891b2"),
    "check": ("验证", "#0891b2"),
}


def render_solution_steps(steps: list[dict], final_answer: str = "") -> None:
    """
    渲染解答步骤列表。

    Args:
        steps: [
            {"label": "步骤1", "text": "识别题型", "latex": "\\lim...", "operation": "classify"},
            ...
        ]
        final_answer: 最终答案 LaTeX 表达式
    """
    if not steps:
        return

    for i, step in enumerate(steps):
        label = step.get("label", f"步骤{i+1}")
        text = step.get("text", "")
        latex = step.get("latex", "")
        operation = step.get("operation", "")

        # 步骤标题 + 操作徽章
        op_label, op_color = _OP_COLORS.get(operation, ("", ""))
        if op_label:
            st.markdown(
                f"**{label}** &nbsp; "
                f"<span style='color:{op_color};border:1px solid {op_color};"
                f"border-radius:4px;padding:1px 8px;font-size:0.8em;'>{op_label}</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{label}**")

        # 步骤文本
        if text:
            try:
                render_ast(split_latex_text(text))
            except Exception:
                st.markdown(text)

        # 步骤公式
        if latex:
            try:
                safe = sanitize_latex_for_render(latex)
                st.latex(safe)
            except Exception:
                render_ast(split_latex_text(latex))

        # 步骤间分隔
        if i < len(steps) - 1:
            st.markdown("---")

    # 最终答案
    if final_answer:
        st.markdown("---")
        st.markdown("**📌 答案**")
        try:
            safe = sanitize_latex_for_render(final_answer)
            st.latex(f"\\boxed{{{safe}}}")
        except Exception:
            render_ast(split_latex_text(final_answer))
