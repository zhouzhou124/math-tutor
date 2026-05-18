"""Dashboard 页面 - 用户首页仪表盘"""

import streamlit as st
from .auth.session_state import get_current_user_id, get_current_username


def render_dashboard():
    """渲染仪表盘页面"""
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
    dashboard = dashboard_service.get_dashboard_data(user_id)
    
    # 欢迎信息
    st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 20px;">
            <h2 style="color: white; font-size: 1.5rem;">欢迎回来，{username} 👋</h2>
            <p style="color: rgba(255,255,255,0.8);">继续你的数学学习之旅吧！</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 今日学习统计
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="已完成题目",
            value=dashboard.total_questions,
            delta=f"+{dashboard.total_questions} 题"
        )
    
    with col2:
        st.metric(
            label="正确率",
            value=f"{dashboard.overall_accuracy:.1%}",
            delta="今日表现"
        )
    
    with col3:
        st.metric(
            label="连续学习",
            value=f"{dashboard.streak_days} 天",
            delta="坚持就是胜利！"
        )
    
    # 薄弱点分析
    st.subheader("📊 薄弱点分析")
    if dashboard.weak_points:
        for idx, point in enumerate(dashboard.weak_points, 1):
            st.warning(f"{idx}. {point}")
    else:
        st.info("暂无薄弱点记录，继续保持！")
    
    # 推荐练习
    st.subheader("🎯 推荐练习")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("专项训练", use_container_width=True):
            st.session_state.page = "practice"
            st.rerun()
    
    with col2:
        if st.button("错题回顾", use_container_width=True):
            st.session_state.page = "error_notebook"
            st.rerun()
    
    # 学习进度
    st.subheader("📈 学习进度")
    if dashboard.chapter_stats:
        chapters = list(dashboard.chapter_stats.keys())[:5]
        accuracies = [dashboard.chapter_stats[c] * 100 for c in chapters]
        
        st.bar_chart(
            {"章节": chapters, "正确率": accuracies},
            x="章节",
            y="正确率",
            use_container_width=True
        )
    else:
        st.info("开始做题，查看你的学习进度！")
    
    # 最近错题
    st.subheader("📝 最近错题")
    if dashboard.recent_errors:
        for error in dashboard.recent_errors[:5]:
            st.write(f"- **{error.knowledge_point}**: {error.question_id}")
    else:
        st.info("暂无错题记录")
