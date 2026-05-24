"""P13-5: LaTeX choice question embedded option extraction."""

import pytest
from services.question_option_tools import (
    extract_embedded_options_latex_safe,
    normalize_choice_question_options,
)


class TestExtractEmbeddedOptions:
    def test_basic_extraction(self):
        text = "题干内容 (A) 选项甲 (B) 选项乙 (C) 选项丙 (D) 选项丁"
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == "题干内容"
        assert opts["A"] == "选项甲"
        assert opts["B"] == "选项乙"
        assert opts["C"] == "选项丙"
        assert opts["D"] == "选项丁"

    def test_chinese_parens(self):
        text = "题干（A）甲（B）乙（C）丙（D）丁"
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == "题干"
        assert opts["A"] == "甲"
        assert opts["D"] == "丁"

    def test_latex_content_preserved(self):
        text = (
            r"设函数满足条件，则（ ）"
            r"(A) $\frac{\partial f}{\partial x}$ 不存在 "
            r"(B) $\frac{\partial f}{\partial x}$ 存在但不可微 "
            r"(C) $f$ 可微 "
            r"(D) 以上都不对"
        )
        stem, opts = extract_embedded_options_latex_safe(text)
        assert "(A)" not in stem
        assert "(B)" not in stem
        assert r"\frac" in opts["A"]
        assert "存在但不可微" in opts["B"]
        assert opts["C"] == r"$f$ 可微"

    def test_single_a_reference_not_extracted(self):
        text = "由条件 (A) 可知函数连续。"
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == text
        assert opts == {}

    def test_two_options_not_extracted(self):
        text = "题干 (A) 甲 (B) 乙"
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == text
        assert opts == {}

    def test_empty_input(self):
        stem, opts = extract_embedded_options_latex_safe("")
        assert stem == ""
        assert opts == {}


class TestNormalizeChoiceQuestion:
    def test_extracts_and_removes_from_stem(self):
        q = {
            "question_type": "选择题",
            "question": "题干 (A) 甲 (B) 乙 (C) 丙 (D) 丁",
        }
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["options"]["A"] == "甲"
        assert out["options"]["D"] == "丁"
        assert out["_options_extracted_from_stem"] is True

    def test_existing_options_overridden_by_embedded(self):
        q = {
            "question_type": "选择题",
            "question": "题干 (A) 新A (B) 新B (C) 新C (D) 新D",
            "options": {"A": "旧A", "B": "旧B", "C": "旧C", "D": "旧D"},
        }
        out = normalize_choice_question_options(q)
        assert out["options"]["A"] == "新A"

    def test_non_choice_unchanged(self):
        q = {"question_type": "解答题", "question": "证明 (A) 成立。"}
        out = normalize_choice_question_options(q)
        assert out == q

    def test_no_embedded_options_normalizes_existing(self):
        q = {
            "question_type": "选择题",
            "question": "选正确的选项",
            "options": ["甲", "乙", "丙", "丁"],
        }
        out = normalize_choice_question_options(q)
        assert out["options"]["A"] == "甲"
        assert out["options"]["C"] == "丙"

    def test_does_not_mutate_input(self):
        q = {
            "question_type": "选择题",
            "question": "题干 (A) 甲 (B) 乙 (C) 丙 (D) 丁",
        }
        original_question = q["question"]
        normalize_choice_question_options(q)
        assert q["question"] == original_question  # unchanged

    def test_missing_question_type_still_extracts_when_four_options(self):
        q = {"question": "题干 (A) 甲 (B) 乙 (C) 丙 (D) 丁"}
        out = normalize_choice_question_options(q)
        # P13-7: detects 4+ options even without explicit question_type
        assert out["question"] == "题干"
        assert out["options"]["A"] == "甲"
        assert out["options"]["D"] == "丁"


