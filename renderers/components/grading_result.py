"""grading_result.py — Grading result cards.

Card layout:
  Score → Knowledge Points → Diagnosis → Step Comparison → Standard Solution → Recommendations
"""
import streamlit as st
from latex_utils import split_latex_text, render_ast


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


def render_knowledge_points(knowledge_points: list, question: dict = None, question_db=None) -> None:
    """独立展示知识点卡片 — 不在标准解法中隐藏

    当 *knowledge_points* 为空且 *question_db* 可用时，尝试从题目文本自动检测知识点。
    """
    # Auto-detect on the fly when the question JSON lacks tags
    if not knowledge_points and question_db and question:
        try:
            q_text = question.get("question", "")
            if q_text:
                knowledge_points = question_db.auto_tag(q_text)
        except Exception:
            pass

    with st.container(border=True):
        st.markdown("**📚 考查知识点**")

        if not knowledge_points:
            st.info("暂无知识点标注，请查看标准解法了解本题涉及的知识点")
        else:
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
            elif not knowledge_points:
                st.markdown("")
                st.markdown("**⚠️ 常见易错点**")
                st.info("暂无常见易错点标注")


def render_diagnosis_card(dr: dict, gr: dict) -> None:
    """Error diagnosis card."""
    error_type = dr.get("error_type", "")
    root_cause = dr.get("root_cause", "")
    is_repeat = dr.get("is_repeat", False)
    weak_points = dr.get("weak_points", [])

    with st.container(border=True):
        st.markdown("**🔍 错因诊断**")

        if not error_type and not root_cause:
            # 检查是否是未作答状态
            comment = gr.get("comment", "")
            if "未作答" in comment:
                error_type = "未作答"
                root_cause = "学生未输入任何作答内容，建议先尝试独立解题再查看标准答案"
            
        if error_type:
            st.markdown(f"**错误类型**: {error_type}")

        if root_cause:
            st.info(root_cause)
        elif not error_type:
            st.info("暂无诊断信息")

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
        elif error_type:
            st.markdown("**薄弱知识点**:")
            st.info("暂无薄弱知识点分析")


def render_standard_solution(solution: dict, expanded: bool = False) -> None:
    """Standard solution card — collapsed by default. Pass expanded=True to show open."""
    steps = solution.get("steps") or []
    answer = solution.get("standard_answer", "")

    # Check structured data first (may have content even when legacy steps/answer are empty).
    # Prefer the current solution payload over session state to avoid rendering stale answers
    # after a new grading run.
    structured = solution.get("_structured") or st.session_state.get("standard_answer_structured")

    if not steps and not answer:
        if isinstance(structured, dict) and structured.get("steps"):
            pass  # Has structured data, proceed to rendering
        else:
            # Truly no content available
            with st.expander("📖 查看标准解法", expanded=expanded):
                st.info("暂无标准解法数据")
            return

    with st.expander("📖 查看标准解法", expanded=expanded):
        # ── 优先：结构化渲染路径 ──
        if isinstance(structured, dict):
            # 检查是否有步骤
            struct_steps = structured.get("steps", [])
            if struct_steps:
                try:
                    from latex_utils import render_structured_safe, validate_structured
                    is_valid, _ = validate_structured(structured)
                    if is_valid:
                        render_structured_safe(structured)
                        return
                except Exception:
                    pass
            else:
                # 结构化数据存在但没有步骤，尝试获取最终答案
                fa = structured.get("final_answer", {})
                if fa and isinstance(fa, dict):
                    fa_content = fa.get("content", "")
                    if fa_content:
                        answer = fa_content

        # ── 回退：将 steps + answer 组装为统一文本 ──
        content_parts = []
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                label = step.get("label", f"步骤{i+1}")
                if step.get("content"):
                    content_parts.append(f"### {label}\n{step['content']}")
                elif step.get("blocks"):
                    block_texts = []
                    for b in step["blocks"]:
                        bc = str(b.get("content", ""))
                        # Safety: never render dict/list as text
                        if b.get("type") == "latex" and bc:
                            block_texts.append(f"${bc}$")
                        elif bc:
                            block_texts.append(bc)
                    if block_texts:
                        content_parts.append(f"### {label}\n" + "\n".join(block_texts))
                # If step has neither content nor blocks, skip it (don't str() it)
            elif isinstance(step, str):
                content_parts.append(f"### 步骤{i+1}\n{step}")
        
        # 确保最终答案被添加
        if answer and isinstance(answer, str) and answer.strip():
            # 如果没有步骤，只显示答案会显得单薄，添加一些说明
            if not content_parts:
                content_parts.append("### 标准解答")
            content_parts.append(f"**最终答案**：{answer}")

        if content_parts:
            raw = "\n\n".join(content_parts)
            try:
                from latex_utils import from_legacy_text, render_structured_safe
                render_structured_safe(from_legacy_text(raw))
            except Exception:
                try:
                    from latex_utils import split_latex_text, render_ast
                    render_ast(split_latex_text(raw))
                except Exception:
                    try:
                        from latex_utils import safe_render
                        safe_render(raw)
                    except Exception:
                        # Absolute last resort: plain text, refuse JSON-like content
                        if '"blocks"' in raw or '"type"' in raw[:200]:
                            st.error("标准解法数据结构异常，请重新批改")
                        else:
                            st.text(raw)


