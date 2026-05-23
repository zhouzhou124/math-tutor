"""pages/mistakes_page.py — 错题本"""
import streamlit as st
import math
import time
from config import SUBJECTS, ERROR_TYPES, DIFFICULTY_LEVELS

PAGE_SIZE = 10           # Fewer records per page = lighter render
DATA_CACHE_TTL = 30      # Longer cache so nav doesn't re-parse JSON

import re as _re


def _extract_plaintext_preview(text: str, max_len: int = 70) -> str:
    """Strip LaTeX and markdown, return plain text fingerprint of a question.

    Used for lightweight mistake list cards — no LaTeX rendering needed.
    """
    if not text:
        return ""
    s = text
    # Remove $$...$$ blocks (display math)
    s = _re.sub(r'\$\$[^$]*\$\$', '', s)
    # Remove $...$ blocks (inline math) — keep content between them
    s = _re.sub(r'\$([^$]+?)\$', r'\1', s)
    # Remove LaTeX commands: \frac{...}{...}, \sqrt{...}, \int, \sum, etc.
    s = _re.sub(r'\\[a-zA-Z]+(?:\{[^}]*\})*', '', s)
    # Remove \left, \right, \mathrm, \mathbf, \begin, \end etc.
    s = _re.sub(r'\\begin\{[^}]*\}', '', s)
    s = _re.sub(r'\\end\{[^}]*\}', '', s)
    # Remove remaining backslash-prefixed tokens
    s = _re.sub(r'\\[;:,.\s]', ' ', s)
    # Remove markdown headers and formatting
    s = _re.sub(r'#{1,6}\s*', '', s)
    s = _re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    s = _re.sub(r'\*([^*]+)\*', r'\1', s)
    # Remove braces, matrix markers, etc.
    s = s.replace('{', '').replace('}', '')
    s = _re.sub(r'[&_^~]', ' ', s)
    # Collapse whitespace
    s = _re.sub(r'\s+', ' ', s)
    # Remove standalone numbers/punctuation at edges
    s = s.strip(' ，。、；：！？\n\r\t0123456789.()（）[]【】')
    s = _re.sub(r'^\s*\$?\d+\.?\$?\s*', '', s)  # Remove question number prefix like "$1.$"
    s = _re.sub(r'^\s*[（(]\s*\d+\s*[）)]\s*', '', s)  # Remove "(1)" prefix
    s = _re.sub(r'\s*本题满分\d+分\s*', '', s)  # Remove score annotation
    # Trim to max_len, breaking at word boundary
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0]
    return s.strip()


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


def _render_record_lightweight(err, i):
    """Lightweight card — plain text only, no LaTeX, no markdown, no expander.

    Layout follows fingerprint pattern:
      [emoji + question_preview]  [score]  [date]
      [knowledge_point tags]     [error preview]
    """
    score = err.get('score', '?')
    max_score = err.get('max_score', err.get('total_score', err.get('full_mark', '?')))
    record_id = err.get('record_id', '')
    is_view_only = err.get('engine') == 'view_only'

    if is_view_only:
        emoji = "👁"
    elif isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        emoji = "✅" if score / max_score >= 0.9 else ("⚠️" if score / max_score >= 0.6 else "❌")
    else:
        emoji = "📝"

    # Question fingerprint — plain text preview, no LaTeX
    q_preview = err.get('question_preview', '')
    if not q_preview:
        db_q = err.get('_db_question')
        if db_q:
            raw = db_q.get('raw_question_text') or db_q.get('question', '')
            q_preview = _extract_plaintext_preview(raw)
        else:
            q_preview = _extract_plaintext_preview(err.get('question', ''))

    # Structured fields from new schema
    wrong_reason = err.get('wrong_reason_short', '') or err.get('preview', '') or err.get('error_type', '')
    tags = err.get('semantic_tags', []) or err.get('knowledge_points', [])
    q_hash = err.get('question_preview_hash', '')
    render_cost = err.get('render_cost_level', '')

    date = err.get('date', '?')

    with st.container(border=True):
        # Row 1: question fingerprint (the "what") + score
        r1_left, r1_right = st.columns([5, 1])
        with r1_left:
            hash_tag = f" `#{q_hash}`" if q_hash else ""
            st.caption(f"{emoji}{hash_tag} {q_preview[:70]}" if q_preview else f"{emoji} (题面缺失)")
        with r1_right:
            st.caption(f"**{score}/{max_score}**")
            if render_cost == 'HIGH':
                st.caption("⚡慢")

        # Row 2: semantic tags + wrong reason
        r2_left, r2_right = st.columns([3, 2])
        with r2_left:
            tag_str = " · ".join(tags[:4])
            st.caption(tag_str[:60] if tag_str else "")
        with r2_right:
            st.caption(f"📝 {wrong_reason[:40]}" if wrong_reason else date)

        # Row 3: date + actions (详情 / 已掌握 / 归档)
        r3_left, r3_a, r3_b, r3_c = st.columns([2, 1, 1, 1])
        with r3_left:
            st.caption(date)
        with r3_a:
            if st.button("📋", key=f"mistake_btn_{record_id}", help="查看详情", use_container_width=True):
                st.session_state._mistake_detail = record_id
        with r3_b:
            if st.button("✅", key=f"mistake_master_{record_id}", help="已掌握", use_container_width=True):
                st.session_state["_status_change"] = (record_id, "MASTERED")
        with r3_c:
            if st.button("📦", key=f"mistake_archive_{record_id}", help="归档", use_container_width=True):
                st.session_state["_status_change"] = (record_id, "ARCHIVED")


