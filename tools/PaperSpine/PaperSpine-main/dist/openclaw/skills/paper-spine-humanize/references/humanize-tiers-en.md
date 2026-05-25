# AI Humanization Writing Directives (English)

When `humanize_tier` in `paper_spine_config.json` is not `none`, apply the
following rules during ALL writing phases.  These are writing constraints to
follow during generation, not a post-writing checklist.

## light

### Connector replacement
Ban high-frequency AI connectors.  Use natural logical transitions instead:
- "Firstly / Secondly / Thirdly / Finally"
- "In conclusion / To sum up / In summary"
- "Furthermore / Moreover / Additionally / In addition"
- "It is worth noting that / It should be pointed out that / It cannot be ignored that"

Replace with paragraph-to-paragraph logical flow: the conclusion of one paragraph
naturally introduces the problem of the next.

### Sentence length variation
Every 3-4 sentences, at least one must differ significantly in length from its
neighbors — either very short (5-8 words, making a single sharp point) or long
(35+ words, unfolding a full reasoning chain).  No 3 consecutive sentences of
similar length.

### Tone
Keep academic register.  Do not pursue symmetrical perfection in sentence
structure.  Allow paragraphs to end with short sentences.

---

## medium (includes all of light + below)

### Sentence diversity
- No 3 consecutive sentences with length difference under 5 words
- Mix declarative, rhetorical-question (1-2 per section), and hypothetical constructions
- No two consecutive paragraphs starting with the same sentence pattern

### Information density layering
- Core argument paragraphs: 2-3 sentences of deep development, each claim paired with specific evidence
- Transition paragraphs: 1 sentence to bridge, no expansion
- Create a "dense—light—dense" rhythm; do not distribute information evenly

### First-person injection
Use "we / our / this work / our study" at:
- Key methodological decision explanations
- Important result analyses
- Comparisons with prior work

At least 2 first-person academic references per 2000 words.

---

## heavy (includes all of medium + below)

### Controlled imperfection
- Allow occasional informal-but-accurate expressions ("in other words", "to put it bluntly")
- Allow 1-2 personal commentary asides after result analyses ("This is actually counter-intuitive because...")
- Allow Introduction to end with a slightly personal transition ("This prompted us to explore...")

### Structural variation
- Introduction: may start in-medias-res (lead with the core problem, then backtrack to background) rather than "background→gap→approach→contributions"
- Methods: may interleave design rationale with description
- Discussion: may leave 1-2 questions deliberately unresolved rather than tying everything up neatly

### Low-frequency vocabulary
At least 1 uncommon-but-precise academic term per 800 words. Accuracy over frequency — do not misuse rare words for show.

### Intuitive leaps
Allow 1-2 instances of skipping intermediate derivation steps in the manuscript (e.g., "A and B trend in the same direction consistently enough that further verification would not change the conclusion"), mimicking the natural cognitive shortcuts human researchers take in writing.

---

## Universal rules (all tiers)

1. Preserve all LaTeX commands, citation keys, equations, file paths, numeric values — only modify narrative prose
2. Do not change factual content (data, results, conclusions)
3. Do not add evidence the author has not provided
4. Keep technical terms as-is; do not substitute synonyms
