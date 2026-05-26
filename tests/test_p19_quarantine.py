"""P19-3: Broken Solution Quarantine tests."""

import pytest


class TestBrokenStructuredDetection:
    def test_structured_with_broken_frac_is_detected(self):
        from services.solution_quality import structured_has_broken_latex
        structured = {
            "steps": [{
                "label": "步骤1",
                "blocks": [{"type": "latex", "content": r"\frac{} x }{ y }"}],
            }]
        }
        assert structured_has_broken_latex(structured)

    def test_clean_structured_passes(self):
        from services.solution_quality import structured_has_broken_latex
        structured = {
            "steps": [{
                "label": "步骤1",
                "blocks": [{"type": "latex", "content": r"\frac{x}{y}"}],
            }]
        }
        assert not structured_has_broken_latex(structured)

    def test_text_blocks_ignored(self):
        from services.solution_quality import structured_has_broken_latex
        structured = {
            "steps": [{
                "label": "步骤1",
                "blocks": [{"type": "text", "content": r"\frac{}"}],
            }]
        }
        assert not structured_has_broken_latex(structured)


class TestSolutionRenderable:
    def test_broken_solution_not_renderable(self):
        from services.solution_quality import solution_is_renderable
        assert not solution_is_renderable({"standard_answer": r"\frac{} x }{ y }"})

    @pytest.mark.parametrize("bad", [
        "步骤1：乱码 �A0� 因此最终答案。",
        r"步骤1：非法矩阵 $\left\begin{array}{cc}1&0\\0&1\end{array}$ 因此最终答案。",
        r"步骤1：孤立右括号 $\right)$ 因此最终答案。",
        r"步骤1：三美元 $$$x=1$$$ 因此最终答案。",
        r"步骤1：空分式 $\frac{}$ 因此最终答案。",
        r"步骤1：红色残片 \textcolor{red}{x=1} 因此最终答案。",
    ])
    def test_new_broken_patterns_not_renderable(self, bad):
        from services.solution_quality import solution_is_renderable
        assert not solution_is_renderable({"standard_answer": bad})

    def test_clean_solution_is_renderable(self):
        from services.solution_quality import solution_is_renderable
        ans = "步骤1：由凸函数定义可得。" + "详细推导" * 50
        assert solution_is_renderable({"standard_answer": ans})

    def test_broken_structured_makes_solution_not_renderable(self):
        from services.solution_quality import solution_is_renderable
        sol = {
            "standard_answer": "正常文本内容",
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{"type": "latex", "content": r"\frac{}"}],
                }]
            }
        }
        assert not solution_is_renderable(sol)


class TestNormalizeSolutionForRenderQuarantine:
    def test_broken_raw_answer_gets_failed_status(self):
        from services.grading_adapter import normalize_solution_for_render
        # Multiple unfixable fragments: empty frac repeated
        sol = {"standard_answer": r"\frac{} \frac{} \frac{}"}
        out = normalize_solution_for_render(sol)
        assert out.get("standard_solution_status") == "failed"
        assert out["_structured"] is None

    def test_broken_structured_is_dropped_and_rebuilt_clean(self):
        from services.grading_adapter import normalize_solution_for_render
        from services.solution_quality import structured_has_broken_latex
        sol = {
            "standard_answer": "由凸函数定义可得。" + "x" * 140,
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{"type": "latex", "content": r"\frac{} x }{ y }"}],
                }]
            },
        }
        out = normalize_solution_for_render(sol)
        # Old broken structured must be dropped; new one rebuilt from clean text
        assert not structured_has_broken_latex(out.get("_structured"))

    def test_clean_structured_is_kept(self):
        from services.grading_adapter import normalize_solution_for_render
        sol = {
            "standard_answer": r"由题意可得 $\frac{x}{y}$。" + "x" * 140,
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{"type": "latex", "content": r"\frac{x}{y}"}],
                }]
            },
        }
        out = normalize_solution_for_render(sol)
        assert out["_structured"] is not None
        assert out.get("standard_solution_status") != "failed"


