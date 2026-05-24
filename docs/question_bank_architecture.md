# Question Bank & Error Notebook Architecture

Last updated: 2026-05-25 (P12-3)

---

# Part I: 真题库系统

## 1. 整体架构

```
UI 层  views/question_bank_page.py
  ↓
QuestionDB  (database/question_db.py)       ← 核心引擎：CRUD / 搜索 / 索引 / 去重
  ↓
QuestionImporter  (database/importer.py)    ← 导入管道：解析 → 校验 → 去重 → 入库
  ↓
ExamParserPipeline  (exam_parser/)          ← 增强解析：LaTeX修复 → 分割 → 匹配 → 标注
  ↓
文件存储  storage/questions/{exams|simulations1|simulations2}/{qid}.json
  ↓
全局索引  storage/questions/_index.json
```

---

## 2. 存储设计

### 2.1 三级分类体系

```
一级: 数学类别 (数学一 / 数学二 / 数学三)
  └─ 二级: 年份 (1987-至今) 或 卷号 (宇哥八套卷-卷一)
       └─ 三级: 题型 (选择题 / 填空题 / 解答题 / 证明题)
```

### 2.2 目录结构

| 目录 | 内容 | ID 格式 |
|------|------|---------|
| `storage/questions/exams/` | 历年真题 | `2024-数一-016` |
| `storage/questions/simulations1/` | 宇哥八套卷 | `数学一-宇哥八套卷-卷一-001` |
| `storage/questions/simulations2/` | 合工大超越 | `数学一-合工大超越-卷一-001` |

每道题一个 JSON 文件，全局索引 `_index.json` 维护三级分类树 + 知识点索引 + 难度索引。

---

## 3. 四层分离原则

文件：`database/question_schema.py`

```
Raw Data (raw_question_text / raw_answer_text)  ← 一旦写入，只读，永不覆盖
  ↓
Parser (纯函数，按需计算，不持久化)
  ↓
Renderer (纯函数，按需计算，不持久化)
  ↓
Semantic IR (semantic_ir 字段)  ← 解释层，不触碰 Raw
```

核心规则：
- `set_raw_question()` / `set_raw_answer()` 是唯一写入原始文本的入口
- 同时写旧字段（`question` / `standard_answer`）做向后兼容
- 没有任何函数可以覆盖 `raw_*` 字段

---

## 4. 索引系统

`QuestionDB` 维护三个索引，搜索时采用 **索引交集优化**：

| 索引 | 结构 | 用途 |
|------|------|------|
| `categories` | `数学一 → 2024 → 选择题 → [id列表]` | 分类浏览 |
| `knowledge_index` | `极限 → [id列表]` | 知识点搜索（部分匹配） |
| `difficulty_index` | `中等 → [id列表]` | 难度筛选 |

搜索流程：先用最精确的索引缩小候选集，再加载候选题做精细过滤，避免全量扫描。有筛选条件时 `max_load=100000`，无筛选时 `limit*3` 采样。

---

## 5. 搜索能力

支持 7 种过滤条件：

| 过滤器 | 说明 | 索引加速 |
|--------|------|---------|
| `math_type` | 数学类别 | ✅ categories |
| `year` | 年份 | ✅ categories |
| `volume` | 卷号 | ✅ categories |
| `question_type` | 题型 | ✅ categories |
| `knowledge_point` | 知识点（部分匹配） | ✅ knowledge_index |
| `difficulty` | 难度 | ✅ difficulty_index |
| `keyword` | 题目内容关键词 | ❌ 全文搜索 |

---

## 6. 去重机制

插入时使用 `SequenceMatcher` 计算题目文本相似度，超过阈值则拒绝插入并返回已有题目 ID，避免同一道题被重复导入。

---

## 7. 导入管道

`QuestionImporter` 支持 **6 种导入方式**：

| 方式 | 入口 | 处理流程 |
|------|------|---------|
| JSON 文件上传 | `import_json()` | 直接解析 JSON |
| 文本粘贴 | `import_dict()` | 解析 JSON 字符串 |
| 在线获取 | 爬取公开网页 | 3秒间隔，HTML→题目 |
| 网页 HTML 粘贴 | 手动粘贴源码 | HTML 解析 |
| 手动添加 | 逐字段填写 | 直接入库 |
| LaTeX 整卷 | `ExamParserPipeline` | 端到端管道 |

核心流程：
```
原始数据 → _enrich()自动补全 → LaTeX校验+修复 → 质量检查 → 去重 → 入库 → 报告
```

`_enrich()` 会自动推断缺失字段：数学类别、题型、年份、知识点标签、难度、分值。

---

## 8. 增强解析引擎

