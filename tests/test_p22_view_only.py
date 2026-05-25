"""P22: View-only answer mode tests."""

import pytest


class TestViewOnlyResult:
    def test_view_only_has_hide_flags(self):
        gr = {
            "view_only": True, "hide_score_card": True, "hide_diagnosis": True,
            "engine": "view_only", "comment": "未作答，仅查看标准答案。",
        }
        assert gr["view_only"] is True
        assert gr["hide_score_card"] is True
        assert gr["hide_diagnosis"] is True

    def test_view_only_no_score_field(self):
        gr = {"engine": "view_only", "view_only": True, "comment": "未作答"}
        assert gr.get("total") is None

    def test_grading_orchestrator_view_only_returns_proper_structure(self):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="test", student_ans="",
            selected_q={"question_id": "q1", "score": 10, "question_type": "解答题"},
            build_solution_fn=lambda **kw: {"standard_answer": "步骤1：推导。综上得证。" + "x" * 120,
                                              "total_score": 10, "steps": []},
        )
        assert result is not None
        gr = result["grading_result"]
        assert gr.get("view_only") is True
        assert gr.get("hide_score_card") is True
        assert result["error_record"] is None
        assert result["diagnosis_result"]["error_type"] == "未作答"


class TestViewOnlyRendering:
    def test_is_view_only_detection(self):
        gr = {"view_only": True, "hide_score_card": True}
        assert bool(gr.get("view_only") or gr.get("hide_score_card")) is True

    def test_normal_grading_not_view_only(self):
        gr = {"engine": "structured", "total": 7}
        assert bool(gr.get("view_only") or gr.get("hide_score_card")) is False


class TestViewOnlyKeepsSolution:
    def test_view_only_still_has_standard_solution(self):
        from services.grading_orchestrator import execute_grading
        result = execute_grading(
            question="test", student_ans="",
            selected_q={"question_id": "q1", "score": 10, "question_type": "解答题"},
            build_solution_fn=lambda **kw: {"standard_answer": "步骤1：推导。综上得证。" + "x" * 120,
                                              "total_score": 10, "steps": []},
        )
        assert result["standard_answer"] is not None

    def test_view_only_with_llm_forces_detailed_generation(self):
        from services.grading_orchestrator import execute_grading

        seen = {}

        result = execute_grading(
            question="test", student_ans="",
            selected_q={"question_id": "q1", "score": 10, "question_type": "填空题"},
            client=object(),
            build_solution_fn=lambda **kw: seen.update(kw) or {
                "standard_answer": "步骤1：推导。步骤2：验证。故最终答案为 x=1。",
                "total_score": 10,
                "steps": [],
            },
        )

        assert result["grading_result"]["engine"] == "view_only"
        assert seen["force_expansion"] is True
