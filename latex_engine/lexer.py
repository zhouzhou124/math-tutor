"""LaTeX Lexer - 数学语言编译器的词法分析层

这是系统架构的关键组件，负责将原始文本转换为结构化的token流。

核心设计原则：
1. 词法边界保护：正确识别完整的LaTeX命令
2. 数学语义感知：区分数学符号与普通文本
3. 增量可扩展：从基础token类型开始，逐步扩展

支持的token类型：
- TEXT: 普通文本（中文、英文、数字等）
- COMMAND: LaTeX命令（如 \sin, \frac, \sqrt）
- BRACE: 花括号 { }
- OPERATOR: 数学运算符（+ - * / = < > 等）
- NUMBER: 数字（整数、小数、科学计数法）
- UNICODE_MATH: Unicode数学符号（∈, ≤, ≥, π等）
- ENVIRONMENT: LaTeX环境（\begin{...}\end{...}）
- WHITESPACE: 空白字符
- NEWLINE: 换行符
"""

from typing import List, Optional, Union
from enum import Enum
import re


class TokenType(Enum):
    """Token类型枚举"""
    TEXT = "text"
    COMMAND = "command"
    BRACE_OPEN = "brace_open"
    BRACE_CLOSE = "brace_close"
    PAREN_OPEN = "paren_open"    # 新增：左圆括号
    PAREN_CLOSE = "paren_close"  # 新增：右圆括号
    BRACKET_OPEN = "bracket_open"  # 新增：左方括号
    BRACKET_CLOSE = "bracket_close"  # 新增：右方括号
    OPERATOR = "operator"
    NUMBER = "number"
    UNICODE_MATH = "unicode_math"
    ENVIRONMENT_START = "environment_start"
    ENVIRONMENT_END = "environment_end"
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    DOLLAR = "dollar"
    IDENTIFIER = "identifier"  # 数学变量标识符
    COMMA = "comma"  # 逗号
    EOF = "eof"  # 文件结束


class Token:
    """Token对象"""
    
    def __init__(self, type: TokenType, value: str, position: int = 0):
        self.type = type
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, pos={self.position})"
    
    def __eq__(self, other):
        if isinstance(other, Token):
            return self.type == other.type and self.value == other.value
        return False


