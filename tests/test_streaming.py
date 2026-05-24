"""P9 streaming tests — lightweight, no LLM/DB needed for unit checks."""

import pytest
from storage.grading_task_store import (
    _trim_stream_answer, MAX_STREAM_ANSWER_CHARS, update_task_stream,
)


class TestStreamAnswerTruncation:
    def test_short_text_passes_through(self):
        short = "## 步骤1：设 $f(x)=x^2$"
        assert _trim_stream_answer(short) == short

    def test_exact_max_passes_through(self):
        exact = "x" * MAX_STREAM_ANSWER_CHARS
        assert _trim_stream_answer(exact) == exact

    def test_over_limit_is_trimmed_with_fold_marker(self):
        long_text = "A" * 25000
        result = _trim_stream_answer(long_text)
        assert len(result) <= MAX_STREAM_ANSWER_CHARS + 100  # allow fold-marker overhead
        assert "已折叠" in result
        assert result.startswith("A" * 6000)
        assert result.endswith("A" * 14000)

    def test_empty_string(self):
        assert _trim_stream_answer("") == ""


class TestStreamingDisplayLogic:
    """Conservative-render logic: detect unclosed $ in streaming text."""

    @staticmethod
    def _has_unclosed_dollar(text: str) -> bool:
        """Replicate the check from grading_page streaming display."""
        dollar_count = text.count('$') - text.count('$$') * 2
        return dollar_count % 2 != 0

    def test_balanced_dollars_pass(self):
        assert not self._has_unclosed_dollar("$x^2$ is a parabola")
        assert not self._has_unclosed_dollar("$$\\int_0^1 f(x)dx$$ done")
        assert not self._has_unclosed_dollar("plain text no math")

    def test_unclosed_inline_math_detected(self):
        assert self._has_unclosed_dollar("start $x^2 mid")

    def test_mixed_display_and_inline_balanced(self):
        text = "$$\\frac{a}{b}$$ and $x=1$"
        assert not self._has_unclosed_dollar(text)

    def test_streaming_cutoff_mid_formula(self):
        # Simulates: LLM is mid-stream, last $ not yet closed
        text = "## 步骤1：求导得 $f'(x) = 2x - "
        assert self._has_unclosed_dollar(text)

    def test_after_completion_balanced(self):
        # Once the formula is completed, should be balanced
        text = "## 步骤1：求导得 $f'(x) = 2x - 1$，令其等于0"
        assert not self._has_unclosed_dollar(text)
