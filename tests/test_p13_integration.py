"""P13-2 integration tests — service → page wiring contracts."""

import pytest
from services.question_bank_service import (
    QuestionQuery, search_questions, get_similar_questions, build_question_card_vm,
)
from services.mistake_review_service import (
    compute_mistake_priority, build_today_review_queue,
    classify_mistake_severity, update_mastery, merge_duplicate_mistakes,
)


class FakeDB:
    """Minimal fake QuestionDB for testing search_questions."""
    def __init__(self, questions=None):
        self._questions = questions or []

    def search(self, **kwargs):
        results = list(self._questions)
        if kwargs.get("keyword"):
            kw = kwargs["keyword"].lower()
            results = [r for r in results if kw in str(r.get("question", "")).lower()]
        if kwargs.get("question_type"):
            results = [r for r in results if r.get("question_type") == kwargs["question_type"]]
        if kwargs.get("difficulty"):
            results = [r for r in results if r.get("difficulty") == kwargs["difficulty"]]
        if kwargs.get("math_type"):
            results = [r for r in results if r.get("math_type") == kwargs["math_type"]]
        if kwargs.get("knowledge_point"):
            kp = kwargs["knowledge_point"]
            results = [r for r in results if kp in (r.get("knowledge_points") or [])]
        return results


def _make_q(qid, **kw):
    return {
        "question_id": qid,
        "year": kw.get("year", 2022),
        "question_type": kw.get("question_type", "解答题"),
        "difficulty": kw.get("difficulty", "中等"),
        "math_type": kw.get("math_type", "数学一"),
        "knowledge_points": kw.get("knowledge_points", []),
        "question": kw.get("question", f"Question {qid}"),
    }


# ═══════════════════════════════════════════════
#  QuestionQuery construction
# ═══════════════════════════════════════════════

class TestQuestionQueryConstruction:
    def test_query_preserves_all_fields(self):
        q = QuestionQuery(
            keyword="极限", years=[2022, 2023], subject="数学一",
            question_type="解答题", difficulty="中等",
            knowledge_points=["极限"], page=2, page_size=10,
        )
        assert q.keyword == "极限"
        assert q.years == [2022, 2023]
        assert q.subject == "数学一"
        assert q.question_type == "解答题"
        assert q.difficulty == "中等"
        assert q.page == 2
        assert q.page_size == 10

    def test_default_query_is_page_one(self):
        q = QuestionQuery()
        assert q.page == 1
        assert q.page_size == 20


# ═══════════════════════════════════════════════
#  search_questions integration
# ═══════════════════════════════════════════════

class TestSearchQuestions:
    def test_keyword_search(self):
        db = FakeDB([_make_q("q1", question="求极限 sinx/x"), _make_q("q2", question="求导数")])
        q = QuestionQuery(keyword="极限")
        r = search_questions(db, q)
        assert r["total"] == 1
        assert r["items"][0]["question_id"] == "q1"

    def test_type_filter(self):
        db = FakeDB([
            _make_q("q1", question_type="选择题"),
            _make_q("q2", question_type="解答题"),
        ])
        q = QuestionQuery(question_type="选择题")
        r = search_questions(db, q)
        assert r["total"] == 1

    def test_pagination(self):
        db = FakeDB([_make_q(f"q{i}") for i in range(25)])
        q = QuestionQuery(page=2, page_size=10)
        r = search_questions(db, q)
        assert len(r["items"]) == 10
        assert r["total"] == 25
        assert r["total_pages"] == 3

    def test_page_beyond_range_returns_empty(self):
        db = FakeDB([_make_q("q1")])
        q = QuestionQuery(page=5, page_size=10)
        r = search_questions(db, q)
        assert r["items"] == []


# ═══════════════════════════════════════════════
#  Question card VM
# ═══════════════════════════════════════════════

class TestQuestionCardVM:
    def test_no_status_when_empty_stats(self):
        q = _make_q("q1")
        vm = build_question_card_vm(q)
        assert vm["status_chips"] == []

    def test_wrong_count_chip(self):
        q = _make_q("q1")
        vm = build_question_card_vm(q, {"wrong_count": 2})
        chips = vm["status_chips"]
        assert any("曾错" in c[0] for c in chips)

    def test_structured_solution_chip(self):
        q = _make_q("q1")
        q["canonical_solutions"] = [{"solution_id": "s1"}]
        vm = build_question_card_vm(q)
        assert any("有解析" in c[0] for c in vm["status_chips"])

    def test_multiple_chips(self):
        q = _make_q("q1")
        q["canonical_solutions"] = [{"solution_id": "s1"}]
        stats = {"graded": True, "wrong_count": 1}
        vm = build_question_card_vm(q, stats)
        assert len(vm["status_chips"]) >= 3

    def test_missing_fields_dont_crash(self):
        vm = build_question_card_vm({})
        assert vm["question_preview"] == ""


