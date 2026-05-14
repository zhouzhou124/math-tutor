"""feedback_layer.py — 反馈层 (Feedback Layer)

负责：怎么展示给学生

反馈内容：
  - 步骤对错
  - 扣分原因
  - 标准解法
  - 错误路径

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                   Feedback Layer                                │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │StepFeedback  │  │DeductionFeed │  │SolutionFeed  │     │
  │  │   步骤反馈   │  │   扣分反馈   │  │   解法反馈   │     │
  │  └──────────────┘  └──────────────┘  └──────────────┘     │
  │                           │                                   │
  │                    UnifiedFeedback                             │
  │                       统一反馈入口                            │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses_json import dataclass_json

from diagnosis_layer import (
    DiagnosisReport,
    DiagnosisResult,
    DiagnosisErrorType,
    get_diagnoser
)

from scoring_layer import (
    ScoringResult,
    StepScore,
    ProofScoringResult,
    ProofScoreDimension,
    get_scorer,
    get_validity_scorer,
    CriticalStepType
)


# ═══════════════════════════════════════════════
# 反馈类型定义
# ═══════════════════════════════════════════════

class FeedbackLevel(Enum):
    """反馈详细程度"""
    BRIEF = "brief"        # 简要反馈
    STANDARD = "standard"   # 标准反馈
    DETAILED = "detailed"  # 详细反馈
    EDUCATIONAL = "educational"  # 教育性反馈（包含讲解）


class FeedbackFormat(Enum):
    """反馈格式"""
    TEXT = "text"           # 纯文本
    MARKDOWN = "markdown"  # Markdown格式
    HTML = "html"          # HTML格式
    JSON = "json"          # JSON格式


# ═══════════════════════════════════════════════
# 反馈结果定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class StepFeedback:
    """单步骤反馈"""
    step_index: int
    is_correct: bool
    score: float
    max_score: float
    message: str
    error_type: str = ""
    error_description: str = ""
    suggestion: str = ""
    is_critical: bool = False
    critical_type: str = ""


@dataclass_json
@dataclass
class DeductionFeedback:
    """扣分反馈"""
    dimension: str
    deduction_reason: str
    deduction_amount: float
    from_score: float
    to_score: float


@dataclass_json
@dataclass
class SolutionFeedback:
    """解法反馈"""
    student_method: str = ""
    standard_method: str = ""
    method_correct: bool = False
    methods_differ: bool = False
    feedback_message: str = ""


@dataclass_json
@dataclass
class FeedbackReport:
    """完整反馈报告"""
    total_score: float
    max_score: float
    score_percentage: float
    step_feedbacks: List[StepFeedback] = field(default_factory=list)
    deduction_feedbacks: List[DeductionFeedback] = field(default_factory=list)
    solution_feedback: SolutionFeedback = field(default_factory=list)
    diagnosis_report: Dict[str, Any] = field(default_factory=dict)
    standard_solution: str = ""
    error_path: str = ""
    overall_feedback: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)
    feedback_level: FeedbackLevel = FeedbackLevel.STANDARD


# ═══════════════════════════════════════════════
# 步骤反馈生成器
# ═══════════════════════════════════════════════

class StepFeedbackGenerator:
    """步骤反馈生成器"""

    @staticmethod
    def generate_step_feedbacks(scoring_result: ScoringResult) -> List[StepFeedback]:
        """从评分结果生成步骤反馈"""
        feedbacks = []

        for step_score in scoring_result.step_scores:
            is_correct = step_score.verified
            error_desc = ""

            if not is_correct:
                error_desc = StepFeedbackGenerator._get_error_description(step_score.error_level)

            feedback = StepFeedback(
                step_index=step_score.step_index,
                is_correct=is_correct,
                score=step_score.score,
                max_score=step_score.max_score,
                message=step_score.message,
                error_type=step_score.error_level.value if step_score.error_level else "",
                error_description=error_desc,
                suggestion=StepFeedbackGenerator._get_improvement_suggestion(step_score),
                is_critical=step_score.is_critical,
                critical_type=step_score.critical_type.name if step_score.critical_type else ""
            )
            feedbacks.append(feedback)

        return feedbacks

    @staticmethod
    def _get_error_description(error_level) -> str:
        """获取错误描述"""
        error_descriptions = {
            "LEVEL_0": "未执行任何数学计算",
            "LEVEL_1": "算术错误：计算过程中出现算术运算错误",
            "LEVEL_2": "代数错误：化简或代数变形出现错误",
            "LEVEL_3": "概念错误：使用了错误的概念或定理",
            "WARNING": "警告：存在不规范表述"
        }
        return error_descriptions.get(error_level.value if hasattr(error_level, 'value') else str(error_level), "未知错误")

    @staticmethod
    def _get_improvement_suggestion(step_score: StepScore) -> str:
        """获取改进建议"""
        if step_score.verified:
            return ""

        suggestions = []

        if step_score.is_critical:
            suggestions.append(f"关键步骤（{step_score.critical_type.name}）错误，请重新理解该方法的适用条件和正确用法")

        if step_score.error_level.value == 1:
            suggestions.append("仔细检查计算过程，特别是符号和基本运算")
        elif step_score.error_level.value == 2:
            suggestions.append("重新检查化简步骤，确保每一步代数变形都正确")
        elif step_score.error_level.value == 3:
            suggestions.append("复习相关概念和定理，确保理解其适用范围和条件")

        return "；".join(suggestions) if suggestions else "请重新检查该步骤"


# ═══════════════════════════════════════════════
# 扣分反馈生成器
# ═══════════════════════════════════════════════

class DeductionFeedbackGenerator:
    """扣分反馈生成器"""

    @staticmethod
    def generate_deduction_feedbacks(scoring_result: ScoringResult) -> List[DeductionFeedback]:
        """从评分结果生成扣分反馈"""
        feedbacks = []
        dimension_names = {
            "result": "结果分",
            "process": "过程分",
            "logic": "逻辑分",
            "method": "方法分",
            "expression": "表达分"
        }

        for dim_score in scoring_result.dimension_scores:
            dim_name = dimension_names.get(dim_score.dimension.value, dim_score.dimension.value)

            if dim_score.score < dim_score.max_score:
                deduction = dim_score.max_score - dim_score.score
                feedbacks.append(DeductionFeedback(
                    dimension=dim_name,
                    deduction_reason=dim_score.reason,
                    deduction_amount=deduction,
                    from_score=dim_score.max_score,
                    to_score=dim_score.score
                ))

        return feedbacks


# ═══════════════════════════════════════════════
# 解法反馈生成器
# ═══════════════════════════════════════════════

class SolutionFeedbackGenerator:
    """解法反馈生成器"""

    @staticmethod
    def generate_solution_feedback(
        student_methods: List[str],
        standard_methods: List[str],
        scoring_result: ScoringResult
    ) -> SolutionFeedback:
        """生成解法反馈"""
        method_overlap = set(student_methods) & set(standard_methods)
        methods_differ = len(method_overlap) == 0 and len(student_methods) > 0

        student_method_str = ", ".join([m.name for m in student_methods]) if student_methods else "未识别"
        standard_method_str = ", ".join([m.name for m in standard_methods]) if standard_methods else "未提供"

        if methods_differ:
            feedback_message = f"您使用了{student_method_str}，与标准解法（{standard_method_str}）不同。"
            feedback_message += "但如果数学过程正确，仍可获得满分。"
        elif method_overlap:
            feedback_message = f"您的解法与标准解法一致，使用了{student_method_str}。"
        else:
            feedback_message = "您的解法正确。"

        return SolutionFeedback(
            student_method=student_method_str,
            standard_method=standard_method_str,
            method_correct=scoring_result.total_score >= scoring_result.max_score * 0.9,
            methods_differ=methods_differ,
            feedback_message=feedback_message
        )


# ═══════════════════════════════════════════════
# 标准解法生成器
# ═══════════════════════════════════════════════

class StandardSolutionGenerator:
    """标准解法生成器（模板化）"""

    SOLUTION_TEMPLATES = {
        CriticalStepType.TAYLOR_EXPANSION: {
            "title": "泰勒展开法",
            "template": """
