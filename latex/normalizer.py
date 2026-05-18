"""
LaTeX Normalizer

LaTeX 规范化器 - 将 LaTeX 表达式转换为标准形式。

核心功能：
  1. 统一命令格式
  2. 移除冗余括号
  3. 规范变量命名
  4. 合并同类项
  5. 标准化符号表示

规范化规则：
  - \sin, \cos, \tan 保持不变
  - \frac{a}{b} 标准化为分数形式
  - 下标、上标标准化
  - 括号规范化
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from .ast import AstNode, FunctionNode, OperatorNode, VariableNode, NumberNode, GroupNode, SubscriptNode, SuperscriptNode, LimitNode, FractionNode, AstVisitor


class LatexNormalizer(AstVisitor):
    """
    LaTeX 规范化器
    
    通过访问者模式遍历 AST 并进行规范化。
    """
    
    def __init__(self):
        # 命令别名映射
        self.command_aliases = {
            'sin': 'sin',
            'cos': 'cos',
            'tan': 'tan',
            'cot': 'cot',
            'sec': 'sec',
            'csc': 'csc',
            'arcsin': 'arcsin',
            'arccos': 'arccos',
            'arctan': 'arctan',
            'sinh': 'sinh',
            'cosh': 'cosh',
            'tanh': 'tanh',
            'exp': 'exp',
            'log': 'log',
            'ln': 'ln',
            'lim': 'lim',
            'limsup': 'limsup',
            'liminf': 'liminf',
            'frac': 'frac',
            'dfrac': 'frac',
            'cfrac': 'frac',
            'sqrt': 'sqrt',
            'sum': 'sum',
            'prod': 'prod',
            'int': 'int',
            'text': 'text',
            'to': 'to',
            'infty': 'infty',
            'pi': 'pi',
            'e': 'e',
        }
        
        # 二元运算符标准化
        self.operator_normalization = {
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '=': '=',
            '<': '<',
            '>': '>',
            '\\leq': '<=',
            '\\geq': '>=',
            '\\neq': '!=',
        }
    
    def normalize(self, ast: AstNode) -> AstNode:
        """
        规范化 AST。
        
        Args:
            ast: 原始 AST
        
        Returns:
            AstNode: 规范化后的 AST
        """
        return ast.accept(self)
    
    def visit_function(self, node: FunctionNode) -> AstNode:
        """规范化函数节点"""
        # 标准化函数名
        normalized_name = self.command_aliases.get(node.name, node.name)
        
        # 规范化参数
        normalized_args = [arg.accept(self) for arg in node.arguments]
        
        return FunctionNode(normalized_name, normalized_args)
    
    def visit_operator(self, node: OperatorNode) -> AstNode:
        """规范化运算符节点"""
        # 标准化运算符
        normalized_operator = self.operator_normalization.get(node.operator, node.operator)
        
        # 规范化左右操作数
        normalized_left = node.left.accept(self)
        normalized_right = node.right.accept(self)
        
        return OperatorNode(normalized_operator, normalized_left, normalized_right)
    
    def visit_variable(self, node: VariableNode) -> AstNode:
        """规范化变量节点"""
        # 标准化变量名（小写）
        normalized_name = node.name.lower()
        
        # 规范化下标
        normalized_subscript = None
        if node.subscript:
            normalized_subscript = node.subscript.accept(self)
        
        return VariableNode(normalized_name, normalized_subscript)
    
    def visit_number(self, node: NumberNode) -> AstNode:
        """规范化数字节点"""
        # 标准化符号常量
        normalized_value = self.command_aliases.get(node.value.strip('\\'), node.value)
        if normalized_value != node.value:
            normalized_value = '\\' + normalized_value
        
        return NumberNode(normalized_value, node.is_symbolic)
    
    def visit_group(self, node: GroupNode) -> AstNode:
        """规范化分组节点"""
        normalized_content = node.content.accept(self)
        
        # 移除冗余分组
        if isinstance(normalized_content, (VariableNode, NumberNode)):
            return normalized_content
        
        return GroupNode(normalized_content)
    
    def visit_subscript(self, node: SubscriptNode) -> AstNode:
        """规范化下标节点"""
        normalized_base = node.base.accept(self)
        normalized_subscript = node.subscript.accept(self)
        
        return SubscriptNode(normalized_base, normalized_subscript)
    
    def visit_superscript(self, node: SuperscriptNode) -> AstNode:
        """规范化上标节点"""
        normalized_base = node.base.accept(self)
        normalized_superscript = node.superscript.accept(self)
        
        return SuperscriptNode(normalized_base, normalized_superscript)
    
    def visit_limit(self, node: LimitNode) -> AstNode:
        """规范化极限节点"""
        normalized_variable = VariableNode(node.variable.name.lower())
        normalized_expression = node.expression.accept(self)
        normalized_body = node.body.accept(self)
        
        return LimitNode(normalized_variable, normalized_expression, normalized_body)
    
    def visit_fraction(self, node: FractionNode) -> AstNode:
        """规范化分数节点"""
        normalized_numerator = node.numerator.accept(self)
        normalized_denominator = node.denominator.accept(self)
        
        return FractionNode(normalized_numerator, normalized_denominator)
    
    def visit_default(self, node: AstNode) -> AstNode:
        """默认访问方法"""
        return node


class ExpressionSimplifier(AstVisitor):
    """
    表达式简化器
    
    对数学表达式进行简化处理。
    """
    
    def __init__(self):
        pass
    
    def simplify(self, ast: AstNode) -> AstNode:
        """简化 AST"""
        return ast.accept(self)
    
    def visit_function(self, node: FunctionNode) -> AstNode:
        """简化函数调用"""
        simplified_args = [arg.accept(self) for arg in node.arguments]
        
        # 特殊简化规则
        if node.name == 'sin' and len(simplified_args) == 1:
            return self._simplify_sin(simplified_args[0])
        if node.name == 'cos' and len(simplified_args) == 1:
            return self._simplify_cos(simplified_args[0])
        
        return FunctionNode(node.name, simplified_args)
    
    def visit_operator(self, node: OperatorNode) -> AstNode:
        """简化运算符表达式"""
        simplified_left = node.left.accept(self)
        simplified_right = node.right.accept(self)
        
        # 常量折叠
        if isinstance(simplified_left, NumberNode) and isinstance(simplified_right, NumberNode):
            return self._constant_fold(node.operator, simplified_left, simplified_right)
        
        return OperatorNode(node.operator, simplified_left, simplified_right)
    
    def visit_variable(self, node: VariableNode) -> AstNode:
        """简化变量"""
        simplified_subscript = None
        if node.subscript:
            simplified_subscript = node.subscript.accept(self)
        
        return VariableNode(node.name, simplified_subscript)
    
    def visit_number(self, node: NumberNode) -> AstNode:
        """简化数字"""
        return node
    
    def visit_group(self, node: GroupNode) -> AstNode:
        """简化分组"""
        simplified_content = node.content.accept(self)
        
        # 移除冗余分组
        if isinstance(simplified_content, (VariableNode, NumberNode)):
            return simplified_content
        
        return GroupNode(simplified_content)
    
    def visit_subscript(self, node: SubscriptNode) -> AstNode:
        """简化下标"""
        simplified_base = node.base.accept(self)
        simplified_subscript = node.subscript.accept(self)
        
        return SubscriptNode(simplified_base, simplified_subscript)
    
    def visit_superscript(self, node: SuperscriptNode) -> AstNode:
        """简化上标"""
        simplified_base = node.base.accept(self)
        simplified_superscript = node.superscript.accept(self)
        
        return SuperscriptNode(simplified_base, simplified_superscript)
    
    def visit_limit(self, node: LimitNode) -> AstNode:
        """简化极限"""
        simplified_expression = node.expression.accept(self)
        simplified_body = node.body.accept(self)
        
        return LimitNode(node.variable, simplified_expression, simplified_body)
    
    def visit_fraction(self, node: FractionNode) -> AstNode:
        """简化分数"""
        simplified_numerator = node.numerator.accept(self)
        simplified_denominator = node.denominator.accept(self)
        
        return FractionNode(simplified_numerator, simplified_denominator)
    
    def visit_default(self, node: AstNode) -> AstNode:
        """默认处理"""
        return node
    
    def _simplify_sin(self, arg: AstNode) -> AstNode:
        """简化 sin 函数"""
        # sin(0) = 0
        if isinstance(arg, NumberNode) and arg.value == '0':
            return NumberNode('0')
        return FunctionNode('sin', [arg])
    
    def _simplify_cos(self, arg: AstNode) -> AstNode:
        """简化 cos 函数"""
        # cos(0) = 1
        if isinstance(arg, NumberNode) and arg.value == '0':
            return NumberNode('1')
        # cos(π) = -1
        if isinstance(arg, NumberNode) and arg.value == r'\pi':
            return NumberNode('-1')
        return FunctionNode('cos', [arg])
    
    def _constant_fold(self, operator: str, left: NumberNode, right: NumberNode) -> AstNode:
        """常量折叠"""
        try:
            left_val = self._parse_number(left)
            right_val = self._parse_number(right)
            
            if operator == '+':
                result = left_val + right_val
            elif operator == '-':
                result = left_val - right_val
            elif operator == '*':
                result = left_val * right_val
            elif operator == '/':
                if right_val == 0:
                    return NumberNode(r'\infty', is_symbolic=True)
                result = left_val / right_val
            else:
                return OperatorNode(operator, left, right)
            
            return NumberNode(str(result))
        
        except (ValueError, TypeError):
            return OperatorNode(operator, left, right)
    
    def _parse_number(self, node: NumberNode) -> float:
        """解析数字节点为浮点数"""
        if node.value == r'\pi':
            return 3.1415926535
        if node.value == r'\infty':
            return float('inf')
        if node.value == r'-1':
            return -1.0
        return float(node.value)


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def normalize_latex(text: str) -> AstNode:
    """便捷函数：规范化 LaTeX"""
    from .tokenizer import tokenize_latex
    from .ast import LatexParser
    
    tokens = tokenize_latex(text)
    parser = LatexParser()
    ast = parser.parse(tokens)
    
    normalizer = LatexNormalizer()
    return normalizer.normalize(ast)


def simplify_latex(text: str) -> AstNode:
    """便捷函数：简化 LaTeX"""
    ast = normalize_latex(text)
    simplifier = ExpressionSimplifier()
    return simplifier.simplify(ast)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        r"\sin(x_n)",
        r"\cos(\sin x)",
        r"\frac{1}{2} + \frac{1}{3}",
        r"\lim_{n \to \infty} x_n",
    ]
    
    for latex in test_cases:
        print(f"=== Input: {latex} ===")
        try:
            normalized = normalize_latex(latex)
            print(f"Normalized: {normalized}")
            
            simplified = simplify_latex(latex)
            print(f"Simplified: {simplified}")
        except Exception as e:
            print(f"Error: {e}")
        print()
