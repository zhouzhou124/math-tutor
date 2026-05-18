from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Sequence, Tuple


# ══════════════════════════════════════════════════════════════
# 1. QuestionIntent — 题目意图分类
# ══════════════════════════════════════════════════════════════

class QuestionIntent(Enum):
    """
    数学题目意图分类。
    
    用于指导解题策略选择和推理路径规划。
    """
    
    # 极限相关
    LIMIT_COMPUTATION = auto()        # 求极限值
    LIMIT_EXISTENCE = auto()          # 判断极限是否存在
    LIMIT_COMPARISON = auto()         # 极限大小比较
    
    # 数列相关
    SEQUENCE_LIMIT = auto()           # 数列极限求值
    SEQUENCE_MONOTONICITY = auto()    # 数列单调性判断
    SEQUENCE_BOUNDEDNESS = auto()     # 数列有界性判断
    SEQUENCE_CONVERGENCE = auto()     # 数列收敛性证明
    
    # 函数相关
    FUNCTION_CONTINUITY = auto()      # 函数连续性判断
    FUNCTION_DIFFERENTIABILITY = auto() # 函数可导性判断
    FUNCTION_MONOTONICITY = auto()    # 函数单调性
    FUNCTION_EXTREME = auto()         # 极值/最值问题
    FUNCTION_INTEGRAL = auto()        # 积分计算
    FUNCTION_SERIES = auto()          # 级数收敛性
    
    # 命题判断
    PROPOSITION_JUDGEMENT = auto()    # 命题真假判断
    PROPOSITION_EQUIVALENCE = auto()  # 命题等价性证明
    COUNTEREXAMPLE = auto()           # 构造反例
    
    # 证明题
    PROOF_DIRECT = auto()             # 直接证明
    PROOF_INDUCTION = auto()          # 数学归纳法
    PROOF_CONTRADICTION = auto()      # 反证法
    PROOF_EXISTENCE = auto()          # 存在性证明
    PROOF_UNIQUENESS = auto()         # 唯一性证明
    
    # 方程求解
    EQUATION_SOLVE = auto()           # 解方程
    SYSTEM_SOLVE = auto()             # 解方程组
    INEQUALITY_PROOF = auto()         # 不等式证明
    OPTIMIZATION = auto()             # 最优化问题
    
    # 矩阵相关
    MATRIX_RANK = auto()              # 矩阵秩
    MATRIX_DETERMINANT = auto()       # 行列式计算
    MATRIX_INVERSE = auto()           # 矩阵求逆
    MATRIX_EIGEN = auto()             # 特征值/特征向量
    
    # 综合题
    COMPREHENSIVE = auto()            # 综合题（多知识点）
    
    # 其他
    UNKNOWN = auto()                  # 未知类型
    
    @property
    def requires_proof(self) -> bool:
        """是否需要证明（而非计算）"""
        return self in {
            QuestionIntent.PROOF_DIRECT,
            QuestionIntent.PROOF_INDUCTION,
            QuestionIntent.PROOF_CONTRADICTION,
            QuestionIntent.PROOF_EXISTENCE,
            QuestionIntent.PROOF_UNIQUENESS,
            QuestionIntent.PROPOSITION_JUDGEMENT,
            QuestionIntent.PROPOSITION_EQUIVALENCE,
            QuestionIntent.COUNTEREXAMPLE,
            QuestionIntent.FUNCTION_CONTINUITY,
            QuestionIntent.FUNCTION_DIFFERENTIABILITY,
            QuestionIntent.SEQUENCE_CONVERGENCE,
            QuestionIntent.SEQUENCE_MONOTONICITY,
            QuestionIntent.SEQUENCE_BOUNDEDNESS,
            QuestionIntent.LIMIT_EXISTENCE,
            QuestionIntent.INEQUALITY_PROOF,
        }
    
    @property
    def requires_computation(self) -> bool:
        """是否需要计算（而非证明）"""
        return self in {
            QuestionIntent.LIMIT_COMPUTATION,
            QuestionIntent.SEQUENCE_LIMIT,
            QuestionIntent.FUNCTION_INTEGRAL,
            QuestionIntent.EQUATION_SOLVE,
            QuestionIntent.SYSTEM_SOLVE,
            QuestionIntent.MATRIX_DETERMINANT,
            QuestionIntent.MATRIX_INVERSE,
            QuestionIntent.MATRIX_EIGEN,
            QuestionIntent.OPTIMIZATION,
        }


# ══════════════════════════════════════════════════════════════
# 2. TopicTag — 知识点标签
# ══════════════════════════════════════════════════════════════

