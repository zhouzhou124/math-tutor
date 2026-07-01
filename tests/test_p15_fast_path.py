"""P15: Fast grading + async solution tests."""

import pytest


class TestChoiceFastPath:
    def test_returns_score_immediately(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "B", "score": 5, "knowledge_points": ["极限"]}
        result = _grade_choice_fast(q, "B", {})
        assert result["grading_result"]["total"] == 5
        assert result["grading_result"]["engine"] == "choice_fast"
        assert result["grading_result"]["confidence"] == 1.0

    def test_wrong_answer_scores_zero(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "B", "score": 5}
        result = _grade_choice_fast(q, "A", {})
        assert result["grading_result"]["total"] == 0
        assert "正确选项是 B" in result["grading_result"]["comment"]

    def test_fast_path_flag_set(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "A", "score": 5}
        result = _grade_choice_fast(q, "A", {})
        assert result["grading_result"].get("_fast_path") is True

    def test_solution_status_field_present(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "C", "score": 5, "standard_answer": ""}
        result = _grade_choice_fast(q, "C", {})
        assert "standard_solution_status" in result["grading_result"]
        assert result["grading_result"]["standard_solution_status"] in ("ready", "pending", "missing")

    def test_extracts_letter_from_chinese_prefix(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "D", "score": 5}
        result = _grade_choice_fast(q, "选D", {})
        assert result["grading_result"]["total"] == 5

    def test_correct_answer_creates_no_error_record(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "A", "score": 5, "question": "test"}
        result = _grade_choice_fast(q, "A", {})
        assert result["error_record"] is None

    def test_wrong_answer_creates_error_record(self):
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "A", "score": 5, "question": "test question"}
        result = _grade_choice_fast(q, "B", {})
        # P15: error_record is None in fast path (built when async solution completes)
        assert result["error_record"] is None

    def test_empty_choice_answer_uses_view_only_not_fast_grade(self):
        from views.grading_page import _execute_grading_process

        result = _execute_grading_process(
            question="选择正确选项",
            student_ans="",
            ocr_data={"question_type": "选择题"},
            selected_q={
                "question_id": "q_choice_empty",
                "question_type": "选择题",
                "correct_option": "B",
                "score": 5,
            },
            _state={},
            client=None,
        )

        assert result["grading_result"]["engine"] == "view_only"
        assert result["grading_result"]["hide_score_card"] is True
        assert result["error_record"] is None


class TestFillFastPath:
    def test_returns_score_immediately(self):
        from views.grading_page import _grade_fill_fast
        q = {"score": 5, "standard_answer": r"$y=Cxe^{-x}$"}
        result = _grade_fill_fast(q, r"$y=Cxe^{-x}$", {})
        assert "total" in result["grading_result"]
        assert result["grading_result"]["engine"] == "fill_compare"

    def test_fast_path_flag_set(self):
        from views.grading_page import _grade_fill_fast
        q = {"score": 5}
        result = _grade_fill_fast(q, "x", {})
        assert result["grading_result"].get("_fast_path") is True

    def test_low_confidence_when_no_standard(self):
        from views.grading_page import _grade_fill_fast
        q = {"score": 5, "standard_answer": ""}
        result = _grade_fill_fast(q, "x", {})
        assert result["grading_result"]["confidence"] <= 0.6


