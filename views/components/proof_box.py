"""ProofBox — 证明义务可视化组件

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  render_obligation(obligations)         → 多种输入 → 证明义务框
  render_obligation_dict(data)           → dict → 证明义务框
  render_proof_block(proof_block)        → ProofBlock → 证明义务框
  render_obligation_panel(views, ...)    → ObligationView[] → 教学面板

═══════════════════════════════════════════════════════════════
渲染效果
═══════════════════════════════════════════════════════════════

  基础模式 (render_obligation):
  ┌─────────────────────────────────────────┐
  │ 📌 需要额外证明：                       │
  │                                         │
  │ 🔴 1. x ≠ 0                            │
  │        原因：约分时约去的因子           │
  │                                         │
  │ 🟡 2. 换元函数单调 （建议证明）         │
  │                                         │
  │ 📊 2 项待证明                           │
  └─────────────────────────────────────────┘

  教学面板模式 (render_obligation_panel):
  ┌─────────────────────────────────────────┐
  │ ⚠ 需要证明                              │
  │                                         │
  │ 🔴 1. x - 1 ≠ 0     ❌ 未证明          │
  │                                         │
  │ ▸ 为什么需要？                          │
  │   约去因子 x-1 时，必须保证 x-1 ≠ 0   │
  │   若 x=1，原式无定义。                  │
  │                                         │
  │ 💡 建议：添加条件 x ≠ 1                 │
  │                                         │
  │ 📊 1 项待证明                           │
  └─────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import streamlit as st

from rendering.document_ast import StepBlock, ProofBlock
from rendering.obligation_renderer import (
    ObligationRenderer,
    ObligationRendererConfig,
    VisualObligation,
    ObligationItem,
    ObligationStatus,
    ObligationSeverity,
)
from rendering.math_formatter import MathFormatter
from runtime_visualization.obligation_panel import (
    ObligationView,
    ObligationPanel,
    ObligationPanelConfig,
)


_fmt = MathFormatter()
_renderer = ObligationRenderer()


def render_obligation(
    obligations: Any,
    title: str = "需要额外证明",
    step_id: str = "",
) -> None:
    """
    渲染证明义务.

    支持多种输入:
      - list[str] → 字符串列表
      - list[dict] → dict 列表
      - VisualObligation → 直接渲染
      - StepBlock → 从 proof_obligations 提取
      - ProofBlock → 从 obligations + discharged 提取
      - dict → 通过 ObligationRenderer.visualize_dict 处理
    """
    if isinstance(obligations, VisualObligation):
        _render_visual_obligation(obligations)
    elif isinstance(obligations, StepBlock):
        vo = _renderer.visualize_step_block(obligations)
        _render_visual_obligation(vo)
    elif isinstance(obligations, ProofBlock):
        vo = _renderer.visualize_proof_block(obligations)
        _render_visual_obligation(vo)
    elif isinstance(obligations, dict):
        vo = _renderer.visualize_dict(obligations)
        _render_visual_obligation(vo)
    elif isinstance(obligations, (list, tuple)):
        vo = _renderer.visualize_obligations(obligations, title, step_id)
        _render_visual_obligation(vo)
    else:
        st.info(f"📋 {str(obligations)}")


def render_obligation_dict(data: dict) -> None:
    """dict → 证明义务框."""
    render_obligation(data)


def render_proof_block(proof: ProofBlock) -> None:
    """ProofBlock → 证明义务框."""
    render_obligation(proof)


# ═══════════════════════════════════════════════════════════
# Internal
# ═══════════════════════════════════════════════════════════

def _render_visual_obligation(vo: VisualObligation) -> None:
    if not vo.items:
        return

    has_pending = vo.has_pending
    has_mandatory = vo.has_mandatory_pending

    if has_mandatory:
        container = st.warning
    elif has_pending:
        container = st.info
    else:
        container = st.success

    with container(f"{vo.icon} {vo.title}"):
        for i, item in enumerate(vo.items, 1):
            _render_obligation_item(item, i, len(vo.items))

        if len(vo.items) > 1:
            st.caption(f"📊 {vo.summary}")


def _render_obligation_item(item: ObligationItem, index: int, total: int) -> None:
    prefix_parts = []
    if item.is_pending:
        prefix_parts.append(item.icon)
    elif item.is_discharged:
        prefix_parts.append("✅")
    elif item.status == ObligationStatus.WAIVED:
        prefix_parts.append("⏭️")
    elif item.status == ObligationStatus.VIOLATED:
        prefix_parts.append("❌")

    if total > 1:
        prefix_parts.append(f"{index}.")

    prefix = " ".join(prefix_parts)
    if prefix:
        prefix += " "

    suffix = ""
    if item.is_pending and item.severity != ObligationSeverity.MANDATORY:
        suffix = f" （{item.severity_label}）"
    if item.is_discharged and item.discharged_by:
        suffix += f" ← {item.discharged_by}"

    proposition = _strip_dollars(_fmt.normalize(item.proposition))

    line = f"{prefix}${proposition}${suffix}"
    st.markdown(line)

    if item.reason and item.is_pending:
        st.caption(f"　　原因：{item.reason}")


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s


# ═══════════════════════════════════════════════════════════
# 教学面板模式
# ═══════════════════════════════════════════════════════════

_panel = ObligationPanel()


def render_obligation_panel(
    views: list[ObligationView],
    title: str = "需要证明",
    step_context: str = "",
    show_explanation: bool = True,
    show_suggested_action: bool = True,
    show_counter_example: bool = True,
    show_theorem_reference: bool = True,
    collapsible_explanations: bool = True,
    show_discharged: bool = False,
) -> None:
    """
    渲染证明义务教学面板.

    与 render_obligation 的区别:
      - 输入是 ObligationView[]（携带"为什么需要"等丰富信息）
      - 提供"为什么需要？"折叠解释
      - 提供"建议补充"行动指引
      - 提供反例说明
      - 提供定理引用

    这是"数学导师"模式的核心 UI:
      不只告诉学生"你漏了证明"
      还告诉学生"为什么需要"和"怎么补"

    Args:
        views:                      ObligationView 列表
        title:                      面板标题
        step_context:               来源步骤描述
        show_explanation:           是否显示"为什么需要"
        show_suggested_action:      是否显示"建议补充"
        show_counter_example:       是否显示反例
        show_theorem_reference:     是否显示定理引用
        collapsible_explanations:   解释是否可折叠
        show_discharged:            是否显示已证明项
    """
    config = ObligationPanelConfig(
        show_explanation=show_explanation,
        show_suggested_action=show_suggested_action,
        show_counter_example=show_counter_example,
        show_theorem_reference=show_theorem_reference,
        collapsible_explanations=collapsible_explanations,
        show_discharged=show_discharged,
    )
    panel = ObligationPanel(config)
    panel.render_streamlit(views, title=title, step_context=step_context)
