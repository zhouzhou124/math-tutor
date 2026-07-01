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

    def test_view_only_choice_uses_detailed_choice_solution_generator(self, monkeypatch):
        from views.grading_page import _build_standard_solution

        calls = {}

        def fake_generate(question, selected_q, client, model=""):
            calls["question"] = question
            calls["selected_q"] = selected_q
            calls["client"] = client
            calls["model"] = model
            return {
                "success": True,
                "question_type": "选择题",
                "standard_answer": (
                    "## 步骤1：核心依据\n先求导并判断零点。\n\n"
                    "## 步骤3：选项分析\nA: 错误\nB: 正确\nC: 错误\nD: 错误\n\n"
                    "## 最终答案\n故选 B。"
                ),
                "choice_solution": {
                    "thought_process": "先求导并判断零点。",
                    "option_analysis": {"A": "错误", "B": "正确", "C": "错误", "D": "错误"},
                    "answer": "B",
                    "correct_answer": "B",
                },
            }

        monkeypatch.setattr(
            "choice_explainer.generate_choice_standard_solution",
            fake_generate,
        )

        class Status:
            def __init__(self):
                self.messages = []

            def write(self, msg):
                self.messages.append(msg)

        selected_q = {
            "question_id": "choice-view-only",
            "question_type": "选择题",
            "question": "设函数 f(x)，求零点个数",
            "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
            "correct_option": "B",
            "score": 4,
        }

        solution = _build_standard_solution(
            "设函数 f(x)，求零点个数",
            {"question_type": "选择题"},
            selected_q,
            object(),
            Status(),
            force_expansion=True,
            _state={},
            model="test-model",
        )

        assert calls["selected_q"]["correct_option"] == "B"
        assert calls["model"] == "test-model"
        assert solution["choice_solution"]["option_analysis"]["B"] == "正确"
        assert "详细解析暂未生成" not in solution["standard_answer"]