class TestNormalizeLatexOptionMarkers:
    def test_dollar_paren_slash_form(self):
        from services.question_option_tools import normalize_latex_option_markers
        text = r"$\(A\)$ 选项A $\(B\)$ 选项B"
        out = normalize_latex_option_markers(text)
        assert "(A)" in out
        assert "(B)" in out
        assert r"$\(A\)$" not in out

    def test_bare_slash_paren(self):
        from services.question_option_tools import normalize_latex_option_markers
        text = r"\(A\) 选项A \(B\) 选项B"
        out = normalize_latex_option_markers(text)
        assert "(A)" in out
        assert r"\(" not in out

    def test_dollar_paren_form(self):
        from services.question_option_tools import normalize_latex_option_markers
        text = r"$(A)$ 选项A $（B）$ 选项B"
        out = normalize_latex_option_markers(text)
        assert "(A)" in out
        assert "(B)" in out  # full-width parens normalized to half-width
        assert "$(A)$" not in out

    def test_mathrm_form(self):
        from services.question_option_tools import normalize_latex_option_markers
        text = r"$\mathrm{A}$ 甲 $\text{B}$ 乙"
        out = normalize_latex_option_markers(text)
        assert "(A)" in out
        assert "(B)" in out

    def test_empty_text(self):
        from services.question_option_tools import normalize_latex_option_markers
        assert normalize_latex_option_markers("") == ""
        assert normalize_latex_option_markers(None) == ""


class TestExtractOptionsWithLatexMarkers:
    def test_extract_after_normalizing_latex_markers(self):
        from services.question_option_tools import extract_embedded_options_latex_safe
        text = (
            r"题干，则（ ）"
            r"$\(A\)$ $\frac{1}{a}$ "
            r"$\(B\)$ $-\frac{1}{a}$ "
            r"$\(C\)$ $0$ "
            r"$\(D\)$ $1$"
        )
        stem, opts = extract_embedded_options_latex_safe(text)
        assert r"$\(A\)$" not in stem
        assert opts["A"] == r"$\frac{1}{a}$"
        assert opts["B"] == r"$-\frac{1}{a}$"

    def test_full_normalize_handles_latex_markers(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question_type": "选择题",
            "question": r"题干 $\(A\)$ 甲 $\(B\)$ 乙 $\(C\)$ 丙 $\(D\)$ 丁",
        }
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["options"]["A"] == "甲"
        assert out["options"]["D"] == "丁"

    def test_dollar_paren_form_with_real_content(self):
        from services.question_option_tools import extract_embedded_options_latex_safe
        text = (
            r"题干 "
            r"$(A)$ $a\neq -4,b$ 为任意实数 "
            r"$(B)$ $a=4,b=1$ "
            r"$(C)$ $a\neq -4$ 且 $b\neq 1$ "
            r"$(D)$ $a=4,b$ 为任意实数"
        )
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == "题干"
        assert opts["A"].startswith(r"$a\neq -4")
        assert opts["B"] == r"$a=4,b=1$"
        assert "且" in opts["C"]
        assert opts["D"].startswith(r"$a=4")

    def test_dollar_paren_full_normalize(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question_type": "选择题",
            "question": r"题干 $(A)$ 甲 $(B)$ 乙 $(C)$ 丙 $(D)$ 丁",
        }
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["options"]["A"] == "甲"
        assert out["options"]["D"] == "丁"

    def test_normalize_markers_removes_dollar_paren(self):
        from services.question_option_tools import normalize_latex_option_markers
        text = r"题干 $(A)$ 甲 $(B)$ 乙 $(C)$ 丙 $(D)$ 丁"
        out = normalize_latex_option_markers(text)
        assert "$(A)$" not in out
        assert "(A)" in out
        assert "(D)" in out


class TestGoldenCases:
    def test_real_matrix_choice_with_dollar_option_markers(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question_type": "选择题",
            "question": (
                r"设 $\alpha_1=\begin{pmatrix}1\\2\\-1\end{pmatrix}$，"
                r"$\alpha_2=\begin{pmatrix}1\\0\\1\end{pmatrix}$，"
                r"$\alpha_3=\begin{pmatrix}-1\\a\\3\end{pmatrix}$，"
                r"$\beta=\begin{pmatrix}3\\2\\b\end{pmatrix}$，"
                r"$a,b$ 为实数。已知 $\beta$ 可由 $\alpha_1,\alpha_2,\alpha_3$ 线性表示，"
                r"但不能由 $\alpha_1,\alpha_2$ 表示，则 "
                r"$(A)$ $a\neq -4,b$ 为任意实数 "
                r"$(B)$ $a=4,b=1$ "
                r"$(C)$ $a\neq -4$ 且 $b\neq 1$ "
                r"$(D)$ $a=4,b$ 为任意实数"
            ),
        }

        out = normalize_choice_question_options(q)

        # Stem must be clean — no option markers, no option content
        assert "$(A)$" not in out["question"]
        assert "为任意实数" not in out["question"]
        # Each option extracted with full LaTeX content
        assert out["options"]["A"].startswith(r"$a\neq -4")
        assert out["options"]["B"] == r"$a=4,b=1$"
        assert "且" in out["options"]["C"]
        assert out["options"]["D"].startswith(r"$a=4")
        # All 4 options present
        assert set(out["options"].keys()) == {"A", "B", "C", "D"}


