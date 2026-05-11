"""
考研数学智能辅导系统
====================
5-Agent 协作：OCR → 解答 → 批改 → 诊断 → 记忆

启动: streamlit run app.py
"""

# ═════════════════════════════pop══════════════════
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
# 硬编码兜底
if os.path.isdir(r"E:\math_tutor") and r"E:\math_tutor" not in sys.path:
    sys.path.insert(0, r"E:\math_tutor")

import html
import json
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import time
from openai import OpenAI

from config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    MATH_TYPES, SUBJECTS, QUESTION_TYPES, DIFFICULTY_LEVELS,
    ERROR_TYPES, STAGES, KNOWLEDGE_POINTS,
)
from database import QuestionDB, QuestionImporter
from agents import OCR_Agent, SolverAgent, GradingAgent, DiagnosisAgent, MemoryAgent
from user_loop import UserLoop
from solution_graph import SolutionGraph, make_choice_graph, make_fill_blank_graph
from symbolic_executor import quick_compare, ErrorLevel
from question_entity import (
    AlignmentValidator, EntityValidator,
    build_entity, EntityStatus,
)
try:
    from latex_normalizer import normalize_latex_style
except ModuleNotFoundError:
    # 兜底：确保路径正确后再试
    import sys as _sys, os as _os
    _FALLBACK = r"E:\math_tutor"
    if _os.path.isdir(_FALLBACK) and _FALLBACK not in _sys.path:
        _sys.path.insert(0, _FALLBACK)
    from latex_normalizer import normalize_latex_style

# ────────────────── matplotlib 中文字体 ──────────────────
import matplotlib.font_manager as fm
_CHINESE_FONTS = [f for f in fm.findSystemFonts() if 'simhei' in f.lower() or 'simsun' in f.lower() or 'msyh' in f.lower() or 'Microsoft YaHei' in f.lower()]
if _CHINESE_FONTS:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
elif any('noto' in f.lower() for f in fm.findSystemFonts()):
    plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Sans SC', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
else:
    # 兜底：尝试常见中文字体名
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

# ────────────────── 页面配置 ──────────────────
st.set_page_config(
    page_title="考研数学智能辅导系统",
    page_icon="∑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ────────────────── 自定义 CSS ──────────────────
st.markdown("""
<style>
    :root {
        --primary: #1d4ed8;
        --primary-soft: #dbeafe;
        --ink: #0f172a;
        --muted: #64748b;
        --line: #dbe4ef;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --accent: #0f766e;
        --warning: #b45309;
        --danger: #b91c1c;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    html, body, [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 12% 0%, rgba(29, 78, 216, 0.08), transparent 28rem),
            linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%);
        color: var(--ink);
    }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1320px !important;
    }

    h1, h2, h3 {
        color: var(--ink);
        letter-spacing: 0;
    }

    h1 {
        font-size: 2rem !important;
        font-weight: 760 !important;
        margin-bottom: 1.15rem !important;
    }

    h2, h3 {
        font-weight: 700 !important;
    }

    p, label, div[data-testid="stMarkdownContainer"] {
        line-height: 1.72;
    }

    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.94);
        border-right: 1px solid var(--line);
        box-shadow: 10px 0 30px rgba(15, 23, 42, 0.04);
    }

    .stMetric {
        background: rgba(255, 255, 255, 0.94);
        padding: 1rem !important;
        border-radius: 8px !important;
        border: 1px solid var(--line) !important;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.055);
        background: rgba(255, 255, 255, 0.92);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.35rem;
        border-bottom: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1rem;
    }

    .stTabs [aria-selected="true"] {
        background: white;
        color: var(--primary);
        border: 1px solid var(--line);
        border-bottom-color: white;
    }

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 650 !important;
        min-height: 2.55rem;
        border-color: #cbd5e1 !important;
        transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--primary) !important;
        box-shadow: 0 10px 20px rgba(29, 78, 216, 0.12);
    }

    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        border-radius: 8px !important;
        border-color: #cbd5e1 !important;
        background: rgba(255, 255, 255, 0.96) !important;
    }

    [data-testid="stFileUploader"] {
        border: 2px dashed #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 2rem !important;
        text-align: center !important;
        background: #f8fafc;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--primary) !important;
        background: var(--primary-soft) !important;
    }

    .stTextArea textarea {
        font-family: 'Noto Serif SC', serif !important;
        font-size: 1rem !important;
        line-height: 1.8 !important;
    }

    .question-card-head {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        margin-bottom: 0.65rem;
        color: var(--muted);
        font-size: 0.86rem;
        font-weight: 650;
    }

    .question-id-pill {
        color: #ffffff;
        background: #0f172a;
        border-radius: 999px;
        padding: 0.18rem 0.58rem;
        font-size: 0.76rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .meta-panel {
        border-left: 1px solid var(--line);
        padding-left: 1.05rem;
        height: 100%;
    }

    .meta-title {
        font-size: 0.76rem;
        color: var(--muted);
        font-weight: 700;
        letter-spacing: 0;
        margin: 0.25rem 0 0.35rem 0;
    }

    .chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-bottom: 0.75rem;
    }

    .chip {
        display: inline-flex;
        align-items: center;
        min-height: 1.7rem;
        border-radius: 999px;
        padding: 0.18rem 0.58rem;
        border: 1px solid #cbd5e1;
        background: #f8fafc;
        color: #334155;
        font-size: 0.78rem;
        font-weight: 650;
        max-width: 100%;
    }

    .chip-accent {
        border-color: #99f6e4;
        background: #ecfdf5;
        color: #0f766e;
    }

    .chip-warning {
        border-color: #fed7aa;
        background: #fff7ed;
        color: #9a3412;
    }

    .answer-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 1rem 1.1rem;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.055);
    }
</style>
""", unsafe_allow_html=True)

# ────────────────── API Key 持久化 ──────────────────
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "storage", "settings.json")

def load_settings() -> dict:
    """加载持久化的设置"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                # Never reload secrets from disk. Use LLM_API_KEY or the current
                # Streamlit session for API credentials.
                settings.pop("api_key", None)
                return settings
        except Exception:
            pass
    return {}

def save_settings(settings: dict):
    """保存设置到文件"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    settings = dict(settings)
    settings.pop("api_key", None)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ────────────────── Session 初始化 ──────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "llm_client" not in st.session_state:
    st.session_state.llm_client = None
if "memory" not in st.session_state:
    st.session_state.memory = MemoryAgent()
if "question_db" not in st.session_state:
    st.session_state.question_db = QuestionDB()
if "user_loop" not in st.session_state:
    st.session_state.user_loop = UserLoop(
        st.session_state.question_db,
        st.session_state.memory,
    )
# 加载持久化的非敏感设置；API Key 只来自环境变量或当前会话
_saved = load_settings()
if "base_url" not in st.session_state:
    st.session_state.base_url = _saved.get("base_url", LLM_BASE_URL)
if "model" not in st.session_state:
    st.session_state.model = _saved.get("model", LLM_MODEL)
if "api_key" not in st.session_state:
    st.session_state.api_key = LLM_API_KEY
if st.session_state.get("api_key") and st.session_state.llm_client is None:
    try:
        st.session_state.llm_client = OpenAI(
            api_key=st.session_state.api_key,
            base_url=st.session_state.base_url,
        )
    except Exception:
        pass
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None  # 从题库选中的题目
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "standard_answer" not in st.session_state:
    st.session_state.standard_answer = None