标准解法（泰勒展开）：

1. 将函数在指定点展开为泰勒级数
   f(x) = f(x₀) + f'(x₀)(x-x₀) + f''(x₀)/2!(x-x₀)² + ...

2. 代入原极限或表达式

3. 化简并求极限

关键点：
- 选择合适的展开点
- 选择合适的阶数（确保余项可忽略）
- 展开后各项的运算要仔细
""",
            "common_errors": [
                "展开阶数不足导致误差过大",
                "展开点选择不当",
                "运算过程中丢失高阶项"
            ]
        },
        CriticalStepType.L_HOSPITAL: {
            "title": "洛必达法则",
            "template": """
标准解法（洛必达法则）：

1. 判断极限类型（0/0 或 ∞/∞）
   lim f(x)/g(x)

2. 验证条件：
   - 分子分母在邻域内可导
   - 分母导数不为零

3. 应用洛必达：
   lim f(x)/g(x) = lim f'(x)/g'(x)

4. 重复步骤1-3直到求出极限

关键点：
- 仅适用于0/0或∞/∞型
- 每次求导后要检查是否仍是未定式
- 求导是同时对分子分母进行
""",
            "common_errors": [
                "在非0/0或∞/∞型时错误使用洛必达",
                "只对分子或只对分母求导",
                "忽视洛必达的条件限制"
            ]
        },
        CriticalStepType.MEAN_VALUE_THEOREM: {
            "title": "中值定理",
            "template": """
