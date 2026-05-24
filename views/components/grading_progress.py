"""Grading progress card — staged progress bar for AI grading pipeline.

Matches the orchestrator phases: prepare → solution → grading → diagnosis → finalize.
"""

import html as _html
import math as _math
import streamlit as st

# ── Phase definitions ──

PHASES = [
    ("prepare",   "准备题目"),
    ("solution",  "标准答案"),
    ("grading",   "AI批改"),
    ("diagnosis", "诊断分析"),
    ("finalize",  "完成结果"),
]
_PHASE_ORDER = [k for k, _ in PHASES]


def inject_progress_css():
    """Inject grading progress card CSS. Call once at app startup."""
    st.markdown("""
    <style>
    .grading-progress-card {
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 16px 16px 14px 16px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
        margin: 10px 0 14px 0;
    }
    .grading-progress-title {
        font-size: 1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .grading-progress-subtitle {
        font-size: 0.88rem;
        color: #64748b;
        margin-bottom: 12px;
    }
    .grading-progress-bar-wrap {
        width: 100%;
        height: 12px;
        background: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
        position: relative;
    }
    .grading-progress-bar {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        transition: width 0.35s ease;
        position: relative;
    }
    .grading-progress-bar::after {
        content: "";
        position: absolute;
        inset: 0;
        background-image: linear-gradient(
            135deg,
            rgba(255,255,255,0.20) 25%, transparent 25%,
            transparent 50%, rgba(255,255,255,0.20) 50%,
            rgba(255,255,255,0.20) 75%, transparent 75%, transparent 100%
        );
        background-size: 24px 24px;
        animation: grading-progress-stripes 1s linear infinite;
    }
    @keyframes grading-progress-stripes {
        from { background-position: 0 0; }
        to   { background-position: 24px 0; }
    }
    .grading-progress-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
        font-size: 0.82rem;
        color: #64748b;
    }
    .grading-progress-steps {
        display: flex;
        justify-content: space-between;
        gap: 6px;
        margin-top: 14px;
        flex-wrap: nowrap;
    }
    .grading-progress-step {
        flex: 1;
        text-align: center;
        font-size: 0.74rem;
        color: #94a3b8;
    }
    .grading-progress-step-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin: 0 auto 6px auto;
        background: #cbd5e1;
    }
    .grading-progress-step.done .grading-progress-step-dot {
        background: #2563eb;
    }
    .grading-progress-step.current .grading-progress-step-dot {
        background: #7c3aed;
        box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.12);
    }
    .grading-progress-step.done,
    .grading-progress-step.current {
        color: #334155;
        font-weight: 600;
    }
    .grading-progress-hint {
        margin-top: 12px;
        font-size: 0.78rem;
        color: #64748b;
        background: #f8fafc;
        border-radius: 10px;
        padding: 8px 10px;
    }
    @media (max-width: 768px) {
        .grading-progress-card {
            border-radius: 16px;
            padding: 14px;
        }
        .grading-progress-title { font-size: 0.98rem; }
        .grading-progress-subtitle { font-size: 0.84rem; }
        .grading-progress-step { font-size: 0.68rem; }
    }
    </style>
    """, unsafe_allow_html=True)


def render_progress(progress: int, phase: str, detail: str = "",
                    elapsed_s: int = 0):
    """Render the staged grading progress card.

    Args:
        progress: 0-100 percentage
        phase: one of prepare/solution/grading/diagnosis/finalize
        detail: current sub-step description
        elapsed_s: seconds elapsed since submission
    """
    progress = max(0, min(100, int(progress)))
    current_idx = _PHASE_ORDER.index(phase) if phase in _PHASE_ORDER else 0

    step_html = []
    for i, (key, label) in enumerate(PHASES):
        cls = "done" if i < current_idx else "current" if i == current_idx else ""
        step_html.append(
            f"""<div class="grading-progress-step {cls}">
                <div class="grading-progress-step-dot"></div>
                <div>{_html.escape(label)}</div>
            </div>"""
        )

    subtitle = detail or "正在处理中，请稍候…"

    st.markdown(
        f"""
        <div class="grading-progress-card">
            <div class="grading-progress-title">🤖 正在 AI 批改</div>
            <div class="grading-progress-subtitle">{_html.escape(subtitle)}</div>
            <div class="grading-progress-bar-wrap">
                <div class="grading-progress-bar" style="width: {progress}%;"></div>
            </div>
            <div class="grading-progress-meta">
                <span>已等待 {elapsed_s} 秒</span>
                <span>{progress}%</span>
            </div>
            <div class="grading-progress-steps">{''.join(step_html)}</div>
            <div class="grading-progress-hint">
                批改过程中可以保持本页打开；手机刷新后也会自动恢复任务。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Smooth progress estimation ──


def estimate_smooth_progress(
    *,
    elapsed_s: float,
    status: str = "processing",
    base_progress: int = 0,
    expected_s: int = 90,
    max_before_done: int = 97,
) -> int:
    """Estimate smooth grading progress that never stalls.

    - processing: exponential growth based on elapsed time, capped at max_before_done
    - completed: 100
    - failed: stays at current progress

    The exponential curve grows fast early then slows, so long tasks
    don't reach 100% prematurely.
    """
    if status == "completed":
        return 100
    if status == "failed":
        return max(0, min(100, int(base_progress or 0)))

    elapsed_s = max(0, float(elapsed_s or 0))
    expected_s = max(10, int(expected_s or 90))

    # Exponential: 1 - e^(-t/expected).  After expected_s, ~63%.
    estimated = 100 * (1 - _math.exp(-elapsed_s / expected_s))

    progress = max(int(base_progress or 0), int(estimated))
    return max(1, min(max_before_done, progress))


def get_expected_grading_seconds(selected_q: dict = None, ocr_data: dict = None) -> int:
    """Return expected grading time based on question type.

    Choice questions are fast (~18s); proof/solution questions are slow (~95s).
    """
    q_type = (
        (selected_q or {}).get("question_type")
        or (ocr_data or {}).get("question_type")
        or ""
    )
    if q_type == "选择题":
        return 18
    if q_type == "填空题":
        return 25
    if q_type in ("解答题", "证明题"):
        return 95
    return 60
