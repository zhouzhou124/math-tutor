"""grading_result.py — Grading result cards.

Card layout:
  Score → Knowledge Points → Diagnosis → Step Comparison → Standard Solution → Recommendations
"""
import json
import logging
import re
import streamlit as st
from latex_utils import split_latex_text, render_ast

logger = logging.getLogger(__name__)

# ── P40: Grading result mobile CSS ──
_GRADING_MOBILE_CSS = """
<style>
/* P40: AI 批改结果移动端响应式 */
.grading-result-container {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
}
.grading-card,
.grading-score-card,
.grading-diagnosis-card,
.standard-solution-card,
.solution-step-card {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    overflow-wrap: anywhere;
    word-break: break-word;
}
/* 批改区块级公式：与全局 .katex-display / st.latex 横滚规则对齐 */
.grading-result-container .katex-display,
.grading-result-container [data-testid="stLatex"],
.grading-result-container [data-testid="stMarkdownContainer"] .katex-display {
    max-width: 100%;
    box-sizing: border-box;
}
.grading-math-scroll {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
}
.grading-code-scroll {
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.grading-action-row {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0;
}
.grading-debug-panel {
    max-width: 100%;
    overflow-x: auto;
}
@media (max-width: 768px) {
    .grading-result-container {
        padding: 0 !important;
        overflow-x: clip;
        min-width: 0;
    }
    .grading-result-container .katex-display,
    .grading-result-container [data-testid="stLatex"],
    .grading-result-container [data-testid="stMarkdownContainer"] .katex-display {
        overflow-x: auto !important;
        overflow-y: visible !important;
        -webkit-overflow-scrolling: touch;
        touch-action: pan-x;
        white-space: nowrap !important;
    }
    .grading-result-container .katex-display > .katex,
    .grading-result-container [data-testid="stLatex"] .katex {
        max-width: none !important;
        white-space: nowrap !important;
    }
    .grading-card,
    .grading-score-card,
    .grading-diagnosis-card,
    .standard-solution-card,
    .solution-step-card {
        margin-bottom: 10px;
    }
    .grading-action-row {
        flex-direction: column;
    }
    .grading-action-row button,
    .grading-action-row .stButton > button {
        width: 100% !important;
    }
    .grading-math-scroll {
        padding: 4px 0;
    }
    .grading-debug-panel pre,
    .grading-debug-panel code {
        font-size: 0.75rem !important;
        white-space: pre-wrap !important;
        word-break: break-all !important;
    }
}
</style>
"""


def inject_grading_mobile_css():
    """P40: Inject grading result mobile responsive CSS."""
    st.markdown(_GRADING_MOBILE_CSS, unsafe_allow_html=True)


def _trace_raw_source_render_attempt(label: str, text: str, source: str = "") -> bool:
    """P37.6.4: Log when raw source text is about to reach a student-facing render.

    Returns True if a raw source leak was detected (caller should block rendering).
    """
    from services.solution_quality import detect_student_raw_source_leak
    if not text or not isinstance(text, str):
        return False
    issues = detect_student_raw_source_leak(text)
    if issues:
        preview = text[:200].replace("\n", "\\n")
        logger.warning(
            "[RAW_SOURCE_LEAK_TRACE] label=%s source=%s issues=%s preview=%s",
            label, source, issues, preview,
        )
        return True
    return False


def _is_admin_user() -> bool:
    """Check if current user has admin role."""
    auth = st.session_state.get("auth") or {}
    if auth.get("is_admin"):
        return True
    if str(auth.get("role", "")).lower() == "admin":
        return True
    cu = st.session_state.get("current_user")
    if cu is not None:
        if getattr(cu, "is_admin", False):
            return True
        if str(getattr(cu, "role", "")).lower() == "admin":
            return True
    user = st.session_state.get("user") or {}
    if str(user.get("role", "")).lower() == "admin":
        return True
    for key in ("user_role", "role"):
        if str(st.session_state.get(key, "")).lower() == "admin":
            return True
    username = (
        auth.get("username")
        or user.get("username")
        or st.session_state.get("username")
        or st.session_state.get("user_name")
        or ""
    )
    return str(username).lower() == "admin"


def _should_show_solution_debug() -> bool:
    """P37.4: Admin-only debug expander visibility check."""
    import os
    if not _is_admin_user():
        return False
    if st.session_state.get("debug_mode"):
        return True
    return os.environ.get("SHOW_SOLUTION_DEBUG", "") == "1"


