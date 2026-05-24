"""
mobile.py -- 移动端自适应模块

为 Streamlit 考研数学辅导系统注入响应式 CSS 和移动端底部导航栏。
"""

import streamlit as st

# ============================================================================
# 移动端 CSS -- 通过 st.markdown 注入全局样式
# ============================================================================

MOBILE_CSS = """
<style>
/* ================================================================
   移动端响应式全局样式
   ================================================================ */

/* --- 防下拉刷新：阻止浏览器默认的 pull-to-refresh --- */
html, body {
    overscroll-behavior: none !important;
    overscroll-behavior-y: contain !important;
    -webkit-overflow-scrolling: touch;
}
/* Streamlit 主容器也阻止 overscroll 传播 */
.main {
    overscroll-behavior: contain !important;
}

/* --- 基础重置 --- */
@media (max-width: 768px) {
    /* Streamlit 主容器：减少内边距，让内容撑满屏幕 */
    .main .block-container {
        padding: 0.75rem 0.5rem !important;
        max-width: 100% !important;
    }

    /* 隐藏 Streamlit 默认的 header/deploy 按钮，释放垂直空间 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    [data-testid="stToolbar"] {
        display: none !important;
    }

    /* 所有标题字体缩小 */
    h1 { font-size: 1.35rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 1rem !important; }
    h4 { font-size: 0.9rem !important; }

    /* 段落字体适应小屏 */
    p, span, div, li, label, .stMarkdown {
        font-size: 0.88rem !important;
    }

    /* 代码块允许横向滚动 */
    pre, code {
        font-size: 0.78rem !important;
        white-space: pre-wrap !important;
        word-break: break-all !important;
    }
}

/* --- 侧边栏：移动端完全隐藏，由底部导航替代 --- */
@media (max-width: 768px) {
    [data-testid="stSidebar"] {
        display: none !important;
    }
    /* 当 sidebar 不可见时，主区域不需要左边距 */
    .main > div:first-child {
        margin-left: 0 !important;
    }
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
}

/* --- 列布局：移动端强制堆叠 --- */
@media (max-width: 768px) {
    [data-testid="column"] {
        width: 100% !important;
        flex: 0 0 100% !important;
        max-width: 100% !important;
    }
    .stHorizontalBlock {
        flex-wrap: wrap !important;
    }
    .stHorizontalBlock > [data-testid="column"] {
        min-width: 100% !important;
    }
}

/* --- 按钮：移动端全宽 + 更大触摸目标 --- */
@media (max-width: 768px) {
    .stButton > button {
        width: 100% !important;
        min-height: 44px !important;
        font-size: 0.92rem !important;
        border-radius: 10px !important;
    }
    /* 小按钮（表格内、工具栏等）不强制全宽 */
    .stButton.compact > button {
        width: auto !important;
        min-height: 36px !important;
    }
}

/* --- 输入框和下拉框：增大触摸区域 --- */
@media (max-width: 768px) {
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox [data-baseweb="select"],
    .stNumberInput input {
        min-height: 44px !important;
        font-size: 16px !important;  /* 16px 防止 iOS 缩放 */
    }
    .stSelectbox [data-baseweb="select"] > div {
        min-height: 44px !important;
    }
}

/* --- 指标卡片 (st.metric) --- */
@media (max-width: 768px) {
    [data-testid="stMetric"] {
        padding: 10px 8px !important;
    }
    [data-testid="stMetric"] label {
        font-size: 0.8rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
}

/* --- 容器边框卡片 --- */
@media (max-width: 768px) {
    [data-testid="stExpander"] {
        margin-bottom: 8px !important;
    }
    .stContainer {
        margin-bottom: 10px !important;
    }
}

/* --- 表格：移动端横向滚动 --- */
@media (max-width: 768px) {
    [data-testid="stTable"] {
        overflow-x: auto !important;
        display: block !important;
    }
    [data-testid="stTable"] table {
        font-size: 0.8rem !important;
    }
}

/* --- 公式：移动端横向滚动，不压缩变形 --- */
@media (max-width: 768px) {
    img, svg, .katex-display, .katex {
        max-width: 100% !important;
        height: auto !important;
    }
    .katex-display {
        overflow-x: auto !important;
        overflow-y: hidden !important;
        white-space: nowrap !important;
        padding: 0.35rem 0 !important;
        margin: 0.65rem 0 !important;
        -webkit-overflow-scrolling: touch;
    }
    .katex-display > .katex {
        overflow-x: visible !important;
    }
    .katex {
        font-size: 1.02em !important;
    }
}

/* --- 移动端统一卡片样式 --- */
.mobile-card {
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 14px;
    background: #ffffff;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
    margin-bottom: 12px;
}
.mobile-card-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.mobile-card-subtitle {
    font-size: 0.82rem;
    color: #64748b;
}

/* --- Sticky action bar（批改按钮 / CTA）--- */
.mobile-sticky-action {
    position: sticky;
    bottom: 72px;  /* above bottom nav */
    z-index: 50;
    background: rgba(255,255,255,0.95);
    backdrop-filter: blur(8px);
    padding: 10px 12px;
    border-top: 1px solid #e5e7eb;
    margin: 0 -12px;
}
@media (max-width: 768px) {
    .mobile-sticky-action .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
    }
}

/* --- Equation number (tag extraction) --- */
.eq-number {
    text-align: right;
    white-space: nowrap;
    color: #475569;
    font-size: 1rem;
    line-height: 1.6;
    padding-top: 1.2rem;
    min-width: 2.5rem;
}
.eq-number-below {
    text-align: right;
    margin-top: -0.35rem;
    padding-right: 0.25rem;
    font-size: 0.95rem;
}
@media (max-width: 768px) {
    .eq-number {
        font-size: 0.95rem;
        padding-top: 1rem;
    }
    .eq-number-below {
        font-size: 0.9rem;
    }
}

/* --- Tabs: 移动端可滚动 --- */
@media (max-width: 768px) {
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
    }
    .stTabs button[role="tab"] {
        white-space: nowrap !important;
        font-size: 0.85rem !important;
        padding: 8px 12px !important;
    }
}

/* --- 文件上传 --- */
@media (max-width: 768px) {
    [data-testid="stFileUploader"] {
        padding: 8px !important;
    }
    [data-testid="stFileUploader"] section {
        padding: 12px !important;
    }
}

/* --- 提示消息 --- */
@media (max-width: 768px) {
    .stAlert {
        padding: 10px !important;
        font-size: 0.85rem !important;
    }
}

/* --- checkbox / radio --- */
@media (max-width: 768px) {
    .stCheckbox label, .stRadio label {
        font-size: 0.9rem !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
    }
}

/* ================================================================
   题目卡片操作区优化
   ================================================================ */
.qcard-actions-bar {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #e5e7eb;
}
/* 操作按钮行间距 */
.qcard-actions-bar .stHorizontalBlock {
    gap: 8px !important;
    margin-bottom: 6px !important;
}
@media (max-width: 768px) {
    .qcard-actions-bar .stButton > button {
        min-height: 42px !important;
        font-size: 0.85rem !important;
    }
}

/* ================================================================
   移动端底部导航栏 — 使用原生 st.columns + st.button
   ================================================================ */
@media (max-width: 768px) {
    /* 为底部导航栏留出空间 */
    .main .block-container {
        padding-bottom: calc(80px + env(safe-area-inset-bottom)) !important;
    }
}

/* --- 顶栏（移动端显示用户/标题） --- */
.mobile-topbar {
    display: none;
}
@media (max-width: 768px) {
    .mobile-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        background: #ffffff;
        border-bottom: 1px solid #e5e7eb;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .mobile-topbar .brand {
        font-weight: 700;
        font-size: 1rem;
        color: #1e293b;
    }
}
</style>
"""

