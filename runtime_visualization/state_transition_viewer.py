"""State Transition Viewer — 状态转移查看器

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  这是整个系统最关键的"调试器"。

  现在: 验证 step (对/错)
  未来: 观察状态如何变化 (S_t → S_{t+1})

  数学推理本质:
    S_t  ──Op──>  S_{t+1}

  你必须能: 可视化状态变化

  没有 Viewer:
    "步骤 3 验证通过"  ← 只知道对错

  有了 Viewer:
    "步骤 3: 约分
     ➕ 约束: x ≠ 0
     ✓ 义务已证: 分母 ≠ 0
     📊 置信度 +0.15"
    ← 知道状态如何变化

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  WorldState[] (状态序列)
      ↓
  StateDiffEngine.diff(before, after)
      ↓
  StateDiff[] (差异序列)
      ↓
  StateTransitionViewer
      ↓
  Streamlit UI / DocumentNode[] / Markdown / HTML

═══════════════════════════════════════════════════════════════
渲染效果
═══════════════════════════════════════════════════════════════

  ┌─ 步骤 3: 约分 ────────────────────────────────────────┐
  │                                                         │
  │ S₂ ──cancel──> S₃                                      │
  │                                                         │
  │ ➕ 约束: x ≠ 0                                          │
  │ ✓ 义务已证: 分母 ≠ 0                                    │
  │ ➕ 事实: x+1 (由约分得到)                                │
  │ 📊 置信度 0.85 → 1.00 (+0.15)                          │
  │                                                         │
  │ 总计: 3 项变化                                          │
  └─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from rendering.document_ast import BlockType, DocumentNode
from rendering.math_formatter import MathFormatter
from runtime_visualization.state_diff import (
    ChangeCategory,
    ChangeDirection,
    ChangeRecord,
    StateDiff,
    StateDiffEngine,
    TransitionRecord,
    TransitionChain,
)


# ═══════════════════════════════════════════════════════════
# Viewer Config
# ═══════════════════════════════════════════════════════════

@dataclass
class TransitionViewerConfig:
    show_constraints: bool = True
    show_facts: bool = True
    show_goals: bool = True
    show_obligations: bool = True
    show_assumptions: bool = True
    show_expressions: bool = True
    show_domains: bool = True
    show_confidence: bool = True
    show_legality: bool = True
    show_fingerprints: bool = False
    show_empty_categories: bool = False
    compact_mode: bool = False
    max_items_per_category: int = 10


# ═══════════════════════════════════════════════════════════
# State Transition Viewer
# ═══════════════════════════════════════════════════════════

class StateTransitionViewer:
    """
    状态转移查看器 — 系统最关键的调试器.

    职责:
      1. 接收 StateDiff / TransitionChain
      2. 渲染为 Streamlit UI / DocumentNode[] / Markdown
      3. 高亮关键变化（新增约束、义务证明、目标达成）
      4. 标记回归（事实失效、约束移除、假设撤销）

    核心价值:
      "观察状态如何变化" — 不只验证对错，更理解过程
    """

    def __init__(self, config: TransitionViewerConfig = None):
        self.config = config or TransitionViewerConfig()
        self._engine = StateDiffEngine()
        self._fmt = MathFormatter()

    # ───────────────────────────────────────────────────────
    # Diff 计算
    # ───────────────────────────────────────────────────────

    def compute_diff(self, before: Any, after: Any) -> StateDiff:
        return self._engine.diff(before, after)

    def build_chain(
        self, states: Sequence[Any], step_ids: Sequence[str] = (),
    ) -> TransitionChain:
        """
        从状态序列构建转移链.

        Args:
            states:   WorldState 序列
            step_ids: 对应的步骤 ID（可选）
        """
        records: list[TransitionRecord] = []
        for i in range(1, len(states)):
            before = states[i - 1]
            after = states[i]
            diff = self._engine.diff(before, after)
            step_id = step_ids[i] if i < len(step_ids) else f"s{i}"
            operation = ""
            if hasattr(after, 'metadata') and hasattr(after.metadata, 'source_operation'):
                operation = after.metadata.source_operation
            records.append(TransitionRecord(
                step_id=step_id,
                operation=operation,
                diff=diff,
                before_fingerprint=before.fingerprint if hasattr(before, 'fingerprint') else "",
                after_fingerprint=after.fingerprint if hasattr(after, 'fingerprint') else "",
            ))
        return TransitionChain(records=records)

    # ───────────────────────────────────────────────────────
    # Streamlit 渲染
    # ───────────────────────────────────────────────────────

    def render_diff_streamlit(
        self, diff: StateDiff, step_id: str = "", operation: str = "",
    ) -> None:
        """
        渲染单个 StateDiff 到 Streamlit.

        效果:
          ┌─ 步骤 3: 约分 ──────────────────────────────┐
          │ ➕ 约束: x ≠ 0                               │
          │ ✓ 义务已证: 分母 ≠ 0                         │
          │ 📊 置信度 +0.15                              │
          └──────────────────────────────────────────────┘
        """
        import streamlit as st

        if diff.is_empty:
            st.info("📭 无状态变化")
            return

        title = self._build_title(step_id, operation)

        sentiment = diff.overall_sentiment
        if sentiment == "progress":
            container = st.success
        elif sentiment == "regression":
            container = st.error
        elif sentiment == "mixed":
            container = st.warning
        else:
            container = st.info

        with container(title):
            self._render_diff_body_streamlit(diff)

    def render_chain_streamlit(self, chain: TransitionChain) -> None:
        """
        渲染完整转移链到 Streamlit.

        每个转移记录渲染为一个可折叠的卡片.
        """
        import streamlit as st

        if chain.is_empty:
            st.info("📭 无状态转移记录")
            return

        st.subheader(f"📊 状态转移链 ({chain.length} 步)")

        for record in chain.records:
            title = self._build_title(record.step_id, record.operation)
            expanded = record.diff.has_regressions or record.diff.has_progress
            with st.expander(title, expanded=expanded):
                self._render_diff_body_streamlit(record.diff)

        self._render_chain_summary_streamlit(chain)

    def _render_diff_body_streamlit(self, diff: StateDiff) -> None:
        import streamlit as st

        cfg = self.config

        if cfg.show_constraints and (diff.added_constraints or diff.removed_constraints or cfg.show_empty_categories):
            self._render_category_streamlit(
                "约束", diff.added_constraints, diff.removed_constraints,
            )

        if cfg.show_facts and (diff.added_facts or diff.invalidated_facts or cfg.show_empty_categories):
            self._render_category_streamlit(
                "事实", diff.added_facts, diff.invalidated_facts,
                added_icon="➕", removed_label="失效",
            )

        if cfg.show_goals and (diff.added_goals or diff.solved_goals or cfg.show_empty_categories):
            self._render_category_streamlit(
                "目标", diff.added_goals, diff.solved_goals,
                added_icon="🎯", removed_icon="✅", removed_label="达成",
            )

        if cfg.show_obligations and (diff.added_obligations or diff.discharged_obligations or cfg.show_empty_categories):
            self._render_category_streamlit(
                "义务", diff.added_obligations, diff.discharged_obligations,
                added_icon="📋", removed_icon="✅", removed_label="已证明",
            )

        if cfg.show_assumptions and (diff.added_assumptions or diff.retracted_assumptions or cfg.show_empty_categories):
            self._render_category_streamlit(
                "假设", diff.added_assumptions, diff.retracted_assumptions,
            )

        if cfg.show_expressions and (diff.added_expressions or cfg.show_empty_categories):
            for expr in diff.added_expressions[:cfg.max_items_per_category]:
                expr_clean = _strip_dollars(expr)
                st.markdown(f"📝 新增表达式: ${expr_clean}$")

        if cfg.show_domains and (diff.added_domains or cfg.show_empty_categories):
            for d in diff.added_domains:
                st.markdown(f"🌐 新增定义域: {d}")

        if cfg.show_legality and diff.legality_change is not None:
            if "合法" in diff.legality_change and "非" not in diff.legality_change:
                st.markdown(f"⚖️ 合法性: → {diff.legality_change}")
            else:
                st.markdown(f"⚠️ 合法性: → {diff.legality_change}")

        if cfg.show_confidence and abs(diff.confidence_delta) > 1e-9:
            sign = "+" if diff.confidence_delta > 0 else ""
            icon = "📈" if diff.confidence_delta > 0 else "📉"
            st.markdown(f"{icon} 置信度: {sign}{diff.confidence_delta:.2f}")

        if cfg.show_fingerprints and diff.before_fingerprint and diff.after_fingerprint:
            st.caption(f"指纹: {diff.before_fingerprint[:8]} → {diff.after_fingerprint[:8]}")

        if diff.total_changes > 0:
            st.caption(f"总计: {diff.total_changes} 项变化")

    def _render_category_streamlit(
        self,
        label: str,
        added: list[str],
        removed: list[str],
        added_icon: str = "➕",
        removed_icon: str = "➖",
        removed_label: str = "移除",
    ) -> None:
        import streamlit as st

        for item in added[:self.config.max_items_per_category]:
            item_clean = _strip_dollars(item)
            if _is_math_expr(item_clean):
                st.markdown(f"{added_icon} {label}: ${item_clean}$")
            else:
                st.markdown(f"{added_icon} {label}: {item}")

        for item in removed[:self.config.max_items_per_category]:
            item_clean = _strip_dollars(item)
            if _is_math_expr(item_clean):
                st.markdown(f"{removed_icon} {label}{removed_label}: ${item_clean}$")
            else:
                st.markdown(f"{removed_icon} {label}{removed_label}: {item}")

    def _render_chain_summary_streamlit(self, chain: TransitionChain) -> None:
        import streamlit as st

        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总步骤", chain.length)
        with col2:
            st.metric("总变化", chain.total_changes)
        with col3:
            st.metric("义务已证", len(chain.all_discharged_obligations))
        with col4:
            st.metric("目标达成", len(chain.all_solved_goals))

        regressions = chain.all_regressions
        if regressions:
            st.warning(f"⚠️ {len(regressions)} 步存在回归")

    # ───────────────────────────────────────────────────────
    # DocumentNode[] 渲染（供 Exporter 使用）
    # ───────────────────────────────────────────────────────

    def render_diff_nodes(
        self, diff: StateDiff, step_id: str = "", operation: str = "",
    ) -> list[DocumentNode]:
        """将 StateDiff 转为 DocumentNode[] 供导出."""
        nodes: list[DocumentNode] = []

        title = self._build_title(step_id, operation)
        nodes.append(DocumentNode(
            type=BlockType.TITLE,
            content=title,
        ))

        cfg = self.config

        if cfg.show_constraints:
            for c in diff.added_constraints:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"➕ 约束: {c}",
                ))
            for c in diff.removed_constraints:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"➖ 约束移除: {c}",
                ))

        if cfg.show_facts:
            for f in diff.added_facts:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"➕ 事实: {f}",
                ))
            for f in diff.invalidated_facts:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"⚠️ 事实失效: {f}",
                ))

        if cfg.show_goals:
            for g in diff.added_goals:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"🎯 新增目标: {g}",
                ))
            for g in diff.solved_goals:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"✅ 目标达成: {g}",
                ))

        if cfg.show_obligations:
            for o in diff.added_obligations:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"📋 新增义务: {o}",
                ))
            for o in diff.discharged_obligations:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"✅ 义务已证: {o}",
                ))

        if cfg.show_assumptions:
            for a in diff.added_assumptions:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"➕ 假设: {a}",
                ))
            for a in diff.retracted_assumptions:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"➖ 假设撤销: {a}",
                ))

        if cfg.show_expressions:
            for e in diff.added_expressions:
                nodes.append(DocumentNode(
                    type=BlockType.DISPLAY_MATH,
                    content=e,
                ))

        if cfg.show_domains:
            for d in diff.added_domains:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"🌐 定义域: {d}",
                ))

        if cfg.show_legality and diff.legality_change is not None:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"⚖️ 合法性: → {diff.legality_change}",
            ))

        if cfg.show_confidence and abs(diff.confidence_delta) > 1e-9:
            sign = "+" if diff.confidence_delta > 0 else ""
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"📊 置信度: {sign}{diff.confidence_delta:.2f}",
            ))

        nodes.append(DocumentNode(
            type=BlockType.PARAGRAPH,
            content=f"总计: {diff.total_changes} 项变化 | {diff.summary}",
        ))

        return nodes

    def render_chain_nodes(self, chain: TransitionChain) -> list[DocumentNode]:
        """将 TransitionChain 转为 DocumentNode[] 供导出."""
        nodes: list[DocumentNode] = []

        nodes.append(DocumentNode(
            type=BlockType.TITLE,
            content=f"状态转移链 ({chain.length} 步)",
        ))

        for record in chain.records:
            nodes.extend(self.render_diff_nodes(
                record.diff, record.step_id, record.operation,
            ))
            nodes.append(DocumentNode(
                type=BlockType.DIVIDER,
                content="---",
            ))

        nodes.append(DocumentNode(
            type=BlockType.TITLE,
            content="总结",
        ))
        nodes.append(DocumentNode(
            type=BlockType.PARAGRAPH,
            content=f"总步骤: {chain.length}，总变化: {chain.total_changes}",
        ))
        nodes.append(DocumentNode(
            type=BlockType.PARAGRAPH,
            content=f"义务已证: {len(chain.all_discharged_obligations)}，目标达成: {len(chain.all_solved_goals)}",
        ))
        if chain.all_regressions:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"⚠️ {len(chain.all_regressions)} 步存在回归",
            ))

        return nodes

    # ───────────────────────────────────────────────────────
    # 内部辅助
    # ───────────────────────────────────────────────────────

    @staticmethod
    def _build_title(step_id: str, operation: str) -> str:
        parts: list[str] = []
        if step_id:
            parts.append(f"步骤 {step_id}")
        if operation:
            op_display = _OPERATION_LABELS.get(operation, operation)
            parts.append(op_display)
        if not parts:
            return "状态转移"
        return ": ".join(parts)


_OPERATION_LABELS: dict[str, str] = {
    "add_constraint": "添加约束",
    "add_expression": "添加表达式",
    "add_assumption": "引入假设",
    "add_goal": "设定目标",
    "add_obligation": "生成义务",
    "derive_fact": "推导事实",
    "discharge_obligation": "证明义务",
    "retract_assumption": "撤销假设",
    "set_domain": "设定定义域",
    "update_goal": "更新目标",
    "update_proof_context": "更新证明上下文",
    "update_scope": "更新作用域",
    "propagate_constraints": "约束传播",
    "cascade_invalidate": "级联失效",
    "cancel": "约分",
    "simplify": "化简",
    "expand": "展开",
    "factor": "因式分解",
    "differentiate": "求导",
    "integrate": "积分",
    "substitute": "换元",
    "lhopital": "洛必达法则",
    "row_reduce": "初等行变换",
    "solve_equation": "解方程",
    "solve_system": "解方程组",
    "solve_inequality": "解不等式",
    "apply_theorem": "应用定理",
    "classify": "分类讨论",
    "induction_step": "归纳步骤",
    "contradiction": "反证法",
    "compute_limit": "求极限",
    "compute": "计算",
}


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s


def _is_math_expr(s: str) -> bool:
    math_indicators = ["\\", "^", "_", "{", "}", "frac", "sqrt", "sum", "int", "alpha", "beta", "gamma", "neq", "leq", "geq", "cdot", "times", "pm", "infty"]
    return any(ind in s for ind in math_indicators)
