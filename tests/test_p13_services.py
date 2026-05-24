"""P13 tests — mistake_review_service + question_bank_service."""

import pytest
from services.mistake_review_service import (
    compute_mistake_priority,
    classify_mistake_severity,
    build_today_review_queue,
    next_review_days,
    compute_next_review_at,
    update_mastery,
    merge_duplicate_mistakes,
)
from services.question_bank_service import QuestionQuery, build_question_card_vm


# ═══════════════════════════════════════════════
#  Mistake priority
# ═══════════════════════════════════════════════

class TestMistakePriority:
    def test_low_score_has_higher_priority(self):
        low = compute_mistake_priority({"score": 2, "max_score": 10, "status": "active"})
        high = compute_mistake_priority({"score": 8, "max_score": 10, "status": "active"})
        assert low > high

    def test_wrong_count_boosts_priority(self):
        once = compute_mistake_priority({"score": 3, "max_score": 10, "wrong_count": 1, "status": "active"})
        thrice = compute_mistake_priority({"score": 3, "max_score": 10, "wrong_count": 3, "status": "active"})
        assert thrice > once

    def test_mastered_lowers_priority(self):
        active = compute_mistake_priority({"score": 5, "max_score": 10, "status": "active"})
        mastered = compute_mistake_priority({"score": 5, "max_score": 10, "status": "mastered"})
        assert mastered < active

    def test_archived_is_very_low(self):
        p = compute_mistake_priority({"score": 0, "max_score": 10, "status": "archived"})
        assert p <= 10

    def test_default_values_dont_crash(self):
        result = compute_mistake_priority({})
        assert isinstance(result, int)
        assert result >= 0


class TestSeverity:
    def test_low_score_is_hot(self):
        assert classify_mistake_severity({"score": 2, "max_score": 10}) == "hot"

    def test_medium_score_is_warm(self):
        assert classify_mistake_severity({"score": 5, "max_score": 10}) == "warm"

    def test_high_score_is_cool(self):
        assert classify_mistake_severity({"score": 8, "max_score": 10}) == "cool"

    def test_perfect_is_done(self):
        assert classify_mistake_severity({"score": 10, "max_score": 10}) == "done"

    def test_missing_score_defaults(self):
        # Empty record: score=0, max_score=10 → ratio=0 → hot
        assert classify_mistake_severity({}) == "hot"


class TestTodayReviewQueue:
    def test_sorts_by_priority(self):
        records = [
            {"score": 8, "max_score": 10, "status": "active"},
            {"score": 2, "max_score": 10, "status": "active"},
            {"score": 5, "max_score": 10, "status": "active"},
        ]
        queue = build_today_review_queue(records)
        # First should be the lowest score
        assert queue[0]["score"] == 2
        assert queue[-1]["score"] == 8

    def test_excludes_mastered(self):
        records = [
            {"score": 2, "max_score": 10, "status": "mastered"},
            {"score": 8, "max_score": 10, "status": "active"},
        ]
        queue = build_today_review_queue(records)
        assert len(queue) == 1
        assert queue[0]["score"] == 8

    def test_excludes_archived(self):
        records = [
            {"score": 2, "max_score": 10, "status": "archived"},
            {"score": 8, "max_score": 10, "status": "active"},
        ]
        queue = build_today_review_queue(records)
        assert len(queue) == 1

    def test_respects_limit(self):
        records = [{"score": i % 10, "max_score": 10, "status": "active"}
                   for i in range(30)]
        queue = build_today_review_queue(records, limit=10)
        assert len(queue) == 10


class TestReviewIntervals:
    def test_level_zero_is_one_day(self):
        assert next_review_days(0) == 1

    def test_level_increases_interval(self):
        assert next_review_days(4) == 30

    def test_level_beyond_max_uses_max(self):
        assert next_review_days(10) == 30

    def test_compute_next_review_at_returns_iso_date(self):
        result = compute_next_review_at(0)
        assert len(result) == 10
        assert result[4] == "-"


class TestUpdateMastery:
    def test_mastering_increments_level(self):
        r = {"mastery_level": 1, "status": "active"}
        updated = update_mastery(r, mastered=True)
        assert updated["mastery_level"] == 2
        assert "next_review_at" in updated

    def test_failing_decrements_level(self):
        r = {"mastery_level": 2, "status": "active"}
        updated = update_mastery(r, mastered=False)
        assert updated["mastery_level"] == 1
        assert updated["status"] == "active"

    def test_level_four_mastered_promotes_status(self):
        r = {"mastery_level": 3, "status": "active"}
        updated = update_mastery(r, mastered=True)
        assert updated["mastery_level"] == 4
        assert updated["status"] == "mastered"

    def test_does_not_go_below_zero(self):
        r = {"mastery_level": 0, "status": "active"}
        updated = update_mastery(r, mastered=False)
        assert updated["mastery_level"] == 0


class TestMergeDuplicates:
    def test_same_qid_merged(self):
        records = [
            {"question_id": "q1", "score": 3, "timestamp": "2026-01-01"},
            {"question_id": "q1", "score": 7, "timestamp": "2026-01-02"},
            {"question_id": "q2", "score": 5, "timestamp": "2026-01-03"},
        ]
        merged = merge_duplicate_mistakes(records)
        assert len(merged) == 2
        q1 = [m for m in merged if m["question_id"] == "q1"][0]
        assert q1["wrong_count"] == 2
        assert q1["best_score"] == 7
        assert q1["latest_score"] == 7
        assert len(q1["history"]) == 2

    def test_single_record_no_merge(self):
        records = [{"question_id": "q1", "score": 5}]
        merged = merge_duplicate_mistakes(records)
        assert len(merged) == 1
        assert merged[0]["wrong_count"] == 1


# ═══════════════════════════════════════════════
#  Question bank service
# ═══════════════════════════════════════════════

class TestQuestionQuery:
    def test_default_query(self):
        q = QuestionQuery()
        assert q.page == 1
        assert q.page_size == 20

    def test_query_with_filters(self):
        q = QuestionQuery(keyword="极限", question_type="解答题", difficulty="中等")
        assert q.keyword == "极限"
        assert q.question_type == "解答题"


class TestQuestionCardVM:
    def test_basic_vm(self):
        q = {"question_id": "test", "question": "求极限", "difficulty": "中等"}
        vm = build_question_card_vm(q)
        assert vm["question_id"] == "test"
        assert vm["status_chips"] == []

    def test_vm_with_status(self):
        q = {"question_id": "test", "question": "求极限"}
        stats = {"graded": True, "wrong_count": 2}
        vm = build_question_card_vm(q, stats)
        assert any("曾错" in c[0] for c in vm["status_chips"])
        assert any("已批改" in c[0] for c in vm["status_chips"])

    def test_vm_structured_solution_chip(self):
        q = {"question_id": "test", "question": "x", "canonical_solutions": [{}]}
        vm = build_question_card_vm(q)
        assert any("有解析" in c[0] for c in vm["status_chips"])

    def test_vm_empty_question_no_crash(self):
        vm = build_question_card_vm({})
        assert vm["question_preview"] == ""
        assert vm["status_chips"] == []
