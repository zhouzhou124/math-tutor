"""
LaTeX Tokenizer

将 LaTeX 字符串转换为结构化的 Token 序列。

核心功能：
  1. 识别 LaTeX 命令（\sin, \cos, \frac 等）
  2. 识别数学符号（+, -, =, (, ), {, } 等）
  3. 识别变量和数字
  4. 处理分组和参数
  5. 处理转义字符

Token 类型：
  - CommandToken: LaTeX 命令（如 \sin, \frac）
  - SymbolToken: 数学符号（如 +, =, (, )）
  - VariableToken: 变量（如 x, x_n, a_n）
  - NumberToken: 数字（如 1, 2.5, \pi）
  - GroupToken: 分组（{...}）
  - SuperscriptToken: 上标（^）
  - SubscriptToken: 下标（_）
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, List, Optional, Union


class TokenType(Enum):
    """Token 类型枚举"""
    COMMAND = auto()       # LaTeX 命令 (\sin, \frac)
    SYMBOL = auto()        # 数学符号 (+, -, =, (, ))
    VARIABLE = auto()      # 变量 (x, x_n, a_n)
    NUMBER = auto()        # 数字 (1, 2.5, \pi)
    GROUP = auto()         # 分组 ({...})
    SUPERSCRIPT = auto()   # 上标 (^)
    SUBSCRIPT = auto()     # 下标 (_)
    WHITESPACE = auto()    # 空白字符
    TEXT = auto()          # 普通文本


@dataclass(frozen=True)
class Token:
    """Token 基类"""
    type: TokenType
    value: str
    position: int  # 在原始字符串中的位置
    
    def __repr__(self) -> str:
        return f"<{self.type.name}: {repr(self.value)} at {self.position}>"
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'value': self.value,
            'position': self.position,
        }


class CommandToken(Token):
    """LaTeX 命令 Token"""
    def __init__(self, name: str, position: int, args: List[Token] = None):
        super().__init__(TokenType.COMMAND, name, position)
        self.args = args or []


class SymbolToken(Token):
    """数学符号 Token"""
    def __init__(self, symbol: str, position: int):
        super().__init__(TokenType.SYMBOL, symbol, position)


class VariableToken(Token):
    """变量 Token"""
    def __init__(self, name: str, position: int, subscript: Optional[str] = None):
        super().__init__(TokenType.VARIABLE, name, position)
        self.subscript = subscript
    
    @property
    def full_name(self) -> str:
        """完整变量名（包含下标）"""
        if self.subscript:
            return f"{self.value}_{self.subscript}"
        return self.value


class NumberToken(Token):
    """数字 Token"""
    def __init__(self, value: str, position: int, is_symbolic: bool = False):
        super().__init__(TokenType.NUMBER, value, position)
        self.is_symbolic = is_symbolic  # 是否为符号常量（如 \pi, \infty）


class GroupToken(Token):
    """分组 Token"""
    def __init__(self, content: List[Token], position: int):
        super().__init__(TokenType.GROUP, '{}', position)
        self.content = content


class SuperscriptToken(Token):
    """上标 Token"""
    def __init__(self, position: int):
        super().__init__(TokenType.SUPERSCRIPT, '^', position)


class SubscriptToken(Token):
    """下标 Token"""
    def __init__(self, position: int):
        super().__init__(TokenType.SUBSCRIPT, '_', position)


class LatexTokenizer:
    """
    LaTeX 词法分析器
    
    核心算法：
      1. 逐字符扫描输入字符串
      2. 根据上下文识别 Token 类型
      3. 处理命令、分组、上下标等特殊结构
    """
    
    def __init__(self):
        # LaTeX 命令列表
        self.commands = {
            # 三角函数
            'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
            'arcsin', 'arccos', 'arctan', 'arccot',
            # 双曲函数
            'sinh', 'cosh', 'tanh', 'coth',
            # 指数对数
            'exp', 'log', 'ln',
            # 极限
            'lim', 'limsup', 'liminf',
            # 微积分
            'frac', 'dfrac', 'cfrac',
            'int', 'oint', 'sum', 'prod',
            'partial', 'nabla', 'det', 'rank',
            # 根号
            'sqrt', 'root',
            # 希腊字母
            'alpha', 'beta', 'gamma', 'delta', 'epsilon',
            'zeta', 'eta', 'theta', 'iota', 'kappa',
            'lambda', 'mu', 'nu', 'xi', 'pi', 'rho',
            'sigma', 'tau', 'upsilon', 'phi', 'chi',
            'psi', 'omega',
            'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi',
            'Pi', 'Sigma', 'Upsilon', 'Phi', 'Psi', 'Omega',
            # 运算符
            'cdot', 'times', 'div', 'pm', 'mp',
            'leq', 'geq', 'neq', 'equiv', 'approx',
            'in', 'subset', 'supset', 'subseteq', 'supseteq',
            'cap', 'cup', 'setminus',
            # 箭头
            'to', 'rightarrow', 'leftarrow', 'Rightarrow',
            'Leftarrow', 'leftrightarrow', 'Leftrightarrow',
            'mapsto',
            # 文本
            'text', 'mathrm', 'mathbf', 'textit', 'textbf',
            # 其他
            'infty', 'partial', 'nabla', 'degree',
        }
        
        # 符号常量
        self.symbolic_constants = {'pi', 'pi', 'infty', 'e', 'phi', 'gamma'}
        
        # 二元运算符
        self.binary_operators = {'+', '-', '*', '/', '=', '<', '>', ':', '|'}
        
        # 分组符号
        self.group_openers = {'(', '[', '{'}
        self.group_closers = {')', ']', '}'}
        self.group_pairs = {'(': ')', '[': ']', '{': '}'}
    
    def tokenize(self, text: str) -> List[Token]:
        """
        将 LaTeX 字符串转换为 Token 序列。
        
        Args:
            text: LaTeX 字符串
        
        Returns:
            List[Token]: Token 序列
        """
        tokens = []
        i = 0
        n = len(text)
        
        while i < n:
            char = text[i]
            
            # 跳过空白字符
            if char.isspace():
                i += 1
                continue
            
            # 处理反斜杠（命令开始）
            if char == '\\':
                command, args, consumed = self._parse_command(text, i)
                if command:
                    tokens.append(command)
                    tokens.extend(args)
                    i += consumed
                else:
                    i += 1
                continue
            
            # 处理上标
            if char == '^':
                tokens.append(SuperscriptToken(i))
                i += 1
                continue
            
            # 处理下标
            if char == '_':
                tokens.append(SubscriptToken(i))
                i += 1
                continue
            
            # 处理分组
            if char in self.group_openers:
                group, consumed = self._parse_group(text, i)
                tokens.append(group)
                i += consumed
                continue
            
            # 处理数字
            if char.isdigit() or char == '.':
                number, consumed = self._parse_number(text, i)
                tokens.append(number)
                i += consumed
                continue
            
            # 处理变量（字母开头）
            if char.isalpha():
                variable, consumed = self._parse_variable(text, i)
                tokens.append(variable)
                i += consumed
                continue
            
            # 处理符号
            if char in self.binary_operators or char in self.group_closers:
                tokens.append(SymbolToken(char, i))
                i += 1
                continue
            
            # 其他字符作为文本
            tokens.append(Token(TokenType.TEXT, char, i))
            i += 1
        
        return tokens
    
    def _parse_command(self, text: str, start: int) -> tuple[Optional[CommandToken], List[Token], int]:
        """
        解析 LaTeX 命令。
        
        Returns:
            (命令Token, 参数Token列表, 消耗的字符数)
        """
        if start + 1 >= len(text):
            return None, [], 1
        
        # 读取命令名
        i = start + 1
        command_name = ''
        
        # 命令名由字母组成
        while i < len(text) and text[i].isalpha():
            command_name += text[i]
            i += 1
        
        if not command_name:
            # 可能是转义字符（如 \}）
            if i < len(text):
                return None, [Token(TokenType.TEXT, text[i], i)], 2
            return None, [], 1
        
        # 检查是否为已知命令
        if command_name not in self.commands:
            # 未知命令，作为普通文本处理
            return None, [Token(TokenType.TEXT, '\\' + command_name, start)], i - start
        
        # 解析命令参数
        args = []
        remaining = text[i:]
        pos = i
        
        # 根据命令类型解析参数
        if command_name in {'frac', 'dfrac', 'cfrac'}:
            # frac 有两个参数：分子和分母
            if remaining.startswith('{'):
                numerator, consumed = self._parse_group(text, pos)
                args.append(numerator)
                pos += consumed
                remaining = text[pos:]
            
            if remaining.startswith('{'):
                denominator, consumed = self._parse_group(text, pos)
                args.append(denominator)
                pos += consumed
        
        elif command_name in {'sqrt', 'root'}:
            # sqrt 可能有可选的根指数
            if remaining.startswith('['):
                # 解析根指数
                bracket_end = remaining.find(']')
                if bracket_end != -1:
                    exponent = Token(TokenType.TEXT, remaining[1:bracket_end], pos + 1)
                    args.append(exponent)
                    pos += bracket_end + 1
            
            # 解析被开方数
            if text[pos:].startswith('{'):
                radicand, consumed = self._parse_group(text, pos)
                args.append(radicand)
                pos += consumed
        
        elif command_name in {'sum', 'prod', 'int', 'oint'}:
            # 可能有上下限
            remaining = text[pos:]
            
            # 检查下标
            if remaining.startswith('_'):
                args.append(SubscriptToken(pos))
                pos += 1
                if text[pos:].startswith('{'):
                    sub_group, consumed = self._parse_group(text, pos)
                    args.append(sub_group)
                    pos += consumed
                else:
                    # 单字符下标
                    args.append(Token(TokenType.TEXT, text[pos], pos))
                    pos += 1
            
            # 检查上标
            remaining = text[pos:]
            if remaining.startswith('^'):
                args.append(SuperscriptToken(pos))
                pos += 1
                if text[pos:].startswith('{'):
                    sup_group, consumed = self._parse_group(text, pos)
                    args.append(sup_group)
                    pos += consumed
                else:
                    # 单字符上标
                    args.append(Token(TokenType.TEXT, text[pos], pos))
                    pos += 1
        
        elif command_name in {'lim', 'limsup', 'liminf'}:
            # 极限可能有下标
            remaining = text[pos:]
            if remaining.startswith('_'):
                args.append(SubscriptToken(pos))
                pos += 1
                if text[pos:].startswith('{'):
                    sub_group, consumed = self._parse_group(text, pos)
                    args.append(sub_group)
                    pos += consumed
        
        command = CommandToken(command_name, start, args)
        return command, args, pos - start
    
    def _parse_group(self, text: str, start: int) -> tuple[GroupToken, int]:
        """
        解析分组 {...}
        
        Returns:
            (分组Token, 消耗的字符数)
        """
        if start >= len(text) or text[start] not in self.group_openers:
            return GroupToken([], start), 1
        
        opener = text[start]
        closer = self.group_pairs[opener]
        content = []
        i = start + 1
        depth = 1
        
        while i < len(text) and depth > 0:
            char = text[i]
            
            if char == '\\':
                # 处理转义字符
                if i + 1 < len(text):
                    content.append(Token(TokenType.TEXT, text[i+1], i))
                    i += 2
                    continue
                else:
                    i += 1
                    continue
            
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    break
            
            content.append(Token(TokenType.TEXT, char, i))
            i += 1
        
        # 递归解析分组内容
        inner_tokens = self.tokenize(''.join(t.value for t in content))
        
        return GroupToken(inner_tokens, start), i - start + 1
    
    def _parse_number(self, text: str, start: int) -> tuple[NumberToken, int]:
        """
        解析数字。
        
        Returns:
            (数字Token, 消耗的字符数)
        """
        i = start
        value = ''
        
        # 检查是否为符号常量
        if text[i:].startswith('\\'):
            j = i + 1
            name = ''
            while j < len(text) and text[j].isalpha():
                name += text[j]
                j += 1
            if name in self.symbolic_constants:
                return NumberToken('\\' + name, start, is_symbolic=True), j - start
        
        # 解析数字
        has_dot = False
        
        while i < len(text):
            char = text[i]
            if char.isdigit():
                value += char
                i += 1
            elif char == '.' and not has_dot:
                value += char
                has_dot = True
                i += 1
            else:
                break
        
        if value:
            return NumberToken(value, start, is_symbolic=False), i - start
        
        return NumberToken(text[start], start, is_symbolic=False), 1
    
    def _parse_variable(self, text: str, start: int) -> tuple[VariableToken, int]:
        """
        解析变量。
        
        Returns:
            (变量Token, 消耗的字符数)
        """
        i = start
        name = ''
        
        # 读取变量名
        while i < len(text) and (text[i].isalnum() or text[i] == '_'):
            name += text[i]
            i += 1
        
        # 检查是否带下标
        subscript = None
        if '_' in name:
            parts = name.split('_', 1)
            name = parts[0]
            subscript = parts[1]
        
        return VariableToken(name, start, subscript), i - start


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def tokenize_latex(text: str) -> List[Token]:
    """便捷函数：tokenize LaTeX"""
    tokenizer = LatexTokenizer()
    return tokenizer.tokenize(text)


def tokens_to_string(tokens: List[Token]) -> str:
    """将 Token 序列转换回字符串"""
    result = []
    for token in tokens:
        if token.type == TokenType.COMMAND:
            result.append(f'\\{token.value}')
        elif token.type == TokenType.VARIABLE:
            if token.subscript:
                result.append(f'{token.value}_{token.subscript}')
            else:
                result.append(token.value)
        elif token.type == TokenType.NUMBER:
            result.append(token.value)
        elif token.type == TokenType.GROUP:
            result.append('{' + tokens_to_string(token.content) + '}')
        else:
            result.append(token.value)
    return ''.join(result)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        r"\sin(x_n)",
        r"\cos(\sin x)",
        r"\lim_{n\to\infty} \frac{n^2+1}{2n^2-n}",
        r"x_n \in [-\frac{\pi}{2}, \frac{\pi}{2}]",
    ]
    
    for latex in test_cases:
        print(f"=== Input: {latex} ===")
        tokens = tokenize_latex(latex)
        for token in tokens:
            print(f"  {token}")
        print(f"Reconstructed: {tokens_to_string(tokens)}")
        print()
