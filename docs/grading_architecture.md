# Grading Architecture

## Module Boundaries

```
views/grading_page.py (1361 lines, down from 2255, -40%)
    UI rendering, session_state, Streamlit polling, thin wrappers
    └─ delegates to services/

services/grading_orchestrator.py
    Full grading pipeline: empty-answer → Engine A/B/C → diagnosis → error record
    Structured logging (engine, score, source, elapsed_ms, qid)
    Error taxonomy: GradingError / SolutionGenerationError / EngineCError / ...

services/solution_service.py (SolutionService)
    Standard answer generation: cache hit, AI expansion, SolverAgent fallback
    Empty-shell detection, canonical persistence
    Dependency-injected: client, model, status_callback

services/grading_task_runner.py
    Background task submission, SQLite persistence, result restoration
    Dependency injection via executor= callback (avoids circular imports)

services/grading_adapter.py
    Data contract normalization:
      normalize_grading_result()  — engine-agnostic grading dict
      normalize_standard_solution()  — solution dict
      normalize_error_record()  — error record for mistake notebook
      solution_has_substance() / is_empty_shell()  — quality checks
      normalize_solution_for_render()  — LaTeX normalization chain

services/grading_service.py
    Service entry point. Requires injected GradingAgent/DiagnosisAgent.
    Raises NotImplementedError without agents (use Fake*Agent in tests).

renderers/components/grading_result.py
    Result card rendering: score, knowledge points, diagnosis, step comparison,
    standard solution, recommendations. No business logic.

latex_utils / latex_normalizer
    LaTeX pipeline: normalize → split → sanitize → render.
    Each layer has a single responsibility.
```

## Data Flow

```
User answers question
       │
       ▼
render_grading_page()
  ├─ [async] submit_grading_async() → grading_task_runner → SQLite
  │    └─ background thread → execute_grading() → complete_task()
  │
  └─ [sync]  _execute_grading_process() (thin wrapper)
       └─ execute_grading()
            │
            ├─ student_ans empty?
            │   YES → view_only path: build solution, no grading
            │   NO  ↓
            │
            ├─ build_solution_fn() → SolutionService.build()
            │   Path 1: cache hit (canonical + has_steps) → return
            │   Path 2: known answer → generate_detailed_answer()
            │   Path 3: no answer → generate_from_scratch()
            │   Fallback: SolverAgent.solve()
            │
            ├─ grade
            │   Engine A: 选择题 → choice_engine (fast)
            │   Engine B: 填空题 → quick_compare (fast)
            │   Engine C: 解答题 → LLM grading (GradingAgent)
            │
            ├─ diagnose
            │   High score → local_diagnose (fast)
            │   Low score → DiagnosisAgent.diagnose()
            │
            └─ error_record
                score < 90% max → create → save to MemoryService
```

## Engine Paths

| Engine | Trigger | Speed | Description |
|--------|---------|-------|-------------|
| A | `question_type == "选择题"` + correct_option | ⚡ fast | Extract option letter, compare |
| B | `question_type == "填空题"` + no correct_option | ⚡ fast | Symbolic quick_compare |
| C | `question_type in ("解答题", "证明题")` | 🐢 slow | Graph-alignment + canonical pool + LLM |

## Standard Solution Paths

```
_build_standard_solution() (thin wrapper)
  └─ SolutionService.build()
       │
       ├─ _prepare_known_answer()
       │   Strips metadata-only, placeholder answers (证明略, 略)
       │   Builds choice answer from correct_option
       │
       ├─ _needs_expansion() → _standard_answer_needs_expansion()
       │   Checks: steps, canonical_solutions pool, solution_metadata
       │
       └─ _build_solution()
            Path 1: cache hit (needs_exp=False) → return cached
            Path 2: known answer → generate_detailed_answer()
            Path 3: no answer → generate_from_scratch()
            Fallback: SolverAgent (structured JSON output)
            Shell detection: is_empty_shell() → trigger fallback
            Brace fix: _fix_latex_braces()
            Wrapping: _wrap_unicode_math() + _wrap_ascii_math()
```

## LaTeX Rendering Pipeline

```
AI output / stored question
  → normalize_latex_style()     light normalization (whitespace, delimiters)
  → _wrap_unicode_math()        wrap Unicode math chars (π, ≤, →, Δ)
  → _wrap_ascii_math()          wrap ASCII math (B^2=E, \frac, \int)
  → _fix_latex_braces()         fix LLM brace errors (\frac{xx{yy} → \frac{xx}{yy})
  → split_latex_text()          segment into text/inline_math/display_math
  → render_ast / render_structured_safe
```

