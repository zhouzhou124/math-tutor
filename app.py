"""
考研数学智能辅导系统
====================
5-Agent 协作：OCR → 解答 → 批改 → 诊断 → 记忆

启动: streamlit run app.py
"""

# ═══════════════════════════════════════════════
# 路径修复 + UTF-8 强制 — 必须在所有本地 import 之前
# ═══════════════════════════════════════════════
import sys, os
# UTF-8 全链路强制
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
try:
    _ROOT = os.path.dirname(os.path.realpath(__file__))
except NameError:
    _ROOT = os.path.realpath(os.getcwd())
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ═══════════════════════════════════════════════
# Streamlit 页面配置 — 必须在任何 st 命令之前！
# ═══════════════════════════════════════════════
import streamlit as st
st.set_page_config(
    page_title="Math Tutor - AI 考研数学智能辅导系统",
    page_icon="📘",
    layout="wide",
)

# ═══════════════════════════════════════════════
# 登录守卫逻辑
# ═══════════════════════════════════════════════
from views.auth.session_state import is_logged_in, try_auto_login

def main():
    """主应用入口"""
    # 检查登录状态
    if not is_logged_in():
        # 尝试自动登录
        if try_auto_login():
            from views.main_page import render_main_app
            render_main_app()
            return
        
        # 未登录，显示登录页面
        from views.auth.login_page import render_login_page
        render_login_page()
    else:
        # 已登录，显示主应用（管理员包含学生功能+管理功能）
        from views.main_page import render_main_app
        render_main_app()

if __name__ == "__main__":
    main()
