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
    """统一数学渲染入口：sanitize → normalize → render。所有带数学内容的地方必须走这里。"""
    if not text:
        return
    from math_sanitizer import safe_latex, is_valid_latex
    try:
        cleaned = safe_latex(text)
        normalized = normalize_latex_style(cleaned)
        st.markdown(normalized)
    except Exception:
        try:
            st.text(f"[数学渲染失败，显示原文]\n{text[:500]}")
        except Exception:
            pass


def render_latex_caption(text: str) -> None:
    """规范化 + 渲染 LaTeX 为小字说明"""
    if text:
        from math_sanitizer import safe_latex
        try:
            st.caption(normalize_latex_style(safe_latex(text)))
        except Exception:
            pass


def md_safe(text: str) -> None:
    """
    st.markdown() 的安全替代。如果文本含有数学符号，强制经过 safe_latex。
    用于无法确定是否含数学内容的文本。
    """
    if not text:
        return
    from math_sanitizer import safe_latex
    # 检测是否含数学内容
    has_math = bool(re.search(r'[\$\\\^_{}]|\\[a-zA-Z]+', text))
    try:
        if has_math:
            st.markdown(normalize_latex_style(safe_latex(text)))
        else:
            st.markdown(text)
    except Exception:
        try:
            st.text(text[:500])
        except Exception:
            pass


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

    selected_bank = st.session_state.get("selected_question")

    if selected_bank:
        # ═══════════════════════════════════════════
        #  情况 A: 题库已选题 — 文本 + 拍照 双入口
        # ═══════════════════════════════════════════
        st.info(f"📋 已选题目: {selected_bank.get('question_id', '?')} — "
                f"{selected_bank.get('category', '')} {selected_bank.get('question_type', '')} "
                f"| 知识点: {', '.join(selected_bank.get('knowledge_points', [])[:3])}")

        if st.button("↩️ 返回题库", key="back_to_bank_from_practice"):
            st.session_state.selected_question = None
            st.rerun()

        # ── 题目展示 ──
        st.subheader("📋 题目内容")
        with st.container(border=True):
            render_latex(selected_bank.get("question", ""))

        # 元数据只读展示
        mt = selected_bank.get("category", "数学一")
        qt = selected_bank.get("question_type", "解答题")
        kps = ", ".join(selected_bank.get("knowledge_points", []))
        st.caption(f"📐 {mt} | 📝 {qt} | 🏷️ {kps}")

        st.markdown("---")
        st.subheader("✍️ 输入你的作答")
        st.caption("文本和图片可同时使用，系统会合并两者内容后再批改。")

        # ── 左右两栏：文本输入 + 拍照上传 ──
        col_text, col_photo = st.columns(2)

        with col_text:
            st.markdown("**⌨️ 文本输入**")
            st.caption("使用 $...$ 包裹公式")
            bank_text_answer = st.text_area(
                "请输入你的解题过程（支持 LaTeX）",
                height=220, key="bank_text_answer", label_visibility="collapsed",
            )

        with col_photo:
            st.markdown("**📷 拍照上传**")
            bank_photo_answer = st.file_uploader(
                "上传作答图片", type=["png", "jpg", "jpeg"],
                key="bank_photo_answer", label_visibility="collapsed",
            )
            if bank_photo_answer:
                st.image(bank_photo_answer, use_container_width=True)

        has_text = bool(bank_text_answer and bank_text_answer.strip())
        has_photo = bank_photo_answer is not None

        # 状态提示
        if has_text and has_photo:
            st.success("📝 文本 + 📷 图片 已就绪，将合并两者内容后批改")
        elif has_text:
            st.info("📝 文本输入已就绪")
        elif has_photo:
            st.info("📷 图片已就绪，提交后将 OCR 识别")

        # ── 提交按钮 ──
        if st.button("🚀 提交批改", type="primary", use_container_width=True,
                     disabled=not (has_text or has_photo)):
            client = get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                student_answer_parts = []

                # 处理图片 OCR
                if has_photo:
                    with st.spinner("OCR 识别答案图片中..."):
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                            f.write(bank_photo_answer.read())
                            a_path = f.name

                        ocr_agent = OCR_Agent(client, st.session_state.get("model", LLM_MODEL))
                        ocr_text = ocr_agent._local_ocr(a_path)
                        if client and ocr_text:
                            cleaned = ocr_agent._llm_cleanup("", ocr_text)
                            if cleaned:
                                ocr_text = cleaned.get("student_answer", ocr_text)
                        if ocr_text and ocr_text.strip():
                            student_answer_parts.append(ocr_text.strip())
                        try:
                            os.unlink(a_path)
                        except Exception:
                            pass

                # 处理文本输入
                if has_text:
                    student_answer_parts.append(bank_text_answer.strip())

                merged_answer = "\n\n".join(student_answer_parts)

                st.session_state.ocr_result = {
                    "success": True,
                    "question": selected_bank["question"],
                    "student_answer": merged_answer,
                    "math_type": mt,
                    "question_type": qt,
                    "knowledge_point": kps,
                    "confidence": 0.9 if has_photo else 1.0,
                    "warnings": [],
                }
                st.session_state.answer_view_mode = False
                st.session_state.page = "grading"
                st.rerun()

    else:
        # ═══════════════════════════════════════════
        #  情况 B: 未选题目 — 原有双 tab 流程
        # ═══════════════════════════════════════════
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
            st.subheader("🎯 智能推荐")
            profile = st.session_state.memory.get_profile()
            weak_points = profile.get("weak_points", [])
            if weak_points:
                w1, w2, w3 = st.columns(3)
                for i, wp in enumerate(weak_points[:3]):
                    col = [w1, w2, w3][i]
                    with col:
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

            col_q2, col_a2 = st.columns(2)
            with col_q2:
                st.subheader("📋 题目内容")
                question_text = st.text_area(
                    "请输入题目（支持 LaTeX）",
                    height=250, key="q_text", label_visibility="collapsed",
                )
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
                    if is_correct:
                        dresult = {
                            "error_type": "无错误", "root_cause": "",
                            "is_repeat": False, "repeat_count": 0,
                            "affects_future": False, "weak_points": [],
                        }
                    else:
                        # 选择题：简洁的错因分析
                        if q_type == "选择题":
                            correct_opt = selected_q.get("correct_option", "")
                            dresult = {
                                "error_type": "选择题答案错误",
                                "root_cause": f"正确答案是 {correct_opt}，你选择了 {student_ans[:10]}。请分析每个选项的数学含义。",
                                "is_repeat": False, "repeat_count": 0,
                                "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                            }
                        else:
                            # 填空题
                            dresult = {
                                "error_type": "填空题错误",
                                "root_cause": f"答案与标准答案不等价。标准答案: {std_ans[:60]}",
                                "is_repeat": False, "repeat_count": 0,
                                "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                            }
                    progress.progress(80, text="快速批改完成，正在保存...")
                else:
                    # Engine C: 图对齐批改（多解法 Best-Match）
                    engine_c_ok = False
                    _canonical = None
                    locked = None
                    _trace_result = None
                    if selected_q.get("question_id"):
                        try:
                            from question_locker import lock_question
                            from graph_matching import grade_with_graph
                            locked = lock_question(selected_q, st.session_state.question_db, client, model)
                            _canonical = locked.get("canonical_trace")

                            # 提取学生轨迹（只做一次，后续 evolver 复用）
                            from student_trace_extractor import extract_student_trace
                            from symbolic_executor import build_student_graph_from_trace
                            _trace_result = extract_student_trace(
                                student_ans or "", question, client, model
                            )
                            student_graph = build_student_graph_from_trace(_trace_result)

                            # Best-Match：遍历所有 canonical methods，取最高分
                            best_score = -1.0
                            best_gresult = None
                            best_method_name = ""
                            method_count = 0

                            if _canonical and _canonical.is_multimethod():
                                progress.progress(40, text=f"多解法图对齐批改中 ({_canonical.method_count()}法)...")
                            else:
                                progress.progress(40, text="图对齐批改中...")

                            for method in (_canonical.methods if _canonical else []):
                                mg = method.graph
                                if not mg or len(mg.nodes) <= 1:
                                    continue
                                method_count += 1
                                try:
                                    graph_result = grade_with_graph(
                                        student_ans or "", mg,
                                        student_graph=student_graph,
                                        student_trace=_trace_result,
                                    )
                                    score = graph_result.get("score", 0)
                                    if score > best_score:
                                        best_score = score
                                        best_gresult = {
                                            "success": True,
                                            "total": round(score, 1),
                                            "step_score": round(score * 0.5, 1),
                                            "result_score": round(score * 0.5, 1),
                                            "step_analysis": [
                                                {"num": i+1, "content": m.get("label", ""),
                                                 "judgment": "正确" if m.get("matched") else "缺失/错误",
                                                 "score": f"{m.get('weight', 0):.1f}",
                                                 "comment": m.get("error", "")}
                                                for i, m in enumerate(graph_result.get("matched_steps", []))
                                            ],
                                            "deductions": [],
                                            "comment": graph_result.get("error_label", ""),
                                            "_engine": "C_graph",
                                        }
                                        best_method_name = method.method_name
                                except Exception:
                                    continue

                            if best_gresult is not None:
                                gresult = best_gresult
                                # 方法分类结果
                                try:
                                    from method_classifier import classify_student_method
                                    classification = classify_student_method(_trace_result, _canonical)
                                    gresult["method_family"] = classification["family_name"]
                                    gresult["tier"] = (
                                        "t1_fast_path" if (
                                            classification["recommendation"] != "semantic_fallback"
                                            and _compute_confidence(None, None) > 0.8
                                        ) else "t3_graph_match" if classification["recommendation"] != "semantic_fallback"
                                        else "t4_semantic_fallback"
                                    )
                                except Exception:
                                    pass
                                # 记录匹配到的方法并增加 usage_count
                                if best_method_name and _canonical:
                                    gresult["method_matched"] = best_method_name
                                    for m in _canonical.methods:
                                        if m.method_name == best_method_name:
                                            m.usage_count += 1
                                            break

                                # 更新 solution 为 lock_question 的标准答案
                                if locked.get("standard_answer"):
                                    solution["standard_answer"] = locked["standard_answer"]
                                engine_c_ok = True
                                progress.progress(70, text=f"图对齐批改完成 ({method_count}法, 最佳: {best_method_name})...")
                        except Exception as _e_c:
                            print(f"[Engine C 失败] {_e_c}")

                    if not engine_c_ok:
                        # Engine B: LLM 批改 (解答题/证明题, 或缓存未命中)
                        # 传入 canonical_trace 让 LLM 参考结构化标准解
                        grading = GradingAgent(client, model)
                        gresult = grading.grade(
                            question=question, standard_answer=std_ans,
                            student_answer=student_ans, total_score=total_score,
                            knowledge_points=ocr_data.get("knowledge_point", ""),
                            difficulty=selected_q.get("difficulty", "中等"),
                            canonical_trace=_canonical,
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
                progress.progress(82, text="检查是否可进化题库...")

                # Step 3.5: 候选方法提交 — 高分低匹配时提交到人工审核队列
                try:
                    _total = gresult.get("total", 0)
                    _max = solution.get("total_score", 10)
                    if _total >= _max * 0.85 and selected_q.get("question_id"):
                        from trace_evolver import submit_candidate
                        if _trace_result and _trace_result.get("steps"):
                            submitted = submit_candidate(
                                question_id=selected_q["question_id"],
                                student_trace=_trace_result,
                                score=_total,
                                total_score=_max,
                                existing_trace=_canonical,
                                grading_summary={"comment": gresult.get("comment", ""),
                                                 "engine": gresult.get("engine", "")},
                            )
                            if submitted:
                                gresult["candidate_submitted"] = True
                                progress.progress(84, text="候选方法已提交审核队列")
                except Exception as _evo_err:
                    pass  # 非关键路径

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

            # 判断题型
            selected_q = st.session_state.get("selected_question") or {}
            q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
            is_fast = q_type in ("选择题", "填空题")

            # 从标准答案中提取知识点和易错点
            sa_kp = sa.get("knowledge_points", [])
            sa_cm = sa.get("common_mistakes", [])

            st.markdown("---")

            # 评分模式提示
            mode_label = "🤖 AI 在线批改" if st.session_state.get("api_key") else "📋 离线批改（基于标准答案对比）"
            st.caption(mode_label)

            # ===== 模板 1: 选择题 + 填空题 =====
            if is_fast:
                _render_choice_fill_ui(gr, sa, dr, ocr_data, selected_q)

            # ===== 模板 2: 解答题 + 证明题 =====
            else:
                _render_essay_grading_ui(gr, sa, dr, ocr_data, selected_q)


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

    # ── 加载已有 profiles ──
    profiles = credential_store.load_profiles()
    profile_names = [p["name"] for p in profiles]
    active = credential_store.get_active_profile()

    # ═══════════════════════════════════════
    #  Provider 配置管理
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("🔑 LLM Provider 管理")
        st.caption("支持多个大模型配置，一键切换。API Key 自动加密保存 15 天，过期自动清除。")

        # ── 已有配置列表 ──
        if profiles:
            st.markdown("**已保存的配置：**")
            for p in profiles:
                is_active = active and p["name"] == active["name"]
                badge = "🟢 使用中" if is_active else "⚪"
                proto_label = p.get("protocol", "openai")
                col_name, col_info, col_act, col_del = st.columns([2, 3, 1, 1])
                with col_name:
                    st.markdown(f"**{p['name']}** {badge}")
                with col_info:
                    masked = credential_store.mask_key(p.get("api_key", ""))
                    days_left = p.get("ttl_days", 15) - int((time.time() - p.get("created_at", 0)) / 86400)
                    st.caption(f"{p.get('base_url', '')} | {p.get('model', '')} | {proto_label} | Key: {masked} | {max(0, days_left)}天后过期")
                with col_act:
                    if not is_active:
                        if st.button("切换", key=f"switch_{p['name']}"):
                            credential_store.set_active_profile(p["name"])
                            st.session_state.api_key = p["api_key"]
                            st.session_state.base_url = p["base_url"]
                            st.session_state.model = p["model"]
                            st.session_state.protocol = p.get("protocol", "openai")
                            st.session_state.llm_client = create_client(
                                api_key=p["api_key"],
                                base_url=p["base_url"],
                                protocol=p.get("protocol", "openai"),
                            )
                            st.toast(f"已切换到 {p['name']}")
                            st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{p['name']}", help=f"删除 {p['name']}"):
                        credential_store.delete_profile(p["name"])
                        st.toast(f"已删除 {p['name']}")
                        st.rerun()
            st.markdown("---")

        # ── 新增/编辑配置（简化版）──
        st.markdown("**添加配置：**")

        # 预设: (base_url, model, protocol)
        presets = {
            "DeepSeek": ("https://api.deepseek.com/anthropic", "deepseek-v4-pro", "anthropic"),
            "OpenAI": ("https://api.openai.com/v1", "gpt-4o", "openai"),
            "通义千问": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", "openai"),
            "Kimi": ("https://api.moonshot.cn/v1", "moonshot-v1-8k", "openai"),
            "智谱": ("https://open.bigmodel.cn/api/paas/v4", "glm-4", "openai"),
        }

        preset = st.selectbox(
            "选择服务商",
            list(presets.keys()),
            key="provider_preset",
        )
        default_url, default_model, default_protocol = presets[preset]

        profile_key = st.text_input(
            "API Key",
            type="password",
            placeholder="粘贴你的 API Key",
            key="profile_key_input",
        )

        # 高级选项：URL、模型名、协议，默认折叠
        with st.expander("高级选项（通常无需修改）"):
            profile_url = st.text_input(
                "API Base URL", value=default_url, key="profile_url_input",
            )
            profile_model = st.text_input(
                "模型名称", value=default_model, key="profile_model_input",
            )
            profile_protocol = st.selectbox(
                "API 协议",
                ["openai", "anthropic"],
                index=0 if default_protocol == "openai" else 1,
                key="profile_protocol_input",
                help="OpenAI 兼容接口选 openai，Anthropic 接口选 anthropic",
            )

        save_col, test_col = st.columns(2)
        with save_col:
            if st.button("💾 保存并启用", type="primary", use_container_width=True,
                         disabled=not profile_key):
                credential_store.save_profile(
                    name=preset,
                    api_key=profile_key,
                    base_url=profile_url or default_url,
                    model=profile_model or default_model,
                    ttl_days=15,
                    protocol=profile_protocol,
                )
                st.session_state.api_key = profile_key
                st.session_state.base_url = profile_url or default_url
                st.session_state.model = profile_model or default_model
                st.session_state.protocol = profile_protocol
                st.session_state.llm_client = create_client(
                    api_key=profile_key,
                    base_url=profile_url or default_url,
                    protocol=profile_protocol,
                )
                st.success(f"✅ {preset} 已保存并启用（协议: {profile_protocol}）")
                st.rerun()

        with test_col:
            if st.button("🔍 测试连接", use_container_width=True,
                         disabled=not profile_key):
                try:
                    test_client = create_client(
                        api_key=profile_key,
                        base_url=profile_url or default_url,
                        protocol=profile_protocol,
                    )
                    resp = test_client.chat.completions.create(
                        model=profile_model or default_model,
                        messages=[{"role": "user", "content": "说一个数字"}],
                        max_tokens=10,
                    )
                    st.success(f"✅ 连接成功: {resp.choices[0].message.content}")
                except Exception as e:
                    st.error(f"❌ 连接失败: {e}")

    # ═══════════════════════════════════════
    #  当前生效配置一览
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("📋 当前生效配置")
        if active:
            ic1, ic2, ic3, ic4, ic5 = st.columns(5)
            ic1.metric("配置名称", active["name"])
            ic2.metric("Base URL", active.get("base_url", "-"))
            ic3.metric("模型", active.get("model", "-"))
            ic4.metric("协议", active.get("protocol", "openai"))
            days_left = active.get("ttl_days", 15) - int((time.time() - active.get("created_at", 0)) / 86400)
            ic5.metric("剩余天数", f"{max(0, days_left)} 天")
        else:
            st.info("尚未配置 API Key，请在上方添加 Provider 配置。")

    # ═══════════════════════════════════════
    #  隐私安全检查
    # ═══════════════════════════════════════
    with st.container(border=True):
        st.subheader("🔒 隐私安全检查")
        st.caption("扫描项目文件，检测可能泄露的 API Key / Secret")

        if st.button("🔍 扫描隐私泄露风险", use_container_width=True):
            import re as _re
            sensitive_patterns = [
                (r'sk-[a-zA-Z0-9]{20,}', '疑似 OpenAI/DeepSeek API Key'),
                (r'api_key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', '硬编码的 API Key'),
                (r'password\s*=\s*["\'][^"\']{4,}["\']', '硬编码的密码'),
                (r'token\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', '硬编码的 Token'),
            ]
            scan_dirs = ["agents", "prompts", "storage/questions"]
            scan_exts = {".py", ".json", ".md", ".yaml", ".yml"}
            findings = []

            for scan_dir in scan_dirs:
                full_dir = os.path.join(_ROOT, scan_dir)
                if not os.path.isdir(full_dir):
                    continue
                for root, _, files in os.walk(full_dir):
                    for fname in files:
                        if os.path.splitext(fname)[1] not in scan_exts:
                            continue
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            for pattern, desc in sensitive_patterns:
                                for m in _re.finditer(pattern, content):
                                    findings.append((fpath, desc, m.group()[:20] + "..."))
                        except Exception:
                            pass

            # 也扫描根目录 py 文件
            for fname in os.listdir(_ROOT):
                if fname.endswith(".py"):
                    fpath = os.path.join(_ROOT, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        for pattern, desc in sensitive_patterns:
                            for m in _re.finditer(pattern, content):
                                findings.append((fpath, desc, m.group()[:20] + "..."))
                    except Exception:
                        pass

            if findings:
                st.warning(f"⚠️ 发现 {len(findings)} 处潜在泄露风险：")
                for fpath, desc, snippet in findings[:20]:
                    rel = os.path.relpath(fpath, _ROOT)
                    st.caption(f"  `{rel}` — {desc}: `{snippet}`")
            else:
                st.success("✅ 未发现明显的 API Key 泄露风险")

        # .gitignore 状态
        st.markdown("**`.gitignore` 敏感文件覆盖检查：**")
        gitignore_path = os.path.join(_ROOT, ".gitignore")
        critical_files = [".env", ".env.*", "storage/.credentials.json", "storage/settings.json"]
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                gi_content = f.read()
            for cf in critical_files:
                if cf in gi_content:
                    st.caption(f"✅ `{cf}` — 已被 .gitignore 排除")
                else:
                    st.error(f"❌ `{cf}` — 未被 .gitignore 排除，有泄露风险！")
        else:
            st.error("❌ 项目根目录缺少 .gitignore 文件")

    # ═══════════════════════════════════════
    #  数据管理
    # ═══════════════════════════════════════
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
