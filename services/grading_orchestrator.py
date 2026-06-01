"""Grading orchestrator — executes the full grading pipeline."""

from __future__ import annotations
from typing import Any
import logging

logger = logging.getLogger(__name__)


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


def _question_total_score(selected_q: dict[str, Any], default: float = 5) -> float:
    for key in ("score", "total_score", "points"):
        if selected_q.get(key) is not None:
            try:
                return float(selected_q.get(key))
            except (TypeError, ValueError):
                continue
    return float(default)


def _grade_choice_fast(selected_q: dict[str, Any], student_answer: str) -> dict[str, Any]:
    from services.grading_question_adapter import resolve_correct_answer
    total_score = _question_total_score(selected_q, 5)
    user_ans = _normalize_choice_answer(student_answer)
    resolved = resolve_correct_answer(selected_q, question_type="选择题")
    correct = str(resolved.get("correct_option") or "")
    if not correct:
        return {
            "success": False, "total": None, "score": 0.0, "total_score": total_score,
            "engine": "local_choice_fast", "method": "choice_exact_match",
            "grading_method": "local_choice_match", "_fast_path": True,
            "needs_review": True, "error_type": "standard_answer_missing",
            "is_correct": None, "student_answer": user_ans,
            "correct_answer": "", "correct_option": "",
            "answer_source_field": str(resolved.get("source_field") or ""),
            "answer_source_issues": list(resolved.get("issues") or []),
            "comment": "该题缺少标准选项，无法自动判分。",
            "steps": [],
        }
    ok = bool(user_ans and correct and user_ans == correct)
    score = total_score if ok else 0.0
    return {
        "total": score, "score": score, "total_score": total_score,
        "engine": "local_choice_fast", "method": "choice_exact_match",
        "grading_method": "local_choice_match",
        "_fast_path": True, "is_correct": ok,
        "student_answer": user_ans, "correct_answer": correct,
        "correct_option": correct,
        "answer_source_field": str(resolved.get("source_field") or ""),
        "comment": "答案正确。" if ok else f"答案错误，正确答案是 {correct}。",
        "steps": [{
            "label": "选择题判分",
            "status": "correct" if ok else "incorrect",
            "score": score,
            "max_score": total_score,
            "student_answer": user_ans,
            "correct_answer": correct,
        }],
        "diagnosis": {} if ok else {
            "error_type": "choice_wrong",
            "main_issue": f"选择题答案错误，正确答案是 {correct}。",
            "weak_points": selected_q.get("knowledge_points", []),
        },
    }


