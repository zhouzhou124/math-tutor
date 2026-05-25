#!/usr/bin/env bash
# Install PaperSpine skills to Codex, Claude Code, and OpenClaw.
# Usage: bash install.sh [all|codex|claude|openclaw] [--clean-legacy]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-all}"
CLEAN_LEGACY=false
[[ "${2:-}" == "--clean-legacy" ]] && CLEAN_LEGACY=true

CODEX_SKILL="$ROOT/dist/codex/paper-spine"
CODEX_SKILLS="$ROOT/dist/codex/skills"
CLAUDE_SKILLS="$ROOT/dist/claude/skills"
CLAUDE_COMMANDS="$ROOT/dist/claude/commands"
OPENCLAW_SKILLS="$ROOT/dist/openclaw/skills"
VERSION_MANIFEST="$ROOT/dist/paperspine_version.json"

# verify source exists
for path in "$CODEX_SKILL" "$CODEX_SKILLS" "$CLAUDE_SKILLS" "$CLAUDE_COMMANDS" "$OPENCLAW_SKILLS" "$VERSION_MANIFEST"; do
    if [ ! -e "$path" ]; then
        echo "Required path not found: $path" >&2
        exit 1
    fi
done

reset_dir() {
    local src="$1" dst="$2"
    rm -rf "$dst"
    mkdir -p "$(dirname "$dst")"
    cp -r "$src" "$dst"
}

install_codex() {
    local dir="$HOME/.codex/skills"
    if $CLEAN_LEGACY; then
        rm -rf "$dir"/PaperSpine "$dir"/PaperSpineV2 "$dir"/paper-spine* 2>/dev/null || true
    fi
    for skill_dir in "$CODEX_SKILLS"/*/; do
        reset_dir "$skill_dir" "$dir/$(basename "$skill_dir")"
    done
    echo "Installed Codex skills: $dir"
}

install_claude() {
    local skill_dir="$HOME/.claude/skills"
    local cmd_dir="$HOME/.claude/commands"
    if $CLEAN_LEGACY; then
        rm -rf "$skill_dir"/PaperSpine "$skill_dir"/PaperSpineV2 "$skill_dir"/paper-writing-assistant "$skill_dir"/paper-spine* 2>/dev/null || true
        rm -f "$cmd_dir"/paperspine.md "$cmd_dir"/paperspine-ui.md 2>/dev/null || true
    fi
    for skill in "$CLAUDE_SKILLS"/*/; do
        reset_dir "$skill" "$skill_dir/$(basename "$skill")"
    done
    mkdir -p "$cmd_dir"
    cp "$CLAUDE_COMMANDS"/*.md "$cmd_dir"/
    echo "Installed Claude Code skills: $skill_dir"
    echo "Installed Claude Code commands: $cmd_dir"
}

install_openclaw() {
    local dir="$HOME/.openclaw/skills"
    if $CLEAN_LEGACY; then
        rm -rf "$dir"/PaperSpine "$dir"/PaperSpineV2 "$dir"/paper-spine* 2>/dev/null || true
    fi
    for skill_dir in "$OPENCLAW_SKILLS"/*/; do
        reset_dir "$skill_dir" "$dir/$(basename "$skill_dir")"
    done
    echo "Installed OpenClaw skills: $dir"
}

case "$TARGET" in
    all|codex)   install_codex ;;
esac
case "$TARGET" in
    all|claude)  install_claude ;;
esac
case "$TARGET" in
    all|openclaw) install_openclaw ;;
esac

# write install state
CONFIG_HOME="${PAPERSPINE_CONFIG_HOME:-$HOME/.paperspine}"
mkdir -p "$CONFIG_HOME"
VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_MANIFEST'))['version'])" 2>/dev/null || echo "unknown")
cat > "$CONFIG_HOME/install_state.json" << STATE
{
  "installed_version": "$VERSION",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "targets": ["codex", "claude", "openclaw"],
  "preserved_config_path": "$CONFIG_HOME/config.json"
}
STATE

# Hide internal PaperSpine skills from Claude Code / menu
SETTINGS="$HOME/.claude/settings.json"
python3 -c "
import json, os
path = os.path.expanduser('$SETTINGS')
data = {}
if os.path.exists(path):
    try: data = json.load(open(path))
    except: pass
data.setdefault('skillOverrides', {})
for skill in ['paper-spine']:
    data['skillOverrides'][skill] = 'off'
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(data, open(path, 'w'), ensure_ascii=False, indent=2)
print(f'Updated skillOverrides in {path}')
" 2>/dev/null || echo "Warning: could not update skillOverrides (Python3 required)"

echo "PaperSpine install complete. Restart Codex, Claude Code, or OpenClaw before use."
