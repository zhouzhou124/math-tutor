import html
import re
"""grading_result.py — Grading result cards.

Card layout:
  Score → Knowledge Points → Diagnosis → Step Comparison → Standard Solution → Recommendations
"""
import streamlit as st
from latex_utils import safe_latex, split_latex_text, render_ast


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
        <div style="text-align:center;padding:8px 0;">
            <span style="font-size:2.5em;">{emoji}</span><br>
            <span style="font-size:2.2em;font-weight:800;color:{color};">{score}</span>
            <span style="font-size:1.2em;color:#94a3b8;"> / {total_score}</span>
        </div>
        """, unsafe_allow_html=True)

        comment = gr.get("comment", "")
        if comment:
            st.caption(comment)


def render_knowledge_points(knowledge_points: list, question: dict = None) -> None:
    """独立展示知识点卡片 — 不在标准解法中隐藏"""
    if not knowledge_points:
        return

    with st.container(border=True):
        st.markdown("**📚 考查知识点**")
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


def render_diagnosis_card(dr: dict, gr: dict) -> None:
    """Error diagnosis card."""
    error_type = dr.get("error_type", "")
    root_cause = dr.get("root_cause", "")
    is_repeat = dr.get("is_repeat", False)
    weak_points = dr.get("weak_points", [])

    if not error_type and not root_cause:
        return

    with st.container(border=True):
        st.markdown("**🔍 错因诊断**")

        if error_type:
            st.markdown(f"**错误类型**: {error_type}")

        if root_cause:
            st.info(root_cause)

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


def _restore_backslashes(text: str) -> str:
    r"""恢复丢失的反斜杠。
    
    LLM输出或JSON传输过程中，反斜杠可能丢失或被转义。
    例如: \x 应该是 \\x, \bigl 应该是 \\bigl
    
    ═══════════════════════════════════════════════
    关键保护：防止误匹配
    ═══════════════════════════════════════════════
    问题：
    1. \sin x → \s ∈ x："in" 被误认为 \in
    2. \sqrt → \d："s" 后跟空格被误认为 \s
    
    解决方案：
    - 先保护已存在的 \命令，避免它们被误处理
    - 按长度降序排序，优先匹配长命令（如 \sqrt 优先于 \s）
    - 使用严格的匹配条件
    ═══════════════════════════════════════════════
    """
    if not text:
        return text
    
    # ═══════════════════════════════════════════════
    # 步骤1：先保护所有已存在的 \命令，避免被误处理
    # ═══════════════════════════════════════════════
    protected = {}
    temp_text = text
    cmd_count = 0
    
    # 匹配所有已存在的 \命令
    existing_cmd_pattern = re.compile(r'\\[a-zA-Z]+')
    matches = list(existing_cmd_pattern.finditer(temp_text))
    
    # 从后往前处理，避免位置偏移
    for match in reversed(matches):
        full_cmd = match.group(0)
        placeholder = f'\x00REST{cmd_count}\x00'
        temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
        protected[placeholder] = full_cmd
        cmd_count += 1
    
    # ═══════════════════════════════════════════════
    # 步骤2：恢复丢失的反斜杠
    # ═══════════════════════════════════════════════
    
    # 常见的LaTeX命令前缀，需要恢复反斜杠
    # 使用原始字符串定义，确保反斜杠不被解释
    latex_prefixes = (
        r'\Biggl', r'\biggl', r'\big', r'\Bigg', r'\bigg', r'\Big',
        r'\left', r'\right', r'\middle',
        r'\frac', r'\sum', r'\int', r'\prod', r'\lim',
        r'\sin', r'\cos', r'\tan', r'\log', r'\ln',
        r'\sqrt', r'\partial',
        r'\mathbf', r'\mathrm', r'\mathcal', r'\mathit',
        r'\cdot', r'\times', r'\equiv', r'\approx', r'\sim',
        r'\in', r'\subset', r'\supset', r'\cup', r'\cap',
        r'\rightarrow', r'\leftarrow', r'\Rightarrow', r'\Leftarrow',
        r'\alpha', r'\beta', r'\gamma', r'\delta', r'\epsilon',
        r'\zeta', r'\eta', r'\theta', r'\iota', r'\kappa',
        r'\lambda', r'\mu', r'\nu', r'\xi', r'\pi',
        r'\rho', r'\sigma', r'\tau', r'\upsilon', r'\phi',
        r'\chi', r'\psi', r'\omega',
        r'\Gamma', r'\Delta', r'\Theta', r'\Lambda', r'\Xi',
        r'\Pi', r'\Sigma', r'\Upsilon', r'\Phi', r'\Psi', r'\Omega',
    )
    
    # 按长度降序排序，避免短命令匹配优先（如 \sqrt 优先于 \s）
    latex_prefixes = sorted(latex_prefixes, key=len, reverse=True)
    
    # 匹配模式：前面不是反斜杠，后面是字母或{
    for prefix in latex_prefixes:
        # 获取不带反斜杠的部分
        cmd = prefix[1:]  # 去掉开头的 \
        
        # 对于短命令（2个字符及以下），使用更严格的匹配条件
        # 避免误匹配：如 "in" 在单词中间不应该被认为是 \in
        if len(cmd) <= 2:
            # 更严格的条件：前面是空格或行首，后面是空格、{或行尾
            pattern = r'(?<![a-zA-Z])' + re.escape(cmd) + r'(?![a-zA-Z])'
        else:
            # 普通条件：前面不是反斜杠，后面跟着字母或{或空格或行尾
            pattern = r'(?<!\\)' + re.escape(cmd) + r'(?=[a-zA-Z]|\{|\s|$)'
        
        # 使用 lambda 函数来避免替换字符串中的反斜杠被解释
        temp_text = re.sub(pattern, lambda m, p=prefix: p, temp_text)
    
    # ═══════════════════════════════════════════════
    # 步骤3：恢复被保护的命令
    # ═══════════════════════════════════════════════
    for placeholder, original in protected.items():
        temp_text = temp_text.replace(placeholder, original)
    
    return temp_text


def _split_mixed_steps(text: str) -> list:
    """将混合的步骤文本分割成独立步骤。
    
    识别步骤分隔模式：
    - #### 步骤二：
    - 步骤二：
    - step2:
    - 【2分】等分数标记
    """
    if not text:
        return [text]
    
    # 先处理可能的JSON转义问题
    text = text.replace('\\\\', '\\')
    
    # 步骤分隔模式（按优先级排序）
    # 模式1: #### 步骤X：（带分隔线的）
    # 模式2: 步骤X：
    # 模式3: 【X分】作为分隔符
    # 支持中文数字（一二三四五六七八九十）和阿拉伯数字（0-9）
    patterns = [
        # #### 步骤二：或 #### 步骤2：（优先匹配带####的）
        re.compile(r'(####\s*步骤[一二三四五六七八九十\d]+[：:])'),
        # 步骤二：或 步骤2：（不带####的）
        re.compile(r'(步骤[一二三四五六七八九十\d]+[：:])'),
        # step2: 或 Step 2: 格式
        re.compile(r'(\b[Ss]tep\s*\d+:)'),
    ]
    
    # 使用第一个匹配的模式进行分割
    for pattern in patterns:
        matches = list(pattern.finditer(text))
        if matches:
            result = []
            last_end = 0
            for match in matches:
                # 获取匹配前的内容
                prefix = text[last_end:match.start()].strip()
                # 获取匹配的标记
                mark = match.group(1)
                # 获取标记后的内容（直到下一个标记或结尾）
                if match != matches[-1]:
                    content = text[match.end():matches[matches.index(match)+1].start()].strip()
                else:
                    content = text[match.end():].strip()
                
                # 如果前缀有内容且不是空白，作为第一个步骤
                if last_end == 0 and prefix:
                    result.append(prefix)
                
                # 添加标记+内容
                step_content = mark + content
                if step_content.strip():
                    result.append(step_content)
                
                last_end = match.end()
            
            # 过滤空内容
            return [p.strip() for p in result if p.strip()]
    
    # 如果没有找到步骤标记，尝试按特殊标记分割
    # 检查是否包含多个步骤混在一起的标记
    if '####' in text:
        parts = re.split(r'####+', text)
        return [p.strip() for p in parts if p.strip()]
    
    return [text]


def render_standard_solution(solution: dict) -> None:
    """Standard solution card — collapsed by default."""
    steps = solution.get("steps") or []
    answer = solution.get("standard_answer", "")

    if not steps and not answer:
        return

    # 去重步骤：移除内容完全相同的重复步骤
    unique_steps = []
    seen_contents = set()
    for step in steps:
        if isinstance(step, dict):
            content = step.get("content", "")
        else:
            content = str(step)
        # 只保留内容不重复的步骤
        if content and content not in seen_contents:
            seen_contents.add(content)
            unique_steps.append(step)
    steps = unique_steps

    with st.expander("📖 查看标准解法", expanded=False):
        if steps:
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    label = step.get("label", f"步骤{i+1}")
                    step_content = step.get("content", "")
                else:
                    label = f"步骤{i+1}"
                    step_content = str(step)
                
                if step_content:
                    # 恢复丢失的反斜杠
                    step_content = _restore_backslashes(step_content)
                    
                    # 检查是否包含多个步骤混在一起
                    sub_steps = _split_mixed_steps(step_content)
                    
                    if len(sub_steps) > 1:
                        # 多个子步骤，分开渲染
                        for j, sub_step in enumerate(sub_steps):
                            # 尝试提取标签
                            label_match = re.match(r'(步骤[一二三四五六七八九十\d]+[：:]|####\s*步骤[一二三四五六七八九十\d]+[：:])', sub_step)
                            if label_match:
                                sub_label = label_match.group(1)
                                sub_content = sub_step[len(sub_label):].strip()
                            else:
                                sub_label = f"{label}-{j+1}"
                                sub_content = sub_step
                            
                            st.markdown(f"**{sub_label}**")
                            try:
                                segments = split_latex_text(sub_content)
                                render_ast(segments)
                            except Exception:
                                # 使用 STLatexRenderer 正确渲染 LaTeX
                                try:
                                    from rendering.renderers.st_latex_renderer import STLatexRenderer
                                    STLatexRenderer.render(sub_content)
                                except Exception:
                                    try:
                                        safe = safe_latex(sub_content)
                                        st.markdown(safe)
                                    except Exception:
                                        st.markdown(sub_content)
                            # 添加分隔线
                            if j < len(sub_steps) - 1:
                                st.markdown("---")
                    else:
                        # 单个步骤，正常渲染
                        st.markdown(f"**{label}**")
                        try:
                            segments = split_latex_text(step_content)
                            render_ast(segments)
                        except Exception as e:
                            # 使用 STLatexRenderer 正确渲染 LaTeX
                            try:
                                from rendering.renderers.st_latex_renderer import STLatexRenderer
                                STLatexRenderer.render(step_content)
                            except Exception:
                                try:
                                    safe = safe_latex(step_content)
                                    st.markdown(safe)
                                except Exception:
                                    st.markdown(step_content)
                    
                    # 步骤之间添加分隔线
                    if i < len(steps) - 1:
                        st.markdown("---")

        elif answer:
            # 没有步骤，只有答案
            import re as _re
            answer = _restore_backslashes(answer)
            
            # Normalize LaTeX: fix inconsistent formatting
            try:
                from latex_normalizer import normalize_latex_style
                answer = normalize_latex_style(answer)
            except Exception:
                pass
            
            st.markdown("**答案**")
            try:
                segments = split_latex_text(answer)
                render_ast(segments)
            except Exception:
                # 使用 STLatexRenderer 正确渲染 LaTeX
                try:
                    from rendering.renderers.st_latex_renderer import STLatexRenderer
                    STLatexRenderer.render(answer)
                except Exception:
                    try:
                        safe = safe_latex(answer)
                        st.markdown(safe)
                    except Exception:
                        st.markdown(answer)


def render_recommendations(dr: dict, question_db=None, current_question=None) -> None:
    """Learning recommendations card with similar question links."""
    weak_points = dr.get("weak_points", [])
    if not weak_points:
        return

    with st.container(border=True):
        st.markdown("**📖 巩固建议**")
        recs = [
            f"重点复习 **{wp}** 相关知识点" for wp in weak_points[:3]
        ]
        for i, rec in enumerate(recs, 1):
            st.markdown(f"{i}. {rec}")

        # 相似题目推荐
        if question_db and current_question and weak_points:
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
                            st.button(
                                f"📝 {qid}",
                                key=f"similar_q_{qid}",
                                use_container_width=True,
                                help=f"{year}年 {qtype}"
                            )
            except Exception as e:
                # 如果推荐功能不可用，显示原有提示
                st.caption("建议在错题本中查看同类题目进行针对性练习")
        else:
            st.caption("建议在错题本中查看同类题目进行针对性练习")


def render_grading_result_cards(gr: dict, sa: dict, dr: dict, total_score: int = 10, 
                                 knowledge_points: list = None, question: dict = None, 
                                 question_db=None) -> None:
    """Progressive disclosure: score + knowledge points + main error visible, details collapsed.

    Default view:
      ┌─ Score card (always visible) ─┐
      ├─ Knowledge Points (always visible) ─┤
      └─ Diagnosis (always visible) ─┘

    Expandable (click to reveal):
      ▶ 📊 步骤对比分析
      ▶ 📖 查看标准解法
      ▶ 📖 巩固建议
    """
    st.markdown("---")

    # ═══ Always visible: Score ═══
    render_score_card(gr, total_score)

    # ═══ Always visible: Knowledge Points — 独立展示，不在标准解法中隐藏 ═══
    kp_list = knowledge_points or question.get("knowledge_points", []) if question else []
    render_knowledge_points(kp_list, question)

    # ═══ Always visible: Diagnosis ═══
    render_diagnosis_card(dr, gr)

    # ═══ Collapsed: Step details ═══
    if gr.get("step_analysis"):
        with st.expander("📊 步骤对比分析", expanded=False):
            _render_step_comparison_body(gr)

    # ═══ Collapsed: Standard solution ═══
    render_standard_solution(sa)

    # ═══ Collapsed: Recommendations ═══
    weak_points = dr.get("weak_points", [])
    if weak_points:
        with st.expander("📖 巩固建议", expanded=False):
            render_recommendations(dr, question_db, question)


def _render_step_comparison_body(gr: dict) -> None:
    """Step comparison body — rendered inside expander."""
    import html as _html
    steps = gr.get("step_analysis") or []
    if not steps:
        return

    h1, h2, h3 = st.columns([1, 0.15, 1])
    with h1:
        st.markdown("<span style='color:#64748b;font-size:0.78rem;font-weight:700;'>📝 你的作答</span>", unsafe_allow_html=True)
    with h2:
        st.markdown("")
    with h3:
        st.markdown("<span style='color:#64748b;font-size:0.78rem;font-weight:700;'>📋 标准步骤</span>", unsafe_allow_html=True)

    for s in steps:
        num = s.get("num", "?")
        content = s.get("content", "")
        judgment = s.get("judgment", "")
        score_str = s.get("score", "")
        comment = s.get("comment", "")

        if judgment == "正确":
            icon, jcolor = "✅", "#16a34a"
        elif "缺失" in str(judgment) or "错误" in str(judgment):
            icon, jcolor = "❌", "#dc2626"
        else:
            icon, jcolor = "⚠️", "#f59e0b"

        student_desc = comment if comment else judgment
        bg = {"#dc2626": "#fef2f2", "#16a34a": "#f0fdf4", "#f59e0b": "#fffbeb"}.get(jcolor, "#f8fafc")

        c1, c2, c3 = st.columns([1, 0.15, 1])
        with c1:
            st.markdown(
                f"<div style='padding:8px;border-radius:8px;background:{bg};"
                f"border-left:3px solid {jcolor};'>"
                f"<span style='font-size:0.82rem;color:#334155;'>{_html.escape(student_desc[:120])}</span>"
                f"</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='text-align:center;font-size:1.2em;'>{icon}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(
                f"<div style='padding:8px;border-radius:8px;background:#f8fafc;"
                f"border-left:3px solid #3b82f6;'>"
                f"<span style='font-size:0.8rem;color:#64748b;font-weight:600;'>步骤{num}</span><br>"
                f"<span style='font-size:0.82rem;color:#334155;'>{_html.escape(content[:120])}</span>"
                f"</div>", unsafe_allow_html=True)
        st.caption(f"得分: {score_str}分")
        if s != steps[-1]:
            st.markdown("---")
