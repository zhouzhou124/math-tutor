"""P40: Mobile responsive layout tests for AI grading result.

Tests verify:
- CSS injection works
- Components wrapped with correct CSS classes
- LaTeX content wrapped with grading-math-scroll
- Action buttons wrapped with grading-action-row
- Debug panel has grading-debug-panel class
- Mobile breakpoint rules exist
- Desktop not regressed
"""
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st


# ── CSS Content Tests ──

class TestGradingMobileCSS:
    """Test that the mobile CSS is correctly defined."""

    def test_css_contains_grading_result_container(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-result-container" in _GRADING_MOBILE_CSS

    def test_css_contains_grading_score_card(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-score-card" in _GRADING_MOBILE_CSS

    def test_css_contains_grading_diagnosis_card(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-diagnosis-card" in _GRADING_MOBILE_CSS

    def test_css_contains_standard_solution_card(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".standard-solution-card" in _GRADING_MOBILE_CSS

    def test_css_contains_solution_step_card(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".solution-step-card" in _GRADING_MOBILE_CSS

    def test_css_contains_grading_math_scroll(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-math-scroll" in _GRADING_MOBILE_CSS
        assert "overflow-x: auto" in _GRADING_MOBILE_CSS

    def test_css_contains_grading_action_row(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-action-row" in _GRADING_MOBILE_CSS

    def test_css_contains_grading_debug_panel(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert ".grading-debug-panel" in _GRADING_MOBILE_CSS

    def test_mobile_breakpoint_768px(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert "@media (max-width: 768px)" in _GRADING_MOBILE_CSS

    def test_mobile_action_row_column_direction(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert "flex-direction: column" in _GRADING_MOBILE_CSS

    def test_mobile_button_full_width(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert "width: 100% !important" in _GRADING_MOBILE_CSS

    def test_math_scroll_touch_scrolling(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert "-webkit-overflow-scrolling: touch" in _GRADING_MOBILE_CSS

    def test_word_break_anywhere(self):
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        assert "overflow-wrap: anywhere" in _GRADING_MOBILE_CSS
        assert "word-break: break-word" in _GRADING_MOBILE_CSS


# ── Injection Tests ──

class TestInjectGradingMobileCSS:
    """Test that CSS injection function works."""

    @patch("streamlit.markdown")
    def test_inject_calls_markdown_with_unsafe(self, mock_md):
        from renderers.components.grading_result import inject_grading_mobile_css
        inject_grading_mobile_css()
        mock_md.assert_called()
        call_args = mock_md.call_args
        assert call_args[1].get("unsafe_allow_html") is True

    @patch("streamlit.markdown")
    def test_inject_contains_style_tag(self, mock_md):
        from renderers.components.grading_result import inject_grading_mobile_css
        inject_grading_mobile_css()
        content = mock_md.call_args[0][0]
        assert "<style>" in content
        assert "</style>" in content


# ── Component Wrapping Tests ──

class TestComponentWrapping:
    """Test that render functions wrap output with correct CSS classes."""

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.caption")
    def test_score_card_wrapped_with_class(self, mock_caption, mock_container, mock_md):
        from renderers.components.grading_result import render_score_card
        mock_ctx = MagicMock()
        mock_container.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_container.return_value.__exit__ = MagicMock(return_value=False)

        render_score_card({"total": 8}, total_score=10)

        # Check that markdown was called with grading-score-card class
        calls = [str(c) for c in mock_md.call_args_list]
        has_class = any("grading-score-card" in c for c in calls)
        assert has_class, f"grading-score-card class not found in calls: {calls}"

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.info")
    @patch("streamlit.caption")
    def test_diagnosis_card_wrapped_with_class(self, mock_caption, mock_info, mock_container, mock_md):
        from renderers.components.grading_result import render_diagnosis_card
        mock_ctx = MagicMock()
        mock_container.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_container.return_value.__exit__ = MagicMock(return_value=False)

        render_diagnosis_card({"error_type": "概念错误", "root_cause": "测试"}, {"total": 5})

        calls = [str(c) for c in mock_md.call_args_list]
        has_class = any("grading-diagnosis-card" in c for c in calls)
        assert has_class, f"grading-diagnosis-card class not found in calls: {calls}"

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.info")
    @patch("streamlit.caption")
    def test_knowledge_points_wrapped_with_class(self, mock_caption, mock_info, mock_container, mock_md):
        from renderers.components.grading_result import render_knowledge_points
        mock_ctx = MagicMock()
        mock_container.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_container.return_value.__exit__ = MagicMock(return_value=False)

        render_knowledge_points(["极限", "导数"])

        calls = [str(c) for c in mock_md.call_args_list]
        has_class = any("grading-card" in c for c in calls)
        assert has_class, f"grading-card class not found in calls: {calls}"


# ── Grading Result Container Tests ──

class TestGradingResultContainer:
    """Test that render_grading_result_cards wraps in container."""

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.expander")
    @patch("streamlit.info")
    @patch("streamlit.caption")
    @patch("streamlit.divider")
    def test_result_cards_has_container_div(self, mock_divider, mock_caption, mock_info,
                                             mock_expander, mock_container, mock_md):
        from renderers.components.grading_result import render_grading_result_cards
        mock_ctx = MagicMock()
        mock_container.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_container.return_value.__exit__ = MagicMock(return_value=False)
        mock_exp_ctx = MagicMock()
        mock_expander.return_value.__enter__ = MagicMock(return_value=mock_exp_ctx)
        mock_expander.return_value.__exit__ = MagicMock(return_value=False)

        gr = {"total": 8, "comment": "不错"}
        sa = {"standard_answer": "答案内容" * 30, "steps": [{"label": "步骤1", "content": "解"}]}
        dr = {"error_type": "", "root_cause": ""}

        render_grading_result_cards(gr, sa, dr, total_score=10)

        calls = [str(c) for c in mock_md.call_args_list]
        has_container = any("grading-result-container" in c for c in calls)
        assert has_container, f"grading-result-container not found in calls: {calls}"

    @patch("streamlit.markdown")
    @patch("streamlit.container")
    @patch("streamlit.expander")
    @patch("streamlit.info")
    @patch("streamlit.caption")
    def test_view_only_has_container_div(self, mock_caption, mock_info, mock_expander,
                                          mock_container, mock_md):
        from renderers.components.grading_result import render_grading_result_cards
        mock_ctx = MagicMock()
        mock_container.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_container.return_value.__exit__ = MagicMock(return_value=False)
        mock_exp_ctx = MagicMock()
        mock_expander.return_value.__enter__ = MagicMock(return_value=mock_exp_ctx)
        mock_expander.return_value.__exit__ = MagicMock(return_value=False)

        gr = {"view_only": True}
        sa = {"standard_answer": "答案", "steps": []}
        dr = {}

        render_grading_result_cards(gr, sa, dr)

        calls = [str(c) for c in mock_md.call_args_list]
        has_container = any("grading-result-container" in c for c in calls)
        assert has_container, f"grading-result-container not found in view_only calls: {calls}"


# ── LaTeX Scroll Wrapper Tests ──

class TestLatexScrollWrapper:
    """Test that LaTeX content is wrapped with grading-math-scroll."""

    @patch("streamlit.markdown")
    def test_text_or_latex_latex_gets_scroll_wrapper(self, mock_md):
        from renderers.components.grading_result import _render_text_or_latex
        with patch("latex_utils.split_latex_text") as mock_split, \
             patch("latex_utils.render_ast") as mock_render:
            mock_split.return_value = [
                {"type": "latex", "content": "x^2 + y^2 = z^2"},
                {"type": "text", "content": "毕达哥拉斯定理"},
            ]
            _render_text_or_latex("x^2 + y^2 = z^2 毕达哥拉斯定理")

            calls = [str(c) for c in mock_md.call_args_list]
            has_scroll = any("grading-math-scroll" in c for c in calls)
            assert has_scroll, f"grading-math-scroll not found in LaTeX render calls: {calls}"

    @patch("streamlit.markdown")
    def test_text_only_no_scroll_wrapper(self, mock_md):
        from renderers.components.grading_result import _render_text_or_latex
        with patch("latex_utils.split_latex_text") as mock_split:
            mock_split.return_value = [{"type": "text", "content": "纯文本内容"}]
            _render_text_or_latex("纯文本内容")

            calls = [str(c) for c in mock_md.call_args_list]
            has_scroll = any("grading-math-scroll" in c for c in calls)
            assert not has_scroll, "grading-math-scroll should not wrap plain text"


# ── Debug Panel Tests ──

class TestDebugPanelWrapping:
    """Test that debug panel is wrapped with grading-debug-panel class."""

    @patch("streamlit.markdown")
    @patch("streamlit.expander")
    @patch("streamlit.warning")
    @patch("streamlit.caption")
    @patch("streamlit.code")
    def test_debug_panel_has_class(self, mock_code, mock_caption, mock_warning,
                                    mock_expander, mock_md):
        from renderers.components.grading_result import _render_blocked_solution_debug
        mock_exp_ctx = MagicMock()
        mock_expander.return_value.__enter__ = MagicMock(return_value=mock_exp_ctx)
        mock_expander.return_value.__exit__ = MagicMock(return_value=False)

        with patch("renderers.components.grading_result._is_admin_user", return_value=True), \
             patch("renderers.components.grading_result._should_show_solution_debug", return_value=True):
            solution = {
                "standard_solution_status": "blocked",
                "_blocked_solution_issues": ["format_issue"],
                "_blocked_solution_quality_report": {"issues": ["format_issue"]},
            }
            _render_blocked_solution_debug(solution)

            calls = [str(c) for c in mock_md.call_args_list]
            has_class = any("grading-debug-panel" in c for c in calls)
            assert has_class, f"grading-debug-panel not found in debug panel calls: {calls}"


# ── Action Button Tests ──

class TestActionButtonWrapping:
    """Test that action buttons are wrapped with grading-action-row."""

    @patch("streamlit.markdown")
    @patch("streamlit.expander")
    @patch("streamlit.warning")
    @patch("streamlit.button")
    @patch("streamlit.caption")
    def test_retry_button_has_action_row(self, mock_caption, mock_button, mock_warning,
                                          mock_expander, mock_md):
        from renderers.components.grading_result import _render_solution_failure_with_debug
        mock_exp_ctx = MagicMock()
        mock_expander.return_value.__enter__ = MagicMock(return_value=mock_exp_ctx)
        mock_expander.return_value.__exit__ = MagicMock(return_value=False)
        mock_button.return_value = False

        with patch("renderers.components.grading_result._is_admin_user", return_value=False):
            _render_solution_failure_with_debug({}, "测试失败")

            calls = [str(c) for c in mock_md.call_args_list]
            has_action_row = any("grading-action-row" in c for c in calls)
            assert has_action_row, f"grading-action-row not found in calls: {calls}"


# ── Desktop Regression Tests ──

class TestDesktopNoRegression:
    """Test that desktop layout is not affected."""

    def test_desktop_css_no_max_width_on_cards(self):
        """Desktop cards should not have forced max-width."""
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        # The mobile max-width rules should only be inside @media block
        # Outside @media, cards should have max-width: 100% (not a fixed pixel value)
        lines = _GRADING_MOBILE_CSS.split("\n")
        in_media = False
        issues = []
        for line in lines:
            if "@media" in line:
                in_media = True
            elif in_media and line.strip() == "}":
                in_media = False
            elif not in_media and "max-width" in line and "100%" not in line:
                issues.append(line.strip())
        assert not issues, f"Desktop cards have restrictive max-width: {issues}"

    def test_desktop_action_row_stays_flex_row(self):
        """Desktop action row should be flex-row, not column."""
        from renderers.components.grading_result import _GRADING_MOBILE_CSS
        # Extract the CSS outside @media block using brace depth tracking
        css = _GRADING_MOBILE_CSS
        # Find @media block boundaries
        media_start = css.find("@media")
        if media_start == -1:
            return  # No media query, nothing to check
        # Count braces to find end of @media block
        depth = 0
        media_end = media_start
        in_block = False
        for i in range(media_start, len(css)):
            if css[i] == "{":
                depth += 1
                in_block = True
            elif css[i] == "}":
                depth -= 1
                if in_block and depth == 0:
                    media_end = i
                    break
        # Check CSS outside @media for flex-direction: column
        outside_css = css[:media_start] + css[media_end + 1:]
        assert "flex-direction: column" not in outside_css, \
            "Desktop action row has flex-direction: column outside @media block"
