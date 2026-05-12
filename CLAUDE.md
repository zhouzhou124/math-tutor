# 考研数学智能辅导系统

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

### Architect → Coder workflow

This project uses a dual-agent workflow:
- **Architect** reads and analyzes, produces task packages, never touches code
- **Coder** implements task packages exactly, never redesigns

Key routing rules:
- New feature requests / "how should I" / architecture questions → invoke `/architect` first
- "Design first" / "analyze before coding" / "plan the implementation" → invoke `/architect`
- Task package ready / "implement this" / "code it" / "make the changes" → invoke `/coder`
- Bugs/errors (not architecture questions) → invoke `/investigate`
- Code review / diff check → invoke `/review`
- QA/testing → invoke `/qa` or `/qa-only`
- Ship/deploy → invoke `/ship` or `/land-and-deploy`

### Auto-invoke before code changes

**Critical:** Before making any non-trivial code change (more than a typo fix or single-line tweak), invoke `/coder` first. This includes:
- After `/investigate` finds a root cause and you're about to fix it
- After `/architect` outputs a task package and you're about to implement
- Any time you determine code needs to change and the fix spans more than one line

Coder constrains you to: follow the spec, modify only affected files, preserve backward compatibility, no redesign.

Trivial exceptions (no Coder needed):
- Fixing a typo in a string or comment
- Adding a single line (print/log/assert)
- Changing a config value

### Decision rule

If the user is asking **what to build or how to design it** → Architect.
If the user is asking to **build a specific thing with clear specs** → Coder.
If you're **about to change code** (beyond trivial) → invoke Coder first.
If unclear, ask "Should I analyze this with Architect first, or jump straight to Coder?"
