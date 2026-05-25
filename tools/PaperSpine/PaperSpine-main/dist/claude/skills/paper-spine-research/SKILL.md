---
name: paper-spine-research
description: Researches target requirements, downloads reference materials, learns strong examples, and prepares motivation options.
---

# PaperSpine Research

Use this skill before motivation confirmation and before any scene-specific
writing. No target-scene research means no venue-specific writing advice.

Research runs in three stages: index locally, launch three parallel
specialist sub-agents, then merge findings into motivation options.

## Inputs

Read `paper_rewriting_output/paper_spine_config.json` when available. The
important fields are `scene`, `tier`, `target_name`, `official_urls`,
`materials_dir`, `draft_path`, `reference_mode`, `reference_paths`, and
`output_language`.

## Tier Rules

- `flash`: collect 3 target-scene examples and 3 recent high-quality field/SOTA
  examples.
- `pro`: collect 6 target-scene examples and 6 recent high-quality field/SOTA
  examples.

Users may override counts explicitly, but do not invent that override.

These learning examples are separate from `citation_support_bank.md`. Learning
examples teach structure and writing strategy. Citation-support papers support
individual literature statements later.

## Stage 1 — Index Local References (main thread)

Create the reference materials workspace:

```text
paper_rewriting_output/reference_materials/
  source_index.md
  official_requirements/
  target_examples/
  field_sota/
  templates/
  figures_images/
  extracted_notes/
```

Index all locally available references. Use `scripts/reference_inventory.py` or
produce the same `source_index.md` format:

| Source ID | Type | Title/Name | Origin/URL/Path | Why Included | Local File/Note | Used For |
|---|---|---|---|---|---|---|

Do NOT stop after indexing. Proceed immediately to Stage 2.

## Stage 2 — Parallel Specialist Agents

Launch the following **three sub-agents simultaneously** (single message, three
Agent tool calls). Each agent works independently and does not see the others'
outputs. Each agent is given only the context it needs — do not pass the full
conversation history.

### Agent A: Scene Analyst

**Goal:** Produce `paper_rewriting_output/research_dossier.md`

**Context to pass:**
- `scene`, `target_name`, `official_urls`, `output_language` from config
- `reference_materials/source_index.md` from Stage 1
- The scene-specific reference: `references/scenario-{journal|conference|report_review|competition}.md`

**Instructions:**
```
You are a Scene Analyst for PaperSpine. Your job is to research the target
venue and produce a structured dossier.

1. Read the scene-specific reference file for format requirements, page limits,
   review criteria, and structural expectations.

2. Visit official URLs (if provided) to check current CFPs, author guidelines,
   templates, rubrics, or rules. Use WebSearch when URLs are not directly
   accessible.

3. Read source_index.md to understand what reference materials are available.

4. Write research_dossier.md with these sections:
   - ## Venue Requirements — concrete format rules (page limit, structure,
     anonymization, supplementary material policy)
   - ## Review Criteria — what reviewers are told to evaluate
   - ## Accepted Paper Patterns — structural patterns observed in accepted papers
     (from the scene reference)
   - ## Constraints for This Paper — specific constraints that must be followed

Output only research_dossier.md. Do NOT produce other files. Do NOT generate
motivation options — that happens in Stage 3.
```

### Agent B: Exemplar Learner

**Goal:** Produce `paper_rewriting_output/exemplar_learning_dossier.md`

**Context to pass:**
- `tier` from config (to know how many examples to analyze)
- `reference_materials/source_index.md` from Stage 1
- The scene scenario reference file path

**Instructions:**
```
You are an Exemplar Learner for PaperSpine. Your job is to learn writing
patterns from strong examples in the target field.

1. Read source_index.md to find available exemplar papers.

2. For each exemplar paper (up to the tier count), analyze:
   - Structural moves: how does the paper organize its argument?
   - Rhetorical patterns: what opening/closing/transition techniques are used?
   - Evidence presentation: how are results, figures, tables presented?
   - Language register: formal level, terminology conventions, sentence patterns.

3. Write exemplar_learning_dossier.md with these sections:
   - ## Exemplar Inventory — table: paper title, venue, year, why selected as exemplar
   - ## Structural Patterns — reusable structural moves observed across exemplars
   - ## Rhetorical Patterns — opening, closing, transition techniques
   - ## Evidence Patterns — how exemplars present results, figures, and tables
   - ## Language Patterns — terminology conventions, register, sentence norms

Output only exemplar_learning_dossier.md. Do NOT produce other files. Do NOT
copy claims or results from exemplars — learn structure only.
```

### Agent C: SOTA Mapper

**Goal:** Produce `paper_rewriting_output/sota_gap_map.md`

**Context to pass:**
- `tier` from config
- `reference_materials/source_index.md` from Stage 1
- The user's `user_motivation` if set (treat as hypothesis, not confirmed)

**Instructions:**
```
You are a SOTA Mapper for PaperSpine. Your job is to map the competitive
landscape and identify where the user's work fits.

1. Read source_index.md to understand available reference materials.

2. For each relevant SOTA paper, identify: what problem it solves, what method
   it uses, what evidence it provides, and what gap it leaves.

3. Write sota_gap_map.md as a Markdown table:

| Candidate Contribution | What SOTA/Examples Already Do | User Evidence | Real Gap | Claim Strength | Risk of Overclaim |
|---|---|---|---|---|---|

4. If the user provided a motivation hypothesis, include it as one row and
   evaluate it against the SOTA evidence honestly. If the user's hypothesis
   overlaps heavily with existing work, flag the overlap.

5. Add a ## Gap Summary section listing the 2-3 most promising gaps.

Output only sota_gap_map.md. Do NOT produce other files.
```

### Agent launch checklist

- Launch all three in ONE message with three Agent tool calls.
- Each agent gets ONLY the context listed above — stripped-down, task-specific.
- Do NOT let agents see each other's instructions or outputs.
- All three write to `paper_rewriting_output/`.

## Stage 3 — Merge and Synthesize (main thread)

After all three agents complete, read their outputs and produce:

### style_profile.md

Merge exemplar language patterns with scene norms:

| Style Dimension | Target Venue Expectation | Exemplar Pattern | Applied To This Paper |
|---|---|---|---|

### motivation_options_after_research.md

Merge the dossier, exemplar analysis, and SOTA gap map into candidate
motivations:

| Option | One-Sentence Motivation | Core Innovation | Why It Is Not Overbroad | Required Evidence | Best-Fit Paper Arc |
|---|---|---|---|---|---|

Rules:
- Each option must be concise. Prefer one controlling contribution.
- If the real novelty is narrow, say so honestly.
- Cross-reference all three agents: a good motivation is one that fits the venue
  (Scene Analyst), follows exemplar structural patterns (Exemplar Learner),
  and occupies a real gap (SOTA Mapper).

### User Confirmation

Stop and present the motivation options to the user. Ask them to choose, revise,
or write their own. Only after confirmation, write `confirmed_motivation.md`:
- exact confirmed motivation,
- user confirmation status,
- rejected options and why,
- scope limits and forbidden overclaims.

## Required Outputs

- `paper_rewriting_output/reference_materials/source_index.md`
- `paper_rewriting_output/research_dossier.md`
- `paper_rewriting_output/exemplar_learning_dossier.md`
- `paper_rewriting_output/style_profile.md`
- `paper_rewriting_output/sota_gap_map.md`
- `paper_rewriting_output/motivation_options_after_research.md`
- `paper_rewriting_output/confirmed_motivation.md` only after user confirmation
