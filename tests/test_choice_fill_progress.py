import json


def test_remember_pending_solution_task_sets_progress_state():
    import time
    from views.grading_page import _remember_pending_solution_task

    state = {"_solution_progress_start": 1.0}
    task = {
        "task_id": "task_choice",
        "grading_result_json": json.dumps({
            "_hide_until_solution_ready": True,
            "standard_solution_status": "pending",
        }),
    }

    before = time.time()
    assert _remember_pending_solution_task(task, session_state=state) is True
    assert state["_pending_solution_task_id"] == "task_choice"
    assert state["_solution_progress_start"] >= before


def test_remember_visible_pending_solution_task_sets_progress_state():
    import time
    from views.grading_page import _remember_pending_solution_task

    state = {}
    task = {
        "task_id": "task_visible_choice",
        "grading_result_json": json.dumps({
            "_hide_until_solution_ready": False,
            "standard_solution_status": "pending",
        }),
    }

    before = time.time()
    assert _remember_pending_solution_task(task, session_state=state) is True
    assert state["_pending_solution_task_id"] == "task_visible_choice"
    assert state["_solution_progress_start"] >= before


def test_remember_ready_solution_task_does_not_set_pending_state():
    from views.grading_page import _remember_pending_solution_task

    state = {}
    task = {
        "task_id": "task_choice",
        "grading_result_json": json.dumps({
            "_hide_until_solution_ready": False,
            "standard_solution_status": "ready",
        }),
    }

    assert _remember_pending_solution_task(task, session_state=state) is False
    assert "_pending_solution_task_id" not in state


def test_refresh_pending_solution_task_waits_until_ready():
    from views.grading_page import _refresh_pending_solution_task

    state = {"_pending_solution_task_id": "task_fill", "_solution_progress_start": 123.0}
    task = {
        "task_id": "task_fill",
        "grading_result_json": json.dumps({
            "_hide_until_solution_ready": True,
            "standard_solution_status": "pending",
        }),
        "standard_answer_json": json.dumps({"standard_answer": "old"}),
    }

    assert _refresh_pending_solution_task(session_state=state, task_fetcher=lambda tid: task) is False
    assert state["_pending_solution_task_id"] == "task_fill"
    assert state["_solution_progress_start"] == 123.0


def test_refresh_ready_solution_task_restores_solution_and_clears_progress_state():
    from views.grading_page import _refresh_pending_solution_task

    state = {"_pending_solution_task_id": "task_fill", "_solution_progress_start": 123.0}
    solution = {"standard_answer": "详细解析", "_structured": {"steps": [{"label": "步骤1"}]}}
    task = {
        "task_id": "task_fill",
        "grading_result_json": json.dumps({
            "_hide_until_solution_ready": False,
            "standard_solution_status": "ready",
            "total": 5,
        }),
        "standard_answer_json": json.dumps(solution, ensure_ascii=False),
    }

    assert _refresh_pending_solution_task(session_state=state, task_fetcher=lambda tid: task) is True
    assert state["_solution_status"] == "ready"
    assert state["standard_answer"]["standard_answer"] == "详细解析"
    assert state["_async_solution"]["standard_answer"] == "详细解析"
    assert state["standard_answer_structured"]["steps"][0]["label"] == "步骤1"
    assert "_pending_solution_task_id" not in state
    assert "_solution_progress_start" not in state
