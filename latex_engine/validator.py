"""AST Validator - AST 验证器

验证 AST 的结构正确性和类型一致性。
"""

from typing import List, Dict, Optional, Any
from .ast import *
from .types import MathType


class ASTValidationError(Exception):
    """AST 验证错误"""
    pass


class ASTValidator:
    """AST 验证器"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, ast: ASTNode) -> bool:
        """验证 AST 是否有效"""
        self.errors = []
        self.warnings = []
        
        self._validate_node(ast)
        
        return len(self.errors) == 0
    
    def _validate_node(self, node: ASTNode, path: str = "") -> Optional[MathType]:
        """递归验证节点"""
        node_type = type(node).__name__
        
        if node is None:
            self.errors.append(f"{path}: Node is None")
            return None
        
        # 检查节点类型是否合法
        if not isinstance(node, ASTNode):
            self.errors.append(f"{path}: Not a valid ASTNode: {type(node).__name__}")
            return None
        
        # 根据节点类型进行特定验证
        if isinstance(node, NumberNode):
            return self._validate_number(node, path)
        elif isinstance(node, SymbolNode):
            return self._validate_symbol(node, path)
        elif isinstance(node, AddNode):
            return self._validate_binary_op(node, path, "Add")
        elif isinstance(node, SubtractNode):
            return self._validate_binary_op(node, path, "Subtract")
        elif isinstance(node, MultiplyNode):
            return self._validate_binary_op(node, path, "Multiply")
        elif isinstance(node, DivideNode):
            return self._validate_divide(node, path)
        elif isinstance(node, PowerNode):
            return self._validate_power(node, path)
        elif isinstance(node, NegateNode):
            return self._validate_unary_op(node, path, "Negate")
        elif isinstance(node, FunctionNode):
            return self._validate_function(node, path)
        elif isinstance(node, GroupNode):
            return self._validate_group(node, path)
        elif isinstance(node, SetNode):
            return self._validate_set(node, path)
        elif isinstance(node, MatrixNode):
            return self._validate_matrix(node, path)
        elif isinstance(node, FractionNode):
            return self._validate_fraction(node, path)
        elif isinstance(node, SqrtNode):
            return self._validate_sqrt(node, path)
        elif isinstance(node, EquationNode):
            return self._validate_equation(node, path)
        elif isinstance(node, CommandNode):
            return self._validate_command(node, path)
        elif isinstance(node, SequenceNode):
            return self._validate_sequence(node, path)
        elif isinstance(node, CasesNode):
            return self._validate_cases(node, path)
        elif isinstance(node, LimitNode):
            return self._validate_limit(node, path)
        elif isinstance(node, SumNode):
            return self._validate_sum(node, path)
        elif isinstance(node, ProductNode):
            return self._validate_product(node, path)
        elif isinstance(node, IntegralNode):
            return self._validate_integral(node, path)
        elif isinstance(node, DerivativeNode):
            return self._validate_derivative(node, path)
        elif isinstance(node, SubscriptNode):
            return self._validate_subscript(node, path)
        elif isinstance(node, SuperscriptNode):
            return self._validate_superscript(node, path)
        elif isinstance(node, BracesNode):
            return self._validate_braces(node, path)
        elif isinstance(node, TextNode):
            return None  # 文本节点无需类型检查
        elif isinstance(node, OperatorNode):
            return self._validate_operator(node, path)
        else:
            self.warnings.append(f"{path}: Unknown node type: {node_type}")
            return None
    
    def _validate_number(self, node: NumberNode, path: str) -> MathType:
        """验证数字节点"""
        if node.value is None:
            self.errors.append(f"{path}: NumberNode has no value")
        
        inferred_type = node.math_type
        if inferred_type is None:
            # 根据值推断类型
            if isinstance(node.value, int):
                inferred_type = MathType.INTEGER
            elif isinstance(node.value, float):
                inferred_type = MathType.REAL
            elif isinstance(node.value, str):
                if '.' in node.value:
                    inferred_type = MathType.REAL
                else:
                    inferred_type = MathType.INTEGER
        
        return inferred_type
    
    def _validate_symbol(self, node: SymbolNode, path: str) -> MathType:
        """验证符号节点"""
        if not node.name or not isinstance(node.name, str):
            self.errors.append(f"{path}: SymbolNode has invalid name: {node.name}")
        
        # 默认假设为实数类型
        return node.math_type or MathType.REAL
    
    def _validate_binary_op(self, node: Any, path: str, op_name: str) -> MathType:
        """验证二元操作节点"""
        if not hasattr(node, 'left') or node.left is None:
            self.errors.append(f"{path}: {op_name}Node has no left operand")
        
        if not hasattr(node, 'right') or node.right is None:
            self.errors.append(f"{path}: {op_name}Node has no right operand")
        
        left_type = self._validate_node(node.left, f"{path}.left")
        right_type = self._validate_node(node.right, f"{path}.right")
        
        # 检查类型兼容性
        if left_type and right_type:
            if left_type != right_type:
                self.warnings.append(
                    f"{path}: Type mismatch in {op_name}: {left_type} vs {right_type}"
                )
        
        return node.math_type or left_type
    
    def _validate_divide(self, node: DivideNode, path: str) -> MathType:
        """验证除法节点"""
        if node.numerator is None:
            self.errors.append(f"{path}: DivideNode has no numerator")
        
        if node.denominator is None:
            self.errors.append(f"{path}: DivideNode has no denominator")
        
        num_type = self._validate_node(node.numerator, f"{path}.numerator")
        den_type = self._validate_node(node.denominator, f"{path}.denominator")
        
        # 检查分母是否可能为零
        if isinstance(node.denominator, NumberNode):
            if node.denominator.value == 0:
                self.errors.append(f"{path}: Division by zero")
        
        return node.math_type or num_type
    
    def _validate_power(self, node: PowerNode, path: str) -> MathType:
        """验证幂运算节点"""
        if node.base is None:
            self.errors.append(f"{path}: PowerNode has no base")
        
        if node.exponent is None:
            self.errors.append(f"{path}: PowerNode has no exponent")
        
        base_type = self._validate_node(node.base, f"{path}.base")
        exp_type = self._validate_node(node.exponent, f"{path}.exponent")
        
        return node.math_type or base_type
    
    def _validate_unary_op(self, node: Any, path: str, op_name: str) -> MathType:
        """验证一元操作节点"""
        if not hasattr(node, 'operand') or node.operand is None:
            self.errors.append(f"{path}: {op_name}Node has no operand")
        
        operand_type = self._validate_node(node.operand, f"{path}.operand")
        
        return node.math_type or operand_type
    
    def _validate_function(self, node: FunctionNode, path: str) -> MathType:
        """验证函数调用节点"""
        if not node.name:
            self.errors.append(f"{path}: FunctionNode has no name")
        
        if node.arguments is None:
            self.errors.append(f"{path}: FunctionNode has no arguments list")
        
        arg_types = []
        for i, arg in enumerate(node.arguments):
            arg_type = self._validate_node(arg, f"{path}.args[{i}]")
            arg_types.append(arg_type)
        
        # 根据函数名检查参数数量
        expected_args = {
            'sin': 1, 'cos': 1, 'tan': 1,
            'sinh': 1, 'cosh': 1, 'tanh': 1,
            'asin': 1, 'acos': 1, 'atan': 1,
            'exp': 1, 'log': 1, 'ln': 1,
            'sqrt': 1, 'abs': 1,
            'lim': 3,  # lim(f, x, a)
            'sum': 3,  # sum(f, i, n)
            'prod': 3, # prod(f, i, n)
            'int': 3,  # int(f, x, a, b) - 可能是3或4个参数
        }
        
        func_name = node.name.lower()
        if func_name in expected_args:
            if len(node.arguments) != expected_args[func_name]:
                self.warnings.append(
                    f"{path}: Function {func_name} expects {expected_args[func_name]} arguments, got {len(node.arguments)}"
                )
        
        # 数学函数通常返回实数
        return node.math_type or MathType.REAL
    
    def _validate_group(self, node: GroupNode, path: str) -> MathType:
        """验证分组节点"""
        if node.content is None or len(node.content) == 0:
            self.errors.append(f"{path}: GroupNode has no content")
        
        inner_types = []
        for i, item in enumerate(node.content):
            inner_type = self._validate_node(item, f"{path}.content[{i}]")
            inner_types.append(inner_type)
        
        # 如果只有一个元素，继承其类型
        if len(inner_types) == 1:
            return inner_types[0]
        
        return None
    
    def _validate_set(self, node: SetNode, path: str) -> MathType:
        """验证集合节点"""
        if node.elements is None:
            self.errors.append(f"{path}: SetNode has no elements")
        
        for i, elem in enumerate(node.elements):
            self._validate_node(elem, f"{path}.elements[{i}]")
        
        return MathType.SET
    
    def _validate_matrix(self, node: MatrixNode, path: str) -> MathType:
        """验证矩阵节点"""
        if node.rows is None or len(node.rows) == 0:
            self.errors.append(f"{path}: MatrixNode has no rows")
        
        row_lengths = []
        for i, row in enumerate(node.rows):
            if row is None:
                self.errors.append(f"{path}: Matrix row {i} is None")
                continue
            
            row_lengths.append(len(row))
            for j, cell in enumerate(row):
                self._validate_node(cell, f"{path}.rows[{i}][{j}]")
        
        # 检查所有行是否长度相同
        if len(set(row_lengths)) > 1:
            self.errors.append(f"{path}: Matrix has inconsistent row lengths: {row_lengths}")
        
        return MathType.MATRIX
    
    def _validate_fraction(self, node: FractionNode, path: str) -> MathType:
        """验证分数节点"""
        if node.numerator is None:
            self.errors.append(f"{path}: FractionNode has no numerator")
        
        if node.denominator is None:
            self.errors.append(f"{path}: FractionNode has no denominator")
        
        self._validate_node(node.numerator, f"{path}.numerator")
        self._validate_node(node.denominator, f"{path}.denominator")
        
        return node.math_type or MathType.REAL
    
    def _validate_sqrt(self, node: SqrtNode, path: str) -> MathType:
        """验证根号节点"""
        if node.radicand is None:
            self.errors.append(f"{path}: SqrtNode has no radicand")
        
        self._validate_node(node.radicand, f"{path}.radicand")
        
        return node.math_type or MathType.REAL
    
    def _validate_equation(self, node: EquationNode, path: str) -> MathType:
        """验证等式节点"""
        if node.left is None:
            self.errors.append(f"{path}: EquationNode has no left side")
        
        if node.right is None:
            self.errors.append(f"{path}: EquationNode has no right side")
        
        if node.relation is None:
            self.errors.append(f"{path}: EquationNode has no relation operator")
        
        self._validate_node(node.left, f"{path}.left")
        self._validate_node(node.right, f"{path}.right")
        
        return MathType.LOGICAL
    
    def _validate_command(self, node: CommandNode, path: str) -> None:
        """验证命令节点"""
        if not node.name:
            self.errors.append(f"{path}: CommandNode has no name")
        
        for i, arg in enumerate(node.args):
            self._validate_node(arg, f"{path}.args[{i}]")
        
        return None
    
    def _validate_sequence(self, node: SequenceNode, path: str) -> MathType:
        """验证序列节点"""
        if node.elements is None:
            self.errors.append(f"{path}: SequenceNode has no elements")
        
        for i, elem in enumerate(node.elements):
            self._validate_node(elem, f"{path}.elements[{i}]")
        
        return MathType.SEQUENCE
    
    def _validate_cases(self, node: CasesNode, path: str) -> MathType:
        """验证分段函数节点"""
        if node.cases is None or len(node.cases) == 0:
            self.errors.append(f"{path}: CasesNode has no cases")
        
        for i, (cond, val) in enumerate(node.cases):
            self._validate_node(cond, f"{path}.cases[{i}].cond")
            self._validate_node(val, f"{path}.cases[{i}].val")
        
        return node.math_type or MathType.FUNCTION
    
    def _validate_limit(self, node: LimitNode, path: str) -> MathType:
        """验证极限节点"""
        if node.expression is None:
            self.errors.append(f"{path}: LimitNode has no expression")
        
        if node.variable is None:
            self.errors.append(f"{path}: LimitNode has no variable")
        
        if node.target is None:
            self.errors.append(f"{path}: LimitNode has no target")
        
        self._validate_node(node.expression, f"{path}.expression")
        self._validate_node(node.variable, f"{path}.variable")
        self._validate_node(node.target, f"{path}.target")
        
        return node.math_type or MathType.REAL
    
    def _validate_sum(self, node: SumNode, path: str) -> MathType:
        """验证求和节点"""
        if node.term is None:
            self.errors.append(f"{path}: SumNode has no term")
        
        self._validate_node(node.term, f"{path}.term")
        if node.index:
            self._validate_node(node.index, f"{path}.index")
        if node.lower_limit:
            self._validate_node(node.lower_limit, f"{path}.lower_limit")
        if node.upper_limit:
            self._validate_node(node.upper_limit, f"{path}.upper_limit")
        
        return node.math_type or MathType.REAL
    
    def _validate_product(self, node: ProductNode, path: str) -> MathType:
        """验证乘积节点"""
        if node.term is None:
            self.errors.append(f"{path}: ProductNode has no term")
        
        self._validate_node(node.term, f"{path}.term")
        if node.index:
            self._validate_node(node.index, f"{path}.index")
        if node.lower_limit:
            self._validate_node(node.lower_limit, f"{path}.lower_limit")
        if node.upper_limit:
            self._validate_node(node.upper_limit, f"{path}.upper_limit")
        
        return node.math_type or MathType.REAL
    
    def _validate_integral(self, node: IntegralNode, path: str) -> MathType:
        """验证积分节点"""
        if node.integrand is None:
            self.errors.append(f"{path}: IntegralNode has no integrand")
        
        self._validate_node(node.integrand, f"{path}.integrand")
        if node.variable:
            self._validate_node(node.variable, f"{path}.variable")
        if node.lower_limit:
            self._validate_node(node.lower_limit, f"{path}.lower_limit")
        if node.upper_limit:
            self._validate_node(node.upper_limit, f"{path}.upper_limit")
        
        return node.math_type or MathType.REAL
    
    def _validate_derivative(self, node: DerivativeNode, path: str) -> MathType:
        """验证导数节点"""
        if node.numerator is None:
            self.errors.append(f"{path}: DerivativeNode has no numerator")
        
        if node.denominator is None:
            self.errors.append(f"{path}: DerivativeNode has no denominator")
        
        self._validate_node(node.numerator, f"{path}.numerator")
        self._validate_node(node.denominator, f"{path}.denominator")
        
        return node.math_type
    
    def _validate_subscript(self, node: SubscriptNode, path: str) -> MathType:
        """验证下标节点"""
        if node.base is None:
            self.errors.append(f"{path}: SubscriptNode has no base")
        
        if node.subscript is None:
            self.errors.append(f"{path}: SubscriptNode has no subscript")
        
        base_type = self._validate_node(node.base, f"{path}.base")
        self._validate_node(node.subscript, f"{path}.subscript")
        
        return base_type
    
    def _validate_superscript(self, node: SuperscriptNode, path: str) -> MathType:
        """验证上标节点"""
        if node.base is None:
            self.errors.append(f"{path}: SuperscriptNode has no base")
        
        if node.superscript is None:
            self.errors.append(f"{path}: SuperscriptNode has no superscript")
        
        base_type = self._validate_node(node.base, f"{path}.base")
        self._validate_node(node.superscript, f"{path}.superscript")
        
        return base_type
    
    def _validate_braces(self, node: BracesNode, path: str) -> MathType:
        """验证花括号节点"""
        if node.content is None:
            self.errors.append(f"{path}: BracesNode has no content")
        
        return self._validate_node(node.content, f"{path}.content")
    
    def _validate_operator(self, node: OperatorNode, path: str) -> MathType:
        """验证通用操作符节点"""
        if not node.operator:
            self.errors.append(f"{path}: OperatorNode has no operator")
        
        if node.left:
            self._validate_node(node.left, f"{path}.left")
        if node.right:
            self._validate_node(node.right, f"{path}.right")
        
        if node.operator in ['=', '<', '>', '<=', '>=', '!=']:
            return MathType.LOGICAL
        
        return node.math_type


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def validate_ast(ast: ASTNode) -> bool:
    """验证 AST 是否有效"""
    validator = ASTValidator()
    is_valid = validator.validate(ast)
    
    if validator.errors:
        print("AST Validation Errors:")
        for error in validator.errors:
            print(f"  - {error}")
    
    if validator.warnings:
        print("AST Validation Warnings:")
        for warning in validator.warnings:
            print(f"  - {warning}")
    
    return is_valid