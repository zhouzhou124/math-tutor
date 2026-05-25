---
name: paper-spine-humanize
description: Reduces AI detection patterns in academic writing via tiered stylistic constraints applied during generation.
---

# PaperSpine Humanize

Use this branch when `humanize_tier` in `paper_spine_config.json` is set to
`light`, `medium`, or `heavy`.  Its job is to apply tier-specific writing
constraints during all prose generation phases — not as a post-hoc fix.

## When To Use

Automatically invoked by `paper-spine-rewrite` and `paper-spine-build` when
the config has `humanize_tier` set to a non-`none` value.  Users configure the
tier in the PaperSpine intake TUI (field 16).

## Tiers

| Tier | Strategy |
|------|----------|
| `light` | Replace formulaic connectors, enforce sentence-length variation |
| `medium` | + Break uniform sentence patterns, layer information density, inject first-person |
| `heavy` | + Allow controlled imperfection, vary structure, use rare terms, permit intuitive leaps |

## Instructions

Read `references/humanize-tiers-{output_language}.md` for the complete
tier-specific writing directives.  The language suffix comes from
`output_language` in the config (`zh` or `en`).

Apply the matching tier's rules throughout all writing phases.  These are
writing constraints enforced during generation — not a checklist to run after
the fact.

## Integration

This branch is called internally by rewrite and build.  Users do not invoke it
directly.  The orchestrator pipeline includes it as an optional stage after
writing and before LaTeX assembly.