class TestCanonicalCacheInvalidation:
    def test_old_format_entry_drops_structured_and_ir(self):
        from services.grading_adapter import normalize_canonical_entry
        entry = {
            "format_version": "old",
            "structured": {"steps": []},
            "canonical_ir": {"proof_trace": {}},
        }
        out = normalize_canonical_entry(entry)
        assert out.get("structured") is None
        assert out.get("canonical_ir") is None
        assert out.get("invalidated_reason") == "old_solution_format"

    def test_current_format_entry_keeps_structured_and_ir(self):
        from services.grading_adapter import normalize_canonical_entry, SOLUTION_FORMAT_VERSION
        entry = {
            "format_version": SOLUTION_FORMAT_VERSION,
            "standard_answer": "步骤1：推导。步骤2：验证。综上，结论成立。" + "x" * 140,
            "structured": {"steps": [{"label": "s1"}]},
            "canonical_ir": {"proof_trace": {}},
        }
        out = normalize_canonical_entry(entry)
        assert out.get("structured") is not None
        assert out.get("canonical_ir") is not None

    def test_broken_structured_with_dropped_reason(self):
        from services.grading_adapter import normalize_solution_for_render
        from services.solution_quality import structured_has_broken_latex
        sol = {
            "standard_answer": "正常文字",
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{"type": "latex", "content": r"\frac{f(x)}"}],
                }]
            },
        }
        out = normalize_solution_for_render(sol)
        # Broken structured dropped, rebuilt from clean raw text
        assert not structured_has_broken_latex(out.get("_structured"))
        assert out.get("_structured_dropped_reason") == "broken_latex"

    def test_repaired_split_frac_can_rebuild(self):
        from services.grading_adapter import normalize_solution_for_render
        sol = {"standard_answer": r"\frac{f(x)-f(u)}" + "\n" + "x-u"}
        out = normalize_solution_for_render(sol)
        assert r"\frac{f(x)-f(u)}{x-u}" in out["standard_answer"]


class TestSolutionCompleteness:
    def test_proof_without_final_marker_is_incomplete(self):
        from services.solution_quality import solution_is_complete
        sol = {
            "standard_answer": "步骤1 证明必要性。步骤2 证明充分性。",
            "_structured": {
                "steps": [
                    {"label": "步骤1", "blocks": [{"type": "text", "content": "证明必要性"}]},
                    {"label": "步骤2", "blocks": [{"type": "text", "content": "证明充分性"}]},
                ]
            }
        }
        q = {"question_type": "证明题", "question": "证明命题成立。"}
        assert solution_is_complete(sol, q) is False

    def test_proof_with_final_marker_is_complete(self):
        from services.solution_quality import solution_is_complete
        sol = {
            "standard_answer": "步骤1 证明必要性。步骤2 证明充分性。综上，命题得证。",
            "_structured": {
                "steps": [
                    {"label": "步骤1", "blocks": [{"type": "text", "content": "证明必要性"}]},
                    {"label": "步骤2", "blocks": [{"type": "text", "content": "证明充分性"}]},
                    {"label": "步骤3", "blocks": [{"type": "text", "content": "综上，命题得证。"}]},
                ]
            }
        }
        q = {"question_type": "证明题", "question": "证明命题成立。"}
        assert solution_is_complete(sol, q) is True

    def test_truncated_solution_not_complete(self):
        from services.solution_quality import solution_is_complete
        sol = {"standard_answer": "由题意可得", "_structured": {"steps": []}}
        assert solution_is_complete(sol, {}) is False

    def test_short_non_proof_with_final_marker_is_complete(self):
        from services.solution_quality import solution_is_complete
        ans = "步骤1：求导。步骤2：代入。故答案为 $x=1$。" + "x" * 120
        sol = {"standard_answer": ans}
        assert solution_is_complete(sol, {"question_type": "解答题"}) is True

    def test_empty_marker_is_incomplete(self):
        from services.solution_quality import solution_is_complete
        assert solution_is_complete({"standard_answer": "暂无可用标准解答。"}) is False
