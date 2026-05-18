"""Canonical IR - 核心中间表示

数学表达式的规范化表示，解决以下问题：
1. AST爆炸：二元树 vs n-ary扁平化
2. 等价性混乱：(x+y)+z 和 x+(y+z) 应该相同
3. 效率低下：无法共享子表达式

设计目标：
- N-ary 操作：Add(args=[x,y,z]) 而非 Add(left=Add(left=x,right=y), right=z)
- Canonical ordering：x+y+z 永远排序为 x<y<z
- Structural hashing：相同表达式全局唯一
- DAG 化：共享子表达式指向同一对象
"""

from __future__ import annotations
from enum import Enum, auto
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, field
import functools


class Op(Enum):
    """操作符枚举"""
    SYMBOL = auto()
    NUMBER = auto()
    ADD = auto()
    MUL = auto()
    SUB = auto()
    DIV = auto()
    NEG = auto()
    POW = auto()
    SIN = auto()
    COS = auto()
    TAN = auto()
    LOG = auto()
    LN = auto()
    EXP = auto()
    SQRT = auto()
    ABS = auto()
    TANH = auto()
    SINH = auto()
    COSH = auto()
    ARCSIN = auto()
    ARCCOS = auto()
    ARCTAN = auto()
    SEC = auto()
    CSC = auto()
    COT = auto()
    LIMIT = auto()
    INTEGRAL = auto()
    DERIVATIVE = auto()
    SUM = auto()
    PRODUCT = auto()
    FRAC = auto()
    GROUP = auto()
    EQUATION = auto()


@dataclass(frozen=True, slots=True)
class Expr:
    """规范化表达式 - 不可变对象

    核心设计：
    - op: 操作符类型
    - args: 子表达式列表（已扁平化）
    - hash: 结构哈希（用于去重和比较）
    """
    op: Op
    args: Tuple[Expr, ...] = field(default_factory=tuple)
    hash: int = 0

    def __post_init__(self):
        if self.hash == 0:
            object.__setattr__(self, 'hash', self._compute_hash())

    def _compute_hash(self) -> int:
        """计算结构哈希"""
        if self.op in (Op.SYMBOL, Op.NUMBER):
            return hash((self.op, tuple(str(a) for a in self.args)))
        return hash((self.op, tuple(a.hash for a in self.args)))

    def __str__(self) -> str:
        return self.to_latex()

    def __repr__(self) -> str:
        return f"Expr({self.op.name}, {self.args})"

    def to_latex(self) -> str:
        """转换为 LaTeX 字符串"""
        return expr_to_latex(self)


# ═══════════════════════════════════════════════════════════════════════════
# 表达式工厂 - Hash Consing
# ═══════════════════════════════════════════════════════════════════════════

