"""State Diff System — 状态差异计算引擎

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学推理本质: 世界状态的演化

    S_t  ──Op──>  S_{t+1}

  StateDiff 回答: "这一步到底改变了什么？"

  没有 diff:
    "步骤 3 验证通过"  ← 只知道对错

  有了 diff:
    "步骤 3 新增约束 x>0，约分义务已证明，目标进度 60%→80%"
    ← 知道状态如何变化

  这是: 调试器 vs 日志 的区别

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  WorldState (before)
  WorldState (after)
      ↓
  StateDiffEngine.diff(before, after)
      ↓
  StateDiff
      ↓
  StateTransitionViewer / DocumentNode[] / Streamlit UI

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Sequence


# ═══════════════════════════════════════════════════════════
# Change Category — 变化类别
# ═══════════════════════════════════════════════════════════

class ChangeCategory(Enum):
    CONSTRAINT = "constraint"
    FACT = "fact"
    GOAL = "goal"
    OBLIGATION = "obligation"
    ASSUMPTION = "assumption"
    EXPRESSION = "expression"
    DOMAIN = "domain"
    SCOPE = "scope"
    PROOF_CONTEXT = "proof_context"
    METADATA = "metadata"


class ChangeDirection(Enum):
    ADDED = auto()
    REMOVED = auto()
    MODIFIED = auto()
    STATUS_CHANGED = auto()


@dataclass(frozen=True)
class ChangeRecord:
    """
    单项变化记录.

    记录: 什么类别、什么方向、具体内容、来源.
    """
    category: ChangeCategory
    direction: ChangeDirection
    key: str = ""
    old_value: str = ""
    new_value: str = ""
    detail: str = ""

    @property
    def icon(self) -> str:
        if self.direction == ChangeDirection.ADDED:
            return "➕"
        if self.direction == ChangeDirection.REMOVED:
            return "➖"
        if self.direction == ChangeDirection.STATUS_CHANGED:
            return "🔄"
        return "✏️"

    @property
    def label(self) -> str:
        direction_labels = {
            ChangeDirection.ADDED: "新增",
            ChangeDirection.REMOVED: "移除",
            ChangeDirection.MODIFIED: "修改",
            ChangeDirection.STATUS_CHANGED: "状态变更",
        }
        category_labels = {
            ChangeCategory.CONSTRAINT: "约束",
            ChangeCategory.FACT: "事实",
            ChangeCategory.GOAL: "目标",
            ChangeCategory.OBLIGATION: "义务",
            ChangeCategory.ASSUMPTION: "假设",
            ChangeCategory.EXPRESSION: "表达式",
            ChangeCategory.DOMAIN: "定义域",
            ChangeCategory.SCOPE: "作用域",
            ChangeCategory.PROOF_CONTEXT: "证明上下文",
            ChangeCategory.METADATA: "元数据",
        }
        d = direction_labels.get(self.direction, "")
        c = category_labels.get(self.category, "")
        return f"{d}{c}"


# ═══════════════════════════════════════════════════════════
# StateDiff — 状态差异结构
# ═══════════════════════════════════════════════════════════

@dataclass
class StateDiff:
    """
    状态差异 — 两步之间的完整变化.

    这是状态转移查看器的核心数据结构.
    回答: "从 S_t 到 S_{t+1}，到底改变了什么？"

    设计:
      - 按 7 大维度分类变化
      - 每个维度区分 added / removed / changed
      - 附带 legality_change 和 confidence_delta
      - 附带 changes 列表供细粒度遍历
    """

    added_constraints: list[str] = field(default_factory=list)
    removed_constraints: list[str] = field(default_factory=list)

    added_facts: list[str] = field(default_factory=list)
    invalidated_facts: list[str] = field(default_factory=list)

    added_goals: list[str] = field(default_factory=list)
    solved_goals: list[str] = field(default_factory=list)

    added_obligations: list[str] = field(default_factory=list)
    discharged_obligations: list[str] = field(default_factory=list)

    added_assumptions: list[str] = field(default_factory=list)
    retracted_assumptions: list[str] = field(default_factory=list)

    added_expressions: list[str] = field(default_factory=list)

    added_domains: list[str] = field(default_factory=list)

    legality_change: Optional[str] = None
    confidence_delta: float = 0.0

    changes: list[ChangeRecord] = field(default_factory=list)

    source_operation: str = ""
    before_fingerprint: str = ""
    after_fingerprint: str = ""

    @property
    def is_empty(self) -> bool:
        return (
            not self.added_constraints
            and not self.removed_constraints
            and not self.added_facts
            and not self.invalidated_facts
            and not self.added_goals
            and not self.solved_goals
            and not self.added_obligations
            and not self.discharged_obligations
            and not self.added_assumptions
            and not self.retracted_assumptions
            and not self.added_expressions
            and not self.added_domains
            and self.legality_change is None
            and abs(self.confidence_delta) < 1e-9
        )

    @property
    def total_changes(self) -> int:
        return (
            len(self.added_constraints) + len(self.removed_constraints)
            + len(self.added_facts) + len(self.invalidated_facts)
            + len(self.added_goals) + len(self.solved_goals)
            + len(self.added_obligations) + len(self.discharged_obligations)
            + len(self.added_assumptions) + len(self.retracted_assumptions)
            + len(self.added_expressions)
            + len(self.added_domains)
        )

    @property
    def summary(self) -> str:
        parts: list[str] = []
        if self.added_constraints:
            parts.append(f"+{len(self.added_constraints)}约束")
        if self.removed_constraints:
            parts.append(f"-{len(self.removed_constraints)}约束")
        if self.added_facts:
            parts.append(f"+{len(self.added_facts)}事实")
        if self.invalidated_facts:
            parts.append(f"~{len(self.invalidated_facts)}事实失效")
        if self.added_goals:
            parts.append(f"+{len(self.added_goals)}目标")
        if self.solved_goals:
            parts.append(f"✓{len(self.solved_goals)}目标达成")
        if self.added_obligations:
            parts.append(f"+{len(self.added_obligations)}义务")
        if self.discharged_obligations:
            parts.append(f"✓{len(self.discharged_obligations)}义务已证")
        if self.added_assumptions:
            parts.append(f"+{len(self.added_assumptions)}假设")
        if self.retracted_assumptions:
            parts.append(f"-{len(self.retracted_assumptions)}假设")
        if self.added_expressions:
            parts.append(f"+{len(self.added_expressions)}表达式")
        if self.added_domains:
            parts.append(f"+{len(self.added_domains)}定义域")
        if self.legality_change:
            parts.append(f"合法性→{self.legality_change}")
        if abs(self.confidence_delta) > 1e-9:
            sign = "+" if self.confidence_delta > 0 else ""
            parts.append(f"置信度{sign}{self.confidence_delta:.2f}")
        if not parts:
            return "无变化"
        return "，".join(parts)

    @property
    def has_regressions(self) -> bool:
        return bool(
            self.invalidated_facts
            or self.removed_constraints
            or self.retracted_assumptions
            or (self.legality_change is not None and "非法" in self.legality_change)
        )

    @property
    def has_progress(self) -> bool:
        return bool(
            self.discharged_obligations
            or self.solved_goals
            or self.added_facts
            or (self.confidence_delta > 0.01)
        )

    @property
    def overall_sentiment(self) -> str:
        if self.has_regressions and not self.has_progress:
            return "regression"
        if self.has_progress and not self.has_regressions:
            return "progress"
        if self.has_progress and self.has_regressions:
            return "mixed"
        if self.is_empty:
            return "neutral"
        return "neutral"

    def to_dict(self) -> dict:
        d: dict = {}
        if self.added_constraints:
            d["added_constraints"] = self.added_constraints
        if self.removed_constraints:
            d["removed_constraints"] = self.removed_constraints
        if self.added_facts:
            d["added_facts"] = self.added_facts
        if self.invalidated_facts:
            d["invalidated_facts"] = self.invalidated_facts
        if self.added_goals:
            d["added_goals"] = self.added_goals
        if self.solved_goals:
            d["solved_goals"] = self.solved_goals
        if self.added_obligations:
            d["added_obligations"] = self.added_obligations
        if self.discharged_obligations:
            d["discharged_obligations"] = self.discharged_obligations
        if self.added_assumptions:
            d["added_assumptions"] = self.added_assumptions
        if self.retracted_assumptions:
            d["retracted_assumptions"] = self.retracted_assumptions
        if self.added_expressions:
            d["added_expressions"] = self.added_expressions
        if self.added_domains:
            d["added_domains"] = self.added_domains
        if self.legality_change is not None:
            d["legality_change"] = self.legality_change
        if abs(self.confidence_delta) > 1e-9:
            d["confidence_delta"] = self.confidence_delta
        d["summary"] = self.summary
        d["total_changes"] = self.total_changes
        d["sentiment"] = self.overall_sentiment
        if self.source_operation:
            d["source_operation"] = self.source_operation
        return d

    @classmethod
    def from_dict(cls, d: dict) -> StateDiff:
        return cls(
            added_constraints=d.get("added_constraints", []),
            removed_constraints=d.get("removed_constraints", []),
            added_facts=d.get("added_facts", []),
            invalidated_facts=d.get("invalidated_facts", []),
            added_goals=d.get("added_goals", []),
            solved_goals=d.get("solved_goals", []),
            added_obligations=d.get("added_obligations", []),
            discharged_obligations=d.get("discharged_obligations", []),
            added_assumptions=d.get("added_assumptions", []),
            retracted_assumptions=d.get("retracted_assumptions", []),
            added_expressions=d.get("added_expressions", []),
            added_domains=d.get("added_domains", []),
            legality_change=d.get("legality_change"),
            confidence_delta=d.get("confidence_delta", 0.0),
            source_operation=d.get("source_operation", ""),
        )


# ═══════════════════════════════════════════════════════════
# StateDiffEngine — 差异计算引擎
# ═══════════════════════════════════════════════════════════

class StateDiffEngine:
    """
    状态差异计算引擎.

    职责:
      1. 接收两个 WorldState，计算 StateDiff
      2. 也支持 dict 输入（用于测试和序列化场景）
      3. 生成 ChangeRecord[] 供细粒度遍历

    使用:
      engine = StateDiffEngine()
      diff = engine.diff(state_before, state_after)
      print(diff.summary)
    """

    def diff(self, before: Any, after: Any) -> StateDiff:
        """
        计算两个 WorldState 之间的差异.

        支持:
          - WorldState 实例
          - dict (to_dict() 输出)
        """
        if isinstance(before, dict) and isinstance(after, dict):
            return self._diff_dicts(before, after)
        return self._diff_world_states(before, after)

    def _diff_world_states(self, before: Any, after: Any) -> StateDiff:
        changes: list[ChangeRecord] = []

        added_constraints = self._list_diff(
            before.active_constraints, after.active_constraints,
        )
        removed_constraints = self._list_diff(
            after.active_constraints, before.active_constraints,
        )
        for c in added_constraints:
            changes.append(ChangeRecord(
                category=ChangeCategory.CONSTRAINT,
                direction=ChangeDirection.ADDED,
                key=c,
                new_value=c,
            ))
        for c in removed_constraints:
            changes.append(ChangeRecord(
                category=ChangeCategory.CONSTRAINT,
                direction=ChangeDirection.REMOVED,
                key=c,
                old_value=c,
            ))

        before_fact_exprs = [f.expression for f in before.facts.facts]
        after_fact_exprs = [f.expression for f in after.facts.facts]
        added_facts = self._list_diff(before_fact_exprs, after_fact_exprs)
        for f in added_facts:
            changes.append(ChangeRecord(
                category=ChangeCategory.FACT,
                direction=ChangeDirection.ADDED,
                key=f,
                new_value=f,
            ))

        before_invalidated = [
            f.expression for f in before.facts.facts
            if getattr(f, "is_invalidated", False)
        ]
        after_invalidated = [
            f.expression for f in after.facts.facts
            if getattr(f, "is_invalidated", False)
        ]
        invalidated_facts = self._list_diff(before_invalidated, after_invalidated)
        for f in invalidated_facts:
            changes.append(ChangeRecord(
                category=ChangeCategory.FACT,
                direction=ChangeDirection.STATUS_CHANGED,
                key=f,
                detail="失效",
            ))

        before_goal_descs = [g.description for g in before.goals]
        after_goal_descs = [g.description for g in after.goals]
        added_goals = self._list_diff(before_goal_descs, after_goal_descs)
        for g in added_goals:
            changes.append(ChangeRecord(
                category=ChangeCategory.GOAL,
                direction=ChangeDirection.ADDED,
                key=g,
                new_value=g,
            ))

        before_solved = [
            g.description for g in before.goals
            if g.status.name == "ACHIEVED"
        ]
        after_solved = [
            g.description for g in after.goals
            if g.status.name == "ACHIEVED"
        ]
        solved_goals = self._list_diff(before_solved, after_solved)
        for g in solved_goals:
            changes.append(ChangeRecord(
                category=ChangeCategory.GOAL,
                direction=ChangeDirection.STATUS_CHANGED,
                key=g,
                new_value="ACHIEVED",
                detail="达成",
            ))

        before_obl_props = [o.proposition for o in before.obligations]
        after_obl_props = [o.proposition for o in after.obligations]
        added_obligations = self._list_diff(before_obl_props, after_obl_props)
        for o in added_obligations:
            changes.append(ChangeRecord(
                category=ChangeCategory.OBLIGATION,
                direction=ChangeDirection.ADDED,
                key=o,
                new_value=o,
            ))

        before_discharged = [
            o.proposition for o in before.obligations
            if o.status.name == "DISCHARGED"
        ]
        after_discharged = [
            o.proposition for o in after.obligations
            if o.status.name == "DISCHARGED"
        ]
        discharged_obligations = self._list_diff(before_discharged, after_discharged)
        for o in discharged_obligations:
            changes.append(ChangeRecord(
                category=ChangeCategory.OBLIGATION,
                direction=ChangeDirection.STATUS_CHANGED,
                key=o,
                new_value="DISCHARGED",
                detail="已证明",
            ))

        before_assumption_props = [a.proposition for a in before.assumptions]
        after_assumption_props = [a.proposition for a in after.assumptions]
        added_assumptions = self._list_diff(before_assumption_props, after_assumption_props)
        retracted_assumptions = self._list_diff(after_assumption_props, before_assumption_props)
        for a in added_assumptions:
            changes.append(ChangeRecord(
                category=ChangeCategory.ASSUMPTION,
                direction=ChangeDirection.ADDED,
                key=a,
                new_value=a,
            ))
        for a in retracted_assumptions:
            changes.append(ChangeRecord(
                category=ChangeCategory.ASSUMPTION,
                direction=ChangeDirection.REMOVED,
                key=a,
                old_value=a,
            ))

        before_expr_texts = [
            e.latex or e.raw_text or "" for e in before.expressions
        ]
        after_expr_texts = [
            e.latex or e.raw_text or "" for e in after.expressions
        ]
        added_expressions = self._list_diff(before_expr_texts, after_expr_texts)
        for e in added_expressions:
            changes.append(ChangeRecord(
                category=ChangeCategory.EXPRESSION,
                direction=ChangeDirection.ADDED,
                key=e,
                new_value=e,
            ))

        before_domain_vars = list(before.domains.entries.keys()) if hasattr(before.domains, 'entries') else []
        after_domain_vars = list(after.domains.entries.keys()) if hasattr(after.domains, 'entries') else []
        added_domains = self._list_diff(before_domain_vars, after_domain_vars)
        for d in added_domains:
            changes.append(ChangeRecord(
                category=ChangeCategory.DOMAIN,
                direction=ChangeDirection.ADDED,
                key=d,
                new_value=d,
            ))

        legality_change = None
        before_legal = self._check_legality(before)
        after_legal = self._check_legality(after)
        if before_legal != after_legal:
            legality_change = "合法" if after_legal else "非法"

        confidence_delta = self._compute_confidence_delta(before, after)

        source_operation = ""
        if hasattr(after, 'metadata') and hasattr(after.metadata, 'source_operation'):
            source_operation = after.metadata.source_operation

        return StateDiff(
            added_constraints=added_constraints,
            removed_constraints=removed_constraints,
            added_facts=added_facts,
            invalidated_facts=invalidated_facts,
            added_goals=added_goals,
            solved_goals=solved_goals,
            added_obligations=added_obligations,
            discharged_obligations=discharged_obligations,
            added_assumptions=added_assumptions,
            retracted_assumptions=retracted_assumptions,
            added_expressions=added_expressions,
            added_domains=added_domains,
            legality_change=legality_change,
            confidence_delta=confidence_delta,
            changes=changes,
            source_operation=source_operation,
            before_fingerprint=before.fingerprint if hasattr(before, 'fingerprint') else "",
            after_fingerprint=after.fingerprint if hasattr(after, 'fingerprint') else "",
        )

    def _diff_dicts(self, before: dict, after: dict) -> StateDiff:
        changes: list[ChangeRecord] = []

        before_constraints = before.get("constraints", {})
        after_constraints = after.get("constraints", {})
        before_constraint_list = self._extract_constraint_exprs(before_constraints)
        after_constraint_list = self._extract_constraint_exprs(after_constraints)
        added_constraints = self._list_diff(before_constraint_list, after_constraint_list)
        removed_constraints = self._list_diff(after_constraint_list, before_constraint_list)
        for c in added_constraints:
            changes.append(ChangeRecord(
                category=ChangeCategory.CONSTRAINT,
                direction=ChangeDirection.ADDED,
                key=c,
            ))
        for c in removed_constraints:
            changes.append(ChangeRecord(
                category=ChangeCategory.CONSTRAINT,
                direction=ChangeDirection.REMOVED,
                key=c,
            ))

        before_facts = [
            f.get("expression", "") for f in before.get("facts", {}).get("facts", [])
        ]
        after_facts = [
            f.get("expression", "") for f in after.get("facts", {}).get("facts", [])
        ]
        added_facts = self._list_diff(before_facts, after_facts)
        for f in added_facts:
            changes.append(ChangeRecord(
                category=ChangeCategory.FACT,
                direction=ChangeDirection.ADDED,
                key=f,
            ))

        invalidated_facts = [
            f.get("expression", "")
            for f in after.get("facts", {}).get("facts", [])
            if f.get("is_invalidated", False)
        ]

        before_goals = [g.get("description", "") for g in before.get("goals", [])]
        after_goals = [g.get("description", "") for g in after.get("goals", [])]
        added_goals = self._list_diff(before_goals, after_goals)
        before_solved = [
            g.get("description", "") for g in before.get("goals", [])
            if g.get("status") == "ACHIEVED"
        ]
        after_solved = [
            g.get("description", "") for g in after.get("goals", [])
            if g.get("status") == "ACHIEVED"
        ]
        solved_goals = self._list_diff(before_solved, after_solved)

        before_obls = [o.get("proposition", "") for o in before.get("obligations", [])]
        after_obls = [o.get("proposition", "") for o in after.get("obligations", [])]
        added_obligations = self._list_diff(before_obls, after_obls)
        before_discharged = [
            o.get("proposition", "") for o in before.get("obligations", [])
            if o.get("status") == "DISCHARGED"
        ]
        after_discharged = [
            o.get("proposition", "") for o in after.get("obligations", [])
            if o.get("status") == "DISCHARGED"
        ]
        discharged_obligations = self._list_diff(before_discharged, after_discharged)

        before_assumptions = [a.get("proposition", "") for a in before.get("assumptions", [])]
        after_assumptions = [a.get("proposition", "") for a in after.get("assumptions", [])]
        added_assumptions = self._list_diff(before_assumptions, after_assumptions)
        retracted_assumptions = self._list_diff(after_assumptions, before_assumptions)

        added_expressions = []
        before_exprs = before.get("expressions", [])
        after_exprs = after.get("expressions", [])
        if isinstance(before_exprs, list) and isinstance(after_exprs, list):
            before_expr_texts = [
                e.get("latex", "") or e.get("raw_text", "") if isinstance(e, dict) else str(e)
                for e in before_exprs
            ]
            after_expr_texts = [
                e.get("latex", "") or e.get("raw_text", "") if isinstance(e, dict) else str(e)
                for e in after_exprs
            ]
            added_expressions = self._list_diff(before_expr_texts, after_expr_texts)

        added_domains = list(
            set(after.get("domains", {}).keys())
            - set(before.get("domains", {}).keys())
        )

        source_operation = after.get("metadata", {}).get("source_operation", "")

        return StateDiff(
            added_constraints=added_constraints,
            removed_constraints=removed_constraints,
            added_facts=added_facts,
            invalidated_facts=invalidated_facts,
            added_goals=added_goals,
            solved_goals=solved_goals,
            added_obligations=added_obligations,
            discharged_obligations=discharged_obligations,
            added_assumptions=added_assumptions,
            retracted_assumptions=retracted_assumptions,
            added_expressions=added_expressions,
            added_domains=added_domains,
            changes=changes,
            source_operation=source_operation,
        )

    # ───────────────────────────────────────────────────────
    # 辅助方法
    # ───────────────────────────────────────────────────────

    @staticmethod
    def _list_diff(before: list, after: list) -> list:
        before_set = set(before)
        after_set = set(after)
        return sorted(after_set - before_set)

    @staticmethod
    def _extract_constraint_exprs(constraints_data: Any) -> list[str]:
        if isinstance(constraints_data, dict):
            nodes = constraints_data.get("nodes", [])
            return [
                n.get("expression", "") for n in nodes
                if n.get("status") in ("ACTIVE", "DERIVED")
            ]
        if isinstance(constraints_data, list):
            return constraints_data
        return []

    @staticmethod
    def _check_legality(state: Any) -> bool:
        if hasattr(state, 'constraints') and hasattr(state.constraints, 'detect_conflicts'):
            report = state.constraints.detect_conflicts()
            return not getattr(report, 'has_conflict', False)
        return True

    @staticmethod
    def _compute_confidence_delta(before: Any, after: Any) -> float:
        before_conf = 0.0
        after_conf = 0.0
        if hasattr(before, 'facts') and hasattr(before.facts, 'facts'):
            facts = before.facts.facts
            if facts:
                before_conf = sum(getattr(f, 'confidence', 1.0) for f in facts) / len(facts)
        if hasattr(after, 'facts') and hasattr(after.facts, 'facts'):
            facts = after.facts.facts
            if facts:
                after_conf = sum(getattr(f, 'confidence', 1.0) for f in facts) / len(facts)
        return round(after_conf - before_conf, 4)


# ═══════════════════════════════════════════════════════════
# Transition Chain — 状态转移链
# ═══════════════════════════════════════════════════════════

@dataclass
class TransitionRecord:
    """
    单次状态转移记录.

    记录: 从哪个状态到哪个状态，执行了什么操作，产生了什么差异.
    """
    step_id: str = ""
    operation: str = ""
    diff: StateDiff = field(default_factory=StateDiff)
    before_fingerprint: str = ""
    after_fingerprint: str = ""
    timestamp: str = ""

    @property
    def summary(self) -> str:
        op = self.operation or "未知操作"
        diff_summary = self.diff.summary
        return f"[{self.step_id}] {op}: {diff_summary}"


@dataclass
class TransitionChain:
    """
    状态转移链 — 完整的推理过程记录.

    由多个 TransitionRecord 组成，展示从初始状态到最终状态的完整演化路径.
    """
    records: list[TransitionRecord] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.records)

    @property
    def is_empty(self) -> bool:
        return len(self.records) == 0

    @property
    def total_changes(self) -> int:
        return sum(r.diff.total_changes for r in self.records)

    @property
    def all_discharged_obligations(self) -> list[str]:
        result: list[str] = []
        for r in self.records:
            result.extend(r.diff.discharged_obligations)
        return result

    @property
    def all_solved_goals(self) -> list[str]:
        result: list[str] = []
        for r in self.records:
            result.extend(r.diff.solved_goals)
        return result

    @property
    def all_regressions(self) -> list[TransitionRecord]:
        return [r for r in self.records if r.diff.has_regressions]

    @property
    def overall_sentiment(self) -> str:
        sentiments = [r.diff.overall_sentiment for r in self.records]
        has_regression = "regression" in sentiments or "mixed" in sentiments
        has_progress = "progress" in sentiments or "mixed" in sentiments
        if has_regression and not has_progress:
            return "regression"
        if has_progress and not has_regression:
            return "progress"
        if has_progress and has_regression:
            return "mixed"
        return "neutral"

    def append(self, record: TransitionRecord) -> TransitionChain:
        return TransitionChain(records=self.records + [record])

    def to_dict(self) -> dict:
        return {
            "length": self.length,
            "total_changes": self.total_changes,
            "overall_sentiment": self.overall_sentiment,
            "records": [
                {
                    "step_id": r.step_id,
                    "operation": r.operation,
                    "diff": r.diff.to_dict(),
                    "before_fingerprint": r.before_fingerprint,
                    "after_fingerprint": r.after_fingerprint,
                }
                for r in self.records
            ],
        }
