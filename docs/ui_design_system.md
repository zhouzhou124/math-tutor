# UI Design System

Last updated: 2026-05-25 (P12-3)

## Principles

- **Unified**: every page uses the same CSS tokens, cards, chips, and header
- **Clean**: minimal visual noise, clear information hierarchy
- **Mobile-first**: all components work on 375px–768px screens
- **Safe**: all user/AI content must pass through `html.escape`

## File map

```
views/ui/
  theme.py       Global CSS, render_page_header, render_flow_steps,
                 render_question_list_card, render_mistake_card
```

Theme injection: `views/main_page.py` calls `inject_app_theme()` once per session.

---

## Component catalog

### 1. Page header — always use `render_page_header`

```python
from views.ui.theme import render_page_header

render_page_header("页面标题", "一句话描述页面的作用和当前状态。", "📊")
```

Never use `st.title()` or `st.header()` for page titles. The subtitle is optional.

### 2. Cards — use `.app-card` / `.app-card-compact`

```html
<!-- Standard card -->
<div class="app-card">...</div>

<!-- Compact card for lists -->
<div class="app-card-compact mistake-card-hot">...</div>
```

CSS classes provided by `inject_app_theme()`:

| Class | Use |
|---|---|
| `.app-card` | Main content cards (18px padding, lg radius) |
| `.app-card-compact` | List item cards (14px padding, md radius) |
| `.mistake-card-hot` | Red left-border for critical errors |
| `.mistake-card-warm` | Orange left-border for moderate errors |
| `.mistake-card-cool` | Blue left-border for minor errors |
| `.mistake-card-done` | Green left-border for mastered items |

### 3. Chips / badges — use `.app-chip-*`

```html
<span class="app-chip app-chip-blue">极限</span>
<span class="app-chip app-chip-green">基础</span>
<span class="app-chip app-chip-orange">较难</span>
<span class="app-chip app-chip-red">难题</span>
<span class="app-chip app-chip-purple">证明题</span>
```

### 4. Question list — use `render_question_list_card`

```python
from views.ui.theme import render_question_list_card
render_question_list_card(q)                    # with action buttons
render_question_list_card(q, show_actions=False)  # header only
```

Input dict must have: `question_id`, `question_type`, `difficulty`. Optional: `year`, `question_preview`, `knowledge_points`.

All fields are auto-escaped via `html.escape`.

### 5. Mistake list — use `render_mistake_card`

```python
from views.ui.theme import render_mistake_card
render_mistake_card(record)
```

Input dict must have: `question_id`, `score`, `max_score`, `knowledge_point`, `root_cause`, `question_preview`, `timestamp`.

Auto-assigns severity class based on score ratio.

### 6. Flow steps — use `render_flow_steps`

```python
from views.ui.theme import render_flow_steps
render_flow_steps(["选择题目", "输入作答", "AI 批改"], active=2)
```

Active step is highlighted blue; others are muted.

### 7. Grading result — use `render_summary_header`

```python
from renderers.components.grading_result import render_summary_header
render_summary_header(gr, dr, total_score=10)
```

Renders a report-style card at the top of grading results. Automatically skips for view_only mode.

---

## Page layout conventions

| Page | Header | Key component |
|---|---|---|
| Dashboard | `render_page_header("学习仪表盘", ...)` | Welcome card + 今日建议 card |
| Practice | `render_page_header("智能刷题", ...)` | Question display + action bar |
| Grading | `render_page_header("AI 批改", ...)` + `render_flow_steps` | Summary → Score → Diagnosis → Solution → Actions |
| Question Bank | (uses `render_question` built-in) | `render_question_list_card` + collapsed filter |
| Mistakes | `render_page_header("错题本", ...)` | Quick filter chips + `mistake-card-*` cards |
| Settings | `render_page_header("系统设置", ...)` | Connection status + basic/advanced sections |
| Profile | `render_page_header("学习画像", ...)` | Stats + progress |

---

## Mobile rules (enforced by CSS)

- All `.stButton > button`: `min-height: 48px`, `width: 100%` on ≤768px
- `.block-container`: bottom padding 6.8rem to clear bottom nav
- Page title shrinks to 1.38rem
- Cards reduce padding to 12-14px
- Filters default collapsed in `st.expander(expanded=False)`

---

## Safety rules

1. All user-generated or AI-generated content in HTML must use `html.escape()`
2. All `question_id` values in HTML attributes must be escaped
3. `render_question_list_card` and `render_mistake_card` auto-escape all fields
4. Never use `unsafe_allow_html=True` with unescaped user input

---

## Adding a new page

1. Import `render_page_header` from `views.ui.theme`
2. Call `render_page_header(title, subtitle, icon)` at the top
3. Use `.app-card` / `.app-card-compact` for card wrappers
4. Use `.app-chip-*` for tags
5. Escape all dynamic content with `html.escape`
6. Test on mobile viewport (375px)

---

## Regression tests

`tests/test_ui_components.py` — 16 headless tests:
- `render_page_header` with/without subtitle, empty params
- `render_flow_steps` normal + out-of-bounds
- `inject_app_theme` idempotent
- `render_question_list_card` normal + empty + XSS
- `render_mistake_card` normal + empty + XSS
- `render_summary_header` normal + view_only skip + empty diagnosis
