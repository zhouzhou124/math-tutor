"""P39: Unified AI grading behavior across sources and question types.

Tests that:
- All question sources (真题/26宇哥/合工大超越) use the same grading path
- All question types use the correct scoring weights from config
- Fill confidence escalation is unified
- Model routing is integrated
- _record_error uses real question_type
- View-only flow is consistent
"""

import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════
# 1. Scoring weights from config
# ═══════════════════════════════════════════

class TestScoringWeights:
    def test_解答题_uses_config_weights(self):
        from config import get_scoring_weights
        w = get_scoring_weights("解答题")
        assert w["correctness"] == 50
        assert w["process"] == 30
        assert w["format"] == 20

    def test_证明题_uses_config_weights(self):
        from config import get_scoring_weights
        w = get_scoring_weights("证明题")
        assert w["correctness"] == 40
        assert w["process"] == 40
        assert w["format"] == 20

    def test_unknown_type_uses_default(self):
        from config import get_scoring_weights
        w = get_scoring_weights("未知题型")
        assert w["correctness"] == 50
        assert w["process"] == 30
        assert w["format"] == 20

    def test_选择题_all_correctness(self):
        from config import get_scoring_weights
        w = get_scoring_weights("选择题")
        assert w["correctness"] == 100
        assert w["process"] == 0
        assert w["format"] == 0

    def test_填空题_all_correctness(self):
        from config import get_scoring_weights
        w = get_scoring_weights("填空题")
        assert w["correctness"] == 100
        assert w["process"] == 0
        assert w["format"] == 0

    def test_no_hardcoded_50_50_in_agent(self):
        """grading_agent.py should use config weights, not hardcoded 50/50."""
        import inspect
        from agents.grading_agent import GradingAgent
        source = inspect.getsource(GradingAgent._grade_structured)
        # Should NOT have hardcoded 0.5
        assert "total_score * 0.5" not in source, (
            "grading_agent still uses hardcoded 50/50 split"
        )

    def test_解答题_weights_in_prompt_params(self):
        """step_total + result_total should reflect config weights."""
        from config import get_scoring_weights
        w = get_scoring_weights("解答题")
        total = 10
        step_total = round(total * (w["correctness"] + w["process"]) / 100, 1)
        result_total = round(total * w["format"] / 100, 1)
        assert step_total == 8.0  # 50 + 30 = 80%
        assert result_total == 2.0  # 20%

    def test_证明题_weights_in_prompt_params(self):
        from config import get_scoring_weights
        w = get_scoring_weights("证明题")
        total = 10
        step_total = round(total * (w["correctness"] + w["process"]) / 100, 1)
        result_total = round(total * w["format"] / 100, 1)
        assert step_total == 8.0  # 40 + 40 = 80%
        assert result_total == 2.0  # 20%


# ═══════════════════════════════════════════
# 2. _record_error uses real question_type
# ═══════════════════════════════════════════

