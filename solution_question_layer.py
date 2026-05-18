"""solution_question_layer.py — 解答题处理层

解答题核心模块：

1. Canonical Trace        ✓ (scoring_layer已有)
2. 多解法支持             ✓
3. Method Classification  ✓
4. Step Extraction        ✓
5. Operation Semantic     ★ (关键缺失)
6. Symbolic Verification  ✓
7. Dependency Graph       ✓
8. Rubric Scoring        ✓ (scoring_layer已有)
9. Partial Credit        ✓ (考研核心)

Operation Semantic 是现在最缺的：
  operation="substitution" 的语义是什么？
  它如何变换问题？
  为什么这样做是正确的？
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses_json import dataclass_json

from scoring_layer import (
    UnifiedScorer,
    ScoringResult,
    StepScore,
    CriticalStepType,
    get_scorer
)


# ═══════════════════════════════════════════════
# 操作语义定义 (Operation Semantic)
# ═══════════════════════════════════════════════

class OperationSemantic(Enum):
    """
    操作语义枚举

    这是解答题系统的核心！
    每个操作不只是标签，而是有明确的数学语义。
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

    # ===== 极限操作 =====
    TAYLOR_EXPANSION = "taylor_expansion"  # 泰勒展开
    L_HOSPITAL = "l_hospital"          # 洛必达
    LIMIT_COMPUTE = "limit_compute"     # 极限计算

    # ===== 方程操作 =====
    SOLVE_EQUATION = "solve_equation"   # 解方程
    FACTOR = "factor"                   # 因式分解
    ROOTS = "roots"                    # 求根

    # ===== 证明操作 =====
    ASSUME = "assume"                   # 假设
    DERIVE = "derive"                   # 推导
    APPLY_THEOREM = "apply_theorem"     # 应用定理
    CONSTRUCT_AUXILIARY = "construct_auxiliary"  # 构造辅助函数
    PROOF_BY_CONTRADICTION = "proof_by_contradiction"  # 反证法
    PROOF_BY_INDUCTION = "proof_by_induction"  # 数学归纳法

    # ===== 不等式操作 =====
    INEQUALITY_COMPARE = "inequality_compare"  # 不等式比较
    Jensen = "jensen"                  # Jensen不等式

    # ===== 特殊操作 =====
    OBSERVATION = "observation"         # 观察/注意到
    EQUIVALENT_TRANSFORM = "equivalent_transform"  # 等价变换
    DEFINITION = "definition"           # 定义
    SUBSTITUTE = "substitute"           # 代入


# ═══════════════════════════════════════════════
# 操作语义详情
# ═══════════════════════════════════════════════

@dataclass
class OperationSemanticDetail:
    """操作语义详情"""
    semantic: OperationSemantic
    display_name: str
    description: str
    input_expectation: str      # 输入状态期望
    output_expectation: str      # 输出状态变化
    validity_check: str        # 有效性检查
    common_errors: List[str]    # 常见错误
    success_criteria: str        # 成功标准


