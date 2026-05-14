"""common_enums.py — 通用枚举定义

所有模块统一使用的枚举值，避免重复定义。

这个文件是整个评分系统的核心枚举库：
- ErrorLevel: 错误级别
- OperationType: 操作类型（合并了CriticalStepType和Op）
- StepStatus: 步骤状态
- ProofStrategy: 证明策略
- NodeType: DAG节点类型
- EdgeType: DAG边类型

使用方式：
  from common_enums import ErrorLevel, OperationType, StepStatus
"""

from enum import Enum
from typing import List, Dict


# ═══════════════════════════════════════════════
# 错误级别定义（三级错误扣分系统）
# ═══════════════════════════════════════════════

class ErrorLevel(Enum):
    """
    错误级别枚举（三级错误扣分系统）

    一级错误（重）Conceptual Error
      - 用错定理、方法错误、推导方向错误
      - 扣分：30~70%

    二级错误（中）Algebraic Error
      - 化简错误、代数运算错误
      - 扣分：5~20%

    三级错误（轻）Arithmetic Error
      - +/- 算错、数值计算错误
      - 扣分：1~5%
    """
    CORRECT = -1           # 完全正确
    LEVEL_0 = 0            # 未执行任何数学计算
    LEVEL_1 = 1            # 三级错误（轻）- Arithmetic Error
    LEVEL_2 = 2            # 二级错误（中）- Algebraic Error
    LEVEL_3 = 3            # 一级错误（重）- Conceptual Error
    WARNING = 4             # 警告（不影响正确性）

    @property
    def label(self) -> str:
        return ERROR_LEVEL_LABELS.get(self, "未知")

    @property
    def description(self) -> str:
        return ERROR_LEVEL_DESCRIPTIONS.get(self, "未知")

    @property
    def is_error(self) -> bool:
        return self.value >= 1

    @property
    def error_tier(self) -> str:
        """返回错误等级名称"""
        if self == ErrorLevel.LEVEL_1:
            return "三级错误（轻）"
        elif self == ErrorLevel.LEVEL_2:
            return "二级错误（中）"
        elif self == ErrorLevel.LEVEL_3:
            return "一级错误（重）"
        return ""


ERROR_LEVEL_LABELS: Dict[ErrorLevel, str] = {
    ErrorLevel.CORRECT: "正确",
    ErrorLevel.LEVEL_0: "解题路径缺失",
    ErrorLevel.LEVEL_1: "三级错误（轻）- 计算错误",
    ErrorLevel.LEVEL_2: "二级错误（中）- 代数错误",
    ErrorLevel.LEVEL_3: "一级错误（重）- 概念错误",
    ErrorLevel.WARNING: "警告",
}

ERROR_LEVEL_DESCRIPTIONS: Dict[ErrorLevel, str] = {
    ErrorLevel.CORRECT: "完全正确",
    ErrorLevel.LEVEL_0: "未执行任何数学计算",
    ErrorLevel.LEVEL_1: "Arithmetic Error: +/- 算错、数值计算错误",
    ErrorLevel.LEVEL_2: "Algebraic Error: 化简错误、代数运算错误",
    ErrorLevel.LEVEL_3: "Conceptual Error: 用错定理、方法错误、推导方向错误",
    ErrorLevel.WARNING: "警告（不影响正确性）",
}


# ═══════════════════════════════════════════════
# 操作类型定义（统一枚举）
# ═══════════════════════════════════════════════

