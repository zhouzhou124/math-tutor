"""Rewrite Trace - 重写追踪系统

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  这是证明生成的核心基础设施。

  现在: expr -> expr'
  未来: expr --rule--> expr'

  然后: proof_step

  最终:
    Rewrite Trace
        ↓
    Proof Object
        ↓
    Verified Proof

  Rule = What transformations are legal
  Strategy = Which transformations are desirable
  Trace = Why this transformation was chosen

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

    strategy.apply(expr, ctx)
           ↓
    ┌─────────────────────────┐
    │     RewriteStep         │
    │  - rule: str           │
    │  - before: Expr        │
    │  - after: Expr         │
    │  - position: Path      │
    │  - cost_before: float  │
    │  - cost_after: float   │
    │  - reason: str         │
    └─────────────────────────┘
           ↓
    ┌─────────────────────────┐
    │     RewriteTrace        │
    │  - steps: [Step]       │
    │  - branches: []        │
    │  - final_expr          │
    └─────────────────────────┘
           ↓
    ┌─────────────────────────┐
    │    EqualityProof        │
    │  - steps: [ProofStep]  │
    │  - theorem_refs        │
    └─────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union
from copy import deepcopy


# ═══════════════════════════════════════════════════════════
# Trace Location - 追踪位置
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PathElement:
    """路径元素 - 表示表达式树中的位置"""
    index: int
    role: str  # 'arg', 'left', 'right', 'base', 'exponent', 'operand', etc.

    def __repr__(self):
        return f"{self.role}[{self.index}]"


class RewriteLocation:
    """重写位置 - 表达式树中的路径"""

    def __init__(self, path: List[PathElement] = None):
        self.path = path or []

    def push(self, role: str, index: int = 0):
        """添加路径元素"""
        self.path.append(PathElement(index=index, role=role))
        return self

    def pop(self):
        """移除最后一个路径元素"""
        if self.path:
            return self.path.pop()
        return None

    def clone(self):
        """克隆路径"""
        return RewriteLocation(list(self.path))

    def to_string(self) -> str:
        """转换为字符串表示"""
        if not self.path:
            return "."
        return "." + ".".join(str(e) for e in self.path)

    def __repr__(self):
        return self.to_string()


# ═══════════════════════════════════════════════════════════
# RewriteStep - 重写步骤
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteStep:
    """
    重写步骤 - 记录单次规则应用。

    这是证明生成的基础单元。
    
    记录:
      - rule: 应用的规则名称
      - before: 重写前的表达式
      - after: 重写后的表达式
      - position: 重写发生的位置
      - cost_before/after: 代价变化
      - reason: 选择此规则的原因
      - confidence: 置信度
      - dependencies: 依赖的事实/约束
    """

    rule: str
    before: Any  # Expr
    after: Any   # Expr
    position: RewriteLocation = field(default_factory=RewriteLocation)
    cost_before: float = 0.0
    cost_after: float = 0.0
    reason: str = ""
    confidence: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    branch_id: Optional[str] = None
    timestamp: float = 0.0

    @property
    def cost_delta(self) -> float:
        return self.cost_after - self.cost_before

    @property
    def is_improvement(self) -> bool:
        return self.cost_after < self.cost_before

    @property
    def before_str(self) -> str:
        if isinstance(self.before, str):
            return self.before
        if hasattr(self.before, 'to_latex'):
            try:
                return self.before.to_latex()
            except Exception:
                return str(self.before)
        return str(self.before)

    @property
    def after_str(self) -> str:
        if isinstance(self.after, str):
            return self.after
        if hasattr(self.after, 'to_latex'):
            try:
                return self.after.to_latex()
            except Exception:
                return str(self.after)
        return str(self.after)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "before": self.before_str,
            "after": self.after_str,
            "position": self.position.to_string(),
            "cost_before": self.cost_before,
            "cost_after": self.cost_after,
            "cost_delta": self.cost_delta,
            "reason": self.reason,
            "confidence": self.confidence,
            "dependencies": self.dependencies,
        }

    def __repr__(self):
        return f"RewriteStep({self.rule}: {self.before_str} → {self.after_str})"


# ═══════════════════════════════════════════════════════════
# RewriteBranch - 重写分支
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteBranch:
    """
    重写分支 - 记录搜索过程中的分支选择。
    
    用于:
      - ChoiceStrategy 的多选项尝试
      - 回溯搜索
      - 并行策略评估
    """

    branch_id: str
    steps: List[RewriteStep] = field(default_factory=list)
    final_expr: Any = None
    final_cost: float = float('inf')
    is_selected: bool = False
    reason: str = ""

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def cost_improvement(self) -> float:
        if not self.steps:
            return 0.0
        first = self.steps[0]
        return first.cost_before - self.final_cost

    def add_step(self, step: RewriteStep):
        step.branch_id = self.branch_id
        self.steps.append(step)

    def to_dict(self) -> dict:
        return {
            "branch_id": self.branch_id,
            "length": self.length,
            "final_cost": self.final_cost,
            "is_selected": self.is_selected,
            "reason": self.reason,
            "steps": [s.to_dict() for s in self.steps],
        }


# ═══════════════════════════════════════════════════════════
# RewriteTrace - 重写追踪
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteTrace:
    """
    重写追踪 - 完整的重写过程记录。

    职责:
      1. 记录所有重写步骤
      2. 管理分支搜索
      3. 生成证明对象
      4. 支持调试和分析

    设计:
      - 线性步骤序列（主路径）
      - 可选的分支记录
      - 可导出为多种格式
    """

    steps: List[RewriteStep] = field(default_factory=list)
    branches: List[RewriteBranch] = field(default_factory=list)
    initial_expr: Any = None
    final_expr: Any = None
    strategy_name: str = ""

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0

    @property
    def total_cost_improvement(self) -> float:
        if not self.steps:
            return 0.0
        first = self.steps[0]
        last = self.steps[-1]
        return first.cost_before - last.cost_after

    @property
    def rules_used(self) -> List[str]:
        return list({s.rule for s in self.steps})

    # ───────────────────────────────────────────────────────
    # 步骤管理
    # ───────────────────────────────────────────────────────

    def add_step(self, step: RewriteStep):
        """添加重写步骤"""
        self.steps.append(step)

    def insert_step(self, index: int, step: RewriteStep):
        """在指定位置插入步骤"""
        self.steps.insert(index, step)

    def clear(self):
        """清空追踪"""
        self.steps.clear()
        self.branches.clear()
        self.initial_expr = None
        self.final_expr = None

    # ───────────────────────────────────────────────────────
    # 分支管理
    # ───────────────────────────────────────────────────────

    def create_branch(self, branch_id: str) -> RewriteBranch:
        """创建新分支"""
        branch = RewriteBranch(branch_id=branch_id)
        self.branches.append(branch)
        return branch

    def select_branch(self, branch_id: str):
        """选择最优分支"""
        for branch in self.branches:
            branch.is_selected = (branch.branch_id == branch_id)

    # ───────────────────────────────────────────────────────
    # 导出
    # ───────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "strategy": self.strategy_name,
            "length": self.length,
            "total_cost_improvement": self.total_cost_improvement,
            "rules_used": self.rules_used,
            "steps": [s.to_dict() for s in self.steps],
            "branches": [b.to_dict() for b in self.branches],
        }

    def to_latex(self) -> str:
        """导出为 LaTeX 证明格式（结构化构建 + 验证）"""
        if not self.steps:
            return ""

        try:
            from rendering.structured_latex_renderer import AlignedBlock, AlignedLine
            from rendering.latex_validator import LaTeXValidator

            aligned_lines = []
            for i, step in enumerate(self.steps, 1):
                before = self._safe_expr_latex(step.before)
                after = self._safe_expr_latex(step.after)
                rule = step.rule or ""

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

            if self.final_expr is not None:
                final_str = self._safe_expr_latex(self.final_expr)
                if final_str:
                    aligned_lines.append(AlignedLine(
                        content=f"&= \\boxed{{{final_str}}}",
                        annotation="",
                    ))

            block = AlignedBlock(lines=aligned_lines)
            full_latex = block.to_full_latex()

            validator = LaTeXValidator()
            result = validator.validate_and_fix(full_latex)
            return result.fixed_latex

        except ImportError:
            return self._to_latex_fallback()

    @staticmethod
    def _safe_expr_latex(expr) -> str:
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

    def _to_latex_fallback(self) -> str:
        if not self.steps:
            return ""
        lines = ["\\begin{align*}"]
        for step in self.steps:
            before = self._safe_expr_latex(step.before)
            after = self._safe_expr_latex(step.after)
            if before and after:
                lines.append(f"    {before} &= {after} \\quad \\text{{({step.rule})}}")
            elif after:
                lines.append(f"    &= {after} \\quad \\text{{({step.rule})}}")
        if self.final_expr is not None:
            final_str = self._safe_expr_latex(self.final_expr)
            if final_str:
                lines.append(f"    &= {final_str}")
        lines.append("\\end{align*}")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """导出为 Markdown"""
        lines = ["## Rewrite Trace", ""]
        
        if self.strategy_name:
            lines.append(f"**Strategy:** {self.strategy_name}")
        
        lines.append(f"**Steps:** {self.length}")
        lines.append(f"**Rules Used:** {', '.join(self.rules_used)}")
        lines.append("")
        lines.append("### Step-by-Step")
        lines.append("")
        
        for i, step in enumerate(self.steps, 1):
            lines.append(f"**Step {i}:** `{step.rule}`")
            lines.append(f"  {step.before_str} → {step.after_str}")
            if step.reason:
                lines.append(f"  *Reason:* {step.reason}")
            if step.dependencies:
                lines.append(f"  *Dependencies:* {', '.join(step.dependencies)}")
            lines.append("")
        
        if self.branches:
            lines.append("### Branches")
            lines.append("")
            for branch in self.branches:
                status = "✓" if branch.is_selected else "✗"
                lines.append(f"**{status} Branch {branch.branch_id}:**")
                lines.append(f"  Steps: {branch.length}, Final Cost: {branch.final_cost}")
                if branch.is_selected:
                    lines.append(f"  *Selected because:* {branch.reason}")
                lines.append("")
        
        return "\n".join(lines)

    def to_proof(self) -> 'EqualityProof':
        """转换为证明对象"""
        return EqualityProof.from_trace(self)

    # ───────────────────────────────────────────────────────
    # 调试
    # ───────────────────────────────────────────────────────

    def print_summary(self):
        """打印摘要"""
        print(f"=== Rewrite Trace Summary ===")
        print(f"Strategy: {self.strategy_name}")
        print(f"Steps: {self.length}")
        print(f"Rules Used: {', '.join(self.rules_used)}")
        print(f"Cost Improvement: {self.total_cost_improvement:.2f}")
        print(f"Branches: {len(self.branches)}")
        print()

    def print_detailed(self):
        """打印详细步骤"""
        self.print_summary()
        print("--- Steps ---")
        for i, step in enumerate(self.steps, 1):
            print(f"Step {i}:")
            print(f"  Rule: {step.rule}")
            print(f"  Before: {step.before_str}")
            print(f"  After: {step.after_str}")
            print(f"  Position: {step.position}")
            print(f"  Cost: {step.cost_before:.2f} → {step.cost_after:.2f} ({step.cost_delta:+.2f})")
            if step.reason:
                print(f"  Reason: {step.reason}")
            print()

    def __repr__(self):
        return f"RewriteTrace(steps={self.length}, branches={len(self.branches)})"


# ═══════════════════════════════════════════════════════════
# EqualityProof - 等式证明
# ═══════════════════════════════════════════════════════════

@dataclass
class ProofStep:
    """
    证明步骤 - 带定理引用的重写步骤。
    
    将重写步骤提升为正式证明步骤。
    """

    before: str
    after: str
    theorem: str
    theorem_ref: Optional[str] = None
    justification: str = ""

    def to_latex(self) -> str:
        ref = f"\\cite{{{self.theorem_ref}}}" if self.theorem_ref else ""
        return f"{self.before} &= {self.after} \\quad \\text{{({self.theorem})}} {ref}"


@dataclass
class EqualityProof:
    """
    等式证明 - 正式的数学证明对象。
    
    由 RewriteTrace 转换而来，可用于:
      - 证明验证
      - 证明检查
      - 证明导出（Isabelle/Coq/Ledger）
    """

    steps: List[ProofStep] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    conclusion: str = ""
    theorem_refs: List[str] = field(default_factory=list)

    @classmethod
    def from_trace(cls, trace: RewriteTrace) -> 'EqualityProof':
        proof = EqualityProof()

        for step in trace.steps:
            before = RewriteTrace._safe_expr_latex(step.before)
            after = RewriteTrace._safe_expr_latex(step.after)
            proof.steps.append(ProofStep(
                before=before,
                after=after,
                theorem=step.rule,
                justification=step.reason,
            ))

        if trace.final_expr is not None:
            proof.conclusion = RewriteTrace._safe_expr_latex(trace.final_expr)

        proof.theorem_refs = trace.rules_used

        return proof

    def to_latex(self) -> str:
        """导出为 LaTeX 证明环境（结构化构建 + 验证）"""
        try:
            from rendering.structured_latex_renderer import AlignedBlock, AlignedLine, ProofIR, ProofStepIR
            from rendering.latex_validator import LaTeXValidator

            proof_steps = []
            for step in self.steps:
                proof_steps.append(ProofStepIR(
                    before=step.before or "",
                    after=step.after or "",
                    rule=step.theorem or "",
                    rule_ref=step.theorem_ref or "",
                ))

            proof_ir = ProofIR(
                steps=proof_steps,
                conclusion=self.conclusion or "",
                assumptions=list(self.assumptions) if self.assumptions else [],
                strategy="direct",
            )

            aligned = proof_ir.to_aligned_block()
            full_latex = aligned.to_full_latex()

            if not full_latex:
                return ""

            validator = LaTeXValidator()
            result = validator.validate_and_fix(full_latex)
            return result.fixed_latex

        except ImportError:
            return self._to_latex_fallback()

    def _to_latex_fallback(self) -> str:
        lines = ["\\begin{align*}"]
        for step in self.steps:
            if step.before and step.after:
                lines.append(f"    {step.before} &= {step.after} \\quad \\text{{({step.theorem})}}")
            elif step.after:
                lines.append(f"    &= {step.after} \\quad \\text{{({step.theorem})}}")
        if self.conclusion:
            lines.append(f"    &= \\boxed{{{self.conclusion}}}")
        lines.append("\\end{align*}")
        return "\n".join(lines)

    def verify(self) -> bool:
        """验证证明（简化版本）"""
        # 实际实现需要调用定理证明器
        return len(self.steps) > 0

    def __repr__(self):
        return f"EqualityProof(steps={len(self.steps)}, conclusion={self.conclusion[:30]}...)"