class ExprCache:
    """表达式缓存池 - 实现 Hash Consing

    确保相同的表达式全局唯一，增强以下能力：
    - 快速等价性比较（同一对象 vs 遍历树）
    - 内存效率（共享子表达式）
    - Rewrite 效率（DAG 操作）
    """
    _cache: Dict[int, Expr] = {}
    _symbol_cache: Dict[str, Expr] = {}
    _number_cache: Dict[Union[int, float], Expr] = {}

    @classmethod
    def symbol(cls, name: str) -> Expr:
        """获取符号表达式（可能复用缓存）"""
        if name not in cls._symbol_cache:
            expr = Expr(Op.SYMBOL, args=(name,))
            cls._symbol_cache[name] = expr
            cls._cache[expr.hash] = expr
        return cls._symbol_cache[name]

    @classmethod
    def number(cls, value: Union[int, float]) -> Expr:
        """获取数字表达式（可能复用缓存）"""
        if value not in cls._number_cache:
            expr = Expr(Op.NUMBER, args=(value,))
            cls._number_cache[value] = expr
            cls._cache[expr.hash] = expr
        return cls._number_cache[value]

    @classmethod
    def expr(cls, op: Op, args: List[Expr]) -> Expr:
        """创建表达式（自动哈希consing）"""
        args = tuple(args)
        expr = Expr(op, args)
        if expr.hash in cls._cache:
            return cls._cache[expr.hash]
        cls._cache[expr.hash] = expr
        return expr

    @classmethod
    def add(cls, args: List[Expr]) -> Expr:
        """创建加法表达式（扁平化+排序）"""
        flattened = []
        for arg in args:
            if arg.op == Op.ADD:
                flattened.extend(arg.args)
            else:
                flattened.append(arg)
        if len(flattened) == 0:
            return cls.number(0)
        if len(flattened) == 1:
            return flattened[0]
        sorted_args = tuple(sorted(flattened, key=_expr_sort_key))
        return cls.expr(Op.ADD, list(sorted_args))

    @classmethod
    def mul(cls, args: List[Expr]) -> Expr:
        """创建乘法表达式（扁平化+排序）"""
        flattened = []
        for arg in args:
            if arg.op == Op.MUL:
                flattened.extend(arg.args)
            else:
                flattened.append(arg)
        if len(flattened) == 0:
            return cls.number(1)
        if len(flattened) == 1:
            return flattened[0]
        sorted_args = tuple(sorted(flattened, key=_expr_sort_key))
        return cls.expr(Op.MUL, list(sorted_args))

    @classmethod
    def sub(cls, left: Expr, right: Expr) -> Expr:
        """创建减法表达式"""
        return cls.expr(Op.SUB, [left, right])

    @classmethod
    def div(cls, numerator: Expr, denominator: Expr) -> Expr:
        """创建除法表达式"""
        return cls.expr(Op.DIV, [numerator, denominator])

    @classmethod
    def neg(cls, operand: Expr) -> Expr:
        """创建负数表达式"""
        if operand.op == Op.NUMBER:
            return cls.number(-float(operand.args[0]))
        return cls.expr(Op.NEG, [operand])

    @classmethod
    def pow(cls, base: Expr, exponent: Expr) -> Expr:
        """创建幂表达式"""
        return cls.expr(Op.POW, [base, exponent])

    @classmethod
    def func(cls, op: Op, args: List[Expr]) -> Expr:
        """创建函数表达式"""
        return cls.expr(op, args)

    @classmethod
    def group(cls, content: Expr) -> Expr:
        """创建分组表达式"""
        return cls.expr(Op.GROUP, [content])

    @classmethod
    def clear_cache(cls):
        """清除缓存（主要用于测试）"""
        cls._cache.clear()
        cls._symbol_cache.clear()
        cls._number_cache.clear()


def _expr_sort_key(expr: Expr) -> Tuple:
    """表达式排序键 - 保证交换律排序的确定性"""
    if expr.op == Op.SYMBOL:
        return (0, str(expr.args[0]))
    elif expr.op == Op.NUMBER:
        return (1, float(expr.args[0]))
    else:
        return (2, expr.op.name)


# ═══════════════════════════════════════════════════════════════════════════
# LaTeX 渲染
# ═══════════════════════════════════════════════════════════════════════════

def expr_to_latex(expr: Expr) -> str:
    """将表达式转换为 LaTeX 字符串"""
    if expr.op == Op.SYMBOL:
        return str(expr.args[0])

    if expr.op == Op.NUMBER:
        val = expr.args[0]
        if isinstance(val, (int, float)):
            return str(val)
        return str(val)

    if expr.op == Op.ADD:
        return " + ".join(expr_to_latex(a) for a in expr.args)

    if expr.op == Op.MUL:
        parts = []
        for a in expr.args:
            a_str = expr_to_latex(a)
            if _needs_parens(a, Op.MUL):
                parts.append(f"({a_str})")
            else:
                parts.append(a_str)
        result = "".join(parts)
        return result

    if expr.op == Op.SUB:
        left, right = expr.args
        left_str = expr_to_latex(left)
        right_str = expr_to_latex(right)
        if _needs_parens(left, Op.SUB):
            left_str = f"({left_str})"
        if _needs_parens(right, Op.SUB):
            right_str = f"({right_str})"
        return f"{left_str} - {right_str}"

    if expr.op == Op.DIV:
        num, den = expr.args
        return f"\\frac{{{expr_to_latex(num)}}}{{{expr_to_latex(den)}}}"

    if expr.op == Op.NEG:
        arg_str = expr_to_latex(expr.args[0])
        if _needs_parens(expr.args[0]):
            return f"-({arg_str})"
        return f"-{arg_str}"

    if expr.op == Op.POW:
        base, exp = expr.args
        base_str = expr_to_latex(base)
        exp_str = expr_to_latex(exp)
        if _needs_parens(base, Op.POW):
            base_str = f"({base_str})"
        if _needs_parens(exp, Op.POW):
            exp_str = f"({exp_str})"
        return f"{base_str}^{{{exp_str}}}"

    if expr.op == Op.GROUP:
        return "{" + expr_to_latex(expr.args[0]) + "}"

    if expr.op == Op.FRAC:
        num, den = expr.args
        return f"\\frac{{{expr_to_latex(num)}}}{{{expr_to_latex(den)}}}"

    op_names = {
        Op.SIN: "sin",
        Op.COS: "cos",
        Op.TAN: "tan",
        Op.LOG: "log",
        Op.LN: "ln",
        Op.EXP: "exp",
        Op.SQRT: "sqrt",
        Op.ABS: "abs",
    }

    if expr.op in op_names:
        func_name = op_names[expr.op]
        args_str = ",".join(expr_to_latex(a) for a in expr.args)
        return f"\\{func_name}({args_str})"

    return f"\\{expr.op.name.lower()}({','.join(expr_to_latex(a) for a in expr.args)})"