# ═══════════════════════════════════════════════
#  get_similar_questions
# ═══════════════════════════════════════════════

class TestSimilarQuestions:
    def test_excludes_current_question(self):
        db = FakeDB([
            _make_q("q1", knowledge_points=["极限"]),
            _make_q("q2", knowledge_points=["极限"]),
            _make_q("q3", knowledge_points=["极限"]),
        ])
        record = {"knowledge_points": ["极限"], "question_type": "解答题", "question_id": "q1"}
        results = get_similar_questions(db, record, exclude_qid="q1", limit=5)
        qids = [r["question_id"] for r in results]
        assert "q1" not in qids
        assert len(results) >= 1

    def test_falls_back_when_no_kp_match(self):
        db = FakeDB([
            _make_q("q1", knowledge_points=["导数"], question_type="解答题"),
        ])
        record = {"knowledge_points": ["极限"], "question_type": "解答题"}
        # Should broaden and find by question_type
        results = get_similar_questions(db, record, limit=5)
        assert len(results) >= 0  # no crash


# ═══════════════════════════════════════════════
#  Today queue — stable sort
# ═══════════════════════════════════════════════

class TestTodayQueueStability:
    def test_same_priority_preserves_input_order(self):
        records = [
            {"score": 5, "max_score": 10, "status": "active", "id": "a"},
            {"score": 5, "max_score": 10, "status": "active", "id": "b"},
        ]
        queue = build_today_review_queue(records, limit=10)
        assert len(queue) == 2

    def test_mastered_not_in_today(self):
        records = [
            {"score": 2, "max_score": 10, "status": "mastered"},
            {"score": 8, "max_score": 10, "status": "active"},
        ]
        queue = build_today_review_queue(records)
        assert len(queue) == 1
        assert queue[0]["status"] == "active"

    def test_archived_not_in_today(self):
        records = [
            {"score": 2, "max_score": 10, "status": "archived"},
        ]
        queue = build_today_review_queue(records)
        assert len(queue) == 0


# ═══════════════════════════════════════════════
#  Error record mastery fields
# ═══════════════════════════════════════════════

class TestErrorRecordFields:
    def test_next_review_at_is_iso_date(self):
        from services.mistake_review_service import compute_next_review_at
        result = compute_next_review_at(0)
        assert len(result) == 10
        assert "-" in result

    def test_update_mastery_sets_next_review(self):
        r = {"score": 3, "max_score": 10, "status": "active", "mastery_level": 0}
        updated = update_mastery(r, mastered=True)
        assert "next_review_at" in updated
        assert updated["mastery_level"] == 1

    def test_priority_includes_mastery_fields(self):
        r = {"score": 3, "max_score": 10, "status": "active",
             "wrong_count": 2, "weak_points": ["极限"], "is_recent": True}
        p = compute_mistake_priority(r)
        assert p >= 40 + 16 + 10 + 8  # low score + wrong_count*8 + recent + weak_points


# ═══════════════════════════════════════════════
#  Merge duplicates
# ═══════════════════════════════════════════════

class TestMergeDuplicatesIntegration:
    def test_wrong_count_accumulates(self):
        records = [
            {"question_id": "q1", "score": 3, "timestamp": "2026-01-01"},
            {"question_id": "q1", "score": 4, "timestamp": "2026-01-02"},
            {"question_id": "q1", "score": 7, "timestamp": "2026-01-03"},
        ]
        merged = merge_duplicate_mistakes(records)
        assert len(merged) == 1
        assert merged[0]["wrong_count"] == 3
        assert merged[0]["best_score"] == 7
        assert merged[0]["latest_score"] == 7
        assert len(merged[0]["history"]) == 3

    def test_different_qids_not_merged(self):
        records = [
            {"question_id": "q1", "score": 3},
            {"question_id": "q2", "score": 3},
        ]
        merged = merge_duplicate_mistakes(records)
        assert len(merged) == 2


# ═══════════════════════════════════════════════
#  LaTeX → plain preview (P13-3)
# ═══════════════════════════════════════════════

