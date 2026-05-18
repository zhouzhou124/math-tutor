"""Repository Layer - 统一数据访问层

采用 JSON + SQLite 混合存储方案：
- SQLite: 存储用户、索引、统计等结构化数据
- JSON: 存储学习画像、错题记录等复杂结构数据

所有数据模型使用 dataclass，确保类型安全和数据一致性。
添加 schema_version 字段支持数据结构升级。

使用方式：
from repository import (
    UserRepository,
    ProfileRepository,
    ProfileStatsRepository,
    ErrorRecordRepository,
    ErrorIndexRepository,
    User,
    UserProfile,
    ErrorRecord,
    ErrorStats,
    DashboardData,
    ReasoningChain,
    GradingResult,
    DiagnosisResult,
)

# 创建 Repository 实例
user_repo = UserRepository(db_path, data_dir)
profile_repo = ProfileRepository(db_path, data_dir)
"""

from .base import BaseRepository, JSONRepository, SQLiteRepository
from .user_repository import UserRepository
from .profile_repository import ProfileRepository, ProfileStatsRepository
from .error_repository import ErrorRecordRepository, ErrorIndexRepository

try:
    from .grading_session_repository import GradingSessionRepository
except ImportError:
    GradingSessionRepository = None  # type: ignore

try:
    from .question_repository import QuestionRepository
except ImportError:
    QuestionRepository = None  # type: ignore
from .models import (
    BaseModel,
    User,
    UserProfile,
    ErrorRecord,
    ErrorStats,
    ReasoningStep,
    ReasoningChain,
    GradingResult,
    DiagnosisResult,
    ASTNode,
    MathAST,
    DashboardData,
    KnowledgeNode,
    KnowledgeEdge,
    KnowledgeGraph,
    OCRResult,
    GradingSession,
    Question,
)

__all__ = [
    # Base classes
    "BaseRepository",
    "JSONRepository",
    "SQLiteRepository",
    
    # Repositories
    "UserRepository",
    "ProfileRepository",
    "ProfileStatsRepository",
    "ErrorRecordRepository",
    "ErrorIndexRepository",
]

if GradingSessionRepository is not None:
    __all__.append("GradingSessionRepository")

if QuestionRepository is not None:
    __all__.append("QuestionRepository")

__all__ += [
    "BaseModel",
    "User",
    "UserProfile",
    "ErrorRecord",
    "ErrorStats",
    "ReasoningStep",
    "ReasoningChain",
    "GradingResult",
    "DiagnosisResult",
    "ASTNode",
    "MathAST",
    "DashboardData",
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeGraph",
    "OCRResult",
    "GradingSession",
    "Question",
]