def _needs_parens(expr: Expr, parent_op: Optional[Op] = None) -> bool:
    """判断表达式是否需要括号"""
    if expr.op == Op.ADD or expr.op == Op.SUB:
        return parent_op in (Op.MUL, Op.DIV, Op.POW)
    if expr.op == Op.MUL:
        return parent_op == Op.POW
    if expr.op == Op.NUMBER or expr.op == Op.SYMBOL:
        return False
    return False


# ═══════════════════════════════════════════════════════════════════════════
# 代数操作
# ═══════════════════════════════════════════════════════════════════════════

def expr_equals(a: Expr, b: Expr) -> bool:
    """判断两个表达式是否相等（结构相等）"""
    if a.hash != b.hash:
        return False
    if a.op != b.op:
        return False
    if len(a.args) != len(b.args):
        return False
    if a.op in (Op.SYMBOL, Op.NUMBER):
        return a.args[0] == b.args[0]
    return all(expr_equals(x, y) for x, y in zip(a.args, b.args))


def expr_copy(expr: Expr) -> Expr:
    """复制表达式（保持不可变性，实际上返回自身）"""
    return expr


# ═══════════════════════════════════════════════════════════════════════════
# AST 到 Canonical IR 的转换
# ═══════════════════════════════════════════════════════════════════════════

def to_ast(expr: Expr) -> 'ASTNode':
    """将 Canonical IR 表达式转换回 AST 节点

    这是 from_ast 的逆操作。
    """
    from .ast import (
        SymbolNode, NumberNode, AddNode, SubtractNode, MultiplyNode,
        DivideNode, NegateNode, PowerNode, GroupNode, FunctionNode
    )

    if expr.op == Op.SYMBOL:
        return SymbolNode(str(expr.args[0]))

    if expr.op == Op.NUMBER:
        return NumberNode(expr.args[0])

    if expr.op == Op.ADD:
        if len(expr.args) == 2:
            return AddNode(to_ast(expr.args[0]), to_ast(expr.args[1]))
        # 多于两个参数时，构建左关联树
        result = AddNode(to_ast(expr.args[0]), to_ast(expr.args[1]))
        for arg in expr.args[2:]:
            result = AddNode(result, to_ast(arg))
        return result

    if expr.op == Op.MUL:
        if len(expr.args) == 2:
            return MultiplyNode(to_ast(expr.args[0]), to_ast(expr.args[1]))
        # 多于两个参数时，构建左关联树
        result = MultiplyNode(to_ast(expr.args[0]), to_ast(expr.args[1]))
        for arg in expr.args[2:]:
            result = MultiplyNode(result, to_ast(arg))
        return result

    if expr.op == Op.SUB:
        return SubtractNode(to_ast(expr.args[0]), to_ast(expr.args[1]))

    if expr.op == Op.DIV:
        return DivideNode(to_ast(expr.args[0]), to_ast(expr.args[1]))

    if expr.op == Op.NEG:
        return NegateNode(to_ast(expr.args[0]))

    if expr.op == Op.POW:
        return PowerNode(to_ast(expr.args[0]), to_ast(expr.args[1]))

    if expr.op == Op.GROUP:
        return GroupNode([to_ast(expr.args[0])])

    op_map = {
        Op.SIN: 'sin', Op.COS: 'cos', Op.TAN: 'tan',
        Op.LOG: 'log', Op.LN: 'ln', Op.EXP: 'exp',
        Op.SQRT: 'sqrt', Op.ABS: 'abs',
    }
    if expr.op in op_map:
        return FunctionNode(op_map[expr.op], [to_ast(arg) for arg in expr.args])

    return SymbolNode(str(expr))


