"""Math Normalizer - 基于 AST 的数学表达式规范化

将数学表达式转换为标准形式，用于等价性检查和语义分析。
"""

from typing import Optional
from .ast import *
from .parser import parse_latex


class MathNormalizer:
    """数学表达式规范化器"""
    
    def normalize(self, text: str) -> ASTNode:
        """将 LaTeX 字符串规范化"""
        ast = parse_latex(text)
        return self._normalize_node(ast)
    
    def _normalize_node(self, node: ASTNode) -> ASTNode:
        """递归规范化节点"""
        if isinstance(node, SymbolNode):
            return self._normalize_symbol(node)
        elif isinstance(node, NumberNode):
            return self._normalize_number(node)
        elif isinstance(node, FractionNode):
            return self._normalize_fraction(node)
        elif isinstance(node, SuperscriptNode):
            return self._normalize_superscript(node)
        elif isinstance(node, SubscriptNode):
            return self._normalize_subscript(node)
        elif isinstance(node, SequenceNode):
            return self._normalize_sequence(node)
        elif isinstance(node, OperatorNode):
            return self._normalize_operator(node)
        elif isinstance(node, IntegralNode):
            return self._normalize_integral(node)
        elif isinstance(node, SumNode):
            return self._normalize_sum(node)
        elif isinstance(node, ProductNode):
            return self._normalize_product(node)
        elif isinstance(node, CommandNode):
            return self._normalize_command(node)
        elif isinstance(node, FunctionNode):
            return self._normalize_function(node)
        elif isinstance(node, GroupNode):
            return self._normalize_group(node)
        elif isinstance(node, BracesNode):
            return self._normalize_braces(node)
        elif isinstance(node, SqrtNode):
            return self._normalize_sqrt(node)
        elif isinstance(node, EquationNode):
            return self._normalize_equation(node)
        elif isinstance(node, LimitNode):
            return self._normalize_limit(node)
        elif isinstance(node, DerivativeNode):
            return self._normalize_derivative(node)
        elif isinstance(node, MatrixNode):
            return self._normalize_matrix(node)
        elif isinstance(node, CasesNode):
            return self._normalize_cases(node)
        elif isinstance(node, TextNode):
            return node
        elif isinstance(node, SetNode):
            return self._normalize_set(node)
        # ═══════════════════════════════════════════════
        # 语义运算符节点
        # ═══════════════════════════════════════════════
        elif isinstance(node, AddNode):
            return self._normalize_add(node)
        elif isinstance(node, SubtractNode):
            return self._normalize_subtract(node)
        elif isinstance(node, MultiplyNode):
            return self._normalize_multiply(node)
        elif isinstance(node, DivideNode):
            return self._normalize_divide(node)
        elif isinstance(node, PowerNode):
            return self._normalize_power(node)
        elif isinstance(node, NegateNode):
            return self._normalize_negate(node)
        else:
            return node
    
    def _normalize_symbol(self, node: SymbolNode) -> SymbolNode:
        """规范化符号（统一大小写等）"""
        # 希腊字母统一小写（除了大写形式）
        name = node.name
        
        # 标准化常见符号名称
        standard_names = {
            'alpha': '\\alpha', 'beta': '\\beta', 'gamma': '\\gamma',
            'delta': '\\delta', 'epsilon': '\\epsilon', 'zeta': '\\zeta',
            'eta': '\\eta', 'theta': '\\theta', 'iota': '\\iota',
            'kappa': '\\kappa', 'lambda': '\\lambda', 'mu': '\\mu',
            'nu': '\\nu', 'xi': '\\xi', 'pi': '\\pi', 'rho': '\\rho',
            'sigma': '\\sigma', 'tau': '\\tau', 'phi': '\\phi',
            'chi': '\\chi', 'psi': '\\psi', 'omega': '\\omega',
            'Gamma': '\\Gamma', 'Delta': '\\Delta', 'Theta': '\\Theta',
            'Lambda': '\\Lambda', 'Xi': '\\Xi', 'Pi': '\\Pi',
            'Sigma': '\\Sigma', 'Phi': '\\Phi', 'Psi': '\\Psi',
            'Omega': '\\Omega',
        }
        
        if name in standard_names:
            return SymbolNode(standard_names[name])
        
        return SymbolNode(name)
    
    def _normalize_number(self, node: NumberNode) -> NumberNode:
        """规范化数字（去除前导零等）"""
        value = node.value
        if isinstance(value, str):
            # 去除前导零
            if '.' not in value:
                value = str(int(value))
            else:
                # 去除小数末尾的零
                value = str(float(value))
        return NumberNode(value)
    
    def _normalize_fraction(self, node: FractionNode) -> ASTNode:
        """规范化分数"""
        numerator = self._normalize_node(node.numerator)
        denominator = self._normalize_node(node.denominator)
        
        # 分母为1时，返回分子
        if isinstance(denominator, NumberNode) and denominator.value == '1':
            return numerator
        
        # 分子为0时，返回0
        if isinstance(numerator, NumberNode) and numerator.value == '0':
            return NumberNode('0')
        
        return FractionNode(numerator, denominator)
    
    def _normalize_superscript(self, node: SuperscriptNode) -> ASTNode:
        """规范化上标"""
        base = self._normalize_node(node.base)
        exponent = self._normalize_node(node.exponent)
        
        # 指数为1时，返回底数
        if isinstance(exponent, NumberNode) and exponent.value == '1':
            return base
        
        # 指数为0时，返回1
        if isinstance(exponent, NumberNode) and exponent.value == '0':
            return NumberNode('1')
        
        return SuperscriptNode(base, exponent)
    
    def _normalize_subscript(self, node: SubscriptNode) -> ASTNode:
        """规范化下标"""
        base = self._normalize_node(node.base)
        subscript = self._normalize_node(node.subscript)
        return SubscriptNode(base, subscript)
    
    def _normalize_sequence(self, node: SequenceNode) -> ASTNode:
        """规范化序列（合并相邻的符号节点）"""
        elements = []
        
        for elem in node.elements:
            normalized = self._normalize_node(elem)
            
            # 如果是 SequenceNode，展开它
            if isinstance(normalized, SequenceNode):
                elements.extend(normalized.elements)
            else:
                elements.append(normalized)
        
        # 合并相邻的 SymbolNode 和 NumberNode
        merged = []
        i = 0
        while i < len(elements):
            current = elements[i]
            
            # 尝试合并符号
            if isinstance(current, SymbolNode) and i + 1 < len(elements):
                next_elem = elements[i + 1]
                if isinstance(next_elem, SymbolNode):
                    merged.append(SymbolNode(current.name + next_elem.name))
                    i += 2
                    continue
            
            merged.append(current)
            i += 1
        
        # 如果只有一个元素，直接返回
        if len(merged) == 1:
            return merged[0]
        
        return SequenceNode(merged)
    
    def _normalize_operator(self, node: OperatorNode) -> ASTNode:
        """规范化运算符"""
        left = self._normalize_node(node.left) if node.left else None
        right = self._normalize_node(node.right) if node.right else None
        
        # 处理乘法：x * y → xy（符号之间）
        if node.operator == '*':
            if isinstance(left, (SymbolNode, NumberNode)) and isinstance(right, (SymbolNode, NumberNode)):
                # 数字之间保留乘号
                if isinstance(left, NumberNode) and isinstance(right, NumberNode):
                    return OperatorNode('*', left, right)
                # 符号之间合并
                return SequenceNode([left, right])
        
        # 处理负号：-x 保持不变
        
        return OperatorNode(node.operator, left, right)
    
    def _normalize_integral(self, node: IntegralNode) -> IntegralNode:
        """规范化积分"""
        integrand = self._normalize_node(node.integrand)
        variable = self._normalize_node(node.variable) if node.variable else None
        lower_limit = self._normalize_node(node.lower_limit) if node.lower_limit else None
        upper_limit = self._normalize_node(node.upper_limit) if node.upper_limit else None
        
        return IntegralNode(
            integrand=integrand,
            variable=variable,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            integral_type=node.integral_type
        )
    
    def _normalize_sum(self, node: SumNode) -> SumNode:
        """规范化求和"""
        term = self._normalize_node(node.term)
        lower_limit = self._normalize_node(node.lower_limit) if node.lower_limit else None
        upper_limit = self._normalize_node(node.upper_limit) if node.upper_limit else None
        
        return SumNode(term=term, lower_limit=lower_limit, upper_limit=upper_limit)
    
    def _normalize_product(self, node: ProductNode) -> ProductNode:
        """规范化乘积"""
        term = self._normalize_node(node.term)
        lower_limit = self._normalize_node(node.lower_limit) if node.lower_limit else None
        upper_limit = self._normalize_node(node.upper_limit) if node.upper_limit else None
        
        return ProductNode(term=term, lower_limit=lower_limit, upper_limit=upper_limit)
    
    def _normalize_command(self, node: CommandNode) -> ASTNode:
        """规范化命令"""
        args = [self._normalize_node(arg) for arg in node.args]
        return CommandNode(node.name, args)
    
    def _normalize_function(self, node: FunctionNode) -> FunctionNode:
        """规范化函数"""
        args = [self._normalize_node(arg) for arg in node.arguments]
        return FunctionNode(node.name, args)
    
    def _normalize_group(self, node: GroupNode) -> ASTNode:
        """规范化分组"""
        content = [self._normalize_node(item) for item in node.content]
        
        # 如果只有一个元素且不是运算符，直接返回
        if len(content) == 1:
            return content[0]
        
        return GroupNode(content)
    
    def _normalize_braces(self, node: BracesNode) -> ASTNode:
        """规范化括号"""
        content = self._normalize_node(node.content)
        
        # 如果内容是单个符号或数字，去掉括号
        if isinstance(content, (SymbolNode, NumberNode)):
            return content
        
        return BracesNode(content)
    
    def _normalize_sqrt(self, node: SqrtNode) -> ASTNode:
        """规范化根号"""
        radicand = self._normalize_node(node.radicand)
        degree = self._normalize_node(node.degree) if node.degree else None
        
        # √1 = 1
        if isinstance(radicand, NumberNode) and radicand.value == '1':
            return NumberNode('1')
        
        # √0 = 0
        if isinstance(radicand, NumberNode) and radicand.value == '0':
            return NumberNode('0')
        
        return SqrtNode(radicand, degree)
    
    def _normalize_equation(self, node: EquationNode) -> EquationNode:
        """规范化方程"""
        left = self._normalize_node(node.left)
        right = self._normalize_node(node.right)
        return EquationNode(left, right, node.relation)
    
    def _normalize_limit(self, node: LimitNode) -> LimitNode:
        """规范化极限"""
        expression = self._normalize_node(node.expression)
        variable = self._normalize_node(node.variable)
        target = self._normalize_node(node.target)
        return LimitNode(expression, variable, target)
    
    def _normalize_derivative(self, node: DerivativeNode) -> DerivativeNode:
        """规范化导数"""
        numerator = self._normalize_node(node.numerator)
        denominator = self._normalize_node(node.denominator)
        return DerivativeNode(numerator, denominator, node.order, node.partial)
    
    def _normalize_matrix(self, node: MatrixNode) -> MatrixNode:
        """规范化矩阵"""
        rows = [
            [self._normalize_node(cell) for cell in row]
            for row in node.rows
        ]
        return MatrixNode(rows, node.matrix_type)
    
    def _normalize_cases(self, node: CasesNode) -> CasesNode:
        """规范化分段函数"""
        cases = [
            (self._normalize_node(cond), self._normalize_node(val))
            for cond, val in node.cases
        ]
        return CasesNode(cases)
    
    def _normalize_set(self, node: SetNode) -> SetNode:
        """规范化集合"""
        elements = [self._normalize_node(e) for e in node.elements]
        return SetNode(elements, node.is_infinite)

    # ═══════════════════════════════════════════════
    # 语义运算符节点规范化方法
    # ═══════════════════════════════════════════════

    def _normalize_add(self, node: AddNode) -> ASTNode:
        """规范化加法"""
        left = self._normalize_node(node.left)
        right = self._normalize_node(node.right)
        
        # x + 0 = x
        if isinstance(right, NumberNode) and right.value == '0':
            return left
        
        # 0 + x = x
        if isinstance(left, NumberNode) and left.value == '0':
            return right
        
        # x + (-y) = x - y
        if isinstance(right, NegateNode):
            return SubtractNode(left, right.operand)
        
        return AddNode(left, right)

    def _normalize_subtract(self, node: SubtractNode) -> ASTNode:
        """规范化减法"""
        left = self._normalize_node(node.left)
        right = self._normalize_node(node.right)
        
        # x - 0 = x
        if isinstance(right, NumberNode) and right.value == '0':
            return left
        
        # x - (-y) = x + y
        if isinstance(right, NegateNode):
            return AddNode(left, right.operand)
        
        return SubtractNode(left, right)

    def _normalize_multiply(self, node: MultiplyNode) -> ASTNode:
        """规范化乘法"""
        left = self._normalize_node(node.left)
        right = self._normalize_node(node.right)
        
        # x * 1 = x
        if isinstance(right, NumberNode) and right.value == '1':
            return left
        
        # 1 * x = x
        if isinstance(left, NumberNode) and left.value == '1':
            return right
        
        # x * 0 = 0
        if isinstance(right, NumberNode) and right.value == '0':
            return NumberNode('0')
        
        # 0 * x = 0
        if isinstance(left, NumberNode) and left.value == '0':
            return NumberNode('0')
        
        return MultiplyNode(left, right)

    def _normalize_divide(self, node: DivideNode) -> ASTNode:
        """规范化除法"""
        numerator = self._normalize_node(node.numerator)
        denominator = self._normalize_node(node.denominator)
        
        # x / 1 = x
        if isinstance(denominator, NumberNode) and denominator.value == '1':
            return numerator
        
        # 0 / x = 0 (x != 0)
        if isinstance(numerator, NumberNode) and numerator.value == '0':
            return NumberNode('0')
        
        return DivideNode(numerator, denominator)

    def _normalize_power(self, node: PowerNode) -> ASTNode:
        """规范化幂运算"""
        base = self._normalize_node(node.base)
        exponent = self._normalize_node(node.exponent)
        
        # x^1 = x
        if isinstance(exponent, NumberNode) and exponent.value == '1':
            return base
        
        # x^0 = 1
        if isinstance(exponent, NumberNode) and exponent.value == '0':
            return NumberNode('1')
        
        # 0^x = 0 (x > 0)
        if isinstance(base, NumberNode) and base.value == '0':
            return NumberNode('0')
        
        # 1^x = 1
        if isinstance(base, NumberNode) and base.value == '1':
            return NumberNode('1')
        
        return PowerNode(base, exponent)

    def _normalize_negate(self, node: NegateNode) -> ASTNode:
        """规范化取反"""
        operand = self._normalize_node(node.operand)
        
        # -(-x) = x
        if isinstance(operand, NegateNode):
            return operand.operand
        
        # -(0) = 0
        if isinstance(operand, NumberNode) and operand.value == '0':
            return NumberNode('0')
        
        # -(a + b) = -a - b
        if isinstance(operand, AddNode):
            return AddNode(
                NegateNode(operand.left),
                NegateNode(operand.right)
            )
        
        return NegateNode(operand)


def normalize_latex(text: str) -> str:
    """便捷函数：将 LaTeX 字符串规范化并返回 LaTeX"""
    normalizer = MathNormalizer()
    ast = normalizer.normalize(text)
    return ast.to_latex()


def normalize_to_ast(text: str) -> ASTNode:
    """便捷函数：将 LaTeX 字符串规范化并返回 AST"""
    normalizer = MathNormalizer()
    return normalizer.normalize(text)


def are_equivalent(expr1: str, expr2: str) -> bool:
    """检查两个数学表达式是否等价（基于规范化）"""
    normalizer = MathNormalizer()
    ast1 = normalizer.normalize(expr1)
    ast2 = normalizer.normalize(expr2)
    
    # 比较 LaTeX 表示（简化的等价性检查）
    return ast1.to_latex() == ast2.to_latex()


def canonical_form(text: str) -> str:
    """获取表达式的标准形式"""
    return normalize_latex(text)