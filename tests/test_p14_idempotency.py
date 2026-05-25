"""P14: grading task idempotency + active task lifecycle tests."""

import pytest
from services.grading_task_runner import (
    build_grading_request_hash,
    clear_active_grading_task,
    RUNNING_STATUSES,
)


class TestRequestHash:
    def test_same_question_answer_produces_same_hash(self):
        q = {"question_id": "q1"}
        h1 = build_grading_request_hash(q, "answer A")
        h2 = build_grading_request_hash(q, "answer A")
        assert h1 == h2

    def test_different_answer_produces_different_hash(self):
        q = {"question_id": "q1"}
        h1 = build_grading_request_hash(q, "answer A")
        h2 = build_grading_request_hash(q, "answer B")
        assert h1 != h2

    def test_different_question_produces_different_hash(self):
        h1 = build_grading_request_hash({"question_id": "q1"}, "x")
        h2 = build_grading_request_hash({"question_id": "q2"}, "x")
        assert h1 != h2

    def test_hash_is_stable_hex_string(self):
        h = build_grading_request_hash({"question_id": "test"}, "ans")
        assert len(h) == 32
        assert all(c in "0123456789abcdef" for c in h)


class TestActiveTaskCleanup:
    def test_clear_removes_all_tracking_keys(self):
        state = {
            "active_grading_task_id": "task_1",
            "active_grading_request_hash": "abc123",
            "grading_in_progress": True,
        }
        clear_active_grading_task(state)
        assert "active_grading_task_id" not in state
        assert "active_grading_request_hash" not in state
        assert state.get("grading_in_progress") is False

    def test_clear_on_empty_state_does_not_crash(self):
        state = {}
        clear_active_grading_task(state)
        assert state.get("grading_in_progress") is False


class TestRunningStatuses:
    def test_processing_is_running(self):
        assert "processing" in RUNNING_STATUSES

    def test_pending_is_running(self):
        assert "pending" in RUNNING_STATUSES

    def test_completed_is_not_running(self):
        assert "completed" not in RUNNING_STATUSES

    def test_failed_is_not_running(self):
        assert "failed" not in RUNNING_STATUSES


class TestMobileTaskGuards:
    def test_submit_reattaches_existing_running_task_for_same_user(self, monkeypatch):
        import json
        from services.grading_task_runner import submit_grading_async

        existing = {
            "task_id": "running_1",
            "status": "processing",
            "selected_q_json": json.dumps({"question_id": "old_q"}),
            "student_answer": "old answer",
        }

        monkeypatch.setattr(
            "storage.grading_task_store.get_recent_task",
            lambda user_id, minutes=2: existing,
        )
        monkeypatch.setattr(
            "storage.grading_task_store.get_task",
            lambda task_id: None,
        )

        def fail_create(*args, **kwargs):
            raise AssertionError("should not create another task")

        monkeypatch.setattr("storage.grading_task_store.create_task", fail_create)

        state = {"auth": {"user_id": "u1"}}
        task_id = submit_grading_async(
            "new q",
            "new answer",
            {},
            {"question_id": "new_q"},
            session_state=state,
            executor=lambda **kw: {},
            get_client_fn=lambda: object(),
        )

        assert task_id == "running_1"

    def test_set_grading_active_writes_session_state(self):
        import streamlit as st
        from views.mobile import set_grading_active

        set_grading_active(True)
        assert st.session_state["grading_in_progress"] is True
        set_grading_active(False)
        assert st.session_state["grading_in_progress"] is False
