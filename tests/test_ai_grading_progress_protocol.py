def _patch_unified_grading_pipeline(monkeypatch, gp):
    def fake_build(*args, **kwargs):
        return {
            "success": True,
            "standard_answer": "## 步骤1：推导\n内容",
            "total_score": 5,
            "steps": [],
        }

    class _Grading:
        def grade(self, **kwargs):
            return {
                "success": True,
                "total": 5,
                "step_score": 5,
                "result_score": 0,
                "comment": "LLM批改",
            }

    class _Diagnosis:
        def _local_diagnose(self, grading_result, history):
            return {"error_type": "无错误", "root_cause": ""}

        def diagnose(self, **kwargs):
            return {"error_type": "", "root_cause": ""}

    monkeypatch.setattr(gp, "_build_standard_solution", fake_build)
    monkeypatch.setattr(gp, "GradingAgent", lambda client, model: _Grading())
    monkeypatch.setattr(gp, "DiagnosisAgent", lambda client, model: _Diagnosis())


def test_choice_uses_unified_pipeline_not_fast_path(monkeypatch):
    import views.grading_page as gp

    monkeypatch.setattr(
        gp,
        "_grade_choice_fast",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fast path")),
    )
    _patch_unified_grading_pipeline(monkeypatch, gp)

    result = gp._execute_grading_process(
        question="选择题题干",
        student_ans="A",
        ocr_data={"question_type": "选择题"},
        selected_q={
            "question_id": "q_choice",
            "question_type": "选择题",
            "correct_option": "A",
            "score": 5,
        },
        _state={"model": "deepseek-chat"},
        client=object(),
    )

    assert result["grading_result"]["comment"] == "LLM批改"
    assert result["grading_result"].get("_fast_path") is not True


def test_fill_uses_unified_pipeline_not_fast_path(monkeypatch):
    import views.grading_page as gp

    monkeypatch.setattr(
        gp,
        "_grade_fill_fast",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fast path")),
    )
    _patch_unified_grading_pipeline(monkeypatch, gp)

    result = gp._execute_grading_process(
        question="填空题干",
        student_ans="1",
        ocr_data={"question_type": "填空题"},
        selected_q={
            "question_id": "q_fill",
            "question_type": "填空题",
            "standard_answer": "1",
            "score": 5,
        },
        _state={"model": "deepseek-chat"},
        client=object(),
    )

    assert result["grading_result"]["comment"] == "LLM批改"
    assert result["grading_result"].get("_fast_path") is not True


def test_choice_single_answer_skips_diagnosis_and_step_analysis(monkeypatch):
    import views.grading_page as gp

    _patch_unified_grading_pipeline(monkeypatch, gp)
    monkeypatch.setattr(
        gp,
        "DiagnosisAgent",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("diagnosis should be skipped")),
    )

    result = gp._execute_grading_process(
        question="choice",
        student_ans="A",
        ocr_data={"question_type": "choice"},
        selected_q={
            "question_id": "q_choice_simple",
            "question_type": "choice",
            "correct_option": "A",
            "score": 5,
        },
        _state={"model": "deepseek-chat"},
        client=object(),
    )

    gr = result["grading_result"]
    assert gr["hide_diagnosis"] is True
    assert gr["skip_diagnosis"] is True
    assert gr["skip_step_analysis"] is True
    assert gr["step_analysis"] == []
    assert result["diagnosis_result"] == {}


def test_fill_single_answer_skips_diagnosis_and_step_analysis(monkeypatch):
    import views.grading_page as gp

    _patch_unified_grading_pipeline(monkeypatch, gp)
    monkeypatch.setattr(
        gp,
        "DiagnosisAgent",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("diagnosis should be skipped")),
    )

    result = gp._execute_grading_process(
        question="fill",
        student_ans="1",
        ocr_data={"question_type": "fill"},
        selected_q={
            "question_id": "q_fill_simple",
            "question_type": "fill",
            "standard_answer": "1",
            "score": 5,
        },
        _state={"model": "deepseek-chat"},
        client=object(),
    )

    gr = result["grading_result"]
    assert gr["hide_diagnosis"] is True
    assert gr["skip_diagnosis"] is True
    assert gr["skip_step_analysis"] is True
    assert gr["step_analysis"] == []
    assert result["diagnosis_result"] == {}


def test_view_only_pending_solution_returns_wait_protocol(monkeypatch):
    import views.grading_page as gp

    def fake_build(*args, **kwargs):
        return {
            "success": True,
            "standard_answer": "",
            "standard_solution_status": "pending",
            "total_score": 5,
            "steps": [],
        }

    monkeypatch.setattr(gp, "_build_standard_solution", fake_build)
    state = {"_solution_task_id": "q_view"}

    result = gp._execute_grading_process(
        question="view",
        student_ans="",
        ocr_data={"question_type": "choice"},
        selected_q={
            "question_id": "q_view",
            "question_type": "choice",
            "correct_option": "B",
            "score": 5,
        },
        _state=state,
        client=object(),
    )

    gr = result["grading_result"]
    assert gr["engine"] == "view_only"
    assert gr["standard_solution_status"] == "pending"
    assert gr["standard_solution_task_id"] == "q_view"
    assert gr["_hide_until_solution_ready"] is False


def test_view_only_failed_empty_solution_gets_displayable_error(monkeypatch):
    import views.grading_page as gp

    def fake_build(*args, **kwargs):
        return {
            "success": True,
            "standard_answer": "",
            "standard_solution_status": "failed",
            "standard_solution_error": "boom",
            "total_score": 5,
            "steps": [],
        }

    monkeypatch.setattr(gp, "_build_standard_solution", fake_build)

    result = gp._execute_grading_process(
        question="view",
        student_ans="",
        ocr_data={"question_type": "choice"},
        selected_q={
            "question_id": "q_view",
            "question_type": "choice",
            "correct_option": "B",
            "score": 5,
        },
        _state={},
        client=object(),
    )

    gr = result["grading_result"]
    assert gr["standard_solution_status"] == "failed"
    assert gr["_hide_until_solution_ready"] is False
    assert result["standard_answer"]["standard_answer"] == ""
    assert result["standard_answer"].get("standard_solution_error") == "boom"
