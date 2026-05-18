"""Design Token System - 设计令牌

所有设计相关的常量集中管理，避免散落在代码中。
包括：颜色、间距、圆角、阴影、字体、图标。
"""

from enum import Enum


# ──────────────────────────────────────────────────────────
# 颜色 Token
# ──────────────────────────────────────────────────────────

class ColorToken(str, Enum):
    """颜色令牌 - 语义化颜色"""
    PRIMARY = "var(--mt-primary)"
    PRIMARY_LIGHT = "var(--mt-primary-light)"
    PRIMARY_DARK = "var(--mt-primary-dark)"
    
    SUCCESS = "var(--mt-success)"
    SUCCESS_BG = "var(--mt-success-bg)"
    WARNING = "var(--mt-warning)"
    WARNING_BG = "var(--mt-warning-bg)"
    ERROR = "var(--mt-error)"
    ERROR_BG = "var(--mt-error-bg)"
    INFO = "var(--mt-info)"
    INFO_BG = "var(--mt-info-bg)"
    
    GRAY_50 = "var(--mt-gray-50)"
    GRAY_100 = "var(--mt-gray-100)"
    GRAY_200 = "var(--mt-gray-200)"
    GRAY_300 = "var(--mt-gray-300)"
    GRAY_500 = "var(--mt-gray-500)"
    GRAY_700 = "var(--mt-gray-700)"
    GRAY_900 = "var(--mt-gray-900)"


# ──────────────────────────────────────────────────────────
# 间距 Token
# ──────────────────────────────────────────────────────────

class SpacingToken(str, Enum):
    """间距令牌"""
    XS = "4px"
    SM = "8px"
    MD = "12px"
    LG = "16px"
    XL = "20px"
    XXL = "24px"


# ──────────────────────────────────────────────────────────
# 圆角 Token
# ──────────────────────────────────────────────────────────

class RadiusToken(str, Enum):
    """圆角令牌"""
    SM = "var(--mt-radius-sm)"
    MD = "var(--mt-radius-md)"
    LG = "var(--mt-radius-lg)"
    PILL = "9999px"


# ──────────────────────────────────────────────────────────
# 阴影 Token
# ──────────────────────────────────────────────────────────

class ShadowToken(str, Enum):
    """阴影令牌"""
    SM = "var(--mt-shadow-sm)"
    MD = "var(--mt-shadow-md)"
    LG = "var(--mt-shadow-lg)"


# ──────────────────────────────────────────────────────────
# 字体 Token
# ──────────────────────────────────────────────────────────

class FontToken(str, Enum):
    """字体令牌"""
    MONO = "var(--mt-font-mono)"
    MATH = "var(--mt-font-math)"


# ──────────────────────────────────────────────────────────
# 语义 Enum - 状态
# ──────────────────────────────────────────────────────────

class StepStatus(str, Enum):
    """推理步骤状态"""
    CORRECT = "correct"
    WRONG = "wrong"
    PARTIAL = "partial"
    WARNING = "warning"
    NEUTRAL = ""


class FormulaStatus(str, Enum):
    """公式状态"""
    CORRECT = "correct"
    WRONG = "wrong"
    PARTIAL = "partial"
    NEUTRAL = ""


class DiffStatus(str, Enum):
    """差异状态"""
    CORRECT = "correct"
    ERROR = "error"
    PARTIAL = "partial"


# ──────────────────────────────────────────────────────────
# 语义 Enum - 类型
# ──────────────────────────────────────────────────────────

class ErrorCategory(str, Enum):
    """错误类型"""
    CONCEPT = "概念错误"
    CALCULATION = "计算错误"
    LOGIC = "逻辑错误"
    METHOD = "方法错误"
    CARELESS = "粗心错误"
    UNKNOWN = "未知错误"


class Difficulty(str, Enum):
    """难度等级"""
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"


class QuestionType(str, Enum):
    """题目类型"""
    CHOICE = "选择题"
    FILL = "填空题"
    SOLUTION = "解答题"