class TestP137Fixes:
    def test_extracts_without_question_type_when_four_options(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question": (
                r"已知 $I_1,I_2$，则 "
                r"(A) $I_1>I_2$ "
                r"(B) $I_1<I_2$ "
                r"(C) $I_1=I_2$ "
                r"(D) 无法判断"
            )
        }
        out = normalize_choice_question_options(q)
        assert "(A)" not in out["question"]
        assert out["options"]["A"] == r"$I_1>I_2$"
        assert out["options"]["D"] == "无法判断"

    def test_extract_inline_options_same_line(self):
        from services.question_option_tools import extract_embedded_options_latex_safe
        text = (
            r"题干 "
            r"(A) $I_1>I_2,J_1>J_2$ "
            r"(B) $I_1>I_2,J_1<J_2$ "
            r"(C) $I_1<I_2,J_1>J_2$ "
            r"(D) $I_1<I_2,J_1<J_2$"
        )
        stem, opts = extract_embedded_options_latex_safe(text)
        assert stem == "题干"
        assert opts["A"] == r"$I_1>I_2,J_1>J_2$"
        assert opts["D"] == r"$I_1<I_2,J_1<J_2$"

    def test_choice_option_latex_preserved(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question": (
                r"题干 "
                r"(A) $I_1 \gt I_2, J_1 \gt J_2$ "
                r"(B) $I_1 \lt I_2, J_1 \lt J_2$ "
                r"(C) $I_1=I_2$ "
                r"(D) 无法判断"
            )
        }
        out = normalize_choice_question_options(q)
        assert r"I_1" in out["options"]["A"]
        assert r"J_1" in out["options"]["A"]

    def test_dollar_paren_full_normalize_without_question_type(self):
        from services.question_option_tools import normalize_choice_question_options
        q = {
            "question": r"题干 $(A)$ 甲 $(B)$ 乙 $(C)$ 丙 $(D)$ 丁",
        }
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["options"]["A"] == "甲"
        assert out["options"]["D"] == "丁"


class TestStemFieldSync:
    def test_normalize_syncs_raw_question_text_after_extract(self):
        from services.question_option_tools import normalize_choice_question_options
        raw = "题干 (A) 甲 (B) 乙 (C) 丙 (D) 丁"
        q = {"question_type": "选择题", "question": raw, "raw_question_text": raw}
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["stem"] == "题干"
        assert out["raw_question_text"] == "题干"
        assert "(A)" not in out["raw_question_text"]
        assert out["options"]["A"] == "甲"

    def test_preview_without_question_type_syncs_clean_stem_fields(self):
        from services.question_option_tools import normalize_choice_question_options
        raw = (
            r"题干 $(A)$ $I_1>I_2$ $(B)$ $I_1<I_2$ "
            r"$(C)$ 相等 $(D)$ 无法判断"
        )
        q = {"question": raw, "raw_question_text": raw}
        out = normalize_choice_question_options(q)
        assert out["question"] == "题干"
        assert out["raw_question_text"] == "题干"
        assert out["options"]["A"] == r"$I_1>I_2$"

    def test_original_question_with_options_preserved_for_debug(self):
        from services.question_option_tools import normalize_choice_question_options
        raw = "题干 (A) 甲 (B) 乙 (C) 丙 (D) 丁"
        out = normalize_choice_question_options({
            "question_type": "选择题",
            "question": raw,
        })
        assert out["_original_question_with_options"] == raw
        assert out["question"] == "题干"
