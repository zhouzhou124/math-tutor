"""AST Pretty Printer - AST 美化输出器

提供 AST 的树形可视化输出，便于调试和验证。
"""

from typing import List, Dict, Optional
from .ast import *


class ASTPrinter:
    """AST 美化输出器"""
    
    def __init__(self, indent: int = 2, show_types: bool = True):
        self.indent = indent
        self.show_types = show_types
    
    def print(self, node: ASTNode, prefix: str = "") -> str:
        """输出 AST 的树形表示"""
        return self._print_node(node, prefix, "")
    
    def _print_node(self, node: ASTNode, prefix: str, branch: str) -> str:
        """递归打印节点"""
        if node is None:
            return "None"
        
        node_type = type(node).__name__
        
        # 获取节点的显示信息
        info = self._get_node_info(node)
        
        # 构建节点行
        line = f"{branch}{node_type}"
        if info:
            line += f": {info}"
        
        # 添加类型信息
        if self.show_types and isinstance(node, TypedNode) and node.math_type:
            line += f" ({node.math_type.name})"
        
        result = line + "\n"
        
        # 获取子节点
        children = self._get_children(node)
        
        # 打印子节点
        num_children = len(children)
        for i, (child_name, child_node) in enumerate(children):
            is_last = (i == num_children - 1)
            
            # 更新前缀
            new_prefix = prefix + ("    " if is_last else "│   ")
            new_branch = prefix + ("└── " if is_last else "├── ")
            
            # 添加子节点名称
            child_line = f"{new_branch}{child_name}:"
            result += child_line + "\n"
            
            # 递归打印子节点
            result += self._print_node(child_node, new_prefix, new_prefix + "    ")
        
        return result
    
    def _get_node_info(self, node: ASTNode) -> str:
        """获取节点的显示信息"""
        if isinstance(node, NumberNode):
            return str(node.value)
        elif isinstance(node, SymbolNode):
            return node.name
        elif isinstance(node, FunctionNode):
            return node.name
        elif isinstance(node, OperatorNode):
            return node.operator
        elif isinstance(node, CommandNode):
            return f"\\{node.name}"
        elif isinstance(node, EquationNode):
            return node.relation
        elif isinstance(node, NegateNode):
            return "-"
        elif isinstance(node, AddNode):
            return "+"
        elif isinstance(node, SubtractNode):
            return "-"
        elif isinstance(node, MultiplyNode):
            return "*"
        elif isinstance(node, DivideNode):
            return "/"
        elif isinstance(node, PowerNode):
            return "^"
        elif isinstance(node, LimitNode):
            return "lim"
        elif isinstance(node, SumNode):
            return "sum"
        elif isinstance(node, ProductNode):
            return "prod"
        elif isinstance(node, IntegralNode):
            return f"∫{node.integral_type or ''}"
        elif isinstance(node, MatrixNode):
            rows = len(node.rows) if node.rows else 0
            cols = len(node.rows[0]) if node.rows and node.rows[0] else 0
            return f"{rows}×{cols}"
        elif isinstance(node, SetNode):
            count = len(node.elements) if node.elements else 0
            return f"{count} elements"
        elif isinstance(node, SequenceNode):
            count = len(node.elements) if node.elements else 0
            return f"{count} elements"
        elif isinstance(node, TextNode):
            return repr(node.text)
        else:
            return ""
    
    def _get_children(self, node: ASTNode) -> List[tuple]:
        """获取节点的子节点列表"""
        children = []
        
        if isinstance(node, (AddNode, SubtractNode, MultiplyNode)):
            children.append(("left", node.left))
            children.append(("right", node.right))
        elif isinstance(node, DivideNode):
            children.append(("numerator", node.numerator))
            children.append(("denominator", node.denominator))
        elif isinstance(node, PowerNode):
            children.append(("base", node.base))
            children.append(("exponent", node.exponent))
        elif isinstance(node, NegateNode):
            children.append(("operand", node.operand))
        elif isinstance(node, FunctionNode):
            for i, arg in enumerate(node.arguments):
                children.append((f"arg[{i}]", arg))
        elif isinstance(node, GroupNode):
            for i, item in enumerate(node.content):
                children.append((f"[{i}]", item))
        elif isinstance(node, SetNode):
            for i, elem in enumerate(node.elements):
                children.append((f"[{i}]", elem))
        elif isinstance(node, MatrixNode):
            for i, row in enumerate(node.rows):
                children.append((f"row[{i}]", SequenceNode(row)))
        elif isinstance(node, FractionNode):
            children.append(("numerator", node.numerator))
            children.append(("denominator", node.denominator))
        elif isinstance(node, SqrtNode):
            children.append(("radicand", node.radicand))
            if node.degree:
                children.append(("degree", node.degree))
        elif isinstance(node, EquationNode):
            children.append(("left", node.left))
            children.append(("right", node.right))
        elif isinstance(node, CommandNode):
            for i, arg in enumerate(node.args):
                children.append((f"arg[{i}]", arg))
        elif isinstance(node, SequenceNode):
            for i, elem in enumerate(node.elements):
                children.append((f"[{i}]", elem))
        elif isinstance(node, CasesNode):
            for i, (cond, val) in enumerate(node.cases):
                children.append((f"case[{i}].cond", cond))
                children.append((f"case[{i}].val", val))
        elif isinstance(node, LimitNode):
            children.append(("expression", node.expression))
            children.append(("variable", node.variable))
            children.append(("target", node.target))
        elif isinstance(node, SumNode) or isinstance(node, ProductNode):
            children.append(("term", node.term))
            if node.index:
                children.append(("index", node.index))
            if node.lower_limit:
                children.append(("lower", node.lower_limit))
            if node.upper_limit:
                children.append(("upper", node.upper_limit))
        elif isinstance(node, IntegralNode):
            children.append(("integrand", node.integrand))
            if node.variable:
                children.append(("variable", node.variable))
            if node.lower_limit:
                children.append(("lower", node.lower_limit))
            if node.upper_limit:
                children.append(("upper", node.upper_limit))
        elif isinstance(node, DerivativeNode):
            children.append(("numerator", node.numerator))
            children.append(("denominator", node.denominator))
        elif isinstance(node, SubscriptNode):
            children.append(("base", node.base))
            children.append(("subscript", node.subscript))
        elif isinstance(node, SuperscriptNode):
            children.append(("base", node.base))
            children.append(("superscript", node.superscript))
        elif isinstance(node, BracesNode):
            children.append(("content", node.content))
        elif isinstance(node, OperatorNode):
            if node.left:
                children.append(("left", node.left))
            if node.right:
                children.append(("right", node.right))
        
        return children


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def pp_ast(node: ASTNode, show_types: bool = True):
    """打印 AST 的树形表示"""
    printer = ASTPrinter(show_types=show_types)
    print(printer.print(node))


def ast_to_string(node: ASTNode, show_types: bool = True) -> str:
    """将 AST 转换为字符串表示"""
    printer = ASTPrinter(show_types=show_types)
    return printer.print(node)