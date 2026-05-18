"""
LaTeX AST

将 Token 序列转换为抽象语法树（AST）。

核心功能：
  1. 构建数学表达式的层次结构
  2. 表示函数调用、运算符、变量、数字等
  3. 支持后续的语义分析和规范化

AST 节点类型：
  - FunctionNode: 函数调用（如 sin(x), cos(x)）
  - OperatorNode: 运算符（如 +, -, *, /）
  - VariableNode: 变量（如 x, x_n）
  - NumberNode: 数字（如 1, 2.5, \pi）
  - GroupNode: 分组表达式
  - SubscriptNode: 下标表达式
  - SuperscriptNode: 上标表达式
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, Optional, Union
from .tokenizer import Token, TokenType, CommandToken, VariableToken, NumberToken, GroupToken, SymbolToken, SuperscriptToken, SubscriptToken


class NodeType(Enum):
    """AST 节点类型枚举"""
    FUNCTION = auto()      # 函数调用
    OPERATOR = auto()      # 运算符
    VARIABLE = auto()      # 变量
    NUMBER = auto()        # 数字
    GROUP = auto()         # 分组
    SUBSCRIPT = auto()     # 下标
    SUPERSCRIPT = auto()   # 上标
    LIMIT = auto()         # 极限
    FRACTION = auto()      # 分数
    SUM = auto()           # 求和
    PRODUCT = auto()       # 乘积
    INTEGRAL = auto()      # 积分
    SQRT = auto()          # 根号


@dataclass
class AstNode:
    """AST 节点基类"""
    type: NodeType
    
    def accept(self, visitor: AstVisitor) -> Any:
        """访问者模式"""
        method_name = f'visit_{self.type.name.lower()}'
        method = getattr(visitor, method_name, visitor.visit_default)
        return method(self)
    
    def to_dict(self) -> dict:
        """转换为字典表示"""
        return {'type': self.type.name}
    
    def __repr__(self) -> str:
        return f'<{self.type.name}>'


@dataclass
class FunctionNode(AstNode):
    """函数调用节点"""
    name: str
    arguments: List[AstNode]
    
    def __init__(self, name: str, arguments: List[AstNode]):
        super().__init__(NodeType.FUNCTION)
        self.name = name
        self.arguments = arguments
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'name': self.name,
            'arguments': [arg.to_dict() for arg in self.arguments],
        }
    
    def __repr__(self) -> str:
        args = ', '.join(repr(arg) for arg in self.arguments)
        return f'<Function: {self.name}({args})>'


@dataclass
class OperatorNode(AstNode):
    """运算符节点"""
    operator: str
    left: AstNode
    right: AstNode
    
    def __init__(self, operator: str, left: AstNode, right: AstNode):
        super().__init__(NodeType.OPERATOR)
        self.operator = operator
        self.left = left
        self.right = right
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'operator': self.operator,
            'left': self.left.to_dict(),
            'right': self.right.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Operator: {self.left} {self.operator} {self.right}>'


@dataclass
class VariableNode(AstNode):
    """变量节点"""
    name: str
    subscript: Optional[AstNode] = None
    
    def __init__(self, name: str, subscript: Optional[AstNode] = None):
        super().__init__(NodeType.VARIABLE)
        self.name = name
        self.subscript = subscript
    
    @property
    def full_name(self) -> str:
        """完整变量名"""
        if self.subscript:
            return f'{self.name}_{self.subscript}'
        return self.name
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'name': self.name,
            'subscript': self.subscript.to_dict() if self.subscript else None,
        }
    
    def __repr__(self) -> str:
        if self.subscript:
            return f'<Variable: {self.name}_{self.subscript}>'
        return f'<Variable: {self.name}>'


@dataclass
class NumberNode(AstNode):
    """数字节点"""
    value: str
    is_symbolic: bool = False
    
    def __init__(self, value: str, is_symbolic: bool = False):
        super().__init__(NodeType.NUMBER)
        self.value = value
        self.is_symbolic = is_symbolic
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'value': self.value,
            'is_symbolic': self.is_symbolic,
        }
    
    def __repr__(self) -> str:
        return f'<Number: {self.value}>'


@dataclass
class GroupNode(AstNode):
    """分组节点"""
    content: AstNode
    
    def __init__(self, content: AstNode):
        super().__init__(NodeType.GROUP)
        self.content = content
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'content': self.content.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Group: ({self.content})>'


@dataclass
class SubscriptNode(AstNode):
    """下标节点"""
    base: AstNode
    subscript: AstNode
    
    def __init__(self, base: AstNode, subscript: AstNode):
        super().__init__(NodeType.SUBSCRIPT)
        self.base = base
        self.subscript = subscript
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'base': self.base.to_dict(),
            'subscript': self.subscript.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Subscript: {self.base}_{self.subscript}>'


@dataclass
class SuperscriptNode(AstNode):
    """上标节点"""
    base: AstNode
    superscript: AstNode
    
    def __init__(self, base: AstNode, superscript: AstNode):
        super().__init__(NodeType.SUPERSCRIPT)
        self.base = base
        self.superscript = superscript
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'base': self.base.to_dict(),
            'superscript': self.superscript.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Superscript: {self.base}^{self.superscript}>'


@dataclass
class LimitNode(AstNode):
    """极限节点"""
    variable: VariableNode
    expression: AstNode
    body: AstNode
    
    def __init__(self, variable: VariableNode, expression: AstNode, body: AstNode):
        super().__init__(NodeType.LIMIT)
        self.variable = variable
        self.expression = expression
        self.body = body
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'variable': self.variable.to_dict(),
            'expression': self.expression.to_dict(),
            'body': self.body.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Limit: lim_{self.variable}->{self.expression} {self.body}>'


@dataclass
class FractionNode(AstNode):
    """分数节点"""
    numerator: AstNode
    denominator: AstNode
    
    def __init__(self, numerator: AstNode, denominator: AstNode):
        super().__init__(NodeType.FRACTION)
        self.numerator = numerator
        self.denominator = denominator
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'numerator': self.numerator.to_dict(),
            'denominator': self.denominator.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f'<Fraction: {self.numerator}/{self.denominator}>'


class AstVisitor:
    """AST 访问者基类"""
    def visit_function(self, node: FunctionNode) -> Any:
        return self.visit_default(node)
    
    def visit_operator(self, node: OperatorNode) -> Any:
        return self.visit_default(node)
    
    def visit_variable(self, node: VariableNode) -> Any:
        return self.visit_default(node)
    
    def visit_number(self, node: NumberNode) -> Any:
        return self.visit_default(node)
    
    def visit_group(self, node: GroupNode) -> Any:
        return self.visit_default(node)
    
    def visit_subscript(self, node: SubscriptNode) -> Any:
        return self.visit_default(node)
    
    def visit_superscript(self, node: SuperscriptNode) -> Any:
        return self.visit_default(node)
    
    def visit_limit(self, node: LimitNode) -> Any:
        return self.visit_default(node)
    
    def visit_fraction(self, node: FractionNode) -> Any:
        return self.visit_default(node)
    
    def visit_default(self, node: AstNode) -> Any:
        return None


class LatexParser:
    """
    LaTeX 语法分析器
    
    将 Token 序列转换为 AST。
    """
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.pos: int = 0
    
    def parse(self, tokens: List[Token]) -> AstNode:
        """
        解析 Token 序列为 AST。
        
        Args:
            tokens: Token 序列
        
        Returns:
            AstNode: AST 根节点
        """
        self.tokens = tokens
        self.pos = 0
        
        if not tokens:
            raise ValueError("空 Token 序列")
        
        return self._parse_expression()
    
    def _parse_expression(self) -> AstNode:
        """解析表达式"""
        return self._parse_binary_expression(0)
    
    def _parse_binary_expression(self, precedence: int) -> AstNode:
        """解析二元表达式（带优先级）"""
        left = self._parse_primary()
        
        while self._has_next():
            token = self._peek()
            
            # 检查是否为二元运算符
            if token.type == TokenType.SYMBOL and token.value in '+-*/=<>':
                op_precedence = self._get_precedence(token.value)
                if op_precedence > precedence:
                    self._consume()
                    right = self._parse_binary_expression(op_precedence)
                    left = OperatorNode(token.value, left, right)
                else:
                    break
            elif token.type == TokenType.COMMAND and token.value in {'frac', 'dfrac', 'cfrac'}:
                # 分数作为二元运算符处理
                self._consume()
                numerator = self._parse_primary()
                denominator = self._parse_primary()
                left = FractionNode(numerator, denominator)
            else:
                break
        
        return left
    
    def _parse_primary(self) -> AstNode:
        """解析基本表达式"""
        if not self._has_next():
            raise ValueError("意外的表达式结束")
        
        token = self._peek()
        
        # 处理函数调用
        if token.type == TokenType.COMMAND:
            return self._parse_function()
        
        # 处理变量
        if token.type == TokenType.VARIABLE:
            return self._parse_variable()
        
        # 处理数字
        if token.type == TokenType.NUMBER:
            return self._parse_number()
        
        # 处理分组
        if token.type == TokenType.GROUP:
            return self._parse_group()
        
        # 处理符号
        if token.type == TokenType.SYMBOL:
            if token.value == '(':
                return self._parse_parenthesized()
            if token.value == '[':
                return self._parse_bracketed()
        
        raise ValueError(f"无法解析 Token: {token}")
    
    def _parse_function(self) -> AstNode:
        """解析函数调用"""
        token = self._consume()
        
        if token.type != TokenType.COMMAND:
            raise ValueError(f"预期命令 Token，得到 {token}")
        
        func_name = token.value
        
        # 特殊处理极限
        if func_name in {'lim', 'limsup', 'liminf'}:
            return self._parse_limit(func_name)
        
        # 特殊处理求和、乘积、积分
        if func_name == 'sum':
            return self._parse_sum()
        if func_name == 'prod':
            return self._parse_product()
        if func_name in {'int', 'oint'}:
            return self._parse_integral()
        
        # 特殊处理根号
        if func_name == 'sqrt':
            return self._parse_sqrt()
        
        # 普通函数：读取参数
        args = []
        
        # 检查是否有分组参数
        if self._has_next() and self._peek().type == TokenType.GROUP:
            while self._has_next() and self._peek().type == TokenType.GROUP:
                group_token = self._consume()
                group_content = self.parse(group_token.content)
                args.append(group_content)
        
        return FunctionNode(func_name, args)
    
    def _parse_limit(self, func_name: str) -> LimitNode:
        """解析极限表达式"""
        # 跳过命令
        self._consume()
        
        # 解析下标（变量和趋向值）
        subscript_token = None
        if self._has_next() and self._peek().type == TokenType.SUBSCRIPT:
            self._consume()  # 跳过 '_'
            subscript_token = self._consume()
        
        # 解析下标内容
        variable_name = 'n'
        expression = None
        
        if subscript_token and subscript_token.type == TokenType.GROUP:
            # 解析分组内容
            group_tokens = subscript_token.content
            if group_tokens:
                # 期望格式: n\to\infty
                i = 0
                if i < len(group_tokens) and group_tokens[i].type == TokenType.VARIABLE:
                    variable_name = group_tokens[i].value
                    i += 1
                if i + 2 < len(group_tokens):
                    if group_tokens[i].type == TokenType.COMMAND and group_tokens[i].value == 'to':
                        i += 1
                        # 解析趋向表达式
                        expression = self.parse(group_tokens[i:])
        
        # 如果没有解析到趋向表达式，默认是无穷
        if expression is None:
            expression = NumberNode(r'\infty', is_symbolic=True)
        
        # 创建变量节点
        variable = VariableNode(variable_name)
        
        # 解析极限主体
        body = self._parse_expression()
        
        return LimitNode(variable, expression, body)
    
    def _parse_sum(self) -> AstNode:
        """解析求和表达式"""
        # 跳过命令
        self._consume()
        
        # 解析下标和上标（可选）
        subscript = None
        superscript = None
        
        if self._has_next() and self._peek().type == TokenType.SUBSCRIPT:
            self._consume()
            if self._has_next() and self._peek().type == TokenType.GROUP:
                subscript_token = self._consume()
                subscript = self.parse(subscript_token.content)
        
        if self._has_next() and self._peek().type == TokenType.SUPERSCRIPT:
            self._consume()
            if self._has_next() and self._peek().type == TokenType.GROUP:
                superscript_token = self._consume()
                superscript = self.parse(superscript_token.content)
        
        # 解析求和主体
        body = self._parse_expression()
        
        # 使用函数节点表示求和
        args = []
        if subscript:
            args.append(subscript)
        if superscript:
            args.append(superscript)
        args.append(body)
        
        return FunctionNode('sum', args)
    
    def _parse_product(self) -> AstNode:
        """解析乘积表达式"""
        self._consume()
        body = self._parse_expression()
        return FunctionNode('prod', [body])
    
    def _parse_integral(self) -> AstNode:
        """解析积分表达式"""
        func_name = self._consume().value
        body = self._parse_expression()
        return FunctionNode(func_name, [body])
    
    def _parse_sqrt(self) -> AstNode:
        """解析根号表达式"""
        self._consume()
        
        # 检查是否有根指数
        root_index = None
        if self._has_next() and self._peek().type == TokenType.SYMBOL and self._peek().value == '[':
            self._consume()  # 跳过 '['
            if self._has_next() and self._peek().type == TokenType.GROUP:
                root_token = self._consume()
                root_index = self.parse(root_token.content)
            if self._has_next() and self._peek().type == TokenType.SYMBOL and self._peek().value == ']':
                self._consume()  # 跳过 ']'
        
        # 解析被开方数
        radicand = None
        if self._has_next() and self._peek().type == TokenType.GROUP:
            radicand_token = self._consume()
            radicand = self.parse(radicand_token.content)
        
        args = []
        if root_index:
            args.append(root_index)
        if radicand:
            args.append(radicand)
        
        return FunctionNode('sqrt', args)
    
    def _parse_variable(self) -> AstNode:
        """解析变量"""
        token = self._consume()
        
        if token.type != TokenType.VARIABLE:
            raise ValueError(f"预期变量 Token，得到 {token}")
        
        # 检查是否有下标
        subscript = None
        if self._has_next() and self._peek().type == TokenType.SUBSCRIPT:
            self._consume()  # 跳过 '_'
            if self._has_next():
                subscript_token = self._consume()
                if subscript_token.type == TokenType.GROUP:
                    subscript = self.parse(subscript_token.content)
                else:
                    subscript = VariableNode(subscript_token.value)
        
        return VariableNode(token.value, subscript)
    
    def _parse_number(self) -> AstNode:
        """解析数字"""
        token = self._consume()
        
        if token.type != TokenType.NUMBER:
            raise ValueError(f"预期数字 Token，得到 {token}")
        
        return NumberNode(token.value, token.is_symbolic)
    
    def _parse_group(self) -> AstNode:
        """解析分组"""
        token = self._consume()
        
        if token.type != TokenType.GROUP:
            raise ValueError(f"预期分组 Token，得到 {token}")
        
        content = self.parse(token.content)
        return GroupNode(content)
    
    def _parse_parenthesized(self) -> AstNode:
        """解析圆括号表达式"""
        self._consume()  # 跳过 '('
        content = self._parse_expression()
        
        if self._has_next() and self._peek().type == TokenType.SYMBOL and self._peek().value == ')':
            self._consume()
        
        return GroupNode(content)
    
    def _parse_bracketed(self) -> AstNode:
        """解析方括号表达式"""
        self._consume()  # 跳过 '['
        
        # 检查是否为区间
        content_tokens = []
        while self._has_next() and not (self._peek().type == TokenType.SYMBOL and self._peek().value == ']'):
            content_tokens.append(self._consume())
        
        if self._has_next() and self._peek().type == TokenType.SYMBOL and self._peek().value == ']':
            self._consume()
        
        # 解析区间内容
        if content_tokens:
            content = self.parse(content_tokens)
            return FunctionNode('interval', [content])
        
        return GroupNode(NumberNode('0'))
    
    def _has_next(self) -> bool:
        """检查是否有下一个 Token"""
        return self.pos < len(self.tokens)
    
    def _peek(self) -> Token:
        """查看下一个 Token（不消费）"""
        if not self._has_next():
            raise ValueError("没有更多 Token")
        return self.tokens[self.pos]
    
    def _consume(self) -> Token:
        """消费并返回当前 Token"""
        token = self._peek()
        self.pos += 1
        return token
    
    def _get_precedence(self, operator: str) -> int:
        """获取运算符优先级"""
        precedence = {
            '+': 1,
            '-': 1,
            '*': 2,
            '/': 2,
            '=': 0,
            '<': 0,
            '>': 0,
        }
        return precedence.get(operator, 0)


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def parse_latex(text: str) -> AstNode:
    """便捷函数：解析 LaTeX 为 AST"""
    from .tokenizer import tokenize_latex
    tokens = tokenize_latex(text)
    parser = LatexParser()
    return parser.parse(tokens)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        r"\sin(x_n)",
        r"\cos(\sin x)",
        r"\lim_{n\to\infty} x_n",
        r"\frac{1}{2}",
        r"x + y",
    ]
    
    for latex in test_cases:
        print(f"=== Input: {latex} ===")
        try:
            ast = parse_latex(latex)
            print(f"AST: {ast}")
            print(f"Dict: {ast.to_dict()}")
        except Exception as e:
            print(f"Error: {e}")
        print()
