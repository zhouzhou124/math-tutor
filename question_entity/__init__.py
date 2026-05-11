"""
Question Entity Layer — 数学题知识实体系统

核心原则:
  一题一实体 — QuestionEntity 是系统唯一可信数据单元
  所有答案/解析/错因/学习记录绑定 question_id
  低置信度匹配 → manual_review，不展示错误答案
  缺失比错误安全

架构:
  QuestionEntity (不可变主键)
    ├── OfficialAnswer (fingerprint 匹配)
    ├── OfficialSolution (fingerprint 匹配)
    ├── AlignmentResult (多阶段对齐验证)
    ├── EntityValidation (实体级合法性检查)
    └── BuildTrace (构建过程追踪)
"""

from .schema import (
    QuestionEntity,
    OfficialAnswer,
    OfficialSolution,
    QuestionStem,
    ChoiceOption,
    EntityStatus,
    AlignmentResult,
    EntityValidationResult,
    BuildTrace,
    FailureMode,
    make_question_id,
    content_hash,
    build_entity,
)
from .registry import QuestionRegistry
from .alignment import AlignmentValidator
from .validator import EntityValidator