Layer boundaries:
- **normalize**: only light formatting, no segmentation, no complex repair
- **split**: only segmentation, no semantic rewrite
- **sanitize**: only pre-`st.latex()` token safety
- **render**: only layout, no content modification

### Standard Solution Rendering Pipeline (P6)

```
LLM Markdown / Structured text
  → normalize_solution_for_render()
      ├─ normalize_latex_style()
      ├─ _wrap_unicode_math()
      ├─ _wrap_ascii_math()
      └─ _fix_latex_braces()
  → from_legacy_text()          build _structured dict
  → polish_solution()           clean leading punct, drop orphans, merge text, add periods
  → render_structured_safe()    validate → iterate steps
      └─ _render_block_latex()  extract \tag, side-by-side or below layout
```

**Tag rendering strategy:**
| Formula | Layout |
|---------|--------|
| Short (<70 chars, single line) | `st.columns` side-by-side, tag on right |
| Long (>70 chars), `aligned`, `\\` | Tag below formula, right-aligned |

**Polisher rules:**
| Rule | Effect |
|------|--------|
| `strip_leading_punctuation()` | `，化简得` → `化简得` |
| `is_punctuation_only()` | `。` block → dropped |
| `is_orphan_formula_number()` | `(1)` / `。(1)` → dropped (tag in LaTeX) |
| `strip_bullet_prefix()` | `• 代入` → `代入` |
| `merge_adjacent_text_blocks()` | `"代入"` + `"化简得"` → `"代入，化简得"` |
| `ensure_sentence_period()` | `其中 E1 为常数` → `其中 E1 为常数。` |

**Prompt constraints (9 rules):** no bullet lists, no fragment sentences, key formulas in `$$`, `aligned` for chains, natural connectors, no leading punctuation, no orphan `(1)`, no markdown bullets, no Chinese in LaTeX blocks. Final answer must be standalone `$$` block.

## Error Record Contract

```python
normalize_error_record(raw) → {
    "question_id", "student_answer", "score", "max_score", "is_correct",
    "error_type", "root_cause", "weak_points", "recommendations",
    "knowledge_points", "engine", "confidence", "timestamp",
    "question_preview", "question_preview_hash", "wrong_reason_short",
    "semantic_tags", "render_cost_level", ...
}
```

Status lifecycle: ACTIVE → MASTERED / ARCHIVED / HIDDEN → DELETED
Records are soft-deleted (ARCHIVED) by default; hard delete requires confirmation.

## Question LaTeX Source Normalization (Input Layer)

Tools for cleaning user-edited question LaTeX source before it enters the bank.

**`services/latex_source_tools.py`:**

- `validate_question_latex_source(text)` — returns warning messages (yellow, non-blocking)
- `normalize_question_latex_source(text)` — auto-fixes common errors before save

**Typical fixes:**
| Issue | Fix |
|-------|-----|
| `$22.$` question number | → `22.` |
| `-1\le 1` missing variable | → `-1\le x\le 1` |
| `cases` without display math | → wrap in `$$...$$` |
| Chinese adjacent to `$` | → insert space |

**Principle:** Input layer only handles question bank source. AI-generated answers go through `solution_polisher`. Rendering layer only handles display safety.

## Troubleshooting Table

| Symptom | Layer | Handler |
|---------|-------|---------|
| `$22.$` renders wrong | Input | `latex_source_tools.py` |
| `将。 a,Aa` period on connector | Post-process | `solution_polisher.py` |
| Red LaTeX raw source | Render | `latex_utils.py` sanitize |
| `\tag{1}` overlaps formula | Render | `_render_block_latex()` |
| Mobile horizontal overflow | Display | `mobile.py` CSS |
| Mistake replay loses answer | Data | `grading_adapter.py` / error_record |
| Bare `\frac` not wrapped | Render | `_wrap_ascii_math()` |
| `[2mm]` spacing artifact | Render | `clean_latex_spacing_artifacts()` |
| Choice options mixed in stem, partially displayed or duplicated | Normalize | `services/question_option_tools.py` |
| `$(A)$` / `$\(A\)$` not recognized as option markers | Normalize | `normalize_latex_option_markers()` |

## Structured Answer Generation (P7)

Three-layer architecture for standard solution generation:

```
CanonicalIR (machine-readable math semantics)
    ↓
StructuredSolution (UI rendering contract: steps + blocks)
    ↓
Legacy Markdown (backward-compat fallback)
```

**Recommended primary path:**
```
LLM → CanonicalIR → validate → StructuredSolution → render_structured_safe()
```