if "answer_view_mode" not in st.session_state:
    st.session_state.answer_view_mode = False
if "grading_result" not in st.session_state:
    st.session_state.grading_result = None
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None


def get_client():
    """获取或创建 LLM 客户端"""
    if st.session_state.llm_client is None and st.session_state.get("api_key"):
        st.session_state.llm_client = OpenAI(
            api_key=st.session_state.api_key,
            base_url=st.session_state.get("base_url", LLM_BASE_URL),
        )
    return st.session_state.llm_client


def render_latex(text: str) -> None:
    """规范化 + 渲染 LaTeX。所有显示数学内容的地方统一入口。"""
    if text:
        st.markdown(normalize_latex_style(text))


def render_latex_caption(text: str) -> None:
    """规范化 + 渲染 LaTeX 为小字说明"""
    if text:
        st.caption(normalize_latex_style(text))


def _chip(label: str, variant: str = "") -> str:
    cls = "chip"
    if variant:
        cls += f" {variant}"
    return f'<span class="{cls}">{html.escape(label)}</span>'


def render_question_meta_panel(question: dict) -> None:
    """Render compact right-side metadata for a question card."""
    knowledge_points = question.get("knowledge_points") or question.get("tags") or ["未标注"]
    mistakes = question.get("common_mistakes") or ["暂无记录"]
    difficulty = question.get("difficulty", "中等")

    kp_html = "".join(_chip(str(kp), "chip-accent") for kp in knowledge_points[:6])
    mistake_html = "".join(_chip(str(item), "chip-warning") for item in mistakes[:4])
    diff_html = _chip(str(difficulty))

    st.markdown(
        f"""
        <div class="meta-panel">
            <div class="meta-title">知识点</div>
            <div class="chip-row">{kp_html}</div>
            <div class="meta-title">难度</div>
            <div class="chip-row">{diff_html}</div>
            <div class="meta-title">常见错误</div>
            <div class="chip-row">{mistake_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ────────────────── 侧栏导航 ──────────────────
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.75rem;padding:1rem 0 1.5rem 0;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#2563eb,#1d4ed8);
                    border-radius:8px;display:flex;align-items:center;justify-content:center;
                    color:white;font-size:1.2rem;font-weight:700;">∑</div>
        <span style="font-size:1.25rem;font-weight:700;color:#2563eb;">考研数学智辅</span>
    </div>
    """, unsafe_allow_html=True)

    # 学习阶段
    profile = st.session_state.memory.get_profile()
    stage = profile.get("level", "强化阶段")
    stage_colors = {"基础薄弱": "#dc2626", "强化阶段": "#2563eb", "冲刺阶段": "#059669"}
    st.markdown(f"""
    <div style="padding:0.5rem 0.75rem;background:#dbeafe;color:#1d4ed8;border-radius:8px;
                font-size:0.8rem;font-weight:600;display:inline-flex;align-items:center;gap:0.5rem;">
        <span style="width:6px;height:6px;background:{stage_colors.get(stage, '#2563eb')};
                     border-radius:50%;animation:pulse 2s infinite;"></span>
        {stage}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 主要功能
    st.caption("主要功能")
    pages = {
        "dashboard": ("📊", "学习仪表盘"),
        "practice": ("✏️", "智能刷题"),
        "grading": ("📝", "AI 批改"),
        "question_bank": ("📋", "真题库"),
    }
    for page_id, (icon, label) in pages.items():
        active = st.session_state.page == page_id
        if st.button(f"{icon} {label}", key=f"nav_{page_id}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.page = page_id
            st.rerun()

    st.markdown("")
    st.caption("学习管理")
    manage_pages = {
        "mistakes": ("📚", "错题本"),
        "profile": ("🎯", "学习画像"),
    }
    for page_id, (icon, label) in manage_pages.items():
        active = st.session_state.page == page_id
        if st.button(f"{icon} {label}", key=f"nav_{page_id}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.page = page_id
            st.rerun()

    st.markdown("")
    st.caption("设置")
    if st.button("⚙️ 系统设置", key="nav_settings",
                 use_container_width=True,
                 type="primary" if st.session_state.page == "settings" else "secondary"):
        st.session_state.page = "settings"
        st.rerun()

    # 底部进度卡
    st.markdown("---")
    stats = st.session_state.memory.get_error_stats()
    total_q = profile.get("total_questions", 0)
    weekly_goal = 60
    progress_pct = min(100, int(total_q / weekly_goal * 100))

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1e293b,#0f172a);color:white;
                padding:1rem;border-radius:12px;font-size:0.85rem;">
        <div style="opacity:0.7;font-size:0.75rem;margin-bottom:0.25rem;">本周刷题进度</div>
        <div style="font-size:1.2rem;font-weight:700;">{total_q} / {weekly_goal} 题</div>
        <div style="height:6px;background:rgba(255,255,255,0.2);border-radius:3px;margin-top:0.5rem;">
            <div style="height:100%;width:{progress_pct}%;
                        background:linear-gradient(90deg,#60a5fa,#3b82f6);border-radius:3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ────────────────── 页面路由 ──────────────────
page = st.session_state.page


# ==================== 学习仪表盘 ====================
if page == "dashboard":
    st.title("📊 学习仪表盘")

    # 4 个统计卡片
    c1, c2, c3, c4 = st.columns(4)
    errors = st.session_state.memory.get_error_stats()
    total_errors = errors.get("total_errors", 0)
    total_q_all = profile.get("total_questions", 0)
    accuracy = max(0, 100 - total_errors * 3) if total_q_all > 0 else 100
    q_stats = st.session_state.question_db.stats()

    c1.metric("📈 总正确率", f"{min(100, accuracy):.1f}%", delta="↑ 5.2% 较上周")
    c2.metric("📚 累计刷题", total_q_all, delta=f"题库共 {q_stats['total']} 题")
    c3.metric("⏱️ 错题数", total_errors, delta=f"{'需注意' if total_errors > 10 else '控制良好'}")
    c4.metric("🔥 连续打卡", "15 天", delta="保持中")

    # 图表区域
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("章节正确率分布")
        chapter_acc = profile.get("chapter_accuracy", {})
        if chapter_acc:
            fig, ax = plt.subplots(figsize=(6, 4))
            labels = list(chapter_acc.keys())[:8]
            values = [chapter_acc[k] * 100 for k in labels]
            colors = plt.cm.Blues([0.3 + 0.7 * (v / max(values)) for v in values])
            bars = ax.barh(range(len(labels)), values, color=colors)
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels([l[:15] for l in labels], fontsize=8)
            ax.set_xlabel("估计正确率 (%)")
            ax.set_xlim(0, 100)
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                        f"{val:.0f}%", va="center", fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            st.pyplot(fig)
            plt.close()
        else:
            st.info("暂无数据 — 开始刷题后这里会显示各章节正确率")

    with col_right:
        st.subheader("错题类型分布")
        by_type = errors.get("by_type", {})
        if by_type:
            fig, ax = plt.subplots(figsize=(6, 4))
            labels = list(by_type.keys())
            values = list(by_type.values())
            wedges, texts, autotexts = ax.pie(
                values, labels=[f"{l}\n({v}次)" for l, v in zip(labels, values)],
                autopct="%1.1f%%", colors=plt.cm.Set2(range(len(labels))),
                startangle=90,
            )
            st.pyplot(fig)
            plt.close()
        else:
            st.info("暂无数据")

    # 今日推荐
    st.subheader("⚡ 今日复习建议")
    recs = st.session_state.memory.get_recommendations()
    weak_pts = profile.get("weak_points", [])
    if not recs:
        recs = [
            "开始刷题吧！系统会根据你的错题自动生成个性化复习建议",
            "建议从高等数学的极限与连续章节开始",
            "每日目标：10-15题，先易后难",
        ]
    for i, rec in enumerate(recs, 1):
        st.markdown(f"""
        <div style="display:flex;gap:1rem;padding:1rem;background:#f8fafc;border-radius:12px;
                    border-left:3px solid #2563eb;margin-bottom:0.5rem;">
            <div style="width:24px;height:24px;background:#2563eb;color:white;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;font-size:0.75rem;
                        font-weight:700;flex-shrink:0;">{i}</div>
            <div style="font-size:0.875rem;color:#334155;">{rec}</div>
        </div>
        """, unsafe_allow_html=True)


# ==================== 智能刷题 ====================
elif page == "practice":
    st.title("✏️ 智能刷题")

    tab_upload, tab_text = st.tabs(["📷 图片上传", "⌨️ 文本输入"])

    with tab_upload:
        col_q, col_a = st.columns(2)
        with col_q:
            st.subheader("📋 上传题目图片")
            question_file = st.file_uploader(
                "题目图片", type=["png", "jpg", "jpeg"],
                key="q_upload", label_visibility="collapsed"
            )
            if question_file:
                st.image(question_file, use_container_width=True)

        with col_a:
            st.subheader("✍️ 上传作答图片")
            answer_file = st.file_uploader(
                "作答图片", type=["png", "jpg", "jpeg"],
                key="a_upload", label_visibility="collapsed"
            )
            if answer_file:
                st.image(answer_file, use_container_width=True)

        # 元数据
        st.markdown("---")
        mc1, mc2, mc3, mc4 = st.columns(4)
        math_type = mc1.selectbox("数学类别", MATH_TYPES, key="mt_upload")
        q_type = mc2.selectbox("题型", QUESTION_TYPES, key="qt_upload")
        difficulty = mc3.selectbox("难度", DIFFICULTY_LEVELS, key="diff_upload")
        kp = mc4.selectbox("知识点", ["自动识别"] + sum(KNOWLEDGE_POINTS.values(), []), key="kp_upload")

        if st.button("🔍 识别并批改", type="primary", use_container_width=True,
                     disabled=not question_file):
            client = get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                with st.spinner("OCR 识别中..."):
                    # 保存上传文件到临时路径
                    import tempfile
                    q_path = None
                    a_path = None
                    if question_file:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                            f.write(question_file.read())
                            q_path = f.name
                    if answer_file:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                            f.write(answer_file.read())
                            a_path = f.name

                    ocr_agent = OCR_Agent(client, st.session_state.get("model", LLM_MODEL))
                    st.session_state.ocr_result = ocr_agent.recognize(q_path, a_path)

                if st.session_state.ocr_result.get("success"):
                    st.success("OCR 识别完成")
                    st.session_state.answer_view_mode = False
                    st.session_state.page = "grading"
                    st.rerun()
                else:
                    st.error(f"OCR 识别失败: {'; '.join(st.session_state.ocr_result.get('warnings', []))}")

    with tab_text:
        # 智能推荐：基于薄弱知识点
        if not st.session_state.get("selected_question"):
            st.subheader("🎯 智能推荐")
            profile = st.session_state.memory.get_profile()
            weak_points = profile.get("weak_points", [])
            if weak_points:
                w1, w2, w3 = st.columns(3)
                for i, wp in enumerate(weak_points[:3]):
                    col = [w1, w2, w3][i]
                    with col:
                        # 获取该知识点的题目数
                        try:
                            qs = st.session_state.question_db.search(knowledge_point=wp, limit=1)
                            count = len(qs)
                        except Exception:
                            count = "?"
                        if st.button(f"📝 {wp[:15]} ({count}题)", key=f"rec_{i}", use_container_width=True):
                            try:
                                qs = st.session_state.question_db.search(knowledge_point=wp, limit=1)
                                if qs:
                                    st.session_state.selected_question = qs[0]
                                    st.rerun()
                            except Exception:
                                pass
                st.markdown("---")

        # 从题库加载的题目
        selected = st.session_state.get("selected_question")
        if selected:
            st.info(f"📋 已加载题目: {selected.get('question_id', '?')} — "
                    f"{selected.get('category', '')} {selected.get('question_type', '')} "
                    f"| 知识点: {', '.join(selected.get('knowledge_points', [])[:3])}")
            if st.button("↩️ 返回题库", key="back_to_bank"):
                st.session_state.selected_question = None
                st.rerun()

        col_q2, col_a2 = st.columns(2)
        with col_q2:
            st.subheader("📋 题目内容")
            default_q = selected.get("question", "") if selected else ""
            # 仅展示渲染后的 LaTeX，不显示原始代码编辑框
            if default_q:
                with st.container(border=True):
                    render_latex(default_q)
            else:
                # 手动输入模式（无选中题目时）
                question_text = st.text_area(
                    "请输入题目（支持 LaTeX）",
                    height=250, key="q_text", label_visibility="collapsed",
                )
            question_text = default_q  # 使用选中题目，不可编辑
        with col_a2:
            st.subheader("✍️ 你的解答")
            st.caption("使用 $...$ 包裹公式，如 $\\int_0^1 x^2 dx = \\frac{1}{3}$")
            student_answer = st.text_area(
                "请输入你的解题过程（支持 LaTeX）",
                height=220, key="a_text", label_visibility="collapsed"
            )
            if student_answer:
                with st.container(border=True):
                    st.markdown(student_answer)

        mc1, mc2, mc3, mc4 = st.columns(4)
        math_type_t = mc1.selectbox("数学类别", MATH_TYPES, key="mt_text")
        q_type_t = mc2.selectbox("题型", QUESTION_TYPES, key="qt_text")
        difficulty_t = mc3.selectbox("难度", DIFFICULTY_LEVELS, key="diff_text")
        kp_t = mc4.selectbox("知识点", sum(KNOWLEDGE_POINTS.values(), []), key="kp_text")

        if st.button("🚀 提交批改", type="primary", use_container_width=True,
                     disabled=not question_text):
            client = get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                st.session_state.ocr_result = {
                    "success": True,
                    "question": question_text,
                    "student_answer": student_answer,
                    "math_type": math_type_t,
                    "question_type": q_type_t,
                    "knowledge_point": kp_t,
                    "confidence": 1.0,
                    "warnings": [],
                }
                st.session_state.answer_view_mode = False
                st.session_state.page = "grading"
                st.rerun()


# ==================== AI 批改 ====================
elif page == "grading":
    st.title("📖 查看答案" if st.session_state.get("answer_view_mode", False) else "📝 AI 批改")

    ocr_data = st.session_state.ocr_result

    if ocr_data is None:
        st.info("请先在「智能刷题」页面上传或输入题目")
        if st.button("➡️ 前往刷题"):
            st.session_state.page = "practice"
            st.rerun()
    else:
        question = ocr_data.get("question", "")
        student_ans = ocr_data.get("student_answer", "")
        answer_view_mode = st.session_state.get("answer_view_mode", False)

        # 题目信息
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.markdown(f"**数学类别**: {ocr_data.get('math_type', '未指定')}")
        mc2.markdown(f"**题型**: {ocr_data.get('question_type', '未识别')}")
        mc3.markdown(f"**知识点**: {ocr_data.get('knowledge_point', '未识别')}")
        mc4.markdown(f"**OCR置信度**: {ocr_data.get('confidence', 0):.0%}")

        # 两栏：题目 + 学生作答
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.caption("📋 题目")
                render_latex(question)
        with col2:
            with st.container(border=True):
                st.caption("✍️ 学生作答")
                if student_ans:
                    render_latex(student_ans)
                else:
                    st.markdown("（未作答）")

        # 知识点提示
        selected_q = st.session_state.get("selected_question") or {}
        kp_list = selected_q.get("knowledge_points", [])
        if kp_list:
            kp_tags = " · ".join(kp_list[:6])
            st.caption(f"🏷️ 考查知识点: {kp_tags}")

        if answer_view_mode and st.session_state.standard_answer:
            st.markdown("---")
            st.subheader("📖 标准答案")
            with st.container(border=True):
                render_latex(st.session_state.standard_answer.get("standard_answer", "暂无答案"))
            st.caption("答案仅在此处完整渲染展示，题库列表不展示答案内容。")

        # 批改按钮
        if not answer_view_mode and st.button("🔍 开始批改", type="primary", use_container_width=True):
            client = get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                progress = st.progress(0, text="正在准备批改...")
                model = st.session_state.get("model", LLM_MODEL)
                selected_q = st.session_state.get("selected_question") or {}

                # Step 1: 获取标准答案（优先用数据库缓存，跳过LLM生成）
                # 题库已预计算标准答案，直接读取无需AI重新求解
                cached_answer = selected_q.get("standard_answer", "")
                if cached_answer and len(cached_answer.strip()) > 1:
                    solution = {
                        "success": True,
                        "standard_answer": cached_answer,
                        "total_score": selected_q.get("score", 10),
                        "steps": selected_q.get("solution_steps", []),
                    }
                    progress.progress(20, text="已加载缓存标准答案，正在批改...")
                else:
                    solver = SolverAgent(client, model)
                    solution = solver.solve(
                        question=question,
                        math_type=ocr_data.get("math_type", "数学一"),
                        question_type=ocr_data.get("question_type", "解答题"),
                        knowledge_point=ocr_data.get("knowledge_point", "未指定"),
                    )
                    progress.progress(25, text="标准解答生成完成，正在批改...")
                st.session_state.standard_answer = solution

                # Step 2: 批改 — Engine A 快速路径(选择/填空) vs Engine B LLM路径(解答/证明)
                q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
                std_ans = solution.get("standard_answer", "")
                total_score = solution.get("total_score", 10)
                is_fast_path = q_type in ("选择题", "填空题") and std_ans

                if is_fast_path:
                    # Engine A: 规则引擎快速判分 (<100ms, 无LLM调用)
                    import re
                    stu = (student_ans or "").strip()
                    correct_option = selected_q.get("correct_option", "")
                    if q_type == "选择题" and correct_option:
                        # 提取学生答案中的选项字母
                        stu_letter = None
                        for m in re.finditer(r'[A-D]', stu.upper()):
                            stu_letter = m.group(0)
                        is_correct = (stu_letter == correct_option)
                        score = total_score if is_correct else 0
                        gresult = {
                            "success": True, "total": score, "step_score": score, "result_score": 0,
                            "step_analysis": [], "deductions": [],
                            "comment": "正确" if is_correct else f"错误, 正确选项为 {correct_option}",
                        }
                    else:
                        # 填空题: 符号等价比较 (SymPy symbolic compare)
                        from symbolic_executor import quick_compare, ErrorLevel
                        result = quick_compare(stu, std_ans)
                        is_correct = result["equivalent"]
                        score = total_score if is_correct else 0
                        gresult = {
                            "success": True, "total": score, "step_score": score, "result_score": 0,
                            "step_analysis": [], "deductions": [],
                            "comment": "正确" if is_correct else (
                                "计算错误" if result["error_level"] == ErrorLevel.LEVEL_1
                                else f"错误, 标准答案为 {std_ans[:100]}"
                            ),
                        }
                    dresult = {
                        "error_type": "无错误" if is_correct else ("选择题错误" if q_type == "选择题" else "填空题错误"),
                        "root_cause": "" if is_correct else f"标准答案为 {std_ans[:80]}",
                        "is_repeat": False, "repeat_count": 0,
                        "affects_future": False, "weak_points": [],
                    }
                    progress.progress(80, text="快速批改完成，正在保存...")
                else:
                    # Engine B: LLM 批改 (解答题/证明题, 或缓存未命中)
                    grading = GradingAgent(client, model)
                    gresult = grading.grade(
                        question=question, standard_answer=std_ans,
                        student_answer=student_ans, total_score=total_score,
                        knowledge_points=ocr_data.get("knowledge_point", ""),
                        difficulty=selected_q.get("difficulty", "中等"),
                    )
                    progress.progress(65, text="批改完成，正在诊断分析...")

                    # Step 3: 诊断（仅解答题需要AI分析）
                    diagnosis = DiagnosisAgent(client, model)
                    history = st.session_state.memory.get_errors(
                        knowledge_point=ocr_data.get("knowledge_point", "")
                    )
                    dresult = diagnosis.diagnose(
                        question=question, student_answer=student_ans,
                        standard_answer=std_ans, grading_result=gresult,
                        error_history=history,
                    )
                st.session_state.grading_result = gresult
                st.session_state.diagnosis_result = dresult
                progress.progress(85, text="正在保存到错题本...")

                # Step 4: 保存到错题本
                if gresult.get("total", 0) < solution.get("total_score", 10) * 0.9:
                    error_record = {
                        "math_type": ocr_data.get("math_type", ""),
                        "question": question[:500],
                        "student_answer": student_ans[:500],
                        "standard_answer": solution.get("standard_answer", "")[:500],
                        "knowledge_point": ocr_data.get("knowledge_point", ""),
                        "question_type": ocr_data.get("question_type", ""),
                        "difficulty": "中等",
                        "score": gresult.get("total", 0),
                        "total_score": solution.get("total_score", 10),
                        "error_type": dresult.get("error_type", "未分类"),
                        "error_reason": dresult.get("root_cause", ""),
                        "question_id": st.session_state.get("selected_question", {}).get("question_id", ""),  # 关联真题库
                    }
                    st.session_state.memory.add_error(error_record)

                progress.progress(100, text="完成！")
                st.rerun()

        # 显示结果
        if st.session_state.grading_result:
            gr = st.session_state.grading_result
            sa = st.session_state.standard_answer or {}
            dr = st.session_state.diagnosis_result or {}

            st.markdown("---")

            # 评分卡片
            st.subheader("📊 评分总览")
            sc1, sc2, sc3 = st.columns(3)
            total = gr.get("total", 0)
            total_max = sa.get("total_score", 10)
            sc1.metric("总分", f"{total}/{total_max}")
            sc2.metric("步骤分", f"{gr.get('step_score', 0)}/{round(total_max*0.7,1)}")
            sc3.metric("结果分", f"{gr.get('result_score', 0)}/{round(total_max*0.3,1)}")

            # 评分模式提示
            st.markdown("---")
            mode_label = "🤖 AI 在线批改" if st.session_state.get("api_key") else "📋 离线批改（基于标准答案对比）"
            st.caption(mode_label)

            # 步骤分析
            st.subheader("🔍 步骤分析")
            steps = gr.get("step_analysis", [])
            if steps:
                for step in steps:
                    judgment = step.get("judgment", "")
                    if "正确" in judgment or "✓" in judgment:
                        icon = "✅"
                    elif "部分" in judgment:
                        icon = "⚠️"
                    else:
                        icon = "❌"

                    with st.container(border=True):
                        st.markdown(f"{icon} **步骤{step.get('num', '')}**: {step.get('content', '')}")
                        st.caption(f"判断: {judgment} | 得分: {step.get('score', '')}")
                        st.caption(f"评语: {step.get('comment', '')}")
            elif gr.get("raw"):
                # LLM返回了原始文本但没有解析出步骤
                with st.container(border=True):
                    st.markdown(gr["raw"])
            else:
                # 离线模式：显示简单对比结果
                with st.container(border=True):
                    student_ans = ocr_data.get("student_answer", "")
                    std_ans = sa.get("standard_answer", "")
                    if student_ans and std_ans:
                        st.markdown(f"**你的作答**: {student_ans[:300]}")
                        st.markdown(f"**标准答案**: {std_ans[:300]}")
                    else:
                        st.info("暂无详细步骤分析。配置 API Key 可启用 AI 深度批改。")

            # 标准答案（带置信度检查）
            st.markdown("---")
            st.subheader("📖 标准答案")

            # 从题库获取匹配置信度
            selected_q = st.session_state.get("selected_question") or {}
            answer_confidence = selected_q.get("answer_confidence", 1.0)
            answer_matched_by = selected_q.get("answer_matched_by", "")

            if answer_confidence < 0.40:
                with st.container(border=True):
                    st.warning(
                        "⚠️ 答案待人工复核\n\n"
                        f"该题答案匹配置信度较低（{answer_confidence:.0%}），"
                        "暂不展示以避免错误答案。\n\n"
                        "匹配方式: {answer_matched_by}"
                    )
            elif answer_confidence < 0.70:
                with st.container(border=True):
                    st.info(
                        f"📋 自动匹配答案（置信度 {answer_confidence:.0%}）"
                    )
                    render_latex(sa.get("standard_answer", "暂无"))
                    st.caption("该答案为自动匹配，建议人工确认")
            else:
                with st.container(border=True):
                    render_latex(sa.get("standard_answer", "暂无"))

            # 错因分析
            st.markdown("---")
            st.subheader("🔬 错因分析")
            etype = dr.get("error_type", "未识别")
            etype_color = {"概念错误": "red", "推导错误": "orange", "计算错误": "orange",
                           "公式记忆错误": "violet", "审题错误": "blue", "计算粗心": "orange",
                           "选择题答案错误": "red", "未作答": "grey"}
            color = etype_color.get(etype, "grey")
            st.markdown(f"**:{color}[{etype}]** — {dr.get('root_cause', '未分析')}")

            # 知识点分析
            if kp_list:
                profile = st.session_state.memory.get_profile()
                chapter_acc = profile.get("chapter_accuracy", {})
                st.caption("📊 相关知识点掌握度:")
                for kp in kp_list[:3]:
                    acc = chapter_acc.get(kp, 0.0)
                    acc_pct = int(acc * 100)
                    bar = "█" * (acc_pct // 10) + "░" * (10 - acc_pct // 10)
                    st.caption(f"  {bar} {kp}: {acc_pct}%")

            is_repeat = dr.get("is_repeat", False)
            repeat_count = dr.get("repeat_count", 0)
            if is_repeat:
                st.error(f"⚠️ 该知识点已连续出错 {repeat_count} 次，需要专项复习！")

            # 推荐同类题目
            if kp_list and dr.get("error_type", "") not in ("无明显错误", ""):
                st.markdown("---")
                st.subheader("🎯 专项强化推荐")
                try:
                    recs = st.session_state.question_db.search(
                        knowledge_point=kp_list[0], limit=2
                    )
                    for rq in recs:
                        if st.button(
                            f"📝 {rq.get('question_id','')} [{rq.get('question_type','')}]",
                            key=f"rec_grading_{rq.get('question_id','')}",
                            use_container_width=True,
                        ):
                            st.session_state.selected_question = rq
                            st.session_state.ocr_result = None
                            st.session_state.grading_result = None
                            st.session_state.page = "practice"
                            st.rerun()
                except Exception:
                    st.caption("题库搜索暂不可用")

            # 学习建议
            st.markdown("---")
            st.subheader("💡 学习建议")
            recs = st.session_state.memory.get_recommendations()
            for i, rec in enumerate(recs, 1):
                st.markdown(f"{i}. {rec}")


# ==================== 真题库 ====================
elif page == "question_bank":
    st.title("📋 真题库")
    db = st.session_state.question_db

    # --- 导入种子数据按钮 ---
    stats = db.stats()

    # --- 本地文件导入提示 ---
    import os as _os
    source_dirs = [
        "storage/math1_source",
        "storage/math12_source",
        "storage/math2_latex",
    ]
    available = [d for d in source_dirs if _os.path.isdir(f"E:/math_tutor/{d}")
                 and any(f.endswith('.md') for f in _os.listdir(f"E:/math_tutor/{d}"))]

    if stats["total"] == 0:
        if available:
            st.info(
                f"📂 检测到本地真题文件: {', '.join(available)}。"
                "点击下方按钮一键导入。",
                icon="📂"
            )
            use_enhanced = st.checkbox(
                "使用增强解析引擎（自动拆分题目、匹配答案、修复LaTeX）",
                value=True, key="use_enhanced_empty",
                help="推荐开启。新引擎会从solutions/目录自动匹配解答。"
            )
            if st.button("🚀 一键导入本地真题", type="primary"):
                all_qs = []
                if use_enhanced:
                    from exam_parser import ExamParserPipeline
                    pipeline = ExamParserPipeline(db=db)
                    paper_dirs = [
                        "storage/math1_source/Kaoyan-Math1-Papers-main/papers",
                    ]
                    for d in paper_dirs:
                        full_path = f"E:/math_tutor/{d}"
                        if _os.path.isdir(full_path):
                            results = pipeline.process_directory(full_path)
                            for result in results:
                                all_qs.extend(result.questions)
                else:
                    from database import MarkdownExamParser
                    for d in available:
                        parser = MarkdownExamParser()
                        full_path = f"E:/math_tutor/{d}"
                        qs = parser.parse_directory(full_path)
                        all_qs.extend(qs)
                if all_qs:
                    importer = QuestionImporter(db)
                    report = importer.import_dict(all_qs)
                    st.success(
                        f"导入完成: 成功 {report['success']} 题, "
                        f"跳过重复 {report['skipped_duplicates']}, "
                        f"失败 {report['failed']}"
                    )
                    st.rerun()
                else:
                    st.error("未能从本地文件中解析出题目。请确认文件格式正确（Markdown格式）。")
        else:
            st.info(
                "📭 真题库为空。请下载真题源文件放到 storage/ 目录，"
                "或使用「导入」功能添加题目。",
                icon="ℹ️"
            )
            col_empty1, col_empty2 = st.columns(2)
            with col_empty1:
                if st.button("📥 载入示例数据", use_container_width=True):
                    importer = QuestionImporter(db)
                    report = importer.seed_examples()
                    st.success(f"导入 {report['success']} 题（演示数据）")
                    st.rerun()
            with col_empty2:
                st.caption(
                    "📌 获取真题:\n"
                    "下载 [Kaoyan-Math1-Papers](https://github.com/TsekaLuk/Kaoyan-Math1-Papers)\n"
                    "解压到 `E:\\math_tutor\\storage\\math1_source\\`"
                )

    if available and stats["total"] > 0:
        with st.expander(f"📂 本地真题文件 ({', '.join(available)})", expanded=False):
            use_enhanced_reexport = st.checkbox(
                "使用增强解析引擎（推荐：自动修复LaTeX、匹配解答、知识点标注）",
                value=True, key="use_enhanced_reexport",
            )
            if st.button("🔄 重新导入本地真题"):
                all_qs = []
                if use_enhanced_reexport:
                    from exam_parser import ExamParserPipeline
                    pipeline = ExamParserPipeline(db=db)
                    paper_dir = "E:/math_tutor/storage/math1_source/Kaoyan-Math1-Papers-main/papers"
                    if _os.path.isdir(paper_dir):
                        results = pipeline.process_directory(paper_dir)
                        for result in results:
                            all_qs.extend(result.questions)
                else:
                    from database import MarkdownExamParser
                    for d in available:
                        parser = MarkdownExamParser()
                        qs = parser.parse_directory(f"E:/math_tutor/{d}")
                        all_qs.extend(qs)
                if all_qs:
                    importer = QuestionImporter(db)
                    report = importer.import_dict(all_qs)
                    st.success(
                        f"导入: {report['success']} 成功, "
                        f"{report['skipped_duplicates']} 跳过(重复), "
                        f"{report['failed']} 失败"
                    )
                    st.rerun()

    # --- 搜索筛选栏 ---
    with st.container(border=True):
        st.caption("🔍 搜索筛选")
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            search_math_type = st.selectbox("数学类别", ["全部"] + MATH_TYPES, key="qb_mt")
        with fc2:
            # 宇哥八套卷显示"卷号"，真题显示"年份"
            if search_math_type == "26宇哥八套卷":
                # Get volumes from category index
                cat_idx = db._load_index().get("categories", {}).get("26宇哥八套卷", {})
                volumes = sorted(cat_idx.keys()) if cat_idx else ["第一套"]
                vol_opts = ["全部"] + volumes
                search_year = st.selectbox("卷号", vol_opts, key="qb_year")
                year_is_volume = True
            else:
                existing_years = stats.get("years_covered", [])
                year_opts = ["全部"] + [str(y) for y in sorted(existing_years, reverse=True)]
                search_year = st.selectbox("年份", year_opts, key="qb_year")
                year_is_volume = False
        with fc3:
            search_qtype = st.selectbox("题型", ["全部"] + QUESTION_TYPES, key="qb_qtype")
        with fc4:
            all_tags = db.get_all_tags()
            search_kp = st.selectbox("知识点", ["全部"] + all_tags if all_tags else ["全部"], key="qb_kp")
        with fc5:
            search_diff = st.selectbox("难度", ["全部"] + DIFFICULTY_LEVELS, key="qb_diff")

        search_kw = st.text_input("关键词搜索", placeholder="输入题目关键词...")

    # --- 执行搜索 ---
    filters = {"limit": 50}
    if search_math_type != "全部": filters["math_type"] = search_math_type
    if search_year != "全部":
        if year_is_volume:
            # For 宇哥八套卷, filter by sub-category (volume name)
            filters["volume"] = search_year
        else:
            filters["year"] = int(search_year)
    if search_qtype != "全部": filters["question_type"] = search_qtype
    if search_kp != "全部": filters["knowledge_point"] = search_kp
    if search_diff != "全部": filters["difficulty"] = search_diff
    if search_kw: filters["keyword"] = search_kw

    results = db.search(**filters)

    st.caption(f"找到 {len(results)} 道题")

    if not results:
        st.info("未找到匹配的题目。尝试调整筛选条件。")
    else:
        for q in results:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="question-card-head">
                        <span class="question-id-pill">{html.escape(q.get('question_id', '?'))}</span>
                        <span>{html.escape(q.get('question_type', '?'))}</span>
                        <span>{html.escape(str(q.get('score', '?')))} 分</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_q, col_meta = st.columns([4.6, 1.9], gap="large")
                with col_q:
                    edit_key = f"edit_mode_{q['question_id']}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    if st.session_state[edit_key]:
                        new_question_text = st.text_area(
                            "编辑 LaTeX 源码",
                            value=q.get("question", ""),
                            height=200,
                            key=f"edit_text_{q['question_id']}",
                        )
                        e1, e2 = st.columns(2)
                        with e1:
                            if st.button("💾 保存修改", key=f"save_{q['question_id']}", type="primary"):
                                db.update(q["question_id"], {"question": new_question_text})
                                st.success("已保存")
                                st.session_state[edit_key] = False
                                st.rerun()
                        with e2:
                            if st.button("↩️ 取消", key=f"cancel_{q['question_id']}"):
                                st.session_state[edit_key] = False
                                st.rerun()
                        st.caption("渲染预览")
                        render_latex(new_question_text)
                    else:
                        render_latex(q.get("question", ""))

                with col_meta:
                    render_question_meta_panel(q)

                cb1, cb2, cb3, cb4 = st.columns([1.1, 1.1, 1.1, 1.1])
                with cb1:
                    if st.button("✏️ 开始刷题", key=f"practice_{q['question_id']}", use_container_width=True):
                        st.session_state.selected_question = q
                        st.session_state.ocr_result = None
                        st.session_state.answer_view_mode = False
                        st.session_state.page = "practice"
                        st.rerun()
                with cb2:
                    if st.button("📖 查看答案", key=f"answer_{q['question_id']}", use_container_width=True):
                        st.session_state.selected_question = q
                        st.session_state.answer_view_mode = True
                        st.session_state.page = "grading"
                        st.session_state.ocr_result = {
                            "success": True,
                            "question": q.get("question", ""),
                            "student_answer": "",
                            "math_type": q.get("category", ""),
                            "question_type": q.get("question_type", ""),
                            "knowledge_point": ", ".join(q.get("knowledge_points", [])),
                            "confidence": 1.0,
                            "warnings": [],
                        }
                        st.session_state.standard_answer = {
                            "success": True,
                            "standard_answer": q.get("standard_answer", "暂无答案"),
                            "total_score": q.get("score", 10),
                            "steps": [],
                        }
                        st.session_state.grading_result = None
                        st.session_state.diagnosis_result = None
                        st.rerun()
                with cb3:
                    if st.button("✏️ 编辑LaTeX", key=f"edit_btn_{q['question_id']}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                with cb4:
                    del_key = f"del_confirm_{q['question_id']}"
                    if del_key not in st.session_state:
                        st.session_state[del_key] = False

                    if st.session_state[del_key]:
                        d1, d2 = st.columns(2)
                        with d1:
                            if st.button("确认", key=f"del_yes_{q['question_id']}", type="primary", use_container_width=True):
                                db.delete(q["question_id"])
                                st.success(f"已删除 {q['question_id']}")
                                st.session_state[del_key] = False
                                st.rerun()
                        with d2:
                            if st.button("取消", key=f"del_no_{q['question_id']}", use_container_width=True):
                                st.session_state[del_key] = False
                                st.rerun()
                    else:
                        if st.button("🗑️ 删除", key=f"del_{q['question_id']}", type="secondary", use_container_width=True):
                            st.session_state[del_key] = True
                            st.rerun()

    # --- 导入区域 ---
    st.markdown("---")
    with st.expander("📥 导入题目（管理员）", expanded=False):
        st.caption("支持格式：JSON 文件 / 文本粘贴 / 图片OCR（需Tesseract）")
        import_tab1, import_tab2, import_tab3, import_tab4, import_tab5 = st.tabs([
            "📄 上传JSON文件", "📝 文本粘贴", "🌐 在线获取", "📋 粘贴网页HTML", "✏️ 手动添加"
        ])

        with import_tab1:
            uploaded = st.file_uploader("选择 JSON 文件", type=["json"], key="import_json")
            if uploaded:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
                    f.write(uploaded.read())
                    tmp_path = f.name
                importer = QuestionImporter(db)
                report = importer.import_json(tmp_path)
                st.success(f"导入完成: 成功 {report['success']} 题, "
                           f"跳过重复 {report['skipped_duplicates']}, "
                           f"失败 {report['failed']}")
                if report["warnings"]:
                    st.warning(f"警告: {'; '.join(report['warnings'][:5])}")
                st.rerun()

        with import_tab2:
            json_text = st.text_area(
                "粘贴 JSON 格式题目数据",
                placeholder='{"questions": [{"year": 2024, "category": "数学一", ...}]}',
                height=200,
            )
            if st.button("📥 导入", disabled=not json_text):
                try:
                    data = json.loads(json_text)
                    importer = QuestionImporter(db)
                    report = importer.import_dict(data if isinstance(data, list) else [data])
                    st.success(f"导入完成: 成功 {report['success']}, 跳过 {report['skipped_duplicates']}, 失败 {report['failed']}")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"JSON 格式错误: {e}")

        with import_tab3:
            st.caption("从公开教育网站自动获取题目")
            st.warning(
                "⚠️ 爬虫仅访问公开可用的网页内容，请求间隔≥3秒。"
                "部分网站可能有反爬机制，如失败请改用「粘贴网页HTML」。",
                icon="⚠️"
            )
            scrape_url = st.text_input(
                "网页URL",
                placeholder="https://example.com/kaoyan/math/2024-1",
                key="scrape_url",
            )
            sc1, sc2 = st.columns(2)
            scrape_mt = sc1.selectbox("数学类别", MATH_TYPES, key="scrape_mt")
            scrape_year = sc2.number_input("年份", 1987, 2026, 2024, key="scrape_year")

            if st.button("🌐 开始爬取", disabled=not scrape_url.strip()):
                with st.spinner("正在获取网页内容（可能需要几秒）..."):
                    from scrapers import PublicEduScraper
                    scraper = PublicEduScraper()
                    questions = scraper.scrape_from_url(
                        scrape_url.strip(),
                        math_type=scrape_mt,
                        year=scrape_year,
                    )
                    if questions:
                        importer = QuestionImporter(db)
                        report = importer.import_dict(questions)
                        st.success(
                            f"爬取完成: 解析出 {len(questions)} 题, "
                            f"导入成功 {report['success']}, "
                            f"跳过重复 {report['skipped_duplicates']}, "
                            f"失败 {report['failed']}"
                        )
                        if report["warnings"]:
                            st.warning(f"数据质量问题: {'; '.join(report['warnings'][:5])}")
                        st.rerun()
                    else:
                        st.error(
                            "未能从该页面解析出题目。请检查URL是否正确，"
                            "或改用「粘贴网页HTML」方式手动提取。"
                        )

        with import_tab4:
            st.caption("从任意教育网站复制HTML内容，粘贴后自动解析")
            st.info(
                "📌 使用方法：在浏览器中打开目标网页 → 右键 → 查看页面源代码 → "
                "复制关键部分 → 粘贴到下方 → 选择数学类别和年份 → 点击解析",
                icon="📌"
            )
            scrape_html = st.text_area(
                "粘贴网页HTML内容",
                placeholder="<div class=\"question\">...</div>",
                height=200,
                key="scrape_html",
            )
            sc3, sc4 = st.columns(2)
            paste_mt = sc3.selectbox("数学类别", MATH_TYPES, key="paste_mt")
            paste_year = sc4.number_input("年份", 1987, 2026, 2024, key="paste_year")

            if st.button("🔍 解析HTML", disabled=not scrape_html.strip()):
                with st.spinner("正在解析HTML..."):
                    from scrapers import ManualHTMLScraper
                    manual = ManualHTMLScraper()
                    questions = manual.paste_and_parse(
                        scrape_html, math_type=paste_mt, year=paste_year
                    )
                    if questions:
                        importer = QuestionImporter(db)
                        report = importer.import_dict(questions)
                        st.success(
                            f"解析完成: 提取 {len(questions)} 题, "
                            f"导入成功 {report['success']}, "
                            f"跳过重复 {report['skipped_duplicates']}, "
                            f"失败 {report['failed']}"
                        )
                        # 显示解析预览
                        with st.expander("📋 解析结果预览", expanded=False):
                            for q in questions[:3]:
                                st.caption(
                                    f"[{q.get('question_type', '?')}] "
                                    f"{' '.join(q.get('knowledge_points', []))} "
                                    f"| {q.get('difficulty', '?')}"
                                )
                                st.markdown(q.get("question", "")[:200])
                                st.divider()
                        st.rerun()
                    else:
                        st.error(
                            "未能从HTML中提取题目。请确认：\n"
                            "1. 粘贴的内容包含题目区块\n"
                            "2. HTML结构中有题号标识（如 '1.', '（1）'）\n"
                            "3. 内容不是JavaScript动态加载的"
                        )

        with import_tab5:
            st.caption("直接输入 LaTeX 代码添加单道题目，自动规范化格式后入库。")
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                new_year = st.number_input("年份", 1987, 2026, 2024, key="new_year")
            with mc2:
                new_type = st.selectbox("题型", QUESTION_TYPES, key="new_type")
            with mc3:
                new_diff = st.selectbox("难度", DIFFICULTY_LEVELS, key="new_diff")
            with mc4:
                new_kp = st.selectbox("知识点", sum(KNOWLEDGE_POINTS.values(), []), key="new_kp")

            new_question = st.text_area(
                "题目内容（LaTeX 源码）",
                height=200,
                key="new_question_text",
                placeholder="输入题目 LaTeX 代码，如：\n已知函数 $f(x) = \\int\\limits_{0}^{x} e^{t^2} \\sin t \\,\\mathrm{d}t$，则 $f'(0) = $",
                help="使用 $...$ 包裹行内公式，$$...$$ 包裹独立公式",
            )
            new_answer = st.text_area(
                "标准答案（LaTeX 源码）",
                height=80,
                key="new_answer_text",
                placeholder="输入答案，如：\n$0$",
            )

            if new_question:
                st.caption("📐 题目渲染预览:")
                render_latex(new_question)
            if new_answer:
                st.caption("📐 答案渲染预览:")
                render_latex(new_answer)

            if st.button("💾 添加到题库", type="primary", use_container_width=True,
                         disabled=not new_question.strip()):
                # 规范化 LaTeX
                clean_q = normalize_latex_style(new_question.strip())
                clean_a = normalize_latex_style(new_answer.strip()) if new_answer.strip() else ""

                # 构建题目 dict
                new_q = {
                    "year": new_year,
                    "category": "数学一",
                    "question_type": new_type,
                    "knowledge_points": [new_kp] if new_kp != "自动识别" else [],
                    "difficulty": new_diff,
                    "score": {"选择题": 5, "填空题": 5, "解答题": 10, "证明题": 12}.get(new_type, 10),
                    "question": clean_q,
                    "standard_answer": clean_a,
                    "solution_steps": [],
                    "common_mistakes": [],
                    "tags": [],
                    "source": "manual_input",
                }

                result = db.insert(new_q)
                if result["success"]:
                    st.success(f"✅ 已添加: {result['question_id']}")
                    st.toast("题目已入库")
                    st.rerun()
                else:
                    st.error(f"添加失败: {'; '.join(result.get('warnings', ['未知错误']))}")

    # --- 数据库统计 ---
    st.markdown("---")
    st.subheader("📊 数据库统计")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("总题数", stats["total"])
    sc2.metric("涵盖年份", len(stats.get("years_covered", [])))
    sc3.metric("知识点标签", stats.get("knowledge_points_covered", 0))

    if stats.get("missing_data"):
        st.warning(f"缺失数据: {len(stats['missing_data'])} 处")
    if stats.get("pending_review"):
        st.info(f"待审核: {len(stats['pending_review'])} 题")

# ==================== 错题本 ====================
elif page == "mistakes":
    st.title("📚 错题本")

    # 筛选
    cf1, cf2, cf3 = st.columns(3)
    filter_subject = cf1.selectbox("科目", ["全部"] + SUBJECTS, key="filter_subject")
    filter_type = cf2.selectbox("错误类型", ["全部"] + ERROR_TYPES, key="filter_type")
    filter_diff = cf3.selectbox("难度", ["全部"] + DIFFICULTY_LEVELS, key="filter_diff")

    errors = st.session_state.memory.get_errors(
        subject=filter_subject if filter_subject != "全部" else None,
        error_type=filter_type if filter_type != "全部" else None,
    )

    stats = st.session_state.memory.get_error_stats()
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("错题总数", stats.get("total_errors", 0))
    sc2.metric("重复率", f"{stats.get('repeat_rate', 0):.1%}")
    sc3.metric("主要错误类型",
               max(stats.get("by_type", {}), key=stats.get("by_type", {}).get)
               if stats.get("by_type") else "暂无")

    # 按知识点错误分布
    by_chapter = stats.get("by_chapter", {})
    if by_chapter:
        top_chapter = max(by_chapter, key=by_chapter.get)
        sc4.metric("高频错误章节", top_chapter[:12] if top_chapter else "暂无")
    else:
        sc4.metric("高频错误章节", "暂无")

    if not errors:
        st.info("📭 错题本为空 — 开始刷题后，错题会自动记录到这里")
    else:
        # 错误知识点分布
        if by_chapter:
            with st.expander("📊 错误知识点分布", expanded=False):
                sorted_chapters = sorted(by_chapter.items(), key=lambda x: x[1], reverse=True)
                for chapter, count in sorted_chapters[:8]:
                    bar_len = min(30, count * 3)
                    bar = "█" * bar_len
                    st.caption(f"{bar} {chapter[:25]}: {count}次")
                st.caption("💡 建议针对高频错误章节进行专项训练")
                if st.button("🎯 开始专项训练", key="targeted_practice", use_container_width=True):
                    # 跳转到刷题页，预选该知识点
                    target_kp = sorted_chapters[0][0] if sorted_chapters else ""
                    try:
                        qs = st.session_state.question_db.search(knowledge_point=target_kp, limit=1)
                        if qs:
                            st.session_state.selected_question = qs[0]
                            st.session_state.page = "practice"
                            st.rerun()
                    except Exception:
                        st.session_state.page = "practice"
                        st.rerun()

        for i, err in enumerate(errors):
            with st.expander(
                f"[{err.get('date', '?')}] {err.get('knowledge_point', '未分类')[:30]} "
                f"— 得分 {err.get('score', '?')}/{err.get('total_score', '?')} "
                f"{'🔁 重复' if err.get('is_repeat') else ''}",
                expanded=(i == 0),
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("题目")
                    st.markdown(err.get("question", "")[:300])
                    st.caption("你的作答")
                    st.markdown(err.get("student_answer", "")[:300])
                with c2:
                    st.caption("标准答案")
                    st.markdown(err.get("standard_answer", "")[:300])
                    st.caption(f"错误类型：{err.get('error_type', '?')}")
                    st.caption(f"原因：{err.get('error_reason', '?')}")


# ==================== 学习画像 ====================
elif page == "profile":
    st.title("🎯 学习画像")

    profile = st.session_state.memory.get_profile()
    stats = st.session_state.memory.get_error_stats()

    # 阶段
    stage = profile.get("level", "强化阶段")
    stage_emoji = {"基础薄弱": "🔴", "强化阶段": "🔵", "冲刺阶段": "🟢"}
    st.markdown(f"### 当前阶段：{stage_emoji.get(stage, '')} {stage}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("各章节正确率")
        chapter_acc = profile.get("chapter_accuracy", {})
        if chapter_acc:
            for kp, acc in sorted(chapter_acc.items(), key=lambda x: x[1]):
                acc_pct = acc * 100
                bar_color = (
                    "#dc2626" if acc_pct < 40 else
                    "#d97706" if acc_pct < 60 else
                    "#2563eb" if acc_pct < 80 else
                    "#059669"
                )
                st.markdown(f"""
                <div style="margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
                        <span>{kp[:25]}</span><span style="font-weight:600;">{acc_pct:.0f}%</span>
                    </div>
                    <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
                        <div style="height:100%;width:{acc_pct}%;background:{bar_color};border-radius:4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无数据")

    with col2:
        st.subheader("薄弱知识点")
        weak = profile.get("weak_points", [])
        if weak:
            for i, w in enumerate(weak, 1):
                st.markdown(f"{i}. {w}")
        else:
            st.info("暂无数据 — 多刷题后系统会分析你的薄弱环节")

        st.subheader("错题类型分布")
        by_type = stats.get("by_type", {})
        if by_type:
            for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- {t}: {c} 次")

    # 复习建议
    st.subheader("📋 复习建议")
    recs = st.session_state.memory.get_recommendations()
    if not recs:
        recs = ["开始刷题以获取个性化建议"]
    for rec in recs:
        st.markdown(f"- {rec}")


