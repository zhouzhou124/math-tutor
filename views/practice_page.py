"""pages/practice_page.py — 智能练习"""
import os
import streamlit as st
import time
from config import MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS, LLM_BASE_URL, KNOWLEDGE_POINTS
from agents import OCR_Agent, SolverAgent
from ._shared import chip as _chip
from renderers import render_question
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


def render_practice_page(db):
    """..."""
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
            render_question(selected_bank)

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
            client = _get_client()
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
                client = _get_client()
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
                client = _get_client()
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

