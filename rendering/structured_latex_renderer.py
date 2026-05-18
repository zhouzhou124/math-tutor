r"""
Structured LaTeX Renderer — 结构化 LaTeX 渲染器

核心原则:
  严禁字符串拼接 LaTeX。

  所有 LaTeX 输出必须通过结构化对象构建:
    - Equation(lhs, rhs)  而非 f"${lhs}={rhs}$"
    - AlignedBlock(lines)  而非 "\\begin{aligned}" + ... + "\\end{aligned}"
    - ProofBlock(steps)   而非 proof.to_latex()

  最后统一 render，确保:
    - $$ 包裹完整环境
    - \left/\right 配对
    - \begin/\end 配对
    - inline/block math 分离

架构:
  Canonical IR / Proof IR / LLM Output
      |
  Structured LaTeX Objects (Equation, AlignedBlock, ProofBlock, ...)
      |
  LatexRenderer.render_*() -> Render IR nodes
      |
  StreamlitRenderer -> st.latex() / st.markdown()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple, Union

from .render_ir import (
    RenderNode, RenderType, RenderTree,
    TextNode, InlineMathNode, BlockMathNode, AlignNode,
    CasesNode, StepNode, ProofNode, WarningNode,
    FinalAnswerNode, DividerNode,
)
from .latex_validator import LaTeXValidator


@dataclass
class Equation:
    lhs: str = ""
    rhs: str = ""
    label: str = ""

    def to_latex(self) -> str:
        if self.label:
            return f"{self.lhs} &= {self.rhs} \\tag{{{self.label}}}"
        return f"{self.lhs} &= {self.rhs}"


@dataclass
class AlignedLine:
    content: str = ""
    annotation: str = ""

    def to_latex(self) -> str:
        if self.annotation:
            return f"{self.content} \\quad \\text{{({self.annotation})}}"
        return self.content


@dataclass
class AlignedBlock:
    lines: List[AlignedLine] = field(default_factory=list)

    def to_latex(self) -> str:
        if not self.lines:
            return ""
        parts = [line.to_latex() for line in self.lines]
        return "\\\\\n".join(parts)

    def to_full_latex(self) -> str:
        body = self.to_latex()
        if not body:
            return ""
        return f"\\begin{{aligned}}\n{body}\n\\end{{aligned}}"


@dataclass
class CasesBlock:
    cases: List[Tuple[str, str]] = field(default_factory=list)

    def to_latex(self) -> str:
        if not self.cases:
            return ""
        parts = []
        for expr, condition in self.cases:
            if condition:
                parts.append(f"{expr}, & \\text{{if }} {condition}")
            else:
                parts.append(f"{expr}, & ")
        return "\\\\\n".join(parts)

    def to_full_latex(self) -> str:
        body = self.to_latex()
        if not body:
            return ""
        return f"\\begin{{cases}}\n{body}\n\\end{{cases}}"


@dataclass
class ProofStepIR:
    before: str = ""
    after: str = ""
    rule: str = ""
    rule_ref: str = ""

    def to_aligned_line(self) -> AlignedLine:
        if self.before and self.after:
            return AlignedLine(
                content=f"{self.before} &= {self.after}",
                annotation=self.rule,
            )
        elif self.after:
            return AlignedLine(content=self.after, annotation=self.rule)
        else:
            return AlignedLine(content=self.before, annotation=self.rule)


@dataclass
class ProofIR:
    steps: List[ProofStepIR] = field(default_factory=list)
    conclusion: str = ""
    assumptions: List[str] = field(default_factory=list)
    strategy: str = "direct"

    def to_aligned_block(self) -> AlignedBlock:
        lines = []
        for step in self.steps:
            lines.append(step.to_aligned_line())
        if self.conclusion:
            lines.append(AlignedLine(content=f"&= \\boxed{{{self.conclusion}}}"))
        return AlignedBlock(lines=lines)


class LatexRenderer:
    """
    结构化 LaTeX 渲染器 — 统一管理所有 LaTeX 输出。

    核心方法:
      render_expr(expr_str)     → InlineMathNode / BlockMathNode
      render_equation(eq)       → AlignNode
      render_aligned(block)     → AlignNode
      render_cases(block)       → CasesNode
      render_proof(proof_ir)    → ProofNode + AlignNode
      render_proof_trace(trace) → list[RenderNode]

    关键特点:
      - 不做字符串拼接
      - 所有输出经过 LaTeXValidator 验证
      - 返回 Render IR 节点，由 StreamlitRenderer 统一渲染
    """

    def __init__(self):
        self._validator = LaTeXValidator()

    def render_expr(self, expr: str, inline: bool = False) -> RenderNode:
        if not expr or not expr.strip():
            return TextNode(text="")

        validated = self._validate_and_fix(expr)

        if inline:
            return InlineMathNode(latex=validated)
        return BlockMathNode(latex=validated)

    def render_equation(self, lhs: str, rhs: str, label: str = "") -> RenderNode:
        eq = Equation(lhs=lhs, rhs=rhs, label=label)
        latex = eq.to_latex()
        validated = self._validate_and_fix(latex)
        return AlignNode(latex=validated)

    def render_aligned(self, block: AlignedBlock) -> RenderNode:
        full_latex = block.to_full_latex()
        if not full_latex:
            return TextNode(text="")
        validated = self._validate_and_fix(full_latex)
        return AlignNode(latex=validated)

    def render_aligned_from_lines(self, lines: List[str], annotations: List[str] = None) -> RenderNode:
        aligned_lines = []
        for i, line in enumerate(lines):
            ann = annotations[i] if annotations and i < len(annotations) else ""
            aligned_lines.append(AlignedLine(content=line, annotation=ann))
        block = AlignedBlock(lines=aligned_lines)
        return self.render_aligned(block)

    def render_cases(self, block: CasesBlock) -> RenderNode:
        full_latex = block.to_full_latex()
        if not full_latex:
            return TextNode(text="")
        validated = self._validate_and_fix(full_latex)
        return CasesNode(latex=validated)

    def render_proof(self, proof_ir: ProofIR) -> List[RenderNode]:
        nodes: List[RenderNode] = []

        if proof_ir.assumptions:
            nodes.append(ProofNode(
                strategy=proof_ir.strategy,
                goal="",
                assumptions=tuple(proof_ir.assumptions),
            ))

        aligned = proof_ir.to_aligned_block()
        if aligned.lines:
            nodes.append(self.render_aligned(aligned))

        return nodes

    def render_proof_trace(self, trace: Any) -> List[RenderNode]:
        """
        将 RewriteTrace 转换为 Render IR 节点列表。

        关键：不再调用 trace.to_latex()，而是结构化构建。
        """
        nodes: List[RenderNode] = []

        steps = getattr(trace, 'steps', [])
        if not steps:
            return nodes

        aligned_lines = []
        for step in steps:
            before = self._safe_get_latex(step, 'before')
            after = self._safe_get_latex(step, 'after')
            rule = getattr(step, 'rule', '') or ''

            if before and after:
                aligned_lines.append(AlignedLine(
                    content=f"{before} &= {after}",
                    annotation=rule,
                ))
            elif after:
                aligned_lines.append(AlignedLine(
                    content=f"&= {after}",
                    annotation=rule,
                ))
            elif before:
                aligned_lines.append(AlignedLine(
                    content=before,
                    annotation=rule,
                ))

        final_expr = getattr(trace, 'final_expr', None)
        if final_expr is not None:
            final_latex = self._expr_to_latex(final_expr)
            if final_latex:
                aligned_lines.append(AlignedLine(
                    content=f"&= \\boxed{{{final_latex}}}",
                    annotation="",
                ))

        if aligned_lines:
            block = AlignedBlock(lines=aligned_lines)
            nodes.append(self.render_aligned(block))

        return nodes

    def render_equality_proof(self, proof: Any) -> List[RenderNode]:
        """
        将 EqualityProof 转换为 Render IR 节点列表。

        关键：不再调用 proof.to_latex()，而是结构化构建。
        """
        nodes: List[RenderNode] = []

        proof_steps = getattr(proof, 'steps', [])
        if not proof_steps:
            return nodes

        aligned_lines = []
        for pstep in proof_steps:
            before = getattr(pstep, 'before', '') or ''
            after = getattr(pstep, 'after', '') or ''
            theorem = getattr(pstep, 'theorem', '') or ''

            if before and after:
                aligned_lines.append(AlignedLine(
                    content=f"{before} &= {after}",
                    annotation=theorem,
                ))
            elif after:
                aligned_lines.append(AlignedLine(
                    content=f"&= {after}",
                    annotation=theorem,
                ))

        conclusion = getattr(proof, 'conclusion', '') or ''
        if conclusion:
            aligned_lines.append(AlignedLine(
                content=f"&= \\boxed{{{conclusion}}}",
                annotation="",
            ))

        if aligned_lines:
            block = AlignedBlock(lines=aligned_lines)
            nodes.append(self.render_aligned(block))

        return nodes

    def render_rewrite_result(self, result: Any) -> List[RenderNode]:
        """
        将 RewriteResult 转换为 Render IR 节点列表。
        """
        nodes: List[RenderNode] = []

        expr = getattr(result, 'expr', None)
        if expr is not None:
            expr_latex = self._expr_to_latex(expr)
            if expr_latex:
                nodes.append(BlockMathNode(latex=expr_latex))

        trace = getattr(result, 'trace', None)
        if trace is not None:
            trace_nodes = self.render_proof_trace(trace)
            nodes.extend(trace_nodes)

        return nodes

    def _validate_and_fix(self, latex: str) -> str:
        if not latex:
            return latex
        result = self._validator.validate_and_fix(latex)
        return result.fixed_latex

    def _safe_get_latex(self, obj: Any, attr: str) -> str:
        val = getattr(obj, attr, None)
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        return self._expr_to_latex(val)

    def _expr_to_latex(self, expr: Any) -> str:
        if expr is None:
            return ""
        if isinstance(expr, str):
            return expr
        if hasattr(expr, 'to_latex'):
            try:
                return expr.to_latex()
            except Exception:
                return str(expr)
        return str(expr)
