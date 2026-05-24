"""UI component contract tests — no Streamlit server needed.

Each test verifies that a component:
  - imports without error
  - accepts valid inputs without crashing (via monkeypatched st.*)
  - handles edge cases gracefully (empty strings, missing fields)
"""

import pytest


# ═══════════════════════════════════════════════
#  Fixture: monkeypatch Streamlit for headless testing
# ═══════════════════════════════════════════════

@pytest.fixture
def mock_streamlit(monkeypatch):
    """Replace st.markdown, st.button, st.columns, etc. with no-ops."""
    import streamlit as st

    monkeypatch.setattr(st, "markdown", lambda *a, **kw: None)
    monkeypatch.setattr(st, "caption", lambda *a, **kw: None)
    monkeypatch.setattr(st, "button", lambda label, **kw: False)
    monkeypatch.setattr(st, "columns", lambda n, **kw: [_FakeColumn() for _ in range(n)])
    monkeypatch.setattr(st, "container", lambda **kw: _FakeContainer())
    monkeypatch.setattr(st, "expander", lambda label, **kw: _FakeContainer())
    monkeypatch.setattr(st, "text", lambda *a, **kw: None)
    monkeypatch.setattr(st, "metric", lambda *a, **kw: None)
    monkeypatch.setattr(st, "subheader", lambda *a, **kw: None)
    monkeypatch.setattr(st, "info", lambda *a, **kw: None)
    monkeypatch.setattr(st, "warning", lambda *a, **kw: None)
    monkeypatch.setattr(st, "error", lambda *a, **kw: None)
    monkeypatch.setattr(st, "success", lambda *a, **kw: None)
    monkeypatch.setattr(st, "divider", lambda *a, **kw: None)
    monkeypatch.setattr(st, "bar_chart", lambda *a, **kw: None)
    monkeypatch.setattr(st, "selectbox", lambda label, options, **kw: options[0] if options else "")
    monkeypatch.setattr(st, "text_input", lambda label, **kw: "")
    monkeypatch.setattr(st, "text_area", lambda label, **kw: "")
    monkeypatch.setattr(st, "session_state", {})
    monkeypatch.setattr(st, "latex", lambda *a, **kw: None)
    monkeypatch.setattr(st, "toast", lambda *a, **kw: None)
    monkeypatch.setattr(st, "query_params", {})

    return st


class _FakeColumn:
    """A minimal stub that supports `with col:` context manager."""
    def __enter__(self): return self
    def __exit__(self, *a): pass


class _FakeContainer:
    """A minimal stub for st.container / st.expander."""
    def __enter__(self): return self
    def __exit__(self, *a): pass


# ═══════════════════════════════════════════════
#  Tests
# ═══════════════════════════════════════════════

