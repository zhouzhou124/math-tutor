"""pages/mistakes_page.py — 错题本"""
import streamlit as st
from config import SUBJECTS, ERROR_TYPES, DIFFICULTY_LEVELS


def render_mistakes_page(db, render_latex):
    """..."""
    st.title("📚 错题本")

    # 筛选
    cf1, cf2, cf3 = st.columns(3)
    filter_subject = cf1.selectbox("科目", ["全部"] + SUBJECTS, key="filter_subject")
    filter_type = cf2.selectbox("错误类型", ["全部"] + ERROR_TYPES, key="filter_type")
    filter_diff = cf3.selectbox("难度", ["全部"] + DIFFICULTY_LEVELS, key="filter_diff")

    errors = st.session_state.memory.get_errors(
        subject=filter_subject if filter_subject != "全部" else None,
        error_type=filter_type if filter_type != "全部" else None,
    )

    stats = st.session_state.memory.get_error_stats()
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("错题总数", stats.get("total_errors", 0))
    sc2.metric("重复率", f"{stats.get('repeat_rate', 0):.1%}")
    sc3.metric("主要错误类型",
               max(stats.get("by_type", {}), key=stats.get("by_type", {}).get)
               if stats.get("by_type") else "暂无")

    # 按知识点错误分布
    by_chapter = stats.get("by_chapter", {})
    if by_chapter:
        top_chapter = max(by_chapter, key=by_chapter.get)
        sc4.metric("高频错误章节", top_chapter[:12] if top_chapter else "暂无")
    else:
        sc4.metric("高频错误章节", "暂无")

    if not errors:
        st.info("📭 错题本为空 — 开始刷题后，错题会自动记录到这里")
    else:
        # 错误知识点分布
        if by_chapter:
            with st.expander("📊 错误知识点分布", expanded=False):
                sorted_chapters = sorted(by_chapter.items(), key=lambda x: x[1], reverse=True)
                for chapter, count in sorted_chapters[:8]:
                    bar_len = min(30, count * 3)
                    bar = "█" * bar_len
                    st.caption(f"{bar} {chapter[:25]}: {count}次")
                st.caption("💡 建议针对高频错误章节进行专项训练")
                if st.button("🎯 开始专项训练", key="targeted_practice", use_container_width=True):
                    # 跳转到刷题页，预选该知识点
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

        for i, err in enumerate(errors):
            with st.expander(
                f"[{err.get('date', '?')}] {err.get('knowledge_point', '未分类')[:30]} "
                f"— 得分 {err.get('score', '?')}/{err.get('total_score', '?')} "
                f"{'🔁 重复' if err.get('is_repeat') else ''}",
                expanded=(i == 0),
            ):
                # 上面：题目和作答
                with st.container(border=True):
                    st.caption("📋 题目")
                    render_latex(err.get("question", ""))
                    
                    st.markdown("---")
                    
                    st.caption("✍️ 你的作答")
                    render_latex(err.get("student_answer", ""))
                
                # 下面：标准答案和错误信息
                with st.container(border=True):
                    st.caption("📖 标准答案")
                    render_latex(err.get("standard_answer", ""))
                    
                    st.markdown("---")
                    
                    st.caption(f"🏷️ 错误类型：{err.get('error_type', '?')}")
                    st.caption(f"💡 原因：{err.get('error_reason', '?')}")


    # ==================== 学习画像 ====================