def render_recommendations(dr: dict, question_db=None, current_question=None) -> None:
    """Learning recommendations card with similar question links."""
    weak_points = dr.get("weak_points", [])

    with st.container(border=True):
        st.markdown("**📖 巩固建议**")
        
        if weak_points:
            recs = [
                f"重点复习 **{wp}** 相关知识点" for wp in weak_points[:3]
            ]
            for i, rec in enumerate(recs, 1):
                st.markdown(f"{i}. {rec}")
        else:
            st.info("建议先完成作答，系统将根据答题情况提供个性化巩固建议")

        # 相似题目推荐
        if question_db and current_question:
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
                            if st.button(
                                f"📝 {qid}",
                                key=f"similar_q_{qid}",
                                width="stretch",
                                help=f"{year}年 {qtype}"
                            ):
                                st.session_state.selected_question = q
                                st.session_state.page = "practice"
                                st.rerun()
                else:
                    st.markdown("")
                    st.markdown("**🎯 同类练习推荐**")
                    st.info("暂无相似题目推荐")
            except Exception as e:
                # 如果推荐功能不可用，显示原有提示
                st.markdown("")
                st.markdown("**🎯 同类练习推荐**")
                st.caption("建议在错题本中查看同类题目进行针对性练习")
        else:
            st.markdown("")
            st.markdown("**🎯 同类练习推荐**")
            st.caption("建议在错题本中查看同类题目进行针对性练习")


def render_grading_result_cards(gr: dict, sa: dict, dr: dict, total_score: int = 10,
                                 knowledge_points: list = None, question: dict = None,
                                 question_db=None, solution_expanded: bool = False) -> None:
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

    # ═══ Verification report — always visible when triggered ═══
    _verification = gr.get("_verification")
    if _verification:
        try:
            from agents.verifier_agent import VerificationReport, ObligationIssue, ConditionIssue, DerivationIssue
            report = VerificationReport(
                passed=_verification.get("passed", True),
                obligation_issues=[ObligationIssue(**o) for o in _verification.get("obligation_issues", [])],
                condition_issues=[ConditionIssue(**c) for c in _verification.get("condition_issues", [])],
                derivation_issues=[DerivationIssue(**d) for d in _verification.get("derivation_issues", [])],
                summary=_verification.get("summary", ""),
            )
            from agents.verifier_agent import render_verification_report
            render_verification_report(report)
        except Exception:
            # Fallback: display raw summary
            _obl_warn = gr.get("_obligation_warning", "")
            if _obl_warn:
                st.warning(_obl_warn)

    # ═══ Always visible: Knowledge Points — 独立展示，不在标准解法中隐藏 ═══
    kp_list = knowledge_points or (question.get("knowledge_points", []) if question else [])
    render_knowledge_points(kp_list, question, question_db)

    # ═══ Always visible: Diagnosis ═══
    render_diagnosis_card(dr, gr)

    # ═══ Collapsed: Step details ═══
    if gr.get("step_analysis"):
        with st.expander("📊 步骤对比分析", expanded=False):
            _render_step_comparison_body(gr)

    # ═══ Collapsed / Expanded: Standard solution ═══
    render_standard_solution(sa, expanded=solution_expanded)

    # ═══ Collapsed: Recommendations ═══
    with st.expander("📖 巩固建议", expanded=False):
        render_recommendations(dr, question_db, question)


def _render_step_comparison_body(gr: dict) -> None:
    """Step comparison body — renders each step with proper text/latex separation."""
    steps = gr.get("step_analysis") or []
    if not steps:
        return

    h1, h2, h3 = st.columns([1, 0.15, 1])
    with h1:
        st.caption("📝 你的作答")
    with h2:
        st.markdown("")
    with h3:
        st.caption("📋 标准步骤")

    for s in steps:
        num = s.get("num", "?")
        content = s.get("content", "")
        judgment = s.get("judgment", "")
        score_str = s.get("score", "")
        comment = s.get("comment", "")

        if judgment == "正确":
            icon = "✅"
        elif "缺失" in str(judgment) or "错误" in str(judgment):
            icon = "❌"
        else:
            icon = "⚠️"

        student_desc = comment if comment else judgment

        c1, c2, c3 = st.columns([1, 0.15, 1])
        with c1:
            _render_text_or_latex(student_desc)
        with c2:
            st.markdown(f"<div style='text-align:center;font-size:1.2em;'>{icon}</div>", unsafe_allow_html=True)
        with c3:
            st.caption(f"步骤{num}")
            _render_text_or_latex(content)
        st.caption(f"得分: {score_str}分")
        if s != steps[-1]:
            st.markdown("---")


def _render_text_or_latex(text: str) -> None:
    """Render content with proper text/latex block separation.

    If content contains LaTeX commands → split and render block by block.
    If content is plain text → render as markdown.
    """
    if not text:
        return
    try:
        from latex_utils import split_latex_text, render_ast
        segments = split_latex_text(str(text))
        if len(segments) == 1 and segments[0].get("type") == "text":
            st.markdown(segments[0]["content"])
        else:
            render_ast(segments)
    except Exception:
        st.markdown(str(text))