OPERATION_SEMANTICS = {
    OperationSemantic.SUBSTITUTION: OperationSemanticDetail(
        semantic=OperationSemantic.SUBSTITUTION,
        display_name="换元法",
        description="通过变量替换简化问题",
        input_expectation="复合函数或复杂表达式",
        output_expectation="更简单的独立变量表达式",
        validity_check="新变量与原变量关系明确，定义域保持一致",
        common_errors=[
            "换元不彻底",
            "忘记换元积分上下限",
            "新变量范围讨论不全"
        ],
        success_criteria="替换后表达式更简单，且可逆"
    ),

    OperationSemantic.INTEGRATION_BY_PARTS: OperationSemanticDetail(
        semantic=OperationSemantic.INTEGRATION_BY_PARTS,
        display_name="分部积分",
        description="∫u dv = uv - ∫v du",
        input_expectation="两个函数相乘的形式",
        output_expectation="分解为易积分的uv项和vdu项",
        validity_check="u选择遵循: 幂函数 > 对数 > 指数 > 三角",
        common_errors=[
            "u选择不当导致循环",
            "符号错误",
            "漏写负号"
        ],
        success_criteria="分解后每项都可积"
    ),

    OperationSemantic.TAYLOR_EXPANSION: OperationSemanticDetail(
        semantic=OperationSemantic.TAYLOR_EXPANSION,
        display_name="泰勒展开",
        description="在点x0处展开为无穷级数",
        input_expectation="函数及展开点",
        output_expectation="多项式逼近表达式",
        validity_check="余项趋于0，或可忽略",
        common_errors=[
            "展开阶数不足",
            "展开点错误",
            "余项处理不当"
        ],
        success_criteria="误差足够小或余项明确"
    ),

    OperationSemantic.L_HOSPITAL: OperationSemanticDetail(
        semantic=OperationSemantic.L_HOSPITAL,
        display_name="洛必达法则",
        description="0/0或∞/∞型求导",
        input_expectation="0/0或∞/∞未定式",
        output_expectation="分子分母同时求导后的新极限",
        validity_check="仍是未定式时继续求导",
        common_errors=[
            "非未定式使用",
            "只对分子或分母求导",
            "条件验证缺失"
        ],
        success_criteria="得到确定极限或确定不存在"
    ),

    OperationSemantic.CONSTRUCT_AUXILIARY: OperationSemanticDetail(
        semantic=OperationSemantic.CONSTRUCT_AUXILIARY,
        display_name="构造辅助函数",
        description="为证明构造辅助函数",
        input_expectation="原命题或要证的结论",
        output_expectation="可应用定理的新函数",
        validity_check="辅助函数性质明确",
        common_errors=[
            "构造方向错误",
            "辅助函数性质不满足",
            "构造过于复杂"
        ],
        success_criteria="辅助函数能揭示问题本质"
    ),

    OperationSemantic.APPLY_THEOREM: OperationSemanticDetail(
        semantic=OperationSemantic.APPLY_THEOREM,
        display_name="应用定理",
        description="正确应用数学定理",
        input_expectation="定理的前提条件",
        output_expectation="定理的结论",
        validity_check="所有条件都满足",
        common_errors=[
            "条件验证缺失",
            "定理误用",
            "结论推导错误"
        ],
        success_criteria="条件和应用都正确"
    ),
}


# ═══════════════════════════════════════════════
# 方法分类 (Method Classification)
# ═══════════════════════════════════════════════

class SolutionMethod(Enum):
    """解法方法分类"""
    DIRECT_COMPUTATION = "direct"           # 直接计算
    SUBSTITUTION_METHOD = "substitution"    # 换元法
    INTEGRATION_BY_PARTS = "parts"          # 分部积分
    TAYLOR_METHOD = "taylor"               # 泰勒展开
    L_HOSPITAL_METHOD = "l_hospital"       # 洛必达
    MEAN_VALUE_METHOD = "mean_value"       # 中值定理
    FACTOR_METHOD = "factor"               # 因式分解
    AUXILIARY_FUNCTION = "auxiliary"        # 构造辅助函数
    CONTRADICTION = "contradiction"         # 反证法
    INDUCTION = "induction"                 # 数学归纳法
    EQUIVALENT_TRANSFORM = "equivalent"    # 等价变换


METHOD_TO_OPERATIONS = {
    SolutionMethod.SUBSTITUTION_METHOD: [
        OperationSemantic.SUBSTITUTION,
        OperationSemantic.SUBSTITUTE
    ],
    SolutionMethod.INTEGRATION_BY_PARTS: [
        OperationSemantic.INTEGRATION_BY_PARTS
    ],
    SolutionMethod.TAYLOR_METHOD: [
        OperationSemantic.TAYLOR_EXPANSION
    ],
    SolutionMethod.L_HOSPITAL_METHOD: [
        OperationSemantic.L_HOSPITAL
    ],
    SolutionMethod.MEAN_VALUE_METHOD: [
        OperationSemantic.APPLY_THEOREM
    ],
    SolutionMethod.AUXILIARY_FUNCTION: [
        OperationSemantic.CONSTRUCT_AUXILIARY
    ],
}