def _render_blocked_solution_debug(solution: dict, grading_result: dict | None = None) -> None:
    """P37.4.2+: Admin-only debug preview for blocked solution candidates."""
    if not _is_admin_user():
        return

    debug_on = _should_show_solution_debug()

    if not debug_on:
        st.caption("💡 你是 admin，但尚未开启开发者调试模式。请在侧边栏打开「开发者调试模式」查看被拦截的候选内容。")
        return

    gr = grading_result if isinstance(grading_result, dict) else (st.session_state.get("grading_result") or {})
    issues = (
        solution.get("_blocked_solution_issues")
        or gr.get("_blocked_solution_issues")
        or []
    )
    qr = (
        solution.get("_blocked_solution_quality_report")
        or gr.get("_blocked_solution_quality_report")
        or solution.get("_quality_report")
        or gr.get("_quality_report")
        or {}
    )
    if not issues and isinstance(qr, dict):
        issues = qr.get("issues") or []
    locations = (
        solution.get("_blocked_solution_error_locations")
        or gr.get("_blocked_solution_error_locations")
        or []
    )
    candidate = solution.get("_blocked_solution_candidate") or gr.get("_blocked_solution_candidate")
    preview = solution.get("_failed_raw_preview") or gr.get("_failed_raw_preview")
    source = (
        solution.get("_blocked_solution_source")
        or gr.get("_blocked_solution_source")
        or solution.get("standard_solution_source", "")
    )
    model_used = solution.get("model_used") or solution.get("_model_used") or gr.get("_model_used", "")
    status = solution.get("standard_solution_status", "")

    logger.info(
        "[ADMIN_DEBUG_RAW_PREVIEW] status=%s source=%s issues_count=%d has_candidate=%s",
        status, source, len(issues), isinstance(candidate, dict),
    )
    with st.expander("🔧 调试：查看被拦截的标准解答候选（仅 admin）"):
        st.markdown('<div class="grading-debug-panel">', unsafe_allow_html=True)
        st.warning("以下内容未通过质量门禁，仅供开发调试，不会保存为标准解答。")
        st.markdown(f"**状态：** `{status}`　**来源：** `{source}`　**模型：** `{model_used}`")
        if issues:
            st.markdown("**质量问题：**")
            for issue in issues:
                st.markdown(f"- `{issue}`")

        if locations:
            st.markdown("**问题字段定位：**")
            for loc in locations:
                st.markdown(f"- **{loc.get('issue', '?')}** → `{loc.get('path', '?')}`")
                if loc.get("preview"):
                    st.code(loc["preview"], language=None)
                if loc.get("suggestion"):
                    st.caption(f"建议：{loc['suggestion']}")

        if isinstance(candidate, dict):
            raw_ans = candidate.get("standard_answer") or ""
            if raw_ans.strip():
                st.markdown("**原始 standard_answer：**")
                st.code(raw_ans[:3000], language=None)
            candidate_struct = candidate.get("_structured")
            if isinstance(candidate_struct, dict):
                import json
                st.markdown("**原始 _structured (JSON)：**")
                st.code(json.dumps(candidate_struct, ensure_ascii=False, indent=2)[:5000], language="json")
        elif preview:
            st.markdown("**原始内容预览：**")
            st.code(preview, language=None)
        else:
            st.info(
                "当前结果没有保存 blocked candidate，请点击「重新生成标准解答」后再查看。"
                "以下为当前 solution debug snapshot。"
            )
            snapshot_ans = solution.get("standard_answer") or gr.get("standard_answer") or ""
            if snapshot_ans.strip():
                st.markdown("**当前 standard_answer：**")
                st.code(snapshot_ans[:3000], language=None)
        st.markdown('</div>', unsafe_allow_html=True)


def render_blocked_solution_debug_panel(
    solution: dict,
    grading_result: dict | None = None,
    context: str = "",
) -> None:
    """Public API: render admin debug panel for blocked solutions."""
    _render_blocked_solution_debug(solution, grading_result=grading_result)


def _render_solution_failure_with_debug(
    solution: dict,
    message: str,
    issues: list | None = None,
    raw_answer: str = "",
) -> list[dict]:
    """Render solution failure warning with admin debug panel and retry button."""
    events: list[dict] = []
    with st.expander("📖 查看标准解法", expanded=False):
        st.warning(message)
        if issues:
            st.caption("质量问题：" + "、".join(str(i) for i in issues[:4]))
        _render_blocked_solution_debug(solution)
        if raw_answer and len(raw_answer.strip()) >= 2:
            st.markdown(f"**最终答案：** {raw_answer}")

        st.markdown('<div class="grading-action-row">', unsafe_allow_html=True)
        if st.button("🔄 重新生成标准解答", key="retry_sol_failure"):
            events.append({"type": "retry_solution"})
        st.markdown('</div>', unsafe_allow_html=True)
    return events


def render_score_card(gr: dict, total_score: int = 10) -> None:
    """Score overview card — prominent, first thing the student sees."""
    score = gr.get("total", 0)
    ratio = score / total_score if total_score > 0 else 0

    if ratio >= 0.9:
        emoji, color, bg = "🌟", "#16a34a", "#f0fdf4"
    elif ratio >= 0.6:
        emoji, color, bg = "📝", "#f59e0b", "#fffbeb"
    else:
        emoji, color, bg = "📚", "#dc2626", "#fef2f2"

    with st.container(border=True):
        st.markdown(f"""
        <div class="grading-score-card" style="text-align:center;padding:8px 0;">
            <span style="font-size:2.5em;">{emoji}</span><br>
            <span style="font-size:2.2em;font-weight:800;color:{color};">{score}</span>
            <span style="font-size:1.2em;color:#94a3b8;"> / {total_score}</span>
        </div>
        """, unsafe_allow_html=True)

        comment = gr.get("comment", "")
        if comment:
            st.caption(comment)


def render_knowledge_points(knowledge_points: list, question: dict = None, question_db=None) -> None:
    """独立展示知识点卡片 — 不在标准解法中隐藏

    当 *knowledge_points* 为空且 *question_db* 可用时，尝试从题目文本自动检测知识点。
    """
    # Auto-detect on the fly when the question JSON lacks tags
    if not knowledge_points and question_db and question:
        try:
            q_text = question.get("raw_question_text") or question.get("question", "")
            if q_text:
                knowledge_points = question_db.auto_tag(q_text)
        except Exception:
            pass

    with st.container(border=True):
        st.markdown('<div class="grading-card">', unsafe_allow_html=True)
        st.markdown("**📚 考查知识点**")

        if not knowledge_points:
            st.info("暂无知识点标注，请查看标准解法了解本题涉及的知识点")
        else:
            tags_html = " ".join(
                f"<span style='background:#eef2ff;color:#4338ca;padding:4px 10px;"
                f"border-radius:16px;font-size:0.85em;border:1px solid #c7d2fe;margin:2px;'>{kp}</span>"
                for kp in knowledge_points[:6]
            )
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:6px;'>{tags_html}</div>", unsafe_allow_html=True)

        # 知识点详情
        if question:
            common_mistakes = question.get("common_mistakes", [])
            if common_mistakes:
                st.markdown("")
                st.markdown("**⚠️ 常见易错点**")
                cm_tags = " ".join(
                    f"<span style='background:#fff7ed;color:#9a3412;padding:3px 8px;"
                    f"border-radius:12px;font-size:0.78em;border:1px solid #fed7aa;margin:2px;'>{cm}</span>"
                    for cm in common_mistakes[:4]
                )
                st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:4px;'>{cm_tags}</div>", unsafe_allow_html=True)
            elif not knowledge_points:
                st.markdown("")
                st.markdown("**⚠️ 常见易错点**")
                st.info("暂无常见易错点标注")
        st.markdown('</div>', unsafe_allow_html=True)


