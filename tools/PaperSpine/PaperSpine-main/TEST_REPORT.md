# PaperSpine v3 Local Hardening Test Report

Status: local release-candidate hardening for the `dist/` release layout.

## Scope

This report covers local validation of the PaperSpine v3 skill suite after the
Claude Code-compatible single-layout change and the latest writing-quality
hardening pass.

Validated areas:

- Codex flat suite layout under `dist/codex/skills/*`,
- Codex legacy bundled fallback under `dist/codex/paper-spine`,
- Claude Code flat suite layout under `dist/claude/skills/*`,
- Claude Code commands under `dist/claude/commands/*`,
- OpenClaw flat suite layout under `dist/openclaw/skills/*`,
- absence of a root `SKILL.md` to avoid duplicate Codex discovery,
- Claude Code plugin manifest,
- top-level `install.ps1`,
- README installation and troubleshooting instructions,
- intake wizard,
- material inventory,
- artifact completeness checker,
- Word output validator,
- LaTeX/style/revision scripts,
- install layout simulation,
- local sync script safety,
- orchestrator/branch-skill routing,
- local or specified-path reference reading,
- citation support bank generation and validation,
- external-window intake UI branch packaging,
- privacy and repository hygiene checks.

## Latest Quality Hardening

The latest pass changes PaperSpine from a surface-level rewriting helper into a
research-then-design workflow shared by both `rewrite_existing` and
`build_from_materials`.

Key enforced rules:

- Research happens before final motivation selection.
- User motivation given at intake is treated as a hypothesis until research is
  complete.
- `paper-spine-research` must create `reference_materials/`,
  `research_dossier.md`, `exemplar_learning_dossier.md`, `style_profile.md`,
  `sota_gap_map.md`, and `motivation_options_after_research.md`.
- The user must confirm the controlling motivation before drafting or rewriting.
- Both build and rewrite workflows must create `writing_rationale_matrix.md`
  before final prose.
- `writing_rationale_matrix.md` is scene-flexible: it must split the work into
  paragraph-sized, claim-sized, evidence, model, synthesis, heading, caption, or
  competition-solution units as needed, not force every task into a fixed IMRaD
  template.
- `artifact_check.py` now checks the matrix content, including overall framework
  row, required rationale columns, minimum row count, and generic/empty cells.
- The rationale matrix must proceed in manuscript order: whole-paper framework,
  abstract, every Introduction paragraph, Methods units, Results evidence units,
  Discussion/Conclusion paragraphs, and argument-bearing headings/captions.
- Each rationale row must connect the writing decision to motivation, learned
  SOTA/example patterns, target-scene norms, user evidence/citation anchors, and
  final text checks.
- English outputs with `translation_package: zh` must translate the complete
  intermediate artifact set and the final result reading package, not only a
  subset.
- Reference/downloaded materials must live under
  `paper_rewriting_output/reference_materials/` with a `source_index.md`.
- Reference reading supports `reference_mode: local_first | specified_paths |
  web`; `local_first` indexes the current work folder before web
  supplementation.
- `paper-spine-citation` creates `citation_support_bank.md` as a separate
  candidate pool for Introduction, Discussion, background, limitation, and
  application claims.
- `citation_target_count` defaults to 20; the candidate pool must be three
  times that value, and roughly 80% should be recent using 2023 as the simple
  threshold in 2026.
- `paper-spine-ui` is a separate branch skill and `/paperspine` is expected to
  route there automatically when config is missing.
- The terminal UI now renders through a deterministic frame function, so tests
  can verify layout text, Chinese output, and obvious mojibake regressions.
- Users can call the full `paper-spine` orchestrator or call a branch skill
  directly, including research-only, citation-only, LaTeX-only, and audit-only
  runs.

## Commands Run

```bash
python -m unittest discover -s tests
python -m compileall src dist tests
rg -n -F -e "<private-path-or-historical-project-patterns>" README.md README.zh-CN.md dist src tests .claude-plugin
```

The unit suite also exercises these paths internally:

```bash
python src/scripts/intake_wizard.py --no-interactive ...
python src/scripts/material_inventory.py ...
python src/scripts/reference_inventory.py ...
python src/scripts/citation_bank_check.py ...
python src/scripts/artifact_check.py ... --markdown --write
python src/scripts/word_guard.py ... --markdown
python src/scripts/style_metrics.py ... --markdown
python src/scripts/revision_audit.py ... --markdown
python src/scripts/latex_guard.py ... --markdown
python src/scripts/sync_local_installs.py --clean-legacy ...
```

## Results

