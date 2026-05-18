"""
ExecutionHistory — 执行历史记录与回放

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学推理的每一步都应可追溯:
    - 诊断: "第3步出错" → 定位到具体操作和状态
    - 回放: 从初始状态重放整个推理过程
    - 对比: 比较学生路径与标准路径的差异
    - 回滚: 回退到任意历史状态

  历史模型:
    HistoryEntry = (timestamp, operation, input_state, output_state, result)
    History = ordered list of HistoryEntry

  查询能力:
    - by_step: 按步骤编号查询
    - by_operation: 按操作类型查询
    - by_fingerprint: 按状态指纹查询
    - error_path: 追溯错误路径
    - diff: 两个历史状态之间的差异

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from runtime.state import RuntimeState
from operations import Op, normalize_op


class EntryKind(Enum):
    OPERATION = auto()
    CONSTRAINT_ADD = auto()
    CONSTRAINT_PROPAGATE = auto()
    FACT_DERIVE = auto()
    OBLIGATION_ADD = auto()
    OBLIGATION_DISCHARGE = auto()
    DOMAIN_SET = auto()
    CHECKPOINT = auto()
    ERROR = auto()
    ROLLBACK = auto()


@dataclass(frozen=True)
class HistoryEntry:
    step: int = 0
    kind: EntryKind = EntryKind.OPERATION
    operation: str = ""
    input_fingerprint: str = ""
    output_fingerprint: str = ""
    detail: str = ""
    timestamp: str = ""
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))

    def to_dict(self) -> dict:
        d = {
            "step": self.step,
            "kind": self.kind.name,
            "operation": self.operation,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "timestamp": self.timestamp,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.duration_ms > 0:
            d["duration_ms"] = self.duration_ms
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: dict) -> HistoryEntry:
        return cls(
            step=d.get("step", 0),
            kind=EntryKind[d.get("kind", "OPERATION")],
            operation=d.get("operation", ""),
            input_fingerprint=d.get("input_fingerprint", ""),
            output_fingerprint=d.get("output_fingerprint", ""),
            detail=d.get("detail", ""),
            timestamp=d.get("timestamp", ""),
            duration_ms=d.get("duration_ms", 0.0),
            metadata=d.get("metadata", {}),
        )


@dataclass(frozen=True)
class StateSnapshot:
    fingerprint: str = ""
    step: int = 0
    state: RuntimeState = field(default_factory=RuntimeState.empty)
    label: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if not self.fingerprint:
            object.__setattr__(self, "fingerprint", self.state.fingerprint)

    def to_dict(self) -> dict:
        d = {
            "fingerprint": self.fingerprint,
            "step": self.step,
            "label": self.label,
            "timestamp": self.timestamp,
        }
        if not self.state.is_empty:
            d["state"] = self.state.to_dict()
        return d


@dataclass
class HistoryDiff:
    from_step: int = 0
    to_step: int = 0
    from_fingerprint: str = ""
    to_fingerprint: str = ""
    operations: list[str] = field(default_factory=list)
    facts_added: list[str] = field(default_factory=list)
    constraints_added: list[str] = field(default_factory=list)
    obligations_added: list[str] = field(default_factory=list)
    obligations_discharged: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "from_step": self.from_step,
            "to_step": self.to_step,
            "from_fingerprint": self.from_fingerprint,
            "to_fingerprint": self.to_fingerprint,
            "operations": self.operations,
            "facts_added": self.facts_added,
            "constraints_added": self.constraints_added,
            "obligations_added": self.obligations_added,
            "obligations_discharged": self.obligations_discharged,
        }


class ExecutionHistory:
    """
    执行历史 — 记录状态变换的完整轨迹。

    使用方式:
        history = ExecutionHistory()
        history.record_operation(state_before, state_after, Op.DIFFERENTIATE, "求导成功")
        entry = history.get_step(1)
        snapshot = history.get_snapshot(1)
    """

    def __init__(self):
        self._entries: list[HistoryEntry] = []
        self._snapshots: list[StateSnapshot] = []
        self._step_counter = 0

    @property
    def length(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    @property
    def latest(self) -> Optional[HistoryEntry]:
        return self._entries[-1] if self._entries else None

    @property
    def latest_snapshot(self) -> Optional[StateSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def record_operation(self, input_state: RuntimeState,
                         output_state: RuntimeState,
                         operation: str,
                         detail: str = "",
                         duration_ms: float = 0.0,
                         metadata: dict = None) -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.OPERATION,
            operation=operation,
            input_fingerprint=input_state.fingerprint,
            output_fingerprint=output_state.fingerprint,
            detail=detail,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        self._snapshots.append(StateSnapshot(
            fingerprint=output_state.fingerprint,
            step=self._step_counter,
            state=output_state,
            label=operation,
        ))
        return self._step_counter

    def record_constraint_add(self, state: RuntimeState,
                              constraint: str,
                              detail: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.CONSTRAINT_ADD,
            operation="add_constraint",
            output_fingerprint=state.fingerprint,
            detail=constraint,
        )
        self._entries.append(entry)
        return self._step_counter

    def record_constraint_propagate(self, input_state: RuntimeState,
                                    output_state: RuntimeState,
                                    detail: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.CONSTRAINT_PROPAGATE,
            operation="propagate_constraints",
            input_fingerprint=input_state.fingerprint,
            output_fingerprint=output_state.fingerprint,
            detail=detail,
        )
        self._entries.append(entry)
        self._snapshots.append(StateSnapshot(
            fingerprint=output_state.fingerprint,
            step=self._step_counter,
            state=output_state,
            label="propagate",
        ))
        return self._step_counter

    def record_fact_derive(self, state: RuntimeState,
                           fact_expression: str,
                           detail: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.FACT_DERIVE,
            operation="derive_fact",
            output_fingerprint=state.fingerprint,
            detail=fact_expression,
        )
        self._entries.append(entry)
        return self._step_counter

    def record_obligation(self, state: RuntimeState,
                          proposition: str,
                          kind: EntryKind = EntryKind.OBLIGATION_ADD,
                          detail: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=kind,
            operation="obligation",
            output_fingerprint=state.fingerprint,
            detail=proposition,
        )
        self._entries.append(entry)
        return self._step_counter

    def record_checkpoint(self, state: RuntimeState,
                          label: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.CHECKPOINT,
            operation="checkpoint",
            output_fingerprint=state.fingerprint,
            detail=label,
        )
        self._entries.append(entry)
        self._snapshots.append(StateSnapshot(
            fingerprint=state.fingerprint,
            step=self._step_counter,
            state=state,
            label=label or "checkpoint",
        ))
        return self._step_counter

    def record_error(self, state: RuntimeState,
                     error_message: str,
                     operation: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.ERROR,
            operation=operation,
            output_fingerprint=state.fingerprint,
            detail=error_message,
        )
        self._entries.append(entry)
        return self._step_counter

    def record_rollback(self, from_state: RuntimeState,
                        to_state: RuntimeState,
                         reason: str = "") -> int:
        self._step_counter += 1
        entry = HistoryEntry(
            step=self._step_counter,
            kind=EntryKind.ROLLBACK,
            operation="rollback",
            input_fingerprint=from_state.fingerprint,
            output_fingerprint=to_state.fingerprint,
            detail=reason,
        )
        self._entries.append(entry)
        self._snapshots.append(StateSnapshot(
            fingerprint=to_state.fingerprint,
            step=self._step_counter,
            state=to_state,
            label=f"rollback: {reason}",
        ))
        return self._step_counter

    def get_step(self, step: int) -> Optional[HistoryEntry]:
        for e in self._entries:
            if e.step == step:
                return e
        return None

    def get_snapshot(self, step: int) -> Optional[StateSnapshot]:
        for s in self._snapshots:
            if s.step == step:
                return s
        return None

    def get_snapshot_by_fingerprint(self, fingerprint: str) -> Optional[StateSnapshot]:
        for s in self._snapshots:
            if s.fingerprint == fingerprint:
                return s
        return None

    def find_by_operation(self, operation: str) -> list[HistoryEntry]:
        return [e for e in self._entries if e.operation == operation]

    def find_by_kind(self, kind: EntryKind) -> list[HistoryEntry]:
        return [e for e in self._entries if e.kind == kind]

    def find_errors(self) -> list[HistoryEntry]:
        return self.find_by_kind(EntryKind.ERROR)

    def error_path(self) -> list[HistoryEntry]:
        errors = self.find_errors()
        if not errors:
            return []
        first_error = errors[0]
        path = []
        for e in self._entries:
            path.append(e)
            if e.step == first_error.step:
                break
        return path

    def diff(self, from_step: int, to_step: int) -> Optional[HistoryDiff]:
        snap_from = self.get_snapshot(from_step)
        snap_to = self.get_snapshot(to_step)
        if not snap_from or not snap_to:
            return None

        operations = []
        for e in self._entries:
            if from_step < e.step <= to_step:
                operations.append(f"{e.operation}: {e.detail}")

        state_from = snap_from.state
        state_to = snap_to.state

        facts_from = {f.expression for f in state_from.derived_facts}
        facts_to = {f.expression for f in state_to.derived_facts}
        facts_added = list(facts_to - facts_from)

        constraints_from = set(state_from.constraints.active_expressions())
        constraints_to = set(state_to.constraints.active_expressions())
        constraints_added = list(constraints_to - constraints_from)

        obl_from = {o.proposition for o in state_from.obligations}
        obl_to = {o.proposition for o in state_to.obligations}
        obligations_added = list(obl_to - obl_from)

        discharged = []
        for o in state_to.obligations:
            if o.is_discharged and o.proposition in obl_from:
                from_obl = next(
                    (fo for fo in state_from.obligations if fo.proposition == o.proposition),
                    None,
                )
                if from_obl and from_obl.is_pending:
                    discharged.append(o.proposition)
        obligations_discharged = discharged

        return HistoryDiff(
            from_step=from_step,
            to_step=to_step,
            from_fingerprint=snap_from.fingerprint,
            to_fingerprint=snap_to.fingerprint,
            operations=operations,
            facts_added=facts_added,
            constraints_added=constraints_added,
            obligations_added=obligations_added,
            obligations_discharged=obligations_discharged,
        )

    def operation_timeline(self) -> list[dict]:
        return [
            {
                "step": e.step,
                "operation": e.operation,
                "kind": e.kind.name,
                "detail": e.detail,
                "timestamp": e.timestamp,
            }
            for e in self._entries
        ]

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self._entries],
            "snapshots": [s.to_dict() for s in self._snapshots],
            "step_counter": self._step_counter,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExecutionHistory:
        history = cls()
        history._entries = [HistoryEntry.from_dict(e) for e in d.get("entries", [])]
        history._step_counter = d.get("step_counter", 0)
        return history

    def clear(self) -> None:
        self._entries.clear()
        self._snapshots.clear()
        self._step_counter = 0
