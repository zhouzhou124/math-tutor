"""question_renderer.py — Type-aware question dispatcher.

Architecture:
  render_question(q) → dispatch → specialized renderer

Components: renderers/components/
  CardOpen → body → MetaTags → Actions → CardClose
"""
import re
import streamlit as st
from math_sanitizer import safe_latex
from latex_utils import split_latex_text, render_ast
from renderers.components import (
    CardOpen, CardClose, render_actions, render_meta_tags,
)


from . import to_ast as _to_ast


# ============================================================
# SOLUTION
# ============================================================

def render_solution_question(q, show_steps: bool = False, show_answer: bool = False, show_actions: bool = True) -> None:
    ast = _to_ast(q)
    qid = CardOpen(ast)

    if ast.stem:
        try:
            render_ast(split_latex_text(ast.stem))
        except Exception:
            st.markdown(ast.stem)

    if show_steps and ast.steps:
        st.markdown("---")
        for i, step in enumerate(ast.steps):
            label = step.label or f"步骤{i+1}"
            if step.content:
                st.markdown(f"**{label}**")
                try:
                    render_ast(split_latex_text(step.content))
                except Exception:
                    st.markdown(step.content)

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


# ============================================================
# PROOF
# ============================================================

def render_proof_question(q, show_steps: bool = False, show_answer: bool = False, show_actions: bool = True) -> None:
    ast = _to_ast(q)
    qid = CardOpen(ast)

    if ast.stem:
        try:
            render_ast(split_latex_text(ast.stem))
        except Exception:
            st.markdown(ast.stem)

    def _render_block(content: str) -> None:
        if re.match(r"(?:证明|解)[：:\s]", content):
            st.markdown("**📋 证明**")
            body = re.sub(r"^(?:证明|解)[：:\s]*", "", content)
            try:
                render_ast(split_latex_text(body))
            except Exception:
                st.markdown(body)
        elif re.match(r"(?:即证|要证)", content):
            st.markdown("**🎯 即证**")
            body = re.sub(r"^(?:即证|要证)[：:\s]*", "", content)
            try:
                render_ast(split_latex_text(body))
            except Exception:
                st.markdown(body)
        elif "得证" in content or "证毕" in content:
            st.markdown("**∎ 得证**")
        else:
            try:
                render_ast(split_latex_text(content))
            except Exception:
                st.markdown(content)

    if show_steps and ast.steps:
        st.markdown("---"); st.markdown("**证明**")
        for step in ast.steps:
            if step.content:
                _render_block(step.content)
    elif show_steps and ast.analysis:
        st.markdown("---"); st.markdown("**证明**")
        for part in re.split(r"(?=(?:证明|解|即证|得证)[：:\s])", ast.analysis):
            part = part.strip()
            if part:
                _render_block(part)

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


# ============================================================
# GENERIC — fallback
# ============================================================

def render_generic_question(q) -> None:
    ast = _to_ast(q)
    qid = CardOpen(ast)

    if ast.stem:
        try:
            render_ast(split_latex_text(ast.stem))
        except Exception:
            st.markdown(ast.stem)

    st.markdown('</div>', unsafe_allow_html=True)  # close qcard-body
    CardClose()


# ============================================================
# Type-aware dispatch (THE entry point)
# ============================================================

def render_question(q, show_steps: bool = False, show_answer: bool = False, show_actions: bool = True) -> None:
    """THE entry point. Accepts QuestionAST or legacy dict."""
    ast = _to_ast(q)

    if ast.question_type == "选择题":
        from .choice_renderer import render_choice_question
        render_choice_question(ast, show_answer=show_answer, show_actions=show_actions)
    elif ast.question_type == "填空题":
        from .fill_renderer import render_fill_question
        render_fill_question(ast, show_answer=show_answer, show_actions=show_actions)
    elif ast.question_type == "解答题":
        render_solution_question(ast, show_steps=show_steps, show_answer=show_answer, show_actions=show_actions)
    elif ast.question_type == "证明题":
        render_proof_question(ast, show_steps=show_steps, show_answer=show_answer, show_actions=show_actions)
    else:
        render_generic_question(ast)


def render_question_list(questions) -> None:
    if not questions:
        st.info("没有找到题目")
        return
    for q in questions:
        render_question(q)
