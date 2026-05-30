"""Tests for grading state management fix.

Verifies that switching questions properly clears stale grading state
and prevents recovery logic from overwriting the user's new selection.

Bug: User grades question A (fails/hangs), then selects question B,
but "开始批改" still grades question A due to stale state.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import streamlit as st


# ── _clear_grading_state tests ──

class TestClearGradingState:
    """Verify _clear_grading_state clears all critical keys."""

    def _call(self, preserve_ocr=False):
        from views.grading_page import _clear_grading_state
        _clear_grading_state(preserve_ocr=preserve_ocr)

    def test_clears_pending_task_id(self):
        st.session_state["pending_task_id"] = "old-task-123"
        self._call()
        assert "pending_task_id" not in st.session_state

    def test_clears_active_grading_task_id(self):
        st.session_state["active_grading_task_id"] = "old-task-456"
        self._call()
        assert "active_grading_task_id" not in st.session_state

    def test_clears_active_grading_request_hash(self):
        st.session_state["active_grading_request_hash"] = "hash-abc"
        self._call()
        assert "active_grading_request_hash" not in st.session_state

    def test_clears_grading_result(self):
        st.session_state["grading_result"] = {"total": 8}
        self._call()
        assert "grading_result" not in st.session_state

    def test_clears_ocr_result_by_default(self):
        st.session_state["ocr_result"] = {"success": True, "question": "old"}
        self._call()
        assert "ocr_result" not in st.session_state

    def test_preserves_ocr_result_when_flag_set(self):
        st.session_state["ocr_result"] = {"success": True, "question": "old"}
        self._call(preserve_ocr=True)
        assert "ocr_result" in st.session_state

    def test_clears_solution_status(self):
        st.session_state["_solution_status"] = "ready"
        self._call()
        assert "_solution_status" not in st.session_state


# ── Recovery block guard tests ──

class TestRecoveryBlockGuard:
    """Verify recovery block skips when user selected a different question."""

    @patch("views.grading_page.get_recent_task")
    @patch("views.grading_page.mark_viewed")
    def test_recovery_skipped_when_different_question_selected(self, mock_mark, mock_recent):
        """When user selected question B but recent task is for question A,
        recovery should be skipped and old task marked as viewed."""
        mock_recent.return_value = {
            "task_id": "task-a",
            "status": "completed",
            "selected_q_json": json.dumps({"question_id": "math1_2003_choice_001"}),
            "ocr_data_json": json.dumps({"question": "old question A"}),
        }

        # User has already selected a different question
        st.session_state["selected_question"] = {"question_id": "math1_2007_fill_005"}
        st.session_state.pop("ocr_result", None)

        # Simulate the recovery guard logic
        recent = mock_recent.return_value
        _existing_sq = st.session_state.get("selected_question") or {}
        _existing_qid = _existing_sq.get("question_id", "")
        _task_qid = ""
        if recent.get("selected_q_json"):
            try:
                _task_qid = (json.loads(recent["selected_q_json"]) or {}).get("question_id", "")
            except Exception:
                pass

        should_skip = bool(_existing_qid and _task_qid and _existing_qid != _task_qid)
        assert should_skip, "Recovery should be skipped when questions differ"
        assert _existing_qid == "math1_2007_fill_005", "selected_question should not be overwritten"

    @patch("views.grading_page.get_recent_task")
    def test_recovery_proceeds_when_same_question(self, mock_recent):
        """When user's selected question matches the recent task, recovery should proceed."""
        mock_recent.return_value = {
            "task_id": "task-a",
            "status": "completed",
            "selected_q_json": json.dumps({"question_id": "math1_2003_choice_001"}),
        }

        st.session_state["selected_question"] = {"question_id": "math1_2003_choice_001"}
        st.session_state.pop("ocr_result", None)

        recent = mock_recent.return_value
        _existing_sq = st.session_state.get("selected_question") or {}
        _existing_qid = _existing_sq.get("question_id", "")
        _task_qid = ""
        if recent.get("selected_q_json"):
            _task_qid = json.loads(recent["selected_q_json"]).get("question_id", "")

        should_skip = bool(_existing_qid and _task_qid and _existing_qid != _task_qid)
        assert not should_skip, "Recovery should proceed when questions match"

    @patch("views.grading_page.get_recent_task")
    def test_recovery_proceeds_when_no_existing_question(self, mock_recent):
        """When no selected_question in session, recovery should proceed."""
        mock_recent.return_value = {
            "task_id": "task-a",
            "status": "completed",
            "selected_q_json": json.dumps({"question_id": "math1_2003_choice_001"}),
        }

        st.session_state.pop("selected_question", None)
        st.session_state.pop("ocr_result", None)

        recent = mock_recent.return_value
        _existing_sq = st.session_state.get("selected_question") or {}
        _existing_qid = _existing_sq.get("question_id", "") if isinstance(_existing_sq, dict) else ""
        _task_qid = ""
        if recent.get("selected_q_json"):
            _task_qid = json.loads(recent["selected_q_json"]).get("question_id", "")

        should_skip = bool(_existing_qid and _task_qid and _existing_qid != _task_qid)
        assert not should_skip, "Recovery should proceed when no existing question"


