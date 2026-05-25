"""P21: Prompt loader tests."""

import pytest
from services.prompt_loader import load_prompt


def test_load_paperspine_prompt():
    text = load_prompt("math_solution_paperspine_style.md")
    assert r"\frac{分子}{分母}" in text
    assert "综上" in text or "aligned" in text

def test_load_self_review_prompt():
    text = load_prompt("math_solution_self_review.md")
    assert "JSON" in text
    assert "should_regenerate" in text

def test_missing_prompt_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt.md")
