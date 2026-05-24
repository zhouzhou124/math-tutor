# UI Architecture

Last updated: 2026-05-25 (P12-3)

---

## 1. 项目 UI 总览

本项目是基于 **Streamlit** 构建的考研数学智能辅导系统，采用单页应用 (SPA) 架构，通过 `st.session_state["page"]` 实现页面路由切换。

入口文件：`app.py` → `views/main_page.py`（路由中枢 + 侧边栏导航）

页面分为两组：
- **学生页面**（7 个）：Dashboard / Practice / Grading / Question Bank / Mistakes / Profile / Settings
- **管理员页面**（6 个 Tab）：Admin Dashboard

---

## 2. 页面路由体系

路由逻辑在 `views/main_page.py`，通过 `st.session_state["page"]` 值分发到不同渲染函数。

侧边栏导航由 `main_page.py` 的 `_render_sidebar()` 渲染，根据用户角色（student / admin）显示不同菜单项。

页面切换方式：
- 点击侧边栏菜单 → 设置 `st.session_state["page"]` → `st.rerun()`
- 页面内按钮跳转（如"前往刷题"）→ 同样设置 page 值 → `st.rerun()`
- 移动端底部导航栏 → `views/mobile.py` 渲染

---

## 3. UI Design System

文件：`views/ui/theme.py`

### 3.1 主题注入

`inject_app_theme()` 在 `main_page.py` 中调用一次，注入全局 CSS 变量和组件样式。

CSS 变量体系：

| 变量 | 值 | 用途 |
|------|-----|------|
| `--primary` | `#2563eb` | 主色调 |
| `--purple` | `#7c3aed` | 渐变辅助色 |
| `--success` | `#16a34a` | 正确/掌握 |
| `--warning` | `#f59e0b` | 警告/需复习 |
| `--danger` | `#dc2626` | 错误/高优先级 |
| `--radius-lg` | `18px` | 卡片圆角 |
| `--shadow-soft` | `0 8px 24px rgba(...)` | 卡片阴影 |

### 3.2 组件目录

| 组件 | 函数 | 用途 |
|------|------|------|
| 页面标题 | `render_page_header(title, subtitle, icon)` | 统一页面标题 + 副标题 |
| 流程步骤 | `render_flow_steps(steps, active)` | 水平步骤指示器 |
| 题目列表卡片 | `render_question_list_card(q, show_actions)` | 题库/搜索结果卡片 |
| 错题卡片 | `render_mistake_card(record)` | 严重度颜色左边框卡片 |

### 3.3 CSS 类

| 类名 | 用途 |
|------|------|
| `.app-card` | 主内容卡片（18px padding, lg radius） |
| `.app-card-compact` | 列表项卡片（14px padding, md radius） |
| `.app-chip` / `.app-chip-blue/green/orange/red/purple` | 标签/徽章 |
| `.mistake-card-hot` | 红色左边框（高优先级错误） |
| `.mistake-card-warm` | 橙色左边框（需复习） |
| `.mistake-card-cool` | 蓝色左边框（轻微错误） |
| `.mistake-card-done` | 绿色左边框（已掌握） |

### 3.4 安全规则

1. 所有用户/AI 生成内容在 HTML 中必须使用 `html.escape()`
2. `render_question_list_card` 和 `render_mistake_card` 自动转义所有字段
3. 禁止在 `unsafe_allow_html=True` 中使用未转义的用户输入

### 3.5 新增页面规范

1. 导入 `render_page_header` from `views.ui.theme`
2. 页面顶部调用 `render_page_header(title, subtitle, icon)`
3. 使用 `.app-card` / `.app-card-compact` 包裹卡片
4. 使用 `.app-chip-*` 渲染标签
5. 所有动态内容用 `html.escape` 转义
6. 在 375px 视口测试移动端

---

## 4. 核心页面

### 4.1 Dashboard（仪表盘）

文件：`views/dashboard_page.py`