`ExamParserPipeline`（`exam_parser/`）是一套端到端的真题解析管道：

```
Raw text
  → LaTeXFixer      (修复 \left\right 配对、括号嵌套等)
  → FormatDetector  (检测真题/模拟卷/OCR 格式)
  → OCRCleaner      (清理 OCR 噪声：乱码、换行、符号)
  → QuestionSplitter(按题号/题型边界分割)
  → AnswerExtractor (提取选择题答案、填空题答案)
  → SolutionMatcher (从 solutions/ 目录匹配完整解答)
  → 验证
  → JSON
```

---

## 9. 缓存策略

| 缓存 | TTL | 位置 | 说明 |
|------|-----|------|------|
| 索引缓存 | 5 秒 | `_index_cache` | 避免频繁读磁盘 |
| 题目缓存 | LRU 100 | `_question_cache` | 带文件修改时间检测，外部编辑自动失效 |
| 搜索结果 | 10 秒 | `session_state` | 切换筛选条件时失效 |
| 统计数据 | 5 秒 | `_stats_cache` | 增删操作后清除 |

---

## 10. 题目编辑

支持在线编辑 LaTeX 源码：
- 编辑时自动校验（`services/latex_source_tools.py` 的 `validate_question_latex_source`）
- 自动修复格式（`normalize_question_latex_source`）
- 保存时通过 `parse_latex_question` 重新解析，确保结构一致

---

## 11. Canonical Solution Pool

每道题支持多种解法（换元法、定义法、几何法等），新解法追加而非覆盖：

```
canonical_solutions: [
  { solution_id: "sol_1716...", method_name: "换元法", standard_answer: "...", reviewed: true },
  { solution_id: "sol_1717...", method_name: "定义法", standard_answer: "...", reviewed: false },
]
solution_metadata: {
  canonical: true,
  has_steps: true,
  pool_size: 2,
  render_version: "v2",
}
```

保存流程（`save_as_canonical_solution`）：
1. LaTeX 质量验证（`_validate_latex_quality`）
2. 拒绝思考草稿（>5000字 或 含"此路不通"等标记）
3. 步骤标记检查（确保包含真正推导）
4. 去重（按 `method_name`）
5. 原子写入（tempfile + `os.replace`）

---

# Part II: 错题本系统

## 1. 整体架构

```
UI 层  views/mistakes_page.py
  ↓
MemoryService  (services/memory_service.py)  ← Supabase 优先 + 本地回退
  ↓
ErrorRecordRepository  (repository/error_repository.py)  ← 每人独立 JSON
ErrorIndexRepository   (repository/error_repository.py)  ← SQLite 快速查询索引
  ↓
存储层  storage/data/errors/{user_id}.json
```

---

## 2. 数据模型

每条错题记录（`repository/models.py` 的 `ErrorRecord`）包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `record_id` | str | 唯一 ID，格式 `err_{timestamp}_{毫秒}` |
| `question_id` | str | 关联题库中的题目 ID（**只存引用，不存全文**） |
| `knowledge_point` | str | 知识点（如"线性代数 - 特征值"） |
| `error_type` | str | 错误类型（计算错误/概念错误/方法错误等） |
| `score / max_score` | float | 得分 / 满分 |
| `student_answer` | str | 学生作答 |
| `is_repeat / repeat_count` | bool/int | 是否重复犯错 / 重复次数 |
| `status` | str | 生命周期状态 |
| `step_analysis` | list | 逐步骤分析 |
| `root_cause` | str | 根本原因 |
| `weak_points` | list | 薄弱知识点 |
| `recommendations` | list | 改进建议 |

---

## 3. 生命周期状态机

```
ACTIVE (当前错题，默认展示)
  ├─→ MASTERED  (已掌握，从错题本移除)
  ├─→ ARCHIVED  (已归档，可恢复)
  ├─→ HIDDEN    (已隐藏)
  └─→ DELETED   (彻底删除)
```

- 默认只展示 `ACTIVE` 状态
- "掌握"和"归档"是软删除，数据不丢失
- `hard_delete_record()` 才会真正从磁盘移除

---

## 4. 存储优化策略

`ErrorRecordRepository` 做了 5 项关键优化：

### 4.1 每人独立文件

`storage/data/errors/{user_id}.json`，不再全量加载所有用户数据。

### 4.2 去冗余存储

`_strip_redundant()` 移除可从题库查到的字段（`question`、`standard_answer`、`solution_steps`），只存 `question_id` 引用。详情页按需从 `db.get(qid)` 加载全文。

### 4.3 增量统计

`_increment_stats()` / `_decrement_stats()` 增量更新统计，不重算全部记录。统计维度：
- `by_chapter`（章节分布）
- `by_type`（错误类型分布）
- `by_difficulty`（难度分布）
- `repeat_rate`（重复率）

