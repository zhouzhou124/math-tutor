"""Rewrite Strategy System - 重写策略系统

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  这是整个数学推理引擎的核心控制系统。

  不再是简单的 "try all rules until one matches"
  而是 "guided search through strategy composition"

  策略类型：
  - BottomUp: 从叶节点开始应用规则
  - TopDown: 从根节点开始应用规则
  - Repeat: 重复应用直到不动点
  - Choice: 多规则择优选择
  - Sequence: 顺序组合多个策略
  - Fixpoint: 不动点迭代
  - Conditional: 条件重写
  - CostBased: 基于代价的优化

  这是 Mathematica / Stratego / Maude 的核心架构。

═══════════════════════════════════════════════════════════════
关键更新
═══════════════════════════════════════════════════════════════

  1. 策略是纯函数 - 所有状态通过 RewriteContext 传递
  2. 支持完整追踪 - 自动记录重写步骤
  3. 内置预算管理 - 防止无限循环
  4. 支持记忆化 - 提高性能

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Callable, Union
from dataclasses import dataclass
from enum import Enum, auto
from time import time

from .canonical_ir import Expr, Op, ExprCache
from .context import RewriteContext, ContextMode, TerminationReason
from .trace import RewriteStep, RewriteLocation
from .result import RewriteResult, changed_result, unchanged_result


# ═══════════════════════════════════════════════════════════
# Cost Model - 代价模型
# ═══════════════════════════════════════════════════════════

class CostModel(ABC):
    """代价模型抽象 - 决定哪个重写结果更优"""

    @abstractmethod
    def cost(self, expr: Expr) -> float:
        """计算表达式的代价"""
        pass

    @abstractmethod
    def compare(self, a: Expr, b: Expr) -> int:
        """比较两个表达式的好坏
        返回: -1 if a < b, 0 if equal, 1 if a > b
        """
        pass


class DefaultCostModel(CostModel):
    """默认代价模型

    考虑因素:
    - 节点数量
    - 操作符复杂度
    - 深度
    - 符号复杂度
    """

    def cost(self, expr: Expr) -> float:
        """计算表达式代价"""
        if expr.op in (Op.SYMBOL, Op.NUMBER):
            return 1.0

        cost = 0.0
        for arg in expr.args:
            cost += self.cost(arg)

        op_costs = {
            Op.ADD: 1.0,
            Op.SUB: 1.5,
            Op.MUL: 1.2,
            Op.DIV: 1.5,
            Op.NEG: 1.0,
            Op.POW: 2.0,
            Op.SIN: 3.0,
            Op.COS: 3.0,
            Op.TAN: 3.0,
            Op.EXP: 3.0,
            Op.LOG: 3.0,
            Op.LN: 3.0,
            Op.SQRT: 2.5,
            Op.ABS: 2.0,
        }

        cost += op_costs.get(expr.op, 1.5)

        if expr.op in (Op.ADD, Op.MUL):
            cost -= 0.1 * (len(expr.args) - 1)

        return cost

    def compare(self, a: Expr, b: Expr) -> int:
        """比较两个表达式的好坏"""
        cost_a = self.cost(a)
        cost_b = self.cost(b)
        if cost_a < cost_b:
            return -1
        elif cost_a > cost_b:
            return 1
        return 0


class ProofComplexityModel(CostModel):
    """证明复杂度代价模型

    优先产生：
    - 更少的步骤
    - 更短的证明
    - 更基础的数学事实
    """

    def cost(self, expr: Expr) -> float:
        if expr.op in (Op.SYMBOL, Op.NUMBER):
            return 1.0

        cost = 0.0
        for arg in expr.args:
            cost += self.cost(arg)

        if expr.op == Op.ADD:
            num_zeros = sum(1 for a in expr.args
                          if a.op == Op.NUMBER and float(a.args[0]) == 0)
            cost -= num_zeros * 2.0

        if expr.op == Op.MUL:
            num_ones = sum(1 for a in expr.args
                         if a.op == Op.NUMBER and float(a.args[0]) == 1)
            cost -= num_ones * 2.0

        return cost

    def compare(self, a: Expr, b: Expr) -> int:
        cost_a = self.cost(a)
        cost_b = self.cost(b)
        if cost_a < cost_b:
            return -1
        elif cost_a > cost_b:
            return 1
        return 0


# ═══════════════════════════════════════════════════════════
# Strategy - 策略基类
# ═══════════════════════════════════════════════════════════

class Strategy(ABC):
    """重写策略基类

    核心原则:
      1. 策略是纯函数 - 不修改全局状态
      2. 所有状态通过 RewriteContext 传递
      3. 支持追踪和证明生成
    """

    def apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        """应用策略"""
        if not context.consume_budget():
            return unchanged_result(expr)
        
        # 检查记忆化
        expr_hash = hash(expr)
        cached = context.lookup_memo(expr_hash)
        if cached is not None:
            return cached
        
        # 检查循环
        if context.has_visited(expr_hash):
            return unchanged_result(expr)
        context.mark_visited(expr_hash)
        
        # 调用子类实现
        result = self._apply(expr, context)
        
        # 记忆化结果
        context.memoize(expr_hash, result)
        
        return result

    @abstractmethod
    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        """子类实现的核心应用逻辑"""
        pass

    def __or__(self, other: Strategy) -> 'SequenceStrategy':
        """组合策略: s1 | s2 表示顺序应用"""
        return SequenceStrategy([self, other])

    def __and__(self, other: Strategy) -> 'ChoiceStrategy':
        """选择策略: s1 & s2 表示选择最优"""
        return ChoiceStrategy([self, other])

    def __call__(self, expr: Expr, context: Optional[RewriteContext] = None) -> RewriteResult:
        """使策略可调用"""
        if context is None:
            context = RewriteContext()
        return self.apply(expr, context)


# ═══════════════════════════════════════════════════════════
# Primitive Strategies - 基础策略
# ═══════════════════════════════════════════════════════════

class BottomUpStrategy(Strategy):
    """自底向上策略

    先重写子节点，再重写当前节点。
    适合：规范化、简化。
    """

    def __init__(self, rule_set: 'RuleSet', name: str = "BottomUp"):
        self.rule_set = rule_set
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        changed = False
        current = expr
        location = RewriteLocation()
        cost_before = context.cost_cache.get(hash(expr))
        if cost_before is None:
            cost_before = context.statistics.cost_model.cost(expr) if context.statistics.cost_model else 0.0
            context.cost_cache.set(hash(expr), cost_before)

        # 对于 GROUP 表达式，直接处理其内部表达式并移除 GROUP 包装
        if expr.op == Op.GROUP:
            if len(expr.args) > 0:
                result = BottomUpStrategy(self.rule_set)._apply(expr.args[0], context)
                # 移除 GROUP 包装，直接返回内部表达式
                return changed_result(result.expr, cost=context.statistics.cost_model.cost(result.expr) if context.statistics.cost_model else 0.0, depth=1)
            return unchanged_result(current)

        # 对于原子表达式（SYMBOL 和 NUMBER），直接尝试应用规则
        if expr.op in (Op.SYMBOL, Op.NUMBER):
            for rule in self.rule_set.rules:
                result = rule.apply(current)
                if result is not None:
                    cost_after = context.statistics.cost_model.cost(result) if context.statistics.cost_model else 0.0
                    context.cost_cache.set(hash(result), cost_after)
                    
                    if context.should_trace():
                        step = RewriteStep(
                            rule=rule.name,
                            before=current,
                            after=result,
                            position=location,
                            cost_before=cost_before,
                            cost_after=cost_after,
                            reason=f"应用规则 {rule.name}",
                        )
                        context.add_trace_step(step)
                    
                    context.statistics.rules_applied += 1
                    return changed_result(
                        result,
                        rule_name=rule.name,
                        cost=cost_after,
                        depth=1,
                    )
            return unchanged_result(current)

        # 递归处理子节点
        new_args = []
        for i, arg in enumerate(expr.args):
            sub_location = location.clone().push('arg', i)
            result = BottomUpStrategy(self.rule_set)._apply(arg, context)
            new_args.append(result.expr)
            if result.changed:
                changed = True

        # 重建表达式
        if changed:
            current = self._rebuild_expr(expr, new_args)

        # 尝试应用规则
        for rule in self.rule_set.rules:
            result = rule.apply(current)
            if result is not None:
                cost_after = context.statistics.cost_model.cost(result) if context.statistics.cost_model else 0.0
                context.cost_cache.set(hash(result), cost_after)
                
                # 记录追踪
                if context.should_trace():
                    step = RewriteStep(
                        rule=rule.name,
                        before=current,
                        after=result,
                        position=location,
                        cost_before=cost_before,
                        cost_after=cost_after,
                        reason=f"应用规则 {rule.name}",
                    )
                    context.add_trace_step(step)
                
                context.statistics.rules_applied += 1
                return changed_result(
                    result,
                    rule_name=rule.name,
                    cost=cost_after,
                    depth=1,
                )

        # 对于多元的 ADD/MUL 表达式，尝试在子表达式上应用规则
        if current.op in (Op.ADD, Op.MUL) and len(current.args) > 2:
            for i, arg in enumerate(current.args):
                for rule in self.rule_set.rules:
                    # 创建一个二元子表达式来测试规则
                    if i == 0:
                        # 取第一个和第二个参数
                        if len(current.args) > 1:
                            sub_expr = ExprCache.add([arg, current.args[1]]) if current.op == Op.ADD else ExprCache.mul([arg, current.args[1]])
                    else:
                        # 取当前参数和第一个参数（保持顺序）
                        sub_expr = ExprCache.add([current.args[0], arg]) if current.op == Op.ADD else ExprCache.mul([current.args[0], arg])
                    
                    result = rule.apply(sub_expr)
                    if result is not None:
                        # 规则匹配成功，需要更新原表达式
                        new_args = list(current.args)
                        if i == 0:
                            # 替换第一个参数为结果，移除第二个参数
                            new_args[0] = result
                            new_args.pop(1)
                        else:
                            # 替换第一个参数为结果，移除当前参数
                            new_args[0] = result
                            new_args.pop(i)
                        
                        # 重建表达式
                        new_expr = ExprCache.add(new_args) if current.op == Op.ADD else ExprCache.mul(new_args)
                        cost_after = context.statistics.cost_model.cost(new_expr) if context.statistics.cost_model else 0.0
                        context.cost_cache.set(hash(new_expr), cost_after)
                        
                        # 记录追踪
                        if context.should_trace():
                            step = RewriteStep(
                                rule=rule.name,
                                before=current,
                                after=new_expr,
                                position=location,
                                cost_before=cost_before,
                                cost_after=cost_after,
                                reason=f"应用规则 {rule.name}",
                            )
                            context.add_trace_step(step)
                        
                        context.statistics.rules_applied += 1
                        return changed_result(
                            new_expr,
                            rule_name=rule.name,
                            cost=cost_after,
                            depth=1,
                        )

        if changed:
            cost_after = context.statistics.cost_model.cost(current) if context.statistics.cost_model else 0.0
            return changed_result(current, cost=cost_after, depth=1)
        
        return unchanged_result(current)

    def _rebuild_expr(self, expr: Expr, args: List[Expr]) -> Expr:
        """根据操作符类型重建表达式"""
        if expr.op == Op.ADD:
            return ExprCache.add(args)
        elif expr.op == Op.MUL:
            return ExprCache.mul(args)
        elif expr.op == Op.SUB:
            return ExprCache.sub(args[0], args[1])
        elif expr.op == Op.DIV:
            return ExprCache.div(args[0], args[1])
        elif expr.op == Op.POW:
            return ExprCache.pow(args[0], args[1])
        elif expr.op == Op.NEG:
            return ExprCache.neg(args[0])
        elif expr.op == Op.GROUP:
            return ExprCache.group(args[0])
        return Expr(expr.op, tuple(args))


class TopDownStrategy(Strategy):
    """自顶向下策略

    先重写当前节点，再重写子节点。
    适合：保持结构、应用全局规则。
    """

    def __init__(self, rule_set: 'RuleSet', name: str = "TopDown"):
        self.rule_set = rule_set
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        location = RewriteLocation()
        cost_before = context.statistics.cost_model.cost(expr) if context.statistics.cost_model else 0.0

        # 先尝试应用规则
        for rule in self.rule_set.rules:
            result = rule.apply(expr)
            if result is not None:
                cost_after = context.statistics.cost_model.cost(result) if context.statistics.cost_model else 0.0
                
                # 记录追踪
                if context.should_trace():
                    step = RewriteStep(
                        rule=rule.name,
                        before=expr,
                        after=result,
                        position=location,
                        cost_before=cost_before,
                        cost_after=cost_after,
                        reason=f"应用规则 {rule.name}",
                    )
                    context.add_trace_step(step)
                
                context.statistics.rules_applied += 1
                return changed_result(
                    result,
                    rule_name=rule.name,
                    cost=cost_after,
                    depth=0,
                )

        # 对于 GROUP 表达式，直接处理其内部表达式
        if expr.op == Op.GROUP:
            if len(expr.args) > 0:
                result = TopDownStrategy(self.rule_set)._apply(expr.args[0], context)
                if result.changed:
                    new_expr = ExprCache.group(result.expr)
                    return changed_result(new_expr, cost=context.statistics.cost_model.cost(new_expr) if context.statistics.cost_model else 0.0, depth=1)
            return unchanged_result(current)

        # 对于原子表达式（SYMBOL 和 NUMBER），没有子节点需要处理
        if expr.op in (Op.SYMBOL, Op.NUMBER):
            return unchanged_result(expr)

        # 递归处理子节点
        new_args = []
        changed = False
        for i, arg in enumerate(expr.args):
            sub_location = location.clone().push('arg', i)
            result = TopDownStrategy(self.rule_set)._apply(arg, context)
            new_args.append(result.expr)
            if result.changed:
                changed = True

        if changed:
            new_expr = self._rebuild_expr(expr, new_args)
            cost_after = context.statistics.cost_model.cost(new_expr) if context.statistics.cost_model else 0.0
            return changed_result(new_expr, cost=cost_after, depth=1)

        return unchanged_result(expr)

    def _rebuild_expr(self, expr: Expr, args: List[Expr]) -> Expr:
        """根据操作符类型重建表达式"""
        if expr.op == Op.ADD:
            return ExprCache.add(args)
        elif expr.op == Op.MUL:
            return ExprCache.mul(args)
        elif expr.op == Op.SUB:
            return ExprCache.sub(args[0], args[1])
        elif expr.op == Op.DIV:
            return ExprCache.div(args[0], args[1])
        elif expr.op == Op.POW:
            return ExprCache.pow(args[0], args[1])
        elif expr.op == Op.NEG:
            return ExprCache.neg(args[0])
        elif expr.op == Op.GROUP:
            return ExprCache.group(args[0])
        return Expr(expr.op, tuple(args))


# ═══════════════════════════════════════════════════════════
# Composite Strategies - 组合策略
# ═══════════════════════════════════════════════════════════

class RepeatStrategy(Strategy):
    """重复策略 - 直到不动点"""

    def __init__(self, strategy: Strategy, max_iterations: int = 100, name: str = "Repeat"):
        self.strategy = strategy
        self.max_iterations = max_iterations
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        current = expr
        total_changed = False
        iterations = 0
        
        # 创建一个独立的上下文副本用于重复迭代
        iteration_context = context.fork()

        while iterations < self.max_iterations:
            if not iteration_context.should_continue():
                break
            
            result = self.strategy.apply(current, iteration_context)
            if not result.changed:
                break
            
            current = result.expr
            total_changed = True
            iterations += 1
            
            # 每次迭代后清除访问记录，允许重新访问表达式
            iteration_context.clear_visited()

        # 将迭代上下文的统计信息合并到主上下文
        context.statistics.rules_applied += iteration_context.statistics.rules_applied
        context.statistics.rewrite_steps += iteration_context.statistics.rewrite_steps
        
        # 合并追踪记录
        if iteration_context.trace and context.trace:
            context.trace.steps.extend(iteration_context.trace.steps)

        if total_changed:
            return changed_result(current, depth=iterations)
        return unchanged_result(current)


class FixpointStrategy(Strategy):
    """不动点策略 - 重复直到状态稳定"""

    def __init__(self, strategy: Strategy, max_iterations: int = 100, name: str = "Fixpoint"):
        self.strategy = strategy
        self.max_iterations = max_iterations
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        current = expr
        history = {hash(current)}
        iterations = 0

        while iterations < self.max_iterations:
            if not context.should_continue():
                break
            
            result = self.strategy.apply(current, context)
            if not result.changed:
                break
            
            current = result.expr
            current_hash = hash(current)
            if current_hash in history:
                break
            history.add(current_hash)
            iterations += 1

        if iterations > 0:
            return changed_result(current, depth=iterations)
        return unchanged_result(current)


class ChoiceStrategy(Strategy):
    """选择策略 - 多策略择优"""

    def __init__(self, strategies: List[Strategy], cost_model: Optional[CostModel] = None, name: str = "Choice"):
        self.strategies = strategies
        self.cost_model = cost_model or DefaultCostModel()
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        best_result = unchanged_result(expr)
        best_cost = float('inf')

        for strategy in self.strategies:
            # 为每个策略创建独立的上下文副本
            strategy_context = context.fork()
            result = strategy.apply(expr, strategy_context)
            
            if result.changed:
                cost = self.cost_model.cost(result.expr)
                
                if not best_result.changed or cost < best_cost:
                    best_result = result
                    best_cost = cost

        return best_result


class SequenceStrategy(Strategy):
    """顺序策略 - 依次应用多个策略"""

    def __init__(self, strategies: List[Strategy], name: str = "Sequence"):
        self.strategies = strategies
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        current = expr
        total_changed = False
        depth = 0

        for strategy in self.strategies:
            result = strategy.apply(current, context)
            if result.changed:
                current = result.expr
                total_changed = True
                depth += result.depth

        if total_changed:
            return changed_result(current, depth=depth)
        return unchanged_result(current)


class ConditionalStrategy(Strategy):
    """条件策略 - 满足条件才应用"""

    def __init__(self, condition: Callable[[Expr], bool], then_strategy: Strategy, name: str = "Conditional"):
        self.condition = condition
        self.then_strategy = then_strategy
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        if self.condition(expr):
            return self.then_strategy.apply(expr, context)
        return unchanged_result(expr)


class CostBasedStrategy(Strategy):
    """基于代价的策略 - 选择代价最低的结果"""

    def __init__(self, strategy: Strategy, cost_model: Optional[CostModel] = None, name: str = "CostBased"):
        self.strategy = strategy
        self.cost_model = cost_model or DefaultCostModel()
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        best = unchanged_result(expr)
        best_cost = self.cost_model.cost(expr)

        current = expr
        for _ in range(100):
            if not context.should_continue():
                break

            result = self.strategy.apply(current, context)
            if not result.changed:
                break

            cost = self.cost_model.cost(result.expr)
            if cost < best_cost:
                best = result
                best_cost = cost
                current = result.expr
            else:
                break

        return best


class ParallelStrategy(Strategy):
    """并行策略 - 同时尝试多个策略，选最优"""

    def __init__(self, strategies: List[Strategy], cost_model: Optional[CostModel] = None, name: str = "Parallel"):
        self.strategies = strategies
        self.cost_model = cost_model or DefaultCostModel()
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        results = []
        
        for strategy in self.strategies:
            strat_context = context.fork()
            result = strategy.apply(expr, strat_context)
            if result.changed:
                results.append(result)
        
        if not results:
            return unchanged_result(expr)
        
        # 选择代价最低的
        results.sort(key=lambda r: self.cost_model.cost(r.expr))
        return results[0]


class DepthBoundStrategy(Strategy):
    """深度限制策略 - 限制递归深度"""

    def __init__(self, strategy: Strategy, max_depth: int = 5, name: str = "DepthBound"):
        self.strategy = strategy
        self.max_depth = max_depth
        self.name = name

    def _apply(self, expr: Expr, context: RewriteContext) -> RewriteResult:
        # 通过上下文传递深度限制
        current_depth = context.extra.get('depth', 0)
        if current_depth >= self.max_depth:
            return unchanged_result(expr)
        
        context.extra['depth'] = current_depth + 1
        result = self.strategy.apply(expr, context)
        context.extra['depth'] = current_depth
        
        return result


# ═══════════════════════════════════════════════════════════
# Rule Set - 规则集合
# ═══════════════════════════════════════════════════════════

class RuleSet:
    """规则集合"""

    def __init__(self):
        self.rules: List['RewriteRule'] = []

    def add(self, rule: 'RewriteRule'):
        """添加规则"""
        self.rules.append(rule)

    def add_rules(self, rules: List['RewriteRule']):
        """添加多个规则"""
        self.rules.extend(rules)

    def __or__(self, other: 'RuleSet') -> 'RuleSet':
        """合并规则集"""
        new_set = RuleSet()
        new_set.rules = self.rules + other.rules
        return new_set


# ═══════════════════════════════════════════════════════════
# Rule - 规则
# ═══════════════════════════════════════════════════════════

@dataclass
class RewriteRule:
    """重写规则"""
    name: str
    pattern: 'Pattern'
    replacement: 'Pattern'
    condition: Optional[Callable] = None

    def apply(self, expr: Expr) -> Optional[Expr]:
        """应用规则"""
        bindings = self.pattern.match(expr, {})
        if bindings is None:
            return None
        if self.condition is not None:
            if not self.condition(bindings):
                return None
        return self.replacement.substitute(bindings)


# ═══════════════════════════════════════════════════════════
# Pattern - 模式
# ═══════════════════════════════════════════════════════════

@dataclass
class Pattern:
    """模式"""
    op: Optional[Op]
    args: List
    is_var: bool = False
    var_name: Optional[str] = None

    @staticmethod
    def var(name: str) -> 'Pattern':
        return Pattern(op=None, args=[], is_var=True, var_name=name)

    @staticmethod
    def lit(value) -> 'Pattern':
        if isinstance(value, (int, float)):
            return Pattern(op=Op.NUMBER, args=[value])
        return Pattern(op=Op.SYMBOL, args=[str(value)])

    def match(self, expr: Expr, bindings: Dict[str, Expr]) -> Optional[Dict[str, Expr]]:
        """匹配表达式"""
        if self.is_var:
            if self.var_name in bindings:
                if bindings[self.var_name] == expr:
                    return bindings
                return None
            result = bindings.copy()
            result[self.var_name] = expr
            return result

        if expr.op != self.op:
            return None

        if len(self.args) == 0:
            return bindings

        if len(self.args) != len(expr.args):
            return None

        for p_arg, e_arg in zip(self.args, expr.args):
            if p_arg.is_var:
                if p_arg.var_name in bindings:
                    if bindings[p_arg.var_name] != e_arg:
                        return None
                else:
                    bindings = bindings.copy()
                    bindings[p_arg.var_name] = e_arg
            elif p_arg.op == Op.NUMBER:
                if e_arg.op != Op.NUMBER or p_arg.args[0] != e_arg.args[0]:
                    return None
            elif p_arg.op == Op.SYMBOL:
                if e_arg.op != Op.SYMBOL or str(p_arg.args[0]) != str(e_arg.args[0]):
                    return None
            elif p_arg.op == Op.GROUP:
                if e_arg.op != Op.GROUP:
                    return None
                if len(p_arg.args) == 1 and len(e_arg.args) == 1:
                    inner_pattern = p_arg.args[0]
                    inner_expr = e_arg.args[0]
                    if inner_pattern.is_var:
                        if inner_pattern.var_name in bindings:
                            if bindings[inner_pattern.var_name] != inner_expr:
                                return None
                        else:
                            bindings = bindings.copy()
                            bindings[inner_pattern.var_name] = inner_expr
                    else:
                        sub_bindings = inner_pattern.match(inner_expr, bindings)
                        if sub_bindings is None:
                            return None
                        bindings = sub_bindings
                else:
                    return None
            else:
                sub_bindings = p_arg.match(e_arg, bindings)
                if sub_bindings is None:
                    return None
                bindings = sub_bindings

        return bindings

    def substitute(self, bindings: Dict[str, Expr]) -> Expr:
        """替换模式变量"""
        if self.is_var:
            return bindings.get(self.var_name)

        if self.op == Op.NUMBER:
            return ExprCache.number(self.args[0])
        if self.op == Op.SYMBOL:
            return ExprCache.symbol(str(self.args[0]))

        args = [p.substitute(bindings) if isinstance(p, Pattern) else p for p in self.args]

        if self.op == Op.ADD:
            return ExprCache.add(args)
        if self.op == Op.MUL:
            return ExprCache.mul(args)
        if self.op == Op.SUB:
            return ExprCache.sub(args[0], args[1])
        if self.op == Op.DIV:
            return ExprCache.div(args[0], args[1])
        if self.op == Op.POW:
            return ExprCache.pow(args[0], args[1])
        if self.op == Op.NEG:
            return ExprCache.neg(args[0])
        if self.op == Op.GROUP:
            return ExprCache.group(args[0])

        return ExprCache.expr(self.op, args)


def create_rule(name: str, pattern: Pattern, replacement: Pattern,
                condition: Optional[Callable] = None) -> RewriteRule:
    """创建规则"""
    return RewriteRule(name, pattern, replacement, condition)


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def make_rule(name: str, pattern_str: str, replacement_str: str) -> RewriteRule:
    """从字符串创建规则（简单版本）"""
    from .rewrite_ir import parse_pattern
    pattern = parse_pattern(pattern_str)
    replacement = parse_pattern(replacement_str)
    return RewriteRule(name, pattern, replacement)


# ═══════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    from .canonical_ir import from_ast
    from .parselet import parse_with_pratt
    from .context import create_trace_context

    print("=" * 60)
    print("Rewrite Strategy System 测试")
    print("=" * 60)

    rules = RuleSet()
    rules.add(create_rule(
        "Additive Identity",
        Pattern(op=Op.ADD, args=[Pattern.var("x"), Pattern.lit(0)]),
        Pattern.var("x")
    ))
    rules.add(create_rule(
        "Multiplicative Identity",
        Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.lit(1)]),
        Pattern.var("x")
    ))
    rules.add(create_rule(
        "Multiplication by Zero",
        Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.lit(0)]),
        Pattern.lit(0)
    ))

    print("\n1. BottomUp 策略 + 追踪模式:")
    context = create_trace_context()
    strategy = BottomUpStrategy(rules)
    for expr_str in ["x+0", "0+x", "x*1", "1*x", "(x+0)*1"]:
        ast = parse_with_pratt(expr_str)
        expr = from_ast(ast)
        result = strategy.apply(expr, context)
        print(f"   {expr_str} -> {result.expr} (changed={result.changed})")
    print(f"   规则应用次数: {context.statistics.rules_applied}")

    print("\n2. TopDown 策略:")
    context = create_trace_context()
    strategy = TopDownStrategy(rules)
    for expr_str in ["x+0", "0+x", "x*1", "1*x", "(x+0)*1"]:
        ast = parse_with_pratt(expr_str)
        expr = from_ast(ast)
        result = strategy.apply(expr, context)
        print(f"   {expr_str} -> {result.expr} (changed={result.changed})")

    print("\n3. Repeat + BottomUp 策略:")
    context = create_trace_context()
    strategy = RepeatStrategy(BottomUpStrategy(rules))
    ast = parse_with_pratt("x+0+0")
    expr = from_ast(ast)
    result = strategy.apply(expr, context)
    print(f"   x+0+0 -> {result.expr} (depth={result.depth})")
    print(f"   追踪步骤: {context.trace.length}")
    if context.trace:
        context.trace.print_detailed()

    print("\n4. 策略组合 (BottomUp | BottomUp):")
    context = create_trace_context()
    strategy = BottomUpStrategy(rules) | BottomUpStrategy(rules)
    ast = parse_with_pratt("(x+0)*1")
    expr = from_ast(ast)
    result = strategy.apply(expr, context)
    print(f"   (x+0)*1 -> {result.expr}")

    print("\n5. Choice 策略:")
    context = create_trace_context()
    strategy = ChoiceStrategy([
        BottomUpStrategy(rules),
        TopDownStrategy(rules)
    ])
    ast = parse_with_pratt("x+0")
    expr = from_ast(ast)
    result = strategy.apply(expr, context)
    print(f"   x+0 -> {result.expr}")

    print("\n6. Cost-Based 策略:")
    context = create_trace_context()
    strategy = CostBasedStrategy(BottomUpStrategy(rules), DefaultCostModel())
    ast = parse_with_pratt("x+x")
    expr = from_ast(ast)
    result = strategy.apply(expr, context)
    cost = DefaultCostModel().cost(result.expr)
    print(f"   x+x -> {result.expr} (cost={cost:.2f})")

    print("\n7. Fixpoint 策略:")
    context = create_trace_context()
    strategy = FixpointStrategy(BottomUpStrategy(rules))
    ast = parse_with_pratt("(x+0)*1*1")
    expr = from_ast(ast)
    result = strategy.apply(expr, context)
    print(f"   (x+0)*1*1 -> {result.expr}")

    print("\n" + "=" * 60)
    print("策略系统测试完成！")
    print("=" * 60)