| 区域 | 内容 |
|------|------|
| 欢迎横幅 | 渐变紫色背景，显示用户名 |
| 三个指标卡 | 已完成题目数 / 正确率 / 连续学习天数 |
| 薄弱点分析 | 列出知识薄弱项（⚠️ 警告样式） |
| 推荐练习 | "专项训练" 和 "错题回顾" 两个按钮 |
| 学习进度 | 各章节正确率柱状图 (`st.bar_chart`) |
| 最近错题 | 最近 5 条错题摘要 |

数据来源：`DashboardService`，带 60 秒 session 级缓存。

### 4.2 Practice（智能刷题）

文件：`views/practice_page.py`

核心交互流程：

```
选题 → 查看题目 → 输入作答 → 提交批改 → 查看结果
```

- **题目展示**：使用 `render_question()` 渲染 LaTeX 题目
- **选择题**：选项按钮横排，点击选中高亮（primary 样式），选项内容支持 LaTeX
- **作答输入**：左右两栏布局
  - 左栏：文本输入区（支持 `$...$` LaTeX）
  - 右栏：拍照上传（PNG/JPG/JPEG）+ OCR 识别建议面板
- **OCR 引擎状态提示**：自动检测 Mathpix / pix2tex 可用性
- **提交批改**：文本+图片合并后交给 `GradingOrchestrator`

### 4.3 Grading（AI 批改）

文件：`views/grading_page.py`

**已完成服务层拆分**（P3/P8），当前架构：

| 模块 | 职责 |
|------|------|
| `views/grading_page.py` | 仅负责 UI、session_state、Streamlit polling、thin wrappers |
| `services/grading_orchestrator.py` | 批改全流程编排：标准答案 → Engine A/B/C → 诊断 → 错题记录 |
| `services/solution_service.py` | 标准答案生成：缓存命中 / AI 展开 / SolverAgent 回退 |
| `services/grading_task_runner.py` | 后台任务提交、SQLite 持久化、结果恢复 |
| `services/grading_adapter.py` | 数据契约归一化：grading_result / solution / error_record |
| `services/grading_text_tools.py` | 选择题答案归一化、题目预览提取（纯函数） |
| `services/solution_text_tools.py` | 解答文本解析、验证、canonical 持久化（纯函数 + DB） |
| `services/latex_text_tools.py` | Unicode/ASCII 数学表达式包裹、LaTeX 括号修复（纯函数） |

**输入区域**：
- 题库选题 或 手动输入题目
- 文本作答 + 拍照上传（同刷题页）
- 选择题选项选择

**批改流程**（后台线程执行）：
```
准备题目 → 生成标准答案 → AI批改评分 → 诊断分析 → 完成结果
```

**结果展示**：
- 分数卡片（`render_score_card`）
- 知识点卡片（`render_knowledge_points`）
- 诊断分析卡片
- 逐步骤对比卡片
- 标准解法卡片
- 改进建议卡片

**特色功能**：
- **后台批改**：`ThreadPoolExecutor` + SQLite 任务存储（`storage/grading_tasks.db`），支持浏览器关闭后恢复结果
- **Unicode/ASCII 数学自动包裹**：`latex_text_tools.wrap_unicode_math()` 和 `wrap_ascii_math()` 将裸数学符号包裹为 `$...$` 供 KaTeX 渲染
- **LaTeX 修复**：`latex_text_tools.fix_latex_braces()` 修复 LLM 生成的常见括号错误
- **Canonical Solution Pool**：每道题支持多种解法（换元法、定义法、几何法等），新解法追加而非覆盖

### 4.4 Question Bank（真题库）

文件：`views/question_bank_page.py`

**卡片式题目列表**：
- 年份 · 题型 · 难度 标签
- 知识点 chip
- 题目预览（纯文本截断）
- 完整题目 LaTeX 渲染
- 三按钮操作栏：✏️练习 / 🤖批改 / 📖解析
- 关键词搜索常驻，高级筛选折叠

**搜索筛选**：科目(数学一/二/三)、题型(选择/填空/解答)、难度、知识点

**导入区域**（折叠面板，6 个 Tab）：
- 📄 上传 JSON / 📝 文本粘贴 / 🌐 在线获取 / 📋 粘贴 HTML / ✏️ 手动添加 / 📐 LaTeX 整卷

