"""feedback_ui.py — AI批改结果展示UI

完整的AI批改UI应包含：

1. 分数总览
   例如：总分：8/10

2. 步骤分析
   例如：
   ✓ Step1 正确
   ⚠ Step2 推导不完整
   ✗ Step3 公式错误

3. 扣分原因
   例如：-2：忽略定义域

4. 标准解法
   必须：带完整步骤

5. 多解法展示
   例如：方法1：换元 方法2：Taylor

6. 错因分析
   例如：概念错误、运算错误

7. 学习建议
   例如：建议强化：Taylor展开、同类题推荐
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from dataclasses_json import dataclass_json

# 导入通用枚举（StepStatus 已移至 common_enums）
from common_enums import StepStatus, STEP_STATUS_LABELS


# ═══════════════════════════════════════════════
# 步骤状态枚举已移至 common_enums
# ═══════════════════════════════════════════════


STEP_STATUS_SYMBOLS = {
    StepStatus.CORRECT: "OK",
    StepStatus.PARTIAL: "WA",
    StepStatus.WRONG: "NG",
    StepStatus.MISSING: "--"
}

STEP_STATUS_COLORS = {
    StepStatus.CORRECT: "\033[92m",   # 绿色
    StepStatus.PARTIAL: "\033[93m",   # 黄色
    StepStatus.WRONG: "\033[91m",     # 红色
    StepStatus.MISSING: "\033[90m",   # 灰色
}


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class StepEvaluation:
    """步骤评估"""
    step_index: int
    step_content: str
    status: str  # "correct", "partial", "wrong", "missing"
    score: float
    max_score: float
    deduction: float
    reason: str  # 扣分原因
    error_type: str = ""  # "concept", "algebraic", "arithmetic", "logic"
    suggestion: str = ""  # 改进建议


@dataclass_json
@dataclass
class SolutionMethod:
    """解法"""
    method_name: str  # "换元法", "Taylor展开"
    method_type: str  # "substitution", "taylor"
    steps: List[str]  # 步骤列表
    key_points: List[str]  # 关键点
    score_weight: float = 1.0  # 方法权重


@dataclass_json
@dataclass
class ErrorAnalysis:
    """错误分析"""
    error_type: str  # "概念错误", "运算错误", "推理断裂", "方法错误"
    severity: str  # "高", "中", "低"
    description: str
    related_knowledge: List[str]
    suggestions: List[str]


@dataclass_json
@dataclass
class LearningSuggestion:
    """学习建议"""
    topic: str  # "Taylor展开", "换元法"
    priority: str  # "high", "medium", "low"
    reason: str
    similar_questions: List[str] = field(default_factory=list)
    practice_count: int = 3


@dataclass_json
@dataclass
class FeedbackReport:
    """完整反馈报告"""
    question_id: str
    question_text: str
    total_score: float
    max_score: float
    score_percentage: float
    step_evaluations: List[StepEvaluation]
    error_analyses: List[ErrorAnalysis]
    standard_solutions: List[SolutionMethod]
    alternative_solutions: List[SolutionMethod]
    learning_suggestions: List[LearningSuggestion]
    partial_credit_explanation: str


# ═══════════════════════════════════════════════
# UI渲染器
# ═══════════════════════════════════════════════

class FeedbackUI:
    """
    反馈UI渲染器

    将评分结果渲染为可读的报告
    """

    def __init__(self, use_color: bool = True, use_emoji: bool = False):
        self.use_color = use_color
        self.use_emoji = use_emoji

    def render_text(self, report: FeedbackReport) -> str:
        """渲染为纯文本"""
        lines = []

        lines.append(self._render_header(report))
        lines.append(self._render_score_overview(report))
        lines.append(self._render_step_analysis(report))
        lines.append(self._render_deduction_reasons(report))
        lines.append(self._render_error_analysis(report))
        lines.append(self._render_standard_solution(report))
        lines.append(self._render_alternative_solutions(report))
        lines.append(self._render_learning_suggestions(report))

        return "\n".join(lines)

    def render_html(self, report: FeedbackReport) -> str:
        """渲染为HTML"""
        html = ['<!DOCTYPE html>', '<html>', '<head>',
                '<meta charset="UTF-8">',
                '<style>',
                self._get_css(),
                '</style>', '</head>', '<body>']

        html.append('<div class="feedback-container">')

        html.append(self._render_html_header(report))
        html.append(self._render_html_score(report))
        html.append(self._render_html_steps(report))
        html.append(self._render_html_deductions(report))
        html.append(self._render_html_errors(report))
        html.append(self._render_html_solutions(report))
        html.append(self._render_html_suggestions(report))

        html.append('</div></body></html>')
        return "\n".join(html)

    def render_markdown(self, report: FeedbackReport) -> str:
        """渲染为Markdown"""
        lines = []

        lines.append(self._render_md_header(report))
        lines.append("")
        lines.append(self._render_md_score(report))
        lines.append("")
        lines.append(self._render_md_steps(report))
        lines.append("")
        lines.append(self._render_md_deductions(report))
        lines.append("")
        lines.append(self._render_md_errors(report))
        lines.append("")
        lines.append(self._render_md_solutions(report))
        lines.append("")
        lines.append(self._render_md_suggestions(report))

        return "\n".join(lines)

    # ─────────────────────────────────────────
    # Text Rendering
    # ─────────────────────────────────────────

    def _render_header(self, report: FeedbackReport) -> str:
        """渲染标题"""
        border = "=" * 60
        title = "【AI智能批改结果】"
        return f"\n{border}\n{title}\n{border}"

    def _render_score_overview(self, report: FeedbackReport) -> str:
        """渲染分数总览"""
        lines = []
        lines.append("\n【分数总览】")
        lines.append("-" * 40)

        percentage = report.score_percentage
        score_display = f"{report.total_score:.1f}/{report.max_score:.1f}"

        if percentage >= 90:
            grade = "优秀"
        elif percentage >= 70:
            grade = "良好"
        elif percentage >= 60:
            grade = "及格"
        else:
            grade = "需改进"

        lines.append(f"总分：{score_display} ({percentage:.0f}%)")
        lines.append(f"评级：{grade}")

        if report.partial_credit_explanation:
            lines.append(f"\n{report.partial_credit_explanation}")

        return "\n".join(lines)

    def _render_step_analysis(self, report: FeedbackReport) -> str:
        """渲染步骤分析"""
        lines = []
        lines.append("\n【步骤分析】")
        lines.append("-" * 40)

        for step in report.step_evaluations:
            status_symbol = self._get_status_symbol(step.status)

            status_text = {
                "correct": "正确",
                "partial": "部分正确",
                "wrong": "错误",
                "missing": "缺失"
            }.get(step.status, step.status)

            lines.append(f"  {status_symbol} Step{step.step_index + 1}: {step.step_content}")
            lines.append(f"      状态: {status_text}, 得分: {step.score:.1f}/{step.max_score:.1f}")

            if step.reason:
                lines.append(f"      原因: {step.reason}")

        return "\n".join(lines)

    def _render_deduction_reasons(self, report: FeedbackReport) -> str:
        """渲染扣分原因"""
        lines = []
        lines.append("\n【扣分原因】")
        lines.append("-" * 40)

        total_deducted = 0
        has_deductions = False

        for step in report.step_evaluations:
            if step.deduction > 0:
                has_deductions = True
                total_deducted += step.deduction
                error_type_display = {
                    "concept": "概念错误",
                    "algebraic": "代数错误",
                    "arithmetic": "算术错误",
                    "logic": "逻辑错误"
                }.get(step.error_type, step.error_type)

                lines.append(f"  -{step.deduction:.0f}分 Step{step.step_index + 1}:")
                lines.append(f"      [{error_type_display}] {step.reason}")
                if step.suggestion:
                    lines.append(f"      建议: {step.suggestion}")

        if not has_deductions:
            lines.append("  无扣分")

        return "\n".join(lines)

    def _render_error_analysis(self, report: FeedbackReport) -> str:
        """渲染错因分析"""
        lines = []
        lines.append("\n【错因分析】")
        lines.append("-" * 40)

        if not report.error_analyses:
            lines.append("  未发现明显错误")
        else:
            for error in report.error_analyses:
                lines.append(f"  【{error.error_type}】(严重程度: {error.severity})")
                lines.append(f"    {error.description}")
                if error.related_knowledge:
                    lines.append(f"    相关知识点: {', '.join(error.related_knowledge)}")
                if error.suggestions:
                    lines.append(f"    改进建议: {'; '.join(error.suggestions)}")

        return "\n".join(lines)

    def _render_standard_solution(self, report: FeedbackReport) -> str:
        """渲染标准解法"""
        lines = []
        lines.append("\n【标准解法】")
        lines.append("-" * 40)

        if not report.standard_solutions:
            lines.append("  暂无标准解法")
        else:
            for i, solution in enumerate(report.standard_solutions, 1):
                lines.append(f"\n  方法{i}：{solution.method_name}")
                for j, step in enumerate(solution.steps, 1):
                    lines.append(f"    Step{j}: {step}")
                if solution.key_points:
                    lines.append(f"    关键点: {'; '.join(solution.key_points)}")

        return "\n".join(lines)

    def _render_alternative_solutions(self, report: FeedbackReport) -> str:
        """渲染多解法展示"""
        lines = []
        lines.append("\n【多解法展示】")
        lines.append("-" * 40)

        if not report.alternative_solutions:
            lines.append("  无其他解法")
        else:
            for i, solution in enumerate(report.alternative_solutions, 1):
                lines.append(f"\n  方法{i}：{solution.method_name} (权重: {solution.score_weight:.0%})")
                for j, step in enumerate(solution.steps, 1):
                    lines.append(f"    Step{j}: {step}")

        return "\n".join(lines)

    def _render_learning_suggestions(self, report: FeedbackReport) -> str:
        """渲染学习建议"""
        lines = []
        lines.append("\n【学习建议】")
        lines.append("-" * 40)

        if not report.learning_suggestions:
            lines.append("  暂无建议")
        else:
            for suggestion in report.learning_suggestions:
                priority_icon = {"high": "!!!", "medium": "!!", "low": "!"}.get(
                    suggestion.priority, "!"
                )
                lines.append(f"\n  {priority_icon} 建议强化: {suggestion.topic}")
                lines.append(f"      原因: {suggestion.reason}")
                if suggestion.similar_questions:
                    lines.append(f"      同类题推荐: {', '.join(suggestion.similar_questions[:3])}")
                lines.append(f"      建议练习: {suggestion.practice_count}道")

        return "\n".join(lines)

    # ─────────────────────────────────────────
    # Markdown Rendering
    # ─────────────────────────────────────────

    def _render_md_header(self, report: FeedbackReport) -> str:
        return f"# AI智能批改结果 - 题目{report.question_id}"

    def _render_md_score(self, report: FeedbackReport) -> str:
        percentage = report.score_percentage
        grade = "优秀" if percentage >= 90 else "良好" if percentage >= 70 else "及格" if percentage >= 60 else "需改进"

        md = f"## 分数总览\n\n"
        md += f"| 项目 | 值 |\n"
        md += f"|------|----|\n"
        md += f"| 总分 | {report.total_score:.1f}/{report.max_score:.1f} |\n"
        md += f"| 得分率 | {percentage:.1f}% |\n"
        md += f"| 评级 | {grade} |\n"
        return md

    def _render_md_steps(self, report: FeedbackReport) -> str:
        md = "## 步骤分析\n\n"
        md += "| 步骤 | 内容 | 状态 | 得分 |\n"
        md += "|------|------|------|------|\n"

        for step in report.step_evaluations:
            status_icon = {"correct": "OK", "partial": "WA", "wrong": "NG", "missing": "--"}.get(step.status, "?")
            md += f"| Step{step.step_index + 1} | {step.step_content[:30]}... | {status_icon} | {step.score:.1f}/{step.max_score:.1f} |\n"

        return md

    def _render_md_deductions(self, report: FeedbackReport) -> str:
        md = "## 扣分原因\n\n"

        deductions = [(s.step_index + 1, s.deduction, s.reason, s.error_type) for s in report.step_evaluations if s.deduction > 0]

        if not deductions:
            return md + "无扣分\n"

        for step_num, ded, reason, err_type in deductions:
            err_display = {"concept": "概念错误", "algebraic": "代数错误", "arithmetic": "算术错误", "logic": "逻辑错误"}.get(err_type, err_type)
            md += f"- **-{ded:.0f}分** Step{step_num}: [{err_display}] {reason}\n"

        return md

    def _render_md_errors(self, report: FeedbackReport) -> str:
        md = "## 错因分析\n\n"

        if not report.error_analyses:
            return md + "未发现明显错误\n"

        for error in report.error_analyses:
            md += f"### {error.error_type} (严重程度: {error.severity})\n\n"
            md += f"{error.description}\n\n"
            if error.related_knowledge:
                md += f"**相关知识点**: {', '.join(error.related_knowledge)}\n\n"
            if error.suggestions:
                md += f"**改进建议**: {'; '.join(error.suggestions)}\n\n"

        return md

    def _render_md_solutions(self, report: FeedbackReport) -> str:
        md = "## 解法\n\n"

        if report.standard_solutions:
            md += "### 标准解法\n\n"
            for i, sol in enumerate(report.standard_solutions, 1):
                md += f"**方法{i}: {sol.method_name}**\n\n"
                for j, step in enumerate(sol.steps, 1):
                    md += f"{j}. {step}\n"
                md += "\n"

        if report.alternative_solutions:
            md += "### 其他解法\n\n"
            for i, sol in enumerate(report.alternative_solutions, 1):
                md += f"**方法{i}: {sol.method_name}** (权重: {sol.score_weight:.0%})\n\n"
                for j, step in enumerate(sol.steps, 1):
                    md += f"{j}. {step}\n"
                md += "\n"

        return md

    def _render_md_suggestions(self, report: FeedbackReport) -> str:
        md = "## 学习建议\n\n"

        if not report.learning_suggestions:
            return md + "暂无建议\n"

        for sug in report.learning_suggestions:
            priority = {"high": "!!!", "medium": "!!", "low": "!"}.get(sug.priority, "!")
            md += f"{priority} **建议强化: {sug.topic}**\n\n"
            md += f"- 原因: {sug.reason}\n"
            if sug.similar_questions:
                md += f"- 同类题: {', '.join(sug.similar_questions[:3])}\n"
            md += f"- 建议练习: {sug.practice_count}道\n\n"

        return md

    # ─────────────────────────────────────────
    # HTML Rendering
    # ─────────────────────────────────────────

    def _get_css(self) -> str:
        return """
        body { font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .feedback-container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section { margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; background: #f8f9fa; }
        .section-title { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px; }
        .score-display { font-size: 36px; color: #007bff; text-align: center; margin: 20px 0; }
        .grade { text-align: center; font-size: 20px; color: #666; }
        .step-item { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .step-correct { background: #d4edda; border-left: 4px solid #28a745; }
        .step-partial { background: #fff3cd; border-left: 4px solid #ffc107; }
        .step-wrong { background: #f8d7da; border-left: 4px solid #dc3545; }
        .deduction { color: #dc3545; font-weight: bold; }
        .method { margin: 15px 0; padding: 10px; background: #e9ecef; border-radius: 5px; }
        .suggestion { background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 5px; }
        .priority-high { color: #dc3545; font-weight: bold; }
        .priority-medium { color: #ffc107; font-weight: bold; }
        """

    def _render_html_header(self, report: FeedbackReport) -> str:
        return f'<h1 style="text-align:center;color:#007bff;">AI智能批改结果 - 题目{report.question_id}</h1>'

    def _render_html_score(self, report: FeedbackReport) -> str:
        percentage = report.score_percentage
        grade = "优秀" if percentage >= 90 else "良好" if percentage >= 70 else "及格" if percentage >= 60 else "需改进"
        grade_color = "#28a745" if percentage >= 70 else "#ffc107" if percentage >= 60 else "#dc3545"

        return f"""
        <div class="section">
            <div class="score-display">{report.total_score:.1f}/{report.max_score:.1f}</div>
            <div class="grade">得分率: {percentage:.1f}% | 评级: <span style="color:{grade_color};font-weight:bold;">{grade}</span></div>
        </div>
        """

    def _render_html_steps(self, report: FeedbackReport) -> str:
        html = '<div class="section"><div class="section-title">步骤分析</div>'

        for step in report.step_evaluations:
            status_class = {"correct": "step-correct", "partial": "step-partial", "wrong": "step-wrong"}.get(step.status, "")
            status_icon = {"correct": "OK", "partial": "WA", "wrong": "NG", "missing": "--"}.get(step.status, "?")
            status_text = {"correct": "正确", "partial": "部分正确", "wrong": "错误", "missing": "缺失"}.get(step.status, step.status)

            html += f'<div class="step-item {status_class}">'
            html += f'<b>[{status_icon}] Step{step.step_index + 1}:</b> {step.step_content}<br>'
            html += f'<small>状态: {status_text} | 得分: {step.score:.1f}/{step.max_score:.1f}</small>'
            if step.reason:
                html += f'<br><small style="color:#666;">原因: {step.reason}</small>'
            html += '</div>'

        html += '</div>'
        return html

    def _render_html_deductions(self, report: FeedbackReport) -> str:
        html = '<div class="section"><div class="section-title">扣分原因</div>'

        deductions = [(s.step_index + 1, s.deduction, s.reason, s.error_type) for s in report.step_evaluations if s.deduction > 0]

        if not deductions:
            return html + '<p>无扣分</p></div>'

        for step_num, ded, reason, err_type in deductions:
            err_display = {"concept": "概念错误", "algebraic": "代数错误", "arithmetic": "算术错误", "logic": "逻辑错误"}.get(err_type, err_type)
            html += f'<div class="deduction">-{ded:.0f}分 Step{step_num}: [{err_display}] {reason}</div>'

        html += '</div>'
        return html

    def _render_html_errors(self, report: FeedbackReport) -> str:
        html = '<div class="section"><div class="section-title">错因分析</div>'

        if not report.error_analyses:
            return html + '<p>未发现明显错误</p></div>'

        for error in report.error_analyses:
            html += f'<div class="suggestion"><b>{error.error_type}</b> (严重程度: {error.severity})<br>{error.description}'
            if error.related_knowledge:
                html += f'<br>相关知识点: {", ".join(error.related_knowledge)}'
            html += '</div>'

        html += '</div>'
        return html

    def _render_html_solutions(self, report: FeedbackReport) -> str:
        html = '<div class="section"><div class="section-title">解法</div>'

        for label, solutions in [("标准解法", report.standard_solutions), ("其他解法", report.alternative_solutions)]:
            if not solutions:
                continue
            html += f'<h4>{label}</h4>'
            for sol in solutions:
                html += f'<div class="method"><b>{sol.method_name}</b>'
                for j, step in enumerate(sol.steps, 1):
                    html += f'<br>{j}. {step}'
                html += '</div>'

        html += '</div>'
        return html

    def _render_html_suggestions(self, report: FeedbackReport) -> str:
        html = '<div class="section"><div class="section-title">学习建议</div>'

        if not report.learning_suggestions:
            return html + '<p>暂无建议</p></div>'

        for sug in report.learning_suggestions:
            priority_class = {"high": "priority-high", "medium": "priority-medium"}.get(sug.priority, "")
            html += f'<div class="suggestion {priority_class}">'
            html += f'<b>建议强化: {sug.topic}</b><br>'
            html += f'原因: {sug.reason}<br>'
            if sug.similar_questions:
                html += f'同类题: {", ".join(sug.similar_questions[:3])}<br>'
            html += f'建议练习: {sug.practice_count}道'
            html += '</div>'

        html += '</div>'
        return html

    # ─────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────

    def _get_status_symbol(self, status: str) -> str:
        if self.use_emoji:
            return {"correct": "✓", "partial": "⚠", "wrong": "✗", "missing": "○"}.get(status, "?")
        else:
            return {"correct": "OK", "partial": "WA", "wrong": "NG", "missing": "--"}.get(status, "?")


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def create_feedback_report(
    question_id: str,
    question_text: str,
    total_score: float,
    max_score: float,
    step_evaluations: List[StepEvaluation],
    error_analyses: List[ErrorAnalysis] = None,
    standard_solutions: List[SolutionMethod] = None,
    alternative_solutions: List[SolutionMethod] = None,
    learning_suggestions: List[LearningSuggestion] = None,
    partial_credit_explanation: str = ""
) -> FeedbackReport:
    """创建反馈报告"""
    percentage = (total_score / max_score * 100) if max_score > 0 else 0

    return FeedbackReport(
        question_id=question_id,
        question_text=question_text,
        total_score=total_score,
        max_score=max_score,
        score_percentage=percentage,
        step_evaluations=step_evaluations,
        error_analyses=error_analyses or [],
        standard_solutions=standard_solutions or [],
        alternative_solutions=alternative_solutions or [],
        learning_suggestions=learning_suggestions or [],
        partial_credit_explanation=partial_credit_explanation
    )


def render_feedback(
    report: FeedbackReport,
    format: str = "text"
) -> str:
    """渲染反馈报告"""
    ui = FeedbackUI()
    if format == "text":
        return ui.render_text(report)
    elif format == "html":
        return ui.render_html(report)
    elif format == "markdown":
        return ui.render_markdown(report)
    else:
        return ui.render_text(report)