def from_ast(node) -> Expr:
    """将 AST 节点转换为 Canonical IR 表达式

    这是连接旧 AST 系统和新 IR 系统的桥梁。
    """
    from .ast import (
        SymbolNode, NumberNode, AddNode, SubtractNode, MultiplyNode,
        DivideNode, NegateNode, SuperscriptNode, GroupNode, FunctionNode
    )

    if isinstance(node, SymbolNode):
        return ExprCache.symbol(node.name)

    if isinstance(node, NumberNode):
        return ExprCache.number(node.value)

    if isinstance(node, AddNode):
        left = from_ast(node.left)
        right = from_ast(node.right)
        return ExprCache.add([left, right])

    if isinstance(node, SubtractNode):
        left = from_ast(node.left)
        right = from_ast(node.right)
        return ExprCache.sub(left, right)

    if isinstance(node, MultiplyNode):
        left = from_ast(node.left)
        right = from_ast(node.right)
        return ExprCache.mul([left, right])

    if isinstance(node, DivideNode):
        num = from_ast(node.numerator)
        den = from_ast(node.denominator)
        return ExprCache.div(num, den)

    if isinstance(node, NegateNode):
        operand = from_ast(node.operand)
        return ExprCache.neg(operand)

    if isinstance(node, SuperscriptNode):
        base = from_ast(node.base)
        exp = from_ast(node.exponent)
        return ExprCache.pow(base, exp)

    if isinstance(node, GroupNode):
        if len(node.content) == 1:
            content = from_ast(node.content[0])
        else:
            content = ExprCache.add([from_ast(c) for c in node.content])
        return ExprCache.group(content)

    if isinstance(node, FunctionNode):
        name = node.name.lower()
        op_map = {
            'sin': Op.SIN, 'cos': Op.COS, 'tan': Op.TAN,
            'log': Op.LOG, 'ln': Op.LN, 'exp': Op.EXP,
            'sqrt': Op.SQRT, 'abs': Op.ABS,
        }
        op = op_map.get(name, Op.FUNC)
        args = [from_ast(arg) for arg in node.arguments]
        return ExprCache.func(op, args)

    return ExprCache.symbol(str(node))


# ═══════════════════════════════════════════════════════════════════════════
# 简化和规范化
# ═══════════════════════════════════════════════════════════════════════════

