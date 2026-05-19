"""pages/grading_page.py — AI 批改"""
import time
import streamlit as st
import logging
from concurrent.futures import ThreadPoolExecutor
from config import LLM_BASE_URL, LLM_MODEL
from agents import GradingAgent, DiagnosisAgent, SolverAgent
from renderers.components.grading_result import render_grading_result_cards
from ._shared import get_client

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _clear_grading_state():
    """清理所有批改相关的状态，用于重新开始批改时确保干净的状态"""
    keys_to_clear = [
        'grading_result', 
        'diagnosis_result', 
        'standard_answer', 
        'standard_answer_structured',
        'answer_view_mode', 
        'grading_triggered'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def _standard_answer_needs_expansion(answer: str, steps: list, q_type: str) -> bool:
    """Return True when a cached answer is too thin for LLM grading/rendering."""
    if steps:
        return False

    text = (answer or "").strip()
    if not text:
        return True

    placeholders = ("证明略", "略", "解析略", "过程略", "答案略", "方法略")
    if any(p in text for p in placeholders):
        return True

    # 选择题只有选项字母（如"A"）、填空题只有数字（如"1/2"）→ 需要展开详细过程
    if q_type in ("选择题", "填空题") and len(text) < 80:
        return True

    # 解答题/证明题的短答案（<120字符）也需要展开
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


def _build_standard_solution(question, ocr_data, selected_q, client, status,
                             force_expansion: bool = False) -> dict:
    """获取/生成标准解答。空作答和正常批改共用同一逻辑。
    force_expansion=True 时所有题型都生成详细步骤（空作答查看答案场景）。
    status 可以是 Streamlit status 或 _ThreadSafeStatus。"""
    cached_answer = selected_q.get("standard_answer", "")
    correct_option = selected_q.get("correct_option", "")
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
    opts = selected_q.get("options") or {}
    model = st.session_state.get("model", LLM_MODEL)

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
                client=client, model=model,
            )
            solution = {
                "success": True,
                "standard_answer": expanded if expanded else _known_answer,
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
                client=client, model=model,
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
            solver = SolverAgent(client, model)
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

    st.session_state.standard_answer = solution
    # 构建 _structured（如果还没有）
    if solution.get("_structured"):
        st.session_state.standard_answer_structured = solution["_structured"]
    else:
        try:
            from latex_utils import from_legacy_text
            raw = _solution_to_text(solution)
            if raw:
                st.session_state.standard_answer_structured = from_legacy_text(raw)
                solution["_structured"] = st.session_state.standard_answer_structured
        except Exception:
            st.session_state.standard_answer_structured = None

    return solution


def _execute_grading_process(question, student_ans, ocr_data, selected_q, container=None):
    """执行批改流程，封装为独立函数"""
    ctx = container or st
    client = get_client()  # 提前获取，空作答和正常批改都可能用到

    # ── 空作答快速通道：只展示标准答案，不进行AI批改和诊断 ──
    if not (student_ans or "").strip():
        status = ctx.status("📖 查看标准答案...", expanded=True)
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status,
                                             force_expansion=True)
        if solution is None:
            st.session_state.grading_triggered = False
            return

        st.session_state.standard_answer = solution
        gresult = {
            "success": True, "total": 0, "step_score": 0, "result_score": 0,
            "step_analysis": [], "deductions": [],
            "comment": "未作答，仅查看标准答案",
            "engine": "view_only",
        }
        _q_kps = (selected_q or {}).get("knowledge_points", []) or []
        # 如果题目没有知识点，用 OCR 识别到的知识点作为兜底
        if not _q_kps:
            _ocr_kp = ocr_data.get("knowledge_point", "") if ocr_data else ""
            _q_kps = [_ocr_kp] if _ocr_kp and _ocr_kp != "未指定" else []
        _q_mistakes = (selected_q or {}).get("common_mistakes", []) or []
        # 将易错提示注入 selected_q，供 render_knowledge_points 展示
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
        st.session_state.grading_result = gresult
        st.session_state.diagnosis_result = dresult
        status.write("✓ 完成")
        st.session_state.answer_view_mode = True
        st.session_state.grading_triggered = False
        status.update(label="✅ 查看答案完成", state="complete", expanded=False)
        st.rerun()

    # client 已在函数开头获取，此处检查是否可用
    if client is None:
        st.warning("请先在「系统设置」中配置 API Key")
        st.session_state.grading_triggered = False
        return

    _t_start = time.time()
    status = ctx.status("🔍 正在准备批改...", expanded=True)
    status.write("⏳ 获取标准答案...")
    model = st.session_state.get("model", LLM_MODEL)
    selected_q = selected_q or st.session_state.get("selected_question") or {}
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))

    # 解答题/证明题：标准答案生成 与 lock_question 可并行
    is_complex = q_type in ("解答题", "证明题")
    solution = None
    _future_solution = None
    _ts_status = None

    if is_complex and selected_q.get("question_id"):
        # 启动标准答案生成到后台线程（用线程安全的 status 包装器）
        _ts_status = _ThreadSafeStatus()
        _executor = ThreadPoolExecutor(max_workers=1)
        _future_solution = _executor.submit(
            _build_standard_solution, question, ocr_data, selected_q, client, _ts_status
        )
        status.write("⏳ 标准答案与规范解并行生成中...")
    else:
        # 选择题/填空题：直接生成（<1s 缓存命中）
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status)
        if solution is None:
            st.session_state.grading_triggered = False
            return

    # Step 2: 批改 — Engine A 快速路径(选择/填空) vs Engine B LLM路径(解答/证明)
    std_ans = ""
    total_score = 10
    is_fast_path = q_type in ("选择题", "填空题")

    if is_fast_path and not is_complex:
        # 等待 solution（如果还没获取）
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
                locked = lock_question(selected_q, st.session_state.question_db, client, model)
                _canonical = locked.get("canonical_trace")

                # 提取学生轨迹（只做一次，后续 evolver 复用）
                from student_trace_extractor import extract_student_trace
                from symbolic_executor import build_student_graph_from_trace
                _trace_result = extract_student_trace(
                    student_ans or "", question, client, model
                )
                student_graph = build_student_graph_from_trace(_trace_result)

                # 等待后台标准答案生成完成（与 lock+extract 并行）
                if _future_solution:
                    solution = _future_solution.result()
                    _ts_status.flush(status)
                    _executor.shutdown(wait=False)
                std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
                total_score = solution.get("total_score", 10)
                status.write("✓ 标准答案与规范解就绪")

                # Best-Match：遍历所有 canonical methods，取最高分
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
                        std_ans = _solution_to_text(solution) or solution["standard_answer"]
                    engine_c_ok = True
                    status.write(f"✓ 图对齐批改完成（{method_count}法，最佳匹配: {best_method_name}）")
            except Exception as _e_c:
                logger.error(f"[Engine C 失败] {_e_c}")

        # 如果后台线程还没取结果（question_id 为空的边缘情况）
        if _future_solution and solution is None:
            solution = _future_solution.result()
            _ts_status.flush(status)
            _executor.shutdown(wait=False)
            std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
            total_score = solution.get("total_score", 10)

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
            status.write("✓ LLM批改完成")

        # Step 3: 诊断（高正确率跳过LLM，直接用本地诊断，节省5-30秒）
        status.write("⏳ 正在诊断分析...")
        _score = gresult.get("total", 0)
        _max = solution.get("total_score", 10)
        _is_high_score = _max > 0 and _score / _max >= 0.9

        if _is_high_score:
            # 高正确率 → 本地诊断，无需LLM
            diagnosis = DiagnosisAgent(None, model)
            history = []
            dresult = diagnosis._local_diagnose(gresult, history)
            status.write("✓ 诊断完成（高分快速通道）")
        else:
            diagnosis = DiagnosisAgent(client, model)
            history = st.session_state.memory.get_errors(
                user_id=st.session_state.auth['user_id'],
                knowledge_point=ocr_data.get("knowledge_point", "")
            )
            dresult = diagnosis.diagnose(
                question=question, student_answer=student_ans,
                standard_answer=std_ans, grading_result=gresult,
                error_history=history,
            )
            status.write("✓ 诊断完成")
    st.session_state.grading_result = gresult
    st.session_state.diagnosis_result = dresult
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

    status.write("⏳ 保存到错题本...")

    # Step 4: 保存到错题本（完整批改结果）
    if gresult.get("total", 0) < solution.get("total_score", 10) * 0.9:
        full_standard_answer = _solution_to_text(solution) or solution.get("standard_answer", "")

        # Build solution_steps from structured data if legacy steps are empty
        saved_steps = solution.get("steps", [])
        if not saved_steps:
            structured = solution.get("_structured") or st.session_state.get("standard_answer_structured")
            if isinstance(structured, dict):
                struct_steps = structured.get("steps", [])
                if struct_steps:
                    saved_steps = struct_steps

        error_record = {
            # 题目信息
            "question_id": selected_q.get("question_id", ""),
            "question": question,
            "math_type": ocr_data.get("math_type", ""),
            "question_type": ocr_data.get("question_type", ""),
            "knowledge_point": ocr_data.get("knowledge_point", ""),
            "knowledge_points": selected_q.get("knowledge_points", []) or dresult.get("knowledge_points", []),
            "difficulty": selected_q.get("difficulty", "中等"),
            # 作答信息
            "student_answer": student_ans,
            "standard_answer": full_standard_answer,
            "solution_steps": saved_steps,
            # 评分结果
            "score": gresult.get("total", 0),
            "max_score": solution.get("total_score", 10),
            "is_correct": gresult.get("total", 0) >= solution.get("total_score", 10) * 0.9,
            "comment": gresult.get("comment", ""),
            "step_analysis": gresult.get("step_analysis", []),
            "method_matched": gresult.get("method_matched", ""),
            "engine": gresult.get("engine", gresult.get("_engine", "unknown")),
            "confidence": gresult.get("confidence", 0.0),
            # 诊断结果
            "error_type": dresult.get("error_type", ""),
            "root_cause": dresult.get("root_cause", ""),
            "weak_points": dresult.get("weak_points", []),
            "recommendations": dresult.get("recommendations", []),
            "common_mistakes": dresult.get("common_mistakes", []),
            "is_repeat_diagnosis": dresult.get("is_repeat", False),
            # 时间戳
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        }
        st.session_state.memory.add_error_record(st.session_state.auth['user_id'], error_record)
        # 清除错题本缓存，确保下次打开时加载最新数据
        st.session_state.mistakes_force_reload = True

    _elapsed = time.time() - _t_start
    status.write(f"✓ 批改完成！（总耗时 {_elapsed:.1f} 秒）")
    st.session_state.answer_view_mode = True  # 设置为查看答案模式
    st.session_state.grading_triggered = False  # 重置触发标志，防止重复执行
    status.update(label=f"✅ 批改完成（{_elapsed:.1f}s）", state="complete", expanded=False)
    st.rerun()


