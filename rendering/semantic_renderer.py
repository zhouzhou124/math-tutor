"""
Semantic Renderer — 语义渲染器

═══════════════════════════════════════════════════════════════
职责
═══════════════════════════════════════════════════════════════

  理解数学语义，生成 Document AST。

  核心转换:

    ReasoningTrace → Document
      ├── StepBlock        (每个 OPERATION 步骤)
      ├── EquationBlock    (input→output 等式关系)
      ├── WarningBlock     (ErrorAnnotation → 警告)
      └── ProofBlock       (证明上下文)

    WorldState → Document
      ├── StepBlock        (约束传播/事实推导)
      ├── EquationBlock    (约束等式)
      ├── WarningBlock     (冲突/失效)
      └── ProofBlock       (证明策略/义务)

    dict → Document
      ├── StepBlock        (步骤块)
      ├── EquationBlock    (等式块)
      ├── WarningBlock     (警告块)
      └── ProofBlock       (证明块)

═══════════════════════════════════════════════════════════════
映射规则
═══════════════════════════════════════════════════════════════

  StepType → BlockType:
    PREMISE      → PARAGRAPH (已知条件)
    OPERATION    → STEP + StepBlock
    EXPRESSION   → DISPLAY_MATH
    CONCLUSION   → STEP + StepBlock (结论步骤)
    ASSUMPTION   → CASE_BRANCH
    GOAL         → PARAGRAPH (目标声明)
    ERROR        → STEP + StepBlock + WARNING
    FINAL_ANSWER → FINAL_ANSWER

  ErrorAnnotation → WarningBlock:
    CORRECT     → 不生成
    MINOR       → severity="info"
    CALCULATION → severity="warning"
    REASONING   → severity="error"
    CONCEPTUAL  → severity="error"
    MISSING     → severity="warning"

  MathOperation → EquationBlock:
    input_expr + output_expr → lhs = rhs

  ProofContext → ProofBlock:
    strategy, phase, theorems_used, branches → ProofBlock

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from rendering.document_ast import (
    BlockType,
    MathDisplayStyle,
    DocumentNode,
    Document,
    StepBlock,
    ProofBlock,
    MatrixBlock,
    EquationBlock,
    WarningBlock,
    TableBlock,
)
from rendering.templates import (
    get_template,
    render_title as tpl_render_title,
    render_explanation as tpl_render_explanation,
    render_constraints as tpl_render_constraints,
    render_error_hints as tpl_render_error_hints,
    OpTemplate,
)
from rendering.templates.expr_formatter import ExprFormatter


_OP_DISPLAY = None
_OP_COLOR = None


def _get_op_display(op_value: str) -> str:
    tpl = get_template(op_value)
    return tpl.title if tpl.op_key == op_value else op_value


def _get_op_color(op_value: str) -> str:
    tpl = get_template(op_value)
    return tpl.color

_LEGALITY_SYMBOL = {
    "valid": "✓",
    "suspect": "⚠",
    "invalid": "✗",
    "unknown": "",
}

_LEGALITY_COLOR = {
    "valid": "#16a34a",
    "suspect": "#f59e0b",
    "invalid": "#ef4444",
    "unknown": "#6b7280",
}

_SEVERITY_MAP = {
    "correct": None,
    "minor": "info",
    "calculation": "warning",
    "reasoning": "error",
    "conceptual": "error",
    "missing": "warning",
}

_STEP_TYPE_BLOCK_MAP = {
    "premise": BlockType.PARAGRAPH,
    "operation": BlockType.STEP,
    "expression": BlockType.DISPLAY_MATH,
    "conclusion": BlockType.STEP,
    "assumption": BlockType.CASE_BRANCH,
    "goal": BlockType.PARAGRAPH,
    "error": BlockType.STEP,
    "final_answer": BlockType.FINAL_ANSWER,
}


@dataclass(frozen=True)
class RenderConfig:
    show_legality: bool = True
    show_operation_badge: bool = True
    show_confidence: bool = False
    show_proof_obligations: bool = True
    show_warnings: bool = True
    show_input_expr: bool = True
    show_output_expr: bool = True
    show_dividers: bool = True
    show_step_numbers: bool = True
    show_equations: bool = True
    show_proof_context: bool = True
    show_facts: bool = True
    show_goals: bool = True
    show_assumptions: bool = True
    show_obligations: bool = True
    show_domains: bool = True
    highlight_final_answer: bool = True
    max_warning_depth: int = 3
    step_number_offset: int = 0
    title: str = ""
    equation_style: str = "aligned"
    include_trace_edges: bool = False


class SemanticRenderer:
    """
    语义渲染器 — 将数学推理结构转换为 Document AST。

    核心入口:
      render(trace) → Document

    支持三种输入源:
      1. ReasoningTrace (MathIR) — render_trace()
      2. WorldState (Runtime)    — render_world_state()
      3. 原始 dict (LLM 输出)    — render_dict()

    输出 Document 结构:
      Document
        ├── StepBlock        (推理步骤)
        ├── EquationBlock    (等式关系)
        ├── WarningBlock     (错误/警告)
        └── ProofBlock       (证明上下文)
    """

    def __init__(self, config: RenderConfig = None):
        self.config = config or RenderConfig()

    def render(self, trace: Any, config: RenderConfig = None) -> Document:
        """
        核心入口: ReasoningTrace → Document。

        生成:
          Document
            ├── StepBlock        (每个 OPERATION/CONCLUSION 步骤)
            ├── EquationBlock    (input→output 等式)
            ├── WarningBlock     (ErrorAnnotation)
            └── ProofBlock       (证明上下文，如有)
        """
        return self.render_trace(trace, config)

    def render_trace(self, trace: Any, config: RenderConfig = None) -> Document:
        cfg = config or self.config
        doc = Document.empty()

        if cfg.title:
            doc = doc.with_title(cfg.title)
        elif hasattr(trace, "question_id") and trace.question_id:
            doc = doc.with_title(trace.question_id)

        steps = getattr(trace, "steps", [])
        for i, step in enumerate(steps):
            nodes = self._render_step_to_nodes(step, i + 1 + cfg.step_number_offset, cfg)
            for node in nodes:
                doc = doc.with_node(node)

        if cfg.include_trace_edges:
            edge_node = self._render_trace_edges(trace)
            if edge_node:
                doc = doc.with_node(edge_node)

        final = self._extract_final_answer(trace)
        if final:
            if cfg.show_dividers:
                doc = doc.with_node(DocumentNode(type=BlockType.DIVIDER))
            doc = doc.with_node(DocumentNode(
                type=BlockType.FINAL_ANSWER,
                content=final,
                metadata={"highlight": cfg.highlight_final_answer},
            ))

        return doc

    def render_world_state(self, ws: Any, config: RenderConfig = None) -> Document:
        """
        WorldState → Document。

        映射:
          assumptions  → PARAGRAPH / CASE_BRANCH
          facts        → PARAGRAPH (按类型分组)
          constraints  → EQUATION / PARAGRAPH
          obligations  → OBLIGATION
          goals        → PARAGRAPH
          proof_context → ProofBlock
          domains      → PARAGRAPH
        """
        cfg = config or self.config
        doc = Document.empty()
        if cfg.title:
            doc = doc.with_title(cfg.title)

        if cfg.show_assumptions:
            doc = self._render_assumptions(ws, doc, cfg)

        if cfg.show_domains:
            doc = self._render_domains(ws, doc, cfg)

        if cfg.show_facts:
            doc = self._render_facts_to_doc(ws, doc, cfg)

        if cfg.show_goals:
            doc = self._render_goals(ws, doc, cfg)

        if cfg.show_obligations:
            doc = self._render_obligations(ws, doc, cfg)

        if cfg.show_proof_context:
            doc = self._render_proof_context_to_doc(ws, doc, cfg)

        return doc

    def render_dict(self, data: dict, config: RenderConfig = None) -> Document:
        """
        dict → Document。

        支持两种格式:
          1. 结构化步骤: {"steps": [...], "final_answer": ...}
          2. 扁平文本: {"text": "...", "latex": "..."}
        """
        cfg = config or self.config
        doc = Document.empty()
        if cfg.title:
            doc = doc.with_title(cfg.title)
        elif data.get("title"):
            doc = doc.with_title(data["title"])

        steps = data.get("steps", [])
        if steps:
            for i, step in enumerate(steps):
                nodes = self._render_dict_step_to_nodes(step, i + 1 + cfg.step_number_offset, cfg)
                for node in nodes:
                    doc = doc.with_node(node)
        elif data.get("text") or data.get("latex"):
            doc = self._render_flat_dict(data, doc, cfg)

        final = data.get("final_answer", "")
        if final:
            final_text = final.get("content", "") if isinstance(final, dict) else str(final)
            if final_text:
                if cfg.show_dividers:
                    doc = doc.with_node(DocumentNode(type=BlockType.DIVIDER))
                doc = doc.with_node(DocumentNode(
                    type=BlockType.FINAL_ANSWER,
                    content=final_text,
                    metadata={"highlight": cfg.highlight_final_answer},
                ))

        return doc

    # ═══════════════════════════════════════════════════════════
    # ReasoningStep → DocumentNode[] (核心映射)
    # ═══════════════════════════════════════════════════════════

    def _render_step_to_nodes(
        self, step: Any, number: int, cfg: RenderConfig
    ) -> list[DocumentNode]:
        """
        将单个 ReasoningStep 映射为 DocumentNode 列表。

        根据 StepType 生成不同结构:
          OPERATION    → [StepBlock, EquationBlock?, WarningBlock*]
          CONCLUSION   → [StepBlock, EquationBlock?]
          PREMISE      → [PARAGRAPH]
          ASSUMPTION   → [CASE_BRANCH]
          GOAL         → [PARAGRAPH]
          ERROR        → [StepBlock, WarningBlock]
          EXPRESSION   → [DISPLAY_MATH]
          FINAL_ANSWER → [FINAL_ANSWER]
        """
        step_type = getattr(step, "step_type", None)
        step_type_val = step_type.value if hasattr(step_type, "value") else str(step_type) if step_type else "operation"

        if step_type_val == "premise":
            return self._render_premise(step, cfg)
        elif step_type_val == "operation":
            return self._render_operation_step(step, number, cfg)
        elif step_type_val == "conclusion":
            return self._render_conclusion_step(step, number, cfg)
        elif step_type_val == "assumption":
            return self._render_assumption_step(step, cfg)
        elif step_type_val == "goal":
            return self._render_goal_step(step, cfg)
        elif step_type_val == "error":
            return self._render_error_step(step, number, cfg)
        elif step_type_val == "expression":
            return self._render_expression_step(step, cfg)
        elif step_type_val == "final_answer":
            return self._render_final_answer_step(step, cfg)
        else:
            return self._render_operation_step(step, number, cfg)

    def _render_operation_step(
        self, step: Any, number: int, cfg: RenderConfig
    ) -> list[DocumentNode]:
        nodes = []

        operation = getattr(step, "operation", None)
        op_type, legality, input_expr, output_expr, theorem, reasoning, confidence = \
            self._extract_operation_fields(operation)

        step_id = getattr(step, "step_id", f"s{number}")
        label = getattr(step, "label", "")
        content = getattr(step, "content", "")
        error = getattr(step, "error", None)

        title = self._build_step_title(label, number, cfg)

        tpl = get_template(op_type)
        tpl_kwargs = self._build_template_kwargs(
            op_type, input_expr, output_expr, theorem, operation
        )

        template_explanation = tpl.render_explanation(**tpl_kwargs)
        template_constraints = tpl.render_constraints(**tpl_kwargs)
        template_error_hints = tpl.render_error_hints(**tpl_kwargs)

        explanation = content or reasoning or template_explanation

        warnings = self._extract_warnings(error)
        obligations = self._extract_obligations(theorem, operation)
        obligations.extend(template_constraints)

        if not warnings and template_error_hints and legality in ("suspect", "invalid"):
            for hint in template_error_hints:
                warnings.append(("warning", hint, ""))

        step_block = StepBlock(
            step_id=step_id,
            title=title,
            explanation=explanation,
            input_expr=input_expr,
            output_expr=output_expr,
            operation=op_type,
            legality=legality,
            warnings=tuple(warnings),
            proof_obligations=tuple(obligations),
            theorem_used=theorem,
            confidence=confidence,
            source_step_id=step_id,
        )

        children = []

        if cfg.show_input_expr and input_expr:
            children.append(DocumentNode(
                type=BlockType.INLINE_MATH,
                content=input_expr,
                metadata={"role": "input"},
            ))

        if cfg.show_output_expr and output_expr:
            children.append(DocumentNode(
                type=BlockType.DISPLAY_MATH,
                content=output_expr,
                metadata={"role": "output"},
            ))

        if cfg.show_equations and input_expr and output_expr:
            eq_block = EquationBlock(
                lhs=input_expr,
                rhs=output_expr,
                label=step_id,
                display=MathDisplayStyle.ALIGNED if cfg.equation_style == "aligned" else MathDisplayStyle.DISPLAY,
            )
            children.append(DocumentNode(
                type=BlockType.EQUATION,
                content=eq_block,
                metadata={"source_step_id": step_id, "role": "transformation"},
            ))

        if cfg.show_warnings and warnings:
            for w in warnings:
                children.append(DocumentNode(
                    type=BlockType.WARNING,
                    content=WarningBlock(
                        severity=w[0],
                        message=w[1],
                        suggestion=w[2] if len(w) > 2 else "",
                    ),
                ))

        if cfg.show_proof_obligations and obligations:
            for o in obligations:
                children.append(DocumentNode(
                    type=BlockType.OBLIGATION,
                    content=o,
                ))

        nodes.append(DocumentNode(
            type=BlockType.STEP,
            content=step_block,
            children=tuple(children),
            metadata={"source_step_id": step_id},
        ))

        return nodes

    def _render_conclusion_step(
        self, step: Any, number: int, cfg: RenderConfig
    ) -> list[DocumentNode]:
        nodes = self._render_operation_step(step, number, cfg)
        if nodes and isinstance(nodes[0].content, StepBlock):
            sb = nodes[0].content
            nodes[0] = DocumentNode(
                type=BlockType.STEP,
                content=StepBlock(
                    step_id=sb.step_id,
                    title=sb.title.replace("步骤", "结论") if "步骤" in sb.title else f"结论: {sb.title}",
                    explanation=sb.explanation,
                    input_expr=sb.input_expr,
                    output_expr=sb.output_expr,
                    operation=sb.operation,
                    legality=sb.legality,
                    warnings=sb.warnings,
                    proof_obligations=sb.proof_obligations,
                    theorem_used=sb.theorem_used,
                    confidence=sb.confidence,
                    source_step_id=sb.source_step_id,
                    metadata={"conclusion": True},
                ),
                children=nodes[0].children,
                metadata={"source_step_id": sb.source_step_id, "conclusion": True},
            )
        return nodes

    def _render_premise(self, step: Any, cfg: RenderConfig) -> list[DocumentNode]:
        content = getattr(step, "content", "")
        label = getattr(step, "label", "已知")
        step_id = getattr(step, "step_id", "")
        text = f"**{label}**: {content}" if label else content
        return [DocumentNode(
            type=BlockType.PARAGRAPH,
            content=text,
            metadata={"source_step_id": step_id, "role": "premise"},
        )]

    def _render_assumption_step(self, step: Any, cfg: RenderConfig) -> list[DocumentNode]:
        content = getattr(step, "content", "")
        label = getattr(step, "label", "假设")
        step_id = getattr(step, "step_id", "")
        return [DocumentNode(
            type=BlockType.CASE_BRANCH,
            content=f"**{label}**: {content}",
            metadata={"source_step_id": step_id, "case_label": label, "role": "assumption"},
        )]

    def _render_goal_step(self, step: Any, cfg: RenderConfig) -> list[DocumentNode]:
        content = getattr(step, "content", "")
        label = getattr(step, "label", "目标")
        step_id = getattr(step, "step_id", "")
        return [DocumentNode(
            type=BlockType.PARAGRAPH,
            content=f"**{label}**: {content}",
            metadata={"source_step_id": step_id, "role": "goal"},
        )]

    def _render_error_step(
        self, step: Any, number: int, cfg: RenderConfig
    ) -> list[DocumentNode]:
        nodes = self._render_operation_step(step, number, cfg)

        error = getattr(step, "error", None)
        if error and getattr(error, "is_error", False):
            severity = self._map_error_severity(error)
            desc = getattr(error, "description", "")
            suggestion = getattr(error, "suggestion", "")
            root_cause = getattr(error, "root_cause", "")

            warn_block = WarningBlock(
                severity=severity,
                message=desc or "步骤有误",
                location=getattr(step, "step_id", f"s{number}"),
                suggestion=suggestion or root_cause,
            )
            nodes.append(DocumentNode(
                type=BlockType.WARNING,
                content=warn_block,
                metadata={"source_step_id": getattr(step, "step_id", "")},
            ))

        return nodes

    def _render_expression_step(self, step: Any, cfg: RenderConfig) -> list[DocumentNode]:
        content = getattr(step, "content", "")
        step_id = getattr(step, "step_id", "")
        if not content:
            return []
        return [DocumentNode(
            type=BlockType.DISPLAY_MATH,
            content=content,
            metadata={"source_step_id": step_id, "role": "expression"},
        )]

    def _render_final_answer_step(self, step: Any, cfg: RenderConfig) -> list[DocumentNode]:
        content = getattr(step, "content", "")
        step_id = getattr(step, "step_id", "")
        if not content:
            return []
        return [DocumentNode(
            type=BlockType.FINAL_ANSWER,
            content=content,
            metadata={"highlight": cfg.highlight_final_answer, "source_step_id": step_id},
        )]

    # ═══════════════════════════════════════════════════════════
    # dict step → DocumentNode[]
    # ═══════════════════════════════════════════════════════════

    def _render_dict_step_to_nodes(
        self, step: dict, number: int, cfg: RenderConfig
    ) -> list[DocumentNode]:
        nodes = []

        label = step.get("label", f"步骤 {number}")
        if cfg.show_step_numbers:
            label = f"步骤 {number}: {label}" if step.get("label") else f"步骤 {number}"

        blocks = step.get("blocks", [])
        operation = step.get("operation", "")
        legality = step.get("legality", "unknown")

        children = []
        input_expr = ""
        output_expr = ""

        for b in blocks:
            b_type = b.get("type", "text")
            b_content = b.get("content", "")
            b_display = b.get("display", "inline")

            if b_type == "latex":
                if b_display == "block":
                    if not output_expr:
                        output_expr = b_content
                    children.append(DocumentNode(
                        type=BlockType.DISPLAY_MATH,
                        content=b_content,
                    ))
                else:
                    if not input_expr:
                        input_expr = b_content
                    children.append(DocumentNode(
                        type=BlockType.INLINE_MATH,
                        content=b_content,
                    ))
            elif b_type == "text":
                children.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=b_content,
                ))
            elif b_type == "equation":
                eq_block = EquationBlock(
                    lhs=b.get("lhs", b_content),
                    rhs=b.get("rhs", ""),
                    label=b.get("label", ""),
                )
                children.append(DocumentNode(
                    type=BlockType.EQUATION,
                    content=eq_block,
                ))
            elif b_type == "warning":
                warn_block = WarningBlock(
                    severity=b.get("severity", "warning"),
                    message=b_content,
                    suggestion=b.get("suggestion", ""),
                )
                children.append(DocumentNode(
                    type=BlockType.WARNING,
                    content=warn_block,
                ))
            elif b_type == "proof":
                proof_block = ProofBlock(
                    strategy=b.get("strategy", "direct"),
                    phase=b.get("phase", "not_started"),
                    goal=b.get("goal", b_content),
                )
                children.append(DocumentNode(
                    type=BlockType.PROOF,
                    content=proof_block,
                ))
            elif b_type == "matrix":
                mat_block = MatrixBlock(
                    rows=tuple(tuple(r) for r in b.get("rows", ())),
                    environment=b.get("environment", "pmatrix"),
                    label=b.get("label", ""),
                )
                children.append(DocumentNode(
                    type=BlockType.MATRIX,
                    content=mat_block,
                ))

        if cfg.show_equations and input_expr and output_expr:
            eq_block = EquationBlock(
                lhs=input_expr,
                rhs=output_expr,
                label=step.get("step_id", f"s{number}"),
            )
            children.append(DocumentNode(
                type=BlockType.EQUATION,
                content=eq_block,
                metadata={"role": "transformation"},
            ))

        tpl = get_template(operation)
        tpl_kwargs = self._build_template_kwargs(
            operation, input_expr, output_expr,
            step.get("theorem_used", ""), None,
        )
        template_explanation = tpl.render_explanation(**tpl_kwargs)
        template_constraints = tpl.render_constraints(**tpl_kwargs)
        template_error_hints = tpl.render_error_hints(**tpl_kwargs)

        explanation = step.get("explanation", "") or template_explanation

        obligations = list(step.get("proof_obligations", ()))
        obligations.extend(template_constraints)

        step_warnings = list(step.get("warnings", []))
        if not step_warnings and template_error_hints and legality in ("suspect", "invalid"):
            for hint in template_error_hints:
                step_warnings.append(hint)

        if cfg.show_warnings and step_warnings:
            for w in step_warnings:
                if isinstance(w, str):
                    warn_block = WarningBlock(severity="warning", message=w)
                elif isinstance(w, dict):
                    warn_block = WarningBlock(
                        severity=w.get("severity", "warning"),
                        message=w.get("message", ""),
                        suggestion=w.get("suggestion", ""),
                    )
                else:
                    continue
                children.append(DocumentNode(
                    type=BlockType.WARNING,
                    content=warn_block,
                ))

        step_block = StepBlock(
            step_id=step.get("step_id", f"s{number}"),
            title=label,
            explanation=explanation,
            input_expr=input_expr,
            output_expr=output_expr,
            operation=operation,
            legality=legality,
            warnings=tuple(step_warnings if all(isinstance(w, str) for w in step_warnings) else ()),
            proof_obligations=tuple(obligations),
            theorem_used=step.get("theorem_used", ""),
            confidence=step.get("confidence", 1.0),
        )

        nodes.append(DocumentNode(
            type=BlockType.STEP,
            content=step_block,
            children=tuple(children),
            metadata={"source_step_id": step.get("step_id", f"s{number}")},
        ))

        return nodes

    def _render_flat_dict(self, data: dict, doc: Document, cfg: RenderConfig) -> Document:
        text = data.get("text", "")
        latex = data.get("latex", "")

        if text:
            doc = doc.with_node(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=text,
            ))

        if latex:
            display = data.get("display", "block")
            block_type = BlockType.DISPLAY_MATH if display == "block" else BlockType.INLINE_MATH
            doc = doc.with_node(DocumentNode(
                type=block_type,
                content=latex,
            ))

        return doc

    # ═══════════════════════════════════════════════════════════
    # WorldState 子模块渲染
    # ═══════════════════════════════════════════════════════════

    def _render_assumptions(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        assumptions = getattr(ws, "assumptions", ())
        if not assumptions:
            return doc

        for a in assumptions:
            text = getattr(a, "proposition", str(a))
            kind = getattr(a, "kind", None)
            kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            confidence = getattr(a, "confidence", 1.0)
            retractable = getattr(a, "retractable", False)

            if kind_val == "case_assumption":
                node = DocumentNode(
                    type=BlockType.CASE_BRANCH,
                    content=f"**假设** ({kind_val}): {text}",
                    metadata={
                        "source": "assumption",
                        "retractable": retractable,
                        "confidence": confidence,
                    },
                )
            else:
                label_map = {
                    "given": "已知",
                    "hypothesis": "假设",
                    "axiom": "公理",
                    "convention": "约定",
                    "temporary": "临时假设",
                }
                label = label_map.get(kind_val, kind_val)
                node = DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"**{label}**: {text}",
                    metadata={
                        "source": "assumption",
                        "kind": kind_val,
                        "confidence": confidence,
                        "retractable": retractable,
                    },
                )
            doc = doc.with_node(node)

        return doc

    def _render_domains(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        domains = getattr(ws, "domains", None)
        if not domains:
            return doc

        all_vars = getattr(domains, "all_variables", lambda: [])()
        if not all_vars:
            return doc

        for v in all_vars:
            entry = getattr(domains, "get", lambda x, y=None: y)(v, None)
            if entry:
                domain_kind = getattr(entry, "kind", None)
                kind_val = domain_kind.value if hasattr(domain_kind, "value") else str(domain_kind) if domain_kind else ""
                node = DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"**定义域** {v} ∈ {kind_val}",
                    metadata={"source": "domain", "variable": v},
                )
                doc = doc.with_node(node)

        return doc

    def _render_facts_to_doc(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        facts = getattr(ws, "facts", None)
        if not facts:
            return doc

        fact_list = getattr(facts, "facts", ())
        if not fact_list:
            return doc

        type_groups: dict[str, list] = {}
        for f in fact_list:
            ft = getattr(f, "fact_type", None)
            ft_val = ft.value if hasattr(ft, "value") else str(ft) if ft else "unknown"
            if ft_val not in type_groups:
                type_groups[ft_val] = []
            expr = getattr(f, "expression", str(f))
            confidence = getattr(f, "confidence", 1.0)
            type_groups[ft_val].append((expr, confidence))

        display_names = {
            "constraint": "约束",
            "theorem": "定理",
            "derived": "推导事实",
            "assumption": "假设",
            "case": "分类讨论",
            "proved": "已证",
            "goal": "目标",
            "definition": "定义",
            "domain": "定义域",
        }

        for ft_val, items in type_groups.items():
            name = display_names.get(ft_val, ft_val)
            for expr, conf in items:
                node = DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"**{name}**: {expr}",
                    metadata={"source": "fact", "fact_type": ft_val, "confidence": conf},
                )
                doc = doc.with_node(node)

        return doc

    def _render_goals(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        goals = getattr(ws, "goals", ())
        if not goals:
            return doc

        for g in goals:
            desc = getattr(g, "description", str(g))
            kind = getattr(g, "kind", None)
            kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            status = getattr(g, "status", None)
            status_val = status.name if hasattr(status, "name") else str(status) if status else ""
            progress = getattr(g, "progress", 0.0)
            strategy = getattr(g, "strategy", None)
            strategy_val = strategy.value if hasattr(strategy, "value") else str(strategy) if strategy else ""
            parent_id = getattr(g, "parent_id", "")
            subgoal_ids = getattr(g, "subgoal_ids", ())

            is_root = not parent_id
            prefix = "**目标**" if is_root else "**子目标**"
            status_tag = f" [{status_val}]" if status_val else ""
            strategy_tag = f" (策略: {strategy_val})" if strategy_val and strategy_val != "direct" else ""
            progress_tag = f" ({progress:.0%})" if progress > 0 else ""

            node = DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"{prefix}{status_tag}{strategy_tag}{progress_tag}: {desc}",
                metadata={
                    "source": "goal",
                    "kind": kind_val,
                    "status": status_val,
                    "is_root": is_root,
                    "subgoal_count": len(subgoal_ids),
                },
            )
            doc = doc.with_node(node)

        return doc

    def _render_obligations(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        obligations = getattr(ws, "obligations", ())
        if not obligations:
            return doc

        for o in obligations:
            prop = getattr(o, "proposition", str(o))
            status = getattr(o, "status", None)
            status_val = status.name if hasattr(status, "name") else str(status) if status else ""
            reason = getattr(o, "reason", "")
            priority = getattr(o, "priority", 5)

            node = DocumentNode(
                type=BlockType.OBLIGATION,
                content=f"[{status_val}] {prop}",
                metadata={
                    "source": "obligation",
                    "status": status_val,
                    "reason": reason,
                    "priority": priority,
                },
            )
            doc = doc.with_node(node)

        return doc

    def _render_proof_context_to_doc(self, ws: Any, doc: Document, cfg: RenderConfig) -> Document:
        proof_ctx = getattr(ws, "proof_context", None)
        if not proof_ctx:
            return doc

        strategy = getattr(proof_ctx, "strategy", None)
        strategy_val = strategy.value if hasattr(strategy, "value") else str(strategy) if strategy else "direct"
        phase = getattr(proof_ctx, "phase", None)
        phase_val = phase.name if hasattr(phase, "name") else str(phase) if phase else "NOT_STARTED"
        theorems_used = getattr(proof_ctx, "theorems_used", ())
        failed_strategies = getattr(proof_ctx, "failed_strategies", ())
        current_branch = getattr(proof_ctx, "current_branch", "")
        completed_branches = getattr(proof_ctx, "completed_branches", ())
        pending_branches = getattr(proof_ctx, "pending_branches", ())
        proof_log = getattr(proof_ctx, "proof_log", ())

        goals = getattr(ws, "goals", ())
        goal_desc = ""
        for g in goals:
            if getattr(g, "is_root", lambda: not getattr(g, "parent_id", ""))():
                goal_desc = getattr(g, "description", "")
                break

        obligations = getattr(ws, "obligations", ())
        obligation_strs = tuple(
            getattr(o, "proposition", str(o)) for o in obligations
        )
        discharged_strs = tuple(
            getattr(o, "proposition", str(o))
            for o in obligations
            if getattr(getattr(o, "status", None), "name", "") == "DISCHARGED"
        )

        proof_block = ProofBlock(
            strategy=strategy_val,
            phase=phase_val,
            goal=goal_desc,
            obligations=obligation_strs,
            discharged=discharged_strs,
            assumptions=tuple(
                getattr(a, "proposition", str(a))
                for a in getattr(ws, "assumptions", ())
            ),
            contradiction_target="",
        )

        children = []

        if theorems_used:
            children.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"**已用定理**: {', '.join(theorems_used)}",
                metadata={"role": "theorems_used"},
            ))

        if failed_strategies:
            children.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"**失败策略**: {', '.join(failed_strategies)}",
                metadata={"role": "failed_strategies"},
            ))

        if current_branch or pending_branches or completed_branches:
            branch_info = []
            if current_branch:
                branch_info.append(f"当前: {current_branch}")
            if completed_branches:
                branch_info.append(f"已完成: {', '.join(completed_branches)}")
            if pending_branches:
                branch_info.append(f"待处理: {', '.join(pending_branches)}")
            children.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"**分类讨论**: {'; '.join(branch_info)}",
                metadata={"role": "case_branches"},
            ))

        if proof_log:
            log_items = [f"  {i+1}. {entry}" for i, entry in enumerate(proof_log[-5:])]
            children.append(DocumentNode(
                type=BlockType.CODE,
                content="\n".join(log_items),
                metadata={"role": "proof_log", "language": "text"},
            ))

        doc = doc.with_node(DocumentNode(
            type=BlockType.PROOF,
            content=proof_block,
            children=tuple(children),
            metadata={"source": "proof_context"},
        ))

        return doc

    # ═══════════════════════════════════════════════════════════
    # Trace edges
    # ═══════════════════════════════════════════════════════════

    def _render_trace_edges(self, trace: Any) -> Optional[DocumentNode]:
        edges = getattr(trace, "edges", [])
        if not edges:
            return None

        rows = []
        for e in edges:
            source = getattr(e, "source_id", "")
            target = getattr(e, "target_id", "")
            kind = getattr(e, "kind", None)
            kind_val = kind.value if hasattr(kind, "value") else str(kind) if kind else ""
            label = getattr(e, "label", "")
            rows.append((source, kind_val, target, label))

        if not rows:
            return None

        table = TableBlock(
            headers=("来源", "关系", "目标", "标注"),
            rows=tuple(rows),
            caption="推理步骤依赖关系",
        )
        return DocumentNode(
            type=BlockType.TABLE,
            content=table,
            metadata={"source": "trace_edges"},
        )

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def _extract_operation_fields(self, operation: Any) -> tuple:
        if not operation:
            return ("", "unknown", "", "", "", "", 1.0)

        op = getattr(operation, "op_type", None)
        op_type = op.value if hasattr(op, "value") else str(op) if op else ""

        legality_val = getattr(operation, "legality", None)
        legality = legality_val.value if hasattr(legality_val, "value") else str(legality_val) if legality_val else "unknown"

        input_expr = ""
        input_state = getattr(operation, "input_state", None)
        if input_state:
            exprs = getattr(input_state, "expressions", ())
            if exprs:
                first = exprs[0]
                input_expr = getattr(first, "latex", "") or getattr(first, "raw_text", str(first))

        output_expr = ""
        output_state = getattr(operation, "output_state", None)
        if output_state:
            exprs = getattr(output_state, "expressions", ())
            if exprs:
                first = exprs[0]
                output_expr = getattr(first, "latex", "") or getattr(first, "raw_text", str(first))

        theorem = getattr(operation, "theorem", "")
        reasoning = getattr(operation, "reasoning", "")
        confidence = getattr(operation, "confidence", 1.0) if hasattr(operation, "confidence") else 1.0

        return (op_type, legality, input_expr, output_expr, theorem, reasoning, confidence)

    def _extract_warnings(self, error: Any) -> list[tuple]:
        if not error or not getattr(error, "is_error", False):
            return []

        severity = self._map_error_severity(error)
        desc = getattr(error, "description", "")
        suggestion = getattr(error, "suggestion", "")
        root_cause = getattr(error, "root_cause", "")

        result = []
        if desc:
            result.append((severity, desc, suggestion or root_cause))
        elif root_cause:
            result.append((severity, root_cause, suggestion))

        return result

    def _extract_obligations(self, theorem: str, operation: Any) -> list[str]:
        obligations = []
        if theorem:
            obligations.append(f"需验证 {theorem} 的适用条件")

        goal = getattr(operation, "goal", "") if operation else ""
        if goal:
            obligations.append(f"目标: {goal}")

        return obligations

    def _build_template_kwargs(
        self, op_type: str, input_expr: str, output_expr: str,
        theorem: str, operation: Any,
    ) -> dict:
        kwargs = {}
        if input_expr:
            kwargs["input"] = input_expr
        else:
            kwargs["input"] = ""
        if output_expr:
            kwargs["output"] = output_expr
        else:
            kwargs["output"] = ""
        if theorem:
            kwargs["theorem"] = theorem
        else:
            kwargs["theorem"] = ""

        formatter = ExprFormatter()
        variable = formatter.extract_variable(input_expr or "")
        if not variable:
            variable = formatter.extract_variable(getattr(operation, "reasoning", "") if operation else "")
        kwargs["variable"] = variable or "x"

        point = formatter.extract_point(input_expr or "")
        if not point:
            point = formatter.extract_point(getattr(operation, "reasoning", "") if operation else "")
        kwargs["point"] = point or "0"

        factor = formatter.extract_factor(input_expr, output_expr)
        kwargs["factor"] = factor or ""
        kwargs["constraint"] = factor or ""

        return kwargs

    def _map_error_severity(self, error: Any) -> str:
        severity = getattr(error, "severity", None)
        severity_val = severity.value if hasattr(severity, "value") else str(severity) if severity else "correct"
        return _SEVERITY_MAP.get(severity_val, "warning") or "warning"

    def _build_step_title(self, label: str, number: int, cfg: RenderConfig) -> str:
        if cfg.show_step_numbers:
            if label:
                return f"步骤 {number}: {label}"
            return f"步骤 {number}"
        return label or f"步骤 {number}"

    def _extract_final_answer(self, trace: Any) -> str:
        steps = getattr(trace, "steps", [])
        for step in reversed(steps):
            step_type = getattr(step, "step_type", None)
            if step_type and hasattr(step_type, "value") and step_type.value == "final_answer":
                return getattr(step, "content", "")
            op = getattr(step, "operation", None)
            if op:
                op_type = getattr(op, "op_type", None)
                if op_type and hasattr(op_type, "value") and op_type.value == "final_answer":
                    output_state = getattr(op, "output_state", None)
                    if output_state:
                        exprs = getattr(output_state, "expressions", ())
                        if exprs:
                            return getattr(exprs[0], "latex", "") or getattr(exprs[0], "raw_text", str(exprs[0]))
                    return getattr(step, "content", "")
        return ""

    @staticmethod
    def op_display_name(op_value: str) -> str:
        return _get_op_display(op_value)

    @staticmethod
    def op_color(op_value: str) -> str:
        return _get_op_color(op_value)

    @staticmethod
    def legality_symbol(legality: str) -> str:
        return _LEGALITY_SYMBOL.get(legality, "")

    @staticmethod
    def legality_color(legality: str) -> str:
        return _LEGALITY_COLOR.get(legality, "#6b7280")