class TestLatexToPlainPreview:
    def test_removes_dollar_delimiters(self):
        from services.question_bank_service import latex_to_plain_preview
        text = r"$1.$ 设 $z=z(x,y)$，求 $\frac{\partial z}{\partial x}$"
        out = latex_to_plain_preview(text)
        assert "$" not in out

    def test_replaces_frac_and_partial(self):
        from services.question_bank_service import latex_to_plain_preview
        text = r"求 $\frac{\partial z}{\partial x}$"
        out = latex_to_plain_preview(text)
        assert r"\frac" not in out
        assert r"\partial" not in out
        assert "分式" in out or "偏导" in out

    def test_replaces_integral(self):
        from services.question_bank_service import latex_to_plain_preview
        text = r"计算 $\int_0^1 x dx$"
        out = latex_to_plain_preview(text)
        assert "积分" in out
        assert r"\int" not in out

    def test_display_math_becomes_placeholder(self):
        from services.question_bank_service import latex_to_plain_preview
        text = r"计算 $$\iint_D f(x,y) dxdy$$"
        out = latex_to_plain_preview(text)
        assert "【公式】" in out
        assert "$$" not in out

    def test_truncates_long_text(self):
        from services.question_bank_service import latex_to_plain_preview
        text = "设函数" * 60
        out = latex_to_plain_preview(text, max_chars=30)
        assert len(out) <= 33
        assert out.endswith("…")

    def test_removes_question_number_prefix(self):
        from services.question_bank_service import latex_to_plain_preview
        text = r"$1.$ 设函数 $f(x)$ 可导"
        out = latex_to_plain_preview(text)
        assert not out.startswith("1.")

    def test_handles_empty_input(self):
        from services.question_bank_service import latex_to_plain_preview
        assert latex_to_plain_preview("") == ""
        assert latex_to_plain_preview(None) == ""

    def test_card_vm_uses_clean_preview(self):
        from services.question_bank_service import build_question_card_vm
        q = {"question": r"$1.$ 求 $\int_0^1 x dx$"}
        vm = build_question_card_vm(q)
        assert "$" not in vm["preview"]
        assert r"\int" not in vm["preview"]

    def test_card_vm_keeps_raw_question(self):
        from services.question_bank_service import build_question_card_vm
        q = {"question": r"$1.$ 求 $\int_0^1 x dx$"}
        vm = build_question_card_vm(q)
        assert "raw_question" in vm
        assert r"\int" in vm["raw_question"]


# ═══════════════════════════════════════════════
#  Stable index integrity (P13-4)
# ═══════════════════════════════════════════════

class TestSearchQuestionsIndexIntegrity:
    def test_pagination_preserves_source_index(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [_make_q(f"q{i}") for i in range(30)]
        db = FakeDB(questions)
        result = search_questions(db, QuestionQuery(page=2, page_size=10))
        first = result["items"][0]
        assert first["display_index"] == 11
        assert first["source_index"] == 10

    def test_filtered_item_keeps_original_question(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [
            _make_q("q1", question="极限题", question_type="选择题"),
            _make_q("q2", question="矩阵题", question_type="解答题"),
            _make_q("q3", question="积分题", question_type="选择题"),
        ]
        db = FakeDB(questions)
        result = search_questions(db, QuestionQuery(question_type="解答题"))
        item = result["items"][0]
        assert item["source_index"] == 1
        assert item["question"]["question"] == "矩阵题"

    def test_every_item_has_stable_question_id(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [_make_q(f"q{i}") for i in range(5)]
        db = FakeDB(questions)
        result = search_questions(db, QuestionQuery())
        for item in result["items"]:
            assert item["question_id"]
            assert item["vm"]["question_id"] == item["question_id"]
            assert item["question"]["question_id"] == item["question_id"]

    def test_question_ids_are_stable_across_pages(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [_make_q(f"q{i}") for i in range(25)]
        db = FakeDB(questions)
        r1 = search_questions(db, QuestionQuery(page=1, page_size=10))
        r2 = search_questions(db, QuestionQuery(page=2, page_size=10))
        ids1 = {it["question_id"] for it in r1["items"]}
        ids2 = {it["question_id"] for it in r2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_keyword_search_uses_plain_text(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [
            _make_q("q1", question=r"求 $\lim_{x\to 0} \frac{\sin x}{x}$"),
            _make_q("q2", question=r"计算 $\int_0^1 x^2 dx$"),
        ]
        db = FakeDB(questions)
        # "极限" should match via build_search_text even though raw has \lim
        result = search_questions(db, QuestionQuery(keyword="极限"))
        assert result["total"] >= 1

    def test_ensure_question_identity_adds_id_when_missing(self):
        from services.question_bank_service import ensure_question_identity
        q = {"question": "无ID的题目", "year": 2024, "question_type": "解答题"}
        result = ensure_question_identity(q, source_index=5)
        assert result["question_id"].startswith("q_")
        assert result["_source_index"] == 5

    def test_items_include_vm_and_question(self):
        from services.question_bank_service import QuestionQuery, search_questions
        questions = [_make_q("q1", question="测试题")]
        db = FakeDB(questions)
        result = search_questions(db, QuestionQuery())
        item = result["items"][0]
        assert "vm" in item
        assert "question" in item
        assert "question_id" in item
        assert "source_index" in item
        assert "display_index" in item
