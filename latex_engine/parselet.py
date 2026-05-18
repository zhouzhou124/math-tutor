"""Parselet-based Pratt Parser Architecture

This implements a true Pratt parser with separate parselets for:
- Prefix operations (unary operators, identifiers, numbers)
- Infix operations (binary operators)
- Postfix operations (postfix operators)
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any

from .lexer import Token, TokenType
from .ast import *


# ═══════════════════════════════════════════════
# Parselet Base Classes
# ═══════════════════════════════════════════════

class Parselet(ABC):
    """Parselet 基类"""
    
    @abstractmethod
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        """解析并返回 AST 节点"""
        pass


class PrefixParselet(Parselet):
    """前缀解析器 - 处理一元操作和原子表达式"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        """解析前缀表达式"""
        pass


class InfixParselet(Parselet):
    """中缀解析器 - 处理二元操作"""
    
    def __init__(self, precedence: int, right_associative: bool = False):
        self.precedence = precedence
        self.right_associative = right_associative
    
    @abstractmethod
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        """解析中缀表达式"""
        pass


class PostfixParselet(Parselet):
    """后缀解析器 - 处理后缀操作"""
    
    def __init__(self, precedence: int):
        self.precedence = precedence
    
    @abstractmethod
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        """解析后缀表达式"""
        pass


# ═══════════════════════════════════════════════
# Prefix Parselets
# ═══════════════════════════════════════════════

class NumberParselet(PrefixParselet):
    """数字解析器"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        value = token.value
        parser.advance()  # 推进 token
        # 尝试解析为整数或浮点数
        if isinstance(value, (int, float)):
            return NumberNode(value)
        # 字符串形式的数字
        if isinstance(value, str):
            if '.' in value:
                try:
                    return NumberNode(float(value))
                except ValueError:
                    pass
            else:
                try:
                    return NumberNode(int(value))
                except ValueError:
                    pass
        return NumberNode(value, math_type=MathType.REAL)


class SymbolParselet(PrefixParselet):
    """符号解析器"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        name = token.value
        parser.advance()  # 推进 token
        
        # 检查是否为保留函数名
        if name.lower() in parser.RESERVED_FUNCTIONS:
            return SymbolNode(name)
        
        # 如果是多字母标识符，拆分成单个字母的隐式乘法
        if len(name) > 1:
            # 拆分成单个字母
            nodes = [SymbolNode(c) for c in name]
            
            # 创建隐式乘法链: a * b * c
            result = nodes[0]
            for node in nodes[1:]:
                result = MultiplyNode(result, node)
            
            return result
        
        return SymbolNode(name)


class GroupParselet(PrefixParselet):
    """分组解析器 - 处理括号"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        parser.advance()  # 消费 PAREN_OPEN
        expr = parser.parse_expression()
        parser.consume(TokenType.PAREN_CLOSE)
        return GroupNode([expr])


