"""metadata_renderer.py — 题目元数据渲染器"""

import html
import streamlit as st


def chip(label: str, variant: str = "") -> str:
    """HTML chip 标签"""
    cls = "chip"
    if variant:
        cls += f" {variant}"
    return f'<span class="{cls}">{html.escape(str(label))}</span>'


_DIFF_COLORS = {
    "基础": "#22c55e",
    "中等": "#f59e0b",
    "较难": "#f97316",
    "难题": "#ef4444",
}


def render_question_meta(q: dict) -> None:
    """
    渲染题目元数据面板。

    显示: 知识点、难度、分值、年份/类别
    """
    knowledge_points = q.get("knowledge_points") or q.get("tags") or ["未标注"]
    difficulty = q.get("difficulty", "中等")
    score = q.get("score", "")
    year = q.get("year", "")
    category = q.get("category", "")
    mistakes = q.get("common_mistakes") or []

    # 知识点 chips
    kp_html = "".join(chip(str(kp), "chip-accent") for kp in knowledge_points[:6])

    # 难度 chip（带颜色）
    diff_color = _DIFF_COLORS.get(difficulty, "#6b7280")
    diff_html = (
        f'<span style="color:{diff_color};border:1px solid {diff_color};'
        f'border-radius:4px;padding:1px 8px;font-size:0.85em;">{html.escape(difficulty)}</span>'
    )

    # 分值/年份信息
    info_parts = []
    if year:
        info_parts.append(str(year))
    if category:
        info_parts.append(str(category))
    if score:
        info_parts.append(f"{score}分")
    info_text = " · ".join(info_parts)

    # 常见错误 chips
    mistake_html = ""
    if mistakes:
        mistake_html = "".join(chip(str(m), "chip-warning") for m in mistakes[:4])

    st.markdown(
        f"""
        <div class="meta-panel">
            <div class="meta-title">知识点</div>
            <div class="chip-row">{kp_html}</div>
            <div class="meta-title">难度 · 信息</div>
            <div class="chip-row">{diff_html} &nbsp; {html.escape(info_text)}</div>
            {f'<div class="meta-title">常见错误</div><div class="chip-row">{mistake_html}</div>' if mistake_html else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