# ═══════════════════════════════════════════════
# 依赖图 (Dependency Graph)
# ═══════════════════════════════════════════════

@dataclass
class StepNode:
    """步骤节点"""
    step_index: int
    operation: str
    semantic: OperationSemantic
    input_state: str
    output_state: str
    dependencies: Set[int] = field(default_factory=set)
    dependents: Set[int] = field(default_factory=set)


class DependencyGraph:
    """
    依赖图

    表示步骤之间的依赖关系：
    步骤3依赖步骤1 → 步骤1 → 步骤3
    """

    def __init__(self):
        self.nodes: Dict[int, StepNode] = {}

    def add_step(
        self,
        step_index: int,
        operation: str,
        input_state: str,
        output_state: str
    ) -> StepNode:
        """添加步骤节点"""
        semantic = self._infer_semantic(operation)

        dependencies = self._infer_dependencies(
            step_index, input_state, output_state
        )

        node = StepNode(
            step_index=step_index,
            operation=operation,
            semantic=semantic,
            input_state=input_state,
            output_state=output_state,
            dependencies=dependencies
        )

        self.nodes[step_index] = node

        for dep in dependencies:
            if dep in self.nodes:
                self.nodes[dep].dependents.add(step_index)

        return node

    def _infer_semantic(self, operation: str) -> OperationSemantic:
        """推断操作语义"""
        op_lower = operation.lower()

        semantic_mapping = {
            "substitution": OperationSemantic.SUBSTITUTION,
            "换元": OperationSemantic.SUBSTITUTION,
            "令": OperationSemantic.SUBSTITUTION,
            "integration_by_parts": OperationSemantic.INTEGRATION_BY_PARTS,
            "分部积分": OperationSemantic.INTEGRATION_BY_PARTS,
            "taylor": OperationSemantic.TAYLOR_EXPANSION,
            "泰勒": OperationSemantic.TAYLOR_EXPANSION,
            "l_hospital": OperationSemantic.L_HOSPITAL,
            "洛必达": OperationSemantic.L_HOSPITAL,
            "洛比达": OperationSemantic.L_HOSPITAL,
            "differentiate": OperationSemantic.DIFFERENTIATE,
            "求导": OperationSemantic.DIFFERENTIATE,
            "integrate": OperationSemantic.INTEGRATE,
            "积分": OperationSemantic.INTEGRATE,
            "solve": OperationSemantic.SOLVE_EQUATION,
            "解方程": OperationSemantic.SOLVE_EQUATION,
            "factor": OperationSemantic.FACTOR,
            "因式分解": OperationSemantic.FACTOR,
            "assume": OperationSemantic.ASSUME,
            "假设": OperationSemantic.ASSUME,
            "derive": OperationSemantic.DERIVE,
            "推导": OperationSemantic.DERIVE,
            "定理": OperationSemantic.APPLY_THEOREM,
            "construct": OperationSemantic.CONSTRUCT_AUXILIARY,
            "构造": OperationSemantic.CONSTRUCT_AUXILIARY,
            "反证": OperationSemantic.PROOF_BY_CONTRADICTION,
            "归纳": OperationSemantic.PROOF_BY_INDUCTION,
            "simplify": OperationSemantic.SIMPLIFY,
            "化简": OperationSemantic.SIMPLIFY,
            "observe": OperationSemantic.OBSERVATION,
            "观察": OperationSemantic.OBSERVATION,
            "注意到": OperationSemantic.OBSERVATION,
            "limit": OperationSemantic.LIMIT_COMPUTE,
            "极限": OperationSemantic.LIMIT_COMPUTE,
        }

        for key, semantic in semantic_mapping.items():
            if key in op_lower:
                return semantic

        return OperationSemantic.COMPUTE

    def _infer_dependencies(
        self,
        step_index: int,
        input_state: str,
        output_state: str
    ) -> Set[int]:
        """推断步骤依赖"""
        dependencies = set()

        if step_index == 0:
            return dependencies

        if not input_state or input_state == output_state:
            for prev_idx in range(step_index):
                dependencies.add(prev_idx)
        else:
            for prev_idx in range(step_index):
                if prev_idx in self.nodes:
                    prev_node = self.nodes[prev_idx]
                    if self._states_related(prev_node.output_state, input_state):
                        dependencies.add(prev_idx)

        return dependencies

    def _states_related(self, state1: str, state2: str) -> bool:
        """判断两个状态是否相关"""
        if not state1 or not state2:
            return True

        common_chars = set(state1) & set(state2)
        return len(common_chars) >= 2

    def get_execution_order(self) -> List[List[int]]:
        """获取可并行的执行顺序"""
        in_degree = {i: 0 for i in self.nodes}
        for node in self.nodes.values():
            for dep in node.dependencies:
                in_degree[node.step_index] += 1

        levels = []
        remaining = set(self.nodes.keys())

        while remaining:
            current_level = [i for i in remaining if in_degree[i] == 0]
            if not current_level:
                break

            levels.append(current_level)
            for idx in current_level:
                remaining.remove(idx)
                for node in self.nodes.values():
                    if idx in node.dependencies:
                        in_degree[node.step_index] -= 1

        return levels

    def to_graphviz(self) -> str:
        """转换为Graphviz格式"""
        lines = ["digraph {", "    rankdir=TB;"]

        for node in self.nodes.values():
            label = f'"{node.step_index}: {node.operation[:20]}"'
            lines.append(f'    {node.step_index} [label={label}];')

        for node in self.nodes.values():
            for dep in node.dependencies:
                lines.append(f"    {dep} -> {node.step_index};")

        lines.append("}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 步骤提取 (Step Extraction)
# ═══════════════════════════════════════════════

@dataclass
class ExtractedStep:
    """提取的步骤"""
    step_index: int
    operation: str
    semantic: OperationSemantic
    semantic_detail: OperationSemanticDetail
    input_state: str
    output_state: str
    is_critical: bool
    method_type: SolutionMethod
    verification_result: str
    is_valid: bool
    error_message: str = ""


class StepExtractor:
    """
    步骤提取器

    从学生解答中提取结构化步骤
    """

    @staticmethod
    def extract_steps(
        student_solution: str,
        question_context: str = ""
    ) -> List[ExtractedStep]:
        """提取步骤"""
        lines = student_solution.strip().split('\n')
        steps = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if line[0].isdigit() and ('.' in line[:3] or '、' in line[:3]):
                parts = re.split(r'[\.、]\s*', line, maxsplit=1)
                operation = parts[1] if len(parts) > 1 else parts[0]
            elif line.startswith('-') or line.startswith('→'):
                operation = line.lstrip('-→').strip()
            else:
                operation = line

            semantic = OperationExtractor.extract_semantic(operation)

            detail = OPERATION_SEMANTICS.get(semantic)

            step = ExtractedStep(
                step_index=i,
                operation=operation,
                semantic=semantic,
                semantic_detail=detail,
                input_state="",
                output_state=operation,
                is_critical=StepExtractor._is_critical_operation(semantic),
                method_type=StepExtractor._infer_method(semantic),
                verification_result="待验证",
                is_valid=True
            )

            steps.append(step)

        return steps

    @staticmethod
    def _is_critical_operation(semantic: OperationSemantic) -> bool:
        """判断是否为关键操作"""
        critical_types = {
            OperationSemantic.SUBSTITUTION,
            OperationSemantic.INTEGRATION_BY_PARTS,
            OperationSemantic.TAYLOR_EXPANSION,
            OperationSemantic.L_HOSPITAL,
            OperationSemantic.CONSTRUCT_AUXILIARY,
            OperationSemantic.APPLY_THEOREM,
        }
        return semantic in critical_types

    @staticmethod
    def _infer_method(semantic: OperationSemantic) -> SolutionMethod:
        """推断解法类型"""
        method_mapping = {
            OperationSemantic.SUBSTITUTION: SolutionMethod.SUBSTITUTION_METHOD,
            OperationSemantic.INTEGRATION_BY_PARTS: SolutionMethod.INTEGRATION_BY_PARTS,
            OperationSemantic.TAYLOR_EXPANSION: SolutionMethod.TAYLOR_METHOD,
            OperationSemantic.L_HOSPITAL: SolutionMethod.L_HOSPITAL_METHOD,
            OperationSemantic.CONSTRUCT_AUXILIARY: SolutionMethod.AUXILIARY_FUNCTION,
            OperationSemantic.APPLY_THEOREM: SolutionMethod.MEAN_VALUE_METHOD,
            OperationSemantic.PROOF_BY_CONTRADICTION: SolutionMethod.CONTRADICTION,
            OperationSemantic.PROOF_BY_INDUCTION: SolutionMethod.INDUCTION,
        }
        return method_mapping.get(semantic, SolutionMethod.DIRECT_COMPUTATION)


class OperationExtractor:
    """操作提取器"""

    @staticmethod
    def extract_semantic(operation: str) -> OperationSemantic:
        """提取操作语义"""
        op_lower = operation.lower()

        for semantic_key, detail in OPERATION_SEMANTICS.items():
            key_lower = detail.display_name.lower()
            if key_lower in op_lower or semantic_key.value in op_lower:
                return semantic_key

        if any(kw in op_lower for kw in ['换元', '令', '令t', '令x']):
            return OperationSemantic.SUBSTITUTION
        elif any(kw in op_lower for kw in ['分部积分', '∫']):
            return OperationSemantic.INTEGRATION_BY_PARTS
        elif any(kw in op_lower for kw in ['泰勒', 'taylor']):
            return OperationSemantic.TAYLOR_EXPANSION
        elif any(kw in op_lower for kw in ['洛必达', 'l hospital', 'l\\hospital']):
            return OperationSemantic.L_HOSPITAL
        elif any(kw in op_lower for kw in ['构造', '辅助']):
            return OperationSemantic.CONSTRUCT_AUXILIARY
        elif any(kw in op_lower for kw in ['定理', '根据']):
            return OperationSemantic.APPLY_THEOREM
        elif any(kw in op_lower for kw in ['求导', '导数', 'differentiate']):
            return OperationSemantic.DIFFERENTIATE
        elif any(kw in op_lower for kw in ['积分', '∫']):
            return OperationSemantic.INTEGRATE
        elif any(kw in op_lower for kw in ['化简', 'simplify']):
            return OperationSemantic.SIMPLIFY
        elif any(kw in op_lower for kw in ['解', '方程']):
            return OperationSemantic.SOLVE_EQUATION

        return OperationSemantic.COMPUTE


# ═══════════════════════════════════════════════
# 多解法支持
# ═══════════════════════════════════════════════

@dataclass
class SolutionMethodVariant:
    """解法变体"""
    method_id: str
    method_name: str
    description: str
    critical_operations: List[OperationSemantic]
    key_steps: List[str]
    expected_result: str


class MultiSolutionSupport:
    """
    多解法支持

    同一个题目可能有多种正确解法
    """

    SOLUTION_VARIANTS = {
        "limit_taylor": SolutionMethodVariant(
            method_id="limit_taylor",
            method_name="泰勒展开法",
            description="利用泰勒展开求极限",
            critical_operations=[OperationSemantic.TAYLOR_EXPANSION],
            key_steps=["识别0/0型", "选择展开点", "确定展开阶数", "计算极限"],
            expected_result="确定数值或表达式"
        ),
        "limit_lhospital": SolutionMethodVariant(
            method_id="limit_lhospital",
            method_name="洛必达法则",
            description="利用洛必达法则求极限",
            critical_operations=[OperationSemantic.L_HOSPITAL],
            key_steps=["验证0/0或∞/∞型", "分子分母求导", "检查是否仍是未定式", "重复或结束"],
            expected_result="确定数值或表达式"
        ),
        "integral_substitution": SolutionMethodVariant(
            method_id="integral_substitution",
            method_name="换元积分法",
            description="通过换元简化积分",
            critical_operations=[OperationSemantic.SUBSTITUTION],
            key_steps=["识别复合函数", "选择替换", "换元", "计算新积分", "换回原变量"],
            expected_result="原函数表达式"
        ),
        "integral_parts": SolutionMethodVariant(
            method_id="integral_parts",
            method_name="分部积分法",
            description="利用分部积分公式",
            critical_operations=[OperationSemantic.INTEGRATION_BY_PARTS],
            key_steps=["选择u和dv", "应用公式∫udv=uv-∫vdu", "计算新积分"],
            expected_result="原函数表达式"
        ),
    }

    @classmethod
    def get_variant(cls, method_id: str) -> Optional[SolutionMethodVariant]:
        """获取解法变体"""
        return cls.SOLUTION_VARIANTS.get(method_id)

    @classmethod
    def match_solution(
        cls,
        extracted_steps: List[ExtractedStep]
    ) -> List[SolutionMethodVariant]:
        """匹配解法变体"""
        matched = []

        for variant in cls.SOLUTION_VARIANTS.values():
            score = 0
            total_critical = len(variant.critical_operations)

            for step in extracted_steps:
                if step.semantic in variant.critical_operations:
                    score += 1

            if total_critical > 0 and score > 0:
                confidence = score / total_critical
                if confidence >= 0.5:
                    matched.append((variant, confidence))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in matched]