def render_diagnosis_card(dr: dict, gr: dict) -> None:
    """Error diagnosis card."""
    error_type = dr.get("error_type", "")
    root_cause = dr.get("root_cause", "")
    is_repeat = dr.get("is_repeat", False)
    weak_points = dr.get("weak_points", [])

    with st.container(border=True):
        st.markdown('<div class="grading-diagnosis-card">', unsafe_allow_html=True)
        st.markdown("**🔍 错因诊断**")

        if not error_type and not root_cause:
            # 检查是否是未作答状态
            comment = gr.get("comment", "")
            if "未作答" in comment:
                error_type = "未作答"
                root_cause = "学生未输入任何作答内容，建议先尝试独立解题再查看标准答案"
            
        if error_type:
            st.markdown(f"**错误类型**: {error_type}")

        if root_cause:
            st.info(root_cause)
        elif not error_type:
            st.info("暂无诊断信息")

        if is_repeat:
            repeat_count = dr.get("repeat_count", 0)
            st.warning(f"⚠️ 历史重复错误（已出现 {repeat_count} 次），需重点巩固")

        if weak_points:
            tags = " ".join(
                f"<span style='background:#fef2f2;color:#dc2626;padding:2px 8px;"
                f"border-radius:12px;font-size:0.8em;'>{w}</span>"
                for w in weak_points[:5]
            )
            st.markdown(f"**薄弱知识点**: {tags}", unsafe_allow_html=True)
        elif error_type:
            st.markdown("**薄弱知识点**:")
            st.info("暂无薄弱知识点分析")
        st.markdown('</div>', unsafe_allow_html=True)


def _view_question_type(solution: dict, grading_result: dict | None = None) -> str:
    gr = grading_result or {}
    selected = st.session_state.get("selected_question") or {}
    ocr = st.session_state.get("ocr_result") or {}
    return (
        gr.get("question_type")
        or solution.get("question_type")
        or selected.get("question_type")
        or ocr.get("question_type")
        or ""
    )


def _has_raw_latex_fragment(text: str) -> bool:
    s = str(text or "")
    try:
        from services.grading_adapter import contains_raw_tex_outside_math
        if contains_raw_tex_outside_math(s):
            return True
    except Exception:
        pass
    return any(marker in s for marker in (
        r"\begin", r"\end", "$$", r"\[", r"\]", r"\frac", r"\dfrac",
        r"\sum", r"\lim", r"\sim", r"\le", r"\ge", r"\mathrm",
        r"\Rightarrow", r"\Leftarrow", r"\cdot", r"\text", r"\sqrt",
        r"\int", r"\iint", r"\ln", r"\pi", r"\overline",
    ))


def _should_decompose_math_text(text: str) -> bool:
    s = str(text or "")
    if not s.strip():
        return False
    if _has_raw_latex_fragment(s):
        return True
    return bool(re.search(r"\\\(|\\\[|\$\$", s))


def render_math_text(text: str) -> bool:
    """Render view-pipeline text (P57: same path as 3289443 grading LaTeX, no block re-split)."""
    if not text:
        return False
    try:
        from services.grading_adapter import _unescape_json_newlines
        s = _unescape_json_newlines(str(text))
    except Exception:
        s = str(text).replace("\\n", "\n")

    try:
        from services.grading_adapter import (
            _has_cjk,
            _prepare_prose_math_text,
            balance_inline_math_delimiters,
            normalize_inline_math_tokens,
            repair_ai_grading_math_artifacts,
            repair_derivation_text_block,
            prepare_grading_math_for_render,
        )
        repaired = repair_ai_grading_math_artifacts(repair_derivation_text_block(s))
        if _has_cjk(repaired):
            s = _prepare_prose_math_text(repaired)
        else:
            s = prepare_grading_math_for_render(
                normalize_inline_math_tokens(
                    balance_inline_math_delimiters(repaired)
                )
            )
    except Exception:
        pass

    if _has_raw_latex_fragment(s) and s.count("{") > s.count("}"):
        st.code(s, language="latex")
        return True
    try:
        from services.grading_adapter import _has_cjk, contains_raw_tex_outside_math
        if (
            _has_cjk(s)
            and "$" in s
            and r"\begin{" not in s
            and r"\begin{aligned}" not in s
            and not contains_raw_tex_outside_math(s)
        ):
            st.markdown(s)
            return True
    except Exception:
        pass
    if "\n" in s and not _has_raw_latex_fragment(s):
        st.markdown(s)
        return True
    try:
        _render_text_or_latex(s)
    except Exception:
        if _has_raw_latex_fragment(s):
            st.code(s, language="latex")
        else:
            st.markdown(s)
    return True


def _format_solution_title(title: str) -> str:
    s = str(title or "").strip()
    if not s:
        return ""
    try:
        from services.grading_adapter import _prepare_prose_math_text, repair_derivation_text_block
        return _prepare_prose_math_text(repair_derivation_text_block(s))
    except Exception:
        return s


