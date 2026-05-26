# 考研数学智能辅导系统

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

### Architect → Coder workflow

This project uses a dual-agent workflow:
- **Architect** reads and analyzes, produces task packages, never touches code
- **Coder** implements task packages exactly, never redesigns

Key routing rules:
- New feature requests / "how should I" / architecture questions → invoke `/architect` first
- "Design first" / "analyze before coding" / "plan the implementation" → invoke `/architect`
- Task package ready / "implement this" / "code it" / "make the changes" → invoke `/coder`
- Bugs/errors (not architecture questions) → invoke `/investigate`
- Code review / diff check → invoke `/review`
- QA/testing → invoke `/qa` or `/qa-only`
- Ship/deploy → invoke `/ship` or `/land-and-deploy`

### Auto-invoke before code changes

**Critical:** Before making any non-trivial code change (more than a typo fix or single-line tweak), invoke `/coder` first. This includes:
- After `/investigate` finds a root cause and you're about to fix it
- After `/architect` outputs a task package and you're about to implement
- Any time you determine code needs to change and the fix spans more than one line

Coder constrains you to: follow the spec, modify only affected files, preserve backward compatibility, no redesign.

Trivial exceptions (no Coder needed):
- Fixing a typo in a string or comment
- Adding a single line (print/log/assert)
- Changing a config value

### Decision rule

If the user is asking **what to build or how to design it** → Architect.
If the user is asking to **build a specific thing with clear specs** → Coder.
If you're **about to change code** (beyond trivial) → invoke Coder first.
If unclear, ask "Should I analyze this with Architect first, or jump straight to Coder?"

## Project Rules

- 不要修改真题库渲染格式。
- 不要修改以下文件，除非用户明确要求：
  - `views/question_bank_page.py`
  - `renderers/question_renderer.py`
  - `renderers/components/question_options.py`
- 不要扫描或修改：
  - `storage/`
  - `tools/PaperSpine/`
  - `.venv/`
  - `__pycache__/`
  - `*.db`
  - `*.tmp`
- 默认先分析，再列修改计划，再修改代码。
- 一次任务最多修改 3 到 5 个文件。
- 不要做大范围重构，除非用户明确要求。

## Common Commands

```bash
# Run focused tests
python -m pytest tests/test_solution_legacy_repair.py -q
python -m pytest tests/test_p19_quarantine.py -q
python -m pytest tests/test_latex_pipeline_golden.py -q

# Run all tests
python -m pytest tests/ -q

# Clear caches after structural changes
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

## AI Grading Core Files

When debugging AI grading or standard solution generation, check these first:

- `services/solution_quality.py` — renderable + completeness gates
- `services/grading_adapter.py` — normalize, format version, canonical entry
- `services/solution_service.py` — build, generate, retry
- `services/solution_legacy_repair.py` — frac repair, mojibake, split frac
- `services/solution_polisher.py` — polish, merge steps, Chinese text split
- `agents/solver_agent.py` — CanonicalIR / legacy solve
- `views/grading_page.py` — async grading + result display
- `renderers/components/grading_result.py` — result cards + view_only gate
- `services/grading_orchestrator.py` — execute_grading, choice fast path

## Question Bank Rendering — Red Line

These files are read-only unless the user explicitly asks:
- `views/question_bank_page.py`
- `renderers/question_renderer.py`
- `renderers/components/question_options.py`

## Rendering Boundary

AI 批改渲染和真题库渲染必须分离。

### 真题库渲染

- 入口必须使用 `render_question_bank_latex`。
- 不允许调用 AI solution repair。
- 不允许调用 `repair_broken_frac_blocks`。
- 不允许调用 `clean_mojibake_tokens`。
- 不允许改变题库卡片布局。
- `$...$` 必须保持 inline。
- `$$...$$` 必须保持 display。
- 中文段落不能被升级为 display math。

### AI 批改渲染

- 入口必须使用 `render_grading_latex`。
- 允许调用 `repair_legacy_solution_text`。
- 允许清理 AI 输出中的坏 LaTeX。
- 允许结构化步骤渲染。
- 必须通过 `solution_is_renderable` 和 `solution_is_complete` 门控。

### 禁止

- 禁止 `question_bank_page.py` 直接调用 grading renderer。
- 禁止 `grading_page.py` 直接调用 question bank renderer。
- 禁止新增无 context 的 `safe_render` 调用。