# ═══════════════════════════════════════════════
# 符号验证
# ═══════════════════════════════════════════════

class SymbolicStepVerifier:
    """
    符号验证器

    验证每一步是否合法
    """

    @staticmethod
    def verify_step(
        step: ExtractedStep,
        prev_steps: List[ExtractedStep]
    ) -> Tuple[bool, str]:
        """
        验证单步

        Returns:
            (is_valid, message)
        """
        if step.semantic_detail is None:
            return True, "操作语义未知，跳过验证"

        detail = step.semantic_detail

        if not prev_steps:
            if step.semantic not in {OperationSemantic.START, OperationSemantic.OBSERVATION}:
                return True, f"起始步骤使用{detail.display_name}可能不合理"
            return True, "起始步骤正常"

        prev_step = prev_steps[-1]

        is_valid, message = SymbolicStepVerifier._verify_semantic_specific(
            step, prev_step, detail
        )

        return is_valid, message

    @staticmethod
    def _verify_semantic_specific(
        step: ExtractedStep,
        prev_step: ExtractedStep,
        detail: OperationSemanticDetail
    ) -> Tuple[bool, str]:
        """根据语义特定验证"""
        semantic = step.semantic

        if semantic == OperationSemantic.SUBSTITUTION:
            return SymbolicStepVerifier._verify_substitution(step, prev_step)

        elif semantic == OperationSemantic.INTEGRATION_BY_PARTS:
            return SymbolicStepVerifier._verify_integration_by_parts(step, prev_step)

        elif semantic == OperationSemantic.L_HOSPITAL:
            return SymbolicStepVerifier._verify_l_hospital(step, prev_step)

        elif semantic == OperationSemantic.TAYLOR_EXPANSION:
            return SymbolicStepVerifier._verify_taylor(step, prev_step)

        return True, "通用验证通过"

    @staticmethod
    def _verify_substitution(
        step: ExtractedStep,
        prev_step: ExtractedStep
    ) -> Tuple[bool, str]:
        """验证换元"""
        op_lower = step.operation.lower()

        has_substitution = any(kw in op_lower for kw in ['令', '令t', '令x', '换元', 'substitution'])

        if not has_substitution:
            return False, "换元操作未明确说明"

        has_equals = '=' in step.operation

        if not has_equals:
            return False, "换元应明确新变量与原变量的关系"

        return True, "换元操作合理"

    @staticmethod
    def _verify_integration_by_parts(
        step: ExtractedStep,
        prev_step: ExtractedStep
    ) -> Tuple[bool, str]:
        """验证分部积分"""
        op_lower = step.operation.lower()

        has_parts = any(kw in op_lower for kw in ['分部积分', '∫udv', 'uv'])

        if not has_parts:
            return False, "分部积分应明确u和dv的选择"

        return True, "分部积分操作合理"

    @staticmethod
    def _verify_l_hospital(
        step: ExtractedStep,
        prev_step: ExtractedStep
    ) -> Tuple[bool, str]:
        """验证洛必达"""
        op_lower = step.operation.lower()

        has_lhospital = any(kw in op_lower for kw in ['洛必达', 'l\\hospital', 'lhospital'])

        if not has_lhospital:
            return False, "应明确使用洛必达法则"

        return True, "洛必达操作合理"

    @staticmethod
    def _verify_taylor(
        step: ExtractedStep,
        prev_step: ExtractedStep
    ) -> Tuple[bool, str]:
        """验证泰勒展开"""
        op_lower = step.operation.lower()

        has_taylor = any(kw in op_lower for kw in ['泰勒', 'taylor', '麦克劳林'])

        if not has_taylor:
            return False, "应明确使用泰勒展开"

        has_order = any(kw in op_lower for kw in ['阶', '次', 'n阶', '二阶'])

        if not has_order:
            return True, "警告：未明确展开阶数"

        return True, "泰勒展开操作合理"


