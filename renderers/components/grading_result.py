import html
"""grading_result.py — Grading result cards.

Card layout:
  Score → Knowledge Points → Diagnosis → Step Comparison → Standard Solution → Recommendations
"""
import streamlit as st
from latex_utils import safe_latex, split_latex_text, render_ast


def render_score_card(gr: dict, total_score: int = 10) -> None:
    """Score overview card — prominent, first thing the student sees."""
    score = gr.get("total", 0)
    ratio = score / total_score if total_score > 0 else 0

    if ratio >= 0.9:
        emoji, color, bg = "🌟", "#16a34a", "#f0fdf4"
    elif ratio >= 0.6:
        emoji, color, bg = "📝", "#f59e0b", "#fffbeb"
    else:
        emoji, color, bg = "📚", "#dc2626", "#fef2f2"

    with st.container(border=True):
        st.markdown(f"""
        <div style="text-align:center;padding:8px 0;">
            <span style="font-size:2.5em;">{emoji}</span><br>
            <span style="font-size:2.2em;font-weight:800;color:{color};">{score}</span>
            <span style="font-size:1.2em;color:#94a3b8;"> / {total_score}</span>
        </div>
        """, unsafe_allow_html=True)

        comment = gr.get("comment", "")
        if comment:
            st.caption(comment)


def render_knowledge_points(knowledge_points: list, question: dict = None) -> None:
    """独立展示知识点卡片 — 不在标准解法中隐藏"""
    if not knowledge_points:
        return

    with st.container(border=True):
        st.markdown("**📚 考查知识点**")
        tags_html = " ".join(
            f"<span style='background:#eef2ff;color:#4338ca;padding:4px 10px;"
            f"border-radius:16px;font-size:0.85em;border:1px solid #c7d2fe;margin:2px;'>{kp}</span>"
            for kp in knowledge_points[:6]
        )
        st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:6px;'>{tags_html}</div>", unsafe_allow_html=True)

        # 知识点详情
        if question:
            common_mistakes = question.get("common_mistakes", [])
            if common_mistakes:
                st.markdown("")
                st.markdown("**⚠️ 常见易错点**")
                cm_tags = " ".join(
                    f"<span style='background:#fff7ed;color:#9a3412;padding:3px 8px;"
                    f"border-radius:12px;font-size:0.78em;border:1px solid #fed7aa;margin:2px;'>{cm}</span>"
                    for cm in common_mistakes[:4]
                )
                st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:4px;'>{cm_tags}</div>", unsafe_allow_html=True)


def render_diagnosis_card(dr: dict, gr: dict) -> None:
    """Error diagnosis card."""
    error_type = dr.get("error_type", "")
    root_cause = dr.get("root_cause", "")
    is_repeat = dr.get("is_repeat", False)
    weak_points = dr.get("weak_points", [])

    if not error_type and not root_cause:
        return

    with st.container(border=True):
        st.markdown("**🔍 错因诊断**")

        if error_type:
            st.markdown(f"**错误类型**: {error_type}")

        if root_cause:
            st.info(root_cause)

        if is_repeat:
            repeat_count = dr.get("repeat_count", 0)
            st.warning(f"⚠️ 历史重复错误（已出现 {repeat_count} 次），需重点巩固")

        if weak_points:
            tags = " ".join(
                f"<span style='background:#fef2f2;color:#dc2626;padding:2px 8px;"
                f"border-radius:12px;font-size:0.8em;'>{w}</span>"
                for w in weak_points[:5]
            )
            st.markdown(f"**薄弱知识点**: {tags}", unsafe_allow_html=True)


def render_standard_solution(solution: dict) -> None:
    """Standard solution card — collapsed by default."""
    steps = solution.get("steps") or []
    answer = solution.get("standard_answer", "")

    if not steps and not answer:
        return

    with st.expander("📖 查看标准解法", expanded=False):
        if steps:
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    label = step.get("label", f"步骤{i+1}")
                    step_content = step.get("content", "")
                else:
                    label = f"步骤{i+1}"
                    step_content = str(step)
                if step_content:
                    st.markdown(f"**{label}**")
                    # 使用 AST-first 渲染方式处理混合文本（文字 + 数学公式）
                    try:
                        segments = split_latex_text(step_content)
                        render_ast(segments)
                    except Exception as e:
                        # 降级处理：先尝试直接渲染
                        try:
                            safe = safe_latex(step_content)
                            st.markdown(safe)
                        except Exception:
                            st.caption(step_content)

        if answer and not steps:
            st.markdown("**答案**")
            try:
                segments = split_latex_text(answer)
                render_ast(segments)
            except Exception:
                try:
                    safe = safe_latex(answer)
                    st.markdown(safe)
                except Exception:
                    st.markdown(answer)


