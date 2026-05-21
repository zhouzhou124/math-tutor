"""pages/grading_page.py — AI 批改"""
import time
import json
import threading
import traceback
import streamlit as st
import logging
from concurrent.futures import ThreadPoolExecutor
from config import LLM_BASE_URL, LLM_MODEL
from agents import GradingAgent, DiagnosisAgent, SolverAgent
from renderers.components.grading_result import render_grading_result_cards
from ._shared import get_client
from storage.grading_task_store import (
    create_task, complete_task, fail_task, get_task,
    get_recent_task, mark_viewed, cleanup_old,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#  Helpers for thread-safe state access
# ═══════════════════════════════════════════════

def _ss_get(key, default=None, *, _state=None):
    """Read from _state dict (bg thread) or st.session_state (main thread)."""
    if _state is not None:
        return _state.get(key, default)
    return st.session_state.get(key, default)


def _ss_set(key, value, *, _state=None):
    """Write to _state dict (bg thread) or st.session_state (main thread)."""
    if _state is not None:
        _state[key] = value
    else:
        st.session_state[key] = value


def _clear_grading_state():
    """清理所有批改相关的状态，用于重新开始批改时确保干净的状态"""
    keys_to_clear = [
        'grading_result',
        'diagnosis_result',
        'standard_answer',
        'standard_answer_structured',
        'answer_view_mode',
        'grading_triggered',
        '_poll_start',
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def _standard_answer_needs_expansion(answer: str, steps: list, q_type: str) -> bool:
    """Return True when a cached answer is too thin for LLM grading/rendering.

    An answer is "good enough" (returns False) when it already contains
    explicit step markers (步骤N：), OR is sufficiently long (previously
    AI-expanded).  Short placeholder answers always need expansion.
    """
    if steps:
        return False

    text = (answer or "").strip()
    if not text:
        return True

    placeholders = ("证明略", "略", "解析略", "过程略", "答案略", "方法略")
    if any(p in text for p in placeholders):
        return True

    # Already has detailed step markers → cache is good enough
    import re
    if re.search(r'步骤\s*\d+\s*[：:]', text):
        return False

    # Short answer for MC / fill-in-the-blank → needs expansion
    if q_type in ("选择题", "填空题") and len(text) < 80:
        return True

    # Short answer for proof / free-response → needs expansion
    return len(text) < 120


def _solution_to_text(solution: dict) -> str:
    """Build a complete plain/markdown representation from all solution fields."""
    if not solution:
        return ""

    parts = []
    steps = solution.get("steps") or []
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            label = step.get("label") or f"步骤{i + 1}"
            block_parts = []
            if step.get("content"):
                block_parts.append(str(step["content"]))
            for block in step.get("blocks") or []:
                content = block.get("content", "")
                if not content:
                    continue
                if block.get("type") == "latex":
                    block_parts.append(f"$${content}$$" if block.get("display") == "block" else f"${content}$")
                else:
                    block_parts.append(str(content))
            if block_parts:
                parts.append(f"### {label}\n" + "\n".join(block_parts))
        elif isinstance(step, str) and step.strip():
            parts.append(f"### 步骤{i + 1}\n{step.strip()}")

    structured = solution.get("_structured") or {}
    if not parts and isinstance(structured, dict):
        for i, step in enumerate(structured.get("steps", [])):
            label = step.get("label") or f"步骤{i + 1}"
            block_parts = []
            for block in step.get("blocks") or []:
                content = block.get("content", "")
                if not content:
                    continue
                if block.get("type") == "latex":
                    block_parts.append(f"$${content}$$" if block.get("display") == "block" else f"${content}$")
                else:
                    block_parts.append(str(content))
            if block_parts:
                parts.append(f"### {label}\n" + "\n".join(block_parts))

    answer = (solution.get("standard_answer") or "").strip()
    final_answer = ""
    if isinstance(structured, dict):
        fa = structured.get("final_answer") or {}
        if isinstance(fa, dict):
            final_answer = (fa.get("content") or "").strip()

    final = final_answer or answer
    if final:
        parts.append(f"### 最终答案\n{final}")

    return "\n\n".join(parts).strip()


def _cache_detailed_answer(selected_q: dict, expanded: str):
    """将 AI 生成的详细解答缓存到题目 JSON 文件，下次批改同一题直接命中。"""
    if not selected_q or not expanded:
        return
    qid = selected_q.get("question_id", "")
    if not qid:
        return
    try:
        from database.question_db import get_question_path
        path = get_question_path(qid)
        if not path.exists():
            return
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["standard_answer"] = expanded
        data["solution_steps"] = []  # 详细解答已包含完整步骤
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 缓存失败不影响主流程


class _ThreadSafeStatus:
    """Wraps a Streamlit status object so writes work safely from background threads.
    In a thread, messages are buffered and replayed on the main thread via flush()."""

    def __init__(self, st_status=None):
        self._st_status = st_status
        self._buffer = []

    def write(self, msg: str):
        if self._st_status:
            try:
                self._st_status.write(msg)
            except Exception:
                self._buffer.append(msg)
        else:
            self._buffer.append(msg)

    def flush(self, to_status):
        """Replay buffered messages to a Streamlit status on the main thread."""
        for msg in self._buffer:
            try:
                to_status.write(msg)
            except Exception:
                pass
        self._buffer.clear()


class _NoOpStatus:
    """A status-like object that silently discards all writes.

    Used in background threads where no Streamlit script context exists.
    """
    def write(self, msg: str): pass
    def update(self, *, label=None, state=None, expanded=None): pass


class _NoOpContext:
    """A st-like object whose .status() returns a _NoOpStatus.

    Used as the *container* argument to _execute_grading_process when
    running in a background thread.
    """
    def status(self, label: str, expanded: bool = True) -> _NoOpStatus:
        return _NoOpStatus()


def _parse_steps_from_text(text: str) -> list:
    """从 AI 生成的详细解答文本中提取步骤列表。

    匹配 "步骤N：" 或 "步骤N: " 标记，返回 [{"label": "步骤1", "content": "..."}, ...]。
    用于在 from_legacy_text 解析失败时给旧版渲染路径提供兜底。
    """
    if not text:
        return []
    import re
    markers = list(re.finditer(r'步骤\s*(\d+)\s*[：:]\s*', text))
    if not markers:
        return []
    steps = []
    for i, m in enumerate(markers):
        step_num = int(m.group(1))
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()
        if content:
            steps.append({"label": f"步骤{step_num}", "content": content})
    return steps


def _build_standard_solution(question, ocr_data, selected_q, client, status,
                             force_expansion: bool = False, *, _state=None, model=None) -> dict:
    """获取/生成标准解答。空作答和正常批改共用同一逻辑。

    _state=None 时使用 st.session_state（主线程），传入 dict 时使用 dict（后台线程）。
    model 参数覆盖 _state 中的 model 配置。
    """
    cached_answer = selected_q.get("standard_answer", "")
    correct_option = selected_q.get("correct_option", "")
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
    opts = selected_q.get("options") or {}
    _model = model or _ss_get("model", LLM_MODEL, _state=_state)

    # 确定已知答案信息（用于 AI 生成详细解答时作为上下文）
    _known_answer = cached_answer or ""
    if q_type == "选择题" and correct_option:
        if correct_option in opts:
            _known_answer = f"正确选项: {correct_option}. {opts[correct_option]}"
        else:
            _known_answer = f"正确选项: {correct_option}"

    # 判断是否需要 AI 生成详细解答
    _needs_exp = _standard_answer_needs_expansion(
        _known_answer, selected_q.get("solution_steps", []) or [], q_type,
    ) or force_expansion

    # 路径1：缓存够详细 → 直接用
    if not _needs_exp and _known_answer and (len(_known_answer.strip()) > 1 or q_type == "选择题"):
        solution = {
            "success": True,
            "standard_answer": _known_answer,
            "total_score": selected_q.get("score", 10),
            "steps": selected_q.get("solution_steps", []) or [],
        }
        status.write("✓ 标准答案已加载（缓存）")

    # 路径2：有已知答案但太简短 → 直接用 generate_detailed_answer 生成详细版（1次LLM）
    elif _needs_exp and _known_answer and client is not None:
        status.write("⏳ AI 生成详细解答...")
        try:
            full_question_dict = dict(selected_q or {})
            full_question_dict.setdefault("question", question)
            if selected_q.get("options"):
                full_question_dict["question"] += "\n" + "\n".join(
                    f"({key}) {value}" for key, value in sorted(selected_q["options"].items())
                )
            from choice_explainer import generate_detailed_answer
            expanded = generate_detailed_answer(
                question=full_question_dict,
                known_answer=_known_answer,
                question_type=q_type or ocr_data.get("question_type", "解答题"),
                client=client, model=_model,
            )
            solution = {
                "success": True,
                "standard_answer": expanded if expanded else _known_answer,
                "total_score": selected_q.get("score", 10),
                "steps": [],
            }
            if expanded:
                # Only cache if the LLM actually produced new content (not
                # just regurgitating the short known_answer as a fallback).
                if expanded != _known_answer:
                    try:
                        from latex_utils import from_legacy_text
                        solution["_structured"] = from_legacy_text(expanded)
                    except Exception:
                        pass
                    _cache_detailed_answer(selected_q, expanded)
                else:
                    # LLM returned the known_answer → generation failed.
                    # Don't cache — next time will try again.
                    status.write("⚠️ AI 未生成新内容，将使用简略答案")
            status.write("✓ 详细解答已生成")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Detailed answer generation failed: %s", exc)
            solution = {
                "success": True,
                "standard_answer": _known_answer or "解答生成失败",
                "total_score": selected_q.get("score", 10), "steps": [],
            }

    # 路径3：无任何已知答案 → 直接使用 generate_detailed_answer 生成详细解答（1次LLM）
    elif client is not None:
        status.write("⏳ AI 生成详细解答...")
        full_question_dict = dict(selected_q or {})
        full_question_dict.setdefault("question", question)
        if selected_q.get("options"):
            full_question_dict["question"] += "\n" + "\n".join(
                f"({key}) {value}" for key, value in sorted(selected_q["options"].items())
            )
        try:
            from choice_explainer import generate_detailed_answer
            expanded = generate_detailed_answer(
                question=full_question_dict,
                known_answer="",
                question_type=q_type or ocr_data.get("question_type", "解答题"),
                client=client, model=_model,
            )
            solution = {
                "success": True,
                "standard_answer": expanded if expanded else "解答生成失败",
                "total_score": selected_q.get("score", 10),
                "steps": [],
            }
            if expanded:
                try:
                    from latex_utils import from_legacy_text
                    solution["_structured"] = from_legacy_text(expanded)
                except Exception:
                    pass
                _cache_detailed_answer(selected_q, expanded)
            status.write("✓ 详细解答已生成")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Detailed answer generation failed: %s", exc)
            # 降级到 SolverAgent
            full_question = question
            if selected_q.get("options"):
                for key in sorted(selected_q.get("options", {}).keys()):
                    full_question += f"\n({key}) {selected_q['options'][key]}"
            solver = SolverAgent(client, _model)
            solution = solver.solve(
                question=full_question,
                math_type=ocr_data.get("math_type", "数学一"),
                question_type=ocr_data.get("question_type", "解答题"),
                knowledge_point=ocr_data.get("knowledge_point", "未指定"),
            )
            status.write("✓ 标准解答已生成（AI求解）")

    # 路径4：无 API Key → 显示已有内容
    else:
        solution = {
            "success": True,
            "standard_answer": _known_answer or "暂无标准答案（请配置 API Key 以自动生成）",
            "total_score": selected_q.get("score", 10), "steps": [],
        }
        status.write("⚠️ 未配置 API Key，无法生成标准解答")

    # 规范化 LaTeX
    try:
        from latex_normalizer import normalize_latex_style
        solution["standard_answer"] = normalize_latex_style(solution.get("standard_answer", ""))
        steps = solution.get("steps", [])
        if steps:
            normalized_steps = []
            for s in steps:
                if isinstance(s, dict):
                    if s.get("content"):
                        s["content"] = normalize_latex_style(s.get("content", ""))
                    for b in s.get("blocks") or []:
                        if isinstance(b, dict) and b.get("type") == "latex":
                            b["content"] = normalize_latex_style(b.get("content", ""))
                elif isinstance(s, str):
                    s = normalize_latex_style(s)
                normalized_steps.append(s)
            solution["steps"] = normalized_steps
    except Exception:
        pass

    _ss_set("standard_answer", solution, _state=_state)
    # 构建 _structured（如果还没有）
    if solution.get("_structured"):
        _ss_set("standard_answer_structured", solution["_structured"], _state=_state)
    else:
        try:
            from latex_utils import from_legacy_text
            raw = _solution_to_text(solution)
            if raw:
                _ss_set("standard_answer_structured", from_legacy_text(raw), _state=_state)
                solution["_structured"] = _ss_get("standard_answer_structured", _state=_state)
        except Exception:
            _ss_set("standard_answer_structured", None, _state=_state)

    return solution


def _execute_grading_process(question, student_ans, ocr_data, selected_q, container=None,
                             *, _state=None, model=None, user_id=None, memory=None,
                             client=None):
    """执行批改流程。

    Args:
        _state: None=使用 st.session_state（主线程），dict=使用 dict（后台线程）
        model: LLM model 名称
        user_id: 用户ID（用于错题本）
        memory: MemoryService 实例（用于错题本）
        client: LLM client（None 则从 _state 获取 API key 自行创建）

    Returns:
        dict: results with keys grading_result, diagnosis_result, standard_answer,
              standard_answer_structured, error_record (for saving to error notebook).
              返回 None 表示前置条件不满足（如无 API key）。
    """
    ctx = container if container is not None else _NoOpContext()
    _model = model or _ss_get("model", LLM_MODEL, _state=_state)
    _user_id = user_id or (_ss_get("auth", {}, _state=_state).get("user_id", ""))
    _memory = memory or _ss_get("memory", _state=_state)

    # 获取或创建 LLM client
    if client is None:
        if _state is not None:
            # 后台线程：从 _state 获取配置自行创建
            api_key = str(_state.get("api_key", "") or "")
            if api_key:
                from llm_client import create_client
                base_url = str(_state.get("base_url", LLM_BASE_URL) or "")
                protocol = str(_state.get("protocol", "openai") or "openai")
                client = create_client(api_key=api_key, base_url=base_url, protocol=protocol)
        else:
            client = get_client()

    # ── 空作答快速通道：只展示标准答案，不进行AI批改和诊断 ──
    if not (student_ans or "").strip():
        status = ctx.status("📖 查看标准答案...", expanded=True)
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status,
                                             force_expansion=True, _state=_state, model=_model)
        if solution is None:
            _ss_set("grading_triggered", False, _state=_state)
            return None

        _ss_set("standard_answer", solution, _state=_state)
        gresult = {
            "success": True, "total": 0, "step_score": 0, "result_score": 0,
            "step_analysis": [], "deductions": [],
            "comment": "未作答，仅查看标准答案",
            "engine": "view_only",
        }
        _q_kps = (selected_q or {}).get("knowledge_points", []) or []
        if not _q_kps:
            _ocr_kp = ocr_data.get("knowledge_point", "") if ocr_data else ""
            _q_kps = [_ocr_kp] if _ocr_kp and _ocr_kp != "未指定" else []
        _q_mistakes = (selected_q or {}).get("common_mistakes", []) or []
        if _q_mistakes and selected_q:
            selected_q["common_mistakes"] = selected_q.get("common_mistakes") or _q_mistakes
        dresult = {
            "error_type": "未作答",
            "root_cause": "学生未输入任何作答内容，建议先尝试独立解题再看答案",
            "is_repeat": False, "repeat_count": 0, "affects_future": False,
            "weak_points": _q_kps[:5],
            "common_mistakes": _q_mistakes[:4],
            "recommendations": [
                "先独立尝试解答，再对照标准答案检查思路",
                f"重点掌握【{'、'.join(_q_kps[:3])}】相关知识点" if _q_kps else "可在错题本中回顾同类题",
                "可对照标准答案逐步骤检查自己的思路差异",
            ],
        }
        _ss_set("grading_result", gresult, _state=_state)
        _ss_set("diagnosis_result", dresult, _state=_state)
        status.write("✓ 完成")
        _ss_set("answer_view_mode", True, _state=_state)
        _ss_set("grading_triggered", False, _state=_state)
        status.update(label="✅ 查看答案完成", state="complete", expanded=False)
        return {
            "grading_result": gresult,
            "diagnosis_result": dresult,
            "standard_answer": solution,
            "standard_answer_structured": _ss_get("standard_answer_structured", _state=_state),
            "error_record": None,
        }

    # client 已在函数开头获取，此处检查是否可用
    if client is None:
        if _state is not None:
            # 后台线程：标记失败
            return None  # caller will handle
        st.warning("请先在「系统设置」中配置 API Key")
        _ss_set("grading_triggered", False, _state=_state)
        return None

    _t_start = time.time()
    status = ctx.status("🔍 正在准备批改...", expanded=True)
    status.write("⏳ 获取标准答案...")
    selected_q = selected_q or _ss_get("selected_question", _state=_state) or {}
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))

    # 解答题/证明题：标准答案生成 与 lock_question 可并行
    is_complex = q_type in ("解答题", "证明题")
    solution = None
    _future_solution = None
    _ts_status = None

    if is_complex and selected_q.get("question_id"):
        _ts_status = _ThreadSafeStatus()
        _executor = ThreadPoolExecutor(max_workers=1)
        _future_solution = _executor.submit(
            _build_standard_solution, question, ocr_data, selected_q, client, _ts_status,
            force_expansion=False, _state=_state, model=_model,
        )
        status.write("⏳ 标准答案与规范解并行生成中...")
    else:
        # 选择题和填空题也需要详细解答，方便用户查看标准解法
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status,
                                            force_expansion=True, _state=_state, model=_model)
        if solution is None:
            _ss_set("grading_triggered", False, _state=_state)
            return None

    # Step 2: 批改 — Engine A 快速路径(选择/填空) vs Engine B LLM路径(解答/证明)
    std_ans = ""
    total_score = 10
    is_fast_path = q_type in ("选择题", "填空题")

    if is_fast_path and not is_complex:
        if _future_solution:
            solution = _future_solution.result()
            _ts_status.flush(status)
        std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
        total_score = solution.get("total_score", 10)
        # Engine A: 规则引擎快速判分 (<100ms, 无LLM调用)
        import re
        stu = (student_ans or "").strip()
        correct_option = selected_q.get("correct_option", "")
        if q_type == "选择题" and correct_option:
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
            from symbolic_executor import quick_compare, ErrorLevel
            result = quick_compare(stu, std_ans)
            is_correct = result["equivalent"]
            score = total_score if is_correct else 0
            gresult = {
                "success": True, "total": score, "step_score": score, "result_score": 0,
                "step_analysis": [], "deductions": [],
                "comment": "正确" if is_correct else (
                    "计算错误" if result["error_level"] == ErrorLevel.LEVEL_1
                    else "答案错误，请查看标准解法"
                ),
            }
        if is_correct:
            dresult = {
                "error_type": "无错误", "root_cause": "",
                "is_repeat": False, "repeat_count": 0,
                "affects_future": False, "weak_points": [],
            }
        else:
            if q_type == "选择题":
                correct_opt = selected_q.get("correct_option", "")
                dresult = {
                    "error_type": "选择题答案错误",
                    "root_cause": f"正确答案是 {correct_opt}，你选择了 {student_ans[:10]}。请分析每个选项的数学含义。",
                    "is_repeat": False, "repeat_count": 0,
                    "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                }
            else:
                dresult = {
                    "error_type": "填空题错误",
                    "root_cause": "答案与标准答案不等价，请查看标准解法了解正确答案。",
                    "is_repeat": False, "repeat_count": 0,
                    "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                }
        status.write("✓ 快速批改完成（规则引擎）")
    else:
        # ── 解答题/证明题：lock_question + extract 与标准答案生成并行 ──
        status.write("⏳ 启动图对齐批改引擎...")
        engine_c_ok = False
        _canonical = None
        locked = None
        _trace_result = None
        if selected_q.get("question_id"):
            try:
                from question_locker import lock_question
                from graph_matching import grade_with_graph
                _qdb = _ss_get("question_db", _state=_state)
                locked = lock_question(selected_q, _qdb, client, _model)
                _canonical = locked.get("canonical_trace")

                from student_trace_extractor import extract_student_trace
                from symbolic_executor import build_student_graph_from_trace
                _trace_result = extract_student_trace(
                    student_ans or "", question, client, _model
                )
                student_graph = build_student_graph_from_trace(_trace_result)

                if _future_solution:
                    solution = _future_solution.result()
                    _ts_status.flush(status)
                    _executor.shutdown(wait=False)
                std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
                total_score = solution.get("total_score", 10)
                status.write("✓ 标准答案与规范解就绪")

                best_score = -1.0
                best_gresult = None
                best_method_name = ""
                method_count = 0

                if _canonical and _canonical.is_multimethod():
                    status.write(f"⏳ 多解法图对齐批改中（{_canonical.method_count()}种解法）...")
                else:
                    status.write("⏳ 图对齐批改中...")

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
                    if best_method_name and _canonical:
                        gresult["method_matched"] = best_method_name
                        for m in _canonical.methods:
                            if m.method_name == best_method_name:
                                m.usage_count += 1
                                break

                    if locked.get("standard_answer"):
                        solution["standard_answer"] = locked["standard_answer"]
                        std_ans = _solution_to_text(solution) or solution["standard_answer"]
                    engine_c_ok = True
                    status.write(f"✓ 图对齐批改完成（{method_count}法，最佳匹配: {best_method_name}）")
            except Exception as _e_c:
                logger.error(f"[Engine C 失败] {_e_c}")

        if _future_solution and solution is None:
            solution = _future_solution.result()
            _ts_status.flush(status)
            _executor.shutdown(wait=False)
            std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
            total_score = solution.get("total_score", 10)

        if not engine_c_ok:
            grading = GradingAgent(client, _model)
            gresult = grading.grade(
                question=question, standard_answer=std_ans,
                student_answer=student_ans, total_score=total_score,
                knowledge_points=ocr_data.get("knowledge_point", ""),
                difficulty=selected_q.get("difficulty", "中等"),
                canonical_trace=_canonical,
            )
            status.write("✓ LLM批改完成")

        # Step 3: 诊断（高正确率跳过LLM，直接用本地诊断，节省5-30秒）
        status.write("⏳ 正在诊断分析...")
        _score = gresult.get("total", 0)
        _max = solution.get("total_score", 10)
        _is_high_score = _max > 0 and _score / _max >= 0.9

        if _is_high_score:
            diagnosis = DiagnosisAgent(None, _model)
            history = []
            dresult = diagnosis._local_diagnose(gresult, history)
            status.write("✓ 诊断完成（高分快速通道）")
        else:
            diagnosis = DiagnosisAgent(client, _model)
            history = []
            if _memory and _user_id:
                try:
                    history = _memory.get_errors(
                        user_id=_user_id,
                        knowledge_point=ocr_data.get("knowledge_point", "")
                    )
                except Exception:
                    pass
            dresult = diagnosis.diagnose(
                question=question, student_answer=student_ans,
                standard_answer=std_ans, grading_result=gresult,
                error_history=history,
            )
            status.write("✓ 诊断完成")
    _ss_set("grading_result", gresult, _state=_state)
    _ss_set("diagnosis_result", dresult, _state=_state)
    status.write("⏳ 检查候选方法...")

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
                    status.write("✓ 候选方法已提交审核队列")
    except Exception as _evo_err:
        pass  # 非关键路径

    # Step 3.6: VerifierAgent — post-hoc reasoning quality check.
    #   SolverAgent → generates standard answer   (pure solve)
    #   VerifierAgent → checks bidirectional logic, missing conditions,
    #                    illegal derivations (pure verify)
    #   Renderer → displays results                (pure display)
    try:
        from agents.verifier_agent import VerifierAgent
        verifier = VerifierAgent()
        report = verifier.verify(
            reasoning_text=gresult.get("comment", ""),
            step_analysis=gresult.get("step_analysis", []),
            diagnosis_text=dresult.get("root_cause", ""),
        )
        if not report.passed:
            gresult["_verification"] = report.to_dict()
            gresult["_obligation_warning"] = report.summary
    except Exception:
        pass  # Verification is advisory; never block grading

    status.write("⏳ 保存到错题本...")

    # Step 4: 构建错题记录
    error_record = None
    if gresult.get("total", 0) < solution.get("total_score", 10) * 0.9:
        full_standard_answer = _solution_to_text(solution) or solution.get("standard_answer", "")

        # Prefer structured steps (blocks, LaTeX-aware) over simple steps (content, plain text).
        # 1) _structured from from_legacy_text (blocks format)
        # 2) standard_answer_structured from session state
        # 3) _parse_steps_from_text on the raw answer (simple content format, last resort)
        saved_steps = []
        structured = solution.get("_structured")
        if isinstance(structured, dict) and structured.get("steps"):
            saved_steps = structured["steps"]
        if not saved_steps:
            structured_from_state = _ss_get("standard_answer_structured", _state=_state)
            if isinstance(structured_from_state, dict) and structured_from_state.get("steps"):
                saved_steps = structured_from_state["steps"]
        if not saved_steps:
            raw_answer = solution.get("standard_answer", "")
            if raw_answer:
                saved_steps = _parse_steps_from_text(raw_answer)

        error_record = {
            "question_id": selected_q.get("question_id", ""),
            "question": question,
            "math_type": ocr_data.get("math_type", ""),
            "question_type": ocr_data.get("question_type", ""),
            "knowledge_point": ocr_data.get("knowledge_point", ""),
            "knowledge_points": selected_q.get("knowledge_points", []) or dresult.get("knowledge_points", []),
            "difficulty": selected_q.get("difficulty", "中等"),
            "student_answer": student_ans,
            "standard_answer": full_standard_answer,
            "solution_steps": saved_steps,
            "score": gresult.get("total", 0),
            "max_score": solution.get("total_score", 10),
            "is_correct": gresult.get("total", 0) >= solution.get("total_score", 10) * 0.9,
            "comment": gresult.get("comment", ""),
            "step_analysis": gresult.get("step_analysis", []),
            "method_matched": gresult.get("method_matched", ""),
            "engine": gresult.get("engine", gresult.get("_engine", "unknown")),
            "confidence": gresult.get("confidence", 0.0),
            "obligation_warning": gresult.get("_obligation_warning", ""),
            "error_type": dresult.get("error_type", ""),
            "root_cause": dresult.get("root_cause", ""),
            "weak_points": dresult.get("weak_points", []),
            "recommendations": dresult.get("recommendations", []),
            "common_mistakes": dresult.get("common_mistakes", []),
            "is_repeat_diagnosis": dresult.get("is_repeat", False),
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        }

        # Save to 错题本.  In the background thread (_state is not None) we
        # defer the actual save to _restore_results_to_session() on the main
        # thread, avoiding a duplicate when both paths write.
        if _memory and _user_id:
            if _state is None:
                # Main thread — save immediately
                try:
                    _memory.add_error_record(_user_id, error_record)
                except Exception:
                    pass
            # Background thread — error_record is returned in results;
            # _restore_results_to_session will save it.
        if _state is not None:
            _state["mistakes_force_reload"] = True
        else:
            st.session_state.mistakes_force_reload = True
        st.session_state["_invalidate_dashboard"] = True

    _elapsed = time.time() - _t_start
    status.write(f"✓ 批改完成！（总耗时 {_elapsed:.1f} 秒）")
    _ss_set("answer_view_mode", True, _state=_state)
    _ss_set("grading_triggered", False, _state=_state)
    status.update(label=f"✅ 批改完成（{_elapsed:.1f}s）", state="complete", expanded=False)

    return {
        "grading_result": gresult,
        "diagnosis_result": dresult,
        "standard_answer": solution,
        "standard_answer_structured": _ss_get("standard_answer_structured", _state=_state),
        "error_record": error_record,
    }


# ═══════════════════════════════════════════════
#  Background grading — runs grading in a daemon
#  thread so the user can leave the page and come
#  back later without losing results.
# ═══════════════════════════════════════════════

def _build_client_from_state(state: dict):
    """Create an LLM client from the flat config stored in *state* (or session_state)."""
    api_key = state.get("api_key", "")
    if not api_key:
        return None
    from llm_client import create_client
    return create_client(
        api_key=str(api_key),
        base_url=str(state.get("base_url", LLM_BASE_URL)),
        protocol=str(state.get("protocol", "openai")),
    )


def _run_grading_bg(task_id: str, task_data: dict):
    """Execute grading in a background thread — writes results to SQLite."""
    try:
        _state = task_data["_state"]
        _model = task_data["model"]
        _user_id = task_data["user_id"]
        _memory = task_data["memory"]
        _client = task_data["client"]

        results = _execute_grading_process(
            question=task_data["question"],
            student_ans=task_data["student_ans"],
            ocr_data=task_data["ocr_data"],
            selected_q=task_data["selected_q"],
            container=None,
            _state=_state,
            model=_model,
            user_id=_user_id,
            memory=_memory,
            client=_client,
        )

        if results is None:
            fail_task(task_id, "LLM client unavailable or grading returned no results")
            return

        complete_task(task_id, results)
    except Exception as exc:
        logger.error(f"Background grading failed for task {task_id}: {exc}")
        logger.error(traceback.format_exc())
        fail_task(task_id, str(exc))


def _submit_grading_async(question, student_ans, ocr_data, selected_q):
    """Create task, start background thread, return task_id.

    Extracts all needed state from st.session_state before spawning the thread.
    Guards against duplicate submission: if user already has a processing task
    that is less than 2 minutes old, re-attach to it instead of creating a new one.
    """
    user_id = st.session_state.auth.get("user_id", "unknown")

    # Guard: re-attach to an existing processing task
    existing = get_recent_task(user_id, minutes=2)
    if existing and existing.get("status") == "processing":
        return existing["task_id"]

    model = st.session_state.get("model", LLM_MODEL)
    memory = st.session_state.get("memory")

    # Create the task row
    task_id = create_task(user_id, question, student_ans, ocr_data, selected_q)

    # Build a plain dict with everything the background thread needs
    _state = {
        "model": model,
        "_client": get_client(),
        "api_key": st.session_state.get("api_key", ""),
        "base_url": st.session_state.get("base_url", LLM_BASE_URL),
        "protocol": st.session_state.get("protocol", "openai"),
        "question_db": st.session_state.get("question_db"),
        "grading_result": None,
        "diagnosis_result": None,
        "standard_answer": None,
        "standard_answer_structured": None,
        "answer_view_mode": False,
        "grading_triggered": False,
        "mistakes_force_reload": False,
    }

    # Use the main thread's already-created client instead of building
    # from scratch (avoids KeyError: 'llm_client' on some servers).
    client = _state.get("_client") or get_client()

    task_data = {
        "_state": _state,
        "question": question,
        "student_ans": student_ans,
        "ocr_data": ocr_data,
        "selected_q": selected_q,
        "model": model,
        "user_id": user_id,
        "memory": memory,
        "client": client,
    }

    thread = threading.Thread(
        target=_run_grading_bg,
        args=(task_id, task_data),
        daemon=True,
    )
    thread.start()

    return task_id


def _restore_results_to_session(task: dict):
    """Load grading results from a SQLite task row into st.session_state."""
    for key, json_key in [
        ("grading_result", "grading_result_json"),
        ("diagnosis_result", "diagnosis_result_json"),
        ("standard_answer", "standard_answer_json"),
        ("standard_answer_structured", "standard_answer_structured_json"),
        ("ocr_result", "ocr_data_json"),
    ]:
        val = task.get(json_key)
        if val:
            try:
                st.session_state[key] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass

    st.session_state["answer_view_mode"] = True

    # Restore selected_question from task
    sq_json = task.get("selected_q_json")
    if sq_json:
        try:
            st.session_state["selected_question"] = json.loads(sq_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Save error record to 错题本 (deferred from background thread).
    # Guard: skip if a record with the same question_id was already saved
    # in this session (avoids duplicates from multi-path saves).
    error_json = task.get("error_record_json")
    if error_json:
        try:
            error_record = json.loads(error_json)
            if error_record and st.session_state.get("memory"):
                qid = error_record.get("question_id", "")
                _seen = st.session_state.get("_saved_error_qids", set())
                _dedup_key = f"{task['user_id']}:{qid}"
                if _dedup_key not in _seen:
                    _seen.add(_dedup_key)
                    st.session_state["_saved_error_qids"] = _seen
                    st.session_state.memory.add_error_record(
                        task["user_id"], error_record
                    )
                    st.session_state.mistakes_force_reload = True
        except (json.JSONDecodeError, TypeError):
            pass

    # Mark as viewed so it won't be auto-restored again
    mark_viewed(task["task_id"])


# ═══════════════════════════════════════════════
#  Page renderer
# ═══════════════════════════════════════════════

def render_grading_page(db, render_latex):
    """..."""
    st.title("📖 查看答案" if st.session_state.get("answer_view_mode", False) else "📝 AI 批改")

    user_id = st.session_state.auth.get("user_id", "") if st.session_state.get("auth") else ""

    # ── Recovery: check SQLite for a recent completed task only ──
    # Note: Only recover completed tasks, not processing tasks.
    # Processing tasks from previous sessions may be stale (server crashed).
    # If user wants to retry, they should explicitly click "开始批改".
    if "ocr_result" not in st.session_state and user_id:
        recent = get_recent_task(user_id)
        if recent and recent.get("status") == "completed":
            _restore_results_to_session(recent)
            st.session_state.page = "grading"
            st.rerun()

    # 检查 ocr_result 是否已初始化
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = None

    ocr_data = st.session_state.ocr_result

    # 如果 ocr_data 为空，但有选中的题目，尝试从 session state 恢复学生答案
    if ocr_data is None:
        selected_q = st.session_state.get("selected_question")
        if selected_q and isinstance(selected_q, dict) and selected_q.get("question"):
            student_answer_parts = []

            selected_option = st.session_state.get("selected_option")
            q_type = selected_q.get("question_type", "")
            if q_type == "选择题" and selected_option:
                student_answer_parts.append(f"选项: {selected_option}")

            bank_text_answer = st.session_state.get("bank_text_answer", "")
            if bank_text_answer and bank_text_answer.strip():
                student_answer_parts.append(bank_text_answer.strip())

            text_answer = st.session_state.get("a_text", "")
            if text_answer and text_answer.strip() and text_answer != bank_text_answer:
                student_answer_parts.append(text_answer.strip())

            merged_answer = "\n\n".join(student_answer_parts)

            mt = selected_q.get("category", "数学一")
            qt = selected_q.get("question_type", "解答题")
            kps = ", ".join(selected_q.get("knowledge_points", []))

            ocr_data = {
                "success": True,
                "question": selected_q["question"],
                "student_answer": merged_answer,
                "math_type": mt,
                "question_type": qt,
                "knowledge_point": kps,
                "confidence": 1.0,
                "warnings": [],
                "selected_option": selected_option,
            }
            st.session_state.ocr_result = ocr_data
        else:
            st.info("请先在「智能刷题」页面上传或输入题目")
            if st.button("➡️ 前往刷题", key="goto_practice_1"):
                st.session_state.page = "practice"
                st.rerun()
            return

    # 确保 ocr_data 不为空
    if ocr_data is None:
        st.info("请先在「智能刷题」页面上传或输入题目")
        if st.button("➡️ 前往刷题", key="goto_practice_2"):
            st.session_state.page = "practice"
            st.rerun()
        return

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
            selected_q = st.session_state.get("selected_question") or {}
            if selected_q and isinstance(selected_q, dict) and selected_q.get("question"):
                from renderers import render_question
                try:
                    render_question(selected_q, show_actions=False)
                except Exception:
                    render_latex(question)
            else:
                render_latex(question)
    with col2:
        with st.container(border=True):
            st.caption("✍️ 学生作答")
            if student_ans:
                try:
                    render_latex(student_ans)
                except Exception:
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        render_structured_safe(from_legacy_text(student_ans))
                    except Exception:
                        st.text(str(student_ans)[:2000])
            else:
                st.markdown("（未作答）")

    # 知识点提示
    selected_q = st.session_state.get("selected_question") or {}
    kp_list = selected_q.get("knowledge_points", [])
    if kp_list:
        kp_tags = " · ".join(kp_list[:6])
        st.caption(f"🏷️ 考查知识点: {kp_tags}")

    # ── Async polling block ──
    pending_task_id = st.session_state.get("pending_task_id")
    if pending_task_id:
        task = get_task(pending_task_id)
        if task is None:
            del st.session_state["pending_task_id"]
            st.rerun()

        # Track when polling started to enforce a 30‑minute timeout
        poll_start = st.session_state.get("_poll_start", 0)
        if poll_start == 0:
            st.session_state["_poll_start"] = time.time()
            poll_start = st.session_state["_poll_start"]

        if task["status"] == "processing":
            elapsed = time.time() - poll_start
            if elapsed > 1800:  # 30 minutes
                fail_task(pending_task_id, "批改超时（超过30分钟未完成），请重试")
                del st.session_state["_poll_start"]
                st.rerun()
            st.info("⏳ 批改任务已提交，正在后台处理中... 页面将自动刷新。")
            st.caption(f"任务ID: `{pending_task_id}` | 已等待 {elapsed:.0f} 秒")
            time.sleep(3)
            st.rerun()
        elif task["status"] == "completed":
            del st.session_state["_poll_start"]
            _restore_results_to_session(task)
            del st.session_state["pending_task_id"]
            st.rerun()
        elif task["status"] == "failed":
            del st.session_state["_poll_start"]
            err_msg = task.get("error_msg", "未知错误")
            # If server restarted mid-task, suggest a fresh retry
            if "Server restarted" in err_msg:
                st.warning("检测到服务曾重启，批改任务已中断。请重新提交。")
            else:
                st.error(f"批改失败: {err_msg}")
            if st.button("🔄 重新批改", key="retry_grading"):
                # Clear the failed task so a fresh one is created
                del st.session_state["pending_task_id"]
                _clear_grading_state()
                st.rerun()
        return

    # ── Auto-submit for "查看解析" (view-only mode) ──
    if st.session_state.pop("_auto_submit_view_solution", None):
        _clear_grading_state()
        task_id = _submit_grading_async(question, student_ans, ocr_data, selected_q)
        st.session_state["pending_task_id"] = task_id
        st.rerun()

    # ── 批改按钮 ──
    if not answer_view_mode and st.button("🔍 开始批改", type="primary", use_container_width=True):
        _clear_grading_state()
        # Submit async: create task → start bg thread → store task_id for polling
        task_id = _submit_grading_async(question, student_ans, ocr_data, selected_q)
        st.session_state["pending_task_id"] = task_id
        st.rerun()

    # 结果/处理区域：用占位符统一管理
    result_placeholder = st.empty()

    # 检查是否需要开始批改流程（同步回退 — 当 pending_task_id 未设置时）
    if st.session_state.get("grading_triggered"):
        # Synchronous fallback path (kept for backward compatibility)
        model = st.session_state.get("model", LLM_MODEL)
        user_id = st.session_state.auth.get("user_id", "")
        memory = st.session_state.get("memory")
        client = get_client()

        with result_placeholder.container():
            results = _execute_grading_process(
                question, student_ans, ocr_data, selected_q, container=st,
                model=model, user_id=user_id, memory=memory, client=client,
            )
        if results:
            # Results already written to st.session_state, just need to trigger rerun
            st.rerun()
        return

    # 显示结果 — Card-based layout
    grading_result = st.session_state.get("grading_result")
    if grading_result:
        with result_placeholder.container():
            gr = grading_result
            sa = st.session_state.standard_answer or {}
            dr = st.session_state.diagnosis_result or {}
            total = sa.get("total_score", 10)

            selected_q = st.session_state.get("selected_question") or {}
            knowledge_points = selected_q.get("knowledge_points", []) or ocr_data.get("knowledge_point", "").split(",")

            render_grading_result_cards(
                gr, sa, dr, total,
                knowledge_points=knowledge_points,
                question=selected_q,
                question_db=db,
                solution_expanded=(gr.get("engine") == "view_only"),
            )

        return  # 提前返回，不执行后续的真题库部分

    # ==================== 真题库 ====================
    st.divider()
    st.subheader("📚 真题库")

    all_knowledge_points = []
    if db:
        try:
            all_knowledge_points = db.get_all_knowledge_points()
        except Exception:
            pass

    selected_kp = st.selectbox(
        "按知识点筛选",
        ["全部"] + sorted(all_knowledge_points),
        key="grading_kp_filter"
    )

    if db and selected_kp != "全部":
        try:
            related_questions = db.search(knowledge_point=selected_kp, limit=3)
            if related_questions:
                st.write(f"**{selected_kp}** 相关题目：")
                for q in related_questions:
                    with st.container(border=True):
                        st.markdown(f"**难度**: {q.get('difficulty', '中等')}")
                        render_latex(q.get("question", ""))
                        if st.button(f"▶️ 练习此题", key=f"practice_{q.get('question_id', '')}", width="stretch"):
                            st.session_state.selected_question = q
                            st.session_state.page = "practice"
                            st.rerun()
            else:
                st.info("暂无相关题目")
        except Exception as e:
            logger.error(f"Failed to fetch related questions: {e}")
            st.error("获取相关题目失败")
