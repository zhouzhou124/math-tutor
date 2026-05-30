"""grading_result.py — Grading result cards.

Card layout:
  Score → Knowledge Points → Diagnosis → Step Comparison → Standard Solution → Recommendations
"""
import logging
import streamlit as st
from latex_utils import split_latex_text, render_ast

logger = logging.getLogger(__name__)


def _trace_raw_source_render_attempt(label: str, text: str, source: str = "") -> bool:
    """P37.6.4: Log when raw source text is about to reach a student-facing render.

    Returns True if a raw source leak was detected (caller should block rendering).
    """
    from services.solution_quality import detect_student_raw_source_leak
    if not text or not isinstance(text, str):
        return False
    issues = detect_student_raw_source_leak(text)
    if issues:
        preview = text[:200].replace("\n", "\\n")
        logger.warning(
            "[RAW_SOURCE_LEAK_TRACE] label=%s source=%s issues=%s preview=%s",
            label, source, issues, preview,
        )
        return True
    return False


def _is_admin_user() -> bool:
    """Check if current user has admin role."""
    auth = st.session_state.get("auth") or {}
    if auth.get("is_admin"):
        return True
    if str(auth.get("role", "")).lower() == "admin":
        return True
    cu = st.session_state.get("current_user")
    if cu is not None:
        if getattr(cu, "is_admin", False):
            return True
        if str(getattr(cu, "role", "")).lower() == "admin":
            return True
    user = st.session_state.get("user") or {}
    if str(user.get("role", "")).lower() == "admin":
        return True
    for key in ("user_role", "role"):
        if str(st.session_state.get(key, "")).lower() == "admin":
            return True
    username = (
        auth.get("username")
        or user.get("username")
        or st.session_state.get("username")
        or st.session_state.get("user_name")
        or ""
    )
    return str(username).lower() == "admin"


def _should_show_solution_debug() -> bool:
    """P37.4: Admin-only debug expander visibility check."""
    import os
    if not _is_admin_user():
        return False
    if st.session_state.get("debug_mode"):
        return True
    return os.environ.get("SHOW_SOLUTION_DEBUG", "") == "1"


def _render_blocked_solution_debug(solution: dict, grading_result: dict | None = None) -> None:
    """P37.4.2+: Admin-only debug preview for blocked solution candidates."""
    if not _is_admin_user():
        return

    debug_on = _should_show_solution_debug()

    if not debug_on:
        st.caption("💡 你是 admin，但尚未开启开发者调试模式。请在侧边栏打开「开发者调试模式」查看被拦截的候选内容。")
        return

    gr = grading_result if isinstance(grading_result, dict) else (st.session_state.get("grading_result") or {})
    issues = (
        solution.get("_blocked_solution_issues")
        or gr.get("_blocked_solution_issues")
        or []
    )
    qr = (
        solution.get("_blocked_solution_quality_report")
        or gr.get("_blocked_solution_quality_report")
        or solution.get("_quality_report")
        or gr.get("_quality_report")
        or {}
    )
    if not issues and isinstance(qr, dict):
        issues = qr.get("issues") or []
    locations = (
        solution.get("_blocked_solution_error_locations")
        or gr.get("_blocked_solution_error_locations")
        or []
    )
    candidate = solution.get("_blocked_solution_candidate") or gr.get("_blocked_solution_candidate")
    preview = solution.get("_failed_raw_preview") or gr.get("_failed_raw_preview")
    source = (
        solution.get("_blocked_solution_source")
        or gr.get("_blocked_solution_source")
        or solution.get("standard_solution_source", "")
    )
    model_used = solution.get("model_used") or solution.get("_model_used") or gr.get("_model_used", "")
    status = solution.get("standard_solution_status", "")

    logger.info(
        "[ADMIN_DEBUG_RAW_PREVIEW] status=%s source=%s issues_count=%d has_candidate=%s",
        status, source, len(issues), isinstance(candidate, dict),
    )
    with st.expander("🔧 调试：查看被拦截的标准解答候选（仅 admin）"):
        st.warning("以下内容未通过质量门禁，仅供开发调试，不会保存为标准解答。")
        st.markdown(f"**状态：** `{status}`　**来源：** `{source}`　**模型：** `{model_used}`")
        if issues:
            st.markdown("**质量问题：**")
            for issue in issues:
                st.markdown(f"- `{issue}`")

        if locations:
            st.markdown("**问题字段定位：**")
            for loc in locations:
                st.markdown(f"- **{loc.get('issue', '?')}** → `{loc.get('path', '?')}`")
                if loc.get("preview"):
                    st.code(loc["preview"], language=None)
                if loc.get("suggestion"):
                    st.caption(f"建议：{loc['suggestion']}")

        if isinstance(candidate, dict):
            raw_ans = candidate.get("standard_answer") or ""
            if raw_ans.strip():
                st.markdown("**原始 standard_answer：**")
                st.code(raw_ans[:3000], language=None)
            candidate_struct = candidate.get("_structured")
            if isinstance(candidate_struct, dict):
                import json
                st.markdown("**原始 _structured (JSON)：**")
                st.code(json.dumps(candidate_struct, ensure_ascii=False, indent=2)[:5000], language="json")
        elif preview:
            st.markdown("**原始内容预览：**")
            st.code(preview, language=None)
        else:
            st.info(
                "当前结果没有保存 blocked candidate，请点击「重新生成标准解答」后再查看。"
                "以下为当前 solution debug snapshot。"
            )
            snapshot_ans = solution.get("standard_answer") or gr.get("standard_answer") or ""
            if snapshot_ans.strip():
                st.markdown("**当前 standard_answer：**")
                st.code(snapshot_ans[:3000], language=None)


