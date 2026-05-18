"""Math Parser v2 - Pratt Parser with Operator Precedence

实现真正的语义表达式树，支持运算符优先级：
- ^ (幂运算)        优先级 5（右结合）
- unary - (负号)    优先级 4
- *, /, \cdot       优先级 3
- +, -              优先级 2
- =, ==, <=, >=, <, > 优先级 1
"""

from typing import List, Optional, Callable, Dict
from .lexer import Token, TokenType, LaTeXLexer
from .ast import *


class PrattParser:
    """Pratt Parser - 支持运算符优先级的递归下降解析器"""
    
    # 运算符优先级（数字越大优先级越高）
    PRECEDENCE = {
        '=': 1,
        '<': 1, '>': 1, '<=': 1, '>=': 1, '!=': 1, '==': 1,
        '+': 2, '-': 2,
        '*': 3, '/': 3, '\\cdot': 3,
        '^': 5,  # 右结合
    }
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else None
        
        # 注册前缀和中缀解析函数
        self.prefix_parselets: Dict[str, Callable[[], ASTNode]] = {
            TokenType.NUMBER: self._parse_number,
            TokenType.IDENTIFIER: self._parse_symbol,
            TokenType.UNICODE_MATH: self._parse_unicode_math,
            TokenType.COMMAND: self._parse_command,
            TokenType.PAREN_OPEN: self._parse_group,
            TokenType.BRACE_OPEN: self._parse_brace_group,
            TokenType.BRACKET_OPEN: self._parse_bracket_group,
        }
        
        # 运算符解析
        self.infix_parselets: Dict[str, Callable[[ASTNode], ASTNode]] = {}
    
    def parse(self) -> ASTNode:
        """解析入口"""
        if not self.tokens:
            return SequenceNode([])
        
        result = self._parse_expression(0)
        
        # 检查是否还有未解析的token
        if self.current_token:
            # 尝试继续解析
            while self.current_token:
                result = SequenceNode([result, self._parse_expression(0)])
        
        return result
    
    def advance(self):
        """前进到下一个token"""
        self.pos += 1
        self.current_token = self.tokens[self.pos] if self.pos < len(self.tokens) else None
        # 跳过空白字符
        while self.current_token and self.current_token.type in (TokenType.WHITESPACE, TokenType.NEWLINE):
            self.pos += 1
            self.current_token = self.tokens[self.pos] if self.pos < len(self.tokens) else None
    
    def peek(self) -> Optional[Token]:
        """查看下一个token"""
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None
    
    def _parse_expression(self, min_precedence: int = 0) -> ASTNode:
        """解析表达式，处理运算符优先级"""
        # 获取前缀解析
        if not self.current_token:
            raise SyntaxError("Unexpected end of input")
        
        token = self.current_token
        
        # 处理前缀运算符（如负号）
        if token.type == TokenType.OPERATOR and token.value == '-':
            self.advance()
            operand = self._parse_expression(4)  # 负号优先级为4
            return NegateNode(operand)
        
        if token.type == TokenType.OPERATOR and token.value == '+':
            self.advance()
            return self._parse_expression(4)
        
        # 获取前缀解析函数
        parselet = self.prefix_parselets.get(token.type)
        if not parselet:
            raise SyntaxError(f"Unexpected token: {token}")
        
        left = parselet()
        
        # 处理中缀运算符
        while self.current_token:
            token = self.current_token
            
            # 检查是否是运算符
            if token.type != TokenType.OPERATOR:
                break
            
            op = token.value
            precedence = self.PRECEDENCE.get(op, 0)
            
            # 如果当前运算符优先级低于最小优先级，停止
            if precedence < min_precedence:
                break
            
            self.advance()
            
            # 幂运算右结合，其他左结合
            if op == '^':
                right = self._parse_expression(precedence)  # 右结合：使用 precedence 而非 precedence + 1
            else:
                right = self._parse_expression(precedence + 1)
            
            # 创建语义运算符节点
            left = self._create_operator_node(op, left, right)
        
        return left
    
    def _create_operator_node(self, op: str, left: ASTNode, right: ASTNode) -> ASTNode:
        """根据运算符创建语义运算符节点"""
        if op == '+':
            return AddNode(left, right)
        elif op == '-':
            return SubtractNode(left, right)
        elif op == '*' or op == '\\cdot':
            return MultiplyNode(left, right)
        elif op == '/':
            return DivideNode(left, right)
        elif op == '^':
            return PowerNode(left, right)
        elif op == '=':
            return EquationNode(left, right, '=')
        else:
            return OperatorNode(op, left, right)
    
    def _parse_number(self) -> ASTNode:
        """解析数字"""
        token = self.current_token
        self.advance()
        return NumberNode(token.value)
    
    def _parse_symbol(self) -> ASTNode:
        """解析符号（变量）"""
        token = self.current_token
        self.advance()
        return SymbolNode(token.value)
    
    def _parse_unicode_math(self) -> ASTNode:
        """解析 Unicode 数学符号"""
        token = self.current_token
        self.advance()
        return SymbolNode(token.value)
    
    def _parse_command(self) -> ASTNode:
        """解析 LaTeX 命令"""
        if not self.current_token or self.current_token.type != TokenType.COMMAND:
            raise SyntaxError("Expected command")
        
        cmd_token = self.current_token
        cmd_name = cmd_token.value[1:]  # 去掉反斜杠
        self.advance()
        
        # 分数命令
        if cmd_name == 'frac':
            return self._parse_fraction()
        
        # 根号命令
        if cmd_name == 'sqrt':
            return self._parse_sqrt()
        
        # 积分命令
        if cmd_name in ('int', 'iint', 'iiint', 'oint'):
            return self._parse_integral(cmd_name)
        
        # 求和命令
        if cmd_name == 'sum':
            return self._parse_sum()
        
        # 乘积命令
        if cmd_name == 'prod':
            return self._parse_product()
        
        # 极限命令
        if cmd_name == 'lim':
            return self._parse_limit()
        
        # 文本命令
        if cmd_name == 'text':
            return self._parse_text()
        
        # 数学字体命令
        if cmd_name in ('mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb'):
            return self._parse_font_command(cmd_name)
        
        # 环境命令
        if cmd_name == 'begin':
            return self._parse_environment()
        
        # 普通命令（如 \sin, \cos）
        return self._parse_general_command(cmd_name)
    
    def _parse_group(self) -> ASTNode:
        """解析圆括号分组"""
        self.advance()  # 跳过 (
        content = self._parse_expression(0)
        if self.current_token and self.current_token.type == TokenType.PAREN_CLOSE:
            self.advance()
            return content
        raise SyntaxError("Unclosed parenthesis")
    
    def _parse_brace_group(self) -> ASTNode:
        """解析花括号分组"""
        self.advance()  # 跳过 {
        content = self._parse_expression(0)
        if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
            self.advance()
            return content
        raise SyntaxError("Unclosed brace")
    
    def _parse_bracket_group(self) -> ASTNode:
        """解析方括号分组"""
        self.advance()  # 跳过 [
        content = self._parse_expression(0)
        if self.current_token and self.current_token.type == TokenType.BRACKET_CLOSE:
            self.advance()
            return content
        raise SyntaxError("Unclosed bracket")
    
    def _parse_fraction(self) -> FractionNode:
        """解析分数 \frac{...}{...}"""
        # 解析分子
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            numerator = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
            else:
                raise SyntaxError("Unclosed brace in numerator")
        else:
            numerator = self._parse_expression(0)
        
        # 解析分母
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            denominator = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
            else:
                raise SyntaxError("Unclosed brace in denominator")
        else:
            denominator = self._parse_expression(0)
        
        return FractionNode(numerator, denominator)
    
    def _parse_sqrt(self) -> SqrtNode:
        """解析根号 \sqrt[...]{}"""
        degree = None
        
        # 检查是否有次数
        if self.current_token and self.current_token.type == TokenType.BRACKET_OPEN:
            self.advance()
            degree = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACKET_CLOSE:
                self.advance()
            else:
                raise SyntaxError("Unclosed bracket in sqrt degree")
        
        # 解析被开方数
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            radicand = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
            else:
                raise SyntaxError("Unclosed brace in sqrt")
        else:
            radicand = self._parse_expression(0)
        
        return SqrtNode(radicand, degree)
    
    def _parse_integral(self, integral_type: str) -> IntegralNode:
        """解析积分"""
        lower_limit = None
        upper_limit = None
        
        # 解析下限
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '_':
            self.advance()
            lower_limit = self._parse_atom()
        
        # 解析上限
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '^':
            self.advance()
            upper_limit = self._parse_atom()
        
        # 解析被积函数
        integrand = self._parse_expression(0)
        
        return IntegralNode(
            integrand=integrand,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            integral_type=integral_type
        )
    
    def _parse_sum(self) -> SumNode:
        """解析求和"""
        lower_limit = None
        upper_limit = None
        
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '_':
            self.advance()
            lower_limit = self._parse_atom()
        
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '^':
            self.advance()
            upper_limit = self._parse_atom()
        
        term = self._parse_expression(0)
        
        return SumNode(term=term, lower_limit=lower_limit, upper_limit=upper_limit)
    
    def _parse_product(self) -> ProductNode:
        """解析乘积"""
        lower_limit = None
        upper_limit = None
        
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '_':
            self.advance()
            lower_limit = self._parse_atom()
        
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '^':
            self.advance()
            upper_limit = self._parse_atom()
        
        term = self._parse_expression(0)
        
        return ProductNode(term=term, lower_limit=lower_limit, upper_limit=upper_limit)
    
    def _parse_limit(self) -> LimitNode:
        """解析极限"""
        variable = None
        target = None
        
        if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '_':
            self.advance()
            if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
                self.advance()
                if self.current_token and self.current_token.type in (TokenType.IDENTIFIER, TokenType.SYMBOL):
                    variable = SymbolNode(self.current_token.value)
                    self.advance()
                    
                    if self.current_token and self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\to':
                        self.advance()
                        target = self._parse_expression(0)
                
                if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                    self.advance()
        
        expression = self._parse_expression(0)
        
        if variable and target:
            return LimitNode(expression, variable, target)
        return FunctionNode('lim', [expression])
    
    def _parse_text(self) -> TextNode:
        """解析文本命令"""
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            content = []
            while self.current_token and self.current_token.type != TokenType.BRACE_CLOSE:
                content.append(self.current_token.value)
                self.advance()
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
                return TextNode(''.join(content))
            raise SyntaxError("Unclosed brace in text")
        raise SyntaxError("Expected brace after \\text")
    
    def _parse_font_command(self, cmd_name: str) -> CommandNode:
        """解析数学字体命令"""
        args = []
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            content = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
                args.append(content)
            else:
                raise SyntaxError(f"Unclosed brace in \\{cmd_name}")
        return CommandNode(cmd_name, args)
    
    def _parse_environment(self) -> ASTNode:
        """解析环境"""
        if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            env_name = ""
            while self.current_token and self.current_token.type != TokenType.BRACE_CLOSE:
                env_name += self.current_token.value
                self.advance()
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
        else:
            raise SyntaxError("Expected brace after \\begin")
        
        if env_name in ('matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Vmatrix'):
            return self._parse_matrix(env_name)
        
        if env_name == 'cases':
            return self._parse_cases()
        
        return CommandNode(f'begin{{{env_name}}}')
    
    def _parse_matrix(self, matrix_type: str) -> MatrixNode:
        """解析矩阵"""
        rows = []
        current_row = []
        
        while self.current_token and not (self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\end'):
            if self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\\\':
                self.advance()
                if current_row:
                    rows.append(current_row)
                    current_row = []
                continue
            
            if self.current_token.type == TokenType.OPERATOR and self.current_token.value == '&':
                self.advance()
                continue
            
            if self.current_token:
                current_row.append(self._parse_expression(0))
        
        if current_row:
            rows.append(current_row)
        
        if self.current_token and self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\end':
            self.advance()
            if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
                self.advance()
                while self.current_token and self.current_token.type != TokenType.BRACE_CLOSE:
                    self.advance()
                if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                    self.advance()
        
        return MatrixNode(rows, matrix_type)
    
    def _parse_cases(self) -> CasesNode:
        """解析分段函数"""
        cases = []
        
        while self.current_token and not (self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\end'):
            if self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\\\':
                self.advance()
                continue
            
            value = self._parse_expression(0)
            
            if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == '&':
                self.advance()
                condition = self._parse_expression(0)
                cases.append((condition, value))
        
        if self.current_token and self.current_token.type == TokenType.COMMAND and self.current_token.value == '\\end':
            self.advance()
            if self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
                self.advance()
                while self.current_token and self.current_token.type != TokenType.BRACE_CLOSE:
                    self.advance()
                if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                    self.advance()
        
        return CasesNode(cases)
    
    def _parse_general_command(self, cmd_name: str) -> ASTNode:
        """解析普通命令"""
        args = []
        
        while self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()
            content = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
                args.append(content)
            else:
                raise SyntaxError(f"Unclosed brace in \\{cmd_name}")
        
        if self.current_token and self.current_token.type == TokenType.PAREN_OPEN:
            self.advance()
            func_args = []
            while self.current_token and self.current_token.type != TokenType.PAREN_CLOSE:
                func_args.append(self._parse_expression(0))
                if self.current_token and self.current_token.type == TokenType.OPERATOR and self.current_token.value == ',':
                    self.advance()
            if self.current_token and self.current_token.type == TokenType.PAREN_CLOSE:
                self.advance()
                return FunctionNode(cmd_name, func_args)
        
        return FunctionNode(cmd_name, args)
    
    def _parse_atom(self) -> ASTNode:
        """解析原子表达式"""
        if not self.current_token:
            raise SyntaxError("Unexpected end of input")
        
        token = self.current_token
        
        if token.type == TokenType.BRACE_OPEN:
            self.advance()
            content = self._parse_expression(0)
            if self.current_token and self.current_token.type == TokenType.BRACE_CLOSE:
                self.advance()
                return content
            raise SyntaxError("Unclosed brace")
        
        return self._parse_expression(5)  # 最高优先级


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def parse_latex(text: str) -> ASTNode:
    """将 LaTeX 字符串解析为语义 AST"""
    lexer = LaTeXLexer()
    tokens = lexer.scan(text)
    parser = PrattParser(tokens)
    return parser.parse()


def latex_to_ast(text: str) -> dict:
    """将 LaTeX 字符串转换为 AST 字典表示"""
    ast = parse_latex(text)
    return ast.to_ast()