**空库引导**：检测 `storage/` 下的 Markdown 真题文件，一键导入 + 增强解析引擎

详细架构见 [question_bank_architecture.md](question_bank_architecture.md)。

### 4.5 Mistakes（错题本）

文件：`views/mistakes_page.py`

**快捷筛选 Chip 按钮**：`全部` | `今日优先` | `低分错题` | `已掌握` | `已归档`

**高级筛选**（折叠）：科目 / 错误类型 / 难度

**严重度卡片**（P12-2/P12-3 升级）：

| 严重度 | 条件 | 左边框颜色 |
|--------|------|-----------|
| 🔥 高优先级 | 得分 < 40% | 红色 |
| ⚠️ 需复习 | 得分 < 70% | 橙色 |
| 💡 轻微错误 | 得分 < 90% | 蓝色 |
| ✅ 已掌握 | 得分 ≥ 90% | 绿色 |
| 👁 仅查看 | view_only 模式 | — |

**两层渲染策略**：

第一层：轻量卡片列表（`_render_record_lightweight`）
- 纯文本预览，不渲染 LaTeX（避免大量 KaTeX 渲染卡顿）
- 严重度颜色条 + 知识点标签
- 三个操作按钮：📋详情 / ✅掌握 / 📦归档

第二层：完整详情展开（`_render_record_full`）
- 只在点击"详情"时渲染，一次只展开一条
- 5 个区域：📋题目 / ✍️学生作答 / 📖标准答案 / 🔍批改详情 / 🏥诊断分析
- 底部操作：✅已掌握 / 📦归档 / 🔁重做

**统计面板**：4 个指标卡（错题总数 / 重复率 / 主要错误类型 / 高频错误章节）

**缓存**：30 秒 TTL session 级缓存，增删操作后精确失效

### 4.6 Profile（学习画像）

文件：`views/profile_page.py`

- **当前阶段**：基础薄弱 🔴 / 强化阶段 🔵 / 冲刺阶段 🟢
- **各章节正确率**：彩色进度条（红<40% / 橙<60% / 蓝<80% / 绿≥80%）
- **薄弱知识点**列表
- **错题类型分布**统计
- **复习建议**：由 `MemoryAgent` 生成个性化推荐

### 4.7 Settings（系统设置）

文件：`views/settings_page.py`

- **LLM Provider 管理**：
  - 多配置保存，一键切换
  - 预设服务商：DeepSeek / OpenAI / 通义千问 / Kimi / 智谱 / 小米MiMo
  - API Key 加密存储，15 天自动过期
  - 高级选项：Base URL / 模型名 / 协议(openai/anthropic)
- **连接测试**：验证 API Key 是否可用

### 4.8 Admin Dashboard（管理员后台）

文件：`views/admin_dashboard.py`

6 个 Tab 页：

| Tab | 功能 |
|-----|------|
| 概览统计 | 总用户数 / 活跃用户 / 错题记录 |
| 用户管理 | 用户列表、角色管理 |
| AI 批改监控 | 批改任务状态、耗时统计 |
| 题库状态 | 题目数量、分布统计 |
| 数据回放 | 历史批改记录回放 |
| 题库管理 | 题目增删改查 |

---

## 5. 移动端适配

文件：`views/mobile.py`

- **响应式 CSS**：`@media (max-width: 768px)` 断点
  - 隐藏侧边栏，改为底部导航栏
  - 标题/字体缩小（1.38rem）
  - 多列布局强制堆叠
  - 防下拉刷新（`overscroll-behavior: contain`）
  - 按钮最小高度 48px，宽度 100%
  - `.block-container` 底部 padding 6.8rem 清除底部导航
- **底部导航栏**：固定在屏幕底部，5 个图标按钮
- **批改页特殊处理**：`set_grading_active()` 控制底部导航显隐

---

## 6. 共享组件

### views/components/

| 组件 | 文件 | 用途 |
|------|------|------|
| 批改进度 | `components/grading_progress.py` | 5 阶段批改进度条（带渐变条纹动画） |
| 步骤卡片 | `components/step_card.py` | 逐步骤评分展示 |

