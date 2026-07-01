def test_orchestrator_choice_single_answer_skips_diagnosis(monkeypatch):
    import agents
    from services.grading_orchestrator import execute_grading

    class _Grading:
        def grade(self, **kwargs):
            return {
                "success": True,
                "total": 5,
                "comment": "scored",
                "step_analysis": [{"num": 1, "comment": "should be removed"}],
                "deductions": [{"reason": "should be removed"}],
            }

    monkeypatch.setattr(agents, "GradingAgent", lambda *args, **kwargs: _Grading())
    monkeypatch.setattr(
        agents,
        "DiagnosisAgent",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("diagnosis should be skipped")),
    )

    result = execute_grading(
        question="choice",
        student_ans="A",
        selected_q={"question_type": "choice", "correct_option": "A", "score": 5},
        client=object(),
        build_solution_fn=lambda **kw: {"standard_answer": "A", "total_score": 5},
    )

    gr = result["grading_result"]
    assert gr["hide_diagnosis"] is True
    assert gr["skip_diagnosis"] is True
    assert gr["skip_step_analysis"] is True
    assert gr["step_analysis"] == []
    assert gr["deductions"] == []
    assert result["diagnosis_result"] == {}


def test_orchestrator_fill_single_answer_skips_diagnosis(monkeypatch):
    import agents
    from services.grading_orchestrator import execute_grading

    class _Grading:
        def grade(self, **kwargs):
            return {
                "success": True,
                "total": 0,
                "comment": "scored",
                "step_analysis": [{"num": 1, "comment": "should be removed"}],
                "deductions": [{"reason": "should be removed"}],
            }

    monkeypatch.setattr(agents, "GradingAgent", lambda *args, **kwargs: _Grading())
    monkeypatch.setattr(
        agents,
        "DiagnosisAgent",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("diagnosis should be skipped")),
    )

    result = execute_grading(
        question="fill",
        student_ans="1",
        selected_q={"question_type": "fill", "standard_answer": "2", "score": 5},
        client=object(),
        build_solution_fn=lambda **kw: {"standard_answer": "2", "total_score": 5},
    )

    gr = result["grading_result"]
    assert gr["hide_diagnosis"] is True
    assert gr["skip_diagnosis"] is True
    assert gr["skip_step_analysis"] is True
    assert gr["step_analysis"] == []
    assert gr["deductions"] == []
    assert result["diagnosis_result"] == {}
