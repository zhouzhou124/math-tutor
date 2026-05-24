# Document Maintenance Checklist

When you make changes to the codebase, update the corresponding doc(s).

## Change → Doc mapping

| Change | Update this doc |
|--------|-----------------|
| Add, move, or remove a page | `docs/ui_architecture.md` |
| Add or change a UI component | `docs/ui_design_system.md` |
| Add or change a CSS token | `docs/ui_design_system.md` |
| Modify AI grading pipeline (orchestrator, engines, agents) | `docs/grading_architecture.md` |
| Modify standard solution generation (SolutionService, SolverAgent) | `docs/grading_architecture.md` |
| Modify LaTeX rendering pipeline | `docs/grading_architecture.md` |
| Modify question bank schema, import pipeline, or storage layout | `docs/question_bank_architecture.md` |
| Modify mistake notebook lifecycle or data model | `docs/question_bank_architecture.md` |
| Add a new `services/` module | `docs/module_ownership.md` |
| Add a new `agents/` or `repository/` module | `docs/module_ownership.md` |
| Mark a module as deprecated | `docs/module_ownership.md` |
| Add a new database file or storage directory | `docs/module_ownership.md` |
| Add a new architectural boundary rule | `docs/module_ownership.md` + `tests/test_architecture_boundaries.py` |
| Add a new streaming or background task behavior | `docs/ui_architecture.md` (Background tasks section) |
| Change mobile CSS or responsive breakpoints | `docs/ui_architecture.md` (Mobile section) |

## When to check

- **Before merging a PR**: verify any affected docs are updated
- **After a multi-P milestone** (e.g., P8, P9, P12): full doc audit
- **When onboarding a new team member**: ensure all docs reflect current state

## Doc inventory

| Doc | Covers |
|-----|--------|
| `docs/ui_architecture.md` | Page routing, design system, mobile, interaction flows, background tasks, LaTeX rendering layers |
| `docs/ui_design_system.md` | Component catalog, CSS tokens, usage examples, safety rules, new-page checklist |
| `docs/grading_architecture.md` | AI grading pipeline, engine paths, solution generation, error records, structured answers |
| `docs/question_bank_architecture.md` | QuestionDB, import pipeline, storage layout, mistake notebook lifecycle, quick filters |
| `docs/module_ownership.md` | Dependency boundaries, deprecated modules, database inventory, new module registry |

## Quick audit command

```bash
# Check if any services/agents still import from forbidden layers
python -m pytest tests/test_architecture_boundaries.py -v

# Check if sensitive files leaked into git
python scripts/check_sensitive_files.py

# Verify eval dataset integrity
python scripts/eval_grading.py
```
