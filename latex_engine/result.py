"""Rewrite Result - 重写结果系统

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  重写结果不只是表达式，还包含:
    - 追踪信息
    - 统计信息
    - 代价信息
    - 证明对象

  这使得:
    - 可解释性
    - 证明生成
    - 调试支持
    - 性能分析

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

    strategy.apply(expr, ctx)
           ↓
    ┌─────────────────────────┐
    │     RewriteResult       │
    │  - expr: Expr          │
    │  - changed: bool       │
    │  - trace: RewriteTrace │
    │  - statistics: {}      │
    │  - cost: float         │
    │  - proof: Proof        │
    └─────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from copy import deepcopy


# ═══════════════════════════════════════════════════════════
# RewriteResult - 重写结果
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteResult:
    """
    重写结果 - 包含表达式、追踪和统计信息。
    
    设计目标:
      1. 包含最终表达式
      2. 包含完整追踪记录
      3. 包含统计信息
      4. 支持证明生成
      5. 支持调试和分析
    """

    expr: Any
    changed: bool
    trace: Optional['RewriteTrace'] = None
    statistics: Dict[str, Any] = field(default_factory=dict)
    cost: Optional[float] = None
    rule_name: Optional[str] = None
    depth: int = 0
    branch_id: Optional[str] = None

    @property
    def has_trace(self) -> bool:
        """是否有追踪记录"""
        return self.trace is not None and self.trace.length > 0

    @property
    def trace_length(self) -> int:
        """追踪长度"""
        return self.trace.length if self.trace else 0

    @property
    def rules_used(self) -> List[str]:
        """使用的规则列表"""
        return self.trace.rules_used if self.trace else []

    @property
    def is_optimized(self) -> bool:
        """是否达到最优"""
        return self.cost is not None

    # ───────────────────────────────────────────────────────
    # 转换方法
    # ───────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "expr": str(self.expr),
            "changed": self.changed,
            "cost": self.cost,
            "rule_name": self.rule_name,
            "depth": self.depth,
            "trace_length": self.trace_length,
            "statistics": self.statistics,
            "has_trace": self.has_trace,
            "rules_used": self.rules_used,
        }

    def to_proof(self) -> Optional['EqualityProof']:
        """转换为证明对象"""
        if self.trace:
            return self.trace.to_proof()
        return None

    def to_latex(self) -> str:
        """导出为 LaTeX"""
        if hasattr(self.expr, 'to_latex'):
            return self.expr.to_latex()
        return str(self.expr)

    def to_markdown(self) -> str:
        """导出为 Markdown"""
        lines = []
        lines.append(f"**Result:** `${self.to_latex()}`")
        lines.append(f"**Changed:** {'Yes' if self.changed else 'No'}")
        if self.cost is not None:
            lines.append(f"**Cost:** {self.cost:.2f}")
        if self.rule_name:
            lines.append(f"**Rule:** {self.rule_name}")
        if self.has_trace:
            lines.append("")
            lines.append(self.trace.to_markdown())
        return "\n".join(lines)

    # ───────────────────────────────────────────────────────
    # 组合方法
    # ───────────────────────────────────────────────────────

    def chain(self, other: 'RewriteResult') -> 'RewriteResult':
        """链接两个重写结果"""
        new_expr = other.expr
        new_changed = self.changed or other.changed
        new_cost = other.cost
        
        # 合并追踪
        new_trace = None
        if self.trace and other.trace:
            new_trace = deepcopy(self.trace)
            new_trace.steps.extend(other.trace.steps)
            new_trace.final_expr = other.expr
        elif other.trace:
            new_trace = deepcopy(other.trace)
        elif self.trace:
            new_trace = deepcopy(self.trace)
            new_trace.final_expr = other.expr
        
        # 合并统计
        new_stats = {}
        for key in set(self.statistics.keys()) | set(other.statistics.keys()):
            val1 = self.statistics.get(key, 0)
            val2 = other.statistics.get(key, 0)
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                new_stats[key] = val1 + val2
            else:
                new_stats[key] = val2 if val2 else val1
        
        return RewriteResult(
            expr=new_expr,
            changed=new_changed,
            trace=new_trace,
            statistics=new_stats,
            cost=new_cost,
            depth=self.depth + other.depth,
        )

    # ───────────────────────────────────────────────────────
    # 便捷方法
    # ───────────────────────────────────────────────────────

    def copy(self) -> 'RewriteResult':
        """复制结果"""
        return RewriteResult(
            expr=self.expr,
            changed=self.changed,
            trace=deepcopy(self.trace),
            statistics=dict(self.statistics),
            cost=self.cost,
            rule_name=self.rule_name,
            depth=self.depth,
            branch_id=self.branch_id,
        )

    def __repr__(self):
        cost_str = f", cost={self.cost:.2f}" if self.cost else ""
        trace_str = f", trace={self.trace_length} steps" if self.has_trace else ""
        return f"RewriteResult(changed={self.changed}{cost_str}{trace_str})"


# ═══════════════════════════════════════════════════════════
# SearchResult - 搜索结果
# ═══════════════════════════════════════════════════════════

@dataclass
class SearchResult:
    """
    搜索结果 - 包含多个候选结果。
    
    用于:
      - ChoiceStrategy 的多选项
      - 代价优化搜索
      - 分支定界搜索
    """

    candidates: List[RewriteResult] = field(default_factory=list)
    best: Optional[RewriteResult] = None
    search_depth: int = 0
    explored_count: int = 0

    @property
    def has_best(self) -> bool:
        return self.best is not None

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0

    def add_candidate(self, result: RewriteResult):
        """添加候选结果"""
        self.candidates.append(result)

    def select_best(self, cost_model=None):
        """选择最优候选"""
        if not self.candidates:
            return None
        
        if self.candidates[0].cost is None:
            self.best = self.candidates[0]
            return self.best
        
        # 按代价排序
        sorted_candidates = sorted(self.candidates, key=lambda r: r.cost or float('inf'))
        self.best = sorted_candidates[0]
        return self.best

    def to_dict(self) -> dict:
        return {
            "candidates_count": len(self.candidates),
            "has_best": self.has_best,
            "search_depth": self.search_depth,
            "explored_count": self.explored_count,
            "best": self.best.to_dict() if self.best else None,
        }

    def __repr__(self):
        return f"SearchResult(candidates={len(self.candidates)}, best={self.best is not None})"


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def unchanged_result(expr: Any) -> RewriteResult:
    """创建未变化的结果"""
    return RewriteResult(expr=expr, changed=False)


def changed_result(expr: Any, **kwargs) -> RewriteResult:
    """创建已变化的结果"""
    return RewriteResult(expr=expr, changed=True, **kwargs)


def failed_result(expr: Any) -> RewriteResult:
    """创建失败结果"""
    return RewriteResult(expr=expr, changed=False)