def _safe_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)


def _render_degraded_answer_card(answer_card, exc: Exception | None = None) -> bool:
    if not answer_card:
        return False
    st.warning("答案卡部分字段渲染异常，以下为可读取内容：")
    if isinstance(answer_card, dict):
        correct = answer_card.get("correct_answer") or answer_card.get("correct_option")
        if correct:
            st.success(f"正确答案：{correct}")
        for key in ("student_answer", "is_correct", "is_equivalent", "confidence", "proof_status"):
            if answer_card.get(key) is not None and answer_card.get(key) != "":
                st.caption(f"{key}: {answer_card.get(key)}")
    else:
        st.code(_safe_json(answer_card))
    return True


def _render_answer_card(view: dict, *, best_effort: bool = True) -> bool:
    q_type = view.get("question_type", "")
    card = view.get("answer_card") or {}
    if not card:
        return False
    if q_type == "选择题":
        correct = card.get("correct_answer") or ""
        if correct:
            st.success(f"正确答案：{correct}")
        else:
            st.warning("正确答案暂未生成。")
        if card.get("student_answer"):
            verdict = "正确" if card.get("is_correct") is True else "错误" if card.get("is_correct") is False else "需复核"
            st.caption(f"你的答案：{card.get('student_answer')}　判定：{verdict}")
    elif q_type == "填空题":
        correct = card.get("correct_answer") or ""
        if correct:
            st.markdown("**标准答案：**")
            text = str(correct).strip()
            text = re.sub(r"^(?:标准答案|最终答案|故填|填)\s*[：:为]?\s*", "", text).strip()
            try:
                from services.grading_adapter import _is_incomplete_math_expr
                if _is_incomplete_math_expr(text):
                    text = ""
            except Exception:
                pass
            if not text:
                st.warning("标准答案暂未识别，详细解析见下方。")
            else:
                is_long_formula = (
                    len(text) > 80
                    or any(marker in text for marker in (r"\begin", r"\\", r"\int", r"\sum", "cases", "matrix"))
                )
                if is_long_formula:
                    render_solution_block({"type": "latex_display", "content": text})
                else:
                    render_math_text(text)
        else:
            st.warning("标准答案暂未识别，详细解析见下方。")
        if card.get("student_answer"):
            verdict = "等价" if card.get("is_equivalent") is True else "不等价" if card.get("is_equivalent") is False else "需人工复核"
            conf = card.get("confidence")
            suffix = f"　confidence={conf}" if conf is not None else ""
            st.caption(f"你的答案：{card.get('student_answer')}　比对结果：{verdict}{suffix}")
    elif q_type == "证明题":
        st.info(card.get("proof_status") or "证明过程如下")
    else:
        score = card.get("score")
        total = card.get("total_score")
        if score is not None and total:
            st.caption(f"本题得分：{score} / {total}")
    return True


def render_equation_group(block: dict) -> bool:
    items = [str(i).strip().replace("$$", "") for i in (block.get("items") or []) if str(i).strip()]
    if not items:
        return False
    layout = block.get("layout", "vertical")
    if layout == "inline_pair":
        st.latex(r"\qquad ".join(items))
        return True
    rows = []
    for item in items:
        if "&" in item or "=" not in item:
            rows.append(item)
        else:
            lhs, rhs = item.split("=", 1)
            rows.append(f"{lhs.strip()} &= {rhs.strip()}")
    st.latex("\\begin{aligned}\n" + r"\\".join(rows) + "\n\\end{aligned}")
    return True


def render_derivation_chain(block: dict) -> bool:
    items = [str(i).strip().replace("$$", "") for i in (block.get("items") or []) if str(i).strip()]
    if not items:
        return False
    rows = []
    for idx, item in enumerate(items):
        rows.append(item if idx == 0 or "&" in item else f"&= {item}")
    st.latex("\\begin{aligned}\n" + r"\\".join(rows) + "\n\\end{aligned}")
    return True


def _case_condition(text: str) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    if any("\u4e00" <= ch <= "\u9fff" for ch in s):
        return r"\text{" + s.replace("{", "").replace("}", "") + "}"
    return s


def render_cases_block(block: dict) -> bool:
    rows = []
    for row in block.get("rows") or []:
        if isinstance(row, dict):
            expr = str(row.get("expr") or row.get("value") or "").strip()
            cond = _case_condition(row.get("condition") or "")
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            expr, cond = str(row[0]).strip(), _case_condition(str(row[1]))
        else:
            continue
        if expr:
            rows.append(f"{expr} & {cond}" if cond else expr)
    if rows:
        lhs = str(block.get("lhs") or "").strip()
        prefix = f"{lhs}=" if lhs else ""
        st.latex(prefix + "\\begin{cases}\n" + r"\\".join(rows) + "\n\\end{cases}")
        return True
    return False


def _render_degraded_block(block: dict, exc: Exception | None = None) -> bool:
    block = block or {}
    btype = str(block.get("type") or "text")
    if btype == "text":
        text = str(block.get("content") or "").replace("\\n", "\n")
        if _has_raw_latex_fragment(text):
            render_math_text(text)
        else:
            st.markdown(text)
        return bool(text.strip())
    if btype == "latex_display":
        st.warning("公式渲染失败，原始公式：")
        st.code(str(block.get("content") or ""), language="latex")
        return True
    if btype == "equation_group":
        st.warning("公式组渲染失败，原始公式组：")
        for item in block.get("items") or []:
            st.code(str(item), language="latex")
        return True
    if btype == "derivation_chain":
        st.warning("推导链渲染失败，原始推导链：")
        for item in block.get("items") or []:
            st.code(str(item), language="latex")
        return True
    if btype == "cases":
        st.warning("分段公式渲染失败，原始分段结构：")
        if block.get("lhs"):
            st.code(str(block.get("lhs")), language="latex")
        for row in block.get("rows") or []:
            if isinstance(row, dict):
                st.code(f"{row.get('expr') or row.get('value') or ''} | {row.get('condition') or ''}", language="latex")
            else:
                st.code(str(row), language="latex")
        return True
    st.code(_safe_json(block))
    return True