标准解法（中值定理）：

1. 验证条件：
   - f(x)在[a,b]上连续
   - f(x)在(a,b)内可导

2. 构造辅助函数（如需要）

3. 应用拉格朗日中值定理：
   f(b) - f(a) = f'(c)(b-a), 其中c∈(a,b)

4. 由结论反推所需条件

关键点：
- 条件不满足时不能使用
- 中值点c的存在性是结论，不是具体值
""",
            "common_errors": [
                "忽视定理的适用条件",
                "错误理解中值点的含义",
                "辅助函数构造不当"
            ]
        },
        CriticalStepType.SUBSTITUTION: {
            "title": "换元法",
            "template": """
标准解法（换元法）：

1. 选择合适的替换
   令 t = g(x)

2. 求出dt/dx = g'(x)，即 dx = dt/g'(x)

3. 换元积分/求导
   ∫f(g(x))g'(x)dx = ∫f(t)dt

4. 将结果中的t换回x

关键点：
- 换元要彻底
- 注意积分上下限的变换
- 换元后要检查新变量的范围
""",
            "common_errors": [
                "换元不彻底",
                "忘记换元积分上下限",
                "新变量范围讨论不全"
            ]
        }
    }

    @classmethod
    def get_solution(cls, method: CriticalStepType) -> str:
        """获取标准解法"""
        if method in cls.SOLUTION_TEMPLATES:
            return cls.SOLUTION_TEMPLATES[method]["template"]
        return f"标准解法（{method.name}）：请参考教材或相关资料。"

    @classmethod
    def get_solution_with_title(cls, method: CriticalStepType) -> Dict[str, str]:
        """获取带标题的标准解法"""
        if method in cls.SOLUTION_TEMPLATES:
            info = cls.SOLUTION_TEMPLATES[method]
            return {
                "title": info["title"],
                "template": info["template"],
                "common_errors": info.get("common_errors", [])
            }
        return {
            "title": method.name,
            "template": f"标准解法（{method.name}）：请参考教材或相关资料。",
            "common_errors": []
        }


# ═══════════════════════════════════════════════
# 错误路径分析器
# ═══════════════════════════════════════════════

class ErrorPathAnalyzer:
    """错误路径分析器"""

    @staticmethod
    def analyze_error_path(scoring_result: ScoringResult, diagnosis_report: DiagnosisReport) -> str:
        """分析错误路径"""
        if not scoring_result.step_scores:
            return "未检测到明确的错误路径"

        error_steps = []
        for step_score in scoring_result.step_scores:
            if not step_score.verified:
                error_steps.append({
                    "step_index": step_score.step_index,
                    "error_level": step_score.error_level,
                    "is_critical": step_score.is_critical,
                    "message": step_score.message
                })

        if not error_steps:
            return "未发现明显错误"

        path_lines = ["错误路径分析："]
        for i, error in enumerate(error_steps):
            step_num = error["step_index"] + 1
            if error["is_critical"]:
                path_lines.append(f"  {i+1}. 步骤{step_num} [关键步骤错误]")
                path_lines.append(f"     这是关键步骤，后续推导可能受影响")
            else:
                path_lines.append(f"  {i+1}. 步骤{step_num} [错误]")

        if len(error_steps) > 1:
            path_lines.append("")
            path_lines.append("注：多个错误可能存在因果关系，请从上到下逐一排查")

        return "\n".join(path_lines)


# ═══════════════════════════════════════════════
# 统一反馈生成器
# ═══════════════════════════════════════════════

class UnifiedFeedbackGenerator:
    """
    统一反馈生成器

    生成完整的反馈报告，包括：
    - 步骤对错反馈
    - 扣分原因反馈
    - 解法反馈
    - 诊断报告
    - 标准解法
    - 错误路径分析
    - 改进建议
    """

    def __init__(self, feedback_level: FeedbackLevel = FeedbackLevel.STANDARD):
        self.feedback_level = feedback_level
        self.step_feedback_gen = StepFeedbackGenerator()
        self.deduction_feedback_gen = DeductionFeedbackGenerator()
        self.solution_feedback_gen = SolutionFeedbackGenerator()
        self.error_path_analyzer = ErrorPathAnalyzer()

    def generate_feedback(
        self,
        scoring_result: ScoringResult,
        diagnosis_report: DiagnosisReport = None,
        student_methods: List[CriticalStepType] = None,
        standard_methods: List[CriticalStepType] = None,
        standard_solution: str = None
    ) -> FeedbackReport:
        """生成完整反馈报告"""

        step_feedbacks = self.step_feedback_gen.generate_step_feedbacks(scoring_result)
        deduction_feedbacks = self.deduction_feedback_gen.generate_deduction_feedbacks(scoring_result)

        solution_feedback = None
        if student_methods and standard_methods:
            solution_feedback = self.solution_feedback_gen.generate_solution_feedback(
                student_methods, standard_methods, scoring_result
            )

        diagnosis_dict = {}
        if diagnosis_report:
            diagnosis_dict = {
                "total_steps": diagnosis_report.total_steps,
                "correct_steps": diagnosis_report.correct_steps,
                "error_count": diagnosis_report.error_count,
                "summary": diagnosis_report.summary,
                "severity_distribution": diagnosis_report.severity_distribution
            }

        error_path = self.error_path_analyzer.analyze_error_path(
            scoring_result, diagnosis_report or DiagnosisReport()
        )

        improvement_suggestions = []
        if diagnosis_report:
            improvement_suggestions = diagnosis_report.improvement_suggestions

        overall_feedback = self._generate_overall_feedback(scoring_result)

        if standard_solution:
            standard_display = standard_solution
        elif standard_methods:
            standard_display = "\n".join([
                StandardSolutionGenerator.get_solution(m)
                for m in standard_methods if m in StandardSolutionGenerator.SOLUTION_TEMPLATES
            ])
        else:
            standard_display = "标准解法未提供"

        return FeedbackReport(
            total_score=scoring_result.total_score,
            max_score=scoring_result.max_score,
            score_percentage=scoring_result.total_score / scoring_result.max_score * 100,
            step_feedbacks=step_feedbacks,
            deduction_feedbacks=deduction_feedbacks,
            solution_feedback=solution_feedback,
            diagnosis_report=diagnosis_dict,
            standard_solution=standard_display,
            error_path=error_path,
            overall_feedback=overall_feedback,
            improvement_suggestions=improvement_suggestions,
            feedback_level=self.feedback_level
        )

    def _generate_overall_feedback(self, scoring_result: ScoringResult) -> str:
        """生成整体反馈"""
        score_pct = scoring_result.total_score / scoring_result.max_score * 100

        if score_pct >= 95:
            return "解题过程完美！所有步骤正确，逻辑清晰，继续保持！"
        elif score_pct >= 80:
            return "解题过程基本正确，存在一些小问题，请注意细节。"
        elif score_pct >= 60:
            return "解题思路正确，但存在一些错误，需要仔细检查关键步骤。"
        elif score_pct >= 40:
            return "解题方法需要改进，建议重新学习相关章节。"
        else:
            return "解题存在较大问题，建议系统复习相关知识点。"

    def format_feedback_text(self, report: FeedbackReport) -> str:
        """将反馈报告格式化为文本"""
        lines = []
        lines.append("=" * 60)
        lines.append("【评分反馈报告】")
        lines.append("=" * 60)
        lines.append(f"总分: {report.total_score:.1f}/{report.max_score:.1f} ({report.score_percentage:.1f}%)")
        lines.append("-" * 60)
        lines.append(f"整体评价: {report.overall_feedback}")
        lines.append("-" * 60)

        lines.append("\n【步骤详情】")
        for sf in report.step_feedbacks:
            status = "[OK]" if sf.is_correct else "[X]"
            lines.append(f"  步骤{sf.step_index+1} {status}: {sf.message}")
            if sf.is_critical and not sf.is_correct:
                lines.append(f"         [关键步骤错误] {sf.error_description}")
            elif not sf.is_correct:
                lines.append(f"         错误: {sf.error_description}")
            if sf.suggestion:
                lines.append(f"         建议: {sf.suggestion}")

        if report.deduction_feedbacks:
            lines.append("\n【扣分明细】")
            for df in report.deduction_feedbacks:
                lines.append(f"  {df.dimension}: -{df.deduction_amount:.1f}分")
                lines.append(f"    原因: {df.deduction_reason}")

        if report.solution_feedback:
            lines.append("\n【解法反馈】")
            lines.append(f"  {report.solution_feedback.feedback_message}")

        if report.error_path:
            lines.append("\n【错误路径】")
            lines.append(report.error_path)

        if report.standard_solution:
            lines.append("\n【标准解法】")
            lines.append(report.standard_solution)

        if report.improvement_suggestions:
            lines.append("\n【改进建议】")
            for i, s in enumerate(report.improvement_suggestions, 1):
                lines.append(f"  {i}. {s}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def format_feedback_markdown(self, report: FeedbackReport) -> str:
        """将反馈报告格式化为Markdown"""
        lines = []
        lines.append("# 评分反馈报告\n")

        lines.append(f"## 总分: {report.total_score:.1f}/{report.max_score:.1f} ({report.score_percentage:.1f}%)")
        lines.append(f"\n**整体评价**: {report.overall_feedback}\n")

        lines.append("## 步骤详情\n")
        for sf in report.step_feedbacks:
            status = "✅" if sf.is_correct else "❌"
            lines.append(f"### 步骤{sf.step_index+1} {status}")
            lines.append(f"- **{sf.message}**")
            if not sf.is_correct:
                lines.append(f"- 错误类型: {sf.error_description}")
                if sf.suggestion:
                    lines.append(f"- 建议: {sf.suggestion}")
            lines.append("")

        if report.deduction_feedbacks:
            lines.append("## 扣分明细\n")
            for df in report.deduction_feedbacks:
                lines.append(f"- **{df.dimension}**: -{df.deduction_amount:.1f}分")
                lines.append(f"  - 原因: {df.deduction_reason}\n")

        if report.solution_feedback:
            lines.append("## 解法反馈\n")
            lines.append(f"{report.solution_feedback.feedback_message}\n")

        if report.error_path:
            lines.append("## 错误路径\n")
            lines.append(f"```\n{report.error_path}\n```\n")

        if report.standard_solution:
            lines.append("## 标准解法\n")
            lines.append(f"```\n{report.standard_solution}\n```\n")

        if report.improvement_suggestions:
            lines.append("## 改进建议\n")
            for i, s in enumerate(report.improvement_suggestions, 1):
                lines.append(f"{i}. {s}\n")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def generate_feedback(
    scoring_result: ScoringResult,
    diagnosis_report: DiagnosisReport = None,
    student_methods: List[CriticalStepType] = None,
    standard_methods: List[CriticalStepType] = None,
    feedback_level: FeedbackLevel = FeedbackLevel.STANDARD
) -> FeedbackReport:
    """快速生成反馈报告"""
    generator = UnifiedFeedbackGenerator(feedback_level)
    return generator.generate_feedback(
        scoring_result, diagnosis_report, student_methods, standard_methods
    )


def format_feedback_text(report: FeedbackReport) -> str:
    """格式化反馈为文本"""
    generator = UnifiedFeedbackGenerator()
    return generator.format_feedback_text(report)


def format_feedback_markdown(report: FeedbackReport) -> str:
    """格式化反馈为Markdown"""
    generator = UnifiedFeedbackGenerator()
    return generator.format_feedback_markdown(report)
