from typing import Optional, Sequence
from rendering.render_ir import (
    RenderNode, RenderType, RenderTree,
    TextNode, InlineMathNode, BlockMathNode, AlignNode,
    MatrixNode, CasesNode, StepNode, ProofNode, WarningNode,
    ObligationNode, FinalAnswerNode, ListNode, TableNode,
    DividerNode, CodeNode, ExpanderNode, ColumnsNode, ContainerNode
)


class ReasoningTraceToIRConverter:
    """
    将 Semantic Graph (ReasoningTrace) 投影为 Render IR (RenderTree)。

    这是关键的"图 → 视图"投影层：
      ReasoningTrace (Semantic Graph)
          ↓ 投影
      RenderTree (View)

    核心洞察：
      Render IR 不是独立结构，而是 Semantic Graph 的视图。
      同一 ReasoningTrace 可以有多个不同的 Render IR 视图：
        - ProofReplayRenderer: 线性回放视图
        - DAGRenderer: 图结构视图
        - StateTransitionRenderer: 状态演化视图

    投影策略：
      - 按 topological_order 线性化
      - 保留 step_id, dependencies, edges (metadata)
      - 每个 RenderNode 包含对原始 ReasoningStep 的引用
    """

    def __init__(self, config: dict = None):
        self._config = config or {}

    def convert(self, trace, view_mode: str = "linear") -> RenderTree:
        """
        主入口：将 ReasoningTrace 转换为 RenderTree。

        Args:
            trace: ReasoningTrace 对象
            view_mode: 视图模式
              - "linear": 线性回放视图（ProofReplay）
              - "dag": DAG 结构视图
              - "state_transition": 状态演化视图

        Returns:
            RenderTree: Semantic Graph 的视图投影
        """
        if not trace or not trace.steps:
            return RenderTree()

        if view_mode == "dag":
            return self._convert_to_dag_view(trace)
        elif view_mode == "state_transition":
            return self._convert_to_state_view(trace)
        else:
            return self._convert_to_linear_view(trace)

    def _convert_to_linear_view(self, trace) -> RenderTree:
        """
        线性回放视图：按 topological_order 线性排列。
        用于 ProofReplay。
        """
        children = []
        order = trace.topological_order()

        for i, step_id in enumerate(order):
            step = trace.get_step(step_id)
            if not step:
                continue

            node = self._step_to_node(step, trace, index=i)
            children.append(node)

        root = RenderNode(
            type=RenderType.CONTAINER,
            children=tuple(children),
            metadata={
                "view_mode": "linear",
                "trace_id": trace.trace_id,
                "step_count": len(order)
            }
        )
        return RenderTree(root=root)

    def _convert_to_dag_view(self, trace) -> RenderTree:
        """
        DAG 结构视图：保留依赖关系。
        用于 DAG Visualization。
        """
        children = []

        nodes_by_depth = {}
        in_degree = {s.step_id: 0 for s in trace.steps}
        for e in trace.edges:
            if e.target_id in in_degree:
                in_degree[e.target_id] += 1

        roots = [sid for sid, deg in in_degree.items() if deg == 0]

        def assign_depth(step_id: str, depth: int):
            if step_id not in nodes_by_depth or nodes_by_depth[step_id] < depth:
                nodes_by_depth[step_id] = depth
            for dep_id in trace.get_dependents(step_id):
                assign_depth(dep_id, depth + 1)

        for root_id in roots:
            assign_depth(root_id, 0)

        for step_id in trace.steps:
            if step_id not in nodes_by_depth:
                nodes_by_depth[step_id] = 0

        max_depth = max(nodes_by_depth.values()) if nodes_by_depth else 0
        depth_groups = [[] for _ in range(max_depth + 1)]
        for step_id, depth in nodes_by_depth.items():
            depth_groups[depth].append(step_id)

        for depth, step_ids in enumerate(depth_groups):
            if not step_ids:
                continue

            columns = []
            for step_id in step_ids:
                step = trace.get_step(step_id)
                if step:
                    node = self._step_to_node(step, trace, index=depth)
                    columns.append(node)

            if len(columns) == 1:
                children.append(columns[0])
            else:
                col_node = ColumnsNode(
                    columns=tuple(columns),
                    column_count=len(columns)
                )
                children.append(col_node)

        root = RenderNode(
            type=RenderType.CONTAINER,
            children=tuple(children),
            metadata={
                "view_mode": "dag",
                "trace_id": trace.trace_id,
                "node_count": len(trace.steps),
                "edge_count": len(trace.edges)
            }
        )
        return RenderTree(root=root)

    def _convert_to_state_view(self, trace) -> RenderTree:
        """
        状态演化视图：显示 State₀ → State₁ → State₂。
        用于 State Transition Viewer。
        """
        children = []

        order = trace.topological_order()
        states = []

        initial_state = MathState.empty()
        if trace.steps and trace.steps[0].operation.input_state:
            initial_state = trace.steps[0].operation.input_state
        states.append(("初始", initial_state))

        for step_id in order:
            step = trace.get_step(step_id)
            if not step:
                continue
            if step.operation.output_state and not step.operation.output_state.is_empty:
                state_label = step.label or step_id
                states.append((state_label, step.operation.output_state))

        for i, (label, state) in enumerate(states):
            state_node = self._state_to_node(label, state, trace, index=i)
            children.append(state_node)

            if i < len(states) - 1:
                transition_label = ""
                if i < len(order):
                    step = trace.get_step(order[i])
                    if step and step.operation.theorem:
                        transition_label = step.operation.theorem
                    elif step and step.operation.op_type:
                        transition_label = step.operation.display_name

                arrow_node = self._transition_to_node(transition_label, trace)
                children.append(arrow_node)

        root = RenderNode(
            type=RenderType.CONTAINER,
            children=tuple(children),
            metadata={
                "view_mode": "state_transition",
                "trace_id": trace.trace_id,
                "state_count": len(states)
            }
        )
        return RenderTree(root=root)

    def _step_to_node(self, step, trace, index: int = 0) -> RenderNode:
        """
        将 ReasoningStep 转换为 StepNode。
        关键：保留 step_id, dependencies, operation 等语义。
        """
        dependencies = step.dependencies or ()
        deps_str = ", ".join(dependencies) if dependencies else "无"

        legality = "unknown"
        if hasattr(step.operation, 'legality'):
            legality = step.operation.legality.value if step.operation.legality else "unknown"

        operation_name = ""
        if hasattr(step.operation, 'display_name'):
            operation_name = step.operation.display_name
        elif hasattr(step.operation, 'op_type'):
            operation_name = str(step.operation.op_type.value)

        theorem = ""
        if hasattr(step.operation, 'theorem') and step.operation.theorem:
            theorem = step.operation.theorem

        output_latex = ""
        if hasattr(step.operation, 'output_state') and step.operation.output_state:
            for expr in step.operation.output_state.expressions:
                if expr.latex:
                    output_latex = expr.latex
                    break

        children = []

        if output_latex:
            math_node = BlockMathNode(
                latex=output_latex,
                metadata={"step_id": step.step_id}
            )
            children.append(math_node)

        error_info = None
        if step.error and step.error.is_error:
            severity = step.error.severity.value if hasattr(step.error, 'severity') else "error"
            desc = step.error.description if hasattr(step.error, 'description') else str(step.error)
            error_info = (severity, desc)

        metadata = {
            "step_id": step.step_id,
            "index": index,
            "dependencies": deps_str,
            "dependency_ids": list(dependencies),
            "legality": legality,
            "operation": operation_name,
            "theorem": theorem,
            "output_expr": output_latex,
            "trace_id": trace.trace_id if hasattr(trace, 'trace_id') else "",
        }

        if error_info:
            metadata["error"] = {"severity": error_info[0], "description": error_info[1]}

        if step.content:
            text_node = TextNode(text=str(step.content), metadata={"role": "step_content"})
            children.insert(0, text_node)

        node = StepNode(
            step_id=step.step_id,
            title=f"步骤 {index + 1}" + (f": {step.label}" if step.label else ""),
            operation=operation_name,
            legality=legality,
            input_expr="",
            output_expr=output_latex,
            explanation="",
            theorem_used=theorem,
            children=tuple(children),
            metadata=metadata
        )

        return node

    def _state_to_node(self, label: str, state, trace, index: int = 0) -> RenderNode:
        """
        将 MathState 转换为可渲染节点。
        """
        if not state or not hasattr(state, 'expressions'):
            return TextNode(text=f"State: {label}")

        exprs = []
        if hasattr(state, 'expressions'):
            for expr in state.expressions:
                if expr and hasattr(expr, 'latex') and expr.latex:
                    exprs.append(expr.latex)

        assumptions = list(getattr(state, 'assumptions', []) or [])
        constraints = list(getattr(state, 'constraints', []) or [])

        children = []

        if exprs:
            for latex in exprs:
                math_node = BlockMathNode(latex=latex, metadata={"state_index": index})
                children.append(math_node)

        info_parts = []
        if assumptions:
            info_parts.append(f"假设: {', '.join(assumptions)}")
        if constraints:
            info_parts.append(f"约束: {', '.join(constraints)}")

        if info_parts:
            info_text = " | ".join(info_parts)
            children.insert(0, TextNode(text=info_text, metadata={"role": "state_info"}))

        container = ContainerNode(
            border=True,
            child=RenderNode(
                type=RenderType.CONTAINER,
                children=tuple(children),
                content=label,
                metadata={"state_label": label, "state_index": index}
            )
        )

        return container

    def _transition_to_node(self, rule: str, trace) -> RenderNode:
        """
        将状态转换（推理规则）转换为可视化节点。
        """
        rule_text = rule if rule else "→"
        return TextNode(
            text=f"⬇️ *{rule_text}*",
            metadata={"role": "transition", "rule": rule}
        )


class MathState:
    @property
    def is_empty(self) -> bool:
        return not self.expressions and not self.assumptions and not self.constraints

    @property
    def expressions(self) -> tuple:
        return getattr(self, '_expressions', ())

    @property
    def assumptions(self) -> tuple:
        return getattr(self, '_assumptions', ())

    @property
    def constraints(self) -> tuple:
        return getattr(self, '_constraints', ())
