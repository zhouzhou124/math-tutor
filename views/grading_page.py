"""pages/grading_page.py — AI 批改"""
import streamlit as st
from config import LLM_BASE_URL, LLM_MODEL
from agents import GradingAgent, DiagnosisAgent, SolverAgent
from solution_graph import CanonicalSolutionTrace
from solution_renderer import render_step, _op_type_cn
from ._shared import chip as _chip
from renderers.components.grading_result import render_grading_result_cards
from llm_client import create_client


def _get_client():
    """Get or create LLM client."""
    if st.session_state.llm_client is None and st.session_state.get("api_key"):
        st.session_state.llm_client = create_client(
            api_key=st.session_state.api_key,
            base_url=st.session_state.get("base_url", LLM_BASE_URL),
            protocol=st.session_state.get("protocol", "openai"),
        )
    return st.session_state.llm_client


def render_grading_page(db, render_latex):
    """..."""
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

        if answer_view_mode and st.session_state.standard_answer:
            st.markdown("---")
            with st.expander("📖 查看标准解法", expanded=False):
                render_latex(st.session_state.standard_answer.get("standard_answer", "暂无答案"))
            st.caption("先独立思考，再查看解法")

        # 批改按钮
        if not answer_view_mode and st.button("🔍 开始批改", type="primary", use_container_width=True):
            client = _get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                status = st.status("🔍 正在准备批改...", expanded=True)
                status.write("⏳ 获取标准答案...")
                model = st.session_state.get("model", LLM_MODEL)
                selected_q = st.session_state.get("selected_question") or {}

                # Step 1: 获取标准答案（优先用数据库缓存，跳过LLM生成）
                # 题库已预计算标准答案，直接读取无需AI重新求解
                cached_answer = selected_q.get("standard_answer", "")
                q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
                has_cached = cached_answer and (
                    len(cached_answer.strip()) > 1 or q_type == "选择题"
                )
                if has_cached:
                    # Build enriched solution steps from available data
                    enriched_answer = cached_answer
                    enriched_steps = selected_q.get("solution_steps", []) or []
                    
                    if not enriched_steps:
                        if q_type == "选择题":
                            correct = cached_answer.strip()
                            opts = selected_q.get("options") or {}
                            if correct in opts:
                                enriched_answer = f"正确选项: {correct}. {opts[correct]}"
                            else:
                                enriched_answer = f"正确选项: {correct}"
                        elif q_type == "填空题":
                            enriched_answer = cached_answer
                        else:
                            enriched_answer = cached_answer
                    
                    solution = {
                        "success": True,
                        "standard_answer": enriched_answer,
                        "total_score": selected_q.get("score", 10),
                        "steps": enriched_steps,
                    }
                    status.write("✓ 标准答案已加载（缓存）")
                else:
                    solver = SolverAgent(client, model)
                    solution = solver.solve(
                        question=question,
                        math_type=ocr_data.get("math_type", "数学一"),
                        question_type=ocr_data.get("question_type", "解答题"),
                        knowledge_point=ocr_data.get("knowledge_point", "未指定"),
                    )
                    status.write("✓ 标准解答已生成（AI求解）")
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
                    status.write("⏳ 启动图对齐批改引擎...")
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
                                engine_c_ok = True
                                status.write(f"✓ 图对齐批改完成（{method_count}法，最佳匹配: {best_method_name}）")
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
                        status.write("✓ LLM批改完成")

                    # Step 3: 诊断（仅解答题需要AI分析）
                    status.write("⏳ 正在诊断分析...")
                    diagnosis = DiagnosisAgent(client, model)
                    history = st.session_state.memory.get_errors(
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

                status.write("✓ 批改完成！")
                status.update(label="✅ 批改完成", state="complete", expanded=False)
                st.rerun()

        # 显示结果 — Card-based layout
        if st.session_state.grading_result:
            gr = st.session_state.grading_result
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


    # ==================== 真题库 ====================