class TestRecordErrorQuestionType:
    def test_选择题_recorded(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({"question_type": "选择题"}) == "选择题"

    def test_填空题_recorded(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({"question_type": "填空题"}) == "填空题"

    def test_解答题_recorded(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({"question_type": "解答题"}) == "解答题"

    def test_证明题_recorded(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({"question_type": "证明题"}) == "证明题"

    def test_missing_field_uses_fallback(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({}) == "未知题型"
        assert _get_question_type_for_record(None) == "未知题型"

    def test_reads_from_grading_result_fallback(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record(
            None, {"question_type": "证明题"}
        ) == "证明题"

    def test_reads_type_field(self):
        from services.grading_service import _get_question_type_for_record
        assert _get_question_type_for_record({"type": "填空题"}) == "填空题"

    def test_no_hardcoded_解答题(self):
        """_record_error should not hardcode 解答题."""
        import inspect
        from services.grading_service import GradingService
        source = inspect.getsource(GradingService._record_error)
        assert '"解答题"' not in source, "_record_error still hardcodes 解答题"


# ═══════════════════════════════════════════
# 3. Fill confidence escalation unified
# ═══════════════════════════════════════════

class TestFillEscalation:
    def test_high_confidence_no_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "confidence": 0.95, "ok": True, "status": "equivalent"
        }) is False

    def test_low_confidence_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "confidence": 0.89, "ok": False, "status": "not_equivalent"
        }) is True

    def test_status_unknown_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "confidence": 0.95, "ok": None, "status": "unknown"
        }) is True

    def test_status_ambiguous_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "confidence": 0.95, "ok": None, "status": "ambiguous"
        }) is True

    def test_no_confidence_ok_false_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "ok": False
        }) is True

    def test_equivalent_high_confidence_no_escalate(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm({
            "equivalent": True, "confidence": 0.95
        }) is False

    def test_default_threshold_from_config(self):
        from config import FILL_QUICK_COMPARE_CONFIDENCE_THRESHOLD
        assert FILL_QUICK_COMPARE_CONFIDENCE_THRESHOLD == 0.9

    def test_custom_threshold(self):
        from config import should_escalate_fill_to_llm
        assert should_escalate_fill_to_llm(
            {"confidence": 0.85, "ok": True}, threshold=0.8
        ) is False


# ═══════════════════════════════════════════
# 4. Model routing integrated
# ═══════════════════════════════════════════

class TestModelRouting:
    def test_user_override_skips_route(self):
        from services.model_router import select_grading_model
        model, reason = select_grading_model(
            {"difficulty": "中等"}, "解答题",
            user_selected_model="my-custom-model",
        )
        assert model == "my-custom-model"
        assert reason == "user_override"

    def test_routed_by_question_type(self):
        from services.model_router import select_grading_model
        model, reason = select_grading_model(
            {"difficulty": "中等"}, "解答题",
        )
        assert model in ("deepseek-chat", "deepseek-v4-pro")
        assert reason == "routed_by_question_type"

    def test_difficult_question_uses_strong_model(self):
        from services.model_router import select_grading_model
        model, reason = select_grading_model(
            {"difficulty": "难"}, "解答题",
        )
        assert model == "deepseek-v4-pro"
        assert reason == "routed_by_question_type"

    def test_route_model_error_fallback(self):
        from services.model_router import select_grading_model
        with patch("services.model_router.route_model", side_effect=Exception("boom")):
            model, reason = select_grading_model(
                {"difficulty": "中等"}, "解答题",
            )
        assert model == "deepseek-chat"
        assert reason == "fallback_session_model"

    def test_选择题_not_routed_for_grading(self):
        """选择题走本地匹配，不经过 model routing for grading."""
        from services.model_router import route_model
        route = route_model(task="choice_grading")
        assert route.model == "local"

    def test_填空题_quick_compare_not_routed(self):
        """填空题 quick_compare 走本地，不经过 model routing."""
        from services.model_router import route_model
        route = route_model(task="fill_compare")
        assert route.model == "local"


# ═══════════════════════════════════════════
# 5. View-only flow consistency
# ═══════════════════════════════════════════

class TestViewOnlyConsistency:
    def test_empty_answer_view_only_choice(self):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="选择正确选项", student_ans="",
            selected_q={"question_id": "q1", "question_type": "选择题",
                         "correct_option": "A", "score": 5},
        )
        assert result["grading_result"]["engine"] == "view_only"
        assert result["grading_result"]["view_only"] is True
        assert result["error_record"] is None

    def test_empty_answer_view_only_fill(self):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="填入结果", student_ans="",
            selected_q={"question_id": "q2", "question_type": "填空题", "score": 5},
        )
        assert result["grading_result"]["engine"] == "view_only"
        assert result["error_record"] is None

    def test_empty_answer_view_only_proof(self):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="证明定理", student_ans="",
            selected_q={"question_id": "q3", "question_type": "证明题", "score": 10},
            build_solution_fn=lambda **kw: {"standard_answer": "证明过程" * 40,
                                              "total_score": 10, "steps": []},
        )
        assert result["grading_result"]["engine"] == "view_only"
        assert result["error_record"] is None

    def test_view_only_no_grading_agent_called(self):
        """View-only should NOT call GradingAgent."""
        from services.grading_orchestrator import execute_grading
        with patch("agents.GradingAgent") as MockAgent:
            result = execute_grading(
                question="test", student_ans="",
                selected_q={"question_id": "q1", "question_type": "解答题", "score": 10},
                build_solution_fn=lambda **kw: {"standard_answer": "x", "total_score": 10},
            )
            MockAgent.assert_not_called()

    def test_view_only_no_diagnose_error(self):
        """View-only should NOT call DiagnosisAgent."""
        from services.grading_orchestrator import execute_grading
        with patch("agents.DiagnosisAgent") as MockDiag:
            result = execute_grading(
                question="test", student_ans="",
                selected_q={"question_id": "q1", "question_type": "解答题", "score": 10},
                build_solution_fn=lambda **kw: {"standard_answer": "x", "total_score": 10},
            )
            MockDiag.assert_not_called()

    def test_view_only_generates_solution(self):
        from services.grading_orchestrator import execute_grading
        called = {}
        result = execute_grading(
            question="test", student_ans="",
            selected_q={"question_id": "q1", "question_type": "解答题", "score": 10},
            build_solution_fn=lambda **kw: called.update(kw) or {
                "standard_answer": "步骤1。" * 40, "total_score": 10, "steps": []},
        )
        assert called.get("question") == "test"
        assert result["standard_answer"] is not None

    def test_is_user_answer_empty(self):
        from config import is_user_answer_empty
        assert is_user_answer_empty("") is True
        assert is_user_answer_empty(None) is True
        assert is_user_answer_empty("  ") is True
        assert is_user_answer_empty("答案") is False

    def test_resolve_grading_intent_empty(self):
        from config import resolve_grading_intent, GRADING_INTENT_VIEW
        r = resolve_grading_intent({}, "")
        assert r["intent"] == GRADING_INTENT_VIEW
        assert r["reason"] == "empty_answer"

    def test_resolve_grading_intent_has_answer(self):
        from config import resolve_grading_intent, GRADING_INTENT_GRADE
        r = resolve_grading_intent({}, "x=1")
        assert r["intent"] == GRADING_INTENT_GRADE
        assert r["reason"] == "has_answer"

    def test_resolve_grading_intent_explicit_view(self):
        from config import resolve_grading_intent, GRADING_INTENT_VIEW
        r = resolve_grading_intent({}, "x=1", action="view_solution")
        assert r["intent"] == GRADING_INTENT_VIEW
        assert r["reason"] == "explicit_view_request"


