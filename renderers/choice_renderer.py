"""choice_renderer.py — Choice question renderer.

Built from reusable components:
  CardOpen → stem → Options → MetaTags → Actions → CardClose
"""
import streamlit as st
from latex_utils import split_latex_text, render_ast
from question_ast import QuestionAST, parse_legacy
from renderers.components import (
    CardOpen, CardClose,
    render_options, render_actions, render_meta_tags,
)


def _to_ast(q) -> QuestionAST:
    if isinstance(q, QuestionAST):
        return q
    return parse_legacy(q)


def render_choice_question(q, show_answer: bool = False) -> None:
    """Render a multiple-choice question.

    Components:
      CardOpen → stem → render_options → MetaTags → Actions → CardClose
    """
    ast = _to_ast(q)

    # ── Card: open (renders header) ──
    qid = CardOpen(ast)

    # ── Stem ──
    if ast.stem:
        try:
            render_ast(split_latex_text(ast.stem))
        except Exception:
            st.markdown(ast.stem)

    # ── Options ──
    if ast.options:
        render_options(ast.options)

    # ── Answer (optional) ──
    if show_answer and ast.answer:
        st.markdown("---")
        st.markdown(f"**答案** &nbsp; **{ast.answer}**")

    # ── Close body ──
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Meta tags ──
    render_meta_tags(ast)

    # ── Actions ──
    render_actions(qid)

    # ── Card: close ──
    CardClose()
