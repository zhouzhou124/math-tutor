"""Presentation Layer - ViewModel 层

职责：将 Domain Model 转换为 Renderer 可消费的 ViewModel。
Renderer 不直接接触 Domain，只消费 ViewModel。

数据流：Domain → ViewModel Mapper → Renderer → HTML
"""

from .viewmodels import (
    StepCardViewModel,
    ErrorViewModel,
    DiagnosisViewModel,
    ScoreViewModel,
    FormulaViewModel,
    DiffViewModel,
    ChainViewModel,
    QuestionViewModel,
    DashboardViewModel,
)
from .mappers import (
    ReasoningStepMapper,
    ErrorRecordMapper,
    DiagnosisMapper,
    GradingMapper,
    QuestionMapper,
    DashboardMapper,
)

__all__ = [
    "StepCardViewModel",
    "ErrorViewModel",
    "DiagnosisViewModel",
    "ScoreViewModel",
    "FormulaViewModel",
    "DiffViewModel",
    "ChainViewModel",
    "QuestionViewModel",
    "DashboardViewModel",
    "ReasoningStepMapper",
    "ErrorRecordMapper",
    "DiagnosisMapper",
    "GradingMapper",
    "QuestionMapper",
    "DashboardMapper",
]