# ═══════════════════════════════════════════
# 6. Source-agnostic: same path for all sources
# ═══════════════════════════════════════════

class TestSourceAgnostic:
    """All three sources must follow the same grading path."""

    @pytest.mark.parametrize("category", ["数学一", "26宇哥八套卷", "26合工大超越"])
    def test_选择题_unified_llm_path_for_all_sources(self, category, monkeypatch):
        from services.grading_orchestrator import execute_grading

        def fake_build(**kwargs):
            return {"standard_answer": "解析", "total_score": 5}

        class _Grading:
            def grade(self, **kwargs):
                return {"success": True, "total": 5, "comment": "ok"}

        class _Diagnosis:
            def diagnose(self, **kwargs):
                return {"error_type": "无错误", "root_cause": ""}

        monkeypatch.setattr("agents.GradingAgent", lambda c, m: _Grading())
        monkeypatch.setattr("agents.DiagnosisAgent", lambda c, m: _Diagnosis())

        result = execute_grading(
            question="test",
            student_ans="B",
            selected_q={
                "question_id": "q1",
                "question_type": "选择题",
                "correct_option": "B",
                "score": 5,
                "category": category,
            },
            client=object(),
            model="deepseek-chat",
            build_solution_fn=fake_build,
        )
        assert result["grading_result"]["total"] == 5
        assert result["grading_result"].get("engine") != "local_choice_fast"

    @pytest.mark.parametrize("category", ["数学一", "26宇哥八套卷", "26合工大超越"])
    def test_view_only_same_for_all_sources(self, category):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="test", student_ans="",
            selected_q={"question_id": "q1", "question_type": "解答题",
                         "score": 10, "category": category},
        )
        assert result["grading_result"]["engine"] == "view_only"

    @pytest.mark.parametrize("category", ["数学一", "26宇哥八套卷", "26合工大超越"])
    def test_scoring_weights_same_for_all_sources(self, category):
        """Scoring weights depend on question_type, not source."""
        from config import get_scoring_weights
        w = get_scoring_weights("解答题")
        assert w == {"correctness": 50, "process": 30, "format": 20}


# ═══════════════════════════════════════════
# 7. Orchestrator error record question_type
# ═══════════════════════════════════════════

class TestOrchestratorErrorRecord:
    def test_error_record_has_question_type_from_selected_q(self):
        from services.grading_orchestrator import _build_error_record
        selected_q = {"question_id": "q1", "question_type": "证明题",
                      "knowledge_points": ["中值定理"], "difficulty": "难"}
        gresult = {"total": 3, "comment": "错", "step_analysis": [],
                   "engine": "B", "confidence": 0.8}
        dresult = {"error_type": "证明错误", "root_cause": "逻辑链断裂",
                   "weak_points": [], "recommendations": []}
        solution = {"total_score": 10, "_structured": None}
        record = _build_error_record(selected_q, "证明题干", "学生作答",
                                      solution, {}, gresult, dresult)
        assert record["question_type"] == "证明题"

    def test_error_record_fallback_to_selected_q_when_no_ocr(self):
        from services.grading_orchestrator import _build_error_record
        selected_q = {"question_id": "q1", "question_type": "填空题"}
        gresult = {"total": 0, "comment": "", "step_analysis": [],
                   "engine": "B", "confidence": 0.5}
        dresult = {"error_type": "", "root_cause": "", "weak_points": [],
                   "recommendations": []}
        solution = {"total_score": 5, "_structured": None}
        record = _build_error_record(selected_q, "题干", "答案",
                                      solution, None, gresult, dresult)
        assert record["question_type"] == "填空题"
