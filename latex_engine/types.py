"""Math Type System - 数学类型系统

定义数学类型枚举、类型操作和类型检查。
这是整个 CAS 的核心基础。
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Union, Any
from dataclasses import dataclass


# ═══════════════════════════════════════════════
# MathType 枚举 - 数学类型系统的核心
# ═══════════════════════════════════════════════

class MathType(Enum):
    """数学类型枚举"""
    
    # 基础标量类型
    REAL = auto()           # 实数
    INTEGER = auto()        # 整数
    COMPLEX = auto()        # 复数
    RATIONAL = auto()       # 有理数
    
    # 集合类型
    SET = auto()            # 集合
    FINITE_SET = auto()     # 有限集合
    INFINITE_SET = auto()   # 无限集合
    
    # 代数结构
    GROUP = auto()          # 群
    RING = auto()           # 环
    FIELD = auto()          # 域
    VECTOR_SPACE = auto()   # 向量空间
    
    # 线性代数类型
    VECTOR = auto()         # 向量
    MATRIX = auto()         # 矩阵
    
    # 函数类型
    FUNCTION = auto()       # 函数
    POLYNOMIAL = auto()     # 多项式
    EXPONENTIAL = auto()    # 指数函数
    TRIGONOMETRIC = auto()  # 三角函数
    LOGARITHMIC = auto()    # 对数函数
    
    # 序列和级数
    SEQUENCE = auto()       # 序列
    SERIES = auto()         # 级数
    
    # 逻辑类型
    LOGICAL = auto()        # 逻辑值 (True/False)
    PROPOSITION = auto()    # 命题
    
    # 抽象类型
    ANY = auto()            # 任意类型
    UNKNOWN = auto()        # 未知类型
    ERROR = auto()          # 类型错误
    
    # 特殊类型
    VOID = auto()           # 空类型
    NUMBER = auto()         # 数值类型(通用)


# ═══════════════════════════════════════════════
# 类型关系和操作
# ═══════════════════════════════════════════════

def is_subtype(subtype: MathType, supertype: MathType) -> bool:
    """检查一个类型是否是另一个类型的子类型"""
    subtype_hierarchy = {
        MathType.INTEGER: [MathType.REAL, MathType.RATIONAL, MathType.NUMBER],
        MathType.RATIONAL: [MathType.REAL, MathType.NUMBER],
        MathType.REAL: [MathType.COMPLEX, MathType.NUMBER],
        MathType.COMPLEX: [MathType.NUMBER],
        MathType.FINITE_SET: [MathType.SET],
        MathType.INFINITE_SET: [MathType.SET],
        MathType.POLYNOMIAL: [MathType.FUNCTION],
        MathType.EXPONENTIAL: [MathType.FUNCTION],
        MathType.TRIGONOMETRIC: [MathType.FUNCTION],
        MathType.LOGARITHMIC: [MathType.FUNCTION],
        MathType.GROUP: [MathType.SET],
        MathType.RING: [MathType.GROUP],
        MathType.FIELD: [MathType.RING],
        MathType.VECTOR_SPACE: [MathType.FIELD],
        MathType.VECTOR: [MathType.VECTOR_SPACE],
        MathType.MATRIX: [MathType.VECTOR_SPACE],
        MathType.SEQUENCE: [MathType.SERIES],
    }
    
    if subtype == supertype:
        return True
    
    return supertype in subtype_hierarchy.get(subtype, [])


def common_supertype(type1: MathType, type2: MathType) -> MathType:
    """找到两个类型的最小公共超类型"""
    if type1 == type2:
        return type1
    
    # 特殊处理
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
    
    # 集合类型
    if is_subtype(type1, MathType.SET) and is_subtype(type2, MathType.SET):
        return MathType.SET
    
    # 函数类型
    if is_subtype(type1, MathType.FUNCTION) and is_subtype(type2, MathType.FUNCTION):
        return MathType.FUNCTION
    
    # 默认返回 ANY
    return MathType.ANY


# ═══════════════════════════════════════════════
# 类型约束和规则
# ═══════════════════════════════════════════════

class TypeRule:
    """类型规则基类"""
    
    def apply(self, *args: MathType) -> Optional[MathType]:
        """应用类型规则"""
        raise NotImplementedError


class BinaryOpTypeRule(TypeRule):
    """二元运算类型规则"""
    
    def __init__(self, op: str):
        self.op = op
        self.rules: List[Dict[str, Any]] = []
    
    def add_rule(self, left_type: MathType, right_type: MathType, result_type: MathType):
        """添加类型规则"""
        self.rules.append({
            'left': left_type,
            'right': right_type,
            'result': result_type
        })
    
    def apply(self, left_type: MathType, right_type: MathType) -> Optional[MathType]:
        """应用规则"""
        for rule in self.rules:
            if rule['left'] == left_type and rule['right'] == right_type:
                return rule['result']
            
            # 子类型匹配
            if is_subtype(left_type, rule['left']) and is_subtype(right_type, rule['right']):
                return rule['result']
        
        # 如果任一类型未知，返回未知
        if left_type == MathType.UNKNOWN or right_type == MathType.UNKNOWN:
            return MathType.UNKNOWN
        
        return None


# ═══════════════════════════════════════════════
# 预定义类型规则
# ═══════════════════════════════════════════════

class TypeRules:
    """预定义类型规则集合"""
    
    @staticmethod
    def get_add_rules() -> BinaryOpTypeRule:
        """加法类型规则"""
        rule = BinaryOpTypeRule('+')
        rule.add_rule(MathType.REAL, MathType.REAL, MathType.REAL)
        rule.add_rule(MathType.INTEGER, MathType.INTEGER, MathType.INTEGER)
        rule.add_rule(MathType.COMPLEX, MathType.COMPLEX, MathType.COMPLEX)
        rule.add_rule(MathType.RATIONAL, MathType.RATIONAL, MathType.RATIONAL)
        rule.add_rule(MathType.VECTOR, MathType.VECTOR, MathType.VECTOR)
        rule.add_rule(MathType.MATRIX, MathType.MATRIX, MathType.MATRIX)
        rule.add_rule(MathType.SET, MathType.SET, MathType.SET)
        return rule
    
    @staticmethod
    def get_subtract_rules() -> BinaryOpTypeRule:
        """减法类型规则"""
        rule = BinaryOpTypeRule('-')
        rule.add_rule(MathType.REAL, MathType.REAL, MathType.REAL)
        rule.add_rule(MathType.INTEGER, MathType.INTEGER, MathType.INTEGER)
        rule.add_rule(MathType.COMPLEX, MathType.COMPLEX, MathType.COMPLEX)
        rule.add_rule(MathType.RATIONAL, MathType.RATIONAL, MathType.RATIONAL)
        rule.add_rule(MathType.VECTOR, MathType.VECTOR, MathType.VECTOR)
        rule.add_rule(MathType.MATRIX, MathType.MATRIX, MathType.MATRIX)
        return rule
    
    @staticmethod
    def get_multiply_rules() -> BinaryOpTypeRule:
        """乘法类型规则"""
        rule = BinaryOpTypeRule('*')
        rule.add_rule(MathType.REAL, MathType.REAL, MathType.REAL)
        rule.add_rule(MathType.INTEGER, MathType.INTEGER, MathType.INTEGER)
        rule.add_rule(MathType.COMPLEX, MathType.COMPLEX, MathType.COMPLEX)
        rule.add_rule(MathType.RATIONAL, MathType.RATIONAL, MathType.RATIONAL)
        rule.add_rule(MathType.REAL, MathType.VECTOR, MathType.VECTOR)
        rule.add_rule(MathType.VECTOR, MathType.REAL, MathType.VECTOR)
        rule.add_rule(MathType.MATRIX, MathType.MATRIX, MathType.MATRIX)
        rule.add_rule(MathType.MATRIX, MathType.VECTOR, MathType.VECTOR)
        rule.add_rule(MathType.REAL, MathType.MATRIX, MathType.MATRIX)
        rule.add_rule(MathType.MATRIX, MathType.REAL, MathType.MATRIX)
        return rule
    
    @staticmethod
    def get_divide_rules() -> BinaryOpTypeRule:
        """除法类型规则"""
        rule = BinaryOpTypeRule('/')
        rule.add_rule(MathType.REAL, MathType.REAL, MathType.REAL)
        rule.add_rule(MathType.INTEGER, MathType.INTEGER, MathType.RATIONAL)
        rule.add_rule(MathType.COMPLEX, MathType.COMPLEX, MathType.COMPLEX)
        rule.add_rule(MathType.RATIONAL, MathType.RATIONAL, MathType.RATIONAL)
        rule.add_rule(MathType.VECTOR, MathType.REAL, MathType.VECTOR)
        rule.add_rule(MathType.MATRIX, MathType.REAL, MathType.MATRIX)
        return rule
    
    @staticmethod
    def get_power_rules() -> BinaryOpTypeRule:
        """幂运算类型规则"""
        rule = BinaryOpTypeRule('^')
        rule.add_rule(MathType.REAL, MathType.REAL, MathType.REAL)
        rule.add_rule(MathType.INTEGER, MathType.INTEGER, MathType.INTEGER)
        rule.add_rule(MathType.COMPLEX, MathType.INTEGER, MathType.COMPLEX)
        rule.add_rule(MathType.MATRIX, MathType.INTEGER, MathType.MATRIX)
        return rule
    
    @staticmethod
    def get_unary_rules() -> Dict[str, Dict[MathType, MathType]]:
        """一元运算类型规则"""
        return {
            '-': {
                MathType.REAL: MathType.REAL,
                MathType.INTEGER: MathType.INTEGER,
                MathType.COMPLEX: MathType.COMPLEX,
                MathType.RATIONAL: MathType.RATIONAL,
                MathType.VECTOR: MathType.VECTOR,
                MathType.MATRIX: MathType.MATRIX,
            },
            '+': {
                MathType.REAL: MathType.REAL,
                MathType.INTEGER: MathType.INTEGER,
                MathType.COMPLEX: MathType.COMPLEX,
                MathType.RATIONAL: MathType.RATIONAL,
                MathType.VECTOR: MathType.VECTOR,
                MathType.MATRIX: MathType.MATRIX,
            },
        }


# ═══════════════════════════════════════════════
# 类型错误
# ═══════════════════════════════════════════════

class TypeError(Exception):
    """类型错误异常"""
    
    def __init__(self, message: str, expr_type: Optional[MathType] = None, expected_type: Optional[MathType] = None):
        super().__init__(message)
        self.expr_type = expr_type
        self.expected_type = expected_type


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def type_to_string(math_type: MathType) -> str:
    """将类型转换为可读字符串"""
    type_names = {
        MathType.REAL: 'Real',
        MathType.INTEGER: 'Integer',
        MathType.COMPLEX: 'Complex',
        MathType.RATIONAL: 'Rational',
        MathType.SET: 'Set',
        MathType.FINITE_SET: 'FiniteSet',
        MathType.INFINITE_SET: 'InfiniteSet',
        MathType.GROUP: 'Group',
        MathType.RING: 'Ring',
        MathType.FIELD: 'Field',
        MathType.VECTOR_SPACE: 'VectorSpace',
        MathType.VECTOR: 'Vector',
        MathType.MATRIX: 'Matrix',
        MathType.FUNCTION: 'Function',
        MathType.POLYNOMIAL: 'Polynomial',
        MathType.EXPONENTIAL: 'Exponential',
        MathType.TRIGONOMETRIC: 'Trigonometric',
        MathType.LOGARITHMIC: 'Logarithmic',
        MathType.SEQUENCE: 'Sequence',
        MathType.SERIES: 'Series',
        MathType.LOGICAL: 'Logical',
        MathType.PROPOSITION: 'Proposition',
        MathType.ANY: 'Any',
        MathType.UNKNOWN: 'Unknown',
        MathType.ERROR: 'Error',
        MathType.VOID: 'Void',
        MathType.NUMBER: 'Number',
    }
    return type_names.get(math_type, str(math_type))