def render_blocked_solution_debug_panel(
    solution: dict,
    grading_result: dict | None = None,
    context: str = "",
) -> None:
    """Public API: render admin debug panel for blocked solutions."""
    _render_blocked_solution_debug(solution, grading_result=grading_result)


def _render_solution_failure_with_debug(
    solution: dict,
    message: str,
    issues: list | None = None,
    raw_answer: str = "",
) -> None:
    """Render solution failure warning with admin debug panel and retry button."""
    with st.expander("📖 查看标准解法", expanded=False):
        st.warning(message)
        if issues:
            st.caption("质量问题：" + "、".join(str(i) for i in issues[:4]))
        _render_blocked_solution_debug(solution)
        if raw_answer and len(raw_answer.strip()) >= 2:
            st.markdown(f"**最终答案：** {raw_answer}")

        def _request_retry():
            st.session_state["_solution_retry_requested"] = True

        if st.button("🔄 重新生成标准解答", key="retry_sol_failure"):
            _request_retry()


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
            q_text = question.get("raw_question_text") or question.get("question", "")
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
        # ── Quality warnings ──
        raw_answer = solution.get("standard_answer", "")
        # Check if there's substantive derivation content (not just metadata)
        struct_steps_count = len(structured.get("steps", [])) if isinstance(structured, dict) else 0
        _has_content = (
            len(steps) > 0
            or struct_steps_count > 0
            or len(raw_answer.strip()) >= 80
        )
        if not raw_answer or (not _has_content and not struct_steps_count):
            st.warning(
                "📝 此题暂未生成详细步骤解答。"
                "请确认已配置 API Key，然后重新点击「开始批改」或「查看答案」以触发 AI 生成。"
                "如多次尝试仍无结果，可能是题目较复杂导致 AI 求解超时，请稍后重试。"
            )
            return
        if raw_answer and not _has_content:
            st.info(
                "💡 当前解答较简短。如需查看详细推导步骤，请重新触发 AI 批改。"
            )
        if solution.get("_ai_consistency_warning"):
            st.warning("⚠️ AI 生成的解答与已知正确答案不完全一致，仅供参考学习，请以题目给定的正确答案为准。")
        if solution.get("_ai_unverified"):
            st.info("💡 此解答由 AI 自动生成，尚未经过人工审核验证。如有疑问请对照教材确认。")
        if solution.get("standard_solution_status") in ("failed", "incomplete"):
            st.warning(solution.get("standard_solution_error") or "标准解答生成不完整，请重新触发生成。")
        # ── 优先：结构化渲染路径 ──
        if isinstance(structured, dict):
            # 检查是否有步骤
            struct_steps = structured.get("steps", [])
            if struct_steps:
                # 预检查：步骤是否有实质性内容（非空 block）
                _has_substance = False
                for s in struct_steps:
                    blocks = s.get("blocks", []) if isinstance(s, dict) else []
                    for b in blocks:
                        if isinstance(b, dict) and b.get("content", "").strip():
                            _has_substance = True
                            break
                    if _has_substance:
                        break
                if _has_substance:
                    try:
                        from latex_utils import render_structured_safe, validate_structured
                        is_valid, _ = validate_structured(structured)
                        if is_valid:
                            render_structured_safe(structured)
                            return
                    except Exception:
                        pass
                # If no substance, fall through to text fallback below
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
                    content_parts.append(f"### {label.rstrip('：:')}：\n{step['content']}")
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
                        content_parts.append(f"### {label.rstrip('：:')}：\n" + "\n".join(block_texts))
                # If step has neither content nor blocks, skip it (don't str() it)
            elif isinstance(step, str):
                content_parts.append(f"### 步骤{i+1}：\n{step}")
        
        # 确保最终答案被添加
        if answer and isinstance(answer, str) and answer.strip():
            # 如果没有步骤，只显示答案会显得单薄，添加一些说明
            if not content_parts:
                content_parts.append("### 标准解答")
            content_parts.append(f"**最终答案**：{answer}")

        if content_parts:
            raw = "\n\n".join(content_parts)
            try:
                from renderers.math_render_policy import render_grading_latex
                render_grading_latex(raw)
            except Exception:
                try:
                    from latex_utils import from_legacy_text, render_structured_safe
                    render_structured_safe(from_legacy_text(raw))
                except Exception:
                    try:
                        from latex_utils import split_latex_text, render_ast
                        render_ast(split_latex_text(raw))
                    except Exception:
                        try:
                            st.markdown(raw)
                        except Exception:
                            st.text(raw)


