"""Grading orchestrator — executes the full grading pipeline."""

from __future__ import annotations
from typing import Any


class GradingError(Exception):
    pass


class SolutionGenerationError(GradingError):
    pass


class EngineCError(GradingError):
    pass


class DiagnosisError(GradingError):
    pass


class PersistenceError(GradingError):
    pass


def _normalize_choice_answer(ans: str) -> str:
    import re
    m = re.search(r"[A-D]", str(ans or "").upper())
    return m.group(0) if m else ""


def _grade_choice_fast(selected_q: dict[str, Any], student_answer: str) -> dict[str, Any]:
    total_score = float(selected_q.get("score") or selected_q.get("total_score") or 5)
    user_ans = _normalize_choice_answer(student_answer)
    correct = _normalize_choice_answer(
        selected_q.get("answer")
        or selected_q.get("correct_answer")
        or selected_q.get("correct_option")
        or selected_q.get("standard_answer")
        or ""
    )
    ok = bool(user_ans and correct and user_ans == correct)
    score = total_score if ok else 0.0
    return {
        "total": score, "score": score, "total_score": total_score,
        "engine": "local_choice_fast", "method": "choice_exact_match",
        "_fast_path": True, "is_correct": ok,
        "student_answer": user_ans, "correct_answer": correct,
        "comment": "答案正确。" if ok else f"答案错误，正确答案是 {correct}。",
        "diagnosis": {} if ok else {
            "error_type": "choice_wrong",
            "main_issue": f"选择题答案错误，正确答案是 {correct}。",
            "weak_points": selected_q.get("knowledge_points", []),
        },
    }


def execute_grading(
    question: str = "",
    student_ans: str = "",
    ocr_data: dict[str, Any] | None = None,
    selected_q: dict[str, Any] | None = None,
    *,
    client=None,
    model: str = "",
    user_id: str = "",
    memory=None,
    question_db=None,
    status_callback=None,
    state: dict[str, Any] | None = None,
    build_solution_fn=None,
) -> dict[str, Any] | None:
    """Execute the full grading pipeline."""
    from services.grading_adapter import normalize_grading_result
    selected_q = selected_q or {}
    state = state if state is not None else {}

    def emit(msg: str):
        if status_callback:
            status_callback(msg)

    q_type = str(selected_q.get("question_type") or "")

    # ── View-only: empty answer ──
    if not (student_ans or "").strip():
        gresult = {
            "success": True, "total": None,
            "comment": "未作答，仅查看标准答案",
            "engine": "view_only", "view_only": True,
            "hide_score_card": True, "hide_diagnosis": True,
        }
        dresult = {"error_type": "未作答", "root_cause": ""}
        solution = None
        if build_solution_fn:
            try:
                solution = build_solution_fn(question=question, ocr_data=ocr_data,
                                             selected_q=selected_q, client=client,
                                             force_expansion=bool(client), model=model)
            except Exception:
                pass
        return {
            "grading_result": gresult,
            "diagnosis_result": dresult,
            "standard_answer": solution,
            "standard_answer_structured": (solution or {}).get("_structured") if solution else None,
            "error_record": None,
        }

    # ── Choice fast path ──
    if "选择" in q_type:
        gresult = _grade_choice_fast(selected_q, student_ans)
        gresult = normalize_grading_result(gresult, engine="local_choice_fast")
        dresult = {
            "error_type": "无错误" if gresult.get("total", 0) > 0 else "选择题答案错误",
            "root_cause": "",
        }
        return {
            "grading_result": gresult,
            "diagnosis_result": dresult,
            "standard_answer": {"standard_answer": gresult.get("correct_answer", ""),
                                "total_score": gresult.get("total_score", 10), "steps": []},
            "standard_answer_structured": None,
            "error_record": None,
        }

    # ── Full LLM grading ──
    from agents import GradingAgent, DiagnosisAgent
    grading = GradingAgent(client, model)

    emit("正在获取标准答案...")
    solution = None
    if build_solution_fn:
        solution = build_solution_fn(
            question=question, ocr_data=ocr_data, selected_q=selected_q,
            client=client, force_expansion=False, model=model,
        )
    std_ans = (solution or {}).get("standard_answer", "") if solution else ""
    total_score = (solution or {}).get("total_score", 10) if solution else 10

    emit("正在批改...")
    gresult = grading.grade(
        question=question, standard_answer=std_ans, student_answer=student_ans,
        total_score=total_score,
        knowledge_points=ocr_data.get("knowledge_point", "") if ocr_data else "",
        difficulty=selected_q.get("difficulty", "中等"),
    )
    gresult = normalize_grading_result(gresult)

    emit("正在诊断...")
    diagnosis = DiagnosisAgent(client, model)
    dresult = diagnosis.diagnose(
        question=question, student_answer=student_ans,
        standard_answer=std_ans, grading_result=gresult, error_history=[],
    )

    emit("批改完成")
    return {
        "grading_result": gresult,
        "diagnosis_result": dresult,
        "standard_answer": solution,
        "standard_answer_structured": (solution or {}).get("_structured") if solution else None,
        "error_record": None,
    }


def _build_error_record(selected_q, question, student_ans, solution, ocr_data,
                        gresult, dresult) -> dict:
    """P16: Build error record dict for the mistake notebook."""
    from services.grading_adapter import normalize_error_record
    import time as _time
    _time_str = _time.strftime("%Y-%m-%d %H:%M")
    score = gresult.get("total", 0)
    max_score = solution.get("total_score", 10)

    saved_steps = []
    structured = solution.get("_structured")
    if isinstance(structured, dict) and structured.get("steps"):
        saved_steps = structured["steps"]

    return normalize_error_record({
        "question_id": selected_q.get("question_id", ""),
        "math_type": ocr_data.get("math_type", ""),
        "question_type": ocr_data.get("question_type", ""),
        "knowledge_point": ocr_data.get("knowledge_point", ""),
        "knowledge_points": selected_q.get("knowledge_points", []) or dresult.get("knowledge_points", []),
        "difficulty": selected_q.get("difficulty", "中等"),
        "student_answer": student_ans,
        "score": score,
        "max_score": max_score,
        "is_correct": score >= max_score * 0.9,
        "comment": gresult.get("comment", ""),
        "step_analysis": gresult.get("step_analysis", []),
        "method_matched": gresult.get("method_matched", ""),
        "engine": gresult.get("engine", "unknown"),
        "confidence": float(gresult.get("confidence", 0.0)),
        "error_type": dresult.get("error_type", ""),
        "root_cause": dresult.get("root_cause", ""),
        "weak_points": dresult.get("weak_points", []),
        "recommendations": dresult.get("recommendations", []),
        "common_mistakes": dresult.get("common_mistakes", []),
        "is_repeat_diagnosis": dresult.get("is_repeat", False),
        "timestamp": _time_str,
        "preview": (dresult.get("root_cause") or dresult.get("error_type") or "答错")[:60],
        "question_preview": (question or "")[:80],
        "wrong_reason_short": (dresult.get("root_cause") or dresult.get("error_type") or "答错")[:40],
        "semantic_tags": list(set(
            (selected_q.get("knowledge_points") or []) +
            (dresult.get("weak_points") or [])
        ))[:6],
        "standard_answer_structured": solution.get("_structured"),
    })
