"""ViewModel 数据类 - 纯展示数据，使用 Enum 替代字符串

ViewModel 只包含 Renderer 需要的展示信息：
- 颜色、图标、状态、显示文本
- 不包含任何业务逻辑
- 不包含任何数据库字段
- 所有状态使用 Enum，避免字符串地狱
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

from rendering.tokens import (
    StepStatus,
    FormulaStatus,
    DiffStatus,
    ErrorCategory,
    Difficulty,
    QuestionType,
    TagType,
    ColorToken,
)


@dataclass
class FormulaViewModel:
    """公式展示 ViewModel"""
    latex: str
    label: str = ""
    status: FormulaStatus = FormulaStatus.NEUTRAL
    status_icon: str = ""
    display_label: str = ""


@dataclass
class StepCardViewModel:
    """推理步骤卡片 ViewModel"""
    step_number: int
    title: str
    expression: str = ""
    reasoning: str = ""
    status: StepStatus = StepStatus.NEUTRAL
    status_icon: str = ""
    status_color: str = ""
    knowledge_tags: List[str] = field(default_factory=list)
    theorem_tag: str = ""
    is_critical: bool = False
    display_title: str = ""


@dataclass
class ErrorViewModel:
    """错误定位 ViewModel"""
    error_type: ErrorCategory = ErrorCategory.UNKNOWN
    error_type_display: str = ""
    error_type_icon: str = "⚠️"
    cause: str = ""
    fix: str = ""
    student_expr: str = ""
    correct_expr: str = ""
    knowledge_point: str = ""
    has_diff: bool = False


@dataclass
class DiagnosisViewModel:
    """诊断面板 ViewModel"""
    error_type: ErrorCategory = ErrorCategory.UNKNOWN
    error_type_display: str = ""
    root_cause: str = ""
    knowledge_tags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_pct: str = "0%"
    is_repeat: bool = False
    repeat_count: int = 0


@dataclass
class ScoreViewModel:
    """评分面板 ViewModel"""
    total_score: int = 0
    max_score: int = 0
    total_display: str = ""
    process_score: int = 0
    max_process: int = 0
    process_display: str = ""
    deduction_total: int = 0
    deduction_display: str = ""
    is_correct: bool = False
    accuracy_pct: str = ""
    deductions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DiffViewModel:
    """差异对比 ViewModel"""
    student_expr: str = ""
    correct_expr: str = ""
    student_label: str = "学生答案"
    correct_label: str = "正确答案"
    status: DiffStatus = DiffStatus.PARTIAL


@dataclass
class ChainViewModel:
    """推理链 ViewModel"""
    chain_id: str = ""
    steps: List[StepCardViewModel] = field(default_factory=list)
    final_answer: Optional[FormulaViewModel] = None
    connectors: List[str] = field(default_factory=list)


@dataclass
class QuestionViewModel:
    """题目展示 ViewModel"""
    question_id: str = ""
    display_title: str = ""
    question_type: QuestionType = QuestionType.CHOICE
    question_type_icon: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM
    difficulty_tag_type: TagType = TagType.MEDIUM
    score: int = 0
    score_display: str = ""
    knowledge_tags: List[str] = field(default_factory=list)
    question_text: str = ""
    options: Dict[str, str] = field(default_factory=dict)
    correct_option: str = ""
    correct_option_display: str = ""
    answer: str = ""
    analysis: str = ""
    has_ocr_fix: bool = False
    ocr_raw: str = ""
    ocr_fixed: str = ""


@dataclass
class DashboardViewModel:
    """仪表盘 ViewModel"""
    username: str = ""
    welcome_message: str = ""
    total_questions: int = 0
    total_errors: int = 0
    accuracy: str = "0%"
    streak_days: int = 0
    streak_display: str = ""
    weak_points: List[str] = field(default_factory=list)
    level: str = ""
    level_display: str = ""
