# PaperSpine Project Memory

## Project Purpose

PaperSpine is a motivation-driven paper and report writing skill suite for
Codex, Claude Code, and OpenClaw. It is not a simple polishing prompt. The
workflow should research the target scene and examples, confirm the controlling
motivation, build a detailed writing rationale matrix, then write or rewrite
the manuscript with LaTeX/PDF output.

## Canonical Working Directory

Use this directory as the main development and release workspace:

```text
C:\Users\Wubin\Desktop\PaperSpine_publish_worktree
```

Treat these as secondary locations:

```text
C:\Users\Wubin\Desktop\paper总\PaperSpine
```

This is a synced desktop backup/export, not the git source of truth.

```text
C:\Users\Wubin\Desktop\paperspine_claude_empty_test
```

This is a Claude Code experiment folder, not the project repository.

## Repository Shape

- `dist/claude/skills/*`: Claude Code flat skill suite.
- `dist/claude/commands/*.md`: Claude Code slash commands.
- `dist/codex/skills/*`: Codex flat skill suite.
- `dist/codex/paper-spine`: legacy Codex bundled fallback.
- `dist/openclaw/skills/*`: OpenClaw flat skill suite.
- `src/scripts/*`: shared deterministic scripts.
- `src/references/*`: shared workflow references.
- `.claude-plugin/*`: Claude Code plugin metadata.
- `tests/*`: local regression tests.

The root intentionally has no `SKILL.md`; adding one can cause duplicate or
incorrect skill discovery.

## Current Suite Skills

- `paper-spine`: orchestrator.
- `paper-spine-ui`: external terminal configuration UI.
- `paper-spine-intake`: config collection and validation.
- `paper-spine-research`: target scene, local references, and exemplar learning.
- `paper-spine-citation`: citation support bank.
- `paper-spine-rewrite`: rewrite existing drafts.
- `paper-spine-build`: build from materials.
- `paper-spine-latex`: LaTeX/PDF/Word assembly and checks.
- `paper-spine-audit`: artifact, logic, citation, translation, and revision audit.
- `paper-spine-translate`: translation_zh/ package with row-by-row translation.
- `paper-spine-update`: check/update PaperSpine while preserving global config.

## Installation And Sync

Recommended install command:

```powershell
.\install.ps1 -Target all
```

Local development sync command:

```powershell
python .\src\scripts\sync_local_installs.py --clean-legacy-claude-nested --desktop-root "C:\Users\Wubin\Desktop\paper总\PaperSpine"
```

This syncs to:

```text
C:\Users\Wubin\.codex\skills
C:\Users\Wubin\.claude\skills
C:\Users\Wubin\.claude\commands
C:\Users\Wubin\.openclaw\skills
C:\Users\Wubin\Desktop\paper总\PaperSpine
```

If the active Windows user path is `C:\Users\吴彬`, verify whether the same
sync is needed there before assuming Claude Code or Codex can see new skills.

## Version And Update Rules

The current version is recorded in:

```text
dist/paperspine_version.json
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
```

Keep these version fields aligned.

`paper-spine-update` uses GitHub `main` as the latest-version source via
`dist/paperspine_version.json`. It writes install state to:

```text
~/.paperspine/install_state.json
```

It must preserve:

```text
~/.paperspine/config.json
```

including UI language preferences. It must not touch user project outputs such
as `paper_rewriting_output/`.

## Development Rules

- Do not run `git reset --hard` or revert unrelated user changes.
- The working tree may already be dirty; inspect before editing.
- Preserve existing user changes and edit incrementally.
- Keep scripts standard-library only unless the user explicitly approves a new
  dependency.
- Keep README.md and README.zh-CN.md content-equivalent when documentation
  changes.
- Keep Claude, Codex, and OpenClaw dist copies synchronized when changing a
  shared skill or script.
- Do not push to GitHub unless the user explicitly asks.

## Required Checks

Run these before claiming a release or major update is ready:

```powershell
python -m unittest discover -s tests
python -m compileall src dist tests
```

For update-specific work:

```powershell
python -m unittest discover -s tests -p test_update_script.py
```

Current expected full test count after adding the update skill is 54 tests.

## PaperSpine Writing Quality Requirements

The main writing value is the workflow, not just final prose. Both
`rewrite_existing` and `build_from_materials` must share the same core logic:

1. collect configuration,
2. read local or specified references first when available,
3. research target-scene norms and strong examples,
4. build citation support candidates,
5. confirm the controlling motivation with the user,
6. create section blueprints,
7. create a detailed `writing_rationale_matrix.md`,
8. write/rewrite,
9. produce LaTeX and PDF when possible,
10. audit artifacts and translation coverage.

`writing_rationale_matrix.md` is a central artifact. It should be detailed
enough for the user to understand why each section, paragraph group, claim,
title, figure caption, or competition/report unit is written that way. Shallow
rows such as "improve clarity" are failures.

When English output requests a Chinese translation package, translate all
required intermediate Markdown artifacts and final Markdown/paper text into
`translation_zh/`. Large files such as `writing_rationale_matrix.md` and
`citation_support_bank.md` must be translated row by row, not summarized.

## User Preference

Use concise Chinese for discussion with the user unless they ask otherwise.
Be direct about engineering risks, failed tests, and whether a change has been
synced locally or pushed to GitHub.
