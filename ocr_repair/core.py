"""
OCR Repair 核心数据结构

所有数据结构在此定义，无外部依赖。
"""

from dataclasses import dataclass, field
from enum import Enum, auto


# ──────────────────── RepairPolicy ────────────────────

@dataclass
class RepairPolicy:
    """修复策略配置"""
    enable_llm: bool = False
    llm_trigger_quality: float = 0.65
    allow_hallucination_risk: bool = False
    strict_fidelity: bool = True
    enable_layout_recovery: bool = True
    enable_rule_engine: bool = True
    enable_math_merge: bool = True
    max_unrecoverable_ratio: float = 0.40


# ──────────────────── WarningCode ────────────────────

class WarningCode(Enum):
    """警告码枚举"""
    question_gap = auto()            # 题号不连续
    missing_option = auto()          # 选项缺漏
    math_bracket_unbalanced = auto() # 数学括号不配对
    numeric_drift = auto()           # 数字数量漂移
    ocr_unrecoverable = auto()       # OCR 不可恢复损坏
    math_syntax_broken = auto()      # 数学语法断裂
    answer_missing = auto()          # 答案缺失
    semantic_ambiguous = auto()      # 语义模糊
    low_fidelity = auto()            # 保真度过低
    unknown_format = auto()          # 未知格式
    layout_collapsed = auto()        # 行结构崩塌
    formula_broken = auto()          # 公式跨行断裂
    encoding_mixed = auto()          # 编码混用


# ──────────────────── ValidationResult ────────────────────

@dataclass
class ValidationResult:
    """单次验证结果"""
    quality_score: float = 0.0           # 0-1 综合质量分
    warnings: list[WarningCode] = field(default_factory=list)
    question_count: int = 0              # 检测到的题号数
    answer_count: int = 0                # 检测到的答案数
    option_count: int = 0                # 检测到的选项字母组数
    math_valid: bool = False             # 数学语法合法性
    needs_manual_review: bool = False    # 是否需要人工复核
    failure_mode: str = ""               # 失败模式描述
    details: dict = field(default_factory=dict)
    # details 示例字段:
    #   chinese_ratio: float
    #   ocr_garbage_ratio: float
    #   unmatched_braces: int
    #   unmatched_dollars: int
    #   option_gaps: list[str]
    #   question_gaps: list[int]


# ──────────────────── RepairTrace ────────────────────

@dataclass
class RepairTrace:
    """单次 pass 的修复追踪"""
    pass_name: str                       # "safe_normalize" | "layout_recovery" | "rule_engine" | "validator"
    input_snippet: str = ""              # 输入片段（前200字）
    output_snippet: str = ""             # 输出片段（前200字）
    modifications: list[str] = field(default_factory=list)
    # 示例: ["选项断行: 插入了3处换行", "跨行合并: line15+line16"]
    warnings: list[WarningCode] = field(default_factory=list)
    char_count_before: int = 0
    char_count_after: int = 0
    math_object_count_before: int = 0
    math_object_count_after: int = 0


# ──────────────────── FidelityScore ────────────────────

@dataclass
class FidelityScore:
    """保真度评分"""
    length_ratio: float = 1.0            # 修复前后长度比
    math_object_drift: float = 0.0       # 数学对象数量漂移率
    numeric_drift: float = 0.0           # 数字数量漂移率
    question_count_drift: int = 0        # 题号数量变化
    status: str = "ok"                   # "ok" | "warning" | "manual_review"


# ──────────────────── RepairReport ────────────────────

@dataclass
class RepairReport:
    """完整修复报告"""
    original: str = ""
    repaired: str = ""
    pre_validation: ValidationResult | None = None
    post_validation: ValidationResult | None = None
    resolved_warnings: list[WarningCode] = field(default_factory=list)
    introduced_warnings: list[WarningCode] = field(default_factory=list)
    fidelity: FidelityScore | None = None
    traces: list[RepairTrace] = field(default_factory=list)
    needs_manual_review: bool = False
    failure_mode: str = ""
    passes_executed: list[str] = field(default_factory=list)
