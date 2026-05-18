"""Math AST - 数学抽象语法树节点定义

这是整个数学语言操作系统的核心数据结构，所有层（渲染、推理、语义分析、证明引擎）都共享此 AST。
"""

from __future__ import annotations
from typing import List, Optional, Union, Any
from abc import ABC, abstractmethod
from .types import MathType


class ASTNode(ABC):
    """所有 AST 节点的基类"""
    
    @abstractmethod
    def to_latex(self) -> str:
        """将节点转换为 LaTeX 字符串"""
        pass
    
    @abstractmethod
    def to_ast(self) -> dict:
        """将节点转换为 JSON 可序列化的字典表示"""
        pass
    
    def __repr__(self) -> str:
        return self.to_latex()


class TypedNode(ASTNode):
    """带类型信息的节点基类"""
    
    def __init__(self, math_type: Optional[MathType] = None):
        self.math_type = math_type
    
    def to_ast(self) -> dict:
        """将节点转换为 JSON 可序列化的字典表示（包含类型信息）"""
        result = self._to_ast_without_type()
        if self.math_type is not None:
            result['math_type'] = self.math_type.name
        return result
    
    @abstractmethod
    def _to_ast_without_type(self) -> dict:
        """返回不含类型信息的 AST 字典"""
        pass


