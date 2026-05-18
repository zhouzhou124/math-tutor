"""Views Layer - 页面视图层"""

from .auth.login_page import render_login_page, render_logout_button
from .auth.auth_guard import auth_guard
from .auth.session_state import (
    init_user_session,
    clear_user_session,
    is_logged_in,
    try_auto_login,
    get_current_user_id,
    get_current_username,
    get_current_role,
    is_admin,
)

__all__ = [
    "render_login_page",
    "render_logout_button",
    "auth_guard",
    "init_user_session",
    "clear_user_session",
    "is_logged_in",
    "try_auto_login",
    "get_current_user_id",
    "get_current_username",
    "get_current_role",
    "is_admin",
]
