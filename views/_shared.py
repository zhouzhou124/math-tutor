"""pages/_shared.py — 页面间共享的渲染辅助函数"""
import html
import streamlit as st
from config import LLM_BASE_URL, LLM_MODEL


# ═══════════════════════════════════════════════
# Shared navigation map
# ═══════════════════════════════════════════════

NAV_MAP = {
    "仪表盘": "dashboard",
    "智能刷题": "practice",
    "AI批改": "grading",
    "真题库": "question_bank",
    "错题本": "error_notebook",
}


# ═══════════════════════════════════════════════
# Shared LLM client factory
# ═══════════════════════════════════════════════

def get_client():
    """Get or create LLM client from session state."""
    if st.session_state.get("llm_client") is None and st.session_state.get("api_key"):
        from llm_client import create_client
        st.session_state.llm_client = create_client(
            api_key=st.session_state.api_key,
            base_url=st.session_state.get("base_url", LLM_BASE_URL),
            protocol=st.session_state.get("protocol", "openai"),
        )
    return st.session_state.get("llm_client")


# ═══════════════════════════════════════════════
# UI helpers
# ═══════════════════════════════════════════════

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
