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
    volume = getattr(ast, 'volume', '')
    
    # 对于宇哥八套卷，显示为 "26宇哥八套卷-卷一" 格式
    if category and '宇哥' in category:
        year_label = f"{category}"
        if volume:
            year_label += f"-{volume}"
    else:
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
    <div style="
        background: #fafafa;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    ">
        <div style="font-size: 1.1rem; font-weight: 600; color: #1f2937; margin-bottom: 4px;">{html.escape(year_label)}</div>
        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 12px;">{" ".join(parts)}</div>
        <div class="qcard-body">
    ''', unsafe_allow_html=True)
    return ast.question_id


def CardClose() -> None:
    """Close the outer card div (qcard-body is closed separately by caller)."""
    st.markdown('</div>', unsafe_allow_html=True)