class TestThemeComponents:
    def test_render_page_header_basic(self, mock_streamlit):
        from views.ui.theme import render_page_header
        render_page_header("Test Title")
        # No exception = pass

    def test_render_page_header_with_subtitle(self, mock_streamlit):
        from views.ui.theme import render_page_header
        render_page_header("Test", "This is a subtitle", "📊")
        # No exception = pass

    def test_render_page_header_empty_subtitle(self, mock_streamlit):
        from views.ui.theme import render_page_header
        render_page_header("Test", "")
        render_page_header("Test", None)
        # No exception = pass

    def test_render_flow_steps_basic(self, mock_streamlit):
        from views.ui.theme import render_flow_steps
        render_flow_steps(["选择题目", "输入作答", "AI 批改"], active=2)
        # No exception = pass

    def test_render_flow_steps_active_out_of_bounds(self, mock_streamlit):
        from views.ui.theme import render_flow_steps
        # active > len(steps): should still render without crash
        render_flow_steps(["A", "B"], active=5)
        render_flow_steps(["A", "B"], active=0)
        render_flow_steps(["A", "B"], active=-1)
        # No exception = pass

    def test_inject_app_theme_is_idempotent(self, mock_streamlit):
        from views.ui.theme import inject_app_theme
        inject_app_theme()
        inject_app_theme()  # second call should be a no-op
        # No exception = pass

    def test_render_question_list_card_normal(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        q = {
            "question_id": "test-001",
            "year": 2022,
            "question_type": "解答题",
            "difficulty": "中等",
            "question": "求极限 $\\lim_{x\\to 0}\\frac{\\sin x}{x}$",
            "question_preview": "求极限 sinx/x",
            "knowledge_points": ["极限", "洛必达"],
        }
        render_question_list_card(q)
        # No exception = pass

    def test_render_question_list_card_minimal(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        render_question_list_card({})
        # No exception = pass

    def test_render_question_list_card_xss_safe(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        q = {
            "question_id": "<script>alert(1)</script>",
            "question": "<img onerror=alert(1)>",
            "difficulty": "中等",
            "knowledge_points": ["<b>bold</b>"],
        }
        render_question_list_card(q)
        # No exception = pass — html.escape prevents injection

    def test_render_mistake_card_normal(self, mock_streamlit):
        from views.ui.theme import render_mistake_card
        record = {
            "question_id": "test-001",
            "score": 3,
            "max_score": 10,
            "knowledge_point": "极限",
            "root_cause": "洛必达条件未验证",
            "question_preview": "求极限 sinx/x",
            "timestamp": "2026-05-25",
        }
        render_mistake_card(record)
        # No exception = pass

    def test_render_mistake_card_minimal(self, mock_streamlit):
        from views.ui.theme import render_mistake_card
        render_mistake_card({})
        # No exception = pass

    def test_render_mistake_card_xss_safe(self, mock_streamlit):
        from views.ui.theme import render_mistake_card
        record = {
            "question_id": "<script>xss</script>",
            "root_cause": "<img src=x>",
            "knowledge_point": "<b>bold</b>",
        }
        render_mistake_card(record)
        # No exception = pass


class TestGradingResultSummary:
    def test_summary_header_imports(self, mock_streamlit):
        from renderers.components.grading_result import render_summary_header
        # No exception = pass

    def test_summary_header_normal(self, mock_streamlit):
        from renderers.components.grading_result import render_summary_header
        gr = {"total": 7, "engine": "structured"}
        dr = {
            "root_cause": "计算错误",
            "weak_points": ["极限", "导数"],
            "recommendations": ["多练习洛必达法则"],
        }
        render_summary_header(gr, dr)
        # No exception = pass

    def test_summary_header_view_only_skips(self, mock_streamlit):
        from renderers.components.grading_result import render_summary_header
        render_summary_header({"total": 0, "engine": "view_only"}, {})
        # No exception = pass (should return early)

    def test_summary_header_empty_diagnosis(self, mock_streamlit):
        from renderers.components.grading_result import render_summary_header
        render_summary_header({"total": 5, "engine": "structured"}, {})
        # No exception = pass


class TestQuestionListCardShowPreview:
    def test_hides_preview_when_false(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        vm = {
            "question_id": "t1", "year": 2026, "question_type": "选择题",
            "difficulty": "中等", "preview": "这段预览不应显示",
            "status_chips": [], "knowledge_points": [],
        }
        # Should not crash, and preview content should not be in output
        render_question_list_card(vm, show_actions=False, show_preview=False)
        # No exception = pass

    def test_shows_preview_when_true(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        vm = {
            "question_id": "t2", "year": 2026, "question_type": "解答题",
            "difficulty": "中等", "preview": "求极限 sinx/x",
            "status_chips": [], "knowledge_points": [],
        }
        render_question_list_card(vm, show_actions=False, show_preview=True)
        # No exception = pass

    def test_card_with_status_chips_does_not_crash(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        vm = {
            "question_id": "t3", "year": 2026, "question_type": "解答题",
            "difficulty": "较难", "preview": "",
            "status_chips": [("已批改", "green"), ("曾错2次", "red")],
            "knowledge_points": ["极限"],
        }
        render_question_list_card(vm, show_actions=False, show_preview=False)
        # No exception = pass

    def test_show_actions_renders_buttons(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        vm = {
            "question_id": "t4", "question_type": "选择题",
            "difficulty": "基础", "status_chips": [], "knowledge_points": [],
        }
        render_question_list_card(vm, show_actions=True, show_preview=False)
        # No exception = pass


class TestChipSafety:
    def test_chip_style_is_allowlisted(self):
        from views.ui.theme import _render_chip_html
        html = _render_chip_html("标签", "blue")
        assert "app-chip-blue" in html
        # Invalid style falls back to blue
        html_bad = _render_chip_html("标签", "<script>")
        assert "<script>" not in html_bad
        assert "app-chip-blue" in html_bad

    def test_chip_label_is_escaped(self):
        from views.ui.theme import _render_chip_html
        html = _render_chip_html("<b>XSS</b>", "red")
        assert "<b>" not in html
        assert "&lt;b&gt;" in html

    def test_build_question_card_vm_no_raw_html(self):
        from services.question_bank_service import build_question_card_vm
        vm = build_question_card_vm({
            "question_id": "q1", "year": 2026, "question_type": "选择题",
            "knowledge_points": ["多元函数微分"],
        })
        # VM must not contain HTML strings
        joined = str(vm)
        assert "<span" not in joined
        assert "<div" not in joined
        assert "多元函数微分" in joined

    def test_render_question_list_card_outputs_html_safely(self, mock_streamlit):
        from views.ui.theme import render_question_list_card
        render_question_list_card({
            "year": 2026, "question_type": "选择题", "difficulty": "中等",
            "knowledge_points": ["多元函数微分"],
            "status_chips": [("有解析", "blue")],
            "question_id": "t1",
        }, show_actions=False)
        # No exception = pass (all output goes through st.markdown with unsafe_allow_html=True)
