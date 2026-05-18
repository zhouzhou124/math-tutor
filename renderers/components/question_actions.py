"""question_actions.py — Action button bar (View only).

Renders buttons. All business logic is in renderers/actions.py.
"""
import streamlit as st
from renderers.actions import start_practice, view_solution, start_edit
from .confirm_dialog import confirm_delete


def render_actions(qid: str) -> None:
    """Render the action button bar. No business logic here."""
    st.markdown('<div class="qcard-actions-bar">', unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns([1.8, 1.8, 0.9, 0.9])

    with b1:
        if st.button("▶ 开始练习", key=f"practice_{qid}",
                     use_container_width=True, type="primary"):
            start_practice(qid)

    with b2:
        if st.button("👁 查看解析", key=f"view_{qid}",
                     use_container_width=True, type="secondary"):
            view_solution(qid)

    with b3:
        if st.button("✏ 编辑", key=f"edit_{qid}", use_container_width=True):
            start_edit(qid)

    with b4:
        confirm_delete(qid)

    st.markdown('</div>', unsafe_allow_html=True)
