# Code Rules — 考研数学 AI 辅导系统

> Coder must follow these. Architect must not violate these in design.

---

## Python Style

- Flat functions over classes (unless following existing Agent pattern)
- One function, one responsibility
- Type hints on all public function signatures
- Docstrings: one line, imperative mood ("Parse query." not "Parses query.")
- No comments unless the WHY is non-obvious
- Max ~100 lines per function; split if longer

## Error Handling

```python
# Optional dependency guard
try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False

# LLM fallback
if client is None:
    return {"success": False, "error": "LLM not configured"}

# File I/O
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    return {"success": False, "error": str(e)}
```

## Data Flow

- Functions return dicts: `{"success": bool, "data": ..., "warnings": [str]}`
- Agents return structured dicts with consistent keys
- Pipelines chain: `result_a = step_a(input) → result_b = step_b(result_a["data"])`
- Session state keys: always initialized in the init block, always checked with `.get()` with defaults

## Imports

```python
# Standard library first
import json, os, re
from pathlib import Path

# Third-party (guarded)
try:
    import sympy as sp
except ImportError:
    sp = None

# Project modules
from config import LLM_API_KEY, ...
from database import QuestionDB
```

## Streamlit Patterns

- Navigation: `st.session_state.page` string-based routing
- Session state init: all keys initialized once at module level
- UI: `st.container(border=True)` for cards, `st.columns()` for layout, `st.tabs()` for modes
- Math rendering: always use `render_latex(text)` — the single entry point
- Buttons: `st.button()` with unique `key=`, `type="primary"` for main actions
- Spinners: `with st.spinner("..."):` for long operations

## LaTeX Rules

- All math in `$...$` (inline) or `$$...$$` (display)
- Chinese text outside math mode
- `render_latex(text)` handles normalization — never call `st.markdown()` directly for math
- Source fidelity: never rewrite original LaTeX structure

## Testing

- Syntax check: `python -c "import py_compile; py_compile.compile('file.py', doraise=True)"`
- Import check: `python -c "from module import function"`
- Logic check: run with sample inputs, verify output shape
- Before committing: verify Streamlit app imports without error
