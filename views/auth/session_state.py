"""Session State 管理 - 负责用户会话初始化和管理"""

from __future__ import annotations

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from repository.models import User, UserProfile, DashboardData

_REMEMBER_FILE = Path("storage/remember_me.json")


def init_user_session(user: User, remember: bool = False):
    """初始化用户会话状态"""
    # 认证状态
    st.session_state.auth = {
        "is_logged_in": True,
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_admin": user.is_admin,
        "login_time": user.updated_at,
    }
    
    # 用户对象
    st.session_state.current_user = user
    
    # 学习画像（延迟加载）
    st.session_state.profile = None
    
    # 仪表盘数据（延迟加载）
    st.session_state.dashboard = None
    
    # 当前学习状态
    st.session_state.learning_state = {
        "current_chapter": None,
        "current_question": None,
        "progress": 0,
    }
    
    # AI 记忆上下文
    st.session_state.memory_context = {
        "recent_errors": [],
        "learning_history": [],
    }
    
    # 题库连接
    from database import QuestionDB
    st.session_state.question_db = QuestionDB()
    
    # AI 记忆服务 — Supabase 优先（云端持久），不可用时回退本地 JSON
    from services import MemoryService
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    supabase_url = os.getenv("SUPABASE_URL", "") or getattr(st.secrets, "SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "") or getattr(st.secrets, "SUPABASE_KEY", "")
    if supabase_url and supabase_key:
        st.session_state.memory = MemoryService.with_supabase(
            db_path, data_dir, supabase_url, supabase_key
        )
    else:
        st.session_state.memory = MemoryService(db_path, data_dir)
    
    # LLM 客户端（延迟初始化）
    st.session_state.llm_client = None
    
    # 加载已保存的 API Key 配置
    try:
        import credential_store
        active_profile = credential_store.get_active_profile()
        if active_profile:
            st.session_state.api_key = active_profile.get("api_key", "")
            st.session_state.base_url = active_profile.get("base_url", "")
            st.session_state.model = active_profile.get("model", "")
            st.session_state.protocol = active_profile.get("protocol", "openai")
    except Exception:
        pass
    
    # 记住登录
    if remember:
        _save_remember_info(user.username)
    else:
        _clear_remember_info()


def clear_user_session():
    """清除用户会话状态"""
    keys_to_clear = [
        "auth",
        "current_user",
        "profile",
        "dashboard",
        "learning_state",
        "memory_context",
        "question_db",
        "memory",
        "llm_client",
        "ocr_result",
        "selected_question",
        "standard_answer",
        "grading_result",
        "diagnosis_result",
        "answer_view_mode",
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    _clear_remember_info()


def is_logged_in() -> bool:
    """检查用户是否已登录"""
    auth = st.session_state.get("auth", {})
    return auth.get("is_logged_in", False)


def get_current_user_id() -> str:
    """获取当前用户ID"""
    auth = st.session_state.get("auth", {})
    return auth.get("user_id", "")


def get_current_username() -> str:
    """获取当前用户名"""
    auth = st.session_state.get("auth", {})
    return auth.get("username", "")


def get_current_role() -> str:
    """获取当前用户角色"""
    auth = st.session_state.get("auth", {})
    return auth.get("role", "student")


def is_admin() -> bool:
    """检查当前用户是否是管理员"""
    auth = st.session_state.get("auth", {})
    return auth.get("is_admin", False)


def get_remembered_username() -> str:
    """获取记住的用户名"""
    info = _load_remember_info()
    return info.get("username", "")


def has_remembered_login() -> bool:
    """是否有记住的登录信息"""
    info = _load_remember_info()
    return bool(info.get("username"))


def try_auto_login():
    """尝试自动登录，返回是否成功"""
    info = _load_remember_info()
    username = info.get("username", "")
    token = info.get("token", "")
    
    if not username or not token:
        return False
    
    # 验证 token 是否有效
    from services import AuthService
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    auth_service = AuthService(db_path, data_dir)
    
    user = auth_service.get_user_by_username(username)
    if user and _verify_token(token, user.hashed_password):
        init_user_session(user, remember=True)
        return True
    
    _clear_remember_info()
    return False


def _save_remember_info(username: str):
    """保存记住登录信息"""
    from services import AuthService
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    auth_service = AuthService(db_path, data_dir)
    
    user = auth_service.get_user_by_username(username)
    if not user:
        return
    
    token = _generate_token(username, user.hashed_password)
    
    _REMEMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "username": username,
        "token": token,
        "saved_at": datetime.now().isoformat(),
    }
    
    with open(_REMEMBER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clear_remember_info():
    """清除记住登录信息"""
    if _REMEMBER_FILE.exists():
        _REMEMBER_FILE.unlink()


def _load_remember_info() -> dict:
    """加载记住登录信息"""
    if not _REMEMBER_FILE.exists():
        return {}
    
    try:
        with open(_REMEMBER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _generate_token(username: str, hashed_password: str) -> str:
    """生成记住登录的 token"""
    raw = f"{username}:{hashed_password}:math_tutor_remember"
    return hashlib.sha256(raw.encode()).hexdigest()


def _verify_token(token: str, hashed_password: str) -> bool:
    """验证 token"""
    info = _load_remember_info()
    username = info.get("username", "")
    expected = _generate_token(username, hashed_password)
    return token == expected
