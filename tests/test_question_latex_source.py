"""Tests for question-bank LaTeX source normalization and validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.latex_source_tools import (
    normalize_question_latex_source,
    validate_question_latex_source,
)


def test_remove_math_wrapped_question_number():
    s = normalize_question_latex_source("$22.$【本题满分12分】")
    assert s.startswith("22.")


def test_fix_missing_x_in_interval():
    s = normalize_question_latex_source(r"-1\le 1")
    assert r"-1\le x\le 1" in s


def test_fix_missing_x_in_interval_spaced():
    s = normalize_question_latex_source(r"-1 \le 1")
    assert r"-1 \le x \le 1" in s


def test_validate_odd_dollar_count():
    issues = validate_question_latex_source("设 $f(x)=x")
    assert any("$ 数量" in i for i in issues)


def test_validate_cases_without_display_math():
    issues = validate_question_latex_source(r"g(x)=\begin{cases}x\\0\end{cases}")
    assert any("cases" in i for i in issues)


def test_validate_question_number_in_math():
    issues = validate_question_latex_source("$22.$【本题满分12分】")
    assert any("题号" in i for i in issues)


def test_validate_clean_source_no_issues():
    issues = validate_question_latex_source(
        "22. 设 $f(x)$ 在 $[0,1]$ 上连续。\n$$\ng(x)=\\begin{cases}x\\\\0\\end{cases}\n$$"
    )
    assert len(issues) == 0


if __name__ == "__main__":
    tests = [
        test_remove_math_wrapped_question_number,
        test_fix_missing_x_in_interval,
        test_fix_missing_x_in_interval_spaced,
        test_validate_odd_dollar_count,
        test_validate_cases_without_display_math,
        test_validate_question_number_in_math,
        test_validate_clean_source_no_issues,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
