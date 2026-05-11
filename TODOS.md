# TODOS

## Completed (2026-05-08)

### P0-P2: Core Pipeline
- [x] StateMachineSplitter shadow mode — `pipeline.py` auto-selects best splitter
- [x] rebuild_db.py — one-click rebuild: backup→extract→import→verify→benchmark
- [x] Benchmark extended — 20 cases across 5 directories (smoke/regression/damaged_ocr/semantic_match)
- [x] VERSION.json — parser 0.6.0, coverage tracked

### P3: LLM Repair (optional, gated)
- [x] LLM pass wired into ocr_repair — triggers only when quality < threshold AND LLM enabled
- [x] Deterministic-first: LLM only activates if strict_fidelity=False

### P4: API Key
- [x] app.py settings page has API Key input
- [x] Agent功能 (grading/solving/diagnosis) gated behind API key check

## Deferred

### P5: Embedding fallback
- **What:** Add `bge-small-zh` embedding fallback to semantic matcher
- **Why:** Fingerprint matching currently covers fingerprint-amenable questions. Embedding would help proof-heavy questions with sparse LaTeX.
- **When:** After answer coverage > 75% with current approach. Current: 68.1%.
- **Context:** `math_fingerprint.py` + `solution_matcher.py` already provide weighted Jaccard + number fallback + SequenceMatcher. Embedding is the 4th layer.

### StateMachineSplitter over-split tuning
- **What:** 2024 produces 25 questions (expected 22), 2025 produces 27 (expected 22)
- **Why:** Fragment merge threshold (`len(text) < 80`) + sub-step detection needs tuning
- **Context:** `state_machine_splitter.py:_QuestionAccumulator.flush()` — `is_substep` check
