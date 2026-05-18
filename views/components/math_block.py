"""MathBlock — 数学公式渲染组件

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  render_math_block(expr, label=None, display=True)

    expr:    LaTeX 表达式（不含 $ 分隔符）
    label:   可选标签（如 "解", "答案"）
    display: True → st.latex / False → inline

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from rendering.math_formatter import MathFormatter


_fmt = MathFormatter()


def render_math_block(
    expr: str,
    label: Optional[str] = None,
    display: bool = True,
    normalize: bool = True,
) -> None:
    """
    渲染数学公式.

    Args:
        expr:      LaTeX 表达式（不含 $ 分隔符）
        label:     可选标签（如 "解", "答案"）
        display:   True → 居中显示 / False → 行内
        normalize: 是否通过 MathFormatter 正规化
    """
    if not expr:
        return

    if normalize:
        expr = _fmt.normalize(expr)

    expr = _strip_dollars(expr)

    if label:
        st.markdown(f"**{label}**")

    if display:
        st.latex(expr)
    else:
        st.markdown(f"${expr}$")


def render_math_blocks(
    exprs: list[str],
    labels: Optional[list[str]] = None,
    display: bool = True,
) -> None:
    """批量渲染数学公式."""
    for i, expr in enumerate(exprs):
        label = labels[i] if labels and i < len(labels) else None
        render_math_block(expr, label=label, display=display)


def render_labeled_math(label: str, expr: str) -> None:
    """渲染带标签的数学公式（标签和公式在同一行）."""
    if not expr:
        return
    expr = _strip_dollars(_fmt.normalize(expr))
    st.markdown(f"**{label}** &nbsp; ${expr}$")


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s
