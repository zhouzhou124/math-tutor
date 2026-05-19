"""grading_task_store.py — SQLite persistence layer for async grading tasks.

Survives server restarts and browser-session loss.  Each grading run is a
row with a unique task_id; the UI polls or recovers from this store.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "grading_tasks.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS grading_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT    NOT NULL UNIQUE,
    user_id         TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'processing',
    question        TEXT,
    student_answer  TEXT,
    ocr_data_json   TEXT,
    selected_q_json TEXT,
    grading_result_json         TEXT,
    diagnosis_result_json       TEXT,
    standard_answer_json        TEXT,
    standard_answer_structured_json TEXT,
    error_record_json           TEXT,
    error_msg       TEXT,
    viewed          INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME
);
"""

# Tasks older than this are ignored during recovery
RECOVERY_WINDOW_MINUTES = 60


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table(conn: sqlite3.Connection):
    conn.execute(_CREATE_TABLE)
    conn.commit()


def init_db():
    """One-time initialisation — safe to call on every import."""
    conn = _connect()
    try:
        _ensure_table(conn)
        # Stamp stale processing tasks as failed so the UI never spins forever.
        conn.execute(
            "UPDATE grading_tasks SET status='failed', error_msg='Server restarted before completion' "
            "WHERE status='processing'"
        )
        conn.commit()
    finally:
        conn.close()


def create_task(
    user_id: str,
    question: str,
    student_answer: str,
    ocr_data: dict,
    selected_q: Optional[dict],
) -> str:
    """Insert a new processing row and return its task_id."""
    task_id = uuid.uuid4().hex[:12]
    conn = _connect()
    try:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO grading_tasks
               (task_id, user_id, status, question, student_answer,
                ocr_data_json, selected_q_json)
               VALUES (?, ?, 'processing', ?, ?, ?, ?)""",
            (
                task_id,
                user_id,
                question,
                student_answer,
                json.dumps(ocr_data, ensure_ascii=False),
                json.dumps(selected_q, ensure_ascii=False) if selected_q else None,
            ),
        )
        conn.commit()
        return task_id
    finally:
        conn.close()


def complete_task(task_id: str, results: dict):
    """Write grading results and mark completed."""
    conn = _connect()
    try:
        conn.execute(
            """UPDATE grading_tasks
               SET status = 'completed',
                   grading_result_json = ?,
                   diagnosis_result_json = ?,
                   standard_answer_json = ?,
                   standard_answer_structured_json = ?,
                   error_record_json = ?,
                   completed_at = ?
               WHERE task_id = ?""",
            (
                json.dumps(results.get("grading_result"), ensure_ascii=False),
                json.dumps(results.get("diagnosis_result"), ensure_ascii=False),
                json.dumps(results.get("standard_answer"), ensure_ascii=False),
                json.dumps(results.get("standard_answer_structured"), ensure_ascii=False),
                json.dumps(results.get("error_record"), ensure_ascii=False),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                task_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def fail_task(task_id: str, error_msg: str):
    conn = _connect()
    try:
        conn.execute(
            "UPDATE grading_tasks SET status='failed', error_msg=?, completed_at=? WHERE task_id=?",
            (error_msg, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), task_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: str) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM grading_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_recent_task(user_id: str, minutes: int = RECOVERY_WINDOW_MINUTES) -> Optional[dict]:
    """Return the most recent completed-or-processing task for *user_id*
    within the recovery window.  Processing tasks are only returned if they
    are less than 5 minutes old (the server-side thread may still be running)."""
    conn = _connect()
    try:
        # Use SQLite's datetime functions so timestamps are compared in the
        # same timezone as CURRENT_TIMESTAMP (UTC), avoiding mismatches with
        # Python's locale-aware datetime.now().
        row = conn.execute(
            """SELECT * FROM grading_tasks
               WHERE user_id = ?
                 AND created_at > datetime('now', ?)
                 AND viewed = 0
                 AND (status = 'completed'
                      OR (status = 'processing' AND created_at > datetime('now', '-5 minutes')))
               ORDER BY created_at DESC
               LIMIT 1""",
            (user_id, f'-{minutes} minutes'),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def mark_viewed(task_id: str):
    conn = _connect()
    try:
        conn.execute(
            "UPDATE grading_tasks SET viewed = 1 WHERE task_id = ?", (task_id,)
        )
        conn.commit()
    finally:
        conn.close()


def cleanup_old(hours: int = 24):
    """Delete tasks older than *hours*."""
    conn = _connect()
    try:
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("DELETE FROM grading_tasks WHERE created_at < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


# Boot
init_db()