def render_grading_page(db, render_latex):
    """..."""
    st.title("📖 查看答案" if st.session_state.get("answer_view_mode", False) else "📝 AI 批改")

    # 检查 ocr_result 是否已初始化
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = None

    ocr_data = st.session_state.ocr_result

    # 如果 ocr_result 为空，但有选中的题目，尝试从 session state 恢复学生答案
    if ocr_data is None:
        selected_q = st.session_state.get("selected_question")
        if selected_q and isinstance(selected_q, dict) and selected_q.get("question"):
            # 尝试从 session state 中恢复学生答案
            student_answer_parts = []
            
            # 恢复选择题选项
            selected_option = st.session_state.get("selected_option")
            q_type = selected_q.get("question_type", "")
            if q_type == "选择题" and selected_option:
                student_answer_parts.append(f"选项: {selected_option}")
            
            # 恢复文本答案
            bank_text_answer = st.session_state.get("bank_text_answer", "")
            if bank_text_answer and bank_text_answer.strip():
                student_answer_parts.append(bank_text_answer.strip())
            
            # 恢复文本输入模式的答案
            text_answer = st.session_state.get("a_text", "")
            if text_answer and text_answer.strip() and text_answer != bank_text_answer:
                student_answer_parts.append(text_answer.strip())
            
            merged_answer = "\n\n".join(student_answer_parts)
            
            # 构建 ocr_result
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

    # 确保 ocr_data 不为空（上一步可能已将 None 恢复为 dict）
    if ocr_data is None:
        st.info("请先在「智能刷题」页面上传或输入题目")
        if st.button("➡️ 前往刷题", key="goto_practice_2"):
            st.session_state.page = "practice"
            st.rerun()
        return
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
                    render_latex(student_ans)
                else:
                    st.markdown("（未作答）")

        # 知识点提示
        selected_q = st.session_state.get("selected_question") or {}
        kp_list = selected_q.get("knowledge_points", [])
        if kp_list:
            kp_tags = " · ".join(kp_list[:6])
            st.caption(f"🏷️ 考查知识点: {kp_tags}")

        # 批改按钮
        if not answer_view_mode and st.button("🔍 开始批改", type="primary", width="stretch"):
            # 清除之前的批改结果和状态
            _clear_grading_state()
            st.session_state.grading_triggered = True
            # 使用 st.rerun() 进行完全刷新
            st.rerun()

        # 结果/处理区域：用占位符统一管理，确保新状态直接替换旧内容而非置灰
        result_placeholder = st.empty()

        # 检查是否需要开始批改流程（rerun后执行）
        if st.session_state.get("grading_triggered"):
            with result_placeholder.container():
                _execute_grading_process(question, student_ans, ocr_data, selected_q, container=st)
            return

        # 显示结果 — Card-based layout
        grading_result = st.session_state.get("grading_result")
        if grading_result:
            with result_placeholder.container():
                gr = grading_result
                sa = st.session_state.standard_answer or {}
                dr = st.session_state.diagnosis_result or {}
                total = sa.get("total_score", 10)

                # 获取题目信息用于知识点展示和相似题目推荐
                selected_q = st.session_state.get("selected_question") or {}
                knowledge_points = selected_q.get("knowledge_points", []) or ocr_data.get("knowledge_point", "").split(",")

                render_grading_result_cards(
                    gr, sa, dr, total,
                    knowledge_points=knowledge_points,
                    question=selected_q,
                    question_db=db
                )

        return  # 提前返回，不执行后续的真题库部分


    # ==================== 真题库 ====================
    st.divider()
    st.subheader("📚 真题库")
    
    # 知识点筛选
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
    
    # 显示推荐题目
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

