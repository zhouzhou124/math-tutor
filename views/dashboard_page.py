"""Dashboard 页面 - 用户首页仪表盘"""

import streamlit as st
from .auth.session_state import get_current_user_id, get_current_username


def render_dashboard():
    """渲染仪表盘页面"""
    import traceback
    user_id = get_current_user_id()
    username = get_current_username()

    # 创建服务
    from pathlib import Path
    from services import DashboardService, MemoryService
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")

    dashboard_service = DashboardService(db_path, data_dir)
    memory_service = MemoryService(db_path, data_dir)

    # 获取仪表盘数据
    try:
        dashboard = dashboard_service.get_dashboard_data(user_id)
    except Exception:
        st.error(f"加载仪表盘数据失败:\n```\n{traceback.format_exc()}\n```")
        return

    # 欢迎信息
    try:
        st.markdown(f"""
            <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 20px;">
                <h2 style="color: white; font-size: 1.5rem;">欢迎回来，{username} 👋</h2>
                <p style="color: rgba(255,255,255,0.8);">继续你的数学学习之旅吧！</p>
            </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.error(f"渲染欢迎横幅失败:\n```\n{traceback.format_exc()}\n```")

    # 今日学习统计
    c1, c2, c3 = st.columns(3)
    with c1:
        try:
            st.metric("已完成题目", dashboard.total_questions,
                      delta=f"+{dashboard.total_questions} 题")
        except Exception:
            st.metric("已完成题目", "—")
    with c2:
        try:
            st.metric("正确率", f"{dashboard.overall_accuracy:.1%}", delta="今日表现")
        except Exception:
            st.metric("正确率", "—")
    with c3:
        try:
            st.metric("连续学习", f"{dashboard.streak_days} 天", delta="坚持就是胜利！")
        except Exception:
            st.metric("连续学习", "—")

    # 薄弱点分析
    st.subheader("📊 薄弱点分析")
    if dashboard.weak_points:
        for idx, point in enumerate(dashboard.weak_points, 1):
            st.warning(f"{idx}. {point}")
    else:
        st.info("暂无薄弱点记录，继续保持！")

    # 推荐练习
    st.subheader("🎯 推荐练习")
    r1, r2 = st.columns(2)
    with r1:
        if st.button("专项训练", width="stretch"):
            st.session_state.page = "practice"
            st.rerun()
    with r2:
        if st.button("错题回顾", width="stretch"):
            st.session_state.page = "error_notebook"
            st.rerun()

    # 学习进度
    st.subheader("📈 学习进度")
    if dashboard.chapter_stats:
        chapters = list(dashboard.chapter_stats.keys())[:5]
        accuracies = [dashboard.chapter_stats[c] * 100 for c in chapters]
        try:
            st.bar_chart(
                {"章节": chapters, "正确率": accuracies},
                x="章节", y="正确率",
                width="stretch",
            )
        except Exception:
            st.info("图表渲染失败，请刷新重试")
    else:
        st.info("开始做题，查看你的学习进度！")

    # 最近错题
    st.subheader("📝 最近错题")
    if dashboard.recent_errors:
        for error in dashboard.recent_errors[:5]:
            st.write(f"- **{error.knowledge_point}**: {error.question_id}")
    else:
        st.info("暂无错题记录")
