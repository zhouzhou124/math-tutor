"""Background grading task runner — extracted from grading_page.py.

Handles async grading submission, background thread execution,
and result restoration from SQLite.  Depends-injected to avoid
circular imports with grading_page.py.

P14: idempotent submission via active_task_id + request_hash.
"""

import json as _json
import hashlib as _hashlib
import threading
import logging as _logging
import inspect as _inspect
from config import LLM_BASE_URL, LLM_MODEL

_log = _logging.getLogger(__name__)

RUNNING_STATUSES = {"pending", "running", "processing"}
_TASK_PHASES: dict[str, dict] = {}
_TASK_PHASE_LOCK = threading.Lock()

_PHASE_DEFAULT_PROGRESS = {
    "prepare": 5,
    "solution": 20,
    "grading": 55,
    "diagnosis": 78,
    "finalize": 92,
    "completed": 100,
    "failed": 0,
}


def update_task_phase(task_id: str, phase: str, detail: str = "",
                      progress: int | None = None) -> dict:
    """Record the real in-process phase for an async grading task."""
    phase = str(phase or "prepare")
    if phase not in _PHASE_DEFAULT_PROGRESS:
        phase = "prepare"
        progress = None
    try:
        pct = int(progress if progress is not None else _PHASE_DEFAULT_PROGRESS[phase])
    except (TypeError, ValueError):
        pct = _PHASE_DEFAULT_PROGRESS[phase]
    event = {
        "phase": phase,
        "detail": str(detail or ""),
        "progress": max(0, min(100, pct)),
    }
    with _TASK_PHASE_LOCK:
        _TASK_PHASES[str(task_id)] = event
    return dict(event)


def get_task_phase(task_id: str) -> dict | None:
    """Return the latest real phase event for a running async grading task."""
    with _TASK_PHASE_LOCK:
        event = _TASK_PHASES.get(str(task_id))
        return dict(event) if event else None


def clear_task_phase(task_id: str):
    with _TASK_PHASE_LOCK:
        _TASK_PHASES.pop(str(task_id), None)


def build_grading_request_hash(question: dict, student_answer: str) -> str:
    """Stable hash of question + answer, used to deduplicate submissions."""
    payload = {
        "question_id": (
            str(question.get("question_id") or question.get("id") or "")
        ),
        "student_answer": str(student_answer or ""),
    }
    raw = _json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return _hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_task_request_hash(task: dict) -> str:
    """Rebuild the request hash from a persisted task row."""
    try:
        selected_q = _json.loads(task.get("selected_q_json") or "{}")
    except (_json.JSONDecodeError, TypeError):
        selected_q = {}
    return build_grading_request_hash(selected_q, task.get("student_answer") or "")


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

    # ── Progress/stream callback: phase dicts stay in-process for the
    #     polling page; plain strings still go to SQLite stream_answer.
    def _stream_callback(event):
        try:
            if isinstance(event, dict):
                update_task_phase(
                    task_id,
                    event.get("phase", "prepare"),
                    event.get("detail", ""),
                    event.get("progress"),
                )
            else:
                update_task_stream(task_id, str(event or ""))
        except Exception:
            pass  # streaming is best-effort; never crash the grading run

    try:
        update_task_phase(task_id, "prepare", "正在准备批改任务", 5)
        _state = task_data["_state"]
        _model = task_data["model"]
        _user_id = task_data["user_id"]
        _memory = task_data["memory"]
        _client = task_data["client"]

        kwargs = {
            "question": task_data["question"],
            "student_ans": task_data["student_ans"],
            "ocr_data": task_data["ocr_data"],
            "selected_q": task_data["selected_q"],
            "container": None,
            "_state": _state,
            "model": _model,
            "user_id": _user_id,
            "memory": _memory,
            "client": _client,
        }
        if "stream_callback" in _inspect.signature(executor).parameters:
            kwargs["stream_callback"] = _stream_callback
        results = executor(**kwargs)

        if results is None:
            update_task_phase(task_id, "failed", "批改未返回结果", 0)
            fail_task(task_id, "LLM client unavailable or grading returned no results")
            return

        update_task_phase(task_id, "completed", "批改完成", 100)
        complete_task(task_id, results)
    except Exception as exc:
        _log.error("Background grading failed for task %s: %s", task_id, exc)
        _log.error(traceback.format_exc())
        update_task_phase(task_id, "failed", str(exc)[:120], 0)
        fail_task(task_id, str(exc))


def submit_grading_async(question, student_ans, ocr_data, selected_q, *,
                         session_state, executor, get_client_fn):
    """Create SQLite task, start background thread, return task_id.

    P14: Idempotent — if the same question+answer already has an active
    task, returns the existing task_id instead of creating a duplicate.
    """
    from storage.grading_task_store import create_task, get_recent_task, get_task

    auth = session_state.get("auth") or {}
    user_id = auth.get("user_id", "unknown")
    request_hash = build_grading_request_hash(selected_q, student_ans)

    # ── P14: reuse active task if same question+answer ──
    active_task_id = session_state.get("active_grading_task_id")
    active_hash = session_state.get("active_grading_request_hash")
    if active_task_id and active_hash == request_hash:
        task = get_task(active_task_id)
        if task and task.get("status") in RUNNING_STATUSES:
            return active_task_id

    # ── Guard: re-attach to an existing processing task ──
    existing = get_recent_task(user_id, minutes=2)
    if (
        existing
        and existing.get("status") in RUNNING_STATUSES
        and build_task_request_hash(existing) == request_hash
    ):
        return existing["task_id"]
    if existing and existing.get("status") in RUNNING_STATUSES:
        # Mobile sessions can be duplicated by refresh/back navigation. Keep one
        # live grading task per user so repeated taps do not spawn unbounded LLM
        # calls; the UI will re-attach to this task and show its progress.
        return existing["task_id"]

    model = session_state.get("model", LLM_MODEL)
    memory = session_state.get("memory")

    task_id = create_task(user_id, question, student_ans, ocr_data, selected_q)

    # ── Track active task for dedup ──
    session_state["active_grading_task_id"] = task_id
    session_state["active_grading_request_hash"] = request_hash
    session_state["grading_in_progress"] = True

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
        "_task_id": task_id,
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


def clear_active_grading_task(session_state):
    """P14: Clean up active task tracking state."""
    session_state.pop("active_grading_task_id", None)
    session_state.pop("active_grading_request_hash", None)
    session_state["grading_in_progress"] = False


def restore_results_to_session(task: dict, *, session_state, memory=None):
    """Load grading results from a SQLite task row into session_state.

    Args:
        task: SQLite task row dict
        session_state: Streamlit session_state or plain dict
        memory: MemoryService (optional, for deferred error-record save)
    """
    # ── P14: clean up active task tracking ──
    clear_active_grading_task(session_state)

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
