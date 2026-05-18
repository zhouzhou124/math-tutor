"""scoring_layer.py — 评分层 (Scoring Layer)

考研数学评分标准：
  ┌─────────────────────────────────────────────────────────────────┐
  │                    考研数学评分结构                               │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │
  │  │ 结果分   │ │ 过程分   │ │ 逻辑分   │ │ 方法分   │ │表达分 │ │
  │  │ 20~30%  │ │ 40~50%  │ │ 15~25%  │ │ 10~20%  │ │0~5%  │ │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────┘ │
  │                              │                                  │
  │                    关键步骤 (Critical Step)                      │
  │                    ┌─────────────────────────┐                  │
  │                    │ Taylor展开 / 换元        │                  │
  │                    │ 构造辅助函数 / 特征方程   │                  │
  │                    └─────────────────────────┘                  │
  └─────────────────────────────────────────────────────────────────┘

正确的评分公式：
  Score = Σ(step_weight × correctness × propagation_factor)
  
  其中：
  - step_weight: 步骤权重（关键步骤权重更高）
  - correctness: 步骤正确性 (0~1)
  - propagation_factor: 错误传播因子（关键步骤错误会传播）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
from dataclasses_json import dataclass_json

# 导入验证层
from verification_layer import (
    VerificationResult, 
    StepTransitionResult, 
    FullVerificationResult,
    ErrorLevel,
    get_verifier
)


# ═══════════════════════════════════════════════
# 关键步骤定义
# ═══════════════════════════════════════════════

class CriticalStepType(Enum):
    """关键步骤类型枚举"""
    TAYLOR_EXPANSION = "taylor_expansion"
    SUBSTITUTION = "substitution"
    AUXILIARY_FUNCTION = "auxiliary_function"
    CHARACTERISTIC_EQUATION = "characteristic_equation"
    INTEGRATION_BY_PARTS = "integration_by_parts"
    L_HOSPITAL = "l_hospital"
    MEAN_VALUE_THEOREM = "mean_value_theorem"
    CHANGE_OF_VARIABLES = "change_of_variables"
    SEPARATION_OF_VARIABLES = "separation_of_variables"
    MATRIX_DIAGONALIZATION = "matrix_diagonalization"
    EIGENVALUE = "eigenvalue"
    SERIES_EXPANSION = "series_expansion"
    INDUCTION = "induction"
    CONTRADICTION = "contradiction"
    OTHER = "other"

# 关键步骤关键词映射
CRITICAL_STEP_PATTERNS: Dict[CriticalStepType, List[str]] = {
    CriticalStepType.TAYLOR_EXPANSION: [
        "taylor", "泰勒", "展开", "级数展开", "麦克劳林", "mclaurin"
    ],
    CriticalStepType.SUBSTITUTION: [
        "换元", "变量替换", "substitution", "令", "设", "let"
    ],
    CriticalStepType.AUXILIARY_FUNCTION: [
        "辅助函数", "构造函数", "construct", "define", "设函数"
    ],
    CriticalStepType.CHARACTERISTIC_EQUATION: [
        "特征方程", "特征根", "characteristic", "齐次方程", "通解"
    ],
    CriticalStepType.INTEGRATION_BY_PARTS: [
        "分部积分", "integration by parts", "uv积分"
    ],
    CriticalStepType.L_HOSPITAL: [
        "洛必达", "洛必达法则", "l_hospital", "0/0", "∞/∞"
    ],
    CriticalStepType.MEAN_VALUE_THEOREM: [
        "中值定理", "拉格朗日", "罗尔", "柯西中值", "mean value"
    ],
    CriticalStepType.CHANGE_OF_VARIABLES: [
        "变量替换", "坐标变换", "变量代换", "transform"
    ],
    CriticalStepType.SEPARATION_OF_VARIABLES: [
        "分离变量", "变量分离", "separation"
    ],
    CriticalStepType.MATRIX_DIAGONALIZATION: [
        "对角化", "相似变换", "相似对角化", "diagonalize"
    ],
    CriticalStepType.EIGENVALUE: [
        "特征值", "特征向量", "eigenvalue", "eigenvector"
    ],
    CriticalStepType.SERIES_EXPANSION: [
        "级数展开", "幂级数", "傅里叶", "fourier", "series"
    ],
    CriticalStepType.INDUCTION: [
        "归纳法", "数学归纳", "induction", "归纳证明"
    ],
    CriticalStepType.CONTRADICTION: [
        "反证法", "矛盾", "contradiction", "假设"
    ],
}

# 关键步骤默认权重（关键步骤权重更高）
CRITICAL_STEP_WEIGHTS: Dict[CriticalStepType, float] = {
    CriticalStepType.TAYLOR_EXPANSION: 0.5,
    CriticalStepType.SUBSTITUTION: 0.4,
    CriticalStepType.AUXILIARY_FUNCTION: 0.5,
    CriticalStepType.CHARACTERISTIC_EQUATION: 0.4,
    CriticalStepType.INTEGRATION_BY_PARTS: 0.3,
    CriticalStepType.L_HOSPITAL: 0.4,
    CriticalStepType.MEAN_VALUE_THEOREM: 0.5,
    CriticalStepType.CHANGE_OF_VARIABLES: 0.4,
    CriticalStepType.SEPARATION_OF_VARIABLES: 0.3,
    CriticalStepType.MATRIX_DIAGONALIZATION: 0.4,
    CriticalStepType.EIGENVALUE: 0.4,
    CriticalStepType.SERIES_EXPANSION: 0.4,
    CriticalStepType.INDUCTION: 0.5,
    CriticalStepType.CONTRADICTION: 0.5,
    CriticalStepType.OTHER: 0.2,
}


# ═══════════════════════════════════════════════
# 评分维度定义
# ═══════════════════════════════════════════════

class ScoreDimension(Enum):
    """评分维度枚举（考研数学标准）"""
    RESULT = "result"
    PROCESS = "process"
    LOGIC = "logic"
    METHOD = "method"
    EXPRESSION = "expression"


class ProofScoreDimension(Enum):
    """
    证明题评分维度枚举
    
    证明题评分结构：
      - 逻辑链完整性 40%
      - 关键定理正确性 30%
      - 证明结构 20%
      - 最终结论 10%
    
    核心思想：证明题绝不能只看结果，必须重视逻辑评分
    """
    LOGIC_CHAIN = "logic_chain"           # 逻辑链完整性 40%
    THEOREM_CORRECTNESS = "theorem"        # 关键定理正确性 30%
    PROOF_STRUCTURE = "structure"          # 证明结构 20%
    FINAL_CONCLUSION = "conclusion"        # 最终结论 10%


class ScoreType(Enum):
    """评分类型枚举"""
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    BONUS = "bonus"


# ═══════════════════════════════════════════════
# 评分结果定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class DimensionScore:
    """维度得分"""
    dimension: ScoreDimension
    score: float = 0.0
    max_score: float = 0.0
    type: ScoreType = ScoreType.NONE
    reason: str = ""
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass_json
@dataclass
class StepScore:
    """单步骤评分"""
    step_index: int
    score: float = 0.0
    max_score: float = 0.0
    weight: float = 0.2           # 步骤权重
    correctness: float = 1.0      # 正确性 (0~1)
    propagation_factor: float = 1.0  # 错误传播因子
    verified: bool = False
    error_level: ErrorLevel = ErrorLevel.CORRECT
    operation: str = ""
    message: str = ""
    is_critical: bool = False
    critical_type: Optional[CriticalStepType] = None


@dataclass_json
@dataclass
class CriticalStepResult:
    """关键步骤识别结果"""
    found_critical_steps: List[CriticalStepType] = field(default_factory=list)
    missing_critical_steps: List[CriticalStepType] = field(default_factory=list)
    critical_step_scores: List[StepScore] = field(default_factory=list)
    critical_score_ratio: float = 0.0


@dataclass_json
@dataclass
class ScoringResult:
    """综合评分结果（考研数学标准）"""
    total_score: float = 0.0
    max_score: float = 0.0
    step_scores: List[StepScore] = field(default_factory=list)
    dimension_scores: List[DimensionScore] = field(default_factory=list)
    critical_result: CriticalStepResult = field(default_factory=CriticalStepResult)
    overall_feedback: str = ""
    confidence: float = 0.0
    breakdown: str = ""
    weighted_breakdown: str = ""  # 加权评分明细


@dataclass_json
@dataclass
class ProofDimensionScore:
    """证明题维度得分"""
    dimension: ProofScoreDimension
    score: float = 0.0
    max_score: float = 0.0
    type: ScoreType = ScoreType.NONE
    reason: str = ""
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass_json
@dataclass
class LogicChainAnalysis:
    """逻辑链分析结果"""
    total_steps: int = 0                    # 总步骤数
    connected_steps: int = 0                # 连接的步骤数
    logic_gaps: List[int] = field(default_factory=list)  # 逻辑跳跃位置
    missing_conditions: List[str] = field(default_factory=list)  # 缺失条件
    redundant_steps: List[int] = field(default_factory=list)  # 冗余步骤
    completeness_score: float = 0.0         # 完整性得分 (0~1)


@dataclass_json
@dataclass
class ProofScoringResult:
    """证明题评分结果"""
    total_score: float = 0.0
    max_score: float = 100.0
    dimension_scores: List[ProofDimensionScore] = field(default_factory=list)
    logic_chain_analysis: LogicChainAnalysis = field(default_factory=LogicChainAnalysis)
    theorem_usage: List[Dict[str, Any]] = field(default_factory=list)  # 定理使用情况
    proof_structure_score: float = 0.0
    overall_feedback: str = ""
    breakdown: str = ""


# ═══════════════════════════════════════════════
# 评分配置定义（考研数学标准）
# ═══════════════════════════════════════════════

@dataclass
class ScoringConfig:
    """
    评分配置（考研数学标准）
    
    三级错误扣分系统：
      一级错误（重）Conceptual Error: 扣30~70%
      二级错误（中）Algebraic Error: 扣5~20%
      三级错误（轻）Arithmetic Error: 扣1~5%
    """
    
    result_weight: float = 0.25
    process_weight: float = 0.45
    logic_weight: float = 0.15
    method_weight: float = 0.12
    expression_weight: float = 0.03
    
    critical_step_weight: float = 0.6
    
    step_full_score: float = 100.0
    step_penalty_factor: float = 0.5
    
    result_full_score: float = 100.0
    result_tolerance: float = 0.01
    
    logic_full_score: float = 100.0
    continuity_threshold: float = 0.5
    
    expression_full_score: float = 100.0
    
    # 关键步骤错误传播系数
    critical_error_propagation: float = 0.3
    
    # 连带错误步骤的方法分比例
    method_score_for_propagated: float = 0.5
    
    # 普通步骤权重
    normal_step_weight: float = 0.15
    
    # 关键步骤权重
    critical_step_base_weight: float = 0.4
    
    # 三级错误扣分比例
    # 一级错误（重）Conceptual Error: 扣30~70%
    # 二级错误（中）Algebraic Error: 扣5~20%
    # 三级错误（轻）Arithmetic Error: 扣1~5%
    error_penalties: Dict[ErrorLevel, float] = field(default_factory=lambda: {
        ErrorLevel.CORRECT: 0.0,      # 正确，不扣分
        ErrorLevel.LEVEL_0: 0.3,      # 解题路径缺失，扣30%
        ErrorLevel.LEVEL_1: 0.03,     # 三级错误（轻）Arithmetic Error，扣1~5%
        ErrorLevel.LEVEL_2: 0.12,     # 二级错误（中）Algebraic Error，扣5~20%
        ErrorLevel.LEVEL_3: 0.5,      # 一级错误（重）Conceptual Error，扣30~70%
        ErrorLevel.WARNING: 0.02,     # 警告，扣2%
    })
    
    # 三级错误扣分范围（用于动态调整）
    error_penalty_ranges: Dict[ErrorLevel, Tuple[float, float]] = field(default_factory=lambda: {
        ErrorLevel.LEVEL_1: (0.01, 0.05),   # 三级错误（轻）: 扣1~5%
        ErrorLevel.LEVEL_2: (0.05, 0.20),   # 二级错误（中）: 扣5~20%
        ErrorLevel.LEVEL_3: (0.30, 0.70),   # 一级错误（重）: 扣30~70%
    })


@dataclass
class ProofScoringConfig:
    """
    证明题评分配置
    
    证明题评分结构：
      - 逻辑链完整性 40%
      - 关键定理正确性 30%
      - 证明结构 20%
      - 最终结论 10%
    
    核心思想：证明题绝不能只看结果，必须重视逻辑评分
    """
    
    # 证明题评分权重
    logic_chain_weight: float = 0.40        # 逻辑链完整性 40%
    theorem_weight: float = 0.30            # 关键定理正确性 30%
    structure_weight: float = 0.20          # 证明结构 20%
    conclusion_weight: float = 0.10         # 最终结论 10%
    
    # 逻辑链评分参数
    logic_chain_full_score: float = 100.0
    gap_penalty: float = 0.15               # 每个逻辑跳跃扣15%
    missing_condition_penalty: float = 0.20  # 每个缺失条件扣20%
    
    # 定理使用评分参数
    theorem_full_score: float = 100.0
    wrong_theorem_penalty: float = 0.5      # 用错定理扣50%
    missing_theorem_penalty: float = 0.3    # 缺失定理扣30%
    
    # 证明结构评分参数
    structure_full_score: float = 100.0
    structure_types: Dict[str, float] = field(default_factory=lambda: {
        "direct": 1.0,           # 直接证明
        "contradiction": 1.0,    # 反证法
        "induction": 1.0,        # 数学归纳法
        "construction": 0.9,     # 构造法
        "counter_example": 0.8,  # 反例证明
    })
    
    # 最终结论评分参数
    conclusion_full_score: float = 100.0
    partial_conclusion_score: float = 0.5   # 部分结论得50%


# ═══════════════════════════════════════════════
# 关键步骤识别器
# ═══════════════════════════════════════════════

class CriticalStepRecognizer:
    """关键步骤识别器"""
    
    @classmethod
    def recognize_critical_step(cls, operation: str, output_state: str = "") -> Optional[CriticalStepType]:
        text = (operation + " " + output_state).lower()
        
        for step_type, patterns in CRITICAL_STEP_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    return step_type
        
        return None
    
    @classmethod
    def recognize_all(cls, steps: List[Dict]) -> List[Tuple[int, CriticalStepType]]:
        results = []
        for i, step in enumerate(steps):
            operation = step.get('operation', '')
            output_state = step.get('output_state', '')
            critical_type = cls.recognize_critical_step(operation, output_state)
            if critical_type:
                results.append((i, critical_type))
        return results
    
    @classmethod
    def check_missing_critical_steps(
        cls, 
        found_steps: List[CriticalStepType], 
        expected_steps: List[CriticalStepType] = None
    ) -> List[CriticalStepType]:
        if expected_steps is None:
            return []
        return [step for step in expected_steps if step not in found_steps]
    
    @classmethod
    def get_step_weight(cls, is_critical: bool, critical_type: Optional[CriticalStepType] = None) -> float:
        """获取步骤权重"""
        if is_critical and critical_type:
            return CRITICAL_STEP_WEIGHTS.get(critical_type, 0.3)
        return 0.15  # 普通步骤权重


# ═══════════════════════════════════════════════
# 结果评分器 (20~30%)
# ═══════════════════════════════════════════════

class ResultScorer:
    """结果评分器"""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
        self.verifier = get_verifier()
    
    def score_result(self, student_result: str, standard_result: str) -> DimensionScore:
        max_score = self.config.result_full_score
        
        verification = self.verifier.verify_expression_equivalence(
            student_result, 
            standard_result
        )
        
        if verification.verified:
            score = max_score
            score_type = ScoreType.FULL
            reason = "答案正确"
        else:
            score = 0.0
            score_type = ScoreType.NONE
            reason = "答案不正确"
        
        return DimensionScore(
            dimension=ScoreDimension.RESULT,
            score=score,
            max_score=max_score,
            type=score_type,
            reason=reason,
            details=[{"method": verification.method}]
        )


# ═══════════════════════════════════════════════
# 过程评分器 (40~50%) - 核心：一次主扣
# ═══════════════════════════════════════════════

class ProcessScorer:
    """
    过程评分器 - 一次主扣机制
    
    核心思想：
    1. 关键步骤错误时，在该步骤"一次主扣"
    2. 后续步骤不再重复扣分（因为是错误结果的连带推导）
    3. 后续步骤如果方法正确，可以给部分"方法分"
    
    例如：
      Step1 Taylor展开错误 → 扣Step1的分（一次主扣）
      Step2 用错误结果化简 → 不扣分（连带错误）
      Step3 最终答案错误 → 不扣分（连带错误）
    
    这符合实际阅卷逻辑！
    """
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
        self.verifier = get_verifier()
    
    def score_process(
        self, 
        steps: List[Dict], 
        expected_critical_steps: List[CriticalStepType] = None
    ) -> Tuple[DimensionScore, List[StepScore], CriticalStepResult]:
        """
        评分过程（一次主扣机制）
        
        核心逻辑：
        1. 找到第一个错误的关键步骤
        2. 在该步骤"一次主扣"
        3. 后续步骤不再重复扣分（标记为"连带错误"）
        4. 如果后续步骤方法正确，给部分方法分
        """
        max_score = self.config.step_full_score
        step_scores = []
        critical_results = []
        found_critical_steps = []
        
        # 归一化权重
        total_weight = 0.0
        step_weights = []
        
        for i, step in enumerate(steps):
            operation = step.get('operation', '')
            output_state = step.get('output_state', '')
            critical_type = CriticalStepRecognizer.recognize_critical_step(operation, output_state)
            is_critical = critical_type is not None
            
            weight = CriticalStepRecognizer.get_step_weight(is_critical, critical_type)
            step_weights.append(weight)
            total_weight += weight
        
        # 错误传播状态
        first_error_step = -1  # 第一个错误的步骤索引
        first_error_is_critical = False  # 第一个错误是否是关键步骤
        error_propagated = False  # 是否已发生错误传播
        
        for i, step in enumerate(steps):
            if i == 0:
                from_output = step.get('output_state', '')
                to_input = step.get('output_state', '')
                operation = step.get('operation', 'start')
            else:
                from_output = steps[i-1].get('output_state', '')
                to_input = step.get('input_state', '')
                operation = step.get('operation', 'compute')
            
            # 验证步骤转换
            transition_result = self.verifier.verify_step_transition(
                from_output, to_input, operation
            )
            
            # 识别关键步骤
            critical_type = CriticalStepRecognizer.recognize_critical_step(
                operation, step.get('output_state', '')
            )
            is_critical = critical_type is not None
            
            if is_critical:
                found_critical_steps.append(critical_type)
            
            # 计算步骤得分（一次主扣机制）
            normalized_weight = step_weights[i] / max(total_weight, 1)
            step_max = max_score * normalized_weight
            
            if transition_result.verification.verified:
                # 步骤正确
                if error_propagated:
                    # 之前有关键步骤错误，当前步骤是基于错误结果的推导
                    # 不重复扣分，给部分"方法分"
                    step_score_value = step_max * self.config.method_score_for_propagated
                    error_level = ErrorLevel.CORRECT
                    message = f"步骤{i+1}方法正确（基于前序错误结果）"
                    is_propagated = True
                else:
                    # 正常得分
                    step_score_value = step_max
                    error_level = ErrorLevel.CORRECT
                    message = f"步骤{i+1}正确"
                    if is_critical:
                        message += f"（关键步骤: {critical_type.name}）"
                    is_propagated = False
            else:
                # 步骤错误
                if not error_propagated:
                    # 这是第一个错误步骤
                    first_error_step = i
                    first_error_is_critical = is_critical
                    
                    if is_critical:
                        # 关键步骤错误：一次主扣
                        penalty = self.config.error_penalties.get(
                            transition_result.verification.error_level, 0.5
                        )
                        step_score_value = step_max * (1 - penalty)
                        error_propagated = True
                        message = f"步骤{i+1}错误（关键步骤，一次主扣）"
                    else:
                        # 普通步骤错误
                        penalty = self.config.error_penalties.get(
                            transition_result.verification.error_level, 0.3
                        )
                        step_score_value = step_max * (1 - penalty)
                        message = f"步骤{i+1}: {transition_result.verification.message}"
                    is_propagated = False
                else:
                    # 已经有关键步骤错误，当前步骤是连带错误
                    # 不重复扣分，给部分"方法分"
                    step_score_value = step_max * self.config.method_score_for_propagated
                    error_level = ErrorLevel.CORRECT
                    message = f"步骤{i+1}方法正确（连带错误）"
                    is_propagated = True
                
                error_level = transition_result.verification.error_level
            
            step_score = StepScore(
                step_index=i,
                score=step_score_value,
                max_score=step_max,
                weight=step_weights[i],
                correctness=step_score_value / step_max if step_max > 0 else 0,
                propagation_factor=1.0 if not error_propagated else self.config.method_score_for_propagated,
                verified=transition_result.verification.verified or is_propagated,
                error_level=error_level,
                operation=operation,
                message=message,
                is_critical=is_critical,
                critical_type=critical_type
            )
            step_scores.append(step_score)
            
            if is_critical:
                critical_results.append(step_score)
        
        # 计算关键步骤得分率
        critical_total = sum(s.score for s in critical_results)
        critical_max = sum(s.max_score for s in critical_results)
        critical_ratio = critical_total / max(critical_max, 1)
        
        # 检查缺失的关键步骤
        missing_steps = CriticalStepRecognizer.check_missing_critical_steps(
            found_critical_steps, expected_critical_steps
        )
        
        # 计算过程分（加权求和）
        process_score = sum(s.score for s in step_scores)
        reason = f"完成{len(critical_results)}个关键步骤"
        if missing_steps:
            reason += f"，缺失{len(missing_steps)}个关键步骤"
        if first_error_is_critical:
            reason += f"，步骤{first_error_step+1}关键步骤错误（一次主扣）"
        
        critical_result = CriticalStepResult(
            found_critical_steps=found_critical_steps,
            missing_critical_steps=missing_steps,
            critical_step_scores=critical_results,
            critical_score_ratio=critical_ratio
        )
        
        return (
            DimensionScore(
                dimension=ScoreDimension.PROCESS,
                score=process_score,
                max_score=max_score,
                type=ScoreType.FULL if process_score >= max_score * 0.9 else ScoreType.PARTIAL,
                reason=reason,
                details=[{"critical_steps_found": len(found_critical_steps), "first_error_step": first_error_step}]
            ),
            step_scores,
            critical_result
        )


# ═══════════════════════════════════════════════
# 逻辑评分器 (15~25%)
# ═══════════════════════════════════════════════

class LogicScorer:
    """逻辑评分器"""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
    
    def score_logic(self, full_result: FullVerificationResult, steps: List[Dict]) -> DimensionScore:
        max_score = self.config.logic_full_score
        
        continuity_score = self._check_continuity(steps)
        gap_count = self._count_logic_gaps(steps)
        
        if full_result.overall_verified and gap_count == 0:
            score = max_score * full_result.overall_score * continuity_score
            score_type = ScoreType.FULL
            reason = "推导逻辑完整连续"
        elif gap_count > 0:
            gap_penalty = min(gap_count * 0.1, 0.3)
            score = max_score * (1 - gap_penalty) * full_result.overall_score
            score_type = ScoreType.PARTIAL
            reason = f"推导存在{gap_count}处逻辑跳跃"
        else:
            penalty = self.config.error_penalties.get(full_result.error_level, 0.3)
            score = max_score * (1 - penalty) * full_result.overall_score
            score_type = ScoreType.PARTIAL
            reason = f"推导逻辑存在问题: {full_result.error_level.label}"
        
        return DimensionScore(
            dimension=ScoreDimension.LOGIC,
            score=score,
            max_score=max_score,
            type=score_type,
            reason=reason,
            details=[{
                "continuity_score": continuity_score,
                "gap_count": gap_count,
                "overall_score": full_result.overall_score
            }]
        )
    
    def _check_continuity(self, steps: List[Dict]) -> float:
        if len(steps) < 2:
            return 1.0
        
        continuous_count = 0
        for i in range(1, len(steps)):
            prev_output = steps[i-1].get('output_state', '')
            curr_input = steps[i].get('input_state', '')
            if prev_output and curr_input and prev_output in curr_input:
                continuous_count += 1
        
        return continuous_count / (len(steps) - 1)
    
    def _count_logic_gaps(self, steps: List[Dict]) -> int:
        gaps = 0
        for i in range(1, len(steps)):
            prev_op = steps[i-1].get('operation', '')
            critical_ops = ['taylor', 'substitution', 'auxiliary', 'characteristic']
            prev_has_critical = any(op in prev_op.lower() for op in critical_ops)
            
            if prev_has_critical and not curr_input_matches_prev_output(steps, i):
                gaps += 1
        
        return gaps


def curr_input_matches_prev_output(steps: List[Dict], i: int) -> bool:
    prev_output = steps[i-1].get('output_state', '')
    curr_input = steps[i].get('input_state', '')
    return prev_output and curr_input and (prev_output in curr_input or curr_input in prev_output)


# ═══════════════════════════════════════════════
# 方法评分器 (10~20%)
# ═══════════════════════════════════════════════

class MethodScorer:
    """方法评分器"""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
    
    def score_method(
        self, 
        steps: List[Dict], 
        optimal_methods: List[CriticalStepType] = None
    ) -> DimensionScore:
        max_score = self.config.result_full_score
        optimal_methods = optimal_methods or []
        
        operations = [step.get('operation', '').lower() for step in steps]
        found_critical = CriticalStepRecognizer.recognize_all(steps)
        complexity = self._estimate_complexity(operations) if operations else 0
        
        if not operations:
            return DimensionScore(
                dimension=ScoreDimension.METHOD,
                score=0.0,
                max_score=max_score,
                type=ScoreType.NONE,
                reason="未使用任何方法",
                details=[{"complexity": 0, "critical_steps_used": 0}]
            )
        
        found_types = [t for _, t in found_critical]
        used_optimal = any(opt in found_types for opt in optimal_methods)
        
        if used_optimal:
            score = max_score
            reason = "使用了最优解题方法"
            score_type = ScoreType.FULL
        else:
            if complexity <= 3:
                score = max_score * 0.8
                reason = "使用了较优方法"
            elif complexity <= 5:
                score = max_score * 0.6
                reason = "使用了可行方法"
            else:
                score = max_score * 0.4
                reason = "方法较为复杂"
            score_type = ScoreType.PARTIAL
        
        return DimensionScore(
            dimension=ScoreDimension.METHOD,
            score=score,
            max_score=max_score,
            type=score_type,
            reason=reason,
            details=[{"complexity": complexity, "critical_steps_used": len(found_critical)}]
        )
    
    def _estimate_complexity(self, operations: List[str]) -> int:
        complexity = len(operations)
        complex_ops = ['integrate', 'differentiate', 'taylor', 'limit', 'series']
        for op in operations:
            if any(c in op for c in complex_ops):
                complexity += 1
        return complexity


# ═══════════════════════════════════════════════
# 表达评分器 (0~5%)
# ═══════════════════════════════════════════════

class ExpressionScorer:
    """表达评分器"""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
    
    def score_expression(self, steps: List[Dict]) -> DimensionScore:
        max_score = self.config.expression_full_score
        
        if not steps:
            return DimensionScore(
                dimension=ScoreDimension.EXPRESSION,
                score=0.0,
                max_score=max_score,
                type=ScoreType.NONE,
                reason="无步骤可评估"
            )
        
        symbol_score = self._check_symbol_consistency(steps)
        clarity_score = self._check_clarity(steps)
        completeness_score = self._check_completeness(steps)
        
        avg_score = (symbol_score + clarity_score + completeness_score) / 3
        score = max_score * avg_score
        
        if avg_score >= 0.9:
            reason = "符号规范，步骤清晰"
            score_type = ScoreType.FULL
        elif avg_score >= 0.6:
            reason = "表达基本规范"
            score_type = ScoreType.PARTIAL
        else:
            reason = "表达需要改进"
            score_type = ScoreType.PARTIAL
        
        return DimensionScore(
            dimension=ScoreDimension.EXPRESSION,
            score=score,
            max_score=max_score,
            type=score_type,
            reason=reason,
            details=[{
                "symbol_score": symbol_score,
                "clarity_score": clarity_score,
                "completeness_score": completeness_score
            }]
        )
    
    def _check_symbol_consistency(self, steps: List[Dict]) -> float:
        symbols_used: Set[str] = set()
        for step in steps:
            output = step.get('output_state', '')
            for sym in ['x', 'y', 'z', 'f', 'g', 'h']:
                if sym in output:
                    symbols_used.add(sym)
        return 1.0 if len(symbols_used) <= 5 else 0.7
    
    def _check_clarity(self, steps: List[Dict]) -> float:
        clear_count = 0
        for step in steps:
            op = step.get('operation', '')
            if op in ['start', 'factor', 'expand', 'solve', 'integrate', 'differentiate']:
                clear_count += 1
        return clear_count / max(len(steps), 1)
    
    def _check_completeness(self, steps: List[Dict]) -> float:
        complete_count = 0
        for step in steps:
            if step.get('output_state') and step.get('operation'):
                complete_count += 1
        return complete_count / max(len(steps), 1)


# ═══════════════════════════════════════════════
# 统一评分器（考研数学标准 - 加权评分）
# ═══════════════════════════════════════════════

class UnifiedScorer:
    """统一评分器 - 加权评分"""
    
    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
        self.result_scorer = ResultScorer(config)
        self.process_scorer = ProcessScorer(config)
        self.logic_scorer = LogicScorer(config)
        self.method_scorer = MethodScorer(config)
        self.expression_scorer = ExpressionScorer(config)
        self.verifier = get_verifier()
    
    def score_derivation(
        self,
        steps: List[Dict],
        student_result: str,
        standard_result: str,
        question_type: str = "solution",
        expected_critical_steps: List[CriticalStepType] = None,
        optimal_methods: List[CriticalStepType] = None
    ) -> ScoringResult:
        """评分完整推导过程（加权评分）"""
        expected_critical_steps = expected_critical_steps or []
        optimal_methods = optimal_methods or []
        
        full_verification = self.verifier.verify_full_derivation(
            steps, student_result
        )
        
        process_score, step_scores, critical_result = self.process_scorer.score_process(
            steps, expected_critical_steps
        )
        
        result_score = self.result_scorer.score_result(student_result, standard_result)
        logic_score = self.logic_scorer.score_logic(full_verification, steps)
        method_score = self.method_scorer.score_method(steps, optimal_methods)
        expression_score = self.expression_scorer.score_expression(steps)
        
        dim_scores = [result_score, process_score, logic_score, method_score, expression_score]
        
        weighted_scores = [
            (result_score.score / result_score.max_score) * 100 * self.config.result_weight,
            (process_score.score / process_score.max_score) * 100 * self.config.process_weight,
            (logic_score.score / logic_score.max_score) * 100 * self.config.logic_weight,
            (method_score.score / method_score.max_score) * 100 * self.config.method_weight,
            (expression_score.score / expression_score.max_score) * 100 * self.config.expression_weight,
        ]
        
        total_score = sum(weighted_scores)
        max_score = 100.0
        
        feedback_parts = []
        if result_score.type == ScoreType.FULL:
            feedback_parts.append("答案正确")
        else:
            feedback_parts.append(f"答案{result_score.reason}")
        
        if critical_result.found_critical_steps:
            feedback_parts.append(f"完成{len(critical_result.found_critical_steps)}个关键步骤")
        if critical_result.missing_critical_steps:
            missing_names = [s.name for s in critical_result.missing_critical_steps]
            feedback_parts.append(f"缺失关键步骤: {', '.join(missing_names)}")
        
        if logic_score.type == ScoreType.FULL:
            feedback_parts.append("推导逻辑清晰")
        else:
            feedback_parts.append(f"推导{logic_score.reason}")
        
        # 生成评分明细
        breakdown_lines = []
        breakdown_lines.append("=" * 50)
        breakdown_lines.append("【考研数学评分明细 - 一次主扣机制】")
        breakdown_lines.append("=" * 50)
        breakdown_lines.append(f"结果分: {weighted_scores[0]:.1f}/{100*self.config.result_weight:.0f} ({result_score.reason})")
        breakdown_lines.append(f"过程分: {weighted_scores[1]:.1f}/{100*self.config.process_weight:.0f} ({process_score.reason})")
        breakdown_lines.append(f"逻辑分: {weighted_scores[2]:.1f}/{100*self.config.logic_weight:.0f} ({logic_score.reason})")
        breakdown_lines.append(f"方法分: {weighted_scores[3]:.1f}/{100*self.config.method_weight:.0f} ({method_score.reason})")
        breakdown_lines.append(f"表达分: {weighted_scores[4]:.1f}/{100*self.config.expression_weight:.0f} ({expression_score.reason})")
        breakdown_lines.append("-" * 50)
        breakdown_lines.append(f"总  分: {total_score:.1f}/{max_score}")
        
        # 一次主扣评分明细
        weighted_lines = []
        weighted_lines.append("\n【一次主扣评分详情】")
        weighted_lines.append("核心思想: 关键步骤错误时，在该步骤一次主扣，后续步骤不重复扣分")
        weighted_lines.append("-" * 50)
        
        for s in step_scores:
            critical_marker = "[关键]" if s.is_critical else "[普通]"
            propagated_marker = " [连带]" if s.propagation_factor < 1.0 else ""
            weighted_lines.append(
                f"  {critical_marker}{propagated_marker} 步骤{s.step_index+1}: "
                f"权重={s.weight:.2f}, "
                f"得分={s.score:.1f}/{s.max_score:.1f}"
            )
            weighted_lines.append(f"      {s.message}")
        
        # 关键步骤详情
        if critical_result.critical_step_scores:
            weighted_lines.append("\n【关键步骤详情】")
            for s in critical_result.critical_step_scores:
                status = "OK" if s.verified else "NG"
                weighted_lines.append(f"  [{status}] 步骤{s.step_index+1}: {s.message}")
        
        return ScoringResult(
            total_score=total_score,
            max_score=max_score,
            step_scores=step_scores,
            dimension_scores=dim_scores,
            critical_result=critical_result,
            overall_feedback="; ".join(feedback_parts),
            confidence=full_verification.overall_score,
            breakdown="\n".join(breakdown_lines),
            weighted_breakdown="\n".join(weighted_lines)
        )
    
    def score_simple(
        self,
        student_answer: str,
        standard_answer: str,
        question_type: str = "choice"
    ) -> ScoringResult:
        """简单评分"""
        verification = self.verifier.verify_expression_equivalence(
            student_answer, standard_answer
        )
        
        if verification.verified:
            total_score = 100.0
            feedback = "回答正确"
        else:
            total_score = 0.0
            feedback = "回答错误"
        
        return ScoringResult(
            total_score=total_score,
            max_score=100.0,
            overall_feedback=feedback,
            confidence=1.0 if verification.verified else 0.5,
            breakdown=f"答案验证: {'通过' if verification.verified else '未通过'}"
        )


# ═══════════════════════════════════════════════
# 证明题评分器
# ═══════════════════════════════════════════════

class MathValidityScorer:
    """
    数学有效性评估器（替代路径相似性评估）

    核心理念：
    评分层真正评估的是"数学有效性"，而不是"路径相似性"。

    正确方法不同：
      - 标准解法：Taylor展开
      - 学生解法：L'Hospital法则
      - 如果数学正确：应满分

    这符合实际阅卷逻辑！
    """

    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
        self.verifier = get_verifier()

    def evaluate_math_validity(
        self,
        steps: List[Dict],
        student_result: str,
        standard_result: str
    ) -> Tuple[float, List[Dict]]:
        """
        评估数学有效性（不关心使用什么方法）

        Args:
            steps: 推导步骤列表
            student_result: 学生最终答案
            standard_result: 标准答案

        Returns:
            (有效性得分, 每步评估详情)
        """
        if not steps:
            return 0.0, []

        step_validations = []
        valid_steps = 0
        total_steps = len(steps)

        for i, step in enumerate(steps):
            if i == 0:
                from_output = step.get('output_state', '')
                to_input = step.get('output_state', '')
                operation = step.get('operation', 'start')
            else:
                from_output = steps[i-1].get('output_state', '')
                to_input = step.get('input_state', '')
                operation = step.get('operation', 'compute')

            # 验证步骤的数学正确性（不关心方法）
            transition_result = self.verifier.verify_step_transition(
                from_output, to_input, operation
            )

            # 识别步骤中使用的关键方法（用于反馈）
            methods_used = self._extract_methods_used(operation, step.get('output_state', ''))

            step_validations.append({
                "step_index": i,
                "is_valid": transition_result.verification.verified,
                "error_level": transition_result.verification.error_level,
                "methods_used": methods_used,
                "message": transition_result.verification.message
            })

            if transition_result.verification.verified:
                valid_steps += 1

        # 计算最终答案的正确性
        final_answer_valid = self.verifier.verify_expression_equivalence(
            student_result, standard_result
        ).verified

        # 计算数学有效性得分
        # 步骤有效性占70%，最终答案占30%
        step_validity_score = (valid_steps / total_steps) * 100 * 0.7
        final_answer_score = 100 * 0.3 if final_answer_valid else 0

        total_validity_score = step_validity_score + final_answer_score

        return total_validity_score, step_validations

    def _extract_methods_used(self, operation: str, output_state: str) -> List[str]:
        """提取步骤中使用的方法"""
        text = (operation + " " + output_state).lower()
        methods = []

        for step_type, patterns in CRITICAL_STEP_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    methods.append(step_type.value)
                    break

        return methods

    def compare_methods(
        self,
        student_methods: List[str],
        standard_methods: List[str]
    ) -> Dict[str, Any]:
        """
        比较学生使用的方法和标准方法

        注意：这不是检查"是否匹配"，而是检查"是否都正确"

        Returns:
            {
                "is_valid": True/False,  # 学生方法是否数学正确
                "student_methods": [...],
                "standard_methods": [...],
                "feedback": "两种方法都正确" / "学生方法正确但与标准不同"
            }
        """
        # 检查学生方法是否包含有效方法
        has_valid_method = len(student_methods) > 0

        # 检查学生方法和标准方法是否完全不同
        method_overlap = set(student_methods) & set(standard_methods)
        methods_differ = len(method_overlap) == 0 and len(student_methods) > 0

        return {
            "is_valid": has_valid_method,
            "student_methods": student_methods,
            "standard_methods": standard_methods,
            "methods_differ": methods_differ,
            "feedback": "两种方法都正确" if has_valid_method else "未使用有效方法"
        }


class ProofScorer:
    """
    证明题评分器
    
    证明题评分结构：
      - 逻辑链完整性 40%
      - 关键定理正确性 30%
      - 证明结构 20%
      - 最终结论 10%
    
    核心思想：证明题绝不能只看结果，必须重视逻辑评分
    """
    
    def __init__(self, config: ProofScoringConfig = None):
        self.config = config or ProofScoringConfig()
        self.verifier = get_verifier()
    
    def score_proof(
        self,
        proof_steps: List[Dict],
        theorems_used: List[str],
        expected_theorems: List[str],
        proof_structure: str,
        final_conclusion: str,
        standard_conclusion: str
    ) -> ProofScoringResult:
        """
        评分证明题
        
        Args:
            proof_steps: 证明步骤列表
            theorems_used: 使用的定理列表
            expected_theorems: 期望使用的定理列表
            proof_structure: 证明结构类型 (direct/contradiction/induction等)
            final_conclusion: 最终结论
            standard_conclusion: 标准结论
        """
        # 1. 评分逻辑链完整性 (40%)
        logic_chain_score, logic_analysis = self._score_logic_chain(proof_steps)
        
        # 2. 评分关键定理正确性 (30%)
        theorem_score, theorem_details = self._score_theorem_correctness(
            theorems_used, expected_theorems
        )
        
        # 3. 评分证明结构 (20%)
        structure_score = self._score_proof_structure(proof_structure)
        
        # 4. 评分最终结论 (10%)
        conclusion_score = self._score_final_conclusion(final_conclusion, standard_conclusion)
        
        # 计算加权总分
        weighted_scores = [
            logic_chain_score * self.config.logic_chain_weight,
            theorem_score * self.config.theorem_weight,
            structure_score * self.config.structure_weight,
            conclusion_score * self.config.conclusion_weight,
        ]
        total_score = sum(weighted_scores)
        
        # 创建维度得分
        dimension_scores = [
            ProofDimensionScore(
                dimension=ProofScoreDimension.LOGIC_CHAIN,
                score=logic_chain_score,
                max_score=self.config.logic_chain_full_score,
                type=ScoreType.FULL if logic_chain_score >= 90 else ScoreType.PARTIAL,
                reason=f"逻辑链完整性: {logic_analysis.connected_steps}/{logic_analysis.total_steps}步连接",
                details=[{"gaps": logic_analysis.logic_gaps, "missing": logic_analysis.missing_conditions}]
            ),
            ProofDimensionScore(
                dimension=ProofScoreDimension.THEOREM_CORRECTNESS,
                score=theorem_score,
                max_score=self.config.theorem_full_score,
                type=ScoreType.FULL if theorem_score >= 90 else ScoreType.PARTIAL,
                reason=f"定理使用: {len(theorems_used)}/{len(expected_theorems)}个",
                details=theorem_details
            ),
            ProofDimensionScore(
                dimension=ProofScoreDimension.PROOF_STRUCTURE,
                score=structure_score,
                max_score=self.config.structure_full_score,
                type=ScoreType.FULL if structure_score >= 90 else ScoreType.PARTIAL,
                reason=f"证明结构: {proof_structure}",
                details=[{"structure_type": proof_structure}]
            ),
            ProofDimensionScore(
                dimension=ProofScoreDimension.FINAL_CONCLUSION,
                score=conclusion_score,
                max_score=self.config.conclusion_full_score,
                type=ScoreType.FULL if conclusion_score >= 90 else ScoreType.PARTIAL,
                reason="结论正确" if conclusion_score >= 90 else "结论不完整",
                details=[{"conclusion_match": conclusion_score >= 90}]
            ),
        ]
        
        # 生成评分明细
        breakdown = self._generate_breakdown(
            weighted_scores, total_score, logic_analysis, theorem_details
        )
        
        # 生成反馈
        feedback_parts = []
        if logic_analysis.logic_gaps:
            feedback_parts.append(f"逻辑跳跃{len(logic_analysis.logic_gaps)}处")
        if logic_analysis.missing_conditions:
            feedback_parts.append(f"缺失条件{len(logic_analysis.missing_conditions)}个")
        if theorem_score < 90:
            feedback_parts.append("定理使用不当")
        if conclusion_score >= 90:
            feedback_parts.append("结论正确")
        
        return ProofScoringResult(
            total_score=total_score,
            max_score=100.0,
            dimension_scores=dimension_scores,
            logic_chain_analysis=logic_analysis,
            theorem_usage=theorem_details,
            proof_structure_score=structure_score,
            overall_feedback="; ".join(feedback_parts) if feedback_parts else "证明完整正确",
            breakdown=breakdown
        )
    
    def _score_logic_chain(self, steps: List[Dict]) -> Tuple[float, LogicChainAnalysis]:
        """评分逻辑链完整性"""
        if not steps:
            return 0.0, LogicChainAnalysis()
        
        total_steps = len(steps)
        connected_steps = 0
        logic_gaps = []
        missing_conditions = []
        
        # 检查步骤之间的逻辑连接
        for i in range(1, len(steps)):
            prev_output = steps[i-1].get('output_state', '')
            curr_input = steps[i].get('input_state', '')
            operation = steps[i].get('operation', '')
            
            # 检查是否有逻辑跳跃
            if prev_output and curr_input:
                if self._check_logical_connection(prev_output, curr_input, operation):
                    connected_steps += 1
                else:
                    logic_gaps.append(i)
            
            # 检查是否缺失条件
            if self._check_missing_condition(steps[i]):
                missing_conditions.append(f"步骤{i+1}缺失条件")
        
        # 计算完整性得分
        base_score = (connected_steps / max(total_steps - 1, 1)) * 100
        gap_penalty = len(logic_gaps) * self.config.gap_penalty * 100
        condition_penalty = len(missing_conditions) * self.config.missing_condition_penalty * 100
        
        completeness_score = max(0, base_score - gap_penalty - condition_penalty)
        
        analysis = LogicChainAnalysis(
            total_steps=total_steps,
            connected_steps=connected_steps,
            logic_gaps=logic_gaps,
            missing_conditions=missing_conditions,
            completeness_score=completeness_score / 100
        )
        
        return completeness_score, analysis
    
    def _check_logical_connection(self, prev_output: str, curr_input: str, operation: str) -> bool:
        """检查两个步骤之间是否有逻辑连接"""
        # 简化检查：看前一步输出是否出现在当前步输入中
        if prev_output in curr_input or curr_input in prev_output:
            return True
        # 检查是否有推导关键词
        derivation_keywords = ['therefore', 'so', 'hence', 'thus', '所以', '因此', '由']
        if any(kw in operation.lower() for kw in derivation_keywords):
            return True
        return False
    
    def _check_missing_condition(self, step: Dict) -> bool:
        """检查步骤是否缺失条件"""
        # 简化检查：如果步骤使用了定理但没有说明条件
        operation = step.get('operation', '')
        theorem_keywords = ['theorem', 'lemma', '定理', '引理']
        condition_keywords = ['if', 'when', '假设', '设', 'given']
        
        has_theorem = any(kw in operation.lower() for kw in theorem_keywords)
        has_condition = any(kw in operation.lower() for kw in condition_keywords)
        
        return has_theorem and not has_condition
    
    def _score_theorem_correctness(
        self, 
        theorems_used: List[str], 
        expected_theorems: List[str]
    ) -> Tuple[float, List[Dict]]:
        """评分关键定理正确性"""
        if not expected_theorems:
            return self.config.theorem_full_score, []
        
        theorem_details = []
        correct_count = 0
        
        for expected in expected_theorems:
            found = False
            for used in theorems_used:
                if self._check_theorem_match(used, expected):
                    found = True
                    correct_count += 1
                    theorem_details.append({
                        "theorem": expected,
                        "status": "correct",
                        "used_as": used
                    })
                    break
            
            if not found:
                theorem_details.append({
                    "theorem": expected,
                    "status": "missing",
                    "used_as": None
                })
        
        # 检查是否使用了错误的定理
        wrong_theorems = []
        for used in theorems_used:
            is_expected = any(
                self._check_theorem_match(used, exp) for exp in expected_theorems
            )
            if not is_expected:
                wrong_theorems.append(used)
                theorem_details.append({
                    "theorem": used,
                    "status": "wrong",
                    "expected": expected_theorems
                })
        
        # 计算得分
        base_score = (correct_count / len(expected_theorems)) * 100
        wrong_penalty = len(wrong_theorems) * self.config.wrong_theorem_penalty * 100
        missing_penalty = (len(expected_theorems) - correct_count) * self.config.missing_theorem_penalty * 100
        
        score = max(0, base_score - wrong_penalty - missing_penalty)
        
        return score, theorem_details
    
    def _check_theorem_match(self, used: str, expected: str) -> bool:
        """检查使用的定理是否匹配期望的定理"""
        # 简化检查：字符串相似度
        used_lower = used.lower()
        expected_lower = expected.lower()
        
        if expected_lower in used_lower or used_lower in expected_lower:
            return True
        
        # 检查关键词
        expected_keywords = expected_lower.split()
        match_count = sum(1 for kw in expected_keywords if kw in used_lower)
        
        return match_count >= len(expected_keywords) * 0.5
    
    def _score_proof_structure(self, structure_type: str) -> float:
        """评分证明结构"""
        structure_score = self.config.structure_types.get(structure_type, 0.8)
        return self.config.structure_full_score * structure_score
    
    def _score_final_conclusion(self, conclusion: str, standard: str) -> float:
        """评分最终结论"""
        if not conclusion or not standard:
            return 0.0
        
        # 使用验证器检查结论等价性
        verification = self.verifier.verify_expression_equivalence(conclusion, standard)
        
        if verification.verified:
            return self.config.conclusion_full_score
        else:
            # 部分正确
            return self.config.conclusion_full_score * self.config.partial_conclusion_score
    
    def _generate_breakdown(
        self, 
        weighted_scores: List[float], 
        total_score: float,
        logic_analysis: LogicChainAnalysis,
        theorem_details: List[Dict]
    ) -> str:
        """生成评分明细"""
        lines = []
        lines.append("=" * 60)
        lines.append("【证明题评分明细】")
        lines.append("=" * 60)
        lines.append(f"逻辑链完整性: {weighted_scores[0]:.1f}/40 ({logic_analysis.completeness_score*100:.0f}%)")
        lines.append(f"关键定理正确性: {weighted_scores[1]:.1f}/30")
        lines.append(f"证明结构: {weighted_scores[2]:.1f}/20")
        lines.append(f"最终结论: {weighted_scores[3]:.1f}/10")
        lines.append("-" * 60)
        lines.append(f"总  分: {total_score:.1f}/100")
        
        if logic_analysis.logic_gaps:
            lines.append(f"\n逻辑跳跃位置: 步骤{logic_analysis.logic_gaps}")
        if logic_analysis.missing_conditions:
            lines.append(f"缺失条件: {logic_analysis.missing_conditions}")
        
        return "\n".join(lines)


def get_proof_scorer(config: ProofScoringConfig = None) -> ProofScorer:
    """获取证明题评分器"""
    return ProofScorer(config)


def get_scorer(config: ScoringConfig = None) -> UnifiedScorer:
    """获取统一评分器"""
    return UnifiedScorer(config)


def get_validity_scorer(config: ScoringConfig = None) -> MathValidityScorer:
    """获取数学有效性评估器（支持正确方法不同）"""
    return MathValidityScorer(config)


# ═══════════════════════════════════════════════
# 示例用法
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    scorer = get_scorer()
    
    # 示例: Taylor展开错误，后续步骤正确
    # 按照加权评分，Taylor展开是关键步骤(weight=0.5)
    # 如果Taylor错了，后续步骤得分受限
    steps = [
        {"output_state": "f(x) = e^x", "operation": "start"},
        {"output_state": "Taylor展开错误结果", "operation": "taylor"},  # 关键步骤错误
        {"output_state": "化简结果", "operation": "simplify"},
        {"output_state": "最终答案", "operation": "compute"},
    ]
    
    result = scorer.score_derivation(
        steps=steps,
        student_result="1",
        standard_result="1",
        expected_critical_steps=[CriticalStepType.TAYLOR_EXPANSION],
        optimal_methods=[CriticalStepType.TAYLOR_EXPANSION]
    )
    
    print(result.breakdown)
    print(result.weighted_breakdown)
    print(f"\n反馈: {result.overall_feedback}")
