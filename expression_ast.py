"""expression_ast.py — 数学表达式抽象语法树

定义数学表达式的结构化表示，支持：
- 表达式解析（LaTeX → AST）
- 表达式等价性比较
- 符号计算
- AST 序列化/反序列化
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Union
from enum import Enum


class ExprType(Enum):
    """表达式类型枚举"""
    # 基本类型
    NUMBER = "number"
    VARIABLE = "variable"
    CONSTANT = "constant"  # 如 pi, e
    
    # 运算符
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    POW = "pow"
    NEG = "neg"
    
    # 函数
    FUNCTION = "function"
    
    # 微积分
    DERIVATIVE = "derivative"
    INTEGRAL = "integral"
    LIMIT = "limit"
    
    # 关系
    EQUALS = "equals"
    INEQUALITY = "inequality"


@dataclass(frozen=True)
class ExprNode:
    """表达式节点基类"""
    type: ExprType
    children: List['ExprNode'] = field(default_factory=list)
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        """计算表达式的值"""
        raise NotImplementedError
    
    def to_latex(self) -> str:
        """转换为 LaTeX 字符串"""
        raise NotImplementedError
    
    def simplify(self) -> 'ExprNode':
        """简化表达式"""
        return self
    
    def substitute(self, var: str, expr: 'ExprNode') -> 'ExprNode':
        """变量替换"""
        return self
    
    def __eq__(self, other: object) -> bool:
        """表达式等价性比较"""
        if not isinstance(other, ExprNode):
            return False
        if self.type != other.type:
            return False
        if len(self.children) != len(other.children):
            return False
        return all(c1 == c2 for c1, c2 in zip(self.children, other.children))
    
    def __hash__(self) -> int:
        return hash((self.type, tuple(self.children)))


@dataclass(frozen=True)
class Number(ExprNode):
    """数值节点"""
    value: float
    type: ExprType = field(default=ExprType.NUMBER, init=False)
    children: List['ExprNode'] = field(default_factory=list, init=False)
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        return self.value
    
    def to_latex(self) -> str:
        # 整数显示为整数形式
        if self.value == int(self.value):
            return str(int(self.value))
        return str(self.value)
    
    def simplify(self) -> 'Number':
        return self
    
    def substitute(self, var: str, expr: 'ExprNode') -> 'Number':
        return self
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Number):
            return abs(self.value - other.value) < 1e-10
        return False
    
    def __hash__(self) -> int:
        return hash(('number', round(self.value, 10)))


@dataclass(frozen=True)
class Variable(ExprNode):
    """变量节点"""
    name: str
    subscript: Optional[str] = None
    type: ExprType = field(default=ExprType.VARIABLE, init=False)
    children: List['ExprNode'] = field(default_factory=list, init=False)
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        if variables is None:
            raise ValueError(f"未提供变量 {self.name} 的值")
        key = self.name + (self.subscript if self.subscript else "")
        if key in variables:
            return variables[key]
        if self.name in variables:
            return variables[self.name]
        raise ValueError(f"未提供变量 {self.name} 的值")
    
    def to_latex(self) -> str:
        if self.subscript:
            return f"{self.name}_{{{self.subscript}}}"
        return self.name
    
    def simplify(self) -> 'Variable':
        return self
    
    def substitute(self, var: str, expr: 'ExprNode') -> 'ExprNode':
        if self.name == var:
            return expr
        return self
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Variable):
            return self.name == other.name and self.subscript == other.subscript
        return False
    
    def __hash__(self) -> int:
        return hash(('variable', self.name, self.subscript))


@dataclass(frozen=True)
class Constant(ExprNode):
    """常数节点（如 pi, e）"""
    name: str
    type: ExprType = field(default=ExprType.CONSTANT, init=False)
    children: List['ExprNode'] = field(default_factory=list, init=False)
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        constants = {
            'pi': 3.141592653589793,
            'e': 2.718281828459045,
            'pi/2': 1.5707963267948966,
            'pi/3': 1.0471975511965976,
        }
        if self.name.lower() in constants:
            return constants[self.name.lower()]
        raise ValueError(f"未知常数: {self.name}")
    
    def to_latex(self) -> str:
        if self.name == 'pi':
            return r'\pi'
        if self.name == 'e':
            return 'e'
        return self.name
    
    def simplify(self) -> 'Constant':
        return self
    
    def substitute(self, var: str, expr: 'ExprNode') -> 'Constant':
        return self


class BinaryOp(ExprNode):
    """二元运算节点"""
    
    def __init__(self, op_type: ExprType, left: ExprNode, right: ExprNode):
        object.__setattr__(self, 'type', op_type)
        object.__setattr__(self, 'left', left)
        object.__setattr__(self, 'right', right)
        object.__setattr__(self, 'children', [left, right])
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        left_val = self.left.evaluate(variables)
        right_val = self.right.evaluate(variables)
        
        if self.type == ExprType.ADD:
            return left_val + right_val
        elif self.type == ExprType.SUB:
            return left_val - right_val
        elif self.type == ExprType.MUL:
            return left_val * right_val
        elif self.type == ExprType.DIV:
            if right_val == 0:
                raise ZeroDivisionError
            return left_val / right_val
        elif self.type == ExprType.POW:
            return left_val ** right_val
        else:
            raise ValueError(f"未知运算符: {self.type}")
    
    def to_latex(self) -> str:
        left_latex = self.left.to_latex()
        right_latex = self.right.to_latex()
        
        # 添加必要的括号
        need_left_paren = isinstance(self.left, BinaryOp) and \
                         self.left.type.value in ['add', 'sub']
        need_right_paren = isinstance(self.right, BinaryOp) and \
                          (self.right.type.value in ['add', 'sub'] or 
                           (self.type.value in ['mul', 'div'] and 
                            self.right.type.value in ['mul', 'div']))
        
        if need_left_paren:
            left_latex = f"({left_latex})"
        if need_right_paren:
            right_latex = f"({right_latex})"
        
        if self.type == ExprType.ADD:
            return f"{left_latex} + {right_latex}"
        elif self.type == ExprType.SUB:
            return f"{left_latex} - {right_latex}"
        elif self.type == ExprType.MUL:
            return f"{left_latex} \\cdot {right_latex}"
        elif self.type == ExprType.DIV:
            return f"\\frac{{{left_latex}}}{{{right_latex}}}"
        elif self.type == ExprType.POW:
            return f"{left_latex}^{{{right_latex}}}"
        return ""
    
    def simplify(self) -> ExprNode:
        # 先简化子节点
        simplified_left = self.left.simplify()
        simplified_right = self.right.simplify()
        
        # 常量折叠
        if isinstance(simplified_left, Number) and isinstance(simplified_right, Number):
            try:
                return Number(self.evaluate())
            except Exception:
                pass
        
        # 简化规则
        if self.type == ExprType.ADD:
            # 0 + x = x
            if isinstance(simplified_left, Number) and simplified_left.value == 0:
                return simplified_right
            # x + 0 = x
            if isinstance(simplified_right, Number) and simplified_right.value == 0:
                return simplified_left
        elif self.type == ExprType.MUL:
            # 0 * x = 0
            if isinstance(simplified_left, Number) and simplified_left.value == 0:
                return Number(0)
            # x * 0 = 0
            if isinstance(simplified_right, Number) and simplified_right.value == 0:
                return Number(0)
            # 1 * x = x
            if isinstance(simplified_left, Number) and simplified_left.value == 1:
                return simplified_right
            # x * 1 = x
            if isinstance(simplified_right, Number) and simplified_right.value == 1:
                return simplified_left
        
        return BinaryOp(self.type, simplified_left, simplified_right)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        new_left = self.left.substitute(var, expr)
        new_right = self.right.substitute(var, expr)
        return BinaryOp(self.type, new_left, new_right)


class UnaryOp(ExprNode):
    """一元运算节点"""
    
    def __init__(self, op_type: ExprType, operand: ExprNode):
        object.__setattr__(self, 'type', op_type)
        object.__setattr__(self, 'operand', operand)
        object.__setattr__(self, 'children', [operand])
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        val = self.operand.evaluate(variables)
        if val is None:
            return None
        if self.type == ExprType.NEG:
            return -val
        return val
    
    def to_latex(self) -> str:
        operand_latex = self.operand.to_latex()
        need_paren = isinstance(self.operand, (BinaryOp, UnaryOp))
        
        if need_paren:
            operand_latex = f"({operand_latex})"
        
        if self.type == ExprType.NEG:
            return f"-{operand_latex}"
        return operand_latex
    
    def simplify(self) -> ExprNode:
        simplified_operand = self.operand.simplify()
        
        # 简化规则
        if self.type == ExprType.NEG:
            # -(-x) = x
            if isinstance(simplified_operand, UnaryOp) and simplified_operand.type == ExprType.NEG:
                return simplified_operand.operand
            # -(0) = 0
            if isinstance(simplified_operand, Number) and simplified_operand.value == 0:
                return Number(0)
        
        return UnaryOp(self.type, simplified_operand)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        new_operand = self.operand.substitute(var, expr)
        return UnaryOp(self.type, new_operand)


class Function(ExprNode):
    """函数节点"""
    
    def __init__(self, name: str, args: List[ExprNode]):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'args', args)
        object.__setattr__(self, 'type', ExprType.FUNCTION)
        object.__setattr__(self, 'children', args)
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        import math

        args_val = [arg.evaluate(variables) for arg in self.args]
        if not args_val or any(v is None for v in args_val):
            return None
        name = self.name.lower()

        if name == 'sin':
            return math.sin(args_val[0])
        elif name == 'cos':
            return math.cos(args_val[0])
        elif name == 'tan':
            return math.tan(args_val[0])
        elif name == 'ln':
            return math.log(args_val[0])
        elif name == 'log':
            return math.log10(args_val[0])
        elif name == 'sqrt':
            return math.sqrt(args_val[0])
        elif name == 'exp':
            return math.exp(args_val[0])
        elif name == 'abs':
            return abs(args_val[0])
        elif name == 'sin^2':
            return math.sin(args_val[0]) ** 2
        elif name == 'cos^2':
            return math.cos(args_val[0]) ** 2
        else:
            raise ValueError(f"未知函数: {self.name}")
    
    def to_latex(self) -> str:
        args_latex = ', '.join(arg.to_latex() for arg in self.args)
        
        # 常见函数不需要括号
        simple_funcs = ['sin', 'cos', 'tan', 'ln', 'log', 'sqrt', 'exp', 'abs']
        if self.name in simple_funcs and len(self.args) == 1:
            return f"\\{self.name}{{{args_latex}}}"
        return f"{self.name}(\\{args_latex})"
    
    def simplify(self) -> ExprNode:
        simplified_args = [arg.simplify() for arg in self.args]
        
        # 常量折叠
        if all(isinstance(arg, Number) for arg in simplified_args):
            try:
                return Number(self.evaluate())
            except Exception:
                pass
        
        return Function(self.name, simplified_args)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        new_args = [arg.substitute(var, expr) for arg in self.args]
        return Function(self.name, new_args)


class Derivative(ExprNode):
    """导数节点"""
    
    def __init__(self, expr: ExprNode, var: Variable, order: int = 1):
        object.__setattr__(self, 'expr', expr)
        object.__setattr__(self, 'var', var)
        object.__setattr__(self, 'order', order)
        object.__setattr__(self, 'type', ExprType.DERIVATIVE)
        object.__setattr__(self, 'children', [expr])
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        # 数值微分
        h = 1e-5
        var_name = self.var.name + (self.var.subscript or "")
        
        # 计算 f(x+h) - f(x-h) / 2h
        vars_plus = (variables or {}).copy()
        vars_minus = (variables or {}).copy()
        
        current_val = variables.get(var_name, 0) if variables else 0
        vars_plus[var_name] = current_val + h
        vars_minus[var_name] = current_val - h
        
        f_plus = self.expr.evaluate(vars_plus)
        f_minus = self.expr.evaluate(vars_minus)
        
        return (f_plus - f_minus) / (2 * h)
    
    def to_latex(self) -> str:
        var_latex = self.var.to_latex()
        expr_latex = self.expr.to_latex()
        
        if self.order == 1:
            return f"\\frac{{d}}{{d{var_latex}}}{{{expr_latex}}}"
        else:
            return f"\\frac{{d^{{{self.order}}}}}{{d{var_latex}^{{{self.order}}}}}{{{expr_latex}}}"
    
    def simplify(self) -> ExprNode:
        simplified_expr = self.expr.simplify()
        return Derivative(simplified_expr, self.var, self.order)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        if self.var.name == var:
            return self  # 不能替换求导变量
        new_expr = self.expr.substitute(var, expr)
        return Derivative(new_expr, self.var, self.order)


class Integral(ExprNode):
    """积分节点"""
    
    def __init__(self, expr: ExprNode, var: Variable, 
                 lower_bound: Optional[ExprNode] = None, 
                 upper_bound: Optional[ExprNode] = None):
        object.__setattr__(self, 'expr', expr)
        object.__setattr__(self, 'var', var)
        object.__setattr__(self, 'lower_bound', lower_bound)
        object.__setattr__(self, 'upper_bound', upper_bound)
        object.__setattr__(self, 'type', ExprType.INTEGRAL)
        object.__setattr__(self, 'children', [expr])
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        # 使用数值积分（梯形法）
        if self.lower_bound is None or self.upper_bound is None:
            raise ValueError("只能计算定积分")
        
        a = self.lower_bound.evaluate(variables)
        b = self.upper_bound.evaluate(variables)
        
        n = 1000
        h = (b - a) / n
        var_name = self.var.name + (self.var.subscript or "")
        
        total = 0.0
        for i in range(n):
            x0 = a + i * h
            x1 = a + (i + 1) * h
            
            vars0 = (variables or {}).copy()
            vars1 = (variables or {}).copy()
            vars0[var_name] = x0
            vars1[var_name] = x1
            
            f0 = self.expr.evaluate(vars0)
            f1 = self.expr.evaluate(vars1)
            
            total += (f0 + f1) * h / 2
        
        return total
    
    def to_latex(self) -> str:
        var_latex = self.var.to_latex()
        expr_latex = self.expr.to_latex()
        
        if self.lower_bound is not None and self.upper_bound is not None:
            lower = self.lower_bound.to_latex()
            upper = self.upper_bound.to_latex()
            return f"\\int_{{{lower}}}^{{{upper}}} {expr_latex} d{var_latex}"
        else:
            return f"\\int {expr_latex} d{var_latex}"
    
    def simplify(self) -> ExprNode:
        simplified_expr = self.expr.simplify()
        simplified_lower = self.lower_bound.simplify() if self.lower_bound else None
        simplified_upper = self.upper_bound.simplify() if self.upper_bound else None
        return Integral(simplified_expr, self.var, simplified_lower, simplified_upper)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        if self.var.name == var:
            return self  # 不能替换积分变量
        new_expr = self.expr.substitute(var, expr)
        new_lower = self.lower_bound.substitute(var, expr) if self.lower_bound else None
        new_upper = self.upper_bound.substitute(var, expr) if self.upper_bound else None
        return Integral(new_expr, self.var, new_lower, new_upper)


class Limit(ExprNode):
    """极限节点"""
    
    def __init__(self, expr: ExprNode, var: Variable, approach: ExprNode):
        object.__setattr__(self, 'expr', expr)
        object.__setattr__(self, 'var', var)
        object.__setattr__(self, 'approach', approach)
        object.__setattr__(self, 'type', ExprType.LIMIT)
        object.__setattr__(self, 'children', [expr])
    
    def evaluate(self, variables: Dict[str, float] = None) -> float:
        # 数值逼近
        target = self.approach.evaluate(variables)
        var_name = self.var.name + (self.var.subscript or "")
        
        # 从两边逼近
        h = 1e-10
        vars_plus = (variables or {}).copy()
        vars_minus = (variables or {}).copy()
        
        vars_plus[var_name] = target + h
        vars_minus[var_name] = target - h
        
        try:
            f_plus = self.expr.evaluate(vars_plus)
            f_minus = self.expr.evaluate(vars_minus)

            # 返回平均值
            return (f_plus + f_minus) / 2
        except Exception:
            # 如果一边失败，尝试另一边
            try:
                return self.expr.evaluate(vars_plus)
            except Exception:
                try:
                    return self.expr.evaluate(vars_minus)
                except Exception:
                    raise ValueError("无法计算极限")
    
    def to_latex(self) -> str:
        var_latex = self.var.to_latex()
        expr_latex = self.expr.to_latex()
        approach_latex = self.approach.to_latex()
        
        return f"\\lim_{{{var_latex} \\to {approach_latex}}} {expr_latex}"
    
    def simplify(self) -> ExprNode:
        simplified_expr = self.expr.simplify()
        simplified_approach = self.approach.simplify()
        return Limit(simplified_expr, self.var, simplified_approach)
    
    def substitute(self, var: str, expr: ExprNode) -> ExprNode:
        if self.var.name == var:
            return self  # 不能替换极限变量
        new_expr = self.expr.substitute(var, expr)
        new_approach = self.approach.substitute(var, expr)
        return Limit(new_expr, self.var, new_approach)


# 便捷函数
def add(left: ExprNode, right: ExprNode) -> ExprNode:
    """创建加法表达式"""
    return BinaryOp(ExprType.ADD, left, right)


def sub(left: ExprNode, right: ExprNode) -> ExprNode:
    """创建减法表达式"""
    return BinaryOp(ExprType.SUB, left, right)


def mul(left: ExprNode, right: ExprNode) -> ExprNode:
    """创建乘法表达式"""
    return BinaryOp(ExprType.MUL, left, right)


def div(left: ExprNode, right: ExprNode) -> ExprNode:
    """创建除法表达式"""
    return BinaryOp(ExprType.DIV, left, right)


def pow(base: ExprNode, exp: ExprNode) -> ExprNode:
    """创建幂表达式"""
    return BinaryOp(ExprType.POW, base, exp)


def neg(expr: ExprNode) -> ExprNode:
    """创建取负表达式"""
    return UnaryOp(ExprType.NEG, expr)


def sin(expr: ExprNode) -> ExprNode:
    """创建正弦函数"""
    return Function('sin', [expr])


def cos(expr: ExprNode) -> ExprNode:
    """创建余弦函数"""
    return Function('cos', [expr])


def ln(expr: ExprNode) -> ExprNode:
    """创建自然对数"""
    return Function('ln', [expr])


def sqrt(expr: ExprNode) -> ExprNode:
    """创建平方根"""
    return Function('sqrt', [expr])


def exp(expr: ExprNode) -> ExprNode:
    """创建指数函数"""
    return Function('exp', [expr])


def derivative(expr: ExprNode, var: Variable, order: int = 1) -> ExprNode:
    """创建导数表达式"""
    return Derivative(expr, var, order)


def integral(expr: ExprNode, var: Variable, 
             lower: Optional[ExprNode] = None, 
             upper: Optional[ExprNode] = None) -> ExprNode:
    """创建积分表达式"""
    return Integral(expr, var, lower, upper)


def limit(expr: ExprNode, var: Variable, approach: ExprNode) -> ExprNode:
    """创建极限表达式"""
    return Limit(expr, var, approach)