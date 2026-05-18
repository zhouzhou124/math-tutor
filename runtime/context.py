"""
RuntimeContext — 运行时上下文

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  RuntimeContext 是整个 runtime 模块的统一入口和协调器。

  它将 RuntimeState + Executor + TransactionManager + History
  组合为一个连贯的工作单元，提供高层 API:

    ctx = RuntimeContext()
    ctx.initialize(question, assumptions)
    ctx.execute(Op.DIFFERENTIATE, "x^2", "x")
    ctx.checkpoint("求导完成")
    result = ctx.diagnose()

  设计原则:
    1. 单一入口 — 外部模块只与 RuntimeContext 交互
    2. 状态不可变 — 内部状态变换始终产生新 RuntimeState
    3. 历史可溯 — 所有操作自动记录到 ExecutionHistory
    4. 事务安全 — 支持试探性推导和回滚
    5. 诊断就绪 — 随时可以生成诊断报告

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from runtime.state import (
    RuntimeState,
    MathFact,
    ProofObligation,
    DomainKind,
    DomainRegistry,
    FactOrigin,
    ObligationStatus,
    RuntimeMetadata,
)
from runtime.executor import RuntimeExecutor, ExecutionResult, ExecutionStatus
from runtime.transaction import TransactionManager, Transaction, TransactionStatus
from runtime.history import ExecutionHistory, HistoryEntry, HistoryDiff, EntryKind
from math_ir import MathExpression, MathState, ExprCategory
from operations import Op
from constraints.graph import ConstraintGraph, ConstraintStatus


@dataclass
class DiagnosisReport:
    total_steps: int = 0
    error_count: int = 0
    warning_count: int = 0
    pending_obligations: int = 0
    constraint_conflicts: int = 0
    derived_facts: int = 0
    certain_facts: int = 0
    error_path: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    state_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_steps": self.total_steps,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "pending_obligations": self.pending_obligations,
            "constraint_conflicts": self.constraint_conflicts,
            "derived_facts": self.derived_facts,
            "certain_facts": self.certain_facts,
            "error_path": self.error_path,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "state_summary": self.state_summary,
        }

    @property
    def is_healthy(self) -> bool:
        return self.error_count == 0 and self.constraint_conflicts == 0


class RuntimeContext:
    """
    运行时上下文 — runtime 模块的统一入口。

    将 State + Executor + Transaction + History 组合为
    一个连贯的工作单元。

    使用方式:
        ctx = RuntimeContext()
        ctx.initialize_from_math_state(math_state)
        ctx.add_assumption("f(x) 连续")
        ctx.add_constraint("x > 0")
        result = ctx.execute(Op.DIFFERENTIATE, "x^2 + 1", "x")
        report = ctx.diagnose()
    """

    def __init__(self, auto_propagate: bool = True,
                 auto_conflict_detect: bool = True):
        self._state = RuntimeState.empty()
        self._executor = RuntimeExecutor(
            auto_propagate=auto_propagate,
            auto_conflict_detect=auto_conflict_detect,
        )
        self._tx_manager = TransactionManager(self._executor)
        self._history = ExecutionHistory()
        self._question_id: str = ""
        self._label: str = ""
        self._visited_hashes: dict[str, int] = {}
        self._cycle_detected: bool = False

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def history(self) -> ExecutionHistory:
        return self._history

    @property
    def executor(self) -> RuntimeExecutor:
        return self._executor

    @property
    def transaction_manager(self) -> TransactionManager:
        return self._tx_manager

    @property
    def question_id(self) -> str:
        return self._question_id

    @property
    def fingerprint(self) -> str:
        return self._state.fingerprint

    def initialize(self, question_id: str = "",
                   expressions: list[MathExpression] = None,
                   assumptions: list[str] = None,
                   constraints: list[str] = None,
                   domains: dict[str, DomainKind] = None) -> RuntimeState:
        self._question_id = question_id
        self._state = RuntimeState.empty()

        if expressions:
            for expr in expressions:
                self._state = self._state.with_expression(expr)

        if assumptions:
            for a in assumptions:
                self._state = self._state.with_assumption(a)

        if constraints:
            for c in constraints:
                self._state = self._state.with_constraint(c)

        if domains:
            for var, kind in domains.items():
                self._state = self._state.with_domain(var, kind)

        self._history.record_checkpoint(self._state, label="initialize")
        self._record_visit()
        return self._state

    def initialize_from_math_state(self, math_state: MathState,
                                    question_id: str = "") -> RuntimeState:
        self._question_id = question_id
        self._state = RuntimeState.from_math_state(math_state)
        self._history.record_checkpoint(self._state, label="from_math_state")
        self._record_visit()
        return self._state

    def execute(self, op: Op, expression: str = "",
                target_variable: str = "",
                extra_constraints: tuple[str, ...] = (),
                dry_run: bool = False) -> ExecutionResult:
        input_state = self._state
        result = self._executor.execute(
            input_state, op, expression, target_variable,
            extra_constraints, dry_run,
        )

        if result.is_success:
            self._state = result.new_state
            self._history.record_operation(
                input_state, self._state, op.value,
                detail=result.message,
                duration_ms=result.duration_ms,
            )
            self._check_cycle()
        else:
            self._history.record_error(
                self._state,
                error_message=result.message,
                operation=op.value,
            )

        return result

    def add_assumption(self, assumption: str) -> RuntimeState:
        old = self._state
        self._state = self._state.with_assumption(assumption)
        self._history.record_operation(
            old, self._state, "add_assumption",
            detail=assumption,
        )
        return self._state

    def add_constraint(self, expression: str,
                       source_step: str = "") -> RuntimeState:
        old = self._state
        self._state = self._state.with_constraint(expression, source_step)
        self._history.record_constraint_add(self._state, expression)
        return self._state

    def add_domain(self, variable: str, kind: DomainKind = DomainKind.REAL,
                   source: str = "") -> RuntimeState:
        old = self._state
        self._state = self._state.with_domain(variable, kind, source=source)
        self._history.record_operation(
            old, self._state, "set_domain",
            detail=f"{variable}: {kind.value}",
        )
        return self._state

    def propagate_constraints(self) -> RuntimeState:
        old = self._state
        self._state = self._state.with_constraints_propagated()
        self._history.record_constraint_propagate(old, self._state)
        return self._state

    def discharge_obligation(self, proposition: str,
                             discharged_by: str = "") -> RuntimeState:
        old = self._state
        self._state = self._state.discharge_obligation(proposition, discharged_by)
        self._history.record_obligation(
            self._state, proposition,
            kind=EntryKind.OBLIGATION_DISCHARGE,
            detail=f"discharged by: {discharged_by}",
        )
        return self._state

    def checkpoint(self, label: str = "") -> str:
        fp = self._state.fingerprint
        self._history.record_checkpoint(self._state, label=label or f"cp_{fp[:8]}")
        return fp

    def begin_transaction(self, label: str = "") -> Transaction:
        return self._tx_manager.begin(self._state, label=label)

    def try_execute(self, op: Op, expression: str = "",
                    target_variable: str = "") -> tuple[RuntimeState, bool]:
        new_state, success = self._tx_manager.try_execute(
            self._state, op, expression, target_variable,
        )
        if success:
            self._state = new_state
            self._history.record_operation(
                self._state, new_state, op.value,
                detail=f"try_execute: success",
            )
        else:
            self._history.record_error(
                self._state,
                error_message=f"try_execute failed: {op.value}({expression})",
                operation=op.value,
            )
        return new_state, success

    def branch(self, branches: list[tuple[str, list[tuple[Op, str, str]]]]) -> list[tuple[str, RuntimeState, bool]]:
        results = self._tx_manager.branch(self._state, branches)
        for label, state, success in results:
            if success:
                self._history.record_operation(
                    self._state, state, "branch",
                    detail=f"branch '{label}': success",
                )
            else:
                self._history.record_error(
                    self._state,
                    error_message=f"branch '{label}': failed",
                    operation="branch",
                )
        return results

    def _record_visit(self) -> None:
        sh = self._state.semantic_hash()
        step = self._history.length
        self._visited_hashes[sh] = step

    def _check_cycle(self) -> bool:
        sh = self._state.semantic_hash()
        if sh in self._visited_hashes:
            self._cycle_detected = True
            return True
        self._visited_hashes[sh] = self._history.length
        return False

    @property
    def cycle_detected(self) -> bool:
        return self._cycle_detected

    @property
    def visited_state_count(self) -> int:
        return len(self._visited_hashes)

    def detect_cycles(self) -> list[tuple[str, int, int]]:
        """
        检测所有环路 — 基于 semantic_hash 的历史回溯。

        Returns:
            list of (semantic_hash, first_seen_step, current_step)
        """
        cycles = []
        hash_first_seen: dict[str, int] = {}
        snapshots = self._history._snapshots
        for i, snap in enumerate(snapshots):
            sh = snap.state.semantic_hash()
            if sh in hash_first_seen:
                cycles.append((sh, hash_first_seen[sh], snap.step))
            else:
                hash_first_seen[sh] = snap.step
        return cycles

    def is_state_visited(self, state: RuntimeState) -> bool:
        return state.semantic_hash() in self._visited_hashes

    def find_similar_states(self, state: RuntimeState) -> list[int]:
        sh = state.semantic_hash()
        return [step for hash_val, step in self._visited_hashes.items() if hash_val == sh]

    def rollback_to(self, fingerprint: str) -> bool:
        snapshot = self._history.get_snapshot_by_fingerprint(fingerprint)
        if not snapshot:
            return False
        old = self._state
        self._state = snapshot.state
        self._history.record_rollback(old, self._state, reason=f"rollback to {fingerprint[:8]}")
        return True

    def diagnose(self) -> DiagnosisReport:
        report = DiagnosisReport()

        report.total_steps = self._history.length
        report.error_count = len(self._history.find_errors())
        report.pending_obligations = len(self._state.pending_obligations)
        report.derived_facts = len(self._state.derived_facts)
        report.certain_facts = len(self._state.certain_facts)
        report.state_summary = self._state.summary()

        conflict = self._state.constraints.detect_conflicts()
        report.constraint_conflicts = len(conflict.conflicting_pairs) if conflict.has_conflict else 0

        error_entries = self._history.error_path()
        report.error_path = [
            {"step": e.step, "operation": e.operation, "detail": e.detail}
            for e in error_entries
        ]

        if conflict.has_conflict:
            report.warnings.extend(conflict.explanations)

        for obl in self._state.pending_obligations:
            report.warnings.append(f"待证明: {obl.proposition}")

        if self._cycle_detected:
            report.warnings.append("检测到推理环路: 状态回到了之前访问过的语义等价状态")

        if report.error_count > 0:
            report.suggestions.append("检查错误路径中的步骤，回滚到出错前重新推导")
        if report.constraint_conflicts > 0:
            report.suggestions.append("存在约束冲突，检查假设是否矛盾")
        if report.pending_obligations > 0:
            report.suggestions.append(f"还有 {report.pending_obligations} 个待证明义务")
        if self._cycle_detected:
            report.suggestions.append("推理出现环路，考虑添加新约束或改变推导策略")

        return report

    def to_math_state(self) -> MathState:
        return self._state.to_math_state()

    def to_dict(self) -> dict:
        return {
            "question_id": self._question_id,
            "state": self._state.to_dict(),
            "history": self._history.to_dict(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RuntimeContext:
        ctx = cls()
        ctx._question_id = d.get("question_id", "")
        ctx._state = RuntimeState.from_dict(d["state"]) if "state" in d else RuntimeState.empty()
        ctx._history = ExecutionHistory.from_dict(d["history"]) if "history" in d else ExecutionHistory()
        return ctx

    def reset(self) -> None:
        self._state = RuntimeState.empty()
        self._history.clear()
        self._question_id = ""
        self._visited_hashes.clear()
        self._cycle_detected = False
