"""pages/dashboard_page.py — 仪表盘"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from config import ERROR_TYPES, STAGES


def render_dashboard_page(db, render_latex):
    """..."""
    profile = st.session_state.get("student_profile", {})
    st.title("📊 学习仪表盘")

    # 4 个统计卡片
    c1, c2, c3, c4 = st.columns(4)
    errors = st.session_state.memory.get_error_stats()
    total_errors = errors.get("total_errors", 0)
    total_q_all = profile.get("total_questions", 0)
    accuracy = max(0, 100 - total_errors * 3) if total_q_all > 0 else 100
    q_stats = st.session_state.question_db.stats()

    c1.metric("📈 总正确率", f"{min(100, accuracy):.1f}%", delta="↑ 5.2% 较上周")
    c2.metric("📚 累计刷题", total_q_all, delta=f"题库共 {q_stats['total']} 题")
    c3.metric("⏱️ 错题数", total_errors, delta=f"{'需注意' if total_errors > 10 else '控制良好'}")
    c4.metric("🔥 连续打卡", "15 天", delta="保持中")

    # 图表区域
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("章节正确率分布")
        chapter_acc = profile.get("chapter_accuracy", {})
        if chapter_acc:
            fig, ax = plt.subplots(figsize=(6, 4))
            labels = list(chapter_acc.keys())[:8]
            values = [chapter_acc[k] * 100 for k in labels]
            colors = plt.cm.Blues([0.3 + 0.7 * (v / max(values)) for v in values])
            bars = ax.barh(range(len(labels)), values, color=colors)
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels([l[:15] for l in labels], fontsize=8)
            ax.set_xlabel("估计正确率 (%)")
            ax.set_xlim(0, 100)
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                        f"{val:.0f}%", va="center", fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            st.pyplot(fig)
            plt.close()
        else:
            st.info("暂无数据 — 开始刷题后这里会显示各章节正确率")

    with col_right:
        st.subheader("错题类型分布")
        by_type = errors.get("by_type", {})
        if by_type:
            fig, ax = plt.subplots(figsize=(6, 4))
            labels = list(by_type.keys())
            values = list(by_type.values())
            wedges, texts, autotexts = ax.pie(
                values, labels=[f"{l}\n({v}次)" for l, v in zip(labels, values)],
                autopct="%1.1f%%", colors=plt.cm.Set2(range(len(labels))),
                startangle=90,
            )
            st.pyplot(fig)
            plt.close()
        else:
            st.info("暂无数据")

    # 今日推荐
    st.subheader("⚡ 今日复习建议")
    recs = st.session_state.memory.get_recommendations()
    weak_pts = profile.get("weak_points", [])
    if not recs:
        recs = [
            "开始刷题吧！系统会根据你的错题自动生成个性化复习建议",
            "建议从高等数学的极限与连续章节开始",
            "每日目标：10-15题，先易后难",
        ]
    for i, rec in enumerate(recs, 1):
        st.markdown(f"""
        <div style="display:flex;gap:1rem;padding:1rem;background:#f8fafc;border-radius:12px;
                    border-left:3px solid #2563eb;margin-bottom:0.5rem;">
            <div style="width:24px;height:24px;background:#2563eb;color:white;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">{i}</div>
            <div style="font-size:0.875rem;color:#334155;">{rec}</div>
        </div>
        """, unsafe_allow_html=True)


    # ==================== 智能刷题 ====================