# ============================================================================
# 移动端底部导航栏配置
# ============================================================================

NAV_ITEMS = [
    {"id": "dashboard",     "label": "仪表盘", "icon": "📊"},
    {"id": "practice",      "label": "刷题",   "icon": "✏️"},
    {"id": "grading",       "label": "批改",   "icon": "🤖"},
    {"id": "question_bank", "label": "题库",   "icon": "📚"},
    {"id": "error_notebook","label": "错题本", "icon": "📝"},
]


def inject_mobile_css():
    """注入移动端响应式 CSS。在 app.py 中 set_page_config 后立即调用。"""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def render_mobile_topbar():
    """渲染移动端顶部栏（仅在小屏幕上可见）。"""
    username = st.session_state.get("auth", {}).get("username", "")
    tc1, tc2 = st.columns([3, 1])
    with tc1:
        st.caption("📐 Math Tutor")
    with tc2:
        st.caption(username)


def render_mobile_nav():
    """渲染移动端底部导航栏。使用原生 st.columns + st.button，避免 HTML 被剥离。"""
    current_page = st.session_state.get("page", "dashboard")

    # Inject the nav container CSS separately (just the shell, no items)
    st.markdown('<div class="mobile-nav" id="mobile-nav"></div>', unsafe_allow_html=True)

    cols = st.columns(len(NAV_ITEMS))
    for i, item in enumerate(NAV_ITEMS):
        is_active = item["id"] == current_page
        label = f'{item["icon"]} {item["label"]}'
        with cols[i]:
            if st.button(
                label,
                key=f"mnav_{item['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.page = item["id"]
                st.rerun()


def set_grading_active(active: bool = True):
    """标记批改进行中。保留接口兼容，实际逻辑由页面状态管理。"""
    pass


_css_injected = False


def render_mobile_wrapper():
    """注入移动端响应式 CSS。侧边栏已提供页面导航。"""
    global _css_injected
    if not _css_injected:
        inject_mobile_css()
        _css_injected = True
