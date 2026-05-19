"""proof_renderer.py — 证明题渲染器"""

import streamlit as st
from math_sanitizer import safe_latex
from latex_utils import split_latex_text, render_ast


def render_proof(steps: list[dict]) -> None:
    """
    渲染证明题解答。

    证明结构: 已知 → 要证 → 证明过程 → 得证

    Args:
        steps: [
            {"type": "given", "content": "已知 f(x) 在 [a,b] 连续"},
            {"type": "to_prove", "content": "求证: 存在 ξ 使得 f(ξ)=0"},
            {"type": "proof_step", "content": "由介值定理...", "latex": "f(a)f(b)<0"},
            {"type": "qed", "content": "得证"},
        ]
    """
    if not steps:
        return

    for step in steps:
        t = step.get("type", "proof_step")
        content = step.get("content", "")
        latex = step.get("latex", "")

        if t == "given":
            st.markdown("**📋 已知**")
            if content:
                try:
                    render_ast(split_latex_text(content))
                except Exception:
                    st.markdown(content)

        elif t == "to_prove":
            st.markdown("**🎯 要证**")
            if content:
                try:
                    render_ast(split_latex_text(content))
                except Exception:
                    st.markdown(content)

        elif t == "proof_step":
            if content:
                try:
                    render_ast(split_latex_text(content))
                except Exception:
                    st.markdown(content)
            if latex:
                try:
                    safe = safe_latex(f"${latex}$")
                    if safe.startswith("$") and safe.endswith("$"):
                        safe = safe[1:-1]
                    st.latex(safe)
                except Exception:
                    st.text(latex[:500])

        elif t == "qed":
            st.markdown("**∎ 得证**")
            if content:
                st.markdown(content)

        # 步骤间留空
        st.markdown("")


def render_proof_from_text(text: str) -> None:
    """
    从混合文本渲染证明。

    自动检测 "证明"、"即证"、"得证" 等关键词并结构化显示。
    """
    if not text:
        return

    import re

    # 简单分段：按 "证明"/"解"/"即证"/"得证" 分割
    parts = re.split(r"(?=(?:证明|解|即证|得证)[：:\s])", text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("证明") or part.startswith("解"):
            st.markdown("**📋 证明**")
            body = re.sub(r"^(?:证明|解)[：:\s]*", "", part)
            try:
                render_ast(split_latex_text(body))
            except Exception:
                st.markdown(body)

        elif part.startswith("即证") or part.startswith("要证"):
            st.markdown("**🎯 即证**")
            body = re.sub(r"^(?:即证|要证)[：:\s]*", "", part)
            try:
                render_ast(split_latex_text(body))
            except Exception:
                st.markdown(body)

        elif part.startswith("得证") or "证毕" in part:
            st.markdown("**∎ 得证**")

        else:
            try:
                render_ast(split_latex_text(part))
            except Exception:
                st.markdown(part)