def render_solution_block(block: dict, *, best_effort: bool = True) -> bool:
    try:
        return _render_solution_block_strict(block)
    except Exception as exc:
        if best_effort:
            logger.warning("standard_solution block render degraded: %s", exc)
            return _render_degraded_block(block, exc)
        raise


def _render_solution_block_strict(block: dict) -> bool:
    btype = str((block or {}).get("type") or "text")
    if btype == "text":
        content = str(block.get("content") or "")
        if r"\begin{" in content:
            if _should_show_solution_debug():
                st.caption("文本块包含未结构化公式，已隐藏。")
            raise ValueError("raw latex environment in text block")
        return render_math_text(content)
    elif btype == "latex_display":
        from services.grading_adapter import _finalize_display_latex, _has_cjk, _latex_display_blocks_without_cjk

        raw = str(block.get("content") or "").replace("$$", "").strip()
        if raw and _has_cjk(raw):
            parts = _latex_display_blocks_without_cjk([{"type": "latex_display", "content": raw}])
            if len(parts) != 1 or parts[0].get("type") != "latex_display":
                return any(_render_solution_block_strict(part) for part in parts if isinstance(part, dict))
        content = _finalize_display_latex(raw)
        if content:
            st.markdown('<div class="grading-math-scroll">', unsafe_allow_html=True)
            try:
                from renderers.math_render_policy import render_grading_latex
                render_grading_latex(f"$$\n{content}\n$$")
            finally:
                st.markdown('</div>', unsafe_allow_html=True)
            return True
    elif btype == "equation_group":
        return render_equation_group(block)
    elif btype == "derivation_chain":
        return render_derivation_chain(block)
    elif btype == "cases":
        return render_cases_block(block)
    return False


def _render_derivation_meta(section: dict) -> bool:
    """Render derivation goal/reason on separate lines (title already shown separately)."""
    from services.grading_adapter import _goal_redundant_with_title, _strip_step_title_prefix

    rendered = False
    goal = _strip_step_title_prefix(str(section.get("goal") or "").strip())
    reason = str(section.get("reason") or "").strip()
    if goal and not _goal_redundant_with_title(goal, str(section.get("title") or "")):
        st.markdown("**推导目标**")
        rendered |= render_math_text(goal)
    if reason:
        st.markdown("**推导理由**")
        rendered |= render_math_text(reason)
    return rendered


def _render_degraded_section(section: dict, exc: Exception | None = None) -> bool:
    section = section or {}
    title = section.get("title") or "解答"
    st.markdown(f"**{_format_solution_title(title)}**")
    if section.get("kind"):
        st.caption(f"kind: {section.get('kind')}")
    st.warning("本部分部分内容渲染异常，以下为 AI 生成的原始步骤内容：")
    _render_derivation_meta(section)
    for block in section.get("blocks") or []:
        _render_degraded_block(block, exc)
    return True


def render_solution_section(section: dict, *, best_effort: bool = True) -> bool:
    rendered_any = False
    with st.container(border=True):
        title = section.get("title") or "解答"
        st.markdown(f"**{_format_solution_title(title)}**")
        rendered_any |= _render_derivation_meta(section)
        for block in section.get("blocks") or []:
            try:
                rendered_any |= render_solution_block(block, best_effort=best_effort)
            except Exception as exc:
                if best_effort:
                    rendered_any |= _render_degraded_block(block, exc)
                else:
                    raise
    return rendered_any or bool(section.get("title"))


def _render_degraded_final_answer(final_answer, exc: Exception | None = None) -> bool:
    if not final_answer:
        return False
    st.markdown("**最终结论**")
    if isinstance(final_answer, str):
        render_math_text(final_answer)
    elif isinstance(final_answer, dict):
        content = final_answer.get("content") or final_answer.get("value")
        if final_answer.get("type"):
            st.caption(f"type: {final_answer.get('type')}")
        if content:
            render_math_text(str(content))
        else:
            st.code(_safe_json(final_answer))
    else:
        st.code(_safe_json(final_answer))
    return True


def render_final_answer(final_answer: dict, *, best_effort: bool = True) -> bool:
    if not isinstance(final_answer, dict) or not final_answer.get("content"):
        return False
    with st.container(border=True):
        st.markdown("**最终结论**")
        return render_solution_block(final_answer, best_effort=best_effort)


def render_standard_solution_view(view: dict, *, best_effort: bool = True) -> bool:
    """Render a normalized standard solution view without parsing business logic."""
    rendered_any = False
    try:
        rendered_any |= _render_answer_card(view, best_effort=best_effort)
    except Exception as exc:
        if best_effort:
            rendered_any |= _render_degraded_answer_card((view or {}).get("answer_card"), exc)
        else:
            raise
    for section in view.get("sections") or []:
        try:
            rendered_any |= render_solution_section(section, best_effort=best_effort)
        except Exception as exc:
            if best_effort:
                with st.container(border=True):
                    rendered_any |= _render_degraded_section(section, exc)
            else:
                raise
    skip_final = (
        view.get("question_type") == "填空题"
        and bool((view.get("answer_card") or {}).get("correct_answer"))
    )
    if not skip_final:
        try:
            rendered_any |= render_final_answer(view.get("final_answer") or {}, best_effort=best_effort)
        except Exception as exc:
            if best_effort:
                with st.container(border=True):
                    rendered_any |= _render_degraded_final_answer(view.get("final_answer"), exc)
            else:
                raise
    return rendered_any


