"""登录页面 - 负责登录和注册的 UI"""

import streamlit as st
from .session_state import init_user_session, clear_user_session, get_remembered_username, try_auto_login


def render_login_page():
    """渲染登录页面"""
    
    # 顶部 Logo 和标题
    st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="font-size: 2.5rem; margin-bottom: 10px;">📘 Math Tutor</h1>
            <p style="color: #666; font-size: 1.1rem;">AI 考研数学智能辅导系统</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Tab 切换
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        render_login_form()
    
    with tab2:
        render_register_form()


def render_login_form():
    """渲染登录表单"""
    st.subheader("登录")
    
    # 读取记住的用户名
    remembered_username = get_remembered_username()
    
    # 表单
    username = st.text_input(
        "用户名", 
        value=remembered_username,
        placeholder="请输入用户名", 
        key="login_username"
    )
    password = st.text_input("密码", type="password", placeholder="请输入密码", key="login_password")
    
    # 记住登录状态：如果之前记住过，默认勾选
    default_remember = bool(remembered_username)
    remember_me = st.checkbox("记住登录状态", value=default_remember, key="login_remember")

    if st.button("登录", width="stretch", key="login_btn"):
        # 验证输入
        if not username or not password:
            st.error("请输入用户名和密码")
            return
        
        # 创建服务
        from pathlib import Path
        from services import AuthService
        db_path = Path("storage/math_tutor.db")
        data_dir = Path("storage/data")
        
        auth_service = AuthService(db_path, data_dir)
        
        # 执行登录
        user_id = auth_service.login(username, password)
        
        if user_id:
            # 获取用户信息
            user = auth_service.get_user(user_id)
            
            if user:
                # 初始化会话（传入 remember 参数）
                init_user_session(user, remember=remember_me)
                
                # 重新加载页面
                st.rerun()
            else:
                st.error("获取用户信息失败")
        else:
            st.error("用户名或密码错误")


def render_register_form():
    """渲染注册表单"""
    st.subheader("注册")
    
    # 表单
    username = st.text_input("用户名", placeholder="请输入用户名", key="register_username")
    email = st.text_input("邮箱（可选）", placeholder="请输入邮箱地址", key="register_email")
    password = st.text_input("密码", type="password", placeholder="请输入密码", key="register_password")
    confirm_password = st.text_input("确认密码", type="password", placeholder="请再次输入密码", key="register_confirm_password")

    if st.button("注册", width="stretch", key="register_btn"):
        # 验证输入
        if not username:
            st.error("请输入用户名")
            return
        
        if not password:
            st.error("请输入密码")
            return
        
        if password != confirm_password:
            st.error("两次输入的密码不一致")
            return
        
        # 创建服务
        from pathlib import Path
        from services import AuthService
        db_path = Path("storage/math_tutor.db")
        data_dir = Path("storage/data")
        
        auth_service = AuthService(db_path, data_dir)
        
        # 执行注册
        user_id = auth_service.register(username, password, email)
        
        if user_id:
            st.success("注册成功！请登录")
        else:
            st.error("注册失败，用户名可能已存在")


def render_logout_button():
    """渲染登出按钮"""
    if st.session_state.get("auth", {}).get("is_logged_in"):
        if st.sidebar.button("退出登录"):
            clear_user_session()
            st.rerun()
