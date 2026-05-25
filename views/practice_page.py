"""pages/practice_page.py — 智能练习"""
import os
import streamlit as st
import time
from config import MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS, LLM_BASE_URL, KNOWLEDGE_POINTS, LLM_MODEL
from agents import OCR_Agent, SolverAgent
from ._shared import chip as _chip, get_client
from renderers import render_question


def render_practice_page(db):
    """..."""
    st.title("✏️ 智能刷题")

    selected_bank = st.session_state.get("selected_question")

    # Clear previous answer selection when the question changes
    if selected_bank:
        _current_qid = selected_bank.get("question_id", "")
        _prev_qid = st.session_state.get("_prev_practice_qid", "")
        if _current_qid != _prev_qid:
            st.session_state["_prev_practice_qid"] = _current_qid
            st.session_state.pop("selected_option", None)
            st.session_state.pop("bank_text_answer", None)

    if selected_bank:
        # ═══════════════════════════════════════════
        #  情况 A: 题库已选题 — 文本 + 拍照 双入口
        # ═══════════════════════════════════════════
        st.info(f"📋 已选题目: {selected_bank.get('question_id', '?')} — "
                f"{selected_bank.get('category', '')} {selected_bank.get('question_type', '')} "
                f"| 知识点: {', '.join(selected_bank.get('knowledge_points', [])[:3])}")

        if st.button("↩️ 返回题库", key="back_to_bank_from_practice"):
            st.session_state.selected_question = None
            st.session_state.page = "question_bank"
            st.rerun()

        # ── 题目展示 ──
        st.subheader("📋 题目内容")
        with st.container(border=True):
            render_question(selected_bank, show_actions=False)

        # 元数据只读展示
        mt = selected_bank.get("category", "数学一")
        qt = selected_bank.get("question_type", "解答题")
        kps = ", ".join(selected_bank.get("knowledge_points", []))
        st.caption(f"📐 {mt} | 📝 {qt} | 🏷️ {kps}")

        st.markdown("---")
        st.subheader("✍️ 输入你的作答")
        st.caption("文本和图片可同时使用，系统会合并两者内容后再批改。")

        # ── 选择题：添加选项选择界面 ──
        selected_option = None
        if qt == "选择题":
            st.markdown("### 🎯 选择你的答案")
            options = selected_bank.get("options", {})
            # Fallback: parse options from question text if not stored
            if not options:
                try:
                    from choice_explainer import _parse_options_from_question
                    options = _parse_options_from_question(
                        selected_bank.get("raw_question_text") or selected_bank.get("question", "")
                    )
                except Exception:
                    options = {}
            if options:
                cols = st.columns(len(options))
                for i, (key, value) in enumerate(options.items()):
                    with cols[i]:
                        is_selected = st.session_state.get("selected_option") == key
                        if st.button(key, key=f"opt_{key}", use_container_width=True,
                                    type="primary" if is_selected else "secondary"):
                            st.session_state.selected_option = key
                            selected_option = key
                        # Render option content below the button with LaTeX support.
                        # Option values are already wrapped in $...$ or $$...$$.
                        cleaned = (value or "").strip()
                        if cleaned:
                            st.markdown(cleaned)
                selected_option = st.session_state.get("selected_option")
                if selected_option:
                    st.success(f"✓ 已选择选项: {selected_option}")
                else:
                    st.info("请选择一个选项")

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
            with st.expander("📸 拍照建议", expanded=False):
                from agents.ocr_agent import OCR_Agent
                from vision.mathpix_client import is_available as mathpix_available  # direct import, avoids cv2 dep
                pix2tex_ok = OCR_Agent.is_pix2tex_available()
                mp_ok = mathpix_available()
                if mp_ok:
                    engine_status = "✅ Mathpix公式识别引擎已启用（手写+印刷）"
                elif pix2tex_ok:
                    engine_status = "✅ pix2tex公式识别引擎已启用（印刷体）"
                else:
                    engine_status = "⚠️ 公式识别引擎未安装 (pip install pix2tex)"
                st.markdown(f"""
                <div style="font-size:0.82rem;color:#64748b;line-height:1.7;">
                {engine_status}<br><br>
                ✅ <b>平整放置</b>：纸张平铺，正上方拍摄<br>
                ✅ <b>光线均匀</b>：避免阴影和反光<br>
                ✅ <b>字迹清晰</b>：用黑色或蓝色笔书写<br>
                ✅ <b>留白适当</b>：周围保留少量边距<br>
                ⚠️ <b>手写识别准确率有限</b>，复杂公式建议配合文本输入
                </div>
                """, unsafe_allow_html=True)
            bank_photo_answer = st.file_uploader(
                "上传作答图片", type=["png", "jpg", "jpeg"],
                key="bank_photo_answer", label_visibility="collapsed",
            )
            if bank_photo_answer:
                st.image(bank_photo_answer, use_container_width=True)
                st.caption("💡 提示：OCR识别手写数学公式准确率有限，建议同时在左侧文本框中输入关键公式")

        has_text = bool(bank_text_answer and bank_text_answer.strip())
        has_photo = bank_photo_answer is not None
        has_option = bool(st.session_state.get("selected_option"))
        
        # 选择题：选项选择即可提交
        can_submit = has_text or has_photo
        if qt == "选择题":
            can_submit = can_submit or has_option

        # 状态提示
        if has_text and has_photo:
            st.success("📝 文本 + 📷 图片 已就绪，将合并两者内容后批改")
        elif has_text:
            st.info("📝 文本输入已就绪")
        elif has_photo:
            st.info("📷 图片已就绪，提交后将 OCR 识别")
        elif has_option and qt == "选择题":
            st.success(f"✓ 已选择选项 {st.session_state.selected_option}")

        # ── 提交按钮（始终可点击，允许空作答查看答案）──
        if st.button("🚀 提交批改", type="primary", use_container_width=True):
            client = get_client()
            if client is None:
                st.warning("请先在「系统设置」中配置 API Key")
            else:
                student_answer_parts = []

                # 处理图片 OCR（带进度显示和超时机制）
                if has_photo:
                    from views.components.ocr_progress import show_ocr_progress, reset_ocr_progress, progress_callback
                    
                    reset_ocr_progress()
                    
                    # 创建一个容器来显示进度
                    progress_container = st.empty()
                    with progress_container.container():
                        show_ocr_progress()
                    
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                        f.write(bank_photo_answer.read())
                        a_path = f.name

                    # 使用改进的OCR Agent（带进度回调和超时机制）
                    ocr_agent = OCR_Agent(client, st.session_state.get("model", LLM_MODEL))
                    
                    try:
                        # 调用识别（带进度追踪）
                        ocr_result = ocr_agent.recognize(
                            answer_image_path=a_path,
                            progress_callback=progress_callback
                        )
                        
                        # 更新进度显示
                        progress_container.empty()
                        
                        # ── 降级策略：根据置信度分级反馈 ──
                        ocr_text = (ocr_result.get("student_answer") or "").strip()
                        ocr_conf = ocr_result.get("confidence", 0)
                        ocr_warnings = ocr_result.get("warnings", [])
                        ocr_quality = ocr_result.get("image_quality", {})
                        ocr_engine = ocr_result.get("engine", "unknown")

                        if ocr_text:
                            student_answer_parts.append(ocr_text)

                            if ocr_conf >= 0.7:
                                # 高置信度：直接使用
                                st.success(
                                    f"✅ OCR识别成功（置信度: {ocr_conf:.0%}，引擎: {ocr_engine}）"
                                )
                                with st.expander("📝 查看识别结果", expanded=False):
                                    st.code(ocr_text[:500], language="latex")

                            elif ocr_conf >= 0.3:
                                # 中置信度：可用但建议复核
                                st.warning(
                                    f"⚠️ OCR置信度较低（{ocr_conf:.0%}），建议人工复核识别结果"
                                )
                                with st.expander("📝 识别结果（可编辑后提交）", expanded=True):
                                    edited = st.text_area(
                                        "确认或修改识别内容",
                                        value=ocr_text[:500],
                                        height=150,
                                        key="ocr_edited_text",
                                    )
                                    if edited != ocr_text:
                                        student_answer_parts[-1] = edited

                            else:
                                # 低置信度：很可能错误
                                st.error(
                                    f"❌ OCR置信度过低（{ocr_conf:.0%}），手写内容无法可靠识别"
                                )
                                st.info("💡 建议在左侧文本框中手动输入作答过程的LaTeX公式")
                                with st.expander("📝 原始识别结果（仅供参考）", expanded=False):
                                    st.code(ocr_text[:500], language="latex")

                            # 显示图片质量报告
                            if ocr_quality and ocr_quality.get("issues"):
                                with st.expander("🔍 图片质量分析", expanded=False):
                                    for issue in ocr_quality["issues"]:
                                        st.caption(f"• {issue}")
                                    if ocr_quality.get("score", 0) < 0.3:
                                        st.caption("💡 建议：使用扫描APP（如CamScanner）或确保光线充足后重拍")

                        else:
                            # 完全失败
                            st.error("❌ OCR未能识别出任何内容")
                            if ocr_warnings:
                                for w in ocr_warnings:
                                    st.caption(f"• {w}")
                            st.info("💡 请在左侧文本框中手动输入作答内容（使用 $...$ 包裹公式）")
                            if ocr_quality and ocr_quality.get("issues"):
                                with st.expander("🔍 图片质量问题", expanded=True):
                                    for issue in ocr_quality["issues"]:
                                        st.caption(f"• {issue}")
                                    st.caption("💡 建议：重拍时确保纸张平整、光线均匀、字迹清晰")
                                
                    except Exception as e:
                        progress_container.empty()
                        st.error(f"识别过程出错: {str(e)}")
                        st.warning("OCR识别失败，建议手动输入作答内容")

                    try:
                        os.unlink(a_path)
                    except Exception:
                        pass

                # 处理选择题选项
                selected_option = st.session_state.get("selected_option")
                # 直接从 session state 获取题目类型，确保正确性
                current_qt = selected_bank.get("question_type", "解答题")
                if current_qt == "选择题" and selected_option:
                    student_answer_parts.insert(0, f"选项: {selected_option}")

                # 处理文本输入
                if has_text:
                    student_answer_parts.append(bank_text_answer.strip())

                merged_answer = "\n\n".join(student_answer_parts)

                # 如果只有选择题选项而没有其他内容，确保 merged_answer 不为空
                if not merged_answer and selected_option:
                    merged_answer = f"选项: {selected_option}"

                st.session_state.ocr_result = {
                    "success": True,
                    "question": selected_bank["question"],
                    "student_answer": merged_answer,
                    "math_type": mt,
                    "question_type": current_qt,
                    "knowledge_point": kps,
                    "confidence": 0.9 if has_photo else 1.0,
                    "warnings": [],
                    "selected_option": selected_option,  # 保存选中的选项
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
                with st.expander("📸 拍照建议", expanded=False):
                    from agents.ocr_agent import OCR_Agent
                    from vision.mathpix_client import is_available as mathpix_available  # direct import, avoids cv2 dep2
                    mp_ok2 = mathpix_available()
                    pix2tex_ok2 = OCR_Agent.is_pix2tex_available()
                    if mp_ok2:
                        engine2 = "✅ Mathpix已启用（手写+印刷）"
                    elif pix2tex_ok2:
                        engine2 = "✅ pix2tex已启用（印刷体）"
                    else:
                        engine2 = "⚠️ 公式识别引擎未安装"
                    st.markdown(f"""
                    <div style="font-size:0.82rem;color:#64748b;line-height:1.7;">
                    {engine2}<br>
                    ✅ 纸张平铺，正上方拍摄<br>
                    ✅ 光线均匀，避免阴影<br>
                    ✅ 字迹清晰，黑/蓝色笔<br>
                    ⚠️ 手写公式识别率有限
                    </div>
                    """, unsafe_allow_html=True)
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
            profile = st.session_state.memory.get_profile(st.session_state.auth['user_id'])
            weak_points = profile.weak_points if profile else []
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
                        from latex_utils import safe_render
                        safe_render(student_answer, role="student_answer")

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
                        answer_text = (student_answer or "").strip()
                        st.session_state.ocr_result = {
                            "success": True,
                            "question": question_text,
                            "student_answer": answer_text,
                            "math_type": math_type_t,
                            "question_type": q_type_t,
                            "knowledge_point": kp_t,
                            "confidence": 1.0,
                            "warnings": [],
                        }
                        st.session_state.answer_view_mode = False
                        st.session_state.page = "grading"
                        st.rerun()

            # 验证学生答案是否为空
            if question_text and not student_answer:
                st.info("未填写作答时将进入查看答案模式，AI 会生成详细步骤解答。")


    # ==================== AI 批改 ====================

