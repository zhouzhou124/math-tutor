"""管理员仪表盘页面 - 系统观测与管理"""

import streamlit as st
from .auth.session_state import get_current_username


def render_admin_dashboard():
    """渲染管理员仪表盘"""
    st.title("🔧 管理员后台")
    st.markdown(f"欢迎回来，**{get_current_username()}** (管理员)")
    
    # 导航标签
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "概览统计", 
        "用户管理", 
        "AI 批改监控", 
        "题库状态",
        "📼 数据回放",
        "📚 题库管理"
    ])
    
    with tab1:
        render_overview()
    
    with tab2:
        render_user_management()
    
    with tab3:
        render_grading_monitor()
    
    with tab4:
        render_question_bank_status()
    
    with tab5:
        render_data_replay()
    
    with tab6:
        render_question_management()


def render_overview():
    """概览统计"""
    st.subheader("📊 系统概览")
    
    # 创建服务
    from pathlib import Path
    from repository import UserRepository, ErrorRecordRepository
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")

    user_repo = UserRepository(db_path, data_dir)
    error_repo = ErrorRecordRepository(db_path, data_dir)
    
    # 获取统计数据
    total_users = get_total_users(user_repo)
    active_users = get_active_users(user_repo)
    total_errors = get_total_errors(error_repo)
    
    # 统计卡片
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("总用户数", total_users)
    
    with col2:
        st.metric("活跃用户", active_users)
    
    with col3:
        st.metric("错题记录", total_errors)
    
    # 最近系统活动
    st.subheader("📝 最近系统活动")
    st.info("系统活动日志功能开发中...")


