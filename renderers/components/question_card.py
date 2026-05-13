"""question_card.py — Card wrapper (open/close)."""
import html
import streamlit as st
from design_system import diff_badge_html, qtype_badge_html


def CardOpen(ast) -> str:
    """Open a question card. Returns question_id.

    Usage:
        qid = CardOpen(ast)
        ... render body ...
        CardClose()
    """
    year = ast.year
    category = ast.category
    subject_short = str(category).replace("数学", "数") if category else ""
    year_label = f"{year} {subject_short}" if year and subject_short else str(year or ast.question_id)

    type_badge = qtype_badge_html(ast.question_type) if ast.question_type else ""
    diff_badge = diff_badge_html(ast.difficulty)
    score_str = f"{html.escape(str(ast.score))}分" if ast.score else ""

    parts = [type_badge]
    if score_str:
        parts.append(f'<span class="qcard-dot">·</span> <span>{score_str}</span>')
    parts.append(f'<span class="qcard-dot">·</span> {diff_badge}')

    st.markdown(f'''
    <div class="qcard">
        <div class="qcard-year">{html.escape(year_label)}</div>
        <div class="qcard-subtitle">{" ".join(parts)}</div>
        <div class="qcard-body">
    ''', unsafe_allow_html=True)
    return ast.question_id


def CardClose() -> None:
    """Close the card and its body div."""
    st.markdown('</div></div>', unsafe_allow_html=True)
