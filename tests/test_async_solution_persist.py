"""Tests for async solution persistence fix.

Verifies that the daemon thread's solution generation result is persisted
to SQLite and properly restored on session recovery.

Bug: "暂无标准解法数据" — daemon thread writes to orphaned _state dict,
UI reads from st.session_state, no bridge exists.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st


# ── update_task_solution tests ──

class TestUpdateTaskSolution:
    """Verify update_task_solution persists solution to SQLite."""

    def test_update_task_solution_basic(self, tmp_path):
        """update_task_solution writes solution to standard_answer_json."""
        from storage.grading_task_store import complete_task, update_task_solution
        import storage.grading_task_store as store

        # Use temp DB
        old_path = store.DB_PATH
        store.DB_PATH = tmp_path / "test.db"
        try:
            # Create a task first
            from storage.grading_task_store import create_task, get_task
            tid = create_task("user1", "Q?", "A", {}, {"question_id": "q1"})
            complete_task(tid, {
                "grading_result": {"total": 5, "_hide_until_solution_ready": True,
                                   "standard_solution_status": "pending"},
                "diagnosis_result": {},
                "standard_answer": {"standard_answer": "", "steps": []},
            })

            # Now update with solution
            solution = {
                "success": True,
                "standard_answer": "详细解答...",
                "steps": [{"label": "步骤1", "content": "..."}],
            }
            update_task_solution(tid, solution, {
                "_hide_until_solution_ready": False,
                "standard_solution_status": "ready",
            })

            # Verify
            task = get_task(tid)
            sa = json.loads(task["standard_answer_json"])
            assert sa["standard_answer"] == "详细解答..."
            assert len(sa["steps"]) == 1

            gr = json.loads(task["grading_result_json"])
            assert gr["_hide_until_solution_ready"] is False
            assert gr["standard_solution_status"] == "ready"
        finally:
            store.DB_PATH = old_path

    def test_update_task_solution_patches_grading_result(self, tmp_path):
        """update_task_solution merges grading_result_patch into existing result."""
        from storage.grading_task_store import complete_task, update_task_solution, get_task
        import storage.grading_task_store as store

        old_path = store.DB_PATH
        store.DB_PATH = tmp_path / "test.db"
        try:
            from storage.grading_task_store import create_task
            tid = create_task("user1", "Q?", "A", {}, {"question_id": "q1"})
            complete_task(tid, {
                "grading_result": {"total": 8, "comment": "不错", "_hide_until_solution_ready": True},
                "diagnosis_result": {},
                "standard_answer": {},
            })

            update_task_solution(tid, {"standard_answer": "解答"}, {
                "_hide_until_solution_ready": False,
                "standard_solution_status": "ready",
            })

            task = get_task(tid)
            gr = json.loads(task["grading_result_json"])
            # Original fields preserved
            assert gr["total"] == 8
            assert gr["comment"] == "不错"
            # Patched fields added
            assert gr["_hide_until_solution_ready"] is False
            assert gr["standard_solution_status"] == "ready"
        finally:
            store.DB_PATH = old_path

    def test_update_task_solution_no_grading_result_patch(self, tmp_path):
        """update_task_solution works without grading_result_patch."""
        from storage.grading_task_store import complete_task, update_task_solution, get_task
        import storage.grading_task_store as store

        old_path = store.DB_PATH
        store.DB_PATH = tmp_path / "test.db"
        try:
            from storage.grading_task_store import create_task
            tid = create_task("user1", "Q?", "A", {}, {"question_id": "q1"})
            complete_task(tid, {
                "grading_result": {"total": 5},
                "standard_answer": {},
            })

            update_task_solution(tid, {"standard_answer": "解答"})

            task = get_task(tid)
            sa = json.loads(task["standard_answer_json"])
            assert sa["standard_answer"] == "解答"
            # grading_result unchanged
            gr = json.loads(task["grading_result_json"])
            assert gr == {"total": 5}
        finally:
            store.DB_PATH = old_path


# ── _restore_results_to_session tests ──

class TestRestoreResultsWithSolution:
    """Verify _restore_results_to_session wires up async solution."""

    @patch("views.grading_page.mark_viewed")
    def test_restore_sets_solution_status_ready(self, mock_mv):
        """When grading_result has standard_solution_status=ready,
        _solution_status should be set in session_state."""
        from views.grading_page import _restore_results_to_session

        task = {
            "task_id": "test-task-1",
            "user_id": "user1",
            "grading_result_json": json.dumps({
                "total": 8,
                "standard_solution_status": "ready",
                "_hide_until_solution_ready": False,
            }),
            "diagnosis_result_json": json.dumps({}),
            "standard_answer_json": json.dumps({
                "success": True,
                "standard_answer": "详细解答",
                "steps": [{"label": "步骤1", "content": "..."}],
            }),
        }

        # Clear relevant state
        for k in ("grading_result", "diagnosis_result", "standard_answer",
                   "_solution_status", "_async_solution"):
            st.session_state.pop(k, None)

        _restore_results_to_session(task)

        assert st.session_state.get("_solution_status") == "ready"

    @patch("views.grading_page.mark_viewed")
    def test_restore_sets_async_solution(self, mock_mv):
        """When solution is ready, _async_solution should be populated."""
        from views.grading_page import _restore_results_to_session

        sa_data = {
            "success": True,
            "standard_answer": "详细解答",
            "steps": [{"label": "步骤1", "content": "..."}],
        }
        task = {
            "task_id": "test-task-2",
            "user_id": "user1",
            "grading_result_json": json.dumps({
                "total": 8,
                "standard_solution_status": "ready",
                "_hide_until_solution_ready": False,
            }),
            "standard_answer_json": json.dumps(sa_data),
        }

        for k in ("grading_result", "standard_answer",
                   "_solution_status", "_async_solution"):
            st.session_state.pop(k, None)

        _restore_results_to_session(task)

        async_sol = st.session_state.get("_async_solution")
        assert async_sol is not None
        assert async_sol["standard_answer"] == "详细解答"

    @patch("views.grading_page.mark_viewed")
    def test_restore_no_async_solution_when_pending(self, mock_mv):
        """When solution is still pending, don't set _async_solution."""
        from views.grading_page import _restore_results_to_session

        task = {
            "task_id": "test-task-3",
            "user_id": "user1",
            "grading_result_json": json.dumps({
                "total": 5,
                "standard_solution_status": "pending",
                "_hide_until_solution_ready": True,
            }),
            "standard_answer_json": json.dumps({"standard_answer": "", "steps": []}),
        }

        for k in ("grading_result", "standard_answer",
                   "_solution_status", "_async_solution"):
            st.session_state.pop(k, None)

        _restore_results_to_session(task)

        assert st.session_state.get("_solution_status") != "ready"
        assert st.session_state.get("_async_solution") is None

    @patch("views.grading_page.mark_viewed")
    def test_restore_no_async_solution_when_hide_flag_set(self, mock_mv):
        """When _hide_until_solution_ready is still True, don't set ready."""
        from views.grading_page import _restore_results_to_session

        task = {
            "task_id": "test-task-4",
            "user_id": "user1",
            "grading_result_json": json.dumps({
                "total": 5,
                "standard_solution_status": "ready",
                "_hide_until_solution_ready": True,  # still hiding
            }),
            "standard_answer_json": json.dumps({"standard_answer": "解答"}),
        }

        for k in ("grading_result", "standard_answer",
                   "_solution_status", "_async_solution"):
            st.session_state.pop(k, None)

        _restore_results_to_session(task)

        # Should NOT set ready because hide flag is still set
        assert st.session_state.get("_solution_status") != "ready"


# ── _state has _task_id test ──

class TestStateHasTaskId:
    """Verify _state dict includes _task_id for daemon thread persistence."""

    def test_state_includes_task_id(self):
        """submit_grading_async should include _task_id in _state."""
        # This is a structural test — verify the _state dict creation includes _task_id
        import inspect
        from services.grading_task_runner import submit_grading_async
        source = inspect.getsource(submit_grading_async)
        assert '"_task_id": task_id' in source or "'_task_id': task_id" in source, \
            "_state dict must include _task_id for daemon thread persistence"


# ── Timeout guard test ──

class TestSolutionTimeout:
    """Verify solution generation has a timeout guard."""

    def test_timeout_constant_exists(self):
        """The rendering gate should have a timeout constant."""
        import inspect
        from views.grading_page import render_grading_page
        source = inspect.getsource(render_grading_page)
        assert "SOLUTION_TIMEOUT" in source or "_SOLUTION_TIMEOUT" in source, \
            "Rendering gate must have a solution timeout to prevent infinite spinner"
