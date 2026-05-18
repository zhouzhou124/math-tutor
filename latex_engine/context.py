"""Rewrite Context - 重写上下文系统

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  这是重写运行时的核心抽象。

  为什么需要 RewriteContext:
    - Memoization: ctx.memo
    - Proof Generation: ctx.trace
    - Cost-guided Search: ctx.cost_cache
    - Equality Saturation: ctx.egraph
    - Rewrite Budget: 防止无限循环

  原则1: Strategies Are Pure
    不要让 strategy 修改全局状态
    所有状态必须通过 ctx 显式传递

  原则2: Rewrite Is Search
    不要把 rewrite 看成 replacement
    而应该看成 search problem

  原则3: Proof Is Runtime Artifact
    Proof 不应该后生成
    而应该在 rewrite 时自然产生

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

    strategy.apply(expr, ctx)
           ↓
    ┌─────────────────────────┐
    │      RewriteContext     │
    │ ┌─────────────────────┐ │
    │ │ memo: {expr → result}│ │
    │ ├─────────────────────┤ │
    │ │ trace: RewriteTrace │ │
    │ ├─────────────────────┤ │
    │ │ cost_cache: {}      │ │
    │ ├─────────────────────┤ │
    │ │ egraph: EGraph      │ │
    │ ├─────────────────────┤ │
    │ │ budget: int         │ │
    │ ├─────────────────────┤ │
    │ │ statistics: {}      │ │
    │ └─────────────────────┘ │
    └─────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import OrderedDict
from time import time


# ═══════════════════════════════════════════════════════════
# Context Flags - 上下文标志
# ═══════════════════════════════════════════════════════════

class ContextMode(Enum):
    """重写上下文模式"""
    NORMAL = auto()           # 正常模式
    TRACE = auto()            # 完整追踪模式
    DEBUG = auto()            # 调试模式（额外信息）
    PROOF = auto()            # 证明生成模式
    OPTIMIZE = auto()         # 优化模式（最大缓存）


class TerminationReason(Enum):
    """终止原因"""
    FIXED_POINT = auto()      # 达到不动点
    BUDGET_EXHAUSTED = auto() # 预算耗尽
    MAX_ITERATIONS = auto()   # 达到最大迭代次数
    LOOP_DETECTED = auto()    # 检测到循环
    MANUAL = auto()           # 手动终止
    ERROR = auto()            # 错误终止


# ═══════════════════════════════════════════════════════════
# Statistics - 统计信息
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteStatistics:
    """重写统计信息"""
    rules_applied: int = 0
    rules_matched: int = 0
    rules_failed: int = 0
    rewrite_steps: int = 0
    memo_hits: int = 0
    memo_misses: int = 0
    cost_evaluations: int = 0
    time_elapsed: float = 0.0
    peak_memory: int = 0
    termination_reason: Optional[TerminationReason] = None
    cost_model: Optional['CostModel'] = None

    def reset(self):
        """重置统计"""
        self.__init__()

    def to_dict(self) -> dict:
        return {
            "rules_applied": self.rules_applied,
            "rules_matched": self.rules_matched,
            "rules_failed": self.rules_failed,
            "rewrite_steps": self.rewrite_steps,
            "memo_hits": self.memo_hits,
            "memo_misses": self.memo_misses,
            "cost_evaluations": self.cost_evaluations,
            "time_elapsed": round(self.time_elapsed, 4),
            "termination_reason": self.termination_reason.name if self.termination_reason else None,
        }


# ═══════════════════════════════════════════════════════════
# Cost Cache - 代价缓存
# ═══════════════════════════════════════════════════════════

class CostCache:
    """代价缓存 - 避免重复计算表达式代价"""

    def __init__(self):
        self._cache: Dict[int, float] = {}

    def get(self, expr_hash: int) -> Optional[float]:
        return self._cache.get(expr_hash)

    def set(self, expr_hash: int, cost: float):
        self._cache[expr_hash] = cost

    def clear(self):
        self._cache.clear()

    def __len__(self):
        return len(self._cache)


# ═══════════════════════════════════════════════════════════
# Memo Table - 记忆化表
# ═══════════════════════════════════════════════════════════

class MemoTable:
    """记忆化表 - 缓存重写结果"""

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[int, Any] = OrderedDict()
        self._max_size = max_size

    def get(self, key: int) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            # 移动到末尾表示最近使用
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: int, value: Any):
        """设置缓存值"""
        if len(self._cache) >= self._max_size:
            # 删除最久未使用的
            self._cache.popitem(last=False)
        self._cache[key] = value
        self._cache.move_to_end(key)

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def __contains__(self, key: int) -> bool:
        return key in self._cache

    def __len__(self):
        return len(self._cache)


# ═══════════════════════════════════════════════════════════
# RewriteContext - 重写上下文
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteContext:
    """
    重写上下文 - 重写运行时的核心状态容器。

    包含:
      - memo: 记忆化缓存
      - trace: 重写追踪记录
      - cost_cache: 代价计算缓存
      - budget: 重写预算（防止无限循环）
      - statistics: 统计信息
      - options: 配置选项

    设计原则:
      1. 所有状态显式传递（策略纯函数）
      2. 支持多种模式（正常/追踪/调试/证明）
      3. 内置预算管理
      4. 可观测性（统计信息）
    """

    # 记忆化
    memo: MemoTable = field(default_factory=MemoTable)
    
    # 追踪系统
    trace: Optional['RewriteTrace'] = None
    
    # 代价缓存
    cost_cache: CostCache = field(default_factory=CostCache)
    
    # 预算控制
    budget: int = 1000
    steps_remaining: int = 1000
    
    # 统计信息
    statistics: RewriteStatistics = field(default_factory=RewriteStatistics)
    
    # 配置选项
    mode: ContextMode = ContextMode.NORMAL
    max_iterations: int = 100
    allow_loop: bool = False
    
    # 访问记录（防循环）
    visited: Set[int] = field(default_factory=set)
    
    # 时间追踪
    start_time: float = 0.0
    
    # 自定义数据
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.trace is None and self.mode in (ContextMode.TRACE, ContextMode.PROOF):
            from .trace import RewriteTrace
            self.trace = RewriteTrace()
        self.start_time = time()

    # ───────────────────────────────────────────────────────
    # 预算管理
    # ───────────────────────────────────────────────────────

    def consume_budget(self, amount: int = 1) -> bool:
        """消耗预算，返回是否可以继续"""
        self.steps_remaining -= amount
        self.statistics.rewrite_steps += amount
        return self.steps_remaining > 0

    def is_budget_exhausted(self) -> bool:
        """预算是否耗尽"""
        return self.steps_remaining <= 0

    def should_continue(self) -> bool:
        """是否应该继续重写"""
        return not self.is_budget_exhausted()

    def reset_budget(self, budget: Optional[int] = None):
        """重置预算"""
        if budget is not None:
            self.budget = budget
        self.steps_remaining = self.budget

    # ───────────────────────────────────────────────────────
    # 循环检测
    # ───────────────────────────────────────────────────────

    def mark_visited(self, expr_hash: int):
        """标记表达式已访问"""
        self.visited.add(expr_hash)

    def has_visited(self, expr_hash: int) -> bool:
        """检查表达式是否已访问"""
        return expr_hash in self.visited

    def clear_visited(self):
        """清空访问记录"""
        self.visited.clear()

    # ───────────────────────────────────────────────────────
    # 记忆化
    # ───────────────────────────────────────────────────────

    def memoize(self, expr_hash: int, result: Any):
        """记忆化重写结果"""
        self.memo.set(expr_hash, result)
        self.statistics.memo_misses += 1

    def lookup_memo(self, expr_hash: int) -> Optional[Any]:
        """查找记忆化结果"""
        result = self.memo.get(expr_hash)
        if result is not None:
            self.statistics.memo_hits += 1
        return result

    # ───────────────────────────────────────────────────────
    # 追踪
    # ───────────────────────────────────────────────────────

    def should_trace(self) -> bool:
        """是否应该追踪"""
        return self.mode in (ContextMode.TRACE, ContextMode.PROOF, ContextMode.DEBUG)

    def add_trace_step(self, step: 'RewriteStep'):
        """添加追踪步骤"""
        if self.trace is not None:
            self.trace.add_step(step)

    # ───────────────────────────────────────────────────────
    # 统计
    # ───────────────────────────────────────────────────────

    def finalize(self, reason: TerminationReason):
        """完成重写，记录统计"""
        self.statistics.termination_reason = reason
        self.statistics.time_elapsed = time() - self.start_time

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self.statistics.to_dict()

    # ───────────────────────────────────────────────────────
    # 复制
    # ───────────────────────────────────────────────────────

    def fork(self) -> 'RewriteContext':
        """创建上下文副本（用于分支搜索）"""
        return RewriteContext(
            memo=MemoTable(),  # 新的 memo，避免污染
            trace=self.trace,
            cost_cache=self.cost_cache,
            budget=self.budget,
            steps_remaining=self.steps_remaining,
            statistics=RewriteStatistics(),
            mode=self.mode,
            max_iterations=self.max_iterations,
            allow_loop=self.allow_loop,
            visited=set(),  # 不复制 visited，每个分支有独立的访问历史
            start_time=time(),
            extra=dict(self.extra),
        )

    # ───────────────────────────────────────────────────────
    # 上下文管理器
    # ───────────────────────────────────────────────────────

    def __enter__(self):
        self.start_time = time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finalize(TerminationReason.FIXED_POINT)
        else:
            self.finalize(TerminationReason.ERROR)

    def __repr__(self):
        return f"RewriteContext(mode={self.mode.name}, budget={self.steps_remaining}/{self.budget})"


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def create_trace_context(budget: int = 1000) -> RewriteContext:
    """创建追踪模式上下文"""
    return RewriteContext(
        mode=ContextMode.TRACE,
        budget=budget,
    )


def create_proof_context(budget: int = 1000) -> RewriteContext:
    """创建证明模式上下文"""
    return RewriteContext(
        mode=ContextMode.PROOF,
        budget=budget,
    )


def create_debug_context(budget: int = 1000) -> RewriteContext:
    """创建调试模式上下文"""
    return RewriteContext(
        mode=ContextMode.DEBUG,
        budget=budget,
    )


def create_optimize_context(budget: int = 10000) -> RewriteContext:
    """创建优化模式上下文"""
    return RewriteContext(
        mode=ContextMode.OPTIMIZE,
        budget=budget,
    )
