"""confirm_dialog.py — Delete confirmation popover (View only).

Uses st.popover() — no layout shift. All logic in renderers/actions.py.
"""
import streamlit as st
from renderers.actions import delete_question


def confirm_delete(qid: str) -> None:
    """Show a delete confirmation inside a popover. No layout shift."""
    with st.popover("🗑", use_container_width=True):
        st.error("确认删除该题目？")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("确认删除", key=f"del_ok_{qid}",
                         type="primary", use_container_width=True):
                delete_question(qid)
                st.rerun()
        with c2:
            if st.button("取消", key=f"del_cancel_{qid}",
                         use_container_width=True):
                st.rerun()
