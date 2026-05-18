"""actions.py — Centralized action handlers.

All business logic lives here. UI components only render buttons.
View (components) and Action (this module) are strictly separated.
"""
import streamlit as st


def start_practice(qid: str) -> None:
    """Navigate to practice page with full question data."""
    q = st.session_state.question_db.get(qid)
    st.session_state.selected_question = q if q else qid
    st.session_state.page = "practice"
    st.rerun()


def view_solution(qid: str) -> None:
    """Navigate to grading page in answer-view mode with full question data."""
    q = st.session_state.question_db.get(qid)
    st.session_state.selected_question = q if q else qid
    st.session_state.answer_view_mode = True
    st.session_state.page = "grading"


def start_edit(qid: str) -> None:
    """Enter edit mode for this question."""
    st.session_state.editing_question = qid
    st.rerun()


def delete_question(qid: str) -> None:
    """Delete a question from the database."""
    st.session_state.question_db.delete(qid)