class OperationType(Enum):
    """
    统一操作类型枚举

    合并了：
    - CriticalStepType (scoring_layer)
    - Op (operations.py)
    - OperationSemantic (solution_question_layer)

    每个操作都有明确的数学语义。
    """

    # ===== 基础操作 =====
    START = "start"                    # 起始：题目输入
    COMPUTE = "compute"                # 计算：直接计算
    SIMPLIFY = "simplify"              # 化简：代数化简
    REWRITE = "rewrite"                 # 重写：等价变形

    # ===== 微积分操作 =====
    DIFFERENTIATE = "differentiate"     # 求导
    INTEGRATE = "integrate"            # 积分
    INTEGRATION_BY_PARTS = "integration_by_parts"  # 分部积分
    SUBSTITUTION = "substitution"       # 换元
    CHANGE_OF_VARIABLES = "change_of_variables"  # 变量替换（换元）
    PARTIAL_DIFF = "partial_diff"      # 偏导数

    # ===== 极限操作 =====
    TAYLOR_EXPANSION = "taylor_expansion"  # 泰勒展开
    L_HOSPITAL = "l_hospital"          # 洛必达
    LIMIT_COMPUTE = "limit_compute"     # 极限计算

    # ===== 方程操作 =====
    SOLVE_EQUATION = "solve_equation"   # 解方程
    SOLVE_SYSTEM = "solve_system"       # 解方程组
    FACTOR = "factor"                   # 因式分解
    ROOTS = "roots"                    # 求根

    # ===== 证明操作 =====
    ASSUME = "assume"                   # 假设
    DERIVE = "derive"                   # 推导
    APPLY_THEOREM = "apply_theorem"     # 应用定理
    CONSTRUCT_AUXILIARY = "construct_auxiliary"  # 构造辅助函数
    PROOF_BY_CONTRADICTION = "proof_by_contradiction"  # 反证法
    PROOF_BY_INDUCTION = "proof_by_induction"  # 数学归纳法

    # ===== 中值定理 =====
    MEAN_VALUE_THEOREM = "mean_value_theorem"  # 中值定理
    LAGRANGE = "lagrange"              # 拉格朗日中值定理
    ROLLE = "rolle"                    # 罗尔定理
    CAUCHY = "cauchy"                  # 柯西中值定理

    # ===== 级数操作 =====
    SERIES_EXPANSION = "series_expansion"  # 级数展开
    SUM_SERIES = "sum_series"          # 级数求和
    CONVERGENCE_TEST = "convergence_test"  # 收敛性判别

    # ===== 线性代数操作 =====
    MATRIX_OP = "matrix_op"            # 矩阵运算
    ROW_REDUCE = "row_reduce"          # 行简化
    EIGEN_SOLVE = "eigen_solve"        # 特征值问题
    DETERMINANT = "determinant"        # 行列式
    DIAGONALIZE = "diagonalize"        # 对角化
    CHARACTERISTIC_EQUATION = "characteristic_equation"  # 特征方程

    # ===== 不等式操作 =====
    INEQUALITY_COMPARE = "inequality_compare"  # 不等式比较
    JENSEN = "jensen"                  # Jensen不等式

    # ===== 概率统计 =====
    PROBABILITY_CALC = "probability_calc"  # 概率计算
    EXPECTATION = "expectation"        # 期望
    MLE_DERIVE = "mle_derive"          # 极大似然估计
    MOMENT_ESTIMATE = "moment_estimate"  # 矩估计
    HYPOTHESIS_TEST = "hypothesis_test"  # 假设检验

    # ===== 特殊操作 =====
    OBSERVATION = "observation"         # 观察/注意到
    EQUIVALENT_TRANSFORM = "equivalent_transform"  # 等价变换
    DEFINITION = "definition"           # 定义
    SEPARATION_OF_VARIABLES = "separation_of_variables"  # 分离变量

    # ===== 通用操作 =====
    FINAL_ANSWER = "final_answer"      # 最终答案
    INDUCTION_STEP = "induction_step"   # 归纳步骤
    OTHER = "other"                    # 其他


OPERATION_PATTERNS: Dict[OperationType, List[str]] = {
    OperationType.TAYLOR_EXPANSION: [
        "taylor", "泰勒", "展开", "级数展开", "麦克劳林", "mclaurin", "麦克劳林展开"
    ],
    OperationType.SUBSTITUTION: [
        "换元", "变量替换", "substitution", "令", "设", "let", "变量换元"
    ],
    OperationType.CONSTRUCT_AUXILIARY: [
        "辅助函数", "构造函数", "construct", "define", "设函数", "构造"
    ],
    OperationType.CHARACTERISTIC_EQUATION: [
        "特征方程", "特征根", "characteristic", "齐次方程", "通解"
    ],
    OperationType.INTEGRATION_BY_PARTS: [
        "分部积分", "integration by parts", "uv积分"
    ],
    OperationType.L_HOSPITAL: [
        "洛必达", "洛必达法则", "l_hospital", "0/0", "∞/∞"
    ],
    OperationType.LAGRANGE: [
        "拉格朗日", "拉格朗日中值定理", "lagrange"
    ],
    OperationType.ROLLE: [
        "罗尔", "Rolle", "罗尔定理"
    ],
    OperationType.CAUCHY: [
        "柯西", "cauchy", "柯西中值定理"
    ],
    OperationType.MEAN_VALUE_THEOREM: [
        "中值定理", "mean value"
    ],
    OperationType.SEPARATION_OF_VARIABLES: [
        "分离变量", "separation of variables"
    ],
    OperationType.DIFFERENTIATE: [
        "求导", "微分", "diff", "derivative", "differentiate"
    ],
    OperationType.INTEGRATE: [
        "积分", "integral", "integrate"
    ],
    OperationType.SOLVE_EQUATION: [
        "解方程", "solve", "求解"
    ],
    OperationType.LIMIT_COMPUTE: [
        "极限", "limit"
    ],
    OperationType.PROOF_BY_CONTRADICTION: [
        "反证法", "假设", "矛盾", "若不然", "contradiction"
    ],
    OperationType.PROOF_BY_INDUCTION: [
        "归纳法", "数学归纳法", "induction", "假设当n=k"
    ],
    OperationType.SERIES_EXPANSION: [
        "级数展开", "展开成级数"
    ],
}


