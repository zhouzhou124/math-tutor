"""pages/mistakes_page.py — 错题本"""
import streamlit as st
import math
import time
from config import SUBJECTS, ERROR_TYPES, DIFFICULTY_LEVELS

MAX_EXPANDED_ITEMS = 1
PAGE_SIZE = 20
DATA_CACHE_TTL = 5  # 同一轮渲染内缓存有效期（秒）


def _get_mistakes_data(user_id: str, subject: str, error_type: str):
    """读取错题数据，使用 session_state 显式缓存，便于增删后精确失效"""
    cache_key = f"mistakes_data_{user_id}_{subject}_{error_type}"
    cache_time_key = cache_key + "_time"
    force_reload = st.session_state.get("mistakes_force_reload", False)

    cached = st.session_state.get(cache_key)
    cached_time = st.session_state.get(cache_time_key, 0)

    if cached is not None and not force_reload and (time.time() - cached_time) < DATA_CACHE_TTL:
        return cached

    errors, stats = st.session_state.memory.get_errors_with_stats(
        user_id=user_id,
        subject=subject if subject != "全部" else None,
        error_type=error_type if error_type != "全部" else None,
    )
    st.session_state[cache_key] = (errors, stats)
    st.session_state[cache_time_key] = time.time()
    st.session_state.mistakes_force_reload = False
    return errors, stats


def _invalidate_mistakes_cache():
    """标记缓存失效，下次读取时强制刷新"""
    st.session_state.mistakes_force_reload = True


def _render_record(err, render_latex, i):
    """Render a single error record expander."""
    score = err.get('score', '?')
    max_score = err.get('max_score', err.get('total_score', err.get('full_mark', '?')))
    record_id = err.get('record_id', '')
    is_view_only = err.get('engine') == 'view_only'

    if is_view_only:
        title_prefix = "👁 查看"
    elif score == 0:
        title_prefix = "❌ 答错"
    elif isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and score < max_score * 0.6:
        title_prefix = "⚠️ 部分正确"
    else:
        title_prefix = "📝 错题"

    with st.expander(
        f"{title_prefix} [{err.get('date', '?')}] "
        f"{err.get('knowledge_point', '未分类')[:30]} "
        f"— 得分 {score}/{max_score} "
        f"{'🔁 重复' if err.get('is_repeat') else ''}",
        expanded=(i < MAX_EXPANDED_ITEMS),
    ):
        with st.container(border=True):
            st.caption("📋 题目")
            _q = err.get("question", "")
            if _q:
                try:
                    render_latex(_q)
                except Exception:
                    st.markdown(_q)
            else:
                st.markdown("*（暂无题目内容）*")
            st.markdown("---")
            st.caption("✍️ 你的作答")
            student_ans = err.get("student_answer", "")
            if student_ans:
                try:
                    render_latex(student_ans)
                except Exception:
                    st.markdown(student_ans)
            else:
                st.markdown("*（未作答，仅查看标准答案）*")

        with st.container(border=True):
            st.caption("📖 标准答案")
            _sa = err.get("standard_answer", "")
            if _sa:
                try:
                    render_latex(_sa)
                except Exception:
                    st.text(_sa[:2000])
            else:
                st.markdown("*（暂无标准答案）*")
            solution_steps = err.get("solution_steps", [])
            
            # 如果没有结构化步骤，尝试从标准答案中解析
            if not solution_steps and _sa:
                try:
                    from latex_utils import from_legacy_text
                    structured = from_legacy_text(_sa)
                    if structured and structured.get("steps"):
                        solution_steps = structured["steps"]
                except Exception:
                    pass
            
            if solution_steps:
                with st.expander("📝 解题步骤", expanded=False):
                    for step in solution_steps:
                        if isinstance(step, dict):
                            label = step.get("label", step.get("num", ""))
                            st.markdown(f"**{label}**")
                            if step.get("blocks"):
                                from latex_utils import render_ast, split_latex_text, sanitize_latex_for_render
                                for b in step["blocks"]:
                                    if b.get("type") == "latex":
                                        try:
                                            st.latex(sanitize_latex_for_render(b.get("content", "")))
                                        except Exception:
                                            render_ast(split_latex_text(b.get("content", "")))
                                    else:
                                        render_ast(split_latex_text(b.get("content", "")))
                            elif step.get("content"):
                                render_latex(step["content"])
                        elif isinstance(step, str):
                            render_latex(step)
            elif _sa:
                # 如果没有步骤但有标准答案，尝试显示格式化的答案
                with st.expander("📝 解题步骤", expanded=False):
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        structured = from_legacy_text(_sa)
                        render_structured_safe(structured)
                    except Exception:
                        render_latex(_sa)

        with st.container(border=True):
            st.caption("🔍 批改详情")
            gm1, gm2, gm3 = st.columns(3)
            gm1.metric("得分", f"{score}/{max_score}")
            method = err.get("method_matched", "")
            gm2.metric("批改方法", method if method else err.get("engine", "未知"))
            confidence = err.get("confidence", 0)
            gm3.metric("置信度", f"{confidence:.0%}" if isinstance(confidence, (int, float)) and confidence > 0 else "N/A")
            step_analysis = err.get("step_analysis", [])
            if step_analysis:
                with st.expander("📊 逐步骤分析", expanded=True):
                    for sa in step_analysis:
                        if isinstance(sa, dict):
                            num = sa.get("num", "")
                            content = sa.get("content", "")
                            judgment = sa.get("judgment", "")
                            step_score = sa.get("score", "")
                            comment = sa.get("comment", "")
                            icon = "✅" if "正确" in str(judgment) else "⚠️"
                            st.markdown(f"{icon} **步骤{num}**: {judgment} ({step_score}分)")
                            if content:
                                render_latex(content)
                            if comment:
                                st.caption(f"  ↳ {comment}")
                        elif isinstance(sa, str):
                            render_latex(sa)
            comment = err.get("comment", err.get("analysis", ""))
            if comment:
                st.markdown("---")
                st.caption("💬 评语")
                st.info(comment)

        with st.container(border=True):
            st.caption("🏥 诊断分析")
            dm1, dm2 = st.columns(2)
            dm1.markdown(f"**错误类型**: {err.get('error_type', '?')}")
            root_cause = err.get("root_cause", err.get("error_reason", ""))
            dm2.markdown(f"**根本原因**: {root_cause}" if root_cause else "")
            weak_points = err.get("weak_points", [])
            knowledge_points = err.get("knowledge_points", [])
            all_kps = weak_points or knowledge_points
            if all_kps:
                kp_tags = " · ".join(all_kps[:8]) if isinstance(all_kps, list) else str(all_kps)
                st.caption(f"🎯 薄弱知识点: {kp_tags}")
            recommendations = err.get("recommendations", [])
            if recommendations:
                with st.expander("💡 改进建议", expanded=False):
                    for rec in recommendations:
                        st.markdown(f"- {rec}")
            common_mistakes = err.get("common_mistakes", [])
            if common_mistakes:
                with st.expander("⚠️ 常见错误", expanded=False):
                    for cm in common_mistakes:
                        st.markdown(f"- {cm}")

        st.markdown("---")
        if st.button("🗑 删除此记录", key=f"del_{record_id}",
                    help="从错题本中移除此记录"):
            st.session_state.memory.delete_error_record(
                st.session_state.auth['user_id'], record_id
            )
            _invalidate_mistakes_cache()
            st.rerun()