def _grade_fill_fast(selected_q: dict[str, Any], student_answer: str) -> dict[str, Any]:
    from services.grading_question_adapter import resolve_correct_answer
    from symbolic_executor import quick_compare

    total_score = _question_total_score(selected_q, 5)
    resolved = resolve_correct_answer(selected_q, question_type="填空题")
    correct = str(resolved.get("answer") or "")
    student = str(student_answer or "").strip()
    if not correct:
        return {
            "success": False, "total": None, "score": 0.0, "total_score": total_score,
            "engine": "fill_compare", "_fast_path": True,
            "needs_review": True, "error_type": "standard_answer_missing",
            "grading_method": "quick_compare",
            "is_correct": None, "student_answer": student,
            "correct_answer": "", "answer_source_field": str(resolved.get("source_field") or ""),
            "answer_source_issues": list(resolved.get("issues") or []),
            "comment": "该题缺少标准答案，无法自动判分。",
        }

    compare = quick_compare(student, correct)
    ok = bool(compare.get("equivalent", False))
    confidence = 0.95 if ok else 0.5
    score = total_score if ok else 0.0
    return {
        "success": True, "total": score, "score": score,
        "step_score": score, "result_score": 0,
        "total_score": total_score, "engine": "fill_compare",
        "_fast_path": True, "is_correct": ok, "ok": ok,
        "student_answer": student, "correct_answer": correct,
        "answer_source_field": str(resolved.get("source_field") or ""),
        "confidence": confidence,
        "quick_compare_confidence": confidence,
        "quick_compare_status": "equivalent" if ok else "not_equivalent",
        "grading_method": "quick_compare",
        "comment": "答案正确。" if ok else "答案需进一步语义判定。",
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

    q_type = str(selected_q.get("question_type") or (ocr_data or {}).get("question_type") or "")
    _q_source = selected_q.get("category") or selected_q.get("source") or ""
    _q_id = selected_q.get("question_id", "")

    # ── View-only: empty answer ──
    if not (student_ans or "").strip():
        logger.info(f"[GRADING_INTENT] qid={_q_id} type={q_type} source={_q_source} mode=view_only")
        gresult = {
            "success": True, "total": None,
            "comment": "未作答，仅查看标准答案",
            "engine": "view_only", "view_only": True,
            "hide_score_card": True, "hide_diagnosis": True,
            "question_type": q_type, "question_source": _q_source,
            "grading_intent": "view_solution_only", "is_view_only": True,
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
            "mode": "view_only",
            "is_view_only": True,
            "mistake_record_created": False,
        }

    # ── Choice fast path ──
    if "选择" in q_type:
        logger.info(f"[GRADING_INTENT] qid={_q_id} type={q_type} source={_q_source} mode=grade path=choice_fast")
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
            "mistake_record_created": False,
        }

    # ── Fill fast path with the same quick_compare escalation contract as UI ──
    if "填空" in q_type:
        logger.info(f"[GRADING_INTENT] qid={_q_id} type={q_type} source={_q_source} mode=grade path=fill_fast")
        gresult = _grade_fill_fast(selected_q, student_ans)
        from config import should_escalate_fill_to_llm
        if not should_escalate_fill_to_llm(gresult):
            gresult = normalize_grading_result(gresult, engine="fill_compare")
            dresult = {
                "error_type": "无错误" if gresult.get("is_correct") else "填空题错误",
                "root_cause": "" if gresult.get("is_correct") else "答案与标准答案不等价",
            }
            return {
                "grading_result": gresult,
                "diagnosis_result": dresult,
                "standard_answer": {"standard_answer": gresult.get("correct_answer", ""),
                                    "total_score": gresult.get("total_score", 10), "steps": []},
                "standard_answer_structured": None,
                "error_record": None,
                "mistake_record_created": False,
            }
        if client is None:
            gresult["grading_method"] = "quick_compare_escalated_llm"
            gresult["needs_review"] = True
            gresult = normalize_grading_result(gresult, engine="fill_compare")
            return {
                "grading_result": gresult,
                "diagnosis_result": {
                    "error_type": "填空题需复核",
                    "root_cause": "quick_compare 置信度不足或判为不等价，需要 LLM 复核",
                },
                "standard_answer": {"standard_answer": gresult.get("correct_answer", ""),
                                    "total_score": gresult.get("total_score", 10), "steps": []},
                "standard_answer_structured": None,
                "error_record": None,
                "mistake_record_created": False,
            }

    # ── Full LLM grading ──
    logger.info(f"[GRADING_INTENT] qid={_q_id} type={q_type} source={_q_source} mode=grade path=llm")
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
    if not std_ans and "填空" in q_type:
        from services.grading_question_adapter import resolve_correct_answer
        std_ans = str(resolve_correct_answer(selected_q, question_type="填空题").get("answer") or "")
    total_score = (solution or {}).get("total_score", 10) if solution else 10

    emit("正在批改...")
    gresult = grading.grade(
        question=question, standard_answer=std_ans, student_answer=student_ans,
        total_score=total_score,
        knowledge_points=ocr_data.get("knowledge_point", "") if ocr_data else "",
        difficulty=selected_q.get("difficulty", "中等"),
        question_type=q_type,
    )
    gresult = normalize_grading_result(gresult)

    # P39: Add unified logging fields
    from config import get_scoring_weights
    _weights = get_scoring_weights(q_type)
    gresult["question_type"] = q_type
    gresult["question_source"] = _q_source
    gresult["grading_path"] = "llm"
    gresult["grading_intent"] = "grade"
    gresult["is_view_only"] = False
    gresult["scoring_weights_used"] = _weights
    logger.info(f"[SCORING_WEIGHTS] qid={_q_id} type={q_type} "
                f"weights={_weights['correctness']}/{_weights['process']}/{_weights['format']}")

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
    from services.math_type_router import math_type_for_ai, source_math_type
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
        "math_type": source_math_type(ocr_data or selected_q),
        "ai_math_type": math_type_for_ai(ocr_data or selected_q),
        "question_type": (ocr_data or {}).get("question_type", "") or selected_q.get("question_type", "") or "未知题型",
        "knowledge_point": (ocr_data or {}).get("knowledge_point", ""),
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
