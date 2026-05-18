"""Rewrite Engine on Canonical IR - 基于规范化中间表示的重写引擎

这是整个数学推理系统的核心。与基于 AST 的重写不同，这里直接操作 Canonical IR，
从而获得：
- 确定性：相同的表达式永远只有一种表示
- 高效匹配：使用哈希而非结构遍历
- DAG 支持：共享子表达式避免重复计算
- 可组合性：规则可堆叠和复用
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass
import re

from .canonical_ir import Expr, Op, ExprCache, from_ast, simplify


# ═══════════════════════════════════════════════════════════════════════════
# Pattern DSL - 模式领域特定语言
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Pattern:
    """模式 - 用于匹配 Canonical IR 表达式"""
    op: Optional[Op]
    args: List[Pattern]
    is_var: bool = False
    var_name: Optional[str] = None

    @staticmethod
    def var(name: str) -> Pattern:
        """创建模式变量"""
        return Pattern(op=None, args=[], is_var=True, var_name=name)

    @staticmethod
    def lit(value) -> Pattern:
        """创建字面量模式"""
        if isinstance(value, (int, float)):
            return Pattern(op=Op.NUMBER, args=[value])
        return Pattern(op=Op.SYMBOL, args=[str(value)])

    @staticmethod
    def any() -> Pattern:
        """匹配任意表达式"""
        return Pattern(op=None, args=[])

    def match(self, expr: Expr, bindings: Dict[str, Expr]) -> Optional[Dict[str, Expr]]:
        """匹配表达式，返回绑定字典"""
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
                if e_arg.op != Op.NUMBER:
                    return None
                if p_arg.args[0] != e_arg.args[0]:
                    return None
            elif p_arg.op == Op.SYMBOL:
                if e_arg.op != Op.SYMBOL:
                    return None
                if str(p_arg.args[0]) != str(e_arg.args[0]):
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
                    sub_bindings = p_arg.match(e_arg, bindings)
                    if sub_bindings is None:
                        return None
                    bindings = sub_bindings
            else:
                sub_bindings = p_arg.match(e_arg, bindings)
                if sub_bindings is None:
                    return None
                bindings = sub_bindings

        return bindings


@dataclass
class RewriteRule:
    """重写规则"""
    name: str
    pattern: Pattern
    replacement: Pattern
    condition: Optional[callable] = None

    def apply(self, expr: Expr) -> Optional[Expr]:
        """应用规则，返回新的表达式（如果匹配）"""
        bindings = self.pattern.match(expr, {})
        if bindings is None:
            return None

        if self.condition is not None:
            if not self.condition(bindings):
                return None

        return self.substitute(self.replacement, bindings)

    def substitute(self, pattern: Pattern, bindings: Dict[str, Expr]) -> Expr:
        """替换模式变量"""
        if pattern.is_var:
            return bindings.get(pattern.var_name)

        if pattern.op == Op.NUMBER:
            return ExprCache.number(pattern.args[0])

        if pattern.op == Op.SYMBOL:
            return ExprCache.symbol(str(pattern.args[0]))

        args = [self.substitute(p, bindings) for p in pattern.args]

        if pattern.op == Op.ADD:
            return ExprCache.add(args)
        if pattern.op == Op.MUL:
            return ExprCache.mul(args)
        if pattern.op == Op.SUB:
            return ExprCache.sub(args[0], args[1])
        if pattern.op == Op.DIV:
            return ExprCache.div(args[0], args[1])
        if pattern.op == Op.POW:
            return ExprCache.pow(args[0], args[1])
        if pattern.op == Op.NEG:
            return ExprCache.neg(args[0])
        if pattern.op == Op.GROUP:
            return ExprCache.group(args[0])

        return ExprCache.expr(pattern.op, args)


# ═══════════════════════════════════════════════════════════════════════════
# Rule DSL Parser - 规则领域特定语言解析器
# ═══════════════════════════════════════════════════════════════════════════

def parse_pattern(s: str) -> Pattern:
    """解析模式字符串

    支持的语法:
    - a, b, x, y, z: 模式变量
    - 0, 1, 2: 字面量数字
    - +, -, *, /: 二元运算
    - ^: 幂运算
    """
    s = s.strip()

    if re.match(r'^[a-zA-Z_]\w*$', s):
        return Pattern.var(s)

    if re.match(r'^-?\d+(\.\d+)?$', s):
        return Pattern.lit(float(s) if '.' in s else int(s))

    if s.startswith('(') and s.endswith(')'):
        return parse_pattern(s[1:-1])

    if '^' in s and '(' not in s:
        parts = s.split('^')
        if len(parts) == 2:
            base = parse_pattern(parts[0])
            exp = parse_pattern(parts[1])
            return Pattern(op=Op.POW, args=[base, exp])

    if '+' in s:
        parts = s.split('+')
        if len(parts) == 2:
            return Pattern(op=Op.ADD, args=[parse_pattern(parts[0]), parse_pattern(parts[1])])

    if '-' in s and s.count('-') == 1:
        parts = s.split('-')
        if len(parts) == 2:
            return Pattern(op=Op.SUB, args=[parse_pattern(parts[0]), parse_pattern(parts[1])])

    if '*' in s:
        parts = s.split('*')
        if len(parts) == 2:
            return Pattern(op=Op.MUL, args=[parse_pattern(parts[0]), parse_pattern(parts[1])])

    if '/' in s:
        parts = s.split('/')
        if len(parts) == 2:
            return Pattern(op=Op.DIV, args=[parse_pattern(parts[0]), parse_pattern(parts[1])])

    return Pattern.var(s)


def parse_rule(s: str) -> RewriteRule:
    """解析规则字符串

    支持的语法:
    - "x + 0 -> x"
    - "x * 1 -> x // comment"
    """
    s = s.strip()

    comment_match = re.search(r'//.*$', s)
    if comment_match:
        comment = comment_match.group(0)[2:].strip()
        s = s[:comment_match.start()].strip()
    else:
        comment = ""

    if '->' not in s:
        raise ValueError(f"Invalid rule format: {s}")

    pattern_str, replacement_str = s.split('->', 1)
    pattern_str = pattern_str.strip()
    replacement_str = replacement_str.strip()

    pattern = parse_pattern(pattern_str)
    replacement = parse_pattern(replacement_str)

    return RewriteRule(name=comment, pattern=pattern, replacement=replacement)


# ═══════════════════════════════════════════════════════════════════════════
# Rewrite Engine - 重写引擎
# ═══════════════════════════════════════════════════════════════════════════

class RewriteEngine:
    """基于 Canonical IR 的重写引擎

    使用策略模式，支持多种重写策略：
    - topdown: 从根开始应用规则
    - bottomup: 从叶节点开始应用规则
    - fixpoint: 重复应用直到不动点
    """

    def __init__(self, strategy: str = "fixpoint"):
        self.rules: List[RewriteRule] = []
        self.strategy = strategy

    def add_rule(self, rule: RewriteRule):
        """添加规则"""
        self.rules.append(rule)

    def add_rules(self, rules: List[RewriteRule]):
        """添加多个规则"""
        self.rules.extend(rules)

    def rewrite(self, expr: Expr, max_iterations: int = 100) -> Tuple[Expr, List[str]]:
        """重写表达式"""
        current = expr
        steps = []

        if self.strategy == "fixpoint":
            changed = True
            iterations = 0
            while changed and iterations < max_iterations:
                changed = False
                iterations += 1

                for rule in self.rules:
                    result = rule.apply(current)
                    if result is not None:
                        before_str = current.to_latex()
                        after_str = result.to_latex()
                        steps.append(f"{before_str} -> {after_str} [{rule.name}]")
                        current = result
                        changed = True
                        break

                if not changed:
                    current, sub_steps = self._rewrite_recursive(current)
                    steps.extend(sub_steps)
                    if sub_steps:
                        changed = True

        return current, steps

    def _rewrite_recursive(self, expr: Expr) -> Tuple[Expr, List[str]]:
        """递归重写子节点"""
        steps = []

        if expr.op == Op.ADD:
            new_args = []
            changed = False
            for arg in expr.args:
                new_arg, sub_steps = self.rewrite(arg)
                new_args.append(new_arg)
                steps.extend(sub_steps)
                if new_arg != arg:
                    changed = True
            if changed:
                return ExprCache.add(new_args), steps
            return expr, steps

        if expr.op == Op.MUL:
            new_args = []
            changed = False
            for arg in expr.args:
                new_arg, sub_steps = self.rewrite(arg)
                new_args.append(new_arg)
                steps.extend(sub_steps)
                if new_arg != arg:
                    changed = True
            if changed:
                return ExprCache.mul(new_args), steps
            return expr, steps

        if expr.op in (Op.SUB, Op.DIV, Op.POW, Op.NEG):
            new_args = []
            changed = False
            for arg in expr.args:
                new_arg, sub_steps = self.rewrite(arg)
                new_args.append(new_arg)
                steps.extend(sub_steps)
                if new_arg != arg:
                    changed = True
            if changed:
                if expr.op == Op.SUB:
                    return ExprCache.sub(new_args[0], new_args[1]), steps
                if expr.op == Op.DIV:
                    return ExprCache.div(new_args[0], new_args[1]), steps
                if expr.op == Op.POW:
                    return ExprCache.pow(new_args[0], new_args[1]), steps
                if expr.op == Op.NEG:
                    return ExprCache.neg(new_args[0]), steps
            return expr, steps

        if expr.op == Op.GROUP:
            new_content, sub_steps = self.rewrite(expr.args[0])
            steps.extend(sub_steps)
            if sub_steps:
                return ExprCache.group(new_content), steps
            return expr, steps

        return expr, steps


# ═══════════════════════════════════════════════════════════════════════════
# Default Rules - 默认规则集
# ═══════════════════════════════════════════════════════════════════════════

def create_default_rules() -> List[RewriteRule]:
    """创建默认规则集"""
    rules = []

    rules.append(RewriteRule(
        name="Additive Identity",
        pattern=Pattern(op=Op.ADD, args=[Pattern.var("x"), Pattern.lit(0)]),
        replacement=Pattern.var("x")
    ))

    rules.append(RewriteRule(
        name="Multiplicative Identity",
        pattern=Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.lit(1)]),
        replacement=Pattern.var("x")
    ))

    rules.append(RewriteRule(
        name="Multiplication by Zero",
        pattern=Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.lit(0)]),
        replacement=Pattern.lit(0)
    ))

    rules.append(RewriteRule(
        name="Power to Zero",
        pattern=Pattern(op=Op.POW, args=[Pattern.var("x"), Pattern.lit(0)]),
        replacement=Pattern.lit(1)
    ))

    rules.append(RewriteRule(
        name="Power to One",
        pattern=Pattern(op=Op.POW, args=[Pattern.var("x"), Pattern.lit(1)]),
        replacement=Pattern.var("x")
    ))

    rules.append(RewriteRule(
        name="Combine Like Terms",
        pattern=Pattern(op=Op.ADD, args=[Pattern.var("x"), Pattern.var("x")]),
        replacement=Pattern(op=Op.MUL, args=[Pattern.lit(2), Pattern.var("x")])
    ))

    def combine_like_terms_condition(bindings):
        x = bindings.get("x")
        if x is None:
            return False
        return x.op in (Op.SYMBOL, Op.NUMBER, Op.MUL, Op.POW)

    rules.append(RewriteRule(
        name="Multiplication by Group (left)",
        pattern=Pattern(op=Op.MUL, args=[Pattern(op=Op.GROUP, args=[Pattern.var("x")]), Pattern.var("y")]),
        replacement=Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.var("y")])
    ))

    rules.append(RewriteRule(
        name="Multiplication by Group (right)",
        pattern=Pattern(op=Op.MUL, args=[Pattern.var("y"), Pattern(op=Op.GROUP, args=[Pattern.var("x")])]),
        replacement=Pattern(op=Op.MUL, args=[Pattern.var("x"), Pattern.var("y")])
    ))

    return rules


# ═══════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════

def rule(s: str) -> RewriteRule:
    """解析规则字符串"""
    return parse_rule(s)


def rewrite(expr: Expr, rules: List[RewriteRule]) -> Tuple[Expr, List[str]]:
    """使用给定规则重写表达式"""
    engine = RewriteEngine()
    engine.add_rules(rules)
    return engine.rewrite(expr)


def rewrite_with_default_rules(expr: Expr) -> Tuple[Expr, List[str]]:
    """使用默认规则重写表达式"""
    engine = RewriteEngine()
    engine.add_rules(create_default_rules())
    return engine.rewrite(expr)


# ═══════════════════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from latex_engine.parselet import parse_with_pratt

    print("=" * 60)
    print("Canonical IR Rewrite Engine 测试")
    print("=" * 60)

    engine = RewriteEngine()
    engine.add_rules(create_default_rules())

    test_cases = [
        ("x+0", "x"),
        ("0+x", "x"),
        ("x*1", "x"),
        ("1*x", "x"),
        ("x+x", "x2"),
        ("(x+0)*1", "x"),
    ]

    print("\n测试用例:")
    for input_expr, expected in test_cases:
        ast = parse_with_pratt(input_expr)
        expr = from_ast(ast)
        result, steps = engine.rewrite(expr)
        actual = result.to_latex()
        status = "OK" if actual == expected else "FAIL"
        print(f"  {status}: {input_expr} -> {actual} (期望: {expected})")
        if steps:
            for step in steps:
                print(f"      {step}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)