### renderers/

| 组件 | 文件 | 用途 |
|------|------|------|
| 题目渲染 | `question_renderer.py` | 题型感知分发（选择/填空/解答/证明） |
| 选择题渲染 | `choice_renderer.py` | 选择题选项 + LaTeX |
| 填空题渲染 | `fill_renderer.py` | 填空题下划线 + LaTeX |
| 解答题渲染 | `solution_renderer.py` | 解题步骤渲染 |
| 证明题渲染 | `proof_renderer.py` | 证明题专用 |
| 元数据渲染 | `metadata_renderer.py` | 题目元数据标签 |
| 批改结果渲染 | `grading_renderer.py` | 基础批改结果卡片 |
| 批改结果卡片 | `components/grading_result.py` | 完整批改结果卡片组（分数/知识点/诊断/步骤/解法/建议） |
| 题目卡片 | `components/question_card.py` | 题目列表卡片 |
| 题目元数据 | `components/question_meta.py` | 元数据标签 |
| 题目操作 | `components/question_actions.py` | 练习/批改/解析按钮 |
| 确认对话框 | `components/confirm_dialog.py` | 删除确认弹窗 |

---

## 7. 后台任务与流式生成

### 7.1 异步批改架构（P9 流式生成体验）

```
用户点击"开始批改"
  → _submit_grading_async()
    → grading_task_runner.submit_grading_async()
      → create_task() 写入 SQLite
      → ThreadPoolExecutor 提交后台线程
        → run_grading_bg()
          → execute_grading() + stream_callback
            → LLM stream=True 增量输出
            → stream_callback → update_task_stream() 写入 SQLite
  → 设置 pending_task_id
  → st.rerun() 进入轮询模式
```

### 7.2 轮询展示

`grading_page.py` 每 0.5 秒（有流式内容时）或 1-2 秒（无流式内容时）轮询：

```python
task = get_task(pending_task_id)
if task["status"] == "processing":
    stream_answer = task.get("stream_answer", "")
    if stream_answer:
        # 保守渲染：未闭合 LaTeX 时不渲染尾部，避免公式闪烁
        _dollar_count = stream_answer.count('$') - stream_answer.count('$$') * 2
        if _dollar_count % 2 != 0:
            # 找到最后一个未闭合 $，拆分为安全部分 + 悬挂部分
            safe_render(safe_part)
            st.text(dangling[:500])
        else:
            safe_render(stream_answer)
    # 进度条 + 阶段指示
    render_progress(...)
    time.sleep(0.5)
    st.rerun()
elif task["status"] == "completed":
    _restore_results_to_session(task)
    st.rerun()
```

### 7.3 进度条（P9 流式生成优先）

批改等待期间，优先展示流式生成的解答文本（P9 streaming），进度条作为辅助指示。

`views/components/grading_progress.py` — 5 阶段进度条（辅助）：

| 阶段 | 名称 | 对应时间 |
|------|------|---------|
| prepare | 准备题目 | 0-10s |
| solution | 标准答案 | 10-25s |
| grading | AI批改 | 25-50s |
| diagnosis | 诊断分析 | 50-75s |
| finalize | 完成结果 | 75s+ |

进度计算：`estimate_smooth_progress()` 基于已用时间和预期总时间，平滑插值，最大 97%（完成后跳 100%）。

### 7.4 任务恢复

- 浏览器刷新后，`get_recent_task(user_id)` 自动恢复进行中/最近完成的任务
- 服务器重启时，`init_db()` 将超过 10 分钟的 processing 任务标记为 failed
- 超时保护：30 分钟未完成的任务自动 fail

---

## 8. LaTeX / 结构化答案渲染

### 8.1 渲染分层

已完成分层（P8）：

| 层 | 文件 | 职责 |
|----|------|------|
| 纯函数层 | `latex_utils.py` | split、sanitize、tag 拆分、display 判断、validate |
| Streamlit 渲染层 | `renderers/streamlit_latex_renderer.py` | `st.latex()` / `st.markdown()` 渲染 |
| 移动端层 | `views/mobile.py` | KaTeX 横滑与响应式样式 |

