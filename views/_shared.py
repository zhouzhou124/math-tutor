"""pages/_shared.py — 页面间共享的渲染辅助函数"""
import html
import streamlit as st


def chip(label: str, variant: str = "") -> str:
    """HTML chip 标签"""
    cls = "chip"
    if variant:
        cls += f" {variant}"
    return f'<span class="{cls}">{html.escape(label)}</span>'


def render_question_meta_panel(question: dict) -> None:
    """题目元数据面板：知识点、难度、常见错误"""
    knowledge_points = question.get("knowledge_points") or question.get("tags") or ["未标注"]
    mistakes = question.get("common_mistakes") or ["暂无记录"]
    difficulty = question.get("difficulty", "中等")

    kp_html = "".join(chip(str(kp), "chip-accent") for kp in knowledge_points[:6])
    mistake_html = "".join(chip(str(item), "chip-warning") for item in mistakes[:4])
    diff_html = chip(str(difficulty))

    st.markdown(
        f"""
        <div class="meta-panel">
            <div class="meta-title">知识点</div>
            <div class="chip-row">{kp_html}</div>
            <div class="meta-title">难度</div>
            <div class="chip-row">{diff_html}</div>
            <div class="meta-title">常见错误</div>
            <div class="chip-row">{mistake_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