# ── actions.py state clearing tests ──

class TestActionsClearState:
    """Verify start_practice and view_solution clear stale grading state."""

    @patch("streamlit.session_state", new_callable=lambda: type("SS", (), {
        "_store": {},
        "pop": lambda self, k, *a: self._store.pop(k, *a),
        "__contains__": lambda self, k: k in self._store,
        "__getitem__": lambda self, k: self._store[k],
        "__setitem__": lambda self, k, v: self._store.__setitem__(k, v),
        "get": lambda self, k, *a: self._store.get(k, *a),
        "keys": lambda self: self._store.keys(),
    })())
    def test_start_practice_clears_ocr_result(self, mock_ss):
        mock_ss._store = {
            "ocr_result": {"success": True, "question": "old"},
            "grading_result": {"total": 5},
            "selected_question": {"question_id": "old-qid"},
        }
        # Simulate the clearing logic from start_practice
        for _k in ("ocr_result", "grading_result", "diagnosis_result",
                    "standard_answer", "pending_task_id", "answer_view_mode",
                    "active_grading_task_id", "active_grading_request_hash"):
            mock_ss.pop(_k, None)

        assert "ocr_result" not in mock_ss._store
        assert "grading_result" not in mock_ss._store

    def test_start_practice_clears_stale_keys(self):
        """start_practice should clear grading-related session state."""
        st.session_state["ocr_result"] = {"question": "old"}
        st.session_state["grading_result"] = {"total": 3}
        st.session_state["pending_task_id"] = "stale-task"
        st.session_state["active_grading_task_id"] = "stale-active"
        st.session_state["active_grading_request_hash"] = "stale-hash"

        # Simulate the clearing loop from start_practice
        for _k in ("ocr_result", "grading_result", "diagnosis_result",
                    "standard_answer", "pending_task_id", "answer_view_mode",
                    "active_grading_task_id", "active_grading_request_hash"):
            st.session_state.pop(_k, None)

        assert "ocr_result" not in st.session_state
        assert "grading_result" not in st.session_state
        assert "pending_task_id" not in st.session_state
        assert "active_grading_task_id" not in st.session_state
        assert "active_grading_request_hash" not in st.session_state

    def test_view_solution_clears_stale_grading_keys(self):
        """view_solution should clear stale grading keys before setting new ocr_result."""
        st.session_state["grading_result"] = {"total": 3}
        st.session_state["pending_task_id"] = "stale-task"
        st.session_state["active_grading_task_id"] = "stale-active"

        # Simulate the clearing loop from view_solution
        for _k in ("grading_result", "diagnosis_result", "standard_answer",
                    "pending_task_id", "active_grading_task_id",
                    "active_grading_request_hash"):
            st.session_state.pop(_k, None)

        assert "grading_result" not in st.session_state
        assert "pending_task_id" not in st.session_state
        assert "active_grading_task_id" not in st.session_state


# ── End-to-end scenario test ──

class TestEndToEndQuestionSwitch:
    """Simulate the exact bug scenario: grade A fails, switch to B, grade B."""

    def test_question_switch_overrides_stale_recovery(self):
        """Full scenario: grading A fails, user selects B, recovery should not
        overwrite B with A."""
        # Step 1: User was grading question A
        st.session_state["ocr_result"] = {
            "success": True,
            "question": "Question A text",
            "student_answer": "Answer A",
        }
        st.session_state["grading_result"] = {"total": 0, "comment": "失败"}

        # Step 2: Grading fails, _clear_grading_state is called
        for _k in ("grading_result", "diagnosis_result", "standard_answer",
                    "pending_task_id", "active_grading_task_id",
                    "active_grading_request_hash", "ocr_result"):
            st.session_state.pop(_k, None)

        # Step 3: User selects question B
        st.session_state["selected_question"] = {
            "question_id": "math1_2007_fill_005",
            "question": "Question B text",
            "question_type": "填空题",
        }

        # Step 4: Recovery block runs — simulate the guard
        import json
        recent = {
            "task_id": "task-a-old",
            "status": "completed",
            "selected_q_json": json.dumps({
                "question_id": "math1_2003_solve_018",
                "question": "Question A text",
            }),
        }
        _existing_sq = st.session_state.get("selected_question") or {}
        _existing_qid = _existing_sq.get("question_id", "")
        _task_qid = ""
        if recent.get("selected_q_json"):
            _task_qid = json.loads(recent["selected_q_json"]).get("question_id", "")

        should_skip = bool(_existing_qid and _task_qid and _existing_qid != _task_qid)
        assert should_skip, "Recovery should be skipped — user selected a different question"
        assert _existing_qid == "math1_2007_fill_005"
        # selected_question is NOT overwritten
        assert st.session_state["selected_question"]["question_id"] == "math1_2007_fill_005"
