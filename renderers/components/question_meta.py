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
    # 使用 getattr 处理 dataclass 对象，避免使用 dict.get() 方法
    kps = getattr(ast, 'knowledge_points', [])
    if not kps:
        kps = getattr(ast, 'tags', [])

    difficulty = getattr(ast, 'difficulty', '')
    year = getattr(ast, 'year', '')
    category = getattr(ast, 'category', '')

    parts = []

    # Knowledge chips
    if kps:
        tags_html = "".join(chip_html(str(k)) for k in kps[:6])
        parts.append(tags_html)

    # Difficulty + year info
    meta_parts = []
    if difficulty:
        meta_parts.append(diff_badge_html(difficulty))
    
    volume = getattr(ast, 'volume', '')
    
    # 模拟卷（宇哥八套卷、合工大超越等）按卷号索引，不显示年份
    if category and volume:
        display_text = f"{category}-{volume}"
        meta_parts.append(
            f'<span style="font-size:0.74rem;color:#94a3b8;font-weight:500;">{display_text}</span>'
        )
    elif year:
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