def render_user_management():
    """用户管理"""
    st.subheader("👥 用户管理")
    
    # 创建服务
    from pathlib import Path
    from repository import UserRepository
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    user_repo = UserRepository(db_path, data_dir)
    
    # 搜索用户
    search_query = st.text_input("搜索用户名")
    
    # 获取用户列表
    users = get_all_users(user_repo)
    
    # 过滤用户
    if search_query:
        users = [u for u in users if search_query.lower() in u.username.lower()]
    
    # 显示用户列表
    if users:
        for user in users:
            with st.expander(f"👤 {user.username}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**用户ID**: {user.user_id}")
                with col2:
                    st.write(f"**角色**: {user.role}")
                with col3:
                    st.write(f"**状态**: {'活跃' if user.is_active else '禁用'}")
                
                st.write(f"**邮箱**: {user.email or '未设置'}")
                st.write(f"**创建时间**: {user.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                if user.is_active:
                    if st.button(f"禁用 {user.username}", key=f"disable_{user.user_id}"):
                        st.warning(f"禁用用户 {user.username} 功能开发中")
                else:
                    if st.button(f"启用 {user.username}", key=f"enable_{user.user_id}"):
                        st.success(f"启用用户 {user.username} 功能开发中")
    else:
        st.info("暂无用户")


def render_grading_monitor():
    """AI 批改监控"""
    st.subheader("🤖 AI 批改监控")
    
    # 最近批改记录
    st.markdown("### 最近批改")
    st.info("最近批改记录功能开发中...")
    
    # 错误率统计
    st.markdown("### 错误率统计")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今日批改", "156")
    with col2:
        st.metric("错误率", "12%")
    with col3:
        st.metric("平均耗时", "2.3s")
    
    # 模型响应时间
    st.markdown("### 模型响应监控")
    st.info("模型响应监控功能开发中...")
    
    # 推理链查看器
    st.markdown("### 推理链查看器")
    st.info("推理链查看器功能开发中...")


def render_question_bank_status():
    """题库状态"""
    st.subheader("📚 题库状态")
    
    # 题库统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总题目数", "385")
    with col2:
        st.metric("已解析", "385")
    with col3:
        st.metric("答案覆盖率", "100%")
    
    # 年份分布
    st.markdown("### 年份分布")
    years = ["2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    counts = [23] * len(years)
    st.bar_chart({"年份": years, "数量": counts})
    
    # 题目类型分布
    st.markdown("### 题目类型分布")
    types = {"选择题": 120, "填空题": 80, "解答题": 185}
    st.bar_chart(types)


def get_total_users(repo: UserRepository) -> int:
    """获取总用户数"""
    cursor = repo._query("SELECT COUNT(*) FROM users")
    row = cursor.fetchone()
    return row[0] if row else 0


def get_active_users(repo: UserRepository) -> int:
    """获取活跃用户数"""
    cursor = repo._query("SELECT COUNT(*) FROM users WHERE is_active = 1")
    row = cursor.fetchone()
    return row[0] if row else 0


def get_total_errors(repo: ErrorRecordRepository) -> int:
    """获取错题总数"""
    errors = repo._load_json(repo.file_path)
    total = 0
    for user_data in errors.values():
        total += len(user_data.get("records", []))
    return total


def get_all_users(repo: UserRepository) -> list:
    """获取所有用户"""
    cursor = repo._query("""
        SELECT user_id, username, email, role, is_admin, is_active, created_at 
        FROM users ORDER BY created_at DESC
    """)
    
    users = []
    from repository.models import User
    from datetime import datetime
    
    for row in cursor.fetchall():
        users.append(User(
            user_id=row[0],
            username=row[1],
            email=row[2],
            role=row[3],
            is_admin=bool(row[4]),
            is_active=bool(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.now(),
        ))
    
    return users


# ──────────────────────────────────────────────────────────
# 数据回放功能
# ──────────────────────────────────────────────────────────

def render_data_replay():
    """数据回放页面 - AI调试核心功能"""
    st.subheader("📼 数据回放")
    st.markdown("查看某次批改的完整过程，包括 OCR、AST、推理链、批改过程和错误传播")
    
    # 创建仓库
    from pathlib import Path
    from repository import GradingSessionRepository, UserRepository
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    
    session_repo = GradingSessionRepository(db_path, data_dir)
    user_repo = UserRepository(db_path, data_dir)
    
    # 获取会话列表
    sessions = session_repo.get_recent_sessions(limit=50)
    
    if not sessions:
        st.info("暂无批改会话记录")
        return
    
    # 选择会话
    session_options = [
        f"{s.session_id} - {get_username(user_repo, s.user_id)} - {s.question_id} - {s.status}"
        for s in sessions
    ]
    
    selected_session_str = st.selectbox("选择批改会话", session_options)
    
    if selected_session_str:
        session_id = selected_session_str.split(" - ")[0]
        session = session_repo.get_session(session_id)
        
        if session:
            render_session_details(session, user_repo)


def render_session_details(session, user_repo):
    """渲染会话详情"""
    st.markdown(f"### 📋 会话信息")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"**会话ID**: {session.session_id}")
    with col2:
        st.write(f"**用户**: {get_username(user_repo, session.user_id)}")
    with col3:
        st.write(f"**题目**: {session.question_id}")
    with col4:
        st.write(f"**状态**: {get_status_badge(session.status)}")
    
    st.write(f"**创建时间**: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if session.total_time > 0:
        st.write(f"**总耗时**: {session.total_time:.2f} 秒")
    
    # 流程步骤标签
    steps = []
    step_labels = []
    
    if session.ocr_result:
        steps.append("ocr")
        step_labels.append("📷 OCR")
    if session.student_ast or session.correct_ast:
        steps.append("ast")
        step_labels.append("🌳 AST")
    if session.reasoning_chain:
        steps.append("reasoning")
        step_labels.append("🧠 推理链")
    if session.grading_result:
        steps.append("grading")
        step_labels.append("✅ 批改结果")
    if session.diagnosis_result:
        steps.append("diagnosis")
        step_labels.append("🔍 诊断")
    
    if steps:
        tabs = st.tabs(step_labels)
        
        for i, step in enumerate(steps):
            with tabs[i]:
                if step == "ocr":
                    render_ocr_step(session.ocr_result)
                elif step == "ast":
                    render_ast_step(session.student_ast, session.correct_ast)
                elif step == "reasoning":
                    render_reasoning_step(session.reasoning_chain)
                elif step == "grading":
                    render_grading_step(session.grading_result)
                elif step == "diagnosis":
                    render_diagnosis_step(session.diagnosis_result)
    
    if session.error_message:
        st.error(f"**错误信息**: {session.error_message}")


def render_ocr_step(ocr_result):
    """渲染OCR步骤"""
    st.markdown("#### 📷 OCR识别结果")
    
    if not ocr_result:
        st.info("暂无OCR数据")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("输入")
        if ocr_result.image_path:
            st.write(f"**图片路径**: {ocr_result.image_path}")
            try:
                st.image(ocr_result.image_path)
            except Exception:
                st.info("图片无法加载")
    
    with col2:
        st.subheader("输出")
        if ocr_result.raw_text:
            st.write("**原始文本**:")
            st.code(ocr_result.raw_text, language="text")
        
        if ocr_result.latex_text:
            st.write("**LaTeX结果**:")
            st.latex(ocr_result.latex_text)
    
    # 元数据
    st.subheader("📊 元数据")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("置信度", f"{ocr_result.confidence:.2%}")
    with col2:
        st.metric("处理时间", f"{ocr_result.processing_time:.2f}s")
    with col3:
        st.metric("错误数", len(ocr_result.errors))
    
    if ocr_result.errors:
        st.subheader("⚠️ 错误信息")
        for error in ocr_result.errors:
            st.warning(error)


def render_ast_step(student_ast, correct_ast):
    """渲染AST步骤"""
    st.markdown("#### 🌳 AST解析")
    
    if student_ast or correct_ast:
        tab1, tab2 = st.tabs(["学生答案AST", "正确答案AST"])
        
        with tab1:
            if student_ast:
                st.write(f"**LaTeX源**:")
                st.latex(student_ast.latex_source)
                st.write(f"**AST ID**: {student_ast.ast_id}")
                if student_ast.validation_errors:
                    st.warning("**验证错误**:")
                    for error in student_ast.validation_errors:
                        st.write(f"- {error}")
            else:
                st.info("暂无学生答案AST")
        
        with tab2:
            if correct_ast:
                st.write(f"**LaTeX源**:")
                st.latex(correct_ast.latex_source)
                st.write(f"**AST ID**: {correct_ast.ast_id}")
                if correct_ast.validation_errors:
                    st.warning("**验证错误**:")
                    for error in correct_ast.validation_errors:
                        st.write(f"- {error}")
            else:
                st.info("暂无正确答案AST")
    else:
        st.info("暂无AST数据")


def render_reasoning_step(reasoning_chain):
    """渲染推理链步骤 - Domain → Mapper → ViewModel → Renderer → Adapter"""
    from presentation import ReasoningStepMapper
    from rendering import ReasoningRenderer, render_html
    
    st.markdown("#### 🧠 推理链")
    
    if not reasoning_chain:
        st.info("暂无推理链数据")
        return
    
    chain_vm = ReasoningStepMapper.to_chain(reasoning_chain)
    html = ReasoningRenderer.render_chain(chain_vm, title="推理步骤")
    render_html(html)


def render_grading_step(grading_result):
    """渲染批改结果步骤 - Domain → Mapper → ViewModel → Renderer → Adapter"""
    from presentation import GradingMapper
    from rendering import ScorePanel, DiffRenderer, FormulaBlock, render_html
    
    st.markdown("#### ✅ 批改结果")
    
    if not grading_result:
        st.info("暂无批改结果")
        return
    
    score_vm = GradingMapper.to_score_view(grading_result)
    formula_vm = GradingMapper.to_formula_view(grading_result)
    diff_vms = GradingMapper.to_diff_views(grading_result)
    
    render_html(ScorePanel.render(score_vm))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**是否正确**: {'✅ 正确' if grading_result.is_correct else '❌ 错误'}")
    with col2:
        st.write(f"**方法匹配**: {grading_result.method_matched or '未匹配'}")
    with col3:
        st.write(f"**置信度**: {grading_result.confidence:.2%}")
    
    render_html(FormulaBlock.render(formula_vm))
    
    if diff_vms:
        st.subheader("步骤分析")
        render_html(DiffRenderer.render_step_diffs(diff_vms))
    
    if grading_result.error_propagation:
        st.subheader("🔄 错误传播路径")
        for i, error in enumerate(grading_result.error_propagation, 1):
            st.markdown(f"{i}. ❌ {error}")


def render_diagnosis_step(diagnosis_result):
    """渲染诊断结果步骤 - Domain → Mapper → ViewModel → Renderer → Adapter"""
    from presentation import DiagnosisMapper
    from rendering import DiagnosisPanel, render_html
    
    st.markdown("#### 🔍 诊断结果")
    
    if not diagnosis_result:
        st.info("暂无诊断结果")
        return
    
    diagnosis_vm = DiagnosisMapper.to_diagnosis_view(diagnosis_result)
    render_html(DiagnosisPanel.render(diagnosis_vm))
    
    if diagnosis_vm.common_mistakes:
        st.subheader("⚠️ 常见错误")
        for mistake in diagnosis_vm.common_mistakes:
            st.warning(f"- {mistake}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**是否重复错误**: {'是' if diagnosis_vm.is_repeat else '否'}")
    with col2:
        st.write(f"**重复次数**: {diagnosis_vm.repeat_count}")


def get_username(user_repo, user_id):
    """获取用户名"""
    user = user_repo.get_user(user_id)
    return user.username if user else "未知用户"


def get_status_badge(status):
    """获取状态徽章"""
    status_map = {
        "pending": "⏳ 处理中",
        "processing": "🔄 处理中",
        "completed": "✅ 已完成",
        "error": "❌ 错误",
    }
    return status_map.get(status, status)


# ──────────────────────────────────────────────────────────
# 题库管理功能
# ──────────────────────────────────────────────────────────

def render_question_management():
    """题库管理页面"""
    st.subheader("📚 题库管理")
    
    # 创建仓库
    from pathlib import Path
    from repository import QuestionRepository
    
    db_path = Path("storage/math_tutor.db")
    data_dir = Path("storage/data")
    question_repo = QuestionRepository(db_path, data_dir)
    
    # 搜索和筛选
    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = st.text_input("关键词搜索", placeholder="搜索题目内容...")
    with col2:
        question_type = st.selectbox("题型筛选", ["", "选择题", "填空题", "解答题"])
    with col3:
        difficulty = st.selectbox("难度筛选", ["", "简单", "中等", "困难"])
    
    col1, col2 = st.columns(2)
    with col1:
        knowledge_points = [""] + question_repo.get_all_knowledge_points()
        knowledge_point = st.selectbox("知识点筛选", knowledge_points)
    
    # 获取题目列表
    questions = question_repo.search_questions(
        keyword=keyword,
        question_type=question_type,
        knowledge_point=knowledge_point,
        difficulty=difficulty
    )
    
    st.write(f"共找到 **{len(questions)}** 道题目")
    
    # 题目列表
    if questions:
        for question in questions:
            with st.expander(f"📝 {question.question_id} - {question.question[:50]}..."):
                render_question_detail(question, question_repo)
    else:
        st.info("暂无符合条件的题目")


def render_question_detail(question, question_repo):
    """渲染题目详情"""
    # 基本信息
    st.markdown("### 基本信息")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.write(f"**年份**: {question.year}")
    with col2:
        st.write(f"**题型**: {question.question_type}")
    with col3:
        st.write(f"**难度**: {question.difficulty}")
    with col4:
        st.write(f"**分值**: {question.score}分")
    
    # 知识点
    if question.knowledge_points:
        st.write(f"**知识点**: {', '.join(question.knowledge_points)}")
    
    # 题目内容
    st.markdown("### 题目")
    st.write(question.question)
    
    # 选项（选择题）
    if question.options:
        st.markdown("### 选项")
        for key, value in question.options.items():
            is_correct = key == question.correct_option
            prefix = "✅ " if is_correct else ""
            st.write(f"{prefix}**{key}**. {value}")
    
    # 答案
    if question.correct_option:
        st.write(f"**正确答案**: {question.correct_option}")
    
    if question.answer:
        st.markdown("### 解答")
        st.latex(question.answer)
    
    # 解析
    if question.analysis:
        st.markdown("### 解析")
        st.write(question.analysis)
    
    # OCR修复
    if question.ocr_raw or question.ocr_fixed:
        st.markdown("### OCR修复")
        if question.ocr_raw:
            st.write("**OCR原文**:")
            st.code(question.ocr_raw)
        if question.ocr_fixed:
            st.write("**修复后**:")
            st.code(question.ocr_fixed)
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(f"编辑题目", key=f"edit_{question.question_id}"):
            st.session_state["editing_question"] = question.question_id
    
    with col2:
        if st.button(f"修复OCR", key=f"ocr_{question.question_id}"):
            st.session_state["fixing_ocr"] = question.question_id
    
    with col3:
        if st.button(f"删除题目", key=f"delete_{question.question_id}"):
            if question_repo.delete_question(question.question_id):
                st.success(f"已删除题目: {question.question_id}")
                st.rerun()
            else:
                st.error("删除失败")
    
    # 编辑表单
    if st.session_state.get("editing_question") == question.question_id:
        render_edit_form(question, question_repo)
    
    # OCR修复表单
    if st.session_state.get("fixing_ocr") == question.question_id:
        render_ocr_fix_form(question, question_repo)


def render_edit_form(question, question_repo):
    """编辑题目表单"""
    st.markdown("---")
    st.subheader("✏️ 编辑题目")
    
    # 表单字段
    question.question = st.text_area("题目内容", question.question, height=100)
    question.question_type = st.selectbox("题型", ["选择题", "填空题", "解答题"], 
                                         index=["选择题", "填空题", "解答题"].index(question.question_type))
    question.difficulty = st.selectbox("难度", ["简单", "中等", "困难"],
                                      index=["简单", "中等", "困难"].index(question.difficulty))
    question.score = st.number_input("分值", min_value=1, value=question.score)
    
    # 知识点
    existing_kps = ", ".join(question.knowledge_points)
    new_kps = st.text_input("知识点（逗号分隔）", existing_kps)
    question.knowledge_points = [k.strip() for k in new_kps.split(",") if k.strip()]
    
    # 选项（选择题）
    if question.question_type == "选择题":
        st.subheader("选项")
        options = {}
        for key in ["A", "B", "C", "D"]:
            options[key] = st.text_input(f"选项 {key}", question.options.get(key, ""))
        question.options = options
        question.correct_option = st.selectbox("正确答案", ["A", "B", "C", "D"])
    
    # 解答题答案
    if question.question_type == "解答题":
        question.answer = st.text_area("参考答案", question.answer or "", height=150)
    
    # 解析
    question.analysis = st.text_area("解析", question.analysis or "", height=150)
    
    # 保存按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存修改"):
            if question_repo.update_question(question):
                st.success("修改成功")
                st.session_state["editing_question"] = None
                st.rerun()
            else:
                st.error("保存失败")
    
    with col2:
        if st.button("取消"):
            st.session_state["editing_question"] = None
            st.rerun()


def render_ocr_fix_form(question, question_repo):
    """OCR修复表单"""
    st.markdown("---")
    st.subheader("🔧 OCR修复")
    
    ocr_raw = st.text_area("OCR原文", question.ocr_raw or "", height=100)
    ocr_fixed = st.text_area("修复后文本", question.ocr_fixed or "", height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存修复"):
            if question_repo.fix_ocr(question.question_id, ocr_raw, ocr_fixed):
                st.success("修复成功")
                st.session_state["fixing_ocr"] = None
                st.rerun()
            else:
                st.error("保存失败")
    
    with col2:
        if st.button("取消"):
            st.session_state["fixing_ocr"] = None
            st.rerun()