### 4.4 上限控制

每人最多 **200 条**（`MAX_RECORDS_PER_USER`），超出自动淘汰最旧记录（FIFO）。

### 4.5 重复检测

添加记录时自动检查同知识点是否已存在，标记 `is_repeat=True` 和 `repeat_count`。

---

## 5. 双栈存储

`MemoryService` 实现 **Supabase 优先 + 本地回退**：

```python
# 每次操作先尝试 Supabase
if self._supabase_error_repo:
    try:
        return self._supabase_error_repo.add_record(...)
    except Exception:
        _log.debug("Supabase unavailable, falling back to local")
# 失败自动回退本地 JSON
self._error_repo.add_record(...)
```

所有 CRUD 操作（`add_error_record`、`get_errors`、`delete_error_record`、`update_error_status`）都遵循这个模式。

---

## 6. SQLite 快速查询索引

`ErrorIndexRepository` 维护 SQLite 索引表：

```sql
CREATE TABLE error_index (
    record_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    knowledge_point TEXT,
    error_type TEXT,
    difficulty TEXT,
    date TEXT NOT NULL,
    ...
)
```

支持按知识点快速搜索（`search_by_knowledge_point`）和按错误类型统计（`get_error_count_by_type`），避免遍历 JSON 文件。

---

## 7. UI 界面

### 7.1 快捷筛选

5 个 Chip 按钮：`全部` | `今日优先` | `低分错题` | `已掌握` | `已归档`

折叠式高级筛选：科目 / 错误类型 / 难度

### 7.2 第一层：轻量卡片列表

`_render_record_lightweight()` — **不渲染 LaTeX**，纯文本预览：

严重度颜色条（P12-2/P12-3）：

| 严重度 | 条件 | 左边框颜色 |
|--------|------|-----------|
| 🔥 高优先级 | 得分 < 40% | 红色（`.mistake-card-hot`） |
| ⚠️ 需复习 | 得分 < 70% | 橙色（`.mistake-card-warm`） |
| 💡 轻微错误 | 得分 < 90% | 蓝色（`.mistake-card-cool`） |
| ✅ 接近掌握 | 得分 ≥ 90% | 绿色（`.mistake-card-done`） |
| 👁 仅查看 | view_only 模式 | — |

- 题目预览：`_extract_plaintext_preview()` 剥离所有 LaTeX/Markdown 标记，纯文本截断 70 字
- 知识点标签 Chip
- 三个操作按钮：📋详情 / ✅掌握 / 📦归档

### 7.3 第二层：完整详情展开

`_render_record_full()` — 只在点击"详情"时渲染，**一次只展开一条**，包含 5 个区域：

| 区域 | 内容 |
|------|------|
| 📋 题目 | 从题库加载完整题目 + LaTeX 渲染（优先 `render_question`，fallback `render_structured_safe`） |
| ✍️ 你的作答 | 学生答案渲染 |
| 📖 标准答案 | 从题库加载答案 + 解题步骤（支持 `blocks` 和 `content` 两种步骤格式） |
| 🔍 批改详情 | 得分/方法/置信度 + 逐步骤分析（✅正确/⚠️有问题）+ 评语 |
| 🏥 诊断分析 | 错误类型 + 根本原因 + 薄弱知识点 + 改进建议 + 常见错误 |

底部三个操作：✅已掌握 / 📦归档 / 🔁重做（跳转练习页）

### 7.4 统计面板

4 个指标卡：错题总数 / 重复率 / 主要错误类型 / 高频错误章节

### 7.5 缓存策略

| 缓存 | TTL | 说明 |
|------|-----|------|
| 数据缓存 | 30 秒 | `mistakes_data_{user_id}_{subject}_{error_type}` |
| 强制刷新 | 增删操作后 | `mistakes_force_reload = True` 精确失效 |

---

# Part III: 两个系统的联动

```
题库 (QuestionDB)                         错题本 (ErrorRecordRepository)
  │                                           │
  │  question_id ─────────────────────────→   │  只存引用，不存全文
  │                                           │
  │  ← 详情页按需加载题目/答案/步骤 ────────   │  _render_record_full 时 db.get(qid)
  │                                           │
  │  ← "重做"按钮跳转练习 ─────────────────   │  selected_question = db.get(qid)
  │                                           │
  └─ AI批改完成后 ─────────────────────────→  │  自动写入错题记录
```

关键设计：错题记录 **只存 `question_id` 引用**，题目全文、标准答案、解题步骤都从题库按需加载。这样既节省存储空间，又保证题库内容更新后错题本自动同步最新版本。
