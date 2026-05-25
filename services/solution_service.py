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
            agent = SolverAgent(self.client, self.model)
            result = agent.solve(
                question=question or selected_q.get("question", ""),
                math_type=selected_q.get("math_type", "数学一"),
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
                    "_ai_unverified": not entry.get("reviewed", False),
                })
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
            sol = normalize_solution_for_render(sol)
            if _is_good(sol):
                self.status("标准答案已加载（缓存）")
                return sol

        # Try SolverAgent with retry on broken/incomplete output
        solution = self._generate(question, selected_q, ocr_data)
        if solution:
            solution = normalize_solution_for_render(solution)
            if _is_good(solution):
                return solution

            if not solution_is_renderable(solution):
                self.status("检测到公式结构异常，正在重新生成…")
            else:
                self.status("检测到解答步骤不完整，正在重新生成…")

            retry = self._generate(question, selected_q, ocr_data)
            if retry:
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