def render_recommendations(dr: dict, question_db=None, current_question=None, is_correct: bool = None) -> None:
    """Learning recommendations card — always shown, tailored to performance."""
    weak_points = dr.get("weak_points", [])

    with st.container(border=True):
        st.markdown("**📖 巩固建议**")

        if is_correct is True:
            st.success("👍 这道题回答正确！继续保持，建议练习同类变式题巩固。")
        elif is_correct is False:
            st.info("📝 这道题还有提升空间，重点关注下方薄弱知识点。")
        else:
            st.info("💡 无论对错，持续练习同类题目都能帮助你巩固知识。")

        if weak_points:
            st.markdown("**薄弱知识点**：")
            tags = " · ".join(
                f"**{wp}**" for wp in weak_points[:5]
            )
            st.markdown(tags)
            recs = [
                f"重点复习 **{wp}** 相关知识点" for wp in weak_points[:3]
            ]
            for i, rec in enumerate(recs, 1):
                st.markdown(f"{i}. {rec}")
        elif is_correct is True:
            # Correct but still suggest related practice
            knowledge_points = (current_question or {}).get("knowledge_points", [])
            if knowledge_points:
                st.markdown(f"已掌握：{' · '.join(knowledge_points[:5])}")
            st.markdown("建议做同类变式题检验是否真正理解。")

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
    """Progressive disclosure layout.

    P22: view_only mode skips score, diagnosis, and recommendations,
    showing only the standard solution and knowledge points.
    """
    is_view_only = bool(gr.get("view_only") or gr.get("hide_score_card"))

    if is_view_only:
        st.info("📖 你当前未提交作答，正在查看标准解答。建议先独立完成本题，再对照标准解答检查思路。")
        st.markdown("---")
        render_standard_solution(sa, expanded=True)
        kp_list = knowledge_points or (question.get("knowledge_points", []) if question else [])
        render_knowledge_points(kp_list, question, question_db)
        return

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
            _obl_warn = gr.get("_obligation_warning", "")
            if _obl_warn:
                st.warning(_obl_warn)

    # ═══ Diagnosis — skipped when hide_diagnosis ═══
    if not gr.get("hide_diagnosis") and dr:
        render_diagnosis_card(dr, gr)

    # ═══ Collapsed: Step details ═══
    if gr.get("step_analysis"):
        with st.expander("📊 步骤对比分析", expanded=False):
            _render_step_comparison_body(gr)

    # ═══ Collapsed / Expanded: Standard solution ═══
    render_standard_solution(sa, expanded=solution_expanded)

    # ═══ Knowledge Points — below Standard Solution, always visible ═══
    kp_list = knowledge_points or (question.get("knowledge_points", []) if question else [])
    render_knowledge_points(kp_list, question, question_db)

    # ═══ Recommendations — skipped when view_only ═══
    if not is_view_only:
        with st.expander("📖 巩固建议", expanded=True):
            render_recommendations(dr, question_db, question, is_correct=(gr.get("total", 0) >= total_score * 0.9))


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


def render_summary_header(gr: dict, dr: dict, total_score: int = 10) -> None:
    """P16: Report-style summary — score, main issue, recommendation."""
    import html as _html
    score = gr.get("total", 0)
    ratio = score / total_score if total_score > 0 else 0
    engine = gr.get("engine", "")

    if engine == "view_only":
        return

    if ratio >= 0.9:
        grade, color = "优秀", "#16a34a"
    elif ratio >= 0.6:
        grade, color = "良好", "#f59e0b"
    else:
        grade, color = "需加强", "#dc2626"

    root_cause = dr.get("root_cause", "") or dr.get("error_type", "")
    weak_points = dr.get("weak_points", [])[:3]
    recs = dr.get("recommendations", [])[:2]

    st.markdown(
        f"""<div class="app-card" style="background:{color}08;border-color:{color}30;">
            <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">📋 批改报告</div>
            <div style="margin-top:4px;color:#475569;font-size:0.92rem;">
                本题得分 <b style="color:{color};">{score}/{total_score}</b> · {grade}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if root_cause:
        st.markdown(
            f'<div class="app-card-compact" style="border-left:4px solid {color};">'
            f'<b>主要问题：</b>{_html.escape(root_cause[:100])}</div>',
            unsafe_allow_html=True,
        )

    if weak_points:
        kp_tags = " ".join(
            f'<span class="app-chip app-chip-orange">{_html.escape(str(kp))}</span>'
            for kp in weak_points
        )
        st.markdown(f"**薄弱知识点** {kp_tags}", unsafe_allow_html=True)

    if recs:
        for rec in recs:
            st.caption(f"💡 {rec}")