| Area | Result | Notes |
|---|---|---|
| Unit tests | PASS | 46 tests passed. |
| Python compile check | PASS | `src/`, `dist/`, and tests compile. |
| Branch skill layout | PASS | Main orchestrator plus UI, intake, research, citation, rewrite, build, LaTeX, and audit branch skills are present and individually callable. |
| Claude Code plugin manifest | PASS | Manifest paths point to `dist/claude/skills/*`. |
| Root duplicate guard | PASS | Root `SKILL.md` is absent by design. |
| Codex release layout | PASS | `dist/codex/skills/*` exposes all suite skills; `dist/codex/paper-spine` remains as a legacy bundled fallback. |
| Claude Code release layout | PASS | `dist/claude/skills/*` is flat and `.claude-plugin` points to those folders. |
| OpenClaw release layout | PASS | `dist/openclaw/skills/*` exposes the same flat suite for OpenClaw-style `SKILL.md` discovery. |
| Installer script | PASS | `install.ps1` installs Codex, Claude Code, OpenClaw skills, and Claude commands from `dist/`. |
| Intake wizard | PASS | Rewrite/build, flash/pro, English/Chinese, Word option, and translation package paths covered. |
| UI branch packaging | PASS | `paper-spine-ui` includes the external terminal launcher and wizard copy. |
| UI layout smoke test | PASS | Static keyboard-frame preview renders clean Chinese labels, left field navigation, right detail panel, and no mojibake tokens. |
| Reference inventory | PASS | Local/specified reference paths are indexed into `reference_materials/source_index.md`. |
| Citation bank check | PASS | 3x candidate-count and recent-paper coverage are enforced. |
| Material inventory | PASS | Images, PDFs, Word/text, LaTeX, data, and code files classify correctly. |
| Artifact check | PASS | Missing artifacts fail; final LaTeX is mandatory; PDF and Word policies are enforced. |
| Translation package check | PASS | English + Chinese package requires all common and workflow-specific translated MD artifacts. |
| Reference material workspace | PASS | `reference_materials/source_index.md` is a required artifact. |
| Rationale matrix check | PASS | `writing_rationale_matrix.md` is a required artifact for both workflows. |
| Word guard | PASS | Requested Word output requires `paper.docx` and `word_report.md`. |
| Existing scripts | PASS | LaTeX, style, and revision smoke tests pass. |
| Install simulation | PASS | Codex package and Claude flat fallback layouts are generated in temporary directories. |
| Sync safety | PASS | Sync script does not delete the source tree when the desktop target equals the source tree. |
| Privacy scan | PASS | No private path, target venue, local file URL, or historical manuscript-version terms found. |
| Codex parse guard | PASS | `SKILL.md` metadata files are UTF-8 without BOM so frontmatter starts at byte 1. |

## Fixes Made During This Pass

- Restructured the repository into `dist/codex`, `dist/claude`, and `src`.
- Added `install.ps1` so users can install without understanding host-specific discovery rules.
- Updated tests for the current no-root-`SKILL.md` design.
- Updated English and Chinese README files to document the new installable layout.
- Added source-tree safety to `src/scripts/sync_local_installs.py`.
- Removed local deployment records containing machine paths from the reusable
  source tree.
- Extended artifact tests to require research-after-intake artifacts,
  reference material indexing, `writing_rationale_matrix.md`, and complete
  translation-package coverage.
- Added `reference_inventory.py` and required local/specified-path source
  indexing before web-only literature expansion.
- Added `paper-spine-citation` and `citation_bank_check.py` to force a separate
  citation support bank with 3x candidates, sentence-level support claims, and
  recent-paper coverage.
- Added `paper-spine-ui` as the dedicated interaction branch and bundled the
  external terminal launcher plus wizard in the Claude Code suite.
- Rebuilt the terminal UI layout: centered welcome screen, cleaner white ridge
  wordmark, stable field/detail panels, full-width/Chinese-aware text
  measurement, and a static preview command for testing.
- Updated Codex single-skill instructions to use the same branch workflow
  internally.
- Verified Claude plugin metadata paths after the documentation and structure changes.
- Cleaned generated `__pycache__` directories after test and compile runs.
- Restored two host-specific release layouts: `dist/codex/paper-spine` as a single official-style Codex skill and `dist/claude/skills/*` as the Claude Code flat suite.
- Removed UTF-8 BOM from PaperSpine metadata/text files; Codex appears to skip `SKILL.md` when frontmatter is preceded by BOM bytes.
- Added `dist/codex/skills/*` so Codex users can call either the full workflow
  or individual branch skills.
- Added `dist/openclaw/skills/*` so OpenClaw users can install the same flat
  suite format.
- Updated `install.ps1` and `sync_local_installs.py` to install all three
  hosts: Codex, Claude Code, and OpenClaw.

## Remaining Manual Checks

These require real host application behavior and were not claimed as automated:

- restart Codex and confirm the slash menu shows one entry per PaperSpine skill;
- restart Claude Code and confirm plugin skill discovery through `/plugin install`;
- restart OpenClaw and confirm `paper-spine` plus `paper-spine-*` branch skills
  are discoverable from `~/.openclaw/skills`;
- run a full real manuscript workflow and inspect whether the rationale matrix
  actually drives substantive section-level rewrites.

## Release Readiness

The local suite is structurally ready for a release-candidate test. The main
remaining risk is qualitative rather than structural: real paper runs must be
reviewed to confirm that the rationale matrix is being used as the drafting plan,
not generated as a superficial post-hoc explanation.




