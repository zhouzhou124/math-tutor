from services.grading_task_runner import get_task_phase, update_task_phase


def test_task_phase_event_is_recorded_and_sanitized():
    event = update_task_phase("task-phase-1", "grading", "正在批改", 62)

    assert event == {
        "phase": "grading",
        "detail": "正在批改",
        "progress": 62,
    }
    assert get_task_phase("task-phase-1") == event


def test_invalid_task_phase_falls_back_to_prepare():
    event = update_task_phase("task-phase-2", "elapsed_guess", "bad", 999)

    assert event["phase"] == "prepare"
    assert event["progress"] == 5
