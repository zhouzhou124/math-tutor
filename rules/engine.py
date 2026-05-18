"""
Rule Engine — 规则引擎

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  RuleEngine 是规则执行的核心调度器。

  职责：
    1. 根据操作类型查找适用规则
    2. 按优先级排序
    3. 逐一应用规则
    4. 汇总结果：
       - 所有适用的规则
       - 所有违反的前提
       - 所有生成的约束
       - 所有证明义务
       - 综合置信度

  输出：
    EngineResult — 综合判定结果

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from operations import Op
from rules.dsl import (
    Rule,
    RuleContext,
    RuleApplicationResult,
    ProofObligation,
    ObligationSeverity,
)


@dataclass
class EngineResult:
    """规则引擎的综合执行结果。"""
    op: Op = Op.COMPUTE
    rules_applied: tuple[str, ...] = ()
    rules_skipped: tuple[str, ...] = ()
    all_preconditions_met: bool = True
    all_postconditions_met: bool = True
    failed_preconditions: tuple[str, ...] = ()
    generated_constraints: tuple[str, ...] = ()
    generated_subgoals: tuple[str, ...] = ()
    may_lose_constraints: tuple[str, ...] = ()
    may_introduce_assumptions: tuple[str, ...] = ()
    proof_obligations: tuple[ProofObligation, ...] = ()
    mandatory_obligations: tuple[ProofObligation, ...] = ()
    confidence: float = 1.0
    explanation: str = ""
    rule_results: tuple[RuleApplicationResult, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.all_preconditions_met and not self.mandatory_obligations

    @property
    def is_suspect(self) -> bool:
        return self.all_preconditions_met and bool(self.mandatory_obligations)

    @property
    def is_invalid(self) -> bool:
        return not self.all_preconditions_met

    def to_verification_dict(self) -> dict:
        """转换为 VerificationResult 兼容的字典。"""
        if self.is_valid:
            legality = "valid"
        elif self.is_suspect:
            legality = "suspect"
        else:
            legality = "invalid"

        return {
            "valid": self.is_valid or self.is_suspect,
            "legality": legality,
            "confidence": self.confidence,
            "violated_constraints": list(self.failed_preconditions),
            "introduced_assumptions": list(self.may_introduce_assumptions),
            "lost_constraints": list(self.may_lose_constraints),
            "generated_subgoals": list(self.generated_subgoals),
            "explanation": self.explanation,
        }


class RuleEngine:
    """
    规则引擎：查找、排序、应用规则，汇总结果。

    使用方式：
        engine = RuleEngine(registry)
        result = engine.apply(op, context)

    registry: dict[Op, list[Rule]] — 按 Op 分类的规则注册表
    """

    def __init__(self, registry: Optional[dict[Op, list[Rule]]] = None):
        self._registry: dict[Op, list[Rule]] = registry or {}

    def register(self, rule: Rule) -> None:
        """注册一条规则。"""
        if rule.op not in self._registry:
            self._registry[rule.op] = []
        self._registry[rule.op].append(rule)
        self._registry[rule.op].sort(key=lambda r: r.priority, reverse=True)

    def register_many(self, rules: list[Rule]) -> None:
        """批量注册规则。"""
        for rule in rules:
            self.register(rule)

    def apply(self, context: RuleContext) -> EngineResult:
        """
        对给定上下文应用所有适用规则。

        流程：
          1. 查找 op 对应的所有规则
          2. 按优先级排序
          3. 逐一应用
          4. 汇总结果
        """
        rules = self._registry.get(context.op, [])

        if not rules:
            return EngineResult(
                op=context.op,
                confidence=0.0,
                explanation=f"无规则覆盖操作: {context.op.value}",
            )

        results: list[RuleApplicationResult] = []
        for rule in rules:
            result = rule.apply(context)
            results.append(result)

        return self._aggregate(context.op, results)

    def _aggregate(self, op: Op, results: list[RuleApplicationResult]) -> EngineResult:
        """汇总多条规则的应用结果。"""
        applied = []
        skipped = []
        all_failed_pre = []
        all_failed_post = []
        all_constraints = []
        all_subgoals = []
        all_lost = []
        all_introduced = []
        all_obligations = []
        confidences = []

        for r in results:
            if r.applicable:
                applied.append(r.rule_name)
                confidences.append(r.confidence)
            else:
                skipped.append(r.rule_name)

            all_failed_pre.extend(r.failed_preconditions)
            all_failed_post.extend(r.failed_postconditions)
            all_constraints.extend(r.generated_constraints)
            all_subgoals.extend(r.generated_subgoals)
            all_lost.extend(r.may_lose_constraints)
            all_introduced.extend(r.may_introduce_assumptions)
            all_obligations.extend(r.proof_obligations)

        unique_failed_pre = list(dict.fromkeys(all_failed_pre))
        unique_failed_post = list(dict.fromkeys(all_failed_post))
        unique_constraints = list(dict.fromkeys(all_constraints))
        unique_subgoals = list(dict.fromkeys(all_subgoals))
        unique_lost = list(dict.fromkeys(all_lost))
        unique_introduced = list(dict.fromkeys(all_introduced))
        unique_obligations = list(dict.fromkeys(all_obligations))

        mandatory = [o for o in unique_obligations if o.is_mandatory]

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        preconditions_met = len(unique_failed_pre) == 0
        postconditions_met = len(unique_failed_post) == 0

        explanation_parts = []
        if applied:
            explanation_parts.append(f"适用规则: {', '.join(applied)}")
        if skipped:
            explanation_parts.append(f"跳过规则: {', '.join(skipped)}")
        if unique_failed_pre:
            explanation_parts.append(f"前提不满足: {', '.join(unique_failed_pre)}")
        if unique_lost:
            explanation_parts.append(f"可能丢失约束: {', '.join(unique_lost)}")
        if unique_introduced:
            explanation_parts.append(f"可能引入假设: {', '.join(unique_introduced)}")
        if mandatory:
            explanation_parts.append(f"必须证明: {', '.join(o.description for o in mandatory)}")

        return EngineResult(
            op=op,
            rules_applied=tuple(applied),
            rules_skipped=tuple(skipped),
            all_preconditions_met=preconditions_met,
            all_postconditions_met=postconditions_met,
            failed_preconditions=tuple(unique_failed_pre),
            generated_constraints=tuple(unique_constraints),
            generated_subgoals=tuple(unique_subgoals),
            may_lose_constraints=tuple(unique_lost),
            may_introduce_assumptions=tuple(unique_introduced),
            proof_obligations=tuple(unique_obligations),
            mandatory_obligations=tuple(mandatory),
            confidence=avg_confidence,
            explanation="; ".join(explanation_parts),
            rule_results=tuple(results),
        )

    @property
    def registry(self) -> dict[Op, list[Rule]]:
        return self._registry

    def rules_for_op(self, op: Op) -> list[Rule]:
        return self._registry.get(op, [])