class LaTeXLexer:
    """LaTeX词法分析器"""
    
    # Unicode数学符号映射
    UNICODE_MATH_SYMBOLS = {
        # 关系符号
        '∈': '\\in', '∉': '\\notin', '∋': '\\ni', '∌': '\\notni',
        '≤': '\\leq', '≥': '\\geq', '≠': '\\neq', '≡': '\\equiv',
        '≈': '\\approx', '≅': '\\cong', '∼': '\\sim', '≃': '\\simeq',
        # 运算符号
        '±': '\\pm', '∓': '\\mp', '×': '\\times', '÷': '\\div',
        '⋅': '\\cdot', '∘': '\\circ', '∗': '\\ast', '⊗': '\\otimes',
        '⊕': '\\oplus', '⊙': '\\odot',
        # 集合符号
        '∪': '\\cup', '∩': '\\cap', '⊂': '\\subset', '⊃': '\\supset',
        '⊆': '\\subseteq', '⊇': '\\supseteq', '∅': '\\emptyset',
        # 逻辑符号
        '∀': '\\forall', '∃': '\\exists', '¬': '\\neg',
        # 箭头
        '→': '\\to', '←': '\\leftarrow', '↔': '\\leftrightarrow',
        '⇒': '\\Rightarrow', '⇐': '\\Leftarrow', '⇔': '\\Leftrightarrow',
        # 希腊字母
        'α': '\\alpha', 'β': '\\beta', 'γ': '\\gamma', 'δ': '\\delta',
        'ε': '\\epsilon', 'ζ': '\\zeta', 'η': '\\eta', 'θ': '\\theta',
        'λ': '\\lambda', 'μ': '\\mu', 'ν': '\\nu', 'ξ': '\\xi',
        'π': '\\pi', 'ρ': '\\rho', 'σ': '\\sigma', 'τ': '\\tau',
        'φ': '\\phi', 'χ': '\\chi', 'ψ': '\\psi', 'ω': '\\omega',
        'Γ': '\\Gamma', 'Δ': '\\Delta', 'Θ': '\\Theta', 'Λ': '\\Lambda',
        'Ξ': '\\Xi', 'Π': '\\Pi', 'Σ': '\\Sigma', 'Φ': '\\Phi',
        'Ψ': '\\Psi', 'Ω': '\\Omega',
        # 其他符号
        '∞': '\\infty', '∂': '\\partial', '∇': '\\nabla',
        '√': '\\sqrt', '∫': '\\int', '∬': '\\iint', '∭': '\\iiint',
        '∮': '\\oint', '∑': '\\sum', '∏': '\\prod',
        '√': '\\sqrt', '∛': '\\sqrt[3]', '∜': '\\sqrt[4]',
    }
    
    # 数学运算符
    MATH_OPERATORS = set('+-*/=<>!|^_~:')
    
    # 二元运算符（需要特殊处理）
    BINARY_OPS = {'==', '!=', '<=', '>=', '->', '=>', '<-', '<=>', '::', '&&', '||'}
    
    def __init__(self, text: str = ""):
        self.text = text
        self.pos = 0
        self.tokens = []
        self.token_index = 0
        if text:
            self.scan(text)
    
    def scan(self, text: str) -> List[Token]:
        """主入口：将文本转换为token流"""
        self.text = text
        self.pos = 0
        self.tokens = []
        
        while self.pos < len(self.text):
            token = self._next_token()
            if token:
                self.tokens.append(token)
        
        return self.tokens
    
    def next_token(self) -> Token:
        """获取下一个 token（用于 Pratt 解析器）"""
        if self.token_index < len(self.tokens):
            token = self.tokens[self.token_index]
            self.token_index += 1
            return token
        return Token(TokenType.EOF, '', len(self.text))
    
    def _next_token(self) -> Optional[Token]:
        """获取下一个token"""
        if self.pos >= len(self.text):
            return None
        
        char = self.text[self.pos]
        
        # 换行符
        if char == '\n':
            token = Token(TokenType.NEWLINE, '\n', self.pos)
            self.pos += 1
            return token
        
        # 空白字符（不包括换行）
        if char.isspace() and char != '\n':
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isspace() and self.text[self.pos] != '\n':
                self.pos += 1
            token = Token(TokenType.WHITESPACE, self.text[start:self.pos], start)
            return token
        
        # 花括号
        if char == '{':
            token = Token(TokenType.BRACE_OPEN, '{', self.pos)
            self.pos += 1
            return token
        if char == '}':
            token = Token(TokenType.BRACE_CLOSE, '}', self.pos)
            self.pos += 1
            return token
        
        # 圆括号
        if char == '(':
            token = Token(TokenType.PAREN_OPEN, '(', self.pos)
            self.pos += 1
            return token
        if char == ')':
            token = Token(TokenType.PAREN_CLOSE, ')', self.pos)
            self.pos += 1
            return token
        
        # 逗号
        if char == ',':
            token = Token(TokenType.COMMA, ',', self.pos)
            self.pos += 1
            return token
        
        # 方括号
        if char == '[':
            token = Token(TokenType.BRACKET_OPEN, '[', self.pos)
            self.pos += 1
            return token
        if char == ']':
            token = Token(TokenType.BRACKET_CLOSE, ']', self.pos)
            self.pos += 1
            return token
        
        # $ 符号（数学模式分隔符）
        if char == '$':
            token = Token(TokenType.DOLLAR, '$', self.pos)
            self.pos += 1
            return token
        
        # 反斜杠命令
        if char == '\\':
            return self._parse_command()
        
        # Unicode数学符号
        if char in self.UNICODE_MATH_SYMBOLS:
            token = Token(TokenType.UNICODE_MATH, char, self.pos)
            self.pos += 1
            return token
        
        # 数字
        if char.isdigit() or (char == '.' and self._peek().isdigit()):
            return self._parse_number()
        
        # 运算符
        if char in self.MATH_OPERATORS:
            return self._parse_operator()
        
        # 标识符（数学变量名）
        if char.islower():
            return self._parse_identifier()
        
        # 普通文本（中文、英文大写字母等）
        return self._parse_text()
    
    def _parse_command(self) -> Token:
        """解析LaTeX命令"""
        start = self.pos
        self.pos += 1  # 跳过反斜杠
        
        # 获取命令名称
        if self.pos < len(self.text) and self.text[self.pos].isalpha():
            # 字母命令：\sin, \frac, etc.
            cmd_start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isalpha():
                self.pos += 1
            cmd_name = self.text[cmd_start:self.pos]
            value = '\\' + cmd_name
            
            # ═══════════════════════════════════════════════
            # 路径检测：如果前面是 `:` 或路径分隔符，不是命令
            # ═══════════════════════════════════════════════
            if start > 0:
                prev_char = self.text[start - 1]
                # Windows 路径如 C:\new_folder 或 Unix 路径如 /home/user
                if prev_char == ':' or prev_char == '\\' or prev_char == '/':
                    # 检查是否真的是路径（后面跟着字母、数字和下划线）
                    # 路径中的反斜杠后面通常跟着目录名（字母开头）
                    # 如果后面是字母或下划线，可能是路径的一部分
                    if self.pos < len(self.text):
                        next_char = self.text[self.pos] if self.pos < len(self.text) else ''
                        if next_char.isalpha() or next_char == '_':
                            # 回退，当作普通文本处理
                            self.pos = start
                            return self._parse_text()
                # 特殊处理：如果前面是数字（如 1:\new），也可能是路径
                elif prev_char.isdigit():
                    # 检查是否前面还有冒号
                    j = start - 2
                    while j >= 0 and self.text[j].isdigit():
                        j -= 1
                    if j >= 0 and self.text[j] == ':':
                        # 看起来像 Windows 路径如 1:\folder
                        self.pos = start
                        return self._parse_text()
                # 特殊处理：前面是空格或换行，后面跟着路径风格的内容
                elif prev_char.isspace():
                    # 检查后面是否是驱动器盘符格式（单个字母+冒号+反斜杠）
                    if self.pos + 2 < len(self.text):
                        # 检查命令名称是否是单个字母（如 C, D, E）
                        if len(cmd_name) == 1 and self.text[self.pos:self.pos+2] == ':\\':
                            # 这是路径驱动器盘符，当作文本处理
                            self.pos = start
                            return self._parse_text()
            
            # ═══════════════════════════════════════════════
            # 路径检测：如果后面跟着文件扩展名（如 .txt），不是命令
            # ═══════════════════════════════════════════════
            if self.pos < len(self.text):
                remaining = self.text[self.pos:]
                # 检查是否是路径中的文件名（如 \test.txt）
                if remaining.startswith('.'):
                    # 检查后面是否是常见文件扩展名
                    ext_patterns = ('.txt', '.doc', '.pdf', '.jpg', '.png', '.py', '.js', '.html', '.css', '.xml', '.json', '.md', '.csv', '.xlsx', '.docx', '.zip', '.rar', '.exe', '.dll')
                    for ext in ext_patterns:
                        if remaining.startswith(ext):
                            # 这是路径中的文件名，当作文本处理
                            self.pos = start
                            return self._parse_text()
            
            # 检查是否是环境开始
            if cmd_name == 'begin':
                # 读取环境名称
                if self.pos < len(self.text) and self.text[self.pos] == '{':
                    self.pos += 1
                    env_start = self.pos
                    while self.pos < len(self.text) and self.text[self.pos] != '}':
                        self.pos += 1
                    if self.pos < len(self.text) and self.text[self.pos] == '}':
                        self.pos += 1
                        env_name = self.text[env_start:self.pos-1]
                        return Token(TokenType.ENVIRONMENT_START, f'\\begin{{{env_name}}}', start)
                return Token(TokenType.COMMAND, value, start)
            
            # 检查是否是环境结束
            if cmd_name == 'end':
                if self.pos < len(self.text) and self.text[self.pos] == '{':
                    self.pos += 1
                    env_start = self.pos
                    while self.pos < len(self.text) and self.text[self.pos] != '}':
                        self.pos += 1
                    if self.pos < len(self.text) and self.text[self.pos] == '}':
                        self.pos += 1
                        env_name = self.text[env_start:self.pos-1]
                        return Token(TokenType.ENVIRONMENT_END, f'\\end{{{env_name}}}', start)
                return Token(TokenType.COMMAND, value, start)
            
            return Token(TokenType.COMMAND, value, start)
        
        # 非字母命令：\$, \&, \_, etc.
        if self.pos < len(self.text):
            special_char = self.text[self.pos]
            self.pos += 1
            return Token(TokenType.COMMAND, '\\' + special_char, start)
        
        # 孤立的反斜杠
        return Token(TokenType.COMMAND, '\\', start)
    
    def _parse_number(self) -> Token:
        """解析数字"""
        start = self.pos
        has_dot = False
        
        # 整数部分
        if self.text[self.pos] == '.':
            has_dot = True
            self.pos += 1
        else:
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        
        # 小数部分
        if self.pos < len(self.text) and self.text[self.pos] == '.' and not has_dot:
            has_dot = True
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        
        # 科学计数法
        if self.pos < len(self.text) and self.text[self.pos].lower() == 'e':
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in '+-':
                self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self.pos += 1
        
        return Token(TokenType.NUMBER, self.text[start:self.pos], start)
    
    def _parse_operator(self) -> Token:
        """解析运算符"""
        start = self.pos
        
        # 检查二元运算符
        for op in sorted(self.BINARY_OPS, key=len, reverse=True):
            if self.text.startswith(op, self.pos):
                # 特殊处理 ::
                if op == '::':
                    # 检查是否是 C++ 作用域解析符或其他用途
                    return Token(TokenType.OPERATOR, op, start)
                self.pos += len(op)
                return Token(TokenType.OPERATOR, op, start)
        
        # 单元运算符
        char = self.text[self.pos]
        
        # ═══════════════════════════════════════════════
        # 特殊处理冒号：检查是否是路径的一部分
        # ═══════════════════════════════════════════════
        if char == ':':
            # 如果前面是单个字母（如 C:\），这是 Windows 路径
            if start > 0 and start - 1 >= 0:
                prev_char = self.text[start - 1]
                # 检查是否是驱动器盘符（单个字母）
                if prev_char.isalpha() and (start == 1 or not self.text[start - 2].isalpha()):
                    # 检查后面是否跟着反斜杠或正斜杠
                    if self.pos + 1 < len(self.text):
                        next_char = self.text[self.pos + 1]
                        if next_char == '\\' or next_char == '/':
                            # 这是路径的一部分，当作普通文本处理
                            self.pos += 1
                            return Token(TokenType.TEXT, ':', start)
        
        self.pos += 1
        return Token(TokenType.OPERATOR, char, start)
    
    def _parse_identifier(self) -> Token:
        """解析标识符（数学变量名）"""
        start = self.pos
        
        # 标识符规则：小写字母开头，后跟小写字母、数字或下划线
        # 支持下标形式如 x_n, f_1
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char.islower() or char.isdigit() or char == '_':
                self.pos += 1
            else:
                break
        
        return Token(TokenType.IDENTIFIER, self.text[start:self.pos], start)
    
    def _parse_text(self) -> Token:
        """解析普通文本"""
        start = self.pos
        
        # 文本分类：中文、英文、其他字符
        while self.pos < len(self.text):
            char = self.text[self.pos]
            
            # 检查是否应该结束
            if char in '\\{}$':
                break
            if char.isspace():
                break
            if char in self.MATH_OPERATORS:
                break
            if char in self.UNICODE_MATH_SYMBOLS:
                break
            
            self.pos += 1
        
        # 如果没有匹配到任何字符，返回单个字符
        if self.pos == start:
            self.pos += 1
            return Token(TokenType.TEXT, self.text[start:self.pos], start)
        
        return Token(TokenType.TEXT, self.text[start:self.pos], start)
    
    def _peek(self) -> str:
        """查看下一个字符"""
        if self.pos + 1 < len(self.text):
            return self.text[self.pos + 1]
        return ''