def render_mistakes_page(db, render_latex):
    st.title("📚 错题本")

    cf1, cf2, cf3 = st.columns(3)
    filter_subject = cf1.selectbox("科目", ["全部"] + SUBJECTS, key="filter_subject")
    filter_type = cf2.selectbox("错误类型", ["全部"] + ERROR_TYPES, key="filter_type")
    filter_diff = cf3.selectbox("难度", ["全部"] + DIFFICULTY_LEVELS, key="filter_diff")

    errors, stats = _get_mistakes_data(
        st.session_state.auth['user_id'], filter_subject, filter_type)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("错题总数", stats.total_errors)
    sc2.metric("重复率", f"{stats.repeat_rate:.1%}")
    sc3.metric("主要错误类型",
               max(stats.by_type, key=stats.by_type.get) if stats.by_type else "暂无")
    by_chapter = stats.by_chapter
    if by_chapter:
        top_chapter = max(by_chapter, key=by_chapter.get)
        sc4.metric("高频错误章节", top_chapter[:12] if top_chapter else "暂无")
    else:
        sc4.metric("高频错误章节", "暂无")

    if not errors:
        st.info("📭 错题本为空 — 开始刷题后，错题会自动记录到这里")
        return

    if by_chapter:
        with st.expander("📊 错误知识点分布", expanded=False):
            sorted_chapters = sorted(by_chapter.items(), key=lambda x: x[1], reverse=True)
            for chapter, count in sorted_chapters[:8]:
                bar_len = min(30, count * 3)
                st.caption(f"{'█' * bar_len} {chapter[:25]}: {count}次")
            st.caption("💡 建议针对高频错误章节进行专项训练")
            if st.button("🎯 开始专项训练", key="targeted_practice", width="stretch"):
                target_kp = sorted_chapters[0][0] if sorted_chapters else ""
                try:
                    qs = st.session_state.question_db.search(knowledge_point=target_kp, limit=1)
                    if qs:
                        st.session_state.selected_question = qs[0]
                        st.session_state.page = "practice"
                        st.rerun()
                except Exception:
                    st.session_state.page = "practice"
                    st.rerun()

    # ── 分页 ──
    total_pages = max(1, math.ceil(len(errors) / PAGE_SIZE))
    page_key = "mistakes_page_number"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    current_page = st.session_state[page_key]
    if current_page > total_pages:
        current_page = total_pages
        st.session_state[page_key] = current_page

    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(errors))

    if total_pages > 1:
        pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
        with pc1:
            if st.button("⏮ 首页", disabled=(current_page == 1), key="mp_first"):
                st.session_state[page_key] = 1; st.rerun()
        with pc2:
            if st.button("◀ 上一页", disabled=(current_page == 1), key="mp_prev"):
                st.session_state[page_key] = current_page - 1; st.rerun()
        with pc3:
            st.markdown(
                f"<div style='text-align:center;padding-top:5px;'>"
                f"第 {current_page} / {total_pages} 页（共 {len(errors)} 条）</div>",
                unsafe_allow_html=True)
        with pc4:
            if st.button("下一页 ▶", disabled=(current_page == total_pages), key="mp_next"):
                st.session_state[page_key] = current_page + 1; st.rerun()
        with pc5:
            if st.button("末页 ⏭", disabled=(current_page == total_pages), key="mp_last"):
                st.session_state[page_key] = total_pages; st.rerun()

    for i, err in enumerate(errors[start_idx:end_idx]):
        _render_record(err, render_latex, i)

    if total_pages > 1:
        st.caption(f"显示第 {start_idx + 1}-{end_idx} 条，共 {len(errors)} 条")
