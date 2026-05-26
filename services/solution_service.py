"""SolutionService — standard answer generation, caching, and canonical persistence."""

from __future__ import annotations
from typing import Any, Callable


class SolutionService:
    """Orchestrates standard-answer generation. Dependency-injected."""

    def __init__(
        self,
        client=None,
        model: str = "",
        status_callback: Callable[[str], None] | None = None,
        stream_callback: Callable[[str], None] | None = None,
    ):
        self.client = client
        self.model = model
        self.status = status_callback or (lambda msg: None)
        self.stream = stream_callback or (lambda delta: None)

    def _generate(self, question, selected_q, ocr_data):
        """Internal: call SolverAgent and return normalized solution or None."""
        if not self.client:
            return None
        try:
            from agents.solver_agent import SolverAgent
            from services.grading_adapter import normalize_standard_solution
            from services.math_type_router import math_type_for_ai
            agent = SolverAgent(self.client, self.model)
            result = agent.solve(
                question=question or selected_q.get("question", ""),
                math_type=math_type_for_ai(selected_q or ocr_data),
                question_type=selected_q.get("question_type", "解答题"),
                knowledge_point=", ".join(selected_q.get("knowledge_points", [])),
            )
            if result.get("success") and result.get("standard_answer"):
                return normalize_standard_solution({
                    **result,
                    "total_score": selected_q.get("score", 10),
                    "_ai_unverified": True,
                })
        except Exception:
            pass
        return None

    def _generated_ir_ready(self, sol: dict[str, Any] | None) -> bool:
        if not isinstance(sol, dict):
            return False
        if not (sol.get("_solution_ir") or sol.get("_canonical_ir")):
            return False
        report = sol.get("_compiled_quality_report") or {}
        return (
            bool(report.get("ok"))
            and bool(sol.get("compiled_renderable"))
            and bool(sol.get("compiled_complete"))
            and bool(sol.get("_used_compiled_standard_answer"))
            and sol.get("standard_solution_source") == "compiled_ir"
        )

    def _ir_feedback(self, sol: dict[str, Any] | None) -> str:
        if not isinstance(sol, dict):
            return "missing_solution_ir"
        issues: list[str] = []
        report = sol.get("_compiled_quality_report")
        if isinstance(report, dict):
            issues.extend(str(i) for i in (report.get("issues") or []))
        if sol.get("_compiled_fallback_reason"):
            issues.append(str(sol.get("_compiled_fallback_reason")))
        if not (sol.get("_solution_ir") or sol.get("_canonical_ir")):
            issues.append("missing_solution_ir")
        return ", ".join(dict.fromkeys(i for i in issues if i)) or "compiled_ir_not_ready"

    def _mandatory_ir_failure(self, sol: dict[str, Any] | None, issues: str) -> dict[str, Any]:
        import html
        raw_preview = ""
        if isinstance(sol, dict):
            raw_preview = str(sol.get("standard_answer") or sol.get("answer") or "")[:500]
        report = {
            "ok": False,
            "renderable": False,
            "complete": False,
            "detailed": False,
            "covers_requirements": False,
            "logically_plausible": False,
            "issues": [i.strip() for i in str(issues or "missing_solution_ir").split(",") if i.strip()],
            "should_regenerate": True,
        }
        return {
            "success": True,
            "standard_answer": "",
            "total_score": int((sol or {}).get("total_score", 10)) if isinstance(sol, dict) else 10,
            "steps": [],
            "_structured": None,
            "standard_solution_status": "failed",
            "standard_solution_source": "failed",
            "standard_solution_error": "新生成标准解答缺少合格 Solution IR，已阻止展示。",
            "_quality_report": report,
            "_should_regenerate": True,
            "_mandatory_ir_failed": True,
            "_failed_quality_report": report,
            "_failed_raw_preview": html.escape(raw_preview, quote=True),
        }

    def _generate_with_mandatory_ir(self, question, selected_q, ocr_data) -> dict[str, Any] | None:
        first = self._generate(question, selected_q, ocr_data)
        if self._generated_ir_ready(first):
            return first

        feedback = self._ir_feedback(first)
        self.status(f"Solution IR 未通过，正在带问题反馈重试：{feedback}")
        retry_question = (
            f"{question or selected_q.get('question', '')}\n\n"
            f"上一次标准解答生成未产生合格 Solution IR，问题包括：{feedback}。\n"
            "请重新生成严格 CanonicalIR JSON，确保 validate_canonical_ir、compiler 和 quality gate 全部通过。"
        )
        retry = self._generate(retry_question, selected_q, ocr_data)
        if self._generated_ir_ready(retry):
            return retry
        return self._mandatory_ir_failure(retry or first, self._ir_feedback(retry or first))

    def build(
        self,
        question: str = "",
        selected_q: dict[str, Any] | None = None,
        ocr_data: dict[str, Any] | None = None,
        force_expansion: bool = False,
    ) -> dict[str, Any]:
        """Build or load a standard solution. P19-3: retry on broken LaTeX."""
        from services.grading_adapter import (
            normalize_standard_solution, normalize_solution_for_render,
            normalize_canonical_entry, solution_has_substance,
        )
        from services.solution_quality import (
            solution_is_renderable, solution_is_complete, solution_quality_report,
        )

        selected_q = selected_q or {}
        ocr_data = ocr_data or {}
        if not selected_q.get("question_type") and ocr_data.get("question_type"):
            selected_q = {**selected_q, "question_type": ocr_data.get("question_type")}
        cached = (selected_q.get("standard_answer") or "").strip()
        pool = selected_q.get("canonical_solutions") or []

        def _is_good(sol: dict[str, Any] | None) -> bool:
            if not isinstance(sol, dict):
                return False
            report = solution_quality_report(sol, selected_q)
            sol["_quality_report"] = report
            sol["_should_regenerate"] = bool(report.get("should_regenerate"))
            if report.get("ok"):
                sol["standard_solution_status"] = "ready"
                sol["standard_solution_error"] = ""
            return bool(report.get("ok"))

        def _mark_quality_failure(sol: dict[str, Any]) -> dict[str, Any]:
            report = solution_quality_report(sol, selected_q)
            sol["_quality_report"] = report
            sol["_should_regenerate"] = True
            issues = "、".join(report.get("issues", [])[:4]) or "quality_gate_failed"
            if not report.get("renderable", False):
                sol["standard_solution_status"] = "failed"
                sol["standard_solution_error"] = f"标准解答生成失败：公式结构异常（{issues}）。"
            else:
                sol["standard_solution_status"] = "incomplete"
                sol["standard_solution_error"] = f"标准解答生成不完整：{issues}。"
            return sol

        # Canonical pool hit — validate + invalidate old formats
        for entry in pool:
            entry = normalize_canonical_entry(entry, question=selected_q)
            if solution_has_substance(entry):
                sol = normalize_standard_solution({
                    "standard_answer": entry.get("standard_answer", ""),
                    "total_score": selected_q.get("score", 10),
                    "steps": entry.get("steps", []),
                    "_structured": entry.get("structured"),
                    "_canonical_ir": entry.get("canonical_ir"),
                    "_solution_ir": entry.get("solution_ir") or entry.get("canonical_ir"),
                    "_ai_unverified": not entry.get("reviewed", False),
                })
                if self._generated_ir_ready(sol) and _is_good(sol):
                    self.status("标准答案已加载（缓存）")
                    return sol
                sol = normalize_solution_for_render(sol)
                if _is_good(sol):
                    self.status("标准答案已加载（缓存）")
                    return sol

        # Legacy cache hit — validate
        if cached and solution_has_substance(cached) and not force_expansion:
            sol = normalize_standard_solution({
                "standard_answer": cached,
                "total_score": selected_q.get("score", 10),
                "steps": selected_q.get("solution_steps", []),
                "_ai_unverified": False,
            })
            if _is_good(sol):
                self.status("标准答案已加载（缓存）")
                return sol
            sol = normalize_solution_for_render(sol)
            if _is_good(sol):
                self.status("标准答案已加载（缓存）")
                return sol

        # Try SolverAgent with retry on broken/incomplete output
        solution = self._generate_with_mandatory_ir(question, selected_q, ocr_data)
        if solution:
            if solution.get("_mandatory_ir_failed"):
                return solution
            if self._generated_ir_ready(solution) and _is_good(solution):
                return solution
            solution = normalize_solution_for_render(solution)
            if _is_good(solution):
                return solution

            if not solution_is_renderable(solution):
                self.status("检测到公式结构异常，正在重新生成…")
            else:
                self.status("检测到解答步骤不完整，正在重新生成…")

            retry = self._generate_with_mandatory_ir(question, selected_q, ocr_data)
            if retry:
                if retry.get("_mandatory_ir_failed"):
                    return retry
                if self._generated_ir_ready(retry) and _is_good(retry):
                    return retry
                retry = normalize_solution_for_render(retry)
                if _is_good(retry):
                    return retry
                return _mark_quality_failure(retry)

            return _mark_quality_failure(solution)

        # Fallback
        return normalize_standard_solution({
            "standard_answer": cached or "暂无标准答案（请配置 API Key 以自动生成）",
            "total_score": selected_q.get("score", 10),
            "steps": [],
        })
