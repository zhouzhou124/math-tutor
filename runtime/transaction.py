"""
Transaction — 事务与回滚

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学推理需要事务支持:
    - 试探性推导: "如果 x > 0，那么..." → 发现矛盾 → 回滚
    - 分类讨论: 情况1/情况2/情况3 各自独立，互不干扰
    - 错误恢复: 发现计算错误，回退到出错前的状态

  事务模型:
    Transaction = Snapshot + Operations + Commit/Rollback

    begin()    → 创建快照
    commit()   → 确认变更，合并到父状态
    rollback() → 丢弃变更，恢复快照

  嵌套事务:
    支持嵌套，内层事务可独立回滚而不影响外层

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from runtime.state import RuntimeState, RuntimeMetadata
from runtime.executor import RuntimeExecutor, ExecutionResult, ExecutionStatus
from operations import Op


class TransactionStatus(Enum):
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()
    FAILED = auto()


@dataclass
class TransactionLog:
    transaction_id: str = ""
    status: TransactionStatus = TransactionStatus.ACTIVE
    operations: list[dict] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    parent_id: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> dict:
        d = {
            "transaction_id": self.transaction_id,
            "status": self.status.name,
            "operations": self.operations,
            "started_at": self.started_at,
        }
        if self.finished_at:
            d["finished_at"] = self.finished_at
        if self.parent_id:
            d["parent_id"] = self.parent_id
        if self.message:
            d["message"] = self.message
        return d


class Transaction:
    """
    单个事务 — 管理一次试探性推导的生命周期。

    使用方式:
        tx = Transaction(state, executor)
        result = tx.execute(Op.DIFFERENTIATE, "x^2", "x")
        if result.is_success:
            tx.commit()
        else:
            tx.rollback()
    """

    _counter = 0

    def __init__(self, state: RuntimeState, executor: RuntimeExecutor,
                 parent_id: str = "", label: str = ""):
        Transaction._counter += 1
        self._id = f"tx_{Transaction._counter}"
        self._snapshot = state
        self._current = state
        self._executor = executor
        self._status = TransactionStatus.ACTIVE
        self._log = TransactionLog(
            transaction_id=self._id,
            parent_id=parent_id,
            message=label,
        )
        self._results: list[ExecutionResult] = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def status(self) -> TransactionStatus:
        return self._status

    @property
    def state(self) -> RuntimeState:
        return self._current

    @property
    def snapshot(self) -> RuntimeState:
        return self._snapshot

    @property
    def is_active(self) -> bool:
        return self._status == TransactionStatus.ACTIVE

    @property
    def results(self) -> list[ExecutionResult]:
        return list(self._results)

    @property
    def has_errors(self) -> bool:
        return any(not r.is_success for r in self._results)

    def execute(self, op: Op, expression: str = "",
                target_variable: str = "",
                extra_constraints: tuple[str, ...] = (),
                dry_run: bool = False) -> ExecutionResult:
        if not self.is_active:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=self._current,
                message=f"事务 {self._id} 已结束 ({self._status.name})",
            )

        result = self._executor.execute(
            self._current, op, expression, target_variable,
            extra_constraints, dry_run,
        )

        self._results.append(result)
        self._log.operations.append({
            "op": op.value,
            "expression": expression,
            "status": result.status.name,
            "message": result.message,
        })

        if result.is_success:
            self._current = result.new_state

        return result

    def commit(self) -> RuntimeState:
        if not self.is_active:
            return self._current

        self._status = TransactionStatus.COMMITTED
        self._log.status = TransactionStatus.COMMITTED
        self._log.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        return self._current

    def rollback(self) -> RuntimeState:
        if not self.is_active:
            return self._snapshot

        self._status = TransactionStatus.ROLLED_BACK
        self._current = self._snapshot
        self._log.status = TransactionStatus.ROLLED_BACK
        self._log.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        return self._current

    def checkpoint(self) -> str:
        fp = self._current.fingerprint
        return fp

    def rollback_to(self, fingerprint: str) -> bool:
        if fingerprint == self._snapshot.fingerprint:
            self._current = self._snapshot
            return True
        for r in reversed(self._results):
            if r.new_state.fingerprint == fingerprint:
                self._current = r.new_state
                return True
        return False

    def log(self) -> TransactionLog:
        return self._log


class TransactionManager:
    """
    事务管理器 — 管理多个事务的生命周期，支持嵌套。

    使用方式:
        tm = TransactionManager(executor)
        tm.begin(state)
        tm.execute(Op.DIFFERENTIATE, "x^2", "x")
        tm.commit()  # 或 tm.rollback()
    """

    def __init__(self, executor: RuntimeExecutor = None):
        self._executor = executor or RuntimeExecutor()
        self._stack: list[Transaction] = []
        self._all_logs: list[TransactionLog] = []

    @property
    def current(self) -> Optional[Transaction]:
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        return len(self._stack)

    @property
    def is_in_transaction(self) -> bool:
        return bool(self._stack)

    def begin(self, state: RuntimeState = None,
              label: str = "") -> Transaction:
        if state is None:
            if self.current:
                state = self.current.state
            else:
                state = RuntimeState.empty()

        parent_id = self.current.id if self.current else ""
        tx = Transaction(state, self._executor, parent_id=parent_id, label=label)
        self._stack.append(tx)
        return tx

    def execute(self, op: Op, expression: str = "",
                target_variable: str = "",
                extra_constraints: tuple[str, ...] = ()) -> ExecutionResult:
        if not self.current:
            raise RuntimeError("没有活跃事务，请先 begin()")
        return self.current.execute(op, expression, target_variable, extra_constraints)

    def commit(self) -> RuntimeState:
        if not self.current:
            raise RuntimeError("没有活跃事务")
        tx = self._stack.pop()
        state = tx.commit()
        self._all_logs.append(tx.log())
        if self.current:
            pass
        return state

    def rollback(self) -> RuntimeState:
        if not self.current:
            raise RuntimeError("没有活跃事务")
        tx = self._stack.pop()
        state = tx.rollback()
        self._all_logs.append(tx.log())
        return state

    def commit_all(self) -> RuntimeState:
        state = RuntimeState.empty()
        while self._stack:
            state = self.commit()
        return state

    def rollback_all(self) -> RuntimeState:
        state = RuntimeState.empty()
        while self._stack:
            tx = self._stack.pop()
            state = tx.rollback()
            self._all_logs.append(tx.log())
        return state

    def all_logs(self) -> list[TransactionLog]:
        return list(self._all_logs)

    def try_execute(self, state: RuntimeState, op: Op,
                    expression: str = "",
                    target_variable: str = "",
                    extra_constraints: tuple[str, ...] = ()) -> tuple[RuntimeState, bool]:
        tx = self.begin(state, label=f"try:{op.value}")
        result = tx.execute(op, expression, target_variable, extra_constraints)
        if result.is_success and not result.has_warnings:
            final = tx.commit()
            self._stack.clear()
            self._all_logs.append(tx.log())
            return final, True
        else:
            final = tx.rollback()
            self._stack.clear()
            self._all_logs.append(tx.log())
            return final, False

    def branch(self, state: RuntimeState,
               branches: list[tuple[str, list[tuple[Op, str, str]]]]) -> list[tuple[str, RuntimeState, bool]]:
        results = []
        for label, operations in branches:
            tx = self.begin(state, label=label)
            success = True
            for op, expr, var in operations:
                exec_result = tx.execute(op, expr, var)
                if not exec_result.is_success:
                    success = False
                    break
            if success:
                final = tx.commit()
            else:
                final = tx.rollback()
            self._stack.clear()
            self._all_logs.append(tx.log())
            results.append((label, final, success))
        return results
