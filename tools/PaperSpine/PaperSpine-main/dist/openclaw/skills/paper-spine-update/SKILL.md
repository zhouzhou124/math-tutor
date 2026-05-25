---
name: paper-spine-update
description: Checks and updates PaperSpine from GitHub while preserving global config; use for upgrades, latest-version checks, or local reinstall.
---

# PaperSpine Update

Use this skill when the user asks to update PaperSpine, check whether
PaperSpine is the latest version, reinstall the local suite from GitHub, or
upgrade the local Codex, Claude Code, or OpenClaw PaperSpine skills while
preserving settings.

## Required Behavior

Run the bundled updater instead of improvising file-copy commands:

```powershell
python scripts/paperspine_update.py --yes
```

For a version check only:

```powershell
python scripts/paperspine_update.py --check-only
```

The updater must:

- read the local install state from `~/.paperspine/install_state.json` when
  present,
- fall back to this skill's bundled `paperspine_version.json` when install
  state is missing,
- compare against the GitHub `main` manifest at
  `dist/paperspine_version.json`,
- update Codex, Claude Code, and OpenClaw installs by default,
- preserve `~/.paperspine/config.json`, including UI language preferences,
- never touch project artifacts such as `paper_rewriting_output/`,
- print a clear already-latest message when no update is needed,
- after installing or updating, run `sync_skill_overrides` logic to ensure
  internal PaperSpine skills remain hidden from the `/` slash-command menu.

## Post-Update skillOverrides

After every update, verify that internal skills are hidden from the
slash-command menu.  Run:

```powershell
# Windows — PowerShell
$settingsPath = Join-Path $HOME ".claude\settings.json"
$settings = if (Test-Path $settingsPath) { Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable } else { @{} }
if (-not $settings.ContainsKey("skillOverrides")) { $settings["skillOverrides"] = @{} }
foreach ($skill in @("paper-spine")) {
  $settings["skillOverrides"][$skill] = "off"
}
$settings | ConvertTo-Json -Depth 4 | Set-Content $settingsPath -Encoding UTF8
```

On Mac/Linux, use the same `sync_local_installs.py --dist-only` command which
includes `sync_skill_overrides()` automatically.

Or manually — `~/.claude/settings.json` should contain:

```json
{
  "skillOverrides": {
    "paper-spine": "off"
  }
}
```

## Advanced Usage

- Use `--target codex`, `--target claude`, or `--target openclaw` only when the
  user explicitly asks to update one host.
- Use `--repo-archive <path-or-url>` for local testing or offline update from a
  downloaded PaperSpine archive.
- Use `--config-home <path>` only for tests or when the user has explicitly
  configured a non-default PaperSpine global config directory.

If network access fails, report the updater error and suggest running the
installer manually from a freshly downloaded repository. Do not delete local
skills after a failed download or failed package validation.
