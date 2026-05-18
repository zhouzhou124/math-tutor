import streamlit as st
from typing import Optional, Callable
from rendering.reasoning_trace_to_ir import ReasoningTraceToIRConverter
from rendering.render_ir import RenderTree, RenderNode, RenderType


class ProofReplayRenderer:
    """
    交互式证明回放渲染器。

    功能：
      - 按 topological_order 线性回放推理步骤
      - 点击步骤高亮其依赖
      - 显示当前状态 vs 目标状态
      - 支持暂停/继续/跳转

    架构位置：
      ReasoningTrace (Semantic Graph)
          ↓
      ReasoningTraceToIRConverter
          ↓
      RenderTree (linear view)
          ↓
      ProofReplayRenderer (交互式渲染)

    使用方式：
      renderer = ProofReplayRenderer()
      renderer.render(trace)
    """

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._converter = ReasoningTraceToIRConverter()
        self._session_key = self._config.get("session_key", "proof_replay_state")

    def render(self, trace, expanded: bool = False) -> None:
        """
        渲染交互式证明回放。

        Args:
            trace: ReasoningTrace 对象
            expanded: 是否默认展开所有步骤
        """
        if not trace or not trace.steps:
            st.info("暂无推理轨迹")
            return

        st.subheader("📜 证明回放")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            current_idx = st.selectbox(
                "当前步骤",
                options=range(len(trace.steps)),
                format_func=lambda i: f"步骤 {i+1}: {trace.steps[i].label or trace.steps[i].step_id}",
                key=f"{self._session_key}_step"
            )

        with col2:
            view_mode = st.radio(
                "视图模式",
                options=["linear", "dag", "state_transition"],
                format_func=lambda m: {"linear": "📜 线性", "dag": "🔀 DAG", "state_transition": "🔄 状态"}[m],
                horizontal=True,
                key=f"{self._session_key}_view"
            )

        with col3:
            show_deps = st.checkbox("显示依赖", value=True, key=f"{self._session_key}_deps")

        self._render_replay_content(trace, current_idx, view_mode, show_deps)

    def _render_replay_content(self, trace, current_idx: int, view_mode: str, show_deps: bool) -> None:
        """
        渲染回放内容。
        """
        tree = self._converter.convert(trace, view_mode=view_mode)

        if view_mode == "linear":
            self._render_linear_replay(trace, current_idx, show_deps)
        elif view_mode == "dag":
            self._render_dag_replay(trace, current_idx, show_deps)
        elif view_mode == "state_transition":
            self._render_state_replay(trace, current_idx)

    def _render_linear_replay(self, trace, current_idx: int, show_deps: bool) -> None:
        """
        线性回放：按顺序显示步骤，可交互选择当前步骤。
        """
        order = trace.topological_order()

        with st.container(border=True):
            st.markdown("### 推理链")

            for i, step_id in enumerate(order):
                step = trace.get_step(step_id)
                if not step:
                    continue

                is_current = (i == current_idx)
                is_past = (i < current_idx)
                is_future = (i > current_idx)

                self._render_step_card(
                    step, trace, i,
                    is_current=is_current,
                    is_past=is_past,
                    is_future=is_future,
                    show_deps=show_deps
                )

                if i < len(order) - 1:
                    st.markdown("---")

    def _render_step_card(self, step, trace, index: int,
                          is_current: bool, is_past: bool, is_future: bool,
                          show_deps: bool) -> None:
        """
        渲染单个步骤卡片。
        """
        dependencies = trace.get_dependencies(step.step_id)

        header_color = "blue" if is_current else ("green" if is_past else "gray")
        header_icon = "▶️" if is_current else ("✅" if is_past else "⏳")

        title = f"{header_icon} 步骤 {index + 1}"
        if step.label:
            title += f": {step.label}"
        elif hasattr(step.operation, 'display_name') and step.operation.display_name:
            title += f" ({step.operation.display_name})"

        with st.container(border=True):
            if is_current:
                st.markdown(f"**{title}** 👈")
            else:
                st.markdown(f"**{title}**")

            col1, col2 = st.columns([3, 1])

            with col1:
                output_latex = ""
                if hasattr(step.operation, 'output_state') and step.operation.output_state:
                    for expr in step.operation.output_state.expressions:
                        if expr and hasattr(expr, 'latex') and expr.latex:
                            output_latex = expr.latex
                            break

                if output_latex:
                    st.latex(output_latex)
                elif step.content:
                    st.markdown(step.content)

            with col2:
                legality = "unknown"
                if hasattr(step.operation, 'legality') and step.operation.legality:
                    legality = step.operation.legality.value

                legality_icons = {
                    "valid": "✅",
                    "suspect": "⚠️",
                    "invalid": "❌",
                    "unknown": "❓"
                }
                st.caption(f"状态: {legality_icons.get(legality, '❓')} {legality}")

            if show_deps and dependencies:
                deps_str = ", ".join(dependencies)
                st.caption(f"🔗 依赖: {deps_str}")

            if show_deps and is_current and dependencies:
                st.markdown("**依赖步骤:**")
                for dep_id in dependencies:
                    dep_step = trace.get_step(dep_id)
                    if dep_step:
                        dep_latex = ""
                        if hasattr(dep_step.operation, 'output_state') and dep_step.operation.output_state:
                            for expr in dep_step.operation.output_state.expressions:
                                if expr and hasattr(expr, 'latex') and expr.latex:
                                    dep_latex = expr.latex
                                    break
                        if dep_latex:
                            st.latex(dep_latex)
                        else:
                            st.caption(f"  {dep_step.label or dep_step.step_id}")

            theorem = ""
            if hasattr(step.operation, 'theorem') and step.operation.theorem:
                theorem = step.operation.theorem

            if theorem:
                st.caption(f"📖 定理: *{theorem}*")

            if step.error and step.error.is_error:
                severity = step.error.severity.value if hasattr(step.error, 'severity') else "error"
                desc = step.error.description if hasattr(step.error, 'description') else "错误"
                st.error(f"{severity}: {desc}")

    def _render_dag_replay(self, trace, current_idx: int, show_deps: bool) -> None:
        """
        DAG 回放：显示依赖图结构。
        """
        order = trace.topological_order()
        if current_idx >= len(order):
            current_idx = len(order) - 1

        current_step_id = order[current_idx] if order else None

        with st.container(border=True):
            st.markdown("### 🔀 推理 DAG")

            cols = st.columns(len(order))

            for i, (col, step_id) in enumerate(zip(cols, order)):
                step = trace.get_step(step_id)
                if not step:
                    continue

                with col:
                    is_current = (step_id == current_step_id)
                    is_past = (i < current_idx)

                    border_color = "green" if is_current else ("blue" if is_past else "gray")

                    output_latex = ""
                    if hasattr(step.operation, 'output_state') and step.operation.output_state:
                        for expr in step.operation.output_state.expressions:
                            if expr and hasattr(expr, 'latex') and expr.latex:
                                output_latex = expr.latex
                                break

                    if is_current:
                        st.markdown(f"**▶️ {step_id}**")
                    else:
                        st.markdown(f"**{step_id}**")

                    if output_latex:
                        st.latex(output_latex)
                    else:
                        st.caption(step.label or "")

                    dependencies = trace.get_dependencies(step_id)
                    if dependencies:
                        st.caption(f"↓ from {', '.join(dependencies)}")

            dependents_map = {}
            for step_id in order:
                deps = trace.get_dependencies(step_id)
                for dep in deps:
                    if dep not in dependents_map:
                        dependents_map[dep] = []
                    dependents_map[dep].append(step_id)

            if show_deps and current_step_id:
                current_deps = trace.get_dependencies(current_step_id)
                current_dependents = dependents_map.get(current_step_id, [])

                st.markdown("---")
                st.markdown(f"**当前步骤 {current_step_id} 的依赖图:**")

                if current_deps:
                    st.markdown("⬆️ 依赖:")
                    for dep_id in current_deps:
                        dep_step = trace.get_step(dep_id)
                        if dep_step:
                            dep_latex = ""
                            if hasattr(dep_step.operation, 'output_state') and dep_step.operation.output_state:
                                for expr in dep_step.operation.output_state.expressions:
                                    if expr and hasattr(expr, 'latex') and expr.latex:
                                        dep_latex = expr.latex
                                        break
                            if dep_latex:
                                st.latex(dep_latex)

                if current_dependents:
                    st.markdown("⬇️ 被依赖:")
                    for dep_id in current_dependents:
                        st.caption(f"  → {dep_id}")

    def _render_state_replay(self, trace, current_idx: int) -> None:
        """
        状态演化回放：显示 State₀ → State₁ → State₂。
        """
        order = trace.topological_order()
        states = []

        initial_state = None
        if trace.steps and hasattr(trace.steps[0], 'operation'):
            if hasattr(trace.steps[0].operation, 'input_state') and trace.steps[0].operation.input_state:
                initial_state = trace.steps[0].operation.input_state

        if initial_state:
            states.append(("初始状态", initial_state))

        for step_id in order[:current_idx + 1]:
            step = trace.get_step(step_id)
            if not step:
                continue
            if hasattr(step.operation, 'output_state') and step.operation.output_state:
                label = step.label or step_id
                states.append((label, step.operation.output_state))

        with st.container(border=True):
            st.markdown("### 🔄 状态演化")

            for i, (label, state) in enumerate(states):
                is_current = (i == len(states) - 1)

                with st.expander(f"{'▶️' if is_current else '✅'} {label}", expanded=is_current):
                    self._render_state_content(state)

                if i < len(states) - 1:
                    next_step_id = order[i] if i < len(order) else None
                    step = trace.get_step(next_step_id) if next_step_id else None
                    rule = ""
                    if step and hasattr(step.operation, 'theorem') and step.operation.theorem:
                        rule = step.operation.theorem
                    elif step and hasattr(step.operation, 'display_name'):
                        rule = step.operation.display_name

                    st.markdown(f"⬇️ **{rule}**")

            if len(states) == 0:
                st.info("暂无状态信息")

    def _render_state_content(self, state) -> None:
        """
        渲染单个状态的数学内容。
        """
        if not state:
            return

        if hasattr(state, 'expressions'):
            for expr in state.expressions:
                if expr and hasattr(expr, 'latex') and expr.latex:
                    st.latex(expr.latex)

        if hasattr(state, 'assumptions') and state.assumptions:
            with st.expander("假设"):
                for assumption in state.assumptions:
                    st.markdown(f"- {assumption}")

        if hasattr(state, 'constraints') and state.constraints:
            with st.expander("约束"):
                for constraint in state.constraints:
                    st.markdown(f"- {constraint}")


def render_proof_replay(trace, **kwargs) -> None:
    """便捷函数：渲染证明回放"""
    renderer = ProofReplayRenderer()
    renderer.render(trace, **kwargs)
