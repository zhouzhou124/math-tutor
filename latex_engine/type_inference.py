"""Type Inference Engine - 类型推断引擎

实现数学表达式的类型推断，将无类型 AST 转换为有类型 AST。
"""

from typing import Optional, Dict, Any
from .ast import *
from .types import MathType, TypeRules, is_subtype, TypeError, type_to_string
from .type_environment import TypeEnvironment, create_default_environment


class TypeInferenceEngine:
    """类型推断引擎"""
    
    def __init__(self, env: Optional[TypeEnvironment] = None):
        self.env = env or create_default_environment()
    
    def infer(self, node: ASTNode) -> ASTNode:
        """推断表达式的类型，并返回带类型的 AST"""
        return self._infer_node(node)
    
    def _infer_node(self, node: ASTNode) -> ASTNode:
        """递归推断节点类型"""
        if isinstance(node, SymbolNode):
            return self._infer_symbol(node)
        elif isinstance(node, NumberNode):
            return self._infer_number(node)
        elif isinstance(node, AddNode):
            return self._infer_add(node)
        elif isinstance(node, SubtractNode):
            return self._infer_subtract(node)
        elif isinstance(node, MultiplyNode):
            return self._infer_multiply(node)
        elif isinstance(node, DivideNode):
            return self._infer_divide(node)
        elif isinstance(node, PowerNode):
            return self._infer_power(node)
        elif isinstance(node, NegateNode):
            return self._infer_negate(node)
        elif isinstance(node, FunctionNode):
            return self._infer_function(node)
        elif isinstance(node, FractionNode):
            return self._infer_fraction(node)
        elif isinstance(node, SqrtNode):
            return self._infer_sqrt(node)
        elif isinstance(node, IntegralNode):
            return self._infer_integral(node)
        elif isinstance(node, SumNode):
            return self._infer_sum(node)
        elif isinstance(node, ProductNode):
            return self._infer_product(node)
        elif isinstance(node, LimitNode):
            return self._infer_limit(node)
        elif isinstance(node, SequenceNode):
            return self._infer_sequence(node)
        elif isinstance(node, GroupNode):
            return self._infer_group(node)
        elif isinstance(node, EquationNode):
            return self._infer_equation(node)
        elif isinstance(node, CommandNode):
            return self._infer_command(node)
        elif isinstance(node, MatrixNode):
            return self._infer_matrix(node)
        elif isinstance(node, CasesNode):
            return self._infer_cases(node)
        elif isinstance(node, TextNode):
            return node  # 文本节点无类型
        elif isinstance(node, BracesNode):
            return self._infer_braces(node)
        elif isinstance(node, SetNode):
            return self._infer_set(node)
        elif isinstance(node, DerivativeNode):
            return self._infer_derivative(node)
        elif isinstance(node, OperatorNode):
            return self._infer_operator(node)
        else:
            return node
    
    def _infer_symbol(self, node: SymbolNode) -> SymbolNode:
        """推断符号类型"""
        symbol_type = self.env.get(node.name)
        
        # 如果类型未知且不是内置符号，尝试从上下文推断
        if symbol_type == MathType.UNKNOWN:
            # 默认假设为实数（常见情况）
            symbol_type = MathType.REAL
        
        return SymbolNode(node.name, math_type=symbol_type)
    
    def _infer_number(self, node: NumberNode) -> NumberNode:
        """推断数字类型（已在构造时处理）"""
        return node
    
    def _infer_add(self, node: AddNode) -> AddNode:
        """推断加法类型"""
        left = self._infer_node(node.left)
        right = self._infer_node(node.right)
        
        left_type = left.math_type if isinstance(left, TypedNode) else MathType.UNKNOWN
        right_type = right.math_type if isinstance(right, TypedNode) else MathType.UNKNOWN
        
        # 使用类型规则
        rule = TypeRules.get_add_rules()
        result_type = rule.apply(left_type, right_type)
        
        if result_type is None:
            # 如果类型规则不匹配，尝试公共超类型
            result_type = self._common_supertype(left_type, right_type)
            
            if result_type == MathType.ANY:
                # 无法确定类型，报错
                raise TypeError(
                    f"Cannot add {type_to_string(left_type)} and {type_to_string(right_type)}",
                    expr_type=(left_type, right_type),
                    expected_type=MathType.REAL
                )
        
        return AddNode(left, right, math_type=result_type)
    
    def _infer_subtract(self, node: SubtractNode) -> SubtractNode:
        """推断减法类型"""
        left = self._infer_node(node.left)
        right = self._infer_node(node.right)
        
        left_type = left.math_type if isinstance(left, TypedNode) else MathType.UNKNOWN
        right_type = right.math_type if isinstance(right, TypedNode) else MathType.UNKNOWN
        
        rule = TypeRules.get_subtract_rules()
        result_type = rule.apply(left_type, right_type)
        
        if result_type is None:
            result_type = self._common_supertype(left_type, right_type)
            
            if result_type == MathType.ANY:
                raise TypeError(
                    f"Cannot subtract {type_to_string(right_type)} from {type_to_string(left_type)}",
                    expr_type=(left_type, right_type),
                    expected_type=MathType.REAL
                )
        
        return SubtractNode(left, right, math_type=result_type)
    
    def _infer_multiply(self, node: MultiplyNode) -> MultiplyNode:
        """推断乘法类型"""
        left = self._infer_node(node.left)
        right = self._infer_node(node.right)
        
        left_type = left.math_type if isinstance(left, TypedNode) else MathType.UNKNOWN
        right_type = right.math_type if isinstance(right, TypedNode) else MathType.UNKNOWN
        
        rule = TypeRules.get_multiply_rules()
        result_type = rule.apply(left_type, right_type)
        
        if result_type is None:
            # 特殊处理：符号和符号相乘保持符号类型
            if left_type == MathType.REAL and right_type == MathType.UNKNOWN:
                result_type = MathType.REAL
            elif left_type == MathType.UNKNOWN and right_type == MathType.REAL:
                result_type = MathType.REAL
            else:
                result_type = self._common_supertype(left_type, right_type)
            
            if result_type == MathType.ANY:
                raise TypeError(
                    f"Cannot multiply {type_to_string(left_type)} and {type_to_string(right_type)}",
                    expr_type=(left_type, right_type),
                    expected_type=MathType.REAL
                )
        
        return MultiplyNode(left, right, math_type=result_type)
    
    def _infer_divide(self, node: DivideNode) -> DivideNode:
        """推断除法类型"""
        numerator = self._infer_node(node.numerator)
        denominator = self._infer_node(node.denominator)
        
        num_type = numerator.math_type if isinstance(numerator, TypedNode) else MathType.UNKNOWN
        den_type = denominator.math_type if isinstance(denominator, TypedNode) else MathType.UNKNOWN
        
        rule = TypeRules.get_divide_rules()
        result_type = rule.apply(num_type, den_type)
        
        if result_type is None:
            result_type = self._common_supertype(num_type, den_type)
            
            if result_type == MathType.ANY:
                raise TypeError(
                    f"Cannot divide {type_to_string(num_type)} by {type_to_string(den_type)}",
                    expr_type=(num_type, den_type),
                    expected_type=MathType.REAL
                )
        
        return DivideNode(numerator, denominator, math_type=result_type)
    
    def _infer_power(self, node: PowerNode) -> PowerNode:
        """推断幂运算类型"""
        base = self._infer_node(node.base)
        exponent = self._infer_node(node.exponent)
        
        base_type = base.math_type if isinstance(base, TypedNode) else MathType.UNKNOWN
        exp_type = exponent.math_type if isinstance(exponent, TypedNode) else MathType.UNKNOWN
        
        rule = TypeRules.get_power_rules()
        result_type = rule.apply(base_type, exp_type)
        
        if result_type is None:
            # 默认假设为实数
            result_type = MathType.REAL
        
        return PowerNode(base, exponent, math_type=result_type)
    
    def _infer_negate(self, node: NegateNode) -> NegateNode:
        """推断取反类型"""
        operand = self._infer_node(node.operand)
        operand_type = operand.math_type if isinstance(operand, TypedNode) else MathType.UNKNOWN
        
        rules = TypeRules.get_unary_rules()
        if '-' in rules and operand_type in rules['-']:
            result_type = rules['-'][operand_type]
        else:
            result_type = operand_type
        
        return NegateNode(operand, math_type=result_type)
    
    def _infer_function(self, node: FunctionNode) -> FunctionNode:
        """推断函数类型"""
        # 推断参数类型
        args = [self._infer_node(arg) for arg in node.arguments]
        
        # 根据函数名推断返回类型
        func_name = node.name.lower()
        
        # 三角函数返回实数
        if func_name in ['sin', 'cos', 'tan', 'sinh', 'cosh', 'tanh', 
                         'asin', 'acos', 'atan']:
            return FunctionNode(node.name, args, math_type=MathType.REAL)
        
        # 指数函数返回实数
        if func_name == 'exp':
            return FunctionNode(node.name, args, math_type=MathType.REAL)
        
        # 对数函数返回实数
        if func_name in ['log', 'ln']:
            return FunctionNode(node.name, args, math_type=MathType.REAL)
        
        # 根号返回实数
        if func_name == 'sqrt':
            return FunctionNode(node.name, args, math_type=MathType.REAL)
        
        # 极限返回实数
        if func_name == 'lim':
            return FunctionNode(node.name, args, math_type=MathType.REAL)
        
        # 默认返回实数
        return FunctionNode(node.name, args, math_type=MathType.REAL)
    
    def _infer_fraction(self, node: FractionNode) -> FractionNode:
        """推断分数类型"""
        numerator = self._infer_node(node.numerator)
        denominator = self._infer_node(node.denominator)
        
        num_type = numerator.math_type if isinstance(numerator, TypedNode) else MathType.UNKNOWN
        den_type = denominator.math_type if isinstance(denominator, TypedNode) else MathType.UNKNOWN
        
        # 分数类型取决于分子和分母
        if num_type == MathType.INTEGER and den_type == MathType.INTEGER:
            result_type = MathType.RATIONAL
        elif num_type == MathType.REAL or den_type == MathType.REAL:
            result_type = MathType.REAL
        else:
            result_type = self._common_supertype(num_type, den_type)
        
        return FractionNode(numerator, denominator, math_type=result_type)
    
    def _infer_sqrt(self, node: SqrtNode) -> SqrtNode:
        """推断根号类型"""
        radicand = self._infer_node(node.radicand)
        radicand_type = radicand.math_type if isinstance(radicand, TypedNode) else MathType.UNKNOWN
        
        # 根号通常返回实数
        return SqrtNode(radicand, node.degree, math_type=MathType.REAL)
    
    def _infer_integral(self, node: IntegralNode) -> IntegralNode:
        """推断积分类型"""
        integrand = self._infer_node(node.integrand)
        integrand_type = integrand.math_type if isinstance(integrand, TypedNode) else MathType.UNKNOWN
        
        # 积分结果类型通常与被积函数相同
        return IntegralNode(
            integrand=integrand,
            variable=self._infer_node(node.variable) if node.variable else None,
            lower_limit=self._infer_node(node.lower_limit) if node.lower_limit else None,
            upper_limit=self._infer_node(node.upper_limit) if node.upper_limit else None,
            integral_type=node.integral_type,
            math_type=integrand_type
        )
    
    def _infer_sum(self, node: SumNode) -> SumNode:
        """推断求和类型"""
        term = self._infer_node(node.term)
        term_type = term.math_type if isinstance(term, TypedNode) else MathType.UNKNOWN
        
        return SumNode(
            term=term,
            index=self._infer_node(node.index) if node.index else None,
            lower_limit=self._infer_node(node.lower_limit) if node.lower_limit else None,
            upper_limit=self._infer_node(node.upper_limit) if node.upper_limit else None,
            math_type=term_type
        )
    
    def _infer_product(self, node: ProductNode) -> ProductNode:
        """推断乘积类型"""
        term = self._infer_node(node.term)
        term_type = term.math_type if isinstance(term, TypedNode) else MathType.UNKNOWN
        
        return ProductNode(
            term=term,
            index=self._infer_node(node.index) if node.index else None,
            lower_limit=self._infer_node(node.lower_limit) if node.lower_limit else None,
            upper_limit=self._infer_node(node.upper_limit) if node.upper_limit else None,
            math_type=term_type
        )
    
    def _infer_limit(self, node: LimitNode) -> LimitNode:
        """推断极限类型"""
        expression = self._infer_node(node.expression)
        expr_type = expression.math_type if isinstance(expression, TypedNode) else MathType.UNKNOWN
        
        return LimitNode(
            expression=expression,
            variable=self._infer_node(node.variable),
            target=self._infer_node(node.target),
            math_type=expr_type
        )
    
    def _infer_sequence(self, node: SequenceNode) -> SequenceNode:
        """推断序列类型"""
        elements = [self._infer_node(elem) for elem in node.elements]
        
        # 尝试找到公共类型
        common_type = MathType.UNKNOWN
        for elem in elements:
            elem_type = elem.math_type if isinstance(elem, TypedNode) else MathType.UNKNOWN
            common_type = self._common_supertype(common_type, elem_type)
        
        return SequenceNode(elements, math_type=common_type)
    
    def _infer_group(self, node: GroupNode) -> GroupNode:
        """推断分组类型"""
        content = [self._infer_node(item) for item in node.content]
        
        # 如果只有一个元素，继承其类型
        if len(content) == 1:
            item_type = content[0].math_type if isinstance(content[0], TypedNode) else None
            return GroupNode(content, math_type=item_type)
        
        return GroupNode(content)
    
    def _infer_braces(self, node: BracesNode) -> BracesNode:
        """推断括号类型"""
        content = self._infer_node(node.content)
        content_type = content.math_type if isinstance(content, TypedNode) else None
        
        return BracesNode(content, math_type=content_type)
    
    def _infer_equation(self, node: EquationNode) -> EquationNode:
        """推断方程类型（方程返回逻辑类型）"""
        left = self._infer_node(node.left)
        right = self._infer_node(node.right)
        
        return EquationNode(left, right, node.relation, math_type=MathType.LOGICAL)
    
    def _infer_command(self, node: CommandNode) -> CommandNode:
        """推断命令类型"""
        args = [self._infer_node(arg) for arg in node.args]
        return CommandNode(node.name, args)
    
    def _infer_matrix(self, node: MatrixNode) -> MatrixNode:
        """推断矩阵类型"""
        rows = [[self._infer_node(cell) for cell in row] for row in node.rows]
        return MatrixNode(rows, node.matrix_type, math_type=MathType.MATRIX)
    
    def _infer_cases(self, node: CasesNode) -> CasesNode:
        """推断分段函数类型"""
        cases = [
            (self._infer_node(cond), self._infer_node(val))
            for cond, val in node.cases
        ]
        
        # 找到所有值的公共类型
        common_type = MathType.UNKNOWN
        for _, val in cases:
            val_type = val.math_type if isinstance(val, TypedNode) else MathType.UNKNOWN
            common_type = self._common_supertype(common_type, val_type)
        
        return CasesNode(cases, math_type=common_type)
    
    def _infer_set(self, node: SetNode) -> SetNode:
        """推断集合类型"""
        elements = [self._infer_node(e) for e in node.elements]
        return SetNode(elements, node.is_infinite, math_type=MathType.SET)
    
    def _infer_derivative(self, node: DerivativeNode) -> DerivativeNode:
        """推断导数类型"""
        numerator = self._infer_node(node.numerator)
        denominator = self._infer_node(node.denominator)
        
        # 导数保持原函数类型
        return DerivativeNode(
            numerator, denominator, node.order, node.partial,
            math_type=numerator.math_type if isinstance(numerator, TypedNode) else None
        )
    
    def _infer_operator(self, node: OperatorNode) -> OperatorNode:
        """推断通用运算符类型"""
        left = self._infer_node(node.left) if node.left else None
        right = self._infer_node(node.right) if node.right else None
        
        left_type = left.math_type if isinstance(left, TypedNode) else MathType.UNKNOWN
        right_type = right.math_type if isinstance(right, TypedNode) else MathType.UNKNOWN
        
        # 根据运算符推断类型
        if node.operator == '=':
            return OperatorNode(node.operator, left, right, math_type=MathType.LOGICAL)
        
        # 默认返回 ANY 类型
        return OperatorNode(node.operator, left, right, math_type=MathType.ANY)
    
    def _common_supertype(self, type1: MathType, type2: MathType) -> MathType:
        """找到两个类型的公共超类型"""
        if type1 == type2:
            return type1
        
        if type1 == MathType.UNKNOWN:
            return type2
        if type2 == MathType.UNKNOWN:
            return type1
        if type1 == MathType.ANY or type2 == MathType.ANY:
            return MathType.ANY
        
        # 数值类型层次
        numeric_order = [MathType.INTEGER, MathType.RATIONAL, MathType.REAL, MathType.COMPLEX, MathType.NUMBER]
        if type1 in numeric_order and type2 in numeric_order:
            idx1 = numeric_order.index(type1)
            idx2 = numeric_order.index(type2)
            return numeric_order[max(idx1, idx2)]
        
        if is_subtype(type1, MathType.SET) and is_subtype(type2, MathType.SET):
            return MathType.SET
        
        if is_subtype(type1, MathType.FUNCTION) and is_subtype(type2, MathType.FUNCTION):
            return MathType.FUNCTION
        
        return MathType.ANY


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def infer_types(ast: ASTNode, env: Optional[TypeEnvironment] = None) -> ASTNode:
    """推断 AST 中所有节点的类型"""
    engine = TypeInferenceEngine(env)
    return engine.infer(ast)


def infer_latex_types(latex: str, env: Optional[TypeEnvironment] = None) -> ASTNode:
    """解析 LaTeX 并推断类型"""
    from .parser import parse_latex
    ast = parse_latex(latex)
    return infer_types(ast, env)