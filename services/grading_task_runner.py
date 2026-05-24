"""Background grading task runner — extracted from grading_page.py.

Handles async grading submission, background thread execution,
and result restoration from SQLite.  Depends-injected to avoid
circular imports with grading_page.py.
"""

import json as _json
import threading
import logging as _logging
from config import LLM_BASE_URL, LLM_MODEL

_log = _logging.getLogger(__name__)


def build_client_from_state(state: dict):
    """Create an LLM client from the flat config stored in *state*."""
    api_key = state.get("api_key", "")
    if not api_key:
        return None
    from llm_client import create_client
    return create_client(
        api_key=str(api_key),
        base_url=str(state.get("base_url", LLM_BASE_URL)),
        protocol=str(state.get("protocol", "openai")),
    )


def run_grading_bg(task_id: str, task_data: dict, *, executor):
    """Execute grading in a background thread — writes results to SQLite.

    Args:
        task_id: SQLite task row id
        task_data: dict with _state, model, user_id, memory, client, question, etc.
        executor: callable — the grading process function (avoids circular import)
    """
    from storage.grading_task_store import complete_task, fail_task, update_task_stream
    import traceback

    # ── Streaming callback: persists LLM output to SQLite so the
    #     polling page can display it in near-real-time. ──
    def _stream_callback(text: str):
        try:
            update_task_stream(task_id, text)
        except Exception:
            pass  # streaming is best-effort; never crash the grading run

    try:
        _state = task_data["_state"]
        _model = task_data["model"]
        _user_id = task_data["user_id"]
        _memory = task_data["memory"]
        _client = task_data["client"]

        results = executor(
            question=task_data["question"],
            student_ans=task_data["student_ans"],
            ocr_data=task_data["ocr_data"],
            selected_q=task_data["selected_q"],
            container=None,
            _state=_state,
            model=_model,
            user_id=_user_id,
            memory=_memory,
            client=_client,
            stream_callback=_stream_callback,
        )

        if results is None:
            fail_task(task_id, "LLM client unavailable or grading returned no results")
            return

        complete_task(task_id, results)
    except Exception as exc:
        _log.error("Background grading failed for task %s: %s", task_id, exc)
        _log.error(traceback.format_exc())
        fail_task(task_id, str(exc))


def submit_grading_async(question, student_ans, ocr_data, selected_q, *,
                         session_state, executor, get_client_fn):
    """Create SQLite task, start background thread, return task_id.

    Guards against duplicate submission.

    Args:
        question: question text
        student_ans: student's answer
        ocr_data: OCR result dict
        selected_q: question dict from DB
        session_state: Streamlit session_state or plain dict
        executor: callable — the grading process (avoids circular import)
        get_client_fn: callable → LLM client
    """
    from storage.grading_task_store import create_task, get_recent_task

    user_id = session_state.get("auth", {}).get("user_id", "unknown")

    # Guard: re-attach to an existing processing task
    existing = get_recent_task(user_id, minutes=2)
    if existing and existing.get("status") == "processing":
        return existing["task_id"]

    model = session_state.get("model", LLM_MODEL)
    memory = session_state.get("memory")

    # Create the task row
    task_id = create_task(user_id, question, student_ans, ocr_data, selected_q)

    # Build a plain dict with everything the background thread needs
    _state = {
        "model": model,
        "_client": get_client_fn(),
        "api_key": session_state.get("api_key", ""),
        "base_url": session_state.get("base_url", LLM_BASE_URL),
        "protocol": session_state.get("protocol", "openai"),
        "question_db": session_state.get("question_db"),
        "grading_result": None,
        "diagnosis_result": None,
        "standard_answer": None,
        "standard_answer_structured": None,
        "answer_view_mode": False,
        "grading_triggered": False,
        "mistakes_force_reload": False,
    }

    client = _state.get("_client") or get_client_fn()

    task_data = {
        "_state": _state,
        "question": question,
        "student_ans": student_ans,
        "ocr_data": ocr_data,
        "selected_q": selected_q,
        "model": model,
        "user_id": user_id,
        "memory": memory,
        "client": client,
    }

    thread = threading.Thread(
        target=run_grading_bg,
        args=(task_id, task_data),
        kwargs={"executor": executor},
        daemon=True,
    )
    thread.start()

    return task_id


def restore_results_to_session(task: dict, *, session_state, memory=None):
    """Load grading results from a SQLite task row into session_state.

    Args:
        task: SQLite task row dict
        session_state: Streamlit session_state or plain dict
        memory: MemoryService (optional, for deferred error-record save)
    """
    for key, json_key in [
        ("grading_result", "grading_result_json"),
        ("diagnosis_result", "diagnosis_result_json"),
        ("standard_answer", "standard_answer_json"),
        ("standard_answer_structured", "standard_answer_structured_json"),
        ("ocr_result", "ocr_data_json"),
    ]:
        val = task.get(json_key)
        if val:
            try:
                session_state[key] = _json.loads(val)
            except (_json.JSONDecodeError, TypeError):
                pass

    session_state["answer_view_mode"] = True

    # Restore selected_question from task
    sq_json = task.get("selected_q_json")
    if sq_json:
        try:
            session_state["selected_question"] = _json.loads(sq_json)
        except (_json.JSONDecodeError, TypeError):
            pass

    # Save error record to 错题本 (deferred from background thread)
    error_json = task.get("error_record_json")
    if error_json and memory:
        try:
            error_record = _json.loads(error_json)
            if error_record:
                qid = error_record.get("question_id", "")
                _seen = session_state.get("_saved_error_qids", set())
                _dedup_key = f"{task['user_id']}:{qid}"
                if _dedup_key not in _seen:
                    _seen.add(_dedup_key)
                    session_state["_saved_error_qids"] = _seen
                    memory.add_error_record(task["user_id"], error_record)
                    session_state["mistakes_force_reload"] = True
        except (_json.JSONDecodeError, TypeError):
            pass
