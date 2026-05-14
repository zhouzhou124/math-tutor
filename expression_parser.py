"""expression_parser.py — LaTeX表达式解析器

将 LaTeX 数学表达式解析为 Expression AST，支持：
- 基本算术运算
- 三角函数、指数、对数
- 导数、积分、极限
- 下标变量
"""
from __future__ import annotations
import re
from typing import Optional, List, Tuple
from expression_ast import *


class ExpressionParser:
    """LaTeX 表达式解析器"""
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
    
    def parse(self, latex: str) -> ExprNode:
        """解析 LaTeX 表达式为 AST"""
        if not latex:
            raise ValueError("空表达式")
        
        # 预处理：移除前后的 $ 符号
        latex = latex.strip()
        if latex.startswith('$'):
            latex = latex[1:]
        if latex.endswith('$'):
            latex = latex[:-1]
        
        # 分词
        self.tokens = self._tokenize(latex)
        self.pos = 0
        
        # 解析表达式
        return self._parse_expression()
    
    def _tokenize(self, latex: str) -> List[Tuple[str, str]]:
        """将 LaTeX 字符串分词"""
        tokens = []
        
        # 定义 token 模式
        patterns = [
            # 命令（如 \sin, \frac, \int）
            (r'\\[a-zA-Z]+', 'COMMAND'),
            # 数字（整数或小数）
            (r'\d+\.?\d*', 'NUMBER'),
            # 变量名
            (r'[a-zA-Z][a-zA-Z0-9]*', 'IDENTIFIER'),
            # 运算符
            (r'\+', 'PLUS'),
            (r'-', 'MINUS'),
            (r'\*', 'MUL'),
            (r'/', 'DIV'),
            (r'\^', 'CARET'),
            (r'=', 'EQUALS'),
            (r'<', 'LT'),
            (r'>', 'GT'),
            # 括号
            (r'\(', 'LPAREN'),
            (r'\)', 'RPAREN'),
            (r'\{', 'LBRACE'),
            (r'\}', 'RBRACE'),
            (r'\[', 'LBRACKET'),
            (r'\]', 'RBRACKET'),
            # 下标
            (r'_', 'UNDERSCORE'),
            # 空格（忽略）
            (r'\s+', 'SPACE'),
            # 其他字符
            (r'.', 'OTHER'),
        ]
        
        pos = 0
        while pos < len(latex):
            matched = False
            for pattern, token_type in patterns:
                match = re.match(pattern, latex[pos:])
                if match:
                    token = match.group()
                    if token_type != 'SPACE':
                        tokens.append((token, token_type))
                    pos += len(token)
                    matched = True
                    break
            if not matched:
                pos += 1
        
        return tokens
    
    def _parse_expression(self) -> ExprNode:
        """解析顶层表达式"""
        return self._parse_binary_op(0)
    
    def _parse_binary_op(self, min_precedence: int) -> ExprNode:
        """解析二元运算（带优先级）"""
        # 优先级：
        # 0: +, -
        # 1: *, /
        # 2: ^
        left = self._parse_unary()
        
        while True:
            op_token = self._peek()
            if not op_token:
                break
            
            token, token_type = op_token
            
            # 获取运算符优先级
            precedence = self._get_precedence(token_type)
            if precedence < min_precedence:
                break
            
            if token_type in ['PLUS', 'MINUS', 'MUL', 'DIV', 'CARET']:
                self._consume()
                right = self._parse_binary_op(precedence + 1)
                
                if token_type == 'PLUS':
                    left = add(left, right)
                elif token_type == 'MINUS':
                    left = sub(left, right)
                elif token_type == 'MUL':
                    left = mul(left, right)
                elif token_type == 'DIV':
                    left = div(left, right)
                elif token_type == 'CARET':
                    left = pow(left, right)
            else:
                break
        
        return left
    
    def _get_precedence(self, token_type: str) -> int:
        """获取运算符优先级"""
        precedence = {
            'PLUS': 0,
            'MINUS': 0,
            'MUL': 1,
            'DIV': 1,
            'CARET': 2,
        }
        return precedence.get(token_type, -1)
    
    def _parse_unary(self) -> ExprNode:
        """解析一元运算"""
        token = self._peek()
        if not token:
            raise ValueError("意外的表达式结束")
        
        token_value, token_type = token
        
        # 处理负号
        if token_type == 'MINUS':
            self._consume()
            operand = self._parse_unary()
            return neg(operand)
        
        return self._parse_primary()
    
    def _parse_primary(self) -> ExprNode:
        """解析基本元素"""
        token = self._peek()
        if not token:
            raise ValueError("意外的表达式结束")
        
        token_value, token_type = token
        
        # 数字
        if token_type == 'NUMBER':
            self._consume()
            return Number(float(token_value))
        
        # 命令（如 \sin, \frac, \int）
        if token_type == 'COMMAND':
            self._consume()
            return self._parse_command(token_value)
        
        # 标识符（变量或常量）
        if token_type == 'IDENTIFIER':
            self._consume()
            return self._parse_identifier(token_value)
        
        # 括号
        if token_type == 'LPAREN':
            self._consume()
            expr = self._parse_expression()
            self._expect('RPAREN')
            return expr
        
        # 花括号
        if token_type == 'LBRACE':
            self._consume()
            expr = self._parse_expression()
            self._expect('RBRACE')
            return expr
        
        raise ValueError(f"无法解析的 token: {token_value}")
    
    def _parse_command(self, command: str) -> ExprNode:
        """解析 LaTeX 命令"""
        command = command[1:]  # 移除反斜杠
        
        # 三角函数
        trig_funcs = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc']
        if command in trig_funcs:
            arg = self._parse_argument()
            return Function(command, [arg])
        
        # 对数函数
        if command == 'ln':
            arg = self._parse_argument()
            return Function('ln', [arg])
        if command == 'log':
            arg = self._parse_argument()
            return Function('log', [arg])
        
        # 平方根
        if command == 'sqrt':
            arg = self._parse_argument()
            return Function('sqrt', [arg])
        
        # 指数
        if command == 'exp':
            arg = self._parse_argument()
            return Function('exp', [arg])
        
        # 绝对值
        if command == 'abs':
            arg = self._parse_argument()
            return Function('abs', [arg])
        
        # 分数
        if command == 'frac':
            numerator = self._parse_braced()
            denominator = self._parse_braced()
            return div(numerator, denominator)
        
        # 积分
        if command == 'int':
            return self._parse_integral()
        
        # 极限
        if command == 'lim':
            return self._parse_limit()
        
        # 求和
        if command == 'sum':
            arg = self._parse_argument()
            return Function('sum', [arg])
        
        # 乘积
        if command == 'prod':
            arg = self._parse_argument()
            return Function('prod', [arg])
        
        # 希腊字母常量
        greek_constants = {
            'pi': Constant('pi'),
            'e': Constant('e'),
        }
        if command in greek_constants:
            return greek_constants[command]
        
        # 未知命令，作为函数处理
        arg = self._parse_argument()
        return Function(command, [arg])
    
    def _parse_identifier(self, name: str) -> ExprNode:
        """解析标识符（变量或常量）"""
        # 检查是否是下标变量
        next_token = self._peek()
        if next_token and next_token[1] == 'UNDERSCORE':
            self._consume()  # 消耗下划线
            subscript = self._parse_subscript()
            return Variable(name, subscript)
        
        # 检查是否是常量
        constants = {'pi': Constant('pi'), 'e': Constant('e')}
        if name.lower() in constants:
            return constants[name.lower()]
        
        return Variable(name)
    
    def _parse_subscript(self) -> str:
        """解析下标内容"""
        token = self._peek()
        if not token:
            return ""
        
        token_value, token_type = token
        
        if token_type == 'LBRACE':
            self._consume()
            subscript = ""
            while self._peek() and self._peek()[1] != 'RBRACE':
                subscript += self._peek()[0]
                self._consume()
            self._expect('RBRACE')
            return subscript
        elif token_type == 'IDENTIFIER' or token_type == 'NUMBER':
            self._consume()
            return token_value
        
        return ""
    
    def _parse_argument(self) -> ExprNode:
        """解析函数参数"""
        token = self._peek()
        if not token:
            raise ValueError("缺少函数参数")
        
        token_value, token_type = token
        
        if token_type == 'LBRACE':
            self._consume()
            expr = self._parse_expression()
            self._expect('RBRACE')
            return expr
        elif token_type == 'LPAREN':
            self._consume()
            expr = self._parse_expression()
            self._expect('RPAREN')
            return expr
        
        # 简单参数
        return self._parse_primary()
    
    def _parse_braced(self) -> ExprNode:
        """解析花括号内的表达式"""
        token = self._peek()
        if not token or token[1] != 'LBRACE':
            raise ValueError("期望 {")
        
        self._consume()
        expr = self._parse_expression()
        self._expect('RBRACE')
        return expr
    
    def _parse_integral(self) -> ExprNode:
        """解析积分表达式"""
        # 检查是否有上下限
        lower_bound = None
        upper_bound = None
        
        # 可能有下标（下限）
        next_token = self._peek()
        if next_token and next_token[1] == 'UNDERSCORE':
            self._consume()
            # 检查是否有花括号
            if self._peek() and self._peek()[1] == 'LBRACE':
                lower_bound = self._parse_braced()
            else:
                # 没有花括号，只解析单个 token（数字或变量）
                lower_bound = self._parse_primary()
        
        # 可能有上标（上限）
        next_token = self._peek()
        if next_token and next_token[1] == 'CARET':
            self._consume()
            # 检查是否有花括号
            if self._peek() and self._peek()[1] == 'LBRACE':
                upper_bound = self._parse_braced()
            else:
                # 没有花括号，只解析单个 token（数字或变量）
                upper_bound = self._parse_primary()
        
        # 被积表达式
        integrand = self._parse_expression()
        
        # 积分变量（以 d 开头）
        next_token = self._peek()
        var_name = 'x'  # 默认变量
        if next_token and next_token[0] == 'd':
            self._consume()
            # 获取变量名
            if self._peek():
                var_name = self._peek()[0]
                self._consume()
        
        return Integral(integrand, Variable(var_name), lower_bound, upper_bound)
    
    def _parse_limit(self) -> ExprNode:
        """解析极限表达式"""
        # 期望下标
        next_token = self._peek()
        if not next_token or next_token[1] != 'UNDERSCORE':
            raise ValueError("极限表达式缺少下标")
        
        self._consume()
        
        # 获取下标内容
        subscript_content = ""
        if self._peek() and self._peek()[1] == 'LBRACE':
            self._consume()
            while self._peek() and self._peek()[1] != 'RBRACE':
                subscript_content += self._peek()[0]
                self._consume()
            self._expect('RBRACE')
        else:
            # 简单下标
            while self._peek() and self._peek()[1] not in ['LPAREN', 'LBRACE', 'RPAREN', 'SPACE']:
                subscript_content += self._peek()[0]
                self._consume()
        
        # 解析下标：如 "x\\to0"
        subscript_parser = ExpressionParser()
        subscript_parser.tokens = subscript_parser._tokenize(subscript_content)
        subscript_parser.pos = 0
        
        # 第一个是变量
        var_token = subscript_parser._peek()
        if not var_token:
            raise ValueError("极限表达式缺少变量")
        var_name = var_token[0]
        subscript_parser._consume()
        
        # 跳过 to
        if subscript_parser._peek() and subscript_parser._peek()[0] == '\\to':
            subscript_parser._consume()
        
        # 获取逼近值
        approach_expr = subscript_parser._parse_expression()
        
        # 获取被取极限的表达式
        expr = self._parse_expression()
        
        return Limit(expr, Variable(var_name), approach_expr)
    
    def _peek(self) -> Optional[Tuple[str, str]]:
        """查看当前 token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _consume(self) -> Optional[Tuple[str, str]]:
        """消耗当前 token"""
        token = self._peek()
        if token:
            self.pos += 1
        return token
    
    def _expect(self, token_type: str) -> None:
        """期望特定类型的 token"""
        token = self._consume()
        if not token or token[1] != token_type:
            raise ValueError(f"期望 {token_type}，得到 {token}")


# 便捷函数
def parse_latex(latex: str) -> ExprNode:
    """解析 LaTeX 表达式为 AST"""
    parser = ExpressionParser()
    return parser.parse(latex)


def latex_to_ast(latex: str) -> ExprNode:
    """别名：解析 LaTeX 表达式为 AST"""
    return parse_latex(latex)


def ast_to_latex(expr: ExprNode) -> str:
    """将 AST 转换为 LaTeX"""
    return expr.to_latex()


def evaluate_latex(latex: str, variables: Dict[str, float] = None) -> float:
    """计算 LaTeX 表达式的值"""
    expr = parse_latex(latex)
    return expr.evaluate(variables)


def simplify_latex(latex: str) -> str:
    """简化 LaTeX 表达式"""
    expr = parse_latex(latex)
    simplified = expr.simplify()
    return simplified.to_latex()