def _render_record_full(err, render_latex, db=None):
    """Render full AI grading detail — only called for the ONE selected record."""
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
        expanded=True,
    ):
        with st.container(border=True):
            st.caption("📋 题目")
            # Prefer the structured question dict from the bank (same rendering
            # path as the grading page), falling back to raw-text rendering.
            _qid = err.get("question_id", "")
            _q = err.get("question", "")
            _rendered = False
            # 优先用预加载缓存，没有才调 db.get
            db_q = err.get("_db_question")
            if not db_q and _qid and db:
                try:
                    db_q = db.get(_qid)
                except Exception:
                    db_q = None
            if db_q and isinstance(db_q, dict) and (db_q.get("raw_question_text") or db_q.get("question")):
                try:
                    from renderers import render_question
                    render_question(db_q, show_actions=False)
                    _rendered = True
                except Exception:
                    pass
            if not _rendered and _q:
                try:
                    render_latex(_q)
                except Exception:
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        render_structured_safe(from_legacy_text(_q))
                    except Exception:
                        st.text(str(_q)[:2000])
            elif not _rendered:
                st.markdown("*（暂无题目内容）*")
            st.markdown("---")
            st.caption("✍️ 你的作答")
            student_ans = err.get("student_answer", "")
            if student_ans:
                try:
                    render_latex(student_ans)
                except Exception:
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        render_structured_safe(from_legacy_text(student_ans))
                    except Exception:
                        st.text(str(student_ans)[:2000])
            else:
                st.markdown("*（未作答，仅查看标准答案）*")

        with st.container(border=True):
            st.caption("📖 标准答案")
            _sa = err.get("standard_answer", "")
            _sid = err.get("question_id", "")
            _sol_steps = err.get("solution_steps", [])
            # 记录中没有则从缓存/题库查（去冗余优化后记录不存全文）
            db_q2 = err.get("_db_question")
            if not _sa and _sid and (db_q2 or db):
                try:
                    if not db_q2 and db:
                        db_q2 = db.get(_sid)
                    if db_q2:
                        _sa = db_q2.get("raw_answer_text") or db_q2.get("standard_answer", "")
                        _sol_steps = _sol_steps or db_q2.get("solution_steps", [])
                except Exception:
                    pass
            if _sa:
                try:
                    render_latex(_sa)
                except Exception:
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        render_structured_safe(from_legacy_text(_sa))
                    except Exception:
                        st.text(str(_sa)[:2000])
            else:
                st.markdown("*（暂无标准答案）*")
            solution_steps = _sol_steps

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
                            _rendered = False
                            _sc = str(step.get("content", ""))
                            # Route A — blocks format (from from_legacy_text)
                            if step.get("blocks"):
                                from latex_utils import _render_blocks_safe
                                try:
                                    _render_blocks_safe(step["blocks"])
                                    _rendered = True
                                except Exception:
                                    pass
                            # Route B — content format (from _parse_steps_from_text)
                            if not _rendered and _sc:
                                try:
                                    from latex_utils import from_legacy_text, render_structured_safe
                                    render_structured_safe(from_legacy_text(_sc))
                                    _rendered = True
                                except Exception:
                                    pass
                            # Ultimate fallback
                            if not _rendered and _sc:
                                st.text(_sc[:2000])
                        elif isinstance(step, str):
                            try:
                                render_latex(step)
                            except Exception:
                                st.text(str(step)[:2000])
            elif _sa:
                # 如果没有步骤但有标准答案，尝试显示格式化的答案
                with st.expander("📝 解题步骤", expanded=False):
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        structured = from_legacy_text(_sa)
                        render_structured_safe(structured)
                    except Exception:
                        render_latex(_sa)

        # ── Proof obligation warning ──
        _obl_warn = err.get("obligation_warning", "")
        if _obl_warn:
            st.warning(_obl_warn)

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
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✅ 已掌握", key=f"master_{record_id}",
                        help="标记为已掌握，从错题本移除", use_container_width=True):
                st.session_state["_status_change"] = (record_id, "MASTERED")
                st.rerun()
        with c2:
            if st.button("📦 归档", key=f"archive_{record_id}",
                        help="归档此记录（可恢复）", use_container_width=True):
                st.session_state["_status_change"] = (record_id, "ARCHIVED")
                st.rerun()
        with c3:
            _qid = err.get("question_id", "")
            if st.button("🔁 重做", key=f"reprac_{record_id}",
                        help="回到练习页面重新作答", use_container_width=True):
                if _qid and db:
                    try:
                        db_q = db.get(_qid)
                        if db_q:
                            st.session_state.selected_question = db_q
                            st.session_state.page = "practice"
                            st.rerun()
                    except Exception:
                        pass
                st.session_state.page = "practice"
                st.rerun()


