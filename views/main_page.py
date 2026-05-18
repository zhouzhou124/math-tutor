"""主应用页面 - 登录后的主界面"""

import streamlit as st
import time
from .auth.login_page import render_logout_button
from .auth.session_state import is_admin, get_current_username
from .dashboard_page import render_dashboard


# 防抖配置
DEBOUNCE_DELAY = 300  # 毫秒，快速点击防抖延迟


def debounce_page_switch(page_name: str) -> bool:
    """
    页面切换防抖函数
    
    Args:
        page_name: 目标页面名称
        
    Returns:
        bool: 是否应该执行页面切换
    """
    now = time.time() * 1000  # 毫秒
    
    # 初始化状态
    if "last_switch_time" not in st.session_state:
        st.session_state.last_switch_time = 0
    if "last_switch_page" not in st.session_state:
        st.session_state.last_switch_page = ""
    
    # 如果是同一页面，允许切换（用于刷新）
    if st.session_state.last_switch_page == page_name:
        st.session_state.last_switch_time = now
        return True
    
    # 检查是否在防抖时间内
    time_since_last_switch = now - st.session_state.last_switch_time
    
    if time_since_last_switch < DEBOUNCE_DELAY:
        # 在防抖时间内，忽略这次点击
        return False
    
    # 更新状态
    st.session_state.last_switch_time = now
    st.session_state.last_switch_page = page_name
    return True


def render_main_app():
    """渲染主应用"""
    
    # 侧边栏
    with st.sidebar:
        st.title("📘 Math Tutor")
        st.write("AI 考研数学智能辅导系统")
        st.divider()
        
        # 学生导航菜单
        st.subheader("学习")
        nav_options = ["仪表盘", "智能刷题", "AI批改", "真题库", "错题本", "学习报告", "系统设置"]
        
        # 管理员额外菜单
        if is_admin():
            st.divider()
            st.subheader("管理")
            admin_options = ["概览统计", "用户管理", "AI 批改监控", "题库状态", "数据回放", "题库管理"]
            all_options = nav_options + admin_options
        else:
            all_options = nav_options
        
        # 设置当前页面
        nav_map = {
            "仪表盘": "dashboard",
            "智能刷题": "practice",
            "AI批改": "grading",
            "真题库": "question_bank",
            "错题本": "error_notebook",
            "学习报告": "report",
            "系统设置": "settings",
        }
        
        if is_admin():
            admin_map = {
                "概览统计": "admin_overview",
                "用户管理": "admin_users",
                "AI 批改监控": "admin_grading",
                "题库状态": "admin_bank_status",
                "数据回放": "admin_replay",
                "题库管理": "admin_questions",
            }
            nav_map.update(admin_map)
        
        # 获取当前页面对应的导航索引
        current_page = st.session_state.get("page", "dashboard")
        default_index = 0
        for i, option in enumerate(all_options):
            if nav_map.get(option) == current_page:
                default_index = i
                break
        
        selected_nav = st.radio("", all_options, index=default_index)
        target_page = nav_map.get(selected_nav, "dashboard")
        
        # 使用防抖机制
        if debounce_page_switch(target_page):
            st.session_state.page = target_page
        
        st.divider()
        
        # 管理员标识
        if is_admin():
            st.markdown("👑 **管理员模式**")
        
        # 登出按钮
        render_logout_button()
    
    # 主内容区域
    page = st.session_state.get("page", "dashboard")
    
    # 学生页面
    if page == "dashboard":
        render_dashboard()
    elif page == "practice":
        render_practice_page()
    elif page == "question_bank":
        render_question_bank_page()
    elif page == "grading":
        render_grading_page()
    elif page == "error_notebook":
        render_error_notebook_page()
    elif page == "report":
        render_report_page()
    elif page == "settings":
        render_settings_page()
    
    # 管理员页面
    elif page == "admin_overview":
        from .admin_dashboard import render_overview
        render_overview()
    elif page == "admin_users":
        from .admin_dashboard import render_user_management
        render_user_management()
    elif page == "admin_grading":
        from .admin_dashboard import render_grading_monitor
        render_grading_monitor()
    elif page == "admin_bank_status":
        from .admin_dashboard import render_question_bank_status
        render_question_bank_status()
    elif page == "admin_replay":
        from .admin_dashboard import render_data_replay
        render_data_replay()
    elif page == "admin_questions":
        from .admin_dashboard import render_question_management
        render_question_management()


def render_practice_page():
    """渲染智能刷题页面"""
    from .practice_page import render_practice_page
    render_practice_page(st.session_state.question_db)


def render_grading_page():
    """渲染 AI 批改页面"""
    from .grading_page import render_grading_page
    from latex_utils import safe_render
    render_grading_page(st.session_state.question_db, safe_render)


def render_question_bank_page():
    """渲染真题库页面"""
    from .question_bank_page import render_question_bank_page
    from latex_utils import safe_render
    render_question_bank_page(st.session_state.question_db, safe_render)


def render_error_notebook_page():
    """渲染错题本页面"""
    from .mistakes_page import render_mistakes_page
    from latex_utils import safe_render
    render_mistakes_page(st.session_state.question_db, safe_render)


def render_report_page():
    """渲染学习报告页面"""
    st.title("📊 学习报告")
    st.info("学习报告功能开发中...")


def render_settings_page():
    """渲染系统设置页面"""
    from .settings_page import render_settings_page
    from latex_utils import safe_render
    render_settings_page(st.session_state.question_db, safe_render)