class UserRole(str, Enum):
    """用户角色"""
    STUDENT = "student"
    ADMIN = "admin"


class TagType(str, Enum):
    """标签类型"""
    KNOWLEDGE = "knowledge"
    ERROR = "error-type"
    THEOREM = "theorem"
    EASY = "difficulty-easy"
    MEDIUM = "difficulty-medium"
    HARD = "difficulty-hard"


# ──────────────────────────────────────────────────────────
# 图标映射
# ──────────────────────────────────────────────────────────

STEP_STATUS_ICON = {
    StepStatus.CORRECT: "✅",
    StepStatus.WRONG: "❌",
    StepStatus.PARTIAL: "⚠️",
    StepStatus.WARNING: "⚠️",
    StepStatus.NEUTRAL: "",
}

FORMULA_STATUS_ICON = {
    FormulaStatus.CORRECT: "✅",
    FormulaStatus.WRONG: "❌",
    FormulaStatus.PARTIAL: "⚠️",
    FormulaStatus.NEUTRAL: "",
}

DIFF_STATUS_ICON = {
    DiffStatus.CORRECT: "✅",
    DiffStatus.ERROR: "❌",
    DiffStatus.PARTIAL: "⚠️",
}

QUESTION_TYPE_ICON = {
    QuestionType.CHOICE: "🔵",
    QuestionType.FILL: "🟢",
    QuestionType.SOLUTION: "🟡",
}

DIFFICULTY_TAG = {
    Difficulty.EASY: TagType.EASY,
    Difficulty.MEDIUM: TagType.MEDIUM,
    Difficulty.HARD: TagType.HARD,
}

ERROR_CATEGORY_ICON = {
    ErrorCategory.CONCEPT: "🧠",
    ErrorCategory.CALCULATION: "🔢",
    ErrorCategory.LOGIC: "🔗",
    ErrorCategory.METHOD: "📐",
    ErrorCategory.CARELESS: "👀",
    ErrorCategory.UNKNOWN: "❓",
}


# ──────────────────────────────────────────────────────────
# 状态 → CSS 类映射
# ──────────────────────────────────────────────────────────

STATUS_CSS_CLASS = {
    StepStatus.CORRECT: "correct",
    StepStatus.WRONG: "error",
    StepStatus.PARTIAL: "warning",
    StepStatus.WARNING: "warning",
    StepStatus.NEUTRAL: "",
    FormulaStatus.CORRECT: "correct",
    FormulaStatus.WRONG: "wrong",
    FormulaStatus.PARTIAL: "partial",
    FormulaStatus.NEUTRAL: "",
}

STATUS_BORDER_COLOR = {
    StepStatus.CORRECT: ColorToken.SUCCESS,
    StepStatus.WRONG: ColorToken.ERROR,
    StepStatus.PARTIAL: ColorToken.WARNING,
    StepStatus.WARNING: ColorToken.WARNING,
    StepStatus.NEUTRAL: ColorToken.GRAY_200,
    FormulaStatus.CORRECT: ColorToken.SUCCESS,
    FormulaStatus.WRONG: ColorToken.ERROR,
    FormulaStatus.PARTIAL: ColorToken.WARNING,
    FormulaStatus.NEUTRAL: ColorToken.GRAY_200,
}

STATUS_BG_COLOR = {
    StepStatus.CORRECT: ColorToken.SUCCESS_BG,
    StepStatus.WRONG: ColorToken.ERROR_BG,
    StepStatus.PARTIAL: ColorToken.WARNING_BG,
    StepStatus.WARNING: ColorToken.WARNING_BG,
    StepStatus.NEUTRAL: ColorToken.GRAY_50,
    FormulaStatus.CORRECT: ColorToken.SUCCESS_BG,
    FormulaStatus.WRONG: ColorToken.ERROR_BG,
    FormulaStatus.PARTIAL: ColorToken.WARNING_BG,
    FormulaStatus.NEUTRAL: ColorToken.GRAY_50,
}