# ==================== 系统设置 ====================
elif page == "settings":
    st.title("⚙️ 系统设置")

    with st.container(border=True):
        st.subheader("LLM API 配置")
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get("api_key", LLM_API_KEY),
            type="password",
            help="支持 DeepSeek / OpenAI 兼容接口",
        )
        base_url = st.text_input(
            "API Base URL",
            value=st.session_state.get("base_url", LLM_BASE_URL),
        )
        model = st.text_input(
            "模型名称",
            value=st.session_state.get("model", LLM_MODEL),
        )

        if st.button("💾 保存配置", type="primary"):
            st.session_state.api_key = api_key
            st.session_state.base_url = base_url
            st.session_state.model = model
            if api_key:
                st.session_state.llm_client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                st.session_state.llm_client = None
            # 仅持久化非敏感配置。API Key 请使用 LLM_API_KEY 环境变量持久化。
            save_settings({
                "base_url": base_url,
                "model": model,
            })
            st.success("✅ 配置已保存；API Key 仅保存在当前会话或环境变量中")
            st.toast("API 配置已更新")

    with st.container(border=True):
        st.subheader("数据管理")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空错题本", type="secondary"):
                st.session_state.memory.clear_all()
                st.warning("错题本和画像已重置")
                st.rerun()
        with col2:
            st.caption(f"错题数: {st.session_state.memory.get_error_stats().get('total_errors', 0)}")
            st.caption(f"数据位置: `E:\\math_tutor\\storage\\`")