def _standard_solution_pending(
    solution: dict,
    grading_result: dict | None = None,
) -> bool:
    gr = grading_result or {}
    status = (
        solution.get("standard_solution_status")
        or gr.get("standard_solution_status")
        or st.session_state.get("_solution_status")
        or ""
    )
    if status == "pending":
        return True
    if status == "failed":
        return False
    try:
        from services.grading_adapter import is_choice_solution_stub
        if is_choice_solution_stub(solution, gr) and st.session_state.get("_solution_status") == "pending":
            return True
    except Exception:
        pass
    return False


def render_standard_solution(solution: dict, expanded: bool = False,
                             grading_result: dict | None = None) -> None:
    """Standard solution card — collapsed by default. Pass expanded=True to show open."""
    if _standard_solution_pending(solution, grading_result):
        with st.expander("📖 查看标准解法", expanded=True):
            st.markdown('<div class="standard-solution-card">', unsafe_allow_html=True)
            st.info("⏳ 正在生成带步骤的详细解析，请稍候…")
            st.caption("批改结果已就绪；完整解题过程生成后会自动刷新本页。")
            st.markdown('</div>', unsafe_allow_html=True)
        return

    steps = solution.get("steps") or []
    answer = solution.get("standard_answer", "")

    # Check structured data first (may have content even when legacy steps/answer are empty).
    # Prefer the current solution payload over session state to avoid rendering stale answers
    # after a new grading run.
    structured = solution.get("_structured") or st.session_state.get("standard_answer_structured")

    gr_answer = ""
    if isinstance(grading_result, dict):
        gr_answer = str(grading_result.get("correct_option") or grading_result.get("correct_answer") or "")

    if not steps and not answer and not gr_answer:
        if isinstance(structured, dict) and structured.get("steps"):
            pass  # Has structured data, proceed to rendering
        else:
            gr = grading_result if isinstance(grading_result, dict) else {}
            status = str(solution.get("standard_solution_status") or gr.get("standard_solution_status") or "")
            if status in {"failed", "incomplete"}:
                err = str(solution.get("standard_solution_error") or gr.get("standard_solution_error") or "")
                with st.expander("📖 查看标准解法", expanded=expanded):
                    if status == "incomplete":
                        st.warning("标准解答生成不完整，请重新生成标准解答。")
                    else:
                        st.warning("标准解答生成失败，请重新生成。")
                    if err:
                        st.caption(f"原因: {err[:150]}")
                return
            if status == "missing":
                with st.expander("📖 查看标准解法", expanded=expanded):
                    st.info("标准解答尚未生成，请重新生成标准解答。")
                return
            # Truly no content available
            with st.expander("📖 查看标准解法", expanded=expanded):
                st.info("暂无标准解法数据")
            return

    with st.expander("📖 查看标准解法", expanded=expanded):
        st.markdown('<div class="standard-solution-card">', unsafe_allow_html=True)
        rendered_any = False
        try:
            from services.grading_adapter import build_answer_only_view, build_standard_solution_view
            q_type = _view_question_type(solution, grading_result)
            view = build_standard_solution_view(solution, q_type, grading_result)
            rendered_any = render_standard_solution_view(view, best_effort=True)
        except Exception:
            logger.exception("standard_solution_view build/render failed; trying answer-only view")
            try:
                q_type = _view_question_type(solution, grading_result)
                fallback_view = build_answer_only_view(solution, q_type, grading_result)
                rendered_any = render_standard_solution_view(fallback_view, best_effort=True)
            except Exception:
                logger.exception("answer-only standard_solution_view failed")
        if not rendered_any:
            gr = grading_result if isinstance(grading_result, dict) else {}
            status = str(solution.get("standard_solution_status") or gr.get("standard_solution_status") or "")
            err = str(solution.get("standard_solution_error") or gr.get("standard_solution_error") or "")
            if status == "incomplete":
                st.warning("标准解答生成不完整，请重新生成标准解答。")
                if err:
                    st.caption(f"原因: {err[:150]}")
            elif status == "failed":
                st.warning("标准解答生成失败，请重新生成。")
                if err:
                    st.caption(f"原因: {err[:150]}")
            elif status == "missing":
                st.info("标准解答尚未生成，请重新生成标准解答。")
            else:
                st.info("暂无标准解法数据")
        st.markdown('</div>', unsafe_allow_html=True)