def render_mistakes_page(db, render_latex):
    st.title("📚 错题本")

    # ── Lifecycle state changes: selectbox sets _status_change → processed here
    _status_change = st.session_state.pop("_status_change", None)
    if _status_change:
        record_id, new_status = _status_change
        try:
            memory = st.session_state.get("memory")
            user_id = st.session_state.auth.get("user_id", "")
            if memory and user_id and hasattr(memory, 'update_error_status'):
                memory.update_error_status(user_id, record_id, new_status)
                _invalidate_mistakes_cache()
        except Exception:
            pass
        st.rerun()

    # ── Deprecated hard-delete path (kept for backward compat)
    _delete_id = st.session_state.pop("_delete_id", None)
    if _delete_id:
        try:
            user_id = st.session_state.auth.get("user_id", "")
            memory = st.session_state.get("memory")
            if user_id and memory and hasattr(memory, 'update_error_status'):
                memory.update_error_status(user_id, _delete_id, "ARCHIVED")
                _invalidate_mistakes_cache()
        except Exception:
            pass
        st.rerun()

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
                    qs = st.session_state.question_db.search(knowledge_point=target_kp, limit=5)
                    if qs:
                        st.session_state.selected_question = qs[0]
                        st.session_state.page = "practice"
                        st.rerun()
                except Exception:
                    pass
                # Fallback: navigate to practice anyway
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

    # ── 冷热分离：列表只显示轻量卡片，点击才渲染完整 AI 内容 ──
    _detail_id = st.session_state.get("_mistake_detail")
    _page_record_ids = {e.get("record_id", "") for e in errors[start_idx:end_idx]}
    if _detail_id and _detail_id not in _page_record_ids:
        _detail_id = None
        st.session_state.pop("_mistake_detail", None)

    # 预加载详情记录所需的 DB 数据
    if _detail_id and db:
        _detail_err = next((e for e in errors if e.get("record_id") == _detail_id), None)
        if _detail_err:
            _qid = _detail_err.get("question_id", "")
            if _qid:
                try:
                    _detail_err["_db_question"] = db.get(_qid)
                except Exception:
                    pass

    if _detail_id:
        # 详情模式：只渲染详情记录 + 返回按钮，不渲染轻量列表
        _detail_err = next((e for e in errors[start_idx:end_idx]
                           if e.get("record_id") == _detail_id), None)
        if _detail_err:
            try:
                _render_record_full(_detail_err, render_latex, db=db)
            except Exception:
                st.error(f"渲染记录 {_detail_id} 时出错，已跳过")
            st.markdown("---")
            if st.button("↩️ 返回列表", key="mistake_back_to_list"):
                st.session_state.pop("_mistake_detail", None)
                st.rerun()
        else:
            # 详情记录不在当前页，回退到列表
            st.session_state.pop("_mistake_detail", None)
            st.rerun()
    else:
        # 列表模式：只渲染轻量卡片
        for i, err in enumerate(errors[start_idx:end_idx]):
            try:
                _render_record_lightweight(err, i)
            except Exception:
                st.caption(f"记录 {err.get('record_id', '?')} 加载失败")

    # Force Streamlit to flush
    st.markdown("")

    if total_pages > 1:
        st.caption(f"显示第 {start_idx + 1}-{end_idx} 条，共 {len(errors)} 条")
