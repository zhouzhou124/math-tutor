# PaperSpine Humanize — Design Spec

**Date**: 2026-05-23
**Status**: approved

## Goal

Add a prompt-driven AI detection reduction stage to PaperSpine, selectable
during configuration, that guides the LLM to produce text with lower AI
detection scores across 知网 5.0, 维普, and Turnitin.

## Architecture

```
paper-spine-humanize/
  SKILL.md                              # skill entry point
  references/
    humanize-tiers-zh.md                # Chinese humanization prompts (3 tiers)
    humanize-tiers-en.md                # English humanization prompts (3 tiers)
  scripts/
    humanize_check.py                   # post-generation AI-feature scan + report
```

## Integration Points

1. **`intake_wizard.py`**: new `humanize_tier` field (values: `none`, `light`,
   `medium`, `heavy`), written into `paper_spine_config.json`.
2. **`paper-spine-rewrite` SKILL.md**: when `humanize_tier != none`, load the
   matching tier+language prompt before writing.
3. **`paper-spine-build` SKILL.md**: same as rewrite.
4. **`paper-spine-audit`**: optionally invoke `humanize_check.py` to scan the
   final manuscript and produce `humanize_report.md`.

## Three Humanization Tiers

### Light
- Replace formulaic connectors with natural transitions
- Enforce sentence-length variation: at least 1 in 4 sentences must differ
  significantly from neighbors (under 5 chars or over 40 chars)
- Keep academic tone; avoid symmetrical perfection

Target: journal/conference drafts, AI-rate threshold > 30%

### Medium (includes Light)
- No 3 consecutive sentences with length difference under 5 chars
- Mix declarative / rhetorical-question / hypothetical constructions
- Information density: core paragraphs deep (2-3 sentences), transition
  paragraphs light (1 sentence)
- Insert first-person academic narration at key analysis points

Target: undergraduate theses, course reports, AI-rate threshold 15-30%

### Heavy (includes Medium)
- Allow occasional informal expressions and personal asides
- Structural variety: intro can start in-medias-res, methods can interleave
  with discussion, conclusion can remain open-ended
- Require at least 1 uncommon-but-correct academic term per 800 characters
- Allow 1-2 instances of intuitive logical leaps (skipping intermediate
  derivation to mimic human cognitive shortcuts)

Target: finalized undergraduate/Masters theses, AI-rate threshold < 15%

## humanize_check.py

Post-generation AI-feature scanner. Four dimensions:

| Dimension | Method | Threshold |
|-----------|--------|-----------|
| Sentence uniformity | Adjacent-sentence length stddev; flag 3+ consecutive sentences with delta < 5 chars | score > 60 warns |
| Connector density | Regex against ~30 high-risk connectors per language; count per 1k chars | > 15/1k warns |
| Information density | Paragraph char count / core-sentence ratio; flag uniform-density mode | uniform-segment ratio reported |
| Tone variety | Frequency distribution of exclamatory/rhetorical/first-person markers | zero-variant warns |

Outputs `humanize_report.md` with per-section scores and flagged passages.

## config.json Addition

```json
{
  "humanize_tier": "none"   // none | light | medium | heavy
}
```

## Files to Create

- `src/skills/paper-spine-humanize/SKILL.md`
- `src/skills/paper-spine-humanize/references/humanize-tiers-zh.md`
- `src/skills/paper-spine-humanize/references/humanize-tiers-en.md`
- `src/scripts/humanize_check.py`

## Files to Modify

- `src/scripts/intake_wizard.py`: add `humanize_tier` field, choice options,
  keyboard UI integration
- `dist/claude/skills/paper-spine-rewrite/SKILL.md`: add humanize tier gating
- `dist/claude/skills/paper-spine-build/SKILL.md`: add humanize tier gating
- `dist/claude/skills/paper-spine-audit/SKILL.md`: add optional humanize_check
  invocation
- `dist/claude/skills/paper-spine/references/suite-map.md`: add new skill entry
- `.claude-plugin/plugin.json`: add new skill to manifest
- `.claude-plugin/marketplace.json`: sync skill list

Plus all corresponding Codex and OpenClaw dist copies (handled by sync script).

## Constraints

- Standard library only for Python scripts; no new dependencies
- Chinese and English content must be kept equivalent
- Must not break existing tests; add new tests for humanize_check and
  intake_wizard tier selection
