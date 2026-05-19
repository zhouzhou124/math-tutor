"""grading_renderer.py — 批改结果渲染器"""

import streamlit as st
from latex_utils import split_latex_text, render_ast, sanitize_latex_for_render


def render_grading_result(result: dict) -> None:
    """
    渲染批改结果。

    Args:
        result: {
            "score": 8,
            "total": 10,
            "correct": True/False,
            "errors": [{"type": "...", "description": "...", "location": "..."}],
            "feedback": "...",
            "student_answer": "...",
            "standard_answer": "...",
            "steps_analysis": [
                {"step": 1, "student": "...", "standard": "...", "match": True/False, "comment": "..."},
            ],
        }
    """
    score = result.get("score", 0)
    total = result.get("total", 10)
    correct = result.get("correct", False)
    feedback = result.get("feedback", "")
    errors = result.get("errors", [])
    student_answer = result.get("student_answer", "")
    standard_answer = result.get("standard_answer", "")
    steps_analysis = result.get("steps_analysis", [])

    # ── 分数卡片 ──
    ratio = score / total if total > 0 else 0
    if ratio >= 0.9:
        color = "#16a34a"
        emoji = "🌟"
    elif ratio >= 0.6:
        color = "#f59e0b"
        emoji = "📝"
    else:
        color = "#ef4444"
        emoji = "📚"

    st.markdown(
        f"<div style='text-align:center;padding:16px;border:2px solid {color};"
        f"border-radius:12px;margin-bottom:16px;'>"
        f"<span style='font-size:2em;'>{emoji}</span><br>"
        f"<span style='font-size:1.5em;font-weight:bold;color:{color};'>{score}/{total}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 正误判断 ──
    if correct:
        st.success("✅ 回答正确")
    else:
        st.error("❌ 存在错误")

    # ── 错误详情 ──
    if errors:
        st.markdown("**🔍 错误分析**")
        for err in errors:
            err_type = err.get("type", "未知")
            desc = err.get("description", "")
            loc = err.get("location", "")
            st.markdown(
                f"- **{err_type}** {desc}"
                + (f" *(位置: {loc})*" if loc else "")
            )

    # ── AI 反馈 ──
    if feedback:
        st.markdown("**💡 反馈**")
        try:
            render_ast(split_latex_text(feedback))
        except Exception:
            st.markdown(feedback)

    # ── 步骤对比 ──
    if steps_analysis:
        st.markdown("---")
        st.markdown("**📊 步骤对比**")
        for sa in steps_analysis:
            step_num = sa.get("step", "?")
            student = sa.get("student", "")
            standard = sa.get("standard", "")
            match = sa.get("match", False)
            comment = sa.get("comment", "")

            icon = "✅" if match else "❌"
            st.markdown(f"**{icon} 步骤{step_num}**")

            col1, col2 = st.columns(2)
            with col1:
                st.caption("你的作答")
                if student:
                    try:
                        st.latex(sanitize_latex_for_render(student))
                    except Exception:
                        render_ast(split_latex_text(student))

            with col2:
                st.caption("标准答案")
                if standard:
                    try:
                        st.latex(sanitize_latex_for_render(standard))
                    except Exception:
                        render_ast(split_latex_text(standard))

            if comment:
                st.caption(comment)

    # ── 答案对比 ──
    if student_answer or standard_answer:
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**你的答案**")
            if student_answer:
                try:
                    st.latex(sanitize_latex_for_render(student_answer))
                except Exception:
                    render_ast(split_latex_text(student_answer))
        with col_b:
            st.markdown("**标准答案**")
            if standard_answer:
                try:
                    st.latex(sanitize_latex_for_render(standard_answer))
                except Exception:
                    render_ast(split_latex_text(standard_answer))
