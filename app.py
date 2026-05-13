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
# 硬编码兜底
if os.path.isdir(r"E:\math_tutor") and r"E:\math_tutor" not in sys.path:
    sys.path.insert(0, r"E:\math_tutor")

import html
import json
import re
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import time
from openai import OpenAI
import importlib.util as _ilu_llm
_llm_spec = _ilu_llm.spec_from_file_location("llm_client", os.path.join(_ROOT, "llm_client.py"))
llm_client_mod = _ilu_llm.module_from_spec(_llm_spec)
_llm_spec.loader.exec_module(llm_client_mod)
create_client = llm_client_mod.create_client

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
_LU = None
try:
    from latex_utils import (
        normalize_latex_style, safe_latex, clean_latex,
        split_latex_text, render_ast,
        render_structured, render_structured_safe, pipeline_canonical,
        from_legacy_text, from_legacy_json, validate_structured,
        as_canonical, graph_to_structured,
        extract_choices, render_choices, render_choice_question,
    )
except (ModuleNotFoundError, KeyError, ImportError):
    # 无条件确保项目根目录在 sys.path 中
    try:
        _app_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        _app_dir = os.path.abspath(os.getcwd())
    _ROOTS = [_app_dir, os.getcwd(), r"E:\math_tutor", r"e:\math_tutor"]
    for _r in _ROOTS:
        if _r and os.path.isdir(_r) and _r not in sys.path:
            sys.path.insert(0, _r)
    # 通过 importlib 直接从文件路径加载
    import importlib.util as _ilu
    _lu_paths = [
        os.path.join(_app_dir, "latex_utils.py"),
        os.path.join(os.getcwd(), "latex_utils.py"),
        r"E:\math_tutor\latex_utils.py",
        r"e:\math_tutor\latex_utils.py",
    ]
    _lu_loaded = False
    for _lp in _lu_paths:
        if os.path.exists(_lp):
            _lu_spec = _ilu.spec_from_file_location("l" \
            "" \
            "" \
            "" \
            "atex_utils", _lp)
            _LU = _ilu.module_from_spec(_lu_spec)
            _lu_spec.loader.exec_module(_LU)
            _lu_loaded = True
            break
    if not _lu_loaded:
        raise
    normalize_latex_style = _LU.normalize_latex_style
    safe_latex = _LU.safe_latex
    clean_latex = _LU.clean_latex
    split_latex_text = _LU.split_latex_text
    render_ast = _LU.render_ast
    render_structured = _LU.render_structured
    render_structured_safe = _LU.render_structured_safe
    pipeline_canonical = _LU.pipeline_canonical
    from_legacy_text = _LU.from_legacy_text
    from_legacy_json = _LU.from_legacy_json
    validate_structured = _LU.validate_structured
    as_canonical = _LU.as_canonical
    graph_to_structured = _LU.graph_to_structured
    extract_choices = _LU.extract_choices
    render_choices = _LU.render_choices
    render_choice_question = _LU.render_choice_question

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

    /* ── Question Card Visual Hierarchy ── */
    /* ── Question Card: 5-layer visual hierarchy ── */
    .qcard {
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 24px;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .qcard:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
    }
    /* Layer 1: Year + Subject — large, primary */
    .qcard-year {
        padding: 0.8rem 1.2rem 0.1rem 1.2rem;
        font-size: 1.15rem;
        font-weight: 750;
        color: #0f172a;
        letter-spacing: 0.01em;
    }
    /* Layer 2: Type + Score + Difficulty — small, muted */
    .qcard-subtitle {
        padding: 0.15rem 1.2rem 0.7rem 1.2rem;
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.15rem;
        border-bottom: 1px solid #f1f5f9;
    }
    .qcard-dot {
        color: #cbd5e1;
        margin: 0 0.3rem;
    }
    .qcard-diff-stars {
        color: #f59e0b;
        letter-spacing: 1px;
    }
    /* Layer 3: Question body */
    .qcard-body {
        padding: 1rem 1.2rem;
    }
    /* Options grid */
    .qcard-options {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px 28px;
        margin-top: 14px;
    }
    .qcard-option {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        min-width: 0;
        padding: 0.5rem 0.7rem;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background: #fafbfc;
        cursor: default;
    }
    .qcard-option:hover { border-color: #94a3b8; }
    .choice-label {
        display: inline-block;
        font-weight: 700;
        color: #6d28d9;
        font-size: 0.88rem;
        margin-bottom: 2px;
    }
    .option-label {
        font-weight: 700;
        color: #6d28d9;
        flex-shrink: 0;
        min-width: 28px;
        font-size: 0.88rem;
    }
    .option-content {
        overflow-x: auto;
        line-height: 1.7;
        font-size: 0.88rem;
        color: #334155;
        min-width: 0;
    }
    @media (max-width: 768px) {
        .qcard-options {
            grid-template-columns: 1fr;
        }
    }
    /* Layer 4: Knowledge tags */
    .qcard-tags {
        padding: 0.5rem 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        flex-wrap: wrap;
    }
    .qcard-tag {
        display: inline-flex;
        align-items: center;
        min-height: 1.4rem;
        border-radius: 999px;
        padding: 0.08rem 0.5rem;
        font-size: 0.72rem;
        font-weight: 600;
        border: 1px solid #c7d2fe;
        background: #eef2ff;
        color: #4338ca;
    }
    /* Layer 5: Action bar */
    .qcard-actions-bar {
        padding: 0.55rem 1.2rem;
        border-top: 1px solid #f1f5f9;
        background: #fafbfc;
        display: flex;
        gap: 0.45rem;
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
import importlib.util as _ilu
_cred_spec = _ilu.spec_from_file_location("credential_store", os.path.join(_ROOT, "credential_store.py"))
credential_store = _ilu.module_from_spec(_cred_spec)
_cred_spec.loader.exec_module(credential_store)

def load_settings() -> dict:
    """加载持久化的设置"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
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
if "editing_question" not in st.session_state:
    st.session_state.editing_question = None
if "user_loop" not in st.session_state:
    st.session_state.user_loop = UserLoop(
        st.session_state.question_db,
        st.session_state.memory,
    )
# 加载持久化的非敏感设置；API Key 从 credential_store 读取（15天自动过期）
_saved = load_settings()
_cred_profile = credential_store.get_active_profile()
if "base_url" not in st.session_state:
    st.session_state.base_url = (
        _cred_profile.get("base_url") if _cred_profile
        else _saved.get("base_url", LLM_BASE_URL)
    )
if "model" not in st.session_state:
    st.session_state.model = (
        _cred_profile.get("model") if _cred_profile
        else _saved.get("model", LLM_MODEL)
    )
if "api_key" not in st.session_state:
    st.session_state.api_key = (
        _cred_profile.get("api_key") if _cred_profile
        else LLM_API_KEY
    )
if "protocol" not in st.session_state:
    st.session_state.protocol = (
        _cred_profile.get("protocol", "openai") if _cred_profile
        else "openai"
    )
if st.session_state.get("api_key") and st.session_state.llm_client is None:
    try:
        st.session_state.llm_client = create_client(
            api_key=st.session_state.api_key,
            base_url=st.session_state.base_url,
            protocol=st.session_state.get("protocol", "openai"),
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
        st.session_state.llm_client = create_client(
            api_key=st.session_state.api_key,
            base_url=st.session_state.get("base_url", LLM_BASE_URL),
            protocol=st.session_state.get("protocol", "openai"),
        )
    return st.session_state.llm_client


def _render_choice_fill_ui(gr, sa, dr, ocr_data, selected_q):
    """选择题/填空题：短、准、快的选项分析 UI。"""
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
    is_choice = (q_type == "选择题")
    std_ans = sa.get("standard_answer", "")
    total_max = sa.get("total_score", selected_q.get("score", 4))
    total = gr.get("total", 0)
    is_correct = total >= total_max

    # ── 非法输入检测 ──
    if gr.get("illegal_input"):
        st.error(f"## ⚠️ {gr.get('comment', '非法输入')}")
        st.warning("本题为**单选题**，只能选择一个答案。请重新提交单个选项字母。")
        return  # 不继续显示后续批改内容

    # ── 结果对比卡 ──
    student_ans = ocr_data.get("student_answer", "")
    correct_opt = selected_q.get("correct_option", "")

    cols = st.columns(2)
    with cols[0]:
        with st.container(border=True):
            st.markdown(f"### {'✅' if is_correct else '❌'} 你的答案")
            st.markdown(f"## {student_ans[:20] or '(未作答)'}")
    with cols[1]:
        with st.container(border=True):
            st.markdown(f"### ✅ 正确答案")
            if is_choice and correct_opt:
                st.markdown(f"## {correct_opt}")
            elif std_ans:
                render_latex(std_ans[:100])

    # 总分
    st.caption(f"得分: {total}/{total_max}" + (" ✓ 正确" if is_correct else ""))

    # ── 错误原因（一句话） ──
    if not is_correct:
        st.error(f"**错误原因**: {dr.get('root_cause', '答案不匹配')}")

    # ── 选项分析（选择题专属） ──
    if is_choice and not is_correct:
        _render_option_analysis(selected_q, correct_opt, student_ans)

    # ── 秒杀技巧（折叠） ──
    solution_steps = sa.get("steps", [])
    if solution_steps:
        with st.expander("💡 解题思路与技巧", expanded=is_correct):
            for i, step in enumerate(solution_steps, 1):
                content = step["content"] if isinstance(step, dict) else str(step)
                with st.container(border=True):
                    st.markdown(f"**Step {i}**")
                    render_latex(content)

    # ── 完整证明（深度折叠） ──
    full_answer = sa.get("standard_answer", "")
    if full_answer and len(full_answer) > 100:
        with st.expander("📖 完整解题过程（可展开）", expanded=False):
            render_latex(full_answer)

    # ── 知识回顾（与当前题目严格相关） ──
    kp_list = selected_q.get("knowledge_points", [])
    sa_kp = sa.get("knowledge_points", [])
    display_kp = sa_kp or kp_list
    sa_cm = sa.get("common_mistakes", [])

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if display_kp:
            st.markdown("**📚 考查知识点**")
            for kp in display_kp[:3]:
                st.markdown(f"- {kp}")
    with col_b:
        if sa_cm:
            st.markdown("**⚠️ 易混淆点**")
            for cm in sa_cm[:3]:
                st.markdown(f"- {cm}")

    # ── 错因与学习建议（仅当错误且与当前题强相关） ──
    if not is_correct and display_kp:
        _render_contextual_recommendations(selected_q, gr, dr, display_kp)


def _render_option_analysis(selected_q, correct_opt, student_ans):
    """选择题选项分析：逐个解释为什么对/错。"""
    options = selected_q.get("options", {})
    if not options:
        return
    st.markdown("**🔍 选项分析**")
    for letter in sorted(options.keys()):
        opt_text = options[letter]
        is_correct_opt = (letter.upper() == correct_opt.upper())
        is_student_choice = (letter.upper() == student_ans.strip().upper())

        icon = "✅" if is_correct_opt else "❌"
        ctx = "你的选择" if is_student_choice else ("正确答案" if is_correct_opt else "")

        with st.container(border=True):
            st.markdown(f"{icon} **{letter}** {ctx}")
            render_latex(opt_text[:200])


def _render_contextual_recommendations(selected_q, gr, dr, display_kp):
    """只推荐与当前题目强相关的学习内容。"""
    st.markdown("**🎯 针对性建议**")
    # 只推荐当前题目涉及的知识点
    for kp in display_kp[:2]:
        try:
            recs = st.session_state.question_db.search(knowledge_point=kp, limit=1)
            for rq in recs:
                col_btn, col_info = st.columns([3, 2])
                with col_btn:
                    st.button(
                        f"📝 练习：{rq.get('question_id','')} [{rq.get('question_type','')}]",
                        key=f"ctx_rec_{rq.get('question_id','')}",
                    )
        except Exception:
            pass
    # 一句话建议
    error_type = dr.get("error_type", "")
    kp_str = display_kp[0] if display_kp else ""
    tips = {
        "概念错误": f"建议重新理解「{kp_str}」的核心定义，区分易混淆概念。",
        "审题错误": f"建议仔细审题，关注「{kp_str}」中的关键词和条件。",
        "选择题答案错误": f"建议练习「{kp_str}」相关的选择题，掌握排除法和快速判断技巧。",
    }
    tip = tips.get(error_type, f"建议针对「{kp_str}」进行专项练习。")
    st.caption(tip)


def _render_essay_grading_ui(gr, sa, dr, ocr_data, selected_q):
    """解答题/证明题：三栏推导分析 UI。"""
    total = gr.get("total", 0)
    total_max = sa.get("total_score", 10)
    engine = gr.get("engine", gr.get("_engine", ""))
    conf = _compute_confidence(gr, None)
    student_ans = ocr_data.get("student_answer", "")

    # ═══ 顶部：评分面板 ═══
    _render_score_panel(gr, sa, total, total_max, engine, conf)
    _render_method_info_bar(gr)

    # ═══ 四层评分明细 ═══
    layers = gr.get("layers", {})
    if layers:
        l1, l2, l3, l4 = (layers.get(k, {}) for k in ("fast", "structural", "semantic", "teaching"))
        col_l1, col_l2, col_l3, col_l4 = st.columns(4)
        with col_l1:
            st.metric("⚡ 答案验证", f"{l1.get('score', 0):.0f}/{l1.get('max_score', total_max):.0f}",
                      help=l1.get("detail", ""))
        with col_l2:
            st.metric("📐 步骤结构", f"{l2.get('score', 0):.0f}/{l2.get('max_score', total_max):.0f}",
                      help=f"{l2.get('detail', '')} | 匹配: {l2.get('matched_method', '-')}")
        with col_l3:
            st.metric("🔬 数学合法性", f"{l3.get('score', 0):.0f}/{l3.get('max_score', total_max):.0f}",
                      help=f"{l3.get('detail', '')} | 自洽性: {l3.get('validity', 0):.0%}")
        with col_l4:
            st.caption(f"💡 {l4.get('teaching_tip', '')}")

    # ═══ 三栏主体 ═══
    # 加载 canonical trace
    _canonical_display = None
    try:
        if selected_q.get("canonical_solutions"):
            from solution_graph import CanonicalSolutionTrace
            _canonical_display = CanonicalSolutionTrace.from_question_json(selected_q)
    except Exception:
        pass

    st.markdown("---")

    if _canonical_display and _canonical_display.methods:
        # 多方法 Tab
        methods = _canonical_display.methods
        method_names = [m.method_name for m in methods]
        if len(method_names) > 1:
            tabs = st.tabs([f"{i+1}. {n}" for i, n in enumerate(method_names)])
            for idx, (tab, method) in enumerate(zip(tabs, methods)):
                with tab:
                    _render_three_column_view(gr, method, student_ans)
        else:
            _render_three_column_view(gr, methods[0], student_ans)
    else:
        # 无 canonical trace：简单展示
        _render_fallback_view(gr, sa, student_ans)

    # ═══ 裁决 → 诊断 → 教学（三层分离）═══
    _render_diagnosis_bottom(gr, sa, dr, ocr_data, selected_q)


def _render_score_panel(gr, sa, total, total_max, engine, conf):
    """顶部评分面板：分数 + 进度条 + 置信度。"""
    pct = total / max(total_max, 1)
    bar = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
    color = "#22c55e" if pct >= 0.9 else "#eab308" if pct >= 0.7 else "#ef4444"

    st.markdown(f"""
    <div style="border: 1px solid #dbe4ef; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <span style="font-size: 1.5em; font-weight: bold; color:{color};">{total}/{total_max}</span>
          <span style="margin-left: 12px; color: #64748b;">
            过程分 {gr.get('step_score', 0)} · 正确分 {gr.get('result_score', 0)}
          </span>
        </div>
        <div style="color: #64748b; font-size: 0.85em;">
          置信度 {conf:.0%} · {gr.get('engine', gr.get('_engine', '?'))}
        </div>
      </div>
      <div style="font-family: monospace; margin-top: 4px; color: {color};">{bar}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_method_info_bar(gr):
    """方法识别信息条。"""
    method_matched = gr.get("method_matched", "")
    method_family = gr.get("method_family", "")
    tier = gr.get("tier", "")
    candidate_submitted = gr.get("candidate_submitted", False)
    if not method_matched and not method_family and not candidate_submitted:
        return
    parts = []
    if method_matched:
        parts.append(f"🎯 匹配解法: **{method_matched}**")
    if method_family:
        tier_map = {"t1_fast": "T1·快速 ⚡", "t1_fast_path": "T1·快速通道 ⚡",
                     "t1_answer_check": "T1·答案检查",
                     "t3_graph_match": "T3·定向图匹配", "t4_semantic_fallback": "T4·语义判断"}
        parts.append(f"📂 {method_family} | {tier_map.get(tier, tier)}")
    if candidate_submitted:
        parts.append("📋 候选方法已提交审核")
    st.caption(" · ".join(parts))


def _render_three_column_view(gr, method, student_ans):
    """三栏布局：标准步骤 | 学生作答 | AI 分析。"""
    from solution_renderer import render_step, _op_type_cn

    nodes = method.graph.nodes
    proc_nodes = [n for n in nodes if n.type != "final_answer"]
    final_node = next((n for n in nodes if n.type == "final_answer"), None)
    step_analysis = gr.get("step_analysis", [])

    # ── 三栏标题 ──
    col_std, col_stu, col_ai = st.columns([3, 3, 2])
    with col_std:
        st.markdown("**📐 规范推导**")
    with col_stu:
        st.markdown("**✍️ 你的推导**")
    with col_ai:
        st.markdown("**🤖 AI 分析**")

    # ── 逐步骤渲染 ──
    for i, node in enumerate(proc_nodes):
        analysis = step_analysis[i] if i < len(step_analysis) else {}
        judgment = analysis.get("judgment", "")
        comment = analysis.get("comment", "")

        # 判断图标
        if "正确" in judgment:
            icon, bg = "✅", "#dcfce7"
        elif "部分" in judgment:
            icon, bg = "⚠️", "#fef9c3"
        elif "缺失" in judgment:
            icon, bg = "❌", "#fecaca"
        else:
            icon, bg = "⬜", ""

        col_std, col_stu, col_ai = st.columns([3, 3, 2])
        with col_std:
            with st.container(border=True):
                op_cn = _OP_TYPE_MAP.get(node.operation or node.type, "计算")
                st.markdown(f"**Step {i+1}** · {op_cn}")
                if node.goal:
                    st.caption(f"🎯 {node.goal}")
                if node.strategy:
                    st.caption(f"📋 {node.strategy}")
                label = node.label or ""
                if label:
                    st.caption(label)
                if node.input_state:
                    st.caption(f"入: ${node.input_state}$")
                if node.output:
                    render_latex(node.output)
                if node.weight:
                    st.caption(f"_{node.weight:.0f}分_")

        with col_stu:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                if analysis.get("input_state"):
                    st.caption(f"状态: ${analysis['input_state']}$")
                st.markdown(comment or "—")

        with col_ai:
            with st.container(border=True):
                st.markdown(f"**{judgment or '未分析'}**")
                if analysis.get("score"):
                    st.caption(f"得分: {analysis['score']}")
                explanation = _gen_step_explanation(node)
                if explanation:
                    st.caption(f"💡 {explanation}")

        # 错误传播：标注影响
        if "❌" in icon and i < len(proc_nodes) - 1:
            col_v = st.columns([3, 3, 2])[2]
            with col_v:
                st.caption("⚠️ 影响后续步骤")

    # ── 最终答案对照 ──
    st.markdown("---")
    final_text = final_node.output if final_node and final_node.output else method.final_answer
    col_fs, col_fd = st.columns(2)
    with col_fs:
        st.caption("**🏁 标准答案**")
        render_latex(final_text or method.final_answer)
    with col_fd:
        st.caption("**🏁 你的答案**")
        sa_answer = sa.get("standard_answer", "")
        if sa_answer:
            render_latex(sa_answer[:200])

    # 错误传播分析
    graph_result = gr.get("_graph_result", {})
    root_errors = graph_result.get("root_errors", [])
    cascaded = graph_result.get("cascaded_errors", [])
    if root_errors or cascaded:
        with st.expander("🔗 错误传播分析", expanded=(len(root_errors) > 0)):
            if root_errors:
                st.caption(f"🔴 根因错误步骤: {', '.join(root_errors)}")
            if cascaded:
                st.caption(f"🟡 级联影响（不重复扣分）: {', '.join(cascaded)}")
                st.caption("这些步骤因上游错误导致，仅扣少量分。")

    # DAG 依赖关系提示
    if method.graph.edges and len(method.graph.edges) > 0:
        with st.expander("🔗 推导依赖图", expanded=False):
            edges_display = [f"{e.source} → {e.target}" for e in method.graph.edges[:10]]
            st.caption(" → ".join(edges_display))


def _render_fallback_view(gr, sa, student_ans):
    """无 canonical trace 时的简单展示。"""
    solution_steps = sa.get("steps", [])
    step_analysis = gr.get("step_analysis", [])
    cols = st.columns(2)
    with cols[0]:
        st.subheader("💡 解题思路")
        if solution_steps:
            for i, step in enumerate(solution_steps, 1):
                content = step["content"] if isinstance(step, dict) else str(step)
                with st.container(border=True):
                    st.markdown(f"**步骤 {i}**")
                    render_latex(content)
        else:
            std_ans = sa.get("standard_answer", "")
            if std_ans:
                render_latex(std_ans)
            else:
                st.info("暂无标准答案")
    with cols[1]:
        st.subheader("🔍 批改分析")
        if step_analysis:
            for step in step_analysis:
                judgment = step.get("judgment", "")
                icon = "✅" if "正确" in judgment else ("⚠️" if "部分" in judgment else "❌")
                st.caption(f"{icon} {step.get('num', '')}. {step.get('content', '')}: {judgment}")
        else:
            st.info("暂无步骤分析")


def _render_diagnosis_bottom(gr, sa, dr, ocr_data, selected_q):
    """底部面板：拆分为 裁决(Judge) → 诊断(Diagnose) → 教学(Tutor) 三层。"""
    sa_kp = sa.get("knowledge_points", [])
    sa_cm = sa.get("common_mistakes", [])
    kp_list = selected_q.get("knowledge_points", [])
    display_kp = sa_kp or kp_list

    # ── 第一层: 裁决 (Judge) — 只看对/错/部分分 + 错因标签 ──
    st.markdown("---")
    st.subheader("⚖️ 裁决")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        etype = dr.get("error_type", "无错误")
        etype_colors = {"概念错误": "red", "推导错误": "orange", "运算错误": "orange",
                        "计算粗心": "orange", "审题错误": "blue", "知识点遗忘": "violet",
                        "无错误": "green"}
        color = etype_colors.get(etype, "grey")
        label = "✓ 无错误" if etype == "无错误" else f"**:{color}[{etype}]**"
        st.markdown(f"判定: {label}")
        if dr.get("root_cause"):
            st.caption(f"原因: {dr.get('root_cause', '')}")
        if dr.get("is_repeat", False):
            st.error(f"⚠️ 该知识点已连续出错 {dr.get('repeat_count', 0)} 次")
    with col_j2:
        if display_kp:
            st.caption("涉及知识点:")
            for kp in display_kp[:3]:
                st.markdown(f"- {kp}")
        if sa_cm:
            st.caption("常见易错:")
            for cm in sa_cm[:2]:
                st.markdown(f"- {cm}")

    # ── 第二层: 诊断 (Diagnoser) — 分析为什么错 ──
    if dr.get("error_type", "") not in ("无错误", "无明显错误", "", None):
        st.markdown("---")
        st.subheader("🔬 诊断")
        etype = dr.get("error_type", "")
        if etype == "概念错误":
            st.info("**概念错误** — 对核心定义或定理理解有偏差。建议回到教材确认基本概念。")
        elif etype == "推导错误":
            st.info("**推导错误** — 推理链存在断裂或跳跃。建议补充中间步骤，检查每一步的依据。")
        elif etype == "运算错误":
            st.info("**运算错误** — 数值或代数运算出错。建议验算关键步骤的计算结果。")
        elif etype == "计算粗心":
            st.info("**计算粗心** — 非理解性问题。建议养成验算习惯，注意符号和系数。")
        elif etype == "审题错误":
            st.info("**审题错误** — 未准确理解题目条件。建议仔细阅读题目中的每一个条件。")

    # ── 第三层: 教学 (Tutor) — 如何学/练 ──
    st.markdown("---")
    st.subheader("📖 学习指导")

    # 知识掌握度
    if display_kp:
        profile = st.session_state.memory.get_profile()
        chapter_acc = profile.get("chapter_accuracy", {})
        accs = [(kp, chapter_acc.get(kp, 0)) for kp in display_kp[:3]]
        if accs:
            bars = " | ".join(
                f"{kp[:10]}: {'█' * int(a * 8)}{'░' * max(0, 8 - int(a * 8))} {int(a * 100)}%"
                for kp, a in accs
            )
            st.caption(f"📊 {bars}")

    # 专项练习推荐（仅与本题相关）
    if display_kp and dr.get("error_type", "") not in ("无错误", "无明显错误", "", None):
        try:
            recs = st.session_state.question_db.search(knowledge_point=display_kp[0], limit=2)
            if recs:
                st.caption("🎯 专项练习:")
                cols = st.columns(2)
                for i, rq in enumerate(recs):
                    with cols[i]:
                        st.button(
                            f"📝 {rq.get('question_id','')}",
                            key=f"tutor_rec_{rq.get('question_id','')}",
                            use_container_width=True,
                        )
        except Exception:
            pass

    # 学习路线建议
    profile = st.session_state.memory.get_profile()
    weak_points = profile.get("weak_points", [])
    if weak_points and dr.get("error_type", "") not in ("无错误", "无明显错误", "", None):
        st.caption(f"📋 建议优先攻克: {', '.join(weak_points[:3])}")


def _render_canonical_method(method, idx: int):
    """结构化步骤卡片渲染 — Step Timeline + 卡片布局。"""
    nodes = method.graph.nodes
    proc_nodes = [n for n in nodes if n.type != "final_answer"]
    final_node = next((n for n in nodes if n.type == "final_answer"), None)

    # ── 🏷 解法总览栏 ──
    col_ov, col_kp = st.columns([3, 2])
    with col_ov:
        st.markdown(f"**{method.method_name}** — {len(proc_nodes)} 步 · {method.graph.total_score}分")
    with col_kp:
        if method.knowledge_points:
            st.caption(" · ".join(method.knowledge_points[:4]))

    # ── 🔵 步骤时间线 ──
    for i, node in enumerate(proc_nodes):
        op_cn = _OP_TYPE_MAP.get(node.operation or node.type, "计算")
        score = node.weight
        is_critical = score >= 2.0
        has_details = bool(node.input_state or node.output)

        # 时间线连接线
        col_dot, col_card = st.columns([0.05, 0.95])
        with col_dot:
            if is_critical:
                st.markdown(f"🔴")
            else:
                st.markdown("🔵")
        with col_card:
            # 卡片标题行
            title = f"Step {i+1} · {node.label or op_cn}"
            if is_critical:
                title += " `关键`"

            with st.expander(title, expanded=(i == 0)):
                # 推理语义层
                st.caption(f"📐 操作: **{op_cn}** `{node.operation or node.type}` | {score:.0f}分")
                if node.goal:
                    st.caption(f"🎯 目标: {node.goal}")
                if node.strategy:
                    st.caption(f"📋 策略: {node.strategy}")
                if node.reasoning:
                    st.info(node.reasoning)

                # 推导块：输入 → 操作 → 输出
                inp = node.input_state or ""
                out = node.output or ""
                if inp or out:
                    col_i, col_a, col_o = st.columns([4, 1, 4])
                    with col_i:
                        if inp:
                            st.caption("📥 输入")
                            render_latex(inp)
                    with col_a:
                        if inp and out:
                            st.caption("→")
                    with col_o:
                        if out:
                            st.caption("📤 输出")
                            render_latex(out)

                # 教学解释
                explanation = _gen_step_explanation(node)
                if explanation:
                    st.info(explanation)

        # 垂直分隔线（非最后一步）
        if i < len(proc_nodes) - 1:
            col_v, _ = st.columns([0.05, 0.95])
            with col_v:
                st.markdown("│")

    # ── 🏁 最终答案卡片 ──
    st.markdown("---")
    final_text = final_node.output if final_node and final_node.output else method.final_answer
    if final_text:
        with st.container(border=True):
            col_fa, col_box = st.columns([1, 4])
            with col_fa:
                st.markdown("### 🏁")
            with col_box:
                st.markdown("**最终答案**")
                render_latex(final_text)

    # ── ⚠ 常见错误卡片 ──
    if method.common_mistakes:
        with st.expander("⚠️ 常见错误提醒", expanded=False):
            for cm in method.common_mistakes[:5]:
                st.markdown(f"- {cm}")


def _render_student_vs_standard(grading_result: dict, canonical_method):
    """学生 vs 标准步骤对照表。"""
    if not grading_result or not canonical_method:
        return

    step_analysis = grading_result.get("step_analysis", [])
    proc_nodes = [n for n in canonical_method.graph.nodes if n.type != "final_answer"]

    if not step_analysis or not proc_nodes:
        return

    st.markdown("---")
    st.subheader("📋 步骤对照")

    # 表头
    col_s, col_j, col_c = st.columns([3, 1, 3])
    with col_s:
        st.caption("**标准步骤**")
    with col_j:
        st.caption("**评判**")
    with col_c:
        st.caption("**你的作答**")

    for i, node in enumerate(proc_nodes):
        analysis = step_analysis[i] if i < len(step_analysis) else {}
        judgment = analysis.get("judgment", "")
        comment = analysis.get("comment", "")
        icon = "✅" if "正确" in judgment else ("⚠️" if "部分" in judgment else "❌")

        col_s, col_j, col_c = st.columns([3, 1, 3])
        with col_s:
            st.markdown(f"**{i+1}.** {node.label or (node.operation or node.type)}")
            if node.output:
                render_latex(node.output)

        with col_j:
            st.markdown(f"### {icon}")
            st.caption(judgment)

        with col_c:
            st.markdown(comment or "—")
        st.markdown("---")


_OP_TYPE_MAP = {
    "differentiate": "求导", "integrate": "积分", "compute_limit": "求极限",
    "partial_diff": "偏导数", "expand": "展开", "factor": "因式分解",
    "simplify": "化简", "substitute": "代换/换元", "collect": "合并同类项",
    "cancel": "约分", "solve_equation": "解方程", "solve_system": "解方程组",
    "matrix_op": "矩阵运算", "row_reduce": "行变换", "eigen_solve": "特征值/特征向量",
    "determinant": "行列式计算", "orthogonalize": "正交化", "quadratic_form": "二次型标准化",
    "expand_series": "级数展开", "convergence_test": "收敛性判别",
    "probability_calc": "概率计算", "expectation": "期望/方差",
    "mle_derive": "极大似然推导", "apply_theorem": "应用定理",
    "classify": "分类讨论", "final_answer": "最终答案", "compute": "计算",
}


def _gen_step_explanation(node) -> str:
    """为步骤生成简短教学解释。"""
    op = node.operation or node.type
    inp = node.input_state or ""
    out = node.output or ""
    if op == "substitute" and inp:
        return f"通过代换简化表达式结构，使后续运算更简便"
    if op == "factor" and inp:
        return "将表达式分解为乘积形式，便于讨论根与符号"
    if op == "simplify":
        return "合并同类项、约分，化为最简形式"
    if op == "integrate":
        return f"对表达式进行积分，寻找原函数"
    if op == "differentiate":
        return "求导数，分析函数增减性与极值"
    if op == "compute_limit":
        return "应用极限法则或等价无穷小求极限"
    if op == "eigen_solve":
        return "构造特征方程，求解特征值与特征向量"
    if op == "apply_theorem":
        return "应用相关定理，将条件转化为可计算形式"
    if op == "classify":
        return "按参数取值分类讨论，确保所有情形被覆盖"
    if out:
        return f"执行{_OP_TYPE_MAP.get(op, op)}运算，得到结果"
    return ""


def render_latex(text: str) -> None:
    """
    AST-first 数学渲染入口。

    管道: split_latex_text → render_ast
      - text 片段 → st.markdown()
      - inline_math → st.markdown("$...$")
      - display_math → st.latex()

    所有带数学内容的地方必须走这里。
    """
    if not text:
        return
    try:
        segments = split_latex_text(text)
        render_ast(segments)
    except Exception:
        try:
            st.text(f"[数学渲染失败，显示原文]\n{text[:500]}")
        except Exception:
            pass


def render_latex_caption(text: str) -> None:
    """小字说明：使用 AST 渲染但保持紧凑"""
    if text:
        try:
            segments = split_latex_text(text)
            render_ast(segments)
        except Exception:
            pass


def md_safe(text: str) -> None:
    """
    st.markdown() 的安全替代。

    含数学内容 → AST-first 渲染（split → render_ast）
    纯文本 → 直接 st.markdown()
    """
    if not text:
        return
    has_math = bool(re.search(r'[\$\\\^_{}]|\\[a-zA-Z]+', text))
    try:
        if has_math:
            segments = split_latex_text(text)
            render_ast(segments)
        else:
            st.markdown(text)
    except Exception:
        try:
            st.text(text[:500])
        except Exception:
            pass


def render_solution(solution, source: str = "canonical") -> None:
    """
    四层解耦渲染入口 — 最终推荐。

    接受任意格式输入，自动归一化为 CanonicalTrace 后安全渲染。

    四层管道:
      Layer 1: as_canonical(source) → StructuredSolution
      Layer 2: render_structured_safe() → 渲染决策
      Layer 3: safe_latex() → token 安全
      Layer 4: st.latex() / st.markdown() → 原生渲染

    支持的输入类型:
      - dict:  LLM 结构化 JSON
      - str:   旧混合文本（自动转换）
      - CanonicalSolutionTrace / SolutionGraph（DAG 自动转换）
    """
    if not solution:
        return
    try:
        pipeline_canonical(solution)
    except Exception:
        try:
            st.text(f"[渲染失败]\n{str(solution)[:500]}")
        except Exception:
            pass


def render_choice(text: str, cols: int = 2) -> None:
    if not text:
        return
    try:
        render_choice_question(text, cols=cols)
    except Exception:
        try:
            st.markdown(text)
        except Exception:
            st.text(text[:500])


def _compute_confidence(gr: dict, locked: dict | None = None) -> float:
    """综合置信度计算。"""
    # 图匹配置信度
    if locked and locked.get("canonical_trace"):
        trace = locked["canonical_trace"]
        if hasattr(trace, "verified") and trace.verified:
            # 已验证的 trace → 高置信度
            verification_confidence = getattr(trace, "verification_log", None)
            if verification_confidence and hasattr(verification_confidence, "confidence"):
                base = verification_confidence.confidence
            else:
                base = 0.9
            # 根据图匹配覆盖率调整
            graph_result = gr.get("_graph_result", {})
            alignment = graph_result.get("alignment_score", 1.0)
            return min(base, alignment)
        else:
            # 未验证的 trace → 中等置信度
            return 0.7
    # LLM 批改 → 默认置信度
    return 0.75


def _extract_solution_from_grading(raw: str) -> str:
    """从 LLM 批改输出中提取纯解题过程，去除评分/扣分/评语等批改信息。"""
    if not raw:
        return ""
    lines = raw.split('\n')
    clean = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^#{1,3}\s*评分总览', stripped):
            skip = True
            continue
        if re.match(r'^#{1,3}\s*整体评价', stripped):
            skip = True
            continue
        if re.match(r'^\*\*总分[:：]', stripped):
            skip = True
            continue
        if re.match(r'^扣分项\d+', stripped):
            skip = True
            continue
        if re.match(r'^-\s*判断[:：]', stripped):
            continue
        if re.match(r'^-\s*得分[:：]', stripped):
            continue
        if re.match(r'^-\s*评语[:：]', stripped):
            continue
        if re.match(r'^#{1,3}\s+', stripped) and not re.match(r'^#{1,3}\s*步骤', stripped):
            skip = False
        if not skip:
            clean.append(line)
    result = '\n'.join(clean).strip()
    result = re.sub(r'^\n+', '', result)
    return result


def _extract_final_answer(solution_steps: list, standard_answer: str = "") -> str:
    """从解题步骤中提取最终答案（\\boxed{...} 或最后一个步骤）。"""
    for step in reversed(solution_steps):
        content = step["content"] if isinstance(step, dict) else str(step)
        m = re.search(r'\\boxed\{([^}]+)\}', content)
        if m:
            return f"$\\boxed{{{m.group(1)}}}$"
    if standard_answer:
        m = re.search(r'\\boxed\{([^}]+)\}', standard_answer)
        if m:
            return f"$\\boxed{{{m.group(1)}}}$"
    if standard_answer:
        m = re.search(r'最终答案[：:\s]*\n?(.*?)(?:\n#{1,3}|\n涉及|\n常见|\Z)', standard_answer, re.DOTALL)
        if m:
            return m.group(1).strip()
    if solution_steps:
        last = solution_steps[-1]
        content = last["content"] if isinstance(last, dict) else str(last)
        return content
    return standard_answer or "暂无"


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
db = st.session_state.question_db

# Recommended: use renderers layer for question display
#   from renderers import render_question_card
#   render_question_card(q)  # instead of render_latex(q["question"])

# Page dispatch — importlib-based loader (bypasses sys.path)
import importlib.util as _ilu_pages

def _load_page(name):
    """Load a page module by file path, bypassing sys.path entirely."""
    # Ensure views + renderers packages are registered (needed for imports)
    for _pkg_name in ("views", "renderers"):
        if _pkg_name not in sys.modules:
            _pkg_path = os.path.join(_ROOT, _pkg_name, "__init__.py")
            if not os.path.exists(_pkg_path):
                _pkg_path = os.path.join(r"E:\math_tutor", _pkg_name, "__init__.py")
            _pkg_spec = _ilu_pages.spec_from_file_location(_pkg_name, _pkg_path)
            _pkg = _ilu_pages.module_from_spec(_pkg_spec)
            sys.modules[_pkg_name] = _pkg
            _pkg_spec.loader.exec_module(_pkg)

    _views_dir = os.path.join(_ROOT, "views")
    _path = os.path.join(_views_dir, f"{name}.py")
    if not os.path.exists(_path):
        _views_dir = r"E:\math_tutoriews"
        _path = os.path.join(_views_dir, f"{name}.py")
    _spec = _ilu_pages.spec_from_file_location(f"views.{name}", _path)
    _mod = _ilu_pages.module_from_spec(_spec)
    sys.modules[f"views.{name}"] = _mod
    _spec.loader.exec_module(_mod)
    return _mod

if page == "dashboard":
    _m = _load_page("dashboard_page")
    _m.render_dashboard_page(db, render_latex)

elif page == "practice":
    _m = _load_page("practice_page")
    _m.render_practice_page(db)

elif page == "grading":
    _m = _load_page("grading_page")
    _m.render_grading_page(db, render_latex)

elif page == "question_bank":
    _m = _load_page("question_bank_page")
    _m.render_question_bank_page(db, render_latex)

elif page == "mistakes":
    _m = _load_page("mistakes_page")
    _m.render_mistakes_page(db, render_latex)

elif page == "profile":
    _m = _load_page("profile_page")
    _m.render_profile_page(db, render_latex)

elif page == "settings":
    _m = _load_page("settings_page")
    _m.render_settings_page(db, render_latex)