def simplify(expr: Expr) -> Expr:
    """简化表达式（应用基础恒等元）"""
    if expr.op == Op.ADD:
        args = []
        for arg in expr.args:
            if not isinstance(arg, Expr):
                arg = ExprCache.number(arg) if isinstance(arg, (int, float)) else ExprCache.symbol(str(arg))
            simplified = simplify(arg)
            if simplified.op == Op.NUMBER and float(simplified.args[0]) == 0:
                continue
            args.append(simplified)
        if not args:
            return ExprCache.number(0)
        if len(args) == 1:
            return args[0]
        return ExprCache.add(args)

    if expr.op == Op.MUL:
        args = []
        for arg in expr.args:
            if not isinstance(arg, Expr):
                arg = ExprCache.number(arg) if isinstance(arg, (int, float)) else ExprCache.symbol(str(arg))
            simplified = simplify(arg)
            if simplified.op == Op.NUMBER and float(simplified.args[0]) == 1:
                continue
            args.append(simplified)
        if not args:
            return ExprCache.number(1)
        if len(args) == 1:
            return args[0]
        return ExprCache.mul(args)

    if expr.op == Op.POW:
        base = expr.args[0] if isinstance(expr.args[0], Expr) else ExprCache.symbol(str(expr.args[0]))
        exp = expr.args[1] if isinstance(expr.args[1], Expr) else ExprCache.number(expr.args[1])
        base = simplify(base)
        exp = simplify(exp)
        if exp.op == Op.NUMBER and float(exp.args[0]) == 1:
            return base
        if exp.op == Op.NUMBER and float(exp.args[0]) == 0:
            return ExprCache.number(1)
        return ExprCache.pow(base, exp)

    if expr.op == Op.NEG:
        arg = expr.args[0] if isinstance(expr.args[0], Expr) else ExprCache.symbol(str(expr.args[0]))
        arg = simplify(arg)
        if arg.op == Op.NEG:
            return arg.args[0]
        return ExprCache.neg(arg)

    if expr.op in (Op.SUB, Op.DIV, Op.GROUP):
        args = []
        for a in expr.args:
            if not isinstance(a, Expr):
                a = ExprCache.number(a) if isinstance(a, (int, float)) else ExprCache.symbol(str(a))
            args.append(simplify(a))
        if expr.op == Op.SUB:
            return ExprCache.sub(args[0], args[1])
        if expr.op == Op.DIV:
            return ExprCache.div(args[0], args[1])
        return ExprCache.group(args[0])

    return ExprCache.expr(expr.op, [simplify(a) if isinstance(a, Expr) else ExprCache.symbol(str(a)) for a in expr.args])


# ═══════════════════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ExprCache.clear_cache()

    x = ExprCache.symbol("x")
    y = ExprCache.symbol("y")
    z = ExprCache.symbol("z")
    zero = ExprCache.number(0)
    one = ExprCache.number(1)
    two = ExprCache.number(2)

    print("=" * 60)
    print("Canonical IR 测试")
    print("=" * 60)

    print("\n1. 符号和数字:")
    print(f"   x = {x}")
    print(f"   y = {y}")
    print(f"   0 = {zero}")
    print(f"   1 = {one}")

    print("\n2. N-ary 加法（扁平化）:")
    expr1 = ExprCache.add([x, y, z])
    expr2 = ExprCache.add([x, ExprCache.add([y, z])])
    print(f"   add([x,y,z]) = {expr1}")
    print(f"   add([x,add([y,z])]) = {expr2}")
    print(f"   相等: {expr1 == expr2}")
    print(f"   同一对象: {expr1 is expr2}")

    print("\n3. 交换律排序:")
    expr3 = ExprCache.add([z, x, y])
    print(f"   add([z,x,y]) = {expr3}")
    print(f"   与 add([x,y,z]) 相等: {expr1 == expr3}")

    print("\n4. N-ary 乘法:")
    expr4 = ExprCache.mul([x, y, z])
    expr5 = ExprCache.mul([x, ExprCache.mul([y, z])])
    print(f"   mul([x,y,z]) = {expr4}")
    print(f"   mul([x,mul([y,z])]) = {expr5}")
    print(f"   相等: {expr4 == expr5}")

    print("\n5. 简化（恒等元）:")
    expr6 = ExprCache.add([x, zero])
    expr7 = ExprCache.mul([x, one])
    print(f"   add([x, 0]) = {expr6}")
    print(f"   mul([x, 1]) = {expr7}")

    print("\n6. 幂运算:")
    expr8 = ExprCache.pow(x, two)
    print(f"   pow(x, 2) = {expr8}")

    print("\n7. 哈希Consing（共享对象）:")
    a = ExprCache.symbol("a")
    b = ExprCache.symbol("a")
    print(f"   symbol('a') == symbol('a'): {a == b}")
    print(f"   symbol('a') is symbol('a'): {a is b}")

    print("\n8. AST 到 Canonical IR:")
    from latex_engine.parselet import parse_with_pratt
    ast = parse_with_pratt("x+0")
    canonical = from_ast(ast)
    print(f"   AST: x+0")
    print(f"   Canonical: {canonical}")
    simplified = simplify(canonical)
    print(f"   Simplified: {simplified}")

    print("\n" + "=" * 60)
    print("Canonical IR 测试完成！")
    print("=" * 60)