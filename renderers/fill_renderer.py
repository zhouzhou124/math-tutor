"""fill_renderer.py — Fill-in-the-blank question renderer."""
import streamlit as st
from math_sanitizer import safe_latex
from latex_utils import split_latex_text, render_ast
from renderers.components import (
    CardOpen, CardClose, render_actions, render_meta_tags,
)


from . import to_ast as _to_ast


def render_fill_question(q, show_answer: bool = False, show_actions: bool = True) -> None:
    ast = _to_ast(q)
    qid = CardOpen(ast)

    if ast.stem:
        try:
            render_ast(split_latex_text(ast.stem))
        except Exception:
            st.markdown(ast.stem)

    if show_answer and ast.answer:
        st.markdown("---")
        try:
            answer_text = ast.answer.strip()
            if '$' in answer_text:
                st.markdown(f"**答案** &nbsp; {answer_text}")
            else:
                safe = safe_latex(f"${answer_text}$")
                if safe.startswith("$") and safe.endswith("$"):
                    safe = safe[1:-1]
                st.markdown(f"**答案** &nbsp; ${safe}$")
        except Exception:
            st.markdown(f"**答案** {ast.answer}")

    st.markdown('</div>', unsafe_allow_html=True)  # close qcard-body
    if show_actions:
        render_actions(qid)
        CardClose()
    else:
        st.markdown('</div>', unsafe_allow_html=True)  # close outer card