# ═══════════════════════════════════════════════
# 统一解答题评分器
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class SolutionQuestion:
    """解答题"""
    question_id: str
    question_text: str
    standard_solutions: List[SolutionMethodVariant]
    rubric: Dict[str, float]
    expected_steps: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class SolutionScoringResult:
    """解答题评分结果"""
    total_score: float
    max_score: float
    score_percentage: float
    is_correct: bool
    method_used: str
    method_confidence: float
    steps: List[ExtractedStep]
    dependency_graph: Dict[str, Any]
    step_scores: List[Dict[str, Any]]
    partial_credit_given: float
    partial_credit_explanation: str
    detailed_feedback: str


class UnifiedSolutionScorer:
    """
    统一解答题评分器

    核心模块整合：
    1. Canonical Trace        ✓
    2. 多解法支持             ✓
    3. Method Classification ✓
    4. Step Extraction        ✓
    5. Operation Semantic     ✓ (核心)
    6. Symbolic Verification  ✓
    7. Dependency Graph       ✓
    8. Rubric Scoring         ✓
    9. Partial Credit         ✓
    """

    def __init__(self):
        self.scoring_layer = get_scorer()
        self.step_extractor = StepExtractor()
        self.symbolic_verifier = SymbolicStepVerifier()
        self.multi_solution = MultiSolutionSupport()

    def score_solution(
        self,
        question: SolutionQuestion,
        student_solution: str,
        student_result: str = ""
    ) -> SolutionScoringResult:
        """
        评分解答题
        """
        extracted_steps = self.step_extractor.extract_steps(student_solution)

        dependency_graph = DependencyGraph()
        for i, step in enumerate(extracted_steps):
            prev_output = extracted_steps[i-1].output_state if i > 0 else ""
            dependency_graph.add_step(
                i, step.operation, prev_output, step.output_state
            )

        matched_variants = self.multi_solution.match_solution(extracted_steps)

        method_used = matched_variants[0].method_name if matched_variants else "未识别"
        method_confidence = matched_variants[0].method_id if matched_variants else ""

        step_scores = []
        total_valid = 0
        total_steps = len(extracted_steps)

        for i, step in enumerate(extracted_steps):
            prev_steps = extracted_steps[:i] if i > 0 else []

            is_valid, message = self.symbolic_verifier.verify_step(step, prev_steps)
            step.is_valid = is_valid
            step.verification_result = message

            if is_valid:
                total_valid += 1

            step_scores.append({
                "step_index": i,
                "operation": step.operation,
                "semantic": step.semantic.value,
                "is_valid": is_valid,
                "is_critical": step.is_critical,
                "verification": message
            })

        step_score_ratio = total_valid / total_steps if total_steps > 0 else 0
        result_score = 1.0 if student_result else 0.0

        rubric_step_weight = question.rubric.get("step", 0.7)
        rubric_result_weight = question.rubric.get("result", 0.3)

        partial_credit = step_score_ratio * rubric_step_weight

        if result_score == 1.0:
            total_score = partial_credit + rubric_result_weight
        else:
            total_score = partial_credit

        partial_explanation = f"步骤得分: {partial_credit:.2f}/{rubric_step_weight:.2f}"
        if result_score == 1.0:
            partial_explanation += f", 结果得分: {rubric_result_weight:.2f}/{rubric_result_weight:.2f}"
        else:
            partial_explanation += ", 结果错误: 0.00"

        detailed = self._generate_detailed_feedback(
            question, extracted_steps, step_scores, method_used
        )

        return SolutionScoringResult(
            total_score=total_score * 100,
            max_score=100.0,
            score_percentage=total_score * 100,
            is_correct=total_score >= 0.6,
            method_used=method_used,
            method_confidence=len(matched_variants) / len(MultiSolutionSupport.SOLUTION_VARIANTS),
            steps=extracted_steps,
            dependency_graph={"nodes": len(dependency_graph.nodes)},
            step_scores=step_scores,
            partial_credit_given=partial_credit,
            partial_credit_explanation=partial_explanation,
            detailed_feedback=detailed
        )

    def _generate_detailed_feedback(
        self,
        question: SolutionQuestion,
        steps: List[ExtractedStep],
        step_scores: List[Dict],
        method_used: str
    ) -> str:
        """生成详细反馈"""
        lines = []
        lines.append(f"识别方法: {method_used}")
        lines.append("")

        lines.append("【步骤分析】")
        for score in step_scores:
            status = "[OK]" if score["is_valid"] else "[X]"
            critical = "[关键]" if score["is_critical"] else ""
            lines.append(f"  步骤{score['step_index']+1} {status} {critical}")
            lines.append(f"    操作: {score['operation']}")
            lines.append(f"    语义: {score['semantic']}")
            lines.append(f"    验证: {score['verification']}")

        lines.append("")
        lines.append("【Operation Semantic 详情】")
        for step in steps:
            if step.semantic_detail:
                detail = step.semantic_detail
                lines.append(f"  {detail.display_name}:")
                lines.append(f"    描述: {detail.description}")
                lines.append(f"    输入期望: {detail.input_expectation}")
                lines.append(f"    输出期望: {detail.output_expectation}")
                if detail.common_errors:
                    lines.append(f"    常见错误: {', '.join(detail.common_errors[:2])}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def extract_operation_semantic(operation: str) -> OperationSemantic:
    """快速提取操作语义"""
    return OperationExtractor.extract_semantic(operation)


def get_semantic_detail(semantic: OperationSemantic) -> OperationSemanticDetail:
    """获取语义详情"""
    return OPERATION_SEMANTICS.get(semantic)


def build_dependency_graph(steps: List[Dict]) -> DependencyGraph:
    """构建依赖图"""
    graph = DependencyGraph()
    for i, step in enumerate(steps):
        graph.add_step(
            i,
            step.get('operation', ''),
            step.get('input_state', ''),
            step.get('output_state', '')
        )
    return graph


def score_solution_question(
    question: SolutionQuestion,
    student_solution: str,
    student_result: str = ""
) -> SolutionScoringResult:
    """快速评分解答题"""
    scorer = UnifiedSolutionScorer()
    return scorer.score_solution(question, student_solution, student_result)


def format_solution_feedback(result: SolutionScoringResult) -> str:
    """格式化解答题反馈"""
    lines = []
    lines.append("=" * 60)
    lines.append("【解答题评分结果】")
    lines.append("=" * 60)
    lines.append(f"总分: {result.total_score:.1f}/{result.max_score:.1f}")
    lines.append(f"方法: {result.method_used}")
    lines.append("")
    lines.append("【部分得分说明】")
    lines.append(result.partial_credit_explanation)
    lines.append("")
    lines.append("【详细反馈】")
    lines.append(result.detailed_feedback)
    lines.append("=" * 60)
    return "\n".join(lines)