def render_recommendations(dr: dict, question_db=None, current_question=None, is_correct: bool = None) -> list[dict]:
    """Learning recommendations card — always shown, tailored to performance."""
    events: list[dict] = []
    weak_points = dr.get("weak_points", [])

    with st.container(border=True):
        st.markdown('<div class="grading-card">', unsafe_allow_html=True)
        st.markdown("**📖 巩固建议**")

        if is_correct is True:
            st.success("👍 这道题回答正确！继续保持，建议练习同类变式题巩固。")
        elif is_correct is False:
            st.info("📝 这道题还有提升空间，重点关注下方薄弱知识点。")
        else:
            st.info("💡 无论对错，持续练习同类题目都能帮助你巩固知识。")

        if weak_points:
            st.markdown("**薄弱知识点**：")
            tags = " · ".join(
                f"**{wp}**" for wp in weak_points[:5]
            )
            st.markdown(tags)
            recs = [
                f"重点复习 **{wp}** 相关知识点" for wp in weak_points[:3]
            ]
            for i, rec in enumerate(recs, 1):
                st.markdown(f"{i}. {rec}")
        elif is_correct is True:
            # Correct but still suggest related practice
            knowledge_points = (current_question or {}).get("knowledge_points", [])
            if knowledge_points:
                st.markdown(f"已掌握：{' · '.join(knowledge_points[:5])}")
            st.markdown("建议做同类变式题检验是否真正理解。")

        # 相似题目推荐
        if question_db and current_question:
            try:
                from similar_question_recommender import recommend_similar
                similar_questions = recommend_similar(
                    question=current_question,
                    diagnosis=dr,
                    question_db=question_db,
                    top_k=3
                )
                
                if similar_questions:
                    st.markdown("")
                    st.markdown("**🎯 同类练习推荐**")
                    cols = st.columns(min(3, len(similar_questions)))
                    for i, q in enumerate(similar_questions):
                        with cols[i]:
                            qid = q.get("question_id", "")
                            qtype = q.get("question_type", "")
                            year = q.get("year", "")
                            if st.button(
                                f"📝 {qid}",
                                key=f"similar_q_{qid}",
                                width="stretch",
                                help=f"{year}年 {qtype}"
                            ):
                                events.append({
                                    "type": "open_practice_question",
                                    "question": q,
                                })
                else:
                    st.markdown("")
                    st.markdown("**🎯 同类练习推荐**")
                    st.info("暂无相似题目推荐")
            except Exception as e:
                # 如果推荐功能不可用，显示原有提示
                st.markdown("")
                st.markdown("**🎯 同类练习推荐**")
                st.caption("建议在错题本中查看同类题目进行针对性练习")
        else:
            st.markdown("")
            st.markdown("**🎯 同类练习推荐**")
            st.caption("建议在错题本中查看同类题目进行针对性练习")
        st.markdown('</div>', unsafe_allow_html=True)
    return events


def render_grading_result_cards(gr: dict, sa: dict, dr: dict, total_score: int = 10,
                                 knowledge_points: list = None, question: dict = None,
                                 question_db=None, solution_expanded: bool = False) -> list[dict]:
    """Progressive disclosure layout.

    P22: view_only mode skips score, diagnosis, knowledge points, and recommendations,
    showing only the standard solution.
    """
    events: list[dict] = []
    is_view_only = bool(gr.get("view_only") or gr.get("hide_score_card"))

    # P40: inject mobile CSS and wrap in container
    inject_grading_mobile_css()
    st.markdown('<div class="grading-result-container">', unsafe_allow_html=True)

    if is_view_only:
        render_standard_solution(sa, expanded=True, grading_result=gr)
        st.markdown('</div>', unsafe_allow_html=True)
        return events

    st.markdown("---")

    # ═══ Always visible: Score ═══
    render_score_card(gr, total_score)

    # ═══ Verification report — always visible when triggered ═══
    _verification = gr.get("_verification")
    if _verification:
        try:
            from agents.verifier_agent import VerificationReport, ObligationIssue, ConditionIssue, DerivationIssue
            report = VerificationReport(
                passed=_verification.get("passed", True),
                obligation_issues=[ObligationIssue(**o) for o in _verification.get("obligation_issues", [])],
                condition_issues=[ConditionIssue(**c) for c in _verification.get("condition_issues", [])],
                derivation_issues=[DerivationIssue(**d) for d in _verification.get("derivation_issues", [])],
                summary=_verification.get("summary", ""),
            )
            from agents.verifier_agent import render_verification_report
            render_verification_report(report)
        except Exception:
            _obl_warn = gr.get("_obligation_warning", "")
            if _obl_warn:
                st.warning(_obl_warn)

    # ═══ Diagnosis — skipped when hide_diagnosis ═══
    if not gr.get("hide_diagnosis") and dr:
        render_diagnosis_card(dr, gr)

    # ═══ Collapsed: Step details ═══
    if gr.get("step_analysis"):
        with st.expander("📊 步骤对比分析", expanded=False):
            _render_step_comparison_body(gr)

    # ═══ Collapsed / Expanded: Standard solution ═══
    render_standard_solution(sa, expanded=solution_expanded, grading_result=gr)

    # ═══ Knowledge Points — below Standard Solution, always visible ═══
    kp_list = knowledge_points or (question.get("knowledge_points", []) if question else [])
    render_knowledge_points(kp_list, question, question_db)

    # ═══ Recommendations — skipped when view_only ═══
    if not is_view_only:
        with st.expander("📖 巩固建议", expanded=True):
            events.extend(render_recommendations(
                dr, question_db, question,
                is_correct=(gr.get("total", 0) >= total_score * 0.9),
            ))
    st.markdown('</div>', unsafe_allow_html=True)
    return events


def _render_step_comparison_body(gr: dict) -> None:
    """Step comparison body — renders each step with proper text/latex separation."""
    steps = gr.get("step_analysis") or []
    if not steps:
        return

    st.markdown('<div class="grading-card">', unsafe_allow_html=True)

    h1, h2, h3 = st.columns([1, 0.15, 1])
    with h1:
        st.caption("📝 你的作答")
    with h2:
        st.markdown("")
    with h3:
        st.caption("📋 标准步骤")

    for s in steps:
        num = s.get("num", "?")
        content = s.get("content", "")
        judgment = s.get("judgment", "")
        score_str = s.get("score", "")
        comment = s.get("comment", "")

        if judgment == "正确":
            icon = "✅"
        elif "缺失" in str(judgment) or "错误" in str(judgment):
            icon = "❌"
        else:
            icon = "⚠️"

        student_desc = comment if comment else judgment

        c1, c2, c3 = st.columns([1, 0.15, 1])
        with c1:
            _render_text_or_latex(student_desc)
        with c2:
            st.markdown(f"<div style='text-align:center;font-size:1.2em;'>{icon}</div>", unsafe_allow_html=True)
        with c3:
            st.caption(f"步骤{num}")
            _render_text_or_latex(content)
        st.caption(f"得分: {score_str}分")
        if s != steps[-1]:
            st.markdown("---")
    st.markdown('</div>', unsafe_allow_html=True)


