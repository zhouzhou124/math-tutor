# Task Package Template

> **For Architect use.** Fill this out completely before handing to Coder.
> Coder reads ONLY the "For Coder" section at the bottom.

---

## 1. Task Goal
<!-- One sentence. What and why. -->

## 2. Root Cause Analysis
<!-- Why is this needed? What's broken/missing? Constraints? -->

## 3. Affected Files
<!--
Format:
- `path/to/file.py` — CREATE — reason
- `path/to/file.py` — MODIFY — reason
- `path/to/file.py` — DELETE — reason
-->

## 4. Required Changes
<!-- Per file, dependency-ordered. WHAT changes, not HOW. -->

### File: `path/to/file.py`
- Change 1
- Change 2

### File: `path/to/file.py`
- Change 1

## 5. Interfaces / Data Contracts
<!--
Every new function signature with types.
Every new data structure.
Every API contract between modules.

```python
def function_name(param: type) -> return_type:
    \"\"\"What it does.\"\"\"
```

```python
# Data structure
{
    "key": type,  # description
}
```
-->

## 6. Edge Cases
<!--
- Empty inputs
- Missing optional deps (sympy, networkx, pytesseract)
- LLM API failures
- Encoding issues
- Boundary conditions (empty string, None, 0, very long input)
-->

## 7. Acceptance Criteria
<!-- Verifiable, testable conditions. Always include: -->
- [ ] No regressions to existing pages (dashboard, practice, grading, question_bank, mistakes, profile, settings)
- [ ] `python -c "import py_compile; py_compile.compile('file.py', doraise=True)"` passes for all changed files
- [ ] ...

---

## 8. For Coder — EXACT TASK PACKAGE

<!--
CODE ONLY. NO REDESIGN.
This is the ONLY section the coder reads.
Must be self-contained and unambiguous.
-->

### Files to Create

#### `path/to/new_file.py`
```python
# Exact function signatures
def function_name(param: type) -> return_type:
    \"\"\"What it does.\"\"\"
    # Implementation note: ...
```

### Files to Modify

#### `path/to/existing_file.py`
- **Location:** After line N, before function X
- **Change:** Add Y
- **Do NOT change:** Z

### Implementation Order
1. Create `file_a.py` (no deps)
2. Create `file_b.py` (depends on file_a)
3. Modify `app.py` (depends on all above)

### Verification
```bash
cd E:/math_tutor && python -c "from module import function; ..."
```