**Not:**
```
LLM → Markdown → regex repair → render
```

### SolverAgent Fallback Chain

```
Layer 1: CanonicalIR path  → validate_canonical_ir() → proof_trace_to_structured()
Layer 2: StructuredSolution → Pydantic validate → render_structured_safe()
Layer 3: Legacy Markdown    → from_legacy_text() → polish_solution() → render
```

### Format Responsibilities

| Layer | Format | Purpose |
|-------|--------|---------|
| CanonicalIR | Semantic JSON | Math semantics, step matching, graph alignment |
| StructuredSolution | Pydantic/dict | UI rendering, step display, LaTeX block display |
| Legacy | Markdown text | Backward compat, old caches, fallback |

**Key principle:** CanonicalIR handles math semantics, StructuredSolution handles display structure, Renderer handles visual presentation, Legacy is compatibility only.

### StructuredSolution Block Rules

- **text block**: natural language only, no LaTeX commands
- **latex block**: formulas only, no Chinese text
- **display=block**: key derivations, long formulas, `\tag` formulas, `aligned`
- **display=inline**: short variables, short expressions

### GradingAgent Structured Output

```json
{
  "score": {"total": 7, "step_score": 4, "result_score": 3},
  "step_analysis": [{"num": 1, "content": "...", "judgment": "正确", "score": 2}],
  "deductions": [{"item": "...", "type": "计算错误", "points": 1}],
  "comment": "...",
  "method_matched": "分离变量法",
  "confidence": 0.86
}
```

All paths feed into `normalize_grading_result()` for unified contract.

### Key Components

| Component | File | Function |
|-----------|------|----------|
| CanonicalIR validation | `semantic_output.py` | Validate and repair IR structure |
| ProofTrace conversion | `semantic_output.py` | CanonicalIR → StructuredSolution |
| JSON extraction | `agents/solver_agent.py` | Extract valid JSON from LLM output |
| Structured validation | `latex_utils.py` | Pydantic validate steps/blocks |
| LaTeX normalization | `latex_utils.py` / `latex_normalizer.py` | Formula cleanup, display detection, tag handling |
| Solution polishing | `services/solution_polisher.py` | Punctuation, bullets, orphans, merging |
| Contract normalization | `services/grading_adapter.py` | solution/grading/error_record unified format |
| UI rendering | `render_structured_safe()` | Step cards + text/latex block rendering |

## Test Suite

| File | Count | Coverage |
|------|-------|----------|
| `test_p0_regression.py` | 10 | P0 crash/security bugs |
| `test_latex_pipeline_golden.py` | 24 | LaTeX wrapping, display math, tag extraction, anti-regression |
| `test_contracts.py` | 9 | Data contract normalization |
| `test_grading_paths.py` | 23 | Path-level business logic + polisher |
| `test_imports.py` | 15 | Import smoke tests |
| `test_e2e_fake.py` | 5 | End-to-end with fake LLM client |
| `test_architecture_boundaries.py` | 5 | Dependency direction enforcement (P8) |
| `test_streaming.py` | 9 | Stream answer truncation + $ balance detection (P9) |
| `test_p10_quality.py` | 20 | Model router + solution/grading quality + timing (P10) |
| `test_ui_components.py` | 16 | UI component contract tests (P12) |
| `test_structured_output.py` | — | CanonicalIR validation tests |

Run: `python -m pytest tests/ -q`

## Common Troubleshooting

1. **Solution shows "解答生成失败，请重试"**: Check LLM API key; check `standard_answer` is not empty/placeholder
2. **LaTeX not rendering**: Check pipeline order (normalize → wrap → fix → split → render); check `$` wrapping
3. **Error record not saved**: Check score < 90% threshold; check `MemoryService` is initialized
4. **Page freeze on mobile**: Check `_clear_grading_state()` before new grading; restart server to clear stale session_state
5. **Canonical answer won't regenerate**: Delete `solution_metadata` and `canonical_solutions` from the question JSON file

## Manual Verification Checklist

- [ ] 空作答查看答案 (empty answer → view_only, no grading)
- [ ] 选择题答对 (Engine A, fast path)
- [ ] 选择题答错 (Engine A, error record created)
- [ ] 填空题等价表达式 (Engine B, quick_compare)
- [ ] 解答题低分进入错题本 (error record with all fields)
- [ ] AI 生成详细步骤 LaTeX 正常渲染
- [ ] 错题本冷热分离 (lightweight list, detail on click)
- [ ] 错题生命周期 (已掌握/归档/隐藏)
- [ ] 手机刷新后恢复批改任务 (URL routing + task recovery)