class SymbolNode(TypedNode):
    """符号节点 - 代表变量、常量符号"""
    
    def __init__(self, name: str, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.name = name
    
    def to_latex(self) -> str:
        return self.name
    
    def _to_ast_without_type(self) -> dict:
        return {"type": "SymbolNode", "name": self.name}


class NumberNode(TypedNode):
    """数字节点 - 代表数值"""
    
    def __init__(self, value: Union[int, float, str], math_type: Optional[MathType] = None):
        # 根据值推断类型
        inferred_type = math_type
        if inferred_type is None:
            if isinstance(value, int):
                inferred_type = MathType.INTEGER
            elif isinstance(value, float):
                inferred_type = MathType.REAL
            elif isinstance(value, str):
                if '.' in value:
                    inferred_type = MathType.REAL
                else:
                    inferred_type = MathType.INTEGER
        
        super().__init__(inferred_type)
        self.value = value
    
    def to_latex(self) -> str:
        return str(self.value)
    
    def _to_ast_without_type(self) -> dict:
        return {"type": "NumberNode", "value": self.value}


class CommandNode(TypedNode):
    r"""命令节点 - 代表 LaTeX 命令（如 \sin, \cos）"""
    
    def __init__(self, name: str, args: List[ASTNode] = None, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.name = name
        self.args = args or []
    
    def to_latex(self) -> str:
        arg_str = "".join(f"{{{arg.to_latex()}}}" for arg in self.args)
        return f"\\{self.name}{arg_str}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "CommandNode",
            "name": self.name,
            "args": [arg.to_ast() for arg in self.args]
        }


class GroupNode(TypedNode):
    """分组节点 - 代表花括号包裹的内容 { ... }"""
    
    def __init__(self, content: List[ASTNode], math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.content = content
    
    def to_latex(self) -> str:
        return "{" + "".join(node.to_latex() for node in self.content) + "}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "GroupNode",
            "content": [node.to_ast() for node in self.content]
        }


class FractionNode(TypedNode):
    """分数节点"""
    
    def __init__(self, numerator: ASTNode, denominator: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.numerator = numerator
        self.denominator = denominator
    
    def to_latex(self) -> str:
        return f"\\frac{{{self.numerator.to_latex()}}}{{{self.denominator.to_latex()}}}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "FractionNode",
            "numerator": self.numerator.to_ast(),
            "denominator": self.denominator.to_ast()
        }


class SuperscriptNode(TypedNode):
    """上标节点"""
    
    def __init__(self, base: ASTNode, exponent: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.base = base
        self.exponent = exponent
    
    def to_latex(self) -> str:
        return f"{self.base.to_latex()}^{{{self.exponent.to_latex()}}}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "SuperscriptNode",
            "base": self.base.to_ast(),
            "exponent": self.exponent.to_ast()
        }


class SubscriptNode(TypedNode):
    """下标节点"""
    
    def __init__(self, base: ASTNode, subscript: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.base = base
        self.subscript = subscript
    
    def to_latex(self) -> str:
        return f"{self.base.to_latex()}_{{{self.subscript.to_latex()}}}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "SubscriptNode",
            "base": self.base.to_ast(),
            "subscript": self.subscript.to_ast()
        }


class FunctionNode(TypedNode):
    """函数节点 - 代表数学函数（如 sin, cos, log）"""
    
    def __init__(self, name: str, arguments: List[ASTNode], math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.name = name
        self.arguments = arguments
    
    def to_latex(self) -> str:
        if len(self.arguments) == 0:
            return f"\\{self.name}"
        args_str = ",".join(arg.to_latex() for arg in self.arguments)
        return f"\\{self.name}({args_str})"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "FunctionNode",
            "name": self.name,
            "arguments": [arg.to_ast() for arg in self.arguments]
        }


class SequenceNode(TypedNode):
    """序列节点 - 代表多个节点的顺序组合"""
    
    def __init__(self, elements: List[ASTNode], math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.elements = elements
    
    def to_latex(self) -> str:
        return "".join(elem.to_latex() for elem in self.elements)
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "SequenceNode",
            "elements": [elem.to_ast() for elem in self.elements]
        }


class OperatorNode(TypedNode):
    """运算符节点"""
    
    def __init__(self, operator: str, left: Optional[ASTNode] = None, right: Optional[ASTNode] = None, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.operator = operator
        self.left = left
        self.right = right
    
    def to_latex(self) -> str:
        parts = []
        if self.left:
            parts.append(self.left.to_latex())
        parts.append(self.operator)
        if self.right:
            parts.append(self.right.to_latex())
        return "".join(parts)
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "OperatorNode",
            "operator": self.operator,
            "left": self.left.to_ast() if self.left else None,
            "right": self.right.to_ast() if self.right else None
        }


# ═══════════════════════════════════════════════
# 语义运算符节点（Semantic Operator Nodes）
# ═══════════════════════════════════════════════

class AddNode(TypedNode):
    """加法节点"""
    
    def __init__(self, left: ASTNode, right: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.left = left
        self.right = right
    
    def to_latex(self) -> str:
        return f"{self.left.to_latex()} + {self.right.to_latex()}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "AddNode",
            "left": self.left.to_ast(),
            "right": self.right.to_ast()
        }


class SubtractNode(TypedNode):
    """减法节点"""
    
    def __init__(self, left: ASTNode, right: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.left = left
        self.right = right
    
    def to_latex(self) -> str:
        return f"{self.left.to_latex()} - {self.right.to_latex()}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "SubtractNode",
            "left": self.left.to_ast(),
            "right": self.right.to_ast()
        }


class MultiplyNode(TypedNode):
    """乘法节点"""
    
    def __init__(self, left: ASTNode, right: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.left = left
        self.right = right
    
    def to_latex(self) -> str:
        # 根据操作数类型决定是否需要乘号
        left_str = self.left.to_latex()
        right_str = self.right.to_latex()
        
        # 数字之间需要乘号
        if isinstance(self.left, NumberNode) and isinstance(self.right, NumberNode):
            return f"{left_str} \\cdot {right_str}"
        
        # 数字和符号之间不需要乘号
        return f"{left_str}{right_str}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "MultiplyNode",
            "left": self.left.to_ast(),
            "right": self.right.to_ast()
        }


class DivideNode(TypedNode):
    """除法节点"""
    
    def __init__(self, numerator: ASTNode, denominator: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.numerator = numerator
        self.denominator = denominator
    
    def to_latex(self) -> str:
        # 如果分母是单个符号或数字，使用斜杠表示
        if isinstance(self.denominator, (SymbolNode, NumberNode)):
            return f"{self.numerator.to_latex()} / {self.denominator.to_latex()}"
        # 否则使用分数形式
        return f"\\frac{{{self.numerator.to_latex()}}}{{{self.denominator.to_latex()}}}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "DivideNode",
            "numerator": self.numerator.to_ast(),
            "denominator": self.denominator.to_ast()
        }


class PowerNode(TypedNode):
    """幂运算节点"""
    
    def __init__(self, base: ASTNode, exponent: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.base = base
        self.exponent = exponent
    
    def to_latex(self) -> str:
        base_str = self.base.to_latex()
        exponent_str = self.exponent.to_latex()
        
        # 如果底数是复杂表达式，需要括号
        if isinstance(self.base, (AddNode, SubtractNode, MultiplyNode, DivideNode)):
            base_str = f"({base_str})"
        
        return f"{base_str}^{{{exponent_str}}}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "PowerNode",
            "base": self.base.to_ast(),
            "exponent": self.exponent.to_ast()
        }


class NegateNode(TypedNode):
    """取反节点（一元负号）"""
    
    def __init__(self, operand: ASTNode, math_type: Optional[MathType] = None):
        super().__init__(math_type)
        self.operand = operand
    
    def to_latex(self) -> str:
        operand_str = self.operand.to_latex()
        
        # 如果操作数是复杂表达式，需要括号
        if isinstance(self.operand, (AddNode, SubtractNode, MultiplyNode, DivideNode, PowerNode)):
            operand_str = f"({operand_str})"
        
        return f"-{operand_str}"
    
    def _to_ast_without_type(self) -> dict:
        return {
            "type": "NegateNode",
            "operand": self.operand.to_ast()
        }


class IntegralNode(ASTNode):
    """积分节点"""
    
    def __init__(
        self,
        integrand: ASTNode,
        variable: Optional[ASTNode] = None,
        lower_limit: Optional[ASTNode] = None,
        upper_limit: Optional[ASTNode] = None,
        integral_type: str = "int"  # int, iint, iiint, oint
    ):
        self.integrand = integrand
        self.variable = variable
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.integral_type = integral_type
    
    def to_latex(self) -> str:
        result = f"\\{self.integral_type}"
        if self.lower_limit:
            result += f"_{{{self.lower_limit.to_latex()}}}"
        if self.upper_limit:
            result += f"^{{{self.upper_limit.to_latex()}}}"
        result += self.integrand.to_latex()
        if self.variable:
            result += f"\\,\\mathrm{{d}}{self.variable.to_latex()}"
        return result
    
    def to_ast(self) -> dict:
        return {
            "type": "IntegralNode",
            "integrand": self.integrand.to_ast(),
            "variable": self.variable.to_ast() if self.variable else None,
            "lower_limit": self.lower_limit.to_ast() if self.lower_limit else None,
            "upper_limit": self.upper_limit.to_ast() if self.upper_limit else None,
            "integral_type": self.integral_type
        }


class SumNode(ASTNode):
    """求和节点"""
    
    def __init__(
        self,
        term: ASTNode,
        index: Optional[ASTNode] = None,
        lower_limit: Optional[ASTNode] = None,
        upper_limit: Optional[ASTNode] = None
    ):
        self.term = term
        self.index = index
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
    
    def to_latex(self) -> str:
        result = "\\sum"
        if self.lower_limit:
            result += f"_{{{self.lower_limit.to_latex()}}}"
        if self.upper_limit:
            result += f"^{{{self.upper_limit.to_latex()}}}"
        result += self.term.to_latex()
        return result
    
    def to_ast(self) -> dict:
        return {
            "type": "SumNode",
            "term": self.term.to_ast(),
            "index": self.index.to_ast() if self.index else None,
            "lower_limit": self.lower_limit.to_ast() if self.lower_limit else None,
            "upper_limit": self.upper_limit.to_ast() if self.upper_limit else None
        }


class ProductNode(ASTNode):
    """乘积节点"""
    
    def __init__(
        self,
        term: ASTNode,
        index: Optional[ASTNode] = None,
        lower_limit: Optional[ASTNode] = None,
        upper_limit: Optional[ASTNode] = None
    ):
        self.term = term
        self.index = index
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
    
    def to_latex(self) -> str:
        result = "\\prod"
        if self.lower_limit:
            result += f"_{{{self.lower_limit.to_latex()}}}"
        if self.upper_limit:
            result += f"^{{{self.upper_limit.to_latex()}}}"
        result += self.term.to_latex()
        return result
    
    def to_ast(self) -> dict:
        return {
            "type": "ProductNode",
            "term": self.term.to_ast(),
            "index": self.index.to_ast() if self.index else None,
            "lower_limit": self.lower_limit.to_ast() if self.lower_limit else None,
            "upper_limit": self.upper_limit.to_ast() if self.upper_limit else None
        }


class SqrtNode(ASTNode):
    """根号节点"""
    
    def __init__(self, radicand: ASTNode, degree: Optional[ASTNode] = None):
        self.radicand = radicand
        self.degree = degree
    
    def to_latex(self) -> str:
        if self.degree:
            return f"\\sqrt[{self.degree.to_latex()}]{{{self.radicand.to_latex()}}}"
        return f"\\sqrt{{{self.radicand.to_latex()}}}"
    
    def to_ast(self) -> dict:
        return {
            "type": "SqrtNode",
            "radicand": self.radicand.to_ast(),
            "degree": self.degree.to_ast() if self.degree else None
        }


class TextNode(ASTNode):
    """文本节点 - 代表 \text{...} 中的内容"""
    
    def __init__(self, content: str):
        self.content = content
    
    def to_latex(self) -> str:
        return f"\\text{{{self.content}}}"
    
    def to_ast(self) -> dict:
        return {"type": "TextNode", "content": self.content}


class BracesNode(ASTNode):
    """括号节点 - 代表分组但不改变语义"""
    
    def __init__(self, content: ASTNode):
        self.content = content
    
    def to_latex(self) -> str:
        return f"({self.content.to_latex()})"
    
    def to_ast(self) -> dict:
        return {
            "type": "BracesNode",
            "content": self.content.to_ast()
        }


class MatrixNode(ASTNode):
    """矩阵节点"""
    
    def __init__(self, rows: List[List[ASTNode]], matrix_type: str = "matrix"):
        self.rows = rows
        self.matrix_type = matrix_type  # matrix, pmatrix, bmatrix, vmatrix, Vmatrix
    
    def to_latex(self) -> str:
        rows_str = "\\\\".join(
            "&".join(cell.to_latex() for cell in row)
            for row in self.rows
        )
        return f"\\begin{{{self.matrix_type}}}{rows_str}\\end{{{self.matrix_type}}}"
    
    def to_ast(self) -> dict:
        return {
            "type": "MatrixNode",
            "rows": [[cell.to_ast() for cell in row] for row in self.rows],
            "matrix_type": self.matrix_type
        }


class CasesNode(ASTNode):
    """分段函数节点"""
    
    def __init__(self, cases: List[tuple]):
        """cases: list of (condition, value) tuples"""
        self.cases = cases
    
    def to_latex(self) -> str:
        cases_str = "\\\\".join(
            f"{value.to_latex()} & {condition.to_latex()}"
            for condition, value in self.cases
        )
        return f"\\begin{{cases}}{cases_str}\\end{{cases}}"
    
    def to_ast(self) -> dict:
        return {
            "type": "CasesNode",
            "cases": [
                {"condition": cond.to_ast(), "value": val.to_ast()}
                for cond, val in self.cases
            ]
        }


class LimitNode(ASTNode):
    """极限节点"""
    
    def __init__(self, expression: ASTNode, variable: ASTNode, target: ASTNode):
        self.expression = expression
        self.variable = variable
        self.target = target
    
    def to_latex(self) -> str:
        return f"\\lim_{{{self.variable.to_latex()} \\to {self.target.to_latex()}}}{self.expression.to_latex()}"
    
    def to_ast(self) -> dict:
        return {
            "type": "LimitNode",
            "expression": self.expression.to_ast(),
            "variable": self.variable.to_ast(),
            "target": self.target.to_ast()
        }


class DerivativeNode(ASTNode):
    """导数节点"""
    
    def __init__(
        self,
        numerator: ASTNode,
        denominator: ASTNode,
        order: int = 1,
        partial: bool = False
    ):
        self.numerator = numerator
        self.denominator = denominator
        self.order = order
        self.partial = partial
    
    def to_latex(self) -> str:
        op = "\\partial" if self.partial else "d"
        if self.order == 1:
            return f"\\frac{{{op}{self.numerator.to_latex()}}}{{{op}{self.denominator.to_latex()}}}"
        return f"\\frac{{{op}^{{{self.order}}}{self.numerator.to_latex()}}}{{{op}{self.denominator.to_latex()}^{{{self.order}}}}}"
    
    def to_ast(self) -> dict:
        return {
            "type": "DerivativeNode",
            "numerator": self.numerator.to_ast(),
            "denominator": self.denominator.to_ast(),
            "order": self.order,
            "partial": self.partial
        }


class SetNode(ASTNode):
    """集合节点"""
    
    def __init__(self, elements: List[ASTNode], is_infinite: bool = False):
        self.elements = elements
        self.is_infinite = is_infinite
    
    def to_latex(self) -> str:
        if self.is_infinite:
            return "\\mathbb{R}" if len(self.elements) == 0 else "{" + ", ".join(e.to_latex() for e in self.elements) + ", \\ldots}"
        return "\\{" + ", ".join(e.to_latex() for e in self.elements) + "\\}"
    
    def to_ast(self) -> dict:
        return {
            "type": "SetNode",
            "elements": [e.to_ast() for e in self.elements],
            "is_infinite": self.is_infinite
        }


class EquationNode(ASTNode):
    """方程节点"""
    
    def __init__(self, left: ASTNode, right: ASTNode, relation: str = "="):
        self.left = left
        self.right = right
        self.relation = relation
    
    def to_latex(self) -> str:
        return f"{self.left.to_latex()} {self.relation} {self.right.to_latex()}"
    
    def to_ast(self) -> dict:
        return {
            "type": "EquationNode",
            "left": self.left.to_ast(),
            "right": self.right.to_ast(),
            "relation": self.relation
        }


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def build_sequence(*nodes: ASTNode) -> SequenceNode:
    """构建序列节点"""
    return SequenceNode(list(nodes))


def parse_ast(ast_dict: dict) -> ASTNode:
    """从字典解析 AST 节点"""
    node_type = ast_dict["type"]
    
    if node_type == "SymbolNode":
        return SymbolNode(ast_dict["name"])
    elif node_type == "NumberNode":
        return NumberNode(ast_dict["value"])
    elif node_type == "CommandNode":
        args = [parse_ast(arg) for arg in ast_dict["args"]]
        return CommandNode(ast_dict["name"], args)
    elif node_type == "GroupNode":
        content = [parse_ast(c) for c in ast_dict["content"]]
        return GroupNode(content)
    elif node_type == "FractionNode":
        numerator = parse_ast(ast_dict["numerator"])
        denominator = parse_ast(ast_dict["denominator"])
        return FractionNode(numerator, denominator)
    elif node_type == "SuperscriptNode":
        base = parse_ast(ast_dict["base"])
        exponent = parse_ast(ast_dict["exponent"])
        return SuperscriptNode(base, exponent)
    elif node_type == "SubscriptNode":
        base = parse_ast(ast_dict["base"])
        subscript = parse_ast(ast_dict["subscript"])
        return SubscriptNode(base, subscript)
    elif node_type == "FunctionNode":
        args = [parse_ast(arg) for arg in ast_dict["arguments"]]
        return FunctionNode(ast_dict["name"], args)
    elif node_type == "SequenceNode":
        elements = [parse_ast(e) for e in ast_dict["elements"]]
        return SequenceNode(elements)
    elif node_type == "OperatorNode":
        left = parse_ast(ast_dict["left"]) if ast_dict["left"] else None
        right = parse_ast(ast_dict["right"]) if ast_dict["right"] else None
        return OperatorNode(ast_dict["operator"], left, right)
    # ═══════════════════════════════════════════════
    # 语义运算符节点
    # ═══════════════════════════════════════════════
    elif node_type == "AddNode":
        left = parse_ast(ast_dict["left"])
        right = parse_ast(ast_dict["right"])
        return AddNode(left, right)
    elif node_type == "SubtractNode":
        left = parse_ast(ast_dict["left"])
        right = parse_ast(ast_dict["right"])
        return SubtractNode(left, right)
    elif node_type == "MultiplyNode":
        left = parse_ast(ast_dict["left"])
        right = parse_ast(ast_dict["right"])
        return MultiplyNode(left, right)
    elif node_type == "DivideNode":
        numerator = parse_ast(ast_dict["numerator"])
        denominator = parse_ast(ast_dict["denominator"])
        return DivideNode(numerator, denominator)
    elif node_type == "PowerNode":
        base = parse_ast(ast_dict["base"])
        exponent = parse_ast(ast_dict["exponent"])
        return PowerNode(base, exponent)
    elif node_type == "NegateNode":
        operand = parse_ast(ast_dict["operand"])
        return NegateNode(operand)
    elif node_type == "IntegralNode":
        integrand = parse_ast(ast_dict["integrand"])
        variable = parse_ast(ast_dict["variable"]) if ast_dict["variable"] else None
        lower_limit = parse_ast(ast_dict["lower_limit"]) if ast_dict["lower_limit"] else None
        upper_limit = parse_ast(ast_dict["upper_limit"]) if ast_dict["upper_limit"] else None
        return IntegralNode(integrand, variable, lower_limit, upper_limit, ast_dict["integral_type"])
    elif node_type == "SumNode":
        term = parse_ast(ast_dict["term"])
        index = parse_ast(ast_dict["index"]) if ast_dict["index"] else None
        lower_limit = parse_ast(ast_dict["lower_limit"]) if ast_dict["lower_limit"] else None
        upper_limit = parse_ast(ast_dict["upper_limit"]) if ast_dict["upper_limit"] else None
        return SumNode(term, index, lower_limit, upper_limit)
    elif node_type == "ProductNode":
        term = parse_ast(ast_dict["term"])
        index = parse_ast(ast_dict["index"]) if ast_dict["index"] else None
        lower_limit = parse_ast(ast_dict["lower_limit"]) if ast_dict["lower_limit"] else None
        upper_limit = parse_ast(ast_dict["upper_limit"]) if ast_dict["upper_limit"] else None
        return ProductNode(term, index, lower_limit, upper_limit)
    elif node_type == "SqrtNode":
        radicand = parse_ast(ast_dict["radicand"])
        degree = parse_ast(ast_dict["degree"]) if ast_dict["degree"] else None
        return SqrtNode(radicand, degree)
    elif node_type == "TextNode":
        return TextNode(ast_dict["content"])
    elif node_type == "BracesNode":
        content = parse_ast(ast_dict["content"])
        return BracesNode(content)
    elif node_type == "MatrixNode":
        rows = [[parse_ast(cell) for cell in row] for row in ast_dict["rows"]]
        return MatrixNode(rows, ast_dict["matrix_type"])
    elif node_type == "CasesNode":
        cases = [
            (parse_ast(c["condition"]), parse_ast(c["value"]))
            for c in ast_dict["cases"]
        ]
        return CasesNode(cases)
    elif node_type == "LimitNode":
        expression = parse_ast(ast_dict["expression"])
        variable = parse_ast(ast_dict["variable"])
        target = parse_ast(ast_dict["target"])
        return LimitNode(expression, variable, target)
    elif node_type == "DerivativeNode":
        numerator = parse_ast(ast_dict["numerator"])
        denominator = parse_ast(ast_dict["denominator"])
        return DerivativeNode(numerator, denominator, ast_dict["order"], ast_dict["partial"])
    elif node_type == "SetNode":
        elements = [parse_ast(e) for e in ast_dict["elements"]]
        return SetNode(elements, ast_dict["is_infinite"])
    elif node_type == "EquationNode":
        left = parse_ast(ast_dict["left"])
        right = parse_ast(ast_dict["right"])
        return EquationNode(left, right, ast_dict["relation"])
    
    raise ValueError(f"Unknown AST node type: {node_type}")