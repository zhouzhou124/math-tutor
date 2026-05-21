"""choice_renderer.py — Choice question renderer.

Built from reusable components:
  CardOpen → stem → Options → MetaTags → Actions → CardClose
"""
import streamlit as st
from latex_utils import split_latex_text, render_ast
from renderers.components import (
    CardOpen, CardClose,
    render_options, render_actions, render_meta_tags,
)


from question_ast import QuestionAST
from . import to_ast as _to_ast


def render_choice_question(q, show_answer: bool = False, show_actions: bool = True) -> None:
    """Render a multiple-choice question.

    Components:
      CardOpen → stem → render_options → MetaTags → Actions → CardClose
    """
    # 如果已经是 QuestionAST 对象，直接使用，不再转换
    if isinstance(q, QuestionAST):
        ast = q
    else:
        ast = _to_ast(q)

    # ── Card: open (renders header) ──
    qid = CardOpen(ast)

    # ── Stem ──
    if ast.stem:
        try:
            # 对包含中文数字序号的题目内容进行分段处理
            stem_text = ast.stem
            # 在①②③④等序号前添加换行符，使每个结论单独占一行
            # 但不在开头的序号前添加换行
            import re
            stem_text = re.sub(r'(?<!^)(?<!\n)([①②③④⑤⑥⑦⑧⑨⑩])', r'\n\1', stem_text)
            render_ast(split_latex_text(stem_text))
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
    st.markdown('</div>', unsafe_allow_html=True)  # close qcard-body

    # ── Actions ──
    if show_actions:
        render_actions(qid)
        CardClose()
    else:
        st.markdown('</div>', unsafe_allow_html=True)  # close outer card