class UnaryOperatorParselet(PrefixParselet):
    """一元操作符解析器"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        operand = parser.parse_expression(50)  # 高优先级
        if token.value == '-':
            return NegateNode(operand)
        elif token.value == '+':
            return operand  # 正号不改变表达式
        return operand


class CommandParselet(PrefixParselet):
    """LaTeX 命令解析器"""
    
    def parse(self, parser: 'PrattParser', token: Token) -> ASTNode:
        cmd_name = token.value[1:]  # 去掉反斜杠
        parser.advance()  # 推进 token
        args = []
        
        # 检查是否有参数（命令后跟 {...} 或 (...)）
        if parser.match(TokenType.BRACE_OPEN):
            arg = parser.parse_expression()
            parser.consume(TokenType.BRACE_CLOSE)
            args.append(arg)
            
            # 可能有多个参数
            while parser.match(TokenType.BRACE_OPEN):
                arg = parser.parse_expression()
                parser.consume(TokenType.BRACE_CLOSE)
                args.append(arg)
        
        return CommandNode(cmd_name, args)


# ═══════════════════════════════════════════════
# Infix Parselets
# ═══════════════════════════════════════════════

class BinaryOperatorParselet(InfixParselet):
    """二元操作符解析器"""
    
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        op = token.value
        
        # 确定右操作数的优先级
        if self.right_associative:
            right = parser.parse_expression(self.precedence - 1)
        else:
            right = parser.parse_expression(self.precedence)
        
        # 根据操作符类型创建相应节点
        if op == '+':
            return AddNode(left, right)
        elif op == '-':
            return SubtractNode(left, right)
        elif op == '*' or op == '\cdot':
            return MultiplyNode(left, right)
        elif op == '/':
            return DivideNode(left, right)
        elif op == '^':
            return PowerNode(left, right)
        elif op == '=':
            return EquationNode(left, right, '=')
        elif op == '<':
            return EquationNode(left, right, '<')
        elif op == '>':
            return EquationNode(left, right, '>')
        elif op == '<=':
            return EquationNode(left, right, '<=')
        elif op == '>=':
            return EquationNode(left, right, '>=')
        elif op == '!=':
            return EquationNode(left, right, '!=')
        
        return OperatorNode(op, left, right)


class FunctionCallParselet(InfixParselet):
    """函数调用解析器"""
    
    def __init__(self):
        super().__init__(precedence=40)
    
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        # left 是函数名（SymbolNode）
        args = []
        
        if not parser.match(TokenType.PAREN_CLOSE):
            args.append(parser.parse_expression())
            while parser.match(TokenType.COMMA):
                args.append(parser.parse_expression())
            parser.consume(TokenType.PAREN_CLOSE)
        
        func_name = left.name if isinstance(left, SymbolNode) else str(left)
        return FunctionNode(func_name, args)


class ImplicitMultiplyParselet(InfixParselet):
    """隐式乘法解析器"""
    
    def __init__(self):
        super().__init__(precedence=30)
    
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        # token 是右操作数的开始
        # 需要重新解析右操作数
        right = parser.parse_expression(self.precedence)
        return MultiplyNode(left, right)


# ═══════════════════════════════════════════════
# Postfix Parselets
# ═══════════════════════════════════════════════

class SubscriptParselet(PostfixParselet):
    """下标解析器"""
    
    def __init__(self):
        super().__init__(precedence=60)
    
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        subscript = parser.parse_expression(0)
        return SubscriptNode(left, subscript)


class SuperscriptParselet(PostfixParselet):
    """上标解析器"""
    
    def __init__(self):
        super().__init__(precedence=60)
    
    def parse(self, parser: 'PrattParser', left: ASTNode, token: Token) -> ASTNode:
        superscript = parser.parse_expression(0)
        return SuperscriptNode(left, superscript)


# ═══════════════════════════════════════════════
# Pratt Parser
# ═══════════════════════════════════════════════

class PrattParser:
    """基于 Parselet 的 Pratt 解析器"""
    
    # 运算符优先级（数字越大优先级越高）
    PRECEDENCE = {
        '=': 10,
        '<': 10, '>': 10, '<=': 10, '>=': 10, '!=': 10,
        '+': 20, '-': 20,
        '*': 30, '/': 30, '\cdot': 30,
        '^': 40,
        'unary': 50,
        'postfix': 60,
    }
    
    # 保留函数名列表
    RESERVED_FUNCTIONS = {
        'sin', 'cos', 'tan', 'sinh', 'cosh', 'tanh',
        'asin', 'acos', 'atan',
        'exp', 'log', 'ln', 'sqrt', 'abs',
        'lim', 'sum', 'prod', 'int', 'sum_{', 'prod_{',
        'det', 'trace', 'rank',
        'min', 'max', 'floor', 'ceil',
        'gcd', 'lcm',
    }
    
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = None
        
        # Parselet 注册表
        self.prefix_parselets: Dict[TokenType, PrefixParselet] = {}
        self.infix_parselets: Dict[TokenType, InfixParselet] = {}
        self.postfix_parselets: Dict[TokenType, PostfixParselet] = {}
        
        # 操作符到解析器的映射（用于 TokenType.OPERATOR）
        self.operator_infix_parselets: Dict[str, InfixParselet] = {}
        
        self._register_default_parselets()
        
        # 提前读取第一个 token
        self.advance()
    
    def _register_default_parselets(self):
        """注册默认的 parselet"""
        
        # 前缀解析器
        self.register_prefix(TokenType.NUMBER, NumberParselet())
        self.register_prefix(TokenType.IDENTIFIER, SymbolParselet())
        self.register_prefix(TokenType.PAREN_OPEN, GroupParselet())
        self.register_prefix(TokenType.BRACE_OPEN, GroupParselet())
        self.register_prefix(TokenType.BRACKET_OPEN, GroupParselet())
        self.register_prefix(TokenType.COMMAND, CommandParselet())
        
        # 一元操作符（通过操作符映射处理）
        self.operator_infix_parselets['-'] = BinaryOperatorParselet(self.PRECEDENCE['unary'], right_associative=True)
        self.operator_infix_parselets['+'] = BinaryOperatorParselet(self.PRECEDENCE['unary'], right_associative=True)
        
        # 二元操作符
        self.operator_infix_parselets['+'] = BinaryOperatorParselet(self.PRECEDENCE['+'])
        self.operator_infix_parselets['-'] = BinaryOperatorParselet(self.PRECEDENCE['-'])
        self.operator_infix_parselets['*'] = BinaryOperatorParselet(self.PRECEDENCE['*'])
        self.operator_infix_parselets['/'] = BinaryOperatorParselet(self.PRECEDENCE['/'])
        self.operator_infix_parselets['\\cdot'] = BinaryOperatorParselet(self.PRECEDENCE['\\cdot'])
        self.operator_infix_parselets['^'] = BinaryOperatorParselet(self.PRECEDENCE['^'], right_associative=True)
        self.operator_infix_parselets['='] = BinaryOperatorParselet(self.PRECEDENCE['='])
        self.operator_infix_parselets['<'] = BinaryOperatorParselet(self.PRECEDENCE['<'])
        self.operator_infix_parselets['>'] = BinaryOperatorParselet(self.PRECEDENCE['>'])
        self.operator_infix_parselets['<='] = BinaryOperatorParselet(self.PRECEDENCE['<='])
        self.operator_infix_parselets['>='] = BinaryOperatorParselet(self.PRECEDENCE['>='])
        self.operator_infix_parselets['!='] = BinaryOperatorParselet(self.PRECEDENCE['!='])
    
    def register_prefix(self, token_type: TokenType, parselet: PrefixParselet):
        """注册前缀解析器"""
        self.prefix_parselets[token_type] = parselet
    
    def register_infix(self, token_type: TokenType, parselet: InfixParselet):
        """注册中缀解析器"""
        self.infix_parselets[token_type] = parselet
    
    def register_postfix(self, token_type: TokenType, parselet: PostfixParselet):
        """注册后缀解析器"""
        self.postfix_parselets[token_type] = parselet
    
    def advance(self):
        """推进到下一个 token"""
        self.current_token = self.lexer.next_token()
    
    def consume(self, token_type: TokenType) -> Token:
        """消费指定类型的 token"""
        if self.current_token and self.current_token.type == token_type:
            token = self.current_token
            self.advance()
            return token
        raise SyntaxError(f"Expected {token_type}, got {self.current_token}")
    
    def match(self, token_type: TokenType) -> bool:
        """检查当前 token 是否匹配指定类型"""
        if self.current_token and self.current_token.type == token_type:
            self.advance()
            return True
        return False
    
    def parse(self) -> ASTNode:
        """解析整个表达式"""
        expr = self.parse_expression()
        
        # 检查是否还有剩余 token
        if self.current_token and self.current_token.type != TokenType.EOF:
            raise SyntaxError(f"Unexpected token: {self.current_token}")
        
        return expr
    
    def parse_expression(self, precedence: int = 0) -> ASTNode:
        """解析表达式，支持指定优先级"""
        token = self.current_token
        
        # 获取前缀解析器
        if token.type in self.prefix_parselets:
            left = self.prefix_parselets[token.type].parse(self, token)
        elif token.type == TokenType.OPERATOR and token.value in ['-', '+']:
            # 一元操作符
            self.advance()
            operand = self.parse_expression(self.PRECEDENCE['unary'])
            if token.value == '-':
                left = NegateNode(operand)
            else:
                left = operand  # 正号不改变表达式
        else:
            raise SyntaxError(f"Unexpected token: {token}")
        
        # 处理中缀和后缀操作
        while self.current_token:
            current = self.current_token
            
            # 检查是否为函数调用（标识符后跟 '('）
            if current.type == TokenType.PAREN_OPEN:
                # 判断前面是否为函数名
                if isinstance(left, SymbolNode):
                    func_name = left.name.lower()
                    if func_name in self.RESERVED_FUNCTIONS:
                        self.advance()
                        args = []
                        if not self.match(TokenType.PAREN_CLOSE):
                            args.append(self.parse_expression())
                            while self.match(TokenType.COMMA):
                                args.append(self.parse_expression())
                            self.consume(TokenType.PAREN_CLOSE)
                        left = FunctionNode(func_name, args)
                        continue
                
                # 否则是隐式乘法或分组
                self.advance()
                inner = self.parse_expression()
                self.consume(TokenType.PAREN_CLOSE)
                # 检查是否为隐式乘法
                if isinstance(left, (SymbolNode, NumberNode)):
                    left = MultiplyNode(left, GroupNode([inner]))
                else:
                    left = GroupNode([inner])
                continue
            
            # 检查后缀操作符
            if current.type in self.postfix_parselets:
                postfix = self.postfix_parselets[current.type]
                if postfix.precedence > precedence:
                    self.advance()
                    left = postfix.parse(self, left, current)
                    continue
                else:
                    break
            
            # 检查中缀操作符
            if current.type == TokenType.OPERATOR:
                if current.value in self.operator_infix_parselets:
                    infix = self.operator_infix_parselets[current.value]
                    if infix.precedence > precedence:
                        self.advance()
                        left = infix.parse(self, left, current)
                        continue
                    else:
                        break
            
            # 检查隐式乘法情况
            # IDENTIFIER 或 NUMBER 后跟 IDENTIFIER 或 PAREN_OPEN
            if (current.type == TokenType.IDENTIFIER or 
                current.type == TokenType.NUMBER or
                current.type == TokenType.PAREN_OPEN):
                
                # 只有当前面是数字或标识符时才触发隐式乘法
                if isinstance(left, (SymbolNode, NumberNode, GroupNode)):
                    # 创建隐式乘法 - 只解析下一个 primary
                    self.advance()
                    right_token = self.current_token
                    
                    # 解析右操作数
                    if right_token.type in self.prefix_parselets:
                        right = self.prefix_parselets[right_token.type].parse(self, right_token)
                    else:
                        right = SymbolNode(right_token.value) if right_token.type == TokenType.IDENTIFIER else NumberNode(right_token.value)
                    
                    left = MultiplyNode(left, right)
                    continue
            
            break
        
        return left


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def parse_with_pratt(latex: str) -> ASTNode:
    """使用 Pratt 解析器解析 LaTeX"""
    from .lexer import LaTeXLexer
    lexer = LaTeXLexer(latex)
    parser = PrattParser(lexer)
    return parser.parse()