class MathSpanDetector:
    """数学区域检测器 - 基于token流识别数学表达式区域"""
    
    # 数学相关的命令
    MATH_COMMANDS = {
        'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
        'sinh', 'cosh', 'tanh', 'coth', 'sech', 'csch',
        'arcsin', 'arccos', 'arctan', 'arccot', 'arcsec', 'arccsc',
        'log', 'ln', 'exp', 'lg', 'min', 'max',
        'sum', 'prod', 'int', 'oint', 'iint', 'iiint', 'iiiint', 'idotsint',
        'lim', 'limsup', 'liminf', 'varlimsup', 'varliminf',
        'frac', 'dfrac', 'cfrac', 'tfrac', 'sqrt', 'root',
        'abs', 'norm',
        'hat', 'widehat', 'tilde', 'widetilde', 'bar', 'vec', 'dot', 'ddot',
        'prime', 'dagger', 'ddagger',
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb',
        'ldots', 'cdots', 'vdots', 'ddots',
        'left', 'right', 'middle', 'Big', 'bigg', 'Biggl', 'biggr', 'Biggr',
        'partial', 'nabla', 'triangle', 'square', 'diamond', 'circ', 'bullet',
        'oplus', 'otimes', 'odot', 'coprod', 'bigcup', 'bigcap', 'bigsqcup',
        'subseteq', 'supseteq', 'approx', 'cong', 'equiv', 'sim', 'simeq',
        'leq', 'geq', 'neq', 'sim', 'simeq', 'approx', 'cong',
        'in', 'notin', 'ni', 'exists', 'forall', 'emptyset', 'infty',
        'to', 'partial', 'nabla',
        'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta',
        'lambda', 'mu', 'nu', 'xi', 'pi', 'rho', 'sigma', 'tau',
        'phi', 'chi', 'psi', 'omega',
        'Gamma', 'Delta', 'Theta', 'Lambda', 'Xi', 'Pi', 'Sigma', 'Upsilon',
        'Phi', 'Psi', 'Omega',
        'Rightarrow', 'Leftarrow', 'leftrightarrow', 'Leftrightarrow',
        'rightarrow', 'leftarrow', 'mapsto', 'hookleftarrow', 'hookrightarrow',
        'cdot', 'times', 'div', 'pm', 'mp', 'cap', 'cup', 'setminus',
    }
    
    # 文本命令（这些命令后面的内容应该被视为文本）
    TEXT_COMMANDS = {
        'text', 'mbox', 'fbox', 'parbox', 'minipage',
        'caption', 'label', 'ref', 'cite', 'include', 'input',
        'title', 'author', 'date', 'maketitle',
        'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph',
        'begin', 'end', 'newcommand', 'renewcommand', 'def', 'let',
        'usepackage', 'documentclass',
    }
    
    # 数学字体命令（这些命令在数学环境中使用，后面跟着花括号内容）
    MATH_FONT_COMMANDS = {
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb',
        'mathrm', 'mathbf', 'mathcal', 'mathit', 'mathtt', 'mathsf', 'mathbb',
        'overline', 'underline', 'overbrace', 'underbrace',
        'hat', 'widehat', 'tilde', 'widetilde', 'bar', 'vec', 'dot', 'ddot',
    }
    
    def __init__(self):
        self.lexer = LaTeXLexer()
    
    def detect(self, text: str) -> List[tuple]:
        """检测文本中的数学区域，返回区间列表 [(start, end, is_math), ...]"""
        tokens = self.lexer.scan(text)
        return self._detect_math_spans(tokens, text)
    
    def _detect_math_spans(self, tokens: List[Token], original_text: str) -> List[tuple]:
        """基于token流检测数学区域"""
        spans = []
        n = len(tokens)
        i = 0
        
        while i < n:
            token = tokens[i]
            
            # 跳过空白和换行
            if token.type in (TokenType.WHITESPACE, TokenType.NEWLINE):
                i += 1
                continue
            
            # 已存在的数学模式分隔符
            if token.type == TokenType.DOLLAR:
                spans.extend(self._parse_dollar_math(tokens, i))
                i = self._find_next_after_dollar(tokens, i)
                continue
            
            # 检查是否是环境
            if token.type == TokenType.ENVIRONMENT_START:
                spans.extend(self._parse_environment(tokens, i))
                i = self._find_next_after_environment(tokens, i)
                continue
            
            # 检查是否应该开始数学区域
            if self._is_math_token(token):
                math_span = self._find_math_span(tokens, i)
                if math_span:
                    start, end, end_idx = math_span
                    spans.append((start, end, 'detected_math'))
                    i = end_idx
                    continue
            
            # 普通文本
            spans.append((token.position, token.position + len(token.value), 'text'))
            i += 1
        
        return spans
    
    def _is_math_token(self, token: Token) -> bool:
        """判断token是否是数学相关的"""
        if token.type in (TokenType.COMMAND, TokenType.UNICODE_MATH, TokenType.OPERATOR, TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.PAREN_OPEN, TokenType.PAREN_CLOSE, TokenType.BRACKET_OPEN, TokenType.BRACKET_CLOSE):
            if token.type == TokenType.COMMAND:
                cmd_name = token.value[1:] if token.value.startswith('\\') else token.value
                return cmd_name in self.MATH_COMMANDS or cmd_name in self.MATH_FONT_COMMANDS
            return True
        return False
    
    def _parse_dollar_math(self, tokens: List[Token], start_idx: int) -> List[tuple]:
        """解析 $...$ 或 $$...$$ 数学区域"""
        spans = []
        n = len(tokens)
        i = start_idx
        
        # 检查是否是 $$
        is_double = False
        if i + 1 < n and tokens[i+1].type == TokenType.DOLLAR:
            is_double = True
            i += 2
        else:
            i += 1
        
        start_pos = tokens[start_idx].position
        content_start = tokens[i].position if i < n else start_pos
        
        # 找到匹配的结束 $
        while i < n:
            if tokens[i].type == TokenType.DOLLAR:
                if is_double and i + 1 < n and tokens[i+1].type == TokenType.DOLLAR:
                    end_pos = tokens[i+1].position + 1
                    span_type = 'display_math'
                    i += 2
                else:
                    end_pos = tokens[i].position + 1
                    span_type = 'inline_math'
                    i += 1
                
                spans.append((start_pos, end_pos, span_type))
                return spans
            
            # 收集内容
            i += 1
        
        # 未找到匹配的 $，返回文本
        spans.append((start_pos, len(self.lexer.text) if i >= n else tokens[i-1].position + len(tokens[i-1].value), 'text'))
        return spans
    
    def _parse_environment(self, tokens: List[Token], start_idx: int) -> List[tuple]:
        """解析 \begin{...}\end{...} 环境"""
        n = len(tokens)
        start_token = tokens[start_idx]
        env_name = start_token.value.replace('\\begin{', '').replace('}', '')
        start_pos = start_token.position
        
        # 找到匹配的 \end
        i = start_idx + 1
        while i < n:
            if tokens[i].type == TokenType.ENVIRONMENT_END:
                end_env_name = tokens[i].value.replace('\\end{', '').replace('}', '')
                if end_env_name == env_name:
                    end_pos = tokens[i].position + len(tokens[i].value)
                    # 判断是否是数学环境
                    math_envs = {'equation', 'align', 'align*', 'gather', 'gather*', 
                                'math', 'displaymath', 'array', 'matrix', 'pmatrix',
                                'bmatrix', 'vmatrix', 'Vmatrix'}
                    span_type = 'display_math' if env_name in math_envs else 'environment'
                    return [(start_pos, end_pos, span_type)]
            i += 1
        
        # 未找到匹配的 \end
        return [(start_pos, start_pos + len(start_token.value), 'text')]
    
    def _find_math_span(self, tokens: List[Token], start_idx: int) -> Optional[tuple]:
        """从指定位置开始查找数学表达式的边界"""
        n = len(tokens)
        if start_idx >= n:
            return None
        
        start_token = tokens[start_idx]
        start_pos = start_token.position
        
        # 数学token类型
        math_token_types = {
            TokenType.COMMAND,
            TokenType.NUMBER,
            TokenType.OPERATOR,
            TokenType.UNICODE_MATH,
            TokenType.BRACE_OPEN,
            TokenType.BRACE_CLOSE,
            TokenType.PAREN_OPEN,    # 新增
            TokenType.PAREN_CLOSE,   # 新增
            TokenType.BRACKET_OPEN,  # 新增
            TokenType.BRACKET_CLOSE, # 新增
            TokenType.WHITESPACE,
            TokenType.NEWLINE,
            TokenType.IDENTIFIER,
        }
        
        i = start_idx
        brace_depth = 0
        paren_depth = 0  # 圆括号深度
        bracket_depth = 0  # 方括号深度
        last_math_pos = start_pos
        
        # 统计数学内容
        math_content_count = 0
        total_content_count = 0
        
        while i < n:
            token = tokens[i]
            
            # 更新各种括号深度
            if token.type == TokenType.BRACE_OPEN:
                brace_depth += 1
            elif token.type == TokenType.BRACE_CLOSE:
                brace_depth -= 1
            elif token.type == TokenType.PAREN_OPEN:
                paren_depth += 1
            elif token.type == TokenType.PAREN_CLOSE:
                paren_depth -= 1
            elif token.type == TokenType.BRACKET_OPEN:
                bracket_depth += 1
            elif token.type == TokenType.BRACKET_CLOSE:
                bracket_depth -= 1
            
            # 检查token类型
            if token.type in math_token_types:
                # 检查命令是否是数学命令
                if token.type == TokenType.COMMAND:
                    cmd_name = token.value[1:] if token.value.startswith('\\') else token.value
                    # 如果遇到文本命令，结束（除非在花括号内）
                    if cmd_name in self.TEXT_COMMANDS and brace_depth <= 0:
                        break
                    # 如果遇到非数学命令且所有括号都平衡，结束
                    if cmd_name not in self.MATH_COMMANDS and cmd_name not in self.MATH_FONT_COMMANDS and cmd_name not in self.TEXT_COMMANDS and brace_depth <= 0 and paren_depth <= 0 and bracket_depth <= 0:
                        # 如果已经有数学内容，结束；否则返回None
                        if i > start_idx:
                            break
                        else:
                            return None
                
                # 统计数学内容
                if token.type not in (TokenType.WHITESPACE, TokenType.NEWLINE):
                    if token.type == TokenType.COMMAND:
                        math_content_count += 2  # 命令权重更高
                    elif token.type in (TokenType.OPERATOR, TokenType.NUMBER, TokenType.UNICODE_MATH):
                        math_content_count += 1.5  # 运算符、数字权重较高
                    else:
                        math_content_count += 1
                    total_content_count += 1
                
                last_math_pos = token.position + len(token.value)
                i += 1
            
            else:
                # 遇到非数学token（如普通文本、路径等）
                # 如果所有括号都平衡，结束数学区域
                if brace_depth <= 0 and paren_depth <= 0 and bracket_depth <= 0:
                    break
                # 否则继续（可能在括号内部）
                i += 1
        
        # ═══════════════════════════════════════════════
        # 最小数学内容检查
        # ═══════════════════════════════════════════════
        # 确保有足够的数学内容才能形成数学区域
        # - 至少需要2个非空白token
        # - 数学内容比例至少达到一定阈值
        if total_content_count < 2:
            return None
        
        # 计算数学密度
        math_density = math_content_count / total_content_count if total_content_count > 0 else 0
        
        # 如果只有单个标识符，不认为是数学区域
        if total_content_count == 1 and start_token.type == TokenType.IDENTIFIER:
            return None
        
        # 如果数学密度太低，不认为是数学区域
        if math_density < 0.5:
            return None
        
        # 计算结果
        if last_math_pos > start_pos:
            return (start_pos, last_math_pos, i)
        
        return None
    
    def _find_next_after_dollar(self, tokens: List[Token], start_idx: int) -> int:
        """找到 $ 结束后的下一个token"""
        n = len(tokens)
        i = start_idx
        
        if i + 1 < n and tokens[i].type == TokenType.DOLLAR and tokens[i+1].type == TokenType.DOLLAR:
            i += 2
        else:
            i += 1
        
        # 找到匹配的结束 $
        while i < n:
            if tokens[i].type == TokenType.DOLLAR:
                if i + 1 < n and tokens[i+1].type == TokenType.DOLLAR:
                    return i + 2
                return i + 1
            i += 1
        
        return n
    
    def _find_next_after_environment(self, tokens: List[Token], start_idx: int) -> int:
        """找到环境结束后的下一个token"""
        n = len(tokens)
        env_name = tokens[start_idx].value.replace('\\begin{', '').replace('}', '')
        
        i = start_idx + 1
        while i < n:
            if tokens[i].type == TokenType.ENVIRONMENT_END:
                end_env_name = tokens[i].value.replace('\\end{', '').replace('}', '')
                if end_env_name == env_name:
                    return i + 1
            i += 1
        
        return n
    
    def _find_token_at_position(self, tokens: List[Token], position: int) -> int:
        """找到指定位置对应的token索引"""
        for i, token in enumerate(tokens):
            if token.position >= position:
                return i
        return len(tokens)
    
    def wrap_math_spans(self, text: str) -> str:
        """将检测到的数学区域用 $ 包裹"""
        spans = self.detect(text)
        
        # 从后往前处理，避免位置偏移
        result = text
        for start, end, span_type in reversed(spans):
            if span_type == 'detected_math':
                # 用 $ 包裹检测到的数学区域
                math_content = text[start:end]
                # 避免重复包裹
                if not math_content.startswith('$') and not math_content.endswith('$'):
                    result = result[:start] + '$' + math_content + '$' + result[end:]
        
        return result


# 便捷函数
def tokenize(text: str) -> List[Token]:
    """便捷函数：将文本转换为token流"""
    lexer = LaTeXLexer()
    return lexer.scan(text)


def detect_math(text: str) -> List[tuple]:
    """便捷函数：检测文本中的数学区域"""
    detector = MathSpanDetector()
    return detector.detect(text)


def wrap_math(text: str) -> str:
    """便捷函数：将数学区域用 $ 包裹"""
    detector = MathSpanDetector()
    return detector.wrap_math_spans(text)
