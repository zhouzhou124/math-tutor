"""pages/question_bank_page.py — 题库页面（优化版）

搜索、浏览、编辑、删除题目。

性能优化:
  1. 支持缓存统计数据
  2. 搜索结果缓存
  3. 懒加载渲染
  4. 避免重复数据库查询
"""
import os as _os
import html
import re
import streamlit as st
import time

from config import MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS, KNOWLEDGE_POINTS
from database import QuestionImporter
from exam_parser import ExamParserPipeline
from database import MarkdownExamParser
from ._shared import chip as _chip
from renderers import render_question


# 缓存时间配置
SEARCH_CACHE_TTL = 10  # 搜索结果缓存时间（秒）


def get_search_cache_key(filters):
    """生成搜索缓存键"""
    return "_".join(f"{k}_{v}" for k, v in sorted(filters.items()) if v)


def render_question_bank_page(db, render_latex, cached_stats=None):
    """渲染题库页面（优化版）

    Args:
        db: QuestionDB 实例
        render_latex: 数学渲染函数 (callable)
        cached_stats: 缓存的统计数据（可选）
    """
    # 使用缓存的统计数据或重新获取
    if cached_stats is not None:
        stats = cached_stats
    else:
        stats = db.stats()

    # --- 本地文件导入提示 ---
    source_dirs = [
        "storage/math1_source",
        "storage/math12_source",
        "storage/math2_latex",
    ]
    available = [d for d in source_dirs if _os.path.isdir(f"E:/math_tutor/{d}")
                 and any(f.endswith('.md') for f in _os.listdir(f"E:/math_tutor/{d}"))]

    if stats["total"] == 0:
        if available:
            st.info(
                f"📂 检测到本地真题文件: {', '.join(available)}。"
                "点击下方按钮一键导入。",
                icon="📂"
            )
            use_enhanced = st.checkbox(
                "使用增强解析引擎（自动拆分题目、匹配答案、修复LaTeX）",
                value=True, key="use_enhanced_empty",
                help="推荐开启。新引擎会从solutions/目录自动匹配解答。"
            )
            if st.button("🚀 一键导入本地真题", type="primary"):
                all_qs = []
                if use_enhanced:
                    from exam_parser import ExamParserPipeline
                    pipeline = ExamParserPipeline(db=db)
                    paper_dirs = [
                        "storage/math1_source/Kaoyan-Math1-Papers-main/papers",
                    ]
                    for d in paper_dirs:
                        full_path = f"E:/math_tutor/{d}"
                        if _os.path.isdir(full_path):
                            results = pipeline.process_directory(full_path)
                            for result in results:
                                all_qs.extend(result.questions)
                else:
                    from database import MarkdownExamParser
                    for d in available:
                        parser = MarkdownExamParser()
                        full_path = f"E:/math_tutor/{d}"
                        qs = parser.parse_directory(full_path)
                        all_qs.extend(qs)
                if all_qs:
                    importer = QuestionImporter(db)
                    report = importer.import_dict(all_qs)
                    st.success(
                        f"导入完成: 成功 {report['success']} 题, "
                        f"跳过重复 {report['skipped_duplicates']}, "
                        f"失败 {report['failed']}"
                    )
                    st.rerun()
                else:
                    st.error("未能从本地文件中解析出题目。请确认文件格式正确（Markdown格式）。")
        else:
            st.info(
                "📭 真题库为空。请下载真题源文件放到 storage/ 目录，"
                "或使用「导入」功能添加题目。",
                icon="ℹ️"
            )
            col_empty1, col_empty2 = st.columns(2)
            with col_empty1:
                if st.button("📥 载入示例数据", use_container_width=True):
                    importer = QuestionImporter(db)
                    report = importer.seed_examples()
                    st.success(f"导入 {report['success']} 题（演示数据）")
                    st.rerun()
            with col_empty2:
                st.caption(
                    "📌 获取真题:\n"
                    "下载 [Kaoyan-Math1-Papers](https://github.com/TsekaLuk/Kaoyan-Math1-Papers)\n"
                    "解压到 `E:\\math_tutor\\storage\\math1_source\\`"
                )

    if available and stats["total"] > 0:
        with st.expander(f"📂 本地真题文件 ({', '.join(available)})", expanded=False):
            use_enhanced_reexport = st.checkbox(
                "使用增强解析引擎（推荐：自动修复LaTeX、匹配解答、知识点标注）",
                value=True, key="use_enhanced_reexport",
            )
            if st.button("🔄 重新导入本地真题"):
                all_qs = []
                if use_enhanced_reexport:
                    from exam_parser import ExamParserPipeline
                    pipeline = ExamParserPipeline(db=db)
                    paper_dir = "E:/math_tutor/storage/math1_source/Kaoyan-Math1-Papers-main/papers"
                    if _os.path.isdir(paper_dir):
                        results = pipeline.process_directory(paper_dir)
                        for result in results:
                            all_qs.extend(result.questions)
                else:
                    from database import MarkdownExamParser
                    for d in available:
                        parser = MarkdownExamParser()
                        qs = parser.parse_directory(f"E:/math_tutor/{d}")
                        all_qs.extend(qs)
                if all_qs:
                    importer = QuestionImporter(db)
                    report = importer.import_dict(all_qs)
                    st.success(
                        f"导入: {report['success']} 成功, "
                        f"{report['skipped_duplicates']} 跳过(重复), "
                        f"{report['failed']} 失败"
                    )
                    st.rerun()

    # --- 搜索筛选栏 ---
    with st.container(border=True):
        st.caption("🔍 搜索筛选")
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        with fc1:
            search_math_type = st.selectbox("数学类别", ["全部"] + MATH_TYPES, key="qb_mt")
        with fc2:
            # 宇哥八套卷显示"卷号"，真题显示"年份"
            if search_math_type == "26宇哥八套卷":
                volumes = db.get_volumes("26宇哥八套卷")
                vol_opts = ["全部"] + volumes if volumes else ["全部", "第一套"]
                search_year = st.selectbox("卷号", vol_opts, key="qb_year")
                year_is_volume = True
            else:
                existing_years = stats.get("years_covered", [])
                year_opts = ["全部"] + [str(y) for y in sorted(existing_years, reverse=True)]
                search_year = st.selectbox("年份", year_opts, key="qb_year")
                year_is_volume = False
        with fc3:
            search_qtype = st.selectbox("题型", ["全部"] + QUESTION_TYPES, key="qb_qtype")
        with fc4:
            # 使用缓存的标签
            all_tags = db.get_all_tags()
            search_kp = st.selectbox("知识点", ["全部"] + all_tags if all_tags else ["全部"], key="qb_kp")
        with fc5:
            search_diff = st.selectbox("难度", ["全部"] + DIFFICULTY_LEVELS, key="qb_diff")

        search_kw = st.text_input("关键词搜索", placeholder="输入题目关键词...")

    # --- 构建搜索过滤条件 ---
    filters = {"limit": 50}
    if search_math_type != "全部":
        filters["math_type"] = search_math_type
    if search_year != "全部":
        if year_is_volume:
            filters["volume"] = search_year
        else:
            filters["year"] = int(search_year)
    if search_qtype != "全部":
        filters["question_type"] = search_qtype
    if search_kp != "全部":
        filters["knowledge_point"] = search_kp
    if search_diff != "全部":
        filters["difficulty"] = search_diff
    if search_kw:
        filters["keyword"] = search_kw

    # --- 执行搜索（带缓存）---
    cache_key = get_search_cache_key(filters)
    cache_time_key = f"search_cache_time_{cache_key}"
    now = time.time()
    
    # 检查缓存
    if (f"search_cache_{cache_key}" in st.session_state and 
        st.session_state.get(cache_time_key, 0) + SEARCH_CACHE_TTL > now):
        results = st.session_state[f"search_cache_{cache_key}"]
    else:
        # 缓存过期，重新搜索
        results = db.search(**filters)
        st.session_state[f"search_cache_{cache_key}"] = results
        st.session_state[cache_time_key] = now

    # 处理 results 为 None 的情况
    if results is None:
        results = []

    st.caption(f"找到 {len(results)} 道题")

    if not results:
        st.info("未找到匹配的题目。尝试调整筛选条件。")
    else:
        # --- 分页渲染 ---
        items_per_page = 10
        total_pages = max(1, (len(results) + items_per_page - 1) // items_per_page)

        if "qb_current_page" not in st.session_state:
            st.session_state.qb_current_page = 1

        # 计算当前页的题目范围
        start_idx = (st.session_state.qb_current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(results))
        current_page_results = results[start_idx:end_idx]

        # 渲染当前页的题目
        for q in current_page_results:
            qid = q["question_id"]
            editing = st.session_state.get("editing_question")

            if editing == qid:
                with st.container(border=True):
                    st.caption(f"编辑 {qid}")
                    edit_value = q.get("question", "")
                    opts = q.get("options") or {}
                    if opts:
                        has_inline = any(
                            ('(' + l + ')' in edit_value)
                            for l in 'ABCD' if l in opts
                        )
                        if not has_inline:
                            parts = []
                            for l in 'ABCD':
                                if l in opts:
                                    parts.append('$(' + l + ')$ ' + opts[l])
                            if parts:
                                edit_value = edit_value.rstrip() + ' ' + ' '.join(parts)
                    new_text = st.text_area(
                        "编辑 LaTeX 源码",
                        value=edit_value,
                        height=200,
                        key=f"edit_text_{qid}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("💾 保存修改", key=f"save_{qid}", type="primary"):
                            from exam_parser.simple_parser import parse_latex_question
                            parsed = parse_latex_question(new_text)
                            db.update(qid, parsed)
                            st.session_state.editing_question = None
                            # 正确清除缓存：删除缓存键而不是设为 None
                            cache_key_to_delete = f"search_cache_{cache_key}"
                            if cache_key_to_delete in st.session_state:
                                del st.session_state[cache_key_to_delete]
                            time_key_to_delete = f"search_cache_time_{cache_key}"
                            if time_key_to_delete in st.session_state:
                                del st.session_state[time_key_to_delete]
                            st.rerun()
                    with c2:
                        if st.button("↩️ 取消", key=f"cancel_{qid}"):
                            st.session_state.editing_question = None
                            st.rerun()
                    st.caption("渲染预览")
                    preview_q = dict(q)
                    from exam_parser.simple_parser import parse_latex_question
                    parsed = parse_latex_question(new_text)
                    preview_q.update(parsed)
                    from question_ast import parse_legacy
                    ast_preview = parse_legacy(preview_q)
                    render_question(ast_preview)
            else:
                render_question(q)

        # 分页控件（题目下方）
        st.caption(f"显示 {start_idx + 1}-{end_idx} / {len(results)} 题")
        if total_pages > 1:
            pc1, pc2, pc3 = st.columns([1, 2, 1])
            with pc2:
                st.session_state.qb_current_page = st.slider(
                    "页码", 1, total_pages, st.session_state.qb_current_page,
                    key="qb_page_slider"
                )

    # --- 导入区域 ---
    st.markdown("---")
    with st.expander("📥 导入题目（管理员）", expanded=False):
        st.caption("支持格式：LaTeX 整卷 / JSON / 文本粘贴 / 图片 OCR（需 Tesseract）")
        import_tab1, import_tab2, import_tab3, import_tab4, import_tab5, import_tab6 = st.tabs([
            "📄 上传JSON文件", "📝 文本粘贴", "🌐 在线获取", "📋 粘贴网页HTML",
            "✏️ 手动添加", "📐 LaTeX整卷",
        ])

        with import_tab1:
            uploaded = st.file_uploader("选择 JSON 文件", type=["json"], key="import_json")
            if uploaded:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
                    f.write(uploaded.read())
                    tmp_path = f.name
                importer = QuestionImporter(db)
                report = importer.import_json(tmp_path)
                st.success(f"导入完成: 成功 {report['success']} 题, "
                           f"跳过重复 {report['skipped_duplicates']}, "
                           f"失败 {report['failed']}")
                if report["warnings"]:
                    st.warning(f"警告: {'; '.join(report['warnings'][:5])}")
                # 清除缓存
                invalidate_search_cache()
                st.rerun()

        with import_tab2:
            import json
            json_text = st.text_area(
                "粘贴 JSON 格式题目数据",
                placeholder='{"questions": [{"year": 2024, "category": "数学一", ...}]}',
                height=200,
            )
            if st.button("📥 导入", disabled=not json_text):
                try:
                    data = json.loads(json_text)
                    importer = QuestionImporter(db)
                    report = importer.import_dict(data if isinstance(data, list) else [data])
                    st.success(f"导入完成: 成功 {report['success']}, 跳过 {report['skipped_duplicates']}, 失败 {report['failed']}")
                    invalidate_search_cache()
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"JSON 格式错误: {e}")

        with import_tab3:
            st.caption("从公开教育网站自动获取题目")
            st.warning(
                "⚠️ 爬虫仅访问公开可用的网页内容，请求间隔≥3秒。"
                "部分网站可能有反爬机制，如失败请改用「粘贴网页HTML」。",
                icon="⚠️"
            )
            scrape_url = st.text_input(
                "网页URL",
                placeholder="https://example.com/kaoyan/math/2024-1",
                key="scrape_url",
            )
            sc1, sc2 = st.columns(2)
            scrape_mt = sc1.selectbox("数学类别", MATH_TYPES, key="scrape_mt")
            scrape_year = sc2.number_input("年份", 1987, 2026, 2024, key="scrape_year")

            if st.button("🌐 开始爬取", disabled=not scrape_url.strip()):
                with st.spinner("正在获取网页内容（可能需要几秒）..."):
                    from scrapers import PublicEduScraper
                    scraper = PublicEduScraper()
                    questions = scraper.scrape_from_url(
                        scrape_url.strip(),
                        math_type=scrape_mt,
                        year=scrape_year,
                    )
                    if questions:
                        importer = QuestionImporter(db)
                        report = importer.import_dict(questions)
                        st.success(
                            f"爬取完成: 解析出 {len(questions)} 题, "
                            f"导入成功 {report['success']}, "
                            f"跳过重复 {report['skipped_duplicates']}, "
                            f"失败 {report['failed']}"
                        )
                        if report["warnings"]:
                            st.warning(f"数据质量问题: {'; '.join(report['warnings'][:5])}")
                        invalidate_search_cache()
                        st.rerun()
                    else:
                        st.error(
                            "未能从该页面解析出题目。请检查URL是否正确，"
                            "或改用「粘贴网页HTML」方式手动提取。"
                        )

        with import_tab4:
            st.caption("从任意教育网站复制HTML内容，粘贴后自动解析")
            st.info(
                "📌 使用方法：在浏览器中打开目标网页 → 右键 → 查看页面源代码 → "
                "复制关键部分 → 粘贴到下方 → 选择数学类别和年份 → 点击解析",
                icon="📌"
            )
            scrape_html = st.text_area(
                "粘贴网页HTML内容",
                placeholder="<div class=\"question\">...</div>",
                height=200,
                key="scrape_html",
            )
            sc3, sc4 = st.columns(2)
            paste_mt = sc3.selectbox("数学类别", MATH_TYPES, key="paste_mt")
            paste_year = sc4.number_input("年份", 1987, 2026, 2024, key="paste_year")

            if st.button("🔍 解析HTML", disabled=not scrape_html.strip()):
                with st.spinner("正在解析HTML..."):
                    from scrapers import ManualHTMLScraper
                    manual = ManualHTMLScraper()
                    questions = manual.paste_and_parse(
                        scrape_html, math_type=paste_mt, year=paste_year
                    )
                    if questions:
                        importer = QuestionImporter(db)
                        report = importer.import_dict(questions)
                        st.success(
                            f"解析完成: 提取 {len(questions)} 题, "
                            f"导入成功 {report['success']}, "
                            f"跳过重复 {report['skipped_duplicates']}, "
                            f"失败 {report['failed']}"
                        )
                        with st.expander("📋 解析结果预览", expanded=False):
                            for q in questions[:3]:
                                st.caption(
                                    f"[{q.get('question_type', '?')}] "
                                    f"{' '.join(q.get('knowledge_points', []))} "
                                    f"| {q.get('difficulty', '?')}"
                                )
                                st.markdown(q.get("question", "")[:200])
                                st.divider()
                        invalidate_search_cache()
                        st.rerun()
                    else:
                        st.error(
                            "未能从HTML中提取题目。请确认：\n"
                            "1. 粘贴的内容包含题目区块\n"
                            "2. HTML结构中有题号标识（如 '1.', '（1）'）\n"
                            "3. 内容不是JavaScript动态加载的"
                        )

        with import_tab5:
            st.caption("直接输入 LaTeX 代码添加单道题目，自动规范化格式后入库。")
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                new_year = st.number_input("年份", 1987, 2026, 2024, key="new_year")
            with mc2:
                new_type = st.selectbox("题型", QUESTION_TYPES, key="new_type")
            with mc3:
                new_diff = st.selectbox("难度", DIFFICULTY_LEVELS, key="new_diff")
            with mc4:
                new_kp = st.selectbox("知识点", sum(KNOWLEDGE_POINTS.values(), []), key="new_kp")

            new_question = st.text_area(
                "题目内容（LaTeX 源码）",
                height=200,
                key="new_question_text",
                placeholder="输入题目 LaTeX 代码，如：\n已知函数 $f(x) = \\int\\limits_{0}^{x} e^{t^2} \\sin t \\,\\mathrm{d}t$，则 $f'(0) = $",
                help="使用 $...$ 包裹行内公式，$$...$$ 包裹独立公式",
            )
            new_answer = st.text_area(
                "标准答案（LaTeX 源码）",
                height=80,
                key="new_answer_text",
                placeholder="输入答案，如：\n$0$",
            )

            # 规范化函数
            def normalize_latex_style(text):
                return text.strip()

            new_options = {}
            new_difficulty = new_diff

            if new_question:
                st.caption("📐 题目渲染预览:")
                preview_q = {"question": new_question, "question_type": new_type,
                             "options": new_options, "standard_answer": new_answer,
                             "difficulty": new_difficulty, "knowledge_points": [new_kp]}
                render_question(preview_q)


            if st.button("💾 添加到题库", type="primary", use_container_width=True,
                         disabled=not new_question.strip()):
                clean_q = normalize_latex_style(new_question.strip())
                clean_a = normalize_latex_style(new_answer.strip()) if new_answer.strip() else ""

                new_q = {
                    "year": new_year,
                    "category": "数学一",
                    "question_type": new_type,
                    "knowledge_points": [new_kp] if new_kp != "自动识别" else [],
                    "difficulty": new_diff,
                    "score": {"选择题": 5, "填空题": 5, "解答题": 10, "证明题": 12}.get(new_type, 10),
                    "question": clean_q,
                    "standard_answer": clean_a,
                    "solution_steps": [],
                    "common_mistakes": [],
                    "tags": [],
                    "source": "manual_input",
                }

                result = db.insert(new_q)
                if result["success"]:
                    st.success(f"✅ 已添加: {result['question_id']}")
                    st.toast("题目已入库")
                    invalidate_search_cache()
                    st.rerun()
                else:
                    st.error(f"添加失败: {'; '.join(result.get('warnings', ['未知错误']))}")

        with import_tab6:
            st.caption(
                "粘贴或上传完整试卷 LaTeX 源码（含 \\documentclass 与 \\begin{document}），"
                "系统将自动拆题并批量入库。"
            )
            st.info(
                "推荐卷面结构：\\section{一、选择题} + \\begin{enumerate} + \\item；"
                "或在正文中使用「一、选择题」与「1.」题号。"
                "公式请使用 $...$ 或 \\[...\\]。",
                icon="ℹ️",
            )
            lc1, lc2 = st.columns(2)
            with lc1:
                latex_year = st.number_input("年份", 1987, 2026, 2024, key="latex_import_year")
            with lc2:
                latex_mt = st.selectbox("数学类别", MATH_TYPES, key="latex_import_mt")

            latex_upload = st.file_uploader(
                "上传 .tex 文件", type=["tex"], key="latex_import_file",
            )
            latex_paste = st.text_area(
                "或粘贴 LaTeX 源码",
                height=280,
                key="latex_import_paste",
                placeholder=(
                    "\\documentclass{article}\n"
                    "\\begin{document}\n"
                    "\\section{一、选择题}\n"
                    "\\begin{enumerate}\n"
                    "\\item 已知 $f(x)=\\cdots$\n"
                    "\\end{enumerate}\n"
                    "\\end{document}"
                ),
            )

            latex_source = ""
            if latex_upload is not None:
                latex_source = latex_upload.read().decode("utf-8", errors="replace")
            elif latex_paste and latex_paste.strip():
                latex_source = latex_paste.strip()

            col_preview, col_import = st.columns(2)
            with col_preview:
                preview_clicked = st.button(
                    "🔍 解析预览", use_container_width=True,
                    disabled=not latex_source,
                )
            with col_import:
                import_clicked = st.button(
                    "📥 导入题库", type="primary", use_container_width=True,
                    disabled=not latex_source,
                )

            if preview_clicked and latex_source:
                with st.spinner("正在解析 LaTeX 试卷..."):
                    try:
                        from exam_parser import LatexExamParser
                        parser = LatexExamParser()
                        norm, norm_report = parser.normalize_latex_source(latex_source)
                        result = parser.parse(
                            latex_source,
                            year=int(latex_year),
                            math_type=latex_mt,
                        )
                        st.session_state.latex_parse_preview = {
                            "result": result,
                            "norm_report": norm_report,
                            "normalized_head": norm[:1200],
                        }
                    except Exception as e:
                        st.error(f"解析失败: {e}")

            preview = st.session_state.get("latex_parse_preview")
            if preview and latex_source:
                result = preview["result"]
                norm_report = preview["norm_report"]
                st.success(
                    f"识别到 **{result.total_questions}** 道题 "
                    f"（章节 {norm_report.section_count} 个，\\item {norm_report.item_count} 个）"
                )
                if result.warnings:
                    with st.expander("⚠️ 解析提示", expanded=False):
                        for w in result.warnings[:12]:
                            st.caption(f"• {w}")
                if norm_report.warnings:
                    for w in norm_report.warnings:
                        st.warning(w)
                with st.expander("📋 规范化文本预览（前 1200 字）", expanded=False):
                    st.code(preview.get("normalized_head", ""), language="markdown")
                if result.questions:
                    with st.expander("📝 题目预览（前 3 道）", expanded=True):
                        for q in result.questions[:3]:
                            st.caption(
                                f"[{q.get('question_type', '?')}] "
                                f"{' / '.join(q.get('knowledge_points', [])[:3])}"
                            )
                            st.markdown((q.get("question") or "")[:400])
                            if q.get("standard_answer"):
                                st.caption("答案片段: " + str(q["standard_answer"])[:120])
                            st.divider()

            if import_clicked and latex_source:
                with st.spinner("正在拆题并写入题库..."):
                    try:
                        from exam_parser import LatexExamParser
                        result = LatexExamParser().parse(
                            latex_source,
                            year=int(latex_year),
                            math_type=latex_mt,
                        )
                        if result.total_questions == 0:
                            st.error(
                                "未能从 LaTeX 中拆出题目。请先点「解析预览」查看提示，"
                                "或调整卷面章节/\\item 结构后重试。"
                            )
                            if result.errors:
                                st.code("\n".join(result.errors[:5]))
                        else:
                            importer = QuestionImporter(db)
                            report = importer.import_dict(result.questions)
                            st.success(
                                f"导入完成: 成功 {report['success']} 题, "
                                f"跳过重复 {report['skipped_duplicates']}, "
                                f"失败 {report['failed']}"
                            )
                            if report.get("warnings"):
                                st.warning("; ".join(report["warnings"][:5]))
                            st.session_state.pop("latex_parse_preview", None)
                            invalidate_search_cache()
                            st.rerun()
                    except Exception as e:
                        st.error(f"导入失败: {e}")

    # --- 数据库统计 ---
    st.markdown("---")
    st.subheader("📊 数据库统计")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("总题数", stats["total"])
    sc2.metric("涵盖年份", len(stats.get("years_covered", [])))
    sc3.metric("知识点标签", stats.get("knowledge_points_covered", 0))

    if stats.get("missing_data"):
        st.warning(f"缺失数据: {len(stats['missing_data'])} 处")
    if stats.get("pending_review"):
        st.info(f"待审核: {len(stats['pending_review'])} 题")


def invalidate_search_cache():
    """清除所有搜索缓存"""
    keys_to_remove = []
    for key in st.session_state:
        if key.startswith("search_cache_"):
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del st.session_state[key]