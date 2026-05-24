"""主应用页面 - 登录后的主界面"""

import streamlit as st
import time
from .auth.login_page import render_logout_button
from ._shared import NAV_MAP
from .auth.session_state import is_admin, get_current_username
from .dashboard_page import render_dashboard


# 数据缓存配置
CACHE_TTL = 300  # 缓存有效期（秒），5分钟


def get_cached_data(key: str, fetch_fn, ttl: int = CACHE_TTL):
    """
    获取缓存数据，如果缓存过期则重新获取
    
    Args:
        key: 缓存键
        fetch_fn: 数据获取函数
        ttl: 缓存有效期（秒）
        
    Returns:
        缓存的数据
    """
    now = time.time()
    
    # 检查缓存是否存在且未过期
    cache_key = f"cache_{key}"
    time_key = f"cache_{key}_time"
    
    if cache_key in st.session_state:
        cache_time = st.session_state.get(time_key, 0)
        if (now - cache_time) < ttl:
            return st.session_state[cache_key]
    
    # 缓存过期或不存在，重新获取
    data = fetch_fn()
    st.session_state[cache_key] = data
    st.session_state[time_key] = now
    return data


def invalidate_cache(key: str):
    """清除指定缓存"""
    cache_key = f"cache_{key}"
    time_key = f"cache_{key}_time"
    if cache_key in st.session_state:
        del st.session_state[cache_key]
    if time_key in st.session_state:
        del st.session_state[time_key]


def _clear_page_specific_state(from_page: str, to_page: str):
    """
    页面切换时清理特定页面的状态，防止状态污染导致卡住
    
    Args:
        from_page: 离开的页面
        to_page: 进入的页面
    """
    # 错题本相关状态（从错题本离开时清理）
    if from_page == "error_notebook":
        keys_to_clear = [
            "mistakes_force_reload",
            "_selected_error_record",
            "_deleting_record_id",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    # 进入真题库时清理相关状态
    if to_page == "question_bank":
        # 清除所有搜索缓存
        keys_to_remove = []
        for key in list(st.session_state.keys()):
            # 清除搜索缓存
            if key.startswith("search_cache_"):
                keys_to_remove.append(key)
            # 清除搜索缓存时间戳
            elif key.startswith("search_cache_time_"):
                keys_to_remove.append(key)
            # 清除真题库缓存
            elif key.startswith("cache_question_bank_"):
                keys_to_remove.append(key)
            # 清除真题库分页状态
            elif key == "qb_current_page":
                keys_to_remove.append(key)
        
        # 执行清除
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]


def _try_recover_grading_session():
    """Check SQLite for an unviewed completed grading task and restore it.

    Called at the beginning of every render_main_app() so that a user who
    returns after their browser tab was killed lands directly on their result.

    Uses a short session-level cache (30 s) — navigating between pages should
    NOT re-query SQLite every time.
    """
    page = st.session_state.get("page", "dashboard")
    if page != "dashboard":
        return  # Only intercept the default landing page

    # 30-second cache — avoid SQLite hit on every nav click
    _last_check = st.session_state.get("_recovery_last_check", 0)
    if time.time() - _last_check < 30:
        return
    st.session_state["_recovery_last_check"] = time.time()

    auth = st.session_state.get("auth", {})
    user_id = auth.get("user_id", "")
    if not user_id:
        return

    try:
        from storage.grading_task_store import get_recent_task, mark_viewed
        recent = get_recent_task(user_id)
        if not recent:
            return
        status = recent.get("status", "")
        if status != "completed":
            return

        import json
        # Restore grading results into session state
        for key, json_key in [
            ("grading_result", "grading_result_json"),
            ("diagnosis_result", "diagnosis_result_json"),
            ("standard_answer", "standard_answer_json"),
            ("standard_answer_structured", "standard_answer_structured_json"),
            ("ocr_result", "ocr_data_json"),
        ]:
            val = recent.get(json_key)
            if val:
                try:
                    st.session_state[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass

        st.session_state["answer_view_mode"] = True

        sq_json = recent.get("selected_q_json")
        if sq_json:
            try:
                st.session_state["selected_question"] = json.loads(sq_json)
            except (json.JSONDecodeError, TypeError):
                pass

        # Save deferred error record to 错题本
        error_json = recent.get("error_record_json")
        if error_json:
            try:
                error_record = json.loads(error_json)
                if error_record and st.session_state.get("memory"):
                    qid = error_record.get("question_id", "")
                    _seen = st.session_state.get("_saved_error_qids", set())
                    _dedup_key = f"{recent['user_id']}:{qid}"
                    if _dedup_key not in _seen:
                        _seen.add(_dedup_key)
                        st.session_state["_saved_error_qids"] = _seen
                        st.session_state.memory.add_error_record(
                            recent["user_id"], error_record
                        )
                        st.session_state.mistakes_force_reload = True
            except (json.JSONDecodeError, TypeError):
                pass

        mark_viewed(recent["task_id"])
        st.session_state["page"] = "grading"
    except Exception:
        pass  # Recovery is best-effort; never block normal rendering


def render_main_app():
    """渲染主应用"""

    # ── Mobile: responsive CSS + topbar + bottom nav ──
    from .mobile import render_mobile_wrapper
    render_mobile_wrapper()

    # ── Recovery: on fresh session, check for unviewed grading results ──
    _try_recover_grading_session()

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
        
        # 设置当前页面映射 (extend shared NAV_MAP with extra entries)
        nav_map = dict(NAV_MAP, **{
            "学习报告": "report",
            "系统设置": "settings",
        })
        
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
        
        # ── 导航 selectbox ──
        # Sync the selectbox to current_page ONLY when the page was changed
        # externally (e.g. "开始练习" button).  When the user clicks the
        # selectbox itself we must NOT overwrite their choice.
        nav_key = "nav_select"
        current_page = st.session_state.get("page", "dashboard")
        _prev_page = st.session_state.get("_prev_page", "")

        current_label = all_options[0]
        for label, pid in nav_map.items():
            if pid == current_page:
                current_label = label
                break

        if _prev_page != current_page:
            # External page change → sync selectbox
            st.session_state[nav_key] = current_label

        selected_label = st.selectbox(
            "导航菜单",
            all_options,
            key=nav_key,
            label_visibility="collapsed",
        )

        st.session_state["_prev_page"] = current_page

        # User clicked a different option → navigate
        selected_page = nav_map.get(selected_label, "dashboard")
        if selected_page != current_page:
            # 清理可能导致页面切换卡住的状态
            _clear_page_specific_state(current_page, selected_page)
            st.session_state.page = selected_page
            st.rerun()
        
        st.divider()
        
        # 管理员标识
        if is_admin():
            st.markdown("👑 **管理员模式**")
        
        # 登出按钮
        render_logout_button()
    
    # 主内容区域 — 隔离容器，确保页面切换时旧内容被完整替换
    main_container = st.container()
    with main_container:
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
    """渲染真题库页面（优化版）"""
    from .question_bank_page import render_question_bank_page
    from latex_utils import safe_render
    
    # 使用缓存机制
    db = st.session_state.question_db
    
    # 获取缓存的统计数据
    def fetch_stats():
        return db.stats()
    
    stats = get_cached_data("question_bank_stats", fetch_stats, ttl=60)
    
    # 渲染页面（传递缓存的统计数据）
    render_question_bank_page(db, safe_render, cached_stats=stats)


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