def _validate_and_repair_latex_block(content: str, block_type: str = "latex_display") -> str | None:
    """P41: Validate and repair a latex block before rendering.

    Returns repaired content if fixable, None if unrepairable (caller should
    show safe fallback).
    """
    from services.solution_quality import (
        detect_broken_derivation_formula_block, detect_broken_latex_environment,
        detect_broken_cases_environment, detect_probability_formula_fragment_leak,
    )
    s = str(content or "").strip()
    if not s:
        return s

    issues = detect_broken_derivation_formula_block(s)
    env_issues = detect_broken_latex_environment(s)
    cases_issues = detect_broken_cases_environment(s)
    prob_issues = detect_probability_formula_fragment_leak(s)
    all_issues = issues + env_issues + cases_issues + prob_issues

    if not all_issues:
        return s  # clean

    # Try auto-repair
    try:
        from latex_utils import (
            normalize_derivation_formula_block, repair_aligned_environment,
            repair_cases_environment, repair_latex_row_spacing_markers,
            repair_bare_fraction_commands, repair_probability_formula_fragments,
        )
        repaired = repair_bare_fraction_commands(s)
        repaired = repair_probability_formula_fragments(repaired)
        repaired = repair_latex_row_spacing_markers(repaired)
        if r'\begin{cases}' in repaired:
            repaired = repair_cases_environment(repaired)
        repaired = repair_aligned_environment(repaired)
        repaired = normalize_derivation_formula_block(repaired)
        remaining = detect_broken_derivation_formula_block(repaired)
        remaining_env = detect_broken_latex_environment(repaired)
        remaining_cases = detect_broken_cases_environment(repaired)
        remaining_prob = detect_probability_formula_fragment_leak(repaired)
        # If repair fixed all issues or only non-critical ones remain
        critical = {
            "detached_substitution_annotation", "text_inside_latex_display",
            "orphan_aligned_begin", "orphan_aligned_end",
            "orphan_display_delimiter_in_cases",
        }
        if not (set(remaining + remaining_env + remaining_cases + remaining_prob) & critical):
            return repaired
    except Exception:
        pass

    # Unrepairable — check admin mode for debug display
    if _is_admin_user():
        # Admin sees the raw broken content in debug
        return s
    return None  # signal to show safe fallback


def _render_text_or_latex(text: str) -> None:
    """Render content with proper text/latex block separation.

    If content contains LaTeX commands → split and render block by block.
    If content is plain text → render as markdown.
    P41.2: If content contains raw aligned environments, split them out
    as latex_display blocks to prevent raw LaTeX leakage.
    """
    if not text:
        return
    s = str(text)

    # P41.2: Check for raw aligned environments in text content
    if r'\begin{aligned}' in s or r'\begin{align}' in s or r'\begin{cases}' in s:
        try:
            from latex_utils import split_text_and_latex_mixed_block, render_structured_safe
            blocks = split_text_and_latex_mixed_block(s)
            if len(blocks) > 1:
                structured = {"steps": [{"label": "", "blocks": blocks}]}
                render_structured_safe(structured)
                return
        except Exception:
            pass
        # If split fails, show safe fallback instead of raw
        if not _is_admin_user():
            st.warning("该公式格式异常，无法正常显示。")
            return

    try:
        from latex_utils import split_latex_text, render_ast
        try:
            from services.grading_adapter import prepare_grading_math_for_render
            s = prepare_grading_math_for_render(s)
        except Exception:
            pass
        segments = split_latex_text(s)
        if len(segments) == 1 and segments[0].get("type") == "text":
            st.markdown(segments[0]["content"])
        else:
            st.markdown('<div class="grading-math-scroll">', unsafe_allow_html=True)
            render_ast(segments)
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception:
        st.markdown(s)


def render_summary_header(gr: dict, dr: dict, total_score: int = 10) -> None:
    """P16: Report-style summary — score, main issue, recommendation."""
    import html as _html
    score = gr.get("total", 0)
    ratio = score / total_score if total_score > 0 else 0
    engine = gr.get("engine", "")

    if engine == "view_only":
        return

    if ratio >= 0.9:
        grade, color = "优秀", "#16a34a"
    elif ratio >= 0.6:
        grade, color = "良好", "#f59e0b"
    else:
        grade, color = "需加强", "#dc2626"

    root_cause = dr.get("root_cause", "") or dr.get("error_type", "")
    weak_points = dr.get("weak_points", [])[:3]
    recs = dr.get("recommendations", [])[:2]

    st.markdown(
        f"""<div class="app-card" style="background:{color}08;border-color:{color}30;">
            <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">📋 批改报告</div>
            <div style="margin-top:4px;color:#475569;font-size:0.92rem;">
                本题得分 <b style="color:{color};">{score}/{total_score}</b> · {grade}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    if root_cause:
        st.markdown(
            f'<div class="app-card-compact" style="border-left:4px solid {color};">'
            f'<b>主要问题：</b>{_html.escape(root_cause[:100])}</div>',
            unsafe_allow_html=True,
        )

    if weak_points:
        kp_tags = " ".join(
            f'<span class="app-chip app-chip-orange">{_html.escape(str(kp))}</span>'
            for kp in weak_points
        )
        st.markdown(f"**薄弱知识点** {kp_tags}", unsafe_allow_html=True)

    if recs:
        for rec in recs:
            st.caption(f"💡 {rec}")