def render_recommendations(dr: dict, question_db=None, current_question=None) -> None:
    """Learning recommendations card with similar question links."""
    weak_points = dr.get("weak_points", [])
    if not weak_points:
        return

    with st.container(border=True):
        st.markdown("**📖 巩固建议**")
        recs = [
            f"重点复习 **{wp}** 相关知识点" for wp in weak_points[:3]
        ]
        for i, rec in enumerate(recs, 1):
            st.markdown(f"{i}. {rec}")

        # 相似题目推荐
        if question_db and current_question and weak_points:
            try:
                from similar_question_recommender import recommend_similar
                similar_questions = recommend_similar(
                    question=current_question,
                    diagnosis=dr,
                    question_db=question_db,
                    top_k=3
                )
                
                if similar_questions:
                    st.markdown("")
                    st.markdown("**🎯 同类练习推荐**")
                    cols = st.columns(min(3, len(similar_questions)))
                    for i, q in enumerate(similar_questions):
                        with cols[i]:
                            qid = q.get("question_id", "")
                            qtype = q.get("question_type", "")
                            year = q.get("year", "")
                            st.button(
                                f"📝 {qid}",
                                key=f"similar_q_{qid}",
                                use_container_width=True,
                                help=f"{year}年 {qtype}"
                            )
            except Exception as e:
                # 如果推荐功能不可用，显示原有提示
                st.caption("建议在错题本中查看同类题目进行针对性练习")
        else:
            st.caption("建议在错题本中查看同类题目进行针对性练习")


def render_grading_result_cards(gr: dict, sa: dict, dr: dict, total_score: int = 10, 
                                 knowledge_points: list = None, question: dict = None, 
                                 question_db=None) -> None:
    """Progressive disclosure: score + knowledge points + main error visible, details collapsed.

    Default view:
      ┌─ Score card (always visible) ─┐
      ├─ Knowledge Points (always visible) ─┤
      └─ Diagnosis (always visible) ─┘

    Expandable (click to reveal):
      ▶ 📊 步骤对比分析
      ▶ 📖 查看标准解法
      ▶ 📖 巩固建议
    """
    st.markdown("---")

    # ═══ Always visible: Score ═══
    render_score_card(gr, total_score)

    # ═══ Always visible: Knowledge Points — 独立展示，不在标准解法中隐藏 ═══
    kp_list = knowledge_points or question.get("knowledge_points", []) if question else []
    render_knowledge_points(kp_list, question)

    # ═══ Always visible: Diagnosis ═══
    render_diagnosis_card(dr, gr)

    # ═══ Collapsed: Step details ═══
    if gr.get("step_analysis"):
        with st.expander("📊 步骤对比分析", expanded=False):
            _render_step_comparison_body(gr)

    # ═══ Collapsed: Standard solution ═══
    render_standard_solution(sa)

    # ═══ Collapsed: Recommendations ═══
    weak_points = dr.get("weak_points", [])
    if weak_points:
        with st.expander("📖 巩固建议", expanded=False):
            render_recommendations(dr, question_db, question)


def _render_step_comparison_body(gr: dict) -> None:
    """Step comparison body — rendered inside expander."""
    import html as _html
    steps = gr.get("step_analysis") or []
    if not steps:
        return

    h1, h2, h3 = st.columns([1, 0.15, 1])
    with h1:
        st.markdown("<span style='color:#64748b;font-size:0.78rem;font-weight:700;'>📝 你的作答</span>", unsafe_allow_html=True)
    with h2:
        st.markdown("")
    with h3:
        st.markdown("<span style='color:#64748b;font-size:0.78rem;font-weight:700;'>📋 标准步骤</span>", unsafe_allow_html=True)

    for s in steps:
        num = s.get("num", "?")
        content = s.get("content", "")
        judgment = s.get("judgment", "")
        score_str = s.get("score", "")
        comment = s.get("comment", "")

        if judgment == "正确":
            icon, jcolor = "✅", "#16a34a"
        elif "缺失" in str(judgment) or "错误" in str(judgment):
            icon, jcolor = "❌", "#dc2626"
        else:
            icon, jcolor = "⚠️", "#f59e0b"

        student_desc = comment if comment else judgment
        bg = {"#dc2626": "#fef2f2", "#16a34a": "#f0fdf4", "#f59e0b": "#fffbeb"}.get(jcolor, "#f8fafc")

        c1, c2, c3 = st.columns([1, 0.15, 1])
        with c1:
            st.markdown(
                f"<div style='padding:8px;border-radius:8px;background:{bg};"
                f"border-left:3px solid {jcolor};'>"
                f"<span style='font-size:0.82rem;color:#334155;'>{_html.escape(student_desc[:120])}</span>"
                f"</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='text-align:center;font-size:1.2em;'>{icon}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(
                f"<div style='padding:8px;border-radius:8px;background:#f8fafc;"
                f"border-left:3px solid #3b82f6;'>"
                f"<span style='font-size:0.8rem;color:#64748b;font-weight:600;'>步骤{num}</span><br>"
                f"<span style='font-size:0.82rem;color:#334155;'>{_html.escape(content[:120])}</span>"
                f"</div>", unsafe_allow_html=True)
        st.caption(f"得分: {score_str}分")
        if s != steps[-1]:
            st.markdown("---")
