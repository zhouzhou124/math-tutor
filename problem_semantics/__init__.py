"""
Problem Semantics Module

核心组件：
  - QuestionIntent: 题目意图分类枚举
  - TopicTag: 知识点标签枚举
  - ObjectType: 问题对象类型枚举
  - ReasoningMode: 推理模式枚举
  - ProblemSchema: 问题语义结构
  - ProblemSemanticParser: 问题语义解析器
  - parse_problem: 便捷解析函数
"""

# 导入语义类型
from .semantic_types import (
    QuestionIntent,
    TopicTag,
    ObjectType,
    ReasoningMode,
    Constraint,
    Proposition,
    ProblemSchema,
)

# 导入解析器
from .parser import ProblemSemanticParser, parse_problem

# 导出所有公共接口
__all__ = [
    'QuestionIntent',
    'TopicTag',
    'ObjectType',
    'ReasoningMode',
    'Constraint',
    'Proposition',
    'ProblemSchema',
    'ProblemSemanticParser',
    'parse_problem',
]
