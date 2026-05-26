"""actions.py — Centralized action handlers.

All business logic lives here. UI components only render buttons.
View (components) and Action (this module) are strictly separated.
"""
import streamlit as st
from services.math_type_router import math_type_for_ai, source_math_type


def start_practice(qid: str) -> None:
    """Navigate to practice page with full question data."""
    db = st.session_state.get("question_db")
    q = db.get(qid) if db else None
    st.session_state.selected_question = q if q else qid
    st.session_state.page = "practice"
    st.rerun()


def view_solution(qid: str) -> None:
    """Navigate to grading page in answer-view mode, auto-triggering the
    empty-answer path so the AI generates detailed step-by-step solution."""
    db = st.session_state.get("question_db")
    q = db.get(qid) if db else None
    st.session_state.selected_question = q if q else qid

    # Build a minimal ocr_result so the grading page sees a "view only" request
    # with an empty student answer — this triggers the AI to generate the
    # detailed standard solution automatically.
    mt_source = source_math_type(q) if q else source_math_type()
    mt = math_type_for_ai(q)
    qt = q.get("question_type", "解答题") if q else "解答题"
    kps = ", ".join(q.get("knowledge_points", [])) if q else ""
    st.session_state.ocr_result = {
        "success": True,
        "question": (q.get("raw_question_text") or q.get("question", "")) if q else "",
        "student_answer": "",          # empty → triggers view-only path
        "math_type": mt,
        "source_math_type": mt_source,
        "question_type": qt,
        "knowledge_point": kps,
        "confidence": 1.0,
        "warnings": [],
    }
    st.session_state.answer_view_mode = True
    # Don't set grading_triggered — the grading page will auto-submit
    # via the async pipeline, avoiding a blocking 30-60 s API call.
    st.session_state["_auto_submit_view_solution"] = True
    st.session_state.page = "grading"
    st.rerun()


def start_edit(qid: str) -> None:
    """Enter edit mode for this question."""
    st.session_state.editing_question = qid
    st.rerun()


def delete_question(qid: str) -> None:
    """Delete a question from the database."""
    db = st.session_state.get("question_db")
    if db:
        db.delete(qid)