class TopicTag(Enum):
    """
    数学知识点标签。
    
    用于识别题目涉及的核心数学概念。
    """
    
    # 分析基础
    LIMIT = auto()                    # 极限
    CONTINUITY = auto()               # 连续性
    DIFFERENTIATION = auto()          # 微分
    INTEGRATION = auto()              # 积分
    SERIES = auto()                   # 级数
    
    # 数列
    SEQUENCE = auto()                 # 数列
    MONOTONICITY = auto()             # 单调性
    BOUNDEDNESS = auto()              # 有界性
    CONVERGENCE = auto()              # 收敛性
    RECURRENCE = auto()               # 递推关系
    
    # 函数
    FUNCTION = auto()                 # 函数
    COMPOSITE_FUNCTION = auto()       # 复合函数
    INVERSE_FUNCTION = auto()         # 反函数
    TRIGONOMETRIC = auto()            # 三角函数
    
    # 证明方法
    DIRECT_PROOF = auto()             # 直接证明
    INDUCTION = auto()                # 数学归纳法
    CONTRADICTION = auto()            # 反证法
    CONTRAPOSITIVE = auto()           # 逆否命题
    
    # 逻辑
    PROPOSITION = auto()              # 命题
    LOGICAL_IMPLICATION = auto()      # 逻辑蕴含
    NECESSARY_SUFFICIENT = auto()     # 充要条件
    
    # 矩阵
    MATRIX = auto()                   # 矩阵
    RANK = auto()                     # 秩
    DETERMINANT = auto()              # 行列式
    EIGENVALUE = auto()               # 特征值
    
    # 优化
    OPTIMIZATION = auto()             # 最优化
    EXTREME_VALUE = auto()            # 极值
    
    # 综合
    COMPREHENSIVE = auto()            # 综合应用


# ══════════════════════════════════════════════════════════════
# 3. ObjectType — 问题对象类型
# ══════════════════════════════════════════════════════════════

class ObjectType(Enum):
    """
    问题中涉及的数学对象类型。
    """
    
    SEQUENCE = auto()                 # 数列
    FUNCTION = auto()                 # 函数
    MATRIX = auto()                   # 矩阵
    SET = auto()                      # 集合
    NUMBER = auto()                   # 数
    EQUATION = auto()                 # 方程
    INEQUALITY = auto()               # 不等式
    PROPOSITION = auto()              # 命题
    THEOREM = auto()                  # 定理
    DEFINITION = auto()               # 定义


# ══════════════════════════════════════════════════════════════
# 4. ReasoningMode — 推理模式
# ══════════════════════════════════════════════════════════════

class ReasoningMode(Enum):
    """
    推荐的推理模式。
    """
    
    DIRECT_CALCULATION = auto()       # 直接计算
    DEFINITION_APPLICATION = auto()   # 定义应用
    THEOREM_APPLICATION = auto()      # 定理应用
    REDUCTIO_AD_ABSURDUM = auto()     # 反证法
    INDUCTION = auto()                # 数学归纳
    CONSTRUCTION = auto()             # 构造法
    CONTRADICTION = auto()            # 矛盾分析法
    CASE_ANALYSIS = auto()            # 分类讨论
    MONOTONICITY_ANALYSIS = auto()    # 单调性分析
    CONTINUITY_ANALYSIS = auto()      # 连续性分析
    INVERTIBILITY_ANALYSIS = auto()   # 可逆性分析
    LIMIT_ANALYSIS = auto()           # 极限分析
    GRAPHICAL_ANALYSIS = auto()       # 图像分析


# ══════════════════════════════════════════════════════════════
# 5. Constraint — 约束条件
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Constraint:
    """
    约束条件表示。
    """
    
    expression: str
    type: str = "general"  # domain, inequality, equality, condition
    
    def to_dict(self) -> dict:
        return {
            "expression": self.expression,
            "type": self.type,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> Constraint:
        return cls(
            expression=d.get("expression", ""),
            type=d.get("type", "general"),
        )


# ══════════════════════════════════════════════════════════════
# 6. Proposition — 命题结构
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Proposition:
    """
    命题结构 — 用于命题判断题的语义解析。
    """
    
    statement: str
    components: tuple[str, ...] = ()
    logical_structure: str = ""  # "A→B", "A∧B", "A∨B", etc.
    is_compound: bool = False
    
    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "components": list(self.components),
            "logical_structure": self.logical_structure,
            "is_compound": self.is_compound,
        }


# ══════════════════════════════════════════════════════════════
# 7. ProblemSchema — 问题语义结构
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProblemSchema:
    """
    问题语义结构 — 对数学题目的深层语义理解。
    
    这是连接"题目文本"和"解题策略"的关键桥梁。
    """
    
    question_type: QuestionIntent = QuestionIntent.UNKNOWN
    targets: tuple[str, ...] = ()
    objects: tuple[tuple[str, ObjectType], ...] = ()
    constraints: tuple[str, ...] = ()
    reasoning_mode: ReasoningMode = ReasoningMode.DIRECT_CALCULATION
    topics: tuple[TopicTag, ...] = ()
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "question_type": self.question_type.name,
            "targets": list(self.targets),
            "objects": [(name, obj_type.name) for name, obj_type in self.objects],
            "constraints": list(self.constraints),
            "reasoning_mode": self.reasoning_mode.name,
            "topics": [topic.name for topic in self.topics],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> ProblemSchema:
        return cls(
            question_type=QuestionIntent[d.get("question_type", "UNKNOWN")],
            targets=tuple(d.get("targets", [])),
            objects=tuple(
                (name, ObjectType[obj_type])
                for name, obj_type in d.get("objects", [])
            ),
            constraints=tuple(d.get("constraints", [])),
            reasoning_mode=ReasoningMode[d.get("reasoning_mode", "DIRECT_CALCULATION")],
            topics=tuple(TopicTag[topic] for topic in d.get("topics", [])),
            confidence=d.get("confidence", 0.0),
            metadata=d.get("metadata", {}),
        )
