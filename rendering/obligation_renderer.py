"""
Obligation Renderer — 证明义务可视化

═══════════════════════════════════════════════════════════════
核心问题
═══════════════════════════════════════════════════════════════

  现在:
    📋 x ≠ 0

  未来:
    📌 需要额外证明：

    1. x ≠ 0
    2. 换元函数单调
    3. 极限满足洛必达条件

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  ProofObligation (rules/dsl.py)
  ProofObligation (runtime/state.py)
  StepBlock.proof_obligations
  ProofBlock.obligations / .discharged
  dict
      ↓
  ObligationRenderer
      ↓
  VisualObligation
    ├── icon          — 📌 / ✅ / ⚠️
    ├── title         — "需要额外证明"
    ├── items         — [ObligationItem, ...]
    │     ├── proposition   — "x ≠ 0"
    │     ├── status        — pending / discharged / waived / violated
    │     ├── severity      — mandatory / recommended / informational
    │     └── reason        — "约分时约去的因子"
    └── summary       — "3 项待证明"

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence

from rendering.document_ast import (
    BlockType,
    DocumentNode,
    StepBlock,
    ProofBlock,
)


# ═══════════════════════════════════════════════════════════
# Obligation Visualization Data Structures
# ═══════════════════════════════════════════════════════════

class ObligationStatus(Enum):
    PENDING = "pending"
    DISCHARGED = "discharged"
    WAIVED = "waived"
    VIOLATED = "violated"


class ObligationSeverity(Enum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class ObligationItem:
    """
    单条证明义务.

    proposition:  需要证明的命题（LaTeX）
    status:       当前状态
    severity:     严重度
    reason:       产生原因
    source_step:  来源步骤
    discharged_by: 由哪个步骤证明
    """
    proposition: str = ""
    status: ObligationStatus = ObligationStatus.PENDING
    severity: ObligationSeverity = ObligationSeverity.MANDATORY
    reason: str = ""
    source_step: str = ""
    discharged_by: str = ""

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
            ObligationStatus.PENDING: "待证明",
            ObligationStatus.DISCHARGED: "已证明",
            ObligationStatus.WAIVED: "已跳过",
            ObligationStatus.VIOLATED: "已违反",
        }[self.status]

    def to_dict(self) -> dict:
        d = {
            "proposition": self.proposition,
            "status": self.status.value,
            "severity": self.severity.value,
        }
        if self.reason:
            d["reason"] = self.reason
        if self.source_step:
            d["source_step"] = self.source_step
        if self.discharged_by:
            d["discharged_by"] = self.discharged_by
        return d


@dataclass
class VisualObligation:
    """
    可视化证明义务组 — 一组待证明/已证明的命题.

    对应用户看到的:
      📌 需要额外证明：

      1. x ≠ 0
      2. 换元函数单调
      3. 极限满足洛必达条件
    """
    icon: str = "📌"
    title: str = "需要额外证明"
    items: list[ObligationItem] = field(default_factory=list)
    source_step_id: str = ""

    @property
    def pending_items(self) -> list[ObligationItem]:
        return [it for it in self.items if it.is_pending]

    @property
    def discharged_items(self) -> list[ObligationItem]:
        return [it for it in self.items if it.is_discharged]

    @property
    def has_pending(self) -> bool:
        return any(it.is_pending for it in self.items)

    @property
    def has_mandatory_pending(self) -> bool:
        return any(it.is_pending and it.is_mandatory for it in self.items)

    @property
    def summary(self) -> str:
        pending = len(self.pending_items)
        discharged = len(self.discharged_items)
        total = len(self.items)
        if total == 0:
            return "无待证明项"
        if pending == 0:
            return f"全部 {total} 项已证明"
        if discharged == 0:
            return f"{pending} 项待证明"
        return f"{pending} 项待证明，{discharged} 项已证明"

    def to_dict(self) -> dict:
        return {
            "icon": self.icon,
            "title": self.title,
            "items": [it.to_dict() for it in self.items],
            "summary": self.summary,
            "source_step_id": self.source_step_id,
        }


# ═══════════════════════════════════════════════════════════
# Obligation Renderer
# ═══════════════════════════════════════════════════════════

@dataclass
class ObligationRendererConfig:
    show_title: bool = True
    show_reason: bool = True
    show_severity: bool = True
    show_discharged: bool = False
    show_summary: bool = True
    number_items: bool = True
    math_mode: str = "display"


_STATUS_MAP = {
    "PENDING": ObligationStatus.PENDING,
    "DISCHARGED": ObligationStatus.DISCHARGED,
    "WAIVED": ObligationStatus.WAIVED,
    "VIOLATED": ObligationStatus.VIOLATED,
    "pending": ObligationStatus.PENDING,
    "discharged": ObligationStatus.DISCHARGED,
    "waived": ObligationStatus.WAIVED,
    "violated": ObligationStatus.VIOLATED,
}

_SEVERITY_MAP = {
    "MANDATORY": ObligationSeverity.MANDATORY,
    "RECOMMENDED": ObligationSeverity.RECOMMENDED,
    "INFORMATIONAL": ObligationSeverity.INFORMATIONAL,
    "mandatory": ObligationSeverity.MANDATORY,
    "recommended": ObligationSeverity.RECOMMENDED,
    "informational": ObligationSeverity.INFORMATIONAL,
}


class ObligationRenderer:
    """
    证明义务渲染器 — 将 ProofObligation 转为可视化 DocumentNode[].

    核心能力:
      1. rules/dsl ProofObligation → VisualObligation → DocumentNode[]
      2. runtime/state ProofObligation → VisualObligation → DocumentNode[]
      3. StepBlock.proof_obligations → VisualObligation → DocumentNode[]
      4. ProofBlock → VisualObligation → DocumentNode[]
      5. dict → VisualObligation → DocumentNode[]
    """

    def __init__(self, config: ObligationRendererConfig = None):
        self.config = config or ObligationRendererConfig()

    def _parse_status(self, status: Any) -> ObligationStatus:
        if isinstance(status, ObligationStatus):
            return status
        if hasattr(status, "name"):
            return _STATUS_MAP.get(status.name, ObligationStatus.PENDING)
        return _STATUS_MAP.get(str(status), ObligationStatus.PENDING)

    def _parse_severity(self, severity: Any) -> ObligationSeverity:
        if isinstance(severity, ObligationSeverity):
            return severity
        if hasattr(severity, "name"):
            return _SEVERITY_MAP.get(severity.name, ObligationSeverity.MANDATORY)
        return _SEVERITY_MAP.get(str(severity), ObligationSeverity.MANDATORY)

    def visualize_dsl_obligation(self, obl: Any) -> ObligationItem:
        """rules/dsl ProofObligation → ObligationItem"""
        return ObligationItem(
            proposition=getattr(obl, "description", str(obl)),
            severity=self._parse_severity(getattr(obl, "severity", "mandatory")),
            reason=getattr(obl, "related_constraint", ""),
            source_step=getattr(obl, "related_rule", ""),
        )

    def visualize_state_obligation(self, obl: Any) -> ObligationItem:
        """runtime/state ProofObligation → ObligationItem"""
        return ObligationItem(
            proposition=getattr(obl, "proposition", str(obl)),
            status=self._parse_status(getattr(obl, "status", "PENDING")),
            reason=getattr(obl, "reason", ""),
            source_step=getattr(obl, "source_step", ""),
            discharged_by=getattr(obl, "discharged_by", ""),
        )

    def visualize_step_block(self, step: StepBlock) -> VisualObligation:
        """StepBlock.proof_obligations → VisualObligation"""
        items = []
        for obl_str in step.proof_obligations:
            items.append(ObligationItem(
                proposition=obl_str,
                severity=ObligationSeverity.MANDATORY,
                source_step=step.step_id,
            ))
        return VisualObligation(
            icon="📌",
            title="需要额外证明",
            items=items,
            source_step_id=step.step_id,
        )

    def visualize_proof_block(self, proof: ProofBlock) -> VisualObligation:
        """ProofBlock → VisualObligation"""
        items = []
        for obl_str in proof.obligations:
            is_discharged = obl_str in proof.discharged
            items.append(ObligationItem(
                proposition=obl_str,
                status=ObligationStatus.DISCHARGED if is_discharged else ObligationStatus.PENDING,
                severity=ObligationSeverity.MANDATORY,
            ))
        return VisualObligation(
            icon="📌",
            title="证明义务",
            items=items,
        )

    def visualize_dict(self, data: dict) -> VisualObligation:
        """dict → VisualObligation"""
        title = data.get("title", "需要额外证明")
        raw_items = data.get("items", data.get("obligations", []))
        step_id = data.get("step_id", data.get("source_step", ""))

        items = []
        for raw in raw_items:
            if isinstance(raw, str):
                items.append(ObligationItem(
                    proposition=raw,
                    severity=ObligationSeverity.MANDATORY,
                    source_step=step_id,
                ))
            elif isinstance(raw, dict):
                items.append(ObligationItem(
                    proposition=raw.get("proposition", raw.get("description", "")),
                    status=self._parse_status(raw.get("status", "pending")),
                    severity=self._parse_severity(raw.get("severity", "mandatory")),
                    reason=raw.get("reason", ""),
                    source_step=raw.get("source_step", step_id),
                    discharged_by=raw.get("discharged_by", ""),
                ))

        return VisualObligation(
            icon="📌",
            title=title,
            items=items,
            source_step_id=step_id,
        )

    def visualize_obligations(
        self, obligations: Sequence[Any], title: str = "需要额外证明", step_id: str = ""
    ) -> VisualObligation:
        """通用入口 — 自动识别类型"""
        items = []
        for obl in obligations:
            if isinstance(obl, ObligationItem):
                items.append(obl)
            elif isinstance(obl, str):
                items.append(ObligationItem(
                    proposition=obl,
                    source_step=step_id,
                ))
            elif isinstance(obl, dict):
                vo = self.visualize_dict({"items": [obl]})
                items.extend(vo.items)
            elif hasattr(obl, "proposition"):
                items.append(self.visualize_state_obligation(obl))
            elif hasattr(obl, "description") and hasattr(obl, "severity"):
                items.append(self.visualize_dsl_obligation(obl))
            else:
                items.append(ObligationItem(proposition=str(obl)))

        return VisualObligation(
            icon="📌",
            title=title,
            items=items,
            source_step_id=step_id,
        )

    def render_visual_obligation(self, vo: VisualObligation) -> list[DocumentNode]:
        """VisualObligation → DocumentNode[]"""
        nodes = []
        cfg = self.config

        if cfg.show_title:
            nodes.append(DocumentNode(
                type=BlockType.OBLIGATION,
                content=f"{vo.icon} {vo.title}：",
                metadata={"role": "obligation_header"},
            ))

        display_items = vo.items if cfg.show_discharged else vo.pending_items

        for i, item in enumerate(display_items, 1):
            prefix_parts = []
            if item.is_pending:
                prefix_parts.append(item.icon)
            elif item.is_discharged:
                prefix_parts.append("✅")
            if cfg.number_items and len(display_items) > 1:
                prefix_parts.append(f"{i}.")

            suffix_parts = []
            if cfg.show_severity and item.is_pending and item.severity != ObligationSeverity.MANDATORY:
                suffix_parts.append(f"（{item.severity_label}）")
            if item.is_discharged and item.discharged_by:
                suffix_parts.append(f"← {item.discharged_by}")

            prefix_str = " ".join(prefix_parts)
            suffix_str = " ".join(suffix_parts)

            line = f"{prefix_str} ${item.proposition}$"
            if suffix_str:
                line += f" {suffix_str}"

            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=line,
                metadata={
                    "role": "obligation_item",
                    "index": i,
                    "status": item.status.value,
                    "severity": item.severity.value,
                },
            ))

            if cfg.show_reason and item.reason and item.is_pending:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"　　原因：{item.reason}",
                    metadata={"role": "obligation_reason", "index": i},
                ))

        if cfg.show_summary and len(vo.items) > 1:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"📊 {vo.summary}",
                metadata={"role": "obligation_summary"},
            ))

        return nodes

    def render_step_obligations(self, step: StepBlock) -> list[DocumentNode]:
        """StepBlock → DocumentNode[] (一步完成)"""
        if not step.proof_obligations:
            return []
        vo = self.visualize_step_block(step)
        return self.render_visual_obligation(vo)

    def render_proof_block(self, proof: ProofBlock) -> list[DocumentNode]:
        """ProofBlock → DocumentNode[] (一步完成)"""
        if not proof.obligations:
            return []
        vo = self.visualize_proof_block(proof)
        return self.render_visual_obligation(vo)

    def render_dict_obligations(self, data: dict) -> list[DocumentNode]:
        """dict → DocumentNode[] (一步完成)"""
        vo = self.visualize_dict(data)
        if not vo.items:
            return []
        return self.render_visual_obligation(vo)

    def render_obligations(
        self, obligations: Sequence[Any], title: str = "需要额外证明", step_id: str = ""
    ) -> list[DocumentNode]:
        """通用入口 → DocumentNode[] (一步完成)"""
        vo = self.visualize_obligations(obligations, title, step_id)
        if not vo.items:
            return []
        return self.render_visual_obligation(vo)


# ═══════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════

_default_renderer = ObligationRenderer()


def visualize_obligations(
    obligations: Sequence[Any], title: str = "需要额外证明", step_id: str = ""
) -> VisualObligation:
    return _default_renderer.visualize_obligations(obligations, title, step_id)


def visualize_dict(data: dict) -> VisualObligation:
    return _default_renderer.visualize_dict(data)


def render_obligations(
    obligations: Sequence[Any], title: str = "需要额外证明", step_id: str = ""
) -> list[DocumentNode]:
    return _default_renderer.render_obligations(obligations, title, step_id)


def render_dict_obligations(data: dict) -> list[DocumentNode]:
    return _default_renderer.render_dict_obligations(data)


def render_step_obligations(step: StepBlock) -> list[DocumentNode]:
    return _default_renderer.render_step_obligations(step)


def render_proof_block(proof: ProofBlock) -> list[DocumentNode]:
    return _default_renderer.render_proof_block(proof)
