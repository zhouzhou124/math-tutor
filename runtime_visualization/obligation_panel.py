"""Obligation Panel — 证明义务面板

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  这是整个系统最重要的"教学层"。

  数学导师 vs AI 判题器的区别:
    AI 判题器:  "你错了"
    数学导师:  "你缺少这个证明"

  数学中大量错误不是"算错"，而是"漏证明":
    约分       → 分母 ≠ 0
    开平方     → 被开方 ≥ 0
    两边平方   → 需验证增根
    洛必达     → 满足 0/0 或 ∞/∞
    换元积分   → 换元可逆
    乘以负数   → 不等号翻转

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  WorldState.obligations (runtime)
  RuleApplicationResult.proof_obligations (rules)
  StepBlock.proof_obligations (document_ast)
      ↓
  ObligationPanel
      ↓
  ObligationView[]  ← 富数据结构，携带"为什么需要"
      ↓
  Streamlit UI / DocumentNode[] / Markdown / HTML

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Sequence

from rendering.obligation_renderer import (
    ObligationRenderer,
    ObligationRendererConfig,
    VisualObligation,
    ObligationItem,
    ObligationStatus,
    ObligationSeverity,
)
from rendering.document_ast import (
    BlockType,
    DocumentNode,
    StepBlock,
    ProofBlock,
)
from rendering.math_formatter import MathFormatter


# ═══════════════════════════════════════════════════════════
# Obligation View — 面板核心数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class ObligationView:
    """
    证明义务视图 — 面板渲染的核心数据.

    比裸 ProofObligation 多了:
      - explanation:       为什么需要这个证明
      - theorem_reference: 相关定理引用
      - suggested_action:  建议学生做什么
      - counter_example:   不满足时的反例

    这些是"数学导师"区别于"AI判题器"的关键.
    """

    obligation_id: str = ""
    proposition: str = ""
    severity: ObligationSeverity = ObligationSeverity.MANDATORY
    status: ObligationStatus = ObligationStatus.PENDING
    generated_by_step: str = ""
    resolved_by_step: Optional[str] = None
    explanation: str = ""
    theorem_reference: Optional[str] = None
    suggested_action: Optional[str] = None
    counter_example: Optional[str] = None

    @property
    def is_pending(self) -> bool:
        return self.status == ObligationStatus.PENDING

    @property
    def is_discharged(self) -> bool:
        return self.status == ObligationStatus.DISCHARGED

    @property
    def is_mandatory(self) -> bool:
        return self.severity == ObligationSeverity.MANDATORY

    @property
    def icon(self) -> str:
        if self.status == ObligationStatus.DISCHARGED:
            return "✅"
        if self.status == ObligationStatus.VIOLATED:
            return "❌"
        if self.status == ObligationStatus.WAIVED:
            return "⏭️"
        if self.severity == ObligationSeverity.MANDATORY:
            return "🔴"
        if self.severity == ObligationSeverity.RECOMMENDED:
            return "🟡"
        return "🔵"

    @property
    def severity_label(self) -> str:
        return {
            ObligationSeverity.MANDATORY: "必须证明",
            ObligationSeverity.RECOMMENDED: "建议证明",
            ObligationSeverity.INFORMATIONAL: "信息提醒",
        }[self.severity]

    @property
    def status_label(self) -> str:
        return {
            ObligationStatus.PENDING: "未证明",
            ObligationStatus.DISCHARGED: "已证明",
            ObligationStatus.WAIVED: "已跳过",
            ObligationStatus.VIOLATED: "已违反",
        }[self.status]

    def to_obligation_item(self) -> ObligationItem:
        return ObligationItem(
            proposition=self.proposition,
            status=self.status,
            severity=self.severity,
            reason=self.explanation,
            source_step=self.generated_by_step,
            discharged_by=self.resolved_by_step or "",
        )

    def to_dict(self) -> dict:
        d: dict = {
            "obligation_id": self.obligation_id,
            "proposition": self.proposition,
            "severity": self.severity.value,
            "status": self.status.value,
        }
        if self.generated_by_step:
            d["generated_by_step"] = self.generated_by_step
        if self.resolved_by_step:
            d["resolved_by_step"] = self.resolved_by_step
        if self.explanation:
            d["explanation"] = self.explanation
        if self.theorem_reference:
            d["theorem_reference"] = self.theorem_reference
        if self.suggested_action:
            d["suggested_action"] = self.suggested_action
        if self.counter_example:
            d["counter_example"] = self.counter_example
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ObligationView:
        return cls(
            obligation_id=d.get("obligation_id", ""),
            proposition=d.get("proposition", ""),
            severity=_parse_severity(d.get("severity", "mandatory")),
            status=_parse_status(d.get("status", "pending")),
            generated_by_step=d.get("generated_by_step", d.get("source_step", "")),
            resolved_by_step=d.get("resolved_by_step", d.get("discharged_by")),
            explanation=d.get("explanation", d.get("reason", "")),
            theorem_reference=d.get("theorem_reference"),
            suggested_action=d.get("suggested_action"),
            counter_example=d.get("counter_example"),
        )


# ═══════════════════════════════════════════════════════════
# Operation → Obligation 映射表
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObligationTemplate:
    """
    操作→义务模板.

    当学生执行某操作时，系统自动生成对应的证明义务.
    """
    operation: str
    proposition_template: str
    explanation_template: str
    severity: ObligationSeverity = ObligationSeverity.MANDATORY
    theorem_reference: str = ""
    suggested_action_template: str = ""
    counter_example_template: str = ""

    def instantiate(self, **kwargs) -> ObligationView:
        import hashlib
        raw = f"{self.operation}:{self.proposition_template}:{kwargs}"
        oid = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return ObligationView(
            obligation_id=oid,
            proposition=self.proposition_template.format(**kwargs),
            severity=self.severity,
            status=ObligationStatus.PENDING,
            explanation=self.explanation_template.format(**kwargs),
            theorem_reference=self.theorem_reference or None,
            suggested_action=self.suggested_action_template.format(**kwargs) if self.suggested_action_template else None,
            counter_example=self.counter_example_template.format(**kwargs) if self.counter_example_template else None,
            generated_by_step=kwargs.get("step_id", ""),
        )


OBLIGATION_TEMPLATES: dict[str, list[ObligationTemplate]] = {
    "cancel": [
        ObligationTemplate(
            operation="cancel",
            proposition_template="{factor} ≠ 0",
            explanation_template="约去因子 {factor} 时，必须保证 {factor} ≠ 0，否则等价性被破坏",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="添加条件 {factor} ≠ 0",
            counter_example_template="若 {factor} = 0，原式无定义",
        ),
    ],
    "simplify": [
        ObligationTemplate(
            operation="simplify",
            proposition_template="{expr} ≥ 0",
            explanation_template="化简根式时，需确认根号内表达式非负",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="验证 {expr} ≥ 0",
            counter_example_template="若 {expr} < 0，根式无实数意义",
        ),
    ],
    "sqrt_both_sides": [
        ObligationTemplate(
            operation="sqrt_both_sides",
            proposition_template="需讨论正负两种情况",
            explanation_template="方程两边开平方后，需讨论正负两种情况：√(a²) = |a|，不是 a",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="补充 ± 情况讨论",
            counter_example_template="x² = 4 → x = ±2，不能只写 x = 2",
        ),
    ],
    "square_both_sides": [
        ObligationTemplate(
            operation="square_both_sides",
            proposition_template="需验证增根",
            explanation_template="方程两边平方可能引入增根，需将解代回原方程验证",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="将求得的解代回原方程验证",
            counter_example_template="√(x) = -1 平方得 x = 1，但 √1 ≠ -1",
        ),
    ],
    "lhopital": [
        ObligationTemplate(
            operation="lhopital",
            proposition_template="满足 0/0 或 ∞/∞ 型未定式",
            explanation_template="洛必达法则要求极限是 0/0 或 ∞/∞ 型未定式",
            severity=ObligationSeverity.MANDATORY,
            theorem_reference="洛必达法则",
            suggested_action_template="验证分子分母同时趋于 0 或 ∞",
            counter_example_template="lim(x→1) x/(x+1) 不是未定式，不能用洛必达",
        ),
    ],
    "substitute": [
        ObligationTemplate(
            operation="substitute",
            proposition_template="换元函数 {g} 单调可逆",
            explanation_template="换元积分要求换元函数单调可逆，否则积分上下限和回代可能出错",
            severity=ObligationSeverity.RECOMMENDED,
            suggested_action_template="验证 {g} 的单调性并确认可逆",
        ),
        ObligationTemplate(
            operation="substitute",
            proposition_template="回代原变量",
            explanation_template="换元积分后需将结果用原变量表示",
            severity=ObligationSeverity.INFORMATIONAL,
            suggested_action_template="将 t = {g} 回代",
        ),
    ],
    "multiply_negative": [
        ObligationTemplate(
            operation="multiply_negative",
            proposition_template="不等号方向已反转",
            explanation_template="不等式两边乘以负数时，不等号方向必须反转",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="确认乘数为负，并翻转不等号",
            counter_example_template="若 -2x > 4，则 x < -2（不是 x > -2）",
        ),
    ],
    "divide": [
        ObligationTemplate(
            operation="divide",
            proposition_template="{divisor} ≠ 0",
            explanation_template="除法要求除数不为零",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="添加条件 {divisor} ≠ 0",
            counter_example_template="若 {divisor} = 0，除法无意义",
        ),
    ],
    "apply_theorem": [
        ObligationTemplate(
            operation="apply_theorem",
            proposition_template="验证{theorem}的所有前提条件",
            explanation_template="应用定理前，必须验证定理的所有前提条件是否满足",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="逐一检查{theorem}的前提条件",
        ),
    ],
    "classify": [
        ObligationTemplate(
            operation="classify",
            proposition_template="分类不重不漏",
            explanation_template="分类讨论必须覆盖所有情况，且各类之间互不重叠",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="检查是否遗漏情况，各类是否互斥",
        ),
    ],
    "induction_step": [
        ObligationTemplate(
            operation="induction_step",
            proposition_template="验证基础情形 (n=1)",
            explanation_template="数学归纳法必须先验证基础情形，再进行归纳步骤",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="验证 n=1 时命题成立",
        ),
    ],
    "differentiate_parametric": [
        ObligationTemplate(
            operation="differentiate_parametric",
            proposition_template="dx/dt ≠ 0",
            explanation_template="参数方程求导要求 dx/dt ≠ 0，否则 dy/dx 无意义",
            severity=ObligationSeverity.MANDATORY,
            suggested_action_template="验证 dx/dt ≠ 0",
        ),
    ],
}


# ═══════════════════════════════════════════════════════════
# Obligation Panel
# ═══════════════════════════════════════════════════════════

@dataclass
class ObligationPanelConfig:
    show_explanation: bool = True
    show_suggested_action: bool = True
    show_counter_example: bool = True
    show_theorem_reference: bool = True
    show_discharged: bool = False
    collapsible_explanations: bool = True
    math_mode: str = "display"


class ObligationPanel:
    """
    证明义务面板 — 系统最重要的教学层.

    职责:
      1. 从 WorldState / RuleApplicationResult / StepBlock 收集义务
      2. 用 OBLIGATION_TEMPLATES 丰富义务（添加"为什么需要"）
      3. 生成 ObligationView[] 供 UI 渲染
      4. 提供 render_* 方法直接输出到 Streamlit / DocumentNode[]

    核心价值:
      "数学规范性教学" — 不只看结果，更看过程是否严谨
    """

    def __init__(self, config: ObligationPanelConfig = None):
        self.config = config or ObligationPanelConfig()
        self._renderer = ObligationRenderer(
            ObligationRendererConfig(
                show_reason=config.show_explanation if config else True,
                show_severity=True,
                show_summary=True,
            )
        )
        self._fmt = MathFormatter()

    # ───────────────────────────────────────────────────────
    # 收集义务
    # ───────────────────────────────────────────────────────

    def collect_from_world_state(self, state: Any) -> list[ObligationView]:
        """从 WorldState 收集所有待证明义务."""
        views: list[ObligationView] = []
        for obl in getattr(state, "obligations", ()):
            views.append(self._runtime_obligation_to_view(obl))
        return views

    def collect_from_step_block(self, step: StepBlock) -> list[ObligationView]:
        """从 StepBlock 收集义务."""
        views: list[ObligationView] = []
        for obl in step.proof_obligations:
            views.append(self._runtime_obligation_to_view(obl, step.step_id))
        return views

    def collect_from_rule_result(self, result: Any) -> list[ObligationView]:
        """从 RuleApplicationResult 收集义务."""
        views: list[ObligationView] = []
        for obl in getattr(result, "proof_obligations", ()):
            views.append(self._dsl_obligation_to_view(obl))
        return views

    def collect_from_dict_list(self, items: Sequence[dict]) -> list[ObligationView]:
        """从 dict 列表收集义务."""
        return [ObligationView.from_dict(d) for d in items]

    # ───────────────────────────────────────────────────────
    # 操作 → 义务生成
    # ───────────────────────────────────────────────────────

    def generate_for_operation(
        self, operation: str, step_id: str = "", **kwargs,
    ) -> list[ObligationView]:
        """
        根据操作类型自动生成证明义务.

        例:
          panel.generate_for_operation("cancel", factor="x-1", step_id="s3")
          → [ObligationView(proposition="x-1 ≠ 0", explanation="约去因子...")]
        """
        templates = OBLIGATION_TEMPLATES.get(operation, [])
        all_kwargs = {"step_id": step_id, **kwargs}
        return [t.instantiate(**all_kwargs) for t in templates]

    # ───────────────────────────────────────────────────────
    # 义务状态管理
    # ───────────────────────────────────────────────────────

    def discharge(
        self, views: list[ObligationView], proposition: str, by_step: str = "",
    ) -> list[ObligationView]:
        """将匹配 proposition 的义务标记为已证明."""
        result = []
        for v in views:
            if v.proposition == proposition and v.is_pending:
                result.append(ObligationView(
                    obligation_id=v.obligation_id,
                    proposition=v.proposition,
                    severity=v.severity,
                    status=ObligationStatus.DISCHARGED,
                    generated_by_step=v.generated_by_step,
                    resolved_by_step=by_step,
                    explanation=v.explanation,
                    theorem_reference=v.theorem_reference,
                    suggested_action=v.suggested_action,
                    counter_example=v.counter_example,
                ))
            else:
                result.append(v)
        return result

    def violate(
        self, views: list[ObligationView], proposition: str, reason: str = "",
    ) -> list[ObligationView]:
        """将匹配 proposition 的义务标记为已违反."""
        result = []
        for v in views:
            if v.proposition == proposition and v.is_pending:
                result.append(ObligationView(
                    obligation_id=v.obligation_id,
                    proposition=v.proposition,
                    severity=v.severity,
                    status=ObligationStatus.VIOLATED,
                    generated_by_step=v.generated_by_step,
                    resolved_by_step=v.resolved_by_step,
                    explanation=reason or v.explanation,
                    theorem_reference=v.theorem_reference,
                    suggested_action=v.suggested_action,
                    counter_example=v.counter_example,
                ))
            else:
                result.append(v)
        return result

    # ───────────────────────────────────────────────────────
    # 统计
    # ───────────────────────────────────────────────────────

    def stats(self, views: list[ObligationView]) -> dict:
        pending = sum(1 for v in views if v.is_pending)
        discharged = sum(1 for v in views if v.is_discharged)
        mandatory_pending = sum(1 for v in views if v.is_pending and v.is_mandatory)
        violated = sum(1 for v in views if v.status == ObligationStatus.VIOLATED)
        return {
            "total": len(views),
            "pending": pending,
            "discharged": discharged,
            "mandatory_pending": mandatory_pending,
            "violated": violated,
            "all_discharged": pending == 0 and len(views) > 0,
            "has_violations": violated > 0,
        }

    # ───────────────────────────────────────────────────────
    # 转换 → VisualObligation (复用已有渲染管线)
    # ───────────────────────────────────────────────────────

    def to_visual_obligation(
        self, views: list[ObligationView], title: str = "需要额外证明",
    ) -> VisualObligation:
        """将 ObligationView[] 转为 VisualObligation 供渲染."""
        items = [v.to_obligation_item() for v in views]
        has_mandatory = any(v.is_pending and v.is_mandatory for v in views)
        icon = "⚠️" if has_mandatory else "📌"
        return VisualObligation(
            icon=icon,
            title=title,
            items=items,
        )

    # ───────────────────────────────────────────────────────
    # 转换 → DocumentNode[] (供 Exporter 使用)
    # ───────────────────────────────────────────────────────

    def to_document_nodes(
        self, views: list[ObligationView], title: str = "需要额外证明",
    ) -> list[DocumentNode]:
        """将 ObligationView[] 转为 DocumentNode[] 供导出."""
        vo = self.to_visual_obligation(views, title)
        return self._renderer.render_visual_obligation(vo)

    # ───────────────────────────────────────────────────────
    # Streamlit 渲染
    # ───────────────────────────────────────────────────────

    def render_streamlit(
        self, views: list[ObligationView], title: str = "需要额外证明",
        step_context: str = "",
    ) -> None:
        """
        渲染证明义务面板到 Streamlit.

        效果:
          ┌─────────────────────────────────────────┐
          │ ⚠ 需要证明                              │
          │                                         │
          │ 条件           状态                      │
          │ x - 1 ≠ 0     ❌ 未证明                 │
          │                                         │
          │ 为什么需要？                             │
          │ 因为约去了因子：x-1                      │
          │ 若 x=1，原式无定义。                     │
          │                                         │
          │ 建议补充                                 │
          │ x ≠ 1                                    │
          └─────────────────────────────────────────┘
        """
        import streamlit as st

        if not views:
            return

        pending = [v for v in views if v.is_pending]
        discharged = [v for v in views if v.is_discharged]
        violated = [v for v in views if v.status == ObligationStatus.VIOLATED]

        if not self.config.show_discharged:
            display_views = pending + violated
        else:
            display_views = views

        if not display_views:
            if discharged:
                st.success(f"✅ 所有 {len(discharged)} 项证明义务已满足")
            return

        has_mandatory = any(v.is_mandatory for v in pending)
        has_violations = len(violated) > 0

        if has_violations:
            container = st.error
            header_icon = "❌"
        elif has_mandatory:
            container = st.warning
            header_icon = "⚠️"
        else:
            container = st.info
            header_icon = "📌"

        with container(f"{header_icon} {title}"):
            if step_context:
                st.caption(f"来源步骤：{step_context}")

            for i, v in enumerate(display_views, 1):
                self._render_view_streamlit(v, i, len(display_views))

            s = self.stats(views)
            if s["total"] > 1:
                st.caption(
                    f"📊 {s['pending']} 项待证明"
                    + (f"，{s['discharged']} 项已证明" if s["discharged"] else "")
                    + (f"，{s['violated']} 项已违反" if s["violated"] else "")
                )

    def _render_view_streamlit(
        self, view: ObligationView, index: int, total: int,
    ) -> None:
        import streamlit as st

        prefix = f"{view.icon} {index}." if total > 1 else view.icon
        suffix = ""
        if view.is_pending and not view.is_mandatory:
            suffix = f" （{view.severity_label}）"
        if view.is_discharged and view.resolved_by_step:
            suffix += f" ← {view.resolved_by_step}"

        proposition = _strip_dollars(self._fmt.normalize(view.proposition))
        st.markdown(f"{prefix} ${proposition}${suffix}")

        if view.is_pending and self.config.show_explanation and view.explanation:
            if self.config.collapsible_explanations:
                with st.expander("为什么需要？", expanded=False):
                    st.markdown(view.explanation)
                    if view.counter_example and self.config.show_counter_example:
                        st.markdown(f"**反例：** {view.counter_example}")
            else:
                st.caption(f"　　{view.explanation}")

        if view.is_pending and self.config.show_suggested_action and view.suggested_action:
            suggested = _strip_dollars(self._fmt.normalize(view.suggested_action))
            if suggested.startswith("\\") or "_" in suggested or "^" in suggested:
                st.caption(f"　　💡 建议：${suggested}$")
            else:
                st.caption(f"　　💡 建议：{view.suggested_action}")

        if view.is_pending and self.config.show_theorem_reference and view.theorem_reference:
            st.caption(f"　　📖 参考：{view.theorem_reference}")

    # ───────────────────────────────────────────────────────
    # 内部转换
    # ───────────────────────────────────────────────────────

    def _runtime_obligation_to_view(
        self, obl: Any, step_id: str = "",
    ) -> ObligationView:
        """runtime ProofObligation → ObligationView."""
        proposition = getattr(obl, "proposition", "")
        reason = getattr(obl, "reason", "")
        source_step = getattr(obl, "source_step", step_id)
        discharged_by = getattr(obl, "discharged_by", "")

        status = _coerce_status(getattr(obl, "status", None))
        severity = _infer_severity(proposition, reason)

        enriched = self._enrich_with_template(proposition, source_step)

        return ObligationView(
            obligation_id=getattr(obl, "fingerprint", "") or _make_id(proposition, source_step),
            proposition=proposition,
            severity=enriched.severity if enriched else severity,
            status=status,
            generated_by_step=source_step,
            resolved_by_step=discharged_by or None,
            explanation=enriched.explanation if enriched else reason,
            theorem_reference=enriched.theorem_reference if enriched else None,
            suggested_action=enriched.suggested_action if enriched else None,
            counter_example=enriched.counter_example if enriched else None,
        )

    def _dsl_obligation_to_view(self, obl: Any) -> ObligationView:
        """rules/dsl ProofObligation → ObligationView."""
        description = getattr(obl, "description", "")
        severity = _coerce_severity(getattr(obl, "severity", None))
        related_constraint = getattr(obl, "related_constraint", "")
        related_rule = getattr(obl, "related_rule", "")

        return ObligationView(
            obligation_id=_make_id(description, related_rule),
            proposition=description or related_constraint,
            severity=severity,
            status=ObligationStatus.PENDING,
            explanation=f"由规则 {related_rule} 生成" if related_rule else "",
            theorem_reference=related_rule or None,
        )

    def _enrich_with_template(
        self, proposition: str, step_id: str = "",
    ) -> Optional[ObligationView]:
        """尝试用 OBLIGATION_TEMPLATES 丰富义务."""
        normalized = proposition.lower().strip()
        for op_key, templates in OBLIGATION_TEMPLATES.items():
            for tmpl in templates:
                sample = tmpl.proposition_template.lower()
                if _proposition_matches(normalized, sample):
                    return tmpl.instantiate(step_id=step_id)
        return None


# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════

def _parse_severity(val: Any) -> ObligationSeverity:
    if isinstance(val, ObligationSeverity):
        return val
    if isinstance(val, str):
        mapping = {
            "mandatory": ObligationSeverity.MANDATORY,
            "recommended": ObligationSeverity.RECOMMENDED,
            "informational": ObligationSeverity.INFORMATIONAL,
            "MANDATORY": ObligationSeverity.MANDATORY,
            "RECOMMENDED": ObligationSeverity.RECOMMENDED,
            "INFORMATIONAL": ObligationSeverity.INFORMATIONAL,
        }
        return mapping.get(val, ObligationSeverity.MANDATORY)
    return ObligationSeverity.MANDATORY


def _parse_status(val: Any) -> ObligationStatus:
    if isinstance(val, ObligationStatus):
        return val
    if isinstance(val, str):
        mapping = {
            "pending": ObligationStatus.PENDING,
            "discharged": ObligationStatus.DISCHARGED,
            "waived": ObligationStatus.WAIVED,
            "violated": ObligationStatus.VIOLATED,
            "PENDING": ObligationStatus.PENDING,
            "DISCHARGED": ObligationStatus.DISCHARGED,
            "WAIVED": ObligationStatus.WAIVED,
            "VIOLATED": ObligationStatus.VIOLATED,
        }
        return mapping.get(val, ObligationStatus.PENDING)
    return ObligationStatus.PENDING


def _coerce_status(val: Any) -> ObligationStatus:
    if isinstance(val, ObligationStatus):
        return val
    try:
        from runtime.state import ObligationStatus as RuntimeStatus
        if isinstance(val, RuntimeStatus):
            mapping = {
                RuntimeStatus.PENDING: ObligationStatus.PENDING,
                RuntimeStatus.DISCHARGED: ObligationStatus.DISCHARGED,
                RuntimeStatus.WAIVED: ObligationStatus.WAIVED,
                RuntimeStatus.VIOLATED: ObligationStatus.VIOLATED,
            }
            return mapping.get(val, ObligationStatus.PENDING)
    except ImportError:
        pass
    try:
        from runtime.world_state import ObligationStatus as WSStatus
        if isinstance(val, WSStatus):
            mapping = {
                WSStatus.PENDING: ObligationStatus.PENDING,
                WSStatus.DISCHARGED: ObligationStatus.DISCHARGED,
                WSStatus.WAIVED: ObligationStatus.WAIVED,
                WSStatus.VIOLATED: ObligationStatus.VIOLATED,
            }
            return mapping.get(val, ObligationStatus.PENDING)
    except ImportError:
        pass
    return _parse_status(val)


def _coerce_severity(val: Any) -> ObligationSeverity:
    if isinstance(val, ObligationSeverity):
        return val
    try:
        from rules.dsl import ObligationSeverity as DSLSeverity
        if isinstance(val, DSLSeverity):
            mapping = {
                DSLSeverity.MANDATORY: ObligationSeverity.MANDATORY,
                DSLSeverity.RECOMMENDED: ObligationSeverity.RECOMMENDED,
                DSLSeverity.INFORMATIONAL: ObligationSeverity.INFORMATIONAL,
            }
            return mapping.get(val, ObligationSeverity.MANDATORY)
    except ImportError:
        pass
    return _parse_severity(val)


def _infer_severity(proposition: str, reason: str) -> ObligationSeverity:
    text = (proposition + " " + reason).lower()
    if any(kw in text for kw in ["必须", "mandatory", "需验证", "需证明", "不能"]):
        return ObligationSeverity.MANDATORY
    if any(kw in text for kw in ["建议", "推荐", "recommended", "可选"]):
        return ObligationSeverity.RECOMMENDED
    if any(kw in text for kw in ["提醒", "注意", "informational", "信息"]):
        return ObligationSeverity.INFORMATIONAL
    return ObligationSeverity.MANDATORY


def _proposition_matches(normalized: str, template_sample: str) -> bool:
    template_lower = template_sample.lower()
    if normalized == template_lower:
        return True
    if "{factor}" in template_lower:
        pattern = template_lower.replace("{factor}", "").strip()
        if pattern and pattern in normalized:
            return True
    if "{expr}" in template_lower:
        pattern = template_lower.replace("{expr}", "").strip()
        if pattern and pattern in normalized:
            return True
    if "{divisor}" in template_lower:
        pattern = template_lower.replace("{divisor}", "").strip()
        if pattern and pattern in normalized:
            return True
    keywords = [w for w in template_lower.split() if len(w) > 2 and not w.startswith("{")]
    if keywords and all(kw in normalized for kw in keywords):
        return True
    return False


def _make_id(proposition: str, source: str = "") -> str:
    import hashlib
    raw = f"{proposition}::{source}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s