### 8.2 LaTeX 渲染管线

```
AI output / stored question
  → normalize_latex_style()       light normalization (whitespace, delimiters)
  → wrap_unicode_math()           wrap Unicode math chars (π, ≤, →, Δ)
  → wrap_ascii_math()             wrap ASCII math (B^2=E, \frac, \int)
  → fix_latex_braces()            fix LLM brace errors (\frac{xx{yy} → \frac{xx}{yy})
  → split_latex_text()            segment into text/inline_math/display_math
  → render_ast / render_structured_safe
```

层边界：
- **normalize**: 仅轻量格式化，不做分段，不做复杂修复
- **split**: 仅分段，不做语义改写
- **sanitize**: 仅 `st.latex()` 前的 token 安全处理
- **render**: 仅布局，不修改内容

### 8.3 标准解法渲染管线（P6）

```
LLM Markdown / Structured text
  → normalize_solution_for_render()
      ├─ normalize_latex_style()
      ├─ wrap_unicode_math()
      ├─ wrap_ascii_math()
      └─ fix_latex_braces()
  → from_legacy_text()            build _structured dict
  → polish_solution()             clean leading punct, drop orphans, merge text, add periods
  → render_structured_safe()      validate → iterate steps
      └─ _render_block_latex()    extract \tag, side-by-side or below layout
```

**Tag 渲染策略**：

| 公式 | 布局 |
|------|------|
| 短公式（<70 字符，单行） | `st.columns` 左右并排，tag 在右 |
| 长公式（>70 字符），含 `aligned`、`\\` | tag 在公式下方，右对齐 |

**Polisher 规则**：

| 规则 | 效果 |
|------|------|
| `strip_leading_punctuation()` | `，化简得` → `化简得` |
| `is_punctuation_only()` | `。` block → 丢弃 |
| `is_orphan_formula_number()` | `(1)` / `。(1)` → 丢弃（tag 在 LaTeX 中） |
| `strip_bullet_prefix()` | `• 代入` → `代入` |
| `merge_adjacent_text_blocks()` | `"代入"` + `"化简得"` → `"代入，化简得"` |
| `ensure_sentence_period()` | `其中 E1 为常数` → `其中 E1 为常数。` |

---

## 9. 页面流转图

```
登录 ──→ 仪表盘 ──→ 智能刷题 ──→ AI批改
              │          ↑            │
              ├→ 真题库 ─┘            │
              ├→ 错题本 ←─────────────┘
              ├→ 学习画像
              └→ 系统设置
```

---

## 10. 当前架构边界

依赖方向（由 `tests/test_architecture_boundaries.py` 强制执行）：

```
views / renderers
    ↓
services
    ↓
agents / repository / utils
    ↓
domain / pure functions
```

禁止：
- `services → views`
- `agents → views`
- `services / agents / repository → streamlit`

已完成的拆分：
- `grading_page.py` 的纯函数已提取到 `services/grading_text_tools.py`、`services/solution_text_tools.py`、`services/latex_text_tools.py`
- `latex_utils.py` 的 Streamlit 渲染已提取到 `renderers/streamlit_latex_renderer.py`
- 渲染组件已统一到 `renderers/` 目录

已解决的遗留问题（P8）：
- `grading_page.py` 的纯函数已迁移到 `services/latex_text_tools.py`，页面保留 thin wrappers
- `verifier_agent.py` 的 `render_verification_report()` 已迁移到 `renderers/components/verification_report.py`

---

## 11. 后续 UI 优化方向

1. **消除 grading_page.py 中的本地纯函数副本**：统一使用 `services/latex_text_tools.py` 导入
2. **VerifierAgent 渲染逻辑分离**：将 `render_verification_report()` 移到 `renderers/`
3. **renderers/ 目录统一**：`rendering/` 目录仍在合并中
4. **移动端体验优化**：长公式横滑、底部导航交互细节
5. **测试覆盖**：补充页面级集成测试