# ═══════════════════════════════════════════════
# 步骤状态
# ═══════════════════════════════════════════════

class StepStatus(Enum):
    """步骤状态"""
    CORRECT = "correct"           # 正确
    PARTIAL = "partial"           # 部分正确
    WRONG = "wrong"              # 错误
    MISSING = "missing"          # 缺失


STEP_STATUS_LABELS: Dict[StepStatus, str] = {
    StepStatus.CORRECT: "正确",
    StepStatus.PARTIAL: "部分正确",
    StepStatus.WRONG: "错误",
    StepStatus.MISSING: "缺失",
}


# ═══════════════════════════════════════════════
# 证明策略
# ═══════════════════════════════════════════════

class ProofStrategy(Enum):
    """证明策略"""
    DIRECT = "direct"                    # 直接证明
    CONTRADICTION = "contradiction"       # 反证法
    INDUCTION = "induction"               # 数学归纳法
    CONSTRUCT = "construct"               # 构造法
    EQUIVALENCE = "equivalence"           # 等价变换
    ANALYSIER = "analysier"               # 分析法
    SYNTHESIS = "synthesis"               # 综合法
    FORWARD = "forward"                   # 正向证明
    BACKWARD = "backward"                 # 逆向证明


PROOF_STRATEGY_PATTERNS: Dict[ProofStrategy, List[str]] = {
    ProofStrategy.DIRECT: ["直接证明", "直接得", "可得", "因此", "所以", "于是"],
    ProofStrategy.CONTRADICTION: ["反证法", "假设", "矛盾", "若不然", "假设不成立"],
    ProofStrategy.INDUCTION: ["归纳法", "数学归纳法", "假设当n=k时", "验证n=1"],
    ProofStrategy.CONSTRUCT: ["构造", "构造辅助函数", "构造函数", "构造序列"],
    ProofStrategy.EQUIVALENCE: ["等价", "充要条件", "当且仅当", "iff"],
    ProofStrategy.ANALYSIER: ["分析法", "要证", "只需证", "等价于"],
    ProofStrategy.SYNTHESIS: ["综合法", "由已知", "因为", "由题设"],
}


# ═══════════════════════════════════════════════
# DAG节点和边类型
# ═══════════════════════════════════════════════

class NodeType(Enum):
    """推理图节点类型"""
    PREMISE = "premise"           # 前提条件
    EXPRESSION = "expression"     # 表达式
    OPERATION = "operation"       # 操作
    CONCLUSION = "conclusion"     # 结论
    ASSUMPTION = "assumption"     # 假设
    GOAL = "goal"                 # 目标
    ERROR = "error"               # 错误节点


class EdgeType(Enum):
    """推理图边类型"""
    DEPENDS_ON = "depends_on"     # 依赖关系
    DERIVES_FROM = "derives_from" # 推导关系
    INPUT_TO = "input_to"         # 输入关系
    OUTPUT_FROM = "output_from"   # 输出关系
    ASSUMES = "assumes"           # 假设关系


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def recognize_operation(text: str) -> OperationType:
    """根据文本识别操作类型"""
    text_lower = text.lower()
    for op_type, patterns in OPERATION_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return op_type
    return OperationType.OTHER


def recognize_proof_strategy(text: str) -> tuple[ProofStrategy, float]:
    """识别证明策略"""
    text_lower = text.lower()
    scores = {}

    for strategy, patterns in PROOF_STRATEGY_PATTERNS.items():
        score = sum(1 for p in patterns if p.lower() in text_lower)
        if score > 0:
            scores[strategy] = score

    if not scores:
        return ProofStrategy.DIRECT, 0.5

    best = max(scores.items(), key=lambda x: x[1])
    confidence = min(best[1] / 3, 1.0)
    return best[0], confidence


# ═══════════════════════════════════════════════
# 兼容性别名（废弃警告）
# ═══════════════════════════════════════════════

# 这些别名用于向后兼容，旧代码可以使用旧名称
CriticalStepType = OperationType
ProofStepStatus = StepStatus
GradingErrorLevel = ErrorLevel
