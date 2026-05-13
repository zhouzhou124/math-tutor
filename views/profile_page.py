"""pages/profile_page.py — 学习档案"""
import streamlit as st


def render_profile_page(db, render_latex):
    """..."""
    st.title("🎯 学习画像")

    profile = st.session_state.memory.get_profile()
    stats = st.session_state.memory.get_error_stats()

    # 阶段
    stage = profile.get("level", "强化阶段")
    stage_emoji = {"基础薄弱": "🔴", "强化阶段": "🔵", "冲刺阶段": "🟢"}
    st.markdown(f"### 当前阶段：{stage_emoji.get(stage, '')} {stage}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("各章节正确率")
        chapter_acc = profile.get("chapter_accuracy", {})
        if chapter_acc:
            for kp, acc in sorted(chapter_acc.items(), key=lambda x: x[1]):
                acc_pct = acc * 100
                bar_color = (
                    "#dc2626" if acc_pct < 40 else
                    "#d97706" if acc_pct < 60 else
                    "#2563eb" if acc_pct < 80 else
                    "#059669"
                )
                st.markdown(f"""
                <div style="margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
                        <span>{kp[:25]}</span><span style="font-weight:600;">{acc_pct:.0f}%</span>
                    </div>
                    <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
                        <div style="height:100%;width:{acc_pct}%;background:{bar_color};border-radius:4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无数据")

    with col2:
        st.subheader("薄弱知识点")
        weak = profile.get("weak_points", [])
        if weak:
            for i, w in enumerate(weak, 1):
                st.markdown(f"{i}. {w}")
        else:
            st.info("暂无数据 — 多刷题后系统会分析你的薄弱环节")

        st.subheader("错题类型分布")
        by_type = stats.get("by_type", {})
        if by_type:
            for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- {t}: {c} 次")

    # 复习建议
    st.subheader("📋 复习建议")
    recs = st.session_state.memory.get_recommendations()
    if not recs:
        recs = ["开始刷题以获取个性化建议"]
    for rec in recs:
        st.markdown(f"- {rec}")


    # ==================== 系统设置 ====================

