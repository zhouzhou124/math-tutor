"""question_meta.py — Meta area component.

Renders below the question body:
  [极限] [定积分] [洛必达]   ← knowledge chips
  🟊🟊🟊  2024 · 数一        ← difficulty + year
"""
import streamlit as st
from design_system import chip_html, diff_badge_html


def render_meta_tags(ast) -> None:
    """Render knowledge point tags + difficulty + year below the question.

    Single source of truth — no duplication with right-side panels.
    """
    kps = ast.knowledge_points if hasattr(ast, 'knowledge_points') else ast.get('knowledge_points', [])
    if not kps:
        kps = ast.tags if hasattr(ast, 'tags') else ast.get('tags', [])

    difficulty = ast.difficulty if hasattr(ast, 'difficulty') else ast.get('difficulty', '')
    year = ast.year if hasattr(ast, 'year') else ast.get('year', '')
    category = ast.category if hasattr(ast, 'category') else ast.get('category', '')

    parts = []

    # Knowledge chips
    if kps:
        tags_html = "".join(chip_html(str(k)) for k in kps[:6])
        parts.append(tags_html)

    # Difficulty + year info
    meta_parts = []
    if difficulty:
        meta_parts.append(diff_badge_html(difficulty))
    if year:
        yr = f"{year}"
        if category:
            yr += f" · {category}"
        meta_parts.append(
            f'<span style="font-size:0.74rem;color:#94a3b8;font-weight:500;">{yr}</span>'
        )
    if meta_parts:
        parts.append(" &nbsp; ".join(meta_parts))

    if parts:
        st.markdown(
            f'<div class="qcard-tags">{" ".join(parts)}</div>',
            unsafe_allow_html=True,
        )
