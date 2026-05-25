"""P25: Solution coverage service tests."""

import pytest
from services.solution_coverage_service import (
    classify_question_solution_state,
    build_solution_backfill_candidates,
)


class TestClassifySolutionState:
    def test_no_answer(self):
        assert classify_question_solution_state({}) == "no_answer"

    def test_answer_only_with_final_answer(self):
        assert classify_question_solution_state({"final_answer": "x=1"}) == "answer_only"

    def test_answer_only_with_raw_answer(self):
        assert classify_question_solution_state({"raw_answer_text": "x=1"}) == "answer_only"

    def test_answer_only_with_correct_option(self):
        assert classify_question_solution_state({"correct_option": "B"}) == "answer_only"

    def test_has_detailed_solution(self):
        assert classify_question_solution_state(
            {"standard_answer": "步骤1：推导。" + "x" * 120}
        ) == "has_detailed_solution"

    def test_has_structured_solution(self):
        assert classify_question_solution_state({
            "canonical_solutions": [{"structured": {"steps": []}}]
        }) == "has_structured_solution"

    def test_pool_entry_with_long_answer_is_detailed(self):
        assert classify_question_solution_state({
            "canonical_solutions": [{"standard_answer": "x" * 120}]
        }) == "has_detailed_solution"


class TestBackfillCandidates:
    def test_filters_out_structured(self):
        # FakeDB that returns questions with structured
        class FakeDB:
            def search(self, **kw):
                return [{
                    "question_id": "q1", "question_type": "解答题",
                    "canonical_solutions": [{"structured": {"steps": []}}],
                }]
        candidates = build_solution_backfill_candidates(FakeDB())
        assert len(candidates) == 0

    def test_includes_answer_only(self):
        class FakeDB:
            def search(self, **kw):
                return [{"question_id": "q2", "question_type": "解答题", "final_answer": "x=1"}]
        candidates = build_solution_backfill_candidates(FakeDB())
        assert len(candidates) >= 1
        assert candidates[0]["current_state"] == "answer_only"

    def test_limit_respected(self):
        class FakeDB:
            def search(self, **kw):
                return [{"question_id": f"q{i}", "question_type": "解答题",
                          "final_answer": "x=1"} for i in range(50)]
        candidates = build_solution_backfill_candidates(FakeDB(), limit=5)
        assert len(candidates) == 5
