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
    r"""恢复丢失的反斜杠和修复数学符号。
    
    LLM输出或JSON传输过程中，反斜杠可能丢失或被转义。
    例如: \s in x → \sin x, \c os x → \cos x
    
    同时处理Unicode数学符号到LaTeX命令的转换。
    """
    if not text:
        return text
    
    result = text
    
    # ── Step 1: 修复被分割的命令（必须在保护之前）──
    # 例如: \s in x → \sin x, \c os x → \cos x
    # 按长度降序排列，优先匹配长命令
    split_cmds = [
        (r'\arcsin', r'\\arcs\s*in'),
        (r'\arccos', r'\\arcc\s*os'),
        (r'\arctan', r'\\arct\s*an'),
        (r'\arccot', r'\\arcc\s*ot'),
        (r'\arcsec', r'\\arcsec'),
        (r'\arccsc', r'\\arccsc'),
        (r'\sinh', r'\\sin\s*h'),
        (r'\cosh', r'\\cos\s*h'),
        (r'\tanh', r'\\tan\s*h'),
        (r'\coth', r'\\cot\s*h'),
        (r'\sech', r'\\sec\s*h'),
        (r'\csch', r'\\csc\s*h'),
        (r'\limsup', r'\\lim\s*sup'),
        (r'\liminf', r'\\lim\s*inf'),
        (r'\varlimsup', r'\\varlim\s*sup'),
        (r'\varliminf', r'\\varlim\s*inf'),
        (r'\sin', r'\\s\s*in'),
        (r'\cos', r'\\c\s*os'),
        (r'\tan', r'\\t\s*an'),
        (r'\cot', r'\\c\s*ot'),
        (r'\sec', r'\\s\s*ec'),
        (r'\csc', r'\\c\s*sc'),
        (r'\log', r'\\l\s*og'),
        (r'\ln', r'\\l\s*n'),
        (r'\exp', r'\\e\s*xp'),
        (r'\min', r'\\m\s*in'),
        (r'\max', r'\\m\s*ax'),
        (r'\sup', r'\\s\s*up'),
        (r'\inf', r'\\i\s*nf'),
        (r'\det', r'\\d\s*et'),
        (r'\dim', r'\\d\s*im'),
        (r'\deg', r'\\d\s*eg'),
        (r'\arg', r'\\a\s*rg'),
        (r'\rank', r'\\r\s*ank'),
    ]
    
    for target, pattern in split_cmds:
        # 使用 lambda 函数避免替换字符串被解析为模板
        result = re.sub(pattern, lambda m, t=target: t, result)
    
    # ── Step 2: 保护所有已存在的反斜杠命令 ──
    # 这可以防止像 \sin 被错误地添加反斜杠变成 \\sin
    protected = {}
    cmd_count = 0
    matches = list(re.finditer(r'\\[a-zA-Z]+', result))
    for match in reversed(matches):
        full_cmd = match.group(0)
        placeholder = f'\x00CMD{cmd_count}\x00'
        result = result[:match.start()] + placeholder + result[match.end():]
        protected[placeholder] = full_cmd
        cmd_count += 1
    
    # ── Step 3: 恢复常见的LaTeX命令前缀（没有反斜杠的命令）──
    # 使用原始字符串定义，确保反斜杠不被解释
    latex_prefixes = (
        r'\Biggl', r'\biggl', r'\big', r'\Bigg', r'\bigg', r'\Big',
        r'\left', r'\right', r'\middle',
        r'\frac', r'\sum', r'\int', r'\prod', r'\lim',
        r'\sin', r'\cos', r'\tan', r'\log', r'\ln',
        r'\sqrt', r'\partial',
        r'\mathbf', r'\mathrm', r'\mathcal', r'\mathit', r'\mathtt', r'\mathsf', r'\mathbb',
        r'\cdot', r'\times', r'\div', r'\equiv', r'\approx', r'\sim', r'\simeq',
        r'\in', r'\notin', r'\subset', r'\supset', r'\subseteq', r'\supseteq', r'\cup', r'\cap',
        r'\rightarrow', r'\leftarrow', r'\mapsto', r'\Rightarrow', r'\Leftarrow', 
        r'\Leftrightarrow', r'\leftrightarrow', r'\hookleftarrow', r'\hookrightarrow',
        r'\alpha', r'\beta', r'\gamma', r'\delta', r'\epsilon', r'\varepsilon',
        r'\zeta', r'\eta', r'\theta', r'\vartheta', r'\iota', r'\kappa',
        r'\lambda', r'\mu', r'\nu', r'\xi', r'\pi', r'\varpi',
        r'\rho', r'\varrho', r'\sigma', r'\varsigma', r'\tau', r'\upsilon', r'\phi',
        r'\varphi', r'\chi', r'\psi', r'\omega',
        r'\Gamma', r'\Delta', r'\Theta', r'\Lambda', r'\Xi',
        r'\Pi', r'\Sigma', r'\Upsilon', r'\Phi', r'\Psi', r'\Omega',
        r'\oplus', r'\otimes', r'\odot', r'\coprod', r'\bigcup', r'\bigcap', r'\bigsqcup',
        r'\setminus', r'\\',
        r'\neq', r'\leq', r'\geq', r'\le', r'\ge', r'\lt', r'\gt',
        r'\forall', r'\exists', r'\emptyset', r'\infty', r'\partial', r'\nabla',
        r'\triangle', r'\square', r'\diamond', r'\circ', r'\bullet',
        r'\hat', r'\widehat', r'\tilde', r'\widetilde',
        r'\bar', r'\vec', r'\dot', r'\ddot', r'\prime', r'\dagger', r'\ddagger',
        r'\pm', r'\mp', r'\cap', r'\cup', r'\setminus',
        r'\to', r'\times', r'\cdot',
        r'\frac', r'\dfrac', r'\cfrac', r'\tfrac', r'\root', r'\abs', r'\norm',
        r'\oint', r'\iint', r'\iiint', r'\iiiint', r'\idotsint',
        r'\ldots', r'\cdots', r'\vdots', r'\ddots',
    )
    
    # 按长度降序排序，避免短命令匹配优先
    latex_prefixes = sorted(latex_prefixes, key=len, reverse=True)
    
    # 匹配模式：前面不是反斜杠，后面是字母、{、空白或行尾
    for prefix in latex_prefixes:
        # 获取不带反斜杠的部分
        cmd = prefix[1:]  # 去掉开头的 \
        # 匹配：前面不是 \，后面跟着命令
        pattern = r'(?<!\\)' + re.escape(cmd) + r'(?=[a-zA-Z]|\{|\s|$|\\)'
        # 使用 lambda 函数来避免替换字符串中的反斜杠被解释
        result = re.sub(pattern, lambda m, p=prefix: p, result)
    
    # ── Step 4: 恢复被保护的命令 ──
    for placeholder, original in protected.items():
        result = result.replace(placeholder, original)
    
    # ── Step 3: Unicode数学符号转换为LaTeX命令 ──
    unicode_to_latex = {
        '∈': r'\in',
        '∉': r'\notin',
        '⊂': r'\subset',
        '⊃': r'\supset',
        '⊆': r'\subseteq',
        '⊇': r'\supseteq',
        '∩': r'\cap',
        '∪': r'\cup',
        '∅': r'\emptyset',
        '∞': r'\infty',
        '≤': r'\leq',
        '≥': r'\geq',
        '≠': r'\neq',
        '≡': r'\equiv',
        '≈': r'\approx',
        '∼': r'\sim',
        '≃': r'\simeq',
        '≅': r'\cong',
        '→': r'\rightarrow',
        '←': r'\leftarrow',
        '⇒': r'\Rightarrow',
        '⇐': r'\Leftarrow',
        '⇔': r'\Leftrightarrow',
        '↔': r'\leftrightarrow',
        '×': r'\times',
        '·': r'\cdot',
        '÷': r'\div',
        '±': r'\pm',
        '∓': r'\mp',
        '∀': r'\forall',
        '∃': r'\exists',
        '∂': r'\partial',
        '∇': r'\nabla',
        '√': r'\sqrt',
        '∑': r'\sum',
        '∏': r'\prod',
        '∫': r'\int',
        '∬': r'\iint',
        '∭': r'\iiint',
        '∮': r'\oint',
        '∠': r'\angle',
        '⊥': r'\perp',
        '∥': r'\parallel',
        '△': r'\triangle',
        '□': r'\square',
        '°': r'^\circ',
        '′': r'\prime',
        '″': r'\prime\prime',
        '‴': r'\prime\prime\prime',
        '⁻¹': r'^{-1}',
        '²': r'^2',
        '³': r'^3',
        'ⁿ': r'^n',
        '₁': r'_1',
        '₂': r'_2',
        '₃': r'_3',
        'ₙ': r'_n',
        'α': r'\alpha',
        'β': r'\beta',
        'γ': r'\gamma',
        'δ': r'\delta',
        'ε': r'\epsilon',
        'ζ': r'\zeta',
        'η': r'\eta',
        'θ': r'\theta',
        'ι': r'\iota',
        'κ': r'\kappa',
        'λ': r'\lambda',
        'μ': r'\mu',
        'ν': r'\nu',
        'ξ': r'\xi',
        'π': r'\pi',
        'ρ': r'\rho',
        'σ': r'\sigma',
        'τ': r'\tau',
        'υ': r'\upsilon',
        'φ': r'\phi',
        'χ': r'\chi',
        'ψ': r'\psi',
        'ω': r'\omega',
        'Γ': r'\Gamma',
        'Δ': r'\Delta',
        'Θ': r'\Theta',
        'Λ': r'\Lambda',
        'Ξ': r'\Xi',
        'Π': r'\Pi',
        'Σ': r'\Sigma',
        'Υ': r'\Upsilon',
        'Φ': r'\Phi',
        'Ψ': r'\Psi',
        'Ω': r'\Omega',
    }
    
    # 只在数学模式外替换Unicode符号（避免替换已经正确的LaTeX命令）
    # 先保护 $...$ 内的内容
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00M{len(protected)-1}\x00'
    temp = re.sub(r'\$[^$]+\$', _protect, result)
    temp = re.sub(r'\$\$[^$]+\$\$', _protect, temp)
    
    # 在保护区域外替换Unicode符号
    for unicode_char, latex_cmd in unicode_to_latex.items():
        temp = temp.replace(unicode_char, latex_cmd)
    
    # 恢复保护区域
    for i, block in enumerate(protected):
        temp = temp.replace(f'\x00M{i}\x00', block)
    
    result = temp
    
    return result


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
    patterns = [
        # #### 步骤二：（优先匹配带####的）
        re.compile(r'(####\s*步骤[一二三四五六七八九十\d]+[：:])'),
        # 步骤二：（不带####的）
        re.compile(r'(步骤[一二三四五六七八九十\d]+[：:])'),
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
            # 恢复丢失的反斜杠
            answer = _restore_backslashes(answer)
            
            st.markdown("**答案**")
            try:
                segments = split_latex_text(answer)
                render_ast(segments)
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