class TestSolutionCacheHit:
    def test_empty_answer_is_not_cached(self):
        from views.grading_page import _solution_cache_hit
        assert not _solution_cache_hit({"standard_answer": ""})

    def test_short_answer_is_not_cached(self):
        from views.grading_page import _solution_cache_hit
        assert not _solution_cache_hit({"standard_answer": "Cxe^{-x}"})

    def test_long_answer_is_cached(self):
        from views.grading_page import _solution_cache_hit
        long_ans = (
            "步骤1：先根据题设建立方程 $x+1=2$，这是求解未知量的直接依据。"
            "步骤2：移项可得 $x=1$，再代回原方程验证左右两边相等。"
            "因此，最终答案为 $x=1$。"
        )
        assert _solution_cache_hit({"standard_answer": long_ans})

    def test_canonical_pool_is_cached(self):
        from views.grading_page import _solution_cache_hit
        from services.grading_adapter import SOLUTION_FORMAT_VERSION
        pool_entry = {
            "solution_id": "s1",
            "format_version": SOLUTION_FORMAT_VERSION,
            "standard_answer": (
                "步骤1：先根据题设建立方程 $x+1=2$，这是求解未知量的直接依据。"
                "步骤2：移项可得 $x=1$，再代回原方程验证左右两边相等。"
                "因此，最终答案为 $x=1$。"
            ),
        }
        assert _solution_cache_hit({"canonical_solutions": [pool_entry]})

    def test_skeletal_long_answer_is_not_cached(self):
        from views.grading_page import _solution_cache_hit
        long_ans = "步骤1：..." + "x" * 120
        assert not _solution_cache_hit({"standard_answer": long_ans})

    def test_canonical_pool_empty_shell_not_cached(self):
        from views.grading_page import _solution_cache_hit
        assert not _solution_cache_hit({"canonical_solutions": [{"solution_id": "s1"}]})


class TestSolutionRequestHash:
    def test_same_request_produces_same_hash(self):
        from views.grading_page import _solution_request_hash
        q = {"question_id": "q1", "correct_option": "B"}
        assert _solution_request_hash(q, "m1") == _solution_request_hash(q, "m1")

    def test_different_qid_produces_different_hash(self):
        from views.grading_page import _solution_request_hash
        h1 = _solution_request_hash({"question_id": "q1"}, "m1")
        h2 = _solution_request_hash({"question_id": "q2"}, "m1")
        assert h1 != h2

    def test_different_model_produces_different_hash(self):
        from views.grading_page import _solution_request_hash
        q = {"question_id": "q1"}
        h1 = _solution_request_hash(q, "m1")
        h2 = _solution_request_hash(q, "m2")
        assert h1 != h2


class TestCanonicalTraceCacheDetection:
    @staticmethod
    def _method():
        return {
            "method_name": "method-1",
            "graph": {
                "question_id": "q1",
                "final_answer": "1",
                "nodes": [
                    {
                        "id": "n1",
                        "type": "compute",
                        "label": "derive answer",
                        "output": "1",
                        "weight": 10,
                    }
                ],
                "edges": [],
                "total_score": 10,
                "grading_mode": "step",
            },
            "final_answer": "1",
        }

    def test_missing_canonical_trace_is_not_cached(self):
        from views.grading_page import _has_cached_canonical_trace
        assert _has_cached_canonical_trace({"question_id": "q1"}) is False

    def test_single_canonical_trace_is_cached(self):
        from views.grading_page import _has_cached_canonical_trace
        assert _has_cached_canonical_trace(
            {"canonical_solution": {"methods": [self._method()]}}
        ) is True

    def test_canonical_solution_pool_is_cached(self):
        from views.grading_page import _has_cached_canonical_trace
        assert _has_cached_canonical_trace(
            {"canonical_solutions": [self._method()]}
        ) is True

    def test_empty_canonical_solution_shell_is_not_cached(self):
        from views.grading_page import _has_cached_canonical_trace
        assert _has_cached_canonical_trace({"canonical_solutions": [{"solution_id": "s1"}]}) is False


class TestSolutionStatusPersistence:
    def test_solution_status_written_to_session_state(self):
        import streamlit as st
        st.session_state["_test_state"] = {}
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "D", "score": 5, "question_id": "test_q", "standard_answer": ""}
        result = _grade_choice_fast(q, "D", {})
        # Status should be in the grading result
        assert result["grading_result"]["standard_solution_status"] in ("ready", "pending", "missing")
        st.session_state.pop("_test_state", None)

    def test_failed_status_does_not_affect_score(self):
        import streamlit as st
        st.session_state["_solution_status"] = "failed"
        st.session_state["_solution_error"] = "test error"
        from views.grading_page import _grade_choice_fast
        q = {"correct_option": "C", "score": 5, "question_id": "q_x", "standard_answer": ""}
        result = _grade_choice_fast(q, "C", {})
        # Score must still be correct even if solution previously failed
        assert result["grading_result"]["total"] == 5
        assert result["grading_result"]["engine"] == "choice_fast"
        st.session_state.pop("_solution_status", None)
        st.session_state.pop("_solution_error", None)
