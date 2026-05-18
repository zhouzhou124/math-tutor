"""Auth Guard - 页面保护组件"""

import streamlit as st
from .session_state import is_logged_in


def auth_guard():
    """认证守卫 - 如果未登录则显示登录页面并停止执行"""
    if not is_logged_in():
        # 导入放在内部避免循环导入
        from .login_page import render_login_page
        
        render_login_page()
        st.stop()
