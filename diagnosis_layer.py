"""diagnosis_layer.py — 诊断层 (Diagnosis Layer)

负责：错在哪里

错误类型：
  - 概念错误 (Conceptual Error)
  - 运算错误 (Algebraic Error)
  - 推理断裂 (Logical Gap)
  - 方法错误 (Method Error)

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                   Diagnosis Layer                              │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │ConceptDiagnose│  │AlgebraDiagnose│ │LogicDiagnose  │     │
  │  │   概念诊断   │  │   运算诊断   │  │   推理诊断   │     │
  │  └──────────────┘  └──────────────┘  └──────────────┘     │
  │                           │                                   │
  │                    UnifiedDiagnoser                           │
  │                       统一诊断入口                            │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses_json import dataclass_json


# ═══════════════════════════════════════════════
# 错误类型定义
# ═══════════════════════════════════════════════

class DiagnosisErrorType(Enum):
    """
    错误类型枚举

    一级错误（重）Conceptual Error
      - 用错定理
      - 方法错误
      - 推导方向错误

    二级错误（中）Algebraic Error
      - 化简错误
      - 代数运算错误

    三级错误（轻）Arithmetic Error
      - +/- 算错
      - 数值计算错误
    """
    CORRECT = "correct"                    # 正确
    CONCEPTUAL_ERROR = "conceptual_error"  # 概念错误（一级）
    ALGEBRAIC_ERROR = "algebraic_error"    # 运算错误（二级）
    ARITHMETIC_ERROR = "arithmetic_error"  # 算术错误（三级）
    LOGICAL_GAP = "logical_gap"            # 推理断裂
    METHOD_ERROR = "method_error"          # 方法错误
    MISSING_STEP = "missing_step"          # 缺失步骤
    UNKNOWN = "unknown"                    # 未知错误


# ═══════════════════════════════════════════════
# 诊断结果定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class DiagnosisResult:
    """诊断结果"""
    error_type: DiagnosisErrorType
    severity: str                    # "一级(重)" / "二级(中)" / "三级(轻)"
    location: str                    # 错误位置
    description: str                  # 错误描述
    suggestion: str                  # 改进建议
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass_json
@dataclass
class DiagnosisReport:
    """完整诊断报告"""
    total_steps: int = 0
    correct_steps: int = 0
    error_count: int = 0
    diagnoses: List[DiagnosisResult] = field(default_factory=list)
    summary: str = ""                # 诊断摘要
    improvement_suggestions: List[str] = field(default_factory=list)
    severity_distribution: Dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════
# 概念错误诊断器
# ═══════════════════════════════════════════════

class ConceptualErrorDiagnoser:
    """
    概念错误诊断器

    检测：
      - 用错定理
      - 方法错误
      - 推导方向错误
      - 条件缺失
    """

    # 常见定理误用模式
    THEOREM_ERROR_PATTERNS = {
        "l'hospital": {
            "wrong_usage": ["直接代入", "分子分母同除", "洛必达法则不适用"],
            "conditions": ["0/0型", "∞/∞型", "分子分母可导"],
            "suggestion": "洛必达法则要求分子分母在邻域内可导，且极限存在"
        },
        "taylor": {
            "wrong_usage": ["展开阶数不足", "展开点错误", "余项忽略"],
            "conditions": ["函数可展开", "阶数选择合理"],
            "suggestion": "泰勒展开需要选择合适的阶数，确保余项可以忽略"
        },
        "mean_value": {
            "wrong_usage": ["条件不满足", "中值点位置错误"],
            "conditions": ["函数连续", "函数可导", "区间端点"],
            "suggestion": "拉格朗日中值定理要求函数在闭区间连续，开区间可导"
        },
        "integration": {
            "wrong_usage": ["积分上下限错误", "分部积分选择错误", "换元不彻底"],
            "conditions": ["被积函数可积", "换元可逆"],
            "suggestion": "换元积分时，需要同步换元积分上下限"
        }
    }

    @classmethod
    def diagnose(cls, operation: str, output_state: str, expected: str = None) -> Optional[DiagnosisResult]:
        """诊断是否存在概念错误"""
        text = (operation + " " + output_state).lower()

        for theorem, info in cls.THEOREM_ERROR_PATTERNS.items():
            if theorem in text:
                for wrong_pattern in info["wrong_usage"]:
                    if wrong_pattern.lower() in text:
                        return DiagnosisResult(
                            error_type=DiagnosisErrorType.CONCEPTUAL_ERROR,
                            severity="一级(重)",
                            location=f"操作: {operation}",
                            description=f"使用了{wrong_pattern}，{theorem}定理使用不当",
                            suggestion=info["suggestion"],
                            details={"theorem": theorem, "wrong_pattern": wrong_pattern}
                        )

                if expected:
                    expected_lower = expected.lower()
                    if theorem not in expected_lower and any(
                        t in expected_lower for t in cls.THEOREM_ERROR_PATTERNS.keys()
                    ):
                        return DiagnosisResult(
                            error_type=DiagnosisErrorType.CONCEPTUAL_ERROR,
                            severity="一级(重)",
                            location=f"操作: {operation}",
                            description=f"使用了{information['theorem']}，但期望使用其他方法",
                            suggestion="请确认题目要求使用的方法",
                            details={"expected": expected, "actual": theorem}
                        )

        return None

    @classmethod
    def check_wrong_theorem(cls, used_theorems: List[str], expected_theorems: List[str]) -> List[DiagnosisResult]:
        """检查是否用错定理"""
        diagnoses = []

        for used in used_theorems:
            is_wrong = True
            for expected in expected_theorems:
                if cls._theorem_similar(used, expected):
                    is_wrong = False
                    break

            if is_wrong:
                diagnoses.append(DiagnosisResult(
                    error_type=DiagnosisErrorType.CONCEPTUAL_ERROR,
                    severity="一级(重)",
                    location=f"定理: {used}",
                    description=f"使用了未预期的定理: {used}",
                    suggestion="请确认是否应该使用其他定理",
                    details={"used": used, "expected": expected_theorems}
                ))

        return diagnoses

    @classmethod
    def _theorem_similar(cls, t1: str, t2: str) -> bool:
        """判断两个定理是否相似"""
        t1_lower = t1.lower()
        t2_lower = t2.lower()

        if t1_lower in t2_lower or t2_lower in t1_lower:
            return True

        keywords1 = set(t1_lower.split())
        keywords2 = set(t2_lower.split())
        overlap = keywords1 & keywords2

        return len(overlap) >= min(len(keywords1), len(keywords2)) * 0.5


# ═══════════════════════════════════════════════
# 运算错误诊断器
# ═══════════════════════════════════════════════

class AlgebraicErrorDiagnoser:
    """
    运算错误诊断器

    检测：
      - 化简错误
      - 代数运算错误
      - 符号错误
      - 移项错误
    """

    # 常见运算错误模式
    ALGEBRAIC_ERROR_PATTERNS = {
        "simplify_error": {
            "patterns": ["合并同类项错误", "化简不彻底", "约分错误"],
            "suggestion": "检查化简步骤，确保每一步都正确"
        },
        "sign_error": {
            "patterns": ["负号丢失", "负号错误", "符号改变"],
            "suggestion": "注意负号的传递和分配"
        },
        "parentheses_error": {
            "patterns": ["去括号错误", "添括号错误", "分配律错误"],
            "suggestion": "注意括号的分配和去括号规则"
        },
        "fraction_error": {
            "patterns": ["分式运算错误", "分子分母颠倒", "通分错误"],
            "suggestion": "分式运算时注意分子分母同时变化"
        },
        "exponent_error": {
            "patterns": ["指数运算错误", "幂函数求导错误", "对数运算错误"],
            "suggestion": "注意指数和对数的运算规则"
        }
    }

    @classmethod
    def diagnose(cls, operation: str, output_state: str, input_state: str) -> Optional[DiagnosisResult]:
        """诊断是否存在运算错误"""
        text = (operation + " " + output_state + " " + input_state).lower()

        for error_type, info in cls.ALGEBRAIC_ERROR_PATTERNS.items():
            for pattern in info["patterns"]:
                if pattern.lower() in text:
                    return DiagnosisResult(
                        error_type=DiagnosisErrorType.ALGEBRAIC_ERROR,
                        severity="二级(中)",
                        location=f"操作: {operation}",
                        description=f"可能存在{pattern}",
                        suggestion=info["suggestion"],
                        details={"error_type": error_type, "pattern": pattern}
                    )

        return None

    @classmethod
    def check_equation_balance(cls, left_side: str, right_side: str, operation: str) -> Optional[DiagnosisResult]:
        """检查等式两边是否平衡"""
        if "=" in left_side or "=" in right_side:
            if operation in ["移项", "变形", "化简"]:
                if not cls._sides_balanced(left_side, right_side):
                    return DiagnosisResult(
                        error_type=DiagnosisErrorType.ALGEBRAIC_ERROR,
                        severity="二级(中)",
                        location=f"等式变形: {left_side} = {right_side}",
                        description="等式两边不平衡",
                        suggestion="检查移项和化简过程，确保等式性质成立",
                        details={"left": left_side, "right": right_side}
                    )
        return None

    @classmethod
    def _sides_balanced(cls, left: str, right: str) -> bool:
        """简单检查两边是否平衡（简化版）"""
        left_clean = left.replace(" ", "").replace("-", "")
        right_clean = right.replace(" ", "").replace("-", "")

        if left_clean == right_clean:
            return True

        left_terms = set(left_clean.split("+"))
        right_terms = set(right_clean.split("+"))

        return left_terms == right_terms


# ═══════════════════════════════════════════════
# 推理断裂诊断器
# ═══════════════════════════════════════════════

class LogicalGapDiagnoser:
    """
    推理断裂诊断器

    检测：
      - 逻辑跳跃
      - 步骤缺失
      - 条件缺失
      - 推导不连续
    """

    # 推导关键词
    DERIVATION_KEYWORDS = ["therefore", "thus", "hence", "so", "所以", "因此", "于是", "可得", "由"]
    GAP_KEYWORDS = ["直接", "显然", "易得", "易知", "显然可得"]

    @classmethod
    def diagnose(cls, steps: List[Dict], current_index: int) -> Optional[DiagnosisResult]:
        """诊断是否存在推理断裂"""
        if current_index == 0 or current_index >= len(steps):
            return None

        current_step = steps[current_index]
        prev_step = steps[current_index - 1]

        prev_output = prev_step.get('output_state', '')
        current_input = current_step.get('input_state', '')
        current_operation = current_step.get('operation', '')

        if not prev_output or not current_input:
            if any(kw in current_operation.lower() for kw in cls.DERIVATION_KEYWORDS):
                return DiagnosisResult(
                    error_type=DiagnosisErrorType.LOGICAL_GAP,
                    severity="一级(重)",
                    location=f"步骤{current_index}到步骤{current_index+1}",
                    description="推导过程跳跃，未说明中间步骤",
                    suggestion="请补充推导的中间步骤，使逻辑连贯",
                    details={"from": prev_output, "to": current_input}
                )

        if current_operation in cls.GAP_KEYWORDS:
            return DiagnosisResult(
                error_type=DiagnosisErrorType.LOGICAL_GAP,
                severity="一级(重)",
                location=f"步骤{current_index+1}",
                description="使用了'显然'等词汇掩盖了推导过程",
                suggestion="请详细写出推导过程，不要跳过步骤",
                details={"operation": current_operation}
            )

        if prev_output and current_input:
            if not cls._check_connection(prev_output, current_input):
                return DiagnosisResult(
                    error_type=DiagnosisErrorType.LOGICAL_GAP,
                    severity="二级(中)",
                    location=f"步骤{current_index}到步骤{current_index+1}",
                    description="前后步骤之间缺乏逻辑连接",
                    suggestion="请确保当前步骤的输入与前一步骤的输出有逻辑关联",
                    details={"previous_output": prev_output, "current_input": current_input}
                )

        return None

    @classmethod
    def check_missing_conditions(cls, step: Dict) -> Optional[DiagnosisResult]:
        """检查是否缺失条件"""
        operation = step.get('operation', '').lower()

        theorem_keywords = ['定理', '引理', 'theorem', 'lemma']
        condition_keywords = ['如果', '假设', 'given', 'if', 'when']

        has_theorem = any(kw in operation for kw in theorem_keywords)
        has_condition = any(kw in operation for kw in condition_keywords)

        if has_theorem and not has_condition:
            return DiagnosisResult(
                error_type=DiagnosisErrorType.LOGICAL_GAP,
                severity="二级(中)",
                location=f"步骤{step.get('step_index', '?')}",
                description="使用定理前未说明条件",
                suggestion="请在使用定理前先说明条件是否满足",
                details={"operation": operation}
            )

        return None

    @classmethod
    def _check_connection(cls, prev_output: str, current_input: str) -> bool:
        """检查前后步骤是否有逻辑连接"""
        if not prev_output or not current_input:
            return True

        if prev_output in current_input or current_input in prev_output:
            return True

        prev_clean = prev_output.lower().replace(" ", "")
        curr_clean = current_input.lower().replace(" ", "")

        common_chars = set(prev_clean) & set(curr_clean)
        return len(common_chars) >= min(len(prev_clean), len(curr_clean)) * 0.3


# ═══════════════════════════════════════════════
# 方法错误诊断器
# ═══════════════════════════════════════════════

class MethodErrorDiagnoser:
    """
    方法错误诊断器

    检测：
      - 方法选择错误
      - 方法不适用
      - 方法过于复杂
    """

    # 方法适用条件
    METHOD_SUITABILITY = {
        "l'hospital": {
            "suitable": ["0/0", "∞/∞", "极限", "limit"],
            "unsuitable": ["多项式", "离散", "不连续"],
            "suggestion": "洛必达法则只适用于0/0型或∞/∞型未定式"
        },
        "taylor": {
            "suitable": ["多项式逼近", "高阶近似", "误差估计"],
            "unsuitable": ["离散", "跳跃", "不可微"],
            "suggestion": "泰勒展开要求函数在该点有足够阶的导数"
        },
        "substitution": {
            "suitable": ["复合函数", "复杂表达式", "换元"],
            "unsuitable": ["简单表达式", "线性"],
            "suggestion": "换元法适用于复合函数或复杂表达式"
        },
        "integration_by_parts": {
            "suitable": ["乘积", "uv形式", "分部积分"],
            "unsuitable": ["单项", "简单分式"],
            "suggestion": "分部积分适用于两个函数相乘的形式"
        }
    }

    @classmethod
    def diagnose(cls, operation: str, output_state: str) -> Optional[DiagnosisResult]:
        """诊断是否存在方法错误"""
        text = (operation + " " + output_state).lower()

        for method, info in cls.METHOD_SUITABILITY.items():
            if method in text:
                unsuitable_found = any(uns in text for uns in info["unsuitable"])
                if unsuitable_found:
                    return DiagnosisResult(
                        error_type=DiagnosisErrorType.METHOD_ERROR,
                        severity="一级(重)",
                        location=f"操作: {operation}",
                        description=f"{method}方法可能不适用当前问题",
                        suggestion=info["suggestion"],
                        details={"method": method, "unsuitable": info["unsuitable"]}
                    )

        return None


# ═══════════════════════════════════════════════
# 统一诊断器
# ═══════════════════════════════════════════════

class UnifiedDiagnoser:
    """
    统一诊断器

    综合使用各种诊断器，给出完整的诊断报告
    """

    def __init__(self):
        self.concept_diagnoser = ConceptualErrorDiagnoser()
        self.algebra_diagnoser = AlgebraicErrorDiagnoser()
        self.logic_diagnoser = LogicalGapDiagnoser()
        self.method_diagnoser = MethodErrorDiagnoser()

    def diagnose_steps(
        self,
        steps: List[Dict],
        expected_methods: List[str] = None
    ) -> DiagnosisReport:
        """
        诊断所有步骤

        Args:
            steps: 步骤列表
            expected_methods: 期望使用的方法列表

        Returns:
            完整诊断报告
        """
        diagnoses = []
        correct_steps = 0

        for i, step in enumerate(steps):
            step_diagnoses = []

            if i == 0:
                from_output = step.get('output_state', '')
                to_input = step.get('output_state', '')
            else:
                from_output = steps[i-1].get('output_state', '')
                to_input = step.get('input_state', '')

            operation = step.get('operation', '')
            output_state = step.get('output_state', '')

            concept_result = self.concept_diagnoser.diagnose(
                operation, output_state
            )
            if concept_result:
                step_diagnoses.append(concept_result)

            algebra_result = self.algebra_diagnoser.diagnose(
                operation, output_state, to_input
            )
            if algebra_result:
                step_diagnoses.append(algebra_result)

            logic_result = self.logic_diagnoser.diagnose(steps, i)
            if logic_result:
                step_diagnoses.append(logic_result)

            missing_condition_result = self.logic_diagnoser.check_missing_conditions(step)
            if missing_condition_result:
                step_diagnoses.append(missing_condition_result)

            method_result = self.method_diagnoser.diagnose(operation, output_state)
            if method_result:
                step_diagnoses.append(method_result)

            if not step_diagnoses:
                correct_steps += 1
            else:
                for d in step_diagnoses:
                    d.location = f"步骤{i+1}: {d.location}"
                    diagnoses.append(d)

        severity_dist = self._count_severity(diagnoses)

        report = DiagnosisReport(
            total_steps=len(steps),
            correct_steps=correct_steps,
            error_count=len(diagnoses),
            diagnoses=diagnoses,
            summary=self._generate_summary(diagnoses, correct_steps, len(steps)),
            improvement_suggestions=self._generate_suggestions(diagnoses),
            severity_distribution=severity_dist
        )

        return report

    def diagnose_single_error(
        self,
        operation: str,
        output_state: str,
        input_state: str = "",
        expected: str = None
    ) -> List[DiagnosisResult]:
        """
        诊断单个错误

        Args:
            operation: 操作类型
            output_state: 输出状态
            input_state: 输入状态
            expected: 期望的方法

        Returns:
            诊断结果列表
        """
        diagnoses = []

        concept_result = self.concept_diagnoser.diagnose(operation, output_state, expected)
        if concept_result:
            diagnoses.append(concept_result)

        algebra_result = self.algebra_diagnoser.diagnose(operation, output_state, input_state)
        if algebra_result:
            diagnoses.append(algebra_result)

        logic_result = self.logic_diagnoser.diagnose([{"operation": operation, "output_state": output_state, "input_state": input_state}], 0)
        if logic_result:
            diagnoses.append(logic_result)

        method_result = self.method_diagnoser.diagnose(operation, output_state)
        if method_result:
            diagnoses.append(method_result)

        return diagnoses

    def _count_severity(self, diagnoses: List[DiagnosisResult]) -> Dict[str, int]:
        """统计错误严重程度分布"""
        dist = {"一级(重)": 0, "二级(中)": 0, "三级(轻)": 0}

        for d in diagnoses:
            if d.severity in dist:
                dist[d.severity] += 1

        return dist

    def _generate_summary(self, diagnoses: List[DiagnosisResult], correct: int, total: int) -> str:
        """生成诊断摘要"""
        if not diagnoses:
            return f"解题过程完整正确，共{total}个步骤，全部正确"

        error_types = {}
        for d in diagnoses:
            error_type = d.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1

        type_names = {
            "conceptual_error": "概念错误",
            "algebraic_error": "运算错误",
            "arithmetic_error": "算术错误",
            "logical_gap": "推理断裂",
            "method_error": "方法错误",
            "missing_step": "缺失步骤"
        }

        type_str = "、".join([f"{type_names.get(k, k)}({v}处)" for k, v in error_types.items()])

        return f"共发现{len(diagnoses)}处错误，其中：{type_str}"

    def _generate_suggestions(self, diagnoses: List[DiagnosisResult]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        conceptual_errors = [d for d in diagnoses if d.error_type == DiagnosisErrorType.CONCEPTUAL_ERROR]
        if conceptual_errors:
            suggestions.append("概念错误：请重新理解相关定理和概念，确保条件和使用方法正确")

        algebraic_errors = [d for d in diagnoses if d.error_type == DiagnosisErrorType.ALGEBRAIC_ERROR]
        if algebraic_errors:
            suggestions.append("运算错误：请仔细检查每一步的代数运算，特别是符号和移项")

        logical_gaps = [d for d in diagnoses if d.error_type == DiagnosisErrorType.LOGICAL_GAP]
        if logical_gaps:
            suggestions.append("推理断裂：请补充推导的中间步骤，使逻辑更加连贯")

        method_errors = [d for d in diagnoses if d.error_type == DiagnosisErrorType.METHOD_ERROR]
        if method_errors:
            suggestions.append("方法错误：请考虑是否使用了最合适的方法，或是否存在更简单的解法")

        if not suggestions:
            suggestions.append("请根据上述错误提示，有针对性地进行复习和练习")

        return suggestions


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def get_diagnoser() -> UnifiedDiagnoser:
    """获取统一诊断器"""
    return UnifiedDiagnoser()


def diagnose_steps(steps: List[Dict], expected_methods: List[str] = None) -> DiagnosisReport:
    """快速诊断步骤"""
    diagnoser = UnifiedDiagnoser()
    return diagnoser.diagnose_steps(steps, expected_methods)


def diagnose_error(
    operation: str,
    output_state: str,
    input_state: str = "",
    expected: str = None
) -> List[DiagnosisResult]:
    """快速诊断单个错误"""
    diagnoser = UnifiedDiagnoser()
    return diagnoser.diagnose_single_error(operation, output_state, input_state, expected)
